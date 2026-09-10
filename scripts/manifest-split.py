#!/usr/bin/env python3
"""Move a Rust manifest's implementation into leaf modules.

`lib.rs` and `mod.rs` are module manifests: the tree, its curated re-exports
and the docs (AGENTS.md `standards`, deep vertical hierarchy). The fleet scan
counts a manifest carrying more than twenty lines of body as
`manifest_implementation`, and burning that class down means moving items out
of hundreds of files.

Doing it by line arithmetic is how a split goes wrong: a boundary taken one
line late orphans a `///` onto the previous section, and one taken early
strands a closing brace. This tool works on whole items instead. It reads the
top-level items of a file -- each with the doc comments, plain comments and
attributes that precede it -- and writes the ones you name into leaf modules,
leaving the file as its own manifest.

The safety net is an exact accounting: every non-blank line of the input must
appear exactly once across the outputs, or nothing is written. The compiler
then checks the rest, since a split changes visibility, not behaviour.

Usage:

    manifest-split.py <file.rs> --plan plan.json [--dry-run]

The plan names each leaf module, its `//!` header, the imports it needs, and
the items it takes by name:

    {"modules": [
       {"name": "types", "doc": "//! ...", "use": "use super::X;",
        "items": ["Config", "Acquisition"]}
     ]}

Items not named in any module stay in the manifest. Names match an item's
declared identifier: `fn f`, `struct S`, `enum E`, `trait T`, `const C`,
`static S`, `type A`, `impl ... for S` and `impl S` (which follow `S`), and
`macro_rules! m`.
"""

import argparse
import io
import json
import pathlib
import re
import sys

NL = chr(10)

ITEM = re.compile(
    r"^(?:pub(?:\([^)]*\))?\s+)?(?:default\s+)?(?:const\s+)?(?:async\s+)?"
    r"(?:unsafe\s+)?(?:extern\s+\"[^\"]*\"\s+)?"
    r"(fn|struct|enum|trait|union|type|const|static|impl|macro_rules!|mod)\b"
)
NAME_AFTER = re.compile(r"\b(?:fn|struct|enum|trait|union|type|const|static|mod)\s+([A-Za-z_]\w*)")
IMPL_FOR = re.compile(r"\bimpl\b[^{]*?\bfor\s+([A-Za-z_]\w*)")
IMPL_SELF = re.compile(r"\bimpl\b(?:<[^>]*>)?\s+([A-Za-z_]\w*)")
MACRO_NAME = re.compile(r"macro_rules!\s+([A-Za-z_]\w*)")
LEAD = ("///", "//!", "//", "#[", "#![")


def read_items(lines):
    """[(name, start, end)] over 0-indexed lines; start includes docs/attrs."""
    items, i, n = [], 0, len(lines)
    while i < n:
        if not ITEM.match(lines[i]):
            i += 1
            continue
        start = i
        while start > 0:
            prev = lines[start - 1].strip()
            if prev.startswith(LEAD) and not prev.startswith("//!"):
                start -= 1
                continue
            break
        header = lines[i]
        kind = ITEM.match(header).group(1)
        name = None
        if "macro_rules!" in header:
            match = MACRO_NAME.search(header)
            name = match.group(1) if match else None
        elif re.match(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:unsafe\s+)?impl\b", header):
            span = header
            j = i
            while "{" not in span and j + 1 < n:
                j += 1
                span += " " + lines[j]
            match = IMPL_FOR.search(span) or IMPL_SELF.search(span)
            name = match.group(1) if match else None
        else:
            match = NAME_AFTER.search(header)
            name = match.group(1) if match else None
        end = i
        depth = 0
        opened = False
        while end < n:
            depth += lines[end].count("{") - lines[end].count("}")
            if "{" in lines[end]:
                opened = True
            if opened and depth <= 0:
                break
            if not opened and lines[end].rstrip().endswith(";"):
                break
            end += 1
        items.append((kind, name, start, min(end, n - 1)))
        i = end + 1
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    path = pathlib.Path(args.file)
    lines = io.open(path, encoding="utf-8").read().replace(chr(13), "").split(NL)
    plan = json.load(io.open(args.plan, encoding="utf-8"))
    items = read_items(lines)
    # A plan entry is a bare name where that is unambiguous, or `kind name`
    # when it is not -- `mod transform;` and `fn transform` share a name, and
    # moving the module declaration instead of the function is a silent break
    # the compiler only catches downstream. A bare `mod` declaration is never
    # movable: the module tree is what a manifest is for.
    by_name = {}
    for kind, name, start, end in items:
        if kind == "mod":
            continue
        by_name.setdefault(name, []).append((start, end))
        by_name.setdefault(f"{kind} {name}", []).append((start, end))
    # `impl` blocks are not a competing kind: a type travels with its inherent
    # and trait impls, which is why a bare name takes them too. Ambiguity is
    # two *declarations* sharing a name, which in practice means a `fn` beside
    # a `mod` of the same name.
    def declared(name):
        return {k for k, n, _, _ in items if n == name and k not in ("mod", "impl")}

    ambiguous = {n for n in by_name if " " not in n and len(declared(n)) > 1}

    taken, sections = set(), {}
    for module in plan["modules"]:
        spans = []
        for want in module["items"]:
            if want in ambiguous:
                kinds = sorted(declared(want))
                sys.exit(
                    f"error: {want!r} names several items in {path} "
                    f"({', '.join(kinds)}) -- qualify it, e.g. \"{kinds[0]} {want}\""
                )
            if want not in by_name:
                sys.exit(f"error: no top-level item named {want!r} in {path}")
            spans.extend(by_name[want])
        spans.sort()
        sections[module["name"]] = (module, spans)
        for start, end in spans:
            taken.update(range(start, end + 1))

    kept = [k for k in range(len(lines)) if k not in taken]
    accounted = len(taken) + len(kept)
    if accounted != len(lines):
        sys.exit(f"error: accounting mismatch ({accounted} of {len(lines)})")

    # A leaf that names no imports inherits the manifest's whole `use` block.
    # Guessing a minimal set per module is how a split stalls; the compiler
    # names the unused ones exactly, so start from everything and narrow once.
    # A leaf sits one level below the manifest, so the paths move with it:
    # `super::X` becomes `super::super::X`, and a bare `X::` naming one of the
    # manifest's own modules becomes `super::X::`. Re-exports (`pub use`) stay
    # in the manifest -- copying them would publish the same name twice.
    MOD_DECL = re.compile(r"\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+([A-Za-z_]\w*)\s*;")
    siblings = set()
    for k in kept:
        match = MOD_DECL.match(lines[k])
        if match:
            siblings.add(match.group(1))

    def rebase(line):
        if line.startswith("use super::"):
            return "use super::super::" + line[len("use super::"):]
        for sibling in siblings:
            prefix = f"use {sibling}::"
            if line.startswith(prefix):
                return f"use super::{sibling}::" + line[len(prefix):]
        return line

    # `use super::*;` first: whatever the manifest re-exports (`pub use`)
    # is part of the module's own surface, and a leaf reads it through the
    # parent rather than reaching past it into the sibling that defines it.
    inherited = NL.join(
        ["use super::*;"]
        + [rebase(lines[k]) for k in kept if lines[k].startswith("use ")]
    )

    outputs = {}
    for name, (module, spans) in sections.items():
        module.setdefault("use", inherited)
        body = NL.join(NL.join(lines[s:e + 1]).rstrip() for s, e in spans)
        text = module["doc"] + NL * 2
        if module.get("use"):
            text += module["use"] + NL * 2
        outputs[path.parent / f"{name}.rs"] = text + body.strip(NL) + NL

    manifest = NL.join(lines[k] for k in kept).rstrip() + NL * 2
    manifest += NL.join(f"mod {n};" for n in sorted(sections)) + NL
    if plan.get("reexport"):
        manifest += NL + plan["reexport"].rstrip() + NL
    outputs[path] = manifest

    written = sum(
        1 for text in outputs.values() for ln in text.split(NL) if ln.strip()
    )
    source = sum(1 for ln in lines if ln.strip())
    extra = sum(
        1 for module in plan["modules"]
        for ln in (module["doc"] + NL + module.get("use", "")).split(NL) if ln.strip()
    )
    extra += len(sections) + sum(
        1 for ln in plan.get("reexport", "").split(NL) if ln.strip()
    )
    if written - extra != source:
        sys.exit(
            f"error: {source} source lines in, {written - extra} out -- refusing to write"
        )

    for out, text in sorted(outputs.items()):
        if not args.dry_run:
            io.open(out, "w", encoding="utf-8", newline=NL).write(text)
        print(f"{text.count(NL) + 1:5d}  {out.as_posix()}")


if __name__ == "__main__":
    main()
