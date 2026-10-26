"""Reconcile bounded source findings without removing or qualifying APIs."""

from collections import Counter

from atlas_parity_schema import need


def validate_ufunc(get, baselines):
    bound = get("numpy-ufunc/bounded-completeness.json")
    objects = get("numpy-ufunc/ufunc-objects.json")
    members = get("numpy-ufunc/ufunc-members.json")
    bindings = get("numpy-ufunc/ufunc-bindings.json")
    expansion = get("numpy-ufunc/ufunc-expansions.json")
    docs = get("numpy-ufunc/documentation-dispositions.json")
    for document in [bound, objects, members, bindings, expansion, docs]:
        need(document["version"] == baselines["numpy"]["version"] and
             document["revision"] == baselines["numpy"]["source_revision"], "NumPy ufunc baseline drift")
        need(not document["full_numpy_surface_complete"] and not document["implementation_or_runtime_evidence"] and
             document["capabilities_verified"] == 0, "NumPy declaration expansion cannot qualify parity")
    old = get("numpy/static-candidates.json")["generated_ufunc_candidates"]
    preserved = objects["original_input_dispositions"]
    need(preserved["all_retained"] and preserved["semantic_merges"] == 0 and
         len(preserved["original_rows_retained"]) == len(old) == 133 and
         {row["original_symbol"]: row["original_record"] for row in preserved["original_rows_retained"]} ==
         {row["symbol"]: row for row in old}, "NumPy original ufunc row lost, changed or merged")
    object_ids = {row["object_id"] for row in objects["objects"]}
    member_ids = {row["member_id"] for row in members["members"]}
    public = {row["binding_id"]: row for row in bindings["bindings"] if row["public_namespace_export"]}
    need(len(objects["objects"]) == len(object_ids) == 130 and
         len(members["members"]) == len(member_ids) == 22 and len(public) == 123 and
         len(bindings["bindings"]) == 642, "NumPy ufunc source-bound count drift")
    rows = expansion["object_member_expansions"]
    expected = {(obj, member) for obj in object_ids for member in member_ids}
    by_id = {row["expansion_id"]: row for row in rows}
    need(len(rows) == len(by_id) == len(expected) == 2860 and
         {(row["object_id"], row["member_id"]) for row in rows} == expected and
         all(not row["semantic_merge"] for row in rows), "NumPy object/member cross-product lost or merged")
    spellings = expansion["public_spelling_member_expansions"]
    need(len(spellings) == len({row["binding_expansion_id"] for row in spellings}) == 2706 and
         {(row["binding_id"], by_id[row["object_expansion_id"]]["member_id"]) for row in spellings} ==
         {(binding, member) for binding in public for member in member_ids}, "NumPy public spelling/member expansion lost")
    for row in spellings:
        target = by_id[row["object_expansion_id"]]
        binding = public[row["binding_id"]]
        need(target["object_id"] == binding["object_id"] and row["symbol"] == binding["symbol"] + "." + target["member"] and
             row["alias_relation_not_semantic_merge"], "NumPy alias spelling/workflow identity lost")
    need({row["symbol"] for row in docs["public_bindings"]} == {row["symbol"] for row in public.values()} and
         all(not row["semantic_equivalence_or_verification"] for row in docs["public_bindings"]),
         "NumPy public binding documentation/alias distinction lost")
    need(len(docs["exact_reference_page_autosummary_dispositions"]) == 104 and
         not docs["frozen_full_rendered_public_scope_complete"] and
         {"_resolve_dtypes_and_context", "_get_strided_loop"} <= {row["member"] for row in members["members"]},
         "NumPy documented native members cannot disappear for an underscore")
    need(all(not any(row["verification"].values()) for row in expansion["workflow_templates"].values()),
         "NumPy workflow proposals cannot earn executed qualification")
    return {"generated_objects": 130, "retained_original_rows": 133, "member_candidates": 22,
            "public_spellings": 123, "object_member_rows": 2860, "spelling_member_rows": 2706,
            "added_api_denominator": 0, "semantic_closures": 0, "runtime_verification": False}


def validate_dispositions(get, baselines: dict) -> dict:
    numpy = validate_ufunc(get, baselines)
    jax = get("jax-selection/selection-dispositions.json")
    original = get("jax/review-ready-additions.json")["records"]
    need(jax["version"] == baselines["jax"]["version"] and
         jax["source_revision"] == baselines["jax"]["source_revision"], "JAX selector baseline drift")
    rows = jax["rows"]
    expected = {row["symbol"]: row for row in original}
    retained = {row["symbol"]: row["original_candidate_preserved"] for row in rows}
    need(len(rows) == len(retained) == jax["original_candidate_count"] == 22 and retained == expected,
         "JAX selector candidate was dropped, changed or duplicated")
    need(dict(Counter(row["selection_state"] for row in rows)) == jax["counts"], "JAX selector count drift")
    need(not jax["semantic_api_closures"] and not jax["configured_tooling"]["rendered_output_verified"] and
         all(not row["rendered_output_verified"] and row["public_scope_action"].startswith("retain original candidate")
             for row in rows), "JAX selection cannot imply rendered proof, exclusion or semantic closure")
    tooling = get("jax-selection/tooling-sources.json")
    need(len(tooling["sources"]) == 74 and len(jax["jax_sources"]) == 8,
         "JAX selector source coverage drift")
    access = get("jax-selection/versioned-docs-access.json")
    need(len(access) == 3 and all(row["status"] == 403 for row in access),
         "Captured JAX rendered-output access evidence changed")

    torch = get("torch-new-tensor/contract.json")
    cases = get("torch-new-tensor/acceptance-cases.json")
    need(torch["version"] == baselines["pytorch"]["version"] and
         torch["revision"] == baselines["pytorch"]["source_revision"], "Torch new_tensor baseline drift")
    signature = torch["builtin_signature"]
    need(signature["accepted_parameter_names"] == ["data", "dtype", "device", "requires_grad"] and
         {"layout", "pin_memory"} <= set(signature["rejected_builtin_keywords"]),
         "Torch new_tensor documented/parser discrepancy lost")
    need(not signature["universal_copy_proven"] and not signature["universal_strided_proven"] and
         {row["id"] for row in torch["contradictions"]} ==
         {"TORCH-NEW-TENSOR-KWARGS", "TORCH-NEW-TENSOR-COPY", "TORCH-NEW-TENSOR-LAYOUT"},
         "Torch new_tensor copy/layout or signature contradiction lost")
    need(not torch["public_api_mapping_complete"] and torch["runtime_verification"] == "not_run" and
         cases["case_count"] == len(cases["cases"]) == 26 and cases["runtime_tests_executed"] == 0 and
         all(row["status"] in {"source_derived_unrun", "boundary_behavior_unrun", "source_counterexample_candidate_unrun"}
             and row["execution_credit"] == "none; proposed acceptance case, no runtime test executed"
             for row in cases["cases"]),
         "Torch source cases cannot earn whole-API/runtime qualification")

    saving = get("keras-saving/saving-endpoint-resolution.json")
    previous = get("tf/keras-reachable-exports.json")["initial_symbols_not_reached"]
    rows = saving["endpoints"]
    need(saving["keras_version"] == "3.15.1" and saving["revision"] == "250b42181ce9f37df68319d8f4753ec89a349a43",
         "Selected Keras companion baseline drift")
    need(len(rows) == len({row["symbol"] for row in rows}) == 14 and
         {row["symbol"] for row in rows} == set(previous) and saving["no_names_dropped"],
         "Keras saving candidate was dropped, changed or duplicated")
    need(len({row["target"] for row in rows if "target" in row}) == 12 and
         saving["counts"] == {"retained_endpoints": 14, "module": 1, "export_names": 13,
                              "distinct_definition_targets": 12}, "Keras saving relation count drift")
    need(all(not row["semantic_equivalence_asserted"] and not row["reference_runtime_verified"] for row in rows) and
         not saving["public_workflow_status"]["actual_runtime_importability_qualified"],
         "Keras packaged exports cannot imply semantic/runtime equivalence")
    modules = get("keras-saving/packaged-module-exports.json")
    need(modules["ordinary_keras_root_reexports_saving"] and not modules["tf_keras_root_reexports_saving"] and
         modules["saving_modules_identical"], "Keras root-lookup/submodule-import distinction lost")
    record = get("keras-saving/record-verification.json")
    source = get("keras-saving/git-source-verification.json")
    need(record["entries"] == len(record["files"]) == 909 and record["verified_hashed_entries"] == 908 and
         source["python_blobs_verified"] == len(source["files"]) == 904, "Keras package source proof count drift")
    acceptance = get("keras-saving/saving-acceptance-specifications.json")
    need(acceptance["counts"] == {"specified": 10, "executed": 0} and len(acceptance["tests"]) == 10 and
         all(row["status"] == "specified_not_executed" for row in acceptance["tests"]),
         "Keras source proposals cannot earn executed-test credit")
    return {"numpy_ufunc_declaration_bound": numpy,
            "jax_retained_selector_classes": jax["counts"], "jax_rendered_output_verified": False,
            "torch_new_tensor_contradictions": len(torch["contradictions"]),
            "torch_new_tensor_unrun_acceptance_cases": len(cases["cases"]),
            "keras_saving_retained_names": len(rows), "keras_saving_source_targets": 12,
            "keras_saving_unrun_acceptance_cases": len(acceptance["tests"]),
            "semantic_closures": 0, "execution_qualification": False}
