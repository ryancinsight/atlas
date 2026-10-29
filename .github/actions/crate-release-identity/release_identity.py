#!/usr/bin/env python3
"""Permit a release retry to skip publishing only for identical verified bytes."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import http.client
import importlib
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
from urllib.request import HTTPHandler, HTTPRedirectHandler, HTTPSHandler, Request, build_opener

METADATA_LIMIT = 16 * 1024 * 1024
REGISTRY_REQUEST_SECONDS = 30.0
API_INTERVAL_SECONDS = 1.0
API_PREFIX = "https://crates.io/api/"
TRANSPORT_ATTEMPTS = 5
TRANSPORT_BACKOFF_SECONDS = 2.0
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\Z")
PRERELEASE = r"(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
                     + rf"(?:-{PRERELEASE}(?:\.{PRERELEASE})*)?"
                     + r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\Z")
STATUS_LINE = re.compile(rb"HTTP/1\.[0-9] [0-9]{3} [\t\x20-\x7e\x80-\xff]*\r\n\Z")
TOKEN_BYTES = frozenset(b"!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")


class IdentityError(ValueError):
    """A release identity is absent, ambiguous, or inconsistent."""


class RegistryTransportError(IdentityError):
    """A transient network failure prevented a complete registry response."""


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

    def invalid_constant(value):
        raise IdentityError(f"invalid JSON constant: {value}")
    return json.loads(data, object_pairs_hook=unique_object, parse_constant=invalid_constant)


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


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class RegistryFramingError(http.client.HTTPException):
    """A syntactically invalid HTTP response cannot be retried as transport loss."""


class RegistryBodyDisconnect(OSError):
    """The peer disconnected before a chunked response reached its terminator."""


class RegistryWorkerError(RuntimeError):
    """A bounded transport child reported a typed exception chain."""

    def __init__(self, chain):
        self.chain = tuple(chain)
        summary = " -> ".join(f"{item['type']}: {item['message']}" for item in self.chain)
        super().__init__(summary)


class HeaderCapture:
    """Record response-head lines while the stdlib owns socket buffering."""

    def __init__(self, stream):
        self.stream = stream
        self.lines = []

    def readline(self, *args, **kwargs):
        line = self.stream.readline(*args, **kwargs)
        self.lines.append(line)
        return line

    def __getattr__(self, name):
        return getattr(self.stream, name)


def valid_token(value):
    return bool(value) and all(byte in TOKEN_BYTES for byte in value)


def validate_field_line(line, kind):
    """Validate RFC 9112 section 5 field-line syntax without normalization."""
    if not line.endswith(b"\r\n"):
        raise RegistryFramingError(f"{kind} lacks its CRLF terminator")
    field = line[:-2]
    name, separator, value = field.partition(b":")
    if not separator or not valid_token(name):
        raise RegistryFramingError(f"malformed HTTP {kind} name")
    if any(byte != 9 and (byte < 32 or byte == 127) for byte in value):
        raise RegistryFramingError(f"malformed HTTP {kind} value")
    return name.lower(), value.strip(b" \t")


def validate_response_head(lines):
    """Validate every captured status/header block and return final fields."""
    position = 0
    while True:
        if position >= len(lines) or not STATUS_LINE.fullmatch(lines[position]):
            raise RegistryFramingError("malformed HTTP status line")
        version, status_bytes, _reason = lines[position].split(b" ", 2)
        status = int(status_bytes)
        position += 1
        fields = []
        while True:
            if position >= len(lines):
                raise RegistryFramingError("HTTP header section lacks the final CRLF")
            line = lines[position]
            position += 1
            if line == b"\r\n":
                break
            fields.append(validate_field_line(line, "header"))
        if status != http.client.CONTINUE:
            if position != len(lines):
                raise RegistryFramingError("unexpected bytes after HTTP header section")
            if version == b"HTTP/1.0" and any(name == b"transfer-encoding"
                                                for name, _value in fields):
                raise RegistryFramingError("HTTP/1.0 response uses Transfer-Encoding")
            return tuple(fields)


def valid_quoted_string(value):
    if len(value) < 2 or value[:1] != b'"' or value[-1:] != b'"':
        return False
    position = 1
    end = len(value) - 1
    while position < end:
        byte = value[position]
        if byte == 92:
            position += 1
            if position == end:
                return False
            byte = value[position]
            if byte != 9 and not (32 <= byte <= 126 or byte >= 128):
                return False
        elif byte != 9 and byte != 32 and not (byte == 33 or 35 <= byte <= 91
                                                 or 93 <= byte <= 126 or byte >= 128):
            return False
        position += 1
    return True


def valid_chunk_extensions(value):
    """Validate RFC 9112 section 7.1.1 chunk-ext grammar."""
    position = 0
    while position < len(value):
        while position < len(value) and value[position] in (9, 32):
            position += 1
        if position == len(value) or value[position] != 59:
            return False
        position += 1
        while position < len(value) and value[position] in (9, 32):
            position += 1
        start = position
        while position < len(value) and value[position] in TOKEN_BYTES:
            position += 1
        if not valid_token(value[start:position]):
            return False
        whitespace = position
        while position < len(value) and value[position] in (9, 32):
            position += 1
        if position < len(value) and value[position] == 61:
            position += 1
            while position < len(value) and value[position] in (9, 32):
                position += 1
            if position == len(value):
                return False
            if value[position] == 34:
                start = position
                position += 1
                while position < len(value):
                    if value[position] == 92:
                        position += 2
                        continue
                    position += 1
                    if value[position - 1] == 34:
                        break
                if not valid_quoted_string(value[start:position]):
                    return False
            else:
                start = position
                while position < len(value) and value[position] in TOKEN_BYTES:
                    position += 1
                if not valid_token(value[start:position]):
                    return False
        elif position != whitespace:
            return False
    return True


class StrictHTTPResponse(http.client.HTTPResponse):
    """Retain stdlib connection handling with strict RFC 9112 framing.

    ``HTTPConnection.response_class`` is the stdlib extension point. The base
    response parser is intentionally lenient about status/header syntax, chunk
    delimiters, extensions, and trailers. Capturing the bytes it consumes lets
    this subclass reject ambiguous framing while retaining the standard TLS,
    proxy, buffering, and connection lifecycle.
    """

    def begin(self):
        if self.headers is not None:
            return
        capture = HeaderCapture(self.fp)
        self.fp = capture
        try:
            super().begin()
        finally:
            if self.fp is capture:
                self.fp = capture.stream
        self.atlas_fields = validate_response_head(capture.lines)

    def _read_next_chunk_size(self):
        line = self.fp.readline(http.client._MAXLINE + 1)
        if len(line) > http.client._MAXLINE:
            raise http.client.LineTooLong("chunk size")
        if not line:
            raise RegistryBodyDisconnect("connection closed before the next chunk size")
        if not line.endswith(b"\r\n"):
            self._close_conn()
            raise RegistryFramingError("chunk size lacks its CRLF terminator")
        size, separator, extensions = line[:-2].partition(b";")
        if not re.fullmatch(rb"[0-9A-Fa-f]+", size):
            self._close_conn()
            raise RegistryFramingError("malformed HTTP chunk size")
        if separator and not valid_chunk_extensions(separator + extensions):
            self._close_conn()
            raise RegistryFramingError("malformed HTTP chunk extension")
        return int(size, 16)

    def _get_chunk_left(self):
        chunk_left = self.chunk_left
        if not chunk_left:
            if chunk_left is not None:
                if self._safe_read(2) != b"\r\n":
                    self._close_conn()
                    raise RegistryFramingError("chunk data lacks its CRLF delimiter")
            chunk_left = self._read_next_chunk_size()
            if chunk_left == 0:
                self._read_and_discard_trailer()
                self._close_conn()
                chunk_left = None
            self.chunk_left = chunk_left
        return chunk_left

    def _read_and_discard_trailer(self):
        while True:
            line = self.fp.readline(http.client._MAXLINE + 1)
            if len(line) > http.client._MAXLINE:
                raise http.client.LineTooLong("trailer line")
            if not line or not line.endswith(b"\r\n"):
                raise RegistryFramingError("chunk trailers lack the final CRLF terminator")
            if line == b"\r\n":
                return
            validate_field_line(line, "trailer")


class StrictHTTPConnection(http.client.HTTPConnection):
    response_class = StrictHTTPResponse


class StrictHTTPSConnection(http.client.HTTPSConnection):
    response_class = StrictHTTPResponse


class StrictHTTPHandler(HTTPHandler):
    def http_open(self, request):
        return self.do_open(StrictHTTPConnection, request)


class StrictHTTPSHandler(HTTPSHandler):
    def https_open(self, request):
        return self.do_open(StrictHTTPSConnection, request, context=self._context)


def _read_url_once(url, limit):
    """Read public registry data with bounded time/size and no authentication."""
    request = Request(url, headers={"User-Agent": "atlas-release-identity (https://github.com/ryancinsight/atlas)"})
    try:
        response = build_opener(NoRedirect(), StrictHTTPHandler(), StrictHTTPSHandler()).open(
            request, timeout=30)
    except HTTPError as error:
        if error.code == 429 or 500 <= error.code <= 599:
            error.close()
            raise RegistryTransportError(
                f"transient registry HTTP status {error.code}: {url}") from error
        if error.code != 404:
            error.close()
            raise IdentityError(f"registry HTTP status {error.code}: {url}") from error
        response = error
    except http.client.RemoteDisconnected as error:
        raise RegistryTransportError(f"registry request failed: {url}: {error}") from error
    except http.client.HTTPException as error:
        raise IdentityError(f"malformed registry HTTP response: {url}: {error}") from error
    except ssl.SSLCertVerificationError as error:
        raise IdentityError(f"registry TLS certificate verification failed: {url}") from error
    except URLError as error:
        if isinstance(error.reason, ssl.SSLCertVerificationError):
            raise IdentityError(
                f"registry TLS certificate verification failed: {url}") from error
        raise RegistryTransportError(f"registry request failed: {url}: {error}") from error
    except (TimeoutError, OSError) as error:
        raise RegistryTransportError(f"registry request failed: {url}: {error}") from error
    with response:
        if response.status not in (200, 404):
            raise IdentityError(f"registry HTTP status {response.status}: {url}")
        lengths = response.headers.get_all("Content-Length", [])
        transfers = response.headers.get_all("Transfer-Encoding", [])
        if (len(lengths) > 1 or (lengths and not re.fullmatch(r"[0-9]+", lengths[0]))
                or len(transfers) > 1 or (lengths and transfers)
                or (transfers and transfers[0].lower() != "chunked")):
            raise IdentityError("malformed or inconsistent registry HTTP framing")
        if lengths and int(lengths[0]) > limit:
            raise IdentityError(f"registry response exceeds identity bound: {url}")
        try:
            body = response.read(limit + 1)
        except RegistryFramingError as error:
            raise IdentityError(f"malformed registry HTTP framing: {url}: {error}") from error
        except (RegistryBodyDisconnect, http.client.IncompleteRead, OSError) as error:
            raise RegistryTransportError(f"registry response failed: {url}: {error}") from error
        except http.client.HTTPException as error:
            raise IdentityError(f"malformed registry HTTP framing: {url}: {error}") from error
        if len(body) > limit:
            raise IdentityError(f"registry response exceeds identity bound: {url}")
        if lengths and len(body) != int(lengths[0]):
            raise RegistryTransportError("incomplete registry HTTP body")
    return response.status, body


def _error_chain(error):
    chain = []
    current = error
    while current is not None and len(chain) < 8:
        chain.append({"type": type(current).__qualname__, "message": str(current)})
        current = current.__cause__
    return chain


def _transport_worker(url, limit):
    """Write one typed response for the bounded parent process."""
    try:
        status, body = _read_url_once(url, limit)
    except RegistryTransportError as error:
        payload = json.dumps({"message": str(error), "chain": _error_chain(error)}).encode()
        sys.stdout.buffer.write(b"T" + payload)
    except IdentityError as error:
        payload = json.dumps({"message": str(error), "chain": _error_chain(error)}).encode()
        sys.stdout.buffer.write(b"P" + payload)
    else:
        sys.stdout.buffer.write(b"S" + struct.pack("!H", status) + body)
    return 0


def _process_tree():
    scripts = Path(__file__).resolve().parents[3] / "scripts"
    if not (scripts / "process_tree.py").is_file():
        raise IdentityError("bounded process-tree runner is absent from the action revision")
    path = str(scripts)
    sys.path.insert(0, path)
    try:
        return importlib.import_module("process_tree")
    finally:
        sys.path.remove(path)


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
    try:
        result = _process_tree().run(command_line, timeout=REGISTRY_REQUEST_SECONDS)
    except subprocess.TimeoutExpired as error:
        raise RegistryTransportError(
            f"registry request exceeded its total deadline: {url}") from error
    if result.returncode != 0:
        cause = subprocess.CalledProcessError(
            result.returncode, command_line, output=result.stdout, stderr=result.stderr)
        raise IdentityError(f"registry transport worker failed: {url}") from cause
    output = result.stdout
    if len(output) >= 3 and output[:1] == b"S":
        status = struct.unpack("!H", output[1:3])[0]
        body = output[3:]
        if status not in (200, 404) or len(body) > limit:
            raise IdentityError("registry transport worker returned an invalid success response")
        return status, body
    if output[:1] in (b"P", b"T"):
        try:
            payload = json.loads(output[1:].decode("utf-8"))
            message = payload["message"]
            chain = payload["chain"]
            if (not isinstance(message, str) or not isinstance(chain, list)
                    or any(not isinstance(item, dict) or set(item) != {"type", "message"}
                           or not all(isinstance(item[key], str) for key in item)
                           for item in chain)):
                raise ValueError("invalid transport error schema")
        except (KeyError, TypeError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
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
