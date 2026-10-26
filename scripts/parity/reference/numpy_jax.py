#!/usr/bin/env python3
"""Extract declared documentation symbols from exact NumPy/JAX release trees.

This is a documentation-source inventory, not proof of public API completeness.
No framework import, execution, dependency installation, or generated-doc build
is performed. Unexpanded autodoc directives are retained as definition gaps.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import urllib.request


ROOT = Path(__file__).resolve().parents[3]
REFERENCES = {
    "numpy": {
        "version": "2.5.4",
        "repository": "numpy/numpy",
        "tag": "v2.5.4",
        "revision": "a3d0ef1df045b858e68115001fdabc930bb3b68c",
        "tree_sha": "838cf31b8096f12d7ca41ededf3ed60d94d37e3d",
        "prefix": "doc/source/",
        "doc_url": "https://numpy.org/doc/2.5/",
        "release_url": "https://pypi.org/pypi/numpy/2.5.4/json",
        "selection_sha256": "04d4e3541780ecbe4ba1db99fd3250f11bb69693e0366a134fb59b18237fc69a",
        "policy_url": "https://numpy.org/doc/2.5/reference/index.html",
    },
    "jax": {
        "version": "0.12.0.1",
        "repository": "jax-ml/jax",
        "tag": "jax-v0.12.0.1",
        "revision": "dc4af684446e65ee98eee8090e1ff6f8211473fb",
        "tree_sha": "bb9547a8148e50cab9c20f8521bf7af7c752b6f6",
        "prefix": "docs/",
        "doc_url": "https://docs.jax.dev/en/latest/",
        "release_url": "https://pypi.org/pypi/jax/0.12.0.1/json",
        "selection_sha256": "6e60595cf7d6ccf50e7c64f42f44f803d12fb6f6ec9b19821d898b81013ad17e",
        "policy_url": "https://docs.jax.dev/en/latest/api_compatibility.html",
    },
}
DIRECTIVE = re.compile(r"^(\s*)\.\.\s+([\w:]+)::\s*(.*)$")
IDENTIFIER = re.compile(r"^[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*$")
AUTO = {
    "automodule": "module", "autoclass": "class",
    "autofunction": "function", "automethod": "method",
    "autoattribute": "attribute", "autoexception": "exception",
    "autodata": "data", "autodecorator": "decorator",
    "autoproperty": "property",
}
PYTHON = {
    "module", "class", "function", "method", "attribute", "exception",
    "data", "decorator", "property", "staticmethod", "classmethod",
    "type", "typealias",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "atlas-parity-inventory/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def domain(symbol: str, path: str) -> str:
    text = (symbol + " " + path).lower()
    rules = [
        ("randomness", ("random",)),
        ("transforms", ("fft", "wavelet")),
        ("nn-optimizers", ("jax.nn", "optimizers", "stax")),
        ("distributed-device", ("sharding", "distributed", "device", "shard_map", "pmap", "mesh", "multihost", "lax.psum", "lax.pmax", "lax.pmin", "lax.ppermute", "lax.psend", "lax.precv", "lax.all_", "collective")),
        ("interoperability-serialization-deployment", ("dlpack", "ffi", "export", "serializ", "c-api", "f2py", "ctypes", "numpy.save", "numpy.load", "memmap", "fromfile", "tofile", "__array")),
        ("autodiff-compiler", ("grad", "jax.jvp", "jax.vjp", "jax.linear", "jax.jit", "vmap", "remat", "checkpoint", "jax.lax", "jaxpr", "jax.stages", "jax.extend", "pallas", "compil", "jax.custom", "jax.eval_shape", "jax.closure")),
        ("dtypes-numerics", ("dtype", "scalar", "linalg", "scipy", "polynomial", "type-promot", "promotion", "ufunc", "numpy.finfo", "numpy.iinfo", "numpy.err", "numpy.seterr", "numpy.geterr")),
        ("tooling", ("test", "profil", "debug", "config", "build", "distutils", "numpy.typing", "numpy.show", "numpy.info", "numpy.lookfor", "jax.print_environment", "jax.clear_caches")),
    ]
    for label, tokens in rules:
        if any(token in text for token in tokens):
            return label
    return "arrays-indexing-layout-numerics"


def qualify(name: str, module: str, framework: str) -> str:
    name = name.lstrip("~!").split("(", 1)[0].strip().replace("::", ".")
    if name.startswith(framework + ".") or name == framework:
        return name
    return module + "." + name if module else name


def stability(symbol: str) -> str:
    if symbol.startswith("jax.experimental."):
        return "experimental-release-documented"
    if symbol.startswith("jax.extend."):
        return "extension-release-documented"
    if symbol.startswith("jax.example_libraries."):
        return "example-library-release-documented"
    if any(x.startswith("_") and not x.startswith("__") for x in symbol.split(".")):
        return "private-name-release-documented"
    return "release-documented-stability-unreviewed"


def native_name(declaration: str) -> str:
    """Read a C declarator's name without mistaking its parameters for it.

    NumPy documents function-pointer members both as ordinary function
    declarators and as parenthesized pointer/type declarators. This is a
    bounded declarator recognizer, not a complete C/C++ parser: unsupported
    forms remain explicit extraction gaps.
    """
    pointer = re.search(r"\(\s*\*\s*([A-Za-z_]\w*)\s*(?:\[[^]]*\]\s*)?\)\s*\(", declaration)
    grouped = re.search(r"\(\s*([A-Za-z_]\w*)\s*\)\s*\(", declaration)
    if pointer or grouped:
        return (pointer or grouped).group(1)
    function = re.search(r"\b([A-Za-z_]\w*)\s*\(", declaration)
    if function:
        return function.group(1)
    # Array extents and initializers are not part of a declarator's name.
    variable = declaration.split("=", 1)[0].split("[", 1)[0].split(":", 1)[0].rstrip(" ;")
    match = re.search(r"\b([A-Za-z_]\w*)\s*$", variable)
    return match.group(1) if match else ""


def parse_document(text: str, path: str, framework: str, initial_module: str = "") -> tuple[list[dict], list[dict]]:
    """Read explicit RST/MyST declarations, retaining every source occurrence."""
    module = initial_module
    declarations: list[dict] = []
    gaps: list[dict] = []
    native_scopes: list[tuple[int, str, str]] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        indentation = len(line) - len(line.lstrip())
        if line.strip():
            while native_scopes and indentation <= native_scopes[-1][0]:
                native_scopes.pop()
        match = DIRECTIVE.match(line)
        if not match:
            # MyST's fenced autodoc directive syntax.
            match = re.match(r"^(\s*)`{3,}\{([\w:]+)\}\s*(.*)$", line)
        if not match:
            index += 1
            continue
        indent, directive, arg = match.groups()
        if directive in {"currentmodule", "py:currentmodule"}:
            module = arg.strip()
        elif directive == "autosummary":
            cursor = index + 1
            while cursor < len(lines):
                candidate = lines[cursor]
                stripped = candidate.strip()
                if stripped and len(candidate) - len(candidate.lstrip()) <= len(indent):
                    break
                if stripped and not stripped.startswith(":"):
                    symbol = qualify(stripped.split()[0], module, framework)
                    if IDENTIFIER.fullmatch(symbol):
                        declarations.append({"symbol": symbol, "kind": "autosummary-object", "line": cursor + 1})
                    else:
                        gaps.append({"line": cursor + 1, "directive": directive, "argument": stripped, "reason": "non-identifier-autosummary-entry"})
                cursor += 1
        else:
            language, _, local = directive.partition(":")
            kind = AUTO.get(directive)
            if kind or (language == "py" and local in PYTHON) or directive in PYTHON:
                kind = kind or (local if language == "py" else directive)
                if kind == "module" and IDENTIFIER.fullmatch(arg.strip()):
                    module = arg.strip()
                symbol = qualify(arg, module, framework)
                if IDENTIFIER.fullmatch(symbol):
                    declarations.append({"symbol": symbol, "kind": kind, "line": index + 1})
                else:
                    gaps.append({"line": index + 1, "directive": directive, "argument": arg, "reason": "unparsed-python-declaration"})
                if directive in AUTO and kind in {"module", "class", "exception"}:
                    following = "\n".join(lines[index + 1:index + 16])
                    if ":members:" in following or kind == "module":
                        gaps.append({"line": index + 1, "directive": directive, "argument": arg, "reason": "autodoc-member-expansion-not-executed"})
            elif language in {"c", "cpp"} and local in {"function", "var", "macro", "type", "enum", "enumerator", "struct", "member", "union"}:
                declaration = arg
                cursor = index
                while declaration.rstrip().endswith("\\") and cursor + 1 < len(lines):
                    cursor += 1
                    declaration = declaration.rstrip()[:-1] + " " + lines[cursor].strip()
                name = native_name(declaration)
                if name:
                    symbol = name
                    details = {"native_name": name, "scope_resolution": "global-declarator"}
                    if local in {"member", "enumerator"}:
                        scope = native_scopes[-1][1] if native_scopes else ""
                        if scope and native_scopes[-1][2] == language:
                            symbol = scope + "." + name
                            details.update(native_scope=scope, scope_resolution="lexical-native-container")
                        else:
                            symbol = f"unresolved::{path}#L{index + 1}::{name}"
                            details["scope_resolution"] = "unresolved-source-occurrence"
                            gaps.append({"line": index + 1, "directive": directive,
                                         "argument": declaration, "reason": "native-member-scope-unresolved"})
                    declarations.append({"symbol": symbol, "kind": directive, "line": index + 1,
                                         "declaration": declaration, **details})
                    if local in {"type", "struct", "union", "enum"}:
                        native_scopes.append((indentation, symbol, language))
                else:
                    gaps.append({"line": index + 1, "directive": directive, "argument": arg, "reason": "unparsed-native-declaration"})
        index += 1
    return declarations, gaps


def extract(framework: str, cache: Path, refresh: bool, output: Path) -> dict:
    config = REFERENCES[framework]
    cache = cache / framework
    cache.mkdir(parents=True, exist_ok=True)
    tree_file = cache / "tree.json"
    tree_url = f"https://api.github.com/repos/{config['repository']}/git/trees/{config['tree_sha']}?recursive=1"
    if refresh or not tree_file.exists():
        tree_file.write_bytes(fetch(tree_url))
    tree_bytes = tree_file.read_bytes()
    tree = json.loads(tree_bytes)
    if tree.get("truncated") or tree["sha"] != config["tree_sha"]:
        raise ValueError(f"{framework}: tree changed or truncated")
    all_docs = [entry for entry in tree["tree"] if entry["type"] == "blob" and entry["path"].startswith(config["prefix"])]
    documents = [entry for entry in all_docs if entry["path"].endswith((".rst", ".md"))]

    def download(entry: dict) -> None:
        target = cache / entry["path"]
        if refresh or not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            url = f"https://raw.githubusercontent.com/{config['repository']}/{config['revision']}/{entry['path']}"
            target.write_bytes(fetch(url))
        # Git blob SHA independently binds downloaded bytes to the release tree.
        data = target.read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual != entry["sha"]:
            raise ValueError(f"{framework}: source blob mismatch: {entry['path']}")

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(download, documents))
    # Autodoc inserts a module's docstring into the reference page. Read those
    # exact module docstrings without importing code or resolving its members.
    module_paths = {}
    for entry in documents:
        text = (cache / entry["path"]).read_text()
        for module in re.findall(r"^\s*\.\.\s+automodule::\s*([\w.]+)", text, re.M):
            base = module.replace(".", "/")
            for candidate in (base + ".py", base + "/__init__.py"):
                found = next((item for item in tree["tree"] if item["path"] == candidate), None)
                if found:
                    module_paths[candidate] = (module, found)
                    break
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(download, [item[1] for item in module_paths.values()]))
    sources, skipped, gaps, grouped = [], [], [], {}
    scans = [(entry, "", 0) for entry in documents]
    scans.extend((entry, module, 0) for module, entry in module_paths.values())
    for entry, initial_module, offset in sorted(scans, key=lambda value: value[0]["path"]):
        path = entry["path"]
        data = (cache / path).read_bytes()
        sources.append({"path": path, "git_blob_sha": entry["sha"], "sha256": digest(data)})
        if "/_templates/" in path:
            skipped.append({"path": path, "reason": "Sphinx template, not concrete API declarations"})
            continue
        source_text = data.decode("utf-8")
        if initial_module:
            syntax = ast.parse(source_text)
            source_text = ast.get_docstring(syntax, clean=False) or ""
            offset = syntax.body[0].lineno - 1 if source_text else 0
        declarations, failures = parse_document(source_text, path, framework, initial_module)
        for failure in failures:
            failure["line"] += offset
            gaps.append({"path": path, **failure})
        for declaration in declarations:
            symbol = declaration["symbol"]
            if not declaration["kind"].startswith(("c:", "cpp:")) and not symbol.startswith(framework + ".") and symbol != framework:
                gaps.append({"path": path, "line": declaration["line"] + offset,
                             "argument": symbol, "reason": "python-namespace-unresolved-in-source"})
            key = (symbol, declaration["kind"] if declaration["kind"].startswith(("c:", "cpp:")) else "python")
            occurrence = {"path": path, "line": declaration["line"] + offset, "kind": declaration["kind"]}
            for detail in ("declaration", "native_name", "native_scope", "scope_resolution"):
                if detail in declaration:
                    occurrence[detail] = declaration[detail]
            grouped.setdefault(key, []).append(occurrence)
    records = []
    for (symbol, language), occurrences in sorted(grouped.items()):
        path = occurrences[0]["path"]
        source = f"https://github.com/{config['repository']}/blob/{config['revision']}/{path}#L{occurrences[0]['line']}"
        records.append({"framework": framework, "version": config["version"], "symbol": symbol,
                        "kind": language if language != "python" else sorted({x["kind"] for x in occurrences})[0],
                        "source": source, "domain": domain(symbol, path),
                        "stability": stability(symbol), "deprecation_status": "not-yet-reviewed",
                        "occurrences": occurrences})
    release_path = cache / "release.json"
    if refresh or not release_path.exists():
        release_path.write_bytes(fetch(config["release_url"]))
    release_bytes = release_path.read_bytes()
    release = json.loads(release_bytes)
    if release["info"]["version"] != config["version"]:
        raise ValueError("release metadata version mismatch")
    result = {
        "schema_version": 1, "framework": framework, "version": config["version"],
        "snapshot_date": "2026-10-26", "source_repository": config["repository"],
        "source_tag": config["tag"], "source_revision": config["revision"], "source_tree": config["tree_sha"],
        "source_tree_url": tree_url, "source_tree_sha256": digest(tree_bytes),
        "release_metadata_url": config["release_url"], "release_metadata_sha256": digest(release_bytes),
        "stable_release_selection": {"observed_on": "2026-10-26", "url": f"https://pypi.org/pypi/{framework}/json",
                                     "observed_info_version": config["version"], "response_sha256": config["selection_sha256"]},
        "release_upload_dates": sorted({item["upload_time_iso_8601"][:10] for item in release["urls"]}),
        "documentation_url": config["doc_url"], "compatibility_policy_url": config["policy_url"],
        "extraction": {
            "method": "all exact-release .rst/.md documentation sources plus available automodule source docstrings; explicit autosummary, Python/autodoc, C/C++ declarations",
            "complete": False,
            "complete_for": "explicit supported declarations in scanned files, subject to listed parser gaps",
            "scope_interpretation": "Source-declared candidate symbols; namespace/domain, public status, deprecation and semantic coverage require reconciliation, not inferred parity.",
            "native_identity": "Members/enumerators use lexical native container qualification; unresolved scopes retain source-occurrence identities and explicit gaps. Callback identities use declarator names, never parameter names.",
            "document_blobs_total": len(all_docs), "rst_md_discovered": len(documents),
            "rst_md_downloaded_and_hash_verified": len(documents), "rst_md_scanned": len(documents) - len(skipped),
            "automodule_docstrings_scanned": len(module_paths), "source_files_downloaded_and_hash_verified": len(sources),
            "unique_symbol_records": len(records), "declaration_occurrences": sum(len(x["occurrences"]) for x in records),
            "counts_by_kind": dict(sorted(Counter(x["kind"] for x in records).items())),
            "counts_by_domain": dict(sorted(Counter(x["domain"] for x in records).items())),
            "unexpanded_or_unparsed_declarations": len(gaps),
            "not_extracted": ["autodoc members generated from imported code and docstrings", "notebook-only API references and signatures", "implicit/generated APIs without explicit source declarations", "per-symbol signature/overload/default/error contracts", "dtype/device/layout/gradient combinations", "prose-only capabilities, deprecations and non-API tooling"],
            "excluded_from_scan": skipped,
            "no_stability_filter": "Private-named, experimental, extension, example-library, legacy and deprecated declarations are retained; review status is explicit.",
            "moving_docs_warning": "JAX latest includes Unreleased and is not used as the extraction revision; NumPy docs use a minor-version URL. Tagged source is authoritative for this extraction.",
        },
        "sources": sources, "extraction_gaps": gaps, "records": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, separators=(",", ":"), ensure_ascii=False) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--framework", choices=["numpy", "jax", "all"], default="all")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--refresh", action="store_true", help="redownload pinned sources; otherwise reuse and verify the source cache")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/parity/reference")
    args = parser.parse_args()
    for framework in REFERENCES if args.framework == "all" else [args.framework]:
        result = extract(framework, args.cache, args.refresh, args.output_dir / (framework + ".json"))
        print(json.dumps({"framework": framework, "version": result["version"], **result["extraction"]}, sort_keys=True))


if __name__ == "__main__":
    main()
