"""Tests for the push-time bare-cast gate."""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import uuid

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "atlas_cast_gate.py"
_SPEC = importlib.util.spec_from_file_location("atlas_cast_gate", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
gate = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = gate
_SPEC.loader.exec_module(gate)

Site = gate.Site
Baseline = gate.Baseline


def site(package, path, line, column=9, width=8, line_end=None):
    """A site whose byte range is derived from its position, unique per position."""
    start = line * 1000 + column
    return Site(package, path, line, column, start, start + width,
                line if line_end is None else line_end)


def baseline(sanctioned=None, counts=None):
    return Baseline(
        {m: frozenset(p) for m, p in (sanctioned or {}).items()},
        counts or {},
    )


def test_added_lines_cover_each_hunk_and_ignore_deletions():
    diff = "\n".join([
        "diff --git a/src/lib.rs b/src/lib.rs",
        "--- a/src/lib.rs",
        "+++ b/src/lib.rs",
        "@@ -3,0 +4,2 @@ fn a() {",
        "+let x = 1;",
        "+let y = 2;",
        "@@ -10 +12 @@",
        "-old",
        "+new",
        "@@ -20,3 +21,0 @@",
        "-gone",
        "diff --git a/src/new.rs b/src/new.rs",
        "--- /dev/null",
        "+++ b/src/new.rs",
        "@@ -0,0 +1,3 @@",
        "diff --git a/src/dead.rs b/src/dead.rs",
        "--- a/src/dead.rs",
        "+++ /dev/null",
        "@@ -1,2 +0,0 @@",
    ])
    assert gate.added_lines(diff) == {
        "src/lib.rs": {4, 5, 12},
        "src/new.rs": {1, 2, 3},
    }


def test_an_added_line_that_reads_like_a_header_stays_content():
    diff = "\n".join([
        "diff --git a/src/lib.rs b/src/lib.rs",
        "--- a/src/lib.rs",
        "+++ b/src/lib.rs",
        "@@ -1,0 +2,1 @@",
        "+++ plus",
        "@@ -5,0 +7,1 @@",
        "+let z = 3;",
    ])
    assert gate.added_lines(diff) == {"src/lib.rs": {2, 7}}


def message(package_id, file_name, line, *, code=gate.LINT, primary=True, column=9,
            byte_start=None, byte_end=None, line_end=None):
    start = line * 1000 + column if byte_start is None else byte_start
    return json.dumps({
        "reason": "compiler-message",
        "package_id": package_id,
        "message": {
            "code": {"code": code},
            "spans": [{
                "file_name": file_name, "line_start": line,
                "column_start": column, "is_primary": primary,
                "byte_start": start, "byte_end": start + 8 if byte_end is None else byte_end,
                "line_end": line if line_end is None else line_end,
            }],
        },
    })


def test_sites_deduplicate_targets_and_drop_foreign_files(tmp_path):
    names = {"id-core": "core"}
    outside = tmp_path.parent / "dep" / "lib.rs"
    stream = [
        "Compiling core v0.1.0",
        message("id-core", "src/lib.rs", 7),
        message("id-core", "src/lib.rs", 7),  # same span, test target
        message("id-core", str(tmp_path / "src" / "ops.rs"), 3),
        message("id-core", "src/lib.rs", 9, code="clippy::cast_lossless"),
        message("id-core", "src/lib.rs", 11, primary=False),
        message("id-core", str(outside), 1),
        message("id-unknown", "src/lib.rs", 2),
        json.dumps({"reason": "compiler-artifact"}),
    ]
    assert gate.sites(stream, tmp_path, names) == {
        site("core", "src/lib.rs", 7),
        site("core", "src/ops.rs", 3),
    }


def test_a_site_records_where_its_span_ends(tmp_path):
    names = {"id-core": "core"}
    stream = [message("id-core", "src/lib.rs", 2, column=13, line_end=6)]
    (found,) = gate.sites(stream, tmp_path, names)
    assert (found.line, found.line_end) == (2, 6)


def test_clippy_lints_every_target_against_the_lock(tmp_path):
    assert gate.clippy_command(tmp_path, ["core", "ops"]) == [
        os.environ.get("CARGO") or "cargo", "clippy",
        "--manifest-path", str(tmp_path / "Cargo.toml"), "-p", "core", "-p", "ops",
        "--all-targets", "--locked", "--message-format=json",
        "--", "--force-warn", "clippy::as_conversions",
    ]


def test_a_standalone_manifest_is_linted_in_place(tmp_path):
    command = gate.clippy_command(tmp_path, [], manifest="fuzz/Cargo.toml")
    assert command[command.index("--manifest-path") + 1] == str(tmp_path / "fuzz" / "Cargo.toml")
    assert "--workspace" in command and "-p" not in command


def test_a_cargo_fuzz_crate_builds_with_the_fuzzing_cfg(monkeypatch):
    fuzz = [{"id": "f", "name": "f", "metadata": {"cargo-fuzz": True}}]
    plain = [{"id": "p", "name": "p", "metadata": None}, {"id": "q", "name": "q"}]
    monkeypatch.setenv("RUSTFLAGS", "-Dwarnings")
    assert gate.clippy_environment(fuzz)["RUSTFLAGS"] == "-Dwarnings --cfg fuzzing"
    assert gate.clippy_environment(plain)["RUSTFLAGS"] == "-Dwarnings"
    monkeypatch.delenv("RUSTFLAGS")
    assert gate.clippy_environment(fuzz)["RUSTFLAGS"] == "--cfg fuzzing"
    assert "RUSTFLAGS" not in gate.clippy_environment(plain)


def test_clippy_runs_a_fuzz_manifest_and_names_its_packages(tmp_path, monkeypatch):
    seen = tmp_path / "seen.txt"
    stub = tmp_path / "cargo_stub.py"
    stub.write_text(
        "import json, os, pathlib, sys\n"
        "manifest = sys.argv[sys.argv.index('--manifest-path') + 1]\n"
        "if 'metadata' in sys.argv and manifest.endswith('fuzz' + os.sep + 'Cargo.toml'):\n"
        "    print(json.dumps({'workspace_root': os.path.dirname(sys.argv[sys.argv.index('--manifest-path') + 1]), 'packages': [\n"
        "        {'id': 'id-fz', 'name': 'member-fuzz', 'metadata': {'cargo-fuzz': True}}]}))\n"
        "elif 'metadata' in sys.argv:\n"
        "    print(json.dumps({'workspace_root': os.path.dirname(sys.argv[sys.argv.index('--manifest-path') + 1]), 'packages': [{'id': 'id-root', 'name': 'root'}]}))\n"
        "else:\n"
        f"    pathlib.Path({str(seen)!r}).write_text(\n"
        "        sys.argv[sys.argv.index('--manifest-path') + 1] + '|' + os.environ.get('RUSTFLAGS', ''))\n"
    )
    monkeypatch.setattr(gate, "cargo", lambda config: [sys.executable, str(stub)])
    monkeypatch.delenv("RUSTFLAGS", raising=False)
    names = tmp_path / "names.txt"
    assert gate.main(["clippy", "--export", str(tmp_path), "--sites", str(tmp_path / "s.json"),
                      "--manifest", "fuzz/Cargo.toml", "--packages-out", str(names)]) == 0
    assert seen.read_text() == f"{tmp_path / 'fuzz' / 'Cargo.toml'}|--cfg fuzzing"
    assert names.read_text(encoding="utf-8") == "member-fuzz\n"


def test_a_failing_clippy_fails_the_step(tmp_path, monkeypatch):
    stub = tmp_path / "cargo_stub.py"
    stub.write_text(
        "import json, os, sys\n"
        "if 'metadata' in sys.argv:\n"
        "    print(json.dumps({'workspace_root': os.path.dirname(sys.argv[sys.argv.index('--manifest-path') + 1]), 'packages': [{'id': 'id-core', 'name': 'core'}]}))\n"
        "else:\n"
        "    sys.exit(101)\n"
    )
    monkeypatch.setattr(gate, "cargo", lambda config: [sys.executable, str(stub)])
    sites_file = tmp_path / "sites.json"
    assert gate.main(["clippy", "--export", str(tmp_path), "--sites", str(sites_file),
                      "-p", "core"]) == 101
    assert gate.read_sites(sites_file) == set()


def test_clippy_forwards_each_rendered_diagnostic(tmp_path, monkeypatch, capsys):
    record = json.loads(message("id-core", "src/lib.rs", 3))
    record["message"]["rendered"] = "warning: using a potentially dangerous silent `as` conversion\n"
    (tmp_path / "clippy.jsonl").write_text(json.dumps(record) + "\n")
    stub = tmp_path / "cargo_stub.py"
    stub.write_text(
        "import json, os, pathlib, sys\n"
        "if 'metadata' in sys.argv:\n"
        "    print(json.dumps({'workspace_root': os.path.dirname(sys.argv[sys.argv.index('--manifest-path') + 1]), 'packages': [{'id': 'id-core', 'name': 'core'}]}))\n"
        "else:\n"
        f"    print(pathlib.Path({str(tmp_path / 'clippy.jsonl')!r}).read_text(), end='')\n"
    )
    monkeypatch.setattr(gate, "cargo", lambda config: [sys.executable, str(stub)])
    status, found = gate.run_clippy(tmp_path, ["core"])
    assert status == 0
    assert found == {site("core", "src/lib.rs", 3)}
    assert "warning: using a potentially dangerous silent `as` conversion\n" in capsys.readouterr().err


def test_nested_casts_starting_together_are_two_sites(tmp_path):
    # `x as u32 as f64`: both spans start at one line and column.
    names = {"id-core": "core"}
    stream = [
        message("id-core", "src/lib.rs", 4, byte_start=30, byte_end=45),
        message("id-core", "src/lib.rs", 4, byte_start=30, byte_end=38),
    ]
    assert len(gate.sites(stream, tmp_path, names)) == 2


# A row with room to spare, so only the added-line check can fail.
ROOMY = baseline(counts={"m": {"core": 9}})


def test_a_cast_on_an_added_line_fails():
    found = {site("core", "src/lib.rs", 4)}
    problems = gate.violations("m", found, {"src/lib.rs": {4}}, ["core"], ROOMY)
    assert problems == ["src/lib.rs:4:9: bare `as` cast on a line this push adds"]


def test_a_cast_closing_a_multi_line_expression_fails_on_its_last_line():
    # `items` / `.iter()` / `.count() as u32`: the span starts at `items`.
    found = {site("core", "src/lib.rs", 2, 13, line_end=6)}
    problems = gate.violations("m", found, {"src/lib.rs": {6}}, ["core"], ROOMY)
    assert problems == ["src/lib.rs:2:13: bare `as` cast on a line this push adds"]
    assert gate.violations("m", found, {"src/lib.rs": {1, 7}}, ["core"], ROOMY) == []


def test_a_cast_starting_on_an_added_line_fails():
    found = {site("core", "src/lib.rs", 2, 13, line_end=6)}
    assert gate.violations("m", found, {"src/lib.rs": {2}}, ["core"], ROOMY) == [
        "src/lib.rs:2:13: bare `as` cast on a line this push adds"
    ]


def test_a_cast_in_a_sanctioned_module_passes():
    found = {site("core", "src/convert/count.rs", 4)}
    rules = baseline({"m": ["src/convert/count.rs"]}, {"m": {}})
    assert gate.violations("m", found, {"src/convert/count.rs": {4}}, ["core"], rules) == []


def test_an_untouched_cast_within_its_row_passes():
    found = {site("core", "src/lib.rs", 30), site("core", "src/lib.rs", 31)}
    rules = baseline(counts={"m": {"core": 2}})
    assert gate.violations("m", found, {"src/lib.rs": {4}}, ["core"], rules) == []


def test_a_count_above_its_row_fails_even_off_the_added_lines():
    found = {site("core", "src/lib.rs", 30), site("core", "src/lib.rs", 31)}
    rules = baseline(counts={"m": {"core": 1}})
    assert gate.violations("m", found, {}, ["core"], rules) == [
        "core: 2 bare `as` casts, above its baseline row of 1"
    ]


def test_a_package_without_a_row_counts_as_zero():
    found = {site("fresh", "src/lib.rs", 30)}
    rules = baseline(counts={"m": {"core": 5}})
    assert gate.violations("m", found, {}, ["fresh"], rules) == [
        "fresh: 1 bare `as` casts, above its baseline row of 0"
    ]


def test_each_package_is_held_to_its_own_row():
    found = {site("core", "src/lib.rs", 1), site("ops", "src/x.rs", 1)}
    rules = baseline(counts={"m": {"core": 1, "ops": 1}})
    assert gate.violations("m", found, {}, ["core", "ops"], rules) == []


def test_only_pushed_packages_are_counted():
    found = {site("core", "src/lib.rs", 1), site("other", "src/x.rs", 1)}
    rules = baseline(counts={"m": {"core": 1}})
    assert gate.violations("m", found, {}, ["core"], rules) == []


def test_two_casts_on_one_line_count_twice():
    found = {site("core", "src/lib.rs", 4, 9), site("core", "src/lib.rs", 4, 30)}
    rules = baseline(counts={"m": {"core": 1}})
    assert gate.violations("m", found, {}, ["core"], rules) == [
        "core: 2 bare `as` casts, above its baseline row of 1"
    ]


def test_an_unmeasured_member_counts_every_package_as_zero():
    found = {site("core", "src/lib.rs", 30)}
    assert gate.violations("m", found, {}, ["core"], baseline()) == [
        "core: 1 bare `as` casts, above its baseline row of 0"
    ]


def test_sites_round_trip_through_their_file(tmp_path):
    found = {site("core", "src/lib.rs", 7), site("ops", "src/x.rs", 1, 2)}
    path = tmp_path / "sites.json"
    gate.write_sites(path, found)
    assert gate.read_sites(path) == found


def test_counts_exclude_sanctioned_modules():
    found = {
        site("core", "src/lib.rs", 1, 1),
        site("core", "src/convert/count.rs", 1, 1),
        site("ops", "src/x.rs", 2, 1),
    }
    assert gate.counts(found, frozenset({"src/convert/count.rs"})) == {"core": 1, "ops": 1}


@pytest.mark.parametrize("rows", [
    '[["core", "src/lib.rs", 4]]',
    '[["core", "src/lib.rs", "4", 9, 4009, 4017, 4]]',
    '[["core", "src/lib.rs", true, 9, 4009, 4017, 4]]',
])
def test_a_malformed_sites_file_cannot_run(tmp_path, capsys, rows):
    sites_file = tmp_path / "sites.json"
    sites_file.write_text(rows)
    rules = tmp_path / "baseline.json"
    rules.write_text('{"sanctioned": {}, "counts": {}}')
    status = gate.main(["--baseline", str(rules), "check", "--member", "m",
                        "--repo", str(tmp_path), "--tip", "HEAD",
                        "--package", "core", "--sites", str(sites_file)])
    assert status == 2
    assert "cast gate: could not run: ValueError" in capsys.readouterr().err


@pytest.mark.parametrize("text", [
    '{"sanctioned": {}, "counts": {"m": 5}}',
    '{"sanctioned": {"m": "src/convert.rs"}, "counts": {}}',
    '{"sanctioned": {"m": [5]}, "counts": {}}',
    '{"sanctioned": {}, "counts": {"m": {"core": "3"}}}',
    '{"sanctioned": {}, "counts": {"m": {"core": true}}}',
])
def test_a_malformed_baseline_cannot_run(tmp_path, capsys, text):
    sites_file = tmp_path / "sites.json"
    sites_file.write_text("[]")
    rules = tmp_path / "baseline.json"
    rules.write_text(text)
    status = gate.main(["--baseline", str(rules), "check", "--member", "m",
                        "--repo", str(tmp_path), "--tip", "HEAD",
                        "--package", "core", "--sites", str(sites_file)])
    assert status == 2
    assert "cast gate: could not run: ValueError" in capsys.readouterr().err


GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}
for _key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
    GIT_ENV.pop(_key, None)


def git(repo: pathlib.Path, *argv: str) -> str:
    return subprocess.run(["git", *argv], cwd=repo, env=GIT_ENV, capture_output=True,
                          text=True, check=True).stdout.strip()


def commit(repo: pathlib.Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def init(repo: pathlib.Path) -> None:
    repo.mkdir(parents=True)
    git(repo, "init", "-q")


OLD = "pub fn a(x: u32) -> u64 {\n    x as u64\n}\n\npub fn b() {}\n"


def test_pushed_additions_reads_the_pushed_direction(tmp_path):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "lib.rs").write_text(OLD)
    base = commit(repo, "base")
    (repo / "lib.rs").write_text(OLD + "pub fn c() {}\n")
    tip = commit(repo, "add")
    assert gate.pushed_additions(repo, base, tip) == {"lib.rs": {6}}


def test_a_moved_file_adds_only_the_lines_the_move_changed(tmp_path):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "src").mkdir()
    (repo / "src" / "old.rs").write_text(OLD)
    base = commit(repo, "base")
    git(repo, "mv", "src/old.rs", "src/new.rs")
    (repo / "src" / "new.rs").write_text(OLD + "pub fn c() {}\n")
    tip = commit(repo, "move")
    assert gate.pushed_additions(repo, base, tip) == {"src/new.rs": {6}}


@pytest.mark.parametrize("key,value", [
    ("diff.dstPrefix", "new/"),
    ("diff.noprefix", "true"),
])
def test_diff_prefix_configuration_does_not_hide_additions(tmp_path, key, value):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "src").mkdir()
    (repo / "src" / "lib.rs").write_text(OLD)
    base = commit(repo, "base")
    (repo / "src" / "lib.rs").write_text(OLD + "pub fn c() {}\n")
    tip = commit(repo, "add")
    git(repo, "config", key, value)
    assert gate.pushed_additions(repo, base, tip) == {"src/lib.rs": {6}}


TEN = "".join(f"pub fn f{n}() {{}}\n" for n in range(1, 11))


def test_hunk_merging_settings_do_not_widen_the_additions(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "lib.rs").write_text(TEN)
    base = commit(repo, "base")
    lines = TEN.splitlines(keepends=True)
    lines[1:1] = ["pub fn x() {}\n"]
    lines[5:5] = ["pub fn y() {}\n"]
    (repo / "lib.rs").write_text("".join(lines))
    tip = commit(repo, "two additions")
    git(repo, "config", "diff.interHunkContext", "5")
    monkeypatch.setenv("GIT_DIFF_OPTS", "-u3")
    assert gate.pushed_additions(repo, base, tip) == {"lib.rs": {2, 6}}


ADDED = "pub fn c(x: u8) -> u32 { x as u32 }\n"


@pytest.mark.parametrize("setup", ["info-binary", "committed-no-diff", "nul-byte",
                                   "external-diff", "textconv"])
def test_no_attribute_or_driver_hides_an_addition(tmp_path, setup):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "lib.rs").write_text(OLD)
    base = commit(repo, "base")
    added = OLD + ADDED
    if setup == "nul-byte":
        added = OLD.replace("pub fn b() {}", 'pub fn b() { let _ = "\0"; }') + ADDED
    if setup == "committed-no-diff":
        (repo / ".gitattributes").write_text("*.rs -diff\n")
    (repo / "lib.rs").write_text(added)
    tip = commit(repo, "add")
    if setup == "info-binary":
        (repo / ".git" / "info" / "attributes").write_text("*.rs binary\n")
    if setup == "external-diff":
        git(repo, "config", "diff.external", "false")
    if setup == "textconv":
        (repo / ".git" / "info" / "attributes").write_text("*.rs diff=hide\n")
        git(repo, "config", "diff.hide.textconv", "true")
    additions = gate.pushed_additions(repo, base, tip)
    assert 6 in additions["lib.rs"]


def test_moves_beyond_the_rename_limit_still_pair(tmp_path):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "a").mkdir()
    (repo / "a" / "one.rs").write_text(TEN)
    (repo / "a" / "two.rs").write_text(TEN.replace("f", "g"))
    base = commit(repo, "base")
    # Renamed basenames: same-name moves pair outside the limit, these do not.
    (repo / "b").mkdir()
    git(repo, "mv", "a/one.rs", "b/uno.rs")
    git(repo, "mv", "a/two.rs", "b/dos.rs")
    (repo / "b" / "uno.rs").write_text(TEN + "pub fn z() {}\n")
    (repo / "b" / "dos.rs").write_text(TEN.replace("f", "g") + "pub fn z() {}\n")
    tip = commit(repo, "move both")
    git(repo, "config", "diff.renameLimit", "1")
    assert gate.pushed_additions(repo, base, tip) == {"b/uno.rs": {11}, "b/dos.rs": {11}}


@pytest.mark.parametrize("separator", [" ", "\x0c", "\r", "\x0b", "\x1c", "\x85"])
def test_a_line_separator_inside_source_is_not_a_line_break(tmp_path, separator):
    # Two hunks, unchanged lines between: a spoofed file header inside the
    # first would hide the second, the cast at line 17.
    repo = tmp_path / "repo"
    init(repo)
    filler = "".join(f"pub fn g{n}() {{}}\n" for n in range(10))
    (repo / "lib.rs").write_bytes((OLD + filler).encode())
    base = commit(repo, "base")
    spoof = f"// note{separator}diff --git a/x b/x{separator}@@ -1 +1,20 @@\n"
    (repo / "lib.rs").write_bytes((OLD + spoof + filler + ADDED).encode())
    tip = commit(repo, "add")
    assert gate.pushed_additions(repo, base, tip) == {"lib.rs": {6, 17}}


def test_the_diff_algorithm_is_pinned(tmp_path):
    # Eight functions reordered: histogram marks other lines added than myers.
    repo = tmp_path / "repo"
    init(repo)
    names = [f"fn f{n}() {{}}\n" for n in range(8)]
    (repo / "lib.rs").write_text("".join(names))
    base = commit(repo, "base")
    (repo / "lib.rs").write_text("".join(names[n] for n in (4, 1, 5, 2, 0, 3, 7, 6)))
    tip = commit(repo, "reorder")
    git(repo, "config", "diff.algorithm", "histogram")
    assert gate.pushed_additions(repo, base, tip) == {"lib.rs": {1, 3, 5, 8}}


def test_a_non_ascii_path_keeps_its_name(tmp_path):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "ünicode.rs").write_text(OLD)
    base = commit(repo, "base")
    (repo / "ünicode.rs").write_text(OLD + "pub fn c() {}\n")
    tip = commit(repo, "add")
    git(repo, "config", "core.quotePath", "true")
    assert gate.pushed_additions(repo, base, tip) == {"ünicode.rs": {6}}


def test_a_path_with_a_space_keeps_its_name(tmp_path):
    # git ends a `+++` header whose path holds a space with a tab.
    repo = tmp_path / "repo"
    init(repo)
    (repo / "my mod.rs").write_text(OLD)
    base = commit(repo, "base")
    (repo / "my mod.rs").write_text(OLD + "pub fn c() {}\n")
    tip = commit(repo, "add")
    assert gate.pushed_additions(repo, base, tip) == {"my mod.rs": {6}}


def test_check_judges_a_pushed_range_end_to_end(tmp_path):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "src").mkdir()
    (repo / "src" / "lib.rs").write_text(OLD)
    base = commit(repo, "base")
    (repo / "src" / "lib.rs").write_text(OLD + "pub fn c(x: u8) -> u32 { x as u32 }\n")
    tip = commit(repo, "add a cast")
    rules = tmp_path / "baseline.json"
    rules.write_text('{"sanctioned": {}, "counts": {"m": {"core": 9}}}')

    def judge(found):
        sites_file = tmp_path / "sites.json"
        gate.write_sites(sites_file, found)
        return gate.main(["--baseline", str(rules), "check", "--member", "m",
                          "--repo", str(repo), "--base", base, "--tip", tip,
                          "--package", "core", "--sites", str(sites_file)])

    assert judge({site("core", "src/lib.rs", 2)}) == 0
    assert judge({site("core", "src/lib.rs", 2), site("core", "src/lib.rs", 6, 26)}) == 1


def test_a_count_above_its_base_fails_within_its_row():
    tip = {site("core", "src/a.rs", 1), site("core", "src/a.rs", 2)}
    base = {site("core", "src/b.rs", 1)}
    problems = gate.violations("m", tip, {}, ["core"], baseline(counts={"m": {"core": 9}}), base,
                               ["core"])
    assert problems == ["core: 2 bare `as` casts, up from 1 at the pushed base"]


def test_a_base_with_no_casts_still_counts():
    # A file of casts moved into a package whose base held none.
    tip = {site("core", "src/moved.rs", 1)}
    problems = gate.violations("m", tip, {}, ["core"], baseline(counts={"m": {"core": 9}}),
                               set(), ["core"])
    assert problems == ["core: 1 bare `as` casts, up from 0 at the pushed base"]


def test_only_the_named_packages_are_held_to_the_base():
    tip = {site("a", "a/x.rs", 1), site("b", "b/x.rs", 1)}
    rules = baseline(counts={"m": {"a": 9, "b": 9}})
    assert gate.violations("m", tip, {}, ["a", "b"], rules, set(), ["b"]) == [
        "b: 1 bare `as` casts, up from 0 at the pushed base"]


def test_a_count_equal_to_its_base_passes():
    tip = {site("core", "src/a.rs", 1)}
    base = {site("core", "src/b.rs", 7)}
    assert gate.violations("m", tip, {}, ["core"], baseline(counts={"m": {"core": 9}}), base,
                           ["core"]) == []


def test_without_a_base_only_the_row_counts():
    tip = {site("core", "src/a.rs", 1), site("core", "src/a.rs", 2)}
    assert gate.violations("m", tip, {}, ["core"], baseline(counts={"m": {"core": 9}})) == []


def test_the_base_count_excludes_sanctioned_modules():
    tip = {site("core", "src/a.rs", 1)}
    base = {site("core", "src/convert.rs", 1)}
    rules = baseline(sanctioned={"m": ["src/convert.rs"]}, counts={"m": {"core": 9}})
    assert gate.violations("m", tip, {}, ["core"], rules, base, ["core"]) == [
        "core: 1 bare `as` casts, up from 0 at the pushed base"]


def test_each_package_is_held_to_its_own_base():
    tip = {site("a", "a/x.rs", 1), site("b", "b/x.rs", 1)}
    base = {site("a", "a/x.rs", 1)}
    rules = baseline(counts={"m": {"a": 9, "b": 9}})
    assert gate.violations("m", tip, {}, ["a", "b"], rules, base, ["a", "b"]) == [
        "b: 1 bare `as` casts, up from 0 at the pushed base"]


def test_check_reads_the_base_sites(tmp_path):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "src").mkdir()
    (repo / "src" / "lib.rs").write_text(OLD)
    base = commit(repo, "base")
    (repo / "src" / "lib.rs").write_text(OLD + "pub fn c() {}\n")
    tip = commit(repo, "add")
    rules = tmp_path / "baseline.json"
    rules.write_text('{"sanctioned": {}, "counts": {"m": {"core": 9}}}')
    tip_sites, base_sites = tmp_path / "tip.json", tmp_path / "base.json"
    gate.write_sites(tip_sites, {site("core", "src/lib.rs", 2), site("core", "src/lib.rs", 3)})
    gate.write_sites(base_sites, {site("core", "src/lib.rs", 2)})
    argv = ["--baseline", str(rules), "check", "--member", "m", "--repo", str(repo),
            "--base", base, "--tip", tip, "--package", "core", "--sites", str(tip_sites)]
    assert gate.main(argv) == 0
    assert gate.main([*argv, "--base-sites", str(base_sites)]) == 0
    assert gate.main([*argv, "--base-sites", str(base_sites), "--base-package", "core"]) == 1


def test_base_triggers_name_moves_and_build_inputs(tmp_path, capsys):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "a" / "src").mkdir(parents=True)
    (repo / "b" / "src").mkdir(parents=True)
    body = "".join(f"pub fn f{i}(x: u16) -> u8 {{ x as u8 }}\n" for i in range(8))
    (repo / "a" / "src" / "moved.rs").write_text(body)
    (repo / "a" / "Cargo.toml").write_text('[package]\nname = "a"\n')
    (repo / "a" / "src" / "lib.rs").write_text("pub fn a() {}\n")
    first = commit(repo, "base")

    (repo / "a" / "src" / "lib.rs").write_text("pub fn a() {}\npub fn a2() {}\n")
    (repo / "a" / "README.md").write_text("beside the manifest, not a build input\n")
    edited = commit(repo, "a plain source edit")
    assert gate.base_triggers(repo, first, edited) == []

    subprocess.run(["git", "mv", "a/src/moved.rs", "b/src/moved.rs"], cwd=repo,
                   env=GIT_ENV, check=True)
    moved = commit(repo, "move")
    assert gate.base_triggers(repo, edited, moved) == ["a/src/moved.rs -> b/src/moved.rs"]

    (repo / "a" / "Cargo.toml").write_text('[package]\nname = "a"\n[features]\nx = []\n')
    (repo / "a" / "build.rs").write_text("fn main() {}\n")
    (repo / "b" / "src" / "build.rs").write_text("pub fn module() {}\n")
    (repo / ".cargo").mkdir()
    (repo / ".cargo" / "config.toml").write_text("[build]\n")
    (repo / "rust-toolchain.toml").write_text('[toolchain]\nchannel = "1.97.0"\n')
    built = commit(repo, "build inputs")
    # `b/src/build.rs` has no manifest beside it: an ordinary module.
    assert gate.base_triggers(repo, moved, built) == [
        ".cargo/config.toml changed", "a/Cargo.toml changed", "a/build.rs changed",
        "rust-toolchain.toml changed"]

    assert gate.main(["base-triggers", "--repo", str(repo), "--base", edited,
                      "--tip", moved]) == 0
    assert capsys.readouterr().out == "a/src/moved.rs -> b/src/moved.rs\n"


def test_base_triggers_at_the_root_and_nested(tmp_path):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "Cargo.toml").write_text('[package]\nname = "r"\n')
    (repo / "crates" / "y").mkdir(parents=True)
    (repo / "crates" / "y" / "notes.txt").write_text("".join(f"line {i}\n" for i in range(20)))
    first = commit(repo, "base")
    (repo / "build.rs").write_text("fn main() {}\n")
    (repo / "rust-toolchain").write_text("1.97.0\n")
    (repo / "crates" / "y" / ".cargo").mkdir()
    subprocess.run(["git", "mv", "crates/y/notes.txt", "crates/y/.cargo/config.toml"],
                   cwd=repo, env=GIT_ENV, check=True)
    tip = commit(repo, "root build script, bare toolchain pin, nested config by rename")
    # A rename names both ends, and its destination is a build input too.
    assert gate.base_triggers(repo, first, tip) == [
        "build.rs changed",
        "crates/y/notes.txt -> crates/y/.cargo/config.toml",
        "crates/y/.cargo/config.toml changed",
        "rust-toolchain changed"]


def baseline_text(counts, sanctioned=None):
    return json.dumps({"sanctioned": sanctioned or {}, "counts": counts})


def test_the_ratchet_lets_rows_fall_and_members_enter():
    base = gate.Baseline.parse(baseline_text({"m": {"a": 3, "b": 2}}, {"m": ["x.rs"]}), "base")
    fell = gate.Baseline.parse(baseline_text({"m": {"a": 1}, "n": {"c": 9}},
                                             {"m": ["x.rs"], "n": ["y.rs"]}), "tip")
    assert gate.raised_rows(base, fell) == []


def test_the_ratchet_refuses_raises_new_rows_and_sanctioned_paths():
    base = gate.Baseline.parse(baseline_text({"m": {"a": 3}}, {"m": ["x.rs"]}), "base")
    tip = gate.Baseline.parse(baseline_text({"m": {"a": 4, "b": 1}}, {"m": ["x.rs", "z.rs"]}),
                              "tip")
    assert gate.raised_rows(base, tip) == [
        "m/a rises from 3 to 4", "m/b rises from 0 to 1", "m sanctions z.rs, which the base does not"]


def test_the_ratchet_reads_the_committed_baseline(tmp_path, capsys):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "scripts").mkdir()
    target = repo / "scripts" / "cast-baseline.json"
    (repo / "README").write_text("before the gate\n")
    empty = commit(repo, "no baseline")
    target.write_text(baseline_text({"m": {"a": 3}}))
    first = commit(repo, "baseline")
    assert gate.main(["ratchet", "--repo", str(repo), "--base", empty, "--tip", first]) == 0
    target.write_text(baseline_text({"m": {"a": 2}}))
    fell = commit(repo, "fall")
    assert gate.main(["ratchet", "--repo", str(repo), "--base", first, "--tip", fell]) == 0
    target.write_text(baseline_text({"m": {"a": 5}}))
    rose = commit(repo, "rise")
    capsys.readouterr()
    assert gate.main(["ratchet", "--repo", str(repo), "--base", fell, "--tip", rose]) == 1
    assert "m/a rises from 2 to 5; rows only fall" in capsys.readouterr().err
    subprocess.run(["git", "rm", "-q", "scripts/cast-baseline.json"], cwd=repo, env=GIT_ENV,
                   check=True)
    gone = commit(repo, "delete")
    assert gate.main(["ratchet", "--repo", str(repo), "--base", rose, "--tip", gone]) == 1
    assert gate.main(["ratchet", "--repo", str(repo), "--base", "f" * 40, "--tip", gone]) == 2


def test_base_triggers_print_paths_outside_the_code_page(tmp_path):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "a").mkdir()
    (repo / "a" / "x.rs").write_text("pub fn x(v: u16) -> u8 { v as u8 }\n")
    first = commit(repo, "base")
    (repo / "c d").mkdir()
    subprocess.run(["git", "mv", "a/x.rs", "c d/\u6570\u636e.rs"], cwd=repo, env=GIT_ENV,
                   check=True)
    moved = commit(repo, "move")
    script = pathlib.Path(gate.__file__)
    run = subprocess.run(
        [sys.executable, str(script), "base-triggers", "--repo", str(repo),
         "--base", first, "--tip", moved],
        capture_output=True, env={**os.environ, "PYTHONIOENCODING": "cp1252"})
    assert run.returncode == 0, run.stderr
    assert run.stdout.decode("utf-8") == "a/x.rs -> c d/\u6570\u636e.rs\n"


def test_a_span_resolves_against_its_workspace_root(tmp_path):
    crate = tmp_path / "fuzz"
    records = [message("id-fz", "fuzz_targets/one.rs", 4)]
    found = gate.sites(records, tmp_path, {"id-fz": "fz"}, crate)
    assert found == {site("fz", "fuzz/fuzz_targets/one.rs", 4)}


def test_a_base_without_the_manifest_counts_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "cargo", lambda config: pytest.fail("cargo ran"))
    sites_file = tmp_path / "sites.json"
    assert gate.main(["clippy", "--export", str(tmp_path), "--sites", str(sites_file),
                      "--manifest", "fuzz/Cargo.toml", "--present-only"]) == 0
    assert gate.read_sites(sites_file) == set()


def test_a_base_runs_only_the_packages_it_has(tmp_path, monkeypatch):
    (tmp_path / "Cargo.toml").write_text("[workspace]\n")
    seen = tmp_path / "seen.txt"
    stub = tmp_path / "cargo_stub.py"
    stub.write_text(
        "import json, os, pathlib, sys\n"
        "if 'metadata' in sys.argv:\n"
        f"    print(json.dumps({{'workspace_root': {str(tmp_path)!r}, 'packages': [\n"
        "        {'id': 'id-core', 'name': 'core'}]}))\n"
        "else:\n"
        f"    pathlib.Path({str(seen)!r}).write_text(' '.join(sys.argv[2:]))\n"
    )
    monkeypatch.setattr(gate, "cargo", lambda config: [sys.executable, str(stub)])
    sites_file = tmp_path / "sites.json"
    argv = ["clippy", "--export", str(tmp_path), "--sites", str(sites_file), "--present-only"]
    assert gate.main([*argv, "-p", "core", "-p", "new"]) == 0
    assert "-p core" in seen.read_text() and "new" not in seen.read_text()
    seen.unlink()
    assert gate.main([*argv, "-p", "new"]) == 0
    assert not seen.exists()
    assert gate.read_sites(sites_file) == set()
    # No selection is the whole workspace, at the base as at the tip.
    assert gate.main(argv) == 0
    assert "-p" not in seen.read_text().split()


def test_new_history_adds_every_line(tmp_path):
    repo = tmp_path / "repo"
    init(repo)
    (repo / "lib.rs").write_text(OLD)
    tip = commit(repo, "root")
    assert gate.pushed_additions(repo, None, tip) == {"lib.rs": {1, 2, 3, 4, 5}}


def shared_target() -> pathlib.Path | None:
    """The stack's one build cache, so the fixture builds into no private one.

    `CARGO_TARGET_DIR` when set, else `target/` beside the checkout's common
    git directory -- the primary checkout's cache, from a linked worktree too.
    """
    if os.environ.get("CARGO_TARGET_DIR"):
        return pathlib.Path(os.environ["CARGO_TARGET_DIR"])
    found = subprocess.run(
        ["git", "-C", str(SCRIPT.parent), "rev-parse", "--path-format=absolute",
         "--git-common-dir"], capture_output=True, text=True,
    )
    if found.returncode != 0:
        return None
    return pathlib.Path(found.stdout.strip()).parent / "target"


MANIFEST = '[package]\nname = "{name}"\nversion = "0.1.0"\nedition = "2021"\n\n[workspace]\n'
CHAIN = (
    "pub fn positives(v: &[u8]) -> u64 {\n"
    "    let k: u64 = v\n"
    "        .iter()\n"
    "        .filter(|b| **b > 0)\n"
    "        .map(|_| 1)\n"
    "        .sum();\n"
    "    k\n"
    "}\n"
)
BASE_LIB = (
    "pub mod convert;\n\n"
    "pub fn widen(x: u32) -> u64 {\n    x as u64\n}\n\n"
) + CHAIN
CONVERT = "pub fn narrow(x: u64) -> u32 {\n    x as u32\n}\n"
EXTRA = "pub fn shrink(x: u64) -> u16 {\n    x as u16\n}\n"


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("cargo") is None, reason="needs cargo with clippy")
def test_the_gate_judges_a_real_clippy_run(tmp_path):
    shared = shared_target()
    if shared is None:
        pytest.skip("no shared target: set CARGO_TARGET_DIR or run from a checkout")
    repo = tmp_path / "member"
    init(repo)
    (repo / "src").mkdir()
    # A name of its own: path sources hash relative to their workspace, so a
    # shared name would make every run's fixture one unit in the shared
    # target, and a concurrent run's newer build could pass for this one's.
    name = f"castgate_fixture_{uuid.uuid4().hex[:12]}"
    (repo / "Cargo.toml").write_text(MANIFEST.format(name=name))
    (repo / "src" / "lib.rs").write_text(BASE_LIB)
    (repo / "src" / "convert.rs").write_text(CONVERT)
    (repo / "src" / "extra.rs").write_text(EXTRA)  # not yet a module: not compiled
    subprocess.run(["cargo", "generate-lockfile", "--offline"], cwd=repo, check=True,
                   capture_output=True)
    first = commit(repo, "base")
    config = tmp_path / "gate-config.toml"
    target = shared.as_posix()
    config.write_text(f"[build]\ntarget-dir = {json.dumps(target)}\n")

    def run(base: str, tip: str, row: int) -> int:
        rules = tmp_path / f"baseline-{row}.json"
        rules.write_text(json.dumps({
            "sanctioned": {"member": ["src/convert.rs"]},
            "counts": {"member": {name: row}},
        }))
        export = tmp_path / f"export-{tip[:12]}"
        if not export.exists():
            # A tree, not a commit: files stamped now, not at the commit time,
            # so cargo cannot take this run's earlier build of the fixture as
            # fresh and replay its diagnostics.
            archive = subprocess.run(["git", "archive", f"{tip}^{{tree}}"], cwd=repo,
                                     env=GIT_ENV, capture_output=True, check=True).stdout
            export.mkdir()
            subprocess.run(["tar", "-x", "-C", str(export)], input=archive, check=True)
            # Tar stamps whole seconds: an export made in the second the last
            # build finished would read as older than that build's output.
            for path in export.rglob("*"):
                os.utime(path)
        found = tmp_path / f"sites-{tip[:12]}.json"
        assert gate.main([
            "--cargo-config", str(config), "clippy", "--export", str(export),
            "--sites", str(found), "--package", name,
        ]) == 0
        return gate.main([
            "--baseline", str(rules), "check", "--member", "member",
            "--repo", str(repo), "--base", base, "--tip", tip,
            "--package", name, "--sites", str(found),
        ])

    # A line added beside an untouched cast: with zero context the cast's
    # line is not added, so only a widened diff would refuse this.
    (repo / "src" / "lib.rs").write_text(BASE_LIB.replace(
        "    x as u64\n", "    x as u64\n}\n\npub fn keep() {\n"))
    beside = commit(repo, "a line beside a cast")
    assert run(first, beside, row=10) == 0

    # Declaring a module that already holds a cast adds no cast line; only
    # the count against its row can refuse it.
    (repo / "src" / "lib.rs").write_text(
        "pub mod extra;\n" + (repo / "src" / "lib.rs").read_text())
    declared = commit(repo, "declare a module holding a cast")
    assert run(beside, declared, row=10) == 0
    assert run(beside, declared, row=1) == 1

    # A cast in the sanctioned conversion module neither counts nor fails.
    (repo / "src" / "convert.rs").write_text(
        CONVERT + "\npub fn count(n: usize) -> f64 {\n    n as f64\n}\n")
    sanctioned = commit(repo, "a cast in the conversion module")
    assert run(declared, sanctioned, row=2) == 0

    # A bare cast on an added line fails however much room its row leaves.
    (repo / "src" / "lib.rs").write_text((repo / "src" / "lib.rs").read_text()
                                         + "\npub fn halve(x: u64) -> u32 {\n    (x / 2) as u32\n}\n")
    added = commit(repo, "a bare cast")
    assert run(sanctioned, added, row=10) == 1

    # A cast closing a method chain: clippy's span starts at `v`, lines above
    # the one added line, so only the span's end puts it on the push.
    (repo / "src" / "lib.rs").write_text((repo / "src" / "lib.rs").read_text().replace(
        "        .map(|_| 1)\n        .sum();\n", "        .count() as u64;\n"))
    chained = commit(repo, "a cast closing a chain")
    assert run(added, chained, row=10) == 1


WORKSPACE = '[workspace]\nmembers = ["a", "b"]\nexclude = ["fuzz"]\nresolver = "2"\n'
CRATE = '[package]\nname = "{name}"\nversion = "0.1.0"\nedition = "2021"\n'
MOVED = "pub fn one(x: u32) -> u64 {\n    x as u64\n}\n\npub fn two(x: u64) -> u32 {\n    x as u32\n}\n"
FUZZ_LIB = "pub fn wide(x: u8) -> u16 {\n    x as u16\n}\n"


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("cargo") is None, reason="needs cargo with clippy")
def test_the_gate_counts_moves_and_reads_standalone_crates(tmp_path):
    shared = shared_target()
    if shared is None:
        pytest.skip("no shared target: set CARGO_TARGET_DIR or run from a checkout")
    repo = tmp_path / "member"
    init(repo)
    tag = uuid.uuid4().hex[:12]
    a, b, fz = f"castgate_a_{tag}", f"castgate_b_{tag}", f"castgate_fz_{tag}"
    (repo / "Cargo.toml").write_text(WORKSPACE)
    for directory, name, lib in (("a", a, "pub mod moved;\n"), ("b", b, "pub fn b() {}\n")):
        (repo / directory / "src").mkdir(parents=True)
        (repo / directory / "Cargo.toml").write_text(CRATE.format(name=name))
        (repo / directory / "src" / "lib.rs").write_text(lib)
    (repo / "a" / "src" / "moved.rs").write_text(MOVED)
    (repo / "fuzz" / "src").mkdir(parents=True)
    (repo / "fuzz" / "Cargo.toml").write_text(CRATE.format(name=fz) + "\n[workspace]\n")
    (repo / "fuzz" / "src" / "lib.rs").write_text(FUZZ_LIB)
    for directory in (repo, repo / "fuzz"):
        subprocess.run(["cargo", "generate-lockfile", "--offline"], cwd=directory,
                       check=True, capture_output=True)
    first = commit(repo, "base")
    config = tmp_path / "gate-config.toml"
    config.write_text(f"[build]\ntarget-dir = {json.dumps(shared.as_posix())}\n")
    rules = tmp_path / "baseline.json"
    rules.write_text(json.dumps({"sanctioned": {}, "counts": {"member": {a: 10, b: 10, fz: 10}}}))

    def export(rev: str) -> pathlib.Path:
        out = tmp_path / f"export-{rev[:12]}"
        if not out.exists():
            archive = subprocess.run(["git", "archive", f"{rev}^{{tree}}"], cwd=repo,
                                     env=GIT_ENV, capture_output=True, check=True).stdout
            out.mkdir()
            subprocess.run(["tar", "-x", "-C", str(out)], input=archive, check=True)
            for path in out.rglob("*"):
                os.utime(path)
        return out

    def sites_of(rev: str, packages: list[str], manifest: str, base: bool) -> pathlib.Path:
        found = tmp_path / f"sites-{rev[:12]}-{manifest.replace('/', '-')}.json"
        argv = ["--cargo-config", str(config), "clippy", "--export", str(export(rev)),
                "--sites", str(found), "--manifest", manifest]
        for package in packages:
            argv += ["-p", package]
        assert gate.main([*argv, *(["--present-only"] if base else [])]) == 0
        return found

    def judge(base: str, tip: str, packages: list[str], manifest: str, with_base: bool) -> int:
        argv = ["--baseline", str(rules), "check", "--member", "member", "--repo", str(repo),
                "--base", base, "--tip", tip,
                "--sites", str(sites_of(tip, packages if manifest == "Cargo.toml" else [],
                                        manifest, False))]
        for package in packages:
            argv += ["--package", package]
        if with_base:
            argv += ["--base-sites", str(sites_of(base, packages if manifest == "Cargo.toml" else [],
                                                  manifest, True))]
            for package in packages:
                argv += ["--base-package", package]
        return gate.main(argv)

    # A file holding two casts moves from `a` to `b`. The rename pairs, so no
    # cast line is added, and `b` stays under its row: only the count against
    # the base, measured with the same selection, refuses it.
    subprocess.run(["git", "mv", "a/src/moved.rs", "b/src/moved.rs"], cwd=repo,
                   env=GIT_ENV, check=True)
    (repo / "a" / "src" / "lib.rs").write_text("pub fn a() {}\n")
    (repo / "b" / "src" / "lib.rs").write_text("pub fn b() {}\npub mod moved;\n")
    moved = commit(repo, "move a file of casts across packages")
    assert judge(first, moved, [a, b], "Cargo.toml", with_base=False) == 0
    assert judge(first, moved, [a, b], "Cargo.toml", with_base=True) == 1

    # A standalone crate names its spans from its own root; a cast added to it
    # is on a line the push adds.
    (repo / "fuzz" / "src" / "lib.rs").write_text(
        FUZZ_LIB + "\npub fn narrow(x: u16) -> u8 {\n    x as u8\n}\n")
    fuzzed = commit(repo, "a cast in the standalone crate")
    assert judge(moved, fuzzed, [fz], "fuzz/Cargo.toml", with_base=False) == 1
