"""Validate source-closure evidence without treating names or aliases as parity."""

from collections import Counter
import hashlib
from pathlib import Path

from atlas_parity_schema import digest, fields, local_path, need, read_json, unique
from atlas_parity_dispositions import validate_dispositions


def gap_key(row: dict) -> tuple:
    return tuple(row.get(key) for key in ("path", "line", "directive", "argument", "reason"))


def validate_closure(root: Path, relative: str, program: dict) -> tuple[dict, list[Path]]:
    path = local_path(root, relative)
    index = read_json(path)
    fields(index, {"schema_version": int, "baselines": dict, "artifacts": list,
                   "public_surface_complete": bool, "semantic_mapping_complete": bool,
                   "execution_verification": bool}, "source closure")
    need(index["schema_version"] == 1, "unsupported source-closure schema")
    need(not any(index[key] for key in ("public_surface_complete", "semantic_mapping_complete",
                                       "execution_verification")),
         "source audits cannot declare whole surface/semantic/runtime qualification")
    inputs, raw = [path], {}
    for snapshot in program["reference_snapshots"]:
        data = read_json(local_path(root, snapshot["path"]))
        expected = {"version": snapshot["version"], "source_revision": data["source_revision"],
                    "inventory_sha256": snapshot["sha256"]}
        need(index["baselines"].get(snapshot["framework"]) == expected,
             f"{snapshot['framework']}: closure advances or changes frozen baseline")
        raw[snapshot["framework"]] = data
    artifacts = unique(index["artifacts"], "path", "closure artifact")
    data_by_path = {}
    for identity, row in artifacts.items():
        fields(row, {"sha256": str, "framework": str, "role": str, "public_surface_complete": bool}, identity)
        need(not row["public_surface_complete"], f"{identity}: bounded audit is not full public surface")
        digest(row["sha256"], identity)
        artifact = local_path(root, identity)
        need(hashlib.sha256(artifact.read_bytes()).hexdigest() == row["sha256"],
             f"{identity}: source-closure artifact hash drift")
        inputs.append(artifact)
        data_by_path[identity] = read_json(artifact)

    def get(name: str) -> dict:
        key = "reference/closure/" + name
        need(key in data_by_path, f"required source audit missing: {name}")
        return data_by_path[key]

    numpy = get("numpy/gap-dispositions.json")
    jax = get("jax/autodoc-dispositions.json")
    for framework, audit, key in (("numpy", numpy, "original"), ("jax", jax, "old_gap")):
        original = [gap_key(row) for row in raw[framework]["extraction_gaps"]]
        disposition = [gap_key(row[key]) for row in audit["dispositions"]]
        need(len(disposition) == len(set(disposition)) and set(disposition) == set(original),
             f"{framework}: missing, duplicate or changed original gap disposition")
    need(numpy["baseline_inventory_sha256"] == index["baselines"]["numpy"]["inventory_sha256"],
         "NumPy disposition basis drift")
    need(jax["input_inventory_sha256"] == index["baselines"]["jax"]["inventory_sha256"],
         "JAX disposition basis drift")
    need(numpy["counts"] == dict(Counter(row["disposition"] for row in numpy["dispositions"])),
         "NumPy disposition count drift")
    need(jax["states"] == dict(Counter(row["state"] for row in jax["dispositions"])),
         "JAX disposition count drift")
    need(all(row["capabilities_verified"] == 0 for row in numpy["dispositions"]),
         "source expansion is not verified functional capability")

    torch = get("torch/source-supplement.json")
    counts = get("torch/closure-summary.json")["counts"]
    torch_counts = {"source_docstrings": "docstring_targets_total", "generated_candidates": "finite_foreach_generated_candidates",
                    "documented_aliases": "explicit_docstring_alias_relations", "operator_schemas": "native_schema_overloads",
                    "missing_inventory_targets": "docstring_targets_absent_from_inventory", "cpp_inputs": "cpp_doxygen_inputs",
                    "namespace_export_aliases": "namespace_export_alias_relations"}
    for key, summary_key in torch_counts.items():
        need(len(torch[key]) == counts[summary_key], f"Torch {key}: count drift")
    need(all(not row["semantic_merge_authorized"] for row in torch["documented_aliases"]),
         "Torch source aliases cannot authorize semantic deduplication")

    tf = get("tf/declaration-relations.json")
    counts = tf["counts"]
    pairs = tf["v1_v2_spelling_candidates"]
    need(len(pairs) == counts["v1_v2_spelling_candidates"], "TF spelling relation count drift")
    need(dict(Counter(row["signatures"] for row in pairs)) == counts["spelling_signature_classes"],
         "TF differing-signature distinctions lost")
    need(all(not row["semantic_equivalence_asserted"] for row in pairs),
         "TF equal spelling/signatures cannot authorize semantic deduplication")
    views = tf["same_endpoint_declaration_views"]
    need(len(views) == counts["view_groups"], "TF declaration view count drift")
    declaration_ids = {hashlib.sha256("\0".join((row["symbol"], row["kind"], row["source"])).encode()).hexdigest()[:24]: row
                       for row in raw["tensorflow"]["records"]}
    for view in views:
        need(not view["semantic_equivalence_asserted"], "TF declaration views are not semantic equivalence")
        need(all(identity in declaration_ids and declaration_ids[identity]["symbol"] == view["symbol"]
                 for identity in view["declaration_ids"]), "TF relation references unknown or different endpoint")
    missing = get("tf/missing-export-candidates.json")
    need(dict(Counter(row["classification"] for row in missing["records"])) == missing["counts"],
         "TF missing-export candidate count drift")
    need(all(not row["excluded_from_goal"] for row in missing["records"]),
         "unsupported/generated export candidates cannot silently leave scope")
    summary = {"original_gaps_dispositioned": len(numpy["dispositions"]) + len(jax["dispositions"]),
               "numpy_gap_dispositions": numpy["counts"], "jax_gap_dispositions": jax["states"],
               "jax_requested_member_sets_pending_rendered_selection": 5,
               "torch_docstring_bindings": len(torch["source_docstrings"]),
               "torch_source_alias_relations": len(torch["documented_aliases"]) + len(torch["namespace_export_aliases"]),
               "tensorflow_spelling_candidates": len(pairs),
               "tensorflow_differing_signatures": counts["spelling_signature_classes"]["different_declared_signatures"],
               "tensorflow_missing_export_candidates": len(missing["records"]),
               "full_surface_complete": False, "semantic_equivalence_inferred": False}
    numpy_candidates = get("numpy/static-candidates.json")
    jax_namespaces = get("jax/namespace-audit.json")
    keras = get("tf/keras-inherited-members.json")
    summary["retained_source_candidate_tables_not_an_additive_api_denominator"] = {
        "numpy_inherited_members": len(numpy_candidates["inherited_array_scalar_candidates"]),
        "numpy_ufunc_and_alias_records": len(numpy_candidates["generated_ufunc_candidates"]),
        "jax_bindings_absent_from_base_documented_set": jax_namespaces["candidates_absent_from_documented_identity_set"],
        "torch_docstring_bindings_absent_from_base_inventory": len(torch["missing_inventory_targets"]),
        "torch_conditional_generated_names": len(torch["generated_candidates"]),
        "tensorflow_missing_exports": len(missing["records"]),
        "keras_inherited_and_direct_member_candidates": keras["counts"]["member_declarations"],
    }
    summary["bounded_source_dispositions"] = validate_dispositions(get, index["baselines"])
    return summary, inputs
