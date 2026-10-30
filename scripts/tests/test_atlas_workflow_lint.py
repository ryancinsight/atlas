import os
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
ACTION_PATH = ".github/actions/sample/action.yml"
CONFIG = "self-hosted-runner:\n  labels: [custom-runner]\n"
GIT_IDENTITY = ("-c", "user.email=workflow-lint@example.invalid", "-c", "user.name=workflow-lint")
REUSABLE = """name: reusable
on: workflow_call
jobs:
  verify:
    runs-on: custom-runner
    steps:
      - run: echo reusable
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


def commit(root: Path, message: str = "test: add workflow fixture") -> str:
    if not (root / ".git").exists():
        lint._git(root, "init", "--quiet")
        lint._git(root, "config", "core.autocrlf", "false")
    lint._git(root, "add", "--", ".github")
    lint._git(root, *GIT_IDENTITY, "commit", "--quiet", "--allow-empty", "-m", message)
    return lint._git(root, "rev-parse", "HEAD").decode().strip()


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

        for spelling in (
            "!!str $/.github/actions/sample",
            '!!str "$/.github/actions/sample"',
            "&ref $/.github/actions/sample",
            '&ref "$/.github/actions/sample"',
        ):
            with self.subTest(spelling=spelling):
                source = WORKFLOW.replace('"$/.github/actions/sample"', spelling).encode()
                projected, targets = lint.project(source, self.workflow, self.root, "workflow")
                self.assertEqual(projected, source.replace(b"$/", b"./", 1))
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
            with self.subTest(kind=kind), self.assertRaisesRegex(lint.WorkflowSourceError, "escapes|alias"):
                lint.project(WORKFLOW.encode(), workflow, root, "workflow")

    def test_rejects_directory_action_metadata(self) -> None:
        alternative = self.action.with_suffix(".yaml")
        alternative.write_text(ACTION, encoding="utf-8", newline="\n")
        _, targets = lint.project(WORKFLOW.encode(), self.workflow, self.root, "workflow")
        self.assertEqual(targets, [self.action])

        self.action.unlink()
        self.action.mkdir()

        with self.assertRaisesRegex(lint.WorkflowSourceError, "regular file"):
            lint.project(WORKFLOW.encode(), self.workflow, self.root, "workflow")

    def test_rejects_malformed_yaml(self) -> None:
        with self.assertRaises(yaml.YAMLError):
            lint.project(b"jobs: [", self.workflow, self.root, "workflow")


class CandidateSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, self.workflow, self.action = fixture(self)
        self.config = self.root / ".github" / "actionlint.yaml"
        self.config.write_text(CONFIG, encoding="utf-8", newline="\n")
        (self.root / ".github" / "actionlint.yml").write_text("config-variables: null\n", encoding="utf-8")
        self.alternate = self.action.with_suffix(".yaml")
        self.alternate.write_text(ACTION.replace("sample action", "alternate action"), encoding="utf-8")
        self.ordinary = self.root / ".github" / "actions" / "ordinary" / "action.yml"
        self.ordinary.parent.mkdir()
        self.ordinary.write_text(ACTION.replace("sample", "ordinary"), encoding="utf-8")
        source = WORKFLOW.replace(
            "      - run: echo '$/not-a-reference'",
            "      - uses: ./.github/actions/ordinary\n      - run: echo '$/not-a-reference'",
        )
        self.workflow.write_text(source, encoding="utf-8", newline="\n")
        self.candidate = commit(self.root)

    def test_collects_raw_candidate_inputs_and_ignores_replacements(self) -> None:
        projected, inputs = lint.snapshot(self.root, self.candidate)
        expected = {
            ".github/workflows/check.yml",
            ".github/actionlint.yaml",
            ACTION_PATH,
            ".github/actions/sample/action.yaml",
            ".github/actions/ordinary/action.yml",
        }
        self.assertEqual(set(inputs), expected)
        workflow = ".github/workflows/check.yml"
        self.assertEqual(projected[workflow], inputs[workflow].replace(b'uses: "$/', b'uses: "./', 1))
        self.assertIn(b"uses: ./.github/actions/ordinary", projected[workflow])

        original = self.action.read_bytes()
        self.action.write_bytes(original.replace(b"echo ok", b"echo replaced"))
        alternate = commit(self.root, "test: create replacement candidate")
        self.action.write_bytes(original)
        lint._git(self.root, "add", "--", ACTION_PATH)
        lint._git(self.root, "update-ref", "HEAD", self.candidate)
        lint._git(self.root, "replace", self.candidate, alternate)
        _, replaced_inputs = lint.snapshot(self.root, self.candidate)
        self.assertEqual(replaced_inputs[ACTION_PATH], original)

    def test_rejects_clean_filter_and_case_inventory_drift(self) -> None:
        attributes = self.root / ".git" / "info" / "attributes"
        attributes.write_text(f"{ACTION_PATH} filter=judged\n", encoding="utf-8", newline="\n")
        lint._git(self.root, "config", "filter.judged.clean", f"git cat-file blob HEAD:{ACTION_PATH}")
        self.action.write_text(ACTION.replace("echo ok", "echo changed"), encoding="utf-8", newline="\n")
        lint._git(self.root, "add", "--", ACTION_PATH)
        self.assertEqual(lint._git(self.root, "status", "--porcelain"), b"")
        with self.assertRaisesRegex(lint.WorkflowSourceError, "differs from candidate"):
            lint.snapshot(self.root, self.candidate)

        root, workflow, _ = fixture(self)
        for name in ("Z.yml", "a.yml"):
            (workflow.parent / name).write_text("jobs: {}\n", encoding="utf-8", newline="\n")
        candidate = commit(root)
        projected, _ = lint.snapshot(root, candidate)
        self.assertEqual(
            tuple(projected),
            (".github/workflows/Z.yml", ".github/workflows/a.yml", ".github/workflows/check.yml"),
        )

        root, workflow, _ = fixture(self)
        workflow.write_text(WORKFLOW.replace("actions/sample", "actions/Sample"), encoding="utf-8")
        wrong_case = commit(root, "test: use wrong path case")
        with self.assertRaisesRegex(lint.WorkflowSourceError, "missing"):
            lint.snapshot(root, wrong_case)

    def test_validates_candidate_entry_modes(self) -> None:
        lint._git(self.root, "config", "core.filemode", "false")
        lint._git(self.root, "update-index", "--chmod=+x", ACTION_PATH)
        executable = commit(self.root, "test: use executable metadata")
        self.assertEqual(lint.snapshot(self.root, executable)[1][ACTION_PATH], self.action.read_bytes())

        link_source = self.root / ".git" / "link-source"
        link_source.write_text("ordinary/action.yml", encoding="utf-8", newline="\n")
        blob = lint._git(self.root, "hash-object", "-w", link_source.as_posix()).decode().strip()
        lint._git(self.root, "update-index", "--add", "--cacheinfo", f"120000,{blob},{ACTION_PATH}")
        lint._git(self.root, *GIT_IDENTITY, "commit", "--quiet", "-m", "test: add symlink entry")
        candidate = lint._git(self.root, "rev-parse", "HEAD").decode().strip()
        lint._git(self.root, "config", "core.symlinks", "false")
        lint._git(self.root, "checkout-index", "--force", "--", ACTION_PATH)

        self.assertTrue(lint._git(self.root, "ls-tree", "HEAD", ACTION_PATH).startswith(b"120000 blob "))
        self.assertFalse(self.action.is_symlink())
        self.assertEqual(lint._git(self.root, "status", "--porcelain"), b"")
        with self.assertRaisesRegex(lint.WorkflowSourceError, "not a regular Git file"):
            lint.snapshot(self.root, candidate)

    def test_rejects_ignored_metadata_and_config(self) -> None:
        for relative in (Path(".github/actionlint.yaml"), Path(ACTION_PATH)):
            with self.subTest(path=relative):
                root, _, _ = fixture(self)
                path = root / relative
                content = CONFIG.encode() if relative.name.startswith("actionlint") else path.read_bytes()
                if path.exists():
                    path.unlink()
                candidate = commit(root)
                (root / ".git" / "info" / "exclude").write_text(
                    f"{relative.as_posix()}\n", encoding="utf-8", newline="\n"
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                with self.assertRaisesRegex(lint.WorkflowSourceError, "inventory differs"):
                    lint.snapshot(root, candidate)

    def test_rejects_candidate_and_head_movement(self) -> None:
        for candidate in ("HEAD", self.candidate.upper()):
            with self.subTest(candidate=candidate), self.assertRaisesRegex(
                lint.WorkflowSourceError, "full lowercase"
            ):
                lint.snapshot(self.root, candidate)

        moved = commit(self.root, "test: create same-tree commit")
        lint._git(self.root, "update-ref", "HEAD", self.candidate)
        hook = self.root / ".git" / "hooks" / "move-head"
        hook.write_text(f"#!/bin/sh\ngit update-ref HEAD {moved}\nprintf 'token\\n'\n", encoding="utf-8", newline="\n")
        hook.chmod(0o755)
        lint._git(self.root, "config", "core.fsmonitor", hook.as_posix())
        with self.assertRaisesRegex(lint.WorkflowSourceError, "declared candidate|source changed"):
            lint.snapshot(self.root, self.candidate)
        self.assertEqual(lint._git(self.root, "rev-parse", "HEAD").decode().strip(), moved)

    def test_rejects_bytes_changed_by_ending_status(self) -> None:
        attributes = self.root / ".git" / "info" / "attributes"
        attributes.write_text(f"{ACTION_PATH} filter=judged\n", encoding="utf-8", newline="\n")
        lint._git(self.root, "config", "filter.judged.clean", f"git cat-file blob HEAD:{ACTION_PATH}")
        hook = self.root / ".git" / "hooks" / "change-input"
        hook.write_text(
            "#!/bin/sh\n"
            "count_file=.git/fsmonitor-count\n"
            "count=0\n"
            "test ! -f \"$count_file\" || count=$(cat \"$count_file\")\n"
            "count=$((count + 1))\n"
            "printf '%s\\n' \"$count\" > \"$count_file\"\n"
            f"test \"$count\" -ne 3 || sed 's/echo ok/echo changed/' {ACTION_PATH} > .git/action.tmp\n"
            f"test \"$count\" -ne 3 || cp .git/action.tmp {ACTION_PATH}\n"
            "printf 'token\\n'\n",
            encoding="utf-8",
            newline="\n",
        )
        hook.chmod(0o755)
        lint._git(self.root, "config", "core.fsmonitor", hook.as_posix())

        with self.assertRaisesRegex(lint.WorkflowSourceError, "differs from candidate"):
            lint.snapshot(self.root, self.candidate)
        self.assertEqual((self.root / ".git" / "fsmonitor-count").read_text().strip(), "3")
        self.assertIn(b"echo changed", self.action.read_bytes())


@unittest.skipUnless(
    all(os.environ.get(name) for name in ("ACTIONLINT", "SHELLCHECK", "PYFLAKES")),
    "native workflow analyzers are not configured",
)
class NativeActionlintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, self.workflow, self.action = fixture(self)
        self.config = self.root / ".github" / "actionlint.yaml"
        self.config.write_text(CONFIG, encoding="utf-8", newline="\n")
        nested = self.root / ".github" / "actions" / "nested" / "action.yml"
        nested.parent.mkdir()
        nested.write_text(ACTION.replace("sample", "nested"), encoding="utf-8", newline="\n")
        self.action.write_text(
            ACTION.replace(
                "description: sample action",
                "description: sample action\ninputs:\n  known:\n    description: known input",
            ).replace("    - shell: bash", '    - uses: "$/.github/actions/nested"\n    - shell: bash'),
            encoding="utf-8",
            newline="\n",
        )
        reusable = self.workflow.with_name("reusable.yml")
        reusable.write_text(REUSABLE, encoding="utf-8", newline="\n")
        self.valid = WORKFLOW.replace(
            '      - uses: "$/.github/actions/sample" # keep this comment',
            '      - uses: "$/.github/actions/sample" # keep this comment\n        with:\n          known: yes',
        ).replace(
            "  build:\n",
            '  reuse:\n    uses: "$/.github/workflows/reusable.yml"\n  build:\n',
        )
        self.workflow.write_text(self.valid, encoding="utf-8", newline="\n")
        self.candidate = commit(self.root)

    def command(self, *extra: str, actionlint: str | None = None):
        command = [
            sys.executable,
            "-I",
            str(SCRIPTS / "python_source_loader.py"),
            "--module",
            f"process_tree={SCRIPTS / 'process_tree.py'}",
            "--module",
            f"windows_process={SCRIPTS / 'windows_process.py'}",
            "--module",
            f"darwin_process={SCRIPTS / 'darwin_process.py'}",
            str(SCRIPTS / "atlas_workflow_lint.py"),
            "--root",
            str(self.root),
            "--candidate",
            self.candidate,
            "--actionlint",
            actionlint or os.environ["ACTIONLINT"],
            "--shellcheck",
            os.environ["SHELLCHECK"],
            "--pyflakes",
            os.environ["PYFLAKES"],
            *extra,
        ]
        return lint.process_tree.run(command, cwd=self.root, timeout=60)

    def restoring_actionlint(self, target: Path, changed: bytes) -> str:
        original = self.root / ".git" / f"original-{target.name}"
        replacement = self.root / ".git" / f"replacement-{target.name}"
        original.write_bytes(target.read_bytes())
        replacement.write_bytes(changed)
        wrapper = self.root / ".git" / ("restoring-actionlint.cmd" if os.name == "nt" else "restoring-actionlint")
        if os.name == "nt":
            wrapper.write_text(
                f'@echo off\r\nif "%1"=="-version" goto run\r\ncopy /y "{replacement}" "{target}" >NUL\r\n'
                f'"{os.environ["ACTIONLINT"]}" %*\r\nset code=%errorlevel%\r\n'
                f'copy /y "{original}" "{target}" >NUL\r\nexit /b %code%\r\n:run\r\n'
                f'"{os.environ["ACTIONLINT"]}" %*\r\n',
                encoding="utf-8",
                newline="",
            )
        else:
            wrapper.write_text(
                "#!/bin/sh\n"
                f'[ "$1" = "-version" ] && exec "{os.environ["ACTIONLINT"]}" "$@"\n'
                f'cp "{replacement}" "{target}"\ntrap \'cp "{original}" "{target}"\' EXIT HUP INT TERM\n'
                f'"{os.environ["ACTIONLINT"]}" "$@"\n',
                encoding="utf-8",
                newline="\n",
            )
            wrapper.chmod(0o755)
        return str(wrapper)

    def test_native_project_checks_and_diagnostics(self) -> None:
        self.assertIn(".github/actions/nested/action.yml", lint.snapshot(self.root, self.candidate)[1])
        result = self.command()
        self.assertEqual(result.returncode, 0, result.stderr)
        cases = {
            "SC2086": self.valid.replace("echo '$/not-a-reference'", "echo $UNQUOTED"),
            "unknown.value": self.valid.replace("echo '$/not-a-reference'", "echo '${{ unknown.value }}'"),
            "undefined_name": self.valid.replace(
                "- run: echo '$/not-a-reference'",
                "- shell: python\n        run: print(undefined_name)",
            ),
            'input "unknown"': self.valid.replace("known: yes", "unknown: yes"),
        }
        for diagnostic, source in cases.items():
            with self.subTest(diagnostic=diagnostic):
                self.workflow.write_text(source, encoding="utf-8", newline="\n")
                self.candidate = commit(self.root, f"test: reject {diagnostic}")
                result = self.command()
                self.assertEqual(result.returncode, 2, result.stdout)
                output = (result.stderr or b"").decode("utf-8", "replace")
                self.assertIn(diagnostic, output)
                self.assertIn("check.yml", output)
                self.assertNotIn("atlas-workflow-lint-", output)
        self.workflow.write_text(self.valid, encoding="utf-8", newline="\n")
        reusable = self.workflow.with_name("reusable.yml")
        reusable.write_text(REUSABLE.replace("echo reusable", "echo '${{ unknown.value }}'"), encoding="utf-8")
        self.candidate = commit(self.root, "test: reject invalid reusable workflow")
        result = self.command()
        self.assertEqual(result.returncode, 2, result.stdout)
        output = (result.stderr or b"").decode()
        self.assertIn("unknown.value", output)
        self.assertIn("reusable.yml", output)

    def test_rejects_tool_failure_and_analysis_mutation(self) -> None:
        missing = str(self.root / ".git" / "missing-tool")
        for option in ("--shellcheck", "--pyflakes"):
            with self.subTest(option=option):
                result = self.command(option, missing)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("executable is unavailable", (result.stderr or b"").decode())
        result = self.command(actionlint=missing)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("required actionlint executable", (result.stderr or b"").decode())

        timed_out = self.command("--timeout", "0.000001")
        self.assertEqual(timed_out.returncode, 2, timed_out.stdout)
        self.assertIn("deadline", (timed_out.stderr or b"").decode())

        wrapper = self.root / ".git" / ("actionlint.cmd" if os.name == "nt" else "actionlint")
        for target in (self.config, self.action):
            with self.subTest(mutation=target.relative_to(self.root)):
                original = target.read_bytes()
                if os.name == "nt":
                    wrapper.write_text(
                        f'@echo off\r\nif not "%1"=="-version" echo changed: true>"{target}"\r\n'
                        f'"{os.environ["ACTIONLINT"]}" %*\r\n',
                        encoding="utf-8",
                        newline="",
                    )
                else:
                    wrapper.write_text(
                        "#!/bin/sh\n"
                        f'[ "$1" = "-version" ] || printf "changed: true\\n" > "{target}"\n'
                        f'exec "{os.environ["ACTIONLINT"]}" "$@"\n',
                        encoding="utf-8",
                        newline="\n",
                    )
                    wrapper.chmod(0o755)
                result = self.command(actionlint=str(wrapper))
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("candidate checkout is not clean", (result.stderr or b"").decode())
                target.write_bytes(original)

    def test_analyzes_captured_inputs_when_origin_is_restored(self) -> None:
        original_action = self.action.read_bytes()
        self.workflow.write_text(self.valid.replace("known: yes", "injected: yes"), encoding="utf-8")
        self.candidate = commit(self.root, "test: reject transient action input")
        changed_action = original_action.replace(
            b"inputs:\n",
            b"inputs:\n  injected:\n    description: transient input\n",
        )
        result = self.command(actionlint=self.restoring_actionlint(self.action, changed_action))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn('input "injected"', (result.stderr or b"").decode())
        self.assertEqual(self.action.read_bytes(), original_action)
        self.assertEqual(lint._git(self.root, "status", "--porcelain"), b"")

        self.workflow.write_text(self.valid.replace("custom-runner", "transient-runner"), encoding="utf-8")
        self.candidate = commit(self.root, "test: reject transient runner config")
        changed_config = CONFIG.replace("]", ", transient-runner]").encode()
        result = self.command(actionlint=self.restoring_actionlint(self.config, changed_config))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("transient-runner", (result.stderr or b"").decode())
        self.assertEqual(self.config.read_bytes(), CONFIG.encode())
        self.assertEqual(lint._git(self.root, "status", "--porcelain"), b"")


if __name__ == "__main__":
    unittest.main()
