#!/usr/bin/env python3
"""Tests for the SAFETY-contract census scanner (`safety-census.py`).

The scanner counts production `unsafe impl` / `unsafe {` sites lacking a
contiguous preceding comment carrying a `SAFETY:` marker (or `# Safety`).
The pure surfaces under test are:

- `cfg_test_spans` — top-level `#[cfg(test)] mod ... { ... }` line spans.
  The rewrite skips attributes/comments/blank lines between the gate and
  the `mod` item, so a gated sidecar is still excluded from production
  counts when there is intervening material.
- `contiguous_comment_covers` — whether the comment walk above a site
  carries a `SAFETY:` marker.
- `scan_file` — one-file site detection and missing-contract reporting.
- `main` — the directory walk, exercised end-to-end via `sys.argv` in a
  temporary crate tree.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "safety-census.py"
_SPEC = importlib.util.spec_from_file_location("safety_census", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_sc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_sc)


class CfgTestSpansTestCase(unittest.TestCase):
    def test_adjacent_gate_and_mod(self) -> None:
        lines = ["#[cfg(test)]", "mod tests {", "    fn x() {}", "}"]
        self.assertEqual(_sc.cfg_test_spans(lines), [(0, 3)])

    def test_attribute_between_gate_and_mod(self) -> None:
        # A sidecar with its own attributes between the gate and the mod
        # item: the gate still owns the block that follows.
        lines = [
            "#[cfg(test)]",
            "#[allow(dead_code)]",
            "mod tests {",
            "    fn x() {}",
            "}",
        ]
        self.assertEqual(_sc.cfg_test_spans(lines), [(0, 4)])

    def test_comment_between_gate_and_mod(self) -> None:
        lines = ["#[cfg(test)]", "// unit tests", "mod tests {", "}"]
        self.assertEqual(_sc.cfg_test_spans(lines), [(0, 3)])

    def test_blank_line_between_gate_and_mod(self) -> None:
        lines = ["#[cfg(test)]", "", "mod tests {", "}"]
        self.assertEqual(_sc.cfg_test_spans(lines), [(0, 3)])

    def test_pub_mod(self) -> None:
        lines = ["#[cfg(test)]", "pub mod tests {", "}"]
        self.assertEqual(_sc.cfg_test_spans(lines), [(0, 2)])

    def test_non_test_gate_ignored(self) -> None:
        lines = ["#[cfg(feature)]", "mod other {", "}"]
        self.assertEqual(_sc.cfg_test_spans(lines), [])

    def test_gate_without_mod_ignored(self) -> None:
        lines = ["#[cfg(test)]", "use something::else;"]
        self.assertEqual(_sc.cfg_test_spans(lines), [])

    def test_multiple_gated_mods_each_spanned(self) -> None:
        lines = [
            "#[cfg(test)]",
            "mod a {",
            "}",
            "",
            "#[cfg(test)]",
            "mod b {",
            "}",
        ]
        self.assertEqual(_sc.cfg_test_spans(lines), [(0, 2), (4, 6)])

    def test_unclosed_gated_mod_spans_to_file_end(self) -> None:
        lines = ["#[cfg(test)]", "mod tests {", "    fn broken() {}"]
        self.assertEqual(_sc.cfg_test_spans(lines), [(0, 2)])

    def test_nested_braces_inside_mod(self) -> None:
        lines = [
            "fn outer() {",
            "#[cfg(test)]",
            "mod tests {",
            "    fn helper() {",
            "        let x = 1;",
            "    }",
            "}",
        ]
        self.assertEqual(_sc.cfg_test_spans(lines), [(1, 6)])


class CommentCoversTestCase(unittest.TestCase):
    def test_no_comment_not_covered(self) -> None:
        self.assertFalse(_sc.contiguous_comment_covers(["unsafe { x(); }"], 0))

    def test_plain_comment_not_covered(self) -> None:
        self.assertFalse(
            _sc.contiguous_comment_covers(
                ["// some comment", "unsafe { x(); }"], 1
            )
        )

    def test_safety_colon_covered(self) -> None:
        self.assertTrue(
            _sc.contiguous_comment_covers(
                ["// SAFETY: non-null", "unsafe { x(); }"], 1
            )
        )

    def test_safety_hashtag_covered(self) -> None:
        self.assertTrue(
            _sc.contiguous_comment_covers(
                ["// # Safety: required", "unsafe { x(); }"], 1
            )
        )

    def test_doc_comment_not_covered(self) -> None:
        self.assertFalse(
            _sc.contiguous_comment_covers(
                ["/// docs only", "unsafe { x(); }"], 1
            )
        )

    def test_marker_reaches_through_code(self) -> None:
        # A marker above a code line still covers a later site: the walk
        # scans up to 16 lines and stops only after a code line breaks the
        # blank/comment run. This is the documented leniency.
        self.assertTrue(
            _sc.contiguous_comment_covers(
                ["// SAFETY: ok", "let x = 1;", "unsafe { x(); }"], 2
            )
        )


class ScanFileTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="atlas-safety-census-")
        self.root = Path(self._tmp.name)
        self.file = self.root / "src" / "lib.rs"
        self.file.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _scan(self, text: str):
        self.file.write_text(text, encoding="utf-8")
        return _sc.scan_file(self.file, self.root)

    def test_unsafe_block_with_safety_comment_clean(self) -> None:
        rel, total, missing = self._scan(
            "// SAFETY: the buffer is guaranteed non-null by the caller.\n"
            "unsafe { do_thing(); }\n"
        )
        self.assertEqual((rel, total, missing), ("src/lib.rs", 1, []))

    def test_unsafe_block_without_comment_missing(self) -> None:
        rel, total, missing = self._scan("unsafe { do_thing(); }\n")
        self.assertEqual((rel, total, missing), ("src/lib.rs", 1, [1]))

    def test_unsafe_impl_with_safety_marker_clean(self) -> None:
        rel, total, missing = self._scan(
            "// SAFETY: all methods uphold the trait contract.\n"
            "unsafe impl Send for Foo {}\n"
        )
        self.assertEqual((rel, total, missing), ("src/lib.rs", 1, []))

    def test_unsafe_impl_without_comment_missing(self) -> None:
        # `unsafe impl` on line 1 is a site; line 1 is reported missing.
        rel, total, missing = self._scan("unsafe impl Send for Foo {}\n")
        self.assertEqual((rel, total, missing), ("src/lib.rs", 1, [1]))

    def test_unsafe_fn_decl_is_not_a_site(self) -> None:
        # A bare `unsafe fn` declaration is not itself a site: edition 2024
        # forces every operation inside it into its own contracted block.
        rel, total, missing = self._scan("unsafe fn dangerous() {}\n")
        self.assertEqual((rel, total, missing), ("src/lib.rs", 0, []))

    def test_type_position_unsafe_fn_excluded(self) -> None:
        rel, total, missing = self._scan(
            "type F = unsafe fn(*const u8) -> u8;\n"
        )
        self.assertEqual((rel, total, missing), ("src/lib.rs", 0, []))

    def test_production_site_counted_and_test_block_excluded(self) -> None:
        # The prod `unsafe` on line 1 is counted and reported missing; the
        # cfg(test) block's own unsafe is excluded from the count.
        rel, total, missing = self._scan(
            "unsafe { prod_thing(); }\n"
            "#[cfg(test)]\n"
            "mod tests {\n"
            "    #[test]\n"
            "    fn t() { unsafe { test_thing(); } }\n"
            "}\n"
        )
        self.assertEqual((rel, total, missing), ("src/lib.rs", 1, [1]))

    def test_whole_file_cfg_test_excluded(self) -> None:
        # A test sidecar whose whole body is under `#[cfg(test)]` module.
        rel, total, missing = self._scan(
            "#[cfg(test)]\n"
            "mod tests {\n"
            "    unsafe { test_thing(); }\n"
            "}\n"
        )
        self.assertEqual((rel, total, missing), ("src/lib.rs", 0, []))

    def test_missing_lines_are_one_based(self) -> None:
        rel, total, missing = self._scan(
            "// normal comment, no marker\n"
            "unsafe { x(); }\n"
        )
        self.assertEqual((rel, total, missing), ("src/lib.rs", 1, [2]))


class MainWalkTestCase(unittest.TestCase):
    def _make_repo(self) -> Path:
        repo = Path(tempfile.mkdtemp(prefix="atlas-safety-census-repo-"))
        crate = repo / "acme" / "src"
        crate.mkdir(parents=True)
        (crate / "lib.rs").write_text(
            "// SAFETY: documented.\n"
            "unsafe { safe_thing(); }\n",
            encoding="utf-8",
        )
        # A second file with an undocumented site to produce a finding.
        (crate / "other.rs").write_text(
            "unsafe { undocumented(); }\n",
            encoding="utf-8",
        )
        return repo

    def test_main_reports_missing_and_exit_zero(self) -> None:
        repo = self._make_repo()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), \
                unittest.mock.patch.object(
                    sys, "argv", ["safety-census.py", str(repo)]
                ):
            rc = _sc.main()
        text = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("other.rs", text)
        self.assertIn("missing=1", text)

    def test_fail_on_missing_returns_one(self) -> None:
        repo = self._make_repo()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), \
                unittest.mock.patch.object(
                    sys, "argv",
                    ["safety-census.py", str(repo), "--fail-on-missing"],
                ):
            rc = _sc.main()
        self.assertEqual(rc, 1)

    def test_usage_error_for_missing_arg(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), \
                unittest.mock.patch.object(
                    sys, "argv", ["safety-census.py"]
                ):
            rc = _sc.main()
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()