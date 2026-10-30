"""Real CLI coverage for the locked SemVer evidence contract."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "atlas_semver_locked.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("atlas_semver_locked", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class NativeContract(unittest.TestCase):
    def command(self, argv, cwd):
        return subprocess.run(argv, cwd=cwd, check=True, capture_output=True,
                              text=True, timeout=120)

    def commit(self, repo, message, empty=False):
        self.command(["git", "add", "Cargo.toml", "Cargo.lock", "src/lib.rs"], repo)
        argv = ["git", "commit", "-m", message]
        if empty:
            argv.append("--allow-empty")
        self.command(argv, repo)
        return self.command(["git", "rev-parse", "HEAD"], repo).stdout.strip()

    def run_contract(self, repo, base, head, report, change="patch"):
        target = next(line[6:] for line in self.command(["rustc", "+1.97.0", "-vV"], repo).stdout.splitlines()
                      if line.startswith("host: "))
        args = argparse.Namespace(
            repo=repo, base=base, head=head, manifest_path="Cargo.toml",
            packages=["contract"], toolchain="1.97.0", change_class=change,
            feature_policy="all", features=[], target=target,
            report=report,
        )
        code = MODULE.compare(args)
        return code, json.loads(report.read_text(encoding="utf-8"))

    def test_native_pass_deny_and_manifest_permission_are_distinct(self):
        with tempfile.TemporaryDirectory(prefix="semver-native-") as directory:
            repo = Path(directory)
            (repo / "src").mkdir()
            (repo / "Cargo.toml").write_text(
                '[package]\nname="contract"\nversion="0.1.0"\nedition="2024"\n', encoding="utf-8")
            (repo / "src/lib.rs").write_text("pub fn retained() {}\npub fn removed() {}\n", encoding="utf-8")
            for argv in (["git", "init", "-b", "main"],
                         ["git", "config", "user.email", "test@example.invalid"],
                         ["git", "config", "user.name", "Contract test"],
                         ["cargo", "generate-lockfile"]):
                self.command(argv, repo)
            base = self.commit(repo, "base")
            head = self.commit(repo, "unchanged", empty=True)
            code, report = self.run_contract(repo, base, head, repo / "pass.json")
            self.assertEqual((code, report["packages"][0]["native"]["status"]), (0, "pass"))
            code, report = self.run_contract(repo, base, head, repo / "major.json", "major")
            self.assertEqual(report["packages"][0]["native"]["status"], "pass")
            self.assertEqual((code, report["packages"][0]["manifest_error"]),
                             (101, "declared change class exceeds manifest boundary"))
            (repo / "src/lib.rs").write_text("pub fn retained() {}\n", encoding="utf-8")
            head = self.commit(repo, "remove API")
            code, report = self.run_contract(repo, base, head, repo / "deny.json")
            native = report["packages"][0]["native"]
            self.assertEqual((code, native["exit_code"], native["status"]),
                             (100, 100, "deny_findings"))
            self.assertIn("--baseline-rev", native["command"])
            self.assertEqual(report["configuration"]["feature_policy"], "all")

    def test_timeout_retires_a_real_descendant(self):
        command = [sys.executable, "-c", (
            "import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);"
            "print(p.pid,flush=True);time.sleep(30)"
        )]
        record = MODULE.attempt(command, Path.cwd(), dict(os.environ), timeout=0.2)
        self.assertEqual(record["status"], "timeout")
        pid = int(record["diagnostics"].strip())
        time.sleep(0.1)
        with self.assertRaises(OSError):
            os.kill(pid, 0)


if __name__ == "__main__":
    unittest.main()
