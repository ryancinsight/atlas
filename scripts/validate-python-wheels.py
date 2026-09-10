"""Validate the complete Python, ABI, and platform tuple set in wheel files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PLATFORMS = {
    "manylinux_2_17_x86_64": re.compile(r"(?:manylinux_2_17_x86_64|manylinux2014_x86_64)"),
    "manylinux_2_17_aarch64": re.compile(r"(?:manylinux_2_17_aarch64|manylinux2014_aarch64)"),
    "musllinux_1_2_x86_64": re.compile(r"musllinux_1_2_x86_64"),
    "musllinux_1_2_aarch64": re.compile(r"musllinux_1_2_aarch64"),
    "win_amd64": re.compile(r"win_amd64"),
    "universal2": re.compile(r"macosx_[0-9]+_[0-9]+_universal2"),
}


def parse_wheel(path: str) -> tuple[str, str, str]:
    tags = Path(path).name.removesuffix(".whl").split("-")[-3:]
    if len(tags) != 3:
        raise ValueError(f"not a wheel filename: {path}")
    python_tag, abi_tag, platform_tag = tags
    tokens = platform_tag.split(".")
    canonical = []
    for token in tokens:
        match = next((name for name, pattern in PLATFORMS.items() if pattern.fullmatch(token)), None)
        if match is None:
            raise ValueError(f"unsupported platform tag in {path}: {token}")
        canonical.append(match)
    if not canonical or len(set(canonical)) != 1:
        raise ValueError(f"incompatible compressed platform tags in {path}: {platform_tag}")
    return python_tag, "abi3t" if abi_tag == "abi3.abi3t" else abi_tag, canonical[0]


def expected(args: argparse.Namespace) -> set[tuple[str, str, str]]:
    result: set[tuple[str, str, str]] = set()
    if args.abi3:
        py = f"cp{args.abi3_python.replace('.', '')}"
        result.update((py, "abi3", platform) for platform in PLATFORMS)
    if args.cpython:
        for version in args.cpython:
            py = f"cp{version.replace('.', '')}"
            result.update((py, py, platform) for platform in PLATFORMS)
    if args.free:
        for version in args.free:
            py = f"cp{version.replace('.', '').removesuffix('t')}"
            result.update((py, f"{py}t", platform) for platform in PLATFORMS if platform in {"manylinux_2_17_x86_64", "manylinux_2_17_aarch64", "win_amd64", "universal2"})
    if args.abi3t:
        py = f"cp{args.abi3t_python.replace('.', '').removesuffix('t')}"
        result.update((py, "abi3t", platform) for platform in ("manylinux_2_17_x86_64", "manylinux_2_17_aarch64", "win_amd64", "universal2"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", action="append", required=True)
    parser.add_argument("--abi3", action="store_true")
    parser.add_argument("--abi3-python", default="3.9")
    parser.add_argument("--cpython", nargs="*", default=[])
    parser.add_argument("--free", nargs="*", default=[])
    parser.add_argument("--abi3t", action="store_true")
    parser.add_argument("--abi3t-python", default="3.15t")
    args = parser.parse_args()
    wanted = expected(args)
    try:
        actual = [parse_wheel(path) for path in args.wheel]
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    if len(actual) != len(set(actual)) or set(actual) != wanted:
        print(f"wheel tuples {actual!r} do not equal expected {sorted(wanted)!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
