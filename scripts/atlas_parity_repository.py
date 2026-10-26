"""Repository exits require actual gate records at the selected exact source."""

from atlas_parity_evidence import review
from atlas_parity_schema import digest, fields, https, need, nonempty, revision, unique

RUST_GATES = {"format", "typecheck", "clippy", "unit", "property", "integration",
              "differential", "performance", "semver", "registry", "fresh_consumer",
              "independent_review", "required_ci", "safety_applicability"}
ATLAS_GATES = {"program_validation", "python_tests", "workflow_lint", "debt_ratchet",
               "independent_review", "link_validation", "required_ci"}


def validate_repository_evidence(rows: list[dict], repositories: dict,
                                 atlas_candidate: str | None = None) -> tuple[dict, set]:
    records = unique(rows, "id", "repository evidence")
    qualified = set()
    for identity, row in records.items():
        fields(row, {"repository": str, "revision": str, "gates": list, "review": dict}, identity)
        name = row["repository"]
        need(name in repositories, f"{identity}: unknown repository")
        revision(row["revision"], identity)
        expected = atlas_candidate if name == "atlas" and atlas_candidate else repositories[name]["candidate_revision"]
        need(row["revision"] == expected, f"{identity}: stale repository execution revision")
        review(row["review"], expected, identity)
        gates = unique(row["gates"], "name", identity)
        required = set(repositories[name]["required_gates"])
        need(required <= set(gates), f"{identity}: missing repository exit gates {sorted(required - set(gates))}")
        for gate_name, gate in gates.items():
            fields(gate, {"command": str, "executed": int, "skipped": int, "result": str,
                         "artifact": str, "sha256": str, "environment": dict}, f"{identity}:{gate_name}")
            nonempty(gate["command"], identity)
            need(gate["executed"] > 0 and gate["skipped"] == 0 and gate["result"] == "success",
                 f"{identity}: unexecuted/skipped/failed repository gate {gate_name}")
            need(bool(gate["environment"]), f"{identity}: repository environment absent")
            https(gate["artifact"], identity)
            digest(gate["sha256"], identity)
            if gate_name == "safety_applicability":
                fields(gate, {"fuzz": str, "miri": str, "loom": str, "domain_proof_artifact": str}, identity)
                https(gate["domain_proof_artifact"], identity)
                for safety in ("fuzz", "miri", "loom"):
                    need(gate[safety] in {"executed_pass", "proved_inapplicable"},
                         f"{identity}: unresolved safety applicability {safety}")
        qualified.add(name)
    return records, qualified
