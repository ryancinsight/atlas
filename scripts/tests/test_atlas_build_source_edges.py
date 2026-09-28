#!/usr/bin/env python3
"""Tests for source identity boundary cases."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from atlas_build_identity_test_support import (
    BuildIdentityError,
    BuildIdentityFixture,
    git,
    identity,
    init_repo,
    source,
)


class SourceIdentityEdgeTestCase(BuildIdentityFixture):
    def test_generated_directory_names_are_excluded_from_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        identity_before = identity.source_identity(self.root)
        generated_names = (
            "target",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
        )
        for name in generated_names:
            generated = self.root / name / "nested" / "output.bin"
            generated.parent.mkdir(parents=True)
            generated.write_bytes(name.encode())

        identity_after = identity.source_identity(self.root)

        self.assertEqual(identity_before.as_dict(), identity_after.as_dict())

    def test_deleting_distinct_tracked_files_changes_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        first_file = self.root / "src" / "first.rs"
        second_file = self.root / "src" / "second.rs"
        first_file.write_bytes(b"pub const FIRST: u8 = 1;\n")
        second_file.write_bytes(b"pub const SECOND: u8 = 2;\n")
        git(self.root, "add", "src/first.rs", "src/second.rs")
        git(self.root, "commit", "-q", "-m", "add source files")
        clean = identity.source_identity(self.root)

        first_file.unlink()
        first_deleted = identity.source_identity(self.root)
        first_file.write_bytes(b"pub const FIRST: u8 = 1;\n")
        second_file.unlink()
        second_deleted = identity.source_identity(self.root)

        self.assertTrue(first_deleted.dirty)
        self.assertTrue(second_deleted.dirty)
        self.assertNotEqual(first_deleted.tree_digest, clean.tree_digest)
        self.assertNotEqual(second_deleted.tree_digest, clean.tree_digest)
        self.assertNotEqual(first_deleted.tree_digest, second_deleted.tree_digest)

    def test_source_directory_named_target_is_included(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        source_directory = self.root / "src" / "target"
        source_directory.mkdir(exist_ok=True)
        source_file = source_directory / "mod.rs"
        source_file.write_bytes(b"pub const VALUE: u8 = 1;\n")
        git(self.root, "add", "src/target/mod.rs")
        git(self.root, "commit", "-q", "-m", "add source module")
        before = identity.source_identity(self.root)

        source_file.write_bytes(b"pub const VALUE: u8 = 2;\n")
        after = identity.source_identity(self.root)

        self.assertTrue(after.dirty)
        self.assertNotEqual(after.tree_digest, before.tree_digest)

    def test_source_read_detects_a_file_changed_during_hashing(self) -> None:
        self.root.mkdir(parents=True)
        source_file = self.root / "large-source.rs"
        source_file.write_bytes(b"A" * (2 * 1024 * 1024))
        original_fdopen = os.fdopen

        class MutatingStream:
            def __init__(self, stream: object) -> None:
                self.stream = stream
                self.mutated = False

            def __enter__(self) -> MutatingStream:
                return self

            def __exit__(self, *arguments: object) -> object:
                return self.stream.__exit__(*arguments)

            def read(self, size: int) -> bytes:
                data = self.stream.read(size)
                if not self.mutated:
                    source_file.write_bytes(b"B" * (2 * 1024 * 1024 + 1))
                    self.mutated = True
                return data

        def open_stream(descriptor: int, mode: str, *, closefd: bool) -> MutatingStream:
            return MutatingStream(original_fdopen(descriptor, mode, closefd=closefd))

        with (
            patch.object(source.os, "fdopen", side_effect=open_stream),
            self.assertRaisesRegex(BuildIdentityError, "source changed while reading"),
        ):
            source._file_state(source_file, "sha1")

    def test_source_symlink_cannot_hide_git_metadata_content(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        source_link = self.root / "src" / "generated.rs"
        metadata_target = self.root / ".git" / "generated.rs"
        class GitMetadataLink:
            def readlink(self) -> Path:
                return Path("../.git/generated.rs")

            def resolve(self, *, strict: bool) -> Path:
                return metadata_target

            def __str__(self) -> str:
                return str(source_link)

        with self.assertRaisesRegex(BuildIdentityError, "excluded content"):
            source._link_target(GitMetadataLink(), self.root, ())

    def test_source_symlink_cannot_hide_implicitly_excluded_content(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        excluded_targets = (
            self.root / "node_modules" / "package" / "source.rs",
            self.root / "__pycache__" / "module.pyc",
            self.root / "target" / "debug" / "generated.rs",
        )
        for target in excluded_targets:
            link = self.root / "src" / f"{target.parts[-2]}.rs"

            class ExcludedContentLink:
                def readlink(self) -> Path:
                    return Path(os.path.relpath(target, link.parent))

                def resolve(self, *, strict: bool) -> Path:
                    return target

                def __str__(self) -> str:
                    return str(link)

            with self.subTest(target=target), self.assertRaisesRegex(
                BuildIdentityError, "excluded content"
            ):
                source._link_target(ExcludedContentLink(), self.root, ())

    def test_removing_an_explicitly_ignored_only_child_preserves_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        generated = self.root / "generated"
        generated.mkdir()
        ignored_file = generated / "input.rs"
        ignored_file.write_bytes(b"pub const VALUE: u8 = 1;\n")
        baseline = identity.source_identity(self.root, ignored_paths=(ignored_file,))

        ignored_file.unlink()
        after_removal = identity.source_identity(self.root, ignored_paths=(ignored_file,))

        self.assertEqual(after_removal.tree_digest, baseline.tree_digest)
        self.assertEqual(after_removal.dirty, baseline.dirty)

    def test_uninitialized_committed_submodule_changes_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        dependency = self.base / "dependency"
        init_repo(dependency, "pub fn value() -> u8 { 1 }\n")
        git(
            self.root,
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            str(dependency),
            "vendor/dependency",
        )
        git(self.root, "commit", "-q", "-m", "add dependency")
        child = self.root / "vendor" / "dependency"
        git(child, "config", "core.autocrlf", "false")
        git(child, "checkout", "--force", "HEAD")
        initialized = identity.source_identity(self.root)
        git(self.root, "submodule", "deinit", "--force", "--", "vendor/dependency")

        uninitialized = identity.source_identity(self.root)

        self.assertFalse(initialized.dirty)
        self.assertTrue(uninitialized.dirty)
        self.assertNotEqual(initialized.tree_digest, uninitialized.tree_digest)


if __name__ == "__main__":
    unittest.main()
