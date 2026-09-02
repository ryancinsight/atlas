#!/usr/bin/env python3
"""Decide whether two benchmark executables carry the same code.

# The trap this exists for

A regression gate builds the baseline and the candidate in different
directories. Two builds of identical source from different paths are never
byte-identical: symbol-name hashes, the GNU build id, and `.strtab` follow the
build path. A whole-file `cmp` therefore always reports a difference, the gate
never short-circuits, and it goes on to time identical code — where a shared
runner's scheduler noise reads as a "replicated regression" (apollo run
33570302967: ~10% slower in every counterbalanced comparison; helios#81: a
workflow-only pull request flagged +1.7% then +0.4%, the two run orders
disagreeing in sign).

Identity is decided on what the CPU executes: every section flagged
`SHF_EXECINSTR`, plus `.rodata` (constant tables the kernels read). Symbol
tables, build ids, debug info, and relocation-only sections are reported but
do not decide.

Exit status: 0 when code is identical, 1 when any deciding section differs,
2 on a malformed input — distinct from 1 so a gate fails loudly on a bad
artifact instead of quietly scheduling measurements. Dependency-free; ELF64
section headers are parsed directly so the gate needs no binutils. Atlas owns
the one copy (consolidation_discipline); members run it from their pinned
atlas checkout, never from a vendored duplicate.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

SHT_NOBITS = 8
SHF_EXECINSTR = 0x4
DECIDING_BY_NAME = {".rodata"}
EXIT_IDENTICAL, EXIT_DIFFERS, EXIT_MALFORMED = 0, 1, 2


class MalformedExecutable(Exception):
    """The input is not an ELF64 file this script can read."""


def sections(path: Path) -> dict[str, tuple[int, bytes]]:
    """Section name → (flags, contents) for every section with file contents."""
    data = path.read_bytes()
    if data[:4] != b"\x7fELF":
        raise MalformedExecutable(f"{path}: not an ELF file")
    if data[4] != 2:
        raise MalformedExecutable(f"{path}: not ELF64")
    endian = "<" if data[5] == 1 else ">"
    shoff = struct.unpack_from(endian + "Q", data, 0x28)[0]
    shentsize, shnum, shstrndx = struct.unpack_from(endian + "HHH", data, 0x3A)
    if shnum == 0 or shstrndx >= shnum:
        raise MalformedExecutable(f"{path}: no section header string table")
    headers = []
    for index in range(shnum):
        off = shoff + index * shentsize
        name, typ, flags, _addr, offset, size = struct.unpack_from(endian + "IIQQQQ", data, off)
        headers.append((name, typ, flags, offset, size))
    strtab = headers[shstrndx][3]

    def section_name(index: int) -> str:
        end = data.index(b"\x00", strtab + index)
        return data[strtab + index:end].decode()

    return {
        section_name(name): (flags, data[offset:offset + size])
        for name, typ, flags, offset, size in headers
        if typ != SHT_NOBITS
    }


def compare(baseline: Path, candidate: Path) -> tuple[bool, list[str]]:
    """(code differs?, report rows) — deciding sections and any differing section."""
    sa, sb = sections(baseline), sections(candidate)
    code_differs = False
    rows = []
    for name in sorted(set(sa) | set(sb)):
        fa, da = sa.get(name, (0, b""))
        fb, db = sb.get(name, (0, b""))
        deciding = bool((fa | fb) & SHF_EXECINSTR) or name in DECIDING_BY_NAME
        same = da == db
        if deciding and not same:
            code_differs = True
        if deciding or not same:
            verdict = "identical" if same else ("DIFFERS" if deciding else "differs (not code)")
            rows.append(f"  {name:<24} {len(da):>9} {len(db):>9}  {verdict}")
    return code_differs, rows


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <baseline-executable> <candidate-executable>", file=sys.stderr)
        return EXIT_MALFORMED
    baseline, candidate = Path(sys.argv[1]), Path(sys.argv[2])
    try:
        code_differs, rows = compare(baseline, candidate)
    except (MalformedExecutable, OSError, struct.error, ValueError) as error:
        print(f"malformed executable: {error}", file=sys.stderr)
        return EXIT_MALFORMED
    print(f"{baseline.name}: {'CODE DIFFERS' if code_differs else 'CODE IDENTICAL'}")
    print(f"  {'section':<24} {'baseline':>9} {'candidate':>9}")
    print("\n".join(rows))
    return EXIT_DIFFERS if code_differs else EXIT_IDENTICAL


if __name__ == "__main__":
    sys.exit(main())
