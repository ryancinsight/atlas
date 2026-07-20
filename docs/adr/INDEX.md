# Atlas-meta ADR Index — doctrine navigation SSOT

> Purpose: future codex sessions discovering Atlas-meta doctrine SHALL start here. Each row points to the canonical ADR file with its current Status + Date + one-line summary + topic grouping; the cross-walk table makes Relates-to chains explicit; the navigation guidance maps common session-start scenarios to the right ADR pairs.
>
> This page is auto-anchored from `D:/atlas/AGENTS.md` `documentation_discipline` + `D:/atlas/backlog.md` `## Cross-repo architect coordination ledger` + `D:/atlas/checklist.md` `## Per-batch Atlas-provider tag reservations` + `D:/atlas/concurrent_agents` contract.

## Listing by ID (one-line summary + status)

| ID | One-line summary | Status | Date | Class | Driver(s) | Topic tag |
|----|------------------|--------|------|-------|-----------|-----------|
| <a id="ADR-0001"></a>**0001** | `hephaestus` stands up as standalone shared GPU/accelerator substrate for `apollo` + `coeus`, composing `cuda-oxide` + `cutile` for CUDA and `wgpu` for portable compute | Accepted | 2026-06-10 | `[arch]` | apollo / coeus | gpu-substrate |
| <a id="ADR-0002"></a>**0002** | `themis`/`mnemosyne`/`moirai`/`hephaestus`/`leto` own the heterogeneous compute topology (CPU/GPU/TPU over per-core caches / NUMA DRAM / HBM / GDDR / pinned host) | Accepted | 2026-06-11 | `[arch]` | atlas-wide | topology-law |
| <a id="ADR-0003"></a>**0003** | single-owner CUDA context + lock-free cross-process work queue + melinoe branded intra-process device sharing; eliminates the inter-process init race without an OS file lock | Proposed | 2026-06-16 | `[arch]` | moirai / melinoe / hephaestus (primary); themis / mnemosyne (supporting) | gpu-parallelization |
| <a id="ADR-0004"></a>**0004** | dialect-parameterized kernel-authoring seam (Wgsl + CudaC) for consumer-authored kernels over wgpu + CUDA; collapses 2.5–3.5k duplicated host-orchestration lines | Accepted | 2026-07-02 | `[arch]` | helios / kwavers / CFDrs | gpu-substrate |
| <a id="ADR-0005"></a>**0005** | `eunomia::NumericElement` as universal `Scalar` supertrait (CR-4 rebind); `coeus-core::Scalar` + `leto-ops::Scalar` rebase; supersedes prior RealField float-only supertrait | Accepted | 2026-07-04 | `[major]` | kwavers / CFDrs / ritk (consumers); coeus / leto / eunomia (providers) | numeric-ssot |
| <a id="ADR-0006"></a>**0006** | `eunomia::ComplexField` as `kwavers-math` `CsrScalar` SSOT (CR-EUNOMIA-COMPLEX); sets the per-batch `num_complex::Complex<T>` migration convention | Approved | 2026-07-05 | `[minor]` | kwavers-math | numeric-ssot |
| <a id="ADR-0007"></a>**0007** | per-subcrate `[patch]` sweep adopting ADR 0010's tag convention + closing `Complex<T>` call-sites per CR-EUNOMIA-COMPLEX; supersedes the per-crate CR-EUNOMIA-COMPLEX PR chain | Proposed | 2026-07-06 | `[minor]` | kwavers-solver / CFDrs / ritk | numeric-ssot |
| <a id="ADR-0008"></a>**0008** | kwavers-math CsrScalar migration push (per-subcrate `[minor]`) — adopts ADR 0006 ComplexField doctrine (Path B: additive `ComplexField::zero()`/`::one()` defaults) + ADR 0007 per-subcrate `[patch]` sweep + ADR 0010 `<subcrate>/atlas-migration-push/<patch-id>` sub-counter tag convention; reserves `kwavers-math/atlas-migration-push/csrscalar-migration`; **Phase-1A pre-landed via peer commit `1dc47028a` (2026-07-05 22:16)**; **Phase-1B eunomia-side ALREADY landed at HEAD `57d7789` per ADR 0006 Path B (verified 2026-07-06; cross-walk `D:/atlas/docs/coordination/2026-07-06-eunomia-csr-scalar-phantom-blocker.md`); residual Phase-1B is kwavers-side (`csr.rs` `CsrScalar: Zero` → `CsrScalar: ComplexField` swap + `kwavers-boundary` `num_complex::Complex64` → `eunomia::Complex64` migration across 8 files / 9 sites + manifest cleanup) — owned by kwavers claim stream per disjoint-scope (ADR 0011 §Leg 2)** | Proposed | 2026-07-06 (reframed 2026-07-06 per phantom-blocker discovery) | `[minor]` | kwavers-math (consumes `eunomia::ComplexField`); kwavers-solver / kwavers-physics / kwavers-gpu (downstream consumers); **eunomia (Phase-1B gate holder — CLOSED retroactively at HEAD `57d7789` per ADR 0006 Path B); kwavers (residual Phase-1B owner)** | numeric-ssot |
| <a id="ADR-0009"></a>**0009** | Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai) Cadence-Tactic-Exercise (CTE) — 107 residual `ndarray::Zip::*` sites across 40 files (31 in kwavers-solver, 9 in kwavers-physics) + 3 Cargo.toml `ndarray` `rayon` feature strips (root + solver + physics); paragraph-collapse closure gate (8-step); reserves `kwavers/atlas-migration-push/batch1` per ADR 0010 | Proposed | 2026-07-06 | `[patch]` | kwavers-solver (31 files, est ~50 sites) + kwavers-physics (9 files, est ~7 sites) + 5 helper files (est ~50 helper call-sites) | atlas-ceremony |
| <a id="ADR-0010"></a>**0010** | Per-batch name pattern (`{consumer-repo}/atlas-migration-push/{batchN}`) + Atlas-parent pointer-advance + tag convention; closure-ritual counterpart for `D:/atlas/backlog.md` migration batches | Accepted | 2026-07-05 | `[minor]` | CFDrs (Batch #2 closure anchor); kwavers / ritk / apollo / moirai (future batches #1, #3, #5, #6) | atlas-ceremony |
| <a id="ADR-0011"></a>**0011** | Atlas-root working-tree hygiene ritual — delegate-cleanup-by-class + disjoint-scope + OOS-record cadence; superseded the implicit `backlog.md` OOS-record shape from commit `283f38cf` | Accepted | 2026-07-06 | `[arch]` | atlas-meta | atlas-ceremony |
| <a id="ADR-0014"></a>**0014** | `kwavers` Batch #1 closeout-tag ceremony (`kwavers/atlas-migration-push/batch1` + KW-CV-001 watchpoint retirement) — flips Batch #1 status from `slice-by-slice partial closure` (ADR 0013 state) to `full closure`; bundles 3 atomic items owned by disjoint scopes (item (a) 1,315-file mechanical drift flush commit on kwavers peer stream; item (b) slice 7 `is_standard_layout` predicate unification commit eliminating the slice 7 `is_c_contiguous` vs slice 6b/8/9 `is_standard_layout` category-mismatch on kwavers peer stream; item (kwavers closeout) closeout-style commit matching the KW-CV-001 watchpoint regex `closeout\|close-batch` on kwavers peer stream); item (c) atlas-meta chore commit advances `repos/kwavers` parent-tree gitlink + retires KW-CV-001 watchpoint from `atlas/backlog.md` §In-flight claims per disjoint-scope (ADR 0011 §Leg 2) | **Proposed** (Status flips to `Accepted` once kwavers peer stream emits items (a)+(b)+closeout-style commit AND item (c) atlas-meta pointer-advance chore commit retires KW-CV-001) | 2026-07-09 | `[patch]` | kwavers peer stream (items a+b+closeout) + atlas-meta (item c pointer advance + watchpoint retirement) | atlas-ceremony |
| <a id="ADR-0015"></a>**0015** | `kwavers-solver` Batch #2 Entry Point #1 — `kwavers_safety::with_zip_standard_layout` const-generics arity extension for N=6/7/8/9 immuts; refines ADR 0013 Entry Point #1 narrative with a const-generics implementation contract (rejecting macro/HRTB/variadic alternatives); acceptance criteria AC-1 through AC-6 (Block #5 gate cleared + helper extension commit + slice 6b backport fixture + 6/6 westervelt_spectral tests bitwise-identical + helper-stress feature rc=0 + slice 6b in-place adoption); implementation commits live on `repos/kwavers` peer stream per disjoint-scope (ADR 0011 §Leg 2) — atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` edits | **Proposed** (Status flips to `Accepted` once AC-1 through AC-6 are all ✅ on the kwavers peer stream post-Block-#5-resolution) | 2026-07-09 | `[minor]` | kwavers peer stream (helper extension commit + slice 6b backport fixture + slice 6b in-place adoption) | numeric-ssot |
| <a id="ADR-0016"></a>**0016** | `kwavers-math` Block #5 (Phase-3/Phase-4 ndarray → leto) resolution design-spec — 3-commit atomic decomposition (Sub-batch 1 strict-additive local `kwavers-transducer` fixes [E0308/E0599/arc.rs syntax + matmul free-function migration + Result.assign migration]; Sub-batch 2 strict-signature migration workspace-wide `Array2::from_shape_vec` tuple→array across 8 crates [kwavers-python, solver, analysis, transducer, receiver, boundary, source, grid]; Sub-batch 3 strict gate-validation regression assertion); rejects 1-monolithic / 4+per-crate / ndarray-compat-suppress / Phase-3-rollback alternatives; verification AC-1 through AC-5 (kwavers-transducer rc=0 + workspace-wide `Array2::from_shape_vec` tuple-form count = 0 + `cargo check -p kwavers-solver --lib --no-default-features` rc=0 + 6/6 westervelt_spectral bitwise vs slice 9 `949e5a39` + no false-positive KW-CV-001 watchpoint trigger); commits live on `repos/kwavers` peer stream per disjoint-scope (ADR 0011 §Leg 2) — atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` edits | **Proposed** (Status flips to `Accepted` once AC-1 through AC-5 are all ✅ post-3-commit Block #5 closure; simultaneously unblocks ADR 0015 AC-1) | 2026-07-09 | `[minor]` | kwavers peer stream (3-commit Block #5 resolution on `codex/kwavers-core-moirai-parallel`) | atlas-ceremony |
| <a id="ADR-0013"></a>**0013** | `kwavers` Batch #1 source-side closure (Zip-migration final state across slices 1-9) — 9 source files migrated, ~121 layout/length precondition asserts (`is_standard_layout` + `is_c_contiguous` + `debug_assert_eq`), 3 distinct helper-rejection shapes (slices 6b/7/8 + slice 9 Pattern A generalization), Batch #2 entry points reserved (Entry Point #1 N>5 closure-captured immuts ergonomics; #2 conditional-read closure bodies; #3 multi-mut disjoint-field sites); carries 4 + 1 carried-forward blockers (post-slice-9 `kwavers-math` Phase-3/Phase-4 ndarray → leto migration breakage explicitly gates Batch #2 start) | Accepted | 2026-07-09 | `[patch]` | kwavers-solver (9 files migrated across slice-by-slice cadence per ADR 0009) | atlas-ceremony |
| <a id="ADR-0019"></a>**0019** | TREE-DUP-002: Dual channel consolidation — fold `unified_channel` into `channel/` module, extend `Channel<T>` trait with batching/close/stats, merge error types, migrate sole consumer `moirai-iter` | Accepted | 2026-07-16 | `[major]` | moirai-core | module-hierarchy |
| <a id="ADR-0020"></a>**0020** | Refresh Atlas provider heads and record the exact provider-graph closure theorem | Accepted | 2026-07-17 | `[arch]` | atlas-meta / kwavers | provider-graph |
| <a id="ADR-0021"></a>**0021** | Promote Aequitas from roadmap candidate to the public physical-quantity and dimensional-law foundation | Accepted | 2026-07-19 | `[arch]` | aequitas / kwavers / atlas-meta | quantity-law |
| <a id="ADR-0022"></a>**0022** | Promote Horae time-integration policy over Aequitas and Athena Krylov policy over Leto CPU plus Hephaestus WGPU after deleting Leto's duplicate CG and GMRES recurrences | Accepted | 2026-07-19 | `[arch]` `[minor]` | horae / athena / leto / hephaestus / atlas-meta | simulation-providers |
| <a id="ADR-0023"></a>**0023** | Promote Harmonia partitioned multiphysics coupling over Horae subcycle plans and Athena Core convergence policy | Accepted | 2026-07-20 | `[arch]` `[minor]` | harmonia / horae / athena-core / eunomia / atlas-meta | simulation-providers |
| <a id="ADR-0024"></a>**0024** | Centralize Criterion base/head regression classification in one Atlas-owned Rust gate | Accepted | 2026-07-20 | `[arch]` `[patch]` | atlas-meta / apollo / helios / kwavers | benchmark-verification |
| <a id="ADR-0025"></a>**0025** | Promote Proteus as the Atlas owner for shared material-property and constitutive-law contracts: validated thermophysical newtypes (`MassDensity`, `SpecificHeatCapacity`, `ThermalConductivity`) over Aequitas quantities and Eunomia scalars with a GAT-based static constitutive seam (`ConstitutiveLaw<Law>`, `ConstantLaw`, `NoState`) and `Cow<str>` material identity | Accepted | 2026-07-20 | `[arch]` `[minor]` | proteus / aequitas / eunomia / atlas-meta | material-and-vocabulary |
| <a id="ADR-0026"></a>**0026** | Promote Tyche as the Atlas owner for reproducible uncertainty studies: counter-stream random-access Latin hypercube designs, index-addressed ensemble execution, online Welford/Chan moments, Pearson screening, finite-sample split-conformal calibration, and Moirai/Consus provider adapters over a `no_std + alloc` core with GAT response seams and const-generic numeric widths | Accepted | 2026-07-20 | `[arch]` `[minor]` | tyche / tyche-core / moirai / consus / eunomia / atlas-meta | uncertainty-quantification |
| <a id="ADR-0027"></a>**0027** | Resolve consumer path dependencies from one exact Atlas gitlink graph through an Atlas-owned Rust action | Accepted | 2026-07-20 | `[arch]` `[patch]` | atlas-meta / helios / kwavers / ritk | provider-graph |
| <a id="ADR-0028"></a>**0028** | Promote Asclepius as the owner for typed gEUD, TCP, NTCP, CEM43, Arrhenius damage, and independent-response composition over Aequitas and Eunomia, with a one-way Coeus autodiff adapter | Accepted | 2026-07-20 | `[arch]` `[minor]` | asclepius / asclepius-coeus / helios / kwavers / atlas-meta | biological-response |

The ADR sequence numbers carry semantic meaning: 0001-0004 are pre-Atlas-foundation doctrine (GPU substrate stack + heterogeneous topology); 0005-0008 are the CR-4 + CR-EUNOMIA-COMPLEX SSOT rebind chain; ADR 0009 is the Batch #1 Cadence-Tactic-Exercise `[patch]` roll-forward; 0010-0011 are the Atlas-provider ceremony counterparts; 0017-0028 record subsequent provider, hierarchy, graph, quantity-law, simulation-provider, coupling-promotion, verification, material-property, uncertainty-quantification, provider-checkout, and biological-response decisions. The index now carries the authored sequence through ADR 0028.

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

### Group E — Benchmark verification (`topic-tag: benchmark-verification`)

Cross-cuts statistical performance regression classification in Atlas
consumers.

- **ADR 0024** — one Atlas-owned Criterion confidence-interval gate with
  phase-reversed counterbalanced replication, family-wise error control, and
  exact-revision consumer pins. **Anchor for Apollo, Helios, and Kwavers
  benchmark-regression CI.**

### Group F — Material-property and UQ vocabulary providers (`topic-tag: material-and-vocabulary`, `uncertainty-quantification`)

Cross-cuts material-property and reproducible-study vocabulary that recurs
across CFDrs, Kwavers, and Helios. Affected crates (primary): `proteus`,
`tyche`, `tyche-core`. Affected crates (supporting): `aequitas`, `eunomia`,
`moirai` (Tyche execution adapter), `consus` (Tyche persistence adapter).

- **ADR 0025** — `proteus` shared material-property and constitutive-law
  contracts over Aequitas quantities and Eunomia scalars. **Anchor for any
  thermophysical material-property question.**
- **ADR 0026** — `tyche` reproducible uncertainty studies: random-access
  Latin hypercube, ensemble moments, calibration, Moirai/Consus adapters.
  **Anchor for any sampling / ensemble / sensitivity / conformal-calibration
  question.**

Cross-walks: 0025 composes 0005 (Eunomia scalar law) and 0021 (Aequitas
quantity law) without re-owning either; 0026 composes 0005 (Eunomia scalar
contract) and lifts 0023 (Harmonia) partitioned models and 0025 (Proteus)
material parameters as study inputs without crossing ownership
boundaries.

### Group G — Provider graph (`topic-tag: provider-graph`)

Cross-cuts reproducible sibling path-dependency materialization.

- **ADR 0020** — the Atlas gitlink graph is the exact provider revision SSOT.
- **ADR 0027** — one Atlas-owned Rust action resolves consumer manifests
  against that graph. **Anchor for Helios, Kwavers, and RITK CI checkout.**

### Group H — Biological response (`topic-tag: biological-response`)

Cross-cuts response laws shared by radiation-therapy and therapeutic-ultrasound
consumers. Affected crates (primary): `asclepius`, `asclepius-coeus`,
`helios-analysis`, and `kwavers-physics`. Affected providers (supporting):
`aequitas`, `eunomia`, and `coeus`.

- **ADR 0028** — `asclepius` typed gEUD, TCP, NTCP, CEM43, Arrhenius damage,
  and independent-insult composition, plus the outward Coeus gEUD adapter.
  **Anchor for biological-response ownership and migration.**

Cross-walks: 0028 composes 0005 (Eunomia scalar law), 0021 (Aequitas quantity
law), 0020/0027 (exact provider graph and checkout), and remains complementary
to 0025 (Proteus material properties).

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
| <a id="ADR-0017"></a>**0017** | `moirai-iter` NUMA path integrity redesign — delete `numa.rs` (4 HARD violations: dead `NumaPolicy`, raw `mmap`+`mbind` in iterator crate, sequential fake-parallel batch functions, fake `async fn` with discarded errors); redirect consumers to Themis (placement), Mnemosyne (allocation), Moirai executor (work-stealing) | Accepted | 2026-07-15 | `[major]` | moirai (provider); atlas-meta (ADR) | topology-law |
| <a id="ADR-0018"></a>**0018** | TREE-SRP-001: Melinoe/Themis/Moirai module hierarchy cleanup — split 4 files exceeding 500-line target; rehome themis tests from `src/` to `tests/` (partial: dead GPU/TPU files deleted, CPU/branded deferred on visibility); split `moirai-core/constants.rs` junk drawer; defer dual-channel consolidation (filed as TREE-DUP-002) | Accepted | 2026-07-15 | `[arch]` | melinoe/halo, themis, moirai-core | module-hierarchy |
| <a id="ADR-0019"></a>**0019** | TREE-DUP-002: Dual channel consolidation — fold `unified_channel` into `channel/` module, extend `Channel<T>` trait with batching/close/stats, merge error types, migrate sole consumer `moirai-iter` | Accepted | 2026-07-16 | `[major]` | moirai-core | module-hierarchy |
| 0020 | 0011 (Atlas-root hygiene) + 0001 (provider ownership) | (none) |
| 0021 | 0005 (Eunomia numeric SSOT) + 0020 (provider graph) | Aequitas ADR 0001; Kwavers ADR 040 |
| 0022 | 0001/0004 (Hephaestus GPU substrate and kernel seam) + 0005 (Eunomia scalar law) + 0021 (Aequitas quantity law) | Horae ADR 0001; Athena ADRs 0001-0002; Leto ADRs 0014-0015 record the completed solver extractions |
| 0023 | 0002 (topology law — Coupling role) + 0021 (Aequitas quantity law — dev-dep fixture only) + 0022 (Horae and Athena Core providers composed, not re-owned) | Harmonia ADR 0001 |
| 0024 | 0010 (cross-repo cadence) + 0011 (Atlas-meta ownership and consumer delivery) | copied Apollo, Helios, and Kwavers Python classifiers |
| 0025 | 0002 (bounded material-property role in topology law) + 0005 (Eunomia scalar contract) + 0021 (Aequitas quantity law — property newtypes transparent over Aequitas quantities) + 0023 (Harmonia coupling, complementary boundary) | Proteus ADR 0001 |
| 0026 | 0002 (bounded UQ role in topology law) + 0005 (Eunomia scalar contract) + 0023 (Harmonia — Tyche studies can wrap a partitioned model) + 0025 (Proteus — Tyche can sweep Proteus material parameters) | Tyche ADR 0001 |
| 0027 | 0020 (exact provider graph) + 0010 (cross-repo cadence) + 0011 (Atlas-meta ownership) | consumer-owned provider checkout actions and moving Atlas branch resolution |
| 0028 | 0005 (Eunomia scalar law) + 0020 (exact provider graph) + 0021 (Aequitas quantity law) + 0025 (complementary material-property boundary) + 0027 (provider checkout) | Asclepius ADR 0001; duplicated Helios and Kwavers response formulas |
| 0010 | 0005 (consumed by Batch #2 closure), 0006 (next-batch adoption), 0007 (per-`[patch]` sweep reuses), 0011 (ceremony counterpart) | inline `D:/atlas/backlog.md` ritual without ADR anchor |
| 0011 | 0005, 0006, 0007 (numeric SSOT chain hygiene), 0010 (Per-batch convention) | inline `D:/atlas/backlog.md` OOS-record shape (first introduced by commit `283f38cf`); implicit cadence carried only in the commit narrative pre-ADR-0011 |

## Atlas-provider ceremony inventory

Cross-repo Atlas-provider migrations that lift or wire shared infrastructure across multiple repos, beyond the per-ADR doctrine. The 6-repo SSOT enforcement surface (per-repo migration-audit gate, listed below) is the first artifact of this category. Cross-walk: `D:/atlas/gap_audit.md` `## SSOT enforcement surface (per-repo migration-audit gate)` for the canonical 6-repo table + per-inner-SHA anchors + recently-closed micro-commit record.

| Ceremony anchor | Description | Cross-repo coverage | Active inner-SHA anchors | Status |
|-----------------|-------------|---------------------|--------------------------|--------|
| `kwavers-Atlas-migration-push` (gate-lift leg, 2026-07-07) | Lift the native `xtask` migration-audit gate to all 6 SSOT-bearing repos under a uniform `.github/workflows/legacy-migration-audit.yml` workflow file. The 3 original repos (cfdrs / ritk / kwavers) carry an established `xtask` workspace member; the 3 added repos (apollo / gaia / helios) are wired this turn — apollo receives a workflow-only addition (`xtask` already exposes `provider-audit`); gaia and helios receive fresh `xtask` scaffolds mirrored verbatim from `cfdrs/xtask` (Cargo.toml + clap-derive src/main.rs + src/migration_audit.rs BTreeSet-diff scanner + header-only xtask/legacy_surface.allowlist baseline). | cfdrs / ritk / kwavers / apollo / gaia / helios | apollo `9df5294e + 2940d66 + cd05eac`; gaia `6a7b7d0 + d47d8a6`; helios `8a6637b + 065bf39` | **LIFTED 2026-07-07** — workflow YAML schema-valid on all 6 repos; inner-SHAs anchored above; day-1 green-banner deferred to first CI-run |

Cross-walk candidates (from ADR 0010 `## Per-batch name pattern`): each per-batch inner-repo tag (`{consumer-repo}/atlas-migration-push/{batchN}`) implicitly raises the per-repo gate (each tag-advance commit is itself a refresh + sweep candidate). The ceremony inventory is the cross-ceremony registry; the per-batch tag reservations are the per-batch anchor record.

**Governed by**: **ADR 0010** (§Per-batch name pattern governs per-repo anchor reservations) + **ADR 0011** (§Decision §Leg 2 disjoint-scope rule governs the docs-only scope of this inventory — atlas-meta touches ONLY workspace-root + docs/ files for these ceremonies; the per-repo chore commits live in the inner-repo claim streams).

## Navigation guidance (session-start recipes)

Map common codex-session scenarios to the ADR pairs (or triples) you should read BEFORE making any commit:

- **New codex session starting Atlas-meta work**: read `D:/atlas/AGENTS.md` `documentation_discipline` + this INDEX.md + jump into the specific group's ADRs by topic (Groups A/B/C/D above).
- **Implementing an Atlas-provider migration batch** (e.g. a new `atlas-migration-push/batchN`): read **ADR 0010** (Per-batch + tag convention) + **ADR 0011** (hygiene + disjoint-scope) BEFORE any commit work. Cross-walk `D:/atlas/checklist.md` `## Per-batch Atlas-provider tag reservations` for the active row.
- **Closing a sub-tree dirty (`§C` Path C retroactive-closed)** in `D:/atlas/backlog.md` `## Out-of-scope (explicit) ## Atlas-root working-tree dirty triage` (e.g. CFDrs / hephaestus / mnemosyne / themis retro-closed per the 2026-07-06 triage turn): follow **ADR 0011** §Decision §Leg 3 OOS-record cadence sub-routine "Resolution branch" + "Post-resolution §-E update" before writing the chore commit.
- **Implementing a numeric SSOT rebind** to `coeus_core::Scalar` / `leto_ops::Scalar` / `kwavers_math::CsrScalar` / `ritk::*`: read **ADR 0005** (NumericElement doctrine) + **ADR 0006** (ComplexField) + **ADR 0007** (Complex<T>) BEFORE any `coeus`/`kwavers`/`ritk` source edit.
- **Working on GPU/accelerator substrate** (any consumer-authored kernel, dispatcher, device seam, or secure-parallelization question): read **ADR 0001** + **ADR 0002** + **ADR 0004** BEFORE any `hephaestus`/`apollo`/`coeus` GPU work. If the work crosses process boundaries, also read **ADR 0003**.
- **Working on a per-submodule inner-cleanup event** (e.g. the PR 0007 `helios/atlas-migration-push/internal-dirty-batch1` sub-counter): follow **ADR 0010** §Per-batch name pattern (adopt the `{consumer-repo}/atlas-migration-push/{batch-id}` shape) + **ADR 0011** §Decision §Leg 2 disjoint-scope rule (NO ATLAS-META RECLAIM).
- **Verifying an Atlas-provider migration push** (a tagged batch + pointer-advance + docs-rounding commit chain): cross-walk **ADR 0010** §Verification plan + **ADR 0011** §Decision §Leg 2 disjoint-scope rule.
- **Changing benchmark-regression policy**: read **ADR 0024** before editing
  the Atlas gate or any Apollo, Helios, or Kwavers integration.
- **Changing path-dependency checkout**: read **ADR 0020** + **ADR 0027**
  before editing the Atlas action or any Helios, Kwavers, or RITK integration.
- **Changing biological-response laws**: read **ADR 0028** and Asclepius
  ADR 0001 before editing Asclepius, Helios response analysis, or Kwavers
  thermal-response computation.

## References

- **`D:/atlas/AGENTS.md`** `documentation_discipline` — SSOT rules for PM artifacts; the rule that makes this INDEX.md authoritative for Atlas-meta doctrine navigation.
- **`D:/atlas/concurrent_agents`** contract — disjoint-scope rule (re-affirmed by ADR 0011 §Decision §Leg 2); consumer-claim-stream ownership rule (cited by ADR 0010 §Decision §Tag pointer anchoring).
- **`D:/atlas/backlog.md`** `## Cross-repo architect coordination ledger` — the CR-class inventory that motivates ADR 0005 (CR-4) + ADR 0006 (CR-EUNOMIA-COMPLEX). **Also**: `## Migration batches (vertical slices) ## Token batch ordering` — the batch-ordering SSOT that ADR 0010's Per-batch tag convention references.
- **`D:/atlas/checklist.md`** `## Per-batch Atlas-provider tag reservations` — the per-batch reservation SSOT (cross-walks ADR 0010's Per-batch name pattern; 6 reserved rows as of 2026-07-06: kwavers/batch1, cfdrs/batch2 [CLOSED], ritk/batch3, kwavers/batch4, apollo/batch5, cfd-core+ritk-core+moirai/batch6).
- **`D:/atlas/docs/audit/`** — the audit trail that motivates the doctrine in ADR 0001 (substrate audit at `2026-07-02-hephaestus-gpu-substrate-audit.md`); cross-repo coordination at `2026-07-02-cross-repo-integration-audit.md`; mnemosyne topology at `2026-06-27-mnemosyne-*` + `2026-07-01-mnemosyne-soundness-perf-audit.md`; kwavers-CFDrs-ritk atlas-migration at `2026-07-05-kwavers-cfdrs-ritk-atlas-migration-audit.md`.
- **`D:/atlas/docs/pr/`** — the PR-equivalent plan templates that inherit ADR 0010's Per-batch convention (e.g. `0007-helios-internal-dirty-cleanup-pr.md` uses the `helios/atlas-migration-push/internal-dirty-batch1` sub-counter; future PR 0008+ inherit the same convention).
- **`D:/atlas/scripts/`** `build-all.sh` / `build-all.ps1` — the Workspace top-level builds that let any consumer-repo edit (per ADR 0011's disjoint-scope) be cross-validated at the Atlas-meta layer through `cargo nextest run -p <consumer>`.
