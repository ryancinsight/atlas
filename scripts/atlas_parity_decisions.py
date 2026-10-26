"""Scope policies resolve only from explicit authority, never fabricated approval."""

from atlas_parity_schema import fields, need, nonempty, unique


def validate_decisions(program: dict, rows: list[dict], repositories: dict) -> dict:
    decisions = unique(rows, "id", "decision")
    need(set(decisions) >= {f"DEC-{i:03}" for i in range(1, 10)}, "scope policy decision disappeared")
    for identity, row in decisions.items():
        fields(row, {"state": str, "owner": str, "decision": str, "alternatives_rejected": list,
                     "impact": str, "basis": list, "remaining_design_or_execution": str,
                     "implementation_approval_granted": bool, "scope_reduction": bool}, identity)
        need(row["owner"] in repositories, f"{identity}: unknown decision owner")
        need(row["state"] in {"open", "resolved_by_existing_direction"}, f"{identity}: invalid policy state")
        for key in ("decision", "impact", "remaining_design_or_execution"):
            nonempty(row[key], identity)
        need(bool(row["basis"]) and bool(row["alternatives_rejected"]), f"{identity}: unreasoned policy resolution")
        need(not row["scope_reduction"] and not row["implementation_approval_granted"],
             f"{identity}: policy cannot reduce scope or fabricate architecture approval")
    need(set(program["open_decisions"]) == {key for key, row in decisions.items() if row["state"] == "open"},
         "open scope-policy list differs from decision register")
    need(set(program.get("resolved_policy_decisions", [])) == {
         key for key, row in decisions.items() if row["state"] == "resolved_by_existing_direction"},
         "resolved scope-policy list differs from decision register")
    return decisions
