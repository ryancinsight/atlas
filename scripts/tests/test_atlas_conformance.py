#!/usr/bin/env python3
"""Tests for the Atlas conformance scanner."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
