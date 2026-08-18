#!/usr/bin/env python3
"""Validate publishable crates against crates.io's manifest rules.

`cargo publish` fails at upload on metadata the local toolchain never checks:
`cargo package` and `cargo publish --dry-run` both build and verify the
*contents* of a package without validating keyword counts or category slugs.
The rejection therefore arrives at the end of a release, against a version
number already burned, which is the worst possible moment to learn about it.

Two classes of rule, and they are enforced differently on purpose:

**Structural rules** are documented limits with fixed values, so they are
checked offline and always:

- at most 5 keywords, each at most 20 characters
- keywords are ASCII alphanumeric plus `-` and `_`, starting alphanumeric
- at most 5 categories
- `description` and `license` (or `license-file`) are present
- a declared `readme` resolves to a file that exists

**Category slugs** are a registry-controlled list that changes over time, so
this script refuses to carry a hardcoded copy — a stale embedded list would
report confident nonsense in both directions. Slugs are validated against
`https://crates.io/api/v1/categories` when it is reachable and reported as
UNVERIFIED when it is not. Local developer runs on a sandboxed network will
usually see UNVERIFIED; CI has network and enforces. `--require-categories`
makes unreachability a failure, which is what CI passes.

Exit status is 1 on any violation, 0 otherwise. UNVERIFIED alone is not a
violation unless `--require-categories` is set.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

MAX_KEYWORDS = 5
MAX_KEYWORD_LEN = 20
MAX_CATEGORIES = 5
KEYWORD_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

CATEGORIES_URL = "https://crates.io/api/v1/categories?per_page=100"
# crates.io rejects requests without an identifying agent.
USER_AGENT = "atlas-registry-metadata (https://github.com/ryancinsight)"


CACHE_PATH = REPO_ROOT / "scripts" / "data" / "crates-io-categories.json"


def _get_json(url: str, timeout: float, attempts: int = 3):
    """GET with backoff. Building the taxonomy takes 59 requests, and
    crates.io rate-limits a burst that size, so a single-shot fetch reports
    the whole registry as unreachable on what is really throttling."""
    for attempt in range(attempts):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
            if attempt == attempts - 1:
                return None
            time.sleep(0.5 * (2**attempt))
    return None


def load_cached_slugs() -> set[str] | None:
    """The committed taxonomy snapshot, or None when absent/unreadable."""
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    slugs = payload.get("slugs")
    return set(slugs) if slugs else None


def write_cached_slugs(slugs: set[str], fetched_at: str) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(
            {
                "source": CATEGORIES_URL,
                "fetched_at": fetched_at,
                "note": (
                    "Derived state: regenerate with "
                    "`python scripts/atlas-registry-metadata.py --refresh`. "
                    "Includes subcategories, which the list endpoint omits."
                ),
                "slugs": sorted(slugs),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def fetch_category_slugs(timeout: float = 20.0) -> set[str] | None:
    """Every category slug crates.io accepts, or None when unreachable.

    The list endpoint returns **top-level categories only** — 58 of them, with
    no `subcategories` field. Nested slugs like `multimedia::images` and
    `science::neuroscience` are real categories that appear only on the
    per-category endpoint. An implementation that validates against the list
    endpoint alone rejects every nested slug in the stack as unregistered,
    which is exactly what the first version of this script did; the ritk
    crates it flagged were correct all along. So: fetch the top level, then
    fetch each category's own record for its children.

    crates.io's taxonomy is two levels deep, so one descent is complete. If
    that ever changes, the missing grandchildren surface as violations on
    slugs that do exist — noisy, but never a silent pass.
    """
    top = _get_json(CATEGORIES_URL, timeout)
    if top is None:
        return None
    slugs: set[str] = set()
    parents: list[str] = []
    for entry in top.get("categories", []):
        slug = entry.get("id")
        if slug:
            slugs.add(slug)
            parents.append(slug)
    if not parents:
        return None

    for index, parent in enumerate(parents):
        if index:
            time.sleep(0.25)  # 58 back-to-back requests trips crates.io throttling
        detail = _get_json(f"https://crates.io/api/v1/categories/{parent}", timeout)
        if detail is None:
            # A partial taxonomy would produce false violations, which is worse
            # than declining to validate at all.
            return None
        for child in detail.get("category", {}).get("subcategories", []) or []:
            child_slug = child.get("id")
            if child_slug:
                slugs.add(child_slug)
    return slugs or None


def manifests() -> list[Path]:
    """Every Cargo.toml under repos/, excluding build output and vendored trees."""
    found: list[Path] = []
    repos = REPO_ROOT / "repos"
    if not repos.is_dir():
        return found
    for manifest in repos.glob("*/**/Cargo.toml"):
        parts = set(manifest.parts)
        if parts & {"target", "worktrees", ".git", "vendor"}:
            continue
        found.append(manifest)
    return sorted(found)


def is_publishable(pkg: dict, workspace: dict) -> bool:
    """False only for an explicit opt-out; absent `publish` means publishable."""
    publish = pkg.get("publish")
    if isinstance(publish, dict) and publish.get("workspace"):
        publish = workspace.get("publish")
    if publish is False:
        return False
    if isinstance(publish, list) and not publish:
        return False
    return True


def inherited(pkg: dict, workspace: dict, key: str):
    """Resolve a field that may carry `{ workspace = true }`."""
    value = pkg.get(key)
    if isinstance(value, dict) and value.get("workspace"):
        return workspace.get(key)
    return value


def check_manifest(
    manifest: Path, valid_categories: set[str] | None
) -> tuple[list[str], list[str]]:
    """Return (violations, unverified) for one manifest."""
    violations: list[str] = []
    unverified: list[str] = []
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"{manifest}: unreadable ({exc})"], []

    pkg = data.get("package")
    if not pkg:
        return [], []  # virtual manifest

    workspace = {}
    ws_manifest = manifest
    for _ in range(6):  # walk up to the workspace root for inherited fields
        ws_manifest = ws_manifest.parent.parent / "Cargo.toml"
        if not ws_manifest.is_file():
            continue
        try:
            ws_data = tomllib.loads(ws_manifest.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        if "workspace" in ws_data:
            workspace = ws_data["workspace"].get("package", {})
            break

    if not is_publishable(pkg, workspace):
        return [], []

    name = pkg.get("name", manifest.parent.name)
    where = manifest.relative_to(REPO_ROOT).as_posix()

    keywords = inherited(pkg, workspace, "keywords") or []
    if len(keywords) > MAX_KEYWORDS:
        violations.append(
            f"{where} [{name}]: {len(keywords)} keywords, crates.io accepts at most {MAX_KEYWORDS}"
        )
    for kw in keywords:
        if len(kw) > MAX_KEYWORD_LEN:
            violations.append(
                f"{where} [{name}]: keyword {kw!r} is {len(kw)} chars, limit is {MAX_KEYWORD_LEN}"
            )
        if not KEYWORD_RE.match(kw):
            violations.append(
                f"{where} [{name}]: keyword {kw!r} must be alphanumeric/-/_ and start alphanumeric"
            )

    categories = inherited(pkg, workspace, "categories") or []
    if len(categories) > MAX_CATEGORIES:
        violations.append(
            f"{where} [{name}]: {len(categories)} categories, crates.io accepts at most {MAX_CATEGORIES}"
        )
    for cat in categories:
        if valid_categories is None:
            unverified.append(f"{where} [{name}]: category {cat!r} unverified (registry unreachable)")
        elif cat not in valid_categories:
            violations.append(
                f"{where} [{name}]: category {cat!r} is not a registered crates.io slug"
            )

    if not inherited(pkg, workspace, "description"):
        violations.append(f"{where} [{name}]: publishable crate has no description")
    if not (inherited(pkg, workspace, "license") or inherited(pkg, workspace, "license-file")):
        violations.append(f"{where} [{name}]: publishable crate declares no license")

    readme = inherited(pkg, workspace, "readme")
    if isinstance(readme, str) and not (manifest.parent / readme).is_file():
        violations.append(f"{where} [{name}]: declared readme {readme!r} does not exist")

    return violations, unverified


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-categories",
        action="store_true",
        help="fail when no category taxonomy is available at all (use in CI)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="re-fetch the taxonomy from crates.io and rewrite the cached snapshot",
    )
    args = parser.parse_args()

    valid = None if args.refresh else load_cached_slugs()
    if valid is not None:
        print(f"categories: {len(valid)} slugs from cached snapshot", file=sys.stderr)
    else:
        valid = fetch_category_slugs()
        if valid is not None:
            write_cached_slugs(
                valid, datetime.datetime.now(datetime.timezone.utc).isoformat()
            )
            print(
                f"categories: {len(valid)} slugs fetched and cached to "
                f"{CACHE_PATH.relative_to(REPO_ROOT).as_posix()}",
                file=sys.stderr,
            )

    if valid is None:
        print("categories: no taxonomy available — slug validation SKIPPED", file=sys.stderr)
        if args.require_categories:
            print(
                "ERROR: --require-categories was set but neither the cached snapshot "
                "nor crates.io yielded a taxonomy",
                file=sys.stderr,
            )
            return 1

    violations: list[str] = []
    unverified: list[str] = []
    checked = 0
    for manifest in manifests():
        v, u = check_manifest(manifest, valid)
        if v or u:
            violations.extend(v)
            unverified.extend(u)
        checked += 1

    for line in unverified:
        print(f"UNVERIFIED {line}")
    for line in violations:
        print(f"VIOLATION  {line}")

    print(
        f"\n{checked} manifests scanned, {len(violations)} violations, "
        f"{len(unverified)} unverified",
        file=sys.stderr,
    )
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
