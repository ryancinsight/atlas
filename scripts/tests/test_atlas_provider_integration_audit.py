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
    def test_active_submodule_names_parses_active_flags(self) -> None:
        gitmodules = "\n".join(
            (
                '[submodule "repos/horae"]',
                "\tpath = repos/horae",
                "\tactive = true",
                '[submodule "repos/themis"]',
                "\tpath = repos/themis",
            )
        )
        parsed = audit._active_submodule_names(gitmodules)
        self.assertEqual(parsed.get("repos/horae"), True)
        self.assertEqual(parsed.get("repos/themis"), False)

    def test_clean_rust_env_removes_compiler_overrides(self) -> None:
        with patch.dict(
            audit.os.environ,
            {"RUSTC": "foreign-rustc", "RUSTDOC": "foreign-rustdoc"},
            clear=False,
        ):
            env = audit._clean_rust_env()

        self.assertNotIn("RUSTC", env)
        self.assertNotIn("RUSTDOC", env)

    def test_clean_checkout_issues_report_head_drift_and_dirty_state(self) -> None:
        provider = "horae"
        expected = "a" * 40
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "repos" / provider).mkdir(parents=True)
            with patch.object(audit, "_gitlink_commits", return_value={provider: expected}), patch.object(
                audit,
                "_git_output",
                side_effect=[
                    (0, expected, ""),
                    (0, " M src/lib.rs\n?? scratch.txt", ""),
                ],
            ), patch.object(audit, "ROOT", root):
                issues = audit._clean_checkout_issues((provider,))

        self.assertEqual(issues, ["repos/horae: checkout is dirty (2 changed entries)"])

    def test_parse_accepts_clean_checkout_gate(self) -> None:
        parsed = audit.parse_args(["--require-clean-checkouts"])
        self.assertTrue(parsed.require_clean_checkouts)

    def test_requested_provider_inventory_is_complete(self) -> None:
        self.assertEqual(len(audit.REQUIRED_PROVIDERS), 22)
        self.assertEqual(audit.INTEGRATOR_REPOS, ("CFDrs", "kwavers", "helios"))
        self.assertEqual(len(audit.REQUESTED_PROVIDERS_20260814), 20)
        self.assertIn("hermes", audit.REQUIRED_PROVIDERS)
        self.assertIn("gaia", audit.REQUIRED_PROVIDERS)
        self.assertIn("harmonia", audit.REQUIRED_PROVIDERS)
        self.assertNotIn("gaia", audit.REQUESTED_PROVIDERS_20260814)

    def test_exact_scope_includes_integrators_once(self) -> None:
        self.assertEqual(
            audit._exact_scope(("horae", "helios")),
            ("horae", "helios", "CFDrs", "kwavers"),
        )

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
        self.assertIn(
            "- 22 providers present and active in .gitmodules", output.getvalue()
        )

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
            scoped, out_of_scope = audit._coherence_scope_issues(
                audit.REQUESTED_PROVIDERS_20260814
            )

        self.assertEqual(len(scoped), 1)
        self.assertIn("repos/themis/Cargo.toml", scoped[0])
        self.assertEqual(out_of_scope, 1)

    def test_coherence_scope_ignores_non_repo_manifest(self) -> None:
        report = {
            "findings": [
                {
                    "manifest": "Cargo.toml",
                    "dependency": "melinoe",
                    "package": "melinoe",
                    "required": "0.10.0",
                    "actual": "0.9.0",
                    "reason": "requirement does not accept current package version",
                },
            ]
        }

        with patch.object(audit.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess(
                args=["cargo"], returncode=1, stdout=json.dumps(report), stderr=""
            )
            scoped, out_of_scope = audit._coherence_scope_issues(("themis",))

        self.assertEqual(scoped, [])
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

    def test_main_uses_coherence_report_json_and_skips_cargo(self) -> None:
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
            report_path = root / "coherence.json"
            report_path.write_text(
                json.dumps(
                    {
                        "findings": [
                            {
                                "manifest": "repos\\themis\\Cargo.toml",
                                "dependency": "melinoe",
                                "package": "melinoe",
                                "required": "0.10.0",
                                "actual": "0.9.0",
                                "reason": "requirement does not accept current package version",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(audit, "ROOT", root), patch.object(
                audit, "GITMODULES", root / ".gitmodules"
            ), patch.object(
                audit,
                "RECORD_FILES",
                (root / "checklist.md", root / "backlog.md", root / "gap_audit.md"),
            ), patch.object(audit.subprocess, "run") as run:
                output = io.StringIO()
                with redirect_stdout(output):
                    code = audit.main(["--coherence-report-json", str(report_path)])

        self.assertEqual(code, 1)
        run.assert_not_called()
        self.assertIn("repos/themis/Cargo.toml", output.getvalue())

    def test_main_invalid_coherence_report_json_is_blocking(self) -> None:
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
            report_path = root / "coherence.json"
            report_path.write_text("{invalid json", encoding="utf-8")

            with patch.object(audit, "ROOT", root), patch.object(
                audit, "GITMODULES", root / ".gitmodules"
            ), patch.object(
                audit,
                "RECORD_FILES",
                (root / "checklist.md", root / "backlog.md", root / "gap_audit.md"),
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = audit.main(["--coherence-report-json", str(report_path)])

        self.assertEqual(code, 1)
        self.assertIn("coherence report JSON at", output.getvalue())
        self.assertIn("is invalid", output.getvalue())

    def test_out_of_scope_coherence_is_non_blocking_by_default(self) -> None:
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
                audit, "_coherence_scope_issues", return_value=([], 2)
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = audit.main([])

        self.assertEqual(code, 0)
        self.assertIn(
            "out-of-scope coherence defects present outside requested providers: 2",
            output.getvalue(),
        )
        self.assertIn("non-blocking here", output.getvalue())

    def test_fail_out_of_scope_makes_out_of_scope_blocking(self) -> None:
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
                audit, "_coherence_scope_issues", return_value=([], 2)
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = audit.main(["--fail-out-of-scope"])

        self.assertEqual(code, 1)
        self.assertIn("provider-integration-audit: FAIL", output.getvalue())
        self.assertIn(
            "out-of-scope coherence defects present outside requested providers: 2 (--fail-out-of-scope)",
            output.getvalue(),
        )

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

    def test_main_forwards_exact_head_worker_setting(self) -> None:
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
                audit, "_exact_head_issues", return_value=[]
            ) as exact_head_issues:
                output = io.StringIO()
                with redirect_stdout(output):
                    code = audit.main(["--exact-heads", "--exact-head-workers", "3"])

        self.assertEqual(code, 0)
        exact_head_issues.assert_called_once_with(
            audit._exact_scope(audit.REQUIRED_PROVIDERS), 3
        )

    def test_gitlink_reads_index_instead_of_child_checkout_head(self) -> None:
        with patch.object(
            audit,
            "_git_output",
            return_value=(0, "160000 staged-head 0\trepos/tyche", ""),
        ):
            self.assertEqual(
                audit._gitlink_commits(("tyche",)),
                {"tyche": "staged-head"},
            )

    def test_gitlink_commits_parses_batch_ls_files(self) -> None:
        stdout = "\n".join(
            (
                "160000 head-a 0\trepos/horae",
                "160000 head-b 0\trepos/hermes",
            )
        )
        with patch.object(audit, "_git_output", return_value=(0, stdout, "")):
            commits = audit._gitlink_commits(("horae", "hermes"))

        self.assertEqual(
            commits,
            {
                "horae": "head-a",
                "hermes": "head-b",
            },
        )

    def test_exact_head_issues_uses_batched_gitlink_map(self) -> None:
        with patch.object(
            audit,
            "_gitlink_commits",
            return_value={"horae": "h1", "hermes": "h2"},
        ), patch.object(
            audit,
            "_provider_remote_head",
            side_effect=(("origin/main", "h1", None), ("origin/main", "h2", None)),
        ):
            issues = audit._exact_head_issues(("horae", "hermes"))

        self.assertEqual(issues, [])

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
                            args=["git"], returncode=1, stdout="", stderr=""
                        ),
                        subprocess.CompletedProcess(
                            args=["git"], returncode=0, stdout="abc123\n", stderr=""
                        ),
                    ),
                ):
                    ref, commit, error = audit._provider_remote_head("hephaestus")

        self.assertEqual((ref, commit, error), ("origin/master", "abc123", None))

    def test_requested_provider_set_uses_twenty_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-provider-audit-") as temp:
            root = Path(temp)
            (root / ".gitmodules").write_text(
                "\n".join(
                    f'[submodule "repos/{name}"]\n\tpath = repos/{name}\n\tactive = true\n'
                    for name in audit.REQUESTED_PROVIDERS_20260814
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
                    code = audit.main(["--provider-set", "requested-2026-08-14"])

        self.assertEqual(code, 0)
        self.assertIn(
            "- 20 providers present and active in .gitmodules", output.getvalue()
        )
        self.assertNotIn("gaia", output.getvalue())

    def test_provider_alias_tychee_normalizes_to_tyche(self) -> None:
        parsed = audit.parse_args(["--providers", "tychee, horae"])
        self.assertEqual(audit._selected_providers(parsed), ("tyche", "horae"))

    def test_providers_file_takes_precedence_over_provider_inputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-provider-audit-") as temp:
            providers_path = Path(temp) / "providers.txt"
            providers_path.write_text("hermes\n", encoding="utf-8")
            parsed = audit.parse_args(
                [
                    "--provider-set",
                    "requested-2026-08-14",
                    "--providers",
                    "tychee,horae",
                    "--providers-file",
                    str(providers_path),
                ]
            )
            self.assertEqual(audit._selected_providers(parsed), ("hermes",))

    def test_providers_file_applies_aliases_and_dedupes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-provider-audit-") as temp:
            providers_path = Path(temp) / "providers.txt"
            providers_path.write_text(
                " tychee,\nTYCHE \n horae, tychee,\nhorae ",
                encoding="utf-8",
            )
            parsed = audit.parse_args(["--providers-file", str(providers_path)])
            self.assertEqual(audit._selected_providers(parsed), ("tyche", "horae"))

    def test_unreadable_providers_file_is_blocking(self) -> None:
        missing_path = Path("D:\\atlas\\does-not-exist-providers.txt")
        output = io.StringIO()
        with redirect_stdout(output):
            code = audit.main(["--providers-file", str(missing_path)])

        self.assertEqual(code, 1)
        self.assertIn("provider-integration-audit: FAIL", output.getvalue())
        self.assertIn("providers file is unreadable", output.getvalue())

    def test_main_json_success_shape(self) -> None:
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
                    code = audit.main(["--format", "json"])

        payload_text = output.getvalue().strip()
        self.assertEqual(len(payload_text.splitlines()), 1)
        payload = json.loads(payload_text)
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["provider_set"], list(audit.REQUIRED_PROVIDERS))
        self.assertEqual(payload["provider_count"], len(audit.REQUIRED_PROVIDERS))
        self.assertEqual(payload["exact_heads"], False)
        self.assertEqual(payload["structural_only"], False)
        self.assertEqual(payload["out_of_scope_coherence"], 0)
        self.assertEqual(payload["issues"], [])

    def test_main_json_failure_shape(self) -> None:
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
                    code = audit.main(["--format", "json"])

        payload_text = output.getvalue().strip()
        self.assertEqual(len(payload_text.splitlines()), 1)
        payload = json.loads(payload_text)
        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["provider_set"], list(audit.REQUIRED_PROVIDERS))
        self.assertEqual(payload["provider_count"], len(audit.REQUIRED_PROVIDERS))
        self.assertEqual(payload["exact_heads"], False)
        self.assertEqual(payload["structural_only"], False)
        self.assertEqual(payload["out_of_scope_coherence"], 0)
        self.assertIsInstance(payload["issues"], list)
        self.assertIn("repos/tyche missing `active = true`", payload["issues"])

    def test_exact_head_workers_must_be_positive(self) -> None:
        with self.assertRaises(SystemExit):
            audit.parse_args(["--exact-head-workers", "0"])


if __name__ == "__main__":
    unittest.main()
