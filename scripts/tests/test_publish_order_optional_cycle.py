#!/usr/bin/env python3
"""Tests for the optional-dependency cycle gate (ADR 0060).

`cargo publish` does not require an optional dependency to be on the
registry at publish time: the published metadata records the dep
string and an `optional` flag, and resolution is gated to the feature.
A cycle that closes only through optional edges is therefore not a
real cycle, because no `cargo build --features <...>` line ever
co-enables both ends, and the required-only graph orders.

The script separates the two cycle shapes in its textual output
already; this file proves the exit code matches.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "publish-order.py"


def _git(directory: Path, *arguments: str) -> str:
    """Run a git command in `directory` and return its stdout."""
    process = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    return process.stdout


def _run_with_members(members: dict[str, dict[str, bool]]) -> subprocess.CompletedProcess:
    """Build an Atlas root, run the CLI, return the completed process.

    `members` maps a recorded member name to a dict whose keys are
    sibling `[package] name` values; the value is `True` for an
    optional edge and `False` for a required edge.
    """
    with tempfile.TemporaryDirectory(prefix="atlas-publish-order-") as temp:
        root = Path(temp)
        members_root = root / "repos"
        members_root.mkdir(parents=True)

        # The atlas root must be a git repo for `update-index` to
        # accept the cacheinfo writes below.
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "test@example.invalid")
        _git(root, "config", "user.name", "Atlas Test")

        for member, deps in members.items():
            provider = members_root / member
            provider.mkdir()
            _git(provider, "init", "-q")
            _git(provider, "config", "user.email", "test@example.invalid")
            _git(provider, "config", "user.name", "Atlas Test")

            # Each member depends on every sibling it names. The
            # `optional = true|false` flag is the test's input.
            dep_lines = "\n".join(
                f'{dep} = {{ workspace = true, optional = {str(optional).lower()} }}'
                for dep, optional in deps.items()
            )
            manifest_path = provider / "Cargo.toml"
            manifest_path.write_text(
                '[package]\n'
                f'name = "{member}"\n'
                'version = "0.1.0"\n'
                '[dependencies]\n'
                + dep_lines + "\n",
                encoding="utf-8",
            )

            _git(provider, "add", "Cargo.toml")
            _git(provider, "commit", "-q", "-m", "seed")
            revision = _git(provider, "rev-parse", "HEAD").strip()

            # Record the member in the parent root so the script's
            # `.gitmodules` reader finds it.
            with (root / ".gitmodules").open("a", encoding="utf-8") as gitmodules:
                gitmodules.write(
                    f'[submodule "{member}"]\n'
                    f'\tpath = repos/{member}\n'
                    f'\turl = https://example.invalid/{member}.git\n'
                )
            subprocess.run(
                [
                    "git", "-C", str(root), "update-index", "--add", "--cacheinfo",
                    f"160000,{revision},repos/{member}",
                ],
                check=True, capture_output=True,
            )

        return subprocess.run(
            ["python", str(SCRIPT), "--root", str(root), "--json"],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )


class OptionalCycleGateTests(unittest.TestCase):
    """ADR 0060: optional edges are not publish-order constraints."""

    def test_optional_only_cycle_exits_zero(self) -> None:
        """Cycle through optional edges: required graph acyclic, exit 0."""
        process = _run_with_members({
            "a": {"b": True},
            "b": {"a": True},
        })
        self.assertEqual(
            process.returncode, 0,
            msg=f"optional-only cycle must not block:\n{process.stdout}\n{process.stderr}",
        )
        payload = json.loads(process.stdout)
        # The discriminator is False (no required edge closes a cycle).
        self.assertFalse(payload["unresolved_includes_required"])
        self.assertEqual(payload["required_unresolved"], [])
        # The full graph still has the cycle, so neither crate reaches a
        # layer — the cycle is recorded in `unresolved` as
        # informational output and the exit code is 0.
        self.assertEqual(set(payload["unresolved"]), {"a", "b"})
        self.assertEqual(payload["layers"], [])

    def test_required_cycle_exits_one(self) -> None:
        """Cycle through required edges: exit 1, the discriminator fires."""
        process = _run_with_members({
            "a": {"b": False},
            "b": {"a": False},
        })
        self.assertEqual(
            process.returncode, 1,
            msg=f"required cycle must block:\n{process.stdout}\n{process.stderr}",
        )
        payload = json.loads(process.stdout)
        self.assertTrue(payload["unresolved_includes_required"])
        self.assertEqual(set(payload["required_unresolved"]), {"a", "b"})

    def test_no_cycle_exits_zero(self) -> None:
        """Linear chain with no optional edges: exit 0, three layers."""
        process = _run_with_members({
            "leaf": {},
            "middle": {"leaf": False},
            "root_pkg": {"middle": False},
        })
        self.assertEqual(process.returncode, 0)
        payload = json.loads(process.stdout)
        self.assertEqual(payload["required_unresolved"], [])
        self.assertEqual(len(payload["layers"]), 3)
        self.assertEqual(payload["layers"][0], ["leaf"])


if __name__ == "__main__":
    unittest.main()