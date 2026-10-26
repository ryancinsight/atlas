import os
import hashlib, json, urllib.request
from pathlib import Path
CACHE = Path(os.environ.get('ATLAS_REFERENCE_SOURCE_CACHE', '/tmp/atlas-numpy-jax-parity/jax'))
TREE = json.loads((CACHE / 'tree.json').read_text(encoding='utf-8'))
if TREE.get('sha') != 'bb9547a8148e50cab9c20f8521bf7af7c752b6f6' or TREE.get('truncated') is not False:
    raise ValueError('Frozen JAX source tree mismatch or truncation')
BLOBS = {x['path']: x for x in TREE['tree'] if x['type'] == 'blob'}
REV = 'dc4af684446e65ee98eee8090e1ff6f8211473fb'

def read(path):
    entry = BLOBS[path]
    file = CACHE / path
    if not file.exists():
        if os.environ.get('ATLAS_REFERENCE_OFFLINE') == '1':
            raise ValueError('Missing frozen offline source: ' + path)
        file.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen('https://raw.githubusercontent.com/jax-ml/jax/' + REV + '/' + path, timeout=30) as r:
            file.write_bytes(r.read())
    data = file.read_bytes()
    actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\x00' + data).hexdigest()
    if actual != entry['sha']:
        raise ValueError((path, 'blob-mismatch'))
    return data.decode()
if __name__ == '__main__':
    for path in ['docs/conf.py', 'jax/_src/numpy/array_creation.py', 'jax/_src/numpy/array_constructors.py', 'jax/_src/basearray.py', 'jax/_src/sharding_impls.py', 'jax/_src/stages.py', 'jax/_src/numpy/lax_numpy.py', 'jax/_src/numpy/util.py', 'jax/_src/dtypes.py', 'jax/_src/config.py', 'jax/_src/core.py', 'tests/lax_numpy_test.py', 'tests/lax_autodiff_test.py']:
        read(path)
        print(path, flush=True)
