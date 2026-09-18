#!/usr/bin/env python3
"""The `.githooks/pre-push` trampoline runs origin's default hook, not the
checkout's.

`core.hooksPath=.githooks` resolves inside the working tree, so the gate
that runs on a push is whatever branch the shared tree happens to have
checked out -- under concurrent agents sharing one tree, routinely a peer's.
On 2026-09-18 the tree held `foundation-f3-correction-2026-09-10`, whose
`.githooks/pre-push` predated a pushed-range fix and refused three valid
pushes (ATLAS-HOOKS-FOLLOW-CHECKOUT-2026-09-18).

These tests drive the real, shipped `.githooks/pre-push` prelude in fixture
git repositories: everything up to and including the
`_atlas_hook_trampoline "$@" || exit 1` line is the production trampoline
exactly as committed, with a stub body appended so the test can tell which
copy ran without depending on the gitlink/debt/budget gates below it.
"""

from __future__ import annotations

import pathlib
import stat
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".githooks" / "pre-push"
ZERO = "0" * 40
PRELUDE_END = '_atlas_hook_trampoline "$@" || exit 1\n'

_IDENT = ["-c", "user.email=t@t", "-c", "user.name=t"]


def _prelude() -> str:
    """The production trampoline text, verbatim, up to its dispatch line."""
    text = SCRIPT.read_text(encoding="utf-8")
    marker = text.find(PRELUDE_END)
    if marker == -1:
        raise AssertionError(
            f"{SCRIPT} no longer contains the trampoline dispatch line "
            f"{PRELUDE_END!r}; this fixture pins the real file, not a copy"
        )
    return text[: marker + len(PRELUDE_END)]


def _git(*argv: str, cwd: pathlib.Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(cwd), *_IDENT, *argv],
        check=check,
        capture_output=True,
        text=True,
    )


def _write_hook(repo: pathlib.Path, body: str) -> None:
    hook = repo / ".githooks" / "pre-push"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(_prelude() + body, encoding="utf-8", newline="\n")
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)


# Stub bodies distinguish which copy actually ran; each also proves argv and
# stdin arrived intact, since the trampoline's job is to pass both through.
HOOK_A_BODY = (
    'echo "HOOK-A-RAN args=$*" >&2\n'
    'while IFS= read -r line; do echo "HOOK-A-STDIN:$line" >&2; done\n'
    "exit 0\n"
)
HOOK_B_BODY = (
    'echo "HOOK-B-RAN" >&2\n'
    "exit 1\n"
)


def _run_hook(repo: pathlib.Path, args: list[str], stdin: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["bash", str(repo / ".githooks" / "pre-push"), *args],
        input=stdin.encode("utf-8"),
        cwd=str(repo),
        capture_output=True,
    )
    return proc.returncode, proc.stderr.decode("utf-8", errors="replace")


class StaleCheckoutDefersToOriginTestCase(unittest.TestCase):
    """Acceptance fixture: origin carries hook A, the checkout carries an
    older hook B, and A runs."""

    def _repo(self, tmp: pathlib.Path) -> pathlib.Path:
        repo = tmp / "clone"
        upstream = tmp / "upstream.git"
        subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
        _git("config", "user.email", "t@t", cwd=repo)
        _git("config", "user.name", "t", cwd=repo)

        # main carries hook A -- the version that must run.
        _write_hook(repo, HOOK_A_BODY)
        _git("add", "-A", cwd=repo)
        _git("commit", "-q", "-m", "seed with hook A", cwd=repo)

        subprocess.run(
            ["git", "init", "-q", "-b", "main", "--bare", str(upstream)], check=True
        )
        _git("remote", "add", "origin", str(upstream), cwd=repo)
        _git("push", "-q", "origin", "HEAD:main", cwd=repo)
        _git("remote", "set-head", "origin", "--auto", cwd=repo)

        # feat branches off main, then regresses to an older hook B --
        # exactly the shared-tree scenario: the checked-out branch's copy
        # predates the fix that origin's default branch already carries.
        _git("checkout", "-q", "-b", "feat", cwd=repo)
        _write_hook(repo, HOOK_B_BODY)
        _git("add", "-A", cwd=repo)
        _git("commit", "-q", "-m", "regress to hook B", cwd=repo)
        return repo

    def test_the_checked_out_older_hook_defers_to_origin_default(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-hook-trampoline-") as tmp:
            repo = self._repo(pathlib.Path(tmp))
            code, err = _run_hook(
                repo,
                ["origin", "git@example:atlas.git"],
                "refs/heads/feat 1111111111111111111111111111111111111111 "
                f"refs/heads/feat {ZERO}\n",
            )
            self.assertEqual(code, 0, err)
            self.assertIn("HOOK-A-RAN", err)
            self.assertNotIn("HOOK-B-RAN", err)

    def test_args_and_stdin_pass_through_to_the_deferred_hook(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-hook-trampoline-") as tmp:
            repo = self._repo(pathlib.Path(tmp))
            code, err = _run_hook(
                repo,
                ["origin", "git@example:atlas.git"],
                "refs/heads/feat 1111111111111111111111111111111111111111 "
                f"refs/heads/feat {ZERO}\n",
            )
            self.assertEqual(code, 0, err)
            self.assertIn("HOOK-A-RAN args=origin git@example:atlas.git", err)
            self.assertIn(
                "HOOK-A-STDIN:refs/heads/feat "
                f"1111111111111111111111111111111111111111 refs/heads/feat {ZERO}",
                err,
            )


class MatchingCheckoutFallsThroughTestCase(unittest.TestCase):
    """When the checkout already matches origin's default hook, the file
    runs its own body directly -- no fetch, no re-exec, no recursion."""

    def test_a_checkout_already_matching_origin_runs_in_place(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-hook-trampoline-") as tmp:
            repo = pathlib.Path(tmp) / "clone"
            upstream = pathlib.Path(tmp) / "upstream.git"
            subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
            _git("config", "user.email", "t@t", cwd=repo)
            _git("config", "user.name", "t", cwd=repo)
            _write_hook(repo, HOOK_A_BODY)
            _git("add", "-A", cwd=repo)
            _git("commit", "-q", "-m", "seed with hook A", cwd=repo)
            subprocess.run(
                ["git", "init", "-q", "-b", "main", "--bare", str(upstream)],
                check=True,
            )
            _git("remote", "add", "origin", str(upstream), cwd=repo)
            _git("push", "-q", "origin", "HEAD:main", cwd=repo)
            _git("remote", "set-head", "origin", "--auto", cwd=repo)

            code, err = _run_hook(repo, ["origin", "url"], f"a b c {ZERO}\n")
            self.assertEqual(code, 0, err)
            self.assertIn("HOOK-A-RAN", err)


class UnresolvableOriginFailsClosedTestCase(unittest.TestCase):
    """No `origin/HEAD` and no `origin/main` refuses the push instead of
    silently running whatever the checkout holds."""

    def test_missing_origin_ref_blocks_the_push(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-hook-trampoline-") as tmp:
            repo = pathlib.Path(tmp) / "clone"
            subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
            _git("config", "user.email", "t@t", cwd=repo)
            _git("config", "user.name", "t", cwd=repo)
            # A hook that would happily pass if it ran -- proving the
            # refusal comes from the trampoline, not from the stub body.
            _write_hook(repo, HOOK_A_BODY)
            _git("add", "-A", cwd=repo)
            _git("commit", "-q", "-m", "no origin configured", cwd=repo)

            code, err = _run_hook(repo, ["origin", "url"], f"a b c {ZERO}\n")
            self.assertNotEqual(code, 0)
            self.assertIn("BLOCKED", err)
            self.assertNotIn("HOOK-A-RAN", err)


if __name__ == "__main__":
    unittest.main()
