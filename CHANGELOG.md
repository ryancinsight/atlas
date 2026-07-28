# Changelog

## Unreleased

- [minor] Advance the Leto/CFDrs provider graph to merged sparse-LU native-view
  ownership. CFDrs direct solves no longer stage the native RHS or returned
  solution through consumer-owned `Vec` buffers; no release is performed.

- Apply the shared line-table-only debug budget to test builds as well as
  development builds. Dependencies, build scripts, and procedural macros emit
  no ordinary test debuginfo, reducing Nextest artifact size and linker memory
  without changing optimization, assertions, or test workloads.

### Added

- File ADR 0030 to promote published Hyperion as the bounded photon/optical
  transport owner. The decision records the Aequitas → Proteus/Hyperion →
  integrator hierarchy, per-consumer deletion ledger, measurable consolidation
  effects, and the rule that P2 does not add Ares or Prometheus without a second
  production consumer and net deletion.

- Promote public Iris as the twenty-fourth Atlas package and file ADR 0029.
  Iris owns normalized color laws, fixed lookup tables, borrowed scientific
  views, and static render-backend contracts. RITK Snap and VTK consume the
  public provider directly and delete their independent color engines. CFDrs
  consumes `NamedColorMap` directly, deletes its local enum and formulas, and
  reduces each overlay range once while borrowing existing field maps. File
  formats, domain interpretation, UI state, and GPU mechanics remain local.

- Register public Asclepius remote default
  `eb65eaf7bf83bbd6ad38778fc5e2b534b01ac6aa` as the twenty-third Atlas
  package and file ADR 0028. The law core and one-way Coeus adapter merge at
  `794f8c3`; Asclepius owns typed gEUD, TCP, NTCP, CEM43, Arrhenius damage,
  and independent-response composition over Aequitas and Eunomia. Helios
  `33bba34` and Kwavers `1cb01fe` consume the public provider directly, with no
  sibling-directory source patch. The stack map, dependency graph, provider
  table, naming registry, roadmap, layout, ADR index, backlog, checklist, and
  gap audit share that boundary. Hephaestus `74dec5d` aligns its Aequitas
  response quantities with the registered provider graph.

- File ADR 0025 (`docs/adr/0025-proteus-material-property-promotion.md`) at
  `Accepted` to record the Proteus promotion decision. Proteus owns shared
  material-property and constitutive-law contracts: validated thermophysical
  newtypes (`MassDensity`, `SpecificHeatCapacity`, `ThermalConductivity`)
  over Aequitas quantities and Eunomia scalars with a GAT-based static
  constitutive seam (`ConstitutiveLaw<Law>`, `ConstantLaw`, `NoState`) and
  `Cow<str>` material identity. Cross-references Proteus ADR 0001, ADR 0002,
  0005, 0021, and 0023 in the ADR INDEX cross-walk.

- File ADR 0026 (`docs/adr/0026-tyche-uq-promotion.md`) at `Accepted` to
  record the Tyche promotion decision. Tyche owns reproducible uncertainty
  studies: counter-stream random-access Latin hypercube designs,
  index-addressed ensemble execution, online Welford/Chan moments, Pearson
  screening, finite-sample split-conformal calibration, and Moirai/Consus
  provider adapters over a `no_std + alloc` core with GAT response seams
  and const-generic numeric widths. Cross-references Tyche ADR 0001, ADR
  0002, 0005, 0023, and 0025 in the ADR INDEX cross-walk.

- Add a `build(atlas)` entry advancing the coeus gitlink from `56fa49a` to
  `c290f3e` after bumping the hephaestus path-dep pins 0.17.0 -> 0.18.0 to
  restore Atlas graph closure following Peer's v0.18.0 hephaestus tag
  advance. Add a matching leto gitlink advance 4158b8e -> 02d74fd wrapping
  PR #55 (perf/leto-ziggurat-normal).

- Add ADR 0027, the Atlas-owned
  `tools/checkout-path-dependencies` Rust engine, and its composite action.
  Consumer Cargo dependency, patch, and replacement paths resolve through exact
  Atlas gitlinks; moving refs, duplicated provider lists, dirty or
  wrong-revision reuse, unknown providers, missing provider URLs, missing
  manifests, and destination escapes fail closed.

- Add ADR 0024 and the Atlas-owned `tools/criterion-regression` Rust gate for
  phase-reversed, counterbalanced Criterion median regressions, 5% family-wise
  error control, and fail-closed missing or mismatched evidence.

- File ADR 0023 (`docs/adr/0023-harmonia-coupling-promotion.md`) at `Proposed`
  to promote `harmonia` as the Atlas coupling-mechanics provider. Phase 0
  contract is two-partition synchronous Jacobi `PartitionedPair<M, T,
  FIRST_SUBSTEPS, SECOND_SUBSTEPS>` with const-generic heterogeneous
  subcycling over Horae subcycle plans and Athena Core convergence policy;
  static transfer and relaxation policies are ZSTs and the workspace
  allocates only at construction. Local Phase 0 evidence (14/14 nextest,
  1/1 doctest, clippy/rustdoc clean) is recorded but the promotion is
  blocked until `repos/harmonia` publishes to a public remote.

- Add a `harmonia` row to the Atlas current-stack table and a coupling
  entry to the Provider ownership table in `README.md`. Retire `harmonia`
  from the Candidate packages roadmap. Add ADR 0023 to the ADR INDEX with
  the topic-tag cross-walk. Surface the pending publish as the
  `HARM-PROMOTE-001` audit row and `HARM-PUBLISH-001` watchpoint in the
  2026-07-20 PM sections of `backlog.md`, and as a 2026-07-20 State refresh
  row in `gap_audit.md`.

### Changed

- Advance Apollo to PR #64 merge `614939fd`, Hephaestus to portable-wheel PR
  #63 merge `b726b39f`, and Moirai to PR #83 merge `ddb665e9`. The Moirai head
  preserves saturated indexed work on the caller and adds a borrowing parallel
  scope; the follow-on Kwavers lock and serialization cleanup remains tracked
  by ATLAS-INTEGRATION-042.

- Advance Moirai through PR #84 merge `e4d2855` and default closeout
  `c870eed`. The cleanup removes only the unused `moirai-core` nightly TLS
  build gate while retaining the platform and executor fast paths; exact
  default run `29963043374` passes Rust and all three wheel platforms.

- Advance Kwavers to PR #307 merge `0602c1fd4` and close its debug build
  budget. Removing wildcard dependency `opt-level = 3` restores generic sharing
  and reduces uncached feature-build stages by 18–45% while full-grid PSTD
  remains below 25 seconds. Record the 16,771,464,617-byte clean debug baseline
  and remove approximately 4.49 GiB from seven obsolete private target trees;
  the shared `D:/atlas/target` cache remains intact. A subsequent stack sweep
  removes 13 more target forks (18.465 GiB), verifies zero repository-local
  targets, and cleans 68,854 files / 20.7 GiB from the canonical cache after
  the completed local gates, leaving the measured shared tree at 0 bytes.

- Close the Atlas Criterion consumer rollout and advance Kwavers to PR #308
  merge `402d9695`. Kwavers PR #306's bounded same-path head passes complete
  candidate smoke, four counterbalanced 21–23 minute pair jobs, and aggregate
  classification while every non-critical benchmark remains covered by one
  candidate execution. PR #304's Tyche collocation integration passes its
  exact-head ordinary CI, architecture, and legacy-audit workflows. PR #308's
  exact documentation head `8373c8bb0` passes CI `29890089765`, architecture
  `29890089803`, and legacy audit `29890089797`.

- Advance P2 from specification to execution. Hyperion `064a189` is public,
  anonymously readable, and hosted-green. Helios `105a093` completes the first
  photon/optical deletion ledger and passes hosted run `29883200466`; Kwavers
  and CFDrs remain. Ares remains
  blocked on Proteus elastic-property consolidation and a second structural
  consumer; Prometheus remains
  blocked on Kwavers/Horae cleanup and a second production reaction-network
  consumer. Package count is not an acceptance criterion.

- Document the supported four-job schedule for long consumer benchmark
  instruments: two isolated, co-located base-first pairs and two isolated,
  co-located candidate-first pairs. The Atlas classifier still requires
  unanimous direction, identical benchmark universes, complete estimates, and
  the derived 5% family-wise confidence bound; no comparison mixes
  measurements from different runners or fixed checkout identities.

- Add the registered Proteus and Tyche packages to the README naming registry.

- Move the shared Cargo target configuration from `repos/.cargo` to the Atlas
  root so root tools, provider repositories, and linked worktrees beneath
  `worktrees/` resolve one `target` cache. Reconcile Apollo, Helios,
  Hephaestus, Leto, and Tyche gitlinks with their fetched public defaults.

- Promote public Harmonia as the twentieth Atlas package. Phase 0 owns
  transactional two-partition Jacobi coupling, borrowed interface transfer,
  relaxation, and heterogeneous subcycling over Horae and Athena Core. Record
  the fetched remote-default gitlink and ADR 0023.

- Clarify the parent-gitlink revision contract and safe submodule inspection in
  the Atlas README. Correct the roadmap so Harmonia composes Horae and Athena
  without depending on material-law ownership. Advance Athena to `96fb26d`
  with external observer construction and package documentation, and Horae to
  documentation merge `92af1a2`.

- Promote Horae and Athena as public Atlas packages. Horae owns typed
  time-integration policy over Aequitas. Athena owns shared PCG and restarted
  right-preconditioned GMRES recurrences over Leto CPU and Hephaestus WGPU,
  and Leto no longer exports duplicate iterative-solver recurrences. Record
  both public gitlinks, advance Leto to PR #54 merge `1752058`, and make
  `.gitmodules` the build-driver package-set SSOT.

- Advance Kwavers to PR #295 merge `49c116f`, replacing its bubble-energy
  `uom` ownership with Aequitas quantities and correcting the heat-capacity
  dimensional law. Pin CFDrs at PR #298 merge `7c37f7f`, where typed spacing
  reaches Hephaestus. Replace the parent graph's local-only `156531e` and
  `a34a01d` gitlinks with fetched merged defaults after their consumer gates
  pass.

- Advance Hephaestus to PM closeout PR #52 merge `cdfcd0c`; runtime code and the
  verified Eunomia 0.6 provider closure remain unchanged.

- Advance Hermes to PR #11 merge `6f9b81f`, locking Eunomia 0.6 after its
  raw-half retirement. Advance Leto to the exact PR #48 merge object
  `bb03244f05a9c43c318d103225c3ccad07e9fad9`, preserving the merged
  Box-Muller paired-normal performance increment.

- Advance Eunomia to PR #48 merge `df77dfd`, removing its production
  `half` dependency and foreign raw-half numeric/cast surface. Advance
  Hephaestus to PR #51 merge `594d57a`, whose reproducibility lock resolves
  Eunomia 0.6.0, Hermes 0.4.0, and Leto 0.39.0 with 312/312 provider tests.

- Tombstone superseded CR-2, RITK, and Kwavers migration queues after their
  recorded closures; refresh the provider/consumer stack table to the 16
  fetched remote-default gitlinks.

- Advance Eunomia to `c196db5`, Hermes to `c9bbdf8`, and Leto to `7afcbd0`.
  Eunomia owns exact reduced-format bit and float-element contracts; Hermes and
  Leto remove raw `half` public ownership in favor of Eunomia `F16`/`Bf16`.
  Reconcile the cumulative Coeus pointer at `5ee07a2` and RITK pointer at
  projection-hardening PR #44 merge `688eb8e`; peer working state remains
  outside the parent commit.

- Advance Helios to PR #7 merge `79b09e9`; its reproducibility lock now
  resolves Apollo 0.25.0, Eunomia 0.4.0, Leto 0.38.2, and Hephaestus 0.17.0
  and contains no `num-complex` package.

- Record Coeus PR #212 merge `bb97cc6` as the NN benchmark-provider closure.
  Burn is absent while all 211 operation groups and 424 native
  Sequential/Moirai measurements remain. The locked graph resolves Eunomia
  0.4.0, Leto 0.38.2, and Hephaestus 0.17.0.

- Record Eunomia PR #39 merge `49dc115` as the canonical sub-byte conversion
  cutover, then advance Leto PR #44 `f0b4d8e` and Hephaestus PR #50 `ed7d76e`
  after their reproducibility locks and full consumer gates resolve Eunomia
  0.4.0. The Atlas graph advances only these three merged defaults.

- Record Coeus PR #211 merge `4459d09` as the tensor legacy-benchmark removal;
  the consumer commits `Cargo.lock`, aligns Hephaestus `0.16.1`, and retains
  only Coeus Sequential/Moirai and Leto benchmark paths. Locked package
  verification, 56/56 Nextest, warning-denied Clippy, doctests, rustdoc,
  metadata, and residue scan pass.

- Record Apollo PR #53 merge `a31b8f8` as the Hephaestus lock convergence;
  `hephaestus-core`, `hephaestus-wgpu`, and `hephaestus-cuda` now select
  provider `cec0e33` after its Leto-owned legacy-math cleanup. Locked compile,
  402/402 Nextest, warning-denied Clippy, doctests, rustdoc, provider audit,
  hosted Rust/Python, and CodeRabbit checks pass.

- Record Hephaestus PR #47 merge `cec0e33` as the Leto-only CPU reference
  cleanup. Its WGPU/CUDA tests and comparative benches no longer depend on
  legacy array or linear-algebra crates; provider execution remains owned by
  Hephaestus and the Python `numpy` bridge remains an FFI-only edge.

- Record Apollo PR #52 merge `7303423` as the Leto merge-pin correction; both
  Leto packages now select Atlas default `3ac0d203` rather than parent
  `6a0e297`. Hosted Rust/Python/CodeRabbit checks pass; the external analyzer
  remains non-required.

- Advance RITK to PR #41 merge `a41e03b9`, aligning its lockfile and composite
  provider checkout with Apollo 0.25. All 22 repository and review checks pass,
  including cross-platform Nextest, Python 3.9–3.13, wheel, lint, dependency
  alignment, and migration audit.

- Record Apollo PR #51 merge `6dcb97c` as the provider-lock refresh; the
  consumer now resolves Hephaestus `93bc38e`, Eunomia `a2e4f390`, Leto
  `6a0e297`, and Moirai `8a51b2a7` from default sources. Locked 402/402
  Nextest and hosted Python/Rust/CodeRabbit checks pass.

- Advance CFDrs, Eunomia, Helios, Leto, and RITK to their merged
  default-branch commits while preserving active Apollo, Kwavers, and RITK
  feature work. The parent graph records only fetched remote defaults; Leto
  owns the remaining sparse-direct capability item needed to remove CFDrs
  `rsparse` without replacing its independent direct tier with GMRES.

- Record Hephaestus PR #46 merge `93bc38e` as the scan-limit theorem closure;
  provider ADR 0009 proves shared storage is `W` partials independent of line
  length, and the existing `L=513`, `W=256` WGPU/CUDA contracts cover the
  long-line path. KS-5b remains a measured performance follow-up.

- Record Apollo PR #50 merge `c874281` as the canonical Winograd trait
  ownership cutover; the obsolete internal `mixed_radix` re-export is deleted,
  all callers use `components::winograd`, and local 402/402 plus hosted Python,
  Rust, and CodeRabbit checks pass. The external `recurseml/analysis` error is
  non-required.

- Record Apollo PR #49 merge `e2f905a` as the obsolete execution-policy-wrapper
  removal; `apollo-fft` now uses Moirai's canonical threshold policy and keeps
  the provider boundary on Hephaestus. Local 393/393 package evidence and the
  hosted Python and Rust workspace lanes pass; the external
  `recurseml/analysis` failure is non-required.

- Advance the Hephaestus provider gitlink to PR #45 merge `3b68228`; memoized
  CUDA driver initialization and serialized context creation close the
  Windows concurrent-acquisition abort, with the full 109/109 CUDA suite
  passing while transfers and kernels remain concurrent.

- Advance the Hephaestus provider gitlink to PR #44 merge `d0eafc8` for the
  shared-memory tiled axis-scan kernels; the provider ADR and long-line
  WGPU/CUDA contracts remain the theorem and behavioral SSOT.

- Record Kwavers PR #294 merge `9eabc4e2` as the clean Hephaestus
  backend-kernel ownership increment; obsolete buffer and pipeline managers
  are deleted, the MVDR wall-clock assertion lives in Criterion, and the
  parent pin advances from `7c7d60f`.
- Record Kwavers `11e577c` as the clean Leto medium-accessor and abdominal
  geometry-contract head; Architecture Validation passes, while CI/CD coverage
  is blocked only by an external Codecov HTTP 429 upload response; PR #293
  retains the generated report gate and makes that transport non-blocking.
- Mark the Apollo `eb46e77` parent pin complete after Atlas PR #18; the
  verified Apollo `main` head is now `0b5d11c` after PR #48.
- Merge Apollo PR #46 and PM closure PR #47 at `eb46e77`; partition GPU
  dispatch verification into a deep private leaf and retain Hephaestus/Leto
  provider ownership.
- Advance the Atlas Apollo gitlink in PR #18 at `56ad179`.
- Keep Kwavers PR #292 at `54575460c` pending hosted coverage diagnosis and
  the remaining matrix; no dirty parent gitlink is advanced.
- Advance the RITK gitlink to its verified Apollo 0.24 source-checkout repair
  on `main`.
- Refresh Apollo, Hephaestus, Kwavers, Leto, and RITK gitlinks to the current
  provider graph; add ADR 0020 with the exact provider-graph closure theorem.
- Align public Atlas submodule pins with their fetched default branches.
- Advance Apollo, Helios, and RITK gitlinks to their merged default-branch
  commits after their provider and cross-platform CI closure.
- Advance the Apollo submodule pin after its concurrent provider-boundary merge.
- Advance the CFDrs and Hephaestus gitlinks after their typed GPU boundary
  closure.
- Advance the CFDrs gitlink after executable one- and two-dimensional
  validation examples replaced static reports on `main`.
- Advance the RITK gitlink after its merged lock metadata repair aligned the
  Hephaestus patch entries with the current provider graph.
- Register Kwavers and Helios in the Atlas public submodule roster.
- Reject bare `cargo test` in cross-stack drivers while retaining doctests.
