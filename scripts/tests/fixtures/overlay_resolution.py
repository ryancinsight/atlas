"""Local Git/Cargo resolver fixture; no network or native test binaries.

The Git source contains an old revision and a current revision. A separate
local provider contains the current core and transport with a path edge.
Cargo metadata reveals whether direct and transitive core references unify;
checking the consumer verifies their token types agree.

Everything the fixture's cargo invocations touch is scoped to the tempdir it
is given -- `CARGO_HOME`, `CARGO_TARGET_DIR` and the Git config alike -- so a run
neither reads machine state nor contends for it.
"""

from __future__ import annotations

import json
import os
import subprocess
import tomllib
from pathlib import Path

# `cargo metadata` and the fixture's own Git plumbing only read and resolve;
# neither runs the compiler, and a healthy invocation finishes in seconds. Keep
# a tight budget here so a resolver that stops making progress fails the
# fixture instead of stalling the suite.
RESOLUTION_TIMEOUT_SECONDS = 30

# `CargoOverlayFixture.check` runs `cargo check`, which compiles rather than
# resolves, so it must not be bounded by the resolution budget above: a 30s
# bound reported a false failure on a cold compile. The build is three trivial
# crates into a target directory that exists only for this fixture (see
# `target`), so it cannot wait on another process's build lock; the whole test
# measures 1.5s here, cold every run. This bound is therefore a hang guard, not
# a performance assertion, and the headroom is deliberate: a CI runner an order
# of magnitude slower than this machine still fits, and a command that hangs
# still fails the fixture instead of stalling the suite. Nothing below is
# relaxed; the assertions the check exists for (selected packages, unified
# token types) must still hold however long the build takes.
COMPILE_TIMEOUT_SECONDS = 120


class CargoOverlayFixture:
    """Construct isolated source and consumer manifests inside a test tempdir."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.source = root / "source"
        self.consumer = root / "consumer"
        self.local = root / "repos" / "provider"
        # The fixture's own build cache, inside the tempdir it already owns and
        # deleted with it. It must not be the stack's shared `target/`: the
        # stack routes every repo through one `CARGO_TARGET_DIR` and the root
        # config accepts that concurrent builds serialize on its build lock, so
        # a fixture building there makes its own duration a function of
        # whatever else is compiling on the machine -- and turns a fixed bound
        # on a compile into a report about someone else's build. Pinned
        # explicitly rather than left to the ambient environment, which the
        # stack's bootstrap scripts export.
        self.target = root / "target"
        self.environment = dict(os.environ)
        global_config = root / "gitconfig"
        global_config.write_text("", encoding="utf-8")
        self.environment.update(
            CARGO_HOME=str(root / "cargo-home"),
            CARGO_TARGET_DIR=str(self.target),
            GIT_CONFIG_GLOBAL=str(global_config),
            GIT_CONFIG_NOSYSTEM="1",
        )
        self.source.mkdir()
        self.run(["git", "init", "--quiet"], self.source)
        self.run(["git", "config", "user.name", "Overlay fixture"], self.source)
        self.run(["git", "config", "user.email", "overlay@example.invalid"], self.source)
        self.write_provider(self.source, "0.5.0")
        self.run(["git", "add", "Cargo.toml", "core", "transport"], self.source)
        self.run(["git", "commit", "--quiet", "-m", "Add old provider"], self.source)
        previous = self.run(["git", "rev-parse", "HEAD"], self.source).strip()
        self.write_provider(self.source, "0.6.0")
        self.run(["git", "add", "core/Cargo.toml", "transport/Cargo.toml"], self.source)
        self.run(["git", "commit", "--quiet", "-m", "Advance provider"], self.source)
        self.write_provider(self.local, "0.6.0")
        self.url = self.source.as_uri()
        self.consumer.mkdir()
        (self.consumer / "src").mkdir()
        (self.consumer / "src" / "lib.rs").write_text(
            "pub fn forward(token: active_core::Token) -> active_core::Token {\n"
            "    transport::forward(token)\n}\n", encoding="utf-8"
        )
        (self.consumer / "Cargo.toml").write_text(
            '[package]\nname = "overlay-consumer"\nversion = "0.1.0"\nedition = "2024"\n'
            '[dependencies]\n'
            f'previous_core = {{ package = "overlay-core", git = "{self.url}", '
            f'version = "^0.5", rev = "{previous}" }}\n'
            f'active_core = {{ package = "overlay-core", git = "{self.url}", version = "^0.6" }}\n'
            f'transport = {{ package = "overlay-transport", git = "{self.url}", version = "^0.6" }}\n',
            encoding="utf-8",
        )

    @staticmethod
    def write_provider(root: Path, version: str) -> None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "Cargo.toml").write_text(
            '[workspace]\nmembers = ["core", "transport"]\nresolver = "3"\n',
            encoding="utf-8",
        )
        for package in ("core", "transport"):
            directory = root / package
            (directory / "src").mkdir(parents=True, exist_ok=True)
            manifest = (
                f'[package]\nname = "overlay-{package}"\nversion = "{version}"\n'
                'edition = "2024"\n'
            )
            if package == "transport":
                manifest += '[dependencies]\noverlay-core = { path = "../core" }\n'
                source = "pub fn forward(token: overlay_core::Token) -> overlay_core::Token { token }\n"
            else:
                source = "pub struct Token;\n"
            (directory / "Cargo.toml").write_text(manifest, encoding="utf-8")
            (directory / "src" / "lib.rs").write_text(source, encoding="utf-8")

    def run(
        self,
        command: list[str],
        cwd: Path,
        timeout: int = RESOLUTION_TIMEOUT_SECONDS,
    ) -> str:
        try:
            result = subprocess.run(command, cwd=cwd, env=self.environment, text=True,
                                    capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as expired:
            # Reported as the fixture's own failure, naming the budget that was
            # exceeded, so a genuine hang stays a defect instead of surfacing
            # as an opaque traceback that reads like an environment problem.
            raise AssertionError(
                f"{command[0]} did not finish within {timeout}s: {' '.join(command)}"
            ) from expired
        if result.returncode:
            raise AssertionError(f"{command[0]} failed ({result.returncode}):\n{result.stderr}")
        return result.stdout

    def resolve(self, block: str, toolchain: str) -> dict:
        configuration = self.root / ".cargo"
        configuration.mkdir(exist_ok=True)
        (configuration / "config.toml").write_text(block, encoding="utf-8")
        # Resolved from the fixture's own directory, so the only configuration
        # discovered is the block under test: cargo walks up from the working
        # directory, and a run from an Atlas checkout would additionally apply
        # the root config's whole stack `[patch]` overlay to a graph that
        # shares none of it. Config discovery is all-or-nothing, so the one key
        # the fixture used to want from there (the shared `target-dir`) could
        # not be had without the other; `target` supplies its own instead. The
        # overlay cost nothing measurable here -- its patch sources are absent
        # from this graph, and the old route measured 1.28s against 1.60s for
        # this one (2026-09-16) -- so both changes are isolation, not speed.
        return json.loads(self.run(
            ["cargo", f"+{toolchain}", "metadata", "--format-version", "1",
             "--manifest-path", str(self.consumer / "Cargo.toml"),
             "--config", str(configuration / "config.toml")], self.root
        ))

    def check(self, toolchain: str) -> None:
        # Only source resolution is fixture-owned; the build writes to the
        # fixture's own `target`, so nothing is added to the stack cache and
        # nothing waits on it. This is a compile of the fixture's closure,
        # hence the compile budget rather than the resolution one.
        # Cargo 1.97 rewrites ordering of unrelated [[patch.unused]] records
        # between invocations. Assert selected packages remain identical rather
        # than treating that derived ordering as a dependency change.
        lock = self.consumer / "Cargo.lock"
        before = tomllib.loads(lock.read_text(encoding="utf-8"))["package"]
        self.run(["cargo", f"+{toolchain}", "check", "--offline",
                  "--manifest-path", str(self.consumer / "Cargo.toml"),
                  "--config", str(self.root / ".cargo" / "config.toml")], self.root,
                 timeout=COMPILE_TIMEOUT_SECONDS)
        after = tomllib.loads(lock.read_text(encoding="utf-8"))["package"]
        if before != after:
            raise AssertionError("Cargo check changed the fixture's selected package graph")
