"""Release idempotency requires archive bytes and exact clean VCS identity."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/crates-publish.yml"
CONDITION = "steps.identity.outputs.publish == 'true'"


def test_workflow_checks_identity_before_any_authentication_or_upload():
    workflow = yaml.safe_load(WORKFLOW.read_text())
    steps = workflow["jobs"]["publish"]["steps"]
    auth = next(s for s in steps if s.get("id") == "auth")
    upload = next(s for s in steps if s.get("name") == "Publish the validated package")
    # The old workflow authorizes both operations unconditionally after validate.
    assert auth.get("if") == CONDITION
    assert upload.get("if") == CONDITION
    guard = next(s for s in steps if s.get("id") == "identity")
    assert steps.index(guard) < steps.index(auth) < steps.index(upload)
    assert upload["run"] == 'cargo publish --locked --package "$RELEASE_PACKAGE"'

# Registry fixtures feed real stdlib HTTPResponse parsing without opening sockets.
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from urllib.parse import urlsplit

import pytest

from test_crates_release_identity_history import commit, history as history, run


@pytest.fixture(scope="module")
def identity():
    path = ROOT / ".github/actions/crate-release-identity/release_identity.py"
    spec = importlib.util.spec_from_file_location("atlas_release_identity", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def source(tmp_path_factory, identity):
    root = tmp_path_factory.mktemp("crate-identity")
    (root / "crates/sample/src").mkdir(parents=True)
    (root / ".gitignore").write_bytes(b"/target/\n")
    (root / "Cargo.toml").write_bytes(b'[workspace]\nmembers=["crates/sample"]\nresolver="3"\n'
                                     b'[workspace.package]\nversion="0.1.2"\nreadme="README.md"\nlicense="MIT"\n')
    (root / "crates/sample/Cargo.toml").write_bytes(b'[package]\nname="atlas-identity-fixture"\n'
                                                   b'version.workspace=true\nreadme.workspace=true\n'
                                                   b'license.workspace=true\nedition="2024"\n')
    (root / "crates/sample/src/lib.rs").write_bytes(
        b"/// Triple an input.\npub fn scale(input: u64) -> u64 { input * 3 }\n")
    (root / "README.md").write_bytes(b"Committed workspace readme, included byte for byte.\n")
    run(["git", "init", "--quiet"], root)
    run(["cargo", "generate-lockfile", "--offline"], root)
    sha = commit(root)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CARGO_NET_OFFLINE", "true")
        package = identity.package_release("atlas-identity-fixture", "0.1.2", sha, root)
    return root, sha, package


@pytest.fixture
def registry(identity, monkeypatch):
    from http.client import HTTPResponse
    from types import SimpleNamespace
    from urllib.error import HTTPError
    routes, requests = {}, []

    class Wire:
        def __init__(self, payload):
            self.payload = payload

        def makefile(self, *args):
            return io.BytesIO(self.payload)

    def open_response(request, timeout):
        path = urlsplit(request.full_url).path
        requests.append((path, request.get_header("Authorization")))
        status, body = routes.get(path, (404, b""))
        wire = (f"HTTP/1.1 {status} fixture\r\nContent-Length: {len(body)}\r\n\r\n".encode() + body)
        response = HTTPResponse(Wire(wire))
        response.begin()
        if status != 200:
            raise HTTPError(request.full_url, status, "fixture", response.headers, response)
        return response

    monkeypatch.setattr(identity, "build_opener", lambda *args: SimpleNamespace(open=open_response))
    yield routes, requests, identity.read_url
    assert all(authorization is None for _, authorization in requests)


def paths(package, identity):
    return (f"/api/v1/crates/{package.name}/{package.version}",
            "/" + identity.index_path(package.name),
            f"/crates/{package.name}/{package.name}-{package.version}.crate")


def clone_fixture(source, destination, cwd):
    run(["git", "-c", "core.autocrlf=false", "clone", "--quiet",
         str(source), str(destination)], cwd)


def published(routes, package, identity, archive=None):
    archive = package.archive if archive is None else archive
    checksum = hashlib.sha256(archive).hexdigest()
    api, index, download = paths(package, identity)
    routes[api] = 200, json.dumps({"version": {"crate": package.name, "num": package.version,
                                              "checksum": checksum}}).encode()
    routes[index] = 200, json.dumps({"name": package.name, "vers": package.version,
                                    "cksum": checksum}).encode()
    routes[download] = 200, archive
    return api, index, download


def repack(package, changes=None, extra=None):
    output = io.BytesIO()
    changes = {} if changes is None else changes
    with tarfile.open(fileobj=io.BytesIO(package.archive), mode="r:gz") as old:
        with tarfile.open(fileobj=output, mode="w:gz") as new:
            for member in old:
                content = old.extractfile(member).read()
                content = changes.get(member.name.split("/", 1)[1], content)
                member.size = len(content)
                new.addfile(member, io.BytesIO(content))
            if extra:
                name, content = extra
                member = tarfile.TarInfo(name)
                member.size = len(content)
                new.addfile(member, io.BytesIO(content))
    return output.getvalue()


def test_fresh_package_verifies_exact_workspace_source_and_archive_values(identity, source):
    root, sha, package = source
    files = identity.archive_files(package)
    assert package.path == "crates/sample"
    assert package.commit == sha
    assert files["README.md"] == (root / "README.md").read_bytes()
    assert files["src/lib.rs"] == run(["git", "show", "HEAD:crates/sample/src/lib.rs"], root).encode() + b"\n"
    assert package.checksum == hashlib.sha256(package.archive).hexdigest()
    assert len(package.archive) > sum(len(v) for v in files.values()) // 10


@pytest.mark.parametrize("existing_index", [False, True])
def test_consistent_exact_version_absence_permits_auth_and_upload(identity, source, registry, existing_index):
    package = source[2]
    routes, requests, fetch = registry
    api, index, download = paths(package, identity)
    if existing_index:
        routes[index] = 200, json.dumps({"name": package.name, "vers": "0.1.1",
                                        "cksum": package.checksum}).encode()
    assert identity.publish_required(package, fetch) is True
    assert [path for path, _ in requests] == [api, index]
    assert download not in [path for path, _ in requests]


def test_sparse_index_reader_preserves_bootstrap_and_strict_failure(identity):
    name = "atlas-identity-fixture"
    checksum = "f" * 64
    rows = b"\n".join((
        json.dumps({"name": name, "vers": "0.1.1", "cksum": "0" * 64}).encode(),
        json.dumps({"name": name, "vers": "0.1.2", "cksum": checksum}).encode(),
    ))
    def answer(status, body):
        def fetch(url, limit):
            assert url == "https://index.crates.io/at/la/atlas-identity-fixture"
            assert limit == identity.METADATA_LIMIT
            return status, body
        return fetch

    assert identity.sparse_index_versions(name, answer(200, rows)) == {
        "0.1.1": "0" * 64,
        "0.1.2": checksum,
    }
    assert identity.sparse_index_versions(name, answer(404, b"")) is None
    with pytest.raises(identity.IdentityError, match="HTTP 503"):
        identity.sparse_index_versions(name, answer(503, b""))
    with pytest.raises(identity.IdentityError, match="empty registry index"):
        identity.sparse_index_versions(name, answer(200, b""))
    with pytest.raises(identity.IdentityError, match="malformed"):
        identity.sparse_index_versions(name, answer(200, b"not JSON"))


def test_sparse_index_reader_rejects_oversized_and_redirected_transport(identity, monkeypatch):
    from types import SimpleNamespace
    from urllib.error import HTTPError

    class OversizedResponse:
        status = 200
        headers = SimpleNamespace(get_all=lambda name, default: default)

        def read(self, limit):
            return b"x" * limit

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    response = OversizedResponse()
    monkeypatch.setattr(identity, "build_opener",
                        lambda *args: SimpleNamespace(open=lambda *args, **kwargs: response))
    with pytest.raises(identity.IdentityError, match="exceeds identity bound"):
        identity.sparse_index_versions("atlas-identity-fixture")

    def redirect(*args, **kwargs):
        raise HTTPError("https://index.crates.io/at/la/atlas-identity-fixture",
                        302, "redirect", {}, None)

    monkeypatch.setattr(identity, "build_opener",
                        lambda *args: SimpleNamespace(open=redirect))
    with pytest.raises(identity.IdentityError, match="HTTP status 302"):
        identity.sparse_index_versions("atlas-identity-fixture")


def test_identical_publication_skips_auth_and_upload_after_all_three_reads(identity, source, registry):
    package = source[2]
    routes, requests, fetch = registry
    expected = published(routes, package, identity)
    assert identity.publish_required(package, fetch) is False
    assert [path for path, _ in requests] == list(expected)


@pytest.mark.parametrize("entry,replacement", [
    ("Cargo.lock", b"changed dependency lock\n"),
    ("README.md", b"changed packaged docs\n"),
    ("src/lib.rs", b"pub fn scale(input: u64) -> u64 { input * 4 }\n"),
    (".cargo_vcs_info.json", json.dumps({"git": {"sha1": "f" * 40}, "path_in_vcs": "crates/sample"}).encode()),
])
def test_any_complete_archive_difference_fails_closed(identity, source, registry, entry, replacement):
    package = source[2]
    routes, requests, fetch = registry
    archive = repack(package, {entry: replacement})
    assert hashlib.sha256(archive).hexdigest() != package.checksum
    published(routes, package, identity, archive)
    with pytest.raises(identity.IdentityError, match="checksum differs"):
        identity.publish_required(package, fetch)
    assert len(requests) == 2


@pytest.mark.parametrize("boundary", ["api404-index-present", "api200-index404", "api200-index-missing",
                                      "api-checksum", "api-name", "api-version", "index-name",
                                      "duplicate-version", "duplicate-json-key", "malformed-json",
                                      "empty-index", "invalid-version", "invalid-checksum", "nonfinite-json"])
def test_ambiguous_registry_identity_never_skips_or_publishes(identity, source, registry, boundary):
    package = source[2]
    routes, requests, fetch = registry
    api, index, download = published(routes, package, identity)
    if boundary == "api404-index-present":
        routes[api] = 404, b""
    elif boundary == "api200-index404":
        routes[index] = 404, b""
    elif boundary == "api200-index-missing":
        row = json.loads(routes[index][1]); row["vers"] = "0.1.1"
        routes[index] = 200, json.dumps(row).encode()
    elif boundary.startswith("api-"):
        record = json.loads(routes[api][1])
        record["version"][{"api-name": "crate", "api-version": "num", "api-checksum": "checksum"}[boundary]] = "different"
        routes[api] = 200, json.dumps(record).encode()
    elif boundary == "duplicate-version":
        routes[index] = 200, routes[index][1] + b"\n" + routes[index][1]
    elif boundary == "duplicate-json-key":
        routes[index] = 200, b'{"name":"wrong","name":"atlas-identity-fixture","vers":"0.1.2","cksum":"' + package.checksum.encode() + b'"}'
    elif boundary == "malformed-json":
        routes[index] = 200, b"not JSON"
    elif boundary == "empty-index":
        routes[index] = 200, b""
    elif boundary == "nonfinite-json":
        routes[index] = 200, routes[index][1][:-1] + b',"invalid":NaN}'
    else:
        row = json.loads(routes[index][1])
        row[{"index-name": "name", "invalid-version": "vers", "invalid-checksum": "cksum"}[boundary]] = "invalid"
        routes[index] = 200, json.dumps(row).encode()
    with pytest.raises((identity.IdentityError, ValueError)):
        identity.publish_required(package, fetch)
    assert download not in [path for path, _ in requests]


@pytest.mark.parametrize("endpoint,status", [(0, 401), (0, 403), (0, 429), (0, 500), (0, 302),
                                             (1, 503), (2, 404), (2, 500)])
def test_lookup_and_download_failures_are_not_version_absence(identity, source, registry, endpoint, status):
    package = source[2]
    routes, requests, fetch = registry
    targets = published(routes, package, identity)
    routes[targets[endpoint]] = status, b"boundary failure"
    with pytest.raises(identity.IdentityError):
        identity.publish_required(package, fetch)
    assert requests[-1][0] == targets[endpoint]


def test_truncated_download_cannot_certify_a_skip(identity, source, registry):
    package = source[2]
    routes, requests, fetch = registry
    _, _, download = published(routes, package, identity)
    routes[download] = 200, package.archive[:-1]
    with pytest.raises(identity.IdentityError, match="archive bytes"):
        identity.publish_required(package, fetch)
    assert len(requests) == 3


def test_network_failure_propagates_without_any_decision(identity, source):
    from urllib.error import URLError
    calls = []

    def disconnected(url, limit):
        calls.append(url)
        raise URLError("offline registry boundary")

    with pytest.raises(URLError):
        identity.publish_required(source[2], disconnected)
    assert calls == ["https://crates.io/api/v1/crates/atlas-identity-fixture/0.1.2"]


@pytest.mark.parametrize("change", ["commit", "path", "dirty", "missing", "duplicate", "traversal", "lock"])
def test_unverified_local_archive_provenance_fails_closed(identity, source, change):
    package = source[2]
    vcs = json.loads(identity.archive_files(package)[".cargo_vcs_info.json"])
    extra = None
    changes = {}
    if change == "commit": vcs["git"]["sha1"] = "f" * 40
    if change == "path": vcs["path_in_vcs"] = "other"
    if change == "dirty": vcs["git"]["dirty"] = True
    if change == "missing": vcs = {}
    if change in ("commit", "path", "dirty", "missing"):
        changes[".cargo_vcs_info.json"] = json.dumps(vcs).encode()
    if change == "duplicate": extra = (f"{package.name}-{package.version}/Cargo.lock", b"duplicate")
    if change == "traversal": extra = (f"{package.name}-{package.version}/../escape", b"unsafe")
    if change == "lock": changes["Cargo.toml"] = b'[package]\nname="different"\nversion="0.1.2"\n'
    bad = identity.Package(package.name, package.version, package.commit, package.path, repack(package, changes, extra))
    with pytest.raises(identity.IdentityError):
        identity.archive_files(bad)


@pytest.mark.parametrize("change", ["dirty", "untracked", "head", "version"])
def test_real_checkout_must_remain_the_exact_clean_release(identity, source, tmp_path, change):
    root = tmp_path / "repo"
    clone_fixture(source[0], root, tmp_path)
    expected = source[1]
    version = "0.1.2"
    if change == "dirty": (root / "README.md").write_text("uncommitted change\n")
    if change == "untracked": (root / "extra.txt").write_text("uncommitted input\n")
    if change == "head": expected = "f" * 40
    if change == "version": version = "0.1.3"
    with pytest.raises(identity.IdentityError):
        identity.package_release("atlas-identity-fixture", version, expected, root)
    assert run(["git", "rev-parse", "HEAD"], root) == source[1]


def test_equal_source_tree_at_different_commit_is_not_identical_publication(identity, source, registry, tmp_path):
    root = tmp_path / "repo"
    clone_fixture(source[0], root, tmp_path)
    new_commit = commit(root)
    assert run(["git", "rev-parse", "HEAD^{tree}"], root) == run(["git", "rev-parse", "HEAD^{tree}"], source[0])
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CARGO_NET_OFFLINE", "true")
        package = identity.package_release("atlas-identity-fixture", "0.1.2", new_commit, root)
    assert new_commit != source[1]
    assert package.archive != source[2].archive
    routes, requests, fetch = registry
    published(routes, source[2], identity)
    with pytest.raises(identity.IdentityError, match="checksum differs"):
        identity.publish_required(package, fetch)
    assert len(requests) == 2


def test_truncated_http_body_cannot_be_classified_as_absent_version(identity, monkeypatch):
    from http.client import HTTPResponse
    from types import SimpleNamespace

    body = b'{"name":"atlas-identity-fixture","vers":"0.1.1","cksum":"' + b"0" * 64 + b'"}\n'
    wire = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body) + 50).encode() + b"\r\n\r\n" + body

    class Wire:
        def makefile(self, *args):
            return io.BytesIO(wire)

    response = HTTPResponse(Wire())
    response.begin()
    monkeypatch.setattr(identity, "build_opener", lambda *args: SimpleNamespace(open=lambda *args, **kwargs: response))
    with pytest.raises(identity.IdentityError, match="incomplete"):
        identity.read_url("https://index.crates.io/at/la/atlas-identity-fixture", 4096)


@pytest.mark.parametrize("status,headers,body,valid", [
    (200, b"Content-Length: 4\r\n", b"data", True),
    (404, b"Content-Length: 4\r\n", b"gone", True),
    (200, b"", b"close-framed", True),
    (200, b"Content-Length: 5\r\n", b"data", False),
    (404, b"Content-Length: 5\r\n", b"gone", False),
    (200, b"Content-Length: bad\r\n", b"data", False),
    (200, b"Content-Length: 4\r\nContent-Length: 4\r\n", b"data", False),
    (404, b"Content-Length: 4\r\nContent-Length: 4\r\n", b"gone", False),
    (200, b"Content-Length: 4\r\nTransfer-Encoding: chunked\r\n", b"data", False),
    (200, b"Transfer-Encoding: unknown\r\n", b"data", False),
])
def test_complete_http_framing_is_required_for_presence_and_absence(identity, monkeypatch, status, headers, body, valid):
    from http.client import HTTPResponse
    from types import SimpleNamespace
    from urllib.error import HTTPError

    wire = f"HTTP/1.1 {status} fixture\r\n".encode() + headers + b"\r\n" + body

    class Wire:
        def makefile(self, *args):
            return io.BytesIO(wire)

    response = HTTPResponse(Wire())
    response.begin()

    def open_response(*args, **kwargs):
        if status == 404:
            raise HTTPError("https://registry.invalid", status, "fixture", response.headers, response)
        return response

    monkeypatch.setattr(identity, "build_opener", lambda *args: SimpleNamespace(open=open_response))
    if valid:
        assert identity.read_url("https://registry.invalid", 4096) == (status, body)
    else:
        with pytest.raises(identity.IdentityError):
            identity.read_url("https://registry.invalid", 4096)


@pytest.mark.parametrize("decision,code", [("true", 0), ("false", 0), ("", 1), ("unknown", 1), ("True", 1), ("false\ntrue", 1)])
def test_workflow_rejects_missing_or_unknown_decision(decision, code):
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["publish"]["steps"]
    step = next(s for s in steps if s.get("name") == "Require a complete publication decision")
    assert step["env"] == {"PUBLISH_REQUIRED": "${{ steps.identity.outputs.publish }}"}
    actual = subprocess.run(["bash", "-c", step["run"]], env={**os.environ, "PUBLISH_REQUIRED": decision},
                            capture_output=True, timeout=5)
    assert actual.returncode == code
    assert (actual.stderr == b"") is (code == 0)


def test_workflow_preserves_validation_interface_permissions_and_upload_command(history):
    base = yaml.safe_load(run(["git", "show", "b553c42da72dcdeb2bb2644c60759dc465fb329a:.github/workflows/crates-publish.yml"], history))
    current = yaml.safe_load(WORKFLOW.read_text())
    assert {k: v for k, v in current.items() if k != "jobs"} == {k: v for k, v in base.items() if k != "jobs"}
    assert current["jobs"]["validate"] == base["jobs"]["validate"]
    old, new = base["jobs"]["publish"], current["jobs"]["publish"]
    assert {k: v for k, v in new.items() if k != "steps"} == {k: v for k, v in old.items() if k != "steps"}
    added = {"Verify exact release publication identity", "Require a complete publication decision"}
    preserved = [{k: v for k, v in step.items() if k != "if"} if step.get("id") == "auth" or step.get("name") == "Publish the validated package" else step
                 for step in new["steps"] if step.get("name") not in added]
    assert preserved == old["steps"]
    assert new["needs"] == "validate"
    assert new["if"] == "github.event_name == 'release'"


def test_workflow_uses_exact_helper_commit_and_correct_action_output(history):
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["publish"]["steps"]
    guard = next(step for step in steps if step.get("id") == "identity")
    match = re.fullmatch(r"ryancinsight/atlas/\.github/actions/crate-release-identity@([0-9a-f]{40})", guard["uses"])
    assert match is not None
    assert match.group(1) == "bff89297f5dee0daed7bcf6d3712474b167f9710"
    assert guard["with"] == {"package": "${{ needs.validate.outputs.package }}",
                            "version": "${{ needs.validate.outputs.version }}",
                            "expected-commit": "${{ github.sha }}"}
    for name in ("action.yml", "release_identity.py"):
        path = ".github/actions/crate-release-identity/" + name
        actual = subprocess.run(["git", "show", f"{match.group(1)}:{path}"], cwd=history,
                                capture_output=True, check=True, timeout=5).stdout
        assert actual == (ROOT / path).read_bytes()
    action = yaml.safe_load((ROOT / ".github/actions/crate-release-identity/action.yml").read_text())
    assert action["outputs"]["publish"]["value"] == "${{ steps.identity.outputs.publish }}"
    execution = action["runs"]["steps"]
    assert len(execution) == 1
    assert execution[0]["id"] == "identity"
    assert '"$GITHUB_ACTION_PATH/release_identity.py"' in execution[0]["run"]
    assert execution[0]["env"] == {"RELEASE_PACKAGE": "${{ inputs.package }}",
                                  "RELEASE_VERSION": "${{ inputs.version }}",
                                  "RELEASE_COMMIT": "${{ inputs.expected-commit }}"}


def test_same_clean_commit_regenerates_the_identical_complete_archive(identity, source, tmp_path):
    root = tmp_path / "repo"
    clone_fixture(source[0], root, tmp_path)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CARGO_NET_OFFLINE", "true")
        package = identity.package_release("atlas-identity-fixture", "0.1.2", source[1], root)
    assert package.archive == source[2].archive
    assert package.checksum == source[2].checksum


def test_ignored_uncommitted_package_content_is_not_clean_provenance(identity, source, tmp_path):
    root = tmp_path / "repo"
    clone_fixture(source[0], root, tmp_path)
    manifest = root / "crates/sample/Cargo.toml"
    manifest.write_text(manifest.read_text() + 'include=["Cargo.toml", "src/**", "payload.bin"]\n')
    (root / ".gitignore").write_text("/target/\n/crates/sample/payload.bin\n")
    sha = commit(root)
    (root / "crates/sample/payload.bin").write_bytes(b"uncommitted packaged payload")
    assert run(["git", "status", "--porcelain"], root) == ""
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CARGO_NET_OFFLINE", "true")
        with pytest.raises((identity.IdentityError, subprocess.CalledProcessError)):
            identity.package_release("atlas-identity-fixture", "0.1.2", sha, root)
    assert run(["git", "status", "--porcelain"], root) == ""
