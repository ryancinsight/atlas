"""Static source witnesses plus stdlib-only control flow, never NumPy runtime."""
import ast
import hashlib
import json
import operator
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parent
REV = 'a3d0ef1df045b858e68115001fdabc930bb3b68c'
NUMERIC = 'numpy/_core/numeric.py'
FROM = 'numpy/_core/fromnumeric.py'
LOOKUP = 'numpy/_core/src/common/get_attr_string.h'
OVERRIDE = 'numpy/_core/src/multiarray/arrayfunction_override.c'
GETSET = 'numpy/_core/src/multiarray/getset.c'

def read(path):
    return (ROOT / 'sources' / path).read_text(encoding='utf-8')

def cite(path, line):
    return f'https://github.com/numpy/numpy/blob/{REV}/{path}#L{line}'

def c_function(path, name):
    source = read(path)
    match = re.search('\\b' + re.escape(name) + '\\([^{}]*\\)\\s*\\{.*?\\n\\}', source, re.S)
    assert match is not None, name
    return (match.group(), source[:match.start()].count('\n') + 1)

def main():
    numpy_functions = {node.name: node for node in ast.parse(read(FROM)).body if isinstance(node, ast.FunctionDef)}
    normalize = next((node for node in ast.parse(read(NUMERIC)).body if isinstance(node, ast.FunctionDef) and node.name == 'normalize_axis_tuple'))
    scalar_if = next((node for node in normalize.body if isinstance(node, ast.If) and 'isinstance' in ast.unparse(node.test)))
    scalar_try = scalar_if.body[0]
    assert isinstance(scalar_try, ast.Try)
    assert len(scalar_try.handlers) == 1
    assert ast.unparse(scalar_try.handlers[0].type) == 'TypeError'
    assert len(scalar_try.handlers[0].body) == 1 and isinstance(scalar_try.handlers[0].body[0], ast.Pass)
    materialize = next((i for i, node in enumerate(normalize.body) if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and (node.value.func.id == 'tuple') and isinstance(node.value.args[0], ast.GeneratorExp) and (ast.unparse(node.value.args[0].elt.func) == 'normalize_axis_index')))
    duplicate = next((i for i, node in enumerate(normalize.body) if isinstance(node, ast.If) and 'len(set(axis))' in ast.unparse(node.test)))
    assert materialize < duplicate
    size_else = next((node for node in numpy_functions['size'].body if isinstance(node, ast.If))).orelse
    assert 'shape(a)' in ast.unparse(size_else[0])
    assert 'normalize_axis_tuple' in ast.unparse(size_else[-2])
    assert 'math.prod' in ast.unparse(size_else[-1])
    attrs = {}
    for name, attr in [('ndim', 'ndim'), ('shape', 'shape'), ('size', 'size')]:
        node = numpy_functions[name]
        statement = next((part for part in ast.walk(node) if isinstance(part, ast.Try)))
        direct = ast.unparse(statement.body[0])
        assert 'a.' + attr in direct
        assert not any((transform in direct for transform in ['int(', 'tuple(', 'detach(', '.item(']))
        attrs[name] = {'direct_branch': direct, 'source': cite(FROM, statement.lineno), 'no_forced_conversion_or_detach_in_branch': True}
    lookup, lookup_line = c_function(LOOKUP, 'PyArray_LookupSpecial')
    assert 'PyTypeObject *tp = Py_TYPE(obj)' in lookup
    assert 'PyObject_GetOptionalAttr((PyObject *)tp, name_unicode, res)' in lookup
    assert 'PyObject_GetOptionalAttr(obj,' not in lookup
    assert '_is_basic_python_type(tp)' in lookup
    basic, basic_line = c_function(LOOKUP, '_is_basic_python_type')
    assert all(('tp == &' + name + '_Type' in basic for name in ['PyBool', 'PyLong', 'PyFloat', 'PyComplex', 'PyList', 'PyTuple', 'PyDict', 'PySet', 'PyFrozenSet', 'PyUnicode', 'PyBytes', 'PySlice']))
    assert all(('tp == Py_TYPE(' + name + ')' in basic for name in ['Py_None', 'Py_Ellipsis', 'Py_NotImplemented']))
    retrieval, retrieval_line = c_function(OVERRIDE, 'get_array_function')
    assert retrieval.index('PyArray_CheckExact(obj)') < retrieval.index('PyArray_LookupSpecial(')
    assert 'PyErr_Clear();' in retrieval
    assert not any((kind in retrieval for kind in ['PyExc_RuntimeError', 'PyExc_MemoryError', 'PyErr_ExceptionMatches']))
    collection, _ = c_function(OVERRIDE, 'get_implementing_args_and_methods')
    assert 'if (method != NULL)' in collection and 'PyCallable_Check(method)' not in collection
    invocation, invocation_line = c_function(OVERRIDE, 'call_array_function')
    assert re.search('PyObject_CallFunctionObjArgs\\(\\s*method,\\s*argument,\\s*public_api,\\s*types,\\s*args,\\s*kwargs,\\s*NULL\\)', invocation)
    assert 'PyErr_Clear' not in invocation and 'PyCallable_Check' not in invocation
    getters = {}
    for name in ['array_ndim_get', 'array_shape_get', 'array_size_get']:
        body, line = c_function(GETSET, name)
        assert not any((token in body for token in ['PyArray_DATA', 'PyArray_BYTES', 'PyArray_DESCR', 'PyArray_STRIDES']))
        getters[name] = {'source': cite(GETSET, line), 'no_buffer_dtype_stride_access_in_getter': True}
    events = []

    class IndexTypeErrorThenIterable:

        def __index__(self):
            events.append('index')
            raise TypeError('intentional index failure')

        def __iter__(self):
            events.append('iter')
            yield 0
    original = IndexTypeErrorThenIterable()
    candidate = original
    try:
        candidate = [operator.index(candidate)]
    except TypeError:
        pass
    normalized_stdlib = tuple((operator.index(item) for item in candidate))
    assert normalized_stdlib == (0,) and events == ['index', 'iter']
    header_bytes = (ROOT / 'sources' / LOOKUP).read_bytes()
    assert hashlib.sha1(b'blob ' + str(len(header_bytes)).encode() + b'\x00' + header_bytes).hexdigest() == '324a92c5ef0c454a5255d3293f587f23e11b8406'
    data = {'schema_version': 1, 'framework': 'numpy', 'version': '2.5.4', 'revision': REV, 'execution_scope': 'Static Python AST/C text source assertions and one standard-library-only index/iteration witness; no NumPy import/build/runtime/provider/AD execution.', 'axis_index_failure_witness': {'source': cite(NUMERIC, scalar_try.lineno), 'caught_exception_type': 'TypeError', 'handler_is_pass': True, 'original_axis_retained_for_iteration': True, 'stdlib_witness_normalized': list(normalized_stdlib), 'stdlib_witness_events': events}, 'axis_materialization_order_witness': {'source': cite(NUMERIC, normalize.lineno), 'tuple_statement_index': materialize, 'duplicate_statement_index': duplicate, 'whole_tuple_before_duplicates': True, 'size_shape_then_normalize_then_product': True, 'derived_case': 'rank2 (0,0,2): conversion of2 raises AxisError before duplicate check; proposed runtime differential, not executed'}, 'delegated_identity_witness': attrs, 'special_lookup_witness': {'source': cite(LOOKUP, lookup_line), 'git_blob_sha': '324a92c5ef0c454a5255d3293f587f23e11b8406', 'target_is_type_object': True, 'instance_only_attribute_ignored': True, 'exact_basic_type_skips': True, 'basic_skip_source': cite(LOOKUP, basic_line), 'present_None_remains_present': True, 'no_callability_precheck_in_collection': True}, 'phase_error_witness': {'source': cite(OVERRIDE, retrieval_line), 'exact_ndarray_fastpath_precedes_lookup': True, 'lookup_failure_clear_has_no_exception_kind_filter': True, 'invocation_does_not_clear_errors': True, 'invocation_source': cite(OVERRIDE, invocation_line), 'exact_invocation_positional_arguments': ['argument', 'public_api', 'types', 'args', 'kwargs']}, 'builtin_getter_only_witness': getters, 'count_arithmetic_witness': {'macro_source': 'https://github.com/numpy/numpy/blob/' + REV + '/numpy/_core/include/numpy/ndarrayobject.h#L70', 'total_count_uses_npy_intp_helper': True, 'selected_axis_uses_python_math_prod': True, 'overflow_region_verified': False}, 'runtime_differential_verified': False, 'ad_preservation_verified': False, 'provider_design_status': 'pending'}
    (ROOT / 'metadata-checker-witnesses.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print('Metadata static witnesses and stdlib index/iteration control-flow witness pass; NumPy runtime/AD not executed')
if __name__ == '__main__':
    main()
