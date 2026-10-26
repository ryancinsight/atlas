"""Lossless selected NumPy packet capture, separate from JAX policy history."""
import hashlib
import json

from atlas_parity_dtype_headers import exact_fields
from atlas_parity_schema import fields, local_path, need, read_json, source_selector
from atlas_parity_tables import unpack

PREFIX = 'dtype-policy/numpy-20261026/'
PACKET_SHA = '04e6d40cd363a27e7169916a1c68e6716c2ed658bd7746f1c9f93ec977265a97'
REVIEW_SHA = '710b8e1d629ceb370bf70ff8866f593688f591738c44613d6072252937ddf33b'
REVISION = 'a3d0ef1df045b858e68115001fdabc930bb3b68c'
SELECTED = {'README.md', 'native-contracts.json', 'policy-tables.json', 'source-receipts.json',
            'source-witnesses.json', 'source-branch-catalog.json', 'acceptance-cases.json',
            'ownership-plan.json', 'gap-disposition.json', 'remaining-gaps.json', 'benchmarks.json',
            'scope.json', 'source-acquisition.json', 'source-acquisition-extra.json',
            'source-acquisition-descriptor-support.json', 'inputs/frozen-tree.json'}


def original_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()


def policy_from_table(metadata, table):
    exact_fields(table, {'format': str, 'metadata': dict, 'columns': list, 'tables': dict, 'rows': list},
                 'NumPy symbolic relation table')
    need(table['metadata'] == {'role': 'symbolic_source_relation_not_descriptor_or_runtime_legality',
                              'source_cells': 576}, 'NumPy symbolic table role drift')
    need('cells' not in metadata['safe_policy'], 'NumPy symbolic cells duplicated')
    result = dict(metadata, safe_policy=dict(metadata['safe_policy'], cells=unpack(table)))
    return result


def preflight_selectors(joins, bindings, correction):
    """Reject malformed addresses before lossless source reconstruction; keep all later checks."""
    for document, groups in ((joins, ('endpoints', 'families', 'cases')), (bindings, ('functions',))):
        for group in groups:
            fields(document, {group: list}, 'NumPy source selector collection')
            for row in document[group]:
                fields(row, {'source_entry': list}, 'NumPy source selector row')
                source_selector(row['source_entry'], 'NumPy ' + group + ' source entry')
    fields(correction, {'correction_entry': list, 'raw_source_contract': dict}, 'NumPy correction source selectors')
    source_selector(correction['correction_entry'], 'NumPy correction source entry')
    exact_fields(correction['raw_source_contract'], {'entry': list, 'path': str, 'sha256': str},
                 'NumPy copied actual mapping source contract')
    source_selector(correction['raw_source_contract']['entry'], 'NumPy copied actual mapping source entry')


def validate_capture(root, index):
    paths, documents = [], {}
    for item in index['artifacts']:
        exact_fields(item, {'path': str, 'sha256': str}, 'NumPy native artifact')
        path = local_path(root, item['path'])
        need(item['path'].startswith(PREFIX) and path not in paths and
             hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'],
             'NumPy native artifact role/hash drift or repeated input')
        paths.append(path)
        if path.suffix == '.json':
            documents[item['path']] = read_json(path)
    def get(name):
        key = PREFIX + name
        need(key in documents, 'NumPy native artifact absent: ' + name)
        return documents[key]
    preflight_selectors(get('joins.json'), get('source-bindings.json'), get('correction-disposition.json'))
    capture, manifest, review = get('capture.json'), get('captured/manifest.json'), get('independent-review.json')
    exact_fields(capture, {'schema_version': int, 'source_manifest_sha256': str,
        'independent_review_sha256': str, 'captured': list, 'full_source_files_vendored': bool,
        'capture_complete_for_selected_artifacts': bool, 'original_json_serialization': str,
        'research_source_files': int, 'research_sealed_files': int, 'original_review_scope': str},
        'NumPy native lossless capture')
    need(hashlib.sha256(local_path(root, PREFIX + 'captured/manifest.json').read_bytes()).hexdigest() == PACKET_SHA and
         hashlib.sha256(local_path(root, PREFIX + 'independent-review.json').read_bytes()).hexdigest() == REVIEW_SHA,
         'NumPy accepted source manifest/review pin differs')
    need(capture == dict(capture, schema_version=1, source_manifest_sha256=PACKET_SHA,
         independent_review_sha256=REVIEW_SHA, full_source_files_vendored=False,
         capture_complete_for_selected_artifacts=True, research_source_files=78, research_sealed_files=211,
         original_json_serialization='json.dumps(sort_keys=True,separators=compact,ensure_ascii=False)+newline',
         original_review_scope='accepted_bounded_source_definition_only_not_canonical_candidate_review') and
         type(capture['full_source_files_vendored']) is bool and
         type(capture['capture_complete_for_selected_artifacts']) is bool,
         'NumPy capture provenance/count/scope drift')
    need(review['packet']['manifest_sha256'] == PACKET_SHA and
         review['packet']['revision'] == REVISION and review['packet']['version'] == '2.5.4' and
         review['outcome'] == 'accept_bounded_source_definition_only' and review['material_findings'] == [] and
         review['independent_controls']['offline_replay']['all_manifest_files_byte_identical'] == 211 and
         not any(review['qualification_limits'].values()), 'NumPy review scope/result drift')
    need(len(manifest['files']) == 211, 'NumPy original sealed file conservation drift')
    original = {}
    for row in capture['captured']:
        exact_fields(row, {'original_path': str, 'paths': list, 'sha256': str, 'storage': str},
                     'NumPy captured selected role')
        name = row['original_path']
        need(name in SELECTED and name not in original, 'NumPy captured selected role duplicated/unknown')
        if row['storage'] == 'policy-with-column-cells':
            need(name == 'policy-tables.json' and row['paths'] ==
                 [PREFIX + 'table-policy.json', PREFIX + 'safe-pairs.json'], 'NumPy table role substitution')
            value = policy_from_table(get('table-policy.json'), get('safe-pairs.json'))
            data = original_bytes(value)
        else:
            need(row['storage'] in {'original-bytes', 'compact-json'} and len(row['paths']) == 1,
                 'NumPy capture encoding invalid')
            path = local_path(root, row['paths'][0])
            need(path in paths, 'NumPy captured selected path not indexed')
            if row['storage'] == 'compact-json':
                value = read_json(path)
                data = original_bytes(value)
            else:
                data = path.read_bytes()
                value = read_json(path) if path.suffix == '.json' else data.decode()
        expected = manifest['files'][name]
        need(row['sha256'] == expected['sha256'] == hashlib.sha256(data).hexdigest() and
             len(data) == expected['bytes'], 'NumPy lossless accepted capture differs: ' + name)
        original[name] = value
    need(set(original) == SELECTED, 'NumPy selected capture role conservation drift')
    expected_paths = {PREFIX + name for name in ('capture.json', 'captured/manifest.json',
        'independent-review.json', 'joins.json', 'source-bindings.json', 'correction-disposition.json',
        'table-policy.json', 'safe-pairs.json')}
    expected_paths |= {p for row in capture['captured'] for p in row['paths']}
    need({p.relative_to(root).as_posix() for p in paths} == expected_paths,
         'NumPy indexed artifact role set differs')
    return original, documents, paths
