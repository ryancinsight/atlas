# Atlas-meta ADR Index — doctrine navigation SSOT

> Purpose: future codex sessions discovering Atlas-meta doctrine SHALL start here. Each row points to the canonical ADR file with its current Status + Date + one-line summary + topic grouping; the cross-walk table makes Relates-to chains explicit; the navigation guidance maps common session-start scenarios to the right ADR pairs.
>
> This page is auto-anchored from `D:/atlas/AGENTS.md` `documentation_discipline` + `D:/atlas/backlog.md` `## Cross-repo architect coordination ledger` + `D:/atlas/checklist.md` `## Per-batch Atlas-provider tag reservations` + `D:/atlas/concurrent_agents` contract.

## Listing by ID (one-line summary + status)

| ID | One-line summary | Status | Date | Class | Driver(s) | Topic tag |
|----|------------------|--------|------|-------|-----------|-----------|
| **0001** | `hephaestus` stands up as standalone shared GPU/accelerator substrate for `apollo` + `coeus`, composing `cuda-oxide` + `cutile` for CUDA and `wgpu` for portable compute | Accepted | 2026-06-10 | `[arch]` | apollo / coeus | gpu-substrate |
| **0002** | `themis`/`mnemosyne`/`moirai`/`hephaestus`/`leto` own the heterogeneous compute topology (CPU/GPU/TPU over per-core caches / NUMA DRAM / HBM / GDDR / pinned host) | Accepted | 2026-06-11 | `[arch]` | atlas-wide | topology-law |
| **0003** | single-owner CUDA context + lock-free cross-process work queue + melinoe branded intra-process device sharing; eliminates the inter-process init race without an OS file lock | Proposed | 2026-06-16 | `[arch]` | moirai / melinoe / hephaestus (primary); themis / mnemosyne (supporting) | gpu-parallelization |
| **0004** | dialect-parameterized kernel-authoring seam (Wgsl + CudaC) for consumer-authored kernels over wgpu + CUDA; collapses 2.5–3.5k duplicated host-orchestration lines | Accepted | 2026-07-02 | `[arch]` | helios / kwavers / CFDrs | gpu-substrate |
| **0005** | `eunomia::NumericElement` as universal `Scalar` supertrait (CR-4 rebind); `coeus-core::Scalar` + `leto-ops::Scalar` rebase; supersedes prior RealField float-only supertrait | Accepted | 2026-07-04 | `[major]` | kwavers / CFDrs / ritk (consumers); coeus / leto / eunomia (providers) | numeric-ssot |
| **0006** | `eunomia::ComplexField` as `kwavers-math` `CsrScalar` SSOT (CR-EUNOMIA-COMPLEX); sets the per-batch `num_complex::Complex<T>` migration convention | Approved | 2026-07-05 | `[minor]` | kwavers-math | numeric-ssot |
| **0007** | per-subcrate `[patch]` sweep adopting ADR 0010's tag convention + closing `Complex<T>` call-sites per CR-EUNOMIA-COMPLEX; supersedes the per-crate CR-EUNOMIA-COMPLEX PR chain | Proposed | 2026-07-06 | `[minor]` | kwavers-solver / CFDrs / ritk | numeric-ssot |
| **0010** | Per-batch name pattern (`{consumer-repo}/atlas-migration-push/{batchN}`) + Atlas-parent pointer-advance + tag convention; closure-ritual counterpart for `D:/atlas/backlog.md` migration batches | Accepted | 2026-07-05 | `[minor]` | CFDrs (Batch #2 closure anchor); kwavers / ritk / apollo / moirai (future batches #1, #3, #5, #6) | atlas-ceremony |
| **0011** | Atlas-root working-tree hygiene ritual — delegate-cleanup-by-class + disjoint-scope + OOS-record cadence; superseded the implicit `backlog.md` OOS-record shape from commit `283f38cf` | Accepted | 2026-07-06 | `[arch]` | atlas-meta | atlas-ceremony |

The ADR sequence numbers carry semantic meaning: 0001-0004 are pre-Atlas-foundation doctrine (GPU substrate stack + heterogeneous topology); 0005-0007 are the CR-4 + CR-EUNOMIA-COMPLEX SSOT rebind chain; 0010-0011 are the Atlas-provider ceremony counterparts. 0008 + 0009 are missing — see **Open Gaps** below.

## Topic-keyword index

### Group A — GPU/accelerator substrate stack (`topic-tag: gpu-substrate`, `gpu-parallelization`)

Cross-cuts the shared substrate for GPU compute + dispatch surfaces + secure parallelization across processes. Affected crates (primary): `hephaestus`, `apollo`, `coeus`, `moirai`, `melinoe`, `mnemosyne`. Affected crates (supporting): `themis`, `kwavers`, `CFDrs`, `helios`, `ritk`.

- **ADR 0001** — `hephaestus` shared substrate (wgpu + CUDA via cuda-oxide + cutile). **Anchor for any GPU-substrate question.**
- **ADR 0004** — custom-kernel seam (consumer-authored kernels over wgpu + CUDA). **Anchor for any consumer-authored kernel work; unblocks helios fused affine-clamp.**
- **ADR 0003** — secure parallelization (single-owner device context + lock-free cross-process work submission + melinoe branded intra-process sharing). **Anchor for any moirai/MPSC work on the accelerator route.**

Cross-walks: 0004 is the seam follow-up ADR promised by 0001 (§Decision §"Open question — seam follow-up"); 0003 depends on 0001 for the substrate and crosses into 0002's topology law for the `SchedulerRoute::Accelerator` integration.

### Group B — Heterogeneous compute topology law (`topic-tag: topology-law`)

Cross-cuts the cross-repo ownership map for CPU/GPU/TPU execution over the memory hierarchy. Affects ALL substrates (consumers + providers).

- **ADR 0002** — `themis` (vocabulary) + `mnemosyne` (allocator + kernel resource budgets) + `moirai` (launch shaping + occupancy planner) + `hephaestus` (backends) + `leto` (CPU cache-aware tiling). **Anchor for any cross-repo ownership question.**

Adjacency: Group A (the substrate laws in 0001/0004 conform to 0002's ownership map); Group A's 0003 explicitly threads 0002's `GpuTopology` through the single-owner device context.

### Group C — Numeric SSOT (eunomia doctrine) (`topic-tag: numeric-ssot`)

Cross-cuts the eunomia scalar/complex rebinds that close CR-4 + CR-EUNOMIA-COMPLEX. Affected crates (primary): `coeus`, `leto`, `eunomia`, `kwavers`, `CFDrs`, `ritk`.

- **ADR 0005** — `eunomia::NumericElement` as universal `Scalar` supertrait (CR-4 rebind). **Anchor for any `coeus-core::Scalar` + `leto-ops::Scalar` work; the float-vs-int supertrait doctrine proof.**
- **ADR 0006** — `eunomia::ComplexField` as `kwavers-math` `CsrScalar` SSOT (CR-EUNOMIA-COMPLEX). Approved (awaiting inner-CR-EUNOMIA-COMPLEX PR closure).
- **ADR 0007** — per-subcrate `[patch]` sweep adopting ADR 0010's tag convention + closing `Complex<T>` call-sites per CR-EUNOMIA-COMPLEX. Proposed (awaiting user sign-off).

Cross-walks: 0006 builds on 0005's NumericElement doctrine (0005 proves `RealField` cannot be a universal supertrait, opening the door for `NumericElement`); 0007 inherits 0006's ComplexField doctrine + 0004's kernel-seam surface + 0010's Per-batch tag convention. All three depend on each other in sequence: 0005 → 0006 → 0007.

### Group D — Atlas-provider ceremony (cross-repo migration ritual) (`topic-tag: atlas-ceremony`)

Cross-cuts the per-batch + per-class delegate + disjoint-scope + OOS-record cadences for Atlas-meta. Affects Atlas-parent repo + every submodule-claim-stream per consumer repos.

- **ADR 0010** — Per-batch name pattern (`{consumer-repo}/atlas-migration-push/{batchN}`) + Atlas-parent pointer-advance + tag convention. **Anchor for the Atlas-provider migration push ceremony (Batch #1-#6 reservations).**
- **ADR 0011** — Atlas-root working-tree hygiene ritual (delegate-cleanup-by-class + disjoint-scope + OOS-record cadence). **Anchor for any `D:/atlas/backlog.md` `## Atlas-root working-tree dirty triage` subsection authoring.**

Cross-walks: 0011's disjoint-scope rule (§Decision §Leg 2) re-affirms 0010's "Atlas-parent is the ceremony repo" boundary; 0011's `## Out-of-scope (explicit)` cadence is the SSOT for any submodule-internal (`§C`) or Helios-internal (`§D`) OOS record. 0010's Per-batch name pattern is the inheritance convention that per-submodule cleanup events (e.g. `PR 0007`'s `helios/atlas-migration-push/internal-dirty-batch1` sub-counter) follow.

## Status flow legend

The ADR status flow is a 3-tier decision gradient per `D:/atlas/AGENTS.md` `documentation_discipline`:

- **`Accepted`** — doctrine in force; implementation closed (or in progress with explicit user sign-off per the `interaction_policy` autonomy-mode pattern: ADR 0004 user-sign-off 2026-07-02; ADR 0005 + 0010 user-autonomy per `interaction_policy`; ADR 0011 implementation closed 2026-07-06 per `0b60c3307` cleanup chore).
- **`Approved`** — doctrine adopted but pending closure artifact. ADR 0006 is in this tier: doctrine approved 2026-07-05; closure pending inner-CR-EUNOMIA-COMPLEX PR land (the `acos/asin/atan` block).
- **`Proposed`** — doctrine drafted but awaiting user sign-off. Examples: ADR 0003 awaiting user review of the staged single-owner device context + loom model-check retrofit (per §Staged plan stage 2); ADR 0007 awaiting user sign-off on the per-subcrate `[patch]` sweep schedule.

## Cross-walk table (Relates-to → ADR link)

| ADR | Relates to | Supersedes |
|-----|------------|------------|
| 0001 | (none — root of GPU-substrate group) | (none — root) |
| 0002 | 0001 (vocabulary conformance + backends) | (none) |
| 0003 | 0001 (substrate), 0002 (topology law) | (none — replaces OS file-lock brute-force with single-owner CAS) |
| 0004 | 0001 (Promise from ADR 0001 §"Open question — seam follow-up") | (none) |
| 0005 | 0010 (Atlas-provider ceremony chain — CR-4 closure consumes Batch #2), 0006 (next-step), 0007 (next-step) | inline CR-4 draft in `D:/atlas/backlog.md` |
| 0006 | 0005 (NumericElement doctrine), 0004 (kwavers-math ∈ adapter layer), 0001 (CUDA backend lives in hephaestus) | (none) |
| 0007 | 0006 (ComplexField doctrine), 0005 (NumericElement foundation), 0004 (kernel-seam), 0010 (per-batch tag convention) | (none — first per-subcrate `[patch]` sweep) |
| 0010 | 0005 (consumed by Batch #2 closure), 0006 (next-batch adoption), 0007 (per-`[patch]` sweep reuses), 0011 (ceremony counterpart) | inline `D:/atlas/backlog.md` ritual without ADR anchor |
| 0011 | 0005, 0006, 0007 (numeric SSOT chain hygiene), 0010 (Per-batch convention) | inline `D:/atlas/backlog.md` OOS-record shape (first introduced by commit `283f38cf`); implicit cadence carried only in the commit narrative pre-ADR-0011 |

## Open gaps

- **ADR 0008 missing** — no ADR captures the `kwavers-math` `CsrScalar` migration push's per-crate sweep as a separate documented decision. Filename placeholder: `D:/atlas/docs/adr/0008-kwavers-math-csrscalar-migration.md`. Recommend authoring as `[minor]` if a kwavers-math owner surfaces a need.
- **ADR 0009 missing** — no ADR captures the Cadence-Tactic-Exercise (CTE) on Batch #1 (`kwavers-solver` / `kwavers-physics` Rayon → Moirai) as a roll-forward decision. Filename placeholder: `D:/atlas/docs/adr/0009-batch1-rayon-to-moirai-cte.md`. Recommend authoring when kwavers Batch #1 closes (gate: paragraph-collapse on the 107 residual `ndarray::Zip::*` sites per `D:/atlas/backlog.md` ## In-flight claims).
- The 0008 + 0009 gaps are minor (each is a small `[minor]` `[patch]` doc-only artifact); they are not blockers but they break the numeric-sequence convention. Recommend closing in 2026 Q3 sprint 1.x.x.x hotfix pre-pull-request to round out the ADR sequence.

## Navigation guidance (session-start recipes)

Map common codex-session scenarios to the ADR pairs (or triples) you should read BEFORE making any commit:

- **New codex session starting Atlas-meta work**: read `D:/atlas/AGENTS.md` `documentation_discipline` + this INDEX.md + jump into the specific group's ADRs by topic (Groups A/B/C/D above).
- **Implementing an Atlas-provider migration batch** (e.g. a new `atlas-migration-push/batchN`): read **ADR 0010** (Per-batch + tag convention) + **ADR 0011** (hygiene + disjoint-scope) BEFORE any commit work. Cross-walk `D:/atlas/checklist.md` `## Per-batch Atlas-provider tag reservations` for the active row.
- **Closing a sub-tree dirty (`§C` Path C retroactive-closed)** in `D:/atlas/backlog.md` `## Out-of-scope (explicit) ## Atlas-root working-tree dirty triage` (e.g. CFDrs / hephaestus / mnemosyne / themis retro-closed per the 2026-07-06 triage turn): follow **ADR 0011** §Decision §Leg 3 OOS-record cadence sub-routine "Resolution branch" + "Post-resolution §-E update" before writing the chore commit.
- **Implementing a numeric SSOT rebind** to `coeus_core::Scalar` / `leto_ops::Scalar` / `kwavers_math::CsrScalar` / `ritk::*`: read **ADR 0005** (NumericElement doctrine) + **ADR 0006** (ComplexField) + **ADR 0007** (Complex<T>) BEFORE any `coeus`/`kwavers`/`ritk` source edit.
- **Working on GPU/accelerator substrate** (any consumer-authored kernel, dispatcher, device seam, or secure-parallelization question): read **ADR 0001** + **ADR 0002** + **ADR 0004** BEFORE any `hephaestus`/`apollo`/`coeus` GPU work. If the work crosses process boundaries, also read **ADR 0003**.
- **Working on a per-submodule inner-cleanup event** (e.g. the PR 0007 `helios/atlas-migration-push/internal-dirty-batch1` sub-counter): follow **ADR 0010** §Per-batch name pattern (adopt the `{consumer-repo}/atlas-migration-push/{batch-id}` shape) + **ADR 0011** §Decision §Leg 2 disjoint-scope rule (NO ATLAS-META RECLAIM).
- **Verifying an Atlas-provider migration push** (a tagged batch + pointer-advance + docs-rounding commit chain): cross-walk **ADR 0010** §Verification plan + **ADR 0011** §Decision §Leg 2 disjoint-scope rule.

## References

- **`D:/atlas/AGENTS.md`** `documentation_discipline` — SSOT rules for PM artifacts; the rule that makes this INDEX.md authoritative for Atlas-meta doctrine navigation.
- **`D:/atlas/concurrent_agents`** contract — disjoint-scope rule (re-affirmed by ADR 0011 §Decision §Leg 2); consumer-claim-stream ownership rule (cited by ADR 0010 §Decision §Tag pointer anchoring).
- **`D:/atlas/backlog.md`** `## Cross-repo architect coordination ledger` — the CR-class inventory that motivates ADR 0005 (CR-4) + ADR 0006 (CR-EUNOMIA-COMPLEX). **Also**: `## Migration batches (vertical slices) ## Token batch ordering` — the batch-ordering SSOT that ADR 0010's Per-batch tag convention references.
- **`D:/atlas/checklist.md`** `## Per-batch Atlas-provider tag reservations` — the per-batch reservation SSOT (cross-walks ADR 0010's Per-batch name pattern; 6 reserved rows as of 2026-07-06: kwavers/batch1, cfdrs/batch2 [CLOSED], ritk/batch3, kwavers/batch4, apollo/batch5, cfd-core+ritk-core+moirai/batch6).
- **`D:/atlas/docs/audit/`** — the audit trail that motivates the doctrine in ADR 0001 (substrate audit at `2026-07-02-hephaestus-gpu-substrate-audit.md`); cross-repo coordination at `2026-07-02-cross-repo-integration-audit.md`; mnemosyne topology at `2026-06-27-mnemosyne-*` + `2026-07-01-mnemosyne-soundness-perf-audit.md`; kwavers-CFDrs-ritk atlas-migration at `2026-07-05-kwavers-cfdrs-ritk-atlas-migration-audit.md`.
- **`D:/atlas/docs/pr/`** — the PR-equivalent plan templates that inherit ADR 0010's Per-batch convention (e.g. `0007-helios-internal-dirty-cleanup-pr.md` uses the `helios/atlas-migration-push/internal-dirty-batch1` sub-counter; future PR 0008+ inherit the same convention).
- **`D:/atlas/scripts/`** `build-all.sh` / `build-all.ps1` — the Workspace top-level builds that let any consumer-repo edit (per ADR 0011's disjoint-scope) be cross-validated at the Atlas-meta layer through `cargo nextest run -p <consumer>`.
