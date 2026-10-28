"""Reproduce bounded source audits in a separate cache; never import frameworks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
REPOSITORY = Path(__file__).resolve().parents[3]
DATA = REPOSITORY / 'docs/parity/reference/closure'
FRAMEWORKS = {'numpy': 'numpy', 'jax': 'jax', 'torch': 'pytorch', 'tf': 'tensorflow'}

def source_files(source: Path, cached: dict | list, canonical: dict | list,
                 frozen_tree: dict, tree_identity: str, revision: str | None=None) -> None:
    """Bind scanned bytes to both versioned capture and exact source tree."""
    if cached != canonical:
        raise ValueError('Cached source manifest differs from canonical capture')
    if frozen_tree.get('sha') != tree_identity or frozen_tree.get('truncated') is not False:
        raise ValueError('Frozen source tree mismatch or truncation')
    rows = canonical if isinstance(canonical, list) else canonical['files']
    if isinstance(canonical, dict):
        if (canonical.get('revision') != revision or canonical.get('tree_truncated') is not False or
                canonical.get('selected_count') != len(rows) or canonical.get('verified_count') != len(rows)):
            raise ValueError('Source manifest revision or selection mismatch')
    blobs = {row['path']: row['sha'] for row in frozen_tree['tree'] if row['type'] == 'blob'}
    declared = {row['path'] for row in rows}
    if len(declared) != len(rows):
        raise ValueError('Duplicate source manifest path')
    actual = {path.relative_to(source).as_posix() for path in source.rglob('*') if path.is_file()}
    if actual != declared:
        raise ValueError('Source scan differs from declared paths (missing or undeclared files)')
    for row in rows:
        path = source / row['path']
        if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()):
            raise ValueError('Source path escapes captured tree')
        raw = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if (blob != row['git_blob_sha'] or blob != blobs.get(row['path']) or
                hashlib.sha256(raw).hexdigest() != row['sha256'] or row.get('bytes', len(raw)) != len(raw)):
            raise ValueError('Source bytes do not match frozen tree/capture: ' + row['path'])

def source_cache(work: Path, framework: str, manifest: str, source: Path,
                 tree_name: str, tree_identity: str, revision: str | None=None) -> None:
    canonical = DATA / framework / manifest
    index = json.loads((DATA / 'index.json').read_text(encoding='utf-8'))
    relative = canonical.relative_to(REPOSITORY / 'docs/parity').as_posix()
    expected = next(row['sha256'] for row in index['artifacts'] if row['path'] == relative)
    if hashlib.sha256(canonical.read_bytes()).hexdigest() != expected:
        raise ValueError('Canonical source manifest hash drift')
    source_files(source, json.loads((work / manifest).read_text(encoding='utf-8')),
                 json.loads(canonical.read_text(encoding='utf-8')),
                 json.loads((work / tree_name).read_text(encoding='utf-8')), tree_identity, revision)

def tree(cache: Path, destination: str, repository: str, revision: str, fetch: bool, legacy: Path | None=None) -> None:
    target = cache / destination
    if not target.exists() and legacy and legacy.exists():
        shutil.copyfile(legacy, target)
    if not target.exists():
        if not fetch:
            raise ValueError(f'Missing frozen tree input {target}; rerun with --fetch')
        url = f'https://api.github.com/repos/{repository}/git/trees/{revision}?recursive=1'
        with urllib.request.urlopen(url, timeout=30) as response:
            target.write_bytes(response.read())
    data = json.loads(target.read_text(encoding='utf-8'))
    if data.get('sha') != revision:
        raise ValueError(f'Frozen source tree mismatch: {target}: expected {revision}, got {data.get("sha")}')
    if data.get('truncated') is not False or not isinstance(data.get('tree'), list) or not data['tree']:
        raise ValueError(f'Truncated source tree: {target}')

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('framework', choices=FRAMEWORKS)
    parser.add_argument('--work', type=Path)
    parser.add_argument('--source-cache', type=Path, help='JAX exact-source cache; defaults to the initial extractor cache')
    parser.add_argument('--fetch', action='store_true', help='Allow missing frozen-source downloads')
    args = parser.parse_args()
    name = args.framework
    work = (args.work or Path(f'/tmp/atlas-parity-{name}-closure')).resolve()
    work.mkdir(parents=True, exist_ok=True)
    for path in (Path(__file__).parent / name).glob('*.py'):
        shutil.copyfile(path, work / path.name)
    for path in (DATA / name).glob('*.json'):
        if not (work / path.name).exists():
            shutil.copyfile(path, work / path.name)
    environment = dict(os.environ)
    environment['ATLAS_REFERENCE_REPOSITORY'] = str(REPOSITORY)
    environment['ATLAS_REFERENCE_INVENTORY'] = str(REPOSITORY / 'docs/parity/reference' / f'{FRAMEWORKS[name]}.json')
    if not args.fetch:
        environment['ATLAS_REFERENCE_OFFLINE'] = '1'

    def run(script: str, *arguments: str) -> None:
        subprocess.run([sys.executable, str(work / script), *arguments], cwd=work, env=environment, check=True, timeout=60)
    if name == 'numpy':
        shutil.copyfile(environment['ATLAS_REFERENCE_INVENTORY'], work / 'baseline-inventory.json')
        tree(work, 'source-tree.json', 'numpy/numpy', '838cf31b8096f12d7ca41ededf3ed60d94d37e3d', args.fetch)
        tree(work, 'source-tree-v2.5.0.json', 'numpy/numpy', '56e113f6f97c1b1c4e69a5353b4bdd4438d59dda', args.fetch)
        if args.fetch:
            run('fetch_sources.py')
        source_cache(work, 'numpy', 'sources.json', work / 'sources', 'source-tree.json',
                     '838cf31b8096f12d7ca41ededf3ed60d94d37e3d')
        for script in ('audit_numpy.py', 'constructor_contracts.py', 'metadata_contracts.py', 'metadata_witnesses.py', 'compare_source_trees.py', 'verify_closure.py'):
            run(script)
    elif name == 'jax':
        source = (args.source_cache or Path('/tmp/atlas-numpy-jax-parity/jax')).resolve()
        source.mkdir(parents=True, exist_ok=True)
        tree(source, 'tree.json', 'jax-ml/jax', 'bb9547a8148e50cab9c20f8521bf7af7c752b6f6', args.fetch)
        environment['ATLAS_REFERENCE_SOURCE_CACHE'] = str(source)
        arguments = ['--inventory', environment['ATLAS_REFERENCE_INVENTORY'], '--cache', str(source), '--out', str(work)]
        if args.fetch:
            arguments.append('--fetch')
        run('audit.py', *arguments)
        for script in ('ready.py', 'namespaces.py', 'constructors.py'):
            run(script)
    elif name == 'torch':
        run('run.py', *([] if args.fetch else ['--offline']))
    else:
        tree(work, 'tensorflow-tree.json', 'tensorflow/tensorflow', 'a481b10260dfdf833a1b16007eead49c1d7febf3', args.fetch, Path('/tmp/atlas-tensorflow-tree.json'))
        tree(work, 'keras-tree.json', 'keras-team/keras', '250b42181ce9f37df68319d8f4753ec89a349a43', args.fetch, Path('/tmp/atlas-keras-tree.json'))
        if args.fetch:
            run('fetch_sources.py')
            run('fetch_extra.py')
        for repository, revision in [('tensorflow', 'a481b10260dfdf833a1b16007eead49c1d7febf3'),
                                     ('keras', '250b42181ce9f37df68319d8f4753ec89a349a43')]:
            source_cache(work, 'tf', repository + '-source-manifest.json', work / 'source' / repository,
                         repository + '-tree.json', revision, revision)
        for script in ('analyze_relations.py', 'analyze_inheritance.py', 'build_contracts.py', 'machine_assertions.py', 'finalize_manifest.py'):
            run(script)
    print(json.dumps({'framework': FRAMEWORKS[name], 'work': str(work), 'framework_imports': False, 'runtime_parity_verified': False}))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
