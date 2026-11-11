import itertools
import os
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_workflow_lint as lint  # noqa: E402
import test_atlas_workflow_lint as base  # noqa: E402

PIN = "0" * 40
SAMPLE = "./.github/actions/sample"
REFERENCE = "./nested-src/.github/actions/sample"
MISSING = "reference escapes or is missing from the checkout"
UNDEFINED = "action comes from a checkout the candidate does not define"
COLLISION = "lint input path has two different sources"
FOREIGN = {"repository": "other/repository"}


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


def related(first: str, second: str) -> bool:
    return all(one == other for one, other in zip(first.casefold().split("/"), second.casefold().split("/")))


def governed(sequence: list[tuple[str | None, bool]], reference: str) -> str:
    """The required outcome: the latest checkout at or above the reference decides unless a later one may rewrite it."""
    for index in range(len(sequence) - 1, -1, -1):
        path, holds_candidate = sequence[index]
        if path is None or not f"{reference}/".startswith(f"./{path}/"):
            continue
        if any(later is None or related(later, path) for later, _ in sequence[index + 1 :]):
            break
        if not holds_candidate:
            return f"{UNDEFINED}: {reference!r}"
        inner = f"./{reference[len(path) + 3 :]}"
        return "accepted" if inner == SAMPLE else f"{MISSING}: {inner!r} (as {reference!r} under checkout {path!r})"
    return f"{MISSING}: {reference!r}"


class CheckoutPrefixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, self.workflow, self.action = base.fixture(self)

    def outcome(self, source: str) -> str:
        try:
            targets = lint.project(source.encode(), self.workflow, self.root, "workflow")[1]
        except lint.WorkflowSourceError as error:
            return str(error)
        self.assertEqual(targets, [self.action] * len(targets))
        return "accepted"

    def snapshot(self, source: str, message: str) -> tuple[dict[str, bytes], dict[str, bytes]]:
        self.workflow.write_text(source, encoding="utf-8", newline="\n")
        return lint.snapshot(self.root, base.commit(self.root, message))

    def test_candidate_checkouts_resolve_to_the_candidate_action(self) -> None:
        spellings = ("${{ github.sha }}", "${{github.event.pull_request.head.sha}}")
        for ref in (None, *spellings, "${{  github.event.pull_request.head.sha   ||github.sha }}"):
            options = {} if ref is None else {"ref": ref, "fetch-depth": "0"}
            with self.subTest(ref=ref):
                self.assertEqual(self.outcome(workflow(job(checkout(**options), step()))), "accepted")
        self.assertEqual(self.outcome(workflow(job(checkout(uses="Actions/Checkout"), step()))), "accepted")

    def test_every_order_of_checkouts_follows_the_rule(self) -> None:
        action_directory = "nested-src/.github/actions/sample"
        shapes = {
            checkout(): ("nested-src", True),
            checkout(ref="main"): ("nested-src", False),
            checkout("nested-src/inner"): ("nested-src/inner", True),
            checkout("nested-src/inner", **FOREIGN): ("nested-src/inner", False),
            checkout(action_directory, **FOREIGN): (action_directory, False),
            checkout("Nested-Src", **FOREIGN): ("Nested-Src", False),
            checkout("other-src", **FOREIGN): ("other-src", False),
            checkout(None, **FOREIGN): (None, False),
            checkout("./nested-src", **FOREIGN): (None, False),
        }
        # After the deciding checkout only unrelated known paths may follow: one such shape for the first
        # reference and two for the second, so lengths one to three give 102 + 115 acceptances.
        accepted = 0
        for length, reference in itertools.product(range(4), (REFERENCE, "./nested-src/inner/.github/actions/sample")):
            for steps in itertools.product(shapes, repeat=length):
                expected = governed([shapes[text] for text in steps], reference)
                accepted += expected == "accepted"
                self.assertEqual(self.outcome(workflow(job(*steps, step(reference)))), expected, (steps, reference))
        self.assertEqual(accepted, 217)

    def test_unreadable_checkouts_void_the_prefix_before_them(self) -> None:
        raw = f"      - uses: actions/checkout@{PIN}\n"
        foreign = "          repository: other/repository\n"
        cases = {
            "expression path": checkout("${{ github.sha }}-src", **FOREIGN),
            "parent component": checkout("x/../nested-src", **FOREIGN),
            "trailing separator": checkout("nested-src/", **FOREIGN),
            "backslash": checkout("nested\\src", **FOREIGN),
            "integer path": raw + f"        with:\n          path: 7\n{foreign}",
            "no inputs": raw,
            "repeated block": raw + f"        with:\n          path: other-src\n        with:\n{foreign}",
            "repeated input": raw + f"        with:\n          path: other-src\n          Path: nested-src\n{foreign}",
            "merge key": raw + "        with:\n          <<: {repository: o/r}\n          path: other-src\n",
        }
        for name, unreadable in cases.items():
            with self.subTest(name=name):
                voided = self.outcome(workflow(job(checkout(), unreadable, step())))
                self.assertEqual(voided, f"{MISSING}: {REFERENCE!r}")
                self.assertEqual(self.outcome(workflow(job(unreadable, step(SAMPLE)))), "accepted")

    def test_checkouts_that_may_not_hold_the_candidate_are_rejected(self) -> None:
        cases = {
            "repository": FOREIGN,
            "repository in another case": {"Repository": "other/repository", "ref": "${{ github.sha }}"},
            "server": {"github-server-url": "https://example.invalid"},
            "branch ref": {"ref": "main"},
            "ref in another case": {"REF": "main"},
            "other expression": {"ref": "${{ github.ref }}"},
            "two expressions": {"ref": "${{ github.sha }} ${{ github.ref }}"},
            "split name": {"ref": "${{ git hub.sha }}"},
            "padded expression": {"ref": " ${{ github.sha }} "},
        }
        for name, options in cases.items():
            with self.subTest(name=name):
                rejected = self.outcome(workflow(job(checkout(**options), step())))
                self.assertEqual(rejected, f"{UNDEFINED}: {REFERENCE!r}")
        at_root = "./nested-src"
        self.assertEqual(self.outcome(workflow(job(checkout(**FOREIGN), step(at_root)))), f"{UNDEFINED}: {at_root!r}")
        self.assertEqual(
            self.outcome(workflow(job(checkout(), step(at_root)))),
            f"invalid same-repository path: './' (as {at_root!r} under checkout 'nested-src')",
        )
        shared = job("      - &shared\n        uses: " + REFERENCE + "\n", checkout(), "      - *shared\n")
        self.assertEqual(self.outcome(workflow(shared)), f"{UNDEFINED}: {REFERENCE!r}")

    def test_references_outside_a_preceding_checkout_keep_the_root_reading(self) -> None:
        other_action = "      - uses: other/action@v1\n        with:\n          path: nested-src\n"
        repeated = "      - uses: " + SAMPLE + "\n        with: {}\n        with: {}\n"
        cases = {
            "no checkout": (job(step()), f"{MISSING}: {REFERENCE!r}"),
            "longer name": (job(checkout("nested"), step()), f"{MISSING}: {REFERENCE!r}"),
            "before checkout": (job(step(), checkout()), f"{MISSING}: {REFERENCE!r}"),
            "other job": (job(checkout(), name="first") + job(step(), name="second"), f"{MISSING}: {REFERENCE!r}"),
            "not a checkout": (job(other_action, step()), f"{MISSING}: {REFERENCE!r}"),
            "repeated block on another step": (job(checkout(), repeated), "accepted"),
        }
        for name, (definition, expected) in cases.items():
            with self.subTest(name=name):
                self.assertEqual(self.outcome(workflow(definition)), expected)
        composite = f"runs:\n  using: composite\n  steps:\n    - uses: actions/checkout@{PIN}\n"
        composite += f"      with:\n        path: nested-src\n    - uses: {REFERENCE}\n"
        with self.assertRaisesRegex(lint.WorkflowSourceError, MISSING):
            lint.project(composite.encode(), self.action, self.root, "action")
        reusable = "jobs:\n  call:\n    uses: ./nested-src/.github/workflows/check.yml\n"
        self.assertEqual(self.outcome(reusable), f"{MISSING}: './nested-src/.github/workflows/check.yml'")

    def test_action_metadata_is_copied_under_the_checkout_path(self) -> None:
        projected, inputs = self.snapshot(workflow(job(checkout(), step())), "copy")
        prefixed = f"nested-src/{base.ACTION_PATH}"
        self.assertEqual(set(inputs), {".github/workflows/check.yml", base.ACTION_PATH, prefixed})
        self.assertEqual(inputs[base.ACTION_PATH], base.ACTION.encode())
        self.assertEqual(inputs[prefixed], inputs[base.ACTION_PATH])
        self.assertEqual(projected[".github/workflows/check.yml"], inputs[".github/workflows/check.yml"])
        analysis = Path(self.enterContext(tempfile.TemporaryDirectory()))
        lint._write_project(analysis, projected, inputs, 30)
        self.assertEqual((analysis / prefixed).read_bytes(), base.ACTION.encode())

    def test_a_copy_never_shares_a_path_with_different_candidate_bytes(self) -> None:
        outer = ".github/actions/outer"
        shadow = self.root.joinpath(*outer.split("/"), ".github", "actions", "sample", "action.yml")
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
                lint.WorkflowSourceError, f"{COLLISION}: {outer}/.github/actions/sample/action.yml"
            ):
                self.snapshot(workflow(definition), name)

    def test_a_copy_never_shares_a_path_with_a_workflow(self) -> None:
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
                lint.WorkflowSourceError, f"{COLLISION}: .github/workflows/action.yml"
            ):
                lint.snapshot(self.root, base.commit(self.root, name))
            caller.unlink()


@unittest.skipUnless(
    all(os.environ.get(name) for name in ("ACTIONLINT", "SHELLCHECK", "PYFLAKES")),
    "native workflow analyzers are not configured",
)
class NativeCheckoutPrefixTests(unittest.TestCase):
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
