"""Exact source retargeting against real offline Cargo graph resolution."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_atlas_lock_sweep import LOCK, NEW, OLD, sweep
from test_lockfile_regenerate import git, provider


class RetargetSourceTests(unittest.TestCase):
    def test_only_selected_revision_fields_change_with_line_endings_preserved(self) -> None:
        source = f"git+https://github.com/ryancinsight/hermes.git#{OLD}"
        replacement = source.rsplit("#", 1)[0] + "#" + NEW
        for newline in ("\n", "\r\n"):
            original = (LOCK + "# " + source + "\n").replace("\n", newline)
            expected = (LOCK.replace(source, replacement) + "# " + source + "\n").replace("\n", newline)
            with self.subTest(newline=repr(newline)):
                self.assertEqual(sweep.retarget_sources(original, {source: NEW}), expected)

    def test_an_explicit_query_cannot_be_silently_reported_current(self) -> None:
        selected = sweep.stale_packages(LOCK, {"leto": NEW}, sweep.locked_packages)
        self.assertEqual([(package.name, package.rev) for package in selected], [("pinned", OLD)])
        self.assertEqual(sweep.stale_packages(LOCK, {"leto": NEW}), ())

    def test_missing_queried_or_malformed_identities_fail(self) -> None:
        source = f"git+https://github.com/ryancinsight/hermes.git#{OLD}"
        pinned = f"git+https://github.com/ryancinsight/leto?rev=abc#{OLD}"
        for revisions in ({source: "bad"}, {source + "0": NEW}, {pinned: NEW}):
            with self.subTest(revisions=revisions), self.assertRaisesRegex(
                    ValueError, "existing unqueried Git identity and full SHA"):
                sweep.retarget_sources(LOCK, revisions)


@unittest.skipUnless(shutil.which("cargo") and shutil.which("git"), "needs real Cargo and Git")
class RetargetMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="atlas-retarget-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        config = self.root / "gitconfig"
        config.write_text("", encoding="utf-8")
        environment = mock.patch.dict(os.environ, {
            "CARGO_HOME": str(self.root / "cargo-home"),
            "GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"})
        environment.start()
        self.addCleanup(environment.stop)
        for name, value in (("ROOT", self.root), ("LOG_ROOT", self.root / "output")):
            patch = mock.patch.object(sweep, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        self.moving = provider(self.root, "moving")
        self.old = git(self.moving, "rev-parse", "HEAD")
        self.consumer = self.root / "consumer"
        (self.consumer / "src").mkdir(parents=True)
        (self.consumer / "src/lib.rs").write_text("", encoding="utf-8")
        manifest = ('[package]\nname = "consumer"\nversion = "0.1.0"\nedition = "2024"\n'
                    '[dependencies]\nmoving = { git = ' + json.dumps(self.moving.as_uri()) + ' }\n')
        (self.consumer / "Cargo.toml").write_text(manifest, encoding="utf-8")
        self.cargo("generate-lockfile")
        self.original = (self.consumer / "Cargo.lock").read_bytes()
        records = sweep.lockfile.locked_package_records(self.original.decode())
        self.source = next(record["source"] for record in records if record["name"] == "moving")
        self.location = self.source[4:].rsplit("#", 1)[0]

    def cargo(self, *arguments: str) -> str:
        result = sweep.cargo(self.consumer, *arguments)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def commit_provider(self, files: dict[str, str]) -> str:
        for name, text in files.items():
            path = self.moving / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        git(self.moving, "add", "--", *files)
        git(self.moving, "commit", "-q", "-m", "advance")
        return git(self.moving, "rev-parse", "HEAD")

    def retarget(self, revision: str):
        (self.consumer / "Cargo.lock").write_bytes(self.original)
        package = sweep.LockedPackage("moving", "0.1.0", self.location, self.old)
        plan = sweep.Plan(self.consumer, self.old, (package,))
        return sweep.retarget_lock(plan, {"moving": revision}, self.consumer)

    def test_same_graph_matches_cargos_generated_lock_and_selected_identity(self) -> None:
        revision = self.commit_provider({"src/lib.rs": "pub fn second() {}\n"})
        self.cargo("update", "--package", "moving", "--precise", revision)
        generated = (self.consumer / "Cargo.lock").read_bytes()
        failure = self.retarget(revision)
        self.assertEqual((failure, (self.consumer / "Cargo.lock").read_bytes()), (None, generated))
        metadata = json.loads(self.cargo("metadata", "--locked", "--offline", "--format-version", "1"))
        package = next(package for package in metadata["packages"] if package["name"] == "moving")
        self.assertEqual(package["source"], self.source.rsplit("#", 1)[0] + "#" + revision)
        self.assertEqual(list(self.root.rglob("*.rlib")), [])

    def test_graph_growth_is_rejected_without_inventing_package_records(self) -> None:
        manifest = (self.moving / "Cargo.toml").read_text() + '[dependencies]\nhelper = { path = "helper" }\n'
        revision = self.commit_provider({
            "Cargo.toml": manifest,
            "helper/Cargo.toml": '[package]\nname = "helper"\nversion = "0.1.0"\nedition = "2024"\n',
            "helper/src/lib.rs": ""})
        self.cargo("update", "--package", "moving", "--precise", revision)
        failure = self.retarget(revision)
        self.assertEqual((failure.action, failure.ok), ("failed", False))
        self.assertIn("locked offline metadata", failure.detail)
        records = sweep.lockfile.locked_package_records((self.consumer / "Cargo.lock").read_text())
        self.assertEqual([record["name"] for record in records], ["consumer", "moving"])

    def test_an_uncached_commit_does_not_float_to_the_provider_branch(self) -> None:
        revision = self.commit_provider({"src/lib.rs": "pub fn uncached() {}\n"})
        failure = self.retarget(revision)
        self.assertEqual((failure.action, failure.ok), ("failed", False))
        self.assertIn("locked offline metadata", failure.detail)
        self.assertEqual(git(self.moving, "rev-parse", "HEAD"), revision)
