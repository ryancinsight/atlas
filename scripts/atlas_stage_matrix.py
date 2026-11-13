#!/usr/bin/env python3
"""Peer-write and kill matrix for the pre-push stage sequence, on real Cargo.

Each cell builds a fixture (kcore with a build script and a large generated
module, kapp with a probe test, Git crate kgit) in its own directory and drives
the tree's `atlas-build-identity.py run` with the hook's stage commands. A cell
is sound when the final complete sequence leaves the probe, every kcore
`gen.rs` and the `value` and `GEN` rustdoc pages at the current revision. It
reports the units rebuilt: `.fingerprint` and `build` directories whose files
changed across that sequence. An unexpected exit, a peer failure, or output
after a kill makes the cell ERR; a kill lands only while its stage runs.

    atlas_stage_matrix.py --tree <checkout> --root <short dir> --setup repush
    atlas_stage_matrix.py --compare parent.json head.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

STAGES = ("clippy", "tests", "rustdoc")
SHAPES = ("single", "samekey")
SETUPS = ("repush", "first", "sibling")
KINDS = ("none", "nextest", "clippy", "doc", "buildrs", "data")
# P: a peer before clippy, between clippy and tests, between tests and rustdoc.
# KT/KR: the tests/rustdoc stage killed that many seconds after its first
# compile/documentation line (heartbeat 5 s); `--compare` skips the 7 s ones.
POSITIONS = ("P0", "P1", "P2", "KT2", "KT7", "KR2", "KR7")
TIMING = ("KT7", "KR7")
REVISIONS = {1: (1, 10), 2: (2, 20)}
EXPECTED = {"probe": "27", "gen": "pub const GEN: u32 = 20;"}
STAGE_SCRIPT = """\
manifest="$1"; shift
selection=(-p kcore -p kapp)
for stage in "$@"; do
  echo "::stage $stage" >&2
  case "$stage" in
    clippy) cargo clippy --manifest-path "$manifest" --all-targets --locked "${selection[@]}" || exit $? ;;
    tests) cargo nextest run --manifest-path "$manifest" --locked --no-tests=pass "${selection[@]}" || exit $? ;;
    rustdoc) env -u CARGO_ENCODED_RUSTDOCFLAGS RUSTDOCFLAGS="-D warnings" \\
      cargo doc --no-deps --manifest-path "$manifest" --locked "${selection[@]}" || exit $? ;;
  esac
  echo "::done $stage" >&2
  [ "$PEER_AFTER" != "$stage" ] || python "$PEER_SCRIPT" || exit 99
done
"""
PEER_SCRIPT = """\
import os, subprocess, sys
from pathlib import Path
kind, peer = os.environ["PEER_KIND"], os.environ["PEER_DIR"]
if kind == "none":
    sys.exit(0)
for path in Path(peer).rglob("*"):  # newer than every unit the running build wrote since the sources were laid down
    if path.is_file() and ".git" not in path.parts:
        os.utime(path)
env = {**os.environ, "CARGO_TARGET_DIR": os.environ["PEER_TARGET"]}
tail = ["--manifest-path", peer + "/Cargo.toml", "--locked", "-p", "kcore", "-p", "kapp"]
if kind == "doc":
    env["RUSTDOCFLAGS"] = "-D warnings"
command = {
    "clippy": ["cargo", "clippy", "--all-targets", *tail],
    "doc": ["cargo", "doc", "--no-deps", *tail],
}.get(kind, ["cargo", "nextest", "run", "--no-tests=pass", "--no-run", *tail])
code = subprocess.run(command, env=env, cwd=peer, capture_output=True).returncode
if code:
    Path(os.environ["PEER_RC"]).write_text(str(code))
sys.exit(code)
"""


def _run(args, cwd=None, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=900)
    if result.returncode:
        raise RuntimeError(f"{args[:3]} exited {result.returncode}: {result.stderr[-600:]}")


def _git(cwd, *args):
    _run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd)


def _commit(cwd, message: str) -> None:
    _git(cwd, "init", "-q")
    _git(cwd, "add", ".")
    _git(cwd, "commit", "-q", "-m", message)


def _contain(process: subprocess.Popen):
    """A function killing the process and all its descendants; a Job Object follows MSYS re-parenting, taskkill /T does not."""
    if os.name != "nt":
        return lambda: os.killpg(process.pid, signal.SIGKILL)
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    job = k32.CreateJobObjectW(None, None)
    if not k32.AssignProcessToJobObject(job, wintypes.HANDLE(int(process._handle))):
        raise OSError(ctypes.get_last_error(), "cannot place the identity process in a Job Object")
    return lambda: k32.TerminateJobObject(job, 1)


def _expect(code: int, what: str) -> None:
    if code:
        raise RuntimeError(f"{what} exited {code}")


class Cell:
    def __init__(self, tree: Path, shape: str, setup: str, kind: str, position: str, functions: int, root: Path | None):
        self.scripts, self.shape, self.setup, self.kind, self.position = tree / "scripts", shape, setup, kind, position
        self.functions, self.killed, self.triggered = functions, False, False
        self.base = Path(tempfile.mkdtemp(prefix="sm-", dir=root))  # unresolved: a subst drive stays short
        self.source, self.peer, self.target = self.base / "ws", self.base / "peer", self.base / "target"
        self.environment = {k: v for k, v in os.environ.items() if k != "CARGO_TARGET_DIR"}
        self.environment.update(PROBE_OUT=str(self.base / "probe.txt"), CARGO_HOME=str(self.base / "c"),
                                PEER_RC=str(self.base / "peer.rc"))
        self.stage = self.landed = self.kill = self.killed_at = None

    def write_revision(self, root: Path, revision: int, aged: bool, scale: int = 1, data: int | None = None) -> None:
        value, number = REVISIONS[revision]
        core = root / "kcore"
        (core / "src").mkdir(parents=True, exist_ok=True)
        big = "".join(f"/// Generated {n}.\npub fn big{n}() -> u32 {{ {n} }}\n" for n in range(self.functions))
        (core / "src" / "big.rs").write_text(big)
        (core / "src" / "lib.rs").write_text('include!(concat!(env!("OUT_DIR"), "/gen.rs"));\npub mod big;\n'
                                             f"/// The value is {value}.\npub fn value() -> u32 {{ {value} }}\n")
        (core / "data.txt").write_text(f"{number if data is None else data}\n")
        (core / "build.rs").write_text(
            'fn main() {\n    println!("cargo:rerun-if-changed=data.txt");\n    println!("cargo:rerun-if-changed=build.rs");\n'
            '    let v: u32 = std::fs::read_to_string("data.txt").unwrap().trim().parse().unwrap();\n'
            '    let out = std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap()).join("gen.rs");\n'
            f'    std::fs::write(out, format!("pub const GEN: u32 = {{}};", v * {scale})).unwrap();\n}}\n'
        )
        if aged:
            old = time.time() - 86400
            for path in (p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts):
                os.utime(path, (old, old))

    def build_fixture(self) -> None:
        kgit = self.base / "kgit"
        (kgit / "src").mkdir(parents=True)
        (kgit / "Cargo.toml").write_text('[package]\nname = "kgit"\nversion = "0.1.0"\nedition = "2021"\n')
        (kgit / "src" / "lib.rs").write_text("pub fn g() -> u32 { 5 }\n")
        _commit(kgit, "k")
        files = {
            "Cargo.toml": '[workspace]\nmembers = ["kcore", "kapp"]\nresolver = "2"\n',
            "kcore/Cargo.toml": '[package]\nname = "kcore"\nversion = "0.1.0"\nedition = "2021"\n',
            "kapp/Cargo.toml": '[package]\nname = "kapp"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\n'
            f'kcore = {{ path = "../kcore" }}\nkgit = {{ git = "{kgit.as_uri()}" }}\n',
            "kapp/src/lib.rs": "pub fn v() -> u32 { kcore::value() + kcore::GEN + kgit::g() }\n#[cfg(test)]\nmod t {\n"
            '    #[test]\n    fn probe() {\n        std::fs::write(std::env::var("PROBE_OUT").unwrap(), super::v().to_string()).unwrap();\n    }\n}\n',
        }
        for relative, text in files.items():
            (self.source / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.source / relative).write_text(text)
        self.write_revision(self.source, 1, False)
        _run(["cargo", "generate-lockfile"], self.source, self.environment)
        _commit(self.source, "s")
        _run(["git", "clone", "-q", str(self.source), str(self.peer)])
        (self.base / "stages.sh").write_text(STAGE_SCRIPT, newline="\n")
        (self.base / "peer.py").write_text(PEER_SCRIPT)

    def prepare_peer(self) -> None:
        """The peer's source, written now: its mtimes are newer than the aged export's units."""
        _git(self.peer, "checkout", "-q", "-f", "HEAD")
        revision = 1 if self.kind in ("nextest", "clippy", "doc") else 2
        self.write_revision(
            self.peer, revision, False, scale=100 if self.kind == "buildrs" else 1, data=99 if self.kind == "data" else None
        )

    def run_peer(self) -> None:
        self.prepare_peer()
        subprocess.run([sys.executable, str(self.base / "peer.py")], env=self.peer_environment(), capture_output=True, timeout=900)

    def peer_environment(self, after: str | None = None) -> dict:
        return {**self.environment, "PEER_KIND": self.kind, "PEER_DIR": str(self.peer), "PEER_AFTER": after or "",
                "PEER_SCRIPT": str(self.base / "peer.py"), "PEER_TARGET": self.target.resolve().as_posix()}

    def land(self, process: subprocess.Popen, wanted: str) -> None:
        self.landed = (self.stage or "after") if process.poll() is None else "exited"
        if self.landed == wanted:
            self.killed, self.killed_at = True, time.monotonic()
            self.kill()

    def identity(self, stages, key: str, peer_after: str | None = None, kill: tuple[str, float] | None = None) -> int:
        manifest = (self.source / "Cargo.toml").as_posix()
        if peer_after:
            self.prepare_peer()
        environment = self.peer_environment(peer_after)
        command = [sys.executable, str(self.scripts / "atlas-build-identity.py"), "run", "--root", str(self.source),
                   "--package", "kcore", "--package", "kapp", "--selection", "kcore", "--selection", "kapp",
                   "--target-dir", str(self.target), "--profile", "debug", "--target", "host", "--manifest", manifest,
                   "--command-cwd", str(self.source), "--command-key", key, "--", "bash", str(self.base / "stages.sh"),
                   manifest, *stages]
        process = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, start_new_session=os.name != "nt")
        self.kill, self.killed_at = _contain(process), None
        trigger = {"tests": "Compiling ", "rustdoc": "Documenting "}
        for line in process.stdout:
            if line.startswith("::stage ") or line.startswith("::done "):
                self.stage = line.split()[1] if line.startswith("::s") else None
            if kill and not self.triggered and self.stage == kill[0] and line.lstrip().startswith(trigger[self.stage]):
                self.triggered = True
                threading.Timer(kill[1], self.land, [process, kill[0]]).start()
        if self.killed_at and time.monotonic() - self.killed_at > 3:
            raise RuntimeError(f"output continued {time.monotonic() - self.killed_at:.0f} s after the kill")
        return process.wait()

    def sequence(self, position: str | None = None, kill: tuple[str, float] | None = None) -> int:
        point = {"P1": "clippy", "P2": "tests"}.get(position)
        if self.shape == "single":
            if position == "P0":
                self.run_peer()
            return self.identity(STAGES, "atlas-pre-push", peer_after=point, kill=kill)
        status = 0
        for stage in STAGES:
            if position == f"P{STAGES.index(stage)}":
                self.run_peer()
            code = self.identity((stage,), "atlas-pre-push", kill=kill if kill and kill[0] == stage else None)
            status = status or code
            if kill and kill[0] == stage and self.killed:
                return code
        return status

    def units(self) -> dict[str, tuple]:
        return {p.relative_to(self.target).as_posix(): (p.stat().st_mtime_ns, p.stat().st_size)
                for part in (".fingerprint", "build") for p in (self.target / "debug" / part).rglob("*") if p.is_file()}

    def verdict(self, final: int) -> dict:
        probe = (self.base / "probe.txt").read_text().strip() if (self.base / "probe.txt").exists() else None
        gens = sorted({p.read_text().strip() for p in (self.target / "debug" / "build").glob("kcore-*/out/gen.rs")})
        def page(name: str) -> str:
            path = self.target / "doc" / "kcore" / name
            return re.sub(r"<[^>]+>", "", path.read_text(encoding="utf-8")) if path.exists() else ""

        documented = "The value is 2" in page("fn.value.html") and re.search(r"GEN: u32 = 20(?![0-9])", page("constant.GEN.html"))
        wrong = [n for n, ok in (("probe", probe == EXPECTED["probe"]), ("gen", gens == [EXPECTED["gen"]]), ("page", documented)) if not ok]
        why = f"rc{final}" if final else "+".join(wrong) or None
        return {"probe": probe, "gens": gens, "why": why, "safe": why is None}

    def execute(self) -> dict:
        outcome = {"setup": self.setup, "shape": self.shape, "kind": self.kind, "position": self.position}
        try:
            self.build_fixture()
            if self.setup != "first":
                _expect(self.sequence(), "the warm sequence")
            self.write_revision(self.source, 2, True)
            if self.setup == "sibling":
                _expect(self.identity(("clippy",), "atlas-pre-push-sibling"), "the sibling clippy run")
            if self.position.startswith("K"):
                stage = "tests" if self.position.startswith("KT") else "rustdoc"
                code = self.sequence(kill=(stage, float(self.position[2:])))
                if self.killed != bool(code):
                    raise RuntimeError(f"the killed run exited {code} with killed={self.killed}")
                self.run_peer()
            elif self.setup == "repush":
                _expect(self.sequence(), "the first R2 sequence")
            before = self.units()
            final = self.sequence(None if self.position.startswith("K") else self.position)
            if (self.base / "peer.rc").exists():
                raise RuntimeError(f"the {self.kind} peer exited {(self.base / 'peer.rc').read_text()}")
            after = self.units()
            changed = {"/".join(k.split("/")[1:3]) for k in before.keys() | after.keys() if before.get(k) != after.get(k)}
            outcome.update(self.verdict(final), final=final, rebuilt=len(changed), killed=self.killed, landed=self.landed)
        except Exception as error:  # a broken cell is reported, never dropped
            outcome.update(error=str(error)[-300:], safe=False)
        finally:
            try:
                shutil.rmtree(self.base, onerror=lambda function, name, _e: (os.chmod(name, stat.S_IWRITE), function(name)))
            except OSError as error:
                outcome.update(error=f"cleanup: {error}", safe=False)
        return outcome


def render(results: list[dict]) -> str:
    """One table per shape and setup: rows are peer kinds, columns positions, cells `ok|X(why)/rebuilt`."""
    def text(r: dict | None, position: str) -> str:
        if r is None or "error" in r:
            return "-" if r is None else "ERR"
        missed = "" if r["killed"] or not position.startswith("K") else f"~{r['landed']}"
        return ("ok" if r["safe"] else f"X({r['why']})") + f"/{r['rebuilt']}{missed}"

    lines = []
    for shape, setup in sorted({(r["shape"], r["setup"]) for r in results}, key=lambda t: (t[0], SETUPS.index(t[1]))):
        cells = {(r["kind"], r["position"]): r for r in results if (r["shape"], r["setup"]) == (shape, setup)}
        positions = [p for p in POSITIONS if any(k[1] == p for k in cells)]
        lines += [f"## {shape} / {setup}   (cell: safe|X(why) / units rebuilt; ~stage = kill missed, it found that stage)",
                  "kind     " + "".join(f"{p:<14}" for p in positions)]
        lines += [f"{kind:<8} " + "".join(f"{text(cells.get((kind, p)), p):<14}" for p in positions)
                  for kind in KINDS if any(k[0] == kind for k in cells)]
    return chr(10).join(lines)


def compare(parent: list[dict], head: list[dict]) -> list[str]:
    """What the head lost against the parent: a green cell, a cell, a landed kill, or fewer units rebuilt."""
    key = lambda r: (r["shape"], r["setup"], r["kind"], r["position"])  # noqa: E731
    new = {key(r): r for r in head}
    problems = []
    for old in (o for o in parent if o["position"] not in TIMING):
        name = "/".join(key(old))
        r = new.get(key(old))
        if r is None:
            problems.append(f"{name}: dropped at the head")
        elif "error" in r:
            problems.append(f"{name}: errored at the head: {r['error']}")
        elif old["safe"] and not r["safe"]:
            problems.append(f"{name}: green at the parent, red at the head")
        elif old.get("killed") and not r["killed"]:
            problems.append(f"{name}: the kill landed at the parent but missed at the head")
        elif r["rebuilt"] > old.get("rebuilt", r["rebuilt"]):
            problems.append(f"{name}: rebuilds {r['rebuilt']} units, parent {old['rebuilt']} (liveness)")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tree", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--shape", choices=SHAPES, default="single")
    for name, choices in (("setup", SETUPS), ("kind", KINDS), ("position", POSITIONS)):
        parser.add_argument(f"--{name}", choices=choices, nargs="+", default=["repush"] if name == "setup" else list(choices))
    parser.add_argument("--functions", type=int, default=15000, help="generated functions in kcore")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--root", type=Path, help="directory for the cells (short on Windows; default: temp)")
    parser.add_argument("--json", type=Path, help="write the cells here")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("PARENT", "HEAD"))
    args = parser.parse_args()
    if args.compare:
        problems = compare(*(json.loads(path.read_text()) for path in args.compare))
        print("\n".join(problems) or "no cell was lost, turned red or rebuilt more")
        return 1 if problems else 0
    cells = [Cell(args.tree, args.shape, s, k, p, args.functions, args.root) for s in args.setup for k in args.kind for p in args.position]
    with ThreadPoolExecutor(args.jobs) as pool:
        results = list(pool.map(Cell.execute, cells))
    if args.json:
        args.json.write_text(json.dumps(results))
    print(render(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
