"""Validate bounded core tensor contracts and preserve every open obligation."""

import hashlib
from pathlib import Path

from atlas_parity_core_math import FIXTURES, negative_fixture_checks, verify_fixtures
from atlas_parity_core_sources import (validate_numpy_jax, validate_provider_boundaries,
                                       validate_torch_tf)
from atlas_parity_schema import (ParityError, api_identity, dag, digest, fields, finite_number, local_path, need,
                                 nonempty, read_json, unique)

NO_CREDIT = {"source_contract_defined": False, "framework_execution_credit": 0,
             "provider_execution_credit": 0, "performance_credit": 0, "release_credit": 0,
             "whole_public_surface_complete": False}
LAWS = {"CT-SHAPE", "CT-PROMOTION", "CT-CAST", "CT-BROADCAST", "CT-AFFINE-VIEW",
        "CT-RESHAPE", "CT-INDEX", "CT-EFFECTS", "CT-AD-BOUNDARY"}


def no_credit(row):
    need(type(row) is dict and set(row) == set(NO_CREDIT) and all(
        type(row[key]) is type(value) and row[key] == value for key, value in NO_CREDIT.items()),
        "core tensor design cannot assert whole API, execution or release qualification")


def entry_at(document, path):
    try:
        for key in path:
            document = document[key]
    except (KeyError, TypeError, IndexError) as error:
        raise ParityError("core tensor original entry absent") from error
    return document


def validate_core_tensor(root: Path, relative: str, program, capabilities, repositories,
                         references, mappings, assigned, program_packages):
    index_path = local_path(root, relative)
    index = read_json(index_path)
    fields(index, {"schema_version": int, "artifacts": list, "status": dict,
                   "research_captures": list}, "core tensor index")
    need(index["schema_version"] == 1, "unsupported core tensor schema")
    need(index["source_review_covers_original_blobs_required"] is True and
         index["public_reference_denominator_changed"] is False, "core source review/denominator policy drift")
    no_credit(index["status"])
    paths, documents = [index_path], {}
    for path, row in unique(index["artifacts"], "path", "core tensor artifact").items():
        digest(row.get("sha256"), path)
        file = local_path(root, path)
        need(hashlib.sha256(file.read_bytes()).hexdigest() == row["sha256"], "core tensor artifact hash drift")
        paths.append(file)
        documents[path] = read_json(file)

    def get(name):
        key = "core-tensor/" + name + ".json"
        need(key in documents, f"core tensor artifact missing: {name}")
        return documents[key]

    need(set(index["research_captures"]) == {"core-tensor/numpy-jax/capture.json",
         "core-tensor/torch-tf/capture.json"} and len(index["research_captures"]) == 2,
         "core research capture set drift")
    for capture_path in index["research_captures"]:
        need(capture_path in documents, "core research capture missing")
        capture = documents[capture_path]
        manifest_path = capture_path.rsplit("/", 1)[0] + "/manifest.json"
        need(manifest_path in documents and hashlib.sha256((root / manifest_path).read_bytes()).hexdigest() ==
             capture["manifest_sha256"], "core research manifest changed")
        manifest = documents[manifest_path]
        captured_files = manifest["files"]
        if isinstance(captured_files, list):
            captured_files = unique(captured_files, "file", "core original capture file")
        need(capture["source_packet_files"] == len(captured_files) and
             capture["capture_complete_for_selected_files"] is True and
             capture["full_source_files_vendored"] is False, "core research capture scope drift")
        admitted_paths, original_paths = set(), set()
        prefix = capture_path.rsplit("/", 1)[0] + "/"
        for row in capture["captured"]:
            fields(row, {"path": str, "original_path": str, "sha256": str}, "core captured artifact")
            need(row["path"] == prefix + row["original_path"] and row["original_path"] not in original_paths,
                 "core captured source role/path association drift")
            original_paths.add(row["original_path"])
            file = local_path(root, row["path"])
            paths.append(file)
            need(row["path"] not in admitted_paths, "core research duplicate captured path")
            admitted_paths.add(row["path"])
            need(hashlib.sha256(file.read_bytes()).hexdigest() == row["sha256"], "core research capture drift")
            if row["original_path"] == "manifest.json":
                need(row["path"] == manifest_path and row["sha256"] == capture["manifest_sha256"],
                     "core original manifest role was reassigned")
            else:
                need(row["original_path"] in captured_files and
                     captured_files[row["original_path"]]["sha256"] == row["sha256"],
                     "core captured artifact differs from original source packet")
        need(manifest_path in admitted_paths, "core captured manifest role absent")
        need({path for path in documents if path.startswith(prefix)} - {capture_path} <= admitted_paths,
             "core tensor source artifact not bound to original capture")

    baselines = {}
    for snapshot in program["reference_snapshots"]:
        document = read_json(local_path(root, snapshot["path"]))
        baselines[snapshot["framework"]] = {"version": snapshot["version"], "revision": document["source_revision"]}
    numpy_citations = validate_numpy_jax(get("numpy-jax/source-receipts"),
                                         get("numpy-jax/source-witnesses"), baselines)
    other_citations = validate_torch_tf(get("torch-tf/line-witnesses"),
                                       get("torch-tf/source-provenance-registry"), baselines)
    provider_contracts = validate_provider_boundaries(get("core-tensor-boundaries"),
        get("provider-source-witnesses"), capabilities, repositories)
    audit_files = unique(get("audit-manifest")["records"], "file", "core provider audit capture")
    for name in ["gamma-source-audit.json", "core-tensor-boundaries.json"]:
        need(name in audit_files and hashlib.sha256((root / "core-tensor" / name).read_bytes()).hexdigest() ==
             audit_files[name]["sha256"], "core provider original audit capture changed")
    gamma = get("gamma-source-audit")
    need(gamma["gamma_integrated_into_defaults_claimed"] is False and
         gamma["delivery_state"]["release_or_remote_delivery_qualified"] is False and bool(gamma["open_gates"]),
         "core gamma local receipt cannot claim default integration or release")
    gamma_candidates = unique(gamma["candidate_cohort"], "repo", "gamma candidate")
    need(set(gamma_candidates) == {"eunomia", "leto", "coeus"}, "core gamma candidate cohort drift")
    for repo, row in gamma_candidates.items():
        need(row["base"] == repositories[repo]["candidate_revision"] and
             row["head"] != row["base"] and row["clean"] is True,
             "core gamma candidate confused with selected default cohort")
    for lane in ["numpy-jax", "torch-tf"]:
        source_review = get("independent-review/" + lane + "-core-final-review")
        need(source_review["result"] == "accept_bounded_source_definition_only" and
             source_review["blocking_findings"] == [] and source_review["reviewed_manifest_sha256"] ==
             get(lane + "/capture")["manifest_sha256"], f"core {lane} source review is stale or blocked")

    fixtures = get("analytical-fixtures")
    fields(fixtures, {"framework_execution_credit": int, "provider_execution_credit": int,
                      "fixtures": list}, "core tensor fixtures")
    need(fixtures["framework_execution_credit"] == fixtures["provider_execution_credit"] == 0,
         "coordinate fixture cannot grant framework or provider execution credit")
    verified = verify_fixtures(fixtures["fixtures"])
    negatives = negative_fixture_checks(fixtures["fixtures"])
    model = get("model")
    no_credit(model["status"])
    clauses = unique(model["clauses"], "id", "core tensor law")
    need(set(clauses) == LAWS, "core tensor required law inventory drift")
    linked_fixtures = set()
    for identity, row in clauses.items():
        need(row["capability"] in capabilities and row["owner"] == capabilities[row["capability"]]["owner"],
             "core tensor law owner drift")
        no_credit(row["status"])
        nonempty(row["law"], identity)
        need(bool(row["unclosed_obligations"]) and bool(row["analytical_fixture_ids"]) and
             set(row["analytical_fixture_ids"]) <= set(FIXTURES), "core tensor law fixture/gap drift")
        linked_fixtures.update(row["analytical_fixture_ids"])
    need(linked_fixtures == set(FIXTURES), "core tensor unbound analytical fixture")

    need(get("contracts")["whole_api_semantic_closure"] is False and get("cases")["all_cases_unrun"] is True,
         "core tensor header contradicts bounded unrun definitions")
    contracts = unique(get("contracts")["contracts"], "id", "core tensor endpoint")
    endpoint_refs, endpoint_sources, source_ids = set(), set(), {}
    for identity, row in contracts.items():
        no_credit(row["status"])
        fields(row, {"reference_id": str, "endpoints": list, "mapping_id": str, "owner": str,
                     "capability": str, "source_endpoint": dict, "clause_ids": list,
                     "unclosed_obligations": list, "case_ids": list}, identity)
        ref = row["reference_id"]
        need(ref in references and ref not in endpoint_refs and row["endpoints"] == [references[ref]["symbol"]],
             "core tensor: duplicate, invented or mismatched API identity")
        endpoint_refs.add(ref)
        need(assigned.get(ref) == row["mapping_id"] and row["mapping_id"] in mappings,
             "core tensor endpoint has no canonical mapping")
        mapping = mappings[row["mapping_id"]]
        need(row["capability"] == mapping["capability"] and row["owner"] == mapping["owner"] and
             bool(row["clause_ids"]) and set(row["clause_ids"]) <= clauses.keys() and
             bool(row["unclosed_obligations"]) and bool(row["case_ids"]), "core tensor contract joins incomplete")
        if mapping["source_contract"]["path"] == "core-tensor/contracts.json":
            variant = next(item for item in mapping["variants"] if item["reference_id"] == ref)
            need(variant["analytical_tests"] == row["case_ids"], "core canonical mapping case links drift")
        source = row["source_endpoint"]
        need(source["path"] in documents, "core tensor: original source endpoint missing")
        original = entry_at(documents[source["path"]], source["entry"])
        endpoint_sources.add((source["path"], tuple(source["entry"])))
        if references[ref]["framework"] in {"numpy", "jax"}:
            source_record, citations = original["identity"]["record"], original["citations"]
            need(original["identity"]["reference_id"] == ref and set(citations) <= numpy_citations,
                 "core tensor NumPy/JAX identity/citation drift")
            need(original["semantic_completion_credit"] is False and original["status"]["runtime_credit"] is False and
                 all(original["status"][key] == "unrun" for key in ["tested", "external", "performance"]),
                 "core tensor NumPy/JAX source asserts unsupported qualification")
            source_ids[ref] = original["id"]
            semantics, gaps = original["semantics"], original["remaining_whole_api_gaps"]
            proposed_capability = original["owner"]["capability"]
        else:
            source_record, citations = original["admitted_record"], original["line_witness_refs"]
            need(original["api_identity"] == ref and set(citations) <= other_citations,
                 "core tensor Torch/TF identity/citation drift")
            need(all(original[key] is False for key in ["fully_specified", "released", "semantic_equivalence_asserted",
                 "unsupported_capability_exclusion"]) and all(original[key] == "unrun" for key in
                 ["tested", "externally_verified", "performance_qualified"]), "core tensor Torch/TF false qualification")
            source_ids[ref] = original["contract_id"]
            semantics = [item["clause"] for item in original["partial_clauses"]]
            gaps = original["native_order_or_binding_gaps"] + original["remaining_variants"]
            proposed_capability = original["planned_framework_capability"]
        need(row["semantics"] == semantics and row["unclosed_obligations"] == gaps,
             "core tensor source semantics/remaining branches changed")
        if row["capability"] != proposed_capability:
            need(row["endpoints"] == ["tf.Variable.assign"] and proposed_capability == "TEN-CORE" and
                 row["capability"] == "TEN-RESOURCE", "core tensor unexplained source ownership normalization")
        need(api_identity(references[ref]["framework"], references[ref]["version"], source_record) == ref,
             "core tensor source declaration identity changed")
    expected = {(f"core-tensor/numpy-jax/contracts/{framework}.json", ("endpoints", i))
                for framework in ["numpy", "jax"] for i in range(len(get(f"numpy-jax/contracts/{framework}")["endpoints"]))}
    expected.update(("core-tensor/torch-tf/contracts.json", ("records", i))
                    for i in range(len(get("torch-tf/contracts")["records"])))
    need(endpoint_sources == expected and len(contracts) == len(expected), "core tensor source endpoints lost or duplicated")

    cases = unique(get("cases")["cases"], "id", "core tensor case")
    case_ids = set()
    for row in contracts.values():
        for identity in row["case_ids"]:
            need(identity in cases and cases[identity]["reference_id"] == row["reference_id"],
                 "core tensor case belongs to another endpoint")
            case_ids.add(identity)
    need(case_ids == cases.keys(), "core tensor unbound source-only case")
    for row in cases.values():
        need(row["status"] == "unrun" and row["provider_evidence"] is None and row["reference_evidence"] is None,
             "core tensor scenario has unsupported runtime evidence")
        source = row["source_case"]
        need(source["path"] in documents and row["original"] ==
             entry_at(documents[source["path"]], source["entry"]), "core tensor source case changed")
        need(source_ids.get(row["reference_id"]) == row["source_endpoint_id"],
             "core tensor case source endpoint mismatches canonical API")
        original = row["original"]
        if "endpoint" in original:
            need(original["endpoint"] == row["source_endpoint_id"] and
                 original["reference_id"] == row["reference_id"] and original["status"] == "unrun" and
                 original["provider_evidence"] is None and original["reference_evidence"] is None,
                 "core tensor NumPy/JAX case source identity/evidence drift")
        else:
            need(row["source_endpoint_id"] in original["contract_refs"] and
                 original["status"] == "specified-not-run" and original["framework_execution"] is False,
                 "core tensor Torch/TF case source identity/evidence drift")
    case_document = get("cases")
    source_programs = {(row["source_case"]["path"], tuple(row["source_case"]["entry"])) for row in cases.values()}
    need(case_document["distinct_source_programs"] == len(source_programs) and
         case_document["api_target_views"] == len(cases), "core tensor case/program counts inflated")
    by_source_id = {source_id: ref for ref, source_id in source_ids.items()}
    need(len(by_source_id) == len(contracts), "core source endpoint IDs are not unique")
    expected_case_views = set()
    for name, key in [("numpy-jax/acceptance-cases", "source_only_cases"), ("torch-tf/analytical-cases", "cases")]:
        for case_index, source in enumerate(get(name)[key]):
            targets = [source["endpoint"]] if key == "source_only_cases" else source["contract_refs"]
            for target in targets:
                need(target in by_source_id, "core original case target has no endpoint contract")
                expected_case_views.add(("core-tensor/" + name + ".json", (key, case_index), by_source_id[target]))
    actual_case_views = {(row["source_case"]["path"], tuple(row["source_case"]["entry"]), row["reference_id"])
                         for row in cases.values()}
    need(actual_case_views == expected_case_views and len(cases) == len(expected_case_views),
         "core captured source case views lost or duplicated")
    package_document = get("implementation-program")
    need(package_document["remaining_full_scope_not_reduced"] is True and
         package_document["full_program_replacement"] is False, "core bounded package cannot reduce or replace full scope")
    packages = unique(package_document["packages"], "id", "core tensor work package")
    parents = {"WP-003", "WP-005", "WP-009", "WP-019", "WP-020"}
    need(set(index["parent_work_packages"]) == parents and len(index["parent_work_packages"]) == len(parents) and
         len(packages) == len(parents) and {row["parent_work_package"] for row in packages.values()} == parents,
         "core acceptance package ownership roles lost or duplicated")
    dag(packages, "dependencies", "core tensor work package")
    for row in packages.values():
        need(row["owner"] in repositories and row["parent_work_package"] in index["parent_work_packages"] and
             row["parent_work_package"] in program_packages and
             row["owner"] == program_packages[row["parent_work_package"]]["owner"] and
             row["done_is_whole_framework_parity"] is False and
             row["state"] == "planned_acceptance_defined_not_started", "core tensor package owner/state drift")
        need(bool(row["acceptance"]) and bool(row["remaining_readiness_blockers"]) and
             bool(row["clause_ids"]) and set(row["clause_ids"]) <= clauses.keys(), "core package obligations missing")
        estimate = row["estimate"]
        need(finite_number(estimate["engineer_weeks_low"]) and finite_number(estimate["engineer_weeks_high"]) and
             0 < estimate["engineer_weeks_low"] <= estimate["engineer_weeks_high"] and
             estimate["confidence"] in {"low", "medium", "high"}, "core tensor package estimate invalid")
    def path_cost(identity, bound):
        package = packages[identity]
        return package["estimate"][bound] + max((path_cost(parent, bound) for parent in package["dependencies"]), default=0)
    estimated_range = [max(path_cost(identity, bound) for identity in packages)
                       for bound in ["engineer_weeks_low", "engineer_weeks_high"]]
    need(package_document["estimate_non_calendar_engineer_weeks_range"] == estimated_range,
         "core package aggregate estimate contradicts dependency path")
    critical = package_document["critical_path"]
    need(type(critical) is list and bool(critical) and all(identity in packages for identity in critical) and
         all(before in packages[after]["dependencies"] for before, after in zip(critical, critical[1:])) and
         sum(packages[identity]["estimate"]["engineer_weeks_high"] for identity in critical) == estimated_range[1],
         "core critical path does not attain the declared upper estimate")
    return {"partial_source_endpoints": len(contracts), "unrun_acceptance_cases": len(cases),
            "distinct_unrun_source_programs": len(source_programs),
            "reusable_laws": len(clauses), "analytical_witnesses": verified,
            "wrong_value_probes_rejected": len(negatives), "provider_boundary_contracts": len(provider_contracts),
            "framework_execution_credit": 0, "whole_api_closure_credit": 0}, paths
