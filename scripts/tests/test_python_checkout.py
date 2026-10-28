"""The Python tiers materialize committed member pins without history payloads."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/python-tests.yml"


class PythonCheckoutTests(unittest.TestCase):
    def git(self, root: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def commit(self, root: Path, message: str) -> str:
        self.git(root, "-c", "user.name=Checkout fixture", "-c",
                 "user.email=checkout@example.invalid", "commit", "-qm", message)
        return self.git(root, "rev-parse", "HEAD")

    def test_both_tiers_keep_pins_history_and_lazy_blobs(self):
        workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
        for tier in ("pytest-fast", "pytest-slow"):
            with self.subTest(tier=tier), tempfile.TemporaryDirectory() as temp:
                self.env = dict(os.environ)
                # A local fixture may fetch only its own file transport; it
                # cannot prompt for credentials or reach a network provider.
                self.env.update(GIT_ALLOW_PROTOCOL="file", GIT_TERMINAL_PROMPT="0")
                folder = Path(temp)
                provider = folder / "provider"
                provider.mkdir()
                self.git(provider, "init", "-qb", "main")
                (provider / "old.txt").write_text("recorded pin\n")
                self.git(provider, "add", "old.txt")
                # A nested fixture gitlink has no clone URL. Direct Atlas
                # members suffice for these tiers and must not recurse here.
                self.git(provider, "update-index", "--add", "--cacheinfo",
                         "160000," + "1" * 40 + ",private/fixture")
                pin = self.commit(provider, "recorded provider")
                (provider / "new.txt").write_text("later default branch\n")
                self.git(provider, "add", "new.txt")
                tip = self.commit(provider, "later provider")
                remote = folder / "provider.git"
                self.git(folder, "clone", "--bare", str(provider), str(remote))
                self.git(remote, "config", "uploadpack.allowFilter", "true")

                parent = folder / "atlas"
                parent.mkdir()
                self.git(parent, "init", "-qb", "main")
                self.git(parent, "config", "-f", ".gitmodules",
                         "submodule.provider.path", "repos/provider")
                self.git(parent, "config", "-f", ".gitmodules",
                         "submodule.provider.url", remote.as_uri())
                self.git(parent, "add", ".gitmodules")
                self.git(parent, "update-index", "--add", "--cacheinfo",
                         "160000," + pin + ",repos/provider")
                self.commit(parent, "recorded Atlas pin")

                steps = workflow["jobs"][tier]["steps"]
                checkout = next(s for s in steps if s.get("name") == "Checkout")
                self.assertEqual(checkout["with"]["fetch-depth"], "0")
                self.assertEqual(checkout["with"]["submodules"], "false")
                setup = next((s for s in steps if s.get("name") ==
                              "Initialize direct Atlas members"), None)
                self.assertIsNotNone(setup, "recorded sources need explicit initialization")
                command = shlex.split(setup["run"])
                result = subprocess.run(command, cwd=parent, env=self.env,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                member = parent / "repos/provider"
                self.assertEqual(self.git(member, "rev-parse", "HEAD"), pin)
                self.assertNotEqual(pin, tip)
                self.assertEqual(self.git(member, "rev-parse", "--is-shallow-repository"),
                                 "false")
                self.assertEqual(self.git(member, "rev-parse", "origin/main"), tip)
                self.assertEqual(self.git(member, "config", "--get",
                                          "remote.origin.promisor"), "true")
                self.assertEqual(self.git(member, "config", "--get",
                                          "remote.origin.partialclonefilter"), "blob:none")
                self.assertFalse((member / "new.txt").exists())
                self.assertEqual(self.git(member, "show", tip + ":new.txt"),
                                 "later default branch")
                self.assertEqual((member / "old.txt").read_text(), "recorded pin\n")
                self.assertFalse((member / "private/fixture/.git").exists())


if __name__ == "__main__":
    unittest.main()
