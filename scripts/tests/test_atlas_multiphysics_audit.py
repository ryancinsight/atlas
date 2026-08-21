#!/usr/bin/env python3
"""Focused tests for the Atlas multiphysics contract audit."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-multiphysics-audit.py"
SPEC = importlib.util.spec_from_file_location("atlas_multiphysics_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def _git(directory: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return process.stdout


class MultiphysicsAuditTestCase(unittest.TestCase):
    def test_dependency_names_include_workspace_and_package_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "Cargo.toml"
            manifest.write_text(
                """
[workspace.dependencies]
harmonia = { git = "https://example.invalid/harmonia" }

[dependencies]
hyperion = "0.1"
""",
                encoding="utf-8",
            )
            self.assertEqual(audit._dependency_names(manifest), {"harmonia", "hyperion"})

    def test_dependency_match_accepts_package_prefixes(self) -> None:
        self.assertTrue(audit._matches_dependency({"apollo-fft"}, "apollo"))
        self.assertFalse(audit._matches_dependency({"apollox"}, "apollo"))

    def test_book_fence_counts_excludes_non_runnable_attributes(self) -> None:
        total, runnable = audit._book_fence_counts(
            "```rust,ignore\nfn ignored() {}\n```\n"
            "```rust,no_run\nfn not_run() {}\n```\n"
            "```rust\nfn run() {}\n```\n"
        )
        self.assertEqual((total, runnable), (3, 1))

    def test_python_typing_evidence_excludes_derived_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            provider = Path(temp)
            (provider / "dist").mkdir()
            (provider / "dist" / "py.typed").write_text("", encoding="utf-8")
            (provider / "target").mkdir()
            (provider / "target" / "generated.pyi").write_text("", encoding="utf-8")
            self.assertEqual(audit._python_typing_evidence(provider), (False, False))

            (provider / "package").mkdir()
            (provider / "package" / "py.typed").write_text("", encoding="utf-8")
            (provider / "package" / "api.pyi").write_text("", encoding="utf-8")
            self.assertEqual(audit._python_typing_evidence(provider), (True, True))

    def test_source_scan_prunes_derived_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            provider = Path(temp)
            (provider / "src").mkdir()
            (provider / "src" / "lib.rs").write_text("", encoding="utf-8")
            (provider / "target" / "debug").mkdir(parents=True)
            (provider / "target" / "debug" / "generated.rs").write_text("", encoding="utf-8")
            (provider / ".venv" / "lib").mkdir(parents=True)
            (provider / ".venv" / "lib" / "generated.py").write_text("", encoding="utf-8")

            self.assertEqual(audit._source_files(provider), [provider / "src" / "lib.rs"])

    def test_audit_reports_missing_gil_release_without_claiming_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            provider = root / "repos" / "CFDrs"
            (provider / "docs" / "book" / "src").mkdir(parents=True)
            (provider / "docs" / "book" / "book.toml").write_text("[book]\ntitle='x'\n", encoding="utf-8")
            (provider / "docs" / "book" / "src" / "SUMMARY.md").write_text(
                "# Summary\n- [Intro](intro.md)\n", encoding="utf-8"
            )
            (provider / "docs" / "book" / "src" / "intro.md").write_text(
                "```rust\nfn main() {}\n```\n", encoding="utf-8"
            )
            (provider / "Cargo.toml").write_text(
                """
[dependencies]
pyo3 = "0.29"
harmonia = "0.1"
""",
                encoding="utf-8",
            )
            (provider / "src.rs").write_text(
                "#[pyclass]\nfn analytical_reference() {}\n// differential benchmark\n#![forbid(unsafe_code)]\n",
                encoding="utf-8",
            )
            with patch.object(audit, "ROOT", root):
                report = audit._audit_profile(audit.PROFILES[0])

        self.assertEqual(report["status"], "fail")
        self.assertIn("no explicit GIL-release site discovered", report["findings"])
        self.assertIn("no source py.typed marker discovered", report["findings"])
        self.assertIn("no Python typing stub discovered", report["findings"])
        self.assertIn("no Tyche source reference discovered", report["findings"])

    def test_profiles_cover_all_three_integrators(self) -> None:
        self.assertEqual({profile.name for profile in audit.PROFILES}, {"CFDrs", "helios", "kwavers"})
        self.assertIn("wgpu", audit.PROFILES[0].forbidden_dependencies)
        self.assertTrue(all("tyche" in profile.required_dependencies for profile in audit.PROFILES))

    def test_require_attribution_rejects_dirty_or_drifted_checkout(self) -> None:
        report = {
            "provider": "CFDrs",
            "status": "ok",
            "findings": [],
            "checkout_dirty": True,
            "checkout_revision": "a" * 40,
            "committed_gitlink": "b" * 40,
        }
        audit._require_attribution([report])
        self.assertEqual(report["status"], "fail")
        self.assertEqual(len(report["findings"]), 2)

    def test_committed_snapshot_excludes_dirty_provider_edits(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            provider = Path(temp) / "provider"
            provider.mkdir()
            _git(provider, "init", "-q")
            _git(provider, "config", "user.email", "test@example.invalid")
            _git(provider, "config", "user.name", "Atlas Test")
            manifest = provider / "Cargo.toml"
            manifest.write_text(
                '[package]\nname = "committed-provider"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )
            _git(provider, "add", "Cargo.toml")
            _git(provider, "commit", "-q", "-m", "initial")
            revision = _git(provider, "rev-parse", "HEAD").strip()
            manifest.write_text(
                '[package]\nname = "dirty-provider"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )

            snapshot = Path(temp) / "snapshot"
            audit._extract_committed_provider(provider, revision, snapshot)
            manifest_text = (snapshot / "Cargo.toml").read_text(encoding="utf-8")
            self.assertIn('name = "committed-provider"', manifest_text)
            self.assertNotIn('name = "dirty-provider"', manifest_text)

            exact_snapshot = {
                **audit._read_committed_files(provider, revision),
                "docs/book/book.toml": "[book]\ntitle = 'x'\n",
                "docs/book/src/intro.md": "```rust\nfn main() {}\n```\n",
            }

            report = audit._audit_profile(
                audit.IntegratorProfile("demo", ()),
                provider=Path(temp) / "unmaterialized-snapshot",
                committed_gitlink=revision,
                snapshot=exact_snapshot,
            )
            self.assertEqual(report["source"], "committed_gitlinks")
            self.assertFalse(report["checkout_dirty"])
            self.assertEqual(report["checkout_revision"], revision)
            self.assertTrue(report["book"])


if __name__ == "__main__":
    unittest.main()
