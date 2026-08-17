#!/usr/bin/env python3
"""Guard Atlas root integration closure for the named provider set.

This is a structural gate for the atlas-meta records. It intentionally checks
only root-owned integration facts:

1. Requested providers are present and active in `.gitmodules`.
2. The canonical root PM records carry the closed audit marker.
3. Naming normalization remains explicit (`Tyche (aka Tychee)`).
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GITMODULES = ROOT / ".gitmodules"
RECORD_FILES = (
    ROOT / "checklist.md",
    ROOT / "backlog.md",
    ROOT / "gap_audit.md",
)
AUDIT_ID = "ATLAS-PROVIDER-INTEGRATION-AUDIT-001"
NAME_NORMALIZATION = "Tyche (aka Tychee)"
REQUIRED_PROVIDERS = (
    "horae",
    "hyperion",
    "themis",
    "tyche",
    "proteus",
    "mnemosyne",
    "consus",
    "helios",
    "aequitas",
    "asclepius",
    "eunomia",
    "moirai",
    "ritk",
    "melinoe",
    "leto",
    "hephaestus",
    "coeus",
    "apollo",
    "gaia",
    "hermes",
    "iris",
)
REQUESTED_PROVIDERS_20260814 = (
    "horae",
    "hyperion",
    "themis",
    "tyche",
    "proteus",
    "mnemosyne",
    "consus",
    "helios",
    "hermes",
    "aequitas",
    "asclepius",
    "eunomia",
    "moirai",
    "ritk",
    "melinoe",
    "leto",
    "hephaestus",
    "coeus",
    "apollo",
    "iris",
)
PROVIDER_SETS: dict[str, tuple[str, ...]] = {
    "atlas-21": REQUIRED_PROVIDERS,
    "requested-2026-08-14": REQUESTED_PROVIDERS_20260814,
}
PROVIDER_ALIASES = {
    "tychee": "tyche",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _active_submodule_names(gitmodules_text: str) -> dict[str, bool]:
    names: dict[str, bool] = {}
    current_name: str | None = None
    current_active = False
    for raw_line in gitmodules_text.splitlines():
        line = raw_line.strip()
        header = re.match(r'^\[submodule\s+"([^"]+)"\]\s*$', line)
        if header:
            if current_name is not None:
                names[current_name] = current_active
            current_name = header.group(1).replace("\\", "/")
            current_active = False
            continue
        if current_name is None or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key.lower() == "active" and value.lower() == "true":
            current_active = True
    if current_name is not None:
        names[current_name] = current_active
    return names


def _provider_activation_issues(
    gitmodules_text: str, providers: tuple[str, ...]
) -> list[str]:
    active_names = _active_submodule_names(gitmodules_text)
    issues: list[str] = []
    for provider in providers:
        submodule_name = f"repos/{provider}"
        is_active = active_names.get(submodule_name)
        if is_active is None:
            issues.append(f"missing submodule block for repos/{provider}")
            continue
        if not is_active:
            issues.append(f"repos/{provider} missing `active = true`")
    return issues


def _git_output(*args: str, cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a bounded Git query and return its exit status and text streams."""
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT if cwd is None else cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _gitlink_commits(providers: tuple[str, ...]) -> dict[str, str]:
    """Return indexed root gitlinks for a provider set using one Git query."""
    if not providers:
        return {}
    paths = [f"repos/{provider}" for provider in providers]
    returncode, stdout, _ = _git_output("ls-files", "--stage", "--", *paths)
    if returncode != 0:
        return {}

    commits: dict[str, str] = {}
    for line in stdout.splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[0] != "160000":
            continue
        path = fields[3].replace("\\", "/")
        provider = path.rsplit("/", 1)[-1]
        commits[provider] = fields[1]
    return commits


def _provider_remote_head(provider: str) -> tuple[str | None, str | None, str | None]:
    """Return a provider's fetched default ref and commit, if available."""
    provider_path = ROOT / "repos" / provider
    if not provider_path.is_dir():
        return None, None, f"repos/{provider} is not initialized"

    returncode, symbolic_ref, _ = _git_output(
        "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD",
        cwd=provider_path,
    )
    candidates = [symbolic_ref] if returncode == 0 and symbolic_ref else []
    candidates.extend(("origin/main", "origin/master"))
    seen: set[str] = set()
    for ref in candidates:
        if not ref or ref in seen:
            continue
        seen.add(ref)
        returncode, commit, _ = _git_output(
            "rev-parse", "--verify", ref, cwd=provider_path
        )
        if returncode == 0 and commit:
            return ref, commit, None
    return None, None, f"repos/{provider} has no fetched origin default head"


def _exact_head_issues(
    providers: tuple[str, ...], max_workers: int | None = None
) -> list[str]:
    """Return root-gitlink drift against each fetched provider default head."""
    issues: list[str] = []
    gitlinks = _gitlink_commits(providers)
    if not gitlinks:
        return [f"{name}: committed gitlink is unavailable" for name in providers]

    def _fetch(provider: str) -> tuple[str, str | None, str | None, str | None]:
        ref, remote_head, error = _provider_remote_head(provider)
        return provider, ref, remote_head, error

    worker_count = (
        min(8, len(providers)) if max_workers is None else max(1, min(max_workers, len(providers)))
    ) or 1
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        remote_results = {
            provider: (ref, remote_head, error)
            for provider, ref, remote_head, error in executor.map(_fetch, providers)
        }

    for provider in providers:
        gitlink = gitlinks.get(provider)
        ref, remote_head, error = remote_results.get(provider, (None, None, None))
        if error:
            issues.append(f"repos/{provider}: {error}")
            continue
        if gitlink is None:
            issues.append(f"repos/{provider}: committed gitlink is unavailable")
            continue
        if gitlink != remote_head:
            issues.append(
                f"repos/{provider}: gitlink {gitlink} != {ref} {remote_head}"
            )
    return issues


def _clean_rust_env() -> dict[str, str]:
    env = os.environ.copy()
    for var in ("RUSTC", "RUSTDOC"):
        env.pop(var, None)
    return env


def _coherence_scope_issues(providers: tuple[str, ...]) -> tuple[list[str], int]:
    """Return requested-scope coherence defects and out-of-scope defect count."""
    command = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(ROOT / "tools" / "version-guard" / "Cargo.toml"),
        "--",
        "coherence",
        "--atlas-root",
        str(ROOT),
        "--format",
        "json",
    ]
    proc = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, env=_clean_rust_env(), check=False
    )
    if proc.returncode not in (0, 1):
        stderr = proc.stderr.strip() or "(no stderr)"
        return ([f"coherence invocation failed (rc={proc.returncode}): {stderr}"], 0)
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return ([f"coherence output was not valid JSON: {exc}"], 0)
    return _coherence_scope_issues_from_report(report, providers)


def _coherence_scope_issues_from_report(
    report: object, providers: tuple[str, ...]
) -> tuple[list[str], int]:
    if not isinstance(report, dict):
        return (["coherence JSON root must be an object"], 0)
    findings = report.get("findings", [])
    if not isinstance(findings, list):
        return (["coherence JSON missing findings list"], 0)

    scoped_issues: list[str] = []
    out_of_scope = 0
    provider_names = set(providers)
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        manifest = str(finding.get("manifest", ""))
        normalized_manifest = manifest.replace("\\", "/")
        parts = normalized_manifest.split("/", 2)
        manifest_provider = parts[1] if len(parts) >= 2 and parts[0] == "repos" else None
        if manifest_provider in provider_names:
            dependency = finding.get("dependency", "?")
            package = finding.get("package", "?")
            required = finding.get("required", "?")
            actual = finding.get("actual", "?")
            reason = finding.get("reason", "unknown reason")
            scoped_issues.append(
                f"{normalized_manifest}: {dependency} ({package}) requires {required}, actual {actual} ({reason})"
            )
        else:
            out_of_scope += 1
    return scoped_issues, out_of_scope


def _coherence_scope_issues_from_json_file(
    report_path: Path, providers: tuple[str, ...]
) -> tuple[list[str], int]:
    try:
        payload = report_path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        return ([f"coherence report JSON is unreadable at {report_path}: {exc}"], 0)
    try:
        report = json.loads(payload)
    except json.JSONDecodeError as exc:
        return ([f"coherence report JSON at {report_path} is invalid: {exc}"], 0)
    if not isinstance(report, dict):
        return ([f"coherence report JSON at {report_path} must be an object"], 0)
    return _coherence_scope_issues_from_report(report, providers)


def _record_issues() -> list[str]:
    issues: list[str] = []
    for path in RECORD_FILES:
        text = _read(path)
        if AUDIT_ID not in text:
            issues.append(f"{path.name}: missing {AUDIT_ID} marker")
            continue
        if not re.search(
            rf"{re.escape(AUDIT_ID)}[\s\S]{{0,220}}?\b(done|closed)\b", text
        ):
            issues.append(f"{path.name}: {AUDIT_ID} is not marked done/closed")
        if NAME_NORMALIZATION not in text:
            issues.append(f"{path.name}: missing '{NAME_NORMALIZATION}' normalization")
    return issues


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    def _positive_int(value: str) -> int:
        parsed = int(value)
        if parsed < 1:
            raise argparse.ArgumentTypeError("must be >= 1")
        return parsed

    parser = argparse.ArgumentParser(
        description=(
            "Validate Atlas provider integration closure markers and requested-provider coherence."
        )
    )
    parser.add_argument(
        "--structural-only",
        action="store_true",
        help="skip requested-provider coherence and run only structural checks",
    )
    parser.add_argument(
        "--exact-heads",
        action="store_true",
        help="verify committed provider gitlinks against fetched origin defaults",
    )
    parser.add_argument(
        "--exact-head-workers",
        type=_positive_int,
        default=8,
        help="worker count for --exact-heads remote-head checks (default: 8)",
    )
    parser.add_argument(
        "--provider-set",
        choices=tuple(PROVIDER_SETS.keys()),
        default="atlas-21",
        help=(
            "named provider scope to audit (default: atlas-21; "
            "requested-2026-08-14 matches the user-requested twenty-provider set)"
        ),
    )
    parser.add_argument(
        "--providers",
        type=str,
        help=(
            "comma-separated provider override (names under repos/, accepts aliases "
            "such as tychee -> tyche)"
        ),
    )
    parser.add_argument(
        "--providers-file",
        type=str,
        help=(
            "provider override file path; names may be separated by commas and/or "
            "newlines (takes precedence over --providers and --provider-set)"
        ),
    )
    parser.add_argument(
        "--fail-out-of-scope",
        action="store_true",
        help="treat out-of-scope coherence defects as blocking",
    )
    parser.add_argument(
        "--coherence-report-json",
        type=str,
        help=(
            "precomputed coherence JSON report path; when provided, consumes this report "
            "instead of invoking cargo coherence"
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    return parser.parse_args(argv)


def _normalized_deduped_providers(raw_names: list[str]) -> tuple[str, ...]:
    selected: list[str] = []
    for raw_name in raw_names:
        name = raw_name.strip().lower()
        if not name:
            continue
        normalized = PROVIDER_ALIASES.get(name, name)
        if normalized not in selected:
            selected.append(normalized)
    return tuple(selected)


def _providers_from_file(path_text: str) -> tuple[str, ...]:
    providers_path = Path(path_text)
    try:
        payload = providers_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            f"providers file is unreadable at {providers_path}: {exc}"
        ) from exc
    raw_names = re.split(r"[,\n]+", payload)
    return _normalized_deduped_providers(raw_names)


def _selected_providers(args: argparse.Namespace) -> tuple[str, ...]:
    if args.providers_file:
        return _providers_from_file(args.providers_file)
    if not args.providers:
        return PROVIDER_SETS[args.provider_set]
    return _normalized_deduped_providers(args.providers.split(","))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        providers = _selected_providers(args)
    except ValueError as exc:
        issues = [str(exc)]
        if args.format == "json":
            print(
                json.dumps(
                    {
                        "status": "fail",
                        "provider_set": [],
                        "provider_count": 0,
                        "exact_heads": bool(args.exact_heads),
                        "structural_only": bool(args.structural_only),
                        "out_of_scope_coherence": 0,
                        "issues": issues,
                    }
                )
            )
            return 1
        print("provider-integration-audit: FAIL")
        print(f"- {issues[0]}")
        return 1
    if not providers:
        issues = ["no providers selected"]
        if args.format == "json":
            print(
                json.dumps(
                    {
                        "status": "fail",
                        "provider_set": list(providers),
                        "provider_count": len(providers),
                        "exact_heads": bool(args.exact_heads),
                        "structural_only": bool(args.structural_only),
                        "out_of_scope_coherence": 0,
                        "issues": issues,
                    }
                )
            )
            return 1
        print("provider-integration-audit: FAIL")
        print("- no providers selected")
        return 1
    issues: list[str] = []
    if not GITMODULES.is_file():
        issues.append("missing .gitmodules")
    else:
        issues.extend(_provider_activation_issues(_read(GITMODULES), providers))

    for path in RECORD_FILES:
        if not path.is_file():
            issues.append(f"missing required record file: {path.name}")
    if not issues:
        issues.extend(_record_issues())
        if args.exact_heads:
            issues.extend(_exact_head_issues(providers, args.exact_head_workers))
        if args.structural_only:
            out_of_scope = 0
        else:
            if args.coherence_report_json:
                scoped_coherence_issues, out_of_scope = _coherence_scope_issues_from_json_file(
                    Path(args.coherence_report_json),
                    providers,
                )
            else:
                scoped_coherence_issues, out_of_scope = _coherence_scope_issues(providers)
            issues.extend(scoped_coherence_issues)
            if args.fail_out_of_scope and out_of_scope:
                issues.append(
                    "out-of-scope coherence defects present outside requested providers: "
                    f"{out_of_scope} (--fail-out-of-scope)"
                )
    else:
        out_of_scope = 0

    if args.format == "json":
        print(
            json.dumps(
                {
                    "status": "fail" if issues else "ok",
                    "provider_set": list(providers),
                    "provider_count": len(providers),
                    "exact_heads": bool(args.exact_heads),
                    "structural_only": bool(args.structural_only),
                    "out_of_scope_coherence": out_of_scope,
                    "issues": issues,
                }
            )
        )
        return 1 if issues else 0

    if issues:
        print("provider-integration-audit: FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("provider-integration-audit: OK")
    print(f"- provider set: {', '.join(providers)}")
    print(f"- {len(providers)} providers present and active in .gitmodules")
    print(f"- {AUDIT_ID} closed across root records")
    print(f"- naming normalization retained: {NAME_NORMALIZATION}")
    if args.exact_heads:
        print("- committed provider gitlinks match fetched origin defaults")
    if args.structural_only:
        print("- requested-provider coherence skipped (--structural-only)")
    elif out_of_scope:
        print(
            "- out-of-scope coherence defects present outside requested providers: "
            f"{out_of_scope} (reported by global coherence, non-blocking here)"
        )
    else:
        print("- requested-provider coherence scope is clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
