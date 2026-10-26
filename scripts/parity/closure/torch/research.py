import os
from pathlib import Path
import hashlib, json, urllib.request, concurrent.futures, os, zlib, re
ROOT = Path(__file__).resolve().parent
CACHE = Path('/tmp/atlas-framework-references')
CACHE.mkdir(exist_ok=True)
BASE = '2b3ec34829036a65cd9d1398ea72a0167dc37470'
REV = '5c4886908584029761b579af026dcfb627c84070'

def fetch(url):
    p = CACHE / hashlib.sha256(url.encode()).hexdigest()
    if p.exists():
        return p.read_bytes()
    if os.environ.get('ATLAS_REFERENCE_OFFLINE') == '1':
        raise RuntimeError('Missing frozen offline input: ' + url)
    req = urllib.request.Request(url, headers={'User-Agent': 'atlas-parity-reference-research/1'})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    p.write_bytes(data)
    return data

def json_url(url):
    return json.loads(fetch(url))

def published_names():
    raw = fetch('https://docs.pytorch.org/docs/2.14/objects.inv?raw=1')
    assert hashlib.sha256(raw).hexdigest() == '021a9908fed68dc53daf1a52b0f43fbd1719a7eb35beb03ab2d798b214c0fe31'
    lines = zlib.decompress(raw.split(b'\n', 4)[4]).decode().splitlines()
    names = {line.split()[0] for line in lines if line.split()[1].startswith('py:')}
    assert len(lines) == 18010 and len(names) == 9066
    return names

def save(name, data):
    (ROOT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
if __name__ == '__main__':
    compare_url = f'https://api.github.com/repos/pytorch/pytorch/compare/{BASE}...{REV}'
    c = json_url(compare_url)
    save('patch-comparison.json', c)
    print('comparison', c['ahead_by'], len(c['files']), [f['filename'] for f in c['files']], flush=True)
    trees = {}
    for label, rev in [('base', BASE), ('release', REV)]:
        url = f'https://api.github.com/repos/pytorch/pytorch/git/trees/{rev}?recursive=1'
        t = json_url(url)
        if t.get('sha') != rev or t.get('truncated') is not False:
            raise ValueError('Frozen PyTorch source tree mismatch or truncation: ' + label)
        save(label + '-tree.json', t)
        trees[label] = {x['path']: x for x in t['tree'] if x['type'] == 'blob'}
        print(label, 'tree', len(t['tree']), len(trees[label]), flush=True)
    files = ['docs/source/conf.py', 'torch/_torch_docs.py', 'torch/_tensor_docs.py', 'torch/_tensor.py', 'torch/__init__.py', 'torch/_C/__init__.pyi.in', 'aten/src/ATen/native/native_functions.yaml', 'tools/autograd/derivatives.yaml', 'aten/src/ATen/native/TensorFactories.cpp', 'aten/src/ATen/native/RangeFactories.cpp', 'aten/src/ATen/native/cpu/RangeFactoriesKernel.cpp', 'aten/src/ATen/native/cuda/RangeFactories.cu', 'torch/csrc/utils/tensor_new.cpp', 'torchgen/api/python.py', 'torch/csrc/autograd/python_torch_functions_manual.cpp', 'docs/source/tensors.rst', 'docs/source/notes/autograd.rst', 'docs/source/notes/out.rst', 'docs/source/notes/numerical_accuracy.rst', 'docs/source/generated/torch.zeros.rst', 'docs/source/generated/torch.full.rst']
    files = [f for f in files if f in trees['release']]

    def source(path):
        url = f'https://raw.githubusercontent.com/pytorch/pytorch/{REV}/{path}'
        data = fetch(url)
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\x00' + data).hexdigest()
        assert blob == trees['release'][path]['sha']
        out = ROOT / 'sources' / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        return {'path': path, 'url': url, 'sha256': hashlib.sha256(data).hexdigest(), 'git_blob': blob, 'bytes': len(data), 'line_count': len(data.splitlines()), 'base_git_blob': trees['base'].get(path, {}).get('sha'), 'unchanged_from_2_14_0': trees['base'].get(path, {}).get('sha') == blob}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        sources = list(pool.map(source, files))
    save('sources.json', sources)
    docs = [path for path in trees['release'] if path.startswith(('docs/source/', 'docs/cpp/source/'))]
    changes = [path for path in docs if trees['base'].get(path, {}).get('sha') != trees['release'][path]['sha']]
    save('scope-summary.json', {'base': BASE, 'revision': REV, 'comparison_url': compare_url, 'comparison_sha256': hashlib.sha256(fetch(compare_url)).hexdigest(), 'compare_total_commits': c['total_commits'], 'compare_files': len(c['files']), 'all_changed_files': [f['filename'] for f in c['files']], 'docs_file_count': len(docs), 'changed_documentation_blobs': changes, 'selected_sources': sources})
    print('sources fetched', len(sources), 'docs files', len(docs), 'docs changes', changes, flush=True)
