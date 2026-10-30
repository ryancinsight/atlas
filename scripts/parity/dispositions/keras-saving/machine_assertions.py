"""Static package/source/doc checks only; never import Keras/TensorFlow."""
import os
import ast, base64, csv, hashlib, io, json
from email import message_from_bytes
from pathlib import Path
from zipfile import ZipFile
ROOT = Path(__file__).resolve().parent
OLD = Path(os.environ['ATLAS_REFERENCE_BASE_CACHE'])
RESULT = []

def sha(b):
    return hashlib.sha256(b).hexdigest()

def load(p):
    return json.loads((ROOT / p).read_bytes())

def check(i, fn):
    try:
        d = fn()
        RESULT.append({'id': i, 'result': 'pass', 'detail': d})
    except Exception as e:
        RESULT.append({'id': i, 'result': 'fail', 'detail': repr(e)})
artifact = load('artifact-provenance.json')
wheel = ROOT / artifact['wheel']['filename']
z = ZipFile(wheel)

def artifact_check():
    assert sha(wheel.read_bytes()) == artifact['wheel']['sha256'] == artifact['wheel']['expected_sha256'] == '836460e480930acbd19bb7a17e62f9ecad40e8a9af9a651fc8d0586a96d27e20'
    assert wheel.stat().st_size == 2398595
    meta = message_from_bytes(z.read('keras-3.15.1.dist-info/METADATA'))
    assert meta['Name'] == 'keras' and meta['Version'] == '3.15.1'
    return artifact['wheel']
check('KS-A001-official-wheel-identity', artifact_check)

def record():
    names = z.namelist()
    assert len(names) == len(set(names)) == 909
    rows = list(csv.reader(io.StringIO(z.read('keras-3.15.1.dist-info/RECORD').decode())))
    assert len(rows) == 909
    assert {r[0] for r in rows} == set(names)
    verified = 0
    for p, h, size in rows:
        assert '..' not in Path(p).parts and (not Path(p).is_absolute())
        if not h:
            assert p.endswith('.dist-info/RECORD')
            continue
        alg, v = h.split('=', 1)
        b = z.read(p)
        assert alg == 'sha256' and int(size) == len(b)
        assert base64.urlsafe_b64encode(hashlib.sha256(b).digest()).decode().rstrip('=') == v
        verified += 1
    assert verified == 908
    return {'entries': 909, 'hashed_entries_verified': 908}
check('KS-A002-wheel-RECORD', record)

def source_correspondence():
    d = load('wheel-source-correspondence.json')
    assert d['python_file_count'] == d['matched_count'] == 904 and (not d['unmatched'])
    tree = json.loads((ROOT / 'inputs/keras-tree.json').read_bytes())
    assert not tree['truncated']
    lookup = {x['path']: x for x in tree['tree']}
    checks = []
    for r in d['matches']:
        b = z.read(r['wheel_path'])
        assert sha(b) == r['sha256']
        blob = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\x00' + b).hexdigest()
        assert blob == lookup[r['source_path']]['sha']
        checks.append({**r, 'git_blob_sha': blob})
    result = {'schema_version': 1, 'source_revision': '250b42181ce9f37df68319d8f4753ec89a349a43', 'source_tree_url': 'https://api.github.com/repos/keras-team/keras/git/trees/250b42181ce9f37df68319d8f4753ec89a349a43?recursive=1', 'tree_snapshot_sha256': sha((ROOT / 'inputs/keras-tree.json').read_bytes()), 'python_blobs_verified': len(checks), 'files': checks}
    (ROOT / 'git-source-verification.json').write_text(json.dumps(result, separators=(',', ':')) + '\n', encoding='utf-8')
    return {'wheel_python_files_matching_exact_release_blobs': len(checks)}
check('KS-A003-wheel-to-release-Git-source', source_correspondence)

def exports():
    m = load('packaged-module-exports.json')
    assert m['ordinary_keras_root_reexports_saving']
    assert not m['tf_keras_root_reexports_saving']
    assert m['saving_modules_identical']
    assert all((not x['defines_module_getattr'] for x in m['modules'].values()))
    return {'ordinary_root_reexport': True, 'selected_TF_root_reexport': False, 'identical_submodule_text': True}
check('KS-A004-root-versus-submodule-exports', exports)

def endpoints():
    r = load('saving-endpoint-resolution.json')
    assert len(r['endpoints']) == 14
    assert r['counts']['distinct_definition_targets'] == 12
    assert r['no_names_dropped']
    assert r['public_workflow_status']['all14_retained']
    assert not r['public_workflow_status']['actual_runtime_importability_qualified']
    names = {x['symbol'] for x in r['endpoints']}
    previous = load('inputs/retained-endpoint-names.json')['retained_endpoint_names']
    assert names == set(previous)
    for e in r['endpoints']:
        assert not e['reference_runtime_verified'] and (not e['semantic_equivalence_asserted'])
        if 'target' in e:
            b = z.read(e['packaged_path'])
            assert sha(b) == e['source_sha256']
            assert e['workflow']['semantic_contract_status'].startswith('partial-source-proposal')
    return r['counts']
check('KS-A005-all14-retained-with-dispositions', endpoints)

def alias_identity():
    e = load('saving-endpoint-resolution.json')['endpoints']
    x = {r['symbol'].split('.')[-1]: r for r in e if 'target' in r}
    assert x['CustomObjectScope']['target'] == x['custom_object_scope']['target']
    assert 'keras.models.save_model' in x['save_model']['public_non_tf_aliases']
    assert 'keras.models.load_model' in x['load_model']['public_non_tf_aliases']
    assert 'keras.utils.serialize_keras_object' in x['serialize_keras_object']['public_non_tf_aliases']
    return 'Direct-import target aliases identified; no semantic equivalence inferred.'
check('KS-A006-generated-alias-targets', alias_identity)

def docs():
    d = load('official-doc-observations.json')
    assert len(d['pages']) == 5
    assert d['counts']['pages_with_selected_release_source_links'] == 4
    for p in d['pages']:
        assert sha((ROOT / p['snapshot_file']).read_bytes()) == p['sha256']
        assert set(p['source_refs']) <= {'v3.15.1'}
    return {'snapshotted_official_pages': 5, 'source_linked_selected_release_pages': 4, 'immutable_page_url_claimed': False}
check('KS-A007-official-doc-release-provenance', docs)

def loader():
    witness = load('source-witnesses.json')
    by_path = {x['source_path']: x for x in witness['sources']}
    for x in witness['sources']:
        assert sha((ROOT / x['snapshot_file']).read_bytes()) == x['sha256']
    src = (ROOT / by_path['tensorflow/python/util/lazy_loader.py']['snapshot_file']).read_text(encoding='utf-8')
    assert 'package_name = "keras._tf_keras.keras"' in src
    assert 'TF_USE_LEGACY_KERAS' in src
    api = (ROOT / by_path['tensorflow/api_template.__init__.py']['snapshot_file']).read_text(encoding='utf-8')
    assert 'get_parent_dir_for_name("keras._tf_keras.keras")' in api
    assert not load('submodule-importers.json')['matching_static_imports']
    return 'Loader/package-path routing retained as source evidence; runtime import-state behavior remains unexecuted.'
check('KS-A008-TF-loader-source-routing', loader)

def safe_mode():
    p = 'keras/src/saving/serialization_lib.py'
    t = ast.parse(z.read(p))
    f = next((n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == 'deserialize_keras_object'))
    args = [a.arg for a in f.args.args]
    defaults = {k: v for k, v in zip(args[-len(f.args.defaults):], f.args.defaults)}
    assert ast.literal_eval(defaults['safe_mode']) is True
    p = 'keras/src/saving/saving_api.py'
    t = ast.parse(z.read(p))
    f = next((n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == 'load_model'))
    args = [a.arg for a in f.args.args]
    defaults = {k: v for k, v in zip(args[-len(f.args.defaults):], f.args.defaults)}
    assert ast.literal_eval(defaults['safe_mode']) is True
    return 'Both selected-release source signatures keep safe_mode=True; no setting changed.'
check('KS-A009-exact-signature-defaults', safe_mode)

def specs():
    d = load('saving-acceptance-specifications.json')
    assert d['counts'] == {'specified': 10, 'executed': 0}
    assert len(d['tests']) == 10 and all((x['status'] == 'specified_not_executed' for x in d['tests']))
    return d['counts']
check('KS-A010-runtime-probes-not-passing-evidence', specs)

def no_imports():
    for p in ROOT.glob('*.py'):
        for n in ast.walk(ast.parse(p.read_bytes())):
            names = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module] if isinstance(n, ast.ImportFrom) else []
            assert not any((x and x.split('.')[0] in ['keras', 'tensorflow', 'numpy', 'torch', 'jax'] for x in names)), p
    return 'Research scripts use standard library only; wheel/source Python text parsed as data.'
check('KS-A011-no-framework-imports', no_imports)
report = {'schema_version': 1, 'assertions': RESULT, 'passed': sum((r['result'] == 'pass' for r in RESULT)), 'failed': sum((r['result'] == 'fail' for r in RESULT)), 'scope': 'Static artifact/RECORD/Git-source/namespace/documentation checks only; no runtime importability, parity, performance, hardware or release-readiness qualification.'}
(ROOT / 'assertion-results.json').write_text(json.dumps(report, separators=(',', ':')) + '\n', encoding='utf-8')
print(json.dumps(report))
raise SystemExit(bool(report['failed']))
