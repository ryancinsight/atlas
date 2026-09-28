#!/usr/bin/env python3
"""Regression tests for shared-cache build identity."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from atlas_build_identity_test_support import (
    BuildIdentityError,
    BuildIdentityFixture,
    OwnerLease,
    TargetDirectory,
    artifact_record,
    artifacts,
    build_workflow,
    check_workflow,
    git,
    identity,
    init_repo,
    lease_is_held,
    package_target_lease_path,
    records,
    source,
    write_script,
)


class BuildIdentityTestCase(BuildIdentityFixture):


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
            code, value = check_workflow.check_record(
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
        target = TargetDirectory(self.target, create=True)
        self.addCleanup(target.close)
        lease = OwnerLease(
            target,
            lock,
            {"root": "other-source", "revision": "other-revision", "package": "demo"},
            60,
        )
        lease.__enter__()
        try:
            self.clean_log.unlink()
            with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
                code, value = check_workflow.check_record(
                    self.root,
                    "demo",
                    self.target,
                    artifact_paths=[self.artifact],
                    manifest=self.root / "Cargo.toml",
                )
            self.assertEqual(code, 3)
            self.assertEqual(value["status"], "owned")
            with self.assertRaises(BuildIdentityError):
                self.build(source_token="intruder")
            self.assertEqual(self.artifact.read_text(encoding="utf-8"), "owner")
            self.assertFalse(self.clean_log.exists())
        finally:
            lease.__exit__(None, None, None)

    def test_a_dependency_owner_blocks_cleaning(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        snapshot = {
            "root": "demo",
            "packages": [],
            "edges": [],
            "clean_packages": ["demo", "dep"],
        }
        snapshot["digest"] = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        lock = package_target_lease_path("dep", self.target)
        self.artifact.write_bytes(b"owned artifact")
        target = TargetDirectory(self.target, create=True)
        self.addCleanup(target.close)
        owner_data = {
            "root": "dependency-root",
            "revision": "dependency-revision",
            "package": "dep",
            "target_dir": str(self.target),
        }
        owner = OwnerLease(
            target,
            lock,
            owner_data,
            60,
        )
        owner.__enter__()
        try:
            owner.handle.seek(0)
            owner_record = owner.handle.read()
            self.clean_log.unlink(missing_ok=True)
            with (
                patch.object(identity, "toolchain_identity", return_value="rustc-test"),
                patch.object(build_workflow, "_dependency_data", return_value=snapshot),
                patch.object(build_workflow, "_run_checked") as run_checked,
            ):
                with self.assertRaisesRegex(
                    BuildIdentityError,
                    "source identity is owned by dependency-root at dependency-revision",
                ):
                    build_workflow.run_build(
                        self.root,
                        self.root / "Cargo.toml",
                        "demo",
                        self.target,
                        [sys.executable, str(self.build_script)],
                        artifact_paths=(),
                    )
                run_checked.assert_not_called()
            self.assertFalse(self.clean_log.exists())
            self.assertEqual(self.artifact.read_bytes(), b"owned artifact")
            owner.handle.seek(0)
            self.assertEqual(owner.handle.read(), owner_record)
        finally:
            owner.__exit__(None, None, None)
        self.assertFalse(lease_is_held(lock))

    def test_an_expired_owner_is_recovered(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        lock = identity.lease_path(spec)
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(
            "\0L" + json.dumps(
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
        self.assertFalse(lease_is_held(lock))

    def test_an_unlocked_unexpired_owner_cannot_be_overwritten(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        lock = identity.lease_path(spec)
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(
            "\0L" + json.dumps(
                {
                    "root": "live-owner",
                    "revision": "live-revision",
                    "package": "demo",
                    "target_dir": str(self.target),
                    "token": "live-token",
                    "expires_ns": 10**30,
                }
            ),
            encoding="utf-8",
        )
        target = TargetDirectory(self.target, create=True)
        self.addCleanup(target.close)

        with self.assertRaisesRegex(BuildIdentityError, "until its lease expires"):
            OwnerLease(
                target,
                lock,
                {"root": str(self.root), "revision": spec.source.revision, "package": "demo"},
                60,
            ).__enter__()

        self.assertFalse(self.clean_log.exists())
        self.assertEqual(
            json.loads(lock.read_bytes()[2:])["token"], "live-token"
        )

    def test_malformed_owner_fails_closed(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        lock = identity.lease_path(spec)
        lock.parent.mkdir(parents=True, exist_ok=True)
        malformed_records = (
            b"not-json",
            b"x"
            + json.dumps(
                {
                    "root": "stale",
                    "revision": "stale",
                    "package": "demo",
                    "target_dir": str(self.target),
                    "token": "stale-token",
                    "expires_ns": 0,
                }
            ).encode(),
        )
        for malformed in malformed_records:
            with self.subTest(malformed=malformed[:8]):
                lock.write_bytes(malformed)
                with self.assertRaises(BuildIdentityError):
                    self.build(source_token="blocked")
                self.assertFalse(self.clean_log.exists())
                self.assertEqual(lock.read_bytes(), malformed)

    def test_toolchain_identity_runs_in_the_source_root(self) -> None:
        completed = type(
            "ProcessResult",
            (),
            {
                "returncode": 0,
                "stdout": b"rustc 1.95.0\n",
                "stderr": b"",
            },
        )()
        with patch.object(source, "execute_process", return_value=completed) as run:
            self.assertEqual(identity.toolchain_identity(self.root), "rustc 1.95.0")
        self.assertEqual(run.call_args.kwargs["cwd"], self.root)
        self.assertEqual(run.call_args.kwargs["timeout"], 60)

    def test_build_commands_use_the_bounded_process_runner(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        completed = type("ProcessResult", (), {"returncode": 0})()
        with TargetDirectory(self.target, create=True) as target:
            expected_fds = target.command_fds
            environment = {"CARGO_TARGET_DIR": target.command_path}
            with patch.object(build_workflow, "execute_process", return_value=completed) as run:
                build_workflow._run_checked(
                    [sys.executable, "-c", "pass"], self.root, environment, target
                )
            self.assertEqual(
                run.call_args.kwargs["timeout"],
                build_workflow.BUILD_COMMAND_TIMEOUT_SECONDS,
            )
            self.assertFalse(run.call_args.kwargs["capture_output"])
            self.assertEqual(run.call_args.kwargs["pass_fds"], expected_fds)
            if os.name != "nt":
                self.assertRegex(
                    run.call_args.kwargs["env"]["CARGO_TARGET_DIR"],
                    r"^/(proc|dev)/fd/\d+$",
                )

    @unittest.skipIf(os.name == "nt", "POSIX descriptor-backed command path")
    def test_build_output_stays_in_the_open_target_after_path_replacement(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        moved = self.base / "shared-target-original"
        outside = self.base / "outside-target"
        outside.mkdir()
        artifact = self.target / "debug" / "deps" / "guard.bin"
        script = self.base / "replace-target.py"
        write_script(
            script,
            "import os\n"
            "from pathlib import Path\n"
            "requested = Path(os.environ['TARGET_PATH'])\n"
            "requested.rename(os.environ['MOVED_TARGET'])\n"
            "requested.symlink_to(os.environ['OUTSIDE_TARGET'], target_is_directory=True)\n"
            "target = Path(os.environ['CARGO_TARGET_DIR'])\n"
            "artifact = target / 'debug' / 'deps' / 'guard.bin'\n"
            "artifact.parent.mkdir(parents=True)\n"
            "artifact.write_bytes(b'anchored build output')\n",
        )

        with patch.dict(
            os.environ,
            {
                "TARGET_PATH": str(self.target),
                "MOVED_TARGET": str(moved),
                "OUTSIDE_TARGET": str(outside),
            },
        ), patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            result = build_workflow.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, str(script)],
                artifact_paths=[artifact],
                clean_command=[sys.executable, "-c", "pass"],
            )

        self.assertEqual(result.artifact_files, (artifact,))
        self.assertEqual((moved / "debug" / "deps" / "guard.bin").read_bytes(), b"anchored build output")
        self.assertFalse((outside / "debug" / "deps" / "guard.bin").exists())
        self.assertTrue((moved / ".atlas" / "source-identity").is_dir())
        self.assertFalse((outside / ".atlas" / "source-identity").exists())








    def test_build_environment_changes_change_the_record_scope(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            with patch.dict(os.environ, {"RUSTFLAGS": "-C debuginfo=0"}):
                first = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
            with patch.dict(os.environ, {"RUSTFLAGS": "-C debuginfo=2"}):
                second = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        self.assertNotEqual(first.environment_digest, second.environment_digest)
        self.assertNotEqual(records.record_path(first), records.record_path(second))










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

        def run_command(
            command: tuple[str, ...],
            root: Path,
            environment: dict[str, str],
            target_root: TargetDirectory,
        ) -> None:
            commands.append(command)
            if len(command) < 2 or command[1] != "clean":
                artifact.write_text("built", encoding="utf-8")

        artifact_value = artifact_record(
            {"debug/deps/libdemo-123.rlib": hashlib.sha256(b"built").hexdigest()}
        )
        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.object(identity, "dependency_snapshot", return_value=snapshot),
            patch.object(build_workflow, "artifact_identity", return_value=artifact_value),
            patch.object(build_workflow, "_run_checked", side_effect=run_command),
        ):
            first = build_workflow.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, "-c", "pass"],
            )
            second = build_workflow.run_build(
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
