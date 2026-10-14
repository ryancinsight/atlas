#!/usr/bin/env python3
"""Run Metis against its canonical Git lock outside Atlas's path overlay.

Path patches change dependency identities and cannot satisfy the canonical
lock. This runner preserves non-patch Cargo configuration, root build profiles
and the shared target directory. Metadata and every compilation use --locked;
provider revisions come from the lock, while Metis sources remain editable.
The temporary configuration lives outside Atlas and is removed on exit.

Usage: python3 scripts/atlas-metis.py [--manifest PATH] serve|dev|build|apple ...
Relative output paths refer to the caller's working directory. The default
manifest is the real metis-starter application. Builds leave canonical locks
unchanged and require published provider revisions.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / "repos/metis/Cargo.toml"
STARTER = ROOT / "repos/metis/crates/metis-starter/metis.json"


def cargo_configuration() -> str:
    """Preserve build settings without replacing canonical dependency sources."""
    config = {
        key: value for key, value in tomllib.loads(
            (ROOT / ".cargo/config.toml").read_text()
        ).items() if key != "patch"
    }
    config["build"]["target-dir"] = str(ROOT / config["build"]["target-dir"])
    return render(config)


def render(config: dict) -> str:
    """Serialize Cargo's nested tables without changing scalar values."""
    lines: list[str] = []
    def table(path: tuple[str, ...], values: dict) -> None:
        scalars = {key: value for key, value in values.items() if not isinstance(value, dict)}
        if scalars:
            lines.append("[" + ".".join(json.dumps(part) for part in path) + "]")
            lines.extend(json.dumps(key) + " = " + json.dumps(value) for key, value in scalars.items())
            lines.append("")
        for key, value in values.items():
            if isinstance(value, dict):
                table((*path, key), value)
    table((), config)
    return "\n".join(lines)


def command_arguments(arguments: list[str], manifest: Path, caller: Path) -> list[str]:
    """Select one manifest explicitly; keep Metis's option parser authoritative."""
    if not arguments or arguments[0] not in {"apple", "dev", "serve", "build"}:
        raise ValueError("choose apple build|run, dev, serve or build")
    position = 2 if arguments[0] == "apple" else 1
    if len(arguments) < position:
        raise ValueError("apple requires build or run")
    result = [*arguments[:position], str(manifest), *arguments[position:]]
    for index, argument in enumerate(result[:-1]):
        if argument == "--output":
            result[index + 1] = str(caller / result[index + 1])
    if arguments[0] == "build" and len(result) == 3:
        result[2] = str(caller / result[2])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=STARTER)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    caller = Path.cwd()
    arguments = command_arguments(options.arguments, options.manifest.resolve(strict=True), caller)
    configuration = cargo_configuration()
    toolchain = tomllib.loads((ROOT / "rust-toolchain.toml").read_text())["toolchain"]["channel"]
    env = {**os.environ, "RUSTUP_TOOLCHAIN": toolchain}
    if "CARGO_TARGET_DIR" in env:
        env["CARGO_TARGET_DIR"] = str((caller / env["CARGO_TARGET_DIR"]).resolve())
    with tempfile.TemporaryDirectory(prefix="atlas-metis-") as directory:
        context = Path(directory)
        (context / ".cargo").mkdir()
        (context / ".cargo/config.toml").write_text(configuration)
        subprocess.run(["cargo", "metadata", "--locked", "--format-version=1", "--manifest-path", str(WORKSPACE)],
                       cwd=context, env=env, stdout=subprocess.DEVNULL, check=True, timeout=120)
        subprocess.run(["cargo", "build", "--locked", "--manifest-path", str(WORKSPACE), "-p", "metis-cli"],
                       cwd=context, env=env, check=True, timeout=900)
        executable = Path(env.get("CARGO_TARGET_DIR", ROOT / "target")) / "debug" / ("metis.exe" if os.name == "nt" else "metis")
        return subprocess.run([str(executable.resolve()), *arguments], cwd=context, env=env, check=False).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f"Metis setup failed: {error}") from error
