"""Generate acceptance obligations; this file does not import or execute torch."""
import os
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parent
rows = []

def case(identity, scope, setup, call, expect, hardware='CPU', status='source_derived_unrun'):
    rows.append({'id': identity, 'scope': scope, 'setup': setup, 'call': call, 'expected': expect, 'required_hardware': hardware, 'status': status, 'execution_credit': 'none; proposed acceptance case, no runtime test executed'})
case('KW-LAYOUT', 'builtin parser', 'ordinary torch.Tensor receiver; overrides/modes disabled', 'prototype.new_tensor([1], layout=torch.strided)', 'TypeError for unexpected layout keyword; do not treat explicit default as accepted')
case('KW-PIN', 'builtin parser', 'ordinary torch.Tensor receiver; overrides/modes disabled', 'prototype.new_tensor([1], pin_memory=False)', 'TypeError for unexpected pin_memory keyword even when False')
case('KW-POSITIONAL', 'builtin parser', 'ordinary torch.Tensor receiver', 'prototype.new_tensor([1], torch.float64)', 'Keyword-only dtype positional misuse rejects')
case('DTYPE-PROTOTYPE', 'dtype defaults', 'prototype int8; global default float64; data [1.75,-2.25]', 'prototype.new_tensor(data)', 'dtype int8 and values [1,-2]; global default and data floating type do not replace receiver dtype')
case('DTYPE-PYCLASS', 'accepted dtype forms', 'prototype float32; data [1,2]', 'prototype.new_tensor(data, dtype=float)', 'float64 values [1,2]; Python float alias is Double, not global default')
case('DEVICE-PROTOTYPE', 'device defaults', 'prototype on cuda:1; current device cuda:0; data Tensor on CPU', 'prototype.new_tensor(data)', 'result cuda:1 and exact represented data; current device restored after call', 'two CUDA devices')
case('DEVICE-OVERRIDE', 'device override', 'prototype on cuda:1; data Tensor cuda:0', 'prototype.new_tensor(data, device="cpu")', 'result CPU and correct represented values', 'two CUDA devices plus CPU')
case('COPY-TENSOR', 'Tensor copy/detach', 'source [2.,3.] with requires_grad=True; receiver float32', 'y=prototype.new_tensor(source, requires_grad=True); loss=(y*y).sum(); loss.backward()', 'new leaf; y.grad=[4,6], source.grad is None; mutate y and verify source values unchanged; nonempty storage addresses differ')
case('GRAD-DEFAULT', 'requires_grad default', 'prototype requires_grad=True; source floating Tensor', 'prototype.new_tensor(source)', 'new leaf requires_grad False; no graph edge to prototype or source')
case('GRAD-INTEGER', 'requires_grad error', 'prototype int64; data [1,2]', 'prototype.new_tensor(data, requires_grad=True)', 'RuntimeError from differentiable dtype guard; no half-constructed returned value')
case('COPY-NUMPY', 'ndarray copy', 'native-endian ndarray [5.]', 'r=prototype.new_tensor(array); array[0]=7', 'r retains5; modifying r also cannot mutate original array; record NumPy build support')
case('NPY-NEGSTRIDE', 'ndarray errors', 'negative-stride ndarray from reversed slice', 'prototype.new_tensor(array)', 'ValueError before copy; do not silently repair by copying to contiguous')
case('NPY-ENDIAN', 'ndarray errors', 'non-native-byte-order ndarray', 'prototype.new_tensor(array)', 'ValueError before copy; do not silently byteswap')
case('LAYOUT-TENSOR', 'Tensor input layout', 'sparse COO input; ordinary dense float32 prototype; compatible target device', 'prototype.new_tensor(sparse)', 'output retains sparse layout and dense-equivalent values; independent indices/values after requested copy', 'backend with sparse copy support')
case('STRIDE-DENSE', 'memory format', 'non-overlapping dense transposed input', 'prototype.new_tensor(input)', 'copied storage and preserved admitted strides; full represented value equality')
case('STRIDE-OVERLAP', 'memory format', 'expanded zero-stride/overlapping input', 'prototype.new_tensor(input)', 'same logical values but infer_dense_strides copy policy; never assert universal stride preservation')
case('STORAGE-ALIAS', 'copy contradiction', 'same-device, matching dtype TypedStorage/UntypedStorage from a nonempty tensor', 'prototype.new_tensor(storage); mutate result', 'Determine whether underlying storage aliases as predicted by set_(storage)+matching to(copy=False); preserve observed outcome and reconcile always-copy documentation. No universal no-alias assertion is allowed.', 'CPU', 'source_counterexample_candidate_unrun')
case('STORAGE-DTYPE', 'Storage error', 'typed float32 Storage; int64 receiver dtype', 'prototype.new_tensor(storage)', 'RuntimeError for typed-storage dtype mismatch before conversion; record any deprecation warning separately')
case('DLPACK-OBJECT', 'DLPack object', 'real producer with __dlpack__ and __dlpack_device__; known values and lifetime', 'prototype.new_tensor(producer)', 'consume valid capsule then copy to target dtype/device; producer mutation cannot change result; preserve stream/lifetime rules', 'matching producer/consumer device')
case('DLPACK-CAPSULE', 'DLPack boundary', 'raw DLPack capsule without __dlpack__ method', 'prototype.new_tensor(capsule)', 'No dedicated capsule branch; record exact rejection rather than assuming torch.from_dlpack capsule support transfers to this API', 'CPU', 'boundary_behavior_unrun')
case('OVERRIDE-KEYWORDS', 'override routing', 'Tensor subclass/TorchFunction mode computes a real Tensor while recording incoming args/kwargs', 'receiver.new_tensor(data, layout=torch.strided, pin_memory=False)', 'Override sees original kwargs before builtin parser; result contract belongs to extension; builtin unexpected-keyword claim must remain scoped')
case('WARNING-ERROR', 'error propagation', 'Tensor data; UserWarning promoted to error', 'prototype.new_tensor(source)', 'UserWarning aborts before normal return; warning cannot be silently swallowed')
case('META-SHAPE', 'symbolic-only path', 'meta prototype and rectangular data', 'prototype.new_tensor([[1,2],[3,4]])', 'meta result shape(2,2); no numerical execution/hardware credit')
case('RAGGED-SHAPE', 'sequence error', 'data [[1,2],[3]]', 'prototype.new_tensor(data)', 'ValueError for expected sequence length; no padded/ragged coercion')
case('CYCLIC-SHAPE', 'sequence error', 'first-element self-referential sequence', 'prototype.new_tensor(data)', 'Trace type_inference=False: compute_sizes max128 guard, not infer_scalar_type self-reference check. Confirm exact error without hanging', 'CPU', 'boundary_behavior_unrun')
case('LEGACY-DISTINCT', 'no constructor deduplication', 'source Tensor requires_grad True; list of integers', 'torch.Tensor(source); torch.tensor(source); prototype.new_tensor(source)', 'Legacy Tensor alias/AD, torch.tensor copied/input-inferred leaf, new_tensor receiver-typed copied Tensor route; verify each value/storage/gradient separately')
from source_contract import cite
for row in rows:
    prefix = row['id'].split('-')[0]
    row['sources'] = [cite('torch/csrc/utils/tensor_new.cpp', 'Tensor new_tensor(')]
    if prefix in ('KW', 'OVERRIDE'):
        row['sources'] += [cite('tools/autograd/templates/python_variable_methods.cpp', 'static PyObject * THPVariable_new_tensor('), cite('torch/csrc/utils/python_arg_parser.cpp', '[[noreturn]] static void extra_kwargs(')]
    elif prefix == 'STORAGE':
        row['sources'] += [cite('torch/csrc/utils/tensor_new.cpp', 'if (isStorage(data))'), cite('aten/src/ATen/native/TensorConversions.cpp', 'bool to_will_alias(')]
    elif prefix == 'NPY' or row['id'] == 'COPY-NUMPY':
        row['sources'] += [cite('torch/csrc/utils/tensor_numpy.cpp', 'at::Tensor tensor_from_numpy(')]
    elif prefix in ('LAYOUT', 'STRIDE'):
        row['sources'] += [cite('aten/src/ATen/native/TensorConversions.cpp', 'Tensor _to_copy(')]
    elif prefix == 'DTYPE':
        row['sources'] += [cite('torch/csrc/utils/python_arg_parser.h', 'inline at::ScalarType toScalarType('), cite('torch/csrc/utils/python_scalars.h', 'inline void store_scalar(')]
    elif prefix in ('RAGGED', 'CYCLIC'):
        row['sources'] += [cite('torch/csrc/utils/tensor_new.cpp', 'std::vector<int64_t> compute_sizes('), cite('torch/csrc/utils/tensor_new.cpp', 'void recursive_store(')]
    elif prefix == 'DLPACK':
        row['sources'] += [cite('torch/utils/dlpack.py', 'def from_dlpack(')]
    elif prefix == 'GRAD' or row['id'] == 'COPY-TENSOR':
        row['sources'] += [cite('torch/csrc/autograd/variable.h', 'void set_requires_grad('), cite('test/test_tensor_creation_ops.py', 'def test_tensor_factory_copy_var(')]
(ROOT / 'acceptance-cases.json').write_text(json.dumps({'schema_version': 1, 'framework': 'pytorch', 'version': '2.14.1', 'source_revision': '5c4886908584029761b579af026dcfb627c84070', 'case_count': len(rows), 'runtime_tests_executed': 0, 'cases': rows}, indent=2) + '\n', encoding='utf-8')
print('Unrun acceptance obligations', len(rows))
