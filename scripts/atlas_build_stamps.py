"""Git build stamps: which content each Git package's artifacts in a build directory were built from."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from atlas_build_lease import BuildIdentityError
from atlas_build_records import _write_atomic
from atlas_build_source import _sha256_bytes


# Cargo's profile name for each profile directory that differs from it.
_CARGO_PROFILE_NAMES = {"debug": "dev"}


@dataclass(frozen=True)
class BuildDirectory:
    """One profile directory of the shared target, where a build writes its artifacts.

    `profile` is the directory's name (`debug`, `release`, a custom
    profile's) and `target` a triple or `host`. A Git package's stamp and
    the clean that invalidates it both cover exactly this directory: `cargo
    clean -p` without `--profile` leaves every other profile's variants, so
    a stamp spanning the target would vouch for artifacts no clean reached.
    """

    target_dir: Path
    profile: str
    target: str

    def stamp(self, record: dict[str, object]) -> Path:
        """Where the content this directory's artifacts of `record` were built from is named."""
        key = _sha256_bytes(
            f"{record.get('name')}\0{record.get('source')}\0{self.profile}\0{self.target}".encode()
        )
        return self.target_dir / ".atlas" / "source-identity" / "git-build" / key

    def clean_arguments(self) -> list[str]:
        """`cargo clean` arguments confining it to this directory, every variant in it."""
        arguments = ["--profile", _CARGO_PROFILE_NAMES.get(self.profile, self.profile)]
        if self.target != "host":
            arguments += ["--target", self.target]
        return arguments


# The stamp a run writes before building a Git package it cleans or finds
# unstamped, replaced by the content digest only once the command and the
# final snapshot succeed. It equals no digest, so a run that fails or is
# killed in between leaves that package stale for the next one: the target
# may already hold what it built. A package whose stamp already matched
# gets no sentinel, so an edit to its checkout during the build, reverted
# before the next run, is not seen (ATLAS-IDENTITY-MIDRUN-GIT-EDIT).
_BUILDING = "building"


def _git_records(dependencies: dict[str, object], names: Iterable[str]) -> list[dict[str, object]]:
    wanted = set(names)
    return [
        record
        for record in dependencies.get("packages", [])
        if isinstance(record, dict) and record.get("kind") == "git" and record.get("name") in wanted
    ]


def _git_names(dependencies: dict[str, object]) -> set[str]:
    return {
        str(record.get("name"))
        for record in dependencies.get("packages", [])
        if isinstance(record, dict) and record.get("kind") == "git"
    }


def _git_stamp(directory: BuildDirectory, record: dict[str, object]) -> str | None:
    """The content digest the stamp names, or `_BUILDING`; None without a stamp."""
    try:
        value = json.loads(directory.stamp(record).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BuildIdentityError(
            f"cannot read the Git build stamp of {record.get('name')}: {error}"
        ) from error
    digest = value.get("content_digest") if isinstance(value, dict) else None
    if not isinstance(digest, str):
        raise BuildIdentityError(f"malformed Git build stamp for {record.get('name')}")
    return digest


def _stale_git(dependencies: dict[str, object], directory: BuildDirectory) -> set[str]:
    """Git packages whose artifacts in the build directory may be from other content.

    Cargo never re-reads a Git checkout, and a record describes only its own
    runs' builds, so the target itself carries one stamp per Git package,
    source and build directory: the content digest of the checkout its
    artifacts there were last built from. A stamp naming other content than the checkout holds now, or a
    build that never finished, means the artifacts may predate an edit or
    its revert, whichever record's run built them. A package with no stamp
    was never built by a run of this checker since stamps began; its
    artifacts are trusted, the bound already accepted for builds outside
    this checker.
    """
    return {
        str(record.get("name"))
        for record in _git_records(dependencies, _git_names(dependencies))
        if (stamp := _git_stamp(directory, record)) is not None
        and stamp != record.get("content_digest")
    }


def _unstamped_git(dependencies: dict[str, object], directory: BuildDirectory) -> set[str]:
    return {
        str(record.get("name"))
        for record in _git_records(dependencies, _git_names(dependencies))
        if _git_stamp(directory, record) is None
    }


def _write_git_stamps(
    dependencies: dict[str, object], directory: BuildDirectory, names: Iterable[str], building: bool
) -> None:
    """Stamp `names`' Git packages as building, or with the content they were built from.

    A refused write raises. The stamp is then `_BUILDING` (or absent, if the
    first write failed), so the next run cleans the package instead of
    trusting it: a failure costs a rebuild, never a stale reuse. Two runs
    stamping one unstamped package concurrently hold it shared and checked
    the same content unchanged across their builds, so either value is true.
    """
    for record in _git_records(dependencies, names):
        value = _BUILDING if building else record.get("content_digest")
        _write_atomic(directory.stamp(record), {"content_digest": value})
