"""Real Git coverage for bounded, complete CI member materialization."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

import process_tree
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/python-tests.yml"
DEPENDENCIES = ("atlas_ci_members.py", "atlas_git_process.py", "process_tree.py", "windows_process.py")
HOOK = r"""import json, os, pathlib, time
folder = pathlib.Path(os.environ['MATERIALIZATION_BARRIER'])
path = pathlib.Path.cwd()
(folder / str(os.getpid())).write_text(json.dumps({'pid': os.getpid(), 'path': str(path)}))
while not (folder / 'release').exists() and not (folder / path.name).exists():
    time.sleep(0.02)
if path.name == os.environ.get('MATERIALIZATION_FAIL', ''):
    raise SystemExit(42)
"""


class PythonCheckoutTests(unittest.TestCase):
    def git(self, root: Path, *args: str) -> str:
        result = subprocess.run(["git", "-C", str(root), *args], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def commit(self, root: Path, message: str) -> str:
        self.git(root, "-c", "user.name=Checkout fixture", "-c",
                 "user.email=checkout@example.invalid", "commit", "-qm", message)
        return self.git(root, "rev-parse", "HEAD")

    @contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve()
            self.env = dict(os.environ)
            self.env.update(GIT_ALLOW_PROTOCOL="file", GIT_TERMINAL_PROMPT="0")
            parent = folder / "atlas"
            parent.mkdir()
            self.git(parent, "init", "-qb", "main")
            (parent / "scripts").mkdir()
            for name in DEPENDENCIES:
                shutil.copyfile(ROOT / "scripts" / name, parent / "scripts" / name)
            members = []
            for index in range(5):
                provider = folder / f"provider{index}"
                provider.mkdir()
                self.git(provider, "init", "-qb", "main")
                (provider / "old.txt").write_text("recorded pin\n")
                self.git(provider, "add", "old.txt")
                self.git(provider, "update-index", "--add", "--cacheinfo",
                         "160000," + "1" * 40 + ",private/fixture")
                pin = self.commit(provider, "recorded provider")
                (provider / "new.txt").write_text("later default branch\n")
                self.git(provider, "add", "new.txt")
                tip = self.commit(provider, "later default")
                remote = folder / f"provider{index}.git"
                self.git(folder, "clone", "--bare", str(provider), str(remote))
                self.git(remote, "config", "uploadpack.allowFilter", "true")
                # Literal bracket/space paths and hierarchical admin names.
                path = f"repos/member {index}[x]"
                name = f"group/provider{index}"
                self.git(parent, "config", "-f", ".gitmodules", f"submodule.{name}.path", path)
                self.git(parent, "config", "-f", ".gitmodules", f"submodule.{name}.url", remote.as_uri())
                self.git(parent, "update-index", "--add", "--cacheinfo", f"160000,{pin},{path}")
                members.append((name, path, pin, tip))
            self.git(parent, "add", ".gitmodules", "scripts")
            self.commit(parent, "recorded Atlas inputs")
            yield folder, parent, members

    def command(self, tier="pytest-fast"):
        workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
        steps = workflow["jobs"][tier]["steps"]
        checkout = next(s for s in steps if s.get("name") == "Checkout")
        self.assertEqual(checkout["with"]["fetch-depth"], "0")
        self.assertEqual(checkout["with"]["submodules"], "false")
        setup = next(s for s in steps if s.get("name") == "Initialize direct Atlas members")
        return shlex.split(setup["run"])

    def barrier(self, folder: Path):
        barrier = folder / "barrier"
        barrier.mkdir()
        templates = folder / "templates"
        (templates / "hooks").mkdir(parents=True)
        script = folder / "checkout_barrier.py"
        script.write_text(HOOK)
        hook = templates / "hooks/post-checkout"
        hook.write_text("#!/bin/sh\nexec " + shlex.quote(Path(sys.executable).as_posix()) +
                        " " + shlex.quote(script.as_posix()) + "\n")
        hook.chmod(0o755)
        env = self.env.copy()
        count = int(env.get("GIT_CONFIG_COUNT", "0"))
        env.update({"GIT_CONFIG_COUNT": str(count + 1),
                    f"GIT_CONFIG_KEY_{count}": "init.templateDir",
                    f"GIT_CONFIG_VALUE_{count}": str(templates),
                    "MATERIALIZATION_BARRIER": str(barrier)})
        return barrier, env

    def entered(self, barrier: Path):
        return [json.loads(p.read_text()) for p in barrier.iterdir() if p.name.isdigit()]

    def wait_entered(self, barrier: Path, count: int):
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            rows = self.entered(barrier)
            if len(rows) >= count:
                return rows
            time.sleep(0.02)
        self.fail(f"Only {len(self.entered(barrier))} of {count} real checkout hooks entered")

    def assert_retired(self, rows):
        deadline = time.monotonic() + 8
        while True:
            live = []
            for row in rows:
                p = subprocess.run(["ps", "-p", str(row["pid"]), "-o", "stat="],
                                   capture_output=True, text=True)
                self.assertFalse(p.stderr.strip(), "Cannot verify owned child retirement: " + p.stderr)
                self.assertIn(p.returncode, (0, 1), "Unexpected child-liveness observation")
                if p.returncode == 0:
                    self.assertTrue(p.stdout.strip(), "Successful ps observation has no process status")
                else:
                    self.assertFalse(p.stdout.strip(), "Missing PID observation contains process output")
                if p.returncode == 0 and p.stdout.strip() and not p.stdout.strip().startswith("Z"):
                    live.append(row["pid"])
            if not live:
                return
            if time.monotonic() >= deadline:
                self.fail(f"Owned checkout hooks remain live: {live}")
            time.sleep(0.02)

    def test_both_tiers_keep_pins_history_and_lazy_blobs(self):
        for tier in ("pytest-fast", "pytest-slow"):
            with self.subTest(tier=tier), self.fixture() as (_, parent, members):
                p = subprocess.run(self.command(tier), cwd=parent, env=self.env,
                                   capture_output=True, text=True, timeout=30)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                self.assertEqual(len(json.loads(p.stdout)["members"]), 5)
                for _, path, pin, tip in members:
                    member = parent / path
                    self.assertEqual(self.git(member, "rev-parse", "HEAD"), pin)
                    self.assertNotEqual(pin, tip)
                    self.assertEqual(self.git(member, "rev-parse", "--is-shallow-repository"), "false")
                    self.assertEqual(self.git(member, "rev-parse", "origin/main"), tip)
                    self.assertEqual(self.git(member, "config", "--get", "remote.origin.promisor"), "true")
                    self.assertEqual(self.git(member, "config", "--get", "remote.origin.partialclonefilter"), "blob:none")
                    self.assertFalse((member / "new.txt").exists())
                    future_blob = self.git(member, "rev-parse", tip + ":new.txt")
                    local_objects = self.git(member, "cat-file", "--batch-all-objects",
                                             "--batch-check=%(objectname)").splitlines()
                    self.assertNotIn(future_blob, local_objects)
                    self.assertEqual(self.git(member, "show", tip + ":new.txt"), "later default branch")
                    self.assertIn(future_blob, self.git(member, "cat-file", "--batch-all-objects",
                                                       "--batch-check=%(objectname)").splitlines())
                    self.assertEqual((member / "old.txt").read_text(), "recorded pin\n")
                    self.assertFalse((member / "private/fixture/.git").exists())

    def test_checkout_phases_overlap_with_four_workers_and_stable_root(self):
        with self.fixture() as (folder, parent, _):
            barrier, env = self.barrier(folder)
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(subprocess.run, self.command(), cwd=parent, env=env,
                                         capture_output=True, timeout=30)
                try:
                    rows = self.wait_entered(barrier, 4)
                    self.assertEqual(len(rows), 4)
                    state = [(parent / ".git" / name).read_bytes() for name in ["config", "index", "HEAD"]]
                    time.sleep(0.1)
                    self.assertEqual(len(self.entered(barrier)), 4)
                finally:
                    (barrier / "release").touch()
                result = future.result(timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(len(self.entered(barrier)), 5)
            self.assertEqual(state, [(parent / ".git" / name).read_bytes() for name in ["config", "index", "HEAD"]])
            intervals = json.loads(result.stdout)["members"]
            events = sorted([(r["started_ns"], 1) for r in intervals] +
                            [(r["finished_ns"], -1) for r in intervals])
            active = peak = 0
            for _, change in events:
                active += change
                peak = max(peak, active)
            self.assertEqual(peak, 4)

    def test_clone_jobs_control_has_serial_checkout(self):
        with self.fixture() as (folder, parent, _):
            barrier, env = self.barrier(folder)
            command = ["git", "--literal-pathspecs", "submodule", "update", "--init",
                       "--force", "--no-recommend-shallow", "--filter=blob:none", "--jobs=4"]
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(process_tree.run, command, cwd=parent, env=env, timeout=30)
                try:
                    self.wait_entered(barrier, 1)
                    time.sleep(0.15)
                    self.assertEqual(len(self.entered(barrier)), 1)
                finally:
                    (barrier / "release").touch()
                result = future.result(timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(len(self.entered(barrier)), 5)

    @unittest.skipUnless(os.name == "posix", "POSIX child-liveness regression")
    def test_failure_stops_queued_members_and_retires_started_children(self):
        with self.fixture() as (folder, parent, members):
            barrier, env = self.barrier(folder)
            env["MATERIALIZATION_FAIL"] = Path(members[0][1]).name
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(subprocess.run, self.command(), cwd=parent, env=env,
                                         capture_output=True, timeout=30)
                try:
                    rows = self.wait_entered(barrier, 4)
                    (barrier / Path(members[0][1]).name).touch()
                    result = future.result(timeout=12)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b"failed", result.stderr)
                    self.assertEqual(len(self.entered(barrier)), 4)
                    self.assert_retired(rows)
                finally:
                    (barrier / "release").touch()

    def test_serial_registration_failure_prevents_every_worker(self):
        with self.fixture() as (_, parent, members):
            self.git(parent, "config", "-f", ".gitmodules", "--unset",
                     "submodule." + members[-1][0] + ".url")
            self.git(parent, "add", ".gitmodules")
            self.commit(parent, "missing final member URL")
            p = subprocess.run(self.command(), cwd=parent, env=self.env,
                               capture_output=True, text=True, timeout=20)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("No url found", p.stderr)
            self.git(parent, "config", "--get", "submodule." + members[0][0] + ".url")
            self.assertFalse((parent / ".git/modules").exists())
            self.assertFalse(any((parent / path / ".git").exists() for _, path, _, _ in members))

    def test_unavailable_recorded_pin_and_clone_source_fail_closed(self):
        for problem in ("pin", "remote"):
            with self.subTest(problem=problem), self.fixture() as (folder, parent, members):
                name, path, _, _ = members[0]
                if problem == "pin":
                    self.git(parent, "update-index", "--cacheinfo", "160000," + "f" * 40 + "," + path)
                else:
                    self.git(parent, "config", "-f", ".gitmodules", "submodule." + name + ".url",
                             (folder / "unavailable.git").as_uri())
                    self.git(parent, "add", ".gitmodules")
                self.commit(parent, "unavailable member " + problem)
                p = subprocess.run(self.command(), cwd=parent, env=self.env,
                                   capture_output=True, text=True, timeout=20)
                self.assertNotEqual(p.returncode, 0)
                self.assertIn("member " + path + " failed", p.stderr)

    @unittest.skipUnless(os.name == "posix", "POSIX child-liveness regression")
    def test_post_update_pin_mismatch_retires_workers_and_keeps_queue_stopped(self):
        with self.fixture() as (folder, parent, members):
            barrier, env = self.barrier(folder)
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(subprocess.run, self.command(), cwd=parent, env=env,
                                         capture_output=True, timeout=30)
                try:
                    rows = self.wait_entered(barrier, 4)
                    _, path, _, tip = members[0]
                    self.git(parent / path, "update-ref", "HEAD", tip)
                    (barrier / Path(path).name).touch()
                    result = future.result(timeout=12)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b"pin mismatch", result.stderr)
                    self.assertEqual(len(self.entered(barrier)), 4)
                    self.assert_retired(rows)
                finally:
                    (barrier / "release").touch()

    @unittest.skipUnless(os.name == "posix", "POSIX deadline/liveness regression")
    def test_pool_deadline_retires_all_owned_checkout_children(self):
        with self.fixture() as (folder, parent, _):
            barrier, env = self.barrier(folder)
            command = [sys.executable, "-c", "import sys; sys.path.insert(0, 'scripts'); "
                       "from pathlib import Path; from atlas_ci_members import materialize; "
                       "materialize(Path.cwd(), 4, timeout=8)"]
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(subprocess.run, command, cwd=parent, env=env,
                                         capture_output=True, timeout=25)
                try:
                    rows = self.wait_entered(barrier, 4)
                    result = future.result(timeout=20)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b"timed out after 8s", result.stderr)
                    self.assertEqual(len(self.entered(barrier)), 4)
                    self.assert_retired(rows)
                finally:
                    (barrier / "release").touch()

    @unittest.skipUnless(os.name == "posix", "POSIX SIGINT regression")
    def test_interrupt_retires_all_owned_checkout_children(self):
        with self.fixture() as (folder, parent, _):
            barrier, env = self.barrier(folder)
            p = subprocess.Popen(self.command(), cwd=parent, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                rows = self.wait_entered(barrier, 4)
                p.send_signal(signal.SIGINT)
                stdout, stderr = p.communicate(timeout=12)
                self.assertNotEqual(p.returncode, 0, stdout + stderr)
                self.assert_retired(rows)
            finally:
                (barrier / "release").touch()
                if p.poll() is None:
                    p.kill()
                p.wait(timeout=5)

    def test_index_drift_and_existing_worktrees_fail_before_materialization(self):
        for problem in ("index", "existing", "admin_existing", "working_mapping",
                        "missing", "duplicate", "admin_overlap"):
            with self.subTest(problem=problem), self.fixture() as (_, parent, members):
                if problem == "index":
                    _, path, _, tip = members[0]
                    self.git(parent, "update-index", "--cacheinfo", f"160000,{tip},{path}")
                elif problem == "existing":
                    destination = parent / members[0][1]
                    destination.mkdir(parents=True)
                    (destination / "owner-work").write_text("preserve")
                elif problem == "admin_existing":
                    destination = parent / ".git/modules" / members[0][0]
                    destination.mkdir(parents=True)
                    (destination / "owner-work").write_text("preserve")
                elif problem == "working_mapping":
                    self.git(parent, "config", "-f", ".gitmodules",
                             "submodule." + members[0][0] + ".path", "different")
                else:
                    if problem == "missing":
                        self.git(parent, "config", "-f", ".gitmodules", "--remove-section", "submodule." + members[0][0])
                    elif problem == "duplicate":
                        self.git(parent, "config", "-f", ".gitmodules", "submodule." + members[1][0] + ".path", members[0][1])
                    else:
                        self.git(parent, "config", "-f", ".gitmodules", "--rename-section", "submodule." + members[0][0], "submodule.overlap")
                        self.git(parent, "config", "-f", ".gitmodules", "--rename-section", "submodule." + members[1][0], "submodule.overlap/child")
                    self.git(parent, "add", ".gitmodules")
                    self.commit(parent, "invalid mapping")
                p = subprocess.run(self.command(), cwd=parent, env=self.env, capture_output=True, text=True, timeout=20)
                self.assertNotEqual(p.returncode, 0)
                expected = {"index": "index gitlinks", "existing": "not fresh",
                            "admin_existing": "already exists", "working_mapping": ".gitmodules",
                            "missing": "incomplete", "duplicate": "duplicate",
                            "admin_overlap": "overlap"}[problem]
                self.assertIn(expected, p.stderr)
                self.assertFalse((parent / members[-1][1] / ".git").exists())
                if problem == "existing":
                    self.assertEqual((parent / members[0][1] / "owner-work").read_text(), "preserve")
                elif problem == "admin_existing":
                    self.assertEqual((parent / ".git/modules" / members[0][0] / "owner-work").read_text(), "preserve")

    @unittest.skipUnless(os.name == "posix", "POSIX symlink containment")
    def test_escaping_worktree_or_admin_symlinks_are_rejected(self):
        for target in ("worktree", "admin", "internal_worktree", "internal_admin"):
            with self.subTest(target=target), self.fixture() as (folder, parent, members):
                outside = (parent if target.startswith("internal") else folder) / "outside"
                outside.mkdir()
                if target.endswith("worktree"):
                    (parent / "repos").symlink_to(outside, target_is_directory=True)
                else:
                    (parent / ".git/modules").symlink_to(outside, target_is_directory=True)
                p = subprocess.run(self.command(), cwd=parent, env=self.env, capture_output=True, text=True, timeout=20)
                self.assertNotEqual(p.returncode, 0)
                self.assertTrue("escapes" in p.stderr or "redirected" in p.stderr, p.stderr)
                self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipUnless(os.name == "posix", "POSIX child-liveness regression")
    def test_root_state_changes_fail_closed_and_retire_workers(self):
        for name in ("config", "index", "HEAD", ".gitmodules"):
            with self.subTest(name=name), self.fixture() as (folder, parent, _):
                barrier, env = self.barrier(folder)
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(subprocess.run, self.command(), cwd=parent,
                                             env=env, capture_output=True, timeout=30)
                    try:
                        rows = self.wait_entered(barrier, 4)
                        changed = parent / ".gitmodules" if name == ".gitmodules" else parent / ".git" / name
                        with changed.open("ab") as stream:
                            stream.write(b"\n")
                        result = future.result(timeout=12)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(b"root config/index/HEAD changed", result.stderr)
                        self.assert_retired(rows)
                    finally:
                        (barrier / "release").touch()

    @unittest.skipUnless(os.name == "posix", "POSIX administrative symlink regression")
    def test_queued_destination_is_rechecked_before_forced_checkout(self):
        for kind in ("owner_work", "admin_alias"):
            with self.subTest(kind=kind), self.fixture() as (folder, parent, members):
                barrier, env = self.barrier(folder)
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(subprocess.run, self.command(), cwd=parent,
                                             env=env, capture_output=True, timeout=30)
                    try:
                        rows = self.wait_entered(barrier, 4)
                        name, path, _, _ = members[-1]
                        if kind == "owner_work":
                            destination = parent / path
                            destination.mkdir(parents=True, exist_ok=True)
                            (destination / "owner-work").write_text("preserve")
                        else:
                            destination = parent / ".git/modules" / name
                            destination.symlink_to(parent / ".git/modules" / members[0][0],
                                                   target_is_directory=True)
                        (barrier / "release").touch()
                        result = future.result(timeout=12)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(b"not fresh" if kind == "owner_work" else b"redirected", result.stderr)
                        self.assert_retired(rows)
                        if kind == "owner_work":
                            self.assertEqual((destination / "owner-work").read_text(), "preserve")
                    finally:
                        (barrier / "release").touch()


if __name__ == "__main__":
    unittest.main()
