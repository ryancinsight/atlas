#!/usr/bin/env python3
"""Tests for source-tree identity."""

from __future__ import annotations

import ctypes
import hashlib
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from atlas_build_identity_test_support import (
    BuildIdentityError,
    BuildIdentityFixture,
    artifact_record,
    build_workflow,
    check_workflow,
    git,
    identity,
    init_repo,
    lease_is_held,
    package_target_lease_path,
    records,
    write_script,
)


class SourceIdentityTestCase(BuildIdentityFixture):
    def test_unchanged_tracked_files_use_the_committed_tree_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        first = identity.source_identity(self.root)
        second = identity.source_identity(self.root)

        self.assertFalse(first.dirty)
        self.assertEqual(second.tree_digest, first.tree_digest)

    def test_a_dirty_tree_is_not_identified_by_revision_alone(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        before = identity.source_identity(self.root)
        (self.root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        after = identity.source_identity(self.root)
        self.assertTrue(after.dirty)
        self.assertNotEqual(before.tree_digest, after.tree_digest)

    def test_assume_unchanged_does_not_hide_compiler_visible_source_changes(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        source_file = self.root / "src/lib.rs"
        git(self.root, "update-index", "--assume-unchanged", "src/lib.rs")
        original_stat = source_file.stat()
        before = identity.source_identity(self.root)
        source_file.write_bytes(b"fn main(){ }\n")
        os.utime(
            source_file,
            ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
        )

        after = identity.source_identity(self.root)

        self.assertEqual(git(self.root, "status", "--porcelain"), "")
        self.assertTrue(after.dirty)
        self.assertNotEqual(after.tree_digest, before.tree_digest)

    def test_same_size_edit_with_restored_timestamp_is_detected(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        source_file = self.root / "src/lib.rs"
        backdated = 1_600_000_000_000_000_000
        os.utime(source_file, ns=(backdated, backdated))
        git(self.root, "update-index", "--refresh")
        original_stat = source_file.stat()
        before = identity.source_identity(self.root)
        source_file.write_bytes(b"fn main(){ }\n")
        os.utime(
            source_file,
            ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
        )

        after = identity.source_identity(self.root)

        self.assertEqual(source_file.stat().st_size, original_stat.st_size)
        self.assertEqual(source_file.stat().st_mtime_ns, original_stat.st_mtime_ns)
        self.assertEqual(git(self.root, "status", "--porcelain"), "")
        self.assertTrue(after.dirty)
        self.assertNotEqual(after.tree_digest, before.tree_digest)

    def test_diff_presentation_configuration_does_not_change_tree_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        source_file = self.root / "src" / "café.rs"
        source_file.write_bytes(b"pub const VALUE: u8 = 1;\n")
        git(self.root, "add", "src/café.rs")
        git(self.root, "commit", "-q", "-m", "add unicode source")
        source_file.write_bytes(b"pub const VALUE: u8 = 2;\n")

        git(self.root, "config", "core.quotePath", "true")
        quoted_diff = git(self.root, "diff", "HEAD", "--binary")
        quoted_identity = identity.source_identity(self.root)
        git(self.root, "config", "core.quotePath", "false")
        plain_diff = git(self.root, "diff", "HEAD", "--binary")
        plain_identity = identity.source_identity(self.root)

        self.assertNotEqual(quoted_diff, plain_diff)
        self.assertEqual(quoted_identity, plain_identity)

    def test_an_ignored_path_does_not_change_the_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        lock = self.root / "Cargo.lock"
        lock.write_text("# committed\n", encoding="utf-8")
        git(self.root, "add", "Cargo.lock")
        git(self.root, "commit", "-qm", "lock")
        before = identity.source_identity(self.root, ignored_paths=(lock,))
        lock.write_text("# rewritten by the gate\n", encoding="utf-8")
        self.assertEqual(identity.source_identity(self.root, ignored_paths=(lock,)), before)
        self.assertTrue(identity.source_identity(self.root).dirty)
        (self.root / "src/lib.rs").write_text("fn main() { let _c = 1; }\n", encoding="utf-8")
        self.assertTrue(identity.source_identity(self.root, ignored_paths=(lock,)).dirty)

    def test_an_ignored_path_outside_the_source_tree_is_rejected(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with self.assertRaises(BuildIdentityError):
            identity.source_identity(
                self.root, ignored_paths=(self.base / "elsewhere.lock",)
            )

    @unittest.skipIf(os.name == "nt", "creating file symlinks may require Windows privileges")
    def test_a_source_symlink_cannot_escape_the_identified_tree(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        outside = self.base / "outside.rs"
        outside.write_bytes(b"pub const VALUE: u8 = 1;\n")
        (self.root / "src" / "external.rs").symlink_to(outside)

        with self.assertRaisesRegex(BuildIdentityError, "escapes the identified tree"):
            identity.source_identity(self.root)

    def test_check_record_revalidates_source_after_artifact_hash(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        built = self.build(source_token="same")
        artifact = artifact_record(
            {"debug/deps/libdemo-abcdef.rlib": hashlib.sha256(b"same").hexdigest()}
        )

        def hash_and_mutate(*_arguments: object) -> dict[str, object]:
            (self.root / "src/lib.rs").write_bytes(b"fn main() { let value = 2; }\n")
            return artifact

        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.object(check_workflow, "artifact_identity", side_effect=hash_and_mutate),
        ):
            code, value = check_workflow.check_record(
                self.root,
                "demo",
                self.target,
                artifact_paths=[self.artifact],
                manifest=self.root / "Cargo.toml",
                command=[sys.executable, str(self.build_script)],
            )
        self.assertEqual(built.status, "rebuilt")
        self.assertEqual(code, 2)
        self.assertEqual(value["status"], "stale")

    @unittest.skipUnless(os.name == "nt", "Git checkout conversion is Windows-specific")
    def test_clean_autocrlf_checkout_hashes_compiler_visible_bytes(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        before = identity.source_identity(self.root)
        converted = self.base / "autocrlf checkout"
        subprocess.run(
            ["git", "clone", "--quiet", "--no-checkout", str(self.root), str(converted)],
            check=True,
            capture_output=True,
            timeout=30,
        )
        git(converted, "config", "core.autocrlf", "true")
        git(converted, "checkout", "--quiet", "HEAD")
        eol = git(converted, "ls-files", "--eol", "--", "src/lib.rs")
        self.assertIn("w/crlf", eol)

        after = identity.source_identity(converted)
        self.assertTrue(after.dirty)
        self.assertNotEqual(after.tree_digest, before.tree_digest)

    def test_explicit_ignored_lockfile_does_not_change_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        lock = self.root / "Cargo.lock"
        lock.write_text("version = 4\n", encoding="utf-8")
        git(self.root, "add", "Cargo.lock")
        git(self.root, "commit", "-q", "-m", "lock")
        before = identity.source_identity(self.root, ignored_paths=(lock,))
        lock.write_text("version = 4\nchanged\n", encoding="utf-8")
        after = identity.source_identity(self.root, ignored_paths=(lock,))
        self.assertEqual(after.tree_digest, before.tree_digest)
        self.assertFalse(after.dirty)

    def test_ignored_source_files_are_hashed_and_can_be_explicitly_excluded(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        (self.root / ".gitignore").write_bytes(b"generated.rs\n")
        git(self.root, "add", ".gitignore")
        git(self.root, "commit", "-q", "-m", "ignore generated source")
        clean = identity.source_identity(self.root)
        generated = self.root / "generated.rs"
        generated.write_bytes(b"first\n")
        before = identity.source_identity(self.root)
        original_stat = generated.stat()
        generated.write_bytes(b"other\n")
        os.utime(generated, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        after = identity.source_identity(self.root)
        self.assertEqual(generated.stat().st_size, original_stat.st_size)
        self.assertEqual(generated.stat().st_mtime_ns, original_stat.st_mtime_ns)
        self.assertTrue(after.dirty)
        self.assertNotEqual(before.tree_digest, after.tree_digest)
        excluded = identity.source_identity(
            self.root, ignored_paths=(self.root / "generated.rs",)
        )
        self.assertFalse(excluded.dirty)
        self.assertEqual(excluded.tree_digest, clean.tree_digest)

    def test_source_changes_during_artifact_hash_are_not_recorded(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        source = self.root / "src/lib.rs"
        previous = self.build(source_token="previous")
        previous_record = previous.record_path.read_bytes()
        self.clean_log.unlink()
        real_artifact_identity = build_workflow.artifact_identity
        hash_calls = 0

        def hash_and_mutate(*arguments: object, **keywords: object) -> dict[str, object]:
            nonlocal hash_calls
            result = real_artifact_identity(*arguments, **keywords)
            hash_calls += 1
            if hash_calls == 2:
                source.write_bytes(b"fn main() { let value = 1; }\n")
            return result

        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.object(build_workflow, "artifact_identity", side_effect=hash_and_mutate),
            patch.dict(
                os.environ,
                {
                    "ARTIFACT": str(self.artifact),
                    "SOURCE_TOKEN": "during-hash",
                    "CLEAN_LOG": str(self.clean_log),
                },
            ),
        ):
            with self.assertRaisesRegex(
                BuildIdentityError,
                "source tree changed while artifacts were being hashed",
            ):
                build_workflow.run_build(
                    self.root,
                    self.root / "Cargo.toml",
                    "demo",
                    self.target,
                    [sys.executable, str(self.build_script)],
                    artifact_paths=[self.artifact],
                    clean_command=[sys.executable, str(self.clean_script)],
                )

        self.assertEqual(source.read_bytes(), b"fn main() { let value = 1; }\n")
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "during-hash")
        self.assertFalse(self.clean_log.exists())
        self.assertEqual(previous.record_path.read_bytes(), previous_record)
        self.assertEqual(hash_calls, 2)
        self.assertFalse(lease_is_held(package_target_lease_path("demo", self.target)))

    def test_source_changes_during_build_are_not_recorded(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        previous = self.build(source_token="previous")
        previous_record = previous.record_path.read_bytes()
        changed = self.root / "src/lib.rs"
        self.clean_log.unlink()
        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.dict(
                os.environ,
                {
                    "ARTIFACT": str(self.artifact),
                    "SOURCE_TOKEN": "during-build",
                    "CLEAN_LOG": str(self.clean_log),
                    "MUTATE_SOURCE": str(changed),
                },
            ),
        ):
            with self.assertRaisesRegex(
                BuildIdentityError,
                "source tree changed while the build was running",
            ):
                build_workflow.run_build(
                    self.root,
                    self.root / "Cargo.toml",
                    "demo",
                    self.target,
                    [sys.executable, str(self.build_script)],
                    artifact_paths=[self.artifact],
                    clean_command=[sys.executable, str(self.clean_script)],
                )

        self.assertEqual(
            changed.read_bytes().replace(b"\r\n", b"\n"),
            b"changed during build\n",
        )
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "during-build")
        self.assertFalse(self.clean_log.exists())
        self.assertEqual(previous.record_path.read_bytes(), previous_record)
        self.assertFalse(lease_is_held(package_target_lease_path("demo", self.target)))

    def test_target_files_do_not_change_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        before = identity.source_identity(self.root)
        target = self.root / "target"
        target.mkdir()
        (target / "artifact.rlib").write_text("generated", encoding="utf-8")
        identity_value = identity.source_identity(self.root, (target,))
        self.assertFalse(identity_value.dirty)
        self.assertEqual(identity_value.tree_digest, before.tree_digest)
        with self.assertRaises(BuildIdentityError):
            identity.build_spec(self.root, "demo", self.root, "debug", "host", "")

    @unittest.skipUnless(os.name == "nt", "Windows short paths are platform-specific")
    def test_target_lease_scope_unifies_short_and_long_windows_paths(self) -> None:
        long_target = self.base / "target directory"
        long_target.mkdir()
        short_buffer = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetShortPathNameW(
            str(long_target), short_buffer, len(short_buffer)
        )
        if not length or short_buffer.value.casefold() == str(long_target).casefold():
            self.skipTest("the filesystem does not provide an 8.3 alias")
        short_target = Path(short_buffer.value)

        self.assertEqual(
            package_target_lease_path("demo", long_target),
            package_target_lease_path("demo", short_target),
        )

    def test_clean_filter_output_changes_identity_while_git_stays_clean(self) -> None:
        self.root.mkdir()
        source_dir = self.root / "src"
        source_dir.mkdir()
        source_file = source_dir / "lib.rs"
        source_file.write_bytes(b"pub const VALUE: u32 = 1;\n")
        (self.root / ".gitattributes").write_text("src/lib.rs filter=source\n", encoding="utf-8")
        filter_script = self.base / "filter.py"
        write_script(
            filter_script,
            "import re, sys\n"
            "data = sys.stdin.buffer.read()\n"
            "data = re.sub(rb'= \\d+', b'= 1', data)\n"
            "sys.stdout.buffer.write(data)\n",
        )
        git(self.root, "init", "-q")
        git(self.root, "config", "core.autocrlf", "false")
        git(self.root, "config", "user.name", "Atlas test")
        git(self.root, "config", "user.email", "atlas-test@example.invalid")
        git(
            self.root,
            "config",
            "filter.source.clean",
            f'"{sys.executable}" "{filter_script}"',
        )
        git(self.root, "add", ".")
        git(self.root, "commit", "-q", "-m", "source")
        self.assertEqual(git(self.root, "status", "--porcelain"), "")
        self.assertEqual(git(self.root, "diff", "HEAD", "--", "src/lib.rs"), "")
        before = identity.source_identity(self.root)
        source_file.write_bytes(b"pub const VALUE: u32 = 2;\n")
        self.assertEqual(git(self.root, "status", "--porcelain"), "")
        self.assertEqual(git(self.root, "diff", "HEAD", "--", "src/lib.rs"), "")
        after = identity.source_identity(self.root)
        self.assertTrue(after.dirty)
        self.assertNotEqual(after.tree_digest, before.tree_digest)

    def test_ignored_input_inside_initialized_submodule_changes_parent_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        dependency = self.base / "dependency"
        init_repo(dependency, "pub fn value() -> u8 { 1 }\n")
        (dependency / ".gitignore").write_text("generated.rs\n", encoding="utf-8")
        git(dependency, "add", ".gitignore")
        git(dependency, "commit", "-q", "-m", "ignore generated input")
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
        before = identity.source_identity(self.root)
        generated = self.root / "vendor" / "dependency" / "generated.rs"
        generated.write_text("pub const VALUE: u8 = 1;\n", encoding="utf-8")
        self.assertNotIn("vendor/dependency", git(self.root, "status", "--porcelain"))
        after = identity.source_identity(self.root)
        self.assertTrue(after.dirty)
        self.assertNotEqual(after.tree_digest, before.tree_digest)

    def test_staged_submodule_addition_tracks_initialized_child_sources(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        dependency = self.base / "dependency"
        init_repo(dependency, "pub fn value() -> u8 { 1 }\n")
        (dependency / ".gitignore").write_text("generated.rs\n", encoding="utf-8")
        git(dependency, "add", ".gitignore")
        git(dependency, "commit", "-q", "-m", "ignore generated source")
        before_addition = identity.source_identity(self.root)
        git(
            self.root,
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            str(dependency),
            "vendor/dependency",
        )
        after_addition = identity.source_identity(self.root)
        generated = self.root / "vendor" / "dependency" / "generated.rs"
        generated.write_bytes(b"pub const GENERATED: u8 = 1;\n")

        after = identity.source_identity(self.root)

        self.assertTrue(after_addition.dirty)
        self.assertNotEqual(before_addition.tree_digest, after_addition.tree_digest)
        self.assertNotEqual(after_addition.tree_digest, after.tree_digest)
        self.assertTrue(after.dirty)

        git(self.root, "submodule", "deinit", "--force", "--", "vendor/dependency")
        uninitialized_addition = identity.source_identity(self.root)
        self.assertTrue(uninitialized_addition.dirty)
        self.assertNotEqual(after_addition.tree_digest, uninitialized_addition.tree_digest)

    def test_staged_submodule_removal_changes_identity_while_checkout_remains(self) -> None:
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
        before = identity.source_identity(self.root)
        git(self.root, "rm", "--cached", "-q", "vendor/dependency")

        after = identity.source_identity(self.root)

        self.assertTrue((self.root / "vendor/dependency/.git").exists())
        self.assertTrue(after.dirty)
        self.assertNotEqual(before.tree_digest, after.tree_digest)

    def test_staged_gitlink_pointer_does_not_hide_the_checked_out_commit(self) -> None:
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
        child = self.root / "vendor" / "dependency"
        git(child, "config", "user.name", "Atlas test")
        git(child, "config", "user.email", "atlas-test@example.invalid")
        git(self.root, "commit", "-q", "-m", "add dependency")
        clean = identity.source_identity(self.root)
        head_pointer = git(self.root, "rev-parse", "HEAD:vendor/dependency")
        child_source = child / "src" / "lib.rs"
        child_source.write_bytes(b"pub fn value() -> u8 { 2 }\n")
        git(child, "add", "src/lib.rs")
        git(child, "commit", "-q", "-m", "advance dependency")
        staged_pointer = git(child, "rev-parse", "HEAD")
        git(self.root, "add", "vendor/dependency")
        git(child, "checkout", "-q", head_pointer)

        result = identity.source_identity(self.root)

        self.assertNotEqual(head_pointer, staged_pointer)
        self.assertEqual(git(child, "rev-parse", "HEAD"), head_pointer)
        self.assertTrue(result.dirty)
        self.assertNotEqual(clean.tree_digest, result.tree_digest)
