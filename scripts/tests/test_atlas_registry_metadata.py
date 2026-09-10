#!/usr/bin/env python3
"""Tests for publishable Cargo manifest metadata validation."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-registry-metadata.py"
SPEC = importlib.util.spec_from_file_location("atlas_registry_metadata", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
registry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class RegistryMetadataTestCase(unittest.TestCase):
    def test_root_package_resolves_its_workspace_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-registry-") as temp:
            root = Path(temp)
            manifest = root / "repos" / "metis" / "Cargo.toml"
            _write(
                manifest,
                """
[package]
name = "metis"
description.workspace = true
license.workspace = true

[workspace]
[workspace.package]
description = "A presentation host"
license = "MIT OR Apache-2.0"
""".lstrip(),
            )

            with patch.object(registry, "REPO_ROOT", root):
                violations, unverified = registry.check_manifest(manifest, set())

        self.assertEqual(violations, [])
        self.assertEqual(unverified, [])

    def test_member_resolves_metadata_from_ancestor_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-registry-") as temp:
            root = Path(temp)
            workspace = root / "repos" / "metis" / "Cargo.toml"
            member = root / "repos" / "metis" / "crates" / "core" / "Cargo.toml"
            _write(
                workspace,
                """
[workspace]
[workspace.package]
description = "A presentation host"
license = "MIT OR Apache-2.0"
""".lstrip(),
            )
            _write(
                member,
                """
[package]
name = "metis-core"
description.workspace = true
license.workspace = true
""".lstrip(),
            )

            with patch.object(registry, "REPO_ROOT", root):
                violations, unverified = registry.check_manifest(member, set())

        self.assertEqual(violations, [])
        self.assertEqual(unverified, [])


if __name__ == "__main__":
    unittest.main()
