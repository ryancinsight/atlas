import contextlib
import io
import itertools
import os
import posixpath
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_workflow_lint as lint  # noqa: E402
import test_atlas_workflow_lint as base  # noqa: E402
from workflow_checkout_prefix import Checkout, governing  # noqa: E402

PIN = "0" * 40
SAMPLE = "./.github/actions/sample"
REFERENCE = "./nested-src/.github/actions/sample"
FOREIGN = {"repository": "other/repository"}
MISSING = "reference escapes or is missing from the checkout"
UNDEFINED = "checkout path is not shown to hold the candidate"
CHECKOUT_PATHS = {
    "a workflow file": ".github/workflows/check.yml",
    "an existing candidate directory": ".github/actions/sample",
    "a component of 300 characters": "L" * 300,
    "200 components of 200 characters": "/".join(["D" * 200] * 200),
    "990 components": "/".join(["a"] * 990),
    "3000 components": "/".join(["a"] * 3000),
    "nul": "nul",
    "CON": "CON",
    "a device name inside a path": "x/COM1/y",
    "the letter case of .github": ".GITHUB",
    "the letter case of an action directory": ".github/actions/SAMPLE",
}
HELD, UNSHOWN = Checkout("nested-src", True), Checkout("nested-src", False)


def checkout(path: str | None = "nested-src", uses: str = "actions/checkout", **options: str) -> str:
    entries = ({"path": path} if path is not None else {}) | options
    lines = "".join(f"          {name}: '{value}'\n" for name, value in entries.items())
    return f"      - uses: {uses}@{PIN}\n        with:\n{lines}"


def job(*steps: str, name: str = "build") -> str:
    return f"  {name}:\n    runs-on: custom-runner\n    steps:\n" + "".join(steps)


def workflow(*jobs: str) -> str:
    return "name: test\non: push\njobs:\n" + "".join(jobs)


def step(reference: str = REFERENCE) -> str:
    return f"      - uses: {reference}\n"


def outcomes(source: str) -> list[Checkout | None]:
    """The prefix that governs each local step reference, in the order the references are first met."""
    return list(governing(yaml.compose(source, Loader=yaml.SafeLoader)).values())


def related(first: str, second: str) -> bool:
    return all(one == other for one, other in zip(first.casefold().split("/"), second.casefold().split("/")))


def governed(sequence: list[tuple[str | None, bool]], reference: str) -> Checkout | None:
    """The required outcome: the latest checkout at or above the reference decides unless a later one may rewrite it."""
    under = f"{reference}/".casefold()
    for index in range(len(sequence) - 1, -1, -1):
        path, holds_candidate = sequence[index]
        if path is None or not under.startswith(f"./{path}/".casefold()):
            continue
        if any(later is None or related(later, path) for later, _ in sequence[index + 1 :]):
            return None
        return Checkout(path, holds_candidate and reference.startswith(f"./{path}/"))
    return None


def candidate_at(sequence: list[tuple[str | None, bool]], reference: str) -> bool:
    """Simulate the workspace: whether a candidate checkout last wrote the directory the reference resolves to."""
    target = posixpath.normpath(reference[2:]).casefold().split("/")
    writes = [(None if path is None else path.casefold().split("/"), holds) for path, holds in sequence]
    for index in range(len(writes) - 1, -1, -1):
        parts, holds_candidate = writes[index]
        if parts is not None and target[: len(parts)] == parts:
            later = [other for other, _ in writes[index + 1 :]]
            return holds_candidate and all(o is not None and o[: len(parts)] != parts[: len(o)] for o in later)
    return False


class CheckoutPrefixTests(unittest.TestCase):
    def test_candidate_checkouts_hold_the_candidate(self) -> None:
        spellings = ("${{ github.sha }}", "${{github.event.pull_request.head.sha}}", "${{\tgithub.sha\t}}")
        for ref in (None, *spellings, "${{  github.event.pull_request.head.sha   ||github.sha }}"):
            options = {} if ref is None else {"ref": ref, "fetch-depth": "0", "persist-credentials": "false"}
            with self.subTest(ref=ref):
                self.assertEqual(outcomes(workflow(job(checkout(**options), step()))), [HELD])
        named = checkout(uses="Actions/Checkout") + "        name: Checkout\n        id: source\n"
        self.assertEqual(outcomes(workflow(job(named, step() + "        with: {}\n"))), [HELD])
        self.assertEqual(outcomes(workflow(job(checkout(), step("./nested-src")))), [HELD])
        document = yaml.compose(workflow(job(checkout(), step())), Loader=yaml.SafeLoader)
        reference = document.value[2][1].value[0][1].value[1][1].value[1].value[0][1]
        self.assertEqual(governing(document), {id(reference): HELD})
        other_repository = checkout(uses="actions/checkout-x", **FOREIGN)
        self.assertEqual(outcomes(workflow(job(checkout(), other_repository, step()))), [HELD])
        self.assertEqual(outcomes(workflow(job(checkout("Nested-Src"), step()))), [Checkout("Nested-Src", False)])

    def test_every_order_of_checkouts_follows_the_rule(self) -> None:
        action_directory = "nested-src/.github/actions/sample"
        shapes = {
            checkout(): ("nested-src", True),
            checkout(ref="main"): ("nested-src", False),
            checkout("nested-src/inner"): ("nested-src/inner", True),
            checkout("nested-src/inner", **FOREIGN): ("nested-src/inner", False),
            checkout(action_directory, **FOREIGN): (action_directory, False),
            checkout("Nested-Src", **FOREIGN): ("Nested-Src", False),
            checkout("Nested-Src"): ("Nested-Src", True),
            checkout("other-src", **FOREIGN): ("other-src", False),
            checkout(None, **FOREIGN): (None, False),
            checkout("./nested-src", **FOREIGN): (None, False),
        }
        plain = (REFERENCE, "./nested-src/inner/.github/actions/sample")
        # After the deciding checkout only unrelated known paths may follow. `nested-src` decides for both plain
        # references and admits one such shape: 1 + 11 + 111 = 123 sequences each. `nested-src/inner` decides
        # for the second and admits two: 1 + 12 + 124 = 137. The third reference leaves its prefix through `..`.
        held = 0
        for length, reference in itertools.product(range(4), (*plain, "./nested-src/../other-src/x")):
            for steps in itertools.product(shapes, repeat=length):
                sequence = [shapes[text] for text in steps]
                (found,) = outcomes(workflow(job(*steps, step(reference))))
                holds = found is not None and found.holds_candidate
                held += holds
                self.assertLessEqual(holds, candidate_at(sequence, reference), (steps, reference))
                if reference in plain:
                    self.assertEqual(found, governed(sequence, reference), (steps, reference))
        self.assertEqual(held, 123 + 123 + 137)

    def test_unreadable_steps_void_the_prefixes_before_them(self) -> None:
        raw = f"      - uses: actions/checkout@{PIN}\n"
        foreign = "          repository: other/repository\n"
        cases = {
            "expression path": checkout("${{ github.sha }}-src", **FOREIGN),
            "parent component": checkout("x/../nested-src", **FOREIGN),
            "trailing separator": checkout("nested-src/", **FOREIGN),
            "backslash": checkout("nested\\src", **FOREIGN),
            "padded path": checkout("nested-src ", **FOREIGN),
            "trailing dot": checkout("nested-src.", **FOREIGN),
            "block path": raw + f"        with:\n          path: |\n            nested-src\n{foreign}",
            "integer path": raw + f"        with:\n          path: 7\n{foreign}",
            "no inputs": raw,
            "repeated block": raw + f"        with:\n          path: other-src\n        with:\n{foreign}",
            "repeated input": raw + f"        with:\n          path: other-src\n          Path: nested-src\n{foreign}",
            "merge key": raw + "        with:\n          <<: {repository: o/r}\n          path: other-src\n",
            "step merge key": "      - <<: {uses: actions/checkout@" + PIN + ", with: {path: other-src}}\n",
            "key in another case": raw.replace("uses", "Uses") + "        with:\n          path: other-src\n",
            "short name": checkout("NESTED~1", **FOREIGN),
            "padded repeat": raw + f"        with:\n          path: other-src\n          'path ': x\n{foreign}",
            "action name is not a string": "      - uses: [actions/checkout]\n",
            "padded action name": checkout(uses="' actions/checkout", **FOREIGN).replace(PIN, f"{PIN}'", 1),
            "space after ref": checkout("other-src", uses="'actions/checkout", **FOREIGN).replace(PIN, f"{PIN} '", 1),
            "doubled separator": checkout(uses="actions//checkout", **FOREIGN),
            "leading separator": checkout(uses="/actions/checkout", **FOREIGN),
            "backslash in the name": checkout(uses="actions\\checkout", **FOREIGN),
            "owner outside ASCII": checkout(uses="acti\u043ens/checkout", **FOREIGN),
            "padded step key": checkout(**FOREIGN).replace("uses", "'uses '"),
            "step key padded in front": checkout(**FOREIGN).replace("uses", "' uses'"),
            "container reference": "      - uses: docker://alpine:3\n",
            "not a mapping": "      - plain\n",
        }
        for name, unreadable in cases.items():
            with self.subTest(name=name):
                self.assertEqual(outcomes(workflow(job(checkout(), unreadable, step()))), [None])
        for source in ("", "- 1\n", "jobs: 3\n", "jobs:\n  build: 3\n", "jobs:\n  build:\n    steps: 3\n"):
            with self.subTest(source=source):
                self.assertEqual(outcomes(source), [])

    def test_checkouts_not_shown_to_hold_the_candidate_govern_without_holding(self) -> None:
        cases = {
            "repository": checkout(**FOREIGN),
            "repository in another case": checkout(Repository="other/repository", ref="${{ github.sha }}"),
            "server": checkout(**{"github-server-url": "https://example.invalid"}),
            "unlisted input": checkout(clean="false"),
            "branch ref": checkout(ref="main"),
            "ref in another case": checkout(REF="main"),
            "other expression": checkout(ref="${{ github.ref }}"),
            "two expressions": checkout(ref="${{ github.sha }} ${{ github.ref }}"),
            "split name": checkout(ref="${{ git hub.sha }}"),
            "padded expression": checkout(ref=" ${{ github.sha }} "),
            "carriage return in the ref": checkout() + '          ref: "${{ github.sha\\r}}"\n',
            "condition": checkout() + "        if: github.event_name == 'push'\n",
            "tolerated failure": checkout() + "        continue-on-error: true\n",
            "condition after another repository": checkout(**FOREIGN) + checkout() + "        if: false\n",
            "path inside the repository": checkout(uses="actions/checkout/sub"),
            "unbroken space in the ref": checkout(ref="${{ github.sha }}"),
        }
        for name, steps in cases.items():
            with self.subTest(name=name):
                self.assertEqual(outcomes(workflow(job(steps, step()))), [UNSHOWN])
        callers = {
            "condition on the caller": step() + "        if: always()\n",
            "another letter case": step("./Nested-Src/.github/actions/sample"),
            "unreadable caller": step() + "        with: {}\n        with: {}\n",
            "checkout path itself": checkout(**FOREIGN) + step("./nested-src"),
            "parent component": step("./nested-src/../other-src/.github/actions/sample"),
            "repository metadata": step("./nested-src/.git/hooks"),
            "repository metadata in another case": step("./nested-src/.GIT/hooks"),
            "repository metadata directory": step("./nested-src/.git"),
            "odd spelling outside every prefix": step("./other-src./.github/actions/sample"),
        }
        for name, caller in callers.items():
            with self.subTest(name=name):
                self.assertEqual(outcomes(workflow(job(checkout(), caller))), [UNSHOWN])
        shared = job("      - &shared\n        uses: " + REFERENCE + "\n", checkout(), "      - *shared\n")
        self.assertEqual(outcomes(workflow(shared)), [UNSHOWN])

    def test_references_outside_a_preceding_checkout_are_not_governed(self) -> None:
        other_action = "      - uses: other/action@v1\n        with:\n          path: nested-src\n"
        repeated = "      - uses: " + SAMPLE + "\n        with: {}\n        with: {}\n"
        cases = {
            "no checkout": job(step()),
            "longer name": job(checkout("nested"), step()),
            "before checkout": job(step(), checkout()),
            "other job": job(checkout(), name="first") + job(step(), name="second"),
            "not a checkout": job(other_action, step()),
            "root reference": job(checkout(), step(SAMPLE)),
            "repeated block on a root reference": job(checkout(), repeated),
        }
        for name, definition in cases.items():
            with self.subTest(name=name):
                self.assertEqual(outcomes(workflow(definition)), [None])
        composite = f"runs:\n  using: composite\n  steps:\n    - uses: actions/checkout@{PIN}\n"
        composite += f"      with:\n        path: nested-src\n    - uses: {REFERENCE}\n"
        self.assertEqual(outcomes(composite), [])
        self.assertEqual(outcomes(workflow(job(checkout(), step() + step().replace("- ", "  ")))), [])
        self.assertEqual(outcomes(workflow(job(checkout(), step() + 2 * step().replace("- ", "  ")))), [])
        self.assertEqual(outcomes("jobs:\n  call:\n    uses: ./nested-src/.github/workflows/check.yml\n"), [])


class CheckoutPathGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, self.workflow, self.action = base.fixture(self)

    def outcome(self, source: str) -> str:
        try:
            targets = lint.project(source.encode(), self.workflow, self.root, "workflow")[1]
        except lint.WorkflowSourceError as error:
            return str(error)
        self.assertEqual(targets, [self.action] * source.count("uses: ./"))
        return "accepted"

    def commit_workflow(self, source: str, message: str) -> str:
        self.workflow.write_text(source, encoding="utf-8", newline="\n")
        return base.commit(self.root, message)

    def stand_in(self) -> Path:
        """An executable that reports the pinned `actionlint` version and accepts any input."""
        windows = os.name == "nt"
        tool = Path(self.enterContext(tempfile.TemporaryDirectory())) / ("analyzer.cmd" if windows else "analyzer")
        if windows:
            script = '@echo off\r\nif "%1"=="-version" (echo 1.7.12& exit /b 0)\r\nmore >nul\r\n'
        else:
            script = '#!/bin/sh\n[ "$1" = -version ] && { echo 1.7.12; exit 0; }\ncat >/dev/null\n'
        tool.write_bytes(script.encode())
        tool.chmod(0o755)
        return tool

    def run_main(self, candidate: str, tool: Path) -> tuple[int, str]:
        scratch = self.enterContext(tempfile.TemporaryDirectory())
        argv = ["workflow-lint", "--root", str(self.root), "--candidate", candidate]
        for option in ("actionlint", "shellcheck", "pyflakes"):
            argv += [f"--{option}", str(tool)]
        errors = io.StringIO()
        with mock.patch.object(sys, "argv", argv), mock.patch.object(tempfile, "tempdir", scratch):
            with contextlib.redirect_stderr(errors):
                status = lint.main()
        self.assertEqual(os.listdir(scratch), [])
        return status, errors.getvalue()

    def test_the_guard_resolves_references_as_the_rule_governs_them(self) -> None:
        inner = "./nested-src/inner/.github/actions/sample"
        shapes = {
            checkout(): ("nested-src", True),
            checkout(ref="main"): ("nested-src", False),
            checkout("nested-src/inner"): ("nested-src/inner", True),
            checkout("Nested-Src", **FOREIGN): ("Nested-Src", False),
            checkout("other-src", **FOREIGN): ("other-src", False),
            checkout(None, **FOREIGN): (None, False),
        }
        # The candidate has the action only at its root, so a reference is accepted exactly when a holding
        # prefix leaves `SAMPLE`: `nested-src` for the first reference, `nested-src/inner` for the second,
        # each followed only by `other-src`. That is 1 + 7 sequences of up to two checkouts per reference.
        accepted = 0
        for length, reference in itertools.product(range(3), (REFERENCE, inner)):
            for steps in itertools.product(shapes, repeat=length):
                over = governed([shapes[text] for text in steps], reference)
                rest = reference if over is None else f"./{reference[len(over.prefix) + 3 :]}"
                under = "" if over is None else f" (as {reference!r} under checkout {over.prefix!r})"
                expected = f"{MISSING}: {rest!r}{under}"
                if over is not None and not over.holds_candidate:
                    expected = f"{UNDEFINED}: {reference!r}"
                elif rest == SAMPLE:
                    expected = "accepted"
                accepted += expected == "accepted"
                self.assertEqual(self.outcome(workflow(job(*steps, step(reference)))), expected, (steps, reference))
        self.assertEqual(accepted, 8 + 8)
        at_root = "./nested-src"
        self.assertEqual(
            self.outcome(workflow(job(checkout(), step(at_root)))),
            f"invalid same-repository path: './' (as {at_root!r} under checkout 'nested-src')",
        )
        composite = f"runs:\n  using: composite\n  steps:\n{checkout()}{step()}".replace("\n      ", "\n    ")
        aliased = job(checkout(), "      - &inner\n        uses: " + REFERENCE + "\n")
        unused_jobs = "jobs:\n" + aliased + "runs:\n  using: composite\n  steps:\n    - *inner\n"
        at_the_root = f"{MISSING}: {REFERENCE!r}$"
        for name, metadata in {"composite steps": composite, "jobs beside composite steps": unused_jobs}.items():
            with self.subTest(name=name), self.assertRaisesRegex(lint.WorkflowSourceError, at_the_root):
                lint.project(metadata.encode(), self.action, self.root, "action")
        reusable = "jobs:\n  call:\n    uses: ./nested-src/.github/workflows/check.yml\n"
        self.assertEqual(self.outcome(reusable), f"{MISSING}: './nested-src/.github/workflows/check.yml'")

    def test_a_reference_under_a_holding_checkout_loses_only_the_checkout_path(self) -> None:
        spellings = {
            "plain": "{}",
            "single-quoted": "'{}'",
            "double-quoted": '"{}"',
            "tagged": "!!str {}",
            "literal block": "|-\n          {}",
            "folded block": ">-\n          {}",
        }
        for newline, (name, spelling) in itertools.product(("\n", "\r\n"), spellings.items()):

            def written(reference: str) -> bytes:
                source = workflow(job(checkout(), f"      - uses: {spelling.format(reference)}\n"))
                return source.replace("name: test", "name: tést").replace("\n", newline).encode()

            with self.subTest(name=name, newline=newline):
                projected, targets = lint.project(written(REFERENCE), self.workflow, self.root, "workflow")
                self.assertEqual(projected, written(SAMPLE))
                self.assertEqual(targets, [self.action])
        escaped = r'      - uses: "./nested-src/.github/actions/\x73ample"' + "\n"
        projected, _ = lint.project(workflow(job(checkout(), escaped)).encode(), self.workflow, self.root, "workflow")
        self.assertEqual(projected, workflow(job(checkout(), escaped.replace("nested-src/", ""))).encode())

    def test_each_deletion_and_replacement_lands_on_its_own_bytes(self) -> None:
        rest = ".github/actions/sample"

        def written(early: str, first: str, second: str, late: str) -> bytes:
            steps = step(early), checkout("nested-src"), step(first), checkout("other-src-longer"), step(second)
            return workflow(job(*steps, step(late))).replace("name: test", "name: tést").encode()

        source = written(f'"$/{rest}"', f"./nested-src/{rest}", f"'./other-src-longer/{rest}'", f"'$/{rest}'")
        projected, targets = lint.project(source, self.workflow, self.root, "workflow")
        self.assertEqual(projected, written(f'"./{rest}"', f"./{rest}", f"'./{rest}'", f"'./{rest}'"))
        self.assertEqual(targets, [self.action] * 4)

    def test_a_reference_that_cannot_be_rewritten_is_rejected(self) -> None:
        spellings = {
            "an escape inside the checkout path": r'"./nested\x2dsrc/.github/actions/sample"',
            "an escape in the leading dot": r'"\x2e/nested-src/.github/actions/sample"',
            "an escape in the separator": r'"./nested-src\x2f.github/actions/sample"',
        }
        for name, spelling in spellings.items():
            source = workflow(job(checkout(), f"      - uses: {spelling}\n"))
            with self.subTest(name=name), self.assertRaisesRegex(lint.WorkflowSourceError, "self-reference spelling"):
                lint.project(source.encode(), self.workflow, self.root, "workflow")
        shared = workflow(job(checkout(), f"      - uses: &ref {REFERENCE}\n", "      - uses: *ref\n"))
        with self.assertRaisesRegex(lint.WorkflowSourceError, "aliased same-repository reference"):
            lint.project(shared.encode(), self.workflow, self.root, "workflow")
        itself = workflow(job(checkout(), step("./nested-src")))
        with self.assertRaisesRegex(lint.WorkflowSourceError, "under checkout 'nested-src'") as raised:
            lint.project(itself.encode(), self.workflow, self.root, "workflow")
        self.assertIsInstance(raised.exception.__cause__, lint.WorkflowSourceError)

    def test_every_checkout_path_is_accepted_and_every_lint_input_is_a_tracked_path(self) -> None:
        workflow_path = ".github/workflows/check.yml"
        rows = {name: f".github/workflows/row{index}.yml" for index, name in enumerate(CHECKOUT_PATHS)}
        for name, relative in rows.items():
            prefix = CHECKOUT_PATHS[name]
            held = workflow(job(step(SAMPLE), checkout(prefix), step(f"./{prefix}/.github/actions/sample")))
            self.root.joinpath(*relative.split("/")).write_text(held, encoding="utf-8", newline="\n")
        candidate = base.commit(self.root, "test: add one workflow per checkout path")
        tracked = set(lint._git(self.root, "ls-tree", "-r", "--name-only", "-z", candidate).decode().split("\0"))
        projected, inputs = lint.snapshot(self.root, candidate)
        self.assertLessEqual(set(inputs), tracked)
        self.assertEqual(set(inputs), {workflow_path, base.ACTION_PATH, *rows.values()})
        with tempfile.TemporaryDirectory() as directory:
            lint._write_project(Path(directory), projected, inputs, 30)
            for name, relative in rows.items():
                rooted = workflow(job(step(SAMPLE), checkout(CHECKOUT_PATHS[name]), step(SAMPLE))).encode()
                with self.subTest(name=name):
                    self.assertEqual(Path(directory, relative).read_bytes(), rooted)
            self.assertEqual(Path(directory, base.ACTION_PATH).read_bytes(), base.ACTION.encode())
        self.assertEqual(self.run_main(candidate, self.stand_in()), (0, ""))


@unittest.skipUnless(
    all(os.environ.get(name) for name in ("ACTIONLINT", "SHELLCHECK", "PYFLAKES")),
    "native workflow analyzers are not configured",
)
class NativeCheckoutPathTests(unittest.TestCase):
    command = base.NativeActionlintTests.command

    def setUp(self) -> None:
        self.root, self.workflow, self.action = base.fixture(self)
        config = self.root / ".github" / "actionlint.yaml"
        config.write_text(base.CONFIG, encoding="utf-8", newline="\n")
        declared = "description: sample action\ninputs:\n  known:\n    description: known input"
        self.action.write_text(
            base.ACTION.replace("description: sample action", declared), encoding="utf-8", newline="\n"
        )

    def lint_with_input(self, name: str):
        source = workflow(job(checkout(), step() + f"        with:\n          {name}: yes\n"))
        self.workflow.write_text(source, encoding="utf-8", newline="\n")
        self.candidate = base.commit(self.root, f"test: pass the {name} input")
        return self.command()

    def test_actionlint_reads_the_action_through_the_rewritten_reference(self) -> None:
        accepted = self.lint_with_input("known")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        rejected = self.lint_with_input("unknown")
        self.assertEqual(rejected.returncode, 2, rejected.stdout)
        output = (rejected.stderr or b"").decode("utf-8", "replace")
        self.assertIn('input "unknown"', output)
        self.assertIn("check.yml", output)


if __name__ == "__main__":
    unittest.main()
