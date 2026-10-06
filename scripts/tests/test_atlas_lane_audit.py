#!/usr/bin/env python3
"""Focused tests for lane-root violation classification."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-lane-audit.py"
SPEC = importlib.util.spec_from_file_location("atlas_lane_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
lane = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lane
SPEC.loader.exec_module(lane)
import atlas_stack  # noqa: E402  (importable once the audit script has extended sys.path)
import atlas_target_dir  # noqa: E402


def git(repo: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *arguments],
        check=True, capture_output=True,
    )


def init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    (root / "seed").write_text("seed\n", encoding="utf-8")
    git(root, "add", "seed")
    git(root, "commit", "-q", "-m", "seed")


def clean_environment():
    """Patch the process environment without any Cargo target variable."""
    environment = {
        key: value for key, value in os.environ.items()
        if key not in atlas_target_dir.TARGET_ENVIRONMENT
    }
    return patch.dict(os.environ, environment, clear=True)


def run_main() -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        status = lane.main()
    return status, output.getvalue()


SIGNATURE = "Signature: 8a477f597d28d172789f06886806bc55\n"
CARGO_TAG = SIGNATURE + "# This file is a cache directory tag created by cargo.\n"
OTHER_TAGS = {
    ".pytest_cache": SIGNATURE + "# This file is a cache directory tag created by pytest.\n",
    ".ruff_cache": SIGNATURE,
    ".mypy_cache": SIGNATURE + "# This file is a cache directory tag automatically created by mypy.\n",
}


class LaneTargetAuditTestCase(unittest.TestCase):
    """The audit must see everything that can send a lane build off the shared cache."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="atlas-lane-target-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "stack"
        init_repo(self.root)
        self.member = self.root / "repos" / "m"
        init_repo(self.member)
        self.lane = self.root / "worktrees" / "m-demo"
        git(self.member, "worktree", "add", "-q", "-b", "demo", str(self.lane))
        for patcher in (
            patch.object(lane, "ROOT", self.root),
            patch.object(lane, "LANE_ROOT", self.root / "worktrees"),
            patch.object(lane, "canonical_lane", lambda path: True),
            patch.object(lane, "registered_members", lambda: [self.member]),
            clean_environment(),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def audit_repo(self, repo: Path | None = None) -> list[str]:
        violations: list[str] = []
        lane.audit_repo(self.member if repo is None else repo, violations)
        return violations

    def write(self, relative: str, text: str, base: Path | None = None) -> Path:
        path = (self.lane if base is None else base) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_a_clean_registered_lane_passes(self) -> None:
        self.assertEqual(self.audit_repo(), [])

    def test_registered_lane_config_override_is_reported(self) -> None:
        config = self.write(".cargo/config.toml", "[build]\ntarget-dir = 'escape'\n")
        violations = self.audit_repo()
        self.assertEqual(len(violations), 1)
        self.assertIn(f"override: {config}", violations[0])
        self.assertIn("declares build.target-dir", violations[0])

    def test_build_dir_is_an_output_root_too(self) -> None:
        config = self.write(".cargo/config.toml", "[build]\nbuild-dir = 'private-build'\n")
        violations = self.audit_repo()
        self.assertEqual(len(violations), 1)
        self.assertIn(f"override: {config}", violations[0])
        self.assertIn("declares build.build-dir", violations[0])

    def test_nested_config_override_is_reported(self) -> None:
        config = self.write("sub/.cargo/config", "build.target-dir = 'escape'\n")
        violations = self.audit_repo()
        self.assertEqual(len(violations), 1)
        self.assertIn(f"override: {config}", violations[0])

    def test_included_override_is_reported_and_include_cycles_terminate(self) -> None:
        self.write(".cargo/extra.toml", "[build]\ntarget-dir = 'escape'\n")
        config = self.write(
            ".cargo/config.toml",
            'include = ["extra.toml", { path = "gone.toml", optional = true }]\n',
        )
        violations = self.audit_repo()
        self.assertEqual(len(violations), 1)
        self.assertIn(f"override: {config}", violations[0])
        self.assertIn("includes", violations[0])
        self.assertIn("extra.toml", violations[0])
        (self.lane / ".cargo" / "extra.toml").write_text(
            'include = ["config.toml"]\n', encoding="utf-8"
        )
        self.assertEqual(self.audit_repo(), [])

    def test_table_form_include_is_followed(self) -> None:
        self.write("conf/extra.toml", "[build]\ntarget-dir = 'escape'\n")
        config = self.write(
            ".cargo/config.toml",
            'include = [{ path = "../conf/extra.toml", optional = true }]\n',
        )
        violations = self.audit_repo()
        self.assertEqual(len(violations), 1)
        self.assertIn(f"override: {config}", violations[0])
        self.assertIn("extra.toml", violations[0])

    def test_unparseable_config_is_reported_not_ignored(self) -> None:
        config = self.write(".cargo/config.toml", "[build\n")
        violations = self.audit_repo()
        self.assertEqual(len(violations), 1)
        self.assertIn(f"override: {config}", violations[0])
        self.assertIn("cannot be read or parsed", violations[0])
        config.write_bytes(b"\xff\xfe[build]\n")
        self.assertIn("cannot be read or parsed", self.audit_repo()[0])

    def test_cargo_output_directories_are_reported_at_any_depth(self) -> None:
        for relative in ("target", "crates/foo/target", "fuzz/target"):
            self.write(f"{relative}/CACHEDIR.TAG", CARGO_TAG)
        violations = self.audit_repo()
        self.assertEqual(len(violations), 3)
        self.assertTrue(all("Cargo output directory" in item for item in violations))
        for relative in ("target", "crates/foo/target", "fuzz/target"):
            expected = str(self.lane / Path(relative))
            self.assertTrue(any(item.endswith(expected) for item in violations), relative)

    def test_cargo_layout_without_a_tag_is_recognized(self) -> None:
        self.write("first/debug/.fingerprint/unit", "x")
        self.write("second/.rustc_info.json", "{}")
        self.assertEqual(len(self.audit_repo()), 2)

    def test_other_tools_caches_are_not_cargo_caches(self) -> None:
        for name, text in OTHER_TAGS.items():
            self.write(f"{name}/CACHEDIR.TAG", text)
        self.write("deep/.pytest_cache/CACHEDIR.TAG", OTHER_TAGS[".pytest_cache"])
        self.assertEqual(self.audit_repo(), [])

    def test_an_unreadable_tag_is_reported_as_a_cargo_directory(self) -> None:
        self.write("opaque/CACHEDIR.TAG", CARGO_TAG)
        read_text = Path.read_text

        def unreadable(path: Path, *arguments, **keywords):
            if path.name == "CACHEDIR.TAG":
                raise PermissionError(path)
            return read_text(path, *arguments, **keywords)

        with patch.object(Path, "read_text", unreadable):
            violations = self.audit_repo()
        self.assertEqual(len(violations), 1)
        self.assertTrue(violations[0].endswith(str(self.lane / "opaque")))

    def test_a_config_inside_another_tools_cache_is_still_scanned(self) -> None:
        config = self.write(
            ".ruff_cache/nested/.cargo/config.toml", "[build]\ntarget-dir = 'escape'\n"
        )
        self.write(".ruff_cache/CACHEDIR.TAG", SIGNATURE)
        violations = self.audit_repo()
        self.assertEqual(len(violations), 1)
        self.assertIn(f"override: {config}", violations[0])

    def test_plain_target_directories_are_not_caches(self) -> None:
        (self.lane / "target").mkdir()
        self.write("src/target/mod.rs", "// source directory named target\n")
        self.assertEqual(self.audit_repo(), [])

    def test_the_scan_does_not_descend_below_a_cargo_directory(self) -> None:
        self.write("target/CACHEDIR.TAG", CARGO_TAG)
        self.write("target/debug/inner/CACHEDIR.TAG", CARGO_TAG)
        self.write("target/x/.cargo/config.toml", "[build]\ntarget-dir = 'inside-cache'\n")
        violations = self.audit_repo()
        self.assertEqual(len(violations), 1)
        self.assertTrue(violations[0].endswith(str(self.lane / "target")))

    def test_every_registered_lane_is_scanned(self) -> None:
        second = self.root / "worktrees" / "m-second"
        git(self.member, "worktree", "add", "-q", "-b", "second", str(second))
        first_config = self.write(".cargo/config.toml", "[build]\ntarget-dir = 'a'\n")
        second_config = self.write(
            ".cargo/config.toml", "[build]\ntarget-dir = 'b'\n", base=second
        )
        violations = self.audit_repo()
        self.assertTrue(any(f"override: {first_config}" in item for item in violations))
        self.assertTrue(any(f"override: {second_config}" in item for item in violations))

    def test_an_umbrella_lane_is_reported_for_closing_not_scanned(self) -> None:
        umbrella_lane = self.root / "worktrees" / "stack-demo"
        git(self.root, "worktree", "add", "-q", "-b", "umbrella-demo", str(umbrella_lane))
        self.write(".cargo/config.toml", '[build]\ntarget-dir = "target"\n', base=umbrella_lane)
        self.write("target/CACHEDIR.TAG", CARGO_TAG, base=umbrella_lane)
        violations = self.audit_repo(self.root)
        self.assertEqual(len(violations), 1)
        self.assertIn("umbrella lane", violations[0])
        self.assertIn("opens no lanes", violations[0])
        self.assertIn("close", violations[0])

    def test_a_lane_outside_the_canonical_roots_is_reported(self) -> None:
        with patch.object(lane, "canonical_lane", atlas_stack.canonical_lane):
            violations = self.audit_repo()
            self.assertEqual(len(violations), 1)
            self.assertIn("outside canonical lane roots", violations[0])
            self.assertIn(str(self.lane), violations[0])
            harness = self.member / ".claude" / "worktrees" / "harness"
            git(self.member, "worktree", "remove", str(self.lane))
            git(self.member, "worktree", "add", "-q", "-b", "harness", str(harness))
            self.assertEqual(self.audit_repo(), [])

    def test_symlinks_and_junctions_are_not_entered(self) -> None:
        outside = Path(self.temp.name).resolve() / "outside"
        self.write(".cargo/config.toml", "[build]\ntarget-dir = 'escape'\n", base=outside)
        self.write("target/CACHEDIR.TAG", CARGO_TAG, base=outside)
        link = self.lane / "linked"
        try:
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(str(outside), str(link))
            else:
                link.symlink_to(outside, target_is_directory=True)
        except (ImportError, OSError, AttributeError):
            self.skipTest("this host cannot create a junction or symlink")
        self.assertTrue(atlas_target_dir._redirects(link))
        self.assertFalse(atlas_target_dir._redirects(self.lane / ".git"))
        self.assertEqual(self.audit_repo(), [])

    def test_audit_main_checks_the_generated_config_and_the_environment(self) -> None:
        status, output = run_main()
        self.assertEqual(status, 1)
        self.assertIn("lane target config missing", output)
        config = self.root / "worktrees" / ".cargo" / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text(lane.lane_config_text(self.root), encoding="utf-8", newline="\n")
        status, output = run_main()
        self.assertEqual(status, 0, output)
        shared = lane.shared_target_for(self.root)
        with patch.dict(os.environ, {"CARGO_TARGET_DIR": str(shared)}):
            status, output = run_main()
        self.assertEqual(status, 0, output)
        for name in ("CARGO_TARGET_DIR", "CARGO_BUILD_TARGET_DIR", "CARGO_BUILD_BUILD_DIR"):
            with patch.dict(os.environ, {name: "relative-target"}):
                status, output = run_main()
            self.assertEqual(status, 1, name)
            self.assertIn(f"{name}=relative-target", output)

    def test_a_host_without_a_lane_root_needs_no_generated_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lane-fresh-") as temp:
            fresh = Path(temp)
            init_repo(fresh)
            with patch.object(lane, "ROOT", fresh):
                violations: list[str] = []
                lane.audit_target_config(violations)
        self.assertEqual(violations, [])

    def test_the_generated_config_directory_is_not_a_lane(self) -> None:
        config = self.root / "worktrees" / ".cargo" / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text(lane.lane_config_text(self.root), encoding="utf-8")
        violations: list[str] = []
        lane.audit_lane_root(violations)
        self.assertEqual(violations, [])


class LaneRootAuditTestCase(unittest.TestCase):
    def test_target_config_reports_missing_stale_and_foreign(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lane-config-") as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
            (root / "worktrees").mkdir()
            config = root / "worktrees" / ".cargo" / "config.toml"
            violations: list[str] = []
            with patch.object(lane, "ROOT", root):
                lane.audit_target_config(violations)
                self.assertIn("missing", violations[0])
                config.parent.mkdir(parents=True)
                config.write_text("[build]\ntarget-dir = 'foreign'\n", encoding="utf-8")
                violations.clear()
                lane.audit_target_config(violations)
                self.assertIn("foreign", violations[0])
                config.write_text(lane.lane_config_text(root) + "\n", encoding="utf-8")
                violations.clear()
                lane.audit_target_config(violations)
                self.assertIn("stale", violations[0])

                legacy = root / "worktrees" / ".cargo" / "config"
                legacy.write_text("[build]\ntarget-dir = 'escape-legacy'\n", encoding="utf-8")
                violations.clear()
                lane.audit_target_config(violations)
                self.assertTrue(any("target config override" in item for item in violations))

    def test_lane_local_toml_and_legacy_configs_cannot_override_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lane-override-") as temp:
            root = Path(temp)
            lane_path = root / "demo-lane"
            (lane_path / ".cargo").mkdir(parents=True)
            violations: list[str] = []
            (lane_path / ".cargo" / "config.toml").write_text(
                "[build]\ntarget-dir = 'escape-toml'\n", encoding="utf-8"
            )
            lane.audit_lane_target_config(lane_path, violations)
            self.assertIn("config.toml", violations[0])
            violations.clear()
            (lane_path / ".cargo" / "config.toml").unlink()
            (lane_path / ".cargo" / "config").write_text(
                "[build]\ntarget-dir = 'escape-legacy'\n", encoding="utf-8"
            )
            lane.audit_lane_target_config(lane_path, violations)
            self.assertIn("config", violations[0])

    def test_archive_directory_is_sanctioned_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lane-") as temp:
            root = Path(temp)
            (root / lane.ARCHIVE_ROOT_NAME).mkdir()
            (root / lane.ARCHIVE_ROOT_NAME / "MANIFEST.txt").write_text(
                "archived lane\n", encoding="utf-8"
            )
            with patch.object(lane, "LANE_ROOT", root):
                violations: list[str] = []
                lane.audit_lane_root(violations)
        self.assertEqual(violations, [])

    def test_empty_non_linked_directory_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lane-") as temp:
            root = Path(temp)
            (root / "orphan-empty").mkdir()
            with patch.object(lane, "LANE_ROOT", root):
                violations: list[str] = []
                lane.audit_lane_root(violations)
        self.assertEqual(violations, [])

    def test_non_empty_non_linked_directory_is_reported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lane-") as temp:
            root = Path(temp)
            child = root / "orphan-nonempty"
            child.mkdir()
            (child / "sentinel.txt").write_text("x", encoding="utf-8")
            with patch.object(lane, "LANE_ROOT", root):
                violations: list[str] = []
                lane.audit_lane_root(violations)
        self.assertEqual(len(violations), 1)
        self.assertIn("worktrees/orphan-nonempty: not a linked worktree", violations[0])

    def test_gitdir_mirror_is_reported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lane-") as temp:
            root = Path(temp)
            child = root / "mirror"
            child.mkdir()
            (child / ".git").write_text("gitdir: D:/atlas/repos/kwavers/.git\n", encoding="utf-8")
            with patch.object(lane, "LANE_ROOT", root):
                violations: list[str] = []
                lane.audit_lane_root(violations)
        self.assertEqual(len(violations), 1)
        self.assertIn("hand-wired gitdir mirror", violations[0])


if __name__ == "__main__":
    unittest.main()
