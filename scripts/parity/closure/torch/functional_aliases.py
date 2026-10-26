from research import *
import re, ast
p = 'torch/functional.py'
url = f'https://raw.githubusercontent.com/pytorch/pytorch/{REV}/{p}'
raw = fetch(url)
tree = {x['path']: x for x in json.loads((ROOT / 'release-tree.json').read_text(encoding='utf-8'))['tree'] if x['type'] == 'blob'}
blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\x00' + raw).hexdigest()
assert blob == tree[p]['sha']
(ROOT / 'sources' / p).write_bytes(raw)
rows = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
rows.append({'path': p, 'url': url, 'sha256': hashlib.sha256(raw).hexdigest(), 'git_blob': blob, 'bytes': len(raw), 'line_count': len(raw.splitlines())})
save('sources.json', rows)
module = ast.parse(raw)
allnode = next((n for n in module.body if isinstance(n, ast.Assign) and any((isinstance(t, ast.Name) and t.id == '__all__' for t in n.targets))))
exported = ast.literal_eval(allnode.value)
text = (ROOT / 'sources/docs/source/torch.aliases.md').read_text(encoding='utf-8')
documented = re.findall('^    ([a-zA-Z_]\\w*)\\s*$', text, re.M)
assert set(documented) <= set(exported)
init = (ROOT / 'sources/torch/__init__.py').read_text(encoding='utf-8').splitlines()
line = next((i for i, x in enumerate(init, 1) if x.startswith('from torch.functional import *')))
relations = [{'source_symbol': 'torch.' + n, 'target_symbol': 'torch.functional.' + n, 'relation': 'documented_namespace_export_alias', 'source': f'https://github.com/pytorch/pytorch/blob/{REV}/docs/source/torch.aliases.md#L1', 'binding_source': f'https://github.com/pytorch/pytorch/blob/{REV}/torch/__init__.py#L{line}', 'export_source': f'https://github.com/pytorch/pytorch/blob/{REV}/torch/functional.py#L{allnode.lineno}', 'semantic_merge_authorized': False, 'required_review': 'Same exported function source; retain public spellings, signatures/defaults and variant tests; no global framework capability closure inferred.'} for n in documented]
supp = json.loads((ROOT / 'source-supplement.json').read_text(encoding='utf-8'))
supp['namespace_export_aliases'] = relations
supp['summary']['counts']['namespace_export_alias_relations'] = len(relations)
supp['summary']['counts']['source_files_hash_verified'] = len(rows)
save('source-supplement.json', supp)
save('closure-summary.json', supp['summary'])
print('namespace aliases', len(relations), 'source count', len(rows))
