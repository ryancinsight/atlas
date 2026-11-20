"""Value-semantic tests for shared Cargo input ownership."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlas_cargo_inputs import CargoInputOwners, cargo_input_owners  # noqa: E402


_IDENT = ["-c", "user.email=t@t", "-c", "user.name=t"]


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *_IDENT, *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _commit(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


def _metadata(root: Path, packages: list[tuple[str, str, str, list[dict] | None]]) -> dict:
    return {
        "workspace_members": [identity for identity, *_ in packages],
        "packages": [
            {
                "id": identity,
                "name": name,
                "manifest_path": str(root / manifest),
                **({"targets": targets} if targets is not None else {}),
            }
            for identity, name, manifest, targets in packages
        ],
    }


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    return root


def test_deleted_root_input_still_selects_root_package(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write(root, "Cargo.toml", '[package]\nname = "root"\nversion = "0.1.0"\n')
    _write(root, "src/lib.rs", "pub fn removed() {}\n")
    _commit(root, "base")
    (root / "src/lib.rs").unlink()
    _commit(root, "delete")
    changed = _git(root, "diff", "--no-renames", "--name-only", "HEAD^", "HEAD").splitlines()

    owners = cargo_input_owners(
        root, "Cargo.toml", _metadata(root, [("root-id", "root", "Cargo.toml", None)]), changed
    )

    assert owners == CargoInputOwners(("root",), (), (), ())


def test_virtual_workspace_classifies_members_and_nested_manifests(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write(root, "Cargo.toml", '[workspace]\nmembers = ["crates/foo"]\n')
    _write(root, "crates/foo/Cargo.toml", '[package]\nname = "foo"\nversion = "0.1.0"\n')
    _write(root, "crates/foo/src/lib.rs", "pub fn foo() {}\n")
    _write(root, "fuzz/Cargo.toml", '[package]\nname = "foo"\nversion = "0.0.0"\n[workspace]\n')
    _write(root, "fuzz/src/main.rs", "fn main() {}\n")
    _write(root, "vendor/Cargo.toml", '[workspace]\nmembers = ["inner"]\n')
    _write(root, "vendor/inner/src/lib.rs", "pub fn inner() {}\n")
    _commit(root, "workspace")
    metadata = _metadata(
        root,
        [("foo-id", "foo", "crates/foo/Cargo.toml", [{"test": False}])],
    )

    owners = cargo_input_owners(
        root,
        "Cargo.toml",
        metadata,
        ["Cargo.toml", "crates/foo/src/lib.rs", "fuzz/src/main.rs", "vendor/inner/src/lib.rs"],
    )

    assert owners == CargoInputOwners(
        ("foo",), ("foo",), ("vendor/Cargo.toml",), ("fuzz/Cargo.toml",)
    )


@pytest.mark.parametrize("changed", [".config/nextest.toml", "rust-toolchain.toml", ".cargo/config.toml"])
def test_global_inputs_select_each_workspace_member(tmp_path: Path, changed: str) -> None:
    root = _repo(tmp_path)
    _write(root, "Cargo.toml", '[workspace]\nmembers = ["a", "b"]\n')
    for name in ("a", "b"):
        _write(root, f"{name}/Cargo.toml", f'[package]\nname = "{name}"\nversion = "0.1.0"\n')
    _commit(root, "workspace")
    metadata = _metadata(
        root,
        [("a-id", "a", "a/Cargo.toml", None), ("b-id", "b", "b/Cargo.toml", None)],
    )

    assert cargo_input_owners(root, "Cargo.toml", metadata, [changed]).packages == ("a", "b")


def test_cli_emits_lf_records_from_crlf_paths(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write(root, "Cargo.toml", '[package]\nname = "root"\nversion = "0.1.0"\n')
    _commit(root, "root")
    paths = tmp_path / "changed.txt"
    paths.write_bytes(b"src/lib.rs\r\n")
    script = Path(__file__).resolve().parents[1] / "atlas_cargo_inputs.py"

    result = subprocess.run(
        [sys.executable, str(script), "--root", str(root), "--workspace-manifest", "Cargo.toml", "--changed-paths", str(paths)],
        input=json.dumps(_metadata(root, [("root-id", "root", "Cargo.toml", None)])).encode(),
        check=True,
        capture_output=True,
    )

    assert result.stdout == b"package\troot\n"
