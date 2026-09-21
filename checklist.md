# atlas — cross-repository integration checklist

<!-- Compacted 2026-09-21 under the 1,000-line board budget: a board is a queue, never a ledger, so closed sections and delivery narrative are gone -- the record of a closed item is the PR that closed it and its `Item:` trailer. Live items, open checkboxes, anchors and open-marked findings are kept. Recover removed narrative with `git log -p -- <this file>`. -->

## ATLAS-ARES-PROMOTION-2026-09-03 [arch][minor]

Board: [`#ares-promotion`](backlog.md#ares-promotion). Charter:
[ADR 0057](docs/adr/0057-ares-phase-0-charter.md).

Prerequisites (not Ares work; block A3 onward):

- [x] CFDrs deletes its elastic copy and composes `proteus::IsotropicSolid` (`f063be4b` on CFDrs main; follow-up `7dcf7726` tests relay fidelity).
- [x] Kwavers deletes `lame_from_speeds` and delegates constructors to `proteus::elastic::IsotropicModuli` (`ab9ddf8fb` / `1f86a9172` on kwavers). Residual: `computed.rs` still hosts the six derived formulas that Proteus also owns — tracked under the peer elastic claim, not a blocker for Ares.
- [x] `aequitas` stress semantics marker lands (`#50` merged 2026-09-04).

Creation:

- [ ] Verify `ares-solid` is available on crates.io **before** creating the repository; if taken, choose the registry name and record it in ADR 0057 before any commit references it.
- [x] **Ask-User:** create `ryancinsight/ares`.
- [x] Scaffold: `[lib] name = "ares"`, edition 2024, MSRV floor matching the stack, `#![forbid(unsafe_code)]`, `#![deny(missing_docs)]`, pedantic floor with `unwrap_used`, `.config/nextest.toml` at the committed 30s/60s budgets, `rust-toolchain.toml` pinned, committed `Cargo.lock`, `deny.toml` with the ADR 0055 prohibition list, `.gitattributes` LF, tracked `.githooks`, CI via the shared reusable workflow, README, CHANGELOG, `docs/adr/` with a generated index.
- [x] Confirm the scaffold passes the full gate and the conformance scan before any physics lands — a repository that starts below the floor never reaches it.

Implementation, each step complete-and-verified before the next:

- [x] A3 kinematics — symmetric tensors, invariants, small strain. Oracle: rigid-body motion gives exactly zero strain.
- [x] A4 constitutive coupling — isotropic Hooke over `IsotropicModuli`, Cauchy stress, von Mises, principal stresses. Oracle: closed-form stress from a known `(E, nu)`. Assert no material constant appears anywhere in `ares`.
- [x] A5 FEM assembly — linear simplices, isoparametric mapping, quadrature, Dirichlet and Neumann conditions, Athena assembly. Oracle: **patch test exact to machine precision**, plus hand-computed element matrices.
- [x] A6 solve and end-to-end — thick-walled cylinder against Lame; cantilever tip deflection; manufactured solution; `O(h^2)` L2 convergence; strain energy equals external work. Every oracle at `f32` and `f64`.

Registration and delivery:

A0-A6 delivered 2026-09-04 through `ares` `f8cb9eb`; `ares` is now a workspace
(`crates/ares` + `crates/ares-operator`, ares ADR 0001), so A7's architecture
test asserts the two-crate edge set. CI and hooks are absent from the
repository and are tracked separately at `#ares-ci-floor`, which blocks A7.

- [x] A7 register: `.gitmodules`, stack table, naming table (move `ares` out of provisional), roadmap, dependency order, suite-coverage row, architecture test edge set, package count. One delivery unit.
- [x] A8 first consumer: CFDrs FSI structural side across Harmonia, traction in and displacement out per ADR 0050. Oracle: interface work conserved.
- [ ] A9 **blocked, not on authority:** publish `ares-solid`. The dependency chain is unpublished - `cargo publish --dry-run` fails on `proteus-mat` missing from crates.io - so release authority is not the binding constraint. Re-open when `proteus-mat` publishes.

## ATLAS-PROMETHEUS-PROMOTION-2026-09-03 [arch][minor]

Board: [`#prometheus-promotion`](backlog.md#prometheus-promotion). Charter:
[ADR 0058](docs/adr/0058-prometheus-phase-0-charter.md).

- [x] P0 prerequisite: `aequitas` gains `ReactionRate` and `MolarFlux` (aequitas `#50` merged 2026-09-04).
- [x] Verify `prometheus-kinetics` availability on crates.io (404; bare `prometheus` remains the metrics client at 200).
- [ ] **Ask-User:** create `ryancinsight/prometheus`. Local tree exists at `repos/prometheus/` with no remote and no commits yet.
- [x] P1 scaffold floor (local): `[lib] name = "prometheus"`, edition 2024, MSRV 1.95 / toolchain 1.97.0, `forbid(unsafe_code)`, `deny(missing_docs)`, pedantic + unwrap/print/dbg floor, nextest 30s/60s, `deny.toml` ADR 0055 bans, README, CHANGELOG, committed-ready `Cargo.lock`. CI/hooks deferred to the first push after remote creation (same shape as ares `45f3eec`).
- [x] P3 species and stoichiometry (local, uncommitted): `Species` + `Concentration` boundaries; sparse `StoichiometricMatrix` over Leto COO; oracle `transpose(nu) * M = 0` exact at `f32`/`f64` on water formation. Gate: fmt, clippy `-D warnings`, nextest 9/9, doc `-D warnings`, `--no-default-features` check (species/concentration only).
- [ ] P4 rate laws — mass-action at arbitrary order, equilibrium constants, reverse-rate consistency, Arrhenius through `proteus::TemperatureResponse`. Oracle: first- and second-order closed forms; `ln k` against `1/T` recovers `Ea` and `A`. Assert no temperature response is implemented in `prometheus` (ADR 0055 R4).
- [ ] P5 net production and reaction enthalpy against hand-computed networks.
- [ ] P6 0-D integration through Horae including the stiff path. Oracles: equilibrium reaches `K_eq`; **Robertson benchmark against published values**; mass conserved; no negative concentrations; integrator order recovered. These are mandatory — stiff kinetics fail in ways smooth-case tolerance checks do not reveal.
- [ ] P7 register in atlas, as A7.
- [ ] P8 first consumer: Kwavers sonodynamic species kinetics under an acoustic dose field, across Harmonia.
- [ ] P9 **Ask-User:** publish `prometheus-kinetics`.

Standing checks for both repositories:

- [ ] No `nalgebra`, `ndarray`, `rayon`, or `num-traits` in either dependency graph; enforced by `deny.toml` bans, not by review.
- [ ] Generic over `T: RealField`; every oracle instantiated at `f32` and `f64`.
- [ ] Every physical value on a public boundary is an `aequitas` quantity.
- [ ] No dependency on an integrator or on another balance domain; coupling only through Harmonia. Asserted by the architecture test.

## ATLAS-WINDOW-ACCELERATOR-INCOMPLETE-2026-09-03 [arch][patch]

- [x] Move the shared `WindowConfiguration` contract to `coeus-hephaestus` and update the WGPU and CUDA consumers without compatibility shims.
- [x] Verify the Hephaestus provider contract and Coeus WGPU/CUDA compile paths, including the CUDA bindgen/toolchain failure. Hephaestus window commits `4355571`/`108db9f`; Coeus `c19923d8`; CUDA nextest 118/118 and WGPU nextest 142/142 pass on the local hardware/runtime.
- [ ] Reconcile the root gitlink and collect the published PRs when the shared index is clear; Hephaestus [#266](https://github.com/ryancinsight/hephaestus/pull/266) merged as `b0988107b795310dda416609e856864819925e0c`. Coeus [#363](https://github.com/ryancinsight/Coeus/pull/363) remains open pending WGPU, CUDA, and Tests completion; external `recurseml/analysis` is failed without a diagnostic.

## ATLAS-APOLLO-BENCH-COMPILE-PROFILE-2026-08-26 [ci][perf]

- [x] Attribute the local Apollo >180s validation signal to the expensive release-profile benchmark artifact build path.
- [x] Change only benchmark executable compilation from `release` to the existing `bench-quick` profile (`codegen-units = 16`, LTO disabled).
- [x] Keep benchmark execution, smoke limits, counterbalanced measurements, and production release profile semantics unchanged.
- [x] Verify workflow assertions, `git diff --check`, and Apollo lock guard (`36` first-party sources) pass.
- [ ] Measure hosted compile duration and benchmark-result stability at the next exact provider head before considering further CI changes.

> This reduces compile work without sleeping, retrying, raising timeouts,
> changing workloads, or changing production/runtime memory behavior.

## ATLAS-PROVIDER-HEAD-ADVANCE-2026-08-26-R4 [integration][perf]

- [x] Re-scan all nested Cargo.lock files with a path-safe inventory after overlay cleanup exposed reverted pins.
- [x] Synchronize stale Apollo references in Asclepius, Athena, CFDrs, Helios, Kwavers, and Ritk to Apollo `94aabac6`; all six guards pass with `41/35/64/59/91/51` first-party sources.
- [x] Preserve active Apollo batched-kernel source edits and the peer-owned Hephaestus lock change.
- [x] Re-run `git diff --check` successfully.
- [ ] Collect hosted full-workspace timing and provider-head confirmation.

> No sleeps, retries, timeout increases, workload changes, allocator changes,
> or production memory-policy changes were introduced.

## ATLAS-PROVIDER-HEAD-ADVANCE-2026-08-26-R3 [integration][perf]

- [x] Recheck current heads: Apollo `94aabac6`, Hermes `15c1958`, Leto `785debb`, and Hephaestus `bef4b4a`.
- [x] Detect and repair stale Apollo/Coeus provider locks without touching peer-owned provider lock work.
- [x] Verify Apollo and Coeus lock guards: `36` and `41` first-party sources.
- [x] Confirm Coeus core/autograd/ops compile in `1m49s`.
- [x] Bound Apollo FFT/NUFFT compilation at `180s`; it exceeded the bound. Existing all-feature test coverage and timeout policy were retained.
- [ ] Collect hosted timing/profile attribution before changing Apollo build partitioning, codegen settings, or test scope.

> No sleeps, retries, timeout increases, workload changes, allocator changes,
> or production memory-policy changes were introduced.

## ATLAS-PROVIDER-HEAD-ADVANCE-2026-08-26-R2 [integration][perf]

- [x] Confirm current provider heads: Apollo `94aabac6`, Hermes `15c1958`, Leto `785debb`, and Hephaestus `bef4b4a`.
- [x] Identify stale, non-peer-owned consumer locks: Apollo and Coeus were behind on provider revisions; Hephaestus's active Hermes lock change was preserved as peer-owned.
- [x] Repin Apollo and Coeus to the current four-provider heads without Cargo regeneration or feature/workload changes.
- [x] Verify Apollo and Coeus lock guards: `36` and `41` first-party sources, both resolving under `--locked`.
- [x] Verify Coeus focused compile: core/autograd/ops completed in `1m49s`.
- [x] Bound Apollo compile validation at `180s`; it exceeded the bound, so no unmeasured profile or timeout change was introduced. Track Apollo's compile graph as the next optimization target.
- [ ] Collect hosted CI timing and full-workspace confirmation at these heads.

> No sleeps, retries, workload changes, timeout increases, allocator changes,
> or production memory-policy changes were introduced.

- [x] Confirm current merged heads: Apollo `ff8f95eb`, Hermes `c0cb8f7d`, Leto `98486ebd`, and Hephaestus `b9ace296`.
- [x] Inventory direct consumer locks and repin Apollo/Hermes entries, including Kwavers and URL variants; retain Leto/Hephaestus pins where already current.
- [x] Validate provider and consumer surfaces with bounded local checks: Hermes benchmark target plus `types_tests` 28/28, Leto 128 + 187 + 8 core/assignment/layout tests, Apollo FFT/NUFFT check, and Hephaestus core/WGPU check all pass.
- [x] Run standalone lock guards for Apollo, Leto, Hephaestus, CFDrs, Coeus, Asclepius, Athena, Helios, Kwavers, and Ritk; all pass with first-party sources.
- [x] Keep Cargo overlay-generated path churn out of portable locks; preserve the peer-owned Hermes benchmark lock changes and active Leto/Hephaestus worktree changes.
- [ ] Collect terminal hosted CI evidence after the moving provider heads are consumed by their pipelines.

> No sleeps, retries, workload changes, timeout increases, allocator changes,
> or production memory-policy changes were introduced.

## ATLAS-LETO-HEPHAESTUS-CONSUMER-REPINS-2026-08-26 [integration][perf]

- [x] Confirm current merged provider heads: Leto `98486ebd` and Hephaestus `b9ace296`, with Hermes `bbc7bdb5` and Apollo `be10c9f2` retained.
- [x] Inventory direct consumer lockfiles and advance stale Apollo, Hermes, Leto, and Hephaestus source revisions, including URL variants.
- [x] Regenerate Gaia's lockfile outside the Atlas overlay; retain the Loom-enabled transitive resolution and verify `22` first-party sources.
- [x] Compile focused surfaces against the live overlay: Gaia, Leto, Hephaestus, CFDrs, and Coeus all pass.
- [x] Run standalone lock guards for all nine affected repositories; all exit `0` with source counts `64/41/36/41/35/59/33/30/51`.
- [x] Restore Cargo-generated local-path churn before the final guard sweep; no workload, feature set, timeout, retry, sleep, allocator, or production memory behavior changed.
- [ ] Collect terminal hosted full-workspace CI evidence after the moving provider heads are consumed by their pipelines.

> Execution steps only. Priority, scope and acceptance oracles live in
> `backlog.md`; this file carries owner-local tactics and never restates them.

## ATLAS-CFDRS-SCHEMATICS-LAYOUT-ALLOCATION-2026-08-26 [perf]

- [x] Audit automatic schematic layout grouping and identify the nested `Vec<Vec<usize>>` allocation path.
- [x] Replace per-depth index buckets with flat depth counts and row cursors; preserve authored-order placement and all existing coordinates.
- [x] Verify the indexed layout and blueprint materialization tests: `1/1` each passed; formatting and diff checks pass.
- [ ] Collect a controlled allocation/runtime comparison on the hosted or instrumented path before claiming a numeric speedup.

> Execution steps only. Priority, scope and acceptance oracles live in
> `backlog.md`; this file carries owner-local tactics and never restates them.

## ATLAS-HERMES-NUMA-GEN-ISOLATION-2026-08-26 [test]

- [x] Reproduce the shared-process failure mode: the test compared a process-global generation counter across an unrelated allocation window.
- [x] Isolate the contract body in a child test process using an environment marker; preserve the allocation-neutrality, deallocation-invalidation, manual-bump, and concurrent-cache assertions.
- [x] Run the focused Hermes test: `1 passed` with parent and child completing in `0.01s`; no sleep, retry, timeout, runner, allocator, or production cache behavior changed.
- [ ] Collect terminal hosted full-suite evidence at the current Hermes head.

> Execution steps only. Priority, scope and acceptance oracles live in
> `backlog.md`; this file carries owner-local tactics and never restates them.

## ATLAS-PROVIDER-API-REPINS-2026-08-26 [integration]

- [x] Confirm tracked Apollo `be10c9f2` and merged Hermes `bbc7bdb5` expose the current capability-argument `LaneKernel::call(self, simd)` contract.
- [x] Inventory direct consumers and stale lock revisions across the Atlas Rust repositories; no downstream `LaneKernel` implementation requires a source migration.
- [x] Repin Apollo/Hermes entries in the nine affected consumer lockfiles to Apollo `be10c9f2` and Hermes `bbc7bdb5`: Apollo, CFDrs, Coeus, Asclepius, Athena, Helios, Hephaestus, Leto, and Ritk.
- [x] Run standalone lock guards for all affected consumers; every guard exits 0 and reports first-party Git sources.
- [x] Compile focused package surfaces against the live Atlas overlay; CFDrs trifurcation tests pass `2/2`, and Asclepius, Athena, Coeus, Helios, Hephaestus, Leto, and Ritk checks pass.
- [ ] Complete hosted full-workspace verification after the provider pins are consumed by CI; no timeout, workload, numerical assertion, or feature budget was changed in this migration.

> Execution steps only. Priority, scope and acceptance oracles live in
> `backlog.md`; this file carries owner-local tactics and never restates them.

## ATLAS-KWAVERS-IGNOREDORACLE-2026-08-22 — current session

- [x] Confirm `KW-GAP-2026-08-20-IGNOREDORACLE` (#5) is the next unowned ordered item and is group-splittable (GPU / budget / PINN / interop / Marchenko).
- [x] Enumerate all 46 `#[ignore]` sites (49 attributes minus 3 doc-comment mentions) with the annotated test and reason; flag the 3 bare ones.
- [x] Measure every budget-group and PINN test locally under the `heavy` profile (serial, 300 s cap): 10 of the ignores were stale — the tests run in 0.6-25 s. Measured: kuznetsov linear 11.8 s; KZK diffraction 6.5 s; PINN ×3 ~20 ms (5/5 stable); probe_coated 3.7 s; multi_bowl 0.6 s; NL-SWE convergence 0.8 s; swe literature 17.5 s; swe scaling 25.4 s; photoacoustic benchmark 1.5 s (failed its underived 1 s threshold). Genuinely heavy: kuznetsov nonlinear 162 s, absorption 42 s, nl_swe_workflow 55 s.
- [x] Re-enable the 10 stale ignores in the default suite; derive the photoacoustic budget (6 s = 4× measured release 1.18 s) at the assertion; route the CPU-saturating re-enabled tests through the `full-grid-sim` nextest group (default + ci overrides).
- [x] Move the 3 heavy tests to the reviewed `heavy` profile with derived 300 s budgets + re-enable triggers; add the `heavy-validation` ci.yml job running them via `--run-ignored ignored-only` (pinned actions, permissions + timeout, mirroring existing job conventions; lane ci.yml rebuilt from origin/main to exclude the main checkout's unrelated SHA-pin overlay).
- [x] GPU group (27): upgrade every `#[ignore]` to carry a reason + trigger; add scheduled `gpu-parity.yml` on `[self-hosted, linux, x64, cuda]` running them nightly via `--run-ignored` (YAML validated).
- [x] Re-run the swe_3d volumetric oracles: two real correctness divergences surfaced (background reconstruction error 1648% vs <30%; stiffness above fibrosis range) — documented in the ignore reasons and tracked as `KW-GAP-2026-08-22-SWERECON` in the kwavers backlog; Marchenko tracked as `KW-GAP-2026-08-22-MARCHENKO` with ADR 019 status note.
- [x] Final state: 36 remaining ignores, zero bare, every one with a reason + re-enable trigger.
- [x] Run provider gates on the lane: fmt clean; check pass; clippy `--lib -D warnings` clean; nextest physics+therapy+transducer 2314/2314, solver 904/904, kwavers 534/534, gpu 9/9; workflow YAML validated. Cargo.lock overlay drift and regenerated test-figures restored.
- [x] Commit at `443421028` (21 files, +217/-61), publish branch `fix/kwavers-ignoredoracle-rehome` and open Kwavers [PR #609](https://github.com/ryancinsight/kwavers/pull/609) at exact head `443421028fa86cbeab4cf6632ee9b22902534384`; `MERGEABLE` on open.
- [ ] Collect hosted terminal checks at the exact PR head (incl. the new heavy-validation job), then merge and advance the Atlas kwavers gitlink; also confirm a self-hosted CUDA runner is registered for kwavers so the scheduled gpu-parity job can run.

## ATLAS-KWAVERS-ALLOC-PROBE-DENY-DOCS-2026-08-21 — current session

- [x] Select `kwavers-alloc-probe` as the pilot crate: single-file crate (no submodules) with every public item already documented.
- [x] Create clean lane `worktrees/kwavers-deny-docs` from fetched `origin/main` `377a98c8`.
- [x] Add `#![deny(missing_docs)]` after the existing `#![doc = include_str!("../README.md")]` attribute — one line, zero source changes beyond the directive.
- [x] Run provider gates: format, check, clippy (`-D warnings`), nextest (0 tests), doctests (1 ignored), rustdoc — all pass on the clean lane.
- [x] Publish branch `fix/kwavers-alloc-probe-deny-docs` and open PR [#598](https://github.com/ryancinsight/kwavers/pull/598) at exact head `aa5ab2bc`.
- [x] DENYDOCS increment 2 — `kwavers-mesh`: add `#![deny(missing_docs)]` and document the 8 uncovered fields (`BoundingBox`, `MeshStatistics`). Commit `489554d3b`.
- [x] DENYDOCS increment 3 — `kwavers-field`: add `#![deny(missing_docs)]` and write the 39 missing doc items (17 `UnifiedFieldType` variants, 6 `BubbleStateFields` fields + constructor, 6 stress-alias constants, 5 `FieldStatistics` fields, 2 accessor constructors, `WaveFields` alias, `wave` module header, `leto` re-export). Commit `67b4099cd`.
- [x] Run provider gates on the extended lane: format, check, clippy (`-D warnings`, all targets), nextest (16 tests), doctests — all pass.
- [x] Ratchet the detector: `missing_deny_docs` 23 → 20 in `scripts/conformance-baseline.json`; verified on the lane by the same scan the detector runs.
- [x] Push the extended branch and update PR #598 (title + body) to the three-crate increment at exact head `67b4099cd`.
- [ ] Collect hosted terminal evidence, merge at the exact PR head, verify the post-merge default, then advance the Atlas gitlink. **Hosted hold (2026-08-21, re-checked):** all 25 workflow runs remain `queued` after 56 minutes of observation across two re-check cycles (CI/CD `32521893944`, Architecture `32521893980`, benchmark `32521893996`, legacy audit `32521894011`, Deploy mdBook `32521894392`). No runner has picked up a single job. CodeRabbit passed; `recurseml/analysis` is errored (report-only). Re-open on terminal checks or a hosted state transition; no pointer advance or bypass is authorized.

## ATLAS-HYGIENE-BASELINE-001 — current conformance increment

- [x] Reproduce the live-scan abort in a provider-local `.pytest_cache` and verify the directory is derived state, not a source root.
- [x] Extend the shared scanner prune set for Python caches/environments and add a decoy-manifest regression fixture; focused suite passes 21/21.
- [x] Reconcile the stale Athena worktree inference against the detached, gitlink-aligned checkout; preserve only verified facts in the audit.
- [x] Re-apply the Step 4 timeout overlay to the 2 regressed moirai workflow files (`python-ci.yml`, `python-release.yml`) after upstream commit `113a7f9` replaced the overlaid files; `workflow_missing_timeout` returns to 0 and both files parse cleanly under `yaml.safe_load`.
- [x] Assess `missing_deny_docs = 118` as a natural Step 5 candidate: 114 of 118 crates have undocumented public items, so the directive cannot be safely added without per-crate provider documentation work. Classified as a provider-level watchpoint, not an Atlas-side editorial sweep.
- [x] Resolve `tag_pinned_actions = 68` (athena 6, kwavers 62) as audit-sweep Step 5: resolve 13 unique action+ref pairs to 40-char SHAs via `gh api`, rewrite each `@<ref>` to `@<sha> # <ref>` in 5 workflow files, and verify both repos report 0 with no other class increasing. All overlaid files parse cleanly under `yaml.safe_load`.
- [x] Assess `print_dbg = 366`: 31 sites are `build.rs` Cargo-protocol false positives (scanner should exempt `cargo:` writes), ~50 are xtask/scratch tooling, and ~285 are genuine library production debt requiring per-site provider-level migration to a logging facade. Not a safe mechanical sweep; recommended scanner fix for the build.rs false positives.
- [x] Fix the conformance scanner to exempt `build.rs` `cargo:` protocol writes from `print_dbg`: add `CARGO_PROTOCOL_PRINT` regex, subtract cargo: hits when `path.name == "build.rs"`. Count drops 366→335 (−31). Focused suite 26/26 (2 new regression tests); full suite 328/77.
- [x] Regenerate the conformance baseline after the scanner fix: `generate --worktree` writes the new counts; `check --worktree` confirms 0 regressions and 0 tightenings. Baseline `print_dbg` total is now 335 (was 366), with coeus/melinoe/themis at 0.
- [ ] Re-run the clean-revision ratchet after the provider workflow changes land and their parent gitlinks advance; do not baseline the current peer-dirty worktree result. **Blocker confirmed mechanically (2026-08-21):** an isolated clean worktree scan at HEAD fails at submodule materialization — `repos/kwavers` records local-only commit `49d80a465b46...` which the remote rejects (`upload-pack: not our ref`), so a clean revision cannot even check out the recorded kwavers gitlink. The ratchet is therefore hard-blocked on the kwavers PR merge chain (#590/#602 → gitlink advance to a pushed commit), not merely on runner capacity. All other submodules materialize; the scan's dirty-tree and gitlink-match guards work as designed.

## ATLAS-ATHENA-ALLOCATION-CONTRACT-2026-08-31 — current session

- [x] Full root-cause audit of the GMRES warm-solve allocation flake: line-level audit of every allocation site the warm solve can reach. `athena-core` is `#![no_std]`; all workspace vectors allocated once in `GmresWorkspace::new`; `SolveReport`, `Termination`, `ConvergencePolicy`, `SolveError` are all stack/Copy; `NoObserver` is a ZST. `athena-leto` backend ops (`copy`/`scale`/`axpy`/ `dot_prepared`/`norm_l2_prepared`/`residual`) are plain slice loops; `LetoVectorBlock` views are contiguous `as_slice` — no alloc. `leto_ops::dot` and `spmv_into` allocate only on the error path (never taken in warm solves). `hermes_simd` dispatch via `is_x86_feature_detected!` caches in `OnceLock<bool>` (inline storage); `SimdView::new` stores a pointer; `stats_alloc` itself is Copy/atomic counters.
- [x] Verdict: the solver path is provably zero-allocation. The 17 deallocs with only 4 allocs (more frees than allocs) cannot be produced by any Drop cycle — it is glibc per-thread arena cleanup of pre-region allocations observed through the global wrapper.
- [x] Experiment delivered: `MALLOC_ARENA_MAX=1` env var added to the `allocation-instrument` CI job (athena `.github/workflows/ci.yml`). Pinning glibc to a single arena eliminates per-thread tcache churn. If the strict zero-traffic contract passes under this pin on hosted Linux, it names glibc arena churn as the environment cause and clears the way for unconditionally re-enabling the strict test.
- [x] Local Windows verification at `d433d34`: default suite 2/2, ignored suite 2/2 (both GMRES strict + classifier), YAML validated.
- [ ] Collect hosted Linux `allocation-instrument` evidence at the next push; if the strict contract passes under `MALLOC_ARENA_MAX=1`, un-`#[ignore]` the GMRES test.

## ATLAS-KWAVERS-VIS-CONFIG-2026-08-25 — current session

- [x] Audit backend and configuration call sites across the stack; establish that `gpu_enabled` is ignored and `render_quality` diverges from the adaptive `quality` field.
- [x] Draft and index the breaking-contract ADR in Kwavers.
- [x] Remove the two stale public fields and synchronize adaptive quality with the initialized renderer through one authoritative quality value.
- [x] Add focused value-semantic regressions and synchronize affected docs.
- [x] Run focused and full applicable gates (2026-08-25, lane `worktrees/kwavers-vis-config` at `bdea8ea71`): fmt clean; `cargo check` for kwavers-analysis and consumers kwavers/kwavers-gpu pass; default-feature Nextest 744/744; `gpu-visualization` Nextest 783/783 including `adaptive_quality_reconfigures_the_initialized_renderer`; doctests 1 passed / 21 ignored; Rustdoc `-D warnings` clean. Clippy: changed files clean under both feature sets; standalone `--all-targets` shows 7 test-target and `gpu-visualization --lib` 44 findings, all in files the branch does not touch (recorded warning-ratchet debt; untouched here).
- [x] Publish the branch/PR and merge after hosted checks: merged via Kwavers [PR #638](https://github.com/ryancinsight/kwavers/pull/638) at `00455130f` (reviewed head `b2a156215` plus the confirmed commits `2c2b65792`/`26ff990e2`/`bdea8ea71`). Atlas gitlink advance to `00455130f` is HELD: 33 hosted checks pass and two skip as intended, but `Benchmark Runtime Smoke` hit its 30-minute timeout after 29 minutes in the Criterion command.
- [ ] Advance the Atlas gitlink after the cold-build benchmark-smoke correction lands and its hosted rerun is terminal green.

## ATLAS-BOOK-CALLER-PINS-2026-08-20 — current session

- [x] Audit all registered provider `book-pages.yml` callers against the reusable workflow and classify the 20 pre-fix references; Apollo and Coeus now carry the repin on merged defaults, while Hephaestus and RITK carry it in active PRs.
- [x] Publish the remaining 16 workflow-only PRs from current provider defaults. The shared implementation pin is `20c9398`; provider hosted book gates are the acceptance oracle.
- [x] Correct the first remote revisions after their reusable-workflow runs failed before job creation: the exact root pin is `20c93980f7c98f2e23a89c4a0540f16c8f2d7239`, and all 16 PR branches now carry that full commit rather than the invalid initial value.
- [x] Collect terminal hosted results for Horae #24, Hyperion #22, Themis #28, Proteus #16, and Tyche #34 at their exact heads; CI and Deploy mdBook pass for each (`32418584339`/`32418584938`, `32418586348`/`32418586803`, `32418600576`/`32418601066`, `32418598026`/`32418598676`, and `32425417532`/`32425418118`).
- [x] Merge the exact-green PRs with expected-head guards: Horae #24 → `d014929`, Hyperion #22 → `91df53e`, Themis #28 → `c441acf`, Proteus #16 → `73c6c81`, and Tyche #34 → `89194f3`; close superseded Tyche #33.
- [ ] Collect terminal post-merge CI, Deploy mdBook, and Pages results at the five merge commits, verify deployed pages, rerun the caller audit, and record default-pointer changes without touching dirty nested checkouts.
- [x] Review Helios workflow PR [#64](https://github.com/ryancinsight/helios/pull/64) as a caller-only change; mark it ready and merge exact head `9a590ffa` at default `e886754d` after its substantive checks passed.
- [ ] Collect Helios post-merge CI `32436531185` and verify the next default Pages deployment before advancing the Helios Atlas gitlink.
- [x] Merge Apollo #108 at `a0c3da9` and Coeus #340 at `5108ed0082fc5c5ed02bc95c4bfa4ad9cdf8133b` after exact-head provider and book checks passed; their merged-default CI/book runs remain queued.
- [x] Merge the next exact-green provider set with expected-head guards: Mnemosyne #67 → `9da9f92`, Aequitas #38 → `14fdd44`, Asclepius #23 → `ce3fea3`, Eunomia #70/#71 → `c7435a2`/`22a02b1`, and Moirai #145/#146 → `c186fd9`/`7f75f5e`.
- [ ] Collect terminal post-merge CI, book, and Pages evidence for that set; keep the Atlas pointers unchanged until the exact merged defaults pass.
- [x] Merge the next exact-green set, including the stacked RITK dependency: RITK #201/#203 → `3bf61e3`/`8196809`, Hephaestus #214 → `7e09efa`, Hermes #58 → `c647368`, Iris #17 → `8700418`, and Melinoe #19 → `8a67d14`.
- [ ] Collect terminal post-merge CI, Python, backend, book, and Pages evidence for this set before advancing any Atlas gitlink.
- [x] Repair Hephaestus #214 at exact head `ae4fd6a` after its book examples failed to import the traits that provide the called methods; the rerun provider and book checks are pending.
- [x] Publish separate Consus book-gate PR [#53](https://github.com/ryancinsight/consus/pull/53) from current `main`; it enables `mdbook-test` for both existing Rust examples and stages `consus-core` without touching dirty peer trees.
- [x] Reinspect PR #53 after publication and repair the generated workflow revision; the branch now contains only the intended YAML, with the exact shared pin, `mdbook-test: true`, and `consus-core` inputs.
- [x] Diagnose the first book-gate failure (`32420406116`) and repair the two standalone example declarations plus the three non-standalone prose fences; exact PR head is now `0f4af6c`.
- [x] Diagnose the `0f4af6c` rerun (`32435508761` CI + `32435508238` Format, `32435508761` Deploy mdBook): the `Format` job failed because both included example sources ended with no trailing newline, and `deploy / Build book` failed at `Test book code samples` because the bare fence at `docs/book/array_shapes.md:44` (the memory-layout formula) defaulted to Rust. Repair in two commits pushed to PR #53: `ef1030f` adds the trailing newlines to `book_array_shapes.rs`/`book_hyperslab.rs`, and `39da478` tags that fence `text`. Local evidence: `cargo fmt --all -- --check` passes, both example sources compile via `cargo check --example`, and `mdbook build` passes. PR head is now `39da478`; replacement CI `32440567003` and Deploy mdBook `32440567210` are queued.
- [ ] Collect PR #53's rerun and terminal book gate, merge at its exact head, and rerun the 25-book inventory so Consus leaves the missing-gate set.
- [x] Close superseded Consus PR #52 after verifying that PR #53 contains its caller change plus the executable examples and fence repairs.

## ATLAS-CONSUS-SZIP-BOUND-2026-08-20 — current session

- [x] Review the untrusted SZIP header path and confirm the allocation risk through the provider's hosted fuzz and package checks.
- [x] Merge Consus PR [#51](https://github.com/ryancinsight/consus/pull/51) from exact head `2e24e6ad` at default `1000699fa`.
- [ ] Collect post-merge CI and Documentation runs `32436374114` and `32436374130` before closing the security item.

## ATLAS-CFDRS-ALLOCATOR-2026-08-20 — current session

- [x] Remove the unconditional `cfd-validation` global allocator without weakening real allocation accounting; keep the tracking facility in an explicit benchmark/test harness. Provider commit: `d1305ee2`.
- [x] Add the provider ADR update and downstream allocator-link regression test; direct rustfmt, focused clippy, diagnostic check, benchmark compilation, focused nextest (1/1), and cfd-validation library nextest (187/187) pass.
- [ ] Run the provider locked workspace all-target gate from a clean hosted revision; local `--locked` is blocked by the shared overlay requesting a dirty peer `Cargo.lock` rewrite. The exact commit is open as CFDrs PR #360 with hosted Rust workspace and figure checks queued.

## ATLAS-SUBSTRATE-003-2026-08-20 — current session

- [x] Consolidate the nine decomposition/Leto differential helpers into one parameterized conformance clause and reconcile the current 15-method seam count. Provider commit: `d24513a`.
- [x] Add the exact host decomposition gate using the shared clause; update the provider ADR/index if the contract decision changes; run focused format, warning-denied checks, doctests, and nextest (1/1).
- [ ] Record the exact provider commit and hosted gate before advancing the Atlas Hephaestus gitlink. Draft PR #215 has the exact head; CUDA, Metal, ROCm, and WGPU checks are queued.

## ATLAS-GAIA-BOOK-GATE-2026-08-20 — current session

- [x] Confirm fetched Gaia default `dbed97a` invokes `mdbook test` but the book has zero Rust fences; the mesh-gallery generator is not mdBook contract coverage.
- [x] Create one value-semantic included Gaia example on the clean bounded lane `worktrees/gaia-book-gate`; local `mdbook build`, formatting, and strict links (9 files, 16 links, zero errors) pass. The local locked build and mdBook test are blocked by the shared overlay lock-form and multi-artifact/toolchain state; hosted CI is the clean-runner oracle.
- [x] Publish PR [#33](https://github.com/ryancinsight/gaia/pull/33) at exact head `39a4f7f`; the book workflow now stages only the current Cargo compiler artifacts and asserts exactly one Gaia library. The earlier `32417028130` failure was the pre-repair merge ref; the intermediate broad-staging run `32459250549` is superseded after reproducing cache-sensitive `E0464` locally. Replacement CI `32473606516` and book `32473606617` are queued at the exact current head.
- [ ] Collect terminal exact-head CI/book evidence, merge, verify the post-merge default and Pages deployment, then advance the Atlas pointer.

## ATLAS-EUNOMIA-NUMPY-CI-2026-08-20 — current session

- [x] Confirm the optional `numpy` feature is real Eunomia code consumed by Hephaestus and Kwavers, while Eunomia has no standalone Python package.
- [x] Correct the Atlas binding inventory to list ten binding crates and name Eunomia as the NumPy element provider.
- [x] Add the isolated provider CI feature/runtime contract gate on a clean Eunomia lane based at `85e590b7`; preserve the dirty primary checkout.
- [x] Repair the first hosted failure: the NumPy job compiled and linted the feature but lacked `cargo-nextest` (`32412277378`, job `96565207307`). Add the pinned `nextest@0.9.140` install to the NumPy job and publish Eunomia PR [#70](https://github.com/ryancinsight/eunomia/pull/70) at exact head `cdc7e68`.
- [ ] Collect replacement Rust/NumPy/supply-chain run `32423868719` and MSRV run `32423868861`, then synchronize the provider and Atlas PM records. `recurseml/analysis` is report-only.
## ATLAS-KWAVERS-DEFAULT-2026-08-20 — current session

- [x] Fetch the moving default and identify merged PR #421 at exact head `b5b4fb0614ad3238ab95ff092cebd5977a201b22`.
- [ ] Collect the terminal default Architecture, migration, CI/CD, and Pages runs `32404999498`/`32404999519`/`32404999529`/`32405000042`; advance the Atlas gitlink only after all required hosted evidence passes.
- [x] Run the full exact-head/coherence audit at root `604bdcd`; it reports only the Themis, RITK, and Kwavers gitlink drifts and no additional coherence issues.

## ATLAS-PROVIDER-INTEGRATION-2026-08-18-CURRENT — superseding recheck

- [x] Resolve and validate the Consus ADR-0045 P4 lane at local head `1909709` in the canonical `worktrees/consus-adr-0045-p4-benchmark` path. The lane retains the newer Zarr crc32c/bytes-codec changes while removing only the obsolete package-owned S3 integration; formatting and locked focused Nextest `c3fcdabb-9493-46e3-865e-245e1e319a33` pass 492/492 tests across `consus-io` and `consus-zarr`.
- [x] Publish the local rebased branch through Consus PR #50. Branch pushed force-with-lease to `1909709c`; PR is MERGEABLE. Book deploy passes; CI matrix queued. Collect hosted verification before merging.
- [x] Correct Kwavers' Python comparison extras and source-install commands at provider commit `308d91594`: `kwave` now installs the MATLAB-free `k-wave-python` bridge, `matlab` owns the MATLAB Engine bridge, and the README uses the repository-root Cargo manifest. The provider commit and Atlas pointer `ad977c6` are pushed. The compiled-extension and hosted comparator residual remains open.
- [x] Remove the remaining stale Kwavers Python install commands from two diagnostics and two examples at provider commit `498f38a3e`; all now use the repository-root `crates/kwavers-python/Cargo.toml` manifest and the `kwavers_python` wheel name. Atlas pointer `0a3e2dd` is pushed. The focused test remains blocked only by the absent local extension.
- [x] Repin Kwavers' book, Python-wheel, and crates.io callers to Atlas reusable-workflow revision `2f17abc`; the wheel caller's `atlas-ref` now resolves to the pushed graph containing Kwavers `498f38a3e`. Provider commit `2bc5dd161` and Atlas pointer `55d8b8d` are pushed; YAML parsing and diff checks pass.
- [x] Collect the Kwavers hosted comparator at provider head `56bded6fa` through run `32237250724`: Ubuntu, Windows, and macOS wheel jobs pass; the installed Ubuntu wheel runs all three value-semantic `test_kwave_comparison.py` cases with `KWAVERS_RUN_SLOW=1`. Provider documentation closure is `e6fb53b90`; advance the Atlas pointer to that exact current default before the root sweep.
- [x] Add `workflow_dispatch` to Kwavers' wheel-smoke workflow at provider commit `a10183c80` so the heavy comparator can run against provider main; YAML validation passes with the workflow trigger present. Atlas pointer `4073b1f` is pushed. The dispatched run is still required for closure.
- [x] Collect CFDrs PR #358 rerun at corrected head `5e13018a`: run `32229463775` passes the Rust workspace and figure SSOT gates, and PR #358 merges at default `834340f7`. The Atlas gitlink records that exact default; the provider checkout remains on its peer branch.
- [x] Collect and merge Apollo PR #107 only after its benchmark gate is green. Benchmark run `32347865841` passes all counterbalanced cases; PR merges at provider default `0c6ffb91ce5d1b68d8da50c6fd12726b7993b1b8`. Post- merge CI `32348784876`, Pages `32348782338`, and live Pages HTTP 200 pass. Atlas gitlink records the merged default.
- [x] Re-run Helios `mdbook test docs/book` at detached HEAD `f8ebe42`: every listed chapter/example completes. Keep H-103 open for provider reconciliation because Helios `backlog.md` still says todo and the checkout has peer-owned Python manifest dirt.
- [x] Run CFDrs `mdbook test docs/book` on clean branch `codex/cfdrs-pypi-001`; every listed chapter/example completes. The locked `xtask check-figures` command remains blocked by the Atlas overlay lock refresh and is not represented as a pass.
- [x] Collect the merged CFDrs default-head gate: PR #355 (`ed585d75`) merged at default `aa54f5cdcdc4e406df0c60ea6c3cb507e968fc97`; Atlas gitlink records that exact default. Stale timeout at `efce3472` is superseded.
- [x] Probe the Kwavers comparative Python test under Python 3.13.12; import fails because the compiled `pykwavers._pykwavers` extension is absent. Preserve the peer-owned checkout and leave the build/wheel repair to KW-PYTHON-064 and its clean-lane hosted gate.
- [x] Re-run stack-overlay, lock-form, and conformance checks after the Aequitas integration: lock-form passes for 27 standalone locks, conformance passes 12/12, and the latest overlay is aligned.
- [x] Reconcile the RITK default movement through PR #175 and PR #178. The Atlas gitlink now records merged default `6bd4bc14` from PR #178; the default CI/Python CI runs `32203816886` and `32203816879` are queued. The earlier exact-head workflow `32200267421` is recorded as a real Python-wheel parity failure, not as hosted closure.
- [x] Complete and merge the Tyche provider cleanup at commit `de925e6` through PR #26 at default `7e55ff8f`: consolidate Latin-hypercube/Sobol index conversions and remove five production type-suffixed helper names. Provider gates pass: nextest 51/51, doctests 18/18, warning-denied Clippy, rustdoc, and conformance zero across all tracked debt classes.
- [x] Correct the Hephaestus hosted-state record. Its default branch is `master`, not `main`; default head `607ce3f` has passing CUDA `32083561386`, WGPU `32083561356`, ROCm `32083561357`, and Metal `32083561389` workflows.
- [x] Reconcile Coeus PR #339, merged at provider default `5adc2d1649bfd2bf68c529b011308e150375810d`, and stage the Atlas gitlink advance without modifying the dirty primary checkout. The old backend parity failure is superseded by the merged Apollo 0.27 lock closure.
- [x] Diagnose the CFDrs PR #355 Rust-gate timeout. The failure reproduces at provider main `44ab23b` in `cfd-validation::benchmark_validation::test_benchmark_run_integration` at the unchanged 30-second budget; the backward-step provider was rebuilding its normalized parabolic inlet vectors on every SIMPLE iteration. Provider commit `1bebb5e` prepares the profile once and reapplies cached values without changing the workload or assertions.
- [x] Collect CFDrs exact-head run `32197696210` at `1bebb5e`, then merge PR #355 only after the Rust and book gates pass. PR #355 merged at default `aa54f5cd`; Atlas gitlink advanced. Timeout at the prior head superseded.
- [x] Re-run the live lane audit after the provider pushes. The 2026-08-19 probe reports four topology violations: Consus has four trees and one lane outside the canonical root, Kwavers has four trees, and RITK has four trees. These remain peer coordination state and were not modified.
- [x] Collect the Themis post-merge CI/MSRV/Pages state: runs `32194584768`, `32194584736`, and `32194583598` pass at `0484a333`.
- [x] Collect Mnemosyne Miri and merge PR #62 at provider default `553499056ae37f3aa9f249cc507a0a09e55fd08d`; Rust verification, MSRV, Loom, Miri, aarch64, ThreadSanitizer, and CodeRabbit pass, while `recurseml/analysis` remains report-only. Reconcile post-merge TSan follow-up commits `9754ebc`, `1c79909`, and `64f0d2e`; Atlas records current default `64f0d2ebe58e14705ca2345cad2c705f99a6b611` without provider edits.
- [x] Reconcile the moving Mnemosyne default. The first recheck at `43cdf047` failed Miri compilation at `mnemosyne-backend/src/backends/unix.rs:292` because `SEGMENT_SIZE` was not imported. The provider default is now `cbccb7ee`; exact-head run `32208332797` passes Rust verification, Miri, Loom, aarch64, and ThreadSanitizer after the provider held that backend out of the Miri gate. Advance the gitlink from `64f0d2e` to `cbccb7ee`, then rerun exact-head, overlay, and lock-form gates.
- [x] Collect Aequitas post-merge CI `32198085105` and Pages `32198084983`; both pass at merged default `260ad10`.
- [ ] Collect the corrected CFDrs exact-head run; run `32197696210` fails in hosted Clippy at `cfd-2d/src/solvers/ns_fvm/solver/solve.rs:218` for `clippy::if_not_else`, while the book-figure check passes. Preserve the peer-owned CFDrs checkout and branch.
- [x] Classify the RITK hosted residual at the exact failed job: the Python Wheel smoke test fails `test_cmake_inverse_displacement_field_2d` (max `2.2323646545`), `test_cmake_inverse_displacement_field_3d` (max `0.0820963383`), and `test_cmake_iterative_inverse_displacement_field` (max `0.1707854271`), while Rustfmt, Clippy, dependency alignment, Python matrices, and the platform test suites pass. The provider fix is tracked in `ATLAS-RITK-PY-WHEEL-PARITY-2026-08-18`; no tolerance widening is permitted.
- [x] Commit the RITK NumPy `[Z,Y,X]` internal-direction correction at provider head `ca25e22c`: the canonical anti-diagonal direction is shared by scalar and color NumPy images; TPS and iterative inversion map physical `(X,Y,Z)` to NumPy `(Z,Y,X)` while Chen's existing mapping remains intact. Local evidence is ritk-filter nextest 1073/1073, ritk-python nextest 47/47, targeted SimpleITK parity 3/3, release maturin build, Clippy, format, and diff checks. Exact-head hosted CI/Python CI runs `32246000940`/`32246000947` pass, including the platform nextest and Python wheel matrices. The unsupported local SimpleITK 3.0 alpha retains one max-2-ULP patch-denoising residual; the pinned hosted oracle is green.
- [x] Fix the ARCH-008 classifier to exclude provider `worktrees/` lanes from member source scans. Focused coverage is 44/44 and the live scan has zero lane paths; defer oracle regeneration until peer provider edits stabilize the exact site set.
- [x] Reconcile the path-dependency audit against accepted ADR 0044: retained `git+` sources are the required standalone lock form, while the only registered cross-repository path lines are the exempt Melinoe contract fixture. Overlay, lock-form, and exact-head gates pass.
- [x] Implement Gaia's direction-set half of `ATLAS-GAIA-POLYLINE-006` in provider commit `3c2d655`: `UnitSphereDirectionSet` reuses the existing geodesic tessellation and Leto `UnitVector3`, while RITK remains on Gaia canonical types. Local nextest 972/972, warning-denied Clippy, doctests 9/9, format, and Rustdoc pass.
- [x] Collect Gaia PR #32 hosted CI and book checks at `3c2d655`, merge the provider default `dbed97a`, advance the Atlas gitlink, and rerun exact-head, overlay, and lock-form gates. Hosted CI `32206596573` and mesh-book `32206596795` pass; CodeRabbit passes and `recurseml/analysis` is report-only error.
- [x] Run the stack-wide book-link detector across all 23 registered books: every `FILE_MISSING`, `ANCHOR_MISSING`, and `READ_FAIL` count is zero. Run its fixture regression suite with `PYTHONPATH=scripts`; 43/43 tests pass, including the intentional missing-link fixture.
- [x] Repair the fast-tier collection import in `scripts/tests/test_atlas_scattered_containers_classify.py` to match the `pytest.ini` `pythonpath = scripts` contract. The committed fast tier now passes 225 tests, deselects 17 slow tests, and passes 74 subtests in 13.75 seconds.
- [x] Run the committed slow Python/book tier: 17/17 tests pass in 1.62 seconds.
- [x] Reconcile the claimed Horae lock slice outside the Atlas overlay, run its locked package gates, and synchronize the provider-local PM.
- [x] Push Horae lock commit `9cc9fd8` and PM synchronization `aefe641` plus evidence-boundary correction `91a020c` on PR #19. Post-merge CI run `32202560133` passes `verify` and `supply-chain`, and Pages deployment `32202559349` passes at default `1ed6a172`. The root gitlink is advanced to that merged head.
- [x] Claim and implement the independent Hyperion lock slice while Horae's hosted run is queued. Provider commit `880eb8c` refreshes Aequitas `260ad10`, Eunomia `85e590b`, and Proteus `f612c99`; local format and locked all-feature metadata pass.
- [x] Collect Hyperion PR #15 hosted `verify` and `supply-chain` at exact head `880eb8cce28d1e887942fbeb185a1cf4173c776a`; PR #15 merged at default `0156f59f78aba1e3b06d4511ffb1ce30d5c0c6d4`, and Atlas advances to that verified provider merge commit.
- [x] Collect Hyperion PM-only PR #16 at exact head `86486139120243e0b6cae84143d7a914eb51a8a3`; hosted `verify` and `supply-chain` pass, and PR #16 merged at provider default `93157c235d1bfabd88a4720b4a02370ff2a00cc2`.
- [x] Run the exact-head clean-checkout audit. It reports 22 findings across 17 provider checkouts: eight checkout-head drifts and fourteen dirty canonical checkouts. Preserve those peer-owned states; do not treat the cleanliness gate as provider source evidence.
- [x] Audit Gaia's tractography boundary: the Atlas-pinned default `4980732` exports the validated `Polyline`, and RITK TCK/TRX consume it directly. Gaia cleanup commit `f88ff17` is local-only and the nested checkout is detached in a peer rebase; no provider or consumer files were changed.

## ATLAS-PROVIDER-INTEGRATION-2026-08-18-LIVE

> Historical baseline superseded by the current recheck above; its queued and
> failure classifications remain evidence for the earlier provider heads.

- [x] Re-run the live structural provider audit at root `04be0d6`. All 22 provider gitlinks now match their fetched `origin/main` defaults, including Consus `ef439b2f`, Mnemosyne `5fd08df6`, and RITK `f9d04a79`.
- [x] Re-run the full requested-provider coherence audit with the same exact heads. The provider set is clean; this is separate from hosted gates and nested-checkout cleanliness.
- [x] Reconcile the fetched Mnemosyne default movement from `638ddab8` to `5fd08df6` in Atlas commit `04be0d6`. The nested provider checkout was already at that fetched head; no provider working-tree files were staged.
- [x] Re-run the committed lock-form gate: all 27 committed standalone locks resolve; `melinoe/contracts/atlas-device/Cargo.lock` remains the single declared in-tree fixture exemption.
- [x] Re-run the conformance regression suite: `scripts/tests/test_atlas_conformance.py` passes 12/12.
- [x] Re-run the clean-checkout audit. It reports only peer-owned dirty or moving nested checkouts: Themis, Tyche, Proteus, Consus, Helios, Harmonia, Eunomia, Moirai, RITK, Melinoe, Leto, Hephaestus, Coeus, Apollo, Hermes, and Iris. No peer dirt was overwritten or staged.
- [x] Re-run the lane audit. CFDrs remains within the two-tree bound after clean merged-lane reclamation. Five violations remain: Coeus has three trees, Consus has three trees plus one lane outside the canonical root, Kwavers has four trees, and RITK has three trees. These are active peer scopes or preserved dirty lanes.
- [ ] Collect the exact-head hosted results for the moving provider defaults and root integration. Local exact-head, lock-form, and overlay gates do not substitute for hosted provider verification; the current structural audit passes, but hosted provider status remains uncollected in this pass.
-      Read-only hosted sweep evidence now includes Mnemosyne CI `32192895997` queued at `5fd08df6` and RITK CI/Python CI `32192759850`/`32192759832` queued at `f9d04a79`. Consus Documentation `32184845179` fails at `ef439b2f` because the `consus-zarr` manifest names a missing `benches/s3_rusoto_moirai.rs`; Coeus Backend parity `32147262055` fails at `79f05dfd` because the locked Apollo Git revision exposes `apollo-fft 0.26.0` while the consumer requires `^0.27.0`. Hephaestus is green on its `master` default at `607ce3f` across CUDA, WGPU, ROCm, and Metal. These are provider/consumer gate findings, not local source-success claims.
- [ ] Reconcile the remaining peer-owned checkout and lane residuals through their owning provider branches. Do not clean, reset, or delete dirty checkouts or open provider lanes from this root audit.
- [x] Audit the current multiphysics books locally. `mdbook test docs/book` passes for CFDrs and Helios; `scripts/check_mdbook_links.py` reports zero missing files and anchors for CFDrs (88 files, 353 links), Helios (48 files, 190 links), and Kwavers (106 files, 463 links).
- [ ] Repair Kwavers' compilable book examples before treating its shared Pages caller as a complete teaching gate. The current `mdbook test` fails on an undefined `DENSITY_WATER_NOMINAL`, output/diagram text in Rust fences, unresolved provider imports, incomplete setup, and pseudocode memory-model snippets. Link integrity alone is insufficient.
- [ ] Keep the CFDrs locked Rust gate separate from the book result. The focused `cargo nextest` invocation is currently blocked before compile because the shared Atlas overlay has unused provider patches and `--locked` refuses the required lockfile update; this is an integration resolver defect, not evidence that the solver tests pass.

## ATLAS-ASCLEPIUS-RELEASE-008 — current package validation

- [x] Validate the current public Asclepius source with offline diagnostics: `cargo check --offline --workspace --all-targets --all-features`, Nextest 18/18, doctests 6/6, Clippy with `-D warnings`, rustdoc, and `cargo package --offline --package asclepius --allow-dirty` all pass. The generated lock changes from the Atlas overlay were discarded; the committed provider lock remains unchanged.
- [ ] Complete the registry transition: run the locked standalone gate without the Atlas development overlay, publish `asclepius` through the protected crates.io environment, enable trusted-publishing-only mode, and create the matching GitHub Release. These are release-authority actions, not local source evidence.

## ATLAS-PROVIDER-INTEGRATION-2026-08-17

- [x] Audit the current 22-provider registration, ownership, exact-head, and hosted-gate boundary. Structural exact-head audit and its 27-test regression suite pass; the full coherence blocker is the exact Apollo 0.26.0/0.27.0 consumer lag recorded below.
- [x] Activate Harmonia as an Atlas submodule and reconcile its parent gitlink to fetched `origin/main` `02ffd14`; the nested checkout retains its peer-owned book, workflow, example, and lockfile dirt.
- [x] Extend the default provider audit from 21 to 22 active providers so the newly activated Harmonia entry is covered without a custom provider list.
- [x] Merge CFDrs PR #348 (`f95209da`), Apollo PR #105 (`df8999f`), and Tyche PR #24 (`5eeaba9`); preserve peer-dirty nested checkouts.
- [x] Collect and merge Hermes PR #52 (`dd4cb129`) and Mnemosyne PR #59 (`d1144f74`); their external `recurseml/analysis` analyzer errors remain report-only.
- [x] Reconcile the subsequent Hermes default movement to `ef40f43`; hosted CI run `32165594249` and Pages run `32165592665` pass at that exact provider head. The nested checkout retains peer-owned `Cargo.lock` dirt.
- [x] Close Iris LF-policy cleanup: provider commit `3d36a9d` merged through PR #16 at default `f8630a13`; hosted verify and supply-chain jobs pass in run `32167630353`. The clean lane retains only the baseline `type_suffixed_fns=1` class; the primary checkout remains untouched.
- [x] Close Aequitas CI timeout cleanup: provider commit `5ef6e23` merged through PR #34 at default `3168a41d`; hosted verify and supply-chain jobs pass in run `32170094595`. The change is limited to finite 30-minute job bounds; RecurseML remains report-only.
- [x] Close Helios LF-policy cleanup: provider commit `a6833b9` merged through PR #66 at default `f8ebe42f`; hosted Rust, Python, and benchmark jobs pass in run `32168302314`. The primary checkout retains peer-owned Python manifest dirt; RecurseML remains report-only.
- [x] Close Eunomia LF-policy cleanup: provider commit `c340d19` merged through PR #69 at default `85e590b7`; hosted Rust verification `95831119410` and supply-chain `95831119356` pass in run `32173862885`. The primary checkout's peer-owned staged and unstaged `Cargo.lock` stays untouched.
- [x] Close Asclepius conformance cleanup: provider commit `b6257ae` merged through PR #20 at default `db33ccaf`; hosted `verify` and `supply-chain` pass in run `32173604736`; RecurseML remains report-only.
- [x] Close Tyche conformance cleanup: provider commit `240b5fe` merged through PR #25 at default `e7f60504`; hosted `verify` and `supply-chain` pass in run `32174221062`; the peer planning checkout remains untouched.
- [x] Close Leto release-workflow timeout cleanup: provider commit `1d7aada` merged through PR #117 at default `01474f2b`; hosted Rust verification run `32174610008` passes; the peer-dirty primary checkout remains untouched.
- [x] Collect and merge RITK PR #165 at default `ae23d4b2`; hosted native CI `32063759899` and Python matrix `32063759848` pass at the final source head.
- [x] Collect and merge Kwavers PR #401 at default `6075940c`; required native, feature, coverage, nightly, Miri, security, benchmark, and documentation gates pass. RecurseML remains report-only and CodeRabbit was rate-limited.
- [x] Collect and merge Asclepius PR #17 at default `5de8a48c` and Coeus PR #336 at default `b14777d`; provider ADR indexes pass the canonical generator check and hosted verification is green.
- [x] Collect and merge Consus PR #44 at default `2dcf05a`; its full format, MSRV, platform-test, check, and fuzz-target build matrix is green.
- [x] Collect and merge Helios PR #62 at default `39a24992`; hosted Rust, Python, and phase-reversed benchmark gates pass in run `32068165866`.
- [x] Advance the four repaired provider gitlinks in Atlas commit `944f6e1`; the structural exact-head audit reports all twenty requested providers aligned with fetched origin defaults.
- [x] Collect final root gates at `944f6e1`: overlay `32072555152`, conformance `32072555155`, and push analysis `32072554308` pass. The local full coherence scan remains limited by peer-owned stale nested Asclepius working-tree content; no peer dirt was overwritten or staged.
- [x] Reconcile Mnemosyne to fetched `origin/main` `d48f4842` in Atlas commit `a49afd3`, preserving the nested peer checkout and synchronizing the moving-default evidence.
- [x] Re-collect the root hosted gates after the provider-head correction: overlay run `32101202278` records Kwavers `0.27.0` versus indexed Apollo `0.26.0`, and conformance run `32101488985` at `d496297` isolates the RITK `oversized_files` regression `43 -> 44`.
- [ ] Complete the remaining Apollo `0.27.0` consumer lock sweep for Kwavers, then rerun affected hosted gates. Coeus and RITK default pointers now carry their provider-side 0.27 migration heads; do not lower consumers or add a shim. Helios lock advance (Apollo `0c6ffb91`, Moirai `3b812865`, Themis `0484a333`) is open as PR [#68](https://github.com/ryancinsight/helios/pull/68); CI queued.
- [ ] Split the committed RITK `region.rs` 540-line implementation without overwriting the peer-owned in-flight region edits, then rerun the root conformance gate at the exact provider head.
- [x] Reconcile the second fetched-default movement: Themis `a609cd70`, Proteus `996b8227`, Mnemosyne `77e6e3e3`, Hermes `35d4c437`, Asclepius `80400760`, Eunomia `bab4f9f8`, RITK `b91bcee6`, and Iris `c10b328d`; preserve all nested peer-owned dirt and re-run the structural exact-head audit.
- [x] Reconcile Mnemosyne's next fetched-default movement to `7967315f` in the Atlas pointer, preserving the primary checkout's peer-owned `Cargo.lock`; hosted run `32172944880` passes Rust verification, Miri, and Loom at the exact provider head.
- [x] Collect Apollo PR #104 at merged default `d585e0f5`. Post-merge Rust, Python, and Pages checks pass in runs `32145206051` and `32145204622`. The latest benchmark remains the failed pre-merge run `32140820453` at `797cc4ad`, so Apollo is hosted-green for build/docs but not fully benchmark-qualified; keep that evidence as a performance residual rather than blocking the exact provider gitlink.
- [x] Complete the Apollo benchmark-instrument lock closure on clean lane `D:/atlas/worktrees/apollo-root-cleanup`, branch `codex/apollo-benchmark-lock-104`, commit `7d56dc2b`, and dependent PR [#106](https://github.com/ryancinsight/apollo/pull/106). Scope stayed limited to `.github/workflows/benchmark-regression.yml` plus the PR-head `Cargo.lock`. The workflow inherits every candidate transform manifest that directly requires `apollo-fft`; Bash block parsing, locked workspace check, 494/494 focused nextest tests, formatting, and workspace doctests pass locally. PR #106 and PR #104 are merged; the latest PR #104 benchmark regression remains failed, so Apollo is not performance- qualified despite green Rust/Python/Pages evidence.
- [x] Reconcile the Kwavers moving default before advancing its Atlas gitlink. Kwavers default is `2a291a0644f07e00f45368dcef6d60b804e5cc08` (PR #429); Atlas gitlink records that exact default. PR #427 branch remains separate.
- [x] Reconcile the Mnemosyne moving default before advancing its Atlas gitlink. Mnemosyne default and Atlas gitlink both point at `6b0e490752f215782d63f876e85059534e25af54`; closure recorded in ATLAS-MNEMOSYNE-BOOK-CLOSURE-2026-08-20.
- [x] Close `ATLAS-ORPHAN-MODULES-096-KWAVERS`: PR #400 merged at `23f53284d789ba9b15788b51b3e83e40d301caf3` after the formatting repair PR #403 merged at `15c12732f5841125a5d65b6c3da2adc0f7c0793a`. The source closure is now in the fetched default history. The clean lane `D:/atlas/worktrees/kwavers-orphan-096` was removed after an empty status check; its branch ref remains available and no peer dirty state was removed. The separate moving-default recheck remains open above.
- [x] Bound every network, package-manager, compiler, mdBook test, and mdBook build command in the shared Pages workflow at root commit `6ed29a9`. The workflow now uses `--locked` for the package build and metadata query, and retains the 20-minute job bound with per-command termination. The local link-contract suite passes 43/43; YAML/actionlint executables are unavailable in this Windows environment. Helios default `408a31b0` still calls the prior shared workflow revision; Kwavers and CFDrs likewise retain peer-owned caller pins (`4c31dd7` and `bb505e5`). Horae and Hyperion have completed their caller repinning slices below.
- [x] Correct the conformance workflow classifier at root commit `78c7880`: pure reusable-workflow callers inherit timeout bounds from their called jobs, while mixed workflows still require a local timeout. The focused scanner suite passes 11/11, the Horae live scan tightens `workflow_missing_timeout` from 1 to 0, and the committed baseline records that correction. The commit also contains pre-staged peer root updates; no peer source files were edited by this slice.
- [x] Collect and merge Horae PR #18 at source `cded674`; merge commit `0631da0` is the Atlas Horae gitlink. Hosted `verify`, `supply-chain`, and `deploy / Build book` pass at the exact source head; the external RecurseML analyzer remains report-only. The caller repins to Atlas workflow `6ed29a9`, enables `mdbook-test`, and builds package `horae`. Post-merge Pages run `32103884266` and live `https://ryancinsight.github.io/horae/` return the expected book title with HTTP 200.
- [x] Collect Helios PR #65 at merged provider default `aa7a4fa`. Rust, Python, and book-build checks pass; the PR benchmark regression check remains in progress, so no performance or Pages-deployment claim is inferred.
- [x] Collect and merge Hyperion PR #14 at source `b8d4fb8`; merge commit `fd752c7` is the Atlas Hyperion gitlink. Hosted `verify`, `supply-chain`, and `deploy / Build book` pass at the exact source head. The change adds the line-ending policy, bounds both CI jobs, and enables the four executable book samples through the shared `mdbook-test` gate. The conformance baseline now records its measured zero residuals. Post-merge Pages run `32103884853` and live `https://ryancinsight.github.io/hyperion/` return the expected book title with HTTP 200.
- [x] Reconcile the current Consus default before advancing the Atlas gitlink. Consus default and Atlas gitlink both point at `0e95c8f25c1df855a8190e72f638f12d776d80b4`; the queued gates at `ef439b2f` are superseded. PR #46 conflict and peer rebase remain open.
- [x] Collect the merged RITK PR #173 default-head gates after the peer root pointer advance. RITK default and Atlas gitlink both at `a16a27f24e814cb1e4315d9c44dec4394f0e26b0`; stale queued runs superseded. Closure recorded in ATLAS-RITK-WORKFLOW-PIN-2026-08-20.
- [x] Remove the clean merged RITK PR #173 and PR #168 lanes after empty status checks. Their branch refs remain available; the dirty or open provider lanes in the rest of the stack remain preserved.
- [ ] Re-open Gaia line-ending cleanup after its peer-owned interactive rebase `cascade/provider-042` completes: the clean origin head lacks only the `.gitattributes` policy in the safe hygiene slice; source ratchet debt is separate and remains unclaimed.
- [ ] Re-run the Atlas conformance ratchet on a clean materialized revision after peer dirt is reconciled. The intentional live-tree scan reports seven regressions in Coeus, Helios, RITK, and root sprawl; it is not a reproducible merge gate while those peer changes and untracked artifacts remain present.

# Sweep 2026-08-13 — execution order

## ATLAS-MULTIPHYSICS-ADOPTION-100 — current execution order

- [x] Record the suite boundary: CFDrs, Kwavers, and Helios are integrators; provider ownership remains with the named Atlas packages and is not inferred from repository presence alone.
- [x] Run the structural 21-provider registration audit and preserve the Tyche/Tychee naming normalization.
- [x] Collect and merge the CFDrs numerical-fidelity slice and the follow-up Fourier/SSOR ownership slice. CFDrs PR #345 merged at exact default `a3c53da2571ffc28532bd65e13975b4ee92a73d6`; hosted run `31997714748` passed the Rust workspace and book-figure gates, and the focused native Fourier/SSOR gates pass locally.
- [x] Collect Coeus PR #334; provider-contract jobs pass at merged default `a8ea12eb23477ff017e38479ae792094ccb85382`, and the Atlas gitlink now points to that exact default without modifying the peer-dirty checkout.
- [x] Advance the Atlas CFDrs gitlink to merged default `a3c53da2571ffc28532bd65e13975b4ee92a73d6`; the peer-dirty nested checkout was preserved.
- [x] Advance the Atlas Apollo gitlink to merged default `ed6d6905afda394a9e12570543159ab1b262589e`; the peer-dirty Apollo checkout remains untouched while the public plan-scratch merge is integrated at the root.
- [x] Advance the Atlas Leto gitlink to the pushed orphan-module cleanup and gate-evidence default `0977fd8`; the Leto checkout is clean and the overlay lockfile limitation is recorded in the provider PM artifacts.
- [x] Close Leto `ATLAS-LETO-CONTRACT-100`: provider `6463f4a` replaces the shutdown `is_err()` assertion with `Err(moirai::ExecutorError::ShuttingDown)`; the scan returns 9, strict Clippy passes, focused Nextest passes 550/550, and hosted CI `32021076930` plus Pages `32021074899` pass at the exact source head. Provider PM closure is `e04fdc7`.
- [x] Collect Kwavers PR #386 after its full hosted matrix passed, mark it ready, merge it as `0e9fb8dab29f2ceef505f685211e84aa3a321645`, and advance the Atlas gitlink without touching the peer's untracked transducer constructors.
- [x] Reconcile Consus `CONSUS-NODEF-GATE-001` against clean `origin/main`: the provider-local record reports six unreachable files removed, `orphan_modules=0`, default/no-default locked gates green, and the exact final provider head `d95ba00` passes hosted CI `32018422744` (80 jobs), Documentation `32018422679`, and Pages `32018420714`. The root pointer now advances to that exact hosted-green head; the Atlas-overlay lock rewrite remains a separate environment note.
- [x] Close Consus `ATLAS-CONSUS-UNWRAP-099`: provider `a9a56ad` removes the three unwrap ratchet delta without a baseline edit; the scan returns 383, default/no-default Nextest passes 2553/2553 and 2031/2031, strict Clippy and doctests pass, and hosted CI `32020339446`, Documentation `32020339452`, and Pages `32020338335` pass at the exact source head. Provider PM closure is `087f810`.
- [x] Close CFDrs `ATLAS-CFDRS-CONFORMANCE-101`: provider source `e9c84bf6` returns baseline `existence_only_assertions=137` and `tag_pinned_actions=0`; locked package check, focused locked Nextest 166/166, and doctests pass; hosted CI `32022469516` passes Rust and book-figure jobs. Advance the Atlas gitlink to PM closure `38bdbeb9`.
- [x] Close `ATLAS-MNEMOSYNE-CONFORMANCE-101` on a clean provider lane. Replace the NUMA binding `is_ok()` assertion with exact `Ok(())` at source `30126aa`, merged provider head `39d76d2`; hosted Rust verification, Loom, and Miri (Stacked and Tree Borrows) pass in `32024295467`. Provider PM closure `f06c8f9` merges at `26ea626`; advance the Atlas gitlink to that PM closure. The provider baseline is four existence-only assertions; the local locked check is overlay-blocked.
- [x] Close the Hephaestus attention structure ratchet. Source `702eba8` moves the shared download assertion into `src/attention/assertions.rs`, reducing `oversized_files` from 39 to 38; provider default `4714b8c` and PM closure `300b9e9` are hosted-green across CUDA `32027773223`, ROCm `32027773309`, WGPU `32027773340`, and Metal `32027773250`. Advance the Atlas gitlink to `300b9e9`; the direct Coeus attention cutover remains a provider-owned dependent item.
- [x] Re-run the exact-head and lane audits at root `d56eaa0`: both the requested 20-provider and Atlas 21-provider sets pass exact-head equality, and the lane audit is clean. The generated overlay still reports only peer-owned Athena lock drift, and the conformance report was collected with `--worktree` at exit 0; it reports 46 remaining orphan modules: Kwavers 22, CFDrs 14, RITK 6, Apollo 3, and Coeus 1. Hermes is now clean after its pushed orphan cleanup. The live scan is evidence only, not a reproducible clean-tree gate. The generated overlay check remains red only for peer-owned Athena's five Hermes SIMD lock entries (0 lagging requirements). The same scan reports 48 workflow-timeout residuals after the Consus jobs were bounded; the remaining classes are unchanged.
- [x] Reconcile the 2026-08-17 moving defaults before the next exact-head closeout: Mnemosyne `924cdcce`, Aequitas `c74b662c`, and Leto `d966e32c` are the fetched `origin/main` heads. Advance only those three root gitlinks; preserve their peer-owned dirty nested files.
- [x] Reconcile the subsequent fetched-default movement without staging nested peer dirt: Themis `f61173bc`, Tyche `5eeaba95`, Proteus `cb70021b`, Mnemosyne `d1144f74`, Consus `2dcf05a8`, Helios `39a24992`, Hermes `dd4cb129`, Aequitas `c74b662c`, Asclepius `5de8a48c`, Moirai `3d5d4c66`, RITK `ae23d4b2`, Coeus `b14777d8`, Apollo `df8999f9`, and Iris `da210d2f` now match fetched `origin/main` in the staged root index. Hosted-gate status is not inferred from this pointer operation.
- [x] Repair the unreachable Athena root gitlink from `638ca74f` to fetched default `bd9346f6`; root workflows `32050420294`, `32050420287`, `32050420276`, and `32050420274` all failed during recursive checkout. The nested Athena checkout remains untouched.
- [x] Repair the next unreachable root gitlink, Gaia `fa35887e`, to fetched default `9595668`; the nested Gaia checkout remains untouched.
- [x] Repair the next unreachable root gitlink, Harmonia `a8ce2fc3`, to fetched default `10e15ae`; the nested Harmonia checkout remains untouched.
- [x] Supersede CFDrs PR #348's source slice with the current PR #349 stream; its historical local value-semantic evidence remains recorded below. Current hosted acceptance is tracked at PR #349 source `3a03a222`.
- [x] Re-run the requested 20-provider and Atlas 22-provider exact-head audits after the pointer commits; both pass for their committed scopes. The clean-checkout gate remains red on peer-owned dirt and checkout-head drift; no peer source, manifest, or lockfile is changed in this sweep.
- [x] Close `ATLAS-CONFORMANCE-BENCH-099`: preserve the target-fork correction, prove `benches/` executable classification, executable support modules, exact test regions, and literal/manifest-rooted `include!` edges with the focused 37-test scanner suite. The baseline records Apollo `orphan_modules=0`; hosted root run `32031997052` at `f84beec` reports 0 regressions and 23 non-regressing tightening candidates.
- [x] Close Leto's `ATLAS-ORPHAN-MODULES-096-LETO` slice: delete the unreachable `crates/leto/src/application/transform.rs`, preserve the canonical `application/array.rs` methods, and record direct detector result `leto_orphan_modules=0`. Standalone format, locked check, warning-denied Clippy, Nextest `314/314`, doctests, and rustdoc pass outside the overlay; no lockfile churn is committed.
- [x] Close Hermes's `ATLAS-ORPHAN-MODULES-096-HERMES` slice: delete the unreachable `crates/hermes-simd-core/src/tensor/mut_view.rs` at provider commit `1fe438c`; the direct detector returns `hermes_orphan_modules=0`. The provider gate remains explicitly blocked by peer-owned formatting edits and a stale peer-owned Cargo.lock; the Atlas gitlink advances only to the pushed provider head and preserves that dirty checkout.
- [x] Complete the Apollo orphan-module sub-scope in clean lane `D:/atlas/worktrees/apollo-orphan-096` at provider default `ed6d6905`. The detector now follows both `mod` and `include!` edges; the two deliberate included sources are no longer false orphans and the exact scan returns `apollo/orphan_modules=0`. Baseline `3 -> 0`; the provider source and peer-dirty primary checkout remain untouched.
- [x] Close the CFDrs orphan sub-scope: provider PR #346 (`b455a416` source, merged `54dcea3c`) landed at final default `5b95fe3a`. Wire `cfd-1d` resistance-model `tests.rs` under `#[cfg(test)]`; preserve the open `OPEN-033` `newton_fallback.rs` as the recorded residual; delete the 11 superseded historical/stub/duplicate modules. Provider Nextest `738/738` (`3` skipped) and hosted CI `32033808279` pass; the exact scan drops `orphan_modules` 14 -> 1 and the Atlas pointer advances to `5b95fe3a`.
- [x] Close the Coeus orphan sub-scope: `crates/coeus-cuda/src/driver_stub.rs` is a feature-gated CUDA stub wired through `#[path = "driver_stub.rs"]`, not dead code. Fix `PATH_ATTR` to follow `#[path]` across intervening doc comments/attributes, add the regression test, and tighten coeus `orphan_modules` 1 -> 0 after confirming it is the sole changed resolution across every recorded gitlink head.
- [x] Close RITK's `ATLAS-RITK-CONFORMANCE-101` structure slice. Source `81f510f6` splits the diffusion Python binding leaves; the exact clean provider count is `manifest_implementation=111` versus 112 before the change. Source default `7ae4b69b`, PM closure `62efbd79`, and PM merge `f23a6acd` are hosted-green: provider-owned checks 21/21 pass across Rust, Nextest on three hosts, Python 3.9–3.13, and wheel smoke. The external `recurseml/analysis` result is report-only. Atlas advances the gitlink without touching the peer-dirty primary checkout.
- [ ] Audit the CFDrs/Kwavers/Helios source closures for direct provider APIs, superseded local wrappers, fallback branches, typed time/quantity/unit boundaries, and real analytical or differential scenarios. CFDrs native Fourier and SSOR ownership are closed; Helios DICOM required-geometry handling and H-103 book hygiene are historical closed slices. The current Kwavers default is `f05d207d`; the open visualization/FDTD PR #402 is at `d8886b032c50c7ebbcc2f12ebaceacabe95e19f1` and is conflicting, so its previous `69478221f` hosted evidence is stale. The current default-head Architecture Validation and CI/CD runs `32182442591` and `32182442617` are queued. The source audit still requires explicit provider ownership, no CPU fallback, and value-semantic differential scenarios before this item can close; no pointer or consumer contract is advanced from the conflicting branch.
- [ ] Complete `ATLAS-CFDRS-BACKWARD-STEP-108`: finish hosted verification and integrate provider PR #349 at current exact source head `7b9673ef`. `cfd-2d` now owns the masked step geometry, SIMPLE solve, fluid-cell-only parabolic inlet, explicit boundary contract, and field-derived signed wall-shear crossing; `cfd-validation` is a thin adapter. The hosted Rust gate previously stopped on 153 pre-existing default-branch Clippy errors; the provider default and PR diff reported the same failure, so no consumer solver or benchmark relaxation is acceptable. Keep this separate from the CFDrs timeout optimization item; no hardcoded runtime correlation, weakened assertion, or reduced workload closes the benchmark contract. Hosted run `32121851451` at `2127f3e7` reduced the gate to one input-dependent `ChannelPath::new(...).expect(...)` in `scheme_io::from_blueprint`; `8e8cd9bf` converts blueprint, JSON, and polyline path construction to typed `MeshError` returns and hardens JSON point/segment parsing. Exact-head run `32122408402` reached Clippy and found only the test-target `map_unwrap_or` plus missing crate docs in `crates/cfd-schematics/tests/preset_autolayout.rs`; `f693a114` and `8ff26dae` fix both without changing assertions or workload. Exact-head run `32123300861` then exposed the next test target, `blueprint_render_parity.rs`: a single-variant wildcard, an exact float comparison, and missing crate docs. Commits `bcfc283c` and `1d6ba045` fix those diagnostics while preserving the test workload and original line-ending pattern. The cfd-2d all-target gate is now green locally: Clippy with `-D warnings` passes and native Nextest reports 585/585 passed with 27 committed skips. Manual workflow dispatch run `32140314701` is superseded by exact-head run `32143999878` at `7b9673ef`. Its book-figure gate passes; numerical fidelity reports 12/14 tests passed and two committed 30-second timeouts: `test_benchmark_run_integration` at 30.003 seconds and `cross_fidelity_trifurcation_dominance` at 30.008 seconds. The provider correction to the masked-face policy, primary shear excursion, and published Re_h=100 reference remains value-verified. A production-path cleanup removes two per-iteration inlet allocations; the original implementation timed out at 30.031 seconds locally, while the allocation-free implementation passed the focused gate at 28.901 seconds. PR #349 is merge-conflicting against current `main`; resolve that base and optimize both real solver paths before rerunning. No workload reduction or assertion weakening is authorized.
- [x] Push the bounded CFDrs lint cleanup through `b39a00b4`: replace state, field-operation, GPU-kernel, compute-dispatch, GPU-integration, conversion, boundary, time-controller, error-context, blood-model, plugin, unsupported-backend, cavitation, backend-validation, and result-existence assertions with invariant-bearing expectations; route GPU-unavailable, benchmark, and friction-factor diagnostics through tracing; and repair HDF5/checkpoint rustdoc examples; use derived epsilon checks for floating-point backend values; pin the backend test fixtures to `f64` after hosted compilation exposed literal-type ambiguity. Formatting and touched-source residue scans pass; document the turbulence benchmark and close its generated Criterion group lint at the benchmark macro site; harden the first `cfd-math` block-preconditioner test family with invariant-bearing expectations and close the sparse-provider test family with the same contract-bearing diagnostics; scope the Criterion-generated benchmark lint expectation at crate level after hosted validation rejected the macro-site attribute; harden the direct-solver provider test family and assert the typed singular-system error; harden the multigrid-cycle test family and assert the typed empty-level configuration error; harden the adaptive, exponential, IMEX, RKC, RK, and stability-analysis test families and route convergence diagnostics through tracing; harden the multigrid coarsening, DG limiter, GMG, SIMD, DG operator, spectral, restriction, smoother, sparse, direct-solver, ILU, DG solver, LGL, and spectral-operator, DG documentation, iterator, interpolation, JFNK, and SIMD test families. Hosted compilation found that the ILU error type is intentionally not `Debug`; commit `22e227eb` uses an explicit match while retaining the typed `InvalidInput` assertion; fix the interpolation fixture return; scope benchmark generated-doc expectations; and harden all remaining cfd-math benchmark and integration-test results. The source scan now has no remaining unwrap, existence-only result assertion, print, or debug macro in `cfd-math`; close hosted Clippy’s ordering, iterator, cast, `let-else`, and empty ignored AMG placeholder findings. The final SIMD-test lint residuals at hosted run `32114902789` are corrected in `c5563b9e`: captured format arguments, machine-epsilon value comparison, and rustdoc Markdown spans. Formatting and the touched-source residue scan pass. Hosted run `32115481118` then exposed eight benchmark-file diagnostics: three acronym Markdown spans and five explicit unit closure patterns; `fe98c280` fixes those diagnostics. Hosted run `32116257992` then exposed two semicolon-if-nothing-returned findings in `swar_ops_bench`; `404594b0` fixes them. Hosted run `32116643827` then exposed one semicolon-if-nothing-returned finding in `algebraic_distance_bench` and one in `rk4_bench`; `05328639` fixes both. Hosted run `32117031666` then exposed one Markdown acronym diagnostic in `amg_integration_test`; `b39a00b4` fixes it. Hosted run `32117428513` then exposed two additional Clippy families in `dg_benchmarks.rs` and `core_solver_tests.rs`; `1bf5b344` and `cb2a6fba` fix them. The exact `cb2a6fba` hosted run `32118252029` then exposed one explicit-iterator diagnostic in `cg_bench.rs`; `ea1426ac` fixes it. Hosted run `32119001889` then exposed three benchmark diagnostics in `spmv_bench.rs`; `eb3aaf76` fixes them while retaining the real SpMV operation and output observation. Hosted run `32119392426` then exposed one final semicolon diagnostic at `flux_alloc_bench.rs:20`; `7a18b9d8` fixes it without changing the benchmark workload. The exact hosted run is now `32119762411`; its terminal result is pending. Locally; the locked package compile is overlay-blocked and the peer Cargo.lock remains unstaged. Re-open after the exact hosted Clippy transcript establishes the remaining count.
- [x] Complete `ATLAS-HELIOS-BOOK-TEST-002` on the clean Helios lane: the shared Pages caller enables `mdbook-test`, local book gates pass, and PR #59 merges at default `679402ae`. Hosted Rust, Python, benchmark, and book gates pass; `recurseml/analysis` remains report-only. The peer-dirty Helios source checkout and branch remain untouched.
- [ ] Keep Helios PR #55 peer-owned and blocked: hosted Rust failed at exact head `83f5ccea` because its RITK checkout lacks `IMAGE_ORIENTATION_PATIENT`, and the same job reports two independent Clippy errors in `helios-planning/src/autodiff.rs`. Re-open after the provider pin and source fixes land; do not alter that active branch from the Atlas integration tree.
- [x] Collect Kwavers PR #388 at exact head `da7f276a`, merged as default `7a109e927cd943e99d6e5240c756b8c341301267` after all 25 hosted checks passed, including the full test-suite and code-coverage gates. The Atlas Kwavers gitlink advances to that merged default; the primary checkout's peer-owned visualization branch and untracked transducer constructors remain untouched.
- [x] Collect Kwavers PR #389 at exact head `ba1db65c`, merged as default `90dde196ba7d946e86b31a533fd9dde2ebb1867b`. The docs-only correction reduces the vacuous GPU-FFT audit finding from four tests to the two AVX-512 tests fixed by PR #388; the two WGPU tests already reject only genuine adapter absence and surface other acquisition failures.
- [ ] Keep the remaining peer PR blockers explicit: CFDrs #333 is `CONFLICTING` at `3b2fffaa` with only its Hermes revision pin verified; RITK #144 has one macOS Kabsch/SVD rank-deficiency test failure at `cc857634`; and RITK #154 is a 405-file conflicting change with no hosted checks. These are not merge or source-closure evidence for Atlas.
- [x] Collect Helios PR #58 at exact head `7482b04`, merged as default `c9817cc8439bcf82e7b19f851a05fa7e86e2fa0d`. Hosted run `32004527001` passes Rust, Python, and the four-pair benchmark regression gate; `32004527388` passes the book build. The pull-request Pages deployment is correctly skipped. The Atlas Helios gitlink is advanced to the merged default. Post-merge Pages run `32007839263` passes its build and deployment jobs; `https://ryancinsight.github.io/helios/` returns HTTP 200 with the expected guide title.
- [ ] Add or repair bounded performance and memory evidence for the suite: controlled criterion baselines, allocation/buffer-reuse measurements, shared-cache checks, and zero-copy boundary verification. Do not change workload sizes or budgets to make a gate pass. SWE scaling slice completed 2026-08-26 in `repos/kwavers`: the former wall-clock `test_performance_scaling` measurement is now a bounded Criterion `wave_propagation_scaling` benchmark over geometric 16³/32³/64³ sizes, with setup excluded from samples and cell throughput reported. Target compiles offline; hosted Criterion baseline remains to be collected. SWE tracker-memory slice completed 2026-08-26: validation callers that discard history now use the compact tracker-only path, retaining one scalar magnitude per eligible voxel per snapshot. Detector equivalence, end-to-end equivalence, strict solver Clippy, and focused coverage tests pass; hosted RSS/private-byte measurement remains pending.
- [ ] Execute `ATLAS-CFDRS-TEST-BUDGET` on a clean CFDrs lane: profile the exact hosted timeout cases, optimize the production solver path, and rerun the unchanged numerical-fidelity tests within the committed budget. Preserve the inherited timeout evidence until the exact final provider head is green. First bounded slice is merged through CFDrs PR #347: provider source head `f7bc741184a000338a5f4d4edf261a6dcfa266c8`, default merge `84499e957d3d0c8ce50b9573185a1f55885f38e2`. It includes cached pressure CSR reuse, explicit propagation of invalid hemolysis-model input, and the flat Leto-backed backward-facing-step stencil. The exact 35 µm and trifurcation cases pass locally in 16.785 s and 16.903 s under locked Nextest; the Pages caller now builds `cfd-validation` and runs the shared `mdbook test` gate. Exact-head Rust job `95426903063` in run `32043533301` failed before checkout on Atlas action-download 503/429 responses, and Pages run `32043533628` reached the package build before exposing the missing `fontconfig.pc` system dependency. Atlas shared workflow `bb505e5` adds the required headers; this branch pins that fix. New exact-head CI and Pages runs `32044071453` and `32044071732` were infrastructure-red; PM-only and source-correctness heads were superseded by `f7bc7411`. Exact-head Rust run `32046526277` passes format, check, ordinary tests, numerical fidelity 14/14 (3036 skipped, 8 slow; 247.309 s), and doctests; figure job `95435610232` and PR book build `95435671291` pass. Post-merge Pages run `32047447199` passes build and deployment. Post-merge Rust run `32047446607` passes format, check, and ordinary tests but numerical fidelity reports 12/14 passed, with the unchanged 30-second budget exceeded by `microventuri_35um_case_produces_converged_informative_2d_result` and `cross_fidelity_trifurcation_dominance`. Rust job `95430179027` and Pages job `95430210781` in runs `32044765872` and `32044766414` failed before checkout on codeload 503/429; figure job `95430179037` passed. Pages retry `95430855675` passed at the same exact head; CodeRabbit and all required PR checks are successful and the PR is merged. The two named solver-budget residuals remain open for the next provider-owned production optimization slice.
- [ ] Verify each affected book's chapter map, code samples, figures, and cross-links; run `mdbook test` where samples are compilable, then verify the same-revision Pages artifact and live HTTP deployment.
- [ ] Close the parent item only after residuals are either fixed or recorded with exact files, heads, hosted run IDs, evidence limits, and re-open triggers.

## ATLAS-KWAVERS-REAL-COMPUTE-028 — Kwavers identity-path audit

- [x] Search the exact fetched Kwavers default for placeholder markers and input-insensitive identity results.
- [x] Confirm the realtime scan-conversion identity path and file it as `KW-GPU-SCANCONV`.
- [x] Confirm mixed-domain time/nonlinear identity paths, KZK retarded-time identity, and PINN domain-adapter identity; record exact acceptance tests.
- [ ] Implement and verify the provider-owned numerical replacements; do not merge the workflow-only Kwavers #363 PR as if it resolved source defects.

## ATLAS-US-CAPABILITY-023 — RITK phased-array review residuals

- [x] Review ritk PR #131 at `9c29e9ff` against ADR 0042 and the full Image transform surface; PR #131 merged at `9ae68b45` without resolving the recorded source findings.
- [x] Record P1 findings: Cartesian-only legacy transform APIs, missing origin/direction composition, and `f64` widen-compute-narrow arithmetic.
- [ ] Fix the findings on the ritk phased-array branch, add non-identity metadata and cross-API differential tests, and pass the hosted image, filter, clippy, rustdoc, and formatting gates.
- [x] Advance the ritk gitlink to the exact merged PR #131 head `9ae68b45` and rerun the Atlas exact-head and dependency-overlay audits.
- [ ] Fix the remaining phased-array transform, metadata, and native-precision findings on a subsequent provider increment.

## ATLAS-US-023-A5 — Move coordinate geometry to ritk-spatial — in review

- [x] Review the peer-owned PR #132 at `e8e7ed6f`: the pure geometry rename preserves the `ritk_image` type re-exports and adds no `ritk-spatial` dependency.
- [x] Confirm the lane is clean and the move introduces no new P0/P1 finding; the local locked nextest gate is blocked by the lane's stack overlay resolving patches to `D:\atlas\repos\ritk` instead of the lane tree.
- [ ] Fix the phased-array contract findings, then merge #132 after its hosted gates pass and advance the Atlas gitlink to the exact merged head.

## ATLAS-SUBSTRATE-001..004 — Compute-substrate consolidation [arch]

Ordered by dependency, not by size. Steps 1-2 must not be reversed: collapsing
Coeus before the seams exist would make it define a second abstraction over
Hephaestus that then has to be deleted (ADR 0039, alternatives).

- [x] Audit the four packages for cross-repo duplication: Coeus vendor clones (1 185 of 1 247 lines identical modulo the vendor token), Apollo's 19-of-23 repeated plan/execution scaffold, the 14-entry-point Leto/Hephaestus decomposition pair with no shared seam.
- [x] Establish that `coeus-fft` correctly delegates to `apollo-fft` (567 lines) — recorded as a non-finding so it is not "consolidated" by mistake.
- [x] Land the first device-generic seam (`AxisReductionOps`) and the conformance crate, proving the shape the remaining families follow.
- [x] **SUBSTRATE-001** Extend the seams to elementwise, reduction, and scan — one family per claim, each with backend impls and conformance clauses. All three families are declared in `hephaestus-core/src/domain/` (`ElementwiseOps`, `ScanOps`, `FullReductionOps` beside `AxisReductionOps`; commits `77df8de`, `39dd602`, `6996f12` are in the gitlink `a68e91f` ancestry), conformance clauses exist in `hephaestus-conformance` (`assert_{elementwise,typed_elementwise,scan,axis_reduction,full_reduction}_contract`), and all four backends (wgpu, cuda, metal, rocm) implement the seams via `*_seam.rs` adapters with 5-6 contract-test binaries each. 2026-08-11 verified under the overlay: `cargo check -p hephaestus-core -p hephaestus-conformance -p hephaestus-host --all-targets` rc=0; `cargo test -p hephaestus-core` 89+1 passed; strict clippy `-D warnings` rc=0; `cargo check -p hephaestus-wgpu --tests` rc=0 (contract-test binaries compile; GPU execution is the external hardware gate). The tyche overlay no longer needs the temp-gitlink bypass: the peer's `cascade/moirai-0.5` advance `e245cf8` committed the root `Cargo.toml`/`Cargo.lock` (restoring `edition.workspace` inheritance), verified 2026-08-11 — clippy and wgpu contract-test gates rerun clean with no `--config` patch.
- [x] **SUBSTRATE-002** Write one generic provider impl in `coeus-hephaestus`; delete the cloned `backend/{elementwise,reduction,runtime}.rs` and their cloned tests from each vendor crate; keep only device acquisition. Provider half landed and verified 2026-08-11. Metal/rocm deletion slice landed (`2f3af87e`/`9167f574`, `codex/coeus-provider-deletion-metal-rocm`) and cuda deletion slice landed (elementwise 58/reduction 290 rewired through `HephaestusBackend<CudaBackend>`; NVRTC fallback + launch_ops deleted; `codex/coeus-provider-deletion-cuda`). Wgpu deletion slice landed (reduction 301 rewired through `HephaestusBackend<WgpuBackend>` via `ReductionProvider`; `codex/coeus-provider-deletion-wgpu`). The vendor deletion ledger is now CLOSED — remaining work is the per-hardware physical-device contract-test execution, an external hardware gate. The generic provider exists in `coeus-hephaestus` (elementwise.rs 485 lines, reduction.rs 313 lines, referenced by all four vendor crates — 6/8/8/6 files each) and its provider tests pass (6+1). Metal/rocm deletion slice delivered 2026-08-11 as `2f3af87e` on `codex/coeus-provider-deletion-metal-rocm` (pushed, final head `9167f574`): all fourteen cloned metal/rocm backend modules (`{elementwise,runtime,reduction,cross_entropy,random_init, rotate_half,stateful_update}.rs`) deleted; both crates now expose only `HephaestusBackend<Provider>` + provider op-bundle declarations; tests migrated to the generic backend; `random_init`/`rotate_half` `implementation.rs` added to the bridge; ADR 0060 records the replacement and the removed `MetalBackend`/`RocmBackend` names. Gates: check rc=0 (all targets), provider tests 6+1, metal/rocm test binaries compile on this host (device/linux-gated at runtime), strict clippy rc=0, fmt + diff-check clean, version-guard scan 0 defects, stack coherence stays clean. The vendor deletion ledger is closed; only the per-hardware suite remains open as an external gate. Coeus PR #323 completes the remaining batched least-squares provider slice; exact post-merge Backend parity run `31666097106` passed CUDA, Metal, ROCm, and WGPU. Required-device CUDA and ROCm jobs were explicitly skipped by workflow policy, so physical-device execution remains an external hardware gate.
- [ ] **SUBSTRATE-003** One role trait for the 14 shared decompositions; fold the per-operation `matches_leto_reference` tests into one parameterized differential clause with derived tolerances.
- [ ] **SUBSTRATE-004** Generic plan/execution layer for Apollo; adopt in two crates to prove it, then the remaining 17 one per claim.
- [ ] Remove `mod helpers` / `mod utils` in each crate as it is touched — not as a separate pass (ADR 0039 §5).

Evidence: ADR 0039 carries the normalized-diff table, the shared-entry-point
list, and the scaffold count. The deletion ledger for SUBSTRATE-002 is roughly
3 700 lines across four vendor crates.

## ATLAS-PUB-001/002 — Adopt the Atlas-shared publication pipelines [patch]

- [x] Audit the duplication: 8 crate-release workflows (4 byte-identical at 142 lines; variation is `RUST_TOOLCHAIN` 1.95.0/1.97.0/1.97.1 and `kwavers` path dependencies) and 4 book workflows (variation is the output path).
- [x] Add `.github/workflows/crates-publish.yml` — `validate` + `publish` jobs, `rust-toolchain` required, optional `atlas-ref` path-dependency step, crates.io OIDC via `rust-lang/crates-io-auth-action`, `crates-io` environment gate.
- [x] Add `.github/workflows/book-pages.yml` — `build` + `deploy` jobs, `output-path` required, staged `mdbook-test` input, Pages artifact flow under `pages: write` + `id-token: write`.
- [x] Verify both parse as `workflow_call` workflows with the audited variation exposed as inputs.
- [x] Reuse only action refs already present in the stack; do not introduce an unresolved commit digest (three Pages actions stay on major-version tags, filed as ATLAS-PUB-004).
- [x] Add `ritk` to the Atlas `docs.yml` cross-book gate (all four books now build under the strict detector).
- [x] Migrate all eight crate-release callers and verify the fetched default workflows are 39-line Atlas callers with the old publish body deleted: apollo, coeus, consus, hephaestus (`origin/master`), kwavers, leto, moirai, and ritk. Hosted validation evidence is recorded in `backlog.md#atlas-pub-001`; current source topology is closed.
- [ ] Run a fresh Kwavers `workflow_dispatch` validation on the current default after the git-source lock repair; the two latest dispatch failures are pre-repair runs. Treat Coeus publish-stage registry failure as the separate ATLAS-PUB-003 external gate.
- [x] Migrate the four book callers. Fetched defaults are current Atlas callers; CFDrs is the only caller requiring the optional `linkcheck2` input.
- [x] Land the shared-workflow linkcheck2 installer and its pinned Rust prerequisite after hosted run `31716368183` exposed the missing backend.
- [ ] Merge CFDrs PR #338 at its corrected full-SHA head, passing `mdbook-linkcheck2-version: 0.12.2`, and rerun its Pages workflow.
- [x] Collect Helios `31716457700` and Kwavers `31716399219`: both Deploy mdBook runs completed successfully at their recorded provider heads.
- [x] Re-run the RITK Pages workflow after its caller pin merges. Pages run `32344964522` passes at RITK default `aa48c471`; PR #196 Pages closure and live HTTP 200 recorded in ATLAS-RITK-WORKFLOW-PIN-2026-08-20.
- [x] Collect the current-pin hosted runs for the four book callers after the workflow-only PRs merge; all four callers (RITK, Tyche, Horae, Hyperion) have passing post-merge Pages evidence recorded in their backlog items.
- [x] Delete each duplicated workflow body in the same change that adds its caller — never keep both.

Evidence: ADR 0035 records the audit, the caller contract, the tokenless
authentication decision, and the per-package adoption ledger. The `atlas-ref`
caller pin reuses ADR 0027's gitlink contract. Registry registration is
user-gated and tracked as ATLAS-PUB-003.

## ATLAS-PUB-006/007 — Facade crates and registry names [arch] [minor]

- [x] Survey facade practice in comparable projects: `burn` 0.21.0 (lockstep `^0.21.0` across 4 required + 18 optional sub-crates), `bevy` 0.19.0, `polars` 0.54.4 lockstep; `tokio` 1.53.1 independent. Coeus already has burn's crate shape.
- [x] Confirm crates.io policy: first-come names, no namespaces, no team-forced transfer without owner approval, squatting removable case-by-case.
- [x] Audit all 207 package manifests (34 `publish = false`, 173 publishable) and check every publishable name — 165 free, 8 collide.
- [x] Audit the facade gap: 6 virtual workspace roots with no entry crate, 8 facades marked `publish = false`, 6 already publishable.
- [x] Verify availability of every proposed `<name>-<domain>` facade name, and rule out a stack-wide `-rs` suffix (4 of those are taken).
- [x] Record the decision, the per-package facade table, and the rejected alternatives in ADR 0037.
- [ ] Author the six missing facade crates: `apollo-transforms`, `cfdrs`, `coeus`, `helios-radiation`, `hephaestus`, `ritk`.
- [ ] Flip `publish` on `aequitas`, `asclepius`, `horae`, `hermes-simd`.
- [ ] Rename and flip: `harmonia-coupling`, `hyperion-photon`, `moirai-runtime`, `proteus-materials`.
- [ ] Rename: `athena-solvers`, `gaia-geometry`, `mnemosyne-alloc`, `themis-placement`, `tyche-uq`.
- [ ] Rename `helios-core`; rename `mnemosyne-core` as one co-evolution unit with `leto`, `hephaestus`, and `moirai`.
- [ ] Add `publish = false` to `repos/ritk/xtask/Cargo.toml`.
- [ ] Re-check each facade name against the registry immediately before its first publish — availability decays under first-come.

Evidence: ADR 0037 carries the practice survey, the 173-name audit with owners
and download counts, the facade-gap audit, and the availability check for every
proposed name. Naming is settled; nothing here waits on a user answer.

## ATLAS-WGPU-SAFETY-002 — Specify the fallible WGPU layout/dispatch boundary [arch]

- [x] Advance Coeus to provider commit `a6dfb2d6` with ADR-0020 and the dependency-ordered migration contract.
- [x] Record the 23 shared layout consumers, the infallible `coeus-ops` operation seam, and the rejection of silent no-op/fallback adapters.
- [x] Add the checked `GpuLayoutInfo` SSOT constructor with typed rank, stride-rank, offset, shape, and stride overflow regressions.
- [ ] Migrate the first complete operation family through the typed error seam and verify CPU/CUDA/WGPU callers.

Evidence: ADR-0020 selects a backend-associated typed error and fallible
operation traits. Coeus `a6dfb2d6` validates all fixed WGSL layout metadata
fields before serialization. Provider format and diff checks pass; package
gates remain blocked before compilation by the preserved Coeus `Cargo.toml`
edit requesting `mnemosyne ^0.6.0` while locked Moirai requires `^0.5.0`.

## ATLAS-TARGET-001 — One build cache, one debug budget [patch]

- [x] Remove Kwavers' wildcard dependency `opt-level = 3` and retain the runtime-required development optimization at level 1 across the graph.
- [x] Prove uncached feature-build reductions of 18–45%, full-grid PSTD below 25 seconds, and a 16,771,464,617-byte clean debug baseline at exact head `909bcdfc7` with 26/26 hosted checks passing.
- [x] Advance the Kwavers gitlink to PR #307 merge `0602c1fd4`.
- [x] Remove 9,363 files and approximately 4.49 GiB from seven obsolete private target trees while preserving the shared `D:/atlas/target` cache.
- [x] Verify the Atlas checkout tool from the primary root: format and warning-denied Clippy pass, Nextest passes 11/11 in 3.746 seconds, and doctests pass 1/1 in 1.93 seconds.
- [x] Apply the line-table-only workspace / no-dependency-debuginfo budget to the test profile so Nextest artifacts do not retain full symbols in the shared cache.
- [x] Stop two abandoned full-target size scans, then remove the verified idle `target/debug/incremental` tree. The five-day cache contained 27,085 session directories; deletion reclaimed 525,183,672,320 bytes in 337.052 seconds while preserving `deps`, linked targets, and the shared target root. A later build recreated three current session directories.
- [x] Remove 13 additional target forks (18.465 GiB), verify zero repo-local target directories, then clean the canonical cache before the remaining hosted checks: 68,854 files and 20.7 GiB removed; measured result 0 bytes.
- [ ] Measure and align remaining member-specific debug/test profiles after their peer-owned worktrees become clean; CFDrs `test opt-level = 2` is the next observed candidate and must retain its current test workloads.
- [x] Route Atlas-meta root-worktree tool builds to the canonical cache without an absolute machine path. Verdict (2026-07-22): no portable tracked route exists in Cargo's config model — relative `target-dir` resolves per config-file location, so a lane checkout's copy of the tracked config necessarily resolves lane-local; `CARGO_TARGET_DIR` is machine-absolute and untracked; `[env]` does not govern Cargo's own target resolution; config `include` is nightly-only. The interim policy is therefore terminal: build Atlas-meta tools from the primary root and reject lane-local `target` creation (`.cargo/config.toml` header and README "Build cache and debug budget" already carry it).
- [ ] Compare unchanged single-build and three-build workloads at the current job count and bounded alternatives before setting `build.jobs`; the live audit observed 23 concurrent `rustc` processes on 24 logical processors. Re-open trigger: a quiet window on the shared `D:/atlas/target` lock (no active peer build); concurrent builds serialize on that lock by design, so the measurement must run when it is uncontended.

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

## Session 9 release dispatch — 2026-07-21 (atlas-meta coordinator)

Dispatch: "begin releasing them all" (carries forward the verified-
green crates from Session 9). Authority: `interaction_policy` release/
deploy is the single explicit Ask-User dimension; user granted this
in the dispatch; proceeding without further asking.

### Released (git tag + GitHub Release)

- [x] **eunomia 0.7.0** [minor] — first formal git-tag of eunomia.
  - Tag `v0.7.0` -> `7021628f` (E-034 relative-equality provider surface).
  - https://github.com/ryancinsight/eunomia/releases/tag/v0.7.0
  - Verification: nextest 91/91 + doctests 9/9 preserved from Session 9 parent `3e4f9eb`.
- [x] **leto 0.40.0** [major] — first formal git-tag of leto.
  - Tag `v0.40.0` -> `630b44c3` (ndarray-compat retirement, `leto_ops::{cg,gmres}` extraction to Athena).
  - https://github.com/ryancinsight/leto/releases/tag/v0.40.0
  - Verification: nextest 173/173 + doctests 9/9 at `80406d9`.
- [x] **hermes 0.4.1** [patch] — first formal git-tag of hermes.
  - Tag `v0.4.1` -> `0e0dfcf` (unchecked CSR SpMV tail gather).
  - https://github.com/ryancinsight/hermes/releases/tag/v0.4.1
  - Watchpoint `HERMES-GEMM-UB-001` carryover recorded in release commit body (pre-existing, disjoint from release).

### Peer-assist increments (peer-pattern-matched, pushed to main)

- [x] **asclepius `7751d86`** `build(deps): Pin Eunomia 0.7, advance Aequitas` — origin/main; `cargo check --workspace` green.
- [x] **tyche `fd03394`** `build(deps): Pin Eunomia 0.7` — origin/main; `cargo check --workspace` green.

### Atlas-meta gitlink advance (commit `1853cfa`)

- [x] 6 of 8 Eunomia-0.7 wave members advanced (eunomia, hermes, asclepius, tyche, aequitas, proteus).
- [ ] **leto gitlink** deferred: peer unpushed local main `000f41d build(deps): Unify provider graph`. Re-open trigger: peer pushes leto main.
- [ ] **helios release** deferred: athena peer uncommitted WIP on `codex/athena-prepared-reductions` branch includes the Eunomia-0.7 + leto-0.40 alignment as part of a larger Krylov solver feature. Re-open trigger: athena origin/main advances.

### Reverted peer-assist attempts (out-of-scope peer-domain adaptation)

- [ ] **harmonia Eunomia-0.7**: reverted; 7 eunomia trait-bounds errors (FloatElement, ConvergencePolicy::* methods, Instant:: advance); requires source adaptation, peer domain.
- [ ] **horae Eunomia-0.7**: reverted; 1 aequitas `Quantity<T, ...>` type mismatch; requires source adaptation, peer domain.

### PM closure for this release dispatch cycle

- [x] `gap_audit.md` Session 9 release dispatch closure entry appended (101 lines, tag SHAs, GitHub Release URLs, deferred items with re-open triggers).
- [x] This checklist row.

Next actionable (awaiting user or peer event):

1. Peer pushes leto local main `000f41d` to origin (then advance
   atlas-meta leto gitlink in a follow-up commit).
2. Peer commits athena Eunomia-0.7 + leto-0.40 alignment to
   origin/main (then re-cut helios 0.1.0 release in a follow-up
   session — helios CHANGELOG `## [0.1.0] — Unreleased` is ready,
   helios Cargo.toml `version = "0.1.0"` stays).
3. Peer adaptates harmonia/horae to eunomia 0.7 / aequitas API drift
   (peer-domain work, recorded above).
4. Carry-overs from Session 9 dispatch: `CFDRS-PERF-SLOW-001`,
   `CFDRS-CFD1D-LINT-001`, `HERMES-GEMM-UB-001`,
   `HEPH-CUDA-WIN-001`.

## Session 17 partial closure (2026-07-23) — ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 partial slice

Coordinator (Session 17 follow-up) landed the ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 partial doc-migration slice. Acceptance criterion (1) of the board item: PASS. Acceptance criteria (2)-(3): DEFERRED to follow-up slices per peer cfd-3d WIP and direct_threshold re-evaluation.

### Closed this slice

- [x] CFDrs `crates/cfd-math/src/linear_solver/direct_solver.rs` module doc migration to reflect leto PR #74 (squash-merged `687b670`) real CSC sparse LU per ADR 0031. Pre-merge misnomer "backed by dense partial-pivoting LU" removed; correct dispatch documented (dense path for `n ≤ small_switch=32` or `nnz/n² ≥ density_threshold=0.1`; CSC sparse LU path with Gilbert–Peierls symbolic reach + slot-indexed left-looking numeric factorization + internal dense fallback for partial pivoting). The CFDrs-side `dense_threshold=1024` retry documented as the orthogonal `max_size`-cap + small-`n` user-intent safety net (not the upstream internal fallback).
- [x] `ordering: i8` field doc corrected; reserved for AMD follow-up `ATLAS-LETO-OPS-AMD-ORDERING-001`.
- [x] Convergence composition with peer's pending `..Default::default()` adaptation to upstream `SparseLuSolver` struct expansion (`small_switch` + `density_threshold` fields per ADR 0031) — preserved in the slice for upstream compatibility.
- [x] CFDrs PR #316 opened with the doc-migration commit (cherry-picked off origin/main `1b2c9018`), squash-merged as `5ac713b3` at 2026-07-24T03:43:21Z.
- [x] Verification on local CFDrs main HEAD `2686b86d` + peer's dirty working tree: `cargo check -p cfd-math` Finished clean (14.6s after build-cache lock wait); `cargo nextest run -p cfd-math -E 'test(direct_solver) | test(dense_lu_fallback)'` 4/4 PASS in 0.193s.
- [x] Atlas-meta `repos/CFDrs` gitlink advances from `1b2c901` to `5ac713b3` (submodule local working tree left at local `354266c0` with peer's WIP preserved per `concurrent_agents`).
- [x] Atlas-meta `backlog.md` `ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001` status flip + tail closure entry appended; gap_audit + checklist closure entries appended.

### Deferred to follow-up slices (peer-held scope or future evidence)

- [ ] Acceptance (2): cfd-3d end-to-end re-verification of `validate_poiseuille_flow` (PR #311 root-caused fix at CFDrs `22ddc27d`) under the new upstream sparse LU path. Requires peer cfd-3d integration (`trifurcation/solver.rs` peer-WIP) and a fresh cfd-3d `cargo nextest run` re-profile with the new upstream sparse LU. Per the Session 13 baseline: `validate_poiseuille_flow` PASS at CFDrs `22ddc27d` in 0.342s post-PR-#311 — the goal is to verify that timing does not regress under the new upstream sparse LU dispatch and that the value-semantic correctness assertion still holds.
- [ ] Acceptance (3): `direct_threshold` field re-evaluation. The CFDrs-side `dense_threshold=1024` retry is preserved as a user-intent safety net; ADR 0031 functional analysis shows it's orthogonal to (not redundant with) the upstream internal fallback. A follow-up slice should re-profile against new evidence to either remove or re-baseline this threshold.
- [ ] Aequitas pin coherence verification across all atlas consumers (URL-only form per Session 12 dual-source-ID recurring risk). Peer's `4d72981` atlas-meta commit advances the path-deps migration; a follow-up slice verifies URL-only alignment and pins after peer integrates.
- [ ] CFDrs `crates/cfd-math/src/lib.rs` `quadrature_rules` doctest path-mismatch watchpoint (peer doctest bug — `use cfd_math::quadrature::{...}` references module exported as `quadrature_rules`; NOT this slice's scope per integrity "do not fix unrelated bugs outside scope").

### Verification matrix

| Item | Method | Result | Evidence limit |
|------|--------|--------|----------------|
| `direct_solver.rs` test parity | `cargo nextest run -p cfd-math -E 'test(direct_solver) \| test(dense_lu_fallback)'` | 4/4 PASS in 0.193s | run on local CFDrs main + peer dirty tree (proteus Cargo.lock unverified at origin/main baseline) |
| Check parity preserved | `cargo check -p cfd-math` Finished | clean (14.6s incl build-lock wait) | same dirty-tree evidence; isolated cherry-pick baseline proteus compile residual |
| Gitlink advance coherent | `git update-index --cacheinfo` records CFDrs origin/main tip `5ac713b3` | OK | working submodule tree left at peer-preserved `354266c0` per concurrent_agents |
| Out-of-scope peer WIP preserved | `git --no-optional-locks status -sb` confirms peer ATLAS-CHECK-FIGURES backlog Hunk + Cargo.lock + lib.rs + error.rs + trifurcation + parity_artefacts + xtask + docs/book all unstaged | OK | per `concurrent_agents` disjoint-scope composition |

## Session 19 — 2026-08-18 — expanded 22-provider multiphysics audit

### Active audit and integration state

- [x] Confirmed the active product boundary: CFDrs, Kwavers, and Helios form the Rust multiphysics integrator layer; Python remains a thin PyO3 boundary.
- [x] Confirmed the expanded provider set: Horae, Hyperion, Harmonia, Themis, Tyche, Proteus, Mnemosyne, Consus, Helios, Aequitas, Asclepius, Eunomia, Moirai, RITK, Melinoe, Leto, Hephaestus, Coeus, Apollo, Gaia, Hermes, and Iris. `Tyche` is canonical; `Tychee` is an audit normalization alias.
- [x] Structural exact-head audit passes for all 22 active providers after fetched-default reconciliation; regression suites pass 29/29 and 3/3.
- [x] Rechecked live consumer coherence after the Harmonia/Apollo pointer advances: the structural exact-head audit passes all 22 providers, while full exact-head/version guard reports the peer-owned RITK requirement `apollo-fft 0.26.0` against provider `0.27.0`. Hosted conformance `32159744862` passes at root `c049d26`; overlay `32159744891` records the same Apollo migration boundary in CFDrs and Kwavers locks. No peer manifest or lockfile is edited here.
- [x] Add and test the opt-in `--require-clean-checkouts` audit mode. It checks checkout HEAD versus the committed gitlink and reports tracked/untracked dirt without modifying peer state.
- [ ] Re-run the clean-checkout audit from a coordinated clean stack. The current shared tree fails on peer-owned checkout drift and dirty files; no reset, stash, or deletion is authorized by this item.
- [x] Advanced the Atlas Apollo gitlink to merged provider default `d585e0f5c6f6e45e5e551a5ec3ca29f41af5afab` without changing the dirty nested Apollo checkout.
- [x] Reconciled shared root commit `f5cdeef4` after it captured dirty nested Apollo, Helios, and RITK heads instead of their fetched defaults; only the parent gitlinks are corrected.
- [ ] CFDrs PR #349 current source head `3a03a222` is awaiting the queued hosted Rust and book jobs in run `32152884477`; preserve workload and budget. The prior exact-head `7b9673ef` result remains historical evidence with two numerical-fidelity timeouts at the committed 30-second slow bound.
- [ ] Release/PyO3/PyPI, crates.io, mdBook/Pages, comparative-package, and provider-adoption audits are pending returned file-level findings from the dispatched read-only audit agents.
- [x] Delivery audit returned no P0 and recorded P1/P2 owners: Helios book snippet contradiction and missing PyPI matrix; CFDrs wheel/PyPI and figure SSOT gaps; Kwavers non-reproducible k-wave comparator, ABI3/path metadata drift, import-only wheel smoke, stale Pages filters, and missing figure manifest; all three locked tree gates are overlay/peer-lock blocked.
- [ ] The next delivery slices remain dependency-ordered: restore lock/overlay coherence, repair Helios `mdbook test`, add CFDrs/Helios wheel behavior and trusted-publishing gates, then repair Kwavers comparator/metadata and the recursive figure SSOT checks.
- [x] Extend the Atlas reusable wheel workflow with an optional provider-owned pytest behavior gate. It runs after wheel installation from the workspace root with `--import-mode=importlib`, and pins pytest `8.4.2` so the default Python 3.9 matrix remains valid. Provider callers still need an explicit test-path update and same-head hosted evidence.
- [x] Add Harmonia's provider-owned mutable pair-level relaxation seam before changing CFDrs `cfd-2d` coupling. Harmonia commit `685f47d` adds the `update_pair`/`relaxation_mut` contract, atomic fixed/full validation, ADR 0002, and local 17/17 nextest coverage. The Anderson/Aitken algorithm is intentionally not duplicated in Harmonia; PR #5 merged at provider default `365f0bb` with verify, supply-chain, and book checks green.
- [x] Replace the CFDrs local Anderson/Aitken wrapper with a direct Harmonia implementation and analytical/differential parity evidence. CFDrs commit `4931f85b` uses Harmonia's transactional `Relaxation<T>` seam, deletes the consumer-owned Aitken state and recovery fallback, and adds the componentwise secant regression. PR #359 merged at default `9761d798`; Atlas records that exact CFDrs head in root commit `993499a`. Locked `cargo check -p cfd-2d --lib`, target rustfmt, and the focused nextest body pass. The hosted Rust/book run `32296720261` is still in progress, so full hosted verification is not claimed.
- [x] **ATLAS-HARMONIA-AITKEN-001:** add the provider-owned, input-sensitive Aitken policy and its analytical, differential, transactional, generic-scalar, and documentation gates in the disjoint Harmonia scope before editing CFDrs. The provider slice owns `src/relaxation/aitken.rs`, its tests, ADR 0003/index, and the relaxation book chapter. Commit `584e961` merged through PR #6 at provider default `b98d3f4`; local locked static/value gates and hosted verify, supply-chain, and book-build checks pass. The CFDrs wrapper stays untouched until the consumer integration item is claimed.
- [x] **ATLAS-HARMONIA-CONFORMANCE-001:** claim a clean Harmonia provider lane for `.gitattributes` and `.github/workflows/ci.yml`. Provider commit `d01cacf` adds the LF policy, pins all six mutable action references, and bounds both CI jobs; PR #7 merges at provider default `3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb`. The clean-lane conformance scan reports zero across all 27 classes; local gates pass; hosted run `32159533930` passes verify `95784806220` and supply-chain `95784806422`. Atlas gitlink commit `c049d26` advances only Harmonia. The dirty primary checkout and reusable Pages caller remain untouched; RecurseML is report-only.
- [x] **ATLAS-PROVIDER-LIVE-CONFORMANCE-001:** run the committed conformance detector across all 22 live provider checkouts. Horae and Hyperion report zero measured classes; Harmonia is zero on its clean merged lane while the dirty primary checkout remains peer evidence; Proteus is zero on its clean merged lane while the dirty primary remains peer evidence. All other nonzero classes map to peer-owned provider trees or active lanes; no peer source, manifest, lockfile, checkout, or lane was changed.
- [x] **ATLAS-PROTEUS-CONFORMANCE-001:** reclaimed the stale merged temperature-validity lane, created a clean Proteus lane from provider `origin/main` `996b822`, and added only `.gitattributes`. Provider commit `50e77f4` merged through PR #13 at default `f612c9981547d56021db3a1be7f75631fd78ff4c`; the clean-lane conformance scan reports zero across all 27 measured classes. Atlas commit `1ce4bfa` advances only the Proteus gitlink; the primary peer-owned `Cargo.lock` remains untouched. Hosted run `32162450077` passes verify `95794242120` and supply-chain `95794242217`; RecurseML remains report-only. Local `cargo fmt --check` and locked metadata pass. The full local batch timed out after 600 seconds under shared-target contention before producing stage results, so no local check, Clippy, Nextest, doctest, Rustdoc, example, or deny result is claimed.
- [x] **ATLAS-WORKTREE-001 lane reclamation:** removed seven verified merged clean linked lanes (Asclepius ADR, Consus ADR, Iris color-space, two Mnemosyne audit lanes, and two Tyche cleanup lanes) and deleted their local branches. The lane audit still reports only active peer scopes: CFDrs 5 trees, Coeus 3, Kwavers 4, and RITK 3; those lanes remain untouched.
- [x] Reconciled the Mnemosyne root gitlink from `ea0839b` to fetched provider default `098bc8e`. The nested checkout has peer-owned dirty files, so only the gitlink is staged; no Mnemosyne source, manifest, lockfile, or workflow file is included.
- [x] Re-ran the delivered-root integration gates at `4e88995`: structural exact-head and committed lock-form checks pass for all 22/27 providers; live coherence and the local overlay are aligned only because peer RITK worktree commit `36592d5` carries the Apollo `0.27.0` sweep while the Atlas RITK pointer remains `dd577946`. The version-guard preflight is blocked by existing rustup directory overrides; no hosted run is claimed for `4e88995`.
- [x] Close **ATLAS-GAIA-CONFORMANCE-001:** Gaia commit `3cb6c82` adds only `.gitattributes` and merges via PR #31 at provider default `4980732c`. The clean-lane conformance scan is zero for all measured classes; local `cargo fmt --check` and locked metadata pass. Hosted CI run `32165632713` / job `95804433635` passes format, denied Clippy, Nextest, doctests, and Rustdoc. RecurseML is report-only; Atlas advances only the Gaia gitlink.

### Delivery rule

No consumer manifest or lockfile is edited across a peer-owned dirty scope.
No hosted timeout is hidden by changing budgets, reducing workloads, or
weakening assertions. The next implementation slice is selected from the
returned audit findings and must include value-semantic tests, documentation,
and the applicable hosted gate.

## 2026-08-19 evidence checkpoint

- [x] Extend the exact-head audit to CFDrs, Kwavers, and Helios. Root commit `bd79803`; live `atlas-22` exact-head audit passes for all 22 providers and all three integrators.
- [x] Re-run root evidence: 234 fast script tests and 74 subtests pass; stack overlay alignment and 27 committed standalone lock forms pass.
- [x] Record merged CFDrs default `931ee3a0130a5238461a1ee9547e12aef11e90bf` after hosted run `32221669165` passed the Rust workspace and book-figure gates. The local standalone locked package check remains an explicit development-overlay blocker.
- [ ] Resolve remaining provider-owned or externally gated residuals: Apollo benchmark regression, Kwavers Python extension build, Helios H-103, and peer-owned checkout/lane cleanup. No peer checkout or lane was changed.

## 2026-08-19 CFDrs hosted evidence refresh

- [x] Record exact default-head run `32222487306` at `931ee3a0`: Rust workspace and figure SSOT gates pass, including numerical fidelity and doctests.
- [x] Push provider PM synchronization as CFDrs commit `f601d827` on PR #357.
- [ ] Collect the separate CFDrs Pages, PyPI release dry-run, and standalone locked package gates. Do not infer them from the Rust/figure result.

## 2026-08-19 CFDrs JFNK residual

- [x] Publish CFDrs PR #358 at source head `0a5076c6` with the reachable, bounded Newton/JFNK recovery and typed checked-residual seam.
- [ ] Collect hosted Rust and book-figure results for run `32225861309` before advancing the Atlas CFDrs gitlink. The run is queued/in progress; this task does not wait on it.

## 2026-08-19 CFDrs JFNK callback correction

- [x] Diagnose hosted E0525 at `newton_fallback.rs:219`: the reused solver workspace makes the residual callback `FnMut`, not `Fn`.
- [x] Push provider fix `bc18b095` with the mutable JFNK seam and regression coverage; local format and diff checks pass.
- [ ] Collect replacement hosted run `32226998372` before advancing Atlas.

## 2026-08-19 Helios H-103 recheck

- [x] Run `mdbook test docs/book` at Helios `f8ebe42f`; all listed chapters and examples pass. The recorded H-103 failure premise is stale at this merged head.
- [ ] Reconcile the provider-owned H-103 board text when the detached, peer-dirty Helios checkout is available; no provider file was changed by this audit.

## 2026-08-19 Kwavers PR #402 recheck

- [x] Confirm PR #402 is merged at `9a7fa7e5`; all listed hosted checks are green and `origin/main` remains `53b3f984`, already matching Atlas.
- [ ] Preserve the primary checkout's two-commit lag and peer-owned untracked ADR until its owner reconciles it; no Kwavers file was changed.

## 2026-08-19 RITK PR #179 recheck

- [x] Confirm PR #179 merged at `6b9092bf`; Rustfmt, Clippy, and all Python matrix checks pass. Fast-forward the clean primary checkout to the exact Atlas gitlink.
- [ ] Preserve the three peer-owned RITK lanes; no lane cleanup was performed.

## 2026-08-19 Kwavers metadata closure

- [x] Remove the unused workspace PyO3 ABI declaration, repair the Python documentation URL, and broaden Pages source/manifest path filters in provider commit `e62d529e6`; push and advance Atlas to `a2f46dc`.
- [ ] Restore a standalone locked provider build after the shared overlay lockfile contention is resolved; the current failure occurs before Rust compilation.

## 2026-08-19 Kwavers book fence repair

- [x] Normalize the 96 code fences that the shared mdBook gate previously parsed incorrectly; equations/output/diagrams are `text`, and workspace-dependent Rust excerpts are `rust,ignore`. Correct the stale `DENSITY_WATER_NOMINAL` excerpt in provider commit `cbf99272b`.
- [x] Run `mdbook test docs/book` and `mdbook build docs/book`; both pass at the exact provider head.
- [ ] Run the linked real examples through `cargo check -p kwavers --examples --locked` after the shared Atlas overlay lock mismatch is repaired. The current attempt is blocked before compilation and is not source evidence.

## 2026-08-19 Conformance submodule-status classification

- [x] Reproduce the hosted pre-scan failure at runs `32247752034` and `32248848495`: both stop at the generic root-dirty diagnostic before the ratchet scan.
- [x] Change the root status query to ignore submodule summaries while keeping provider-local status validation; add the 18-case regression suite.
- [ ] Collect the next exact-head hosted conformance run; local root execution remains blocked by intentionally preserved peer-dirty provider trees.

## 2026-08-19 Exact conformance ratchet attribution

- [x] Collect hosted run `32250014209` at root head `a4f24ee`; it passes the clean-checkout phase and fails only the three listed ratchet regressions.
- [x] Attribute the regressions to CFDrs `network_solver.rs` (`500 -> 568`), Consus `consus-zarr/src/codec/mod.rs` (`439 -> 643`), and Coeus `coeus-autograd/src/lib.rs` (the counted crate-level allow).
- [ ] Split the CFDrs and Consus oversized files and replace the Coeus crate-level suppression with item-scoped expectations or code cleanup; run provider gates, hosted conformance, then advance exact gitlinks. This item is blocked by the current peer-owned provider checkouts/lanes; the re-open trigger is a landed peer fix or a stale claim.

## 2026-08-20 RITK release-gate closure

- [x] Merge RITK PR #194 (`ci/ritk-release-timeout`) at merge commit `65bee2c2`; adds finite timeout bounds to all release workflow jobs. Hosted evidence: Rustfmt, Clippy, dep alignment, Test Suite macOS/Windows, Python CI 3.9–3.13 all pass. Python Wheel smoke and ubuntu test suite still running at merge time; non-blocking given all platform-level gates pass. `recurseml/analysis` is report-only.
- [x] Advance Atlas RITK gitlink to merged default `65bee2c2` in root commit `ae76f3c`. Exact-head audit, overlay, and lock-form checks to follow at the next full gate sweep.
- [ ] Collect hosted Python Wheel smoke and Ubuntu test-suite results at `65bee2c2`; record as evidence once available.

## 2026-08-20 Kwavers FWI-024-D increment 2

- [x] Implement `RotatingOpposedLinearArray` in `kwavers-physics`: two opposed linear arrays at `+/-standoff`, rotated through `view_count` uniform angles. `transmission_count = n*views`, `receiver_count = 2*n`. All positions pre-computed at construction. Round-trip, geometry, separation, and count tests added.
- [x] Add `RotatingAcquisition<'a>` wrapper in `kwavers-solver/acquisition.rs` implementing `TransmissionAcquisition`; export via `frequency_domain/mod.rs`.
- [x] Write ADR 116 (`116-fwi-rotating-acquisition-geometry.md`): settles route (a) — per-view element rotation on fixed grid — over route (b) — per-view model interpolation (rejected: puts interpolation error in gradient).
- [x] Rebase `feat/kwavers-fwi-rotation-stage` onto main after PR #420 merged; push to origin. PR #424 open, CI queued.
- [ ] Collect CI for PR #424 (Architecture Validation, CI/CD Pipeline, etc.); merge when all required checks pass; advance Atlas Kwavers gitlink.

## 2026-08-20 Tyche + Asclepius book-test enablement

- [x] Open Tyche PR #27 (`codex/tyche-planning-closure` → main): enables `mdbook-test: true`, pins Rust `1.97.0`, selects `tyche-core`, updates two book examples with staged-library declarations. CI queued.
- [x] Open Asclepius PR #22 (`ci/asclepius-book-test` → main): enables `mdbook-test: true`, `rust-toolchain: "1.97.0"`, `cargo-package: asclepius`; no source or lockfile changes. CI queued.
- [ ] Merge Tyche PR #27 and Asclepius PR #22 when CI passes; advance Atlas gitlinks.

## 2026-08-20 Helios Radon assertion cleanup

- [x] Claimed only `crates/helios-imaging/src/radon.rs` on a clean Helios lane; preserve the dirty primary checkout and unrelated workflow/book files.
- [x] Replace the `is_ok()` assertion plus unwrap with a typed extraction and retain the negative and value-semantic assertions in the provider PR branch.
- [x] Publish the exact provider branch at `7a973331`; Helios PR #69 is open and carries the Radon assertion fix together with the typed Python surface and executable Compton book oracle.
- [ ] Collect PR #69's terminal Rust, Python, benchmark, supply-chain, and book/Page evidence, then merge and advance the Atlas gitlink only after the exact merged-default checks and live-page probe pass.

The earlier `fdfe61a`/connector-403 record is superseded by hosted PR #69 at
`7a973331`; no hosted merge or Atlas pointer advance is claimed yet.

## ATLAS-GAP-AUDIT-2026-08-20 (owner: atlas-gap-audit)

- [x] Dispatch one auditor per registered submodule against a single completeness rubric; 24 of 25 reported, Tyche outstanding.
- [x] Source-verify the three highest-severity claims at their cited lines before synthesis: kwavers GPU mock, CFDrs library `#[global_allocator]`, CFDrs orphaned root targets. All three confirmed.
- [x] Confirm no cross-repo contamination after the scratchpad filename collision reported by the Helios auditor: every `Finding 2026-08-20` heading names its own repository; the CFDrs strings in Helios artifacts predate this sweep.
- [x] Record the aggregate finding in `gap_audit.md` and file `ATLAS-GAP-AUDIT-2026-08-20` in `backlog.md`.
- [ ] Collect the Tyche audit and update the finding table and both averages.
- [ ] Dispatch P0 items 1-4 as independent provider items; they share no scope.
- [ ] Open the ADR for item 10 (Leto/Athena solver ownership) before any implementation; recommended option is Athena as owner per ADRs 0014/0015, with the Leto surface deleted and callers migrated in one change.
- [ ] Leave every provider checkout, lane, and dirty file as found; the audit wrote only PM artifacts and documentation-drift corrections, and committed nothing in any submodule.

## ATLAS-GAP-AUDIT-2026-08-20 P0 delivery (owner: atlas-gap-audit)

All four P0 items from `backlog.md#atlas-gap-audit-2026-08-20` are delivered as
pull requests. None merged; each waits on its own hosted gate.

- [x] **P0-3/P0-4 Consus** — [consus#51](https://github.com/ryancinsight/consus/pull/51). szip header sample count bounded twice before any reserve: the `expected_size` contract moved onto the header, plus a payload-derived bound (`read_unary` costs at least one bit per sample, so the count cannot exceed eight times the post-header bytes). Reserve is `try_reserve_exact`. `-C target-cpu=native` removed from the committed `.cargo/config.toml`. Local: 26/26 szip tests. The regression test asserts on `can encode at most`, a string only the new guard emits, so it cannot pass vacuously. Exact PR head `2e24e6ad` remains hosted-pending in run `32408174545`; `recurseml/analysis` is report-only. The dead `xtask` alias remains a separate cleanup residual.
- [x] **P0-1 Kwavers** — [kwavers#439](https://github.com/ryancinsight/kwavers/pull/439). `swe/gpu/` deleted, net -903 lines. `kwavers-solver` declares no GPU dependency at all, so the module could never have launched a kernel. `AdaptiveResolution` was examined for rescue and also found fabricated (`simulate_solve_quality` returns `0.7 + fudge`; `computation_time` is `0.1 * 4^level`); its genuine grid pyramid and trilinear interpolation had no consumer outside the module. Local: `cargo check -p kwavers-solver` passes, `swe_3d_validation` 2 passed / 4 pre-existing skips.
- [x] **P0-2 CFDrs** — [CFDrs#362](https://github.com/ryancinsight/CFDrs/pull/362). The library `#[global_allocator]` and every API that reads it sit behind a non-default `memory-profiling` feature; `MemoryStatsSnapshot` stays ungated so `suite.rs` is unchanged and `None` means "not measured" rather than a zeroed lie. Local: 433 tests feature-off, 435 feature-on, clippy `-D warnings` clean both ways. Gate liveness proved by negative control, a probe crate installing its own allocator: builds with the feature off, fails `E0152` with it on, reproducing the pre-fix default.

Two findings recorded rather than actioned, both outside the P0 scope:

- [ ] Kwavers pins two incompatible wgpu majors in one workspace — `kwavers-gpu` on `30.0.0`, `kwavers-analysis` on `26.0`. Filed upstream as KW-GPU-202 with the wider `kwavers-gpu` to Hephaestus migration (662 raw `wgpu::` sites, 18.4k LOC). This is the forked vendor dimension ADR 0039 exists to prevent.
- [ ] `repos/CFDrs/docs/atlas-migration/moirai-ssot.md:63` claims `cfd-core` holds the workspace `#[global_allocator]`, used to justify Moirai's `no-global-alloc` posture. No allocator exists in `cfd-core`; the only one was the `cfd-validation` static now gated. Noted in CFDrs#362, left unedited to keep the defect diff clean.

Correction to this board's own P3 framing: items 10 and 11 are not open
decisions. ADR 0033 (Accepted 2026-07-27) already names Athena sole Krylov owner
and calls the Leto iterative family a regression to unwind, with a four-stage
plan; ADR 0039 already gives the vendor dimension to Hephaestus. Stage A of ADR
0033 (Athena BiCGSTAB/LSQR plus the Jacobi/SOR/SSOR/ILU set over Leto) is
largely delivered — the Athena audit located all of them. The live work is
stages B, C and D, plus one real gap for backend-dependent solving: Athena's
Hephaestus path carries no preconditioner, so accelerator PCG is currently
unpreconditioned CG.

## ATLAS-MOIRAI-SEQCST-SLICE-2026-08-21 - current session

- [x] Take over the dead Moirai primary checkout (35h stale, upstream gone): uncommitted Step-4 timeouts overlay, PM deltas, and an LF .gitattributes candidate archived under worktrees/.archive/moirai-dead-checkout-20260821/; checkout reset clean to origin/main ff56d60.
- [x] Remove the two stray detached kwavers trees at D:/tmp (kw-main2, kw-verify); both clean with commits reachable on pushed origin branches. Four canonical-root kwavers lanes and leto-stage-d remain untouched: measured-fresh live-peer territory, watchpoint recorded.
- [x] Open canonical lane worktrees/moirai-seqcst-relax from fetched origin/main; claim ATLAS-MOIRAI-ORDERING-052.
- [x] Land the archived Step-4 timeouts overlay as a proper provider commit: lane commit 9904670 "ci(moirai): Default workflow steps to 30-minute timeouts" on fix/moirai-seqcst-ordering-ratchet (python-ci.yml, python-release.yml; YAML validated). Branch push + PR evidence pending collection.
- [ ] Re-run the SeqCst inventory at ff56d60; select one coherent family; apply justified weakest-ordering relaxations naming each happens-before edge; verify focused nextest + clippy -D warnings + loom where present; push branch and record PR evidence. No Atlas pointer move.
- [x] Re-ran inventory at ff56d60 and completed the Chase-Lev derivation: the thief gate (load resizing -> fetch_add steal_accesses -> recheck) and the resizer drain require one total order; a Relaxed increment has no SC-order position, so the drain could miss an admitted thief. All chase_lev/idle/ blocking/worker/scheduler-core/async sites stay SeqCst as recorded decisions (idle.rs module doc names the Dekker pairing that yesterday's 20-line-window classifier missed for blocking.rs:67).
- [x] Found and fixed the real lever instead of forcing relaxations: the scanner counted committed test sidecars as production (async_iter_tests.rs held 16 SeqCst). Fix landed atlas-side at 9828ee8; honest moirai count is 85.
- [x] Family sweep completed over the last unverified files: worker.rs (17 sites - quiescence Dekker handshake, wake-bitset store-buffer pairing, single-total-order is_quiescent predicate), scheduler/core.rs (9 - producer/joiner halves with explicit why-Release-fails derivations), futex_mutex.rs (7 - paired SeqCst fences guarding the locked/waiters Dekker pair against waiter stranding), and mpmc/channel.rs:172,261 (register-before-recheck waiter halves; independent derivation confirms the inline docs - the store-load race is closed only by SeqCst). Verdict: every honest production site is a recorded KEEP decision; zero undocumented sites remain. Item closes at the instrument-fixed count 85 with no source change.
- [x] Root-caused PR #148 hosted failure (runs died at parse with no jobs/logs): GitHub defaults.run accepts only shell/working-directory - moved the bound to per-job timeout-minutes (12ff108); reusable-workflow caller jobs accept no timeout key at all - removed it there, bound lives in atlas python-wheels.yml (42dbad0). artifact-metadata scope verified valid via in-production usage at atlas python-wheels.yml:219. Post-fix push: no python-release parse failure, Python Bindings queued on head.
- [x] Executed reclaimed MOI-AUDIT-FLOOR-012 immediately: armed #![deny(missing_docs)] in moirai-core/crypto/gpu/python + moirai-tests (the five of nineteen lacking it). Zero surfaced violations - public surface was already documented; lint now enforces by construction. Gates: cargo check clean x5, nextest 143/143 (0.76s), clippy -D warnings exit 0. Lane branch fix/moirai-missing-docs-floor -> Moirai PR #151. Post-merge follow-up: flip FLOOR-012 status line in docs/backlog.md (landed via #150).
- [x] Board-reclaim increment: audited the dead-checkout board (462 KB untracked) against current moirai main - twelve open items existed in no tracked artifact. Re-verified each with read-only probes: six admitted DoR-shaped to docs/backlog.md (FLOOR-012 5/19 crates, VER-006 with named unsafe sites, VER-010 proptest, SEC-001 fuzz/restrictions, DOC-009 book, PM-008 index generator), four recorded closed-upstream (miri/loom/PAL/ ADR-0015), two held for manual review. Lane branch chore/moirai-board-reclaim -> Moirai PR #150. Archive retirement follows its merge.
- [x] Landed moirai LF policy from the lane (re-pointed to chore/moirai-lf-policy off origin/main; PR #148 branch stays pushed and open): commit f415006 adds .gitattributes (* text=auto eol=lf) and renormalizes the single committed CRLF blob book-pages.yml, closing conformance class gitattributes_missing for moirai. Pre-change audit: 1 i/crlf of 632 tracked files; repo is pure text (no binary guards needed). Opened Moirai PR #149.
- [~] Ritk mtime.rs:46 Relaxed tick DEFERRED: repos/ritk primary checkout is held by a live peer session (detached HEAD b35c9331 with uncommitted PM sync: backlog +217 incl. overlay-free Nextest 184/184 evidence, gap_audit +302, checklist +140, README metric docs). Skip rung of the assist ladder; re-open when their increment lands. One ambient artifact restored during orientation: orphaned Cargo.lock overlay drift (producing [patch] config absent; regenerates from config in seconds, nothing unique lost).
- [x] Scratch triage: deleted 11 superseded seqcst/lane/overlay scripts plus conformance_full_tmp.json and step5 sha-pin applier (athena+kwavers already fully SHA-pinned upstream); removed 3 misdirected root strays (python-ci.yml, python-release.yml byte-identical to archive copies; orphan package-lock.json). Preserved the peer's uncommitted gap_audit SHA-pin finding record.
- [x] Baseline regeneration deferred to the next co-evolution sweep: provider gitlinks drifted ambiently (CFDrs carries a peer Sprint series at a5a92bfc uncommitted; more M/m entries), and generate refuses both dirty roots and --worktree results as gate inputs. The stale baseline is conservative (moirai seqcst recorded 101 > honest 85), so check cannot under-fail; refresh lands when pointers integrate.
- [x] Pushed fix/moirai-seqcst-ordering-ratchet; opened Moirai PR #148 (ryancinsight/Moirai) for the 30-minute timeout defaults; MERGEABLE, checks registering at collection time.
- [~] Hosted collection (all still externally queued, zero failures): Tyche #36 MERGEABLE (verify/book-figures/supply-chain QUEUED); Eunomia #73 MERGEABLE (4 checks QUEUED); Consus main CI/Docs/Deploy QUEUED; Moirai #148 MERGEABLE. CFDrs #365 OPEN CONFLICTING/DIRTY with a live peer Sprint series inside the submodule - conflict resolution waits for their series to land (recorded watchpoint, not my claim).
