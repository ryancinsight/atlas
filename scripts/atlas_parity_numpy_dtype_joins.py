"""NumPy source families, unrun cases, suppliers and existing API associations."""
from atlas_parity_dtype import mapping_association, policy_supplier
from atlas_parity_dtype_headers import exact_fields
from atlas_parity_schema import need, source_entry_at, unique

FAMILY_SUPPLIERS = {'native:argument-and-dispatch': 'INTEROP-DISPATCH',
                    'native:descriptor-coercion': 'NUM-REP',
                    'native:new-and-custom-dtypes': 'NUM-REP'}
GROUPS = {
 'argument-and-dispatch': ['no-arguments', 'positional-only-keyword', 'target-none-before-python-value-error',
    'casting-error-before-missing-from', 'unknown-keyword-before-converter', 'casting-parameter-order-not-keyword-order',
    'outer-override-body-error-not-suppressed', 'outer-type-object-lookup-error-cleared', 'outer-noncallable-override-is-not-absent'],
 'casting-mode': ['same-value-not-accepted-here', 'casting-spelling-exact', 'casting-invalid-utf8-bytes', 'casting-nonstring-no-str-coercion',
    'casting-error-before-missing-from', 'casting-parameter-order-not-keyword-order'],
 'descriptor-coercion': ['none-converter2', 'python-type-versus-value', 'dtype-hook-error-not-suppressed',
    'dtype-hook-none-is-invalid-present', 'ctypes-pointer-dtype-rejection', 'ctypes-structure-bitfield-rejection', 'ctypes-probe-error-disposition'],
 'common-dtype': ['metadata-identical-fastpath', 'metadata-distinct-nonparametric', 'nonassociative-string', 'python-type-versus-value'],
 'promote-types': ['metadata-identical-fastpath', 'metadata-distinct-nonparametric', 'string-width', 'nonassociative-string',
    'void-length-mismatch', 'subarray-shape-mismatch', 'structured-names-mismatch', 'structured-padding-recomputed',
    'structured-titles-mismatch', 'temporal-gcd', 'timedelta-nonlinear-barrier'],
 'weak-result-type': ['single-huge-int-discovery', 'multi-huge-int-weak', 'python-type-versus-value', 'single-canonical-byteorder', 'weak-tags-exact-types'],
 'can-cast': ['dtype-query-no-payload-representability-proof', 'python-numeric-value-rejected', 'target-none-before-python-value-error',
    'byteorder-equiv-vs-no', 'structured-renamed-field-policy', 'void-width-relations', 'object-direction', 'datetime-safe-multiplier',
    'timedelta-same-kind-barrier', 'resolver-error-cleared-only-at-query-boundary', 'advertised-safe-bypasses-resolver',
    'stringdtype-unspecified-output-fastpath', 'temporal-metric-quotient-source-question'],
 'legacy-tables': ['dtype-query-no-payload-representability-proof'],
 'parametric-casts': ['string-width', 'void-length-mismatch', 'subarray-shape-mismatch', 'structured-names-mismatch',
    'structured-padding-recomputed', 'structured-titles-mismatch', 'temporal-gcd', 'timedelta-nonlinear-barrier',
    'byteorder-equiv-vs-no', 'structured-renamed-field-policy', 'void-width-relations', 'object-direction',
    'datetime-safe-multiplier', 'timedelta-same-kind-barrier', 'temporal-metric-quotient-source-question'],
 'new-and-custom-dtypes': ['stringdtype-unspecified-output-fastpath', 'resolver-error-cleared-only-at-query-boundary',
    'advertised-safe-bypasses-resolver', 'ctypes-pointer-dtype-rejection', 'ctypes-structure-bitfield-rejection',
    'ctypes-probe-error-disposition', 'dtype-hook-error-not-suppressed', 'dtype-hook-none-is-invalid-present']}
ENDPOINT_FAMILIES = {
 'numpy.can_cast': ['argument-and-dispatch', 'casting-mode', 'descriptor-coercion', 'can-cast', 'legacy-tables', 'parametric-casts', 'new-and-custom-dtypes'],
 'numpy.promote_types': ['argument-and-dispatch', 'descriptor-coercion', 'common-dtype', 'promote-types', 'legacy-tables', 'parametric-casts', 'new-and-custom-dtypes'],
 'numpy.result_type': ['argument-and-dispatch', 'descriptor-coercion', 'common-dtype', 'weak-result-type', 'legacy-tables', 'parametric-casts', 'new-and-custom-dtypes'],
 'numpy.dtype': ['descriptor-coercion', 'new-and-custom-dtypes'],
 'PyArray_CanCastTypeTo': ['casting-mode', 'can-cast', 'legacy-tables', 'parametric-casts', 'new-and-custom-dtypes'],
 'PyArray_PromoteTypes': ['common-dtype', 'promote-types', 'legacy-tables', 'parametric-casts', 'new-and-custom-dtypes'],
 'PyArray_ResultType': ['common-dtype', 'weak-result-type', 'legacy-tables', 'parametric-casts', 'new-and-custom-dtypes'],
 'PyArray_DescrConverter2': ['descriptor-coercion', 'new-and-custom-dtypes']}
ROLE = 'source_policy_suppliers_and_actual_canonical_API_mappings_no_new_mapping_or_qualification'


def supplier(capability, capabilities):
    need(capability in capabilities, 'NumPy proposed supplier capability absent')
    row = capabilities[capability]
    return dict(capability=capability, owner=row['owner'], prerequisites=row['prerequisites'])


def expected_joins(policy, cases, witnesses, capabilities, mappings, assigned):
    endpoints = []
    for group, role in [('public_entrypoints', 'primary_entrypoint'), ('supporting_admitted_ids', 'supporting_existing_ID')]:
        for symbol, row in policy[group].items():
            endpoints.append({'reference_id': row['reference_id'], 'symbol': symbol, 'role': role,
                'admission': row['admission'], 'source_entry': [group, symbol],
                'family_ids': ['native:' + x for x in ENDPOINT_FAMILIES[symbol]],
                'policy_supplier': supplier('NUM-PROMOTE', capabilities),
                'canonical_API_mapping': mapping_association(row['reference_id'], mappings, assigned),
                'complete_API_mapping_credit': False, 'semantic_completion_credit': False})
    families = []
    for i, family in enumerate(policy['families']):
        identity = family['id']
        names = GROUPS[identity.removeprefix('native:')]
        families.append({'id': identity, 'source_entry': ['families', i],
            'planned_component': family['planned_component'], 'planned_owner': family['planned_owner'],
            'assignment': 'definition_planning_only_no_codeowner_or_implementation_ADR_approval',
            'policy_supplier': supplier(FAMILY_SUPPLIERS.get(identity, 'NUM-PROMOTE'), capabilities),
            'source_function_ids': family['functions'],
            'source_citations': list(dict.fromkeys(witnesses['functions'][f]['source'] for f in family['functions'])),
            'upstream_family_ids': [x for x in family['prerequisites'] if x.startswith('native:')],
            'upstream_capability_ids': [x for x in family['prerequisites'] if x in capabilities],
            'unresolved_source_prerequisites': [x for x in family['prerequisites'] if not x.startswith('native:') and x not in capabilities],
            'related_existing_reference_ids': [x['reference_id'] for x in endpoints if identity in x['family_ids']],
            'case_ids': [c['id'] for c in cases['cases'] if c['id'].removeprefix('numpy-dtype:') in names],
            'actual_implementation_owner': None, 'source_mapping_complete': False, 'runtime_cases_executed': 0})
    case_links = [{'id': c['id'], 'source_entry': ['cases', i], 'reference_id': c['reference_id'],
        'related_family_ids': ['native:' + name for name, values in GROUPS.items()
                               if c['id'].removeprefix('numpy-dtype:') in values],
        'source_relation_scope': 'reviewable_related_source_families_not_case_execution_or_complete_call_graph',
        'runtime_executed': False} for i, c in enumerate(cases['cases'])]
    return {'schema_version': 1, 'ownership_roles': ROLE, 'cases_are_unrun': True,
            'endpoints': endpoints, 'families': families, 'cases': case_links}


def validate_joins(document, policy, cases, witnesses, capabilities, references, mappings, assigned):
    exact_fields(document, {'schema_version': int, 'ownership_roles': str, 'cases_are_unrun': bool,
        'endpoints': list, 'families': list, 'cases': list}, 'NumPy native canonical role joins')
    need(document['schema_version'] == 1 and document['ownership_roles'] == ROLE and document['cases_are_unrun'] is True,
         'NumPy native role/credit drift')
    need(policy['whole_api_semantics_complete'] is False and type(policy['provider_runtime_executions']) is int and
         type(policy['reference_runtime_executions']) is int and policy['provider_runtime_executions'] ==
         policy['reference_runtime_executions'] == 0, 'NumPy captured contract runtime/whole API credit forbidden')
    endpoints = unique(document['endpoints'], 'reference_id', 'NumPy endpoint role')
    need(len(endpoints) == 8 and len(policy['public_entrypoints']) == 3 and len(policy['supporting_admitted_ids']) == 5,
         'NumPy existing primary/supporting ID conservation drift')
    for group in ('public_entrypoints', 'supporting_admitted_ids'):
        for symbol, original in policy[group].items():
            identity = original['reference_id']
            need(identity in references and references[identity]['symbol'] == symbol and
                 all(references[identity][k] == v for k, v in original['record'].items()),
                 'NumPy existing admitted record/source association drift')
    for row in endpoints.values():
        exact_fields(row, {'reference_id': str, 'symbol': str, 'role': str, 'admission': str, 'source_entry': list,
            'family_ids': list, 'policy_supplier': dict, 'canonical_API_mapping': dict,
            'complete_API_mapping_credit': bool, 'semantic_completion_credit': bool}, 'NumPy endpoint typed role')
        group = {'primary_entrypoint': 'public_entrypoints',
                 'supporting_existing_ID': 'supporting_admitted_ids'}.get(row['role'])
        selected = source_entry_at(policy, row['source_entry'], 'NumPy endpoint source entry')
        need(group is not None and row['source_entry'] == [group, row['symbol']] and
             type(selected) is dict and selected['reference_id'] == row['reference_id'],
             'NumPy endpoint source entry/identity drift')
        policy_supplier(row['policy_supplier'], 'NUM-PROMOTE', capabilities)
        association = row['canonical_API_mapping']
        kinds = {'state': str, 'reference_id': str}
        if association.get('state') == 'mapped':
            kinds.update(mapping_id=str, capability=str, owner=str)
        exact_fields(association, kinds, 'NumPy actual canonical API association')
        need(association == mapping_association(row['reference_id'], mappings, assigned),
             'NumPy actual API mapping association differs; policy supplier cannot replace owner')
        need(row['complete_API_mapping_credit'] is False and row['semantic_completion_credit'] is False,
             'NumPy endpoint qualification credit forbidden')
    functions = witnesses['functions']
    source_families = unique(policy['families'], 'id', 'NumPy captured family')
    family_positions = {row['id']: position for position, row in enumerate(policy['families'])}
    need(len(source_families) == len(document['families']) == 10, 'NumPy native family conservation drift')
    for row in document['families']:
        exact_fields(row, {'id': str, 'source_entry': list, 'planned_component': str, 'planned_owner': str,
            'assignment': str, 'policy_supplier': dict, 'source_function_ids': list, 'source_citations': list,
            'upstream_family_ids': list, 'upstream_capability_ids': list, 'unresolved_source_prerequisites': list,
            'related_existing_reference_ids': list,
            'case_ids': list, 'actual_implementation_owner': type(None), 'source_mapping_complete': bool,
            'runtime_cases_executed': int}, 'NumPy family typed source/owner role')
        need(row['id'] in source_families, 'NumPy family source identity absent')
        original = source_families[row['id']]
        selected = source_entry_at(policy, row['source_entry'], 'NumPy family source entry')
        need(row['source_entry'] == ['families', family_positions[row['id']]] and selected is original,
             'NumPy family source entry/identity drift')
        policy_supplier(row['policy_supplier'], FAMILY_SUPPLIERS.get(row['id'], 'NUM-PROMOTE'), capabilities)
        need(row['planned_owner'] == original['planned_owner'] and
             set(row['source_function_ids']) <= functions.keys() and row['source_function_ids'] and
             set(row['upstream_family_ids']) <= source_families.keys() and
             set(row['upstream_capability_ids']) <= capabilities.keys(), 'NumPy family supplier/function/prerequisite join drift')
        status = original['status']
        exact_fields(status, {'source': str, 'implementation': str, 'reference_tests': str, 'provider_tests': str,
            'performance': str, 'release': str, 'whole_api_complete': bool}, 'NumPy captured family status')
        need(status == dict(source='bounded_branch_composition_defined', implementation='not_assessed',
             reference_tests='unrun', provider_tests='unrun', performance='unrun', release='not_assessed', whole_api_complete=False),
             'NumPy family source-only status drift')
    need(cases['execution_status'] == 'all_unrun' and len(cases['cases']) == len(document['cases']) == 47 and
         len({c['id'] for c in cases['cases']}) == 47, 'NumPy acceptance case count/status drift')
    source_cases = unique(cases['cases'], 'id', 'NumPy captured case')
    case_positions = {row['id']: position for position, row in enumerate(cases['cases'])}
    for row in cases['cases']:
        need(row['status'] == 'unrun' and row['reference_evidence'] is None and row['provider_evidence'] is None and
             row['no_runtime_or_semantic_promotion'] is True and row['reference_id'] in endpoints,
             'NumPy acceptance execution/qualification credit forbidden')
    for row in document['cases']:
        exact_fields(row, {'id': str, 'source_entry': list, 'reference_id': str, 'related_family_ids': list,
            'source_relation_scope': str, 'runtime_executed': bool}, 'NumPy case typed relation')
        need(row['id'] in source_cases, 'NumPy case source identity absent')
        selected = source_entry_at(cases, row['source_entry'], 'NumPy case source entry')
        need(row['source_entry'] == ['cases', case_positions[row['id']]] and
             selected is source_cases[row['id']] and selected['reference_id'] == row['reference_id'],
             'NumPy case source entry/identity drift')
        need(row['related_family_ids'] and row['runtime_executed'] is False,
             'NumPy case source relation absent or runtime credit')
    need(document == expected_joins(policy, cases, witnesses, capabilities, mappings, assigned),
         'NumPy exact family/entry/case/ID/ownership relation drift')
    return len(endpoints)
