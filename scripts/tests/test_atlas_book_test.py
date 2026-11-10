import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest


SCRIPT = Path(__file__).parents[1] / "atlas-book-test.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("atlas_book_test", SCRIPT)
assert SPEC and SPEC.loader
book_test = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(book_test)


class BookArtifactSelectionTests(unittest.TestCase):
    def test_real_graph_tests_values_and_excludes_stale_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._fixture(root, expected=18)
            book_test._run(
                ["cargo", "generate-lockfile", "--manifest-path", str(root / "Cargo.toml")],
                cwd=root,
                timeout=60,
            )
            stale = root / "target/debug/deps/libstale-deadbeef.rlib"
            stale.parent.mkdir(parents=True, exist_ok=True)
            stale.write_bytes(b"not a Cargo artifact")
            stages = root / "stages"
            stages.mkdir()
            report = book_test.execute(
                root / "Cargo.toml", "book-root", "book_root", root / "book",
                build_timeout=180, test_timeout=120, temp_root=stages,
            )
            names = [item["basename"] for item in report["artifacts"]]
            shared = [item for item in report["artifacts"] if "shared" in item["package_id"]]
            macros = [item for item in report["artifacts"] if "book-macro" in item["package_id"]]
            self.assertEqual(2, len(shared))
            self.assertEqual(2, len({item["basename"] for item in shared}))
            self.assertTrue(any(name.endswith((".dll", ".dylib", ".so")) for name in names))
            self.assertEqual(1, len(macros))
            self.assertNotIn(stale.name, names)
            self.assertFalse(Path(report["stage"]).exists())
            self.assertEqual([], list(stages.iterdir()))

            self._chapter(root, expected=19)
            with self.assertRaisesRegex(book_test.BookTestError, "command exited"):
                book_test.execute(
                    root / "Cargo.toml", "book-root", None, root / "book",
                    build_timeout=180, test_timeout=120, temp_root=stages,
                )
            self.assertEqual([], list(stages.iterdir()))

    def test_rejects_malformed_missing_and_conflicting_artifacts(self) -> None:
        with self.assertRaisesRegex(book_test.BookTestError, "malformed Cargo JSON"):
            book_test._artifact_messages(b"not-json", "root 1.0.0", "root")
        with self.assertRaisesRegex(book_test.BookTestError, "expected one library"):
            book_test._package({"packages": [{"name": "root", "id": "id", "targets": []}]}, "root", None)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            stage = root / "stage"
            stage.mkdir()
            missing = {"path": root / "absent.rlib", "package_id": "id", "target": "root", "fresh": False}
            with self.assertRaisesRegex(book_test.BookTestError, "missing or non-regular"):
                book_test._stage([missing], stage)
            left = root / "left/same.rlib"
            right = root / "right/same.rlib"
            left.parent.mkdir()
            right.parent.mkdir()
            left.write_bytes(b"left")
            right.write_bytes(b"right")
            records = [dict(missing, path=left), dict(missing, path=right)]
            with self.assertRaisesRegex(book_test.BookTestError, "conflicting Cargo artifacts"):
                book_test._stage(records, stage)

    def test_timeout_retires_descendants_and_cleans_stage(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            artifact = root / "libroot.rlib"
            artifact.write_bytes(b"artifact")
            stages = root / "stages"
            stages.mkdir()
            child = "import threading; print('ready', flush=True); threading.Event().wait()"
            parent = textwrap.dedent(
                f"""
                import subprocess, sys, threading
                process = subprocess.Popen([sys.executable, '-c', {child!r}], stdout=subprocess.PIPE, text=True)
                assert process.stdout.readline().strip() == 'ready'
                threading.Event().wait()
                """
            )
            with self.assertRaises(book_test.process_tree.ProcessTreeTimeout):
                book_test._stage_and_run(
                    [{"path": artifact, "package_id": "id", "target": "root", "fresh": False}],
                    lambda _stage: [sys.executable, "-c", parent],
                    cwd=root,
                    timeout=1,
                    temp_root=stages,
                )
            self.assertEqual([], list(stages.iterdir()))

    @staticmethod
    def _write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")

    def _fixture(self, root: Path, expected: int) -> None:
        self._write(root / "Cargo.toml", """
            [workspace]
            resolver = "3"
            members = ["root", "macro"]
            exclude = ["shared-one", "shared-two"]
        """)
        self._write(root / "root/Cargo.toml", """
            [package]
            name = "book-root"
            version = "0.1.0"
            edition = "2024"
            [lib]
            name = "book_root"
            [dependencies]
            shared_one = { package = "shared", path = "../shared-one" }
            shared_two = { package = "shared", path = "../shared-two" }
            book-macro = { path = "../macro" }
        """)
        self._write(root / "root/src/lib.rs", """
            use book_macro::identity;
            #[identity]
            pub fn value() -> u32 { shared_one::value() + shared_two::value() }
        """)
        for directory, version, value in (("shared-one", "1.0.0", 7), ("shared-two", "2.0.0", 11)):
            self._write(root / directory / "Cargo.toml", f"""
                [package]
                name = "shared"
                version = "{version}"
                edition = "2024"
            """)
            self._write(root / directory / "src/lib.rs", f"pub fn value() -> u32 {{ {value} }}")
        self._write(root / "macro/Cargo.toml", """
            [package]
            name = "book-macro"
            version = "0.1.0"
            edition = "2024"
            [lib]
            proc-macro = true
        """)
        self._write(root / "macro/src/lib.rs", """
            extern crate proc_macro;
            use proc_macro::TokenStream;
            #[proc_macro_attribute]
            pub fn identity(_: TokenStream, item: TokenStream) -> TokenStream { item }
        """)
        self._write(root / "book/book.toml", "[book]\ntitle = \"Artifact test\"\n")
        self._write(root / "book/src/SUMMARY.md", "# Summary\n\n- [Test](test.md)\n")
        self._chapter(root, expected)

    def _chapter(self, root: Path, expected: int) -> None:
        self._write(root / "book/src/test.md", f"""
            # Test

            ```rust
            extern crate book_root;
            assert_eq!(book_root::value(), {expected});
            ```
        """)


if __name__ == "__main__":
    unittest.main()
