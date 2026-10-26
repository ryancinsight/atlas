"""Source-derived public-scope normalization shared by capture and validation."""

import hashlib

from atlas_parity_schema import digest, fields, need, revision


def audit_identity(framework, document, expected):
    """Reject relabeling before capture, and recheck the complete restored audit."""
    for key, value in {"framework": framework, "version": expected["version"],
                       "reference_version": expected["version"], "revision": expected["revision"],
                       "source_revision": expected["revision"]}.items():
        need(key not in document or document[key] == value, f"{framework}: contradictory audit {key}")
    if framework in {"numpy", "jax"}:
        fields(document, {"framework": str, "version": str, "source_revision": str}, "audit baseline")
        observed = (document["framework"], document["version"], document["source_revision"])
    elif framework == "pytorch":
        fields(document, {"summary": dict}, "Torch audit baseline")
        summary = document["summary"]
        fields(summary, {"framework": str, "version": str, "revision": str}, "Torch audit baseline")
        observed = (summary["framework"], summary["version"], summary["revision"])
        for row in document["records"]:
            need((row.get("framework"), row.get("version"), row.get("revision")) ==
                 (framework, expected["version"], expected["revision"]), "Torch source row baseline drift")
    else:
        fields(document, {"input": dict}, "TF audit baseline")
        need(document["input"].get("sha256") in
             {expected["inventory_sha256"], *expected.get("verified_input_parents", [])},
             "TF source audit inventory baseline drift")
        return
    revision(observed[2], "source audit baseline")
    need(observed == (framework, expected["version"], expected["revision"]),
         f"{framework}: source audit version/revision baseline drift")


def input_parent(expected, parent, parent_sha256):
    """A reviewed correction may consume a frozen classification of the same inventory."""
    digest(parent_sha256, "source-audit parent digest")
    fields(parent, {"input": dict, "records": list, "columns": list, "tables": dict}, "source-audit parent")
    audit_identity("tensorflow", parent, expected)
    fields(parent["input"], {"sha256": str, "count": int}, "source-audit parent inventory")
    need(parent["input"].get("sha256") == expected["inventory_sha256"] and
         0 < len(parent["records"]) == parent["input"]["count"] == expected["inventory_records"],
         "source-audit parent does not bind the selected inventory/count")
    columns = ["declaration_id", "input_index", "symbol", "record_template", "source_ref_set",
               "documentation_template", "typed_relation_ref_set", "semantic_variant_template"]
    table_names = ["record_templates", "source_ref_sets", "documentation_templates",
                   "typed_relation_ref_sets", "semantic_variant_templates"]
    need(parent["columns"] == columns and set(parent["tables"]) == set(table_names) and
         all(type(parent["tables"][name]) is list for name in table_names), "source-audit parent compact schema drift")
    primary = expected["primary_records"]
    need(len(primary) == expected["inventory_records"], "source-audit parent primary record count drift")
    indexes, identities = set(), set()
    for row in parent["records"]:
        need(type(row) is list and len(row) == len(columns), "source-audit parent malformed row")
        index = row[1]
        need(type(index) is int and 0 <= index < len(primary) and index not in indexes,
             "source-audit parent duplicate/missing/invalid input index")
        indexes.add(index)
        selected = []
        for cell, name in zip(row[3:], table_names):
            need(type(cell) is int and 0 <= cell < len(parent["tables"][name]),
                 "source-audit parent invalid table reference")
            selected.append(parent["tables"][name][cell])
        template, source_refs, documentation, relations, variants = selected
        fields(template, {"kind": str}, "source-audit parent template")
        need(type(source_refs) is list and type(documentation) is dict and type(relations) is list and
             type(variants) is dict, "source-audit parent malformed table value")
        reference = primary[index]
        declaration = hashlib.sha256("\0".join((reference["symbol"], reference["kind"],
                                               reference["source"])).encode()).hexdigest()[:24]
        need(row[0] == declaration and row[0] not in identities and row[2] == reference["symbol"] and
             template["kind"] == reference["kind"], "source-audit parent declaration differs from frozen primary")
        identities.add(row[0])
    need(indexes == set(range(len(primary))), "source-audit parent missing frozen primary record")
    return {**expected, "verified_input_parents": [parent_sha256]}


def family_rows(framework, document, key, source_artifact, caps, repos):
    values = document[key]
    iterable = list(values.items()) if isinstance(values, dict) else list(enumerate(values))
    rows = []
    for entry, original in iterable:
        need(original.get("framework", framework) == framework and
             ("frameworks" not in original or framework in original["frameworks"]),
             "raw family framework differs from its source document")
        name = original.get("contract_id", original.get("id"))
        owner = original.get("accountable_owner", original.get("accountable_owner_proposal"))
        cap = original.get("capability", original.get("canonical_capability"))
        cap_ids = original.get("canonical_capability_ids", [cap] if cap else [])
        # Atlas evidence/triage accountability is never an implementation route.
        resolved = owner in repos and owner != "atlas" and bool(cap_ids)
        if not resolved:
            owner, cap_ids = None, []
        prerequisites = sorted({dep for cap_id in cap_ids for dep in caps[cap_id]["prerequisites"]})
        rows.append({"id": framework + ":" + name, "framework": framework,
                     "source_artifact": source_artifact, "source_entry": [key, entry],
                     "planned_owner": owner, "owner_revision": repos[owner]["candidate_revision"] if owner else None,
                     "capabilities": cap_ids, "prerequisites": prerequisites,
                     "route_state": "canonical_family_proposal" if resolved else "ownership_unresolved",
                     "semantic_definition_complete": False,
                     "signature_variants_and_effects": "Per-reference source detail; no shared-name equivalence",
                     "implementation_owner_verified": False})
    return rows


def classify(framework, row):
    classes = {"numpy": {"private implementation declaration", "public documented contract",
                         "public export pending documented semantics", "source-backed alias/view"},
               "jax": {"documented_alias_or_inherited_generated_view", "public_documented_or_exported",
                       "private_implementation_positive_evidence", "unresolved"},
               "pytorch": {"documented_public_contract", "private_implementation_positive_evidence",
                           "public_alias_inherited_generated_view", "unresolved"},
               "tensorflow": {"documented_public_api", "positive_evidence_private_implementation",
                              "public_export_view_alias_generated_inherited_identity", "unresolved"}}
    key = "scope_classification" if framework == "pytorch" else "scope_class" if framework == "tensorflow" else "classification"
    need(framework in classes and isinstance(row.get(key), str) and row[key] in classes[framework],
         "unknown source publicness classification")
    need(row.get("excluded", False) is False and row.get("unsupported_capability_exclusion", False) is False,
         "source classification cannot exclude a retained obligation")
    if framework == "numpy":
        kind = row["classification"]
        visible = ("internal_source_candidate" if row["visibility"] == "private" else
                   "public_export_or_view" if "view" in kind or "export" in kind else "documented_public")
        return (visible, row["candidate_role"], row["primary_contract"],
                "; ".join(view.get("kind", "declaration view") for view in row["signature_variant_links"]))
    if framework == "jax":
        kind = row["classification"]
        visible = ("publicness_unresolved" if kind == "unresolved" else
                   "internal_source_candidate" if kind == "private_implementation_positive_evidence" else
                   "public_export_or_view" if "view" in kind else "documented_public")
        return visible, kind, row["group"], row["signature"]["status"]
    if framework == "pytorch":
        kind = row["scope_classification"]
        visible = ("documented_extension_hook" if kind == "private_implementation_positive_evidence" else
                   "publicness_unresolved" if kind == "unresolved" else
                   "public_export_or_view" if "view" in kind else "documented_public")
        return visible, kind, row["family_proposal"], row["signature"]["status"]
    kind = row["scope_class"]
    # The current policy page conflicts with frozen public API traversal/goldens.
    # Preserve all 486 proposals as unresolved; no namespace-based exclusion.
    visible = ("publicness_unresolved" if kind in {"positive_evidence_private_implementation", "unresolved"} else
               "documented_public" if kind == "documented_public_api" else "public_export_or_view")
    return visible, ";".join(row["identity_roles"]), row["family_id"], row["documentation"]["status"]
