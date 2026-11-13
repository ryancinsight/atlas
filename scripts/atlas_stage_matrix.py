#!/usr/bin/env python3
"""Peer-write and kill matrix for the pre-push stage sequence, on real Cargo.

Each cell builds a fixture (kcore with a build script and a large generated
module, kapp with a probe test, Git crate kgit) in its own temporary directory
and drives `atlas-build-identity.py run` of the tree under test with the
hook's stage commands. A cell reports whether the final complete sequence is
sound (probe and rustdoc output equal the current revision's) and how many
units it rebuilt (Compiling, Checking and Documenting lines), because a
cleaner that rebuilds everything is sound in every cell and proves nothing.

    atlas_stage_matrix.py --tree <checkout> --shape single --setup repush
    atlas_stage_matrix.py --compare parent.json head.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

STAGES = ("clippy", "tests", "rustdoc")
SHAPES = ("single", "stage", "samekey")
SETUPS = ("repush", "first", "sibling")
KINDS = ("none", "nextest", "clippy", "doc", "buildrs", "data")
# P: a peer before clippy, between clippy and tests, between tests and
# rustdoc. KT and KR: the tests (rustdoc) stage tree-killed that many seconds
# after its first compile (documentation) line; the heartbeat period is 5 s.
POSITIONS = ("P0", "P1", "P2", "KT2", "KT7", "KR2", "KR7")
REVISIONS = {1: (1, 10), 2: (2, 20)}
EXPECTED = {"probe": "27", "doc": "2"}
UNIT_LINE = re.compile(r"^\s*(Compiling|Checking|Documenting) ")
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
  [ "$PEER_AFTER" != "$stage" ] || python "$PEER_SCRIPT" || exit 99
done
"""
PEER_SCRIPT = """\
import os, subprocess, sys
kind, peer = os.environ["PEER_KIND"], os.environ["PEER_DIR"]
if kind == "none":
    sys.exit(0)
env = {**os.environ, "CARGO_TARGET_DIR": os.environ["PEER_TARGET"]}
tail = ["--manifest-path", peer + "/Cargo.toml", "--locked", "-p", "kcore", "-p", "kapp"]
if kind == "doc":
    env["RUSTDOCFLAGS"] = "-D warnings"
command = {
    "clippy": ["cargo", "clippy", "--all-targets", *tail],
    "doc": ["cargo", "doc", "--no-deps", *tail],
}.get(kind, ["cargo", "nextest", "run", "--no-tests=pass", "--no-run", *tail])
sys.exit(subprocess.run(command, env=env, cwd=peer, capture_output=True).returncode)
"""


def _run(args, cwd=None, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=900)
    if result.returncode:
        raise RuntimeError(f"{args[:3]} exited {result.returncode}: {result.stderr[-600:]}")


def _git(cwd, *args):
    _run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd)


def _tree_kill(process: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
    else:
        os.killpg(process.pid, signal.SIGKILL)


class Cell:
    def __init__(self, tree: Path, shape: str, setup: str, kind: str, position: str, functions: int):
        self.scripts, self.shape, self.setup, self.kind, self.position = tree / "scripts", shape, setup, kind, position
        self.functions = functions
        self.base = Path(tempfile.mkdtemp(prefix="stage-matrix-")).resolve()
        self.source, self.peer, self.target = self.base / "ws", self.base / "peer", self.base / "target"
        self.environment = {k: v for k, v in os.environ.items() if k != "CARGO_TARGET_DIR"}
        self.environment.update(PROBE_OUT=str(self.base / "probe.txt"), CARGO_HOME=str(self.base / "ch"))
        self.rebuilt = 0
        self.killed = self.triggered = False

    def write_revision(self, root: Path, revision: int, aged: bool, scale: int = 1, data: int | None = None) -> None:
        value, number = REVISIONS[revision]
        core = root / "kcore"
        (core / "src").mkdir(parents=True, exist_ok=True)
        big = "".join(f"/// Generated {n}.\npub fn big{n}() -> u32 {{ {n} }}\n" for n in range(self.functions))
        (core / "src" / "big.rs").write_text(big)
        (core / "src" / "lib.rs").write_text(
            'include!(concat!(env!("OUT_DIR"), "/gen.rs"));\npub mod big;\n'
            f"/// The value is {value}.\npub fn value() -> u32 {{ {value} }}\n"
        )
        (core / "data.txt").write_text(f"{number if data is None else data}\n")
        (core / "build.rs").write_text(
            'fn main() {\n    println!("cargo:rerun-if-changed=data.txt");\n    println!("cargo:rerun-if-changed=build.rs");\n'
            '    let v: u32 = std::fs::read_to_string("data.txt").unwrap().trim().parse().unwrap();\n'
            '    let out = std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap()).join("gen.rs");\n'
            f'    std::fs::write(out, format!("pub const GEN: u32 = {{}};", v * {scale})).unwrap();\n}}\n'
        )
        if aged:
            old = time.time() - 86400
            for path in root.rglob("*"):
                if path.is_file() and ".git" not in path.parts:
                    os.utime(path, (old, old))

    def build_fixture(self) -> None:
        kgit = self.base / "kgit"
        (kgit / "src").mkdir(parents=True)
        (kgit / "Cargo.toml").write_text('[package]\nname = "kgit"\nversion = "0.1.0"\nedition = "2021"\n')
        (kgit / "src" / "lib.rs").write_text("pub fn g() -> u32 { 5 }\n")
        _git(kgit, "init", "-q")
        _git(kgit, "add", ".")
        _git(kgit, "commit", "-q", "-m", "k")
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
        _git(self.source, "init", "-q")
        _git(self.source, "add", ".")
        _git(self.source, "commit", "-q", "-m", "s")
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
        if self.kind == "none":
            return
        self.prepare_peer()
        environment = {**self.environment, "PEER_KIND": self.kind, "PEER_DIR": str(self.peer),
                       "PEER_TARGET": self.target.resolve().as_posix()}
        subprocess.run([sys.executable, str(self.base / "peer.py")], env=environment, capture_output=True, timeout=900)

    def land(self, process: subprocess.Popen) -> None:
        if process.poll() is None:
            self.killed = True
            _tree_kill(process)

    def identity(self, stages, key: str, peer_after: str | None = None, kill: tuple[str, float] | None = None) -> int:
        manifest = (self.source / "Cargo.toml").as_posix()
        environment = dict(self.environment)
        if peer_after:
            self.prepare_peer()
            environment.update(PEER_AFTER=peer_after, PEER_KIND=self.kind, PEER_DIR=str(self.peer),
                               PEER_SCRIPT=str(self.base / "peer.py"), PEER_TARGET=self.target.resolve().as_posix())
        command = [sys.executable, str(self.scripts / "atlas-build-identity.py"), "run", "--root", str(self.source),
                   "--package", "kcore", "--package", "kapp", "--selection", "kcore", "--selection", "kapp",
                   "--target-dir", str(self.target), "--profile", "debug", "--target", "host", "--manifest", manifest,
                   "--command-cwd", str(self.source), "--command-key", key, "--", "bash", str(self.base / "stages.sh"),
                   manifest, *stages]
        process = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, start_new_session=os.name != "nt")
        stage, trigger = None, {"tests": "Compiling ", "rustdoc": "Documenting "}
        for line in process.stdout:
            if line.startswith("::stage "):
                stage = line.split()[1]
            if UNIT_LINE.match(line):
                self.rebuilt += 1
            if kill and not self.triggered and stage == kill[0] and line.lstrip().startswith(trigger[stage]):
                self.triggered = True
                threading.Timer(kill[1], self.land, [process]).start()
        return process.wait()

    def sequence(self, position: str | None = None, kill: tuple[str, float] | None = None) -> int:
        """The three stages in the shape; the peer runs at `position`; the kill applies to its stage."""
        point = {"P0": None, "P1": "clippy", "P2": "tests"}.get(position)
        if self.shape == "single":
            if position == "P0":
                self.run_peer()
            return self.identity(STAGES, "atlas-pre-push", peer_after=point, kill=kill)
        status = 0
        for stage in STAGES:
            if position == {"clippy": "P0", "tests": "P1", "rustdoc": "P2"}[stage]:
                self.run_peer()
            key = "atlas-pre-push" if self.shape == "samekey" else f"atlas-pre-push-{stage}"
            code = self.identity((stage,), key, kill=kill if kill and kill[0] == stage else None)
            status = status or code
            if kill and kill[0] == stage and self.killed:
                return code
        return status

    def execute(self) -> dict:
        outcome = {"setup": self.setup, "shape": self.shape, "kind": self.kind, "position": self.position}
        try:
            self.build_fixture()
            if self.setup != "first":
                assert self.sequence() == 0, "the warm sequence failed"
            self.write_revision(self.source, 2, True)
            if self.setup == "sibling":
                self.identity(("clippy",), "atlas-pre-push-casts-base")
            if self.position.startswith("K"):
                stage = "tests" if self.position.startswith("KT") else "rustdoc"
                self.sequence(kill=(stage, float(self.position[2:])))
                self.run_peer()
                self.rebuilt, killed = 0, self.killed
                final = self.sequence()
                self.killed = killed
            else:
                if self.setup == "repush":
                    assert self.sequence() == 0, "the first R2 sequence failed"
                self.rebuilt = 0
                final = self.sequence(self.position)
            probe = (self.base / "probe.txt").read_text().strip() if (self.base / "probe.txt").exists() else None
            page = self.target / "doc" / "kcore" / "fn.value.html"
            documented = "2" if page.exists() and "The value is 2" in page.read_text(encoding="utf-8") else None
            outcome.update(probe=probe, doc=documented, final=final, rebuilt=self.rebuilt, killed=self.killed,
                           safe=final == 0 and probe == EXPECTED["probe"] and documented == EXPECTED["doc"])
        except Exception as error:  # a broken cell is reported, never dropped
            outcome.update(error=str(error)[-300:], safe=False)
        finally:
            shutil.rmtree(self.base, ignore_errors=True)
        return outcome


def render(results: list[dict]) -> str:
    """One table per setup: rows are peer kinds, columns positions, cells `ok|X(probe)/rebuilt`."""
    lines = []
    for shape in sorted({r["shape"] for r in results}):
        for setup in SETUPS:
            cells = {(r["kind"], r["position"]): r for r in results if r["shape"] == shape and r["setup"] == setup}
            if not cells:
                continue
            positions = [p for p in POSITIONS if any(k[1] == p for k in cells)]
            lines += [f"## {shape} / {setup}   (cell: safe|X(probe) / units rebuilt; ~ = kill did not land)",
                      "kind     " + "".join(f"{p:<14}" for p in positions)]
            for kind in KINDS:
                row = []
                for position in positions:
                    r = cells.get((kind, position))
                    text = "-" if r is None else "ERR" if "error" in r else (
                        ("ok" if r["safe"] else f"X({r['probe']})") + f"/{r['rebuilt']}" + ("" if r["killed"] or not position.startswith("K") else "~"))
                    row.append(f"{text:<14}")
                if any(k[0] == kind for k in cells):
                    lines.append(f"{kind:<8} " + "".join(row))
    return "\n".join(lines)


def compare(parent: list[dict], head: list[dict]) -> list[str]:
    """Cells safe at the parent and unsafe at the head, and cells that rebuild more units."""
    index = {(r["shape"], r["setup"], r["kind"], r["position"]): r for r in parent}
    problems = []
    for r in head:
        old = index.get((r["shape"], r["setup"], r["kind"], r["position"]))
        name = f"{r['shape']}/{r['setup']}/{r['kind']}/{r['position']}"
        if old and old["safe"] and not r["safe"]:
            problems.append(f"{name}: green at the parent, red at the head")
        elif old and old.get("rebuilt") is not None and r.get("rebuilt", 0) > old["rebuilt"]:
            problems.append(f"{name}: rebuilds {r['rebuilt']} units, parent {old['rebuilt']} (liveness)")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tree", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--shape", choices=SHAPES, default="single")
    parser.add_argument("--setup", choices=SETUPS, nargs="+", default=["repush"])
    parser.add_argument("--kind", choices=KINDS, nargs="+", default=list(KINDS))
    parser.add_argument("--position", choices=POSITIONS, nargs="+", default=list(POSITIONS))
    parser.add_argument("--functions", type=int, default=15000, help="generated functions in kcore")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--json", type=Path, help="write the cells here")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("PARENT", "HEAD"))
    args = parser.parse_args()
    if args.compare:
        problems = compare(*(json.loads(path.read_text()) for path in args.compare))
        print("\n".join(problems) or "no cell turned red or slower")
        return 1 if any("red" in p for p in problems) else 0
    cells = [Cell(args.tree, args.shape, s, k, p, args.functions) for s in args.setup for k in args.kind for p in args.position]
    with ThreadPoolExecutor(args.jobs) as pool:
        results = list(pool.map(Cell.execute, cells))
    if args.json:
        args.json.write_text(json.dumps(results))
    print(render(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
