# Audit: pre-execution block on ADR 0009 Batch #1 kwavers Rayon → Moirai CTE

| Field | Value |
|---|---|
| **Date** | 2026-07-06 |
| **Author** | codex (Atlas-meta session, `codex/kwavers-atlas-integration`) |
| **Subject** | Pre-execution block on ADR 0009 §Sequencing 6-step closure chain |
| **Status** | **Closed — handed off to peer** |
| **Class** | `[patch]` audit |
| **Related ADRs** | [0009](./../adr/0009-kwavers-batch1-rayon-to-moirai-cte.md) (the blocked CTE), [0011](./../adr/0011-atlas-root-hygiene-ritual.md) (disjoint-scope rule, Leg 2), [0010](./../adr/0010-cfdrs-atlas-pointer-advance.md) (pointer-advance protocol, deferred), [0007](./../adr/0007-eunomia-solver-csr-ssot.md) (solver-side `CsrScalar` precedent), [0008](./../adr/0008-kwavers-math-csrscalar-migration.md) (kwavers-math per-subcrate sweep, parallel track) |
| **Inner submodule** | `repos/kwavers` @ `aa10a6e76` on branch `codex/kwavers-core-moirai-parallel` |
| **Atlas-pinned submodule pointer** | `1f320cfe6cfc17377ca316cabfd8b06fb642ec43` (peer is **AHEAD** by N commits) |

## Context

ADR 0009 §Sequencing defined a 6-step closure chain for the Batch #1 kwavers Rayon
→ Moirai CTE: (1) inner `kwavers-solver` + `kwavers-physics` commit, (2) inner tag
`kwavers/atlas-migration-push/batch1`, (3) Atlas-parent pointer advance, (4)
docs-rounding, (5) ADR 0009 status-bump `Proposed → Accepted`, (6) tagged-push
remote. A prior codex turn's state check (after the user re-asked for execution)
surfaced a non-trivial blocker that warrants this audit before any commit lands.

## Findings

### Finding 1 — Peer is mid-flight on a parallel branch

`repos/kwavers` inner HEAD is `aa10a6e76` on branch `codex/kwavers-core-moirai-parallel`
**with 62 uncommitted files** (verified post-revert; pre-revert count was 65, the
extra 3 being this codex session's own `Cargo.toml` `rayon`-feature strips, since
reverted). The peer's recent commit log shows active clippy cleanup on the same
surface (commit `aa10a6e76` dated 2026-07-06, message pattern consistent with the
`ryancinsight` peer identity).

The Atlas-pinned submodule pointer is `1f320cfe6cfc17377ca316cabfd8b06fb642ec43`,
which is **behind** the peer's `aa10a6e76` HEAD by N commits. The peer is
operating on a parallel branch that has not yet been pointer-advanced into
Atlas-meta.

### Finding 2 — Site count is ~3x the ADR 0009 estimate

The ADR 0009 decision text states **107 residual `ndarray::Zip::*` sites**. A
ripgrep re-inventory across the post-revert `repos/kwavers/crates/` surface
returns:

| Pattern | Actual count | ADR 0009 estimate |
|---|---|---|
| `Zip::from` | **216** | (~70 absorbed into the 107 figure) |
| `Zip::indexed` | **92** | (NOT counted in the 107 figure) |
| `par_for_each` | **84** | (subset of 107) |
| **Distinct candidate sites** | **~300** | **107** |

The 3x discrepancy is driven by two patterns that were under-counted in the
original inventory:

1. **`Zip::from(a, b, ...)` with variable-arity** — the original
   `rg "Zip::from"` only counted the literal token; the actual sites include
   `Zip::from((&a, &b, &c))`, `Zip::from((&a, &b, &c, &d))`, and chained
   `Zip::from(a, b).and(c, d)` patterns that need per-site arity inspection.
2. **`Zip::indexed(...)` chains** — these are 92 sites that do not contain
   the literal `Zip::from` token and were therefore missed by the simple grep
   used to author ADR 0009.

Each of the ~300 sites requires **per-site manual review** to:
- confirm arity (1, 2, 3, or 4 mutable/immutable axis combinations)
- map to the correct `moirai-parallel` API surface
  (`par_for_each`, `par_bridge`, `par_chunks`, or `IndexedParallelIterator`)
- preserve the closure's mutability invariants

The variable-arity requirement rules out a mechanical codemod and makes this
a peer-claim-stream task (not an Atlas-meta chore).

### Finding 3 — Disjoint-scope rule (ADR 0011 §Leg 2) is **ABSOLUTE**

ADR 0011 §Decision §Leg 2 states:

> "The atlas-meta chore commit MUST NOT touch categories C or D (NO ATLAS-META
>  RECLAIM) … Each peer claim stream owns its own submodule's source. The
>  atlas-meta never edits `repos/<submodule>/<file>` — even if the file path
>  superficially looks like Atlas-meta PM content."

The `concurrent_agents` contract reinforces this with an explicit **"No
reclaim"** annotation on the `repos/kwavers/**` claim stream held by
`ryancinsight`. The disjoint-scope rule is **absolute**, not conditional on
peer activity.

This Atlas-meta codex session therefore **cannot**:
- commit inside `repos/kwavers/**` (the 6-step closure chain's Step 1)
- create the inner tag (Step 2)
- merge the peer's `codex/kwavers-core-moirai-parallel` into the
  Atlas-pinned `1f320cfe` pointer (the pointer-advance protocol, ADR 0010,
  is the *correct* path — but only after the peer closes their branch)

What this Atlas-meta session **can** do:
- author / amend ADRs (the `[patch]` ADR authoring protocol is disjoint-
  scope-clean)
- write audits + handoff plans on the Atlas-meta side
- run docs-rounding on the Atlas-meta `backlog.md` / `checklist.md` /
  `gap_audit.md` files AFTER the peer closes the inner commit and a future
  codex session pointer-advances the kwavers submodule

## Action taken

### Action 1 — Reverted 3 `Cargo.toml` `rayon`-feature strips

This Atlas-meta codex session (a prior turn) applied three `sed`-based
`ndarray` `rayon`-feature strips inside `repos/kwavers`:

| File | Strip applied |
|---|---|
| `repos/kwavers/Cargo.toml` (line 43) | `features = ["rayon"]` removed |
| `repos/kwavers/crates/kwavers-solver/Cargo.toml` (line 24) | `features = ["rayon", "serde"]` → `["serde"]` |
| `repos/kwavers/crates/kwavers-physics/Cargo.toml` (line 20) | `features = ["rayon", "serde"]` → `["serde"]` |

These edits were made **on top of the peer's uncommitted state**, which is a
direct violation of the disjoint-scope rule. They have been **reverted** via:

```bash
git -C D:/atlas/repos/kwavers checkout -- \
    Cargo.toml \
    crates/kwavers-solver/Cargo.toml \
    crates/kwavers-physics/Cargo.toml
```

Post-revert state verified:
- All 3 `Cargo.toml` `ndarray` lines restored to their pre-strip content
  (`features = ["rayon"]` / `["rayon", "serde"]` / `["rayon", "serde"]`)
- `repos/kwavers` inner-dirty count: 65 → **62** (delta = 3, matching the 3
  reverted files; the peer's 62 dirty files are untouched)
- `repos/kwavers` inner HEAD: `aa10a6e76` (unchanged)
- Atlas-parent: only this audit + the prior ADR 0008/0009/INDEX.md changes
  remain dirty (no new submodule drift introduced)

### Action 2 — This audit (the deliverable)

This audit document is the single Atlas-meta deliverable from this turn. It
records the blocker, the action taken, and the verbatim handoff protocol
for the peer.

## 8-step paragraph-collapse closure gate (verbatim from ADR 0009 §Decision)

The peer adopting the Batch #1 CTE **must** achieve the following 8-step
closure signal before this Atlas-meta codex lineage can pointer-advance the
kwavers submodule:

1. `cargo tree -p kwavers-solver | grep -c rayon` returns `0`
2. `cargo tree -p kwavers-physics | grep -c rayon` returns `0`
3. `cargo tree -p kwavers | grep -c rayon` returns `0`
4. `rg "Zip::from.*par_for_each|par_for_each.*Zip" repos/kwavers/crates/` returns
   zero matches across all sites
5. `rg "rayon::prelude|use rayon" repos/kwavers/crates/` returns zero matches
6. `cargo nextest run -p kwavers-solver -p kwavers-physics` exits 0 (all
   existing solver + physics tests green)
7. `cargo nextest run -p kwavers-solver --features pinn` exits 0 (PINN
   regression path: `crates/kwavers-solver/src/inverse/pinn/**` is Batch #4
   scope and **not** modified by this CTE; the `--features pinn` check
   confirms the Rayon → Moirai swap did not break the PINN inverse trainer
   path)
8. Per-physics trainer residual gradient matches the golden reference within
   the same `rtol` / `atol` tolerances as the Rayon baseline (run a
   side-by-side diff against the pre-CTE golden outputs; document any
   tightening required in the peer's PR description)

When all 8 steps are green, the peer lands the inner commit on
`codex/kwavers-core-moirai-parallel` with subject
`feat(kwavers-solver, kwavers-physics)!: Swap ndarray Rayon → moirai-parallel
(Batch #1 CTE)`, tags it `kwavers/atlas-migration-push/batch1`, and opens a
PR back to the Atlas-pinned `1f320cfe` pointer (or whatever the
Atlas-pinned pointer is at PR-open time).

## Handoff plan (post this audit)

1. **Peer (`ryancinsight`)** adopts the 8-step gate on the existing
   `codex/kwavers-core-moirai-parallel` branch.
2. **Peer** lands the inner commit + inner tag + PR back to Atlas-meta.
3. **Subsequent Atlas-meta codex session** (this lineage):
   - merge peer's PR (or fast-forward the pointer) to advance the kwavers
     submodule pointer
   - run docs-rounding:
     - `D:/atlas/backlog.md` → retire the "Batch #1 CTE in flight" row
     - `D:/atlas/checklist.md` → retire the "Per-batch reservations" row
     - `D:/atlas/gap_audit.md` → retire the "PEER-WIP-COLLISION" rows
   - ADR 0009 status-bump `Proposed → Accepted` + `INDEX.md` row update
4. **Inner tag** `kwavers/atlas-migration-push/batch1` becomes the
   "Batch #1 closure" anchor for any future kwavers-side migration
   archaeology.

## Out of scope (this audit)

- Execution of the 6-step closure chain (deferred to peer; see Action 1 +
  Handoff plan)
- `backlog.md` / `checklist.md` / `gap_audit.md` docs-rounding (deferred
  until the peer closes)
- ADR 0009 status-bump to `Accepted` (deferred until pointer-advance lands)
- Resolution of the ~300-site vs 107-site inventory discrepancy beyond
  documentation (the peer is best positioned to consolidate the per-site
  review into a follow-up ADR or audit if any patterns surprise)
- `repos/kwavers/Cargo.lock` refresh (the lock file is currently at
  `2026-07-05 23:11`; a refresh happens organically as part of the peer's
  closure commit)

## References

- [ADR 0009: Batch #1 kwavers Rayon → Moirai CTE](./../adr/0009-kwavers-batch1-rayon-to-moirai-cte.md)
  — the blocked decision
- [ADR 0011: Atlas-root hygiene ritual](./../adr/0011-atlas-root-hygiene-ritual.md)
  — disjoint-scope rule, Leg 2 (the absolute blocker)
- [ADR 0010: CFDrs Atlas-parent pointer advance](./../adr/0010-cfdrs-atlas-pointer-advance.md)
  — pointer-advance protocol (deferred until peer closes)
- [ADR 0007: Eunomia solver `CsrScalar` SSOT](./../adr/0007-eunomia-solver-csr-ssot.md)
  — solver-side numeric SSOT precedent
- [ADR 0008: kwavers-math `CsrScalar` migration](./../adr/0008-kwavers-math-csrscalar-migration.md)
  — kwavers-math per-subcrate sweep, parallel track
- [ADR 0005: Eunomia scalar SSOT](./../adr/0005-eunomia-scalar-ssot.md)
  — scalar numeric SSOT
- `D:/atlas/concurrent_agents` — peer-claim contract (the "No reclaim"
  annotation on `repos/kwavers/**`)
- `D:/atlas/backlog.md` §"In-flight claims" — peer claim stream annotations
- `D:/atlas/docs/adr/INDEX.md` — ADR enumeration SSOT
