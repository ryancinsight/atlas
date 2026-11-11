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
REFERENCE = "./nested-src/.github/actions/sample"
MISSING = "reference escapes or is missing from the checkout"
UNDEFINED = "action comes from a checkout the candidate does not define"
INVALID_PATH = "invalid same-repository path"
CANDIDATE_REFS = (
    None,
    "${{ github.sha }}",
    "${{github.event.pull_request.head.sha}}",
    "${{  github.event.pull_request.head.sha   ||github.sha }}",
)


def checkout(path: str | None = "nested-src", **options: str) -> str:
    entries = ({"path": path} if path is not None else {}) | options
    lines = "".join(f"          {name}: '{value}'\n" for name, value in entries.items())
    return f"      - uses: actions/checkout@{PIN}\n        with:\n{lines}"


def job(*steps: str, name: str = "build") -> str:
    return f"  {name}:\n    runs-on: custom-runner\n    steps:\n" + "".join(steps)


def workflow(*jobs: str) -> str:
    return "name: test\non: push\njobs:\n" + "".join(jobs)


def step(reference: str = REFERENCE) -> str:
    return f"      - uses: {reference}\n"


class CheckoutPrefixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, self.workflow, self.action = base.fixture(self)

    def project(self, source: str) -> list[Path]:
        return lint.project(source.encode(), self.workflow, self.root, "workflow")[1]

    def test_resolves_candidate_checkouts_to_the_candidate_action(self) -> None:
        for ref in CANDIDATE_REFS:
            options = {} if ref is None else {"ref": ref}
            with self.subTest(ref=ref):
                self.assertEqual(self.project(workflow(job(checkout(**options), step()))), [self.action])

    def test_latest_overlapping_checkout_governs(self) -> None:
        outer = checkout("nested-src", ref="main")
        inner = checkout("nested-src/inner")
        reference = "./nested-src/inner/.github/actions/sample"
        self.assertEqual(self.project(workflow(job(outer, inner, step(reference)))), [self.action])
        self.assertEqual(self.project(workflow(job(inner, outer, inner, step(reference)))), [self.action])
        replaced = checkout("nested-src/inner", ref="main")
        for name, steps in {
            "outer after inner": (inner, outer),
            "same path replaced": (inner, replaced),
        }.items():
            message = f"{UNDEFINED}: {reference!r}"
            with self.subTest(name=name), self.assertRaisesRegex(lint.WorkflowSourceError, message):
                self.project(workflow(job(*steps, step(reference))))

    def test_collects_action_metadata_under_the_checkout_path(self) -> None:
        self.workflow.write_text(workflow(job(checkout(), step())), encoding="utf-8", newline="\n")
        candidate = base.commit(self.root)
        projected, inputs = lint.snapshot(self.root, candidate)
        prefixed = f"nested-src/{base.ACTION_PATH}"
        self.assertEqual(set(inputs), {".github/workflows/check.yml", base.ACTION_PATH, prefixed})
        self.assertEqual(inputs[base.ACTION_PATH], base.ACTION.encode())
        self.assertEqual(inputs[prefixed], inputs[base.ACTION_PATH])
        self.assertEqual(projected[".github/workflows/check.yml"], inputs[".github/workflows/check.yml"])
        analysis = Path(self.enterContext(tempfile.TemporaryDirectory()))
        lint._write_project(analysis, projected, inputs, 30)
        self.assertEqual((analysis / prefixed).read_bytes(), base.ACTION.encode())

    def test_rejects_alias_that_replaces_a_different_candidate_input(self) -> None:
        shadow = self.root / ".github" / "actions" / "outer" / ".github" / "actions" / "sample" / "action.yml"
        shadow.parent.mkdir(parents=True)
        shadow.write_text(base.ACTION.replace("sample", "shadow"), encoding="utf-8", newline="\n")
        reference = "./.github/actions/outer/.github/actions/sample"
        outer = checkout(".github/actions/outer")
        orders = {
            "root reference first": workflow(job(step(reference), outer, step(reference))),
            "alias first": workflow(job(outer, step(reference), name="first"), job(step(reference), name="second")),
        }
        for name, source in orders.items():
            self.workflow.write_text(source, encoding="utf-8", newline="\n")
            candidate = base.commit(self.root, name)
            with self.subTest(name=name), self.assertRaisesRegex(
                lint.WorkflowSourceError,
                "lint input path has two different sources: .github/actions/outer/.github/actions/sample/action.yml",
            ):
                lint.snapshot(self.root, candidate)

    def test_names_the_written_reference_when_the_checkout_lacks_the_action(self) -> None:
        reference = "./nested-src/.github/actions/missing"
        with self.assertRaises(lint.WorkflowSourceError) as raised:
            self.project(workflow(job(checkout(), step(reference))))
        self.assertEqual(
            str(raised.exception),
            f"{MISSING}: './.github/actions/missing' (as {reference!r} under checkout 'nested-src')",
        )

    def test_rejects_checkouts_that_may_not_hold_the_candidate(self) -> None:
        cases = {
            "repository": checkout(repository="other/repository"),
            "repository with candidate ref": checkout(repository="other/repository", ref="${{ github.sha }}"),
            "branch ref": checkout(ref="main"),
            "other expression": checkout(ref="${{ github.ref }}"),
            "compound expression": checkout(ref="${{ github.sha }} ${{ github.ref }}"),
            "empty ref": checkout(ref=""),
        }
        for name, definition in cases.items():
            with self.subTest(name=name), self.assertRaisesRegex(
                lint.WorkflowSourceError, f"{UNDEFINED}: {REFERENCE!r}"
            ):
                self.project(workflow(job(definition, step())))

    def test_rejects_references_without_a_preceding_checkout_of_that_path(self) -> None:
        other_action = "      - uses: other/action@v1\n        with:\n          path: nested-src\n"
        cases = {
            "no checkout": job(step()),
            "other path": job(checkout("other-src"), step()),
            "before checkout": job(step(), checkout()),
            "other job": job(checkout(), name="first") + job(step(), name="second"),
            "not a checkout": job(other_action, step()),
        }
        for name, definition in cases.items():
            with self.subTest(name=name), self.assertRaisesRegex(
                lint.WorkflowSourceError, f"{MISSING}: {REFERENCE!r}"
            ):
                self.project(workflow(definition))

    def test_unusable_checkout_paths_define_no_prefix(self) -> None:
        cases = {
            "expression": ("${{ github.sha }}-src", "./${{ github.sha }}-src/.github/actions/sample", MISSING),
            "parent component before prefix": ("x/../nested-src", REFERENCE, MISSING),
            "parent component": ("a/../nested-src", "./a/../nested-src/.github/actions/sample", INVALID_PATH),
            "current component": ("nested-src/.", "./nested-src/./.github/actions/sample", INVALID_PATH),
            "trailing separator": ("nested-src/", "./nested-src//.github/actions/sample", INVALID_PATH),
            "absolute": ("/nested-src", ".//nested-src/.github/actions/sample", INVALID_PATH),
            "backslash": ("nested\\src", "./nested\\src/.github/actions/sample", "invalid same-repository reference"),
        }
        for name, (path, reference, message) in cases.items():
            with self.subTest(name=name), self.assertRaisesRegex(lint.WorkflowSourceError, message):
                self.project(workflow(job(checkout(path), step(reference))))

    def test_composite_actions_and_reusable_workflows_resolve_from_the_root(self) -> None:
        composite = (
            "runs:\n  using: composite\n  steps:\n"
            f"    - uses: actions/checkout@{PIN}\n      with:\n        path: nested-src\n"
            f"    - uses: {REFERENCE}\n"
        )
        with self.assertRaisesRegex(lint.WorkflowSourceError, MISSING):
            lint.project(composite.encode(), self.action, self.root, "action")
        reusable = "jobs:\n  call:\n    uses: ./nested-src/.github/workflows/check.yml\n"
        with self.assertRaisesRegex(lint.WorkflowSourceError, MISSING):
            self.project(reusable)


if __name__ == "__main__":
    unittest.main()
