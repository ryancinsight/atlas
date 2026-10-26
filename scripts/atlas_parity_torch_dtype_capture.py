"""Lossless selected repaired Torch source packet, without full source/history vendor."""
import hashlib
import json

from atlas_parity_dtype_headers import exact_fields
from atlas_parity_schema import local_path, need, read_json
from atlas_parity_tables import unpack

PREFIX = 'dtype-policy/pytorch-20261026/'
PACKET_SHA = 'a34fc711c04e087985c8835b933bcfae275493fdeb0b72455523ee7e1618fcb0'
REVIEW_SHA = '013862e7a4bff259a08aaa1cf31531f0c5e67f0069e91d764f482124dd6b94c6'
PREDECESSOR_SHA = '697b0c7463ba3bff6935c48bbc73d24728e05843123d0587bf6e6b077314bd21'
INITIAL_REVIEW_SHA = '3ac30501eabe1b0cca49f5edb2b60f4ea9cf8a05430da288191e90100d658de1'
REVISION = '5c4886908584029761b579af026dcfb627c84070'
SELECTED = {'README.md', 'contracts.json', 'acceptance-cases.json', 'dtype-model.json',
    'admitted-bindings.json', 'computation-policies.json', 'source-registry.json', 'source-witnesses.json',
    'counts.json', 'remaining-gaps.json', 'workspace-policy-proposal.json', 'relations.json',
    'source-checks.json', 'input-manifest.json', 'git-blob-read-receipts.json', 'acquisition-summary.json',
    'dependency-register.json', 'correction-history.json', 'predecessor-preservation.json',
    'prior-packet-preservation.json', 'history/initial-independent-review/initial-review.json'}
ROW_FIELDS = {'core_lookup_cells': ['left', 'right', 'result', 'source_ref'],
    'native_promotion_pairs': ['left', 'right', 'native_outcome', 'public_wrapper_outcome', 'dtype', 'branch'],
    'native_cast_permission_pairs': ['from', 'to', 'permitted', 'branch']}


def original_bytes(value):
    return (json.dumps(value, separators=(',', ':'), ensure_ascii=False) + '\n').encode()


def reconstruct_model(metadata, tables):
    result = dict(metadata)
    need(set(tables) == set(ROW_FIELDS), 'Torch finite table role set differs')
    for key, fields in ROW_FIELDS.items():
        need(metadata[key] == [], 'Torch finite table metadata duplicates cells')
        table = tables[key]
        exact_fields(table, {'format': str, 'metadata': dict, 'columns': list, 'tables': dict, 'rows': list}, 'Torch source table')
        need(table['metadata'] == {'role': key, 'qualification': 'source_only_not_public_kernel_registry'},
             'Torch finite table role/qualification differs')
        need(set(table['columns']) <= set(fields), 'Torch finite source table contains unknown fields')
        records = unpack(table)
        need(all(set(row) <= set(fields) for row in records), 'Torch finite source row contains unknown fields')
        result[key] = [{name: row[name] for name in fields if name in row} for row in records]
    return result


def validate_capture(root, index):
    paths, docs = [], {}
    for item in index['artifacts']:
        exact_fields(item, {'path': str, 'sha256': str}, 'Torch source artifact')
        path = local_path(root, item['path'])
        need(item['path'].startswith(PREFIX) and path not in paths and
             hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], 'Torch artifact role/hash differs')
        paths.append(path)
        if path.suffix == '.json': docs[item['path']] = read_json(path)
    def get(name):
        need(PREFIX + name in docs, 'Torch indexed artifact absent: ' + name)
        return docs[PREFIX + name]
    capture, manifest, review = get('capture.json'), get('captured/manifest.json'), get('independent-review.json')
    exact_fields(capture, {'schema_version': int, 'source_manifest_sha256': str, 'independent_review_sha256': str,
        'captured': list, 'full_source_files_vendored': bool, 'full_history_vendored': bool,
        'capture_complete_for_selected_artifacts': bool, 'research_source_files': int, 'research_sealed_files': int,
        'original_json_serialization': str}, 'Torch capture schema')
    need(capture['schema_version'] == 1 and capture['source_manifest_sha256'] == PACKET_SHA and
         capture['independent_review_sha256'] == REVIEW_SHA and capture['full_source_files_vendored'] is False and
         capture['full_history_vendored'] is False and capture['capture_complete_for_selected_artifacts'] is True and
         capture['research_source_files'] == 45 and capture['research_sealed_files'] == 156 and
         capture['original_json_serialization'] == 'compact_insertion_order_ensure_ascii_false_newline_or_original_bytes',
         'Torch capture count/scope/provenance differs')
    need(hashlib.sha256(local_path(root, PREFIX + 'captured/manifest.json').read_bytes()).hexdigest() == PACKET_SHA and
         hashlib.sha256(local_path(root, PREFIX + 'independent-review.json').read_bytes()).hexdigest() == REVIEW_SHA,
         'Torch accepted source/review immutable pin differs')
    need(review['sealed_manifest_sha256'] == PACKET_SHA and review['predecessor_manifest_sha256'] == PREDECESSOR_SHA and
         review['revision'] == REVISION and review['version'] == '2.14.1' and
         review['result'] == 'ACCEPTED_BOUNDED_SOURCE_DEFINITION' and review['findings'] == [] and
         review['same_independent_reviewer'] is True and
         {x['id'] for x in review['resolved_findings']} == {'F1-COMPLEX-FIXTURE-ENCODING', 'F2-AGGREGATE-SCOPE-CREDIT-COHERENCE'} and
         all(x['disposition'] == 'resolved' for x in review['resolved_findings']), 'Torch successor review acceptance differs')
    need(len(manifest['files']) == 156, 'Torch original sealed artifact count differs')
    by_name = {r['file']: r for r in manifest['files']}
    original = {}
    for row in capture['captured']:
        exact_fields(row, {'original_path': str, 'paths': list, 'storage': str, 'sha256': str}, 'Torch captured role')
        name = row['original_path']
        need(name in SELECTED and name not in original, 'Torch captured role unknown/duplicated')
        if row['storage'] == 'model-column-tables':
            names = ['model.json'] + [key + '.json' for key in ROW_FIELDS]
            need(name == 'dtype-model.json' and row['paths'] == [PREFIX + x for x in names], 'Torch model projection role differs')
            value = reconstruct_model(get('model.json'), {key: get(key + '.json') for key in ROW_FIELDS})
            data = original_bytes(value)
        else:
            need(row['storage'] in {'compact-json', 'original-bytes'} and len(row['paths']) == 1, 'Torch capture storage differs')
            expected_path = PREFIX + 'captured/' + ('README.source.txt' if name == 'README.md' else name)
            need(row['paths'] == [expected_path], 'Torch exact selected artifact path role differs')
            path = local_path(root, row['paths'][0]);need(path in paths, 'Torch captured role not indexed')
            value = read_json(path) if path.suffix == '.json' else path.read_text()
            data = original_bytes(value) if row['storage'] == 'compact-json' else path.read_bytes()
        expected = by_name[name]
        need(row['sha256'] == expected['sha256'] == hashlib.sha256(data).hexdigest() and len(data) == expected['bytes'],
             'Torch lossless accepted source projection differs: ' + name)
        original[name] = value
    need(set(original) == SELECTED, 'Torch selected original role conservation differs')
    initial = PREFIX + 'captured/history/initial-independent-review/initial-review.json'
    need(hashlib.sha256(local_path(root, initial).read_bytes()).hexdigest() == INITIAL_REVIEW_SHA,
         'Torch initial material findings history differs')
    expected = {PREFIX + x for x in ['capture.json', 'captured/manifest.json', 'independent-review.json',
        'joins.json', 'source-proof.json', 'acceptance-plan.json', 'review-proof.json']}
    expected |= {x for row in capture['captured'] for x in row['paths']}
    need({p.relative_to(root).as_posix() for p in paths} == expected, 'Torch indexed artifact role conservation differs')
    return original, docs, paths
