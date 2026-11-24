#!/usr/bin/env python3
"""Push-time gate for bare `as` casts.

The stack's cast rule sends every conversion std has no trait for through one
conversion module, and lets `as` appear only there and in a crate's cast
module. Existing casts are scheduled for burn-down, not annotated, so the
workspace lint tables still allow the cast family; nothing in the build fails
on a new cast. This gate is the enforcement:

- clippy runs on the pushed packages with `--force-warn clippy::as_conversions`,
  which reports every `as` through allows and expects alike;
- a reported site whose span covers a line the push adds fails, unless its
  file is a sanctioned conversion module (a span covers the whole
  `expr as T`, so a cast ending a method chain starts lines above its `as`).
  A conversion module is excluded from every count. A package's one cast
  module (`cast_modules`) is counted like any other file, so a cast moved
  into it neither raises nor lowers the package's count. Its added lines pass
  only under `cast_module_fault`, no file of its package mounted twice
  (`clippy::duplicate_mod`, force-warned), the module compiled by exactly one
  crate target of its package (`second_target_problems`), and the base count;
- a pushed package whose Rust text holds a `cfg` or `cfg_attr` predicate, or a
  `cfg_select!` arm head, naming `clippy` fails (`cfg_clippy_problems`):
  clippy-driver sets `cfg(clippy)` and rustc does not, so code under
  `cfg(not(clippy))` is compiled only by the run that skips it, and code under
  `cfg(clippy)` by no build the gate counts. The scan reads the files the
  package's crate targets compile (`package_sources`: module trees, `#[path]`
  and `include!("literal")` files of any extension, wherever they lie) and the
  tracked `.rs` files under its directory that no other workspace member holds,
  with comments and strings blanked, and refuses a file that cannot be read as
  Rust. A manifest `tomllib` rejects fails the push naming the manifest. A
  predicate built by macro substitution (`#[cfg(not($p))]`) has no `cfg(` token
  and is not seen;
- a package whose site count rises above its row in `cast-baseline.json`
  fails, a package with no row counting as zero -- a newly registered member
  is measured (`measure`) before its first gated push;
- a package whose site count rises above its count at the pushed range's base,
  measured with the same `-p` selection, fails: rows are measured
  `--workspace`, which compiles more features than a `-p` run, so a row alone
  leaves headroom a moved file or a newly compiled module could fill. A
  feature change that compiles existing casts in a pushed package fails this
  too, until those casts convert. The base builds only when the range can
  bring existing casts into a pushed package without adding their lines
  (`base-triggers`): a renamed file, a changed cast module, or a changed
  `Cargo.toml`, package-root `build.rs`, cargo config or `rust-toolchain`
  file. A source-level `cfg`
  flip, `#[path]`, `include!`, a new `mod` line naming a file that was not
  compiled before, or a build script at a custom `package.build` path or in
  a helper module is not a trigger and is held to the row alone. Only pushed packages are counted:
  clippy lints the selected packages, so a pushed package enabling a feature
  of one it depends on is not measured there. The comparison covers the
  packages named by `--base-package`; the hook names a manifest's packages
  only when that manifest's base built, so one that fails to compile leaves
  its own packages to their rows and no others. A newly locked standalone
  manifest is held to zero only when real metadata on immutable exports
  proves that no base workspace owned it.

Sites are deduplicated by span, since `--all-targets` reports a library site
once per target. The exclusion is by path only: `--force-warn` output does not
say whether a site sits under an `#[expect]`.

A cast module that two crate targets of one package compile (`lib`, `bin`,
`tests/`, `examples/`, `benches/`, the build script) is counted once there
and linted once, so `second_target_problems` walks each target root's module
tree over the pushed tip's files and names the package and every root that
reaches the module. It follows `mod name;` as rustc resolves it, `#[path]`,
both outcomes of a `cfg_attr(.., path = ..)`, and `include!("literal")`
(rustc 1.97.0 rejects an `include!` of a module that opens with its inner
`#![expect]`, so that mount is a fault either way). A `mod` a macro writes is
not followed, and a mount from another package's target is outside the rule.

The tip's clippy run is the hook's own: `clippy` runs it under the
source-identity leases in place of the plain step, writing each diagnostic's
rendered text to stderr as plain clippy would and the cast sites to a file.
The base run is the one extra compile, under the same leases.

    atlas_cast_gate.py clippy --export <dir> --sites <file> --package <pkg>
    atlas_cast_gate.py check --member eunomia --repo <dir> --base <sha> \
        --tip <sha> --package eunomia --sites <file> [--sites ...] \
        [--base-sites <file> ... --base-package eunomia ...]

`--base-package` names the packages the base could hold to a count. The gate
holds the ones the base's workspace had: a package the base never had carries
no count there, so its casts are judged by the row that records them, and a
crate that returns to the workspace brings that debt with it. The membership
is read from the base revision's own manifests, so a package the push adds is
absent from it. `--zero-base-package` records the proven standalone exception.
    atlas_cast_gate.py base-triggers --repo <dir> --base <sha> --tip <sha>
    atlas_cast_gate.py new-standalone-owners --repo <dir> --base <sha> \
        --tip <sha> --manifest fuzz/Cargo.toml [--manifest ...]
    atlas_cast_gate.py resolved-changes --repo <dir> --base <sha> --tip <sha> \
        --base-export <dir> --tip-export <dir>
    atlas_cast_gate.py measure --member eunomia --export <dir>
    atlas_cast_gate.py ratchet --repo <atlas> --base <sha> --tip <sha>

`ratchet` holds `cast-baseline.json` itself to the rule that rows only fall:
atlas's pre-push hook and its conformance job run it on every pushed range.
A row may fall or be dropped; it may not rise, and a package of a member the
base already measured may not gain a row (no row counts as zero). A member
the base does not measure enters with its rows (onboarding). A sanctioned
path may not be added to a member the base measures: exclusion lowers a
count without converting a cast. A cast module may be added for a package
that has none, since its casts stay counted; a package's cast module path
does not change, which would make a second module.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import pathlib
import posixpath
import re
import shutil
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field

BASELINE = pathlib.Path(__file__).resolve().with_name("cast-baseline.json")
LINT = "clippy::as_conversions"
DUPLICATE_MOD = "clippy::duplicate_mod"  # canonical paths, after macro expansion
HISTORICAL_CAST_KEY = "atlas-pre-push-casts-base"
HISTORICAL_CAST_PROFILE = "cast-history"
HISTORICAL_CAST_CONFIG = ("--config", f'profile.{HISTORICAL_CAST_PROFILE}.inherits="dev"')
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
# `cfg(...)` and `cfg_attr(...)` name their predicate in the first argument, and
# each arm of `cfg_select! { <predicate> => ..., }` begins with one.
# `clippy` is a real cfg set by clippy-driver and not by rustc, so code under
# `cfg(not(clippy))` compiles only in the clippy run -- which then skips it --
# and code under `cfg(clippy)` compiles only where the gate is looking. Both
# are unmeasurable, and a gate that cannot see a cast must refuse the push
# rather than count the rest of the package and pass.
CFG_PREDICATE = re.compile(r"\b(cfg|cfg_attr)\s*\(")
CFG_SELECT = re.compile(r"\bcfg_select\s*!\s*[({\[]")
CLIPPY_PREDICATE = re.compile(r"\bclippy\b")


@dataclass(frozen=True, order=True)
class Site:
    """One `as` cast: the package it belongs to and its primary span.

    The byte range identifies the span; a nested cast (`x as u32 as f64`)
    starts two spans at one line and column. `line_end` is the span's last
    line, where a cast closing a multi-line expression has its `as`.
    """

    package: str
    path: str
    line: int
    column: int
    byte_start: int
    byte_end: int
    line_end: int


def cargo(config: pathlib.Path | None) -> list[str]:
    """`cargo`, with an explicit config file when the caller supplies one.

    The hook supplies its Cargo execution directory separately from the source
    export, so config discovery follows that directory. A caller outside the
    stack passes the stack config minus its `[patch]` overlay, or Cargo builds
    a private target.
    """
    program = os.environ.get("CARGO") or "cargo"
    return [program, "--config", str(config)] if config else [program]


def clippy_command(export: pathlib.Path, packages: Iterable[str],
                   config: pathlib.Path | None = None,
                   manifest: str = "Cargo.toml", *,
                   profile: str | None = None) -> list[str]:
    """The clippy run that reports every `as` in `packages` of `manifest`.

    `manifest` is relative to `export`: the member's root workspace, or a
    standalone crate (cargo-fuzz) that the root workspace excludes. No
    packages selects every package of that manifest's workspace.
    """
    if profile not in (None, HISTORICAL_CAST_PROFILE):
        raise ValueError(f"unsupported cast profile {profile}")
    selection: list[str] = []
    for package in packages:
        selection += ["-p", package]
    if not selection:
        selection = ["--workspace"]
    return [
        *cargo(config), "clippy", *(HISTORICAL_CAST_CONFIG if profile is not None else ()),
        "--manifest-path", str(export / manifest),
        *selection, *(["--profile", profile] if profile is not None else []),
        "--all-targets", "--locked", "--message-format=json",
        "--", "--force-warn", LINT, "--force-warn", DUPLICATE_MOD,
    ]


@dataclass(frozen=True)
class Workspace:
    """The workspace `cargo metadata` reports for one manifest."""

    root: pathlib.Path
    packages: list[dict]
    members: frozenset[str]
    environment: dict[str, str]

    def names(self) -> dict[str, str]:
        """Package id to package name, for the workspace members."""
        return {p["id"]: p["name"] for p in self.packages if p["id"] in self.members}

    def member_manifests(self) -> dict[pathlib.Path, str]:
        """Absolute member manifest paths to their package names."""
        return {
            pathlib.Path(p["manifest_path"]): p["name"]
            for p in self.packages if p["id"] in self.members
        }


def _workspace_record(record: object, environment: dict[str, str]) -> Workspace:
    """Validate the ownership fields emitted by Cargo metadata."""
    if not isinstance(record, dict):
        raise ValueError("cargo metadata record must be an object")
    root = record.get("workspace_root")
    packages = record.get("packages")
    members = record.get("workspace_members")
    if not isinstance(root, str) or not pathlib.Path(root).is_absolute():
        raise ValueError("cargo metadata workspace_root must be an absolute path")
    if not isinstance(packages, list):
        raise ValueError("cargo metadata packages must be an array")
    if (not isinstance(members, list)
            or any(not isinstance(member, str) for member in members)):
        raise ValueError("cargo metadata workspace_members must be an array of strings")

    by_id: dict[str, dict] = {}
    by_manifest: dict[str, str] = {}
    for package in packages:
        if not isinstance(package, dict):
            raise ValueError("cargo metadata package must be an object")
        package_id = package.get("id")
        name = package.get("name")
        manifest_path = package.get("manifest_path")
        if (not isinstance(package_id, str) or not package_id
                or not isinstance(name, str) or not name):
            raise ValueError("cargo metadata package id and name must be nonempty strings")
        if (not isinstance(manifest_path, str)
                or not pathlib.Path(manifest_path).is_absolute()):
            raise ValueError("cargo metadata package manifest_path must be an absolute path")
        if package_id in by_id:
            raise ValueError(f"cargo metadata repeats package id {package_id!r}")
        normalized_manifest = os.path.normcase(os.path.realpath(manifest_path))
        if normalized_manifest in by_manifest:
            raise ValueError(
                "cargo metadata repeats a normalized package manifest path "
                f"for {by_manifest[normalized_manifest]!r} and {package_id!r}"
            )
        by_id[package_id] = package
        by_manifest[normalized_manifest] = package_id

    member_ids = frozenset(members)
    if len(member_ids) != len(members):
        raise ValueError("cargo metadata repeats a workspace member")
    missing = sorted(member_ids - by_id.keys())
    if missing:
        raise ValueError(f"cargo metadata omits workspace member packages: {missing!r}")
    member_names = [by_id[member]["name"] for member in members]
    if len(set(member_names)) != len(member_names):
        raise ValueError("cargo metadata repeats a workspace member package name")
    return Workspace(pathlib.Path(root), packages, member_ids, environment)


def workspace(export: pathlib.Path, config: pathlib.Path | None = None,
              manifest: str = "Cargo.toml",
              command_cwd: pathlib.Path | None = None,
              metadata_timeout: float = 120.0) -> Workspace:
    """Read `export`'s manifest with config discovery at `command_cwd`.

    Omission runs Cargo from the export, preserving the legacy invocation.
    Cargo owns workspace interpretation; malformed, unlocked, or incomplete
    metadata is an error rather than evidence that a package is absent.
    """
    from atlas_build_inputs import effective_compiler_environment
    import process_tree

    if not 0 < metadata_timeout:
        raise ValueError("cargo metadata timeout must be positive")
    directory = command_cwd or export
    manifest_path = export / manifest
    cargo_command = cargo(config)
    environment = effective_compiler_environment(
        manifest_path, directory, cargo_command
    )
    command = [
        *cargo_command, "metadata", "--no-deps", "--locked", "--format-version", "1",
        "--manifest-path", str(manifest_path),
    ]
    completed = process_tree.run(
        command, cwd=directory, env=environment, timeout=min(metadata_timeout, 120.0)
    )
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode, command,
            output=completed.stdout, stderr=completed.stderr,
        )
    out = (completed.stdout or b"").decode("utf-8", errors="strict")
    return _workspace_record(json.loads(out), environment)


def sites(messages: Iterable[str], export: pathlib.Path,
          names: dict[str, str], workspace_root: pathlib.Path | None = None) -> set[Site]:
    """The `as` sites among cargo's JSON messages, deduplicated by span.

    Cargo names a span's file relative to the root of the workspace it built
    (`workspace_root`, by default `export`): for a standalone crate that is
    the crate's own directory, not the repository's. The recorded path is
    relative to `export`, as the pushed diff names it. A span whose file lies
    outside `export` (a dependency, generated code in `OUT_DIR`) is not this
    repository's and is skipped.
    """
    root = export.resolve()
    base = (workspace_root or export).resolve()
    found: set[Site] = set()
    for raw in messages:
        if not raw.startswith("{"):
            continue
        record = json.loads(raw)
        if record.get("reason") != "compiler-message":
            continue
        message = record["message"]
        code = (message.get("code") or {}).get("code")
        package = names.get(record.get("package_id", ""))
        if code not in (LINT, DUPLICATE_MOD) or package is None:
            continue
        if code == DUPLICATE_MOD:  # a file mounted twice: a line-0 marker, never counted
            found.add(Site(package, "", 0, 0, 0, 0, 0))
            continue
        for span in message["spans"]:
            if not span["is_primary"]:
                continue
            path = pathlib.Path(span["file_name"])
            if not path.is_absolute():
                path = base / path
            try:
                relative = path.resolve().relative_to(root).as_posix()
            except ValueError:
                continue
            found.add(Site(package, relative, span["line_start"], span["column_start"],
                           span["byte_start"], span["byte_end"], span["line_end"]))
    return found


def run_clippy(export: pathlib.Path, packages: Iterable[str],
               config: pathlib.Path | None = None,
               manifest: str = "Cargo.toml",
               command_cwd: pathlib.Path | None = None, *,
               profile: str | None = None) -> tuple[int, set[Site]]:
    """Run clippy on `packages` of `export`: its exit status and cast sites.

    Each diagnostic's rendered text goes to stderr, so a caller reading the
    output sees what plain clippy prints; cargo's own stderr passes through.
    """
    space = workspace(export, config, manifest, command_cwd)
    names = space.names()
    proc = subprocess.Popen(
        clippy_command(export, packages, config, manifest, profile=profile),
        cwd=command_cwd or export,
        env=space.environment,
        stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.stdout is not None
    found: set[Site] = set()
    try:
        for raw in proc.stdout:
            found |= sites([raw], export, names, space.root)
            if raw.startswith("{"):
                record = json.loads(raw)
                if record.get("reason") == "compiler-message":
                    sys.stderr.write(record["message"].get("rendered") or "")
                    sys.stderr.flush()
    except BaseException:
        proc.kill()
        proc.wait()
        raise
    return proc.wait(), found


SITE_FIELDS = (str, str, int, int, int, int, int)


def write_sites(path: pathlib.Path, found: set[Site]) -> None:
    rows = [[s.package, s.path, s.line, s.column, s.byte_start, s.byte_end, s.line_end]
            for s in sorted(found)]
    path.write_text(json.dumps(rows), encoding="utf-8")


def read_sites(path: pathlib.Path) -> set[Site]:
    """The sites `write_sites` recorded; a malformed row is a ValueError."""
    found: set[Site] = set()
    for row in json.loads(path.read_text(encoding="utf-8")):
        if (not isinstance(row, list) or len(row) != len(SITE_FIELDS)
                or not all(type(v) is t for v, t in zip(row, SITE_FIELDS))):
            raise ValueError(f"{path}: malformed site row {row!r}")
        found.add(Site(*row))
    return found


def added_lines(diff: str) -> dict[str, set[int]]:
    """Path to the line numbers a zero-context unified diff adds.

    File headers are read only between a `diff --git` line and the file's
    first hunk, so an added line whose text begins `++ ` (rendered `+++ `)
    is content, never a header. Lines split on `\n` alone: a carriage
    return, form feed or U+2028 inside a source line stays inside it.
    """
    added: dict[str, set[int]] = {}
    path: str | None = None
    in_header = False
    for line in diff.split("\n"):
        if line.startswith("diff --git "):
            in_header, path = True, None
            continue
        if in_header and line.startswith("+++ "):
            target = line[4:].rstrip("\t")
            path = None if target == "/dev/null" else target.removeprefix("b/")
            continue
        match = HUNK.match(line)
        if match:
            in_header = False
            if path is not None:
                start, count = int(match[1]), int(match[2] or "1")
                added.setdefault(path, set()).update(range(start, start + count))
    return added


def pushed_additions(repo: pathlib.Path, base: str | None, tip: str) -> dict[str, set[int]]:
    """Lines `base..tip` adds in `repo`; every line of `tip` when there is no base.

    Renames are detected (`-M`, unlimited `-l0`), so a moved file contributes
    only the lines the move changed. Every file diffs as text (`--text`), so
    a `binary`/`-diff` attribute or a NUL byte cannot turn its lines into
    "Binary files differ". Prefixes, path quoting, hunk merging, the diff
    algorithm, external diff drivers and textconv filters are fixed on the
    command line and `GIT_DIFF_OPTS` is dropped from the environment, since
    user settings would otherwise change the headers or line ranges parsed.
    """
    diff = pushed_diff(repo, base, tip, ["-U0", "--inter-hunk-context=0", "--text",
                                         "--src-prefix=a/", "--dst-prefix=b/"])
    # Bytes, decoded without newline translation: text mode would turn a
    # carriage return inside a source line into a line break.
    return added_lines(diff.decode("utf-8", errors="replace"))


def code_without_comments_or_strings(text: str) -> str:
    """`text` with comments and literals blanked, newlines kept in place.

    A `cfg` predicate inside a comment or a string is not code, so it must not
    be read as one. Offsets and line breaks survive the blanking so a fault can
    name the line the predicate is written on.
    """
    return "".join(
        re.sub(r"[^\n]", " ", text[start:end]) if kind in ("comment", "string", "char")
        else text[start:end]
        for kind, start, end in spans(text)
    )


def closing_bracket(code: str, opening: int) -> int:
    """The index of the bracket closing the one at `opening`; unclosed raises."""
    depth = 0
    for index in range(opening, len(code)):
        if code[index] in "([{":
            depth += 1
        elif code[index] in ")]}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("an unclosed bracket")


def cfg_predicate(code: str, name: str, opening: int, closing: int) -> str:
    """The predicate text of one `cfg`/`cfg_attr`; only the first argument of
    `cfg_attr` is its predicate -- the rest is the attribute it applies."""
    inner = code[opening + 1:closing]
    if name == "cfg":
        return inner
    depth = 0
    for index, char in enumerate(inner):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            return inner[:index]
    return inner


def cfg_select_heads(code: str, opening: int, closing: int) -> Iterator[tuple[int, str]]:
    """The (offset, text) of each arm head of the `cfg_select!` group between
    `opening` and `closing`: its grammar is `<predicate> => <block or expression>`,
    arms separated by a comma that a block body does not need."""
    index = opening + 1
    while index < closing:
        depth, arrow = 0, index
        while arrow < closing and (depth or not code.startswith("=>", arrow)):
            depth += (code[arrow] in "([{") - (code[arrow] in ")]}")
            arrow += 1
        if arrow >= closing:
            return
        yield index, code[index:arrow]
        index = arrow + 2
        while code[index].isspace():
            index += 1
        if code[index] == "{":
            index = closing_bracket(code, index) + 1
        else:
            depth = 0
            while index < closing and (depth or code[index] != ","):
                depth += (code[index] in "([{") - (code[index] in ")]}")
                index += 1
        while index < closing and (code[index].isspace() or code[index] == ","):
            index += 1


def cfg_clippy_lines(text: str) -> list[int]:
    """Lines whose `cfg`/`cfg_attr` predicate, or `cfg_select!` arm head, names `clippy`."""
    code = code_without_comments_or_strings(text)
    found: list[int] = []
    for match in CFG_PREDICATE.finditer(code):
        opening = code.find("(", match.start())
        closing = closing_bracket(code, opening)
        if CLIPPY_PREDICATE.search(cfg_predicate(code, match.group(1), opening, closing)):
            found.append(code.count("\n", 0, match.start()) + 1)
    for match in CFG_SELECT.finditer(code):
        opening = match.end() - 1
        for start, head in cfg_select_heads(code, opening, closing_bracket(code, opening)):
            if CLIPPY_PREDICATE.search(head):
                found.append(code.count("\n", 0, start + len(head) - len(head.lstrip())) + 1)
    return sorted(found)


def member_directories(manifests: Mapping[str, dict]) -> frozenset[str]:
    """The directories of packages cargo builds apart from the package above
    them: each workspace member (`members` globs less `exclude`) and each
    manifest that opens a workspace of its own. A package that is only a path
    dependency of a workspace root is not named here; its files stay with the
    package above, which only widens that package's scan."""
    found: set[str] = set()
    for path, manifest in manifests.items():
        table = manifest.get("workspace")
        if not isinstance(table, dict):
            continue
        root = posixpath.dirname(path)
        prefix = f"{root}/" if root else ""
        inside = [other.removeprefix(prefix) for other in manifests if other.startswith(prefix)]
        excluded = [entry for entry in table.get("exclude", []) if isinstance(entry, str)]
        found.add(root)
        members = [member for member in table.get("members", []) if isinstance(member, str)]
        named = [name for member in members for name in member_manifests(member, inside)]
        for manifest_path in named:
            directory = posixpath.dirname(manifest_path)
            if not any(is_excluded(directory, entry) for entry in excluded):
                found.add("/".join(filter(None, [root, directory])))
    return frozenset(found)


def package_sources(tip: Revision, packages: Iterable[str]) -> tuple[set[str], dict[str, str]]:
    """The tracked files the named packages compile, and why any could not be
    read: (paths, error by path).

    A package compiles the files its crate targets' module trees reach
    (`compiled_files`), whatever their extension or directory, and the scan
    adds every tracked `.rs` file under the package directory that no other
    workspace member's directory contains: a file no `mod` reaches can still
    be compiled by a macro the walk does not read. A manifest that declares no
    package, or is not a member, fences nothing off. A package no manifest
    names has no files.
    """
    manifests = tip.manifests[0]
    members = member_directories(manifests)
    wanted = frozenset(packages)
    files: set[str] = set()
    errors: dict[str, str] = {}
    for path, manifest in manifests.items():
        if package_name(manifest) not in wanted:
            continue
        directory = posixpath.dirname(path)
        prefix = f"{directory}/" if directory else ""
        for root in target_roots(manifest, directory, tip.index):
            reached, unreadable = compiled_files(tip.index, tip.read, root)
            files |= reached
            errors |= unreadable
        nested = tuple(f"{member}/" for member in members
                       if member and member != directory and f"{member}/".startswith(prefix))
        files |= {file for file in tip.paths
                  if file.endswith(".rs") and file.startswith(prefix)
                  and not file.startswith(nested)}
    return files, errors


def cfg_clippy_problems(tip: Revision, packages: Iterable[str]) -> list[str]:
    """One problem per `cfg` predicate naming `clippy` in a pushed package.

    The scan covers the files the package compiles (`package_sources`) and no
    other text. A file holds such a predicate only if the word `clippy` occurs
    in it, and the lexer then decides whether a hit is code and whether the
    predicate -- not a `cfg_attr` body -- names `clippy`. A file that cannot be
    read as Rust is refused: its predicates, and the modules it declares,
    cannot be read.
    """
    files, unreadable = package_sources(tip, packages)
    problems = [f"{path}: cannot be read as Rust ({error}), so the gate cannot tell "
                "whether a `cfg` predicate names `clippy`"
                for path, error in sorted(unreadable.items())]
    for path in sorted(files.difference(unreadable)):
        text = tip.read(path) or ""
        if not CLIPPY_PREDICATE.search(text):
            continue
        try:
            lines = cfg_clippy_lines(text)
        except ValueError as error:
            problems.append(
                f"{path}: cannot be read as Rust ({error}), so the gate cannot tell "
                "whether a `cfg` predicate names `clippy`")
            continue
        problems += [
            f"{path}:{line}: a `cfg` predicate names `clippy`, which clippy-driver sets "
            "and rustc does not, so the gate cannot count the code it guards"
            for line in lines
        ]
    return problems


def second_target_problems(tip: Revision, cast_modules: Mapping[str, str]) -> list[str]:
    """One problem per package whose registered cast module (`cast_modules`
    maps a package to its path) more than one of its crate targets compile.

    `clippy::duplicate_mod` works per crate, and `sites()` merges a span two
    builds report, so a second target that mounts the module is counted once
    and linted once. A file the walk reaches and cannot read fails the package:
    the gate cannot tell what that file mounts.
    """
    problems = []
    for path, manifest in tip.manifests[0].items():
        package = package_name(manifest)
        cast = cast_modules.get(package) if package else None
        if cast is None:
            continue
        roots: list[str] = []
        unreadable: dict[str, str] = {}
        for root in target_roots(manifest, posixpath.dirname(path), tip.index):
            reached, failed = compiled_files(tip.index, tip.read, root)
            unreadable |= failed
            if cast in reached:
                roots.append(root)
        problems += [f"{package}: {file}: {error}, so the gate cannot tell whether {cast} is "
                     "compiled by more than one crate target"
                     for file, error in sorted(unreadable.items())]
        if len(roots) > 1:
            problems.append(
                f"{package}: cast module {cast} is compiled by more than one crate "
                f"target ({', '.join(roots)}); clippy::duplicate_mod cannot see a "
                "second target"
            )
    return problems


def pushed_diff(repo: pathlib.Path, base: str | None, tip: str, form: list[str]) -> bytes:
    """`git diff base..tip` in `form`, under the settings `pushed_additions` pins."""
    env = {k: v for k, v in os.environ.items() if k != "GIT_DIFF_OPTS"}
    if not base:
        base = subprocess.run(
            ["git", "-C", str(repo), "hash-object", "-t", "tree", "--stdin"],
            input="", capture_output=True, text=True, encoding="utf-8", check=True,
            env=env,
        ).stdout.strip()
    command = ["git", "-c", "core.quotePath=false", "-C", str(repo), "diff", *form,
               "--diff-algorithm=myers", "--no-color", "--no-ext-diff", "--no-textconv",
               "--no-relative", "-M", "-l0", base, tip]
    return subprocess.run(command, capture_output=True, env=env, check=True).stdout


# Files whose change can compile existing code differently: manifests (features,
# targets, `[lib] path`), cargo config (`rustflags`), and the toolchain pin
# (a build script's cfg probes). A build script counts only at its package root,
# beside a manifest: `src/**/build.rs` is often an ordinary module.
BUILD_INPUTS = ("Cargo.toml", "rust-toolchain", "rust-toolchain.toml")


def package_build_script(repo: pathlib.Path, tip: str, path: str) -> bool:
    """Whether `path` is a `build.rs` beside a `Cargo.toml` at `tip`. A manifest
    present at the base alone was deleted in the range, a trigger itself."""
    directory, _, name = path.rpartition("/")
    if name != "build.rs":
        return False
    manifest = f"{directory}/Cargo.toml" if directory else "Cargo.toml"
    return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{tip}:{manifest}"],
                          capture_output=True).returncode == 0


def changed_entries(repo: pathlib.Path, base: str, tip: str) -> list[tuple[str, ...]]:
    """The paths of each change the range makes. A rename gives its source and
    target, so a file moved between packages changes both. A copy is not one:
    without `-C` it diffs as an added file, every line added."""
    fields = pushed_diff(repo, base, tip, ["--name-status", "-z"]).decode("utf-8").split("\0")
    entries: list[tuple[str, ...]] = []
    index = 0
    while index < len(fields) and fields[index]:
        width = 3 if fields[index][0] == "R" else 2
        entries.append(tuple(fields[index + 1:index + width]))
        index += width
    return entries


def base_triggers(repo: pathlib.Path, base: str, tip: str,
                  cast_modules: frozenset[str] = frozenset()) -> list[str]:
    """Why the range needs the base count: each change that can bring existing
    casts into a pushed package without adding their lines, and each change
    to a path in `cast_modules`, whose added casts only the base count holds.
    The hook names no member here, so `cast_modules` is every member's: a
    path another member registers costs one extra compile, never a pass."""
    reasons: list[str] = []
    for paths in changed_entries(repo, base, tip):
        if len(paths) == 2:
            reasons.append(" -> ".join(paths))
        for path in paths:
            name = path.rsplit("/", 1)[-1]
            if (name in BUILD_INPUTS or "/.cargo/" in f"/{path}"
                    or package_build_script(repo, tip, path)):
                reasons.append(f"{path} changed")
            if path in cast_modules:
                reasons.append(f"{path} is a cast module")
    return list(dict.fromkeys(reasons))


# Toolchain pins: a change reaches every package by no resolved dependency,
# so `resolved_changes` gates every member.
GLOBAL_INPUTS = ("rust-toolchain", "rust-toolchain.toml")


@dataclass(frozen=True)
class ResolvedPackage:
    """One workspace package as `cargo metadata` resolves it at one revision.

    `signature` holds the resolved inputs metadata reports for the package:
    its edition, rust-version, links, targets, declared and enabled
    features, each direct dependency with its package, extern name and
    kinds, and every package it reaches with that package's enabled
    features. A path package is named by its directory, so a retarget to
    another directory holding the same name and version differs. Paths are
    relative to the export, so two checkouts of one revision compare equal.
    Metadata unifies features across platforms and dependency kinds, so a
    feature that another platform's, a build or a dev edge already enables
    reads the same at both revisions even when the host's build of a
    package changes; callers that must see such a change follow `reaches`.
    `reaches` names every package the member depends on, directly or not.
    """

    signature: tuple
    reaches: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Resolution:
    """A workspace as `cargo metadata` resolves it for the host at one revision.

    `root_manifest` is the workspace root manifest relative to the export.
    `members` holds each workspace member's `ResolvedPackage`. `reach` maps
    every resolved package name, member or not, to the names it depends on
    directly or not, merged across the versions that share the name.
    """

    root_manifest: str
    members: dict[str, ResolvedPackage]
    reach: dict[str, frozenset[str]]


def _relative(path: str, export: pathlib.Path) -> str:
    """`path` relative to `export`, `/`-separated; raises outside it."""
    inner = pathlib.Path(os.path.realpath(path))
    outer = pathlib.Path(os.path.realpath(export))
    relative = inner.relative_to(outer).as_posix()
    return "" if relative == "." else relative


def resolution(record: dict, export: pathlib.Path) -> Resolution:
    """The workspace a `cargo metadata` record resolves, relative to `export`."""
    members = set(record["workspace_members"])
    by_id = {package["id"]: package for package in record["packages"]}

    def label(package_id: str) -> str:
        package = by_id[package_id]
        source = package["source"] or (
            "path " + _relative(str(pathlib.Path(package["manifest_path"]).parent), export))
        return f"{package['name']}@{package['version']} {source}"

    nodes = {node["id"]: node for node in record["resolve"]["nodes"]}

    def reached(package_id: str) -> set[str]:
        """Every package `package_id` depends on, directly or not."""
        seen: set[str] = set()
        pending = [dependency["pkg"] for dependency in nodes[package_id]["deps"]]
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            pending.extend(dependency["pkg"] for dependency in nodes[current]["deps"])
        return seen

    resolved: dict[str, ResolvedPackage] = {}
    for package_id in members:
        package = by_id[package_id]
        node = nodes[package_id]
        reaches = reached(package_id)
        targets = tuple(sorted(
            (
                target["name"], tuple(target["kind"]), tuple(target["crate_types"]),
                target.get("edition", ""), tuple(sorted(target.get("required-features", []))),
                _relative(target["src_path"], export), target.get("test", True),
                target.get("doctest", True),
            )
            for target in package["targets"]
        ))
        dependencies = tuple(sorted(
            (
                label(dependency["pkg"]), dependency["name"],
                tuple(sorted((kind["kind"] or "normal", kind["target"] or "")
                             for kind in dependency["dep_kinds"])),
            )
            for dependency in node["deps"]
        ))
        signature = (
            package["edition"], package.get("rust_version") or "", package.get("links") or "",
            json.dumps(package["features"], sort_keys=True), targets,
            tuple(sorted(node["features"])), dependencies,
            tuple(sorted((label(current), tuple(sorted(nodes[current]["features"])))
                         for current in reaches)),
        )
        resolved[package["name"]] = ResolvedPackage(
            signature, frozenset(by_id[current]["name"] for current in reaches))
    reach: dict[str, frozenset[str]] = {}
    for package_id in nodes:
        name = by_id[package_id]["name"]
        reach[name] = reach.get(name, frozenset()) | frozenset(
            by_id[current]["name"] for current in reached(package_id))
    root = _relative(record["workspace_root"], export)
    return Resolution(f"{root}/Cargo.toml" if root else "Cargo.toml", resolved, reach)


def read_resolution(export: pathlib.Path, manifest: str,
                    config: pathlib.Path | None = None) -> Resolution:
    """The workspace `manifest` belongs to, resolved against the export's
    committed lock. `--filter-platform` keeps only the host's dependency
    edges, which are the ones clippy compiles; it does not filter features,
    which metadata reports unified across platforms (`ResolvedPackage`)."""
    from atlas_build_inputs import effective_compiler_environment

    manifest_path = export / manifest
    cargo_command = cargo(config)
    environment = effective_compiler_environment(manifest_path, export, cargo_command)
    out = subprocess.run(
        [*cargo_command, "metadata", "--format-version", "1", "--locked",
         "--filter-platform", "host-tuple", "--manifest-path", str(manifest_path)],
        cwd=export, env=environment,
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    return resolution(json.loads(out), export)


def changed_table_packages(base_text: str | None, tip_text: str | None) -> frozenset[str]:
    """The package names of every `[workspace.dependencies]` entry the range
    adds, removes or changes, at either side (`package = ...` renames)."""
    def table(text: str | None) -> dict:
        data = tomllib.loads(text) if text is not None else {}
        workspace = data.get("workspace")
        entries = workspace.get("dependencies") if isinstance(workspace, dict) else None
        return entries if isinstance(entries, dict) else {}

    def package_name(key: str, entry: object) -> str:
        renamed = entry.get("package") if isinstance(entry, dict) else None
        return renamed if isinstance(renamed, str) else key

    base, tip = table(base_text), table(tip_text)
    return frozenset(
        package_name(key, side[key])
        for key in base.keys() | tip.keys() if base.get(key) != tip.get(key)
        for side in (base, tip) if key in side
    )


def without_workspace_dependencies(text: str | None) -> dict | None:
    """A root manifest with `[workspace.dependencies]` removed: those entries
    reach a package only through its own resolved dependencies."""
    if text is None:
        return None
    data = tomllib.loads(text)
    workspace = data.get("workspace")
    if isinstance(workspace, dict):
        workspace.pop("dependencies", None)
    return data


def resolved_changes(repo: pathlib.Path, base: str, tip: str, base_export: pathlib.Path,
                     tip_export: pathlib.Path, manifest: str,
                     config: pathlib.Path | None = None) -> tuple[frozenset[str] | None, str]:
    """The members a changed root manifest compiles differently, or None and
    the reason when every member must be gated.

    A root manifest whose only change is to `[workspace.dependencies]` reaches
    a member only through the packages the member resolves and the features
    their compilation enables. A member is changed when its resolved
    signature differs, when it is new, or when it is or reaches a package a
    changed entry names or one such a package reaches, at either revision:
    an entry's features enable features only of its package and the
    packages that package depends on, and metadata's unified features can
    hide that change from every signature (`ResolvedPackage`). Any other root
    change, a range that leaves the root manifest unchanged, a changed
    toolchain pin, cargo config or nextest config, a manifest Python cannot
    parse, and a revision cargo cannot resolve gate every member: those
    reach members by no resolved dependency this reads.
    """
    from atlas_build_inputs import BuildIdentityError

    try:
        paths = [path for entry in changed_entries(repo, base, tip) for path in entry]
    except (subprocess.CalledProcessError, OSError, UnicodeDecodeError) as error:
        return None, f"git could not list the pushed range ({error})"
    for path in paths:
        if (path.rsplit("/", 1)[-1] in GLOBAL_INPUTS or "/.cargo/" in f"/{path}"
                or f"/{path}".endswith("/.config/nextest.toml")):
            return None, f"{path} changed"
    try:
        base_resolution = read_resolution(base_export, manifest, config)
        tip_resolution = read_resolution(tip_export, manifest, config)
    except (subprocess.CalledProcessError, OSError, ValueError, KeyError) as error:
        return None, f"cargo metadata could not resolve both revisions ({error})"
    except BuildIdentityError as error:
        # The build environment parses `manifest` with `tomllib` first, so a
        # manifest cargo accepts but Python cannot parse ends here.
        return None, f"the build environment cannot be read ({error})"
    root_manifest = base_resolution.root_manifest
    if tip_resolution.root_manifest != root_manifest:
        return None, "the workspace root moved"
    if root_manifest not in paths:
        return None, f"{root_manifest} is not changed by the pushed range"
    base_text, tip_text = git_file(repo, base, root_manifest), git_file(repo, tip, root_manifest)
    try:
        if without_workspace_dependencies(base_text) != without_workspace_dependencies(tip_text):
            return None, f"{root_manifest} changes beyond [workspace.dependencies]"
        entries = changed_table_packages(base_text, tip_text)
    except tomllib.TOMLDecodeError as error:
        return None, f"{root_manifest} does not parse as TOML here ({error})"
    touched = set(entries)
    for name in entries:
        touched |= base_resolution.reach.get(name, frozenset())
        touched |= tip_resolution.reach.get(name, frozenset())
    base_packages = base_resolution.members
    return frozenset(
        name for name, package in tip_resolution.members.items()
        if name not in base_packages or base_packages[name].signature != package.signature
        or name in touched or package.reaches & touched
        or base_packages[name].reaches & touched
    ), ""


def git_file(repo: pathlib.Path, revision: str, path: str) -> str | None:
    """The file at `path` in `revision`, or None when the revision has none."""
    run = subprocess.run(["git", "-C", str(repo), "show", f"{revision}:{path}"],
                         capture_output=True)
    if run.returncode != 0:
        return None
    return run.stdout.decode("utf-8", errors="replace")


def path_clean(path: str) -> str:
    """`path` as rustc finds a file on the Windows host the gate runs on:
    backslash separators accepted, `.` and `..` components collapsed."""
    return posixpath.normpath(path.replace("\\", "/"))


def path_key(path: str) -> str:
    """The key a path is looked up under: `path_clean` with case folded, as
    NTFS compares names. The reading is the Windows one on every host, a safe
    superset where a Linux checkout holds names that differ only in case; two
    such tracked paths count as one."""
    return path_clean(path).casefold()


def path_index(paths: Iterable[str]) -> dict[str, str]:
    """Tracked paths by `path_key`."""
    return {path_key(path): path for path in paths}


class ManifestError(ValueError):
    """A manifest `tomllib` rejects. Cargo accepts TOML that `tomllib` does not
    (a multi-line inline table), so the gate cannot tell which package the
    file declares and must not read the package as absent."""

    def __init__(self, path: str, error: Exception) -> None:
        super().__init__(f"{path} does not parse as TOML here ({error}), so the gate "
                         "cannot tell which package it declares")
        self.path = path


class Revision:
    """The tracked files of one revision. Blobs are read through one `git
    cat-file --batch` process, started on the first read, so a scan that reads
    thousands of files pays for one process, not one per file."""

    def __init__(self, repo: pathlib.Path, revision: str) -> None:
        listing = subprocess.run(
            ["git", "-C", str(repo), "ls-tree", "-r", "-z", revision],
            capture_output=True, check=True).stdout.decode("utf-8", errors="replace")
        self.repo = repo
        self.blobs: dict[str, str] = {}
        for entry in listing.split("\0"):
            fields, _, path = entry.partition("\t")
            if path and fields.split()[1] == "blob":  # a gitlink is a commit
                self.blobs[path] = fields.split()[2]
        self.paths = list(self.blobs)
        self._texts: dict[str, str] = {}
        self._reader: subprocess.Popen[bytes] | None = None

    def __enter__(self) -> Revision:
        return self

    def __exit__(self, *exception: object) -> None:
        reader = self._reader
        if reader is not None:
            assert reader.stdin is not None and reader.stdout is not None
            reader.stdin.close()
            reader.wait()
            reader.stdout.close()

    def read(self, path: str) -> str | None:
        """The text of `path`, or None when the revision tracks no such file."""
        oid = self.blobs.get(path)
        if oid is None:
            return None
        if path not in self._texts:
            if self._reader is None:
                self._reader = subprocess.Popen(
                    ["git", "-C", str(self.repo), "cat-file", "--batch"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            reader = self._reader
            assert reader.stdin is not None and reader.stdout is not None
            reader.stdin.write(f"{oid}\n".encode())
            reader.stdin.flush()
            size = int(reader.stdout.readline().split()[2])
            self._texts[path] = reader.stdout.read(size + 1)[:size].decode(
                "utf-8", errors="replace")
        return self._texts[path]

    @functools.cached_property
    def index(self) -> dict[str, str]:
        """The tracked paths by `path_index` key."""
        return path_index(self.paths)

    @functools.cached_property
    def manifests(self) -> tuple[dict[str, dict], dict[str, ManifestError]]:
        """Every tracked manifest as (parsed by path, refused by path)."""
        parsed: dict[str, dict] = {}
        refused: dict[str, ManifestError] = {}
        for path in self.paths:
            if is_manifest(path):
                try:
                    parsed[path] = self.manifest_at(path) or {}
                except ManifestError as error:
                    refused[path] = error
        return parsed, refused

    def manifest_at(self, path: str) -> dict | None:
        """The parsed manifest at `path`; None when none is tracked there; an
        unparseable one raises `ManifestError`."""
        text = self.read(path)
        if text is None:
            return None
        try:
            return tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise ManifestError(path, error) from error


def is_manifest(path: str) -> bool:
    """Whether `path` is a `Cargo.toml`."""
    return posixpath.basename(path) == "Cargo.toml"


def package_name(manifest: dict) -> str | None:
    """The package a manifest declares, or None when it declares none."""
    package = manifest.get("package")
    if isinstance(package, dict) and isinstance(package.get("name"), str):
        return package["name"]
    return None


def member_regex(pattern: str) -> re.Pattern[str]:
    """Cargo's member glob: `*` and `?` stop at a separator, `**` crosses it."""
    parts: list[str] = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if pattern.startswith("**", index):
                parts.append(".*")
                index += 2
                continue
            parts.append("[^/]*")
        elif char == "?":
            parts.append("[^/]")
        elif char == "[":
            end = pattern.find("]", index + 1)
            if end == -1:
                parts.append(re.escape(char))
            else:
                parts.append(pattern[index:end + 1])
                index = end + 1
                continue
        else:
            parts.append(re.escape(char))
        index += 1
    return re.compile("^" + "".join(parts) + "$")


def member_manifests(member: str, manifests: list[str]) -> list[str]:
    """The manifests a member entry names, under cargo's glob rules."""
    entry = member.rstrip("/")
    if not any(char in entry for char in "*?["):
        path = f"{entry}/Cargo.toml" if entry not in ("", ".") else "Cargo.toml"
        return [path] if path in manifests else []
    pattern = member_regex(entry)
    named = []
    for manifest in manifests:
        directory = "" if manifest == "Cargo.toml" else manifest[: -len("/Cargo.toml")]
        if pattern.match(directory):
            named.append(manifest)
    return named


def is_excluded(directory: str, pattern: str) -> bool:
    """Whether a member directory lies under an excluded path."""
    entry = pattern.rstrip("/")
    if any(char in entry for char in "*?["):
        return bool(member_regex(entry).match(directory))
    return directory == entry or directory.startswith(entry + "/")


def base_workspace_packages(repo: pathlib.Path, base: str) -> frozenset[str]:
    """The packages the workspace at `base` had.

    The root manifest at `base` names the members, and each member manifest
    names its package. A repository that is one package is its own workspace.
    A manifest `tomllib` rejects raises `ManifestError`.
    """
    with Revision(repo, base) as tree:
        data = tree.manifest_at("Cargo.toml")
        if data is None:
            return frozenset()
        workspace = data.get("workspace")
        if not isinstance(workspace, dict):
            name = package_name(data)
            return frozenset({name}) if name else frozenset()
        packages = set()
        name = package_name(data)
        if name:
            packages.add(name)
        excluded = [entry for entry in workspace.get("exclude", []) if isinstance(entry, str)]
        manifests = [path for path in tree.paths if is_manifest(path)]
        for member in workspace.get("members", []):
            if not isinstance(member, str):
                continue
            for manifest in member_manifests(member, manifests):
                directory = posixpath.dirname(manifest)
                if any(is_excluded(directory, entry) for entry in excluded):
                    continue
                name = package_name(tree.manifest_at(manifest) or {})
                if name:
                    packages.add(name)
        return frozenset(packages)


def target_roots(manifest: dict, directory: str, index: Mapping[str, str]) -> list[str]:
    """The crate-root files of one package: library, build script, bins, tests,
    examples and benches that exist among the tracked paths `index` (`path_index`).

    Specification: the Cargo Book, "Target auto-discovery" in
    https://doc.rust-lang.org/cargo/reference/cargo-targets.html and
    https://doc.rust-lang.org/cargo/guide/project-layout.html. The defaults
    are `src/lib.rs`, `build.rs`, `src/main.rs`, and in `src/bin`, `tests`,
    `examples` and `benches` each `<name>.rs` and each `<name>/main.rs`; the
    `autolib`, `autobins`, `autotests`, `autoexamples` and `autobenches` keys
    switch the discovery off, and `[lib]`, `[[bin]]`, `[[test]]`, `[[example]]`
    and `[[bench]]` add targets, a missing `path` being inferred from the name.
    The build script is a root: clippy-driver wraps every rustc call of a
    workspace package, the script's included (recalled, not run here).
    """
    prefix = f"{directory}/" if directory else ""
    package = manifest.get("package") if isinstance(manifest.get("package"), dict) else {}
    lib = manifest.get("lib") if isinstance(manifest.get("lib"), dict) else {}
    own = {path.removeprefix(prefix) for path in index.values() if path.startswith(prefix)}
    found = []
    if "lib" in manifest or package.get("autolib", True) is not False:
        found.append(lib["path"] if isinstance(lib.get("path"), str) else "src/lib.rs")
    if package.get("build", True) is not False:
        found.append(package["build"] if isinstance(package.get("build"), str) else "build.rs")
    for key, folder, auto in (("bin", "src/bin", "autobins"), ("test", "tests", "autotests"),
                              ("example", "examples", "autoexamples"),
                              ("bench", "benches", "autobenches")):
        entries = manifest.get(key)
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if isinstance(entry.get("path"), str):
                found.append(entry["path"])
            elif isinstance(name, str):
                found += [f"{folder}/{name}.rs", f"{folder}/{name}/main.rs"]
                if key == "bin" and name == package.get("name"):
                    found.append("src/main.rs")
        if package.get(auto, True) is not False:
            if key == "bin":
                found.append("src/main.rs")
            found += [path for path in own
                      if re.fullmatch(rf"{folder}/([^/]+|[^/]+/main)\.rs", path)]
    keys = dict.fromkeys(path_key(prefix + path) for path in found)
    return [index[key] for key in keys if key in index]


@dataclass(frozen=True)
class Module:
    """A `mod` item as written: its name, its `#[path]` values, and the values
    under `cfg_attr`, whose predicate is not evaluated."""

    name: str
    paths: tuple[str, ...] = ()
    conditional: tuple[str, ...] = ()


@dataclass(frozen=True)
class Mount:
    """A `mod name;` declaration and the inline modules around it, outermost first."""

    module: Module
    enclosing: tuple[Module, ...]


def attribute_paths(tokens: list[tuple[str, str]], head: str) -> tuple[list[str], list[str]]:
    """The `path = "..."` values one outer attribute sets: (`#[path]`, `cfg_attr`)."""
    found = [literal(tokens[index + 2][1]) for index in range(len(tokens) - 2)
             if tokens[index] == ("word", "path") and tokens[index + 1] == ("punct", "=")
             and tokens[index + 2][0] == "string"]
    return (found, []) if head == "path" else ([], found) if head == "cfg_attr" else ([], [])


@functools.cache
def mod_declarations(text: str) -> tuple[tuple[Mount, ...], tuple[str, ...]]:
    """The `mod name;` declarations and the `include!("path")` literals of one
    file, read from its token stream.

    An inline `mod name { ... }` is an enclosing module of what it holds; any
    other brace is none. A `mod` the tokens show is seen wherever it stands,
    macro body included, and a `mod` a macro writes from `$` is not.
    """
    tokens = lex(text)
    starts = {start: (end, inner, head) for start, end, inner, head in attributes(tokens)}
    found: list[Mount] = []
    included: list[str] = []
    inline: list[Module | None] = []
    plain: list[str] = []
    conditional: list[str] = []
    index = 0
    while index < len(tokens):
        if index in starts:
            end, inner, head = starts[index]
            if not inner:
                paths, conditions = attribute_paths(tokens[index:end], head)
                plain, conditional = plain + paths, conditional + conditions
            index = end
            continue
        kind, word = tokens[index]
        after = tokens[index + 1:index + 4]
        if ((kind, word) == ("word", "include") and len(after) == 3 and after[0] == ("punct", "!")
                and after[1] in (("punct", "("), ("punct", "["), ("punct", "{"))
                and after[2][0] == "string"):
            included.append(literal(after[2][1]))
            index += 4
            continue
        if ((kind, word) == ("word", "mod") and len(after) >= 2 and after[0][0] == "word"
                and after[1] in (("punct", ";"), ("punct", "{"))):
            module = Module(after[0][1].removeprefix("r#"), tuple(plain), tuple(conditional))
            if after[1][1] == ";":
                found.append(Mount(module, tuple(m for m in inline if m)))
            else:
                inline.append(module)
            plain, conditional, index = [], [], index + 3
            continue
        if kind == "punct" and word in "{};":
            if word == "{":
                inline.append(None)
            elif word == "}" and inline:
                inline.pop()
            plain, conditional = [], []
        index += 1
    return tuple(found), tuple(included)


def module_directories(states: set[tuple[str, str | None]],
                       module: Module) -> set[tuple[str, str | None]]:
    """The (directory, stem) states inside the inline `module` of each state in
    `states`: its `#[path]` values joined to the directory, and without one its
    name after the directory and stem."""
    found: set[tuple[str, str | None]] = set()
    for directory, stem in states:
        found |= {(posixpath.join(directory, path), None)
                  for path in (*module.paths, *module.conditional)}
        if not module.paths:
            found.add((posixpath.join(directory, *filter(None, [stem]), module.name), None))
    return found


def compiled_files(index: Mapping[str, str], read: Callable[[str], str | None],
                   root: str) -> tuple[set[str], dict[str, str]]:
    """The files the crate root `root` compiles, and why any could not be read:
    (tracked paths, error by path). `index` is `path_index` of the tracked
    paths and `read` yields a tracked file's text.

    Specification: the Rust Reference, "Module source filenames" and "The
    path attribute" in https://doc.rust-lang.org/reference/items/modules.html,
    and rustc 1.97.0 `--emit=dep-info` where the Reference is silent. A module
    has a directory and, for a file that is not `mod.rs`, a stem: `mod name;`
    loads `<directory>/<stem>/name.rs` or `.../name/mod.rs`, and each inline
    module adds a component. `#[path]` on `mod name;` is joined to the
    directory without the stem, and an inline module's own `#[path]` replaces
    its component, joined likewise (`#[path = "num"] mod m { mod cast; }`
    in `src/a.rs` loads `src/num/cast.rs`). A file loaded through `#[path]` or
    `include!("literal")`, the latter relative to the file holding the call,
    resolves its children beside itself. A `cfg_attr` path counts as both
    outcomes, since its predicate is not evaluated. Each candidate is
    normalised and matched as `path_index` reads names. Not followed: a `mod`
    a macro writes, and `include!` of anything but a literal.
    """
    files: set[str] = set()
    errors: dict[str, str] = {}
    seen: set[tuple[str, str, str | None]] = set()
    pending: list[tuple[str, str, str | None]] = [(root, posixpath.dirname(root), None)]
    while pending:
        file, directory, stem = pending.pop()
        file = path_clean(file)
        if (path_key(file), directory, stem) in seen:
            continue
        seen.add((path_key(file), directory, stem))
        real = index.get(path_key(file))
        text = None if real is None else read(real)
        if real is None or text is None:
            continue
        files.add(real)
        try:
            mounts, included = mod_declarations(text)
        except ValueError as error:
            errors[real] = str(error)
            continue
        for literal_path in included:
            path = path_clean(posixpath.join(posixpath.dirname(file), literal_path))
            pending.append((path, posixpath.dirname(path), None))
        for mount in mounts:
            states = {(directory, stem)}
            for module in mount.enclosing:
                states = module_directories(states, module)
            module = mount.module
            for here, here_stem in states:
                for path in (*module.paths, *module.conditional):
                    path = path_clean(posixpath.join(here, path))
                    pending.append((path, posixpath.dirname(path), None))
                if not module.paths:
                    base = posixpath.join(here, *filter(None, [here_stem]))
                    pending += [(posixpath.join(base, f"{module.name}.rs"), base, module.name),
                                (posixpath.join(base, module.name, "mod.rs"),
                                 posixpath.join(base, module.name), None)]
    return files, errors


def held_to_base(repo: pathlib.Path, base: str, candidates: Iterable[str],
                 measured: set[Site]) -> frozenset[str]:
    """The candidate packages the base can hold to a count.

    A package the base never had carries no count there: its casts are the
    debt its row in `cast-baseline.json` records, and a crate that returns
    to the workspace brings that debt with it. The membership is read from
    the base revision's own manifests, so a package the push adds is absent
    from it; a package the base measured is present even when its workspace
    was a nested one.
    """
    if not base:
        return frozenset()
    present = set(base_workspace_packages(repo, base))
    present.update(site.package for site in measured)
    return frozenset(candidates) & present


def new_standalone_owners(repo: pathlib.Path, base: str, tip: str,
                          manifests: Iterable[str], base_export: pathlib.Path,
                          tip_export: pathlib.Path, config: pathlib.Path | None = None,
                          metadata_timeout: float = 120.0) -> frozenset[str]:
    """New singleton owners proven from native metadata on immutable exports.

    Unsupported topology keeps the ordinary historical comparison.
    """
    from lockfile import tracked_texts

    base_texts = tracked_texts(repo, staged=False, revision=base)
    tip_texts = tracked_texts(repo, staged=False, revision=tip)
    base_manifests = {name: text for name, text in base_texts.items()
                      if pathlib.PurePosixPath(name).name == "Cargo.toml"}
    documents: dict[str, dict[str, object]] = {}
    for name, text in base_manifests.items():
        try:
            documents[name] = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise ValueError(f"{base}:{name} does not parse as TOML ({error})") from error
    candidates = []
    for manifest in set(manifests):
        path = pathlib.PurePosixPath(manifest)
        lock = path.with_name("Cargo.lock").as_posix()
        if (manifest in base_manifests and manifest in tip_texts
                and lock not in base_texts and lock in tip_texts):
            candidates.append((manifest, lock))
    if len(candidates) != 1:
        return frozenset()
    manifest, lock = candidates[0]
    path = pathlib.PurePosixPath(manifest)
    root_workspace = documents.get("Cargo.toml", {}).get("workspace")
    package = documents[manifest].get("package")
    if (path == pathlib.PurePosixPath("Cargo.toml")
            or not isinstance(root_workspace, dict)
            or root_workspace.get("exclude", []) != []
            or not isinstance(package, dict)
            or "workspace" in documents[manifest] or "workspace" in package
            or {name for name in base_texts if name.endswith("Cargo.lock")}
            != {"Cargo.lock"}
            or {name for name in tip_texts if name.endswith("Cargo.lock")}
            != {"Cargo.lock", lock}):
        return frozenset()

    deadline = time.monotonic() + min(metadata_timeout, 120.0)

    def read_workspace(export: pathlib.Path, relative: str) -> Workspace:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("cargo metadata exhausted the cast-gate deadline")
        return workspace(export, config, relative, export, remaining)

    def relative_members(space: Workspace, export: pathlib.Path) -> dict[str, str]:
        export_root = pathlib.Path(os.path.realpath(export))
        found = {}
        for member_path, name in space.member_manifests().items():
            try:
                relative = pathlib.Path(os.path.realpath(member_path)).relative_to(export_root)
            except ValueError as error:
                raise ValueError(f"workspace member lies outside {export}") from error
            found[relative.as_posix()] = name
        return found

    base_space = read_workspace(base_export, "Cargo.toml")
    base_members = relative_members(base_space, base_export)
    if (pathlib.Path(os.path.realpath(base_space.root))
            != pathlib.Path(os.path.realpath(base_export))
            or manifest in base_members
            or set(base_members) - {"Cargo.toml"}
            != set(base_manifests) - {"Cargo.toml", manifest}):
        return frozenset()
    candidate_space = read_workspace(tip_export, manifest)
    candidate_members = relative_members(candidate_space, tip_export)
    if (pathlib.Path(os.path.realpath(candidate_space.root))
            != pathlib.Path(os.path.realpath(tip_export / path.parent))
            or set(candidate_members) != {manifest}):
        return frozenset()
    candidate_name = candidate_members[manifest]
    if candidate_name in base_space.names().values():
        raise ValueError(
            f"{manifest}: newly owned package name already exists at the base: {candidate_name}"
        )
    return frozenset({manifest})


@dataclass(frozen=True)
class Baseline:
    """Sanctioned conversion modules, per-package cast modules, and per-package
    site counts. A JSON object repeating a key is refused: `json` would keep
    the last value, and a second path for one package is a second module."""

    sanctioned: dict[str, frozenset[str]]
    counts: dict[str, dict[str, int]]
    cast_modules: dict[str, dict[str, str]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: pathlib.Path) -> Baseline:
        """The baseline at `path`; a value of the wrong shape is a ValueError."""
        return cls.parse(path.read_text(encoding="utf-8"), str(path))

    @classmethod
    def parse(cls, text: str, path: str) -> Baseline:
        """The baseline in `text`, read from `path`; a wrong shape is a ValueError."""
        def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
            keys = [key for key, _ in pairs]
            for key in keys:
                if keys.count(key) > 1:
                    raise ValueError(f"{path}: the baseline repeats the key {key!r}")
            return dict(pairs)

        data = json.loads(text, object_pairs_hook=unique)
        if not isinstance(data, dict):
            raise ValueError(f"{path}: the baseline is a JSON object")
        sanctioned = data.get("sanctioned", {})
        counts = data.get("counts", {})
        cast_modules = data.get("cast_modules", {})
        if not (isinstance(sanctioned, dict) and all(
                isinstance(paths, list) and all(isinstance(p, str) for p in paths)
                for paths in sanctioned.values())):
            raise ValueError(f"{path}: `sanctioned` maps members to lists of paths")
        if not (isinstance(counts, dict) and all(
                isinstance(rows, dict) and all(
                    isinstance(k, str) and type(v) is int for k, v in rows.items())
                for rows in counts.values())):
            raise ValueError(f"{path}: `counts` maps members to package counts")
        if not (isinstance(cast_modules, dict) and all(
                isinstance(modules, dict) and all(isinstance(p, str) for p in modules.values())
                for modules in cast_modules.values())):
            raise ValueError(f"{path}: `cast_modules` maps members to one path per package")
        for member in sorted({*sanctioned, *cast_modules}):
            named = [*cast_modules.get(member, {}).values(), *sanctioned.get(member, [])]
            for module in named:
                if named.count(module) > 1:
                    raise ValueError(f"{path}: {member} names {module} more than once")
        return cls(
            {m: frozenset(p) for m, p in sanctioned.items()},
            {m: dict(c) for m, c in counts.items()},
            {m: dict(p) for m, p in cast_modules.items()},
        )


TOKEN = re.compile(r"""(?P<space>[\s\ufeff]+)|(?P<comment>//[^\n]*)
    |(?P<string>[bc]?r(?P<hashes>\#*)"[\s\S]*?"(?P=hashes)|[bc]?"(?:\\[\s\S]|[^"\\])*")
    |(?P<char>b?'(?:\\(?:x\w\w|u\{\w*\}|.)|[^\\'\n])')|(?P<lifetime>'(?:r\#)?\w+)
    |(?P<word>(?:r\#)?\w+)|(?P<punct>[!\#-/:-@\[-^`{-~])""", re.X)
COPIES = "; one `as` there can compile to many casts the gate counts once"  # one site per span
# The attributes a cast module may carry: single-word built-ins, which no macro rebinds
# (rustc 1.97.0: E0659; `cfg` is reserved). `rustfmt::skip` is no such name: `use pm as
# rustfmt;` or a renamed dependency makes it a macro.
ATTRIBUTES = frozenset("allow cfg cold deny doc expect forbid inline must_use repr "
                       "track_caller warn".split())
UNARY_AFTER = frozenset("break if in match return while yield".split())  # `!` is a not
# The tokens an `impl` item follows; after any other, `impl` names a type.
ITEM_START = frozenset({("punct", ";"), ("punct", "{"), ("punct", "}"), ("punct", "]"),
                        ("word", "unsafe")})
# clippy 1.97.0's `as` and pointer cast lints (`clippy-driver -W help`). A name
# pattern also admits `match_as_ref` and eleven more Option, str and XOR lints.
CAST_LINTS = frozenset(f"clippy::{name}" for name in (
    "as_conversions as_pointer_underscore as_ptr_cast_mut as_underscore borrow_as_ptr "
    "cast_abs_to_unsigned cast_enum_constructor cast_enum_truncation cast_lossless "
    "cast_nan_to_int cast_possible_truncation cast_possible_wrap cast_precision_loss "
    "cast_ptr_alignment cast_sign_loss cast_slice_different_sizes "
    "cast_slice_from_raw_parts char_lit_as_u8 confusing_method_to_numeric_cast "
    "fn_to_numeric_cast fn_to_numeric_cast_any fn_to_numeric_cast_with_truncation "
    "invalid_upcast_comparisons needless_type_cast ptr_as_ptr ptr_cast_constness "
    "ptr_offset_with_cast ref_as_ptr unnecessary_cast").split())


def spans(text: str) -> Iterator[tuple[str, int, int]]:
    """The (kind, start, end) of every Rust token of `text`, space and comments
    (block ones nested) included. An unclosed literal or comment, or a stray
    character, raises."""
    index = 0
    while index < len(text):
        start = index
        if text.startswith("/*", index):
            depth, index = 1, index + 2
            while depth:
                close, opened = text.find("*/", index), text.find("/*", index)
                if close < 0:
                    raise ValueError("an unclosed block comment")
                depth, index = ((depth + 1, opened + 2) if 0 <= opened < close
                                else (depth - 1, close + 2))
            yield "comment", start, index
        elif match := TOKEN.match(text, index):
            index = match.end()
            yield match.lastgroup, start, index
        else:
            raise ValueError(f"no token at offset {index}")


def lex(text: str) -> list[tuple[str, str]]:
    """The (kind, text) Rust tokens of `text`, comments and space dropped."""
    return [(kind, text[start:end]) for kind, start, end in spans(text)
            if kind not in ("space", "comment")]


def attributes(tokens: list[tuple[str, str]]) -> list[tuple[int, int, bool, str]]:
    """Each attribute as (index of `#`, index after `]`, inner, path); unclosed raises."""
    found, index = [], 0
    while index < len(tokens):
        inner = tokens[index + 1:index + 2] == [("punct", "!")]
        opening = index + 1 + inner
        if tokens[index] != ("punct", "#") or tokens[opening:opening + 1] != [("punct", "[")]:
            index += 1
            continue
        path, end = "", opening + 1
        while end < len(tokens) and (tokens[end][0] == "word" or tokens[end] == ("punct", ":")):
            path, end = path + tokens[end][1], end + 1
        depth = 0
        for end in range(opening, len(tokens)):
            kind, text = tokens[end]
            depth += (text in "([{") - (text in ")]}") if kind == "punct" else 0
            if not depth:
                break
        else:
            raise ValueError("an unclosed attribute")
        found.append((index, end + 1, inner, path))
        index = end + 1
    return found


def copying_fault(tokens: list[tuple[str, str]],
                  spans: list[tuple[int, int, bool, str]]) -> str | None:
    """Why one `as` here could compile to many casts (attribute, macro, generic)."""
    for _, _, _, path in spans:
        if path not in ATTRIBUTES:
            return f"carries `#[{path}]`, not a built-in attribute it may use{COPIES}"
    for index, (kind, text) in enumerate(tokens):
        before = tokens[index - 1] if index else ("punct", ";")
        after = tokens[index + 1] if index + 1 < len(tokens) else ("punct", ";")
        if (kind == "word" and text in ("macro", "macro_rules")
                or (kind, text) == ("punct", "!") and before[0] == "word"
                and before[1] not in UNARY_AFTER and after != ("punct", "=")):
            return f"invokes or defines a macro{COPIES}"
        if kind == "word" and (
                text == "trait"
                or text == "impl" and (after == ("punct", "<") or before not in ITEM_START)
                or text == "fn" and tokens[index + 2:index + 3] == [("punct", "<")]):
            return f"declares a generic item, a trait or an `impl Trait` type{COPIES}"
    return None


def literal(text: str) -> str:  # the body of a string literal token
    return re.sub(r'^[bc]?r?#*"|"#*$', "", text)


def cast_module_fault(text: str | None) -> str | None:
    """Why `text` is not a cast module; None when it is one: it copies no cast
    (`copying_fault`) and opens, before any item, with exactly one inner
    `#![expect(...)]` naming only cast lints with a reason. Whether each lint
    fires is rustc's to judge (`unfulfilled_lint_expectations`)."""
    if text is None:
        return "is absent at the pushed tip"
    try:
        tokens = lex(text)
        spans = attributes(tokens)
    except ValueError as error:
        return f"cannot be lexed ({error}){COPIES}"
    if fault := copying_fault(tokens, spans):
        return fault
    expects = [(start, end) for start, end, inner, path in spans if inner and path == "expect"]
    if len(expects) != 1:
        return f"holds {len(expects)} inner `#![expect(...)]` attributes, not one"
    (start, end), leading = expects[0], 0
    for opening, closing, inner, _ in spans:
        if opening != leading or not inner:
            break
        leading = closing
    if start >= leading:
        return "places its `#![expect(...)]` after an item, so it does not scope the file"
    args = tokens[start + 5:end - 2] if tokens[start + 4] == ("punct", "(") else []
    at = next((at for at in range(len(args) - 2)
               if args[at:at + 2] == [("word", "reason"), ("punct", "=")]), None)
    if at is None or args[at + 2][0] != "string" or not literal(args[at + 2][1]).strip():
        return "gives its `#![expect(...)]` no reason"
    lints = "".join(text for _, text in args[:at] + args[at + 3:]).split(",")
    if not any(lints) or not all(lint in CAST_LINTS for lint in lints if lint):
        return "names a lint other than a cast lint, or none, in its `#![expect(...)]`"
    return None


def violations(member: str, found: set[Site], added: dict[str, set[int]],
               packages: Iterable[str], baseline: Baseline,
               base: set[Site] = frozenset(),
               base_packages: Iterable[str] = (),
               cast_modules: Mapping[str, tuple[str, str | None]] | None = None) -> list[str]:
    """Why the push fails, one line per violation; empty when it passes.

    `base` holds the sites of the pushed range's base, measured with the same
    selection. Each package in `base_packages` is held to its count there; any
    other package is held to its row alone.

    `cast_modules` maps a package to its cast module's path and fault at the
    tip; an added cast there passes with neither a fault nor a missing base count.
    A copying fault fails every module site: a use added elsewhere multiplies it.
    """
    sanctioned = baseline.sanctioned.get(member, frozenset())
    bare = sorted(s for s in found if s.path not in sanctioned)
    rows = baseline.counts.get(member, {})
    compared = frozenset(base_packages)
    problems = []
    for s in bare:
        path, fault = (cast_modules or {}).get(s.package, ("", None))
        where = f"{s.path}:{s.line}:{s.column}"
        if s.path == path and fault and fault.endswith(COPIES):
            problems.append(f"{where}: `as` cast in {s.package}'s cast module, which {fault}")
        elif added.get(s.path, set()).isdisjoint(range(s.line, s.line_end + 1)):
            continue
        elif s.path != path:
            problems.append(f"{where}: bare `as` cast on a line this push adds")
        elif fault:
            problems.append(f"{where}: `as` cast added to {s.package}'s cast module, "
                            f"which {fault}")
        elif s.package not in compared:
            problems.append(f"{where}: `as` cast added to {s.package}'s cast module "
                            "without a count at the pushed base")
    for package in sorted(set(packages)):
        count = sum(1 for s in bare if s.package == package)
        row = rows.get(package, 0)
        if count > row:
            problems.append(
                f"{package}: {count} bare `as` casts, above its baseline row of {row}"
            )
        if package in compared:
            before = sum(1 for s in base if s.package == package and s.path not in sanctioned)
            if count > before:
                problems.append(
                    f"{package}: {count} bare `as` casts, up from {before} at the pushed base"
                )
    return problems


def counts(found: set[Site], sanctioned: frozenset[str]) -> dict[str, int]:
    """Bare sites per package, sanctioned modules excluded."""
    tally: dict[str, int] = {}
    for site in found:
        if site.line and site.path not in sanctioned:
            tally[site.package] = tally.get(site.package, 0) + 1
    return dict(sorted(tally.items()))


def clippy(args: argparse.Namespace) -> int:
    export = pathlib.Path(args.export)
    if args.profile is not None or args.config is not None:
        if (not args.present_only or args.profile != HISTORICAL_CAST_PROFILE
                or args.config != HISTORICAL_CAST_CONFIG[1] or args.cargo_config is not None):
            raise ValueError("the historical cast profile requires its bound config and --present-only")
        _check_historical_profile(export, export / args.manifest, args.command_cwd or export)
    sites_file = pathlib.Path(args.sites)
    packages = list(args.package)
    if args.present_only:
        # The base of a range: a package the push adds, or a standalone crate
        # it creates, is absent there and counts zero; cargo refuses a `-p`
        # naming a package its workspace lacks.
        if not (export / args.manifest).is_file():
            write_sites(sites_file, set())
            return 0
        present = set(workspace(
            export, args.cargo_config, args.manifest, args.command_cwd
        ).names().values())
        packages = [p for p in packages if p in present]
        if args.package and not packages:
            write_sites(sites_file, set())
            return 0
    status, found = run_clippy(
        export, packages, args.cargo_config, args.manifest, args.command_cwd, profile=args.profile
    )
    write_sites(sites_file, found)
    if args.packages_out:
        names = sorted(set(workspace(
            export, args.cargo_config, args.manifest, args.command_cwd
        ).names().values()))
        # Bytes, so Windows text mode cannot turn the hook's lines into CRLF.
        pathlib.Path(args.packages_out).write_bytes(("\n".join(names) + "\n").encode("utf-8"))
    return status


def check(args: argparse.Namespace) -> int:
    baseline = Baseline.load(args.baseline)
    found: set[Site] = set()
    for path in args.sites:
        found |= read_sites(pathlib.Path(path))
    base: set[Site] = set()
    for path in args.base_sites:
        base |= read_sites(pathlib.Path(path))
    repo = pathlib.Path(args.repo)
    added = pushed_additions(repo, args.base or None, args.tip)
    problems = []
    try:
        held = held_to_base(repo, args.base, args.base_package, base)
    except ManifestError as error:
        held = frozenset()
        problems.append(str(error))
    held |= frozenset(args.zero_base_package)
    doubled = {s.package for s in found if not s.line}
    found, base = {s for s in found if s.line}, {s for s in base if s.line}
    modules = {}
    for package, path in baseline.cast_modules.get(args.member, {}).items():
        fault = cast_module_fault(git_file(repo, args.tip, path))
        if package in doubled and (fault is None or not fault.endswith(COPIES)):
            fault = f"shares its package with a file clippy finds mounted twice{COPIES}"
        modules[package] = (path, fault)
    problems += violations(args.member, found, added, args.package, baseline, base,
                           held, modules)
    with Revision(repo, args.tip) as tip:
        problems += [str(error) for error in tip.manifests[1].values()]
        problems += cfg_clippy_problems(tip, args.package)
        problems += second_target_problems(
            tip, {package: path for package, (path, _) in modules.items()})
    for problem in problems:
        print(f"cast gate: {problem}", file=sys.stderr)
    if problems and args.member not in baseline.counts:
        print(f"cast gate: {args.member} has no baseline rows; measure them with "
              "`atlas_cast_gate.py measure` and add them to cast-baseline.json",
              file=sys.stderr)
    return 1 if problems else 0


def raised_rows(base: Baseline, tip: Baseline) -> list[str]:
    """Each way `tip` loosens `base`: a row above its base row, a row for a
    package of a measured member that had none, a sanctioned path added to a
    measured member, or a package's cast module moved to another path. A
    member `base` does not measure is onboarding. A cast module added for a
    package that had none loosens nothing: its casts stay counted."""
    problems = []
    for member, rows in sorted(tip.counts.items()):
        if member not in base.counts:
            continue
        for package, count in sorted(rows.items()):
            before = base.counts[member].get(package, 0)
            if count > before:
                problems.append(f"{member}/{package} rises from {before} to {count}; "
                                "rows only fall")
        for path in sorted(tip.sanctioned.get(member, frozenset())
                           - base.sanctioned.get(member, frozenset())):
            problems.append(f"{member} sanctions {path}, which the base does not; "
                            "exclusion lowers a count without converting a cast")
        modules = base.cast_modules.get(member, {})
        for package, path in sorted(tip.cast_modules.get(member, {}).items()):
            if modules.get(package, path) != path:
                problems.append(f"{member}/{package} names a second cast module, {path}; "
                                f"its cast module is {modules[package]}")
    return problems


def baseline_at(repo: pathlib.Path, revision: str) -> Baseline | None:
    """The committed baseline at `revision`; None where the revision has none."""
    path = "scripts/cast-baseline.json"
    run = subprocess.run(["git", "-C", str(repo), "show", f"{revision}:{path}"],
                         capture_output=True)
    if run.returncode != 0:
        if subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet",
                           f"{revision}^{{commit}}"], capture_output=True).returncode != 0:
            raise ValueError(f"{revision} is not a commit in {repo}")
        return None
    return Baseline.parse(run.stdout.decode("utf-8"), f"{revision}:{path}")


def ratchet(args: argparse.Namespace) -> int:
    repo = pathlib.Path(args.repo)
    base = baseline_at(repo, args.base)
    tip = baseline_at(repo, args.tip)
    if base is None:
        return 0
    if tip is None:
        print("cast gate: the push deletes scripts/cast-baseline.json, which every "
              "member's push reads", file=sys.stderr)
        return 1
    problems = raised_rows(base, tip)
    for problem in problems:
        print(f"cast gate: baseline {problem}", file=sys.stderr)
    return 1 if problems else 0


def triggers(args: argparse.Namespace) -> int:
    # UTF-8 whatever the console code page: a path outside it must not stop
    # the gate (a Windows pipe defaults to the ANSI code page).
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    modules = Baseline.load(args.baseline).cast_modules
    paths = frozenset(path for packages in modules.values() for path in packages.values())
    for reason in base_triggers(pathlib.Path(args.repo), args.base, args.tip, paths):
        print(reason)
    return 0


def owners(args: argparse.Namespace) -> int:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    for manifest in sorted(new_standalone_owners(
            pathlib.Path(args.repo), args.base, args.tip, args.manifest,
            pathlib.Path(args.base_export), pathlib.Path(args.tip_export),
            args.cargo_config, args.metadata_timeout)):
        print(manifest)
    return 0


def changes(args: argparse.Namespace) -> int:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    changed, reason = resolved_changes(
        pathlib.Path(args.repo), args.base, args.tip, pathlib.Path(args.base_export),
        pathlib.Path(args.tip_export), args.manifest, args.cargo_config,
    )
    if changed is None:
        print(f"cast gate: every member is gated: {reason}", file=sys.stderr)
        return 3
    for package in sorted(changed):
        print(package)
    return 0


def measure(args: argparse.Namespace) -> int:
    baseline = Baseline.load(args.baseline)
    status, found = run_clippy(
        pathlib.Path(args.export), [], args.cargo_config, args.manifest, args.command_cwd
    )
    if status != 0:
        raise RuntimeError(f"clippy did not complete (exit {status})")
    tally = counts(found, baseline.sanctioned.get(args.member, frozenset()))
    print(json.dumps({args.member: tally}, indent=1, sort_keys=True))
    return 0


def _clippy_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--export", required=True, help="checkout of the pushed tip")
    parser.add_argument("--sites", required=True, help="file the cast sites are written to")
    parser.add_argument("-p", "--package", action="append", default=[],
                     help="a package to gate; none gates every package of --manifest")
    parser.add_argument("--manifest", default="Cargo.toml",
                     help="manifest relative to the export: a standalone crate's, for one")
    parser.add_argument("--packages-out",
                     help="file the manifest's workspace package names are written to")
    parser.add_argument("--present-only", action="store_true",
                     help="skip packages (or a manifest) absent from the export: a range's base")
    parser.add_argument("--command-cwd", type=pathlib.Path,
                     help="directory Cargo runs from; defaults to the export")
    parser.add_argument("--profile", choices=[HISTORICAL_CAST_PROFILE],
                        help="physical Cargo profile for historical casts only")
    parser.add_argument("--config", choices=[HISTORICAL_CAST_CONFIG[1]],
                        help="stack-owned inline Cargo config for historical casts")


def _check_historical_profile(
    export: pathlib.Path, manifest: pathlib.Path, command_cwd: pathlib.Path,
) -> None:
    from atlas_build_source import cargo_config_digest

    if any(name.upper().startswith("CARGO_PROFILE_CAST_HISTORY_") for name in os.environ):
        raise ValueError("historical cast profile must inherit the stack dev profile")
    if os.environ.get("CARGO_BUILD_PROFILE") not in (None, "", "debug", "dev"):
        raise ValueError("historical cast comparison requires dev as the ordinary Cargo profile")
    cargo_config_digest(command_cwd, forbidden_profile=HISTORICAL_CAST_PROFILE)
    export = export.resolve(strict=True)
    path = manifest.resolve(strict=True)
    if not path.is_relative_to(export):
        raise ValueError("historical cast manifest lies outside its export")
    pending = [
        directory / "Cargo.toml" for directory in (path.parent, *path.parent.parents)
        if directory.is_relative_to(export) and (directory / "Cargo.toml").is_file()
    ]
    checked: set[pathlib.Path] = set()
    while pending:
        candidate = pending.pop()
        source = candidate.resolve(strict=True)
        if not source.is_relative_to(export):
            raise ValueError(f"Cargo manifest {candidate} lies outside the export")
        if source in checked:
            continue
        checked.add(source)
        data = tomllib.loads(source.read_text(encoding="utf-8-sig"))
        profiles = data.get("profile", {})
        if not isinstance(profiles, dict):
            raise ValueError(f"Cargo profile table is malformed in {candidate}")
        if HISTORICAL_CAST_PROFILE in profiles:
            raise ValueError(f"reserved Cargo profile {HISTORICAL_CAST_PROFILE} is defined in {candidate}")
        workspace = data.get("package", {}).get("workspace")
        if workspace is not None:
            target = (source.parent / workspace / "Cargo.toml").resolve()
            if not target.is_relative_to(export):
                raise ValueError(f"Cargo workspace from {candidate} lies outside the export")
            pending.append(target)


def historical_cast_command(
    command: tuple[str, ...], *, root: pathlib.Path, manifest: pathlib.Path,
    command_cwd: pathlib.Path | None, selection: Iterable[str],
) -> tuple[str, ...]:
    """Bind the hook's historical command to the same profile as identity."""
    if len(command) < 3 or command[2] != "clippy":
        raise ValueError("historical cast identity requires the owned clippy command")
    interpreter = shutil.which(command[0])
    if interpreter is None or not pathlib.Path(interpreter).samefile(sys.executable):
        raise ValueError("historical cast command requires the identity interpreter")
    script = pathlib.Path(command[1])
    owned = pathlib.Path(__file__).resolve()
    if script.name != owned.name or not script.is_absolute():
        raise ValueError("historical cast command must name the owned absolute script")
    if script.read_bytes().replace(b"\r\n", b"\n") != owned.read_bytes().replace(b"\r\n", b"\n"):
        raise ValueError("historical cast command differs from the bound stack tool")
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False, exit_on_error=False)
    _clippy_options(parser)
    try:
        options = parser.parse_args(command[3:])
    except (argparse.ArgumentError, SystemExit) as error:
        raise ValueError("invalid historical cast arguments") from error
    export = pathlib.Path(options.export).resolve(strict=True)
    manifest_path = (export / options.manifest).resolve(strict=True)
    if (
        not options.present_only
        or options.profile is not None
        or options.config is not None
        or options.packages_out is not None
        or export != root.resolve(strict=True)
        or manifest_path != manifest.resolve(strict=True)
        or not manifest_path.is_relative_to(export)
        or (options.command_cwd or export).resolve(strict=True)
            != (command_cwd or root).resolve(strict=True)
        or not options.package
        or sorted(options.package) != sorted(selection)
    ):
        raise ValueError("historical cast arguments do not match the selected build")
    _check_historical_profile(export, manifest_path, command_cwd or root)
    return (*command, "--profile", HISTORICAL_CAST_PROFILE, *HISTORICAL_CAST_CONFIG)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--baseline", type=pathlib.Path, default=BASELINE)
    # Resolved here: cargo runs from the export, where a relative path misses.
    parser.add_argument("--cargo-config", type=lambda value: pathlib.Path(value).resolve(),
                        help="cargo config file (the stack config without its [patch] overlay)")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("clippy", help="run clippy, recording its cast sites")
    _clippy_options(run)
    run.set_defaults(run=clippy)
    gate = commands.add_parser("check", help="gate a pushed revision")
    gate.add_argument("--member", required=True)
    gate.add_argument("--repo", required=True, help="the member repository")
    gate.add_argument("--base", default="", help="pushed range base; empty for new history")
    gate.add_argument("--tip", required=True)
    gate.add_argument("--package", action="append", default=[], required=True)
    gate.add_argument("--sites", action="append", default=[], required=True,
                      help="a file `clippy` wrote")
    gate.add_argument("--base-sites", action="append", default=[],
                      help="a file `clippy` wrote for the range's base")
    gate.add_argument("--base-package", action="append", default=[],
                      help="a package with a proven base count, including zero for a "
                           "newly owned standalone manifest")
    gate.add_argument("--zero-base-package", action="append", default=[],
                      help="a newly owned package explicitly held to zero")
    gate.set_defaults(run=check)
    trigger = commands.add_parser(
        "base-triggers", help="print why the range needs the base count; nothing when it does not")
    trigger.add_argument("--repo", required=True, help="the member repository")
    trigger.add_argument("--base", required=True)
    trigger.add_argument("--tip", required=True)
    trigger.set_defaults(run=triggers)
    owner = commands.add_parser("new-standalone-owners")
    owner.add_argument("--repo", required=True)
    owner.add_argument("--base", required=True)
    owner.add_argument("--tip", required=True)
    owner.add_argument("--manifest", action="append", default=[], required=True)
    owner.add_argument("--base-export", required=True)
    owner.add_argument("--tip-export", required=True)
    owner.add_argument("--metadata-timeout", type=float, default=120.0)
    owner.set_defaults(run=owners)
    resolved = commands.add_parser(
        "resolved-changes",
        help=("print the members a changed root manifest resolves differently, one per "
              "line sorted by name; exit 3 for all"))
    resolved.add_argument("--repo", required=True, help="the member repository")
    resolved.add_argument("--base", required=True)
    resolved.add_argument("--tip", required=True)
    resolved.add_argument("--base-export", required=True, help="checkout of the range's base")
    resolved.add_argument("--tip-export", required=True, help="checkout of the pushed tip")
    resolved.add_argument("--manifest", default="Cargo.toml",
                          help="workspace manifest relative to the exports")
    resolved.set_defaults(run=changes)
    count = commands.add_parser("measure", help="print per-package counts for a member")
    count.add_argument("--member", required=True)
    count.add_argument("--export", required=True)
    count.add_argument("--manifest", default="Cargo.toml",
                       help="manifest relative to the export: a standalone crate's, for one")
    count.add_argument("--command-cwd", type=pathlib.Path,
                       help="directory Cargo runs from; defaults to the export")
    count.set_defaults(run=measure)
    hold = commands.add_parser("ratchet", help="refuse a pushed range that raises the baseline")
    hold.add_argument("--repo", required=True, help="the atlas repository")
    hold.add_argument("--base", required=True)
    hold.add_argument("--tip", required=True)
    hold.set_defaults(run=ratchet)
    args = parser.parse_args(argv)
    try:
        return args.run(args)
    except Exception as exc:  # a gate that cannot judge exits 2, never 1 (a finding)
        print(f"cast gate: could not run: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
