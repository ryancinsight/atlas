#!/usr/bin/env python3
"""A provider reached through two sources is compiled twice, and nothing says so.

The build stays green and the lock resolves under `--locked`; the two copies'
public types simply stop matching where the consumers that took different routes
meet. These tests pin the measurement and the ratchet that bounds it.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "lockfile.py"
SPEC = importlib.util.spec_from_file_location("atlas_lockfile_identity", SCRIPT)
lockfile = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lockfile
SPEC.loader.exec_module(lockfile)


def lock(*sources: str) -> str:
    """A minimal lock body carrying one `source` line per argument."""
    return "\n".join(
        f'[[package]]\nname = "p{index}"\nsource = "{source}"\n'
        for index, source in enumerate(sources)
    )


class ProviderIdentityTestCase(unittest.TestCase):
    def test_one_source_per_repository_is_not_a_fork(self) -> None:
        text = lock(
            "git+https://github.com/ryancinsight/hermes.git?rev=5a399ee#5a399ee",
            "git+https://github.com/ryancinsight/hermes.git?rev=5a399ee#5a399ee",
            "git+https://github.com/ryancinsight/leto.git#1caa846",
        )
        identities = lockfile.provider_identities(text)
        self.assertEqual(
            {name: len(sources) for name, sources in identities.items()},
            {
                "git+https://github.com/ryancinsight/hermes": 1,
                "git+https://github.com/ryancinsight/leto": 1,
            },
        )

    def test_a_pinned_and_unpinned_edge_are_two_sources(self) -> None:
        """The exact shape a unilateral pin removal produces."""
        text = lock(
            "git+https://github.com/ryancinsight/hermes.git#e6e0821",
            "git+https://github.com/ryancinsight/hermes.git?rev=5a399ee#5a399ee",
        )
        identities = lockfile.provider_identities(text)
        self.assertEqual(len(identities["git+https://github.com/ryancinsight/hermes"]), 2)

    def test_url_spelling_does_not_hide_a_fork(self) -> None:
        """`Mnemosyne` and `Mnemosyne.git` are one repository, so two revisions of
        them are one fork rather than two providers."""
        text = lock(
            "git+https://github.com/ryancinsight/Mnemosyne?rev=a07f999#a07f999",
            "git+https://github.com/ryancinsight/Mnemosyne.git?rev=af7a23a#af7a23a",
        )
        identities = lockfile.provider_identities(text)
        self.assertEqual(len(identities), 1)
        self.assertEqual(len(next(iter(identities.values()))), 2)

    def test_third_party_sources_are_not_counted(self) -> None:
        text = lock(
            "registry+https://github.com/rust-lang/crates.io-index",
            "git+https://github.com/other/thing.git?rev=aaa#aaa",
        )
        self.assertEqual(lockfile.provider_identities(text), {})


class ProviderIdentityRatchetTestCase(unittest.TestCase):
    FORKED = lock(
        "git+https://github.com/ryancinsight/hermes.git#e6e0821",
        "git+https://github.com/ryancinsight/hermes.git?rev=5a399ee#5a399ee",
        "git+https://github.com/ryancinsight/leto.git#1caa846",
    )

    def run_against(self, lock_text: str, baseline: str | None) -> int:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Cargo.lock").write_text(lock_text, encoding="utf-8")
            if baseline is not None:
                (root / lockfile.PROVIDER_IDENTITY_BASELINE_NAME).write_text(
                    baseline, encoding="utf-8"
                )
            original = lockfile.LOCKFILE
            lockfile.LOCKFILE = root / "Cargo.lock"
            try:
                return lockfile.check_provider_identity()
            finally:
                lockfile.LOCKFILE = original

    def test_absent_baseline_reports_without_failing(self) -> None:
        """A member that has never measured its graph is not failed by a guard it
        has not adopted."""
        self.assertEqual(self.run_against(self.FORKED, None), 0)

    def test_excess_above_the_baseline_fails(self) -> None:
        self.assertEqual(self.run_against(self.FORKED, "0\n"), 1)

    def test_excess_at_the_baseline_passes(self) -> None:
        self.assertEqual(self.run_against(self.FORKED, "1\n"), 0)

    def test_excess_below_the_baseline_passes(self) -> None:
        """Lowering is the ratchet's direction, so it reports rather than fails."""
        self.assertEqual(self.run_against(self.FORKED, "3\n"), 0)

    def test_a_comment_after_the_number_is_allowed(self) -> None:
        self.assertEqual(self.run_against(self.FORKED, "1  # see backlog\n"), 0)

    def test_a_malformed_baseline_fails(self) -> None:
        self.assertEqual(self.run_against(self.FORKED, "several\n"), 1)


if __name__ == "__main__":
    unittest.main()
