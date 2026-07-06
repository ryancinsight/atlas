# ADR 0009 — Cadence-Tactic-Exercise (CTE) on Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai) as a `[patch]` roll-forward decision

- Status: **Proposed** — implementation pending next codex-session authorship per `D:/atlas/AGENTS.md` `interaction_policy` + `documentation_discipline` provisions (`[patch]` class default Proposed unless user sign-off).
- Date: 2026-07-06.
- Driver: the inline CTE cadence for Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai) is currently carried only in `D:/atlas/backlog.md` `## In-flight claims (per concurrent_agents)` paragraph as an unenumerated "what the peer is doing" annotation. With ADR 0008 capturing the kwavers-math CsrScalar per-subcrate `[minor]` precedent, the Batch #1 CTE deserves a parallel `[patch]` ADR so the next codex session inherits a clean authorship gate. This ADR captures: (a) the 107 residual `ndarray::Zip::*` sites' per-site migration pattern, (b) the 3 Cargo.toml `ndarray = { features = ["rayon", ...] }` strips, (c) the paragraph-collapse closure gate, and (d) the per-batch tag + ceremony chain per ADR 0010.
- Class: `[patch]`
- Relates to: ADR 0008 (the kwavers-math CsrScalar per-subcrate `[minor]` — adjacent per-subcrate work pattern), ADR 0010 (Atlas-parent pointer advance + Per-batch name pattern; Batch #1 reservation `kwavers/atlas-migration-push/batch1` is the inner-tag target), ADR 0011 (Atlas-root working-tree hygiene ritual; disjoint-scope rule re-affirmed: Atlas-meta does NOT touch kwavers-internal source), ADR 0005 / 0006 / 0007 (numeric SSOT chain — Batch #1 is downstream of the CR-4 closure that enables the Rayon → Moirai MPSC dispatch).
- Supersedes: the implicit CTE cadence for Batch #1 previously carried only inline in `D:/atlas/backlog.md` `## In-flight claims (per concurrent_agents)` paragraph; no prior ADR anchored the per-site migration pattern + the paragraph-collapse closure gate.

## Context

### Batch #1 surface (per `D:/atlas/backlog.md` `## In-flight claims`)

Per the Atlas-parent backlog, peer `ryancinsight` on the `codex/kwavers-core-moirai-parallel` claim stream is actively landing adjacent scope (notably `1dc47028a refactor(kwavers-math)!: Port to eunomia/leto/moirai-parallel, drop nalgebra` and `f36995162 refactor(kwavers-gpu, kwavers-solver)!: Generic GPU provider seam over Hephaestus`). The peer's recent work drained kwavers' inner-dirty from 602 → 132 files via these two landing commits.

**Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai) remains OPEN**: 107 residual `ndarray::Zip::indexed(...).par_for_each(...)` / `Zip::from(...).par_for_each(...)` sites across 40 files (31 in `kwavers-solver`, 9 in `kwavers-physics`); `kwavers-math` and `kwavers-core` are Rayon-free. The 3 affected Cargo.toml `ndarray = { ..., features = ["rayon", ...] }` declarations live at:

- `D:/atlas/repos/kwavers/Cargo.toml:43` (root workspace dep)
- `D:/atlas/repos/kwavers/crates/kwavers-solver/Cargo.toml:24` (solver crate dep)
- `D:/atlas/repos/kwavers/crates/kwavers-physics/Cargo.toml:20` (physics crate dep)

### What "Cadence-Tactic-Exercise (CTE)" means here

A CTE is the doctrinal unit that names the canonical pattern for a finite, well-bounded internal-crate refactor that:

- (Cadence) follows a verifiable per-site enumeration (the 107 sites have a finite, derivable list),
- (Tactic) has a one-time pre-merge + post-merge test contract, and
- (Exercise) is the atomic commit that collapses the 107 sites + the 3 Cargo.toml `rayon` feature strips into a single inner commit.

For Batch #1 CTE, the "paragraph-collapse closure" is the gate: when all 107 sites are migrated AND all 3 Cargo.toml `rayon` features are stripped, the dependency paragraph (Rayon as a transitive kwavers dep) collapses to zero — that's the closure signal. Per the `D:/atlas/backlog.md` `## Migration batches ## Batch #1` row's pass condition, the closure paragraphs are:

> `cargo nextest run -p kwavers-solver` green; spatial-step norm conservation within derived epsilon; `ndarray = ..., features = ["rayon"]` strip from `kwavers-solver/Cargo.toml:24` and `kwavers-physics/Cargo.toml:20` asserts `cargo tree -p kwavers-solver | grep rayon` empty

This is the canonical paragraph-collapse: the Rayon dep paragraph collapses to nothing. ADR 0009 formalizes the CTE cadence as a documented decision.

### What ADR 0009 specifically captures (vs adjacent ADRs)

| Decision thread | Anchored in |
|-----------------|-------------|
| Per-batch name pattern + tag convention (Batch #1 reserved tag `kwavers/atlas-migration-push/batch1`) | ADR 0010 §Per-batch name pattern |
| Atlas-parent pointer-advance ceremony (5-commit closure chain) | ADR 0010 §Decision §Tag pointer anchoring |
| Disjoint-scope rule (Atlas-meta does NOT touch kwavers source) | ADR 0011 §Decision §Leg 2 |
| Per-subcrate `[patch]` sweep tactical (the strategy this CTE follows) | ADR 0007 §Decision (was for CR-EUNOMIA-COMPLEX; CTE adopts the same per-crate-sweep shape) |
| Per-subcrate `[minor]` work scope example (kwavers-math CsrScalar — adjacent precedent) | ADR 0008 §Decision |
| **Batch #1 CTE per-site migration pattern + paragraph-collapse closure gate** | **ADR 0009 §Decision (this ADR)** |

ADR 0009 fills the gap between ADR 0007's per-subcrate sweep tactical + ADR 0008's per-subcrate `[minor]` work scope: what does the per-subcrate `[patch]` (the lowest-class, smallest-scope doctrinal unit) look like for the Batch #1 CTE?

## Decision

Adopt a `[patch]` Cadence-Tactic-Exercise (CTE) on Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai) with the following atomic commit chain:

### 1. Inner commit (the work product — 107 sites + 3 Cargo.toml strips)

Single atomic commit in `repos/kwavers` on branch `codex/kwavers-batch1-rayon-to-moirai` (branch name is peer-session owner's choice per the disjoint-scope rule from ADR 0011 §Decision §Leg 2):

```
refactor(kwavers-solver, kwavers-physics)!: Rayon → Moirai Batch #1 CTE (107 sites + 3 Cargo.toml `rayon` feature strips)

BREAKING CHANGE: ndarray::Zip::* par_for_each callers migrate to
moirai-parallel::par_mut().enumerate() per kwavers-solver's consumer-side
helpers in crates/kwavers-physics/src/parallel.rs (already cover 1-mut
+ N-imm and 2-mut + N-imm arities; 3-mut + N-imm and 4-mut + N-imm
indexed zips are the helper-coverage gap surfaced by the CTE).

Eliminates the Rayon dependency paragraph from the kwavers workspace.
```

Subject style follows conventional-commits BREAKING-CHANGE marker; the `!` in the scope denotes the Rayon-strip is a breaking change for downstream consumers that directly import `rayon` from kwavers (none expected per the disjoint-scope check).

Per-site migration patterns (per `D:/atlas/backlog.md` `## Migration batches ## Batch #1 ## File-line scope`):

- **`par_for_each` Zip → `moirai-parallel::par_mut().enumerate()` (62 sites across 40 files, 31 in `kwavers-solver` + 9 in `kwavers-physics`)**:
  - Caller pattern: `Zip::from(arr1, arr2, ...).par_for_each(|(a, b, ...)| { ... })`
  - Migration: replace with `moirai_parallel::par_mut().enumerate().for_each(|(i, slice)| { ... })` where the slice bounds are computed via the existing kwavers-physics/src/parallel.rs helpers.
- **`Zip::indexed.par_for_each` → `par().enumerate()` (24 sites across same 40 files)**:
  - Caller pattern: `Zip::indexed(arr).par_for_each(|(i, val)| { ... })`
  - Migration: replace with `par().enumerate().for_each(|(i, val)| { ... })` using the consumer-side `for_each_index_with` helper (moirai-parallel `src/ops.rs:155`).

3 Cargo.toml feature strips:

- `D:/atlas/repos/kwavers/Cargo.toml:43` — strip `ndarray = { version = "...", features = ["rayon", ...] }` to `ndarray = { version = "...", default-features = false }` (or remove the `rayon` feature only).
- `D:/atlas/repos/kwavers/crates/kwavers-solver/Cargo.toml:24` — same strip.
- `D:/atlas/repos/kwavers/crates/kwavers-physics/Cargo.toml:20` — same strip.

Per-file dependency ordering: Cargo.toml strips MUST land before the source-site migration commit (the source sites reference `rayon::prelude::*` directly, so a pre-commit gate `cargo build --workspace` will fail otherwise). Recommended atomic commit structure:

- **Step 1a** (separate commit, optional): strip the 3 Cargo.toml `rayon` features + `cargo update --workspace --offline` to refresh Cargo.lock.
- **Step 1b** (the CTE commit): migrate the 107 sites + cargo-build green + tests green.
- **OR** fold both into one atomic commit with the Cargo.toml strip first in the staging (the `git add` order doesn't matter for the tree; the commit message body enumerates them).

The CTE adopts a SINGLE atomic commit (Step 1b only) to keep the audit granularity tight; if the peer-session owner prefers a 2-commit split (Step 1a + Step 1b), that's an acceptable variant — both are documented under §Alternatives considered.

### 2. Inner tag

Annotated tag anchored on the inner commit per ADR 0010 §Decision §"Tag pointer anchoring":

```bash
git -C D:/atlas/repos/kwavers tag -a kwavers/atlas-migration-push/batch1 <inner-SHA> \
  -m "Atlas-provider migration push for kwavers Batch #1 (Rayon -> Moirai CTE; 107 ndarray::Zip sites + 3 Cargo.toml rayon feature strips).

Inner kwavers commit: <inner-SHA> on branch codex/kwavers-batch1-rayon-to-moirai.
Batch #1 reservation per ADR 0010 Per-batch name pattern: kwavers/atlas-migration-push/batch1.
Per-subcrate [patch] CTE (Cadence-Tactic-Exercise) cadence per ADR 0009.
Per-subcrate sweep tactical per ADR 0007.
Adjacent per-subcrate [minor] precedent: kwavers-math CsrScalar per ADR 0008.
Upstream numeric SSOT (CR-4 closure) per ADR 0005 enables the MPSC dispatch.
Atlas-parent ceremony links: pointer advance + docs-rounding + ADR 0009 status-bump commit.

See:
  - ADR 0005 (upstream NumericElement doctrine; consumed by the MPSC dispatch)
  - ADR 0007 (per-subcrate sweep tactical)
  - ADR 0008 (adjacent per-subcrate [minor] precedent)
  - ADR 0009 (this tag's anchoring ADR)
  - ADR 0010 (Per-batch name pattern)
  - ADR 0011 (disjoint-scope rule re-affirmed)
  - D:/atlas/backlog.md ## Migration batches ## Batch #1 row
  - repos/kwavers/CHANGELOG.md ## Unreleased kwavers-solver / kwavers-physics Rayon -> Moirai section"
git -C D:/atlas/repos/kwavers push origin codex/kwavers-batch1-rayon-to-moirai --tags
```

### 3. Atlas-parent pointer advance (ceremony commit)

```bash
git -C D:/atlas add repos/kwavers
# verify staged gitlink SHA = <inner-SHA>
git -C D:/atlas commit -m "chore(atlas): Advance kwavers submodule pointer to <inner-SHA> (Batch #1 Rayon -> Moirai CTE)"
```

### 4. Atlas-parent docs-rounding (SSOT-tracking commit)

```bash
# Modify 3 files: backlog.md (Batch #1 row flip to CLOSED 2026-07-MM); checklist.md (Per-batch reservations table row flip CLOSED); gap_audit.md (PEER-WIP-COLLISION rows affected).
git -C D:/atlas add backlog.md checklist.md gap_audit.md
git -C D:/atlas commit -m "chore(atlas): Sync kwavers pointer <inner-SHA> + Batch #1 CTE closure record"
```

### 5. Atlas-parent ADR 0009 status-bump commit (status: Proposed → Accepted)

Single atomic docs commit that flips ADR 0009's `Status:` line from `**Proposed**` to `**Accepted** — implementation closed 2026-07-MM (Batch #1 CTE landed)` + updates the date to the closure date + updates `D:/atlas/docs/adr/INDEX.md` enumeration table to flip ADR 0009 from "Open Gap" to "Accepted" + removes the Open Gaps entry for 0009 entirely.

### 6. Tagged-push remote

```bash
git -C D:/atlas/repos/kwavers push origin codex/kwavers-batch1-rayon-to-moirai --tags
```

### Paragraph-collapse closure gate

The CTE is "closed" (paragraph-collapse achieved) when ALL of the following are true:

1. `cargo tree -p kwavers-solver | grep rayon` returns zero matches (the Rayon dep paragraph is gone from the solver's dep tree).
2. `cargo tree -p kwavers-physics | grep rayon` returns zero matches (the Rayon dep paragraph is gone from the physics crate's dep tree).
3. `cargo tree -p kwavers | grep rayon` returns zero matches (the Rayon dep paragraph is gone from the root workspace's dep tree).
4. `rg "Zip::from.*par_for_each|par_for_each.*Zip" crates/kwavers-solver/ crates/kwavers-physics/` returns zero matches (all 107 sites migrated).
5. `rg "rayon::prelude|use rayon" crates/kwavers-solver/ crates/kwavers-physics/` returns zero matches (no direct `use rayon` imports in the solver/physics crates).
6. `cargo nextest run -p kwavers-solver -p kwavers-physics` green.
7. `cargo nextest run -p kwavers-solver --features pinn` green (per Batch #4's pre-merge gate; the Batch #1 CTE doesn't break the PINN path).
8. Per-physics trainer residual gradient matches golden reference within neum-compensated epsilon (per `D:/atlas/backlog.md` `## Migration batches ## Batch #4` pass condition; this is the same gate; the Batch #1 CTE doesn't regress the Batch #4 pre-merge gate because the Rayon → Moirai swap is functionally equivalent for the parallel-iterator arity patterns used by the trainer).

When all 8 paragraph-collapse gates are green, the CTE is "closed" and the inner commit is the canonical closure artifact.

### Scope file-line targets (the 107 sites)

Per `D:/atlas/backlog.md` `## Migration batches ## Batch #1 ## File-line scope` enumeration:

| Sub-tree | File-pattern | Site count |
|----------|--------------|------------|
| `kwavers-solver` | `crates/kwavers-solver/src/inverse/reconstruction/seismic/rtm/inherent/{wavefield,propagation,mod,laplacian,imaging,illumination}.rs` | 17 (est) |
| `kwavers-solver` | `crates/kwavers-solver/src/forward/nonlinear/{kuznetsov,westervelt_spectral}/...` | 8 (est) |
| `kwavers-solver` | `crates/kwavers-solver/src/forward/{elastic/swe/int, pstd/ext, multiphysics/fluid_structure}/...` | 24 (est) |
| `kwavers-physics` | `crates/kwavers-physics/src/acoustics/...` | 6 (est) |
| `kwavers-physics` | `crates/kwavers-physics/src/optics/polarization/linear.rs` | 1 |
| **Total `kwavers-solver` (31 files, est)** | | **~50 sites** |
| **Total `kwavers-physics` (9 files, est)** | | **~7 sites** |
| **Sub-total (40 files, est)** | | **~57 sites** |
| **Cross-file helpers** (`crates/kwavers-physics/src/parallel.rs` + `crates/kwavers-solver/src/forward/elastic/swe/integration/integrator/mod.rs` + `crates/kwavers-solver/src/forward/elastic/swe/stress/divergence.rs` + `crates/kwavers-solver/src/forward/pstd/extensions/elastic.rs` + `crates/kwavers-solver/src/forward/pstd/extensions/elastic_orchestrator/split_field_step/{stress,velocity,mod}.rs`) | 5 helper files | ~50 helper call-sites |

Σ ~107 sites across 40 files + 5 helper files. (Per-file counts are estimates; the authoritative count comes from the `rg "par_for_each.*Zip|Zip.*par_for_each" crates/kwavers-{solver,physics}/` pre-commit gate.)

## Alternatives considered

### Rejected Variant A — Fold the Batch #1 CTE into ADR 0007 (treat Batch #1 as one row in the per-subcrate sweep table)

Pros: avoids the ADR-sequence numbering for Batch #1; saves authorship effort.

Cons: ADR 0007's scope is the per-subcrate `[patch]` sweep STRATEGY (the tactical plan), not the per-batch work SCOPE. The Batch #1 CTE has unique closure semantics (paragraph-collapse + 3 Cargo.toml strips + 107-site enumeration) that don't generalize to other per-subcrate sweeps. Fold-in would crowd ADR 0007 with Batch #1-specific details.

**Verdict**: separate ADR 0009 keeps the strategy/work split clean per AGENTS.md's `documentation_discipline`.

### Rejected Variant B — Skip the Batch #1 CTE ADR; rely on the `D:/atlas/backlog.md` `## Migration batches ## Batch #1` row's existing scope description

Pros: the backlog row already mentions Batch #1 + the 107 sites + the 3 Cargo.toml + the paragraph-collapse pass condition.

Cons: the backlog row is a tactical enumeration; ADR 0009 formalizes the CTE cadence (Cadence + Tactic + Exercise) as a documented decision. The backlog row lacks the per-site migration pattern (`Zip::from(...).par_for_each` → `moirai-parallel::par_mut().enumerate()`) and the paragraph-collapse closure gate as an 8-step checklist. ADR 0009 elevates this to a doctrinal anchor.

**Verdict**: not portable; the paragraph-collapse gate is a per-CTE property, not a per-batch-row property.

### Rejected Variant C — Tag the Batch #1 CTE under a different name shape (e.g. `kwavers/atlas-migration-push/cte1` or `kwavers/atlas-migration-push/batch1-fixup`)

Pros: disambiguates the CTE cadence from the cross-Atlas migration batches.

Cons: ADR 0010 §Per-batch name pattern reserves the bare-`batchN` shape for cross-Atlas migration batches. The Batch #1 CTE IS a cross-Atlas migration batch (it's literally `## Migration batches ## Batch #1` in the backlog). It should adopt the `batch1` shape per the existing reservation row in `D:/atlas/checklist.md` `## Per-batch Atlas-provider tag reservations`. A `cte1` or `batch1-fixup` sub-counter would falsely group with the PR 0007's `helios/atlas-migration-push/internal-dirty-batch1` sub-counter (which is a separate convention for inner-cleanup events, NOT a CTE).

**Verdict**: bare-`batch1` is the correct tag name per ADR 0010's Per-batch name pattern + the existing `kwavers/atlas-migration-push/batch1` reservation.

## Failure modes / risks

- **Per-site migration pattern drift.** If the peer-session owner uses a different migration pattern for some sites (e.g., `par_chunks_mut` instead of `par_mut().enumerate()`), the inner commit loses uniformity. **Mitigation**: pre-merge gate `rg "par_for_each.*Zip|Zip.*par_for_each" crates/kwavers-{solver,physics}/` returns zero matches (post-migration); if non-zero, the inner commit is incomplete. **Backstop**: ADR 0009 §Decision §1 enumerates the two canonical patterns; deviations require ADR 0009 amendment or a `kwavers/atlas-migration-push/batch1-fixup` follow-up tag per ADR 0010 §Failure modes.

- **3 Cargo.toml strip ordering.** If the 3 Cargo.toml `rayon` features are stripped but the source sites still reference `rayon::prelude::*` or `use rayon`, the inner commit fails `cargo build --workspace`. **Mitigation**: the source-site migration MUST be in the same atomic commit as the Cargo.toml strip (or in a 2-commit chain where Step 1a = Cargo.toml strip + Step 1b = source migration; in either case, the inner commit message body enumerates them). Pre-merge gate: `cargo build --workspace --locked` MUST return 0.

- **Cargo.lock drift post-Cargo.toml-strip.** The Cargo.lock file will be regenerated by `cargo update --workspace --offline` after the Cargo.toml strip. If the lockfile drift is large, downstream consumers (kwavers-gpu, kwavers-solver, kwavers-physics) may see feature-resolution changes. **Mitigation**: the inner commit's diff stat is bounded by ~3 Cargo.toml lines + 107 source-site lines + 1 Cargo.lock; the kwavers-gpu crate (not in scope of this CTE) is unaffected because it doesn't depend on `rayon` per the disjoint-scope check.

- **Paragraph-collapse pass-condition drift.** If the 8-step closure gate (per §Decision §"Paragraph-collapse closure gate") regresses on any step (e.g., a new test adds a `rayon::prelude::*` import), the CTE closure is invalid. **Mitigation**: per `D:/atlas/checklog.md` `## Migration batches ## Batch #1` row, the existing `cargo nextest run -p kwavers-solver` + `cargo tree -p kwavers-solver | grep rayon` empty pass condition is the canonical gate. ADR 0009 elevates this to an 8-step checklist for explicit peer-session audit.

- **Inner commit scope drift.** If the inner commit rolls in unrelated changes (e.g., kwavers-math CsrScalar rebind per ADR 0008, or a kwavers-gpu GPU kernel fix), the inner commit loses audit granularity. **Mitigation**: peer-session owner + `git -C repos/kwavers diff --stat HEAD~1` pre-merge-vote gate; insist on Batch-#1-only diff (the 107 sites + 3 Cargo.toml strips + Cargo.lock refresh; nothing else).

- **Cross-PR contamination with ADR 0008.** If the peer-session owner authors the kwavers-math CsrScalar rebind (ADR 0008) AND the Batch #1 CTE (ADR 0009) in the same merge window, the two inner commits may conflict at the cargo-build level. **Mitigation**: ADR 0008 (per-subcrate `[minor]`) targets `crates/kwavers-math` only; ADR 0009 (per-subcrate `[patch]`) targets `crates/kwavers-solver` + `crates/kwavers-physics` only. The disjoint-scope rule from ADR 0011 §Decision §Leg 2 applies: Atlas-meta does NOT touch kwavers-internal source; the peer-session owner chooses commit order (recommended: Batch #1 CTE first, then kwavers-math CsrScalar rebind; this avoids Cargo.toml-induced dep-graph churn overlapping the source migration).

- **Cross-PR contamination with the peer's `refactor(kwavers-math)!: drop nalgebra` + `refactor(kwavers-gpu, kwavers-solver)!: GPU provider seam`.** If the peer's two recent landing commits (`1dc47028a` + `f36995162`) are still being rebased, the Batch #1 CTE inner commit may conflict. **Mitigation**: the `D:/atlas/backlog.md` `## In-flight claims` paragraph notes the peer's two commits landed 2026-07-05 22:19; by 2026-07-06 they're stable. The next codex session can author the Batch #1 CTE without coordination risk; if conflict arises, the peer-session owner rebases onto `codex/kwavers-core-moirai-parallel` (the peer's branch).

- **Branch choice drift.** The peer-session owner may want to use `codex/kwavers-core-moirai-parallel` (the peer's existing branch) rather than `codex/kwavers-batch1-rayon-to-moirai` (a new branch). **Mitigation**: per ADR 0010 §Failure modes, the branch choice is the peer-session owner's call; the tag name `kwavers/atlas-migration-push/batch1` resolves regardless of branch (annotated tags are commit-pointer metadata, not branch-locked).

## Verification plan

After the closure chain (steps 1-6 above) lands, the following commands verify:

1. **`git -C D:/atlas/repos/kwavers show-ref --tags kwavers/atlas-migration-push/batch1`** — confirms the tag exists; expected output `<inner-SHA> refs/tags/kwavers/atlas-migration-push/batch1`.
2. **`git -C D:/atlas/repos/kwavers show --no-patch --format='%H %s' kwavers/atlas-migration-push/batch1`** — confirms tag annotation captures ADR 0005 + 0007 + 0008 + 0009 + 0010 + 0011 references.
3. **`git -C D:/atlas/repos/kwavers cat-file -t kwavers/atlas-migration-push/batch1`** — confirms annotated (not lightweight).
4. **`git -C D:/atlas/repos/kwavers rev-parse --abbrev-ref HEAD`** — must be `codex/kwavers-batch1-rayon-to-moirai` (or whatever branch used) at tag-creation time.
5. **`git -C D:/atlas rev-parse HEAD`** — confirms Atlas-parent pointer advance landed; SHA-matches the docs-rounding commit.
6. **`git -C D:/atlas log --oneline -5`** — confirms the docs commit chain: inner pointer + docs-rounding + ADR 0009 status-bump.
7. **`git -C D:/atlas/repos/kwavers ls-remote --tags origin 'kwavers/atlas-migration-push/*'`** — confirms push-reachability.
8. **`cargo tree -p kwavers-solver | grep rayon`** — must return zero matches (paragraph-collapse gate §1).
9. **`cargo tree -p kwavers-physics | grep rayon`** — must return zero matches (paragraph-collapse gate §2).
10. **`cargo tree -p kwavers | grep rayon`** — must return zero matches (paragraph-collapse gate §3, root workspace).
11. **`rg "Zip::from.*par_for_each|par_for_each.*Zip" crates/kwavers-solver/ crates/kwavers-physics/`** — must return zero matches (paragraph-collapse gate §4, all 107 sites migrated).
12. **`rg "rayon::prelude|use rayon" crates/kwavers-solver/ crates/kwavers-physics/`** — must return zero matches (paragraph-collapse gate §5, no direct `use rayon` imports).
13. **`cargo nextest run -p kwavers-solver -p kwavers-physics`** — must return 0 exit code (paragraph-collapse gate §6).
14. **`cargo nextest run -p kwavers-solver --features pinn`** — must return 0 exit code (paragraph-collapse gate §7, PINN path regression check).
15. **`git -C D:/atlas/docs/adr/INDEX.md`** — post-merge, the enumeration table should now have 11 rows (10 prior + 0009); Open Gaps entry for 0009 removed.

## Sequencing (this ADR's authorship + closure chain)

This ADR is authored in the **uncompleted-state** of the Batch #1 CTE: the decision is documented, but implementation is pending next codex-session authorship. The full closure chain (next codex session):

1. Inner kwavers-solver + kwavers-physics CTE commit (per §1 above) — 107 sites + 3 Cargo.toml strips + Cargo.lock refresh.
2. Inner tag creation + push per §2.
3. Atlas-parent pointer advance per §3.
4. Atlas-parent docs-rounding per §4.
5. Atlas-parent ADR 0009 status-bump commit + `INDEX.md` enumeration-table update + Open Gaps entry removal per §5.
6. Pre-flight verification per the 15-step plan above.

If steps 5's `INDEX.md` update is too ambitious for one commit, split into:

- 5a. `INDEX.md` enumeration table row insert for 0009 (one atomic commit).
- 5b. `INDEX.md` Open Gaps entry removal for 0009 (one atomic commit).
- 5c. ADR 0009 status-bump (one atomic commit).

## Out of scope (explicit non-goals)

- **The kwavers-math CsrScalar rebind (per ADR 0008)** — separate per-subcrate `[minor]` work; not part of the Batch #1 CTE. ADR 0008 + ADR 0009 are disjoint-scope per ADR 0011 §Decision §Leg 2.
- **The PINN Burn → Coeus rebind (per `D:/atlas/backlog.md` `## Migration batches ## Batch #4`)** — separate `[minor]` work; not part of the Batch #1 CTE. The Batch #1 CTE is the prerequisite parallel-iterator migration that Batch #4 builds on; Batch #4 authors the Burn-keyed-facade replacement.
- **The `kwavers-gpu` GPU provider seam** — separate `[minor]` work (peer ryancinsight's recent `f36995162 refactor(kwavers-gpu, kwavers-solver)!: Generic GPU provider seam over Hephaestus` already landed 2026-07-05; not part of this CTE's scope).
- **The `kwavers-math` Rayon-strip** — `kwavers-math` and `kwavers-core` are already Rayon-free per the `D:/atlas/backlog.md` `## In-flight claims` paragraph; the CTE scope is `kwavers-solver` + `kwavers-physics` only.
- **The `crates/kwavers-solver/src/inverse/pinn/**` 80 files** — those are Batch #4 (PINN Burn → Coeus) scope, not Batch #1. The Batch #1 CTE should NOT touch the PINN sub-tree; the paragraph-collapse gate §7 ensures the PINN path is not regressed but does not require migrating PINN-source sites.
- **The atomic-implementation commit for the Batch #1 CTE itself** — this ADR documents the decision; the implementation lands in the next codex session's authorship per `D:/atlas/AGENTS.md` `interaction_policy` + `documentation_discipline` provisions.
- **Tag-name changes for any pre-existing `kwavers/atlas-migration-push/*` tags** — Batch #1's `batch1` tag is the FIRST cross-Atlas migration batch to land; no pre-existing tag conflicts. The bare-`batchN` shape is reserved per ADR 0010 §Per-batch name pattern.

## References

- **ADR 0005** — `D:/atlas/docs/adr/0005-eunomia-scalar-ssot.md` — the upstream `eunomia::NumericElement` supertrait doctrine (CR-4 closure enables the MPSC dispatch in `moirai-parallel`).
- **ADR 0007** — `D:/atlas/docs/adr/0007-eunomia-solver-csr-ssot.md` — the per-subcrate `[patch]` sweep tactical strategy this CTE adopts.
- **ADR 0008** — `D:/atlas/docs/adr/0008-kwavers-math-csrscalar-migration.md` — adjacent per-subcrate `[minor]` precedent (kwavers-math CsrScalar rebind; same per-crate work pattern).
- **ADR 0010** — `D:/atlas/docs/adr/0010-cfdrs-atlas-pointer-advance.md` — Per-batch name pattern + Atlas-parent pointer-advance ceremony + tag convention; the `kwavers/atlas-migration-push/batch1` tag is the FIRST reserved row per the per-batch reservations SSOT.
- **ADR 0011** — `D:/atlas/docs/adr/0011-atlas-root-hygiene-ritual.md` — Atlas-root working-tree hygiene ritual; disjoint-scope rule re-affirmed (`NO ATLAS-META RECLAIM` for any kwavers-internal source edits per §Decision §Leg 2).
- **ADR Index** — `D:/atlas/docs/adr/INDEX.md` — to be updated post-merge to mark ADR 0009 as Accepted (currently flagged as Open Gap with `Filename placeholder: D:/atlas/docs/adr/0009-batch1-rayon-to-moirai-cte.md`; the Open Gaps entry reverts post-merge to "CLOSED 2026-07-06 (Proposed)").
- **`D:/atlas/backlog.md`** `## Migration batches ## Batch #1` row + `## In-flight claims (per concurrent_agents)` paragraph — the SSOT for the 107 sites + 3 Cargo.toml + 40-file breakdown.
- **`D:/atlas/checklist.md`** `## Per-batch Atlas-provider tag reservations` — the per-batch reservation SSOT (this ADR's `kwavers/atlas-migration-push/batch1` reservation is the first row; closure status OPEN until next codex-session authorship lands the CTE).
- **`D:/atlas/concurrent_agents`** contract — disjoint-scope rule (re-affirmed per ADR 0011); kwavers-claim-stream ownership of `repos/kwavers/**`.
- **`D:/atlas/repos/kwavers/crates/kwavers-physics/src/parallel.rs`** — the consumer-side helper module that covers 1-mut + N-imm and 2-mut + N-imm arities; the 3-mut + N-imm and 4-mut + N-imm indexed zips are the helper-coverage gap surfaced by the CTE (visible in `crates/kwavers-solver/src/forward/elastic/swe/integration/integrator/mod.rs` + `crates/kwavers-solver/src/forward/elastic/swe/stress/divergence.rs` + `crates/kwavers-solver/src/forward/pstd/extensions/elastic.rs` + `crates/kwavers-solver/src/forward/pstd/extensions/elastic_orchestrator/split_field_step/{stress,velocity,mod}.rs`).
