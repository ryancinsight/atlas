import os
'Static reference relation proposal. Never imports TensorFlow or Keras.'
import ast, hashlib, json
from collections import defaultdict, Counter, deque
from pathlib import Path
ROOT = Path(__file__).resolve().parent
TFREV = 'a481b10260dfdf833a1b16007eead49c1d7febf3'
KREV = '250b42181ce9f37df68319d8f4753ec89a349a43'
CANON = Path(os.environ['ATLAS_REFERENCE_INVENTORY'])
TFROOT = ROOT / 'source/tensorflow'
KROOT = ROOT / 'source/keras'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def save(name, obj):
    p = ROOT / name
    p.write_text(json.dumps(obj, separators=(',', ':'), ensure_ascii=False) + '\n', encoding='utf-8')
    return {'path': str(p), 'sha256': sha(p.read_bytes())}

def qname(n):
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        p = qname(n.value)
        return p + '.' + n.attr if p else None
    if isinstance(n, ast.Subscript):
        return qname(n.value)
    return None

def module_of(p):
    s = str(p).removesuffix('.py').replace('/', '.')
    return s.removesuffix('.__init__')

def link(repo, rev, p, line=None):
    return f'https://github.com/{repo}/blob/{rev}/{p}' + (f'#L{line}' if line else '')

def rid(r):
    return sha('\x00'.join((r['symbol'], r['kind'], r['source'])).encode())[:24]

def source(module, root):
    p = Path(module.replace('.', '/'))
    for f in [root / p.with_suffix('.py'), root / p / '__init__.py']:
        if f.exists():
            return f
    if module.startswith('keras.') and (not module.startswith(('keras.api.', 'keras.src.'))):
        return source('keras.api.' + module.removeprefix('keras.'), root)
    return None
inv = json.loads(CANON.read_bytes())
records = inv['records']
by_symbol = defaultdict(list)
for r in records:
    by_symbol[r['symbol']].append(r)
views = [{'symbol': name, 'declaration_ids': [rid(r) for r in rows], 'kinds': [r['kind'] for r in rows], 'relation': 'declaration_views_of_same_public_endpoint', 'semantic_equivalence_asserted': False} for name, rows in sorted(by_symbol.items()) if len(rows) > 1]
spelling = []
for name, rows in sorted(by_symbol.items()):
    if not name.startswith('tf.compat.v1.'):
        continue
    other = 'tf.' + name.removeprefix('tf.compat.v1.')
    if other not in by_symbol:
        continue
    a = {r['signature'] for r in rows if 'signature' in r}
    b = {r['signature'] for r in by_symbol[other] if 'signature' in r}
    spelling.append({'v1': name, 'v2': other, 'relation': 'same_relative_spelling_only', 'signatures': 'equal_declared_signatures' if a and a == b else 'different_declared_signatures' if a and b else 'signature_absent', 'semantic_equivalence_asserted': False})
export_groups = []
unresolved = []
parse_errors = []
call_count = 0
production_count = 0
parsed_count = 0
for p in sorted(TFROOT.rglob('*.py')):
    rel = p.relative_to(TFROOT).as_posix()
    try:
        t = ast.parse(p.read_bytes(), filename=rel)
    except Exception as e:
        parse_errors.append({'path': rel, 'error': str(e)})
        continue
    parsed_count += 1
    parents = {child: parent for parent in ast.walk(t) for child in ast.iter_child_nodes(parent)}
    imports = {}
    for n in ast.walk(t):
        if isinstance(n, ast.ImportFrom) and n.module:
            for a in n.names:
                imports[a.asname or a.name] = n.module + '.' + a.name
        elif isinstance(n, ast.Import):
            for a in n.names:
                imports[a.asname or a.name] = a.name
    module = module_of(rel)

    def resolve(expr):
        n = qname(expr)
        if not n:
            return None
        first, *tail = n.split('.')
        base = imports.get(first, module + '.' + first)
        return '.'.join([base] + tail)
    for n in ast.walk(t):
        if not isinstance(n, ast.Call):
            continue
        f = resolve(n.func)
        if f != 'tensorflow.python.util.tf_export.tf_export':
            continue
        call_count += 1
        test = '/tests/' in rel or rel.endswith('_test.py') or '/testdata/' in rel
        if test:
            continue
        production_count += 1
        try:
            v2 = [ast.literal_eval(a) for a in n.args]
            assert all((isinstance(x, str) for x in v2))
            kw = {k.arg: ast.literal_eval(k.value) for k in n.keywords}
            v1 = kw.get('v1', v2)
            assert isinstance(v1, (list, tuple)) and all((isinstance(x, str) for x in v1))
        except Exception as e:
            unresolved.append({'source': link('tensorflow/tensorflow', TFREV, rel, n.lineno), 'reason': 'nonliteral export names', 'expression': ast.unparse(n)})
            continue
        parent = parents.get(n)
        target = None
        mode = None
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n in parent.decorator_list:
            target = module + '.' + parent.name
            mode = 'decorated_definition'
        elif isinstance(parent, ast.Call) and parent.func is n and (len(parent.args) == 1):
            target_expr = parent.args[0]
            while isinstance(target_expr, ast.Call) and len(target_expr.args) == 1 and (not target_expr.keywords):
                target_expr = target_expr.args[0]
            target = resolve(target_expr)
            mode = 'decorator_application'
            gp = parents.get(parent)
            if isinstance(gp, ast.Assign) and len(gp.targets) == 1:
                target = module + '.' + (qname(gp.targets[0]) or ast.unparse(gp.targets[0]))
                mode = 'assigned_export_application'
        elif isinstance(parent, ast.Attribute) and parent.attr == 'export_constant':
            call = parents.get(parent)
            if isinstance(call, ast.Call) and len(call.args) == 2:
                try:
                    target = module + '.' + ast.literal_eval(call.args[1])
                    mode = 'export_constant'
                except Exception:
                    pass
        names = ['tf.' + s for s in v2] + ['tf.compat.v1.' + s for s in v1]
        if target is None:
            unresolved.append({'source': link('tensorflow/tensorflow', TFREV, rel, n.lineno), 'reason': 'unresolved export target expression', 'expression': ast.unparse(n), 'endpoints': names})
        export_groups.append({'target': target, 'mode': mode, 'endpoints': names, 'present_in_frozen_inventory': [s for s in names if s in by_symbol], 'missing_from_frozen_inventory': [s for s in names if s not in by_symbol], 'source': link('tensorflow/tensorflow', TFREV, rel, n.lineno), 'source_path': rel, 'line': n.lineno, 'relation': 'same_tf_export_invocation', 'semantic_equivalence_asserted': False, 'caveat': 'Same exported target evidence only; wrappers, dispatcher extensions, context, build selection and version policy still require semantic review.'})
queue = deque([('keras._tf_keras.keras', 'tf.keras')])
seen = set()
krows = []
module_forms = []
unhandled = []
while queue:
    mod, prefix = queue.popleft()
    if (mod, prefix) in seen:
        continue
    seen.add((mod, prefix))
    p = source(mod, KROOT)
    if p is None:
        unhandled.append({'module': mod, 'prefix': prefix, 'reason': 'module source absent'})
        continue
    rel = p.relative_to(KROOT).as_posix()
    if not rel.startswith('keras/api/'):
        unhandled.append({'module': mod, 'prefix': prefix, 'reason': 'reachable module is not generated API', 'source_path': rel})
        continue
    t = ast.parse(p.read_bytes())
    krows.append({'symbol': prefix, 'kind': 'module', 'target': mod, 'source_path': rel, 'line': 1, 'source': link('keras-team/keras', KREV, rel, 1)})
    for n in t.body:
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
            continue
        if not isinstance(n, ast.ImportFrom) or n.module is None:
            unhandled.append({'module': mod, 'source_path': rel, 'line': n.lineno, 'reason': 'unhandled generated top-level form', 'form': ast.dump(n)})
            continue
        for a in n.names:
            target = n.module + '.' + a.name
            name = prefix + '.' + (a.asname or a.name)
            if a.name == '*':
                unhandled.append({'source_path': rel, 'line': n.lineno, 'reason': 'wildcard export'})
                continue
            dest = source(target, KROOT)
            is_api_module = bool(dest and dest.relative_to(KROOT).as_posix().startswith('keras/api/'))
            krows.append({'symbol': name, 'kind': 'module_export' if is_api_module else 'symbol_export', 'target': target, 'source_path': rel, 'line': n.lineno, 'source': link('keras-team/keras', KREV, rel, n.lineno), 'semantic_equivalence_asserted': False})
            if is_api_module:
                queue.append((target, name))
old_keras = {r['symbol'] for r in records if r['symbol'].startswith('tf.keras')}
new_keras = {r['symbol'] for r in krows}
alias_targets = defaultdict(list)
for r in krows:
    if r['kind'] == 'symbol_export':
        alias_targets[r['target']].append(r['symbol'])
k_alias = [{'target': t, 'endpoints': sorted(set(names)), 'relation': 'same_generated_import_target', 'semantic_equivalence_asserted': False} for t, names in sorted(alias_targets.items()) if len(set(names)) > 1]
outputs = []
outputs.append(save('declaration-relations.json', {'schema_version': 1, 'inventory_input': {'path': str(CANON), 'sha256': sha(CANON.read_bytes()), 'declarations': len(records), 'distinct_symbols': len(by_symbol)}, 'same_endpoint_declaration_views': views, 'v1_v2_spelling_candidates': spelling, 'tf_export_groups': export_groups, 'keras_generated_import_aliases': k_alias, 'unresolved_tf_exports': unresolved, 'parse_errors': parse_errors, 'counts': {'view_groups': len(views), 'v1_v2_spelling_candidates': len(spelling), 'spelling_signature_classes': dict(Counter((s['signatures'] for s in spelling))), 'tf_export_calls_seen_all_sources': call_count, 'non_test_path_tf_export_calls': production_count, 'resolved_non_test_export_name_groups': len(export_groups), 'unresolved_tf_exports': len(unresolved), 'parsed_tensorflow_python_sources': parsed_count, 'keras_generated_import_alias_groups': len(k_alias)}}))
outputs.append(save('keras-reachable-exports.json', {'schema_version': 1, 'revision': KREV, 'entrypoint': 'keras._tf_keras.keras', 'public_prefix': 'tf.keras', 'selected_backend': 'tensorflow', 'records': krows, 'new_symbols_absent_from_initial_inventory': sorted(new_keras - old_keras), 'initial_symbols_not_reached': sorted(old_keras - new_keras), 'unhandled': unhandled, 'counts': {'reachable_module_paths': len(seen), 'distinct_generated_source_files': len(set((r['source_path'] for r in krows))), 'declarations': len(krows), 'distinct_symbols': len(new_keras), 'previous_unique_symbols': len(old_keras), 'new_unique_symbols': len(new_keras - old_keras)}}))
print(json.dumps({'outputs': outputs, 'tensorflow_export_counts': json.loads((ROOT / 'declaration-relations.json').read_text(encoding='utf-8'))['counts'], 'keras_counts': json.loads((ROOT / 'keras-reachable-exports.json').read_text(encoding='utf-8'))['counts'], 'unhandled_generated_forms': len(unhandled)}))
