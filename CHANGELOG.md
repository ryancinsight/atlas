# Changelog

## Unreleased

- Reconcile the publication documentation with the live book inventory: all 24
  registered packages carry a book and Pages caller, 13 enable `mdbook test`,
  and 11 remain tracked for executable sample coverage. Root docs build and
  strict link checks cover all 24 books.

- Merge Aequitas PR #37 at provider default `c0542bf8` after its executable
  book examples and API snippets pass CI `32337268558` and the shared Pages
  build `32337268946`; the pull-request deployment is skipped.

- Publish Mnemosyne PR #65 to execute both included allocator examples through
  the shared package-staging book gate; local package and example evidence
  passes, with hosted verification pending.

- Open Hermes PR #56 at exact head `932468dac5ef4abadea4bdd12d62b420a4225ba7`
  for the shared package-staged book gate; four included examples and the SIMD
  architecture snippet pass direct local rustc/rustdoc checks, with hosted
  verification pending.

- Merge Horae PR #22 at source `aaed0cff8e777d62fcaff4f20b3347bb1eefa403`
  as provider default `c2e7766847e3ef28125b809d98fe07250acc6cec` after its
  shared-workflow pin checks and book build pass. Post-merge CI, book, and
  Pages deployment runs pass; live Pages returns HTTP 200.

- Merge Hyperion PR #19 at source `5e8d47008e01f401c8d1b464c30e2909ff1a56c8`
  as provider default `719d84e80163b958cc5500b5fa44a5b01095d6d1` after its
  shared-workflow pin checks and book build pass. Post-merge CI, book, and
  Pages deployment runs pass; live Pages returns HTTP 200.

- Reconcile Kwavers to hosted-green default `9cf62aa98364e8f00cba0ca4a5d431b90a0ab55a`;
  Architecture Validation `32333948199`, CI/CD `32333948192`, Legacy Migration
  Audit `32333948196`, and Pages `32333948521` pass. The open queue-contract
  PR #427 remains a separate branch residual.

- Merge Hermes PR #56 at source `932468dac5ef4abadea4bdd12d62b420a4225ba7`
  as provider default `3a39ef16d679dbac9c1a479b2b9c44135e262af3` after its
  executable book examples, SIMD snippet, and benchmark runtime gate pass.
  Post-merge CI, book, and Pages runs pass; live Pages returns HTTP 200.

- Merge Mnemosyne PR #65 at source `a527380a15e8979c3b773a4e9891f1d53b0bc45c`
  as provider default `7003eb3d09a716a91b4560e1810d65970c874daa` after its
  executable allocator examples and Miri gate pass. Post-merge CI, MSRV, and
  book runs pass; live Pages returns HTTP 200.

- Merge the provider-owned PM closure PRs for Horae #23 and Hyperion #20 at
  defaults `a05dbebbb947a627cbe69a9d839fb88cae46e459` and
  `e2dbc9bb28d7f9cbccf354d2a9b278c6231a85d1`; Atlas records both closure
  revisions after their exact documentation-only verification passes.

- Merge Proteus PR #14 and its PM closure PR #15 after the executable book gate
  passes: CI run `32338237653` and Pages build `32338238163` validate both
  included material examples; the pull-request Pages deployment is skipped.

- Integrate Helios PR #67 at provider default `423d6ec9`, including the
  `helios-python` abi3-py39 trusted-publishing workflow and package metadata;
  no PyPI release is performed.

- Record the Kwavers moving-default boundary at `9cf62aa9`: its current
  default-head Architecture and CI/CD gates remain queued, so Atlas retains
  the last verified pointer `b20eb48b`.

- Make the ADR index check fail when an on-disk ADR is absent from `HEAD`,
  with a focused regression covering a matching generated index.

- Extend the default provider-integration audit to all 22 active Atlas domain
  providers, including Harmonia; update its focused inventory and output tests.

- Activate Harmonia in `.gitmodules` and advance its Atlas gitlink to fetched
  default `02ffd14`, preserving the nested peer-owned worktree changes.

- Merge Horae PR #18 at source `cded674` as `0631da0` and Hyperion PR #14 at
  source `b8d4fb8` as `fd752c7`. Their exact-head hosted `verify`,
  `supply-chain`, and shared Pages book-build gates pass; the Atlas gitlinks
  now point to the merged default heads. Horae enables executable mdBook
  samples and Hyperion completes its CI-bound and line-ending cleanup. The
  root conformance baseline records Hyperion's zero measured residuals. The
  Horae RecurseML analyzer error remains report-only. Helios PR #64 remains
  open pending its benchmark regression gate. Post-merge Pages runs
  `32103884266` and `32103884853` deploy both books successfully; live HTTP
  checks return 200 with the expected titles.

- Correct the conformance scanner at root commit `78c7880` so pure reusable
  workflow callers are evaluated through the called workflow's bounded jobs;
  GitHub disallows `timeout-minutes` on the caller job. Mixed workflows retain
  the local timeout requirement. The focused scanner suite passes 11/11 and
  Horae's false `workflow_missing_timeout` baseline entry is removed.

- Bound the shared Pages workflow at root commit `6ed29a9`: network downloads,
  package installation, package builds, metadata resolution, mdBook tests, and
  mdBook rendering now have explicit termination bounds; the package build and
  metadata query use the committed lockfile. The local mdBook link-contract
  suite passes 43/43. Helios already enables `mdbook-test`; its caller and the
  Kwavers/CFDrs callers still pin earlier shared-workflow revisions and remain
  separate peer-owned integration work.

- Push the Atlas exact-head audit correction at `d496297`. The structural
  requested-provider audit passes for all 20 providers and preserves the
  `Tyche`/`Tychee` normalization. Hosted conformance run `32101488985` now
  reports only the genuine RITK `oversized_files` regression (`43 -> 44`) from
  the committed 540-line `crates/ritk-image/src/region.rs`; the peer-owned
  RITK checkout already has in-flight edits to that region and remains
  untouched. Root overlay run `32101202278` records the separate Apollo
  `0.26.0` versus Kwavers `0.27.0` requirement lag. Kwavers PR #402 remains
  blocked at `69478221f` until Apollo's `0.27.0` default lands; no consumer
  downgrade or compatibility path is added.

- Reconcile moving provider defaults by advancing the Atlas Aequitas gitlink
  to `c74b662c`, Hermes gitlink to `c6265cb4`, and Mnemosyne gitlink to
  current `d48f4842` through the previously recorded `bfe76db0`. The changes
  touch only committed submodule pointers; nested provider checkout dirt
  remains peer-owned and excluded. The structural exact-head audit passes.
  Full coherence reaches the requested scope but reports only the peer-owned
  Apollo checkout's in-flight `0.27.0` manifest against committed Coeus and
  RITK `0.26.0` requirements; Apollo `origin/main` remains `0.26.0`. Root
  hosted gates are re-collected for this pointer advance once the moving
  provider work is stable.

- Reconcile the second moving-default sweep by advancing the Atlas Themis,
  Proteus, Mnemosyne, Hermes, Asclepius, Eunomia, RITK, and Iris gitlinks to
  their fetched default heads. The structural requested-provider audit passes;
  the full coherence limitation is the separately recorded peer-owned Apollo
  `0.27.0` worktree against committed consumer `0.26.0` requirements. Nested
  checkout dirt remains excluded and root hosted gates are pending for the
  resulting root head.

- Merge Hephaestus PR #213 at default `607ce3f`, adding the provider-owned
  typed f32 FDTD contract, WGPU velocity/pressure kernels, and sequential
  contract coverage. Kwavers PR #402 carries the consumer cutover at final
  head `5155f32e8`; its benchmark-regression run `32095365142` is executing,
  and the remaining exact-head matrix is required before the Atlas gitlink
  advances.

- Advance fourteen requested-provider gitlinks to their fetched defaults after
  peer merges; the structural exact-head audit passes. Full coherence remains
  blocked only by the locally materialized Asclepius manifest lag, which still
  requires Aequitas `0.1.0` and Coeus `0.9.0`.

- Close the conformance classifier correction with 37 focused scanner tests,
  Apollo's clean orphan baseline at 0, and hosted root run `32031997052`
  reporting zero ratchet regressions at `f84beec`.

- Advance RITK to PM closure `f23a6acd` after splitting the diffusion Python
  binding leaves. The exact provider `manifest_implementation` count reduces
  from 112 to 111; provider-owned Rust, Nextest, Python matrix, and wheel
  smoke gates pass.

- Advance Hephaestus to PM closure `300b9e9` after the attention structure
  ratchet cleanup and exact-head CUDA/ROCm/WGPU/Metal gates. The provider
  `oversized_files` count is 38; direct Coeus attention cutover remains open.

- Correct the orphan-module conformance graph to follow literal and
  `CARGO_MANIFEST_DIR`-rooted `include!` sources. Apollo's clean exact count
  tightens from 3 to 0 without changing provider source.

- Advance the Helios and CFDrs integrator gitlinks to merged PR #57
  `7fddf789` and PR #345 `a3c53da2`. Helios now rejects incomplete required
  DICOM geometry; CFDrs uses Apollo's native-precision Fourier API and Leto's
  SSOR provider directly. Exact-head hosted gates pass for both consumers.

- Advance the Tyche provider gitlink to merged PR #22 `b1c5cc9f`; the provider
  correction aligns package-distribution and reproducible-study verification
  claims. Advance Mnemosyne to merged PR #51 `997ec088` with event-driven
  decay-test synchronization. The staged root exact-head/coherence audit
  passes for all 20 requested providers.

- Correct the conformance instrument and regenerate its baseline in the same
  change. `scripts/atlas-conformance.py` classified a file as test code only
  when a path *part* matched `tests`/`benches`/`examples`/`fuzz`, but
  `Path.parts` yields `tests.rs` as a filename and never `tests`, and
  `split_test_region` splits only on an *in-file* `#[cfg(test)]` — so every
  co-located `src/**/tests.rs` sidecar was scanned as production code. Four
  independent repo audits reached that conclusion separately. Matching now
  covers directory parts only, plus a new `declared_cfg_test` check that reads
  the parent module's `#[cfg(test)] mod <stem>;` declaration. Stack
  `unwrap_production` moves 4713 → 1460 (kwavers 2630 → 259, consus 709 → 334)
  with the counts landing in the test-region classes where they belong
  (`existence_only_assertions` 598 → 807, `sleep_synced_tests` 117 → 132). The
  ratchet returns to 0 regressions / 0 tightenings. Every burn-down target
  recorded before this fix was aimed by a broken instrument.

- Second conformance correction: `.unwrap()` inside `///` and `//!` doc-comment
  bodies is doctest code, not production. Counting it reported 23 "production
  unwraps" for tyche, whose workspace denies `unwrap_used` outright — every one
  was a doc example, and tyche now correctly reports 0. Stack
  `unwrap_production` 1460 → 1242. Also added `.git` to the sanctioned root set,
  since a submodule's `.git` is a gitlink *file* and was counted as unfiled
  sprawl in every member.

- Add `scripts/atlas-board-compact.py` and apply it. `backlog.md` 13,399 →
  5,369 lines and `checklist.md` 5,810 → 4,170, collapsing 299 closed items to
  one-line archive entries carrying their commit SHAs. Verified no item ID was
  lost in either file. The collapse is mechanical so it is reproducible rather
  than a one-off hand edit; it anchors the closed-status marker to the final
  em-dash segment of a heading, because matching anywhere after an em-dash
  archives live items whose *title* contains a status word.

- File the 2026-08-13 full-stack audit on the board: fourteen read-only audits
  covering all 25 registered members plus the meta-repo, opening 33 DoR-shaped
  items across four tiers. Tier 0 carries two safe-code paths to undefined
  behaviour (`themis` duplicating a melinoe capability token; a `mnemosyne`
  scratch-pool aliasing hole), an unvalidated public `Layout` under 84 leto
  unsafe blocks, unbounded parser allocation and recursion in consus, and two
  precision-contract violations in eunomia — one silently computing five `F64`
  transcendentals in `f32`, one ordering sub-byte floats by raw bit pattern so
  every min/max reduction over them is sign-inverted.

- Remove `helios_workflow_output/{ct,dose,mu,recon}.png` from tracking. They
  are run output of `tomotherapy_workflow.rs:102-104,209-212`, referenced by no
  test, xtask, workflow, Makefile or script, and `.gitignore:74` already names
  that exact path as derived state. helios itself tracks zero PNGs, so no fresh
  clone ever had them.

- Remove nine unfiled work products from `tools/` (~1.5 MB of `_probe_meta*`
  JSON, `cfdrs-lint*.stderr` dumps, one-shot `_fix_apostrophe.py` and
  `_insert_meta_docs.py`) and the Windows reserved-name `nul` artifact at the
  repository root.

- Advance all twenty requested provider gitlinks to their fetched default
  heads after CI-only Atlas workflow-pin merges. Exact-head, provider
  coherence, stack-overlay, and lane audits pass; peer-owned child checkout
  dirt remains excluded from the root change.

- Pin the shared Pages linkcheck2 installer to the stable Rust toolchain before
  `cargo install`; hosted caller validation exposed that the reusable workflow
  must not rely on the runner's ambient Cargo selection. Caller repinning and
  hosted reruns remain open.

- Close the publication-lock residual at the Atlas boundary. Exact committed
  kwavers and CFDrs gitlinks have complete first-party Git lock sources (33/33
  and 22/22); peer-owned overlay lock churn remains uncommitted and excluded.
  The shared crates.io workflow retains `--locked` validation.

- Advance Leto to merged default `39683975` after PR #109 added provider-owned
  disjoint mutable task partitions and the Moirai scheduler boundary. Exact
  PR Rust verification `31714562863`, post-merge Rust CI `31715060346`, and
  Pages deployment `31715059328` pass. Local Leto and Leto-ops Nextest passed
  286/286 and 527/527; the external recurseml analyzer remains report-only.

- Advance Leto to merged default `6e4a1627` after PR #96 replaced the
  production L-BFGS jagged history with a flat CSR-shaped ring and head
  eviction. Exact PR Rust run `31710403431`, post-merge Rust run
  `31710771815`, and Pages deployment `31710771170` pass. The task-partition
  API remains a separate provider-owned residual; superseded PR #103 is
  closed because Hermes 0.6 is already present in default `a722fbc8`.

- Close Hephaestus PR #113 as superseded: product-axis parity already exists
  in current history as `8bc589a`, while its obsolete round-6a path-lock
  rewrite is not compatible with the current git+version source model. The
  current default provider runs `31691399110`, `31691399171`, `31691399196`,
  and `31691399214` pass.

- Close Apollo PR #86 as superseded by the broader current-default cleanup
  `49632c6c` (ADR 0039 s5); the affected `helpers.rs` modules are already
  dissolved into concern-specific leaves. No duplicate rename is integrated.

- Advance Apollo to merged default `fc564896` after PR #83 converged the
  shared WGPU validation surface and real Mnemosyne branded-slice integration
  test. Duplicate GFT validators were removed; the `mnemosyne-memory` lock
  edge and benchmark candidate-manifest synchronization were completed.
  Exact PR Rust/Python run `31708004091`, benchmark run `31708004087`,
  post-merge CI `31708720285`, and Pages deployment `31708718632` pass.

- Advance Coeus to merged default `72372c91` after PR #320 removed the
  host-side batched Frobenius-norm fold. Provider square, last-two-axis
  reduction, square root, and batch reshape now remain in the provider graph;
  rank-two and non-contiguous paths retain their value-semantic contracts.
  Exact PR run `31701736189`, post-merge Backend parity run `31704377695`, and
  Pages run `31704377431` pass the applicable gates. Required-device CUDA and
  ROCm jobs remain unverified.

- Advance Helios to merged default `546c199f` after PR #48 converged its Pages
  caller on the Atlas shared workflow. The caller passes the actual rendered
  output `target/book/helios/html`; PR Rust, Python, book, and 45-minute
  benchmark gates passed. Post-merge Rust/Python and Pages deployment runs
  `31700981248` and `31700981609` passed.

- Advance Hermes to merged default `d1627cd2` after PR #37's native aarch64
  permute A/B gate. Neutral NEON reverse overrides were removed; large f32
  interleave and deinterleave wins of 1.27% and 1.40% remain. PR run
  `31695534571` and post-merge default run `31696261625` pass the applicable
  provider-owned gates. AVX-512 timing remains open under HS-429 real-silicon
  infrastructure.

- Advance Hephaestus to PM-closeout default `c373de19` and Coeus to
  PM-closeout default `a4063be1` for the CUDA `f64` comparison seam. Exact
  Hephaestus default runs `31691399110`, `31691399171`, `31691399196`, and
  `31691399214`, plus Coeus default run `31672329963`, pass their software
  provider contracts; required-device jobs remain unverified.

- Advance Leto to provider default `a722fbc8`. Close the generic convolution
  provider PM record after exact-head provider runs `31690152639` and
  `31690301356`, with Coeus direct-consumer evidence in `31672329963`.

- Advance Helios to provider default `f108dc9b`. The stale H-098 provider PM
  record is closed; exact-head hosted run `31686100896` passes Rust, Python,
  and the phase-reversed benchmark regression gate.

- Advance Apollo to provider default `36f2f364`. The real symmetric spherical-
  harmonic basis and scattered-direction design matrix are now recorded as
  integrated with RITK's diffusion and tractography consumers; the exact
  current-default hosted Rust/Python verification is `31684967756`.

- Merge Consus cross-format test closure PRs #24 and #25. Cross-format
  integration tests now call provider-owned HDF5, Zarr, NetCDF, and in-memory
  contracts directly with deterministic value-semantic fixtures; hosted run
  `31684429085` passes all 68 repository-owned jobs at the exact source head.

- Merge Consus PR #23 (`b3ca01c2`) to close the FITS, HDF5, and NWB
  no-default storage boundaries. Alloc-backed modules, re-exports, tests, and
  benchmark surfaces are gated consistently; the exact-head hosted matrix
  `31681611017` passes.

- Merge Consus PR #22 (`37f835d1`) to close the `consus-arrow` and
  `consus-parquet` no-default cfg boundaries. Alloc-backed bridges, wire paths,
  tests, and benches are gated consistently while descriptor-only no-alloc APIs
  retain value-semantic coverage; the exact-head hosted matrix passes.

- Pin shell scripts to LF so the Bash toolchain bootstrap remains executable
  after Windows checkouts.

- Merge Kwavers PR #341 (`e3389e79`) for typed two-dimensional transducer-array
  geometry, curvature, focus, frequency, velocity, steering, and delay
  contracts through Aequitas. Center-to-center pitch generation is corrected;
  Python retains SI/degree scalars only at serialization boundaries. Eunomia
  real/quadrature values retain one observable signal unit with no imaginary SI
  unit. Hosted Code Coverage `91842334110` and Test Suite Coverage
  `91842333977` pass; the RecurseML analyzer remains report-only.

- [minor] Advance the Leto/CFDrs provider graph to merged sparse-LU native-view
  ownership. CFDrs direct solves no longer stage the native RHS or returned
  solution through consumer-owned `Vec` buffers; no release is performed.

- Apply the shared line-table-only debug budget to test builds as well as
  development builds. Dependencies, build scripts, and procedural macros emit
  no ordinary test debuginfo, reducing Nextest artifact size and linker memory
  without changing optimization, assertions, or test workloads.

- Merge Kwavers PR #335 (`c3e0ca39`) to type sensor-beamformer positions,
  sampling and steering frequencies, angles, sound speed, spacing, aperture,
  F-number, and spatial-frequency metrics through Aequitas. The corrected
  LLVM coverage workflow selects targets by Cargo feature requirements and
  preserves Eunomia's real/quadrature shared-unit representation without an
  imaginary SI unit.

- Merge Kwavers PR #337 (`d5d2d964`) to type PAM delay-and-sum and neural sensor
  geometry, timing, frequency, angle, event-coordinate, and coherence metrics
  through Aequitas. Uncalibrated PAM threshold/intensity remain representation
  values; Eunomia complex FFT data retains one observable unit with no
  imaginary SI unit. Final hosted coverage, architecture, safety, feature,
  benchmark, and platform gates pass.

- Merge Kwavers MET-60 for typed transducer design and focused propagation
  contracts: geometry, wavelength, frequency, velocity, calibration,
  impedance, pressure, intensity, and extents now use Aequitas through the
  driver boundary. Focused real/quadrature accumulators remain components of
  one observable pressure signal; no imaginary SI unit is introduced. PR #338
  merged at `7ec566b6` and PM closure PR #339 merged at
  `3f96514d`; hosted Code Coverage `91794809116` and Test Suite Coverage
  `91794808091` pass, with the external RecurseML analysis remaining
  report-only.

- Merge Kwavers MET-61 for typed acquisition geometry: element coordinates,
  bowl radius, ring diameter and row spacing, breast-FWI geometry, and CBS/
  Born numerical callers now use Aequitas `Length` through PR #340. The
  absorption reference assertion uses a scale-relative 16-ulp bound. Eunomia
  real/quadrature values retain one observable signal unit with no imaginary SI
  unit. PR #340 merged at `9a6aac1c`; hosted Code Coverage `91827476450` and
  Test Suite Coverage `91827477067` pass with the complete repository-owned
  matrix.

### Added

- Generalize Tyche correlation, Morris, and Saltelli sensitivity estimators
  and reports over a const-generic output dimension while preserving the
  single-output API. Add analytical and seeded two-output law coverage.

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
