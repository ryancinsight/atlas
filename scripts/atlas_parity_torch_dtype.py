"""Canonical repaired Torch dtype source slice, never whole API/runtime qualification."""
import json

from atlas_parity_dtype import no_credit
from atlas_parity_dtype_headers import exact_fields
from atlas_parity_torch_dtype_capture import PREFIX, PACKET_SHA, REVIEW_SHA, REVISION, validate_capture
from atlas_parity_torch_dtype_joins import validate_joins
from atlas_parity_torch_dtype_model import validate_model, result_type
from atlas_parity_torch_dtype_oracles import validate_complex_case
from atlas_parity_torch_dtype_sources import validate_sources
from atlas_parity_schema import need, local_path, read_json
from atlas_parity_tables import canonical

STATUS = {'definition': 'bounded_source_partial', 'implementation': 'unknown', 'tested': 'unrun',
          'external': 'unrun', 'performance': 'unrun', 'release': 'unreleased', 'actual_implementation_owner': None}


def counts(original):
    return {'public_endpoint_partial_contracts': len(original['contracts.json']['records']),
        'admitted_binding_identities': len(original['admitted-bindings.json']['records']),
        'source_receipts': len(original['source-registry.json']['records']),
        'source_line_witnesses': len(original['source-witnesses.json']['records']),
        'native_dtype_enums': len(original['dtype-model.json']['native_enum_records']),
        'core_promotion_cells': len(original['dtype-model.json']['core_lookup_cells']),
        'native_promotion_pairs': len(original['dtype-model.json']['native_promotion_pairs']),
        'native_cast_permission_pairs': len(original['dtype-model.json']['native_cast_permission_pairs']),
        'analytical_or_source_parametric_cases_unrun': sum(c['status'] == 'UNRUN' for c in original['acceptance-cases.json']['records']),
        'open_named_gaps': sum(g['status'] == 'open' for g in original['remaining-gaps.json']['records']),
        'new_source_blob_reads': len(original['git-blob-read-receipts.json']['records']),
        'runtime_cases_executed': sum(c['execution_count'] for c in original['acceptance-cases.json']['records'])}


def typed_counts(actual, expected, context):
    exact_fields(actual, {key: int for key in expected}, context)
    need(actual == expected, context + ': record-derived count differs')


def validate_aggregates(original, manifest, index):
    actual = counts(original)
    fixed = dict(public_endpoint_partial_contracts=10, admitted_binding_identities=10, source_receipts=45,
        source_line_witnesses=88, native_dtype_enums=47, core_promotion_cells=196, native_promotion_pairs=2209,
        native_cast_permission_pairs=2209, analytical_or_source_parametric_cases_unrun=66, open_named_gaps=14,
        new_source_blob_reads=28, runtime_cases_executed=0)
    need(actual == fixed, 'Torch bounded record conservation differs')
    for document in [index['counts'], manifest['counts'], original['counts.json']['counts']]:
        typed_counts(document, actual, 'Torch aggregate')
    for status in [original['contracts.json']['status']] + [r['status'] for r in original['contracts.json']['records']]:
        need(canonical(status) == canonical(STATUS), 'Torch source partial/unrun/null-owner status domain differs')
    need(canonical(manifest['status']) == canonical(dict(STATUS, definition='bounded_partial_source_definition')),
         'Torch manifest whole-scope/runtime status differs')
    model = original['dtype-model.json'];source = original['source-registry.json'];cases = original['acceptance-cases.json'];gaps = original['remaining-gaps.json']
    typed_counts(model['counts'], dict(native_dtype_enums=47, core_lookup_axes=14, core_lookup_cells=196,
                 native_dtype_pairs=2209, cast_permission_pairs=2209), 'Torch native model')
    for doc in [original['source-witnesses.json'], original['contracts.json'], cases, gaps]:
        need(type(doc['schema_version']) is int and doc['schema_version'] == 1 and type(doc['count']) is int and
             doc['count'] == len(doc['records']), 'Torch record header aggregate differs')
    need(type(source['planned_paths']) is type(source['verified_paths']) is int and
         source['planned_paths'] == source['verified_paths'] == len(source['records']) == 45 and source['remaining_paths'] == [],
         'Torch selected source coverage differs')
    for case in cases['records']:
        need(case['status'] == 'UNRUN' and type(case['execution_count']) is int and case['execution_count'] == 0 and
             type(case['runtime_evidence']) is list and case['runtime_evidence'] == [], 'Torch case runtime credit forbidden')
    need(cases['all_framework_cases_unrun'] is True, 'Torch aggregate UNRUN state differs')
    bounded = gaps['bounded_completeness']
    for flag in ['full_transitive_native_closure', 'whole_public_api_semantics', 'whole_public_dtype_registry']:
        need(bounded[flag] is False, 'Torch full-scope credit forbidden')
    need(bounded['framework_runtime_cases_executed'] == 0 and type(bounded['framework_runtime_cases_executed']) is int and
         all(g['status'] == 'open' and g['scope_exclusion'] is False for g in gaps['records']), 'Torch gap/runtime qualification forbidden')
    report = original['source-checks.json']
    typed_counts({k: report[k] for k in ['check_count', 'adversarial_probe_count', 'framework_runtime_cases_executed']},
        dict(check_count=len(report['checks']), adversarial_probe_count=len(report['adversarial_probes']), framework_runtime_cases_executed=0), 'Torch source report')
    typed_counts(manifest['checks'], dict(source_definition_checks=14, adversarial_rejection_probes=38, framework_runtime_cases_executed=0), 'Torch manifest source checks')
    need(len(report['checks']) == 14 and len(report['adversarial_probes']) == 38 and
         model['status'] == 'source-model-only; neither runtime evidence nor complete public dtype registry' and
         original['contracts.json']['definition_state'] == 'bounded partial source obligations only; no whole-API closure' and
         original['workspace-policy-proposal.json']['status'] == 'proposed ordinary native/generic workspace design; no ADR approval or implementation claim',
         'Torch source-only scope/status domain differs')
    return actual


def prepare_torch_dtype(root, relative, program):
    root = root.resolve()
    need(relative == PREFIX + 'index.json' and program['files'].get('torch_native_dtype_policy') == relative,
         'Torch program source-specific role differs')
    index_path = local_path(root, relative);index = read_json(index_path)
    exact_fields(index, {'schema_version': int, 'version': str, 'parent_program_version': str, 'framework': str,
        'reference_version': str, 'reference_revision': str, 'source_manifest_sha256': str, 'independent_review_sha256': str,
        'artifacts': list, 'counts': dict, 'status': dict, 'original_source_review_scope': str}, 'Torch source index')
    need(index['schema_version'] == 1 and index['version'] == '2026-10-26.1' and
         index['parent_program_version'] == '2026-10-26.10' and index['framework'] == 'pytorch' and
         index['reference_version'] == '2.14.1' and index['reference_revision'] == REVISION and
         index['source_manifest_sha256'] == PACKET_SHA and index['independent_review_sha256'] == REVIEW_SHA and
         index['original_source_review_scope'] == 'accepted_repaired_source_only_not_canonical_candidate_review',
         'Torch introduction/version/pin/review scope differs')
    no_credit(index['status'])
    original, documents, paths = validate_capture(root, index)
    validate_aggregates(original, documents[PREFIX + 'captured/manifest.json'], index)
    return root, index, original, documents, paths + [index_path]


def validate_plan(plan, original, citations):
    exact_fields(plan, {'schema_version': int, 'scope': str, 'parent_work_packages': list, 'packages': list,
        'analytical_controls': list, 'framework_runtime_cases_executed': int, 'whole_API_credit': bool}, 'Torch conditional acceptance plan')
    need(plan['schema_version'] == 1 and plan['scope'] == 'conditional_native_acceptance_not_implementation_or_ADR_approval' and
         plan['parent_work_packages'] == ['WP-001', 'WP-003', 'WP-004'] and plan['framework_runtime_cases_executed'] == 0 and
         plan['whole_API_credit'] is False and len(plan['packages']) == 3 and len(plan['analytical_controls']) == 6,
         'Torch conditional acceptance scope/count differs')
    need(len({p['id'] for p in plan['packages']}) == 3 and {p['id'] for p in plan['packages']} ==
         {'TORCH-DTYPE-DEFINITION', 'TORCH-DTYPE-POLICY', 'TORCH-DTYPE-TENSOR'}, 'Torch bounded package IDs differ')
    numeric = {'PT-DTYPE-PROMOTE', 'PT-DTYPE-CANCAST', 'PT-DTYPE-RESULT', 'PT-DTYPE-GET-DEFAULT', 'PT-DTYPE-SET-DEFAULT'}
    for index, package in enumerate(plan['packages']):
        exact_fields(package, {'id': str, 'planned_owner': str, 'prerequisites': list, 'readiness': str,
            'gap_ids': list, 'acceptance_case_ids': list, 'required_evidence': list,
            'actual_implementation_owner': type(None)}, 'Torch conditional package')
        expected_cases = [c['id'] for c in original['acceptance-cases.json']['records'] if index == 0 or (c['contract_id'] in numeric) == (index == 1)]
        need(package['acceptance_case_ids'] == expected_cases, 'Torch conditional operation/case domain differs')
        need(package['planned_owner'] == ['atlas', 'eunomia', 'coeus'][index] and
             package['prerequisites'] == [[], ['TORCH-DTYPE-DEFINITION'], ['TORCH-DTYPE-POLICY']][index] and
             package['readiness'] == 'not_ready_evidence_required' and package['actual_implementation_owner'] is None and
             package['required_evidence'] and package['acceptance_case_ids'] and
             set(package['gap_ids']) <= {r['id'] for r in original['remaining-gaps.json']['records']} and
             set(package['acceptance_case_ids']) <= {r['id'] for r in original['acceptance-cases.json']['records']} and
             set(package['prerequisites']) <= {p['id'] for p in plan['packages'][:index]}, 'Torch conditional readiness/DAG/case/gap differs')
    for control in plan['analytical_controls']:
        exact_fields(control, {'id': str, 'source_case_id': str, 'case': dict, 'runtime_executed': bool}, 'Torch analytical control role')
        need(control['source_case_id'] == 'ADD-COMPLEX-GRAD' and control['runtime_executed'] is False,
             'Torch analytical control cannot claim runtime')
        validate_complex_case(control['case'])
    need(len({c['id'] for c in plan['analytical_controls']}) == 6, 'Torch analytical control IDs duplicate')


def validate_torch_dtype(prepared, program, capabilities, references, mappings, assigned):
    root, index, original, docs, paths = prepared;get = lambda name: docs[PREFIX + name]
    snapshot = next(s for s in program['reference_snapshots'] if s['framework'] == 'pytorch')
    need(snapshot['version'] == '2.14.1' and read_json(local_path(root, snapshot['path']))['source_revision'] == REVISION,
         'Torch frozen canonical snapshot differs')
    citations = validate_sources(original['source-registry.json'], original['source-witnesses.json'],
                                 get('captured/manifest.json'), get('source-proof.json'))
    categories, axis, table = validate_model(original['dtype-model.json'], original['source-witnesses.json'], original['computation-policies.json'])
    validate_joins(get('joins.json'), original['contracts.json'], original['acceptance-cases.json'],
        original['admitted-bindings.json'], capabilities, references, mappings, assigned)
    for contract in original['contracts.json']['records']:
        need(set(contract['source_refs']) <= citations and set(contract['open_gap_ids']) <=
             {g['id'] for g in original['remaining-gaps.json']['records']}, 'Torch contract source/gap absent')
    for case in original['acceptance-cases.json']['records']:
        need(set(case['source_refs']) <= citations, 'Torch case source absent')
        if case['contract_id'] == 'PT-DTYPE-RESULT':
            need(result_type(case['fixture']['operands'], categories, axis, table) == case['expected']['dtype'], 'Torch input-sensitive rank/default source oracle differs')
        if case['id'] == 'ADD-COMPLEX-GRAD': validate_complex_case(case)
    validate_plan(get('acceptance-plan.json'), original, citations)
    evidence = get('review-proof.json');review = get('independent-review.json')
    exact_fields(evidence, {'schema_version': int, 'role': str, 'records': list}, 'Torch review proof')
    need(evidence['schema_version'] == 1 and evidence['role'] == 'original_source_review_proof_not_canonical_or_runtime_approval' and len(evidence['records']) == 2, 'Torch review proof role differs')
    import hashlib
    need({r['original_path'] for r in evidence['records']} == {'independent-model-and-replay.json', 'independent-repair-checks.json'}, 'Torch review proof record identities differ')
    for record in evidence['records']:
        exact_fields(record, {'original_path': str, 'original_text': str}, 'Torch review proof original bytes')
        expected = review['review_evidence'][record['original_path']];data = record['original_text'].encode()
        need(hashlib.sha256(data).hexdigest() == expected['sha256'] and len(data) == expected['bytes'], 'Torch original review proof bytes differ')
        value = json.loads(data)
        need(value.get('framework_runtime_cases_executed', value.get('runtime_cases_executed', 0)) == 0, 'Torch review proof grants no runtime')
    actual = counts(original)
    return {**actual, 'existing_mapped_API_associations': sum(r['reference_id'] in assigned for r in get('joins.json')['records']),
        'explicitly_unmapped_API_associations': sum(r['reference_id'] not in assigned for r in get('joins.json')['records']),
        'analytical_complex_controls': 6, 'public_denominator_changed': False, 'whole_API_closure_credit': 0,
        'framework_execution_credit': 0, 'source_packet_sha256': PACKET_SHA, 'source_review_sha256': REVIEW_SHA}, paths
