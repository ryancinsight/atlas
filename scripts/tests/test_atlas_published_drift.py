#!/usr/bin/env python3
"""Tests for the published-drift scan (ATLAS-PUB-011).

The registry is stubbed: a fetch function answers index and `.crate` URLs from
in-memory fixtures and records every URL it is asked. Everything else is real --
`.crate` archives are built with tarfile, source trees are written to a tempdir,
and the stack cases drive `main` against throwaway git repositories (local paths
stand in for remote URLs, which is what `ls-remote` reads) and a real
`cargo metadata --no-deps`.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-published-drift.py"
SPEC = importlib.util.spec_from_file_location("atlas_published_drift", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
tool = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tool
SPEC.loader.exec_module(tool)

IDENT = ("-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false")


def make_crate(name: str, version: str, files: dict[str, bytes]) -> bytes:
    """A `.crate` (gzip tar) whose entries sit under `<name>-<version>/`."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for path, data in files.items():
            entry = tarfile.TarInfo(f"{name}-{version}/{path}")
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
    return buffer.getvalue()


def index_body(name: str, versions: list[str]) -> bytes:
    return "".join(json.dumps({"name": name, "vers": v}) + "\n" for v in versions).encode()


OWNERS_URL = "https://crates.io/api/v1/crates/{name}/owners"


class Registry:
    """Answers index, owners, and `.crate` URLs from fixtures; records every URL asked.

    Every indexed name is owned by the tool's default owner unless `owners` says otherwise.
    """

    def __init__(self, index: dict[str, list[str]], crates: dict[tuple[str, str], bytes] | None = None,
                 status: dict[str, int] | None = None,
                 owners: dict[str, list[str]] | None = None) -> None:
        self.index, self.crates, self.status, self.asked = index, crates or {}, status or {}, []
        self.owners = {name: [tool.DEFAULT_OWNER] for name in index} | (owners or {})

    def __call__(self, url: str) -> tuple[int, bytes]:
        self.asked.append(url)
        if url in self.status:
            return self.status[url], b""
        for name, logins in self.owners.items():
            if url == OWNERS_URL.format(name=name):
                return 200, json.dumps({"users": [{"login": login} for login in logins]}).encode()
        if url.startswith("https://index.crates.io/"):
            path = url.removeprefix("https://index.crates.io/")
            for name, versions in self.index.items():
                if tool.crates_pending.index_path(name) == path:
                    return 200, index_body(name, versions)
            return 404, b""
        for (name, version), body in self.crates.items():
            if url == tool.CRATE_URL.format(name=name, version=version):
                return 200, body
        return 404, b""


MANIFEST = b'[package]\nname = "demo"\nversion = "0.1.0"\n'
SOURCE = {"src/lib.rs": b"pub fn one() -> u32 { 1 }\n", "src/util/mod.rs": b"pub mod x;\n"}


class MeasureCrateTestCase(unittest.TestCase):
    """One crate's source against its registry copy."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="atlas-published-drift-test-")
        self.addCleanup(self._tmp.cleanup)
        self.package = Path(self._tmp.name)

    def write_tree(self, source: dict[str, bytes], manifest: bytes = MANIFEST) -> None:
        for path, data in source.items():
            target = self.package / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (self.package / "Cargo.toml").write_bytes(manifest)

    def measure(self, published: dict[str, bytes]):
        crate = make_crate("demo", "0.1.0", published)
        registry = Registry({"demo": ["0.0.9", "0.1.0"]}, {("demo", "0.1.0"): crate})
        reading = tool.measure_crate("demo", "0.1.0", "Cargo.toml", self.package, registry)
        return reading, registry

    @staticmethod
    def published() -> dict[str, bytes]:
        return {**SOURCE, "Cargo.toml.orig": MANIFEST}

    def test_identical_source_reads_as_not_drifted(self) -> None:
        self.write_tree(SOURCE)
        reading, _ = self.measure(self.published())
        self.assertEqual(reading.status, tool.PUBLISHED_CURRENT)
        self.assertEqual(reading.drift, tool.Drift())
        self.assertEqual(reading.latest_published, "0.1.0")

    def test_changed_source_file_reads_as_drifted(self) -> None:
        self.write_tree({**SOURCE, "src/lib.rs": b"pub fn one() -> u32 { 2 }\n"})
        reading, _ = self.measure(self.published())
        self.assertEqual(reading.status, tool.PUBLISHED_DRIFTED)
        self.assertEqual(reading.drift, tool.Drift(changed=("src/lib.rs",)))

    def test_changed_manifest_reads_as_drifted(self) -> None:
        self.write_tree(SOURCE, manifest=MANIFEST + b'serde = "1"\n')
        reading, _ = self.measure(self.published())
        self.assertEqual(reading.status, tool.PUBLISHED_DRIFTED)
        self.assertEqual(reading.drift, tool.Drift(changed=("Cargo.toml",)))

    def test_added_source_file_reads_as_drifted(self) -> None:
        self.write_tree({**SOURCE, "src/new.rs": b"pub fn two() {}\n"})
        reading, _ = self.measure(self.published())
        self.assertEqual(reading.status, tool.PUBLISHED_DRIFTED)
        self.assertEqual(reading.drift, tool.Drift(added=("src/new.rs",)))

    def test_removed_source_file_reads_as_drifted(self) -> None:
        self.write_tree({"src/lib.rs": SOURCE["src/lib.rs"]})
        reading, _ = self.measure(self.published())
        self.assertEqual(reading.status, tool.PUBLISHED_DRIFTED)
        self.assertEqual(reading.drift, tool.Drift(removed=("src/util/mod.rs",)))

    def test_a_difference_only_in_ignored_files_reads_as_not_drifted(self) -> None:
        self.write_tree(SOURCE)
        (self.package / "Cargo.lock").write_bytes(b"tree lock\n")
        (self.package / "README.md").write_bytes(b"tree readme\n")
        published = self.published()
        published[".cargo_vcs_info.json"] = b'{"git":{"sha1":"abc"}}'
        published["Cargo.lock"] = b"registry lock\n"
        published["Cargo.toml"] = b'[package]\nname = "demo"\nversion = "0.1.0"\nreadme = "x"\n'
        published["build.rs"] = b"fn main() {}\n"
        reading, _ = self.measure(published)
        self.assertEqual(reading.status, tool.PUBLISHED_CURRENT)
        self.assertEqual(reading.drift, tool.Drift())

    def test_line_endings_alone_do_not_read_as_drift(self) -> None:
        self.write_tree({"src/lib.rs": b"a\nb\n"}, manifest=b"[package]\nname = \"demo\"\n")
        published = {"src/lib.rs": b"a\r\nb\r\n", "Cargo.toml.orig": b"[package]\r\nname = \"demo\"\r\n"}
        reading, _ = self.measure(published)
        self.assertEqual(reading.drift, tool.Drift())

    def test_never_published_crate_is_reported_and_downloads_nothing(self) -> None:
        self.write_tree(SOURCE)
        registry = Registry({})
        reading = tool.measure_crate("demo", "0.1.0", "Cargo.toml", self.package, registry)
        self.assertEqual(reading.status, tool.NEVER_PUBLISHED)
        self.assertIsNone(reading.drift)
        self.assertIsNone(reading.latest_published)
        self.assertEqual(registry.asked, ["https://index.crates.io/de/mo/demo"])

    def test_version_absent_from_the_index_is_unpublished_and_names_the_latest(self) -> None:
        self.write_tree(SOURCE)
        registry = Registry({"demo": ["0.1.0", "0.10.0", "0.9.0", "0.10.0-rc.1"]})
        reading = tool.measure_crate("demo", "0.2.0", "Cargo.toml", self.package, registry)
        self.assertEqual(reading.status, tool.UNPUBLISHED_VERSION)
        self.assertEqual(reading.latest_published, "0.10.0")
        self.assertEqual(registry.asked, ["https://index.crates.io/de/mo/demo",
                                          OWNERS_URL.format(name="demo")])

    def test_a_name_another_account_owns_is_foreign_and_never_compared(self) -> None:
        self.write_tree(SOURCE)
        crate = make_crate("demo", "0.1.0", self.published())
        registry = Registry({"demo": ["0.1.0"]}, {("demo", "0.1.0"): crate},
                            owners={"demo": ["someone-else", "another"]})
        reading = tool.measure_crate("demo", "0.1.0", "Cargo.toml", self.package, registry)
        self.assertEqual(reading.status, tool.FOREIGN_NAME)
        self.assertIsNone(reading.drift)
        self.assertIsNone(reading.latest_published)
        self.assertEqual(registry.asked, ["https://index.crates.io/de/mo/demo",
                                          OWNERS_URL.format(name="demo")])

    def test_a_name_with_no_owner_at_all_is_foreign(self) -> None:
        self.write_tree(SOURCE)
        registry = Registry({"demo": ["0.1.0"]}, owners={"demo": []})
        reading = tool.measure_crate("demo", "0.1.0", "Cargo.toml", self.package, registry)
        self.assertEqual(reading.status, tool.FOREIGN_NAME)

    def test_the_expected_owner_comes_from_the_argument(self) -> None:
        self.write_tree(SOURCE)
        crate = make_crate("demo", "0.1.0", self.published())
        registry = Registry({"demo": ["0.1.0"]}, {("demo", "0.1.0"): crate},
                            owners={"demo": ["someone-else"]})
        reading = tool.measure_crate("demo", "0.1.0", "Cargo.toml", self.package, registry,
                                     owner="someone-else")
        self.assertEqual(reading.status, tool.PUBLISHED_CURRENT)

    def test_an_owned_name_is_compared_with_its_crate(self) -> None:
        self.write_tree({**SOURCE, "src/lib.rs": b"pub fn one() -> u32 { 2 }\n"})
        reading, registry = self.measure(self.published())
        self.assertEqual(reading.status, tool.PUBLISHED_DRIFTED)
        self.assertEqual(registry.asked, [
            "https://index.crates.io/de/mo/demo",
            OWNERS_URL.format(name="demo"),
            tool.CRATE_URL.format(name="demo", version="0.1.0"),
        ])

    def test_owners_outage_fails_instead_of_reading_as_owned(self) -> None:
        self.write_tree(SOURCE)
        registry = Registry({"demo": ["0.1.0"]}, status={OWNERS_URL.format(name="demo"): 503})
        with self.assertRaisesRegex(tool.RegistryError, "owners API returned HTTP 503 for demo"):
            tool.measure_crate("demo", "0.1.0", "Cargo.toml", self.package, registry)

    def test_index_outage_fails_instead_of_reading_as_not_drifted(self) -> None:
        self.write_tree(SOURCE)
        registry = Registry({"demo": ["0.1.0"]}, status={"https://index.crates.io/de/mo/demo": 503})
        with self.assertRaisesRegex(tool.RegistryError, "HTTP 503 for demo"):
            tool.measure_crate("demo", "0.1.0", "Cargo.toml", self.package, registry)

    def test_missing_crate_file_for_an_indexed_version_fails(self) -> None:
        self.write_tree(SOURCE)
        registry = Registry({"demo": ["0.1.0"]})
        with self.assertRaisesRegex(tool.RegistryError, "HTTP 404 for demo 0.1.0"):
            tool.measure_crate("demo", "0.1.0", "Cargo.toml", self.package, registry)

    def test_corrupt_crate_fails(self) -> None:
        self.write_tree(SOURCE)
        registry = Registry({"demo": ["0.1.0"]}, {("demo", "0.1.0"): b"not gzip"})
        with self.assertRaisesRegex(tool.RegistryError, "unreadable"):
            tool.measure_crate("demo", "0.1.0", "Cargo.toml", self.package, registry)

    def test_crate_entry_outside_its_directory_fails(self) -> None:
        self.write_tree(SOURCE)
        wrong = make_crate("other", "0.1.0", {"src/lib.rs": b""})
        registry = Registry({"demo": ["0.1.0"]}, {("demo", "0.1.0"): wrong})
        with self.assertRaisesRegex(tool.RegistryError, "outside demo-0.1.0/"):
            tool.measure_crate("demo", "0.1.0", "Cargo.toml", self.package, registry)


class HttpTestCase(unittest.TestCase):
    def test_request_carries_only_the_tool_user_agent(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b"body"
        with mock.patch.object(tool.urllib.request, "urlopen", return_value=response) as opened:
            self.assertEqual(tool.http_get("https://index.crates.io/de/mo/demo"), (200, b"body"))
        request = opened.call_args.args[0]
        self.assertEqual(request.full_url, "https://index.crates.io/de/mo/demo")
        self.assertEqual(request.headers,
                         {"User-agent": "atlas-published-drift (github.com/ryancinsight/atlas)"})

    def test_http_error_status_is_an_answer_and_is_not_retried(self) -> None:
        not_found = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
        with mock.patch.object(tool.urllib.request, "urlopen", side_effect=not_found) as opened, \
                mock.patch.object(tool.time, "sleep") as slept:
            self.assertEqual(tool.http_get("https://x"), (404, b""))
        self.assertEqual((opened.call_count, slept.call_count), (1, 0))

    def test_transport_failure_retries_with_doubling_backoff_then_is_an_error(self) -> None:
        with mock.patch.object(tool.urllib.request, "urlopen",
                               side_effect=urllib.error.URLError("refused")) as opened, \
                mock.patch.object(tool.time, "sleep") as slept, \
                mock.patch.object(tool.random, "uniform", return_value=1.0):
            with self.assertRaisesRegex(tool.RegistryError, r"refused.*after 5 attempts"):
                tool.http_get("https://x")
        self.assertEqual(opened.call_count, 5)
        self.assertEqual([call.args[0] for call in slept.call_args_list], [2.0, 4.0, 8.0, 16.0])

    def test_a_reset_connection_that_recovers_returns_the_answer(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b"owners"
        reset = ConnectionResetError(10054, "forcibly closed")
        with mock.patch.object(tool.urllib.request, "urlopen",
                               side_effect=[reset, reset, response]) as opened, \
                mock.patch.object(tool.time, "sleep") as slept:
            self.assertEqual(tool.http_get("https://x"), (200, b"owners"))
        self.assertEqual((opened.call_count, slept.call_count), (3, 2))


class ThrottleTestCase(unittest.TestCase):
    def test_a_second_api_request_waits_out_the_rest_of_the_interval(self) -> None:
        throttle = tool.ApiThrottle(interval=1.0)
        clock = iter([10.0, 10.25, 11.0])
        slept: list[float] = []
        with mock.patch.object(tool.time, "monotonic", side_effect=lambda: next(clock)), \
                mock.patch.object(tool.time, "sleep", side_effect=slept.append):
            throttle.wait()
            throttle.wait()
        self.assertEqual(slept, [0.75])

    def test_only_api_urls_pass_through_the_throttle(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b"{}"
        with mock.patch.object(tool.urllib.request, "urlopen", return_value=response), \
                mock.patch.object(tool.API_THROTTLE, "wait") as wait:
            tool.http_get("https://index.crates.io/de/mo/demo")
            tool.http_get("https://static.crates.io/crates/demo/demo-0.1.0.crate")
            self.assertEqual(wait.call_count, 0)
            tool.http_get("https://crates.io/api/v1/crates/demo/owners")
            self.assertEqual(wait.call_count, 1)


def package(name: str, dependencies: list[dict]) -> dict:
    return {"name": name, "dependencies": dependencies}


def dependency(name: str, req: str, kind: str | None = None, rename: str | None = None) -> dict:
    return {"name": name, "req": req, "kind": kind, "rename": rename}


def reading(name: str, crates: list[str], packages: list[dict]) -> "tool.MemberReading":
    return tool.MemberReading(
        name, "main", "0" * 40,
        [tool.CrateReading(c, "0.1.0", "Cargo.toml", tool.PUBLISHED_CURRENT) for c in crates],
        packages)


class ReverseEdgesTestCase(unittest.TestCase):
    def test_edges_name_the_requiring_crate_requirement_kind_and_rename(self) -> None:
        provider = reading("provider", ["prov"], [package("prov", [])])
        consumer = reading("consumer", ["con", "con-tool"], [
            package("con", [dependency("prov", "^0.4.1")]),
            package("con-tool", [dependency("prov", ">=0.3, <0.5", kind="dev", rename="p")]),
        ])
        tool.reverse_edges([provider, consumer])
        self.assertEqual(provider.crates[0].dependents, [
            {"member": "consumer", "crate": "con", "requirement": "^0.4.1",
             "kind": "normal", "rename": None},
            {"member": "consumer", "crate": "con-tool", "requirement": ">=0.3, <0.5",
             "kind": "dev", "rename": "p"},
        ])
        self.assertEqual(consumer.crates[0].dependents, [])

    def test_a_member_requiring_its_own_crate_is_not_a_reverse_edge(self) -> None:
        member = reading("m", ["a", "b"], [package("b", [dependency("a", "^0.1")])])
        tool.reverse_edges([member])
        self.assertEqual(member.crates[0].dependents, [])

    def test_a_dependency_on_a_non_stack_crate_is_ignored(self) -> None:
        member = reading("m", ["a"], [package("a", [dependency("serde", "^1")])])
        other = reading("o", ["b"], [package("b", [dependency("serde", "^1")])])
        tool.reverse_edges([member, other])
        self.assertEqual([c.dependents for m in (member, other) for c in m.crates], [[], []])

    def test_markdown_lists_each_dependent_with_its_requirement(self) -> None:
        provider = reading("provider", ["prov"], [package("prov", [])])
        consumer = reading("consumer", ["con"], [
            package("con", [dependency("prov", "^0.4.1", rename="p")])])
        tool.reverse_edges([provider, consumer])
        self.assertEqual(tool.dependents_cell(provider.crates[0].dependents),
                         "consumer: con as p `^0.4.1`")


class VersionOrderTestCase(unittest.TestCase):
    def test_numeric_components_order_numerically_and_prereleases_sort_below(self) -> None:
        versions = ["0.9.0", "0.10.0", "0.10.0-rc.1", "0.2.15"]
        self.assertEqual(sorted(versions, key=tool.version_key),
                         ["0.2.15", "0.9.0", "0.10.0-rc.1", "0.10.0"])


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *IDENT, *args], capture_output=True,
                          encoding="utf-8", errors="replace")
    assert proc.returncode == 0, f"git {args}: {proc.stderr}"
    return proc.stdout.strip()


class StackTestCase(unittest.TestCase):
    """`main` over real repositories: members are read at their remote default tip."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="atlas-published-drift-stack-")
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()
        config = self.base / "gitconfig"
        config.write_text("", encoding="utf-8")
        patcher = mock.patch.dict(os.environ, {
            "GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.origins = self.base / "origins"
        self.root = self.base / "atlas"

    def commit_files(self, repo: Path, files: dict[str, str], message: str = "c") -> None:
        for path, text in files.items():
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
        git(repo, "add", "-A")
        git(repo, "commit", "--quiet", "-m", message)

    def origin(self, name: str, files: dict[str, str]) -> Path:
        repo = self.origins / name
        repo.mkdir(parents=True)
        git(repo, "init", "-b", "trunk", "--quiet")
        self.commit_files(repo, files)
        return repo

    def build_stack(self, members: dict[str, dict[str, str]]) -> dict[str, Path]:
        origins = {name: self.origin(name, files) for name, files in members.items()}
        modules = "".join(
            f'[submodule "repos/{n}"]\n\tpath = repos/{n}\n\turl = {o.as_posix()}\n'
            for n, o in origins.items())
        atlas_origin = self.origin("atlas", {".gitmodules": modules})
        subprocess.run(["git", "clone", "--quiet", atlas_origin.as_posix(), str(self.root)],
                       check=True, capture_output=True)
        for name, origin in origins.items():
            subprocess.run(["git", "clone", "--quiet", origin.as_posix(),
                            str(self.root / "repos" / name)], check=True, capture_output=True)
        return origins

    def run_tool(self, registry: Registry, *extra: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = tool.main(["--stack-root", str(self.root), "--jobs", "2", *extra], registry)
        return status, out.getvalue(), err.getvalue()

    ALPHA = {
        "Cargo.toml": '[package]\nname = "alpha"\nversion = "0.1.0"\n',
        "src/lib.rs": "pub fn one() -> u32 { 1 }\n",
    }
    BETA = {
        "Cargo.toml": '[workspace]\nresolver = "2"\nmembers = ["crates/*"]\n',
        "crates/beta/Cargo.toml": (
            '[package]\nname = "beta"\nversion = "0.2.0"\n'
            '[dependencies]\na = { package = "alpha", version = "0.1" }\n'),
        "crates/beta/src/lib.rs": "pub fn two() -> u32 { 2 }\n",
        "crates/hidden/Cargo.toml": '[package]\nname = "hidden"\nversion = "0.1.0"\npublish = false\n',
        "crates/hidden/src/lib.rs": "",
    }

    def alpha_registry(self, published_source: str) -> Registry:
        crate = make_crate("alpha", "0.1.0", {
            "src/lib.rs": published_source.encode(),
            "Cargo.toml.orig": self.ALPHA["Cargo.toml"].encode(),
            "Cargo.toml": b"normalized",
        })
        return Registry({"alpha": ["0.1.0"]}, {("alpha", "0.1.0"): crate})

    def test_drift_is_measured_at_the_remote_tip_with_dependents_and_exit_status(self) -> None:
        origins = self.build_stack({"alpha": self.ALPHA, "beta": self.BETA})
        # The working tree is dirty and the member origin has moved past the clone: neither
        # the dirt nor the clone's stale checkout is what the scan measures.
        (self.root / "repos" / "alpha" / "src" / "lib.rs").write_text("dirt\n", encoding="utf-8")
        self.commit_files(origins["alpha"], {"src/lib.rs": "pub fn one() -> u32 { 11 }\n"})
        tip = git(origins["alpha"], "rev-parse", "HEAD")

        status, out, err = self.run_tool(self.alpha_registry("pub fn one() -> u32 { 1 }\n"))

        self.assertEqual((status, err), (1, ""))
        document = json.loads(out)
        self.assertEqual(document["atlas_revision"], git(self.origins / "atlas", "rev-parse", "HEAD"))
        alpha, beta = document["members"]
        self.assertEqual((alpha["name"], alpha["branch"], alpha["revision"]), ("alpha", "trunk", tip))
        self.assertEqual(
            alpha["crates"],
            [{
                "name": "alpha", "version": "0.1.0", "manifest": "Cargo.toml",
                "status": "published-drifted", "published": True, "latest_published": "0.1.0",
                "drift": {"changed": ["src/lib.rs"], "added": [], "removed": []},
                "dependents": [{"member": "beta", "crate": "beta", "requirement": "^0.1",
                                "kind": "normal", "rename": "a"}],
            }])
        self.assertEqual(
            beta["crates"],
            [{
                "name": "beta", "version": "0.2.0", "manifest": "crates/beta/Cargo.toml",
                "status": "never-published", "published": False, "latest_published": None,
                "drift": None, "dependents": [],
            }])
        self.assertEqual(
            document["summary"],
            {"crates": 2, "never_published": 1, "foreign_name": 0, "unpublished_version": 0,
             "published_current": 0, "published_drifted": 1, "drifted": 1, "findings": 1,
             "by_member": {
                 "alpha": {"crates": 1, "never_published": 0, "foreign_name": 0,
                           "unpublished_version": 0, "published_current": 0,
                           "published_drifted": 1, "drifted": 1, "findings": 1},
                 "beta": {"crates": 1, "never_published": 1, "foreign_name": 0,
                          "unpublished_version": 0, "published_current": 0,
                          "published_drifted": 0, "drifted": 0, "findings": 0}}})

    def test_a_clean_stack_exits_zero_and_renders_the_markdown_table(self) -> None:
        origins = self.build_stack({"alpha": self.ALPHA, "beta": self.BETA})
        self.commit_files(origins["alpha"], {"src/lib.rs": "pub fn one() -> u32 { 11 }\n"})

        status, out, _ = self.run_tool(self.alpha_registry("pub fn one() -> u32 { 11 }\n"),
                                       "--format", "md")

        self.assertEqual(status, 0)
        self.assertIn("2 publishable crates, 0 drifted, 0 on a name another account owns, "
                      "1 never published", out)
        self.assertIn("| alpha | 1 | 0 | 0 | 0 | 0 | 1 |", out)
        self.assertIn("| alpha | alpha | 0.1.0 | published-current | 0.1.0 | 0 | 0 | 0 | "
                      "beta: beta as a `^0.1` |", out)

    def test_an_index_outage_fails_the_tool_with_status_two(self) -> None:
        self.build_stack({"alpha": self.ALPHA})
        registry = Registry({}, status={"https://index.crates.io/al/ph/alpha": 500})
        status, out, err = self.run_tool(registry)
        self.assertEqual((status, out), (2, ""))
        self.assertIn("HTTP 500 for alpha", err)

    def test_a_foreign_name_exits_one_and_downloads_no_crate(self) -> None:
        self.build_stack({"alpha": self.ALPHA})
        registry = Registry({"alpha": ["0.1.0"]}, owners={"alpha": ["someone-else"]})

        status, out, err = self.run_tool(registry)

        self.assertEqual((status, err), (1, ""))
        document = json.loads(out)
        self.assertEqual(
            document["members"][0]["crates"],
            [{
                "name": "alpha", "version": "0.1.0", "manifest": "Cargo.toml",
                "status": "foreign-name", "published": False, "latest_published": None,
                "drift": None, "dependents": [],
            }])
        counts = {"crates": 1, "never_published": 0, "foreign_name": 1, "unpublished_version": 0,
                  "published_current": 0, "published_drifted": 0, "drifted": 0, "findings": 1}
        self.assertEqual(document["summary"], {**counts, "by_member": {"alpha": counts}})
        self.assertEqual(registry.asked, ["https://index.crates.io/al/ph/alpha",
                                          OWNERS_URL.format(name="alpha")])

    def test_the_owner_option_selects_the_expected_account(self) -> None:
        self.build_stack({"alpha": self.ALPHA})
        registry = Registry({"alpha": ["0.1.0"]}, owners={"alpha": ["someone-else"]})
        registry.crates[("alpha", "0.1.0")] = make_crate("alpha", "0.1.0", {
            "src/lib.rs": self.ALPHA["src/lib.rs"].encode(),
            "Cargo.toml.orig": self.ALPHA["Cargo.toml"].encode()})
        status, out, _ = self.run_tool(registry, "--owner", "someone-else")
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out)["members"][0]["crates"][0]["status"], "published-current")

    def test_an_owners_outage_fails_the_tool_with_status_two(self) -> None:
        self.build_stack({"alpha": self.ALPHA})
        registry = Registry({"alpha": ["0.1.0"]},
                            status={OWNERS_URL.format(name="alpha"): 500})
        status, out, err = self.run_tool(registry)
        self.assertEqual((status, out), (2, ""))
        self.assertIn("owners API returned HTTP 500 for alpha", err)

    def test_an_unregistered_member_name_fails_the_tool(self) -> None:
        self.build_stack({"alpha": self.ALPHA})
        status, _, err = self.run_tool(Registry({}), "--member", "nope")
        self.assertEqual(status, 2)
        self.assertIn("not registered members: nope", err)


if __name__ == "__main__":
    unittest.main()
