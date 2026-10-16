"""Explicit release cohorts never expand into an unrelated pending package."""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_crates_pending as legacy
from test_crates_pending import Cargo, OWNER, ROOT, Registry, cp, no_sleep, pkg


class CohortTests(unittest.TestCase):
    def test_plan_verifies_only_the_exact_requested_cohort(self):
        registry = Registry({"alpha": ["1.0.0"], "unrelated": ["8.0.0"]})
        cargo = Cargo([pkg("alpha", "1.1.0"), pkg("unrelated", "9.0.0")])
        with contextlib.redirect_stdout(io.StringIO()):
            result = cp.command_plan(OWNER, registry, cargo, no_sleep,
                                     cohort={"alpha": "1.1.0"})
        self.assertEqual(result, {"packages": "alpha", "count": "1"})
        self.assertEqual(cargo.calls[1:], [
            ["cargo", "package", "--locked", "--no-verify", "--package", "alpha"],
            ["cargo", "package", "--locked", "--package", "alpha"],
        ])
        self.assertFalse(any("unrelated" in url for url in registry.asked))

    def test_explicit_empty_cohort_is_unarmed_without_cargo_or_registry(self):
        def forbidden(*args):
            raise AssertionError(f"empty cohort must not perform I/O: {args}")
        self.assertEqual(cp.command_plan(OWNER, forbidden, forbidden, forbidden, cohort={}),
                         {"count": "0"})

    def test_held_cohort_never_falls_back_to_an_unrelated_ready_package(self):
        registry = Registry({"alpha": ["1.0.0"], "unrelated": ["8.0.0"]})
        cargo = Cargo([pkg("alpha", "1.1.0", deps=("upstream",)), pkg("unrelated", "9.0.0")],
                      {("cargo", "package", "--locked", "--no-verify"):
                       (101, 'error: failed to select a version for the requirement `upstream = "^0.7.0"`')})
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = cp.command_plan(OWNER, registry, cargo, no_sleep,
                                     cohort={"alpha": "1.1.0"})
        self.assertEqual(result, {"count": "0"})
        self.assertFalse(any("unrelated" in url for url in registry.asked))
        self.assertFalse(any("unrelated" in argv for argv in cargo.calls))

    def test_cohort_json_is_an_exact_flat_identity_map(self):
        self.assertEqual(cp.parse_cohort('{}'), {})
        self.assertEqual(cp.parse_cohort('{"alpha":"1.2.3-rc.1+build"}'),
                         {"alpha": "1.2.3-rc.1+build"})
        for raw in ['', 'null', '[]', 'true', '{"alpha":false}', '{"alpha":{}}',
                    '{"alpha":""}', '{"bad/name":"1.0.0"}',
                    '{"alpha":"1.0.0","alpha":"2.0.0"}']:
            with self.subTest(raw=raw), self.assertRaises(SystemExit):
                cp.parse_cohort(raw)

    def test_unknown_private_or_wrong_version_requests_fail_before_registry(self):
        for cohort in [{"absent": "1.1.0"}, {"alpha": "1.2.0"}, {"private": "1.0.0"}]:
            registry = Registry({"alpha": ["1.0.0"]})
            cargo = Cargo([pkg("alpha", "1.1.0"), pkg("private", "1.0.0", [])])
            with self.subTest(cohort=cohort), self.assertRaises(SystemExit):
                cp.command_plan(OWNER, registry, cargo, no_sleep, cohort=cohort)
            self.assertEqual(registry.asked, [])
            self.assertEqual(len(cargo.calls), 1)

    def test_publish_rejects_every_unplanned_name_before_any_upload(self):
        for names in [["alpha", "unrelated"], ["unrelated"], ["alpha", "alpha"], [""]]:
            registry = Registry({"alpha": ["1.0.0"], "unrelated": ["9.0.0"]})
            cargo = Cargo([pkg("alpha", "1.1.0"), pkg("unrelated", "9.0.0")])
            with self.subTest(names=names), self.assertRaises(SystemExit):
                cp.command_publish(names, registry, cargo, cohort={"alpha": "1.1.0"})
            self.assertEqual(registry.asked, [])
            self.assertFalse(any(c[:2] == ["cargo", "publish"] for c in cargo.calls))

    def test_publish_and_tag_reject_manifest_version_drift(self):
        for command in ['publish', 'tag']:
            registry = Registry({"alpha": ["1.2.0"]})
            cargo = Cargo([pkg("alpha", "1.2.0")])
            with self.subTest(command=command), self.assertRaises(SystemExit):
                if command == 'publish':
                    cp.command_publish(["alpha"], registry, cargo, cohort={"alpha": "1.1.0"})
                else:
                    cp.command_tag(["alpha"], "crate-", "sha", "o/r", True,
                                   registry, cargo, no_sleep, cohort={"alpha": "1.1.0"})
            self.assertEqual(registry.asked, [])
            self.assertEqual(len(cargo.calls), 1)

    def test_tag_rejects_unrelated_names_before_creating_any_release(self):
        registry = Registry({"alpha": ["1.1.0"], "unrelated": ["9.0.0"]})
        cargo = Cargo([pkg("alpha", "1.1.0"), pkg("unrelated", "9.0.0")])
        with self.assertRaises(SystemExit):
            cp.command_tag(["alpha", "unrelated"], "crate-", "sha", "o/r", True,
                           registry, cargo, no_sleep, cohort={"alpha": "1.1.0"})
        self.assertEqual(registry.asked, [])
        self.assertFalse(any(c[0] == 'gh' for c in cargo.calls))

    def test_valid_publish_keeps_the_planned_subset(self):
        cargo = Cargo([pkg("alpha", "1.1.0"), pkg("unrelated", "9.0.0")])
        with contextlib.redirect_stdout(io.StringIO()):
            cp.command_publish(["alpha"], Registry({"alpha": ["1.0.0"]}), cargo,
                               cohort={"alpha": "1.1.0"})
        self.assertEqual(cargo.calls[-1],
                         ["cargo", "publish", "--locked", "--no-verify", "--package", "alpha"])

    def test_valid_tag_uses_only_the_exact_version(self):
        cargo = Cargo([pkg("alpha", "1.1.0"), pkg("unrelated", "9.0.0")],
                      {("gh", "release", "view"): (1, "")})
        with contextlib.redirect_stdout(io.StringIO()):
            cp.command_tag(["alpha"], "crate-", "sha", "o/r", True,
                           Registry({"alpha": ["1.1.0"]}), cargo, no_sleep,
                           cohort={"alpha": "1.1.0"})
        created = [c for c in cargo.calls if c[:3] == ['gh', 'release', 'create']]
        self.assertEqual([c[3] for c in created], ['crate-alpha-v1.1.0'])

    def test_real_cli_empty_cohort_never_invokes_cargo(self):
        script = ROOT / '.github/actions/crates-pending/crates_pending.py'
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            result = subprocess.run(
                [sys.executable, str(script), 'plan', '--owner', OWNER, '--cohort-json', '{}'],
                env=dict(os.environ, PATH=directory, GITHUB_OUTPUT=str(output)),
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(), 'count=0\n')

    def test_action_forwards_the_same_cohort_to_every_command(self):
        legacy.ActionScriptTests.setUpClass()
        action = legacy.ActionScriptTests('test_every_input_reaches_its_argument')
        for command in ['plan', 'publish', 'tag']:
            with self.subTest(command=command):
                code, argv = action.run_action(command, packages='alpha', owner=OWNER,
                                               cohort_json='{"alpha":"1.1.0"}')
                self.assertEqual(code, 0)
                self.assertEqual(argv[-2:], ['--cohort-json', '{"alpha":"1.1.0"}'])

    def test_installation_empty_cohort_keeps_both_privileged_jobs_unarmed(self):
        import yaml
        workflow = yaml.safe_load((ROOT / '.github/workflows/crates-publish-pending.yml').read_text())
        self.assertEqual(set(workflow[True]), {'workflow_call'})
        result = cp.command_plan(OWNER, cohort=cp.parse_cohort('{}'))
        self.assertEqual(result, {'count': '0'})
        for name in ['semver', 'publish']:
            self.assertEqual(workflow['jobs'][name]['if'], "needs.plan.outputs.count != '0'")
            self.assertFalse(result['count'] != '0')
        for job in ['plan', 'publish']:
            for step in workflow['jobs'][job]['steps']:
                if step.get('with', {}).get('command') in ['plan', 'publish', 'tag']:
                    self.assertEqual(step['with']['cohort-json'], '${{ inputs.cohort-json }}')


if __name__ == '__main__':
    unittest.main()
