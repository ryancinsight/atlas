# Atlas-meta coordination folder — index

> Purpose: track coordination notes that cross submodule-claim-stream boundaries (e.g. eunomia ↔ kwavers, ritk ↔ coeus, Apollo ↔ melinoe) but stay within the Atlas-meta doc-claim-free zone (per ADR 0011 §Decision §Leg 2 disjoint-scope rule). Each row points to the canonical coordination note with its current Status + Date + one-line summary + cross-walk anchors.
>
> **Scope rule**: a coordination note in this folder never modifies `repos/<submodule>/**` directly; it documents the cross-claim-stream coordination need and surfaces the handoff to the appropriate claim-stream owner for inner execution. Per-realm coordination (eunomia-only, kwavers-only, ritk-only) belongs in the owning `repos/<submodule>/docs/coordination/` folder (if it exists) — NOT here.

## Listing by date (most recent first)

| Date | ID | One-line summary | Status | Class | Driver(s) | Relates to |
|------|----|------------------|--------|-------|-----------|------------|
| 2026-07-06 | `2026-07-06-eunomia-csr-scalar-phantom-blocker` | Eunomia `csr.rs` non-sealed `Scalar` trait coordination ask reframed: eunomia-side `[patch]` ALREADY LANDED at HEAD `57d7789` per ADR 0006 Path B (additive `ComplexField::zero()`/`::one()` defaults in `crates/eunomia/src/traits/field.rs:149,158`); the residual Phase-1B is kwavers-side (csr.rs swap + kwavers-boundary num_complex→eunomia::Complex64 migration + manifest cleanup) — owned by kwavers claim stream per disjoint-scope (ADR 0011 §Leg 2 ABSOLUTE). ADR 0008 §Decision §0 reframed accordingly. | Reconciled — eunomia-side `[patch]` CLOSED at HEAD `57d7789`; residual Phase-1B back to kwavers claim stream. | `[patch]` coordination note | eunomia (CLOSED retroactively per ADR 0006 Path B) + kwavers (residual Phase-1B owner per disjoint-scope) | ADR 0006, ADR 0008, ADR 0011, ADR 0010 |

## Folder convention

- **Path**: `D:/atlas/docs/coordination/`
- **File naming**: `YYYY-MM-DD-{short-descriptor}.md` (date-suffixed-stable convention; mirrors `D:/atlas/docs/audit/` naming + `D:/atlas/docs/pr/` naming)
- **Frontmatter table**: each file carries a 5-field frontmatter table — Date, Driver, Status, Relates to, Index reference (to this INDEX.md).
- **Atlas-meta claim scope**: this folder is part of the Atlas-meta claim-free zone per ADR 0011 §Decision §Leg 2 (no inner-submodule source edits; only docs/ + workspace-root artifact edits). Files in this folder are Atlas-meta doc/chore/deliverable scope — safe to commit at any time per the cadence rules below.

## Cadence rules

1. **New coordination note authoring**: a new file is authored when a codex session identifies a cross-claim-stream coordination need that cannot be satisfied inside a single inner-submodule's `repos/<submodule>/docs/coordination/` folder (because the coordination needs to surface Atlas-meta visibility + cross-claim-stream handoff signal).
2. **Status flow**: per ADR 0011 §Decision (the SSOT for ADR status flow) — `Proposed` → `Approved` (or `Accepted`) → `Reconciled` (or `Closed`). A coordination note typically reaches `Reconciled` when one or more cross-claim-stream deliverables have landed and the remaining work is owned by a single claim stream.
3. **Retraction cadence**: a coordination note is retracted from `INDEX.md` when (a) the cross-claim-stream coordination need has fully resolved (both/every owning claim stream has landed its atomic commits), OR (b) a follow-up codex session has folded the coordination note's contents into a permanent ADR (in which case the ADR's References section cross-walks back to this folder's prior note entry).
4. **Cross-walk obligation**: each ADR that references a coordination note MUST add the `D:/atlas/docs/coordination/{filename}` cross-walk to its References section. Each coordination note MUST cite the owning ADRs in its Relates-to frontmatter.

## Out of scope (explicit non-goals)

- **Inner-submodule source edits**: per ADR 0011 §Decision §Leg 2 disjoint-scope rule, the Atlas-meta codex session CANNOT edit `repos/<submodule>/<file>` for any submodule. Coordination notes in this folder either (a) document the coordination need (preferred; pure Atlas-meta scope), or (b) propose pre-merge verification commands the inner claim stream should run. They NEVER ship code patches into `repos/<submodule>/`.
- **Per-claim-stream coordination**: coordination between two true-namespace occupants of the same inner-submodule (e.g. two co-located kwavers peers coordinating the per-subcrate `[patch]` sweep timing) belongs in the kwavers own `repos/kwavers/docs/coordination/` (if it exists), NOT here.
- **Backlog PM artifact edits**: rows in `D:/atlas/backlog.md` are SSOT for cross-repo architect coordination ledger + Atlas-root working-tree triage + cross-engineering verification. Coordination notes here cross-walk to backlog.md rows but do NOT replace them — the backlogs are the operational SSOT, coordination notes are the architectural-handoff scaffolding.

## References

- **ADR 0006** — `D:/atlas/docs/adr/0006-eunomia-complex-csr-ssot.md` — the canonical eunomia-side decision for the CR-EUNOMIA-COMPLEX migration; Path B (additive `ComplexField::zero()`/`::one()` defaults) chosen over Variant A (rejected).
- **ADR 0008** — `D:/atlas/docs/adr/0008-kwavers-math-csrscalar-migration.md` — the kwavers-math CsrScalar migration push per-subcrate `[minor]` ADR; §Decision §0 reframed per the 2026-07-06 phantom-blocker discovery.
- **ADR 0010** — `D:/atlas/docs/adr/0010-cfdrs-atlas-pointer-advance.md` — per-batch + sub-counter tag convention + Atlas-parent pointer-advance ceremony.
- **ADR 0011** — `D:/atlas/docs/adr/0011-atlas-root-hygiene-ritual.md` — Atlas-root working-tree hygiene ritual + disjoint-scope rule (§Leg 2) + OOS-record cadence (§Leg 3). This folder's existence + scope rule inherit from §Leg 2.
- **`D:/atlas/docs/audit/`** — adjacent precedent for cross-claim-stream audit notes (`2026-07-02-cross-repo-integration-audit.md`, `2026-07-02-hephaestus-gpu-substrate-audit.md`, `2026-07-02-cross-engineering-verification-audit.md`, `2026-07-01-mnemosyne-soundness-perf-audit.md`, etc.). Coordination notes differ from audits in (a) coordination notes specify a pending deliverable / handoff, audits specify a discovered gap / risk.
- **`D:/atlas/docs/pr/`** — adjacent precedent for `D:/atlas/docs/pr/{NNNN}-{short-descriptor}-pr.md` PR-equivalent plan templates (PR 0007 `helios-internal-dirty-cleanup-pr.md` etc.). Coordination notes are lighter-weight (PM scaffolding) than PR templates (full closure commit chain specification).
