"""Typed exact-rational analytical controls, never framework execution evidence."""
from fractions import Fraction
import math
import struct

from atlas_parity_dtype_headers import exact_fields
from atlas_parity_schema import need


def exact_fraction(exact):
    try:
        rounded = struct.unpack('f', struct.pack('f', float(exact)))[0]
    except (ValueError, OverflowError):
        need(False, 'Torch oracle outside finite binary32-exact analytical domain')
    need(math.isfinite(rounded) and Fraction(rounded) == exact, 'Torch oracle component/intermediate not binary32-exact')
    return exact


def scalar(value):
    need(type(value) in (int, float), 'Torch oracle real component must be numeric, not bool/list/string')
    need(type(value) is int or math.isfinite(value), 'Torch oracle component must be finite')
    return exact_fraction(Fraction(value))


def complex_value(value):
    need(type(value) is dict, 'Torch oracle requires tagged complex object')
    exact_fields(value, {'kind': str, 'real': type(value.get('real')), 'imag': type(value.get('imag'))}, 'Torch tagged complex scalar')
    need(value['kind'] == 'complex', 'Torch oracle complex tag differs')
    return scalar(value['real']), scalar(value['imag'])


def tensor(value, dtype='complex64', leaf=False):
    fields = {'kind': str, 'dtype': str, 'shape': list, 'device': str, 'values': list}
    if leaf: fields['requires_grad'] = bool
    exact_fields(value, fields, 'Torch oracle native Tensor')
    need(value['kind'] == 'native_tensor' and value['dtype'] == dtype and value['shape'] == [] and
         value['device'] == 'cpu' and len(value['values']) == 1 and (not leaf or value['requires_grad'] is True),
         'Torch oracle rank-zero dtype/device/differentiable leaf differs')
    if dtype == 'complex64': return complex_value(value['values'][0])
    item = value['values'][0]
    need(type(item) is dict and set(item) == {'kind', 'value'} and item['kind'] == 'real', 'Torch oracle real scalar encoding')
    return scalar(item['value'])


def complex_add(fixture):
    exact_fields(fixture, {'operation': str, 'a': dict, 'b': dict, 'alpha': dict, 'loss': dict}, 'Torch oracle fixture')
    need(fixture['operation'] == 'torch.add.Tensor', 'Torch oracle operation differs')
    a, b = tensor(fixture['a'], leaf=True), tensor(fixture['b'], leaf=True)
    alpha = fixture['alpha']
    exact_fields(alpha, {'kind': str, 'python_type': str, 'value': dict}, 'Torch oracle Python Number alpha')
    need(alpha['kind'] == 'python_number' and alpha['python_type'] == 'complex', 'Torch oracle alpha must be Python complex Number')
    ar, ai = complex_value(alpha['value'])
    loss = fixture['loss']
    exact_fields(loss, {'kind': str, 'input': str, 'output_dtype': str, 'output_shape': list, 'upstream_cotangent': dict}, 'Torch oracle loss')
    need(loss['kind'] == 'real_sum' and loss['input'] == 'result' and loss['output_dtype'] == 'float32' and
         loss['output_shape'] == [], 'Torch oracle real scalar loss rank/dtype differs')
    exact_fields(loss['upstream_cotangent'], {'kind': str, 'value': type(loss['upstream_cotangent'].get('value'))}, 'Torch oracle cotangent')
    need(loss['upstream_cotangent']['kind'] == 'real', 'Torch oracle cotangent must be real')
    seed = scalar(loss['upstream_cotangent']['value'])
    rr, ii, ri, ir = [exact_fraction(x) for x in (ar * b[0], ai * b[1], ar * b[1], ai * b[0])]
    result = exact_fraction(a[0] + exact_fraction(rr - ii)), exact_fraction(a[1] + exact_fraction(ri + ir))
    return dict(result=result, real_loss=result[0], reverse_grad_a=(seed, Fraction(0)),
                reverse_grad_b=(exact_fraction(seed * ar), exact_fraction(-seed * ai)))


def validate_complex_case(case):
    need(case['id'] == 'ADD-COMPLEX-GRAD' and case['contract_id'] == 'PT-DTYPE-ADD', 'Torch complex source case identity differs')
    observed, expected = complex_add(case['fixture']), case['expected']
    exact_fields(expected, {'result': dict, 'real_loss': dict, 'reverse_grad_a': dict,
                           'reverse_grad_b': dict, 'source_conjugation': bool}, 'Torch complex result/gradient schema')
    need(expected['source_conjugation'] is True, 'Torch complex conjugation boundary differs')
    for key in ('result', 'reverse_grad_a', 'reverse_grad_b'):
        need(tensor(expected[key]) == observed[key], 'Torch input-sensitive complex result/gradient differs: ' + key)
    need(tensor(expected['real_loss'], 'float32') == observed['real_loss'], 'Torch input-sensitive real loss differs')
    return observed


def encoded_tensor(value, dtype='complex64', leaf=False):
    if dtype == 'complex64':
        item = {'kind': 'complex', 'real': float(value[0]), 'imag': float(value[1])}
    else: item = {'kind': 'real', 'value': float(value)}
    result = dict(kind='native_tensor', dtype=dtype, shape=[], device='cpu', values=[item])
    if leaf: result['requires_grad'] = True
    return result


def analytical_control(a, b, alpha, seed):
    fixture = {'operation': 'torch.add.Tensor', 'a': encoded_tensor(a, leaf=True), 'b': encoded_tensor(b, leaf=True),
        'alpha': {'kind': 'python_number', 'python_type': 'complex',
                  'value': {'kind': 'complex', 'real': alpha[0], 'imag': alpha[1]}},
        'loss': {'kind': 'real_sum', 'input': 'result', 'output_dtype': 'float32', 'output_shape': [],
                 'upstream_cotangent': {'kind': 'real', 'value': seed}}}
    result = complex_add(fixture)
    expected = {key: encoded_tensor(value, 'float32' if key == 'real_loss' else 'complex64') for key, value in result.items()}
    expected['source_conjugation'] = True
    return dict(id='ADD-COMPLEX-GRAD', contract_id='PT-DTYPE-ADD', fixture=fixture, expected=expected)
