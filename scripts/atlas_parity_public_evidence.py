"""Admit accepted source evidence without applying public-scope exemptions."""
from atlas_parity_dtype_headers import exact_fields
from atlas_parity_public_capture import (PREFIX,PACKETS,FROZEN_ATLAS,NO_CREDIT,
    ADMISSION_MANIFEST_SHA,capture,exact,sha)
from atlas_parity_public_joins import validate_joins
from atlas_parity_public_sources import validate_tf, validate_six
from atlas_parity_schema import local_path,need,read_json

COUNTS=dict(existing_reference_links=498,TF_records=492,JAX_records=3,Torch_records=3,
    TF_source_files=155,TF_source_spans=747,six_source_files=15,six_source_spans=1010,
    tooling_source_receipts=74,tooling_AST_fingerprints=56,tooling_callable_views_not_new_IDs=974,
    TF_workflow_groups=19,TF_unresolved_publicness=480,TF_open_member_selectors=211,
    admission_certificates_applied=0)


def prepare_public_evidence(root,relative,program):
    need(relative==PREFIX+'index.json' and program['files'].get('public_evidence')==relative,
         'public evidence program source-role association differs')
    path=local_path(root,relative);index=read_json(path)
    exact_fields(index,{'schema_version':int,'version':str,'introduced_in_program':str,
        'packets':dict,'artifacts':list,'counts':dict,'status':dict,'joins':str,'witnesses':str,
        'admission_design':dict,'original_review_scope':str,'full_public_surface_complete':bool,
        'semantic_definition_complete':bool},'public evidence index')
    expected=dict(schema_version=1,version='2026-10-26.1',introduced_in_program='2026-10-26.11',
        packets={k:PREFIX+c['directory']+'/index.json' for k,c in PACKETS.items()},
        counts=COUNTS,status=NO_CREDIT,joins=PREFIX+'joins.json',witnesses=PREFIX+'six-portable-witnesses.json',
        admission_design=dict(manifest=PREFIX+'admission-design/manifest.json',sha256=ADMISSION_MANIFEST_SHA,applied=False),
        original_review_scope='original_packets_only_canonical_exact_head_review_pending',
        full_public_surface_complete=False,semantic_definition_complete=False)
    exact({k:index[k] for k in expected},expected,'public evidence typed metadata/counts/no credit')
    paths=[path];documents={}
    for row in index['artifacts']:
        exact_fields(row,{'path':str,'sha256':str},'public evidence indexed artifact')
        file=local_path(root,row['path'])
        need(row['path'].startswith(PREFIX) and file not in paths and sha(file.read_bytes())==row['sha256'],
             'public evidence artifact hash/role/duplicate differs')
        paths.append(file);documents[row['path']]=read_json(file) if file.suffix=='.json' else file.read_text()
    manifest_path=PREFIX+'admission-design/manifest.json'
    need(manifest_path in documents and sha(local_path(root,manifest_path).read_bytes())==ADMISSION_MANIFEST_SHA,
         'public evidence independent admission design binding differs')
    design=documents[manifest_path]
    need(design['canonical_changes'] is False and design['new_gate_or_admission_changes'] is False and
         design['reviewed_revision']==FROZEN_ATLAS,'public evidence design cannot apply admission/gate relief')
    for name,digest in design['files'].items():
        full=PREFIX+'admission-design/'+name
        need(full in documents and sha(local_path(root,full).read_bytes())==digest,
             'public evidence accepted design source/certificate differs')
    roles={index['joins'],index['witnesses'],manifest_path,*index['packets'].values()}
    roles|={PREFIX+'admission-design/'+n for n in design['files']}
    need(set(documents)==roles,'public evidence indexed artifact role set differs')
    packets={};manifests={}
    for key,relative in index['packets'].items():
        original,files=capture(root,key,relative);packets[key]=original;paths.extend(files)
        manifests[key]=read_json(local_path(root,PREFIX+PACKETS[key]['directory']+'/source-manifest.json'))
    return root,index,packets,manifests,documents,paths


def validate_public_evidence(prepared,program,references,scope,capabilities,mappings,assigned):
    root,index,packets,manifests,documents,paths=prepared
    # All original classifications/signatures/obligations remain in existing authoritative tables.
    need(all(s['public_surface_complete'] is False and s['semantics_complete'] is False
             for s in program['reference_snapshots']), 'public evidence cannot close any framework denominator')
    tf=validate_tf(packets['tf492'],manifests['tf492'])
    six=validate_six(packets['six'],manifests['six'],documents[index['witnesses']])
    joined=validate_joins(documents[index['joins']],packets,references,scope,capabilities,mappings,assigned)
    return dict({**COUNTS,**tf,**six,**joined,**NO_CREDIT},
        version=index['version'],introduced_in_program=index['introduced_in_program'],
        frozen_source_Atlas_revision=FROZEN_ATLAS,
        original_source_reviews_only=True,canonical_exact_head_review_required=True,
        remaining_definition_gaps=['480 TF publicness questions','211 TF inherited/generated/native selectors',
            'six JAX/Torch publicness/stability questions','JAX rendered HTTP403 route stopped',
            'actual resolved documentation environment/callbacks unavailable',
            'three NumPy internal proposals lack admission certificates',
            'complete per-signature semantics and runtime/provider/hardware/release qualification']),paths
