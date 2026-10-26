"""Canonical joins for the bounded frozen JAX promotion/casting policy."""
import ast
import hashlib

from atlas_parity_core_sources import validate_numpy_jax
from atlas_parity_dtype_capture import PREFIX, PACKET_SHA, REVIEW_SHA, validate_capture
from atlas_parity_dtype_graph import validate_graphs
from atlas_parity_schema import digest, fields, local_path, need, read_json, unique

NO_CREDIT = {'public_denominator_changed': False, 'whole_API_semantics_complete': False,
             'reference_runtime_cases': 0, 'provider_execution_cases': 0,
             'external_verified': False, 'performance_qualified': False, 'released': False}
ENDPOINT_CLAUSES = {
    'jax.numpy.result_type': ['JP01', 'JP02', 'JP03', 'JP04', 'JP05', 'JP06', 'JP07', 'JP12'],
    'jax.numpy.promote_types': ['JP01', 'JP02', 'JP07', 'JP13'],
    'jax.numpy.can_cast': ['JP01', 'JP08'], 'jax.dtypes.canonicalize_dtype': ['JP03'],
    'jax.numpy.dtype': ['JP01', 'JP05'], 'jax.numpy.astype': ['JP04', 'JP14', 'JP15', 'JP17'],
    'jax.lax.convert_element_type': ['JP04', 'JP15', 'JP17'],
    'jax.grad': ['JP16', 'JP17', 'JP18'], 'jax.jvp': ['JP16', 'JP17', 'JP18']}


def no_credit(status):
    need(type(status) is dict and set(status) == set(NO_CREDIT) and all(
        type(status[k]) is type(v) and status[k] == v for k, v in NO_CREDIT.items()),
        'dtype source policy cannot assert complete API, runtime, performance or release credit')


def source_references(value):
    if type(value) is dict:
        for child in value.values():
            yield from source_references(child)
    elif type(value) is list:
        for child in value:
            yield from source_references(child)
    elif type(value) is str and value.startswith(('jax:', 'numpy:')) and ':L' in value:
        yield value


def validate_source_functions(policy, witnesses):
    for clause in policy['rules']:
        for function in clause['source_functions']:
            need(function['source'] in witnesses, 'dtype function source absent')
            # The reviewed generator's AST-render digest is immutable capture
            # provenance. ast.unparse formatting can differ across Python
            # versions; exact body bytes are checked by the span receipt above.
            digest(function['source_ast_sha256'], 'dtype original AST rendering')
            tree = ast.parse(witnesses[function['source']]['text'])
            nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function['name']]
            need(len(nodes) == 1 and ast.unparse(nodes[0].args) == function['parameters'],
                 'dtype source function signature drift')
            for variant in function['declaration_variants']:
                need(variant['source'] in witnesses, 'dtype declaration variant source absent')
                parsed = ast.parse(witnesses[variant['source']]['text'])
                node = next((n for n in parsed.body if isinstance(n, ast.FunctionDef)), None)
                need(node is not None and ast.unparse(node.args) == variant['parameters'] and
                     (ast.unparse(node.returns) if node.returns else None) == variant['returns'] and
                     [ast.unparse(n) for n in node.decorator_list] == variant['decorators'],
                     'dtype overload/signature variant drift')


def validate_joins(document, policy, cases, capabilities, references, citations):
    clauses = unique(document['clauses'], 'id', 'dtype clause join')
    source_clauses = unique(policy['rules'], 'id', 'dtype captured clause')
    targets = unique(cases['acceptance_targets'], 'id', 'dtype acceptance target')
    need(set(clauses) == set(source_clauses) == {f'JP{i:02}' for i in range(1, 19)},
         'dtype clause conservation drift')
    need(document['cases_are_unrun'] is True and document['all_source_policy_clauses_joined'] is True,
         'dtype clause acceptance status drift')
    endpoint_rows = unique(document['endpoints'], 'reference_id', 'dtype endpoint join')
    source_endpoints = unique(policy['existing_admitted_endpoints'], 'reference_id', 'dtype captured endpoint')
    need(endpoint_rows.keys() == source_endpoints.keys() and len(endpoint_rows) == 9,
         'dtype existing identity conservation drift')
    for identity, row in endpoint_rows.items():
        cap = row['canonical_capability']
        need(identity in references and row['symbol'] == references[identity]['symbol'] ==
             source_endpoints[identity]['symbol'] and cap in capabilities,
             'dtype API/source identity join drift')
        expected_cap = ('AD-REVERSE' if row['symbol'] == 'jax.grad' else
                        'AD-FORWARD' if row['symbol'] == 'jax.jvp' else 'NUM-PROMOTE')
        need(cap == expected_cap and row['single_accountable_owner'] == capabilities[cap]['owner'] and
             row['prerequisites'] == capabilities[cap]['prerequisites'] and
             row['complete_API_mapping_credit'] is False and row['semantic_completion_credit'] is False,
             'dtype API owner/prerequisite/credit drift')
        need(row['clause_ids'] == ENDPOINT_CLAUSES.get(row['symbol']) and
             len(row['clause_ids']) == len(set(row['clause_ids'])) and
             set(row['clause_ids']) <= set(clauses), 'dtype endpoint clause join absent')
    for identity, row in clauses.items():
        original = source_clauses[identity]
        cap = 'AD-TRANSFORM' if original['category'] in {'autodiff_dtype', 'extended_autodiff_protocol'} else 'NUM-PROMOTE'
        need(row['canonical_capability'] == cap and row['single_accountable_owner'] == capabilities[cap]['owner'] and
             row['prerequisites'] == capabilities[cap]['prerequisites'], 'dtype clause owner/DAG drift')
        position = policy['rules'].index(original)
        need(row['source_entry'] == ['rules', position] and row['source_citations'] == original['sources'] and
             set(row['source_citations']) <= citations, 'dtype clause source entry/join drift')
        expected_cases = [t['id'] for t in cases['acceptance_targets'] if identity in t['rule_ids']]
        expected_refs = [r['reference_id'] for r in document['endpoints'] if identity in r['clause_ids']]
        need(row['case_ids'] == expected_cases and expected_cases and
             row['related_existing_reference_ids'] == expected_refs and
             row['source_mapping_complete'] is False and type(row['runtime_cases_executed']) is int and
             row['runtime_cases_executed'] == 0, 'dtype clause case/API/status join drift')
    need(len(targets) == 18 and cases['count'] == 18 and all(
        t['reference_runtime'] == t['provider_execution'] == t['external_verification'] ==
        t['performance'] == 'unrun' and t['skips_count_as_verification'] is False and
        bool(t['rule_ids']) and set(t['rule_ids']) <= set(clauses) for t in targets.values()),
        'dtype acceptance target status/conservation drift')
    need(set().union(*(set(t['rule_ids']) for t in targets.values())) == set(clauses),
         'dtype source clause lacks an unrun acceptance target')


def validate_dtype_policy(root, relative, program, capabilities, references):
    root = root.resolve()
    index_path = local_path(root, relative)
    index = read_json(index_path)
    fields(index, {'schema_version': int, 'version': str, 'artifacts': list, 'status': dict}, 'dtype index')
    fields(index, {'rules': int, 'source_pairs': int, 'unrun_acceptance_targets': int,
                   'remaining_gaps': int}, 'dtype counts')
    need(index['schema_version'] == 1 and index['version'] == '2026-10-26.1' and
         index['parent_program_version'] == program['program_version'] and
         index['source_manifest_sha256'] == PACKET_SHA and index['independent_review_sha256'] == REVIEW_SHA,
         'dtype index version/pin drift')
    no_credit(index['status'])
    original, docs, paths = validate_capture(root, index)
    paths.append(index_path)
    get = lambda name: docs[PREFIX + name]
    graph, catalog = original['promotion-graph.json'], original['dtype-catalog.json']
    pairs = validate_graphs(graph, catalog)
    need(index['rules'] == index['unrun_acceptance_targets'] == 18 and
         index['source_pairs'] == pairs and index['remaining_gaps'] == 10,
         'dtype index aggregate drift')
    snapshots = {}
    for snapshot in program['reference_snapshots']:
        raw = read_json(local_path(root, snapshot['path']))
        snapshots[snapshot['framework']] = dict(version=snapshot['version'], revision=raw['source_revision'])
    receipts = dict(original['source-receipts.json'], network_requests=0,
                    whole_framework_source_or_semantic_complete=False)
    citations = validate_numpy_jax(receipts, get('source-witnesses.json'), snapshots)
    need(len(citations) == 63 and len(receipts['sources']) == 17, 'dtype source receipt conservation drift')
    policy = original['policy-contracts.json']
    for document in original.values():
        if isinstance(document, dict):
            need(set(source_references(document)) <= citations, 'dtype policy/case source citation absent')
    validate_source_functions(policy, get('source-witnesses.json')['witnesses'])
    validate_joins(get('joins.json'), policy, original['acceptance-targets.json'], capabilities, references, citations)
    cp, disposition = original['CP02-evidence-audit.json'], get('companion-disposition.json')
    workflow_path = local_path(root, disposition['raw_record_path'])
    paths.append(workflow_path)
    workflow = read_json(workflow_path)
    raw = [r for r in workflow['companions'] if r['id'] == 'CP02']
    need(len(raw) == 1 and raw[0] == cp['canonical_record'] == original['inputs/CP02.json'] and
         hashlib.sha256(workflow_path.read_bytes()).hexdigest() == disposition['raw_record_sha256'] and
         disposition['raw_pin_status'] == raw[0]['pin_status'] == 'decision_required_no_resolved_artifact_set' and
         disposition['derived_pin_status'] == cp['recommended_record_disposition'] ==
         'evidence_required_no_resolved_artifact_set', 'dtype CP02 immutable raw/derived disposition drift')
    need(disposition['captured_raw_entry_path'] == PREFIX + 'captured/inputs/CP02.json' and
         disposition['raw_record_path'] == 'workflows/companion-inventory.json' and
         disposition['raw_id'] == 'CP02' and disposition['resolved_artifacts'] is False and
         disposition['canonical_workflow_capture_mutated'] is False and
         not disposition['true_user_scope_decisions_identified_now'], 'dtype CP02 role or false resolution drift')
    cp_gaps = unique(cp['gaps'], 'id', 'dtype companion evidence gap')
    need(set(cp_gaps) == set(disposition['ordinary_evidence_gap_ids']) ==
         {f'CP02-E{i:02}' for i in range(1, 9)} and not cp['true_user_decisions_identified_now'] and
         all(g['owner'] == 'atlas' and g['user_decision_required_now'] is False for g in cp_gaps.values()),
         'dtype CP02 evidence gap classification/conservation drift')
    gaps = original['remaining-gaps.json']
    need(len(gaps['gaps']) == 10 and len({r['id'] for r in gaps['gaps']}) == 10 and
         all(g['scope_reduction'] is False and g['user_decision_required_now'] is False for g in gaps['gaps']) and
         not gaps['true_irreconcilable_architecture_or_scope_decisions_proven'], 'dtype wider gap/decision drift')
    need(policy['new_public_ids_admitted'] == 0 and policy['whole_api_semantics_complete'] is False,
         'dtype policy cannot admit or specify whole APIs')
    return {'policy_version': index['version'], 'source_graphs': 8, 'finite_source_pairs': pairs,
            'source_clauses': 18, 'existing_endpoint_links': 9, 'unrun_acceptance_targets': 18,
            'open_wider_gaps': 10, 'ordinary_companion_evidence_gaps': 8,
            'source_blobs': 17, 'source_spans': 63, 'public_denominator_changed': False,
            'framework_execution_credit': 0, 'whole_API_closure_credit': 0,
            'source_packet_sha256': PACKET_SHA, 'source_review_sha256': REVIEW_SHA}, paths
