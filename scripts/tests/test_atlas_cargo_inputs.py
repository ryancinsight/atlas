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
_MAIN = ("root",)
_BS = "\x5c\x5c"


def _root_metadata(root: Path) -> dict:
    return _metadata(root, [("root-id", "root", "Cargo.toml", None)])


def _repository(
    tmp_path: Path, files: dict[str, str], changed: list[str], manifest: str = _ROOT_PACKAGE
) -> Path:
    root = _repo(tmp_path)
    _write(root, "Cargo.toml", manifest)
    _write(root, "src/lib.rs", "pub fn root() {}\n")
    for path, content in {**files, **dict.fromkeys(changed, "prose\n")}.items():
        _write(root, path, content)
    _commit(root, "base")
    return root


def _owned(root: Path, changed: list[str]) -> tuple[str, ...]:
    return cargo_input_owners(root, "Cargo.toml", _root_metadata(root), changed).packages


def _gated(tmp_path: Path, files: dict[str, str], changed: list[str], manifest: str = _ROOT_PACKAGE):
    return _owned(_repository(tmp_path, files, changed, manifest), changed)


_STD_ONLY = (
    '#![cfg_attr(not(feature = "std"), no_std)]\n#![deny(missing_docs)]\n'
    "/// Docs name `docs/adr/0002-x.md` and https://docs.rs/root without including them.\n"
    "#[derive(Debug, Clone, PartialEq)]\npub struct A;\n"
    "macro_rules! twice { ($x:expr) => { $x + $x }; }\n"
    '#[path = "other.rs"]\nmod other;\n'
    'pub fn f() -> usize { println!("{}", twice!(1)); include_str!("../docs/other.md").len() }\n'
)


@pytest.mark.parametrize(
    "changed",
    [
        ["docs/adr/0002-rate-constant-typing.md", "backlog.md"],
        ["docs/book/cpu_topology.md", "docs/book/topology_epoch.md", "CHANGELOG.md"],
        ["docs/X.markdown", "docs/OTHER2.MD"],
    ],
)
def test_markdown_no_target_can_read_owns_no_root_package(tmp_path: Path, changed: list[str]) -> None:
    build = 'fn main() { println!("cargo:rerun-if-changed=build.rs"); }\n'
    manifest = _ROOT_PACKAGE + 'readme = "README.md"\n'
    files = {"src/lib.rs": _STD_ONLY, "src/other.rs": "\n", "build.rs": build}

    assert _gated(tmp_path, files, changed, manifest) == ()


def _one(text: str, changed: str = "docs/x.md", at: str = "src/lib.rs") -> tuple[dict[str, str], str]:
    return {at: text}, changed


_INC = 'const T: &str = include_str!("../docs/x.md");\n'
_G = "guide/intro.md"
_CASES = {
    "include-str": _one(_INC),
    "include-bytes": _one('static B: &[u8] = include_bytes!("../docs/x.md");\n'),
    "include-in-doc-attribute": _one('#![doc = include_str!("../docs/x.md")]\n'),
    "include-of-same-name-elsewhere": _one(_INC, "other/x.md"),
    "include-of-uppercase-file-name": _one(_INC, "docs/X.MD"),
    "include-path-case": _one('const T: &str = include_str!("../DOCS/X.MD");\n'),
    "includer-in-tests": _one(_INC, at="tests/it.rs"),
    "includer-in-sibling-crate": _one(_INC, at="crates/b/src/lib.rs"),
    "includer-in-target-module": _one(_INC, at="src/target/mod.rs"),
    "includer-in-target-directory": _one(_INC, at="target/gen.rs"),
    "includer-below-nested-git": _one(_INC, at="vendor/.git/hook.rs"),
    "includer-in-uppercase-extension": (
        {"src/lib.rs": '#[path = "inc.RS"]\nmod inc;\n', "src/inc.RS": _INC},
        "docs/x.md",
    ),
    "build-script-reads-manifest-directory": _one('fn main() { std::fs::read_dir(env!("CARGO_MANIFEST_DIR")); }\n', _G, "build.rs"),
    "build-script-reads-listed-paths": _one('fn main() { std::fs::read_to_string("chapters.txt"); }\n', _G, "build.rs"),
    "test-runs-git-ls-files": _one('fn t() { std::process::Command::new("git").arg("ls-files"); }\n', _G, "tests/tidy.rs"),
    "path-reads-directory": _one("fn t(p: &std::path::Path) { let _ = p.read_dir(); }\n", _G),
    "reads-environment": _one('fn t() { let _ = std::env::var("DOC_DIR"); }\n', _G),
    "calls-foreign-function": _one('extern "C" { fn system(c: *const u8) -> i32; }\n', _G),
    "runs-inline-assembly": _one('fn t() { unsafe { core::arch::asm!("nop"); } }\n', _G),
    "runs-global-assembly": _one('core::arch::global_asm!("nop");\n', _G),
    "runs-naked-assembly": _one('fn t() { naked_asm!("ret"); }\n', _G),
    "doctest-reads-directory": _one('/// ```\n/// std::fs::read_dir(".");\n/// ```\npub fn f() {}\n', _G),
    "code-after-block-comment-marker": _one('/*\n// */ std::fs::read_dir(".");\n', _G),
    "include-argument-from-fragments": _one('const T: &str = include_str!(concat!("../do", "cs/x.m", "d"));\n'),
    "include-argument-raw-string": _one('const T: &str = include_str!(r"../docs/y");\n', "c/n.md"),
    "include-argument-with-escape": _one(f'const T: &str = include_str!("..{_BS}docs{_BS}y");\n', "c/n.md"),
    "include-of-rust-text-in-another-file": ({"src/lib.rs": 'include!("t.in");\n', "src/t.in": _INC}, "docs/x.md"),
    "path-attribute-to-non-rust-file": ({"src/lib.rs": '#[path = "t.in"]\nmod t;\n', "src/t.in": _INC}, "docs/x.md"),
    "path-attribute-raw-string": ({"src/lib.rs": '#[path = r"t.in"]\nmod t;\n', "src/t.in": _INC}, "docs/x.md"),
    "cargo-config": _one("[build]\njobs = 1\n", at=".cargo/config.toml"),
    "cargo-config-without-extension": _one("[build]\njobs = 1\n", at=".cargo/config"),
    "nextest-config": _one("[profile.default]\n", at=".config/nextest.toml"),
    "sibling-manifest-declares-dependency": _one('[package]\nname = "b"\n[dependencies]\nh = "1"\n', at="crates/b/Cargo.toml"),
    "sibling-manifest-cannot-be-parsed": _one("[[", at="crates/b/Cargo.toml"),
    "sibling-manifest-in-uppercase": _one('[dependencies]\nh = "1"\n', at="crates/b/CARGO.TOML"),
}


@pytest.mark.parametrize("case", sorted(_CASES))
def test_markdown_the_repository_can_read_keeps_the_origin_main_owner(tmp_path: Path, case: str) -> None:
    files, changed = _CASES[case]

    assert _gated(tmp_path, files, [changed]) == _MAIN


def test_symlink_keeps_the_origin_main_owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repository(tmp_path, {"docs/real.md": "prose\n", "docs/link.md": "real.md"}, ["docs/x.md"])
    monkeypatch.setattr(os.path, "islink", lambda path: Path(path).name == "link.md")

    assert _owned(root, ["docs/real.md"]) == _MAIN


def test_repository_git_directory_is_not_scanned(tmp_path: Path) -> None:
    files = {".git/refs/spelled.rs": 'fn f() { std::fs::read_dir("."); }\n'}

    assert _gated(tmp_path, files, ["docs/x.md"]) == ()


_MANIFEST_CLAIMS = [
    ('readme = "docs/readme.md"\n', "docs/readme.md", True),
    ('readme = "./docs/Readme.md"\n', "docs/readme.md", True),
    (f'readme = "docs{_BS}readme.md"\n', "docs/readme.md", True),
    ("", "README.md", True),
    ("readme = false\n", "README.md", False),
    ('readme = "other.md"\n', "docs/x.md", False),
    ("", "docs/x.markdown", False),
    ("", "docs/X.MD", False),
    ('license-file = "docs/LICENSE.md"\n', "docs/LICENSE.md", True),
    ('include = ["src/**"]\n', "docs/x.md", True),
    ("readme.workspace = true\n", "docs/x.md", True),
    ("license-file.workspace = true\n", "docs/x.md", True),
    ("include.workspace = true\n", "docs/x.md", True),
    ("exclude.workspace = true\n", "docs/x.md", True),
    ("exclude = [1]\n", "docs/x.md", True),
    ('exclude = ["*.md"]\n', "docs/x.md", False),
    ("build.workspace = true\n", "docs/x.md", True),
    ("version = =\n", "docs/x.md", True),
    ('build = "tools/build.md"\n', "docs/x.md", True),
    ('build = "build.rs"\n', "docs/x.md", False),
    ('"build" = "gen.txt"\n', "docs/x.md", True),
    ('[lib]\npath = "src/lib.rs"\n', "docs/x.md", False),
    ('[lib]\npath = "SRC/LIB.RS"\n', "docs/x.md", False),
    ('[[bin]]\nname = "b"\npath = "lit/main.md"\n', "docs/x.md", True),
    ('[[test]]\nname = "t"\n"path" = "tests/t.txt"\n', "docs/x.md", True),
    ('[dependencies]\nhelper = "1"\n', "docs/x.md", True),
    ('[dev-dependencies]\nhelper = "1"\n', "docs/x.md", True),
    ('[build-dependencies]\nhelper = "1"\n', "docs/x.md", True),
    ('[dev_dependencies]\nhelper = "1"\n', "docs/x.md", True),
    ('[build_dependencies]\nhelper = "1"\n', "docs/x.md", True),
    ('[dependencies.helper]\nversion = "1"\n', "docs/x.md", True),
    ("[target.'cfg(unix)'.dependencies]\nhelper = \"1\"\n", "docs/x.md", True),
    ('[workspace.dependencies]\nhelper = "1"\n', "docs/x.md", True),
    ("[dependencies]\n", "docs/x.md", False),
]


@pytest.mark.parametrize(("extra", "changed", "gates"), _MANIFEST_CLAIMS)
def test_manifest_fields_decide_whether_markdown_gates(
    tmp_path: Path, extra: str, changed: str, gates: bool
) -> None:
    assert _gated(tmp_path, {}, [changed], _ROOT_PACKAGE + extra) == (_MAIN if gates else ())


def test_package_table_inside_a_string_is_not_a_package(tmp_path: Path) -> None:
    manifest = '[workspace]\nmembers = []\nnote = """\n[package]\n"""\n'

    assert _gated(tmp_path, {}, ["docs/x.md"], manifest) == _MAIN


@pytest.mark.parametrize(("owner", "attribute", "name"), [(os, "scandir", "hidden"), (Path, "read_text", "locked.rs")])
def test_unreadable_input_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner: object, attribute: str, name: str
) -> None:
    root = _repository(tmp_path, {"src/locked.rs": "\n", "src/hidden/x.rs": "\n"}, ["docs/x.md"])
    real = getattr(owner, attribute)

    def fault(subject: object, *arguments: object, **keywords: object) -> object:
        if Path(subject).name == name:
            raise PermissionError(13, "denied", str(subject))
        return real(subject, *arguments, **keywords)

    monkeypatch.setattr(owner, attribute, fault)

    with pytest.raises(PermissionError):
        _owned(root, ["docs/x.md"])


def test_undecodable_sibling_manifest_keeps_the_origin_main_owner(tmp_path: Path) -> None:
    root = _repository(tmp_path, {}, ["docs/x.md"])
    (root / "crates" / "b").mkdir(parents=True)
    (root / "crates" / "b" / "Cargo.toml").write_bytes(b"\xff\xfe")

    assert _owned(root, ["docs/x.md"]) == _MAIN


def test_undecodable_source_is_still_scanned(tmp_path: Path) -> None:
    root = _repository(tmp_path, {}, ["docs/x.md"])
    (root / "src" / "lib.rs").write_bytes(b"\xff\xfe\nfn f() { std::fs::read_dir(\".\"); }\n")

    assert _owned(root, ["docs/x.md"]) == _MAIN


def test_markdown_in_member_crate_is_judged_against_its_own_manifest(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write(root, "Cargo.toml", '[workspace]\nmembers = ["crates/foo"]\n')
    _write(root, "crates/foo/Cargo.toml", '[package]\nname = "foo"\nversion = "0.1.0"\nreadme = "README.md"\n')
    for path in ("src/lib.rs", "README.md", "docs/notes.md"):
        _write(root, f"crates/foo/{path}", "pub fn foo() {}\n" if path.endswith(".rs") else "prose\n")
    _commit(root, "base")
    metadata = _metadata(root, [("foo-id", "foo", "crates/foo/Cargo.toml", None)])

    assert cargo_input_owners(root, "Cargo.toml", metadata, ["crates/foo/README.md"]).packages == ("foo",)
    assert cargo_input_owners(root, "Cargo.toml", metadata, ["crates/foo/docs/notes.md"]).packages == ()
