#!/usr/bin/env python3
"""Peer-write and kill matrix for the pre-push stage sequence, on real Cargo.

Each cell builds a fixture (kcore with a build script and a large generated
module, kapp with a probe test, Git crate kgit) in its own temporary directory
and drives `atlas-build-identity.py run` of the tree under test with the
hook's stage commands. A cell reports whether the final complete sequence is
sound (the probe, every kcore `gen.rs` and the rustdoc pages of `value` and
`GEN` equal the current revision's) and how many units it rebuilt: the
`.fingerprint` and `build` directories whose files changed in name, mtime or
size across it. A cleaner that rebuilds everything is sound everywhere and
proves nothing. An unexpected exit makes the cell ERR; a kill lands only
while the intended stage runs. Pass `--root` a short directory on Windows.

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
import stat
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


def _commit(cwd, message: str) -> None:
    _git(cwd, "init", "-q")
    _git(cwd, "add", ".")
    _git(cwd, "commit", "-q", "-m", message)


def _tree_kill(process: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
    else:
        os.killpg(process.pid, signal.SIGKILL)


def _remove(path: Path) -> None:
    """Delete a tree, clearing the read-only bit Git sets on its objects; a failure is raised."""
    shutil.rmtree(path, onerror=lambda function, name, _error: (os.chmod(name, stat.S_IWRITE), function(name)))


def _expect(code: int, what: str) -> None:
    if code:
        raise RuntimeError(f"{what} exited {code}")


class Cell:
    def __init__(self, tree: Path, shape: str, setup: str, kind: str, position: str, functions: int, root: Path | None):
        self.scripts, self.shape, self.setup, self.kind, self.position = tree / "scripts", shape, setup, kind, position
        self.functions = functions
        self.base = Path(tempfile.mkdtemp(prefix="sm-", dir=root))  # unresolved: a subst drive stays short
        self.source, self.peer, self.target = self.base / "ws", self.base / "peer", self.base / "target"
        self.environment = {k: v for k, v in os.environ.items() if k != "CARGO_TARGET_DIR"}
        self.environment.update(PROBE_OUT=str(self.base / "probe.txt"), CARGO_HOME=str(self.base / "c"))
        self.stage = self.landed = None
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
        environment = {**self.environment, "PEER_KIND": self.kind, "PEER_DIR": str(self.peer),
                       "PEER_TARGET": self.target.resolve().as_posix()}
        code = subprocess.run([sys.executable, str(self.base / "peer.py")], env=environment, capture_output=True,
                              timeout=900).returncode
        if code:
            raise RuntimeError(f"the {self.kind} peer exited {code}")

    def land(self, process: subprocess.Popen, wanted: str) -> None:
        self.landed = self.stage if process.poll() is None else "exited"
        if self.landed == wanted:
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
        trigger = {"tests": "Compiling ", "rustdoc": "Documenting "}
        for line in process.stdout:
            if line.startswith("::stage "):
                self.stage = line.split()[1]
            if kill and not self.triggered and self.stage == kill[0] and line.lstrip().startswith(trigger[self.stage]):
                self.triggered = True
                threading.Timer(kill[1], self.land, [process, kill[0]]).start()
        return process.wait()

    def sequence(self, position: str | None = None, kill: tuple[str, float] | None = None) -> int:
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

    def units(self) -> dict[str, tuple]:
        return {p.relative_to(self.target).as_posix(): (p.stat().st_mtime_ns, p.stat().st_size)
                for part in (".fingerprint", "build") for p in (self.target / "debug" / part).rglob("*") if p.is_file()}

    def verdict(self, final: int) -> dict:
        probe = (self.base / "probe.txt").read_text().strip() if (self.base / "probe.txt").exists() else None
        gens = sorted({p.read_text().strip() for p in (self.target / "debug" / "build").glob("kcore-*/out/gen.rs")})
        page = lambda name: re.sub(r"<[^>]+>", "", (self.target / "doc" / "kcore" / name).read_text(encoding="utf-8"))  # noqa: E731
        try:
            documented = "The value is 2" in page("fn.value.html") and re.search(r"GEN: u32 = 20(?![0-9])", page("constant.GEN.html"))
        except OSError:
            documented = False
        why = (f"rc{final}" if final else probe if probe != EXPECTED["probe"] else "gen" if gens != [EXPECTED["gen"]]
               else None if documented else "page")
        return {"probe": probe, "gens": gens, "why": why, "safe": why is None}

    def execute(self) -> dict:
        outcome = {"setup": self.setup, "shape": self.shape, "kind": self.kind, "position": self.position}
        try:
            self.build_fixture()
            if self.setup != "first":
                _expect(self.sequence(), "the warm sequence")
            self.write_revision(self.source, 2, True)
            if self.setup == "sibling":
                # Another command key over the same build: its record can stand in for the stage's own.
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
            _expect(99 if final == 99 else 0, "the peer inside the sequence")
            after = self.units()
            changed = {"/".join(k.split("/")[1:3]) for k in before.keys() | after.keys() if before.get(k) != after.get(k)}
            outcome.update(self.verdict(final), final=final, rebuilt=len(changed), killed=self.killed, landed=self.landed)
        except Exception as error:  # a broken cell is reported, never dropped
            outcome.update(error=str(error)[-300:], safe=False)
        finally:
            _remove(self.base)
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
    for old in parent:
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
