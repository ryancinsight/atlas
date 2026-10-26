"""Finite source-parametric Torch dtype rules; no Torch/NumPy import or kernel claim."""
import ast
import itertools
import re

from atlas_parity_schema import need
from atlas_parity_tables import canonical


def body(text, name):
    match = re.search(re.escape(name) + r'\s*\(', text)
    need(match is not None, 'Torch source helper absent: ' + name)
    start = text.index('{', match.start());depth = 1;end = start + 1
    while depth and end < len(text):
        depth += (text[end] == '{') - (text[end] == '}');end += 1
    need(depth == 0, 'Torch bounded source helper unbalanced')
    return text[start + 1:end - 1]


def source_parts(witnesses):
    w = {r['id']: r['excerpt'] for r in witnesses['records']}
    enums = [(n, int(i)) for _, n, i in re.findall(r'_\((.*),\s*(\w+)\) /\* (\d+) \*/', w['enum-47'])]
    need(len(enums) == 47 and [i for _, i in enums] == list(range(47)), 'Torch source enum ordinal conservation')
    def names(name, source='dtype-classifiers'):
        return set(re.findall(r't == ScalarType::(\w+)', body(w[source], name)))
    f8 = names('isFloat8Type');reduced = names('isReducedFloatingType') | f8
    categories = {'integral_nonbool': sorted(names('isIntegralType') - {'Bool'}),
        'floating': sorted(names('isFloatingType') | reduced), 'float8': sorted(f8),
        'reduced_floating': sorted(reduced), 'complex': sorted(names('isComplexType')), 'bits': sorted(names('isBitsType')),
        'barebones_unsigned': sorted(names('isBarebonesUnsignedType')), 'quantized': sorted(names('isQIntType', 'enum-qint')), 'bool': ['Bool']}
    aliases = dict(re.findall(r'constexpr auto (\w+) = ScalarType::(\w+);', w['promote-axis']))
    match = re.search(r'index2dtype = std::to_array<c10::ScalarType>\(\s*\{([^}]+)\}', w['promote-axis'])
    need(match is not None, 'Torch source promotion axes absent')
    labels = [x.strip() for x in match[1].split(',')];axis = [aliases[x] for x in labels]
    rows = re.findall(r'/\* (\w+) \*/ \{([^}]+)\}', w['promote-table'])
    need(len(axis) == len(rows) == 14, 'Torch source lookup dimensions differ')
    cells = []
    for i, (label, values) in enumerate(rows):
        columns = [x.strip() for x in values.split(',') if x.strip()]
        need(label == labels[i] and len(columns) == 14, 'Torch source lookup row differs')
        for j, code in enumerate(columns):
            cells.append(dict(left=axis[i], right=axis[j], result=aliases[code], source_ref='promote-table'))
    ordered = w['promote-ordered']
    markers = ['a == ud || b == ud', 'a == b', 'isQIntType(a)', 'isBitsType(a)', 'isFloat8Type(a)',
               'isBarebonesUnsignedType(a)', 'auto ix_a', 'auto ix_b']
    positions = [ordered.find(x) for x in markers]
    need(all(x >= 0 for x in positions) and positions == sorted(positions), 'Torch native promotion guard order differs')
    return w, enums, categories, axis, cells


def promote(a, b, categories, axis, table):
    if a == 'Undefined' or b == 'Undefined':
        return dict(native_outcome='undefined', public_wrapper_outcome='unsupported_promotion_error', branch='undefined_first')
    if a == b:
        return dict(native_outcome='dtype', public_wrapper_outcome='dtype', dtype=a, branch='equal_before_unsupported')
    for key, branch, native, public in [('quantized', 'quantized', 'error', 'quantized_promotion_error'),
        ('bits', 'bits', 'undefined', 'unsupported_promotion_error'), ('float8', 'float8', 'error', 'float8_promotion_error')]:
        if a in categories[key] or b in categories[key]:
            return dict(native_outcome=native, public_wrapper_outcome=public, branch=branch)
    if a in categories['barebones_unsigned'] or b in categories['barebones_unsigned']:
        for t in (a, b):
            if t in categories['floating']:
                return dict(native_outcome='dtype', public_wrapper_outcome='dtype', dtype=t, branch='barebones_unsigned_with_float')
        return dict(native_outcome='error', public_wrapper_outcome='unsigned_promotion_error', branch='barebones_unsigned')
    for t, side in [(a, 'left'), (b, 'right')]:
        if t not in axis:
            return dict(native_outcome='internal_assert', public_wrapper_outcome='internal_assert_unqualified_public_reachability',
                        branch='unmapped_' + side + '_native_enum')
    return dict(native_outcome='dtype', public_wrapper_outcome='dtype', dtype=table[a, b], branch='core_lookup')


def can_cast(a, b, categories):
    if a in categories['complex'] and b not in categories['complex']: return False, 'complex_to_noncomplex'
    if a in categories['floating'] and b in categories['integral_nonbool']: return False, 'floating_to_integral'
    if a != 'Bool' and b == 'Bool': return False, 'nonbool_to_bool'
    return True, 'permitted_category_only'


def validate_model(model, witnesses, policies):
    w, enums, categories, axis, cells = source_parts(witnesses)
    need(canonical([(r['native_enum'], r['serialization_ordinal']) for r in model['native_enum_records']]) == canonical(enums) and
         model['classifiers'] == categories and model['core_lookup_axes'] == axis and
         canonical(model['core_lookup_cells']) == canonical(cells), 'Torch enum/classifier/core cell differs from pinned source')
    table = {(r['left'], r['right']): r['result'] for r in cells}
    native = [x for x, _ in enums]
    expected_promotion, expected_cast = [], []
    for a, b in itertools.product(native, repeat=2):
        expected_promotion.append(dict(left=a, right=b, **promote(a, b, categories, axis, table)))
        allowed, branch = can_cast(a, b, categories)
        expected_cast.append({'from': a, 'to': b, 'permitted': allowed, 'branch': branch})
    need(canonical(model['native_promotion_pairs']) == canonical(expected_promotion),
         'Torch ordered promotion pairs differ from independent source reconstruction')
    need(canonical(model['native_cast_permission_pairs']) == canonical(expected_cast),
         'Torch cast permission pairs differ from independent source reconstruction')
    opmath = [{'cpp_storage_type': a.strip(), 'cpp_computation_type': b.strip()} for a, b in
              re.findall(r'struct OpMathType<(.*?)>\s*\{\s*using type = (.*?);', w['opmath-native'], re.S)]
    need(canonical(opmath) == canonical(policies['native_opmath_specializations']) and len(opmath) == 9,
         'Torch source computation specializations differ')
    accumulators = []
    excerpt = next(r for r in witnesses['records'] if r['id'] == 'accumulation-native')
    for offset, line in enumerate(excerpt['excerpt'].splitlines()):
        match = re.match(r'(CPU|CUDA|MPS|XPU)_ACC_TYPE\((.*), ([^,]+)\)', line)
        if match:
            accumulators.append(dict(device_helper=match[1], cpp_storage_type=match[2], cpp_accumulator_type=match[3],
                line=excerpt['start_line'] + offset, conditional_cuda_or_hip_native_half=match[2] == 'half', source_ref='accumulation-native'))
    need(canonical(accumulators) == canonical(policies['native_accumulate_specializations']) and len(accumulators) == 73,
         'Torch source accumulator table differs')
    maps = {}
    for name in ['_computation_dtype_map', '_cpu_acc_type_map', '_complex_to_real_dtype_map', '_real_to_complex_dtype_map']:
        text = w['python-opmath-acc'] if name in {'_computation_dtype_map', '_cpu_acc_type_map'} else w['python-dtype-sets']
        match = re.search(re.escape(name) + r'\s*=\s*(\{.*?\})', text, re.S)
        need(match is not None, 'Torch source Python mapping absent')
        expr = ast.parse(match[1], mode='eval').body
        need(isinstance(expr, ast.Dict), 'Torch source Python mapping shape')
        maps[name] = {ast.unparse(k): ast.unparse(v) for k, v in zip(expr.keys, expr.values)}
    need(maps == policies['python_maps'], 'Torch source Python computation/accumulator maps differ')
    need('acc_type<scalar_t, true>' in w['sum-cpu-cascade'] and
         'self.suggest_memory_format() == memory_format' in w['to-alias-predicate'] and
         '!copy' in w['to-alias-predicate'], 'Torch sum callsite/compatible-format alias condition differs')
    trunc = w['div-cpu-trunc'].split('} else if')[0]
    need('TORCH_CHECK(b != 0' in trunc and 'return a / b' in trunc and 'numeric_limits' not in trunc,
         'Torch visible trunc guard cannot invent signed-overflow handling')
    return categories, axis, table


def result_type(operands, categories, axis, table):
    undefined = 'Undefined';state = {'dim': undefined, 'zero': undefined, 'wrapped': undefined}
    def combine(a, b):
        if a == undefined: return b
        if b == undefined: return a
        row = promote(a, b, categories, axis, table)
        need(row['native_outcome'] == 'dtype', 'Torch result_type fixture promotion leaves valid domain')
        return row['dtype']
    def categories_combine(higher, lower):
        if higher in categories['complex']: return higher
        if lower in categories['complex']:
            return {'Half': 'ComplexHalf', 'BFloat16': 'BComplex32', 'Float': 'ComplexFloat', 'Double': 'ComplexDouble'}[higher] if higher in categories['floating'] else lower
        if higher in categories['floating']: return higher
        if higher == 'Bool' or lower in categories['floating']: return combine(higher, lower)
        return higher if higher != undefined else lower
    for operand in operands:
        if operand['kind'] == 'tensor':
            need(type(operand['rank']) is int and operand['rank'] >= 0, 'Torch rank fixture must be nonnegative integer')
            key, dtype = ('dim' if operand['rank'] > 0 else 'zero'), operand['dtype']
        elif operand['kind'] == 'python_float': key, dtype = 'wrapped', operand['default_float']
        else:
            need(operand['kind'] == 'python_int', 'Torch bounded result fixture operand kind')
            key, dtype = 'wrapped', operand['dtype']
        state[key] = combine(state[key], dtype)
    return categories_combine(state['dim'], categories_combine(state['zero'], state['wrapped']))
