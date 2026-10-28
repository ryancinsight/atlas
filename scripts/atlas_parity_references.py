"""Frozen reference documents and explicit supplemental identities, without name dedupe."""

import hashlib
from collections import Counter
from pathlib import Path

from atlas_parity_schema import (api_identity, digest, fields, https, local_path, need,
                                 nonempty, read_json, revision, unique)

FRAMEWORKS = {"numpy", "jax", "pytorch", "tensorflow"}


def _documents(root: Path, documents: list[tuple[str, dict]]) -> tuple[dict, list[dict]]:
    result, summaries = {}, []
    for framework, snapshot in documents:
        fields(snapshot, {"version": str, "path": str, "sha256": str, "records": int,
                          "unique_symbols": int, "public_surface_complete": bool,
                          "semantics_complete": bool}, framework)
        digest(snapshot["sha256"], framework)
        path = local_path(root, snapshot["path"])
        need(hashlib.sha256(path.read_bytes()).hexdigest() == snapshot["sha256"],
             f"{framework}: snapshot content hash drift")
        data = read_json(path)
        fields(data, {"framework": str, "version": str, "source_revision": str,
                      "records": list, "sources": list, "extraction": dict}, framework)
        need(data["framework"] == framework and data["version"] == snapshot["version"],
             f"{framework}: reference version mismatch")
        revision(data["source_revision"], framework)
        need(bool(data["sources"]), f"{framework}: no extraction sources")
        for source in data["sources"]:
            fields(source, {"sha256": str}, framework)
            digest(source["sha256"], framework)
            if "url" in source:
                https(source["url"], framework)
            else:
                nonempty(source.get("path"), framework)
        source_urls = {}
        source_paths = set()
        for source in data["sources"]:
            if "path" in source:
                source_paths.add(source["path"])
            url = source.get("url")
            if url is None:
                source_paths.add(source["path"])
                url = (f"https://github.com/{data['source_repository']}/blob/"
                       f"{data['source_revision']}/{source['path']}")
            need(url not in source_urls, f"{framework}: duplicate source manifest identity")
            source_urls[url] = source
        extraction = data["extraction"]
        for key in ("source_count", "source_files_downloaded_and_hash_verified"):
            if key in extraction:
                need(extraction[key] == len(source_urls), f"{framework}: source count drift")
        need(len(data["records"]) == snapshot["records"] > 0, f"{framework}: record count drift")
        need(len({row["symbol"] for row in data["records"]}) == snapshot["unique_symbols"],
             f"{framework}: symbol count drift")
        counts = data.get("counts", {})
        if counts:
            need(counts.get("records") == len(data["records"]), f"{framework}: declared count mismatch")
        else:
            need(data["extraction"].get("unique_symbol_records") == len(data["records"]),
                 f"{framework}: declared count mismatch")
        for axis, aggregate in (("kind", "by_kind"), ("domain", "by_domain"), ("stability", "by_stability")):
            declared = counts.get(aggregate, extraction.get(f"counts_{aggregate}"))
            if declared is not None:
                need(declared == dict(Counter(row[axis] for row in data["records"])),
                     f"{framework}: {axis} aggregate drift")
        if "unique_symbols" in counts:
            need(counts["unique_symbols"] == snapshot["unique_symbols"], f"{framework}: unique symbol aggregate drift")
        if "declaration_occurrences" in extraction:
            need(extraction["declaration_occurrences"] == sum(len(row.get("occurrences", [])) for row in data["records"]),
                 f"{framework}: declaration occurrence count drift")
        occurrence_counts = Counter(row["source"].split("#", 1)[0] for row in data["records"])
        for row in data.get("documentation_records", []):
            occurrence_counts[row["source"].split("#", 1)[0]] += 1
        documentation = data.get("documentation_records", [])
        documentation_counts = data.get("documentation_counts", {})
        if documentation_counts:
            need(documentation_counts.get("records") == len(documentation) and
                 documentation_counts.get("unique_symbols") == len({row["symbol"] for row in documentation}),
                 f"{framework}: documentation aggregate drift")
            for axis in ("kind", "domain", "stability"):
                need(documentation_counts.get(f"by_{axis}") == dict(Counter(row[axis] for row in documentation)),
                     f"{framework}: documentation {axis} aggregate drift")
        need(set(occurrence_counts) <= set(source_urls), f"{framework}: API source absent from source manifest")
        for url, source in source_urls.items():
            if "observed_entries" in source:
                need(source["observed_entries"] == occurrence_counts[url],
                     f"{framework}: per-source declaration count drift")
                if "parsed_entries" in source:
                    need(source["parsed_entries"] == source["observed_entries"], f"{framework}: source parse loss")
        complete = data["extraction"].get("public_surface_complete", data["extraction"].get("complete"))
        need(type(complete) is bool and complete == snapshot["public_surface_complete"],
             f"{framework}: completeness claim differs from extraction")
        for row in data["records"]:
            fields(row, {"domain": str, "stability": str}, framework)
            identity = api_identity(framework, data["version"], row)
            need(identity not in result, f"{framework}: duplicate API identity {identity}")
            https(row["source"], identity)
            for occurrence in row.get("occurrences", []):
                fields(occurrence, {"path": str, "line": int}, identity)
                need(occurrence["path"] in source_paths and occurrence["line"] > 0,
                     f"{identity}: occurrence absent from source manifest or invalid line")
            need(row.get("framework", framework) == framework and
                 row.get("version", data["version"]) == data["version"], f"{identity}: per-row version drift")
            result[identity] = {**row, "framework": framework, "version": data["version"]}
        summaries.append({"framework": framework, "version": data["version"],
                          "records": snapshot["records"], "unique_symbols": snapshot["unique_symbols"],
                          "public_surface_complete": complete})
    return result, summaries



def references(root: Path, snapshots: list[dict]) -> tuple[dict, list[dict]]:
    frozen = unique(snapshots, "framework", "reference snapshot")
    need(set(frozen) == FRAMEWORKS, "all four reference frameworks are required")
    documents = []
    for framework, snapshot in frozen.items():
        documents.append((framework, snapshot))
        for supplement in snapshot.get("supplements", []):
            need(supplement.get("framework") == framework and supplement.get("version") == snapshot["version"],
                 f"{framework}: supplement changes frozen release")
            documents.append((framework, supplement))
    rows, parts = _documents(root, documents)
    summary = []
    for framework, snapshot in frozen.items():
        own = [r for r in rows.values() if r["framework"] == framework]
        summary.append({"framework": framework, "version": snapshot["version"], "records": len(own),
                        "unique_symbols": len({r["symbol"] for r in own}),
                        "documents": sum(part["framework"] == framework for part in parts),
                        "public_surface_complete": all(part["public_surface_complete"]
                                                       for part in parts if part["framework"] == framework)})
    return rows, summary
