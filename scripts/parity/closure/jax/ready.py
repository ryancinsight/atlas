"""Emit only requested member identities with reviewed static resolution."""
import json
from pathlib import Path
P = Path(__file__).parent
report = json.loads((P / 'autodoc-dispositions.json').read_text(encoding='utf-8'))
sources = {r['path']: r for r in report['sources']}
records = []
for row in report['dispositions']:
    if row['state'] != 'expanded_requested_member_set':
        continue
    for member in row['generated_members']:
        path = member['source'].split('/' + report['source_revision'] + '/', 1)[1].split('#', 1)[0]
        records.append({'framework': 'jax', 'version': '0.12.0.1', 'symbol': member['symbol'], 'kind': member['kind'], 'source': member['source'], 'domain': 'autodiff-compiler', 'stability': 'release-documented-stability-unreviewed', 'deprecation_status': 'not-yet-reviewed', 'occurrences': [{'path': path, 'line': member['line'], 'kind': member['kind'], 'documentation_directive': row['source'], 'selection_basis': 'Explicit requested member or directly documented public method of class with :members:', 'inherited_from': member.get('inherited_from')}], 'signature': member.get('signature'), 'definition_status': 'documented API identity addition only; full semantic mapping remains unreviewed'})
needed = {o['path'] for r in records for o in r['occurrences']}
assert len(records) == len({r['symbol'] for r in records}) == 22
result = {'framework': 'jax', 'version': '0.12.0.1', 'input_inventory_sha256': report['input_inventory_sha256'], 'source_revision': report['source_revision'], 'records': records, 'sources': [sources[path] for path in sorted(needed)], 'new_documented_identities': len(records), 'full_semantic_mappings_completed': 0, 'scope': 'Review-ready finite first slice; preserve unresolved classes and source namespace candidates separately.'}
(P / 'review-ready-additions.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print({'additions': len(records), 'source_files': len(needed)})
