"""Target-directory access remains beneath one opened directory identity."""

from __future__ import annotations

import ctypes
import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlas_build_lease import BuildIdentityError
from atlas_git_process import execute_process
from atlas_build_target import TargetDirectory
from atlas_build_identity_test_support import (
    BuildIdentityFixture,
    artifacts,
    build_workflow,
    identity,
    init_repo,
)


class TargetDirectoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="atlas-target-directory-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def _link_directory(self, link: Path, target: Path) -> None:
        if os.name == "nt":
            subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
                check=True,
                capture_output=True,
                timeout=30,
            )
            self.addCleanup(lambda: link.rmdir() if link.exists() else None)
        else:
            link.symlink_to(target, target_is_directory=True)

    def test_file_reads_are_relative_to_the_held_target(self) -> None:
        target = self.base / "target"
        artifact = target / "debug" / "deps" / "libdemo.rlib"
        artifact.parent.mkdir(parents=True)
        artifact.write_bytes(b"target bytes")

        with TargetDirectory(target) as directory:
            with directory.open_file(Path("debug/deps/libdemo.rlib")) as stream:
                self.assertEqual(stream.read(), b"target bytes")

    def test_create_opens_a_missing_target_root(self) -> None:
        target = self.base / "new" / "target"
        record = Path(".atlas/source-identity/build.json")

        with TargetDirectory(target, create=True) as directory:
            directory.atomic_write(record, b'{"generation":1}\n')
            self.assertTrue(directory.path.is_dir())
            self.assertEqual(directory.read_file(record), b'{"generation":1}\n')

    def test_atomic_write_creates_parents_and_replaces_within_target(self) -> None:
        target = self.base / "target"
        target.mkdir()
        record = Path(".atlas/source-identity/build.json")

        with TargetDirectory(target) as directory:
            directory.atomic_write(record, b'{"generation":1}\n')
            self.assertEqual(directory.read_file(record), b'{"generation":1}\n')
            directory.atomic_write(record, b'{"generation":2}\n')
            self.assertEqual(directory.read_file(record), b'{"generation":2}\n')

        self.assertEqual(
            (target / record).read_bytes(), b'{"generation":2}\n'
        )

    def test_atomic_write_rejects_reparse_record_parent(self) -> None:
        target = self.base / "target"
        target.mkdir()
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "record.json").write_bytes(b"outside")
        self._link_directory(target / ".atlas", outside)

        with TargetDirectory(target) as directory:
            with self.assertRaises(BuildIdentityError):
                directory.atomic_write(
                    Path(".atlas/record.json"), b'{"generation":1}\n'
                )

        self.assertEqual((outside / "record.json").read_bytes(), b"outside")

    def test_lock_open_rejects_a_reparse_parent_before_touching_outside_files(self) -> None:
        target = self.base / "target"
        target.mkdir()
        outside_identity = self.base / "outside" / "source-identity"
        outside_identity.mkdir(parents=True)
        sentinel = outside_identity / "lease.lock"
        sentinel.write_bytes(b"outside")
        self._link_directory(target / ".atlas", outside_identity.parent)

        with TargetDirectory(target) as directory:
            with self.assertRaises(BuildIdentityError):
                directory.open_lock_file(Path(".atlas/source-identity/lease.lock"))

        self.assertEqual(sentinel.read_bytes(), b"outside")

    @unittest.skipIf(os.name == "nt", "creating file symlinks may require Windows privileges")
    def test_lock_open_rejects_a_symlinked_lock_file(self) -> None:
        target = self.base / "target"
        lock_dir = target / ".atlas" / "source-identity"
        lock_dir.mkdir(parents=True)
        outside = self.base / "outside.lock"
        outside.write_bytes(b"outside")
        (lock_dir / "lease.lock").symlink_to(outside)

        with TargetDirectory(target) as directory:
            with self.assertRaises(BuildIdentityError):
                directory.open_lock_file(Path(".atlas/source-identity/lease.lock"))

        self.assertEqual(outside.read_bytes(), b"outside")

    def test_absolute_short_path_alias_resolves_to_the_held_target(self) -> None:
        if os.name != "nt":
            self.skipTest("Windows short paths are platform-specific")
        target = self.base / "target directory"
        artifact = target / "artifact.rlib"
        target.mkdir()
        artifact.write_bytes(b"target bytes")
        buffer = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetShortPathNameW(
            str(target), buffer, len(buffer)
        )
        if not length or buffer.value.casefold() == str(target).casefold():
            self.skipTest("the filesystem does not provide an 8.3 alias")

        with TargetDirectory(target) as directory:
            with directory.open_file(Path(buffer.value) / artifact.name) as stream:
                self.assertEqual(stream.read(), b"target bytes")

    def test_explicit_path_through_a_directory_reparse_point_is_rejected(self) -> None:
        target = self.base / "target"
        actual = target / "actual"
        actual.mkdir(parents=True)
        (actual / "artifact.rlib").write_bytes(b"inside")
        alias = target / "alias"
        self._link_directory(alias, actual)

        with TargetDirectory(target) as directory:
            with self.assertRaises(BuildIdentityError):
                directory.open_file(alias / "artifact.rlib")

    def test_replacing_an_artifact_parent_with_an_external_link_is_rejected(self) -> None:
        target = self.base / "target"
        deps = target / "debug" / "deps"
        deps.mkdir(parents=True)
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "libdemo.rlib").write_bytes(b"outside")
        moved = target / "debug" / "deps-original"

        with TargetDirectory(target) as directory:
            deps.rename(moved)
            self._link_directory(deps, outside)
            with self.assertRaises(BuildIdentityError):
                directory.open_file(deps / "libdemo.rlib")

    def test_replacing_the_target_path_does_not_redirect_its_open_handle(self) -> None:
        target = self.base / "target"
        target.mkdir()
        (target / "artifact.rlib").write_bytes(b"original")
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "artifact.rlib").write_bytes(b"replacement")
        moved = self.base / "target-original"

        with TargetDirectory(target) as directory:
            if os.name == "nt":
                with self.assertRaises(OSError):
                    target.rename(moved)
            else:
                target.rename(moved)
                target.symlink_to(outside, target_is_directory=True)
                self.addCleanup(lambda: target.unlink() if target.is_symlink() else None)
            with directory.open_file(Path("artifact.rlib")) as stream:
                self.assertEqual(stream.read(), b"original")

    @unittest.skipIf(os.name == "nt", "POSIX descriptor-backed command path")
    def test_subprocess_path_stays_anchored_after_target_replacement(self) -> None:
        target = self.base / "target"
        target.mkdir()
        moved = self.base / "target-original"
        outside = self.base / "outside"
        outside.mkdir()
        script = (
            "import os, pathlib, sys\n"
            "requested = pathlib.Path(sys.argv[1])\n"
            "requested.rename(sys.argv[2])\n"
            "requested.symlink_to(sys.argv[3], target_is_directory=True)\n"
            "output = pathlib.Path(os.environ['CARGO_TARGET_DIR']) / 'build-output'\n"
            "output.write_bytes(b'held directory')\n"
        )

        with TargetDirectory(target) as directory:
            result = execute_process(
                (
                    sys.executable,
                    "-c",
                    script,
                    str(target),
                    str(moved),
                    str(outside),
                ),
                env={"CARGO_TARGET_DIR": directory.command_path},
                pass_fds=directory.command_fds,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0)

        self.assertEqual((moved / "build-output").read_bytes(), b"held directory")
        self.assertFalse((outside / "build-output").exists())

    @unittest.skipUnless(sys.platform.startswith("linux"), "requires Linux directory descriptors")
    def test_artifact_discovery_stays_on_held_target_after_path_replacement(self) -> None:
        target = self.base / "target"
        moved = self.base / "target-original"
        outside = self.base / "outside"
        source = self.base / "source"
        source.mkdir()
        artifact = target / "debug" / "deps" / "libdemo-0123456789abcdef.rlib"
        decoy = outside / "debug" / "deps" / artifact.name
        artifact.parent.mkdir(parents=True)
        decoy.parent.mkdir(parents=True)
        artifact.write_bytes(b"held target")
        decoy.write_bytes(b"replacement target")

        with TargetDirectory(target) as directory:
            target.rename(moved)
            target.symlink_to(outside, target_is_directory=True)
            result = artifacts.artifact_identity(
                source, directory, "demo", "debug", ()
            )

        self.assertEqual(
            result["files"],
            {
                "debug/deps/libdemo-0123456789abcdef.rlib": hashlib.sha256(
                    b"held target"
                ).hexdigest()
            },
        )

    def test_target_path_cannot_contain_a_reparse_point(self) -> None:
        actual = self.base / "actual"
        actual.mkdir()
        alias = self.base / "target alias"
        self._link_directory(alias, actual)

        with self.assertRaises(BuildIdentityError):
            TargetDirectory(alias)

    @unittest.skipUnless(os.name == "nt", "Windows UTF-16 paths are platform-specific")
    def test_supplementary_unicode_component_does_not_open_a_prefix_sibling(self) -> None:
        requested = self.base / "target😀x"
        sibling = self.base / "target😀"
        requested.mkdir()
        sibling.mkdir()
        (requested / "artifact").write_bytes(b"requested target")
        (sibling / "artifact").write_bytes(b"prefix sibling")

        with TargetDirectory(requested) as directory:
            self.assertEqual(directory.read_file(Path("artifact")), b"requested target")


class TargetRecordDiscoveryTestCase(BuildIdentityFixture):
    @unittest.skipUnless(sys.platform.startswith("linux"), "requires Linux directory descriptors")
    def test_sibling_record_discovery_stays_on_held_target_after_path_replacement(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        command = [sys.executable, str(self.build_script)]
        self.build(source_token="same", command_key="clippy")
        outside = self.base / "outside"
        outside.mkdir()

        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            TargetDirectory(self.target) as target_root,
        ):
            dependencies = identity._dependency_data(
                self.root / "Cargo.toml",
                "demo",
                self.target,
                self.root,
                (),
                True,
            )
            spec = identity.build_spec(
                self.root,
                "demo",
                self.target,
                "debug",
                "host",
                "",
                command,
                "tests",
                dependency_digest=str(dependencies["digest"]),
            )
            moved = self.base / "target-original"
            self.target.rename(moved)
            self.target.symlink_to(outside, target_is_directory=True)
            matched = build_workflow._sibling_matches(
                spec,
                dependencies,
                self.root / "Cargo.toml",
                self.root,
                (self.artifact,),
                target_root,
            )

        self.assertTrue(matched)


if __name__ == "__main__":
    unittest.main()
