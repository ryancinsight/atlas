#!/usr/bin/env python3
"""Permit a release retry to skip publishing only for identical verified bytes."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from http.client import HTTPException
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import tomllib
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

METADATA_LIMIT = 16 * 1024 * 1024
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


def unique_object(pairs):
    """Reject duplicate JSON keys instead of silently accepting the last."""
    value = {}
    for key, item in pairs:
        if key in value:
            raise IdentityError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def parse_json(data):
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


def read_url(url, limit):
    """Read public registry data with bounded time/size and no authentication."""
    request = Request(url, headers={"User-Agent": "atlas-release-identity (https://github.com/ryancinsight/atlas)"})
    try:
        response = build_opener(NoRedirect()).open(request, timeout=30)
    except HTTPError as error:
        if error.code != 404:
            raise IdentityError(f"registry HTTP status {error.code}: {url}") from error
        response = error
    except (URLError, TimeoutError, OSError) as error:
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
        try:
            body = response.read(limit + 1)
        except (OSError, HTTPException) as error:
            raise RegistryTransportError(f"registry response failed: {url}: {error}") from error
        if lengths and len(body) != int(lengths[0]):
            raise IdentityError("incomplete registry HTTP body")
    if len(body) > limit:
        raise IdentityError(f"registry response exceeds identity bound: {url}")
    return response.status, body


def index_path(name):
    name = name.lower()
    if len(name) < 3:
        return f"{len(name)}/{name}"
    if len(name) == 3:
        return f"3/{name[0]}/{name}"
    return f"{name[:2]}/{name[2:4]}/{name}"


def sparse_index_versions(name, fetch=read_url):
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


def publish_required(package, fetch=read_url):
    """Only consistent absence publishes; complete identity equality skips."""
    api_status, api_body = fetch(f"https://crates.io/api/v1/crates/{package.name}/{package.version}", METADATA_LIMIT)
    if api_status not in (200, 404):
        raise IdentityError("registry lookup did not return 200 or 404")
    versions = sparse_index_versions(package.name, fetch)
    checksum = None if versions is None else versions.get(package.version)
    if api_status == 404:
        if checksum is not None:
            raise IdentityError("registry API absence conflicts with the index")
        return True
    record = parse_json(api_body)["version"]
    if (record.get("crate") != package.name or record.get("num") != package.version
            or versions is None or checksum is None or record.get("checksum") != checksum):
        raise IdentityError("registry API and index release identities disagree")
    if checksum != package.checksum:
        raise IdentityError("published archive checksum differs from this exact release")
    status, published = fetch(f"https://static.crates.io/crates/{package.name}/{package.name}-{package.version}.crate", len(package.archive))
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
    main()
