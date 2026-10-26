"""Bounded NumPy native dtype source overlay, no API/runtime qualification."""

from atlas_parity_dtype import no_credit
from atlas_parity_dtype_headers import exact_fields
from atlas_parity_numpy_dtype_capture import PREFIX, PACKET_SHA, REVIEW_SHA, REVISION, validate_capture
from atlas_parity_numpy_dtype_joins import validate_joins
from atlas_parity_numpy_dtype_relations import validate_relations
from atlas_parity_numpy_dtype_sources import validate_sources
from atlas_parity_schema import local_path, need, read_json


def prepare_numpy_dtype(root, relative, program):
    root = root.resolve()
    need(relative == PREFIX + 'index.json' and program['files'].get('numpy_native_dtype_policy') == relative, 'NumPy native program files role association differs')
    index_path = local_path(root, relative)
    index = read_json(index_path)
    exact_fields(index, {'schema_version': int, 'version': str, 'parent_program_version': str,
        'framework': str, 'reference_version': str, 'reference_revision': str, 'artifacts': list,
        'status': dict, 'source_manifest_sha256': str, 'independent_review_sha256': str,
        'original_source_review_scope': str, 'counts': dict}, 'NumPy native source index')
    need(index['schema_version'] == 1 and index['version'] == '2026-10-26.1' and
         index['parent_program_version'] == '2026-10-26.9' and index['framework'] == 'numpy' and
         index['reference_version'] == '2.5.4' and index['reference_revision'] == REVISION and
         index['source_manifest_sha256'] == PACKET_SHA and index['independent_review_sha256'] == REVIEW_SHA and
         index['original_source_review_scope'] == 'accepted_source_only_not_exact_canonical_candidate_review',
         'NumPy native index version/pin/source-review scope drift')
    no_credit(index['status'])
    exact_fields(index['counts'], {'source_files': int, 'source_functions': int, 'source_spans': int,
        'symbolic_safe_cells': int, 'illustrative_ABI_profiles': int, 'source_families': int,
        'primary_IDs': int, 'supporting_IDs': int, 'unrun_cases': int, 'open_gaps': int}, 'NumPy native exact counts')
    need(index['counts'] == dict(source_files=78, source_functions=129, source_spans=131,
        symbolic_safe_cells=576, illustrative_ABI_profiles=2, source_families=10, primary_IDs=3,
        supporting_IDs=5, unrun_cases=47, open_gaps=8), 'NumPy native count conservation drift')
    original, documents, paths = validate_capture(root, index)
    return root, index, original, documents, paths + [index_path]


def validate_correction(document, original, mappings):
    exact_fields(document, {'schema_version': int, 'raw_mapping_id': str, 'raw_source_contract': dict,
        'correction_entry': list, 'previous_statement': str, 'corrected_scope': str,
        'history_mutated': bool, 'mapping_stage_changed': bool, 'whole_API_credit': bool},
        'NumPy prior wording correction disposition')
    raw = mappings.get('core-numpy-numpy-result-type')
    need(raw is not None and document['schema_version'] == 1 and
         document['raw_mapping_id'] == raw['id'] and document['raw_source_contract'] == raw['source_contract'] and
         document['correction_entry'] == ['corrections', 2] and
         document['previous_statement'] == original['gap-disposition.json']['corrections'][2]['previous'] and
         document['corrected_scope'] == original['gap-disposition.json']['corrections'][2]['correct'] and
         document['history_mutated'] is document['mapping_stage_changed'] is document['whole_API_credit'] is False,
         'NumPy annotated correction must preserve history, exact source and mapping stage')


def validate_numpy_dtype(prepared, program, capabilities, references, mappings, assigned):
    root, index, original, documents, paths = prepared
    get = lambda name: documents[PREFIX + name]
    snapshots = [s for s in program['reference_snapshots'] if s['framework'] == 'numpy']
    need(len(snapshots) == 1 and snapshots[0]['version'] == '2.5.4' and
         read_json(local_path(root, snapshots[0]['path']))['source_revision'] == REVISION,
         'NumPy native source snapshot differs')
    sources = original['source-receipts.json']
    witnesses = original['source-witnesses.json']
    citations = validate_sources(sources, witnesses, original['source-branch-catalog.json'],
                                original['inputs/frozen-tree.json'], get('source-bindings.json'))
    cells = validate_relations(original['policy-tables.json'], witnesses['citations'])
    ids = validate_joins(get('joins.json'), original['native-contracts.json'], original['acceptance-cases.json'],
                         witnesses, capabilities, references, mappings, assigned)
    validate_correction(get('correction-disposition.json'), original, mappings)
    scope = original['scope.json']
    need(scope['source_file_count'] == 78 and scope['c_or_python_function_count'] == 129 and
         scope['citation_count'] == 131 and scope['source_safe_table_cells'] == 576 and
         scope['framework_imports'] == scope['builds'] == scope['runtime_executions'] == 0 and
         scope['canonical_provider_edits'] is False and scope['whole_api_semantics_complete'] is False,
         'NumPy original source-scope qualification drift')
    owner = original['ownership-plan.json']
    need(owner['status'] == 'planning_recommendation_no_codeowner_or_implementation_ADR_approval' and
         owner['api_policy_primary'] == 'eunomia' and owner['user_decisions_required'] == [],
         'NumPy original ownership/ADR or user-decision credit drift')
    gaps = original['remaining-gaps.json']
    need(len(gaps['gaps']) == 8 and len({g['id'] for g in gaps['gaps']}) == 8 and
         all(g['status'] == 'open' for g in gaps['gaps']) and gaps['runtime_credit'] is False and
         gaps['whole_api_semantics_complete'] is False and gaps['source_acquisition_blocker'] is None and
         gaps['source_reads_denied'] == gaps['source_reads_uncertain'] == [],
         'NumPy open evidence gaps cannot become current access holds, exclusions or qualification')
    requests = [row for name in ('source-acquisition.json', 'source-acquisition-extra.json',
                'source-acquisition-descriptor-support.json') for row in original[name]['requests']]
    need(len(requests) == len({r['expected_git_blob'] for r in requests}) == 47 and
         all(r['outcome'] == 'verified' and r['retries'] == r['returncode'] == 0 and
             r['target'] == 'https://api.github.com/repos/numpy/numpy/git/blobs/' + r['expected_git_blob'] and
             sources['source_files'][r['source_path']]['git_blob'] == r['expected_git_blob'] for r in requests),
         'NumPy historical acquisition receipt conservation/route drift')
    need(original['benchmarks.json']['status'] == 'unrun', 'NumPy benchmark qualification forbidden')
    return {'policy_version': index['version'], **index['counts'], 'existing_endpoint_links': ids,
            'existing_mapped_API_associations': sum(r['reference_id'] in assigned for r in get('joins.json')['endpoints']),
            'explicitly_unmapped_API_associations': sum(r['reference_id'] not in assigned for r in get('joins.json')['endpoints']),
            'unresolved_source_prerequisite_labels': ['INTEROP-NATIVE'],
            'public_denominator_changed': False, 'whole_API_closure_credit': 0,
            'framework_execution_credit': 0, 'source_packet_sha256': PACKET_SHA,
            'source_review_sha256': REVIEW_SHA, 'current_access_actions': 0}, paths
