"""Bounded immutable source-input comparison; never promotes older semantics."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def main():
    previous = json.loads((ROOT / 'source-v2.5.0-provenance.json').read_text(encoding='utf-8'))
    old = {entry['path']: entry['sha'] for entry in json.loads((ROOT / 'source-tree-v2.5.0.json').read_text(encoding='utf-8'))['tree'] if entry['type'] == 'blob'}
    new = {entry['path']: entry['sha'] for entry in json.loads((ROOT / 'source-tree.json').read_text(encoding='utf-8'))['tree'] if entry['type'] == 'blob'}
    all_paths = set(old) | set(new)
    audited = {entry['path'] for entry in json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))}
    groups = {'all_documentation_sources_including_notebooks_templates': {p for p in all_paths if p.startswith('doc/source/')}, 'documentation_config_and_requirements': {'doc/source/conf.py', 'requirements/doc_requirements.txt'}, 'non_test_type_stubs': {p for p in all_paths if p.startswith('numpy/') and p.endswith('.pyi') and ('/tests/' not in p)}, 'ufunc_and_type_codegen': {p for p in all_paths if p.startswith('numpy/_core/code_generators/') or p in {'numpy/_core/src/umath/umathmodule.c', 'numpy/_core/src/multiarray/arraytypes.c.src', 'numpy/_core/src/multiarray/scalartypes.c.src'}}, 'export_module_initializers': {p for p in all_paths if p.startswith('numpy/') and p.endswith(('/__init__.py', '/__init__.pyi')) and ('/tests/' not in p)}, 'exact_static_audit_input_files': audited}
    results = {}
    for name, paths in groups.items():
        comparisons = []
        for path in sorted(paths):
            status = 'unchanged' if old.get(path) == new.get(path) else 'added' if path not in old else 'removed' if path not in new else 'changed'
            comparisons.append({'path': path, 'status': status, 'old_git_blob_sha': old.get(path), 'new_git_blob_sha': new.get(path), 'old_source': f"https://github.com/numpy/numpy/blob/{previous['revision']}/{path}", 'new_source': f'https://github.com/numpy/numpy/blob/a3d0ef1df045b858e68115001fdabc930bb3b68c/{path}'})
        counts = {status: sum((item['status'] == status for item in comparisons)) for status in ['unchanged', 'changed', 'added', 'removed']}
        assert sum(counts.values()) == len(paths)
        results[name] = {'total': len(paths), 'counts': counts, 'identical_within_this_bound': counts['unchanged'] == len(paths), 'files': comparisons}
    data = {'schema_version': 1, 'old_version': '2.5.0', 'old_revision': previous['revision'], 'frozen_version': '2.5.4', 'frozen_revision': 'a3d0ef1df045b858e68115001fdabc930bb3b68c', 'comparison': 'Exact Git blob identity, not a semantic API-equivalence assumption', 'groups': results, 'entire_rendered_symbol_inventory_equivalence_proven': False, 'conclusion': 'The official2.5.0 inventory remains supplemental. Changed documentation/type/generator/export inputs prevent a blanket exact-input proof for the2.5.4 generated/inherited inventory. Unchanged bounded inputs can support targeted symbol reconciliation; no2.5.0 numerical or error semantics are promoted.', 'uncovered_generation_inputs': ['Build environment, imported builtin/extension runtime members, Sphinx extension dependency transitive graph and platform-conditioned C templates are not exhausted by these static file bounds.']}
    (ROOT / 'source-comparison-2.5.0-to-2.5.4.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value['counts'] for key, value in results.items()}, sort_keys=True))
if __name__ == '__main__':
    main()
