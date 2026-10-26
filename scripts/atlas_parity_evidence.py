"""Validate per-API semantic coverage and independent evidence stages."""

from __future__ import annotations

from atlas_parity_schema import digest, fields, https, need, nonempty, revision, unique

STATES = {
    "mapping": {"unmapped", "partial", "specified"},
    "implementation": {"unknown", "absent", "partial", "implemented"},
    "tested": {"unrun", "failed", "passed", "unavailable"},
    "external": {"unrun", "failed", "passed", "unavailable"},
    "performance": {"unrun", "failed", "qualified", "unavailable"},
    "release": {"unreleased", "released"},
}
PROMOTED = {"implementation": "implemented", "tested": "passed", "external": "passed",
            "performance": "qualified", "release": "released"}
AXES = ("dtype", "device", "layout", "gradient", "execution", "domain")


def states(record: dict, context: str) -> None:
    fields(record, {key: str for key in STATES}, context)
    for key, allowed in STATES.items():
        need(record[key] in allowed, f"{context}: invalid {key} state {record[key]}")


def review(record: dict, expected: str, context: str) -> None:
    fields(record, {"state": str, "revision": str, "artifact": str, "independent": bool}, context)
    need(record["state"] == "approved" and record["independent"], f"{context}: independent review absent")
    revision(record["revision"], context)
    need(record["revision"] == expected, f"{context}: stale review revision")
    https(record["artifact"], context)


def validate_mappings(rows: list[dict], capabilities: dict, references: dict,
                      repositories: dict) -> tuple[dict, dict]:
    mappings = unique(rows, "id", "mapping")
    assigned = {}
    for identity, row in mappings.items():
        fields(row, {"capability": str, "owner": str, "revision": str, "canonical_operation": str,
                     "reference_ids": list, "variants": list, "coverage_classes": list,
                     "status": dict, "stage_evidence": dict, "source_contract": dict}, identity)
        need(row["capability"] in capabilities, f"{identity}: unknown capability")
        need(row["owner"] == capabilities[row["capability"]]["owner"], f"{identity}: conflicting owner")
        def upstream(capability: str) -> set[str]:
            result = set()
            for dependency in capabilities[capability].get("prerequisites", []):
                result.add(dependency)
                result.update(upstream(dependency))
            return result
        for prerequisite in row.get("prerequisites", []):
            fields(prerequisite, {"capability": str, "contract": str}, identity)
            nonempty(prerequisite["contract"], identity)
            need(prerequisite["capability"] in upstream(row["capability"]),
                 f"{identity}: semantic prerequisite absent from acyclic provider order")
        revision(row["revision"], identity)
        need(row["revision"] == repositories[row["owner"]]["candidate_revision"],
             f"{identity}: mapping is outside the selected exact revision")
        nonempty(row["canonical_operation"], identity)
        states(row["status"], identity)
        need(row["status"]["mapping"] in {"partial", "specified"}, f"{identity}: mapping row has no semantic contract")
        if row["status"]["mapping"] == "partial":
            fields(row, {"unresolved_obligations": list, "source_contract": dict}, identity)
            need(bool(row["unresolved_obligations"]), f"{identity}: partial mapping needs named remaining obligations")
            need(all(isinstance(item, str) and item.strip() for item in row["unresolved_obligations"]),
                 f"{identity}: invalid unresolved obligation")
            need(all(row["status"][stage] != value for stage, value in PROMOTED.items()),
                 f"{identity}: partial semantic contract cannot claim full API qualification")
        else:
            need(not row.get("unresolved_obligations"),
                 f"{identity}: specified mapping retains unresolved obligations")
        need(bool(row["reference_ids"]), f"{identity}: no reference APIs")
        need(len(set(row["reference_ids"])) == len(row["reference_ids"]), f"{identity}: duplicate references")
        for ref in row["reference_ids"]:
            need(ref in references, f"{identity}: unknown reference {ref}")
            need(ref not in assigned, f"{identity}: reference has multiple canonical owners: {ref}")
            assigned[ref] = identity
        variants = unique(row["variants"], "reference_id", f"{identity} variant")
        need(set(variants) == set(row["reference_ids"]), f"{identity}: missing framework semantic variant")
        for ref, variant in variants.items():
            fields(variant, {"semantics": str, "error_cases": list, "coverage_proof": str,
                             "analytical_tests": list, "differential_tests": list,
                             "benchmarks": list, "hardware": list}, f"{identity}:{ref}")
            for key in ("semantics", "coverage_proof"):
                nonempty(variant[key], f"{identity}:{key}")
            for key in ("error_cases", "analytical_tests", "differential_tests", "benchmarks", "hardware"):
                need(bool(variant[key]), f"{identity}:{key}: empty contract")
        classes = unique(row["coverage_classes"], "id", f"{identity} coverage")
        need(bool(classes), f"{identity}: no materialized coverage classes")
        covered_refs = set()
        for class_id, item in classes.items():
            fields(item, {"reference_id": str, **{axis: str for axis in AXES}}, class_id)
            need(item["reference_id"] in variants, f"{class_id}: unknown reference variant")
            covered_refs.add(item["reference_id"])
            for axis in AXES:
                nonempty(item[axis], f"{class_id}:{axis}")
                need(item[axis].lower() not in {"unknown", "unmapped", "todo", "all", "reference_valid_combinations"},
                     f"{class_id}:{axis}: unresolved coverage")
        need(covered_refs == set(variants), f"{identity}: variant without coverage classes")
    return mappings, assigned


def validate_source_definition(mapping: dict, entry: dict) -> None:
    """Source-backed specification requires explicit whole-API definition closure."""
    if mapping["status"]["mapping"] == "specified":
        need(isinstance(entry, dict) and isinstance(entry.get("status"), dict) and
             entry["status"].get("source_contract_defined") is True,
             f"{mapping['id']}: bound source contract remains partial or undefined")


def validate_evidence(rows: list[dict], mappings: dict, capabilities: dict, references: dict) -> dict:
    evidence = unique(rows, "id", "evidence")
    for identity, row in evidence.items():
        fields(row, {"stage": str, "owner": str, "revision": str, "capability": str,
                     "mapping_ids": list, "command": str, "result": str, "skipped": int,
                     "executed": int, "artifact": str, "sha256": str, "environment": dict,
                     "coverage": list, "execution_device_by_class": dict, "review": dict}, identity)
        need(row["stage"] in PROMOTED, f"{identity}: invalid evidence stage")
        revision(row["revision"], identity)
        https(row["artifact"], identity)
        digest(row["sha256"], identity)
        nonempty(row["command"], identity)
        need(row["capability"] in capabilities, f"{identity}: unknown capability")
        need(row["owner"] == capabilities[row["capability"]]["owner"], f"{identity}: conflicting owner")
        need(bool(row["mapping_ids"]) and bool(row["coverage"]) and bool(row["environment"]),
             f"{identity}: incomplete execution identity")
        need(row["executed"] > 0 and row["skipped"] == 0 and row["result"] == "success",
             f"{identity}: skipped, unavailable, failed or unexecuted evidence is not verification")
        review(row["review"], row["revision"], identity)
        declared = {}
        for mapping_id in row["mapping_ids"]:
            need(mapping_id in mappings, f"{identity}: unknown mapping")
            mapping = mappings[mapping_id]
            need(mapping["capability"] == row["capability"] and mapping["owner"] == row["owner"],
                 f"{identity}: mapping ownership mismatch")
            need(mapping["revision"] == row["revision"], f"{identity}: stale execution revision")
            for item in mapping["coverage_classes"]:
                need(item["id"] not in declared, f"{identity}: ambiguous coverage identity")
                declared[item["id"]] = item
        for class_id in row["coverage"]:
            need(class_id in declared, f"{identity}: undeclared coverage {class_id}")
            need(row["execution_device_by_class"].get(class_id) == declared[class_id]["device"],
                 f"{identity}: silent fallback or device mismatch for {class_id}")
        if row["stage"] == "external":
            fields(row, {"oracle_releases": dict, "input_sha256": str, "numerical_bound": str}, identity)
            need(bool(row["oracle_releases"]), f"{identity}: unpinned differential oracle")
            for class_id in row["coverage"]:
                ref = references[declared[class_id]["reference_id"]]
                need(row["oracle_releases"].get(ref["framework"]) == ref["version"],
                     f"{identity}: oracle release differs from frozen {ref['framework']} {ref['version']}")
                companion = ref.get("companion_version")
                if companion:
                    package, version = companion.split("==", 1)
                    need(row["oracle_releases"].get(package) == version,
                         f"{identity}: companion oracle release differs from frozen {companion}")
            digest(row["input_sha256"], identity)
            nonempty(row["numerical_bound"], identity)
        if row["stage"] == "performance":
            fields(row, {"baseline_revision": str, "target": str, "measurement": dict}, identity)
            revision(row["baseline_revision"], identity)
            nonempty(row["target"], identity)
            need(bool(row["measurement"]), f"{identity}: no matched measurement")
        if row["stage"] == "release":
            fields(row, {"registry_artifact": str, "fresh_consumer_artifact": str}, identity)
            https(row["registry_artifact"], identity)
            https(row["fresh_consumer_artifact"], identity)
    for mapping_id, mapping in mappings.items():
        classes = {item["id"] for item in mapping["coverage_classes"]}
        for stage, promoted in PROMOTED.items():
            if mapping["status"][stage] != promoted:
                continue
            ids = mapping["stage_evidence"].get(stage, [])
            need(bool(ids), f"{mapping_id}: promoted {stage} without evidence")
            covered = set()
            for evidence_id in ids:
                need(evidence_id in evidence, f"{mapping_id}: missing evidence {evidence_id}")
                record = evidence[evidence_id]
                need(record["stage"] == stage and mapping_id in record["mapping_ids"],
                     f"{mapping_id}: wrong evidence stage or mapping")
                covered.update(record["coverage"])
            need(classes <= covered, f"{mapping_id}: {stage} did not execute every coverage class")
    return evidence
