"""Torch source roles: existing API mapping, facade proposal and numeric supplier."""
from atlas_parity_dtype import mapping_association, policy_supplier
from atlas_parity_dtype_headers import exact_fields
from atlas_parity_schema import need, source_entry_at
from atlas_parity_tables import canonical

ROLE = 'actual_canonical_API_mapping_separate_from_facade_proposal_and_numeric_policy_supplier'


def expected_joins(contracts, cases, capabilities, mappings, assigned):
    cap = capabilities['NUM-PROMOTE']
    supplier = dict(capability='NUM-PROMOTE', owner=cap['owner'], prerequisites=cap['prerequisites'])
    records = []
    for index, contract in enumerate(contracts['records']):
        records.append({'id': contract['id'], 'reference_id': contract['api_identity'],
            'symbol': contract['reference_record']['symbol'], 'source_entry': ['records', index],
            'canonical_API_mapping': mapping_association(contract['api_identity'], mappings, assigned),
            'facade_proposal': {'capability': 'TEN-OPS', 'owner': 'coeus', 'role': 'planning_proposal_not_canonical_API_accountable_owner'},
            'policy_supplier': supplier, 'actual_implementation_owner': None,
            'source_citations': contract['source_refs'], 'case_ids': contract['analytical_case_ids'],
            'open_gap_ids': contract['open_gap_ids'], 'whole_API_or_mapping_credit': False})
    return {'schema_version': 1, 'ownership_roles': ROLE, 'records': records,
        'cases': [{'id': c['id'], 'contract_id': c['contract_id'], 'source_entry': ['records', i],
                   'runtime_executed': False} for i, c in enumerate(cases['records'])]}


def validate_joins(document, contracts, cases, bindings, capabilities, references, mappings, assigned):
    exact_fields(document, {'schema_version': int, 'ownership_roles': str, 'records': list, 'cases': list}, 'Torch joins header')
    need(document['schema_version'] == 1 and document['ownership_roles'] == ROLE and
         len(document['records']) == 10 and len(document['cases']) == 66, 'Torch role/count conservation differs')
    for i, row in enumerate(document['records']):
        exact_fields(row, {'id': str, 'reference_id': str, 'symbol': str, 'source_entry': list,
            'canonical_API_mapping': dict, 'facade_proposal': dict, 'policy_supplier': dict,
            'actual_implementation_owner': type(None), 'source_citations': list, 'case_ids': list,
            'open_gap_ids': list, 'whole_API_or_mapping_credit': bool}, 'Torch typed endpoint roles')
        selected = source_entry_at(contracts, row['source_entry'], 'Torch typed source selector endpoint')
        need(row['source_entry'] == ['records', i] and selected is contracts['records'][i] and
             selected['id'] == row['id'], 'Torch typed source selector endpoint identity differs')
        identity = row['reference_id']
        need(identity in references and row['symbol'] == references[identity]['symbol'], 'Torch admitted ID join differs')
        policy_supplier(row['policy_supplier'], 'NUM-PROMOTE', capabilities)
        exact_fields(row['facade_proposal'], {'capability': str, 'owner': str, 'role': str}, 'Torch facade proposal')
        need(row['canonical_API_mapping'] == mapping_association(identity, mappings, assigned) and
             row['actual_implementation_owner'] is None and row['whole_API_or_mapping_credit'] is False,
             'Torch actual mapping cannot be replaced by facade/supplier or qualification')
    for i, row in enumerate(document['cases']):
        exact_fields(row, {'id': str, 'contract_id': str, 'source_entry': list, 'runtime_executed': bool}, 'Torch case role')
        selected = source_entry_at(cases, row['source_entry'], 'Torch typed source selector case')
        need(row['source_entry'] == ['records', i] and selected is cases['records'][i] and
             selected['id'] == row['id'], 'Torch typed source selector case identity differs')
        need(row['runtime_executed'] is False, 'Torch case execution credit forbidden')
    need(canonical(document) == canonical(expected_joins(contracts, cases, capabilities, mappings, assigned)),
         'Torch source/API/case/facade/supplier exact relation differs')
    ids = {r['api_identity'] for r in bindings['records']}
    need(ids == {r['reference_id'] for r in document['records']} and len(ids) == 10,
         'Torch existing admitted identity conservation differs')
