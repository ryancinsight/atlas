#!/usr/bin/env python3
"""Guard: every subprocess call in scripts/ that reads text names its encoding.

With `text=True` alone, Windows decodes as cp1252; a member manifest carrying
an em dash raised inside the reader thread and `.stdout` came back None, so a
tool reported two members as having no manifest
(ATLAS-SUBPROCESS-UTF8-DECODING-2026-09-01). The class is silent and lands as
a false finding about the member, so it is guarded here rather than reviewed
for.

The scanner is bounded to the enclosing call's parentheses: an `encoding=` in
a neighbouring call must not exempt this one. It is tested on synthetic
snippets first, so the guard's own verdicts are proven before they judge the
tree.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent


def enclosing_call(text: str, index: int) -> str | None:
    depth = 0
    start = None
    for i in range(index, -1, -1):
        if text[i] == ")":
            depth += 1
        elif text[i] == "(":
            if depth == 0:
                start = i
                break
            depth -= 1
    if start is None:
        return None
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[start : j + 1]
    return None


def undecoded_sites(text: str) -> list[int]:
    """Line numbers of `text=True` arguments whose call names no `encoding=`."""
    sites = []
    for match in re.finditer(r"text=True", text):
        line_start = text.rfind("\n", 0, match.start()) + 1
        line = text[line_start : text.find("\n", match.start())]
        if line.lstrip().startswith("#"):
            continue
        call = enclosing_call(text, match.start())
        if call is None or "encoding=" not in call:
            sites.append(text.count("\n", 0, match.start()) + 1)
    return sites


class ScannerTests(unittest.TestCase):
    def test_bare_text_true_is_flagged(self) -> None:
        self.assertEqual(undecoded_sites('subprocess.run(["git"], capture_output=True, text=True)\n'), [1])

    def test_explicit_encoding_in_the_same_call_is_accepted(self) -> None:
        self.assertEqual(undecoded_sites('subprocess.run(["git"], text=True, encoding="utf-8")\n'), [])

    def test_encoding_in_a_neighbouring_call_does_not_exempt(self) -> None:
        text = 'a = run(["x"], encoding="utf-8")\nb = run(["y"], text=True)\n'
        self.assertEqual(undecoded_sites(text), [2])

    def test_multiline_calls_are_bounded_by_their_own_parentheses(self) -> None:
        text = 'subprocess.run(\n    ["git"],\n    capture_output=True,\n    text=True,\n)\nother(encoding="utf-8")\n'
        self.assertEqual(undecoded_sites(text), [4])

    def test_comments_are_not_call_sites(self) -> None:
        self.assertEqual(undecoded_sites("# with `text=True` alone, Windows decodes as cp1252\n"), [])


class TreeGuard(unittest.TestCase):
    def test_every_script_names_its_subprocess_encoding(self) -> None:
        offenders = {}
        for script in sorted(SCRIPTS.glob("*.py")):
            lines = undecoded_sites(script.read_text(encoding="utf-8"))
            if lines:
                offenders[script.name] = lines
        self.assertEqual(
            offenders,
            {},
            "subprocess calls decoding with text=True and no encoding= "
            "(Windows decodes cp1252 and returns None on a UTF-8 byte); "
            'use encoding="utf-8", errors="replace"',
        )


if __name__ == "__main__":
    unittest.main()
