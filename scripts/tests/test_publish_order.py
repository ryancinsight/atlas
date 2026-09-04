#!/usr/bin/env python3
"""Tests for committed-gitlink publish graph attribution."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "publish-order.py"
SPEC = importlib.util.spec_from_file_location("publish_order", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
publish_order = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publish_order)


def _git(directory: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return process.stdout


class PublishOrderTestCase(unittest.TestCase):
    def test_exact_gitlinks_ignore_dirty_provider_manifest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-order-") as temp:
            root = Path(temp) / "atlas"
            provider = root / "repos" / "demo"
            provider.mkdir(parents=True)
            _git(provider, "init", "-q")
            _git(provider, "config", "user.email", "test@example.invalid")
            _git(provider, "config", "user.name", "Atlas Test")
            manifest = provider / "Cargo.toml"
            manifest.write_text(
                '[package]\nname = "committed-demo"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )
            _git(provider, "add", "Cargo.toml")
            _git(provider, "commit", "-q", "-m", "initial")
            committed = _git(provider, "rev-parse", "HEAD").strip()

            root.mkdir(parents=True, exist_ok=True)
            _git(root, "init", "-q")
            _git(root, "config", "user.email", "test@example.invalid")
            _git(root, "config", "user.name", "Atlas Test")
            (root / ".gitmodules").write_text(
                '[submodule "demo"]\n\tpath = repos/demo\n\turl = https://example.invalid/demo.git\n',
                encoding="utf-8",
            )
            _git(root, "add", ".gitmodules")
            _git(
                root,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{committed},repos/demo",
            )
            _git(root, "commit", "-q", "-m", "record")
            (root / ".gitmodules").write_text(
                '[submodule "demo"]\n\tpath = repos/demo\n\turl = https://example.invalid/demo.git\n'
                '[submodule "dirty"]\n\tpath = repos/dirty\n\turl = https://example.invalid/dirty.git\n',
                encoding="utf-8",
            )

            manifest.write_text(
                '[package]\nname = "dirty-demo"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )

            worktree_packages, *_ = publish_order.load_graph(root)
            exact_packages, *_ = publish_order.load_graph(root, exact_gitlinks=True)

            self.assertIn("dirty-demo", worktree_packages)
            self.assertNotIn("committed-demo", worktree_packages)
            self.assertIn("committed-demo", exact_packages)
            self.assertNotIn("dirty-demo", exact_packages)
            self.assertEqual(
                exact_packages["committed-demo"]["manifest"],
                "repos/demo/Cargo.toml",
            )


class InheritedRenameTests(unittest.TestCase):
    """A workspace-inherited `package = "x"` rename must reach the order.

    Two indirections separate a dependency-table key from the registry name,
    and missing either drops an edge *silently* - a dropped edge produces a
    plausible earlier wave rather than an error, so the failure surfaces at
    publish time. `ares` is the witness that found this: its member manifest
    says `proteus.workspace = true` while the workspace root carries
    `package = "proteus-mat"`, so reading the member alone placed `ares-solid`
    a wave ahead of the crate it depends on.
    """

    ROOT = {
        "workspace": {
            "dependencies": {
                "proteus": {"package": "proteus-mat", "version": "0.1.0"},
                "plain": {"version": "1.0"},
            }
        }
    }

    def test_inherited_rename_resolves_to_the_registry_name(self) -> None:
        member = {"dependencies": {"proteus": {"workspace": True}}}
        names = publish_order.dependency_names(
            member, ("dependencies",), publish_order.workspace_dependency_table(self.ROOT)
        )
        self.assertEqual(names, {"proteus-mat"})

    def test_inherited_dependency_without_a_rename_keeps_its_key(self) -> None:
        member = {"dependencies": {"plain": {"workspace": True}}}
        names = publish_order.dependency_names(
            member, ("dependencies",), publish_order.workspace_dependency_table(self.ROOT)
        )
        self.assertEqual(names, {"plain"})

    def test_a_site_local_rename_still_wins(self) -> None:
        # `package` written at the use site is not inherited and must not be
        # overridden by the root's entry for the same key.
        member = {"dependencies": {"proteus": {"package": "other", "workspace": True}}}
        names = publish_order.dependency_names(
            member, ("dependencies",), publish_order.workspace_dependency_table(self.ROOT)
        )
        self.assertEqual(names, {"other"})

    def test_an_unknown_inherited_key_falls_back_to_itself(self) -> None:
        member = {"dependencies": {"absent": {"workspace": True}}}
        names = publish_order.dependency_names(
            member, ("dependencies",), publish_order.workspace_dependency_table(self.ROOT)
        )
        self.assertEqual(names, {"absent"})

    def test_optional_dependencies_are_skippable(self) -> None:
        # The required-only graph is what distinguishes a feature-gated cycle
        # from one in the dependencies every consumer gets.
        member = {
            "dependencies": {
                "proteus": {"workspace": True},
                "plain": {"workspace": True, "optional": True},
            }
        }
        root = publish_order.workspace_dependency_table(self.ROOT)
        self.assertEqual(
            publish_order.dependency_names(member, ("dependencies",), root),
            {"proteus-mat", "plain"},
        )
        self.assertEqual(
            publish_order.dependency_names(
                member, ("dependencies",), root, skip_optional=True
            ),
            {"proteus-mat"},
        )

    def test_a_manifest_without_a_workspace_table_yields_no_inheritance(self) -> None:
        self.assertEqual(publish_order.workspace_dependency_table({}), {})
        self.assertEqual(
            publish_order.workspace_dependency_table({"workspace": {"members": ["a"]}}), {}
        )


if __name__ == "__main__":
    unittest.main()
