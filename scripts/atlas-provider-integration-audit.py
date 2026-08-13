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
    "hermes",
    "iris",
)

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _submodule_block(name: str, gitmodules_text: str) -> str | None:
    pattern = (
        r"\[submodule \"repos/"
        + re.escape(name)
        + r"\"\][\s\S]*?(?=\n\[submodule|\Z)"
    )
    match = re.search(pattern, gitmodules_text)
    return match.group(0) if match else None


def _provider_activation_issues(gitmodules_text: str) -> list[str]:
    issues: list[str] = []
    for provider in REQUIRED_PROVIDERS:
        block = _submodule_block(provider, gitmodules_text)
        if block is None:
            issues.append(f"missing submodule block for repos/{provider}")
            continue
        if not re.search(r"(?m)^\s*active\s*=\s*true\s*$", block):
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


def _gitlink_commit(provider: str) -> str | None:
    """Return the committed root gitlink for one requested provider."""
    returncode, stdout, _ = _git_output(
        "ls-tree", "HEAD", "--", f"repos/{provider}"
    )
    if returncode != 0:
        return None
    fields = stdout.split()
    if len(fields) < 3 or fields[1] != "commit":
        return None
    return fields[2]


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


def _exact_head_issues() -> list[str]:
    """Return root-gitlink drift against each fetched provider default head."""
    issues: list[str] = []
    for provider in REQUIRED_PROVIDERS:
        gitlink = _gitlink_commit(provider)
        ref, remote_head, error = _provider_remote_head(provider)
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
        if not env.get(var):
            env.pop(var, None)
    return env


def _coherence_scope_issues() -> tuple[list[str], int]:
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
    findings = report.get("findings", [])
    if not isinstance(findings, list):
        return (["coherence JSON missing findings list"], 0)

    scoped_issues: list[str] = []
    out_of_scope = 0
    provider_prefixes = tuple(f"repos/{name}/" for name in REQUIRED_PROVIDERS)
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        manifest = str(finding.get("manifest", ""))
        normalized_manifest = manifest.replace("\\", "/")
        if normalized_manifest.startswith(provider_prefixes):
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    issues: list[str] = []
    if not GITMODULES.is_file():
        issues.append("missing .gitmodules")
    else:
        issues.extend(_provider_activation_issues(_read(GITMODULES)))

    for path in RECORD_FILES:
        if not path.is_file():
            issues.append(f"missing required record file: {path.name}")
    if not issues:
        issues.extend(_record_issues())
        if args.exact_heads:
            issues.extend(_exact_head_issues())
        if args.structural_only:
            out_of_scope = 0
        else:
            scoped_coherence_issues, out_of_scope = _coherence_scope_issues()
            issues.extend(scoped_coherence_issues)
    else:
        out_of_scope = 0

    if issues:
        print("provider-integration-audit: FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("provider-integration-audit: OK")
    print(
        f"- {len(REQUIRED_PROVIDERS)} providers present and active in .gitmodules"
    )
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
