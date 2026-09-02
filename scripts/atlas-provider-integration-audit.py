#!/usr/bin/env python3
"""Guard Atlas root integration closure for the named provider set.

This is a structural gate for the atlas-meta records. It checks root-owned
integration facts and can optionally require each initialized provider checkout
to be clean and at its recorded gitlink:

1. Requested providers are present and active in `.gitmodules`.
2. The canonical root PM records carry the closed audit marker.
3. Naming normalization remains explicit (`Tyche (aka Tychee)`).

When exact-head or clean-checkout verification is requested, the three Atlas
integrators (CFDrs, Kwavers, and Helios) are checked as well. They are not
members of the provider-count inventory, but their root gitlinks are part of
the same integration contract.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_stack import run_tool  # noqa: E402

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
    "harmonia",
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
INTEGRATOR_REPOS = ("CFDrs", "kwavers", "helios")
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
    "atlas-22": REQUIRED_PROVIDERS,
    "requested-2026-08-14": REQUESTED_PROVIDERS_20260814,
}
PROVIDER_ALIASES = {
    "tychee": "tyche",
}

# Keep the Cargo-backed coherence probe bounded below the root conformance job
# budget while allowing a cold local version-guard build to finish.
COHERENCE_TIMEOUT_SECONDS = 120
REMOTE_HEAD_TIMEOUT_SECONDS = 30


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
        encoding="utf-8", errors="replace",
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _gitlink_commits(providers: tuple[str, ...]) -> dict[str, str]:
    """Return committed root gitlinks for a provider set using one Git query."""
    if not providers:
        return {}
    paths = [f"repos/{provider}" for provider in providers]
    returncode, stdout, _ = _git_output("ls-tree", "HEAD", "--", *paths)
    if returncode != 0:
        return {}

    commits: dict[str, str] = {}
    for line in stdout.splitlines():
        fields = line.split(maxsplit=3)
        if len(fields) < 4 or fields[0] != "160000" or fields[1] != "commit":
            continue
        path = fields[3].replace("\\", "/")
        provider = path.rsplit("/", 1)[-1]
        commits[provider] = fields[2]
    return commits


def _committed_provider_url(provider: str) -> tuple[str | None, str | None]:
    """Read a provider URL from the committed root submodule manifest."""
    returncode, text, error = _git_output("show", "HEAD:.gitmodules")
    if returncode != 0:
        return None, error or "committed .gitmodules is unavailable"
    current_path: str | None = None
    current_url: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        header = re.match(r'^\[submodule\s+"([^"]+)"\]$', line)
        if header:
            if current_path == f"repos/{provider}" and current_url:
                return current_url, None
            current_path = None
            current_url = None
            continue
        if current_path is None and line.startswith("path") and "=" in line:
            current_path = line.split("=", 1)[1].strip().replace("\\", "/")
        elif current_path is not None and line.startswith("url") and "=" in line:
            current_url = line.split("=", 1)[1].strip()
    if current_path == f"repos/{provider}" and current_url:
        return current_url, None
    return None, f"repos/{provider} has no committed submodule URL"


def _normalize_git_url(url: str) -> str:
    """Normalize equivalent GitHub URL spellings for identity comparison."""
    normalized = url.strip().lower().rstrip("/")
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    return normalized


def _provider_remote_head(provider: str) -> tuple[str | None, str | None, str | None]:
    """Return a provider's authoritative remote default ref and commit."""
    provider_path = ROOT / "repos" / provider
    if not provider_path.is_dir():
        return None, None, f"repos/{provider} is not initialized"

    def remote_query(*arguments: str) -> tuple[int, str, str]:
        try:
            process = subprocess.run(
                ["git", *arguments],
                cwd=provider_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=REMOTE_HEAD_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return (
                124,
                "",
                f"git {' '.join(arguments)} timed out after "
                f"{REMOTE_HEAD_TIMEOUT_SECONDS}s",
            )
        except OSError as exc:
            return 127, "", str(exc)
        return process.returncode, process.stdout.strip(), process.stderr.strip()

    expected_url, url_error = _committed_provider_url(provider)
    if url_error:
        return None, None, f"repos/{provider}: {url_error}"
    origin_code, origin_url, origin_error = remote_query(
        "config", "--get", "remote.origin.url"
    )
    if origin_code != 0 or not origin_url:
        detail = origin_error or "remote.origin.url is unavailable"
        return None, None, f"repos/{provider}: cannot verify origin URL ({detail})"
    if expected_url is None or _normalize_git_url(origin_url) != _normalize_git_url(expected_url):
        return (
            None,
            None,
            f"repos/{provider}: origin URL does not match committed submodule URL",
        )

    symbolic_code, symbolic_output, symbolic_error = remote_query(
        "ls-remote", "--symref", "origin", "HEAD"
    )
    branches: list[str] = []
    if symbolic_code == 0:
        for line in symbolic_output.splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[0] == "ref:" and fields[1].startswith(
                "refs/heads/"
            ):
                branches.append(fields[1].removeprefix("refs/heads/"))
                break
    elif symbolic_error:
        symbolic_error = f"remote default query failed: {symbolic_error}"

    # Main/master are the supported Atlas provider default names. They remain
    # fallbacks when a hosting service omits the symbolic HEAD response.
    branches.extend(branch for branch in ("main", "master") if branch not in branches)
    errors: list[str] = [symbolic_error] if symbolic_error else []
    for branch in branches:
        returncode, output, error = remote_query(
            "ls-remote", "origin", f"refs/heads/{branch}"
        )
        fields = output.split()
        if returncode == 0 and fields:
            return f"origin/{branch}", fields[0], None
        if error:
            errors.append(f"origin/{branch}: {error}")
    detail = "; ".join(errors) if errors else "no remote default branch found"
    return None, None, f"repos/{provider} remote default unavailable ({detail})"


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


def _clean_checkout_issues(providers: tuple[str, ...]) -> list[str]:
    """Return provider checkout drift or dirty-state findings."""
    gitlinks = _gitlink_commits(providers)
    issues: list[str] = []
    for provider in providers:
        provider_path = ROOT / "repos" / provider
        if not provider_path.is_dir():
            issues.append(f"repos/{provider}: checkout is not initialized")
            continue

        returncode, checkout_head, stderr = _git_output(
            "rev-parse", "--verify", "HEAD", cwd=provider_path
        )
        if returncode != 0 or not checkout_head:
            detail = stderr or "HEAD is unavailable"
            issues.append(f"repos/{provider}: cannot read checkout HEAD ({detail})")
        elif gitlinks.get(provider) != checkout_head:
            issues.append(
                f"repos/{provider}: checkout HEAD {checkout_head} != committed gitlink "
                f"{gitlinks.get(provider, '(missing)')}"
            )

        returncode, status, stderr = _git_output(
            "status", "--porcelain=v1", "--untracked-files=all", cwd=provider_path
        )
        if returncode != 0:
            detail = stderr or "status query failed"
            issues.append(f"repos/{provider}: cannot read checkout status ({detail})")
        elif status:
            changed_entries = len(status.splitlines())
            issues.append(
                f"repos/{provider}: checkout is dirty ({changed_entries} changed entries)"
            )
    return issues


def _clean_rust_env() -> dict[str, str]:
    env = os.environ.copy()
    for var in ("RUSTC", "RUSTDOC"):
        env.pop(var, None)
    return env


def _coherence_scope_issues(providers: tuple[str, ...]) -> tuple[list[str], int]:
    """Return requested-scope coherence defects and out-of-scope defect count."""
    try:
        proc = run_tool(
            "version-guard",
            ["coherence", "--atlas-root", str(ROOT), "--format", "json"],
            capture_output=True,
            encoding="utf-8", errors="replace",
            env=_clean_rust_env(),
            timeout=COHERENCE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return (
            [
                "coherence invocation timed out after "
                f"{COHERENCE_TIMEOUT_SECONDS} seconds"
            ],
            0,
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

    scoped_groups: dict[tuple[str, str, str, str, str], list[str]] = {}
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
            dependency = str(finding.get("dependency", "?"))
            package = str(finding.get("package", "?"))
            required = str(finding.get("required", "?"))
            actual = str(finding.get("actual", "?"))
            reason = str(finding.get("reason", "unknown reason"))
            key = (dependency, package, required, actual, reason)
            scoped_groups.setdefault(key, []).append(normalized_manifest)
        else:
            out_of_scope += 1
    scoped_issues: list[str] = []
    for key, manifests in sorted(
        scoped_groups.items(), key=lambda item: len(item[1]), reverse=True
    ):
        dependency, package, required, actual, reason = key
        count = len(manifests)
        examples = ", ".join(manifests[:3])
        scoped_issues.append(
            f"{count}x {dependency} ({package}) requires {required},"
            f" actual {actual} ({reason}); examples: {examples}"
        )
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
    def current_item(text: str) -> str | None:
        heading_pattern = re.compile(
            rf"(?m)^(?P<marks>\#{{1,6}})[ \t]+[^\n]*{re.escape(AUDIT_ID)}[^\n]*$"
        )
        heading_matches = list(heading_pattern.finditer(text))
        if heading_matches:
            match = heading_matches[0]
            level = len(match.group("marks"))
            boundary_pattern = re.compile(r"(?m)^(?P<marks>\#{1,6})[ \t]+")
            end = len(text)
            for boundary in boundary_pattern.finditer(text, match.end()):
                if len(boundary.group("marks")) <= level:
                    end = boundary.start()
                    break
            next_item = re.search(
                rf"(?m)^(?:\#{1,6}[ \t]+[^\n]*{re.escape(AUDIT_ID)}[^\n]*|"
                rf"[ \t]*[-*+][ \t]+(?:\*\*)?{re.escape(AUDIT_ID)})",
                text[match.end() :],
            )
            if next_item is not None:
                end = min(end, match.end() + next_item.start())
            return text[match.start() : end]

        item_pattern = re.compile(
            rf"(?m)^(?P<indent>[ \t]*)[-*+][ \t]+(?:\*\*)?"
            rf"{re.escape(AUDIT_ID)}"
        )
        item_match = item_pattern.search(text)
        if item_match is None:
            return None
        indent = len(item_match.group("indent").expandtabs(4))
        end = len(text)
        boundary_pattern = re.compile(
            r"(?m)^(?P<indent>[ \t]*)(?:[-*+]|\d+[.)])[ \t]+|"
            r"^(?P<heading>\#{1,6})[ \t]+"
        )
        for boundary in boundary_pattern.finditer(text, item_match.end()):
            if boundary.group("heading") is not None:
                end = boundary.start()
                break
            boundary_indent = len(boundary.group("indent").expandtabs(4))
            if boundary_indent <= indent:
                end = boundary.start()
                break
        return text[item_match.start() : end]

    issues: list[str] = []
    for path in RECORD_FILES:
        text = _read(path)
        item = current_item(text)
        if item is None:
            issues.append(f"{path.name}: missing current {AUDIT_ID} item")
            continue
        if not re.search(r"\b(done|closed)\b", item, flags=re.IGNORECASE):
            issues.append(f"{path.name}: {AUDIT_ID} is not marked done/closed")
        if NAME_NORMALIZATION not in item:
            issues.append(f"{path.name}: missing '{NAME_NORMALIZATION}' normalization")
    return issues


def _structural_provider_count(providers: tuple[str, ...]) -> int:
    """Return the provider count for the requested structural audit scope."""
    return len(providers)


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
        help="verify committed provider gitlinks against current remote defaults",
    )
    parser.add_argument(
        "--exact-head-workers",
        type=_positive_int,
        default=8,
        help="worker count for --exact-heads remote-head checks (default: 8)",
    )
    parser.add_argument(
        "--require-clean-checkouts",
        action="store_true",
        help=(
            "require initialized provider checkouts to match committed gitlinks "
            "and have no tracked or untracked changes"
        ),
    )
    parser.add_argument(
        "--provider-set",
        choices=tuple(PROVIDER_SETS.keys()),
        default="atlas-22",
        help=(
            "named provider scope to audit (default: atlas-22; "
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


def _exact_scope(providers: tuple[str, ...]) -> tuple[str, ...]:
    """Extend exact-head checks to the Atlas integrator gitlinks."""
    return tuple(dict.fromkeys((*providers, *INTEGRATOR_REPOS)))


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
                        "require_clean_checkouts": bool(args.require_clean_checkouts),
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
                        "require_clean_checkouts": bool(args.require_clean_checkouts),
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
        exact_scope = (
            _exact_scope(providers)
            if (args.exact_heads or args.require_clean_checkouts)
            else providers
        )
        if args.exact_heads:
            issues.extend(_exact_head_issues(exact_scope, args.exact_head_workers))
        if args.require_clean_checkouts:
            issues.extend(_clean_checkout_issues(exact_scope))
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
                    "provider_count": _structural_provider_count(providers),
                    "exact_heads": bool(args.exact_heads),
                    "require_clean_checkouts": bool(args.require_clean_checkouts),
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
    print(
        f"- {_structural_provider_count(providers)} providers present and active in .gitmodules"
    )
    print(f"- {AUDIT_ID} closed across root records")
    print(f"- naming normalization retained: {NAME_NORMALIZATION}")
    if args.exact_heads:
        print("- committed provider gitlinks match current remote origin defaults")
        print(
            "- integrator gitlinks match current remote origin defaults: "
            + ", ".join(INTEGRATOR_REPOS)
        )
    if args.require_clean_checkouts:
        print("- initialized provider checkouts match committed gitlinks and are clean")
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
