"""Source-only contract/contradiction capture for frozen Tensor.new_tensor."""
import os
from pathlib import Path
import ast, hashlib, json, re
ROOT = Path(__file__).resolve().parent
P = ROOT / 'sources'
REV = '5c4886908584029761b579af026dcfb627c84070'

def text(path):
    return (P / path).read_text(encoding='utf-8')

def cite(path, needle):
    n = next((i for i, l in enumerate(text(path).splitlines(), 1) if needle in l))
    return f'https://github.com/pytorch/pytorch/blob/{REV}/{path}#L{n}'

def body(source, marker):
    """Extract a C++ brace body, ignoring comments and quoted strings."""
    start = source.index(marker)
    i = source.index('{', start)
    begin = i
    depth = 0
    state = 'code'
    quote = ''
    while i < len(source):
        c = source[i]
        two = source[i:i + 2]
        if state == 'line':
            if c == '\n':
                state = 'code'
        elif state == 'block':
            if two == '*/':
                state = 'code'
                i += 1
        elif state == 'quoted':
            if c == '\\':
                i += 1
            elif c == quote:
                state = 'code'
        elif two == '//':
            state = 'line'
            i += 1
        elif two == '/*':
            state = 'block'
            i += 1
        elif c in ('"', "'"):
            state = 'quoted'
            quote = c
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return source[begin:i + 1]
        i += 1
    raise ValueError('Unclosed body: ' + marker)

def analyze(sources):
    construction = sources['torch/csrc/utils/tensor_new.cpp']
    binding = sources['tools/autograd/templates/python_variable_methods.cpp']
    conversions = sources['aten/src/ATen/native/TensorConversions.cpp']
    method = body(binding, 'static PyObject * THPVariable_new_tensor(')
    ctor = body(construction, 'Tensor new_tensor(')
    copy = body(construction, 'Tensor new_from_data_copy(')
    internal = body(construction, 'Tensor internal_new_from_data(')
    signature = re.search('"(new_tensor\\(PyObject\\* data[^"\\n]+)"', ctor).group(1)
    names = ['data'] + re.findall('(?:ScalarType|Device\\?|bool)\\s+(\\w+)=', signature)
    assert names == ['data', 'dtype', 'device', 'requires_grad']
    assert signature == 'new_tensor(PyObject* data, *, ScalarType dtype=None, Device? device=None, bool requires_grad=False)'
    assert 'has_torch_function(self)' in method and method.index('handle_torch_function') < method.index('torch::utils::new_tensor(')
    assert 'OptionalDeviceGuard device_guard(device_of(self_));' in method
    assert 'legacyExtractDispatchKey(self_), self_.scalar_type(), args, kwargs' in method
    assert re.search('\\{"new_tensor",\\s*castPyCFunctionWithKeywords\\(THPVariable_new_tensor\\),\\s*METH_VARARGS \\| METH_KEYWORDS', binding)
    assert 'layout' not in signature and 'pin_memory' not in signature
    assert 'r.scalartypeWithDefault(1, scalar_type)' in ctor and 'device_or_from_dispatch_key(r.deviceOptional(2), dispatch_key)' in ctor
    assert ctor.index('new_from_data_copy(') < ctor.index('new_tensor.detach_()') < ctor.index('new_tensor.set_requires_grad(args_requires_grad)')
    assert 'PyExc_UserWarning' in ctor and 'THPVariable_Check(data)' in ctor
    assert '/*copy_variables=*/true' in copy and '/*copy_numpy=*/true' in copy and ('/*type_inference=*/false' in copy)
    tensor_branch = internal[internal.index('if (THPVariable_Check(data))'):internal.index('#ifdef USE_NUMPY')]
    assert 'var = var.detach();' in tensor_branch and '/*copy=*/copy_variables' in tensor_branch
    storage_branch = body(internal, 'if (isStorage(data))')
    assert 'tensor.set_(storage);' in storage_branch and '.clone(' not in storage_branch
    assert '/*copy=*/false' in internal[internal.index('if (only_lift_cpu_tensors())'):]
    assert 'tensor = at::lift_fresh(tensor);' in internal
    tocopy = body(conversions, 'Tensor _to_copy(')
    assert 'self.layout() == layout.value()' in tocopy and 'options = self.options().merge_in(options)' in tocopy
    alias = body(conversions, 'bool to_will_alias(')
    assert '!copy' in alias and 'is_null_or_equal_to(device, self.device())' in alias
    toimpl = body(conversions, 'static inline Tensor to_impl(')
    assert 'return self;' in toimpl
    tokens = ['THPVariable_Check(data)', 'PyObject_HasAttrString(data, "__cuda_array_interface__")', 'PyArray_Check(data)', 'PyObject_HasAttrString(data, "__dlpack__")', 'compute_sizes(data, scalar_type)', 'if (isStorage(data))']
    positions = [internal.index(t) for t in tokens]
    assert positions == sorted(positions)
    assert '#ifdef USE_NUMPY' in internal
    kwargs = body(sources['torch/csrc/utils/python_arg_parser.cpp'], '[[noreturn]] static void extra_kwargs(')
    assert 'TORCH_CHECK_TYPE' in kwargs and 'got an unexpected keyword argument' in kwargs
    return {'signature': signature, 'accepted_parameter_names': names, 'rejected_builtin_keywords': ['layout', 'pin_memory', 'out', 'non_blocking', 'copy'], 'builtin_route': 'manual parser after self __torch_function__ interception', 'universal_copy_proven': False, 'universal_strided_proven': False, 'protocol_branch_order': tokens, 'source_assertion_groups_passed': 15}

def main():
    rows = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
    sources = {r['path']: text(r['path']) for r in rows}
    result = analyze(sources)
    cases = re.findall('case at::(k\\w+):', body(sources['torch/csrc/utils/python_scalars.h'], 'inline void store_scalar('))
    tests_module = ast.parse(sources['test/test_tensor_creation_ops.py'])
    test_definitions = []
    for node in ast.walk(tests_module):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in ('test_tensor_factory_copy_var', 'test_new_tensor', 'test_new_tensor_device'):
            test_definitions.append({'name': node.name, 'source': cite('test/test_tensor_creation_ops.py', 'def ' + node.name + '('), 'decorators': [ast.unparse(d) for d in node.decorator_list], 'execution': 'not_run', 'credit': 'source definition only; decorators/conditional hardware clauses receive no execution credit'})
    contracts = {'schema_version': 1, 'framework': 'pytorch', 'version': '2.14.1', 'revision': REV, 'symbol': 'torch.Tensor.new_tensor', 'source_contract_status': 'partial_whole_api; builtin_parser_boundary_resolved', 'runtime_verification': 'not_run', 'public_api_mapping_complete': False, 'builtin_signature': result, 'defaults': {'dtype': 'Omitted/None uses receiver scalar_type; no inference from data and no global default-dtype substitution. Explicit torch.dtype or Python float/int/bool/complex types accepted by parser; Python aliases map Double/Long/Bool/ComplexDouble.', 'device': 'Omitted/None resolves receiver legacy dispatch device type inside OptionalDeviceGuard(device_of(self)); guard preserves indexed receiver device. Explicit torch.device/string or nonnegative integer accelerator index overrides; symbolic integer device forms guard/specialize. Backend admission/device initialization remains separate.', 'requires_grad': 'DefaultFalse; parser bool parameter, then result.detach_() and set_requires_grad. True requires isDifferentiableType(dtype). Tensor data emits UserWarning before construction; warning-as-error can abort.', 'layout_and_pinning': 'No built-in keyword parameters. Tensor route preserves input layout through .to; sequence/storage/array routes have their own layout/storage behavior. No API control of pinned allocation is forwarded.'}, 'input_protocols': [{'kind': 'Tensor', 'route': 'detach when copy_variables=True; .to(target device,target dtype,non_blocking=False,copy=True); final detach_ and requires_grad', 'alias': 'fresh copied Tensor storage where .to is admitted; input layout kind preserved; exact stride preservation depends non-overlapping/dense and _to_copy policy', 'source': cite('torch/csrc/utils/tensor_new.cpp', 'if (THPVariable_Check(data))')}, {'kind': 'CUDA array interface', 'route': 'USE_NUMPY-guarded, before ndarray/DLPack; validate dict/shape/typestr/data/strides then .to(copy=True)', 'alias': 'copy requested; stream/read-only/version behavior must follow CAI consumer source, not ndarray or DLPack assumptions', 'source': cite('torch/csrc/utils/tensor_numpy.cpp', 'at::Tensor tensor_from_cuda_array_interface(')}, {'kind': 'NumPy ndarray', 'route': 'USE_NUMPY + is_numpy_available; validate mapped dtype/native-endian/nonnegative element-compatible strides; .to(copy=True); warning for nonwritable suppressed when copying', 'alias': 'copy requested, including nonwritable arrays; negative strides and nonnative byte order reject before copying', 'source': cite('torch/csrc/utils/tensor_numpy.cpp', 'at::Tensor tensor_from_numpy(')}, {'kind': 'DLPack object', 'route': 'Object must expose __dlpack__; torch.utils.dlpack.from_dlpack(data), then .to(copy=True); from_dlpack negotiates version/device/stream protocol', 'alias': 'new_tensor copy requested after initial DLPack consumption; raw capsule has no dedicated new_tensor branch', 'source': cite('torch/csrc/utils/tensor_new.cpp', 'if (PyObject_HasAttrString(data, "__dlpack__"))')}, {'kind': 'Storage', 'route': 'typed/untyped Storage admitted by isStorage; type check, allocate empty then tensor.set_(storage); later .to(copy=False) can return self on matching metadata', 'alias': 'universal copying is not established; same-device/dtype alias path survives. Exact admitted behavior needs explicit source-supported acceptance case and reference oracle before semantic closure.', 'source': cite('torch/csrc/utils/tensor_new.cpp', 'if (isStorage(data))')}, {'kind': 'Scalar/rectangular sequence', 'route': 'compute_sizes, max128 rank, nonempty recursive_store in receiver/explicit dtype with type_inference=False; CPU construction/lift/device transfer as source defines; meta branch skips materialization', 'alias': 'new allocation for ordinary values; ragged shapes, unsupported scalar objects and representability errors propagate', 'source': cite('torch/csrc/utils/tensor_new.cpp', 'auto sizes = compute_sizes(data, scalar_type);')}, {'kind': 'Overridden receiver or TorchFunction mode', 'route': 'handle_torch_function receives original args/kwargs before manual parser', 'alias': 'extension-defined behavior; unsupported built-in keywords can be handled by an override, so builtin rejection must be scoped', 'source': cite('tools/autograd/templates/python_variable_methods.cpp', 'static PyObject * THPVariable_new_tensor(')}], 'scalar_storage_dispatch_types': cases, 'contradictions': [{'id': 'TORCH-NEW-TENSOR-KWARGS', 'documented': 'layout and pin_memory are listed in exact docstring/published minor docs', 'builtin_source': 'manual parser has neither keyword and rejects extras', 'resolution': 'Builtin accepted signature resolved; preserve published documented capability as distinct reference discrepancy, not a silently excluded parameter.', 'sources': [cite('torch/_tensor_docs.py', 'new_tensor(data,'), cite('torch/csrc/utils/tensor_new.cpp', '"new_tensor(PyObject* data,')]}, {'id': 'TORCH-NEW-TENSOR-COPY', 'documented': 'new_tensor always copies data', 'builtin_source': 'Storage route set_(storage), then matching .to(copy=False) alias fast path; no clone inserted', 'resolution': 'Do not assert universal copy. Keep Storage alias counterexample as source-derived obligation pending admitted-case/oracle confirmation.', 'sources': [cite('torch/csrc/utils/tensor_new.cpp', 'if (isStorage(data))'), cite('aten/src/ATen/native/TensorConversions.cpp', 'bool to_will_alias(')]}, {'id': 'TORCH-NEW-TENSOR-LAYOUT', 'documented': 'default layout strided', 'builtin_source': 'Tensor input .to preserves its layout; _to_copy rejects layout conversion and merges input options', 'resolution': 'Do not claim all inputs become strided. Keep sparse/quantized/nested and stride classes separate.', 'sources': [cite('aten/src/ATen/native/TensorConversions.cpp', 'Tensor _to_copy(')]}], 'legacy_separation': {'torch_tensor': 'copies/detaches Tensor data; dtype inferred from data when unspecified', 'torch_Tensor': 'legacy Tensor(Tensor) alias/AD and default-floating sequence behavior', 'new_tensor': 'receiver dtype/device defaults; Tensor route copy/detach, Storage concern separate; no type inference'}, 'source_test_definitions': test_definitions, 'source_test_limitations': ['test_tensor_factory_copy_var compares bound data_ptr methods rather than calling data_ptr(); it does not prove pointer inequality. Value-mutation test_new_tensor is stronger for ordinary Tensor/NumPy copy.', 'The inspected new_tensor tests do not establish keyword rejection, Storage no-alias, all layout classes or DLPack/CAI behavior. This is a selected-source search, not a claim that the entire reference suite lacks such cases.', 'Conditional multi-GPU branches and CUDA-only tests are source definitions, not executed coverage.'], 'remaining_whole_api_questions': ['Confirm same-device/dtype TypedStorage and UntypedStorage admission/alias behavior and clarify documented always-copy disagreement.', 'Materialize complete input-kind x dtype x layout x backend admission and conversion matrix, including quantized, sparse/nested, shell/packed/float8/complex reduced precision and meta/Fake modes.', 'Account exact device-guard/default-device/TorchFunction mode behavior for every optional backend and build feature; no CPU fallback credit.', 'Close CAI stream/version/lifetime and DLPack versioned/read-only protocol behavior through actual generated/native consumers; do not infer full behavior from attribute presence.', 'Derive and test exact conversion/shape/error/warning boundaries; cyclic sequences differ because type_inference=False bypasses infer_scalar_type cycle checks.', 'Close compiled/exported/trace/dynamic shape and forward/reverse/higher-order/vmap/functionalization behavior for each protocol/override class.']}
    (ROOT / 'contract.json').write_text(json.dumps(contracts, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'parameters': result['accepted_parameter_names'], 'source_assertion_groups': 15, 'source_files': len(rows), 'scalar_storage_type_cases': len(cases), 'whole_api_complete': False}, indent=2))
if __name__ == '__main__':
    main()
