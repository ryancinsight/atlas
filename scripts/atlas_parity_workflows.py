"""Validate partial end-to-end designs without granting runtime parity credit."""

import hashlib
from pathlib import Path

from atlas_parity_schema import (ParityError, dag, digest, fields, https, local_path,
                                 need, read_json, revision, unique)
from atlas_parity_workflow_math import negative_fixture_checks, verify_fixture_truth

REPOSITORIES = {"numpy": "numpy/numpy", "jax": "jax-ml/jax", "pytorch": "pytorch/pytorch",
                "tensorflow": "tensorflow/tensorflow", "keras": "keras-team/keras"}


def instruction_policy(workflow, case):
    """Typed stages of the reviewed workflow recipe; no unbound stage may disappear."""
    result = ["construct", "compute"]
    for names, instructions in [({"WF03", "WF05", "WF06", "WF07", "WF19"}, ["differentiate"]),
                                ({"WF08", "WF10", "WF11", "WF13", "WF14", "WF23"}, ["train_step"]),
                                ({"WF12", "WF13", "WF23"}, ["collective"]),
                                ({"WF04", "WF09", "WF14", "WF22", "WF23", "WF24"}, ["persist", "load"])]:
        if workflow in names:
            result.extend(instructions)
    if workflow in {"WF15", "WF17", "WF18", "WF19", "WF24"}:
        result.extend(["export"] + ([] if case.get("source_rejected_route") else ["execute_target"]))
    if case["id"] == "WF21-AWQ":
        result.extend(["calibrate", "quantize_pack", "persist", "load", "execute_target"])
    return result + ["assert"] + (["measure"] if workflow == "WF20" else [])


def no_execution(document, context):
    fields(document, {"framework_cases_executed": int, "api_mapping_credit": int,
                      "public_surface_complete": bool, "semantic_mapping_complete": bool}, context)
    need(document["framework_cases_executed"] == document["api_mapping_credit"] == 0 and
         not document["public_surface_complete"] and not document["semantic_mapping_complete"],
         f"{context}: partial designs cannot assert execution or complete mappings")


def validate_workflows(root: Path, relative: str, program: dict, capabilities: dict,
                       repositories: dict) -> tuple[dict, list[Path]]:
    index_path = local_path(root, relative)
    index = read_json(index_path)
    fields(index, {"schema_version": int, "artifacts": list, "full_workflow_inventory_complete": bool,
                   "semantic_definition_complete": bool, "execution_credit": int}, "workflow index")
    need(index["schema_version"] == 1 and not index["full_workflow_inventory_complete"] and
         not index["semantic_definition_complete"] and index["execution_credit"] == 0,
         "workflow index: bounded designs cannot assert complete inventory or qualification")
    paths, documents = [index_path], {}
    for path, row in unique(index["artifacts"], "path", "workflow artifact").items():
        digest(row.get("sha256"), path)
        file = local_path(root, path)
        need(hashlib.sha256(file.read_bytes()).hexdigest() == row["sha256"], f"{path}: workflow artifact drift")
        paths.append(file)
        documents[path] = read_json(file)

    digest(index.get("source_handoff_manifest_sha256"), "captured workflow manifest")
    captured_path = "workflows/deliverable-manifest.json"
    need(captured_path in documents and
         hashlib.sha256((root / captured_path).read_bytes()).hexdigest() == index["source_handoff_manifest_sha256"],
         "workflow capture manifest missing or changed")
    captured = documents[captured_path]
    for row in captured["files"]:
        if not row["path"].endswith(".json"):
            continue
        path = "workflows/" + row["path"]
        need(path in documents and hashlib.sha256((root / path).read_bytes()).hexdigest() == row["sha256"],
             f"{path}: captured source artifact removed or changed")
    for name in ["final-review", "corrected-independent-checks", "corrected-replay"]:
        need("workflows/independent-review/" + name + ".json" in documents, "workflow capture review receipt missing")

    def get(name):
        path = "workflows/" + name + ".json"
        need(path in documents, f"missing workflow artifact: {name}")
        return documents[path]

    versions, revisions = {}, {}
    for snapshot in program["reference_snapshots"]:
        data = read_json(local_path(root, snapshot["path"]))
        versions[snapshot["framework"]], revisions[snapshot["framework"]] = snapshot["version"], data["source_revision"]
        for companion in data.get("supplemental_baselines", []):
            versions[companion["name"]], revisions[companion["name"]] = companion["version"], companion["source_revision"]
    manifest = get("source-manifest")
    sources = unique(manifest["sources"], "id", "workflow source")
    need(set(manifest["baselines"]) == set(revisions), "workflow source baseline set drift")
    for framework, baseline in manifest["baselines"].items():
        need(baseline["revision"] == revisions[framework] and baseline["repository"] == REPOSITORIES[framework],
             "workflow source revision/repository drift")
    for identity, source in sources.items():
        digest(source.get("sha256"), identity)
        revision(source.get("git_blob_sha"), identity)
        revision(source.get("revision"), identity)
        https(source.get("url"), identity)
        need(source["framework"] in revisions and source["revision"] == revisions[source["framework"]] and
             source["repository"] == REPOSITORIES[source["framework"]] and
             source["url"] == f"https://github.com/{source['repository']}/blob/{source['revision']}/{source['path']}" and
             source["source_executed"] is False, f"{identity}: wrong source identity or source-execution claim")
    citations = unique(get("source-citations")["citations"], "id", "workflow citation")
    witnesses = get("source-witnesses")
    need(witnesses["sources"].keys() == sources.keys() and witnesses["anchors"].keys() == citations.keys(),
         "workflow source/citation witness set changed")
    for identity, row in citations.items():
        need(row["source_id"] in sources, f"{identity}: missing source receipt")
        source = sources[row["source_id"]]
        measured = witnesses["sources"][row["source_id"]]
        anchor = witnesses["anchors"][identity]
        need(row["sha256"] == source["sha256"] and row["git_blob_sha"] == source["git_blob_sha"] and
             measured["source_sha256"] == source["sha256"] and measured["git_blob_sha"] == source["git_blob_sha"] and
             type(row["line_start"]) is int and type(row["line_end"]) is int and
             0 < row["line_start"] <= row["line_end"] <= measured["lines"] and
             anchor["source_id"] == row["source_id"] and anchor["line_start"] == row["line_start"] and
             anchor["line_end"] == row["line_end"] and
             (not row["anchor_text"] or row["anchor_text"] in anchor["first_line"]) and
             row["url"] == source["url"] + "#L" + str(row["line_start"]), f"{identity}: citation/source mismatch")

    workflow_document = get("workflow-contracts")
    no_execution(workflow_document, "workflow contracts")
    need(workflow_document["frozen_versions"] == versions, "workflow frozen version drift")
    workflows = unique(workflow_document["workflows"], "id", "workflow")
    dag(workflows, "workflow_prerequisites", "workflow")
    companion_document = get("companion-inventory")
    need(companion_document["all_companion_versions_resolved"] is False and
         companion_document["all_companion_public_api_scope_resolved"] is False,
         "captured companion source scope and pins remain unresolved")
    companions = unique(companion_document["companions"], "id", "workflow companion")
    fixtures = unique(get("analytical-fixtures")["fixtures"], "id", "analytical fixture")
    expected_states = {"implementation": "unknown", "tested": "unrun", "external": "unrun",
                       "performance": "unrun", "release": "unreleased", "api_mapping_credit": 0,
                       "executed_framework_cases": 0}
    scenarios, scenario_workflows = {}, {}
    for identity, row in workflows.items():
        need(row["single_accountable_owner"] in repositories and row["states"] == expected_states,
             f"{identity}: missing owner or false evidence promotion")
        need(bool(row["canonical_capability_prerequisites"]) and
             set(row["canonical_capability_prerequisites"]) <= capabilities.keys(), f"{identity}: unknown prerequisites")
        need(row["hardware_classes"] and row["specific_obligations"] and row["done_when"], f"{identity}: missing acceptance")
        need(set(row["companion_decisions"]) <= companions.keys(), f"{identity}: missing companion decision")
        for framework, variant in row["framework_variants"].items():
            need(variant["release"] == versions.get(framework) and variant["sources"] and
                 set(variant["sources"]) <= citations.keys(), f"{identity}: framework variant/version/source drift")
        for case in row["acceptance_scenarios"]:
            need(case["id"] not in scenarios and case["execution_status"] == "unrun" and
                 case["given"] and case["when"] and case["then"] and case["negative_cases"],
                 f"{identity}: repeated scenario, missing acceptance or false execution")
            need(not case["analytical_fixture"] or case["analytical_fixture"] in fixtures,
                 f"{identity}: unknown analytical fixture")
            scenarios[case["id"]] = case
            scenario_workflows[case["id"]] = identity
    for identity, row in companions.items():
        need(row["selected_versions"] is None and row["selected_artifact_sha256"] is None and
             row["compatibility_executed"] is False and row["workspace_runtime_permission"] is False and
             row["states"] == expected_states and
             row["public_companion_api_inventory_complete"] is False and row["sources"] and
             set(row["sources"]) <= citations.keys() and set(row["blocks_workflows"]) <= workflows.keys(),
             f"{identity}: unreviewed companion cannot acquire pins, scope or runtime permission")
    decisions = get("architecture-decisions")
    need(decisions["decisions_approved"] is False and decisions["runtime_architecture_permission_granted"] is False,
         "captured workflow recommendations cannot grant implementation ADR/runtime permission")
    for row in decisions["decisions"]:
        need(row["status"] == "decision_required" and row["sources"] and set(row["sources"]) <= citations.keys(),
             "workflow source recommendation status/source drift")
    dispositions = get("planning-dispositions")
    need(dispositions["scope_reduction"] is False and dispositions["workspace_runtime_permission"] is False and
         dispositions["policy_directions_resolved"] is True and dispositions["concrete_provider_approvals_granted"] is False,
         "planning directions cannot grant a scope reduction or concrete implementation/runtime approval")
    choices = unique(dispositions["decisions"], "id", "workflow planning direction")
    original_choices = unique(decisions["decisions"], "id", "captured workflow recommendation")
    need(choices.keys() == original_choices.keys(), "workflow planning direction lost a source decision")
    for identity, row in choices.items():
        need(row["selected_direction"] == original_choices[identity]["recommendation"] and
             row["accountable_owner"] == original_choices[identity]["owner"] and
             row["existing_policy_authority"] and
             set(row["existing_policy_authority"]) <= set(program["resolved_policy_decisions"]) and
             row["concrete_provider_ADR_approval"] is False and row["implementation_authorization_inferred"] is False,
             f"{identity}: source direction, policy authority or concrete approval drift")
    language = get("acceptance-language")
    need(language["all_runtime_adapters_bound"] is False and language["all_api_parameter_domains_materialized"] is False and
         language["runtime_evidence_credit"] == 0, "unbound acceptance programs cannot qualify")
    programs = unique(language["scenario_programs"], "scenario_id", "acceptance program")
    need(programs.keys() == scenarios.keys(), "workflow scenario/program conservation failed")
    opcodes = unique(language["opcode_contracts"], "opcode", "acceptance opcode")
    for identity, row in programs.items():
        case = scenarios[identity]
        workflow = workflows[scenario_workflows[identity]]
        expected_adapters = {framework: {"root_version": variant["release"],
                            "binding": "unbound; source public selection and exact legal axes/companions required",
                            "sources": variant["sources"]}
                            for framework, variant in workflow["framework_variants"].items()
                            if framework in case.get("reference_variants", workflow["framework_variants"])}
        need(row["workflow_id"] == scenario_workflows[identity] and
             row["fixture"] == scenarios[identity]["analytical_fixture"] and
             row["native_adapter"]["owner"] == workflows[row["workflow_id"]]["single_accountable_owner"] and
             row["reference_adapters"] == expected_adapters and row["negative_contracts"] == case["negative_cases"] and
             row["export_matrix_id"] == case.get("export_matrix_id") and
             row["source_rejected_route"] == case.get("source_rejected_route", False),
             f"{identity}: program/scenario/workflow/fixture owner mismatch")
        need(row["execution_status"] == "unrun" and row["native_adapter"]["revision"] is None and
             row["native_adapter"]["binding"].startswith("unbound"), f"{identity}: unbound native execution claimed")
        need(bool(row["program"]) and
             [op["sequence"] for op in row["program"]] == list(range(len(row["program"]))) and
             all(op["opcode"] in opcodes for op in row["program"]) and
             row["program"][-1]["opcode"] in {"assert", "measure"}, f"{identity}: invalid acceptance program")
        need([operation["opcode"] for operation in row["program"]] == instruction_policy(row["workflow_id"], case),
             f"{identity}: required computation/assertion or workflow stage missing")
        for framework, adapter in row["reference_adapters"].items():
            need(framework in versions and adapter["root_version"] == versions[framework] and
                 adapter["sources"] and set(adapter["sources"]) <= citations.keys() and
                 adapter["binding"].startswith("unbound"), f"{identity}: reference adapter/source/version drift")
        for operation in row["program"]:
            need(operation["source_steps"] == (case["when"] if operation["opcode"] == "compute" else None) and
                 operation["assertions"] == (case["then"] if operation["opcode"] == "assert" else None),
                 f"{identity}: acceptance operations do not bind the scenario's inputs/assertions")
    matrix = get("export-acceptance-matrix")
    fields(matrix, {"framework_cases_executed": int, "public_surface_complete": bool,
                    "semantic_mapping_complete": bool}, "export matrix")
    need(matrix["framework_cases_executed"] == 0 and matrix["public_surface_complete"] is False and
         matrix["semantic_mapping_complete"] is False and matrix["frozen_versions"] == versions,
         "export matrix cannot claim execution, complete scope or another baseline")
    profiles = unique(matrix["rows"], "id", "export profile")
    matrix_cases = [case for case in scenarios.values() if "export_matrix_id" in case]
    need({case["export_matrix_id"] for case in matrix_cases} == profiles.keys(), "export profile/scenario set mismatch")
    for row in profiles.values():
        need(row["execution_status"] == "unrun" and row["native_target_execution_credit"] == 0 and
             row["framework"] in versions and row["sources"] and set(row["sources"]) <= citations.keys() and
             row["semantic_mapping_complete"] is False and row["source_valid_axis_expansion_complete"] is False and
             row["compatibility_outcome"]["guaranteed_by_required_options"] is False,
             "export source profile cannot imply target or compatibility qualification")
        need(row["compatibility_outcome"]["status"] in {"unrun", "unrun-potential-version-conflict"},
             "export compatibility outcome cannot claim a passing runtime result")
    for case in matrix_cases:
        profile = profiles[case["export_matrix_id"]]
        need(case["reference_variants"] == [profile["framework"]] and
             set(case["sources"]) <= citations.keys(), "export scenario/profile framework/source mismatch")
        if not case.get("stateful_export_suffix"):
            need(case["given"]["shape_contract"] == profile["shape_contract"] and
                 case["given"]["required_options"] == profile["required_options"],
                 "export scenario/profile shape/options mismatch")
    need(__debug__, "analytical fixture checking requires Python assertions enabled")
    try:
        verify_fixture_truth(fixtures)
        negatives = negative_fixture_checks(fixtures)
    except (AssertionError, ValueError, KeyError, TypeError, ZeroDivisionError) as error:
        raise ParityError(f"analytical workflow fixture fails: {error}") from error
    return {"workflows": len(workflows), "unrun_acceptance_scenarios": len(scenarios),
            "export_route_profiles": len(matrix["rows"]), "analytical_fixtures_checked": len(fixtures),
            "malformed_fixture_rejections": len(negatives), "source_receipts": len(sources),
            "source_citations": len(citations), "unresolved_companion_pins": len(companions),
            "runtime_evidence_credit": 0, "full_workflow_inventory_complete": False}, paths
