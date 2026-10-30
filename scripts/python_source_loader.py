#!/usr/bin/env python3
"""Execute declared sibling modules from their current source bytes.

Undeclared imports retain the interpreter's normal resolution behavior.
The target owns ``__main__``; sibling declarations cannot replace it.
"""

from __future__ import annotations

import argparse
import importlib.abc
import importlib.util
import re
import sys
import types
from pathlib import Path


MODULE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_MISSING = object()


class SourceLoadError(ValueError):
    """A requested source module cannot be loaded exactly."""


def _module_argument(value: str) -> tuple[str, Path]:
    name, separator, path = value.partition("=")
    if name == "__main__":
        raise argparse.ArgumentTypeError("__main__ is reserved for the target script")
    if not separator or not MODULE_NAME.fullmatch(name) or not path:
        raise argparse.ArgumentTypeError("module must be NAME=PATH")
    return name, Path(path)


def _source(path: Path) -> tuple[Path, bytes]:
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise SourceLoadError(f"cannot resolve Python source: {path}") from error
    if path.is_symlink() or not resolved.is_file() or resolved.suffix != ".py":
        raise SourceLoadError(f"Python source must be a regular .py file: {path}")
    return resolved, resolved.read_bytes()


class _SourceFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, sources: dict[str, tuple[Path, bytes]]) -> None:
        self.sources = sources

    def find_spec(self, fullname: str, path, target=None):
        source = self.sources.get(fullname)
        if source is None:
            return None
        return importlib.util.spec_from_file_location(fullname, source[0], loader=self)

    def exec_module(self, module: types.ModuleType) -> None:
        path, source = self.sources[module.__name__]
        exec(compile(source, str(path), "exec", dont_inherit=True), module.__dict__)


def _execute(script: str, arguments: list[str], modules: list[tuple[str, Path]]) -> None:
    resolved, source = _source(Path(script))
    sources = {name: _source(path) for name, path in modules}
    previous_modules = {name: sys.modules.get(name, _MISSING) for name in sources}
    for name in sources:
        sys.modules.pop(name, None)
    finder = _SourceFinder(sources)
    sys.meta_path.insert(0, finder)
    sys.argv = [script, *arguments]
    module = types.ModuleType("__main__")
    module.__file__ = str(resolved)
    module.__package__ = None
    module.__spec__ = None
    previous = sys.modules.get("__main__", _MISSING)
    sys.modules["__main__"] = module
    try:
        exec(compile(source, str(resolved), "exec", dont_inherit=True), module.__dict__)
    finally:
        sys.meta_path.remove(finder)
        for name, previous_module in previous_modules.items():
            if previous_module is _MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous_module
        if previous is _MISSING:
            sys.modules.pop("__main__", None)
        else:
            sys.modules["__main__"] = previous


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", action="append", default=[], type=_module_argument)
    parser.add_argument("script")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    names = [name for name, _ in options.module]
    if len(names) != len(set(names)):
        raise SourceLoadError("module names must be unique")
    _execute(options.script, options.arguments, options.module)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
