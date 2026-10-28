"""Bounded TensorFlow conversion source/analytical contracts, never runtime credit."""
import copy

from atlas_parity_dtype_headers import exact_fields
from atlas_parity_schema import fields, local_path, need, read_json, source_entry_at
from atlas_parity_tf_conversion_capture import (PREFIX, PACKET_SHA, REVIEW_SHA, FROZEN_ATLAS,
    FROZEN_TREE, TF_REVISION, KERAS_REVISION, capture)
from atlas_parity_tf_conversion_model import exact, project_case
from atlas_parity_tf_conversion_joins import expected_plan, validate_joins
from atlas_parity_tf_conversion_sources import validate_sources

NO_CREDIT = dict(public_denominator_changed=False, mapping_stage_changes=0,
    framework_execution_credit=0, provider_execution_credit=0, whole_API_semantics_complete=False,
    actual_implementation_owner=None, performance_credit=0, release_credit=0)


def source_counts(original):
    cases=original['acceptance-cases.json']['records']
    return dict(selected_source_blobs=len(original['source-receipts.json']['records']),
        portable_source_spans=len(original['source-witnesses.json']['records']),
        existing_API_identities=len(original['inputs/existing-api-identities.json']['records']),
        primary_unmapped_API_identities=1, existing_partial_API_identities=4, existing_unmapped_API_identities=6,
        source_clauses=len(original['proposal.json']['clauses']),
        supporting_source_distinctions=len(original['proposal.json']['supporting_distinctions']),
        future_cases_UNRUN=sum(c['status']=='UNRUN' for c in cases),
        open_gap_groups=sum(g['status']=='open' for g in original['remaining-gaps.json']['records']),
        runtime_cases_executed=0)


def prepare_tf_conversion(root, relative, program):
    need(relative==PREFIX+'index.json' and program['files'].get('tensorflow_conversion_boundary')==relative,
         'TF conversion program/index source role differs')
    file=local_path(root,relative);index=read_json(file)
    exact_fields(index, {'schema_version':int,'version':str,'introduced_in_program':str,
        'source_manifest_sha256':str,'source_review_sha256':str,'frozen_atlas_revision':str,
        'frozen_atlas_tree':str,'references':dict,'artifacts':list,'counts':dict,'status':dict,
        'source_review_scope':str}, 'TF conversion index')
    fixed=dict(schema_version=1,version='2026-10-26.1',introduced_in_program='2026-10-26.12',
        source_manifest_sha256=PACKET_SHA,source_review_sha256=REVIEW_SHA,
        frozen_atlas_revision=FROZEN_ATLAS,frozen_atlas_tree=FROZEN_TREE,
        references={'tensorflow':{'version':'2.21.0','revision':TF_REVISION},
                    'keras':{'version':'3.15.1','revision':KERAS_REVISION}},status=NO_CREDIT,
        source_review_scope='accepted_bounded_original_source_only_not_canonical_candidate_or_runtime_approval')
    need(exact({k:index[k] for k in fixed},fixed),'TF conversion exact version/no-credit/provenance differs')
    original,documents,paths=capture(root,index)
    actual=source_counts(original)
    need(exact(index['counts'],actual) and exact(actual,dict(selected_source_blobs=21,portable_source_spans=63,
        existing_API_identities=10,primary_unmapped_API_identities=1,existing_partial_API_identities=4,
        existing_unmapped_API_identities=6,source_clauses=11,supporting_source_distinctions=5,
        future_cases_UNRUN=30,open_gap_groups=10,runtime_cases_executed=0)), 'TF conversion typed count conservation differs')
    spec=original['contract-specification.json']
    need(exact(spec['proposal'],original['proposal.json']) and
         exact(spec['acceptance_cases'],original['acceptance-cases.json']) and
         exact(spec['gaps'],original['remaining-gaps.json']) and
         exact(spec['plan'],original['implementation-plan.json']), 'TF conversion immutable source/prototype relations differ')
    observation=original['inputs/atlas-observation.json']
    need(observation['head']==FROZEN_ATLAS and observation['tree']==FROZEN_TREE,
         'TF conversion historical canonical proof pin differs')
    need(all(g['status']=='open' for g in spec['gaps']['records']) and
         spec['gaps']['scope_exclusions']==[] and spec['gaps']['whole_api_complete'] is False and
         spec['gaps']['full_transitive_source_closure'] is False, 'TF conversion open source/gap scope differs')
    return root,index,original,documents,paths+[file]


def validate_cases(cases, original):
    prototype=original['contract-specification.json']['acceptance_cases']
    need(type(cases) is dict and cases.keys()==prototype.keys() and
         type(cases.get('records')) is list and len(cases['records'])==30,
         'TF conversion complete typed thirty-case schema required')
    expected=copy.deepcopy(prototype);rows=[]
    for case,source in zip(cases['records'],prototype['records']):
        fields(case,{'id':str,'input':dict,'expected':dict},'TF conversion source-parametric case')
        need(case['id']==source['id'],'TF conversion case identity/order differs')
        rows.append(project_case(case,source))
    expected['records']=rows
    need(exact(cases,expected),'TF conversion input-sensitive analytical/error/shape/identity/AD projection differs')
    return rows


def validate_tf_conversion(prepared, program, capabilities, repositories, packages, references, mappings, assigned):
    root,index,original,docs,paths=prepared
    def get(name):return docs[PREFIX+name]
    cases=get('cases.json');validate_cases(cases,original)
    validate_sources(get('source-proof.json'),original)
    reference_path=local_path(root,'reference/tensorflow.json');reference=read_json(reference_path)
    need(reference['version']=='2.21.0' and reference['source_revision']==TF_REVISION,
         'TF conversion exact frozen public reference differs')
    validate_joins(get('joins.json'),original,cases,capabilities,references,mappings,assigned,reference)
    need(exact(get('plan.json'),expected_plan(original,capabilities,repositories,packages)),
         'TF conversion current owner/DAG/null-approval/conditional-evidence/estimate plan differs')
    for row in get('joins.json')['records']:
        actual=row['canonical_API_mapping']
        if actual['state']=='mapped':
            contract=actual['mapping']['source_contract'];path=local_path(root,contract['path'])
            selected=source_entry_at(read_json(path),contract['entry'],'TF conversion current actual mapping source')
            need(selected['mapping_id']==actual['mapping']['id'] and selected['reference_id']==row['reference_id'],
                 'TF conversion current full mapping/source identity association differs')
            paths.append(path)
    return dict(source_counts(original), source_packet_sha256=PACKET_SHA, source_review_sha256=REVIEW_SHA,
        current_full_API_mapping_associations=4, primary_mapping_stage='unmapped',
        canonical_candidate_review='pending', mathematical_model='source_parametric_not_backend_evidence',
        **NO_CREDIT),paths+[reference_path]
