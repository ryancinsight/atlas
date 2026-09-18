<a id="atlas-stack-leto-churn-017"></a>
## ATLAS-STACK-LETO-CHURN-017 — Upstream working-tree churn blocks consumer verification — todo

outcome: a decided fix for the recurring pattern where the stack `[patch]` overlay resolves first-party deps to local working trees, so a peer's uncommitted mid-edit state in an upstream repo breaks every downstream consumer's verification non-deterministically.
- Recommended direction (b): have the overlay resolve to each member's last *committed* revision rather than its working tree, making peer WIP invisible stack-wide until committed. This is `[arch]` (revises the development-overlay contract) and needs an ADR.
- Falsified: option (c) (narrow the overlay per session to repos an agent edits) — a fourth occurrence (2026-08-13) showed churn spread across four repos a branch never touched; narrowing enough to avoid it would defeat the overlay.
- Current fallback (option a): treat upstream redness as a park-and-switch signal (already the contention-response default), but retrying costs real time since a green run on a churning crate is a peer-quiet window, not evidence.
- next: draft the ADR for option (b) and implement.
