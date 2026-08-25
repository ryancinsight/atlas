#!/usr/bin/env python3
"""Audit executable mdBook sample gates at committed Atlas gitlinks.

The root repository owns the inventory check, while each provider owns its
book workflow.  This audit reads both files from the committed submodule
revision, so a dirty or differently checked-out provider cannot change the
result.  It distinguishes the shared reusable-workflow input from a provider
workflow that invokes ``mdbook test`` directly (Gaia's current contract).

Members with neither a book manifest nor a book workflow are outside the
book-bearing inventory. A member with only one side is reported as an
incomplete inventory entry. Workflow wiring is not sufficient evidence: a
book with no executable Rust fence in its ``SUMMARY.md`` sources is reported
 as vacuous coverage. The inventory and residual counts are derived from the
 committed gitlinks.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import posixpath
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_stack import ROOT, registered_member_names  # noqa: E402


BOOK_MANIFEST = "docs/book/book.toml"
BOOK_SUMMARY = "docs/book/SUMMARY.md"
BOOK_WORKFLOW = ".github/workflows/book-pages.yml"
SHARED_INPUT_RE = re.compile(r"^\s*mdbook-test\s*:\s*true\s*(?:#.*)?$")
CANONICAL_WORKFLOW_RE = re.compile(
    r"^\s*uses:\s*ryancinsight/atlas/\.github/workflows/book-pages\.yml@"
    r"[0-9a-f]{40}\s*(?:#.*)?$",
    re.IGNORECASE,
)
DIRECT_COMMAND_RE = re.compile(
    r"(?:^|(?:&&|\|\||[;|])\s*|(?:if|then)\s+)"
    r"(?:!\s*)?(?:command\s+)?mdbook\s+test(?:\s|$)"
)
RUST_FENCE_RE = re.compile(r"^\s*```(?:rust|rs)(?P<attributes>(?:,[^\s]+)*)\s*$")
SUMMARY_LINK_RE = re.compile(r"\]\((?P<target>[^)#]+)(?:#[^)]*)?\)")
IMAGE_LINK_RE = re.compile(
    r"!\[[^\]]*\]\((?P<target>[^)\s]+)(?:\s+['\"][^)]*['\"])?\)"
)
RUN_RE = re.compile(r"^(?P<indent>\s*)(?:-\s+)?run:\s*(?P<body>.*)$")


@dataclass(frozen=True)
class BookGate:
    """Evidence for one committed provider book inventory entry."""

    member: str
    gitlink: str
    book_manifest: bool
    workflow: bool
    gate: str
    reason: str
    rust_fences: int = 0
    executable_rust_fences: int = 0
    missing_figures: tuple[str, ...] = ()


@dataclass(frozen=True)
class GitRead:
    """Result of reading one path from a committed provider revision."""

    text: str | None
    missing: bool = False
    error: str | None = None


class AuditReadError(RuntimeError):
    """Raised when committed provider evidence cannot be read."""


def _git(*args: str, cwd: Path = ROOT) -> tuple[int, str, str]:
    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return process.returncode, process.stdout, process.stderr


def _gitlink(member: str) -> str | None:
    code, output, _ = _git("ls-tree", "HEAD", "--", f"repos/{member}")
    if code != 0:
        return None
    fields = output.strip().split()
    if len(fields) >= 3 and fields[1] == "commit":
        return fields[2]
    return None


def _at_gitlink(member: str, gitlink: str, path: str) -> GitRead:
    provider = ROOT / "repos" / member
    if not provider.exists():
        return GitRead(None, error=f"provider checkout is missing: {provider}")
    code, output, stderr = _git(
        "-C", str(provider), "show", f"{gitlink}:{path}"
    )
    if code == 0:
        return GitRead(output)
    lowered = stderr.lower()
    if "does not exist in" in lowered or "exists on disk, but not" in lowered:
        return GitRead(None, missing=True)
    detail = stderr.strip() or f"git show exited with status {code}"
    return GitRead(None, error=f"unable to read {path}: {detail}")


def _is_direct_run(line: str) -> bool:
    command = line.strip()
    if command.startswith("-"):
        command = command[1:].lstrip()
    return not command.startswith("#") and DIRECT_COMMAND_RE.search(command) is not None


def _direct_command(workflow: str) -> bool:
    """Return whether a ``run`` field executes ``mdbook test``.

    Searching only run fields avoids false positives from job names, comments,
    and documentation strings elsewhere in a workflow.
    """
    block_indent: int | None = None
    for raw_line in workflow.splitlines():
        match = RUN_RE.match(raw_line)
        if match:
            block_indent = None
            body = match.group("body").strip()
            if body in {"|", ">", "|-", ">-", "|+", ">+"}:
                block_indent = len(match.group("indent"))
                continue
            if _is_direct_run(body):
                return True
            continue

        if block_indent is not None:
            if not raw_line.strip():
                continue
            indent = len(raw_line) - len(raw_line.lstrip())
            if indent <= block_indent:
                block_indent = None
            elif _is_direct_run(raw_line):
                return True
    return False


def classify_workflow(workflow: str) -> tuple[str, str]:
    """Classify a provider workflow as shared, direct, or ungated."""
    canonical = any(CANONICAL_WORKFLOW_RE.match(line) for line in workflow.splitlines())
    shared_input = any(SHARED_INPUT_RE.match(line) for line in workflow.splitlines())
    if canonical and shared_input:
        return "shared-input", "mdbook-test: true"
    if shared_input and not canonical:
        return "none", "mdbook-test: true without the canonical Atlas workflow"
    if _direct_command(workflow):
        return "direct-command", "run field invokes mdbook test"
    return "none", "no executable mdbook test gate"


def classify_coverage(
    gate: str, reason: str, executable_rust_fences: int
) -> tuple[str, str]:
    """Reject workflow gates whose book has no executable Rust sample."""
    if gate in {"shared-input", "direct-command"} and executable_rust_fences == 0:
        return (
            f"vacuous-{gate}",
            f"{reason}; no executable Rust book fence",
        )
    return gate, reason


def _summary_sources(summary: str) -> tuple[str, ...]:
    """Return Markdown sources rendered by a book's ``SUMMARY.md``."""
    sources = {BOOK_SUMMARY}
    for match in SUMMARY_LINK_RE.finditer(summary):
        target = match.group("target").strip()
        if not target or target.startswith(("#", "/")) or target.lower().startswith(
            ("http://", "https://", "mailto:")
        ):
            continue
        source = posixpath.normpath(posixpath.join("docs/book", target))
        if source.startswith("docs/book/") and source.endswith(".md"):
            sources.add(source)
    return tuple(sorted(sources))


def _book_fence_counts(member: str, gitlink: str, summary: str) -> tuple[int, int]:
    """Count executable Rust fences in rendered book sources."""
    sources = set(_summary_sources(summary))
    if not sources:
        return 0, 0
    code, output, _ = _git(
        "-C",
        str(ROOT / "repos" / member),
        "grep",
        "-I",
        "-n",
        "-E",
        r"^[[:space:]]*```(rust|rs)(,[^[:space:]]+)*[[:space:]]*$",
        gitlink,
        "--",
        "docs/book",
    )
    if code not in {0, 1}:
        detail = "git grep failed while reading committed book sources"
        raise AuditReadError(detail)

    rust_fences = 0
    executable = 0
    for line in output.splitlines():
        _, separator, record = line.partition(":")
        if separator == "":
            continue
        path, separator, record = record.partition(":")
        if separator == "" or path not in sources:
            continue
        _, separator, content = record.partition(":")
        if separator == "":
            continue
        match = RUST_FENCE_RE.match(content)
        if match is None:
            continue
        rust_fences += 1
        attributes = {
            value.strip().lower()
            for value in match.group("attributes").lstrip(",").split(",")
            if value.strip()
        }
        if not attributes.intersection({"ignore", "no_run"}):
            executable += 1
    return rust_fences, executable


def _book_figure_gaps(
    member: str, gitlink: str, sources: tuple[str, ...]
) -> tuple[str, ...]:
    """Return rendered-book image targets absent from the committed tree."""
    if not sources:
        return ()
    code, output, _ = _git(
        "-C",
        str(ROOT / "repos" / member),
        "grep",
        "-I",
        "-n",
        "-E",
        r"!\[[^]]*\]\([^)]+\)",
        gitlink,
        "--",
        "docs/book",
    )
    if code not in {0, 1}:
        raise AuditReadError(
            "git grep failed while reading committed book figures"
        )

    source_set = set(sources)
    missing: set[str] = set()
    for line in output.splitlines():
        _, separator, record = line.partition(":")
        if separator == "":
            continue
        path, separator, content = record.partition(":")
        if separator == "" or path not in source_set:
            continue
        for match in IMAGE_LINK_RE.finditer(content):
            target = match.group("target").split("#", 1)[0].strip()
            if not target or target.startswith(("#", "/")) or target.lower().startswith(
                ("http://", "https://", "mailto:", "data:")
            ):
                continue
            resolved = posixpath.normpath(
                posixpath.join(posixpath.dirname(path), target)
            )
            if not resolved.startswith("docs/book/"):
                continue
            read = _at_gitlink(member, gitlink, resolved)
            if read.error is not None:
                raise AuditReadError(read.error)
            if read.missing:
                missing.add(resolved)
    return tuple(sorted(missing))


def audit() -> list[BookGate]:
    """Read and classify every member participating in the book inventory."""
    results: list[BookGate] = []
    for member in sorted(registered_member_names()):
        gitlink = _gitlink(member)
        if gitlink is None:
            continue
        manifest_read = _at_gitlink(member, gitlink, BOOK_MANIFEST)
        if manifest_read.error is not None:
            results.append(
                BookGate(
                    member,
                    gitlink,
                    False,
                    False,
                    "invalid",
                    manifest_read.error,
                )
            )
            continue
        workflow_read = _at_gitlink(member, gitlink, BOOK_WORKFLOW)
        if workflow_read.error is not None:
            results.append(
                BookGate(
                    member,
                    gitlink,
                    manifest_read.text is not None,
                    False,
                    "invalid",
                    workflow_read.error,
                )
            )
            continue
        manifest = manifest_read.text
        workflow = workflow_read.text
        if manifest is None and workflow is None:
            continue
        if manifest is None or workflow is None:
            missing = BOOK_MANIFEST if manifest is None else BOOK_WORKFLOW
            results.append(
                BookGate(
                    member,
                    gitlink,
                    manifest is not None,
                    workflow is not None,
                    "invalid",
                    f"missing {missing}",
                )
            )
            continue
        summary_read = _at_gitlink(member, gitlink, BOOK_SUMMARY)
        if summary_read.error is not None:
            results.append(
                BookGate(
                    member,
                    gitlink,
                    True,
                    True,
                    "invalid",
                    summary_read.error,
                )
            )
            continue
        if summary_read.missing:
            results.append(
                BookGate(
                    member,
                    gitlink,
                    True,
                    True,
                    "invalid",
                    f"missing {BOOK_SUMMARY}",
                )
            )
            continue
        try:
            rust_fences, executable = _book_fence_counts(
                member, gitlink, summary_read.text or ""
            )
            missing_figures = _book_figure_gaps(
                member, gitlink, _summary_sources(summary_read.text or "")
            )
        except AuditReadError as error:
            results.append(
                BookGate(member, gitlink, True, True, "invalid", str(error))
            )
            continue
        gate, reason = classify_coverage(
            *classify_workflow(workflow), executable
        )
        if missing_figures:
            reason = (
                f"{reason}; {len(missing_figures)} referenced figure(s) missing"
            )
        results.append(
            BookGate(
                member,
                gitlink,
                True,
                True,
                gate,
                reason,
                rust_fences,
                executable,
                missing_figures,
            )
        )
    return results


def _print_text(results: list[BookGate]) -> None:
    for item in results:
        print(f"{item.member}: {item.gate} ({item.reason}) [{item.gitlink[:12]}]")
    counts: dict[str, int] = {}
    for item in results:
        counts[item.gate] = counts.get(item.gate, 0) + 1
    print(
        "book-gate-audit: "
        f"{len(results)} inventory entries; "
        f"shared={counts.get('shared-input', 0)}, "
        f"direct={counts.get('direct-command', 0)}, "
        f"vacuous={sum(value for key, value in counts.items() if key.startswith('vacuous-'))}, "
        f"missing-or-invalid={sum(value for key, value in counts.items() if key not in {'shared-input', 'direct-command'})}, "
        f"missing-figures={sum(bool(item.missing_figures) for item in results)}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when a book inventory entry is structurally incomplete",
    )
    parser.add_argument(
        "--require-gates",
        action="store_true",
        help="also fail until every book has an executable sample gate",
    )
    parser.add_argument(
        "--require-figures",
        action="store_true",
        help="fail when a rendered book references a missing local figure",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    results = audit()
    if args.format == "json":
        print(json.dumps([asdict(item) for item in results], indent=2, sort_keys=True))
    else:
        _print_text(results)
    failures: list[BookGate] = []
    failure_messages: list[str] = []
    if args.require_gates:
        failures = [
            item
            for item in results
            if item.gate not in {"shared-input", "direct-command"}
        ]
        failure_messages.append(
            f"book-gate-audit: {len(failures)} inventory entry(s) lack an executable gate"
        )
    elif args.check:
        failures = [item for item in results if item.gate == "invalid"]
        failure_messages.append(
            f"book-gate-audit: {len(failures)} invalid inventory entry(s)"
        )
    if args.require_figures:
        figure_failures = [item for item in results if item.missing_figures]
        failures.extend(item for item in figure_failures if item not in failures)
        failure_messages.append(
            f"book-gate-audit: {len(figure_failures)} inventory entry(s) reference missing figures"
        )
    if failures:
        print("; ".join(failure_messages), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
