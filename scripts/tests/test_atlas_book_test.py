import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest

import pytest
from scripts.tests.test_process_tree import _assert_process_inactive


SCRIPT = Path(__file__).parents[1] / "atlas-book-test.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("atlas_book_test", SCRIPT)
assert SPEC and SPEC.loader
book_test = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(book_test)


class BookArtifactSelectionTests(unittest.TestCase):
    def test_workflow_loads_tooling_from_called_revision(self) -> None:
        workflow = (Path(__file__).parents[2] / ".github/workflows/book-pages.yml").read_text()
        self.assertIn("repository: ryancinsight/atlas", workflow)
        self.assertIn("ref: ${{ fromJSON(toJSON(job)).workflow_sha }}", workflow)
        self.assertNotIn("ref: ${{ github.workflow_sha }}", workflow)

        step = workflow.split("      - name: Validate called Atlas workflow revision\n", 1)[1]
        step = step.split("\n      - name:", 1)[0]
        shell = step.split("        run: |\n", 1)[1]
        script = textwrap.dedent(shell)
        valid = "0123456789abcdef0123456789abcdef01234567"
        cases = ((valid, 0), (None, 1), ("", 1), ("main", 1))
        for revision, expected in cases:
            with self.subTest(revision=revision):
                env = os.environ.copy()
                if revision is None:
                    env.pop("CALLED_WORKFLOW_SHA", None)
                else:
                    env["CALLED_WORKFLOW_SHA"] = revision
                result = book_test.process_tree.run(
                    ["bash", "-c", script], env=env, timeout=10
                )
                self.assertEqual(expected, result.returncode)
                if expected:
                    self.assertIn(b"must be a full commit SHA", result.stderr)

    @pytest.mark.slow
    def test_real_graph_tests_values_and_excludes_stale_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._fixture(root, expected=18)
            manifest = str(root / "Cargo.toml")
            book_test._run(["cargo", "generate-lockfile", "--manifest-path", manifest], cwd=root, timeout=60)
            command = ["cargo", "metadata", "--locked", "--no-deps", "--format-version", "1",
                       "--manifest-path", manifest]
            metadata = json.loads(book_test._run(command, cwd=root, timeout=60))
            stale_dir = Path(metadata["target_directory"]) / "debug/deps"
            stale_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(prefix="libatlas_book_stale_", suffix=".rlib", dir=stale_dir, delete=False) as file:
                file.write(b"not a Cargo artifact")
                stale = Path(file.name)
            stages = root / "stages"
            stages.mkdir()
            try:
                report = book_test.execute(root / "Cargo.toml", "book-root", "book_root", root / "book",
                                           build_timeout=180, test_timeout=120, temp_root=stages)
            finally:
                stale.unlink(missing_ok=True)
            shared = [item for item in report["artifacts"] if "shared" in item["package_id"]]
            self.assertEqual(2, len(shared))
            self.assertEqual(2, len({item["basename"] for item in shared}))
            self.assertTrue(any(item["basename"].endswith((".dll", ".dylib", ".so")) for item in report["artifacts"]))
            self.assertEqual(1, sum("book-macro" in item["package_id"] for item in report["artifacts"]))
            self.assertNotIn(stale.name, [item["basename"] for item in report["artifacts"]])
            self.assertFalse(Path(report["stage"]).exists())
            self.assertEqual([], list(stages.iterdir()))

            self._chapter(root, expected=19)
            with self.assertRaisesRegex(book_test.BookTestError, "command exited"):
                book_test.execute(root / "Cargo.toml", "book-root", None, root / "book",
                                  build_timeout=180, test_timeout=120, temp_root=stages)
            self.assertEqual([], list(stages.iterdir()))

    def test_rejects_malformed_missing_and_conflicting_artifacts(self) -> None:
        with self.assertRaisesRegex(book_test.BookTestError, "malformed Cargo JSON"):
            book_test._artifact_messages(b"not-json", "root 1.0.0", "root")
        artifact = dict(reason="compiler-artifact", package_id="root 1.0.0",
                        target={"name": "root", "kind": ["lib"], "crate_types": ["lib"]},
                        filenames=["libroot.rlib"], fresh=False)
        malformed = dict(artifact, fresh="false")
        with self.assertRaisesRegex(book_test.BookTestError, "invalid fresh flag"):
            book_test._artifact_messages(json.dumps(malformed).encode(), "root 1.0.0", "root")
        non_json = json.dumps(artifact).replace('"fresh": false', '"fresh": NaN').encode()
        with self.assertRaisesRegex(book_test.BookTestError, "non-JSON constant 'NaN'"):
            book_test._artifact_messages(non_json, "root 1.0.0", "root")
        for field, value, error in (("package_id", 1, "invalid identity fields"),
                                    ("filenames", "libroot.rlib", "invalid filenames")):
            invalid = dict(artifact, **{field: value})
            with self.subTest(field=field), self.assertRaisesRegex(book_test.BookTestError, error):
                book_test._artifact_messages(json.dumps(invalid).encode(), "root 1.0.0", "root")
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
            identity = root / "descendant.json"
            child = (
                "import json,os,pathlib,sys,threading; "
                "pathlib.Path(sys.argv[1]).write_text(json.dumps({'pid':os.getpid(),'token':sys.argv[2]})); "
                "print('ready', flush=True); threading.Event().wait()"
            )
            token = "atlas-book-descendant"
            parent = textwrap.dedent(
                f"""
                import subprocess, sys, threading
                process = subprocess.Popen([sys.executable, '-c', {child!r}, {str(identity)!r}, {token!r}], stdout=subprocess.PIPE, text=True)
                assert process.stdout.readline().strip() == 'ready'
                threading.Event().wait()
                """
            )
            with self.assertRaises(book_test.process_tree.ProcessTreeTimeout):
                record = {"path": artifact, "package_id": "id", "target": "root", "fresh": False}
                book_test._stage_and_run([record], lambda _stage: [sys.executable, "-c", parent],
                                         cwd=root, timeout=1, temp_root=stages)
            self.assertEqual([], list(stages.iterdir()))
            descendant = json.loads(identity.read_text(encoding="utf-8"))
            self.assertEqual(token, descendant["token"])
            _assert_process_inactive(self, descendant["pid"])

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
            [[bin]]
            name = "book_root"
            path = "src/bin/book_root.rs"
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
        self._write(root / "root/src/bin/book_root.rs", "fn main() {}")
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
