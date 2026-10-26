"""Verify the read-only PyTorch research proposal; no reference runtime imports."""
from pathlib import Path
import ast, copy, hashlib, json, re
from research import published_names
ROOT = Path(__file__).resolve().parent
REV = '5c4886908584029761b579af026dcfb627c84070'

def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))

def verify_supplement(data):
    source = ROOT / 'sources'
    rows = data['source_docstrings']
    generated = data['generated_candidates']
    schemas = data['operator_schemas']
    aliases = data['documented_aliases']
    cpp = data['cpp_inputs']
    assert len(rows) == len({r['symbol'] for r in rows}) == 1020
    assert len(generated) == len({r['symbol'] for r in generated}) == 58
    assert len(schemas) == len({r['schema'] for r in schemas}) == 2585
    assert len(aliases) == 56
    assert len(data['namespace_export_aliases']) == 19
    assert all((r['semantic_merge_authorized'] is False for r in data['namespace_export_aliases']))
    assert all((r['semantic_merge_authorized'] is False for r in aliases))
    assert len(cpp) == 49 and sum((r['state'] == 'generated_build_input_missing_from_git_tree' for r in cpp)) == 3
    for r in rows:
        assert r['source'].endswith(f"/{r['source_path']}#L{r['line']}")
        line = (source / r['source_path']).read_text(encoding='utf-8').splitlines()[r['line'] - 1]
        assert line.strip() in ('add_docstr(', 'add_docstr_all(')
    for r in schemas:
        path, line = r['source'].split(f'/blob/{REV}/', 1)[1].split('#L')
        assert (source / path).read_text(encoding='utf-8').splitlines()[int(line) - 1] == '- func: ' + r['schema']
    names = published_names()
    missing = {r['symbol'] for r in rows} - names
    assert missing == {r['symbol'] for r in data['missing_inventory_targets']} and len(missing) == 27
    assert 'torch.Tensor.new_empty_strided' in missing
    assert all(('hasattr' in r['conditional_exposure'] for r in generated))
    assert 'torch._foreach_exp_' in {r['symbol'] for r in generated}
    return len(rows) + len(generated) + len(schemas)

def main():
    sources = load('sources.json')
    tree = {x['path']: x for x in load('release-tree.json')['tree'] if x['type'] == 'blob'}
    assert len(sources) == 40 and len({s['path'] for s in sources}) == 40
    for s in sources:
        raw = (ROOT / 'sources' / s['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == s['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\x00' + raw).hexdigest() == s['git_blob'] == tree[s['path']]['sha']
    compare = load('patch-comparison.json')
    assert compare['base_commit']['sha'] == '2b3ec34829036a65cd9d1398ea72a0167dc37470'
    assert compare['total_commits'] == len(compare['commits']) == 5 and len(compare['files']) == 15
    base = {x['path']: x['sha'] for x in load('base-tree.json')['tree'] if x['type'] == 'blob'}
    release = {k: v['sha'] for k, v in tree.items()}
    changed = {p for p in set(base) | set(release) if base.get(p) != release.get(p)}
    assert changed == {x['filename'] for x in compare['files']}
    assert not [p for p in changed if p.startswith(('docs/source/', 'docs/cpp/source/'))]
    data = load('source-supplement.json')
    count = verify_supplement(data)
    failures = []
    for label, mutate in [('lost inherited method', lambda d: d['source_docstrings'].pop()), ('lost schema', lambda d: d['operator_schemas'].pop()), ('unsafe alias merge', lambda d: d['documented_aliases'][0].update(semantic_merge_authorized=True)), ('dropped missing inventory target', lambda d: d['missing_inventory_targets'].pop())]:
        broken = copy.deepcopy(data)
        mutate(broken)
        try:
            verify_supplement(broken)
        except AssertionError:
            failures.append(label)
    assert len(failures) == 4
    contracts = load('constructor-contracts.json')
    assert len(contracts['records']) == contracts['record_count'] == 14
    for row in contracts['records']:
        assert row['implementation_status'] == 'unmapped' and row['test_status'] == 'unrun'
        assert row.get('reference_contradictions') is not None
        assert row.get('workflow', {}).get('coverage_status') == 'source_audited_partial_axes; not a complete public API mapping or execution evidence'
    assert list(range(-5, 6, 3)) == [-5, -2, 1, 4]
    assert [-3 + (5 - -3) * i / 4 for i in range(5)] == [-3, -1, 1, 3, 5]
    assert [2.0 ** (-2 + i) for i in range(5)] == [0.25, 0.5, 1.0, 2.0, 4.0]
    result = {'source_integrity_files': len(sources), 'patch_commits': 5, 'patch_files': 15, 'docs_blobs_unchanged': 408, 'retained_source_and_schema_records': count, 'constructor_contract_proposals': 14, 'negative_mutations_rejected': failures, 'reference_runtime_imports': 0, 'reference_runtime_tests': 0, 'public_surface_complete': False, 'semantic_api_mapping_complete': False}
    (ROOT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
if __name__ == '__main__':
    main()
