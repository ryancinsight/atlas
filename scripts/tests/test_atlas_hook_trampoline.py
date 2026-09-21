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


def _atlas_root_derivation() -> str:
    """The production `atlas_root` derivation from the gate body below the
    trampoline, verbatim (from the `atlas_root=` assignment up to, but not
    including, the following `binary=` line).

    Extracted rather than hardcoded so this fixture tracks whatever the
    shipped file currently does: pinned to the vulnerable
    `dirname "${BASH_SOURCE[0]}"` form, a body built from this derivation
    resolves the wrong root the moment the trampoline re-execs it through
    process substitution (`${BASH_SOURCE[0]}` becomes the `/dev/fd/NN`
    descriptor, not this file's on-disk path) -- reproducing
    ATLAS-HOOKS-FOLLOW-CHECKOUT-2026-09-18's observed
    `/dev/tools/gitlink-coherence/Cargo.toml does not exist` failure exactly.
    Pinned to the fixed `git rev-parse --show-toplevel` form, the same body
    resolves correctly regardless of re-exec, since `exec` never changes the
    working directory git already set to the repo root.
    """
    text = SCRIPT.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines) if line.startswith("atlas_root="))
    end = next(i for i in range(start, len(lines)) if lines[i].startswith("binary="))
    return "".join(lines[start:end])


def _root_reading_body() -> str:
    """A stub gate body using the production root derivation to read
    `tools/marker` relative to the resolved root -- test (a)'s fixture body.
    """
    return (
        _atlas_root_derivation()
        + 'if [ -r "${atlas_root}/tools/marker" ]; then\n'
        + '    echo "MARKER:$(cat "${atlas_root}/tools/marker")" >&2\n'
        + "    exit 0\n"
        + "else\n"
        + '    echo "MARKER-MISSING atlas_root=${atlas_root}" >&2\n'
        + "    exit 1\n"
        + "fi\n"
    )


def _git(*argv: str, cwd: pathlib.Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(cwd), *_IDENT, *argv],
        check=check,
        capture_output=True,
        text=True,
    )


def _write_hook(repo: pathlib.Path, body: str) -> None:
    _write_hook_at(repo / ".githooks" / "pre-push", body)


def _write_hook_at(hook: pathlib.Path, body: str) -> None:
    """Like `_write_hook`, but at an arbitrary path -- for fixtures where the
    file actually invoked (a `core.hooksPath` override) is not the checkout's
    `.githooks/pre-push`.
    """
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
# Reports the invoking file's own `BASH_SOURCE[0]` -- the observable that
# distinguishes "ran in place" from "re-exec'd": a re-exec via
# `bash <(git cat-file ...)` replaces it with the process-substitution
# descriptor (`/dev/fd/NN` and similar), never the on-disk hook path.
SELF_PATH_REPORT_BODY = (
    'echo "SELF_PATH:${BASH_SOURCE[0]}" >&2\n'
    "exit 0\n"
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


class ReExecPreservesRepoRootTestCase(unittest.TestCase):
    """ATLAS-HOOKS-FOLLOW-CHECKOUT-2026-09-18 follow-up (a): the default
    branch's hook is re-exec'd via `bash <(git cat-file -p "$blob_sha")`, a
    process substitution -- so `${BASH_SOURCE[0]}` inside it is a transient
    `/dev/fd/NN` descriptor, not this file's on-disk path. A gate body that
    derives `atlas_root` from `dirname "${BASH_SOURCE[0]}"` (the production
    code before this fix) resolves `/dev` there instead of the repository
    root, and every path built from it -- including the observed
    `/dev/tools/gitlink-coherence/Cargo.toml does not exist` -- breaks with
    it. This drives the actual production derivation (`_atlas_root_derivation`),
    so it fails against the unfixed file and passes once `atlas_root` is
    derived from `git rev-parse --show-toplevel` instead.
    """

    def test_the_reexecuted_hook_resolves_the_repo_root_correctly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-hook-trampoline-") as tmp:
            tmp_path = pathlib.Path(tmp)
            repo = tmp_path / "clone"
            upstream = tmp_path / "upstream.git"
            subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
            _git("config", "user.email", "t@t", cwd=repo)
            _git("config", "user.name", "t", cwd=repo)

            # main carries the hook that must run: the production root
            # derivation, reading a file relative to the resolved root.
            _write_hook(repo, _root_reading_body())
            marker_dir = repo / "tools"
            marker_dir.mkdir(parents=True, exist_ok=True)
            (marker_dir / "marker").write_text("present\n", encoding="utf-8")
            _git("add", "-A", cwd=repo)
            _git("commit", "-q", "-m", "seed with root-reading hook", cwd=repo)

            subprocess.run(
                ["git", "init", "-q", "-b", "main", "--bare", str(upstream)],
                check=True,
            )
            _git("remote", "add", "origin", str(upstream), cwd=repo)
            _git("push", "-q", "origin", "HEAD:main", cwd=repo)
            _git("remote", "set-head", "origin", "--auto", cwd=repo)

            # feat regresses to an older hook -- the mismatch that makes the
            # trampoline re-exec origin's committed copy instead of running
            # the checkout's own (stale) file.
            _git("checkout", "-q", "-b", "feat", cwd=repo)
            _write_hook(repo, HOOK_B_BODY)
            _git("add", "-A", cwd=repo)
            _git("commit", "-q", "-m", "regress to hook B", cwd=repo)

            code, err = _run_hook(
                repo,
                ["origin", "git@example:atlas.git"],
                "refs/heads/feat 1111111111111111111111111111111111111111 "
                f"refs/heads/feat {ZERO}\n",
            )
            self.assertEqual(code, 0, err)
            self.assertIn("MARKER:present", err)
            self.assertNotIn("HOOK-B-RAN", err)


class HooksPathOverrideComparesTheExecutingFileTestCase(unittest.TestCase):
    """ATLAS-HOOKS-FOLLOW-CHECKOUT-2026-09-18 follow-up (b): the trampoline
    must compare the file actually executing against origin's default
    branch, not the checkout's `.githooks/pre-push` -- so a
    `core.hooksPath` override pointing elsewhere is judged correctly. Before
    this fix, `self_sha` was hashed from `${root}/.githooks/pre-push`
    regardless of which file was invoked, so an override already matching
    origin still triggered a spurious re-exec whenever the checkout's own
    `.githooks/pre-push` happened to differ (exactly this stack's routine
    state under concurrent agents).
    """

    def test_hooks_path_override_already_matching_origin_runs_in_place(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-hook-trampoline-") as tmp:
            tmp_path = pathlib.Path(tmp)
            repo = tmp_path / "clone"
            upstream = tmp_path / "upstream.git"
            subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
            _git("config", "user.email", "t@t", cwd=repo)
            _git("config", "user.name", "t", cwd=repo)

            # main carries the self-path-reporting hook -- this is what
            # origin's default branch must serve.
            _write_hook(repo, SELF_PATH_REPORT_BODY)
            _git("add", "-A", cwd=repo)
            _git("commit", "-q", "-m", "seed with self-path-reporting hook", cwd=repo)

            subprocess.run(
                ["git", "init", "-q", "-b", "main", "--bare", str(upstream)],
                check=True,
            )
            _git("remote", "add", "origin", str(upstream), cwd=repo)
            _git("push", "-q", "origin", "HEAD:main", cwd=repo)
            _git("remote", "set-head", "origin", "--auto", cwd=repo)

            # feat regresses the checkout's own .githooks/pre-push to an
            # older, unrelated version -- exactly test (a)'s stale-checkout
            # scenario, and this stack's routine state under concurrent
            # agents: the checked-out branch's copy differs from what is
            # currently origin's default.
            _git("checkout", "-q", "-b", "feat", cwd=repo)
            _write_hook(repo, HOOK_B_BODY)
            _git("add", "-A", cwd=repo)
            _git("commit", "-q", "-m", "regress checkout's own copy", cwd=repo)

            # The file actually invoked -- a `core.hooksPath` override
            # elsewhere in the tree -- already carries the exact bytes of
            # origin's current default-branch blob. It is never committed:
            # only its on-disk presence at the invoked path matters.
            override = repo / ".githooks-current" / "pre-push"
            _write_hook_at(override, SELF_PATH_REPORT_BODY)

            proc = subprocess.run(
                ["bash", str(override), "origin", "git@example:atlas.git"],
                input=(
                    "refs/heads/feat 1111111111111111111111111111111111111111 "
                    f"refs/heads/feat {ZERO}\n"
                ).encode("utf-8"),
                cwd=str(repo),
                capture_output=True,
            )
            err = proc.stderr.decode("utf-8", errors="replace")
            self.assertEqual(proc.returncode, 0, err)
            self.assertNotIn("HOOK-B-RAN", err)
            self.assertIn("SELF_PATH:", err)
            # No re-exec happened: the reported path is the real on-disk
            # override, never a process-substitution descriptor -- proving
            # the comparison used the executing file, not the checkout's
            # (deliberately mismatched) `.githooks/pre-push`.
            reported = err.split("SELF_PATH:", 1)[1].splitlines()[0].strip()
            self.assertNotIn("fd/", reported)
            self.assertIn("current", reported)


if __name__ == "__main__":
    unittest.main()
