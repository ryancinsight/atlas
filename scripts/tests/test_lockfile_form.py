#!/usr/bin/env python3
"""The rule defining a standalone `Cargo.lock`, and the sweep over committed locks.

The rule separates two things a `git+` line count cannot: a lock whose git
source was *stripped* by the stack overlay, and a workspace that legitimately
resolves no git dependency at all. Both directions are asserted on the
predicate, then through `check_committed` over synthetic repositories so the
failure path is exercised end to end and the verdict is shown to come from the
commit, never the working tree.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path, PurePosixPath
from unittest import mock

SCRIPT = Path(__file__).resolve().parent.parent / "lockfile.py"
SPEC = importlib.util.spec_from_file_location("atlas_lockfile_form", SCRIPT)
lockfile = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lockfile
SPEC.loader.exec_module(lockfile)

ROOT_WORKSPACE = PurePosixPath(".")

STANDALONE = textwrap.dedent(
    """\
    version = 4

    [[package]]
    name = "member"
    version = "0.1.0"
    dependencies = ["eunomia"]

    [[package]]
    name = "eunomia"
    version = "0.8.0"
    source = "git+https://github.com/ryancinsight/eunomia#abc123"
    """
)

STRIPPED = textwrap.dedent(
    """\
    version = 4

    [[package]]
    name = "member"
    version = "0.1.0"
    dependencies = ["eunomia"]

    [[package]]
    name = "eunomia"
    version = "0.8.0"

    [[patch.unused]]
    name = "themis-topology"
    version = "0.3.0"
    """
)

MANIFEST = textwrap.dedent(
    """\
    [package]
    name = "member"
    version = "0.1.0"

    [dependencies]
    eunomia = { version = "0.8", git = "https://github.com/ryancinsight/eunomia" }
    """
)


class ViolationPredicateTestCase(unittest.TestCase):
    LOCAL = {"member"}
    DEPS = {"eunomia"}

    def test_standalone_lock_is_clean(self) -> None:
        self.assertEqual(lockfile.violations(STANDALONE, self.LOCAL, self.DEPS), [])

    def test_stripped_source_is_flagged(self) -> None:
        found = lockfile.violations(STRIPPED, self.LOCAL, self.DEPS)
        self.assertIn("`eunomia` locked without a git source (stripped)", found)

    def test_one_provider_stripped_while_another_keeps_its_source_is_flagged(self) -> None:
        """A partial strip: a count of first-party sources is still nonzero, so
        only the per-package rule sees it."""
        lock = STANDALONE + '\n[[package]]\nname = "hermes"\nversion = "0.2.0"\n'
        found = lockfile.violations(lock, self.LOCAL, {"eunomia", "hermes"})
        self.assertEqual(found, ["`hermes` locked without a git source (stripped)"])

    def test_patch_unused_residue_is_flagged_even_without_git_deps(self) -> None:
        """A workspace with zero git dependencies can still carry overlay residue:
        the overlay patches URLs it does not use, and cargo records them."""
        found = lockfile.violations(STRIPPED, self.LOCAL, set())
        self.assertEqual(found, ["1 [[patch.unused]] table(s): overlay residue"])

    def test_residue_beside_intact_sources_is_flagged(self) -> None:
        lock = STANDALONE + '\n[[patch.unused]]\nname = "themis-topology"\nversion = "0.3.0"\n'
        found = lockfile.violations(lock, self.LOCAL, self.DEPS)
        self.assertEqual(found, ["1 [[patch.unused]] table(s): overlay residue"])

    def test_member_with_no_git_dependencies_is_not_a_violation(self) -> None:
        """The false positive a `git+` line count would produce: zero git
        sources is correct when nothing is sourced from git."""
        registry_only = textwrap.dedent(
            """\
            version = 4

            [[package]]
            name = "member"
            version = "0.1.0"

            [[package]]
            name = "serde"
            version = "1.0.0"
            source = "registry+https://github.com/rust-lang/crates.io-index"
            """
        )
        self.assertEqual(lockfile.violations(registry_only, {"member"}, set()), [])

    def test_declared_but_unused_workspace_dependency_is_not_a_violation(self) -> None:
        """A `[workspace.dependencies]` row no crate consumes never reaches the
        lock; absence is correct, not a stripped source."""
        found = lockfile.violations(STANDALONE, self.LOCAL, self.DEPS | {"ritk-core"})
        self.assertEqual(found, [])

    def test_local_path_package_shadowing_a_git_name_is_not_a_violation(self) -> None:
        """A workspace that both declares and defines a package resolves it by
        path; a sourceless entry is then correct."""
        found = lockfile.violations(STRIPPED, {"member", "eunomia"}, self.DEPS)
        self.assertTrue(all("eunomia" not in problem for problem in found))

    def test_an_unparseable_lock_is_a_violation(self) -> None:
        found = lockfile.violations("[[package\n", self.LOCAL, self.DEPS)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("unparseable lock"))


class DependencyTablesTestCase(unittest.TestCase):
    """A dependency declared in any table counts, so no declaration hides a strip."""

    def declared(self, manifest: str) -> frozenset[str]:
        facts = lockfile.workspace_facts({"Cargo.toml": manifest}, ROOT_WORKSPACE, [])
        return facts.git_dependencies

    def test_every_table_that_declares_dependencies_is_read(self) -> None:
        git = '{ git = "https://github.com/ryancinsight/p" }'
        tables = {
            "[dependencies]": "regular",
            "[dev-dependencies]": "development",
            "[build-dependencies]": "build",
            "[workspace.dependencies]": "shared",
            "[target.'cfg(unix)'.dependencies]": "unix",
            "[target.'cfg(unix)'.dev-dependencies]": "unixdev",
            "[target.'cfg(unix)'.build-dependencies]": "unixbuild",
        }
        for header, name in tables.items():
            with self.subTest(header):
                manifest = f'[package]\nname = "m"\nversion = "0.1.0"\n\n{header}\n{name} = {git}\n'
                if header == "[workspace.dependencies]":
                    manifest += f'[dependencies]\n{name} = {{ workspace = true }}\n'
                self.assertEqual(self.declared(manifest), {name})

    def test_strong_and_weak_features_have_distinct_source_requirements(self) -> None:
        dependencies = [(name, {"optional": True}, PurePosixPath("Cargo.toml")) for name in ("inside", "outside")]
        for reference, expected in (("inside/extra", {"inside", "outside"}), ("inside?/extra", {"inside"})):
            with self.subTest(reference):
                manifest = {"features": {"bundle": [reference], "inside": ["dep:inside", "dep:outside"]}}
                active, forwarded = lockfile.active_dependencies(manifest, dependencies, {"bundle"})
                self.assertEqual((active, forwarded), (expected, {"inside": {"extra"}}))

    def test_a_renamed_dependency_is_declared_under_its_package_name(self) -> None:
        manifest = (
            '[package]\nname = "m"\nversion = "0.1.0"\n\n[dependencies]\n'
            'alias = { package = "real", git = "https://github.com/ryancinsight/p" }\n'
        )
        self.assertEqual(self.declared(manifest), {"real"})

    def test_registry_and_path_dependencies_are_not_git_dependencies(self) -> None:
        manifest = (
            '[package]\nname = "m"\nversion = "0.1.0"\n\n[dependencies]\n'
            'serde = "1"\nlocal = { path = "../local" }\n'
        )
        self.assertEqual(self.declared(manifest), frozenset())

    def test_a_stripped_dev_dependency_is_found_through_the_whole_rule(self) -> None:
        manifest = (
            '[package]\nname = "member"\nversion = "0.1.0"\n\n[dev-dependencies]\n'
            'eunomia = { version = "0.8", git = "https://github.com/ryancinsight/eunomia" }\n'
        )
        problems, exempt = lockfile.judge_locks({"Cargo.toml": manifest, "Cargo.lock": STRIPPED})
        self.assertIn("Cargo.lock: `eunomia` locked without a git source (stripped)", problems)
        self.assertEqual(exempt, [])


class FixtureDetectionTestCase(unittest.TestCase):
    """Only a workspace reaching *outside its own repository* by path is an
    in-tree fixture. An intra-repo `path = ".."` (the fuzz-crate idiom) must
    not exempt the whole workspace from the rule."""

    def facts(self, dependency: str, directory: str = "fuzz") -> lockfile.WorkspaceFacts:
        manifests = {
            "Cargo.toml": '[package]\nname = "member"\nversion = "0.1.0"\n',
            f"{directory}/Cargo.toml": (
                f'[package]\nname = "sub"\nversion = "0.1.0"\n\n[dependencies]\n{dependency}\n'
            ),
        }
        return lockfile.workspace_facts(manifests, PurePosixPath(directory), [])

    def test_intra_repo_parent_path_is_not_a_fixture(self) -> None:
        self.assertFalse(self.facts('member = { path = ".." }').fixture)

    def test_cross_repo_path_is_a_fixture(self) -> None:
        self.assertTrue(self.facts('other = { path = "../../sibling" }').fixture)

    def test_a_path_leaving_the_repository_from_a_deeper_manifest_is_a_fixture(self) -> None:
        self.assertTrue(self.facts('other = { path = "../../../x" }', "a/b").fixture)

    def test_a_path_staying_inside_from_a_deeper_manifest_is_not_a_fixture(self) -> None:
        self.assertFalse(self.facts('other = { path = "../../c" }', "a/b").fixture)

    def test_an_absolute_path_is_a_fixture(self) -> None:
        self.assertTrue(self.facts('other = { path = "/opt/other" }').fixture)

    def test_a_windows_drive_path_is_a_fixture_in_either_separator(self) -> None:
        self.assertTrue(self.facts('other = { path = "C:/opt/other" }').fixture)
        self.assertTrue(self.facts(r"other = { path = 'C:\opt\other' }").fixture)

    def test_a_path_resolving_exactly_to_the_parent_of_the_repository_is_a_fixture(self) -> None:
        """`..` from the root manifest and `../../..` from `a/b` both name the
        directory above the repository, with no component left after the `..`."""
        self.assertTrue(
            lockfile.workspace_facts(
                {"Cargo.toml": '[dependencies]\nup = { path = ".." }\n'}, ROOT_WORKSPACE, []
            ).fixture
        )
        self.assertTrue(self.facts('other = { path = "../../.." }', "a/b").fixture)

    def test_a_path_resolving_to_the_repository_root_is_not_a_fixture(self) -> None:
        self.assertFalse(self.facts('other = { path = "../.." }', "a/b").fixture)

    def test_inherited_external_paths_keep_their_workspace_origin(self) -> None:
        texts = {
            "Cargo.toml": '[workspace]\nmembers = ["member"]\n[workspace.dependencies]\n'
                          'outside = { path = "../outside" }\n',
            "member/Cargo.toml": '[package]\nname = "member"\nversion = "0.1.0"\n'
                                 '[dependencies]\noutside = { workspace = true }\n',
            "Cargo.lock": STANDALONE,
        }
        self.assertEqual(lockfile.judge_locks(texts), ([], ["Cargo.lock"]))

    def test_a_fixture_lock_is_exempt_and_reported(self) -> None:
        manifests = {
            "Cargo.toml": '[package]\nname = "m"\nversion = "0.1.0"\n\n[dependencies]\n'
            'x = { path = "../../sibling" }\n',
            "Cargo.lock": STRIPPED,
        }
        problems, exempt = lockfile.judge_locks(manifests)
        self.assertEqual((problems, exempt), ([], ["Cargo.lock"]))


class LockManifestSelectionTestCase(unittest.TestCase):
    def test_root_and_excluded_workspace_locks_are_selected(self) -> None:
        texts = {"Cargo.toml": '[workspace]\nexclude = ["fuzz"]\n', "Cargo.lock": STANDALONE,
                 "fuzz/Cargo.toml": '[package]\nname = "fuzz"\nversion = "0.0.0"\n[workspace]\n[dependencies]\npal = { path = "../pal" }\n',
                 "fuzz/Cargo.lock": STANDALONE, "orphan/Cargo.toml": '[package]\nname = "orphan"\nversion = "0.1.0"\n'}
        self.assertEqual(lockfile.lock_manifests(texts), (["Cargo.toml", "fuzz/Cargo.toml"], [], ["orphan/Cargo.toml: sibling Cargo.lock is missing"]))
        self.assertEqual(lockfile.lock_manifests({"nested/Cargo.lock": STANDALONE}), ([], [], ["nested/Cargo.lock: sibling Cargo.toml is missing"]))

    def test_candidate_rejects_directory_links(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
            root = Path(temp)
            (linked := root / "linked").mkdir()
            original_link = Path.is_symlink
            with (
                mock.patch.object(Path, "is_symlink", lambda path: path.name == "linked" or original_link(path)),
                self.assertRaisesRegex(OSError, "symbolic directory link"),
            ):
                lockfile.disk_texts(root, ignored_directories=frozenset())

    def test_candidate_rejects_file_metadata_links(self) -> None:
        for name in ("Cargo.toml", "Cargo.lock", lockfile.PROVIDER_IDENTITY_BASELINE_NAME):
            with self.subTest(name), tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
                root = Path(temp)
                outside = root / "outside"
                outside.write_text("outside input")
                candidate = root / "tree"
                candidate.mkdir()
                try:
                    (candidate / name).symlink_to(outside)
                except OSError as error:
                    self.skipTest(f"this host cannot create a file symlink: {error}")
                with self.assertRaisesRegex(OSError, "symbolic metadata link"):
                    lockfile.disk_texts(candidate, ignored_directories=frozenset())
                self.assertEqual(outside.read_text(), "outside input")

    def test_cli_keeps_the_candidate_root_lexical(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
            root = Path(temp)
            (manifest := root / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
            (root / "Cargo.lock").write_text("version = 4\n", encoding="utf-8")
            original_resolve, original_link = Path.resolve, Path.is_symlink

            def resolve(path: Path, *args, **kwargs) -> Path:
                self.assertNotEqual(path, manifest, "CLI resolved the requested manifest")
                return original_resolve(path, *args, **kwargs)
            with (
                mock.patch.object(sys, "argv", ["lockfile.py", "--check", "--manifest-path", str(manifest)]),
                mock.patch.object(Path, "resolve", resolve),
                mock.patch.object(Path, "is_symlink", lambda path: path == manifest or original_link(path)),
                contextlib.redirect_stderr(stderr := io.StringIO()),
            ):
                code = lockfile.main()
        self.assertEqual(code, 1)
        self.assertIn("symbolic metadata link", stderr.getvalue())


class TreeCheckTestCase(unittest.TestCase):
    @staticmethod
    def write(root: Path, relative: str, text: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def cargo(self, root: Path, manifest: str) -> None:
        completed = lockfile.run_outside_the_overlay(["generate-lockfile"], root / manifest, deadline=60)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def package(self, root: Path, directory: str, name: str, extra: str = "") -> str:
        manifest = f"{directory}/Cargo.toml"
        self.write(root, manifest, f'[package]\nname = "{name}"\nversion = "0.1.0"\n'
                   f'edition = "2024"\n{extra}')
        self.write(root, f"{directory}/src/lib.rs", "pub fn present() {}\n")
        return manifest

    def test_tree_cli_accepts_a_member_under_build_output_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
            root = Path(temp)
            self.write(root, "Cargo.toml", '[workspace]\nresolver = "3"\nmembers = ["target/tool"]\n')
            self.package(root, "target/tool", "tracked-member")
            self.cargo(root, "Cargo.toml")
            command = [sys.executable, str(SCRIPT), "--check", "--check-tree", str(root)]
            completed = lockfile.run_bounded(command, cwd=root, env=os.environ, deadline=60)
        self.assertEqual((completed.returncode, completed.stdout.count("checking lock owner")), (0, 1), completed.stderr)

    def test_tree_cli_rejects_each_independent_package_without_a_lock(self) -> None:
        cases = (("orphan", ""), ("good/nested", "[workspace]\n"))
        for directory, extra in cases:
            with self.subTest(directory), tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
                root = Path(temp)
                self.package(root, directory, "orphan", extra)
                self.cargo(root, self.package(root, "good", "good", '[dependencies]\norphan = { path = "../orphan" }\n' if directory == "orphan" else ""))
                command = [sys.executable, str(SCRIPT), "--check", "--check-tree", str(root)]
                completed = lockfile.run_bounded(command, cwd=root, env=os.environ, deadline=60)
            missing = f"{directory}/Cargo.toml: sibling Cargo.lock is missing"
            self.assertEqual((completed.returncode, missing in completed.stderr), (1, True), completed.stdout)

    def assert_stale_consumer_lock(self, root: Path) -> None:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(lockfile.check(root), 0)
        lock = root / "Cargo.lock"
        lock.write_text(lock.read_text().replace('name = "consumer"\nversion = "0.1.0"',
                                                 'name = "consumer"\nversion = "0.0.1"'))
        metadata = lockfile.run_outside_the_overlay(["metadata", "--offline", "--locked", "--format-version", "1"],
                                                   root / "Cargo.toml", deadline=60)
        self.assertEqual(metadata.returncode, 101, metadata.stderr)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr := io.StringIO()):
            self.assertEqual(lockfile.check(root), 1)
        self.assertIn("does not resolve under --locked", stderr.getvalue())

    def test_inherited_sources_match_cargo(self) -> None:
        cases = (('{ path = "dep" }', 'workspace = true, path = "../missing"', ""),
                 ('"0.1.0"', 'workspace = true', '[patch.crates-io]\ndep = { path = "dep" }\n'))
        for default, declaration, patch in cases:
            with self.subTest(default), tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
                root = Path(temp)
                self.write(root, "Cargo.toml", '[package]\nname = "consumer"\nversion = "0.1.0"\nedition = "2024"\n'
                           '[workspace]\nexclude = ["dep"]\n[workspace.dependencies]\n'
                           f'dep = {default}\n[dependencies]\ndep = {{ {declaration} }}\n{patch}')
                self.write(root, "src/lib.rs", "")
                self.package(root, "dep", "dep", '[workspace]\n')
                for manifest in ("Cargo.toml", "dep/Cargo.toml"):
                    generated = lockfile.run_outside_the_overlay(["generate-lockfile", "--offline"],
                                                                 root / manifest, deadline=60)
                    self.assertEqual(generated.returncode, 0, generated.stderr)
                self.assert_stale_consumer_lock(root)


    def test_unused_dependency_edges_do_not_exempt_a_stale_consuming_lock(self) -> None:
        for kind in ("dev-dependencies", "target.'cfg(unix)'.dev-dependencies", "workspace.dependencies"):
            with self.subTest(kind), tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
                root = Path(temp)
                self.write(root, "Cargo.toml", '[package]\nname = "consumer"\nversion = "0.1.0"\nedition = "2024"\n'
                           '[workspace]\nexclude = ["dep"]\n[dependencies]\ndep = { path = "dep" }\n')
                self.write(root, "src/lib.rs", "")
                self.package(root, "dep", "dep", f'[workspace]\n[{kind}]\nmissing = {{ path = "../../missing" }}\n')
                self.cargo(root, "Cargo.toml")
                if kind == "workspace.dependencies":
                    self.cargo(root, "dep/Cargo.toml")
                self.assert_stale_consumer_lock(root)

    def test_excluded_inheritance_cannot_create_a_fixture_exemption(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
            root = Path(temp)
            self.write(root, "Cargo.toml", '[workspace]\nmembers = ["app"]\nexclude = ["fixture"]\n'
                       '[workspace.dependencies]\noutside = { path = "../outside" }\n')
            self.package(root, "app", "app")
            self.package(root, "fixture", "fixture", '[dependencies]\noutside.workspace = true\n')
            self.cargo(root, "Cargo.toml")
            self.write(root, "fixture/Cargo.lock", 'version = 4\n[[package]]\nname = "fixture"\nversion = "0.1.0"\n')
            ownership = lockfile.run_outside_the_overlay(["locate-project", "--workspace", "--message-format", "json"],
                                                        root / "fixture/Cargo.toml", deadline=60)
            self.assertEqual(ownership.returncode, 101, ownership.stderr)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr := io.StringIO()):
                self.assertEqual(lockfile.check(root), 1)
            self.assertIn("LOCK OWNERSHIP VIOLATION", stderr.getvalue())
            self.assertIn("failed to find a workspace root", stderr.getvalue())

    def test_external_owner_and_override_paths_fail_before_cargo(self) -> None:
        cases = ('[patch.crates-io]\ndep = { path = "../outside" }\n',
                 '[replace]\n"dep:0.1.0" = { path = "../outside" }\n',
                 '[package]\nname = "app"\nversion = "0.1.0"\nworkspace = "../outside"\n',
                 '[workspace]\nmembers = ["../outside"]\n')
        for manifest in cases:
            with self.subTest(manifest), tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
                root = Path(temp)
                self.write(root, "Cargo.toml", manifest)
                self.write(root, "Cargo.lock", 'version = 4\n')
                # Any Cargo attempt uses a missing executable and raises immediately.
                with mock.patch.object(lockfile, "CARGO_COMMAND", ("missing-cargo-boundary-probe",)), contextlib.redirect_stdout(stdout := io.StringIO()), contextlib.redirect_stderr(stderr := io.StringIO()):
                    self.assertEqual(lockfile.check(root), 1)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("path leaves the candidate: ../outside", stderr.getvalue())

    def test_fixture_overrides_are_not_resolved(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
            root = Path(temp)
            self.write(root, "Cargo.toml", '[package]\nname = "fixture"\nversion = "0.1.0"\nedition = "2024"\n'
                       '[workspace]\n[dependencies]\noutside = { path = "../outside" }\n'
                       '[patch.crates-io]\npatched = { path = "../patched" }\n')
            self.write(root, "src/lib.rs", "")
            self.write(root, "Cargo.lock", 'version = 4\n')
            with contextlib.redirect_stdout(stdout := io.StringIO()), contextlib.redirect_stderr(stderr := io.StringIO()):
                self.assertEqual(lockfile.check(root), 0, stderr.getvalue())
            self.assertIn("exempt (in-tree fixture", stdout.getvalue())
            self.assertNotIn("resolves under --locked", stdout.getvalue())

    def test_internal_overrides_cannot_load_external_dependency_graphs(self) -> None:
        for optional in ("", ", optional = true"):
            with self.subTest(optional), tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
                root = Path(temp)
                self.write(root, "Cargo.toml", '[package]\nname = "app"\nversion = "0.1.0"\nedition = "2024"\n'
                           '[workspace]\nexclude = ["dep"]\n[dependencies]\ndep = "0.1.0"\n'
                           '[patch.crates-io]\ndep = { path = "dep" }\n')
                self.write(root, "src/lib.rs", "")
                self.package(root, "dep", "dep", f'[workspace]\n[dependencies]\noutside = {{ path = "../../outside"{optional} }}\n')
                self.write(root, "Cargo.lock", 'version = 4\n')
                with mock.patch.object(lockfile, "CARGO_COMMAND", ("missing-cargo-boundary-probe",)), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr := io.StringIO()):
                    self.assertEqual(lockfile.check(root), 1)
                self.assertIn("source override path leaves the candidate: ../../outside", stderr.getvalue())

    def test_optional_external_edges_match_cargo_features(self) -> None:
        cases = (
            ("", "", False),
            ("", '[features]\ndefault = ["outside"]\n', True),
            ('default-features = false', '[features]\ndefault = ["outside"]\n', False),
            ('features = ["bundle"]', '[features]\nbundle = ["dep:outside"]\n', True),
            ("", '[features]\ndefault = ["outside?/extra"]\n', True),
            ("", '[features]\ndefault = ["outside/extra"]\n', True),
        )
        for options, features, active in cases:
            with self.subTest(options=options, features=features), tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
                parent = Path(temp)
                root = parent / "tree"
                outside = parent / "outside"
                self.write(outside, "Cargo.toml", '[package]\nname = "outside"\nversion = "0.1.0"\nedition = "2024"\n[features]\nextra = []\n')
                self.write(outside, "src/lib.rs", "")
                suffix = f", {options}" if options else ""
                self.write(root, "Cargo.toml", '[package]\nname = "consumer"\nversion = "0.1.0"\nedition = "2024"\n'
                           f'[workspace]\nexclude = ["dep"]\n[dependencies]\ndep = {{ path = "dep"{suffix} }}\n')
                self.write(root, "src/lib.rs", "")
                self.package(root, "dep", "dep", '[workspace]\n[dependencies]\noutside = { path = "../../outside", optional = true }\n' + features)
                self.cargo(root, "Cargo.toml")
                self.cargo(root, "dep/Cargo.toml")
                (outside / "Cargo.toml").unlink()
                metadata = lockfile.run_outside_the_overlay(["metadata", "--offline", "--locked", "--all-features", "--format-version", "1"],
                                                           root / "Cargo.toml", deadline=60)
                self.assertEqual(metadata.returncode, 101 if active else 0, metadata.stderr)
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr := io.StringIO()):
                    self.assertEqual(lockfile.check(root), 0, stderr.getvalue())
                lock = root / "Cargo.lock"
                lock.write_text(lock.read_text().replace('name = "consumer"\nversion = "0.1.0"',
                                                         'name = "consumer"\nversion = "0.0.1"'))
                with contextlib.redirect_stdout(stdout := io.StringIO()), contextlib.redirect_stderr(stderr := io.StringIO()):
                    self.assertEqual(lockfile.check(root), 0 if active else 1, stderr.getvalue())
                self.assertEqual("exempt (in-tree fixture, not standalone-consumable): Cargo.lock" in stdout.getvalue(), active)

    def test_excluded_dependencies_do_not_add_workspace_members(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
            root = Path(temp)
            self.write(root, "Cargo.toml", '[package]\nname = "consumer"\nversion = "0.1.0"\nedition = "2024"\n'
                       '[workspace]\nexclude = ["dep"]\n[dependencies]\ndep = { path = "dep" }\n')
            self.write(root, "src/lib.rs", "")
            self.package(root, "dep", "dep", '[workspace]\n[dependencies]\nchild = { path = "../child" }\n')
            self.package(root, "child", "child", '[dependencies]\noutside = { path = "../../outside", optional = true }\n')
            self.cargo(root, "Cargo.toml")
            self.cargo(root, "dep/Cargo.toml")
            self.assert_stale_consumer_lock(root)

    def test_member_locks_fail_before_resolving_the_parent_fixture(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
            root = Path(temp)
            self.write(root, "Cargo.toml", '[workspace]\nmembers = ["member", "fixture"]\n')
            self.package(root, "member", "member")
            self.package(root, "fixture", "fixture", '[dependencies]\noutside = { path = "../../outside" }\n')
            for lock in ("Cargo.lock", "member/Cargo.lock"):
                self.write(root, lock, 'version = 4\n')
            with contextlib.redirect_stdout(stdout := io.StringIO()), contextlib.redirect_stderr(stderr := io.StringIO()):
                self.assertEqual(lockfile.check(root), 1)
            self.assertIn("Cargo uses", stderr.getvalue())
            self.assertNotIn("checking lock owner", stdout.getvalue())

    def test_a_member_lock_is_not_checked_through_its_parent_lock(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
            root = Path(temp)
            self.write(root, "Cargo.toml", '[workspace]\nresolver = "3"\nmembers = ["member"]\n')
            self.package(root, "member", "member")
            self.cargo(root, "Cargo.toml")
            self.write(root, "member/Cargo.lock", 'version = 4\n[[package]]\nname = "member"\nversion = "0.0.1"\n')
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr := io.StringIO()):
                code = lockfile.check(root)
            self.assertEqual(code, 1)
            self.assertIn("LOCK OWNERSHIP VIOLATION", stderr.getvalue())
            self.assertIn("Cargo uses", stderr.getvalue())
            self.assertEqual((root / "member/Cargo.lock").read_text(), 'version = 4\n[[package]]\nname = "member"\nversion = "0.0.1"\n')

    def test_target_dependency_stales_only_the_excluded_workspace_lock(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lock-tree-") as temp:
            root = Path(temp)
            self.write(root, "Cargo.toml", '[workspace]\nresolver = "3"\n'
                       'members = ["pal", "support"]\nexclude = ["fuzz"]\n')
            for package in ("pal", "support"):
                self.package(root, package, package)
            self.package(root, "fuzz", "fuzz", '[workspace]\n[dependencies]\npal = { path = "../pal" }\n')
            self.cargo(root, "Cargo.toml")
            self.cargo(root, "fuzz/Cargo.toml")
            with (root / "pal/Cargo.toml").open("a", encoding="utf-8") as manifest:
                manifest.write("\n[target.'cfg(loom)'.dependencies]\n"
                               'support = { path = "../support" }\n')
            self.cargo(root, "Cargo.toml")
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                bad = lockfile.check(root)
            self.assertEqual((bad, "fuzz" in stderr.getvalue(), "exempt" in stdout.getvalue()), (1, True, False))
            self.cargo(root, "fuzz/Cargo.toml")
            self.assertEqual(lockfile.check(root), 0)


class WorkspaceScopeTestCase(unittest.TestCase):
    def test_a_nested_workspace_owns_its_manifests(self) -> None:
        """Manifests under a sibling lock's root belong to that lock."""
        manifests = {
            "Cargo.toml": '[package]\nname = "outer"\nversion = "0.1.0"\n',
            "fuzz/Cargo.toml": '[package]\nname = "inner"\nversion = "0.1.0"\n\n[dependencies]\n'
            'p = { git = "https://github.com/ryancinsight/p" }\n',
        }
        outer = lockfile.workspace_facts(manifests, ROOT_WORKSPACE, [PurePosixPath("fuzz")])
        inner = lockfile.workspace_facts(manifests, PurePosixPath("fuzz"), [])
        self.assertEqual((outer.local, outer.git_dependencies), ({"outer"}, frozenset()))
        self.assertEqual((inner.local, inner.git_dependencies), ({"inner"}, {"p"}))

    def test_build_output_manifests_are_not_part_of_a_workspace(self) -> None:
        manifests = {
            "Cargo.toml": '[package]\nname = "m"\nversion = "0.1.0"\n',
            "target/package/x/Cargo.toml": '[dependencies]\np = { git = "https://x/p" }\n',
        }
        self.assertEqual(
            lockfile.workspace_facts(manifests, ROOT_WORKSPACE, []).git_dependencies, frozenset()
        )

    def test_a_manifest_that_does_not_parse_makes_the_lock_unjudgeable(self) -> None:
        problems, _ = lockfile.judge_locks({"Cargo.toml": "[package\n", "Cargo.lock": STANDALONE})
        self.assertEqual(
            problems, ["Cargo.lock: Cargo.toml does not parse, so the lock cannot be judged"]
        )

    def test_a_member_outside_the_lock_directory_belongs_to_the_workspace(self) -> None:
        """Membership is the `members` list, not containment by the lock's directory.

        `tools/Cargo.lock` is resolved by `tools/Cargo.toml`, whose member lives
        beside it. Reading only manifests under `tools/` missed the member's git
        dependency entirely, so a stripped source passed.
        """
        manifests = {
            "tools/Cargo.toml": '[workspace]\nmembers = ["../shared"]\n',
            "shared/Cargo.toml": '[package]\nname = "shared"\nversion = "0.1.0"\n\n'
            '[dependencies]\n'
            'eunomia = { git = "https://github.com/ryancinsight/eunomia" }\n',
            "tools/Cargo.lock": STRIPPED,
        }
        problems, exempt = lockfile.judge_locks(manifests)
        self.assertIn(
            "tools/Cargo.lock: `eunomia` locked without a git source (stripped)", problems
        )
        self.assertEqual(exempt, [])

    def test_an_excluded_crate_does_not_shadow_a_stripped_source(self) -> None:
        """`exclude` wins over `members`: the excluded crate's package name is not
        a local package of the workspace, so it cannot explain a sourceless entry.
        """
        manifests = {
            "Cargo.toml": '[workspace]\nmembers = ["member", "shadow"]\nexclude = ["shadow"]\n',
            "member/Cargo.toml": '[package]\nname = "member"\nversion = "0.1.0"\n\n'
            '[dependencies]\n'
            'eunomia = { git = "https://github.com/ryancinsight/eunomia" }\n',
            "shadow/Cargo.toml": '[package]\nname = "eunomia"\nversion = "0.1.0"\n',
            "Cargo.lock": STRIPPED,
        }
        problems, exempt = lockfile.judge_locks(manifests)
        self.assertIn(
            "Cargo.lock: `eunomia` locked without a git source (stripped)", problems
        )
        self.assertEqual(exempt, [])

    def test_a_lockless_nested_workspace_does_not_exempt_the_root_lock(self) -> None:
        """A nested `[workspace]` is a separate unit even without its own lock, so
        its path outside the repository cannot turn the root lock into a fixture.
        """
        manifests = {
            "Cargo.toml": '[workspace]\n\n[package]\nname = "member"\nversion = "0.1.0"\n\n'
            '[dependencies]\n'
            'eunomia = { git = "https://github.com/ryancinsight/eunomia" }\n',
            "nested/Cargo.toml": '[workspace]\n\n[package]\nname = "nested"\nversion = "0.1.0"\n\n'
            '[dependencies]\n'
            'sibling = { path = "../../outside" }\n',
            "Cargo.lock": STRIPPED,
        }
        problems, exempt = lockfile.judge_locks(manifests)
        self.assertIn(
            "Cargo.lock: `eunomia` locked without a git source (stripped)", problems
        )
        self.assertEqual(exempt, [])

    def test_a_members_glob_selects_the_packages_it_names(self) -> None:
        manifests = {
            "Cargo.toml": '[workspace]\nmembers = ["crates/*"]\n',
            "crates/member/Cargo.toml": '[package]\nname = "member"\nversion = "0.1.0"\n\n'
            '[dependencies]\n'
            'eunomia = { git = "https://github.com/ryancinsight/eunomia" }\n',
            "other/Cargo.toml": '[package]\nname = "eunomia"\nversion = "0.1.0"\n',
            "Cargo.lock": STRIPPED,
        }
        problems, _ = lockfile.judge_locks(manifests)
        self.assertIn(
            "Cargo.lock: `eunomia` locked without a git source (stripped)", problems
        )


def git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), "-c", "user.email=t@t", "-c", "user.name=t",
         "-c", "core.autocrlf=false", *arguments],
        check=True, capture_output=True, text=True, encoding="utf-8", timeout=60,
    ).stdout.strip()


class CommittedSweepTestCase(unittest.TestCase):
    """Drive `check_committed` over synthetic repositories."""

    def repository(self, files: dict[str, str]) -> Path:
        directory = tempfile.TemporaryDirectory(prefix="atlas-lock-sweep-")
        self.addCleanup(directory.cleanup)
        repository = Path(directory.name) / "synthetic"
        repository.mkdir()
        git(repository, "init", "-q", "-b", "main")
        for name, text in files.items():
            path = repository / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        git(repository, "add", "-A")
        git(repository, "commit", "-q", "-m", "seed")
        return repository

    def sweep(self, *repositories: Path) -> tuple[int, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = lockfile.check_committed(list(repositories))
        return status, output.getvalue()

    def test_a_committed_stripped_lock_fails(self) -> None:
        status, output = self.sweep(self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STRIPPED}))
        self.assertEqual(status, 1)
        self.assertIn("LOCK FORM VIOLATION: synthetic/Cargo.lock: `eunomia` locked without", output)
        self.assertIn("2 violation(s) across 1 committed lock(s)", output)

    def test_a_committed_standalone_lock_passes(self) -> None:
        status, output = self.sweep(self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STANDALONE}))
        self.assertEqual(status, 0)
        self.assertIn("lock form clean: 1 committed lock(s) resolve standalone", output)

    def test_a_stripped_lock_in_a_tool_workspace_is_flagged(self) -> None:
        """A cargo run inside a tool workspace walks up into the stack overlay
        exactly as a member's does, so every tracked lock is judged, not only
        the root's."""
        repository = self.repository(
            {"tools/synthetic/Cargo.toml": MANIFEST, "tools/synthetic/Cargo.lock": STRIPPED}
        )
        status, output = self.sweep(repository)
        self.assertEqual(status, 1)
        self.assertIn("synthetic/tools/synthetic/Cargo.lock", output)

    def test_the_commit_is_judged_not_the_working_file(self) -> None:
        repository = self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STRIPPED})
        (repository / "Cargo.lock").write_text(STANDALONE, encoding="utf-8", newline="\n")
        self.assertEqual(self.sweep(repository)[0], 1)

    def test_a_staged_change_is_not_part_of_the_commit_being_judged(self) -> None:
        sound = self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STANDALONE})
        (sound / "Cargo.lock").write_text(STRIPPED, encoding="utf-8", newline="\n")
        git(sound, "add", "Cargo.lock")
        self.assertEqual(self.sweep(sound)[0], 0)
        stripped = self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STRIPPED})
        (stripped / "Cargo.lock").write_text(STANDALONE, encoding="utf-8", newline="\n")
        git(stripped, "add", "Cargo.lock")
        self.assertEqual(self.sweep(stripped)[0], 1)

    def test_a_flattened_working_file_does_not_fail_a_sound_commit(self) -> None:
        repository = self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STANDALONE})
        (repository / "Cargo.lock").write_text(STRIPPED, encoding="utf-8", newline="\n")
        self.assertEqual(self.sweep(repository)[0], 0)

    def test_a_directory_that_is_not_a_repository_root_is_skipped_with_a_warning(self) -> None:
        """An uninitialized submodule is an empty directory inside its parent,
        and git run there answers for the parent."""
        parent = self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STRIPPED})
        (parent / "repos" / "absent").mkdir(parents=True)
        status, output = self.sweep(parent / "repos" / "absent")
        self.assertEqual(status, 0)
        self.assertIn("::warning::absent: not a repository root; skipped", output)
        self.assertNotIn("VIOLATION", output)

    def test_a_repository_git_cannot_read_is_a_failure(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="atlas-lock-sweep-")
        self.addCleanup(directory.cleanup)
        repository = Path(directory.name) / "unborn"
        repository.mkdir()
        git(repository, "init", "-q", "-b", "main")
        status, output = self.sweep(repository)
        self.assertEqual(status, 1)
        self.assertIn("unborn: cannot be read", output)

    def test_the_command_line_sweeps_the_repositories_it_names(self) -> None:
        repository = self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STRIPPED})
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--check-committed", str(repository)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn("LOCK FORM VIOLATION", completed.stdout)



class ExportedInputsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="atlas-lock-inputs-")))
        git(self.root, "init", "-q")

    def inputs(self, manifest: bytes, lock: bytes = b'version = 4\n') -> lockfile.GitTree:
        for name, content in (("Cargo.toml", manifest), ("Cargo.lock", lock), ("src/lib.rs", b"")):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        git(self.root, "add", "Cargo.toml", "Cargo.lock", "src/lib.rs")
        git(self.root, "commit", "-qm", "Inputs")
        return lockfile.GitTree(self.root, git(self.root, "rev-parse", "HEAD"))

    def check(self, source: lockfile.GitTree) -> tuple[int, str]:
        with (contextlib.redirect_stderr(stderr := io.StringIO()),
              contextlib.redirect_stdout(io.StringIO())):
            code = lockfile.check(self.root, source)
        return code, stderr.getvalue()

    def test_source_tree_rejects_changed_missing_and_link_inputs(self) -> None:
        source = self.inputs(b'[workspace]\n')
        manifest = self.root / "Cargo.toml"
        for changed in ('[workspace]\nresolver = "3"\n', '[workspace]\r', None):
            with self.subTest(changed=changed):
                if changed is None:
                    manifest.unlink()
                else:
                    manifest.write_text(changed, encoding="utf-8")
                code, error = self.check(source)
                self.assertEqual(code, 1)
                self.assertIn("exported lock inputs differ", error)
        manifest.write_text('[workspace]\n', encoding="utf-8")
        blob = git(self.root, "rev-parse", "HEAD:Cargo.toml")
        git(self.root, "update-index", "--cacheinfo", f"120000,{blob},Cargo.toml")
        git(self.root, "commit", "-qm", "Linked metadata")
        code, error = self.check(lockfile.GitTree(self.root, git(self.root, "rev-parse", "HEAD")))
        self.assertEqual(code, 1)
        self.assertIn("symbolic metadata input", error)

    def test_source_tree_accepts_checkout_line_endings(self) -> None:
        source = self.inputs(
            b'[package]\r\nname = "tool"\r\nversion = "0.1.0"\r\n',
            b'version = 4\r\n[[package]]\r\nname = "tool"\r\nversion = "0.1.0"\r\n',
        )
        for name in ("Cargo.toml", "Cargo.lock"):
            path = self.root / name
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
        self.assertEqual(self.check(source), (0, ""))

    def test_tree_source_requires_a_commit_object(self) -> None:
        self.inputs(b'[workspace]\n')
        tree = git(self.root, "rev-parse", "HEAD^{tree}")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--check", "--check-tree", str(self.root),
             "--tree-source", str(self.root), tree], capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("tree-source must be a commit object", result.stderr)

    def test_unrelated_path_bytes_do_not_change_lock_inputs(self) -> None:
        self.inputs(
            b'[package]\nname = "tool"\nversion = "0.1.0"\n',
            b'version = 4\n[[package]]\nname = "tool"\nversion = "0.1.0"\n',
        )
        blob = git(self.root, "rev-parse", "HEAD:Cargo.toml")
        subprocess.run(
            ["git", "-C", str(self.root), "update-index", "-z", "--index-info"],
            input=b"100644 " + blob.encode("ascii") + b"\tunrelated-\xff.bin\0",
            check=True, capture_output=True, timeout=60,
        )
        git(self.root, "commit", "-qm", "Unrelated binary path")
        source = lockfile.GitTree(self.root, git(self.root, "rev-parse", "HEAD"))
        self.assertEqual(self.check(source), (0, ""))

    def test_invalid_utf8_cannot_match_a_reencoded_export(self) -> None:
        source = self.inputs(
            b'[package]\nname = "tool"\nversion = "0.1.0"\n# invalid \xff\n',
            b'version = 4\n[[package]]\nname = "tool"\nversion = "0.1.0"\n',
        )
        original = lockfile.run_bounded(
            ["cargo", "metadata", "--format-version", "1", "--manifest-path",
             str(self.root / "Cargo.toml"), "--locked", "--no-deps"],
            cwd=self.root, env=dict(os.environ), deadline=60,
        )
        self.assertEqual(original.returncode, 101)
        self.assertIn("not valid utf-8", original.stderr.lower())
        manifest = self.root / "Cargo.toml"
        manifest.write_bytes(manifest.read_bytes().replace(b"\xff", b"\xef\xbf\xbd"))
        code, error = self.check(source)
        self.assertEqual(code, 1)
        self.assertIn("Cargo.toml: Cargo input is not valid UTF-8", error)
        manifest.write_bytes(manifest.read_bytes().replace(b"\xef\xbf\xbd", b"\xff"))
        with contextlib.redirect_stderr(stderr := io.StringIO()):
            self.assertEqual(lockfile.check(self.root), 1)
        self.assertIn("Cargo.toml: Cargo input is not valid UTF-8", stderr.getvalue())
        (self.root / "Cargo.lock").write_text('version = 4\n[[package]]\nname = "tool"\nversion = "0.1.0"\n# staged\n')
        git(self.root, "add", "Cargo.lock")
        staged = subprocess.run(
            [sys.executable, str(SCRIPT), "--check-staged"], cwd=self.root,
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(staged.returncode, 1, staged.stdout + staged.stderr)
        self.assertIn("Cargo.toml: Cargo input is not valid UTF-8", staged.stderr)


if __name__ == "__main__":
    unittest.main()
