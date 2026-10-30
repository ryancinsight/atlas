import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import atlas_workflow_lint as lint  # noqa: E402


WORKFLOW = """name: test
on: push
env: &shared
  VALUE: fixed
jobs:
  build:
    env: *shared
    runs-on: custom-runner
    steps:
      - uses: "$/.github/actions/sample" # keep this comment
      - run: echo '$/not-a-reference'
"""
ACTION = """name: sample
description: sample action
inputs:
  known:
    description: known input
runs:
  using: composite
  steps:
    - shell: bash
      run: echo ok
"""


def fixture(test: unittest.TestCase) -> tuple[Path, Path, Path]:
    temporary = tempfile.TemporaryDirectory()
    test.addCleanup(temporary.cleanup)
    root = Path(temporary.name)
    workflow = root / ".github" / "workflows" / "check.yml"
    action = root / ".github" / "actions" / "sample" / "action.yml"
    workflow.parent.mkdir(parents=True)
    action.parent.mkdir(parents=True)
    (root / ".github" / "actionlint.yaml").write_text("self-hosted-runner:\n  labels: [custom-runner]\n", encoding="utf-8")
    workflow.write_text(WORKFLOW, encoding="utf-8", newline="\n")
    action.write_text(ACTION, encoding="utf-8", newline="\n")
    return root, workflow, action


def commit_fixture(test: unittest.TestCase, root: Path) -> str:
    for arguments in (
        ["init", "--quiet"],
        ["config", "user.email", "workflow-lint@example.invalid"],
        ["config", "user.name", "workflow-lint"],
        ["config", "core.autocrlf", "false"],
        ["add", "--", ".github"],
        ["commit", "--quiet", "-m", "test: add workflow fixture"],
    ):
        result = lint.process_tree.run(["git", *arguments], cwd=root, timeout=30)
        test.assertEqual(result.returncode, 0, result.stderr)
    return lint._git(root, "rev-parse", "HEAD")


class WorkflowProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, self.workflow, self.action = fixture(self)

    def test_projection_changes_only_the_reference_sigil(self) -> None:
        projected, targets = lint.project(self.workflow, self.root, "workflow")

        expected = WORKFLOW.replace('uses: "$/', 'uses: "./', 1).encode()
        self.assertEqual(projected, expected)
        self.assertEqual(targets, [self.action.resolve()])

    def test_projection_preserves_non_reference_bytes(self) -> None:
        source = WORKFLOW.replace("name: test", "name: t\u00e9st").replace("\n", "\r\n").encode()
        self.workflow.write_bytes(source)

        projected, _ = lint.project(self.workflow, self.root, "workflow")

        self.assertEqual(projected, source.replace(b'uses: "$/', b'uses: "./', 1))

    def test_rejects_ambiguous_and_invalid_references(self) -> None:
        cases = {
            "alias": "shared: &ref $/.github/actions/sample\njobs:\n  build:\n    uses: *ref\n",
            "mutable": "jobs:\n  build:\n    uses: $/.github/workflows/check.yml@main\n",
            "traversal": "jobs:\n  build:\n    uses: $/../check.yml\n",
            "missing": WORKFLOW.replace("sample", "missing"),
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                self.workflow.write_text(source, encoding="utf-8", newline="\n")
                with self.assertRaises(lint.WorkflowLintError):
                    lint.project(self.workflow, self.root, "workflow")

    def test_rejects_unsupported_and_escaping_targets(self) -> None:
        second = self.action.parent / "action.yaml"
        second.write_text(ACTION, encoding="utf-8")
        with self.assertRaisesRegex(lint.WorkflowLintError, "exactly one"):
            lint.project(self.workflow, self.root, "workflow")
        second.unlink()
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.mkdir()
        self.addCleanup(shutil.rmtree, outside)
        self.action.unlink()
        self.action.parent.rmdir()
        try:
            self.action.parent.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlinks are unavailable")
        with self.assertRaisesRegex(lint.WorkflowLintError, "escapes"):
            lint.project(self.workflow, self.root, "workflow")

    def test_rejects_escaping_action_metadata(self) -> None:
        outside = self.root.parent / f"{self.root.name}-metadata"
        outside.mkdir()
        self.addCleanup(shutil.rmtree, outside)
        outside_action = outside / "action.yml"
        outside_action.write_text(ACTION, encoding="utf-8", newline="\n")
        self.action.unlink()
        try:
            self.action.symlink_to(outside_action)
        except OSError:
            self.skipTest("file symlinks are unavailable")

        with self.assertRaisesRegex(lint.WorkflowLintError, "metadata escapes"):
            lint.project(self.workflow, self.root, "workflow")


class CandidateInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, self.workflow, self.action = fixture(self)
        self.candidate = commit_fixture(self, self.root)

    def test_collects_only_candidate_owned_inputs(self) -> None:
        projected, inputs = lint._collect(self.root.resolve(), self.candidate)

        self.assertEqual(projected[self.workflow.resolve()], WORKFLOW.replace('uses: "$/', 'uses: "./', 1).encode())
        self.assertEqual(inputs[self.action.resolve()], ACTION.encode())
        self.assertIn((self.root / ".github" / "actionlint.yaml").resolve(), inputs)

    def test_rejects_changed_or_untracked_ignored_inputs(self) -> None:
        cases = (self.workflow, self.action, self.root / ".github" / "actionlint.yaml")
        for path in cases:
            with self.subTest(path=path.relative_to(self.root)):
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                with self.assertRaisesRegex(lint.WorkflowLintError, "differs from candidate"):
                    lint._collect(self.root.resolve(), self.candidate)
                path.write_bytes(original)

        self.action.unlink()
        excluded = self.root / ".git" / "info" / "exclude"
        excluded.write_text(".github/actions/sample/action.yml\n", encoding="utf-8", newline="\n")
        self.action.write_text(ACTION, encoding="utf-8", newline="\n")
        tracked = lint.process_tree.run(["git", "rm", "--cached", "--quiet", "--", ".github/actions/sample/action.yml"], cwd=self.root, timeout=30)
        self.assertEqual(tracked.returncode, 0, tracked.stderr)
        removed = lint.process_tree.run(["git", "commit", "--quiet", "-m", "test: remove action metadata"], cwd=self.root, timeout=30)
        self.assertEqual(removed.returncode, 0, removed.stderr)
        candidate = lint._git(self.root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(lint.WorkflowLintError, "does not belong to candidate"):
            lint._collect(self.root.resolve(), candidate)


@unittest.skipUnless(os.environ.get("ACTIONLINT"), "ACTIONLINT is not configured")
class ActionlintIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, self.workflow, self.action = fixture(self)
        initialized = lint.process_tree.run(["git", "init", "--quiet"], cwd=self.root, timeout=30)
        self.assertEqual(initialized.returncode, 0, initialized.stderr)

    def actionlint(self, source: str):
        self.workflow.write_text(source, encoding="utf-8", newline="\n")
        projected, _ = lint.project(self.workflow, self.root, "workflow")
        return lint.process_tree.run(
            [os.environ["ACTIONLINT"], "-no-color", "-stdin-filename", str(self.workflow), "-"],
            cwd=self.root,
            input=projected,
            timeout=30,
        )

    def test_real_actionlint_retains_project_and_analyzer_checks(self) -> None:
        valid = WORKFLOW.replace(
            'uses: "$/.github/actions/sample"',
            'uses: "$/.github/actions/sample"\n        with:\n          known: yes',
        )
        self.assertEqual(self.actionlint(valid).returncode, 0)
        config = self.root / ".github" / "actionlint.yaml"
        config.unlink()
        unconfigured = self.actionlint(valid)
        self.assertIn("custom-runner", ((unconfigured.stdout or b"") + (unconfigured.stderr or b"")).decode())
        config.write_text("self-hosted-runner:\n  labels: [custom-runner]\n", encoding="utf-8")
        invalid = {
            "unknown": valid.replace("known: yes", "unknown: yes"),
            "unknown.value": valid.replace("echo '$/not-a-reference'", "echo '${{ unknown.value }}'"),
            "secrets": valid.replace("echo '$/not-a-reference'", "echo '${{ secrets }}'"),
            "missing": valid.replace("echo '$/not-a-reference'", "echo '${{ steps.missing.outputs.value }}'"),
        }
        if shutil.which("shellcheck"):
            invalid["SC2086"] = valid.replace("echo '$/not-a-reference'", "echo $UNQUOTED")
        if shutil.which("pyflakes"):
            invalid["undefined_name"] = valid.replace(
                "- run: echo '$/not-a-reference'",
                "- shell: python\n        run: print(undefined_name)",
            )
        for diagnostic, source in invalid.items():
            with self.subTest(diagnostic=diagnostic):
                result = self.actionlint(source)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                output = (result.stdout or b"") + (result.stderr or b"")
                self.assertIn(diagnostic, output.decode("utf-8", "replace"))

        self.workflow.write_text("jobs: [", encoding="utf-8", newline="\n")
        with self.assertRaises(yaml.YAMLError):
            lint.project(self.workflow, self.root, "workflow")


if __name__ == "__main__":
    unittest.main()
