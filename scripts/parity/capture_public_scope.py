"""Capture source-audit proposals; never promote them to semantic/runtime proof.

All four input directories are explicit. This command reads already acquired
source audits, not framework runtimes or the network. Frozen reference records
stay in their canonical inventories; removed duplicate originals are restored by
reference_id and checked canonical SHA-256. Record tables preserve other fields.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlas_parity_references import references
from atlas_parity_schema import api_identity, need, read_json
from atlas_parity_tables import canonical, pack, unpack
from atlas_parity_scope_sources import audit_identity, classify, family_rows, input_parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value, compact=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = canonical(value) if compact else json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def source_document(base, framework):
    files = {"numpy": "classifications.json", "jax": "public-scope.json",
             "pytorch": "scope.json", "tensorflow": "classified-declarations.json"}
    path = base / files[framework]
    document = read_json(path)
    return document, {"name": path.name, "sha256": sha(path.read_bytes()), "bytes": path.stat().st_size,
                      "semantic_sha256": sha(canonical(document).encode())}


def contract_document(base, framework, document):
    paths = {"numpy": "reusable-contracts.json", "pytorch": "families.json",
             "tensorflow": "semantic-families.json"}
    if framework == "jax":
        return {"contract_groups": document["contract_groups"]}, "contract_groups"
    data = read_json(base / paths[framework])
    return data, "contracts" if framework == "numpy" else "families"



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    for framework in ["numpy", "jax", "pytorch", "tensorflow"]:
        parser.add_argument("--" + framework, type=Path, required=True)
    parser.add_argument("--tensorflow-correction", type=Path,
                        help="Reviewed correction over the unchanged frozen TensorFlow source-audit inputs")
    args = parser.parse_args()
    root = args.root.resolve()
    program = read_json(root / "program.json")
    refs, _ = references(root, program["reference_snapshots"])
    caps = {row["id"]: row for row in read_json(root / program["files"]["capabilities"])}
    repos = {row["repository"]: row for row in read_json(root / program["files"]["repositories"])}
    target = root / "reference" / "public-scope"
    baselines = {}
    for snapshot in program["reference_snapshots"]:
        data = read_json(root / snapshot["path"])
        baselines[snapshot["framework"]] = {"version": snapshot["version"],
            "revision": data["source_revision"], "inventory_sha256": snapshot["sha256"],
            "inventory_records": snapshot["records"]}
    contracts, bindings, receipts, captured_paths = [], [], [], []
    extras = {"numpy": ["sources.json", "signature-extraction.json", "rules-and-exceptions.json",
                         "ownership-exceptions.json", "miscellaneous-routing-audit.json", "correction-history.json"],
              "jax": ["architecture-dispositions.json"],
              "pytorch": ["sources.json", "source-definitions.json", "documentation-declarations.json",
                          "ownership-exceptions.json", "input-manifest.json"],
              "tensorflow": ["source-registry.json", "typed-identity-relations.json",
                             "ambiguous-operator-exceptions.json", "operator-protocol-resolution.json",
                             "inputs/capabilities-provenance.json", "inputs/capabilities-9f4645b2.json"]}
    for framework in ["numpy", "jax", "pytorch", "tensorflow"]:
        base = getattr(args, framework).resolve()
        audit = args.tensorflow_correction.resolve() if framework == "tensorflow" and args.tensorflow_correction else base
        document, receipt = source_document(audit, framework)
        expected = baselines[framework]
        if audit != base:
            parent = audit / "inputs/before-classified-declarations-compact.json"
            parent_hash = sha(parent.read_bytes())
            need(document["input"]["sha256"] == parent_hash, "correction parent input hash drift")
            expected = input_parent(expected, read_json(parent), parent_hash)
            receipt["input_parent"] = "reference/public-scope/tensorflow/correction/baseline-classifications.json"
        audit_identity(framework, document, expected)
        family_document, family_key = contract_document(audit, framework, document)
        relative = "reference/public-scope/" + framework + "/"
        family_path, record_path = relative + "contracts.json", relative + "records.json"
        write(root / family_path, family_document)
        captured_paths.append(root / family_path)
        contracts.extend(family_rows(framework, family_document, family_key, family_path, caps, repos))
        need(not {"capture_receipt", "duplicate_original_record", "restore_original_record"} & set(document),
             "source document collides with capture metadata")
        original_rows = document.pop("records")
        normalized_rows = []
        framework_refs = {identity: row for identity, row in refs.items() if row["framework"] == framework}
        by_symbol_kind = {}
        for identity, ref in framework_refs.items():
            by_symbol_kind.setdefault((ref["symbol"], ref["kind"]), []).append(identity)
        tf_input = read_json(root / "reference/tensorflow.json")["records"] if framework == "tensorflow" else []
        for index, row in enumerate(original_rows):
            need(not {"reference_id", "reference_sha256"} & set(row), "source record collides with capture identity")
            original = row.pop("original_record", None)
            if original is not None:
                identity = api_identity(framework, original["version"], original)
            elif framework == "tensorflow":
                original = tf_input[row["input_index"]]
                need(original["symbol"] == row["symbol"] and original["kind"] == row["kind"], "TF declaration mismatch")
                identity = api_identity(framework, baselines["tensorflow"]["version"], original)
            else:
                candidates = by_symbol_kind[(row["symbol"], row["kind"])]
                need(len(candidates) == 1, "Torch source identity is ambiguous")
                identity = candidates[0]
            need(identity in framework_refs, f"unadmitted source identity: {identity}")
            if original is not None:
                expected = framework_refs[identity]
                need({**original, "framework": framework, "version": expected["version"]} == expected,
                     f"changed original reference payload: {identity}")
            row["reference_id"] = identity
            row["reference_sha256"] = sha(canonical(framework_refs[identity]).encode())
            normalized_rows.append(row)
            visibility, role, family, signature = classify(framework, row)
            bindings.append({"reference_id": identity, "visibility": visibility, "identity_role": role,
                             "contract": framework + ":" + family, "retained_obligation": True,
                             "signature_status": signature, "source_artifact": record_path, "source_row": index})
        encoded = pack(normalized_rows, {**document, "capture_receipt": receipt,
                       "restore_original_record": framework in {"numpy", "jax"},
                       "duplicate_original_record": "Rehydrate from immutable reference_id; reference_sha256 binds full canonical record"})
        need(unpack(encoded) == normalized_rows, "record-table roundtrip differs")
        write(root / record_path, encoded, compact=True)
        captured_paths.append(root / record_path)
        extra_receipts = []
        names = list(extras[framework])
        if framework == "pytorch":
            correction_names = ["routing-correction.json", "correction-history.json", "prose-extraction-gap-annex.json"]
            if any((base / name).exists() for name in correction_names):
                need(all((base / name).is_file() for name in correction_names), "partial Torch correction handoff")
                names.extend(correction_names)
        for name in names:
            source, destination = base / name, root / relative / name
            need(source.is_file(), f"missing selected source evidence: {source}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            captured_paths.append(destination)
            extra_receipts.append({"name": name, "sha256": sha(source.read_bytes()), "bytes": source.stat().st_size})
        if audit != base:
            manifest = read_json(audit / "manifest.json")
            baseline_hash = sha((base / "manifest.json").read_bytes())
            need(manifest["frozen_handoffs"]["scope"]["sha256"] == baseline_hash,
                 "TF correction does not preserve the selected baseline handoff")
            correction_names = ["manifest.json", "correction-history.json", "source-verified-application-routes.json",
                                "ownership-exceptions.json", "independent-test-specifications.json",
                                "assertion-results.json", "baseline-routing-provenance.json"]
            for name in correction_names:
                source, destination = audit / name, root / relative / "correction" / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                captured_paths.append(destination)
                extra_receipts.append({"name": "correction/" + name, "sha256": sha(source.read_bytes()),
                                       "bytes": source.stat().st_size})
            destination = root / receipt["input_parent"]
            shutil.copyfile(audit / "inputs/before-classified-declarations-compact.json", destination)
            captured_paths.append(destination)
            receipt["preserved_baseline_handoff_sha256"] = baseline_hash
        receipt["additional_evidence"] = extra_receipts
        receipts.append({"framework": framework, **receipt, "retained_records": len(normalized_rows)})
    write(target / "contracts.json", contracts)
    write(target / "bindings.json", pack(bindings), compact=True)
    captured_paths.extend([target / "contracts.json", target / "bindings.json"])
    # Source component reviews are external to the generation step. Retain their
    # committed receipt bytes, without calling them an exact Atlas-head review.
    captured_paths.extend(sorted((target / "source-review").glob("*.json")))
    by_contract = {row["id"]: row for row in contracts}
    unresolved = sum(by_contract[row["contract"]]["route_state"] == "ownership_unresolved" for row in bindings)
    counts = {"retained_raw_candidates": len(bindings), "visibility": dict(Counter(row["visibility"] for row in bindings)),
              "reusable_framework_contracts": len(contracts), "planned_family_routes": len(bindings) - unresolved,
              "ownership_unresolved_candidates": unresolved, "implementation_owners_verified": 0,
              "new_semantic_closures": 0, "execution_credit": 0, "raw_candidates_removed": 0,
              "full_public_surface_complete": False}
    artifacts = [{"path": path.relative_to(root).as_posix(), "sha256": sha(path.read_bytes()),
                  "role": ("Independent source/proposal correction review; not exact Atlas candidate or runtime qualification"
                           if path.parent.name == "source-review" else
                           "source routing proposal; not semantic or runtime evidence")}
                 for path in sorted(captured_paths)]
    write(target / "index.json", {"schema_version": 1, "artifacts": artifacts,
          "bindings": "reference/public-scope/bindings.json", "contracts": "reference/public-scope/contracts.json",
          "full_public_surface_complete": False, "semantic_definition_complete": False,
          "execution_credit": 0, "counts": counts, "capture_receipts": receipts})
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
