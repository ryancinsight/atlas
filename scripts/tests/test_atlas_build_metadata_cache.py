#!/usr/bin/env python3
"""`cargo metadata` is read once per unchanged workspace.

The identity asks for the same manifest's metadata a dozen times per push
(the dependency snapshot, the package layout, the artifact owners, once per
phase), and each call costs a cargo process. The answer is a pure function
of the workspace's manifests and its lockfile, the local packages' build
scripts, the toolchain selector and the cargo configuration, so one read
serves them all -- and a workspace whose inputs changed is read again.
"""

from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import patch

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import atlas_build_snapshot as snapshot  # noqa: E402

SPEC = importlib.util.spec_from_file_location(
    "atlas_build_snapshot_probe", SCRIPTS / "atlas_build_snapshot.py"
)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class MetadataCacheTests(unittest.TestCase):
    """One cargo process per unchanged workspace; a change reads again."""

    def setUp(self) -> None:
        module._METADATA_CACHE.clear()
        self.workspace = pathlib.Path(self.enterContext(__import__("tempfile").TemporaryDirectory()))
        (self.workspace / "demo" / "src").mkdir(parents=True)
        (self.workspace / "Cargo.toml").write_text(
            '[workspace]\nmembers = ["demo"]\nresolver = "2"\n', encoding="utf-8"
        )
        (self.workspace / "demo" / "Cargo.toml").write_text(
            '[package]\nname = "demo"\nversion = "0.1.0"\nedition = "2021"\n',
            encoding="utf-8",
        )
        (self.workspace / "demo" / "src" / "lib.rs").write_text(
            "pub fn demo() {}\n", encoding="utf-8"
        )
        subprocess.run(
            ["cargo", "generate-lockfile", "--offline"],
            cwd=self.workspace,
            check=True,
            capture_output=True,
            timeout=120,
        )
        self.calls: list[list[str]] = []
        real_run = subprocess.run

        def counting(argv, *args, **kwargs):
            if isinstance(argv, (list, tuple)) and "metadata" in argv:
                self.calls.append(list(argv))
            return real_run(argv, *args, **kwargs)

        self.patcher = patch.object(module.subprocess, "run", counting)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def _metadata(self) -> dict:
        return module._cargo_metadata(
            self.workspace / "Cargo.toml", self.workspace, no_deps=False
        )

    def test_an_unchanged_workspace_is_read_once(self) -> None:
        first = self._metadata()
        second = self._metadata()
        self.assertEqual(len(self.calls), 1, "the second read must come from the cache")
        self.assertEqual(first, second)

    def test_a_changed_manifest_is_read_again(self) -> None:
        self._metadata()
        manifest = self.workspace / "demo" / "Cargo.toml"
        # A `[package.metadata]` field: the lockfile still matches, so
        # `--locked` holds, and the metadata reports the new value.
        manifest.write_text(
            '[package]\nname = "demo"\nversion = "0.1.0"\nedition = "2021"\n'
            '[package.metadata.atlas]\nmarker = "changed"\n',
            encoding="utf-8",
        )
        changed = self._metadata()
        self.assertEqual(len(self.calls), 2, "a changed manifest must be read again")
        marker = next(
            entry["metadata"].get("atlas")
            for entry in changed["packages"]
            if isinstance(entry, dict) and entry.get("name") == "demo"
        )
        self.assertEqual(marker, {"marker": "changed"}, "the read must see the new manifest")

    def test_a_changed_lockfile_is_read_again(self) -> None:
        self._metadata()
        lock = self.workspace / "Cargo.lock"
        lock.write_text(lock.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self._metadata()
        self.assertEqual(len(self.calls), 2, "a changed lockfile must be read again")

    def test_a_new_build_script_is_read_again(self) -> None:
        """Cargo auto-detects a package's `build.rs`, so the script's
        presence is part of the graph cargo reports: adding one must
        invalidate the entry, or the snapshot reports a package with no
        build target."""
        self._metadata()
        (self.workspace / "demo" / "build.rs").write_text(
            "fn main() {}\n", encoding="utf-8"
        )
        value = self._metadata()
        self.assertEqual(len(self.calls), 2, "a new build script must be read again")
        kinds = {
            kind
            for entry in value["packages"]
            if entry["name"] == "demo"
            for target in entry["targets"]
            for kind in target["kind"]
        }
        self.assertIn(
            "custom-build", kinds, "the fresh read must report the build target"
        )

    def test_a_changed_cargo_config_is_read_again(self) -> None:
        """A configuration that breaks the read must not be answered from
        the cache. The fresh read raises, so the entry must raise too: a
        cached success in place of a cargo error is a masked failure."""
        self._metadata()
        cargo_dir = self.workspace / ".cargo"
        cargo_dir.mkdir()
        (cargo_dir / "config.toml").write_text(
            '[patch.crates-io]\nabsent = { path = "does-not-exist" }\n',
            encoding="utf-8",
        )
        with self.assertRaises(snapshot.BuildIdentityError):
            self._metadata()
        self.assertEqual(len(self.calls), 2, "a changed cargo config must be read again")

    def test_a_new_toolchain_file_is_read_again(self) -> None:
        """Cargo reads `rust-toolchain.toml` upward from the directory it
        runs in, so creating one must invalidate the entry."""
        self._metadata()
        (self.workspace / "rust-toolchain.toml").write_text(
            '[toolchain]\nchannel = "1.97.0-x86_64-pc-windows-msvc"\n',
            encoding="utf-8",
        )
        try:
            self._metadata()
        except snapshot.BuildIdentityError:
            # The toolchain selector decides which cargo runs; whether that
            # toolchain is installed is not the property under test.
            pass
        self.assertEqual(len(self.calls), 2, "a new toolchain file must be read again")

    def test_another_manifest_is_read_on_its_own(self) -> None:
        self._metadata()
        other = self.workspace / "other"
        (other / "src").mkdir(parents=True)
        # Its own workspace root: a package under the first workspace's
        # directory belongs to that workspace unless it says otherwise.
        (other / "Cargo.toml").write_text(
            '[workspace]\n'
            '[package]\nname = "other"\nversion = "0.1.0"\nedition = "2021"\n',
            encoding="utf-8",
        )
        (other / "src" / "lib.rs").write_text("pub fn other() {}\n", encoding="utf-8")
        subprocess.run(
            ["cargo", "generate-lockfile", "--offline"],
            cwd=other,
            check=True,
            capture_output=True,
            timeout=120,
        )
        module._cargo_metadata(other / "Cargo.toml", other, no_deps=False)
        self.assertEqual(len(self.calls), 2, "another manifest is another read")


if __name__ == "__main__":
    unittest.main()
