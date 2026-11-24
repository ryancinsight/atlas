"""Value-semantic tests for shared Cargo input ownership."""

from __future__ import annotations

import json
import os
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


def test_changed_hybrid_root_manifest_selects_every_member(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write(
        root,
        "Cargo.toml",
        '[package]\nname = "metis-ui"\nversion = "0.1.0"\n'
        '[workspace]\nmembers = ["crates/metis-core"]\n',
    )
    _write(
        root,
        "crates/metis-core/Cargo.toml",
        '[package]\nname = "metis-core"\nversion = "0.1.0"\n',
    )
    _commit(root, "workspace")
    metadata = _metadata(
        root,
        [
            ("ui-id", "metis-ui", "Cargo.toml", None),
            ("core-id", "metis-core", "crates/metis-core/Cargo.toml", None),
        ],
    )

    owners = cargo_input_owners(root, "Cargo.toml", metadata, ["Cargo.toml"])

    assert owners.packages == ("metis-ui", "metis-core")


def test_unrecognized_nested_manifest_stops_ancestor_walk(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write(root, "Cargo.toml", '[workspace]\nmembers = ["crates/foo"]\n')
    _write(root, "crates/foo/Cargo.toml", '[package]\nname = "foo"\nversion = "0.1.0"\n')
    _write(
        root,
        "crates/foo/fixtures/input/Cargo.toml",
        '[dependencies]\nserde = "1"\n',
    )
    _write(root, "crates/foo/fixtures/input/case.txt", "input\n")
    _commit(root, "workspace")
    metadata = _metadata(
        root,
        [("foo-id", "foo", "crates/foo/Cargo.toml", None)],
    )

    owners = cargo_input_owners(
        root,
        "Cargo.toml",
        metadata,
        ["crates/foo/fixtures/input/case.txt"],
    )

    assert owners == CargoInputOwners((), (), (), ())


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


_ROOT_PACKAGE = '[package]\nname = "root"\nversion = "0.1.0"\n'


def _root_metadata(root: Path) -> dict:
    return _metadata(root, [("root-id", "root", "Cargo.toml", None)])


def _gated(
    tmp_path: Path, files: dict[str, str], changed: list[str], manifest: str = _ROOT_PACKAGE
) -> tuple[str, ...]:
    root = _repo(tmp_path)
    _write(root, "Cargo.toml", manifest)
    _write(root, "src/lib.rs", "pub fn root() {}\n")
    for path, content in files.items():
        _write(root, path, content)
    for path in changed:
        _write(root, path, "prose\n")
    _commit(root, "base")
    return cargo_input_owners(root, "Cargo.toml", _root_metadata(root), changed).packages


@pytest.mark.parametrize(
    "changed",
    [
        ["docs/adr/0002-rate-constant-typing.md", "backlog.md"],
        ["docs/book/cpu_topology.md", "docs/book/topology_epoch.md", "CHANGELOG.md"],
    ],
)
def test_unreferenced_markdown_owns_no_root_package(tmp_path: Path, changed: list[str]) -> None:
    lib = '#![deny(missing_docs)]\npub const A: &str = "my_docs";\npub const B: &str = "docs.rs";\n'
    files = {"src/lib.rs": lib, "README.md": "readme\n"}

    assert _gated(tmp_path, files, changed, _ROOT_PACKAGE + 'readme = "README.md"\n') == ()


_SOURCES = {
    "quoted-directory": ("src/lib.rs", 'pub const D: &str = "docs";\n', "docs/adr/0001-x.md"),
    "doc-comment-url": ("src/lib.rs", "//! https://host/docs/adr/\n", "docs/adr/0001-x.md"),
    "build-script-read-dir": (
        "build.rs",
        'fn main() { std::fs::read_dir("docs/book").unwrap(); }\n',
        "docs/book/ch1.md",
    ),
    "concat-built-path": (
        "src/lib.rs",
        'pub const T: &str = include_str!(concat!("../docs/", "intro", ".md"));\n',
        "docs/intro.md",
    ),
    "macro-built-stem": (
        "src/lib.rs",
        'macro_rules! chapter { ($n:literal) => { include_str!(concat!("../book/", $n, ".md")) }; }\n'
        'pub const C: &str = chapter!("intro");\n',
        "book/intro.md",
    ),
    "test-reads-directory": (
        "tests/corpus.rs",
        'fn corpus() { std::fs::read_dir("tests/corpus").unwrap(); }\n',
        "tests/corpus/case1.md",
    ),
    "stem-quoted-root-level": ("src/lib.rs", 'pub const S: &str = "changelog";\n', "CHANGELOG.md"),
    "name-before-separator": ("src/lib.rs", 'pub const N: &str = "x.md/";\n', "x.md"),
    "backslash-separator": (
        "src/lib.rs",
        'pub const W: &str = "docs\\\\book";\n',
        "docs/book/x.md",
    ),
    "text-case": ("src/lib.rs", 'pub const D: &str = "DOCS";\n', "docs/x.md"),
    "path-case": ("src/lib.rs", 'pub const D: &str = "docs";\n', "Docs/X.md"),
    "extension-with-dot": (
        "src/lib.rs",
        'pub fn f(n: &str) -> bool { n.ends_with(".md") }\n',
        "zzz/q.md",
    ),
    "extension-bare": (
        "src/lib.rs",
        'pub fn f(e: &std::ffi::OsStr) -> bool { e == "md" }\n',
        "zzz/q.md",
    ),
    "extension-markdown": (
        "src/lib.rs",
        'pub fn f(n: &str) -> bool { n.ends_with(".markdown") }\n',
        "zzz/q.md",
    ),
    "extension-glob": ("src/lib.rs", 'pub const G: &str = "*.md,*.txt";\n', "zzz/q.md"),
    "includer-in-tests": ("tests/it.rs", 'const D: &str = "docs";\n', "docs/x.md"),
    "includer-in-examples": ("examples/e.rs", 'const D: &str = "docs";\n', "docs/x.md"),
    "includer-in-sibling-crate": ("crates/b/src/lib.rs", 'const D: &str = "docs";\n', "docs/x.md"),
    "includer-in-target-module": ("src/target/mod.rs", 'const D: &str = "docs";\n', "docs/x.md"),
    "includer-in-target-directory": ("target/gen.rs", 'const D: &str = "docs";\n', "docs/x.md"),
    "includer-below-nested-git": ("vendor/.git/hook.rs", 'const D: &str = "docs";\n', "docs/x.md"),
}


@pytest.mark.parametrize("case", sorted(_SOURCES))
def test_markdown_a_rust_source_can_read_gates(tmp_path: Path, case: str) -> None:
    includer, text, changed = _SOURCES[case]

    assert _gated(tmp_path, {includer: text}, [changed]) == ("root",)


def _repository_with_docs(tmp_path: Path) -> Path:
    root = _repo(tmp_path)
    _write(root, "Cargo.toml", _ROOT_PACKAGE)
    _write(root, "src/lib.rs", "pub fn root() {}\n")
    _write(root, "docs/x.md", "prose\n")
    _commit(root, "base")
    return root


def test_repository_git_directory_is_not_scanned(tmp_path: Path) -> None:
    root = _repository_with_docs(tmp_path)
    _write(root, ".git/refs/spelled.rs", 'const D: &str = "docs";\n')

    assert cargo_input_owners(root, "Cargo.toml", _root_metadata(root), ["docs/x.md"]).packages == ()


_MANIFEST_CLAIMS = [
    ('readme = "docs/readme.md"\n', "docs/readme.md", True),
    ('readme = "./docs/Readme.md"\n', "docs/readme.md", True),
    ('readme = "docs\\\\readme.md"\n', "docs/readme.md", True),
    ("readme = true\n", "README.md", True),
    ("", "README.md", True),
    ("readme = false\n", "README.md", False),
    ('readme = "other.md"\n', "docs/x.md", False),
    ('license-file = "docs/LICENSE.md"\n', "docs/LICENSE.md", True),
    ('include = ["src/**"]\n', "docs/x.md", True),
    ("readme.workspace = true\n", "docs/x.md", True),
    ("license-file.workspace = true\n", "docs/x.md", True),
    ("include.workspace = true\n", "docs/x.md", True),
    ("exclude.workspace = true\n", "docs/x.md", True),
    ("build.workspace = true\n", "docs/x.md", True),
    ("include = [1]\n", "docs/x.md", True),
]


@pytest.mark.parametrize(("extra", "changed", "gates"), _MANIFEST_CLAIMS)
def test_manifest_fields_decide_whether_markdown_gates(
    tmp_path: Path, extra: str, changed: str, gates: bool
) -> None:
    packages = _gated(tmp_path, {}, [changed], _ROOT_PACKAGE + extra)

    assert packages == (("root",) if gates else ())


@pytest.mark.parametrize(
    "manifest",
    [
        _ROOT_PACKAGE + "version = =\n",
        '[workspace]\nmembers = []\nnote = """\n[package]\n"""\n',
    ],
)
def test_manifest_that_cannot_be_interpreted_claims_every_file(
    tmp_path: Path, manifest: str
) -> None:
    assert _gated(tmp_path, {}, ["docs/x.md"], manifest) == ("root",)


def test_unlistable_directory_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repository_with_docs(tmp_path)
    (root / "src" / "hidden").mkdir()
    real = os.scandir

    def scandir(path: str = ".") -> object:
        if Path(path).name == "hidden":
            raise PermissionError(13, "denied", str(path))
        return real(path)

    monkeypatch.setattr(os, "scandir", scandir)

    with pytest.raises(PermissionError):
        cargo_input_owners(root, "Cargo.toml", _root_metadata(root), ["docs/x.md"])


def test_unreadable_source_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repository_with_docs(tmp_path)
    _write(root, "src/locked.rs", "pub fn locked() {}\n")
    real = Path.read_text

    def read_text(self: Path, *arguments: object, **keywords: object) -> str:
        if self.name == "locked.rs":
            raise PermissionError(13, "denied", str(self))
        return real(self, *arguments, **keywords)

    monkeypatch.setattr(Path, "read_text", read_text)

    with pytest.raises(PermissionError):
        cargo_input_owners(root, "Cargo.toml", _root_metadata(root), ["docs/x.md"])


def test_undecodable_source_is_still_scanned(tmp_path: Path) -> None:
    root = _repository_with_docs(tmp_path)
    (root / "src" / "lib.rs").write_bytes(b'\xff\xfe\nconst D: &str = "docs";\n')

    owners = cargo_input_owners(root, "Cargo.toml", _root_metadata(root), ["docs/x.md"])

    assert owners.packages == ("root",)


def test_markdown_deleted_but_still_included_gates(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write(root, "Cargo.toml", _ROOT_PACKAGE)
    _write(root, "src/lib.rs", 'pub const TEXT: &str = include_str!("../docs/gone.md");\n')
    _commit(root, "base")

    owners = cargo_input_owners(root, "Cargo.toml", _root_metadata(root), ["docs/gone.md"])

    assert owners.packages == ("root",)


def test_markdown_in_member_crate_is_judged_against_its_own_manifest(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write(root, "Cargo.toml", '[workspace]\nmembers = ["crates/foo"]\n')
    _write(root, "crates/foo/Cargo.toml", '[package]\nname = "foo"\nversion = "0.1.0"\nreadme = "README.md"\n')
    _write(root, "crates/foo/src/lib.rs", "pub fn foo() {}\n")
    _write(root, "crates/foo/README.md", "readme\n")
    _write(root, "crates/foo/docs/notes.md", "notes\n")
    _commit(root, "base")
    metadata = _metadata(root, [("foo-id", "foo", "crates/foo/Cargo.toml", None)])

    assert cargo_input_owners(root, "Cargo.toml", metadata, ["crates/foo/README.md"]).packages == ("foo",)
    assert cargo_input_owners(root, "Cargo.toml", metadata, ["crates/foo/docs/notes.md"]).packages == ()
