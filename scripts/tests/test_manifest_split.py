#!/usr/bin/env python3
"""Regression tests for the manifest splitter's tree and import contracts."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "manifest-split.py"


class ManifestSplitTests(unittest.TestCase):
    """Exercise output placement and whole-item import rebasing."""

    def test_rust_file_leaves_use_child_directory_and_dry_run_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            source = root / "foo.rs"
            source.write_text(
                "mod child;\n"
                "use {\n"
                "    super::Thing,\n"
                "    child::Item,\n"
                "};\n"
                "struct Thing {\n"
                "    value: usize,\n"
                "}\n"
                "impl Thing {\n"
                "    fn value(&self) -> usize { self.value }\n"
                "}\n"
                "fn keep() {}\n",
                encoding="utf-8",
            )
            plan = root / "plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "modules": [
                            {"name": "thing", "doc": "//! Thing leaf", "items": ["Thing"]}
                        ]
                    }
                ),
                encoding="utf-8",
            )

            dry_run = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), "--plan", str(plan), "--dry-run"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
            self.assertFalse((root / "foo").exists())

            run = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), "--plan", str(plan)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            leaf = root / "foo" / "thing.rs"
            self.assertTrue(leaf.is_file())
            leaf_text = leaf.read_text(encoding="utf-8")
            self.assertIn("super::super::Thing", leaf_text)
            self.assertIn("super::child::Item", leaf_text)
            self.assertIn("mod thing;", source.read_text(encoding="utf-8"))

    def test_module_manifest_keeps_leaves_as_siblings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            module_dir = root / "nested"
            module_dir.mkdir()
            source = module_dir / "mod.rs"
            source.write_text("pub struct Value;\npub fn keep() {}\n", encoding="utf-8")
            plan = root / "plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "modules": [
                            {"name": "value", "doc": "//! Value leaf", "items": ["Value"]}
                        ]
                    }
                ),
                encoding="utf-8",
            )

            run = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), "--plan", str(plan)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue((module_dir / "value.rs").is_file())
            self.assertFalse((module_dir / "mod" / "value.rs").exists())


if __name__ == "__main__":
    unittest.main()
