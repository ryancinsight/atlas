"""Portable reviewed source excerpts and independently bound source facts."""
import ast
import hashlib
import textwrap

from atlas_parity_dtype_headers import exact_fields
from atlas_parity_schema import need, source_entry_at
from atlas_parity_tf_conversion_model import exact
from atlas_parity_tf_conversion_capture import TF_REVISION, KERAS_REVISION


def source_facts(original):
    witnesses = {w['id']:w for w in original['source-witnesses.json']['records']}
    def quote(path,first,last):
        return witnesses[f'tensorflow:{path}:{first}-{last}']['text']
    registry = 'tensorflow/python/framework/tensor_conversion_registry.py'
    full = ''.join(quote(registry,a,b) for a,b in [(164,209),(210,237),(238,264)])
    convert = ast.parse(full).body[0]
    need(isinstance(convert,ast.FunctionDef) and convert.name=='convert','TF conversion registry quote function')
    hook = next(n for n in convert.body if isinstance(n,ast.If) and ast.unparse(n.test)=='overload is not None')
    need(ast.unparse(hook.body[0])=='return overload(dtype, name)','TF conversion direct hook return')
    loop = next(n for n in convert.body if isinstance(n,ast.For))
    trial = next(n for n in ast.walk(loop) if isinstance(n,ast.Try))
    need(ast.unparse(trial.handlers[0].type)=='(TypeError, ValueError)' and
         any(isinstance(n,ast.Attribute) and ast.unparse(n)=='ret.dtype'
             for statement in trial.orelse for n in ast.walk(statement)), 'TF conversion hint try-else exception boundary')
    banned = ast.parse(quote(registry,31,38)).body[0].value
    need([ast.unparse(n) for n in banned.elts]==['int','float','np.generic','np.ndarray'], 'TF conversion exact registration exclusion tuple')
    tensor = ast.parse(textwrap.dedent(quote('tensorflow/python/framework/ops.py',640,652))).body[0]
    need(isinstance(tensor.body[0].body[-1],ast.Return) and
         ast.unparse(tensor.body[0].body[-1].value)=='graph.capture(self, name=name)' and
         ast.unparse(tensor.body[1].value)=='super().__tf_tensor__(dtype, name)', 'TF conversion capture returns without dtype/superclass')
    return {'hook_return':'direct_before_registry_no_hint_forwarded',
        'hinted_normal_None':'AttributeError_in_try_else_before_retry',
        'caught_converter_TypeError_ValueError':'same_converter_unhinted_retry',
        'unhinted_None':'RuntimeError_accepted_result_types', 'NotImplemented':'next_converter',
        'registration_exclusions':['int','float','np.generic','np.ndarray'],
        'Python_complex_registration':'not_banned_by_exclusion_tuple',
        'Python_bool_registration':'banned_as_int_subclass',
        'non_eager_capture':'returns_graph_capture_without_dtype_or_superclass_branch',
        'target_conversion_order':'infer_then_convert_operands_then_operation',
        'nearest_even_and_native_backend_execution':'UNRUN_analytical_premise_only',
        'finite_AD_model':'all_output_loss_intermediate_and_cotangent_components_checked_in_declared_dtype',
        'whole_public_API_credit':False,'framework_execution_credit':0}


def expected_source_proof(original):
    rows=[];proposal=original['proposal.json']
    for group in ['clauses','supporting_distinctions']:
        for i,row in enumerate(proposal[group]):
            rows.append({'id':row['id'],'source_entry':[group,i],'witness_refs':row['witness_refs'],
                         'whole_API_credit':False})
    return {'schema_version':1,'role':'portable_excerpts_and_original_cached_blob_review_not_runtime_proof',
        'frameworks':{'tensorflow':{'version':'2.21.0','revision':TF_REVISION},
                      'keras':{'version':'3.15.1','revision':KERAS_REVISION}},
        'selected_source_blobs':21,'portable_source_spans':63,'clauses':rows,
        'facts':source_facts(original)}


def validate_sources(document, original):
    source=original['source-receipts.json'];witnesses=original['source-witnesses.json']['records']
    by={r['id']:r for r in source['records']}
    need(len(by)==len(source['records'])==21 and len(witnesses)==63,'TF conversion21 source/63 span conservation')
    for row in source['records']:
        need(row['revision']==({'tensorflow':TF_REVISION,'keras':KERAS_REVISION}[row['framework']]) and
             row['sha256']==row['earlier_cache_entry']['sha256'] and
             row['git_blob_sha']==row['frozen_tree_entry']['sha']==row['earlier_cache_entry']['git_blob_sha'],
             'TF conversion original Git/cache source identity differs')
    for row in witnesses:
        need(row['source_id'] in by and type(row['start_line']) is type(row['end_line']) is int and
             1<=row['start_line']<=row['end_line'] and
             len(row['text'].splitlines())==row['end_line']-row['start_line']+1 and
             hashlib.sha256(row['text'].encode()).hexdigest()==row['sha256'],
             'TF conversion portable source span/body differs')
    need(type(document) is dict and type(document.get('clauses')) is list and len(document['clauses'])==16,
         'TF conversion sixteen exact source clause links required')
    exact_fields(document,{'schema_version':int,'role':str,'frameworks':dict,'selected_source_blobs':int,
        'portable_source_spans':int,'clauses':list,'facts':dict},'TF conversion source proof')
    for row in document['clauses']:
        exact_fields(row,{'id':str,'source_entry':list,'witness_refs':list,'whole_API_credit':bool},'TF conversion typed source clause')
        selected=source_entry_at(original['proposal.json'],row.get('source_entry'),'TF conversion clause source selector')
        need(selected['id']==row.get('id') and exact(selected['witness_refs'],row.get('witness_refs')),
             'TF conversion source clause/witness relation differs')
    need(exact(document,expected_source_proof(original)),'TF conversion exact source facts/proof scope differs')
