#!/usr/bin/env python3
"""Enforce the committed Cargo.lock form across the Atlas stack (ADR-0021).

A member's committed `Cargo.lock` is a *standalone* artifact: it must resolve
the repository exactly as a clean checkout, CI runner, or `cargo publish`
sandbox would -- none of which see the stack `[patch]` overlay. Therefore every
git dependency the lock actually resolves must carry its `source = "git+..."`
line, and no committed lock may carry `[[patch.unused]]` residue.

The stack overlay (`scripts/atlas-stack-overlay.py`, the `[patch]` block in the
root `.cargo/config.toml`) rewrites working-tree locks on every local build: it
drops the `source` line of every patched package and appends `[[patch.unused]]`
tables. That rewrite is derived state, never an edit -- `restore` puts it back.

Modes:

    check       fail when any *committed* lock is in the overlay-stripped form
    status      same measurement, reported for committed and working copies
    staged      same rule against one member's staged locks (pre-commit hook)
    restore     revert working-tree locks whose only diff from HEAD is the
                overlay rewrite (refuses on any other difference)
    regenerate  rebuild a member's lock in standalone form, by invoking cargo
                from a directory outside the Atlas tree so the overlay is not
                discovered
    install-hooks
                per-clone bootstrap: point member `core.hooksPath` at
                scripts/git-hooks so `staged` runs on every member commit

`check` is the CI gate. It is deliberately narrow: it flags only a package that
is *present in the lock* yet locked without a source despite being declared as
a git dependency. A member with no git dependencies has nothing to flag, and a
`[workspace.dependencies]` entry no crate actually uses is legitimately absent
from the lock -- neither is a violation, and a naive `git+` line count would
misreport both.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_stack import ROOT, registered_member_names  # noqa: E402

REPOS = ROOT / "repos"
SKIP_DIRS = {"target", ".git", "node_modules"}
PATCH_UNUSED = "[[patch.unused]]"
FIRST_PARTY_HOST = "github.com/ryancinsight/"


def run(*args: str, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        args, cwd=None if cwd is None else str(cwd), capture_output=True, encoding="utf-8", errors="replace"
    )
    return proc.returncode, proc.stdout, proc.stderr


def tracked_locks(repo: Path) -> list[str]:
    code, out, _ = run("git", "-C", str(repo), "ls-files", "*Cargo.lock")
    if code != 0:
        return []
    return sorted(line.strip() for line in out.splitlines() if line.strip())


def _dep_tables(data: dict):
    for key in ("dependencies", "dev-dependencies", "build-dependencies"):
        if isinstance(data.get(key), dict):
            yield data[key]
    workspace = data.get("workspace", {})
    if isinstance(workspace.get("dependencies"), dict):
        yield workspace["dependencies"]
    for target in (data.get("target") or {}).values():
        if isinstance(target, dict):
            for key in ("dependencies", "dev-dependencies", "build-dependencies"):
                if isinstance(target.get(key), dict):
                    yield target[key]


def workspace_facts(
    ws_root: Path, nested: list[Path], repo: Path
) -> tuple[set[str], set[str], bool]:
    """Return (locally defined packages, packages declared as git deps, fixture).

    `nested` lists sibling workspace roots that own their own lock; manifests
    beneath them belong to that lock, not this one.

    `fixture` marks a workspace that depends on sibling repositories by relative
    path (`../../../hephaestus/...`). Such a workspace exists only inside a full
    Atlas checkout -- it can never resolve standalone, so the standalone-form
    rule does not apply to its lock. This is the one exemption (ADR-0021) and it
    is reported rather than skipped silently.
    """
    local: set[str] = set()
    git_deps: set[str] = set()
    fixture = False
    for manifest in ws_root.glob("**/Cargo.toml"):
        if {part.lower() for part in manifest.parts} & SKIP_DIRS:
            continue
        if any(other in manifest.parents for other in nested):
            continue
        try:
            data = tomllib.loads(manifest.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError):
            continue
        package = data.get("package")
        if isinstance(package, dict) and isinstance(package.get("name"), str):
            local.add(package["name"])
        for table in _dep_tables(data):
            for name, spec in table.items():
                if not isinstance(spec, dict):
                    continue
                if isinstance(spec.get("git"), str):
                    git_deps.add(spec.get("package", name))
                elif isinstance(spec.get("path"), str):
                    target = (manifest.parent / spec["path"]).resolve()
                    root = repo.resolve()
                    if target != root and root not in target.parents:
                        fixture = True
    return local, git_deps, fixture


def violations(lock_text: str, local: set[str], git_deps: set[str]) -> list[str]:
    """Overlay-stripping violations in one lock's text.

    Two independent signatures, both produced only by resolving under a
    `[patch]` overlay and neither reachable from a clean standalone resolve:

    1. a `[[patch.unused]]` table, and
    2. a package declared as a git dependency, present in the lock, resolved
       with no `source` -- i.e. locked as a local path package although no
       manifest in the workspace defines it.
    """
    found: list[str] = []
    try:
        data = tomllib.loads(lock_text)
    except tomllib.TOMLDecodeError as exc:
        return [f"unparseable lock: {exc}"]

    unused = lock_text.count(PATCH_UNUSED)
    if unused:
        found.append(f"{unused} [[patch.unused]] table(s): overlay residue")

    sources: dict[str, list[str | None]] = {}
    for package in data.get("package", []):
        sources.setdefault(package.get("name"), []).append(package.get("source"))

    for name in sorted(git_deps - local):
        entries = sources.get(name)
        if entries is None:
            continue  # declared but unused (e.g. an idle [workspace.dependencies] row)
        if not any(source and source.startswith("git+") for source in entries):
            found.append(f"`{name}` locked without a git source (stripped)")
    return found


def lock_units() -> list[tuple[str, str, set[str], set[str], bool]]:
    """(member, lock path relative to the member, local, git deps, is fixture)."""
    units = []
    for member in sorted(registered_member_names()):
        repo = REPOS / member
        if not repo.is_dir():
            continue
        locks = tracked_locks(repo)
        roots = [(repo / lock).parent for lock in locks]
        for lock in locks:
            ws_root = (repo / lock).parent
            nested = [r for r in roots if r != ws_root and ws_root in r.parents]
            local, git_deps, fixture = workspace_facts(ws_root, nested, repo)
            units.append((member, lock, local, git_deps, fixture))
    return units


def committed_text(repo: Path, lock: str) -> str | None:
    code, out, _ = run("git", "-C", str(repo), "show", f"HEAD:{lock}")
    return out if code == 0 else None


def cmd_check(_args) -> int:
    failures = 0
    checked = 0
    for member, lock, local, git_deps, fixture in lock_units():
        repo = REPOS / member
        text = committed_text(repo, lock)
        if text is None:
            print(f"::warning::{member}/{lock}: not readable at HEAD; skipped")
            continue
        if fixture:
            print(f"exempt (in-tree fixture, not standalone-consumable): {member}/{lock}")
            continue
        checked += 1
        for problem in violations(text, local, git_deps):
            failures += 1
            print(f"LOCK FORM VIOLATION: {member}/{lock}: {problem}")
    if failures:
        print(
            f"\n{failures} violation(s) across {checked} committed lock(s).\n"
            "A committed lock must resolve standalone: every git dependency it\n"
            "resolves carries its `source = \"git+...\"` line and no\n"
            "[[patch.unused]] residue (ADR-0021).\n"
            "Repair without touching the shared overlay:\n"
            "  python scripts/atlas-lock-form.py regenerate <member>\n"
            "Never `git add` a lock dirtied by a local build; restore it first:\n"
            "  python scripts/atlas-lock-form.py restore"
        )
        return 1
    print(f"lock form clean: {checked} committed lock(s) resolve standalone")
    return 0


def cmd_staged(args) -> int:
    """Gate one member's *staged* locks -- the member-side pre-commit hook.

    `check` guards integration; this guards the commit that would create the
    violation in the first place, which is where the churn actually escapes:
    a `git add` of a lock a local build has just rewritten.
    """
    repo = Path(args.repo or ".").resolve()
    code, out, _ = run("git", "-C", str(repo), "diff", "--cached", "--name-only")
    staged = {line.strip() for line in out.splitlines() if line.strip().endswith("Cargo.lock")}
    if code != 0 or not staged:
        return 0
    units = {
        lock: (local, deps, fixture)
        for member, lock, local, deps, fixture in lock_units()
        if (REPOS / member).resolve() == repo
    }
    failures = 0
    for lock in sorted(staged):
        if lock not in units:
            continue
        local, deps, fixture = units[lock]
        if fixture:
            continue
        blob_code, blob, _ = run("git", "-C", str(repo), "show", f":{lock}")
        if blob_code != 0:
            continue
        for problem in violations(blob, local, deps):
            failures += 1
            print(f"LOCK FORM VIOLATION (staged): {lock}: {problem}")
    if failures:
        print(
            "\nThis lock was rewritten by the stack [patch] overlay, not edited.\n"
            "Unstage it and restore the committed form:\n"
            "  git restore --staged Cargo.lock\n"
            "  python <atlas>/scripts/atlas-lock-form.py restore\n"
            "To change the lock deliberately, regenerate it outside the overlay:\n"
            "  python <atlas>/scripts/atlas-lock-form.py regenerate <member>"
        )
        return 1
    return 0


def cmd_status(_args) -> int:
    print(f"{'member/lock':<44} {'HEAD':<10} {'worktree':<10}")
    for member, lock, local, git_deps, fixture in lock_units():
        repo = REPOS / member
        head = committed_text(repo, lock)
        path = repo / lock
        work = path.read_text(encoding="utf-8") if path.exists() else None

        def verdict(text: str | None, fixture=fixture, local=local, git_deps=git_deps) -> str:
            if text is None:
                return "missing"
            if fixture:
                return "exempt"
            problems = violations(text, local, git_deps)
            if problems:
                return "STRIPPED"
            return "ok" if git_deps - local else "no-git-deps"

        print(f"{member + '/' + lock:<44} {verdict(head):<10} {verdict(work):<10}")
    return 0


def is_first_party(source: str | None) -> bool:
    return bool(source) and source.startswith("git+") and FIRST_PARTY_HOST in source.lower()


def _strip_only(head_text: str, work_text: str) -> bool:
    """True when `work_text` is exactly `head_text` put through the overlay.

    Guards `restore` against discarding real work. The eligible set is every
    package the committed lock sources from a first-party git repository -- not
    the `[patch]` table's own keys, because patching one crate to a path makes
    its whole workspace resolve by path, so siblings the overlay never names
    (`moirai-transport` beneath a patched `moirai-core`) lose their source too.

    Non-first-party packages must match exactly: name, version, and source. A
    first-party package may change version -- the local tree is routinely ahead
    of the pinned rev -- but must only ever *lose* its source, never gain one
    or move to a different rev; either of those is a real re-resolve.

    The direction matters. A working copy that *removes* overlay residue is a
    repair towards the committed form, not churn away from it; reverting it
    would throw the fix away. Churn only ever adds residue.
    """
    if work_text.count(PATCH_UNUSED) < head_text.count(PATCH_UNUSED):
        return False
    try:
        head = tomllib.loads(head_text)
        work = tomllib.loads(work_text)
    except tomllib.TOMLDecodeError:
        return False
    if head.get("version") != work.get("version"):
        return False

    eligible = {
        pkg.get("name")
        for pkg in head.get("package", [])
        if is_first_party(pkg.get("source"))
    }

    def split(data: dict):
        plain: dict[tuple[str, str], str | None] = {}
        first_party: dict[str, list[str | None]] = {}
        for pkg in data.get("package", []):
            name = pkg.get("name")
            if name in eligible:
                first_party.setdefault(name, []).append(pkg.get("source"))
            else:
                plain[(name, pkg.get("version"))] = pkg.get("source")
        return plain, first_party

    head_plain, head_fp = split(head)
    work_plain, work_fp = split(work)
    if head_plain != work_plain:
        return False
    for name, sources in work_fp.items():
        for source in sources:
            if source is None:
                continue  # replaced by the local tree: the expected rewrite
            if source not in head_fp.get(name, []):
                return False  # a rev the committed lock never pinned
    return True


def cmd_restore(_args) -> int:
    restored, kept = [], []
    for member, lock, local, git_deps, fixture in lock_units():
        repo = REPOS / member
        path = repo / lock
        head = committed_text(repo, lock)
        if head is None or not path.exists() or fixture:
            continue
        work = path.read_text(encoding="utf-8")
        if work == head:
            continue
        if violations(head, local, git_deps):
            kept.append(f"{member}/{lock} (committed lock itself violates; "
                        "the working copy may be the repair -- left alone)")
            continue
        if _strip_only(head, work):
            code, _, err = run("git", "-C", str(repo), "checkout", "--", lock)
            (restored if code == 0 else kept).append(
                f"{member}/{lock}" + ("" if code == 0 else f" (git checkout failed: {err.strip()})")
            )
        else:
            kept.append(f"{member}/{lock} (real change, left alone)")
    for line in restored:
        print(f"restored overlay churn: {line}")
    for line in kept:
        print(f"kept: {line}")
    print(f"\n{len(restored)} restored, {len(kept)} left for review")
    return 0


def _cargo_outside(manifest: Path, *extra: str) -> subprocess.CompletedProcess:
    """Resolve `manifest` with the stack overlay out of scope.

    Cargo discovers `.cargo/config.toml` upward from the *current directory*,
    not from the manifest path. Running from a scratch directory outside the
    Atlas tree is therefore what makes this resolve against git rather than the
    local working trees -- and it does so without toggling the shared overlay
    out from under concurrent peers.
    """
    with tempfile.TemporaryDirectory(prefix="atlas-lock-") as scratch:
        env = dict(os.environ)
        # Leaving the overlay's scope also leaves `[build] target-dir` behind,
        # so cargo would default to a per-member `target/` -- the cache fork
        # the shared root exists to prevent. Name the canonical shared path
        # explicitly: this is the value the config would have supplied, not an
        # override of it.
        env["CARGO_TARGET_DIR"] = str(ROOT / "target")
        return subprocess.run(
            [
                "cargo", "metadata", "--format-version", "1",
                "--manifest-path", str(manifest), *extra,
            ],
            cwd=scratch,
            capture_output=True,
            encoding="utf-8", errors="replace",
            env=env,
        )


def cmd_regenerate(args) -> int:
    """Repair locks into standalone form, then prove they resolve `--locked`.

    `cargo metadata` re-resolves only what the lock cannot supply, so a
    stripped source is restored without gratuitously advancing every unrelated
    pin -- which `cargo generate-lockfile` would do.
    """
    members = args.members or sorted(registered_member_names())
    failed = 0
    for member in members:
        manifest = REPOS / member / "Cargo.toml"
        if not manifest.is_file():
            print(f"{member}: no root Cargo.toml; skipped")
            continue
        repair = _cargo_outside(manifest)
        if repair.returncode != 0:
            failed += 1
            print(f"{member}: repair FAILED\n{repair.stderr.rstrip()}")
            continue
        verify = _cargo_outside(manifest, "--locked")
        if verify.returncode != 0:
            failed += 1
            print(f"{member}: --locked verification FAILED\n{verify.stderr.rstrip()}")
            continue
        print(f"{member}: repaired and verified (`cargo metadata --locked` ok)")
    return 1 if failed else 0


def cmd_install_hooks(_args) -> int:
    """Point every member's `core.hooksPath` at the committed guard.

    Local git config, so it is a per-clone bootstrap rather than committed
    state -- the same shape as the meta-repo's own
    `git config core.hooksPath .githooks`. A member that already sets
    `core.hooksPath` is reported and left alone: silently retargeting someone
    else's hooks would disable them.
    """
    hooks = (Path(__file__).resolve().parent / "git-hooks").as_posix()
    installed, skipped = 0, 0
    for member in sorted(registered_member_names()):
        repo = REPOS / member
        if not repo.is_dir():
            continue
        code, existing, _ = run(
            "git", "-C", str(repo), "config", "--local", "--get", "core.hooksPath"
        )
        current = existing.strip()
        if code == 0 and current and current != hooks:
            print(f"{member}: core.hooksPath already set to {current}; left alone")
            skipped += 1
            continue
        code, _, err = run(
            "git", "-C", str(repo), "config", "--local", "core.hooksPath", hooks
        )
        if code != 0:
            print(f"{member}: FAILED to set core.hooksPath: {err.strip()}")
            skipped += 1
            continue
        installed += 1
    print(f"lock-form pre-commit guard installed in {installed} member(s), {skipped} skipped")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("check").set_defaults(func=cmd_check)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("restore").set_defaults(func=cmd_restore)
    staged = sub.add_parser("staged")
    staged.add_argument("--repo", default=None)
    staged.set_defaults(func=cmd_staged)
    regen = sub.add_parser("regenerate")
    regen.add_argument("members", nargs="*")
    regen.set_defaults(func=cmd_regenerate)
    sub.add_parser("install-hooks").set_defaults(func=cmd_install_hooks)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
