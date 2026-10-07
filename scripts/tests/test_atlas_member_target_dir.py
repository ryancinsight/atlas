#!/usr/bin/env python3
"""Linked Atlas worktrees must keep member builds on the primary cache."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-member-target-dir.py"
sys.path.insert(0, str(SCRIPT.parent))
import atlas_target_dir  # noqa: E402
SPEC = importlib.util.spec_from_file_location("atlas_member_target_dir", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
target_dir = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(target_dir)


def git(directory: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def cargo_environment() -> dict[str, str]:
    """The process environment without any Cargo output-directory variable."""
    return {
        key: value for key, value in os.environ.items()
        if key not in atlas_target_dir.TARGET_ENVIRONMENT
    }


def mark_lane(path: Path) -> None:
    """Make ``path`` look like a linked worktree: a lane holds a `.git` entry."""
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")


class SharedTargetWorktreeTestCase(unittest.TestCase):
    @staticmethod
    def cargo_target(lane: Path) -> Path:
        result = subprocess.run(
            ["cargo", "metadata", "--no-deps", "--format-version", "1", "--offline"],
            cwd=lane,
            check=True,
            capture_output=True,
            text=True,
            env=cargo_environment(),
        )
        return Path(json.loads(result.stdout)["target_directory"]).resolve()

    def test_generated_member_pin_targets_the_primary_checkout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-worktree-") as temp:
            root = Path(temp) / "primary"
            lane = Path(temp) / "worktrees" / "lane"
            root.mkdir(parents=True)
            git(root, "init", "--quiet")
            git(root, "config", "user.name", "Atlas test")
            git(root, "config", "user.email", "atlas-test@example.invalid")
            (root / "README.md").write_text("fixture\n", encoding="utf-8")
            git(root, "add", "README.md")
            git(root, "commit", "--quiet", "-m", "Initialize fixture")
            lane.parent.mkdir(parents=True)
            git(root, "worktree", "add", "--quiet", "--detach", str(lane), "HEAD")
            try:
                expected = target_dir.shared_target_for(root)
                actual = target_dir.shared_target_for(lane)
                self.assertEqual(actual, expected)
                self.assertTrue(os.path.samefile(actual.parent, root))
                self.assertIn(
                    f'target-dir = "{expected.as_posix()}"', target_dir.desired(lane)
                )
                # Generated from a linked worktree, both files still name the
                # primary checkout's cache, not the worktree's own.
                self.assertIn(
                    f'target-dir = "{expected.as_posix()}"',
                    atlas_target_dir.lane_config_text(lane),
                )
                self.assertIn(
                    f'target-dir = "{expected.as_posix()}"',
                    atlas_target_dir.member_config_text(lane),
                )
            finally:
                git(root, "worktree", "remove", str(lane))

    def test_non_repository_checkout_returns_a_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-outside-") as temp:
            with self.assertRaisesRegex(RuntimeError, "cannot resolve Git common directory"):
                target_dir.shared_target_for(Path(temp))

    def test_only_a_repository_root_resolves_a_shared_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-subdirectory-") as temp:
            root = stack_repository(Path(temp).resolve())
            (root / "inside").mkdir()
            self.assertEqual(target_dir.shared_target_for(root), (root / "target").resolve())
            with self.assertRaisesRegex(RuntimeError, "cannot resolve Git common directory"):
                target_dir.shared_target_for(root / "inside")

    def test_a_common_directory_not_named_dot_git_is_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-separate-") as temp:
            base = Path(temp).resolve()
            root = stack_repository(base)
            git(root, "init", "--quiet", "--separate-git-dir", str(base / "gitdata"))
            with self.assertRaisesRegex(RuntimeError, "unexpected Git common directory"):
                target_dir.shared_target_for(root)
            self.assertIn(
                "unexpected Git common directory",
                atlas_target_dir.generation_refusal(root),
            )

    def test_lane_config_detects_missing_stale_and_foreign_states(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-lane-") as temp:
            root = Path(temp) / "stack"
            root.mkdir(parents=True)
            git(root, "init", "--quiet", "-b", "main")
            git(root, "config", "user.name", "Atlas test")
            git(root, "config", "user.email", "atlas-test@example.invalid")
            (root / "seed").write_text("seed\n", encoding="utf-8")
            git(root, "add", "seed")
            git(root, "commit", "--quiet", "-m", "seed")
            lane_config = root / "worktrees" / ".cargo" / "config.toml"
            with patch.object(target_dir, "ATLAS_ROOT", root), patch.object(
                target_dir, "LANE_CONFIG", lane_config
            ):
                self.assertEqual(target_dir.lane_state(), "absent")
                lane_config.parent.parent.mkdir()
                self.assertEqual(target_dir.lane_state(), "missing")
                target_dir.ensure_lane_config(root)
                self.assertEqual(target_dir.lane_state(), "current")
                lane_config.write_text("[build]\ntarget-dir = 'foreign'\n", encoding="utf-8")
                self.assertEqual(target_dir.lane_state(), "foreign")
                lane_config.write_text(target_dir.lane_config_text(root) + "\n", encoding="utf-8")
                self.assertEqual(target_dir.lane_state(), "stale")

    def test_lane_state_rejects_local_and_legacy_target_overrides(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-override-") as temp:
            root = Path(temp) / "stack"
            root.mkdir(parents=True)
            git(root, "init", "--quiet", "-b", "main")
            git(root, "config", "user.name", "Atlas test")
            git(root, "config", "user.email", "atlas-test@example.invalid")
            (root / "seed").write_text("seed\n", encoding="utf-8")
            git(root, "add", "seed")
            git(root, "commit", "--quiet", "-m", "seed")
            mark_lane(root / "worktrees" / "demo-lane")
            lane_path = root / "worktrees" / "demo-lane" / ".cargo"
            lane_path.mkdir(parents=True)
            with patch.object(target_dir, "ATLAS_ROOT", root), patch.object(
                target_dir, "LANE_CONFIG", root / "worktrees" / ".cargo" / "config.toml"
            ):
                (lane_path / "config.toml").write_text(
                    "[build]\ntarget-dir = 'escape-toml'\n", encoding="utf-8"
                )
                self.assertEqual(target_dir.lane_state(), "override")
                (lane_path / "config.toml").unlink()
                (lane_path / "config").write_text(
                    "[build]\ntarget-dir = 'escape-legacy'\n", encoding="utf-8"
                )
                self.assertEqual(target_dir.lane_state(), "override")
                (lane_path / "config").unlink()
                legacy = root / "worktrees" / ".cargo" / "config"
                legacy.parent.mkdir(parents=True, exist_ok=True)
                legacy.write_text("[build]\ntarget-dir = 'escape-root-legacy'\n", encoding="utf-8")
                self.assertEqual(atlas_target_dir.lane_target_overrides(root), [legacy])
                self.assertEqual(target_dir.lane_state(), "override")
                with self.assertRaisesRegex(RuntimeError, "shadows"):
                    target_dir.ensure_lane_config(root)

    def test_relative_target_dir_resolves_against_the_parent_of_the_declaring_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-relative-") as temp:
            root = Path(temp).resolve() / "stack"
            member = root / "repos" / "member"
            package = member / "crates" / "demo"
            (package / "src").mkdir(parents=True)
            (package / "src" / "lib.rs").write_text("pub fn value() {}\n", encoding="utf-8")
            (package / "Cargo.toml").write_text(
                "[package]\nname = \"demo\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
                encoding="utf-8",
            )
            (member / "Cargo.toml").write_text(
                "[workspace]\nmembers = [\"crates/demo\"]\nresolver = \"2\"\n",
                encoding="utf-8",
            )
            config = root / ".cargo" / "config.toml"
            config.parent.mkdir()
            config.write_text('[build]\ntarget-dir = "target"\n', encoding="utf-8")
            self.assertEqual(self.cargo_target(package), root / "target")
            self.assertEqual(self.cargo_target(member), root / "target")

            # An included file is the declaring file: its relative path resolves
            # against the parent of the directory holding *it*, not of the
            # `.cargo` directory that includes it.
            (root / "conf").mkdir()
            (root / "conf" / "inc.toml").write_text(
                '[build]\ntarget-dir = "inc-tgt"\n', encoding="utf-8"
            )
            config.write_text('include = ["../conf/inc.toml"]\n', encoding="utf-8")
            self.assertEqual(self.cargo_target(package), root / "inc-tgt")

    def test_cargo_resolves_all_target_dir_spellings_and_shared_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-spellings-") as temp:
            root = Path(temp) / "stack"
            lane = root / "worktrees" / "demo"
            lane.mkdir(parents=True)
            git(root, "init", "--quiet", "-b", "main")
            git(root, "config", "user.name", "Atlas test")
            git(root, "config", "user.email", "atlas-test@example.invalid")
            (lane / "Cargo.toml").write_text(
                "[package]\nname = \"demo\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
                encoding="utf-8",
            )
            (lane / "src").mkdir()
            (lane / "src" / "lib.rs").write_text("pub fn value() -> u8 { 1 }\n", encoding="utf-8")
            target_dir.ensure_lane_config(root)
            shared = target_dir.shared_target_for(root).resolve()
            generated = (root / "worktrees" / ".cargo" / "config.toml").read_text(
                encoding="utf-8"
            )
            target_dir.ensure_lane_config(root)
            self.assertEqual(
                generated,
                (root / "worktrees" / ".cargo" / "config.toml").read_text(encoding="utf-8"),
            )
            self.assertEqual(self.cargo_target(lane), shared)

            spellings = (
                "build.target-dir = 'escape-dotted'\n",
                "[build]\n\"target-dir\" = 'escape-quoted'\n",
                "build = { \"target-dir\" = 'escape-inline' }\n",
            )
            for index, spelling in enumerate(spellings):
                config = lane / ".cargo" / "config.toml"
                config.parent.mkdir(exist_ok=True)
                config.write_text(spelling, encoding="utf-8")
                self.assertEqual(atlas_target_dir.scan_lane(lane).overrides, [config])
                self.assertEqual(
                    self.cargo_target(lane),
                    (lane / f"escape-{('dotted', 'quoted', 'inline')[index]}").resolve(),
                )
                config.unlink()

            config = lane / ".cargo" / "config.toml"
            config.write_text('include = ["extra.toml"]\n', encoding="utf-8")
            (lane / ".cargo" / "extra.toml").write_text(
                "[build]\ntarget-dir = 'escape-include'\n", encoding="utf-8"
            )
            self.assertEqual(atlas_target_dir.scan_lane(lane).overrides, [config])
            self.assertEqual(self.cargo_target(lane), (lane / "escape-include").resolve())
            config.unlink()
            (lane / ".cargo" / "extra.toml").unlink()

            nested = lane / "sub" / ".cargo" / "config.toml"
            nested.parent.mkdir(parents=True)
            nested.write_text("[build]\ntarget-dir = 'escape-nested'\n", encoding="utf-8")
            self.assertEqual(atlas_target_dir.scan_lane(lane).overrides, [nested])
            self.assertEqual(self.cargo_target(lane), shared)
            self.assertEqual(
                self.cargo_target(lane / "sub"), (lane / "sub" / "escape-nested").resolve()
            )
            nested.unlink()

            legacy = root / "worktrees" / ".cargo" / "config"
            legacy.write_text("[net]\noffline = true\n", encoding="utf-8")
            self.assertEqual(self.cargo_target(lane), (lane / "target").resolve())
            with self.assertRaisesRegex(RuntimeError, "shadows"):
                target_dir.ensure_lane_config(root)


def stack_repository(base: Path) -> Path:
    root = base / "stack"
    root.mkdir(parents=True)
    git(root, "init", "--quiet", "-b", "main")
    git(root, "config", "user.name", "Atlas test")
    git(root, "config", "user.email", "atlas-test@example.invalid")
    (root / "seed").write_text("seed\n", encoding="utf-8")
    git(root, "add", "seed")
    git(root, "commit", "--quiet", "-m", "seed")
    return root


class GeneratedLaneConfigTestCase(unittest.TestCase):
    """Generation, refresh, and checking of the config every lane inherits."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-target-generate-")
        self.addCleanup(temp.cleanup)
        self.root = stack_repository(Path(temp.name))
        self.lane_config = self.root / "worktrees" / ".cargo" / "config.toml"
        self.member_config = self.root / "repos" / ".cargo" / "config.toml"
        for patcher in (
            patch.object(target_dir, "ATLAS_ROOT", self.root),
            patch.object(target_dir, "REPOS", self.root / "repos"),
            patch.object(target_dir, "CONFIG", self.member_config),
            patch.object(target_dir, "LANE_CONFIG", self.lane_config),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def run_tool(operation) -> tuple[int, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = operation()
        return status, output.getvalue()

    def test_generate_writes_both_configs(self) -> None:
        self.assertEqual(target_dir.lane_state(), "absent")
        status, _ = self.run_tool(target_dir.generate)
        self.assertEqual(status, 0)
        self.assertEqual(
            self.lane_config.read_text(encoding="utf-8"), target_dir.lane_config_text(self.root)
        )
        self.assertEqual(target_dir.lane_state(), "current")
        self.assertEqual(target_dir.state(), "current")
        self.assertEqual(self.run_tool(target_dir.check)[0], 0)

    def test_ensure_refreshes_a_stale_generated_config(self) -> None:
        target_dir.ensure_lane_config(self.root)
        self.lane_config.write_text(
            target_dir.lane_config_text(self.root) + "# edited\n", encoding="utf-8"
        )
        self.assertEqual(target_dir.lane_state(), "stale")
        target_dir.ensure_lane_config(self.root)
        self.assertEqual(
            self.lane_config.read_text(encoding="utf-8"), target_dir.lane_config_text(self.root)
        )

    def test_a_foreign_config_is_never_overwritten(self) -> None:
        self.lane_config.parent.mkdir(parents=True)
        for content in (b"[build]\ntarget-dir = 'foreign'\n", b"\xff\xfe not utf-8"):
            self.lane_config.write_bytes(content)
            with self.assertRaisesRegex(RuntimeError, "not generated by Atlas"):
                target_dir.ensure_lane_config(self.root)
            self.assertEqual(self.lane_config.read_bytes(), content)
            self.assertEqual(target_dir.lane_state(), "foreign")
            status, output = self.run_tool(target_dir.generate)
            self.assertEqual(status, 1)
            self.assertIn("left alone", output)
            self.assertEqual(self.lane_config.read_bytes(), content)

    def test_generate_refuses_while_a_lane_declares_a_target_dir(self) -> None:
        mark_lane(self.root / "worktrees" / "demo")
        override = self.root / "worktrees" / "demo" / "sub" / ".cargo" / "config.toml"
        override.parent.mkdir(parents=True)
        override.write_text("[build]\ntarget-dir = 'escape'\n", encoding="utf-8")
        status, output = self.run_tool(target_dir.generate)
        self.assertEqual(status, 1)
        self.assertIn("declares target-dir", output)
        self.assertFalse(self.lane_config.exists())

    def test_check_gates_on_the_lane_config_and_names_its_state(self) -> None:
        self.member_config.parent.mkdir(parents=True)
        self.member_config.write_text(target_dir.desired(self.root), encoding="utf-8")
        self.assertEqual(target_dir.state(), "current")
        self.assertEqual(self.run_tool(target_dir.check)[0], 0)  # fresh clone: no lanes yet
        self.lane_config.parent.parent.mkdir()
        status, output = self.run_tool(target_dir.check)
        self.assertEqual(status, 1)
        self.assertIn("lane target config missing", output)
        self.lane_config.parent.mkdir()
        self.lane_config.write_text("[build]\ntarget-dir = 'x'\n", encoding="utf-8")
        status, output = self.run_tool(target_dir.check)
        self.assertEqual(status, 1)
        self.assertIn("lane target config foreign", output)
        self.lane_config.write_text(
            target_dir.lane_config_text(self.root) + "\n", encoding="utf-8"
        )
        status, output = self.run_tool(target_dir.check)
        self.assertEqual(status, 1)
        self.assertIn("lane target config stale", output)
        mark_lane(self.root / "worktrees" / "demo")
        override = self.root / "worktrees" / "demo" / ".cargo" / "config"
        override.parent.mkdir(parents=True)
        override.write_text("build.target-dir = 'x'\n", encoding="utf-8")
        status, output = self.run_tool(target_dir.check)
        self.assertEqual(status, 1)
        self.assertIn("lane target config override", output)
        self.assertIn("override: worktrees/demo/.cargo/config", output)

    def test_lane_state_counts_nested_included_and_unparseable_overrides(self) -> None:
        target_dir.ensure_lane_config(self.root)
        lane = self.root / "worktrees" / "demo"
        mark_lane(lane)
        for relative, text in (
            ("sub/.cargo/config.toml", "[build]\ntarget-dir = 'x'\n"),
            (".cargo/config.toml", "[build]\nbuild-dir = 'x'\n"),
            (".cargo/config.toml", 'include = ["more.toml"]\n'),
            (".cargo/config", "[build\n"),
        ):
            path = lane / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            (lane / ".cargo").mkdir(exist_ok=True)
            (lane / ".cargo" / "more.toml").write_text(
                "[build]\ntarget-dir = 'y'\n", encoding="utf-8"
            )
            path.write_text(text, encoding="utf-8")
            self.assertEqual(target_dir.lane_state(), "override", relative)
            path.unlink()
        self.assertEqual(target_dir.lane_state(), "current")

    def test_a_foreign_member_config_is_never_overwritten(self) -> None:
        self.member_config.parent.mkdir(parents=True)
        for content in (b"[build]\ntarget-dir = 'foreign'\n", b"\xff\xfe not utf-8"):
            self.member_config.write_bytes(content)
            self.assertEqual(target_dir.state(), "foreign")
            with self.assertRaisesRegex(RuntimeError, "not generated by Atlas"):
                atlas_target_dir.ensure_member_config(self.root)
            status, output = self.run_tool(target_dir.generate)
            self.assertEqual(status, 1)
            self.assertIn("left alone", output)
            self.assertEqual(self.member_config.read_bytes(), content)
            self.assertFalse(self.lane_config.exists())

    def test_a_stale_member_config_is_refreshed(self) -> None:
        atlas_target_dir.ensure_member_config(self.root)
        self.member_config.write_text(
            target_dir.desired(self.root) + "# edited\n", encoding="utf-8"
        )
        self.assertEqual(target_dir.state(), "stale")
        status, _ = self.run_tool(target_dir.generate)
        self.assertEqual(status, 0)
        self.assertEqual(target_dir.state(), "current")

    def test_scratch_directories_in_the_lane_root_are_not_lanes(self) -> None:
        scratch = self.root / "worktrees" / "report" / ".cargo" / "config.toml"
        scratch.parent.mkdir(parents=True)
        scratch.write_text("[build]\ntarget-dir = 'x'\n", encoding="utf-8")
        self.assertEqual(atlas_target_dir.lane_checkouts(self.root), [])
        status, _ = self.run_tool(target_dir.generate)
        self.assertEqual(status, 0)
        self.assertEqual(target_dir.lane_state(), "current")
        mark_lane(self.root / "worktrees" / "report")
        self.assertEqual(atlas_target_dir.lane_checkouts(self.root), [self.root / "worktrees" / "report"])
        self.assertEqual(target_dir.lane_state(), "override")

    def test_the_generated_config_and_archives_are_not_lanes(self) -> None:
        target_dir.ensure_lane_config(self.root)
        archived = self.root / "worktrees" / ".archive" / "old" / ".cargo" / "config.toml"
        archived.parent.mkdir(parents=True)
        archived.write_text("[build]\ntarget-dir = 'x'\n", encoding="utf-8")
        self.assertEqual(atlas_target_dir.lane_target_overrides(self.root), [])
        self.assertEqual(target_dir.lane_state(), "current")


class EnvironmentOverrideTestCase(unittest.TestCase):
    def test_only_a_variable_that_leaves_the_shared_target_is_reported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-environment-") as temp:
            shared = Path(temp).resolve() / "target"
            found = atlas_target_dir.environment_target_overrides
            self.assertEqual(found({}, shared), [])
            self.assertEqual(found({"CARGO_TARGET_DIR": str(shared)}, shared), [])
            self.assertEqual(found({"CARGO_TARGET_DIR": ""}, shared), [])
            self.assertEqual(
                found({"CARGO_TARGET_DIR": "target"}, shared), ["CARGO_TARGET_DIR=target"]
            )
            other = str(Path(temp).resolve() / "elsewhere")
            self.assertEqual(
                found({"CARGO_BUILD_TARGET_DIR": other}, shared),
                [f"CARGO_BUILD_TARGET_DIR={other}"],
            )
            self.assertEqual(
                found({"CARGO_BUILD_BUILD_DIR": "private"}, shared),
                ["CARGO_BUILD_BUILD_DIR=private"],
            )

    def test_a_relative_value_is_rejected_even_when_it_would_reach_the_shared_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-relative-env-") as temp:
            base = Path(temp).resolve()
            shared = base / "target"
            shared.mkdir()
            previous = Path.cwd()
            os.chdir(base)
            try:
                found = atlas_target_dir.environment_target_overrides(
                    {"CARGO_TARGET_DIR": "target"}, shared
                )
            finally:
                os.chdir(previous)
            self.assertEqual(found, ["CARGO_TARGET_DIR=target"])


if __name__ == "__main__":
    unittest.main()
