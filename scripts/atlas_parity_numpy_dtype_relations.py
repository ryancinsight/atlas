"""Reconstruct finite NumPy source relations without running foreign code."""
import ast
import re

from atlas_parity_schema import ParityError, need
from atlas_parity_tables import canonical

TYPES = ['BOOL', 'BYTE', 'UBYTE', 'SHORT', 'USHORT', 'INT', 'UINT', 'LONG', 'ULONG',
         'LONGLONG', 'ULONGLONG', 'FLOAT', 'DOUBLE', 'LONGDOUBLE', 'CFLOAT', 'CDOUBLE',
         'CLONGDOUBLE', 'OBJECT', 'STRING', 'UNICODE', 'VOID', 'DATETIME', 'TIMEDELTA', 'HALF']
TABLE_SOURCE = 'numpy/_core/src/multiarray/can_cast_table.h:L1-L124'
META_SOURCE = 'numpy/_core/src/multiarray/scalartypes.c.src:L4326-L4491'


def split_arguments(text):
    result, start, depth = [], 0, 0
    for i, token in enumerate(text):
        if token in '({':
            depth += 1
        elif token in ')}':
            depth -= 1
            need(depth >= 0, 'NumPy symbolic source delimiter underflow')
        elif token == ',' and depth == 0:
            result.append(text[start:i].strip())
            start = i + 1
    need(depth == 0, 'NumPy symbolic source unclosed delimiter')
    if text[start:].strip():
        result.append(text[start:].strip())
    return result


def predicate(text):
    """A closed comparison/boolean grammar, not eval or a C preprocessor."""
    try:
        tree = ast.parse(text.strip().replace('&&', ' and ').replace('||', ' or '), mode='eval')
    except SyntaxError as error:
        raise ParityError('NumPy symbolic predicate syntax') from error
    def visit(node):
        if isinstance(node, ast.Constant):
            need(type(node.value) is int and node.value >= 0, 'NumPy symbolic integer literal')
            return node.value
        if isinstance(node, ast.Name):
            need(re.fullmatch(r'NPY_SIZEOF_[A-Z_]+', node.id) is not None, 'NumPy symbolic ABI name')
            return {'abi': node.id}
        if isinstance(node, ast.Compare):
            need(len(node.ops) == len(node.comparators) == 1, 'NumPy symbolic comparison arity')
            operations = {ast.Lt: '<', ast.LtE: '<=', ast.Gt: '>', ast.GtE: '>=', ast.Eq: '=='}
            need(type(node.ops[0]) in operations, 'NumPy symbolic comparison operation')
            return [operations[type(node.ops[0])], visit(node.left), visit(node.comparators[0])]
        if isinstance(node, ast.BoolOp):
            need(type(node.op) in {ast.And, ast.Or}, 'NumPy symbolic boolean operation')
            operation = 'and' if isinstance(node.op, ast.And) else 'or'
            values = [visit(value) for value in node.values]
            result = values[0]
            for value in values[1:]:
                result = [operation, result, value]
            return result
        need(False, 'NumPy symbolic predicate forbidden syntax')
    return visit(tree.body)


def source_cells(text):
    clean = re.sub(r'/\*.*?\*/', '', text, flags=re.S).replace('\\\n', ' ')
    macros = {}
    for line in clean.splitlines():
        found = re.fullmatch(r'\s*#define\s+(\w+)\(([^)]*)\)\s+(.*)', line)
        if found:
            macros[found[1]] = (split_arguments(found[2]), found[3])
    need(set(macros) == {'FITS', 'UFITS', 'IFITS', 'CASTS_SAFELY_FROM_UINT',
                        'CASTS_SAFELY_FROM_INT', 'CASTS_SAFELY_FROM_FLOAT',
                        'CASTS_SAFELY_FROM_CFLOAT'}, 'NumPy symbolic macro set changed')
    def expand(value, ancestors=()):
        match = re.search(r'\b(' + '|'.join(macros) + r')\(', value)
        if not match:
            return re.sub(r'\s*##\s*', '', value)
        name = match[1]
        need(name not in ancestors, 'NumPy symbolic recursive macro')
        depth, end = 1, match.end()
        while depth and end < len(value):
            depth += (value[end] == '(') - (value[end] == ')')
            end += 1
        need(depth == 0, 'NumPy symbolic macro arity delimiter')
        arguments = split_arguments(value[match.end():end - 1])
        parameters, body = macros[name]
        need(len(arguments) == len(parameters), 'NumPy symbolic macro arity')
        for key, replacement in zip(parameters, arguments):
            body = re.sub(r'\b' + re.escape(key) + r'\b', lambda _: replacement, body)
        expanded = expand(body, ancestors + (name,))
        return expand(value[:match.start()] + expanded + value[end:], ancestors)
    found = re.search(r'_npy_can_cast_safely_table\[[^=]+?=\s*\{(.*?)\};', clean, re.S)
    need(found is not None, 'NumPy symbolic source initializer absent')
    rows = split_arguments(expand(found[1]))
    need(len(rows) == 24, 'NumPy symbolic source row count')
    result = []
    for i, row in enumerate(rows):
        need(row.startswith('{') and row.endswith('}'), 'NumPy symbolic row structure')
        columns = split_arguments(row[1:-1])
        need(len(columns) == 24, 'NumPy symbolic source column count')
        for j, expression in enumerate(columns):
            result.append(dict(from_type=TYPES[i], to_type=TYPES[j], ordinal=[i, j],
                               predicate=predicate(expression)))
    return result


def template_values(text):
    result = []
    for token in split_arguments(text):
        match = re.fullmatch(r'(?:\((.*?)\)|(\w+))\*(\d+)', token)
        if match:
            result.extend((split_arguments(match[1]) if match[1] else [match[2]]) * int(match[3]))
        else:
            result.append(token)
    return result


def source_metadata(text):
    match = re.search(r'#NAME\s*=(.*?)#\s*\*\s*#BIGGERTYPE\s*=(.*?)#\s*\*\s*#SCKIND\s*=(.*?)#', text, re.S)
    need(match is not None, 'NumPy promotion template metadata absent')
    values = [template_values(re.sub(r'\n\s*\*\s*', ' ', value).strip()) for value in match.groups()]
    names, larger, kinds = values
    need(len(names) == len(larger) == len(kinds) == 18, 'NumPy promotion template arity')
    smallest = dict(re.findall(r'_npy_smallest_type_of_kind_table\[NPY_(\w+)_SCALAR\] = NPY_(\w+);', text))
    need(set(smallest) == {'BOOL', 'INTPOS', 'INTNEG', 'FLOAT', 'COMPLEX', 'OBJECT'},
         'NumPy promotion smallest-kind source assignments')
    return {'names': names, 'next_larger': {n: None if b == '-1' else b.removeprefix('NPY_')
            for n, b in zip(names, larger)}, 'scalar_kind': dict(zip(names, kinds)),
            'kind_order': ['BOOL', 'INTPOS', 'INTNEG', 'FLOAT', 'COMPLEX', 'OBJECT'], 'smallest': smallest}


def evaluate(node, abi):
    if type(node) is int:
        return node
    if type(node) is dict:
        need(set(node) == {'abi'} and node['abi'] in abi, 'NumPy symbolic ABI parameter absent')
        return abi[node['abi']]
    need(type(node) is list and len(node) == 3, 'NumPy symbolic expression shape')
    operation, left, right = node
    a, b = evaluate(left, abi), evaluate(right, abi)
    if operation == 'and': return bool(a and b)
    if operation == 'or': return bool(a or b)
    if operation == '<': return a < b
    if operation == '<=': return a <= b
    if operation == '>': return a > b
    if operation == '>=': return a >= b
    need(operation == '==', 'NumPy symbolic operator absent')
    return a == b


def initializer(safe, metadata):
    """Interpret selected initialization decisions; descriptor callbacks remain outside."""
    positions = {name: i for i, name in enumerate(TYPES)}
    result = [[-1] * 24 for _ in TYPES]
    deferred = {'STRING', 'UNICODE', 'VOID', 'DATETIME', 'TIMEDELTA'}
    order = metadata['kind_order']
    for i, first in enumerate(TYPES):
        result[i][i] = -1 if first in deferred else i
        if first in deferred:
            result[i][positions['OBJECT']] = result[positions['OBJECT']][i] = positions['OBJECT']
            continue
        for j in range(i + 1, 24):
            second = TYPES[j]
            if second in {'STRING', 'UNICODE', 'VOID'}:
                choice = -1
            elif safe[i][j]: choice = j
            elif safe[j][i]: choice = i
            else:
                first_kind = metadata['scalar_kind'].get(first, 'OBJECT')
                second_kind = metadata['scalar_kind'].get(second, 'OBJECT')
                if order.index(first_kind) > order.index(second_kind):
                    kind, candidate = first_kind, first
                else:
                    kind, candidate = second_kind, second
                visited = set()
                while True:
                    need((kind, candidate) not in visited, 'NumPy promotion source initializer cycle')
                    visited.add((kind, candidate))
                    candidate = metadata['next_larger'].get(candidate)
                    if candidate is None:
                        rank = order.index(kind) + 1
                        if rank == len(order):
                            choice = -1
                            break
                        kind = order[rank]
                        candidate = metadata['smallest'][kind]
                    k = positions[candidate]
                    if safe[i][k] and safe[j][k]:
                        choice = k
                        break
            result[i][j] = result[j][i] = choice
    return result


def validate_relations(policy, citations):
    need(policy['schema_version'] == 1 and policy['type_order'] == TYPES and
         policy['build_generated_abi_values_observed'] is False and
         policy['public_api_or_runtime_credit'] is False, 'NumPy symbolic policy scope drift')
    need(policy['safe_policy']['source'] == TABLE_SOURCE and policy['promotion_metadata']['source'] == META_SOURCE,
         'NumPy symbolic source association drift')
    expected = source_cells(citations[TABLE_SOURCE]['text'])
    cells = policy['safe_policy']['cells']
    need(len(cells) == 576 and len({tuple(c['ordinal']) for c in cells}) == 576,
         'NumPy symbolic cell conservation drift')
    for actual, wanted in zip(cells, expected):
        need(set(actual) == {'from_type', 'to_type', 'ordinal', 'predicate', 'c_expression'} and
             canonical({key: actual[key] for key in wanted}) == canonical(wanted) and
             canonical(predicate(actual['c_expression'])) == canonical(wanted['predicate']),
             'NumPy symbolic relation differs from independently expanded pinned source')
    metadata = source_metadata(citations[META_SOURCE]['text'])
    need(all(policy['promotion_metadata'][key] == value for key, value in metadata.items()),
         'NumPy promotion metadata differs from pinned source')
    profiles = policy['illustrative_abi_profiles']
    need(len(profiles) == 2 and {p['name'] for p in profiles} == {'LP64_extended16', 'LLP64_double8'},
         'NumPy illustrative ABI profile conservation')
    for profile in profiles:
        abi = profile['abi_parameters']
        need(profile['status'] == 'analytical_profile_only_reference_and_provider_unrun' and
             all(type(v) is int and v > 0 for v in abi.values()), 'NumPy ABI observation/runtime credit forbidden')
        matrix = [[bool(evaluate(c['predicate'], abi)) for c in cells[i * 24:(i + 1) * 24]] for i in range(24)]
        need(type(profile['safe_table']) is list and len(profile['safe_table']) == 24 and
             all(type(row) is list and len(row) == 24 and all(type(v) is bool for v in row) for row in profile['safe_table']) and
             type(profile['promotion_initializer_table']) is list and len(profile['promotion_initializer_table']) == 24 and
             all(type(row) is list and len(row) == 24 and all(type(v) is int for v in row) for row in profile['promotion_initializer_table']) and
             profile['safe_table'] == matrix and profile['promotion_initializer_table'] == initializer(matrix, metadata),
             'NumPy illustrative ABI source relation/initializer drift')
        need(all(profile['promotion_initializer_table'][i][j] == profile['promotion_initializer_table'][j][i]
                 for i in range(24) for j in range(24)), 'NumPy source initializer symmetry drift')
    return 576
