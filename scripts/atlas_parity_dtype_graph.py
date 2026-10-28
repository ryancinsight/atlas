"""Finite source-symbol graph assertions; never imports a dtype runtime."""
from itertools import product

from atlas_parity_schema import need, unique


def expected_adjacency(catalog, strict, x64):
    strong = catalog['promotion_strong_symbols']
    integers = [n for n in strong if n.startswith(('strong:int', 'strong:uint'))]
    floats = [n for n in strong if n.startswith(('strong:float', 'strong:bfloat'))]
    complexes = [n for n in strong if n.startswith('strong:complex')]
    if strict:
        return {**{n: [] for n in strong}, 'weak:int': ['weak:float'] + integers,
                'weak:float': ['weak:complex'] + floats, 'weak:complex': complexes}
    small = [n for n in floats if n not in {'strong:bfloat16', 'strong:float16',
                                         'strong:float32', 'strong:float64'}]
    out = {'strong:bool': ['weak:int'],
           'weak:int': ['strong:uint8', 'strong:uint2', 'strong:uint4',
                        'strong:int8', 'strong:int2', 'strong:int4'],
           **{n: [] for n in small + ['strong:uint2', 'strong:uint4', 'strong:int2', 'strong:int4']},
           'strong:uint8': ['strong:int16', 'strong:uint16'],
           'strong:uint16': ['strong:int32', 'strong:uint32'],
           'strong:uint32': ['strong:int64' if x64 else 'strong:int32', 'strong:uint64'],
           'strong:uint64': ['weak:float'],
           'strong:int8': ['strong:int16'], 'strong:int16': ['strong:int32'],
           'strong:int32': ['strong:int64'], 'strong:int64': ['weak:float'],
           'weak:float': small + ['strong:bfloat16', 'strong:float16', 'weak:complex'],
           'strong:bfloat16': ['strong:float32'], 'strong:float16': ['strong:float32'],
           'strong:float32': ['strong:float64', 'strong:complex64'],
           'strong:float64': ['strong:complex128'], 'weak:complex': ['strong:complex64'],
           'strong:complex64': ['strong:complex128'], 'strong:complex128': []}
    for node in ['strong:int1', 'strong:uint1']:
        if node in strong:
            out['weak:int'].append(node)
            out[node] = []
    return out


def joins(adjacency):
    nodes = sorted(adjacency)
    positions = {node: i for i, node in enumerate(nodes)}
    need(all(type(v) is list and len(v) == len(set(v)) and set(v) <= set(nodes)
             for v in adjacency.values()), 'dtype graph: invalid or repeated edge')
    reach = [(1 << i) | sum(1 << positions[v] for v in adjacency[node])
             for i, node in enumerate(nodes)]
    for k in range(len(nodes)):
        for i in range(len(nodes)):
            if reach[i] & (1 << k):
                reach[i] |= reach[k]
    need(all(not (reach[i] & (1 << j) and reach[j] & (1 << i))
             for i in range(len(nodes)) for j in range(i)), 'dtype graph: cycle')
    result = {}
    for i, left in enumerate(nodes):
        for j, right in enumerate(nodes):
            common = reach[i] & reach[j]
            minimal = [c for c in range(len(nodes)) if common & (1 << c) and not any(
                d != c and common & (1 << d) and reach[d] & (1 << c) for d in range(len(nodes)))]
            need(len(minimal) <= 1, 'dtype graph: nonunique least upper bound')
            result[left, right] = nodes[minimal[0]] if minimal else None
    return result


def validate_graphs(packet, catalog):
    need(packet['source_symbol_graph_not_framework_execution'] is True and
         packet['whole_dtype_or_api_legality_complete'] is False and
         type(packet['runtime_cases_executed']) is int and packet['runtime_cases_executed'] == 0 and
         catalog['full_api_legality_complete'] is False, 'dtype graph/catalog whole-API credit forbidden')
    need(len(catalog['profiles']) == 2 and
         {r['companion_int1_uint1_present'] for r in catalog['profiles']} == {False, True} and
         all(type(r['companion_int1_uint1_present']) is bool for r in catalog['profiles']),
         'dtype catalog profile conservation drift')
    for cat in catalog['profiles']:
        strong = set(cat['promotion_strong_symbols'])
        categories = set().union(*map(set, cat['category_members'].values()))
        need(cat['weak_nodes'] == ['weak:int', 'weak:float', 'weak:complex'] and
             set(cat['valid_native_dtype_symbols']) == strong | {'strong:float0', 'strong:StringDType'} and
             categories == strong and 'strong:bool' not in cat['category_members']['numeric'] and
             cat['native_registry_or_kernel_acceptance_executed'] is False,
             'dtype category/valid/weak/graph domain distinction drift')
    profiles = unique(packet['profiles'], 'id', 'dtype companion profile')
    graphs = unique(packet['graphs'], 'id', 'dtype graph')
    need(set(profiles) == {f'int1_{i}_uint1_{j}' for i, j in product([0, 1], repeat=2)} and
         len(graphs) == 8, 'dtype graph/profile count drift')
    count = 0
    for label, profile in profiles.items():
        i, u = profile['companion_attributes']['int1'], profile['companion_attributes']['uint1']
        need(type(i) is bool and type(u) is bool and label == f'int1_{int(i)}_uint1_{int(u)}',
             'dtype companion guards drift')
        need(profile['initialization_runtime'] == 'unrun', 'dtype profile runtime credit forbidden')
        expected = [label + ('_strict' if strict else '_standard') + ('_x64' if x64 else '_x32')
                    for strict, x64 in product([False, True], repeat=2)] if i == u else []
        need(profile['graphs'] == expected, 'dtype conditional graph selection drift')
        if i != u:
            need(profile['source_initialization_disposition'] == 'conditional_companion_shape_rejects' and
                 profile['source_error'] == ('AssertionError' if i else 'ValueError') and
                 '14-target/13-value' in profile['exception_qualification'],
                 'dtype one-sided source guard/error proof drift')
    for identity, graph in graphs.items():
        profile = profiles.get(graph['companion_profile'])
        need(profile is not None and identity in profile['graphs'] and
             type(graph['strict']) is bool and type(graph['enable_x64']) is bool,
             'dtype graph config/profile join drift')
        need(identity == profile['id'] + ('_strict' if graph['strict'] else '_standard') +
             ('_x64' if graph['enable_x64'] else '_x32'), 'dtype graph config spelling drift')
        present = profile['companion_attributes']['int1']
        guards = [('_int1_dtype is not None', 706, present), ('not strict', 714, not graph['strict'])]
        if not graph['strict']:
            guards += [('i1 is not None', 740, present), ('u1 is not None', 743, present),
                       ('not x64', 750, not graph['enable_x64'])]
        need(graph['source_branch_selections'] == [dict(condition=c, line=n, selected=v) for c, n, v in guards]
             and all(type(r['selected']) is bool for r in graph['source_branch_selections']),
             'dtype source profile/config guard selection drift')
        cats = [r for r in catalog['profiles'] if r['companion_int1_uint1_present'] is present]
        need(len(cats) == 1, 'dtype catalog profile absent')
        cat = cats[0]; adjacency = graph['adjacency']
        need(adjacency == expected_adjacency(cat, graph['strict'], graph['enable_x64']),
             'dtype source edges differ from reviewed promotion policy')
        need(set(adjacency) == set(cat['promotion_strong_symbols']) | set(cat['weak_nodes']) and
             len(adjacency) == graph['nodes'] == (35 if present else 33) and
             graph['edges'] == sum(map(len, adjacency.values())), 'dtype graph node/edge conservation drift')
        oracle = joins(adjacency)
        table = graph['pair_table']
        pairs = {(r['left'], r['right']): r for r in table}
        need(len(pairs) == len(table) == graph['nodes'] ** 2 and pairs.keys() == oracle.keys(),
             'dtype source pair conservation drift')
        for pair, row in pairs.items():
            need(row['lub_source_symbol'] == oracle[pair] and
                 row['source_graph_result'] == ('unique_lub' if oracle[pair] else
                    'TypePromotionError_no_common_upper_bound') and
                 row['final_numpy_dtype_or_api_legality_verified'] is False,
                 'dtype source join/error differs or falsely qualifies API legality')
        need(graph['framework_cases_executed'] == 0 and type(graph['framework_cases_executed']) is int and
             graph['api_dtype_legality_complete'] is False and
             graph['pair_table_complete_for_finite_source_graph'] is True,
             'dtype graph must remain finite source-only evidence')
        count += len(table)
    need(count == 9256 and packet['counts'] == {'conditional_profiles': 4, 'constructible_profiles': 2,
         'graphs': 8, 'ordered_binary_source_symbol_pairs': count}, 'dtype graph aggregate drift')
    return count
