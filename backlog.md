# atlas — cross-repository integration backlog

> Cross-repo migration board. **Per-repo** PM artifacts remain SSOT for repo-local concerns (e.g. `repos/kwavers/backlog.md`, `repos/CFDrs/docs/backlog.md`, `repos/ritk/backlog.md`); this artifact owns only the migration scope that crosses repo boundaries (provider-side obstacles, dep-velocity closure, and shared definition-of-ready gates).
>
> Active tactic: `checklist.md`. Full migration inventory: `gap_audit.md`. PM artifact freshness/SSOT rules per atlas `AGENTS.md` `documentation_discipline`.
>
> **Integration base**: fetched `origin/main`. Git owns the exact revision;
> this board does not duplicate a commit that becomes stale after each merge.

## ATLAS-RITK-655 — RITK B-spline bounded dense hot-path closure [minor] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/ritk` only.
- Outcome: PERF-432 / PERF-406-02 partially closed. The bounded dense
  support-matrix path landed in
  `ritk_registration::bspline_ffd::basis::{evaluate_bspline_displacement_dense_into,
  should_use_dense_path, DENSE_LATTICE_CUTOFF}`. The registration engine
  (`BSplineFFDRegistration::register` inner loop) auto-dispatches to the
  dense path when `ctrl_dims.product() <= 1_000_000` AND the dense support
  table stays within 16 MiB resident. Explicit `f64` arithmetic with `u32`
  control-point indices sidesteps the historical `coeus-core`/`leto-ops`
  `E0034` ambiguity on `from_f64`/`from_usize`.
- Acceptance: `cargo clippy -p ritk-registration --all-targets -- -D warnings`
  clean; `cargo nextest run -p ritk-registration bspline_dense` green
  (3/3 — dense matches sparse / zero-input invariant / dispatch predicate);
  equivalence asset: `bspline_dense_matches_sparse_on_small_lattice`
  abs-tolerance `5e-5` over the 8³ voxel lattice.
- Risk/change class: `[minor]`; performance increment with profiling
  counterpart (`bspline_displacement` bench is unchanged at criterion level;
  the dense path replaces the cache-based interior path on qualifying
  lattices in the registration's inner loop).
- Dependencies: none at the crate level — the change is purely additive
  inside `bspline_ffd::basis`. Coeus/Leto path consumes the trait surface
  only through `B: ComputeBackend` generic dispatch.
- Evidence limit: value-semantic nextest plus in-tree benchmark;
  no runtime allocation or perf claim in CI (the criterion bench reports
  count only).

## ATLAS-EUNOMIA-044 — Wrapper integer checked/saturating ops correctness [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/eunomia` only.
- Outcome: wrapper integer types I8/I16/I32 correctly implement `checked_add`,
  `checked_mul`, `saturating_add`, and `saturating_mul` on `NumericElement`,
  matching the primitive i8/i16/i32 implementations. Unsigned primitive
  types u8/u16/u32/u64/usize also receive `checked_add`/`checked_mul`
  overrides. Wrapper I32 sqrt routes through exact `isqrt()` instead of f64.
- Acceptance: `cargo nextest run -p eunomia` passes with new overflow/underflow
  regression tests; `cargo test --doc -p eunomia` passes; `cargo clippy
  -D warnings` clean; all affected types return `None` on overflow from
  `checked_add`/`checked_mul`.
- Risk/change class: `[patch]`; foundation-crate correctness fix with
  maximum leverage across all downstream consumers.
- Dependencies: none; eunomia is the stack foundation.
- Evidence limit: value-semantic overflow tests; no runtime allocation or
  performance claim.
- Delivery: extended `impl_numeric_element_unsigned!` macro in
  `crates/eunomia/src/impls/primitives/float.rs` with native
  `saturating_add`/`saturating_mul`/`checked_add`/`checked_mul` overrides
  (the unsigned impls lived in `float.rs`, an existing SRP-noise that is
  out-of-scope for this patch). Extended `impl_numeric_element!` macro in
  `crates/eunomia/src/impls/wrappers/numeric.rs` with an optional
  `$(, $sat_add, $sat_mul, $chk_add, $chk_mul)?` trailing arg so float
  wrappers keep the trait defaults while I8/I16/I32 provide the four
  integer-correct overrides. Routed I32 (and I8/I16 for parity) sqrt
  through the exact `i32::isqrt`/`i8::isqrt`/`i16::isqrt` primitives with
  the documented `neg → 0` guard. Added 15 overflow regression tests in
  `tests/integer_element.rs` (5 unsigned + 5 signed + 5 wrapper parity
  including a 100 001-case I32 sqrt oracle sweep).

## ATLAS-CFDRS-PERF-045 — CFDRS-PERF-SLOW-001 closure: poiseuille Picard perf [patch] — done

- Owner: atlas-meta coordinator (Claude); last-update: 2026-07-23; scope:
  `repos/CFDrs/crates/cfd-3d/src/fem/solver.rs` +
  `repos/CFDrs/crates/cfd-3d/src/venturi/solver.rs` only.
- Outcome: `validate_poiseuille_flow` PASS in 0.342s (was 30s+ TIMEOUT).
  Two root causes fixed at the algorithm, not symptom:
  1. `MidNodeCache::build` + `vertex_positions` recomputed per Picard iter and
     immediately discarded; worker closure paid O(n_mid) per cell. Hoisted to
     `FemSolver` struct fields keyed on `(n_corner_nodes, vertex_count)`, both
     `assemble_system` and `print_continuity_residual_stats` worker closures
     now use `extract_vertex_indices_cached` with uncached fallback preserving
     independent callability. Bit-identical Divergence Stats output verified.
  2. `leto_ops::SparseLuSolver` is a misnamed dense partial-pivoting LU, O(n^3)
     (see `crates/cfd-math/src/linear_solver/direct_solver.rs:3-7`); was firing
     for 1700-DOF saddle-point at `with_direct_threshold(100_000)`. Lowered to
     512 in both `solve` and `solve_picard` so medium saddle-point systems route
     to GMRES+AMG (Tier 2; GMRES+BlockDiag Tier 3 fallback). Collapse is ~100x.
- Acceptance: `validate_poiseuille_flow` PASS in 0.342s; full cfd-3d suite
  394/394 PASS (2 slow within budget at 16.7s/23.6s); no test or assertion
  relaxed; no `slow-timeout` bound raised. PR #311 squashed merged as CFDrs main
  `22ddc27df272c749d8c4e5c4b171113bfa1c272a`.
- Evidence limit: empirical (nextest under `.config/nextest.toml`).
- Strategic TODO: the misnamed dense-LU-claiming-to-be-sparse-LU is itself a
  defect in `leto-ops` — filed as ATLAS-LETO-OPS-SPARSE-LU-001 below.

## ATLAS-LETO-OPS-SPARSE-LU-001 — Real sparse LU/Cholesky in leto-ops [arch] — todo

- Owner: unclaimed (atlas-meta coordinator recorded; leto peer owns `leto-ops`
  source tree and is mid-refactor — peer-active; assist ladder step 3).
- Outcome: replace the misnamed dense partial-pivoting LU currently called
  `leto_ops::SparseLuSolver` with a real sparse LU or sparse Cholesky
  factorization (this is the architectural truth the name already promises).
  The CFDrs `crates/cfd-math/src/linear_solver/direct_solver.rs` doc at lines
  3-7 currently admits "atlas-native sparse direct solver backed by dense
  partial-pivoting LU" — i.e. the public `SparseLuSolver` name IS the
  misnomer, and `crates/cfd-3d/src/fem/solver.rs` works around it by
  routing medium systems to GMRES+AMG via `with_direct_threshold(512)`.
- Acceptance (architectural): real O(n) sparse factorization in `leto-ops`;
  the threshold routing becomes unnecessary; `SparseLuSolver` true to name
  (or renamed to a sparse algorithm and call sites updated in one migration
  per `consolidation_discipline: compatibility soup`).
- Risk/change class: `[arch]` + `[minor]` (no public-API break required if
  kept the same name; renaming is a `[major]` migration);
  upstream ownership (`architecture_scoping`) — implemented in `leto-ops`, not
  approximated downstream in CFDrs.
- Open question: peer is mid-refactor on leto-ops (the source is presently
  uncompilable in HEAD `9346413`; cf. "Residual CFDrs watchpoints carried
  forward" below). Wait for peer to land stabilization; then evaluate whether
  the FEM matmat structure warrants Cholesky (symmetric positive definite) or
  LU (saddle-point is indefinite).
- Refs: backlog.md#CFDRS-PERF-SLOW-001, ATLAS-CFDRS-PERF-045.

## ATLAS-PERF-043 — Preserve provider-native sparse-LU ownership [minor] — done

- Owner: Codex `/root`; delivered scope: `repos/leto` sparse-LU provider API,
  `repos/CFDrs` direct-solver consumer, their focused tests/docs, exact merged
  provider pin, and these cross-repo evidence entries. Broader solver-family
  migration, dense-LU algorithm changes, and release/deploy are non-goals.
- Outcome: `leto_ops::SparseLuSolver::solve_view` accepts `ArrayView1`; CFDrs
  passes its native `Array1` view and returns the provider-owned result without
  consumer-side RHS/result `Vec` staging.
- Acceptance: Leto PR #70 merged at `b24fc860864abad84af3118aa2bb27c32bb81265`;
  CFDrs PR #309 merged at `74efcceff0c737d09cc3251f24ed37bbb11de232`; provider
  SemVer checks pass 196/196 with 57 skips; provider sparse Nextest passes
  29/29; consumer direct-solver Nextest passes 4/4; doctest, Rustdoc, check,
  and warning-denied Clippy gates pass on the exact child revisions.
- Evidence limit: memory reduction is established by source/data-flow audit;
  no runtime allocation profile or speedup claim is made.

## ATLAS-INTEGRATION-042 — Close provider delivery graph [patch] — in progress

- Owner: Codex `/root`; last-update: 2026-07-23; scope: already-merged Apollo,
  Hephaestus, and Moirai provider heads, the dependent Kwavers lock and
  scheduler-workaround removal, RITK's TLS security update, and the final Atlas
  gitlinks. Unrelated live peer work in Leto and CFDrs is excluded.
- Outcome: publish one canonical graph in which Apollo and Hephaestus retain
  portable Python wheels, Moirai preserves saturated indexed work and exposes
  borrowing scopes, and Kwavers consumes that merged scheduler without
  serializing therapy tests.
- Acceptance: Atlas first pins Apollo `614939fd`, Hephaestus `b726b39f`, and
  Moirai `ddb665e9`; the follow-on Moirai cleanup removes only its unused core
  TLS gate while preserving executor and platform fast paths; RITK advances to
  merged TLS correction `06cba046` and Atlas publishes canonical graph
  `c982fe0`; Kwavers regenerates its lock through Cargo, removes the six-test
  serialization workaround, passes the affected therapy lane and hosted Linux
  resolution, then Atlas advances the final Kwavers gitlink.
- Evidence: Apollo PR #64, Hephaestus PR #63, and Moirai PR #83 are merged;
  Moirai exact head `b543b98` passes Rust, Linux, macOS, Windows, Greptile, and
  CodeRabbit checks. Kwavers PR #313's security job exposed inherited
  RUSTSEC-2026-0098, RUSTSEC-2026-0099, and RUSTSEC-2026-0104 through the
  Atlas-pinned RITK Reqwest 0.11 graph. RITK PR #49 exact head `6ecac07a`
  passes 21 first-party Rust, Python 3.9–3.13, wheel, dependency, and migration
  checks and merges as `06cba046`; the external analyzer alone errors. Atlas
  correction PR #87 merges as `c982fe0` and pins that merged default, not the
  provisional PR head. No downstream audit bypass is accepted. Moirai PR #84
  merges as `e4d2855`; default closeout `c870eed` passes exact Rust and
  three-platform wheel run `29963043374`.
- Root cause fix (2026-07-23): CI hosted matrix was failing because the
  kwavers checkout-path-dependencies action pinned `atlas_ref` to `c982fe0`,
  whose aequitas gitlink points to `262b3e0` (pre-acoustic-types). The
  `Intensity`, `VolumetricPowerDensity`, and `AcousticImpedance` types were
  added in aequitas `ce3ef7a6` but the stale pin caused CI to check out the
  old revision. Fixed by advancing `atlas_ref` to `806c6e7` (current atlas
  HEAD with correct gitlinks) in all 3 kwavers CI references. Kwavers branch
  `codex/kwavers-aequitas-acoustic-boundaries` pushed at `5766bfe7a` with the
  fix; atlas gitlink advanced to `5766bfe7a`.

## ATLAS-INTEGRATION-041 — Align the Leto consumer graph [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-22; delivered scope:
  `repos/leto`, `repos/ritk`, `repos/coeus`, `repos/hephaestus`, this item, and
  the corresponding checklist entry. Provider source changes, unrelated
  gitlinks, and release/deploy are non-goals.
- Outcome: make the canonical Atlas graph resolve one Eunomia numeric identity
  for Kwavers and Apollo by advancing Leto plus its RITK, Coeus, and Hephaestus
  consumers to their already-merged Eunomia 0.7/Leto 0.40 compatibility heads.
- Acceptance: Atlas pins Leto `c00fa04a`, RITK `5f57557a`, Coeus `eb93d124`,
  and Hephaestus `8c6ab72d`; the checkout-path-dependencies gate passes; and
  Kwavers resolves, compiles, tests, and benchmarks through the exact updated
  graph without Eunomia 0.6/0.7 type duplication.
- Risk/change class: `[patch]`; verification uses the Atlas checkout gate plus
  Kwavers all-feature locked metadata, focused compile, and hosted CI.
- Evidence: the Atlas checkout tool passes 11/11 tests in 3.070 s. The exact
  downstream graph resolves with one Eunomia 0.7 identity, passes locked
  all-feature metadata and `kwavers-math` compilation, and passes all 266
  `kwavers-math` tests. Kwavers head `909bcdfc7` passes 26 exact-head hosted
  checks with zero failures: CI run `29917018067`, architecture run
  `29917018155`, benchmark run `29917018135`, and legacy audit run
  `29917018053`. The benchmark gate proves its three merge-critical executables
  byte-identical and completes in 12 minutes without running redundant
  statistical pairs; Kwavers PR #307 merges as `0602c1fd4`. No release occurs.

## ATLAS-ROADMAP-040 — P2 domain-provider consolidation [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-22; delivered scope:
  `repos/hyperion/**`, the published Aequitas/Proteus/Asclepius/Leto/Hephaestus
  dependency-alignment commits, direct Hyperion migrations in Helios, Kwavers,
  and CFDrs, exact provider/consumer gitlinks, and this item's Atlas PM entries.
  Helios book edits and unrelated dirty submodules remain outside the claim.
  Outcome: replace the speculative two-package target with
  an evidence-gated P2 program whose registrations are consequences of code
  consolidation. Scope is Hyperion's first photon/optical transport slice plus
  the prerequisites that decide whether Ares or Prometheus can become a second
  package. General electromagnetics, dose workflow, fluid-structure coupling,
  combustion closure, and release/deploy are non-goals.
- Acceptance: Hyperion Phase 0 migrates Kwavers, Helios, and CFDrs to one typed
  coefficient, optical-depth, Beer-Lambert, and derived-diffusion SSOT; deletes
  all named duplicate formula/model sites; and passes analytical, invalid-
  input, generic-scalar, and exact consumer-differential oracles. No empty
  repository or compatibility layer enters Atlas.
- P2-B readiness: Ares stays blocked until Proteus owns the duplicated elastic
  conversions/catalogs and a second production solid-operator consumer is
  ready in the same extraction. Prometheus stays blocked until Kwavers has one
  reaction vocabulary, Horae owns reusable embedded stepping, and a second
  production reaction-network consumer is ready. Manufactured validation alone
  does not satisfy the trigger.
- Dependencies and hierarchy: Proteus owns material identity/properties;
  Hyperion Phase 0 owns photon/optical attenuation and derived transport laws;
  Gaia/Leto/Athena/Hephaestus own geometry, arrays, solver policy, and
  accelerator mechanics. Future Ares owns solid kinematics/balance while
  Harmonia owns coupling orchestration. Future Prometheus owns reaction
  networks while transport discretization stays in consumers.
- Risk/change class: `[arch]`; each provider's additive public surface is
  `[minor]`, while consumer removals are classified independently by
  `cargo-semver-checks`. Package-name availability and exact provider APIs are
  verified when the ADR and first code slice begin.
- Execution evidence: the source audit found three independent
  Beer-Lambert owners and repeated Kwavers optical laws. The same audit found
  Ares's immediate duplicates belong to Proteus and Prometheus lacks a second
  production consumer; these limits are promotion blockers, not deferred
  assumptions. Hyperion `7b4561b` is published and anonymously readable. ADR
  0030 records the bounded hierarchy and consolidation accounting. Helios
  `105a093` deletes its coefficient, NIST-table, projection-law, and raw
  production transmission owners; its full local consumer gate and hosted run
  `29883200466` pass. Kwavers `5fc6f0419` deletes its repeated derived optical
  laws and passes 6,168/6,168 configured workspace tests. CFDrs implementation
  `9c8ce32e`, merged as `69323418`, deletes its raw 405-nm expression and passes
  132/132 configured package tests plus warning-denied static and documentation
  gates. Atlas registers the exact public Hyperion head and advances the CFDrs
  gitlink in the same change. The P2-A deletion ledger is closed; Ares and
  Prometheus remain evidence-gated rather than scheduled package additions.

## ATLAS-INTEGRATION-038 — Iris visualization promotion [arch] [minor] — done

- Owner: Codex `/root`; scope: public Iris color/view/render contracts, direct
  `ritk-snap` and `ritk-vtk` adoption, deletion of both RITK color engines,
  exact Iris/RITK gitlinks, ADR 0029, and stack documentation. Medical
  windowing, VTK formats, UI state, GPU mechanics, Kwavers migration, and
  CFDrs/Kwavers plot-series assembly are non-goals for this increment.
- Acceptance: Iris is anonymously readable and passes all crate/feature/docs/
  supply-chain gates; RITK directly consumes the public revision with exact
  table-node differential tests and no local interpolation; PR 46 hosted gates
  pass and merge; Atlas pins both remote defaults and its checkout-engine and
  documentation consistency gates pass.
- Evidence: Iris PR 2 closed the public foundation at remote default
  `a8ea96f7`; its verify and supply-chain jobs passed. RITK PR 47 closed the
  consumer record and merged-default Rustfmt drift as `a36e65df` after CI
  `29833657517`, Python CI `29833657538`, and migration audit `29833657634`
  passed on exact head `a41774fa`. The preceding implementation evidence
  includes 943/943 focused Nextest tests, exact 2,560-node table comparison,
  non-finite regressions, and SemVer classification of only the intentional
  public removals. Atlas PR 71 registered Iris; this closure pins both final
  public defaults and passes the checkout-engine and documentation gates.

## ATLAS-INTEGRATION-039 — Iris CFDrs consolidation [arch] [major] — done

- Owner: Codex `/root`; scope: the exact Iris blue-red law, direct
  `cfd-schematics` adoption, deletion of CFDrs's parallel map enum and
  formulas, overlay range/allocation correction, exact Iris/CFDrs gitlinks,
  ADR 0029 extension, and synchronized stack documentation. CFD field
  semantics, Plotters rendering, and the actively claimed Kwavers renderer are
  non-goals.
- Acceptance: Iris exhaustively verifies the additive law; CFDrs consumes
  `NamedColorMap` without a wrapper, computes range once per overlay, borrows
  existing field maps, and contains no superseded map formula; both public
  defaults merge and Atlas records their exact commit objects.
- Evidence: Iris PRs 3 and 4 merge the provider and closure at `c7454ef3`;
  default-branch CI `29845556866` passes. CFDrs PR 303 merges the consumer at
  `394c9977`; 176/176 `cfd-schematics` tests, 10 iterator/window tests, 16
  doctests, warning-denied Clippy and Rustdoc, feature checks, and Venturi
  render inspection pass. The attempted isolated CFDrs SemVer comparison was
  blocked before API analysis by pre-existing Aequitas/Leto Git-source
  identity splits; no SemVer-pass claim is made.

## ATLAS-INTEGRATION-037 — Asclepius P1 promotion [arch] [minor] — done

- Owner: Codex `/root`; scope: public Asclepius core and Coeus adapter, Atlas
  registration, direct Helios and Kwavers adoption, deletion of superseded
  response formulas, provider-graph checkout, documentation, and proof-backed
  verification. Images, grids, transport, material properties, tissue
  catalogs, planning objectives, and clinical parameter recommendations remain
  consumer-owned.
- Acceptance: Atlas pins fetched Asclepius `origin/HEAD`; ADR 0028 records the
  dependency boundary and theorems; Helios directly uses Asclepius radiation
  laws and the Coeus adapter; Kwavers directly uses Asclepius CEM43, Arrhenius,
  and independent-insult laws; duplicate computation and compatibility
  wrappers are absent; focused and full consumer gates plus exact-head hosted
  CI pass.
- Evidence: public Asclepius remote default `eb65eaf` contains the `no_std` law
  core and one-way Coeus adapter merged at `794f8c3`, plus the completed public
  distribution contract. Analytical, property, differential, layout, ZST,
  GAT, `Cow`, const-generic, allocation, and `f32`/`f64` tests pass. Helios
  remote default `33bba34` contains direct adoption `4ce96b1` after 270/270
  local Nextest plus workspace check, Clippy, doctest, rustdoc, examples,
  cargo-deny, and exact-head hosted CI. Kwavers PR 301 merges as `1cb01fe`,
  deletes consumer-owned response formulas, consumes the public Asclepius Git
  source without a sibling patch, and passes all 23 first-party hosted checks.
  Anonymous Git resolves all three exact remote-default OIDs. Atlas pins those
  public defaults and the final structural residue scan finds no superseded
  response-law implementation or compatibility wrapper in the migrated
  consumer paths.

## ATLAS-INTEGRATION-035 — Proteus and Tyche promotion ADRs [arch] [minor] — done

- Owner: atlas-meta; scope: file ADRs 0025 and 0026 documenting the Proteus
  and Tyche provider promotions peer landed via `f043d22`, `beb2713`,
  `feed3bc`, and `edf99e4` without stack-level ADR ceremony — recording
  bounded context, dependency direction, Phase scope, theorems and evidence,
  rejected alternatives, consequences, and Relates-to to ADRs 0002/0005/0021/
  0023/0025 per `documentation_discipline` ADR SSOT. Consumer material-property
  and UQ migrations remain separate vertical increments.
- Acceptance: ADR 0025 records the Proteus material-property promotion with
  Phase-1 thermophysical boundary (MassDensity, SpecificHeatCapacity,
  ThermalConductivity, derived thermal diffusivity), Aequitas-quantity-
  transparent newtypes, GAT-based ConstitutiveLaw seam, NoState ZST, and
  `Cow<str>` material identity; ADR 0026 records the Tyche UQ promotion with
  Phase-0 random-access Latin hypercube, ensemble execution, online moments,
  Pearson screening, split-conformal calibration, and Moirai/Consus adapters,
  with no_std core and const-generic numeric widths. INDEX table adds rows
  0025 and 0026, narrative extends through 0026, cross-walk adds two rows,
  Group F topic-keyword index added, CHANGELOG `### Added` records the
  backfilled ADRs.
- Evidence: ADR files authored against peer-published remote HEADs (Proteus
  `2b06be3`, Tyche `7898899`) cross-referencing the in-repo ADRs 0001 of each
  provider; ADR INDEX updates compile-level stable (markdown only); the
  promotion ceremonies themselves were already peer-verified at package-level
  (Proteus property positivity/dimensional algebra/codegen fixture, Tyche
  LHS permutation/replay/Welford/Cauchy-Schwarz/conformal rank).

## ATLAS-INTEGRATION-036 — Coeus hephaestus 0.18.0 bump [patch] — done

- Owner: atlas-meta; scope: `repos/coeus/Cargo.toml` workspace.dependencies
  pin update for `hephaestus-{wgpu,core,cuda}` from `^0.17.0` to `^0.18.0`
  after peer's v0.18.0 hephaestus tag advance, plus Atlas-parent gitlink
  advance for coeus `56fa49a` -> `c290f3e` and leto `4158b8e` -> `02d74fd`.
- Acceptance: `cargo check --workspace --all-targets` clean across all 20
  Atlas packages (including coeus) after resolving the path-dep version
  pin mismatch that blocked `coeus-wgpu` from selecting a hephaestus-core
  version; Atlas-parent gitlinks advanced and pushed.
- Evidence: `cargo check --workspace --all-targets` rc=0 across all 20
  packages via `scripts/build-all.ps1` (1m 48s clean after bump);
  `cargo nextest run --workspace` on coeus 938/938 passed;
  `cargo test --doc --workspace` on coeus passed (8 doctests across
  coeus-tensor and coeus-wgpu). Coeus merged via PR-style no-ff merge
  `c290f3e`. Atlas-parent merge `3f40b79`.

## ATLAS-INTEGRATION-034 — Benchmark gate repair [arch] [patch] — done

- Owner: Codex `/root`; scope: Atlas Criterion comparison SSOT and the Apollo,
  Helios, and Kwavers CI integrations that introduced copied, same-run
  baseline checks. Unrelated benchmark bodies and performance tuning remain
  out of scope.
- Acceptance: one Atlas-owned Rust tool classifies two replicated
  base-first/candidate-first comparison pairs, controls family-wise
  error at 5%, and fails closed on missing or mismatched evidence; each
  consumer holds its candidate harness constant, keeps both revisions in each
  pair on one runner and at one filesystem path, deletes copied Python gates,
  and passes exact-head hosted CI. Long instruments may distribute the four
  co-located pairs across isolated jobs.
- Evidence: unit and CLI tests, warning-denied Clippy and rustdoc, synthetic
  positive/overlapping/missing comparison fixtures, consumer workflow review,
  and hosted CI on each published child revision.
- Current increment: Apollo hosted run `29764170548` reported twelve apparent
  regressions across source-identical revisions under one ABBA block. The
  Atlas gate now intersects phase-reversed ABBA and BAAB blocks and fails
  closed across both benchmark universes; local static, value-semantic,
  doctest, and documentation gates pass. Atlas also owns the exact-gitlink
  checkout action for Helios, Kwavers, and RITK; Apollo's checkout is dead
  because Apollo has no external Cargo path dependencies. Apollo's hosted
  benchmark gate merges through PRs 57-58 at `2a22319`; Helios PR 13 merges
  at `4ce96b1` with hosted benchmark evidence. Kwavers PR 299 merges at
  `198f2b8c`; exact-head hosted run `29841101698` completed all four pair jobs
  but found three replicated apparent regressions despite no semantic
  production delta. Distinct checkout paths remained correlated with revision.
  Kwavers PR #304 then merged Tyche collocation as `9ad18523d` after exact-head
  ordinary CI `29875284052`, architecture `29875284007`, and legacy audit
  `29875283982` passed. Its superseded full-suite benchmark run `29875283986`
  classified 190 cases and reported 37 regressions outside the three canonical
  targets, confirming the already-recorded scope and latency defect. PR #306
  merged the bounded same-path workflow as `00d06f00e`; exact head `a85aa58e5`
  passes complete candidate smoke, all four 21–23 minute AB/BA pairs, aggregate
  classification (`29884797777`), and the three ordinary workflow runs. PR
  #308 closes KW-UQ-064 and KW-CI-063 as `402d9695`; its exact documentation
  head `8373c8bb0` passes CI `29890089765`, architecture `29890089803`, and
  legacy audit `29890089797`. Atlas advances that fetched default-branch
  gitlink without modifying peer worktrees.

## ATLAS-INTEGRATION-033 — Harmonia Phase 0 [arch] [minor] — done

- Owner: Codex `/root`; scope: Harmonia Phase 0, Athena observer construction,
  public Harmonia remote, Atlas submodule registration, ADR 0023, stack map,
  and provider boundary documentation. Consumer coupling-loop migrations
  remain separate vertical increments.
- Acceptance: Harmonia owns transactional two-partition Jacobi coupling over
  Horae time/subcycling and Athena convergence policy; production code is
  `no_std`, statically dispatched, allocation-free after workspace
  construction for built-in borrowed transfers, and contains no physics,
  array, accelerator, allocator, or scheduler ownership.
- Evidence: Harmonia 14/14 nextest, one doctest, `f32`/`f64` instantiations,
  analytical contraction bound, generated properties, subcycle differential,
  transaction, pointer-identity, ZST-layout, allocation, and release-codegen
  checks; warning-denied Clippy/rustdoc, `no_std`, example, cargo-deny, and
  exact-head GitHub CI. Atlas pins fetched Harmonia `origin/main`
  `cf6ce3e9175bbc3eebc51918d137492b2da5edba`.

## ATLAS-INTEGRATION-032 — Documentation and checkout hygiene [patch] — done

- Owner: Codex `/root`; scope: Atlas, Athena, and Horae READMEs; Athena
  observer-construction review; published child documentation heads; parent
  gitlinks. Unique CFDrs, RITK, and Harmonia working state remains excluded.
- Acceptance: Atlas distinguishes recorded gitlinks from local child state,
  does not encode a false Harmonia-to-Proteus dependency, and documents
  targeted checkout recovery. Athena and Horae state their Atlas boundaries,
  features, and infrastructure dependencies. Every README-backed rustdoc
  target compiles.
- Evidence: Athena external observer doctest, 2/2 focused nextest cases,
  warning-denied Clippy, and merged README PR #3 at `96fb26d`; Horae
  no-default-feature compilation, doctest, rustdoc, and merged README PR #2 at
  `92af1a2`; Atlas package-count, target-path, stale-edge, and diff checks.
- Closure: the parent advances only Athena and Horae. Leto's superseded
  feature checkout was restored to recorded merge `1752058`; unpublished
  CFDrs work, modified RITK content, and the unregistered Harmonia repository
  remain preserved outside the parent commit.

## ATLAS-INTEGRATION-031 — Horae/Athena extraction [arch] [minor] — done

- Owner: Codex `/root`; scope: Horae and Athena provider repositories, Leto
  CG/GMRES ownership deletion, public remotes, Atlas gitlinks, stack
  documentation, and build-discovery SSOT. CFDrs/Kwavers consumer migrations
  remain separate dependency-ordered increments.
- Acceptance: Horae owns typed explicit time integration over Aequitas; Athena
  owns backend-neutral PCG and restarted right-preconditioned GMRES over Leto
  CPU and Hephaestus WGPU; Leto exports no duplicate iterative-solver
  recurrence; both providers are public, versioned, CI-equipped packages with
  exact parent gitlinks.
- Evidence: Horae passes 14/14 configured nextest cases, its doctest, rustdoc,
  analytical example, and dependency-policy gate. Athena passes 20/20 with no
  skips, including generic CPU and real-device WGPU PCG/GMRES, post-workspace
  allocation checks, four executed examples, doctest, rustdoc, and
  dependency-policy gates. Follow-up provider CI verifies the derived Horae
  bounds and Athena's direct `A*x=b` CPU/Jacobi/WGPU PCG oracles on merged
  heads. Leto PR #54 merges as `1752058` after 295/295 `leto-ops` cases and
  eight doctests; semver-checks classifies the removed public surface as major.
- Closure: public `ryancinsight/horae` main is `e57f798`; public
  `ryancinsight/athena` main is `7d647e7`; Atlas records both exact objects and
  advances Leto to merged default `1752058`. The current package count is 19.

## ATLAS-INTEGRATION-030 — Aequitas consumer closure [patch] — done

- Owner: Codex `/root`; scope: merged CFDrs PR #298 and Kwavers PR #295,
  their parent gitlinks, and Aequitas provider-graph evidence.
- Acceptance: Kwavers replaces bubble-energy `uom` ownership with Aequitas,
  CFDrs carries typed spacing into Hephaestus, and Atlas records only merged
  remote-default objects rather than local-only child commits.
- Evidence: Kwavers head `0fb31d800` passes all 24 hosted checks, including
  stable/beta/nightly, feature combinations, CUDA, 1,554 native tests,
  doctests, Miri, security, coverage, and Criterion benchmarks. CFDrs PR #298
  passes warning-denied GPU Clippy and 13/13 focused Laplacian tests.
- Closure: Kwavers PR #295 merges as
  `49c116ffb7466f9163b7762f03bc74725d8026c3`; CFDrs PR #298 merges as
  `7c37f7f30dc286e8853bdf41da7652abeadebe23`. The parent replaces unpublished
  gitlinks `156531eeb` and `a34a01d1` with those fetched `origin/main` commits.

## ATLAS-INTEGRATION-028 — Hephaestus PM convergence [patch] — done

- Owner: Codex `/root`; scope: Hephaestus PR #52's PM-only default commit and
  its parent gitlink. Dirty child worktrees remain peer-owned.
- Acceptance: the parent records exact Hephaestus default
  `cdfcd0cb38de03d28107fc231042eaf55e078e3a`; every other gitlink is unchanged;
  the final 16-link audit has zero drift.
- Closure: Atlas PR #49 merges at `2c1ee62`; all 16 parent gitlinks resolve to
  existing commits equal to their fetched remote defaults.

## ATLAS-INTEGRATION-027 — Provider-default convergence [patch] — done

- Owner: Codex `/root`; scope: merged Hermes and Leto defaults and their parent
  gitlinks. Dirty child worktrees and root package-manager state remain
  peer-owned and outside this claim.
- Acceptance: Hermes resolves merged Eunomia 0.6 without restoring raw-half
  ownership; Leto's merged Box-Muller increment remains intact; every Atlas
  gitlink equals its fetched remote default.
- Evidence: Hermes PRs #10-#11 merge at `6f9b81f` after warning-denied Clippy,
  388/388 Nextest cases, 18/18 runnable doctests, and warning-denied rustdoc.
  Leto PR #48 merges at
  `bb03244f05a9c43c318d103225c3ccad07e9fad9` with its recorded 304/304
  `leto-ops` tests and criterion comparison.
- Closure: Atlas PR #46 advances Hermes and Leto; PR #47 corrects the invalid
  same-prefix Leto object ID detected by the post-merge audit. All 16 parent
  gitlinks then resolve to existing commits equal to their fetched defaults.

## ATLAS-INTEGRATION-026 — Eunomia runtime-half retirement [patch] — done

- Owner: Codex `/root`; scope: merged Eunomia and Hephaestus defaults, their
  parent gitlinks, and cross-repo evidence. Main-tree Coeus/RITK and root
  package-manager working state remain peer-owned and outside this claim.
- Acceptance: Eunomia's production graph excludes `half`; Hephaestus resolves
  the coherent Eunomia 0.6/Hermes 0.4/Leto 0.39 closure; both child defaults
  are merged and the parent records only those defaults.
- Evidence: Eunomia PR #48 merges at `df77dfd`; Hephaestus PR #51 merges at
  `594d57a`. Producer Nextest passes 86/86 and Hephaestus passes 312/312,
  together with warning-denied diagnostics and documentation gates.
- Integration state: the branch advances only `repos/eunomia` and
  `repos/hephaestus`; all other parent gitlinks remain unchanged.
- Closure: Atlas PR #44 merges at `d207cf6`; the parent records Eunomia
  `df77dfd` and Hephaestus `594d57a`.

## ATLAS-INTEGRATION-029 — Hephaestus provider-first CFDrs 2D GPU Laplacian [minor] — done

- Owner: Atlas integration; scope: `repos/hephaestus` provider-side stencil
  surface and `repos/CFDrs` consumer thin-typed migration.
- Acceptance: Hephaestus owns the 2D Laplacian WGSL kernel, parameters, and
  boundary-condition enum; `cfd-core` no longer carries the shader source or
  uniform layout; `cfd-core`/`cfd-math` remain thin typed consumers; all
  relevant Clippy, nextest, and rustdoc gates pass.
- Evidence: Hephaestus `crates/hephaestus-wgpu/src/application/stencil/` now
  contains `Laplacian2DKernel`, `Laplacian2DParams`, and `BoundaryCondition`;
  `cfd-core` `compute/gpu/kernels/laplacian/kernel.rs` forwards to the
  provider; `cfd-core/src/compute/gpu/shaders.rs` deleted. Local verification:
  `hephaestus-wgpu` 140/140 nextest; `cfd-core --features gpu` 245/245 nextest;
  `cfd-math --features gpu` 362/362 nextest; `cargo clippy -D warnings` clean on
  both crates.
- Closure: provider-first ownership removes the falsely generic f32 WGSL
  boundary from the consumer; the kernel is compiled once and reused, and the
  consumer validates only the CFD grid contract.

## ATLAS-INTEGRATION-025 — Eunomia precision graph [major] — done

- Owner: Codex `/root`; scope: merged Eunomia, Hermes, and Leto defaults,
  their parent gitlinks, and cross-repo evidence. The cumulative Atlas branch
  also reconciles previously committed Coeus and RITK gitlinks to their merged
  defaults; their working trees and root package-manager state remain
  peer-owned and outside this claim.
- Acceptance: Eunomia owns the reduced-format bit and float-element contracts;
  Hermes and Leto expose only Eunomia reduced-precision types; Leto resolves
  current provider defaults and passes its complete gate; the parent records
  only merged default commits.
- Evidence: Eunomia PRs #46-#47 merge at `c196db5`; Hermes PRs #8-#9 merge at
  `c9bbdf8`; Leto PRs #46-#47 merge at `7afcbd0`. Leto passes format,
  all-feature compilation, warning-denied Clippy, 593/593 configured Nextest,
  nine doctests, rustdoc, no-default-feature compilation, and residue scans.
  All 16 Atlas gitlinks equal their fetched remote defaults.
- Closure: this increment advances Eunomia, Hermes, and Leto and reconciles
  previously committed Coeus and RITK pointers to current merged defaults.
  Atlas PR #41 merged at `3f5f51f`; local `main` reconciled to the same commit.
  Fresh RITK, Coeus, and root package-manager work remains unstaged.

## ATLAS-INTEGRATION-024 — Helios provider lock convergence [patch] — done

- Owner: Codex `/root`; scope: stale Helios lock takeover, merged Helios
  default, and the parent Helios gitlink.
- Acceptance: replace the invalid partial Apollo edit with one complete Cargo
  resolution; select merged Eunomia/Leto/Hephaestus providers; remove
  `num-complex`; pass the complete Helios workspace gate.
- Evidence: Helios PR #7 merges at `79b09e9`; locked metadata and format,
  warning-denied all-target/all-feature Clippy, 272/272 configured Nextest,
  ten Rust library doctest targets, and warning-clean rustdoc pass.
- Closure: parent advances only `repos/helios`; concurrent Leto, RITK, Themis,
  and root package-manager state remains unstaged.

## ATLAS-INTEGRATION-023 — Coeus NN provider benchmark closure [patch] — done

- Owner: Codex `/root`; scope: stale Coeus PR #212 takeover, merged Coeus
  default, its provider lock, and the parent Coeus gitlink.
- Acceptance: remove Burn without deleting or shrinking the native NN
  benchmark instrument; retain every Sequential/Moirai scenario; resolve the
  current Eunomia/Leto/Hephaestus graph; merge only after local and hosted
  evidence is green.
- Evidence: Coeus PR #212 merges at `bb97cc6`; the benchmark retains 211
  operation groups and 424 native rows. Format, all-target/all-feature locked
  Clippy, 268/268 configured Nextest, eight doctests with two intentionally
  ignored, warning-clean rustdoc, locked metadata, and CodeRabbit pass.
- Closure: parent advances only `repos/coeus` from stale PR head `a365b25` to
  merged default `bb97cc6`; concurrent Helios, RITK, Themis, and root
  package-manager state remains unstaged.

## ATLAS-INTEGRATION-022 — Eunomia sub-byte graph [patch] — done

- Owner: Codex `/root`; scope: merged Eunomia, Leto, and Hephaestus defaults,
  consumer reproducibility locks, and cross-repo PM artifacts.
- Acceptance: Eunomia owns one canonical reduced-format conversion kernel;
  Leto and Hephaestus resolve Eunomia 0.4.0 from its merged default; every
  provider/consumer gate is green; the parent records only merged defaults.
- Evidence: Eunomia PR #39 merges at `49dc115` after 60/60 Nextest, exhaustive
  encoding/rounding/dispatch coverage, AArch64 source compilation, and local
  Leto/Hephaestus integration. Leto PR #44 merges at `f0b4d8e` after 593/593
  Nextest. Hephaestus PR #50 merges at `ed7d76e` after 312/312 Nextest,
  including real CUDA and WGPU contracts. All three warning-denied compile,
  doctest, and rustdoc gates pass.
- Closure: parent advances `repos/eunomia`, `repos/leto`, and
  `repos/hephaestus`; all other dirty child and root paths remain unstaged.

## ATLAS-INTEGRATION-019 — Hephaestus legacy-math residue [patch] — done

- Owner: Codex `/root`; scope: `repos/hephaestus` test/benchmark manifests,
  CPU reference code, and synchronized provider-graph PM artifacts. Kwavers
  and RITK working trees remain outside this claim.
- Acceptance: Hephaestus has no `ndarray` or `nalgebra` dependency or source
  reference in tests/benches; differential references use Leto/Leto Ops or
  explicit analytical oracles, and the provider's value-semantic gates remain
  green.
- Evidence: Hephaestus PR #47 merges at `cec0e33`; its direct legacy math
  edges and source references are deleted, WGPU differential oracles use Leto,
  and the comparative benches measure Leto against real WGPU/CUDA dispatch.
  Core Nextest is 48/48, WGPU 140/140, CUDA 109/109; warning-denied Clippy,
  doctests, warning-clean rustdoc, and all-target benchmark checks pass.
- Closure: parent advances `repos/hephaestus` from `93bc38e` to `cec0e33`.

## ATLAS-INTEGRATION-020 — Apollo Hephaestus lock convergence [patch] — done

- Owner: Codex `/root`; scope: Apollo `Cargo.lock`, Apollo PM records, and
  the parent Apollo gitlink. The lock-only consumer refresh is sequenced after
  Hephaestus PR #47 and does not touch Kwavers or RITK peer scopes.
- Acceptance: Apollo's three Hephaestus packages resolve merged provider
  `cec0e33`, with no source/manifest compatibility path; locked Apollo gates
  and the provider audit remain green.
- Evidence: Apollo PR #53 merges at `a31b8f8`; all three lock entries select
  `cec0e33`. Locked compile, 402/402 Nextest, warning-denied Clippy,
  doctests, warning-clean rustdoc, provider audit, hosted Rust/Python, and
  CodeRabbit checks pass. The external analyzer error is non-required.
- Closure: parent advances `repos/apollo` from `7303423` to `a31b8f8`.

## ATLAS-INTEGRATION-021 — Coeus tensor legacy benchmark removal [patch] — done

- Owner: Codex `/root`; scope: merged Coeus PR #211 gitlink and synchronized
  provider-graph PM artifacts. The peer-owned Kwavers pointer remains outside
  this increment.
- Acceptance: Coeus tensor benchmarks no longer declare or execute a legacy
  tensor backend; retained rows use Coeus Sequential/Moirai and Leto dispatch,
  and the consumer lock graph aligns to merged Hephaestus `0.16.1`.
- Evidence: Coeus PR #211 merges at `4459d09`; locked package check, 56/56
  Nextest, warning-denied Clippy, five doctests, warning-clean rustdoc,
  locked metadata, and the targeted residue scan pass. Coeus has no hosted
  workflow; the external analyzer is non-required.
- Closure: parent advances `repos/coeus` from `093f31f` to `4459d09`.

## ATLAS-INTEGRATION-018 — RITK Apollo alignment [patch] — done

- Owner: Codex `/root`; scope: merged RITK default gitlink plus cross-repo PM
  artifacts.
- Acceptance: the gitlink names RITK PR #41's merged default-branch commit,
  whose lock and composite checkout resolve Apollo 0.25 without staging the
  active Kwavers GPU feature branch.
- Evidence: RITK merge `a41e03b9`; all 22 repository and review checks pass,
  including Linux/macOS/Windows Nextest, Python 3.9–3.13, wheel, Clippy,
  formatting, dependency alignment, and migration audit. The external
  `recurseml/analysis` error is non-required.
- Closure: parent advances `repos/ritk` from `aededa6b` to `a41e03b9`.

## ATLAS-INTEGRATION-015 — Merged default refresh [patch] — done

- Owner: Codex `/root`; scope: merged CFDrs, Eunomia, Helios, Leto, and RITK
  default-branch gitlinks plus cross-repo PM artifacts.
- Acceptance: every advanced gitlink names a merged remote-default commit;
  fresh Apollo, Kwavers, and RITK peer work remains unmodified and no dirty
  feature-branch head enters the parent graph.
- Closure: CFDrs `a833b7fe` preserves the independent sparse-LU contract;
  Eunomia `a2e4f390`, Helios `972fb53e`, Leto `3ac0d203`, and RITK
  `aededa6b` carry their merged provider increments. Apollo remains at merged
  `c8742814`, Hephaestus at `93bc38e6`, and Kwavers at merged `9eabc4e2`.
- Evidence: each recorded object equals its fetched remote default. CFDrs
  direct-solver Nextest passes 4/4, its direct-after-GMRES consumer regression
  passes 1/1, and warning-denied `cfd-math` Clippy passes. RITK PR #40's
  cross-platform Nextest, Python 3.9–3.13, wheel, lint, dependency-alignment,
  and migration-audit lanes pass. Provider-specific evidence remains in each
  repository's PM artifacts.

## ATLAS-INTEGRATION-012 — Apollo policy-wrapper removal [major] — done

- Owner: Atlas integration; scope: `repos/apollo` gitlink and the provider-graph
  PM artifacts only.
- Acceptance: the gitlink names Apollo PR #49's merged default-branch commit,
  which deletes the duplicate radix execution-policy wrapper, routes directly
  through Moirai's `AdaptiveWithThreshold`, and advances `apollo-fft` to
  0.25.0 without an Apollo-owned WGPU implementation.
- Evidence: Apollo merge `e2f905a`; local locked `apollo-fft` Nextest 393/393,
  warning-denied Clippy, doctests, rustdoc, source-residue scan, and provider
  audit pass; hosted Python bindings and Rust workspace workflow
  `29620388853` pass. The known external `recurseml/analysis` failure is
  non-required and does not inspect the merged head's build gates.
- Closure: parent advances `repos/apollo` from `0b5d11c` to `e2f905a`.

## ATLAS-INTEGRATION-013 — Apollo Winograd re-export removal [patch] — done

- Owner: Atlas integration; scope: `repos/apollo` gitlink and the provider-graph
  PM artifacts only.
- Acceptance: the gitlink names Apollo PR #50's merged default-branch commit,
  which removes the obsolete `mixed_radix::traits::ShortWinogradScalar`
  re-export and rewrites all callers to the canonical
  `components::winograd` module without changing FFT value semantics.
- Evidence: Apollo merge `c874281`; local locked Nextest 402/402,
  warning-denied Clippy, doctests, warning-clean rustdoc, source-residue scan,
  and provider audit pass. Hosted Python bindings, Rust workspace, and
  CodeRabbit pass; the external `recurseml/analysis` error is non-required.
- Closure: parent advances `repos/apollo` from `e2f905a` to `c874281`.

## ATLAS-INTEGRATION-014 — Hephaestus scan-limit theorem [patch] — done

- Owner: Atlas integration; scope: `repos/hephaestus` gitlink and the
  provider-graph PM artifacts only.
- Acceptance: the gitlink names Hephaestus PR #46's merged default-branch
  commit, which records the scan shared-memory bound and keeps KS-5b
  benchmark-triggered rather than adding an unneeded multi-pass kernel.
- Evidence: Hephaestus merge `93bc38e`; nightly formatting and core Nextest
  pass 48/48. The provider ADR records the theorem
  `shared_bytes = W * size_of(T)` and existing WGPU/CUDA `L=513`, `W=256`
  contracts witness the `L > W` path.
- Closure: parent advances `repos/hephaestus` from `3b68228` to `93bc38e`.

## ATLAS-INTEGRATION-016 — Apollo provider-lock refresh [patch] — done

- Owner: Atlas integration; scope: `repos/apollo` gitlink and provider-graph
  PM artifacts only.
- Acceptance: the gitlink names Apollo PR #51's merged default-branch commit,
  whose lockfile resolves Hephaestus `93bc38e`, Eunomia `a2e4f390`, Leto
  `6a0e297`, and Moirai `8a51b2a7` without local path or revision overrides.
- Evidence: Apollo merge `6dcb97c`; locked compile, 402/402 Nextest,
  warning-denied Clippy, doctests, warning-clean rustdoc, and provider audit
  pass. Hosted Python bindings, Rust workspace, and CodeRabbit pass; the
  external `recurseml/analysis` error is non-required.
- Closure: parent advances `repos/apollo` from `c874281` to `6dcb97c`.

## ATLAS-INTEGRATION-017 — Apollo Leto merge pin [patch] — done

- Owner: Atlas integration; scope: `repos/apollo` gitlink and provider-graph
  PM artifacts only.
- Acceptance: the gitlink names Apollo PR #52's merged default-branch commit,
  whose lockfile resolves both Leto packages to Atlas default merge
  `3ac0d203` rather than parent `6a0e297`.
- Evidence: Apollo merge `7303423`; `cargo metadata --locked --no-deps` and
  exact provider-tree comparison pass. Hosted Rust workspace, Python
  bindings, and CodeRabbit pass; the external analyzer error is non-required.
  The local fresh compile was blocked by stale peer test executables holding
  the shared target, while the preceding identical-tree sweep passed 402/402.
- Closure: parent advances `repos/apollo` from `6dcb97c` to `7303423`.

## ATLAS-INTEGRATION-011 — Hephaestus CUDA initialization closure [patch] — done

- Owner: Atlas integration; scope: `repos/hephaestus` gitlink and the
  provider-graph PM artifacts only.
- Acceptance: the gitlink names the merged Hephaestus default-branch commit
  that memoizes CUDA driver initialization and serializes only process-global
  context creation, while preserving concurrent transfers and kernels.
- Evidence: Hephaestus PR #45 merged at `3b68228`; the full CUDA suite is
  109/109 under `cargo nextest run -p hephaestus-cuda --locked`, including
  `concurrent_device_acquisition_is_safe`; warning-denied Clippy, doctests,
  and rustdoc pass.
- Closure: parent advances `repos/hephaestus` from `d0eafc8` to `3b68228`.

## ATLAS-INTEGRATION-010 — Hephaestus tiled scan provider closure [minor] — done

- Owner: Atlas integration; scope: `repos/hephaestus` gitlink and the
  provider-graph PM artifacts only.
- Acceptance: the gitlink names the merged Hephaestus default-branch commit
  that dispatches one shared-memory tiled scan workgroup/block per line in
  both WGPU and CUDA; theorem/spec and long-line value contracts remain in
  the provider repository.
- Evidence: Hephaestus PR #44 merged at `d0eafc8`; core nextest 48/48, WGPU
  nextest 140/140, CUDA nextest 108/108 when the independent
  `concurrent_device_acquisition_is_safe` Windows access violation is
  excluded, doctests, rustdoc, warning-denied Clippy, and real-device
  long-line scan contracts pass. ADR 0009 is the provider theorem SSOT.
- Closure: parent advances `repos/hephaestus` from `df33d4d` to `d0eafc8`.

## ATLAS-INTEGRATION-007 — RITK Apollo checkout pin [patch] — done

- Owner: Atlas integration; scope: `repos/ritk` gitlink and Atlas PM artifacts
  only.
- Acceptance: the Atlas gitlink names RITK `main` at `ffda3ec`, which checks
  out Apollo `157467e` for its dependency-alignment workflow and resolves
  `apollo-fft` 0.24 from that source.
- Evidence: RITK `main` at `ffda3ec` passes the cross-platform Nextest,
  Python 3.9–3.13, wheel, lint, dependency-alignment, and migration-audit
  workflows. This increment carries that verified head into the reproducible
  Atlas graph without a consumer-side fallback.

## ATLAS-INTEGRATION-008 — Apollo dispatch verification tree [arch] — ✅ done

- Owner: Atlas integration; scope: `repos/apollo` gitlink and provider-graph
  documentation.
- Acceptance: Apollo PR #46 merges the deep GPU dispatch verification leaf,
  keeps execution owned by Leto/Hephaestus, exposes no Apollo-owned raw WGPU
  path, and the Atlas gitlink advances to the merge commit.
- Evidence: Apollo merge `0b5d11c` (PR #48 canonical-export documentation
  after PR #47 PM closure); locked
  `apollo-fft` Nextest 393/393,
  warning-denied Clippy, warning-clean rustdoc, and provider audit 5/5.
- Closure: Atlas PR #18 merged at `56ad179`; Apollo `main` carries the
  documentation-only PR #48 merge `0b5d11c`, and the parent pin is current.

## ATLAS-INTEGRATION-009 — Kwavers hosted closure [patch] — ✅ done

- Owner: Codex `/root` takeover after the prior 60-minute claim expired;
  scope: the verified Kwavers default-branch head and the `repos/kwavers`
  gitlink only.
- Acceptance: required hosted checks pass for the clean default-branch head,
  and the parent advances only to that verified commit.
- Evidence: Kwavers PR #294 merged at `9eabc4e2`; its head `e84bb571e`
  contains the Leto-backed medium
  accessor removal, canonical abdominal geometry contract, Hephaestus
  backend-kernel ownership cutover, and the MVDR wall-clock assertion moved
  from the tarpaulin correctness lane into the Criterion benchmark. Legacy
  Migration Audit `29614208769` passes; local locked GPU Nextest passes 143/143
  with one hardware skip, ultrasound physics passes 18/18, and the benchmark
  target checks. The hosted Architecture Validation and CI/CD matrices retain
  generated-report coverage as a source gate. Architecture Validation
  `29614208770`, CI/CD `29614208862`, and Legacy Migration Audit
  `29614208769` pass; only external `recurseml/analysis` remains errored.
- Closure: the parent advances from `7c7d60f` to merged Kwavers `main`
  `9eabc4e2` in this increment.

## ATLAS-INTEGRATION-006 — Refresh provider heads [arch] — done

- Owner: Atlas meta; scope: Apollo, Hephaestus, Kwavers, Leto, and RITK
  gitlinks plus ADR 0020.
- Acceptance: the Atlas checkout graph resolves the verified Apollo,
  Hephaestus, Kwavers, Leto, and RITK default-branch heads;
  the provider-graph theorem and exact gitlink evidence are recorded.
- Evidence: Apollo `0b5d11c`, Hephaestus `df33d4d`, Kwavers `9eabc4e2`,
  Leto `6a0e297`, and RITK `ffda3ec` are the current provider heads; all
  required hosted checks pass.
- Closure: Atlas PR #15 merged at `29041d9`. Its RITK source checkout repair
  is carried by ATLAS-INTEGRATION-007; the current Kwavers #291 matrix remains
  the behavioral closure for the Apollo axis-transform path.

## ATLAS-INTEGRATION-005 — RITK lock-integrity pin [patch] — done

- Owner: Atlas integration; scope: `repos/ritk` gitlink and Atlas PM artifacts
  only.
- Acceptance: the gitlink names the merged RITK default-branch head after its
  lock metadata reconciles current Hephaestus patch entries.
- Closure: RITK PR #38 merged at `0dd71e52` after its full cross-platform
  Nextest, Python, wheel, lint, dependency, and migration-audit matrix passed.
  This pin carries that verified provider graph into Atlas without modifying
  a consumer-owned compatibility path.

## ATLAS-INTEGRATION-003 — provider-neutral GPU pin reconciliation [patch] — ✅ done

- Owner: Codex; scope: `repos/{hephaestus,CFDrs}` gitlinks and Atlas PM
  artifacts only.
- Acceptance: Hephaestus `main` supplies downlevel-complete typed device limits,
  CFDrs `main` owns no public raw WGPU adapter/feature/limits contract, and both
  gitlinks name the merged default-branch heads.
- Closure: Hephaestus PRs #40–#42 merged at `29ff2ff` (0.16.1); CFDrs PR #295
  merged at `7d4c9edf` (0.3.0). The provider exact-descriptor test, CFDrs
  GPU grouped nextest suites, warning-denied Clippy, and the major API
  classification passed before the parent pin advance.

## ATLAS-INTEGRATION-004 — CFDrs executable-example pin [patch] — ✅ done

- Owner: Atlas integration; scope: `repos/CFDrs` gitlink and Atlas PM artifacts
  only.
- Acceptance: the gitlink names the merged CFDrs default-branch head after
  its retained examples execute the provider implementation rather than emit
  static validation reports.
- Closure: CFDrs PR #296 merged at `a13f7f51`. It replaces the retained
  one- and two-dimensional examples with executable provider calls and
  deletes unexecutable three-dimensional/static-report examples. The parent
  gitlink advance records that merged contract without introducing a wrapper.

## ATLAS-INTEGRATION-001 — default-main reconciliation [patch] — ✅ done

Resolved the root metadata and gitlink merge against `main`. The integrated
tree preserves the current migration artifacts, adds the Helios stack entry,
and records conflicted submodules at commits reachable from their respective
default branches. Coeus is pinned at merge `093f31f`; Gaia is pinned at merge
`9e48102`.

## ATLAS-INTEGRATION-002 — merged-provider pin reconciliation [patch] — ✅ done

- Owner: Atlas integration; scope: `repos/{apollo,helios,ritk}` gitlinks and
  Atlas PM artifacts only.
- Acceptance: each pin names a commit reachable from its repository's remote
  default branch after all required provider PRs merge.
- Target heads: Apollo `f26369eb` (PR #44), Helios `04e496b7` (PR #5), and
  RITK `ec7cb832` (PR #37). RITK CI passes Rustfmt, dependency alignment,
  Clippy, migration audit, Python wheel, Python 3.9–3.13, and Ubuntu/macOS/
  Windows Nextest on the merged PR head. Atlas PR #9 merged this pin set at
  `e3380b6`.

## ATLAS-MNEMOSYNE-017 — Maximum-small deallocation audit [patch] — ✅ done

- Owner: Mnemosyne; Atlas scope: provider PR #25 and the `repos/mnemosyne`
  gitlink.
- Closure: PR #25 merged at `0012c4fad0c44c0a40ec4d36de68e7138ae218d8`.
  The matched default-feature Criterion row measures Mnemosyne `36.960 ns`
  versus RpMalloc `6.1139 ns` for `allocator deallocation latency/large/8192`.
  The opt-in branch probe pins the maximum-small same-owner free to
  `InPlaceSmall`; no page-list transition or large/huge classifier defect was
  found, so no speculative production mutation was made.
- Atlas pin closure: `4908208` advances `repos/mnemosyne` from `52cd5ee` to
  the merged provider head. Provider verification is recorded in the inner
  Mnemosyne PM artifacts; peer-owned submodule dirt remains outside this
  item.

## ATLAS-MOIRAI-016 — Cancellation-safe async wait queues [patch] — ✅ done

- Owner: Moirai; Atlas scope: cross-repo audit record only.
- Findings: `Condvar::wait` lost-notification window; `mpsc::SendFuture`/`RecvFuture`
  waker retention after cancellation; `oneshot::RecvFuture` rx_waker leak.
- Fixes applied to `repos/moirai/moirai-async/src/sync/`:
  - `condvar.rs`: pre-register waiter in `WaitQueue` while still holding the
    `MutexGuard`, using a `NoopWaker` placeholder replaced on first `poll`.
  - `mpsc.rs`: ID-based waiter tracking (`VecDeque<(u64, Waker)>`) with `Drop`
    impls that remove by ID on cancellation; 2 regression tests added.
  - `oneshot.rs`: `Drop for RecvFuture` clears `shared.rx_waker = None`.
- Evidence: `cargo check -p moirai-async` clean; `cargo nextest run -p moirai-async`
  82/82 passes (80 existing + 2 new cancellation regressions), no slow tests.
- Closure trigger reached: provider commit with focused regression evidence.

## ATLAS-RITK-654 — RITK native migration reconciliation [patch] — ✅ done

- Owner: Codex; scope: RITK PRs #31/#32/#33 and the `repos/ritk` gitlink.
- Acceptance: RITK PR #33 merged to `origin/main` at
  `17b84bdc18c2395d6329f3435ed3d860d1c72e00`; Atlas advances the gitlink to
  that merge commit. Final docs-head CI is green in run `29421402596`
  (Rustfmt, dependency alignment, Clippy, wheel smoke, and Linux/macOS/Windows
  nextest), run `29421402755` (Python 3.9–3.12 on Linux/macOS/Windows), and
  audit run `29421402503`.
- Performance and memory evidence: native statistics extrema now consume a
  fallible host slice instead of materializing a `Vec`; the xtask audit fixture
  roots use process-plus-sequence uniqueness and RAII cleanup. These are
  source/data-flow improvements; no unbenchmarked speedup is claimed.
- Residual: RITK retains 13 Burn manifests and 641 Burn-surface source files
  for dependency-ordered Coeus/Leto consumer cutovers (peer-owned sub-batches
  #3.g–#6). Three registration tests remain above the 30-second slow threshold
  and require profile-guided optimization. No shim or fallback is accepted as
  closure evidence.

## ATLAS-APOLLO-015 — RustFFT/WGPU provider promotion [major] — ✅ done

- Owner: Codex; scope: `repos/apollo` PR #8 and its Atlas consumer pins.
- Acceptance: Apollo PR #8 is reviewed with repository CI green, the provider
  state reaches `main`, and consumers replace temporary branch pins with the
  merged commit.
- Closure: Apollo PR #8 merged at `6e99a567c118f6bf5790f80346475b44db2c7555`.
  Authoritative CI run `29381809234` passed Rust format, Clippy, tests,
  doctests, documentation, provider audit, RustSec, dependency policy, and
  Python bindings. Coeus PR #209 subsequently merged the Mnemosyne 0.4,
  Hephaestus 0.13, WGPU 30, and Themis 0.10 provider constraints required by
  RITK.
- Closure: RITK PR #33 completed the consumer matrix against the merged
  Apollo/Coeus graph at `17b84bdc`; the external `recurseml/analysis` status is
  non-required.

## ATLAS-WGPU-030 — Provider ABI migration [arch] — done

- Owner: Codex; last-update: 2026-07-13; scope:
  `repos/mnemosyne`, `repos/hephaestus`, `repos/apollo`, their gitlinks, and matching cross-repo PM
  entries. Peer-owned CFDrs, Helios, RITK, and shared Cargo configuration are
  excluded.
- Acceptance: Mnemosyne removes the raw-pointer WGPU staging allocator contract
  that WGPU 30 cannot represent safely; Hephaestus owns one current WGPU ABI; its complete WGPU feature
  surface passes format, warning-denied Clippy, nextest, doctest, and rustdoc;
  Apollo consumes the pushed provider commit, removes obsolete dependency and
  advisory constraints, and repeats its release gates without duplicate WGPU
  source identities.
- Dependencies: current WGPU release/API metadata; existing Hephaestus and
  Apollo release branches; shared `D:/atlas/target` build cache.
- Closure: Mnemosyne `01e7de7` contains the WGPU allocator removal from
  `4a9d2a3`; Hephaestus `090611d`, Leto `8651dfc`, Moirai `c43f86a`, and Apollo
  `96e67a2` are pushed. Apollo 0.15 owns one WGPU 30 graph and passes 1029/1029
  Rust nextest cases, 34/34 Python cases, warning-denied Clippy and rustdoc,
  doctest, provider audit, RustSec, cargo-deny policy checks, and applicable
  pre-1.0 API checks.

## ATLAS-APOLLO-014 — Apollo release graph [arch] — done

- Owner: Codex; scope: `repos/{apollo,mnemosyne,moirai,hermes,leto,hephaestus}`
  gitlinks and matching parent PM entries.
- Acceptance: Apollo pins one exact, standalone-Git-resolvable Atlas provider
  graph; Rust, Python, API, supply-chain, and documentation gates pass; all
  provider and Apollo commits are pushed before Atlas advances their gitlinks.
- Closure: Apollo `a4742bb` and provider commits Mnemosyne `eb0d941`, Hermes
  `51c530f`, Moirai `b2f3732`, Leto `1b125ce`, and Hephaestus `f726742` are
  pushed and release-gated; Atlas integration commit `e7f27a7` records their
  gitlinks. The completed `ATLAS-WGPU-030` increment supersedes this historical
  WGPU 26 release graph.

> **2026-07-09 current-tree reconciliation**: the direct production
> `nalgebra`/`ndarray`/`burn`/Tokio/Rayon removal front is closed in CFDrs.
> The next cross-repo correctness slice is provider-first ownership of the
> CFDrs 2D GPU Laplacian in Hephaestus: remove the falsely generic `f32` WGSL
> boundary and silent CPU fallback, then leave `cfd-core`/`cfd-math` as thin
> typed consumers. This candidate is not claimed while Hephaestus remains on
> the active `ks5-cholesky-panel` branch. Kwavers and RITK each have a smaller
> subtractive cleanup candidate, but their current dirty migration streams own
> those files; no atlas-meta source edit crosses those claims.

---

## Cross-repo architect coordination ledger

Three CR-class items carried from `docs/audit/2026-07-02-cross-repo-integration-audit.md` (`L71-149`). Each is self-contained and gates specific consumer-side migrations below.

| ID | Class | Title | Owner repo (provider land) | Supertypes | Consumer land unlocked |
| --- | --- | --- | --- | --- | --- |
| **CR-4** | `[major]` | Rebase `coeus-core::Scalar` + `leto-ops::Scalar` over `eunomia::NumericElement` as the universal supertrait (single SSOT) — **✅ CLOSED 2026-07-09** (eunomia `57d7789`, coeus `2b3f820`, leto PR #31 merge `d9e8ac9`; ADR 0005 Accepted; re-verified 2026-07-22: `leto-ops/src/domain/scalar.rs:11` and `coeus-core/src/dtype/traits.rs:295` carry `Scalar: NumericElement`; consumer unlocks tracked and closed in batches #2/#3). Delete the vocabulary that already lives on `NumericElement` (`zero`/`one`/`to_f64`/`from_f64`/`from_usize`/`sqrt_val`/`abs_val`); keep the backend-specific slice-kernel surface (`add_slice`/.../`max_slice`, `gemv_*`, `tiled_gemm`, `axpy_rows`, leto-ops `from_usize`). See `atlas/docs/adr/0005-eunomia-scalar-ssot.md` for the proof that `RealField` (float-only) cannot be a universal `Scalar` supertrait (would orphan `coeus_core::Int` for i8/u8/.../u64). | `coeus`, `leto` (joint) | `eunomia` is doctrine holder | kwavers `RealField` nalgebra → eunomia; CFDrs `cfd-math` solver-chain RealField seam; ritk `Burn::Module → coeus::Module` rebind |
| **CR-2** | `[arch]` | Consolidate `#[global_allocator]` to a single binary-only registration. Strip from `cfd-core`, `ritk-core`, `moirai/lib`. Pass `Mnemosyne` handles via DI to library callers. | `cfd-core`, `ritk-core`, `moirai` (joint) | `mnemosyne` is allocator holder | Library composition stays provider-neutral; binaries own allocator policy — **✅ CLOSED 2026-07-18** (`cfd-core` ✅, `moirai` ✅, `ritk-core` ✅; zero `#[global_allocator]` in all three library crates) |
| **CR-1** | `[arch]` | Delete `apollo/crates/apollo-ghostcell` standalone GhostCell reimplementation; redirect all apollo sites to `melinoe::MelinoeCell` (with `brand_scope!` mint). | `apollo`, `melinoe` (consumer) | `melinoe` is brand doctrine holder | All brand-borrow contention becomes provider-exclusive — **✅ CLOSED 2026-07-07** (Apollo commit `50029b7` deletes `crates/apollo-ghostcell`; `repos/moirai/Cargo.toml` aligned to `melinoe = 0.8.0`; focused nextest `-p apollo-validation melinoe` 2/2 green and `-p apollo-sft -p apollo-radon` 43/43 green; `find_path repos/apollo/crates/apollo-ghostcell/**` returns zero files 2026-07-20 re-confirm; full evidence at `gap_audit.md` L1429-1430) |

### Provider extension register

These cross-cut consumer migration but live in provider land. Each requires its own [minor] backlog entry in the owning provider repo:

| Provider | Missing surface | Substrate | Tracked in |
| --- | --- | --- | --- |
| `leto` | ✅ `Quaternion<T>` Add/Sub/Neg/Mul&lt;T&gt;/Div&lt;T&gt; + `try_inverse` + `to_rotation_matrix`; ✅ `FixedMatrix&lt;4,4&gt;` determinant/try_inverse + generic Add/Sub/Neg/Mul&lt;T&gt;/Div&lt;T&gt;/Assign. **Verified 2026-07-14**: 229/229 tests green, clippy `-D warnings` clean. | math | `leto/backlog.md` |
| `leto-ops` | ✅ `CscMatrix<T>`, `CooMatrix<T>`, `lu_batch`; `ExecutionStrategy` trait — all verified present at `leto/crates/leto-ops/src/`. | ops | `leto/backlog.md` |
| `moirai-async` | ✅ `mpsc::channel`, `oneshot::channel`, `Condvar`, `Mutex`, and `#[moirai::main]` exist. `ATLAS-MOIRAI-016` cancellation audit closed: Condvar lost-notification race fixed (pre-register waiter while holding guard), mpsc/oneshot waker leaks fixed (Drop impls with ID-based cleanup), 82/82 nextest pass with 2 regression tests. | async | `moirai/docs/backlog.md` |
| `apollo` | ✅ RustFFT-free differential oracle — pure O(N²) DFT reference replaces rustfft. `b291003` on `codex/remove-rustfft`. Workspace `rustfft = "6.4.1"` pin removed; `external-references` feature removed; dev-dep and vs_rustfft benchmark removed; xtask benchmark runner stripped. | validate | `apollo/backlog.md` |
| `eunomia` | ✅ eunomia-gpu deleted (E-019); folded into `hephaestus::DialectScalar`. README clean — no aspirational claims about eunomia-gpu. | basis | `eunomia/backlog.md` |
| `coeus` | ✅ `scatter_add` exists at Tensor/Var/Python; all 6 comparison ops (eq/ne/lt/gt/le/ge) exist. `Dataset`/`DataLoader` deferred per "if PINN dataset paths require" condition — no PINN path in current scope requires them. | autograd | `coeus/docs/backlog.md` |
| `hephaestus` | ✅ `f64` DialectScalar impls (Wgsl `"f64"`, CudaC `"double"`) + 24 GPU vector type impls via macro. **Verified 2026-07-14**: 47/47 nextest green, clippy `-D warnings` clean. Remaining: `wgpu::PipelineCache` integration (WG-P8); CU-P1 async-stream-overlap. | gpu | `hephaestus/backlog.md` |

---

## Migration batches (vertical slices)

Ordered per Definition-of-Ready (provider SSOT closes first). Each batch is self-contained, has observable pass conditions, and respects the WIP limit (one in-flight merge-affecting item per micro-sprint). Cross-repo item as policy: one batch is **the** item; commits ride under the established `codex/kwavers-atlas-integration` branch through that batch's owner.

### Consumer-side (kwavers / CFDrs / ritk)

| Batch | Class | Crate | Surface | Pre-reqs | Pass condition (value-semantic) | File-line scope (illustrative) |
| --- | --- | --- | --- | --- | --- | --- |
| #1 | `[patch]` | `kwavers-solver` ([side path RTM/elastic PDE](file_pattern)) | `par_for_each` Zip → `moirai-parallel::par_mut().enumerate()` (62 sites); `Zip::indexed` → `par().enumerate()` (24 sites) | (none — confirmed by `moirai-parallel/src/lib.rs:106-181` tan rename) | ✅ **CLOSED 2026-07-12** at peer commit `5913f2946`: zero `par_for_each` source sites, zero `burn::` hits, zero `nalgebra` hits, zero `use ndarray` imports; `kwavers-solver/Cargo.toml` clean of `ndarray`/`rayon`/`burn` (substrate is `leto` + `leto-ops` + `moirai-parallel`); `cargo nextest run --workspace --exclude kwavers-driver --no-fail-fast --lib` 5117/5119 pass (2 timeouts are pre-existing KW-WATCH-002 perf on the 90s `elastic-fwi` profile override — peer-stream perf, NOT a Batch #1 regression). Atlas-meta `repos/kwavers` gitlink advanced `01643ed9 → 5913f2946`. | `crates/kwavers-solver/src/inverse/reconstruction/seismic/rtm/inherent/{wavefield,propagation,mod,laplacian,imaging,illumination}.rs`; `crates/kwavers-solver/src/forward/nonlinear/{kuznetsov,westervelt_spectral}/...`; `crates/kwavers-solver/src/forward/{elastic/swe/int, pstd/ext, multiphysics/fluid_structure}/...`; `crates/kwavers-physics/src/acoustics/...`; `crates/kwavers-physics/src/optics/polarization/linear.rs` |
| #2 | `[minor]` | `CFDrs/cfd-math` ([ite solver finish](file_pattern) + `cfd-1d`/`cfd-3d`/`cfd-validation`) | nalgebra → let, nalgebra-sparse → leto-ops `CsrMatrix`; covariance solves / geometry / finite-element typedefs | CR-4 (eunomia SSOT) so `RealField → eunomia::RealField` is universal | `cargo nextest run -p cfd-math -p cfd-3d -p cfd-1d -p cfd-validation` green; xtask scanner delta shows `nalgebra` allowlist contracts under cfdec-solver chain, cfd-3d fem/libnodes, cfd-1d linear_system and cfd-validation geometry; `nalgebra-sparse` allowlist contracts to zero | `cfd-math/src/linear_solver/{chain, preconditioners/{*, ilu/*, multigrid/*, schwarz, ssor}}.rs`; `cfd-3d/src/fem/{element, projection_solver, leto_bridge, solver, stabilization, stress, quadrature, shape, fluid}.rs`; `cfd-3d/src/{bifurcation, trifurcation, venturi, serpentine, ibm}/**`; `cfd-3d/src/vof/{cavitation, reconstruction}.rs`; `cfd-1d/src/solver/core/{convergence,linear_system,matrix_assembly,state,workspace,anderson,solver_detection}.rs`; `cfd-validation/src/{geometry, benchmarks, literature, manufactured, numerical, adaptive_mesh, tests}/**` |
| #3 | `[minor]` | `ritk` ([Provider-side Burn trait rebind](file_pattern)) | `ritk_core::{Image, Transform, Interpolator}` → `coeus_core::{ComputeBackend, Scalar}`; `ritk-spatial::{Vector,Point,Direction}` lose `burn::module::{Module,AutodiffModule}+burn::record::Record` impls; `ritk-image::types::Image<B,D>` re-exports exit Burn-keyed facade | CR-4 so eunomia `Scalar/RealField` is universal | `ritk-image::native::Image<T: Scalar, B: ComputeBackend, const D: usize>` becomes the canonical re-export; `cargo nextest run -p ritk-{core, image, filter, registration, segmentation, transform, interpolation}` green; `cargo tree --workspace -i burn-wgpu`, `cargo tree --workspace -i burn-cuda`, and `cargo tree --workspace -i burn-rocm` each return zero (Burn only CPU NdArray backend remains per DEP-496-01) | `ritk-core/src/{image/types,transform/trait_,interpolation/trait_}.rs`; `ritk-spatial/src/{vector,point,direction,spacing}.rs`; `ritk-image/src/types.rs` + `ritk-image/src/lib.rs:11` re-export line; `ritk-wgpu-compat/src/lib.rs` (`apply_row_chunks` `B:Backend` bound → `B:ComputeBackend`); per-filter `*/new(B::Device)` constructors |
| #4 | `[minor]` | `kwavers-solver` ([PINN Burn → Coeus](file_pattern)) | `burn::backend::NdArray<f32>` ⇒ `coeus-core::MoiraiBackend`; `burn::optim::{SGD,Adam,AdamW,lr_schedule::*}` ⇒ `coeus-optim::*`; `burn::module::Module` ⇒ `coeus-nn::Module`; `burn::record::Record` ⇒ `coeus-nn::Record`; `burn::tensor::*` ⇒ `coeus-tensor::*`; ~325 source lines + ~17 top-level dev-dep files | CR-4 + #3 + `coeus-autograd/scatter_add` extension | `cargo nextest run -p kwavers-solver --features pinn` green; per-physics trainer residual gradient matches golden reference within neum-compensated epsilon (derived from reduction depth × sqrt(N) per current `es::BatchModern` chain); kwavers top-level `Cargo.toml:138` `[dev-dependencies] burn = "0.19"` flips to deps via `coeus` (or top-level burn demoted fully) | `crates/kwavers-solver/src/inverse/pinn/**` (~80 files; cite-referenced inside the inventory in checklist.md); top-level `crates/kwavers/{benches,examples,tests}/**` (17 files); `kwavers-solver/Cargo.toml:42` feature set; `kwavers/Cargo.toml:138` dev-deps |
| #5 | `[arch]` | CR-1: `apollo-ghostcell` deletion + `melinoe::MelinoeCell` rebind (provider land) — single coordinated commit | (See provider-extension register above) | (None — provider-only action) | (See CR-1 row above) | `apollo/crates/apollo-ghostcell/src/lib.rs` removed; every apollo consumer routed via `melinoe::MelinoeCell`; `cargo nextest run -p apollo-* --features melinoe` green; `cargo miri test -p melinoe` green |
| #6 | `[arch]` | CR-2: Consolidate `#[global_allocator]` (provider land) — single coordinated commit across `cfd-core`, `ritk-core`, `moirai/lib` | (See CR-2 row above) | (None) | (See CR-2 row above) | Library registry sites reduced; per-binary (`kwavers-cli`, `cfd-cli`, `helios`, `ritk-cli`, `mnemosyne-gbench`, etc.) keeps or replaces registration; `cargo build -p cfd-core` without `mnemosyne` feature succeeds |
| #7 | `[arch]` | CR-4: `coeus-core::Scalar` + `leto-ops::Scalar` rebase to eunomia supertraits (provider land) — **STATUS: ✅ CLOSED 2026-07-09. eunomia (`57d7789` ✅), coeus (`2b3f820` ✅), leto (`86d366bc` ✅ on `main` via PR #31 merge `d9e8ac9`)** | (See CR-4 row above) | (None) | (See CR-4 row above) | eunomia: `eunomia/crates/eunomia/src/traits/numeric.rs` doc clarified (ZERO/ONE/sqrt/abs/to_f64 stay FloatElement for float paths); Complex<T>/isize/usize implementations added. coeus: `coeus/coeus-core/src/dtype/traits.rs` (`Scalar: NumericElement + CpuUnaryDispatch + Pod + Rem + Clone`); 64-file coeus call-site disambiguation landed. leto: `leto/crates/leto-ops/src/domain/scalar.rs` `pub trait Scalar: NumericElement` rebind; redundant UFCS items removed (ZERO/ONE/add/sub/mul/div/bitand/bitor/bitxor/count_ones/to_f64); slice kernels given default bodies; `from_usize` retained. `Cargo.toml` workspace version `0.35.1 → 0.36.0`. Resolution (a) applied (additive rebind is structurally infeasible per `atlas/checklist.md` structural-infeasibility addendum + E0034 evidence). Verification (pre-merge on `codex/leto-cr4-ssot-rebind`, 5 files / 196 +/-622 net subtraction): `cargo nextest run -p leto-ops` 270/270 green + `-p leto` 189/189 green + 8 doctests green + clippy `-D warnings` green on `--lib --tests` scope. Pixel/range/structural artifact: net 466-line subtractive consolidation (no vocab duplication remains). RG-verified zero `Scalar::add/sub/mul/div/ZERO/ONE/bitand/bitor/bitxor/count_ones/to_f64` UFCS references in `crates/`. |
| #8 | `[minor]` | Provider extension (provider land): ✅ `leto` (Quaternion ops, FixedMatrix<4,4> ops) — verified; ✅ `hephaestus` (DialectScalar f64 + GPU vectors) — verified; ✅ `moirai-async` (mpsc/oneshot/Condvar/Mutex/`#[moirai::main]`) — verified; remaining: `apollo`, `eunomia`, `coeus`, `leto-ops` | (See provider-extension register above) | (Threads across consumer migration; file as individual [minor] items in owning repos) | (See register above) | tracked separately in `repos/<provider>/backlog.md` |

### Token batch ordering

Batches #5, #6, #7 are the [arch] provider-SSOT gates. Per `decision_policy` nternals:

1. **#7 first** (CR-4 eunomia SSOT) — **ALL SIDES ✅ CLOSED 2026-07-09**. eunomia (`57d7789` ✅), coeus (`2b3f820` ✅), leto (`86d366bc` ✅ on `main` via PR #31 merge `d9e8ac9` — Resolution (a): rebase onto origin/main post-PR-#30, `Scalar: NumericElement` supertrait, redundant UFCS items removed). Unblocks #2 (CFDrs nalgebra finish), #3 (ritk Burn rebind), and #4 (kwavers PINN Burn → coeus). ADR `0005-eunomia-scalar-ssot.md` (status **Accepted**) describes the actual rebase; `RealField` is NOT a universal `Scalar` supertrait (would orphan `Int`); `NumericElement` is. ADR signed off via autonomy mode per `interaction_policy`.
2. **#5 second** (CR-1) — Pure provider cleanup; no consumer call sites depend on it for the migration below.
3. **#6 third** (CR-2) — Library-vs-binary layering. **cfd-core ✅, moirai ✅ landed** (2026-07-10). **ritk-core ✅ committed** (`ba6da3a5`, 2026-07-14). All sites resolved.
4. **#1 fourth** — `kwavers-solver` residual Rayon → Moirai. Self-contained. Calls CTE immediately after a clean CR-4. ✅ **CLOSED 2026-07-12** — kwavers peer commit `5913f2946` (`perf(kwavers-solver): Migrate solver tree to moirai parallel iterators`) drives source-site count to zero: `par_for_each`=0, `burn::`=0, `nalgebra`=0, `use ndarray`=0, `kwavers-solver/Cargo.toml` clean of `ndarray`/`rayon`/`burn` (substrate is `leto` + `leto-ops` + `moirai-parallel` only). `cargo nextest run --workspace --exclude kwavers-driver --no-fail-fast --lib`: 5117/5119 pass, 2 timeouts (pre-existing KW-WATCH-002 abdominal-preprocessing perf on 90s `elastic-fwi` profile override — peer-stream perf, NOT a Batch #1 regression). `cargo check -p kwavers-solver --features pinn` PASSES (Batch #4 co-verified closed). Atlas-meta `repos/kwavers` gitlink advanced `01643ed9 → 5913f2946`. Sole residual is the `kwavers-solver/Cargo.toml` `ndarray` `rayon` feature gate, flagged separately in the peer commit body — manifest detail tracked as a kwavers-peer follow-up. Batch #4 (`kwavers-solver PINN Burn → Coeus`) is also closed at this HEAD (co-verified).
5. **#2 fifth** — Largest consumer body (176 CFDrs source files). Depends on CR-4. ✅ **CLOSED 2026-07-05** — inner CFDrs HEAD advanced `0f578e1af110c5b8536476174bf266bf8b812c37` → **`d58d1fe320d046816425e1d20d16735fcfee7995`** via a single Atlas-provider migration push (subject `refactor(cfdrs): Atlas-provider migration push (Leto CSR + Eunomia scalar + Hephaestus GPU + cfd-math / cfd-2d / cfd-3d / cfd-1d / cfd-validation consumer cones)` — 752 modified + 19 added files, 51,857 insertions / 22,087 deletions, ~2,500 tests pass, 0 warnings). Atlas-parent submodule pointer advance recorded at parent HEAD `51922a56c4d4acab3dbe786b90cc5acf92e22277` (`chore(atlas): Advance CFDrs submodule pointer to d58d1fe3`).
6. **#3 sixth** — ritk Burn keyed-trait rebind. ✅ **CLOSED 2026-07-18**.
7. **#4 seventh** — kwavers-solver PINN Burn → coeus. ✅ **CLOSED 2026-07-12**.
8. **#8 last** — Provider extensions; tracked in provider repos separately; own claim stream.

### Batch #3 sub-batches (ritk Burn-trait rebind — 6 atomic commits per ADR 0012)

`Batch #3` (`[minor]` ritk Burn-keyed trait rebind) is decomposed into 6 atomic sub-batches per [`atlas/docs/adr/0012-ritk-burn-trait-rebind.md`](docs/adr/0012-ritk-burn-trait-rebind.md) (Accepted 2026-07-06). Each sub-batch widens the Atlas surface OR narrows the Burn surface — never both in one commit — atomic-boundary discipline per ADR 0012 §Decision. Reserved inner tag: `ritk/atlas-migration-push/batch3` (per ADR 0010 §Decision §"Per-batch name pattern").

**Historical sub-batch #3 framework (opened 2026-07-06; fully consumed
2026-07-18)**: the following per-crate queue records the original atomic
decomposition. PR #42 consumed #3.a–#3.g and #4–#6; PR #43 closed the ledger,
so no reservation or open queue remains.

| Sub-batch | Class | Atomic-boundary disposition | Closeout per sub-batch | Status (2026-07-09) |
|-----------|-------|------------------------------|-----------------------|---------------------|
| #1 | `[patch]` | **Additive** — Atlas-typed parallel trait surface (`TransformAtlas<T,B,D>`, `InterpolatorAtlas<T,B>`, `ResampleableAtlas<T,B,D>`) + `pub use native::Image as AtlasImage;` re-export. Burn-keyed surface untouched. | `cargo nextest run -p ritk-{core,image,filter,registration,segmentation,transform,interpolation,spatial}` green + `cargo tree --workspace -i burn-wgpu` (and `cuda`, `rocm`) zero | **closed 2026-07-06** |
| #2 | `[patch]` | **Subtractive-by-documentation** — soft docstring deprecation ONLY on Burn-keyed surface. No `#[deprecated]` attr (would emit 671-file compile-warning cascade). | (same gates as #1) | **closed 2026-07-06** |
| #3 | `[minor]` | **Subtractive-by-conversion (7 per-crate queue)**: Atlas-typed migrator test-source ports from `burn_ndarray::NdArray<B>` to `AtlasImage<T: Scalar, B: ComputeBackend, D>` over `coeus_tensor::Tensor<T, MoiraiBackend>`. Per-crate atomic-boundary discipline per ADR 0012. | (same gates as #1) | **✅ CLOSED 2026-07-18** — All sub-batches consumed by PR #42 `f01b1643` (1298 files, -59482 lines) + PR #43 `b4be04ca` (closeout docs). burn_surface.allowlist deleted; all Burn/ndarray deps removed. |
| #4 | `[patch]` | **Subtractive-by-impl-removal** — `ritk-spatial::{Vector, Point, Direction, Spacing}` drop `burn::module::{Module, AutodiffModule}` + `burn::record::Record` impls. Atlas-side impls only IF `coeus-nn` PINN consumer code requires. | (same gates as #1) | **✅ CLOSED 2026-07-18** — Consumed by PR #42 atomic cutover. |
| #5 | `[major]` | **Subtractive-by-dep-strip** + **subtractive-by-reexport** — Cargo dep strip `burn` + `burn-ndarray` from manifests; `pub use types::Image;` re-export path switch; `apply_row_chunks<B: Backend>` removal. **THIS IS THE ONLY SUB-BATCH ALLOWED TO DELETE OR RENAME `[dependencies]` LINES.** | (same gates as #1) + `cargo semver-checks release -p ritk-core -p ritk-image -p ritk-spatial` authoritative classification | **✅ CLOSED 2026-07-18** — Consumed by PR #42 atomic cutover. |
| #6 | `[patch]` | **Subtractive-by-allowlist-contract** — `xtask/burn_surface.allowlist` reset on sub-batch #5 re-enter; CI scan gates tighten: zero `burn::tensor::Backend`-bound public symbols + Atlas-only backend trait assertion. | CI gate asserts `coeus_core::ComputeBackend` is the only atlas-side backend trait in the cross-crate re-export graph | **✅ CLOSED 2026-07-18** — burn_surface.allowlist deleted in PR #42. |

### Historical in-flight claims (superseded)

> This section preserves dated coordination snapshots. It does not describe
> current work; the live board at the top of this file is authoritative.

- Atlas-meta branch: `codex/kwavers-atlas-integration` (PM artifacts only).
- Atlas-meta claim scope (this turn): `backlog.md`, `checklist.md`, `gap_audit.md` at the atlas workspace root; no per-repo files touched at the atlas-meta layer.
- **Mnemosyne fixed Themis pin** [patch]: **DONE** — PR #11 merged as `f95d372`; Mnemosyne pins Themis 0.10 at `18807bb`, with metadata, clippy, 288/288 nextest, doctests, and docs green.
- **Leto Themis co-evolution and provider extension** [patch]: **DONE** — PR #32 merged as `8d39f58`; the lock graph, cache-level contract, quaternion interpolation, and fixed-matrix value contracts are verified by the complete local gate.
- **Hermes fixed Themis pin** [patch]: **DELIVERED / MERGE-BLOCKED** — PR #6 commit `6080aa4` pins Themis 0.10 at `18807bb`; all CI checks pass except the pre-existing Miri allocator failure reproduced on Hermes main. The PR remains open pending that independent correctness residual.
- Atlas-meta last landed (codex session): `61931faf` (RITK Batch #3 sub-batch #1 sync + kwavers/Burn risk surfacing, 2026-07-06, layered atop peer commits `e82fe14c`, `4a04cad1`, `4b71cda9`, `3062ce1b`, `c5f2a84e`, `61931faf` itself; followed by peer `5adf4a27` "Helios closure triage" 2026-07-06 13:37). This turn: peer landed `c6b845f81` Batch #4 slice 2 (`burn_wave_equation_2d` dependency graph: 12-family native Burn→Coeus rewrite; `burn::` line-hits 315→186, file-count 144→80). See risk #8 below.
- **This codex session (2026-07-08, Bulk-provider-surface round-1 + round-2 + round-3)**: three sequential bulk-advance blocks landed (round-1 `2e1c4f20d`→`274a6a961`→`a12d1dd77` for apollo/coeus/hermes/melinoe/ritk + themis pointer refreshes; round-2 `5d3395e95` + `715cff24e` + `02da06611`→`ab71f08ad`→`36acbbca9` for hermes-r2/coeus/cascade + multi-PM-reconciliations + `.gitignore hardening); round-3 `ad6cf57d4`→`1828ea14a`→`852de7129`→`769b70a67`→`1fe3c0e56` for apollo/eunomia/hermes/leto/mnemosyne). See `gap_audit.md` row 13 for the per-submodule advance record + provenance triples + branch-context notes (especially hermes on `rescue/detached-simd-numa-work` divergent 17 commits ahead of `origin/main`, NOT peer-WIP at the parent gitlink level; mnemosyne sjump `482670d` → `98a02b6` reflects the Miri alloc/free HIGH-PRIORITY finding at `eff(backend)` + `fix(backend)` + `docs(gap_audit)` chain). **Net alignment state post-`1fe3c0e56`**: all 12 actively-tracked submodules (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, kwavers) ALIGNED at inner HEAD with zero DIVERGED gitlinks — the first all-aligned state since the `e0bf55684` cross-tree reclamation audit. **ritk-python test suite (47/47)** compiled+passed at committed inner HEAD `1f49278c` (value-semantic asserts — see `gap_audit.md` row 154 bulk-advance unblock evidence). **KW-CV-001 watchpoint re-affirmed ACTIVE** at inner HEAD `35ee01076`: trigger `(cd /d/atlas/repos/kwavers && git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l)` returns 0; peer continues slice-by-slice Batch #1 + Batch #4 work without explicit closeout commit. **Atlanta-meta path forward**: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit (per `concurrent_agents` disjoint-scope rule); the round-3 block leaves kwavers at the peer-tracked HEAD `35ee01076` (atlas-meta gitlink already aligned, not divergent, just not watching for closure-style advances here — the KW-CV-001 watchpoint owns that path). **Branch context**: this turn's round-3 work landed under `codex/kwavers-atlas-integration`; `36acbbca9` `.gitignore` hardening prevents transient root scratch artifacts from re-entering `git status --short` (no body-scratch file was created for any of the 5 round-3 chore commits, per the user's signal-change-in-the-tree batch ceremony convention from ADR 0010 §Per-batch name pattern; each commit body authored inline via subject + body `-m` pairs + a final `-m` provenance-triple block citing row 11 dynamic-SHA extraction). **Cross-references**: `gap_audit.md` row 13 (per-submodule advance record with prior-SHA + derived-full-SHA + inner-chore-subject for each of the 5 round-3 modules); `checklist.md` §Next micro-sprint for the round-3 line-item summary. **Residual risks** (tracked in `gap_audit.md` row 6 row-268–270 kwavers sub-bullets): kwavers 267 dirty files at inner HEAD `35ee01076` is peer-WIP, not reclaimable from atlas-meta; kwavers Batch #1 closure condition (zero `par_for_each` source sites) is NOT yet met (41 sites across 15 files per `gap_audit.md` line-93); kwavers Batch #4 closeout condition (zero `burn::` source hits + zero `crates/kwavers-solver/Cargo.toml:42` burn dev-deps + `burn.rs`/`burn_compat` deletion) WAS met at `05500930c` per the line-92 sub-bullet (file deletion + manifest strip landed on the peer stream). The next bulk-advance round (round-4) is contingent on either inner HEAD churn (peer-WIP-after-push divergence) OR KW-CV-001 firing for kwavers.
- **This codex session (2026-07-06, Helios closure)**: `c5f2a84e` closed the direct Helios H-061/H-062 dependency slice by removing the unused `num-traits` workspace edge, removing the aggregate dicom-rs `ndarray` feature edge, adding the local Melinoe patch required by patched Gaia's `melinoe` 0.8.0 edge, and syncing Helios PM evidence. Concurrent peer commit `61931faf` then landed the RITK Batch #3 sub-batch #1 Atlas-parent pointer advance; preserve that pointer state.
- **This codex session (2026-07-06, Helios/RITK DICOM ownership)**: RITK inner commit `8f8360ff` adds `ritk-dicom::{DicomTag, tags, DicomAttributeRead}` so downstream DICOM geometry/modality-LUT attribute reads are RITK-owned. Helios H-061 now routes production DICOM parsing, typed attributes, transfer-syntax lookup, and pixel decode through `ritk-dicom`; dicom-rs remains direct only as a dev-dependency for synthetic Part 10 fixture generation. Helios H-063 is filed for the remaining `helios-imaging` audit: generic medical-image I/O/registration/toolkit operations move upstream to RITK; radiation-domain MVCT projection/reconstruction kernels stay in Helios.
- **This codex session (2026-07-07, RITK DEP-497-01 dead-dep strip)**: `repos/ritk` commits `7a66d1ee` (strip unused production `burn` dep from 17 leaf crates: `ritk-{cli,core,filter,io,jpeg,metaimage,mgh,minc,model,nifti,nrrd,png,registration,segmentation,snap,statistics,tiff,transform,vtk}`; `burn-ndarray` dev-dep retained where sub-batch #3 per-crate test ports are still open) + `00d57005` (checklist sync), pushed to `origin/main`. Distinct from Batch #3 sub-batch #5 (`[major]` full Burn Cargo strip + `Image<B,D>` re-export) per ADR 0012 — this is a non-breaking dead-edge removal, no version bump. Verified: `cargo nextest run` across the 19 touched crates 4258/4258 green, `cargo clippy --workspace --all-targets -D warnings` clean, `cargo fmt --check` clean for touched crates, `cargo doc --no-deps` no new warnings. Fixed an incidental `clippy::doc_lazy_continuation` false-positive in `ritk-model/src/ssmmorph/encoder/tests.rs`. Residual risks filed in `repos/ritk/checklist.md` (2 pre-existing broken intra-doc links in `ritk-filter`; a full-workspace-nextest-only timeout in `ritk-snap::pacs_ops` reproduced only under full-parallel resource contention, isolated run passes in 2.1s — not a hang). Atlas-meta `repos/ritk` gitlink advanced to `00d57005` via the dynamic-SHA-extraction convention (gap_audit.md row 11).
- **`repos/kwavers` `codex/kwavers-core-moirai-parallel` — peer ryancinsight ACTIVE** (inner HEAD `05500930c` 2026-07-07 19:11, `[ahead 0, behind 0]` of `origin/codex/kwavers-core-moirai-parallel` per inner `git rev-list --left-right --count`; atlas-meta `HEAD:repos/kwavers` gitlink pinned at `7235d464afb04dfec62dee1cd8e6e8d660b54250` lagging inner HEAD by 37 commits). State at inner HEAD `05500930c` per T1 verification: **Batch #4 (kwavers-solver PINN Burn → Coeus) source-residual is now ZERO** — canonical inner chore `8b128c478` "Remove dead burn compatibility shim and drop burn dependency" + slice 3+ commits drained the residual; `crates/kwavers-solver/src/burn.rs` + `burn_compat` module ABSENT; `rg -n '\bburn\b' -g '*.toml' .` zero hits in `crates/kwavers-solver/Cargo.toml` + root `Cargo.toml`; `rg -l '\bburn::' crates --type rust` zero hits across the kwavers source tree (was 186 line-hits / 80 files at `b605e2e74`, full clean at `05500930c`). **Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai)**: `crates/kwavers-{solver,physics}/Cargo.toml:{24,20}` now read `ndarray = { version = "0.16", features = ["serde"] }` (per peer `702e4f125` "drop unused ndarray/rayon feature from kwavers manifests"; the `rayon` feature strip is landed, contradicting the prior stale paragraph that read `features = ["rayon", "serde"]`); residual is now **41 `.par_for_each()` sites across 15 files** in `crates/kwavers-solver/src` (down from 84 sites / 28 files at `b605e2e74`, −51%) — concentration in `forward/{elastic/swe/{integration/integrator/mod,stress/divergence}, nonlinear/{kuznetsov/{diffusion,nonlinear,numerical,operator_splitting/mod,solver/{model_impl,rhs},spectral,workspace}, westervelt_spectral/spectral}, pstd/extensions/{elastic,elastic_orchestrator/pml/mod}, multiphysics/fluid_structure/{interface,solver/struct_impl}}`. Closeout state: no formal `closeout` / `final` / `completion` commit in the last 30 inner commits — peer lands Batch #4 + Batch #1 slice-by-slice without explicit closure commits. **Atlas-meta continues to defer parent-side pointer advance** for `repos/kwavers` until a kwavers-side final closeout commit lands (per `concurrent_agents` disjoint-scope rule). `burn.rs` + `burn_compat` facade deletion + Cargo.toml strip are LANDED on the inner peer stream (lifting the surrogate pre-condition cited in sub-batch #5 standing reminder per `docs/adr/0012-ritk-burn-trait-rebind.md`). See `gap_audit.md` row 6 kwavers sub-bullets L268-L270 for the kwavers-side reconciliation record.
- Neighbor claim streams to honor (disjoint from kwavers Batch #1, also DO NOT touch): `repos/moirai` `refactor/remove-dead-subsystems` (26 dirty paths — moirai source forbidden); `repos/leto` `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile (14 dirty paths — leto source forbidden); `repos/coeus` `main` (19 dirty paths); `repos/eunomia` `main` (`acos`/`asin`/`atan` peer queue, 7 dirty paths); `repos/apollo` (235), `repos/CFDrs` (79), `repos/gaia` (5), `repos/hermes` (46), and `repos/melinoe` (13) carry in-flight peer claims. `repos/helios`, `repos/ritk`, `repos/hephaestus`, `repos/mnemosyne`, and `repos/themis` are clean of inner dirty paths after the Helios/RITK DICOM ownership closure and prior pointer-sync commits.
- The moirai-parallel API surface for kwavers Batch #1 already exists: `for_each_chunk_pair_mut_enumerated_with`, `for_each_chunk_triple_mut_enumerated_with`, `for_each_chunk_quad_mut_enumerated_with`, `enumerate_mut_with`, `for_each_index_with` (moirai-parallel `src/ops.rs:281,335,408,125,155`). No moirai source change is required for Batch #1 closure; the consumer-side helpers in `crates/kwavers-physics/src/parallel.rs` already cover 1-mut + N-imm and 2-mut + N-imm arities, with 3-mut + N-imm and 4-mut + N-imm indexed zips (visible in `kwavers-solver/src/forward/elastic/swe/{integration/integrator/mod.rs,stress/divergence.rs}` and `forward/pstd/extensions/elastic.rs` and `forward/pstd/extensions/elastic_orchestrator/split_field_step/{stress,velocity,mod}.rs`) as the remaining helper-coverage gap.

- **This codex session (2026-07-08, Bulk-provider-surface round-4 — post-OOB `6902d2e92` re-probe)**: 7 atomic chore captures in this turn. The OOB consolidation commit `6902d2e92` ("chore(atlas): Advance repos/hephaestus pointer to 240b260 (CU-P6/CU-M3)") absorbed my staged round-4 reset state, capturing `hermes` `5ad1b58 → c7b17b02` + `leto` `a9572da → 86d366bc` (batched LU / CSC sparse format / CG/GMRES iterative solvers — unblocks kwavers-solver Bulk-solver migration closure target) bundled into a single `e3223094a`. The remaining per-crate captures split into one-atomic-chore-per-crate for cleanliness:
  - `6a598da91` kwavers `35ee01076 → 89117870` (inner `Migrate kwavers Complex/ndarray types to eunomia/leto atlas crates` — Phase-3 closure of Complex<f32>/f64, ndarray Array, coefficient paths onto eunomia+leto substrates; replaces nalgebra/ndarray/numeric-complex stack in kwavers-core domain)
  - `0e34ae082` coeus `e36f95f → ec69a6a` (inner `fix(coeus-dist): close TOCTOU race in TCP test port allocation` + co-emitted `342f38d` MS-406/407 reconciliation; TOCTOU between bind and listen eliminated in coeus-distributed harness)
  - `045291499` ritk `1f49278c → e75d8748` (inner `Add Module/AutodiffModule impls for DisplacementField and DisplacementFieldTransform` — DIRECTLY resolves the displacement_registration_test failure tracked in row 6; Sub-batch #5 RITK-spatial-rebind closure per ADR 0012)
  - `4a4cf928a` coeus `ec69a6a → 006f2a7` (inner `feat(coeus-nn): add MaxPool3d/AvgPool3d benchmark rows (G-043)` — criterion bench registry extension for 3D pooling kernels)
  - `4b7f4804e` kwavers `89117870 → 09c645f30` (inner `Migrate kwavers-core/source/signal/grid/field from ndarray to leto` — Phase-4 closure of kwavers-core domain crates source/signal/grid/field off ndarray onto leto's NDArray substrate; follow-on to `89117870`)
  - **Net alignment state post-`4b7f4804e`**: all 13 actively-tracked submodules ALIGNED at inner HEAD with zero DIVERGED gitlinks. Seven bulk-provider pointers advanced in this session cycle (well above round-3 cadence). KW-CV-001 watchpoint re-probed at every commit — still 0; peers continue `Migrate *.rs from ndarray to leto` subject phrasing, not `closeout`/`final`/`completion`/`close-batch`.
  - **Atlas-meta action posture**: round-4 captured all in-session churn. Awaiting peer's next kwavers/ritk commit; either KW-CV-001 fires for kwavers OR slice-7+ launches to re-open round-5 capture. Either path stays in observation mode; no source-tree work concrete to atlas-meta.

- **This codex session (2026-07-08, mid-session test/example validation sweep) collapsed to canonical L104** — the orphan duplicate of the user-directive sweep block at former L275-L281 + the prior stale ROUND-3 dedup claim in L283-tombstone are reconciled by the present chore: the canonical `### In-flight claims (per concurrent_agents)` L104 carries the full T1 evidence (ritk nextest 47/47; CFDrs 2177/2177+1335/1335 subsets; kwavers 1-site `plugin/mod.rs:204` test-mock slip); the L283 tombstone is updated below to reflect this collapse. Mid-session test/example issues resolved by **peer-owned** per-`concurrent_agents` disjoint-scope: the kwavers `Boundary<eunomia::Complex<f64>,3>` trait-rewire at `crates/kwavers-solver/src/plugin/mod.rs:182+204` and the `fn to_leto3` dead-code warning in `crates/kwavers-simulation/src/dispatch/elastic_pstd.rs:8` are peer-stream fixes; atlas-meta does not touch `repos/kwavers/crates/kwavers-solver/src/plugin/mod.rs` or any other peer-claimed source.

#### Historical closure templates — Atlas Batch #3 sub-batches #4–#6

> All three templates were consumed by RITK PR #42 and tombstoned by PR #43
> on 2026-07-18. They remain below only as design-history evidence; none is a
> standing reminder, prerequisite, or next-session instruction.

These templates preserve the original atomic commit shapes and prerequisites
from ADR 0012. They are historical evidence only; no roll-up surfacing or
future-session action remains.

- **Sub-batch #4 [patch] — Standing reminder**: `ritk-spatial rebind — drop burn::module::{Module, AutodiffModule} + burn::record::Record impls`. **Atomic inner commit shape**: a single inner-RITK commit that strips the four `burn::module::*` + `burn::record::Record` impls on `repos/ritk/crates/ritk-spatial/src/{vector,point,direction,spacing}.rs:7` and (conditionally) adds `impl<T: Scalar, B: ComputeBackend> coeus_nn::Record for *` ONLY IF the downstream PINN consumer code in `kwavers-solver/src/inverse/pinn/**` or `helios-imaging/**` requires it (cross-walk Batch #4 §Progress in `atlas/checklist.md` for the in-flight audit; otherwise sub-batch #4 is a strict-removal commit with no Atlas-side replacement per ADR 0012 §Decision §Sub-batch #4). **Standing pre-reqs**: (a) Batch #3 sub-batch #3 fully closed — i.e., the 7 per-crate queue `#3.a..#3.g` has landed (each with its own test-from-`burn_ndarray::NdArray<B>`-to-`AtlasImage<T: Scalar, B: ComputeBackend, D>` over `coeus_tensor::Tensor<T, MoiraiBackend>` port) and `xtask/burn_surface.allowlist` source-rows have been progressively decremented per per-crate closure; (b) the impact audit of `burn::module::{Module, AutodiffModule}` removal on `kwavers-solver` Batch #4 PINN code paths is completed and posted to `kwavers/gap_audit.md` (the auto-`ModuleMapper` / `GradientExtractor` / `GradientApplicator` pattern from the `coeus_nn::load_parameters` extension must already be in place, OR the per-PINN code-path-side adapter lives inline at the PINN consumer site, NOT on the spatial carriers); (c) cooldown — if any per-crate sub-batch in `#3.{b..g}` transitively touches `ritk-spatial`, it must be closed before `#4` lands to preserve the atomic-boundary invariant (no legacy Burn-keyed reference survives into the post-#4 tree). **Pre-flight gate per session**: `cargo check -p ritk-spatial --all-targets` + `cargo doc -p ritk-spatial --no-deps` warning-clean + `cargo clippy -p ritk-spatial --all-targets -- -D warnings`.

- **Sub-batch #5 [major] — Standing reminder (mandatory semver-checks pre-release gate)**: `RITK Burn Cargo dep strip + Image<B,D> re-export path`. **Atomic inner commit shape**: a single inner-RITK BREAKING CHANGE commit that (i) deletes `burn` + `burn-ndarray` from `repos/ritk/Cargo.toml:69-72`, `ritk-core/Cargo.toml:23-24` (dev-deps), `ritk-image/Cargo.toml:9-10`, `ritk-wgpu-compat/Cargo.toml:8`, and per-crate `burn` + `burn-ndarray` dev-dep cleanup from `crates/ritk-{filter,transform,interpolation,registration}/Cargo.toml:23,30`; (ii) switches the public re-export at `repos/ritk/crates/ritk-image/src/lib.rs:11` from `pub use types::Image;` to `pub use AtlasImage as Image;` (verify which `atlas/checklist.md` §Batch #3 §Plan step 1 prefers — alternative is `pub use native::Image;`); (iii) removes `apply_row_chunks<B: Backend>` from `repos/ritk/crates/ritk-wgpu-compat/src/lib.rs:40+` (no async replacement; docstring-only if a docstring is needed for archival context); (iv) updates all `Image<B, D>` references in source across the workspace (this is the [major] breaking event per RITK semver). **MANDATORY pre-release confirmation** (per ADR 0012 §Decision §Sub-batch #5 + the `versioning` section of `atlas/AGENTS.md`): `cargo semver-checks release -p ritk-core -p ritk-image -p ritk-spatial` MUST run pre-merge and MUST authoritative-classify the commit body as `[major]` (the table-row label `[major]` in `atlas/backlog.md` §Batch #3 sub-batches is provisional; `cargo-semver-checks` is the ground truth). **If `cargo-semver-checks` reports `[minor]` or `[patch]` instead, the sub-batch #5 commit message `[major]` annotation MUST be downgraded by the actual outcome** (an observable regression per `atlas/checklist.md` §Per-batch atomic commit + version bump rules). The CHANGELOG entry under `## [Unreleased]` uses `cargo-semver-checks`'s verdict, NOT the provisional table-row class label. **Standing pre-reqs**: (a) sub-batch #4 closed OR skipped (sub-batch #4 may be omitted if the kwavers Batch #4 PINN audit confirms no Atlas-side `coeus_nn::Record` replacement is required — the omit path is documented per ADR 0012 §Decision §Sub-batch #4); (b) kwavers Batch #4 (`burn::module::Module` → `coeus_nn::Module`) `burn.rs` + `burn_compat` facade deletions are LANDED on the `repos/kwavers` peer stream so the cross-crate risk #8 exposure is closed (cross-walk `atlas/gap_audit.md` surfacing risk #8 + the peer's `c6b845f81`-style "per prior direction not to build burn-compat shims" framing); (c) per upstream-consumer audit, no peer claim stream touches `repos/ritk/{Cargo.toml, src/lib.rs:11}` per `concurrent_agents` disjoint-scope rule (the absence can be verified by `git -C repos/ritk status --short` returning zero on the inner-RITK working tree prior to staging the sub-batch #5 commit). **Pre-flight gate per session**: `cargo semver-checks release -p ritk-core -p ritk-image -p ritk-spatial` (mandatory pre-release verdict — the only source of truth for the version-bump rule) + `cargo build -p ritk-core -p ritk-image -p ritk-spatial --release` + `cargo test --doc -p ritk-core -p ritk-image` + `cargo tree --workspace -i burn`, `-i burn-ndarray`, `-i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` ALL return zero.

- **Sub-batch #6 [patch] — Standing reminder (downstream of sub-batch #5)**: `xtask/burn_surface.allowlist contract reset + CI scan gates tighten`. Cross-link to ADR 0012 §Decision §Sub-batch #6: source entries are removed; the allowlist file becomes the post-migration SSOT and is archived or rewritten. CI scan gates tighten: new CI gate asserts zero `burn::tensor::Backend`-bound public symbols; new CI gate asserts `coeus_core::ComputeBackend` is the only atlas-side backend trait in the cross-crate re-export graph. CHANGELOG `[patch]` per RITK (CI-only). **Atomic inner commit shape**: a single inner-RITK CI-only commit that (i) regenerates `xtask/burn_surface.allowlist` content against the post-`#5 xtask/burn_surface_audit` regeneration (the contract-file becomes the post-migration SSOT — the pre-`#5` generated-from-`burn::` allowlist entries parcel to migration-done rows); (ii) adds a new CI scan gate that asserts zero `burn::tensor::Backend`-bound public symbols in the cross-crate re-export graph; (iii) adds a second CI scan gate asserting `coeus_core::ComputeBackend` is the only atlas-side backend trait in the cross-crate re-export graph (i.e., every public `B: Backend` constraint has been re-routed to `B: ComputeBackend` for atlas-side surface). Cross-link: README + the Atlas-meta CI pipeline (if it exists in CI providers); the new gates are authored in the atlas-meta peripheral repo (`repos/atlas`) which carries the meta-CI pipeline, NOT on the inner-RITK repo directly — the inner-RITK commit body references the atlas-meta commit SHA that introduces the gates. **Standing pre-reqs**: (a) sub-batch #5 MUST be RE-ENTERED first — the sub-batch #6 atomic commit's body references the sub-batch #5 inner SHA in its message ("Corresponding to ritk/atlas-migration-push/batch3 tag-advance inner SHA <sub-batch-#5-sha>" — the tag annotation body also updates at this point). The atomic-boundary discipline holds because sub-batch #5 closed + tag-advanced leaves the workspace clean of the Burn-keyed surface, making sub-batch #6 a pure-CI-tool change with no behavioural code surface; (b) `xtask/burn_surface_audit` runs against the post-sub-batch-`#5` `cargo tree -p ritk -i burn-ndarray` reset state and reports zero Burn-keyed source-files per crate (the sub-batch #6 commit body MUST include this audit's complete output as evidence); (c) the new CI scan gates themselves are exercised pre-commit by `bash xtask ci --strict-atlas-only --dry-run` + `bash xtask ci --strict-backend-trait --dry-run` (the dry-run output is captured in the commit body as evidence). **Pre-flight gate per session**: `xtask/burn_surface_audit` (regenerates the allowlist contract) + `bash xtask ci --strict-atlas-only --dry-run` + `bash xtask ci --strict-backend-trait --dry-run` all return their expected zero-output invariants.

### Cross-engineering verification — `hephaestus-cuda` eigen.rs Complex upload

The earlier `fb83d009` residual risk is stale in the checked-out `repos/hephaestus` `ks5-cholesky-panel` tree. Source inspection on 2026-07-06 shows `hephaestus-cuda/src/application/decomposition/eigen.rs` maps `leto_ops::eigenvalues(&view)` output into `num_complex::Complex<f32>` with `Complex::new(z.re, z.im)` before `device.upload(&e_host)`, while `hephaestus-core::ComputeDevice::upload<T: bytemuck::Pod>` remains the generic transfer seam. Focused compile evidence: `rustup run nightly cargo check -p hephaestus-cuda --features decomposition` completed successfully against local `leto`/`leto-ops` `0.36.0`. Evidence tier: compile/build verification plus source inspection; no runtime CUDA device execution was claimed.


---

## Out-of-scope (explicit)

- **`**Spec composition layers**` updated later (e.g. `cfd-validation`, testing frameworks)**: not part of this migration; filing as separate backlog if it's not in CFDrs's own backlog.
- **HELIOS/Python binding for kwavers**: Phase-3 rich-image scoping state; deferred-until `kwavers-python` intent-bledged beyond current net-style top-level.
- **GPU backend complete production rollout across ritk-model**: PPG-model is reserved-wave per `docs/audit/2026-07-02-hephaestus-gpu-substrate-audit.md` HIGH-sev list; out of scope until defect closure.

### Atlas-root working-tree dirty triage (2026-07-06)

The Atlas-root `D:/atlas` working tree carries 29 dirty files (19 tracked-modified + 10 untracked) outside the migration-push closure chain. The vast majority have been classified as real Atlas-meta PM artifacts and committed in five atomic batches on 2026-07-06 (see commit history since `2c38db42`). The remainder is explicitly recorded below as **out-of-scope for the Atlas-parent pointer-advance ritual** — they live in scopes the Atlas-parent cannot reach (submodule internals, foreign root-level scratch, or non-submodule external dirs) and require separate-flow cleanup that is staged outside this branch's claim scope.

#### A. Root-level scratch (retracted 2026-07-06)

Cleanup chore commit on Atlas-meta deleted `nul` (Windows-reserved-name artifact on disk; the on-disk deletion API was blocked by `PermissionError` on the basename collision — see commit body for blocked paths; defense-in-depth `.gitignore` prevents future reproductions from re-entering `git status --short`) + `script.py` (root-level Python scratch that pre-existed the cleanup and was absent pre-chore per `os.path.exists`; the `.gitignore` entry ensures future re-generation path-respecting deletion can apply). Both items are now `.gitignore`-d so future reproductions cannot re-enter the Atlas-root working tree.

#### B. External / non-ASCII-dir content (retracted 2026-07-06)

Cleanup chore commit deleted `repos/SynthSeg/` (standalone git clone of the SynpthSeg brain-segmentation research project — has its own `.git/`, NOT in `.gitmodules`; deletion via `shutil.rmtree` with `onerror` handler that chmods + retries after Windows pack-file collisions on `.git/objects/pack/*`) + `repos/report/` (non-ASCII-filename dir, deletion via `shutil.rmtree` succeeded directly). Both items are now `.gitignore`d. Note: the prior-analysis claim that `repos/SynthSeg/` had "no `.git` of its own" was a stale read; the on-disk state had its own `.git/` and required the onerror handler for clean removal.

#### C. Submodule-internal dirtiness (uncommitted in inner repos — out of Atlas-parent reach)

These show up in Atlas-root `git status` as `M repos/<name>` (parent-tree entry marked dirty because the inner submodule's tree contains modifications relative to the gitlink pinned here). They are **cleanable only by an inner-submodule commit + parent-tree gitlink advance**, NOT by Atlas-parent commit. Each row is the inner-dirty count + inner HEAD as of 2026-07-06. No reclaim from Atlas-meta; these belong to the claim streams holding the inner repos.

| Submodule | Inner dirty count | Inner HEAD | Inner branch / claim stream | Triage decision (2026-07-06, per ADR 0011 §Decision §Leg 3) | Atlas-meta artifact action |
|-----------|---:|------|------|--------------------------------|------------------------------|
| `apollo`         | 235 | `f1ddf7a`     | peer claim stream `codex/apollo-atlas-migration` (WIP) | **Path B — OOS-next-sprint**: 235-file pre-CR-5 surface; queued behind ADR 0010 `apollo/atlas-migration-push/batch5` reservation | stay in §C with Batch-#5 reservation cross-walk |
| `CFDrs`          | 79  | `d58d1fe3`    | peer claim stream on `codex/cfdrs-atlas-migration` after Batch #2 closure | **Path B — OOS-next-sprint**: Batch #2 remains closed at `d58d1fe3`, but current source dirtiness has reappeared after the closure push and belongs to the CFDrs inner-repo claim stream; do not retract this row from §C until the inner tree is clean again or a new CFDrs commit lands | stay in §C; keep Batch #2 closure cross-link, but current dirty-tree accounting is live |
| `coeus`          | 19  | `b2beec3`     | peer claim stream on `main` (source + docs; includes dtype, tensor, Python embedding, and parity-test files) | **Path B — OOS-next-sprint**: not a PM-only closure-tail; source files are dirty and must land inside the Coeus claim stream with Coeus package gates | stay in §C as peer-active; no Atlas-meta source reclaim |
| `eunomia`        | 7   | `57d7789`     | peer claim stream (CR-4 closed; CR-EUNOMIA-COMPLEX ⏳ `acos/asin/atan` PR-queue per ADR 0006; **eunomia-side retroactive-closed per ADR 0006 §Decision §1 Path B**) | **Path C retroactive-closed 2026-07-06** (ADR 0006 §Decision §1 Path B additive `ComplexField::zero()`/`::one()` defaults landed at eunomia HEAD `57d7789`); 7-dirty reclassified as peer's UNRELATED `acos`/`asin`/`atan` PR-queue (per `## In-flight claims` Neighbor claim streams). Cross-walk §C eunomia reclassification bullet below + `D:/atlas/docs/coordination/2026-07-06-eunomia-csr-scalar-phantom-blocker.md` + ADR 0008 §Decision §0 reframed. | retract from §C on next §-triage pass; the prior `Path B — OOS-next-sprint` classification was based on a stale ADR 0008 §0 Variant A / unseal `NumericElement` framing that ADR 0006 explicitly REJECTED |
| `gaia`           | 5   | `8f4a862da`     | peer claim stream `refactor/migrate-to-leto-geometry` | **Path B — OOS-next-sprint**: source and benchmark files are dirty (`src/application/csg/arrangement/classify.rs`, `benches/csg_performance.rs`), so the PM files cannot be committed as a source-disjoint Atlas closeout | stay in §C as peer-active; no split closeout |
| `hermes`         | 46  | `1b5392a`     | peer claim stream | **Path B — OOS-next-sprint**: 46-file scattered across `hermes-simd-*` crates + ADR footer updates; moderate-size, multi-domain peer-active | stay in §C; peer-active |
| `kwavers`        | 27  | `400c32624`   | peer claim stream `codex/kwavers-core-moirai-parallel` ACTIVE | **Path B — OOS-next-sprint**: dirty count drained from 132 to 27; remaining Batch #1/#4 surface still belongs to the kwavers inner-repo claim stream and stays behind ADR 0010 `kwavers/atlas-migration-push/batch1` reservation | stay in §C; cross-walk ADR 0010 reservation; drain-counter annotation now `-575` from the original 602-file capture |
| `leto`           | 14  | `626ebf538`     | peer claim stream `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile | **Path B — OOS-next-sprint**: 14-file ACTIVE peer stream (disjoint from CR-4 leto side per `concurrent_agents`) | stay in §C; disjoint with CR-4 leto side |
| `melinoe`        | 13  | `7ec0a44`     | peer claim stream | **Path B — OOS-next-sprint**: 13-file `crates/halo/` + 4 src sync; CR-1 consumer (brand doctrine holder for `apollo-ghostcell` deletion); cross-crate work with apollo CR-5 reservation | stay in §C; CR-1 cross-link |
| `moirai`         | 26  | `9b7881f`     | historical peer claim stream `refactor/remove-dead-subsystems` | **Superseded:** CR-2 closed 2026-07-18 with zero `#[global_allocator]` sites across the three library crates | historical snapshot only |
| `ritk`           | 0   | `8f8360ff`    | local follow-up committed after the clean nine-commit Batch #3 migration sequence, then advanced by Atlas-parent pointer commits | **Path C closed for risk #1 and Helios DICOM ownership**: inner commit `65a1a0fd` removes stale Burn `wgpu` default; inner commit `d7a940b5` adds the Batch #3 sub-batch #1 Atlas-typed parallel trait surface; inner commit `8f8360ff` adds typed DICOM attribute reads for downstream imaging consumers | pointer advanced by this Helios/RITK DICOM ownership commit; keep broader Batch #3 closure separate until package gates are current |
| **Σ** | **471 inner files** (fresh `git status --short` sweep; Helios and RITK now clean) | — | — | **2 retroactive/closed rows + 0 source-disjoint partial closeouts + 9 stay-OOS-next-sprint rows** | **No source-disjoint Atlas-meta closeout remains; next source work belongs inside the active inner-repo claim streams** |

#### D. Helios/RITK DICOM ownership cleanup (closed 2026-07-06)

Commit `c5f2a84e` closed the six-file Helios direct dependency slice under `repos/helios/**`: H-062 removed the unused direct `num-traits` workspace edge, H-061 removed Helios' unused aggregate dicom-rs `ndarray` feature edge while leaving pixel decoding owned by `ritk-dicom`, and the local Melinoe patch now lets patched Gaia resolve its `melinoe` 0.8.0 edge during Helios validation. Follow-up RITK commit `8f8360ff` closes the remaining production DICOM boundary drift by moving common DICOM image tag vocabulary and typed parsed-object attribute reads into `ritk-dicom`; Helios now consumes that API for parsing, typed attributes, transfer-syntax lookup, and pixel decode. Current Atlas-root status is expected to have no committed `repos/helios/**` direct-file dirtiness after this pointer-advance commit; the remaining imaging boundary is H-063 (`helios-imaging` audit for generic toolkit operations that belong in RITK).

#### E. Remaining future-correction hooks (post-2026-07-06)

§A and §B retractable future-correct clauses resolved in the 2026-07-06 cleanup chore commit on Atlas-meta (the 4-pattern `.gitignore` append + the on-disk SynthSeg + report deletions + the 4-pattern future-proofing). §C is partially-triage-classified per ADR 0011 §Decision §Leg 3 OOS-record cadence (sub-routine "Initial record" + "Post-resolution §-E update when stay-OOS-next-sprint"). Total submodule-internal dirty now stands at 471 inner files after the Helios direct-file closure (`c5f2a84e`), RITK Batch #3 sub-batch #1 pointer advance (`61931faf` to `d7a940b5`), Helios/RITK DICOM ownership pointer advance (`8f8360ff`), and the refreshed peer-WIP counts. This triage leaves three open forward-looking hooks:

- **§C retroactive-closings (Path C rows)**: 2026-07-06 triage retracted the zero-dirty `hephaestus`, `mnemosyne`, and `themis` rows from §C because they are no longer submodule-internal dirtiness. `CFDrs` was not retracted: re-verification shows 79 inner dirty paths on `codex/cfdrs-atlas-migration`, so the Batch #2 closure remains recorded while the current dirty tree stays tracked as a live CFDrs claim stream. The remaining Path C row is `eunomia`, which is covered by the separate reclassification bullet below.

- **§C partial-closeable queue (Path A candidates for next claim stream)**: empty after re-verification. `coeus` and `gaia` both contain source/benchmark dirtiness, so their PM files cannot be split into source-disjoint commits without hiding peer-active implementation context. `ritk` left this queue after inner commit `65a1a0fd`. Recommended pre-commit gate for future claim streams: `git -C repos/<X> status --short` once before the inner commit, to confirm no peer-stream claim landed in the interim.

- **§C stay-OOS-next-sprint (Path B rows)**: 9 submodules post-2026-07-06 refresh — `apollo` (235, Batch #5 reservation `apollo/atlas-migration-push/batch5` per ADR 0010; pre-CR-5 surface), `CFDrs` (79, Batch #2 closure remains closed at `d58d1fe3`, but current dirty paths belong to the live CFDrs inner-repo stream), `coeus` (19, source + docs peer stream), `gaia` (5, source/bench + PM peer stream), `hermes` (46, peer-active scattered), `kwavers` (27, Batch #1 + Batch #4 + Phase-1B reservations), `leto` (14, ACTIVE peer stream `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile), `melinoe` (13, CR-1 consumer cross-crate with apollo Batch #5; brand doctrine holder), `moirai` (26, Batch #6 reservation `cfd-core+ritk-core+moirai/atlas-migration-push/batch6` per ADR 0010; `refactor/remove-dead-subsystems` ACTIVE). Removed: `eunomia` (retroactive-closed; 7 dirty files are unrelated `acos`/`asin`/`atan` PR-queue), `ritk` (clean at `8f8360ff` after the DICOM ownership pointer advance), and `helios` (direct dependency plus DICOM ownership slices closed; H-063 filed for future `helios-imaging` audit). No Atlas-meta reclaim per disjoint-scope rule (ADR 0011 §Decision §Leg 2). Each row stays in §C until its owning claim stream emits a pointer-advance to Atlas-parent.

- **§C eunomia row reclassification (post-2026-07-06 phantom-blocker discovery)**: the §C `eunomia` row above has been reclassified from `Path B — OOS-next-sprint` to `Path C retroactive-closed (eunomia-side per ADR 0006 §Decision §1 / Path B additive `ComplexField::zero()`/`::one()` defaults landed at HEAD `57d7789`)`. The 7-dirty is now re-attributed to the peer's UNRELATED active WIP stream (`acos`/`asin`/`atan` PR-queue per § In-flight claims Neighbor claim streams section) — OUT of §C scope on the next §-triage pass per ADR 0011 §Decision §Leg 3 \"Resolution branch\". The residual Phase-1B is kwavers-side per ADR 0008 §Decision §0 (reframed per the discovery); cross-walk `D:/atlas/docs/coordination/2026-07-06-eunomia-csr-scalar-phantom-blocker.md` for the full verification matrix.

- **§D (Helios/RITK DICOM ownership closure)**: closed by `c5f2a84e` plus RITK `8f8360ff` and this Helios consumer reroute; current Atlas-root status has no committed `repos/helios/**` direct-file dirtiness after the pointer-advance commit, and H-063 tracks the remaining `helios-imaging` generic-toolkit audit.

- **`nul`** (whose on-disk deletion API was blocked by Windows-reserved-device-name PermissionError on this build): the `.gitignore` defense in this chore commit prevents future `nul` reproductions from re-entering `git status --others`. The on-disk file may still surface via `dir` from bash contexts but is gitignored; admin `cmd /c del /F /Q nul` or Windows-reboot may be required for actual on-disk removal. Filed for the next codex-session restart-handler.


### RN-CC-05 (transitive parent-SHA chain breach detection + audit-discipline establishment)

Filed by `chore(atlas): Roll-up review-nit RN-CC-05 -- transitive parent-SHA chain breach detection` (post-`536366e`). Retroactively addresses code-reviewer-minimax-m3 NIT surfaced in the post-`536366e` cycle: commits `93a0723177` + `a96d46d7294` declared the RN-CC-04 discipline but inline-cited the parent rather than carrying a `Parent-SHA:` line-block at the top of body. Per NO-AMEND, retroactive body repair is forbidden; the breach is disclosed across 4 docs files + recorded in the RN-CC-05 commit body. Parent-SHA: forward-propagation audit discipline: `rg -F "Parent-SHA:" gap_audit.md backlog.md checklist.md docs/coordination/` yields >=2 line-hits; `git log --grep "Parent-SHA:" --oneline` yields >=2 entries. Self-discipline demonstration: `74df54d4f963b96d1b642ce89e77c9b019ad3de7` + `74df54d4f` + `536366e` + this RN-CC-05 chore carry line blocks at top of body; `93a0723177` + `a96d46d7294` need forward-session transparency (this row).

## Review nit rolling list (forward-looking improvement tracking, 2026-07-08)

> Persistent review-improvement tracking items surfaced by the
> post-`91896c477` code-reviewer pass on the Atlas architectural
> directive framing chore. Each nit is annotated: ID, scope,
> severity, source-chore, fix status, suggested follow-up.
> Future chore-cycles reference this list when templating
> `docs(atlas):` commits so the same drifts don't recur.

| ID | Nit | Severity | Source chore | Status | Follow-up |
| --- | --- | --- | --- | --- | --- |
| **RN-01** | CR-2 (open; Batch #6) citation error -- mnemosyne row cited "per CR-2 (open; Batch #6)" but CR-2 is **OPEN** per Surfacing risks row 1.2 (Batch #6 reserved), not CLOSED. | factual | `91896c477` | **FIXED in `b29cfa24b`** (mnemosyne row changed to "per CR-2 target axiom [open; Batch #6]") | file-wide rg `per CR-2 (open; Batch #6)` on subsequent docs-only chores; extend fix to any other inverted citations |
| **RN-02** | 11+3 stack split -- the monolithic `### Stack (13 atlas crates)` table conflated 11 providers with 3 consumers in one 14-row table. | structural | `91896c477` | **FIXED in `b29cfa24b`** (split into `### Provider stack (11 atlas crates)` + `### Consumer migration targets (3 simulation suites)`) | template future `Atlas-stack` table sections with the provider/consumer split pattern from the start; split mnemosyne+themis row when allocator-pair semantic is involved |
| **RN-03** | Gitlink SHA truncation -- table used 7-char truncated SHAs (`98a02b6...`, `37ff12d5...`, etc.) which break grep-ability and don't match the 40-char convention used elsewhere in `gap_audit.md`. | presentational | `91896c477` | **FIXED in `b29cfa24b`** (all 14 table SHAs now full 40-char live from `git ls-files --stage`) | prefer full 40-char SHA in all `docs(atlas):` table cells; only allow truncation when the SHA is genuinely abbreviated (e.g., an inner HEAD short-SHA in narrative prose) |
| **RN-04** | FRONT-MATTER sync -- `gap_audit.md` lines 1-11 blockquote enumerated 4 record-types but the new `## Atlas architectural directive` section added a 5th without updating the enumeration. | presentational | `91896c477` | **FIXED in `b29cfa24b`** (item 5 appended to front-matter blockquote: `Atlas architectural directive (2026-07-08); consolidator framing -- stack table, migration targets, design principles, constraints, bulk-migration priority order`) | when adding a new top-level section to `gap_audit.md`, also update lines 1-11 blockquote enumeration; consider automating via a pre-commit check |

**File-wide open follow-ups surfaced by the post-`b29cfa24b` review**:

- **CR-2 file-wide citation scope (RN-01 scope extension)**: a file-wide
  `rg -n 'per CR-2 (open; Batch #6)' gap_audit.md` post-patch may surface
  additional inverted citations outside the table row that was fixed
  in RN-01 (e.g., CR-class status cell, Surfacing risks row 1.2
  narrative, cross-cutting notes). **Status**: not yet verified
  post-patch; a follow-up patch chore should run the rg + extend the
  fix to any other hits.
- **Subsection naming collision (RN-02 cosmetic extension)**: the new
  `### Consumer migration targets (3 simulation suites)` (table)
  sits adjacent to the existing `### Migration consumer targets (3 in
  flight)` (prose). The two names are lexically adjacent on
  "consumer migration targets" -- a grep footgun. **Status**: not
  yet renamed; recommend renaming the new table to `### Consumer
  simulation suites (3 in flight)` for disjoint-name grep-ability.
- **Prose subsection inner-HEAD SHA uniformity (RN-03 scope
  extension)**: the preserved prose subsection (`### Migration
  consumer targets (3 in flight)`) still uses 9-char short-SHAs
  (`inner HEAD 05500930c`, `702e4f125`, `d58d1fe3`, etc.); the new
  directive table uses 40-char SHAs. **Status**: deliberate scope
  choice -- not yet upgraded for visual consistency. Either
  upgrade in a follow-up patch, or document the inconsistency
  explicitly in body-scratch as a preservation choice.
- **Body-scratch subject parent-SHA anchor (RN-04 audit-discipline
  extension)**: subject of `b29cfa24b` is `Patch 4 review nits on
  directive chore (...)` and doesn't grep-match `91896c477` (parent
  SHA). **Status**: noted as a `concurrent_agents` precedent for
  future subject-pattern discipline; recommend appending `(parent
  <SHORT-SHA>)` to chore subject or putting parent-SHA on
  body-scratch line 1.

**Audit-lifecycle note**: this rolling list persists until (a) a
follow-up chore closes all 4 RN items above (RN-01..RN-04 already
FIXED in `b29cfa24b`; 4 follow-up extension nits remain open), or
(b) a future chore re-classifies any item as RESOLVED-by-design
via explicit `docs(atlas): Mark RN-XX as RESOLVED-by-design (...)`
commit. Re-probe cadence: per `docs(atlas):` chore landing that
touches `gap_audit.md` PM surface.

**Cross-link**: see `gap_audit.md` `## Atlas architectural directive
(2026-07-08)` (line 12) for the source-chore context + `## Surfacing
risks` for the open follow-ups' parent audit-class entries. See
`D:/atlas/gap_audit.md` `L339 PRESERVED` parity-row in the
`### Anchor-evolution history` section for the prior anchor-iteration
history convention (anchor-tail intent-over-version naming).


---

- **This codex session (2026-07-08, Bulk-provider-surface round-1 + round-2 + round-3)**: three sequential bulk-advance blocks landed (round-1 `2e1c4f20d`→`274a6a961`→`a12d1dd77` for apollo/coeus/hermes/melinoe/ritk + themis pointer refreshes; round-2 `5d3395e95` + `715cff24e` + `02da06611`→`ab71f08ad`→`36acbbca9` for hermes-r2/coeus/cascade + multi-PM-reconciliations + `.gitignore hardening); round-3 `ad6cf57d4`→`1828ea14a`→`852de7129`→`769b70a67`→`1fe3c0e56` for apollo/eunomia/hermes/leto/mnemosyne). See `gap_audit.md` row 13 for the per-submodule advance record + provenance triples + branch-context notes (especially hermes on `rescue/detached-simd-numa-work` divergent 17 commits ahead of `origin/main`, NOT peer-WIP at the parent gitlink level; mnemosyne sjump `482670d` → `98a02b6` reflects the Miri alloc/free HIGH-PRIORITY finding at `eff(backend)` + `fix(backend)` + `docs(gap_audit)` chain). **Net alignment state post-`1fe3c0e56`**: all 12 actively-tracked submodules (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, kwavers) ALIGNED at inner HEAD with zero DIVERGED gitlinks — the first all-aligned state since the `e0bf55684` cross-tree reclamation audit. **ritk-python test suite (47/47)** compiled+passed at committed inner HEAD `1f49278c` (value-semantic asserts — see `gap_audit.md` row 154 bulk-advance unblock evidence). **KW-CV-001 watchpoint re-affirmed ACTIVE** at inner HEAD `35ee01076`: trigger `(cd /d/atlas/repos/kwavers && git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l)` returns 0; peer continues slice-by-slice Batch #1 + Batch #4 work without explicit closeout commit. **Atlanta-meta path forward**: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit (per `concurrent_agents` disjoint-scope rule); the round-3 block leaves kwavers at the peer-tracked HEAD `35ee01076` (atlas-meta gitlink already aligned, not divergent, just not watching for closure-style advances here — the KW-CV-001 watchpoint owns that path). **Branch context**: this turn's round-3 work landed under `codex/kwavers-atlas-integration`; `36acbbca9` `.gitignore` hardening prevents transient root scratch artifacts from re-entering `git status --short` (no body-scratch file was created for any of the 5 round-3 chore commits, per the user's signal-change-in-the-tree batch ceremony convention from ADR 0010 §Per-batch name pattern; each commit body authored inline via subject + body `-m` pairs + a final `-m` provenance-triple block citing row 11 dynamic-SHA extraction). **Cross-references**: `gap_audit.md` row 13 (per-submodule advance record with prior-SHA + derived-full-SHA + inner-chore-subject for each of the 5 round-3 modules); `checklist.md` §Next micro-sprint for the round-3 line-item summary. **Residual risks** (tracked in `gap_audit.md` row 6 row-268–270 kwavers sub-bullets): kwavers 267 dirty files at inner HEAD `35ee01076` is peer-WIP, not reclaimable from atlas-meta; kwavers Batch #1 closure condition (zero `par_for_each` source sites) is NOT yet met (41 sites across 15 files per `gap_audit.md` line-93); kwavers Batch #4 closeout condition (zero `burn::` source hits + zero `crates/kwavers-solver/Cargo.toml:42` burn dev-deps + `burn.rs`/`burn_compat` deletion) WAS met at `05500930c` per the line-92 sub-bullet (file deletion + manifest strip landed on the peer stream). The next bulk-advance round (round-4) is contingent on either inner HEAD churn (peer-WIP-after-push divergence) OR KW-CV-001 firing for kwavers.
- **This codex session (2026-07-06, Helios closure)**: `c5f2a84e` closed the direct Helios H-061/H-062 dependency slice by removing the unused `num-traits` workspace edge, removing the aggregate dicom-rs `ndarray` feature edge, adding the local Melinoe patch required by patched Gaia's `melinoe` 0.8.0 edge, and syncing Helios PM evidence. Concurrent peer commit `61931faf` then landed the RITK Batch #3 sub-batch #1 Atlas-parent pointer advance; preserve that pointer state.
- **This codex session (2026-07-06, Helios/RITK DICOM ownership)**: RITK inner commit `8f8360ff` adds `ritk-dicom::{DicomTag, tags, DicomAttributeRead}` so downstream DICOM geometry/modality-LUT attribute reads are RITK-owned. Helios H-061 now routes production DICOM parsing, typed attributes, transfer-syntax lookup, and pixel decode through `ritk-dicom`; dicom-rs remains direct only as a dev-dependency for synthetic Part 10 fixture generation. Helios H-063 is filed for the remaining `helios-imaging` audit: generic medical-image I/O/registration/toolkit operations move upstream to RITK; radiation-domain MVCT projection/reconstruction kernels stay in Helios.
- **This codex session (2026-07-07, RITK DEP-497-01 dead-dep strip)**: `repos/ritk` commits `7a66d1ee` (strip unused production `burn` dep from 17 leaf crates: `ritk-{cli,core,filter,io,jpeg,metaimage,mgh,minc,model,nifti,nrrd,png,registration,segmentation,snap,statistics,tiff,transform,vtk}`; `burn-ndarray` dev-dep retained where sub-batch #3 per-crate test ports are still open) + `00d57005` (checklist sync), pushed to `origin/main`. Distinct from Batch #3 sub-batch #5 (`[major]` full Burn Cargo strip + `Image<B,D>` re-export) per ADR 0012 — this is a non-breaking dead-edge removal, no version bump. Verified: `cargo nextest run` across the 19 touched crates 4258/4258 green, `cargo clippy --workspace --all-targets -D warnings` clean, `cargo fmt --check` clean for touched crates, `cargo doc --no-deps` no new warnings. Fixed an incidental `clippy::doc_lazy_continuation` false-positive in `ritk-model/src/ssmmorph/encoder/tests.rs`. Residual risks filed in `repos/ritk/checklist.md` (2 pre-existing broken intra-doc links in `ritk-filter`; a full-workspace-nextest-only timeout in `ritk-snap::pacs_ops` reproduced only under full-parallel resource contention, isolated run passes in 2.1s — not a hang). Atlas-meta `repos/ritk` gitlink advanced to `00d57005` via the dynamic-SHA-extraction convention (gap_audit.md row 11).
- **`repos/kwavers` `codex/kwavers-core-moirai-parallel` — peer ryancinsight ACTIVE** (inner HEAD `05500930c` 2026-07-07 19:11, `[ahead 0, behind 0]` of `origin/codex/kwavers-core-moirai-parallel` per inner `git rev-list --left-right --count`; atlas-meta `HEAD:repos/kwavers` gitlink pinned at `7235d464afb04dfec62dee1cd8e6e8d660b54250` lagging inner HEAD by 37 commits). State at inner HEAD `05500930c` per T1 verification: **Batch #4 (kwavers-solver PINN Burn → Coeus) source-residual is now ZERO** — canonical inner chore `8b128c478` "Remove dead burn compatibility shim and drop burn dependency" + slice 3+ commits drained the residual; `crates/kwavers-solver/src/burn.rs` + `burn_compat` module ABSENT; `rg -n '\bburn\b' -g '*.toml' .` zero hits in `crates/kwavers-solver/Cargo.toml` + root `Cargo.toml`; `rg -l '\bburn::' crates --type rust` zero hits across the kwavers source tree (was 186 line-hits / 80 files at `b605e2e74`, full clean at `05500930c`). **Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai)**: `crates/kwavers-{solver,physics}/Cargo.toml:{24,20}` now read `ndarray = { version = "0.16", features = ["serde"] }` (per peer `702e4f125` "drop unused ndarray/rayon feature from kwavers manifests"; the `rayon` feature strip is landed, contradicting the prior stale paragraph that read `features = ["rayon", "serde"]`); residual is now **41 `.par_for_each()` sites across 15 files** in `crates/kwavers-solver/src` (down from 84 sites / 28 files at `b605e2e74`, −51%) — concentration in `forward/{elastic/swe/{integration/integrator/mod,stress/divergence}, nonlinear/{kuznetsov/{diffusion,nonlinear,numerical,operator_splitting/mod,solver/{model_impl,rhs},spectral,workspace}, westervelt_spectral/spectral}, pstd/extensions/{elastic,elastic_orchestrator/pml/mod}, multiphysics/fluid_structure/{interface,solver/struct_impl}}`. Closeout state: no formal `closeout` / `final` / `completion` commit in the last 30 inner commits — peer lands Batch #4 + Batch #1 slice-by-slice without explicit closure commits. **Atlas-meta continues to defer parent-side pointer advance** for `repos/kwavers` until a kwavers-side final closeout commit lands (per `concurrent_agents` disjoint-scope rule). `burn.rs` + `burn_compat` facade deletion + Cargo.toml strip are LANDED on the inner peer stream (lifting the surrogate pre-condition cited in sub-batch #5 standing reminder per `docs/adr/0012-ritk-burn-trait-rebind.md`). See `gap_audit.md` row 6 kwavers sub-bullets L268-L270 for the kwavers-side reconciliation record.
- Neighbor claim streams to honor (disjoint from kwavers Batch #1, also DO NOT touch): `repos/moirai` `refactor/remove-dead-subsystems` (26 dirty paths — moirai source forbidden); `repos/leto` `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile (14 dirty paths — leto source forbidden); `repos/coeus` `main` (19 dirty paths); `repos/eunomia` `main` (`acos`/`asin`/`atan` peer queue, 7 dirty paths); `repos/apollo` (235), `repos/CFDrs` (79), `repos/gaia` (5), `repos/hermes` (46), and `repos/melinoe` (13) carry in-flight peer claims. `repos/helios`, `repos/ritk`, `repos/hephaestus`, `repos/mnemosyne`, and `repos/themis` are clean of inner dirty paths after the Helios/RITK DICOM ownership closure and prior pointer-sync commits.
- The moirai-parallel API surface for kwavers Batch #1 already exists: `for_each_chunk_pair_mut_enumerated_with`, `for_each_chunk_triple_mut_enumerated_with`, `for_each_chunk_quad_mut_enumerated_with`, `enumerate_mut_with`, `for_each_index_with` (moirai-parallel `src/ops.rs:281,335,408,125,155`). No moirai source change is required for Batch #1 closure; the consumer-side helpers in `crates/kwavers-physics/src/parallel.rs` already cover 1-mut + N-imm and 2-mut + N-imm arities, with 3-mut + N-imm and 4-mut + N-imm indexed zips (visible in `kwavers-solver/src/forward/elastic/swe/{integration/integrator/mod.rs,stress/divergence.rs}` and `forward/pstd/extensions/elastic.rs` and `forward/pstd/extensions/elastic_orchestrator/split_field_step/{stress,velocity,mod}.rs`) as the remaining helper-coverage gap.
- **This codex session (2026-07-09, Bulk-migration #2 E0369/E0599 closure-front triage in `kwavers-math`)**: dry-run enumeration via `rg '::ones\([^)]*\)\s*\*' --type rust` + `rg '\.view\(\)' --type rust` against `crates/kwavers-math/src/**` returns **0 `::ones(...) * scalar` sites (E0369 front fully drained, idiom-set closure confirmed)** and **151 prefix-form `.view()` call sites across 27 distinct files (138 bare `.view()` + 13 `.view_mut()`; total per row 14.5 SSOT in `gap_audit.md`; E0599 front, separate closure track)**. **Idiom-set triage conclusion**: the 3-item idiom list recorded in `gap_audit.md` `### Bulk-migration priority #2 routing lesson (2026-07-09)` — `array.iter_mut().for_each(|v| *v *= scalar)`, `as_slice_memory_order_mut()`, and the project-native `scale_array` helper — IS operationally complete for the E0369 front as of the prior-session proof-of-pattern work (`avx2.rs:46,56` + `dispatcher.rs:139,151` closed 4 of 4 E0369 sites; cargo check error count 128 → 124). **The `.view()` E0599 sites are a SEPARATE closure-front** (most call sites are `.view()` / `.view_mut()` invocations on ndarray `Array3`/`Array4`, requiring explicit error propagation rewrites + trait-bound refactor of `Boundary<_>` carrier), and **are NOT covered by the E0369 3-item idiom set**. Per the user’s “if new patterns emerge, file a follow-up docs update rather than diverge from the lesson” guidance, the 3-item list is NOT expanded in this turn — the E0599 front stays tracked here as a transient atlas-meta carryover with the 138/27 enumeration, awaiting either peer-side Bulk-#2 phase work or future-session idiom-set expansion posture.


- **[SUPERSEDED 2026-07-09 by ADR 0013 `## Supersedes` field]** the prior partial-closure-mark was 2026-07-08; superseded; see D:/atlas/docs/adr/0013-kwavers-batch1-source-side-closure.md for the full Batch #1 source-side closure mark.
- **slice 1 partial-closure-mark 2026-07-08 — kwavers Batch #1 source-side migration slice 1 PARTIAL CLOSURE (2/41 sites, 1/15 files)**: per the peer's `5cd8c708` chore (`refactor(kwavers-solver): Migrate struct_impl.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 1)`, on `codex/kwavers-core-moirai-parallel` atop parent `ccc6bbf9`): 2 of the 41 source-side `.par_for_each()` sites have been migrated. The 2 sites live in `crates/kwavers-solver/src/multiphysics/fluid_structure/solver/struct_impl.rs` (3D `Array3<f64>` element-wise relaxation on `p_fluid_ghost` + `p_fluid_ghost_prev`; plus a 1D sub-view relaxation on `t_solid_ghost` + `t_solid_ghost_prev`). Migration dispatch: idiomatic `moirai_parallel::ParallelSliceMut::par_mut().enumerate(closure)` trait form (auto-Adaptive policy; no `ExecutionPolicy` generic needed); cargo-check pre-validate clean at inner HEAD `5cd8c708`. **KW-CV-001 watchpoint state**: remains ACTIVE — the closure-style trigger (`closeout|final|completion|close-batch` substring grep on the last 30 kwavers commits) is still 0; per the `concurrent_agents` disjoint-scope rule, atlas-meta is *observing* (not advancing) the peer's slice-by-slice progress without re-emitting the prior retracted full-closure mark. The remaining 39/41 sites / 14/15 files will be tracked via per-slice partial-closure marks (this entry is the first such mark) until the source-side count actually drops to zero, at which point the full closure-mark can be reasserted. **Atlas-meta path forward**: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit; do NOT bump the kwavers gitlink from the current `35ee01076` even as subsequent Batch #1 slices land on the peer stream, per the watchpoint's no-advance-without-closeout policy. **Note (data-quality, post-e73d524 dedup)**: the round-3 codex-session block was historically duplicated at L87+L90 (pre-chore-cycle stale snapshot); de-duplicated in chore-commit `e73d5241f` via structural-cleanup; see the OBSERVED 2026-07-09 tombstone (post-cut at L283) for the audit trail. The partial-closure mark is appended at end-of-file for grep-ability + future-automation reliability.


- **This codex session (2026-07-08, Bulk-provider-surface round-4 — post-OOB `6902d2e92` re-probe)**: 7 atomic chore captures in this turn. The OOB consolidation commit `6902d2e92` ("chore(atlas): Advance repos/hephaestus pointer to 240b260 (CU-P6/CU-M3)") absorbed my staged round-4 reset state, capturing `hermes` `5ad1b58 → c7b17b02` + `leto` `a9572da → 86d366bc` (batched LU / CSC sparse format / CG/GMRES iterative solvers — unblocks kwavers-solver Bulk-solver migration closure target) bundled into a single `e3223094a`. The remaining per-crate captures split into one-atomic-chore-per-crate for cleanliness:
  - `6a598da91` kwavers `35ee01076 → 89117870` (inner `Migrate kwavers Complex/ndarray types to eunomia/leto atlas crates` — Phase-3 closure of Complex<f32>/f64, ndarray Array, coefficient paths onto eunomia+leto substrates; replaces nalgebra/ndarray/numeric-complex stack in kwavers-core domain)
  - `0e34ae082` coeus `e36f95f → ec69a6a` (inner `fix(coeus-dist): close TOCTOU race in TCP test port allocation` + co-emitted `342f38d` MS-406/407 reconciliation; TOCTOU between bind and listen eliminated in coeus-distributed harness)
  - `045291499` ritk `1f49278c → e75d8748` (inner `Add Module/AutodiffModule impls for DisplacementField and DisplacementFieldTransform` — DIRECTLY resolves the displacement_registration_test failure tracked in row 6; Sub-batch #5 RITK-spatial-rebind closure per ADR 0012)
  - `4a4cf928a` coeus `ec69a6a → 006f2a7` (inner `feat(coeus-nn): add MaxPool3d/AvgPool3d benchmark rows (G-043)` — criterion bench registry extension for 3D pooling kernels)
  - `4b7f4804e` kwavers `89117870 → 09c645f30` (inner `Migrate kwavers-core/source/signal/grid/field from ndarray to leto` — Phase-4 closure of kwavers-core domain crates source/signal/grid/field off ndarray onto leto's NDArray substrate; follow-on to `89117870`)
  - **Net alignment state post-`4b7f4804e`**: all 13 actively-tracked submodules ALIGNED at inner HEAD with zero DIVERGED gitlinks. Seven bulk-provider pointers advanced in this session cycle (well above round-3 cadence). KW-CV-001 watchpoint re-probed at every commit — still 0; peers continue `Migrate *.rs from ndarray to leto` subject phrasing, not `closeout`/`final`/`completion`/`close-batch`.
  - **Atlas-meta action posture**: round-4 captured all in-session churn. Awaiting peer's next kwavers/ritk commit; either KW-CV-001 fires for kwavers OR slice-7+ launches to re-open round-5 capture. Either path stays in observation mode; no source-tree work concrete to atlas-meta.

- **This codex session (2026-07-08, mid-session test/example validation sweep)**: user directive "cleanup and resolution of all test and example issues/errors" triggered a fresh sweep across consumer-side trees at the just-advanced inner HEADs. T1 evidence:
  - **ritk** at inner HEAD `529d6651`: `cargo nextest run -p ritk-python --lib` 47/47 PASS (value-semantic asserts verified — `mi_normalized_identical_is_one`, `mi_rejects_shape_mismatch`, `test_validate_percentiles_descending_elements_returns_error`, `test_validate_range_inverted_bounds_returns_error`).
  - **CFDrs** at inner HEAD `72275347fb71`: `cargo check --workspace --all-targets` PASS (no warnings); `cargo nextest run --workspace --lib` 2177/2177 PASS (1 skipped, 0 failed, 1 slow at 28.1s — within CFDrs's 30s terminate budget).
  - **CFDrs subset** `cargo nextest run -p cfd-math -p cfd-1d -p cfd-2d --lib`: 1335/1335 PASS (1 skipped, 24.9s execution).
  - **kwavers** at inner HEAD `ccc6bbf9e6` (`Workspace-wide ndarray↔leto boundary fixes; cargo check --workspace passes`): `cargo check -p kwavers-solver --workspace` PASS; `cargo check --workspace` PASS with 1 dead-code warning (`fn to_leto3` unused in `crates/kwavers-simulation/src/dispatch/elastic_pstd.rs:8:4`); **`cargo nextest run --workspace --lib` FAILS at compile** with 1 site: `crates/kwavers-solver/src/plugin/mod.rs:204:21` — the test-mock `NullBoundary::apply_acoustic_freq` reads `_field: &mut Array3<kwavers_math::fft::Complex64>` (resolving via in-scope `use ndarray::Array3;` at line 182, which shadows the workspace's `leto::Array3` re-binding); the `Boundary` trait now declares `&mut leto::Array<eunomia::Complex<f64>, VecStorage<eunomia::Complex<f64>>, 3>`. **Disjoint-scope peer-owned per `concurrent_agents`**: atlas-meta records surface + line; the inner peer stream owns the 2-line edit (`use ndarray::Array3;` → `use leto::Array3;` at L182 + parameter signature updates at L204). Filed at `gap_audit.md` row 14.5.
  - **Note**: a 2nd `kwavers-solver` site at `crates/kwavers-solver/src/forward/pstd/physics/residual_gas_absorption.rs:74` (`spectrum: &mut Array3<kwavers_math::fft::Complex64>`) ALREADY uses `use leto::{Array3, ArrayView3};` (L65), so its `Array3` resolves correctly. Only the plugin test mock is broken.
- **`repos/kwavers` gitlink advance this session**: `4f344f840` (Phase-3 → Phase-4 → Phase-5 sweep closure at inner HEAD `ccc6bbf9e6`). KW-CV-001 watchpoint re-probed at `ccc6bbf9e6` — still 0; peers continue `Migrate *.rs from ndarray to leto` subject phrasing. Atlas-meta defers final closeout pose until peer's closeout subject lands.

- **[OBSERVED 2026-07-09 round-3 codex-session block + Standing reminders + Cross-engineering verification + Out-of-scope + Atlas-root dirty triage + Review nit rolling list deduplicated to canonical Region 1 (L1-L282) ordering via atomic structural-cleanup chore; see `### In-flight claims (per concurrent_agents)` L82 + canonical `#### Standing reminders` L112 + canonical `## Review nit rolling list` L186 for the authoritative copies. This tombstone also absorbs the prior `93f676ffd` forward-auditor cross-reference to the L262 SUPERSEDED + L263 slice-1 partial-closure-mark block, which remains the canonical Batch #1 source-side closure reference (see ADR 0013 `## Supersedes` field for the full Batch #1 source-side closure mark).]**


## Batch #1 source-side migration -- slice 3 partial-closure-mark 2026-07-08

Per the peer's `d2cb977b` chore (refactor(kwavers-solver): Migrate diffusion.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 3), on codex/kwavers-core-moirai-parallel atop parent c77a926d8): **5/41 sites migrated in 3/15 files** cumulative. The 1 new site is in crates/kwavers-solver/src/forward/nonlinear/kuznetsov/diffusion.rs (1 mut + 4 immut Zip par_for_each at L93, migrated with 5 is_standard_layout() asserts + as_slice{_mut,}() + par_mut().enumerate() with 4 flat-index lookups). **36/41 sites / 12/15 files remain**. Full-closure mark remains retracted. KW-CV-001 watchpoint remains ACTIVE.
## Batch #1 source-side migration -- slice 2 partial-closure-mark 2026-07-08
> Note: this mark landed after the slice 3 mark (commit f2c89a73) due to flaky prior re-emission attempts; it documents cumulative state AT slice 2 chore landing, not the present state.

Per the peer's 9541155f chore (refactor(kwavers-solver): Migrate model_impl.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 2), on codex/kwavers-core-moirai-parallel atop parent 5cd8c708): **4/41 sites migrated in 2/15 files cumulative** at slice 2. The 2 new sites are in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/model_impl.rs` (1-mut + 2-immut Zip par_for_each at L48 + 1-mut + 3-immut Zip par_for_each at L62 inside KuznetsovWave::update_wave). **37/41 sites / 13/15 files remain**. KW-CV-001 watchpoint remains ACTIVE. NOTE: retroactive land AFTER slice 3 mark (prior re-emission attempts failed).
## Batch #1 source-side migration -- model_impl.rs Nit 1 asymmetry fixup mark 2026-07-08

Per the peers b21679f5c chore (fix(kwavers-solver): Add standard-layout assert to model_impl.rs migration, on codex/kwavers-core-moirai-parallel atop parent d2cb977b): closes Nit 1 asymmetry by retroactively adding 7 is_standard_layout() asserts to model_impl.rs (slice 2 file): 3 in first-step branch + 4 in multi-step branch. Mirrors the struct_impl.rs fixup c77a926d8 in style. Cargo check clean. Cumulative at the migration level unchanged: **5/41 sites / 3/15 files migrated + 2 file-level fixups** (c77a926d8 + b21679f5). 36/41 sites / 12/15 files remain. KW-CV-001 watchpoint remains ACTIVE.

## Batch #1 source-side migration -- slice 4 partial-closure-mark 2026-07-08

Per the peer `9595a99f5` chore (refactor(kwavers-solver): Migrate nonlinear.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 4), on codex/kwavers-core-moirai-parallel atop parent b21679f5c): **6/41 sites migrated in 4/15 files** cumulative. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/nonlinear.rs` (1-mut + 3-immut Zip par_for_each at L109 in `compute_nonlinear_term_workspace`). **35/41 sites / 11/15 files remain**. Full-closure mark (Batch #1 CLOSED) remains retracted, this is the fourth per-slice partial-closure mark. KW-CV-001 watchpoint remains ACTIVE.

## Batch #1 source-side migration -- slice 5 partial-closure-mark 2026-07-08

Per the peer `d614a7f57` chore (refactor(kwavers-solver): Migrate operator_splitting/mod.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 5), on codex/kwavers-core-moirai-parallel atop parent 9595a99f): **7/41 sites migrated in 5/15 files** cumulative. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/operator_splitting/mod.rs` (1-mut + 1-immut Zip par_for_each at L191 in `OperatorSplittingSolver::nonlinear_step`). **34/41 sites / 10/15 files remain**. KW-CV-001 watchpoint remains ACTIVE.

## bash-heredoc artifact audit verification 2026-07-08

> Audit verified: 0 unresolved `\$VAR` artifacts (matches pattern `\$[A-Z_]+`) remain in 3 PM artifacts after the \$SHORT substitution chore (commit `92dad112`). All residual `$` characters in the 3 PM artifacts are legitimate (Rust generic syntax `<$t as Scalar>`, command-substitution documentation `$(cd repos/...)`, mathematical notation, or anti-pattern template examples in audit prose). Code-reviewer N3 carry-forward from the \$SHORT substitution chore is now CLOSED.

## Batch #1 source-side migration -- slice 6 partial-closure-mark 2026-07-08 (heterogeneous site 1 deferred)

Per the peer `7be3fbbd8` chore (refactor(kwavers-solver): Migrate rhs.rs homogeneous par_for_each sites to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 6), on codex/kwavers-core-moirai-parallel atop parent d614a7f5): **11/41 sites migrated in 6/15 files** cumulative. The 4 new sites are in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/rhs.rs` (1-mut + 1-immut Zip par_for_each sites in `KuznetsovWave::compute_rhs` homogeneous branch -- linear/laplacian, source/cache_source, nonlinearity/nonlinear_term, diffusion/diffusive_term). **30/41 sites / 9/15 files remain**. **Heterogeneous Zip::indexed site 1 deferred to follow-up chore**. KW-CV-001 watchpoint remains ACTIVE. Filename arithmetic restored to 6/15 from commit-body off-by-one of 5/15.

- **slice 9 partial-closure-mark 2026-07-09 — kwavers Batch #1 source-side migration slice 9 PARTIAL CLOSURE (1 site in spectral.rs; the deferred heterogeneous 4-mut-0-immut Zip::indexed chain)**: per the peer's `949e5a39` chore (`refactor(kwavers-solver): Migrate spectral.rs 4-mut Zip::indexed to verbose is_standard_layout (Batch #1 source-side slice 9)`, on `codex/kwavers-core-moirai-parallel` atop slice 8 parent `9ab677b0`): 1 deferred heterogeneous site migrated. The site lives in `crates/kwavers-solver/src/forward/nonlinear/westervelt_spectral/spectral.rs` in `initialize_kspace_grids` — the 4-way `Zip::indexed(&mut kx).and(&mut ky).and(&mut kz).and(&mut k_squared).par_for_each(|(i, j, k), kx_v, ky_v, kz_v, k2| { let kx_val = kx_axis[i]; let ky_val = ky_axis[j]; let kz_val = kz_axis[k]; *kx_v = kx_val; *ky_v = ky_val; *kz_v = kz_val; *k2 = kx_val * kx_val + ky_val * ky_val + kz_val * kz_val })` chain. **Strategy**: Pattern A — extend divergence.rs slice 7 3-mut strategy to 4 muts. Keep `Zip::indexed(kx.view_mut())` as the parallel iterator (the closure body consumes `(i, j, k)` for closure-captured Vec<f64> reads `kx_axis[i]/ky_axis[j]/kz_axis[k]`); pre-extract 3 flat `as_slice_mut()` buffers for `{ky, kz, k_squared}`; write 3 additional mut outs via `op_slice[idx]` inside the closure, computing `idx = i*(ny*nz) + j*nz + k` inline once per iteration (~10 cycles vs ~100 for a div/mod-based idx-to-(i,j,k) decomposition in a drop-everything pattern). Race-freedom preserved: each parallel task writes to 4 distinct output elements (kx_v via Zip iterator + 3 disjoint `slice[idx]` writes), all addressed by the same unique `(i, j, k)` tuple. **Precondition asserts**: 7 layout/length asserts total = 4 verbose `is_standard_layout()` on `{kx, ky, kz, k_squared}` mut outs + 3 `debug_assert_eq!` on `{kx_axis, ky_axis, kz_axis}.len()` (Vec<f64> is unconditionally C-contiguous, so length is the only precondition — matching slice 8 cluster D's `σ_*` Array1<f64> pattern verbatim). **WHY NOT HELPER rationale documented inline**: (a) verbose-form is Batch #1 SSOT with helper adoption in 0 of 9 migrated sites across slices 1-8; (b) the slice 9 4-mut extension deliberately matches divergence.rs slice 7 3-mut verbatim for source-level consistency; (c) broader helper-validation across heterogeneous patterns is deferred to Batch #2. **Validation**: `cargo check -p kwavers-solver --lib --no-default-features` rc=0; `cargo test -p kwavers-solver --lib forward::nonlinear::westervelt_spectral` rc=0 — all 6 westervelt_spectral tests pass bitwise (`k_squared_dc_bin_is_exactly_zero`, `k_squared_fundamental_mode_matches_2pi_over_lx`, `k_squared_nyquist_bin_equals_pi_over_dx`, `spectral_laplacian_of_constant_is_zero`, `spectral_laplacian_of_sine_matches_analytical`, `spectral_laplacian_into_is_bitwise_identical_to_allocating`). **Code-reviewer verdict on the source-side commit**: OK to commit after 1 minor nit applied (sharpened the WHY-NOT-HELPER section (b) rationale to drop the imprecise "N>5 closure-captured immuts" claim, since this site only has 3 immuts). **KW-CV-001 watchpoint state**: remains ACTIVE — no formal `closeout`/`final`/`completion`/`close-batch` substring exit in the last 30 inner kwavers commits; per `concurrent_agents` disjoint-scope rule, atlas-meta continues to observe without re-emitting the prior retracted full-closure mark. Atlas-meta path forward: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit.

- **ADR 0014 forward-looking note 2026-07-09 — KW CV-001 watchpoint active awaiting kwavers peer stream closeout-tag chore**: per the new ADR 0014 `D:/atlas/docs/adr/0014-kwavers-batch1-closeout-tag.md` (Status `Proposed` on 2026-07-09), the kwavers Batch #1 closeout-tag ceremony chore is opened but not yet executable. The KW-CV-001 watchpoint (per `D:/atlas/backlog.md` §In-flight claims `repos/kwavers` row: `git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l` returns 0 at inner HEAD `949e5a39`) gates the Status flip from `slice-by-slice partial closure` (ADR 0013) to `full closure` (ADR 0014). The chore bundles 3 atomic items on disjoint scopes: item (a) 1,315-file mechanical drift flush + item (b) slice 7 `is_standard_layout` predicate unification + item (kwavers closeout) — all 3 emit on `repos/kwavers` `codex/kwavers-core-moirai-parallel` per disjoint-scope (ADR 0011 §Leg 2 — atlas-meta is FORBIDDEN from touching `D:/atlas/repos/<X>/`). Atlas-meta's bystander role here: item (c) `chore(atlas): Advance repos/kwavers submodule pointer + KW-CV-001 retirement` is a forward chore whose trigger is items (a) + (b) + closeout-style-commit having landed on the kwavers peer stream. When the stash lands, item (c) advances `repos/kwavers` parent-tree gitlink + either deletes or marks `RETIRED 2026-07-09+` the KW-CV-001 row in §In-flight claims. ADR 0014 itself is then flipped `Proposed` → `Accepted` via a follow-up atlas-meta chore commit. Until the kwavers peer stream emits items (a)+(b)+closeout, this ADR remains `Proposed` + this note remains the residual forward-looking visibility surface.

- **Blocker-triage chore briefs 2026-07-09 — 5 carried-forward blockers re-probed against owning peer streams (per ADR 0013/#14 §Out of scope items 1-4)**: atlas-meta orchestrates the 2026-07-09 re-probe of the 5 carried-forward blockers referenced by ADR 0013 §Out of scope items 1-5 + ADR 0014 §Out of scope items 1-5. The re-probe results classify each blocker as RETIRED (cargo-clean), RECLASSIFIED (different actual cause), CORRECTED (right outcome, wrong count), or CONVERTED (workstream-already-progressing). Each blocker becomes a discrete chore on its owning peer stream per disjoint-scope (ADR 0011 §Leg 2); atlas-meta's bystander role is filing the brief here.

| Row | Blocker ID | Owning peer stream | Re-probe classification | Action verb on peer stream | Cross-walk |
|-----|-----------|---------------------|-------------------------|----------------------------|------------|
| 1 | ritk-wgpu-compat burn workspace-manifest (ADR 0013 §Out-of-scope #1) | `repos/ritk` | **➜ RETIRED** — `cargo check -p ritk-wgpu-compat --lib --no-default-features` rc=0 verified on ritk inner HEAD `a1bf4ac43` (17.32s) on branch `main`; `burn` + `burn-ndarray` deps are accepted by cargo | No chore required for Batch #1 closure. Optional: Burn-strip per ADR 0012 §Sub-batch #5 `[major]` for the longer-term Burn removal cycle (NOT part of Batch #1 gate) | ADR 0013 §Out-of-scope #1 amended with ➜ RETIRED note |
| 2 | ritk-registration burn dep strip (ADR 0013 §Out-of-scope #2) | `repos/ritk` | **➜ RECLASSIFIED** — actual cause is `direct-parzen` feature-gate regression; 2 `E0432` errors at `crates/ritk-registration/src/metric/histogram/parzen/image_cache_helpers.rs:7:43` (`SparseWFixedCache` gated behind `direct-parzen` feature) + `crates/ritk-registration/src/metric/histogram/mod.rs:10:17` (`atlas_parzen_cache` module gated behind same feature) | Open chore on `repos/ritk`: gate the importing modules behind a `#[cfg(feature = "direct-parzen")]` proxy or fix the import path; commit title `fix(ritk-registration): Resolve direct-parzen feature-gate E0432 errors`. Verification: `cargo check -p ritk-registration --lib --no-default-features` rc=0 | ADR 0013 §Out-of-scope #2 amended with ➜ RECLASSIFIED note; ADR 0014 §Out-of-scope #2 inherits |
| 3 | ritk-image autodiff-module syntax (ADR 0013 §Out-of-scope #3) | `repos/ritk` | **➜ RETIRED** — `cargo check -p ritk-image --lib --no-default-features` rc=0 verified on ritk inner HEAD `a1bf4ac43` (18.77s); remaining `autodiff` references (`host_extract.rs:73,114,115` `type AB = Autodiff<NdArray<f32>>;` test fixture + `types.rs:188` comment) are inert feature-gated test types | No chore required. Informational only — the carried-forward entry was inaccurate; the lib does not have a syntax error | ADR 0013 §Out-of-scope #3 amended with ➜ RETIRED note |
| 4 | 1,315-file kwavers mechanical drift (ADR 0013 §Out-of-scope #4) | `repos/kwavers` | **➜ CORRECTED** — actual drift is 30 modified files, not 1,315 (`git status --short | wc -l` against `repos/kwavers` inner HEAD `445ab9b2` on `codex/kwavers-core-moirai-parallel`); sample of 30/30 modifications is whitespace-only (LF vs CRLF normalization) | Open chore on `repos/kwavers`: emit `chore(kwavers): Flush mechanical dirty triage (30-file CRLF/whitespace batch)` per ADR 0014 §Sequencing step 1 (corrected file count). Verification: `git status --short | wc -l` returns 0 post-chore | ADR 0014 §Sequencing step 1 + §Verification plan item 2 amended with corrected 30-file count |
| 5 | kwavers-math Phase-3/Phase-4 ndarray → leto migration breakage (ADR 0013 §Out-of-scope #5) | `repos/kwavers` | **➜ CONVERTED** — 2 actual commits landed on kwavers peer post-slice-9 `949e5a39`: `445ab9b2` `fix(kwavers-math): linear algebra import/API mismatches` + `e2e1e180f` `fix(kwavers-math): grid/transducer compilation issues` (both kwavers-math-scoped exclusively) | Workstream already in progress on kwavers peer stream; no new chore required from atlas-meta. Monitoring posture until `cargo check -p kwavers-solver --lib --no-default-features` rc=0 restored post-`Array2::from_shape_vec` signature shift | ADR 0013 §Out-of-scope #5 + ADR 0014 §Out-of-scope #5 amended with ➜ CONVERTED note referencing actual commit SHAs |

Triage-summary headline: **5 carried-forward blockers re-probed 2026-07-09; 3 NOT real (#1, #3, #4 overstated), 1 misdiagnosed (#2 not Burn — feature-gate), 1 real + active (#5 already progressing on kwavers peer with 2 actual commits). Batch #1 closure gate unaffected**: ✅ ADR 0013 §Verification plan step 2 `cargo check -p kwavers-solver --lib --no-default-features` rc=0 at slice 9 parent inner HEAD `949e5a39` verified. The post-slice-9 `kwavers-solver --lib` breakage from `Array2::from_shape_vec` signature shift is the explicit Batch #2 prerequisite gate per ADR 0014 §Verification plan step 8. Filing this brief acts as the forwarding ledger: each row's own peer stream picks up its chore at their cadence; atlas-meta does not co-emit the chore commits per disjoint-scope.

- **ADR 0015 trigger-chore brief 2026-07-09 — Open KW Batch #2 Entry Point #1 (`kwavers_safety::with_zip_standard_layout` const-generics arity extension) on kwavers peer stream**: per the new ADR 0015 `D:/atlas/docs/adr/0015-kwavers-batch2-entrypoint1-helper-const-generics.md` (Status `Proposed` on 2026-07-09), the kwavers-solver Batch #2 Entry Point #1 acceptance-validation chore is opened but **currently BLOCKED on Block #5** (per ADR 0013/0014 §Out of scope #5 + Blocker-triage chore briefs row 5). The chore design refines ADR 0013 §Open Batch #2 Entry Point #1 with a const-generics arity extension `[(&'static str, &'imm Array3<A>); N]` with `const N: usize` for the helper signature; this replaces the current dynamic-slice form `'imm [(&'static str, &'imm Array3<A>)]` (which forces runtime indexing + local `Vec` allocation + HRTB friction at N>5 closure captures). The implementation commits live on `repos/kwavers` peer stream per disjoint-scope (ADR 0011 §Leg 2 ABSOLUTE — atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` edits). **Acceptance criteria (AC-1 through AC-6) per ADR 0015 §Verification plan**: AC-1 `cargo check -p kwavers-solver --lib --no-default-features` rc=0 (Block #5 gate); AC-2 `cargo test -p kwavers-solver --lib` rc=0; AC-3 6/6 westervelt_spectral tests bitwise-identical; AC-4 helper-stress fixture backporting slice 6b rhs.rs 9-immut heterogeneous Phase 2 site bitwise vs verbose-form RHS at all (i,j,k) grid points; AC-5 `cargo test -p kwavers-solver --lib --features helper-stress` rc=0; AC-6 slice 6b site in-place adoption preserves bitwise equivalence. The standing reminder is recorded here in atlas-meta side until AC-1 through AC-6 are all ✅; at that point, atlas-meta emits Step 5 (status-flip chore commit) per ADR 0015 §Sequencing on the kwavers peer core-moirai-parallel branch HEAD that achieves acceptance.

- **ADR 0015 Step 2 design-spec landing 2026-07-09 — KW Batch #2 Entry Point #1 Step 2 helper const-generics extension design-spec filed on atlas-meta side per disjoint-scope**: per ADR 0015 §Sequencing `### Step 2 detailed design specification` amendment landed on atlas-meta by this commit, the Step 2 design-spec is filed as the SSOT that the kwavers claim stream picks up once Block #5 closes. **Status reaffirmation (probed 2026-07-09)**: Block #5 pre-flight gate STILL BLOCKED on `cargo check -p kwavers-solver --lib --no-default-features` (rc≠0; E0308 type mismatches in `kwavers-transducer` + E0599 missing `matmul`/`assign` methods + `kwavers-transducer/focused/arc.rs` syntax gaps; the post-slice-9 commits `445ab9b2` + `e2e1e180f` did not close the gate). The Step 2 design-spec captures: (a) target file `D:/atlas/repos/kwavers/crates/kwavers-solver/src/safety/mod.rs:L84-130` (NEVER EDIT FROM ATLAS-META); (b) 4 modifications to apply (add `const N: usize` + change `immuts` to `[(&str, &Array3<A>); N]` + simplify closure-bound array form + replace `Vec` with `std::array::from_fn`); (c) preserved constraint surface verbatim (`A: Copy + Send + Sync` + verbose panic message form + `'out` lifetime + Nit-1-fix `A: 'static` omission); (d) monomorphization analysis (~30 KB binary impact bounded at N=0..9); (e) Send + Sync propagation + disjoint-capture-rule analysis; (f) HRTB retention recommendation (`for<'s>` kept for forward-compat); (g) acceptance criteria AC-2a/AC-2b/AC-2c + reviewing checklist (atomic-boundary + disjoint-scope + paragraph-collapse). Step 2 cannot execute from atlas-meta per ADR 0011 §Leg 2; the kwavers claim stream owns the implementation commit. Standing reminder updated to: Step 2 design-spec SHIPPED; Block #5 gate BLOCKED; pre-flight gate re-probe required before ASSEMBLE-STATE confirmation.

- **ADR 0016 trigger-chore brief 2026-07-09 — Open Block #5 (kwavers-math ndarray → leto) resolution design-spec on kwavers peer stream per disjoint-scope**: per the new ADR 0016 `D:/atlas/docs/adr/0016-kwavers-block5-resolution-design-spec.md` (Status `Proposed` on 2026-07-09), the kwavers-math Phase-3/Phase-4 ndarray → leto migration resolution chore is opened with a 3-commit atomic decomposition recommended design. Block #5 pre-flight gate is the **AC-1 prerequisite for ADR 0015 Acceptance** (Batch #2 Entry Point #1 helper const-generics extension depends on this). Pre-flight gate state (probed 2026-07-09): `cargo check -p kwavers-solver --lib --no-default-features` returns rc≠0 with 8 errors in `kwavers-transducer` (E0308 type mismatches in `beamforming/processor.rs` + E0599 missing `matmul` on `leto::Array` + E0599 missing `assign` on `Result` in `calibration/manager/mod.rs` + arc.rs syntax gaps in `transducers/focused/arc.rs`); the 2 already-landed commits `445ab9b2a` + `e2e1e180f` closed kwavers-math-only scope but did NOT propagate fixes to kwavers-transducer/receiver/boundary/source/grid callers. The 3-commit atomic decomposition per ADR 0016 §Decision: (1) `fix(kwavers-transducer): Resolve E0308/E0599 + arc.rs syntax (Block #5 sub-batch 1 — strict additive)` — arc.rs syntax + o_ops::linalg::matmul import) + Result.assign migration (destructured `if let Err(e)` pattern) + E0308 `leto::Array` boundary reconciliation; (2) `refactor(kwavers-migration): Migrate Array2::from_shape_vec tuple→array workspace-wide (Block #5 sub-batch 2 — strict signature migration)` --- 8 crates [python, solver, analysis, transducer, receiver, boundary, source, grid] using `sed`-assisted migration from `(rows, cols)` form to `[rows, cols]` array form; (3) `chore(kwavers): Block #5 gate-validation regression test (Block #5 sub-batch 3 — gate reset)` --- CI-side rc=0 assertion + bitwise-identical 6/6 westervelt_spectral tests against slice 9 inner HEAD `949e5a39` baseline. AC-1 through AC-5 per ADR 0016 §Verification plan (kwavers-transducer rc=0 + workspace-wide `Array2::from_shape_vec((` count = 0 + kwavers-solver rc=0 + 6/6 westervelt_spectral bitwise + no false-positive KW-CV-001 watchpoint trigger). Implementation commits live on `repos/kwavers` peer stream per disjoint-scope (ADR 0011 §Leg 2 — atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` edits). Standing reminder: Block #5 design-spec SHIPPED as the SSOT; kwavers claim stream owns the 3-commit implementation; once the 3 commits land + AC-1 through AC-5 satisfied, atlas-meta emits Step 5 status-flip chore per ADR 0016 §Sequencing flipping ADR 0016 to `Accepted` + simultaneously unblocks ADR 0015 AC-1.

## Provider integration audit queue — 2026-07-13

| ID | Class | Status | Owner/scope | Acceptance |
|---|---|---|---|---|
| HEPH-EMPTY-001 | [patch] | done (`65e89b7`, merged `991f12e`) | Hephaestus decomposition state | Synthetic empty factors deleted; determinant, identity, rank, permutation, and shape contracts pass CUDA/WGPU value tests and the 239-test package suite. |
| MEL-SCOPE-001 | [major] | done (`55ad20e`, merged `bb07447`) | Melinoe capability plus Mnemosyne/Themis/Moirai/Gaia/Coeus/Hephaestus consumers | Unsafe implementer obligation encoded; consumers migrated; Miri, conformance, and provider-version unification pass. |
| MOI-NUMA-001 | [major] | done — ADR 0017, deleted `numa.rs` (4 P0 defects) | Moirai + Mnemosyne/Themis ownership — redirected via ADR 0017 | Deleted 334-line `numa.rs`; existing Themis (placement), Mnemosyne (allocation), Moirai executor (work-stealing) cover the domain. Zero external consumers confirmed. |
| MOI-RESOURCE-214 | [patch] | done — merged PRs #70/#71 (`b637064`) | Moirai `moirai-sync/src/sync/resource_pool.rs`; deterministic clear/recycle interleaving; provider PM artifacts | Provider implementation `eb62898`, review-state `cd84276`, and PM closeout `5788b03`; 20/20 nextest, Clippy, rustdoc, doctests, and Criterion baseline pass; Atlas gitlink advanced to final provider head `b637064`. |
| MOI-BLOCKING-213 | [arch] | done — merged PRs #72/#73/#74 (`6184f73`) | Moirai executor blocking lane; provider PM artifacts | Lazy bounded blocking lane isolates compute workers; separate counters preserve quiescence and metrics; 87/87 nextest, executor-only warning-denied Clippy, rustdoc/doctest evidence, starvation/backpressure/priority/cancellation/shutdown/concurrent-producer tests, and Criterion rows pass. |
| THEM-CACHE-001 | [minor] | done (`18807bb`, merged PR #6) | Themis cache detection | Linux cache parsing returns typed absence on malformed input; Themis consumer pins are co-evolving. |
| LETO-SCALAR-001 | [major] | partial (`855f3ad`) | Leto scalar execution — length pre-validated; Hermes error propagation remains | Partial write closed: `assert_eq!` preconditions in all mutating Scalar methods. 304/304 leto-ops tests pass, apollo-fft builds clean. Error propagation deferred to Result-returning Scalar trait API change. |
| MNE-PERCPU-001 | [patch] | done (verified 2026-07-15) | Mnemosyne local cache — lazy `OnceLock<Box<>>` confirmed | Static footprint ~56 bytes, not 720,896. No backend enables `ENABLE_CPU_CACHE`. |
| TREE-SRP-001 | [arch] | done — ADR 0018 Phases 1-3 complete; Phase 4 filed as TREE-DUP-002 | Melinoe/Themis/Moirai hierarchy | ADR-0018: melinoe halo consolidated (→ melinoe::collections), themis tests rehomed (→ tests/), moirai constants.rs split, Phase 4 deferred. |

## Watchpoints — 2026-07-19 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| MR-WATCH-001 | moirai-scheduler/executor rebuild | `9c015a3` peer break + `5343ebfc` mid-fix | peer green clean HEAD | ✅ CLOSED 2026-07-14 (720/720 at `c43f86a`) |
| HERMES-WATCH-001 | Hermes Mnemosyne consumer Miri | PR #6 `db8e1a4` after provider PR #13 | fresh GitHub Miri/CI completes green | ✅ CLOSED 2026-07-19 (`cargo miri test -p hermes-simd-core` 14/14 pass; mnemosyne locked at `9b8585db` includes aliasing fix `5a9f49f`) |
| MOI-CONTENTION-001 | moirai contention audit | `perf/moirai-contention-audit` branch with contention fixes | merged to main at `9cd650f`, 82/82 pass | ✅ CLOSED 2026-07-15 |
| KW-WATCH-002 | kwavers-therapy abdominal perf | 90s `elastic-fwi` nextest override | peer-stream perf fix | ⏳ open (FFT zero-alloc helper committed, algorithmic perf in peer scope) |
| KW-WATCH-003 | kwavers-python leto→ndarray conversion compile break | `b861254` peer HEAD + 13 WT dirty | peer lands clean green committed HEAD | ✅ CLOSED 2026-07-19 (false positive: pyo3 0.29 alignment resolved 61 E0277; `cargo check -p kwavers-python` clean with 0 errors) |
| ritk Burn-strip verify-block | ritk Batch #3 #4-#6 dep strip | `ba6da3a` 1-ahead + 5 WT dirty | peer pushes, cleans WT, nextest green | ✅ CLOSED 2026-07-19 (Burn→Coeus doc rename committed `22cdbffb`; zero Burn/ndarray production deps remain; `cargo check --workspace` clean) |
| MNE-PERCPU-001 | Mnemosyne per-CPU cache | 720,896-byte dormant static | n/a | ✅ CLOSED 2026-07-15 (lazy OnceLock verified) |
| LETO-SCALAR-001 | Leto scalar length pre-validation | Hermes error discard + silent partial write | n/a | ✅ CLOSED 2026-07-15 (`aecb231`); error propagation deferred to `[major]` |

## Watchpoints — 2026-07-20 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| HARM-PUBLISH-001 | `repos/harmonia` submodule registration | Local `repos/harmonia` worktree was unversioned pending remote publish | Peer publishes the `repos/harmonia` worktree to `https://github.com/ryancinsight/harmonia` and advances the Atlas gitlink | ✅ CLOSED 2026-07-20 (peer PR #57 merged `0b0d01d`: Harmonia published at `cf6ce3e`, `.gitmodules` entry added, gitlink advanced, ADR 0023 flipped `Proposed` → `Accepted`, current-stack table reconciled to 20 packages) |
| HEPH-CUDA-WIN-001 | `repos/hephaestus/crates/hephaestus-cuda` + `hephaestus-python` Windows-gnu link | Verified sweep across all 20 Atlas packages: `cargo check` clean across all 20; the bounded per-package nextest run reports `hephaestus-cuda` and `hephaestus-python` fail to build with `x86_64-w64-mingw32-gcc` link error reading `-L /usr/local/cuda-11.3/lib64/` and `-lcuda` on the Windows-gnu host. Hephaestus core/wgpu/metal subset (211/211) is clean | Upstream build script (in `cuda-oxide` or `cutile-rs`) emits a Windows-aware CUDA SDK path via `CUDA_PATH` (`%CUDA_PATH%\lib\x64\cuda.lib`) and the link succeeds on a Windows NVIDIA host; this is an environment defect, not a code regression | ⏳ open (2026-07-20 Session 3 re-confirmed: 211/211 hephaestus core/wgpu/metal under `--exclude hephaestus-cuda --exclude hephaestus-python`; cuda + python skipped per upstream `cuda-oxide`/`cutile-rs` Linux-shaped link path; not a regression) |

## Watchpoints — 2026-07-20 Session 3 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| ASCLEPIUS-REG-001 | `repos/asclepius/` registration | Published two-crate workspace and fetched remote-default merge `ceb8b6d`; explicit P1 promotion request satisfies the prior reopen trigger | Merge `.gitmodules`, exact gitlink, ADR 0028, and stack documentation; then materialize the provider in consumer CI | ✅ CLOSED 2026-07-20 Session 5 (peer commit `6fb5576` "feat(atlas): Register Asclepius" registered the submodule; ADR `0028-asclepius-biological-response-promotion.md` filed Status `Accepted`; `.gitmodules` lines 86-88 reference `repos/asclepius` -> `https://github.com/ryancinsight/asclepius.git`; 23-package stack recorded in README + INDEX; cross-ref `gap_audit.md` L3-34 Asclepius P1 promotion entry) |

## Watchpoints — 2026-07-21 Session 6 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| HELIOS-TYCHE-MAJOR-001 | `repos/helios/crates/helios-imaging/src/noise.rs` + workspace `tyche-core` pin | tyche peer landed breaking `e1a5964 feat(tyche-core)!: Type counter streams` (`StandardNormal<T>` -> `StandardNormal<T, A: StreamAlgorithm>`); the helios `[patch]` override resolves tyche-core to local HEAD `0fc810b` (post-break), bypassing the manifest rev `87923da9...` (dead pin) | Peer migrates `helios-imaging/src/noise.rs:17,45` to the two-param form `StandardNormal::<f64, SplitMix64>::at(seed, sample_index, 0)` (add `SplitMix64` to the `use tyche_core::{...}` import on line 17) and re-establishes the 251/251 nextest baseline; OR bumps the manifest rev pin to `0fc810b` and updates `Cargo.lock` accordingly | ✅ CLOSED 2026-07-21 by helios peer PR #15 (`d82e3bb`): commit `4a01443 "feat(helios-imaging)!: Pin Tyche stream"` removed the local path override entirely (eliminating rev drift), made the algorithm and stream version part of the replay identity, and filed ADR `0005-tyche-noise-stream.md`. Helios main `11487c2` is the merged default post-PR #15; user's standing "implement and resolve examples" helios dispatch is satisfied. |
| CFDRS-TYCHE-MAJOR-001 | `repos/CFDrs/crates/cfd-optim/src/design/space/sampling/mod.rs` + workspace `tyche-core` pin | same tyche breaking change; the CFDrs `[patch]` override resolved the post-break provider | Peer supplies `SplitMix64` to `LatinHypercube` and routes indexed words through `Counter<UserDomain<0>, SplitMix64>` | ✅ CLOSED 2026-07-21 by CFDrs `fca1a9a9`; the exact migrated source is present in public default `394c9977` |
| CFDRS-CFD1D-LINT-001 | `repos/CFDrs/crates/cfd-1d/**` (15 files, ~50 sites) | surfaced in Session 6 `cargo clippy --workspace --all-targets -- -D warnings` during tyche-break verification; pre-existing pedantic lint floor debt in cfd-1d independent of tyche | Peer brings cfd-1d to the workspace `-D warnings` floor: ~26 `uninlined_format_args`, ~6 `manual_map`, ~5 `useless_conversion` to `f64`, 3 `result_large_err` (Err variant >=160 bytes in `PrimarySolveError`), 2 `manual_range_contains`, 2 `field_reassign_with_default`, and ~6 scattered (`complexity`, `explicit_into_iter_loop`, `empty_line_after_doc_comments`, `iter_cloned_collect`) | ⏳ open until 8-warning residual baseline clears (first decrement landed 2026-07-23 by atlas-meta coordinator PR #312 `4ccd4f85`): 54 pedantic warnings -> 8 via mechanical `cargo clippy --fix` (12-file span, 26 `uninlined_format_args` + 20 sibling auto-fixables `unnecessary_map_or`/`useless_conversion`/`.into_iter`/`.into`). Residual 8-warning baseline: 3 `result_large_err`, 1 `very_complex_type`, 1 `empty_line_after_doc_comments`, 3 doc-test wrap — all manual-only categories peer-architectural) |

## Watchpoints — 2026-07-21 Session 7 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| CFDRS-PERF-SLOW-001 | `repos/CFDrs` heavy GPU/3D-CFD integration tests | Session 7 `cargo nextest run --no-fail-fast --workspace` on peer commit `fca1a9a9` (post-tyche-migration) reports 3 tests timing out at the 30s slow budget: `cfd-3d::poiseuille_test::validate_poiseuille_flow` (30.183s), `cfd-suite::cross_fidelity_blueprint::cross_fidelity_blueprint_complex_branching` (30.212s), `cfd-validation::benchmarks::threed::bifurcation::tests::test_bifurcation_flow_3d_murray_and_mass` (30.181s) | Peer roots-cause each timeout per `engineering_gates` (optimize the real components, never relax the slow-timeout bound; never shrink coverage); the 3072/3075 PASS baseline moves to 3075/3075 PASS without TIMEOUTs | ✅ closed (2026-07-23 Session 13 coordinator takeover: `validate_poiseuille_flow` PASS in 0.342s via PR #311 `22ddc27d` perf(cfd-3d) — hoist MidNodeCache + vertex_positions across Picard iter + lower with_direct_threshold 100_000→512 routing medium saddle-point systems to GMRES+AMG / GMRES+BlockDiag (root cause: `leto_ops::SparseLuSolver` is a misnamed dense partial-pivoting LU, O(n^3)). `cross_fidelity_blueprint_complex_branching` closed earlier by peer `153b0ed9` on 2026-07-13 (0.799s). `test_bifurcation_flow_3d_murray_and_mass` re-verified 1.934s at CFDrs main `22ddc27d`. Full cfd-3d suite: 394/394 PASS. Strategic TODO recorded as ATLAS-LETO-OPS-SPARSE-LU-001 [arch] for upstream real sparse LU/Cholesky in leto-ops) |
| CFDRS-LINT-CASCADE-001 | `repos/CFDrs/crates/cfd-math/src/iterators/stencils.rs:101`, `cfd-math/src/iterators/windows.rs:108`, `cfd-schematics/src/heatmap/mod.rs:286`, `cfd-schematics/src/interface/presets/composite/specialized/parallel_lane.rs:24` | Session 7 `cargo clippy --workspace --all-targets -- -D warnings` halts on 4 site-level errors before reaching cfd-1d/cfd-2d/cfd-3d/cfd-core/cfd-validation/cfd-optim/cfd-suite/cfd-io/cfd-python/xtask; the 4 blockers are `needless_question_mark` ×2 in cfd-math and `print_literal` + `manual_filter` in cfd-schematics | Peer remediates the 4 cascade-blocking clippy errors; once unblocked, run `cargo clippy --workspace --all-targets -- -D warnings` to measure the actual `cfd-1d` baseline vs the Session 6 ~50-site estimate (which may have been inflated by the prior `cargo check`-then-clippy masking) | ⏳ open (2026-07-21 Session 7 cataloged; independent of tyche migration; blocks the `CFDRS-CFD1D-LINT-001` baseline measurement; recorded for the CFDrs peer) |

## Watchpoints — 2026-07-21 Session 8 (atlas-meta coordinator view)

No new atlas-meta-owned watchpoints. Session 8 activity:

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| LETO-VERIFY-CONTENTION-001 | `repos/leto` at `b7224832e` `perf(leto-ops): Vectorize UDU weighted-dot` | Session 8 bounded subagent attempt to run `cargo nextest run --no-fail-fast --workspace` + `cargo test --doc --workspace` on leto post-gitlink-reconcile; blocked by peer-held `CARGO_TARGET_DIR` lock (peer `cargo-nextest.exe` PID 48380 live, not orphan). This is verification contention, not a defect | Atlas-meta bounded nextest + doctest re-run when peer build activity ceases (no live `cargo-nextest.exe` in `tasklist`); per `concurrent_agents` peer's green run on this shared tree IS authoritative evidence on shared branch | ✅ closed (2026-07-21 Session 8 closing annotation: peer cargo-clippy shift released lock; atlas-meta bounded nextest 592/592 PASS rc=0 (slowest 1.023s, zero timeouts) + doctests 9/9 PASS (leto 1, leto-ops 8, leto-python 0). Differential oracles `*_matches_numpy`/`*_matches_scipy` over vectorized UDU weighted-dot kernel pass. Value-semantic correctness preserved atop `9a03735 refactor(leto)!: Retire ndarray boundary`) |

## Watchpoints — 2026-07-21 Session 9 (atlas-meta coordinator view)

atlas-meta main re-oriented at `abbec58` after peer landed 17 commits in the gap since Session 8 close. All Session 8 dispatch items superseded by peer work (user's "proceed as recommended" authorized the no-op continuation). New watchpoint evidence recorded; no new defects cataloged.

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| CFDRS-LINT-CASCADE-001 (originally Session 7) | `repos/CFDrs/crates/cfd-math/src/iterators/stencils.rs:101`, `cfd-math/src/iterators/windows.rs:108`, `cfd-schematics/src/heatmap/mod.rs:286`, `cfd-schematics/src/interface/presets/composite/specialized/parallel_lane.rs:24` | Session 7 catalog of 4 site-level clippy errors blocking `cargo clippy --workspace --all-targets -- -D warnings`. Session 9 audit: peer commit `dc256705` remediated sites 1-3 (stencils.rs, windows.rs, heatmap/mod.rs) via `let-else` idiom + SVG format-arg fix. Site 4 (parallel_lane.rs:24) was clean at HEAD `7a521343` — the code is already in the `Option::filter` form `manual_filter` recommends; the watchpoint entry was stale when filed | n/a — peer has remediated or never needed remediation | ✅ closed (2026-07-21 Session 9 bounded subagent audit at HEAD `7a521343`: `cargo clippy -p cfd-schematics --all-targets -- -D warnings` exits rc=0 zero warnings. All 4 watchpoint sites verified clean; clippy gate no longer blocks the cfd-1d lint baseline measurement; `CFDRS-CFD1D-LINT-001` baseline measurement is now unblocked and ready for peer to schedule under the ratchet) |
| HERMES-ADVANCE-001 (Session 9 catalog) | `repos/hermes` gitlink pin `004e6a492` vs inner HEAD `53b83165` | Single commit delta `perf(hermes): Unchecked CSR SpMV tail gather` touched only `CHANGELOG.md` + `spmv.rs` (+8 −1). nextest 388 tests 383 PASS / 5 ABORT — but all 5 aborts are in disjoint gemm/tiling dispatch tests (`ptr::replace` alignment UB on Windows), NOT in the CSR SpMV path (CSR tests `test_spmv_csr_*` all pass). Doctests 18/18 PASS, 10 ignored (cfg-gated) | n/a — peer advanced atlas-meta gitlink in the gap via peer's own `99699ea build(atlas): advance hermes gitlink — SpMV unchecked tail`. Atlas-meta's planned advance was made redundant | ✅ closed (made redundant by peer — atlas-meta main `abbec58` pins hermes at `53b83165`). Residual: the 5 gemm/tiling `ptr::replace` aborts are a pre-existing Windows UB defect — recorded below as HERMES-GEMM-UB-001 |
| HYPERION-PHASE-0-001 (Session 9 catalog) | new stack member `hyperion` at `D:\atlas\repos\hyperion\` (untracked dir, NOT in `.gitmodules`) + ADR 0030 `hyperion-photon-optical-promotion.md` + atlas-meta `0b97ba0` / `4ff5c07` consolidation commits | Peer created ADR 0030 consolidating photon/optical law across Asclepius/Leto/Hephaestus/Helios into a new standalone crate `hyperion` (v0.1.0, edition 2024, deps aequitas/eunomia/proteus). Phase 0 = scaffold + dep alignment; phase 1 = register as atlas submodule. Peer's kwavers tree has 40+ dirty files mid-Hyperion-extraction — the migration is in flight | n/a — Hyperion `7b4561b`, Helios `105a093`, Kwavers `5fc6f0419`, and CFDrs merge `69323418` complete the deletion ledger; Atlas records the exact provider and consumer gitlinks | ✅ closed (2026-07-22: `.gitmodules`, stack map, ADR 0030, PM state, and the 25-package count are synchronized; Ares and Prometheus remain separately evidence-gated) |
| HERMES-GEMM-UB-001 (Session 9 catalog — filed during HERMES-ADVANCE-001 audit) | `repos/hermes/crates/hermes-simd/tests/host_capability_tests.rs` + `crates/hermes-simd/tests/tiling_tests.rs` — 5 GEMM dispatch tests abort | `cargo nextest run --workspace` reports 5 ABORTs: `local_gemm_dispatch_matches_scalar_reference_for_irregular_shapes` (0.807s), `test_gemm_int8_signed_differential` (0.362s), `test_gemm_bf16_size_16` (0.396s), `test_gemm_int8_high_level` (0.427s), `test_gemm_bf16_high_level` (0.471s). All panic at `core::ptr::mut_ptr.rs:1495:18: unsafe precondition(s) violated: ptr::replace requires that the pointer argument is aligned and non-null`. Non-unwinding panic on Windows surfaces as `STATUS_STACK_BUFFER_OVERRUN` (0xc0000409) → abort. Pre-existing — reproducible at peer's pre-advance pin `004e6a492` as well as HEAD `53b83165`. Disjoint from the CSR SpMV path this gitlink advance introduced | Peer root-causes the `ptr::replace` alignment precondition violation in the GEMM tiling-remainder write (likely a `*mut T` produced from an under-aligned slice/holder feeding a packed-view bridge). Recommended first probe: `RUST_BACKTRACE=1 cargo nextest run -p hermes-simd --test tiling_tests test_gemm_bf16_size_16`; then Miri on the gemm kernel (SIMD intrinsics Miri-unreachable → ASan/TSan per unsafe-discipline for the load/store surface) | ⏳ open (2026-07-21 Session 9 cataloged; pre-existing defect not caused by the CSR SpMV advance. Independent of the hermes gitlink `004e6a492 → 53b83165` advance that peer landed in this session's gap. Recorded for peer scheduling since hermes is a peer-owned source tree) |
| EUNOMIA-DOCTEST-001 (Session 9 catalog — closed same session) | `repos/eunomia/crates/eunomia/src/relative_eq.rs` lines 241, 338 — `assert_relative_eq` and `relative_eq` doctests | Early Session 9 bounded subagent at eunomia 0.6.0 published surface reported 2 doctest FAILs with self-contradictory `epsilon = 1e-10, max_relative = 1e-10` example bounds for `1.0_f64` vs `1.0000001` (gap `1e-7`). Peer landed `884d193 feat(eunomia): Add relative equality` + `3e4f9eb docs(eunomia): Close equality provider gate`. Atlas-meta gitlink advance via peer's `a5279bf build(atlas): Advance Eunomia provider` reconciled the pin | n/a — peer closed the doctest gate | ✅ closed (2026-07-21 Session 9 recheck at HEAD `3e4f9eb`: doctests 9/9 PASS, zero failures, zero ignored. The two previously-failing examples now pass value-semantically against consistent bounds. Eunomia is release-ready at HEAD `3e4f9eb`) |
| HELIOS-APPROX-EUNOMIA-001 (Session 9 catalog) | `repos/helios` HEAD `105a0939 refactor(helios): migrate approx -> eunomia assert_relative_eq workspace-wide` | Peer integrated the workspace `approx -> eunomia::assert_relative_eq` migration into helios. Verification at HEAD `56e3572` (1 commit unpushed then; now pushed to origin/main = `105a0939`): nextest 251/251 PASS rc=0, slowest test 1.036s (`helios-imaging fbp::tests::quantum_noise_degrades_recon_and_scales_with_flux`), doctests 11/11 GREEN (helios-python cdylib is the only structural warning — expected). `approx` fully excised from helios `Cargo.toml` | n/a — peer landed + pushed; atlas-meta gitlink advanced via `61e209e` | ✅ closed (2026-07-21 Session 9 verification: helios `approx -> eunomia` migration is GREEN at HEAD `105a0939`. Caveat: helios still uses edition 2021 / resolver 2 (project-wide observation, not a migration defect). Dirty mdBook migration_*.md files are peer's pending book content not part of the migration commit) |

## Residual CFDrs watchpoints carried forward (still peer-owned, still open)

| ID | Status | Note |
|---|---|---|
| CFDRS-PERF-SLOW-001 | ✅ closed (2026-07-23 Session 13) | All 3 perf-slow tests under 2s at CFDrs main `22ddc27d`: `validate_poiseuille_flow` 0.342s (Session 13 perf PR #311), `cross_fidelity_blueprint_complex_branching` 0.799s (peer `153b0ed9` 2026-07-13), `test_bifurcation_flow_3d_murray_and_mass` 1.934s. Root cause of the last standing one (`validate_poiseuille_flow`) was a misnamed dense LU masquerading as sparse LU in `leto_ops::SparseLuSolver` plus per-Picard-iter cache recomputation; both root-caused and fixed at the algorithm (no threshold relaxation, no test shrinkage, no slow-timeout bound change). Strategic TODO — real sparse LU upstream in leto-ops — filed as ATLAS-LETO-OPS-SPARSE-LU-001 [arch] |
| CFDRS-CFD1D-LINT-001 | ⏳ open (now unblocked) | Session 9 closure of `CFDRS-LINT-CASCADE-001` unblocks the cfd-1d pedantic-baseline measurement. The original Session 6 estimate was ~50 sites. Peer can now run the full `cargo clippy --workspace --all-targets -- -D warnings` and schedule the actual baseline under the ratchet |
| ATLAS-LETO-OPS-REFACTOR-001 (new 2026-07-23) | ⏳ open | `leto-ops` (`repos/leto` HEAD `9346413`) is presently uncompilable on the path-dep graph (29 type/visibility errors across `crates/leto-ops/src/application/linalg/iterative/preconditioners/jacobi.rs`, `ilu.rs`, `cg.rs`, `sparse/csr.rs` mod-privacy + generic-`T`-vs-`usize` index comparison). Last destructive code commit `9a82a4d feat(leto-ops): add sparse_lu_solve and SparseLuSolver`. Subsequent commits have been audit doc/test only. Peer is mid-refactor (`ATLAS-LETO-OPS-SPARSE-LU-001` owner context). Assist-ladder (2) decision: skip — fresh and actively held by the leto peer; no claimable periphery in `leto-ops` source that doesn't collide with peer's refactor. Re-verify when peer stabilizes; not coordinator-actionable |
| CFDRS-CFD1D-LINT-001 | ⏳ open (first decrement done; 8-warning residual baseline established) | First ratchet decrement landed by atlas-meta coordinator via PR #312 `4ccd4f85` (squashed merged 2026-07-23). `cargo clippy --fix --allow-dirty -p cfd-1d --all-targets` applied 12-file mechanical remediation: 26 `uninlined_format_args` + 20 sibling auto-fixable lints (`unnecessary_map_or` -> `is_some_and`, `useless_conversion` -> `to_vec`, minor `.into_iter()` / `.into()` cleanups). Baseline: 54 pedantic warnings -> 8 (3 `result_large_err`, 1 `very_complex_type`, 1 `empty_line_after_doc_comments`, 3 doc-test wrap). Net delta -46 warnings (-85%); 728/728 cfd-1d nextest pass post-runtime. Residual 8-warning baseline parked as peer-architectural decisions (error-type redesign, type-factor, doc-comment cleanup) — next decrement candidate |

## Provider integration audit queue — 2026-07-20

| ID | Class | Status | Owner/scope | Acceptance |
|---|---|---|---|---|
| HARM-PROMOTE-001 | [arch] `[minor]` | done — PR #57 merged `0b0d01d` | harmonia / horae / athena-core / eunomia / atlas-meta | `repos/harmonia` published to `https://github.com/ryancinsight/harmonia` (HEAD `cf6ce3e`, CI run `29753063192` green); Atlas `.gitmodules` entry recorded; parent gitlink advanced; ADR 0023 Status `Accepted`; README current-stack table reconciled to 20 packages. |

## ATLAS-WORKTREE-001 — Canonical lane root consolidation [patch] — in progress

- Owner: Codex `/root` (stale-claim takeover 2026-07-22); scope: worktree lane
  locations only, no member-repo code.
- Done 2026-07-21: 24 verified-duplicate standalone clones (12 at
  `D:\worktrees`, 12 at `D:\atlas\worktrees`; all detached, clean, HEADs
  contained, zero local branches), the SHA-keyed `.atlas-provider-checkout`
  cache, and the empty `D:\worktrees\atlas` were removed; stray
  `report/figures` SVG was rescued to `repos/report/figures/`.
- Done 2026-07-22: the legacy `D:\worktrees` root is absent, 16 redundant
  junction aliases are removed, and the former scratch scripts are absent.
  The only remaining lanes are the active Atlas RITK graph lane and Kwavers
  portability lane under the canonical `D:\atlas\worktrees/` root. Each repo
  remains within the main-tree-plus-one-lane bound.
- Residual: merge Atlas PR #86 after RITK PR #49 and merge Kwavers PR #312
  after PR #313, then remove both completed lanes and their branches.

## ATLAS-TARGET-001 — One build cache, one debug budget [patch] — in-progress (residual)

- Owner: Codex `/root`; last-update: 2026-07-22; scope: cache trees and
  profile sections only, no simulation logic.
- Done 2026-07-21: 18 stale cache forks deleted (repo-local `target/`, `target_isolated`, `target_benches`, nested crate `target/`) reclaiming 177.8 GB; `moirai` dev/test profiles aligned to line-tables-only/deps-none (was `debug = true`, pushed `946b4a7`); root `.cargo/config.toml` gains `[profile.dev.build-override] debug = false`. Policy: AGENTS.md performance_engineering "one build cache per stack" — a discovered fork is disposable derived state.
- Done 2026-07-22: the root test profile now matches the development profile:
  workspace test crates retain line tables, while dependencies, build scripts,
  and procedural macros emit no test debuginfo. This closes the configuration
  path through which Nextest could repopulate the shared cache with full
  symbols.
- Done 2026-07-22: removed two abandoned full-target `du` scans that had
  traversed the cache for about 2.5 hours, then pruned the idle incremental
  tree. Its 27,085 session directories occupied 525,183,672,320 bytes
  (approximately 489 GiB); the five-minute deletion preserved shared
  dependencies and linked artifacts, and a subsequent build recreated only
  three current session directories. This is operational reclamation, not a
  clean-build footprint claim.
- Done 2026-07-22: Kwavers PR #307 merges as `0602c1fd4`. Its broad
  dependency graph inherits development `opt-level = 1` instead of wildcard
  `opt-level = 3`, restoring exported generic sharing. Uncached feature-build
  steps fall 18–45%; exact head `909bcdfc7` passes 26 hosted checks, full-grid
  PSTD remains below 25 seconds, and a clean debug tree measures
  16,771,464,617 bytes across 6,109 files. Cargo removes the formerly blocked
  `repos/kwavers/target_isolated` plus six other obsolete private targets:
  9,363 files and approximately 4.49 GiB, without touching `D:/atlas/target`.
  Atlas-meta format and warning-denied Clippy pass; checkout-path Nextest passes
  11/11 in 3.746 seconds and doctests pass 1/1 in 1.93 seconds from the primary
  root against the shared cache.
- Done 2026-07-22: a stack-wide sweep removed 13 additional disposable target
  forks and reclaimed 18.465 GiB; no repository-local target directory
  remains. Before the remaining hosted checks, `cargo clean` against the
  canonical `D:/atlas/target` removed 68,854 files and 20.7 GiB. The configured
  shared cache then measured 0 bytes, below the 10-GiB operating budget; the
  final sweep must repeat after any later local gate.
- Residual: audit member workspaces with their own `[profile.*]` or `.cargo`
  sections (helios, hermes, CFDrs, coeus, ritk, mnemosyne). CFDrs currently
  compiles workspace tests at `opt-level = 2`; its dirty peer-owned workspace
  and active full test build preclude an unmeasured profile edit. Re-open that
  member as a separate measured increment after the peer work integrates,
  retaining only runtime- or profiling-justified deviations. Atlas-meta root
  worktrees copy `.cargo/config.toml` and therefore resolve a lane-local target;
  run meta-tool verification from the primary root until a portable route to
  the canonical cache is implemented and tested. One live sample found three
  independent top-level builds, five Cargo processes, and 23 concurrent `rustc`
  processes on a 24-thread/31.7-GiB host. Compare unchanged single- and
  concurrent-build workloads before selecting a global jobs cap; the sample
  proves oversubscription exposure, not an optimal cap.

## ATLAS-BENCH-BUDGET-001 — Wall-clock budgets for benches and examples [patch] — in-progress (enforcement merged; sweep residual)

- Owner: Claude (user-directed claim 2026-07-22); home: tools/criterion-regression (ADR 0024); policy: AGENTS.md engineering_gates "Runtime budgets" + performance_engineering "Benchmark time budget".
- Outcome: no bench binary or CI example exceeds its committed bound; suite time is designed, not emergent.
- Scope: (1) gate smoke — bench binaries run single-iteration (criterion `--test`) under the standard 30s/60s budget; (2) timing runs — per-binary wall-clock bound (default 300s) enforced in the criterion-regression runner/CI; (3) CI-safe examples complete within the test budget as scaled demos; (4) audit the 164 bench files (moirai 47, CFDrs 29, kwavers 22, hermes 12, ritk 10, rest ≤8) against the analytical time model — zero suites declare measurement_time/sample_size today, i.e. all run unbudgeted criterion defaults with sweeps; apply flat sampling for slow iterations, geometric sweeps, smallest regime-exercising inputs; where a single iteration is genuinely slow, profile and optimize the production kernel (farsight), never delete the bench or raise the bound in the offending diff.
- Acceptance: budget enforcement merged in the runner + full-stack bench sweep completes within per-binary bounds; breaches root-caused and fixed or filed with derivation.
- Done 2026-07-22: `enforce-budget` subcommand in tools/criterion-regression — modes smoke (bench single-iteration, 60s), timing (full measurement, 300s), examples (60s), `--bound-seconds`/`--skip` overrides. Compiles unbounded, executes binaries directly (killing cargo would orphan the bench grandchild) with CARGO_TARGET_DIR pinned to the shared target (no minted repo-local target/), fail-closed exit. Validated: themis smoke/timing clean; eunomia timing at 5s bound → breach terminated mid-measurement, exit 1. Gates: clippy pedantic clean, 21/21 nextest, doc clean.
- Residual: full-stack sweep at committed bounds (probe per repo; live peer scopes deferred to their completion), CI wiring per repo workflow convention, and suite resizing per breach (flat sampling, geometric sweeps) or kernel optimization per farsight.
## ATLAS-BUILD-STRUCTURE-001 — Consolidate leaf binaries; compiler-last dev profiles [patch] — in progress

- Owner: Codex `/root`; last-update: 2026-07-23; completed vertical slice:
  `repos/coeus/coeus-ops/tests/**` only. Peer-owned member profiles and other
  repository test trees remain out of scope.
- Claim: consolidate the 36 flat `coeus-ops` Rust integration-test binaries
  into one hierarchical `tests/ops.rs` harness with `tests/ops/*.rs` modules,
  preserving all 87 test functions and their value-semantic assertions. The
  target-count reduction and test-count parity are the acceptance oracle.

- Policy: AGENTS.md performance_engineering "Debug-tree and compile-time structure" + "Compiler-last optimization order". Monomorphization stays the design default — an instantiation codegens identically to its hand-written equivalent; the debug-tree multiplier is leaf-binary count and duplicate paths, never genericity.
- Evidence 2026-07-22: ~950 leaf binaries stack-wide, each a full link with own incremental cache and PDB — tests/examples per repo: CFDrs 118/66, coeus 110/2, kwavers 94/62, consus 55/0, ritk 28/7, hermes 20/4, moirai 15/22, melinoe 15/1, others <=11. Dev-profile audit: helios declares wildcard `[profile.dev.package."*"] opt-level = 3` (the pattern removed from kwavers in PR #307); kwavers `opt-level = 1` with documented 5-10x PSTD justification is the sanctioned named-and-measured form. The shared incremental tree reached 27,085 session directories and approximately 489 GiB in five days, making leaf-target consolidation and CI `CARGO_INCREMENTAL=0` the next measured size levers.
- Scope: (1) consolidate each repo's tests/*.rs into one-or-few area harness binaries (`tests/<area>/main.rs` with modules) — nextest still isolates per test function in its own process, so coverage and isolation are unchanged while link count, incremental caches, and debug artifacts drop by the file count; worst offenders first (CFDrs, coeus, kwavers, consus, ritk, hermes); (2) merge near-duplicate examples per consolidation_discipline; (3) replace wildcard dev dependency opt raises with named, measured, per-package exceptions (helios first, peer-held — coordinate via board); (4) record per-repo binary-target count and debug-tree size before/after as the acceptance measurement.
- Acceptance: binary-target census reduced and recorded per repo; debug-tree size delta measured against the shared cache; test function count unchanged (no coverage loss); no wildcard dev opt-level overrides remain without a named measured justification.
- Completed vertical slice: Coeus `coeus-ops/tests` moved from 36 flat
  integration targets to one `ops` target with ten operation-family
  directories. The harness exposes 87 integration tests and the exact
  package Nextest run passes 196/196; whole-workspace debug-tree measurement
  remains a later bounded slice.
- Evidence: warning-denied Clippy, package check, format, and diff checks pass
  on Coeus commit `f67789c4`; the 87 harness tests are unchanged by source
  count and all 196 package tests pass. This item is closed for the bounded
  Coeus slice; the broader stack-wide debug-tree delta remains open work.
- Coeus-NN slice complete at provider commit `95bb9090`: the existing
  `nn_tests.rs` harness and its already hierarchical `tests/nn/` modules stay
  intact while the 33 other direct test binaries move behind one `nn_ops`
  harness, preserving the 268 total package tests. The 34 direct test targets
  reduced to 2 (`nn_ops` and `nn_tests`); the exact package run passes
  268/268 with 0 skipped. Whole-workspace debug-tree measurement remains open.
- Coeus-autograd slice complete at provider commit `f8f6d665`: the existing
  `autograd_tests.rs` harness and `tests/autograd/` module tree remain intact
  while the three other direct targets move behind one `autograd_ops` harness.
  The four integration targets reduce to two; the exact package run passes
  94/94 with 0 skipped. Whole-workspace debug-tree measurement remains open.
- Next claimed slice: Coeus `coeus-tensor/tests` has 13 flat integration
  targets and 57 listed package tests. Move the operation-family leaves behind
  one `tensor_ops` harness without changing tensor production code or test
  assertions.

## ATLAS-BOOK-001 — Domain books teach the field; evict process content [patch] — todo

- Policy: AGENTS.md documentation_discipline "Domain book" — books teach physics/math from the ground up (governing equations with resolved citations, numerical methods, theory-to-API worked examples with regenerated figures); migration and changelog content belongs to versioning/CHANGELOG, never the book.
- Evidence 2026-07-23: three books carry internal-migration process parts — CFDrs `docs/book` Part VII "Atlas Stack Integration (Migration Reference)" (13 files incl. appendix_changelog.md, appendix_migration.md); helios Part VIII (13 files incl. appendix_changelog.md); kwavers Part VI (10 files incl. migration_quick_reference.md). All three repos peer-held at filing time — owners coordinate via board, disjoint from live scopes.
- Scope per repo: (1) delete the Migration Reference part and changelog/migration appendices from SUMMARY.md and the tree, salvaging any genuine theory-to-API mapping into usage chapters first (information preserved, then deletion — no orphaned SUMMARY entries; book builds green after); (2) audit the remaining book against the Domain-book rule — fundamentals-first structure, tested samples, figures from committed plotting code — and file chapter-gap DoR items; (3) repos with domain scope but no book (e.g. ritk, coeus, gaia, apollo, hephaestus) get an outline-first book item each.
- Acceptance: no migration/status/changelog chapters remain in any book; each touched book builds in CI with tested samples; gaps filed as DoR items per repo.
