#!/usr/bin/env python3
"""Tests for the pull-request bump guard (ATLAS-PUB-011).

The registry is the published-drift tests' stub; everything else is real: a member
repository with base and head commits, `git archive`, and `cargo metadata --no-deps`.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_atlas_published_drift import Registry, git, make_crate

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-bump-guard.py"
SPEC = importlib.util.spec_from_file_location("atlas_bump_guard", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = guard
SPEC.loader.exec_module(guard)

ROOT_MANIFEST = ('[workspace]\nresolver = "2"\nmembers = ["crates/*"]\n'
                 '[workspace.dependencies]\nserde = "{serde}"\n')
ALPHA_MANIFEST = ('[package]\nname = "alpha"\nversion = "{version}"\nedition = "2021"\n'
                  '[dependencies]\nserde = {{ workspace = true }}\n')
BETA_MANIFEST = '[package]\nname = "beta"\nversion = "0.2.0"\nedition = "2021"\n'
ALPHA_SOURCE = "pub fn one() -> u32 { 1 }\n"
BETA_SOURCE = "pub fn two() -> u32 { 2 }\n"


def published_alpha(version: str = "0.1.0", source: str = ALPHA_SOURCE,
                    serde: str = "1.0") -> bytes:
    """alpha's `.crate`: its original manifest, cargo's normalized one, and its source."""
    original = ALPHA_MANIFEST.format(version=version)
    normalized = (f'[package]\nname = "alpha"\nversion = "{version}"\nedition = "2021"\n'
                  f'[dependencies.serde]\nversion = "{serde}"\n')
    return make_crate("alpha", version, {"src/lib.rs": source.encode(),
                                         "Cargo.toml.orig": original.encode(),
                                         "Cargo.toml": normalized.encode()})


def published_beta(source: str = BETA_SOURCE) -> bytes:
    return make_crate("beta", "0.2.0", {"src/lib.rs": source.encode(),
                                        "Cargo.toml.orig": BETA_MANIFEST.encode(),
                                        "Cargo.toml": BETA_MANIFEST.encode()})


class BumpGuardTestCase(unittest.TestCase):
    """A member pull request: `base` is the merge target, `head` the pull request."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="atlas-bump-guard-test-")
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name).resolve() / "member"
        config = self.repo.parent / "gitconfig"
        config.write_text("", encoding="utf-8")
        patcher = mock.patch.dict(os.environ, {
            "GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main", "--quiet")
        self.commit({
            "Cargo.toml": ROOT_MANIFEST.format(serde="1.0"),
            "crates/alpha/Cargo.toml": ALPHA_MANIFEST.format(version="0.1.0"),
            "crates/alpha/src/lib.rs": ALPHA_SOURCE,
            # beta's source has moved past its published copy before this pull request.
            "crates/beta/Cargo.toml": BETA_MANIFEST,
            "crates/beta/src/lib.rs": "pub fn two() -> u32 { 22 }\n",
        })
        self.base = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "switch", "--quiet", "-c", "pr")

    def commit(self, files: dict[str, str]) -> str:
        for path, text in files.items():
            target = self.repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "--quiet", "-m", "c")
        return git(self.repo, "rev-parse", "HEAD")

    def run_guard(self, registry: Registry, base: str | None = None) -> tuple[int, str, str]:
        head = git(self.repo, "rev-parse", "HEAD")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = guard.main(["--repo", str(self.repo), "--base", base or self.base,
                                 "--head", head], registry)
        return status, out.getvalue(), err.getvalue()

    @staticmethod
    def registry(alpha: bytes | None = None, **overrides) -> Registry:
        return Registry({"alpha": ["0.1.0"], "beta": ["0.2.0"]},
                        {("alpha", "0.1.0"): alpha or published_alpha(),
                         ("beta", "0.2.0"): published_beta()}, **overrides)

    def test_a_source_change_at_an_indexed_version_fails_naming_the_crate(self) -> None:
        self.commit({"crates/alpha/src/lib.rs": "pub fn one() -> u32 { 11 }\n"})
        status, out, err = self.run_guard(self.registry())
        self.assertEqual(status, 1)
        self.assertEqual(out, "- `alpha` 0.1.0: published-drifted\n")
        self.assertEqual(err, "alpha 0.1.0: bump required; crates.io already carries 0.1.0 "
                              "and the source differs from it (changed src/lib.rs)\n")

    def test_a_source_change_with_the_version_moved_passes(self) -> None:
        self.commit({"crates/alpha/src/lib.rs": "pub fn one() -> u32 { 11 }\n",
                     "crates/alpha/Cargo.toml": ALPHA_MANIFEST.format(version="0.1.1")})
        status, out, err = self.run_guard(self.registry())
        self.assertEqual((status, out, err), (0, "- `alpha` 0.1.1: unpublished-version\n", ""))

    def test_a_source_change_to_a_never_published_crate_passes(self) -> None:
        self.commit({"crates/alpha/src/lib.rs": "pub fn one() -> u32 { 11 }\n"})
        registry = Registry({"beta": ["0.2.0"]}, {("beta", "0.2.0"): published_beta()})
        status, out, err = self.run_guard(registry)
        self.assertEqual((status, out, err), (0, "- `alpha` 0.1.0: never-published\n", ""))

    def test_drift_in_an_untouched_crate_does_not_fail_the_pull_request(self) -> None:
        # alpha changes back to what crates.io holds; beta, drifted at the base, is
        # not part of the pull request and is never asked about.
        published = "pub fn one() -> u32 { 7 }\n"
        self.commit({"crates/alpha/src/lib.rs": published})
        registry = self.registry(published_alpha(source=published))
        status, out, err = self.run_guard(registry)
        self.assertEqual((status, out, err), (0, "- `alpha` 0.1.0: published-current\n", ""))
        self.assertFalse([url for url in registry.asked if "beta" in url])

    def test_crates_the_base_moved_after_the_fork_are_not_selected(self) -> None:
        self.commit({"crates/alpha/src/lib.rs": "pub fn one() -> u32 { 11 }\n",
                     "crates/alpha/Cargo.toml": ALPHA_MANIFEST.format(version="0.1.1")})
        git(self.repo, "switch", "--quiet", "main")
        moved = self.commit({"crates/beta/src/lib.rs": "pub fn two() -> u32 { 222 }\n"})
        git(self.repo, "switch", "--quiet", "pr")
        registry = self.registry()
        status, out, err = self.run_guard(registry, base=moved)
        self.assertEqual((status, out, err), (0, "- `alpha` 0.1.1: unpublished-version\n", ""))
        self.assertFalse([url for url in registry.asked if "beta" in url])

    def test_an_inherited_requirement_change_selects_and_fails_the_crate(self) -> None:
        # Only the workspace root changes; alpha's own manifest and source do not.
        self.commit({"Cargo.toml": ROOT_MANIFEST.format(serde="1.1")})
        status, out, err = self.run_guard(self.registry())
        self.assertEqual(status, 1)
        self.assertEqual(out, "- `alpha` 0.1.0: published-drifted\n")
        self.assertEqual(err, "alpha 0.1.0: bump required; crates.io already carries 0.1.0 "
                              "and the source differs from it (dependency requirements "
                              "serde: req 1.0 -> ^1.1)\n")

    def test_a_pull_request_without_crate_changes_asks_nothing(self) -> None:
        self.commit({"README.md": "docs\n"})
        registry = self.registry()
        status, out, err = self.run_guard(registry)
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(out, "No publishable crate's source, manifest, or dependency "
                              "requirements changed.\n")
        self.assertEqual(registry.asked, [])

    def test_a_crate_at_the_repository_root_is_selected_by_its_own_paths(self) -> None:
        # A single-crate member: the package directory is the root, so its paths are
        # `src/**` and `Cargo.toml` themselves. Its manifest pins serde directly, so it
        # also differs from the published `Cargo.toml.orig`, which inherits it.
        git(self.repo, "rm", "-r", "--quiet", "crates")
        self.base = self.commit({
            "Cargo.toml": ALPHA_MANIFEST.replace("{{ workspace = true }}", '"1.0"')
            .format(version="0.1.0"),
            "src/lib.rs": ALPHA_SOURCE})
        self.commit({"src/lib.rs": "pub fn one() -> u32 { 11 }\n"})
        status, out, err = self.run_guard(self.registry())
        self.assertEqual(status, 1)
        self.assertEqual(out, "- `alpha` 0.1.0: published-drifted\n")
        self.assertEqual(err, "alpha 0.1.0: bump required; crates.io already carries 0.1.0 "
                              "and the source differs from it (changed Cargo.toml, src/lib.rs)\n")

    def test_a_registry_failure_is_a_measurement_failure_not_a_pass(self) -> None:
        self.commit({"crates/alpha/src/lib.rs": "pub fn one() -> u32 { 11 }\n"})
        url = guard.drift.CRATE_URL.format(name="alpha", version="0.1.0")
        status, out, err = self.run_guard(self.registry(status={url: 503}))
        self.assertEqual((status, out), (2, ""))
        self.assertIn("HTTP 503 for alpha 0.1.0", err)


if __name__ == "__main__":
    unittest.main()
