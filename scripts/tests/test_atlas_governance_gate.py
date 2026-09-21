#!/usr/bin/env python3
"""Tests for the Atlas governance gate."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-governance-gate.py"
SPEC = importlib.util.spec_from_file_location("atlas_governance_gate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class AtlasGovernanceGateTestCase(unittest.TestCase):
    def test_workflow_action_issues_detect_unpinned_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = Path(tmpdir) / "ci.yml"
            workflow.write_text(
                "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n",
                encoding="utf-8",
            )
            issues = module._workflow_action_issues(workflow)
            self.assertTrue(issues)
            self.assertIn("actions/checkout@v4", issues[0])

    def test_workflow_action_issues_ignore_inline_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = Path(tmpdir) / "ci.yml"
            workflow.write_text(
                "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567 # v7\n",
                encoding="utf-8",
            )
            issues = module._workflow_action_issues(workflow)
            self.assertFalse(issues)

    def test_member_issues_report_missing_toolchain_and_workflows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "repos" / "demo"
            repo.mkdir(parents=True)
            (repo / "Cargo.toml").write_text("[package]\nname = \"demo\"\nversion = \"0.1.0\"\n", encoding="utf-8")
            with patch.object(module, "registered_members", return_value=[repo]):
                issues = module._member_issues()
            self.assertTrue(any("missing rust-toolchain.toml" in issue for issue in issues))
            self.assertTrue(any("missing .github/workflows/*.yml" in issue for issue in issues))

    def test_main_accepts_pinned_workflows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "repos" / "demo"
            repo.mkdir(parents=True)
            (repo / "Cargo.toml").write_text("[workspace]\nmembers = []\n", encoding="utf-8")
            (repo / "rust-toolchain.toml").write_text('[toolchain]\nchannel = "1.97.0"\n', encoding="utf-8")
            workflows = repo / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "ci.yml").write_text(
                "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567\n",
                encoding="utf-8",
            )
            with patch.object(module, "ROOT", root), patch.object(
                module, "registered_members", return_value=[repo]
            ):
                self.assertEqual(module.main(), 0)


if __name__ == "__main__":
    unittest.main()
