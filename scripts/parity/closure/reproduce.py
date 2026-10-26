"""Reproduce bounded source audits in a separate cache; never import frameworks."""
import argparse
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
    work = args.work or Path(f'/tmp/atlas-parity-{name}-closure')
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
        for script in ('audit_numpy.py', 'constructor_contracts.py', 'metadata_contracts.py', 'metadata_witnesses.py', 'compare_source_trees.py', 'verify_closure.py'):
            run(script)
    elif name == 'jax':
        source = args.source_cache or Path('/tmp/atlas-numpy-jax-parity/jax')
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
        for script in ('analyze_relations.py', 'analyze_inheritance.py', 'build_contracts.py', 'machine_assertions.py', 'finalize_manifest.py'):
            run(script)
    print(json.dumps({'framework': FRAMEWORKS[name], 'work': str(work), 'framework_imports': False, 'runtime_parity_verified': False}))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
