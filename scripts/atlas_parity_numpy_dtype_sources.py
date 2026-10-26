"""Portable exact-span/function proofs and named registered-cast phases."""
import ast
import hashlib
import re

from atlas_parity_dtype_headers import exact_fields
from atlas_parity_numpy_dtype_capture import REVISION
from atlas_parity_schema import digest, need, unique

PHASES = [
    ('registered-lookup', 'PyArray_GetCastingImpl', ['if (from == to)', 'if (res != NULL)', 'ensure_castingimpl_exists(from, to)']),
    ('advertised-before-resolver', 'PyArray_CheckCastSafety', ['PyArray_GetCastingImpl', 'PyArray_MinCastSafety(castingimpl->casting, casting)', '_get_cast_safety_from_castingimpl']),
    ('resolver-source-target-cleanup', '_get_cast_safety_from_castingimpl', ['castingimpl->resolve_descriptors', 'out_descrs[0] != descrs[0]', 'out_descrs[1] != descrs[1]', 'Py_DECREF(out_descrs[0])']),
    ('query-error-projection', 'PyArray_CanCastTypeTo', ['PyDataType_ISUNSIZED(to)', 'PyArray_CheckCastSafety', 'PyErr_Clear()', 'return 0;']),
    ('registered-temporal-slot', 'PyArray_InitializeDatetimeCasts', ['.casting = NPY_UNSAFE_CASTING', 'slots[0].slot = NPY_METH_resolve_descriptors', 'slots[0].pfunc = &time_to_time_resolve_descriptors', 'PyArray_AddCastingImplementation_FromSpec']),
    ('registered-temporal-quotient', 'time_to_time_resolve_descriptors', ['given_descrs[0] == given_descrs[1]', '(meta1->num / meta2->num) == 1000', 'meta1->base == NPY_FR_GENERIC', 'meta2->base == NPY_FR_GENERIC', 'is_timedelta &&', 'datetime_metadata_divides'])]


def expected_bindings(witnesses):
    functions = witnesses['functions']
    phases = []
    for identity, name, markers in PHASES:
        matches = [f for f in functions.values() if f['name'] == name]
        need(len(matches) == 1, 'NumPy registered phase function is not unique')
        function = matches[0]
        phases.append({'id': identity, 'function_id': function['id'], 'source_citation': function['source'],
                       'ordered_source_markers': markers, 'runtime_executed': False,
                       'scope': 'named_local_source_sequence_not_transitive_CFG_or_runtime_proof'})
    return {'schema_version': 1, 'whole_API_or_runtime_credit': False,
        'functions': [{'id': key, 'source_entry': ['functions', key], 'source_citation': f['source'],
            'path': f['path'], 'signature_source': f['signature_source'], 'body_sha256': f['body_sha256'],
            'body_kind': f['body_kind'], 'source_mapping_complete': False} for key, f in functions.items()],
        'registered_resolver_phases': phases,
        'temporal_quotient_disposition': {'case_id': 'numpy-dtype:temporal-metric-quotient-source-question',
            'example': 'same-byteorder 2001ms -> 2s', 'source_integer_quotient': 1000,
            'mathematically_equal_durations': False, 'exact_binary_comparison': 'unrun',
            'reference_bug_waiver_or_exclusion': False}}


def validate_sources(receipts, witnesses, catalog, tree, bindings):
    exact_fields(receipts, {'schema_version': int, 'revision': str, 'version': str, 'source_files': dict,
        'receipt_complete_for_selected_bytes': bool, 'whole_source_or_semantics_complete': bool}, 'NumPy source receipts')
    need(receipts['schema_version'] == 1 and receipts['revision'] == REVISION and receipts['version'] == '2.5.4' and
         receipts['receipt_complete_for_selected_bytes'] is True and receipts['whole_source_or_semantics_complete'] is False,
         'NumPy source receipt qualification drift')
    sources = receipts['source_files']
    need(tree['sha'] == '838cf31b8096f12d7ca41ededf3ed60d94d37e3d' and tree['truncated'] is False,
         'NumPy exact frozen source tree drift')
    entries = {r['path']: r for r in tree['tree'] if r['type'] == 'blob'}
    need(len(sources) == 78, 'NumPy source file conservation drift')
    for path, source in sources.items():
        exact_fields(source, {'bytes': int, 'frozen2_5_0_blob': str, 'git_blob': str, 'line_count': int,
            'path': str, 'revision': str, 'same_frozen2_5_0_blob': bool, 'sha256': str, 'url': str, 'version': str},
            'NumPy frozen source file')
        need(source['path'] == path and source['revision'] == REVISION and source['version'] == '2.5.4' and
             source['git_blob'] == entries[path]['sha'] and source['bytes'] == entries[path]['size'] and
             source['line_count'] > 0 and source['url'] == f'https://github.com/numpy/numpy/blob/{REVISION}/{path}',
             'NumPy exact source tree/receipt/path join drift')
        digest(source['sha256'], 'NumPy full source SHA256')
    exact_fields(witnesses, {'schema_version': int, 'citations': dict, 'functions': dict,
        'lexical_not_CFG_or_semantic_coverage': bool, 'runtime_credit': bool}, 'NumPy source witness header')
    need(witnesses['schema_version'] == 1 and witnesses['lexical_not_CFG_or_semantic_coverage'] is True and
         witnesses['runtime_credit'] is False and len(witnesses['citations']) == 131 and
         len(witnesses['functions']) == 129, 'NumPy source witness count/credit drift')
    for identity, citation in witnesses['citations'].items():
        exact_fields(citation, {'end': int, 'path': str, 'sha256': str, 'start': int, 'text': str, 'url': str},
                     'NumPy source citation')
        need(citation['path'] in sources and 1 <= citation['start'] <= citation['end'] <= sources[citation['path']]['line_count'] and
             identity == f"{citation['path']}:L{citation['start']}-L{citation['end']}" and
             len(citation['text'].splitlines()) == citation['end'] - citation['start'] + 1 and
             hashlib.sha256(citation['text'].encode()).hexdigest() == citation['sha256'] and
             citation['url'] == sources[citation['path']]['url'] + f"#L{citation['start']}-L{citation['end']}",
             'NumPy source citation bounds/quote/hash drift')
    funcs = witnesses['functions']
    for identity, function in funcs.items():
        required = {'body_kind': str, 'body_sha256': str, 'id': str, 'lexical_extraction': str, 'name': str,
                    'path': str, 'signature_source': str, 'source': str, 'whole_semantics_or_runtime_credit': bool}
        if function['body_kind'] == 'C_lexical_offsets':
            required.update(body_offsets=list, control_sites=list, call_or_macro_occurrences=list)
        exact_fields(function, required, 'NumPy selected source function')
        need(identity == function['id'] == function['path'] + '::' + function['name'] and
             function['source'] in witnesses['citations'] and function['whole_semantics_or_runtime_credit'] is False,
             'NumPy function source identity/credit drift')
        text = witnesses['citations'][function['source']]['text']
        if function['body_kind'] == 'C_lexical_offsets':
            body = text[:text.rfind('}') + 1]
            offsets = function['body_offsets']
            need(len(offsets) == 2 and all(type(x) is int for x in offsets) and 0 <= offsets[0] < offsets[1] and
                 offsets[1] - offsets[0] == len(body) and text[:text.find('{')].strip() == function['signature_source'] and
                 function['name'] in body.split('{', 1)[0], 'NumPy lexical signature/body extent drift')
        else:
            need(function['body_kind'] == 'Python_AST', 'NumPy function extraction kind drift')
            nodes = [n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.FunctionDef) and n.name == function['name']]
            need(len(nodes) == 1, 'NumPy Python source function absent')
            body = ast.get_source_segment(text, nodes[0])
            need(function['signature_source'] == f"{function['name']}({ast.unparse(nodes[0].args)})",
                 'NumPy Python function signature drift')
        need(hashlib.sha256(body.encode()).hexdigest() == function['body_sha256'], 'NumPy exact function body hash drift')
    need(catalog['semantic_branch_completeness'] is False and catalog['declaration_to_api_credit'] is False and
         catalog['function_count'] == 129 and catalog['control_site_count'] == 855,
         'NumPy lexical catalog count/semantic credit drift')
    entries = unique(catalog['functions'], 'id', 'NumPy lexical catalog function')
    need(entries.keys() == funcs.keys() and all(entries[key] == funcs[key] for key in entries) and
         sum(len(f.get('control_sites', [])) for f in funcs.values()) == 855,
         'NumPy catalog/function witness join drift')
    exact_fields(bindings, {'schema_version': int, 'whole_API_or_runtime_credit': bool, 'functions': list,
        'registered_resolver_phases': list, 'temporal_quotient_disposition': dict}, 'NumPy source binding schema')
    for row in bindings['functions']:
        exact_fields(row, {'id': str, 'source_entry': list, 'source_citation': str, 'path': str, 'signature_source': str,
            'body_sha256': str, 'body_kind': str, 'source_mapping_complete': bool}, 'NumPy typed function binding')
    for row in bindings['registered_resolver_phases']:
        exact_fields(row, {'id': str, 'function_id': str, 'source_citation': str, 'ordered_source_markers': list,
            'runtime_executed': bool, 'scope': str}, 'NumPy typed registered phase')
    exact_fields(bindings['temporal_quotient_disposition'], {'case_id': str, 'example': str, 'source_integer_quotient': int,
        'mathematically_equal_durations': bool, 'exact_binary_comparison': str, 'reference_bug_waiver_or_exclusion': bool},
        'NumPy temporal unresolved source question')
    need(bindings == expected_bindings(witnesses), 'NumPy function binding/registered phase/temporal role drift')
    for phase in bindings['registered_resolver_phases']:
        text = witnesses['citations'][phase['source_citation']]['text']
        positions = [text.find(marker) for marker in phase['ordered_source_markers']]
        need(all(i >= 0 for i in positions) and positions == sorted(positions),
             'NumPy registered resolver phase source sequence differs')
    return set(witnesses['citations'])
