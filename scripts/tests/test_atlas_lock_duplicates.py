#!/usr/bin/env python3
"""Tests for the cross-member duplicate crate version audit.

Everything is local: fixture locks live in throwaway directories, no
network, no cargo, no registry. The real member locks are exercised by
running the script itself, not by this suite.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-lock-duplicates.py"
SPEC = importlib.util.spec_from_file_location("atlas_lock_duplicates", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def make_lock(packages: list[tuple[str, str, str | None]]) -> str:
    """Minimal Cargo.lock text for (name, version, source-or-None) rows."""
    blocks = ["# fixture lock", 'version = 4', ""]
    for name, version, source in packages:
        blocks.append("[[package]]")
        blocks.append(f'name = "{name}"')
        blocks.append(f'version = "{version}"')
        if source is not None:
            blocks.append(f'source = "{source}"')
        blocks.append("")
    return "\n".join(blocks)


REGISTRY = "registry+https://github.com/rust-lang/crates.io-index"


class DuplicateAuditTestCase(unittest.TestCase):
    """Two fixture members with controlled lock contents."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def member(self, name: str, lock_text: str | None) -> Path:
        member = self.root / name
        member.mkdir(parents=True, exist_ok=True)
        if lock_text is not None:
            (member / "Cargo.lock").write_text(lock_text, encoding="utf-8")
        return member

    def test_shared_version_is_not_a_duplicate(self) -> None:
        first = self.member(
            "alpha", make_lock([("serde", "1.0.219", REGISTRY)])
        )
        second = self.member(
            "beta", make_lock([("serde", "1.0.219", REGISTRY)])
        )
        result = audit.audit_members([first, second])
        self.assertEqual(result.rows, [])
        self.assertEqual(result.errors, [])
        self.assertEqual(result.members_audited, ["alpha", "beta"])

    def test_two_versions_across_members_is_one_row(self) -> None:
        first = self.member(
            "alpha", make_lock([("serde", "1.0.210", REGISTRY)])
        )
        second = self.member(
            "beta", make_lock([("serde", "1.0.219", REGISTRY)])
        )
        result = audit.audit_members([first, second])
        self.assertEqual(len(result.rows), 1)
        row = result.rows[0]
        self.assertEqual(row.name, "serde")
        self.assertEqual(
            row.versions["1.0.210"]["members"], ["alpha"]
        )
        self.assertEqual(
            row.versions["1.0.219"]["members"], ["beta"]
        )

    def test_three_versions_all_appear(self) -> None:
        members = [
            self.member(
                name, make_lock([("tokio", version, REGISTRY)])
            )
            for name, version in (
                ("alpha", "1.40.0"),
                ("beta", "1.43.0"),
                ("gamma", "1.47.1"),
            )
        ]
        result = audit.audit_members(members)
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(
            sorted(result.rows[0].versions), ["1.40.0", "1.43.0", "1.47.1"]
        )

    def test_missing_lock_is_skipped_openly(self) -> None:
        first = self.member(
            "alpha", make_lock([("serde", "1.0.219", REGISTRY)])
        )
        second = self.member("beta", None)
        result = audit.audit_members([first, second])
        self.assertEqual(result.rows, [])
        self.assertEqual(result.members_skipped, ["beta"])
        self.assertEqual(result.errors, [])

    def test_unparseable_lock_is_an_error(self) -> None:
        first = self.member("alpha", "not = [valid toml")
        result = audit.audit_members([first])
        self.assertEqual(result.rows, [])
        self.assertEqual(len(result.errors), 1)
        self.assertIn("alpha", result.errors[0])

    def test_json_output_parses_and_names_members(self) -> None:
        first = self.member(
            "alpha", make_lock([("serde", "1.0.210", REGISTRY)])
        )
        second = self.member(
            "beta", make_lock([("serde", "1.0.219", REGISTRY)])
        )
        result = audit.audit_members([first, second])
        import json

        payload = json.loads(audit.render_json(result))
        self.assertEqual(len(payload["duplicates"]), 1)
        self.assertEqual(payload["duplicates"][0]["name"], "serde")

    def test_main_exit_codes(self) -> None:
        from unittest import mock

        first = self.member(
            "alpha", make_lock([("serde", "1.0.210", REGISTRY)])
        )
        second = self.member(
            "beta", make_lock([("serde", "1.0.219", REGISTRY)])
        )
        with (
            mock.patch.object(audit, "registered_members", return_value=[first, second]),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(audit.main([]), 0)
            self.assertEqual(audit.main(["--fail-on-duplicates"]), 2)
            self.assertEqual(audit.main(["--member", "alpha"]), 0)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(audit.main(["--member", "no-such-member"]), 1)


if __name__ == "__main__":
    unittest.main()
