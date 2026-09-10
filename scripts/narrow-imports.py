#!/usr/bin/env python3
"""Delete the imports rustc reports as unused, from its own suggestions.

`cargo fix` does this, but it re-resolves and rewrites the member's
`Cargo.lock` when run under the stack overlay (recorded on the atlas board as
`ATLAS-TARGET-FORK-REGRESSION`'s sibling trap). This applies the identical
edits without touching resolution: it runs the check with `--locked`, reads
the machine-readable diagnostics, and rewrites exactly the spans rustc's own
`unused_imports` suggestion names.

It is the second half of `manifest-split.py`. A split gives every leaf the
manifest's whole import block because guessing a minimal set per module is how
a split stalls; this narrows each one to what it actually uses, in a single
pass over the compiler's answer rather than by reading errors one at a time.

Usage:

    narrow-imports.py --manifest-path <Cargo.toml> -p <package> [-- <cargo args>]

Only `unused_imports` is applied. Spans outside the workspace are skipped, and
a file whose content changed since the diagnostic was produced is left alone --
re-run to converge.
"""

import argparse
import io
import json
import pathlib
import subprocess
import sys

NL = chr(10)


def diagnostics(manifest, package, extra):
    """Run the check and yield rustc's structured diagnostics."""
    cmd = [
        "cargo", "clippy", "--locked",
        "--manifest-path", str(manifest),
        "-p", package,
        "--all-targets", "--no-deps",
        "--message-format", "json",
    ] + list(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if message.get("reason") == "compiler-message":
            yield message["message"]


def unused_import_edits(diags):
    """{path: [(start, end, replacement)]} from `unused_imports` suggestions."""
    edits = {}
    for diag in diags:
        code = (diag.get("code") or {}).get("code")
        if code != "unused_imports":
            continue
        for child in diag.get("children", []):
            for span in child.get("spans", []):
                replacement = span.get("suggested_replacement")
                if replacement is None:
                    continue
                edits.setdefault(span["file_name"], []).append(
                    (span["byte_start"], span["byte_end"], replacement)
                )
    return edits


def apply(edits, root):
    """Apply non-overlapping edits back-to-front so offsets stay valid."""
    touched = 0
    for name, spans in sorted(edits.items()):
        path = (root / name).resolve()
        if not path.is_file():
            print(f"skip (not a file): {name}", file=sys.stderr)
            continue
        data = io.open(path, "rb").read()
        spans = sorted(set(spans), reverse=True)
        last_start = len(data) + 1
        applied = 0
        for start, end, replacement in spans:
            if end > last_start:
                continue  # overlapping suggestion; the next pass catches it
            data = data[:start] + replacement.encode("utf-8") + data[end:]
            last_start = start
            applied += 1
        io.open(path, "wb").write(data)
        touched += 1
        print(f"{applied:4d} import(s) removed  {name}")
    return touched


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-path", required=True)
    parser.add_argument("-p", "--package", required=True)
    parser.add_argument("cargo_args", nargs="*")
    args = parser.parse_args()

    manifest = pathlib.Path(args.manifest_path).resolve()
    root = manifest.parent
    edits = unused_import_edits(diagnostics(manifest, args.package, args.cargo_args))
    if not edits:
        print("no unused imports reported")
        return
    files = apply(edits, root)
    print(f"{files} file(s) rewritten -- re-run until it reports none")


if __name__ == "__main__":
    main()
