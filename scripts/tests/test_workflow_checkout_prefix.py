import itertools
import os
import posixpath
import sys
import tempfile
import unittest
from pathlib import Path

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
COLLISION = "lint input path has two different sources"
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
            "suffixed action name": checkout(uses="actions/checkout.git"),
            "suffixed name over the prefix": checkout() + checkout(uses="Actions/Checkout.GIT", **FOREIGN),
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
        for key in ("container: alpine:3", "Container: alpine:3", "'container ': alpine:3", "env: {}\n    env: {}"):
            contained = job(checkout(), step()).replace("    steps:", f"    {key}\n    steps:")
            with self.subTest(job_key=key):
                self.assertEqual(outcomes(workflow(contained)), [UNSHOWN])
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

    def snapshot(self, source: str, message: str) -> tuple[dict[str, bytes], dict[str, bytes]]:
        self.workflow.write_text(source, encoding="utf-8", newline="\n")
        return lint.snapshot(self.root, base.commit(self.root, message))

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

    def test_action_metadata_is_copied_under_the_checkout_path(self) -> None:
        projected, inputs = self.snapshot(workflow(job(step(SAMPLE), checkout(), step())), "copy")
        prefixed = f"nested-src/{base.ACTION_PATH}"
        self.assertEqual(set(inputs), {".github/workflows/check.yml", base.ACTION_PATH, prefixed})
        self.assertEqual(inputs[base.ACTION_PATH], base.ACTION.encode())
        self.assertEqual(inputs[prefixed], inputs[base.ACTION_PATH])
        self.assertEqual(projected[".github/workflows/check.yml"], inputs[".github/workflows/check.yml"])
        analysis = Path(self.enterContext(tempfile.TemporaryDirectory()))
        lint._write_project(analysis, projected, inputs, 30)
        self.assertEqual((analysis / prefixed).read_bytes(), base.ACTION.encode())

    def test_a_copy_never_shares_a_directory_with_another_source(self) -> None:
        outer = ".github/actions/outer"
        shadow = self.root.joinpath(*outer.split("/"), ".github", "actions", "sample", "action.yaml")
        shadow.parent.mkdir(parents=True)
        shadow.write_text(base.ACTION.replace("sample", "shadow"), encoding="utf-8", newline="\n")
        copied, shadowed = step(f"./{outer}/.github/actions/sample"), step(f"./{outer}/{outer}/.github/actions/sample")
        orders = {
            "root reference first": job(copied, checkout(outer), copied),
            "copy first": job(checkout(outer), copied, name="first") + job(copied, name="second"),
            "shadow through the prefix": job(checkout(outer), copied, shadowed),
            "shadow through the prefix first": job(checkout(outer), shadowed, copied),
        }
        for name, definition in orders.items():
            with self.subTest(name=name), self.assertRaisesRegex(
                lint.WorkflowSourceError, f"{COLLISION}: {outer}/.github/actions/sample$"
            ):
                self.snapshot(workflow(definition), name)
        twice = step(f"./p/{outer}/.github/actions/sample")
        copies = job(checkout("p"), twice, name="first") + job(checkout(f"p/{outer}"), twice, name="second")
        with self.assertRaisesRegex(lint.WorkflowSourceError, f"{COLLISION}: p/{outer}/.github/actions/sample$"):
            self.snapshot(workflow(copies), "two copies")

    def test_a_copy_never_crosses_the_path_of_another_input(self) -> None:
        inside = f".github/{base.ACTION_PATH}"
        below = self.root.joinpath(*inside.split("/"), "below", "action.yml")
        below.parent.mkdir(parents=True)
        below.write_text(base.ACTION, encoding="utf-8", newline="\n")
        check, copy = ".github/workflows/check.yml", f"p/{base.ACTION_PATH}"

        def through(prefix: str, name: str = "build") -> str:
            return job(checkout(prefix), step(f"./{prefix}/.github/actions/sample"), name=name)

        at_the_root = job(step(f"./{inside}/below"), name="first")
        cases = {
            "workflow above a copy": (through(check), check),
            "copy above a copy": (through("p", "first") + through(copy, "second"), copy),
            "copy below a copy": (through(copy, "first") + through("p", "second"), copy),
            "copy above a candidate action": (at_the_root + through(".github", "second"), inside),
            "two crossings": (through(check, "first") + through("p", "second") + through(copy, "third"), check),
        }
        for name, (definition, crossed) in cases.items():
            with self.subTest(name=name), self.assertRaisesRegex(
                lint.WorkflowSourceError, f"{COLLISION}: {crossed}$"
            ):
                self.snapshot(workflow(definition), name)
        longer_name = self.snapshot(workflow(through(f"{check}2")), "a path that only starts alike")[1]
        self.assertIn(f"{check}2/{base.ACTION_PATH}", longer_name)

    def test_a_copy_that_cannot_be_written_is_a_source_error(self) -> None:
        refused = {"a name of 300 characters": "L" * 300, "a path of 40,199 characters": "/".join(["D" * 200] * 200)}
        for name, prefix in refused.items():
            held = workflow(job(checkout(prefix), step(f"./{prefix}/.github/actions/sample")))
            projected, inputs = self.snapshot(held, name)
            analysis = Path(self.enterContext(tempfile.TemporaryDirectory()))
            unwritable = f"^lint input cannot be written: {prefix}/{base.ACTION_PATH}: "
            with self.subTest(name=name), self.assertRaisesRegex(lint.WorkflowSourceError, unwritable):
                lint._write_project(analysis, projected, inputs, 30)

    def test_a_copy_never_shares_a_directory_with_a_workflow(self) -> None:
        metadata = self.root / "workflows" / "action.yml"
        metadata.parent.mkdir()
        same_bytes = base.ACTION + "on: push\njobs:\n" + job(step(SAMPLE))
        metadata.write_text(same_bytes, encoding="utf-8", newline="\n")
        lint._git(self.root, "init", "--quiet")
        lint._git(self.root, "add", "--", "workflows")
        calling = workflow(job(checkout(".github"), step("./.github/workflows")))
        self.workflow.with_name("action.yml").write_text(same_bytes, encoding="utf-8", newline="\n")
        for name in ("a.yml", "z.yml"):
            caller = self.workflow.with_name(name)
            caller.write_text(calling, encoding="utf-8", newline="\n")
            with self.subTest(name=name), self.assertRaisesRegex(
                lint.WorkflowSourceError, f"{COLLISION}: .github/workflows$"
            ):
                lint.snapshot(self.root, base.commit(self.root, name))
            caller.unlink()


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

    def test_actionlint_reads_the_action_under_the_checkout_path(self) -> None:
        accepted = self.lint_with_input("known")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        rejected = self.lint_with_input("unknown")
        self.assertEqual(rejected.returncode, 2, rejected.stdout)
        output = (rejected.stderr or b"").decode("utf-8", "replace")
        self.assertIn("input \"unknown\"", output)
        self.assertIn("check.yml", output)


if __name__ == "__main__":
    unittest.main()
