"""No-runtime integrity/traceability assertions for the temporary TF handoff."""
import hashlib, json, ast
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
ROOT = Path(__file__).resolve().parent
RESULT = []

def sha(b):
    return hashlib.sha256(b).hexdigest()

def load(p):
    return json.loads((ROOT / p).read_bytes())

def check(ident, fn):
    try:
        detail = fn()
        RESULT.append({'id': ident, 'result': 'pass', 'detail': detail})
    except Exception as e:
        RESULT.append({'id': ident, 'result': 'fail', 'detail': repr(e)})

def sources():
    count = 0
    for name in ['tensorflow', 'keras']:
        d = load(name + '-source-manifest.json')
        assert d['selected_count'] == d['verified_count'] == len(d['files'])
        for x in d['files']:
            b = (ROOT / 'source' / name / x['path']).read_bytes()
            assert len(b) == x['bytes']
            assert sha(b) == x['sha256']
            assert hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\x00' + b).hexdigest() == x['git_blob_sha']
            count += 1
    assert count == 4134
    return {'verified_source_files': count, 'runtime_execution': False}
check('A001-source-identities', sources)
D = load('declaration-relations.json')
K = load('keras-reachable-exports.json')
I = load('keras-inherited-members.json')
C = load('constructor-contracts.json')

def input_identity():
    p = Path(D['inventory_input']['path'])
    assert sha(p.read_bytes()) == D['inventory_input']['sha256']
    d = json.loads(p.read_bytes())
    assert len(d['records']) == 24589
    return D['inventory_input']
check('A002-frozen-input-unchanged', input_identity)

def views():
    x = D['same_endpoint_declaration_views']
    assert len(x) == 1210
    assert all((len(r['declaration_ids']) == 2 and (not r['semantic_equivalence_asserted']) for r in x))
    return {'same_endpoint_views': len(x), 'equivalence_assertions': 0}
check('A003-declaration-views-not-capabilities', views)

def spellings():
    x = D['v1_v2_spelling_candidates']
    assert len(x) == 6030
    assert all((not r['semantic_equivalence_asserted'] for r in x))
    c = Counter((r['signatures'] for r in x))
    assert c['different_declared_signatures'] == 188
    assert c['equal_declared_signatures'] == 4069
    return dict(c)
check('A004-same-spelling-is-not-equivalence', spellings)

def exports():
    x = D['tf_export_groups']
    assert len(x) == 2193
    assert not D['unresolved_tf_exports'] and (not D['parse_errors'])
    assert all((r['target'] and (not r['semantic_equivalence_asserted']) for r in x))

    def groups(n):
        return [r for r in x if n in r['endpoints']]
    assert any(('tf.compat.v1.zeros' in r['endpoints'] for r in groups('tf.zeros')))
    assert not any(('tf.compat.v1.zeros_like' in r['endpoints'] for r in groups('tf.zeros_like')))
    missing = {n for r in x for n in r['missing_from_frozen_inventory']}
    assert len(missing) == 252
    assert len([n for n in missing if n.startswith('tf.experimental.numpy.')]) == 236
    return {'source_export_groups': len(x), 'missing_source_export_endpoints_retained': len(missing), 'experimental_numpy_missing_endpoints': 236}
check('A005-export-identities-and-omissions', exports)

def reachable():
    assert not K['unhandled']
    assert K['counts']['distinct_symbols'] == 1653
    assert not K['new_symbols_absent_from_initial_inventory']
    assert len(K['initial_symbols_not_reached']) == 14
    assert any((r['symbol'] == 'tf.keras.ops.linspace' for r in K['records']))
    return K['counts']
check('A006-generated-module-reachability', reachable)

def inherited():
    assert not I['parse_errors']
    assert not I['unresolved_mro']
    assert not I['inherited_member_surface_complete']
    assert I['counts']['public_class_exports'] == 407
    assert I['counts']['distinct_public_class_targets'] == 338
    assert I['counts']['member_declarations'] == 11207
    assert I['counts']['inherited_member_declarations'] == 9389
    assert I['external_inheritance_boundaries']
    dense = next((r for r in I['class_exports'] if r['symbol'] == 'tf.keras.layers.Dense'))
    m = next((r for r in dense['members'] if r['name'] == 'add_weight'))
    assert m['inherited'] and m['defining_class'] == 'keras.src.layers.layer.Layer'
    symbolic = next((r for r in I['class_exports'] if r['symbol'] == 'tf.keras.KerasTensor'))
    dtype = next((r for r in symbolic['members'] if r['name'] == 'dtype'))
    assert dtype['kind'] == 'property'
    assert {x['accessor_role'] for x in dtype['declarations']} == {'getter', 'setter'}
    return {'candidate_members': 11207, 'inherited_candidates': 9389, 'public_capability_completeness_asserted': False, 'external_boundaries': I['external_inheritance_boundaries']}
check('A007-inherited-member-provenance', inherited)

def gradients():
    p = ROOT / 'source/tensorflow/tensorflow/python/ops'
    m = (p / 'math_grad.py').read_text(encoding='utf-8')
    a = (p / 'array_grad.py').read_text(encoding='utf-8')
    assert 'ops.NotDifferentiable("Range")' in m and 'ops.NotDifferentiable("LinSpace")' in m
    assert '@ops.RegisterGradient("Fill")' in a and 'return None, math_ops.reduce_sum(grad)' in a
    math_ast = ast.parse((p / 'math_ops.py').read_bytes())
    fn = next((x for x in math_ast.body if isinstance(x, ast.FunctionDef) and x.name == 'linspace_nd'))
    calls = [ast.unparse(x.func) for x in ast.walk(fn) if isinstance(x, ast.Call)]
    assert not any((x in ['gen_math_ops.lin_space', 'gen_math_ops.linspace'] for x in calls))
    assert 'array_ops.slice' in calls
    return 'High-level linspace is a distinct composite; raw LinSpace/Range have explicit nondifferentiability declarations.'
check('A008-constructor-gradient-source-proofs', gradients)

def residency():
    p = ROOT / 'source/tensorflow/tensorflow'
    k = (p / 'core/kernels/sequence_ops.cc').read_text(encoding='utf-8')
    assert '.HostMemory("output")' in k
    f = (p / 'compiler/tf2xla/kernels/fill_op.cc').read_text(encoding='utf-8')
    assert 'CompileTimeConstantInput("dims")' in f
    assert 'Currently we do not support filling strings on GPU' in (p / 'core/kernels/constant_op.cc').read_text(encoding='utf-8')
    return 'Host-output and compiler-constant constraints retained; no native-device execution result inferred.'
check('A009-device-and-jit-source-proofs', residency)

def analytical():
    a, b = (F(1), F(5))
    alpha = [F(0), F(1, 2), F(1)]
    y = [(1 - x) * a + x * b for x in alpha]
    assert y == [1, 3, 5]
    g = [1, 2, 4]
    da = sum((v * (1 - x) for v, x in zip(g, alpha)))
    db = sum((v * x for v, x in zip(g, alpha)))
    assert (da, db) == (2, 5)
    jvp = [(1 - x) * 2 + x * -2 for x in alpha]
    assert jvp == [2, 0, -2]
    assert [F(3) - F(1, 2) * i for i in range(4)] == [F(3), F(5, 2), F(2), F(3, 2)]
    assert sum([1, 2, 3, 4, 5, 6]) == 21
    assert sum((1 - x for x in alpha)) * 3 == F(9, 2)
    assert sum(alpha) * 2 == 3
    return {'exact_rational_oracles': 'interpolation, broadcast adjoints, VJP, JVP, half-open progression and Fill VJP', 'reference_runtime_execution': False}
check('A010-independent-analytical-oracles', analytical)

def contracts():
    assert len(C['contracts']) == 9 and len(C['test_specifications']) == 40
    assert len({r['id'] for r in C['test_specifications']}) == 40
    for x in C['contracts']:
        assert not x['reference_runtime_verified'] and (not x['atlas_implementation_verified'])
        assert all((k in C['sources'] for k in x['source_ids']))
    for x in C['test_specifications']:
        assert x['status'] == 'specified_not_executed'
        assert all((k in C['sources'] for k in x['source_ids']))
        assert x['expected_oracle'] and x['mathematical_or_source_basis']
    for x in C['sources'].values():
        repo = 'tensorflow' if x['repository'] == 'tensorflow/tensorflow' else 'keras'
        assert sha((ROOT / 'source' / repo / x['path']).read_bytes()) == x['sha256']
    return C['counts']
check('A011-specification-traceability', contracts)

def no_imports():
    for name in ['analyze_relations.py', 'analyze_inheritance.py', 'build_contracts.py', 'fetch_sources.py', 'fetch_extra.py', 'machine_assertions.py']:
        t = ast.parse((ROOT / name).read_bytes())
        for node in ast.walk(t):
            imports = [n.name for n in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) else []
            assert not any((n and n.split('.')[0] in ['tensorflow', 'keras', 'torch', 'jax', 'numpy'] for n in imports)), (name, imports)
    return 'Research scripts import only standard-library modules; source files are parsed as data.'
check('A012-no-framework-imports', no_imports)
report = {'schema_version': 1, 'assertions': RESULT, 'passed': sum((r['result'] == 'pass' for r in RESULT)), 'failed': sum((r['result'] == 'fail' for r in RESULT)), 'scope': 'Static source/integrity/analytical checks only. No reference-runtime, Atlas implementation, performance or hardware parity verification.'}
(ROOT / 'assertion-results.json').write_text(json.dumps(report, separators=(',', ':')) + '\n', encoding='utf-8')
print(json.dumps(report))
raise SystemExit(bool(report['failed']))
