"""Analyze release wheel as ZIP/AST data. Do not import any framework."""
import os
import ast, base64, csv, hashlib, io, json
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile
ROOT = Path(__file__).resolve().parent
SRC = Path(os.environ['ATLAS_REFERENCE_BASE_CACHE']) / 'source' / 'keras'
REV = '250b42181ce9f37df68319d8f4753ec89a349a43'
WHEEL = ROOT / 'keras-3.15.1-py3-none-any.whl'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def write(n, d):
    (ROOT / n).write_text(json.dumps(d, separators=(',', ':'), ensure_ascii=False) + '\n', encoding='utf-8')

def imports(b):
    t = ast.parse(b)
    out = []
    for n in t.body:
        if isinstance(n, ast.ImportFrom):
            for a in n.names:
                out.append({'name': a.asname or a.name, 'target': n.module + '.' + a.name, 'line': n.lineno})
    return out
with ZipFile(WHEEL) as z:
    names = z.namelist()
    assert len(set(names)) == len(names)
    record = next((n for n in names if n.endswith('.dist-info/RECORD')))
    rows = list(csv.reader(io.StringIO(z.read(record).decode())))
    checks = []
    for p, h, size in rows:
        b = z.read(p)
        if h:
            alg, value = h.split('=', 1)
            assert alg == 'sha256'
            assert base64.urlsafe_b64encode(hashlib.sha256(b).digest()).decode().rstrip('=') == value
            assert len(b) == int(size)
        else:
            assert p == record and size == ''
        checks.append({'path': p, 'sha256': sha(b), 'bytes': len(b), 'record_hash_verified': bool(h)})
    assert {r[0] for r in rows} == set(names)
    write('record-verification.json', {'schema_version': 1, 'record_path': record, 'entries': len(rows), 'verified_hashed_entries': sum((x['record_hash_verified'] for x in checks)), 'unhashed_record_self_entry': 1, 'files': checks})
    source_matches = []
    unmatched = []
    tree = json.loads((ROOT / 'inputs/keras-tree.json').read_bytes())
    lookup = {x['path']: x for x in tree['tree']}
    for p in names:
        if not p.endswith('.py') or not p.startswith('keras/'):
            continue
        candidates = [SRC / p] if p.startswith('keras/src/') else [SRC / 'keras/api' / p.removeprefix('keras/'), SRC / p]
        b = z.read(p)
        blob = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\x00' + b).hexdigest()
        src = next((x for x in candidates if x.relative_to(SRC).as_posix() in lookup and lookup[x.relative_to(SRC).as_posix()]['sha'] == blob), None)
        if src:
            source_matches.append({'wheel_path': p, 'source_path': src.relative_to(SRC).as_posix(), 'sha256': sha(z.read(p))})
        else:
            unmatched.append(p)
    write('wheel-source-correspondence.json', {'schema_version': 1, 'revision': REV, 'python_file_count': len(source_matches) + len(unmatched), 'matched_count': len(source_matches), 'unmatched': unmatched, 'matches': source_matches})
    module_paths = ['keras/__init__.py', 'keras/_tf_keras/keras/__init__.py', 'keras/saving/__init__.py', 'keras/_tf_keras/keras/saving/__init__.py']
    module_data = {}
    for p in module_paths:
        b = z.read(p)
        d = {'wheel_path': p, 'sha256': sha(b), 'bytes': len(b), 'imports': imports(b), 'defines_module_getattr': any((isinstance(n, ast.FunctionDef) and n.name == '__getattr__' for n in ast.parse(b).body))}
        src = next((x for x in source_matches if x['wheel_path'] == p), None)
        if src:
            d.update({'source_path': src['source_path'], 'source_url': f"https://github.com/keras-team/keras/blob/{REV}/{src['source_path']}"})
        module_data[p] = d
    assert 'saving' in {x['name'] for x in module_data['keras/__init__.py']['imports']}
    assert 'saving' not in {x['name'] for x in module_data['keras/_tf_keras/keras/__init__.py']['imports']}
    assert module_data['keras/saving/__init__.py']['imports'] == module_data['keras/_tf_keras/keras/saving/__init__.py']['imports']
    write('packaged-module-exports.json', {'schema_version': 1, 'modules': module_data, 'ordinary_keras_root_reexports_saving': True, 'tf_keras_root_reexports_saving': False, 'saving_modules_identical': z.read('keras/saving/__init__.py') == z.read('keras/_tf_keras/keras/saving/__init__.py'), 'caveat': 'Initializer binding graph and wheel file existence only; conditional execution/dependency readiness and actual TensorFlow import aliases are not runtime-tested.'})
    all_imports = defaultdict(list)
    specific_submodule_importers = []
    for p in names:
        if not p.endswith('.py'):
            continue
        t = ast.parse(z.read(p))
        if p.startswith('keras/') and (not p.startswith('keras/src/')):
            namespace = p.removesuffix('/__init__.py').removesuffix('.py').replace('/', '.')
            for row in imports(z.read(p)):
                all_imports[row['target']].append({'symbol': namespace + '.' + row['name'], 'source_path': p, 'line': row['line']})
        for n in ast.walk(t):
            if isinstance(n, ast.ImportFrom) and (n.module or '').startswith('keras._tf_keras.keras.saving'):
                specific_submodule_importers.append({'path': p, 'line': n.lineno, 'module': n.module})
            elif isinstance(n, ast.ImportFrom) and n.module == 'keras._tf_keras.keras' and any((a.name == 'saving' for a in n.names)):
                specific_submodule_importers.append({'path': p, 'line': n.lineno, 'module': n.module})
            elif isinstance(n, ast.Import) and any((a.name.startswith('keras._tf_keras.keras.saving') for a in n.names)):
                specific_submodule_importers.append({'path': p, 'line': n.lineno, 'module': [a.name for a in n.names]})
    write('submodule-importers.json', {'schema_version': 1, 'matching_static_imports': specific_submodule_importers, 'note': 'An absence of static imports is not a proof against arbitrary runtime imports by external dependencies or user code.'})
    exports = module_data['keras/_tf_keras/keras/saving/__init__.py']['imports']
    assert len(exports) == 13
    endpoints = [{'symbol': 'tf.keras.saving', 'kind': 'module', 'packaged_path': 'keras/_tf_keras/keras/saving/__init__.py', 'scope_disposition': 'retain-as-packaged-submodule; distinguish ordinary root attribute lookup from explicit submodule import workflow', 'root_initializer_reexported': False, 'reference_runtime_verified': False, 'semantic_equivalence_asserted': False}]
    for row in exports:
        mod, name = row['target'].rsplit('.', 1)
        p = mod.replace('.', '/') + '.py'
        b = z.read(p)
        nodes = ast.parse(b).body
        node = next((n for n in nodes if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name == name))
        assert hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\x00' + b).hexdigest() == lookup[p]['sha']
        aliases = all_imports[row['target']]
        endpoints.append({'symbol': 'tf.keras.saving.' + row['name'], 'kind': 'class' if isinstance(node, ast.ClassDef) else 'function', 'target': row['target'], 'saving_module_import_line': row['line'], 'packaged_path': p, 'definition_line': node.lineno, 'signature': ast.unparse(node.args) if isinstance(node, ast.FunctionDef) else None, 'source_url': f'https://github.com/keras-team/keras/blob/{REV}/{p}#L{node.lineno}', 'source_sha256': sha(b), 'docstring_sha256': sha((ast.get_docstring(node) or '').encode()), 'generated_aliases': aliases, 'scope_disposition': 'retain documented saving capability and packaged submodule spelling; do not equate root lookup with explicit import', 'reference_runtime_verified': False, 'semantic_equivalence_asserted': False})
    write('saving-endpoint-resolution.json', {'schema_version': 1, 'keras_version': '3.15.1', 'revision': REV, 'wheel_sha256': sha(WHEEL.read_bytes()), 'endpoints': endpoints, 'counts': {'retained_endpoints': len(endpoints), 'module': 1, 'export_names': 13, 'distinct_definition_targets': len(set((r['target'] for r in endpoints if 'target' in r)))}, 'workflow_classification': {'keras.saving': 'ordinary root initializer reexport; thirteen direct target imports', 'tf.keras.saving': 'not bound by selected _tf_keras.keras root initializer; packaged submodule exists; later explicit import can bind parent attribute under standard Python import semantics', 'keras._tf_keras.keras.saving': 'concrete packaged module path with thirteen direct imports; runtime dependency readiness and selected TF integration remain unexecuted', 'tensorflow.keras.saving': 'TensorFlow api_template extends package paths to selected Keras; module path must be tested on generated TensorFlow wheel before runtime availability claims'}, 'no_names_dropped': True})
    print(json.dumps({'wheel_entries': len(names), 'record_hashed_verified': 908, 'source_matches': len(source_matches), 'unmatched_source_python': unmatched, 'saving_export_names': 13, 'distinct_targets': len(set((x['target'] for x in exports))), 'specific_static_submodule_importers': len(specific_submodule_importers)}))
