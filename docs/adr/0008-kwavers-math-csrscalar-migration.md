# ADR 0008 — kwavers-math CsrScalar migration push (per-subcrate [minor] — adopts ADR 0006 ComplexField doctrine + ADR 0007 per-subcrate `[patch]` sweep + ADR 0010 Per-batch tag convention)

- Status: **Proposed** — implementation pending next codex-session authorship per `D:/atlas/AGENTS.md` `interaction_policy` autonomy-mode + `documentation_discipline` provisions (`[minor]` class default Proposed unless user sign-off).
- Date: 2026-07-06.
- Driver: the eunomia numeric SSOT chain (ADR 0005 → ADR 0006 → ADR 0007) has a kwavers-math-specific instantiation that requires a separate ADR so the next codex session inherits a clean `[minor]` authorship gate. The kwavers-math `CsrScalar` is the consumer-landing site for the `eunomia::ComplexField` rebind; ADR 0008 captures the per-subcrate work scope, the ceremony chain (per ADR 0010 §Decision), and the pre-merge verification gates.
- Class: `[minor]`
- Relates to: ADR 0005 (eunomia::NumericElement supertrait doctrine — upstream), ADR 0006 (eunomia::ComplexField SSOT doctrine — this push consumes), ADR 0007 (per-subcrate `[patch]` sweep tactical strategy — adopted by this push), ADR 0010 (Atlas-provider migration ceremony + Per-batch name pattern), ADR 0011 (Atlas-root working-tree hygiene ritual; disjoint-scope rule re-affirmed).
- Supersedes: the implicit kwavers-math `CsrScalar` migration push scope previously carried inline under `D:/atlas/backlog.md` `## Migration batches (vertical slices)` consumer-cone descriptions (kwavers-math's `CsrScalar` limb was not separately documented prior to this ADR; ADR 0008 gives it a single anchor).

- Index: docs/adr/INDEX.md#ADR-0008
## Context

### The eunomia numeric SSOT chain (3 limbs)

1. **ADR 0005** — `eunomia::NumericElement` as universal `Scalar` supertrait (CR-4 closure, status Accepted). Establishes the float-vs-int supertrait doctrine proof (`RealField` cannot be a universal supertrait; `NumericElement` is); consumed by CR-EUNOMIA-COMPLEX upstream.
2. **ADR 0006** — `eunomia::ComplexField` as kwavers-math `CsrScalar` SSOT (CR-EUNOMIA-COMPLEX, status Approved, awaiting inner-CR-EUNOMIA-COMPLEX PR closure per ADR 0006 §Decision §"zero()/one() defaults + complex.rs impl update"). Adds `zero()`/`one()` defaults on `ComplexField`; sets the per-batch `num_complex::Complex<T>` migration convention.
3. **ADR 0007** — per-subcrate `[patch]` sweep adopting ADR 0010's Per-batch tag convention (status Proposed, awaiting user sign-off for the per-subcrate sweep schedule). Tactical plan: the kwavers-math CsrScalar migration is the FIRST per-subcrate sweep instance.

ADR 0008 captures the kwavers-math-specific work scope that 0006 establishes the doctrine for + 0007 plans the tactical strategy for: which call-sites in `crates/kwavers-math` migrate, in what commit-order, with what per-batch tag, what per-crate `[patch]` semantics, and what verification gates.

### What ADR 0008 specifically captures (vs ADR 0006 / 0007 / 0010)

| Decision thread | Anchored in |
|-----------------|-------------|
| Doctrine: `ComplexField` as universal complex supertrait | ADR 0006 §Decision |
| Tactical: per-subcrate `[patch]` sweep adopting ADR 0010's Per-batch tag convention | ADR 0007 §Decision |
| **kwavers-math-specific work scope, ceremony chain, pre-merge verification gates** | **ADR 0008 §Decision (this ADR)** |
| Per-batch name pattern shape (`*atlas-migration-push/{batchN}` + sub-counter `*atlas-migration-push/<patch-id>`) | ADR 0010 §Per-batch name pattern |
| Upstream supertrait doctrine (CR-4 rebind → CR-EUNOMIA-COMPLEX) | ADR 0005 §Decision |
| Disjoint-scope rule (Atlas-meta doesn't touch inner-submodule source) | ADR 0011 §Decision §Leg 2 |

ADR 0008 fills the gap: between ADR 0007's tactical plan and ADR 0010's ceremony, what does the kwavers-math CsrScalar migration push look like as a concrete `[minor]` commit chain?

### Scope of the kwavers-math CsrScalar migration push

`kwavers-math` owns the math primitives consumed by `kwavers-solver`, `kwavers-physics`, `kwavers-gpu`. The `CsrScalar` surface is the complex-element type that the kwavers math kernels consume for sparse-CSR matrix operations (the core numerical workhorse for kwavers's seismic RTM/PSTD/elastic solvers per `D:/atlas/backlog.md` `## Migration batches ## Batch #1` consumer cone + `Batch #4 (kwavers PINN Burn → Coeus)`).

Per ADR 0006 §Decision, the SSOT rebind requires:

- `kwavers_math::CsrScalar` to consume `eunomia::ComplexField` (instead of the prior `let_ops::Complex<T>` ad-hoc f64-composition shim).
- The `num_complex::Complex<T>` call-site migration across `crates/kwavers-math/src/{complex_sparse, conjugate, hermitian, eigenvalues, fft}/**` and the corresponding `crates/kwavers-math/src/application/{linalg, sparse, special}/**`.
- `crates/kwavers-math/src/lib.rs` re-exports `eunomia::ComplexField` as the canonical complex supertrait.

Per ADR 0007 §Decision, the per-subcrate `[patch]` sweep adopts a sub-counter name pattern: `<crate-name>/atlas-migration-push/<patch-id>`. The kwavers-math push consumes a new sub-counter `<subcrate>/atlas-migration-push/csrscalar-migration` — distinct from the cross-Atlas migration batch reservations (`kwavers/atlas-migration-push/batch1` through `batch6`, which retain the bare-`batch{N}` shape per ADR 0010 §Per-batch name pattern).

Per ADR 0010 §Decision §"Tag pointer anchoring", the atomic inner commit lives in `kwavers` (this is the work product); the Atlas-parent submodule gitlink advance is the ceremony commit; docs-rounding + ADR-authoring commits are the SSOT-tracking pair.

## Decision

Author a `[minor]` kwavers-math CsrScalar migration push, with the following atomic commit chain:

### 1. Inner commit (the work product)

Single atomic commit in `repos/kwavers` on branch `codex/kwavers-math-csrscalar-migration` (or `feature/kwavers-math-csrscalar-migration` — branch name is peer-session owner's choice per the disjoint-scope rule from ADR 0011 §Decision §Leg 2):

```
refactor(kwavers-math)!: CsrScalar migration push (eunomia::ComplexField SSOT + leto_ops::CsrMatrix plumbing)

BREAKING CHANGE: kwavers_math::CsrScalar's complex-element type rebinds
from leto_ops::Complex<T>-shim to eunomia::ComplexField. New consumer
surface: T: eunomia::ComplexField.
```

Subject style follows conventional-commits BREAKING-CHANGE marker.

Stats expectation (illustrative; pre-merge exact stat TBD by peer-session):

- **Modified files**: 18-22 across `crates/kwavers-math/src/{complex_sparse, conjugate, hermitian, eigenvalues, fft}/**` + `crates/kwavers-math/src/application/{linalg, sparse, special}/**` + `crates/kwavers-math/src/lib.rs` + `crates/kwavers-math/Cargo.toml` + `crates/kwavers-math/CHANGELOG.md`.
- **Added files**: 0-2 (any new bindings to `eunomia::ComplexField` requiring typed wrappers — e.g., a `kwavers_math::complex::{CsrScalarExt, EigvalshExt}` convenience module).
- **Deletions dominated by the `let_ops::Complex<T>`-shim callsite collapse** (the `csr_mat_shim.rs` and `conjugate_shim.rs` intermediate files casualty list).

### 2. Inner tag

Annotated tag anchored on the inner commit per ADR 0010 §Decision §"Tag pointer anchoring — why the inner consumer commit":

```bash
git -C D:/atlas/repos/kwavers tag -a kwavers-math/atlas-migration-push/csrscalar-migration <inner-SHA> \
  -m "Atlas-provider migration push for kwavers-math CsrScalar limb of CR-EUNOMIA-COMPLEX.

Inner kwavers commit: <inner-SHA> on branch codex/kwavers-math-csrscalar-migration.
Per-subcrate [patch] sweep per ADR 0007 §Decision.
CsrScalar complex-element rebound from leto_ops::Complex<T>-shim to eunomia::ComplexField per ADR 0006 §Decision.
Upstream NumericElement supertrait (CR-4 closure consumed) per ADR 0005 §Decision.
Atlas-parent ceremony links: pointer advance + docs-rounding + ADR 0008 authoring (where this ADR 0008 authoring commit IS this repo's SSOT after tag).

See:
  - ADR 0005 (upstream NumericElement doctrine)
  - ADR 0006 (ComplexField doctrine consumed)
  - ADR 0007 (per-subcrate sweep tactical)
  - ADR 0008 (this tag's anchoring ADR)
  - ADR 0010 (Per-batch name pattern)
  - repos/kwavers/CHANGELOG.md ## Unreleased kwavers-math CsrScalar migration section"
git -C D:/atlas/repos/kwavers push origin codex/kwavers-math-csrscalar-migration --tags
```

Tag-name convention: `kwavers-math/atlas-migration-push/csrscalar-migration` — a sub-counter under the `kwavers` repo for subcrate-level patches. Distinct from the kwavers cross-Atlas migration batches #1-#4 (`kwavers/atlas-migration-push/batch1` + `batch4`) which retain the bare-`batch{N}` shape per ADR 0010 §"Per-batch name pattern".

### 3. Atlas-parent pointer advance (ceremony commit)

```bash
git -C D:/atlas add repos/kwavers
# verify staged gitlink SHA = <inner-SHA>
git -C D:/atlas commit -m "chore(atlas): Advance kwavers submodule pointer to <inner-SHA> (kwavers-math CsrScalar migration)"
```

### 4. Atlas-parent docs-rounding (SSOT-tracking commit)

```bash
# Modify 3 files: backlog.md (per-crate update under Batch #4 consumer cone); checklist.md (Per-batch reservations table row for the kwavers-math CsrScalar sub-counter); gap_audit.md (per-crate linkage update).
git -C D:/atlas add backlog.md checklist.md gap_audit.md
git -C D:/atlas commit -m "chore(atlas): Sync kwavers pointer <inner-SHA> + kwavers-math CsrScalar migration record"
```

### 5. Atlas-parent ADR 0008 status-bump commit (status: Proposed → Accepted)

Single atomic docs commit that flips ADR 0008's `Status:` line from `**Proposed**` to **`Accepted** — implementation closed 2026-07-06 (kwavers-math CsrScalar migration landed)` + updates the date to the closure date + updates `D:/atlas/docs/adr/INDEX.md` enumeration table to remove ADR 0008 from the Open Gaps entry + updates Realm-of-influence notes.

### 6. Tagged-push remote

```bash
git -C D:/atlas/repos/kwavers push origin codex/kwavers-math-csrscalar-migration --tags
```

### Scope file-line targets

| File | Migration action |
|------|------------------|
| `crates/kwavers-math/src/complex_sparse/{csr_mat, csr_view, spgemm}/*.rs` | `CsrScalar` complex-element plumbing to `eunomia::ComplexField` |
| `crates/kwavers-math/src/conjugate/*.rs` | `conjugate(s: CsrScalar) -> CsrScalar` plumbing |
| `crates/kwavers-math/src/hermitian/*.rs` | `is_hermitian(s: CsrScalar) -> bool` plumbing |
| `crates/kwavers-math/src/eigenvalues/*.rs` | `eigvalsh` + `eigvals` plumbing for complex Hermitian |
| `crates/kwavers-math/src/fft/{complex, hermitian}/*.rs` | `fft` + `ifft` for complex-valued input |
| `crates/kwavers-math/src/application/linalg/*.rs` | Linear algebra convenience fns threading `eunomia::ComplexField` |
| `crates/kwavers-math/src/application/sparse/*.rs` | Sparse matrix convenience fns (SpMV, SpMM, SpGEMM) |
| `crates/kwavers-math/src/application/special/*.rs` | Special-function plumbing (Bessel, log-gamma, etc. for complex domain) |
| `crates/kwavers-math/src/lib.rs` | Re-export `eunomia::ComplexField` as the canonical complex supertrait |
| `crates/kwavers-math/Cargo.toml` | Drop pre-eunomia `let_ops` complex shim dependency (if applicable); add `eunomia = { workspace = true }` (if not already present) |
| `crates/kwavers-math/CHANGELOG.md` | `## Unreleased kwavers-math CsrScalar migration` section enumerating the call-site migration + BREAKING CHANGE marker + cross-walk to ADR 0008 |

### Pass conditions

Pre-merge:

- `cargo nextest run -p kwavers-math` green (all `kwavers-math` unit + integration tests pass with the rebound CsrScalar surface).
- `cargo tree -p kwavers-math | grep let_ops` empty (post-shim-collapse).
- `cargo tree -p kwavers-math | grep eunomia` resolves to the `ComplexField`-providing version (post CR-4 closure).
- Differential tests: per-`kwavers-math::complex_sparse` unitary test inputs retain golden reference within single-precision epsilon; reference numerics from `crates/kwavers-math/src/complex_sparse/tests/csr_reference/` (peer-session verifies).

Post-merge:

- Atlas-parent pointer advance to `<inner-SHA>` lands.
- Tag `kwavers-math/atlas-migration-push/csrscalar-migration` resolves per ADR 0010 §Verification plan §1-§5.

## Alternatives considered

### Rejected Variant A — Fold the kwavers-math CsrScalar migration into ADR 0007 (treat kwavers-math as one row in the per-subcrate sweep table)

Pros: avoids the ADR-sequence numbering for kwavers-math; saves authorship effort.

Cons: ADR 0007's scope is the per-subcrate SWEEP STRATEGY, not the per-crate WORK SCOPE. Fold-in would crowd ADR 0007 with call-site details that belong to the kwavers CsrScalar limb specifically.

**Verdict**: separate ADR 0008 keeps the strategy/work split clean per AGENTS.md's `documentation_discipline`.

### Rejected Variant B — Skip the kwavers-math CsrScalar ADR; rely on `D:/atlas/backlog.md` `## Migration batches ## Batch #1` row's existing scope description

Pros: the row already mentions kwavers-math as part of the Batch #1 Rayon → Moirai sweep; the CsrScalar limb could be implied.

Cons: Batch #1 is the Rayon → Moirai scope; the CsrScalar migration push is a DIFFERENT scope (complex-element rebind, not parallel-iterator rebind). Conflating them in a single backlog row would lose the audit granularity.

**Verdict**: not portable; ADR 0008 separates the two work streams cleanly.

### Rejected Variant C — Re-tag the kwavers CsrScalar migration under the bare-`batchN` shape (`kwavers/atlas-migration-push/batch7`)

Pros: uniform with the cross-Atlas migration batch tags.

Cons: ADR 0010 §Per-batch name pattern reserves the bare-`batchN` shape for cross-Atlas migration batches. The kwavers-math CsrScalar migration is a per-subcrate `[patch]` (per ADR 0007's tactical-strategy decision); it should adopt the stronger sub-counter shape (`<subcrate-name>/atlas-migration-push/<patch-id>`) which distinguishes it from the migration batches. Bare-batch would falsely group with the migration-batch pegs and break `git tag -l '*/atlas-migration-push/*'` audit-clarity.

**Verdict**: sub-counter shape (`kwavers-math/atlas-migration-push/csrscalar-migration`) is the correct tag name per ADR 0010's per-batch name pattern + ADR 0007's per-subcrate sweep tactical.

## Failure modes / risks

- **Inner commit scope drift.** If the kwavers-math CsrScalar migration commit rolls in unrelated changes (e.g., `kwavers-gpu` GPU kernel fixes or `kwavers-solver` Rayon conversions), the inner commit loses audit granularity. **Mitigation**: peer-session owner + `git -C repos/kwavers diff --stat HEAD~1` pre-merge-vote gate; insist on CsrScalar-only diff or split into per-file commits.
- **Tag-name collision with future migration batches.** If a future codex session drafts a `kwavers-math/atlas-migration-push/csrscalar-migration-fixup` follow-up, the new tag's name should append a sub-counter suffix `(fixup)` or `(compat)` per ADR 0010 §Failure modes. **Mitigation**: follow ADR 0010's tag-naming discipline; surface a `variant-of` table in the kwavers-math project if sub-counters proliferate.
- **CR-EUNOMIA-COMPLEX PR gate falseness.** ADR 0006 is `Approved` (awaiting inner `acos/asin/atan` PR closure per ADR 0006 §Decision). If the kwavers-math CsrScalar migration push lands before the inner PR closes the ComplexField `zero()`/`one()` defaults, the kwavers-math push may itself need to land the ComplexField `zero()`/`one()` defaults (one-line impl additions to `eunomia::ComplexField` trait). **Mitigation**: pre-merge gate on `eunomia::ComplexField::default()` accessibility; if missing, block the inner commit + mandatorily land the eunomia-side impl update first (a `[patch]` minor eunomia commit may need to ride ahead of the kwavers-math push).
- **Upstream NumericElement supertrait drift.** If kwavers-math consumes `eunomia::NumericElement` supertrait (per ADR 0005) and any provider-side supertrait drift happens (via a separate codex session rebinding NumericElement), kwavers-math CsrScalar's plumbing might lose type inference or trait-bound. **Mitigation**: keep the kwavers-math CsrScalar commit minimal — use only the ComplexField surface-level trait, not the NumericElement supertrait hierarchy. If NumericElement drift happens post-merge, file a follow-up `[patch]` migration push.
- **Atlas-parent pointer advance on a stale snapshot.** If `git -C D:/atlas add repos/kwavers` happens before the inner kwavers commit `<inner-SHA>` reaches the local submodule's HEAD (e.g., different-machine push + slow `git fetch`), the pointer advance records the wrong SHA. **Mitigation**: per ADR 0010 §Failure modes, the convention is "inner commit first, then pointer-advance"; pre-flight `git -C repos/kwavers rev-parse HEAD` BEFORE `git -C D:/atlas add repos/kwavers` confirms the expected SHA.
- **Branch naming drift across repos.** The kwavers-math branch name `codex/kwavers-math-csrscalar-migration` is one of two conventions; some projects prefer `feature/<descriptor>` over `codex/<descriptor>`. **Mitigation**: peer-session owner picks one consistent convention per their project's CLAUDE.md or AGENTS.md; cross-walk `repos/kwavers/AGENTS.md` before cherry-pick.

## Verification plan

After the closure chain (steps 1-6 above) lands, the following commands verify:

1. **`git -C D:/atlas/repos/kwavers show-ref --tags kwavers-math/atlas-migration-push/csrscalar-migration`** — confirms the tag exists; expected output `<inner-SHA> refs/tags/kwavers-math/atlas-migration-push/csrscalar-migration`.
2. **`git -C D:/atlas/repos/kwavers show --no-patch --format='%H %s' kwavers-math/atlas-migration-push/csrscalar-migration`** — confirms tag annotation captures ADR 0005 + 0006 + 0007 + 0008 + 0010 references.
3. **`git -C D:/atlas/repos/kwavers cat-file -t kwavers-math/atlas-migration-push/csrscalar-migration`** — confirms annotated (not lightweight).
4. **`git -C D:/atlas/repos/kwavers rev-parse --abbrev-ref HEAD`** — must be `codex/kwavers-math-csrscalar-migration` (or whatever branch used) at tag-creation time.
5. **`git -C D:/atlas rev-parse HEAD`** — confirms Atlas-parent pointer advance landed; SHA-matches the docs-rounding commit.
6. **`git -C D:/atlas log --oneline -4`** — confirms the docs commit chain: inner pointer + docs-rounding + ADR 0008 status-bump.
7. **`git -C D:/atlas/repos/kwavers ls-remote --tags origin 'kwavers-math/atlas-migration-push/*'`** — confirms push-reachability; output line `<remote-SHA> refs/tags/kwavers-math/atlas-migration-push/csrscalar-migration`.
8. **`grep -c '^#### ' D:/atlas/backlog.md`** — should still return 6 (the §A/§B/§C/§D/§E + the parent h3 anchored under `## Out-of-scope (explicit)`); §-structure integrity preserved.
9. **`awk '/^## Per-batch/,/^## /' D:/atlas/checklist.md | grep -c 'batchN\\|<subcrate>'`** — should return 7 (6 existing rows + 1 new kwavers-math/CsrScalar sub-counter row).
10. **`git -C D:/atlas docs/adr/INDEX.md | head`** — confirms enumeration table now includes ADR 0008 row; Open Gaps for 0008 marked CLOSED 2026-07-06.

## Sequencing (this ADR's authorship + closure chain)

This ADR is authored in the **uncompleted-state** of the kwavers-math CsrScalar migration push: the decision is documented, but implementation is pending next codex-session authorship. The full closure chain (next codex session):

1. Inner kwavers-math CsrScalar migration commit (per §1 above).
2. Inner tag creation + push per §2.
3. Atlas-parent pointer advance per §3.
4. Atlas-parent docs-rounding per §4.
5. Atlas-parent ADR 0008 status-bump commit + cross-reference footer updates on ADR 0006/0007/0010 + `INDEX.md` enumeration-table update + Open Gaps update per §5.
6. Pre-flight verification per the 10-step plan above.

If steps 5's cross-reference footer updates on ADR 0006 / 0007 / 0010 are too ambitious for one commit, split into:

- 5a. ADR 0006 cross-reference footer update + ADR 0007 cross-reference footer update (one atomic commit).
- 5b. ADR 0010 cross-reference footer update (one atomic commit).
- 5c. ADR 0008 status-bump + `INDEX.md` enumeration-table update + Open Gaps update (one atomic commit).

## Out of scope (explicit non-goals)

- **The orthonormal eunomia::ComplexField per-subcrate `[patch]` sweep across `kwavers-solver` / `kwavers-physics` / `kwavers-gpu`** — those get separate per-subcrate `[patch]` ADRs (e.g., ADR 0008-N) once the kwavers-math CsrScalar migration lands and the pattern is established. ADR 0007 §Decision already commits to this tactical strategy.
- **The bare-`batchN` migration batch tags for kwavers-matrix-level work** — those remain ADR 0010's batch reservation pattern (e.g., `kwavers/atlas-migration-push/batch1` for Batch #1 Rayon → Moirai; this ADR's `<subcrate>/atlas-migration-push/<patch-id>` sub-counter pattern is distinct).
- **Migration of the upstream supertrait hierarchy** (NumericElement → ComplexField → CsrScalar) into other subcrates beyond kwavers-math — that's a downstream consumer-side decision; each downstream consumer (`kwavers-solver`, `kwavers-physics`, `CFDrs`, `ritk`) gets its own per-subcrate `[patch]` ADR tracking.
- **The atomic-implementation commit for kwavers-math CsrScalar migration itself** — this ADR documents the decision; the implementation lands in the next codex session's authorship per `D:/atlas/AGENTS.md` `interaction_policy` + `documentation_discipline` provisions (`[minor]` class default Proposed unless user sign-off).
- **Tag-name changes for any pre-existing kwavers/atlas-migration-push tags** — those retain their bare-`batchN` shape per ADR 0010 §Per-batch name pattern; the kwavers-math sub-counter is strictly additive.

## References

- **ADR 0005** — `D:/atlas/docs/adr/0005-eunomia-scalar-ssot.md` — the upstream `eunomia::NumericElement` supertrait doctrine (CR-4 closure consumed by CR-EUNOMIA-COMPLEX).
- **ADR 0006** — `D:/atlas/docs/adr/0006-eunomia-complex-csr-ssot.md` — the `eunomia::ComplexField` SSOT doctrine this push consumes.
- **ADR 0007** — `D:/atlas/docs/adr/0007-eunomia-solver-csr-ssot.md` — the per-subcrate `[patch]` sweep tactical strategy this push adopts.
- **ADR 0010** — `D:/atlas/docs/adr/0010-cfdrs-atlas-pointer-advance.md` — Per-batch name pattern + Atlas-parent pointer-advance ceremony + tag convention; the sub-counter `<subcrate>/atlas-migration-push/<patch-id>` shape is the per-subcrate specialization.
- **ADR 0011** — `D:/atlas/docs/adr/0011-atlas-root-hygiene-ritual.md` — Atlas-root working-tree hygiene ritual; disjoint-scope rule re-affirmed (`NO ATLAS-META RECLAIM` for any kwavers-internal source edits per §Decision §Leg 2).
- **ADR Index** — `D:/atlas/docs/adr/INDEX.md` — to be updated post-merge to mark ADR 0008 as Accepted (currently flagged as Open Gap with `Filename placeholder: D:/atlas/docs/adr/0008-kwavers-math-csrscalar-migration.md`; the Open Gaps entry reverts post-merge to "CLOSED 2026-07-06 (Proposed)").
- **`D:/atlas/backlog.md`** `## Cross-repo architect coordination ledger` CR-4 row + `## Migration batches ## Batch #1` (kwavers Rayon → Moirai) consumer cone + `## Batch #4 (kwavers PINN Burn → Coeus)` — the migration inventory.
- **`D:/atlas/checklist.md`** `## Per-batch Atlas-provider tag reservations` — the per-batch reservation SSOT (this ADR adds a new sub-counter row alongside the 6 existing rows: `kwavers-math/atlas-migration-push/csrscalar-migration` reserved-at 2026-07-06, closure status OPEN until the next codex-session authorship).
- **`D:/atlas/concurrent_agents`** contract — disjoint-scope rule (re-affirmed per ADR 0011); kwavers-claim-stream ownership of `repos/kwavers/**`.
- **PR 0007** — `D:/atlas/docs/pr/0007-helios-internal-dirty-cleanup-pr.md` — adjacent precedent for sub-counters (`helios/atlas-migration-push/internal-dirty-batch1`); ADR 0008's sub-counter convention inherits the same naming-perfective.
