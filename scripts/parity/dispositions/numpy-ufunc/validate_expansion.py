"""Validate the declared source bound, identity trace and non-verification flags.

This checker reads text/AST only. It neither imports NumPy nor executes source
generators; references to NumPy are immutable input data.
"""
import ast
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parent
REV = 'a3d0ef1df045b858e68115001fdabc930bb3b68c'
ARTIFACTS = ('ufunc-objects.json', 'ufunc-members.json', 'ufunc-bindings.json', 'ufunc-expansions.json', 'documentation-dispositions.json', 'identity-input-comparison.json', 'bounded-completeness.json', 'remaining-scope.json')

class ValidationError(ValueError):
    pass

def need(condition, message):
    if not condition:
        raise ValidationError(message)

def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))

def bundle():
    return {name: read(name) for name in ARTIFACTS}

def native_table_names(source, name):
    body = source.split(name + '[] = {', 1)[1].split('\n};', 1)[0]
    return set(re.findall('\\{\\s*"([^"]+)"\\s*,', body))

def verify_sources():
    source_tree = {r['path']: r for r in read('inputs/source-tree.json')['tree']}
    for row in read('inputs/manifest.json'):
        need(hashlib.sha256((ROOT / 'inputs' / row['path']).read_bytes()).hexdigest() == row['sha256'], 'immutable input changed: ' + row['path'])
    sources = read('source-manifest.json')
    need(len({row['path'] for row in sources}) == len(sources), 'duplicate source path')
    for row in sources:
        body = (ROOT / 'sources' / row['path']).read_bytes()
        need(hashlib.sha256(body).hexdigest() == row['sha256'], 'source SHA256: ' + row['path'])
        blob = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\x00' + body).hexdigest()
        need(blob == row['git_blob_sha'] == source_tree[row['path']]['sha'], 'source Git blob: ' + row['path'])
    old = read('comparison-source/manifest.json')
    body = (ROOT / 'comparison-source/ufunc_object-2.5.0.c').read_bytes()
    need(hashlib.sha256(body).hexdigest() == old['sha256'], 'older native comparison SHA256')
    need(hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\x00' + body).hexdigest() == old['git_blob_sha'], 'older native comparison Git blob')
    return len(sources)

def source_citations(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from source_citations(child)
    elif isinstance(value, list):
        for child in value:
            yield from source_citations(child)
    elif isinstance(value, str):
        match = re.fullmatch('https://github.com/numpy/numpy/blob/' + REV + '/(.+)#L(\\d+)', value)
        if match:
            yield (match[1], int(match[2]))

def validate(data, source_hashes=True):
    if source_hashes:
        verify_sources()
    for name in ARTIFACTS:
        if name == 'identity-input-comparison.json':
            continue
        item = data[name]
        need(item['version'] == '2.5.4' and item['revision'] == REV, 'wrong frozen version')
        need(item['full_numpy_surface_complete'] is False, 'full NumPy completion overclaim')
        need(item['implementation_or_runtime_evidence'] is False and item['capabilities_verified'] == 0, 'declaration promoted to verification')
    objects = data['ufunc-objects.json']['objects']
    members = data['ufunc-members.json']['members']
    bindings = data['ufunc-bindings.json']['bindings']
    exp = data['ufunc-expansions.json']
    docs = data['documentation-dispositions.json']
    source = (ROOT / 'sources/numpy/_core/code_generators/generate_umath.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    literal = next((node.value for node in tree.body if isinstance(node, ast.Assign) and any((isinstance(t, ast.Name) and t.id == 'defdict' for t in node.targets))))
    expected_names = [ast.literal_eval(node) for node in literal.keys]
    obj = {row['generated_name']: row for row in objects}
    ids = {row['object_id'] for row in objects}
    need(len(objects) == len(obj) == len(ids) == 130, 'object identities missing or merged')
    need(set(obj) == set(expected_names), 'literal generator coverage; private candidates retained')
    for key, value in zip(literal.keys, literal.values):
        row = obj[ast.literal_eval(key)]
        need((row['nin'], row['nout']) == tuple((ast.literal_eval(node) for node in value.args[:2])), 'nin/nout mismatch')
        need(row['runtime_instantiation_verified'] is False and row['semantic_completeness'] is False, 'runtime/semantic object overclaim')
        need(row['object_id'] == 'numpy@2.5.4:generated:' + row['generated_name'], 'unstable object identity')
    need({name for name, row in obj.items() if row['generalized']} == {'matmul', 'vecdot', 'matvec', 'vecmat'}, 'gufunc scope mismatch')
    need(obj['degrees']['object_id'] != obj['rad2deg']['object_id'], 'mathematical resemblance merged object declarations')
    original = read('inputs/original-generated-ufunc-rows.json')
    dispositions = data['ufunc-objects.json']['original_input_dispositions']
    need(Counter((json.dumps(row, sort_keys=True) for row in original)) == Counter((json.dumps(row['original_record'], sort_keys=True) for row in dispositions['original_rows_retained'])), 'original133 rows lost or altered')
    need(dispositions['all_retained'] and dispositions['semantic_merges'] == 0, 'original disposition overclaim')
    for row in dispositions['original_rows_retained']:
        digest = hashlib.sha256(json.dumps(row['original_record'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        need(digest == row['original_record_sha256'] and row['object_id'] in ids, 'original row provenance')
    c = (ROOT / 'sources/numpy/_core/src/umath/ufunc_object.c').read_text(encoding='utf-8')
    by_member = {r['member']: r for r in members}
    need(len(members) == len(by_member) == 22, 'member identities missing or merged')
    for table, kind in [('ufunc_methods', 'native-method'), ('ufunc_getset', 'native-getset'), ('ufunc_members', 'native-member')]:
        need(native_table_names(c, table) == {r['member'] for r in members if r['native_kind'] == kind}, 'native table coverage: ' + table)
    for name in ['_resolve_dtypes_and_context', '_get_strided_loop']:
        need(by_member[name]['stability'] == 'public-unstable-C-user-specific', 'public underscored C-user API dropped/reclassified')
    need(by_member['__doc__']['native_setter_present'] is True and 'conflict' in by_member['__doc__']['documentation_conflict'].lower(), 'mutable doc/readonly conflict hidden')
    need('not a universally verified' in by_member['__qualname__']['runtime_status'] or 'not proven' in by_member['__qualname__']['runtime_status'], 'conditional qualname overclaim')
    binding_ids = {r['binding_id'] for r in bindings}
    by_symbol = {r['symbol']: r for r in bindings}
    public = [r for r in bindings if r['public_namespace_export']]
    need(len(bindings) == len(binding_ids) == len(by_symbol) == 642, 'binding identity count')
    need(all((r['object_id'] in ids and r['chain'] and (r['runtime_verified'] is False) for r in bindings)), 'untraced/verified source binding')
    need(Counter((r['symbol'].rsplit('.', 1)[0] for r in public)) == {'numpy': 106, 'numpy.strings': 17}, 'public namespace bound changed')
    for name, target in {'abs': 'absolute', 'bitwise_not': 'invert', 'mod': 'remainder', 'conj': 'conjugate', 'true_divide': 'divide'}.items():
        need(by_symbol['numpy.' + name]['object_id'] == obj[target]['object_id'], 'alias relation: ' + name)
    need('numpy._core.umath._arg' not in by_symbol and 'numpy._core._multiarray_umath._arg' in by_symbol, 'private wrapper label correction lost')
    wrappers = data['ufunc-bindings.json']['wrapper_dispositions']
    need(len(wrappers) == 6 and all((row['symbol'] not in by_symbol for row in wrappers)), 'Python wrapper mistaken for native alias')
    alias_rows = data['ufunc-bindings.json']['explicit_native_alias_relations']
    need({(r['alias'], r['target_name']) for r in alias_rows} == {('true_divide', 'divide'), ('conj', 'conjugate'), ('mod', 'remainder')}, 'native alias omission/merge')
    rows = exp['object_member_expansions']
    pairs = {(r['object_id'], r['member']) for r in rows}
    need(len(rows) == len(pairs) == 2860 and pairs == set(itertools.product(ids, by_member)), 'object/member cross-product omission')
    need(len({r['expansion_id'] for r in rows}) == len(rows), 'duplicate expansion identity')
    need(all((r['semantic_merge'] is False for r in rows)), 'semantic row merge')
    public_rows = exp['public_spelling_member_expansions']
    need(len(public_rows) == len({r['binding_expansion_id'] for r in public_rows}) == 2706, 'public spelling expansion omission')
    need({(r['binding_id'], r['symbol'].rsplit('.', 1)[-1]) for r in public_rows} == set(itertools.product({r['binding_id'] for r in public}, by_member)), 'alias workflow spelling omission')
    need(all((r['object_expansion_id'] in {x['expansion_id'] for x in rows} for r in public_rows)), 'dangling alias workflow')
    workflows = exp['workflow_templates']
    need(len(workflows) == 9, 'workflow templates missing')
    need(all((v is False for w in workflows.values() for v in w['verification'].values())), 'workflow qualification overclaim')
    indexed = {(r['generated_name'], r['member']): r for r in rows}
    need(indexed['divmod', 'outer']['descriptor_gate']['status'] == 'descriptor-conditionally-eligible', 'multi-output outer incorrectly rejected')
    need(indexed['divmod', 'reduce']['descriptor_gate']['first_error'] == 'ValueError', 'multi-output reduce guard')
    need(indexed['matmul', 'reduce']['descriptor_gate']['first_error'] == 'RuntimeError', 'gufunc reduction first error')
    need(indexed['matmul', 'outer']['descriptor_gate']['first_error'] == 'TypeError', 'gufunc outer first error')
    need(indexed['matmul', 'resolve_dtypes']['descriptor_gate']['reduction_true'] == 'descriptor-eligible', 'dtype-resolution mode conflated with actual reduce')
    need(indexed['frexp', 'at']['descriptor_gate']['first_error'] == 'ValueError', 'multi-output at guard')
    need({r['symbol'] for r in docs['public_bindings']} == {r['symbol'] for r in public}, 'public docs reconciliation omission')
    need(all((r['original_frozen_extraction_present'] or r['named_alias_doc_mention'] is not None for r in docs['public_bindings'])), 'named alias/source docs disposition lost')
    payloads = [r['generated_documentation'] for r in objects]
    need(Counter((r['payload_status'] for r in payloads)) == {'nonempty-source-doc-payload': 122, 'explicit-empty-source-doc-payload-retained': 8}, 'empty source docs hidden')
    need(len(docs['exact_reference_page_autosummary_dispositions']) == 104 and all((r['not_dropped'] for r in docs['exact_reference_page_autosummary_dispositions'])), 'autosummary selector omission')
    need(docs['frozen_full_rendered_public_scope_complete'] is False, 'rendered full scope overclaim')
    for row in [*docs['public_bindings'], *docs['class_members']]:
        if row['official_index_supplement']:
            need(row['official_index_supplement']['documentation_version'] == '2.5.0', 'older docs relabeled frozen version')
    comparison = data['identity-input-comparison.json']
    need(comparison['whole_runtime_or_semantic_equivalence_claim'] is False, 'input identity promoted to semantics')
    need(len(comparison['exact_native_member_table_comparisons']) == 3 and all((r['identical'] and r['old_section_sha256'] == r['frozen_section_sha256'] for r in comparison['exact_native_member_table_comparisons'])), 'native member-table bridge')
    need(len(data['remaining-scope.json']['obligations']) >= 8, 'remaining scope erased')
    citation_pairs = set(source_citations(data))
    for path, line in citation_pairs:
        cached = ROOT / 'sources' / path
        need(cached.is_file(), 'uncached frozen source citation: ' + path)
        need(0 < line <= len(cached.read_text(encoding='utf-8').splitlines()), 'out-of-bounds frozen source citation')
    counts = data['bounded-completeness.json']['counts']
    need(counts['generated_objects'] == len(objects) and counts['member_union'] == len(members) and (counts['public_namespace_bindings'] == len(public)), 'declared counts mismatch')
    return {'status': 'passed', 'source_files': len(read('source-manifest.json')), 'unique_frozen_source_line_citations': len(citation_pairs), 'original_rows_retained': 133, 'bounded_object_member_expansions': len(rows), 'public_spelling_member_expansions': len(public_rows), 'framework_imports_or_builds': 0, 'semantic_verification_credited': 0}
if __name__ == '__main__':
    print(json.dumps(validate(bundle()), sort_keys=True))
