"""Every timeout-minutes in the stack's workflows carries a written derivation.

A bare `timeout-minutes` is a number nobody can re-derive: it reads the same whether it is
five times a measurement or a guess about a cold runner. Every job and every step that sets
one therefore has a comment directly above it, at the bound's own indent, saying what the
run does and where the number comes from; a comment that quotes a bound quotes that bound's
own value. A bound moved without its derivation fails here instead of drifting, and a step
comment cannot stand in for its job's bound or the reverse.
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
    def test_every_bound_has_a_derivation_comment(self) -> None:
        for bound in cases():
            with self.subTest(bound.label):
                self.assertTrue(bound.comment, f"{bound.label} sets {bound.value} with no derivation")

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

    def test_a_bound_without_a_comment_has_none(self) -> None:
        self.assertEqual(comment_above(["        timeout-minutes: 3"], 0, 8), "")

    def test_a_comment_at_another_indent_is_not_this_bound(self) -> None:
        lines = ["    # 5 min of job overhead", "        timeout-minutes: 3"]
        self.assertEqual(comment_above(lines, 1, 8), "")

    def test_a_moved_bound_and_its_comment_disagree(self) -> None:
        bound = Bound("x.yml", "job", 1, 45, "30 min is the cold build")
        self.assertEqual(quoted_mismatch(bound), [30])

    def test_a_moved_bound_whose_comment_quotes_only_it_agrees(self) -> None:
        bound = Bound("x.yml", "job", 1, 30, "30 min is 2x the 12.5 measured")
        self.assertEqual(quoted_mismatch(bound), [])

    def test_a_comment_that_quotes_no_number_needs_none(self) -> None:
        self.assertEqual(quoted_mismatch(Bound("x.yml", "job", 1, 45, "covers the queue")), [])


if __name__ == "__main__":
    unittest.main()
