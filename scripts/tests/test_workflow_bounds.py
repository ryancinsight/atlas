"""Every sourced `timeout-minutes` carries a derivation the test recomputes.

A bare `timeout-minutes` reads the same whether it is a multiple of a measurement or a guess
about a cold runner. A bound is therefore explained by one comment line directly above it, at
the bound's own indent, in this form:

    # bound: <seconds> s (<source>) -> <minutes> min = <ratio>x

`<minutes>` is the YAML value. `<seconds>` is one integer or a sum of products of integers
(`20 * 2 + 60 * 4`). `<source>` is `run <id>`, a hosted run in which the job or step took that
long, or a `scripts/` path whose deadlines the arithmetic adds up. `<ratio>` is
`<minutes> * 60 / <seconds>` truncated to three decimals, and the bound must not be below the
duration it explains. Three decimals pin a figure to the second for every figure here, so moving the bound,
the figure or the ratio without the others fails.

A measured figure is the longest duration of that job or step among the runs of the workflow
that runs it on `main`, among the ten latest completed ones when read, in which the job
concluded success (a step's job counts, whatever else failed in other jobs), read on
2026-11-24 from
`gh run list --workflow <file> --branch main --limit 10` and
`gh api repos/ryancinsight/atlas/actions/runs/<id>/jobs` (`started_at` to `completed_at`,
whole seconds). A reusable workflow's jobs are read from its caller's runs, or from its own standalone runs
when it has them. A ten-run maximum is a sample, not a ceiling. This test checks
the arithmetic and that a `scripts/` source exists; it cannot reread a run.

`REMAINING` maps each workflow whose bounds have no hosted run to source here to its bound
values in file order: each is a reusable workflow (`workflow_call` only) with no succeeded run
in ryancinsight/atlas. Calls from member repositories were not sampled. Those values stay as
recorded until a run sources them, at which point the workflow leaves the mapping.
"""

from __future__ import annotations

import re
import unittest
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
BOUND = re.compile(r"^( +)timeout-minutes: (\d+)$")
QUOTED = re.compile(r"(\d+) min\b")
JOB_KEY = re.compile(r"^  [a-z0-9][a-z0-9-]*:")
DERIVATION = re.compile(
    r"bound: (?P<seconds>\d+(?: [*+] \d+)*) s "
    r"\((?P<source>run \d{8,}|scripts/[A-Za-z0-9_./-]+)\) "
    r"-> (?P<minutes>\d+) min = (?P<ratio>\d+\.\d{3})x(?!\d)")
REMAINING = {
    "adr-index-guard.yml": (5,),
    "artifact-budget.yml": (5,),
    "book-pages.yml": (25, 10),
    "conformance-guard.yml": (5,),
    "crates-publish-pending.yml": (45, 30),
    "crates-publish.yml": (30, 30),
    "lockfile-guard.yml": (5,),
    "python-wheels.yml": (30, 30, 30, 30, 30),
    "semver-gate.yml": (30, 25, 10, 20),
}


@dataclass(frozen=True)
class Bound:
    """One `timeout-minutes` line: where it is, what it is, and what explains it."""

    workflow: str
    role: str
    line: int
    value: int
    comment: str

    @property
    def label(self) -> str:
        return f"{self.workflow}:{self.line} ({self.role})"


def comment_above(lines: list[str], index: int, indent: int) -> str:
    """The comment block directly above `lines[index]` at `indent`, read as one line."""
    collected = []
    while index > 0 and lines[index - 1].startswith(" " * indent + "#"):
        index -= 1
        collected.append(lines[index].strip().lstrip("#").strip())
    return " ".join(reversed(collected))


def job_spans(lines: list[str]) -> list[tuple[str, int, int]]:
    """Each job's name and its half-open line range."""
    spans = []
    starts = [i for i, line in enumerate(lines) if JOB_KEY.fullmatch(line)]
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        spans.append((lines[start].strip().rstrip(":"), start, end))
    return spans


def job_bounds(path: Path) -> dict[str, bool]:
    """Which jobs YAML says set a job-level bound."""
    jobs = yaml.safe_load(path.read_text(encoding="utf-8")).get("jobs") or {}
    return {name: isinstance(job, dict) and "timeout-minutes" in job
            for name, job in jobs.items()}


def bounds(path: Path) -> list[Bound]:
    """Every bound in the file, each labelled by whether it is its job's or a step's."""
    lines = path.read_text(encoding="utf-8").splitlines()
    declared = job_bounds(path)
    found = []
    for job, start, end in job_spans(lines):
        matches = [(i, match) for i in range(start, end)
                   if (match := BOUND.match(lines[i]))]
        if not matches:
            continue
        job_index = min(matches, key=lambda pair: len(pair[1].group(1)))[0]
        for index, match in matches:
            role = "job" if declared.get(job) and index == job_index else "step"
            found.append(Bound(path.name, role, index + 1, int(match.group(2)),
                               comment_above(lines, index, len(match.group(1)))))
    return found


def steps_fit_inside_jobs(path: Path) -> list[tuple[str, int, int]]:
    """Per job that sets a bound, the sum of its step bounds against its own."""
    lines = path.read_text(encoding="utf-8").splitlines()
    declared = job_bounds(path)
    reading = []
    for job, start, end in job_spans(lines):
        matches = [(i, int(match.group(2)), len(match.group(1)))
                   for i in range(start, end) if (match := BOUND.match(lines[i]))]
        if not matches or not declared.get(job):
            continue
        job_index = min(matches, key=lambda entry: entry[2])[0]
        steps = sum(value for index, value, _ in matches if index != job_index)
        job_bound = next(value for index, value, _ in matches if index == job_index)
        reading.append((f"{path.name}:{job}", steps, job_bound))
    return reading


def quoted_mismatch(bound: Bound) -> list[int]:
    """The numbers a comment quotes as minutes, when the bound's own is not among them."""
    quoted = [int(number) for number in QUOTED.findall(bound.comment)]
    return quoted if quoted and bound.value not in quoted else []


def seconds_of(expression: str) -> int:
    """The value of a sum of products of integers, as written in a derivation."""
    total = 0
    for term in expression.split(" + "):
        product = 1
        for factor in term.split(" * "):
            product *= int(factor)
        total += product
    return total


def ratio_text(minutes: int, seconds: int) -> str:
    """`minutes * 60 / seconds` truncated to three decimals, without float rounding."""
    thousandths = minutes * 60000 // seconds
    return f"{thousandths // 1000}.{thousandths % 1000:03d}"


def derivation_faults(bound: Bound, root: Path = ROOT) -> list[str]:
    """Why the bound's comment does not derive it, or an empty list when it does."""
    found = list(DERIVATION.finditer(bound.comment))
    if len(found) != 1:
        return [f"needs exactly one `bound: <s> s (<source>) -> <n> min = <ratio>x`, found {len(found)}"]
    note = found[0]
    seconds = seconds_of(note["seconds"])
    faults = []
    if int(note["minutes"]) != bound.value:
        faults.append(f"derives {note['minutes']} min, YAML sets {bound.value}")
    if seconds <= 0 or bound.value * 60 < seconds:
        faults.append(f"{bound.value} min is below the {seconds} s it explains")
    elif note["ratio"] != ratio_text(bound.value, seconds):
        faults.append(f"ratio {note['ratio']}x, recomputed {ratio_text(bound.value, seconds)}x")
    source = note["source"]
    if source.startswith("scripts/") and not (root / source).is_file():
        faults.append(f"{source} does not exist")
    return faults


def cases() -> list[Bound]:
    return [bound for path in WORKFLOWS for bound in bounds(path)]


def yaml_bound_count(path: Path) -> int:
    """How many bounds YAML sees: one per job key and one per step that sets one."""
    jobs = yaml.safe_load(path.read_text(encoding="utf-8")).get("jobs") or {}
    total = 0
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        total += 1 if "timeout-minutes" in job else 0
        total += sum(1 for step in job.get("steps") or []
                     if isinstance(step, dict) and "timeout-minutes" in step)
    return total


class BoundDerivationTests(unittest.TestCase):
    def test_every_sourced_bound_is_derived(self) -> None:
        for bound in cases():
            if bound.workflow in REMAINING:
                continue
            with self.subTest(bound.label):
                self.assertEqual(derivation_faults(bound), [], f"{bound.label} sets {bound.value}")

    def test_the_remaining_list_names_only_workflows_still_unsourced(self) -> None:
        names = {path.name for path in WORKFLOWS}
        self.assertLessEqual(set(REMAINING), names)
        for name in sorted(REMAINING):
            with self.subTest(name):
                undone = [bound for bound in cases() if bound.workflow == name
                          and derivation_faults(bound)]
                self.assertTrue(undone, f"{name} is fully derived: remove it from REMAINING")

    def test_an_unsourced_workflow_keeps_the_bounds_recorded_for_it(self) -> None:
        for name, recorded in sorted(REMAINING.items()):
            with self.subTest(name):
                values = tuple(bound.value for bound in cases() if bound.workflow == name)
                self.assertEqual(values, recorded)

    def test_a_derivation_that_quotes_a_bound_quotes_its_own(self) -> None:
        for bound in cases():
            with self.subTest(bound.label):
                self.assertEqual(quoted_mismatch(bound), [],
                                 f"{bound.label} sets {bound.value}, comment quotes {bound.comment}")

    def test_the_sweep_covers_every_bound_yaml_sees(self) -> None:
        expected = sum(yaml_bound_count(path) for path in WORKFLOWS)
        self.assertEqual(len(cases()), expected)
        self.assertGreater(expected, 0)

    def test_every_step_bound_fits_inside_its_job_bound(self) -> None:
        for path in WORKFLOWS:
            for job, steps, job_bound in steps_fit_inside_jobs(path):
                with self.subTest(job):
                    self.assertLessEqual(steps, job_bound,
                                         f"{job}: step bounds sum to {steps}, job bound {job_bound}")


class RuleTests(unittest.TestCase):
    """The sweep's rules, on fixtures rather than on the live workflows."""

    def bound(self, value: int, comment: str) -> Bound:
        return Bound("x.yml", "job", 1, value, comment)

    def test_a_bound_without_a_comment_has_none(self) -> None:
        self.assertEqual(comment_above(["        timeout-minutes: 3"], 0, 8), "")

    def test_a_comment_at_another_indent_is_not_this_bound(self) -> None:
        lines = ["    # 5 min of job overhead", "        timeout-minutes: 3"]
        self.assertEqual(comment_above(lines, 1, 8), "")

    def test_a_derivation_that_adds_up_has_no_fault(self) -> None:
        note = "Hosted maximum. bound: 181 s (run 45274225788) -> 10 min = 3.314x"
        self.assertEqual(derivation_faults(self.bound(10, note)), [])

    def test_a_sum_of_products_is_evaluated(self) -> None:
        self.assertEqual(seconds_of("20 * 2 + 60 * 4"), 280)
        self.assertEqual(ratio_text(5, 280), "1.071")

    def test_a_moved_bound_with_its_comment_untouched_fails(self) -> None:
        note = "bound: 181 s (run 45274225788) -> 10 min = 3.314x"
        self.assertEqual(derivation_faults(self.bound(20, note)),
                         ["derives 10 min, YAML sets 20", "ratio 3.314x, recomputed 6.629x"])

    def test_a_moved_bound_and_minutes_with_the_old_figure_fails_on_the_ratio(self) -> None:
        note = "bound: 181 s (run 45274225788) -> 20 min = 3.314x"
        self.assertEqual(derivation_faults(self.bound(20, note)), ["ratio 3.314x, recomputed 6.629x"])

    def test_a_figure_moved_by_one_second_with_its_ratio_text_fails(self) -> None:
        plain = re.compile(r"bound: ([0-9]+) s")
        checked = 0
        for bound in cases():
            found = plain.search(bound.comment)
            if bound.workflow in REMAINING or not found or "run " not in bound.comment:
                continue
            for step in (-1, 1):
                moved = plain.sub(f"bound: {int(found[1]) + step} s", bound.comment)
                with self.subTest(f"{bound.label} {step:+d} s"):
                    self.assertNotEqual(
                        derivation_faults(Bound(bound.workflow, bound.role, bound.line,
                                                bound.value, moved)), [])
            checked += 1
        self.assertGreater(checked, 10)

    def test_a_placeholder_is_not_a_derivation(self) -> None:
        for text in ("TODO", "", "bound: TODO", "bound: 181 s -> 10 min = 3.314x",
                     "10 min is the stack's floor"):
            with self.subTest(text):
                self.assertEqual(len(derivation_faults(self.bound(10, text))), 1)

    def test_a_bound_below_the_duration_it_explains_fails(self) -> None:
        note = "bound: 700 s (run 45274225788) -> 10 min = 0.857x"
        self.assertEqual(derivation_faults(self.bound(10, note)),
                         ["10 min is below the 700 s it explains"])

    def test_a_script_source_must_exist(self) -> None:
        note = "bound: 60 s (scripts/no-such-script.py) -> 5 min = 5.000x"
        self.assertEqual(derivation_faults(self.bound(5, note)),
                         ["scripts/no-such-script.py does not exist"])

    def test_a_second_derivation_in_one_comment_fails(self) -> None:
        note = ("bound: 181 s (run 45274225788) -> 10 min = 3.314x "
                "bound: 90 s (run 45274225788) -> 10 min = 6.666x")
        self.assertEqual(len(derivation_faults(self.bound(10, note))), 1)

    def test_a_comment_that_quotes_another_bound_disagrees(self) -> None:
        self.assertEqual(quoted_mismatch(self.bound(45, "30 min is the cold build")), [30])

    def test_a_comment_that_quotes_only_its_own_bound_agrees(self) -> None:
        self.assertEqual(quoted_mismatch(self.bound(30, "30 min is 2x the 12.5 measured")), [])


if __name__ == "__main__":
    unittest.main()
