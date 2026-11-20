"""Build and use the pinned SemVer checker in one owned lifetime."""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import time
import tomllib
from atlas_cargo_home import cargo_home
from atlas_build_source import cargo_config_digest, cargo_config_without_patches
from atlas_git_process import archive, execute, extract_archive
import process_tree
SOURCE_SECONDS, BUILD_SECONDS = 120, 600
_PIN_FIELDS = {"repository", "revision", "tree", "package", "version", "rust_version", "toolchain"}
_ALLOWED_CARGO_ENV = {"CARGO", "CARGO_HOME", "CARGO_LOG", "CARGO_TARGET_DIR",
                      "CARGO_REGISTRY_TOKEN", "CARGO_REGISTRY_GLOBAL_CREDENTIAL_PROVIDERS"}
_ALLOWED_CARGO_PREFIXES = ("CARGO_CACHE_", "CARGO_CREDENTIAL_ALIAS_", "CARGO_HTTP_", "CARGO_NET_",
                           "CARGO_TERM_")

def _text(value: bytes | None) -> str:
    return (value or b"").decode("utf-8", errors="replace")
def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
def _remaining(started: float, ceiling: float) -> float:
    remaining = BUILD_SECONDS - (time.monotonic() - started)
    if remaining <= 0:
        raise RuntimeError("SemVer checker setup exceeded its 600-second deadline")
    return min(ceiling, remaining)
def _record(command: list[str], result, elapsed: float) -> dict[str, object]:
    return {"command": command, "exit_code": result.returncode, "duration_seconds": elapsed,
            "stdout": _text(result.stdout), "stderr": _text(result.stderr)}
def _run(command: list[str], cwd: Path, env: dict[str, str], timeout: float,
         records: list[dict[str, object]]):
    started = time.monotonic()
    result = process_tree.run(command, cwd=cwd, env=env, timeout=timeout)
    record = _record(command, result, time.monotonic() - started)
    records.append(record)
    if result.returncode:
        raise RuntimeError(f"command exited {result.returncode}: {command!r}\n"
                           f"{record['stdout']}{record['stderr']}")
    return result
def _git(repo: Path, arguments: tuple[str, ...], env: dict[str, str],
         records: list[dict[str, object]]):
    command = ["git", "-C", str(repo), *arguments]
    started = time.monotonic()
    result = execute(repo, arguments, env=env, timeout=SOURCE_SECONDS)
    record = _record(command, result, time.monotonic() - started)
    records.append(record)
    if result.returncode:
        raise RuntimeError(f"Git exited {result.returncode}: {command!r}\n"
                           f"{record['stdout']}{record['stderr']}")
    return result
def _pin(path: Path) -> dict[str, str]:
    values = tomllib.loads(path.read_text(encoding="utf-8"))
    if set(values) != _PIN_FIELDS or any(
            not isinstance(value, str) or not value for value in values.values()):
        raise ValueError(f"invalid SemVer tool pin fields in {path}")
    return values
def _source_inputs(source: Path, pin: dict[str, str]) -> dict[str, str]:
    manifest, lock = source / "Cargo.toml", source / "Cargo.lock"
    try:
        package = tomllib.loads(manifest.read_text(encoding="utf-8"))["package"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as error:
        raise RuntimeError(f"cannot validate SemVer source manifest: {error}") from error
    observed = (package.get("name"), package.get("version"), package.get("rust-version"))
    expected = (pin["package"], pin["version"], pin["rust_version"])
    if observed != expected or not lock.is_file():
        raise RuntimeError(f"SemVer source manifest or lock differs: {observed!r}")
    return {"manifest_sha256": _digest(manifest), "lock_sha256": _digest(lock)}
def _source(root: Path, pin: dict[str, str], records: list[dict[str, object]],
            env: dict[str, str]) -> tuple[Path, dict[str, str]]:
    objects, source = root / "objects", root / "source"
    objects.mkdir()
    git_env = dict(env, GIT_NO_REPLACE_OBJECTS="1")
    _git(objects, ("init", "--bare"), git_env, records)
    _git(objects, ("fetch", "--no-tags", "--depth=1", pin["repository"], pin["revision"]),
         git_env, records)
    commit = _text(_git(objects, ("rev-parse", "--verify", "--end-of-options", "FETCH_HEAD^{commit}"),
                        git_env, records).stdout).strip()
    tree = _text(_git(objects, ("rev-parse", "--verify", "--end-of-options", "FETCH_HEAD^{tree}"),
                      git_env, records).stdout).strip()
    if (commit, tree) != (pin["revision"], pin["tree"]):
        raise RuntimeError(f"fetched SemVer source identity changed: {commit} {tree}")
    payload = archive(objects, commit, env=git_env, timeout=SOURCE_SECONDS)
    records.append({"command": ["git", "-C", str(objects), "archive", "--format=tar",
                                        f"{commit}^{{tree}}"], "exit_code": 0,
                    "archive_sha256": hashlib.sha256(payload).hexdigest()})
    source.mkdir()
    extract_archive(payload, source)
    return source, _source_inputs(source, pin)
def _tools(pin: dict[str, str], root: Path, env: dict[str, str],
           records: list[dict[str, object]]) -> dict[str, dict[str, str]]:
    rustup_name = shutil.which("rustup")
    if rustup_name is None:
        raise RuntimeError("rustup is required to resolve the pinned build toolchain")
    rustup = str(Path(rustup_name).resolve(strict=True))
    tools: dict[str, dict[str, str]] = {}
    for name in ("cargo", "rustc", "rustdoc"):
        result = _run([rustup, "which", "--toolchain", pin["toolchain"], name],
                      root, env, SOURCE_SECONDS, records)
        path = Path(_text(result.stdout).strip()).resolve(strict=True)
        version = _text(_run([str(path), "-Vv" if name == "cargo" else "-vV"],
                             root, env, SOURCE_SECONDS, records).stdout).strip()
        if f"release: {pin['toolchain']}" not in version.splitlines():
            raise RuntimeError(f"{name} does not report release {pin['toolchain']}: {version!r}")
        tools[name] = {"path": str(path), "version": version, "sha256": _digest(path)}
    return tools
def _build_environment(source: dict[str, str], tools: dict[str, dict[str, str]],
                       pin: dict[str, str], target: Path) -> dict[str, str]:
    overrides = sorted(name for name, value in source.items() if value and (
        (name.startswith("CARGO_") and name not in _ALLOWED_CARGO_ENV and
         not name.startswith(_ALLOWED_CARGO_PREFIXES) and not (
             name.startswith("CARGO_REGISTRIES_") and name.endswith(("_TOKEN", "_CREDENTIAL_PROVIDER", "_PROTOCOL")))) or
        name.startswith("RUSTC_") or name in {"RUSTFLAGS", "RUSTDOCFLAGS"}))
    if overrides:
        raise RuntimeError(f"build environment contains overrides: {', '.join(overrides)}")
    result = dict(source)
    for name, key in (("CARGO", "cargo"), ("RUSTC", "rustc"), ("RUSTDOC", "rustdoc")):
        expected = tools[key]["path"]
        if result.get(name) and Path(result[name]).resolve() != Path(expected):
            raise RuntimeError(f"{name} does not match the pinned build toolchain")
        result[name] = expected
    result.update({"RUSTUP_TOOLCHAIN": pin["toolchain"], "CARGO_TARGET_DIR": str(target)})
    return result
def _config_identity(cwd: Path, env: dict[str, str], arguments: tuple[str, ...]) -> str:
    directory, ambient = cwd.resolve(), []
    while True:
        ambient.extend(path for name in ("config.toml", "config")
                       if (path := directory / ".cargo" / name).is_file())
        if directory.parent == directory:
            break
        directory = directory.parent
    home = cargo_home(env, cwd.resolve())
    ambient.extend(path for name in ("config.toml", "config")
                   if (path := home / name).is_file())
    if ambient:
        raise RuntimeError("ambient Cargo configuration is not admitted: " +
                           ", ".join(str(path) for path in ambient))
    return cargo_config_digest(cwd, arguments, env)
@dataclass(frozen=True)
class _PreparedChecker:
    executable: Path
    provenance: dict[str, object]
    sha256: str
    workspace: Path
    def verify(self) -> None:
        if _digest(self.executable) != self.sha256:
            raise RuntimeError("prepared cargo-semver-checks executable changed during use")
    def command(self, arguments: list[str]) -> list[str]:
        self.verify()
        return [str(self.executable), "semver-checks", *arguments]

@contextmanager
def prepared_checker(pin_path: Path | None = None, atlas_root: Path | None = None):
    """Yield the checker built from the committed pin, then remove only its workspace."""
    started = time.monotonic()
    scripts = Path(__file__).resolve().parent
    pin = _pin(pin_path or scripts / "semver-tool.toml")
    atlas = (atlas_root or scripts.parent).resolve(strict=True)
    thread = os.environ.get("CODEX_THREAD_ID")
    session = Path(tempfile.gettempdir()) / f"codex-{thread}" if thread else Path(tempfile.gettempdir())
    session.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="semver-tool-", dir=session) as name:
        root = Path(name)
        records: list[dict[str, object]] = []
        env = dict(os.environ)
        source, hashes = _source(root, pin, records, env)
        config = root / "config.toml"
        config.write_text(cargo_config_without_patches(atlas / ".cargo" / "config.toml"),
                          encoding="utf-8", newline="\n")
        if "patch" in tomllib.loads(config.read_text(encoding="utf-8")):
            raise RuntimeError("neutral Cargo configuration retains development patches")
        target_name = env.get("CARGO_TARGET_DIR")
        if not target_name or not Path(target_name).is_absolute():
            raise RuntimeError("CARGO_TARGET_DIR must name Atlas's absolute shared target")
        target = Path(target_name).resolve(strict=True)
        tools = _tools(pin, root, env, records)
        env = _build_environment(env, tools, pin, target)
        install, neutral = root / "install", root / "neutral"
        install.mkdir()
        neutral.mkdir()
        config_args = (str(config), "profile.release.lto=false")
        config_hash = _config_identity(neutral, env, config_args)
        build = [tools["cargo"]["path"], "--config", config_args[0], "--config",
                 config_args[1], "install", "--locked", "--path", str(source),
                 "--root", str(install), "--bin", "cargo-semver-checks"]
        _run(build, neutral, env, _remaining(started, BUILD_SECONDS), records)
        if config_hash != _config_identity(neutral, env, config_args):
            raise RuntimeError("Cargo configuration changed during build")
        if any(_digest(Path(tool["path"])) != tool["sha256"] for tool in tools.values()):
            raise RuntimeError("pinned build tool changed during build")
        if hashes != {
            "manifest_sha256": _digest(source / "Cargo.toml"),
            "lock_sha256": _digest(source / "Cargo.lock"),
        }:
            raise RuntimeError("SemVer source inputs changed during build")
        executable = install / "bin" / (
            "cargo-semver-checks.exe" if os.name == "nt" else "cargo-semver-checks")
        binary_hash = _digest(executable)
        version = _text(_run([str(executable), "semver-checks", "--version"], neutral, env,
                             _remaining(started, SOURCE_SECONDS), records).stdout).strip()
        if version != f"cargo-semver-checks {pin['version']}":
            raise RuntimeError(f"built checker reported an unexpected version: {version!r}")
        provenance = {
            "version": version, "sha256": binary_hash, "executable": str(executable),
            "source": {**pin, **hashes},
            "build": {
                "tools": tools, "config_sha256": config_hash,
                "config_overrides": ["profile.release.lto=false"],
                "target_dir": str(target), "commands": records,
            },
        }
        checker = _PreparedChecker(executable, provenance, binary_hash, root)
        checker.verify()
        yield checker
        checker.verify()
