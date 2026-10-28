"""Attach immutable source workflows/docs to the retained saving spellings."""
import os
import ast, hashlib, json
from pathlib import Path
from zipfile import ZipFile
ROOT = Path(__file__).resolve().parent
SRC = Path(os.environ['ATLAS_REFERENCE_BASE_CACHE']) / 'source' / 'keras'
TFROOT = Path(os.environ['ATLAS_REFERENCE_BASE_CACHE']) / 'source' / 'tensorflow'
REV = '250b42181ce9f37df68319d8f4753ec89a349a43'
TFREV = 'a481b10260dfdf833a1b16007eead49c1d7febf3'

def load(p):
    return json.loads((ROOT / p).read_bytes())

def sha(b):
    return hashlib.sha256(b).hexdigest()

def write(n, d):
    (ROOT / n).write_text(json.dumps(d, separators=(',', ':'), ensure_ascii=False) + '\n', encoding='utf-8')
r = load('saving-endpoint-resolution.json')
docs = load('official-doc-observations.json')
html = {x['url']: x for x in docs['pages']}
base = 'https://keras.io/api/models/model_saving_apis/'
workflow = {'KerasFileEditor': ('weights_file_editing', 'Edits serialized weight structures; inspect/compare/rename/add/delete and resave weights are separate operations. This is not whole-model save/load.', 'keras_file_editor/'), 'CustomObjectScope': ('scoped_deserialization_registry', 'Context manager copies a temporary custom-object dictionary into scoped global state and restores the prior scope on exit, including exception paths. Distinct from mutating the live global registry.', 'serialization_utils/'), 'custom_object_scope': ('scoped_deserialization_registry', 'Exact same generated import target as CustomObjectScope; retain both exported names. Identity evidence does not erase scoped state and nesting/exception behavior.', 'serialization_utils/'), 'get_custom_objects': ('global_registry_access', 'Returns the live GLOBAL_CUSTOM_OBJECTS dictionary. Scoped custom objects are held separately; returning a copy would change observable mutation semantics.', 'serialization_utils/'), 'get_registered_name': ('registered_identity_lookup', 'Looks up the object in GLOBAL_CUSTOM_NAMES; falls back to the Python object name. Registration state and collision behavior remain contract dimensions.', 'serialization_utils/'), 'get_registered_object': ('registered_object_lookup', 'Source lookup precedence distinguishes scoped objects, global registration, supplied custom_objects and module_objects; absence returns None. Preserve object identity and namespace/collision rules.', 'serialization_utils/'), 'register_keras_serializable': ('global_registry_registration', 'Decorator registers package>name and reverse object-name mapping; classes need get_config, functions do not. This mutates serialization registry state and returns the decorated object.', 'serialization_utils/'), 'save_model': ('whole_model_save', 'Persists architecture, weights and optimizer state through native .keras archive/unzipped or legacy HDF5 branches. Destination controls zipped default; overwrite=False can prompt. SavedModel inference export uses Model.export rather than this workflow.', 'model_saving_and_loading/'), 'load_model': ('whole_model_restore', 'Returns a reconstructed model, with compile and safe_mode defaults True. Native Keras, legacy HDF5 and optional Orbax/remote paths have distinct state/dependency/error contracts. It is not weights-only restore.', 'model_saving_and_loading/'), 'save_weights': ('weights_only_save', 'Writes weights with .weights.h5 or sharded .weights.json workflow; max_shard_size controls shards. This does not by itself establish architecture/optimizer restoration. Model.save_weights is a caller method, not a direct imported-function identity.', 'weights_saving_and_loading/'), 'load_weights': ('weights_only_restore', 'Mutates an existing model; skip_mismatch, legacy by_name and objects_to_skip validity depend on format. Native, sharded, legacy HDF5 and optional Orbax paths require separate round-trip/error evidence.', 'weights_saving_and_loading/'), 'serialize_keras_object': ('configuration_serialization', 'Produces a config object/dictionary for Keras objects; tensor/array and special-type cases have distinct contracts. This is not a whole-model file, weights archive or inference export.', 'serialization_utils/'), 'deserialize_keras_object': ('configuration_deserialization', 'Reconstructs from config with custom objects and safe_mode=True in the signature. Doc text on the live utilities page says defaults False, so preserve a documentation conflict; do not alter the source default.', 'serialization_utils/')}
for e in r['endpoints']:
    if e['kind'] == 'module':
        continue
    name = e['symbol'].split('.')[-1]
    kind, sem, page = workflow[name]
    doc = html[base + page]
    e['workflow'] = {'family': kind, 'source_derived_contract_note': sem, 'semantic_contract_status': 'partial-source-proposal; runtime behavior unverified'}
    e['official_documentation'] = {'url': doc['url'], 'snapshot_sha256': doc['sha256'], 'source_refs': doc['source_refs'], 'exact_selected_source_ref_present': doc['source_refs_include_selected_v3_15_1'], 'caveat': 'Major-version documentation page is mutable; source href pinsv3.15.1, verified against selected commit/wheel. Not every export has an individual rendered heading.'}
    e['identity_relation'] = 'same-generated-import-target-only'
    e['public_non_tf_aliases'] = [a['symbol'] for a in e['generated_aliases'] if '._tf_keras.' not in a['symbol']]
    e['selected_tf_root_accessible_alias_candidates'] = [a.replace('keras.', 'tf.keras.', 1) for a in e['public_non_tf_aliases'] if not a.startswith('keras.saving.')]
r['public_workflow_status'] = {'all14_retained': True, 'source_and_packaging_questions_resolved': True, 'actual_runtime_importability_qualified': False, 'patch_source_provenance': 'Four official saving pages linkv3.15.1, resolved to selected250b42181ce9f37df68319d8f4753ec89a349a43.', 'root_lookup_inference': 'The TensorFlow-facing root initializer has no saving binding or module __getattr__; fresh ordinary attribute lookup has no initializer-provided saving export. Explicit submodule import can bind the parent attribute under standard Python semantics. Dependencies/user imports may change process state; this inference is not a runtime result.'}
r['method_adapters'] = [{'method': 'tf.keras.Model.save', 'target': 'keras.src.saving.saving_api.save_model', 'relation': 'caller-method forwards self and arguments; not same Python function object', 'source': f'https://github.com/keras-team/keras/blob/{REV}/keras/src/models/model.py#L274'}, {'method': 'tf.keras.Model.save_weights', 'target': 'keras.src.saving.saving_api.save_weights', 'relation': 'caller-method workflow; not direct-import identity', 'source': f'https://github.com/keras-team/keras/blob/{REV}/keras/src/models/model.py#L320'}, {'method': 'tf.keras.Model.load_weights', 'target': 'keras.src.saving.saving_api.load_weights', 'relation': 'caller-method workflow; not direct-import identity', 'source': f'https://github.com/keras-team/keras/blob/{REV}/keras/src/models/model.py#L378'}]
r['remaining_scope'] = ['No TensorFlow/Keras runtime imports were authorized/executed; fresh-process root lookup and explicit import routes remain acceptance tests, not passing results.', 'Exact TensorFlow generated wheel namespace aliases, TensorFlow dependency resolution and environment variable TF_USE_LEGACY_KERAS variants remain separate; optional legacy tf_keras is not silently dropped.', 'Serialization/weights/model/editor semantics remain partial source contracts requiring real artifact round trips, registry/state/error/format/mode/dtype/device coverage and independent review.', 'Public saving APIs are retained even when one tf.keras root spelling lacks an initializer reexport. No API namespace absence is counted as missing mathematical capability or accepted scope exclusion.', 'Keras3 documentation/source conflicts and optional remote/Orbax/HDF5 dependencies require exact-version tests. No environment/security/access changes or safe-mode weakening occurs.']
write('saving-endpoint-resolution.json', r)
witnesses = []
for repo, rev, root, paths in [('keras-team/keras', REV, SRC, ['api_gen.py', 'keras/api/__init__.py', 'keras/api/_tf_keras/keras/__init__.py', 'keras/api/saving/__init__.py', 'keras/api/_tf_keras/keras/saving/__init__.py']), ('tensorflow/tensorflow', TFREV, TFROOT, ['tensorflow/api_template.__init__.py', 'tensorflow/python/util/lazy_loader.py'])]:
    for p in paths:
        dest = ROOT / 'source-witnesses' / repo / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        b = dest.read_bytes() if dest.exists() else (root / p).read_bytes()
        dest.write_bytes(b)
        witnesses.append({'repository': repo, 'revision': rev, 'source_path': p, 'snapshot_file': str(dest.relative_to(ROOT)), 'sha256': sha(b), 'source_url': f'https://github.com/{repo}/blob/{rev}/{p}'})
write('source-witnesses.json', {'schema_version': 1, 'sources': witnesses})
tests = []

def test(i, workflow, expected):
    tests.append({'id': i, 'workflow': workflow, 'expected_source_oracle': expected, 'status': 'specified_not_executed', 'requires': 'fresh isolated consumer with exact TensorFlow2.21.0/Keras3.15.1 dependency graph; no user state reused'})
test('KS001', 'Fresh import tensorflow as tf; inspect tf.keras.saving before any explicit saving-submodule import.', 'Source predicts no root-initializer saving binding. Record actual AttributeError/availability and imported-module set; do not turn static inference into runtime pass.')
test('KS002', 'Explicitly import keras._tf_keras.keras.saving and access every thirteen exported names.', 'Packaged path resolves conditional on dependencies; parent saving attribute becomes bound under import semantics. Verify all direct targets by identity.')
test('KS003', 'from tensorflow.keras import saving; import tensorflow.keras.saving; from tensorflow.keras.saving import save_model in separate fresh processes.', 'Determine generated TensorFlow package-path/lazy-loader behavior separately from attribute lookup; no assumptions from same spelling.')
test('KS004', 'import keras; inspect keras.saving and all thirteen exports.', 'Ordinary root explicitly reexports saving; verify namespace and source objects at exact wheel version.')
test('KS005', 'Compare generated alias objects against keras.saving targets, including CustomObjectScope/custom_object_scope; inspect Model methods separately.', 'Direct imports share target identity; bound Model methods are caller adapters and need behavior tests rather than is-identity equality.')
test('KS006', 'Save/restore a trained real model with nontrivial architecture, weights, optimizer slots and resumed steps through .keras and unzipped workflows.', 'Values, config and optimizer state/resume outcomes match independently derived/reference results; archive path is not inference export.')
test('KS007', 'Save/load weights through .weights.h5, sharded .weights.json and legacy HDF5 with shape mismatches and format-invalid keyword combinations.', 'Existing-model mutation, sharding, skip_mismatch/by_name/objects_to_skip errors are format-specific; do not equate with whole-model restore.')
test('KS008', 'Nest custom_object_scope with exception exit and compare against get_custom_objects live registry behavior in an isolated process.', 'Scope copied/restored independently of global dictionary; registry alias and object precedence preserved without mutating user state.')
test('KS009', 'Serialize/deserialize custom classes/functions with registered names, duplicate names, get_config validation, shared references and unsupported objects.', 'Config/schema/identity/error contracts hold; retain source safe_mode=True default, including doc conflict disposition.')
test('KS010', 'Use KerasFileEditor to inspect/compare/change selected real weight entries, resave and load via independent consumer.', 'Only requested payloads change; output is valid weights artifact. This is distinct from whole-model reconstruction and inference export.')
write('saving-acceptance-specifications.json', {'schema_version': 1, 'tests': tests, 'counts': {'specified': len(tests), 'executed': 0}, 'no_runtime_tests_executed': True})
print(json.dumps({'retained_endpoints': len(r['endpoints']), 'source_witnesses': len(witnesses), 'runtime_specs': len(tests), 'actual_runtime_importability_qualified': False}))
