"""Local Git/Cargo resolver fixture; no network or native test binaries.

The Git source contains an old revision and a current revision. A separate
local provider contains the current core and transport with a path edge.
Cargo metadata reveals whether direct and transitive core references unify;
checking the consumer verifies their token types agree.
"""

from __future__ import annotations

import json
import os
import subprocess
import tomllib
from pathlib import Path


class CargoOverlayFixture:
    """Construct isolated source and consumer manifests inside a test tempdir."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.source = root / "source"
        self.consumer = root / "consumer"
        self.local = root / "repos" / "provider"
        self.environment = dict(os.environ)
        global_config = root / "gitconfig"
        global_config.write_text("", encoding="utf-8")
        self.environment.update(
            CARGO_HOME=str(root / "cargo-home"),
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

    def run(self, command: list[str], cwd: Path) -> str:
        result = subprocess.run(command, cwd=cwd, env=self.environment, text=True,
                                capture_output=True, timeout=30, check=False)
        if result.returncode:
            raise AssertionError(f"{command[0]} failed ({result.returncode}):\n{result.stderr}")
        return result.stdout

    def resolve(self, block: str, toolchain: str, stack_root: Path) -> dict:
        configuration = self.root / ".cargo"
        configuration.mkdir(exist_ok=True)
        (configuration / "config.toml").write_text(block, encoding="utf-8")
        return json.loads(self.run(
            ["cargo", f"+{toolchain}", "metadata", "--format-version", "1",
             "--manifest-path", str(self.consumer / "Cargo.toml"),
             "--config", str(configuration / "config.toml")], stack_root
        ))

    def check(self, toolchain: str, stack_root: Path) -> None:
        # Running beneath Atlas inherits its sole shared target directory.
        # Only source resolution is fixture-owned; no private target is created.
        # Cargo 1.97 rewrites ordering of unrelated [[patch.unused]] records
        # between invocations. Assert selected packages remain identical rather
        # than treating that derived ordering as a dependency change.
        lock = self.consumer / "Cargo.lock"
        before = tomllib.loads(lock.read_text(encoding="utf-8"))["package"]
        self.run(["cargo", f"+{toolchain}", "check", "--offline",
                  "--manifest-path", str(self.consumer / "Cargo.toml"),
                  "--config", str(self.root / ".cargo" / "config.toml")], stack_root)
        after = tomllib.loads(lock.read_text(encoding="utf-8"))["package"]
        if before != after:
            raise AssertionError("Cargo check changed the fixture's selected package graph")
