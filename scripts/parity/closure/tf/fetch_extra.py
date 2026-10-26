import hashlib, json, urllib.request
from pathlib import Path
root = Path(__file__).resolve().parent
src = root / 'source/tensorflow'
rev = 'a481b10260dfdf833a1b16007eead49c1d7febf3'
tree = json.load(open(str(ROOT / 'tensorflow-tree.json')))['tree']
lookup = {x['path']: x for x in tree}
paths = ['tensorflow/core/framework/register_types.h', 'tensorflow/core/framework/types.h', 'tensorflow/compiler/tf2xla/kernels/fill_op.cc']
manifest = json.load(open(root / 'tensorflow-source-manifest.json'))
entries = {x['path']: x for x in manifest['files']}
for p in paths:
    b = urllib.request.urlopen(urllib.request.Request(f'https://raw.githubusercontent.com/tensorflow/tensorflow/{rev}/{p}', headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read()
    s = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\x00' + b).hexdigest()
    assert s == lookup[p]['sha']
    f = src / p
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b)
    entries[p] = {'path': p, 'git_blob_sha': s, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}
manifest.update({'selected_count': len(entries), 'verified_count': len(entries), 'source_bytes': sum((x['bytes'] for x in entries.values())), 'files': [entries[p] for p in sorted(entries)]})
(root / 'tensorflow-source-manifest.json').write_text(json.dumps(manifest, separators=(',', ':')) + '\n', encoding='utf-8')
print('source_files', len(entries))
