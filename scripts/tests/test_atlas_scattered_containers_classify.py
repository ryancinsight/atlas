#!/usr/bin/env python3
"""Tests for the ATLAS-ARCH-008 scattered-container classifier.

Covers the production vs test/bench/example split, the `#[cfg(test)]` /
`mod tests` brace-depth tracking, the comment/literal stripping that keeps
template strings and doc text from posing as predicates or sites, and the two
`MemberSource` implementations (working tree vs pinned git objects).
Fixtures are `tmp_path` trees so the tests never touch the live repository.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath

import pytest

from atlas_scattered_containers_classify import (
    Occurrence,
    PinnedSource,
    VEC_VEC,
    WorktreeSource,
    _gated_attribute_block,
    _lexical,
    _path_decl_map,
    classify_file,
    compute_test_regions,
    verify_oracle,
)


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    path = tmp_path.joinpath(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _sites(tmp_path: Path, rel: str, content: str) -> list[Occurrence]:
    _write(tmp_path, rel, content)
    source = WorktreeSource(tmp_path)
    return classify_file(
        "member", source, PurePosixPath(rel), _path_decl_map(source)
    )


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    ).stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "Atlas Tests")
    _git(repo, "config", "commit.gpgsign", "false")


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _pinned_sites(
    repo: Path, pin: str, rel: str
) -> list[Occurrence]:
    source = PinnedSource(repo, pin)
    try:
        return classify_file(
            "member", source, PurePosixPath(rel), _path_decl_map(source)
        )
    finally:
        source.close()


def test_production_occurrence_is_classified_production(tmp_path: Path) -> None:
    occurrences = _sites(
        tmp_path,
        "src/lib.rs",
        "fn build() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n",
    )
    assert len(occurrences) == 1
    assert occurrences[0].test_local is False


def test_cfg_test_block_is_test_local(tmp_path: Path) -> None:
    content = (
        "pub fn build() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n"
        "#[cfg(test)]\n"
        "mod tests {\n"
        "    fn collect() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n"
        "}\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert [o.test_local for o in occurrences] == [False, True]


def test_cfg_all_test_feature_alloc_gate(tmp_path: Path) -> None:
    content = (
        "#[cfg(all(test, feature = \"alloc\"))]\n"
        "mod tests {\n"
        "    let rows: Vec<Vec<f64>> = Vec::new();\n"
        "}\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 1
    assert occurrences[0].test_local is True


def test_cfg_test_attribute_on_same_line(tmp_path: Path) -> None:
    content = "#[cfg(test)] mod tests {\n    let rows: Vec<Vec<f64>> = Vec::new();\n}\n"
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 1
    assert occurrences[0].test_local is True


def test_mod_tests_block_is_test_local(tmp_path: Path) -> None:
    content = (
        "mod tests {\n"
        "    fn collect() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n"
        "}\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 1
    assert occurrences[0].test_local is True


def test_feature_string_value_is_not_a_test_predicate(tmp_path: Path) -> None:
    content = (
        "#[cfg(feature = \"test-utils\")]\n"
        "fn build() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 1
    assert occurrences[0].test_local is False


def test_not_test_guard_stays_production(tmp_path: Path) -> None:
    content = (
        "#[cfg(not(test))]\n"
        "fn build() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 1
    assert occurrences[0].test_local is False


def test_path_under_tests_dir_is_test_local(tmp_path: Path) -> None:
    occurrences = _sites(
        tmp_path,
        "crates/x/tests/integration.rs",
        "fn main() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n",
    )
    assert len(occurrences) == 1
    assert occurrences[0].test_local is True


def test_provider_worktree_lane_is_not_scanned(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/lib.rs",
        "fn build() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n",
    )
    _write(
        tmp_path,
        "worktrees/peer/src/lib.rs",
        "fn peer() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n",
    )

    files = WorktreeSource(tmp_path).files()

    assert files == [PurePosixPath("src/lib.rs")]


def test_benches_and_examples_are_bench_local(tmp_path: Path) -> None:
    bench = _sites(
        tmp_path,
        "benches/measure.rs",
        "fn bench() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n",
    )
    example = _sites(
        tmp_path,
        "examples/demo.rs",
        "fn main() { let rows: Vec<Vec<f64>> = Vec::new(); }\n",
    )
    assert bench[0].test_local is True
    assert example[0].test_local is True


def test_test_utils_helper_file_is_production(tmp_path: Path) -> None:
    occurrences = _sites(
        tmp_path,
        "src/test_utils.rs",
        "pub fn helper() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n",
    )
    assert len(occurrences) == 1
    assert occurrences[0].test_local is False


def test_suffixed_test_file_is_test_local(tmp_path: Path) -> None:
    occurrences = _sites(
        tmp_path,
        "src/collector_tests.rs",
        "fn collect() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n",
    )
    assert len(occurrences) == 1
    assert occurrences[0].test_local is True


def test_string_literal_does_not_arm_test_context(tmp_path: Path) -> None:
    content = (
        "fn render() {\n"
        "    let template = \"mod tests {\";\n"
        "    let rows: Vec<Vec<f64>> = Vec::new();\n"
        "    rows\n"
        "}\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 1
    assert occurrences[0].test_local is False


def test_commented_occurrence_is_not_counted(tmp_path: Path) -> None:
    content = (
        "// let rows: Vec<Vec<f64>> = Vec::new();  // commented site\n"
        "fn build() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 1
    assert occurrences[0].test_local is False


def test_block_comment_does_not_arm_context(tmp_path: Path) -> None:
    content = (
        "/*\n"
        " * mod tests {\n"
        " */\n"
        "fn build() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 1
    assert occurrences[0].test_local is False


def test_raw_string_literal_is_not_scanned(tmp_path: Path) -> None:
    content = (
        "fn gen() {\n"
        "    let tpl = r\"let rows: Vec<Vec<f64>> = Vec::new();\";\n"
        "    tpl\n"
        "}\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 0


def test_lifetime_signature_occurrence_is_counted(tmp_path: Path) -> None:
    content = (
        "pub fn merge<'a, T: Scalar>(left: &'a [f64], right: &'a [f64]) -> Vec<Vec<T>> {\n"
        "    vec![left.to_vec(), right.to_vec()]\n"
        "}\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 1
    assert occurrences[0].test_local is False


def test_char_literal_brace_does_not_corrupt_depth(tmp_path: Path) -> None:
    content = (
        "#[cfg(test)]\n"
        "mod tests {\n"
        "    fn find(c: char) -> bool { c == '{' }\n"
        "    let rows: Vec<Vec<f64>> = Vec::new();\n"
        "}\n"
        "fn prod() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert [o.test_local for o in occurrences] == [True, False]


def test_multiline_raw_string_is_not_scanned(tmp_path: Path) -> None:
    content = (
        "fn gen() {\n"
        "    let tpl = r#\"\n"
        "        let rows: Vec<Vec<f64>> = Vec::new();\n"
        "    \"#;\n"
        "    tpl\n"
        "}\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 0


def test_brace_tracking_ends_after_test_block(tmp_path: Path) -> None:
    content = (
        "#[cfg(test)]\n"
        "mod tests {\n"
        "    fn inner() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n"
        "}\n"
        "fn production() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert [o.test_local for o in occurrences] == [True, False]


def test_semicolon_line_does_not_leak_pending_test(tmp_path: Path) -> None:
    content = (
        "#[cfg(test)]\n"
        "use crate::collect;\n"
        "fn production() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 1
    assert occurrences[0].test_local is False


def test_compute_test_regions_nested_braces() -> None:
    lines = [
        "#[cfg(test)]",
        "mod tests {",
        "    fn outer() {",
        "        let rows: Vec<Vec<f64>> = Vec::new();",
        "    }",
        "}",
        "fn prod() {}",
    ]
    regions = compute_test_regions(lines)
    # The attribute line and the closing-brace boundary line are outside the
    # guarded region; every line between the opening `mod tests {` and the
    # matching `}` is test-local.
    assert regions == [False, True, True, True, True, False, False]


def test_site_string_is_path_line_column() -> None:
    occ = Occurrence(
        member="kwavers",
        path="crates/x/src/lib.rs",
        line=12,
        column=34,
        test_local=False,
    )
    assert occ.site() == "crates/x/src/lib.rs:12:34"


def test_deterministic_order(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/b.rs",
        "fn b() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n",
    )
    _write(
        tmp_path,
        "src/a.rs",
        "fn a() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n",
    )
    source = WorktreeSource(tmp_path)
    decls = _path_decl_map(source)
    first = classify_file("member", source, PurePosixPath("src/b.rs"), decls)
    first += classify_file("member", source, PurePosixPath("src/a.rs"), decls)
    second = classify_file("member", source, PurePosixPath("src/b.rs"), decls)
    second += classify_file("member", source, PurePosixPath("src/a.rs"), decls)
    assert [o.site() for o in first] == [o.site() for o in second]


def test_default_pattern_matches_vec_of_vec() -> None:
    assert VEC_VEC.search("let x: Vec<Vec<f64>> = vec![];") is not None
    assert VEC_VEC.search("let x: Vec<Vec < f64 >> = vec![];") is not None
    assert VEC_VEC.search("let x: Vec<f64> = vec![];") is None
    assert re.fullmatch(VEC_VEC.pattern, "Vec<Vec<") is not None


def test_scan_pattern_reaches_file_classifier(
    tmp_path: Path, monkeypatch: object
) -> None:
    import atlas_scattered_containers_classify as clf

    _write(
        tmp_path,
        "src/lib.rs",
        "fn value() { let rows: Box<Box<f64>> = Box::new(Box::new(1.0)); rows }\n",
    )
    pattern = re.compile(r"\bBox\s*<\s*Box\s*<")
    sources = [("member", WorktreeSource(tmp_path))]
    occurrences = clf.scan(pattern, sources)

    assert [occ.site() for occ in occurrences] == ["repos/member/src/lib.rs:1:24"]


def test_verify_oracle_matches() -> None:
    oracle = (
        "repos/x/src/lib.rs:3:5  # x\n"
        "repos/y/src/a.rs:10:2  # y\n"
    )
    drift = verify_oracle(
        ["repos/x/src/lib.rs:3:5", "repos/y/src/a.rs:10:2"], oracle
    )
    assert drift.matches is True
    assert drift.added == ()
    assert drift.removed == ()


def test_verify_oracle_reports_added_sites() -> None:
    oracle = "repos/x/src/lib.rs:3:5  # x\n"
    drift = verify_oracle(
        ["repos/x/src/lib.rs:3:5", "repos/z/src/b.rs:7:9"], oracle
    )
    assert drift.matches is False
    assert drift.added == ("repos/z/src/b.rs:7:9",)
    assert drift.removed == ()


def test_verify_oracle_reports_removed_sites() -> None:
    oracle = (
        "repos/x/src/lib.rs:3:5  # x\n"
        "repos/z/src/b.rs:7:9  # z\n"
    )
    drift = verify_oracle(["repos/x/src/lib.rs:3:5"], oracle)
    assert drift.matches is False
    assert drift.added == ()
    assert drift.removed == ("repos/z/src/b.rs:7:9",)


def test_verify_oracle_ignores_member_suffix_and_blanks() -> None:
    oracle = (
        "repos/x/src/lib.rs:3:5  # x\n"
        "\n"
        "   repos/y/src/a.rs:10:2   \n"
    )
    drift = verify_oracle(
        ["repos/x/src/lib.rs:3:5", "repos/y/src/a.rs:10:2"], oracle
    )
    assert drift.matches is True


def test_verify_oracle_empty_oracle_reports_all_added() -> None:
    drift = verify_oracle(["repos/x/src/lib.rs:3:5"], "")
    assert drift.matches is False
    assert drift.added == ("repos/x/src/lib.rs:3:5",)
    assert drift.removed == ()


def test_verify_oracle_cli_match_returns_zero(
    tmp_path: Path, monkeypatch: object
) -> None:
    import atlas_scattered_containers_classify as clf

    oracle = tmp_path / "oracle.txt"
    oracle.write_text("repos/x/src/lib.rs:9:4  # x\n", encoding="utf-8")
    occ = Occurrence(
        member="x",
        path="repos/x/src/lib.rs",
        line=9,
        column=4,
        test_local=False,
    )
    monkeypatch.setattr(clf, "scan", lambda pattern, sources: [occ])
    assert clf.main(["--verify-oracle", str(oracle)]) == 0


def test_verify_oracle_cli_drift_returns_one(
    tmp_path: Path, monkeypatch: object
) -> None:
    import atlas_scattered_containers_classify as clf

    oracle = tmp_path / "oracle.txt"
    oracle.write_text("repos/x/src/lib.rs:3:5  # x\n", encoding="utf-8")
    occ = Occurrence(
        member="x",
        path="repos/x/src/lib.rs",
        line=9,
        column=4,
        test_local=False,
    )
    monkeypatch.setattr(clf, "scan", lambda pattern, sources: [occ])
    assert clf.main(["--verify-oracle", str(oracle)]) == 1


def test_verify_oracle_cli_missing_file_returns_two(
    tmp_path: Path, monkeypatch: object
) -> None:
    import atlas_scattered_containers_classify as clf

    monkeypatch.setattr(clf, "scan", lambda pattern, sources: [])
    missing = tmp_path / "nope.txt"
    assert clf.main(["--verify-oracle", str(missing)]) == 2


def test_include_gated_module_file_is_test_local(tmp_path: Path) -> None:
    # A whole file compiled only under tests via the include-site gate must
    # be test-local even though the file itself carries no cfg markers.
    _write(tmp_path, "src/mod.rs", "#[cfg(test)]\nmod support;\n")
    occurrences = _sites(
        tmp_path,
        "src/support.rs",
        "fn helper() {\n    let rows: Vec<Vec<f64>> = Vec::new();\n    rows\n}\n",
    )
    assert len(occurrences) == 1
    assert occurrences[0].test_local is True


def test_plain_module_include_stays_production(tmp_path: Path) -> None:
    _write(tmp_path, "src/mod.rs", "mod support;\n")
    occurrences = _sites(
        tmp_path,
        "src/support.rs",
        "fn helper() {\n    let rows: Vec<Vec<f64>> = Vec::new();\n    rows\n}\n",
    )
    assert len(occurrences) == 1
    assert occurrences[0].test_local is False


def test_cfg_attribute_of_previous_declaration_does_not_leak(tmp_path: Path) -> None:
    # The #[cfg(test)] belongs to `adversarial`; `support` is plain production
    # (the boolean_csg regression: attribute of a neighbouring declaration).
    _write(
        tmp_path,
        "src/mod.rs",
        "#[cfg(test)]\nmod adversarial;\nmod support;\n",
    )
    occurrences = _sites(
        tmp_path,
        "src/support.rs",
        "fn helper() {\n    let rows: Vec<Vec<f64>> = Vec::new();\n    rows\n}\n",
    )
    assert len(occurrences) == 1
    assert occurrences[0].test_local is False


def test_include_gated_dir_module_is_test_local(tmp_path: Path) -> None:
    # dir/mod.rs files are declared as `mod <dir>;` from the crate root.
    _write(tmp_path, "src/lib.rs", "#[cfg(test)]\nmod sync;\n")
    occurrences = _sites(
        tmp_path,
        "src/sync/mod.rs",
        "pub fn run() {\n    let rows: Vec<Vec<f64>> = Vec::new();\n    rows\n}\n",
    )
    assert len(occurrences) == 1
    assert occurrences[0].test_local is True


def test_test_attr_function_is_test_local(tmp_path: Path) -> None:
    content = (
        "#[test]\n"
        "fn roundtrip() {\n"
        "    let rows: Vec<Vec<f64>> = Vec::new();\n"
        "    rows\n"
        "}\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 1
    assert occurrences[0].test_local is True


def test_test_attr_does_not_leak_into_following_fn(tmp_path: Path) -> None:
    content = (
        "#[test]\n"
        "fn roundtrip() {\n"
        "    let rows: Vec<Vec<f64>> = Vec::new();\n"
        "    rows\n"
        "}\n"
        "fn production() {\n"
        "    let rows: Vec<Vec<f64>> = Vec::new();\n"
        "    rows\n"
        "}\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert [o.test_local for o in occurrences] == [True, False]


def test_proptest_block_is_test_local(tmp_path: Path) -> None:
    content = (
        "proptest! {\n"
        "    #[test]\n"
        "    fn prop_roundtrip(v in 0..10u32) {\n"
        "        let rows: Vec<Vec<f64>> = Vec::new();\n"
        "        let _ = v;\n"
        "    }\n"
        "}\n"
    )
    occurrences = _sites(tmp_path, "src/lib.rs", content)
    assert len(occurrences) == 1
    assert occurrences[0].test_local is True


def test_path_decl_map_finds_path_attr_decls(tmp_path: Path) -> None:
    # A file loaded via #[path = "..."] is declared under an arbitrary module
    # name; the map must record the declaration (keyed by the resolved path,
    # since a basename key would collide on `mod.rs`) so the gate lookup finds
    # it. Keys are member-relative, so the two sources agree.
    _write(
        tmp_path,
        "src/mod.rs",
        "#[cfg(test)]\n#[path = \"support_extra.rs\"]\nmod support;\n",
    )
    source = WorktreeSource(tmp_path)
    decls = _path_decl_map(source)
    assert "src/support_extra.rs" in decls
    decl_rel, mod_idx = decls["src/support_extra.rs"]
    assert decl_rel == PurePosixPath("src/mod.rs")
    assert "mod support;" in source.read_text(decl_rel).splitlines()[mod_idx]


def test_gated_attribute_block_stacked_path_attr(tmp_path: Path) -> None:
    # The tests_ply pattern: #[cfg(test)] + #[path] stacked above the mod decl.
    mod = _write(
        tmp_path,
        "src/mod.rs",
        "#[cfg(test)]\n#[path = \"support_extra.rs\"]\nmod support;\n",
    )
    lines = mod.read_text(encoding="utf-8").splitlines()
    mod_idx = next(i for i, l in enumerate(lines) if "mod support;" in l)
    assert _gated_attribute_block(lines, mod_idx, "support_extra.rs") is True


def test_gated_attribute_block_plain_include_is_not_gated(tmp_path: Path) -> None:
    mod = _write(tmp_path, "src/mod.rs", "mod support;\n")
    lines = mod.read_text(encoding="utf-8").splitlines()
    assert _gated_attribute_block(lines, 0, "support.rs") is False


def test_gated_attribute_block_previous_decl_cfg_does_not_leak(tmp_path: Path) -> None:
    # The boolean_csg regression: the #[cfg(test)] belongs to `adversarial`.
    mod = _write(
        tmp_path,
        "src/mod.rs",
        "#[cfg(test)]\nmod adversarial;\nmod support;\n",
    )
    lines = mod.read_text(encoding="utf-8").splitlines()
    mod_idx = next(i for i, l in enumerate(lines) if "mod support;" in l)
    assert _gated_attribute_block(lines, mod_idx, "support.rs") is False


# --- MemberSource: working tree vs pinned git objects -----------------------


def test_lexical_collapses_dot_segments() -> None:
    assert _lexical("src/./lib.rs") == "src/lib.rs"
    assert _lexical("src/nested/../lib.rs") == "src/lib.rs"
    assert _lexical("./src//lib.rs") == "src/lib.rs"
    assert _lexical("src/lib.rs") == "src/lib.rs"


def test_pinned_source_reads_the_commit_not_the_checkout(tmp_path: Path) -> None:
    # The defect this mode exists to prevent: a member parked on a feature
    # branch must not change the census of what atlas pins. The pin carries a
    # site the checkout has since removed, and only the pin may report it.
    repo = tmp_path / "m"
    _init_repo(repo)
    _write(
        repo,
        "src/lib.rs",
        "fn build() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n",
    )
    pin = _commit_all(repo, "one")
    _write(
        repo,
        "src/lib.rs",
        "fn build() { let rows: Vec<f64> = Vec::new(); rows }\n",
    )

    pinned = _pinned_sites(repo, pin, "src/lib.rs")
    checkout = WorktreeSource(repo)
    worktree = classify_file(
        "member", checkout, PurePosixPath("src/lib.rs"), _path_decl_map(checkout)
    )

    assert [o.site() for o in pinned] == ["repos/member/src/lib.rs:1:24"]
    assert worktree == []


def test_pinned_and_worktree_agree_when_the_checkout_is_the_pin(
    tmp_path: Path,
) -> None:
    # The two sources must be interchangeable whenever nothing is in flight,
    # which is what lets the pinned mode replace the working-tree mode without
    # changing a single reported site.
    repo = tmp_path / "m"
    _init_repo(repo)
    _write(
        repo,
        "src/lib.rs",
        "fn build() { let rows: Vec<Vec<f64>> = Vec::new(); rows }\n",
    )
    _write(repo, "src/plain.rs", "fn other() {}\n")
    _write(repo, "benches/measure.rs", "fn bench() { let v: Vec<Vec<u8>> = vec![]; }\n")
    pin = _commit_all(repo, "one")

    checkout = WorktreeSource(repo)
    pinned = PinnedSource(repo, pin)
    try:
        assert pinned.files() == checkout.files()
        assert pinned.exists(PurePosixPath("src/plain.rs")) is True
        for rel in ("src/lib.rs", "benches/measure.rs", "src/plain.rs"):
            path = PurePosixPath(rel)
            assert [
                (o.site(), o.test_local)
                for o in classify_file(
                    "member", pinned, path, _path_decl_map(pinned)
                )
            ] == [
                (o.site(), o.test_local)
                for o in classify_file(
                    "member", checkout, path, _path_decl_map(checkout)
                )
            ]
    finally:
        pinned.close()


def test_pinned_source_existence_follows_the_commit(tmp_path: Path) -> None:
    repo = tmp_path / "m"
    _init_repo(repo)
    _write(repo, "src/lib.rs", "fn build() {}\n")
    pin = _commit_all(repo, "one")
    _write(repo, "src/later.rs", "fn later() {}\n")

    pinned = PinnedSource(repo, pin)
    try:
        assert pinned.exists(PurePosixPath("src/lib.rs")) is True
        assert pinned.exists(PurePosixPath("src/later.rs")) is False
        assert pinned.files() == [PurePosixPath("src/lib.rs")]
    finally:
        pinned.close()


def test_pinned_source_fails_loudly_on_an_unreadable_member(
    tmp_path: Path,
) -> None:
    # Regression: a failed `git ls-tree` used to yield an empty file list, so a
    # whole member left the census while the gate still reported a match --
    # observed for real when `make` ran under a different HOME and Git refused
    # `repos/metis` as dubiously owned. Silent member loss is the one outcome
    # this artifact exists to make impossible.
    not_a_repo = tmp_path / "m"
    not_a_repo.mkdir()

    with pytest.raises(SystemExit) as excinfo:
        PinnedSource(not_a_repo, "0" * 40)

    assert "ls-tree failed" in str(excinfo.value)
