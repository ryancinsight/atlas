"""Validate the versioned four-framework parity program, without runtime builds."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from atlas_parity_decisions import validate_decisions
from atlas_parity_closure import validate_closure
from atlas_parity_evidence import (PROMOTED, review, states, validate_evidence,
                                   validate_mappings, validate_source_definition)
from atlas_parity_references import references
from atlas_parity_repository import ATLAS_GATES, RUST_GATES, validate_repository_evidence
from atlas_parity_schema import (ParityError, api_identity, dag, digest, fields, https,
                                 local_path, need, nonempty, read_json, revision, unique)

FRAMEWORKS = {"numpy", "jax", "pytorch", "tensorflow"}
DEFAULT = Path(__file__).resolve().parents[1] / "docs" / "parity"



def program_structure(program: dict, capabilities: dict, repositories: dict, packages: dict) -> None:
    revision(program["atlas_base_revision"], "Atlas baseline")
    for repo, row in repositories.items():
        fields(row, {"baseline_revision": str, "entry": list, "exit": list, "specific_exit": str}, repo)
        revision(row["baseline_revision"], repo)
        revision(row.get("candidate_revision"), f"{repo} candidate")
        fields(row, {"required_gates": list, "qualification_evidence": list}, repo)
        minimum = ATLAS_GATES if repo == "atlas" else RUST_GATES
        need(minimum <= set(row["required_gates"]), f"{repo}: required exit gates removed")
        need(bool(row["entry"]) and bool(row["exit"]), f"{repo}: missing 1.0 criteria")
        nonempty(row["specific_exit"], repo)
    for identity, row in capabilities.items():
        fields(row, {"owner": str, "contract": dict, "tests": dict, "benchmark": dict,
                     "status": dict, "definition_of_done": str}, identity)
        need(row["owner"] in repositories, f"{identity}: unknown owner")
        revision(row.get("target_revision"), f"{identity} target")
        need(row["target_revision"] == repositories[row["owner"]]["candidate_revision"],
             f"{identity}: target revision differs from owner snapshot")
        for key in ("semantics", "dtypes", "devices", "layouts", "gradients", "error_domain", "coverage_state"):
            nonempty(row["contract"].get(key), f"{identity}:{key}")
        for key in ("analytical", "differential", "integration"):
            nonempty(row["tests"].get(key), f"{identity}:{key}")
        fields(row["benchmark"], {"workloads": str, "target": str, "hardware": list}, identity)
        need(bool(row["benchmark"]["hardware"]), f"{identity}: required hardware missing")
        states(row["status"], identity)
        need(row["status"]["mapping"] == "unmapped" and all(
            row["status"][stage] != value for stage, value in PROMOTED.items()),
            f"{identity}: family labels cannot assert API qualification; use per-API mappings")
    dag(capabilities, "prerequisites", "capability")
    dag(packages, "dependencies", "work package")
    suppliers = {}
    for identity, row in packages.items():
        fields(row, {"owner": str, "capabilities": list, "estimate": dict,
                     "acceptance": str, "readiness": str, "state": str}, identity)
        need(row["owner"] in repositories, f"{identity}: unknown package owner")
        nonempty(row["acceptance"], identity)
        nonempty(row["readiness"], identity)
        estimate = row["estimate"]
        low, high = estimate.get("engineer_weeks_low"), estimate.get("engineer_weeks_high")
        need(type(low) in (int, float) and type(high) in (int, float) and 0 <= low <= high,
             f"{identity}: invalid estimate range")
        need(estimate.get("confidence") in {"low", "medium", "high"}, f"{identity}: no confidence")
        for capability in row["capabilities"]:
            need(capability in capabilities, f"{identity}: unknown capability {capability}")
            suppliers.setdefault(capability, set()).add(identity)
    need(set(suppliers) == set(capabilities), "capability has no implementation work package")

    def ancestors(identity: str) -> set[str]:
        result = {identity}
        for dependency in packages[identity]["dependencies"]:
            result.update(ancestors(dependency))
        return result

    for identity, row in packages.items():
        available = ancestors(identity)
        for capability in row["capabilities"]:
            for prerequisite in capabilities[capability]["prerequisites"]:
                need(bool(suppliers[prerequisite] & available),
                     f"{identity}: capability prerequisite {prerequisite} scheduled later")


def load(root: Path = DEFAULT) -> dict:
    program = read_json(local_path(root, "program.json"))
    fields(program, {"schema_version": int, "program_version": str, "atlas_base_revision": str,
                     "definition_complete": bool, "reference_snapshots": list, "files": dict,
                     "open_decisions": list, "definition_gaps": list,
                     "implementation_blockers": list}, "program")
    need(program["schema_version"] == 1, "unsupported parity schema version")
    objects = {}
    for key in ("capabilities", "repositories", "work_packages", "mappings", "evidence", "repository_evidence", "decisions"):
        value = read_json(local_path(root, program["files"].get(key)))
        need(isinstance(value, list), f"{key}: expected list")
        objects[key] = value
    capabilities = unique(objects["capabilities"], "id", "capability")
    repositories = unique(objects["repositories"], "repository", "repository")
    packages = unique(objects["work_packages"], "id", "work package")
    decisions = validate_decisions(program, objects["decisions"], repositories)
    need(bool(capabilities) and bool(repositories) and bool(packages), "program cannot have empty owner/DAG sets")
    program_structure(program, capabilities, repositories, packages)
    refs, summaries = references(root, program["reference_snapshots"])
    closure, extra_inputs = validate_closure(root, program["files"].get("reference_closure"), program)
    mappings, assigned = validate_mappings(objects["mappings"], capabilities, refs, repositories)
    specified = {ref: mapping_id for ref, mapping_id in assigned.items()
                 if mappings[mapping_id]["status"]["mapping"] == "specified"}
    for row in mappings.values():
        if "source_contract" not in row:
            continue
        contract = row["source_contract"]
        fields(contract, {"path": str, "sha256": str, "entry": list}, row["id"])
        source = local_path(root, contract["path"])
        need(hashlib.sha256(source.read_bytes()).hexdigest() == contract["sha256"],
             f"{row['id']}: semantic source-contract hash drift")
        document = read_json(source)
        current = document
        try:
            for key in contract["entry"]:
                current = current[key]
        except (KeyError, IndexError, TypeError) as error:
            raise ParityError(f"{row['id']}: missing semantic contract entry") from error
        need(bool(current), f"{row['id']}: empty semantic contract")
        validate_source_definition(row, current)
        symbols = set()
        if isinstance(current, dict):
            if isinstance(current.get("symbol"), str):
                symbols.add(current["symbol"])
            symbols.update(current.get("endpoints", []))
            if (not symbols and document.get("framework") == "numpy" and contract["entry"] and
                    isinstance(contract["entry"][-1], str)):
                name = contract["entry"][-1]
                signature = next((current[key] for key in ("published_signature", "runtime_python_signature",
                                 "published_text_signature") if key in current), "")
                need(signature.startswith(name + "("), f"{row['id']}: signature/entry mismatch")
                symbols.add("numpy." + name)
        need(bool(symbols) and all(refs[identity]["symbol"] in symbols for identity in row["reference_ids"]),
             f"{row['id']}: semantic source entry belongs to another public endpoint")
        extra_inputs.append(source)
    for snapshot in program["reference_snapshots"]:
        if snapshot["semantics_complete"]:
            need(all(identity in specified for identity, row in refs.items()
                     if row["framework"] == snapshot["framework"]),
                 f"{snapshot['framework']}: semantics_complete contradicts unmapped APIs")
    evidence = validate_evidence(objects["evidence"], mappings, capabilities, refs)
    repository_evidence, qualified_repositories = validate_repository_evidence(objects["repository_evidence"], repositories)
    for name, row in repositories.items():
        if row.get("status") == "qualified":
            ids = row["qualification_evidence"]
            need(bool(ids) and all(identity in repository_evidence and
                 repository_evidence[identity]["repository"] == name for identity in ids),
                 f"{name}: qualified repository without exact exit evidence")
    result = {"program": program, "capabilities": capabilities, "repositories": repositories,
              "packages": packages, "references": refs, "snapshots": summaries,
              "mappings": mappings, "assigned": assigned, "evidence": evidence,
              "specified": specified,
              "decisions": decisions,
              "reference_closure": closure, "extra_inputs": extra_inputs,
              "repository_evidence": repository_evidence, "qualified_repositories": qualified_repositories}
    if program["definition_complete"]:
        need(not definition_blockers(result), "definition_complete contradicts unresolved obligations")
    return result


def definition_blockers(bundle: dict) -> list[str]:
    program = bundle["program"]
    blockers = [f"{row['framework']}: public source extraction incomplete"
                for row in bundle["snapshots"] if not row["public_surface_complete"]]
    unresolved = len(bundle["references"]) - len(bundle.get("specified", bundle["assigned"]))
    if unresolved:
        blockers.append(f"{unresolved} API declarations lack complete semantic mappings")
    if program["open_decisions"]:
        blockers.append(f"{len(program['open_decisions'])} scope/architecture decisions open")
    blockers.extend(program["definition_gaps"])
    return blockers


def qualification(bundle: dict, gate: str, candidate: str, external: dict | None = None) -> list[str]:
    blockers = definition_blockers(bundle)
    program = bundle["program"]
    if not program["definition_complete"]:
        blockers.append("definition_complete is false")
    external = external or {}
    if "definition_review" in external:
        review(external["definition_review"], candidate, "definition review")
    else:
        blockers.append("independent exact-final-revision definition review pending")
    if gate == "release":
        blockers.extend(f"implementation: {item}" for item in program["implementation_blockers"])
        for mapping_id, row in bundle["mappings"].items():
            missing = [stage for stage, value in PROMOTED.items() if row["status"][stage] != value]
            if missing:
                blockers.append(f"{mapping_id}: unqualified {', '.join(missing)}")
        _, extra_qualified = validate_repository_evidence(
            external.get("repository_evidence", []), bundle["repositories"], candidate)
        qualified = (bundle["qualified_repositories"] - {"atlas"}) | extra_qualified
        for name in bundle["repositories"]:
            if name not in qualified:
                blockers.append(f"{name}: repository exit criteria unqualified")
        if "release_review" not in external:
            blockers.append("independent exact-final-revision release review pending")
        else:
            review(external["release_review"], candidate, "release review")
    return blockers


def report(bundle: dict) -> dict:
    return {"program_version": bundle["program"]["program_version"],
            "snapshots": bundle["snapshots"], "reference_declarations": len(bundle["references"]),
            "mapped_declarations": len(bundle["specified"]),
            "partially_mapped_declarations": len(bundle["assigned"]) - len(bundle["specified"]),
            "unmapped_declarations": len(bundle["references"]) - len(bundle["assigned"]),
            "capabilities": len(bundle["capabilities"]), "repositories": len(bundle["repositories"]),
            "work_packages": len(bundle["packages"]), "evidence_records": len(bundle["evidence"]),
            "resolved_policy_decisions": len(bundle["program"].get("resolved_policy_decisions", [])),
            "open_policy_decisions": len(bundle["program"]["open_decisions"]),
            "implementation_blockers": bundle["program"]["implementation_blockers"],
            "reference_closure": bundle["reference_closure"],
            "definition_blockers": definition_blockers(bundle)}


def committed_inputs(paths: list[Path], repository: Path, candidate: str) -> list[str]:
    """Bind consumed bytes to HEAD, including files that status would ignore."""
    blockers = []
    for path in sorted(set(path.resolve() for path in paths)):
        if not path.is_relative_to(repository.resolve()):
            blockers.append(f"qualification input outside candidate checkout: {path}")
            continue
        relative = path.relative_to(repository.resolve()).as_posix()
        result = subprocess.run(["git", "-C", str(repository), "rev-parse", f"{candidate}:{relative}"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, check=False)
        actual = subprocess.run(["git", "-C", str(repository), "hash-object", "--path", relative, str(path)],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, check=False)
        if result.returncode or actual.returncode or result.stdout.strip() != actual.stdout.strip():
            blockers.append(f"qualification input differs from committed candidate: {relative}")
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "report", "qualify"))
    parser.add_argument("--root", type=Path, default=DEFAULT)
    parser.add_argument("--gate", choices=("definition", "release"), default="definition")
    parser.add_argument("--review-evidence", type=Path,
                        help="External post-commit exact-revision review/repository evidence JSON")
    args = parser.parse_args()
    try:
        bundle = load(args.root)
        if args.mode == "qualify":
            candidate = subprocess.check_output(["git", "-C", str(args.root), "rev-parse", "HEAD"],
                                                text=True, encoding="utf-8", errors="replace", timeout=10).strip()
            repository_root = Path(subprocess.check_output(
                ["git", "-C", str(args.root), "rev-parse", "--show-toplevel"], text=True, encoding="utf-8", errors="replace", timeout=10).strip())
            dirty = subprocess.check_output(["git", "-C", str(repository_root), "status", "--porcelain",
                                              "--untracked-files=all"], text=True, encoding="utf-8", errors="replace", timeout=10)
            external = None
            if args.review_evidence:
                need(not args.review_evidence.resolve().is_relative_to(repository_root.resolve()),
                     "post-commit review evidence must be external to the candidate checkout")
                external = read_json(args.review_evidence)
                fields(external, {"candidate_revision": str}, "external review evidence")
                need(external["candidate_revision"] == candidate, "external review names a different candidate")
            blockers = qualification(bundle, args.gate, candidate, external)
            inputs = [local_path(args.root, "program.json")]
            inputs.extend(local_path(args.root, path) for path in bundle["program"]["files"].values())
            inputs.extend(local_path(args.root, item["path"]) for item in bundle["program"]["reference_snapshots"])
            for snapshot in bundle["program"]["reference_snapshots"]:
                inputs.extend(local_path(args.root, item["path"]) for item in snapshot.get("supplements", []))
            inputs.extend(bundle["extra_inputs"])
            inputs.extend(Path(__file__).parent.glob("atlas_parity*.py"))
            inputs.append(Path(__file__).parent / "atlas-parity.py")
            blockers.extend(committed_inputs(inputs, repository_root, candidate))
            if dirty:
                blockers.append("working tree differs from the committed candidate revision")
            print(json.dumps({"gate": args.gate, "candidate_revision": candidate,
                              "qualified": not blockers, "blockers": blockers}, indent=2))
            return 1 if blockers else 0
        print(json.dumps(report(bundle), indent=2))
        return 0
    except (ParityError, OSError, subprocess.SubprocessError) as error:
        print(f"atlas-parity: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
