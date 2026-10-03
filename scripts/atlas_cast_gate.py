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
  file is a sanctioned conversion or cast module (a span covers the whole
  `expr as T`, so a cast ending a method chain starts lines above its `as`);
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
  (`base-triggers`): a renamed file, or a changed `Cargo.toml`, package-root
  `build.rs`, cargo config or `rust-toolchain` file. A source-level `cfg`
  flip, `#[path]`, `include!`, a new `mod` line naming a file that was not
  compiled before, or a build script at a custom `package.build` path or in
  a helper module is not a trigger and is held to the row alone. Only pushed packages are counted:
  clippy lints the selected packages, so a pushed package enabling a feature
  of one it depends on is not measured there. The comparison covers the
  packages named by `--base-package`; the hook names a manifest's packages
  only when that manifest's base built, so one that fails to compile leaves
  its own packages to their rows and no others.

Sites are deduplicated by span, since `--all-targets` reports a library site
once per target. The exclusion is by path only: `--force-warn` output does not
say whether a site sits under an `#[expect]`.

The tip's clippy run is the hook's own: `clippy` runs it under the
source-identity leases in place of the plain step, writing each diagnostic's
rendered text to stderr as plain clippy would and the cast sites to a file.
The base run is the one extra compile, under the same leases.

    atlas_cast_gate.py clippy --export <dir> --sites <file> --package <pkg>
    atlas_cast_gate.py check --member eunomia --repo <dir> --base <sha> \
        --tip <sha> --package eunomia --sites <file> [--sites ...] \
        [--base-sites <file> ... --base-package eunomia ...]
    atlas_cast_gate.py base-triggers --repo <dir> --base <sha> --tip <sha>
    atlas_cast_gate.py measure --member eunomia --export <dir>
    atlas_cast_gate.py ratchet --repo <atlas> --base <sha> --tip <sha>

`ratchet` holds `cast-baseline.json` itself to the rule that rows only fall:
atlas's pre-push hook and its conformance job run it on every pushed range.
A row may fall or be dropped; it may not rise, and a package of a member the
base already measured may not gain a row (no row counts as zero). A member
the base does not measure enters with its rows (onboarding). A sanctioned
path may not be added to a member the base measures: exclusion lowers a
count without converting a cast.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

BASELINE = pathlib.Path(__file__).resolve().with_name("cast-baseline.json")
LINT = "clippy::as_conversions"
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


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

    The hook runs inside its export, whose mirrored stack configs already name
    the shared target directory; a caller outside the stack passes the stack
    config minus its `[patch]` overlay, or cargo builds a private target.
    """
    program = os.environ.get("CARGO") or "cargo"
    return [program, "--config", str(config)] if config else [program]


def clippy_command(export: pathlib.Path, packages: Iterable[str],
                   config: pathlib.Path | None = None,
                   manifest: str = "Cargo.toml") -> list[str]:
    """The clippy run that reports every `as` in `packages` of `manifest`.

    `manifest` is relative to `export`: the member's root workspace, or a
    standalone crate (cargo-fuzz) that the root workspace excludes. No
    packages selects every package of that manifest's workspace.
    """
    selection: list[str] = []
    for package in packages:
        selection += ["-p", package]
    if not selection:
        selection = ["--workspace"]
    return [
        *cargo(config), "clippy", "--manifest-path", str(export / manifest),
        *selection, "--all-targets", "--locked", "--message-format=json",
        "--", "--force-warn", LINT,
    ]


@dataclass(frozen=True)
class Workspace:
    """The workspace `cargo metadata` reports for one manifest."""

    root: pathlib.Path
    packages: list[dict]

    def names(self) -> dict[str, str]:
        """Package id to package name, for the workspace members."""
        return {p["id"]: p["name"] for p in self.packages}


def workspace(export: pathlib.Path, config: pathlib.Path | None = None,
              manifest: str = "Cargo.toml") -> Workspace:
    """The workspace of `manifest` (relative to `export`)."""
    out = subprocess.run(
        [*cargo(config), "metadata", "--no-deps", "--format-version", "1",
         "--manifest-path", str(export / manifest)],
        cwd=export, capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    record = json.loads(out)
    return Workspace(pathlib.Path(record["workspace_root"]), record["packages"])


FUZZ_CFG = "--cfg fuzzing"


def clippy_environment(packages: list[dict]) -> dict[str, str]:
    """The environment clippy runs in: `--cfg fuzzing` for a cargo-fuzz crate.

    `cargo fuzz` compiles its targets with `--cfg fuzzing`, and fuzz-only
    hooks in the crates under test sit behind that cfg, so a fuzz target does
    not compile without it. `RUSTFLAGS` replaces config `build.rustflags`; the
    stack config sets none.
    """
    env = dict(os.environ)
    if any((p.get("metadata") or {}).get("cargo-fuzz") is True for p in packages):
        env["RUSTFLAGS"] = f"{env.get('RUSTFLAGS', '')} {FUZZ_CFG}".strip()
    return env


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
        if (message.get("code") or {}).get("code") != LINT:
            continue
        package = names.get(record.get("package_id", ""))
        if package is None:
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
               manifest: str = "Cargo.toml") -> tuple[int, set[Site]]:
    """Run clippy on `packages` of `export`: its exit status and cast sites.

    Each diagnostic's rendered text goes to stderr, so a caller reading the
    output sees what plain clippy prints; cargo's own stderr passes through.
    """
    space = workspace(export, config, manifest)
    names = space.names()
    proc = subprocess.Popen(
        clippy_command(export, packages, config, manifest), cwd=export,
        env=clippy_environment(space.packages),
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


def base_triggers(repo: pathlib.Path, base: str, tip: str) -> list[str]:
    """Why the range needs the base count: each change that can bring existing
    casts into a pushed package without adding their lines. A copy is not
    one: without `-C` it diffs as an added file, every line added."""
    fields = pushed_diff(repo, base, tip, ["--name-status", "-z"]).decode("utf-8").split("\0")
    reasons: list[str] = []
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        if status[0] == "R":
            source, target = fields[index + 1], fields[index + 2]
            index += 3
            reasons.append(f"{source} -> {target}")
            paths = [source, target]
        else:
            paths = [fields[index + 1]]
            index += 2
        for path in paths:
            name = path.rsplit("/", 1)[-1]
            if (name in BUILD_INPUTS or "/.cargo/" in f"/{path}"
                    or package_build_script(repo, tip, path)):
                reasons.append(f"{path} changed")
    return list(dict.fromkeys(reasons))


@dataclass(frozen=True)
class Baseline:
    """Sanctioned conversion and cast modules, and per-package site counts."""

    sanctioned: dict[str, frozenset[str]]
    counts: dict[str, dict[str, int]]

    @classmethod
    def load(cls, path: pathlib.Path) -> Baseline:
        """The baseline at `path`; a value of the wrong shape is a ValueError."""
        return cls.parse(path.read_text(encoding="utf-8"), str(path))

    @classmethod
    def parse(cls, text: str, path: str) -> Baseline:
        """The baseline in `text`, read from `path`; a wrong shape is a ValueError."""
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError(f"{path}: the baseline is a JSON object")
        sanctioned = data.get("sanctioned", {})
        counts = data.get("counts", {})
        if not (isinstance(sanctioned, dict) and all(
                isinstance(paths, list) and all(isinstance(p, str) for p in paths)
                for paths in sanctioned.values())):
            raise ValueError(f"{path}: `sanctioned` maps members to lists of paths")
        if not (isinstance(counts, dict) and all(
                isinstance(rows, dict) and all(
                    isinstance(k, str) and type(v) is int for k, v in rows.items())
                for rows in counts.values())):
            raise ValueError(f"{path}: `counts` maps members to package counts")
        return cls(
            {m: frozenset(p) for m, p in sanctioned.items()},
            {m: dict(c) for m, c in counts.items()},
        )


def violations(member: str, found: set[Site], added: dict[str, set[int]],
               packages: Iterable[str], baseline: Baseline,
               base: set[Site] = frozenset(),
               base_packages: Iterable[str] = ()) -> list[str]:
    """Why the push fails, one line per violation; empty when it passes.

    `base` holds the sites of the pushed range's base, measured with the same
    selection. Each package in `base_packages` is held to its count there (a
    package the base lacks counts zero); any other package is held to its row
    alone.
    """
    sanctioned = baseline.sanctioned.get(member, frozenset())
    bare = sorted(s for s in found if s.path not in sanctioned)
    problems = [
        f"{s.path}:{s.line}:{s.column}: bare `as` cast on a line this push adds"
        for s in bare
        if not added.get(s.path, set()).isdisjoint(range(s.line, s.line_end + 1))
    ]
    rows = baseline.counts.get(member, {})
    compared = frozenset(base_packages)
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
        if site.path not in sanctioned:
            tally[site.package] = tally.get(site.package, 0) + 1
    return dict(sorted(tally.items()))


def clippy(args: argparse.Namespace) -> int:
    export = pathlib.Path(args.export)
    sites_file = pathlib.Path(args.sites)
    packages = list(args.package)
    if args.present_only:
        # The base of a range: a package the push adds, or a standalone crate
        # it creates, is absent there and counts zero; cargo refuses a `-p`
        # naming a package its workspace lacks.
        if not (export / args.manifest).is_file():
            write_sites(sites_file, set())
            return 0
        present = set(workspace(export, args.cargo_config, args.manifest).names().values())
        packages = [p for p in packages if p in present]
        if args.package and not packages:
            write_sites(sites_file, set())
            return 0
    status, found = run_clippy(export, packages, args.cargo_config, args.manifest)
    write_sites(sites_file, found)
    if args.packages_out:
        names = sorted(set(workspace(export, args.cargo_config, args.manifest).names().values()))
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
    added = pushed_additions(pathlib.Path(args.repo), args.base or None, args.tip)
    problems = violations(args.member, found, added, args.package, baseline, base,
                          args.base_package)
    for problem in problems:
        print(f"cast gate: {problem}", file=sys.stderr)
    if problems and args.member not in baseline.counts:
        print(f"cast gate: {args.member} has no baseline rows; measure them with "
              "`atlas_cast_gate.py measure` and add them to cast-baseline.json",
              file=sys.stderr)
    return 1 if problems else 0


def raised_rows(base: Baseline, tip: Baseline) -> list[str]:
    """Each way `tip` loosens `base`: a row above its base row, a row for a
    package of a measured member that had none, or a sanctioned path added to
    a measured member. A member `base` does not measure is onboarding."""
    problems = []
    for member, rows in sorted(tip.counts.items()):
        if member not in base.counts:
            continue
        for package, count in sorted(rows.items()):
            before = base.counts[member].get(package, 0)
            if count > before:
                problems.append(f"{member}/{package} rises from {before} to {count}")
        for path in sorted(tip.sanctioned.get(member, frozenset())
                           - base.sanctioned.get(member, frozenset())):
            problems.append(f"{member} sanctions {path}, which the base does not")
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
        print(f"cast gate: baseline {problem}; rows only fall", file=sys.stderr)
    return 1 if problems else 0


def triggers(args: argparse.Namespace) -> int:
    # UTF-8 whatever the console code page: a path outside it must not stop
    # the gate (a Windows pipe defaults to the ANSI code page).
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    for reason in base_triggers(pathlib.Path(args.repo), args.base, args.tip):
        print(reason)
    return 0


def measure(args: argparse.Namespace) -> int:
    baseline = Baseline.load(args.baseline)
    status, found = run_clippy(pathlib.Path(args.export), [], args.cargo_config, args.manifest)
    if status != 0:
        raise RuntimeError(f"clippy did not complete (exit {status})")
    tally = counts(found, baseline.sanctioned.get(args.member, frozenset()))
    print(json.dumps({args.member: tally}, indent=1, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--baseline", type=pathlib.Path, default=BASELINE)
    # Resolved here: cargo runs from the export, where a relative path misses.
    parser.add_argument("--cargo-config", type=lambda value: pathlib.Path(value).resolve(),
                        help="cargo config file (the stack config without its [patch] overlay)")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("clippy", help="run clippy, recording its cast sites")
    run.add_argument("--export", required=True, help="checkout of the pushed tip")
    run.add_argument("--sites", required=True, help="file the cast sites are written to")
    run.add_argument("-p", "--package", action="append", default=[],
                     help="a package to gate; none gates every package of --manifest")
    run.add_argument("--manifest", default="Cargo.toml",
                     help="manifest relative to the export: a standalone crate's, for one")
    run.add_argument("--packages-out",
                     help="file the manifest's workspace package names are written to")
    run.add_argument("--present-only", action="store_true",
                     help="skip packages (or a manifest) absent from the export: a range's base")
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
                      help="a package held to its count at the base; others are held to "
                           "their rows alone")
    gate.set_defaults(run=check)
    trigger = commands.add_parser(
        "base-triggers", help="print why the range needs the base count; nothing when it does not")
    trigger.add_argument("--repo", required=True, help="the member repository")
    trigger.add_argument("--base", required=True)
    trigger.add_argument("--tip", required=True)
    trigger.set_defaults(run=triggers)
    count = commands.add_parser("measure", help="print per-package counts for a member")
    count.add_argument("--member", required=True)
    count.add_argument("--export", required=True)
    count.add_argument("--manifest", default="Cargo.toml",
                       help="manifest relative to the export: a standalone crate's, for one")
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
