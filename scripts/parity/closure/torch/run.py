import os
'Reproduce the proposal from frozen primary inputs; no PyTorch import.'
import argparse, os, subprocess, sys
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--offline', action='store_true')
args = p.parse_args()
root = Path(__file__).resolve().parent
env = dict(os.environ)
if args.offline:
    env['ATLAS_REFERENCE_OFFLINE'] = '1'
for script in ('research.py', 'extra_sources.py', 'more_sources.py', 'derive.py', 'constructors.py', 'functional_aliases.py', 'verify.py'):
    subprocess.run([sys.executable, str(root / script)], check=True, env=env, cwd=root, timeout=60)
