"""Generate a bounded ufunc identity/member/workflow inventory from source."""
from collections import Counter
import hashlib
import json
import re
from ufunc_sources import C, DOC, GEN, PAYLOAD, ROOT, REV, autosummary_selectors, cite, direct_bindings, find_line, generated_doc_payloads, generated_objects, load, member_inventory, native_aliases, table, text
from ufunc_workflows import expand, parser_schemas

def save(path, data):
    (ROOT / path).write_text(json.dumps(data, separators=(',', ':'), ensure_ascii=False) + '\n', encoding='utf-8')

def section(source, name):
    start = re.search('\\b' + name + '\\[\\]\\s*=\\s*\\{', source).start()
    return source[start:source.index('\n};', start) + 3]

def compare_identity_inputs():
    old = {entry['path']: entry for entry in load('inputs/source-tree-v2.5.0.json')['tree']}
    new = {entry['path']: entry for entry in load('inputs/source-tree.json')['tree']}
    files = []
    for row in load('source-manifest.json'):
        path = row['path']
        files.append({'path': path, 'old_git_blob_sha': old.get(path, {}).get('sha'), 'frozen_git_blob_sha': new[path]['sha'], 'identical': old.get(path, {}).get('sha') == new[path]['sha'], 'old_source': f'https://github.com/numpy/numpy/blob/6910b28fc12f4c3e821f315e24c51a6a2d89ba49/{path}', 'frozen_source': row['url']})
    old_source = (ROOT / 'comparison-source/ufunc_object-2.5.0.c').read_text(encoding='utf-8')
    table_rows = []
    for name in ['ufunc_methods', 'ufunc_getset', 'ufunc_members']:
        a, b = (section(old_source, name), section(text(C), name))
        table_rows.append({'table': name, 'old_section_sha256': hashlib.sha256(a.encode()).hexdigest(), 'frozen_section_sha256': hashlib.sha256(b.encode()).hexdigest(), 'identical': a == b})
    assert all((row['identical'] for row in table_rows))
    return {'old_documentation_version': '2.5.0', 'frozen_reference_version': '2.5.4', 'files': files, 'exact_native_member_table_comparisons': table_rows, 'bounded_conclusion': 'The three exact native member registration blocks are byte-identical. Existing official2.5.0 class member identities can be checked against frozen2.5.4 declarations; this does not promote2.5.0 numerical semantics or prove all rendered2.5.4 selection.', 'whole_runtime_or_semantic_equivalence_claim': False}

def documentation_reconciliation(objects, members, bindings, payloads):
    frozen = load('inputs/frozen-original-inventory.json')
    older = load('inputs/official-inventory-2.5.0.json')
    by_name = {row['symbol']: row for row in frozen['records']}
    observed = {row['symbol']: row for row in older['records'] if row['kind'].startswith('py:')}
    source_hashes = {row['path']: row['sha256'] for row in frozen['sources']}
    public, cls = ([], [])
    for row in bindings:
        if not row['public_namespace_export']:
            continue
        name = row['symbol']
        declared = by_name.get(name)
        old_entry = observed.get(name)
        target_name = next((obj['generated_name'] for obj in objects.values() if obj['object_id'] == row['object_id']))
        payload = payloads[target_name]
        alias_literal = None
        if declared is None:
            alias = name.rsplit('.', 1)[-1]
            match = re.search('\\b(?:np|numpy)\\.' + alias + '\\b', payload['raw_for_alias_checks'])
            if match:
                alias_literal = {'source': payload['source'], 'symbol': name, 'object_doc_alias_mention': True}
        public.append({'symbol': name, 'object_id': row['object_id'], 'source_binding_chain': row['chain'], 'frozen_documentation_occurrences': [{**occ, 'source': cite(occ['path'], occ['line']), 'file_sha256': source_hashes.get(occ['path'])} for occ in declared['occurrences']] if declared else [], 'original_frozen_extraction_present': declared is not None, 'exact_generated_object_doc_payload': {key: value for key, value in payload.items() if key != 'raw_for_alias_checks'}, 'named_alias_doc_mention': alias_literal, 'official_index_supplement': {'documentation_version': '2.5.0', 'mirror_revision': older['mirror_revision'], 'entry': old_entry} if old_entry else None, 'disposition': 'source-native-binding-with-documentation-trace' if declared else 'source-native-alias-with-explicit-generated-doc-mention' if alias_literal else 'source-native-export-retained;named-selector-reconciliation-open', 'semantic_equivalence_or_verification': False})
    expected_old_members = {row['symbol'] for row in older['records'] if row['symbol'].startswith('numpy.ufunc.') and row['kind'].startswith('py:')}
    for name, row in members.items():
        symbol = 'numpy.ufunc.' + name
        entry = observed.get(symbol)
        source_decl = by_name.get(symbol)
        cls.append({'symbol': symbol, 'member_id': row['member_id'], 'native_kind': row['native_kind'], 'frozen_source': row.get('source'), 'exact_doc_source': row.get('doc_source'), 'stub_source': row.get('stub_source'), 'frozen_original_occurrences': source_decl['occurrences'] if source_decl else [], 'official_index_supplement': {'documentation_version': '2.5.0', 'entry': entry} if entry else None, 'disposition': 'official-older-index-plus-exact-native-source' if entry else 'documented-public-unstable-underscored-native-member-retained' if name in {'_get_strided_loop', '_resolve_dtypes_and_context'} else 'native/prose/stub/conditional-member-retained-not-rendered-selection-proof', 'publicness_or_runtime_conflicts': row.get('runtime_status') or row.get('documentation_conflict'), 'not_dropped_for_underscore_or_unsupported_workflow': True})
    actual = {'numpy.ufunc.' + name for name in members}
    assert expected_old_members <= actual
    by_binding = {row['symbol']: row for row in bindings}
    selectors = []
    for selector in autosummary_selectors():
        symbol = selector['symbol']
        classification = 'class-selector' if symbol == 'numpy.ufunc' else 'member-selector' if symbol in actual else 'native-object-binding-selector' if symbol in by_binding else 'outside-generator-bound-retained'
        selectors.append({**selector, 'disposition': classification, 'object_id': by_binding.get(symbol, {}).get('object_id'), 'not_dropped': True})
    return {'frozen_reference': 'NumPy2.5.4@' + REV, 'public_bindings': public, 'class_members': cls, 'exact_reference_page_autosummary_dispositions': selectors, 'official_older_inventory_member_count': len(expected_old_members), 'official_older_member_rows_all_reconciled': expected_old_members <= actual, 'frozen_full_rendered_public_scope_complete': False, 'older_index_provenance': {key: older[key] for key in ['reference_documentation_version', 'mirror_revision', 'inventory_sha256']}}

def input_dispositions(objects, aliases, bindings):
    original = load('inputs/original-generated-ufunc-rows.json')
    alias_by_name = {row['alias']: row for row in aliases}
    binding_by_name = {row['symbol']: row for row in bindings}
    rows = []
    for item in original:
        name = item['symbol'].rsplit('.', 1)[-1]
        obj = objects[name] if name in objects else objects[alias_by_name[name]['target_name']]
        rows.append({'original_symbol': item['symbol'], 'original_record': item, 'original_record_sha256': hashlib.sha256(json.dumps(item, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), 'object_id': obj['object_id'], 'native_origin': obj['native_origin'], 'original_wrapper_label_proven_export': item['symbol'] in binding_by_name, 'disposition': 'native-alias-object-relation-preserved' if name in alias_by_name else 'native-generated-object-preserved', 'namespace_note': 'The generator creates native _multiarray_umath objects; a private helper is not assumed reexported by umath merely because its original candidate label used that namespace.', 'source': obj['source'], 'capabilities_verified': 0})
    assert len(rows) == 133 and len({r['original_symbol'] for r in rows}) == 133
    return {'original_rows_retained': rows, 'original_count': 133, 'all_retained': True, 'semantic_merges': 0}

def main():
    for entry in load('inputs/manifest.json'):
        assert hashlib.sha256((ROOT / 'inputs' / entry['path']).read_bytes()).hexdigest() == entry['sha256']
    for entry in load('source-manifest.json'):
        b = (ROOT / 'sources' / entry['path']).read_bytes()
        assert hashlib.sha256(b).hexdigest() == entry['sha256']
        assert hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\x00' + b).hexdigest() == entry['git_blob_sha']
    objects = generated_objects()
    payloads = generated_doc_payloads(objects)
    for name, obj in objects.items():
        obj['generated_documentation'] = {key: value for key, value in payloads[name].items() if key != 'raw_for_alias_checks'}
    aliases = native_aliases(objects)
    members = member_inventory()
    bindings, wrappers, _ = direct_bindings(objects, aliases)
    object_expansions, public_expansions, workflows = expand(objects, members, bindings)
    docs = documentation_reconciliation(objects, members, bindings, payloads)
    dispositions = input_dispositions(objects, aliases, bindings)
    prefix = {'schema_version': 1, 'framework': 'numpy', 'version': '2.5.4', 'revision': REV, 'full_numpy_surface_complete': False, 'implementation_or_runtime_evidence': False, 'capabilities_verified': 0}
    save('ufunc-objects.json', {**prefix, 'objects': list(objects.values()), 'original_input_dispositions': dispositions})
    save('ufunc-members.json', {**prefix, 'members': list(members.values()), 'manual_parser_schemas': parser_schemas()})
    save('ufunc-bindings.json', {**prefix, 'bindings': bindings, 'explicit_native_alias_relations': aliases, 'wrapper_dispositions': wrappers, 'public_namespace_bound': ['numpy', 'numpy.strings'], 'normal_installation_condition': 'Installed-native normal import branch, not NumPy setup/source-tree import mode.', 'remaining_char_boundary': 'numpy.char uses dynamic __getattr__ forwarding into defchararray; function wrappers are not silently converted to native object aliases. Broader dynamic alias coverage remains tracked.'})
    save('ufunc-expansions.json', {**prefix, 'object_member_expansions': object_expansions, 'public_spelling_member_expansions': public_expansions, 'workflow_templates': workflows})
    save('documentation-dispositions.json', {**prefix, **docs})
    identity = compare_identity_inputs()
    save('identity-input-comparison.json', identity)
    private_public = {'_get_strided_loop', '_resolve_dtypes_and_context'}
    assert private_public <= set(members)
    assert all((members[name]['stability'] == 'public-unstable-C-user-specific' for name in private_public))
    assert len(object_expansions) == len(objects) * len(members)
    public_count = sum((row['public_namespace_export'] for row in bindings))
    assert len(public_expansions) == public_count * len(members)
    assert len({row['expansion_id'] for row in object_expansions}) == len(object_expansions)
    assert len({row['binding_expansion_id'] for row in public_expansions}) == len(public_expansions)
    assert all((row['object_id'] in {obj['object_id'] for obj in objects.values()} for row in bindings))
    counts = {'original_input_rows': 133, 'generated_objects': len(objects), 'explicit_native_alias_rows': len(aliases), 'member_union': len(members), 'native_registered_methods': 8, 'native_getsets': 9, 'source_bindings': len(bindings), 'public_namespace_bindings': public_count, 'public_bindings_by_namespace': dict(Counter((row['symbol'].rsplit('.', 1)[0] for row in bindings if row['public_namespace_export']))), 'object_member_expansions': len(object_expansions), 'public_spelling_member_expansions': len(public_expansions), 'gufunc_objects': sum((obj['generalized'] for obj in objects.values())), 'workflow_templates': len(workflows), 'wrapper_shadow_dispositions': len(wrappers), 'exact_generated_object_doc_payloads': len(payloads), 'nonempty_generated_object_doc_payloads': sum((row['payload_status'] == 'nonempty-source-doc-payload' for row in payloads.values())), 'explicit_empty_generated_object_doc_payloads': sum((row['payload_status'] == 'explicit-empty-source-doc-payload-retained' for row in payloads.values())), 'exact_reference_page_autosummary_selectors': len(docs['exact_reference_page_autosummary_dispositions']), 'public_bindings_source_doc_or_named_alias_traced': sum((row['original_frozen_extraction_present'] or row['named_alias_doc_mention'] is not None for row in docs['public_bindings'])), 'public_binding_original_source_doc_matches': sum((row['original_frozen_extraction_present'] for row in docs['public_bindings'])), 'public_binding_older_official_index_matches': sum((row['official_index_supplement'] is not None for row in docs['public_bindings']))}
    completeness = {**prefix, 'bounded_extraction_complete': True, 'complete_for': 'Exact130 literal generator objects plus3 original aliases; literal native method/getset/member union, call slot, lazy signature descriptor, ufclass stub/source metadata candidates; root/strings native-binding graph and full cross-product declaration expansions.', 'not_a_claim': 'Not exhaustive runtime ufunc population, public rendered NumPy2.5.4 selection, instantiated type loops, semantic equivalence or dtype/device/AD qualification.', 'counts': counts, 'checks': {'all133_original_rows_disposed': True, 'all_private_and_unsupported_candidates_retained': True, 'member_union_cross_product_has_no_omissions': True, 'public_spelling_cross_product_has_no_omissions': True, 'all130_generated_objects_have_exact_doc_payload': len(payloads) == 130, 'all14_older_index_class_members_reconciled': docs['official_older_inventory_member_count'] == 14, 'exact_native_registration_blocks_match_older_index_source': all((row['identical'] for row in identity['exact_native_member_table_comparisons'])), 'semantic_merges': 0, 'framework_imports_or_builds': 0}}
    save('bounded-completeness.json', completeness)
    remaining = {**prefix, 'obligations': ['Native runtime instantiation, registered dtype loops/promoters, ntypes/types values, conditional/ABI/ISA registration and custom DType extensions remain unverified.', 'The official mirror is2.5.0. Exact native member registration blocks and selected doc/codegen input identities are proved, but whole rendered2.5.4 public selection and numerical semantics are not inferred.', '__qualname__ is a stub/conditional string-instance candidate, not a universally verified attribute. __module__ metadata is conditional; mutable __dict__/__doc__/lazy signature behavior conflicts with blanket readonly prose and needs semantic reconciliation.', 'Factories frompyfunc and external C APIs can create unbounded new ufuncs; private linalg/gufunc and other native modules outside defdict require separate inventory. This bound does not drop those obligations.', 'Dynamic legacy numpy.core/numpy.char forwarding, standard Python object inherited members/type slots and other namespaces are not exhausted by the declared root/strings graph.', 'Each concrete ufunc/member/spelling workflow requires exact dtype/promotion/casting/shape/layout/output/mask/alias/error/override/gradient/performance contracts; shared templates are not semantic merges or verification.', 'Binary multi-output outer and gufunc dtype-resolution reduction mode must be reviewed independently of reduce-like typing shortcuts; native descriptor eligibility is only an initial gate.', 'NumPy architecture is a reference. This extraction authorizes no third-party runtime adoption, provider repair, fallback, license/security change or 1.0 bump.']}
    save('remaining-scope.json', remaining)
    print(json.dumps(counts, sort_keys=True))
if __name__ == '__main__':
    main()
