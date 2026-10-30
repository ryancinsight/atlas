import contextlib
import io
import os
import py_compile
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import process_tree  # noqa: E402
import python_source_loader as loader  # noqa: E402


LOADER = SCRIPTS / "python_source_loader.py"


def _write(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8", newline="\n")


def _poison_bytecode(path: Path, cached_source: str) -> None:
    source = path.read_bytes()
    cached = cached_source.encode()
    if len(source) != len(cached):
        raise AssertionError("fixture sources must have equal lengths")
    original = path.stat()
    path.write_bytes(cached)
    os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
    py_compile.compile(
        str(path),
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP,
    )
    path.write_bytes(source)
    os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))


class PythonSourceLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.left = self.root / "left.py"
        self.right = self.root / "right.py"
        self.owner = self.root / "owner.py"
        self.script = self.root / "tool.py"
        _write(self.left, 'VALUE = "left-source"\n')
        _write(self.right, 'VALUE = "right-source"\n')
        _write(
            self.owner,
            'import left\nimport right\nVALUE = f"{left.VALUE}|{right.VALUE}|owner-source"\n',
        )
        _write(self.script, 'import owner\nimport sys\nprint(f"{owner.VALUE}|{sys.argv[1]}|tool-source")\n')

    def test_executes_declared_source_despite_valid_stale_bytecode(self) -> None:
        _poison_bytecode(self.left, 'VALUE = "left-cached"\n')
        _poison_bytecode(self.right, 'VALUE = "right-cached"\n')
        _poison_bytecode(
            self.owner,
            'import left\nimport right\nVALUE = f"{left.VALUE}|{right.VALUE}|owner-cached"\n',
        )
        _poison_bytecode(
            self.script,
            'import owner\nimport sys\nprint(f"{owner.VALUE}|{sys.argv[1]}|tool-cached")\n',
        )
        poison = self.root / "poison"
        poison.mkdir()
        _write(poison / "left.py", 'VALUE = "left-poison"\n')
        _write(poison / "right.py", 'VALUE = "right-poison"\n')
        _write(poison / "owner.py", 'VALUE = "owner-poison"\n')

        result = process_tree.run(
            [
                sys.executable,
                str(LOADER),
                "--module",
                f"owner={self.owner}",
                "--module",
                f"left={self.left}",
                "--module",
                f"right={self.right}",
                str(self.script),
                "input-sensitive",
            ],
            env={**os.environ, "PYTHONPATH": str(poison)},
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.decode().splitlines(),
            ["left-source|right-source|owner-source|input-sensitive|tool-source"],
        )

    def test_rejects_duplicate_module_bindings(self) -> None:
        result = process_tree.run(
            [
                sys.executable,
                str(LOADER),
                "--module",
                f"left={self.left}",
                "--module",
                f"left={self.right}",
                str(self.script),
            ],
            timeout=30,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"module names must be unique", result.stderr)

    def test_rejects_reserved_main_module_binding(self) -> None:
        previous = sys.modules["__main__"]

        with self.assertRaisesRegex(loader.argparse.ArgumentTypeError, "reserved for the target"):
            loader._module_argument(f"__main__={self.left}")

        self.assertIs(sys.modules["__main__"], previous)
        result = process_tree.run(
            [
                sys.executable,
                str(LOADER),
                "--module",
                f"__main__={self.left}",
                str(self.script),
            ],
            timeout=30,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"__main__ is reserved for the target script", result.stderr)

    def test_declared_module_has_standard_location_metadata(self) -> None:
        _write(
            self.left,
            "from pathlib import Path\n"
            "VALUE = (Path(__file__).name, __spec__.origin, "
            "type(__loader__).__name__, __package__)\n",
        )
        _write(self.script, "import left\nprint(repr(left.VALUE))\n")

        result = process_tree.run(
            [sys.executable, str(LOADER), "--module", f"left={self.left}", str(self.script)],
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.decode().splitlines(),
            [repr((self.left.name, str(self.left.resolve()), "_SourceFinder", ""))],
        )

    def test_loads_real_process_tree_from_declared_sources(self) -> None:
        _write(
            self.script,
            "import process_tree\nimport sys\nfrom pathlib import Path\n"
            "result = process_tree.run([sys.executable, '-c', 'print(37)'], timeout=30)\n"
            "print(Path(process_tree.__file__).name, result.stdout.decode().strip())\n",
        )

        result = process_tree.run(
            [
                sys.executable,
                str(LOADER),
                "--module",
                f"process_tree={SCRIPTS / 'process_tree.py'}",
                "--module",
                f"darwin_process={SCRIPTS / 'darwin_process.py'}",
                "--module",
                f"windows_process={SCRIPTS / 'windows_process.py'}",
                str(self.script),
            ],
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().splitlines(), ["process_tree.py 37"])

    def test_preserves_direct_main_module_semantics(self) -> None:
        source = """from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar
import sys
marker = 29
@dataclass
class Item:
    marker: ClassVar[int] = 13
    value: int = 7
print(Item(13))
print(sys.modules[__name__].marker)
"""
        _write(self.script, source)
        direct = process_tree.run([sys.executable, str(self.script)], timeout=30)
        loaded = process_tree.run([sys.executable, str(LOADER), str(self.script)], timeout=30)

        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertEqual(loaded.returncode, 0, loaded.stderr)
        self.assertEqual(loaded.stdout, direct.stdout)
        self.assertEqual(loaded.stdout.decode().splitlines(), ["Item(value=13)", "29"])

    def test_preserves_relative_argv_zero(self) -> None:
        _write(self.script, "import sys\nprint(sys.argv[0])\n")

        result = process_tree.run(
            [sys.executable, str(LOADER), self.script.name], cwd=self.root, timeout=30
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().splitlines(), [self.script.name])

    def test_failure_restores_import_blocking_entry(self) -> None:
        name = "blocked_module"
        previous = sys.modules.get(name, loader._MISSING)
        self.addCleanup(
            lambda: sys.modules.pop(name, None)
            if previous is loader._MISSING
            else sys.modules.__setitem__(name, previous)
        )
        cases = {"syntax": "not valid Python !", "runtime": "raise RuntimeError('stop')\n"}
        for case, source in cases.items():
            with self.subTest(case=case):
                sys.modules[name] = None
                path = self.root / f"{case}.py"
                _write(path, source)
                _write(self.script, f"import {name}\n")
                with self.assertRaises((SyntaxError, RuntimeError)):
                    loader._execute(str(self.script), [], [(name, path)])
                self.assertIn(name, sys.modules)
                self.assertIsNone(sys.modules[name])

    def test_preserves_import_cycles_and_prior_module(self) -> None:
        name = "left"
        previous = object()
        sys.modules[name] = previous
        self.addCleanup(sys.modules.pop, name, None)
        _write(self.left, 'import right\nVALUE = f"left:{right.VALUE}"\n')
        _write(self.right, 'import left\nVALUE = f"right:{left.__name__}"\n')
        _write(self.script, 'import left\nprint(left.VALUE)\n')

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            loader._execute(
                str(self.script),
                [],
                [("right", self.right), ("left", self.left)],
            )

        self.assertEqual(output.getvalue().splitlines(), ["left:right:left"])
        self.assertIs(sys.modules[name], previous)


if __name__ == "__main__":
    unittest.main()
