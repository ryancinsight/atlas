#!/usr/bin/env python3
"""Tests for the Atlas provider integration audit guard."""

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


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-provider-integration-audit.py"
SPEC = importlib.util.spec_from_file_location("atlas_provider_integration_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def _seed_record(path: Path) -> None:
    path.write_text(
        "\n".join(
            (
                "## ATLAS-PROVIDER-INTEGRATION-AUDIT-001 — done 2026-08-11",
                "Scope: Tyche (aka Tychee)",
            )
        ),
        encoding="utf-8",
    )


class ProviderIntegrationAuditTestCase(unittest.TestCase):
    def test_requested_provider_inventory_is_complete(self) -> None:
        self.assertEqual(len(audit.REQUIRED_PROVIDERS), 20)
        self.assertIn("hermes", audit.REQUIRED_PROVIDERS)

    def test_main_succeeds_with_complete_inputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-provider-audit-") as temp:
            root = Path(temp)
            (root / ".gitmodules").write_text(
                "\n".join(
                    f'[submodule "repos/{name}"]\n\tpath = repos/{name}\n\tactive = true\n'
                    for name in audit.REQUIRED_PROVIDERS
                ),
                encoding="utf-8",
            )
            for filename in ("checklist.md", "backlog.md", "gap_audit.md"):
                _seed_record(root / filename)

            with patch.object(audit, "ROOT", root), patch.object(
                audit, "GITMODULES", root / ".gitmodules"
            ), patch.object(
                audit,
                "RECORD_FILES",
                (root / "checklist.md", root / "backlog.md", root / "gap_audit.md"),
            ), patch.object(
                audit, "_coherence_scope_issues", return_value=([], 0)
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = audit.main([])

        self.assertEqual(code, 0)
        self.assertIn("provider-integration-audit: OK", output.getvalue())

    def test_main_fails_when_provider_inactive(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-provider-audit-") as temp:
            root = Path(temp)
            lines: list[str] = []
            for name in audit.REQUIRED_PROVIDERS:
                lines.append(f'[submodule "repos/{name}"]')
                lines.append(f"\tpath = repos/{name}")
                if name != "tyche":
                    lines.append("\tactive = true")
                lines.append("")
            (root / ".gitmodules").write_text("\n".join(lines), encoding="utf-8")
            for filename in ("checklist.md", "backlog.md", "gap_audit.md"):
                _seed_record(root / filename)

            with patch.object(audit, "ROOT", root), patch.object(
                audit, "GITMODULES", root / ".gitmodules"
            ), patch.object(
                audit,
                "RECORD_FILES",
                (root / "checklist.md", root / "backlog.md", root / "gap_audit.md"),
            ), patch.object(
                audit, "_coherence_scope_issues", return_value=([], 0)
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = audit.main([])

        self.assertEqual(code, 1)
        self.assertIn("repos/tyche missing `active = true`", output.getvalue())

    def test_main_fails_when_record_not_done(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-provider-audit-") as temp:
            root = Path(temp)
            (root / ".gitmodules").write_text(
                "\n".join(
                    f'[submodule "repos/{name}"]\n\tpath = repos/{name}\n\tactive = true\n'
                    for name in audit.REQUIRED_PROVIDERS
                ),
                encoding="utf-8",
            )
            (root / "checklist.md").write_text(
                "## ATLAS-PROVIDER-INTEGRATION-AUDIT-001 — in-progress\nTyche (aka Tychee)\n",
                encoding="utf-8",
            )
            _seed_record(root / "backlog.md")
            _seed_record(root / "gap_audit.md")

            with patch.object(audit, "ROOT", root), patch.object(
                audit, "GITMODULES", root / ".gitmodules"
            ), patch.object(
                audit,
                "RECORD_FILES",
                (root / "checklist.md", root / "backlog.md", root / "gap_audit.md"),
            ), patch.object(
                audit, "_coherence_scope_issues", return_value=([], 0)
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = audit.main([])

        self.assertEqual(code, 1)
        self.assertIn(
            "checklist.md: ATLAS-PROVIDER-INTEGRATION-AUDIT-001 is not marked done/closed",
            output.getvalue(),
        )

    def test_coherence_scope_filters_out_of_scope_findings(self) -> None:
        report = {
            "findings": [
                {
                    "manifest": "repos\\themis\\Cargo.toml",
                    "dependency": "melinoe",
                    "package": "melinoe",
                    "required": "0.10.0",
                    "actual": "0.9.0",
                    "reason": "requirement does not accept current package version",
                },
                {
                    "manifest": "repos\\athena\\Cargo.toml",
                    "dependency": "mnemosyne",
                    "package": "mnemosyne-memory",
                    "required": "0.7.0",
                    "actual": "0.6.0",
                    "reason": "requirement does not accept current package version",
                },
            ]
        }

        with patch.object(audit.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess(
                args=["cargo"], returncode=1, stdout=json.dumps(report), stderr=""
            )
            scoped, out_of_scope = audit._coherence_scope_issues()

        self.assertEqual(len(scoped), 1)
        self.assertIn("repos/themis/Cargo.toml", scoped[0])
        self.assertEqual(out_of_scope, 1)

    def test_structural_only_skips_coherence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-provider-audit-") as temp:
            root = Path(temp)
            (root / ".gitmodules").write_text(
                "\n".join(
                    f'[submodule "repos/{name}"]\n\tpath = repos/{name}\n\tactive = true\n'
                    for name in audit.REQUIRED_PROVIDERS
                ),
                encoding="utf-8",
            )
            for filename in ("checklist.md", "backlog.md", "gap_audit.md"):
                _seed_record(root / filename)

            with patch.object(audit, "ROOT", root), patch.object(
                audit, "GITMODULES", root / ".gitmodules"
            ), patch.object(
                audit,
                "RECORD_FILES",
                (root / "checklist.md", root / "backlog.md", root / "gap_audit.md"),
            ), patch.object(
                audit, "_coherence_scope_issues", side_effect=AssertionError("should not run")
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = audit.main(["--structural-only"])

        self.assertEqual(code, 0)
        self.assertIn("requested-provider coherence skipped", output.getvalue())

    def test_exact_head_mode_reports_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-provider-audit-") as temp:
            root = Path(temp)
            (root / ".gitmodules").write_text(
                "\n".join(
                    f'[submodule "repos/{name}"]\n\tpath = repos/{name}\n\tactive = true\n'
                    for name in audit.REQUIRED_PROVIDERS
                ),
                encoding="utf-8",
            )
            for filename in ("checklist.md", "backlog.md", "gap_audit.md"):
                _seed_record(root / filename)

            with patch.object(audit, "ROOT", root), patch.object(
                audit, "GITMODULES", root / ".gitmodules"
            ), patch.object(
                audit,
                "RECORD_FILES",
                (root / "checklist.md", root / "backlog.md", root / "gap_audit.md"),
            ), patch.object(
                audit, "_coherence_scope_issues", return_value=([], 0)
            ), patch.object(
                audit,
                "_exact_head_issues",
                return_value=["repos/mnemosyne: gitlink old != origin/main new"],
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = audit.main(["--exact-heads"])

        self.assertEqual(code, 1)
        self.assertIn("repos/mnemosyne: gitlink old", output.getvalue())

    def test_provider_remote_head_accepts_master_default(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-provider-audit-") as temp:
            root = Path(temp)
            provider_path = root / "repos" / "hephaestus"
            provider_path.mkdir(parents=True)
            with patch.object(audit, "ROOT", root):
                with patch.object(
                    audit.subprocess,
                    "run",
                    side_effect=(
                        subprocess.CompletedProcess(
                            args=["git"], returncode=0, stdout="origin/master\n", stderr=""
                        ),
                        subprocess.CompletedProcess(
                            args=["git"], returncode=0, stdout="abc123\n", stderr=""
                        ),
                    ),
                ):
                    ref, commit, error = audit._provider_remote_head("hephaestus")

        self.assertEqual((ref, commit, error), ("origin/master", "abc123", None))


if __name__ == "__main__":
    unittest.main()
