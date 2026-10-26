"""Portable accepted span/AST witnesses; source facts are not runtime facts."""
import ast
import hashlib
from pathlib import Path

from atlas_parity_dtype_headers import exact_fields
from atlas_parity_public_capture import exact, manifest_files, sha
from atlas_parity_schema import digest, need, unique

REVISIONS = {'tensorflow': ('tensorflow/tensorflow','a481b10260dfdf833a1b16007eead49c1d7febf3'),
    'keras': ('keras-team/keras','250b42181ce9f37df68319d8f4753ec89a349a43'),
    'jax': ('jax-ml/jax','dc4af684446e65ee98eee8090e1ff6f8211473fb'),
    'pytorch': ('pytorch/pytorch','5c4886908584029761b579af026dcfb627c84070')}


def source_witnesses(packet, originals):
    """Read only exact accepted source files; never execute their Python bodies."""
    sources = originals['source-receipts.json']; texts={}
    for key,row in sources['sources'].items():
        data=(Path(packet)/'sources'/row['framework']/row['path']).read_bytes()
        need(sha(data)==row['sha256'] and len(data)==row['bytes'] and hashlib.sha1(
            b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['git_blob'],
            'public evidence exact frozen source byte/Git proof differs')
        texts[key]=data.decode().splitlines(keepends=True)
    spans=[]
    for key,span in sources['spans'].items():
        lines=texts[span['source_key']]
        text=''.join(lines[span['start']-1:span['end']])
        need(sha(text.encode())==span['sha256'],'public evidence accepted span differs')
        full=span['start']==1 and span['end']==len(lines)
        spans.append(dict(id=key,**span,text=None if full else text,
            capture_role='certified_full_file_span_digest_only' if full else 'certified_partial_source_span'))
    methods=[]
    for row in originals['tooling-selection-evidence.json']['method_fingerprints']:
        data=(Path(packet)/'tooling'/row['path']).read_bytes()
        need(sha(data)==row['source_sha256'],'public evidence selected tooling source bytes differ')
        nodes=ast.parse(data).body
        names=row['name'].split('.')
        if len(names)==2:nodes=next(n.body for n in nodes if isinstance(n,ast.ClassDef) and n.name==names[0])
        node=next(n for n in nodes if isinstance(n,ast.FunctionDef) and n.name==names[-1])
        dump=ast.dump(node,include_attributes=False)
        need(sha(dump.encode())==row['AST_sha256'],'public evidence selected tooling AST differs')
        methods.append(dict(row,AST_dump=dump,capture_role='canonical_AST_not_full_source_or_execution'))
    return dict(schema_version=1,spans=spans,tooling_AST=methods,source_files_vendored=0,
        framework_execution_credit=0,source_selection_execution_credit=0,
        whole_source_capture_complete=False,full_file_spans_digest_only=4)


def validate_tf(originals, manifest):
    sources=originals['source-registry.json']; witnesses=originals['line-witnesses.json']
    exact(sources['missing'],[],'public evidence TF source missing set')
    rows=unique(sources['sources'],'key','public evidence TF source')
    spans=unique(witnesses['records'],'id','public evidence TF witness')
    need(len(rows)==155 and len(spans)==747,'public evidence TF source/span conservation differs')
    files=manifest_files(manifest)
    for key,row in rows.items():
        framework,path=key.split('|',1);repository,revision=REVISIONS[framework]
        exact_fields(row,{'key':str,'file':str,'framework':str,'repository':str,'revision':str,
            'path':str,'sha256':str,'bytes':int,'line_count':int,'git_blob_sha':str,'url':str,
            'original_registry_refs':list,'roles':list},'public evidence TF source receipt')
        need(row['path']==path and row['framework']==framework and row['repository']==repository and
            row['revision']==revision and row['file']=='sources/'+framework+'/'+path and
            row['url']==f'https://github.com/{repository}/blob/{revision}/{path}' and
            row['sha256']==files[row['file']]['sha256'] and row['bytes']==files[row['file']]['bytes'],
            'public evidence TF frozen source path/blob receipt differs')
        digest(row['sha256'],'public evidence TF source SHA256')
    for identity,w in spans.items():
        exact_fields(w,{'excerpt':str,'excerpt_sha256':str,'git_blob_sha':str,'id':str,'line_end':int,
            'line_start':int,'path':str,'repository':str,'revision':str,'role':str,'source_file_bytes':int,
            'source_file_line_count':int,'source_key':str,'source_sha256':str,'url':str},
            'public evidence TF line witness')
        s=rows[w['source_key']]
        need(1<=w['line_start']<=w['line_end']<=s['line_count'] and
            len(w['excerpt'].splitlines())==w['line_end']-w['line_start']+1 and
            sha(w['excerpt'].encode())==w['excerpt_sha256'] and w['git_blob_sha']==s['git_blob_sha'] and
            w['path']==s['path'] and w['source_sha256']==s['sha256'] and
            w['repository']==s['repository'] and w['revision']==s['revision'] and
            w['source_file_bytes']==s['bytes'] and w['source_file_line_count']==s['line_count'] and
            w['url']==s['url']+f"#L{w['line_start']}-L{w['line_end']}",
            'public evidence TF source witness identity/bounds/hash differs')
    whole_goldens=[w for w in spans.values() if w['line_start']==1 and w['line_end']==rows[w['source_key']]['line_count']]
    need(len(whole_goldens)==13 and all('/golden/' in w['path'] and w['line_end']<=8 for w in whole_goldens),
         'public evidence whole small golden quote accounting differs')
    records=originals['dispositions.json']['records']
    ast_rows=sum(bool(r['signature_views']['ast_definitions']) for r in records)
    definitions=set()
    for record in records:
        need(record['selector_provenance']['golden_witness_ref'] in spans,
             'public evidence TF golden source selector absent')
        for definition in record['signature_views']['ast_definitions']:
            need(definition['witness_ref'] in spans and definition['source_key'] in rows and
                spans[definition['witness_ref']]['source_key']==definition['source_key'],
                'public evidence TF AST/signature/source association differs')
            definitions.add((definition['source_key'],definition['line']))
    need(ast_rows==281 and len(definitions)==225,'public evidence TF AST source signature conservation differs')
    groups=originals['workflow-contracts.json']['contracts']
    need(len(groups)==19 and sum(g['member_count'] for g in groups)==492 and
        all(g['fully_specified'] is False and g['framework_runtime_executed'] is False and
            g['implementation_owner'] is None and g['proposal_only'] is True for g in groups),
        'public evidence workflow groups cannot acquire implementation/runtime credit')
    contexts=originals['companion-consumer-context.json']['records']
    need(len(contexts)==24 and len({r['source_key'] for r in contexts})==13 and
        all(r['witness_ref'] in spans and r['runtime_evidence'] is False for r in contexts),
        'public evidence companion source view cannot become runtime evidence')
    return dict(TF_AST_bearing_rows=281,TF_unique_AST_definitions=225,TF_companion_contexts=24,
                TF_whole_small_golden_quotes=13)


def lambda_from_span(text, column):
    """The certified span can include dictionary commas or an enclosing call's ')'.

    Choose the longest expression prefix that is exactly one lambda. The pinned
    parameter/body strings below must still match; this does not run the lambda.
    """
    suffix=text[column:].strip()
    for end in range(len(suffix),0,-1):
        try:node=ast.parse(suffix[:end],mode='eval').body
        except SyntaxError:continue
        if isinstance(node,ast.Tuple) and len(node.elts)==1:node=node.elts[0]
        if isinstance(node,ast.Lambda):return node
    need(False,'public evidence certified lambda expression cannot be parsed')


def validate_six(originals, manifest, portable):
    receipts=originals['source-receipts.json']; sources=receipts['sources']; spans=receipts['spans']
    exact_fields(portable,{'schema_version':int,'spans':list,'tooling_AST':list,'source_files_vendored':int,
        'framework_execution_credit':int,'source_selection_execution_credit':int,
        'whole_source_capture_complete':bool,'full_file_spans_digest_only':int},'public evidence portable witness header')
    exact({k:v for k,v in portable.items() if k not in ('spans','tooling_AST')},dict(schema_version=1,
        source_files_vendored=0,framework_execution_credit=0,source_selection_execution_credit=0,
        whole_source_capture_complete=False,full_file_spans_digest_only=4),'public evidence portable scope/no credit')
    need(len(sources)==15 and len(spans)==1010,'public evidence six source/span conservation differs')
    files=manifest_files(manifest)
    for key,row in sources.items():
        framework,path=key.split(':',1);repo,revision=REVISIONS[framework]
        need(row['framework']==framework and row['revision']==revision and row['path']==path and
            row['url']==f'https://github.com/{repo}/blob/{revision}/{path}' and
            row['sha256']==files['sources/'+framework+'/'+path]['sha256'] and
            row['bytes']==files['sources/'+framework+'/'+path]['bytes'],
            'public evidence six frozen source path/blob receipt differs')
    witnesses=unique(portable['spans'],'id','public evidence portable span')
    need(witnesses.keys()==spans.keys(),'public evidence portable span identity set differs')
    full_count=0
    for identity,w in witnesses.items():
        exact_fields(w,{'id':str,'source_key':str,'start':int,'end':int,'sha256':str,'url':str,
            'text':type(None) if w.get('text') is None else str,'capture_role':str},'public evidence portable span')
        expected=spans[identity]
        need(w['source_key'] in sources,'public evidence portable source key absent')
        s=sources[w['source_key']]
        exact({k:w[k] for k in expected},expected,'public evidence certified span/source identity')
        need(identity==f"{w['source_key']}:L{w['start']}-L{w['end']}" and
            1<=w['start']<=w['end']<=s['line_count'] and
            w['url']==s['url']+f"#L{w['start']}-L{w['end']}", 'public evidence span source bounds differ')
        full=w['start']==1 and w['end']==s['line_count'];full_count+=full
        if full:
            need(w['text'] is None and w['capture_role']=='certified_full_file_span_digest_only',
                'public evidence full source file must remain digest-only')
        else:
            need(type(w['text']) is str and sha(w['text'].encode())==w['sha256'] and
                len(w['text'].splitlines())==w['end']-w['start']+1 and
                w['capture_role']=='certified_partial_source_span',
                'public evidence portable source witness hash/extent differs')
    need(full_count==4,'public evidence full-file span count differs')
    tooling=originals['tooling-selection-evidence.json']
    need(len(tooling['cached_primary_source_receipts'])==74 and len(tooling['method_fingerprints'])==56 and
        len(portable['tooling_AST'])==56,'public evidence tooling source/AST accounting differs')
    for w,original in zip(portable['tooling_AST'],tooling['method_fingerprints']):
        exact({k:w.get(k) for k in original},original,'public evidence tooling fingerprint/source binding')
        need(set(w)==set(original)|{'AST_dump','capture_role'} and type(w['AST_dump']) is str and
            sha(w['AST_dump'].encode())==original['AST_sha256'] and
            w['capture_role']=='canonical_AST_not_full_source_or_execution',
            'public evidence portable tooling AST differs')
    views=originals['returned-tooling-views.json']
    need(views['source_lambda_count']==len(views['source_lambda_views'])==974 and
        views['new_public_IDs']==views['framework_cases_executed']==0 and
        views['exhaustive_runtime_returned_dictionary_or_operator_surface'] is False,
        'public evidence returned tooling views cannot become API/kernel/runtime credit')
    for row in views['source_lambda_views']:
        need(row['source'] in witnesses and row['kernel_semantics_or_runtime_signature_verified'] is False,
             'public evidence tooling lambda source association/credit differs')
        text=witnesses[row['source']]['text']
        need(type(text) is str,'public evidence lambda source span missing')
        # Parse only the exact lambda expression suffix; no eval/import or source invocation.
        node=lambda_from_span(text,row['column'])
        need(isinstance(node,ast.Lambda) and ast.unparse(node.args)==row['parameters'] and
            ast.unparse(node.body)==row['return_expression'],
            'public evidence tooling lambda AST/signature differs')
    return dict(portable_partial_spans=1006,certified_full_file_spans_digest_only=4,
                tooling_AST_fingerprints=56,tooling_callable_views_not_new_IDs=974)
