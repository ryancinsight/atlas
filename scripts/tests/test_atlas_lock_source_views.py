"""Real Git and Cargo coverage for immutable selected source views."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

from test_lockfile_regenerate import git

SCRIPT = Path(__file__).resolve().parent.parent / "atlas-lock-sweep.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("atlas_lock_source_views", SCRIPT)
sweep = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = sweep
SPEC.loader.exec_module(sweep)

A = "https://github.com/ryancinsight/Transaction-A.git"
B = "https://github.com/ryancinsight/transaction-b"
C = "https://github.com/ryancinsight/transaction-c"


def provider(repository: Path, name: str, version: str,
             dependencies: tuple[tuple[str, str, str], ...] = ()) -> str:
    (repository / "src").mkdir(exist_ok=True)
    (repository / "src/lib.rs").write_text("", encoding="utf-8")
    manifest = f'[package]\nname="{name}"\nversion="{version}"\nedition="2024"\n'
    if dependencies:
        manifest += "[dependencies]\n" + "".join(
            f'{package}={{git="{url}",version="{requirement}"}}\n'
            for package, url, requirement in dependencies
        )
    (repository / "Cargo.toml").write_text(manifest, encoding="utf-8")
    git(repository, "add", "Cargo.toml", "src/lib.rs")
    git(repository, "commit", "-qm", f"Record {version}")
    return git(repository, "rev-parse", "HEAD")


def transport(repositories: dict[str, Path]) -> dict[str, str]:
    return {
        **os.environ,
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": f"url.{repositories['a'].resolve().as_uri()}.insteadOf",
        "GIT_CONFIG_VALUE_0": A,
        "GIT_CONFIG_KEY_1": f"url.{repositories['b'].resolve().as_uri()}.insteadOf",
        "GIT_CONFIG_VALUE_1": B,
        "GIT_TERMINAL_PROMPT": "0",
    }


class SelectedSourceViewTests(unittest.TestCase):
    def test_competing_rewrites_cannot_defeat_selected_heads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="selected-source-views-") as directory:
            root = Path(directory)
            repos = {
                "a": root / "repos/transaction-a",
                "b": root / "repos/transaction-b",
                "c": root / "repos/transaction-c",
                "consumer": root / "repos/consumer",
            }
            for repository in repos.values():
                repository.mkdir(parents=True)
                git(repository, "init", "-q", "-b", "main")

            (root / ".gitmodules").write_text(
                "".join(
                    f'[submodule "repos/{name}"]\npath = repos/{name}\nurl = {url}\n'
                    for name, url in (
                        ("transaction-a", A), ("transaction-b", B),
                        ("transaction-c", C), ("consumer", A + "-consumer"),
                    )
                ),
                encoding="utf-8",
            )
            provider(repos["b"], "transaction-b", "0.1.0")
            provider(repos["a"], "transaction-a", "0.1.0",
                     (("transaction-b", B, "=0.1.0"),))
            (repos["consumer"] / "src").mkdir()
            (repos["consumer"] / "src/lib.rs").write_text("", encoding="utf-8")
            (repos["consumer"] / "Cargo.toml").write_text(
                '[package]\nname="consumer"\nversion="0.1.0"\nedition="2024"\n'
                f'[dependencies]\ntransaction-a={{git="{A}"}}\n'
                f'transaction-b={{git="{B}"}}\n',
                encoding="utf-8",
            )
            generated = sweep.lockfile.run_outside_the_overlay(
                ["--config", "net.git-fetch-with-cli=true", "generate-lockfile"],
                repos["consumer"] / "Cargo.toml", env=transport(repos), deadline=60,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)
            git(repos["consumer"], "add", "Cargo.toml", "Cargo.lock", "src/lib.rs")
            git(repos["consumer"], "commit", "-qm", "Record old graph")

            selected = {
                "transaction-c": provider(repos["c"], "transaction-c", "0.1.0"),
                "transaction-b": provider(repos["b"], "transaction-b", "0.2.0"),
            }
            selected["transaction-a"] = provider(
                repos["a"], "transaction-a", "0.2.0",
                (("transaction-b", B, "=0.2.0"), ("transaction-c", C, "=0.1.0")),
            )
            provider(repos["c"], "transaction-c", "0.2.0")
            provider(repos["b"], "transaction-b", "0.3.0")
            provider(repos["a"], "transaction-a", "0.3.0",
                     (("transaction-b", B, "=0.1.0"),))

            global_config = root / "global.gitconfig"
            conflict = f"url.{repos['c'].resolve().as_uri()}.insteadOf"
            git(root, "config", "--file", str(global_config), conflict, C)
            git(root, "config", "--file", str(global_config), "protocol.version", "2")
            environment = transport(repos)
            environment.update({
                "GIT_CONFIG_COUNT": "3",
                "GIT_CONFIG_KEY_2": conflict,
                "GIT_CONFIG_VALUE_2": C,
                "GIT_CONFIG_GLOBAL": str(global_config),
            })
            lock = (repos["consumer"] / "Cargo.lock").read_text(encoding="utf-8")
            plan = sweep.Plan(repos["consumer"], git(repos["consumer"], "rev-parse", "HEAD"),
                              sweep.stale_packages(lock, selected))
            parent_environment = dict(os.environ)

            with tempfile.TemporaryDirectory(prefix="source-config-", dir=root) as views:
                scoped, _ = sweep.selected_source_environment(
                    plan, selected, list(plan.stale), Path(views), environment)
                preserved = sweep.lockfile.run_bounded(
                    ["git", "config", "--get", "protocol.version"],
                    cwd=root, env=scoped, deadline=30,
                )
            self.assertEqual((preserved.returncode, preserved.stdout.strip()), (0, "2"))

            self.assertIsNone(sweep.resolve_lock(plan, selected, repos["consumer"], environment))
            packages = {package.provider: package for package in sweep.locked_packages(
                (repos["consumer"] / "Cargo.lock").read_text(encoding="utf-8"))}
            self.assertEqual(
                {(package.version, package.rev) for package in packages.values()},
                {("0.2.0", selected["transaction-a"]),
                 ("0.2.0", selected["transaction-b"]),
                 ("0.1.0", selected["transaction-c"])},
            )
            self.assertEqual(dict(os.environ), parent_environment)
            self.assertEqual(list((root / "repos").glob("lock-sources-*")), [])
