#!/usr/bin/env python3
"""Permit a release retry to skip publishing only for identical verified bytes."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import random
import re
import ssl
import struct
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import tomllib
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request

METADATA_LIMIT = 16 * 1024 * 1024
REGISTRY_REQUEST_SECONDS = 30.0
API_INTERVAL_SECONDS = 1.0
API_PREFIX = "https://crates.io/api/"
TRANSPORT_ATTEMPTS = 5
TRANSPORT_BACKOFF_SECONDS = 2.0
REGISTRY_ERROR_CHAIN_ITEMS = 8
REGISTRY_ERROR_TEXT = 1024
REGISTRY_ERROR_TYPE_TEXT = 128
REGISTRY_ERROR_PROTOCOL_BYTES = 16 * 1024
REGISTRY_STDERR_BYTES = 4 * 1024
JSON_NESTING_DEPTH = 32
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\Z")
PRERELEASE = r"(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
                     + rf"(?:-{PRERELEASE}(?:\.{PRERELEASE})*)?"
                     + r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\Z")


class IdentityError(ValueError):
    """A release identity is absent, ambiguous, or inconsistent."""


class RegistryTransportError(IdentityError):
    """A transient network failure prevented a complete registry response."""


def _load_exact_module(source, role):
    """Load one exact action dependency under a per-invocation private identity."""
    source = source.resolve()
    if not source.is_file():
        raise IdentityError(f"required {role} source is absent from the action revision")
    token = object()
    name = f"_atlas_release_{role}_{id(_load_exact_module):x}_{id(token):x}"
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise IdentityError(f"required {role} source cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    if Path(module.__file__).resolve() != source:
        raise IdentityError(f"required {role} source origin differs from the action revision")
    return module


registry_http = _load_exact_module(
    Path(__file__).resolve().with_name("registry_http.py"), "registry_http"
)


def unique_object(pairs):
    """Reject duplicate JSON keys instead of silently accepting the last."""
    value = {}
    for key, item in pairs:
        if key in value:
            raise IdentityError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def parse_json(data):
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise IdentityError("registry JSON is not strict UTF-8") from error
    elif not isinstance(data, str):
        raise IdentityError("registry JSON must be text or UTF-8 bytes")

    depth = 0
    quoted = False
    escaped = False
    for character in data:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            if depth > JSON_NESTING_DEPTH:
                raise IdentityError("registry JSON nesting exceeds the identity bound")
        elif character in "]}":
            depth -= 1

    def invalid_constant(value):
        raise IdentityError(f"invalid JSON constant: {value}")
    try:
        return json.loads(data, object_pairs_hook=unique_object, parse_constant=invalid_constant)
    except RecursionError as error:
        raise IdentityError("registry JSON nesting exceeds the identity bound") from error


def command(args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, check=True, timeout=1800)
    return result.stdout


def git(root, *args):
    return command(["git", "-C", str(root), *args], root)


def clean_checkout(root, expected):
    if git(root, "rev-parse", "HEAD").decode().strip() != expected:
        raise IdentityError("checkout HEAD differs from the release revision")
    if git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise IdentityError("release checkout is dirty")


def committed_file(root, path):
    path = path.resolve().relative_to(root)
    return git(root, "show", f"HEAD:{path.as_posix()}")


@dataclass(frozen=True)
class Package:
    name: str
    version: str
    commit: str
    path: str
    archive: bytes

    @property
    def checksum(self):
        return hashlib.sha256(self.archive).hexdigest()


def archive_files(package):
    """Inspect a locally generated archive without extracting any tar paths."""
    prefix = f"{package.name}-{package.version}"
    files = {}
    with tarfile.open(fileobj=io.BytesIO(package.archive), mode="r:gz") as archive:
        seen = set()
        for entry in archive:
            parts = entry.name.split("/")
            if (entry.name in seen or len(parts) < 2 or parts[0] != prefix
                    or entry.name.startswith("/") or any(p in ("", ".", "..") for p in parts)
                    or not entry.isfile()):
                raise IdentityError("duplicate, unsafe, or non-file package entry")
            seen.add(entry.name)
            stream = archive.extractfile(entry)
            if stream is None:
                raise IdentityError("unreadable package entry")
            files["/".join(parts[1:])] = stream.read()
    required = {"Cargo.toml", "Cargo.toml.orig", "Cargo.lock", ".cargo_vcs_info.json"}
    if not required <= files.keys():
        raise IdentityError("package lacks manifest, lockfile, or VCS provenance")
    vcs = parse_json(files[".cargo_vcs_info.json"])
    info = vcs.get("git", {})
    if (info.get("sha1") != package.commit or info.get("dirty", False) is not False
            or vcs.get("path_in_vcs") != package.path):
        raise IdentityError("archive VCS identity differs from the clean release checkout")
    manifest = tomllib.loads(files["Cargo.toml"].decode())["package"]
    if manifest.get("name") != package.name or manifest.get("version") != package.version:
        raise IdentityError("archive package/version differs from the validated release")
    return files


def package_release(name, version, expected_commit, cwd=None):
    """Regenerate and Cargo-verify expected bytes in this publish job."""
    cwd = Path.cwd() if cwd is None else Path(cwd)
    if not NAME.fullmatch(name) or not VERSION.fullmatch(version) or not COMMIT.fullmatch(expected_commit):
        raise IdentityError("invalid release package or expected commit")
    root = Path(command(["git", "rev-parse", "--show-toplevel"], cwd).decode().strip()).resolve()
    clean_checkout(root, expected_commit)
    metadata = parse_json(command(["cargo", "metadata", "--locked", "--no-deps", "--format-version", "1"], cwd))
    matches = [p for p in metadata["packages"] if p["name"] == name and p["id"] in metadata["workspace_members"]]
    if len(matches) != 1 or matches[0]["version"] != version:
        raise IdentityError("expected exactly one workspace package at the release version")
    selected = matches[0]
    if selected.get("publish") is not None and "crates-io" not in selected["publish"]:
        raise IdentityError("package does not permit crates.io publication")
    manifest = Path(selected["manifest_path"]).resolve()
    relative = manifest.parent.relative_to(root).as_posix()
    relative = "" if relative == "." else relative
    # A generated or ignored workspace lock is not committed release provenance.
    lock = Path(metadata["workspace_root"]) / "Cargo.lock"
    if committed_file(root, lock) != lock.read_bytes():
        raise IdentityError("workspace lock differs from committed release provenance")
    with tempfile.TemporaryDirectory(prefix="atlas-release-identity-") as directory:
        command(["cargo", "package", "--locked", "--package", name, "--target-dir", directory], cwd)
        archive = (Path(directory) / "package" / f"{name}-{version}.crate").read_bytes()
    clean_checkout(root, expected_commit)
    package = Package(name, version, expected_commit, relative, archive)
    files = archive_files(package)
    if files["Cargo.toml.orig"] != committed_file(root, manifest):
        raise IdentityError("packaged original manifest differs from committed source")
    generated = {"Cargo.toml", "Cargo.toml.orig", "Cargo.lock", ".cargo_vcs_info.json"}
    for entry, content in files.items():
        if entry in generated:
            continue
        source = manifest.parent / entry
        # Cargo flattens workspace-inherited readme/license files into the crate.
        if not source.exists():
            candidates = [manifest.parent / selected[key] for key in ("readme", "license_file") if selected.get(key)]
            candidates = [p for p in candidates if p.name == entry]
            if len(candidates) != 1:
                raise IdentityError(f"unverified archive source: {entry}")
            source = candidates[0]
        if content != committed_file(root, source):
            raise IdentityError(f"archive differs from committed source: {entry}")
    clean_checkout(root, expected_commit)
    return package


class RegistryWorkerError(RuntimeError):
    """A bounded transport child reported a typed exception chain."""

    def __init__(self, chain):
        self.chain = tuple(chain)
        summary = " -> ".join(f"{item['type']}: {item['message']}" for item in self.chain)
        super().__init__(summary)


def _raise_registry_io(error, url):
    """Classify one typed registry transport or framing failure."""
    reason = error.reason if isinstance(error, URLError) else error
    if isinstance(reason, ssl.SSLCertVerificationError):
        raise IdentityError(f"registry TLS certificate verification failed: {url}") from error
    if isinstance(reason, ssl.SSLEOFError):
        raise RegistryTransportError(f"registry response failed: {url}: {reason}") from error
    if isinstance(reason, ssl.SSLError):
        raise IdentityError(f"registry TLS protocol failed: {url}") from error
    if isinstance(reason, registry_http.RegistryFramingError):
        raise IdentityError(
            f"malformed registry HTTP response framing: {url}: {reason}") from error
    if isinstance(reason, (registry_http.RegistryBodyDisconnect, http.client.IncompleteRead,
                           http.client.RemoteDisconnected, TimeoutError, OSError)):
        raise RegistryTransportError(f"registry response failed: {url}: {reason}") from error
    if isinstance(reason, http.client.HTTPException):
        raise IdentityError(f"malformed registry HTTP response: {url}: {reason}") from error
    if isinstance(error, URLError):
        raise RegistryTransportError(f"registry request failed: {url}: {error}") from error
    raise error


def _read_url_once(url, limit):
    """Read public registry data with bounded time/size and no authentication."""
    request = Request(url, headers={"User-Agent": "atlas-release-identity (https://github.com/ryancinsight/atlas)"})
    try:
        try:
            response = registry_http.open_response(request, timeout=30)
        except HTTPError as error:
            response = error
        with response:
            fields = getattr(response, "atlas_fields", None)
            if fields is None:
                fields = tuple(
                    (name.lower().encode("ascii"), value.strip(" \t").encode("iso-8859-1"))
                    for name, value in response.headers.raw_items())
            length, _chunked = registry_http.framing_fields(fields)
            if length is not None and length > limit:
                raise IdentityError(f"registry response exceeds identity bound: {url}")
            body = response.read(limit + 1)
            if len(body) > limit:
                raise IdentityError(f"registry response exceeds identity bound: {url}")
            if length is not None and len(body) != length:
                raise RegistryTransportError("incomplete registry HTTP body")
            status = response.status
    except IdentityError:
        raise
    except (URLError, TimeoutError, OSError, http.client.HTTPException) as error:
        _raise_registry_io(error, url)
    if status == 429 or 500 <= status <= 599:
        raise RegistryTransportError(f"transient registry HTTP status {status}: {url}")
    if status not in (200, 404):
        raise IdentityError(f"registry HTTP status {status}: {url}")
    return status, body


def _diagnostic_text(value):
    text = str(value)
    text = "".join(character if character >= " " and character != "\x7f" else "?"
                   for character in text)
    if not text:
        return type(value).__qualname__
    marker = " [truncated]"
    if len(text) > REGISTRY_ERROR_TEXT:
        text = text[:REGISTRY_ERROR_TEXT - len(marker)] + marker
    return text


def _error_chain(error):
    chain = []
    current = error
    while current is not None and len(chain) < REGISTRY_ERROR_CHAIN_ITEMS:
        chain.append({"type": type(current).__qualname__, "message": _diagnostic_text(current)})
        current = current.__cause__
    return chain


def _transport_worker(url, limit):
    """Write one typed response for the bounded parent process."""
    try:
        status, body = _read_url_once(url, limit)
    except RegistryTransportError as error:
        payload = json.dumps({"message": _diagnostic_text(error),
                              "chain": _error_chain(error)}, separators=(",", ":")).encode()
        sys.stdout.buffer.write(b"T" + payload)
    except IdentityError as error:
        payload = json.dumps({"message": _diagnostic_text(error),
                              "chain": _error_chain(error)}, separators=(",", ":")).encode()
        sys.stdout.buffer.write(b"P" + payload)
    else:
        sys.stdout.buffer.write(b"S" + struct.pack("!H", status) + body)
    return 0


def _process_tree():
    scripts = Path(__file__).resolve().parents[3] / "scripts"
    return _load_exact_module(scripts / "process_tree.py", "process_tree")


def _valid_protocol_text(value, *, type_name=False):
    limit = REGISTRY_ERROR_TYPE_TEXT if type_name else REGISTRY_ERROR_TEXT
    if not isinstance(value, str) or not value or len(value) > limit:
        return False
    if any(character < " " or character == "\x7f" for character in value):
        return False
    if type_name and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", value) is None:
        return False
    return True


def read_url(url, limit):
    """Read one registry response within an absolute process-tree deadline.

    The child boundary covers interpreter startup, DNS, connect, headers, body,
    and trailers. Socket timeouts alone cover only inactivity and cannot bound a
    peer that keeps dripping bytes or an operating-system resolver call.
    """
    if type(limit) is not int or not 0 <= limit <= METADATA_LIMIT:
        raise IdentityError("registry response limit is outside the identity bound")
    command_line = [sys.executable, "-I", str(Path(__file__).resolve()),
                    "--registry-transport", url, str(limit)]
    runner = _process_tree()
    output_limit_error = getattr(runner, "ProcessTreeOutputLimit", ())
    try:
        result = runner.run(
            command_line,
            timeout=REGISTRY_REQUEST_SECONDS,
            stdout_limit=max(limit + 3, REGISTRY_ERROR_PROTOCOL_BYTES + 1),
            stderr_limit=REGISTRY_STDERR_BYTES,
        )
    except subprocess.TimeoutExpired as error:
        raise RegistryTransportError(
            f"registry request exceeded its total deadline: {url}") from error
    except output_limit_error as error:
        raise IdentityError("registry transport worker exceeded its output bound") from error
    if result.returncode != 0:
        cause = subprocess.CalledProcessError(
            result.returncode, command_line, output=result.stdout, stderr=result.stderr)
        raise IdentityError(f"registry transport worker failed: {url}") from cause
    if result.stderr:
        raise IdentityError("registry transport worker returned unexpected diagnostics")
    output = result.stdout
    if len(output) >= 3 and output[:1] == b"S":
        status = struct.unpack("!H", output[1:3])[0]
        body = output[3:]
        if status not in (200, 404) or len(body) > limit:
            raise IdentityError("registry transport worker returned an invalid success response")
        return status, body
    if output[:1] in (b"P", b"T"):
        if len(output) > REGISTRY_ERROR_PROTOCOL_BYTES:
            raise IdentityError("registry transport worker returned an oversized error")
        try:
            payload = parse_json(output[1:])
            if set(payload) != {"message", "chain"}:
                raise ValueError("invalid transport error schema")
            message = payload["message"]
            chain = payload["chain"]
            expected = "RegistryTransportError" if output[:1] == b"T" else "IdentityError"
            if (not _valid_protocol_text(message) or not isinstance(chain, list)
                    or not 1 <= len(chain) <= REGISTRY_ERROR_CHAIN_ITEMS
                    or any(not isinstance(item, dict) or set(item) != {"type", "message"}
                           or not _valid_protocol_text(item["type"], type_name=True)
                           or not _valid_protocol_text(item["message"])
                           for item in chain)):
                raise ValueError("invalid transport error schema")
            if chain[0]["type"] != expected or chain[0]["message"] != message:
                raise ValueError("invalid transport error origin")
        except (IdentityError, KeyError, TypeError, UnicodeDecodeError,
                ValueError, json.JSONDecodeError) as error:
            raise IdentityError("registry transport worker returned an invalid error") from error
        cause = RegistryWorkerError(chain)
        error_type = RegistryTransportError if output[:1] == b"T" else IdentityError
        raise error_type(message) from cause
    raise IdentityError("registry transport worker returned an invalid response")


Fetch = Callable[[str, int], "tuple[int, bytes]"]


class ApiThrottle:
    """Space crates.io API requests across concurrent registry callers."""

    def __init__(self, interval: float = API_INTERVAL_SECONDS) -> None:
        self.interval = interval
        self._lock = threading.Lock()
        self._last: float | None = None

    def wait(self) -> None:
        with self._lock:
            if self._last is not None:
                remaining = self._last + self.interval - time.monotonic()
                if remaining > 0:
                    time.sleep(remaining)
            self._last = time.monotonic()


API_THROTTLE = ApiThrottle()


class RegistryPolicy:
    """Apply registry pacing and transient retry policy to the bounded reader."""

    def __init__(self, reader: Fetch = read_url, *,
                 throttle: ApiThrottle = API_THROTTLE,
                 sleep: Callable[[float], None] = time.sleep,
                 jitter: Callable[[float, float], float] = random.uniform) -> None:
        self.reader = reader
        self.throttle = throttle
        self.sleep = sleep
        self.jitter = jitter

    def __call__(self, url: str, limit: int) -> tuple[int, bytes]:
        for attempt in range(1, TRANSPORT_ATTEMPTS + 1):
            if url.startswith(API_PREFIX):
                self.throttle.wait()
            try:
                return self.reader(url, limit)
            except RegistryTransportError as error:
                if attempt == TRANSPORT_ATTEMPTS:
                    raise RegistryTransportError(
                        f"{url}: {error} (after {attempt} attempts)") from error
                delay = (TRANSPORT_BACKOFF_SECONDS * 2 ** (attempt - 1)
                         * self.jitter(0.5, 1.0))
                self.sleep(delay)
        raise AssertionError("unreachable: the last attempt returns or raises")


REGISTRY_POLICY = RegistryPolicy()


def index_path(name):
    name = name.lower()
    if len(name) < 3:
        return f"{len(name)}/{name}"
    if len(name) == 3:
        return f"3/{name[0]}/{name}"
    return f"{name[:2]}/{name[2:4]}/{name}"


def sparse_index_versions(name, fetch=REGISTRY_POLICY):
    """Read every validated version checksum through the bounded sparse-index transport."""
    status, body = fetch(f"https://index.crates.io/{index_path(name)}", METADATA_LIMIT)
    if status == 404:
        return None
    if status != 200:
        raise IdentityError(f"crates.io index returned HTTP {status} for {name}")
    if not body.strip():
        raise IdentityError("empty registry index")
    versions = {}
    try:
        for line in body.splitlines():
            if not line.strip():
                continue
            row = parse_json(line)
            version = row.get("vers")
            checksum = row.get("cksum")
            if (row.get("name") != name or not isinstance(version, str)
                    or not VERSION.fullmatch(version) or version in versions
                    or not isinstance(checksum, str) or not SHA256.fullmatch(checksum)):
                raise IdentityError("malformed, duplicate, or inconsistent index identity")
            versions[version] = checksum
    except IdentityError:
        raise
    except (AttributeError, TypeError, ValueError) as error:
        raise IdentityError(f"malformed crates.io index record for {name}: {error}") from error
    return versions


def _registry_release_checksum(name, version, fetch=REGISTRY_POLICY):
    """Return a checksum only when the API and sparse index identify one release."""
    if not NAME.fullmatch(name) or not VERSION.fullmatch(version):
        raise IdentityError("invalid registry package identity")
    api_status, api_body = fetch(
        f"https://crates.io/api/v1/crates/{name}/{version}", METADATA_LIMIT)
    if api_status not in (200, 404):
        raise IdentityError("registry lookup did not return 200 or 404")
    versions = sparse_index_versions(name, fetch)
    checksum = None if versions is None else versions.get(version)
    if api_status == 404:
        if checksum is not None:
            raise IdentityError("registry API absence conflicts with the index")
        return None
    response = parse_json(api_body)
    record = response.get("version") if isinstance(response, dict) else None
    if (not isinstance(record, dict) or record.get("crate") != name or record.get("num") != version
            or versions is None or checksum is None or record.get("checksum") != checksum):
        raise IdentityError("registry API and index release identities disagree")
    return checksum


def published_checksum(name, version, fetch=REGISTRY_POLICY):
    """Hash the registry archive after the API and index agree on its identity."""
    checksum = _registry_release_checksum(name, version, fetch)
    if checksum is None:
        raise IdentityError(f"registry lacks {name}@{version}")
    status, archive = fetch(
        f"https://static.crates.io/crates/{name}/{name}-{version}.crate", METADATA_LIMIT)
    if status != 200 or hashlib.sha256(archive).hexdigest() != checksum:
        raise IdentityError("published archive checksum differs from registry identity")
    return checksum


def publish_required(package, fetch=REGISTRY_POLICY):
    """Only consistent absence publishes; complete identity equality skips."""
    checksum = _registry_release_checksum(package.name, package.version, fetch)
    if checksum is None:
        return True
    if checksum != package.checksum:
        raise IdentityError("published archive checksum differs from this exact release")
    status, published = fetch(
        f"https://static.crates.io/crates/{package.name}/{package.name}-{package.version}.crate",
        METADATA_LIMIT)
    if status != 200 or hashlib.sha256(published).hexdigest() != checksum or published != package.archive:
        raise IdentityError("published archive bytes do not verify the release identity")
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()
    package = package_release(args.package, args.version, args.expected_commit)
    required = publish_required(package)
    # The action exposes a decision only after every check succeeds.
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"publish={str(required).lower()}\n")
    print(f"{package.name}@{package.version}: {'unpublished' if required else 'identical published archive'}; sha256={package.checksum}; commit={package.commit}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--registry-transport"]:
        if len(sys.argv) != 4:
            raise SystemExit("registry transport requires URL and response limit")
        raise SystemExit(_transport_worker(sys.argv[2], int(sys.argv[3])))
    main()
