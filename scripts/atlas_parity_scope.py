"""Public-surface routing is distinct from whole-API semantic qualification."""

from collections import Counter
import hashlib
from pathlib import Path

from atlas_parity_schema import (ParityError, digest, fields, local_path, need,
                                 read_json, revision, unique)
from atlas_parity_tables import canonical, unpack
from atlas_parity_scope_sources import audit_identity, classify, family_rows

VISIBILITY = {"documented_public", "public_export_or_view", "internal_source_candidate",
              "publicness_unresolved", "documented_extension_hook"}


def validate_bindings(rows, refs, contracts, capabilities, repositories):
    bindings = unique(rows, "reference_id", "public scope")
    need(set(bindings) == set(refs), "public scope: missing, extra or changed reference identity")
    for identity, row in bindings.items():
        fields(row, {"visibility": str, "identity_role": str, "contract": str,
                     "retained_obligation": bool, "signature_status": str,
                     "source_artifact": str, "source_row": int}, identity)
        need(row["visibility"] in VISIBILITY and row["retained_obligation"],
             f"{identity}: unsupported/private proposal cannot remove an obligation")
        need(row["signature_status"] and row["source_row"] >= 0,
             f"{identity}: missing signature disposition or source row")
        need(row["contract"] in contracts, f"{identity}: missing reusable contract")
        contract = contracts[row["contract"]]
        need(contract["framework"] == refs[identity]["framework"],
             f"{identity}: framework-specific variant linked to another framework")
    for identity, row in contracts.items():
        fields(row, {"framework": str, "source_artifact": str, "source_entry": list,
                     "capabilities": list, "prerequisites": list, "route_state": str,
                     "semantic_definition_complete": bool, "implementation_owner_verified": bool}, identity)
        need(not row["semantic_definition_complete"] and not row["implementation_owner_verified"],
             f"{identity}: routing does not establish complete semantic definition")
        need(row["route_state"] in {"canonical_family_proposal", "ownership_unresolved"},
             f"{identity}: unreviewed routing cannot claim implementation ownership")
        owner = row.get("planned_owner")
        need(owner is None or isinstance(owner, str) and owner in repositories,
             f"{identity}: unknown planned owner")
        need(all(isinstance(cap, str) and cap in capabilities for cap in row["capabilities"] + row["prerequisites"]),
             f"{identity}: unknown capability or prerequisite")
        if row["route_state"] == "ownership_unresolved":
            need(owner is None, f"{identity}: unresolved route cannot count a triage owner")
        else:
            need(bool(row["capabilities"]) and owner is not None and owner != "atlas" and
                 any(capabilities[cap]["owner"] == owner for cap in row["capabilities"]),
                 f"{identity}: planned provider differs from canonical capability owner")
            revision(row.get("owner_revision"), identity)
            need(row["owner_revision"] == repositories[owner]["candidate_revision"],
                 f"{identity}: planned owner revision differs from selected snapshot")
        expected = {dependency for cap in row["capabilities"]
                    for dependency in capabilities[cap]["prerequisites"]}
        need(set(row["prerequisites"]) == expected,
             f"{identity}: canonical upstream prerequisites lost or changed")
    return bindings


def source_records(document):
    """Decode the declared format; never mistake view deduplication for API loss."""
    return unpack(document)


def restore_audit(document, refs):
    """Prove the complete rich audit survives table storage/reference reuse."""
    metadata = dict(document["metadata"])
    fields(metadata, {"capture_receipt": dict, "restore_original_record": bool,
                      "duplicate_original_record": str}, "source-audit capture")
    receipt = metadata.pop("capture_receipt")
    digest(receipt.get("semantic_sha256"), "source-audit semantic receipt")
    restore_original = metadata.pop("restore_original_record")
    metadata.pop("duplicate_original_record")
    rows = []
    for original in source_records(document):
        fields(original, {"reference_id": str, "reference_sha256": str}, "source detail")
        need(original["reference_id"] in refs, "source detail: unknown reference identity")
        row = dict(original)
        identity = row.pop("reference_id")
        row.pop("reference_sha256")
        if restore_original:
            row["original_record"] = refs[identity]
        rows.append(row)
    result = {**metadata, "records": rows}
    need(hashlib.sha256(canonical(result).encode()).hexdigest() == receipt["semantic_sha256"],
         "public scope: rich audit roundtrip differs from captured source")
    return result


def validate_scope(root: Path, relative: str, refs: dict, capabilities: dict,
                   repositories: dict, snapshots: list) -> tuple[dict, list[Path]]:
    index_path = local_path(root, relative)
    index = read_json(index_path)
    fields(index, {"schema_version": int, "artifacts": list, "bindings": str,
                   "contracts": str, "full_public_surface_complete": bool,
                   "semantic_definition_complete": bool, "execution_credit": int,
                   "counts": dict}, "public scope")
    need(index["schema_version"] == 1 and not index["full_public_surface_complete"] and
         not index["semantic_definition_complete"] and index["execution_credit"] == 0,
         "bounded public-scope audits cannot qualify full definition or execution")
    artifacts = unique(index["artifacts"], "path", "public-scope artifact")
    paths, documents = [index_path], {}
    for identity, row in artifacts.items():
        fields(row, {"sha256": str, "role": str}, identity)
        digest(row["sha256"], identity)
        path = local_path(root, identity)
        need(hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"],
             f"{identity}: public-scope artifact hash drift")
        documents[identity] = read_json(path)
        paths.append(path)
    need(index["contracts"] in documents and index["bindings"] in documents,
         "public scope: unregistered contracts or bindings")
    contracts = unique(documents[index["contracts"]], "id", "reusable source contract")
    rows = source_records(documents[index["bindings"]])
    bindings = validate_bindings(rows, refs, contracts, capabilities, repositories)
    source_tables, restored, baselines = {}, {}, {}
    for snapshot in snapshots:
        data = read_json(local_path(root, snapshot["path"]))
        baselines[snapshot["framework"]] = {"version": snapshot["version"],
            "revision": data["source_revision"], "inventory_sha256": snapshot["sha256"]}
    for identity, row in bindings.items():
        path = row["source_artifact"]
        need(path in documents, f"{identity}: unregistered source detail")
        if path not in source_tables:
            restored[path] = restore_audit(documents[path], refs)
            framework = refs[identity]["framework"]
            audit_identity(framework, restored[path], baselines[framework])
            source_tables[path] = source_records(documents[path])
        records = source_tables[path]
        need(row["source_row"] < len(records), f"{identity}: missing source row")
        original = records[row["source_row"]]
        expected = hashlib.sha256(canonical(refs[identity]).encode()).hexdigest()
        need(original.get("reference_id") == identity and original.get("reference_sha256") == expected,
             f"{identity}: source detail belongs to another signature/declaration")
        framework = refs[identity]["framework"]
        visibility, role, family, signature = classify(framework, original)
        need((row["visibility"], row["identity_role"], row["contract"], row["signature_status"]) ==
             (visibility, role, framework + ":" + family, signature),
             f"{identity}: normalized binding differs from source classification/route/signature")
    derived_documents = {}
    for identity, row in contracts.items():
        need(row["source_artifact"] in documents, f"{identity}: missing contract source")
        framework = row["framework"]
        need(row["source_artifact"] == f"reference/public-scope/{framework}/contracts.json",
             f"{identity}: contract source belongs to another framework")
        current = documents[row["source_artifact"]]
        need(current.get("framework", framework) == framework,
             f"{identity}: raw source framework differs from normalized framework")
        try:
            for key in row["source_entry"]:
                current = current[key]
        except (KeyError, IndexError, TypeError) as error:
            raise ParityError(f"{identity}: missing reusable contract source entry") from error
        need(bool(current), f"{identity}: empty reusable contract")
        need(isinstance(current, dict) and current.get("contract_id", current.get("id")) == identity.split(":", 1)[1],
             f"{identity}: reusable source entry belongs to another contract")
        path = row["source_artifact"]
        if path not in derived_documents:
            key = "contracts" if framework == "numpy" else "contract_groups" if framework == "jax" else "families"
            derived_documents[path] = unique(family_rows(framework, documents[path], key, path,
                                             capabilities, repositories), "id", "source families")
        need(row == derived_documents[path].get(identity),
             f"{identity}: normalized owner/capability route differs from pinned source family")
    visibility = Counter(row["visibility"] for row in rows)
    unresolved = sum(contracts[row["contract"]]["route_state"] == "ownership_unresolved" for row in rows)
    summary = {"retained_raw_candidates": len(bindings), "visibility": dict(visibility),
               "reusable_framework_contracts": len(contracts),
               "planned_family_routes": len(bindings) - unresolved,
               "ownership_unresolved_candidates": unresolved,
               "implementation_owners_verified": 0, "new_semantic_closures": 0,
               "execution_credit": 0, "raw_candidates_removed": 0,
               "full_public_surface_complete": False}
    need(summary == index["counts"], "public scope: reported counts differ from actual conserved rows")
    return {"summary": summary, "bindings": bindings, "contracts": contracts}, paths
