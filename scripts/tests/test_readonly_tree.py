"""Fixture removal owns its tree and links, never external link targets."""

import os
import stat
import tempfile
import unittest
from pathlib import Path

from readonly_tree import clear_readonly_tree


class ReadonlyTreeTests(unittest.TestCase):
    def test_removes_owned_readonly_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            tree = Path(temporary) / "owned"
            child = tree / "nested" / "file"
            child.parent.mkdir(parents=True)
            child.write_text("owned", encoding="utf-8")
            child.chmod(0o400)
            child.parent.chmod(0o500)
            tree.chmod(0o500)
            clear_readonly_tree(tree)
            self.assertFalse(tree.exists())

    @unittest.skipUnless(os.name == "posix", "POSIX symlink and mode semantics")
    def test_dangling_and_external_links_do_not_change_external_modes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            target = outside / "target"
            target.write_text("external", encoding="utf-8")
            target.chmod(0o400)
            outside.chmod(0o500)
            tree = root / "owned"
            tree.mkdir()
            (tree / "dangling").symlink_to(outside / "absent")
            (tree / "file-link").symlink_to(target)
            (tree / "directory-link").symlink_to(outside, target_is_directory=True)
            try:
                clear_readonly_tree(tree)
                self.assertFalse(tree.exists())
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o400)
                self.assertEqual(stat.S_IMODE(outside.stat().st_mode), 0o500)
                self.assertEqual(target.read_text(encoding="utf-8"), "external")
            finally:
                outside.chmod(0o700)

    @unittest.skipUnless(os.name == "posix", "POSIX symlink semantics")
    def test_root_link_removes_only_the_link_including_a_dangling_link(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "external"
            target.mkdir()
            for destination in (target, root / "absent"):
                with self.subTest(destination=destination):
                    link = root / "owned"
                    link.symlink_to(destination, target_is_directory=True)
                    clear_readonly_tree(link)
                    self.assertFalse(link.is_symlink())
                    self.assertTrue(target.is_dir())


if __name__ == "__main__":
    unittest.main()
