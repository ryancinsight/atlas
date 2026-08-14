#!/usr/bin/env python3
"""Regression tests for the coeus-dist byte-identity harness PE helpers."""
from __future__ import annotations

import importlib.util
import os
import struct
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-coeus-dist-byte-identity.py"
_SPEC = importlib.util.spec_from_file_location("atlas_coeus_dist_byte_identity", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_harness = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_harness)


def _make_pe(timestamp: int = 0x12345678, checksum: int = 0xDEADBEEF) -> bytes:
    """Build a minimal valid-layout PE32+ image (nonzero headers, no sections)."""
    e_lfanew = 0x40
    pe = 0x40  # e_lfanew points at the "PE\\0\\0" signature itself here
    image = bytearray(0x200)
    struct.pack_into("<I", image, 0x3C, e_lfanew)
    image[pe:pe + 4] = b"PE\x00\x00"
    struct.pack_into("<H", image, pe + 4, 0x8664)  # machine: x64
    struct.pack_into("<H", image, pe + 6, 0)  # number of sections
    struct.pack_into("<I", image, pe + 8, timestamp)
    optional_header = pe + 0x18
    struct.pack_into("<H", image, optional_header, 0x20B)  # PE32+ magic
    struct.pack_into("<I", image, optional_header + 0x40, checksum)
    return bytes(image)


class PeNormalizationTestCase(unittest.TestCase):
    def test_offsets(self) -> None:
        data = _make_pe(timestamp=0x11111111, checksum=0x22222222)
        e_lfanew, timestamp, checksum = _harness.pe_offsets(data)
        self.assertEqual(e_lfanew, 0x40)
        self.assertEqual(timestamp, 0x48)
        self.assertEqual(checksum, 0x98)

    def test_normalize_zeroes_both_nondeterministic_fields(self) -> None:
        data = _make_pe(timestamp=0x12345678, checksum=0xDEADBEEF)
        norm = _harness.normalize_pe(data)
        _, timestamp, checksum = _harness.pe_offsets(norm)
        self.assertEqual(struct.unpack_from("<I", norm, timestamp)[0], 0)
        self.assertEqual(struct.unpack_from("<I", norm, checksum)[0], 0)

    def test_normalize_equates_otherwise_identical_images(self) -> None:
        a = _make_pe(timestamp=0x100, checksum=0xAAA)
        b = _make_pe(timestamp=0x200, checksum=0xBBB)
        self.assertNotEqual(a, b)
        self.assertEqual(_harness.normalize_pe(a), _harness.normalize_pe(b))
        self.assertEqual(_harness.sha256(_harness.normalize_pe(a)),
                         _harness.sha256(_harness.normalize_pe(b)))

    def test_normalize_preserves_other_bytes(self) -> None:
        data = _make_pe(timestamp=0x12345678, checksum=0xDEADBEEF)
        norm = _harness.normalize_pe(data)
        # Only the two 4-byte fields may differ; everything else is intact.
        diffs = [
            i for i in range(min(len(data), len(norm)))
            if data[i] != norm[i]
        ]
        _, timestamp, checksum = _harness.pe_offsets(data)
        expected = set(range(timestamp, timestamp + 4)) | set(range(checksum, checksum + 4))
        self.assertEqual(set(diffs), expected)

    def test_rejects_non_pe_input(self) -> None:
        with self.assertRaises(ValueError):
            _harness.pe_offsets(b"too short")

    def test_rejects_missing_pe_signature(self) -> None:
        data = _make_pe()
        # Corrupt the "PE\\0\\0" signature while keeping the layout intact.
        data = bytearray(data)
        data[0x40:0x44] = b"EX\x00\x00"
        with self.assertRaises(ValueError):
            _harness.pe_offsets(bytes(data))

    def test_rejects_bad_optional_header_magic(self) -> None:
        data = bytearray(_make_pe())
        struct.pack_into("<H", data, 0x40 + 0x18, 0x1234)  # not 0x10B/0x20B
        with self.assertRaises(ValueError):
            _harness.pe_offsets(bytes(data))

    def test_accepts_pe32_magic(self) -> None:
        data = bytearray(_make_pe())
        struct.pack_into("<H", data, 0x40 + 0x18, 0x10B)  # PE32 magic
        e_lfanew, timestamp, checksum = _harness.pe_offsets(bytes(data))
        self.assertEqual(timestamp, 0x48)
        self.assertEqual(checksum, 0x98)


class TargetSetsTestCase(unittest.TestCase):
    def test_default_order_is_canonical(self) -> None:
        sets = _harness.resolve_sets(None)
        self.assertEqual(list(sets), ["dist", "python", "wgpu"])

    def test_selects_subset_in_requested_order(self) -> None:
        sets = _harness.resolve_sets(["wgpu", "dist"])
        self.assertEqual(list(sets), ["wgpu", "dist"])
        pkg, test, globs = sets["wgpu"]
        self.assertEqual(pkg, "coeus-wgpu")
        self.assertEqual(test, "wgpu_ops")
        self.assertEqual(globs, ("wgpu_ops-*.exe",))

    def test_every_set_is_well_formed(self) -> None:
        for name, (pkg, test, globs) in _harness.TARGET_SETS.items():
            self.assertIsInstance(pkg, str)
            self.assertTrue(pkg)
            if test is not None:
                self.assertIsInstance(test, str)
                self.assertTrue(test)
            self.assertIsInstance(globs, tuple)
            self.assertTrue(globs)
            for g in globs:
                self.assertIsInstance(g, str)
                self.assertTrue(g)

    def test_rejects_unknown_set(self) -> None:
        with self.assertRaises(ValueError):
            _harness.resolve_sets(["dist", "bogus"])


def _make_pe_with_section(raw_size: int = 512, extra: bytes = b"") -> bytes:
    """A minimal PE32+ image with one `.text` section plus optional payload.

    `extra` is appended AFTER the fixed image (outside any section) so it does
    not disturb the PE layout.
    """
    image = bytearray(0x300)
    e_lfanew = 0x40
    struct.pack_into("<I", image, 0x3C, e_lfanew)
    image[0x40:0x44] = b"PE\x00\x00"
    struct.pack_into("<H", image, 0x44, 0x8664)  # machine x64
    struct.pack_into("<H", image, 0x46, 1)  # one section
    struct.pack_into("<H", image, 0x54, 0xF0)  # size of optional header
    struct.pack_into("<H", image, 0x58, 0x20B)  # PE32+ magic
    # section table at 0x40 + 24 + 0xF0 = 0x148
    sec = 0x148
    image[sec:sec + 8] = b".text\x00\x00\x00"
    struct.pack_into("<I", image, sec + 8, raw_size)  # virtual size
    struct.pack_into("<I", image, sec + 16, raw_size)  # raw size
    struct.pack_into("<I", image, sec + 20, 0x200)  # raw ptr
    return bytes(image) + extra


class RemapAndSectionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.worktree = Path("D:/atlas/repos/hephaestus")
        self.clone = Path("D:/atlas/target/hephaestus-gitlink")

    def test_remap_rustflags_bakes_both_checkouts_to_one_canonical(self) -> None:
        flags = _harness.remap_rustflags(self.worktree, self.clone)
        # both remaps point AT the canonical source path
        self.assertEqual(flags.count(_harness.CANONICAL_SRC.replace("/", "\\")), 2)
        self.assertIn("hephaestus-gitlink", flags)
        self.assertIn("repos", flags)
        self.assertEqual(flags.count("--remap-path-prefix="), 2)
        # determinism: same input, same flag string (needed for metadata hash)
        self.assertEqual(flags, _harness.remap_rustflags(self.worktree, self.clone))

    def test_section_raw_sizes(self) -> None:
        data = _make_pe_with_section(raw_size=1024)
        sizes = _harness.section_raw_sizes(data)
        self.assertEqual(sizes, ((".text", 1024),))

    def test_section_raw_sizes_unequal_across_images(self) -> None:
        a = _make_pe_with_section(raw_size=1024)
        b = _make_pe_with_section(raw_size=2048)
        self.assertNotEqual(_harness.section_raw_sizes(a),
                            _harness.section_raw_sizes(b))

    def test_residual_diff_count(self) -> None:
        a = b"aaaa" + b"xxxxxxxx" + b"cccc"
        b = b"aaaa" + b"yyyyyyyy" + b"cccc"
        self.assertEqual(_harness.residual_diff_count(a, b), 8)
        self.assertEqual(_harness.residual_diff_count(b"abc", b"abcd"), 1)

    def test_crate_alignment_detects_content_and_artifact_differences(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            p1, p2 = Path(d1), Path(d2)
            for root in (p1, p2):
                (root / "hephaestus-core").mkdir(parents=True)
            w = p1 / "hephaestus-core"
            c = p2 / "hephaestus-core"
            (w / "src.rs").write_text("same")
            (c / "src.rs").write_text("same")
            (w / "touched.rs").write_text("worktree")
            (c / "touched.rs").write_text("clone")
            # artifacts must be ignored
            (w / "target").mkdir()
            (w / "target" / "a.o").write_text("obj")
            (w / "__pycache__").mkdir()
            (w / "__pycache__" / "x.cpython-313.pyc").write_bytes(b"pyc")
            (c / "extra.rs").write_text("only clone")
            alignment = _harness.crate_alignment(
                p1, p2, ("hephaestus-core",)
            )["hephaestus-core"]
            self.assertEqual(alignment["content_diff"], 1)  # touched.rs
            self.assertEqual(alignment["only_clone"], 1)  # extra.rs
            self.assertEqual(alignment["only_worktree"], 0)  # artifacts ignored
            self.assertFalse(_harness.source_aligned(
                {"hephaestus-core": alignment}))

    def test_source_aligned_true_when_all_zero(self) -> None:
        self.assertTrue(_harness.source_aligned({
            "hephaestus-core": {"only_worktree": 0, "only_clone": 0, "content_diff": 0},
            "hephaestus-wgpu": {"only_worktree": 0, "only_clone": 0, "content_diff": 0},
        }))

    def _write(self, data: bytes) -> Path:
        import tempfile
        fd, name = tempfile.mkstemp(suffix=".exe")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return Path(name)

    def test_classify_pass(self) -> None:
        a = self._write(_make_pe_with_section())
        b = self._write(_make_pe_with_section())
        verdict, detail = _harness.classify_binary(a.read_bytes(), b.read_bytes(), self.clone)
        self.assertEqual(verdict, "PASS")
        for p in (a, b):
            p.unlink(missing_ok=True)

    def test_classify_fail_on_section_size(self) -> None:
        a = self._write(_make_pe_with_section(raw_size=512))
        b = self._write(_make_pe_with_section(raw_size=1024))
        verdict, _ = _harness.classify_binary(a.read_bytes(), b.read_bytes(), self.clone)
        self.assertEqual(verdict, "FAIL")
        for p in (a, b):
            p.unlink(missing_ok=True)

    def test_classify_fail_on_clone_string(self) -> None:
        a = self._write(_make_pe_with_section())
        b = self._write(_make_pe_with_section(
            extra=b"D:\\atlas\\target\\hephaestus-gitlink\\crates\\hephaestus-wgpu"))
        verdict, _ = _harness.classify_binary(a.read_bytes(), b.read_bytes(), self.clone)
        self.assertEqual(verdict, "FAIL")
        for p in (a, b):
            p.unlink(missing_ok=True)

    def test_classify_equivalent_on_disambiguator_residual(self) -> None:
        a = self._write(_make_pe_with_section(extra=b"aaaaaaaaaaaaaaaa"))
        b = self._write(_make_pe_with_section(extra=b"bbbbbbbbbbbbbbbb"))
        verdict, detail = _harness.classify_binary(
            a.read_bytes(), b.read_bytes(), self.clone)
        self.assertEqual(verdict, "EQUIVALENT")
        self.assertIn("metadata-disambiguator", detail)
        for p in (a, b):
            p.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
