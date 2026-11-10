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
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parent.parent / "atlas-lock-sweep.py"
sys.path.insert(0, str(SCRIPT.parent))
from atlas_git_process import execute as execute_git
import process_tree
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
        for url in (
            "https://github.com/ryancinsight/Mnemosyne.GIT?branch=main",
            "https://github.com/ryancinsight/mnemosyne/",
        ):
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

    def test_query_pins_are_parsed_but_excluded_from_update_mode(self) -> None:
        source = f"git+https://GitHub.com/RyAnCiNsIgHt/Leto.GIT?tag=v1#{NEW}"
        lock = "version = 4\n" + package("pinned", "1.0.0", source)
        self.assertEqual(sweep.locked_packages(lock)[0].provider, "leto")
        self.assertEqual(sweep.first_party_packages(lock), [])

    def test_default_https_port_preserves_the_exact_identity_tuple(self) -> None:
        location = "https://GitHub.com:443/RyAnCiNsIgHt/Leto.GIT?branch=main"
        lock = "version = 4\n" + package("leto-ops", "0.9.0", f"git+{location}#{NEW}")
        identity = sweep.locked_packages(lock)[0]
        self.assertEqual(
            (identity.name, identity.version, identity.url, identity.rev, identity.provider),
            ("leto-ops", "0.9.0", location, NEW, "leto"),
        )

    def test_missing_source_is_a_valid_local_package(self) -> None:
        lock = "version = 4\n" + package("local", "1.0.0", None)
        self.assertEqual(sweep.locked_packages(lock), [])

    def test_malformed_first_party_identity_fails_closed(self) -> None:
        malformed = (
            "git+https://github.com/ryancinsight/hermes#not-a-commit",
            "git+https://github.com/ryancinsight/hermes",
        )
        for source in malformed:
            with self.subTest(source=source), self.assertRaisesRegex(
                ValueError, "unreadable first-party Git source identity"
            ):
                sweep.first_party_packages(
                    "version = 4\n" + package("hermes-simd", "0.5.0", source)
                )

    def test_first_party_path_shape_matrix(self) -> None:
        for path in ("/ryancinsight/leto", "/RyAnCiNsIgHt/Leto.GIT/"):
            source = f"git+https://github.com{path}#{OLD}"
            lock = "version = 4\n" + package("leto-ops", "0.9.0", source)
            with self.subTest(path=path):
                self.assertEqual(sweep.locked_packages(lock)[0].provider, "leto")

        malformed = (
            "/ryancinsight",
            "/ryancinsight//leto",
            "//ryancinsight/leto",
            "/ryancinsight/leto//",
            "/ryancinsight/leto/extra",
            "/ryancinsight/./leto",
            "/ryancinsight/../leto",
            "/%72yancinsight/leto",
            "/ryancinsight/Kwavers",
        )
        for path in malformed:
            source = f"git+https://github.com{path}#{OLD}"
            lock = "version = 4\n" + package("leto-ops", "0.9.0", source)
            with self.subTest(path=path), self.assertRaisesRegex(
                ValueError, "first-party Git source (?:identity|path)"
            ) as error:
                sweep.locked_packages(lock)
            self.assertNotIn(source, str(error.exception))

    def test_first_party_identity_rejects_raw_controls(self) -> None:
        locations = (
            r"ht\ntps://github.com/ryancinsight/leto",
            r"https://git\rhub.com/ryancinsight/leto",
            r"https://github.com/ryan\tcinsight/leto",
            r"https://github.com/ryancinsight/le\nto",
            r"\u0000https://github.com/ryancinsight/leto",
        )
        for location in locations:
            source = f"git+{location}#{OLD}"
            lock = "version = 4\n" + package("leto-ops", "0.9.0", source)
            with self.subTest(location=location), self.assertRaisesRegex(
                ValueError, "unreadable first-party Git source identity"
            ) as error:
                sweep.locked_packages(lock)
            self.assertNotIn(source, str(error.exception))

    def test_unsupported_first_party_transport_fails_without_echoing_source(self) -> None:
        for source in (
            f"git+ssh://git@github.com/ryancinsight/hermes#{OLD}",
            f"git+http://github.com/ryancinsight/hermes#{OLD}",
        ):
            lock = "version = 4\n" + package("hermes-simd", "0.5.0", source)
            with self.subTest(source=source), self.assertRaisesRegex(
                ValueError, "unsupported first-party Git source authority"
            ) as error:
                sweep.locked_packages(lock)
            self.assertNotIn(source, str(error.exception))

    def test_nondefault_or_malformed_first_party_port_fails_redacted(self) -> None:
        for port in ("444", "not-a-port"):
            source = f"git+https://github.com:{port}/ryancinsight/hermes#{OLD}"
            lock = "version = 4\n" + package("hermes-simd", "0.5.0", source)
            with self.subTest(port=port), self.assertRaisesRegex(
                ValueError, "first-party Git source authority"
            ) as error:
                sweep.locked_packages(lock)
            self.assertNotIn(source, str(error.exception))

    def test_similar_hosts_and_owners_are_not_first_party(self) -> None:
        lock = "version = 4\n" + "".join(
            (
                package("host", "cargo-owned", f"git+https://github.com.evil/ryancinsight/x#{OLD}"),
                package("owner", "cargo-owned", f"git+https://github.com/ryancinsight.evil/x#{OLD}"),
                package(
                    "path",
                    "cargo-owned",
                    f"git+https://example.invalid/github.com/ryancinsight/tool#{OLD}",
                ),
            )
        )
        self.assertEqual(sweep.locked_packages(lock), [])

    def test_third_party_source_payloads_are_opaque(self) -> None:
        lock = "version = 4\n" + "".join(
            (
                package("registry", "cargo-owned", "registry+https://exa mple.invalid/index"),
                package("other", "also-cargo-owned", f"git+https://example.invalid/other#{OLD}"),
            )
        )
        self.assertEqual(sweep.locked_packages(lock), [])

    def test_unknown_first_party_provider_is_preserved_for_caller_diagnosis(self) -> None:
        source = f"git+https://github.com/ryancinsight/not-registered#{OLD}"
        lock = "version = 4\n" + package("unknown", "1.0.0", source)
        self.assertEqual(sweep.locked_packages(lock)[0].provider, "not-registered")


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

    def test_lock_failure_restores_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "Cargo.lock"
            original = b"version = 4\r\n# exact\n"
            lock.write_bytes(b"changed\n")
            outcome = sweep.lock_failure(self.plan({"hermes": NEW}), lock, original, "rejected")
            self.assertEqual((outcome.action, outcome.ok, outcome.detail),
                             ("failed", False, "rejected"))
            self.assertEqual(lock.read_bytes(), original)

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


class InventoryTests(unittest.TestCase):
    def git(self, repo: Path, *args: str) -> str:
        result = execute_git(repo, ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *args), timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.decode().strip()

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="lock-inventory-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git(self.root, "init", "-q", "-b", "main")
        for name in ("provider", "consumer"):
            repo = self.root / "repos" / name
            repo.mkdir(parents=True)
            self.git(repo, "init", "-q", "-b", "main")
        self.commit_member("provider", "0.1.0")
        self.first_provider = self.git(self.root / "repos/provider", "rev-parse", "HEAD")
        self.commit_member("consumer", "0.1.0", self.first_provider)
        self.first_consumer = self.git(self.root / "repos/consumer", "rev-parse", "HEAD")
        (self.root / ".gitmodules").write_text("".join(
            f'[submodule "{name}"]\npath = repos/{name}\nurl = https://github.com/ryancinsight/{name}\n'
            for name in ("provider", "consumer")
        ), encoding="utf-8")
        self.git(self.root, "add", ".gitmodules")
        self.first_root = self.commit_pins()

    def commit_member(self, name: str, version: str, provider: str | None = None) -> None:
        repo = self.root / "repos" / name
        manifest = f'[package]\nname="{name}"\nversion="{version}"\nedition="2024"\n'
        lock = "version=4\n" + package(name, version, None)
        if provider is not None:
            manifest += f'[dependencies]\nprovider={{git="https://github.com/ryancinsight/provider",version="{version}"}}\n'
            lock += package("provider", version, "git+https://github.com/ryancinsight/provider#" + provider)
        (repo / "Cargo.toml").write_text(manifest, encoding="utf-8")
        (repo / "Cargo.lock").write_text(lock, encoding="utf-8")
        self.git(repo, "add", "Cargo.toml", "Cargo.lock")
        self.git(repo, "commit", "-qm", "Record inputs")

    def commit_pins(self) -> str:
        for name in ("provider", "consumer"):
            commit = self.git(self.root / "repos" / name, "rev-parse", "HEAD")
            self.git(self.root, "update-index", "--add", "--cacheinfo", f"160000,{commit},repos/{name}")
        self.git(self.root, "commit", "-qm", "Record pins")
        return self.git(self.root, "rev-parse", "HEAD")

    def test_revision_inputs_ignore_live_dirt_and_replacement_objects(self) -> None:
        self.commit_member("provider", "0.2.0")
        newer = self.git(self.root / "repos/provider", "rev-parse", "HEAD")
        self.commit_member("consumer", "0.2.0", newer)
        new_consumer = self.git(self.root / "repos/consumer", "rev-parse", "HEAD")
        new_root = self.commit_pins()
        self.git(self.root, "replace", self.first_root, new_root)
        self.git(self.root / "repos/consumer", "replace", self.first_consumer, new_consumer)
        (self.root / ".gitmodules").write_text("not the committed mapping", encoding="utf-8")
        (self.root / "repos/consumer/Cargo.lock").write_text("not TOML", encoding="utf-8")
        for revision, source, version in ((self.first_root, self.first_provider, "0.1.0"), (new_root, newer, "0.2.0")):
            with self.subTest(revision=revision):
                result = sweep.lock_inventory(self.root, revision)
                self.assertEqual(result["basis"], revision)
                self.assertEqual({row["member"] for row in result["members"]}, {"provider", "consumer"})
                consumer = next(row for row in result["members"] if row["member"] == "consumer")
                self.assertEqual(consumer["locks"], [{"path": "Cargo.lock", "packages": [{
                    "name": "provider", "version": version, "url": "https://github.com/ryancinsight/provider",
                    "rev": source, "provider": "provider",
                }]}])

    def test_inventory_cli_leaves_refs_and_index_unchanged(self) -> None:
        before = self.git(self.root, "show-ref")
        index = (self.root / ".git/index").read_bytes()
        result = process_tree.run([sys.executable, "-I", str(SCRIPT), "--inventory", "--revision", self.first_root],
                                  env={**os.environ, "ATLAS_STACK_ROOT": str(self.root)}, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["basis"], self.first_root)
        self.assertEqual(report["members"][0]["locks"][0]["packages"][0]["rev"], self.first_provider)
        self.assertEqual(self.git(self.root, "show-ref"), before)
        self.assertEqual((self.root / ".git/index").read_bytes(), index)

    def test_missing_promisor_blobs_refuse_without_fetching(self) -> None:
        source = self.root / "promisor-source"
        source.mkdir()
        self.git(source, "init", "-q", "-b", "main")
        (source / "Cargo.toml").write_text(
            '[package]\nname="consumer"\nversion="0.1.0"\nedition="2024"\n',
            encoding="utf-8",
        )
        (source / "Cargo.lock").write_text(
            "version=4\n" + package("consumer", "0.1.0", None), encoding="utf-8"
        )
        self.git(source, "add", "Cargo.toml", "Cargo.lock")
        self.git(source, "commit", "-qm", "Record inputs")
        self.git(source, "config", "uploadpack.allowFilter", "true")
        revision = self.git(source, "rev-parse", "HEAD")
        blobs = {
            self.git(source, "rev-parse", "HEAD:Cargo.toml"),
            self.git(source, "rev-parse", "HEAD:Cargo.lock"),
        }

        root = self.root / "promisor-root"
        root.mkdir()
        self.git(root, "init", "-q", "-b", "main")
        member = root / "repos" / "consumer"
        member.parent.mkdir()
        cloned = execute_git(
            self.root,
            ("clone", "-q", "--bare", "--filter=blob:none", source.as_uri(), str(member)),
            timeout=30,
        )
        self.assertEqual(cloned.returncode, 0, cloned.stderr)
        (root / ".gitmodules").write_text(
            '[submodule "consumer"]\npath = repos/consumer\n'
            'url = https://github.com/ryancinsight/consumer\n',
            encoding="utf-8",
        )
        self.git(root, "add", ".gitmodules")
        self.git(
            root,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{revision},repos/consumer",
        )
        self.git(root, "commit", "-qm", "Record pin")
        basis = self.git(root, "rev-parse", "HEAD")
        refs = self.git(root, "show-ref")
        member_refs = self.git(member, "show-ref")
        index = (root / ".git/index").read_bytes()
        no_fetch = {**os.environ, "GIT_NO_LAZY_FETCH": "1"}
        inherited_no_fetch = os.environ.get("GIT_NO_LAZY_FETCH")

        def missing(blob: str) -> bool:
            result = execute_git(
                member, ("--no-replace-objects", "cat-file", "-e", blob),
                env=no_fetch, timeout=10,
            )
            return result.returncode != 0

        self.assertTrue(all(missing(blob) for blob in blobs))
        with self.assertRaisesRegex(sweep.lockfile.GitUnavailable, "cat-file could not read"):
            sweep.lock_inventory(root, basis)
        self.assertTrue(all(missing(blob) for blob in blobs))
        self.assertEqual(self.git(root, "show-ref"), refs)
        self.assertEqual(self.git(member, "show-ref"), member_refs)
        self.assertEqual((root / ".git/index").read_bytes(), index)
        self.assertEqual(os.environ.get("GIT_NO_LAZY_FETCH"), inherited_no_fetch)

    def test_committed_lock_without_owner_rejects(self) -> None:
        repo = self.root / "repos/consumer"
        (repo / "nested").mkdir()
        (repo / "nested/Cargo.lock").write_text("version=4\n" + package("orphan", "0.1.0", None), encoding="utf-8")
        self.git(repo, "add", "nested/Cargo.lock")
        self.git(repo, "commit", "-qm", "Record orphan")
        with self.assertRaisesRegex(ValueError, "no readable standalone owner"):
            sweep.lock_inventory(self.root, self.commit_pins())

    def test_unregistered_first_party_source_rejects(self) -> None:
        repo = self.root / "repos/consumer"
        path = repo / "Cargo.lock"
        path.write_text(path.read_text(encoding="utf-8").replace("ryancinsight/provider", "ryancinsight/unregistered"), encoding="utf-8")
        self.git(repo, "add", "Cargo.lock")
        self.git(repo, "commit", "-qm", "Record unknown source")
        with self.assertRaisesRegex(ValueError, "not a registered provider"):
            sweep.lock_inventory(self.root, self.commit_pins())


if __name__ == "__main__":
    unittest.main()
