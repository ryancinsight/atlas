#!/usr/bin/env python3
"""Tests for atlas-lock-sweep.py's pure decisions.

The sweep's repository operations are exercised by running it; what unit
tests pin is every decision that could silently exclude or misplace a
consumer: which lock entries are first-party sources a sweep may move, which
of them are stale against the named targets, when an updated lock missed a
target, and what the branch, commit, and report look like. A wrong answer to
any of these is a consumer skipped without a row, or a lock committed at a
revision nobody named -- the failures the tool exists to prevent.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent.parent / "atlas-lock-sweep.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("atlas_lock_sweep", SCRIPT)
sweep = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
# dataclasses resolve `from __future__` annotations through sys.modules.
sys.modules[SPEC.name] = sweep
SPEC.loader.exec_module(sweep)

NL = chr(10)
OLD = "1" * 40
NEW = "2" * 40
MOVED = "3" * 40


def package(name: str, version: str, source: str | None) -> str:
    lines = ["[[package]]", f'name = "{name}"', f'version = "{version}"']
    if source is not None:
        lines.append(f'source = "{source}"')
    return NL.join(lines) + NL


def run_git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments], check=True, capture_output=True, text=True
    ).stdout.strip()


def commit_repository(repository: Path, files: dict[str, str]) -> str:
    repository.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
    run_git(repository, "config", "user.email", "test@example.com")
    run_git(repository, "config", "user.name", "Test")
    for name, text in files.items():
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    run_git(repository, "add", *files)
    run_git(repository, "commit", "--quiet", "-m", "fixture")
    return run_git(repository, "rev-parse", "HEAD")


def commit_meta(repository: Path, modules: str, pins: dict[str, str | None]) -> str:
    base = commit_repository(repository, {".gitmodules": modules})
    for name, pin in pins.items():
        entry = f"160000,{pin or base},repos/{name}"
        run_git(repository, "update-index", "--add", "--cacheinfo", entry)
    if pins:
        run_git(repository, "commit", "--quiet", "-m", "meta fixture")
    return run_git(repository, "rev-parse", "HEAD")


def gitmodules(*names: str) -> str:
    return "".join(f'[submodule "repos/{name}"]\npath = repos/{name}\nurl = local-{name}\n' for name in names)


LOCK = NL.join(
    [
        "version = 4",
        "",
        package("consumer", "0.1.0", None),
        package("hermes-simd", "0.5.0", f"git+https://github.com/ryancinsight/hermes.git#{OLD}"),
        package("hermes-simd-core", "0.5.0", f"git+https://github.com/ryancinsight/hermes.git#{OLD}"),
        package("mnemosyne-memory", "0.8.0", f"git+https://github.com/ryancinsight/Mnemosyne#{NEW}"),
        package("mnemosyne-memory", "0.7.0", f"git+https://github.com/ryancinsight/Mnemosyne.git#{OLD}"),
        package("pinned", "1.0.0", f"git+https://github.com/ryancinsight/leto?rev=abc#{OLD}"),
        package("serde", "1.0.0", "registry+https://github.com/rust-lang/crates.io-index"),
        package("other", "0.1.0", f"git+https://github.com/someone/other#{OLD}"),
    ]
)


class UrlTests(unittest.TestCase):
    def test_provider_name_ignores_suffix_case_and_trailing_slash(self) -> None:
        for url in ("https://github.com/ryancinsight/Mnemosyne.git", "https://github.com/ryancinsight/mnemosyne/"):
            self.assertEqual(sweep.provider_repo_name(url), "mnemosyne")


class LockTests(unittest.TestCase):
    def test_only_unpinned_first_party_git_entries_are_read(self) -> None:
        names = [(p.name, p.version, p.url) for p in sweep.first_party_packages(LOCK)]
        self.assertEqual(
            names,
            [
                ("hermes-simd", "0.5.0", "https://github.com/ryancinsight/hermes.git"),
                ("hermes-simd-core", "0.5.0", "https://github.com/ryancinsight/hermes.git"),
                ("mnemosyne-memory", "0.8.0", "https://github.com/ryancinsight/Mnemosyne"),
                ("mnemosyne-memory", "0.7.0", "https://github.com/ryancinsight/Mnemosyne.git"),
            ],
        )

    def test_the_spec_names_the_source_so_two_spellings_stay_distinct(self) -> None:
        specs = {p.spec for p in sweep.first_party_packages(LOCK) if p.name == "mnemosyne-memory"}
        self.assertEqual(
            specs,
            {
                "git+https://github.com/ryancinsight/Mnemosyne#mnemosyne-memory@0.8.0",
                "git+https://github.com/ryancinsight/Mnemosyne.git#mnemosyne-memory@0.7.0",
            },
        )


class RevisionIdentityTests(unittest.TestCase):
    targets = {"hermes": NEW, "mnemosyne": NEW}

    def finding(self, path: str, lock: str, fixture: bool = False):
        return sweep.revision_lock_findings("consumer", path, lock, self.targets, fixture)

    def test_same_version_source_drift_reports_exact_path_and_revisions(self) -> None:
        report, problems = self.finding(
            "Cargo.lock",
            "version = 4\n" + package(
                "hermes-simd", "0.5.0",
                f"git+https://github.com/ryancinsight/hermes#{OLD}",
            ),
        )
        self.assertEqual(report, "consumer/Cargo.lock: measured 1 first-party package(s)")
        expected = (
            f"consumer/Cargo.lock: hermes-simd locks hermes@{OLD}; selected {NEW}; "
            f"source git+https://github.com/ryancinsight/hermes#{OLD}"
        )
        self.assertEqual(problems, [expected])

    def test_nested_fuzz_lock_path_is_not_collapsed_to_the_root(self) -> None:
        source = f"git+https://github.com/ryancinsight/hermes#{OLD}"
        _, problems = self.finding(
            "fuzz/Cargo.lock", "version = 4\n" + package("hermes-simd", "0.5.0", source)
        )
        self.assertTrue(problems[0].startswith("consumer/fuzz/Cargo.lock:"))

    def test_queried_alias_and_url_case_resolve_to_the_registered_provider(self) -> None:
        for query in (f"rev={OLD}", "branch=main", "tag=v0.8.0"):
            with self.subTest(query=query):
                source = f"git+https://GitHub.com/RyAnCiNsIgHt/Mnemosyne.GIT?{query}#{OLD}"
                _, problems = self.finding(
                    "Cargo.lock", "version = 4\n" + package("mnemosyne-memory", "0.8.0", source)
                )
                expected = (
                    f"consumer/Cargo.lock: mnemosyne-memory locks mnemosyne@{OLD}; "
                    f"selected {NEW}; source {source}"
                )
                self.assertEqual(problems, [expected])

    def test_exact_source_is_reported_aligned(self) -> None:
        report, problems = self.finding(
            "Cargo.lock",
            "version = 4\n" + package(
                "hermes-simd", "0.5.0",
                f"git+https://github.com/ryancinsight/hermes.git#{NEW}",
            ),
        )
        self.assertEqual(report, "consumer/Cargo.lock: aligned 1 first-party package(s)")
        self.assertEqual(problems, [])

    def test_structural_path_fixture_with_git_identity_requires_unification(self) -> None:
        lock = "version = 4\n" + package(
            "hermes-simd", "0.5.0",
            f"git+https://github.com/ryancinsight/hermes#{NEW}",
        )
        texts = {
            "Cargo.toml": (
                '[package]\nname = "fixture"\nversion = "0.1.0"\n'
                '[dependencies]\nsibling = { path = "../../sibling" }\n'
            ),
            "Cargo.lock": lock,
        }
        standalone, exempt = sweep.lockfile.judge_locks(texts)
        self.assertEqual((standalone, exempt), ([], ["Cargo.lock"]))
        report, problems = self.finding("Cargo.lock", lock, "Cargo.lock" in exempt)
        self.assertEqual(report, "consumer/Cargo.lock: path fixture (1 first-party Git identities)")
        self.assertIn("path-unification required for hermes-simd", problems[0])

    def test_unknown_first_party_repository_fails_closed(self) -> None:
        source = f"git+https://github.com/ryancinsight/not-registered#{NEW}"
        _, problems = self.finding(
            "Cargo.lock", "version = 4\n" + package("unknown", "0.1.0", source)
        )
        self.assertIn("unknown registered first-party identity not-registered", problems[0])


class RevisionRepositoryTests(unittest.TestCase):
    def check_meta(
        self, modules: str, pins: dict[str, str | None],
        plain_members: tuple[str, ...] = (),
    ) -> sweep.RevisionCheck:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit_meta(root, modules, pins)
            for member in plain_members:
                (root / "repos" / member).mkdir(parents=True)
            return sweep.check_revision(root, "HEAD")

    def fixture(self, root: Path) -> tuple[Path, str, str]:
        provider = root / "repos" / "provider"
        provider_pin = commit_repository(
            provider,
            {
                "Cargo.toml": '[package]\nname = "provider"\nversion = "0.1.0"\n',
                "Cargo.lock": 'version = 4\n\n[[package]]\nname = "provider"\nversion = "0.1.0"\n',
            },
        )
        consumer = root / "repos" / "consumer"
        aligned_source = f"git+https://github.com/ryancinsight/provider#{provider_pin}"
        aligned = package("provider", "0.1.0", aligned_source)
        drift_source = f"git+https://github.com/ryancinsight/provider#{OLD}"
        drift = package("provider", "0.1.0", drift_source)
        consumer_pin = commit_repository(
            consumer,
            {
                "Cargo.toml": (
                    '[package]\nname = "consumer"\nversion = "0.1.0"\n'
                    '[dependencies]\nprovider = { git = "https://github.com/ryancinsight/provider" }\n'
                ),
                "Cargo.lock": 'version = 4\n\n[[package]]\nname = "consumer"\nversion = "0.1.0"\n' + aligned,
                "fuzz/Cargo.toml": (
                    '[package]\nname = "consumer-fuzz"\nversion = "0.1.0"\n'
                    '[dependencies]\nprovider = { git = "https://github.com/ryancinsight/provider" }\n'
                ),
                "fuzz/Cargo.lock": 'version = 4\n\n[[package]]\nname = "consumer-fuzz"\nversion = "0.1.0"\n' + drift,
            },
        )
        pins = {"provider": provider_pin, "consumer": consumer_pin}
        meta_pin = commit_meta(root, gitmodules("provider", "consumer"), pins)
        return provider, provider_pin, meta_pin

    def test_exact_revision_reads_every_nested_committed_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, provider_pin, meta_pin = self.fixture(root)
            result = sweep.check_revision(root, meta_pin)
        self.assertEqual(result.revision, meta_pin)
        self.assertEqual(result.locks, 3)
        self.assertIn("consumer/Cargo.lock: aligned 1 first-party package(s)", result.reports)
        self.assertEqual(
            result.problems,
            (
                "consumer/fuzz/Cargo.lock: provider locks "
                f"provider@{OLD}; selected {provider_pin}; source "
                f"git+https://github.com/ryancinsight/provider#{OLD}",
            ),
        )

    def test_unreadable_selected_member_object_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, _ = self.fixture(root)
            missing = "f" * 40
            run_git(root, "update-index", "--cacheinfo", f"160000,{missing},repos/provider")
            run_git(root, "commit", "--quiet", "-m", "missing provider object")
            result = sweep.check_revision(root, "HEAD")
        self.assertTrue(any("selected object cannot be read" in problem for problem in result.problems))

    def test_invalid_member_topologies_fail_closed(self) -> None:
        quoted = (
            '[submodule "repos/provider"]\n'
            'path = "repos/provider"\nurl = local-provider\n'
        )
        mixed_outside = gitmodules("provider") + (
            '[submodule "outside"]\npath = ../outside\nurl = local-outside\n'
        )
        traversal = (
            '[submodule "traversal"]\npath = repos/provider/../outside\nurl = local-outside\n'
        )
        missing_path = '[submodule "missing"]\nurl = local-missing\n'
        duplicate_field = (
            '[submodule "provider"]\npath = repos/provider\n'
            'path = repos/other\nurl = local-provider\n'
        )
        duplicate_path = gitmodules("provider") + (
            '[submodule "alias"]\npath = repos/provider\nurl = local-alias\n'
        )
        malformed = '[submodule "provider"\npath = repos/provider\n'
        cases = (
            (gitmodules("provider"), {"provider": None}, ("provider",),
             "no independent object repository"),
            (gitmodules(".."), {}, (), "unsafe registered member name '..'"),
            ("", {}, (), "no registered members"),
            (quoted, {}, (), "registered member projection is incomplete"),
            (mixed_outside, {"provider": None}, (), "unsupported submodule path '../outside'"),
            (traversal, {}, (), "unsupported submodule path 'repos/provider/../outside'"),
            (missing_path, {}, (), "has no path"),
            (duplicate_field, {}, (), "has multiple paths"),
            (duplicate_path, {}, (), "duplicate registered submodule path repos/provider"),
            (malformed, {}, (), "cannot parse .gitmodules"),
            (gitmodules("provider"), {"provider": None, "aaa-extra": None}, (),
             "unregistered gitlink repos/aaa-extra"),
            (gitmodules("provider"), {"provider": None, "nested/extra": None}, (),
             "unsupported gitlink repos/nested/extra"),
        )
        for modules, pins, plain_members, diagnostic in cases:
            with self.subTest(diagnostic=diagnostic):
                result = self.check_meta(modules, pins, plain_members)
            self.assertIn(diagnostic, result.problems[0])

class PlanTests(unittest.TestCase):
    def test_entries_behind_their_target_are_stale_and_entries_at_it_are_not(self) -> None:
        stale = sweep.stale_packages(LOCK, {"hermes": NEW, "mnemosyne": NEW})
        self.assertEqual(
            [(p.name, p.version) for p in stale],
            [("hermes-simd", "0.5.0"), ("hermes-simd-core", "0.5.0"), ("mnemosyne-memory", "0.7.0")],
        )

    def test_providers_that_are_not_targets_never_move(self) -> None:
        self.assertEqual(sweep.stale_packages(LOCK, {"leto": NEW, "other": NEW}), ())

    def test_a_lock_at_every_target_has_nothing_stale(self) -> None:
        self.assertEqual(sweep.stale_packages(LOCK, {"hermes": OLD}), ())

    def test_an_update_that_reached_every_target_has_no_misses(self) -> None:
        stale = sweep.stale_packages(LOCK, {"hermes": NEW})
        updated = LOCK.replace(f"hermes.git#{OLD}", f"hermes.git#{NEW}")
        self.assertEqual(sweep.unmet_targets(updated, stale, {"hermes": NEW}), [])

    def test_a_provider_head_past_the_named_merge_is_a_miss_for_every_entry(self) -> None:
        stale = sweep.stale_packages(LOCK, {"hermes": NEW})
        updated = LOCK.replace(f"hermes.git#{OLD}", f"hermes.git#{MOVED}")
        self.assertEqual(
            sweep.unmet_targets(updated, stale, {"hermes": NEW}),
            [
                "hermes-simd resolved 33333333, target hermes@22222222",
                "hermes-simd-core resolved 33333333, target hermes@22222222",
            ],
        )

    def test_each_source_past_its_target_is_pulled_back_once(self) -> None:
        stale = sweep.stale_packages(LOCK, {"hermes": NEW, "mnemosyne": NEW})
        updated = LOCK.replace(f"hermes.git#{OLD}", f"hermes.git#{MOVED}").replace(
            f"Mnemosyne.git#{OLD}", f"Mnemosyne.git#{NEW}"
        )
        self.assertEqual(
            sweep.pullbacks(updated, stale, {"hermes": NEW, "mnemosyne": NEW}),
            [("git+https://github.com/ryancinsight/hermes.git#hermes-simd@0.5.0", NEW)],
        )

    def test_sources_at_their_target_need_no_pullback(self) -> None:
        stale = sweep.stale_packages(LOCK, {"hermes": NEW})
        updated = LOCK.replace(f"hermes.git#{OLD}", f"hermes.git#{NEW}")
        self.assertEqual(sweep.pullbacks(updated, stale, {"hermes": NEW}), [])

    def test_one_spelling_left_behind_is_a_miss(self) -> None:
        stale = sweep.stale_packages(LOCK, {"mnemosyne": NEW})
        self.assertEqual(
            sweep.unmet_targets(LOCK, stale, {"mnemosyne": NEW}),
            ["mnemosyne-memory resolved 11111111, target mnemosyne@22222222"],
        )


class CommitTests(unittest.TestCase):
    def plan(self, targets: dict[str, str]):
        return sweep.Plan(Path("repos/leto"), OLD, sweep.stale_packages(LOCK, targets))

    def test_one_target_names_its_provider_and_revision(self) -> None:
        self.assertEqual(sweep.branch_name({"hermes": NEW}), "build/deps-hermes-22222222")

    def test_a_target_set_has_one_branch_independent_of_order(self) -> None:
        first = sweep.branch_name({"hermes": NEW, "mnemosyne": OLD})
        self.assertEqual(first, sweep.branch_name({"mnemosyne": OLD, "hermes": NEW}))
        self.assertTrue(first.startswith("build/deps-lock-sweep-"))
        self.assertNotEqual(first, sweep.branch_name({"hermes": NEW, "mnemosyne": MOVED}))

    def test_the_message_names_every_moved_provider_merge_and_the_item(self) -> None:
        targets = {"hermes": NEW, "mnemosyne": NEW, "leto": MOVED}
        message = sweep.commit_message(self.plan(targets), targets, "ITEM-1")
        lines = message.splitlines()
        self.assertEqual(lines[0], "build(deps): Advance first-party locks")
        self.assertLessEqual(len(lines[0]), 50)
        self.assertIn(f"Refs: hermes@{NEW}", lines)
        self.assertIn(f"Refs: mnemosyne@{NEW}", lines)
        self.assertNotIn(f"Refs: leto@{MOVED}", lines)
        self.assertIn("Item: ITEM-1", lines)
        self.assertTrue(lines[-1].startswith("Co-Authored-By: "))

    def test_a_single_provider_subject_names_it(self) -> None:
        message = sweep.commit_message(self.plan({"hermes": NEW}), {"hermes": NEW}, None)
        self.assertEqual(message.splitlines()[0], "build(deps): Update hermes to 22222222")
        self.assertNotIn("Item:", message)

    def test_line_endings_follow_the_committed_lock(self) -> None:
        self.assertEqual(sweep.with_line_endings_of(b"a\nb\n", b"x\r\ny\r\n"), b"x\ny\n")
        self.assertEqual(sweep.with_line_endings_of(b"a\r\nb\r\n", b"x\ny\n"), b"x\r\ny\r\n")


class ResumeTests(unittest.TestCase):
    targets = {"hermes": NEW}
    plan = sweep.Plan(Path("repos/leto"), OLD, sweep.stale_packages(LOCK, {"hermes": NEW}))
    url = "https://github.com/ryancinsight/leto/pull/7"

    def resume(self, remote: str, listed: str, open_prs: bool, opened=None):
        calls: list[list[str]] = []

        def gh(argv, **_options):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, listed, "")

        opener = opened or (lambda *_args: self.fail("no PR may be opened"))
        with mock.patch.object(sweep, "git", lambda *_args: remote), \
                mock.patch.object(sweep.subprocess, "run", gh), \
                mock.patch.object(sweep, "open_sweep_pull_request", opener):
            return sweep.resume(self.plan, self.targets, None, open_prs), calls

    def test_an_unpushed_branch_is_left_to_the_sweep(self) -> None:
        outcome, calls = self.resume("", "", True)
        self.assertIsNone(outcome)
        self.assertEqual(calls, [])

    def test_an_open_pr_on_the_branch_is_pending_and_nothing_is_redone(self) -> None:
        outcome, calls = self.resume(f"{NEW}\trefs/heads/build/deps-hermes-22222222", self.url + NL, True)
        self.assertEqual((outcome.action, outcome.ok), ("pending", True))
        self.assertIn(self.url, outcome.detail)
        self.assertEqual(calls[0][:5], ["gh", "pr", "list", "--head", "build/deps-hermes-22222222"])

    def test_a_pushed_branch_without_a_pr_gets_one(self) -> None:
        opened = sweep.Outcome("leto", "opened", self.url, True)
        outcome, _ = self.resume(f"{NEW}\trefs/heads/x", "", True, opened=lambda *_args: opened)
        self.assertEqual(outcome, opened)

    def test_a_dry_run_only_reports_the_missing_pr(self) -> None:
        outcome, _ = self.resume(f"{NEW}\trefs/heads/x", "", False)
        self.assertEqual((outcome.action, outcome.ok), ("would", True))


class ReportTests(unittest.TestCase):
    def test_report_lists_every_member_with_its_action(self) -> None:
        rows = [
            sweep.Outcome("leto", "opened", "https://github.com/ryancinsight/leto/pull/7", True),
            sweep.Outcome("kwavers", "failed", "cargo update: error: failed to select", False),
            sweep.Outcome("iris", "current", "every first-party source at its target", True),
        ]
        report = sweep.render_report({"hermes": NEW}, rows)
        self.assertEqual(report.splitlines()[0], "lock sweep -> hermes@22222222")
        for name in ("leto", "kwavers", "iris"):
            self.assertIn(name, report)
        self.assertEqual(len(report.splitlines()), 2 + len(rows))


if __name__ == "__main__":
    unittest.main()
