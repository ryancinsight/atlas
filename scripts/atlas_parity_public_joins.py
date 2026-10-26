"""Frozen source roles and live canonical ownership are different joins."""
from collections import Counter

from atlas_parity_public_capture import NO_CREDIT, exact, sha
from atlas_parity_dtype_headers import exact_fields
from atlas_parity_schema import need, source_entry_at, unique
from atlas_parity_tables import canonical, unpack

TABLE_METADATA = {'role': 'source_evidence_not_scope_or_semantic_admission',
                  'introduced_in_program': '2026-10-26.11'}


def association(identity, mappings, assigned):
    mid = assigned.get(identity)
    return dict(state='unmapped', reference_id=identity) if mid is None else dict(
        state='mapped', reference_id=identity, mapping_id=mid,
        capability=mappings[mid]['capability'], owner=mappings[mid]['owner'],
        stage=mappings[mid]['status']['mapping'])


def expected_joins(packets, references, scope, capabilities, mappings, assigned):
    rows = []
    for key in ('tf492', 'six'):
        records = packets[key]['dispositions.json' if key == 'tf492' else 'six-dispositions.json']['records']
        unique(records, 'reference_id', 'public evidence accepted identity')
        for position, original in enumerate(records):
            identity = original['reference_id']
            need(identity in references and identity in scope['bindings'], 'public evidence identity absent from live catalog')
            frozen = original['original_binding'] if key == 'tf492' else original['original']['binding']
            source = original['original_source_row'] if key == 'tf492' else original['original']['source_record']
            refhash = sha(canonical(references[identity]).encode())
            need(refhash == source['reference_sha256'], 'public evidence source/primary identity hash differs')
            if key == 'tf492':
                # Framework/version are attached by the canonical loader, not copied into raw primary rows.
                raw = {k:v for k,v in references[identity].items() if k not in ('framework','version')}
                exact(original['primary_record'], raw, 'public evidence TF exact primary/signature source')
            live = scope['bindings'][identity]
            exact(live,frozen,'public evidence existing canonical visibility/signature binding must be preserved')
            contract = scope['contracts'][live['contract']]
            route = {k:contract[k] for k in ('id', 'framework', 'capabilities', 'prerequisites',
                'route_state', 'planned_owner', 'implementation_owner_verified', 'semantic_definition_complete')}
            route['capability_suppliers'] = [dict(capability=cap, owner=capabilities[cap]['owner'],
                prerequisites=capabilities[cap]['prerequisites']) for cap in contract['capabilities']]
            rows.append(dict(reference_id=identity, reference_sha256=refhash, packet=key,
                source_artifact='dispositions.json' if key=='tf492' else 'six-dispositions.json',
                source_entry=['records',position], frozen_binding=frozen,
                frozen_source_route=packets['tf492']['ownership-route-comparison.json']['records'][position]
                    if key=='tf492' else original['owner_route'],
                source_proposal=original['proposal'] if key=='tf492' else dict(
                    disposition=original['proposed_source_disposition'],
                    required_functionality_retained=original['required_functionality_retained']),
                live_binding=live, live_contract_route=route,
                live_API_mapping=association(identity,mappings,assigned),
                actual_implementation_owner=None, source_review_applies_to='original_packet_only',
                out_of_scope_admission_applied=False, required_workflow_obligations_retained=True,
                status=NO_CREDIT))
    return rows


def validate_joins(document, packets, references, scope, capabilities, mappings, assigned):
    exact_fields(document,{'format':str,'metadata':dict,'columns':list,'tables':dict,'rows':list},
                 'public evidence join table')
    exact(document['metadata'], TABLE_METADATA, 'public evidence joins role')
    rows = unpack(document)
    need(len(rows)==498 and len({r['reference_id'] for r in rows})==498,
         'public evidence candidate identity/count conservation differs')
    # Validate selectors before any equality: bool/float aliases are never list offsets.
    for row in rows:
        exact_fields(row,{'reference_id':str,'reference_sha256':str,'packet':str,'source_artifact':str,
            'source_entry':list,'frozen_binding':dict,'frozen_source_route':dict,'source_proposal':dict,
            'live_binding':dict,'live_contract_route':dict,'live_API_mapping':dict,
            'actual_implementation_owner':type(None),'source_review_applies_to':str,
            'out_of_scope_admission_applied':bool,'required_workflow_obligations_retained':bool,'status':dict},
            'public evidence typed join')
        need(row['packet'] in ('tf492','six'), 'public evidence unknown source packet')
        need(row['source_artifact']==('dispositions.json' if row['packet']=='tf492' else 'six-dispositions.json'),
             'public evidence source artifact role differs')
        selected = source_entry_at(packets[row['packet']][row['source_artifact']], row['source_entry'],
                                   'public evidence typed source selector')
        need(type(selected) is dict and selected.get('reference_id') == row['reference_id'],
             'public evidence source selector/identity differs')
    expected = expected_joins(packets,references,scope,capabilities,mappings,assigned)
    exact(rows,expected,'public evidence frozen/source/live ownership joins')
    selected = {r['reference_id'] for r in rows}
    unresolved = {i for i,b in scope['bindings'].items() if b['visibility']=='publicness_unresolved'}
    need(selected == unresolved, 'public evidence all498 unresolved live identities must remain conserved')
    need(all(r['live_binding']['retained_obligation'] and r['live_API_mapping']['state']=='unmapped' for r in rows),
         'public evidence slice cannot discharge obligations or promote canonical mappings')
    proposals = Counter(r['source_proposal']['admission_category'] for r in rows if r['packet']=='tf492')
    exact(dict(proposals),dict(internal_implementation_identity=6, required_operator_extension_or_protocol_view=5,
        required_extension_namespace_grouping_view=1,publicness_unresolved=480), 'public evidence TF proposal accounting')
    return dict(existing_reference_links=len(rows), unresolved_publicness_retained=len(selected),
                TF_proposal_categories=dict(proposals))
