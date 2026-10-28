from research import *
t = {x['path']: x for x in json.loads((ROOT / 'release-tree.json').read_text(encoding='utf-8'))['tree'] if x['type'] == 'blob'}
files = ['aten/src/ATen/native/RangeUtils.h', 'torch/autograd/grad_mode.py', 'torch/csrc/autograd/variable.h', 'c10/core/ScalarType.h', 'aten/src/ATen/AccumulateType.h', 'aten/src/ATen/native/Fill.cpp', 'aten/src/ATen/native/cpu/FillKernel.cpp', 'aten/src/ATen/native/cuda/FillKernel.cu']
rows = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
for path in files:
    if path not in t:
        continue
    url = f'https://raw.githubusercontent.com/pytorch/pytorch/{REV}/{path}'
    data = fetch(url)
    blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\x00' + data).hexdigest()
    assert blob == t[path]['sha']
    out = ROOT / 'sources' / path
    out.parent.mkdir(exist_ok=True, parents=True)
    out.write_bytes(data)
    rows.append({'path': path, 'url': url, 'sha256': hashlib.sha256(data).hexdigest(), 'git_blob': blob, 'bytes': len(data), 'line_count': len(data.splitlines())})
save('sources.json', rows)
print('sources', len(rows))
