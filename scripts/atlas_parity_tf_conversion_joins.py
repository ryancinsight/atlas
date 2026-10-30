"""Live API/supplier joins, separate from immutable fd0 planning context."""
import copy

from atlas_parity_dtype_headers import exact_fields
from atlas_parity_schema import api_identity, need, source_entry_at, source_selector
from atlas_parity_tf_conversion_model import exact
from atlas_parity_tf_conversion_capture import FROZEN_ATLAS, FROZEN_TREE, TF_REVISION, KERAS_REVISION

ROLE = 'current_API_mapping_not_facade_or_policy_supplier_no_new_mapping'


def relevant_caps(original, capabilities):
    historical = original['inputs/capability-roles.json']['records']
    result = []
    for row in historical:
        key = row['id'];need(key in capabilities, 'TF conversion current capability absent')
        current = capabilities[key]
        need(exact({k:current[k] for k in ('owner','prerequisites')},
                   {k:row[k] for k in ('owner','prerequisites')}),
             'TF conversion reviewed architecture owner/prerequisite changed; explicit new review required')
        result.append({k:current[k] for k in ('id','owner','prerequisites','target_revision')})
    return result


def expected_joins(original, cases, capabilities, references, mappings, assigned, reference_document):
    supplier = capabilities['NUM-PROMOTE']
    policy = {k:supplier[k] for k in ('owner','prerequisites')};policy['capability']='NUM-PROMOTE'
    policy['role']='scalar_dtype_policy_only_not_whole_public_API_or_Keras_autocast_ownership'
    records = []
    for i, source in enumerate(original['inputs/existing-api-identities.json']['records']):
        identity = source['api_identity'];need(identity in references, 'TF conversion existing reference ID absent')
        admitted = source['admitted_record']
        need(exact(references[identity], dict(admitted, framework='tensorflow', version='2.21.0')),
             'TF conversion existing reference signature/source/metadata differs')
        matches = [n for n,r in enumerate(reference_document['records'])
                   if api_identity('tensorflow','2.21.0',r)==identity]
        need(len(matches)==1, 'TF conversion current raw reference occurrence differs')
        mapping_id = assigned.get(identity)
        current = [mappings[mapping_id]] if mapping_id is not None else []
        need(exact(current,source['mapping_associations']),
             'TF conversion full current API mapping differs from independently reviewed association/stage')
        records.append({'reference_id':identity,'symbol':admitted['symbol'],'source_entry':['records',i],
            'reference_entry':['records',matches[0]],
            'reference_source_owner':{'repository':'keras-team/keras','revision':KERAS_REVISION} if 'keras-team/keras/' in admitted['source'] else {'repository':'tensorflow/tensorflow','revision':TF_REVISION},
            'public_API_accountable_owner':current[0]['owner'] if current else None,
            'workspace_kernel_implementation_owner':None,
            'canonical_API_mapping': {'state':'mapped','mapping':copy.deepcopy(current[0])} if current else {'state':'unmapped','reference_id':identity},
            'policy_supplier':copy.deepcopy(policy),
            'facade_proposal':{'owner':'coeus','capability':'TEN-CORE','approved':False,
                'role':'primary_tensor_facade_proposal_not_actual_API_or_implementation_owner'} if admitted['symbol']=='tf.convert_to_tensor' else None,
            'actual_implementation_owner':None,
            'case_ids':[c['id'] for c in cases['records'] if identity in c['api_identity_refs']],
            'new_mapping_or_stage_credit':False})
    return {'schema_version':1,'ownership_roles':ROLE,'records':records,
        'cases':[{'id':c['id'],'source_entry':['records',i],'runtime_executed':False}
                 for i,c in enumerate(cases['records'])]}


def expected_plan(original, capabilities, repositories, packages):
    result = copy.deepcopy(original['implementation-plan.json'])
    result['existing_capability_dag'] = relevant_caps(original,capabilities)
    result['context'] = {'frozen_source_revision':FROZEN_ATLAS,'frozen_source_tree':FROZEN_TREE,
        'historical_context_role':'immutable_provenance_not_current_task_or_owner_authority',
        'live_owner_source':'current_canonical_capabilities_repositories_mappings_and_work_packages',
        'uses_historical_task_ownership_for_current_authority':False,
        'current_supplier_revisions':{r['owner']:repositories[r['owner']]['candidate_revision'] for r in result['roles']},
        'current_parent_work_packages':[{k:packages[p][k] for k in ('id','owner','capabilities','dependencies')}
                                      for p in result['parent_packages']]}
    return result


def validate_joins(document, original, cases, capabilities, references, mappings, assigned, reference_document):
    exact_fields(document,{'schema_version':int,'ownership_roles':str,'records':list,'cases':list},'TF conversion joins')
    need(type(document) is dict and type(document.get('records')) is list and len(document['records'])==10,
         'TF conversion ten exact existing joins required')
    bindings = original['inputs/existing-api-identities.json']
    for i,row in enumerate(document['records']):
        need(type(row) is dict,'TF conversion join row must be an object')
        exact_fields(row,{'reference_id':str,'symbol':str,'source_entry':list,'reference_entry':list,
            'reference_source_owner':dict,'public_API_accountable_owner':type(None) if row.get('public_API_accountable_owner') is None else str,
            'workspace_kernel_implementation_owner':type(None),'canonical_API_mapping':dict,'policy_supplier':dict,
            'facade_proposal':type(None) if row.get('facade_proposal') is None else dict,
            'actual_implementation_owner':type(None),'case_ids':list,'new_mapping_or_stage_credit':bool},'TF conversion typed join row')
        actual_mapping=row['canonical_API_mapping']
        need(actual_mapping.get('state') in {'mapped','unmapped'},'TF conversion actual mapping state differs')
        exact_fields(actual_mapping,{'state':str,'mapping':dict} if actual_mapping['state']=='mapped'
                     else {'state':str,'reference_id':str},'TF conversion actual mapping role')
        exact_fields(row['policy_supplier'],{'owner':str,'prerequisites':list,'capability':str,'role':str},'TF conversion scalar policy role')
        selected = source_entry_at(bindings,row.get('source_entry'),'TF conversion source selector')
        actual = source_entry_at(reference_document,row.get('reference_entry'),'TF conversion reference selector')
        need(selected is bindings['records'][i] and selected['api_identity']==row.get('reference_id') and
             api_identity('tensorflow','2.21.0',actual)==row.get('reference_id'),
             'TF conversion typed source/reference row association differs')
        for mapping in ([row['canonical_API_mapping'].get('mapping')] if row['canonical_API_mapping'].get('state')=='mapped' else []):
            need(type(mapping) is dict, 'TF conversion full actual mapping required')
            contract=mapping.get('source_contract')
            exact_fields(contract,{'path':str,'sha256':str,'entry':list},'TF conversion current mapping source role')
            source_selector(contract['entry'], 'TF conversion current mapping source selector')
    need(type(document.get('cases')) is list and len(document['cases'])==30,'TF conversion thirty case selectors required')
    for i,row in enumerate(document['cases']):
        exact_fields(row,{'id':str,'source_entry':list,'runtime_executed':bool},'TF conversion typed case link')
        selected = source_entry_at(cases,row.get('source_entry'),'TF conversion case selector')
        need(selected is cases['records'][i] and selected['id']==row.get('id'), 'TF conversion exact case row association differs')
    expected = expected_joins(original,cases,capabilities,references,mappings,assigned,reference_document)
    need(exact(document,expected),'TF conversion current full API/owner/supplier/case join differs')
