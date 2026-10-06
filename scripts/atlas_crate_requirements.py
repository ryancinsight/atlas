"""Dependency requirements a published crate binds, read two ways and compared.

A crate's consumers resolve its normal and build dependencies, so those are what a
registry copy and its source must agree on. The registry copy's normalized
`Cargo.toml` states each one with workspace inheritance resolved; the source side comes
from `cargo metadata`, which resolves the same inheritance. Dev-dependencies are never
compared: cargo strips them from what a consumer resolves, so a change there leaves
every consumer's resolution unchanged.

A requirement is compared as a semver requirement, never as text: `0.9`, `^0.9`, and
`^0.9.0` bind the same versions. Each comparator is expanded to the lower and upper
bounds it states (the semver crate's rules for `^`, `~`, `=`, `<`, `<=`, `>`, `>=`, and
wildcards) and the set is reduced to its tightest lower and upper bound.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

NORMAL = "normal"
BUILD = "build"
# The kinds a consumer resolves. Dev-dependencies are absent from this set on purpose.
RESOLVED_KINDS = (NORMAL, BUILD)

_MANIFEST_TABLES = {"dependencies": NORMAL, "build-dependencies": BUILD}
_COMPARATOR = re.compile(
    r"""^(?P<op>=|>=|>|<=|<|\^|~)?\s*
        (?P<major>\d+|[*xX])
        (?:\.(?P<minor>\d+|[*xX]))?
        (?:\.(?P<patch>\d+|[*xX]))?
        (?:-(?P<pre>[0-9A-Za-z.-]+))?
        (?:\+[0-9A-Za-z.-]+)?$""",
    re.VERBOSE,
)
_WILDCARDS = frozenset("*xX")

Version = tuple
Bound = tuple[Version, bool]


class RequirementError(ValueError):
    """A requirement or manifest the comparison cannot read."""


def _identifier_key(identifier: str) -> tuple[int, int | str]:
    """Semver precedence of one pre-release identifier: numeric below alphanumeric."""
    return (0, int(identifier)) if identifier.isdigit() else (1, identifier)


def _version(major: int, minor: int, patch: int, pre: str | None) -> Version:
    """Orderable version: a pre-release sorts below its release."""
    if pre is None:
        return (major, minor, patch, 1, ())
    return (major, minor, patch, 0, tuple(_identifier_key(i) for i in pre.split(".")))


def _comparator_bounds(text: str) -> tuple[Bound | None, Bound | None]:
    """(lower, upper) bound of one comparator; a bound is (version, inclusive)."""
    found = _COMPARATOR.match(text.strip())
    if found is None:
        raise RequirementError(f"unreadable version requirement comparator {text!r}")
    operator = found["op"]
    parts = [found["major"], found["minor"], found["patch"]]
    wildcard = any(part in _WILDCARDS for part in parts if part is not None)
    after_wildcard = False
    for part in parts:
        if part in _WILDCARDS:
            after_wildcard = True
        elif after_wildcard and part is not None:
            raise RequirementError(f"number after a wildcard in {text!r}")
    if parts[0] in _WILDCARDS:
        return None, None
    numbers = [int(part) for part in parts if part is not None and part not in _WILDCARDS]
    major = numbers[0]
    minor = numbers[1] if len(numbers) > 1 else None
    patch = numbers[2] if len(numbers) > 2 else None
    pre = found["pre"]
    if wildcard and operator not in (None, "="):
        raise RequirementError(f"wildcard under an operator in {text!r}")
    low = _version(major, minor or 0, patch or 0, pre)

    def below(next_major: int, next_minor: int, next_patch: int) -> Bound:
        return (_version(next_major, next_minor, next_patch, None), False)

    def next_after() -> Bound:
        """The exclusive bound above every version the partial version `major[.minor]` names."""
        return below(major, minor + 1, 0) if minor is not None else below(major + 1, 0, 0)

    if operator == "=" or (wildcard and operator is None):
        if patch is not None:
            return (low, True), (low, True)
        return (low, True), next_after()
    if operator == ">":
        lower = (low, False) if patch is not None else (next_after()[0], True)
        return lower, None
    if operator == ">=":
        return (low, True), None
    if operator == "<":
        return None, (low, False)
    if operator == "<=":
        upper = (low, True) if patch is not None else next_after()
        return None, upper
    if operator == "~":
        return (low, True), next_after()
    if major > 0:
        upper = below(major + 1, 0, 0)
    elif minor is None:
        upper = below(1, 0, 0)
    elif minor > 0:
        upper = below(0, minor + 1, 0)
    elif patch is None:
        upper = below(0, 1, 0)
    else:
        upper = below(0, 0, patch + 1)
    return (low, True), upper


def canonical_requirement(text: str) -> tuple:
    """The versions `text` admits, as a value equal across spellings of one requirement.

    Returns (tightest lower bound, tightest upper bound); a bound is (version, inclusive),
    and a version carrying a pre-release sorts below its release.
    """
    lowers: list[Bound] = []
    uppers: list[Bound] = []
    for comparator in text.split(","):
        lower, upper = _comparator_bounds(comparator)
        if lower is not None:
            lowers.append(lower)
        if upper is not None:
            uppers.append(upper)
    # An exclusive bound is tighter than an inclusive one at the same version.
    tightest_lower = max(lowers, key=lambda b: (b[0], not b[1]), default=None)
    tightest_upper = min(uppers, key=lambda b: (b[0], b[1]), default=None)
    return tightest_lower, tightest_upper


@dataclass(frozen=True)
class Requirement:
    """One dependency a consumer resolves, as declared by a crate."""

    kind: str
    target: str | None
    declared: str
    package: str
    req: str
    optional: bool
    default_features: bool
    features: tuple[str, ...]

    @property
    def key(self) -> tuple[str, str | None, str]:
        return (self.kind, self.target, self.declared)

    def describe(self) -> dict:
        """The requirement's compared fields, as reported."""
        return {
            "package": self.package,
            "req": self.req,
            "optional": self.optional,
            "default_features": self.default_features,
            "features": list(self.features),
        }

    def differences(self, other: "Requirement") -> list[str]:
        """Field-level differences between `self` (published) and `other` (source)."""
        found = []
        if self.package != other.package:
            found.append(f"package {self.package} -> {other.package}")
        if canonical_requirement(self.req) != canonical_requirement(other.req):
            found.append(f"req {self.req} -> {other.req}")
        if self.optional != other.optional:
            found.append(f"optional {_flag(self.optional)} -> {_flag(other.optional)}")
        if self.default_features != other.default_features:
            found.append(f"default-features {_flag(self.default_features)} -> "
                         f"{_flag(other.default_features)}")
        if self.features != other.features:
            found.append(f"features {list(self.features)} -> {list(other.features)}")
        return found


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _target_key(target: str | None) -> str | None:
    """A target spelled without whitespace, so `cfg(a = "b")` and `cfg(a="b")` agree."""
    return None if target is None else re.sub(r"\s+", "", target)


def _features(value: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(value)))


def _manifest_requirement(kind: str, target: str | None, declared: str,
                          value: str | Mapping) -> Requirement:
    detail = {"version": value} if isinstance(value, str) else value
    if "workspace" in detail:
        raise RequirementError(
            f"dependency {declared!r} is workspace-inherited: not a normalized manifest")
    return Requirement(
        kind=kind,
        target=_target_key(target),
        declared=declared,
        package=detail.get("package", declared),
        req=detail.get("version", "*"),
        optional=bool(detail.get("optional", False)),
        # Older cargo wrote the underscore spelling, which it still accepts.
        default_features=bool(detail.get("default-features", detail.get("default_features", True))),
        features=_features(detail.get("features", ())),
    )


def manifest_requirements(manifest: bytes) -> dict[tuple, Requirement]:
    """Normal and build requirements of a normalized `Cargo.toml`, keyed by `Requirement.key`.

    Covers `[dependencies]`, `[build-dependencies]`, and their `[target.<spec>.*]` forms.
    """
    try:
        document = tomllib.loads(manifest.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise RequirementError(f"unreadable manifest: {error}") from error
    found: dict[tuple, Requirement] = {}

    def collect(tables: Mapping, target: str | None) -> None:
        for table, kind in _MANIFEST_TABLES.items():
            for declared, value in tables.get(table, {}).items():
                requirement = _manifest_requirement(kind, target, declared, value)
                found[requirement.key] = requirement

    collect(document, None)
    for target, tables in document.get("target", {}).items():
        collect(tables, target)
    return found


def metadata_requirements(dependencies: Sequence[Mapping]) -> dict[tuple, Requirement]:
    """Normal and build requirements from a package's `cargo metadata` `dependencies`."""
    found: dict[tuple, Requirement] = {}
    for dependency in dependencies:
        kind = dependency.get("kind") or NORMAL
        if kind not in RESOLVED_KINDS:
            continue
        declared = dependency.get("rename") or dependency["name"]
        requirement = Requirement(
            kind=kind,
            target=_target_key(dependency.get("target")),
            declared=declared,
            package=dependency["name"],
            req=dependency["req"],
            optional=bool(dependency["optional"]),
            default_features=bool(dependency["uses_default_features"]),
            features=_features(dependency["features"]),
        )
        found[requirement.key] = requirement
    return found


@dataclass(frozen=True)
class DependencyDrift:
    """One dependency whose requirement differs between the registry copy and the source."""

    name: str
    kind: str
    target: str | None
    published: dict | None
    source: dict | None
    reason: str


def compare_requirements(published: Mapping[tuple, Requirement],
                         source: Mapping[tuple, Requirement]) -> tuple[DependencyDrift, ...]:
    """Dependencies added, removed, or changed in the source since the registry copy."""
    drift = []
    for key in sorted(published.keys() | source.keys(), key=lambda k: (k[0], k[1] or "", k[2])):
        old, new = published.get(key), source.get(key)
        kind, target, declared = key
        if old is None:
            reason = f"added: {new.req}"
        elif new is None:
            reason = f"removed: {old.req}"
        else:
            changes = old.differences(new)
            if not changes:
                continue
            reason = "; ".join(changes)
        drift.append(DependencyDrift(
            declared, kind, target,
            None if old is None else old.describe(),
            None if new is None else new.describe(),
            reason))
    return tuple(drift)
