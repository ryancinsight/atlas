#!/usr/bin/env python3
"""Report crate versions duplicated across member lockfiles.

# The trap this exists for

Two members pin different versions of one third-party crate and nobody
notices until a feature unifies them, a lock regenerates against drifted
siblings, or an advisory forces a bump that only fixes half the stack. The
kwavers `chrono` removal (RUSTSEC-2026-0543) showed the shape: direct uses
were trivially replaceable, but `dicom-core` and `serde_with` kept pulling
`chrono` transitively, and the duplicate-`leto` drift that blocks local
`--locked` resolution was invisible until a build broke. This is the tool
that makes that drift visible before it blocks.

# What it does

For every registered member with a root `Cargo.lock`, parse its package
records with the shared `lockfile.locked_package_records` parser and group
by crate name. A crate with more than one distinct version anywhere in the
stack is one row: each version lists its source identity and the members
pinned to it. Members without a root lock are skipped openly, never
silently. Output is a human table by default and `--json` for tracking.
Exit status is 0 with or without findings; `--fail-on-duplicates` exits 2
when any duplicate row exists, for the CI job that wants the gate.
Unparseable locks and other errors exit 1. The tool never writes, fetches,
or resolves anything: it reads committed working-tree locks only.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import lockfile  # noqa: E402  (shared lock parser; not copied)
from atlas_stack import ROOT, registered_members  # noqa: E402


@dataclass
class DuplicateRow:
    """One crate name pinned to more than one version across the stack."""

    name: str
    versions: dict[str, dict[str, object]] = field(default_factory=dict)
    # version -> {"sources": sorted list, "members": sorted list}


@dataclass
class AuditResult:
    rows: list[DuplicateRow]
    members_audited: list[str]
    members_skipped: list[str]
    errors: list[str]


def _source_identity(source: object) -> str:
    if not isinstance(source, str) or not source:
        return "<workspace>"
    return source


def audit_members(member_dirs: list[Path]) -> AuditResult:
    """Group every member lock's packages by crate name and keep multiples."""
    by_name: dict[str, dict[str, dict[str, set[str]]]] = {}
    audited: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []
    for member_dir in sorted(member_dirs):
        lock = member_dir / "Cargo.lock"
        if not lock.is_file():
            skipped.append(member_dir.name)
            continue
        try:
            records = lockfile.locked_package_records(
                lock.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as error:
            errors.append(f"{member_dir.name}: {error}")
            continue
        audited.append(member_dir.name)
        seen: set[tuple[str, str]] = set()
        for record in records:
            name = record["name"]
            assert isinstance(name, str)
            version = record["version"]
            assert isinstance(version, str)
            source = _source_identity(record.get("source"))
            if (name, version, source) in seen:
                continue
            seen.add((name, version, source))
            versions = by_name.setdefault(name, {})
            entry = versions.setdefault(version, {"sources": set(), "members": set()})
            assert isinstance(entry["sources"], set)
            assert isinstance(entry["members"], set)
            entry["sources"].add(source)
            entry["members"].add(member_dir.name)
    rows = [
        DuplicateRow(
            name=name,
            versions={
                version: {
                    "sources": sorted(entry["sources"]),
                    "members": sorted(entry["members"]),
                }
                for version, entry in sorted(versions.items())
            },
        )
        for name, versions in sorted(by_name.items())
        if len(versions) > 1
    ]
    return AuditResult(
        rows=rows,
        members_audited=sorted(audited),
        members_skipped=sorted(skipped),
        errors=errors,
    )


def render_text(result: AuditResult) -> str:
    lines = [
        f"members audited: {len(result.members_audited)} "
        f"({', '.join(result.members_audited) or 'none'})"
    ]
    if result.members_skipped:
        lines.append(
            f"members skipped (no root Cargo.lock): "
            f"{', '.join(result.members_skipped)}"
        )
    if result.errors:
        lines.append("errors:")
        lines.extend(f"  {error}" for error in result.errors)
    if not result.rows:
        lines.append("no duplicated crate versions.")
        return "\n".join(lines) + "\n"
    lines.append(f"duplicated crates: {len(result.rows)}")
    for row in result.rows:
        lines.append(f"{row.name}:")
        versions = row.versions
        assert isinstance(versions, dict)
        for version, detail in versions.items():
            assert isinstance(detail, dict)
            lines.append(
                f"  {version} [{', '.join(detail['sources'])}] "
                f"<- {', '.join(detail['members'])}"
            )
    return "\n".join(lines) + "\n"


def render_json(result: AuditResult) -> str:
    return (
        json.dumps(
            {
                "members_audited": result.members_audited,
                "members_skipped": result.members_skipped,
                "errors": result.errors,
                "duplicates": [
                    {"name": row.name, "versions": row.versions}
                    for row in result.rows
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report crate versions duplicated across member Cargo.lock files."
        )
    )
    parser.add_argument(
        "--member",
        action="append",
        default=[],
        help="Only audit this registered member (repeatable).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the human table.",
    )
    parser.add_argument(
        "--fail-on-duplicates",
        action="store_true",
        help="Exit 2 when any duplicated crate version exists.",
    )
    args = parser.parse_args(argv)
    members = registered_members(ROOT)
    if args.member:
        wanted = set(args.member)
        members = [m for m in members if m.name in wanted]
        missing = wanted - {m.name for m in members}
        if missing:
            print(
                f"unknown members: {', '.join(sorted(missing))}",
                file=sys.stderr,
            )
            return 1
    result = audit_members(members)
    if args.json:
        sys.stdout.write(render_json(result))
    else:
        sys.stdout.write(render_text(result))
    if result.errors:
        return 1
    if args.fail_on_duplicates and result.rows:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
