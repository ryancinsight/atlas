import itertools
import posixpath
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow_checkout_prefix import Checkout, governing  # noqa: E402

PIN = "0" * 40
SAMPLE = "./.github/actions/sample"
REFERENCE = "./nested-src/.github/actions/sample"
FOREIGN = {"repository": "other/repository"}
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
        spellings = ("${{ github.sha }}", "${{github.event.pull_request.head.sha}}")
        for ref in (None, *spellings, "${{  github.event.pull_request.head.sha   ||github.sha }}"):
            options = {} if ref is None else {"ref": ref, "fetch-depth": "0", "persist-credentials": "false"}
            with self.subTest(ref=ref):
                self.assertEqual(outcomes(workflow(job(checkout(**options), step()))), [HELD])
        named = checkout(uses="Actions/Checkout") + "        name: Checkout\n        id: source\n"
        self.assertEqual(outcomes(workflow(job(named, step() + "        with: {}\n"))), [HELD])
        self.assertEqual(outcomes(workflow(job(checkout(), step("./nested-src")))), [HELD])
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
        self.assertEqual(outcomes("jobs:\n  call:\n    uses: ./nested-src/.github/workflows/check.yml\n"), [])


if __name__ == "__main__":
    unittest.main()
