"""Lossless selected captures of independently accepted public-surface evidence."""
import hashlib
import json

from atlas_parity_dtype_headers import exact_fields
from atlas_parity_schema import local_path, need, read_json
from atlas_parity_tables import unpack

PREFIX = 'reference/public-evidence/'
FROZEN_ATLAS = '20ae8d85f6c3aa6a6712e4f0b823b5f066bdc008'
NO_CREDIT = dict(admission_changes=0, new_reference_IDs=0, mapping_stage_changes=0,
    route_owner_verifications=0, framework_execution_credit=0, provider_execution_credit=0,
    semantic_completion_credit=0, performance_credit=0, release_credit=0,
    whole_public_surface_complete=False)
PACKETS = {
 'tf492': dict(directory='tensorflow-492-20261026', manifest='manifest.json',
    manifest_sha256='ac452a116143b668c2f40840022674649f214940c0fff9d14400e77566c023b4',
    review_sha256='47d7cb36e104bd9666846a937e96ba13ee100b9b71b9e715597e57dbdd50a114',
    sealed_files=199, source_files=155, source_spans=747,
    selected={'README.md': None, 'dispositions.json': 'records', 'source-registry.json': 'sources',
      'line-witnesses.json': 'records', 'workflow-contracts.json': 'contracts',
      'classification-rules.json': None, 'companion-consumer-context.json': 'records',
      'ownership-route-comparison.json': 'records', 'remaining-gaps.json': None,
      'transitive-public-obligations.json': None, 'inputs/operator-protocol-resolution.json': None,
      'input-manifest.json': None}),
 'six': dict(directory='jax-torch-six-20261026', manifest='deliverable-manifest.json',
    manifest_sha256='67ed237788d85c2cd6a44751a79ab11a366981840b7d8f878875e111cd744bd2',
    review_sha256='29c75bc93843600bdc8a05119900667bcf29f29c9e4dabbc00e31d5188556d7d',
    sealed_files=265, source_files=15, source_spans=1010,
    selected={'README.md': None, 'six-dispositions.json': 'records', 'source-receipts.json': None,
      'tooling-selection-evidence.json': 'method_fingerprints', 'configuration-selection-evidence.json': None,
      'published-inventory-evidence.json': None, 'returned-tooling-views.json': 'source_lambda_views',
      'remaining-evidence.json': None, 'canonical-anchors.json': None, 'inputs/original-six.json': None})}
ADMISSION_MANIFEST_SHA = '0df315ad9b771daa81610fb6f293fcfb7e82b46f3023422d61a6334a9c77cfb9'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def exact(value, expected, context):
    """Typed structural equality; Python bool/integer/float aliases never match."""
    need(type(value) is type(expected), context + ': type drift')
    if type(expected) is dict:
        need(value.keys() == expected.keys(), context + ': field drift')
        for key in expected:
            exact(value[key], expected[key], context + '.' + key)
    elif type(expected) is list:
        need(len(value) == len(expected), context + ': count drift')
        for index, (a, b) in enumerate(zip(value, expected)):
            exact(a, b, context + f'[{index}]')
    else:
        need(value == expected, context + ': value drift')


def original_bytes(value, serialization):
    options = {'sort_keys': True, 'allow_nan': False}
    if serialization == 'compact-unicode':
        options.update(separators=(',', ':'), ensure_ascii=False)
    elif serialization == 'pretty-ascii':
        options.update(indent=2, ensure_ascii=True)
    else:
        need(False, 'public evidence: unknown original JSON serialization')
    return (json.dumps(value, **options) + '\n').encode()


def manifest_files(document):
    rows = document['files']
    return rows if type(rows) is dict else {r.get('path', r.get('file')): r for r in rows}


def review_binding(key, review, config):
    need(review['reviewed_manifest_sha256'] == config['manifest_sha256'], 'public evidence review/manifest drift')
    if key == 'tf492':
        need(review['result'] == 'accepted_bounded_source_and_guard_successor' and review['findings'] == [] and
             review['input_atlas_revision'] == FROZEN_ATLAS and review['scope_assessment']['canonical_admission_changes'] == 0 and
             review['scope_assessment']['framework_executions'] == 0, 'TF492 accepted review scope drift')
    else:
        need(review['result'] == 'accept_bounded_source_definition_only' and review['blocking_findings'] == [] and
             review['checks']['offline_Git_commit'] == FROZEN_ATLAS and review['checks']['framework_or_Sphinx_imports'] == 0,
             'six-row accepted review scope drift')


def capture(root, key, relative):
    config = PACKETS[key]
    prefix = PREFIX + config['directory'] + '/'
    expected_path = prefix + 'index.json'
    need(relative == expected_path, 'public evidence capture index role changed')
    path = local_path(root, relative)
    index = read_json(path)
    exact_fields(index, {'schema_version': int, 'packet': str, 'introduced_in_program': str,
        'source_manifest_sha256': str, 'source_review_sha256': str, 'frozen_atlas_revision': str,
        'artifacts': list, 'capture': dict, 'status': dict}, 'public evidence packet index')
    exact({k: index[k] for k in ('schema_version', 'packet', 'introduced_in_program', 'source_manifest_sha256',
        'source_review_sha256', 'frozen_atlas_revision', 'status')}, dict(schema_version=1, packet=key,
        introduced_in_program='2026-10-26.11', source_manifest_sha256=config['manifest_sha256'],
        source_review_sha256=config['review_sha256'], frozen_atlas_revision=FROZEN_ATLAS, status=NO_CREDIT),
        'public evidence packet metadata/no credit')
    paths, docs = [path], {}
    for row in index['artifacts']:
        exact_fields(row, {'path': str, 'sha256': str}, 'public evidence artifact role')
        file = local_path(root, row['path'])
        need(row['path'].startswith(prefix) and file not in paths and sha(file.read_bytes()) == row['sha256'],
             'public evidence artifact role/hash/duplicate drift')
        paths.append(file)
        docs[row['path']] = read_json(file) if file.suffix == '.json' else file.read_text()
    def get(name):
        full = prefix + name
        need(full in docs, 'public evidence missing role: ' + name)
        return docs[full]
    manifest = get('source-manifest.json'); review = get('independent-review.json')
    need(sha(local_path(root, prefix + 'source-manifest.json').read_bytes()) == config['manifest_sha256'] and
         sha(local_path(root, prefix + 'independent-review.json').read_bytes()) == config['review_sha256'],
         'public evidence accepted source/review pin differs')
    source_files = manifest_files(manifest)
    need(len(source_files) == config['sealed_files'], 'public evidence original sealed file count drift')
    review_binding(key, review, config)
    header = index['capture']
    exact_fields(header, {'selected': list, 'standalone_foreign_source_files_vendored': bool,
        'whole_history_vendored': bool, 'complete_for_selected_roles': bool, 'source_files': int,
        'source_spans': int, 'original_review_scope': str}, 'public evidence capture metadata')
    exact({k: header[k] for k in header if k != 'selected'}, dict(standalone_foreign_source_files_vendored=False,
        whole_history_vendored=False, complete_for_selected_roles=True, source_files=config['source_files'],
        source_spans=config['source_spans'], original_review_scope='accepted_original_source_only_not_canonical_candidate_review'),
        'public evidence capture scope/counts')
    original, selected_paths = {}, set()
    for row in header['selected']:
        exact_fields(row, {'original_path': str, 'paths': list, 'storage': str,
            'collection': type(None) if row.get('collection') is None else str,
            'serialization': str, 'original_sha256': str}, 'public evidence captured role')
        name = row['original_path']
        need(name in config['selected'] and name not in original and row['collection'] == config['selected'][name],
             'public evidence selected source role duplicated/unknown')
        for selected in row['paths']:
            need(type(selected) is str and selected in docs and selected not in selected_paths,
                 'public evidence selected path role/duplicate')
            selected_paths.add(selected)
        if row['storage'] == 'column-records':
            need(row['collection'] is not None and len(row['paths']) == 2,
                 'public evidence record-table role drift')
            metadata, table = (docs[p] for p in row['paths'])
            exact_fields(table, {'format': str, 'metadata': dict, 'columns': list, 'tables': dict, 'rows': list},
                         'public evidence lossless source table')
            exact(table['metadata'], dict(packet=key, original_path=name, collection=row['collection']),
                  'public evidence table role')
            need(type(metadata) is dict and row['collection'] not in metadata, 'public evidence table metadata drift')
            value = dict(metadata, **{row['collection']: unpack(table)})
            data = original_bytes(value, row['serialization'])
        else:
            need(row['collection'] is None or row['storage'] == 'original-bytes', 'public evidence collection storage drift')
            need(len(row['paths']) == 1, 'public evidence source path arity')
            value = docs[row['paths'][0]]
            if row['storage'] == 'compact-json':
                data = original_bytes(value, row['serialization'])
            else:
                need(row['storage'] == 'original-bytes' and row['serialization'] == 'original-bytes',
                     'public evidence source encoding unknown')
                data = local_path(root, row['paths'][0]).read_bytes()
        receipt = source_files[name]
        need(row['original_sha256'] == receipt['sha256'] == sha(data) and len(data) == receipt['bytes'],
             'public evidence lossless accepted source differs: ' + name)
        original[name] = value
    need(set(original) == set(config['selected']), 'public evidence selected source set differs')
    exact(set(docs), selected_paths | {prefix + 'source-manifest.json', prefix + 'independent-review.json'},
          'public evidence indexed source role set')
    return original, paths
