"""Real Git comparison history stays separate from publication identity decisions."""
from pathlib import Path

import os
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]

def run(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True,
                          timeout=60, env={**os.environ, "CARGO_NET_OFFLINE": "true"}).stdout.strip()


HISTORY = {"b553c42da72dcdeb2bb2644c60759dc465fb329a": (".github/workflows/crates-publish.yml",),
           "6d6e6935062ea5d9c69bd819e6f8c2c4fc4918ae": (".github/actions/crate-release-identity/action.yml",
                                                       ".github/actions/crate-release-identity/release_identity.py")}


def history_store(root, store):
    """Fetch only immutable comparison commits; never deepen the checkout itself."""
    run(["git", "init", "--quiet", "--bare", str(store)], root)
    # A blobless checkout can have the commit without being able to serve its
    # blobs. Read the immutable bytes from origin into this isolated store.
    source = run(["git", "remote", "get-url", "origin"], root)
    for sha in HISTORY:
        run(["git", "fetch", "--quiet", "--no-tags", "--no-recurse-submodules", "--no-filter",
             "--depth=1", source, sha], store)
    return store


@pytest.fixture(scope="module")
def history(tmp_path_factory):
    return history_store(ROOT, tmp_path_factory.mktemp("release-history"))


def test_history_fixture_fetches_exact_git_bytes_without_mutating_shallow_checkout(history, tmp_path):
    root = tmp_path / "checkout"
    run(["git", "clone", "--quiet", "--no-local", "--depth=1", str(ROOT), str(root)], tmp_path)
    run(["git", "remote", "set-url", "origin", str(history)], root)
    assert run(["git", "rev-parse", "--is-shallow-repository"], root) == "true"
    assert all(subprocess.run(["git", "cat-file", "-e", sha], cwd=root, capture_output=True,
                              timeout=5).returncode != 0 for sha in HISTORY)
    before = (run(["git", "count-objects", "-v"], root), run(["git", "for-each-ref"], root),
              run(["git", "rev-parse", "HEAD"], root))
    fetched = history_store(root, tmp_path / "history")
    assert before == (run(["git", "count-objects", "-v"], root), run(["git", "for-each-ref"], root),
                      run(["git", "rev-parse", "HEAD"], root))
    assert run(["git", "rev-parse", "--is-shallow-repository"], root) == "true"
    for sha, paths in HISTORY.items():
        for path in paths:
            args = ["git", "show", f"{sha}:{path}"]
            assert (subprocess.run(args, cwd=fetched, capture_output=True, check=True, timeout=5).stdout
                    == subprocess.run(args, cwd=history, capture_output=True, check=True, timeout=5).stdout)


def test_history_fixture_reads_origin_without_mutating_blobless_checkout(tmp_path, monkeypatch):
    origin = tmp_path / "origin"
    origin.mkdir()
    expected = b"Immutable comparison bytes, including the final newline.\n"
    (origin / "comparison.txt").write_bytes(expected)
    run(["git", "init", "--quiet"], origin)
    revision = commit(origin)
    blob = run(["git", "rev-parse", "HEAD:comparison.txt"], origin)
    root = tmp_path / "checkout"
    run(["git", "clone", "--quiet", "--no-local", "--no-checkout", "--filter=blob:none",
         "--upload-pack=git -c uploadpack.allowFilter=true upload-pack",
         origin.as_uri(), str(root)], tmp_path)
    missing = ["git", "rev-list", "--objects", "--missing=print", "--all"]
    assert "?" + blob in run(missing, root)
    assert run(["git", "cat-file", "-t", revision], root) == "commit"
    assert run(["git", "rev-parse", "--is-shallow-repository"], root) == "false"
    before = (run(missing, root), run(["git", "count-objects", "-v"], root),
              run(["git", "for-each-ref"], root), (root / ".git/config").read_bytes())
    monkeypatch.setattr(sys.modules[__name__], "HISTORY", {revision: ("comparison.txt",)})
    fetched = history_store(root, tmp_path / "history")
    assert before == (run(missing, root), run(["git", "count-objects", "-v"], root),
                      run(["git", "for-each-ref"], root), (root / ".git/config").read_bytes())
    result = subprocess.run(["git", "show", f"{revision}:comparison.txt"], cwd=fetched,
                            capture_output=True, check=True, timeout=5)
    assert result.stdout == expected


def commit(root):
    run(["git", "add", "."], root)
    run(["git", "-c", "user.name=Identity fixture", "-c", "user.email=fixture@example.invalid",
         "commit", "--quiet", "--allow-empty", "-m", "fixture source"], root)
    return run(["git", "rev-parse", "HEAD"], root)
