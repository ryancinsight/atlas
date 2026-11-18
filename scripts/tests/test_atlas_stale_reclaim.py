"""Deterministic synthetic ref-lock reclamation interleaving."""
from pathlib import Path
import os
import queue
import shlex
import subprocess
import sys
import tempfile
import threading
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'git-hooks' / 'pre-push'

class StaleReclaimTests(unittest.TestCase):
    def start(self, root, pause=True, cleanup=False):
        source = HOOK.read_text()
        block = source[source.index('# One push of a ref at a time.'):source.index('prepared_stack_scripts=""')]
        cleanup_code = source[source.index('run_temps=()'):source.index('# Per-step wall-clock')]
        script = '\n'.join([
            'set -euo pipefail', 'exec 3>&1',
            f'repo_store={shlex.quote(str(root))}',
            f'python_bin={shlex.quote(sys.executable)}',
            'gate_phase=push', 'run_temps=()',
            cleanup_code if cleanup else ':',
            'content_lines=("refs/heads/topic abc refs/heads/topic 000")',
            # Pause only owner observations; real filesystem/PID operations
            # and the production acquisition/recovery code remain unchanged.
            'cat() { command cat "$@"; if [[ "${1:-}" == "$push_lock/pid" ]]; then echo OBSERVED >&3; read -r resume; fi; }' if pause else ':',
            block, 'echo ACQUIRED', 'read -r release',
        ])
        return subprocess.Popen(['bash', '-c', script], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def line(self, process):
        messages = queue.Queue()
        threading.Thread(target=lambda: messages.put(process.stdout.readline()), daemon=True).start()
        return messages.get(timeout=10).strip()

    def send(self, process, line):
        process.stdin.write(line + '\n'); process.stdin.flush()

    def test_delayed_stale_observer_cannot_remove_live_successor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = subprocess.check_output(['git', 'hash-object', '--stdin'], input=b'refs/heads/topic').decode().strip()[:16]
            lock = root / 'atlas-push-locks' / key
            lock.mkdir(parents=True)
            dead = subprocess.Popen(['true']); dead.wait()
            (lock / 'pid').write_text(str(dead.pid) + '\n')
            first = self.start(root)
            second = None
            try:
                self.assertEqual(self.line(first), 'OBSERVED')
                second = self.start(root)
                event = self.line(second)
                self.send(first, 'resume')
                if os.name == 'nt':
                    self.assertEqual(self.line(first), '')
                    self.assertEqual((lock / 'pid').read_text(), str(dead.pid) + '\n')
                    return
                self.assertEqual(self.line(first), 'ACQUIRED')
                winner_pid = (lock / 'pid').read_text()
                if event == 'OBSERVED':
                    self.send(second, 'resume')
                    event = self.line(second)
                self.assertNotEqual(event, 'ACQUIRED', 'delayed reclaimer entered concurrently')
                self.assertEqual((lock / 'pid').read_text(), winner_pid)
                self.assertIsNone(first.poll(), 'winner must still hold the gate')
            finally:
                for process in (first, second):
                    if process is not None:
                        if process.poll() is None:
                            process.communicate('release\n', timeout=10)
                        else:
                            process.communicate(timeout=10)

    def fixture_lock(self, root):
        key = subprocess.check_output(['git', 'hash-object', '--stdin'], input=b'refs/heads/topic').decode().strip()[:16]
        lock = root / 'atlas-push-locks' / key
        lock.parent.mkdir(parents=True)
        return lock

    def test_uncertain_owner_is_preserved(self):
        for owner in [None, '', 'not-a-pid', '0', '-1', '999999999999999999999999999999']:
            with self.subTest(owner=owner), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); lock = self.fixture_lock(root); lock.mkdir()
                if owner is not None:
                    (lock / 'pid').write_text(owner)
                process = self.start(root, pause=False, cleanup=True)
                out, err = process.communicate(timeout=10)
                self.assertNotEqual(process.returncode, 0, err)
                self.assertNotIn('ACQUIRED', out)
                self.assertTrue(lock.is_dir())
                self.assertEqual((lock / 'pid').read_text() if owner is not None else None, owner)

    def test_abandoned_guard_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); lock = self.fixture_lock(root)
            guard = lock.with_name(lock.name + '.reclaim'); guard.mkdir()
            process = self.start(root, pause=False, cleanup=True)
            out, err = process.communicate(timeout=10)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn('abandoned', err)
            self.assertNotIn('ACQUIRED', out)
            self.assertTrue(guard.is_dir())
            self.assertFalse(lock.exists())

    def test_normal_exit_releases_owned_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); lock = self.fixture_lock(root)
            process = self.start(root, pause=False, cleanup=True)
            self.assertEqual(self.line(process), 'ACQUIRED')
            self.assertTrue(lock.is_dir())
            process.communicate('release\n', timeout=10)
            self.assertEqual(process.returncode, 0)
            self.assertFalse(lock.exists())
            self.assertFalse(lock.with_name(lock.name + '.reclaim').exists())

    def test_exit_does_not_remove_different_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); lock = self.fixture_lock(root)
            process = self.start(root, pause=False, cleanup=True)
            self.assertEqual(self.line(process), 'ACQUIRED')
            # Synthetic successor identity: simulate delayed old cleanup only.
            (lock / 'pid').write_text('1\n')
            process.communicate('release\n', timeout=10)
            self.assertEqual(process.returncode, 0)
            self.assertEqual((lock / 'pid').read_text(), '1\n')

    def test_liveness_oracle_reclaims_only_esrch(self):
        source = HOOK.read_text()
        start = source.index('import os, sys\nif os.name == "nt":')
        code = source[start:source.index("' \"$push_holder\"", start)]
        # Fault-inject only the syscall result in an isolated interpreter.
        # This exercises production liveness classification without signaling
        # protected processes or needing a different host UID for EPERM.
        for exception, expected in [('ProcessLookupError', 0), ('PermissionError', 1), ('OSError', 1), (None, 1)]:
            with self.subTest(exception=exception):
                wrapper = 'import os, sys\nos.name = "posix"\nsys.argv = ["probe", "1"]\n'
                wrapper += ('def probe(*args):\n    raise ' + exception + '()\n') if exception else 'def probe(*args):\n    return None\n'
                wrapper += 'os.kill = probe\nexec(' + repr(code) + ')\n'
                result = subprocess.run([sys.executable, '-c', wrapper], capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, expected, result.stderr)

    def test_native_windows_does_not_probe_shell_pid(self):
        source = HOOK.read_text()
        start = source.index('import os, sys\nif os.name == "nt":')
        code = source[start:source.index("' \"$push_holder\"", start)]
        wrapper = ('import os, sys\nos.name = "nt"\nsys.argv = ["probe", "1"]\n'
                   'def forbidden_probe(*args):\n    raise AssertionError("native PID mismatch")\n'
                   'os.kill = forbidden_probe\nexec(' + repr(code) + ')\n')
        result = subprocess.run([sys.executable, '-c', wrapper], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, '')

if __name__ == '__main__':
    unittest.main()
