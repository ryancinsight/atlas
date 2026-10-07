"""Tests for the crates-pending action: selection, verification, publish, tagging."""

from __future__ import annotations

import importlib.util
import json
import contextlib
import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "crates_pending", ROOT / ".github" / "actions" / "crates-pending" / "crates_pending.py")
cp = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = cp
SPEC.loader.exec_module(cp)

OWNER = "ryancinsight"


class Registry:
    """Answers index and owners URLs from fixtures; records every URL asked."""

    def __init__(self, index: dict[str, list[str]], owners: dict[str, list[str]] | None = None,
                 status: dict[str, int] | None = None) -> None:
        self.index, self.owners, self.status, self.asked = index, owners or {}, status or {}, []

    def __call__(self, url: str) -> tuple[int, str]:
        self.asked.append(url)
        if url in self.status:
            return self.status[url], ""
        if url.startswith("https://index.crates.io/"):
            path = url.removeprefix("https://index.crates.io/")
            for name, versions in self.index.items():
                if cp.index_path(name) == path:
                    return 200, "".join(json.dumps({"name": name, "vers": v}) + "\n" for v in versions)
            return 404, ""
        name = url.removeprefix("https://crates.io/api/v1/crates/").removesuffix("/owners")
        return 200, json.dumps({"users": [{"login": l} for l in self.owners.get(name, [OWNER])]})


CARGO_CALL_LIMIT = 20


class Cargo:
    """Records argv; answers by the first matching argv prefix."""

    def __init__(self, packages: list[dict], answers: dict[tuple[str, ...], tuple[int, str]] | None = None):
        self.packages, self.answers, self.calls = packages, answers or {}, []

    def __call__(self, argv: list[str]) -> subprocess.CompletedProcess:
        self.calls.append(argv)
        # A plan resolves at most once per pending package plus one compile; a caller that
        # keeps asking is looping, and must fail the test rather than hang it.
        if len(self.calls) > CARGO_CALL_LIMIT:
            raise AssertionError(f"cargo called {len(self.calls)} times; the caller does not terminate")
        if argv[:2] == ["cargo", "metadata"]:
            return subprocess.CompletedProcess(argv, 0, json.dumps({"packages": self.packages}), "")
        for prefix, (code, stderr) in self.answers.items():
            if tuple(argv[:len(prefix)]) == prefix:
                return subprocess.CompletedProcess(argv, code, "", stderr)
        return subprocess.CompletedProcess(argv, 0, "", "")


def pkg(name: str, version: str, publish=None, deps: tuple[str, ...] = ()) -> dict:
    return {"name": name, "version": version, "publish": publish,
            "dependencies": [{"name": dep} for dep in deps]}


def no_sleep(_: float) -> None:
    return None


class IndexTests(unittest.TestCase):
    def test_index_path_follows_the_sparse_layout_and_lowercases(self) -> None:
        self.assertEqual(
            [cp.index_path(n) for n in ("a", "io", "Syn", "Serde", "hermes-simd")],
            ["1/a", "2/io", "3/s/syn", "se/rd/serde", "he/rm/hermes-simd"])

    def test_versions_read_every_line_and_not_found_is_none(self) -> None:
        registry = Registry({"alpha": ["0.1.0", "0.2.0", "0.1.1"]})
        self.assertEqual(cp.published_versions("alpha", registry), ["0.1.0", "0.2.0", "0.1.1"])
        self.assertIsNone(cp.published_versions("beta", registry))

    def test_any_other_status_is_an_error_not_an_answer(self) -> None:
        for code in (403, 429, 503):
            registry = Registry({}, status={"https://index.crates.io/al/ph/alpha": code})
            with self.assertRaises(cp.RegistryError):
                cp.published_versions("alpha", registry)


class HttpTests(unittest.TestCase):
    def test_status_codes_pass_through_and_network_failure_raises(self) -> None:
        def raising(error):
            return mock.patch.object(cp.urllib.request, "urlopen", side_effect=error)
        for code in (404, 503):
            with raising(urllib.error.HTTPError("u", code, "m", {}, io.BytesIO())):
                self.assertEqual(cp.http_get("https://index.crates.io/1/a"), (code, ""))
        with raising(urllib.error.URLError("down")), self.assertRaises(cp.RegistryError):
            cp.http_get("https://index.crates.io/1/a")
        with raising(TimeoutError()), self.assertRaises(cp.RegistryError):
            cp.http_get("https://index.crates.io/1/a")

    def test_requests_carry_the_user_agent_and_a_deadline(self) -> None:
        # crates.io's crawler policy requires an identifying User-Agent; the deadline bounds a hung socket.
        response = mock.MagicMock(status=200)
        response.read.return_value = b"{}"
        response.__enter__.return_value = response
        with mock.patch.object(cp.urllib.request, "urlopen", return_value=response) as urlopen:
            self.assertEqual(cp.http_get("https://crates.io/api/v1/crates/a/owners"), (200, "{}"))
        (request,), options = urlopen.call_args
        self.assertEqual(request.full_url, "https://crates.io/api/v1/crates/a/owners")
        self.assertEqual(request.get_header("User-agent"), cp.USER_AGENT)
        self.assertEqual(cp.USER_AGENT, "atlas-crates-pending (github.com/ryancinsight/atlas)")
        self.assertEqual(options, {"timeout": 30})

    def test_a_503_index_answer_is_an_error_end_to_end(self) -> None:
        error = urllib.error.HTTPError("u", 503, "m", {}, io.BytesIO())
        with mock.patch.object(cp.urllib.request, "urlopen", side_effect=error), \
                self.assertRaises(cp.RegistryError):
            cp.published_versions("alpha")


class SelectTests(unittest.TestCase):
    def test_selects_versions_absent_from_the_index_even_when_older_lines_follow(self) -> None:
        registry = Registry({"alpha": ["0.6.0", "0.7.0", "0.6.1"], "alpha-core": ["0.6.0"]})
        plan = cp.select({"packages": [pkg("alpha", "0.7.0"), pkg("alpha-core", "0.7.0")]},
                         OWNER, registry, no_sleep)
        self.assertEqual(plan.pending, ["alpha-core"])

    def test_registry_scoping_and_first_publication(self) -> None:
        registry = Registry({"kept": ["1.0.0"], "listed": ["1.0.0"]})
        plan = cp.select({"packages": [
            pkg("kept", "1.1.0"), pkg("listed", "1.1.0", ["crates-io"]),
            pkg("internal", "0.1.0", []), pkg("private", "0.1.0", ["my-registry"]),
            pkg("fresh", "0.1.0")]}, OWNER, registry, no_sleep)
        self.assertEqual(plan.pending, ["kept", "listed"])
        self.assertEqual(len(plan.notices), 1)
        self.assertIn("fresh has never been published", plan.notices[0])
        self.assertFalse(any("internal" in u or "private" in u for u in registry.asked))

    def test_a_never_published_name_does_not_end_the_selection(self) -> None:
        registry = Registry({"kept": ["1.0.0"]})
        plan = cp.select({"packages": [pkg("fresh", "0.1.0"), pkg("kept", "1.1.0")]}, OWNER, registry, no_sleep)
        self.assertEqual(plan.pending, ["kept"])

    def test_selection_follows_the_expected_owner(self) -> None:
        registry = Registry({"a": ["0.1.0"]}, owners={"a": ["someone"]})
        self.assertEqual(cp.select({"packages": [pkg("a", "0.2.0")]}, "someone", registry, no_sleep).pending, ["a"])
        self.assertEqual(cp.select({"packages": [pkg("a", "0.2.0")]}, OWNER, registry, no_sleep).pending, [])

    def test_a_name_someone_else_owns_is_never_published(self) -> None:
        registry = Registry({"horae": ["0.1.1", "0.2.1"]}, owners={"horae": ["zhaohang1205"]})
        plan = cp.select({"packages": [pkg("horae", "0.1.0")]}, OWNER, registry, no_sleep)
        self.assertEqual(plan.pending, [])
        self.assertIn("owned by zhaohang1205, not ryancinsight", plan.warnings[0])

    def test_owners_outage_fails_instead_of_reading_as_nobody(self) -> None:
        # A rate limit, and a 404 for a name the index holds, are both failures to answer.
        for status in (429, 404):
            with self.subTest(status=status):
                registry = Registry({"bumped": ["1.0.0"]},
                                    status={"https://crates.io/api/v1/crates/bumped/owners": status})
                with self.assertRaises(cp.RegistryError):
                    cp.select({"packages": [pkg("bumped", "1.1.0")]}, OWNER, registry, no_sleep)

    def test_owners_requests_follow_the_crawler_interval(self) -> None:
        slept = []
        cp.select({"packages": [pkg("a", "0.2.0"), pkg("b", "0.2.0")]}, OWNER,
                  Registry({"a": ["0.1.0"], "b": ["0.1.0"]}), slept.append)
        self.assertEqual(slept, [cp.API_INTERVAL_SECONDS, cp.API_INTERVAL_SECONDS])

    def test_owners_are_asked_only_for_pending_names(self) -> None:
        registry = Registry({"current": ["1.0.0"], "bumped": ["1.0.0"]})
        cp.select({"packages": [pkg("current", "1.0.0"), pkg("bumped", "1.1.0")]}, OWNER, registry, no_sleep)
        self.assertEqual([u for u in registry.asked if "/owners" in u],
                         ["https://crates.io/api/v1/crates/bumped/owners"])


MISSING = "error: failed to select a version for the requirement `{} = \"^0.7.0\"`"
RESOLVE = ("cargo", "package", "--locked", "--no-verify")
# cargo 1.97.0, for a dependency feature no published version has.
UNSATISFIED = """error: failed to select a version for `{0}`.
    ... required by package `a v0.2.0 (D:\\w\\a)`
versions that meet the requirements `^1` are: 1.0.15, 1.0.14

package `a` depends on `{0}` with feature `unpublished` but `{0}` does not have that feature.


failed to select a version for `{0}` which could resolve this conflict"""


def resolve(*names: str) -> tuple[str, ...]:
    return (*RESOLVE, *cp.package_args(list(names)))


class VerifyTests(unittest.TestCase):
    def test_ready_checks_resolution_then_compiles(self) -> None:
        cargo = Cargo([])
        packages = [pkg("a", "0.2.0"), pkg("b", "0.2.0")]
        self.assertEqual(cp.verify(["a", "b"], packages, OWNER, Registry({}), cargo, no_sleep), ["a", "b"])
        self.assertEqual(cargo.calls, [
            ["cargo", "package", "--locked", "--no-verify", "--package", "a", "--package", "b"],
            ["cargo", "package", "--locked", "--package", "a", "--package", "b"]])

    def test_missing_version_of_a_crate_the_owner_publishes_waits_without_compiling(self) -> None:
        cargo = Cargo([], {RESOLVE: (101, MISSING.format("hermes-simd"))})
        registry = Registry({})
        packages = [pkg("leto-ops", "0.2.0", deps=("hermes-simd",))]
        self.assertEqual(cp.verify(["leto-ops"], packages, OWNER, registry, cargo, no_sleep), [])
        self.assertEqual(len(cargo.calls), 1)
        self.assertEqual(registry.asked, ["https://crates.io/api/v1/crates/hermes-simd/owners"])

    def test_only_the_names_that_need_the_missing_version_wait(self) -> None:
        # c depends on the missing hermes-simd, b on c, and a on neither: a publishes now.
        # b reaches c through a dev-dependency, which cargo package resolves like any other.
        dev = pkg("b", "0.2.0")
        dev["dependencies"] = [{"name": "c", "kind": "dev", "req": "^0.2.0"}]
        packages = [pkg("a", "0.2.0", deps=("serde",)), dev, pkg("c", "0.2.0", deps=("hermes-simd",))]
        cargo = Cargo([], {resolve("a", "b", "c"): (101, MISSING.format("hermes-simd"))})
        slept: list[float] = []
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            ready = cp.verify(["a", "b", "c"], packages, OWNER, Registry({}), cargo, slept.append)
        self.assertEqual(ready, ["a"])
        self.assertEqual(cargo.calls, [list(resolve("a", "b", "c")), list(resolve("a")),
                                       ["cargo", "package", "--locked", "--package", "a"]])
        self.assertEqual(slept, [1.0])
        self.assertIn("::notice::waiting for the required hermes-simd version to reach the index: b c",
                      stdout.getvalue())

    def test_every_versioned_dependency_form_holds_back_its_dependent(self) -> None:
        # The dependency entries cargo metadata 1.97 emits for each form the stack uses: a build
        # dependency (mnemosyne-local), an optional one (apollo), a target-specific one
        # (metis-app), and a dev-dependency with both a path and a version (ritk-cli). cargo
        # package keeps each, so each is a need.
        base = {"name": "dep", "kind": None, "req": "^0.2.0", "optional": False, "target": None}
        forms = {"build": {"kind": "build"}, "optional": {"optional": True},
                 "target-specific": {"target": "cfg(windows)"},
                 "dev with path and version": {"kind": "dev", "path": "../dep"}}
        for form, fields in forms.items():
            with self.subTest(form=form):
                needing = pkg("a", "0.2.0")
                needing["dependencies"] = [{**base, **fields}]
                packages = [needing, pkg("c", "0.2.0")]
                cargo = Cargo([], {resolve("a", "c"): (101, MISSING.format("dep"))})
                with contextlib.redirect_stdout(io.StringIO()):
                    ready = cp.verify(["a", "c"], packages, OWNER, Registry({}), cargo, no_sleep)
                self.assertEqual(ready, ["c"])

    def test_a_dev_dependency_without_a_version_holds_nothing_back(self) -> None:
        # cargo package strips a path-only dev-dependency (cargo metadata reports its requirement
        # as `*`), so b packages without c: only c waits. ritk-diffusion-scheme has one.
        dev = pkg("b", "0.2.0")
        dev["dependencies"] = [{"name": "c", "kind": "dev", "req": "*", "path": "../c"}]
        packages = [dev, pkg("c", "0.2.0", deps=("hermes-simd",))]
        cargo = Cargo([], {resolve("b", "c"): (101, MISSING.format("hermes-simd"))})
        with contextlib.redirect_stdout(io.StringIO()):
            ready = cp.verify(["b", "c"], packages, OWNER, Registry({}), cargo, no_sleep)
        self.assertEqual(ready, ["b"])
        self.assertEqual(cp.dependents(["b", "c"], packages, "hermes-simd"), ["c"])

    def test_dependency_kinds_are_read_from_decoded_cargo_metadata(self) -> None:
        # cargo metadata reaches the plan as JSON: compare its strings by value, never identity.
        dev = pkg("b", "0.2.0")
        dev["dependencies"] = [{"name": "c", "kind": "dev", "req": "*", "path": "../c"}]
        decoded = cp.metadata(Cargo([dev, pkg("c", "0.2.0", deps=("hermes-simd",))]))["packages"]
        self.assertEqual(cp.dependents(["b", "c"], decoded, "hermes-simd"), ["c"])

    def test_a_renamed_dependency_is_followed_by_its_package_name(self) -> None:
        # `moirai = { package = "moirai-runtime", ... }`: cargo metadata carries the package name
        # in `name` and the local one in `rename`, and cargo's error names the package.
        renamed = pkg("a", "0.2.0")
        renamed["dependencies"] = [{"name": "moirai-runtime", "rename": "moirai", "req": "^0.6.0"}]
        packages = [renamed, pkg("c", "0.2.0")]
        cargo = Cargo([], {resolve("a", "c"): (101, MISSING.format("moirai-runtime"))})
        with contextlib.redirect_stdout(io.StringIO()):
            ready = cp.verify(["a", "c"], packages, OWNER, Registry({}), cargo, no_sleep)
        self.assertEqual(ready, ["c"])

    def test_the_wait_check_sleeps_before_its_owners_request(self) -> None:
        packages = [pkg("a", "0.2.0", deps=("dep",)), pkg("c", "0.2.0")]
        registry = Registry({})
        asked_before_sleep: list[int] = []
        cargo = Cargo([], {resolve("a", "c"): (101, MISSING.format("dep"))})
        with contextlib.redirect_stdout(io.StringIO()):
            cp.verify(["a", "c"], packages, OWNER, registry, cargo,
                      lambda _: asked_before_sleep.append(len(registry.asked)))
        self.assertEqual(asked_before_sleep, [0])
        self.assertEqual(registry.asked, ["https://crates.io/api/v1/crates/dep/owners"])

    def test_each_missing_version_holds_back_only_its_dependents(self) -> None:
        packages = [pkg("a", "0.2.0", deps=("x",)), pkg("b", "0.2.0", deps=("y",)), pkg("c", "0.2.0")]
        cargo = Cargo([], {resolve("a", "b", "c"): (101, MISSING.format("x")),
                           resolve("b", "c"): (101, MISSING.format("y"))})
        self.assertEqual(cp.verify(["a", "b", "c"], packages, OWNER, Registry({}), cargo, no_sleep), ["c"])

    def test_a_missing_version_no_pending_name_depends_on_fails(self) -> None:
        cargo = Cargo([], {RESOLVE: (101, MISSING.format("hermes-simd"))})
        with self.assertRaisesRegex(SystemExit, "hermes-simd, which no pending package depends on"):
            cp.verify(["a"], [pkg("a", "0.2.0", deps=("serde",))], OWNER, Registry({}), cargo, no_sleep)

    def test_a_foreign_crate_missing_version_holds_back_only_its_dependents(self) -> None:
        foreign = Registry({}, owners={"itoa": ["dtolnay"]})
        packages = [pkg("a", "0.2.0", deps=("itoa",)), pkg("c", "0.2.0")]
        cargo = Cargo([], {resolve("a", "c"): (101, MISSING.format("itoa"))})
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            ready = cp.verify(["a", "c"], packages, OWNER, foreign, cargo, no_sleep)
        self.assertEqual(ready, ["c"])
        self.assertIn("::warning::itoa is owned by another crates.io account and the index lacks "
                      "the required version; held: a", stdout.getvalue())

    def test_a_workspace_member_missing_version_holds_back_only_its_dependents(self) -> None:
        registry = Registry({})
        packages = [pkg("a", "0.2.0", deps=("a-core",)), pkg("a-core", "0.3.0", []), pkg("c", "0.2.0")]
        cargo = Cargo([], {resolve("a", "c"): (101, MISSING.format("a-core"))})
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            ready = cp.verify(["a", "c"], packages, OWNER, registry, cargo, no_sleep)
        self.assertEqual(ready, ["c"])
        self.assertIn("::warning::no version of workspace member a-core on crates.io or in this run's "
                      "pending set satisfies the requirement on it; held: a", stdout.getvalue())
        self.assertIn("held: a", stdout.getvalue())
        # A member's ownership is this workspace's; nothing is asked of the owners API.
        self.assertEqual(registry.asked, [])

    def test_a_never_published_dependency_holds_back_only_its_dependents(self) -> None:
        # cargo 1.97 for a name with no index entry: this is not the select-a-version message.
        absent = "error: no matching package named `ritk-parcellation` found\nlocation searched: crates.io index"
        for packages in ([pkg("a", "0.2.0", deps=("ritk-parcellation",)), pkg("c", "0.2.0")],
                         [pkg("a", "0.2.0", deps=("ritk-parcellation",)), pkg("c", "0.2.0"),
                          pkg("ritk-parcellation", "0.1.0")]):
            with self.subTest(member="ritk-parcellation" in {p["name"] for p in packages}):
                registry = Registry({})
                cargo = Cargo([], {resolve("a", "c"): (101, absent)})
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    ready = cp.verify(["a", "c"], packages, OWNER, registry, cargo, no_sleep)
                self.assertEqual(ready, ["c"])
                self.assertIn("::warning::ritk-parcellation has never been published on crates.io; its "
                              "first publish needs an API token; held: a", stdout.getvalue())
                self.assertEqual(registry.asked, [])

    def test_the_expected_owner_decides_wait_or_warning(self) -> None:
        packages = [pkg("a", "0.2.0", deps=("dep",)), pkg("c", "0.2.0")]
        for owner, kind in (("someone", "::notice::waiting"), (OWNER, "::warning::dep is owned")):
            with self.subTest(owner=owner):
                cargo = Cargo([], {resolve("a", "c"): (101, MISSING.format("dep"))})
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    ready = cp.verify(["a", "c"], packages, owner, Registry({}, owners={"dep": ["someone"]}),
                                      cargo, no_sleep)
                self.assertEqual(ready, ["c"])
                self.assertIn(kind, stdout.getvalue())

    def test_an_unsatisfiable_requirement_holds_back_only_its_dependents(self) -> None:
        packages = [pkg("a", "0.2.0", deps=("itoa",)), pkg("c", "0.2.0")]
        cargo = Cargo([], {resolve("a", "c"): (101, UNSATISFIED.format("itoa"))})
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            ready = cp.verify(["a", "c"], packages, OWNER, Registry({}, owners={"itoa": ["dtolnay"]}),
                              cargo, no_sleep)
        self.assertEqual(ready, ["c"])
        self.assertIn("::warning::itoa is owned by another crates.io account and the index lacks "
                      "the required version; held: a", stdout.getvalue())

    def test_every_crate_name_character_class_is_read_from_each_cargo_form(self) -> None:
        # crates.io names take ASCII letters of either case, digits, `-` and `_`: serde_json,
        # sha2, proc-macro2 and Inflector are all on the index.
        forms = {"unmet requirement": MISSING.format,
                 "unsatisfiable requirement": UNSATISFIED.format,
                 "never published": "error: no matching package named `{}` found".format}
        for name in ("serde_json", "sha2", "proc-macro2", "Inflector"):
            packages = [pkg("a", "0.2.0", deps=(name,)), pkg("c", "0.2.0")]
            for form, stderr in forms.items():
                with self.subTest(name=name, form=form):
                    cargo = Cargo([], {resolve("a", "c"): (101, stderr(name))})
                    stdout = io.StringIO()
                    with contextlib.redirect_stdout(stdout):
                        ready = cp.verify(["a", "c"], packages, OWNER,
                                          Registry({}, owners={name: ["another-account"]}), cargo, no_sleep)
                    self.assertEqual(ready, ["c"])
                    self.assertIn(f"{name} ", stdout.getvalue())

    def test_a_dependency_only_a_held_package_needs_ends_the_loop(self) -> None:
        # After a is held for dep, cargo names dep again while resolving c alone: nothing still
        # ready depends on it, so the plan fails instead of re-resolving the same set forever.
        packages = [pkg("a", "0.2.0", deps=("dep",)), pkg("c", "0.2.0")]
        cargo = Cargo([], {resolve("a", "c"): (101, MISSING.format("dep")),
                           resolve("c"): (101, MISSING.format("dep"))})
        with contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaisesRegex(SystemExit, "cargo names dep, which no pending package depends on"):
            cp.verify(["a", "c"], packages, OWNER, Registry({}), cargo, no_sleep)
        self.assertEqual(len(cargo.calls), 2)

    def test_the_hold_back_follows_a_chain_to_its_end(self) -> None:
        # x needs dep, b needs x, a needs b: in this order each pass adds one name.
        packages = [pkg("a", "0.2.0", deps=("b",)), pkg("b", "0.2.0", deps=("x",)),
                    pkg("x", "0.2.0", deps=("dep",)), pkg("c", "0.2.0")]
        self.assertEqual(cp.dependents(["a", "b", "x", "c"], packages, "dep"), ["a", "b", "x"])

    def test_an_unrelated_error_quoting_a_requirement_is_not_a_wait(self) -> None:
        cargo = Cargo([], {RESOLVE: (101, 'error: invalid table key `serde = "1"` in manifest')})
        with self.assertRaisesRegex(SystemExit, "other than a missing dependency version"):
            cp.verify(["a"], [pkg("a", "0.2.0", deps=("serde",))], OWNER, Registry({}), cargo, no_sleep)

    def test_owners_outage_during_a_wait_fails(self) -> None:
        registry = Registry({}, status={"https://crates.io/api/v1/crates/hermes-simd/owners": 503})
        with self.assertRaises(cp.RegistryError):
            cp.verify(["a"], [pkg("a", "0.2.0", deps=("hermes-simd",))], OWNER, registry,
                      Cargo([], {RESOLVE: (101, MISSING.format("hermes-simd"))}), no_sleep)

    def test_other_resolution_and_compile_failures_fail(self) -> None:
        packages = [pkg("a", "0.2.0")]
        with self.assertRaises(SystemExit):
            cp.verify(["a"], packages, OWNER, Registry({}),
                      Cargo([], {RESOLVE: (101, "error: missing license")}), no_sleep)
        with self.assertRaises(SystemExit):
            cp.verify(["a"], packages, OWNER, Registry({}),
                      Cargo([], {("cargo", "package", "--locked", "--package"): (101, "error[E0432]")}), no_sleep)


class PolicyBoundTests(unittest.TestCase):
    def test_the_crawler_interval_and_the_index_budget_meet_their_published_bounds(self) -> None:
        # crates.io crawler policy: at most one API request per second.
        self.assertGreaterEqual(cp.API_INTERVAL_SECONDS, 1.0)
        # Exactly five minutes of polling after cargo's own 60 s wait before a version counts
        # as lost: shorter loses slow releases, longer outlives the job's timeout silently.
        self.assertEqual(cp.INDEX_POLL_ATTEMPTS * cp.INDEX_POLL_INTERVAL_SECONDS, 300.0)
        self.assertGreater(cp.INDEX_POLL_INTERVAL_SECONDS, 0.0)


class PlanCommandTests(unittest.TestCase):
    def test_a_co_owned_crate_is_pending_whichever_login_comes_first(self) -> None:
        for logins in (["a-co-owner", OWNER], [OWNER, "a-co-owner"]):
            with self.subTest(logins=logins):
                registry = Registry({"a": ["0.1.0"]}, owners={"a": logins})
                out = cp.command_plan(OWNER, registry, Cargo([pkg("a", "0.2.0")]), no_sleep)
                self.assertEqual(out, {"packages": "a", "count": "1"})

    def test_the_owner_input_decides_selection_and_waiting(self) -> None:
        # Every name is owned by "someone": a plan for any other owner selects nothing, and a
        # plan for "someone" publishes c and waits for dep, which "someone" publishes elsewhere.
        logins = {name: ["someone"] for name in ("a", "c", "dep")}
        registry = Registry({"a": ["0.1.0"], "c": ["0.1.0"]}, owners=logins)
        cargo = Cargo([pkg("a", "0.2.0", deps=("dep",)), pkg("c", "0.2.0")],
                      {resolve("a", "c"): (101, MISSING.format("dep"))})
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            out = cp.command_plan("someone", registry, cargo, no_sleep)
        self.assertEqual(out, {"packages": "c", "count": "1"})
        self.assertIn("::notice::waiting for the required dep version to reach the index: a",
                      stdout.getvalue())
        self.assertEqual(cp.command_plan(OWNER, registry, Cargo([pkg("a", "0.2.0"), pkg("c", "0.2.0")]),
                                         no_sleep), {"count": "0"})

    def test_outputs_the_pending_set(self) -> None:
        cargo = Cargo([pkg("a", "0.2.0"), pkg("b", "0.2.0")])
        out = cp.command_plan(OWNER, Registry({"a": ["0.1.0"], "b": ["0.1.0"]}), cargo, no_sleep)
        self.assertEqual(out, {"packages": "a,b", "count": "2"})

    def test_an_unpublishable_member_holds_back_only_its_dependents(self) -> None:
        cargo = Cargo([pkg("a", "0.2.0", deps=("a-internal",)), pkg("a-internal", "0.3.0", []), pkg("c", "0.2.0")],
                      {resolve("a", "c"): (101, MISSING.format("a-internal"))})
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            out = cp.command_plan(OWNER, Registry({"a": ["0.1.0"], "a-internal": ["0.1.0"], "c": ["0.1.0"]}),
                                  cargo, no_sleep)
        self.assertEqual(out, {"packages": "c", "count": "1"})
        self.assertIn("::notice::pending packages (a) wait on a dependency", stdout.getvalue())

    def test_nothing_pending_or_waiting_is_count_zero(self) -> None:
        self.assertEqual(cp.command_plan(OWNER, Registry({"a": ["0.1.0"]}), Cargo([pkg("a", "0.1.0")]), no_sleep),
                         {"count": "0"})
        waiting = Cargo([pkg("a", "0.2.0", deps=("hermes-simd",))], {RESOLVE: (101, MISSING.format("hermes-simd"))})
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(cp.command_plan(OWNER, Registry({"a": ["0.1.0"]}), waiting, no_sleep), {"count": "0"})
        self.assertIn("::notice::pending packages (a) wait on a dependency version not yet on crates.io",
                      stdout.getvalue())

    def test_a_partly_waiting_set_publishes_the_rest_and_names_the_held(self) -> None:
        cargo = Cargo([pkg("a", "0.2.0"), pkg("b", "0.2.0", deps=("hermes-simd",))],
                      {resolve("a", "b"): (101, MISSING.format("hermes-simd"))})
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            out = cp.command_plan(OWNER, Registry({"a": ["0.1.0"], "b": ["0.1.0"]}), cargo, no_sleep)
        self.assertEqual(out, {"packages": "a", "count": "1"})
        self.assertIn("::notice::pending packages (b) wait on a dependency version not yet on crates.io",
                      stdout.getvalue())

    def test_foreign_names_and_first_publications_are_annotated(self) -> None:
        registry = Registry({"horae": ["0.2.1"]}, owners={"horae": ["zhaohang1205"]})
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            out = cp.command_plan(OWNER, registry, Cargo([pkg("horae", "0.3.0"), pkg("fresh", "0.1.0")]), no_sleep)
        self.assertEqual(out, {"count": "0"})
        lines = stdout.getvalue().splitlines()
        self.assertIn("::warning::horae on crates.io is owned by zhaohang1205, not ryancinsight; "
                      "it needs a registry name of its own (ADR 0037 section 3)", lines)
        self.assertIn("::notice::fresh has never been published; its first publish needs an API token "
                      "before trusted publishing applies", lines)


class PublishTests(unittest.TestCase):
    def test_a_name_the_index_has_never_seen_is_still_pending(self) -> None:
        registry = Registry({"b": ["0.2.0"]})
        self.assertEqual(cp.still_pending(["a", "b"], {"a": "0.2.0", "b": "0.2.0"}, registry), ["a"])

    def test_publishes_only_what_is_still_pending_without_reverifying(self) -> None:
        cargo = Cargo([pkg("a", "0.2.0"), pkg("b", "0.2.0"), pkg("c", "0.2.0")])
        cp.command_publish(["a", "b", "c"], Registry({"a": ["0.1.0"], "b": ["0.1.0", "0.2.0"], "c": ["0.1.0"]}), cargo)
        self.assertEqual(cargo.calls[-1],
                         ["cargo", "publish", "--locked", "--no-verify", "--package", "a", "--package", "c"])

    def test_an_already_published_set_publishes_nothing(self) -> None:
        cargo = Cargo([pkg("a", "0.2.0")])
        cp.command_publish(["a"], Registry({"a": ["0.2.0"]}), cargo)
        self.assertFalse(any(c[:2] == ["cargo", "publish"] for c in cargo.calls))

    def test_publish_failure_fails(self) -> None:
        with self.assertRaises(SystemExit):
            cp.command_publish(["a"], Registry({"a": ["0.1.0"]}),
                               Cargo([pkg("a", "0.2.0")], {("cargo", "publish"): (101, "error")}))


class Index:
    """An index that gains a version after a number of reads (None: never)."""

    def __init__(self, before: list[str], after: list[str], reads_until_visible: int | None) -> None:
        self.before, self.after, self.left = before, after, reads_until_visible

    def __call__(self, url: str) -> tuple[int, str]:
        visible = self.left is not None and self.left <= 0
        if self.left is not None:
            self.left -= 1
        versions = self.after if visible else self.before
        return 200, "".join(json.dumps({"vers": v}) + "\n" for v in versions)


class TagTests(unittest.TestCase):
    def test_an_existing_release_does_not_end_the_tagging(self) -> None:
        cargo = Cargo([pkg("a", "0.2.0"), pkg("b", "0.2.0")],
                      {("gh", "release", "view", "crate-a-v0.2.0"): (0, ""),
                       ("gh", "release", "view", "crate-b-v0.2.0"): (1, "release not found")})
        cp.command_tag(["a", "b"], "crate-", "abc", "o/r", False,
                       Registry({"a": ["0.2.0"], "b": ["0.2.0"]}), cargo, no_sleep)
        self.assertEqual([c[3] for c in cargo.calls if c[:3] == ["gh", "release", "create"]], ["crate-b-v0.2.0"])

    def test_tags_indexed_versions_and_skips_existing_releases(self) -> None:
        cargo = Cargo([pkg("a", "0.2.0"), pkg("b", "0.2.0"), pkg("c", "0.2.0")],
                      {("gh", "release", "view", "crate-a-v0.2.0"): (1, "release not found"),
                       ("gh", "release", "view", "crate-b-v0.2.0"): (0, "")})
        cp.command_tag(["a", "b", "c"], "crate-", "abc123", "o/r", False,
                       Registry({"a": ["0.2.0"], "b": ["0.2.0"], "c": ["0.1.0"]}), cargo, no_sleep)
        created = [c for c in cargo.calls if c[:3] == ["gh", "release", "create"]]
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0][3:8], ["crate-a-v0.2.0", "--repo", "o/r", "--target", "abc123"])
        self.assertIn("--latest=false", created[0])

    def test_after_a_successful_publish_waits_for_a_lagging_index(self) -> None:
        cargo = Cargo([pkg("a", "0.2.0")], {("gh", "release", "view"): (1, "release not found")})
        slept = []
        cp.command_tag(["a"], "crate-", "abc", "o/r", True, Index(["0.1.0"], ["0.1.0", "0.2.0"], 2),
                       cargo, slept.append)
        self.assertEqual(slept, [cp.INDEX_POLL_INTERVAL_SECONDS] * 2)
        self.assertEqual(len([c for c in cargo.calls if c[:3] == ["gh", "release", "create"]]), 1)

    def test_one_lagging_version_among_several_fails_and_is_not_tagged(self) -> None:
        cargo = Cargo([pkg("a", "0.2.0"), pkg("b", "0.2.0")], {("gh", "release", "view"): (1, "not found")})
        index = {"a": Index(["0.1.0"], ["0.2.0"], 1), "b": Index(["0.1.0"], [], None)}

        def fetch(url: str) -> tuple[int, str]:
            return index[url.rsplit("/", 1)[1]](url)

        with self.assertRaisesRegex(SystemExit, "missing from the index: b$"):
            cp.command_tag(["a", "b"], "crate-", "abc", "o/r", True, fetch, cargo, no_sleep)
        self.assertFalse(any(c[:3] == ["gh", "release", "create"] for c in cargo.calls))

    def test_a_published_version_that_never_appears_fails_the_run(self) -> None:
        slept = []
        with self.assertRaisesRegex(SystemExit, "missing from the index: a"):
            cp.command_tag(["a"], "crate-", "abc", "o/r", True, Index(["0.1.0"], [], None),
                           Cargo([pkg("a", "0.2.0")]), slept.append)
        self.assertEqual(len(slept), cp.INDEX_POLL_ATTEMPTS)

    def test_after_a_failed_publish_only_indexed_versions_are_tagged_without_waiting(self) -> None:
        cargo = Cargo([pkg("a", "0.2.0"), pkg("b", "0.2.0")], {("gh", "release", "view"): (1, "not found")})
        slept = []
        cp.command_tag(["a", "b"], "crate-", "abc", "o/r", False,
                       Registry({"a": ["0.2.0"], "b": ["0.1.0"]}), cargo, slept.append)
        self.assertEqual(slept, [])
        self.assertEqual([c[3] for c in cargo.calls if c[:3] == ["gh", "release", "create"]],
                         ["crate-a-v0.2.0"])

    def test_a_failed_release_creation_fails(self) -> None:
        cargo = Cargo([pkg("a", "0.2.0")], {("gh", "release", "view"): (1, "release not found"),
                                            ("gh", "release", "create"): (1, "HTTP 502")})
        with self.assertRaisesRegex(SystemExit, "crate-a-v0.2.0"):
            cp.command_tag(["a"], "crate-", "abc", "o/r", False, Registry({"a": ["0.2.0"]}), cargo, no_sleep)

    def test_an_index_outage_fails_the_plan_and_the_publish(self) -> None:
        # A 503 from the index is no answer: neither "nothing pending" nor "never published".
        for status in (403, 429, 503):
            with self.subTest(status=status):
                outage = Registry({"a": ["0.1.0"]}, status={"https://index.crates.io/1/a": status})
                cargo = Cargo([pkg("a", "0.2.0")])
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(cp.RegistryError):
                    cp.command_plan(OWNER, outage, cargo, no_sleep)
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(cp.RegistryError):
                    cp.command_publish(["a"], outage, cargo)
                self.assertFalse(any(c[:2] in (["cargo", "package"], ["cargo", "publish"]) for c in cargo.calls))

    def test_registry_outage_fails_instead_of_skipping(self) -> None:
        registry = Registry({}, status={"https://index.crates.io/1/a": 500})
        with self.assertRaises(cp.RegistryError):
            cp.command_tag(["a"], "crate-", "abc", "o/r", False, registry, Cargo([pkg("a", "0.2.0")]), no_sleep)


class EntryPointTests(unittest.TestCase):
    def test_plan_writes_its_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = os.path.join(tmp, "out")
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": output}), \
                    mock.patch.object(cp, "command_plan", return_value={"packages": "a,b", "count": "2"}) as plan:
                self.assertEqual(cp.main(["plan", "--owner", "someone"]), 0)
            plan.assert_called_once_with("someone")
            with open(output, encoding="utf-8") as out:
                self.assertEqual(out.read(), "packages=a,b\ncount=2\n")

    def test_publish_and_tag_arguments_reach_their_commands(self) -> None:
        with mock.patch.object(cp, "command_publish") as publish:
            cp.main(["publish", "a,b"])
        publish.assert_called_once_with(["a", "b"])
        for outcome, published in (("success", True), ("failure", False), ("", False)):
            with mock.patch.object(cp, "command_tag") as tag:
                cp.main(["tag", "a,b", "--prefix", "crate-", "--sha", "abc", "--repo", "o/r",
                         "--publish-outcome", outcome])
            tag.assert_called_once_with(["a", "b"], "crate-", "abc", "o/r", published)


class ProcessTests(unittest.TestCase):
    """Child processes: captured text output, and a signal (negative return code) is a failure."""

    def test_run_captures_text(self) -> None:
        result = cp.run([sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr)"])
        self.assertEqual((result.returncode, result.stdout.splitlines(), result.stderr.splitlines()),
                         (0, ["out"], ["err"]))

    def test_a_process_killed_by_a_signal_fails_each_step(self) -> None:
        killed = (-9, "")
        packages = [pkg("a", "0.2.0")]
        steps = {
            "metadata": (lambda: cp.command_publish(["a"], Registry({"a": ["0.1.0"]}),
                                                    KilledMetadata(packages)), "cargo metadata failed"),
            "resolve": (lambda: cp.verify(["a"], packages, OWNER, Registry({}),
                                          Cargo([], {RESOLVE: killed}), no_sleep), "other than a missing"),
            "verify": (lambda: cp.verify(["a"], packages, OWNER, Registry({}),
                                         Cargo([], {("cargo", "package", "--locked", "--package"): killed}),
                                         no_sleep), "verification failed"),
            "publish": (lambda: cp.command_publish(["a"], Registry({"a": ["0.1.0"]}),
                                                   Cargo(packages, {("cargo", "publish"): killed})),
                        "cargo publish failed"),
            "release create": (lambda: cp.command_tag(["a"], "crate-", "abc", "o/r", False,
                                                      Registry({"a": ["0.2.0"]}),
                                                      Cargo(packages, {("gh", "release", "view"): (1, ""),
                                                                       ("gh", "release", "create"): killed}),
                                                      no_sleep), "could not create release"),
        }
        for step, (call, message) in steps.items():
            with self.subTest(step=step), contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaisesRegex(SystemExit, message):
                call()

    def test_a_failed_metadata_read_fails_the_command(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()) as stderr,                 self.assertRaisesRegex(SystemExit, "cargo metadata failed"):
            cp.command_publish(["a"], Registry({"a": ["0.1.0"]}), FailedMetadata([pkg("a", "0.2.0")]))
        self.assertIn("failed to parse manifest", stderr.getvalue())

    def test_a_release_view_killed_by_a_signal_is_no_release(self) -> None:
        cargo = Cargo([pkg("a", "0.2.0")], {("gh", "release", "view"): (-9, "")})
        with contextlib.redirect_stdout(io.StringIO()):
            cp.command_tag(["a"], "crate-", "abc", "o/r", False, Registry({"a": ["0.2.0"]}), cargo, no_sleep)
        self.assertEqual([c[3] for c in cargo.calls if c[:3] == ["gh", "release", "create"]], ["crate-a-v0.2.0"])


class KilledMetadata(Cargo):
    code = -9

    def __call__(self, argv: list[str]) -> subprocess.CompletedProcess:
        if argv[:2] == ["cargo", "metadata"]:
            return subprocess.CompletedProcess(argv, self.code, "", "error: failed to parse manifest")
        return super().__call__(argv)


class FailedMetadata(KilledMetadata):
    code = 101


class ArgumentTests(unittest.TestCase):
    """The command line as the action passes it: argv strings are never interned literals."""

    @staticmethod
    def built(*words: str) -> list[str]:
        return ["".join(list(word)) for word in words]

    def test_each_command_dispatches_on_the_value_of_its_name(self) -> None:
        with mock.patch.object(cp, "command_plan", return_value={"count": "0"}) as plan, \
                mock.patch.object(cp, "write_outputs"):
            cp.main(self.built("plan", "--owner", "someone"))
        plan.assert_called_once_with("someone")
        with mock.patch.object(cp, "command_publish") as publish:
            cp.main(self.built("publish", "a"))
        publish.assert_called_once_with(["a"])
        with mock.patch.object(cp, "command_tag") as tag:
            cp.main(self.built("tag", "a", "--prefix", "crate-", "--sha", "abc", "--repo", "o/r",
                               "--publish-outcome", "success"))
        tag.assert_called_once_with(["a"], "crate-", "abc", "o/r", True)

    def test_every_required_argument_is_required(self) -> None:
        tag = ["tag", "a", "--prefix", "crate-", "--sha", "abc", "--repo", "o/r", "--publish-outcome", "success"]
        cases = {"no command": [], "plan without --owner": ["plan"]}
        for flag in ("--prefix", "--sha", "--repo", "--publish-outcome"):
            at = tag.index(flag)
            cases[f"tag without {flag}"] = tag[:at] + tag[at + 2:]
        for case, argv in cases.items():
            with self.subTest(case=case), contextlib.redirect_stderr(io.StringIO()) as stderr, \
                    self.assertRaises(SystemExit) as exit_:
                cp.main(argv)
            self.assertEqual(exit_.exception.code, 2, case)
            self.assertIn("required", stderr.getvalue(), case)

    def test_help_describes_the_tool(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as stdout, self.assertRaises(SystemExit):
            cp.main(["--help"])
        self.assertIn("Select, publish, and tag workspace crates whose manifest version is not on crates.io.",
                      " ".join(stdout.getvalue().split()))

    def test_the_script_runs_main(self) -> None:
        script = ROOT / ".github" / "actions" / "crates-pending" / "crates_pending.py"
        result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 2)
        self.assertIn("the following arguments are required: command", result.stderr)


# python3 stand-in: records its argv one per line, then exits with $STUB_EXIT.
STUB_PYTHON = """\
#!/usr/bin/env bash
printf '%s\\n' "$@" > "$STUB_DIR/argv"
exit "${STUB_EXIT:-0}"
"""


@unittest.skipUnless(shutil.which("bash"), "the action step is a bash script")
class ActionScriptTests(unittest.TestCase):
    """The composite action's shell passes each input to the module unchanged and keeps its exit status."""

    @classmethod
    def setUpClass(cls) -> None:
        import yaml
        action = yaml.safe_load((ROOT / ".github" / "actions" / "crates-pending" / "action.yml").read_text(encoding="utf-8"))
        cls.step = action["runs"]["steps"][0]

    def run_action(self, command: str, exit_code: int = 0, **inputs: str):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = os.path.join(tmp, "bin")
            os.mkdir(bin_dir)
            stub = os.path.join(bin_dir, "python3")
            with open(stub, "w", encoding="utf-8", newline="\n") as out:
                out.write(STUB_PYTHON)
            os.chmod(stub, os.stat(stub).st_mode | stat.S_IXUSR)
            script = os.path.join(tmp, "step.sh")
            with open(script, "w", encoding="utf-8", newline="\n") as out:
                out.write(self.step["run"])
            env = dict(os.environ, PATH=bin_dir + os.pathsep + os.environ["PATH"], STUB_DIR=tmp,
                       STUB_EXIT=str(exit_code), COMMAND=command, GITHUB_ACTION_PATH="/action",
                       GITHUB_SHA="sha-value", GITHUB_REPOSITORY="owner/repo",
                       PACKAGES=inputs.get("packages", ""), OWNER=inputs.get("owner", ""),
                       TAG_PREFIX=inputs.get("tag_prefix", ""), PUBLISH_OUTCOME=inputs.get("publish_outcome", ""))
            proc = subprocess.run(["bash", script], env=env, capture_output=True, text=True)
            argv_file = os.path.join(tmp, "argv")
            argv = []
            if os.path.exists(argv_file):
                with open(argv_file, encoding="utf-8") as recorded:
                    argv = recorded.read().splitlines()
            return proc.returncode, argv

    def test_every_input_reaches_its_argument(self) -> None:
        self.assertEqual(self.run_action("plan", owner="someone"),
                         (0, ["/action/crates_pending.py", "plan", "--owner", "someone"]))
        self.assertEqual(self.run_action("publish", packages="a,b"),
                         (0, ["/action/crates_pending.py", "publish", "a,b"]))
        self.assertEqual(
            self.run_action("tag", packages="a,b", tag_prefix="crate-", publish_outcome="failure"),
            (0, ["/action/crates_pending.py", "tag", "a,b", "--prefix", "crate-", "--sha", "sha-value",
                 "--repo", "owner/repo", "--publish-outcome", "failure"]))

    def test_a_failing_command_fails_the_step(self) -> None:
        for command in ("plan", "publish", "tag"):
            self.assertEqual(self.run_action(command, exit_code=3, owner="o")[0], 3, command)
        self.assertNotEqual(self.run_action("unknown")[0], 0)

    def test_the_action_interface_and_output_plumbing(self) -> None:
        import yaml
        action = yaml.safe_load((ROOT / ".github" / "actions" / "crates-pending" / "action.yml").read_text(encoding="utf-8"))
        strip = lambda specs: {n: {k: v for k, v in s.items() if k != "description"} for n, s in specs.items()}
        self.assertEqual(strip(action["inputs"]), {
            "command": {"required": True},
            "packages": {"required": False, "default": ""},
            "owner": {"required": False, "default": "ryancinsight"},
            "tag-prefix": {"required": False, "default": "crate-"},
            "publish-outcome": {"required": False, "default": ""}})
        self.assertEqual(strip(action["outputs"]), {
            "packages": {"value": "${{ steps.run.outputs.packages }}"},
            "count": {"value": "${{ steps.run.outputs.count }}"}})
        self.assertEqual(action["runs"]["using"], "composite")
        self.assertEqual(len(action["runs"]["steps"]), 1)
        self.assertEqual((self.step["id"], self.step["shell"]), ("run", "bash"))

    def test_the_step_maps_its_environment_from_the_inputs(self) -> None:
        self.assertEqual(self.step["env"], {
            "COMMAND": "${{ inputs.command }}", "PACKAGES": "${{ inputs.packages }}",
            "OWNER": "${{ inputs.owner }}", "TAG_PREFIX": "${{ inputs.tag-prefix }}",
            "PUBLISH_OUTCOME": "${{ inputs.publish-outcome }}", "GH_TOKEN": "${{ github.token }}"})


if __name__ == "__main__":
    unittest.main()
