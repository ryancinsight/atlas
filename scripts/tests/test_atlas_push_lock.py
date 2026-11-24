"""Exercise the owned hook's ref-lock block with real filesystem operations."""
from __future__ import annotations

from pathlib import Path
import shlex
import os
import shutil
import queue
import threading
import subprocess
import sys
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'git-hooks' / 'pre-push'

# Native Windows CreateProcess can choose System32's WSL bash even when
# shutil.which found Git Bash. Never pass a bare executable name to it.
_bash = os.environ.get('ATLAS_TEST_BASH')
if not _bash and os.name != 'nt':
    _bash = shutil.which('bash')
if not _bash or not Path(_bash).is_absolute() or not Path(_bash).is_file():
    raise RuntimeError('ATLAS_TEST_BASH must name an existing absolute Git Bash executable on Windows')
BASH = str(Path(_bash).resolve())
# Git Bash also records the owner's identity beside the pid.
LOCK_ENTRIES = {'pid', 'start'} if os.name == 'nt' else {'pid'}


class PushLockPortabilityTests(unittest.TestCase):
    def run_claim(self, root: Path, python: str = sys.executable, hold: bool = False, no_gnu_mv: bool = False):
        # Bash/MSYS $$ is not necessarily native Python Popen.pid.
        # Record it independently before the production block writes its lock.
        with tempfile.NamedTemporaryFile(dir=root) as witness:
            shell_pid_path = Path(witness.name)
        python_path = Path(python).as_posix() if python else ""
        source = HOOK.read_text()
        block = source[source.index('# One push of a ref at a time.'):source.index('prepared_stack_scripts=""')]
        script = '\n'.join([
            'set -euo pipefail',
            f"printf '%s\\n' \"$$\" > {shlex.quote(shell_pid_path.as_posix())}",
            f'repo_store={shlex.quote(root.as_posix())}',
            f'python_bin={shlex.quote(python_path)}',
            'gate_phase=push',
            'run_temps=()',
            'content_lines=("refs/heads/topic abc refs/heads/topic 000")',
            block,
            'echo ACQUIRED',
            'read -r release' if hold else ':',
        ])
        environment = None
        if no_gnu_mv:
            binary = root / 'bin'
            binary.mkdir()
            shim = binary / 'mv'
            real_mv = shutil.which('mv')
            self.assertIsNotNone(real_mv)
            shim.write_text('#!/bin/sh\nfor arg do [ "$arg" != "-T" ] || exit 64; done\n'
                            + f'exec {shlex.quote(Path(real_mv).as_posix())} "$@"\n', newline="\n")
            shim.chmod(0o755)
            environment = dict(os.environ)
            environment['PATH'] = str(binary) + os.pathsep + environment.get('PATH', '')
        process = subprocess.Popen([BASH, '-c', script], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                env=environment)
        process.shell_pid_path = shell_pid_path
        return process

    def announced(self, process):
        messages = queue.Queue()
        threading.Thread(target=lambda: messages.put(process.stdout.readline()), daemon=True).start()
        return messages.get(timeout=10).strip()

    def test_native_atomic_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            process = self.run_claim(root)
            out, err = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, err)
            self.assertEqual(out.strip(), 'ACQUIRED')
            locks = list((root / 'atlas-push-locks').iterdir())
            self.assertEqual(len(locks), 1)
            self.assertEqual((locks[0] / 'pid').read_text().strip(), process.shell_pid_path.read_text().strip())
            self.assertEqual({entry.name for entry in locks[0].iterdir()}, LOCK_ENTRIES)

    def test_publication_does_not_require_gnu_mv(self):
        with tempfile.TemporaryDirectory() as directory:
            process = self.run_claim(Path(directory), no_gnu_mv=True)
            out, err = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, err)
            self.assertEqual(out.strip(), 'ACQUIRED')

    def test_export_claim_does_not_require_gnu_mv(self):
        source = HOOK.read_text()
        start = source.index('claim_gate_root() {')
        block = source[start:source.index('if ! claim_gate_root;', start)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Any mv call fails: atomic publication must not depend on GNU -T
            # or fall back to mv's directory-nesting semantics.
            script = '\n'.join([
                'set -euo pipefail',
                f'gate_root={shlex.quote((root / "export").as_posix())}',
                f'python_bin={shlex.quote(Path(sys.executable).as_posix())}',
                'run_temps=()',
                'mv() { return 64; }',
                block,
                'claim_gate_root',
                'if claim_gate_root; then exit 65; fi',
                'test "$(cat "$gate_root.lock/pid")" = "$$"',
            ])
            result = subprocess.run([BASH, '-c', script], text=True,
                                    capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            lock = root / 'export.lock'
            self.assertEqual(list(lock.iterdir()), [lock / 'pid'])

    def test_live_incumbent_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            incumbent = self.run_claim(root, hold=True)
            try:
                self.assertEqual(self.announced(incumbent), 'ACQUIRED')
                locks = list((root / 'atlas-push-locks').iterdir())
                before = (locks[0] / 'pid').read_bytes()
                contender = self.run_claim(root)
                out, err = contender.communicate(timeout=10)
                self.assertNotEqual(contender.returncode, 0)
                self.assertIn('another push', err)
                self.assertNotIn('ACQUIRED', out)
                self.assertEqual((locks[0] / 'pid').read_bytes(), before)
                self.assertEqual({entry.name for entry in locks[0].iterdir()}, LOCK_ENTRIES)
            finally:
                incumbent.communicate('release\n', timeout=10)

    def test_two_contenders_publish_only_one_incumbent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contenders = [self.run_claim(root, hold=True) for _ in range(2)]
            try:
                messages = [self.announced(process) for process in contenders]
                self.assertEqual(messages.count('ACQUIRED'), 1)
                locks = list((root / 'atlas-push-locks').iterdir())
                self.assertEqual(len(locks), 1)
                winner = contenders[messages.index('ACQUIRED')]
                self.assertEqual((locks[0] / 'pid').read_text().strip(), winner.shell_pid_path.read_text().strip())
                loser = contenders[1 - messages.index('ACQUIRED')]
                _, err = loser.communicate(timeout=10)
                self.assertNotEqual(loser.returncode, 0)
                self.assertIn('another push', err)
                self.assertEqual({entry.name for entry in locks[0].iterdir()}, LOCK_ENTRIES)
            finally:
                for process in contenders:
                    if process.poll() is None:
                        process.communicate('release\n', timeout=10)

    def test_missing_python_fails_closed_without_claiming_contention(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            process = self.run_claim(root, python='')
            out, err = process.communicate(timeout=10)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn('no python interpreter found', err)
            self.assertNotIn('another push', err)
            self.assertNotIn('ACQUIRED', out)
            self.assertFalse((root / 'atlas-push-locks').exists())


if __name__ == '__main__':
    unittest.main()
