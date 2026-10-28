import os
'Review exact public-binding candidates without claiming semantic equivalence.'
import ast, collections, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from audit import Sources, BASE, REV
ROOT = Path(os.environ['ATLAS_REFERENCE_REPOSITORY'])
s = Sources(Path(os.environ.get('ATLAS_REFERENCE_SOURCE_CACHE', '/tmp/atlas-numpy-jax-parity/jax')))
d = json.loads((ROOT / 'docs/parity/reference/jax.json').read_text(encoding='utf-8'))
existing = {r['symbol'] for r in d['records']}
modules = sorted({g['argument'] for g in d['extraction_gaps'] if g['directive'] == 'automodule'})
rows = []
new = []
for module in modules:
    path, t, bindings, stars = s.module(module)
    exports = []
    issues = []
    for name, node in sorted(bindings.items()):
        if name.startswith('_'):
            continue
        kind = None
        target = None
        if isinstance(node, tuple):
            if node[0] == 'import':
                _, m, n, a = node
                aliases = [a0 for a0 in a.names if (a0.asname or a0.name) == name]
                if not any((a0.asname == a0.name for a0 in aliases)):
                    continue
                kind = 'explicit-self-alias-reexport'
                target = m + '.' + n
                line = a.lineno
            else:
                _, m, a = node
                if not any((a0.asname is not None and a0.asname == a0.name.rsplit('.', 1)[-1] for a0 in a.names)):
                    continue
                kind = 'explicit-module-reexport'
                target = m
                line = a.lineno
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = type(node).__name__
            line = node.lineno
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            kind = 'assignment-candidate'
            line = node.lineno
            target = ast.unparse(node.value) if node.value else None
        if kind:
            symbol = module + '.' + name
            record = {'symbol': symbol, 'kind': kind, 'target': target, 'source': BASE + path + '#L' + str(line), 'documented_identity_present': symbol in existing, 'semantic_equivalence': 'unreviewed; alias target alone cannot merge reference variants'}
            exports.append(record)
            if symbol not in existing:
                new.append(record)
    if stars:
        issues.append('wildcard-imports:' + ','.join(stars))
    if '__getattr__' in bindings:
        issues.append('dynamic/deprecated module __getattr__ requires explicit compatibility export reconciliation')
    if '__all__' in bindings:
        n = bindings['__all__']
        try:
            allnames = ast.literal_eval(n.value)
            issues.append('__all__ literal recorded; compare membership before public classification')
        except (ValueError, TypeError):
            allnames = None
            issues.append('dynamic __all__ requires additional extraction')
    else:
        allnames = None
    for n in ast.walk(t):
        if isinstance(n, ast.Call):
            target = ast.unparse(n.func)
            if target in ('setattr', 'globals().update') or 'globals()[' in target:
                issues.append('potential namespace mutation:' + target + ':' + str(n.lineno))
    for statement in t.body:
        if isinstance(statement, (ast.If, ast.Try, ast.For, ast.While, ast.With, ast.Match)):
            public = []
            for node in ast.walk(statement):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and (not node.name.startswith('_')):
                    public.append(node.name)
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and (not node.id.startswith('_')):
                    public.append(node.id)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    public.extend((a.asname or a.name for a in node.names if not (a.asname or a.name).startswith('_')))
            if public:
                issues.append('compound-statement export alternatives require runtime-condition reconciliation at line ' + str(statement.lineno) + ':' + ','.join(sorted(set(public))))
    rows.append({'module': module, 'source_path': path, 'exports': exports, 'issues': sorted(set(issues)), 'explicit_all': allnames, 'complete_for_static_binding_model': not issues, 'full_public_namespace_complete': False})
result = {'framework': 'jax', 'version': '0.12.0.1', 'source_revision': REV, 'module_count': len(rows), 'static_binding_candidates': sum((len(r['exports']) for r in rows)), 'candidates_absent_from_documented_identity_set': len(new), 'warning': 'These are public-shaped source binding candidates, not automatically documented capabilities. Preserve/reconcile each, do not silently add, exclude, or semantically merge by target/name.', 'namespaces': rows, 'additional_candidates': new, 'sources': sorted(s.used.values(), key=lambda r: r['path'])}
Path(__file__).with_name('namespace-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print({k: v for k, v in result.items() if k not in ['namespaces', 'additional_candidates', 'sources']})
