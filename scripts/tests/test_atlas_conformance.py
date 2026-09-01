#!/usr/bin/env python3
"""Tests for the Atlas conformance scanner."""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-conformance.py"
SPEC = importlib.util.spec_from_file_location("atlas_conformance", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
conformance = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = conformance
SPEC.loader.exec_module(conformance)


def _write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class AtlasConformanceTestCase(unittest.TestCase):
    def test_clean_revision_classifies_provider_dirt_after_clean_root(self) -> None:
        root_revision = "a" * 40
        provider_revision = "b" * 40
        calls: list[tuple[tuple[str, ...], Path]] = []

        def fake_git_output(*args: str, cwd: Path | None = None) -> str:
            if cwd is None:
                cwd = conformance.ROOT
            calls.append((args, cwd))
            if args == ("rev-parse", "--verify", "HEAD^{commit}"):
                return root_revision
            if args == ("rev-parse", "HEAD") and cwd == conformance.ROOT:
                return root_revision
            if args == ("status", "--porcelain", "--ignore-submodules=all"):
                return ""
            if args == ("rev-parse", "HEAD"):
                return provider_revision
            if args == ("status", "--porcelain"):
                return "M src/lib.rs"
            raise AssertionError(f"unexpected git query: {args!r} in {cwd}")

        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            (root / "repos" / "demo").mkdir(parents=True)
            with (
                patch.object(conformance, "ROOT", root),
                patch.object(conformance, "git_output", side_effect=fake_git_output),
                patch.object(
                    conformance,
                    "registered_member_names_at",
                    return_value={"demo"},
                ),
                patch.object(conformance, "gitlink_revision", return_value=provider_revision),
            ):
                with self.assertRaisesRegex(RuntimeError, "repos/demo worktree is dirty"):
                    conformance.check_clean_revision("HEAD")

            self.assertIn(
                (("status", "--porcelain", "--ignore-submodules=all"), root),
                calls,
            )

    def test_json_check_output_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            baseline_path = Path(temp) / "baseline.json"
            baseline_path.write_text(
                json.dumps({"demo": {"markers": 0, "print_dbg": 2}}),
                encoding="utf-8",
            )
            output = io.StringIO()
            with (
                patch.object(conformance, "BASELINE", baseline_path),
                patch.object(
                    conformance,
                    "scan_stack",
                    return_value={"demo": {"markers": 1, "print_dbg": 1}},
                ),
                patch.object(sys, "argv", [str(SCRIPT), "check", "--worktree", "--json"]),
                redirect_stdout(output),
            ):
                result = conformance.main()

        self.assertEqual(result, 1)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["results"], {"demo": {"markers": 1, "print_dbg": 1}})
        self.assertEqual(payload["regressions"], ["demo/markers: 0 -> 1"])
        self.assertEqual(payload["tightenings"], ["demo/print_dbg: 2 -> 1"])

    def test_render_baseline_reproduces_the_committed_file(self) -> None:
        """The generator must reproduce its own committed artifact byte for byte.

        Otherwise `generate` rewrites all ~1500 lines on every run, and a
        single laundered count is invisible in a diff that size -- which is
        how `e9c5821`'s `ritk/print_dbg: 12 -> 17` passed review. Before this
        was fixed the generator wrote `indent=1` against a file committed at
        `indent=2`.
        """
        baseline = SCRIPT.parent / "conformance-baseline.json"
        raw = baseline.read_text(encoding="utf-8")
        rendered = conformance.render_baseline(json.loads(raw))
        self.assertEqual(
            rendered,
            raw,
            "regenerating the committed baseline changed its formatting; "
            "`generate` is no longer idempotent",
        )

    def test_excess_worktrees_counts_registered_trees_over_the_bound(self) -> None:
        """The two-tree bound is a precondition, so something must check it.

        Nothing did, and one member reached five trees with 26 lane
        directories stack-wide before anyone measured.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            main = root / "main"
            main.mkdir()
            _write(main, "a.txt", "seed\n")
            ident = ["-c", "user.email=t@t", "-c", "user.name=t"]
            for argv in (
                ["init", "-q", "-b", "main"],
                [*ident, "add", "a.txt"],
                [*ident, "commit", "-q", "-m", "seed"],
            ):
                subprocess.run(["git", "-C", str(main), *argv], check=True)

            # Main tree alone is within the bound.
            self.assertEqual(conformance.count_excess_worktrees(main), 0)

            # A single lane is still within it.
            subprocess.run(
                ["git", "-C", str(main), "worktree", "add", "-q",
                 str(root / "lane1"), "-b", "lane1"],
                check=True,
            )
            self.assertEqual(conformance.count_excess_worktrees(main), 0)

            # A second lane exceeds it.
            subprocess.run(
                ["git", "-C", str(main), "worktree", "add", "-q",
                 str(root / "lane2"), "-b", "lane2"],
                check=True,
            )
            self.assertEqual(conformance.count_excess_worktrees(main), 1)

    def test_excess_worktrees_is_zero_outside_a_repository(self) -> None:
        """A non-repository cannot substantiate a violation, so it reports none."""
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            self.assertEqual(conformance.count_excess_worktrees(Path(temp)), 0)

    def test_crate_level_allow_is_counted_separately(self) -> None:
        """The blanket form must be measured, and not by `allow_sites`.

        `allow_sites` counts the substring `#[allow(`, which `#![allow(`
        does not contain -- the `!` breaks the match. Until this class
        existed, the one suppression form the lint floor singles out as
        never acceptable was the one form nothing counted.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(
                root,
                "src/lib.rs",
                "#![allow(clippy::pedantic)]\n#[allow(dead_code)]\npub fn f() {}\n",
            )
            counts = conformance.scan_repo(root)
            self.assertEqual(counts["crate_level_allows"], 1)
            self.assertEqual(counts["allow_sites"], 1)

    def test_benches_are_executable_for_print_scan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(
                root,
                "src/lib.rs",
                "pub fn prod() { println!(\"prod\"); }\n",
            )
            _write(
                root,
                "benches/measure.rs",
                "fn bench() { println!(\"bench\"); }\n",
            )

            counts = conformance.scan_repo(root)

        self.assertEqual(counts["print_dbg"], 1)

    def test_binary_support_modules_are_executable_for_print_scan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(root, "task/Cargo.toml", "[package]\nname = 'task'\n")
            _write(root, "task/src/main.rs", "mod report;\n")
            _write(
                root,
                "task/src/report.rs",
                "pub fn emit() { println!(\"task output\"); }\n",
            )

            counts = conformance.scan_repo(root)

        self.assertEqual(counts["print_dbg"], 0)

    def test_build_rs_cargo_protocol_is_exempt_from_print_scan(self) -> None:
        # `println!("cargo:...")` is the canonical Cargo build-script
        # protocol (rerun-if-changed, rustc-cfg, rustc-link-arg).  It is
        # required, not debug debt — the scanner must exempt it inside
        # build.rs files while still counting non-cargo writes there.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[package]\nname = 'fixture'\n")
            _write(root, "build.rs",
                'println!("cargo:rerun-if-changed=build.rs");\n'
                'println!("cargo:rustc-cfg=nightly");\n'
                'println!("debug: building");\n'
            )
            _write(root, "src/lib.rs", "")

            counts = conformance.scan_repo(root)

        # The two cargo: writes are exempt; the one debug println! counts.
        self.assertEqual(counts["print_dbg"], 1)

    def test_build_rs_cargo_protocol_exempt_does_not_leak_to_lib(self) -> None:
        # The exemption must be scoped to build.rs only: a `println!`
        # in a library source file that happens to contain "cargo:"
        # in its string argument is NOT exempt.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[package]\nname = 'fixture'\n")
            _write(
                root,
                "src/lib.rs",
                'pub fn info() { println!("cargo: info"); }\n',
            )

            counts = conformance.scan_repo(root)

        self.assertEqual(counts["print_dbg"], 1)

    def test_include_sources_are_not_orphans(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[package]\nname = 'fixture'\n")
            _write(
                root,
                "src/lib.rs",
                'include!("included.rs");\ninclude!("concat_root.rs");\n',
            )
            _write(root, "src/included.rs", "pub const VALUE: usize = 1;\n")
            _write(root, "src/concat.rs", "pub const OTHER: usize = 2;\n")
            _write(
                root,
                "src/concat_root.rs",
                'include!(concat!(\n'
                '    env!("CARGO_MANIFEST_DIR"),\n'
                '    "/src/concat.rs"\n'
                '));\n',
            )

            self.assertEqual(conformance.count_orphan_modules(root), 0)

    def test_path_attr_with_intervening_doc_comment_is_not_orphan(self) -> None:
        # Coeus wires its feature-gated CUDA driver stub as
        # `#[path = "driver_stub.rs"]` followed by a doc comment before
        # `pub mod driver;`. The `#[path]` attribute still applies across the
        # doc comment, so the stub is compiled (not an orphan); PATH_ATTR must
        # not require `#[path]` to sit immediately before the `mod`.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[package]\nname = 'fixture'\n")
            _write(
                root,
                "src/lib.rs",
                '#[cfg(not(feature = "cuda"))]\n'
                '#[path = "driver_stub.rs"]\n'
                "/// Stub CUDA driver surface used when the `cuda` feature is disabled.\n"
                "pub mod driver;\n",
            )
            _write(root, "src/driver_stub.rs", "pub const STUB: usize = 1;\n")

            self.assertEqual(conformance.count_orphan_modules(root), 0)

    def test_path_redirected_cfg_test_sidecar_is_not_production(self) -> None:
        # moirai-iter declares its async-iter sidecar from a subdirectory:
        # src/async_iter/mod.rs gates
        # `#[path = "../async_iter_tests.rs"] mod async_iter_tests;`. The
        # declaring module is not the sidecar's parent, so only a #[path]-
        # aware lookup sees the gate; without it the sidecar's SeqCst uses
        # counted as production debt.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[package]\nname = 'fixture'\n")
            _write(root, "src/lib.rs", "pub mod async_iter;\n")
            _write(
                root,
                "src/async_iter/mod.rs",
                "#[cfg(test)]\n"
                "#[path = \"../async_iter_tests.rs\"]\n"
                "mod async_iter_tests;\n",
            )
            _write(
                root,
                "src/async_iter_tests.rs",
                "use std::sync::atomic::{AtomicUsize, Ordering};\n"
                "static WAKES: AtomicUsize = AtomicUsize::new(0);\n"
                "pub fn wakes() -> usize { WAKES.load(Ordering::SeqCst) }\n",
            )
            sidecar = root / "src" / "async_iter_tests.rs"

            self.assertTrue(conformance.declared_cfg_test(sidecar))
            self.assertEqual(conformance.scan_repo(root)["seqcst_production"], 0)

    def test_ungated_redirect_keeps_sidecar_in_production(self) -> None:
        # The redirect alone proves nothing about testness: drop the gate
        # and the same file must count again.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[package]\nname = 'fixture'\n")
            _write(root, "src/lib.rs", "pub mod async_iter;\n")
            _write(
                root,
                "src/async_iter/mod.rs",
                "#[path = \"../async_iter_tests.rs\"]\nmod async_iter_tests;\n",
            )
            _write(
                root,
                "src/async_iter_tests.rs",
                "use std::sync::atomic::{AtomicUsize, Ordering};\n"
                "static WAKES: AtomicUsize = AtomicUsize::new(0);\n"
                "pub fn wakes() -> usize { WAKES.load(Ordering::SeqCst) }\n",
            )

            self.assertFalse(
                conformance.declared_cfg_test(root / "src" / "async_iter_tests.rs")
            )
            self.assertEqual(conformance.scan_repo(root)["seqcst_production"], 1)

    def test_path_match_catches_stem_renamed_sidecar(self) -> None:
        # A #[path] target whose stem differs from the declared module name
        # matches by resolved path, not by stem.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[package]\nname = 'fixture'\n")
            _write(root, "src/lib.rs", "pub mod async_iter;\n")
            _write(
                root,
                "src/async_iter/mod.rs",
                "#[cfg(test)]\n#[path = \"../ai_wake_tests.rs\"]\n"
                "mod async_iter_tests;\n",
            )
            _write(root, "src/ai_wake_tests.rs", "pub const N: usize = 1;\n")

            self.assertTrue(
                conformance.declared_cfg_test(root / "src" / "ai_wake_tests.rs")
            )

    def test_pages_target_output_is_not_a_cargo_fork(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(root, "target/book/athena/index.html", "<html>\n")

            counts = conformance.scan_repo(root)

        self.assertEqual(counts["target_forks"], 0)

    def test_cargo_target_markers_and_suffixes_are_counted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(root, "target/debug/.fingerprint", "")
            _write(root, "target_isolated/release/.fingerprint", "")

            counts = conformance.scan_repo(root)

        self.assertEqual(counts["target_forks"], 2)

    def test_repeated_scan_is_stable(self) -> None:
        # The per-scan read caches must not leak state between scans.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(root, "crates/a/Cargo.toml", "[package]\nname = 'a'\n")
            _write(root, "crates/a/src/lib.rs", "pub fn f() { println!(\"x\"); }\n")
            _write(root, "crates/a/src/extra.rs", "pub const X: usize = 1;\n")

            first = conformance.scan_repo(root)
            second = conformance.scan_repo(root)

        self.assertEqual(first, second)
        self.assertEqual(conformance._file_text_cache(), {})
        self.assertEqual(conformance._cfg_test_decl_cache(), {})

    def test_nested_workspace_lints_table_satisfies_inheritance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(
                root,
                "Cargo.toml",
                "[workspace]\n"
                "[workspace.lints.rust]\n"
                "missing_docs = \"deny\"\n",
            )

            counts = conformance.scan_repo(root)

        self.assertEqual(counts["workspace_lints_missing"], 0)

    def test_reusable_workflow_caller_inherits_called_job_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(
                root,
                ".github/workflows/book-pages.yml",
                "jobs:\n"
                "  book:\n"
                "    uses: example/atlas/.github/workflows/book-pages.yml@"
                "0123456789012345678901234567890123456789\n",
            )

            counts = conformance.scan_repo(root)

        self.assertEqual(counts["workflow_missing_timeout"], 0)

    def test_mixed_reusable_workflow_keeps_local_timeout_requirement(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(
                root,
                ".github/workflows/mixed.yml",
                "jobs:\n"
                "  book:\n"
                "    uses: example/atlas/.github/workflows/book-pages.yml@"
                "0123456789012345678901234567890123456789\n"
                "  local:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: true\n",
            )

            counts = conformance.scan_repo(root)

        self.assertEqual(counts["workflow_missing_timeout"], 1)

    def test_git_blame_ignore_revisions_is_root_configuration(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(root, ".git-blame-ignore-revs", "# formatting commit\n")

            counts = conformance.scan_repo(root)

            self.assertEqual(counts["root_sprawl"], 0)
            _write(root, "session-report.txt", "unfiled output\n")
            counts = conformance.scan_repo(root)

        self.assertEqual(counts["root_sprawl"], 1)

    def test_cargo_manifests_prune_caches(self) -> None:
        # rglob would crawl target/ and book/; the pruned walker must skip them.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(
                root,
                "target/debug/decoy/Cargo.toml",
                "[package]\nname = 'decoy'\n",
            )
            _write(
                root,
                "book/custom/Cargo.toml",
                "[package]\nname = 'bookdecoy'\n",
            )
            _write(
                root,
                ".pytest_cache/decoy/Cargo.toml",
                "[package]\nname = 'pytestdecoy'\n",
            )

            manifests = sorted(
                p.relative_to(root).as_posix()
                for p in conformance.cargo_manifests(root)
            )

        self.assertEqual(manifests, ["Cargo.toml"])

    def test_executable_source_dirs_prune_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(root, "crates/cli/Cargo.toml", "[package]\nname = 'cli'\n")
            _write(root, "crates/cli/src/main.rs", "fn main() {}\n")
            _write(root, "target/decoy/Cargo.toml", "[package]\nname = 'decoy'\n")
            _write(root, "target/decoy/src/main.rs", "fn main() {}\n")

            dirs = conformance.executable_source_dirs(root)

        self.assertEqual(len(dirs), 1)

    def test_stack_scan_preserves_registered_member_results(self) -> None:
        """Parallel provider scans retain deterministic member attribution."""
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(
                root,
                ".gitmodules",
                "[submodule \"alpha\"]\n\tpath = repos/alpha\n"
                "[submodule \"beta\"]\n\tpath = repos/beta\n",
            )
            _write(root, "repos/alpha/.git", "gitdir: modules/alpha\n")
            _write(root, "repos/beta/.git", "gitdir: modules/beta\n")
            _write(root, "repos/alpha/src/lib.rs", "pub fn alpha() {}\n")
            _write(root, "repos/beta/src/lib.rs", "pub fn beta() {}\n")

            results = conformance.scan_stack(root)

        self.assertEqual(results["alpha"]["oversized_files"], 0)
        self.assertEqual(results["beta"]["oversized_files"], 0)
        self.assertEqual(set(results), {"<meta>", "alpha", "beta"})

    def test_stack_scan_rejects_unmaterialized_provider(self) -> None:
        """An empty gitlink directory cannot masquerade as a clean provider."""
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(
                root,
                ".gitmodules",
                "[submodule \"alpha\"]\n\tpath = repos/alpha\n",
            )
            (root / "repos/alpha").mkdir(parents=True)

            with self.assertRaisesRegex(
                RuntimeError,
                r"provider checkouts are not materialized: alpha",
            ):
                conformance.scan_stack(root)

    def test_generate_refuses_to_raise_a_count(self) -> None:
        """`generate` must not launder a regression into the baseline.

        A ratchet whose baseline can be rewritten upward is not a ratchet:
        any failing `check` could be cleared by re-running `generate`, which
        satisfies the gate's form while inverting its purpose. This happened
        once in practice (atlas `e9c5821` lifted ritk/print_dbg 12 -> 17), so
        the guard is pinned by a test rather than by convention.
        """
        previous = {"demo": {"print_dbg": 1}}
        current = {"demo": {"print_dbg": 4}}
        raises = conformance.baseline_raises(previous, current)
        self.assertEqual(raises, [("demo", "print_dbg", 1, 4)])

    def test_generate_allows_a_lowered_or_equal_count(self) -> None:
        previous = {"demo": {"print_dbg": 4, "markers": 2}}
        current = {"demo": {"print_dbg": 1, "markers": 2}}
        self.assertEqual(conformance.baseline_raises(previous, current), [])

    def test_a_newly_measured_repo_is_not_a_raise(self) -> None:
        """A repo or class absent from the baseline has nothing to exceed."""
        previous = {"demo": {"print_dbg": 1}}
        current = {"demo": {"print_dbg": 1, "markers": 7}, "fresh": {"print_dbg": 9}}
        self.assertEqual(conformance.baseline_raises(previous, current), [])


if __name__ == "__main__":
    unittest.main()
