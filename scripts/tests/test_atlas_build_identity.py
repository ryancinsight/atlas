#!/usr/bin/env python3
"""Regression tests for shared-cache source identity."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas_build_identity.py"
SPEC = importlib.util.spec_from_file_location("atlas_build_identity", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
sys.path.insert(0, str(SCRIPT.parent))
import atlas_build_artifacts as artifacts

identity = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = identity
SPEC.loader.exec_module(identity)


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.stdout.strip()


def init_repo(root: Path, source: str) -> None:
    root.mkdir(parents=True)
    (root / "Cargo.toml").write_text(
        "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n", encoding="utf-8"
    )
    (root / "Cargo.lock").write_text(
        "version = 4\n\n[[package]]\nname = \"demo\"\nversion = \"0.1.0\"\n",
        encoding="utf-8",
    )
    (root / "src").mkdir()
    (root / "src/lib.rs").write_text(source, encoding="utf-8")
    git(root, "init", "-q")
    git(root, "config", "user.name", "Atlas test")
    git(root, "config", "user.email", "atlas-test@example.invalid")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "source")


def write_script(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


class BuildIdentityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "source-a"
        self.target = self.base / "shared-target"
        self.artifact = self.target / "debug" / "deps" / "libdemo-abcdef.rlib"
        self.artifact.parent.mkdir(parents=True)
        self.clean_log = self.base / "clean.log"
        self.build_script = self.base / "build.py"
        self.clean_script = self.base / "clean.py"
        write_script(
            self.build_script,
            "import os\n"
            "from pathlib import Path\n"
            "path = Path(os.environ['ARTIFACT'])\n"
            "path.parent.mkdir(parents=True, exist_ok=True)\n"
            "path.write_text(os.environ['SOURCE_TOKEN'], encoding='utf-8')\n"
            "mutate = os.environ.get('MUTATE_SOURCE')\n"
            "if mutate:\n"
            "    Path(mutate).write_text('changed during build\\n', encoding='utf-8')\n",
        )
        write_script(
            self.clean_script,
            "import os\n"
            "from pathlib import Path\n"
            "Path(os.environ['CLEAN_LOG']).write_text('cleaned\\n', encoding='utf-8')\n"
            "Path(os.environ['ARTIFACT']).unlink(missing_ok=True)\n",
        )

    def build(
        self,
        root: Path | None = None,
        source_token: str = "source-a",
        **options: object,
    ) -> identity.BuildResult:
        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.dict(
                os.environ,
                {
                    "ARTIFACT": str(self.artifact),
                    "SOURCE_TOKEN": source_token,
                    "CLEAN_LOG": str(self.clean_log),
                },
            ),
        ):
            return identity.run_build(
                root or self.root,
                (root or self.root) / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, str(self.build_script)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, str(self.clean_script)],
                **options,
            )

    def test_source_transition_cleans_once_and_rebuilds_the_affected_package(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        first = self.build(source_token="revision-a")
        self.assertEqual(first.status, "rebuilt")
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "revision-a")
        self.assertTrue(self.clean_log.exists())

        (self.root / "src/lib.rs").write_text("fn main() { println!(\"b\"); }\n", encoding="utf-8")
        git(self.root, "add", "src/lib.rs")
        git(self.root, "commit", "-q", "-m", "source-b")
        self.clean_log.unlink()
        unrelated = self.target / "debug" / "deps" / "libcontrol-abcdef.rlib"
        unrelated.write_text("control", encoding="utf-8")

        second = self.build(source_token="revision-b")
        self.assertEqual(second.status, "rebuilt")
        self.assertEqual(self.clean_log.read_text(encoding="utf-8"), "cleaned\n")
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "revision-b")
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "control")

    def test_matching_source_reuses_the_recorded_artifact(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        first = self.build(source_token="same")
        self.clean_log.unlink()
        second = self.build(source_token="same")
        self.assertEqual(first.record_path, second.record_path)
        self.assertEqual(second.status, "reused")
        self.assertFalse(second.cleaned)
        self.assertFalse(self.clean_log.exists())
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            code, value = identity.check_record(
                self.root,
                "demo",
                self.target,
                artifact_paths=[self.artifact],
                command=[sys.executable, str(self.build_script)],
            )
        self.assertEqual(code, 0)
        self.assertEqual(value["status"], "match")

    def test_a_different_source_root_is_a_different_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        self.build(source_token="a")
        other = self.base / "source-b"
        init_repo(other, "fn main() {}\n")
        self.clean_log.unlink()
        result = self.build(root=other, source_token="b")
        self.assertEqual(result.status, "rebuilt")
        self.assertTrue(self.clean_log.exists())
        record = json.loads(result.record_path.read_text(encoding="utf-8"))
        self.assertEqual(record["source"]["root"], other.resolve().as_posix())

    def test_an_active_owner_blocks_cleaning_and_preserves_the_artifact(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        self.build(source_token="owner")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        lock = identity.lease_path(spec)
        lease = identity.OwnerLease(
            lock,
            {"root": "other-source", "revision": "other-revision", "package": "demo"},
            60,
        )
        lease.__enter__()
        try:
            self.clean_log.unlink()
            with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
                code, value = identity.check_record(
                    self.root,
                    "demo",
                    self.target,
                    artifact_paths=[self.artifact],
                    manifest=self.root / "Cargo.toml",
                )
            self.assertEqual(code, 3)
            self.assertEqual(value["status"], "owned")
            with self.assertRaises(identity.IdentityError):
                self.build(source_token="intruder")
            self.assertEqual(self.artifact.read_text(encoding="utf-8"), "owner")
            self.assertFalse(self.clean_log.exists())
        finally:
            lease.__exit__(None, None, None)

    def test_an_expired_owner_is_recovered(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        lock = identity.lease_path(spec)
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(
            json.dumps(
                {
                    "root": "stale",
                    "revision": "stale",
                    "package": "demo",
                    "target_dir": str(self.target),
                    "token": "stale-token",
                    "expires_ns": 0,
                }
            ),
            encoding="utf-8",
        )
        result = self.build(source_token="recovered")
        self.assertEqual(result.status, "rebuilt")
        self.assertFalse(identity.lease_is_held(lock))

    def test_malformed_owner_fails_closed(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        lock = identity.lease_path(spec)
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("not-json", encoding="utf-8")
        with self.assertRaises(identity.IdentityError):
            self.build(source_token="blocked")
        self.assertFalse(self.clean_log.exists())

    def test_toolchain_identity_runs_in_the_source_root(self) -> None:
        completed = subprocess.CompletedProcess(["rustc"], 0, "rustc 1.95.0\n", "")
        with patch.object(identity.subprocess, "run", return_value=completed) as run:
            self.assertEqual(identity.toolchain_identity(self.root), "rustc 1.95.0")
        self.assertEqual(run.call_args.kwargs["cwd"], self.root)

    def test_command_cwd_is_used_without_changing_record_scope(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        execution_root = self.base / "execution"
        execution_root.mkdir()
        cwd_marker = self.base / "command-cwd.txt"
        command_script = self.base / "record-cwd.py"
        write_script(
            command_script,
            "import os\n"
            "from pathlib import Path\n"
            f"Path({str(cwd_marker)!r}).write_text(os.getcwd(), encoding='utf-8')\n"
            f"Path({str(self.artifact)!r}).write_text('built\\n', encoding='utf-8')\n",
        )
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            result = identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, str(command_script)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, "-c", "pass"],
                command_cwd=execution_root,
            )
        record = json.loads(result.record_path.read_text(encoding="utf-8"))
        self.assertNotIn("command_cwd", record["build"])
        self.assertEqual(cwd_marker.read_text(encoding="utf-8"), str(execution_root.resolve()))

    def test_a_dirty_tree_is_not_identified_by_revision_alone(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        before = identity.source_identity(self.root)
        (self.root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        after = identity.source_identity(self.root)
        self.assertTrue(after.dirty)
        self.assertNotEqual(before.tree_digest, after.tree_digest)

    def test_ignored_source_files_are_hashed_and_can_be_explicitly_excluded(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        (self.root / ".gitignore").write_text("generated.rs\n", encoding="utf-8")
        git(self.root, "add", ".gitignore")
        git(self.root, "commit", "-q", "-m", "ignore generated source")
        clean = identity.source_identity(self.root)
        (self.root / "generated.rs").write_text("first\n", encoding="utf-8")
        before = identity.source_identity(self.root)
        (self.root / "generated.rs").write_text("second\n", encoding="utf-8")
        after = identity.source_identity(self.root)
        self.assertTrue(after.dirty)
        self.assertNotEqual(before.tree_digest, after.tree_digest)
        excluded = identity.source_identity(
            self.root, ignored_paths=(self.root / "generated.rs",)
        )
        self.assertFalse(excluded.dirty)
        self.assertEqual(excluded.tree_digest, clean.tree_digest)

    def test_target_files_do_not_change_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        before = identity.source_identity(self.root)
        target = self.root / "target"
        target.mkdir()
        (target / "artifact.rlib").write_text("generated", encoding="utf-8")
        identity_value = identity.source_identity(self.root, (target,))
        self.assertFalse(identity_value.dirty)
        self.assertEqual(identity_value.tree_digest, before.tree_digest)
        with self.assertRaises(identity.IdentityError):
            identity.build_spec(self.root, "demo", self.root, "debug", "host", "")

    def test_explicit_ignored_lockfile_does_not_change_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        lock = self.root / "Cargo.lock"
        lock.write_text("version = 4\n", encoding="utf-8")
        git(self.root, "add", "Cargo.lock")
        git(self.root, "commit", "-q", "-m", "lock")
        before = identity.source_identity(self.root)
        lock.write_text("version = 4\nchanged\n", encoding="utf-8")
        after = identity.source_identity(self.root, ignored_paths=(lock,))
        self.assertEqual(after.tree_digest, before.tree_digest)
        self.assertFalse(after.dirty)

    def test_build_environment_changes_change_the_record_scope(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            with patch.dict(os.environ, {"RUSTFLAGS": "-C debuginfo=0"}):
                first = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
            with patch.dict(os.environ, {"RUSTFLAGS": "-C debuginfo=2"}):
                second = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        self.assertNotEqual(first.environment_digest, second.environment_digest)
        self.assertNotEqual(identity.record_path(first), identity.record_path(second))

    def test_source_changes_during_build_are_not_recorded(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        changed = self.root / "src/lib.rs"
        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.dict(
                os.environ,
                {
                    "ARTIFACT": str(self.artifact),
                    "SOURCE_TOKEN": "during",
                    "CLEAN_LOG": str(self.clean_log),
                    "MUTATE_SOURCE": str(changed),
                },
            ),
            self.assertRaises(identity.IdentityError),
        ):
            identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, str(self.build_script)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, str(self.clean_script)],
            )
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(
                self.root,
                "demo",
                self.target,
                "debug",
                "host",
                "",
                [sys.executable, str(self.build_script)],
            )
        self.assertFalse(identity.record_path(spec).exists())

    def test_discovery_uses_target_triple_and_exact_package_name(self) -> None:
        deps = self.target / "x86_64-unknown-linux-gnu" / "debug" / "deps"
        deps.mkdir(parents=True)
        wanted = deps / "libdemo-111.rlib"
        similar = deps / "libdemo-tools-222.rlib"
        executable = deps / "demo-333.exe"
        for path in (wanted, similar, executable):
            path.write_bytes(path.name.encode())
        with patch.object(
            artifacts,
            "_workspace_artifact_owners",
            return_value={
                "demo": frozenset({"demo"}),
                "demo-tools": frozenset({"demo_tools"}),
            },
        ):
            paths = identity.discover_artifacts(
                self.target,
                "demo",
                "debug",
                "x86_64-unknown-linux-gnu",
                self.root / "Cargo.toml",
            )
        self.assertEqual(set(paths), {wanted.resolve(), executable.resolve()})

    def test_discovery_normalizes_target_names_and_fingerprint_layout(self) -> None:
        deps = self.target / "debug" / "deps"
        fingerprint = self.target / "debug" / ".fingerprint" / "my-pkg-123"
        deps.mkdir(parents=True, exist_ok=True)
        fingerprint.mkdir(parents=True, exist_ok=True)
        artifact = deps / "libcustom_target-111.rlib"
        output = fingerprint / "output"
        artifact.write_bytes(b"artifact")
        output.write_bytes(b"output")
        with patch.object(
            artifacts,
            "_workspace_artifact_owners",
            return_value={"my-pkg": frozenset({"custom_target", "my_pkg"})},
        ):
            paths = artifacts.discover_artifacts(
                self.target, "my-pkg", "debug", manifest=self.root / "Cargo.toml"
            )
        self.assertEqual(set(paths), {artifact.resolve(), output.resolve()})

    def test_dependency_snapshot_tracks_reachable_path_sources(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        dependency_root = self.base / "dependency"
        dependency_root.mkdir()
        (dependency_root / "Cargo.toml").write_text("[package]\nname = \"dep\"\n", encoding="utf-8")
        metadata = {
            "packages": [
                {
                    "id": "root 0.1.0",
                    "name": "demo",
                    "version": "0.1.0",
                    "source": None,
                    "manifest_path": str((self.root / "Cargo.toml").resolve()),
                },
                {
                    "id": "path+dep 0.1.0",
                    "name": "dep",
                    "version": "0.1.0",
                    "source": None,
                    "manifest_path": str((dependency_root / "Cargo.toml").resolve()),
                },
            ],
            "workspace_members": ["root 0.1.0"],
            "resolve": {
                "nodes": [
                    {"id": "root 0.1.0", "deps": [{"pkg": "path+dep 0.1.0", "dep_kinds": []}]},
                    {"id": "path+dep 0.1.0", "deps": []},
                ]
            },
        }
        with patch.object(artifacts, "_cargo_metadata", return_value=metadata):
            first = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "a"},
            )
            second = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "b"},
            )
        self.assertNotEqual(first["digest"], second["digest"])
        self.assertEqual(first["clean_packages"], ["demo", "dep"])

    def test_registry_package_content_changes_change_the_dependency_snapshot(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        registry_root = self.base / "registry"
        (registry_root / "src").mkdir(parents=True)
        (registry_root / "Cargo.toml").write_text(
            "[package]\nname = \"dep\"\nversion = \"0.1.0\"\n", encoding="utf-8"
        )
        source = registry_root / "src" / "lib.rs"
        source.write_text("pub fn value() -> u8 { 1 }\n", encoding="utf-8")
        metadata = {
            "packages": [
                {
                    "id": "root 0.1.0",
                    "name": "demo",
                    "version": "0.1.0",
                    "source": None,
                    "manifest_path": str((self.root / "Cargo.toml").resolve()),
                },
                {
                    "id": "registry dep",
                    "name": "dep",
                    "version": "0.1.0",
                    "source": "registry+https://example.invalid/dep",
                    "manifest_path": str((registry_root / "Cargo.toml").resolve()),
                },
            ],
            "workspace_members": ["root 0.1.0"],
            "resolve": {
                "nodes": [
                    {"id": "root 0.1.0", "deps": [{"pkg": "registry dep", "dep_kinds": []}]},
                    {"id": "registry dep", "deps": []},
                ]
            },
        }
        with patch.object(artifacts, "_cargo_metadata", return_value=metadata):
            first = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "a"},
            )
            source.write_text("pub fn value() -> u8 { 2 }\n", encoding="utf-8")
            second = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "a"},
            )
        self.assertNotEqual(first["digest"], second["digest"])
        first_registry = next(
            package for package in first["packages"] if package["name"] == "dep"
        )
        second_registry = next(
            package for package in second["packages"] if package["name"] == "dep"
        )
        self.assertNotEqual(
            first_registry["content_digest"],
            second_registry["content_digest"],
        )

    def test_outside_artifact_is_rejected_before_cleaning(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        outside = self.base / "outside.rlib"
        outside.write_text("outside", encoding="utf-8")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            with self.assertRaises(identity.IdentityError):
                identity.run_build(
                    self.root,
                    self.root / "Cargo.toml",
                    "demo",
                    self.target,
                    [sys.executable, str(self.build_script)],
                    artifact_paths=[outside],
                    clean_command=[sys.executable, str(self.clean_script)],
                )
        self.assertFalse(self.clean_log.exists())

    def test_dependency_transition_cleans_the_reachable_path_packages(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        snapshot = {
            "root": "demo",
            "packages": [],
            "edges": [],
            "clean_packages": ["demo", "dep"],
            "digest": "dependency-digest",
        }
        artifact = self.target / "debug" / "deps" / "libdemo-123.rlib"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        commands: list[tuple[str, ...]] = []

        def run_command(command: tuple[str, ...], root: Path, environment: dict[str, str]) -> None:
            commands.append(command)
            if len(command) < 2 or command[1] != "clean":
                artifact.write_text("built", encoding="utf-8")

        artifact_value = {"files": {"debug/deps/libdemo-123.rlib": "digest"}, "digest": "artifact"}
        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.object(identity, "dependency_snapshot", return_value=snapshot),
            patch.object(identity, "artifact_identity", return_value=artifact_value),
            patch.object(identity, "_run_checked", side_effect=run_command),
        ):
            first = identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, "-c", "pass"],
            )
            second = identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, "-c", "pass"],
            )
        self.assertEqual(first.status, "rebuilt")
        self.assertEqual(second.status, "reused")
        clean_commands = [command for command in commands if list(command[1:3]) == ["clean", "-p"]]
        self.assertEqual([command[3] for command in clean_commands], ["demo", "dep"])

    def test_malformed_records_fail_closed(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(
                self.root,
                "demo",
                self.target,
                "debug",
                "host",
                "",
                [sys.executable, str(self.build_script)],
            )
            record = identity.record_path(spec)
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text('{"version": true}', encoding="utf-8")
            with self.assertRaises(identity.IdentityError):
                identity.check_record(
                    self.root,
                    "demo",
                    self.target,
                    artifact_paths=[self.artifact],
                    manifest=self.root / "Cargo.toml",
                    command=[sys.executable, str(self.build_script)],
                )

    def test_artifact_paths_must_stay_inside_the_shared_target(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        outside = self.base / "outside.rlib"
        outside.write_text("outside", encoding="utf-8")
        with self.assertRaises(identity.IdentityError):
            identity.artifact_identity(
                self.root,
                self.target,
                "demo",
                "debug",
                [outside],
            )

    def test_command_keys_keep_separate_records_over_one_source(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        clippy = self.build(source_token="same", command_key="clippy")
        self.assertTrue(clippy.cleaned)
        self.clean_log.unlink()
        tests = self.build(source_token="same", command_key="tests")
        self.assertNotEqual(clippy.record_path, tests.record_path)
        # The tests step builds the source clippy just built: nothing foreign
        # to clean, so the clippy artifacts survive.
        self.assertFalse(tests.cleaned)
        self.assertFalse(self.clean_log.exists())

    def test_a_new_command_key_after_a_source_change_still_cleans(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        self.build(source_token="a", command_key="clippy")
        (self.root / "src/lib.rs").write_text("fn main() { let _b = 1; }\n", encoding="utf-8")
        git(self.root, "commit", "-qam", "source-b")
        self.clean_log.unlink()
        result = self.build(source_token="b", command_key="tests")
        self.assertTrue(result.cleaned)
        self.assertTrue(self.clean_log.exists())

    def test_an_ignored_path_does_not_change_the_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        lock = self.root / "Cargo.lock"
        lock.write_text("# committed\n", encoding="utf-8")
        git(self.root, "add", "Cargo.lock")
        git(self.root, "commit", "-qm", "lock")
        before = identity.source_identity(self.root)
        lock.write_text("# rewritten by the gate\n", encoding="utf-8")
        self.assertEqual(identity.source_identity(self.root, ignored_paths=(lock,)), before)
        self.assertTrue(identity.source_identity(self.root).dirty)
        (self.root / "src/lib.rs").write_text("fn main() { let _c = 1; }\n", encoding="utf-8")
        self.assertTrue(identity.source_identity(self.root, ignored_paths=(lock,)).dirty)

    def test_an_ignored_path_outside_the_source_tree_is_rejected(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with self.assertRaises(identity.IdentityError):
            identity.source_identity(
                self.root, ignored_paths=(self.base / "elsewhere.lock",)
            )

    def test_commands_run_in_the_requested_directory(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        elsewhere = self.base / "gate-cwd"
        elsewhere.mkdir()
        marker = self.base / "cwd.txt"
        record_cwd = self.base / "record_cwd.py"
        write_script(
            record_cwd,
            "import os, sys\n"
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text(os.getcwd(), encoding='utf-8')\n"
            f"exec(open({str(self.build_script)!r}).read())\n",
        )
        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.dict(
                os.environ,
                {"ARTIFACT": str(self.artifact), "SOURCE_TOKEN": "cwd", "CLEAN_LOG": str(self.clean_log)},
            ),
        ):
            identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, str(record_cwd)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, str(self.clean_script)],
                command_cwd=elsewhere,
            )
        self.assertEqual(Path(marker.read_text(encoding="utf-8")).resolve(), elsewhere.resolve())


class CommandLineTestCase(unittest.TestCase):
    """The entry point accepts the exact argument shape the member pre-push passes."""

    _run_checked = staticmethod(identity._run_checked)

    def _skip_cargo_clean(self, command, cwd, environment) -> None:
        # The CLI cannot inject a clean command; keep the test off real Cargo.
        if list(command[:2]) == ["cargo", "clean"]:
            return
        self._run_checked(command, cwd, environment)

    def test_the_pre_push_invocation_parses_and_runs(self) -> None:
        cli_path = Path(__file__).resolve().parents[1] / "atlas-build-identity.py"
        cli_spec = importlib.util.spec_from_file_location("atlas_build_identity_cli", cli_path)
        assert cli_spec is not None and cli_spec.loader is not None
        cli = importlib.util.module_from_spec(cli_spec)
        cli_spec.loader.exec_module(cli)
        with tempfile.TemporaryDirectory(prefix="atlas-build-identity-cli-") as temp:
            base = Path(temp)
            root = base / "member"
            init_repo(root, "fn main() {}\n")
            target = base / "target"
            artifact = target / "debug" / "deps" / "libdemo-cli.rlib"
            build = base / "build.py"
            write_script(
                build,
                "from pathlib import Path\n"
                f"path = Path({str(artifact)!r})\n"
                "path.parent.mkdir(parents=True, exist_ok=True)\n"
                "path.write_text('built', encoding='utf-8')\n",
            )
            with (
                patch.object(cli, "run_build", wraps=identity.run_build) as run_build,
                patch.object(identity, "toolchain_identity", return_value="rustc-test"),
                patch.object(identity, "_run_checked", side_effect=self._skip_cargo_clean),
            ):
                code = cli.main([
                    "run",
                    "--root", str(root),
                    "--package", "demo",
                    "--target-dir", str(target),
                    "--profile", "debug",
                    "--target", "host",
                    "--manifest", str(root / "Cargo.toml"),
                    "--command-cwd", str(root),
                    "--command-key", "atlas-pre-push:demo",
                    "--ignore-path", str(root / "Cargo.lock"),
                    "--manifest", str(root / "Cargo.toml"),
                    "--",
                    sys.executable, str(build),
                ])
            self.assertEqual(code, 0)
            kwargs = run_build.call_args.kwargs
            self.assertEqual(kwargs["command_key"], "atlas-pre-push:demo")
            self.assertEqual(kwargs["command_cwd"], root)
            self.assertEqual(kwargs["ignore_paths"], [root / "Cargo.lock"])
            self.assertEqual(artifact.read_text(encoding="utf-8"), "built")


if __name__ == "__main__":
    unittest.main()
