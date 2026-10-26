from research import *
t = json.loads((ROOT / 'release-tree.json').read_text(encoding='utf-8'))
tree = {x['path']: x for x in t['tree'] if x['type'] == 'blob'}
files = ['aten/src/ATen/native/RangeFactories.h', 'docs/source/tensors.md', 'docs/source/tensor_attributes.md', 'docs/source/tensor_view.md', 'docs/source/torch.aliases.md', 'docs/source/notes/autograd.md', 'docs/source/notes/out.md', 'docs/source/notes/numerical_accuracy.md', 'docs/source/torch.md', 'docs/cpp/source/api/aten/creation.md', 'docs/cpp/source/Doxyfile', 'docs/cpp/check_coverage.py', 'tools/autograd/gen_python_functions.py', 'torch/_C/_VariableFunctions.pyi.in', 'torch/_C/_nn.pyi.in', 'torch/csrc/utils/python_arg_parser.cpp', 'torch/csrc/autograd/generated/python_variable_methods.cpp', 'torchgen/packaged/autograd/derivatives.yaml']

def source(path):
    url = f'https://raw.githubusercontent.com/pytorch/pytorch/{REV}/{path}'
    data = fetch(url)
    actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\x00' + data).hexdigest()
    assert actual == tree[path]['sha']
    out = ROOT / 'sources' / path
    out.parent.mkdir(exist_ok=True, parents=True)
    out.write_bytes(data)
    return {'path': path, 'url': url, 'sha256': hashlib.sha256(data).hexdigest(), 'git_blob': actual, 'line_count': len(data.splitlines()), 'bytes': len(data)}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    new = list(pool.map(source, [p for p in files if p in tree]))
s = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
s.extend(new)
save('sources.json', s)
print('sources', len(s), flush=True)
