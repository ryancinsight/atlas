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
runs:
  using: composite
  steps:
    - shell: bash
      run: echo ok
"""


def fixture(test: unittest.TestCase) -> tuple[Path, Path, Path]:
    temporary = tempfile.TemporaryDirectory()
    test.addCleanup(temporary.cleanup)
    root = Path(temporary.name).resolve()
    workflow = root / ".github" / "workflows" / "check.yml"
    action = root / ".github" / "actions" / "sample" / "action.yml"
    workflow.parent.mkdir(parents=True)
    action.parent.mkdir(parents=True)
    (root / ".github" / "actionlint.yaml").write_text("self-hosted-runner:\n  labels: [custom-runner]\n", encoding="utf-8", newline="\n")
    workflow.write_text(WORKFLOW, encoding="utf-8", newline="\n")
    action.write_text(ACTION, encoding="utf-8", newline="\n")
    return root, workflow, action


def commit(test: unittest.TestCase, root: Path) -> str:
    commands = (
        ("init", "--quiet"),
        ("config", "user.email", "workflow-lint@example.invalid"),
        ("config", "user.name", "workflow-lint"),
        ("config", "core.autocrlf", "false"),
        ("add", "--", ".github"),
        ("commit", "--quiet", "-m", "test: add workflow fixture"),
    )
    for command in commands:
        result = lint.process_tree.run(["git", *command], cwd=root, timeout=30)
        test.assertEqual(result.returncode, 0, result.stderr)
    return lint._git(root, "rev-parse", "HEAD").decode().strip()


class WorkflowProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, self.workflow, self.action = fixture(self)

    def test_changes_only_reference_sigil_bytes(self) -> None:
        source = WORKFLOW.replace("name: test", "name: t\u00e9st").replace("\n", "\r\n").encode()

        projected, targets = lint.project(source, self.workflow, self.root, "workflow")

        self.assertEqual(projected, source.replace(b'uses: "$/', b'uses: "./', 1))
        self.assertEqual(targets, [self.action])

    def test_rejects_ambiguous_or_invalid_references(self) -> None:
        cases = {
            "alias": "shared: &ref $/.github/actions/sample\njobs:\n  build:\n    uses: *ref\n",
            "mutable": "jobs:\n  build:\n    uses: $/.github/workflows/check.yml@main\n",
            "traversal": "jobs:\n  build:\n    uses: $/../check.yml\n",
            "missing": WORKFLOW.replace("sample", "missing"),
        }
        for name, source in cases.items():
            with self.subTest(name=name), self.assertRaises(lint.WorkflowSourceError):
                lint.project(source.encode(), self.workflow, self.root, "workflow")

    def test_rejects_escaping_action_path_components(self) -> None:
        for kind in ("file", "directory"):
            root, workflow, action = fixture(self)
            outside = root.parent / f"{root.name}-{kind}"
            outside.mkdir()
            self.addCleanup(shutil.rmtree, outside)
            target = outside / "action.yml"
            target.write_text(ACTION, encoding="utf-8", newline="\n")
            action.unlink()
            try:
                if kind == "file":
                    action.symlink_to(target)
                else:
                    action.parent.rmdir()
                    action.parent.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest(f"{kind} symlinks are unavailable")
            with self.subTest(kind=kind), self.assertRaisesRegex(lint.WorkflowSourceError, "escapes|symlink"):
                lint.project(WORKFLOW.encode(), workflow, root, "workflow")


class CandidateSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, self.workflow, self.action = fixture(self)
        self.candidate = commit(self, self.root)

    def test_collects_candidate_owned_workflow_action_and_config(self) -> None:
        projected, inputs = lint.snapshot(self.root, self.candidate)

        self.assertEqual(projected[self.workflow], WORKFLOW.replace('uses: "$/', 'uses: "./', 1).encode())
        self.assertEqual(inputs[self.action], ACTION.encode())
        self.assertEqual(
            set(inputs),
            {self.workflow, self.action, self.root / ".github" / "actionlint.yaml"},
        )

    def test_rejects_changed_candidate_inputs(self) -> None:
        for path in (self.workflow, self.action, self.root / ".github" / "actionlint.yaml"):
            with self.subTest(path=path.relative_to(self.root)):
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                with self.assertRaisesRegex(lint.WorkflowSourceError, "differs from candidate"):
                    lint._candidate_bytes(self.root, self.candidate, path)
                path.write_bytes(original)

    def test_rejects_ignored_inputs_absent_from_candidate(self) -> None:
        for relative in (
            Path(".github/workflows/check.yml"),
            Path(".github/actions/sample/action.yml"),
            Path(".github/actionlint.yaml"),
        ):
            with self.subTest(path=relative):
                root, _, _ = fixture(self)
                path = root / relative
                source = path.read_bytes()
                path.unlink()
                candidate = commit(self, root)
                exclude = root / ".git" / "info" / "exclude"
                exclude.write_text(f"{relative.as_posix()}\n", encoding="utf-8", newline="\n")
                path.write_bytes(source)
                with self.assertRaises(lint.WorkflowSourceError):
                    lint.snapshot(root, candidate)

    def test_rejects_malformed_yaml(self) -> None:
        with self.assertRaises(yaml.YAMLError):
            lint.project(b"jobs: [", self.workflow, self.root, "workflow")


if __name__ == "__main__":
    unittest.main()
