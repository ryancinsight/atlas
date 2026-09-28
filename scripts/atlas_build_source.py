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


def source_identity(
    root: Path,
    excluded_roots: Sequence[Path] = (),
    ignored_paths: Sequence[Path] = (),
) -> SourceIdentity:
    root = _canonical(root, strict=True)
    top = Path(os.fsdecode(_git(root, "rev-parse", "--show-toplevel").strip())).resolve()
    revision = os.fsdecode(_git(top, "rev-parse", "HEAD").strip())
    excluded = tuple(_canonical(path) for path in excluded_roots)
    ignored = tuple(_canonical(path) for path in ignored_paths)
    diff = _diff_bytes(top, ignored)
    untracked_entries: list[tuple[bytes, bytes, Path]] = []
    for marker, arguments in (
        (b"untracked", ("ls-files", "--others", "--exclude-standard", "-z")),
        (b"ignored", ("ls-files", "--others", "--ignored", "--exclude-standard", "-z")),
    ):
        for raw_path in _git(top, *arguments).split(b"\0"):
            if not raw_path:
                continue
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
# the same dimension.
_EXCLUDED_ENVIRONMENT_KEYS = frozenset({"CARGO_TARGET_DIR"})


def environment_digest(environment: Mapping[str, str] | None = None) -> str:
    """A digest of the environment variables that change how Cargo builds.

    `CARGO_BUILD_*` (target, rustflags, jobs, ...), `CARGO_TARGET_*`
    (per-triple rustflags and runners), `CARGO_UNSTABLE_*` (nightly `-Z`
    flags mirrored as env, e.g. `build-std`), and `CARGO_HOST_*` (host-triple
    rustflags) are covered by prefix, alongside the existing
    `CARGO_PROFILE_*` prefix and the fixed single-variable set -- which adds
    `RUSTC_BOOTSTRAP` (gates unstable rustc flags) to the set already
    covering `RUSTFLAGS`. A `CARGO_BUILD_RUSTFLAGS` recompiling every
    dependency at a different codegen setting was previously invisible here,
    matching this run's exact-comparison record to one built under a
    different value.

    Rustdoc-only inputs -- `RUSTDOCFLAGS`, `CARGO_ENCODED_RUSTDOCFLAGS`,
    `RUSTDOC` -- are deliberately excluded, even though the pre-push hook's
    doc step sets one of them. `discover_artifacts` never looks under
    `target/doc`, so this record's tracked artifacts (the compiled
    dependency closure) are unaffected by a rustdoc-only flag; Cargo's own
    per-unit doc fingerprint tracks that flag independently and rebuilds
    docs on its own when it changes. The hook runs clippy, nextest, and
    `cargo doc` under one shared `command_key` for one package precisely so
    they read one record (`_sibling_matches` ignores only the command key,
    comparing every other build dimension); including a rustdoc-only input
    here would give the doc step's `env RUSTDOCFLAGS=... cargo doc`
    invocation a different `environment_digest` from the clippy and test
    steps' plain invocations, splitting one shared record into two and
    making each stale to the other -- a real-Cargo run of that exact
    three-step sequence measured this cleaning the whole dependency closure
    on every push instead of after the first.
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


def _feed_config_file(digest: "hashlib._Hash", marker: bytes, path: Path, seen: set[Path]) -> None:
    """Hash `path` into `digest`, then recurse into its `include` directive.

    Cargo 1.97 stable follows `include = "path"` or `include = ["path", ...]`
    in a config file, resolved relative to the directory holding that file,
    and merges the included file's own settings; an edit confined to an
    included file changes the build without changing the including file's
    bytes at all. `seen` guards a cycle (an included file naming its own
    includer, directly or through a chain) and also lets one file reached
    two ways (an explicit include of a file this walk would find anyway)
    contribute to the digest only once.
    """
    if path in seen:
        _feed_framed(digest, marker)
        _feed_framed(digest, b"seen:" + path.name.encode("utf-8", "surrogateescape"))
        return
    seen.add(path)
    _feed_framed(digest, marker)
    try:
        content = path.read_bytes()
    except OSError as error:
        raise BuildIdentityError(f"cannot read cargo config {path}: {error}") from error
    _feed_framed(digest, content)
    try:
        data = tomllib.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        return
    include = data.get("include")
    if isinstance(include, str):
        include = [include]
    if not isinstance(include, list):
        return
    for entry in include:
        if not isinstance(entry, str):
            continue
        included = (path.parent / entry).resolve()
        if included.is_file():
            _feed_config_file(digest, b"include", included, seen)


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
    directive (stable since Cargo 1.97) recursively. None of these live
    inside the package's own repository -- the pre-push gate mirrors the
    stack's shared config two directories above the export, one `nested`
    level per layered stack config -- so no git diff of that repository can
    ever see one of them change; a profile or rustflags edit there
    recompiles a dependency while every record naming it stays
    byte-identical.

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
    two can differ. Read failures are surfaced rather than silently skipped:
    a config file this run cannot read is a build input it cannot account
    for.
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
            _feed_framed(digest, b"arg-inline")
            _feed_framed(digest, text.encode("utf-8"))
    return digest.hexdigest()
