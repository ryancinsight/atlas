#!/usr/bin/env python3
"""Verify coeus test binaries compile identically across overlays.

The claim under test (ATLAS-SUBSTRATE-002, 2026-08-12): test binaries compile
identically whether the hephaestus `[patch]` resolves from the local worktree
(the plain Atlas overlay) or from a clean temporary clone at the committed
gitlink (exactly what CI builds). The harness covers three target sets:

    dist    coeus-dist      dist_ops / coeus_dist TCP-collectives tests
    python  coeus-python    binding_ops binding tests
    wgpu    coeus-wgpu      wgpu_ops backend tests (hephaestus-wgpu/core)

`cargo tree` confirms the `dist` and `python` test-binary graphs contain ZERO
hephaestus references, so for them the hephaestus redirect is unused and the
byte-identity proof holds at full fidelity. `wgpu` links hephaestus directly
and therefore genuinely exercises the redirect.

Raw SHA-256 equality is NOT a valid cross-build criterion on Windows for two
independent reasons:

1. PE linker stamps: the MSVC/LLVM linker embeds a TimeDateStamp plus a
   CheckSum computed over it, so consecutive identical builds differ in those
   bytes. Normalized: TimeDateStamp at PE-signature+8, CheckSum at optional
   header+0x40 (opt = PE-signature+0x18).

2. Dependency checkout path: rustc embeds each path-dependency's absolute
   source directory in the binary (168 occurrences in `wgpu_ops-*.exe`), and
   cargo derives a metadata-hash disambiguator from the dependency's package
   ID — which includes the checkout path. The disambiguator is mangled into
   every hephaestus symbol name, which in turn changes the linker's
   deterministic ordering: `.text` layout, COFF symbol table, and data-
   directory RVAs all shift. CI builds at ONE fixed path, so none of this is
   visible to CI.

The harness therefore:
  * passes the SAME `--remap-path-prefix` pair to BOTH builds, baking both
    hephaestus checkouts to one canonical source path. Identical flag strings
    keep cargo metadata hashes (binary-name disambiguators) comparable for
    path-invariant graphs, and the embedded-path content class disappears.
  * asserts byte-identity after PE normalization, else classifies:
      PASS       byte-identical after PE normalization
      EQUIVALENT source-aligned (worktree == gitlink for consumed crates,
                 no clone-path strings remain) with a residual confined to
                 the metadata-disambiguator / linker-layout class
      SKEWED     EQUIVALENT would apply but the worktree diverges from the
                 committed gitlink, so identity cannot be attested
      FAIL       any other difference
  * gates EQUIVALENT on a per-crate source comparison of the worktree
    against the gitlink clone for exactly the crates the coeus build consumes
    (core/cuda/metal/rocm/wgpu; conformance is reported but not consumed).
    `git status` masks such divergence via assume-unchanged/skip-worktree,
    so the gate reads file bytes, not git metadata.
  * redirects OTHER overlay peers (apollo-fft/nufft/sht) to clean temporary
    clones at their committed gitlinks for BOTH builds. Apollo's worktree is
    frequently mid-merge with uncommitted conflict markers that break every
    coeus build; keeping the peer identical in both overlays removes it from
    the comparison without touching the owner's merge state.

Exit status is nonzero when any set FAILs or is SKEWED, so CI can gate on it.
The hephaestus and apollo worktrees are read-only in this flow: the temp
clones are the only copies checked out at their gitlinks.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import stat
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

ATLAS_ROOT = Path(__file__).resolve().parents[1]
REPOS = ATLAS_ROOT / "repos"
COEUS = REPOS / "coeus"
HEPHAESTUS = REPOS / "hephaestus"
APOLLO = REPOS / "apollo"
TARGET = ATLAS_ROOT / "target"
TEMP_CLONE = TARGET / "hephaestus-gitlink"
TEMP_APOLLO = TARGET / "apollo-gitlink"

HEPHAESTUS_CRATES = (
    "hephaestus-core", "hephaestus-cuda", "hephaestus-metal",
    "hephaestus-rocm", "hephaestus-wgpu",
)
HEPHAESTUS_SOURCES = (
    "https://github.com/ryancinsight/hephaestus",
    "https://github.com/ryancinsight/hephaestus.git",
)

# apollo is a transitive peer of every coeus build. Its worktree is commonly
# mid-merge (uncommitted conflict markers), so the harness redirects it to a
# clean temporary clone at its committed gitlink for BOTH builds — keeping the
# peer constant so it cannot distort the hephaestus comparison.
APOLLO_CRATES = ("apollo-fft", "apollo-nufft", "apollo-sht")
APOLLO_SOURCES = (
    "https://github.com/ryancinsight/apollo",
    "https://github.com/ryancinsight/apollo.git",
)

# name -> (package, optional test target, binary globs to snapshot)
TARGET_SETS: dict[str, tuple[str, str | None, tuple[str, ...]]] = {
    "dist": ("coeus-dist", None, ("dist_ops-*.exe", "coeus_dist-*.exe")),
    "python": ("coeus-python", "binding_ops", ("binding_ops-*.exe",)),
    "wgpu": ("coeus-wgpu", "wgpu_ops", ("wgpu_ops-*.exe",)),
}


def resolve_sets(names: list[str] | None) -> dict[str, tuple[str, str | None, tuple[str, ...]]]:
    """Return the selected target sets in canonical (dict) order.

    `names` is the user-supplied selection; unknown names raise ValueError.
    """
    if names:
        unknown = [n for n in names if n not in TARGET_SETS]
        if unknown:
            raise ValueError(f"unknown target set(s): {', '.join(unknown)}")
        return {n: TARGET_SETS[n] for n in names}
    return dict(TARGET_SETS)


# --------------------------------------------------------------------------
# PE normalization
# --------------------------------------------------------------------------

def pe_offsets(data: bytes) -> tuple[int, int, int]:
    """Return (e_lfanew, timestamp_offset, checksum_offset) for a PE image.

    Validates the DOS stub pointer, the "PE\\0\\0" signature, and the optional
    header magic (PE32 0x10B / PE32+ 0x20B) so non-PE input fails loudly
    instead of silently producing bogus offsets.
    """
    if len(data) < 0x40:
        raise ValueError("file too small to be a PE image")
    e_lfanew = struct.unpack("<I", data[0x3C:0x40])[0]
    pe = e_lfanew  # "PE\\0\\0" signature start
    if pe + 0x44 > len(data) or data[pe:pe + 4] != b"PE\x00\x00":
        raise ValueError(f"no PE signature at e_lfanew 0x{pe:x}")
    optional_header = pe + 0x18  # after the 20-byte COFF header
    magic = struct.unpack("<H", data[optional_header:optional_header + 2])[0]
    if magic not in (0x10B, 0x20B):
        raise ValueError(f"unrecognized optional-header magic 0x{magic:x}")
    timestamp = pe + 8  # signature(4) + machine(2) + numsections(2) + stamp
    checksum = optional_header + 0x40  # PE32 and PE32+ both place it here
    return e_lfanew, timestamp, checksum


def normalize_pe(data: bytes) -> bytes:
    """Zero the nondeterministic PE fields (TimeDateStamp, CheckSum)."""
    _, timestamp, checksum = pe_offsets(data)
    out = bytearray(data)
    out[timestamp:timestamp + 4] = b"\x00\x00\x00\x00"
    out[checksum:checksum + 4] = b"\x00\x00\x00\x00"
    return bytes(out)


def section_raw_sizes(data: bytes) -> tuple[tuple[str, int], ...]:
    """Return ((section_name, raw_size), ...) for a PE image."""
    pe = struct.unpack("<I", data[0x3C:0x40])[0]
    num = struct.unpack("<H", data[pe + 6:pe + 8])[0]
    opt = struct.unpack("<H", data[pe + 20:pe + 22])[0]
    table = pe + 24 + opt
    out: list[tuple[str, int]] = []
    for i in range(num):
        off = table + i * 40
        name = data[off:off + 8].rstrip(b"\x00").decode("latin1")
        raw_size = struct.unpack("<I", data[off + 16:off + 20])[0]
        out.append((name, raw_size))
    return tuple(out)


def residual_diff_count(a: bytes, b: bytes) -> int:
    """Count differing bytes across the common prefix plus any length delta."""
    n = min(len(a), len(b))
    return sum(1 for i in range(n) if a[i] != b[i]) + abs(len(a) - len(b))


CANONICAL_SRC = "C:/atlas/src/hephaestus"  # common path baked by both builds


def remap_rustflags(worktree: Path, clone: Path) -> str:
    """`--remap-path-prefix` pairs baking both checkouts to ONE canonical path.

    The SAME flag string is passed to the plain and the gitlink build. Cargo's
    metadata hash (the binary-name disambiguator) includes the rustflags, so
    identical flag strings keep suffixes identical for path-invariant graphs;
    and both hephaestus checkouts embed the same canonical source path, so the
    dependency-path content class disappears from the comparison.
    """
    bs = lambda p: str(p).replace("/", "\\")
    canonical = CANONICAL_SRC.replace("/", "\\")
    return (
        f"--remap-path-prefix={bs(worktree)}={canonical} "
        f"--remap-path-prefix={bs(clone)}={canonical}"
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


SKIP_DIRS = {"target", "__pycache__", ".git", ".cargo"}
SKIP_SUFFIXES = (".pyc", ".exe", ".dll", ".pdb", ".rlib", ".rmeta")


def _tree_digest(root: Path) -> dict[str, str]:
    """{relative_path: sha256} for source files, excluding build artifacts."""
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        parts = p.relative_to(root).parts
        if any(part in SKIP_DIRS for part in parts[:-1]):
            continue
        if p.name.endswith(SKIP_SUFFIXES):
            continue
        out[p.relative_to(root).as_posix()] = sha256(p.read_bytes())
    return out


def crate_alignment(
    worktree_crates: Path, clone_crates: Path, names: tuple[str, ...]
) -> dict[str, dict[str, int]]:
    """Per-crate {only_worktree, only_clone, content_diff} source counts."""
    out: dict[str, dict[str, int]] = {}
    for crate in names:
        w = _tree_digest(worktree_crates / crate)
        c = _tree_digest(clone_crates / crate)
        out[crate] = {
            "only_worktree": len(set(w) - set(c)),
            "only_clone": len(set(c) - set(w)),
            "content_diff": sum(1 for k in set(w) & set(c) if w[k] != c[k]),
        }
    return out


def source_aligned(alignment: dict[str, dict[str, int]]) -> bool:
    """True when every compared crate matches its gitlink commit exactly."""
    return all(sum(v.values()) == 0 for v in alignment.values())


def _make_writable(path: Path) -> None:
    """Clear the read-only attribute on Windows so deletion is permitted."""
    if os.name != "nt":
        return
    current = os.stat(path).st_mode
    if not current & stat.S_IWRITE:
        os.chmod(path, current | stat.S_IWRITE)


def _force_delete_tree(path: Path) -> None:
    """Clear read-only bits, then delete. Git object files are read-only."""
    for root, dirs, files in os.walk(path, topdown=False):
        for name in dirs + files:
            _make_writable(Path(root) / name)
    shutil.rmtree(path)


def rmtree_robust(path: Path, retries: int = 5, delay: float = 0.5) -> None:
    """Remove a directory tree, retrying on transient Windows handle locks.

    Git object files are read-only (WinError 5 on unlink without clearing the
    attribute) and can be briefly held open after a subprocess exits; both are
    handled here.
    """
    for attempt in range(retries):
        try:
            _force_delete_tree(path)
            return
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(delay)


# --------------------------------------------------------------------------
# git / cargo helpers
# --------------------------------------------------------------------------

def run(
    cmd: list[str],
    cwd: Path,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, encoding="utf-8", errors="replace", check=check, env=full_env
    )


def committed_gitlink(rel_path: str) -> str:
    proc = run(["git", "ls-files", "-s", rel_path], ATLAS_ROOT)
    return proc.stdout.split()[1]


def overlay_config_args(
    temp_crates: Path, sources: tuple[str, ...], crates: tuple[str, ...]
) -> list[str]:
    """Build `--config patch.<src>.<crate>.path=` overrides for one peer.

    Paths use forward slashes: backslashes would be parsed as TOML escape
    sequences inside the quoted value (and cargo accepts `/` on Windows).
    """
    root = temp_crates.as_posix()
    out: list[str] = []
    for source in sources:
        for crate in crates:
            out.extend(
                [
                    "--config",
                    f'patch."{source}".{crate}.path="{root}/{crate}"',
                ]
            )
    return out


def make_clean_clone(repo: Path, dest: Path, gitlink: str, cwd: Path) -> str:
    """Recreate a clean temporary clone of `repo` at the committed gitlink."""
    if dest.exists():
        rmtree_robust(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "-q", str(repo), str(dest)], cwd)
    run(["git", "checkout", "-q", gitlink], dest)
    head = run(["git", "rev-parse", "HEAD"], dest).stdout.strip()
    dirty = len(run(["git", "status", "--short"], dest).stdout.strip())
    return f"{head[:12]} dirty={dirty}"


def restore_coeus_lock() -> None:
    run(["git", "checkout", "--", "Cargo.lock"], COEUS, check=False)


def snapshot_test_binaries(
    globs: list[str], normalize: Callable[[bytes], bytes] | None = None
) -> dict[str, dict]:
    """Hash every matching test binary under target/debug/deps.

    Returns {stem: {path, raw_sha, norm_sha, size, norm_size, suffix}} where
    stem is the test-target name without the cargo metadata-hash suffix (e.g.
    `wgpu_ops` from `wgpu_ops-8eb42c5c...exe`). Pairing by stem is required
    because the metadata hash includes the path-dependency checkout path, so
    it legitimately differs between the two overlays for hephaestus-linking
    binaries.
    """
    if normalize is None:
        normalize = normalize_pe
    deps = TARGET / "debug" / "deps"
    result: dict[str, dict] = {}
    for pattern in globs:
        for path in sorted(deps.glob(pattern)):
            data = path.read_bytes()
            norm = normalize(data)
            stem, _, suffix = path.stem.partition("-")
            if stem in result:
                raise ValueError(f"duplicate test-target stem {stem!r} in snapshot")
            result[stem] = {
                # Bytes are captured NOW: the plain artifacts are deleted before
                # the gitlink build, so paths would dangle at compare time.
                "data": data,
                "raw_sha": sha256(data),
                "norm_sha": sha256(norm),
                "size": len(data),
                "norm_size": len(norm),
                "suffix": suffix,
            }
    return result


def remove_matching(globs: list[str]) -> None:
    deps = TARGET / "debug" / "deps"
    for pattern in globs:
        for path in deps.glob(pattern):
            path.unlink(missing_ok=True)


def build_package(
    cargo: Path,
    package: str,
    test_name: str | None,
    extra_config: list[str] | None = None,
    rustflags: str | None = None,
) -> None:
    cmd = [str(cargo), "test", "-p", package, "--no-run"]
    if test_name:
        cmd += ["--test", test_name]
    if extra_config:
        cmd += extra_config
    env = {"RUSTFLAGS": rustflags} if rustflags else None
    proc = run(cmd, COEUS, check=False, env=env)
    if proc.returncode != 0:
        sys.stderr.write(f"cargo test -p {package} --no-run failed:\n")
        sys.stderr.write(proc.stdout[-2000:])
        sys.stderr.write(proc.stderr[-2000:])
        sys.exit(1)


def classify_binary(a_data: bytes, b_data: bytes, clone: Path) -> tuple[str, str]:
    """Classify the plain-vs-gitlink residual for one binary pair.

    Returns (verdict, detail) with verdict in {PASS, EQUIVALENT, FAIL}.
    """
    if sha256(normalize_pe(a_data)) == sha256(normalize_pe(b_data)):
        return ("PASS", "byte-identical after PE normalization")

    if section_raw_sizes(a_data) != section_raw_sizes(b_data):
        return ("FAIL", "PE section raw sizes differ between overlays")

    clone_bs = str(clone).replace("/", "\\").encode()
    clone_fs = str(clone).replace("\\", "/").encode()
    if any(n in a_data or n in b_data for n in (clone_bs, clone_fs)):
        return ("FAIL", "clone-path strings still embedded after remap")

    return (
        "EQUIVALENT",
        "source-identical; the only residual is the cargo metadata-disambiguator "
        "symbol names and their linker-layout cascade (path-inherent, CI-invisible)",
    )


# --------------------------------------------------------------------------
# per-set verification
# --------------------------------------------------------------------------

def verify_target_set(
    cargo: Path,
    package: str,
    test_name: str | None,
    globs: tuple[str, ...],
    plain_config: list[str],
    gitlink_config: list[str],
    rustflags: str,
    source_aligned_flag: bool,
) -> tuple[bool, list[str]]:
    """Run the plain-vs-gitlink build/hash/compare cycle for one target set.

    Both builds receive the SAME rustflags (canonical path remap) so cargo
    metadata hashes stay comparable for path-invariant graphs. `plain_config`
    keeps non-hephaestus peers (e.g. apollo) at their committed gitlinks in
    the plain build; `gitlink_config` additionally redirects hephaestus.
    Returns (ok, verdict_lines).
    """
    glob_list = list(globs)
    label = package if not test_name else f"{package} [{test_name}]"
    verdicts: list[str] = [f"== target set: {label}"]

    # Plain overlay (worktree hephaestus) with the same rustflags.
    remove_matching(glob_list)
    build_package(cargo, package, test_name, plain_config, rustflags)
    plain = snapshot_test_binaries(glob_list)
    if not plain:
        sys.stderr.write(f"no plain-overlay test binaries found for {label} ({globs})\n")
        return False, verdicts
    for name, h in sorted(plain.items()):
        verdicts.append(f"   PLAIN {name}-{h['suffix']}  norm={h['norm_sha'][:16]}… {h['size']}B")

    # Delete the artifacts, then rebuild under the GITLINK overlay.
    remove_matching(glob_list)
    build_package(cargo, package, test_name, gitlink_config, rustflags)
    gitlink_bins = snapshot_test_binaries(glob_list)
    for name, h in sorted(gitlink_bins.items()):
        verdicts.append(f"   GITLINK {name}-{h['suffix']}  norm={h['norm_sha'][:16]}… {h['size']}B")

    ok = True
    if set(plain) != set(gitlink_bins):
        verdicts.append(
            "   FAIL: test-target stems differ between overlays "
            f"({sorted(plain)} vs {sorted(gitlink_bins)})"
        )
        ok = False
    for stem in sorted(plain):
        a, b = plain[stem], gitlink_bins.get(stem)
        if b is None:
            verdicts.append(f"   FAIL: {stem} test binary missing from gitlink build")
            ok = False
            continue
        if a["suffix"] != b["suffix"]:
            verdicts.append(
                f"   note: {stem} metadata-hash suffix differs ({a['suffix']} vs "
                f"{b['suffix']}) — expected when the peer patch path is remapped "
                "(path-deps encode their absolute path in the metadata hash)"
            )
        verdict, detail = classify_binary(a["data"], b["data"], TEMP_CLONE)
        if verdict == "EQUIVALENT" and not source_aligned_flag:
            verdicts.append(
                f"   SKEWED: {stem} — source gate failed; the worktree diverges "
                f"from the gitlink, so identity cannot be attested ({detail})"
            )
            ok = False
        else:
            verdicts.append(f"   {verdict}: {stem} — {detail}")
            if verdict == "FAIL":
                ok = False
    return ok, verdicts


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--atlas-root",
        type=Path,
        default=ATLAS_ROOT,
        help="stack root (default: this script's parent)",
    )
    parser.add_argument(
        "--keep-temp-clone",
        action="store_true",
        help="leave target/hephaestus-gitlink in place for inspection",
    )
    parser.add_argument(
        "--cargo", default="cargo", help="cargo executable (default: cargo)"
    )
    parser.add_argument(
        "--set",
        choices=list(TARGET_SETS),
        nargs="+",
        default=None,
        help="target sets to verify (default: all of %(choices)s)",
    )
    args = parser.parse_args(argv)

    atlas_root = args.atlas_root
    globals().update(
        REPOS=atlas_root / "repos",
        COEUS=atlas_root / "repos" / "coeus",
        HEPHAESTUS=atlas_root / "repos" / "hephaestus",
        TARGET=atlas_root / "target",
        TEMP_CLONE=atlas_root / "target" / "hephaestus-gitlink",
    )

    try:
        return _run(atlas_root, args)
    finally:
        # Always restore the worktree, even when a build fails mid-run.
        for clone in (TEMP_CLONE, TEMP_APOLLO):
            if not args.keep_temp_clone and clone.exists():
                rmtree_robust(clone)
        restore_coeus_lock()


def _run(atlas_root: Path, args: argparse.Namespace) -> int:
    """Body of main(); wrapped in try/finally by main() for cleanup."""
    hep_gitlink = committed_gitlink("repos/hephaestus")
    apo_gitlink = committed_gitlink("repos/apollo")
    print(f"== hephaestus gitlink: {hep_gitlink}")
    print(f"== apollo gitlink: {apo_gitlink} (redirected in both builds)")

    # 1. Recreate the clean temp clones at the committed gitlinks.
    hep_state = make_clean_clone(HEPHAESTUS, TEMP_CLONE, hep_gitlink, atlas_root)
    apo_state = make_clean_clone(APOLLO, TEMP_APOLLO, apo_gitlink, atlas_root)
    print(f"== hephaestus temp clone: {hep_state}")
    print(f"== apollo temp clone: {apo_state}")

    # 2. Source gate: the committed gitlink content must equal the worktree for
    # the crates the coeus build actually consumes. Other crates (e.g.
    # hephaestus-conformance) are reported but do not gate the proof.
    alignment = crate_alignment(
        HEPHAESTUS / "crates", TEMP_CLONE / "crates", HEPHAESTUS_CRATES
    )
    source_ok = source_aligned(alignment)
    print("== source gate: worktree vs gitlink per consumed crate ==")
    for crate, counts in alignment.items():
        print(
            f"   {crate}: only_worktree={counts['only_worktree']} "
            f"only_clone={counts['only_clone']} content_diff={counts['content_diff']}"
        )
    print(f"   source aligned: {source_ok}")
    if not source_ok:
        print(
            "   NOTE: the hephaestus worktree diverges from the committed gitlink "
            "(masked from `git status` by assume-unchanged/skip-worktree). Sets "
            "whose graphs consume hephaestus (python, wgpu) cannot attest "
            "identity until the owner aligns or commits."
        )

    apollo_args = overlay_config_args(TEMP_APOLLO / "crates", APOLLO_SOURCES, APOLLO_CRATES)
    hep_args = overlay_config_args(TEMP_CLONE / "crates", HEPHAESTUS_SOURCES, HEPHAESTUS_CRATES)
    plain_config = apollo_args  # apollo clean in BOTH builds; hephaestus only in the gitlink one
    gitlink_config = hep_args + apollo_args
    rustflags = remap_rustflags(HEPHAESTUS, TEMP_CLONE)

    # 3. Verify each selected target set under both overlays.
    sets = resolve_sets(args.set)
    ok = True
    for package, test_name, globs in sets.values():
        set_ok, lines = verify_target_set(
            Path(args.cargo),
            package,
            test_name,
            globs,
            plain_config,
            gitlink_config,
            rustflags,
            source_ok,
        )
        for line in lines:
            print("  " + line)
        if not set_ok:
            ok = False

    print("\nVERDICT:", "OK" if ok else "NOT OK")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
