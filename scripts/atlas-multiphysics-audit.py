#!/usr/bin/env python3
"""Audit the cross-provider contracts required by the Atlas integrators.

The provider integration audit checks registration and version coherence. This
audit checks the next boundary: the three integrators must name their shared
providers, expose a real Rust-backed Python surface, carry an executable book,
and retain independent numerical and operational evidence. It is deliberately
reporting-oriented: missing evidence is a finding, not a synthetic pass.
The ``--exact-gitlinks`` mode scans text snapshots of the provider commits
recorded by Atlas, so dirty nested worktrees cannot change the result.
"""

from __future__ import annotations

import argparse
import io
from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import sys
import tarfile
import tomllib

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class IntegratorProfile:
    """Acceptance requirements for one Atlas integrator."""

    name: str
    required_dependencies: tuple[str, ...]
    forbidden_dependencies: tuple[str, ...] = ("rayon", "tokio", "wgpu")


PROFILES = (
    IntegratorProfile(
        "CFDrs",
        (
            "harmonia",
            "hyperion",
            "proteus",
            "aequitas",
            "eunomia",
            "athena",
            "coeus",
            "consus",
            "ritk",
            "iris",
            "leto",
            "hermes",
            "moirai",
            "themis",
            "hephaestus",
            "tyche",
        ),
    ),
    IntegratorProfile(
        "helios",
        (
            "hyperion",
            "proteus",
            "asclepius",
            "aequitas",
            "eunomia",
            "horae",
            "coeus",
            "consus",
            "ritk",
            "apollo",
            "leto",
            "hephaestus",
            "moirai",
            "mnemosyne",
            "themis",
            "gaia",
            "tyche",
        ),
    ),
    IntegratorProfile(
        "kwavers",
        (
            "hyperion",
            "proteus",
            "asclepius",
            "aequitas",
            "eunomia",
            "horae",
            "ritk",
            "coeus",
            "apollo",
            "hephaestus",
            "hermes",
            "themis",
            "moirai",
            "leto",
            "mnemosyne",
            "gaia",
            "consus",
            "tyche",
        ),
    ),
)

DEPENDENCY_TABLES = {"dependencies", "dev-dependencies", "build-dependencies"}
SOURCE_SUFFIXES = {".rs", ".py", ".pyi", ".toml", ".md"}
DERIVED_PYTHON_DIRS = {"target", ".git", "dist", "build", ".venv"}
DERIVED_SCAN_DIRS = frozenset(DERIVED_PYTHON_DIRS)
RUST_FENCE = re.compile(
    r"^\s*```(?:rust|rs)(?P<attributes>(?:,[^\s]+)*)\s*$", re.MULTILINE
)
PYTHON_SURFACE = re.compile(r"#\s*\[(?:pyclass|pyfunction|pymodule)\b")
GIL_RELEASE = re.compile(r"\b(?:allow_threads|detach)\s*\(")
TYCHE_SOURCE_REFERENCE = re.compile(r"\btyche_core\b")
BOOK_LINK = re.compile(r"\]\((?P<target>[^)#]+)(?:#[^)]*)?\)")
ANALYTICAL = re.compile(
    r"\b(?:analytical|manufactured|closed[- ]form|poiseuille|radon|sinogram|reference)\b",
    re.IGNORECASE,
)
DIFFERENTIAL = re.compile(
    r"\b(?:differential|independent|cross[- ]backend|k[- ]?wave|kwave|oracle)\b",
    re.IGNORECASE,
)
PERFORMANCE = re.compile(
    r"\b(?:criterion|benchmark|flamegraph|perf|throughput|latency|allocation|stats_alloc|dhat)\b",
    re.IGNORECASE,
)
SAFETY = re.compile(r"(?:forbid|deny)\s*\(unsafe_code\)|#!\s*\[forbid\(unsafe_code\)\]")
AUDIT_ARCHIVE_PATHS = (
    "*.rs",
    "*.py",
    "*.pyi",
    "*.toml",
    "*.md",
    "py.typed",
    "*/py.typed",
    "**/py.typed",
)


def _provider_path(name: str) -> Path:
    return ROOT / "repos" / name


def _git_value(*args: str, cwd: Path = ROOT) -> str | None:
    try:
        process = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            encoding="utf-8", errors="replace",
            check=False,
        )
    except OSError:
        return None
    value = process.stdout.strip()
    return value if process.returncode == 0 and value else None


def _committed_gitlink(name: str) -> str | None:
    record = _git_value("ls-tree", "HEAD", "--", f"repos/{name}")
    if not record:
        return None
    fields = record.split()
    return fields[2] if len(fields) >= 3 and fields[1] == "commit" else None


def _committed_archive(provider: Path, revision: str) -> bytes:
    """Return an archive containing only files consumed by this audit."""
    try:
        paths = subprocess.run(
            ["git", "-C", str(provider), "ls-tree", "-r", "--name-only", revision],
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"git tree listing failed: {exc}") from exc
    if paths.returncode:
        detail = paths.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or "git tree listing failed")
    names = paths.stdout.decode("utf-8", errors="replace").splitlines()
    archive_paths = [
        pattern
        for pattern in AUDIT_ARCHIVE_PATHS
        if any(
            PurePosixPath(name).name == "py.typed"
            if "py.typed" in pattern
            else name.endswith(pattern.removeprefix("*"))
            for name in names
        )
    ]

    if not archive_paths:
        return b""
    try:
        process = subprocess.run(
            [
                "git",
                "-C",
                str(provider),
                "archive",
                "--format=tar",
                revision,
                "--",
                *archive_paths,
            ],
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"git archive failed: {exc}") from exc
    if process.returncode:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or "git archive failed")
    return process.stdout


def _read_committed_files(provider: Path, revision: str) -> dict[str, str]:
    """Read audit-readable text files from a committed provider snapshot."""
    contents: dict[str, str] = {}
    archive_bytes = _committed_archive(provider, revision)
    if not archive_bytes:
        return contents
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
        for member in archive.getmembers():
            if member.issym() or member.islnk():
                raise RuntimeError(f"unsupported link in committed snapshot: {member.name}")
            member_path = PurePosixPath(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError(f"archive path escapes snapshot: {member.name}")
            if member.isdir():
                continue
            if not member.isfile():
                raise RuntimeError(f"unsupported archive entry: {member.name}")
            source = archive.extractfile(member)
            if source is None:
                raise RuntimeError(f"archive entry has no content: {member.name}")
            with source:
                contents[member.name] = source.read().decode("utf-8", errors="replace")
    return contents


def _extract_committed_provider(provider: Path, revision: str, destination: Path) -> None:
    """Extract a committed provider snapshot for fixture and diagnostic use."""
    contents = _read_committed_files(provider, revision)
    destination.mkdir(parents=True, exist_ok=False)
    for name, text in contents.items():
        target = destination.joinpath(*PurePosixPath(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _source_files(provider: Path) -> list[Path]:
    paths: list[Path] = []
    for directory, subdirectories, filenames in os.walk(provider):
        subdirectories[:] = [
            name for name in subdirectories if name not in DERIVED_SCAN_DIRS
        ]
        paths.extend(
            Path(directory) / filename
            for filename in filenames
            if Path(filename).suffix in SOURCE_SUFFIXES or filename == "py.typed"
        )
    return paths


def _dependency_names_from_document(document: object) -> set[str]:
    """Collect dependency keys from a parsed manifest document."""
    names: set[str] = set()

    def walk(value: object, path: tuple[str, ...] = ()) -> None:
        if not isinstance(value, dict):
            return
        if path and path[-1] in DEPENDENCY_TABLES:
            names.update(str(key) for key in value)
            for dependency in value.values():
                if isinstance(dependency, dict):
                    package = dependency.get("package")
                    if isinstance(package, str):
                        names.add(package)
        for key, child in value.items():
            walk(child, (*path, str(key)))

    walk(document)
    return names


def _dependency_names(manifest: Path) -> set[str]:
    """Collect dependency keys from all package/workspace dependency tables."""
    try:
        document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return set()
    return _dependency_names_from_document(document)


def _dependency_inventory(provider: Path) -> set[str]:
    names: set[str] = set()
    for manifest in _files_under(provider, {"Cargo.toml"}):
        names.update(_dependency_names(manifest))
    return names


def _files_under(provider: Path, names: set[str]) -> list[Path]:
    """Enumerate named files while pruning derived directories at traversal time."""
    paths: list[Path] = []
    for directory, subdirectories, filenames in os.walk(provider):
        subdirectories[:] = [
            name for name in subdirectories if name not in DERIVED_SCAN_DIRS
        ]
        paths.extend(
            Path(directory) / filename for filename in filenames if filename in names
        )
    return paths


def _matches_dependency(names: set[str], provider: str) -> bool:
    normalized = provider.lower().replace("_", "-")
    for name in names:
        candidate = name.lower().replace("_", "-")
        if candidate == normalized or candidate.startswith(f"{normalized}-"):
            return True
    return False


def _read_texts(files: list[Path]) -> list[tuple[Path, str]]:
    """Read each audit input once for the evidence scans."""
    texts: list[tuple[Path, str]] = []
    for path in files:
        try:
            texts.append((path, path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return texts


def _linked_book_texts(entries: list[tuple[Path, str]]) -> list[tuple[Path, str]]:
    """Return only Markdown sources reachable from a book SUMMARY file."""
    by_path = {
        path.as_posix().replace("\\", "/"): text
        for path, text in entries
    }
    summaries = sorted(
        path for path in by_path if path.startswith("docs/book/") and path.endswith("SUMMARY.md")
    )
    reachable: set[str] = set()
    pending = list(summaries)
    while pending:
        current = pending.pop()
        if current in reachable:
            continue
        reachable.add(current)
        current_dir = posixpath.dirname(current)
        for match in BOOK_LINK.finditer(by_path[current]):
            target = match.group("target").strip()
            if not target or target.startswith(("/", "#")) or target.lower().startswith(
                ("http://", "https://", "mailto:")
            ):
                continue
            candidate = posixpath.normpath(posixpath.join(current_dir, target))
            if candidate not in by_path or not candidate.startswith("docs/book/"):
                continue
            if candidate not in reachable:
                pending.append(candidate)
    return [(Path(path), by_path[path]) for path in sorted(reachable)]


def _python_typing_evidence(provider: Path) -> tuple[bool, bool]:
    """Return source-package ``py.typed`` and stub presence."""
    marker = False
    stubs = False
    for path in _source_files(provider):
        if path.name == "py.typed":
            marker = True
        elif path.suffix == ".pyi":
            stubs = True
        if marker and stubs:
            break
    return marker, stubs


def _book_fence_counts(text: str) -> tuple[int, int]:
    """Return all Rust fences and those not marked ``ignore`` or ``no_run``."""
    matches = list(RUST_FENCE.finditer(text))
    runnable = 0
    for match in matches:
        attributes = {
            value.strip().lower()
            for value in match.group("attributes").lstrip(",").split(",")
            if value.strip()
        }
        if not attributes.intersection({"ignore", "no_run"}):
            runnable += 1
    return len(matches), runnable


def _audit_profile(
    profile: IntegratorProfile,
    *,
    provider: Path | None = None,
    committed_gitlink: str | None = None,
    snapshot: dict[str, str] | None = None,
) -> dict[str, object]:
    provider = provider or _provider_path(profile.name)
    exact = committed_gitlink is not None
    checkout_revision = (
        committed_gitlink
        if exact
        else _git_value("rev-parse", "HEAD", cwd=provider)
    )
    checkout_status = (
        None
        if exact
        else _git_value(
            "status", "--porcelain=v1", "--untracked-files=all", cwd=provider
        )
    )
    book_root = provider / "docs" / "book"
    if snapshot is None:
        source_files = _source_files(provider) if provider.is_dir() else []
        manifests = _dependency_inventory(provider) if provider.is_dir() else set()
        book_files = (
            [path for path in book_root.rglob("*.md") if path.is_file()]
            if book_root.is_dir()
            else []
        )
        source_texts = _read_texts(source_files)
        book_texts = _linked_book_texts(
            [
                (path.relative_to(provider), text)
                for path, text in _read_texts(book_files)
            ]
        )
        provider_initialized = provider.is_dir()
        book_present = (book_root / "book.toml").is_file()
        py_typed, python_stubs = _python_typing_evidence(provider)
    else:
        snapshot_entries = [
            (Path(name), text)
            for name, text in snapshot.items()
            if not any(part in DERIVED_SCAN_DIRS for part in Path(name).parts)
        ]
        source_texts = [
            (path, text)
            for path, text in snapshot_entries
            if path.suffix in SOURCE_SUFFIXES or path.name == "py.typed"
        ]
        source_files = [path for path, _ in source_texts]
        manifests = set()
        for path, text in snapshot_entries:
            if path.name == "Cargo.toml":
                try:
                    manifests.update(
                        _dependency_names_from_document(tomllib.loads(text))
                    )
                except tomllib.TOMLDecodeError:
                    continue
        book_entries = [
            (path, text)
            for path, text in snapshot_entries
            if path.as_posix().startswith("docs/book/") and path.suffix == ".md"
        ]
        book_texts = _linked_book_texts(book_entries)
        book_files = [path for path, _ in book_texts]
        provider_initialized = True
        book_present = "docs/book/book.toml" in snapshot
        py_typed = any(path.name == "py.typed" for path, _ in snapshot_entries)
        python_stubs = any(path.suffix == ".pyi" for path, _ in snapshot_entries)
    book_text = "\n".join(text for _, text in book_texts)
    python_texts = [
        text for path, text in source_texts if path.suffix in {".rs", ".py", ".pyi"}
    ]
    rust_texts = [text for path, text in source_texts if path.suffix == ".rs"]
    findings: list[str] = []
    missing_dependencies = [
        dependency
        for dependency in profile.required_dependencies
        if not _matches_dependency(manifests, dependency)
    ]
    forbidden_dependencies = [
        dependency
        for dependency in profile.forbidden_dependencies
        if _matches_dependency(manifests, dependency)
    ]
    if not provider_initialized:
        findings.append("provider checkout is not initialized")
    if missing_dependencies:
        findings.append("missing provider dependencies: " + ", ".join(missing_dependencies))
    if forbidden_dependencies:
        findings.append("direct incumbent dependencies: " + ", ".join(forbidden_dependencies))

    pyo3 = _matches_dependency(manifests, "pyo3")
    python_surface = sum(len(PYTHON_SURFACE.findall(text)) for text in python_texts)
    gil_release = sum(len(GIL_RELEASE.findall(text)) for text in python_texts)
    tyche_source_references = sum(
        len(TYCHE_SOURCE_REFERENCE.findall(text)) for text in python_texts
    )
    if not pyo3:
        findings.append("no PyO3 dependency")
    if pyo3 and python_surface == 0:
        findings.append("PyO3 dependency has no discovered binding declarations")
    if pyo3 and gil_release == 0:
        findings.append("no explicit GIL-release site discovered")
    if pyo3 and not py_typed:
        findings.append("no source py.typed marker discovered")
    if pyo3 and not python_stubs:
        findings.append("no Python typing stub discovered")
    if tyche_source_references == 0:
        findings.append("no Tyche source reference discovered")

    if not book_present:
        findings.append("docs/book/book.toml is missing")
    rust_fences, runnable_rust_fences = _book_fence_counts(book_text)
    if runnable_rust_fences == 0:
        findings.append("book has no executable Rust fence")

    all_texts = [text for _, text in source_texts + book_texts]
    analytical = sum(len(ANALYTICAL.findall(text)) for text in all_texts)
    differential = sum(len(DIFFERENTIAL.findall(text)) for text in all_texts)
    performance = sum(len(PERFORMANCE.findall(text)) for text in all_texts)
    safety = sum(len(SAFETY.findall(text)) for text in rust_texts)
    if analytical == 0:
        findings.append("no analytical/reference evidence marker discovered")
    if differential == 0:
        findings.append("no independent/differential evidence marker discovered")
    if performance == 0:
        findings.append("no performance or allocation evidence marker discovered")
    if safety == 0:
        findings.append("no crate-level unsafe-code prohibition discovered")

    return {
        "provider": profile.name,
        "status": "fail" if findings else "ok",
        "findings": findings,
        "checkout_revision": checkout_revision,
        "committed_gitlink": committed_gitlink or _committed_gitlink(profile.name),
        "checkout_dirty": None if exact else bool(checkout_status),
        "source": "committed_gitlinks" if exact else "worktrees",
        "dependency_count": len(manifests),
        "required_dependencies": list(profile.required_dependencies),
        "missing_dependencies": missing_dependencies,
        "forbidden_dependencies": forbidden_dependencies,
        "pyo3": pyo3,
        "python_surface_declarations": python_surface,
        "gil_release_sites": gil_release,
        "py_typed_marker": py_typed,
        "python_typing_stubs": python_stubs,
        "tyche_source_references": tyche_source_references,
        "book": book_present,
        "rust_fences": rust_fences,
        "runnable_rust_fences": runnable_rust_fences,
        "analytical_reference_markers": analytical,
        "differential_reference_markers": differential,
        "performance_memory_markers": performance,
        "unsafe_code_prohibition_markers": safety,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--integrators",
        default=",".join(profile.name for profile in PROFILES),
        help="comma-separated integrators (default: CFDrs,helios,kwavers)",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--exact-gitlinks",
        action="store_true",
        help="audit isolated snapshots of the provider commits recorded by Atlas",
    )
    parser.add_argument(
        "--require-evidence",
        action="store_true",
        help="return failure when any evidence finding exists; default reports findings",
    )
    return parser.parse_args(argv)


def _require_attribution(reports: list[dict[str, object]]) -> None:
    """Add revision/cleanliness findings required by the blocking mode."""
    for report in reports:
        provider = report.get("provider", "")
        if provider not in {profile.name for profile in PROFILES}:
            continue
        findings = report.setdefault("findings", [])
        if report.get("checkout_dirty"):
            findings.append("provider checkout is dirty; clean attribution is required")
        checkout_revision = report.get("checkout_revision")
        committed_gitlink = report.get("committed_gitlink")
        if checkout_revision != committed_gitlink:
            findings.append(
                "checkout revision does not match the committed gitlink; exact attribution is required"
            )
        report["status"] = "fail" if findings else "ok"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    selected = {name.strip() for name in args.integrators.split(",") if name.strip()}
    profiles = tuple(profile for profile in PROFILES if profile.name in selected)
    unknown = selected - {profile.name for profile in PROFILES}
    if args.exact_gitlinks:
        reports = []
        for profile in profiles:
            revision = _committed_gitlink(profile.name)
            if revision is None:
                reports.append(
                    {
                        "provider": profile.name,
                        "status": "fail",
                        "findings": ["committed gitlink is unavailable"],
                        "source": "committed_gitlinks",
                    }
                )
                continue
            provider = _provider_path(profile.name)
            try:
                snapshot = _read_committed_files(provider, revision)
            except RuntimeError as exc:
                reports.append(
                    {
                        "provider": profile.name,
                        "status": "fail",
                        "findings": [f"committed snapshot unavailable: {exc}"],
                        "committed_gitlink": revision,
                        "source": "committed_gitlinks",
                    }
                )
                continue
            reports.append(
                _audit_profile(
                    profile,
                    provider=provider,
                    committed_gitlink=revision,
                    snapshot=snapshot,
                )
            )
        return _finish(args, selected, unknown, reports)

    reports = [_audit_profile(profile) for profile in profiles]
    return _finish(args, selected, unknown, reports)


def _finish(
    args: argparse.Namespace,
    selected: set[str],
    unknown: set[str],
    reports: list[dict[str, object]],
) -> int:
    """Apply selection checks and render an audit result."""
    if not selected:
        reports.append(
            {
                "provider": "<selection>",
                "status": "fail",
                "findings": ["no integrators selected"],
            }
        )
    if unknown:
        reports.append({"provider": "<selection>", "status": "fail", "findings": [
            "unknown integrators: " + ", ".join(sorted(unknown))
        ]})
    if args.require_evidence:
        _require_attribution(reports)
    failed = [report for report in reports if report.get("status") == "fail"]
    if args.format == "json":
        print(json.dumps({"status": "fail" if failed else "ok", "integrators": reports}, indent=2))
    else:
        source = "committed provider snapshots" if args.exact_gitlinks else "provider worktrees"
        print(f"multiphysics-audit: {'FAIL' if failed else 'OK'} (source: {source})")
        for report in reports:
            print(f"- {report['provider']}: {report['status']}")
            for finding in report.get("findings", []):
                print(f"  - {finding}")
    selection_error = not selected or bool(unknown)
    return 1 if selection_error or (args.require_evidence and failed) else 0


if __name__ == "__main__":
    sys.exit(main())
