from research import *
import ast, re, yaml, collections, posixpath
P = ROOT / 'sources'
trees = {label: {x['path']: x for x in json.loads((ROOT / (label + '-tree.json')).read_text(encoding='utf-8'))['tree'] if x['type'] == 'blob'} for label in ('base', 'release')}
url = f'https://raw.githubusercontent.com/pytorch/pytorch/{BASE}/aten/src/ATen/native/native_functions.yaml'
base_data = fetch(url)
assert hashlib.sha1(b'blob ' + str(len(base_data)).encode() + b'\x00' + base_data).hexdigest() == trees['base']['aten/src/ATen/native/native_functions.yaml']['sha']
base_schemas = yaml.safe_load(base_data)
schemas = yaml.safe_load((P / 'aten/src/ATen/native/native_functions.yaml').read_text(encoding='utf-8'))
assert [r['func'] for r in base_schemas] == [r['func'] for r in schemas]
source_rows = []
aliases = []
dynamic = []

def strings(node):
    return '\n'.join((x.value for x in ast.walk(node) if isinstance(x, ast.Constant) and isinstance(x.value, str)))
for file, func in [('torch/_torch_docs.py', 'add_docstr'), ('torch/_tensor_docs.py', 'add_docstr_all')]:
    module = ast.parse((P / file).read_text(encoding='utf-8'))
    for node in module.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call) or ast.unparse(node.value.func) != func:
            continue
        call = node.value
        target = call.args[0]
        symbol = 'torch.Tensor.' + target.value if isinstance(target, ast.Constant) else ast.unparse(target)
        assert not symbol.startswith('getattr'), symbol
        doc = strings(call.args[1])
        lines = [x.strip() for x in doc.splitlines() if x.strip()]
        record = {'symbol': symbol, 'kind': 'source:doc-binding', 'source': f'https://github.com/pytorch/pytorch/blob/{REV}/{file}#L{call.lineno}', 'line': call.lineno, 'signature_text': lines[0] if lines else '', 'source_path': file, 'stability': 'exact-release-docstring-public-status-review-required'}
        source_rows.append(record)
        for target in re.findall('(?:Alias for|alias for|Alias of|alias of)\\s+:func:`([^`]+)`', doc):
            if '.' not in target:
                target = 'torch.Tensor.' + target if record['symbol'].startswith('torch.Tensor.') else 'torch.' + target
            aliases.append({'source_symbol': symbol, 'target_symbol': target, 'relation': 'documented_alias', 'source': record['source'], 'semantic_merge_authorized': False, 'required_review': 'Retain both spellings and full signatures; reconcile argument/default/out/in-place/domain/AD behavior before sharing canonical operation.'})
module = ast.parse((P / 'torch/_torch_docs.py').read_text(encoding='utf-8'))
loops = [n for n in module.body if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and (n.target.id == 'unary_base_func_name')]
assert len(loops) == 1
loop = loops[0]
names = ast.literal_eval(loop.iter)
assert len(names) == len(set(names)) == 29
for name in names:
    for suffix in ('', '_'):
        symbol = 'torch._foreach_' + name + suffix
        dynamic.append({'symbol': symbol, 'kind': 'py:function', 'source': f'https://github.com/pytorch/pytorch/blob/{REV}/torch/_torch_docs.py#L{loop.lineno}', 'source_path': 'torch/_torch_docs.py', 'line': loop.lineno, 'conditional_exposure': 'hasattr(torch, symbol); dispatcher binding must confirm availability', 'signature_text': f'{symbol}(self: List[Tensor]) -> ' + ('None' if suffix else 'List[Tensor]'), 'stability': 'private-spelling-docstring-generated-public-status-review-required'})
inventory_names = published_names()
source_set = {x['symbol'] for x in source_rows}
missing = [x for x in source_rows if x['symbol'] not in inventory_names]
line_by_schema = {}
for line, text in enumerate((P / 'aten/src/ATen/native/native_functions.yaml').read_text(encoding='utf-8').splitlines(), 1):
    m = re.match('- func: (.*)', text)
    if m:
        line_by_schema[m.group(1)] = line
assert len(line_by_schema) == len(schemas)
operators = []
for item in schemas:
    s = item['func']
    operators.append({'schema': s, 'operator': s.split('(')[0], 'source': f'https://github.com/pytorch/pytorch/blob/{REV}/aten/src/ATen/native/native_functions.yaml#L{line_by_schema[s]}', 'variants': item.get('variants', 'function'), 'python_module': item.get('python_module'), 'dispatch': item.get('dispatch', {}), 'public_disposition': 'unreviewed_source_schema_not_assumed_public', 'generated_extra': item.get('autogen')})
doxy = (P / 'docs/cpp/source/Doxyfile').read_text(encoding='utf-8')
input_block = re.search('^INPUT\\s*=\\s*(.*?)(?=\\n[A-Z_]+\\s*=)', doxy, re.M | re.S).group(1)
cpp_inputs = []
for raw in re.findall('\\.\\./\\.\\./\\.\\./[^\\s\\\\]+', input_block):
    path = posixpath.normpath(posixpath.join('docs/cpp/source', raw))
    matches = [p for p in trees['release'] if p == path or p.startswith(path + '/')]
    cpp_inputs.append({'input': path, 'tracked_blob_count': len(matches), 'state': 'tracked_source' if matches else 'generated_build_input_missing_from_git_tree', 'source': f'https://github.com/pytorch/pytorch/blob/{REV}/docs/cpp/source/Doxyfile#L32'})
summary = {'schema_version': 1, 'framework': 'pytorch', 'version': '2.14.1', 'revision': REV, 'base_revision': BASE, 'patch_reconciliation': {'docs_minor_label': 'expected_by_exact_release_conf.py', 'source': f'https://github.com/pytorch/pytorch/blob/{REV}/docs/source/conf.py#L138', 'compare_commits': 5, 'changed_files': 15, 'changed_documentation_blobs': [], 'all_native_function_schemas_unchanged': True, 'native_schema_count': len(schemas), 'native_dispatch_delta': 'conj_physical.out MPS dispatch now shares conj_physical_out with CPU/CUDA/XPU', 'numerical_correctness_delta_required': ['MPS complex batched underdetermined lstsq', 'MPS rank-deficient/ill-conditioned SVD orthogonality/small singular values', 'MPS conjugated/column-major SVD and native small-input path', 'CUDA13.2.2 NVFP4 cublasLt scaling and divergent-kernel correctness in binary selection'], 'inventory_artifact_source_commit': 'not cryptographically identified by published Sphinx header; exact-source corroboration is scoped, not proof of all inventory semantics'}, 'counts': {'top_level_docstring_targets': sum((x['source_path'].endswith('_torch_docs.py') for x in source_rows)), 'inherited_tensor_docstring_targets': sum((x['source_path'].endswith('_tensor_docs.py') for x in source_rows)), 'docstring_targets_total': len(source_rows), 'docstring_targets_absent_from_inventory': len(missing), 'finite_foreach_generated_candidates': len(dynamic), 'explicit_docstring_alias_relations': len(aliases), 'native_schema_overloads': len(operators), 'cpp_doxygen_inputs': len(cpp_inputs), 'cpp_generated_input_gaps': sum((x['state'] != 'tracked_source' for x in cpp_inputs))}, 'extraction_closure': {'selected_docstring_call_sites': 'complete for direct module-level add_docstr/add_docstr_all calls in two exact files; function helper body excluded', 'foreach_loop': 'all29*2 name candidates retained with hasattr condition, not public availability proof', 'native_schemas': 'all2585 explicit - func entries retained; generated autogen declarations retained separately; Python skip/manual binding code must be reconciled, not blanket exported', 'cpp': 'Doxygen input list fully enumerated; actual C++ declarations/inheritance/generated headers remain unclosed'}, 'gaps': ['All torch modules beyond these two documentation files require their own autodoc/export/decorator/inheritance closure.', 'Source docstrings absent from published inventory are retained, not silently classified nonpublic.', 'Operator schema/python codegen skip/manual exposure and autogen expansion require exact generation audit.', 'C++ generated headers/Doxygen declarations/inheritance require source generator output; no build/import was performed.', 'Companion package versions and contracts remain separately unclosed; no arbitrary latest package is substituted.', 'Per-backend dtype/layout/gradient/compiler coverage remains unexecuted and partly unmapped.']}
save('source-supplement.json', {'summary': summary, 'source_docstrings': source_rows, 'generated_candidates': dynamic, 'documented_aliases': aliases, 'missing_inventory_targets': missing, 'operator_schemas': operators, 'cpp_inputs': cpp_inputs})
save('closure-summary.json', summary)
print(json.dumps(summary['counts'], indent=2))
