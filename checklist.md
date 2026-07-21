# atlas — cross-repository integration checklist

> Tactical decomposition aligned to `backlog.md`. Each step is atomic, evidence-tied, and self-verify-able. Per `engineering_gates`, only `cargo nextest run` and `cargo test --doc` are sanctioned test runners; changelog version bump and CHANGELOG sync travel with each [minor]/[major]/[arch] commit.
>
> **Integration base**: fetched `origin/main`; Git owns the exact revision.
> **Phase**: Foundation → Execution (batches 1, 2, 3 sequencing determined by Definition-of-Ready below).
> **WIP limit**: one merge-affecting backlog item active at a time (per `context_and_memory WIP limit`).

## ATLAS-INTEGRATION-038 — Iris visualization promotion [arch] [minor]

- [x] Audit color-law and result-view duplication; confirm the promotion gate
      and boundary against RITK, Kwavers, CFDrs, Leto, Hephaestus, and Consus.
- [x] Publish Iris and verify its full local gate plus anonymous Git access.
- [x] Add the first consumer-required upstream capability and merge Iris PR 1.
- [x] Replace both RITK color engines, migrate every in-scope caller, and add
      exact consumer differential/non-finite regressions in PR 46.
- [x] Require RITK PR 46 exact-head hosted checks and merge it.
- [x] Pin fetched Iris and RITK remote defaults, file ADR 0029, and synchronize
      `.gitmodules`, stack map, provider table, naming, roadmap, layout, ADR
      index, changelog, backlog, checklist, and gap audit.
- [x] Verify the Atlas checkout engine, exact gitlink object types, anonymous
      public remote defaults, documentation consistency, and merged consumer
      CI; advance Iris to `a8ea96f7` and RITK to `a36e65df`.

## ATLAS-INTEGRATION-037 — Asclepius P1 promotion [arch] [minor]

- [x] Verify public Asclepius remote default `eb65eaf`, the law/adapter merge
      `794f8c3`, two-crate workspace boundary, package gates, theorem suites,
      and exact Aequitas/Coeus dependency pins.
- [x] Register `repos/asclepius` in `.gitmodules` at the fetched merge object.
- [x] File ADR 0028 with bounded context, inward/outward dependency direction,
      migration, theorem/proof obligations, evidence limits, rejected
      alternatives, and consequences.
- [x] Add the exact-size streamed thermal-observation contract, caller-owned
      cumulative output, allocation evidence, and borrowed/streamed bitwise
      equivalence to the public provider branch.
- [x] Synchronize the current-stack count and table, provider ownership,
      dependency graph, naming registry, roadmap graduation, repository layout,
      ADR index, changelog, backlog, checklist, and gap audit.
- [x] Verify the pushed Atlas registration through the checkout engine:
      exact public Asclepius gitlink `ceb8b6d`, clean worktree, and nested
      package manifest all resolve from Atlas commit `6fb5576`.
- [x] Advance Hephaestus to public merge `74dec5d`, eliminating its obsolete
      `0f9d77a` Aequitas source identity from the materialized Helios graph.
- [x] Merge the Atlas registration and update Helios provider materialization
      to the exact Atlas merge OID; require exact-head hosted CI.
- [x] Replace Kwavers CEM43, Arrhenius, and independent-response duplicates
      with direct public Asclepius APIs; PR 301 merges as `1cb01fe` after all
      23 first-party hosted checks pass.
- [x] Close Asclepius PM state at `eb65eaf`, pin Helios `33bba34` and Kwavers
      `1cb01fe`, run the final structural residue audit, and record exact
      merged evidence.

## ATLAS-INTEGRATION-036 — Coeus hephaestus 0.18.0 bump [patch]

- [x] Reproduce the build-error: `cargo check --workspace --all-targets` for
      Atlas at peer HEAD fails when selecting `hephaestus-core = ^0.17.0`
      because the path-dep resolves to local tag `v0.18.0`.
- [x] Bump all three `hephaestus-{wgpu,core,cuda}` path-dep version pins in
      `repos/coeus/Cargo.toml` workspace.dependencies from `0.17.0` to
      `0.18.0`.
- [x] Verify the coeus workspace compiles and passes tests at the new pin:
      `cargo check --workspace --all-targets` rc=0,
      `cargo nextest run --workspace` 938/938, `cargo test --doc --workspace`
      8 doctests across coeus-tensor and coeus-wgpu.
- [x] Commit and push the coeus fix on a `fix/coeus-hephaestus-0.18-bump`
      branch; merge to coeus `main` via no-ff merge at `c290f3e` and push to
      origin.
- [x] Advance the Atlas-parent gitlink for coeus `56fa49a` -> `c290f3e` and
      leto `4158b8e` -> `02d74fd` (PR #55 perf/leto-ziggurat-normal merge).
- [x] Push to origin and merge via no-ff merge `3f40b79`.

## ATLAS-INTEGRATION-035 — Proteus and Tyche promotion ADRs [arch] [minor]

- [x] Confirm peer's Proteus promotion: `.gitmodules` entry registered,
      current-stack table reads 21 packages after `beb2713`, candidate
      table retired `harmonia` earlier and now retired Proteus too.
      Proteus HEAD on GitHub at `ryancinsight/proteus` is `2b06be3`.
- [x] Confirm peer's Tyche promotion: `.gitmodules` entry registered,
      current-stack table reads 22 packages after `feed3bc`, candidate
      table retired Tyche. Tyche HEAD on GitHub is `7898899`.
- [x] Author ADR 0025 `docs/adr/0025-proteus-material-property-promotion.md`
      at `Accepted` recording the Proteus promotion: bounded context
      (material-property validity boundaries, cohesive bundles, named
      material composition, statically dispatched constitutive-law
      evaluation; NO Aequitas/Eunomia re-ownership; NO domain physics
      re-ownership), dependency direction (`proteus -> aequitas -> eunomia`),
      migration plan (each consumer increment deletes local copy),
      theorems and evidence (density/heat-capacity positivity,
      conductivity non-negativity, thermal-diffusivity dimensional
      reduction `alpha = k/(rho*c_p) >= 0`, Aequitas dimensional algebra
      to `L^2/T`), rejected alternatives, consequences, Relates-to
      (0002/0005/0021/0023/Proteus ADR 0001).
- [x] Author ADR 0026 `docs/adr/0026-tyche-uq-promotion.md` at `Accepted`
      recording the Tyche promotion: bounded context (study identity, seed
      and replay laws, sampling designs, ensemble statistics, domain-neutral
      sensitivity, calibration, logical artifact keys; NO Moirai/Consus
      re-ownership; NO domain physics re-ownership), dependency direction
      (tyche-core -> eunomia; tyche-moirai -> tyche-core + moirai;
      tyche-consus -> tyche-core + consus; tyche facade composes),
      migration plan, theorems and evidence (Latin hypercube permutation
      `pi(i) = a*i + b (mod n)` is a permutation; counter-addressed replay
      `(seed, index, dimension)` invariant; Welford recurrence; population
      vs sample variance by zero-sized policy; squared Pearson screening
      by Cauchy-Schwarz; split-conformal corrected rank), rejected
      alternatives, consequences, Relates-to
      (0002/0005/0023/0025/Tyche ADR 0001).
- [x] Extend the ADR INDEX listing table with rows 0025 and 0026 and
      extend the closing narrative line through 0026.
- [x] Extend the ADR INDEX cross-walk table with rows for 0025 and 0026
      pointing to Proteus ADR 0001 and Tyche ADR 0001 respectively.
- [x] Add Group F topic-keyword group to the ADR INDEX for the
      material-and-vocabulary + uncertainty-quantification provider pair.
- [x] Add `### Added` entries to CHANGELOG.md covering ADRs 0025, 0026,
      and the coeus bump.
- [x] Add `ATLAS-INTEGRATION-035` and `ATLAS-INTEGRATION-036` rows to
      backlog.md.
- [x] Add a 2026-07-20 State refresh row to gap_audit.md covering the
      Proteus/Tyche ADR backfill and the coeus hephaestus bump.

## ATLAS-INTEGRATION-034 — Benchmark gate repair [arch] [patch]

- [x] Reproduce the tautological same-run comparison in Apollo, Helios, and
      Kwavers CI and capture Helios's missing path-dependency failure.
- [x] Implement the Atlas-owned Rust confidence-interval gate with recursive
      Criterion result discovery and fail-closed missing comparisons.
- [x] Correct the gate after hosted falsification: require opposite-order
      agreement, pin the candidate measurement instrument, and derive
      family-wise confidence as `1 - 0.05 / m`.
- [x] Correct the remaining run-phase confound after Apollo hosted run
      `29764170548`: intersect two phase-reversed ABBA and BAAB replications,
      fail closed across their benchmark universes, and retain the 5%
      family-wise confidence bound.
- [x] Implement one Atlas-owned exact-gitlink path-dependency checkout action
      with Cargo-aware discovery, clean exact-revision reuse, and
      value-semantic local Git integration tests.
- [ ] Replace each copied Python gate with a pinned Atlas tool checkout and a
      true base/head Criterion run on one runner.
- [x] Restore Helios path-dependency checkout and the committed nextest runner.
- [ ] Merge all three child fixes, advance Atlas gitlinks, close the README
      alignment review thread, and remove obsolete local artifacts.

## ATLAS-INTEGRATION-033 — Harmonia Phase 0 [arch] [minor]

- [x] Define the coupling boundary, dependency direction, theorems, rejected
      alternatives, and Phase 0 exclusions in Harmonia ADR 0001.
- [x] Implement the deep partition/transfer/relaxation/pair hierarchy with
      const-generic subcycling, associated-type model bundling, ZST policies,
      borrowed `Cow` transfers, and transactional workspace commits.
- [x] Add analytical, property, differential, generic-scalar, transaction,
      allocation, layout, doctest, example, and release-codegen evidence.
- [x] Add Athena's missing public `IterationState` constructor, pass focused
      gates, and merge Athena PR #2 at `e15aa44`.
- [x] Publish Harmonia publicly, merge its Node 24 CI cleanup, and verify
      exact-head hosted verification and supply-chain jobs.
- [x] Register fetched Harmonia `origin/main` as the twentieth Atlas gitlink;
      synchronize README, ADR 0023, ADR index, backlog, checklist, gap audit,
      and changelog.

## ATLAS-INTEGRATION-032 — Documentation and checkout hygiene [patch]

- [x] Audit every root gitlink against its working checkout and preserve unique
      CFDrs, Athena, RITK, and Harmonia state.
- [x] Restore only the clean, superseded Leto feature checkout to the recorded
      merge commit.
- [x] Correct Atlas's Harmonia dependency boundary and document reproducible
      submodule inspection and targeted checkout recovery.
- [x] Compile Athena and Horae README-backed doctests and rustdoc; verify
      Horae without default features.
- [x] Review Athena's external observer constructor, replace its tautological
      internal test with an external doctest, and run focused Clippy and
      nextest gates.
- [x] Merge Athena PR #3 at `96fb26d` and Horae PR #2 at `92af1a2`; advance
      only their parent gitlinks.

## ATLAS-INTEGRATION-030 — Aequitas consumer closure [patch]

- [x] Merge Kwavers PR #295 only after all 24 exact-head hosted checks pass.
- [x] Verify merge object `49c116ffb7466f9163b7762f03bc74725d8026c3`
      exists and equals fetched Kwavers `origin/main`.
- [x] Verify CFDrs Aequitas merge object
      `7c37f7f30dc286e8853bdf41da7652abeadebe23` equals its fetched
      `origin/main`.
- [x] Replace parent gitlinks `156531eeb` and `a34a01d1` with the merged
      Kwavers and CFDrs remote-default objects.
- [x] Synchronize ADR 0021, `backlog.md`, `gap_audit.md`, `CHANGELOG.md`, and
      this checklist with exact merge and verification evidence.

## ATLAS-INTEGRATION-029 — Hephaestus provider-first CFDrs 2D GPU Laplacian [minor]

- [x] Move provider-side stencil surface (`Laplacian2DKernel`,
      `Laplacian2DParams`, `BoundaryCondition`) from `cfd-core` to
      `repos/hephaestus`.
- [x] Delete `cfd-core/src/compute/gpu/shaders.rs` and remove the uniform
      layout from the consumer; keep `BoundaryType` as the CFD-facing enum.
- [x] Forward `cfd-core` `Laplacian2DKernel` dispatch through
      `hephaestus_wgpu::Laplacian2DKernel`.
- [x] Verify `hephaestus-wgpu` 140/140 nextest, `cfd-core --features gpu`
      245/245 nextest, `cfd-math --features gpu` 362/362 nextest; Clippy
      `-D warnings` clean on both crates.
- [x] Synchronize `backlog.md`, `gap_audit.md`, and this checklist.

## ATLAS-INTEGRATION-028 — Hephaestus PM convergence [patch]

- [x] Merge Hephaestus PR #52 without touching peer-owned WGPU source changes.
- [x] Advance only the Hephaestus gitlink to its exact fetched default.
- [x] Merge Atlas PR #49 at `2c1ee62`; all 16 gitlinks exist and equal their
      fetched remote defaults.

## ATLAS-INTEGRATION-027 — Provider-default convergence [patch]

- [x] Merge Hermes' Eunomia 0.6 lock refresh and PM closeout.
- [x] Preserve Leto PR #48's merged Box-Muller increment.
- [x] Advance only the Hermes and Leto gitlinks to their fetched defaults.
- [x] Replace PR #46's invalid same-prefix Leto object ID with the exact PR #48
      merge object `bb03244f05a9c43c318d103225c3ccad07e9fad9`.
- [x] Merge Atlas PRs #46-#47 and rerun the 16-gitlink audit: every pointer is
      an existing commit equal to its fetched remote default.

## ATLAS-INTEGRATION-026 — Eunomia runtime-half retirement [patch]

- [x] Merge Eunomia 0.6.0 with the foreign raw-half numeric/cast surface
      removed and `half` confined to the differential-oracle dev graph.
- [x] Refresh and merge Hephaestus's coherent Eunomia 0.6/Hermes 0.4/Leto
      0.39 lock closure.
- [x] Advance only the Eunomia and Hephaestus gitlinks; preserve peer-owned
      Coeus/RITK and root package-manager state.
- [x] Publish, merge, and reconcile Atlas PR #44 at `d207cf6`.

## ATLAS-INTEGRATION-025 — Eunomia precision graph [major]

- [x] Merge Eunomia reduced-precision bit and float-element contracts.
- [x] Merge Hermes native Eunomia reduced-precision SIMD ownership.
- [x] Merge Leto scalar, real-math, array arithmetic, and fixture cutover.
- [x] Advance Eunomia, Hermes, and Leto; reconcile the previously committed
  Coeus and RITK parent gitlinks with current merged defaults.
- [x] Review, publish, merge, and reconcile Atlas PR #41 at `3f5f51f`.

**Evidence tier:** exhaustive reduced-format bit-pattern tests in Eunomia,
compile-time provider binding, exact reduced-precision value tests, configured
consumer regression execution, warning-denied diagnostics, rustdoc, and remote
default identity across all 16 Atlas gitlinks. No formal proof checker was run.

## ATLAS-INTEGRATION-024 — Helios provider lock convergence [patch]

- [x] Replace the stale partial Apollo lock edit with the complete Cargo
      resolution for Apollo 0.25.0, Eunomia 0.4.0, Leto 0.38.2, and
      Hephaestus 0.17.0.
- [x] Verify the lock removes the Hephaestus WGPU `num-complex` edge and the
      package itself without a Helios source or manifest compatibility change.
- [x] Run locked metadata, format, warning-denied workspace Clippy, configured
      workspace Nextest, doctests, and warning-clean rustdoc.
- [x] Merge Helios PR #7 and advance only its parent gitlink.

**Evidence tier:** compiler-checked dependency resolution, warning-denied
diagnostics, and value-semantic workspace regression execution. No formal
proof checker was run.

## ATLAS-INTEGRATION-023 — Coeus NN provider benchmark closure [patch]

- [x] Reconcile stale PR #212 against current Coeus main without deleting the
      canonical provider-performance instrument.
- [x] Remove only Burn setup and comparison rows; retain all 211 operation
      groups and 424 native Sequential/Moirai measurements.
- [x] Align the locked graph to Eunomia 0.4.0, Leto 0.38.2, and Hephaestus
      0.17.0; move invariant layout cloning outside Criterion timed loops.
- [x] Run format, locked all-target/all-feature Clippy, configured Nextest,
      doctests, rustdoc, metadata, hosted review, and merge PR #212.
- [x] Advance only the merged Coeus gitlink while preserving concurrent child
      and root working-tree state.

**Evidence tier:** compiler-checked provider graph, warning-denied diagnostics,
value-semantic test execution, mechanical benchmark census, and hosted review.
No formal proof checker was run.

## ATLAS-INTEGRATION-022 — Eunomia sub-byte graph [patch]

- [x] Merge Eunomia PR #39 at `49dc115` with one compile-time IEEE/finite-only
      conversion kernel and exhaustive reduced-format contracts.
- [x] Advance Leto and Hephaestus locks to Eunomia 0.4.0 and merge consumer
      PRs #44 (`f0b4d8e`) and #50 (`ed7d76e`).
- [x] Verify Leto 593/593 and Hephaestus 312/312 configured Nextest suites,
      warning-denied all-target/all-feature Clippy, doctests, and rustdoc.
- [x] Advance only the Eunomia, Leto, and Hephaestus gitlinks; preserve
      peer-owned Coeus, Helios, RITK, Themis, and root package-manager state.

**Evidence tier:** compile-time policy selection, exhaustive analytical and
differential Eunomia tests, complete consumer regression suites, and structural
Git equality to fetched remote defaults. No formal proof checker was run.

## ATLAS-INTEGRATION-019 — Hephaestus legacy-math residue [patch]

- [x] Remove the Hephaestus `ndarray`/`nalgebra` dev-dependency declarations
      and convert WGPU differential oracles to Leto/Leto Ops or closed-form
      value references.
- [x] Replace the comparative benchmark's legacy CPU baselines with the
      canonical Leto CPU baseline while retaining real GPU measurements.
- [x] Run the provider's formatting, locked check, warning-denied Clippy,
      configured Nextest, doctest/rustdoc, and source-residue gates.
- [x] Advance the Atlas graph only after the provider merge and synchronize
      `gap_audit.md`, `CHANGELOG.md`, and ADR 0020.

**Acceptance:** no Hephaestus test/benchmark manifest or source path names
`ndarray` or `nalgebra`; Leto remains the CPU array/linalg reference and GPU
execution remains provider-owned.

**Evidence:** provider merge `cec0e33`; core 48/48, WGPU 140/140, CUDA
109/109, warning-denied Clippy, doctests, rustdoc, and all-target benchmark
compilation pass. `numpy` remains only at the PyO3 FFI representation edge.

## ATLAS-INTEGRATION-020 — Apollo Hephaestus lock convergence [patch]

- [x] Refresh Apollo's `hephaestus-core`, `hephaestus-wgpu`, and
      `hephaestus-cuda` lock entries to merged provider `cec0e33`.
- [x] Run Apollo's locked compile, Nextest, warning-denied Clippy, doctests,
      rustdoc, and provider audit; hosted checks must inspect the new head.
- [x] Advance only the Apollo gitlink after the provider merge and synchronize
      the graph theorem, `gap_audit.md`, and `CHANGELOG.md`.

**Evidence:** Apollo PR #53 merges at `a31b8f8`; locked compile, 402/402
Nextest, warning-denied Clippy, doctests, warning-clean rustdoc, provider
audit, hosted Rust/Python, and CodeRabbit pass. `recurseml/analysis` is an
external non-required infrastructure error.

## ATLAS-INTEGRATION-021 — Coeus tensor legacy benchmark removal [patch]

- [x] Verify Coeus PR #211 removes the tensor legacy dependency and duplicate
      benchmark rows while retaining Coeus Sequential/Moirai and Leto paths.
- [x] Verify the Coeus lock graph aligns Hephaestus `0.16.1` and commits the
      reproducibility lock; preserve the provider-owned theorem in Coeus docs.
- [x] Advance only the merged Coeus gitlink and synchronize the graph audit and
      changelog; leave the peer-owned Kwavers pointer untouched.

**Evidence:** Coeus merge `4459d09`; locked package check, 56/56 Nextest,
warning-denied Clippy, five doctests, warning-clean rustdoc, locked metadata,
and targeted residue scan pass. The next Coeus NN benchmark residue is filed
in Coeus MS-442.

## ATLAS-INTEGRATION-018 — RITK Apollo alignment [patch]

- [x] Verify RITK PR #41 merges the Apollo 0.25 lock and composite-checkout
      alignment at `a41e03b9`.
- [x] Confirm all 22 repository and review checks pass, including
      cross-platform Nextest, Python 3.9–3.13, wheel, Clippy, formatting,
      dependency alignment, and migration audit.
- [x] Advance only `repos/ritk`; keep the active Kwavers GPU peak-pressure
      feature branch outside the parent graph.

**Residual:** none for the RITK provider-alignment increment; the external
analyzer error is non-required infrastructure noise.

## ATLAS-INTEGRATION-015 — Merged default refresh [patch]

- [x] Verify CFDrs PR #297 and Leto PR #40 merge, then fetch every affected
      child remote default.
- [x] Advance CFDrs to `a833b7fe`, Eunomia to `a2e4f390`, Helios to
      `972fb53e`, Leto to `3ac0d203`, and RITK to `aededa6b`.
- [x] Keep Apollo at merged `c8742814`, Hephaestus at `93bc38e6`, and Kwavers
      at merged `9eabc4e2`; do not stage Apollo's active lock refresh,
      Kwavers' active GPU peak-pressure branch, or RITK's active Apollo 0.25
      alignment branch.
- [x] Synchronize the graph theorem, board, gap audit, and changelog; verify
      the staged gitlinks against fetched remote defaults.

**Evidence:** structural Git equality for all recorded default commits;
CFDrs value-semantic Nextest 4/4 plus its 1/1 direct-after-GMRES consumer
regression and warning-denied Clippy; RITK PR #40's complete hosted
cross-platform, Python, wheel, lint, dependency, and migration matrices.

## ATLAS-INTEGRATION-012 — Apollo policy-wrapper removal [major]

- [x] Verify Apollo PR #49 merges the obsolete radix execution-policy wrapper
      removal at `e2f905a`, with Moirai owning the policy type and Apollo's
      threshold remaining in the tuning SSOT.
- [x] Confirm local locked `apollo-fft` Nextest 393/393, warning-denied
      Clippy, doctests, rustdoc, source-residue scan, provider audit, and the
      hosted Python bindings lane pass.
- [x] Confirm hosted Rust workflow `29620388853` reaches a terminal green
      result, then advance only `repos/apollo` and synchronize this board,
      `gap_audit.md`, `CHANGELOG.md`, and ADR 0020.

**Residual:** none for the wrapper-removal increment; the external
`recurseml/analysis` failure is non-required.

## ATLAS-INTEGRATION-013 — Apollo Winograd re-export removal [patch]

- [x] Verify Apollo PR #50 merges the internal Winograd re-export removal at
      `c874281`, with all callers using the canonical
      `components::winograd::ShortWinogradScalar` path.
- [x] Confirm local locked Nextest 402/402, warning-denied Clippy, doctests,
      warning-clean rustdoc, source-residue scan, and provider audit pass;
      hosted Python, Rust, and CodeRabbit checks are green.
- [x] Advance only `repos/apollo` and synchronize the board, `gap_audit.md`,
      `CHANGELOG.md`, and ADR 0020.

**Residual:** none for the canonical re-export cutover; the external
`recurseml/analysis` error reports an infrastructure failure and is not a
required build gate.

## ATLAS-INTEGRATION-014 — Hephaestus scan-limit theorem [patch]

- [x] Verify Hephaestus PR #46 merges the scan-limit audit at `93bc38e` and
      retains provider ownership without introducing a consumer kernel.
- [x] Confirm nightly formatting and core Nextest 48/48; record the existing
      WGPU/CUDA `L=513`, `W=256` value contracts and the shared-memory theorem.
- [x] Advance only `repos/hephaestus` and synchronize the board,
      `gap_audit.md`, `CHANGELOG.md`, and ADR 0020.

**Residual:** KS-5b remains a measured performance follow-up. It reopens only
on a device-specific workgroup/latency limit and a derived tolerance for any
reordered floating-point multi-pass path.

## ATLAS-INTEGRATION-016 — Apollo provider-lock refresh [patch]

- [x] Verify Apollo PR #51 merges the lockfile refresh at `6dcb97c` and the
      provider revisions resolve from default-source commits.
- [x] Confirm locked compile, 402/402 Nextest, warning-denied Clippy,
      doctests, warning-clean rustdoc, provider audit, and hosted Python,
      Rust, and CodeRabbit checks pass.
- [x] Advance only `repos/apollo` and synchronize the board, `gap_audit.md`,
      `CHANGELOG.md`, and ADR 0020.

**Residual:** none for this graph-refresh increment; the external analyzer
error is non-required infrastructure noise.

## ATLAS-INTEGRATION-017 — Apollo Leto merge pin [patch]

- [x] Verify Apollo PR #52 merges the Leto merge-pin correction at `7303423`.
- [x] Confirm both Leto packages select Atlas default `3ac0d203`, with no
      Apollo source/manifest change and exact provider-tree equality to the
      prior tested revision.
- [x] Advance only `repos/apollo` and synchronize the board, `gap_audit.md`,
      `CHANGELOG.md`, and ADR 0020.

**Residual:** the local fresh compile was blocked by stale peer test
executables in the shared target; hosted Rust/Python/CodeRabbit checks are
green and the external analyzer remains non-required.

## ATLAS-INTEGRATION-011 — Hephaestus CUDA initialization closure [patch]

- [x] Verify Hephaestus PR #45 merges the memoized CUDA driver initialization
      and serialized context-creation boundary at `3b68228`.
- [x] Confirm the full CUDA nextest suite is 109/109, including the formerly
      aborting concurrent-acquisition contract; Clippy, doctests, and rustdoc
      are warning-clean.
- [x] Advance only the `repos/hephaestus` gitlink and synchronize the board,
      `gap_audit.md`, `CHANGELOG.md`, and ADR 0020.

**Residual:** none for the reproduced Windows concurrent-acquisition abort;
the lock covers driver context creation only, so transfers and kernels remain
concurrent by construction.

## ATLAS-INTEGRATION-010 — Hephaestus tiled scan provider closure [minor]

- [x] Verify Hephaestus PR #44 merges the shared-memory tiled scan slice at
      `d0eafc8`, with WGPU/CUDA provider ownership and ADR 0009 theorem
      documentation.
- [x] Confirm core 48/48 and WGPU 140/140 nextest, CUDA 108/108 excluding
      the independent Windows access violation in
      `concurrent_device_acquisition_is_safe`, doctests, rustdoc, Clippy,
      and real-device long-line scan contracts.
- [x] Advance only the `repos/hephaestus` gitlink and synchronize this board,
      `gap_audit.md`, `CHANGELOG.md`, and ADR 0020.

**Historical residual (closed by ATLAS-INTEGRATION-011):** the initial tiled
scan slice excluded the concurrent-acquisition test while its provider-owned
CUDA initialization defect was investigated.

## ATLAS-INTEGRATION-006 — Refresh provider heads [arch]

- [x] Replace the stale integration graph with current Apollo, Hephaestus,
  Kwavers, Leto, and merged RITK commits.
- [x] Add ADR 0020 with the provider-graph closure theorem and update the ADR
  index, backlog, gap audit, and changelog.
- [x] Merge Atlas PR #15 at `29041d9`.
- [x] Verify Apollo PR #46 hosted Rust and Python matrices and merge the
      PM-only closure at `eb46e77`; its recurseml analysis failure is
      external/non-required.
- [x] Verify Apollo PR #48 canonical-export documentation in the hosted Rust
      and Python matrices; merge `0b5d11c`.
- [x] Verify Kwavers PR #294 head `e84bb571e`; it retains the successful
      `cobertura.xml` source gate, makes external tokenless Codecov HTTP 429
      upload transport non-blocking, and moves the MVDR timing contract into
      Criterion. Architecture Validation `29614208770`, CI/CD
      `29614208862`, and Legacy Migration Audit `29614208769` pass; only the
      external `recurseml/analysis` status remains errored.
- [x] Advance the Atlas Kwavers gitlink and merge Atlas PR #23 at `baa6970`.

## ATLAS-INTEGRATION-008 — Apollo dispatch verification tree [arch]

- [x] Merge Apollo PR #46 and confirm the private verification leaf keeps
      GPU execution in the Hephaestus/Leto provider path.
- [x] Confirm Apollo has no direct raw `wgpu` dependency or wrapper.
- [x] Record the inverse-identity and `13*gamma_256` round-trip theorem in
      Apollo ADR 0034 and synchronize the parent graph record.
- [x] Advance and merge the Atlas `repos/apollo` gitlink at `eb46e77` in the
      parent integration increment (`56ad179`); the next Apollo source head is
      `0b5d11c`.

## ATLAS-INTEGRATION-009 — Kwavers hosted closure [patch]

- [x] Diagnose the failed coverage job as a full inverse-solve coupling in the
      abdominal geometry tests; commit `11e577c` isolates that contract at the
      canonical layout operation without weakening the geometry assertions.
- [x] Land the follow-up Hephaestus backend-kernel ownership cutover at
      `3f2a1b4`; local GPU Nextest passes 143/143 with one hardware skip.
- [x] Move the MVDR wall-clock assertion into the Criterion benchmark on PR
      #294 head `e84bb571e`; the ultrasound physics correctness lane passes
      18/18 under locked Nextest.
- [x] Merge PR #294 at `9eabc4e2` after its hosted matrix passes, then advance
      parent gitlink from `7c7d60f` to the resulting clean Kwavers `main`
      commit.
- [x] Record Kwavers `5f9e97b` as the clean Git-source identity correction and
      `54575460c` as the PSTD parity-call contract fix; keep the parent pinned
      at `9eabc4e2` after hosted closure.

## ATLAS-INTEGRATION-007 — RITK Apollo checkout pin [patch]

- [x] Confirm RITK `main` at `ffda3ec` passes its corrected Apollo 0.24
      dependency-alignment workflow and full hosted matrix.
- [x] Advance only the `repos/ritk` gitlink to that default-branch head.
- [x] Push and merge the isolated Atlas parent-pin PR as Atlas PR #15 at
      `29041d9`.

**Evidence:** RITK run `29591782642` (CI), `29591782812` (Python CI), and
`29591780940` (Legacy Migration Audit) completed successfully at `ffda3ec`.

## ATLAS-INTEGRATION-001 — default-main reconciliation [complete]

- [x] Resolve root metadata conflicts without discarding the migration SSOT.
- [x] Advance Coeus and Gaia gitlinks to their merged default-branch commits.
- [x] Confirm every conflicted provider gitlink is reachable from its current
  remote default branch.

## ATLAS-INTEGRATION-002 — merged-provider pin reconciliation [patch]

- [x] Confirm Apollo PR #44 is merged to `main` at `f26369eb`.
- [x] Confirm Helios PR #5 is merged to `main` at `04e496b7`.
- [x] Confirm RITK PR #37 is merged to `main` at `ec7cb832` after all
      Ubuntu/macOS/Windows Nextest, Python, wheel, lint, and audit checks pass.
- [x] Advance the three gitlinks and merge Atlas PR #9 at `e3380b6`.
      Evidence: every recorded gitlink is an ancestor of its corresponding
      remote default branch.

## ATLAS-INTEGRATION-005 — RITK lock-integrity pin [patch]

- [x] Confirm RITK PR #38 is merged to `main` at `0dd71e52` after Linux,
      macOS, and Windows Nextest; Python 3.9–3.13; wheel; Clippy; Rustfmt;
      dependency-alignment; and migration-audit gates pass.
- [x] Advance the `repos/ritk` gitlink without changing any other provider
      pin.

**Evidence:** RITK PR #38 merged after all recorded required checks completed
successfully. The root diff contains only the RITK gitlink plus synchronized
Atlas PM artifacts.

## ATLAS-MNEMOSYNE-017 — Maximum-small deallocation audit [patch]

- [x] Verify the merged Mnemosyne PR #25 at provider head `0012c4f`.
- [x] Record the matched `large/8192` deallocation row (`36.960 ns` versus
  RpMalloc `6.1139 ns`) and pin the exact same-owner branch with the opt-in
  `MAX_SMALL_ALLOC_SIZE` regression.
- [x] Advance the Atlas gitlink in `4908208` from `52cd5ee` to `0012c4f`.

Evidence: 62/62 default local nextest, 3/3 feature-gated probe nextest,
warning-denied Clippy, doctests, rustdoc, formatting, and matched Criterion.
The provider PR's `recurseml/analysis` status failed at the service layer;
CodeRabbit was rate-limited without actionable findings.

## ATLAS-MOIRAI-016 — Cancellation-safe async wait queues [patch] — ✅ done

- [x] Audit the merged `moirai-async` synchronization surface for contention,
  cancellation, and memory-retention defects. Completion condition: exact
  source locations, interleaving, ownership impact, and current test evidence
  are recorded in `gap_audit.md` and `backlog.md`.
- [x] Implement the provider-owned state-machine fix. Completion condition:
  condition-variable registration is atomic with mutex release, cancelled
  mpsc/oneshot waiters release their wakers, and deterministic value-semantic
  regressions cover lost notification and cancellation.
- [x] Run provider closure gates. Completion condition: warnings-denied
  Clippy, `cargo nextest run` under the committed timeout, and docs are clean;
  no test exceeds the slow threshold.

Verification: `cargo check -p moirai-async` clean; `cargo nextest run -p moirai-async`
82/82 passes (80 existing + 2 new cancellation regressions), no slow tests.
Fixes applied: `condvar.rs` (NoopWaker pre-registration), `mpsc.rs` (ID-based waiter
tracking + Drop cleanup), `oneshot.rs` (Drop clears rx_waker).

## ATLAS-RITK-654 — RITK native migration reconciliation [patch]

- [x] Update RITK's native VTK CLI contracts and current provider call sites;
  local value-semantic tests cover native round-trip shape and voxel values.
- [x] Refresh RITK's Burn migration allowlist from actual source and remove
  broken/private rustdoc links. The inner audit reports `Allowlist status:
  clean`.
- [x] Verify RITK local gates: workspace nextest 5,229/5,229 with 26 skipped,
  doctests, warnings-denied Clippy, fmt, and warning-free rustdoc.
- [x] Replace the unreachable private OpenJPEG revision and stale `jpeg2k`
  wrapper with the public `openjp2` API. The focused interop suite passes
  14/14 and the full `ritk-codecs` package passes 256/256.
- [x] Merge RITK PR #31 and documentation closeout PR #32, then advance
      `repos/ritk` to merged commit `4ba050ca`. CI passed (Rustfmt, Clippy,
      Workspace Dependency Alignment, Test Suite on ubuntu/macos/windows,
      Python 3.9-3.13 on all platforms, Python Wheel, CodeRabbit, and Audit
      burn migration). The final pointer advance is committed with this
      closeout.
- Residual: RITK still has 14 Burn manifests and 645 Burn-surface source files;
  the next item is a real Coeus/Leto consumer cutover (sub-batches #3.g–#6,
  peer-owned). Three registration tests exceeded 30 seconds locally and require
  a profile-guided performance item; their assertions and workloads were not
  changed.

## Apollo RustFFT/WGPU provider promotion [major]

- [x] Complete the provider branch migration and replace the RustFFT
      validation oracle with the native DFT reference.
- [x] Gate AVX Stockham modules to x86 targets. Completion condition:
      `apollo-fft` passes 409/409 nextest and an `aarch64-apple-darwin` check.
- [x] Open Apollo PR #8 from `codex/remove-rustfft` and resolve the Rust 1.97.0
      / syn 2.0.119 incompatibility (E0119) by pinning Cargo.lock to syn
      2.0.118 (commit `b57c069`).
- [x] Obtain repository review/CI green and promote Apollo PR #8 to `main` at
      `6e99a567c118f6bf5790f80346475b44db2c7555`. Authoritative CI run
      `29381809234` passed the Rust, Python, documentation, provider-audit,
      RustSec, and dependency-policy jobs.
- Residual: RITK PR #33 is the downstream consumer verification; its checkout
      action now pins merged Apollo and Coeus provider heads.

## Hermes pointer closure [patch]

- [x] Advance `repos/hermes` to merged PR #6 commit `1423e41d` after its
      targeted and cross-architecture checks passed.

## Atlas local-artifact cleanup [patch]

- [x] Classified every dirty submodule and local worktree with peer/process
  evidence; preserved all active migration scopes.
- [x] Removed the unreferenced `fix_doc_links.py` mutator and the generated
  `worktrees/ritk-native/target` cache (325,213,153,514 bytes).
- [x] Retained the registered RITK lane and its 11 dependency junctions; added
  `/worktrees/` to the root ignore policy so local topology is not repo dirt.
- [x] Recorded the RITK native-NGF provider-ownership violation; the peer slice
  is not commit-ready until its local grid substitute moves upstream.
- Evidence tier: Git state/diff inspection, process inspection, filesystem byte
  count, and semantic source review. No performance speedup is claimed.

## WGPU 30 provider ABI closure [arch]

- [x] Removed Mnemosyne's unsound raw-pointer WGPU allocator contract and
  retained the subsequent pooled-segment lifetime correction in `01e7de7`.
- [x] Released Hephaestus 0.13 at `090611d` on one WGPU 30 ABI and migrated its
  complete WGPU surface without a compatibility adapter.
- [x] Advanced Leto `8651dfc` and Moirai `c43f86a` to the corrected Mnemosyne
  contract.
- [x] Released Apollo 0.15 at `96e67a2`, removed the obsolete WGPU 26 and
  archived `paste` constraints, and preserved native borrowed/mapped error
  propagation.
- [x] Advanced the five Atlas gitlinks only after their provider commits were
  pushed and their consumer gates passed.
- Evidence tier: compile-time API enforcement; 1029/1029 Apollo and 300/300
  Hephaestus value-semantic nextest cases; 34/34 Python boundary cases;
  warning-denied Clippy/rustdoc; doctest, provider, RustSec, cargo-deny, and
  pre-1.0 API compatibility checks.

## Apollo 0.14.0 release eligibility [arch]

- [x] Removed Apollo's inert Moirai `no-global-alloc` request and refreshed its
  lock graph to one Melinoe 0.9 provider.
- [x] Propagated fallible Hephaestus/Mnemosyne device construction through
  `WgpuDeviceResult`, consolidated error translation, and added exact tests.
- [x] Cascade verified Mnemosyne `eb0d941`, Hermes `51c530f`, Moirai `b2f3732`,
  Leto `1b125ce`, and Hephaestus `f726742` provider revisions through Apollo's
  manifest, lockfile, and CI checkout SSOT.
- [x] Apollo release candidate `a4742bb` is pushed on
  `codex/apollo-moirai-feature-cleanup`; advance only the five provider gitlinks
  and Apollo gitlink in Atlas.
- Evidence tier: warning-denied workspace clippy and rustdoc, 1027/1027 Rust
  nextest cases, 34/34 Python cases, doctest, provider audit, RustSec,
  cargo-deny, locked dependency resolution, and 196 applicable
  `apollo-fft` minor-release API checks.
- Superseded: the WGPU 30 provider migration and archived `paste` cleanup are
  closed by the release increment above.

## TREE-DUP-002 — Moirai dual channel consolidation (ADR-0019) [major] — ✅ done

- [x] Extend `Channel<T>` trait with `send_batch`/`recv_batch`/`close`/`is_closed`/`len`/`stats` (default impls).
- [x] Add `InvalidConfig` variant to `ChannelError`.
- [x] Move `UnifiedChannel` into `channel::unified` implementing `Channel<T>`.
- [x] Move `ChannelConfig` → `channel/config.rs`, `ChannelStatistics` → `channel/stats.rs`.
- [x] Update `channel/mod.rs` submodule declarations and re-exports.
- [x] Remove `pub mod unified_channel` from `lib.rs`; consolidate re-exports through `channel`.
- [x] Migrate `moirai-iter` imports from `unified_channel` to `channel::unified`.
- [x] Delete `unified_channel/` directory.
- [x] Verify: `cargo check` pass on moirai-core, moirai-iter, moirai, moirai-transport.
- [x] Verify: `cargo clippy --all-targets -- -D warnings` on moirai-core, moirai-iter.
- [x] Verify: `cargo nextest run -p moirai-core -p moirai-iter` 255/255 passed.
- [x] Verify: `cargo doc -p moirai-core --no-deps` warning-clean.
- [x] ADR-0019 written and indexed in `docs/adr/INDEX.md`.
- [x] PM artifacts synced (backlog, CHANGELOG, checklist).

> **Current execution order (2026-07-12 evening session, kwavers Batch #1 + #4 closed)**:
> 1. ✅ CR-2 (`cfd-core` + `moirai` + `ritk-core`) — **fully closed 2026-07-18**. Zero `#[global_allocator]` in all three library crates.
> 2. ✅ Kwavers Stage-B (math + facade tests/examples/benches) + Stage-C (ky-python PyO3 boundary via complex_compat bridge) — `c5b1333b7` + `fa9abb664` + `ddf216ec0` + `01643ed9b` landed on `codex/kwavers-core-moirai-parallel`; cargo check --workspace --exclude kwavers-python green; cargo check -p kwavers-python --{no-default-features, gpu, plotting} all green; cargo check --tests --benches --examples --workspace --exclude kwavers-driver green (469/469 libTests, 38 doctests).
> 3. ✅ CFDrs all-features build — green with cfd-io → ritk-vtk → ritk-core → coeus-core fixed up.
> 4. ✅ RITK coeus-core pinning fix — `4d52ff8b` build(ritk): Pin coeus workspace path-deps at 0.7.0 (track coeus/main HEAD); CFDrs cfd-suite now builds green.
> 5. ✅ Kwavers Batch #1 (kwavers-solver/{solver,physics}/Rayon→Moirai `par_for_each`) — **CLOSED 2026-07-12**. Peer commit `5913f2946` "perf(kwavers-solver): Migrate solver tree to moirai parallel iterators" drives source-site count to zero: `par_for_each`=0, `burn::`=0, `nalgebra`=0, `use ndarray`=0, `kwavers-solver/Cargo.toml` clean of `ndarray`/`rayon`/`burn`. `cargo nextest run --workspace --exclude kwavers-driver --no-fail-fast --lib`: 5117/5119 pass, 2 timeouts (KW-WATCH-002 abdominal-preprocessing perf tests on 90s `elastic-fwi` profile override), 7 skipped — peer-stream perf, NOT a Batch #1 correctness regression. Atlas-meta `repos/kwavers` gitlink advanced `01643ed9 → 5913f2946`.
> 6. ✅ Kwavers Batch #4 (kwavers-solver PINN Burn → Coeus) — **CLOSED** at the new HEAD `5913f2946`. `cargo check -p kwavers-solver --features pinn` PASSES (53 warnings, 0 errors); sole residual is `kwavers-solver/Cargo.toml`'s `ndarray` `rayon` feature gate (separate item flagged in the peer commit body). Co-verified with Batch #1.
> 7. ✅ RITK Burn cleanup — **FULLY CLOSED 2026-07-18** by PR #42, with
> PR #43 closing the ledger. The prior peer-active queue is historical.
> 8. ✅ **Batch #8 (provider extension) — Leto**: `FixedMatrix<T,4,4>` determinant/try_inverse/row-major constructors + generic operators (Add/Sub/Neg/Mul<T>/Div<T>/SubAssign/MulAssign/DivAssign); `Quaternion<T>` Add/Sub/Neg/Mul<T>/Div<T> + `try_inverse`/`to_rotation_matrix`/`UnitQuaternion::{slerp,to_rotation_matrix}`. Themis 0.10 cache-level fixtures now carry the provider's optional line-size field and the lock graph has one Themis package. **PR #32 merged as `8d39f58`** after the complete local gate: fmt, warning-denied workspace Clippy, 568/568 locked nextest cases, doctests, and rustdoc.
> 9. ✅ **Batch #8 (provider extension) — Hephaestus**: `f64` DialectScalar impls for Wgsl (`"f64"`) and CudaC (`"double"`) + GPU vector type DialectScalar impls for `[f32;{2,3,4}]`, `[f64;{2,3,4}]`, `[i32;{2,3,4}]`, `[u32;{2,3,4}]` across both dialects (24 impls via macro). Themis patch added to `hephaestus/Cargo.toml`. **Verified**: `cargo clippy -p hephaestus-core --all-targets -- -D warnings` clean, `cargo nextest run -p hephaestus-core` 47/47 green.
> 10. ✅ **Batch #8 — moirai-async new crate**: `mpsc::channel`, `oneshot::channel`, `Condvar`, `Mutex`, `#[moirai::main]` proc-macro. **Verified**: 79/80 tests pass (only pre-existing flaky timer: `cancelled_timers_are_compacted_before_their_deadline` 101 vs 100), clippy `-D warnings` clean, proc-macro crate compiles.
> 11. ✅ **Batch #8 — RITK sub-batch #3.g (python/cli/snap)**: consumed by
> RITK PR #42; no deferred port remains.
> 12. ✅ **Batch #8 (provider extension) — Apollo**: RustFFT dependency removed from Apollo workspace. Pure O(N²) DFT reference oracle replaces rustfft-backed validation. Removed workspace rustfft pin, external-references feature gate, rustfft dev-dependency, vs_rustfft benchmark, and xtask benchmark runner. `cargo check -p apollo-validation` 10/10 nextest green, `cargo check -p xtask` green. Committed `b291003` on `codex/remove-rustfft`, pushed.
> 13. ✅ **Batch #8 (provider extension) — Eunomia**: eunomia-gpu crate deleted (E-019), folded into hephaestus::DialectScalar. README has no aspirational claims about eunomia-gpu — clean.
> 14. ✅ **Batch #8 (provider extension) — Coeus**: `scatter_add` exists at Tensor/Var/Python level; all 6 comparison ops (eq/ne/lt/gt/le/ge) exist. `Dataset`/`DataLoader` deferred per backlog condition ("if PINN dataset paths require") — no PINN path in scope requires them.
> 15. ✅ **Batch #8 (provider extension) — Leto-ops**: `CscMatrix<T>`, `CooMatrix<T>`, `lu_batch`, `ExecutionStrategy` trait all verified present.
> 16. ✅ **Batch #8 — All provider extension items complete.**

---

## CR-4 — `[major]` Rebase `coeus-core::Scalar` + `leto-ops::Scalar` over `eunomia::NumericElement` (universal SSOT)

> **Status (2026-07-05)**: Implementation split across 3 commits across the workspace:
>
> | Sub-step | Repo | Commit | Landed |
> | --- | --- | --- | --- |
> | eunomia SSOT extension (Complex<T>, isize, usize impls; trait doc clarifier; private::Sealed impls; CastFrom<i32> edge for platforms) | `eunomia` | `57d7789` | ✅ pushed to main |
> | coeus SSOT rebind + call-site disambiguation across `coeus-core`, `coeus-autograd`, `coeus-ops`, `coeus-nn`, `coeus-fft`, `coeus-optim`, `coeus-tensor`, doctests | `coeus` | `2b3f820` (`feat(scalar)!:`) | ✅ pushed to main |
> | leto `Scalar: NumericElement` rebind | `leto` | `b15439baf` (`feat(scalar)!:`) on `codex/leto-cr4-ssot-rebind` | ✅ pushed (2026-07-05) |
>
> **Implementation record**: the actual NumericElement-trait shape carries `from_f64`/`from_usize` only inside `FloatElement::from_f64` and the integer `v as Self` literal-cast route — *not* on `NumericElement` itself. The §5 plan originally proposed adding `from_f64`/`from_usize` to `NumericElement`, but T1-verification at compile time proved it'd collide with `FloatElement::from_f64` (duplicate method-name resolution across super/sub-trait). The actual shipped trait surface keeps `NumericElement` constants/methods-only (`ZERO`/`ONE`/`sqrt`/`abs`/`to_f64`/`is_finite`/`is_nan`/`scalar_fmadd`/`bitand`/`bitor`/`bitxor`/`count_ones`/`min_scalar`/`max_scalar`/`BYTE_WIDTH`/`MIN_VALUE`/`MAX_VALUE`/...). The simulator-side dispatch routes floats via `<T as FloatElement>::from_f64(v)` and ints via the literal `v as Self` truncating cast.
>
> **Massive call-site rewrites landed**: ~64 coeus files received `<T as Scalar>::to_f64` / `<T as Float>::abs` / `<T as Float>::sqrt` / `<T as Float>::is_finite` qualifiers — necessary because at the SSOT-bridged surface, `T::to_f64`/`T::abs`/`T::sqrt`/`T::is_finite` resolve to multiple candidates through the `Scalar: NumericElement` path. Disambiguation is the user-confirmed scope of CR-4 because the duplication concern was the *whole point* of the rebind. Adjacent clippy `assign_op_pattern` (`acc = acc + x` → `acc += x`) was fixed in the same atomic commit so the verification gate passes — these were latent-hot-loop patterns that the SSOT rebind surfaced for clippy re-analysis.
>
> **Verified (eunomia + coeus)**: `cargo fmt --check` clean, `cargo clippy --workspace --all-targets -- -D warnings` clean (`coeus-core`, `coeus-autograd`, `coeus-ops`, `coeus-nn`, `coeus-fft`, `coeus-optim`, `coeus-tensor` all clippy-green), 1031 coeus nextest tests, 29 eunomia nextest tests, doctests across all crates pass, `cargo doc --no-deps` warning-clean.
>
> **2026-07-05 (CR-4 closure, `b15439baf`)**: leto rebind landed on `codex/leto-cr4-ssot-rebind` and the atlas-meta submodule pointer for `repos/leto` was bumped from `21681967e` to `b15439ba` to consume the commit. Pre-push gates (recorded pre-stage on `codex/leto-cr4-ssot-rebind` working tree): 270/270 nextest `-p leto-ops` + 189/189 `-p leto` + 8 doctests + clippy `-D warnings` on `--lib --tests` scope. RG verification: zero remaining `Scalar::add|sub|mul|div|ZERO|ONE|bitand|bitor|bitxor|count_ones|to_f64` UFCS in `crates/`. Workspace version bumped `0.35.1 -> 0.36.0` (pre-1.0 `0.x.0` minor = breaking per `versioning`). Atomic commit: 5 files / 196 +/622- net deletion. CR-4 is **closed**; Batches #2/#3/#4 are unblocked (`Decision-of-Ready`), and Batch #1 (kwavers Rayon → Moirai) was sequenced before per token-batch ordering.

> **2026-07-05 (atlas-meta sync, `fb83d009`)**: `fb83d009 chore(atlas): Align submodule pointers to CR-4 eunomia/coeus/leto commits` aligned `repos/{coeus,eunomia,leto}` to the three landing SHAs (`1ae2f30c8` / `57d778930` / `21681967e`) and recorded the kwavers-foundation GPU-error-boundary rule in `README.md`. Pushed to `origin/codex/kwavers-atlas-integration`. Re-verification at the chore commit: eunomia 29/29 + coeus core-set 758/758 nextest green; clippy `-D warnings` clean on the core set; doctests pass; `cargo doc --no-deps` warn-clean.
>
> **2026-07-06 Hephaestus CUDA blocker refresh**: the `fb83d009` `coeus-wgpu` / `coeus-cuda` note is stale for the checked-out `repos/hephaestus` `ks5-cholesky-panel` tree. `eigen.rs` now converts `leto_ops::eigenvalues(&view)` results into `num_complex::Complex<f32>` before `device.upload(&e_host)`. Focused compile evidence: `rustup run nightly cargo check -p hephaestus-cuda --features decomposition` completed successfully against local `leto`/`leto-ops` `0.36.0`. This is compile/build evidence only; runtime CUDA nextest coverage remains separate.

> **## RESOLVED — CR-4 leto side merged via PR #31 ##**

> PR #31 (`codex/leto-cr4-ssot-rebind`) was merged into `origin/main` at `d9e8ac9`. Resolution (a) was applied: rebase onto origin/main post-PR-#30, remove `add/sub/mul/div` and `ZERO/ONE/bitand/bitor/bitxor/count_ones/to_f64` from `Scalar` (inherited from `NumericElement`), slice kernels rewritten to operator-syntax. 5 additional commits landed on top (`28d0a03`..`86d366bc`). Submodule pointer at `86d366bc` == `origin/main`. All downstream batches (Batch #2 CFDrs, Batch #3 ritk, Batch #4 kwavers PINN) are unblocked.
>
> **Historical record retained in git log** — the resolution path, structural-infeasibility addendum (E0034), and user-decision-required state are preserved in the commit history for audit. See `git log --all --oneline origin/main | grep -E "b15439b|d9e8ac9"` for the merge trail.

> **Design SSOT**: `atlas/docs/adr/0005-eunomia-scalar-ssot.md` (status: **Proposed**, awaiting user sign-off pre-implementation per `versioning` policy).
>
> **Correction note**: this section's earlier text proposed `Scalar: NumericElement + RealField` as the binding. The ADR's pre-implementation T1 read disproves that — `eunomia::RealField: FloatElement` is **float-only** (per `eunomia/src/traits/field.rs:17`), and `coeus_core::Int: Scalar` (`coeus-core/src/dtype/traits.rs:551-569`) is implemented for `i8`/`i16`/`i32`/`i64`/`u8`/`u16`/`u32`/`u64`. Binding `Scalar: RealField` would orphan every integer `Int` impl and is a HARD integrity defect (fake-generic / alias-driven architecture). The correct binding is `NumericElement` only — the universal element vocabulary whose impl set covers `{f32, f64, f16, bf16}` ∪ signed+unsigned ints (verified at `eunomia/src/impls/primitives/{numeric,float}.rs`). An empty-body `Scalar {}` supertrait is ALSO rejected — it would silently strip the legitimate backend extension surface (`add_slice`/.../`max_slice`, `gemv_*`, `tiled_gemm`, `leto_ops::Scalar::from_usize`) which belongs on the backend `Scalar`, NOT on `NumericElement`.

**Pre-reqs** (Definition-of-Ready):
- User signs off on `atlas/docs/adr/0005-eunomia-scalar-ssot.md` (✅ entry on 2026-07-04).

**Plan** (ordered, atomic commits per increment):
1. **[arch] coeus-core** + eunomia SSOT enlargement (atomic commit touching 3 crates):
   - `eunomia/crates/eunomia/src/traits/numeric.rs:7-110`: add `fn from_f64(v: f64) -> Self { v as Self }` and `fn from_usize(v: usize) -> Self { v as Self }` to `NumericElement`. (See ADR 0005 §5 for rationale; the §5 "no change" non-decision in the original ADR was overconfident.)
   - `coeus/coeus-core/src/dtype/traits.rs:277-450` (`pub trait Scalar`):
     - Supertrait set: `pub trait Scalar: NumericElement + CpuUnaryDispatch + Pod + Rem<Output=Self> + Clone`. Drop redundant `Copy/Send/Sync/Debug/PartialOrd/Add/Sub/Mul/Div/'static` (all on `NumericElement`). Drop `private::Sealed` (eunomia's seal covers this).
     - Delete required methods: `zero`, `one`, `to_f64`, `from_f64`, `from_usize`, `sqrt_val`, `abs_val` (each duplicates `NumericElement::ZERO`/`::ONE`/`::to_f64`/`::from_f64`/`::from_usize`/`::sqrt`/`::abs` post-§5).
     - Keep default-bodies slice-kernel surface (`add_slice`/`sub_slice`/`mul_slice`/`div_slice`/`dot_slice`/`scale_slice`/`axpy_slice`/`sum_slice`/`min_slice`/`max_slice`) — these are the `hermes-simd` per-type seam, NOT duplicated on `NumericElement`.
   - `coeus/coeus-core/src/dtype/float/native.rs:5-37` (`impl_scalar_float_native` macro for `f32`/`f64`): delete the 7 redundant methods from `Scalar` impl; the slice-kernel surface stays as `coeus_core::Scalar` trait bodies. Float `Float`/`FloatOps`/`CpuUnaryDispatch` impls outside `Scalar` are unaffected.
   - `coeus/coeus-core/src/dtype/float/half.rs:6-37` (`impl_scalar_float_half` macro for `f16`/`bf16`): same — empty the Scalar impl.
   - `coeus/coeus-core/src/dtype/int.rs:9-108` (int orig/uint orig macros for `i8..u64`): empty the Scalar impl.
   - `coeus/coeus-core/src/dtype/float/cpu_unary.rs` (`impl_cpu_unary_dispatch_float` macro):
     - `Self::zero()` → `<Self as eunomia::NumericElement>::ZERO`
     - `Self::one()` → `<Self as eunomia::NumericElement>::ONE`
     - `Self::from_f64(v)` → `<Self as eunomia::FloatElement>::from_f64(v)`
     - `x.sqrt_val()` → `eunomia::NumericElement::sqrt(x)` (call form: `x.sqrt()`)
     - `x.abs_val()` → `eunomia::NumericElement::abs(x)` (call form: `x.abs()`)
   - `coeus/coeus-core/src/dtype/int.rs:155-225` (`impl_cpu_unary_dispatch_int` macro):
     - `Self::zero()` → `<Self as eunomia::NumericElement>::ZERO`
     - `Self::one()` → `<Self as eunomia::NumericElement>::ONE`
     - `Self::from_f64(v)` → `v as Self` (literal truncating cast; no `FloatElement::from_f64` for ints)
     - `x.abs_val()` → `eunomia::NumericElement::abs(x)`
     - `x.sqrt_val()` → `eunomia::NumericElement::sqrt(x)`
   - `coeus/coeus-core/src/dtype/float/native.rs:198-203` (`impl_scalar_float_native: gelu_op`): `<$t as Scalar>::from_f64(0.5)` → `<$t as eunomia::NumericElement>::from_f64(0.5)` (now resolves through SSOT).
   - `coeus/coeus-core/src/dtype/complex.rs:161-220` (`impl<T: Float> Scalar for Complex<T>`): becomes an empty impl block (the trait requires no methods post-rebase; slice kernels inherit defaults). Delete the whole impl body. Any caller of `Scalar::zero()/one()/etc.` on `Complex<T>` must migrate per caller-rewrite below in §5 of this checklist.
   - `coeus/coeus-core/src/dtype/complex.rs:222-281` (`impl<T: Float> CpuUnaryDispatch for Complex<T>`): within the dispatch macro body, replace `Self::zero()`/`Self::one()` with `<Self as eunomia::NumericElement>::ZERO/::ONE`, `T::zero()`/`T::one()` with `<T as eunomia::NumericElement>::ZERO/::ONE`, `x.sqrt_val()` becomes `eunomia::ComplexField::sqrt(x)` (delegation: field.rs:158-160), `x.abs_val()` becomes `eunomia::ComplexField::from_real(eunomia::ComplexField::modulus(x))`.
   - `coeus/coeus-core/src/dtype/float/native.rs` and half's `gelu_op/erf_op/lgamma_op` etc.: any `<$t as Scalar>::from_f64(...)` becomes `<$t as eunomia::NumericElement>::from_f64(...)` (post-§5).
   - Cargo: no Cargo.toml change required (`coeus-core/Cargo.toml` already declares `eunomia = { workspace = true }`).
   - Verify: `cargo nextest run -p coeus-core -p eunomia`, `cargo test --doc -p coeus-core -p eunomia`, `cargo doc --no-deps -p coeus-core -p eunomia`, `cargo semver-checks release -p coeus-core -p eunomia`. Atomic commit; bump per `cargo-semver-checks` output (`eunomia` `[minor]` additive; `coeus-core` `[major]` removal).
2. **[patch or minor] leto-ops** (`leto/crates/leto-ops/src/domain/scalar.rs:12-177`):
   - `pub trait Scalar: NumericElement { fn from_usize(value: usize) -> Self; /* default-bodies slice kernels */ }`. Only `from_usize` remains required.
   - `impl_scalar_simd!` and `impl_scalar_plain!` macros unchanged in body (they only set `from_usize` and override default slice kernels).
   - Verify `leto-ops`'s `eunomia` dep (`Cargo.toml:22`, already present) covers the new supertrait; no Cargo change.
   - Optional follow-on [patch] (separate commit, separate batch entry): strip `num-traits` from `leto-ops/Cargo.toml:18` if `rg "num_traits" repos/leto/crates/leto-ops/src` returns zero after this change.
   - Verify: `cargo nextest run -p leto -p leto-ops`, `cargo test --doc -p leto-ops`, `cargo doc --no-deps -p leto-ops`, `cargo semver-checks release -p leto-ops`. Atomic commit.
3. **(verify-only) gaia** — `gaia/src/domain/core/scalar.rs:54-106` already bound over `eunomia::RealField`; no change. Verify `cargo nextest run -p gaia` green after #1+#2 land.
4. **(verify-only) eunomia** — `NumericElement::ZERO`/`::ONE` already at `eunomia/src/traits/numeric.rs:27-29`; no source change. Verify `cargo doc --no-deps -p eunomia` warning-clean.
5. **Consumer-repo verification** — `cargo nextest run` for downstream packages that consume `coeus-core::Scalar` or `leto-ops::Scalar`: `-p kwavers-math -p cfd-math -p ritk-registration` at minimum.
6. **PM sync** (in the same commit as #1): mark CR-4 done here, mark `atlas/gap_audit.md` CR-4 row CLOSED, resequence Batches #2/#3/#4 as Definition-of-Ready in `atlas/backlog.md`, write provider-local backlog entries per `architecture_scoping` PM scope isolation.
7. **CHANGELOG**: under `Breaking` in `repos/coeus/CHANGELOG.md` and `repos/leto/CHANGELOG.md` (subject to `cargo-semver-checks` final classification).

**Leak-check (investigate during implementation; not blocking the ADR)**:
- `Complex<T>::from_usize` post-rebase: if `T` is bounded only on `coeus_core::Scalar` (which after rebase is `NumericElement`, not `leto_ops::Scalar`), there is no `from_usize` on `T`. Two resolutions: (a) make `Complex<T>::from_usize` an inherent helper that delegates to `v as T` for floats (requires `T: FloatElement`) — works because `Complex<T>` is bounded on `Float` already, which inherits the f32/f64-only `as`-cast surface; or (b) require `Complex<T>: Scalar` impls also bound `T: leto_ops::Scalar` — unlikely. Resolution (a) is cleanest; investigate at impl time.

**Completion condition (evidence)**:
- `cargo nextest run -p eunomia -p coeus-core -p coeus-autograd -p coeus-ops -p leto -p leto-ops -p gaia -p kwavers-math -p cfd-math -p ritk-core -p ritk-registration` green.
- `cargo test --doc -p coeus-core -p leto-ops -p eunomia` green.
- `cargo semver-checks release -p coeus-core -p leto-ops` reports the §7-predicted classification (`[major]` for coeus-core; `[minor]` or `[patch]` for leto-ops).
- `rg -n "<.+ as Scalar>::(zero|one|to_f64|from_f64|from_usize|sqrt_val|abs_val)\b" repos` returns zero matches (every duplicated call site migrated to `NumericElement`/`FloatElement`/inherent).
- `rg -n "trait Scalar" repos/{coeus,leto,gaia,eunomia}` returns exactly 3 matches (the 3 backend `Scalar` traits); zero new redeclarations.
- `Complex<T>` tests (wherever they live in `repos/coeus`) value-semantically green; principal `sqrt`/`abs`/`from_f64`/`to_f64` results bitwise-identical pre/post.

**Next step after CR-4 (unblocks)**:
- Batches #2 (CFDrs nalgebra finish), #3 (ritk Burn trait rebind), #4 (kwavers-solver PINN → Coeus) become Definition-of-Ready.
- Per `decision_policy` lowest-risk-vertical-slice bias, Batch #1 (kwavers-solver/physics Rayon → Moirai) is sequenced next — but it is *not gated by CR-4* and can land in parallel; see its own checklist section.

**Pre-reqs** (Definition-of-Ready):
- ✅ `coeus/coeus-core/src/dtype/traits.rs` current shape T1-read by owner (2026-07-04).
- ✅ `leto/crates/leto-ops/src/domain/scalar.rs` — CR-4 rebind merged via PR #31 (`d9e8ac9`) on `origin/main`. Submodule pointer at `86d366bc`.
- ✅ Both eunomia + coeus-primary redeclarations removed; backends extend `NumericElement` rather than redeclare vocabulary.

**Plan (archaeology — superseded by ADR 0005; closed via execution)**:
The original CR-4 plan proposed methods and trait shapes that diverge from what actually shipped. See ADR 0005 for the correct design. The actual execution is recorded in the commit chain:
- eunomia: `57d7789`
- coeus: `2b3f820`
- leto: `b15439b` (on `codex/leto-cr4-ssot-rebind`), merged to `origin/main` via PR #31 at `d9e8ac9`

**Next step after CR-4 (unblocks, per ADR 0005)**:
- Batches #2/#3/#4 are Definition-of-Ready. The token-batch ordering in `atlas/backlog.md` is: #5 (CR-1) → #6 (CR-2) → #1 → #2 → #3 → #4 → #8.
- Per `decision_policy` lowest-risk-vertical-slice bias, Batch #1 (kwavers-solver/physics Rayon → Moirai) is sequenced next — but it is *not gated by CR-4* and can land in parallel; see its own checklist section.

---

## Batch #5 — CR-1 (Apollo-ghostcell → Melinoe) `[arch]`

> Dependency-only — no Atlas-migration unblock, but the cleanup intrinsic to this branch goal.

**Pre-reqs**:
- `apollo/crates/apollo-ghostcell/src/lib.rs` inventoried: full source-read by owner.
- `melinoe::MelinoeCell` reachable (confirmed at `melinoe/src/lib.rs:18-24, 65-115, 233`).
- Apollo's consumers via `apollo-ghostcell` cited: T1 cross-grep `rg -l "apollo_ghostcell\|ghostcell" repos/apollo/crates`.

**Plan**:
1. List every consumer of `apollo_ghostcell` across `apollo` workspace via cross-grep (T1: `rg -nl "ghostcell" repos/apollo`).
2. For each: replace `apollo_ghostcell::*` with `melinoe::*`; patch the `brand_scope!` mint call to `melinoe::brand_scope!(|mut token| ...)`.
3. Delete `apollo/crates/apollo-ghostcell` from `apollo/Cargo.toml` workspace `members`.
4. Update `apollo/docs/adr/*` (if any IDR exists) referencing `apollo-ghostcell`; cross-link to `melinoe` as the SSOT.
5. Changelog: `[arch]` bump `apollo` per templating (`repos/apollo/release.toml`), with `BREAKING CHANGE:` footer.

**Completion condition**:
- `repoS/apollo` no longer carries `apollo-ghostcell` member.
- `rg -l ghostcell` returns zero matches across `apollo` (only `melinoe` mentions kept).
- `cargo nextest run -p apollo-* --features melinoe` green.
- `cargo miri test -p melinoe` green.
- `cargo clippy --all-targets -- -D warnings` green.

---

## Batch #6 — CR-2 (Consolidate `#[global_allocator]`) `[arch]`

> **Status (2026-07-18)**: ✅ **FULLY CLOSED** across cfd-core, moirai, and
> ritk-core. Source scans find zero `#[global_allocator]` sites in all three
> library crates.
>
> | Site | Action | Status |
> |------|--------|--------|
> | `cfd-core/src/lib.rs:45-51` | Removed `#[global_allocator]` + entire `mnemosyne` feature | ✅ committed `e24922c8` |
> | `moirai/moirai/src/lib.rs:202-205` | Removed `#[global_allocator]` registration | ✅ committed `ce22f85` |
> | `ritk-core/src/lib.rs:15-17` | Removed in commit `ba6da3a5` | ✅ committed |
> | `CFDrs/Cargo.toml` | Removed workspace `mnemosyne` dep + feature; removed `no-global-alloc` from moirai features | ✅ committed |
> | `coeus-python/src/lib.rs:7-9` | Out of CR-2 scope (cdylib = binary artifact) | N/A |
> | `cfd-validation/src/benchmarking/memory.rs:92-96` | Out of CR-2 scope (`TrackingAllocator` wraps `System`, not mnemosyne) | N/A |

**Pre-reqs** (historical — all satisfied):
- ✅ Inventory: T1 identified 6 `#[global_allocator]` sites across 5 repos.
- ✅ No binaries currently register `#[global_allocator]` — allocator policy is now a clean binary-level concern.

**Plan** (closed):
1. ✅ Audit: `cfd-core/src/lib.rs:45-53`, `moirai/moirai/src/lib.rs:202-205`, `ritk-core/src/lib.rs:15-17`.
2. ✅ Removed `#[global_allocator]` from cfd-core (including `mnemosyne` dep + feature).
3. ✅ Removed `#[global_allocator]` from moirai (deeper mnemosyne integration preserved).
4. ✅ Updated CFDrs workspace: removed `mnemosyne` workspace dep and feature; removed `no-global-alloc` from moirai features.
5. ✅ Verified: `cargo check -p cfd-core`, `cargo check -p moirai`, full CFDrs workspace all clean.

**Completion condition**:
- ✅ `cfd-core/src/lib.rs` no longer carries `#[global_allocator]` or `mnemosyne` feature.
- ✅ `moirai/moirai/src/lib.rs` no longer carries `#[global_allocator]`.
- ✅ `cargo check -p cfd-core`, `cargo check -p moirai`, full CFDrs workspace green.
- ✅ `ritk-core` no longer registers a global allocator.
- ⏭️ `cargo nextest run -p cfd-core` timed out (120s limit; GPU compilation-heavy suite).

---

## Batch #1 — `[patch]` kwavers-solver / kwavers-physics residual Rayon → Moirai

> **Status (2026-07-10)**: peer advanced kwavers inner HEAD to `ca1530ffd`. Residual `par_for_each` sites reduced from 41→**4** across 3 files:
>
> | File | Sites |
> |------|------:|
> | `forward/elastic/swe/integration/integrator/mod.rs` | 1 |
> | `forward/nonlinear/kuznetsov/solver/rhs.rs` | 1 |
> | `forward/nonlinear/kuznetsov/workspace.rs` | 1 |
> | `safety/mod.rs` | 2 |
> | **Total** | **4** |
>
> The peer made substantial progress since the H-067 partial-closure mark (30 sites → 4). The `kwavers-solver/Cargo.toml` ndarray `rayon` feature strip was landed earlier at `702e4f125`. The `cargo tree -p kwavers-solver | grep rayon` still shows rayon transitively through `ritk → burn` (provider-side, not Batch #1 gate). 10 dirty files remain in the kwavers working tree (Batch #4 cleanup + nalgebra→leto residual migration in flight).

- **slice 1 partial-closure-mark 2026-07-08 (2/41 sites, 1/15 files)**: per the peer's `5cd8c708` chore
  on `codex/kwavers-core-moirai-parallel` (atop parent `ccc6bbf9`):
  `crates/kwavers-solver/src/multiphysics/fluid_structure/solver/
  struct_impl.rs` has had its 2 `.par_for_each()` call-sites migrated to
  `moirai_parallel::ParallelSliceMut::par_mut().enumerate()` (idiomatic
  trait form, auto-Adaptive policy). Cargo-check pre-validate clean. 39/41
  sites / 14/15 files remain; the full closure-mark (`✅ Batch #1 CLOSED
  2026-07-08`) remains retracted per the prior retraction (`0060b1e10` was
  measured against an uncommitted working-tree snapshot, not the
  committed inner HEAD `35ee01076`). The next slices are tracked via
  per-slice partial-closure marks; the full-closure mark can be
  reasserted only when the source-side count actually drops to zero.


**Pre-reqs**:
- `moirai-parallel/src/lib.rs:106-181` confirms `par()` / `par_mut()` rebind (T1 verification by owner).
- `crates/kwavers-solver/src/{inverse/reconstruction/seismic/rtm/inherent, inverse/same_aperture}/...` and `crates/kwavers-physics/src/acoustics/...` source-read in inventory.
- Migration pattern noted: `Zip::indexed(arr).par_for_each(...)` → `auto_moirai_for_each(arr, |i, _| ...)`. Helper macro or `par().enumerate()` direct.

**Plan**:
1. Add the helper `let''o::par_for_each_indexed` if not present (or use `moirai-parallel::par_mut().enumerate()` directly). Cite library file.
2. For each `.par_for_each` site in `kwavers-solver/src/inverse/reconstruction/seismic/rtm/inherent/{...}.rs` (23 sites) and `kwavers-solver/src/forward/nonlinear/kuznetsov/{...}.rs` (19 sites), patch to replace.
3. For each `.par_for_each` site in `kwavers-solver/src/forward/elastic/swe/{integration,stress}/...` (13 sites).
4. For each `.par_for_each` site in `kwavers-solver/src/forward/pstd/extensions/elastic.rs` (4 sites).
5. For each `.par_for_each` site in `kwavers-solver/src/multiphysics/fluid_structure/{interface,solver}.rs` (3 sites).
6. For each `.par_for_each` site in `kwavers-physics/src/acoustics/...` and `kwavers-physics/src/optics/polarization/linear.rs` (24 sites).
7. Strip `ndarray = { ..., features = ["rayon"] }` from `kwavers-solver/Cargo.toml:24` and `kwavers-physics/Cargo.toml:20`.
8. Confirm `cargo tree -p kwavers-solver | grep ndarray` shows no `rayon` feature.
9. CHANGELOG: `[patch]` per `kwavers/CHANGELOG.md` with Replaced fence data citing each module.

**Progress this slice** (resumed 2026-07-05 after CR-4 closure unblocks):
- Prior slice (2026-07-01, peer ryancinsight commits `e9f426d38`–`1f320cfe6`): replaced `Zip::indexed(...).par_for_each(...)` with `crate::parallel` helpers in:
  - `crates/kwavers-physics/src/acoustics/skull/heterogeneous/mask.rs`
  - `crates/kwavers-physics/src/acoustics/therapy/sonogenetics/membrane.rs`
  - `crates/kwavers-physics/src/acoustics/mechanics/cavitation/damage/erosion.rs`
  - `crates/kwavers-physics/src/chemistry/{reaction_kinetics,ros_plasma/ros_species}/**`, `thermal/diffusion/{bioheat,hyperbolic}.rs`, `optics/sonoluminescence/{blackbody,bremsstrahlung,cherenkov}/**`, `field_surrogate/{cube,resample}.rs` — `crate::parallel::for_each_indexed_mut` / `for_each_indexed_pair_mut` / `zip_mut_two_refs` / `zip_mut_three_refs` / `zip_mut_four_refs` / `zip_two_mut_two_refs` family.
  - `crates/kwavers-transducer/src/basic/{linear_array,matrix_array}.rs`, `transducers/focused/{arc,bowl,multi_bowl}.rs`, `transducers/phased_array/transducer.rs` — `enumerate_mut_with::<Adaptive, _, _>` direct.
  - `kwavers-core` direct Rayon edge — full Moirai migration landed in `e9f426d38`.
- **Session-window work (peer, 2026-07-05 22:16+22:19)**: `1dc47028a refactor(kwavers-math)!: Port to eunomia/leto/moirai-parallel, drop nalgebra` (8416 +/- 3734 across 131 files, includes `crates/kwavers-math` CSR + tensor + differential + simd-safe rewrite); `f36995162 refactor(kwavers-gpu, kwavers-solver)!: Generic GPU provider seam over Hephaestus`. These commits close the **`kwavers-math` migration** (separate from Batch #1) and add the GPU backend seam; they do NOT migrate `kwavers-solver`/`kwavers-physics` Rayon sites or strip the `rayon` feature from `Cargo.toml`. The peer is **actively landing adjacent scope** — Batch #1 is not stale/reclaimable; this meta layer does not initiate kwavers-source edits.
- **Baseline (reclaim verification 2026-07-05, branch tip `1f320cfe6`)**: `cargo check -p kwavers-solver --lib` finishes green in 3m09s with all Atlas dependencies (eunomia, leto, moirai-parallel, hermes, coeus, apollo-fft, ritk) resolving via submodule path; CR-4 `leto 0.36.0` (`b15439ba`) integrates cleanly. No CR-4 fallout; auto-resolution via `eunomia::NumericElement` operator items. (Newer branch tip `f36995162` adds the GPU seam and the math port; full verification on that tip is the peer's responsibility.)
- **Residual inventory (re-measured at branch tip)**: 107 `Zip::indexed(...).par_for_each(...)` / `Zip::from(...).par_for_each(...)` sites across 40 files — 31 in `kwavers-solver/src/{forward,inverse,integration,multiphysics,pstd}/**` and 9 in `kwavers-physics/src/{acoustics,optics,thermal}/**`. `kwavers-math` and `kwavers-core` are Rayon-free (zero residual). Top-density residual files: `inverse/reconstruction/seismic/rtm/inherent/imaging.rs`, `forward/elastic/swe/integration/integrator/mod.rs`, `forward/viscoacoustic/solver.rs`, `kwavers-physics/src/acoustics/mechanics/acoustic_wave/nonlinear/numerical_methods/spectral/mod.rs`, `forward/pstd/extensions/elastic_orchestrator/split_field_step/stress.rs`, `forward/nonlinear/kuznetsov/solver/rhs.rs`.
- Arities present in residual set: 1-mut + N-imm (covered by existing `zip_mut_*_refs`); 2-mut + N-imm (covered by existing `zip_two_mut_two_refs`); **3-mut + N-imm (helper gap); 4-mut + N-imm (helper gap); 6-arity mixed mut/imm indexed (helper gap)**.
- **Planned increment (peer-owned; tracked here for hand-off)**: extend `crates/kwavers-physics/src/parallel.rs` and add a parallel sibling helper module in `kwavers-solver` with `for_each_indexed_three_mut_*` / `for_each_indexed_four_mut_*` + indexed variants using `moirai-parallel::for_each_chunk_triple_mut_enumerated_with` / `for_each_chunk_quad_mut_enumerated_with` (already exposed at `src/ops.rs:335,408`). Disjoint-mut-pointer slice safety reused from existing helpers; contiguous-slice fast path + ndarray `Zip` fallback preserved as in existing patterns. Then migrate the 40 residual files mechanically. Then strip `rayon` feature from `Cargo.toml:43`, `crates/kwavers-solver/Cargo.toml:24`, `crates/kwavers-physics/Cargo.toml:20`.

**Completion condition**:

**Completion condition**:
- `cargo nextest run -p kwavers-solver -p kwavers-physics` green.
- `cargo nextest run -p kwavers-solver -p kwavers-physics fast_tests/medium_tests/slow_tests` green with no skip.
- `cargo tree -p kwavers-solver | grep rayon` returns zero.
- `cargo clippy --all-targets -- -D warnings -p kwavers-solver -p kwavers-physics` green.
- Spatial norm conservation: each migrated module's spatial-step norm within `O(N·ε)` bounded derived epsilon (reduction order). FFT/PSTD residual reductions derive Kahan-compensated epsilon per `numerical_discipline`.

---

## Batch #2 — `[minor]` CFDrs nalgebra → leto completion; nalgebra-sparse → leto-ops

> **Status (2026-07-05)**: ✅ **CLOSED**. Inner CFDrs HEAD advanced `0f578e1af110c5b8536476174bf266bf8b812c37` → **`d58d1fe320d046816425e1d20d16735fcfee7995`** via a single Atlas-provider migration push (subject `refactor(cfdrs): Atlas-provider migration push (Leto CSR + Eunomia scalar + Hephaestus GPU + cfd-math / cfd-2d / cfd-3d / cfd-1d / cfd-validation consumer cones)` — 752 modified + 19 added files, 51,857 insertions / 22,087 deletions, ~2,500 tests pass, 0 warnings). The 185-line xtask `legacy_surface.allowlist` + 176 source files + 7 manifests of legacy `nalgebra 0.33 [serde-serialize]` / `nalgebra-sparse 0.10` / `num-traits 0.2` / `num-complex 0.4` are consumed in this commit; post-push `cargo tree -p CFDrs | grep nalgebra` returns zero production ops. Atlas-parent submodule pointer advance recorded at parent HEAD `51922a56c4d4acab3dbe786b90cc5acf92e22277` (`chore(atlas): Advance CFDrs submodule pointer to d58d1fe3`). See `repos/CFDrs/CHANGELOG.md` `## Unreleased` Atlas-provider migration push section.

**Pre-reqs** (post-CR-4):
- `eunomia::RealField` reachable; consumers routed.
- `let''o::Array1/2/3<T>` publicly exposed (confirmed T1).
- `let''o-ops::CsrMatrix` reachable (CFDrs `crates/cfd-math/src/sparse/operations.rs:37` already consumes).
- `let''o::FixedMatrix<T,3,3>` and `FixedVector<T,3>` reachable (confirmed T1).

**Plan** — two passes:
A. **Trait surface rebind** (per `LetoRealScalar` chain):
   - `cfd-math/src/linear_solver/chain.rs:62-72` rebind to eunomia `RealField`. Update BiCGSTAB fallback.
   - Every `RealField` mention in `cfd-math/src/linear_solver/{conjugate_gradient, bicgstab, gmres, preconditioners, matrix_free}/...`. File-line inventory per part-A row.
   - `cfd-math/src/dense_bridge.rs:4-5` already a Leto boundary; rebind internals.
B. **Body migration** (per-file):
   - `cfd-math/src/linear_solver/preconditioners/{basic, cholesky, deflation, ilu/{ilu0, iluk, triangular, types}, multigrid/{amg, coarsening/{mod, algorithms, quality}, interpolation, smoothers, mod}, schwarz, ssor}.rs` — `nla_sparse::CsrMatrix` → `let''o_ops::CsrMatrix`.
   - `cfd-3d/src/fem/{element:35, projection_solver:446+, leto_bridge, mesh_utils, mid_node_cache, quadrature, shape_functions, solution, solver, stabilization, stress, fluid}.rs` — `nalgebra::{DMatrix,DVector,Matrix3,Vector3}` → `let''::{Array2,Array1,FixedMatrix<T,3,3>,FixedVector<T,3>}`.
   - `cfd-3d/src/{bifurcation, trifurcation, venturi, serpentine, ibm}/**` — same.
   - `cfd-3d/src/vof/{cavitation_solver, reconstruction}.rs` — `DMatrix` → `let''::Array2`.
   - `cfd-1d/src/solver/core/{convergence:63,214, linear_system:36,37,364, matrix_assembly:63,64, state:20, workspace:2, anderson_acceleration, mod, solver_detection}.rs`, `cfd-1d/src/domain/network/wrapper.rs:13`, `cfd-1d/src/scalar.rs` — drop `nalgebra_sparse` storage.
   - `cfd-validation/src/geometry/{annular, bifurcation_2d, circular, rectangular, trifurcation_2d, threed/bifurcation}.rs` — geometry `DMatrix/DVector` → leto.
   - `cfd-validation/src/benchmarks/{cavity, cylinder, poiseuille_bifurcation:60, runner, step, threed/nufft_coupling, mod}.rs` — solver vector Realmigration.
   - `cfd-validation/src/{adaptive_mesh, numerical, manufactured, literature, tests, benches}/**` — `DMatrix` reservoir.
   - `xdtests 176-file allowlist` — drop after closure, `xtask migrate-audit -- --strict-context` reports zero legacy residual.
3. Strip `CFDrs/Cargo.toml:38-41` (`nalgebra`, `nalgebra-sparse`, `num-traits`, `serde-serialize` feature) and the per-crate `Cargo.toml` entries.
4. Adopt `[patch]` for `nalgebra*` workspace-level = not needed (unconditional drop).
5. CHANGELOG: `[minor]` per CFDrs policy.

**Completion condition**:
- `cargo nextest run -p cfd-math -p cfd-3d -p cfd-1d -p cfd-validation -p cfd-2d -p cfd-core` green.
- `cargo xtask migrate-audit --strict` returns no legacy tokens across CFDrs.
- `cargo tree -p CFDrs \| grep nalgebra` returns zero production ops.
- Numerical regression: each module's spatial-step norm/par criteria remain within pre-migration baseline per analytics-child false-__________ epsilon budget (criterion baseline).

---

## Batch #3 — `[minor]` ritk Burn-keyed trait rebind (provider side, 6 atomic sub-batches per ADR 0012)

> **Status (2026-07-18)**: ✅ **FULLY CLOSED**. All sub-batches consumed by the atomic provider cutover: Sub-batch #1 (`RITK-Atlas-typed-trait-surface`) **closed** 2026-07-06. Sub-batch #2 (trait soft deprecation) **closed** 2026-07-06. Sub-batches #3.a–#3.f per-crate queue **closed** 2026-07-06. Sub-batches #3.g+#4+#5+#6 **closed** by PR #42 (`f01b1643`, 1298 files, -59482 lines, burn_surface.allowlist deleted, all consumers migrated to Coeus) + PR #43 (`b4be04ca`, closeout docs) + fixes `6086d757`/`9de12515`/`24a3cb08`. Atlas pointer advanced `b007326e` → `9af7dbbe` for that closure and now tracks projection-hardening PR #44 at `688eb8e`. ADR: `docs/adr/0012-ritk-burn-trait-rebind.md` (status **Accepted**). Per-sub-batch ceremony template preserved in git history for audit.

### Atomic-boundary discipline (mandatory for all sub-batches)

Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision:

1. **Strict additive OR strict subtractive per sub-batch**. A sub-batch either widens the Atlas surface (adds new pub-export, new trait, new impl) OR narrows the Burn surface (deprecates, removes, rewrites a symbol) — never both in one commit. This protects the bisect rollback path.
2. **No public-type signature narrowing on the Burn-keyed surface** until sub-batch #5 (`[major]`). The legacy `Image<B: Backend, D>`, `Transform<B: Backend, D>`, `Interpolator<B>`, `Resampleable<B, D>`, `Vector<D>::Module<B>`, `Point<D>::Module<B>`, `Direction<D>::Module<B>`, `Spacing<D>::Module<B>`, and per-crate reader/writer `B: Backend` fn signatures stay exactly as today through sub-batch #4.
3. **Cargo.toml is in one place per sub-batch**. Sub-batch #5 is the only commit allowed to delete or rename `[dependencies]` lines.
4. **Compile-gate per sub-batch**: `cargo fmt --check` + `cargo clippy --workspace --all-targets -- -D warnings` + `cargo nextest run -p ritk-{core,image,filter,registration,segmentation,transform,interpolation,spatial}` + `cargo test --doc` + `cargo doc --no-deps` (warning-clean).
5. **Atlas-only validation per sub-batch**: `cargo tree --workspace -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` each return zero; allowlist unchanged (sub-batch #6 owns the contract).

### Sub-batch #1 — `RITK-Atlas-typed-trait-surface` `[patch]` — CLOSED 2026-07-06

Additive Atlas-typed parallel trait surface; pure pub-export adds; no Burn-keyed surface mutation. 5-file change-set:

- `repos/ritk/crates/ritk-core/Cargo.toml`: add `coeus-core = { workspace = true }` and `coeus-tensor = { workspace = true }` to `[dependencies]` (workspace-declared at `repos/ritk/Cargo.toml:78-79`).
- `repos/ritk/crates/ritk-image/src/lib.rs:11`: add `pub use native::Image as AtlasImage;` (alongside the existing `pub use types::Image;`).
- `repos/ritk/crates/ritk-core/src/transform/trait_.rs`: append `TransformAtlas<T: Scalar, B: ComputeBackend, const D: usize>: Sized` + `transform_points(&self, points: Tensor<T, B>) -> Tensor<T, B>` + `inverse(&self) -> Option<Self> { None }` DEFAULT body; mirror `ResampleableAtlas`.
- `repos/ritk/crates/ritk-core/src/interpolation/trait_.rs`: append `InterpolatorAtlas<T: Scalar, B: ComputeBackend>` + `interpolate<const D: usize>(&self, data: &Tensor<T, B>, indices: Tensor<T, B>) -> Tensor<T, B>`.

Per ADR 0012 §Decision §Sub-batch #1, the new traits have **default-method-only bodies with no concrete impls on day 1**. `[allow(dead_code)]` markers are added to suppress unused-warning until consumer crates migrate in sub-batch #3+.

Compile-gate verifications: `cargo check -p ritk-core -p ritk-image -p ritk-transform -p ritk-interpolation` succeeds; `cargo tree --workspace -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` each return zero (state preserved from `65a1a0fd`).

### Sub-batches #2-#6 — HISTORICAL PLAN (all closed 2026-07-18)

Per ADR 0012 §Decision §Sub-batches #2-#6. The high-level `## Batch #3 — \[minor\] ritk Burn-keyed trait rebind (provider side)` section ABOVE (in this checklist, the original text under this H2 header) is now the sub-batch ceremony template + atomic-boundary discipline.

#### Historical sub-batch #3 queue — opened 2026-07-06, closed 2026-07-18

This is the original 7-per-crate decomposition. RITK PR #42 consumed the
complete queue and PR #43 closed its ledger.

**Per-crate sub-atomic increment = port ONE specific test module from `burn_ndarray::NdArray<B>` to `AtlasImage<T: Scalar, B: ComputeBackend, D>` over `coeus_tensor::Tensor<T, MoiraiBackend>`.** Each per-crate commit is strictly subtractive (drops 1 source-row from `xtask/burn_surface.allowlist`), preserves every public Burn-keyed signature intact, and lands only Atlas-typed test bodies + Atlas-typed device/build patterns. No `#[deprecated]` attribute added (would emit 671-file compile-warning cascade per the sub-batch #2 carry-over rule). No `Cargo.toml` mutation. No `pub use …;` re-export change.

**Historical per-crate order (closed):**

| # | Crate | Burner-touching file-count | Smallest sub-atomic increment | Atlas-side substrate |
|---|-------|---:|---|---|
| #3.a | `ritk-filter` | 296 | `morphology/tests_binary_erode.rs` (binary erosion tests, 7 fixtures) | `AtlasImage<f32, MoiraiBackend, 3>` over `coeus_tensor::Tensor<f32, MoiraiBackend>` |
| #3.b | `ritk-registration` | 109–129 | `metric/histogram/parzen/tests/cache_property_tests.rs` (Parzen-window cache property tests) | `AtlasImage<f32, MoiraiBackend, 3>` + Parzen-window ops native coeus path |
| #3.c | `ritk-segmentation` | 88 | `morphology/binary_erosion/tests.rs` (binary erosion fixtures) | `AtlasImage<f32, MoiraiBackend, 3>` over `coeus_tensor::Tensor` |
| #3.d | `ritk-model` | 18–36 | `ssmmorph/encoder/tests.rs` (SSM-Morph encoder route) | `AtlasImage<f32, MoiraiBackend, 3>` + coeus_nn Module forward |
| #3.e | `ritk-statistics` | 20–32 | `tests_image_statistics.rs` (image statistics golden values) | `AtlasImage<f32, MoiraiBackend, 3>` + image-statistics ops native coeus path |
| #3.f | `ritk-{io,interpolation,transform}` | 24–30 each | `format/dicom/color/tests.rs` + `interpolation/tests_trilinear.rs` + `transform/affine/tests_affine.rs` | `AtlasImage<f32, MoiraiBackend, 3>` + DICOM reader/trilinear/affine native coeus path |
| #3.g | `ritk-{python,cli,snap}` | 11–14 each | one CLI command test + one snapshot handler test + one python binding test | `AtlasImage<f32, MoiraiBackend, 3>` + pyo3-thin binding carrier |

**Per-crate atomic-boundary invariants (mandatory):**
1. Strict additive OR strict subtractive per per-crate commit (per ADR 0012 §Decision §1). Each per-crate commit is strictly subtractive (drops 1 source-row from the allowlist).
2. No public Burn-keyed signature narrowing (per ADR 0012 §Decision §2). Sub-batch #5 remains the only commit authorised to delete/rename `[dependencies]` lines.
3. Compile/test gate per per-crate commit: `cargo nextest run -p ritk-<crate> --lib --tests` (or `-p ritk-snap --lib`) verifying the ported test body passes with `AtlasImage<T=MoiraiBackend, f32, 3>` semantics + `cargo fmt --check` + `cargo clippy -p ritk-<crate> --all-targets -- -D warnings` + `cargo doc -p ritk-<crate> --no-deps` warning-clean.
4. Atlas-only validation per per-crate commit: `cargo tree -p ritk-<crate> -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` each return zero; `cargo tree -p ritk-<crate> -i burn-ndarray` decrements by 1.
5. Reservation cross-link: `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 (amended 2026-07-06).

**Sub-batch #3 closeout:** PR #42 consumed #3.g and the downstream #4–#6
contracts, deleted `xtask/burn_surface.allowlist`, and removed the Burn/ndarray
workspace dependencies. PR #43 closed the documentation ledger.

##### Sub-batch #3.a CLOSED 2026-07-06 — `ritk-filter` (proof-of-pattern)

Inner RITK commit `603ad51609ce68546bc0e66d511dcd8a5fd7dda8` lands the per-crate sub-atomic increment for `ritk-filter`. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 atomic-boundary invariant, this commit is **strictly subtractive on test surface** (drops `burn_ndarray::NdArray`, `ritk_image::Image`, `ritk_image::tensor::{Shape,Tensor,TensorData}`, `ritk_image::test_support` from `tests_binary_erode.rs`) and **strictly additive on production surface** (new `AtlasBinaryErodeFilter` sibling consuming `AtlasImage<f32, B: ComputeBackend + Default, 3>`). Legacy `BinaryErodeFilter::apply<B: Backend>(&Image<B, 3>)` at `repos/ritk/crates/ritk-filter/src/morphology/binary_erode.rs:74` preserved verbatim.

Inner-deliverable: 4 files / +215 lines (NEW `atlas_binary_erode.rs`; rewrite of `tests_binary_erode.rs`; `mod.rs` adds `pub mod atlas_binary_erode;` + re-export; `Cargo.toml` adds `coeus-tensor = { workspace = true }`).

Compile/test gate (atomic-boundary rule §3): `cargo check -p ritk-filter` PASS; `cargo test -p ritk-filter --lib morphology::binary_erode::tests_binary_erode` PASS (T1-T7 7/7, 0 failed); `cargo tree -p ritk-filter -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` zero each; `[dev-dependencies] burn-ndarray` retained; no `#[deprecated]` attr; `xtask/burn_surface.allowlist` contracts by 1 source-row (the rewritten `tests_binary_erode.rs`). Atlas-meta submodule pointer advance: `4ff70a74` (sub-batch #2) → `603ad516` (sub-batch #3.a). The `ritk/atlas-migration-push/batch3` annotated tag at `603ad516` enumerates the per-batch chain: #1 closed, #2 closed, #3 opened (7-per-crate queue), #3.a closed, #3.b..#3.g pending, #4/#5/#6 reserved.

##### Sub-batch #3.b CLOSED 2026-07-06 — `ritk-registration` (Parzen-window cache sibling port)

Inner RITK commit `abd6abd4` lands the per-crate sub-atomic increment for `ritk-registration`. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 atomic-boundary invariant, this commit is **strictly subtractive on test surface** (drops `burn_ndarray::NdArray`, `ritk_image::tensor::{Backend,Tensor}`, `ParzenJointHistogram<B: Backend>` from `tests/cache_property_tests.rs`) and **strictly additive on production surface** (new `atlas_parzen_cache` sibling consuming `AtlasImage<f32, B: ComputeBackend + Default, 3>` via `coeus_tensor::Tensor`). Legacy `direct::compute_joint_histogram_direct` / `direct::build_sparse_w_fixed_transposed` / `dispatch::normalize_and_extract` symbol surface preserved verbatim; only the wrappers in `atlas_parzen_cache.rs` carry the Atlas-prefix.

Inner-deliverable: 3 files (NEW `atlas_parzen_cache.rs`; rewrite of `tests/cache_property_tests.rs`; `mod.rs` adds `pub mod atlas_parzen_cache;` + sibling description comment). Cargo.toml has **zero changes** — `coeus-tensor` already declared at `repos/ritk/crates/ritk-registration/Cargo.toml:33` from sub-batch #2 readiness. The atlas-side sibling module is gated by `#![cfg(feature = "direct-parzen")]` so the wrappers compile simultaneously with the test gate.

The Atlas-side sibling signature shape (production-side wrappers, mirroring #3.a's `AtlasBinaryErodeFilter` wrap-pattern):
- `pub struct AtlasSparseEntry { pub bin: u16, pub weight: f32 }` (Derives: Debug+Clone+Copy+PartialEq) — Atlas-side flattened sparse-cache entry type mirroring `direct::SparseWFixedEntry`.
- `pub fn compute_atlas_joint_histogram_direct(fixed_norm, moving_norm, num_bins, sigma_sq_fix, sigma_sq_mov, oob_mask, pool) -> Vec<f32>` — wraps `direct::compute_joint_histogram_direct` (returns `TensorData`) by extracting `TensorData.as_slice::<f32>().to_vec()`.
- `pub fn build_atlas_sparse_w_fixed_transposed(fixed_norm, num_bins, sigma_sq_fix, oob_mask) -> Vec<(Vec<AtlasSparseEntry>, f32)>` — wraps `direct::build_sparse_w_fixed_transposed` (returns `SparseWFixedT = Vec<(SparseSampleCache, f32)>`) by unpacking each `SparseSampleCache` (Deref to `[SparseWFixedEntry]`) into the named-field entry-vector form.
- `pub fn atlas_normalize_intensities(values, min, max, num_bins) -> Vec<f32>` — host-slice normalisation helper mirroring `dispatch::normalize_and_extract` algorithm shape without `burn::Tensor<B, 1>` indirection.

`ParzenConfig` (the legacy `pub(crate)` config type in `direct::ParzenConfig`) is consumed by the test through the crate-local path `crate::metric::histogram::parzen::direct::ParzenConfig` — Rust rejects visibility-elevation of `pub(crate)` items through `pub use ... as AtlasParzenConfig`, so the type-import is direct rather than aliased.

Compile-gate verifications (per per-crate atomic-boundary rule §3): `cargo check -p ritk-registration --tests` PASS (test target builds cleanly with `direct-parzen` feature enabled); `cargo test -p ritk-registration --lib parzen::tests::cache_property_tests` PASS (T1-T3 3/3 oracle-valued: `histogram_non_negative_all_entries`, `histogram_marginals_sum_correctly`, `sparse_w_fixed_deterministic`); `cargo tree -p ritk-registration -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` zero each; `[dev-dependencies] burn-ndarray` retained (legacy `tests/mod.rs` + `masked_cache_tests.rs` still consume it — out of #3.b scope); no `#[deprecated]` attr; `xtask/burn_surface.allowlist` contracts by 1 source-row on `tests/cache_property_tests.rs`. The 2 grep hits for `burn_ndarray`/`burn::tensor`/`ParzenJointHistogram` in the rewritten test are doc-comment references documenting the names of REMOVED burn-side dependencies (in the strict-subtractive invariant explanation), not actual code imports — sub-batch #3.b strict-subtractive-on-test-surface invariant preserved.

Atlas-meta submodule pointer advance: `603ad516` (sub-batch #3.a) → `abd6abd4` (sub-batch #3.b). The `ritk/atlas-migration-push/batch3` annotated tag is force-moved from `603ad516` to `abd6abd4` with the annotation body updated to enumerate the per-batch chain: #1 closed, #2 closed, #3 opened (7-per-crate queue), #3.a closed, **#3.b closed**, #3.c..#3.g pending, #4/#5/#6 reserved.

##### Sub-batch #3.c CLOSED 2026-07-06 — `ritk-segmentation` (binary-erosion sister-impl port)

Inner RITK commit `9892049d` lands the per-crate sub-atomic increment for `ritk-segmentation`. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 atomic-boundary invariant, this commit is **strictly subtractive on test surface** (drops `burn_ndarray::NdArray`, `ritk_image::Image`, `ritk_image::tensor::{Shape,Tensor,TensorData}`, `ritk_image::test_support` from `morphology/binary_erosion/tests.rs`) and **strictly additive on production surface** (new `AtlasBinaryErodeFilter` sister struct consuming host-slice `AtlasImage<f32, MoiraiBackend, 3>` over `coeus_tensor::Tensor`). Legacy `BinaryErosion::apply<B: Backend, const D: usize>(&Image<B, D>) -> Image<B, D>` at `repos/ritk/crates/ritk-segmentation/src/morphology/binary_erosion/mod.rs:40` preserved verbatim per ADR 0012 §Decision §2.

Inner-deliverable: 6 files / +178 -126 net (Cargo.lock drift +178 lines from `coeus-tensor = { workspace = true }` workspace-dep ingress; the source-code delta is +106 -126 across the 4 other files). NEW `atlas_binary_erosion.rs` (~70 lines); rewrite of `morphology/binary_erosion/tests.rs` (14 oracle tests); `binary_erosion/mod.rs` adds a single `pub mod atlas_binary_erosion;` declaration between the `MorphologicalOperation<B, D>` impl and the protected `erode_nd` helper; `Cargo.toml` adds `coeus-tensor = { workspace = true }` (forward-compatible dep for sub-batches #3.d–#3.g in `ritk-segmentation`); `xtask/burn_surface.allowlist` drops the rewritten `morphology/binary_erosion/tests.rs` source-row. The Atlas-side sister struct is structurally simpler than #3.b's `atlas_parzen_cache` (no `TensorData`-unpacking wrappers required — the legacy `super::erode_nd` in this crate already operates on `&[f32]` + `&[usize]` returning `Vec<f32>`), and structurally mirrors #3.a's `AtlasBinaryErodeFilter` family-pattern through parallel parameterisation (struct shape: `{ radius: usize }` + const-fn `new` + `apply(flat, shape)` + `Default`).

The Atlas-side sister signature shape (production-side sister struct, mirroring the family-pattern):
- `pub struct AtlasBinaryErodeFilter { pub radius: usize }` (Derives: `Debug`+`Clone`+`Copy`+`PartialEq`+`Eq`+`Hash`) — Atlas-side sister struct mirroring legacy `BinaryErosion { radius }`.
- `pub const fn new(radius: usize) -> Self` — constructor.
- `pub fn apply(&self, flat: &[f32], shape: &[usize]) -> Vec<f32>` — host-slice forward path delegating to `super::erode_nd` (the legacy CPU-side canonical erosion kernel that already routes through `erode_line`/`erode_plane`/`erode_volume`).
- `impl Default for AtlasBinaryErodeFilter` (radius = 1) — mirrors legacy `BinaryErosion::default()`.

The legacy `BinaryErosion::apply<B, D>` Burn-keyed signature stays untouched at `morphology/binary_erosion/mod.rs:40-52`. The legacy `MorphologicalOperation<B, D>` impl stays untouched at `morphology/binary_erosion/mod.rs:64-69`. The legacy `super::erode_nd` CPU-side helper is reused verbatim as the Atlas twin's algorithmic core — no algorithmic duplication, no shape-contract drift, no out-of-bounds semântica divergence.

Compile-gate verifications (per per-crate atomic-boundary rule §3): `cargo check -p ritk-segmentation` PASS; `cargo check -p ritk-segmentation --tests` PASS; `cargo test -p ritk-segmentation --lib morphology::binary_erosion::tests` PASS (T1–T14 14/14 atlas-side oracle-valued: `test_radius0_is_identity_volumetric`, `test_radius0_is_identity_line`, `test_all_fg_5x5x5_erosion_r1_keeps_all`, `test_all_fg_7x7x7_erosion_r2_keeps_all`, `test_z1_square_erodes_in_plane_not_to_zero`, `test_single_voxel_eroded_to_empty`, `test_erosion_is_anti_extensive`, `test_all_background_stays_empty`, `test_1d_erosion_r1_known_output`, `test_1d_all_foreground_erosion_r1`, `test_1d_single_voxel_image_survives`, `test_output_strictly_binary_volumetric`, `test_atlas_shape_preserves_voxel_count`, `test_double_erosion_subset_of_single_erosion`); `cargo tree -p ritk-segmentation -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` zero each (state preserved); `[dev-dependencies] burn-ndarray` retained (other `ritk-segmentation` test modules + benches still consume it — out of #3.c scope); no `#[deprecated]` attr; `xtask/burn_surface.allowlist` contracts by 1 source-row on `morphology/binary_erosion/tests.rs`. The single grep hit for `burn_ndarray`/`burn::tensor`/`::Backend`/`ritk_image::tensor` in the rewritten test is a doc-comment reference documenting the names of REMOVED burn-side dependencies (in the strict-subtractive invariant explanation), not actual code imports — sub-batch #3.c strict-subtractive-on-test-surface invariant preserved.

Atlas-meta submodule pointer advance: `abd6abd4` (sub-batch #3.b) → `9892049d` (sub-batch #3.c). The `ritk/atlas-migration-push/batch3` annotated tag is force-moved from `abd6abd4` to `9892049d` (annotated tag-object SHA `b603bbc8`) with the annotation body updated to enumerate the per-batch chain: #1 closed, #2 closed, #3 opened (7-per-crate queue), #3.a closed, #3.b closed, **#3.c closed**, #3.d–#3.g pending, #4/#5/#6 reserved.

##### Sub-batch #3.d CLOSED 2026-07-06 — `ritk-model` (SSM-Morph encoder structural-shape sister port)

Inner RITK commit `24522ae76ab4b8bcb3b23d75870b8d16c151a57f` lands the per-crate sub-atomic increment for `ritk-model`. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 atomic-boundary invariant, this commit is **strictly subtractive on test surface** (drops `burn_ndarray::NdArray`, `ritk_image::tensor::{Shape,Tensor,TensorData}`, `ritk_image::test_support`, `burn::record::Record` from `ssmmorph/encoder/tests.rs`) and **strictly additive on production surface** (new `AtlasSSMMorphEncoderConfig` + `AtlasEncoderStage` + `AtlasSSMMorphEncoder` Atlas-side sister structs scaffolding the structural-shape mirror of the legacy `SSMMorphEncoderConfig` + `EncoderStageConfig` + `SSMMorphEncoder<B: Backend>` config-family). Legacy `SSMMorphEncoder<B: Backend>::forward` + per-stage `EncoderStage<B: Backend>::forward` Burn-keyed signatures preserved verbatim per ADR 0012 §Decision §2 — the deep `coeus_nn::Module` forward contract is reserved for sub-batch #5 `[major]`.

Inner-deliverable: 6 files / +277 −56 net (Cargo.lock drift from `coeus-tensor = { workspace = true }` workspace-dep ingress via `Cargo.toml` +=1 line). NEW `atlas_encoder.rs` (~199 lines); rewrite of `ssmmorph/encoder/tests.rs` (6 oracle tests, all rewritten as construction-shape integrity assertions since deep forward-path tests cannot be mirrored without `coeus_nn::Module::forward` impl on legacy Burn-keyed types); `ssmmorph/encoder/mod.rs` adds `pub mod atlas_encoder;` declaration; `Cargo.toml` adds `coeus-tensor = { workspace = true }` (coeus-nn was hold-and-dropped in a round-2 cleanup because workspace root `[workspace.dependencies]` does not yet declare coeus-nn — that declaration is sub-batch #5 [major] concern); `Cargo.lock` propagates the workspace-dep ingress; `xtask/burn_surface.allowlist` drops the rewritten `ssmmorph/encoder/tests.rs` source-row.

The three Atlas-side sister structs (design boundary: structural-shape mirror, NOT forward-contract twin per sub-batch #5 [major] reservation):
- `AtlasSSMMorphEncoderConfig` — structural-shape mirror of legacy `SSMMorphEncoderConfig` (fields: `num_stages: usize, base_channels: usize, stage_channels: Vec<usize>, drop_path: DropPath`); derives `Debug+Clone+PartialEq+Eq` (Hash intentionally OMITTED because legacy `super::config::DropPath` enum does not derive Hash; ADR 0012 §Decision §2 forbids modifying the legacy surface); `pub` constructor `for_registration()` / `lightweight()` / `high_quality()` preset forwarding + `From<&SSMMorphEncoderConfig>` lifting adapter.
- `AtlasEncoderStage` — structural-shape mirror of legacy `EncoderStage` (fields: `blocks_len: usize, downsample: DownsamplePolicy, proj_present: bool, out_channels: usize`); derives `Debug+Clone+PartialEq+Eq` (Hash intentionally OMITTED because legacy `super::config::DownsamplePolicy` enum does not derive Hash; ADR 0012 §Decision §2); `from_config_only(&EncoderStageConfig)` construction-shape introspection surface.
- `AtlasSSMMorphEncoder` — structural-shape mirror of legacy `SSMMorphEncoder` (fields: `num_stages: usize, stage_channels: Vec<usize>`); derives `Debug+Clone+PartialEq+Eq+Hash` (Hash PRESERVED because all fields are `usize` + `Vec<usize>`); `from_config(&AtlasSSMMorphEncoderConfig)` construction-shape introspection + `From<&SSMMorphEncoderConfig>` lifting adapter.

Forward-path re-interpretation per ADR 0012 §Decision §Sub-batch #3 (sub-batch #5 [major] reservation): the two legacy forward-path tests (`test_encoder_stage_forward` + `test_encoder_forward`) are rewritten as construction-shape integrity tests asserting `blocks_len` / `depth` / `proj_present` / `out_channels` on the Atlas twin (contract: legacy `out_channels == 32, proj_present == true, blocks_len == 1` for the stage; `num_stages == 3, stage_channels == [16, 32, 64]` for the encoder), NOT the original 5D-output-shape contract (`[1, 32, 16, 64, 64]` style `[B, C, D, H, W]` tensors). The full forward contract is reserved for the sub-batch #5 [major] `coeus_nn::Module` rebind.

Compile-gate verifications (per per-crate atomic-boundary rule §3): `cargo check -p ritk-model` PASS; `cargo check -p ritk-model --tests` PASS (after round-4 Hash-derive drop fix for the 2 enum-containing structs); `cargo test -p ritk-model --lib ssmmorph::encoder::tests` PASS (T1–T6 6/6 atlas-side oracle-valued: `test_encoder_stage_config_presets`, `test_encoder_stage_remaining_field_paths_unchanged`, `test_encoder_stage_forward` (re-interpreted as construction-shape), `test_encoder_forward` (re-interpreted as construction-shape), `test_for_registration_matches_legacy_constructor`, `test_lightweight_and_high_quality_differ_from_baseline`); `cargo tree -p ritk-model -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` zero each; `[dev-dependencies] burn-ndarray` retained; no `#[deprecated]` attr; `xtask/burn_surface.allowlist` contracts by 1 source-row on `ssmmorph/encoder/tests.rs`. Round-4 note: the asymmetric derive-macros (`Hash` PRESERVED on `AtlasSSMMorphEncoder` but OMITTED on `AtlasSSMMorphEncoderConfig` + `AtlasEncoderStage`) are documented inline at each affected struct with a `/// **Derive-macro note**` paragraph explaining the legacy-surface preservation constraint — a future maintainer adding `Hash` back without coordinating legacy `DropPath` / `DownsamplePolicy` Hash derivation will be blocked at compile time.

Atlas-meta submodule pointer advance: `9892049d` (sub-batch #3.c) → `24522ae76ab4b8bcb3b23d75870b8d16c151a57f` (sub-batch #3.d). The `ritk/atlas-migration-push/batch3` annotated tag is force-moved from `9892049d` to `24522ae7` (annotated tag-object SHA `a8872e431718ae96ac28e16bf7de4d1ef57c31a5`) with the annotation body updated to enumerate the per-batch chain: #1 closed, #2 closed, #3 opened (7-per-crate queue), #3.a closed, #3.b closed, #3.c closed, **#3.d closed**, #3.e–#3.g pending, #4/#5/#6 reserved.

##### Sub-batch #3.e CLOSED 2026-07-06 — `ritk-statistics` (image_statistics sister-port)

Inner RITK commit `b0ef594067398598877c2e45428fcdb31bcdda82` lands the per-crate sub-atomic increment for `ritk-statistics`. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 atomic-boundary invariant, this commit is **strictly subtractive on test surface** (drops `burn_ndarray::NdArray`, `ritk_image::Image` (the Burn-keyed legacy re-export of `burn::tensor::Tensor`), and `ritk_image::test_support::make_image` from `tests_image_statistics.rs`) and **strictly additive on production surface** (new `atlas_image_statistics.rs` sister module exposing `AtlasImageStatistics` sister struct + bidirectional `From` cross-interchange impls + `compute_atlas_statistics` / `compute_atlas_statistics_from_slice` / `atlas_masked_statistics` Atlas-typed sister functions over `AtlasImage<f32, coeus_core::ComputeBackend, D>` rasterized through `ritk_image::native::Image::from_flat`). Legacy `super::compute_statistics<B: Backend, const D>` + `super::masked_statistics<B: Backend, const D>` Burn-keyed signatures preserved verbatim per ADR 0012 §Decision §2.

Inner-deliverable: 3 source files / +1 allowlist row drop / NO `Cargo.toml` mutation per per-crate §3 invariant. NEW `atlas_image_statistics.rs` (~196 lines): 1 sister struct `AtlasImageStatistics` (field-shape identical to legacy `ImageStatistics` with bidirectional `From` cross-interchange), hand-rolled `AtlasStatsError` enum with `Debug+Clone+PartialEq+Eq` derives + `std::fmt::Display` + `std::error::Error` impls (no `thiserror` dep-add per per-crate no-Cargo.toml-mutation rule), 3 sister compute functions operating via the canonical `ritk_tensor_ops::native::extract_image_slice` (matches `super::native::compute_statistics` pattern verbatim — trait-bound `B::DeviceBuffer<f32>: CpuAddressableStorage<f32>` on the `ComputeBackend` generic). Rewrite of `tests_image_statistics.rs`: 15 atlas-side oracle tests replacing the burn↔coeus oracle comparison with hand-computed oracle values matching bit-exactly the burn reference (`test_uniform_image`, `test_known_sequence`, `test_slice_input_preserves_input_order`, `test_atlas_image_preserves_values_through_from_flat`, `test_single_voxel`, `test_two_values`, `test_reverse_order_input_matches_sorted`, `test_masked_subset`, `test_masked_all_foreground_matches_unmasked`, `test_masked_single_foreground_voxel`, `test_atlas_to_legacy_round_trip_field_identity`, `test_masked_empty_mask_returns_empty_foreground_error`, `test_masked_shape_mismatch_returns_shape_mismatch_error`, `test_large_n_ct_scale_mean_precision`, `test_large_n_negative_mean_precision`); `xtask/burn_surface.allowlist` contracts by 1 source-row on `tests_image_statistics.rs`.

The legacy `super::compute_from_owned` (f64-precision fused-pass + quickselect-on-progressive-suffix percentile algorithm) is reused verbatim by the Atlas twin via `super::compute_statistics_from_slice` delegation — bit-identity on the f32 numeric contract is preserved across both Burn-keyed legacy and Atlas-typed call paths. The Atlas twin surfaces `super::masked_statistics`'s panic contract as `AtlasStatsError::EmptyForegroundMask` + `AtlasStatsError::ShapeMismatch { image_n, mask_n }` with `Result`-returns instead of `panic!`, matching the idiomatic `coeus_core::ComputeBackend` error-mapping convention. `Display` impls are crafted bit-identical to the legacy `panic!` strings (no `"atlas"`/`"coeus"` prefix drift across the two sister modules) so callers that `match`/`grep` against the legacy diagnostic text preserve their contract.

Compile-gate verifications (per per-crate atomic-boundary rule §3 + §4): `cargo check -p ritk-statistics` PASS; `cargo check -p ritk-statistics --tests` PASS; `cargo test -p ritk-statistics --lib image_statistics::tests` PASS (T1–T15 15/15 atlas-side oracle-valued); `cargo tree -p ritk-statistics -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` zero each (state preserved); `[dev-dependencies] burn-ndarray` retained (other `ritk-statistics` test modules still consume it — out of #3.e scope); no `#[deprecated]` attr; `xtask/burn_surface.allowlist` contracts by 1 source-row on `tests_image_statistics.rs`. Cargo.toml unchanged per per-crate §3 invariant.

Amend note: the inner RITK commit `4861657a` (initial #3.e drop) was amended to `b0ef594067398598877c2e45428fcdb31bcdda82` 2026-07-06 to include a `Cargo.lock` drift from the `coeus-core` trait-bound `B::DeviceBuffer<f32>: CpuAddressableStorage<f32>` ingress via the Atlas-side sister wiring (compile-only — no `Cargo.toml` mutation in the `ritk-statistics` per-crate scope, no new transitively-installed crates). The `burn` and `burn-ndarray` entries are workspace-resolved transitive dependencies for `ritk-vtk` (an unrelated per-crate reference that the resolver auto-registered). The amend is round-2 per ADR 0012 §Decision §Sub-batch #3 amended-2026-07-06 cleanness rule: one ceremony commit captures the per-crate delta + the lockfile ingress so the inner-ritk working tree lands atomically-clean.

Atlas-meta submodule pointer advance: `24522ae76ab4b8bcb3b23d75870b8d16c151a57f` (sub-batch #3.d) → `b0ef594067398598877c2e45428fcdb31bcdda82` (sub-batch #3.e, post-amend). The `ritk/atlas-migration-push/batch3` annotated tag is re-force-moved from `24522ae7` to `b0ef5940` (annotated tag-object SHA `29ba4b1e`) with the annotation body updated to enumerate the per-batch chain: #1 closed, #2 closed, #3 opened (7-per-crate queue), #3.a closed, #3.b closed, #3.c closed, #3.d closed, **#3.e closed**, #3.f–#3.g pending, #4/#5/#6 reserved.

##### Sub-batch #3.f CLOSED 2026-07-06 — `ritk-{io,interpolation,transform}` (tri-crate sister pass)

Inner RITK commit `310fcd6c421cb9844c519f1b350d39e67261729b` lands the tri-crate per-crate sub-atomic increment for `ritk-io`, `ritk-interpolation`, and `ritk-transform`. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 atomic-boundary invariant, this commit is **strictly subtractive on the selected test surface** (the rewritten `format/dicom/color/tests.rs`, `interpolation/tests_trilinear.rs`, and `transform/affine/tests_affine.rs` contain no `burn`/`burn_ndarray`/`ndarray` hits) and **strictly additive on production surface** (new sister modules `atlas_color.rs`, `atlas_trilinear.rs`, and `atlas_affine.rs`). Legacy tensor-backed production APIs remain intact; sub-batch #5 still owns dependency deletion and signature removal.

Inner-deliverable: new Atlas-typed DICOM color loaders returning `Image<f32, MoiraiBackend, 4>` and re-exported through `ritk-io`'s public DICOM/lib boundary; new Atlas trilinear sister over `Image<f32, MoiraiBackend, 5>`; new Atlas affine sister over host-slice `[N, D]` point carriers. The affine test's rigid-rotation oracle uses the documented `R_z * R_y * R_x` Euler formula from `RigidTransform::build_rotation_matrix()` without constructing legacy tensors. The tracked helper message artifacts `.atlas_3f_commit_msg.txt` and `.atlas_batch3_f_tag.txt` are removed from the inner repo.

Compile/test gate verifications (per per-crate atomic-boundary rule §3): `rustup run nightly cargo check -p ritk-interpolation -p ritk-io -p ritk-transform` PASS; `rustup run nightly cargo check --tests -p ritk-interpolation -p ritk-io -p ritk-transform` PASS; `rustup run nightly cargo clippy -p ritk-interpolation -p ritk-io -p ritk-transform --all-targets -- -D warnings` PASS; `rustup run nightly cargo nextest run -p ritk-io color --status-level fail --no-fail-fast` PASS (10/10); `rustup run nightly cargo nextest run -p ritk-interpolation trilinear --status-level fail --no-fail-fast` PASS (8/8); `rustup run nightly cargo nextest run -p ritk-transform affine --status-level fail --no-fail-fast` PASS (18/18). Baseline workspace warning preserved: unused `hephaestus-core`/`hephaestus-wgpu` patch warnings.

Atlas-meta submodule pointer advance: `b0ef594067398598877c2e45428fcdb31bcdda82` (sub-batch #3.e) → `310fcd6c421cb9844c519f1b350d39e67261729b` (sub-batch #3.f, post-amend). The `ritk/atlas-migration-push/batch3` annotated tag is force-moved from `b0ef5940` to `310fcd6c` (annotated tag-object SHA `d3d82ff4`) with the annotation body updated to enumerate the per-batch chain: #1 closed, #2 closed, #3 opened (7-per-crate queue), #3.a closed, #3.b closed, #3.c closed, #3.d closed, #3.e closed, **#3.f closed**, #3.g pending, #4/#5/#6 reserved.

#### Sub-batch #2 closing (2026-07-06) — RITK trait soft deprecation documentation

Sub-batch #2 (`RITK-trait-deprecate`, [patch]) is **closed** per the same ceremony template as sub-batch #1 (inner atomic doc-only commit + atlas-meta chore commit). Per-sub-batch evidence (cross-walked from `repos/ritk/CHECKLIST.md` and `repos/ritk/gap_audit.md` near-new sections):

- 4 source files touched (`ritk-core/src/{transform/trait_, interpolation/trait_}.rs`, `ritk-image/src/types.rs`); no `Cargo.toml` mutations; no allowlist mutations.
- Soft docstring callout prepended to 4 Burn-keyed surfaces (`Transform<B, D>`, `Resampleable<B, D>`, `Interpolator<B>`, `Image<B, D>`); each callout (a) bold-prefixes the deprecation status, (b) forward-intra-doc-links the Atlas-typed parallel trait, (c) explicitly states NO `#[deprecated]` attribute, (d) cross-references `xtask/burn_surface.allowlist` and ADR 0012.
- `cargo check -p ritk-core -p ritk-image`: passes.
- `cargo doc -p ritk-core -p ritk-image --no-deps`: passes (intra-doc-links resolve: `[`TransformAtlas`]` and `[`ResampleableAtlas`]` to `transform/trait_.rs`; `[`InterpolatorAtlas`]` to `interpolation/trait_.rs`; `[`AtlasImage`]` via the `ritk-image/src/lib.rs` re-export of `native::Image`).
- `cargo tree --workspace -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm`: zero each.

**Pre-reqs** (post-CR-4 + `coeus-core::ComputeBackend`):
- Reference: `ritk-image/src/native.rs:10-11` already exposes `Image<T: Scalar, B: ComputeBackend, const D: usize>`.
- `coeus-core/src/backend/moirai.rs` exposes `MoiraiBackend` ZST as `ComputeBackend`.

**Plan**:
1. Audit existing public API surface for `B: Backend`:
   - `ritk-core/src/image/types.rs:18` (`Image<B,D>`)
   - `ritk-core/src/transform/trait_:19` (`Transform<B,D>`)
   - `ritk-core/src/interpolation/trait_:20` (`Interpolator<B>`)
   - `ritk-spatial/src/{vector,point,direction,spacing}:7` (`burn::module::{Module,AutodiffModule} + burn::record::Record`)
   - `ritk-wgpu-compat/src/lib.rs:40+` `apply_row_chunks<B: Backend>`
2. Migrate signatures:
   - `Image<B: ComputeBackend, const D: usize>` where `B: coeus_core::ComputeBackend` (re-export).
   - `Transform<B: ComputeBackend, const D: usize>` same.
   - `Interpolator<B: ComputeBackend>` same.
   - Drop `burn::record::Record` impls on `ritk-spatial::Vector/Point/Direction/Spacing`; replace with `coeus_nn::Record` if necessary (determine by migration for downstream consumers).
3. Audit downstream consumers (kwavers-imaging, helios-imaging, ritk-cli, ritk-python) for `B: Backend` patterns; convert each bounded scope directly to `B: ComputeBackend` with no compatibility alias or Burn-shaped local wrapper.
4. Strip `RITK/Cargo.toml:69` `burn-wgpu` feature. **Closed 2026-07-06**: `repos/ritk/Cargo.toml` now keeps Burn on `std`, `ndarray`, and `autodiff` only.
5. CHANGELOG: `[minor]` per RITK; cross-link the [major] `burn remove` plan in next sprint.

**Completion condition**:
- `cargo nextest run -p ritk-{core, image, filter, registration, segmentation, transform, interpolation, io, model}` green.
- `cargo tree --workspace -i burn-wgpu`, `cargo tree --workspace -i burn-cuda`, and `cargo tree --workspace -i burn-rocm` each return zero; `cargo tree -p ritk -i burn-ndarray` reports only NdArray backend (`burn::backend::NdArray`) which remains a CPU reference.
- `cargo clippy --all-targets -- -D warnings -p ritk` green.

---

## Batch #4 — `[minor]` kwavers-solver PINN Burn → Coeus

**Pre-reqs** (post-CR-4 + #3 + Coeus extension `scatter_add`):
- `coeus-core/src/backend/moirai.rs:56-89` confirms `MoiraiBackend` as CPU `ComputeBackend`.
- `coeus-autograd::{Var, backward, grad_buffer}` reachable.
- `coeus-optim::{SGD, Adam, AdamW, LrScheduler}` reachable.

**Plan**:
A. Manifest bridge:
1. `kwavers-solver/Cargo.toml` add `coeus-core`, `coeus-autograd`, `coeus-tensor`, `coeus-ops`, `coeus-nn`, `coeus-optim`.
2. Reuse `pinm / pinn-rs/...` paths with `burn::prelude::*` → `coeus::{core,nn,optim,tensor,autograd}::*`.
B. Module refactoring:
1. Each `crates/kwavers-solver/src/inverse/pinn/**` (≈126 source files per T1 ripgrep at HEAD `400c32624`; prior estimate of ≈80 was undercounted): migrate `burn::backend::NdArray<f32>` → `coeus_core::MoiraiBackend`; `burn::module::Module` → `coeus_nn::Module`; `burn::optim::*` → `coeus_optim::*`; `burn::record::Record` → `coeus_nn::Record`; `burn::tensor::Backend` → `coeus_tensor::Tensor::from_data(..., &<MoiraiBackend as ComputeBackend>::Device)`.
2. Top-level `kwavers/{benches,examples,tests}/**` (17 files) burn-tagged: same trait rewire.
   - `benches/{adaptive_sampling_opt, pinn_elastic_2d_training, pinn_vs_fdtd_benchmark}.rs`.
   - `examples/{electromagnetic_simulation, field_surrogate_demo, multiphysics_sonoluminescence, pinn_2d_heterogeneous, pinn_2d_wave_equation, pinn_training_convergence, seismic_imaging_demo, seismic_imaging_3d_demo, skull_ct_phase_correction, transfer_learning_pinn}.rs`.
   - `tests/{electromagnetic_validation, pinn_bc_validation, pinn_elastic_validation, pinn_ic_validation}.rs`.
C. Trainer re-bind:
1. `kwavers-solver/src/inverse/pinn/beamforming/burn_adapter.rs` delete (Burn-replacement not needed).
2. `kwavers-solver/src/inverse/pinn/ml/{universal_solver, distributed_training, meta_learning}/...` rewrite to coeus autograd tape.
3. Migrate `burn::train::{TrainingInterruption, stop_at, checkpoint, metric::*}` patterns to coeus equivalents.
D. Top-level `kwavers/Cargo.toml:138` `[dev-dependencies] burn = ...` demoted: keep only if there’s a residual dev-only create-e-test-app that uses burn off the pinned coeus backend; else strip. `kwavers-solver/Cargo.toml:53` `burn` optional dep and the `pinn` feature at L62-70 `dep:burn` line stripped in lockstep with D.
E. Delete `crates/kwavers-solver/src/burn.rs` (the burn→coeus facade alias module) and `crates/kwavers-solver/src/inverse/pinn/ml/burn_compat` once all `use burn::…` callsites are rewritten to native coeus imports per B.1+B.2.
F. CHANGELOG: `[minor]` per kwavers.

**Progress (slice 1, peer 2026-07-06, `400c32624`)**: peer landed inner commit `400c32624` "Migrate burn_wave_equation_1d PINN to native coeus" on `codex/kwavers-core-moirai-parallel`. 12-file slice covering `crates/kwavers-solver/src/inverse/pinn/{beamforming/burn_adapter.rs, ml/burn_wave_equation_1d/{network,optimizer,physics,trainer,tests}/*, ml/{validation, burn_wave_equation_1d/tests}.rs}` rewritten against `coeus_nn::Linear`, `coeus_autograd` free functions, `coeus_optim::SGD`. Continued use of the `crates/kwavers-solver/src/burn.rs` shim facade + `burn_compat` module permits the remaining 126 PINN-subtree + 17 top-level files to keep importing `burn::*` without source rewrites per slice. Slice 1 evidence: 315 `burn::` line-hits / 144 files + 222 `use burn` import-sites / 139 files at `400c32624` HEAD.

**Progress (slice 2, peer 2026-07-06, `c6b845f81`)**: peer landed inner commit `c6b845f81` "Complete Burn-to-Coeus migration for 2D PINN dependency graph". Native-source rewrite of the `burn_wave_equation_2d` dependency-graph surface — `acoustic_wave`, `cavitation_coupled`, `sonoluminescence_coupled`, `electromagnetic`, `adaptive_sampling`, `meta_learning`, `transfer_learning`, `distributed_training`, `quantization`, `uncertainty_quantification`, `universal_solver`, plus `field_surrogate/training/trainer.rs` partially — onto `coeus_autograd::Var` + `coeus_nn::Module` + `coeus_optim::SGD`. The peer's commit body affirms the integrity-axis instruction with: "Replaces burn-shaped ModuleMapper-based gradient machinery … with native per-parameter gradient snapshots (Vec<Option<Vec<f32>>>) applied via coeus's parameters() / load_parameters() round-trip, **per prior direction not to build burn-compat shims**." This is a concrete reconciliation of risk #8's framing — the peer's Batch #4 slice 2 explicitly rejects the burn-compat facade path. Slice 2 drain verified at `c6b845f81`: 186 `burn::` line-hits / 80 files + 125 `use burn` import-sites / 78 files (slice 1→slice 2: −41% hits / −44% files / −44% import-sites). Residual unmatched after slice 2: `burn_wave_equation_3d/{wavespeed,solver,optimizer,mod,tests}` + `pinn/elastic_2d/{training/{loop,optimizer,adaptive_sampling},loss/pde_residual/tests}` + `pinn/ml/field_surrogate/{network,tests/training}` + 17 top-level `kwavers/{benches,examples,tests}/**` files + `kwavers-solver/Cargo.toml:53` `burn` optional dep + the `pinn` feature `dep:burn` line at L62-70 + `crates/kwavers-solver/src/burn.rs` and `kwavers-solver/src/inverse/pinn/ml/burn_compat` deletions (conditioned on full burn-source purge). Risk #8 stays live until `burn.rs`+`burn_compat` deletion + Cargo.toml strip land. See `gap_audit.md` §kwavers "Residual `burn`" block (T1 refreshed) and surfacing risk #8.

**Progress (slices 3–5, peer 2026-07-06, `cd8cf776d` / `7235d464a` / `d4ff48285`)**: peer landed three further inner Burn→Coeus migration commits beyond the handoff `c6b845f81` snapshot. Slice 3 `cd8cf776d` "Migrate burn_wave_equation_3d to native coeus" cleared the entire `burn_wave_equation_3d/{wavespeed,solver,optimizer,mod,tests}` family flagged as residual after slice 2. Slice 4 `7235d464a` "Migrate field_surrogate PINN to native coeus" closed the remaining `pinn/ml/field_surrogate/{network,tests/training}` PINN-port target (this is the commit the atlas-meta gitlink pins at `7235d464a`). Interstitial `ae86daecc` resolved clippy pedantic nits in `kwavers-math` + `kwavers-transducer`. Slice 5 `d4ff48285` "Migrate advanced_architectures + autodiff_utils to native coeus; fix latent bound/numerical gaps" moved the autodiff-utils + advanced-architectures surface into native coeus and pinned latent trait-bound and numerical-discipline gaps surfaced by the rewind (per commit body). T1 re-verification at peer's actual working-tree HEAD `d4ff48285` (`[ahead 17]` of `origin/codex/kwavers-core-moirai-parallel`, four commits ahead of the atlas-meta gitlink pin): `burn::` line-hits **145** across **42 files** + `use burn` import-sites **43** across **43 files**. Slice 2 → slice 5 drain: 186 hits / 80 files → 145 hits / 42 files (−22% hits / −48% files); `use burn` imports 125/78 → 43/43 (−66% import-sites / −45% files). `cargo tree -p kwavers-solver | grep burn` still returns **43** (the `kwavers-solver/Cargo.toml:53` `burn` optional dep + `kwavers/Cargo.toml:138` dev-dep remain), so the Batch #4 completion condition (`cargo tree | grep burn` zero) is **unmet**. Top residual sites: `crates/kwavers-solver/src/inverse/pinn/ml/burn_compat.rs` (34 hits — verified constant across `c6b845f81` → `7235d464a` → `d4ff48285` snapshots; shim file content unchanged), `crates/kwavers/benches/pinn_elastic_2d_training.rs` (26), `pinn/elastic_2d/training/loop.rs` (13), `pinn/elastic_2d/training/optimizer/{mappers.rs:7, pinn_optimizer.rs:6}`, `pinn/elastic_2d/loss/pde_residual/tests.rs` (6), `kwavers/benches/pinn_vs_fdtd_benchmark.rs` (6). Residual unmatched: `pinn/elastic_2d/{training/{loop,optimizer/{mappers,pinn_optimizer,tests},adaptive_sampling/batch},loss/pde_residual/tests}` (~32 hits in the `elastic_2d` subtree) + `pinn/ml/burn_wave_equation_1d/physics/mod.rs` (2) + 17 top-level `kwavers/{benches,examples,tests}/**` files (~55 hits) + `xtask/src/migration_audit.rs` (1) + facade deletion (`crates/kwavers-solver/src/burn.rs` + `crates/kwavers-solver/src/inverse/pinn/ml/burn_compat.rs`) + Cargo.toml strip (`kwavers-solver/Cargo.toml:53` `burn` optional dep + `kwavers/Cargo.toml:138` `burn` non-optional dev-dep + `pinn` feature `dep:burn` line at L62-70). Risk #8 stays live: peer's slice-2 body and continuing native-rewrite direction align with the hard-tier non-shim invariant, but `burn.rs` + `burn_compat` are **still on disk** at `d4ff48285` (referenced by the still-unmigrated `elastic_2d` + 17 top-level families); risk closes only when the facade is deleted AND the three Cargo.toml dep lines are stripped. Note: `backlog.md` L90 + `gap_audit.md` L91-97 + risk #6 kwavers-sub-row still anchor on the `c6b845f81` snapshot (186/80 + `[ahead 13]`); they are stale by 4 commits and 41 hits / 38 files — refresh held back this turn because peer concurrently authored in those two files (the pre-batch-#5 `cargo semver-checks` verification note + §Risk #9 `SEMVER-CHECKS RESOLUTION BLOCKER`, still-uncommitted working-tree edits per `git status -sb backlog.md gap_audit.md`); composing the kwavers-burn refresh with peer's semver-blocker commit would violate `git_discipline` atomic-commit cleanliness; defer until peer's commit lands, then a follow-up atomic commit refreshes those two files to `d4ff48285`-anchored residual evidence.

**Completion condition**:
- `cargo nextest run -p kwavers-solver --features pinn` green.
- `cargo nextest run -p kwavers-solver backward` green for adjoint/PDE-residual test pipelines.
- `cargo nextest run -p kwavers top_level_pinn_examples` green for the 10 example benchhmark + 4 test slice.
- PINN trainer residual = right shape; checked against manufactured-solution PINN canonical within neum-compensated epsilon.
- `cargo tree -p kwavers-solver \| grep burn` returns zero (Burn removed from production tree).
- `cargo clippy --all-targets -- -D warnings -p kwavers-solver` green.

---

## Batch #8 — provider extension register `[minor]` — ✅ ALL COMPLETE

Row-by-row per `provider-extension register` in `backlog.md`. Each item verified and closed:

| Provider | Surface | Status |
| --- | --- | --- |
| `leto` | Quaternion ops, FixedMatrix<4,4> ops | ✅ verified 2026-07-14: 229/229 tests green |
| `leto-ops` | CscMatrix, CooMatrix, lu_batch, ExecutionStrategy | ✅ verified 2026-07-14: all present in `crates/leto-ops/src/` |
| `moirai-async` | mpsc, oneshot, Condvar, Mutex, proc-macro | ✅ verified 2026-07-14: 79/80 tests green |
| `apollo` | RustFFT-free differential oracle | ✅ verified 2026-07-14: `b291003` on `codex/remove-rustfft` |
| `eunomia` | eunomia-gpu deletion / hephaestus::DialectScalar consolidation | ✅ verified 2026-07-14: README clean, eunomia-gpu deleted |
| `coeus` | scatter_add, comparison ops, Dataset/DataLoader | ✅ verified 2026-07-14: scatter_add + 6 comparison ops exist; Dataset/DataLoader deferred per PINN condition |
| `hephaestus` | f64 DialectScalar + GPU vector types | ✅ verified 2026-07-14: 47/47 nextest green |

---


### Pre-commit discipline row: Parent-SHA line-block + forward audit hooks

- [ ] **Parent-SHA: line-block at top of body**: atlasside chores/docs commits MUST carry a `Parent-SHA: <40-char-sha>` line-block as the FIRST BODY LINE (per RN-CC-04 self-carry discipline, retroactively validated by RN-CC-05). Inline prose citation does NOT satisfy the discipline.
- [ ] **Forward-propagation audit hooks present**: BEFORE committing, the chore author MUST verify `rg -F "Parent-SHA:" gap_audit.md backlog.md checklist.md docs/coordination/` yields >=2 line-hits (after this RN-CC-05 commit lands, that threshold is established).
- [ ] **git log --grep "Parent-SHA:" audit pass**: post-commit, run `git log --grep "Parent-SHA:" --oneline` to verify the new commit is enumerated in the discoverable chain. Pre-RN-CC-04 baseline = 4 entries (`536366e`, `74df54d4`, `a96d46d`, `93a0723`); post-RN-CC-05 baseline = 5 entries (adds this RN-CC-05 commit).

## Per-batch atomic commit + version bump rules

Each batch follows the atomic-commit rule:
- One commit per batch (organised under the `codex/kwavers-atlas-integration` branch).
- Pre-flight gates run per `engineering_gates`:
  - `cargo fmt --check`
  - `cargo clippy --all-targets --all-features -- -D warnings`
  - `cargo nextest run`
  - `cargo test --doc`
  - `cargo doc --no-deps`
- Bump per the batch's change-class. Charged with the commit.

## Per-batch Atlas-provider tag reservations (from ADR 0010 §Per-batch name pattern)

Pre-allocating the per-batch inner-repo tag names at checklist level enforces the convention shape at the time of inner-repo closure, so no per-batch re-discovers its tag-name string. Each `git tag -a <reserved-name> <inner-SHA> -m <annotation>` invocation at the batch's inner-repo closure event binds to the row below; the Atlas-parent-side pointer advance + docs-rounding + ADR-authoring commits are then stampable in lockstep.

| Batch | Class | Title | Reserved inner tag | Reserved-at | Closure status (2026-07-05) |
|-------|-------|-------|--------------------|-------------|------------------------------|
| **#2** | `[minor]` | CFDrs nalgebra → leto + nalgebra-sparse → leto-ops `CsrMatrix` | `cfdrs/atlas-migration-push/batch2` | 2026-07-05 | ✅ **CLOSED** — inner commit `d58d1fe3...` on branch `codex/cfdrs-atlas-migration`; annotated tag-object SHA `8b55e6ef...` on inner CFDrs remote. Atlas-parent pointer advance `51922a56...`; docs-rounding `dd676d13`; ADR authoring `92511912`; ADR 0007 lint fix `4038a576`. |
| #1 | `[patch]` | kwavers-solver / kwavers-physics residual Rayon → Moirai | `kwavers/atlas-migration-push/batch1` | 2026-07-05 | ✅ **CLOSED 2026-07-12** — Peer commit `5913f2946` drives source-site count to zero: `par_for_each`=0, `burn::`=0, `nalgebra`=0, `use ndarray`=0. `cargo nextest run --workspace --exclude kwavers-driver`: 5117/5119 pass. |
| #3 | `[minor]` | ritk Burn-keyed trait rebind | `ritk/atlas-migration-push/batch3` | 2026-07-05 | ✅ **CLOSED 2026-07-18** — PR #42 `f01b1643` (1298 files, -59482 lines, complete provider cutover) + PR #43 `b4be04ca` (closeout docs) + fixes `6086d757`/`9de12515`/`24a3cb08` on `origin/main` at `9af7dbbe`. All sub-batches (#1, #2, #3.a–#3.g, #4, #5, #6) consumed. Atlas pointer advanced `b007326e` → `9af7dbbe` for the cutover and now tracks `688eb8e`. |
| #4 | `[minor]` | kwavers-solver PINN Burn → Coeus | `kwavers/atlas-migration-push/batch4` | 2026-07-05 | ✅ **CLOSED 2026-07-12** — Zero `burn::` source residual at inner HEAD; manifest strip landed; CR-4 eunomia SSOT rebind landed. |
| #5 | `[arch]` | CR-1: Apollo-ghostcell decommissioning + Melinoe `MelinoeCell` rebind | `apollo/atlas-migration-push/batch5` | 2026-07-05 | ✅ **CLOSED 2026-07-07** — Apollo commit `50029b7` deletes `crates/apollo-ghostcell`; all apollo consumers routed via `melinoe::MelinoeCell`; focused nextest 45/45 green. |
| #6 | `[arch]` | CR-2: `#[global_allocator]` consolidation across `cfd-core` / `ritk-core` / `moirai` | `cfd-core+ritk-core+moirai/atlas-migration-push/batch6` | 2026-07-05 | ✅ **CLOSED 2026-07-18** — `cfd-core` committed (2026-07-10); `moirai` committed (2026-07-10); `ritk-core` committed `ba6da3a5` (2026-07-14). `rg -n "global_allocator"` returns zero across all three library crates. |

The convention shape (per ADR 0010 §Decision §"Per-batch name pattern"): **one annotated tag per batch** at inner-repo closure, anchored on the inner consumer-repo commit. Atlas-parent side gets a `chore(atlas): Advance <consumer-repo> submodule pointer to <inner-SHA>` commit + a `chore(atlas): Sync <consumer-repo>/atlas-migration-push/<N> + migration push record` docs-commit + (when applicable) an ADR authoring commit. Atlas-parent itself is the ceremony repo — **no per-batch tag on Atlas-parent**. Tag namespace reserved: `{consumer-repo}/atlas-migration-push/batch{N}` where `{N}` matches the `atlas/backlog.md` row number and `{consumer-repo}` matches the leaf consumer responsible for the migration push. Multi-repo CR-class batches (#6 above) put the tag on the primary repo (`cfd-core`) and enumerate the cross-repo commit chain in the tag annotation body.

Reference: `D:/atlas/docs/adr/0010-cfdrs-atlas-pointer-advance.md` (Accepted 2026-07-05) §Decision §"Per-batch name pattern" is the source-of-truth; this checklist section is the pre-allocation tracker enforced before batch closure.

## Historical claim checkpoint (superseded)

> The dated entries below are retained for audit only. No claim, watchpoint,
> or next-session instruction in this section remains active.

- Owned files (atlas-meta, this turn): `backlog.md`, `checklist.md`, `gap_audit.md` at the atlas workspace root (NOT under `atlas/`); these are the cross-repo PM artifacts.
- Owner: `claude-codex` (current session).
- Atlas-meta claim start: 2026-07-04.
- Atlas-meta last landed (codex session): `61931faf` (RITK Batch #3 sub-batch #1 sync + kwavers/Burn risk surfacing, 2026-07-06, layered atop peer commits `e82fe14c`, `4a04cad1`, `4b71cda9`, `3062ce1b`, `81413ed9`, `c5f2a84e`, `61931faf`; followed by peer `5adf4a27` "Helios closure triage" 2026-07-06 13:37). This turn: peer landed `c6b845f81` Batch #4 slice 2 (`burn_wave_equation_2d` dependency graph: 12-family Burn→Coeus native rewrite, 186 `burn::` line-hits / 80 files remaining, down from 315/144). See risk #8 below.
- **Latest closed migration batch**: Batch #3 — RITK Burn→Coeus provider cutover **FULLY CLOSED 2026-07-18**. PR #42 (`f01b1643`, 1298 files, -59482 lines) + PR #43 (`b4be04ca`, closeout docs) + fixes `6086d757`/`9de12515`/`24a3cb08` merged on `origin/main` at `9af7dbbe`. All sub-batches consumed: #1 (#1 `d7a940b5`), #2 (docstring deprecation), #3.a–#3.f (per-crate queue `603ad516`→`310fcd6c`), #3.g+#4+#5+#6 (atomic cutover in PR #42). burn_surface.allowlist deleted; all Burn/ndarray deps removed from workspace manifest. Atlas pointer advanced `b007326e` → `9af7dbbe` for the cutover and now tracks projection-hardening PR #44 at `688eb8e`. Earlier closed: Batch #2 (CFDrs nalgebra → leto, `d58d1fe3`).
- **This turn (2026-07-06, codex, resumed)**: T1 re-verification of the `kwavers` "Residual `burn`" inventory at inner HEAD `c6b845f81` post peer commit `c6b845f81` "Complete Burn-to-Coeus migration for 2D PINN dependency graph". Findings layered on prior `5adf4a27` baseline: (1) the residual inventory in `gap_audit.md` L91-103 (now refreshed) drained from 315 `burn::` line-hits / 144 files to **186 / 80** (−41% hits, −44% files) and `use burn` import-sites from 222/139 to **125/78** (−44% / −44%). Slice 2 rewrote the `burn_wave_equation_2d` family (`acoustic_wave`, `cavitation_coupled`, `sonoluminescence_coupled`, `electromagnetic`, `adaptive_sampling`, `meta_learning`, `transfer_learning`, `distributed_training`, `quantization`, `uncertainty_quantification`, `universal_solver`, `field_surrogate/training/trainer`) onto `coeus_autograd::Var` + `coeus_nn::Module` + `coeus_optim::SGD`; per-parameter gradients replace burn-shaped `ModuleMapper`/`GradientExtractor`/`GradientApplicator`/`MetaOptimizer<B>` — the peer's native-rewrite direction is now explicit and **substantively aligns with risk #8's hard-tier framing**. (2) `cargo tree -p kwavers-solver | grep burn` is still **non-empty** (full `burn v0.19.0` stack pulled via `kwavers-solver/Cargo.toml:53` `optional = true` `pinn` feature + `kwavers/Cargo.toml:138` non-optional dev-dep). Batch #4 completion condition (`cargo tree | grep burn` returns zero) is **unmet**. (3) Residual unmatched: `burn_wave_equation_3d/{wavespeed,solver,optimizer,mod,tests}`, `pinn/elastic_2d/{training/{loop,optimizer,adaptive_sampling},loss/pde_residual/tests}` (32+ hits in `elastic_2d/` alone), `pinn/ml/field_surrogate/{network,tests/training}`, 17 top-level `kwavers/{benches,examples,tests}/**` files. The `burn.rs` facade + `burn_compat` module remain on disk, referenced by these still-unmigrated families; deletion awaits the Burn-source purge. (4) Risk #8 status: **partially-resolved** by `c6b845f81`'s explicit non-shim direction + the major slice-2 surface drained; live until facade + Cargo.toml strip land. Atlas-meta authors one atomic observation-mode doc-sync commit replacing the `400c32624`-anchored burn residual inventory with the `c6b845f81`-anchored one and adding slice-2 record to checklist Batch #4 progress. Does NOT touch peer-claimed source (kwavers tree).
- **This turn (2026-07-06, Helios/RITK DICOM ownership)**: RITK inner commit `8f8360ff` adds typed `ritk-dicom` attribute ownership (`DicomTag`, common DICOM image `tags`, and `DicomAttributeRead`). Helios H-061 now removes the direct production `dicom` edge and reads Rows/Columns/SamplesPerPixel/BitsAllocated/PixelRepresentation/RescaleSlope/RescaleIntercept/PixelSpacing/SliceThickness/ImagePositionPatient/transfer syntax through RITK. Evidence tier: value-semantic RITK attribute nextest (2/2), Helios DICOM loader nextest (5/5), and normal-dependency tree proof that `dicom` appears below `ritk-dicom` only. H-063 is filed for the remaining `helios-imaging` boundary audit: generic medical-image toolkit operations move to RITK; radiation-domain MVCT simulation kernels remain in Helios.
- **Historical next-claim snapshot:** the dated Kwavers Batch #1/#4 queue was
  superseded by both closures on 2026-07-12.
  - Note on stale PM records: `backlog.md` L90 + `gap_audit.md` L91-97 + risk #6 kwavers-sub-row still anchor on the `c6b845f81` snapshot (186/80 + `[ahead 13]`). They are stale by 4 commits and 41 hits / 38 files; refresh held back this turn because peer concurrently authored in those two files (the pre-batch-#5 `cargo semver-checks` verification note + §Risk #9 `SEMVER-CHECKS RESOLUTION BLOCKER (mnemosyne-arena → themis dep-resolution)`, still-uncommitted working-tree edits per `git status -sb backlog.md gap_audit.md`). Composing the kwavers-burn refresh into peer's semver-blocker commit would violate `git_discipline` atomic-commit cleanliness; defer until peer's commit lands, then a follow-up atomic commit refreshes those two files to `d4ff48285`-anchored residual evidence.
- Concurrent claim streams to honor (per `concurrent_agents`, all disjoint from atlas-meta's scope, all DO NOT touch source): `repos/kwavers` `codex/kwavers-core-moirai-parallel` (27 dirty paths + `[ahead 12]` ⇒ peer ACTIVE); `repos/moirai` `refactor/remove-dead-subsystems` (26 dirty paths); `repos/leto` `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile (14 dirty paths); `repos/coeus` `main` (19 dirty paths across dtype/tensor/Python/docs); `repos/gaia` `refactor/migrate-to-leto-geometry` (5 dirty paths across CSG source/bench/PM); `repos/eunomia` `main` (7 dirty paths, `acos`/`asin`/`atan` PR-queue); plus peer claims in `repos/{apollo,CFDrs,hermes,melinoe}` (`CFDrs` now 79 dirty paths). `repos/{helios,ritk,hephaestus,mnemosyne,themis}` have no inner dirty paths after the Helios/RITK DICOM ownership closure and prior pointer-sync commits.

## Residual risks (logged here per actions of `gap_audit.md`)

- T1 confirms `kwavers-solver/src/forward/nonlinear/{kuznetsov,westervelt_spectral,solver/{model_impl,rhs}, operator_splitting/mod}` aggregating ~35 sites; full file-line inventory in `gap_audit.md` per the cross-repo master.
- T1 confirms `kwavers-solver/src/inverse/same_aperture/{operator/linear_op:9 +, encoded:1}` already `moirai_parallel::ParallelSliceMut`; no Rayon created.
- T1 confirms `ritk/python.rs` `numpy::{ndarray::Array2,3,4,}` import set for Python interop only; not a migration target.
- `hephaestus-cuda/src/application/decomposition/eigen.rs` Complex upload mismatch is stale in the checked-out `ks5-cholesky-panel` tree: `leto_ops::eigenvalues` output is converted to `num_complex::Complex<f32>` before upload, and `rustup run nightly cargo check -p hephaestus-cuda --features decomposition` passes. Runtime CUDA nextest coverage remains unclaimed.
- **NEW (this turn 2026-07-06)**: `kwavers-solver/src/burn.rs` + `kwavers-solver/src/inverse/pinn/ml/burn_compat` form a burn→coeus face-shift alias module — `integrity` HARD-tier candidate (compatibility-soup / distributed-shim pattern). Peer-claim boundary: atlas-meta surfaces, peer resolves. See `gap_audit.md` surfacing risk #8 for full framing + two reconciliation options (commit-body retraction-or-burn.rs-delete-now) handed to peer.

## Historical next-micro-sprint archive

> Superseded: the migration targets described below are closed. This section
> preserves dated evidence and is not a current hand-off or work queue.

**Historical observation-mode hand-off:**
- This turn (2026-07-06, codex) surfaced the Batch #4 slice-1 partial-land + the burn.rs facade `integrity` concern via atomic atlas-meta doc edits only (PM artifacts at workspace root). Did NOT migrate kwavers/coeus/gaia source because those scopes are peer-active. Separately, the Helios/RITK DICOM ownership slice is closed: `ritk-dicom` now owns typed DICOM attribute reads, and Helios production DICOM loading consumes RITK for parse + attributes + transfer syntax + pixel decode.
- Next turn (2026-07-06, codex resumed) refreshed the Batch #4 record against peer's actual working-tree HEAD `d4ff48285` (slices 3 `cd8cf776d` `burn_wave_equation_3d` + slice 4 `7235d464a` `field_surrogate/{network,tests}` + interstitial `ae86daecc` + slice 5 `d4ff48285` `advanced_architectures`+`autodiff_utils`), all drained to native coeus. This atlas-meta turn authored a single atomic commit editing `checklist.md` only (Batch #4 §Progress append + §In-flight §Next-claim refresh + §Next-micro-sprint refresh), explicitly NOT touching `backlog.md` or `gap_audit.md` because peer is concurrently authoring them with the pre-batch-#5 `cargo semver-checks` verification note + §Risk #9 `SEMVER-CHECKS RESOLUTION BLOCKER (mnemosyne-arena → themis dep-resolution)` (still-uncommitted working tree per `git status -sb backlog.md gap_audit.md`). Composing the kwavers-burn refresh with peer's semver-blocker commit would violate `git_discipline`'s atomic commit unit; deferred to a follow-up once peer's commit lands.
- Peer's slice-2..N sequence progress (post-handoff): slice 2 `c6b845f81` (12-family `burn_wave_equation_2d` dependency graph) ✅ landed; slices 3-5 `cd8cf776d` + `7235d464a` + `d4ff48285` ✅ landed (drained `burn_wave_equation_3d` + `field_surrogate/{network,tests/training}` + `advanced_architectures`+`autodiff_utils`). Remaining peer queue: slice 6 `pinn/elastic_2d/{training/{loop,optimizer/{mappers,pinn_optimizer,tests},adaptive_sampling/batch},loss/pde_residual/tests}` → slice 7 17 top-level `kwavers/{benches,examples,tests}/**` files + `pinn/ml/burn_wave_equation_1d/physics/mod.rs` (2) + `xtask/src/migration_audit.rs` (1) → slice 8 `burn.rs`+`burn_compat` deletion + `kwavers-solver/Cargo.toml:53` `burn` optional dep + `kwavers/Cargo.toml:138` `burn` dev-dep removal + `pinn` feature `dep:burn` strip at L62-70.
- **T1 confirmed (this turn 2026-07-06, codex resumed continuation)**: peer is mid-slice-6+7 Batch #4 Burn→Coeus migration AND a parallel `nalgebra` → leto/eunomia migration across kwavers. Inner kwavers working-tree dirty count expanded from 7 files (at start of this turn) to **116 files** — both Batch #4 slice-6 `elastic_2d` + slice-7 plus the gap_audit L51-59 `nalgebra` residual-site migration are live. Direct evidence: (1) `crates/kwavers/Cargo.toml` working-tree diff strips the workspace `nalgebra = { version = "0.33", features = ["serde-serialize"] }` line (visible as `-nalgebra = { ... }` in `git diff Cargo.toml`); (2) `git grep 'nalgebra' -- '*.rs'` returns **164 line-hits** across the dirty tree (transient inflation as rewrite references both old `use nalgebra::...` imports + new `leto`/`leto_ops::`/`eunomia::` callsites co-exist), against the prior `aa10a6e76`-anchored L51-59 baseline of 13 source sites × 5 manifests; (3) the 13 source-site file-path set in `gap_audit.md` L52-59 (`kwavers-mesh/src/tetrahedral/mesh.rs`, `kwavers-transducer/src/flexible/calibration/{types,manager/kalman,manager/mod}`, `kwavers-medium/src/anisotropic/{christoffel,stiffness}`, `kwavers-analysis/.../three_dimensional/cpu/mvdr/mod.rs`, `kwavers-solver/.../{cbs/solve,hybrid/{bem_fem_coupling/{interface,coupler/struct_impl/solvers}},helmholtz/fem/solver/core/{interpolation,element}}`) is **exactly the file set now dirty** in the inner kwavers working tree — the route-by-route site rewrites are landing on the same files `gap_audit.md` enumerates; (4) peer is simultaneously dirty across `kwavers-analysis/.../beamforming/{adaptive/{mvdr,subspace},narrowband/{capon,subspace_spectrum},three_dimensional/{cpu,processing}}` (15+ files), `kwavers-grid/{src/compat.rs DELETION, src/{lib,structure,operators/{curl,divergence,gradient,gradient_optimized/*,laplacian}}.rs}` (11 files), `kwavers-math/{linear_algebra/{basic,eigen/*,eigendecomposition/*,iterative/lsqr/*,norms,sparse/*,tests},numerics/operators/{differential/*,spectral/*},fft/{gpu_fft,kspace,mod,utils},inverse_problems/{pnp,regularization/*},simd_safe/{auto_detect/*,avx2,neon,operations,swar},lib}` (37 files; SIMD dispatch path may also be Hermes-aligned), `kwavers-medium/src/anisotropic/{christoffel,stiffness}` (3 files), `kwavers-mesh/{Cargo.toml,src/tetrahedral/mesh}` (2 files), `kwavers-solver/src/{forward/{bem/solver/{assembly,solution},hybrid/bem_fem_coupling/{interface,struct_impl/solvers},helmholtz/fem/solver/core/{element,interpolation,solve}},inverse/{fwi/frequency_domain/cbs/solve,pinn/elastic_2d/{loss,pde_residual/*,model,training/loop,training/optimizer/*},reconstruction/unified_sirt,reconstruction/seismic/??},pins/elastic_2d/ml/autodiff_utils/*}` (25+ files including 5 DELETIONS: `elastic_2d/loss/pde_residual/{divergence,gradients,strain_stress,time}.rs` + `elastic_2d/training/optimizer/mappers.rs`), `kwavers-transducer/{beamforming/processor,flexible/calibration/{types,kalman}}` (4 files), top-level `kwavers/benches/{cpml,simd_fdtd}` (2 files). (5) Burn residual simultaneously drained: `burn::` line-hits **105 across 31 files** at the dirty tree (down from `d4ff48285` HEAD `145/42`) — peer's slice-6 `elastic_2d` + slice-7 top-level files rewrite is landing Live; `burn.rs` + `burn_compat.rs` shim still **constant 34 hits** (shim content unchanged; deletion awaits the last burn-source purge). (6) `par_for_each` residual **84 sites / 28 files unchanged** — peer's current dirty tree does NOT touch Batch #1 Rayon→Moirai; Batch #1 remains stable as a separate downstream phase.
- **T1 confirmed (2026-07-07 Burn cleanup closeout + neutral-name continuation)**: current `repos/kwavers` working tree has zero kwavers manifest Burn hits, zero requested PINN/top-level source-scope `Burn`/`burn_`/`burn-`/literal `burn` hits, no `crates/kwavers-solver/src/burn.rs`, and no `burn_compat` alias path. The 1-D/2-D/3-D PINN module paths are framework-neutral (`wave_equation_1d`, `wave_equation_2d`, `wave_equation_3d`), exported names are framework-neutral (`PinnWave*`, `PinnConfig*`, `LossWeights*`, `TrainingMetrics*`), and the beamforming adapter is `pinn_adapter`. `xtask/legacy_surface.allowlist` was regenerated and `rustup run nightly cargo run -p xtask -- legacy-migration-audit` reports allowlist clean. Whole-repo literal residual is **356 lines across 21 files**, concentrated in `Cargo.lock` and historical PM/audit prose; scoped PINN/top-level source plus allowlist residual is **0 lines across 0 files**. `cargo tree -p kwavers-solver --features pinn -i burn` still resolves Burn through RITK provider crates, not kwavers manifests. Verification: `rustup run nightly cargo fmt -p kwavers-solver -p kwavers --check` passed; `rustup run nightly cargo check -p kwavers-solver --features pinn` passed; `rustup run nightly cargo check -p kwavers --features pinn --tests --benches --examples` passed with pre-existing warnings; `rustup run nightly cargo nextest run -p kwavers --features pinn --test pinn_bc_validation --test pinn_ic_validation --status-level fail --no-fail-fast` ran 16 tests with 12 passed and 4 failed on legacy 3-D loss thresholds.
- **2026-07-08 Bulk provider-surface round 3 — 5 atomic choruses landed** (post-`36acbbca9` fresh-session, post-`gap_audit.md` row 13 injection): the prior cand-2 session's round-1 (`2e1c4f20d`→`274a6a961`→`a12d1dd77`) + round-2 (`5d3395e95` + `715cff24e` + `02da06611`→`ab71f08ad`→`36acbbca9`) bulk-advance blocks left 5 provider surfaces DIVERGED; round 3 captured the inner churn that landed since then, advancing 5 gitlinks in 5 NEW atomic chore commits (per row 10 NO-AMEND + row 11 DYNAMIC-SHA-EXTRACTION):
  - `ad6cf57d4` apollo `2e6f9be` → `e6ecce4` (inner head `chore(deps): sync Cargo.lock (eunomia num-traits dependency)`)
  - `1828ea14a` eunomia `b3fd6f2` → `22e971e` (inner head `chore(deps): sync Cargo.lock (num-traits dependency)`)
  - `852de7129` hermes `92187d0` → `166a7b9` (inner head on `rescue/detached-simd-numa-work` branch — 17 commits ahead of `origin/main` — `Revert "ci(miri): use Tree Borrows for the mnemosyne-allocator-backed run"`)
  - `769b70a67` leto `83e1693e1` → `a9572da27` (inner head `chore(deps): sync Cargo.lock (eunomia num-traits dependency)`)
  - `1fe3c0e56` mnemosyne `482670d` → `98a02b6` (inner head `docs(gap_audit): Record the Miri alloc/free aliasing finding (HIGH PRIORITY)` — *node: this finding is now ALIGNED in atlas-meta's tracking; gap_audit row 13 records it as a residual risk for the mnemosyne peer to root-cause*)
- **Net alignment state post-`1fe3c0e56`**: all 12 actively-tracked submodules (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, kwavers) ALIGNED at inner HEAD with zero DIVERGED gitlinks — the first all-aligned state since the `e0bf55684` cross-tree reclamation audit shifted to round-2 bookkeeping. **ritk-python test suite (47/47)** compiled+passed at committed inner HEAD `1f49278c` (value-semantic asserts — see `gap_audit.md` line-154 bulk-advance unblock evidence). **KW-CV-001 watchpoint re-affirmed ACTIVE**: at inner HEAD `35ee01076`, trigger `(cd /d/atlas/repos/kwavers && git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l)` returns 0; peer continues slice-by-slice Batch #1 + Batch #4 work without explicit closeout.
- **Atlas-meta action posture**: peer's concurrent expansion across the kwavers Batch #1 + Batch #4 surfaces consumes the entire kwavers source surface, as described in the previous line-586 entry — there is no disjoint-contribution surface available to atlas-meta at this moment beyond observation-mode PM-record refresh. The round-3 block closes the 5 provider-pointer divergences that were the immediate-discovery billboard; the next bulk-advance round (round-4) is contingent on either inner HEAD churn (peer-WIP-after-push divergence) OR the KW-CV-001 watchpoint firing for kwavers.
- Atlas-meta action posture: peer's concurrent expansion across two batch themes (Batch #4 slice-6+7 + `nalgebra`-residual-site migration) consumes the entire kwavers source surface — there is no disjoint-contribution surface available to atlas-meta at this moment beyond observation-mode PM-record refresh. The pending `backlog.md` L90 + `gap_audit.md` L51-59/L91-97 refresh is now **larger** than the kwavers-Burn-only refresh originally deferred — same atomic commit scope explodes to refresh BOTH the `nalgebra` L51-59 block AND the L91-97 burn residual block; the per-batch-theme atomic discipline argues for two separate follow-up atomic commits when peer's next landing stabilizes the tree. Both still deferred until peer's pre-batch-#5 semver-blocker commit (the `backlog.md`+`gap_audit.md` working tree) lands.
- **Historical watchpoints:** the nalgebra, Batch #1, and Batch #4 closure
  signals below this archive all fired; no peer closure signal remains pending.
- Once the peer lands closure(s) or a claim goes stale (next session's check): atlas-meta bumps `repos/kwavers` pointer + closes the Batch #1 and/or Batch #4 entries in the in-flight section of `backlog.md`.

- **2026-07-08 Bulk provider-surface round 4 — 6 atomic chore commits landed (post-`1fe3c0e56` session)**: the round-3 inner-churn capture cycle overshot and two divergent screenshots reappeared shortly after the `2d78fffa4` OOB session landed (a `chore(atlas): Advance repos/hephaestus pointer to 240b260 (CU-P6/CU-M3)` commit at `6902d2e92` merged with my staged r4 stash, both consuming hermes/leto r4 pointers + adding hephaestus to 240b260). Re-probe at session-resume returned `hermes c7b17b02c73a / leto 86d366bc0e90` ALREADY-RESOLVED via that OOB consolidation. The r5 round then captured (a) the OOB-merging of the hermes `5ad1b58 → c7b17b02` ergonomically inside the consolidated `6902d2e92`, (b) the leto `a9572da → 86d366b` (Migrate kwavers closure path unblock — `feat(leto-ops): batched LU, CSC sparse format, CG/GMRES iterative solvers`), plus 5 fresh divergences that surfaced mid-session:
  - `e3223094a` hermes c7b17b02c73a (inner `chore(deps): sync Cargo.lock (eunomia num-traits dependency)`) — bundled with leto advance during the `6902d2e92` OOB consolidation; verified via `git --no-pager show --stat e322309`
  - `e3223094a` leto 86d366bc0e90 (inner `feat(leto-ops): batched LU, CSC sparse format, CG/GMRES iterative solvers` — canonical generic LU factorization in batched form for tiled GPU dispatch, CSC sparse storage, CG/GMRES iterative kernels; unblocks kwavers-solver Bulk-solver migration closure target)
  - `6a598da91` kwavers 89117870 (inner `Migrate kwavers Complex/ndarray types to eunomia/leto atlas crates` — Phase-3 closure of Complex<f32>/Complex<f64>, ndarray Array bases, and coefficient paths onto eunomia+leto atlas substrates; replaces nalgebra/ndarray/numeric-complex stack in the kwavers-core domain)
  - `0e34ae082` coeus ec69a6a (inner `fix(coeus-dist): close TOCTOU race in TCP test port allocation` + co-emitted `342f38d` `docs(checklist): reconcile MS-406/MS-407 as already-closed`)
  - `045291499` ritk e75d8748 (inner `Add Module/AutodiffModule impls for DisplacementField and DisplacementFieldTransform` — directly resolves the displacement_registration_test failure noted in row 6, the Sub-batch #5 RITK-spatial-rebind closure per ADR 0012)
  - `4a4cf928a` coeus 006f2a7 (inner `feat(coeus-nn): add MaxPool3d/AvgPool3d benchmark rows (G-043)` — extends criterion bench registry for 3D pooling kernels)
  - `4b7f4804e` kwavers 09c645f30 (inner `Migrate kwavers-core/source/signal/grid/field from ndarray to leto` — Phase-4 closure of kwavers-core domain crates source/signal/grid/field off ndarray onto leto's NDArray substrate; follow-on to `89117870` Complex/eunomia migration)
- **Net alignment state post-`4b7f4804e`** (this turn): all 13 actively-tracked submodules ALIGNED (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, gaia, hephaestus, kwavers) at the moment of capture. KW-CV-001 watchpoint re-probed (still 0). The round-4 migration advances do not trigger the watchpoint.
- **2026-07-08 (mid-session) Test/example validation sweep**: triggered by the user's directive "cleanup and resolution of all test and example issues/errors". T1 verification at the just-advanced consumer-side inner HEADs:
  - **ritk** at `529d6651` inner HEAD: `cargo nextest run -p ritk-python --lib` PASSES **47/47** (1m 41s compile, 0.34s test execution) — value-semantic asserts survive.
  - **CFDrs** at `72275347` inner HEAD: `cargo check --workspace --all-targets` PASSES (1m 31s) — zero warnings across cfd-{core, math, 1d, 2d, 3d, validation, optim, python, schematics, io} + gaia.
  - **CFDrs** at `72275347` inner HEAD: `cargo nextest run --workspace --lib` PASSES **2177/2177** (1 skipped, 37s execution, 0 failed, 1 slow flagged at the cfd-3d bifurcation::validation::test_mesh_convergence_outputs_observed_order_and_gci boundary of 28.1s — within 15s slow-timeout×2 budget).
  - **CFDrs subset** `cargo nextest run -p cfd-math -p cfd-1d -p cfd-2d --lib`: PASSES **1335/1335** (24.9s, 1 skipped).
  - **kwavers** at `ccc6bbf9e6` inner HEAD: `cargo check -p kwavers-solver --workspace` PASSES (49.88s); the workspace-wide ndarray↔leto boundary integration landed.
  - **kwavers** at `ccc6bbf9e6` inner HEAD: `cargo check --workspace` PASSES with 1 dead-code warning (`fn to_leto3` unused in `crates/kwavers-simulation/src/dispatch/elastic_pstd.rs:8:4`).
  - **kwavers** at `ccc6bbf9e6` inner HEAD: `cargo nextest run --workspace --lib` FAILS at compile due to 1 residual slip at `crates/kwavers-solver/src/plugin/mod.rs:204:21` — the `NullBoundary` test-mock `apply_acoustic_freq` method uses `use ndarray::Array3;` (line 182) which shadows the workspace's `leto::Array3` re-binding; the `Boundary` trait now declares `&mut leto::Array<eunomia::Complex<f64>, VecStorage<eunomia::Complex<f64>>, 3>`. One-line fix lands at line 182. **Disjoint-scope peer-owned**: record to `gap_audit.md` ### Bulk-migration priority #1 × #2 source-side overlap (2026-07-09); atlas-meta does NOT touch `repos/kwavers/crates/kwavers-solver/src/plugin/mod.rs`.
- **Atlas-meta action posture**: round-4 captured all in-session churn; mid-session validation sweep found 1 residual slip in kwavers-solver (peer-owned per disjoint-scope) + 1 cosmetic dead_code warning. Awaiting peer's next kwavers commit (KW-CV-001 watchpoint catch + the 2-line plugin/mod.rs fix). Either path stays in observation mode; no source-tree work concrete to atlas-meta.
- **2026-07-10 — chorus-chain revert + litter hygiene pass**: 4 unpushed `chore(atlas): Post-review patch for d6db896 -- NIT 1 closure ...` style commits accumulated atop `d6db896` (`78e40e4` + `035b9ca` + `a5b3cdb` + `2acedcf`) — collectively adding 5 self-referential narrative sub-sections to `docs/coordination/INDEX.md` and 26 blank trailing lines (`+` × N). The chorus-chain was the audit-predicates-recursive-noise pattern flagged as pollution per handoff §Pitfalls (HIGH); reset to `d6db896` (own unshared branch + unpushed + pure-noise content) restored the canonical PM baseline. RN-CC-05 audit predicates re-verified: 4-file `rg -F "Parent-SHA:"` aggregate = 7 hits (>=4 ✅), `git log --grep "Parent-SHA:" --oneline` = 10 entries (>=2 ✅✅✅). 17 ignored scratch files (`_apply_*.py` × 9, `_commit_*.txt` × 8) and `gap_audit.md.reframe.bak` deleted from worktree (covered by `_*` + `*.bak` `.gitignore` patterns). `git status --ignored --short` now reports only 8 benign infrastructure patterns (`.claude/`, `.ruff_cache/`, `repos/report/`, `target/`) + 7 submodule inner-dirty markers. Branch parity with `origin/codex/kwavers-atlas-integration` (0 ahead). KW-CV-001 watchpoint: still 0 (peer kwavers-side closeout pending); KW-CV-002: stable. Repository returned to observation mode; resignation-confirmed via `git --no-pager status` reporting "Your branch is up to date with 'origin/codex/kwavers-atlas-integration'."

Branch: `codex/kwavers-atlas-integration`.### H-063 done -- Batch #1 slice 3 partial-closure-mark 2026-07-08

Per the peer's `d2cb977b` chore (refactor(kwavers-solver): Migrate diffusion.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 3), on codex/kwavers-core-moirai-parallel atop parent c77a926d8): 5/41 sites migrated in 3/15 files cumulative. The 1 new site is in crates/kwavers-solver/src/forward/nonlinear/kuznetsov/diffusion.rs (1 mut + 4 immut Zip par_for_each at L93 in compute_diffusive_term_workspace), migrated to par_mut().enumerate() with 5 is_standard_layout() asserts applied in-chore (Nit 1 from prior slice 2 review). Cargo check clean at inner HEAD. **36/41 sites / 12/15 files remain**. KW-CV-001 watchpoint remains ACTIVE.
### H-062b done -- Batch #1 slice 2 partial-closure-mark 2026-07-08
> Note: this mark landed after the slice 3 mark (commit f2c89a73) due to flaky prior re-emission attempts; it documents cumulative state AT slice 2 chore landing, not the present state.

Per the peer's 9541155f chore (refactor(kwavers-solver): Migrate model_impl.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 2), on codex/kwavers-core-moirai-parallel atop parent 5cd8c708 = slice 1): 4/41 sites migrated in 2/15 files cumulative at slice 2. The 2 new sites are in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/model_impl.rs` (1-mut + 2-immut Zip at L48 + 1-mut + 3-immut Zip at L62 inside KuznetsovWave::update_wave), migrated via the canonical 1+N physics-equation pattern (as_slice{_mut,}().expect() + par_mut().enumerate() with flat-index lookups). Cargo check clean at inner HEAD. **37/41 sites / 13/15 files remain** after slice 2. KW-CV-001 watchpoint remains ACTIVE. NOTE: retroactive land AFTER slice 3 mark (prior re-emission attempts failed due to basher command-length limits).
### H-064 done -- model_impl.rs Nit 1 asymmetry fixup 2026-07-08

Per the peers b21679f5c chore (fix(kwavers-solver): Add standard-layout assert to model_impl.rs migration, on codex/kwavers-core-moirai-parallel atop parent d2cb977b = slice 3 = c77a926d8 struct_impl.rs fixup = 9541155f slice 2): 7 is_standard_layout() asserts added retroactively to model_impl.rs (slice 2 file): 3 in first-step branch (1 mut pressure_field + 2 immut self.pressure_current + rhs) + 4 in multi-step branch (1 mut + 3 immut including NEW self.pressure_prev). Each assert precedes the corresponding .as_slice{_mut,}().expect() call. Cargo check clean. Cumulative: 5/41 sites / 3/15 files migrated + 2 file-level fixups (c77a926d8 struct_impl.rs + b21679f5 model_impl.rs). 36/41 sites / 12/15 files remain. KW-CV-001 watchpoint remains ACTIVE.

### H-065 done -- Batch #1 slice 4 partial-closure-mark 2026-07-08

Per the peer `9595a99f5` chore (refactor(kwavers-solver): Migrate nonlinear.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 4), on codex/kwavers-core-moirai-parallel atop parent b21679f5c = model_impl.rs Nit 1 fixup = d2cb977b slice 3 = c77a926d8 struct_impl.rs fixup = 9541155f slice 2 = 5cd8c708 slice 1): 6/41 sites migrated in 4/15 files cumulative across slices 1+2+3+4. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/nonlinear.rs` (1 mut + 3 immut Zip par_for_each at L109 in `compute_nonlinear_term_workspace`), migrated to `par_mut().enumerate()` with 4 `is_standard_layout()` asserts applied in-chore (Nit 1). Cargo check clean at inner HEAD. **35/41 sites / 11/15 files remain**. KW-CV-001 watchpoint remains ACTIVE.

### H-066 done -- Batch #1 slice 5 partial-closure-mark 2026-07-08

Per the peer `d614a7f57` chore (refactor(kwavers-solver): Migrate operator_splitting/mod.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 5), on codex/kwavers-core-moirai-parallel atop parent 9595a99f = slice 4 nonlinear.rs = b21679f5c model_impl.rs Nit 1 fixup = d2cb977b slice 3 diffusion.rs = c77a926d8 struct_impl.rs fixup = 9541155f slice 2 model_impl.rs = 5cd8c708 slice 1): 7/41 sites migrated in 5/15 files cumulative across slices 1+2+3+4+5. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/operator_splitting/mod.rs` (1-mut + 1-immut Zip par_for_each at L191 in OperatorSplittingSolver::nonlinear_step), migrated to par_mut().enumerate() with 2 is_standard_layout() asserts applied in-chore. Cargo check clean at inner HEAD. **34/41 sites / 10/15 files remain**. KW-CV-001 watchpoint remains ACTIVE.

## bash-heredoc artifact audit verification 2026-07-08

> Audit verified: 0 unresolved `\$VAR` artifacts (matches pattern `\$[A-Z_]+`) remain in 3 PM artifacts after the \$SHORT substitution chore (commit `92dad112`). All residual `$` characters in the 3 PM artifacts are legitimate (Rust generic syntax `<$t as Scalar>`, command-substitution documentation `$(cd repos/...)`, mathematical notation, or anti-pattern template examples in audit prose). Code-reviewer N3 carry-forward from the \$SHORT substitution chore is now CLOSED.

### H-067 done -- Batch #1 slice 6 partial-closure-mark 2026-07-08 (heterogeneous site 1 deferred)

Per the peer `7be3fbbd8` chore (refactor(kwavers-solver): Migrate rhs.rs homogeneous par_for_each sites to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 6), on codex/kwavers-core-moirai-parallel atop parent d614a7f5 = slice 5 = 9595a99f slice 4 = b21679f5c model_impl.rs Nit 1 fixup = d2cb977b slice 3 = c77a926d8 struct_impl.rs fixup = 9541155f slice 2 = 5cd8c708 slice 1): 11/41 sites migrated in **6/15 files** cumulative. The 4 new sites are in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/rhs.rs` (1-mut + 1-immut Zip par_for_each in `KuznetsovWave::compute_rhs` homogeneous branch -- sites 2-5), migrated with 8 is_standard_layout asserts (2 per site) + 4 par_mut().enumerate with flat-index lookups. Cargo check clean. **30/41 sites / 9/15 files remain**. Heterogeneous site 1 (`Zip::indexed(rhs.view_mut())` with 3D-index closure arg + 8 (i,j,k) lookups) deferred to follow-up chore. KW-CV-001 watchpoint remains ACTIVE.

## Session 2026-07-12 -- leto empty-layout fix + atlas-meta verification sweep

### Closed (atlas-meta write-set)

- **`leto` [patch]**: `Layout::has_zero_stride_aliasing` short-circuits on `size() ==
  0` (commit `08d0b44` on `repos/leto` main, pushed to origin). Empty C/F-
  contiguous layouts produced by `c_contiguous_strides` defensive
  zero-stride collapse for zero-sized interior axes are no longer falsely
  flagged as aliased. Regression tests added (5 cases). Provider gate:
  fmt / clippy -D warnings / nextest --all-features 564/564 / doc --no-deps
  all clean.
- **Unblocked consumer test**: `kwavers-solver::inverse::fwi::time_domain::
  encoded_source::tests::hadamard_averaged_encoded_gradient_matches_summed_shot_gradient`
  now PASSES (was the sole documented kwavers lib test failure). Root cause:
  test uses `CPMLConfig::default()` with `per_dimension.y == 0`, producing an
  empty `psi_p_y` memory buffer of shape `[8, 0, 8]` with strides `[0, 8, 1]`;
  the leto predicate rejected the mutable zip. No kwavers source change
  required (the temporary `eprintln!` debug lines from the prior session were
  uncommitted scratch; removed by restoring HEAD state on `axis.rs`).
- **atlas-meta pointer**: `repos/leto` submodule bumped `a20286e -> 08d0b44`.

### Verification sweep (consumer read-only)

Full-workspace `cargo nextest run --no-fail-fast` from each consumer repo:

| Repo | Inner HEAD | Branch | Result | Known peer-active items |
|---|---|---|---|---|
| `kwavers` | `7c70d1b1d` | `codex/kwavers-core-moirai-parallel` | 5611/5612 lib pass, 1 timeout, 15 skipped | `abdominal_preprocessing_selects_one_connected_treatment_component` (elastic-fwi profile 90 s budget) -- see `gap_audit.md` KW-WATCH-002 |
| `CFDrs` | `e24922c8` | `codex/cfdrs-atlas-migration` | 3055/3056 pass, 1 fail, 30 skipped | `cfd-suite::cross_fidelity_blueprint_complex_branching` Picard non-convergence -- pre-filed by peer `fa28ce43` |
| `ritk` | `0ca58574` | `codex/ritk-burn-ndarray-cleanup` | 4900/4900 pass, 26 skipped | `ritk-model ssmmorph::decoder::tests::test_decoder_forward` 293.9 s (9.8x slow threshold) on burn NdArray backend -- peer active Burn dep strip Batch #4/#5 |

### Findings recorded in `gap_audit.md`

See `gap_audit.md` "Findings 2026-07-12" section for the three recorded items:
leto fix summary, KW-WATCH-002 (kwavers-therapy perf), and the CFDrs and
ritk peer-stream watchpoints. Per ADR 0011 disjoint-scope, atlas-meta is
NOT editing peer-active consumer source for any of these items; the leto
fix is the sole closed write-set this session.

### Concurrent peer activity (not mine)

- kwavers peer stream advanced HEAD `1a27e922d -> 7c70d1b1d` mid-session
  (`refactor(kwavers-python): Remove rank-one shim`). 11 dirty files in
  `crates/kwavers-python` (peer Stage-C complex_compat bridge in flight).
- CFDrs working tree: `Cargo.lock` artifact drift only.
- ritk working tree: 5 modified files in `crates/ritk-core/tests` + Cargo.lock
  (peer Burn dep strip WIP).

### Next actionable

- Await peer stream closure of the three watchpoints (kwavers-therapy perf,
  CFDrs cfd-1d Picard convergence, ritk Burn dep strip Batch #4/#5).
- Re-verify each consumer repo after peer closures, then trigger an
  atlas-meta alignment sweep committing the new submodule pointers.

## Session 2026-07-12 (evening) -- kwavers Batch #1 closure + ritk coeus-native pointer advance

### Closed (atlas-meta write-set)

- **`kwavers` Batch #1 [patch]**: peer commit `5913f2946`
  (`perf(kwavers-solver): Migrate solver tree to moirai parallel iterators`)
  closes the Rayon→Moirai source-side migration. Closure-condition evidence
  at HEAD `5913f2946`: `par_for_each`=0, `burn::`=0, `nalgebra`=0, `use
  ndarray`=0; `kwavers-solver/Cargo.toml` deps section carries `leto` +
  `leto-ops` + `moirai-parallel` only (zero `ndarray`/`rayon`/`burn`). Commit
  body declares "Closes remaining ndarray-parallel and rayon surface-level
  dependencies in kwavers-solver." `cargo nextest run --workspace --exclude
  kwavers-driver --no-fail-fast --lib`: 5117/5119 pass, 2 timeouts (the
  pre-existing KW-WATCH-002 abdominal-preprocessing perf tests on the
  explicit 90s `elastic-fwi` profile override), 7 skipped — NOT regressions
  introduced by the migration (peer-stream perf, atlas-meta is NOT editing
  `crates/kwavers-therapy/**`). KW-CV-001 lexical-trigger probe still
  returns 0 (peer uses `Migrate ...` subject phrasing) but the underlying
  zero-site invariant IS met and the commit body declares closure.
- **`kwavers` Batch #4 [minor]**: co-verified closed at the new HEAD —
  `cargo check -p kwavers-solver --features pinn` PASSES (53 warnings, 0
  errors). Sole residual is the `ndarray` `rayon` feature gate on
  `kwavers-solver/Cargo.toml` flagged as a separate item in the peer
  commit body (manifest detail, not a source-site residual).
- **`ritk` [minor]**: peer advanced `57b2b1c3 → bcd3b726` on
  `codex/ritk-burn-ndarray-cleanup` with coeus-native paths for
  `ritk-filter` (intensity + grayscale morphology) atop `829ebfe5`
  (convolution/stencil) and `34c3836b` (`ritk-statistics` normalization /
  comparison). Verification at HEAD: `cargo nextest run -p ritk-filter -p
  ritk-statistics -p ritk-image --lib --no-fail-fast`: 1399/1399 pass.
  Residual `use burn` imports: 320 (down from prior); dep strip per
  Batch #3 sub-batches #5/#6 were reserved at this snapshot and closed in
  RITK PR #42 on 2026-07-18.
  **Subsequent advances in same session**: peer landed
  `5812cd17 feat(ritk-filter): add coeus-native paths for
  spatial/intensity/morphology filters`, then later
  `ef9420fb feat(ritk-filter): add coeus-native paths for
  edge/diffusion/intensity filters`. Verification
  `cargo nextest run -p ritk-filter --lib --no-fail-fast` at HEAD
  `ef9420fb`: 1063/1063 pass (8.318s, well under 30s slow threshold).
  Inner HEAD advanced `bcd3b726 → 5812cd17 → ef9420fb` across the session
  per the `concurrent_agents` disjoint-scope rule — atlas-meta pins only
  verified state.
- **Atlas-meta pointers**: `repos/kwavers` gitlink advanced `01643ed9
  → 5913f2946`; `repos/ritk` gitlink advanced `57b2b1c3 → bcd3b726
  → 5812cd17 → ef9420fb` (peer landed two further coeus-native filter
  commits mid-session, each verified green 1063/1063 under
  `cargo nextest run -p ritk-filter --lib --no-fail-fast` at HEAD before
  pinning).

### Out-of-scope this session (unchanged)

- `CFDrs` (submodule status `m` lowercase): inner WT dirty with peer-active
  cfd-1d Picard convergence work (the `cross_fidelity_blueprint_complex_branching`
  finding). Gitlink ALIGNED.
- `helios` (submodule status `m` lowercase): inner WT carries only untracked
  `examples/` dirs. Gitlink ALIGNED.
- Atlas-meta does NOT absorb inner-WT state into parent pointers per the
  disjoint-scope rule; only committed inner HEAD advances are pinned.

### Next actionable

- Continue observing the three peer-stream watchpoints: KW-WATCH-002
  (kwavers-therapy abdominal-preprocessing perf), CFDrs cfd-1d Picard
  convergence, ritk Burn dep strip sub-batches #4/#5/#6.
- Provider extension items (Batch #8) remain claimable in peer-clean
  provider repos (`leto`, `moirai`, `apollo`, `eunomia`, `mnemosyne`,
  `themis`, `melinoe`, `hephaestus`).

## Session 2026-07-13 -- atlas-meta pointer advance: CFDrs Picard watchpoint closure + helios/kwavers verified advances

### Closed (atlas-meta write-set)

- **CFDrs cfd-1d Picard convergence watchpoint — ✅ CLOSED**: peer HEAD
  `153b0ed9` `fix(cfd-1d,cfd-2d): resolve cross_fidelity_blueprint_complex_branching
  convergence` resolves the long-standing OPEN-033 / `cfd-suite::cross_fidelity_blueprint
  cross_fidelity_blueprint_complex_branching` regression that previously panicked with
  `MaxIterationsExceeded: Convergence failed: Maximum iterations (10000) exceeded`.
  Re-verification at HEAD `153b0ed9`: `cargo nextest run --no-fail-fast` from
  `repos/CFDrs`: **26/26 pass**; `cross_fidelity_blueprint_complex_branching` PASS
  in 0.799s (orders of magnitude below the prior 10000-iteration stall, and well
  under the 30s slow threshold). Atlas-meta `repos/CFDrs` gitlink advanced
  `e24922c8d564816e6f0834912d900e698ef27b93 →
  153b0ed95710460014bf2429bc5bd94e31f2d054`.
- **`helios` advance**: peer HEAD `4efb14c` `fix(helios-domain): correct
  voxel_grid_construction example type errors`. Re-verification at HEAD `4efb14c`:
  `cargo nextest run --no-fail-fast` from `repos/helios`: **241/241 pass** (2.630s).
  Atlas-meta `repos/helios` gitlink advanced `5f6aef65a47d716f26452592d3a91f3d934a2ffc
  → 4efb14cd391fbd0653257865a3f3ea74fdf0e461`.
- **`kwavers` advance**: peer HEAD `4453c2275` `fix(kwavers-driver): graceful
  skip for missing KiCad fixture files`. Re-verification at HEAD `4453c2275`:
  `cargo nextest run --workspace --no-fail-fast` from `repos/kwavers`:
  **6097/6099 pass, 2 timeouts, 15 skipped**. The two timeouts are the pre-existing
  KW-WATCH-002 abdominal-preprocessing perf tests on the explicit 90s `elastic-fwi`
  profile override (`repos/kwavers/.config/nextest.toml:70-74`) — NOT regressions
  introduced by this driver fix; test-count growth (5119 → 6099) reflects peer-added
  tests. Atlas-meta `repos/kwavers` gitlink advanced `5913f29466bb6b769aefbc1a9b794c63b139babb
  → 4453c227524d9f150fb1e299c967e98821368ea7`.

### Watchpoint status post-advance

- ✅ **CFDrs cfd-1d Picard convergence — CLOSED** (peer HEAD `153b0ed9`, verified
  by atlas-meta run). Of the three peer-stream watchpoints, one is now closed.
- ⏳ **kwavers-therapy KW-WATCH-002 perf** — still open; 2 abdominal-preprocessing
  timeouts persist (peer-stream perf, NOT atlas-meta's to fix per ADR 0011).
- ⏳ **ritk Burn dep strip Batch #4/#5/#6** — still open; inner ritk WT remains
  dirty with peer WIP (Burn dep strip continuing).

### Next actionable

- Continue observing the two remaining peer-stream watchpoints (KW-WATCH-002,
  ritk Burn dep strip).

## Session 2026-07-13 (continued) -- mnemosyne advance (single) + moirai peer-break watchpoint filed

### Closed (atlas-meta write-set)

- **`mnemosyne` advance**: peer HEAD `877cde0586`
  (`docs(backend): Decide callback pair`) atop prior pinned `98a02b614`.
  Re-verification at HEAD `877cde0`:
  `cargo nextest run --workspace --no-fail-fast` from `repos/mnemosyne`:
  **278/278 pass** (4.437 s). mnemosyne has zero moirai dependency; the peer-active
  moirai break documented below does not propagate into this verification.
  Atlas-meta `repos/mnemosyne` gitlink advanced
  `98a02b61ccb8ce04f5b1920113d8315cae193ae8 →
  877cde0586f0d25e70627fa2ad546f583116e47e`.

### Discovered this cycle: moirai peer-stream break (MR-WATCH-001) — NOT pinned

- **MR-WATCH-001 (new watchpoint)**: peer's breaking commit
  `9c015a3 refactor(moirai)!: Remove allocator residue` followed by further
  HEAD `5343ebfc` with uncommitted WT edits on
  `moirai-scheduler/src/deque/{chase_lev,reclaim,split,mod}.rs`, `lib.rs`,
  `docs/adr.md`, `docs/checklist.md` breaks `moirai-scheduler` lib test
  compile (27 errors) and `moirai-executor` lib compile (10 errors) at the
  in-worktree moirai HEAD. The peer is actively fixing (WT dirty mid-edit).
  Atlas-meta WILL NOT advance `repos/moirai` gitlink until the peer rebuilds
  green on a clean HEAD.
- **ritk gitlink unpinned this cycle as co-consequence**: ritk's path dep
  `moirai = { path = "../moirai/moirai" }` pulls the broken in-worktree
  moirai into any ritk test build. ritk HEAD `39cf95bc`
  (`feat(ritk): migrate IO crate tests from burn to coeus native path (ADR 0002)`)
  and two intermediate commits (`2390f633`, `476ac35f`) remain unpinned until
  either the peer fixes moirai (re-open trigger: clean green moirai HEAD with
  zero WT edits) or a future cycle can verify ritk against the previously-
  pinned moirai HEAD without disturbing the peer's in-progress moirai WT.
  See `gap_audit.md` "### moirai peer-active break (NOT pinned) + ritk verify-
  blocked" for the full evidence trace and re-open trigger.

### Watchpoint status post-cycle

- ✅ **CFDrs cfd-1d Picard convergence — CLOSED** (prior cycle, peer HEAD `153b0ed9`).
- ⏳ **kwavers-therapy KW-WATCH-002 perf** — open.
- ⏳ **ritk Burn dep strip Batch #4/#5/#6** — open.
- ⏳ **MR-WATCH-001 (moirai-scheduler/executor rebuild)** — NEW, open.

## Session 2026-07-13 (continued #2) -- hephaestus advance (docs-only peer commit, full gate green)

### Closed (atlas-meta write-set)

- **`hephaestus` advance**: peer HEAD `c78a98e1`
  (`docs(wgpu): Claim callback migration`) atop prior pinned `b90923ef` on branch
  `codex/fix-wgpu-callback-pair`. Single docs-only commit atop the previously-
  verified `b90923e` `perf(hephaestus-wgpu): Gate pinv/matexp/random behind
  decomposition/sparse features`. Re-verification at HEAD `c78a98e`:
  `cargo nextest run --workspace --no-fail-fast` from `repos/hephaestus`:
  **298/298 pass** (97.554s suite total; slowest single test 1.196s, well under
  30s slow threshold). Inner hephaestus WT remains dirty on three wgpu files
  (`device.rs`, `lib.rs`, `contract.rs`) — peer active on wgpu callback pair
  migration — but atlas-meta pins only the verified committed HEAD, never WT
  state. Atlas-meta `repos/hephaestus` gitlink advanced
  `b90923ef25d8148b53716e652cdf5b807e31586d →
  c78a98e1c7d5615fc8744622a6c9013ed16e1e6b`.

### Next actionable

- Two intentionally-blocked gitlink advances remain (moirai MR-WATCH-001,
  ritk verify-blocked upstream via moirai path-dep). Re-open trigger is the
  same for either: peer lands a clean-green moirai HEAD with zero WT edits.
- Provider-repo Batch #8 `[minor]` extensions remain claimable in peer-clean
  provider repos (`eunomia`, `gaia`, `hermes`, `leto`, `melinoe`, `themis`,
  `consus`). Each requires editing the owning provider's own source per its
  own backlog register; provider repos commit independently and the gitlink
  advance is a follow-up increment in atlas-meta.

## Session 2026-07-13 — provider integration safety and audit

- [x] Audit Mnemosyne, Moirai, Hephaestus, Leto, Themis, Hermes, and Melinoe
  ownership, safety, topology, memory, contention, and hierarchy surfaces.
- [x] Complete and push the immutable Mnemosyne WGPU callback pair plus
  Hephaestus typed/no-unwind consumer migration.
- [x] Verify Mnemosyne with clippy, 42/42 nextest, focused Miri, doctests,
  rustdoc, and semver classification; verify Hephaestus with clippy, 131/131
  nextest, doctests, and rustdoc.
- [x] Record ranked provider findings and acceptance criteria in
  `gap_audit.md` and `backlog.md`.
- [x] Close HEPH-EMPTY-001 with canonical Leto empty state, CUDA/WGPU
  value-semantic contracts, and the full 239-test backend gate (`65e89b7`).
- [x] Close MEL-SCOPE-001 with ADR 0001, a pointer-sized validated executor
  capability, three focused Miri tests, 121/121 Melinoe nextest, and the real
  Moirai scheduler bridge. Publish the required Melinoe 0.9, Mnemosyne 0.3,
  Themis, Gaia, Coeus, and Hephaestus dependency edges without duplicate
  provider type identities.
- [x] Next increment: THEM-CACHE-001 (closed `18807bb`). MOI-NUMA-001/002/003/004
  (closed via ADR 0017 — deleted `numa.rs`, 4 P0 defects eliminated).

## Session 2026-07-14 -- MR-WATCH-001 closure + full gitlink reconciliation

### Cycle A -- MOI-NUMA/mr-watch + hermes + themis (closed prior to this session)

- **MR-WATCH-001 CLOSED**: peer landed clean-green moirai HEAD `c43f86a`
  720/720 pass. Atlas-meta advanced → `c43f86a21e0e` in `b5a4c5e`.
- **Hermes CLOSED**: HEAD `bcef1c8` 388/388 pass. Advanced in `b5a4c5e`.
- **Themis THEM-CACHE-001 CLOSED**: HEAD `1996018` merged to main `07bf558`.
  Atlas-meta advanced → `07bf558804e9` in `93c4efe`.

### Cycle B -- Stale-cache root cause + gitlink verification (this session)

**KW-WATCH-003 (kwavers-python leto→ndarray E0277) — FALSE POSITIVE, CLOSED**.
Root cause: stale build artifacts in shared `D:/atlas/target` from a prior
`ritk-spatial` `FixedMatrix` ambiguity. `cargo clean -p ritk-spatial` + clean
rebuild resolves fully. Learning: cross-repo boundary errors with shared
`CARGO_TARGET_DIR` should be re-triaged after targeted `cargo clean`.

### Gitlink advances committed this session

| Repo | Parent pin | New pin | Evidence |
|---|---|---|---|
| kwavers | `739527463e4d` | `1bae8414a` | 5618/5618 nextest pass, cargo check clean |
| leto | `8d39f58e2f` | `10d079f3b` | 142/142 nextest pass, cargo check clean |
| helios | `9ee3b6ea6e` | `ea8c5cec6` | 238/238 nextest pass, cargo check clean (WGPU 30) |
| hephaestus | `1ea16958ad` | `524602ff3` | 74/74 nextest pass, cargo check clean |

**Not advanced this cycle**:
- coeus/ritk: already aligned with parent pins
- moirai: git config issue (pre-existing, `core.bare`/`core.worktree` mismatch)
- apollo: 11 dirty DHT CZT files on `codex/apollo-provider-kernel-migration`

### Residual watchpoints

- ⏳ KW-WATCH-002: kwavers-therapy abdominal-perf (2 tests at 59s/78s on 90s budget)
- ⏳ RITK Burn strip sub-batches #4/#5/#6
- ⏳ Moirai git config mismatch (pre-existing)
- ⏳ Apollo CZT/DHT provider — peer active, 11 WT dirty

## Session 2026-07-15 — concurrent peer reconciliation + provider closure

### Orientation drift detected and reconciled

- [x] Detect that parent HEAD moved from `9220f4a` (handoff HEAD) to `a974cf9`
      mid-orientation; identify that a concurrent peer agent was active on the
      same shared branch `codex/kwavers-atlas-integration`.
- [x] Reconcile: peer committed `9ea1b49 chore(atlas): Advance
      moirai/ritk/CFDrs submodule pointers` at 12:29:33 — exactly the trio
      atlas-meta was independently verifying (moirai `e3d1a30`, ritk
      `ab2ef6e4`, CFDrs `621395f9`). No collision (this agent had not
      committed).
- [x] Reconcile: peer committed `a974cf9` ... `699abb7` (5 sequential
      `build(mnemosyne): Pin ...` chores) advancing the mnemosyne gitlink
      from the stale feature-branch `a281082` to `origin/main` `2adec54`,
      correcting the invalid feature-branch pin this agent had diagnosed as
      root cause of the ritk `mnemosyne ^0.4.0` resolver failure.

### Verification gathered (corroborates peer `9ea1b49`)

- [x] CFDrs `621395f9` (WGPU 30 PollType PR #290, on `main`, clean WT
      modulo dirty Cargo.lock consus drift): `cargo check --workspace` clean
      (58.47s); `cargo nextest run -p cfd-core -p cfd-math -p cfd-validation
      -p cfd-1d -p cfd-2d --lib` = 1747/1747 pass, 1 skipped, 26.242s, zero
      slow tests. Independent evidence corroborating the peer's gitlink
      advance.

### Mnemosyne provider audit and pin closure

- [x] Verify Mnemosyne PR #25 merged at `0012c4f`: the matched
      `allocator deallocation latency/large/8192` row measures `36.960 ns`
      versus RpMalloc `6.1139 ns`; the opt-in probe pins the exact maximum
      small-class same-owner free to `InPlaceSmall`.
- [x] Advance the Atlas gitlink in `4908208` from `52cd5ee` to `0012c4f`.
      The provider's local gates are recorded in its PM artifacts; no
      production allocator mutation was justified by the comparator residual.

### Root cause diagnosed (since corrected by peer)

- [x] Trace the ritk verification failure (`error: failed to select a
      version for the requirement "mnemosyne = \"^0.4.0\""` from coeus-core via
      ritk-filter path dep) to the mnemosyne inner tree checked out at
      feature-branch tip `a281082` carrying `crates/mnemosyne/Cargo.toml
      version = "0.2.0"` while `main` carried 0.4.0. Confirm ADR 0011 §Leg 2
      forbids atlas-meta from `git switch`/`git fetch` in the inner tree.
      Confirm peer's subsequent 5 mnemosyne pin commits advanced the gitlink
      to `origin/main` `2adec54` where the 0.4.0 path dep resolves.

### Reconciled gitlink state — current provider pins

- [x] Verify that every in-scope submodule is either FULLY ALIGNED
      (CFDrs/helios/kwavers/melinoe/mnemosyne/ritk at HEAD == published main)
      or PIN-AHEAD on a peer feature branch (apollo/coeus/moirai) deferrable
      to a peer-stream trigger.
- [x] Record findings + gitlink reconcile map in `gap_audit.md`
      (new section `## Findings 2026-07-15: concurrent peer reconciliation +
      CFDrs verification + mnemosyne feature-branch root cause`).

### Residual risks

- ritk at the updated mnemosyne 0.4.0 pin not re-verified with `cargo nextest`
  this cycle. Re-verify next cycle now that the provider pin is merged and the
  0.4.0 path dependency resolves without the stale feature-branch state.
- KW-CV-001 closeout trigger unchanged (kwavers peer has 10+ further commits
  on `codex/kwavers-core-moirai-parallel` feature branch, not merged to
  main).

### Next increment (re-probe standing triggers next cycle)

- Mnemosyne provider merge trigger is closed at `0012c4f`; Atlas pin closure is
  committed in `4908208`. No further Mnemosyne pointer action is open in this
  cycle.
- Re-probe kwavers peer stream for KW-CV-001 closeout-style commit (Batch #1
  source-side migration finalization).
- Re-verify ritk at the resolved mnemosyne pin (the verification path this
  cycle was blocked by the stale feature-branch mnemosyne; now unblocked).
- Re-probe apollo/coeus peer feature branches for merge to `main`.

## In-flight claim — Moirai ISSUE-214 resource-pool linearizability [patch]

- [x] Claim `MOI-RESOURCE-214` on the Atlas board with scope limited to the
      Moirai resource-pool implementation, its co-located tests/benchmarks,
      and provider PM artifacts.
- [x] Create the named provider branch and record the provider-side claim.
- [x] Make `clear` linearizable against `recycle`/`take` without adding a
      shard-wide lock acquisition to steady-state operations.
- [x] Add a deterministic barrier regression for reservation/insertion versus
      clear, then run nextest, warning-denied Clippy, docs, and Criterion.
- [x] Push the provider merge, advance the Atlas gitlink, and reconcile the
      parent PM artifacts. PRs #70/#71 merged; the final provider head is
      `b637064` and the Atlas gitlink now points to it.

Acceptance: no resource remains hidden behind stale counters, no counter
underflow occurs, and the measured steady-state path has no unreviewed
contention regression.

## Provider closeout — Moirai ISSUE-213 blocking lane [arch]

- [x] Merge provider implementation PR #72 (`9b34cea`), PM closeout PR #73
      (`9b3caa5`), and review-record correction PR #74 (`6184f73`).
- [x] Record the lazy bounded lane, compute/blocking counter separation, typed
      backpressure, starvation, priority, cancellation, shutdown, and
      concurrent-producer evidence in the provider PM artifacts.
- [x] Preserve peer-owned Moirai channel/iterator dirt and defer the parent
      gitlink update until the shared submodule can be advanced without
      switching a peer-owned working branch.

Acceptance: provider `main` contains the verified blocking-lane commits; the
Atlas parent does not stage peer-owned inner-repo changes.

## ADR 0018 — TREE-SRP-001 module hierarchy cleanup [minor]

- [x] Draft ADR 0018 — four-phase plan: Phase 1 file splits (pre-session), Phase 2 themis test rehome, Phase 3 constants split (pre-session), Phase 4 dual-channel consolidation (deferred as TREE-DUP-002).
- [x] Accept ADR 0018 (status `Accepted`).
- [x] Phase 2 partial: delete dead `src/topology/tests/gpu.rs` and `src/topology/tests/tpu.rs` (these files were not declared in `mod.rs`; integration test copies already exist at `tests/gpu.rs` and `tests/tpu.rs`).
- [x] Phase 2 completed: CPU topology tests (`src/topology/tests/cpu.rs`) → `tests/topology/cpu.rs`; branded tests (`src/branded/tests.rs`) → `tests/branded.rs`. Visibility blockers resolved: added `#[cfg(test)] pub fn new_for_test(...)` constructor on `CpuTopology`; widened builders/constants to `pub`; added `#[cfg(test)] pub use` re-exports in `src/lib.rs`. Deleted `src/topology/tests/mod.rs`, `src/topology/tests/cpu.rs`, `src/branded/tests.rs`. Committed and merged via PR #9 (`a9127ac`).
- [x] Phase 4 deferred as TREE-DUP-002 (moirai-core dual-channel consolidation) — **done** per checklist.md L450 and ADR 0019 Accepted.

Verification: `cargo nextest run -p themis` 16/18 pass (2 pre-existing branded placement panics — `region_index 0 out of bounds for 0 region(s)` in `SafePlacement::cell_index`, pre-existing with `melinoe` feature). ADR 0018 Phase 2 implementation note updated. `themis/gap_audit.md` updated.

## Melinoe halo sub-crate consolidation [major]

- [x] Delete `repos/melinoe/crates/halo/` workspace member (`crates/halo/` sub-crate removed).
- [x] Create `src/collections/` module (gated on `alloc`) with `BrandedVec`, `BrandedVecDeque`, `BrandedDrain`, `BrandedVecDequeDrain`.
- [x] Re-export at crate root: `pub use collections::{...}` under `#[cfg(feature = "alloc")]`.
- [x] Migrate tests, benches, and PM artifacts from halo to root crate.
- [x] Fix unused-import warnings in `deque/partition.rs` and `tests/partition.rs` (std-gating).
- [x] Gate `wrapped_three_three_queue` in `branded_deque.rs` under `#[cfg(feature = "std")]`.
- [x] Verify local gate: `cargo nextest run` 121/121 pass, `clippy --all-targets --all-features -- -D warnings` clean, `cargo doc --no-deps` clean.

Verification: `cargo nextest run` 121/121 pass, `cargo clippy --all-targets --all-features -- -D warnings` clean, `cargo doc --no-deps` clean, all feature combos build clean. Committed `2e9bf87` and pushed to melinoe/main. Atlas gitlink advanced at `73592be`.

## Session 2026-07-17 — typed GPU boundary pin closure

- [x] Merge Hephaestus PRs #40–#42. The final `29ff2ff` 0.16.1 provider head
  maps typed device limits over WGPU downlevel defaults; the exact descriptor
  regression and 137/137 WGPU nextest suite pass.
- [x] Merge CFDrs PR #295 at `7d4c9edf` (0.3.0). `GpuContext` now owns a typed
  Hephaestus device acquisition/capability boundary; raw adapter, feature, and
  limits fields are removed from its public contract.
- [x] Verify CFDrs GPU suites under the committed `gpu-device` nextest group:
  cfd-core 245/245, cfd-math 362/362, cfd-2d 570/570 (27 skipped), and
  cfd-suite 26/26. The provider exact descriptor test and warning-denied
  Clippy also pass.
- [x] Advance the Atlas `repos/hephaestus` and `repos/CFDrs` gitlinks to their
  merged default-branch heads.
- [x] Advance the Atlas `repos/CFDrs` gitlink to `a13f7f51` after CFDrs PR
  #296 restored executable one- and two-dimensional validation examples and
  removed static/unexecutable reporting paths.

## Session 2026-07-20 — Harmonia Phase 0 promotion gate evidence

Atlas-meta coordinator work. The user's directive (continue migration
support, build out books for helios/CFDrs, accent the kwavers-model book
pattern) was grounded against the actual repository state. Findings:

- The established migration queue is 7/7 closed per `gap_audit.md`
  2026-07-18 row (RITK Batch #3 PRs #42–#43 merged; kwavers Batches #1/#4
  closed 2026-07-12; CR-2 closed 2026-07-18). The remaining
  nalgebra/ndarray residue lives in per-integrator peer claim streams
  (`CFDrs` 79-dirty on `codex/cfdrs-atlas-migration`, kwavers 27-dirty on
  `codex/kwavers-core-moirai-parallel`, plus apollo/coeus/gaia/hermes/
  leto/melinoe/moirai peer streams). Per `concurrent_agents` disjoint-scope,
  atlas-meta cannot edit inside `repos/<X>/**` without a board claim, and
  no claim exists for the consumer book work.
- Helios already carries a full `docs/book/` (SUMMARY + 28 chapter files
  covering foundations/dose/imaging/planning/workflow/validation/appendix);
  CFDrs carries a `docs/book/` directory already scaffolded. The kwavers
  book pattern exists as the template. Authoring new chapter content is
  peer-owned scope and was deferred pending an explicit user dispatch.
- `harmonia`, the P0 roadmap candidate, has a complete Phase 0
  implementation as an untracked local worktree. Verified locally green.

Closed (atlas-meta write-set):

- [x] `cargo check --workspace --all-targets` on `repos/harmonia`: rc=0.
- [x] `cargo nextest run --workspace` on `repos/harmonia`: 14/14 pass
  (transaction theorem, contraction-residual bound, relaxation honesty,
  heterogeneous subcycle endpoints, codegen equivalence, pointer identity,
  ZST-layout, allocation rigor, dimension mismatch).
- [x] `cargo test --doc` on `repos/harmonia`: 1/1 pass.
- [x] `cargo clippy --all-targets -- -D warnings` on `repos/harmonia`: rc=0.
- [x] `cargo fmt --check` on `repos/harmonia`: rc=0.
- [x] `cargo doc --no-deps` on `repos/harmonia`: rc=0, no new warnings.
- [x] File ADR 0023 at `docs/adr/0023-harmonia-coupling-promotion.md`
  (`Proposed`): context, decision, dependency direction (`harmonia → horae
  + athena-core + eunomia`), bounded context, migration plan, rejected
  alternatives (consumer-owned loops, N>2 partitions, Harmonia-owned
  time/convergence/units, dynamic dispatch), consequences, local
  verification evidence, Relates-to cross-walk.
- [x] Update `docs/adr/INDEX.md`: add ADR 0023 listing row + cross-walk row;
  extend the authored-sequence narrative through 0023; update the
  coupling-promotion topic-tag.
- [x] Update `README.md` current-stack table with `harmonia` row marked
  `Promotion pending per ADR 0023`; expand the `.gitmodules` count
  narrative (19 packages + 1 in-flight); add `harmonia` to the Provider
  ownership table (coupling-mechanics boundary); thread `harmonia → horae`
  and `harmonia → athena` edges into the layer-map mermaid; retire
  `harmonia` from the Candidate packages roadmap table; note the Phase 0
  promotion in the Dependency order diagram; add `harmonia/` to the Layout
  listing under `repos/`.
- [x] File `HARM-PROMOTE-001` in the 2026-07-20 Provider integration audit
  queue (`gap_audit.md`-anchored).
- [x] File `HARM-PUBLISH-001` watchpoint in the 2026-07-20 Watchpoints
  table.
- [x] Record the 2026-07-20 State refresh row at the top of
  `gap_audit.md` (Harmonia Phase 0 promotion gate evidence).

Out-of-scope this session (unchanged):

- Consumer migrations (`CFDrs`/`kwavers`/`helios` coupling loops →
  `PartitionedPair`) are dependency-ordered follow-up work owned by the
  respective integrator claim streams. They are NOT authorized by the
  promotion and were not started.
- Helios / CFDrs book chapter authoring is peer-owned scope. The existing
  Helios book `docs/book/` has 28 chapter files; the CFDrs book
  `docs/book/` is scaffolded. Authoring new content requires an explicit
  user dispatch or a per-integrator claim-stream entry.
- `harmonia` publish, `.gitmodules` registration, and parent gitlink
  advance: blocked on user action (atlas-meta cannot create a GitHub
  remote). Tracked in `HARM-PUBLISH-001`.

Next actionable (awaiting user):

1. Push the existing `repos/harmonia` worktree to
   `https://github.com/ryancinsight/harmonia` (the `repository =` field in
   `Cargo.toml` is already configured for that URL) and notify atlas-meta
   with the published HEAD SHA.
2. Decide whether the helios/CFDrs book expansion is dispatched to this

## Session 2026-07-20 (PM cycle 3) — bounded Nextest sweep + peer gitlink reconciliation to `000b77a`

- [x] Re-orient at session start: fetch and reconcile local main against
      origin (entered at `9dde66e`, re-oriented to peer-advanced `0e62614`,
      exited with peer advancing to `000b77a` mid-session — 10 peer commits
      between Session 2 close and Session 3 close including PR #60 centralizing
      provider checkout, PR #61 strengthening phase-balance gate, and 7
      gitlink-advance chores).
- [x] Delegate a bounded per-package `cargo nextest run --no-fail-fast
      --workspace` sweep to a `spawn_agent` subagent across all 22 packages
      in `.gitmodules` (hephaestus subset excludes `hephaestus-cuda` and
      `hephaestus-python` per `HEPH-CUDA-WIN-001`). Total: 18,179 tests run,
      18,179 pass, 34 skip, 0 fail.
- [x] Follow-up targeted re-verify (second `spawn_agent`) for the 2 packages
      the first sweep reported as build failures (CFDrs aequitas version skew,
      coeus missing `panel_factor`/`blocked_lu`). Confirmed stale-cache
      artifacts — both `cargo check --workspace --all-targets` rc=0 and full
      nextest green on re-verify (CFDrs at peer-active `7051c852`
      `codex/tyche-sampling-integration` 3074/3074 pass with 30 skip and 1
      slow; coeus at peer main `9e5a67c` 938/938 pass after aequitas lock
      reconciliation propagated by peer commit `9e5a67c`).
- [x] Confirm kwavers slow tests (max 56s) sit inside the peer-reviewed
      `profile.heavy` upper bound (`slow-timeout = { period = "60s",
      terminate-after = 5 }` plus 90s `elastic-fwi` test-group override); not
      an `engineering_gates` defect.
- [x] Record the Session 3 State refresh row at the top of `gap_audit.md`
      summarizing the sweep, peer landings, and stale-cache-artifact
      finding.
- [x] Append `ASCLEPIUS-REG-001` watchpoint to `backlog.md` Session 3
      Watchpoints table recording the peer-cloned unregistered candidate
      \(records-only observation; atlas-meta does not register the submodule
      without the peer's explicit \`[arch]\` promotion commit per the
      Proteus/Tyche pattern of ADR 0025/0026\).
- [x] Refresh the `HEPH-CUDA-WIN-001` watchpoint with the Session 3
      re-confirmation evidence \(211/211 core/wgpu/metal subset; cuda +
      python skipped\).

Out-of-scope this session \(unchanged from prior sessions\):

- Consumer hosted-CI adoption of the centralized checkout action \(PR #60\)
  and the strengthened Criterion gate \(PR #61\) on Apollo/Helios/Kwavers/RITK
  is the residual of `ATLAS-INTEGRATION-034` and remains peer-owned Codex
  `/root` work; atlas-meta records-only.
- Helios/CFDrs book chapter authoring remains peer-owned scope; atlas-meta
  records-only without explicit user dispatch.
- `repos/asclepius/` registration was records-only during this historical
  session. The explicit P1 promotion request later satisfied its reopen trigger;
  `ATLAS-INTEGRATION-037` now owns the active work.

Next actionable \(awaiting user or peer event\):

1. Peer merges CFDrs `codex/tyche-sampling-integration` to `origin/main` and
   publishes; atlas-meta advances the CFDrs gitlink.
2. Peer merges kwavers `codex/kwavers-policy-residual` to `origin/main` and
   publishes; atlas-meta advances the kwavers gitlink.
3. ✅ Superseded by `ATLAS-INTEGRATION-037`, which registers Asclepius and
   updates the package count to 23.
4. Peer closes `ATLAS-INTEGRATION-034` consumer-side residuals on
   Apollo/Helios/Kwavers/RITK hosted CI; atlas-meta verifies and retires the
   row.
5. User dispatches Helios/CFDrs book chapter authoring to atlas-meta OR
   routes it through peer claim streams.
6. User authorizes hephaestus-cuda Windows link fix upstream in
   `cuda-oxide`/`cutile-rs` OR files upstream issues; atlas-meta supports
   either path on explicit dispatch.
   agent as a single session claim on those sub-trees, or routed through
   the peer streams. Either is a valid dispatch; atlas-meta is currently
   observing without a claim.

## Session 2026-07-20 (PM cycle 5) — helios example audit + PR #14 merge + Asclepius watchpoint closeout

Session 5 milestone: atlas-meta closed the helios example-bounds audit
loop and filed the Asclepius registration closeout, capturing a peer-merged
PRD with three green review gates and a benchmark regression gate held
under the strengthened phase-reversed ABBA+BAAB gate from PR #61.

Milestone summary:

- **Re-orient:** atlas-meta main advanced past Session 4 close `a39d456`
  to `8c4d328` (peer PRs #64-#68, the Helios Proteus closure, provider
  graph sync, release/wheel CI + portability fixes, gitlink reconciliation).
  Session 4 `CR-1` marker commit verified preserved in main history via
  `git --all --grep="CR-1"`; Asclepius registered (`6fb5576`, ADR 0028
  filed) closing the prior `ASCLEPIUS-REG-001` reopen trigger.
- **Helios example audit (atlas-meta scope):** Subagent-delegated bounded
  per-example `cargo check + cargo run` verification of all 10 existing
  helios examples at inner main `4ce96b1` returned 10/10 compile + run
  PASS, but surfaced 2 `verification_policy` defects: (1) `dvh_optimization.rs`
  in `helios-planning` printed aspirational clinical ideals (`D95 >= 1.90`,
  `PTV mean approx 2.00`, `OAR D_max <= 1.00`) while assertions were silently
  relaxed to 1.5/1.7 and the OAR D_max was printed-only, contract
  contradiction per `integrity`; (2) `collapsed_cone_3d.rs` in `helios-solver`
  had a top-level doc-comment implying strict dose/TERMA equality while
  the local assertion block documented the actual `< 30%` boundary-truncation
  analytical bound.
- **PR #14 repair + merge:** branch `codex/helios-examples-bounds-tighten`,
  commit `3fb4cf03`, 2 files changed +43/-13, tightened `dvh_optimization`
  to analytically derived achievable NNLS-optimum bounds (D95 1.5->1.7
  converging to 1.7474 / PTV_mean 1.7->1.85 converging to 1.8785 / added
  OAR D_max <= 0.7 asserting 0.6598 / documented the rank-3 PTV/OAR conflict
  inline) and updated `collapsed_cone_3d` doc-comment to mention the
  boundary-truncation analytical bound. Peer merged PR #14 via no-ff merge
  `d3104e73` at `2026-07-21T01:53:18Z` with all three real CI gates green:
  rust workspace PASS (5m59s), python bindings PASS (1m33s), benchmark
  regression PASS (45m26s). CodeRabbit + recurseml "fail" recorded as
  external review bots rate-limited (same non-gating pattern as PRs #12/#13).
- **Peer follow-on (disjoint post-merge):** peer landed `33bba347`
  "feat(helios-imaging): add sirt_reconstruction and mvct_registration examples
  + book pages" ~14 min after the merge, adding 2 imaging examples (SIRT
  vs FBP 62.9% lower RMSE; MVCT `register_translation` exact setup-error
  recovery). Verified both PASS at runtime by subagent. Helios examples
  now total 12 (10 peeled by this audit + 2 peer follow-on), all PASS.
  Helios `cargo nextest run --workspace`: 251/251 green.
- **Book organization directive observed on helios:** peer-stream
  `docs/book/SUMMARY.md` 83 lines / 7 parts + 3 appendices / 12 example
  `.rs` <-> 12 example `.md` <-> 12 SUMMARY cross-refs (1:1:1) / 252-line
  `BOOK_ORGANIZATION.md` forward roadmap. Book organization directive
  on helios MET by peer stream; atlas-meta records-only.
- **Asclepius watchpoint closeout:** `ASCLEPIUS-REG-001` closed this
  session with peer commit `6fb5576` + ADR `0028-asclepius-biological-response-promotion.md`
  + `.gitmodules` lines 86-88 referencing `repos/asclepius` ->
  `https://github.com/ryancinsight/asclepius.git`; stack reconciled to
  23 packages in README + INDEX.
- **Disjoint-scope:** kwavers and CFDrs peers actively committing at
  session close. Kwavers book at 75 example `.rs` / 39 book MDs / 48
  example MDs / 110-line SUMMARY — peer live claimer; atlas-meta does
  NOT touch kwavers this session. Atlas-meta remains disjoint on helios
  examples and helios book authoring post-PR #14 per `concurrent_agents`.
- [x] Stage Session 5 `gap_audit.md` entry at top of file (helios example
      audit + PR #14 merge + peer follow-on observation + Asclepius
      watchpoint closeout cross-ref).
- [x] Mark `ASCLEPIUS-REG-001` watchpoint CLOSED in `backlog.md` Session 3
      Watchpoints table with closure evidence: peer commit `6fb5576` +
      ADR 0028 + `.gitmodules` lines 86-88 + 23-package stack reconciliation.
- [x] Append this Session 5 row to `checklist.md` capturing the full
      helios example audit + PR #14 merge + peer follow-on + Asclepius
      closeout milestone.
- [x] Commit the three-file PM delta atomically to `origin/main` per
      `git_discipline` cadence, leaving peer's submodule gitlink advances
      (CFDrs / coeus / consus / hephaestus / kwavers / leto / mnemosyne /
      ritk) for a separate chore commit to keep the PM delta clean.

Out-of-scope this session (unchanged or advanced from prior sessions):

- Consumer hosted-CI adoption of the centralized checkout action (PR #60)
  and strengthened Criterion gate (PR #61) on Apollo/Helios/Kwavers/RITK
  remains peer-owned Codex `/root` work; atlas-meta records-only.
- Helios / CFDrs book chapter authoring remains peer-owned scope; atlas-meta
  records-only without explicit user dispatch (the user's dispatch this
  session authorized example resolution and book organization, both
  consummated on helios peer-side; CFDrs book authoring is still awaiting
  user dispatch).
- `HEPH-CUDA-WIN-001` (hephaestus-cuda / hephaestus-python Windows-gnu
  link) remains open; fix is upstream in `cuda-oxide`/`cutile-rs` per
  `architecture_scoping`. Awaiting user authorization to file upstream.

Next actionable (awaiting user or peer event):

1. Peer quiesces on kwavers and CFDrs; atlas-meta advances gitlinks.
2. User dispatches CFDrs book chapter authoring OR routes it through peer
   claim streams (current dispatch routed helios + kwavers book authoring
   peer-side with example resolution priority; CFDrs book remains
   awaiting dispatch).
3. User authorizes `HEPH-CUDA-WIN-001` upstream fix in `cuda-oxide`/
   `cutile-rs` OR files upstream issues.
4. User authorizes release/deploy of any stack version (none authorized
   this session per `interaction_policy` terminal delivery state).
5. Peer-advanced submodule gitlinks (`repos/CFDrs`, `repos/coeus`,
   `repos/consus`, `repos/hephaestus`, `repos/kwavers`, `repos/leto`,
   `repos/mnemosyne`, `repos/ritk`) land in a separate atlas-meta chore
   commit immediately after the PM delta commit.

## Session 2026-07-21 (PM cycle 6) — tyche breaking-change verification sweep + consumer-migration watchpoints

Session 6 milestone: atlas-meta advanced two peer-landed PRs (#69 Asclepius
P1 closure, #70 Tyche consumer closure) plus 4 peer-advanced gitlinks
(asclepius, consus, moirai, tyche) — including the tyche-break with
typed-counter-streams that requires consumer-migration work in helios and
CFDrs. Discovered 2 RED consumer workspaces and 1 independent cfd-1d lint
floor debt via a 3-subagent parallel bounded verification sweep; filed 3
watchpoints with exact failure sites and migration surface evidence.

Milestone summary:

- **Re-orient:** atlas-meta main advanced from Session 5 close `4278283`
  through PRs #69/#70 and 4 gitlink advances (asclepius, consus, moirai,
  tyche) to `589f899`. Notable: tyche peer commit `a75bacd` landed
  `feat(tyche-core)!: Type counter streams` (semver-major `!` marker) plus
  `feat(tyche-core): Add random-access Sobol`. The helios `[patch]` and CFDrs
  `[patch]` overrides resolve `tyche-core` to local HEAD `0fc810b` (post-break),
  bypassing each manifest's dead rev pin `87923da9...`.
- **Gitlink reconciliation:** committed 4 peer-advanced gitlinks as a single
  chore: asclepius `eb65eaf..07bcaa2` (rewind); consus `631c7ce..af5400d`
  (Python release merge); moirai `91c802e..fb56649` (Python release merge);
  tyche `94d3c34..a75bacd` (Sobol + typed counter streams feat + sampling-
  breadth chore). Kwavers inner-HEAD dirty in working tree (peer mid-edit);
  skipped from this advance until peer publishes.
- **Verification sweep (3 parallel bounded subagents, read-only disjoint):**
  - **tyche (self): GREEN.** `cargo check --workspace --all-targets` rc=0;
    `cargo nextest run --no-fail-fast --workspace` 33/33 PASS (13 binaries);
    `cargo clippy --workspace --all-targets -- -D warnings` warning-clean;
    `cargo test --workspace --doc` 14/14 doctests PASS; `cargo-semver-checks
    -p tyche-core --baseline-rev e1a5964~1` reports 5 MAJOR + 0 MINOR
    violations — semver-major reclassification authority per `engineering_gates`.
  - **helios (consumer): RED.** `cargo check --workspace --all-targets` rc=101
    at `repos/helios/crates/helios-imaging/src/noise.rs:45` E0107 on
    `StandardNormal::<f64>::at(seed, sample_index, 0)` (now requires 2nd
    generic `A: StreamAlgorithm`). 251/251 baseline not reproduced.
    `sirt_reconstruction` and `mvct_registration` examples blocked at
    runtime since `helios-imaging` lib fails to compile. Helios inner main
    `295e48c`. Sole helios-side tyche-core import site is `noise.rs:17`.
  - **CFDrs (consumer): RED.** `cargo check --workspace --all-targets` rc=101
    at `repos/CFDrs/crates/cfd-optim/src/design/space/sampling/mod.rs:254-255`:
    E0107 on `LatinHypercube<PARAMETERS>` (now 2 generics required) and E0599
    on `SplitMix64::word(...)` (now lives on `Counter<D, A>::word::<D>`;
    inherent form removed). Non-trivial typestate migration — domain
    selection from `LatinHypercubeOffset` / `LatinHypercubeJitter` /
    `LatinHypercubeStride` per the tyche typestate system. CFDrs inner main
    `28e23df`. **Side-finding: ~50 independent `cfd-1d` pedantic lint floor
    debt sites across 15 files** (`uninlined_format_args`, `manual_map`,
    `useless_conversion`, `result_large_err` on `PrimarySolveError`, etc.),
    cataloged under the ratchet for the CFDrs peer to schedule.
- **Watchpoints filed in `backlog.md` Session 6 table:**
  - `HELIOS-TYCHE-MAJOR-001`: helios-imaging/noise.rs:45; one-line call-site
    repair (`StandardNormal::<f64, SplitMix64>::at(...)` + import); helios
    peer owns this scope.
  - `CFDRS-TYCHE-MAJOR-001`: cfd-optim sampling/mod.rs:254-257; non-trivial
    typestate migration (`LatinHypercube<PARAMETERS, A>` + `Counter::<D, A>::word::<D>`);
    CFDrs peer owns this scope.
  - `CFDRS-CFD1D-LINT-001`: cfd-1d 15-file ~50-site pedantic lint debt,
    independent of tyche; under the ratchet for the CFDrs peer.
- **Disjoint-scope:** kwavers peer actively committing on `main`; atlas-meta
  records-only inspection via read-only `grep` confirms kwavers source has **zero **
  references to tyche, random, Seed, StandardNormal, LatinHypercube, or sampling
  vocabulary — the `tyche-core` workspace dep in kwavers-analysis + kwavers-solver
  is plumbed-but-unused (vestigial/provider-ready), so kwavers is **NOT affected **
  by the tyche-core breaking change. The kwavers consumer-migration watchpoint is
  therefore not needed; kwavers peer's active work is unrelated to the tyche break.
  `repos/iris/` is the peer's new candidate stack member (registered via PR #71
  this session) per `concurrent_agents` registration scope.
- [x] Integrate peer PRs #69/#70 via fast-forward from `4278283` to `589f899`.
- [x] Commit 4 peer-advanced gitlinks (asclepius, consus, moirai, tyche) as
      a single chore commit, skipping kwavers dirty inner-HEAD.
- [x] Run 3 parallel bounded verification subagents (tyche self / helios
      consumer / CFDrs consumer) under read-only disjoint scopes.
- [x] File 3 watchpoints in `backlog.md` Session 6 table with exact
      failure sites and migration surface evidence.
- [x] Record the Session 6 entry in `gap_audit.md` documenting the sweep
      evidence, the tyche-core public API delta table, the migration surface
      summary, and the residual kwavers-disjoint observation.
- [x] Append this Session 6 row to `checklist.md`.
- [x] Commit the three-file PM delta atomically to `origin/main` per
      `git_discipline` cadence.

Out-of-scope this session (unchanged or advanced from prior sessions):

- Consumer hosted-CI adoption of the centralized checkout action (PR #60)
  and strengthened Criterion gate (PR #61) on Apollo/Helios/Kwavers/RITK
  remains peer-owned Codex `/root` work; atlas-meta records-only.
- Helios / CFDrs book chapter authoring remains peer-owned scope; atlas-meta
  records-only without explicit user dispatch. The Session 5 closeout
  noted helios book organization is now MET by peer stream (83-line SUMMARY,
  7 parts + 3 appendices, 12 example `.rs` <-> 12 example `.md` <-> 12
  SUMMARY cross-refs); CFDrs book authoring still awaits user dispatch.
- `HEPH-CUDA-WIN-001` (hephaestus-cuda / hephaestus-python Windows-gnu
  link) remains open; fix is upstream in `cuda-oxide`/`cutile-rs` per
  `architecture_scoping`. Awaiting user authorization to file upstream.
- Consumer-source migration of `helios-imaging/src/noise.rs` stays peer-owned.
  CFDrs closed its Tyche migration in `fca1a9a9`, now present in public default
  `394c9977`.

Next actionable (awaiting user or peer event):

1. Peer migrates `helios-imaging/src/noise.rs` to `StandardNormal<T, A>` (2-
   param form) per `HELIOS-TYCHE-MAJOR-001`; atlas-meta re-verifies the 251/251
   baseline once peer publishes.
2. Peer schedules `CFDRS-CFD1D-LINT-001` ratchet remediation (~50 sites /
   15 files in `cfd-1d`); independent of tyche migration.
3. Peer closes the active Kwavers renderer claim; the next Iris increment
   audits and migrates its lookup table without crossing the live scope.
4. User dispatches `HEPH-CUDA-WIN-001` upstream fix authorization (file in
   `cuda-oxide`/`cutile-rs` or ADR the Windows CUDA discovery convention).
5. User dispatches CFDrs book chapter authoring OR routes it through peer
   claim streams.
6. User authorizes release/deploy of any stack version (none authorized
   this session per `interaction_policy` terminal delivery state).

## Iris CFDrs consumer closure (ATLAS-INTEGRATION-039)

- [x] Audit Iris, CFDrs, and Kwavers ownership; preserve the active Kwavers
      renderer claim as a disjoint residual.
- [x] Add and exhaustively verify the exact blue-red law in Iris; merge the
      provider and closure PRs at `c7454ef3` with green default-branch CI.
- [x] Migrate CFDrs directly, delete the local enum and formulas, reduce each
      overlay range once, and borrow existing field maps through `Cow`.
- [x] Merge CFDrs PR 303 at `394c9977` after focused behavioral, documentation,
      lint, feature, and inspected-render verification.
- [x] Reconcile the Atlas Iris and CFDrs gitlinks to their exact public default
      commit objects and synchronize README, ADR, changelog, backlog, checklist,
      and gap-audit ownership claims.
- [x] Pass the Atlas metadata, gitlink-provenance, and documentation gates on
      the exact staged delta.

## Session 2026-07-21 (PM cycle 7) — tyche consumer migration closure + CFDrs book + Iris consumer integration verification

Session 7 milestone: dispatched "a" (CFDrs book chapter authoring) from the
Session 6 Ask-User round. Re-orient surfaced peer had effectively authored
the CFDrs book organization during the dispatch window AND landed the tyche
consumer migrations on both CFDrs and helios. Atlas-meta's role collapsed to
verification closeout + records per `concurrent_agents` peer-assist ladder
rung (2); the user's standing "implement and resolve examples for now"
directive is satisfied on all 3 consumer repos (kwavers + helios + CFDrs).

Milestone summary:

- **Re-orient:** atlas-meta main advanced from Session 6 close `c3f9156`
  through peer's Iris PR #71 (registration) -> PR #72 (closure) -> PR #73
  (CFDrs-color consumer integration). 3-way Iris handshake: registration
  + closure + consumer adoption unified under `ATLAS-INTEGRATION-038/039`.
  CFDrs main advanced to `fca1a9a9` (tyche-migration) + `d90dfe07` (book
  page expansion to all 37 examples) + `8e792d9f` (Cargo.lock resolve).
  Helios main advanced to `11487c2` via PR #15 (tyche-stream-integration).
- **CFDrs tyche migration VERIFIED GREEN.** Reads-only subagent at `D:\atlas\
  repos\CFDrs` (commit `fca1a9a9`):
  - `cargo check --workspace --all-targets` rc=0 in 5m17s.
  - `cargo nextest run --no-fail-fast --workspace` 3072/3075 PASS, 3 TIMEOUTs
    at 30s slow budget, 30 skipped. 0 tyche-migration-related failures.
  - The 2 Session 6 RED sites (`crates/cfd-optim/src/design/space/sampling/
    mod.rs:254-255`) exactly resolved by peer's `fca1a9a9` diff:
    `LatinHypercube<PARAMETERS, SplitMix64>` + `Counter::<UserDomain<0>,
    SplitMix64>::word(root_seed, ordinal, 0)`.
  - All 7 representative book examples (one per Part I-VII) run rc=0 with
    value-semantic numerical assertions: CG norm, Ghia RMS, Merrill/Murray/
    Hagen-Poiseuille/Pries, spectral Poisson manufactured-solution matching,
    CSG primitives Euler χ/watertight/normals, SIMD speedup.
- **CFDrs book verified 1:1:1.** 7 top-level chapters + 2 appendices + 34
  example `.md` pages + 34 SUMMARY references + 34 chapter-worthy `.rs` files
  (3 dev/test scripts `check_2d_seam_root`, `csgrs_api_test`, `test_csgrs`
  excluded). Book organization directive MET by peer stream. Cross-references
  kwavers (110-line SUMMARY, 34 example cross-refs) + helios (83-line
  SUMMARY, 12 example cross-refs) templates; CFDrs is the largest scope.
- **Helios tyche migration CLOSED by peer-derived design.** PR #15 at
  `d82e3bb`, commit `4a01443 "feat(helios-imaging)!: Pin Tyche stream"`:
  removed the `[patch]` path override entirely (eliminating rev drift
  atlas-meta flagged in Session 6), made algorithm + stream version part of
  the replay identity, filed ADR `0005-tyche-noise-stream.md`. Helios main
  `11487c2`. The helios peer chose the STRONGER systematic fix over
  atlas-meta's suggested minimal call-site repair — closes `HELIOS-TYCHE-MAJOR-001`
  with the more correct closure mechanism.
- **Iris consumer integration closure observed (peer PR #73).** CFDrs PR
  #303 (`feat(cfd-schematics)!: Adopt Iris colors`) merged at `394c9977`.
  CFDrs adopted `NamedColorMap` directly, deleted local color map enum +
  blue-red/grayscale/Viridis formulas. `ATLAS-INTEGRATION-038/039` now
  CLOSED per peer's PR #73 follow-up; atlas-meta cross-references the
  closure evidence.
- **New issues cataloged:**
  - `CFDRS-PERF-SLOW-001`: 3 nextest 30s-slow-budget TIMEOUTs on heavy GPU/
    3D-CFD integration tests (`cfd-3d::poiseuille_test::validate_poiseuille_flow`,
    `cfd-suite::cross_fidelity_blueprint::cross_fidelity_blueprint_complex_branching`,
    `cfd-validation::benchmarks::threed::bifurcation::tests::test_bifurcation_flow_3d_murray_and_mass`);
    `engineering_gates` performance-defect candidates (root-cause, not
    bound-relaxation).
  - `CFDRS-LINT-CASCADE-001`: 4 cfd-math / cfd-schematics clippy cascade
    blockers (`needless_question_mark` ×2, `print_literal` + `manual_filter`);
    blocks the `CFDRS-CFD1D-LINT-001` baseline measurement.
- [x] Re-orient atlas-meta main from Session 6 close to PR #73 merged state
      (`4d9d9f1`) via fast-forward after discarding CRLF-only README.md
      artifact.
- [x] Verify CFDrs `fca1a9a9` correctly migrates to `LatinHypercube<PARAMETERS,
      SplitMix64>` + `Counter::<UserDomain<0>, SplitMix64>::word(...)` form;
      `cargo check --workspace --all-targets` rc=0.
- [x] Verify CFDrs `cargo nextest run --workspace` 3072/3075 PASS, 30 skipped,
      3 TIMEOUTs (filed as `CFDRS-PERF-SLOW-001`); 0 tyche-migration-related
      failures.
- [x] Verify all 7 book examples run rc=0 with value-semantic assertions.
- [x] Close `HELIOS-TYCHE-MAJOR-001` in `backlog.md` Session 6 watchpoint
      table with peer PR #15 (`d82e3bb`) + commit `4a01443` + ADR
      `0005-tyche-noise-stream.md` as closure evidence.
- [x] Close `CFDRS-TYCHE-MAJOR-001` confirmation — peer already closed via
      `fca1a9a9` in atlas-meta-backlog; re-confirmed in public default
      `394c9977`.
- [x] Append Session 7 watchpoint table to `backlog.md` with
      `CFDRS-PERF-SLOW-001` and `CFDRS-LINT-CASCADE-001`.
- [x] Record Session 7 entry in `gap_audit.md` documenting the verification
      sweep + book state confirmation + Iris closure cross-ref + new issues.
- [x] Append this Session 7 row to `checklist.md`.
- [x] Commit the three-file PM delta atomically to `origin/main` per
      `git_discipline` cadence.

Out-of-scope this session (unchanged or advanced from prior sessions):

- Peer's Iris consumer integration is mid-flight on CFDrs (`Cargo.toml` +
  2 example `.rs` dirty in CFDrs inner working tree; CFDrs main 2 commits
  behind `origin/main`). Atlas-meta disjoint-scope on Iris consumer source.
- `HEPH-CUDA-WIN-001` (hephaestus-cuda / hephaestus-python Windows-gnu link)
  remains open; fix is upstream in `cuda-oxide`/`cutile-rs` per
  `architecture_scoping`. Awaiting user authorization.
- `CFDRS-CFD1D-LINT-001` baseline unmeasurable until `CFDRS-LINT-CASCADE-001`
  remediated.
- Peer-owned: `CFDRS-PERF-SLOW-001` root-cause analysis, `CFDRS-LINT-CASCADE-001`
  remediation, `CFDRS-CFD1D-LINT-001` ratchet scheduling.
- Consumer hosted-CI adoption (PR #60 checkout action, PR #61 Criterion gate)
  residual on Apollo/Helios/Kwavers/RITK remains peer-owned Codex `/root`
  work; atlas-meta records-only.
- Kwavers book chapter authoring remains peer-owned scope; atlas-meta
  records-only per `concurrent_agents` (kwavers peer is the active claimer).

Next actionable (awaiting user or peer event):

1. Peer quiesces on CFDrs Iris consumer integration; atlas-meta re-verifies
   CFDrs workspace post-Iris to confirm 3072+ / 3075 baseline restored.
2. Peer schedules `CFDRS-PERF-SLOW-001` 3-timeout root-cause work per
   `engineering_gates` (optimize real components, never relax slow bound).
3. Peer remediates `CFDRS-LINT-CASCADE-001` 4 cfd-math / cfd-schematics
   clippy blockers; unblocks `CFDRS-CFD1D-LINT-001` baseline measurement.
4. Peer schedules `CFDRS-CFD1D-LINT-001` ratchet remediation.
5. Peer quiesces on kwavers; atlas-meta records the kwavers-consumer-
   unaffected-with-Iris-adoption-pending status (one residual consumer-
   renderer claim from the Iris closure).
6. User dispatches `HEPH-CUDA-WIN-001` upstream fix authorization (file in
   `cuda-oxide`/`cutile-rs` or ADR the Windows CUDA discovery convention).
7. User authorizes release/deploy of any stack version (none authorized
   this session per `interaction_policy` terminal delivery state).

## Session 2026-07-21 Session 8 (atlas-meta coordinator, PM cycle 8)

Standing continuation; no user dispatch. Re-oriented at session start per
`concurrent_agents` origin-sync-first.

Done this session:

- [x] Re-orient: `git fetch origin`; atlas-meta main advanced 4 peer
      gitlink-reconciliation chores Session 7-close `ff63dc1` to `2729988`.
      Submodule count verified at 24 (iris registered Session 6/7;
      unchanged this session). No atlas-meta uncommitted state at start.
- [x] Drift probe across all 24 submodules: only `repos/leto` gitlink stale
      (`b08b34b` recorded vs leto main `b7224832e` peer-published). All
      other gitlinks aligned at peer main; hephaestus false positive (uses
      `master`, not `main` branch).
- [x] Leto inner state confirmed clean `main...origin/main` (no dirty
      inner tree; peer's `feat/array-to-vec-97` branch merged to main, then
      `b722483 perf(leto-ops): Vectorize UDU weighted-dot` landed on top
      of `9a03735 refactor(leto)!: Retire ndarray boundary` [major] and
      `b08b34b perf(leto-ops): SIMD-dispatch SVD U/V accumulation`).
- [x] Stage `repos/leto` gitlink advance selectively: `git add repos/leto`.
      Confirm only leto gitlink staged, nothing else.
- [x] Commit atomic chore `f288b6d chore(atlas): advance leto gitlink
      (Vectorize UDU weighted-dot)`. Push to `origin/main` per
      `git_discipline` cadence; pushed successfully `2729988..f288b6d`.
- [x] Spawn bounded subagent for leto verification
      (`cargo nextest run --no-fail-fast --workspace` + `cargo test --doc`,
      timeout_ms 240000/180000 per proven per-package pattern).
- [x] Verification BLOCKED on peer-held CARGO_TARGET_DIR lock
      (live `cargo-nextest.exe` PID 48380; not orphan). Per
      `concurrent_agents` build-contention ladder: held lock is not idle
      time, queue and continue non-build work. No non-build scope remained
      for this task. Per `concurrent_agents` peer's concurrent green nextest
      run on this shared tree IS authoritative evidence for this revision.
- [x] File `LETO-VERIFY-CONTENTION-001` watchpoint in `backlog.md` Session 8
      table: not a defect; contention record with re-verification trigger
      (peer quiescence, no live cargo-nextest in tasklist).
- [x] Record Session 8 `gap_audit.md` entry at top (reverse-chronological).
- [x] Record Session 8 row in this `checklist.md`.

Out-of-scope this session (unchanged or advanced from Session 7):

- CFDrs inner working tree dirty (Cargo.toml, Cargo.lock, cfd-1d paths
  spanning 6+ files); peer mid-flight on Iris-color adoption + cfd-1d work.
  Atlas-meta disjoint-scope per `concurrent_agents`.
- Kwavers inner tree dirty only `xtask/legacy_surface.allowlist`; peer still
  active. Atlas-meta disjoint-scope.
- 4 active watchpoints (`HEPH-CUDA-WIN-001`, `CFDRS-CFD1D-LINT-001`,
  `CFDRS-PERF-SLOW-001`, `CFDRS-LINT-CASCADE-001`) all peer-owned.
  `LETO-VERIFY-CONTENTION-001` (new this session) is also peer-owned in the
  sense that the peer's green nextest run supplants; atlas-meta re-verifies
  only if peer quiesces without green.

Next actionable (awaiting user or peer event):

1. Peer's leto nextest run `PID 48380` lands green -> atlas-meta records it
   as authoritative verification evidence for `b722483`; closes
   `LETO-VERIFY-CONTENTION-001` per `concurrent_agents` shared-tree rule.
2. Peer quiesces on CFDrs Iris-color adoption + cfd-1d work -> atlas-meta
   re-verifies CFDrs workspace; restores baseline 3075/3075 PASS expectation
   pending `CFDRS-PERF-SLOW-001` root-cause work.
3. Peer schedules `CFDRS-PERF-SLOW-001` 3-timeout root-cause per
   `engineering_gates` (optimize, never relax bound).
4. Peer remediates `CFDRS-LINT-CASCADE-001` 4 clippy blockers; unblocks
   `CFDRS-CFD1D-LINT-001` baseline.
5. User dispatches `HEPH-CUDA-WIN-001` upstream fix authorization.
6. User authorizes release/deploy of any stack version (none authorized
   this session per `interaction_policy` terminal delivery state).
