"""Portable source receipts for the bounded core tensor semantic slice.

Hash and line consistency is a source-integrity check. Independent review of the
original cached blobs remains necessary; no framework/runtime test is implied.
"""

import hashlib

from atlas_parity_schema import digest, fields, https, need, revision, unique

REPOSITORIES = {"numpy": "numpy/numpy", "jax": "jax-ml/jax", "pytorch": "pytorch/pytorch",
                "tensorflow": "tensorflow/tensorflow"}


def source_identity(row, baselines):
    framework = row.get("framework")
    need(framework in baselines, "core source: unknown framework")
    revision(row.get("revision"), "core source")
    need(row["revision"] == baselines[framework]["revision"], "core source: frozen revision changed")
    return f"https://github.com/{REPOSITORIES[framework]}/blob/{row['revision']}/{row['path']}"


def validate_numpy_jax(receipts, witnesses, baselines):
    fields(receipts, {"sources": dict, "citations": dict, "builds": int,
                      "framework_imports": int, "network_requests": int,
                      "whole_framework_source_or_semantic_complete": bool}, "core NumPy/JAX receipts")
    need(receipts["builds"] == receipts["framework_imports"] == receipts["network_requests"] == 0 and
         receipts["whole_framework_source_or_semantic_complete"] is False,
         "core NumPy/JAX source capture cannot assert runtime or closure")
    sources, citations = receipts["sources"], receipts["citations"]
    fields(witnesses, {"witnesses": dict}, "core NumPy/JAX witnesses")
    need(witnesses["witnesses"].keys() == citations.keys(), "core citation/witness set drift")
    for key, row in sources.items():
        fields(row, {"framework": str, "path": str, "revision": str, "version": str,
                     "line_count": int, "bytes": int, "sha256": str, "git_blob": str}, key)
        digest(row["sha256"], key)
        revision(row["git_blob"], key)
        need(key == row["framework"] + ":" + row["path"] and row["line_count"] > 0 and row["bytes"] > 0 and
             row["url"] == source_identity(row, baselines) and
             row["version"] == baselines[row["framework"]]["version"], "core source key/version/URL drift")
    for identity, row in citations.items():
        fields(row, {"source_key": str, "start": int, "end": int, "sha256": str, "url": str}, identity)
        need(row["source_key"] in sources, "core citation: unknown source")
        source = sources[row["source_key"]]
        witness = witnesses["witnesses"][identity]
        fields(witness, {"text": str}, identity)
        need(all(witness.get(key) == value for key, value in row.items()), "core citation witness identity drift")
        need(0 < row["start"] <= row["end"] <= source["line_count"] and
             len(witness["text"].splitlines()) == row["end"] - row["start"] + 1 and
             hashlib.sha256(witness["text"].encode()).hexdigest() == row["sha256"] and
             row["url"] == source["url"] + f"#L{row['start']}-L{row['end']}",
             "core citation hash/bounds/URL drift")
    return set(citations)


def validate_torch_tf(document, provenance, baselines):
    fields(document, {"records": list, "count": int}, "core Torch/TF witnesses")
    rows = unique(document["records"], "id", "core Torch/TF witness")
    registry = unique(provenance["records"], "key", "core Torch/TF source")
    for key, row in registry.items():
        fields(row, {"bytes": int, "line_count": int, "sha256": str, "git_blob_sha": str}, key)
        digest(row["sha256"], key)
        revision(row["git_blob_sha"], key)
        blob_url = source_identity(row, baselines)
        raw_url = f"https://raw.githubusercontent.com/{REPOSITORIES[row['framework']]}/{row['revision']}/{row['path']}"
        need(key == row["framework"] + "|" + row["path"] and row["bytes"] > 0 and row["line_count"] > 0 and
             row["url"] in {blob_url, raw_url}, "core Torch/TF source registry drift")
    need(len(rows) == document["count"], "core Torch/TF witness count drift")
    for identity, row in rows.items():
        fields(row, {"framework": str, "revision": str, "path": str, "source_sha256": str,
                     "git_blob_sha": str, "line_start": int, "line_end": int,
                     "excerpt": str, "excerpt_sha256": str, "url": str}, identity)
        digest(row["source_sha256"], identity)
        digest(row["excerpt_sha256"], identity)
        revision(row["git_blob_sha"], identity)
        key = row["framework"] + "|" + row["path"]
        need(key in registry, "core Torch/TF witness source absent")
        source = registry[key]
        need(row["source_sha256"] == source["sha256"] and row["git_blob_sha"] == source["git_blob_sha"] and
             row["source_file_bytes"] == source["bytes"] and row["source_file_line_count"] == source["line_count"],
             "core Torch/TF witness source dimensions/hash drift")
        need(0 < row["line_start"] <= row["line_end"] <= source["line_count"] and
             len(row["excerpt"].splitlines()) == row["line_end"] - row["line_start"] + 1 and
             hashlib.sha256(row["excerpt"].encode()).hexdigest() == row["excerpt_sha256"] and
             row["url"] == source_identity(row, baselines) + f"#L{row['line_start']}-L{row['line_end']}",
             "core Torch/TF witness hash/bounds/URL drift")
        https(row["url"], identity)
    return set(rows)


def validate_provider_boundaries(document, witnesses, capabilities, repositories):
    fields(document, {"contracts": list, "source_files": list, "cohorts": dict}, "core provider audit")
    contracts = unique(document["contracts"], "id", "core provider contract")
    sources = {(row["repo"], row["path"]): row for row in document["source_files"]}
    need(len(sources) == len(document["source_files"]), "core provider: duplicate source")
    measured = {(row["repo"], row["path"]): row for row in witnesses["sources"]}
    need(len(measured) == len(witnesses["sources"]) and measured.keys() == sources.keys(),
         "core provider witness source set drift")
    for key, source in sources.items():
        witness = measured[key]
        digest(source.get("sha256"), str(key))
        revision(source.get("git_blob"), str(key))
        fields(witness, {"lines": int, "bytes": int, "anchors": list}, str(key))
        need(source["repo"] in repositories and source["revision"] ==
             repositories[source["repo"]]["candidate_revision"] and
             all(witness[name] == source[name] for name in ["revision", "git_blob", "bytes"]) and
             witness["source_sha256"] == source["sha256"] and witness["lines"] > 0 and
             source["source_url"] == f"https://github.com/ryancinsight/{source['repo']}/blob/"
             f"{source['revision']}/{source['path']}", "core provider source provenance drift")
        for anchor in witness["anchors"]:
            digest(anchor.get("sha256"), str(key))
    anchors = set()
    for identity, row in contracts.items():
        cap = row["canonical_capability"]
        need(cap in capabilities and row["single_accountable_owner"] == capabilities[cap]["owner"] and
             row["canonical_prerequisites"] == capabilities[cap]["prerequisites"], "core provider owner/DAG drift")
        status = row["status"]
        need(status["source_boundary_observed"] is True and type(status["tests_executed_this_audit"]) is int and
             status["tests_executed_this_audit"] == 0 and all(status[key] is False for key in
             ["design_ADR_approved", "full_semantic_definition", "implementation_complete", "external_verified",
              "owner_proposal_approved", "performance_qualified", "released"]), "core provider: unsupported qualification")
        for anchor in row["sources"]:
            key = (anchor["repo"], anchor["path"])
            need(key in sources, "core provider anchor missing source")
            source, witness = sources[key], measured[key]
            need(source["revision"] == repositories[source["repo"]]["candidate_revision"] and
                 all(anchor[name] == source[name] for name in ["revision", "git_blob", "sha256"]) and
                 witness["source_sha256"] == source["sha256"] and witness["git_blob"] == source["git_blob"] and
                 witness["revision"] == source["revision"], "core provider source pin/hash drift")
            start, end = anchor["line_start"], anchor["line_end"]
            need(type(start) is int and type(end) is int and 0 < start <= end <= witness["lines"],
                 "core provider source anchor bounds")
            token = (key, identity, start, end)
            anchors.add(token)
            need(sum(a["contract_id"] == identity and a["line_start"] == start and a["line_end"] == end
                     for a in witness["anchors"]) == 1, "core provider anchor witness missing")
    witnessed = {(key, a["contract_id"], a["line_start"], a["line_end"])
                 for key, row in measured.items() for a in row["anchors"]}
    need(witnessed == anchors, "core provider: unbound anchor witness")
    return contracts
