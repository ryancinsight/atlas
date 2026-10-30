#!/usr/bin/env python3
"""Tests for atlas-lock-sweep.py's pure decisions.

The sweep's repository operations are exercised by running it; what unit
tests pin is every decision that could silently exclude or misplace a
consumer: which lock entries are first-party sources a sweep may move, which
of them are stale against the named targets, when an updated lock missed a
target, and what the branch, commit, and report look like. A wrong answer to
any of these is a consumer skipped without a row, or a lock committed at a
revision nobody named -- the failures the tool exists to prevent.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent.parent / "atlas-lock-sweep.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("atlas_lock_sweep", SCRIPT)
sweep = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
# dataclasses resolve `from __future__` annotations through sys.modules.
sys.modules[SPEC.name] = sweep
SPEC.loader.exec_module(sweep)

NL = chr(10)
OLD = "1" * 40
NEW = "2" * 40
MOVED = "3" * 40


def package(name: str, version: str, source: str | None) -> str:
    lines = ["[[package]]", f'name = "{name}"', f'version = "{version}"']
    if source is not None:
        lines.append(f'source = "{source}"')
    return NL.join(lines) + NL


def run_git(repository: Path, *arguments: str) -> str:
    command = ["git", "-C", str(repository), *arguments]
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()


def commit_repository(repository: Path, files: dict[str, str]) -> str:
    repository.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
    run_git(repository, "config", "user.email", "test@example.com")
    run_git(repository, "config", "user.name", "Test")
    for name, text in files.items():
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    run_git(repository, "add", *files)
    run_git(repository, "commit", "--quiet", "-m", "fixture")
    return run_git(repository, "rev-parse", "HEAD")


def commit_meta(repository: Path, modules: str, pins: dict[str, str | None]) -> str:
    base = commit_repository(repository, {".gitmodules": modules})
    for name, pin in pins.items():
        path = name if "/" in name else f"repos/{name}"
        entry = f"160000,{pin or base},{path}"
        run_git(repository, "update-index", "--add", "--cacheinfo", entry)
    if pins:
        run_git(repository, "commit", "--quiet", "-m", "meta fixture")
    return run_git(repository, "rev-parse", "HEAD")


def gitmodules(*names: str) -> str:
    return "".join(f'[submodule "repos/{name}"]\npath = repos/{name}\nurl = local-{name}\n' for name in names)


PROVIDER_MANIFEST = '[package]\nname = "provider"\nversion = "0.1.0"\n'
PROVIDER_LOCK = 'version = 4\n\n[[package]]\nname = "provider"\nversion = "0.1.0"\n'
CONSUMER_MANIFEST = (PROVIDER_MANIFEST.replace('name = "provider"', 'name = "consumer"') +
                     '[dependencies]\nprovider = { git = "https://github.com/ryancinsight/provider" }\n')


LOCK = NL.join(
    [
        "version = 4",
        "",
        package("consumer", "0.1.0", None),
        package("hermes-simd", "0.5.0", f"git+https://github.com/ryancinsight/hermes.git#{OLD}"),
        package("hermes-simd-core", "0.5.0", f"git+https://github.com/ryancinsight/hermes.git#{OLD}"),
        package("mnemosyne-memory", "0.8.0", f"git+https://github.com/ryancinsight/Mnemosyne#{NEW}"),
        package("mnemosyne-memory", "0.7.0", f"git+https://github.com/ryancinsight/Mnemosyne.git#{OLD}"),
        package("pinned", "1.0.0", f"git+https://github.com/ryancinsight/leto?rev=abc#{OLD}"),
        package("serde", "1.0.0", "registry+https://github.com/rust-lang/crates.io-index"),
        package("other", "0.1.0", f"git+https://github.com/someone/other#{OLD}"),
    ]
)


class UrlTests(unittest.TestCase):
    def test_provider_name_ignores_suffix_case_and_trailing_slash(self) -> None:
        for url in (
            "https://github.com/ryancinsight/Mnemosyne.GIT?branch=main",
            "https://github.com/ryancinsight/mnemosyne/",
        ):
            self.assertEqual(sweep.provider_repo_name(url), "mnemosyne")


class LockTests(unittest.TestCase):
    def test_only_unpinned_first_party_git_entries_are_read(self) -> None:
        names = [(p.name, p.version, p.url) for p in sweep.first_party_packages(LOCK)]
        self.assertEqual(
            names,
            [
                ("hermes-simd", "0.5.0", "https://github.com/ryancinsight/hermes.git"),
                ("hermes-simd-core", "0.5.0", "https://github.com/ryancinsight/hermes.git"),
                ("mnemosyne-memory", "0.8.0", "https://github.com/ryancinsight/Mnemosyne"),
                ("mnemosyne-memory", "0.7.0", "https://github.com/ryancinsight/Mnemosyne.git"),
            ],
        )

    def test_the_spec_names_the_source_so_two_spellings_stay_distinct(self) -> None:
        specs = {p.spec for p in sweep.first_party_packages(LOCK) if p.name == "mnemosyne-memory"}
        self.assertEqual(
            specs,
            {
                "git+https://github.com/ryancinsight/Mnemosyne#mnemosyne-memory@0.8.0",
                "git+https://github.com/ryancinsight/Mnemosyne.git#mnemosyne-memory@0.7.0",
            },
        )

    def test_query_pins_are_parsed_but_excluded_from_update_mode(self) -> None:
        source = f"git+https://GitHub.com/RyAnCiNsIgHt/Leto.GIT?tag=v1#{NEW}"
        lock = "version = 4\n" + package("pinned", "1.0.0", source)
        self.assertEqual(sweep.locked_packages(lock)[0].provider, "leto")
        self.assertEqual(sweep.first_party_packages(lock), [])

    def test_default_https_port_preserves_the_exact_identity_tuple(self) -> None:
        location = "https://GitHub.com:443/RyAnCiNsIgHt/Leto.GIT?branch=main"
        lock = "version = 4\n" + package("leto-ops", "0.9.0", f"git+{location}#{NEW}")
        identity = sweep.locked_packages(lock)[0]
        self.assertEqual(
            (identity.name, identity.version, identity.url, identity.rev, identity.provider),
            ("leto-ops", "0.9.0", location, NEW, "leto"),
        )

    def test_missing_source_is_a_valid_local_package(self) -> None:
        lock = "version = 4\n" + package("local", "1.0.0", None)
        self.assertEqual(sweep.locked_packages(lock), [])

    def test_malformed_first_party_identity_fails_closed(self) -> None:
        malformed = (
            "git+https://github.com/ryancinsight/hermes#not-a-commit",
            "git+https://github.com/ryancinsight/hermes",
        )
        for source in malformed:
            with self.subTest(source=source), self.assertRaisesRegex(
                ValueError, "unreadable first-party Git source identity"
            ):
                sweep.first_party_packages(
                    "version = 4\n" + package("hermes-simd", "0.5.0", source)
                )

    def test_first_party_path_shape_matrix(self) -> None:
        for path in ("/ryancinsight/leto", "/RyAnCiNsIgHt/Leto.GIT/"):
            source = f"git+https://github.com{path}#{OLD}"
            lock = "version = 4\n" + package("leto-ops", "0.9.0", source)
            with self.subTest(path=path):
                self.assertEqual(sweep.locked_packages(lock)[0].provider, "leto")

        malformed = (
            "/ryancinsight",
            "/ryancinsight//leto",
            "//ryancinsight/leto",
            "/ryancinsight/leto//",
            "/ryancinsight/leto/extra",
            "/ryancinsight/./leto",
            "/ryancinsight/../leto",
            "/%72yancinsight/leto",
            "/ryancinsight/Kwavers",
        )
        for path in malformed:
            source = f"git+https://github.com{path}#{OLD}"
            lock = "version = 4\n" + package("leto-ops", "0.9.0", source)
            with self.subTest(path=path), self.assertRaisesRegex(
                ValueError, "first-party Git source (?:identity|path)"
            ) as error:
                sweep.locked_packages(lock)
            self.assertNotIn(source, str(error.exception))

    def test_first_party_identity_rejects_raw_controls(self) -> None:
        locations = (
            r"ht\ntps://github.com/ryancinsight/leto",
            r"https://git\rhub.com/ryancinsight/leto",
            r"https://github.com/ryan\tcinsight/leto",
            r"https://github.com/ryancinsight/le\nto",
            r"\u0000https://github.com/ryancinsight/leto",
        )
        for location in locations:
            source = f"git+{location}#{OLD}"
            lock = "version = 4\n" + package("leto-ops", "0.9.0", source)
            with self.subTest(location=location), self.assertRaisesRegex(
                ValueError, "unreadable first-party Git source identity"
            ) as error:
                sweep.locked_packages(lock)
            self.assertNotIn(source, str(error.exception))

    def test_unsupported_first_party_transport_fails_without_echoing_source(self) -> None:
        for source in (
            f"git+ssh://git@github.com/ryancinsight/hermes#{OLD}",
            f"git+http://github.com/ryancinsight/hermes#{OLD}",
        ):
            lock = "version = 4\n" + package("hermes-simd", "0.5.0", source)
            with self.subTest(source=source), self.assertRaisesRegex(
                ValueError, "unsupported first-party Git source authority"
            ) as error:
                sweep.locked_packages(lock)
            self.assertNotIn(source, str(error.exception))

    def test_nondefault_or_malformed_first_party_port_fails_redacted(self) -> None:
        for port in ("444", "not-a-port"):
            source = f"git+https://github.com:{port}/ryancinsight/hermes#{OLD}"
            lock = "version = 4\n" + package("hermes-simd", "0.5.0", source)
            with self.subTest(port=port), self.assertRaisesRegex(
                ValueError, "first-party Git source authority"
            ) as error:
                sweep.locked_packages(lock)
            self.assertNotIn(source, str(error.exception))

    def test_similar_hosts_and_owners_are_not_first_party(self) -> None:
        lock = "version = 4\n" + "".join(
            (
                package("host", "cargo-owned", f"git+https://github.com.evil/ryancinsight/x#{OLD}"),
                package("owner", "cargo-owned", f"git+https://github.com/ryancinsight.evil/x#{OLD}"),
                package(
                    "path",
                    "cargo-owned",
                    f"git+https://example.invalid/github.com/ryancinsight/tool#{OLD}",
                ),
            )
        )
        self.assertEqual(sweep.locked_packages(lock), [])

    def test_third_party_source_payloads_are_opaque(self) -> None:
        lock = "version = 4\n" + "".join(
            (
                package("registry", "cargo-owned", "registry+https://exa mple.invalid/index"),
                package("other", "also-cargo-owned", f"git+https://example.invalid/other#{OLD}"),
            )
        )
        self.assertEqual(sweep.locked_packages(lock), [])

    def test_unknown_first_party_provider_is_preserved_for_caller_diagnosis(self) -> None:
        source = f"git+https://github.com/ryancinsight/not-registered#{OLD}"
        lock = "version = 4\n" + package("unknown", "1.0.0", source)
        self.assertEqual(sweep.locked_packages(lock)[0].provider, "not-registered")


class RevisionIdentityTests(unittest.TestCase):
    targets = {"hermes": (NEW, {"hermes-simd": frozenset({"0.5.0"})}), "mnemosyne": (NEW, {"mnemosyne-memory": frozenset({"0.8.0"})})}

    def finding(self, path: str, lock: str, fixture: bool = False):
        return sweep.revision_lock_findings("consumer", path, lock, self.targets, fixture)

    def test_drift_findings_preserve_path_revision_and_registration(self) -> None:
        lock = "version = 4\n" + package("hermes-simd", "0.5.0", f"git+https://github.com/ryancinsight/hermes#{OLD}")
        report, problems = self.finding("Cargo.lock", lock)
        expected = f"consumer/Cargo.lock: hermes-simd locks hermes@{OLD}; selected {NEW}"
        _, nested = self.finding("fuzz/Cargo.lock", lock)
        unknown = f"git+https://github.com/ryancinsight/not-registered#{NEW}"
        _, unregistered = self.finding("Cargo.lock", "version = 4\n" + package("unknown", "0.1.0", unknown))
        self.assertEqual((report, problems), ("consumer/Cargo.lock: measured 1 first-party package(s)", [expected]))
        self.assertTrue(nested[0].startswith("consumer/fuzz/Cargo.lock:"))
        self.assertIn("unknown registered first-party identity not-registered", unregistered[0])

    def test_queried_alias_resolves_without_disclosing_query(self) -> None:
        for query in (f"rev={OLD}", "branch=main", "tag=v0.8.0", "token=SYNTHETIC_SECRET"):
            with self.subTest(query=query):
                source = f"git+https://GitHub.com/RyAnCiNsIgHt/Mnemosyne.GIT?{query}#{OLD}"
                _, problems = self.finding(
                    "Cargo.lock", "version = 4\n" + package("mnemosyne-memory", "0.8.0", source)
                )
                expected = f"consumer/Cargo.lock: mnemosyne-memory locks mnemosyne@{OLD}; selected {NEW}"
                self.assertEqual((problems, query in repr(problems)), ([expected], False))

    def test_exact_source_is_reported_aligned(self) -> None:
        source = f"git+https://github.com/ryancinsight/hermes.git#{NEW}"
        report, problems = self.finding("Cargo.lock", "version = 4\n" + package("hermes-simd", "0.5.0", source))
        self.assertEqual((report, problems), ("consumer/Cargo.lock: aligned 1 first-party package(s)", []))

    def test_structural_path_fixture_with_git_identity_requires_unification(self) -> None:
        source = f"git+https://github.com/ryancinsight/hermes#{NEW}"
        lock = "version = 4\n" + package("hermes-simd", "0.5.0", source)
        manifest = ('[package]\nname = "fixture"\nversion = "0.1.0"\n[dependencies]\n'
                    'sibling = { path = "../../sibling" }\n')
        texts = {"Cargo.toml": manifest, "Cargo.lock": lock}
        standalone, exempt = sweep.lockfile.judge_locks(texts)
        self.assertEqual((standalone, exempt), ([], ["Cargo.lock"]))
        report, problems = self.finding("Cargo.lock", lock, "Cargo.lock" in exempt)
        self.assertEqual(report, "consumer/Cargo.lock: path fixture (1 first-party Git identities)")
        self.assertIn("path-unification required for hermes-simd", problems[0])

class RevisionRepositoryTests(unittest.TestCase):
    def check_meta(self, modules: str, pins: dict[str, str | None],
                   plain_members: tuple[str, ...] = ()) -> sweep.RevisionCheck:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit_meta(root, modules, pins)
            for member in plain_members:
                (root / "repos" / member).mkdir(parents=True)
            return sweep.check_revision(root, "HEAD")

    def fixture(self, root: Path, locked_version: str = "0.1.0", query: str = "",
                provider_files: dict[str, str] | None = None,
                package_name: str = "provider", root_lock: bool = True) -> tuple[str, str]:
        provider = root / "repos" / "provider"
        provider_files = provider_files or {"Cargo.toml": PROVIDER_MANIFEST, "Cargo.lock": PROVIDER_LOCK}
        provider_pin = commit_repository(provider, provider_files)
        consumer = root / "repos" / "consumer"
        aligned_source = f"git+https://github.com/ryancinsight/provider{query}#{provider_pin}"
        aligned = package(package_name, locked_version, aligned_source)
        drift_source = f"git+https://github.com/ryancinsight/provider#{OLD}"
        drift = package(package_name, "0.1.0", drift_source)
        consumer_files = {"Cargo.toml": CONSUMER_MANIFEST,
                          "Cargo.lock": PROVIDER_LOCK.replace('name = "provider"', 'name = "consumer"') + aligned,
                          "fuzz/Cargo.toml": CONSUMER_MANIFEST.replace("consumer", "consumer-fuzz"),
                          "fuzz/Cargo.lock": PROVIDER_LOCK.replace('name = "provider"', 'name = "consumer-fuzz"') + drift}
        if not root_lock: consumer_files.pop("Cargo.lock")
        consumer_pin = commit_repository(consumer, consumer_files)
        pins = {"provider": provider_pin, "consumer": consumer_pin}
        meta_pin = commit_meta(root, gitmodules("provider", "consumer"), pins)
        return provider_pin, meta_pin

    def checked_fixture(self, **arguments) -> tuple[str, str, sweep.RevisionCheck]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider, meta = self.fixture(root, **arguments)
            return provider, meta, sweep.check_revision(root, meta)

    def test_exact_revision_reads_every_nested_committed_lock(self) -> None:
        provider_pin, meta_pin, result = self.checked_fixture()
        _, _, rootless = self.checked_fixture(root_lock=False)
        self.assertEqual((result.revision, result.locks), (meta_pin, 3))
        self.assertIn("consumer/Cargo.lock: aligned 1 first-party package(s)", result.reports)
        self.assertEqual(result.problems, (f"consumer/fuzz/Cargo.lock: provider locks provider@{OLD}; selected {provider_pin}",))
        self.assertIn("no committed root Cargo.lock", "\n".join(rootless.problems))

    def test_exact_revision_checks_version_and_redacts_query(self) -> None:
        _, _, result = self.checked_fixture(locked_version="9.9.9", query="?token=SYNTHETIC_SECRET")
        evidence = repr((result.reports, result.problems))
        self.assertEqual(("locks version 9.9.9; selected provider manifests declare 0.1.0" in evidence,
                          "SYNTHETIC_SECRET" in evidence), (True, False))

    def test_provider_package_facts_fail_closed_without_dropping_duplicates(self) -> None:
        missing = {"Cargo.toml": '[workspace]\nmembers = ["crates/missing"]\n',
                   "Cargo.lock": "version = 4\n"}
        duplicates = {"Cargo.toml": '[workspace]\nmembers = ["one", "two"]\n',
                      "Cargo.lock": "version = 4\n",
                      "one/Cargo.toml": PROVIDER_MANIFEST.replace("provider", "shared"),
                      "two/Cargo.toml": PROVIDER_MANIFEST.replace("provider", "shared").replace("0.1.0", "9.9.9")}
        _, _, missing_result = self.checked_fixture(provider_files=missing)
        _, _, duplicate_result = self.checked_fixture(provider_files=duplicates, package_name="shared")
        _, _, manifest_result = self.checked_fixture(provider_files={"Cargo.lock": "version = 4\n"})
        self.assertIn("declares workspace member 'crates/missing'", repr(missing_result.problems))
        self.assertNotIn("locks version", repr(duplicate_result.problems))
        self.assertIn("workspace has no committed Cargo.toml", repr(manifest_result.problems))

    def test_unreadable_selected_member_object_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            run_git(root, "update-index", "--cacheinfo", f"160000,{'f' * 40},repos/provider")
            run_git(root, "commit", "--quiet", "-m", "missing provider object")
            result = sweep.check_revision(root, "HEAD")
        self.assertTrue(any("selected object cannot be read" in problem for problem in result.problems))

    def test_native_git_quoted_member_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit_meta(root, '[submodule "provider"]\npath = "repos/provider"\nurl = local\n', {})
            self.assertEqual(sweep.committed_member_names(root, "HEAD"), {"provider"})

    def test_invalid_member_topologies_fail_closed(self) -> None:
        cases = (
            (gitmodules("provider"), {"provider": None}, ("provider",), "no independent object repository"),
            (gitmodules(".."), {}, (), "unsafe registered member name '..'"),
            ("", {}, (), "no registered members"),
            (gitmodules("provider") + '[submodule "outside"]\npath = ../outside\nurl = local\n', {"provider": None}, (),
             "unsupported submodule path '../outside'"),
            ('[submodule "x"]\npath = repos/provider/../outside\nurl = local\n', {}, (), "unsupported submodule path 'repos/provider/../outside'"),
            ('[submodule "missing"]\nurl = local\n', {}, (), "has no path"),
            ('[submodule "missing"]\npath = repos/provider\n', {"provider": None}, (), "has no url"),
            ('[submodule "x"]\npath = repos/provider\npath = repos/other\nurl = local\n', {}, (), "has multiple paths"),
            (gitmodules("provider") + '[submodule "alias"]\npath = repos/provider\nurl = local\n', {}, (), "duplicate registered submodule path repos/provider"),
            ('[submodule "provider"\npath = repos/provider\n', {}, (), "cannot parse .gitmodules"),
            (gitmodules("provider"), {"provider": None, "aaa-extra": None}, (), "unregistered gitlink repos/aaa-extra"),
            (gitmodules("provider"), {"provider": None, "repos/nested/extra": None}, (), "unsupported gitlink repos/nested/extra"),
            (gitmodules("provider"), {"provider": None, "outside/provider": None}, (), "unsupported gitlink outside/provider"),
        )
        for modules, pins, plain_members, diagnostic in cases:
            with self.subTest(diagnostic=diagnostic):
                result = self.check_meta(modules, pins, plain_members)
            self.assertIn(diagnostic, result.problems[0])

class PlanTests(unittest.TestCase):
    def test_entries_behind_their_target_are_stale_and_entries_at_it_are_not(self) -> None:
        stale = sweep.stale_packages(LOCK, {"hermes": NEW, "mnemosyne": NEW})
        self.assertEqual(
            [(p.name, p.version) for p in stale],
            [("hermes-simd", "0.5.0"), ("hermes-simd-core", "0.5.0"), ("mnemosyne-memory", "0.7.0")],
        )

    def test_providers_that_are_not_targets_never_move(self) -> None:
        self.assertEqual(sweep.stale_packages(LOCK, {"leto": NEW, "other": NEW}), ())

    def test_a_lock_at_every_target_has_nothing_stale(self) -> None:
        self.assertEqual(sweep.stale_packages(LOCK, {"hermes": OLD}), ())

    def test_an_update_that_reached_every_target_has_no_misses(self) -> None:
        stale = sweep.stale_packages(LOCK, {"hermes": NEW})
        updated = LOCK.replace(f"hermes.git#{OLD}", f"hermes.git#{NEW}")
        self.assertEqual(sweep.unmet_targets(updated, stale, {"hermes": NEW}), [])

    def test_a_provider_head_past_the_named_merge_is_a_miss_for_every_entry(self) -> None:
        stale = sweep.stale_packages(LOCK, {"hermes": NEW})
        updated = LOCK.replace(f"hermes.git#{OLD}", f"hermes.git#{MOVED}")
        self.assertEqual(
            sweep.unmet_targets(updated, stale, {"hermes": NEW}),
            [
                "hermes-simd resolved 33333333, target hermes@22222222",
                "hermes-simd-core resolved 33333333, target hermes@22222222",
            ],
        )

    def test_each_source_past_its_target_is_pulled_back_once(self) -> None:
        stale = sweep.stale_packages(LOCK, {"hermes": NEW, "mnemosyne": NEW})
        updated = LOCK.replace(f"hermes.git#{OLD}", f"hermes.git#{MOVED}").replace(
            f"Mnemosyne.git#{OLD}", f"Mnemosyne.git#{NEW}"
        )
        self.assertEqual(
            sweep.pullbacks(updated, stale, {"hermes": NEW, "mnemosyne": NEW}),
            [("git+https://github.com/ryancinsight/hermes.git#hermes-simd@0.5.0", NEW)],
        )

    def test_sources_at_their_target_need_no_pullback(self) -> None:
        stale = sweep.stale_packages(LOCK, {"hermes": NEW})
        updated = LOCK.replace(f"hermes.git#{OLD}", f"hermes.git#{NEW}")
        self.assertEqual(sweep.pullbacks(updated, stale, {"hermes": NEW}), [])

    def test_one_spelling_left_behind_is_a_miss(self) -> None:
        stale = sweep.stale_packages(LOCK, {"mnemosyne": NEW})
        self.assertEqual(
            sweep.unmet_targets(LOCK, stale, {"mnemosyne": NEW}),
            ["mnemosyne-memory resolved 11111111, target mnemosyne@22222222"],
        )


class CommitTests(unittest.TestCase):
    def plan(self, targets: dict[str, str]):
        return sweep.Plan(Path("repos/leto"), OLD, sweep.stale_packages(LOCK, targets))

    def test_one_target_names_its_provider_and_revision(self) -> None:
        self.assertEqual(sweep.branch_name({"hermes": NEW}), "build/deps-hermes-22222222")

    def test_a_target_set_has_one_branch_independent_of_order(self) -> None:
        first = sweep.branch_name({"hermes": NEW, "mnemosyne": OLD})
        self.assertEqual(first, sweep.branch_name({"mnemosyne": OLD, "hermes": NEW}))
        self.assertTrue(first.startswith("build/deps-lock-sweep-"))
        self.assertNotEqual(first, sweep.branch_name({"hermes": NEW, "mnemosyne": MOVED}))

    def test_the_message_names_every_moved_provider_merge_and_the_item(self) -> None:
        targets = {"hermes": NEW, "mnemosyne": NEW, "leto": MOVED}
        message = sweep.commit_message(self.plan(targets), targets, "ITEM-1")
        lines = message.splitlines()
        self.assertEqual(lines[0], "build(deps): Advance first-party locks")
        self.assertLessEqual(len(lines[0]), 50)
        self.assertIn(f"Refs: hermes@{NEW}", lines)
        self.assertIn(f"Refs: mnemosyne@{NEW}", lines)
        self.assertNotIn(f"Refs: leto@{MOVED}", lines)
        self.assertIn("Item: ITEM-1", lines)
        self.assertTrue(lines[-1].startswith("Co-Authored-By: "))

    def test_a_single_provider_subject_names_it(self) -> None:
        message = sweep.commit_message(self.plan({"hermes": NEW}), {"hermes": NEW}, None)
        self.assertEqual(message.splitlines()[0], "build(deps): Update hermes to 22222222")
        self.assertNotIn("Item:", message)

    def test_line_endings_follow_the_committed_lock(self) -> None:
        self.assertEqual(sweep.with_line_endings_of(b"a\nb\n", b"x\r\ny\r\n"), b"x\ny\n")
        self.assertEqual(sweep.with_line_endings_of(b"a\r\nb\r\n", b"x\ny\n"), b"x\r\ny\r\n")


class ResumeTests(unittest.TestCase):
    targets = {"hermes": NEW}
    plan = sweep.Plan(Path("repos/leto"), OLD, sweep.stale_packages(LOCK, {"hermes": NEW}))
    url = "https://github.com/ryancinsight/leto/pull/7"

    def resume(self, remote: str, listed: str, open_prs: bool, opened=None):
        calls: list[list[str]] = []

        def gh(argv, **_options):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, listed, "")

        opener = opened or (lambda *_args: self.fail("no PR may be opened"))
        with mock.patch.object(sweep, "git", lambda *_args: remote), \
                mock.patch.object(sweep.subprocess, "run", gh), \
                mock.patch.object(sweep, "open_sweep_pull_request", opener):
            return sweep.resume(self.plan, self.targets, None, open_prs), calls

    def test_an_unpushed_branch_is_left_to_the_sweep(self) -> None:
        outcome, calls = self.resume("", "", True)
        self.assertIsNone(outcome)
        self.assertEqual(calls, [])

    def test_an_open_pr_on_the_branch_is_pending_and_nothing_is_redone(self) -> None:
        outcome, calls = self.resume(f"{NEW}\trefs/heads/build/deps-hermes-22222222", self.url + NL, True)
        self.assertEqual((outcome.action, outcome.ok), ("pending", True))
        self.assertIn(self.url, outcome.detail)
        self.assertEqual(calls[0][:5], ["gh", "pr", "list", "--head", "build/deps-hermes-22222222"])

    def test_a_pushed_branch_without_a_pr_gets_one(self) -> None:
        opened = sweep.Outcome("leto", "opened", self.url, True)
        outcome, _ = self.resume(f"{NEW}\trefs/heads/x", "", True, opened=lambda *_args: opened)
        self.assertEqual(outcome, opened)

    def test_a_dry_run_only_reports_the_missing_pr(self) -> None:
        outcome, _ = self.resume(f"{NEW}\trefs/heads/x", "", False)
        self.assertEqual((outcome.action, outcome.ok), ("would", True))


class ReportTests(unittest.TestCase):
    def test_report_lists_every_member_with_its_action(self) -> None:
        rows = [
            sweep.Outcome("leto", "opened", "https://github.com/ryancinsight/leto/pull/7", True),
            sweep.Outcome("kwavers", "failed", "cargo update: error: failed to select", False),
            sweep.Outcome("iris", "current", "every first-party source at its target", True),
        ]
        report = sweep.render_report({"hermes": NEW}, rows)
        self.assertEqual(report.splitlines()[0], "lock sweep -> hermes@22222222")
        for name in ("leto", "kwavers", "iris"):
            self.assertIn(name, report)
        self.assertEqual(len(report.splitlines()), 2 + len(rows))


if __name__ == "__main__":
    unittest.main()
