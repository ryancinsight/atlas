import hashlib, json, tarfile, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent
SPECS = [('tensorflow', 'tensorflow/tensorflow', 'a481b10260dfdf833a1b16007eead49c1d7febf3', str(ROOT / 'tensorflow-tree.json')), ('keras', 'keras-team/keras', '250b42181ce9f37df68319d8f4753ec89a349a43', str(ROOT / 'keras-tree.json'))]
EXTRA_TF = {'tensorflow/core/ops/array_ops.cc', 'tensorflow/core/ops/math_ops.cc', 'tensorflow/core/kernels/constant_op.cc', 'tensorflow/core/kernels/sequence_ops.cc', 'tensorflow/core/kernels/sequence_ops.h', 'tensorflow/core/kernels/sequence_ops_gpu.cu.cc', 'tensorflow/core/kernels/fill_functor.h', 'tensorflow/core/kernels/fill_functor.cc', 'tensorflow/compiler/tf2xla/kernels/sequence_ops.cc', 'tensorflow/compiler/tf2xla/kernels/constant_op.cc'}
for name, repo, revision, tree_file in SPECS:
    tree = json.load(open(tree_file))
    assert not tree['truncated']
    expected = {i['path']: i for i in tree['tree'] if i['type'] == 'blob' and (i['path'].endswith('.py') or (name == 'tensorflow' and i['path'] in EXTRA_TF))}
    dest = ROOT / 'source' / name
    dest.mkdir(parents=True, exist_ok=True)
    seen = {}
    todo = set(expected)
    for p, i in expected.items():
        target = dest / p
        if target.exists():
            b = target.read_bytes()
            actual = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\x00' + b).hexdigest()
            if actual == i['sha']:
                seen[p] = {'path': p, 'git_blob_sha': actual, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}
                todo.remove(p)
    if todo:
        url = f'https://codeload.github.com/{repo}/tar.gz/{revision}'
        print('reading', name, 'wanted', len(todo), flush=True)
        response = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60)
        with tarfile.open(fileobj=response, mode='r|gz') as archive:
            for member in archive:
                p = member.name.split('/', 1)[-1]
                if p not in todo:
                    continue
                b = archive.extractfile(member).read()
                actual = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\x00' + b).hexdigest()
                assert actual == expected[p]['sha'], p
                target = dest / p
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b)
                seen[p] = {'path': p, 'git_blob_sha': actual, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}
                todo.remove(p)
    assert not todo, sorted(todo)
    payload = {'name': name, 'repository': repo, 'revision': revision, 'tree_truncated': False, 'selected_count': len(expected), 'verified_count': len(seen), 'source_bytes': sum((i['bytes'] for i in seen.values())), 'selection': 'all tracked Python files plus explicitly named TensorFlow constructor kernel/operation/XLA files', 'files': [seen[p] for p in sorted(seen)]}
    (ROOT / (name + '-source-manifest.json')).write_text(json.dumps(payload, separators=(',', ':')) + '\n', encoding='utf-8')
    print(name, len(seen), payload['source_bytes'], flush=True)
