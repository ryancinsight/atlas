#!/usr/bin/env python3
"""Audit Aequitas adoption and unit typing across the Atlas members.

The provider integration audit checks that each integrator names its
providers; the conformance scanner checks mechanical classes. This audit
covers the dimensioned-quantity seam: which members resolve Aequitas, at
which revision, whether that revision is the same one the rest of the stack
resolves, and which public trait getters still hand back a bare ``f64`` while
their doc comment names an SI unit.

Four findings it exists to catch, each measured rather than inferred:

- **Cohort skew.** A member pinned one commit behind Aequitas' default branch
  builds fine on its own and is invisible in every other gate. The audit
  names the majority revision and every outlier.
- **Requirement shape.** A requirement written as a range that crosses a
  0.x minor boundary (``>=0.3.1, <0.5.0``) is a breaking change by cargo's
  pre-1.0 rules: a fresh resolve may land on an API that no member has
  compiled against. The lock hides this until it does not.
- **Untyped SI getters.** A trait method returning ``f64`` directly under a
  doc comment that names ``[Pa]`` or ``(m/s)`` is the exact site where the
  unit exists only in prose. Scanning for it is how the kwavers acoustic
  surface was finished, and it is the cheapest cross-member check available.
- **Misleading unit suffixes.** An accessor named ``..._mm`` that returns a
  canonical-SI ``Length`` tells the reader the value is millimetres when it is
  metres. The type is right and the name is wrong, which is worse than either
  alone: a caller who trusts the suffix is off by 1000. The check compares the
  name's final scale token with the returned quantity alias' canonical unit; a
  compound unit name (``..._m_per_s``) is not read at all, because reading its
  last token would read ``s`` out of a velocity.

Reporting-oriented by default: findings are reported, not turned into a
synthetic failure. ``--strict`` exits non-zero when any finding exists, for
callers that want a gate.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
REPOS = ROOT / "repos"
PROVIDER = REPOS / "aequitas"
GITMODULES = ROOT / ".gitmodules"
MEMBER_PATH = re.compile(r"^\s*path\s*=\s*repos/(\S+)\s*$", re.MULTILINE)

SI_UNIT = re.compile(
    r"\[(?:Pa|m/s|kg/m[^\]\s]*|W/m[^\]\s]*|Np(?:/m)?|m²|m\^2|Hz|W|J|K|A|V|C|Ω)\]"
    r"|\((?:Pa|m/s|kg/m[^)\s]*|W/m[^)\s]*|Np/m|m²/s)\)"
)
F64_GETTER = re.compile(r"^\s*(?:fn|pub fn)\s+(\w+)\s*\([^)]*\)\s*->\s*f64")
TRAIT_START = re.compile(r"^\s*pub trait\s+(\w+)")
FROM_UNIT = re.compile(r"from_unit::<(\w+)>")
PUB_FN = re.compile(r"^\s*pub fn (\w+)\s*\(")

# Quantity alias -> canonical (base-scale) unit token, for the suffix check.
CANONICAL_UNIT = {
    "Length": "m",
    "Area": "m2",
    "Volume": "m3",
    "Mass": "kg",
    "Time": "s",
    "Velocity": "m/s",
    "Acceleration": "m/s2",
    "Pressure": "pa",
    "Stress": "pa",
    "Energy": "j",
    "Power": "w",
    "Force": "n",
    "Frequency": "hz",
    "Angle": "rad",
    "ThermodynamicTemperature": "k",
    "TemperatureDifference": "k",
    "MassDensity": "kg/m3",
    "AreaPerMass": "m2/kg",
    "ReciprocalLength": "1/m",
    "Intensity": "w/m2",
    "VolumetricPowerDensity": "w/m3",
    "AbsorbedDose": "gy",
    "SpecificHeatCapacity": "j/(kg*k)",
    "ThermalConductivity": "w/(m*k)",
    "ThermalDiffusivity": "m2/s",
    "DynamicViscosity": "pa*s",
    "KinematicViscosity": "m2/s",
    "ElectricalConductivity": "s/m",
    "ElectricPotential": "v",
    "ElectricCurrent": "a",
    "Capacitance": "f",
    "ElectricCharge": "c",
    "AcousticImpedance": "pa*s/m",
    "SurfaceTension": "n/m",
    "MolarEnergy": "j/mol",
    "MolarHeatCapacity": "j/(mol*k)",
    "ReactionRate": "mol/(m3*s)",
    "MolarConcentration": "mol/m3",
    "EnergyPerArea": "j/m2",
    "EnergyPerVolume": "j/m3",
    "ReciprocalTime": "1/s",
    "ReciprocalTemperature": "1/k",
    "NumberDensity": "1/m3",
    "VolumetricFlowRate": "m3/s",
    "HydraulicResistance": "pa*s/m3",
    "HydraulicInertance": "kg/m4",
    "Compliance": "m3/pa",
}

# Final name token -> the unit scale it claims. A token absent here is not a
# unit (``min`` is the minimum, not minutes).
NAME_UNIT = {
    "nm": "nm",
    "um": "um",
    "mm": "mm",
    "cm": "cm",
    "km": "km",
    "m": "m",
    "ns": "ns",
    "us": "us",
    "ms": "ms",
    "s": "s",
    "pa": "pa",
    "kpa": "kpa",
    "mpa": "mpa",
    "gpa": "gpa",
    "hz": "hz",
    "khz": "khz",
    "mhz": "mhz",
    "rad": "rad",
    "deg": "deg",
    "j": "j",
    "kj": "kj",
    "mj": "mj",
    "w": "w",
    "kw": "kw",
    "mw": "mw",
    "v": "v",
    "kv": "kv",
    "a": "a",
    "k": "k",
}
AEQUITAS_DEP = re.compile(
    r'^aequitas\s*=\s*\{([^}]*)\}|^aequitas\s*=\s*"([^"]+)"', re.MULTILINE
)
REV_FIELD = re.compile(r'rev\s*=\s*"([^"]+)"')
VERSION_FIELD = re.compile(r'version\s*=\s*"([^"]+)"')


@dataclass
class Member:
    """One Atlas member's Aequitas footprint."""

    name: str
    requirement: str | None = None
    locked_version: str | None = None
    locked_rev: str | None = None
    references: int = 0
    from_base: int = 0
    into_base: int = 0
    quantities: int = 0
    units_constructed: Counter = field(default_factory=Counter)
    untyped_si_getters: list[str] = field(default_factory=list)
    misleading_suffixes: list[str] = field(default_factory=list)

    @property
    def conversion_balance(self) -> int:
        """`from_base` sites minus `into_base` sites."""
        return self.from_base - self.into_base

    def as_json(self) -> dict:
        return {
            "member": self.name,
            "requirement": self.requirement,
            "locked_version": self.locked_version,
            "locked_rev": self.locked_rev,
            "references": self.references,
            "from_base": self.from_base,
            "into_base": self.into_base,
            "conversion_balance": self.conversion_balance,
            "quantities": self.quantities,
            "units_constructed": dict(self.units_constructed.most_common()),
            "untyped_si_getters": self.untyped_si_getters,
            "misleading_suffixes": self.misleading_suffixes,
        }


def _sources(member: Path) -> list[Path]:
    return [
        path
        for path in (
            list(member.glob("src/**/*.rs")) + list(member.glob("crates/*/src/**/*.rs"))
        )
        if path.is_file()
    ]


def _requirement(member: Path) -> str | None:
    manifests = [member / "Cargo.toml", *member.glob("crates/*/Cargo.toml")]
    for manifest in manifests:
        if not manifest.is_file():
            continue
        text = manifest.read_text(encoding="utf-8", errors="replace")
        match = AEQUITAS_DEP.search(text)
        if not match:
            continue
        body = match.group(1) or match.group(2) or ""
        rev = REV_FIELD.search(body)
        version = VERSION_FIELD.search(body)
        if rev and version:
            return f"{version.group(1)} @ {rev.group(1)[:9]}"
        if rev:
            return f"rev {rev.group(1)[:9]}"
        if version:
            return version.group(1)
        return "workspace"
    return None


def _locked_from(text: str) -> tuple[str | None, str | None]:
    for block in text.split("[[package]]"):
        if 'name = "aequitas"' not in block:
            continue
        version = re.search(r'version = "([^"]+)"', block)
        source = re.search(r'source = "([^"]+)"', block)
        revision = None
        if source and "#" in source.group(1):
            revision = source.group(1).rsplit("#", 1)[-1][:9]
        return version.group(1) if version else None, revision
    return None, None


def _locked(member: Path) -> tuple[str | None, str | None]:
    """The member's locked Aequitas, preferring the committed lock.

    A checkout inside the stack carries the `[patch]` overlay, whose path
    source replaces every first-party git source: the working lock then
    reports no revision at all even though the committed one names it. Read
    the revision from `HEAD` in that case, so a member is never reported as
    unpinned just because the overlay rewrote its working copy.
    """
    lock = member / "Cargo.lock"
    if not lock.is_file():
        return None, None
    version, revision = _locked_from(lock.read_text(encoding="utf-8", errors="replace"))
    if revision or version is None:
        return version, revision
    try:
        committed = subprocess.run(
            ["git", "-C", str(member), "show", "HEAD:Cargo.lock"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return version, revision
    committed_version, committed_revision = _locked_from(committed.stdout)
    if committed_revision:
        return committed_version or version, committed_revision
    return version, revision


def _untyped_si_getters(member: Path) -> list[str]:
    findings: list[str] = []
    for source in _sources(member):
        text = source.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        trait = None
        for index, line in enumerate(lines):
            start = TRAIT_START.match(line)
            if start:
                trait = start.group(1)
                continue
            if trait and line.startswith("}"):
                trait = None
                continue
            if not trait:
                continue
            getter = F64_GETTER.match(line)
            if not getter:
                continue
            doc = " ".join(lines[max(0, index - 3): index])
            if SI_UNIT.search(doc):
                rel = source.relative_to(member).as_posix()
                findings.append(f"{rel}:{index + 1} {trait}::{getter.group(1)}")
    return findings


def _misleading_suffixes(member: Path) -> list[str]:
    """Accessors whose name claims a unit other than the returned quantity's.

    Only `&self` methods are considered: a free function named `length_mm`
    taking millimetres is a constructor, and its name is the input unit.

    A compound unit in the name (`..._m_per_s`, `..._w_per_m2`) is not read at
    all: the single-token table below carries scales, and reading the last
    token of a compound unit would read `s` out of `m_per_s` and report a
    velocity accessor whose name is correct.
    """
    findings: list[str] = []
    for source in _sources(member):
        lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines):
            match = PUB_FN.match(line)
            if match is None or "&self" not in line:
                continue
            signature = " ".join(lines[index:index + 8])
            returned = re.search(r"->\s*([A-Za-z_]\w*)", signature)
            unit = CANONICAL_UNIT.get(returned.group(1)) if returned else None
            if unit is None:
                continue
            name = match.group(1)
            if "_" not in name or "_per_" in name:
                continue
            claimed = NAME_UNIT.get(name.rsplit("_", 1)[-1].lower())
            if claimed is None or claimed == unit:
                continue
            rel = source.relative_to(member).as_posix()
            findings.append(f"{rel}:{index + 1} {name} returns {unit}, name claims {claimed}")
    return findings


def scan(member: Path) -> Member:
    """Collect one member's Aequitas footprint."""
    record = Member(name=member.name)
    record.requirement = _requirement(member)
    record.locked_version, record.locked_rev = _locked(member)
    for source in _sources(member):
        text = source.read_text(encoding="utf-8", errors="replace")
        record.references += text.count("aequitas::")
        record.from_base += text.count("from_base(")
        record.into_base += text.count("into_base()")
        record.quantities += text.count("Quantity<")
        record.units_constructed.update(FROM_UNIT.findall(text))
    record.untyped_si_getters = _untyped_si_getters(member)
    record.misleading_suffixes = _misleading_suffixes(member)
    return record


def registered_members() -> set[str]:
    """The package set the stack records, from `.gitmodules`.

    A directory under `repos/` that `.gitmodules` does not record is local work,
    not a member. Measuring it would report a cohort outlier no pin can move and
    no release gate covers, so the audit's subject is the recorded set. An
    unreadable `.gitmodules` falls back to the directory scan.
    """
    try:
        return set(MEMBER_PATH.findall(GITMODULES.read_text(encoding="utf-8", errors="replace")))
    except OSError:
        return set()


def spanning_range(requirement: str | None) -> bool:
    """Whether a requirement admits two 0.x minors, a breaking boundary."""
    if not requirement:
        return False
    minors = {int(part) for part in re.findall(r"0\.(\d+)\.", requirement)}
    return len(minors) > 1


def provider_head() -> str | None:
    """The provider's default-branch revision, or None when unreadable."""
    try:
        resolved = subprocess.run(
            ["git", "-C", str(PROVIDER), "rev-parse", "origin/main"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return resolved.stdout.strip()[:9] or None


def commits_behind(revision: str, head: str) -> int | None:
    """How many provider commits `revision` lacks, or None when unknown."""
    try:
        counted = subprocess.run(
            ["git", "-C", str(PROVIDER), "rev-list", "--count", f"{revision}..{head}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return int(counted.stdout.strip())


def report(records: list[Member], strict: bool, as_json: bool) -> int:
    """Print the audit and return the process status."""
    revs = Counter(record.locked_rev for record in records if record.locked_rev)
    majority_rev, majority_count = (revs.most_common(1)[0] if revs else (None, 0))
    head = provider_head()

    findings: list[str] = []
    if head:
        # Direction matters: a member one commit behind the provider's default
        # branch is a sweep behind, whatever the majority resolves. Comparing
        # against the majority instead would call a lagging stack consistent.
        for record in records:
            if not record.locked_rev or record.locked_rev == head:
                continue
            behind = commits_behind(record.locked_rev, head)
            if behind is None:
                detail = "not an ancestor of the default branch"
            elif behind == 0:
                detail = "ahead of the default branch"
            else:
                detail = f"{behind} commit(s) behind"
            findings.append(
                f"cohort skew: {record.name} resolves aequitas "
                f"{record.locked_version} at {record.locked_rev}, {detail} "
                f"({head})"
            )
    elif majority_rev:
        for record in records:
            if record.locked_rev and record.locked_rev != majority_rev:
                findings.append(
                    f"cohort skew: {record.name} resolves aequitas "
                    f"{record.locked_version} at {record.locked_rev}, the majority "
                    f"({majority_count} members) at {majority_rev}"
                )
    for record in records:
        if spanning_range(record.requirement):
            findings.append(
                f"requirement shape: {record.name} admits two 0.x minors "
                f"({record.requirement}), which cargo treats as a breaking boundary"
            )
        for getter in record.untyped_si_getters:
            findings.append(
                f"untyped SI getter: {record.name} {getter} returns f64 beneath an SI unit"
            )
        for suffix in record.misleading_suffixes:
            findings.append(f"unit suffix: {record.name} {suffix}")

    if as_json:
        print(
            json.dumps(
                {
                    "provider_head": head,
                    "majority_revision": majority_rev,
                    "members": [record.as_json() for record in records],
                    "findings": findings,
                },
                indent=2,
            )
        )
        return 1 if strict and findings else 0

    print(f"aequitas default branch: {head or 'unresolved'}")
    print(f"aequitas cohort: {majority_rev or 'unresolved'} ({majority_count} members)")
    print()
    header = f"{'member':14} {'locked':10} {'rev':11} {'refs':>6} {'from':>6} {'into':>6} {'quant':>6}"
    print(header)
    for record in sorted(records, key=lambda item: -item.references):
        if not (record.references or record.locked_version):
            continue
        print(
            f"{record.name:14} {record.locked_version or '-':10} "
            f"{record.locked_rev or '-':11} {record.references:6} "
            f"{record.from_base:6} {record.into_base:6} {record.quantities:6}"
        )

    units = Counter()
    for record in records:
        units.update(record.units_constructed)
    if units:
        print("\nunits constructed through from_unit::<U>:")
        print("  " + ", ".join(f"{unit} x{count}" for unit, count in units.most_common()))

    print(f"\n{len(findings)} finding(s)")
    for finding in findings:
        print(f"  {finding}")
    return 1 if strict and findings else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--members", default="", help="comma-separated subset (default: all)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict", action="store_true", help="fail when a finding exists")
    args = parser.parse_args()

    wanted = {name.strip() for name in args.members.split(",") if name.strip()}
    registered = registered_members()
    records = []
    for member in sorted(path for path in REPOS.iterdir() if path.is_dir()):
        if wanted and member.name not in wanted:
            continue
        if registered and member.name not in registered:
            continue
        if not (member / "Cargo.toml").is_file() and not any(member.glob("crates/*/Cargo.toml")):
            continue
        records.append(scan(member))
    return report(records, args.strict, args.format == "json")


if __name__ == "__main__":
    sys.exit(main())
