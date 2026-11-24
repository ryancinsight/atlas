"""Deterministic synthetic ref-lock reclamation interleaving."""
from pathlib import Path
import os
import queue
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
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
GIT = shutil.which('git')
if not GIT or not Path(GIT).is_absolute():
    raise RuntimeError('git must resolve to an absolute executable')


def dead_pid():
    # The hook probes the pid in its own namespace: Git Bash's on Windows.
    if os.name == 'nt':
        return subprocess.check_output([BASH, '-c', 'echo $$'], text=True).strip()
    dead = subprocess.Popen([sys.executable, '-c', 'pass']); dead.wait()
    return str(dead.pid)


def live_pid(test):
    holder = subprocess.Popen([BASH, '-c', 'echo $$; read -r _'], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, text=True)
    test.enterContext(holder)
    return holder.stdout.readline().strip()


class StaleReclaimTests(unittest.TestCase):
    def start(self, root, pause=True, cleanup=False, prelude=':'):
        source = HOOK.read_text()
        block = source[source.index('# One push of a ref at a time.'):source.index('prepared_stack_scripts=""')]
        cleanup_code = source[source.index('run_temps=()'):source.index('# Per-step wall-clock')]
        script = '\n'.join([
            'set -euo pipefail', 'exec 3>&1',
            f'repo_store={shlex.quote(root.as_posix())}',
            f'python_bin={shlex.quote(Path(sys.executable).as_posix())}',
            'gate_phase=push', 'run_temps=()', prelude,
            cleanup_code if cleanup else ':',
            'content_lines=("refs/heads/topic abc refs/heads/topic 000")',
            # Pause only owner observations; real filesystem/PID operations
            # and the production acquisition/recovery code remain unchanged.
            'cat() { command cat "$@"; if [[ "${1:-}" == "$push_lock/pid" ]]; then echo OBSERVED >&3; read -r resume; fi; }' if pause else ':',
            block, 'echo ACQUIRED', 'read -r release',
        ])
        return subprocess.Popen([BASH, '-c', script], stdin=subprocess.PIPE,
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
            key = subprocess.check_output([GIT, 'hash-object', '--stdin'], input=b'refs/heads/topic').decode().strip()[:16]
            lock = root / 'atlas-push-locks' / key
            lock.mkdir(parents=True)
            (lock / 'pid').write_text(dead_pid() + '\n')
            first = self.start(root)
            second = None
            try:
                self.assertEqual(self.line(first), 'OBSERVED')
                second = self.start(root)
                event = self.line(second)
                self.send(first, 'resume')
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
        key = subprocess.check_output([GIT, 'hash-object', '--stdin'], input=b'refs/heads/topic').decode().strip()[:16]
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

    @unittest.skipUnless(os.name == 'nt', 'identities tell Git Bash pids apart, which only Windows reuses')
    def test_git_bash_owner_is_judged_by_pid_and_identity(self):
        live, dead = live_pid(self), dead_pid()
        root, born = (subprocess.check_output([BASH, '-c', c, live], text=True).strip()
                      for c in ('cygpath -m /', 'stat -c %W /proc/$0'))
        same, later = f'{root}|{born}', f'{root}|{int(born) + 1}'
        kill_fails, stat_zero, stat_fails = 'kill() { return 1; }', 'stat() { echo 0; }', 'stat() { return 1; }'
        cases = [  # (pid, recorded identity, shell prelude, reclaimed)
            (dead, same, ':', True), (dead, None, ':', True),
            (live, same, ':', False), (live, later, ':', True),
            (live, None, ':', False), (live, '', ':', False), (live, 'garbage', ':', False),
            (live, later, stat_zero, False), (live, later, stat_fails, False),
            # `kill -0` fails while /proc/<pid> exists: only the identity decides.
            (live, same, kill_fails, False), (live, later, kill_fails, True),
            (dead, 'D:/other/|1', ':', False), (live, 'D:/other/|1', ':', False),
            ('9' * 10, same, ':', False)]
        for pid, recorded, prelude, reclaimed in cases:
            with self.subTest(pid=pid, recorded=recorded, prelude=prelude), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); lock = self.fixture_lock(root); lock.mkdir()
                (lock / 'pid').write_text(pid + '\n')
                if recorded is not None:
                    (lock / 'start').write_text(recorded + '\n')
                process = self.start(root, pause=False, cleanup=True, prelude=prelude)
                out, err = process.communicate('release\n', timeout=10)
                self.assertEqual(process.returncode == 0, reclaimed, err)
                self.assertEqual('ACQUIRED' in out, reclaimed)
                if not reclaimed:
                    self.assertEqual((lock / 'pid').read_text(), pid + '\n')

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
