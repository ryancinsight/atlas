"""Pin `canonical_stack_root` in `.githooks/stack-root.sh`, which both root hooks source."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

from root_hook_support import (
    FIXTURE_PROCESS_TIMEOUT_SECONDS, STACK_ROOT, fixture_environment, git, init_separate_git_dir,
)


def separate_git_dir_repository(
    environment: dict[str, str], worktree: Path, metadata: Path,
) -> None:
    """`init_separate_git_dir` with an empty root commit, so a lane can branch from it."""
    init_separate_git_dir(environment, worktree, metadata)
    git(environment, worktree, "commit", "-q", "--allow-empty", "-m", "root")


def distant_metadata(root: Path) -> Path:
    """A metadata directory five levels below `root`.

    The resolver's search from the metadata reaches `root` only at its fifth
    ancestor, so a test that puts a worktree under `root` is decided by the
    search from the lane.
    """
    return root.joinpath("g1", "g2", "g3", "g4", "g5") / "repo.git"


def msys_path(path: Path) -> str:
    """`path` as Git Bash spells it, its drive letter a leading `/c`; unchanged off Windows."""
    if os.name != "nt":
        return str(path)
    drive, rest = os.path.splitdrive(str(path))
    return "/" + drive[0].lower() + rest.replace("\\", "/")


def windows_short_path(path: Path) -> str | None:
    """`path` with its 8.3 short names, or None off Windows and where none can be made."""
    if os.name != "nt":
        return None
    import ctypes

    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer))
    return buffer.value if 0 < length < len(buffer) else None


def link_directory(link: Path, target: Path) -> None:
    """`link` as a link to the directory `target`: a symbolic link, or on Windows a junction.

    A junction needs no privilege, and Git and `cd -P` resolve it as they do a
    symbolic link.
    """
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=True, capture_output=True, timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
        )
    else:
        link.symlink_to(target, target_is_directory=True)


def canonical_root(
    environment: dict[str, str], directory: Path, scratch: Path, **extra: str,
) -> subprocess.CompletedProcess:
    """`canonical_stack_root` from `.githooks/stack-root.sh`, as a hook calls it.

    The hook passes Git's top level for its own directory, so this does too.
    The driver is a script file: `bash -c` halves the backslashes of its
    argument on Windows, which breaks the resolver's own path handling.
    """
    toplevel = git(environment, directory, "rev-parse", "--show-toplevel").stdout.strip()
    driver = scratch / "resolve.sh"
    driver.write_bytes(b'. "$1"\ncanonical_stack_root "$2"\n')
    return subprocess.run(
        ["bash", str(driver), STACK_ROOT.as_posix(), toplevel],
        cwd=toplevel, env=dict(environment, **extra), capture_output=True, text=True,
        timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
    )


class StackRootTests(unittest.TestCase):
    def assertResolves(self, result: subprocess.CompletedProcess, expected: Path) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(os.path.samefile(result.stdout.strip(), expected), result.stdout)

    def test_a_checkout_is_its_own_canonical_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = fixture_environment()
            repo = root / "atlas"
            repo.mkdir()
            git(environment, repo, "init", "-q", "-b", "main")

            self.assertResolves(canonical_root(environment, repo, root), repo)

    def test_a_linked_lane_resolves_to_the_main_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = fixture_environment()
            repo = root / "atlas"
            repo.mkdir()
            git(environment, repo, "init", "-q", "-b", "main")
            git(environment, repo, "commit", "-q", "--allow-empty", "-m", "root")
            lane = root / "lane"
            git(environment, repo, "worktree", "add", "-q", "-b", "lane", str(lane))

            self.assertResolves(canonical_root(environment, lane, root), repo)

    def test_a_separate_git_dir_lane_resolves_to_the_canonical_worktree(self) -> None:
        """Only a scan of the ancestors can name the worktree, as its `.git` is a file."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = fixture_environment()
            worktree = root / "checkouts" / "canonical"
            separate_git_dir_repository(environment, worktree, root / "metadata" / "repo.git")
            lane = root / "lane"
            git(environment, worktree, "worktree", "add", "-q", "-b", "lane", str(lane))
            configured = git(
                environment, worktree, "config", "--get", "core.worktree", check=False,
            )
            self.assertEqual(configured.stdout, "", "the layout must leave `core.worktree` unset")

            self.assertResolves(canonical_root(environment, lane, root), worktree)

    def test_core_worktree_names_a_canonical_root_no_scan_reaches(self) -> None:
        """The scan looks six directories down; a configured worktree needs no scan."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = fixture_environment()
            worktree = root.joinpath(*"abcdefgh") / "canonical"
            metadata = root / "metadata" / "repo.git"
            separate_git_dir_repository(environment, worktree, metadata)
            lane = root / "lane"
            git(environment, worktree, "worktree", "add", "-q", "-b", "lane", str(lane))
            git(environment, lane, "--git-dir", str(metadata), "config", "core.worktree", str(worktree))

            self.assertResolves(canonical_root(environment, lane, root), worktree)

    def test_a_crlf_git_file_resolves_the_canonical_worktree(self) -> None:
        """Git accepts a CRLF `.git` file, so the resolver must match its path.

        A carriage return left on the `gitdir:` line matches no worktree, and
        the search then finds none. A match returns at the first ancestor;
        otherwise the search ends at `GIT_CEILING_DIRECTORIES`, which the test
        sets to the fixture's parent, so a failed match is a failed assertion
        within seconds.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = fixture_environment()
            worktree = root / "checkouts" / "canonical"
            separate_git_dir_repository(environment, worktree, root / "metadata" / "repo.git")
            lane = root / "lane"
            git(environment, worktree, "worktree", "add", "-q", "-b", "lane", str(lane))
            gitfile = worktree / ".git"
            lines = gitfile.read_bytes().decode("utf-8").splitlines()
            self.assertEqual(len(lines), 1, lines)
            # Git for Windows marks the file hidden, which refuses a rewrite
            # in place.
            gitfile.unlink()
            gitfile.write_bytes((lines[0] + "\r\n").encode("utf-8"))
            self.assertTrue(gitfile.read_bytes().endswith(b"\r\n"))
            git(environment, worktree, "rev-parse", "--git-dir")
            # Resolved, since the temporary directory may be a short name.
            ceiling = str(root.resolve().parent)

            self.assertResolves(
                canonical_root(environment, lane, root, GIT_CEILING_DIRECTORIES=ceiling), worktree,
            )

    def test_a_lane_inside_the_canonical_worktree_resolves(self) -> None:
        """`<project>/.claude/worktrees/<name>`: the worktree's parent is the lane's fourth ancestor.

        The search from the lane finds the worktree there and no sooner, so a
        resolver that bounds its search at three ancestors fails.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = fixture_environment()
            worktree = root / "project"
            separate_git_dir_repository(environment, worktree, distant_metadata(root))
            lane = worktree / ".claude" / "worktrees" / "task"
            git(environment, worktree, "worktree", "add", "-q", "-b", "task", str(lane))

            self.assertResolves(canonical_root(environment, lane, root), worktree)

    def test_a_harness_lane_far_from_the_canonical_worktree_resolves(self) -> None:
        """`<base>/<home>/.codex/worktrees/<id>/<project>`, the main tree elsewhere under `<base>`.

        `<base>` is the lane's fifth ancestor, so a resolver that bounds its
        search at four ancestors fails.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = fixture_environment()
            worktree = root / "main" / "project"
            separate_git_dir_repository(environment, worktree, distant_metadata(root))
            lane = root / "h1" / ".codex" / "worktrees" / "id" / "project"
            git(environment, worktree, "worktree", "add", "-q", "-b", "task", str(lane))

            self.assertResolves(canonical_root(environment, lane, root), worktree)

    def refused_beyond_the_ceiling(self, ceiling_for: Callable[[Path, Path], str]) -> None:
        """A lane and its metadata under `<root>/ceiling`, whose canonical worktree lies above it.

        Both ancestor searches reach the worktree, which sits under `<root>`,
        only by entering the ceiling, so a resolver that ignores the ceiling
        resolves it. Honoring the ceiling refuses at once, as Git's own
        discovery does. The control resolves the same layout without one.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = fixture_environment()
            worktree = root / "checkouts" / "canonical"
            separate_git_dir_repository(environment, worktree, root / "ceiling" / "metadata" / "repo.git")
            lane = root / "ceiling" / "lane"
            git(environment, worktree, "worktree", "add", "-q", "-b", "lane", str(lane))
            self.assertResolves(canonical_root(environment, lane, root), worktree)

            refused = canonical_root(
                environment, lane, root,
                GIT_CEILING_DIRECTORIES=ceiling_for(root, root / "ceiling"),
            )
            self.assertEqual(refused.returncode, 1, refused.stdout + refused.stderr)
            self.assertEqual(refused.stdout, "")

    def test_a_semicolon_list_ends_the_search_at_a_ceiling(self) -> None:
        self.refused_beyond_the_ceiling(lambda root, ceiling: f"{root / 'unrelated'};{ceiling}")

    def test_a_colon_list_ends_the_search_at_a_ceiling(self) -> None:
        self.refused_beyond_the_ceiling(
            lambda root, ceiling: f"{msys_path(root / 'unrelated')}:{msys_path(ceiling)}",
        )

    def test_a_ceiling_spelled_through_a_link_ends_the_search(self) -> None:
        def through_a_link(root: Path, ceiling: Path) -> str:
            link = root / "ceiling-link"
            link_directory(link, ceiling)
            return str(link)

        self.refused_beyond_the_ceiling(through_a_link)

    def test_a_ceiling_in_short_form_ends_the_search(self) -> None:
        """Git expands 8.3 names before it compares a ceiling; so does the resolver."""
        def short_form(_root: Path, ceiling: Path) -> str:
            short = windows_short_path(ceiling)
            if short is None or short.lower() == str(ceiling.resolve()).lower():
                self.skipTest("no distinct 8.3 spelling of the ceiling exists here")
            return short

        self.refused_beyond_the_ceiling(short_form)

    def test_a_ceiling_in_another_case_ends_the_search_on_windows(self) -> None:
        if os.name != "nt":
            self.skipTest("only Windows folds the case of a path")
        self.refused_beyond_the_ceiling(lambda _root, ceiling: str(ceiling).swapcase())


class CeilingParsingTests(unittest.TestCase):
    """`_stack_root_at_ceiling` on both hosts' spellings, whichever host runs the tests.

    The driver sets `OSTYPE` before sourcing the resolver, and no path named
    here exists, so each case is a statement about the list's syntax.
    """

    def at_ceiling(self, ostype: str, ceilings: str, directory: str) -> bool:
        with tempfile.TemporaryDirectory() as temporary:
            driver = Path(temporary) / "ceiling.sh"
            driver.write_bytes(
                b'OSTYPE="$1"\n. "$2"\nGIT_CEILING_DIRECTORIES="$3"\n'
                b'_stack_root_load_ceilings\n_stack_root_at_ceiling "$4"\n',
            )
            result = subprocess.run(
                ["bash", str(driver), ostype, STACK_ROOT.as_posix(), ceilings, directory],
                env=fixture_environment(), capture_output=True, text=True,
                timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
            )
        self.assertIn(result.returncode, (0, 1), result.stdout + result.stderr)
        return result.returncode == 0

    def test_a_windows_list_is_semicolon_separated(self) -> None:
        self.assertTrue(self.at_ceiling("msys", "C:/stack-root-a;D:/stack-root-b", "D:/stack-root-b"))
        self.assertFalse(self.at_ceiling("msys", "C:/stack-root-a;D:/stack-root-b", "D:/stack-root-c"))

    def test_a_windows_drive_colon_is_no_separator(self) -> None:
        self.assertTrue(self.at_ceiling("msys", "C:/stack-root-a", "C:/stack-root-a"))
        self.assertFalse(self.at_ceiling("msys", "C:/stack-root-a", "C:"))

    def test_a_windows_path_compares_across_slashes_and_case(self) -> None:
        self.assertTrue(self.at_ceiling("msys", r"C:\Stack-Root-A\Inner", "c:/stack-root-a/inner"))

    def test_a_msys_colon_list_is_split_at_every_colon(self) -> None:
        self.assertTrue(self.at_ceiling("msys", "/c/stack-root-a:/d/stack-root-b", "/d/stack-root-b"))

    def test_a_posix_list_is_colon_separated(self) -> None:
        self.assertTrue(self.at_ceiling("linux-gnu", "/stack-root-a:/stack-root-b", "/stack-root-b"))
        self.assertFalse(self.at_ceiling("linux-gnu", "/stack-root-a:/stack-root-b", "/stack-root-c"))

    def test_a_posix_single_letter_top_level_directory_is_not_a_drive(self) -> None:
        """`/c/work` is a directory under `/c`, not drive C: and so never rewritten."""
        self.assertTrue(self.at_ceiling("linux-gnu", "/c/stack-root-work", "/c/stack-root-work"))
        self.assertFalse(self.at_ceiling("linux-gnu", "/c/stack-root-work", "c:/stack-root-work"))

    def test_a_posix_path_keeps_its_case(self) -> None:
        self.assertFalse(self.at_ceiling("linux-gnu", "/Stack-Root-A", "/stack-root-a"))


if __name__ == "__main__":
    unittest.main()
