from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import atlas_build_package_source as package_source


def framed_digest(files: dict[str, bytes]) -> str:
    """The record format stored before the cache: framed kind, path, bytes."""
    digest = hashlib.sha256()
    for relative in sorted(files):
        for part in (b"file", relative.encode("utf-8"), files[relative]):
            digest.update(len(part).to_bytes(8, "big"))
            digest.update(part)
    return digest.hexdigest()


class PackageSourceDigestTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name).resolve()
        self.root = base / "dep-0.1.0"
        self.cache = base / "cache"
        self.files = {
            "Cargo.toml": b"[package]\nname = \"dep\"\n",
            "src/lib.rs": b"pub fn value() -> u8 { 1 }\n",
            "src/nested/mod.rs": b"pub mod inner;\n",
        }
        for relative, content in self.files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        (self.root / ".git").mkdir()
        (self.root / ".git" / "HEAD").write_bytes(b"ref: refs/heads/main\n")

    def cached(self) -> str:
        return package_source.cached_package_source_digest(self.root, self.cache)

    def entries(self) -> list[Path]:
        return sorted(self.cache.glob("*.json"))

    def test_full_read_keeps_the_recorded_format(self) -> None:
        self.assertEqual(
            package_source.package_source_digest(self.root), framed_digest(self.files)
        )

    def test_cached_digest_equals_the_full_read_and_stores_one_entry(self) -> None:
        self.assertEqual(self.cached(), framed_digest(self.files))
        self.assertEqual(len(self.entries()), 1)

    def test_unchanged_fingerprint_is_answered_without_reading(self) -> None:
        expected = self.cached()
        with patch.object(Path, "read_bytes", side_effect=AssertionError("read")):
            self.assertEqual(self.cached(), expected)

    def test_size_change_is_read_again(self) -> None:
        self.cached()
        self.files["src/lib.rs"] = b"pub fn value() -> u16 { 2 }\n"
        (self.root / "src" / "lib.rs").write_bytes(self.files["src/lib.rs"])
        self.assertEqual(self.cached(), framed_digest(self.files))

    def test_same_size_edit_with_a_new_mtime_is_read_again(self) -> None:
        self.cached()
        path = self.root / "src" / "lib.rs"
        before = path.stat()
        self.files["src/lib.rs"] = b"pub fn value() -> u8 { 7 }\n"
        path.write_bytes(self.files["src/lib.rs"])
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
        self.assertEqual(path.stat().st_size, before.st_size)
        self.assertEqual(self.cached(), framed_digest(self.files))

    def test_added_file_is_read_again(self) -> None:
        self.cached()
        self.files["build.rs"] = b"fn main() {}\n"
        (self.root / "build.rs").write_bytes(self.files["build.rs"])
        self.assertEqual(self.cached(), framed_digest(self.files))

    def test_malformed_entry_is_read_again(self) -> None:
        self.cached()
        (entry,) = self.entries()
        entry.write_text("{", encoding="utf-8")
        self.assertEqual(self.cached(), framed_digest(self.files))

    def test_entry_naming_another_root_is_not_trusted(self) -> None:
        self.cached()
        (entry,) = self.entries()
        value = json.loads(entry.read_text(encoding="utf-8"))
        value["root"] = "elsewhere"
        value["digest"] = "0" * 64
        entry.write_text(json.dumps(value), encoding="utf-8")
        self.assertEqual(self.cached(), framed_digest(self.files))

    def test_source_moving_during_the_read_stores_nothing(self) -> None:
        content_digest = package_source._content_digest

        def rewrite_while_reading(root: Path, entries: list) -> str:
            digest = content_digest(root, entries)
            (self.root / "src" / "lib.rs").write_bytes(b"pub fn value() -> u32 { 3 }\n")
            return digest

        with patch.object(package_source, "_content_digest", rewrite_while_reading):
            self.assertEqual(self.cached(), framed_digest(self.files))
        self.assertEqual(self.entries(), [])


if __name__ == "__main__":
    unittest.main()
