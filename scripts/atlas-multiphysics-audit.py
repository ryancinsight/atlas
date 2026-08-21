#!/usr/bin/env python3
"""Audit the cross-provider contracts required by the Atlas integrators.

The provider integration audit checks registration and version coherence. This
audit checks the next boundary: the three integrators must name their shared
providers, expose a real Rust-backed Python surface, carry an executable book,
and retain independent numerical and operational evidence. It is deliberately
reporting-oriented: missing evidence is a finding, not a synthetic pass.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import sys
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
RUST_FENCE = re.compile(
    r"^\s*```(?:rust|rs)(?P<attributes>(?:,[^\s]+)*)\s*$", re.MULTILINE
)
PYTHON_SURFACE = re.compile(r"#\s*\[(?:pyclass|pyfunction|pymodule)\b")
GIL_RELEASE = re.compile(r"\b(?:allow_threads|detach)\s*\(")
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


def _provider_path(name: str) -> Path:
    return ROOT / "repos" / name


def _git_value(*args: str, cwd: Path = ROOT) -> str | None:
    try:
        process = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
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


def _source_files(provider: Path) -> list[Path]:
    return [
        path
        for path in provider.rglob("*")
        if path.is_file()
        and path.suffix in SOURCE_SUFFIXES
        and "target" not in path.parts
        and ".git" not in path.parts
    ]


def _dependency_names(manifest: Path) -> set[str]:
    """Collect dependency keys from all package/workspace dependency tables."""
    try:
        document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return set()

    names: set[str] = set()

    def walk(value: object, path: tuple[str, ...] = ()) -> None:
        if not isinstance(value, dict):
            return
        if path and path[-1] in DEPENDENCY_TABLES:
            names.update(str(key) for key in value)
        for key, child in value.items():
            walk(child, (*path, str(key)))

    walk(document)
    return names


def _dependency_inventory(provider: Path) -> set[str]:
    names: set[str] = set()
    for manifest in provider.rglob("Cargo.toml"):
        if "target" not in manifest.parts and ".git" not in manifest.parts:
            names.update(_dependency_names(manifest))
    return names


def _matches_dependency(names: set[str], provider: str) -> bool:
    normalized = provider.lower().replace("_", "-")
    for name in names:
        candidate = name.lower().replace("_", "-")
        if candidate == normalized or candidate.startswith(f"{normalized}-"):
            return True
    return False


def _count_matches(files: list[Path], pattern: re.Pattern[str]) -> int:
    count = 0
    for path in files:
        try:
            count += len(pattern.findall(path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return count


def _python_typing_evidence(provider: Path) -> tuple[bool, bool]:
    """Return source-package ``py.typed`` and stub presence."""
    marker = False
    stubs = False
    for path in provider.rglob("*"):
        if not path.is_file() or DERIVED_PYTHON_DIRS.intersection(path.parts):
            continue
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


def _audit_profile(profile: IntegratorProfile) -> dict[str, object]:
    provider = _provider_path(profile.name)
    checkout_revision = _git_value("rev-parse", "HEAD", cwd=provider)
    checkout_status = _git_value(
        "status", "--porcelain=v1", "--untracked-files=all", cwd=provider
    )
    source_files = _source_files(provider) if provider.is_dir() else []
    manifests = _dependency_inventory(provider) if provider.is_dir() else set()
    book_root = provider / "docs" / "book"
    book_files = (
        [path for path in book_root.rglob("*.md") if path.is_file()]
        if book_root.is_dir()
        else []
    )
    book_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace") for path in book_files
    )
    python_files = [path for path in source_files if path.suffix in {".rs", ".py", ".pyi"}]
    rust_files = [path for path in source_files if path.suffix == ".rs"]
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
    if not provider.is_dir():
        findings.append("provider checkout is not initialized")
    if missing_dependencies:
        findings.append("missing provider dependencies: " + ", ".join(missing_dependencies))
    if forbidden_dependencies:
        findings.append("direct incumbent dependencies: " + ", ".join(forbidden_dependencies))

    pyo3 = _matches_dependency(manifests, "pyo3")
    python_surface = _count_matches(python_files, PYTHON_SURFACE)
    gil_release = _count_matches(python_files, GIL_RELEASE)
    py_typed, python_stubs = _python_typing_evidence(provider)
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

    if not (book_root / "book.toml").is_file():
        findings.append("docs/book/book.toml is missing")
    rust_fences, runnable_rust_fences = _book_fence_counts(book_text)
    if runnable_rust_fences == 0:
        findings.append("book has no executable Rust fence")

    analytical = _count_matches(source_files + book_files, ANALYTICAL)
    differential = _count_matches(source_files + book_files, DIFFERENTIAL)
    performance = _count_matches(source_files + book_files, PERFORMANCE)
    safety = _count_matches(rust_files, SAFETY)
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
        "committed_gitlink": _committed_gitlink(profile.name),
        "checkout_dirty": bool(checkout_status),
        "dependency_count": len(manifests),
        "required_dependencies": list(profile.required_dependencies),
        "missing_dependencies": missing_dependencies,
        "forbidden_dependencies": forbidden_dependencies,
        "pyo3": pyo3,
        "python_surface_declarations": python_surface,
        "gil_release_sites": gil_release,
        "py_typed_marker": py_typed,
        "python_typing_stubs": python_stubs,
        "book": book_root.is_dir() and (book_root / "book.toml").is_file(),
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
    reports = [_audit_profile(profile) for profile in profiles]
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
        print(f"multiphysics-audit: {'FAIL' if failed else 'OK'}")
        for report in reports:
            print(f"- {report['provider']}: {report['status']}")
            for finding in report.get("findings", []):
                print(f"  - {finding}")
    return 1 if args.require_evidence and failed else 0


if __name__ == "__main__":
    sys.exit(main())
