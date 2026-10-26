"""Portable selected source receipts/spans bound to accepted full-file review."""
import hashlib

from atlas_parity_dtype_headers import exact_fields
from atlas_parity_schema import need
from atlas_parity_tables import canonical


def proof(registry, witnesses):
    return {'schema_version': 1, 'full_source_files_vendored': False, 'whole_API_or_runtime_credit': False,
        'records': [{'path': row['path'], 'git_blob_sha': row['git_blob_sha'], 'sha256': row['sha256'],
            'bytes': row['bytes'], 'line_count': row['line_count'], 'source_entry': ['records', i],
            'span_ids': [w['id'] for w in witnesses['records'] if w['path'] == row['path']]} for i, row in enumerate(registry['records'])],
        'scope': 'full_file_receipts_and_bounded_exact_excerpts_not_local_full_source_reverification_or_CFG'}


def validate_sources(registry, witnesses, manifest, document):
    exact_fields(document, {'schema_version': int, 'full_source_files_vendored': bool, 'whole_API_or_runtime_credit': bool,
        'records': list, 'scope': str}, 'Torch source proof header')
    by_file = {r['file']: r for r in manifest['files']}
    sources = {r['path']: r for r in registry['records']}
    need(len(sources) == 45 and len(witnesses['records']) == 88, 'Torch source receipt/span conservation differs')
    for row in registry['records']:
        exact_fields(row, {'path': str, 'revision': str, 'repository': str, 'git_blob_sha': str, 'sha256': str,
            'bytes': int, 'line_count': int, 'snapshot': str, 'url': str, 'acquisition': str}, 'Torch exact source receipt')
        raw = by_file[row['snapshot']]
        need(row['snapshot'] == 'sources/' + row['path'] and row['repository'] == 'pytorch/pytorch' and
             row['revision'] == '5c4886908584029761b579af026dcfb627c84070' and
             row['sha256'] == raw['sha256'] and row['bytes'] == raw['bytes'] and row['line_count'] > 0 and
             row['url'] == f"https://github.com/pytorch/pytorch/blob/{row['revision']}/{row['path']}",
             'Torch accepted full-file source receipt differs')
    ids = set()
    for row in witnesses['records']:
        exact_fields(row, {'id': str, 'path': str, 'revision': str, 'git_blob_sha': str, 'source_sha256': str,
            'source_bytes': int, 'source_line_count': int, 'start_line': int, 'end_line': int, 'url': str,
            'excerpt': str, 'excerpt_sha256': str}, 'Torch exact source span')
        source = sources[row['path']]
        need(row['id'] not in ids and 1 <= row['start_line'] <= row['end_line'] <= source['line_count'] and
             row['revision'] == source['revision'] and row['git_blob_sha'] == source['git_blob_sha'] and
             row['source_sha256'] == source['sha256'] and row['source_bytes'] == source['bytes'] and
             row['source_line_count'] == source['line_count'] and
             len(row['excerpt'].splitlines()) == row['end_line'] - row['start_line'] + 1 and
             hashlib.sha256(row['excerpt'].encode()).hexdigest() == row['excerpt_sha256'] and
             row['url'] == source['url'] + f"#L{row['start_line']}-L{row['end_line']}",
             'Torch exact quote/source/line/hash binding differs')
        ids.add(row['id'])
    for i, row in enumerate(document['records']):
        exact_fields(row, {'path': str, 'git_blob_sha': str, 'sha256': str, 'bytes': int, 'line_count': int,
                          'source_entry': list, 'span_ids': list}, 'Torch typed source proof row')
        from atlas_parity_torch_dtype_joins import selector
        selector(row['source_entry'], 'records', i)
    need(canonical(document) == canonical(proof(registry, witnesses)), 'Torch selected source proof projection differs')
    return ids
