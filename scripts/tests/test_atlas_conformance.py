#!/usr/bin/env python3
"""Tests for the Atlas conformance scanner."""

from __future__ import annotations

import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
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
    def test_untracked_git_timeout_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".git").mkdir()
            with patch.object(
                conformance,
                "execute_git",
                side_effect=conformance.GitProcessError("timed out", timed_out=True),
            ):
                with self.assertRaisesRegex(RuntimeError, "cannot list untracked paths"):
                    conformance.untracked_root_names(repo)

    def test_untracked_git_failure_fails_closed(self) -> None:
        failure = subprocess.CompletedProcess(
            ["git"], 128, stdout=b"", stderr=b"fatal: failed"
        )
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".git").mkdir()
            with patch.object(conformance, "execute_git", return_value=failure):
                with self.assertRaisesRegex(RuntimeError, "failed"):
                    conformance.untracked_root_names(repo)

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

    def test_untracked_root_files_are_host_state_not_repository_debt(self) -> None:
        """A scratch file at the root is this checkout's, not the repo's.

        `count_root_sprawl` walks the live directory, so a peer's `.mine.patch`
        counted exactly like a committed stray file -- and because `generate`
        refuses while any raise stands, one scratch file blocked recording
        every tightening the stack had earned.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-root-sprawl-") as temp:
            repo = Path(temp)
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            (repo / "README.md").write_text("sanctioned\n", encoding="utf-8")
            (repo / "stray-committed.txt").write_text("debt\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "-c", "user.email=t@example.com",
                 "-c", "user.name=t", "commit", "-q", "-m", "seed"],
                check=True,
            )
            (repo / ".mine.patch").write_text("scratch\n", encoding="utf-8")

            carried, untracked = conformance.count_root_sprawl(repo)

        self.assertEqual(carried, 1, "the committed stray file is repository debt")
        self.assertEqual(untracked, 1, "the scratch file is measured, as host state")
        self.assertIn("root_sprawl_untracked", conformance.HOST_OBSERVED_CLASSES)

    def test_ignored_root_files_are_host_state_not_repository_debt(self) -> None:
        """A gitignored root file is no more the repository's than an unignored one.

        `f64w.pdb` -- ignored by `*.pdb` -- raised atlas `root_sprawl` 0 -> 1:
        the untracked listing used `--exclude-standard` alone, so ignored files
        fell into neither bucket and were counted as carried.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-root-ignored-") as temp:
            repo = Path(temp)
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            (repo / "README.md").write_text("sanctioned\n", encoding="utf-8")
            (repo / ".gitignore").write_text("*.pdb\ntarget/\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "-c", "user.email=t@example.com",
                 "-c", "user.name=t", "commit", "-q", "-m", "seed"],
                check=True,
            )
            (repo / "scratch.pdb").write_text("symbols\n", encoding="utf-8")
            (repo / "target").mkdir()
            (repo / "target" / "artifact.rlib").write_text("x\n", encoding="utf-8")

            carried, untracked = conformance.count_root_sprawl(repo)

        self.assertEqual(carried, 0, "an ignored file is not repository content")
        self.assertEqual(untracked, 1, "measured as host state; an ignored directory is not a root file")

    def test_generate_records_zero_for_host_observed_classes(self) -> None:
        """A generated baseline never carries this machine's state.

        Those classes read the live checkout, so generating from a developer's
        tree would record one lane or one forked cache as the stack's
        permitted debt -- and the ratchet would then defend it.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            baseline_path = Path(temp) / "baseline.json"
            measured = {
                "demo": {"markers": 2, "target_forks": 3, "excess_worktrees": 1}
            }
            with (
                patch.object(conformance, "BASELINE", baseline_path),
                # `generate` reports the baseline path relative to the root.
                patch.object(conformance, "ROOT", Path(temp)),
                patch.object(conformance, "scan_stack", return_value=measured),
                # `--json` renders the written baseline; the plain form calls
                # `report`, which indexes every class this fixture omits.
                patch.object(sys, "argv", [str(SCRIPT), "generate", "--json"]),
                redirect_stdout(io.StringIO()),
            ):
                result = conformance.main()
            written = json.loads(baseline_path.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertEqual(written["demo"]["markers"], 2, "repository debt is recorded")
        self.assertEqual(written["demo"]["target_forks"], 0)
        self.assertEqual(written["demo"]["excess_worktrees"], 0)

    def test_host_state_is_reported_apart_from_repository_debt(self) -> None:
        """A forked cache is not a regression in any repository.

        `target_forks` and `excess_worktrees` read the live checkout, so a CI
        runner measures zero for both by construction and every committed
        baseline records zero. Reporting them beside the revision-measured
        classes made 1.2 GB of stray `target/` read as a ratchet violation
        while the hosted gate that never sees them reported green. They still
        fail the run -- host debt is debt -- under their own heading.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            baseline_path = Path(temp) / "baseline.json"
            baseline_path.write_text(
                json.dumps({"demo": {"markers": 0, "target_forks": 0}}),
                encoding="utf-8",
            )
            output = io.StringIO()
            with (
                patch.object(conformance, "BASELINE", baseline_path),
                patch.object(
                    conformance,
                    "scan_stack",
                    return_value={"demo": {"markers": 0, "target_forks": 1}},
                ),
                patch.object(sys, "argv", [str(SCRIPT), "check", "--json"]),
                redirect_stdout(output),
            ):
                result = conformance.main()

        payload = json.loads(output.getvalue())
        self.assertEqual(payload["regressions"], [])
        self.assertEqual(payload["host_regressions"], ["demo/target_forks: 0 -> 1"])
        self.assertEqual(result, 1, "host debt still fails the run it is measured on")

    def test_report_renders_counts_that_do_not_match_the_class_list(self) -> None:
        """A report-only count must not kill the report.

        `<meta>` folds in the artifact budget, which emits
        `items_over_budget` -- reported, never gated, and so deliberately
        absent from `CLASSES`. The unguarded accumulator raised
        `KeyError: 'items_over_budget'` on every `report` run once that
        key existed, taking out the whole non-`--json` path. The opposite
        shape is just as real: a partial fixture omits keys a full scan
        produces, which is why the generate test above had to pass
        `--json` to avoid this function.
        """
        results = {
            "demo": {"markers": 2, "print_dbg": 1},
            "<meta>": {"target_forks": 1, "items_over_budget": 9},
        }
        output = io.StringIO()
        with redirect_stdout(output):
            conformance.report(results)
        text = output.getvalue()

        self.assertIn("markers", text, "a class with a count is rendered")
        self.assertIn("demo=2", text, "its worst offender is named")
        self.assertNotIn(
            "items_over_budget", text,
            "a report-only count is not a ratcheted class",
        )
        for line in text.splitlines()[1:]:
            klass = line.split()[0]
            self.assertIn(klass, conformance.CLASSES)

    def test_git_ignored_files_are_not_repository_debt(self) -> None:
        """An ignored path is this machine's, not the repository's.

        A live scan walks the filesystem, so a member's ignored directory
        was scanned as if it were its own source. apollo ignores
        `/artifacts/`, which held four identical copies of a probe script,
        and their eight `println!` calls were reported as library print
        debt on a repository whose committed tree contains none -- a raise
        no apollo commit could clear and a CI checkout would never see,
        exactly like `target_forks` and `root_sprawl_untracked`.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-ignored-") as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            _write(root, ".gitignore", "/artifacts/\n")
            _write(root, "Cargo.toml",
                   "[package]\nname = \"demo\"\n")
            _write(root, "src/lib.rs", "pub fn demo() {}\n")
            _write(root, "artifacts/probe.rs",
                   'fn main() { println!("probe"); }\n')

            scanned = {p.name for p, _ in conformance.rust_files(root)}

        self.assertIn("lib.rs", scanned, "tracked source is still scanned")
        self.assertNotIn(
            "probe.rs", scanned,
            "an ignored path is host state, not repository debt",
        )

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

    def test_pull_request_target_use_counts_triggers_not_text(self) -> None:
        # metis PR #418 filtered artifacts by the Actions API field
        # `.workflow_run.head_repository_id` to reject fork-uploaded markers;
        # it uses neither trigger, but the text-match detector counted it
        # anyway. The class exists for the pwn-request trigger risk, so only
        # a workflow's actual `on:` trigger set may count it.
        pull_request_target = "name: ci\non: pull_request_target\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps: []\n"
        workflow_run_list = "name: ci\non: [push, workflow_run]\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps: []\n"
        workflow_run_map = (
            "name: ci\non:\n  workflow_run:\n    workflows: [x]\n"
            "jobs:\n  a:\n    runs-on: ubuntu-latest\n    steps: []\n"
        )
        false_positive = (
            "name: ci\non:\n  pull_request:\n  push:\n"
            "jobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n"
            "      # not pull_request_target: rejects fork-uploaded markers\n"
            "      - run: |\n"
            "          jq '.workflow_run.head_repository_id' event.json\n"
        )
        self.assertEqual(conformance.workflow_triggers(pull_request_target), {"pull_request_target"})
        self.assertEqual(conformance.workflow_triggers(workflow_run_list), {"push", "workflow_run"})
        self.assertEqual(conformance.workflow_triggers(workflow_run_map), {"workflow_run"})
        self.assertEqual(conformance.workflow_triggers(false_positive), {"pull_request", "push"})
        self.assertIsNone(conformance.workflow_triggers("name: ci\non: [\n"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".github/workflows/a.yml", pull_request_target)
            _write(root, ".github/workflows/b.yml", workflow_run_list)
            _write(root, ".github/workflows/c.yml", workflow_run_map)
            _write(root, ".github/workflows/d.yml", false_positive)
            counts: dict[str, int] = {name: 0 for name in conformance.CLASSES}
            conformance.scan_workflows(root, counts)
            self.assertEqual(counts["pull_request_target_use"], 3)
        # A file PyYAML cannot parse falls back to the conservative text match,
        # consistent with workflow_yaml_is_valid treating it as unverifiable.
        with patch.object(conformance, "_yaml_loader", return_value=None):
            self.assertIsNone(conformance.workflow_triggers(false_positive))
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _write(root, ".github/workflows/d.yml", false_positive)
                counts = {name: 0 for name in conformance.CLASSES}
                conformance.scan_workflows(root, counts)
                self.assertEqual(counts["pull_request_target_use"], 1)

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

    def test_doctest_println_is_not_library_output(self) -> None:
        # Doc-comment bodies are doctests: a `println!` inside `//!`/`///`
        # is example prose (consus-zarr's ignored chunk-key loop), not
        # production debug output — the same reason `unwrap_production`
        # strips doc comments before counting.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(
                root,
                "src/lib.rs",
                "//! ```ignore\n"
                "//! for key in keys {\n"
                '//!     println!("chunk key: {key}");\n'
                "//! }\n"
                "//! ```\n"
                "pub fn keys() {}\n",
            )

            counts = conformance.scan_repo(root)

        self.assertEqual(counts["print_dbg"], 0)

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

    def test_directory_module_gated_by_cfg_test_is_not_production(self) -> None:
        # apollo declares its test-only codelet from a subdirectory:
        # components/mod.rs gates `#[cfg(test)] mod codelet;`, whose file is
        # codelet/mod.rs. The entry stem is `mod`, so only a lookup through
        # the parent directory's *name* as the module stem sees the gate;
        # without it the codelet's 100+ line `LaneKernel::call` counted as a
        # production `lane_kernel_uninlined` site.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[package]\nname = 'fixture'\n")
            _write(root, "src/lib.rs", "pub mod kernel;\n")
            _write(root, "src/kernel/mod.rs", "pub mod components;\n")
            _write(
                root,
                "src/kernel/components/mod.rs",
                "#[cfg(test)]\nmod codelet;\n",
            )
            _write(
                root,
                "src/kernel/components/codelet/mod.rs",
                "use std::sync::atomic::{AtomicUsize, Ordering};\n"
                "static WAKES: AtomicUsize = AtomicUsize::new(0);\n"
                "pub fn wakes() -> usize { WAKES.load(Ordering::SeqCst) }\n",
            )
            codelet = root / "src" / "kernel" / "components" / "codelet" / "mod.rs"

            self.assertTrue(conformance.declared_cfg_test(codelet))
            self.assertEqual(conformance.scan_repo(root)["seqcst_production"], 0)

    def test_a_gate_reaches_modules_below_the_gated_directory(self) -> None:
        # A cfg(test) gate covers everything under the module it names, but
        # only that module's own file carries a declaration a lookup can see.
        # Splitting one gated file into a directory of modules therefore
        # reclassified all of them as production: apollo's pinned probe turned
        # 25 measurement `println!`s into print debt without a line of it
        # changing.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[package]\nname = 'fixture'\n")
            _write(root, "src/lib.rs", "mod base;\n")
            _write(root, "src/base/mod.rs", "#[cfg(test)]\nmod probe;\n")
            _write(root, "src/base/probe/mod.rs", "mod measurement;\n")
            _write(
                root,
                "src/base/probe/measurement.rs",
                "fn report(value: u64) {\n"
                "    println!(\"cycles {value}\");\n"
                "}\n",
            )
            child = root / "src" / "base" / "probe" / "measurement.rs"

            self.assertTrue(
                conformance.declared_cfg_test(child),
                "a module below a gated directory is test code too",
            )
            self.assertEqual(conformance.scan_repo(root)["print_dbg"], 0)

    def test_the_gate_does_not_reach_across_an_ungated_module(self) -> None:
        # Inheritance follows declarations, not directories: a module that no
        # gated declaration covers keeps counting as production.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[package]\nname = 'fixture'\n")
            _write(root, "src/lib.rs", "mod base;\n")
            _write(root, "src/base/mod.rs", "mod probe;\n")
            _write(root, "src/base/probe/mod.rs", "mod measurement;\n")
            _write(
                root,
                "src/base/probe/measurement.rs",
                "fn report(value: u64) {\n"
                "    println!(\"cycles {value}\");\n"
                "}\n",
            )
            child = root / "src" / "base" / "probe" / "measurement.rs"

            self.assertFalse(conformance.declared_cfg_test(child))
            self.assertEqual(conformance.scan_repo(root)["print_dbg"], 1)

    def test_ungated_directory_module_stays_in_production(self) -> None:
        # The gate, not the shape, decides: a directory module declared
        # without cfg(test) must still count as production code.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[package]\nname = 'fixture'\n")
            _write(root, "src/lib.rs", "pub mod kernel;\n")
            _write(root, "src/kernel/mod.rs", "pub mod components;\n")
            _write(root, "src/kernel/components/mod.rs", "mod codelet;\n")
            _write(
                root,
                "src/kernel/components/codelet/mod.rs",
                "use std::sync::atomic::{AtomicUsize, Ordering};\n"
                "static WAKES: AtomicUsize = AtomicUsize::new(0);\n"
                "pub fn wakes() -> usize { WAKES.load(Ordering::SeqCst) }\n",
            )

            self.assertFalse(
                conformance.declared_cfg_test(
                    root / "src" / "kernel" / "components" / "codelet" / "mod.rs"
                )
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

    def test_tests_suffix_directory_counts_as_test_path(self) -> None:
        # `src/lib_tests/cfft_tests.rs` hangs off a cfg-gated `mod lib_tests;`
        # whose gate the scanner cannot see without building a module graph;
        # the `<name>_tests` convention classifies such files the way `tests/`
        # classifies its own, so their println!s stay test output.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[package]\nname = 'fixture'\n")
            _write(root, "src/lib.rs", "#[cfg(test)]\nmod lib_tests;\n")
            _write(
                root,
                "src/lib_tests/cfft_tests.rs",
                "#[test]\nfn t() { println!(\"benchmark\"); }\n",
            )
            _write(root, "src/plain.rs", "pub fn p() { println!(\"x\"); }\n")

            counts = conformance.scan_repo(root)

        self.assertEqual(counts["print_dbg"], 1)
        self.assertTrue(conformance._is_testish_path_part("lib_tests"))

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

    def test_file_without_lane_kernel_literal_is_clean(self) -> None:
        # The substring pre-filter in `count_lane_kernel_uninlined` must not
        # change the count: a file with neither literal reports 0 the same way
        # the full regex pass would.
        source = "pub fn double(value: u64) -> u64 {\n    value + value\n}\n"
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

    def test_build_rs_is_root_configuration(self) -> None:
        # A build script is cargo-required root layout like the manifest:
        # themis and melinoe emit `rustc-check-cfg` for `nightly_tls_active`
        # from it, so it must not count as unfiled sprawl.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(root, "build.rs", "fn main() {}\n")

            counts = conformance.scan_repo(root)

        self.assertEqual(counts["root_sprawl"], 0)

    def test_application_manifests_are_root_configuration_for_owners(self) -> None:
        # Application manifests are the explicit payload inventory for the
        # Metis and RITK executables and installers, so a repository-level
        # metis.json is configuration rather than an unfiled report for either
        # owning repository.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            for name in ("metis", "ritk"):
                root = Path(temp) / name
                _write(root, "Cargo.toml", "[workspace]\n")
                _write(root, "metis.json", "{}\n")

                counts = conformance.scan_repo(root)
                self.assertEqual(counts["root_sprawl"], 0)

    def test_application_manifest_is_sprawl_for_other_repositories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp) / "apollo"
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(root, "metis.json", "{}\n")

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

    def test_walkers_prune_reusable_workflow_overlay(self) -> None:
        # The member workflow checks out Atlas at `_atlas` beside the member
        # checkout. Scanning that overlay would import Atlas's own debt into
        # the member baseline.
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "Cargo.toml", "[workspace]\n")
            _write(root, "src/lib.rs", "pub fn f() {}\n")
            _write(root, "_atlas/Cargo.toml", "[workspace]\n")
            _write(root, "_atlas/src/lib.rs", "pub fn atlas() {}\n")

            manifests = sorted(
                p.relative_to(root).as_posix()
                for p in conformance.cargo_manifests(root)
            )
            sources = sorted(
                p.relative_to(root).as_posix()
                for p, _ in conformance.rust_files(root)
            )

        self.assertEqual(manifests, ["Cargo.toml"])
        self.assertEqual(sources, ["src/lib.rs"])

    def test_walkers_skip_unreadable_directories(self) -> None:
        """A directory denying reads contributes nothing, never an abort.

        Stale build residue can carry cross-account ACLs; the fleet scan
        measures trees, it does not audit their permissions.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(root, "pkg/Cargo.toml", "[package]\nname = 'pkg'\n")
            _write(root, "pkg/src/lib.rs", "pub fn f() {}\n")
            _write(root, "locked/Cargo.toml", "[package]\nname = 'locked'\n")
            locked = root / "locked"
            real_iterdir = Path.iterdir

            def gated(self: Path):
                if self == locked:
                    raise PermissionError(13, "denied")
                return real_iterdir(self)

            with patch.object(Path, "iterdir", gated):
                manifests = sorted(
                    p.relative_to(root).as_posix()
                    for p in conformance.cargo_manifests(root)
                )
                sources = sorted(
                    p.relative_to(root).as_posix()
                    for p, _ in conformance.rust_files(root)
                )

        self.assertEqual(manifests, ["pkg/Cargo.toml"])
        self.assertEqual(sources, ["pkg/src/lib.rs"])

    def test_type_suffixed_clone_exempts_conversions(self) -> None:
        """Conversion-lattice methods name their target type, not a clone.

        `F16::to_f32` and `Bf16::to_f32` cannot consolidate into one generic
        entry point (the receivers differ); `process_f32` can.
        """
        for name in ("to_f32", "from_f32", "from_f64", "to_u8"):
            self.assertFalse(conformance._is_type_suffixed_clone(name))
        for name in ("process_f32", "widen_f16", "fill_f64", "next_f32"):
            self.assertTrue(conformance._is_type_suffixed_clone(name))

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

    def test_stack_scan_maps_closure_member_edges(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(
                root,
                ".gitmodules",
                "[submodule \"kwavers\"]\n\tpath = repos/kwavers\n"
                "[submodule \"hyperion\"]\n\tpath = repos/hyperion\n",
            )
            for member in ("kwavers", "hyperion"):
                _write(root, f"repos/{member}/.git", "gitdir: modules/member\n")
            _write(
                root,
                "repos/kwavers/Cargo.toml",
                "[package]\nname = 'kwavers-physics'\n"
                "[dependencies]\nhyperion = { path = '../../hyperion' }\n",
            )
            _write(root, "repos/kwavers/src/lib.rs", "pub fn kwavers() {}\n")
            _write(
                root,
                "repos/hyperion/Cargo.toml",
                "[package]\nname = 'hyperion'\n",
            )
            _write(root, "repos/hyperion/src/lib.rs", "pub fn hyperion() {}\n")
            observed: list[str] = []
            classifier = conformance._classify_balance_member_edge
            self.assertIsNotNone(classifier)

            def record_finding(edge, member_for_package):
                finding = classifier(edge, member_for_package)
                observed.append(finding.kind)
                return finding

            with (
                patch.object(
                    conformance,
                    "_MEMBER_BALANCE_DOMAINS",
                    frozenset({"kwavers"}),
                ),
                patch.object(
                    conformance,
                    "_CLOSURE_DOMAINS",
                    frozenset({"hyperion"}),
                ),
                patch.object(
                    conformance,
                    "_classify_balance_member_edge",
                    side_effect=record_finding,
                ),
            ):
                results = conformance.scan_stack(root)

        self.assertEqual(results["kwavers"]["balance_domain_edges"], 0)
        self.assertIn("closure_provider", observed)

    def test_stack_scan_counts_distinct_gate_versions(self) -> None:
        """`member_gate_versions` converges to 1 as the rollout lands.

        Distinct `.githooks/pre-push` contents across members plus the
        owned source: alpha matches the source, beta carries a fork, gamma
        has no hook at all, and delta carries the source with CRLF endings
        (a clean Windows checkout reads CRLF where an archive reads LF) --
        still three versions, one rollout.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            _write(
                root,
                ".gitmodules",
                "[submodule \"alpha\"]\n\tpath = repos/alpha\n"
                "[submodule \"beta\"]\n\tpath = repos/beta\n"
                "[submodule \"gamma\"]\n\tpath = repos/gamma\n"
                "[submodule \"delta\"]\n\tpath = repos/delta\n",
            )
            _write(root, "scripts/git-hooks/pre-push", "owned\n")
            for member in ("alpha", "beta", "gamma", "delta"):
                _write(root, f"repos/{member}/.git", "gitdir: elsewhere\n")
            _write(root, "repos/alpha/.githooks/pre-push", "owned\n")
            _write(root, "repos/beta/.githooks/pre-push", "forked\n")
            delta_hook = root / "repos/delta/.githooks/pre-push"
            delta_hook.parent.mkdir(parents=True, exist_ok=True)
            delta_hook.write_bytes(b"owned\r\n")

            results = conformance.scan_stack(root)

        self.assertEqual(results["<meta>"]["member_gate_versions"], 3)

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

    def test_stack_scan_skips_registered_member_without_gitlink(self) -> None:
        """A promotion mid-flight must not blind the fleet scan.

        When `.gitmodules` names a member but no revision records its
        gitlink yet (the checkout is a standalone clone, exactly like
        `repos/ares` during promotion), the recorded-revision scan skips
        that member with a warning instead of aborting every other
        member's measurement.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            ident = ["-c", "user.email=t@t", "-c", "user.name=t"]
            _write(
                root,
                ".gitmodules",
                "[submodule \"demo\"]\n\tpath = repos/demo\n"
                "\turl = https://example.com/demo.git\n",
            )
            for argv in (
                ["init", "-q", "-b", "main"],
                [*ident, "add", ".gitmodules"],
                [*ident, "commit", "-q", "-m", "register demo"],
            ):
                subprocess.run(["git", "-C", str(root), *argv], check=True)
            demo = root / "repos" / "demo"
            demo.mkdir(parents=True)
            for argv in (
                ["init", "-q", "-b", "main"],
                [*ident, "commit", "-q", "--allow-empty", "-m", "seed"],
            ):
                subprocess.run(["git", "-C", str(demo), *argv], check=True)
            _write(demo, "src/lib.rs", "pub fn demo() {}\n")
            rev = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()

            err = io.StringIO()
            with redirect_stderr(err):
                results = conformance.scan_stack(root, rev)

            self.assertNotIn("demo", results)
            self.assertIn("demo", err.getvalue())

    def test_stack_scan_skips_unlinked_member_before_materialization_gate(
        self,
    ) -> None:
        """A clean checkout has no directory for an unlinked member at all.

        The materialization gate aborts on a missing checkout, so the
        recorded-revision scan must drop never-linked members first —
        otherwise one promotion mid-flight fails the gate on machines
        without the standalone clone. The linked member still scans.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            ident = ["-c", "user.email=t@t", "-c", "user.name=t"]
            # `demo` is registered but has neither a gitlink nor even a
            # directory — the clean-checkout shape of a promotion
            # mid-flight, where the materialization gate would abort.
            provider = root / "provider"
            provider.mkdir(parents=True)
            for argv in (
                ["init", "-q", "-b", "main"],
                [*ident, "commit", "-q", "--allow-empty", "-m", "seed"],
            ):
                subprocess.run(["git", "-C", str(provider), *argv], check=True)
            _write(
                root,
                ".gitmodules",
                "[submodule \"linked\"]\n\tpath = repos/linked\n"
                "\turl = https://example.com/linked.git\n"
                "[submodule \"demo\"]\n\tpath = repos/demo\n"
                "\turl = https://example.com/demo.git\n",
            )
            linked_sha = subprocess.run(
                ["git", "-C", str(provider), "rev-parse", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            # A materialized checkout of the linked member, as a submodule
            # clone would provide: clean and exactly at the recorded pin,
            # so the scan reads it live with no archiving involved.
            subprocess.run(
                ["git", "clone", "-q", str(provider),
                 str(root / "repos" / "linked")],
                check=True,
            )
            for argv in (
                ["init", "-q", "-b", "main"],
                [*ident, "add", ".gitmodules"],
                ["update-index", "--add", "--cacheinfo",
                 f"160000,{linked_sha},repos/linked"],
                [*ident, "commit", "-q", "-m", "register"],
            ):
                subprocess.run(["git", "-C", str(root), *argv], check=True)
            rev = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()

            err = io.StringIO()
            with redirect_stderr(err):
                results = conformance.scan_stack(root, rev)

            self.assertIn("linked", results)
            self.assertNotIn("demo", results)
            self.assertIn("demo", err.getvalue())

    def test_recorded_revision_scan_measures_the_meta_row_at_the_revision(
        self,
    ) -> None:
        """The meta row reads the revision, not the checkout holding it.

        A shared checkout routinely holds an older or dirty branch; the meta
        row once read it live, so `generate --revision origin/main` reported
        a phantom raise measured from the wrong tree.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            root = Path(temp)
            ident = ["-c", "user.email=t@t", "-c", "user.name=t"]
            _write(root, ".gitmodules", "")
            _write(root, ".gitattributes", "* text=auto eol=lf\n")
            _write(
                root,
                "backlog.md",
                '<a id="ATLAS-A-001"></a>\n'
                "## ATLAS-A-001 - ready - todo\n"
                "- priority: correctness\n",
            )
            for argv in (
                ["init", "-q", "-b", "main"],
                [*ident, "add", "-A"],
                [*ident, "commit", "-q", "-m", "clean board"],
            ):
                subprocess.run(["git", "-C", str(root), *argv], check=True)
            rev = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            # The live tree drifts from the revision: the policy file is
            # gone and the board gains an off-set item.
            (root / ".gitattributes").unlink()
            with (root / "backlog.md").open("a", encoding="utf-8") as board:
                board.write("## ATLAS-A-002 - finished - done\n")

            at_revision = conformance.scan_stack(root, rev)["<meta>"]
            live = conformance.scan_stack(root)["<meta>"]

            self.assertEqual(at_revision["gitattributes_missing"], 0)
            self.assertEqual(at_revision["board_items_outside_status_set"], 0)
            self.assertEqual(live["gitattributes_missing"], 1)
            self.assertEqual(live["board_items_outside_status_set"], 1)

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

    def test_a_single_member_scan_judges_the_recorded_gitlink(self) -> None:
        """`check --repo` under a pre-push gate: the root commit records the
        member's second revision while the checkout sits dirty on the first,
        and the scan must count the recorded revision's debt, not the tree's."""
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            stack = Path(temp)
            provider, first, second = self._provider(stack)
            self._git(provider, "checkout", "-q", first)
            _write(provider, "src/lib.rs", "pub fn alpha() { dbg!(1); dbg!(2); }\n")
            self._git(stack, "init", "-q", "-b", "main")
            self._git(stack, "config", "user.email", "t@example.invalid")
            self._git(stack, "config", "user.name", "t")
            self._git(stack, "update-index", "--add", "--cacheinfo", f"160000,{second},repos/alpha")
            tree = self._git(stack, "write-tree")
            root_commit = self._git(stack, "commit-tree", tree, "-m", "pin alpha")

            recorded = conformance.scan_member(stack, "alpha", root_commit)
            live = conformance.scan_member(stack, "alpha", None)

            self.assertEqual(recorded["print_dbg"], 1, "the pinned revision's one println!")
            self.assertEqual(live["print_dbg"], 2, "the live tree's two dbg!")

    def test_a_gitlink_absent_from_the_object_store_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as temp:
            provider, first, _ = self._provider(Path(temp))
            self._git(provider, "checkout", "-q", first)
            with self.assertRaisesRegex(RuntimeError, "not in the provider's object store"):
                conformance.materialize_member(provider, "0" * 40, Path(temp) / "scratch")

# Manifest fixtures for SubstrateContractTests.
RUNTIME_RAYON = "[dependencies]\nrayon = \"1.8\""
TARGET_NALGEBRA = "[target.'cfg(unix)'.dependencies]\nnalgebra = \"0.33\""
DEV_RAYON = "[dev-dependencies]\nrayon = \"1.8\""
BUILD_NDARRAY = "[build-dependencies]\nndarray = \"0.16\""
WORKSPACE_RAYON = "[workspace.dependencies]\nrayon = \"1.8\""
HARNESS = (
    "[package]\nname = \"x-benchmarks\"\nversion = \"0.1.0\"\npublish = false\n\n"
    "[dependencies]\nrayon = \"1.8\"\n\n"
    "[[bench]]\nname = \"industry_comparison\""
)
PUBLISHED_WITH_BENCH = (
    "[package]\nname = \"x\"\nversion = \"0.1.0\"\n\n"
    "[dependencies]\nrayon = \"1.8\"\n\n"
    "[[bench]]\nname = \"b\""
)
UNPUBLISHED_NO_BENCH = (
    "[package]\nname = \"x\"\nversion = \"0.1.0\"\npublish = false\n\n"
    "[dependencies]\nrayon = \"1.8\""
)
MALFORMED = "[dependencies\nrayon ="
FIRST_PARTY = "[dependencies]\nleto = \"0.4\"\nmoirai = \"0.5\"\neunomia = \"0.8\""


class SubstrateContractTests(unittest.TestCase):
    """The ADR 0055 substrate contract check, and what it must not flag.

    The check is preventive: the fleet carries zero violations, so every test
    here guards a discrimination rather than a known defect. A check that
    cannot tell a shipped dependency from a comparison baseline would either
    be ignored, or would forbid measuring a first-party provider against the
    crate it replaces.
    """

    def names(self, manifest: str) -> set[str]:
        return set(conformance.runtime_dependency_names(manifest))

    def prohibited(self, manifest: str) -> set[str]:
        return self.names(manifest) & conformance.PROHIBITED_SUBSTRATE

    def test_runtime_dependency_is_flagged(self):
        self.assertEqual(self.prohibited(RUNTIME_RAYON), {"rayon"})

    def test_target_specific_runtime_dependency_is_flagged(self):
        self.assertEqual(self.prohibited(TARGET_NALGEBRA), {"nalgebra"})

    def test_dev_dependency_is_not_flagged(self):
        # The baseline a first-party provider is measured against lives here.
        self.assertEqual(self.prohibited(DEV_RAYON), set())

    def test_build_dependency_is_not_flagged(self):
        self.assertEqual(self.prohibited(BUILD_NDARRAY), set())

    def test_workspace_declaration_is_not_flagged(self):
        # Declaring a version activates nothing; a crate enters the graph only
        # through its own [dependencies].
        self.assertEqual(self.prohibited(WORKSPACE_RAYON), set())

    def test_measurement_harness_is_not_flagged(self):
        # moirai-benchmarks in miniature: unpublished, bench targets only,
        # depending on the crate it benchmarks against.
        self.assertEqual(self.prohibited(HARNESS), set())

    def test_published_crate_with_benches_is_still_flagged(self):
        # The exemption turns on unpublished *and* bench-declaring. A published
        # crate does not escape the contract by adding a bench target.
        self.assertEqual(self.prohibited(PUBLISHED_WITH_BENCH), {"rayon"})

    def test_unpublished_crate_without_benches_is_still_flagged(self):
        self.assertEqual(self.prohibited(UNPUBLISHED_NO_BENCH), {"rayon"})

    def test_unparseable_manifest_yields_nothing(self):
        # Malformed manifests are the manifest checks' business, not this one.
        self.assertEqual(self.names(MALFORMED), set())

    def test_first_party_providers_are_not_prohibited(self):
        self.assertEqual(self.prohibited(FIRST_PARTY), set())

    def test_the_class_is_registered_for_the_ratchet(self):
        self.assertIn("substrate_contract_violations", conformance.CLASSES)


class BareGitDependencyTestCase(unittest.TestCase):
    def count(self, manifest: str) -> int:
        return conformance.count_bare_git_dependencies(manifest)

    def test_version_less_git_dependency_is_counted(self):
        self.assertEqual(
            self.count('eunomia = { git = "https://example.com/eunomia" }'), 1
        )

    def test_version_requirement_clears_the_class(self):
        self.assertEqual(
            self.count(
                'eunomia = { version = "0.5", git = "https://example.com/eunomia" }'
            ),
            0,
        )

    def test_rev_pin_is_deliberate_width_not_neglect(self):
        # The sanctioned quarantine form: pin discipline requires the removal
        # trigger in a comment beside it, so the pin is recorded intent.
        self.assertEqual(
            self.count('moirai = { git = "https://example.com/Moirai", rev = "83aa411" }'),
            0,
        )

    def test_non_git_inline_tables_are_ignored(self):
        self.assertEqual(
            self.count('dep = { version = "1.0", features = ["a"] }'),
            0,
        )

    def test_the_class_is_registered_for_the_ratchet(self):
        self.assertIn("bare_git_dependency", conformance.CLASSES)
        self.assertIn("cache_retention_policy_missing", conformance.CLASSES)


class CrlfStoredBlobsTestCase(unittest.TestCase):
    """The detector reads the index, so its fixture is a real commit."""

    def _repo(self, attributes: str | None) -> Path:
        root = Path(tempfile.mkdtemp(prefix="crlf-detector-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        # Identity travels with the command, not the machine: CI runners
        # carry no global git identity, so a bare `commit` fails there
        # while passing on any developer box.
        ident = ["-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        # Commit WITHOUT the policy in effect: with `text=auto eol=lf` already
        # present, git normalizes on the way into the index and a contradicting
        # blob cannot exist. The defect class is historical — blobs committed
        # before the policy, exactly what the board item measured.
        (root / "keep.txt").write_bytes(b"lf blob\nsecond line\n")
        (root / "legacy.txt").write_bytes(b"crlf blob\r\nsecond line\r\n")
        # Raw-byte semantics: the host default (`core.autocrlf=true` on
        # Windows) would normalize at checkin and make the defect unfixturable.
        subprocess.run(
            ["git", "-C", str(root), "-c", "core.autocrlf=false", "add", "."],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "-c", "core.autocrlf=false", *ident,
             "commit", "-q", "-m", "blobs"], check=True
        )
        if attributes is not None:
            (root / ".gitattributes").write_text(attributes)
        return root

    def count(self, repo: Path) -> int:
        return conformance.count_crlf_stored_blobs(repo)

    def test_stored_crlf_blob_contradicting_the_policy_is_counted(self):
        repo = self._repo("* text=auto eol=lf\n")
        self.assertEqual(self.count(repo), 1)

    def test_renormalized_blob_clears_the_class(self):
        repo = self._repo("* text=auto eol=lf\n")
        subprocess.run(
            ["git", "-C", str(repo), "add", "--renormalize", "."], check=True
        )
        self.assertEqual(self.count(repo), 0)

    def test_without_a_policy_there_is_nothing_to_contradict(self):
        repo = self._repo(None)
        self.assertEqual(self.count(repo), 0)

    def test_the_class_is_registered_for_the_ratchet(self):
        self.assertIn("crlf_stored_blobs", conformance.CLASSES)


class ExistenceOnlyAssertionTests(unittest.TestCase):
    """The condition has to be the whole assertion, not one term of it."""

    def matches(self, source: str) -> int:
        return len(conformance.EXISTENCE_ONLY.findall(source))

    def test_a_bare_result_check_counts(self) -> None:
        self.assertEqual(self.matches("assert!(result.is_ok());"), 1)
        self.assertEqual(self.matches('assert!(missing.is_err(), "msg");'), 1)
        self.assertEqual(
            self.matches('assert!(result.is_ok(), "failed: {:?}", err);'), 1
        )

    def test_a_compound_predicate_does_not_count(self) -> None:
        """A disjunction is a property; a defect can fail it."""
        self.assertEqual(
            self.matches(
                'assert!(\n    classified[i] || map.is_some(),\n'
                '    "point {i} is neither C-point nor mapped F-point"\n)'
            ),
            0,
        )
        self.assertEqual(
            self.matches("assert!(count > 0 && handle.is_some());"), 0
        )

    def test_the_pattern_still_spans_wrapped_source(self) -> None:
        """The four real sites were written across lines."""
        self.assertEqual(
            self.matches('assert!(\n    result.is_ok(),\n    "must succeed"\n)'),
            1,
        )

    def test_a_trailing_conjunction_does_not_count(self) -> None:
        """The call must be the whole condition, not its first term either."""
        self.assertEqual(self.matches("assert!(result.is_ok() && other);"), 0)
        self.assertEqual(self.matches("assert!(handle.is_some() || fallback);"), 0)
        self.assertEqual(self.matches("assert!(result.is_ok() == expected);"), 0)


class MemberPathScanTests(unittest.TestCase):
    """`--member-path` judges a member from its own checkout."""

    def run_check(self, argv: list[str], results: dict, baseline: dict):
        with tempfile.TemporaryDirectory(prefix="atlas-member-path-") as temp:
            baseline_path = Path(temp) / "baseline.json"
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            member = Path(temp) / "member"
            member.mkdir()
            output = io.StringIO()
            with (
                patch.object(conformance, "BASELINE", baseline_path),
                patch.object(conformance, "scan_repo", return_value=results),
                patch.object(
                    sys, "argv",
                    [str(SCRIPT), "check", "--json", *argv, "--member-path", str(member)],
                ),
                redirect_stdout(output),
            ):
                code = conformance.main()
            return code, output.getvalue()

    def test_a_raise_in_the_member_fails_its_own_check(self) -> None:
        code, payload = self.run_check(
            ["--repo", "demo"],
            results={"markers": 3},
            baseline={"demo": {"markers": 0}},
        )
        self.assertEqual(code, 1)
        self.assertIn("demo/markers: 0 -> 3", json.loads(payload)["regressions"])

    def test_counts_at_or_below_the_baseline_pass(self) -> None:
        code, payload = self.run_check(
            ["--repo", "demo"],
            results={"markers": 0},
            baseline={"demo": {"markers": 2}},
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(payload)["regressions"], [])

    def test_a_path_without_a_member_is_refused(self) -> None:
        """Nothing to judge against is a usage error, not a pass."""
        with tempfile.TemporaryDirectory(prefix="atlas-member-path-") as temp:
            with (
                patch.object(
                    sys, "argv",
                    [str(SCRIPT), "check", "--member-path", temp],
                ),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(conformance.main(), 2)

    def test_a_revision_without_a_member_path_is_refused(self) -> None:
        with (
            patch.object(
                sys, "argv",
                [str(SCRIPT), "check", "--repo", "demo", "--member-revision", "HEAD"],
            ),
            redirect_stdout(io.StringIO()),
            redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(conformance.main(), 2)


def _git(repo: Path, *argv: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
         "-c", "core.autocrlf=false", *argv],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def _member_repo(root: Path) -> Path:
    """A one-crate git repository with a committed, in-budget source file."""
    member = root / "member"
    _write(member, "Cargo.toml", '[package]\nname = "demo"\nversion = "0.1.0"\n')
    _write(member, "src/lib.rs", "pub fn f() {}\n")
    _git(member.parent, "init", "-q", str(member))
    _git(member, "add", "-A")
    _git(member, "commit", "-q", "-m", "seed")
    return member


class MemberRevisionScanTests(unittest.TestCase):
    """`--member-revision` judges a commit of the member, not its checkout.

    The pre-push gate passes the pushed tip. A shared checkout holds whatever
    branch and uncommitted files a peer left there, so a working-tree scan
    judged a state nobody was pushing -- in both directions.
    """

    # 500 newline-terminated lines count as 501: the scan counts the text
    # after the last newline as a line, matching the 501-line push it refuses.
    OVERSIZED = "".join(f"// line {n}\n" for n in range(500))

    def check(self, member: Path, revision: str, baseline: dict) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory(prefix="atlas-baseline-") as temp:
            baseline_path = Path(temp) / "baseline.json"
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            output = io.StringIO()
            with (
                patch.object(conformance, "BASELINE", baseline_path),
                patch.object(
                    sys, "argv",
                    [str(SCRIPT), "check", "--json", "--repo", "demo",
                     "--member-path", str(member), "--member-revision", revision],
                ),
                redirect_stdout(output),
            ):
                code = conformance.main()
            return code, json.loads(output.getvalue())

    def seed_counts(self, member: Path) -> dict:
        """The seed commit's own counts, recorded as the member's baseline."""
        _, payload = self.check(member, "HEAD", {"demo": {}})
        counts = payload["results"]["demo"]
        self.assertEqual(counts["oversized_files"], 0)
        return counts

    def test_uncommitted_debt_is_not_the_revision_s(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-member-rev-") as temp:
            member = _member_repo(Path(temp))
            recorded = self.seed_counts(member)
            _write(member, "src/big.rs", self.OVERSIZED)
            code, payload = self.check(member, "HEAD", {"demo": recorded})
            self.assertEqual(payload["results"]["demo"]["oversized_files"], 0)
            self.assertEqual(payload["regressions"], [])
            self.assertEqual(code, 0)

    def test_committed_debt_fails_even_when_the_checkout_is_elsewhere(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-member-rev-") as temp:
            member = _member_repo(Path(temp))
            recorded = self.seed_counts(member)
            seed = _git(member, "rev-parse", "HEAD")
            _write(member, "src/big.rs", self.OVERSIZED)
            _write(member, "src/lib.rs", "pub mod big;\npub fn f() {}\n")
            _git(member, "add", "src")
            _git(member, "commit", "-q", "-m", "oversized")
            pushed = _git(member, "rev-parse", "HEAD")
            # The checkout moves back, as a peer switching the shared tree would.
            _git(member, "checkout", "-q", seed)
            code, payload = self.check(member, pushed, {"demo": recorded})
            self.assertEqual(payload["results"]["demo"]["oversized_files"], 1)
            self.assertEqual(payload["regressions"], ["demo/oversized_files: 0 -> 1"])
            self.assertEqual(code, 1)

    def test_host_rows_are_reported_without_failing_a_revision(self) -> None:
        """A lane or forked cache on this machine is not in the pushed commit."""
        with tempfile.TemporaryDirectory(prefix="atlas-member-rev-") as temp:
            member = _member_repo(Path(temp))
            with patch.object(conformance, "scan_repo", return_value={"target_forks": 1}):
                code, payload = self.check(member, "HEAD", {"demo": {"target_forks": 0}})
            self.assertEqual(payload["host_regressions"], ["demo/target_forks: 0 -> 1"])
            self.assertEqual(code, 0)


class LinkSnapshotTests(unittest.TestCase):
    """`link_snapshot` reproduces `git archive` of the revision exactly."""

    @staticmethod
    def tree(root: Path) -> dict[str, bytes]:
        return {
            p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file() and p.name != ".git"
        }

    def test_the_snapshot_matches_the_archived_revision(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-link-snapshot-") as temp:
            member = _member_repo(Path(temp))
            _write(member, "src/kept.rs", "pub fn kept() {}\n")
            _write(member, "src/edited.rs", "pub fn committed() {}\n")
            _write(member, "src/removed.rs", "pub fn removed() {}\n")
            _git(member, "add", "-A")
            _git(member, "commit", "-q", "-m", "revision")
            revision = _git(member, "rev-parse", "HEAD")
            # A shared checkout's state after the commit: an edit, a deletion,
            # and a scratch file, none of which the revision contains.
            _write(member, "src/edited.rs", "pub fn uncommitted() {}\n")
            (member / "src" / "removed.rs").unlink()
            _write(member, "scratch.rs", "fn peer() {}\n")

            archived = Path(temp) / "archived"
            archived.mkdir()
            conformance.extract_archive(
                conformance.archive(member, revision, timeout=60), archived
            )
            scratch = Path(temp) / "scratch"
            scratch.mkdir()
            linked = conformance.link_snapshot(member, revision, scratch)

            self.assertEqual(self.tree(linked), self.tree(archived))
            self.assertEqual(
                (linked / "src" / "edited.rs").read_text(), "pub fn committed() {}\n"
            )
            self.assertFalse((linked / "scratch.rs").exists())
            # The checkout itself is untouched by the snapshot and its removal.
            shutil.rmtree(linked)
            self.assertEqual(
                (member / "src" / "edited.rs").read_text(), "pub fn uncommitted() {}\n"
            )
            self.assertEqual(
                [e.strip() for e in _git(member, "status", "--porcelain", "-z").split("\0")],
                ["M src/edited.rs", "D src/removed.rs", "?? scratch.rs", ""],
            )


class BaselineRevisionTests(unittest.TestCase):
    """`--baseline-rev` reads the committed baseline, not the working copy."""

    def test_the_committed_baseline_is_the_one_judged_against(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-baseline-rev-") as temp:
            stack = Path(temp) / "stack"
            baseline_path = stack / "scripts" / "conformance-baseline.json"
            _write(stack, "scripts/conformance-baseline.json",
                   json.dumps({"demo": {"markers": 5}}))
            _git(stack.parent, "init", "-q", str(stack))
            _git(stack, "add", "-A")
            _git(stack, "commit", "-q", "-m", "baseline")
            # A regeneration in progress rewrote the working copy downward.
            baseline_path.write_text(json.dumps({"demo": {"markers": 0}}))
            member = Path(temp) / "member"
            member.mkdir()

            def run(extra: list[str]) -> int:
                with (
                    patch.object(conformance, "ROOT", stack),
                    patch.object(conformance, "BASELINE", baseline_path),
                    patch.object(conformance, "scan_repo", return_value={"markers": 3}),
                    patch.object(
                        sys, "argv",
                        [str(SCRIPT), "check", "--repo", "demo",
                         "--member-path", str(member), *extra],
                    ),
                    redirect_stdout(io.StringIO()),
                ):
                    return conformance.main()

            self.assertEqual(run(["--baseline-rev", "HEAD"]), 0)
            self.assertEqual(run([]), 1)

    def test_an_unreadable_baseline_revision_cannot_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-baseline-rev-") as temp:
            stack = Path(temp) / "stack"
            stack.mkdir()
            _git(stack.parent, "init", "-q", str(stack))
            member = Path(temp) / "member"
            member.mkdir()
            with (
                patch.object(conformance, "ROOT", stack),
                patch.object(
                    conformance, "BASELINE",
                    stack / "scripts" / "conformance-baseline.json",
                ),
                patch.object(conformance, "scan_repo", return_value={"markers": 0}),
                patch.object(
                    sys, "argv",
                    [str(SCRIPT), "check", "--repo", "demo", "--member-path",
                     str(member), "--baseline-rev", "no-such-ref"],
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(conformance.main(), 2)


class RootAllowanceFollowsTheMemberTests(unittest.TestCase):
    """A member's sanctioned root files travel with the member's name."""

    def sprawl(self, directory_name: str, member: str | None):
        with tempfile.TemporaryDirectory(prefix="atlas-root-allowance-") as temp:
            repo = Path(temp) / directory_name
            repo.mkdir()
            (repo / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
            (repo / "metis.json").write_text("{}\n", encoding="utf-8")
            carried, _ = conformance.count_root_sprawl(repo, member=member)
            return carried

    def test_the_allowance_applies_when_the_member_is_named(self) -> None:
        """An export, or any checkout whose directory is named otherwise."""
        self.assertEqual(self.sprawl("metis-pr-322-export", member="metis"), 0)

    def test_the_directory_name_still_works_as_the_proxy(self) -> None:
        """`repos/<name>` keeps resolving without a caller passing it."""
        self.assertEqual(self.sprawl("metis", member=None), 0)

    def test_an_unsanctioned_root_file_still_counts(self) -> None:
        """The allowance is per name, not an exemption for the member."""
        with tempfile.TemporaryDirectory(prefix="atlas-root-allowance-") as temp:
            repo = Path(temp) / "anywhere"
            repo.mkdir()
            (repo / "scratch.patch").write_text("diff\n", encoding="utf-8")
            carried, _ = conformance.count_root_sprawl(repo, member="metis")
            self.assertEqual(carried, 1)


class CitationResolutionTests(unittest.TestCase):
    """A cited hash resolves through default branches and tags alone, so the
    count is a function of the scanned tree: a branch deletion elsewhere can
    neither raise it nor lower it, and a branch-only citation counts from the
    push that writes it."""

    GIT_ENV = {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_NOSYSTEM": "1", "HOME": tempfile.gettempdir(),
        "PATH": __import__("os").environ["PATH"],
        # Fixed dates make every fixture sha the same on every run. With
        # clock dates a cited 9-character prefix was all digits about 1.5% of
        # the time, which the citation pattern rightly does not read as a
        # hash, and the expected count came out one short.
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
    }
    CLS = conformance.REF_DRIFT_CLASS

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="atlas-ref-drift-")
        self.root = Path(self._tmp.name)
        conformance.board_lint._REACHABLE_INDEX.clear()

    def tearDown(self) -> None:
        conformance.board_lint._REACHABLE_INDEX.clear()
        self._tmp.cleanup()

    def _git(self, repo: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True,
            text=True, env=self.GIT_ENV,
        ).stdout.strip()

    def _commit(self, repo: Path, rel: str, text: str) -> str:
        _write(repo, rel, text)
        self._git(repo, "add", rel)
        self._git(repo, "commit", "-q", "-m", rel)
        return self._git(repo, "rev-parse", "HEAD")

    def _branch_only_commit(self, repo: Path) -> str:
        """A commit reachable from `feature` alone, which is then deleted."""
        self._git(repo, "switch", "-q", "-c", "feature")
        orphan = self._commit(repo, "feature.txt", "feature\n")
        self._git(repo, "switch", "-q", "main")
        self.assertRegex(
            orphan[:9], conformance.board_lint.HASH_PATTERN,
            "the fixture cites this prefix, so it must read as a hash",
        )
        return orphan

    def _stack(self) -> tuple[str, str, str]:
        """Root and member boards each cite a branch-only commit at base."""
        member = self.root / "repos" / "member"
        member.mkdir(parents=True)
        self._git(member, "init", "-q", "-b", "main")
        self._commit(member, "README.md", "member\n")
        member_orphan = self._branch_only_commit(member)
        member_base = self._commit(member, "backlog.md", f"- at {member_orphan[:9]}\n")

        self._git(self.root, "init", "-q", "-b", "main")
        self._commit(self.root, "README.md", "root\n")
        root_orphan = self._branch_only_commit(self.root)
        _write(self.root, "backlog.md", f"- at {root_orphan[:9]}\n")
        self._git(self.root, "add", "backlog.md")
        self._git(
            self.root, "update-index", "--add", "--cacheinfo",
            f"160000,{member_base},repos/member",
        )
        self._git(self.root, "commit", "-q", "-m", "base")
        base = self._git(self.root, "rev-parse", "HEAD")
        return base, root_orphan, member_orphan

    def _measure(self) -> dict[str, dict[str, int]]:
        stores = conformance.board_lint.object_stores(self.root)
        return {
            "<meta>": {self.CLS: conformance.board_lint.count_unresolved(self.root, stores)},
            "member": {
                self.CLS: conformance.board_lint.count_unresolved(
                    self.root / "repos" / "member", stores
                )
            },
        }

    def _remeasure(self) -> dict[str, dict[str, int]]:
        conformance.board_lint._REACHABLE_INDEX.clear()
        return self._measure()

    def test_a_branch_deletion_leaves_the_count_unchanged(self) -> None:
        self._stack()
        cited_on_branches = self._measure()
        self.assertEqual(cited_on_branches, {"<meta>": {self.CLS: 1}, "member": {self.CLS: 1}})
        self._git(self.root, "branch", "-q", "-D", "feature")
        self._git(self.root / "repos" / "member", "branch", "-q", "-D", "feature")
        self.assertEqual(self._remeasure(), cited_on_branches)

    def test_a_merged_citation_resolves(self) -> None:
        self._stack()
        self._git(self.root, "merge", "-q", "--no-ff", "-m", "land", "feature")
        self._git(self.root, "branch", "-q", "-D", "feature")
        self.assertEqual(
            self._remeasure(), {"<meta>": {self.CLS: 0}, "member": {self.CLS: 1}}
        )

    def test_a_tagged_citation_resolves(self) -> None:
        self._stack()
        member = self.root / "repos" / "member"
        self._git(member, "tag", "v1", "feature")
        self._git(member, "branch", "-q", "-D", "feature")
        self.assertEqual(
            self._remeasure(), {"<meta>": {self.CLS: 1}, "member": {self.CLS: 0}}
        )

    def _origin_store(self) -> tuple[str, str]:
        """A store whose origin refs name a default and a working branch.

        Local `main` is moved onto the working-branch commit, so a resolver
        that consulted local branches beside origin would resolve it.
        """
        self._git(self.root, "init", "-q", "-b", "main")
        trunk = self._commit(self.root, "README.md", "root\n")
        branch_only = self._branch_only_commit(self.root)
        self._git(self.root, "update-ref", "refs/remotes/origin/feature", branch_only)
        self._git(self.root, "update-ref", "refs/heads/main", branch_only)
        return trunk, branch_only

    def test_origin_head_names_the_default(self) -> None:
        trunk, branch_only = self._origin_store()
        self._git(self.root, "update-ref", "refs/remotes/origin/trunk", trunk)
        self._git(
            self.root, "symbolic-ref", "refs/remotes/origin/HEAD",
            "refs/remotes/origin/trunk",
        )
        stores = conformance.board_lint.object_stores(self.root)
        self.assertEqual(
            conformance.board_lint.resolve_hashes({trunk[:9], branch_only[:9]}, stores),
            {trunk[:9]},
        )

    def test_origin_main_is_the_default_without_origin_head(self) -> None:
        # The CI superproject: origin branches fetched, no `origin/HEAD`.
        trunk, branch_only = self._origin_store()
        self._git(self.root, "update-ref", "refs/remotes/origin/main", trunk)
        stores = conformance.board_lint.object_stores(self.root)
        self.assertEqual(
            conformance.board_lint.resolve_hashes({trunk[:9], branch_only[:9]}, stores),
            {trunk[:9]},
        )

    def test_origin_refs_without_a_default_stop_the_scan(self) -> None:
        trunk, _ = self._origin_store()
        self._git(self.root, "update-ref", "refs/remotes/origin/trunk", trunk)
        stores = conformance.board_lint.object_stores(self.root)
        with self.assertRaisesRegex(RuntimeError, "origin refs name no default branch"):
            conformance.board_lint.resolve_hashes({trunk[:9]}, stores)

    def test_an_unreadable_store_stops_the_scan(self) -> None:
        self._git(self.root, "init", "-q", "-b", "main")
        trunk = self._commit(self.root, "README.md", "root\n")
        (self.root / ".git" / "HEAD").write_text("garbage\n")
        stores = [self.root]
        with self.assertRaisesRegex(RuntimeError, "cannot list refs"):
            conformance.board_lint.resolve_hashes({trunk[:9]}, stores)

    def test_an_unwalkable_history_stops_the_scan(self) -> None:
        self._git(self.root, "init", "-q", "-b", "main")
        parent = self._commit(self.root, "README.md", "root\n")
        tip = self._commit(self.root, "second.txt", "second\n")
        # Refs still list, but the walk from `main` reaches a missing parent.
        missing = self.root / ".git" / "objects" / parent[:2] / parent[2:]
        missing.chmod(0o644)  # git stores loose objects read-only
        missing.unlink()
        stores = [self.root]
        with self.assertRaisesRegex(RuntimeError, "cannot walk landed history"):
            conformance.board_lint.resolve_hashes({tip[:9]}, stores)

    def test_branch_only_citation_counts_as_a_ratchet_regression(self) -> None:
        baseline = {"member": {self.CLS: 0}}
        results = {"member": {self.CLS: 1}}
        regressions, host, tightenings = conformance.ratchet_delta(baseline, results)
        self.assertEqual(regressions, [f"member/{self.CLS}: 0 -> 1"])
        self.assertEqual((host, tightenings), ([], []))


class SecondOutputRootTestCase(unittest.TestCase):
    """`output/` is canonical; a legacy root beside it is debt.

    ATLAS-RUN-OUTPUT-SEGREGATION: `run-output/` held 327 MB at the stack
    root, ignored but outside the one committed retention policy, which
    only ever covered `output/`.
    """

    def test_no_legacy_root_counts_zero(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-output-root-") as temp:
            root = Path(temp)
            (root / "output").mkdir()
            self.assertEqual(conformance.count_second_output_roots(root), 0)

    def test_run_output_directory_counts_one(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-output-root-") as temp:
            root = Path(temp)
            (root / "output").mkdir()
            (root / "run-output").mkdir()
            self.assertEqual(conformance.count_second_output_roots(root), 1)

    def test_every_legacy_root_present_counts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-output-root-") as temp:
            root = Path(temp)
            for name in conformance.SECOND_OUTPUT_ROOT_NAMES:
                (root / name).mkdir()
            self.assertEqual(
                conformance.count_second_output_roots(root),
                len(conformance.SECOND_OUTPUT_ROOT_NAMES),
            )

    def test_a_same_named_file_is_not_counted(self) -> None:
        """Directory-only: an empty placeholder file is not the debt."""
        with tempfile.TemporaryDirectory(prefix="atlas-output-root-") as temp:
            root = Path(temp)
            (root / "run-output").write_text("", encoding="utf-8")
            self.assertEqual(conformance.count_second_output_roots(root), 0)

    def test_the_class_is_registered_for_the_ratchet(self) -> None:
        self.assertIn("second_output_root", conformance.CLASSES)
        self.assertIn("second_output_root", conformance.HOST_OBSERVED_CLASSES)


if __name__ == "__main__":
    unittest.main()
