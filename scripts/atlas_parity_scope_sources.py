"""Source-derived public-scope normalization shared by capture and validation."""

from atlas_parity_schema import fields, need, revision


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
        need(document["input"].get("sha256") == expected["inventory_sha256"],
             "TF source audit inventory baseline drift")
        return
    revision(observed[2], "source audit baseline")
    need(observed == (framework, expected["version"], expected["revision"]),
         f"{framework}: source audit version/revision baseline drift")


def family_rows(framework, document, key, source_artifact, caps, repos):
    values = document[key]
    iterable = list(values.items()) if isinstance(values, dict) else list(enumerate(values))
    rows = []
    for entry, original in iterable:
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
