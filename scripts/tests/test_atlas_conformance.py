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

    def test_unconditional_cancel_on_a_push_trigger_is_counted(self) -> None:
        # Each merge cancelled the previous merge's pending verification; the
        # conforming form keys default-branch runs per commit and cancels only PRs.
        offending = (
            "name: ci\non:\n  push:\n    branches: [main]\n  pull_request:\n"
            "concurrency:\n  group: ci-${{ github.ref }}\n  cancel-in-progress: true\n"
            "jobs:\n  a:\n    runs-on: ubuntu-latest\n    steps: []\n"
        )
        conforming = offending.replace(
            "  group: ci-${{ github.ref }}\n  cancel-in-progress: true\n",
            "  group: ci-${{ github.event_name == 'pull_request' && github.ref || github.sha }}\n"
            "  cancel-in-progress: ${{ github.event_name == 'pull_request' }}\n",
        )
        pull_request_only = offending.replace("  push:\n    branches: [main]\n", "")
        self.assertTrue(conformance.cancels_default_branch_runs(offending))
        self.assertFalse(conformance.cancels_default_branch_runs(conforming))
        self.assertFalse(conformance.cancels_default_branch_runs(pull_request_only))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".github/workflows/ci.yml", offending)
            _write(root, ".github/workflows/pr-only.yml", pull_request_only)
            counts: dict[str, int] = {name: 0 for name in conformance.CLASSES}
            conformance.scan_workflows(root, counts)
            self.assertEqual(counts["default_branch_cancel_in_progress"], 1)

    def test_toolchain_requests_the_committed_pin_outranks_are_counted(self) -> None:
        # Seven members' MSRV jobs installed an older toolchain under a committed
        # 1.97.0 pin and compiled with 1.97.0; RUSTUP_TOOLCHAIN exempts a job.
        workflow = (
            "name: ci\non: [push]\njobs:\n"
            "  msrv:\n    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: dtolnay/rust-toolchain@4cda84d5c5c54efe2404f9d843567869ab1699d4\n"
            "        with:\n          toolchain: 1.95.0\n"
            "  msrv-fixed:\n    runs-on: ubuntu-latest\n    env:\n      RUSTUP_TOOLCHAIN: 1.95.0\n    steps:\n"
            "      - uses: dtolnay/rust-toolchain@4cda84d5c5c54efe2404f9d843567869ab1699d4\n"
            "        with:\n          toolchain: 1.95.0\n"
            "  verify:\n    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: dtolnay/rust-toolchain@4cda84d5c5c54efe2404f9d843567869ab1699d4\n"
            "        with:\n          toolchain: \"1.97\"\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".github/workflows/ci.yml", workflow)
            _write(root, "rust-toolchain.toml", '[toolchain]\nchannel = "1.97.0"\n')
            counts: dict[str, int] = {name: 0 for name in conformance.CLASSES}
            conformance.scan_workflows(root, counts)
            self.assertEqual(counts["toolchain_request_overridden"], 1)
            # Without a committed pin nothing outranks the install step.
            (root / "rust-toolchain.toml").unlink()
            counts = {name: 0 for name in conformance.CLASSES}
            conformance.scan_workflows(root, counts)
            self.assertEqual(counts["toolchain_request_overridden"], 0)
        self.assertTrue(conformance.same_release("1.95", "1.95.2"))
        self.assertTrue(conformance.same_release("1.97.0", "1.97.0-x86_64-pc-windows-msvc"))
        self.assertFalse(conformance.same_release("1.95.0", "1.97.0"))

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

    def test_dup_key_workflow_is_malformed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(
                root,
                ".github/workflows/release.yml",
                "name: first\n"
                "on:\n"
                "  workflow_call:\n"
                "name: second\n"
                "jobs:\n"
                "  run:\n"
                "    runs-on: ubuntu-latest\n",
            )

            counts = conformance.scan_repo(root)

        self.assertEqual(counts["workflow_malformed_yaml"], 1)

    def test_valid_workflow_is_not_malformed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(
                root,
                ".github/workflows/release.yml",
                "name: release\n"
                "permissions:\n"
                "  contents: read\n"
                "on:\n"
                "  push:\n"
                "    tags: ['*']\n"
                "jobs:\n"
                "  run:\n"
                "    runs-on: ubuntu-latest\n"
                "    timeout-minutes: 10\n"
                "    steps:\n"
                "      - run: true\n",
            )

            counts = conformance.scan_repo(root)

        self.assertEqual(counts["workflow_malformed_yaml"], 0)

    def test_missing_pyyaml_does_not_count_as_malformed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(
                root,
                ".github/workflows/release.yml",
                "name: release\nname: duplicate\njobs: {}\n",
            )
            with patch.object(conformance, "_yaml", None):
                counts = conformance.scan_repo(root)

        self.assertEqual(counts["workflow_malformed_yaml"], 0)

    def _large_call_body(self, with_inline: bool) -> int:
        """Build a LaneKernel impl whose call body is 120 lines."""
        attr = "#[inline(always)]\n" if with_inline else ""
        body = "\n".join(f"        let v{i} = value + {i};" for i in range(115))
        source = (
            "impl<T> LaneKernel<T> for BigKernel<T> {\n"
            "    type Output = ();\n"
            f"    {attr}fn call<A: SimdArch>(self, _simd: Simd<T, A>) {{\n"
            "        let value = 0;\n"
            f"{body}\n"
            "    }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(root, "src/lib.rs", source)
            counts = conformance.scan_repo(root)
        return counts["lane_kernel_uninlined"]

    def test_large_uninlined_lane_kernel_is_flagged(self) -> None:
        self.assertEqual(self._large_call_body(with_inline=False), 1)

    def test_large_inlined_lane_kernel_is_clean(self) -> None:
        self.assertEqual(self._large_call_body(with_inline=True), 0)

    def test_small_uninlined_lane_kernel_is_clean(self) -> None:
        source = (
            "impl<T> LaneKernel<T> for SmallKernel<T> {\n"
            "    type Output = ();\n"
            "    fn call<A: SimdArch>(self, _simd: Simd<T, A>) {\n"
            "        let _ = 0;\n"
            "    }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(root, "src/lib.rs", source)
            counts = conformance.scan_repo(root)
        self.assertEqual(counts["lane_kernel_uninlined"], 0)

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


class DetectorPrecisionTests(unittest.TestCase):
    """Prose that begins with a keyword is not commented-out code; absence
    is not an existence-only assertion; compound cfg predicates gate test
    regions item by item; comment lines may sit between stacked attributes."""

    def test_keyword_led_prose_is_not_commented_out_code(self) -> None:
        prose = [
            "        // for all k1 in 0..n1 and all j in 0..n2 = all N indices).",
            "        // for `p in 0..ROWS/2` and `g = 2q + mh` with `q in 0..4,",
            "    // asserted where they are built.",
            "        // for groups == 2, require the triple writes to scratch",
            "        // for this: an ISA minimum returns one operand or the other",
            "            // let a NaN in the first chunk poison its accumulator",
            "        // let `vbsl`-based masked ops splice operands bit-by-bit.",
            "        // assertion above upholds its bounds precondition.",
            "        // if either is NaN, so a NaN in `v` could replace a real minimum",
            "        // use Align to govern both.",
            "        // implicit widening keeps the accumulator wide.",
            "        // return the newest artifact per crate",
        ]
        for line in prose:
            self.assertIsNone(conformance.COMMENTED_CODE.match(line), line)

    def test_code_shaped_comments_are_commented_out_code(self) -> None:
        code = [
            "    // let x = 5;",
            "    // let mut total: f64 = 0.0;",
            "    // for i in 0..n {",
            "    // for (a, b) in pairs {",
            "    // assert_eq!(a, b);",
            "    // assert!(x > 0);",
            "    // fn helper(x: u32) -> u32 {",
            "    // use std::io;",
            "    // use crate::ops::{Add, Mul};",
            "    // pub fn old_entry() {}",
            "    // impl Foo for Bar {",
            "    // match value {",
            "    // if let Some(v) = maybe {",
            "    // while depth > 0 {",
            "    // struct Legacy {",
            "    // return Ok(());",
        ]
        for line in code:
            self.assertIsNotNone(conformance.COMMENTED_CODE.match(line), line)

    def test_absence_is_not_an_existence_only_assertion(self) -> None:
        self.assertIsNone(conformance.EXISTENCE_ONLY.search("assert!(plan.base128.is_none());"))
        for existence in ("assert!(r.is_ok());", 'assert!(v.is_some(), "present");', "assert!(r.is_err());"):
            self.assertIsNotNone(conformance.EXISTENCE_ONLY.search(existence), existence)

    def test_cfg_predicates_name_test_outside_not(self) -> None:
        gated = conformance.cfg_predicate_is_test_gated
        self.assertTrue(gated("test"))
        self.assertTrue(gated('all(test, windows, target_arch = "x86_64")'))
        self.assertTrue(gated("all(test, not(miri))"))
        self.assertTrue(gated("any(test, all(test, windows))"))
        self.assertTrue(gated("all(unix, any(test, all(test, miri)))"))
        self.assertFalse(gated('any(test, feature = "std")'), "production whenever the feature is on")
        self.assertFalse(gated("not(test)"))
        self.assertFalse(gated("not(all(test, windows))"))
        self.assertFalse(gated('feature = "test-utils"'))
        self.assertFalse(gated("all(unix, not(miri))"))
        self.assertFalse(gated(""))

    def test_comments_between_stacked_attributes_keep_the_sidecar_gated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(
                root,
                "src/kernel/mod.rs",
                "#[cfg(test)]\n"
                "// The footprint instrument installs a global allocator that miri\n"
                "// rejects, so the instrument stays out of miri runs.\n"
                "#[cfg(not(miri))]\n"
                "mod retained_footprint;\n"
                "pub fn kernel() {}\n",
            )
            _write(root, "src/kernel/retained_footprint.rs", 'fn report() { println!("probe"); }\n')
            self.assertTrue(conformance.declared_cfg_test(root / "src/kernel/retained_footprint.rs"))
            self.assertEqual(conformance.scan_repo(root)["print_dbg"], 0)

    def test_test_regions_are_scoped_to_their_items(self) -> None:
        source = (
            "fn production() {}\n"
            '#[cfg(all(test, windows, target_arch = "x86_64"))]\n'
            "macro_rules! sect {\n"
            "    ($label:literal, $body:block) => {{\n"
            "        static SECTIONS: std::sync::LazyLock<bool> =\n"
            '            std::sync::LazyLock::new(|| std::env::var_os("S").is_some());\n'
            '        if *SECTIONS { eprintln!("RSECT {}", $label); }\n'
            "    }};\n"
            "}\n"
            '#[cfg(not(all(test, windows, target_arch = "x86_64")))]\n'
            "macro_rules! sect { ($label:literal, $body:block) => { $body }; }\n"
            'fn after() { println!("library output"); }\n'
            "#[cfg(test)]\n"
            "mod tests;\n"
            "fn trailing() { let v: [u8; 3] = [0; 3]; }\n"
            "#[cfg(test)]\n"
            "mod inline_tests {\n"
            "    #[test]\n"
            "    fn t() { assert!(x.is_ok()); }\n"
            "}\n"
        )
        production, tests = conformance.split_test_region(source)
        self.assertIn("RSECT", tests)
        self.assertNotIn("RSECT", production)
        self.assertIn("mod tests;", tests)
        self.assertIn("mod inline_tests", tests)
        self.assertIn("is_ok()", tests)
        for kept in ("fn production()", "$body };", "library output", "fn trailing()"):
            self.assertIn(kept, production, kept)
            self.assertNotIn(kept, tests, kept)
        self.assertEqual(len(conformance.PRINT_DBG.findall(production)), 1)


class MaterializedMemberTests(unittest.TestCase):
    """A member checkout that is dirty or behind its recorded gitlink is
    scanned from an archived snapshot of that gitlink, never from its live
    state; a clean checkout at the gitlink is scanned in place."""

    def _git(self, repo: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, encoding="utf-8",
            errors="replace", check=True,
        ).stdout.strip()

    def _provider(self, temp: Path) -> tuple[Path, str, str]:
        provider = temp / "repos" / "alpha"
        provider.mkdir(parents=True)
        self._git(provider, "init", "-q", "-b", "main")
        self._git(provider, "config", "user.email", "t@example.invalid")
        self._git(provider, "config", "user.name", "t")
        _write(provider, "src/lib.rs", "pub fn alpha() {}\n")
        self._git(provider, "add", ".")
        self._git(provider, "commit", "-q", "-m", "one")
        first = self._git(provider, "rev-parse", "HEAD")
        _write(provider, "src/lib.rs", 'pub fn alpha() { println!("debt"); }\n')
        self._git(provider, "commit", "-q", "-am", "two")
        second = self._git(provider, "rev-parse", "HEAD")
        return provider, first, second

    def test_clean_checkout_at_the_gitlink_scans_in_place(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            provider, _, second = self._provider(Path(temp))
            content, live = conformance.materialize_member(provider, second, Path(temp) / "scratch")
            self.assertEqual((content, live), (provider, provider))

    def test_behind_or_dirty_checkout_scans_the_recorded_snapshot(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            provider, first, second = self._provider(Path(temp))
            self._git(provider, "checkout", "-q", first)
            _write(provider, "src/lib.rs", "pub fn alpha() { dbg!(1); dbg!(2); }\n")
            scratch = Path(temp) / "scratch"
            content, live = conformance.materialize_member(provider, second, scratch)
            self.assertEqual(live, provider)
            self.assertEqual(content, scratch / "alpha")
            self.assertEqual(
                (content / "src/lib.rs").read_text(encoding="utf-8"),
                'pub fn alpha() { println!("debt"); }\n',
            )
            counts = conformance.scan_repo(content, live_repo=provider)
            self.assertEqual(counts["print_dbg"], 1, "the recorded revision's one print, not the live tree's two dbg!")

    def test_a_gitlink_absent_from_the_object_store_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            provider, first, _ = self._provider(Path(temp))
            self._git(provider, "checkout", "-q", first)
            with self.assertRaisesRegex(RuntimeError, "not in the provider's object store"):
                conformance.materialize_member(provider, "0" * 40, Path(temp) / "scratch")


if __name__ == "__main__":
    unittest.main()
