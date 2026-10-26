"""Capture two accepted local public-evidence packets; no source acquisition/import."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlas_parity_public_capture import (PREFIX, PACKETS, FROZEN_ATLAS, NO_CREDIT,
    ADMISSION_MANIFEST_SHA, manifest_files, original_bytes, sha)
from atlas_parity_public_joins import expected_joins, TABLE_METADATA
from atlas_parity_public_sources import source_witnesses
from atlas_parity_tables import pack


def encode(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()


def checked_packet(path, config):
    data=(path/config['manifest']).read_bytes()
    assert sha(data)==config['manifest_sha256'],'accepted source packet pin'
    manifest=json.loads(data)
    for name, receipt in manifest_files(manifest).items():
        content=(path/name).read_bytes()
        assert sha(content)==receipt['sha256'] and len(content)==receipt['bytes'],name
    return data,manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('tf-packet','tf-review','six-packet','six-review','admission-design'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--atlas-root',type=Path,default=Path(__file__).resolve().parents[2])
    args=parser.parse_args(); root=args.atlas_root.resolve()/'docs/parity'; dest=root/PREFIX
    inputs={'tf492':(args.tf_packet,args.tf_review),'six':(args.six_packet,args.six_review)}
    def raw(relative,data):
        path=dest/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    def write(relative,value):raw(relative,encode(value))
    packets={}; packet_indexes={}
    for key,config in PACKETS.items():
        packet,review=inputs[key]; manifest_bytes,manifest=checked_packet(packet,config)
        review_bytes=review.read_bytes();assert sha(review_bytes)==config['review_sha256']
        directory=config['directory']+'/'
        raw(directory+'source-manifest.json',manifest_bytes)
        raw(directory+'independent-review.json',review_bytes)
        selected=[]; original={}
        for name,collection in sorted(config['selected'].items()):
            data=(packet/name).read_bytes()
            if name=='README.md':
                value=data.decode(); paths=[directory+'captured/README.source.txt']
                raw(paths[0],data); storage=serialization='original-bytes'
            else:
                value=json.loads(data)
                serialization='compact-unicode' if key=='tf492' else 'pretty-ascii'
                if original_bytes(value,serialization)!=data:
                    paths=[directory+'captured/'+name]; raw(paths[0],data)
                    storage=serialization='original-bytes'
                elif collection is not None:
                    metadata={k:v for k,v in value.items() if k!=collection}
                    stem=name.removesuffix('.json')
                    paths=[directory+'captured/'+stem+'.metadata.json',directory+'captured/'+stem+'.records.json']
                    write(paths[0],metadata)
                    write(paths[1],pack(value[collection],dict(packet=key,original_path=name,collection=collection)))
                    storage='column-records'
                else:
                    paths=[directory+'captured/'+name];write(paths[0],value);storage='compact-json'
            original[name]=value
            selected.append(dict(original_path=name,paths=[PREFIX+p for p in paths],storage=storage,
                collection=collection,serialization=serialization,original_sha256=sha(data)))
        packets[key]=original
        artifacts=[dict(path=path.relative_to(root).as_posix(),sha256=sha(path.read_bytes()))
            for path in sorted((dest/config['directory']).rglob('*')) if path.is_file() and path.name!='index.json']
        index=dict(schema_version=1,packet=key,introduced_in_program='2026-10-26.11',
            source_manifest_sha256=config['manifest_sha256'],source_review_sha256=config['review_sha256'],
            frozen_atlas_revision=FROZEN_ATLAS,artifacts=artifacts,status=NO_CREDIT,
            capture=dict(selected=selected,standalone_foreign_source_files_vendored=False,whole_history_vendored=False,
                complete_for_selected_roles=True,source_files=config['source_files'],source_spans=config['source_spans'],
                original_review_scope='accepted_original_source_only_not_canonical_candidate_review'))
        write(directory+'index.json',index)
        packet_indexes[key]=PREFIX+directory+'index.json'
    # Extract only already-certified partial source spans and AST payloads, never execute source.
    witnesses=source_witnesses(args.six_packet,packets['six'])
    write('six-portable-witnesses.json',witnesses)
    design=args.admission_design
    data=(design/'manifest.json').read_bytes();assert sha(data)==ADMISSION_MANIFEST_SHA
    manifest=json.loads(data);raw('admission-design/manifest.json',data)
    for name,receipt in manifest['files'].items():
        data=(design/name).read_bytes();assert sha(data)==receipt;raw('admission-design/'+name,data)
    # Live joins use current canonical data. Frozen packet routes are a separate, pinned source view.
    from atlas_parity_references import references
    from atlas_parity_scope import validate_scope
    program=json.loads((root/'program.json').read_bytes())
    capabilities={r['id']:r for r in json.loads((root/'capabilities.json').read_bytes())}
    repositories={r['repository']:r for r in json.loads((root/'repositories.json').read_bytes())}
    refs,_=references(root,program['reference_snapshots'])
    scope,_=validate_scope(root,program['files']['public_scope'],refs,capabilities,repositories,program['reference_snapshots'])
    mappings={r['id']:r for r in json.loads((root/'mappings.json').read_bytes())}
    assigned={i:r['id'] for r in mappings.values() for i in r['reference_ids']}
    write('joins.json',pack(expected_joins(packets,refs,scope,capabilities,mappings,assigned),TABLE_METADATA))
    top_names=['joins.json','six-portable-witnesses.json']+[
        'admission-design/'+name for name in ['manifest.json',*manifest['files']]]
    artifacts=[dict(path=PREFIX+name,sha256=sha((dest/name).read_bytes())) for name in sorted(top_names)]
    artifacts += [dict(path=packet_indexes[k],sha256=sha((root/packet_indexes[k]).read_bytes())) for k in PACKETS]
    counts=dict(existing_reference_links=498,TF_records=492,JAX_records=3,Torch_records=3,
        TF_source_files=155,TF_source_spans=747,six_source_files=15,six_source_spans=1010,
        tooling_source_receipts=74,tooling_AST_fingerprints=56,tooling_callable_views_not_new_IDs=974,
        TF_workflow_groups=19,TF_unresolved_publicness=480,TF_open_member_selectors=211,
        admission_certificates_applied=0)
    write('index.json',dict(schema_version=1,version='2026-10-26.1',introduced_in_program='2026-10-26.11',
        packets=packet_indexes,artifacts=artifacts,counts=counts,status=NO_CREDIT,
        joins=PREFIX+'joins.json',witnesses=PREFIX+'six-portable-witnesses.json',
        admission_design=dict(manifest=PREFIX+'admission-design/manifest.json',
            sha256=ADMISSION_MANIFEST_SHA,applied=False),
        original_review_scope='original_packets_only_canonical_exact_head_review_pending',
        full_public_surface_complete=False,semantic_definition_complete=False))
    print(json.dumps(dict(captured_packet_records=498,framework_executions=0,standalone_foreign_files_vendored=0,
        new_reference_IDs=0,admission_certificates_applied=0)))


if __name__=='__main__':main()
