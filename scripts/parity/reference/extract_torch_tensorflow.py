#!/usr/bin/env python3
"""Extract release reference metadata without importing framework runtimes.

Downloaded inputs are cached outside the repository. API names are evidence of
reference scope, never evidence of implementation, semantics or Atlas parity.
"""

import argparse
import ast
import concurrent.futures
import hashlib
import json
import re
import urllib.parse
import urllib.request
import zlib
from collections import Counter
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify_git_blob(data, expected):
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if actual != expected:
        raise ValueError(f"Git source digest mismatch: {actual} != {expected}")


class Inputs:
    def __init__(self, cache, offline):
        self.cache, self.offline = Path(cache), offline
        self.cache.mkdir(parents=True, exist_ok=True)

    def read(self, url):
        path = self.cache / digest(url.encode())
        if path.exists():
            return path.read_bytes()
        if self.offline:
            raise RuntimeError(f"Missing offline input: {url}")
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
        path.write_bytes(data)
        return data

    def json(self, url):
        return json.loads(self.read(url))


def domain(symbol):
    s = symbol.lower()
    rules = [
        ("distributed", (".distributed", ".distribute", ".dtensor", ".device_mesh")),
        ("randomness", (".random", ".generator", ".distributions")),
        ("autodiff", (".autograd", ".autodiff", ".gradienttape", ".custom_gradient", ".func.")),
        ("compiler", (".compiler", ".compile", ".export", ".fx", ".jit", ".autograph", ".function", ".xla", ".mlir")),
        ("neural_networks", (".nn", ".keras.layers", ".keras.activations", ".keras.models", ".keras.applications", ".keras.losses", ".keras.metrics", ".keras.model")),
        ("optimizers", (".optim", ".keras.optimizers", ".train")),
        ("transforms", (".fft", ".signal")),
        ("linear_algebra", (".linalg",)),
        ("serialization_deployment", (".saved_model", ".checkpoint", ".serialization", ".save", ".load", ".onnx", ".package", ".lite", ".nativert")),
        ("interop", (".dlpack", ".numpy", ".from_numpy", ".from_dlpack", ".library", ".cpp_extension")),
        ("device_execution", (".cuda", ".mps", ".xpu", ".mtia", ".accelerator", ".backends", ".config", ".cpu", ".device")),
        ("sparse_ragged_quantized", (".sparse", ".ragged", ".quantization", ".quantized", ".nested", ".masked", ".ao.")),
        ("data_io", (".data", ".io", ".strings", ".lookup", ".image", ".audio", ".keras.datasets", ".keras.preprocessing")),
        ("tooling", (".profiler", ".testing", ".test", ".debugging", ".summary", ".monitor", ".utils", ".keras.callbacks", ".keras.utils")),
    ]
    return next((name for name, terms in rules if any(t in s for t in terms)), "arrays_dtypes_numerics")


def stability(symbol):
    parts = symbol.split(".")
    if "experimental" in parts or "prototype" in parts:
        return "experimental_namespace"
    if "compat" in parts:
        return "legacy_compatibility_namespace"
    if any(p.startswith("_") and not p.startswith("__") for p in parts):
        return "documented_private_spelling"
    return "declaration_requires_per_api_review"


def common(framework, version):
    return {
        "schema_version": 1,
        "framework": framework,
        "version": version,
        "observed_at": "2026-10-26",
        "implementation_status": "unmapped",
        "status_note": "Reference enumeration only. No runtime, differential, hardware or performance verification is implied.",
        "domain_classification": "Namespace/name heuristic for routing only; semantic ownership requires per-API review, including raw operators and aliases.",
    }


def release_metadata(inputs, package, version):
    # Exact-version metadata keeps future re-extraction on this frozen baseline.
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    data = inputs.read(url)
    metadata = json.loads(data)
    assert metadata["info"]["version"] == version
    files = metadata["urls"]
    selection_hashes = {
        "torch": "cad63dc8aa6714ea2133a44b64985d87b3e4ebea217657f1e02e35481fa33b61",
        "tensorflow": "1131276b5df32f5396ed0b860a5b53f1a84f6e7339a7acc5373bab41433330a8",
        "keras": "ba6f7ddc7c6845fc565e98a30c1a79877ca578ca2db1be4744eef8d03ae496e3",
    }
    return {"url": url, "sha256": digest(data), "version": version,
            "first_upload": min(x["upload_time_iso_8601"] for x in files),
            "requires_dist": metadata["info"].get("requires_dist"),
            "stable_selection_observation": {"url": f"https://pypi.org/pypi/{package}/json",
                                             "sha256": selection_hashes[package], "observed_latest_version": version,
                                             "observed_at": "2026-10-26"},
            "note": "Stable selection is an observed snapshot; regeneration uses exact-version metadata and never silently advances the frozen baseline."}


def counts(records):
    return {
        "records": len(records),
        "unique_symbols": len({x["symbol"] for x in records}),
        "by_kind": dict(sorted(Counter(x["kind"] for x in records).items())),
        "by_domain": dict(sorted(Counter(x["domain"] for x in records).items())),
        "by_stability": dict(sorted(Counter(x["stability"] for x in records).items())),
    }


def pytorch(inputs):
    result = common("pytorch", "2.14.1")
    inv = "https://docs.pytorch.org/docs/2.14/objects.inv?raw=1"
    data = inputs.read(inv)
    header = data.split(b"\n", 4)
    assert header[0] == b"# Sphinx inventory version 2"
    assert header[2] == b"# Version: 2.14"
    lines = zlib.decompress(header[4]).decode().splitlines()
    pattern = re.compile(r"^(.+?)\s+(\S+:\S+)\s+(-?\d+)\s+(\S+)\s+(.*)$")
    records, documents, invalid = [], [], []
    for line in lines:
        m = pattern.match(line)
        if not m:
            invalid.append(line)
            continue
        name, kind, priority, location, display = m.groups()
        location = location[:-1] + name if location.endswith("$") else location
        item = {"symbol": name, "kind": kind, "source": inv,
                "documentation": urllib.parse.urljoin("https://docs.pytorch.org/docs/2.14/", location),
                "domain": domain(name), "stability": stability(name), "display_name": display}
        if kind.startswith("py:"):
            records.append(item)
        else:
            documents.append(item)
    assert not invalid, invalid[:3]
    result.update({
        "release_source": "https://github.com/pytorch/pytorch/releases/tag/v2.14.1",
        "release_metadata": release_metadata(inputs, "torch", "2.14.1"),
        "source_revision": "5c4886908584029761b579af026dcfb627c84070",
        "sources": [{"url": inv, "sha256": digest(data), "bytes": len(data),
                     "declared_version": "2.14", "observed_entries": len(lines),
                     "parsed_entries": len(records) + len(documents)}],
        "extraction": {"method": "Sphinx inventory v2; all entries parsed; Python objects retained as records and all other entries retained as documentation_records.",
                       "complete_for_source": True, "public_surface_complete": False,
                       "source_count": 1, "omitted_source_entries": 0},
        "gaps": [
            "The published inventory declares 2.14 rather than exact patch 2.14.1; reconcile every patch-level API/semantic difference with the exact source revision before baseline closure.",
            "Inventory presence does not establish stability or deprecation; pages and exact tagged decorators must be reviewed per API. Experimental and private-spelling entries are retained.",
            "Python reference extraction does not enumerate the separate LibTorch C++ API, operator schema/overload registry, environment-variable semantics, tutorial-only APIs, or domain libraries (torchvision/torchaudio/etc.); each remains program scope requiring explicit closure.",
            "Per-signature argument semantics, dtype/device/layout/gradient support and error behavior require per-API contracts; names alone never close a parity row.",
        ],
        "counts": counts(records), "documentation_counts": counts(documents),
        "records": sorted(records, key=lambda x: (x["symbol"], x["kind"])),
        "documentation_records": sorted(documents, key=lambda x: (x["symbol"], x["kind"])),
    })
    return result


def proto_nodes(text):
    """Parse the API golden subset (nested messages and quoted scalar fields)."""
    token_pattern = re.compile(r'"(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z_0-9]*|[{}:]|-?\d+')
    tokens, previous = [], 0
    for match in token_pattern.finditer(text):
        if text[previous:match.start()].strip():
            raise ValueError("Unrecognized API golden syntax")
        tokens.append(match.group())
        previous = match.end()
    if text[previous:].strip():
        raise ValueError("Unrecognized API golden suffix")
    index = 0

    def message():
        nonlocal index
        fields = {}
        while index < len(tokens) and tokens[index] != "}":
            key = tokens[index]
            index += 1
            op = tokens[index]
            index += 1
            if op == "{":
                value = message()
                assert tokens[index] == "}"
                index += 1
            else:
                assert op == ":", (key, op)
                token = tokens[index]
                index += 1
                value = ast.literal_eval(token) if token.startswith('"') else token
            fields.setdefault(key, []).append(value)
        return fields

    result = message()
    assert index == len(tokens), (index, len(tokens))
    return result


def golden_records(path, data, url):
    root = proto_nodes(data.decode())
    name = root["path"][0]
    prefix = "tf.compat.v1" if "/v1/" in path else "tf"
    name = prefix + name.removeprefix("tensorflow")
    group_kind = "class" if "tf_class" in root else "module"
    if "tf_proto" in root:
        descriptor = root["tf_proto"][0]["descriptor"][0]
        items = [{"symbol": name, "kind": "protocol_message", "descriptor": descriptor}]
        for field in descriptor.get("field", []):
            items.append({"symbol": name + "." + field["name"][0], "kind": "protocol_field", "descriptor": field})
        group = {}
    else:
        group = root.get("tf_class", root.get("tf_module"))[0]
        items = [{"symbol": name, "kind": group_kind}]
    for kind in ["member", "member_method"]:
        for member in group.get(kind, []):
            item = {"symbol": name + "." + member["name"][0],
                    "kind": ("method" if group_kind == "class" else "function") if kind == "member_method" else "attribute"}
            if "argspec" in member:
                item["signature"] = member["argspec"][0]
            if "mtype" in member:
                item["declared_type"] = member["mtype"][0]
            items.append(item)
    for item in items:
        item.update({"source": url, "domain": domain(item["symbol"]), "stability": stability(item["symbol"]),
                     "documentation": "https://www.tensorflow.org/api_docs/python/" + item["symbol"].replace(".", "/"),
                     "documentation_version_verified": False})
    return items


def tensorflow(inputs, workers):
    result = common("tensorflow", "2.21.0")
    revision = "a481b10260dfdf833a1b16007eead49c1d7febf3"
    tree_url = f"https://api.github.com/repos/tensorflow/tensorflow/git/trees/{revision}?recursive=1"
    tree_data = inputs.read(tree_url)
    tree = json.loads(tree_data)
    assert not tree["truncated"]
    files = [x for x in tree["tree"] if re.match(r"tensorflow/tools/api/golden/v[12]/.*\.pbtxt$", x["path"])]

    def extract(entry):
        url = f"https://raw.githubusercontent.com/tensorflow/tensorflow/{revision}/{entry['path']}"
        data = inputs.read(url)
        verify_git_blob(data, entry["sha"])
        rows = golden_records(entry["path"], data, url)
        source = {"url": url, "sha256": digest(data), "git_blob_sha": entry["sha"],
                  "bytes": len(data), "observed_entries": len(rows)}
        return source, rows

    sources, records = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for source, rows in pool.map(extract, files):
            sources.append(source)
            records.extend(rows)
    keras_sources, keras_rows = keras(inputs, workers)
    sources.extend(keras_sources)
    records.extend(keras_rows)
    result.update({
        "release_source": "https://github.com/tensorflow/tensorflow/releases/tag/v2.21.0",
        "release_metadata": release_metadata(inputs, "tensorflow", "2.21.0"),
        "source_revision": revision,
        "supplemental_baselines": [{"name": "keras", "version": "3.15.1", "source_revision": "250b42181ce9f37df68319d8f4753ec89a349a43",
                                    "release_metadata": release_metadata(inputs, "keras", "3.15.1"),
                                    "reason": "TensorFlow 2.21.0 requires keras>=3.12.0; the tf.keras namespace is a separately versioned external dependency. Latest stable 3.15.1 selected for explicit coherent baseline; no runtime compatibility test is implied."}],
        "sources": sorted(sources, key=lambda x: x["url"]),
        "source_indexes": [{"url": tree_url, "sha256": digest(tree_data), "truncated": False}],
        "extraction": {"method": "All TensorFlow exact-release v1/v2 API golden files, including legacy compatibility; generated Keras tf.keras exports parsed with Python AST without importing frameworks.",
                       "complete_for_source": True, "public_surface_complete": False,
                       "source_count": len(sources), "tensorflow_golden_file_count": len(files),
                       "keras_export_file_count": len(keras_sources), "omitted_source_entries": 0},
        "gaps": [
            "TensorFlow live API documentation identifies version 2.16.1; exact 2.21.0 source goldens are the scope evidence. Documentation links are navigation aids with unverified current-version semantics.",
            "Goldens test API compatibility, not documentation coverage: reconcile generated docs, export decorators, raw-op signatures and versioned tutorials before full public-surface closure.",
            "Keras generated exports enumerate names/aliases only; inherited class methods, backend-specific behavior and Keras guides remain unextracted. Current Keras baseline compatibility with TensorFlow 2.21.0 is untested.",
            "C++/C, Java, JavaScript, TensorFlow Serving, TensorBoard, TensorFlow Lite standalone/LiteRT, TensorFlow Probability, Datasets and other separately versioned ecosystem packages are not exhaustively extracted; scope decisions and versioned inventories remain release blockers where relevant.",
            "Per-API dtype/device/layout/gradient/error contracts, checkpoint/SavedModel signature semantics, stateful/stateless randomness and distributed failure semantics remain unmapped; API counts do not imply parity.",
            "Deprecated status is not encoded in the goldens: legacy/experimental namespace labels are mechanical hints only; per-API deprecation/stability review remains required.",
        ],
        "counts": counts(records), "records": sorted(records, key=lambda x: (x["symbol"], x["kind"], x["source"])),
    })
    return result


def keras(inputs, workers):
    revision = "250b42181ce9f37df68319d8f4753ec89a349a43"
    tree = inputs.json(f"https://api.github.com/repos/keras-team/keras/git/trees/{revision}?recursive=1")
    assert not tree["truncated"]
    prefix = "keras/api/_tf_keras/keras/"
    files = [x for x in tree["tree"] if x["path"].startswith(prefix) and x["path"].endswith("__init__.py")]

    def extract(entry):
        url = f"https://raw.githubusercontent.com/keras-team/keras/{revision}/{entry['path']}"
        data = inputs.read(url)
        verify_git_blob(data, entry["sha"])
        suffix = entry["path"][len(prefix):].removesuffix("__init__.py").strip("/").replace("/", ".")
        namespace = "tf.keras" + ("." + suffix if suffix else "")
        rows = [{"symbol": namespace, "kind": "module"}]
        for node in ast.parse(data).body:
            if not isinstance(node, ast.ImportFrom):
                continue
            for alias in node.names:
                exported = alias.asname or alias.name
                rows.append({"symbol": namespace + "." + exported, "kind": "export",
                             "alias_target": node.module + "." + alias.name})
        for row in rows:
            row.update({"source": url, "domain": domain(row["symbol"]), "stability": stability(row["symbol"]),
                        "companion_version": "keras==3.15.1"})
        return {"url": url, "sha256": digest(data), "git_blob_sha": entry["sha"], "bytes": len(data), "observed_entries": len(rows)}, rows

    sources, rows = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for source, records in pool.map(extract, files):
            sources.append(source)
            rows.extend(records)
    return sources, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("framework", choices=["pytorch", "tensorflow"])
    parser.add_argument("--cache", default="/tmp/atlas-framework-references")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/parity/reference"))
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    inputs = Inputs(args.cache, args.offline)
    result = pytorch(inputs) if args.framework == "pytorch" else tensorflow(inputs, args.workers)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / (args.framework + ".json")
    target.write_text(json.dumps(result, separators=(",", ":"), ensure_ascii=False) + "\n")
    print(json.dumps({"file": str(target), "sha256": digest(target.read_bytes()),
                      "counts": result["counts"], "source_count": len(result["sources"])}))


if __name__ == "__main__":
    main()
