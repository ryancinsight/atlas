"""Lossless projections of the independently reviewed source-only dtype packet."""
import hashlib
import json

from atlas_parity_schema import fields, local_path, need, read_json
from atlas_parity_tables import unpack

PACKET_SHA = '72206a73ecad553b819b42af2f45fc35efcdf4b6a3dea45de86e96af9fc3befe'
REVIEW_SHA = '364896a26a94ba037ed6895c072e9dd3211c2faa5e0298a411328d3db87f995f'
PREFIX = 'dtype-policy/jax-20261026/'


def original_bytes(document):
    return (json.dumps(document, indent=2, sort_keys=True) + '\n').encode()


def graphs_from_tables(metadata, table):
    # Preserve original graph and pair order, including null versus absent keys.
    need(all('pair_table' not in g for g in metadata['graphs']), 'dtype compact graph duplicates pair storage')
    need(table['metadata'] == {'role': 'finite_source_symbol_pairs_not_runtime_or_dtype_legality',
                              'source_pairs': 9256}, 'dtype pair table must retain source-only role')
    result = dict(metadata)
    result['graphs'] = [dict(g, pair_table=[]) for g in metadata['graphs']]
    by_id = {g['id']: g for g in result['graphs']}
    need(len(by_id) == len(result['graphs']), 'dtype compact graph identity duplicated')
    for row in unpack(table):
        row = dict(row)
        identity = row.pop('_graph_id', None)
        need(identity in by_id, 'dtype pair table has unknown graph')
        by_id[identity]['pair_table'].append(row)
    return result


def validate_capture(root, index):
    paths = []
    documents = {}
    for item in index['artifacts']:
        fields(item, {'path': str, 'sha256': str}, 'dtype artifact')
        path = local_path(root, item['path'])
        need(path not in paths and hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'],
             'dtype artifact hash drift or repeated input')
        paths.append(path)
        if path.suffix == '.json':
            documents[item['path']] = read_json(path)
    def get(name):
        key = PREFIX + name
        need(key in documents, 'dtype artifact absent: ' + name)
        return documents[key]
    capture = get('capture.json')
    manifest_path = local_path(root, PREFIX + 'captured/deliverable-manifest.json')
    review_path = local_path(root, PREFIX + 'independent-review.json')
    need(hashlib.sha256(manifest_path.read_bytes()).hexdigest() == PACKET_SHA and
         hashlib.sha256(review_path.read_bytes()).hexdigest() == REVIEW_SHA,
         'dtype accepted source manifest/review hash differs')
    manifest = get('captured/deliverable-manifest.json')
    review = get('independent-review.json')
    need(review['reviewed_manifest_sha256'] == PACKET_SHA and
         review['result'] == 'accept_bounded_source_dtype_policy_definition' and
         not review['blocking_findings'], 'dtype source review does not accept this packet')
    need(capture['schema_version'] == 1 and capture['source_manifest_sha256'] == PACKET_SHA and
         capture['independent_review_sha256'] == REVIEW_SHA and
         capture['full_source_files_vendored'] is False and
         capture['capture_complete_for_selected_artifacts'] is True,
         'dtype source capture provenance/scope drift')
    original = {}
    for row in capture['captured']:
        name = row['original_path']
        need(name not in original and name in manifest['files'], 'dtype captured role duplicated or unknown')
        if row['storage'] == 'graph-with-column-pairs':
            need(name == 'promotion-graph.json' and row['paths'] ==
                 [PREFIX + 'graph.json', PREFIX + 'pairs.json'], 'dtype graph capture role drift')
            value = graphs_from_tables(get('graph.json'), get('pairs.json'))
            data = original_bytes(value)
        else:
            need(row['storage'] in {'original-bytes', 'compact-json'} and len(row['paths']) == 1,
                 'dtype capture encoding unknown')
            path = local_path(root, row['paths'][0])
            need(path in paths, 'dtype captured path not indexed')
            if row['storage'] == 'compact-json':
                value = get(path.relative_to(root).as_posix().removeprefix(PREFIX))
                data = original_bytes(value)
            else:
                data = path.read_bytes()
                value = read_json(path) if path.suffix == '.json' else data.decode()
        expected = manifest['files'][name]
        need(row['sha256'] == expected['sha256'] == hashlib.sha256(data).hexdigest() and
             len(data) == expected['bytes'], 'dtype lossless original packet projection drift: ' + name)
        original[name] = value
    required = {'README.md', 'promotion-graph.json', 'dtype-catalog.json', 'policy-contracts.json',
                'CP02-evidence-audit.json', 'acceptance-targets.json', 'remaining-gaps.json',
                'analytical-witnesses.json', 'scope.json', 'source-receipts.json', 'verification.json',
                'inputs/CP02.json', 'inputs/capture.json'}
    need(set(original) == required, 'dtype source capture original role set drift')
    return original, documents, paths
