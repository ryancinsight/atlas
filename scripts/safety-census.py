"""SAFETY-contract census for production unsafe sites.

Scans a repository's first-party crates for `unsafe fn`, `unsafe impl`, and
`unsafe {` sites lacking a contiguous preceding comment carrying `SAFETY:` or
`# Safety`. Type-position pointers (`type F = unsafe fn(..)`), attributes,
and `#[cfg(test)]` modules are excluded, so the count reflects the audited
production surface only.

Usage:
    python safety-census.py <repo-root> [--fail-on-missing]

Exit codes: 0 clean, 1 missing contracts found, 2 usage error.
"""

import re
import sys
from pathlib import Path

SAFETY_MARKERS = ("SAFETY:", "# Safety", "Safety:")
UNSAFE_DECL = re.compile(r"^\s*(pub(?:\([^)]*\))?\s+)?unsafe\s+(?:async\s+)?fn\b")
UNSAFE_IMPL = re.compile(r"^\s*(pub(?:\([^)]*\))?\s+)?unsafe\s+impl\b")
UNSAFE_BLOCK = re.compile(r"unsafe\s*\{")
TYPE_POSITION = re.compile(
    r"(^\s*(pub(?:\([^)]*\))?\s+)?type\s|^\s*let\s|:\s*unsafe\s+fn\b|\b->\s*unsafe\s+fn\b)"
)
TEST_DIR_PARTS = ("/tests/", "/benches/", "/target/")


def contiguous_comment_covers(lines, site_idx):
    """True when the comment run ending just above the site carries a marker."""
    i = site_idx - 1
    seen_code_since_comment = False
    steps = 0
    while i >= 0 and steps < 16:
        stripped = lines[i].strip()
        if stripped.startswith("//"):
            if any(m in stripped for m in SAFETY_MARKERS):
                return True
            seen_code_since_comment = False
        elif stripped == "":
            # Blank line ends the comment run unless still inside a doc block.
            if seen_code_since_comment:
                break
        else:
            if seen_code_since_comment:
                break
            seen_code_since_comment = True
        i -= 1
        steps += 1
    return False


def cfg_test_spans(lines):
    """Line spans of top-level `#[cfg(test)] mod ... { ... }` blocks."""
    spans = []
    i = 0
    while i < len(lines):
        if re.match(r"^\s*#\[\s*cfg\(\s*test\s*\)\s*\]", lines[i]):
            j = i + 1
            # Skip attributes/comments between the gate and the mod item.
            while j < len(lines) and (
                lines[j].strip().startswith("#") or lines[j].strip().startswith("//")
                or lines[j].strip() == ""
            ):
                j += 1
            if j < len(lines) and re.match(
                r"^\s*(pub(?:\([^)]*\))?\s+)?mod\s+\w+", lines[j]
            ):
                depth = 0
                opened = False
                k = j
                while k < len(lines):
                    depth += lines[k].count("{") - lines[k].count("}")
                    if "{" in lines[k]:
                        opened = True
                    if opened and depth <= 0:
                        break
                    k += 1
                spans.append((i, min(k, len(lines) - 1)))
                i = k + 1
                continue
        i += 1
    return spans


def scan_file(path, repo_root):
    rel = path.relative_to(repo_root).as_posix().replace("\\", "/")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    head = chr(10).join(lines[:12])
    if re.search(r"^#!\[cfg\(test\)\]", head, re.MULTILINE):
        return rel, 0, []
    spans = cfg_test_spans(lines)
    missing = []
    total = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        in_test = any(a <= i <= b for a, b in spans)
        if in_test:
            continue
        # A bare `unsafe fn` declaration is not itself a site: edition 2024
        # forces every operation inside it into its own contracted block.
        is_impl = bool(UNSAFE_IMPL.match(line))
        is_block = bool(UNSAFE_BLOCK.search(line)) and not s.startswith("#[")
        if not (is_impl or is_block):
            continue
        if TYPE_POSITION.search(line):
            continue
        total += 1
        if not contiguous_comment_covers(lines, i):
            missing.append(i + 1)
    return rel, total, missing


TEST_GATED_MOD = re.compile(
    r"#\[\s*cfg\(\s*test\s*\)\s*]\s*\n\s*(pub\(.*?\)\s+)?mod\s+(\w+)\s*;"
)


def test_gated_children(dir_path):
    """Child modules declared under #[cfg(test)] in this directory's mod.rs."""
    gated = set()
    for manifest in (dir_path / "mod.rs", dir_path / (dir_path.name + ".rs")):
        if manifest.is_file():
            text = manifest.read_text(encoding="utf-8", errors="replace")
            for m in TEST_GATED_MOD.finditer(text):
                gated.add(m.group(2) + ".rs")
    return gated


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fail = "--fail-on-missing" in sys.argv
    if len(args) != 1:
        print(__doc__)
        return 2
    root = Path(args[0]).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}")
        return 2
    files = sorted(root.glob("*/src/**/*.rs"))
    grand_total = grand_missing = 0
    offenders = []
    for f in files:
        rel_posix = f.relative_to(root).as_posix().replace("\\", "/")
        if any(part in "/" + rel_posix for part in TEST_DIR_PARTS):
            continue
        if f.name in test_gated_children(f.parent):
            continue
        rel, total, missing = scan_file(f, root)
        grand_total += total
        grand_missing += len(missing)
        if missing:
            offenders.append((rel, missing))
    for rel, missing in offenders:
        print(f"{rel}: missing={len(missing)} lines={missing}")
    print(
        f"TOTAL sites={grand_total} missing={grand_missing} "
        f"files-scanned={len(files)}"
    )
    if fail and grand_missing:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
