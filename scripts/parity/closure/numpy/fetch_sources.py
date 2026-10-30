"""Fetch immutable NumPy source for static analysis; never imports NumPy."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request
ROOT = Path(__file__).resolve().parent
REVISION = 'a3d0ef1df045b858e68115001fdabc930bb3b68c'
CACHE = Path('/tmp/atlas-numpy-jax-parity/numpy')

def fetch(entry):
    target = ROOT / 'sources' / entry['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    cached = CACHE / entry['path']
    if not target.exists():
        if cached.exists():
            target.write_bytes(cached.read_bytes())
        else:
            url = f"https://raw.githubusercontent.com/numpy/numpy/{REVISION}/{entry['path']}"
            with urllib.request.urlopen(url, timeout=30) as response:
                target.write_bytes(response.read())
    data = target.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\x00' + data).hexdigest()
    if blob != entry['sha']:
        raise ValueError(f"source hash mismatch: {entry['path']}")
    return {'path': entry['path'], 'git_blob_sha': blob, 'sha256': hashlib.sha256(data).hexdigest(), 'url': f"https://github.com/numpy/numpy/blob/{REVISION}/{entry['path']}"}
if __name__ == '__main__':
    selected = json.loads((ROOT / 'requested-sources.json').read_text(encoding='utf-8'))
    baseline = json.loads((ROOT / 'baseline-inventory.json').read_text(encoding='utf-8'))
    tree = {entry['path']: entry for entry in json.loads((ROOT / 'source-tree.json').read_text(encoding='utf-8'))['tree']}
    selected = {entry['path']: entry for entry in selected}
    selected.update({entry['path']: tree[entry['path']] for entry in baseline['sources']})
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(fetch, selected.values()))
    (ROOT / 'sources.json').write_text(json.dumps(sorted(records, key=lambda x: x['path']), indent=2) + '\n', encoding='utf-8')
    print(f'{len(records)} source files hash-verified')
