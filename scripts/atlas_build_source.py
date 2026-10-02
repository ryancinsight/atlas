"""Identify source trees, ignored inputs, and build environments."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from atlas_build_lease import BuildIdentityError


@dataclass(frozen=True)
class SourceIdentity:
    root: str
    revision: str
    tree_digest: str
    dirty: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "revision": self.revision,
            "tree_digest": self.tree_digest,
            "dirty": self.dirty,
        }


def _git(root: Path, *arguments: str) -> bytes:
    environment = os.environ.copy()
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_PREFIX",
        "GIT_COMMON_DIR",
    ):
        environment.pop(key, None)
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise BuildIdentityError(f"cannot run git in {root}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise BuildIdentityError(f"git {' '.join(arguments)} failed in {root}: {detail}")
    return result.stdout


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _feed_framed(digest: "hashlib._Hash", data: bytes) -> None:
    digest.update(len(data).to_bytes(8, "big"))
    digest.update(data)


def _canonical(path: Path, *, strict: bool = False) -> Path:
    try:
        return path.resolve(strict=strict)
    except OSError as error:
        raise BuildIdentityError(f"cannot resolve {path}: {error}") from error


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _ignored_source_path(path: Path, top: Path) -> bool:
    try:
        parts = path.relative_to(top).parts[:-1]
    except ValueError:
        return True
    return any(
        part
        in {
            ".git",
            "target",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
        }
        for part in parts
    )


def _diff_bytes(top: Path, ignored: Sequence[Path]) -> bytes:
    arguments = ["diff", "--binary", "HEAD", "--", "."]
    for path in ignored:
        try:
            relative = path.relative_to(top).as_posix()
        except ValueError as error:
            raise BuildIdentityError(
                f"ignored source path is outside the repository: {path}"
            ) from error
        arguments.append(f":(exclude){relative}")
    return _git(top, *arguments)


def _untracked_paths(top: Path) -> tuple[tuple[bytes, list[bytes]], ...]:
    """The untracked and the ignored files under `top`, each group in Git's path order.

    One `git status` walks the tree once for both groups, where
    `ls-files --others` and `ls-files --others --ignored` walked it twice
    in two processes. Each group is the list those commands print, sorted
    as Git sorts it (byte order), so the source digest is unchanged.
    Submodules are not entered: only `?` and `!` entries are read.
    """
    output = _git(
        top,
        "--no-optional-locks",
        "status",
        "--porcelain=v2",
        "-z",
        "--untracked-files=all",
        "--ignored=traditional",
        "--ignore-submodules=all",
        "--no-renames",
    )
    untracked: list[bytes] = []
    ignored: list[bytes] = []
    # Under `--no-renames` every entry is one field: none carries an original path.
    for field in output.split(b"\0"):
        if field.startswith(b"? "):
            untracked.append(field[2:])
        elif field.startswith(b"! "):
            ignored.append(field[2:])
    return (b"untracked", sorted(untracked)), (b"ignored", sorted(ignored))


def repository_head(root: Path) -> tuple[Path, str]:
    """The top of the work tree holding `root`, and the revision its `HEAD` names."""
    root = _canonical(root, strict=True)
    top_line, revision_line = _git(root, "rev-parse", "--show-toplevel", "HEAD").splitlines()
    return Path(os.fsdecode(top_line.strip())).resolve(), os.fsdecode(revision_line.strip())


def source_identity(
    root: Path,
    excluded_roots: Sequence[Path] = (),
    ignored_paths: Sequence[Path] = (),
) -> SourceIdentity:
    return worktree_identity(*repository_head(root), excluded_roots, ignored_paths)


def worktree_identity(
    top: Path,
    revision: str,
    excluded_roots: Sequence[Path] = (),
    ignored_paths: Sequence[Path] = (),
) -> SourceIdentity:
    """The identity of the work tree at `top`, whose `HEAD` is `revision`.

    `top` and `revision` are what `repository_head` returned for it.
    """
    excluded = tuple(_canonical(path) for path in excluded_roots)
    ignored = tuple(_canonical(path) for path in ignored_paths)
    diff = _diff_bytes(top, ignored)
    untracked_entries: list[tuple[bytes, bytes, Path]] = []
    for marker, raw_paths in _untracked_paths(top):
        for raw_path in raw_paths:
            path = (top / Path(os.fsdecode(raw_path))).resolve()
            if any(_is_within(path, excluded_root) for excluded_root in excluded):
                continue
            if any(_is_within(path, ignored_path) for ignored_path in ignored):
                continue
            if _ignored_source_path(path, top):
                continue
            untracked_entries.append((marker, raw_path, path))
    if not diff and not untracked_entries:
        return SourceIdentity(
            root=top.as_posix(),
            revision=revision,
            tree_digest=_sha256_bytes(revision.encode()),
            dirty=False,
        )

    digest = hashlib.sha256()
    _feed_framed(digest, diff)
    for marker, raw_path, path in untracked_entries:
        _feed_framed(digest, marker)
        _feed_framed(digest, raw_path)
        try:
            _feed_framed(digest, path.read_bytes())
        except OSError as error:
            raise BuildIdentityError(f"cannot read untracked source {path}: {error}") from error
    return SourceIdentity(
        root=top.as_posix(),
        revision=revision,
        tree_digest=digest.hexdigest(),
        dirty=True,
    )


def toolchain_identity(root: Path) -> str:
    try:
        result = subprocess.run(
            [os.environ.get("RUSTC", "rustc"), "--version", "--verbose"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise BuildIdentityError(f"cannot run rustc: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip()
        raise BuildIdentityError(f"rustc --version --verbose failed: {detail}")
    return " ".join(result.stdout.split())


#  `CARGO_TARGET_DIR` is already the record's own `target_dir` dimension
# (canonicalized to a real path, never compared as an environment string,
# and the shared-cache root the pre-push gate always sets identically), so
# including it here would only add a second, differently-spelled copy of
# the same dimension. `CARGO_BUILD_RUSTDOCFLAGS`/`CARGO_BUILD_RUSTDOC` are
# the `CARGO_BUILD_*`-prefixed spellings of the rustdoc-only inputs excluded
# below by their own names; excluding only the bare names while the prefix
# match let these two back in would defeat that exclusion for no reason.
_EXCLUDED_ENVIRONMENT_KEYS = frozenset(
    {"CARGO_TARGET_DIR", "CARGO_BUILD_RUSTDOCFLAGS", "CARGO_BUILD_RUSTDOC"}
)


def environment_digest(environment: Mapping[str, str] | None = None) -> str:
    """A digest of the environment variables that change how Cargo builds.

    `CARGO_BUILD_*` (target, rustflags, jobs, ...), `CARGO_TARGET_*`
    (per-triple rustflags and runners), `CARGO_UNSTABLE_*` (nightly `-Z`
    flags mirrored as env, e.g. `build-std`), `CARGO_HOST_*` (host-triple
    rustflags), and `CARGO_ALIAS_*` (a `[alias]` table entry set as env,
    which can itself carry compile-affecting flags, e.g.
    `CARGO_ALIAS_CLIPPY="check --config build.rustflags=[...]"`) are covered
    by prefix, alongside the existing `CARGO_PROFILE_*` prefix and the fixed
    single-variable set -- which adds `RUSTC_BOOTSTRAP` (gates unstable
    rustc flags) to the set already covering `RUSTFLAGS`. A
    `CARGO_BUILD_RUSTFLAGS` recompiling every dependency at a different
    codegen setting was previously invisible here, matching this run's
    exact-comparison record to one built under a different value.

    Rustdoc-only inputs -- `RUSTDOCFLAGS`, `CARGO_ENCODED_RUSTDOCFLAGS`,
    `RUSTDOC` (and their `CARGO_BUILD_*`-prefixed spellings, excluded
    alongside them below) -- are deliberately excluded, even though the
    pre-push hook's doc step sets one of them, and even though the record
    *does* name doc-unit fingerprint files (`discover_artifacts` walks a
    package's whole `.fingerprint/<pkg>-<hash>/` directory, which holds
    `doc-lib-*`/`output-doc-lib-*` beside the compile-unit files; a real run
    confirmed both are recorded). Excluding them from this digest is sound
    because Cargo's own fingerprint scheme makes the omission moot, not
    because a later mismatch here would catch a stale one: Cargo's per-unit
    fingerprint for a `doc` unit already incorporates that unit's own
    effective rustdoc flags, so `cargo doc` unconditionally re-invokes
    rustdoc -- rewriting `doc-lib-*`/`output-doc-lib-*` -- whenever those
    flags differ from the last run, before this scheme ever reads the
    resulting bytes. There is consequently no stale-doc case for
    `environment_digest` to guard against: whatever a given `cargo doc` run
    writes already reflects that run's own flags, so the `matched` branch in
    `run_build` simply *adopts* those bytes into the record
    (`files[relative] = settled_digest(...)`, unconditionally, once settled)
    rather than comparing them against a prior expectation -- adoption, not
    mismatch detection, because Cargo already did the enforcing before this
    module looked. What exclusion actually buys: the pre-push hook runs
    clippy, nextest, and `cargo doc` under one shared `command_key` for one
    package precisely so they read one record (`_sibling_matches` ignores
    only the command key, comparing every other build dimension); including
    a rustdoc-only input here would give the doc step's
    `env RUSTDOCFLAGS=... cargo doc` invocation a different
    `environment_digest` from the clippy and test steps' plain invocations,
    splitting one shared record into two and making each stale to the
    other -- a real-Cargo run of that exact three-step sequence measured
    this cleaning the whole dependency closure on every push instead of
    after the first.
    """
    source = os.environ if environment is None else environment
    keys = {
        key
        for key in source
        if key not in _EXCLUDED_ENVIRONMENT_KEYS
        and (
            key.startswith("CARGO_PROFILE_")
            or key.startswith("CARGO_BUILD_")
            or key.startswith("CARGO_TARGET_")
            or key.startswith("CARGO_UNSTABLE_")
            or key.startswith("CARGO_HOST_")
            or key.startswith("CARGO_ALIAS_")
            or key
            in {
                "CARGO",
                "CARGO_ENCODED_RUSTFLAGS",
                "CARGO_INCREMENTAL",
                "RUSTC",
                "RUSTC_BOOTSTRAP",
                "RUSTC_WORKSPACE_WRAPPER",
                "RUSTC_WRAPPER",
                "RUSTFLAGS",
                # Cargo folds it into every unit's metadata hash.
                "__CARGO_DEFAULT_LIB_METADATA",
            }
        )
    }
    values = {key: _sha256_bytes(str(source[key]).encode()) for key in sorted(keys)}
    return _sha256_bytes(
        json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
    )


def _cargo_home(environment: Mapping[str, str] | None = None) -> Path:
    source = os.environ if environment is None else environment
    configured = source.get("CARGO_HOME")
    return Path(configured) if configured else Path.home() / ".cargo"


def _include_paths(include: object) -> list[str]:
    """The file paths a config's `include` value names, in Cargo's own forms.

    Cargo 1.97 stable accepts a list of strings (`include = ["a.toml"]`) or a
    list of tables (`include = [{ path = "a.toml" }]`, each optionally
    carrying `optional = true`) -- never a bare string, which Cargo itself
    rejects ("expected a list of strings or a list of tables"). An
    `optional` entry naming a file that does not exist is not an error for
    Cargo, and not one here either: the caller's own `is_file()` check
    already skips a missing path silently, exactly matching that semantic.
    """
    if not isinstance(include, list):
        return []
    paths: list[str] = []
    for entry in include:
        if isinstance(entry, str):
            paths.append(entry)
        elif isinstance(entry, dict) and isinstance(entry.get("path"), str):
            paths.append(entry["path"])
    return paths


def _feed_config_text(
    digest: "hashlib._Hash",
    marker: bytes,
    content: bytes,
    base: Path,
    seen: set[Path],
    source: str,
) -> None:
    """Hash `content` into `digest`, then recurse into its `include` value.

    Shared by a config file (whose own bytes are `content`) and an inline
    `--config` TOML argument (which has no file of its own, only `content`):
    both can carry `include`, resolved against `base` -- the including
    file's own directory, or the execution root for an inline argument,
    matching where Cargo resolves each. `source` is a human-readable label
    for error messages only (the file's path, or a description of the
    inline argument); it plays no part in the digest.

    A leading UTF-8 BOM is stripped before parsing: Cargo's own config
    parser accepts one, so a BOM-only difference from an otherwise
    byte-identical config must not stop this digest from following that
    config's own `include`. Any parse failure that remains fails closed by
    raising rather than returning as though the config had no `include`:
    Cargo's TOML grammar is looser than `tomllib`'s strict TOML 1.0 in
    several ways -- a trailing comma after an inline table's last element,
    an inline table split across lines, and the TOML 1.1 string escapes
    `\\e` and `\\xHH` are all accepted by Cargo's parser and rejected by
    `tomllib` -- so a config `tomllib` cannot parse can still be one Cargo
    parses and builds with, and silently stopping there would under-hash a
    config whose `include` this digest can no longer see, exactly the
    staleness this scheme exists to prevent. The pre-push hook surfaces the
    raised error through its identity-branch classification (a source
    identity failure, distinct from an ordinary compile failure), naming
    the offending file; it is not classified as an environment failure.
    """
    _feed_framed(digest, marker)
    _feed_framed(digest, content)
    text = content
    if text.startswith(b"\xef\xbb\xbf"):
        text = text[3:]
    try:
        data = tomllib.loads(text.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise BuildIdentityError(
            f"cannot parse cargo config as TOML ({source}): {error}; rewrite it in "
            "TOML 1.0 syntax (Cargo's own parser is looser -- a trailing comma after an "
            "inline table's last element, an inline table split across lines, and the "
            "TOML 1.1 string escapes \\e and \\xHH are not TOML 1.0) so its `include` "
            "directive, if any, can be followed"
        ) from error
    for entry in _include_paths(data.get("include")):
        included = (base / entry).resolve()
        if included.is_file():
            _feed_config_file(digest, b"include", included, seen)


def _feed_config_file(digest: "hashlib._Hash", marker: bytes, path: Path, seen: set[Path]) -> None:
    """Hash `path` into `digest`, then recurse into its `include` directive.

    An edit confined to an included file changes the build without changing
    the including file's own bytes at all. `seen` guards a cycle (an
    included file naming its own includer, directly or through a chain) and
    also lets one file reached two ways (an explicit include of a file this
    walk would find anyway) contribute to the digest only once.
    """
    if path in seen:
        _feed_framed(digest, marker)
        _feed_framed(digest, b"seen:" + path.name.encode("utf-8", "surrogateescape"))
        return
    seen.add(path)
    try:
        content = path.read_bytes()
    except OSError as error:
        raise BuildIdentityError(f"cannot read cargo config {path}: {error}") from error
    _feed_config_text(digest, marker, content, path.parent, seen, str(path))


def cargo_config_digest(
    execution_root: Path,
    config_arguments: Sequence[str] = (),
    environment: Mapping[str, str] | None = None,
) -> str:
    """A digest of every Cargo configuration source that shapes this build.

    Cargo merges `.cargo/config.toml` and the legacy `.cargo/config` (Cargo
    itself prefers the extensionless file when both exist at one level, but
    this digest hashes whichever are present rather than picking one, so
    either changing is visible) from every directory between the execution
    root and the filesystem root, closer files overriding farther ones, plus
    `$CARGO_HOME/config.toml`/`$CARGO_HOME/config` and any `--config`
    argument on the command line, and follows each file's own `include`
    directive (stable since Cargo 1.97) recursively. The pre-push gate
    mirrors the stack's shared config two directories above the export, one
    `nested` level per layered stack config, outside the diffed repository
    entirely -- so no git diff of that repository can ever see a change
    there; a profile or rustflags edit at that level recompiles a
    dependency while every record naming it stays byte-identical, which is
    the gap this digest closes for that source. A config committed inside
    the package's own repository (an in-tree `.cargo/config.toml`) is a
    different case: a git diff of the repository would show that edit, and
    this digest also covers it at depth 0, but only as one input among the
    others above -- neither case makes the other irrelevant.

    Each directory config is framed by its depth from the execution root
    and its filename, never its absolute path: the pre-push gate exports
    each push to a fresh temporary directory, so a path-keyed digest would
    make a config file committed inside the repository itself look new on
    every push, reintroducing the exact whole-closure-every-push staleness
    this identity scheme exists to avoid. Depth is stable across exports
    with the same relative layout (a stack config one directory above an
    `export-N` sibling is depth 1 on every push) while still distinguishing
    a config at one level from a same-named, differently-positioned one.
    `$CARGO_HOME` does not move export to export, so its digest carries no
    path either, only its content. A `--config` argument naming an existing
    file is hashed by content; an inline directive (`key=value` or TOML)
    has no file to read, so its literal text is hashed instead. A relative
    `--config` path is resolved against the execution root, matching Cargo's
    own resolution (relative to its `cwd`), never this process's own working
    directory: the pre-push gate invokes this module from the checkout while
    passing `--command-cwd` for the export Cargo actually runs in, so the
    two can differ. Read and parse failures are surfaced rather than
    silently skipped: a config file this run cannot read, or cannot parse
    under its own TOML grammar (BOM aside), is a build input it cannot
    account for, and returning as though it had no `include` would under-
    hash it instead of reporting the gap.
    """
    digest = hashlib.sha256()
    seen: set[Path] = set()
    origin = _canonical(execution_root)
    directory = origin
    depth = 0
    while True:
        for name in (".cargo/config.toml", ".cargo/config"):
            path = directory / name
            if path.is_file():
                marker = b"dir:" + str(depth).encode("ascii") + b":" + name.encode("ascii")
                _feed_config_file(digest, marker, path, seen)
        parent = directory.parent
        if parent == directory:
            break
        directory = parent
        depth += 1
    home = _cargo_home(environment)
    for name in ("config.toml", "config"):
        path = home / name
        if path.is_file():
            _feed_config_file(digest, b"home:" + name.encode("ascii"), path, seen)
    for argument in config_arguments:
        text = str(argument)
        candidate = Path(text)
        if not candidate.is_absolute():
            candidate = origin / candidate
        if candidate.is_file():
            _feed_config_file(digest, b"arg-file", candidate, seen)
        else:
            # An inline `--config` value is TOML text with no file of its
            # own (`--config 'include=["x.toml"]'`, or a dotted key such as
            # `profile.dev.opt-level=3`); its `include`, if any, resolves
            # against the execution root, matching Cargo's own resolution
            # for a command-line `--config` value.
            _feed_config_text(
                digest,
                b"arg-inline",
                text.encode("utf-8"),
                origin,
                seen,
                f"inline --config argument {text!r}",
            )
    return digest.hexdigest()
