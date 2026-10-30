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
    root = Path(test.enterContext(tempfile.TemporaryDirectory())).resolve()
    workflow = root / ".github" / "workflows" / "check.yml"
    action = root / ".github" / "actions" / "sample" / "action.yml"
    workflow.parent.mkdir(parents=True)
    action.parent.mkdir(parents=True)
    workflow.write_text(WORKFLOW, encoding="utf-8", newline="\n")
    action.write_text(ACTION, encoding="utf-8", newline="\n")
    return root, workflow, action


class WorkflowProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, self.workflow, self.action = fixture(self)

    def test_changes_only_reference_sigil_bytes(self) -> None:
        source = WORKFLOW.replace("name: test", "name: t\u00e9st").replace("\n", "\r\n").encode()

        projected, targets = lint.project(source, self.workflow, self.root, "workflow")

        self.assertEqual(projected, source.replace(b'uses: "$/', b'uses: "./', 1))
        self.assertEqual(targets, [self.action])

        block = WORKFLOW.replace(
            'uses: "$/.github/actions/sample" # keep this comment',
            "uses: >- # $/ is a self reference\n          $/.github/actions/sample",
        )
        projected, _ = lint.project(block.encode(), self.workflow, self.root, "workflow")
        self.assertEqual(projected, block.replace("\n          $/", "\n          ./", 1).encode())

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

    def test_rejects_unsupported_spelling_and_nonstring_tags(self) -> None:
        cases = {
            "escaped": (
                WORKFLOW.replace('"$/.github/actions/sample"', r'"\x24/.github/actions/$/sample"'),
                "unsupported leading self-reference spelling",
            ),
            "tag": (WORKFLOW.replace('"$/.github/actions/sample"', "!!int $/"), "string scalar"),
        }
        for name, (source, message) in cases.items():
            with self.subTest(name=name), self.assertRaisesRegex(lint.WorkflowSourceError, message):
                lint.project(source.encode(), self.workflow, self.root, "workflow")

    def test_rejects_escaping_action_path_components(self) -> None:
        for kind in ("file", "directory"):
            root, workflow, action = fixture(self)
            outside = Path(self.enterContext(tempfile.TemporaryDirectory()))
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

    def test_rejects_malformed_yaml(self) -> None:
        with self.assertRaises(yaml.YAMLError):
            lint.project(b"jobs: [", self.workflow, self.root, "workflow")


if __name__ == "__main__":
    unittest.main()
