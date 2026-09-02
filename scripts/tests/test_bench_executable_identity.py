#!/usr/bin/env python3
"""Tests for bench_executable_identity.py on synthesized ELF64 files.

The gate's contract: sections the CPU executes (`SHF_EXECINSTR`) and `.rodata`
decide; build-path artefacts (`.strtab`, `.note.gnu.build-id`, `.comment`) may
differ freely; a non-ELF input is malformed (exit 2), never "differs".
"""

from __future__ import annotations

import importlib.util
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bench_executable_identity.py"
SPEC = importlib.util.spec_from_file_location("bench_executable_identity", SCRIPT)
identity = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = identity
SPEC.loader.exec_module(identity)

SHF_ALLOC, SHF_EXECINSTR = 0x2, 0x4
SHT_PROGBITS, SHT_STRTAB = 1, 3


def elf64(sections: dict[str, tuple[int, bytes]]) -> bytes:
    """A minimal little-endian ELF64 image: header, section bodies, shstrtab, headers."""
    names = [""] + list(sections) + [".shstrtab"]
    shstrtab = b"\x00" + b"".join(n.encode() + b"\x00" for n in names[1:])
    name_offsets = {}
    cursor = 1
    for n in names[1:]:
        name_offsets[n] = cursor
        cursor += len(n) + 1
    body = bytearray(b"\x00" * 64)
    offsets = {}
    for n, (_flags, data) in sections.items():
        offsets[n] = len(body)
        body += data
    offsets[".shstrtab"] = len(body)
    body += shstrtab
    shoff = len(body)
    entries = [(0, 0, 0, 0, 0)]
    for n, (flags, data) in sections.items():
        entries.append((name_offsets[n], SHT_PROGBITS, flags, offsets[n], len(data)))
    entries.append((name_offsets[".shstrtab"], SHT_STRTAB, 0, offsets[".shstrtab"], len(shstrtab)))
    for name, typ, flags, offset, size in entries:
        body += struct.pack("<IIQQQQIIQQ", name, typ, flags, 0, offset, size, 0, 0, 1, 0)
    header = bytearray(64)
    header[:4] = b"\x7fELF"
    header[4], header[5], header[6] = 2, 1, 1  # ELF64, little-endian, version
    struct.pack_into("<HHIQQQIHHHHHH", header, 16, 2, 0x3E, 1, 0, 0, shoff, 0, 64, 0, 0, 64, len(entries), len(entries) - 1)
    body[:64] = header
    return bytes(body)


BASE = {".text": (SHF_ALLOC | SHF_EXECINSTR, b"\x55\x48\x89\xe5\xc3"), ".rodata": (SHF_ALLOC, b"table-v1"),
        ".strtab": (0, b"\x00_ZN6apollo1a17h0123456789abcdefE\x00"), ".comment": (0, b"rustc 1.97.0")}


def write(directory: Path, name: str, sections: dict) -> Path:
    path = directory / name
    path.write_bytes(elf64(sections))
    return path


class IdentityTests(unittest.TestCase):
    def test_build_path_artifacts_do_not_decide(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-elf-") as tmp:
            a = write(Path(tmp), "a", BASE)
            b = write(Path(tmp), "b", {**BASE, ".strtab": (0, b"\x00_ZN6apollo1a17hfedcba9876543210E\x00"),
                                       ".comment": (0, b"rustc 1.97.0 from another dir")})
            differs, rows = identity.compare(a, b)
        self.assertFalse(differs)
        self.assertTrue(any("differs (not code)" in r for r in rows))

    def test_a_text_change_decides(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-elf-") as tmp:
            a = write(Path(tmp), "a", BASE)
            b = write(Path(tmp), "b", {**BASE, ".text": (SHF_ALLOC | SHF_EXECINSTR, b"\x55\x48\x89\xe5\x90\xc3")})
            differs, rows = identity.compare(a, b)
        self.assertTrue(differs)
        self.assertTrue(any(".text" in r and "DIFFERS" in r for r in rows))

    def test_a_rodata_change_decides(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-elf-") as tmp:
            a = write(Path(tmp), "a", BASE)
            b = write(Path(tmp), "b", {**BASE, ".rodata": (SHF_ALLOC, b"table-v2")})
            self.assertTrue(identity.compare(a, b)[0])

    def test_exit_codes_distinguish_identical_differs_and_malformed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-elf-") as tmp:
            a = write(Path(tmp), "a", BASE)
            b = write(Path(tmp), "b", {**BASE, ".text": (SHF_ALLOC | SHF_EXECINSTR, b"\xc3")})
            bad = Path(tmp) / "bad"
            bad.write_bytes(b"MZ not an elf")
            run = lambda x, y: subprocess.run([sys.executable, str(SCRIPT), str(x), str(y)], capture_output=True,
                                              encoding="utf-8", errors="replace").returncode
            self.assertEqual(run(a, a), identity.EXIT_IDENTICAL)
            self.assertEqual(run(a, b), identity.EXIT_DIFFERS)
            self.assertEqual(run(a, bad), identity.EXIT_MALFORMED)


if __name__ == "__main__":
    unittest.main()
