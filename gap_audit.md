# atlas — kwavers/CFDrs/ritk → Atlas migration gap audit

## State refresh (2026-07-17) — Apollo dispatch verification merge

- **Finding:** Apollo’s GPU dispatch execution already used Hephaestus and
  Leto, but its verification tests were embedded in a dense 589-line leaf.
- **Correction:** Apollo PR #46 partitions the tests into
  `gpu_fft/verification/dispatch.rs`, records the inverse-identity and
  `13*gamma_256` bound in ADR 0034, and merges at `11fd1d0`.
- **Evidence tier:** hosted required checks plus local value-semantic tests:
  Apollo Rust workspace and Python bindings pass; locked Nextest 393/393,
  Clippy `-D warnings`, rustdoc `-D warnings`, and provider audit 5/5 pass.
- **Provider audit:** Apollo owns no direct raw WGPU dependency; GPU device
  and dispatch infrastructure remain Hephaestus-owned.
- **Closure:** Atlas PR #18 merged at `56ad179`; `repos/apollo` now resolves
  to `11fd1d0` on the default branch.

## State refresh (2026-07-17) — Kwavers hosted closure

- **Finding:** PR #292 head `aa5d29f` contains the locked workflow and
  obsolete-deploy cleanup, but required hosted jobs are still queued.
- **Evidence tier:** local locked GPU/simulation/solver Nextest 1036/1036 and
  feature Nextest 144/144; Architecture Validation run `29593744645` and
  CI/CD run `29593747035` are queued.
- **Residual:** do not advance the Kwavers gitlink while its working tree has
  an uncommitted Cargo source-dependency edit or before required hosted checks
  complete.

## State refresh (2026-07-17) — ATLAS-INTEGRATION-007 RITK source checkout

- **Finding:** RITK PR #39 raised `apollo-fft` to 0.24 but its composite
  dependency checkout still selected the prior Apollo 0.23 source revision.
- **Correction:** RITK `main` `ffda3ec` checks out Apollo `157467e`; Atlas
  advances the RITK gitlink from `a5e375f` to that corrected default-branch
  head.
- **Evidence tier:** hosted integration evidence. RITK CI, Python CI, and
  Legacy Migration Audit runs `29591782642`, `29591782812`, and `29591780940`
  completed successfully.
- **Residual:** Kwavers #291 must complete its independent hosted matrix;
  the RITK correction itself has no remaining failed required check.

## State refresh (2026-07-17) — ATLAS-INTEGRATION-006 provider graph

- **Finding:** the fixed Kwavers checkout branch had stale Apollo, Hephaestus,
  Kwavers, and Leto pins plus non-compiling RITK batch commit `b1850302`.
- **Correction:** Atlas now stages Apollo `157467e`, Hephaestus `cf4df20`,
  Kwavers `2fb8661`, Leto `37968f7`, and RITK `a5e375f`.
- **Evidence tier:** exact staged gitlink equality and remote commit
  reachability; behavioral closure is delegated to the dependent Kwavers CI.
- **Residual:** the parent-pin branch must merge before default-branch users
  consume these revisions. ADR 0020 is the theorem SSOT.

## State refresh (2026-07-17) — merged provider pins

- Hephaestus PRs #40–#42 are merged to `origin/master` at
  `29ff2ff`; 0.16.1 preserves WGPU downlevel defaults when converting the
  typed device-limit contract.
- CFDrs PR #295 is merged to `origin/main` at
  `7d4c9edf`; its `GpuContext` now acquires a provider-owned `WgpuDevice` and
  exposes typed capabilities rather than raw WGPU adapter, feature, or limits
  fields. The grouped GPU nextest suites pass without cross-process device
  contention.
- CFDrs PR #296 is merged to `origin/main` at `a13f7f51`; retained
  one- and two-dimensional validation examples now execute the owning solver
  or model. The static/unexecutable three-dimensional reporting paths are
  deleted. The unresolved labelled-outlet boundary contract remains tracked
  in CFDrs as `CFD-3D-BIFURCATION-BOUNDARIES-1`, rather than being represented
  by a false root-level validation claim.
- Apollo PR #44 is merged to `origin/main` at
  `f26369eb2000b9a8b763066064173f8c5ebf8f65`.
- Helios PR #5 is merged to `origin/main` at
  `04e496b7370bcf9201f5cf5aecdc7a43ca148f8a`.
- RITK PR #37 is merged to `origin/main` at
  `ec7cb8329898835c3e63b6c307afb4919a37af78`. Its CI passes formatting,
  dependency alignment, Clippy, migration audit, wheel smoke, Python 3.9–3.13,
  and Ubuntu/macOS/Windows Nextest. The prior macOS DICOM release failure is
  closed by the `A-RELEASE-RQ`/`A-RELEASE-RP` lifecycle boundary; upstream
  transport correction is tracked in Enet4/dicom-rs#811.
- RITK PR #38 is merged to `origin/main` at
  `0dd71e5219dfc83c2d9538c3cdb48983e7657a44`. It synchronizes only the
  Hephaestus patch metadata in the provider lock graph; Rustfmt, Clippy,
  dependency alignment, migration audit, wheel smoke, Python 3.9–3.13, and
  Ubuntu/macOS/Windows Nextest all pass before this root pin refresh.
- Primary Atlas and peer worktrees remain dirty and out of scope; Atlas PR #9
  merged the clean lane's gitlink and root-artifact update at `e3380b6`.

## State refresh (2026-07-15) — MOI-NUMA-001/002/003/004 closure: deleted `moirai-iter/src/numa.rs`

- **MOI-NUMA-001/002/003/004 — CLOSED** per ADR 0017 (accepted).
  1. **MOI-NUMA-001** (`NumaPolicy` stored but never applied) — eliminated by deletion.
  2. **MOI-NUMA-002** (raw `libc::mmap`+`syscall(SYS_mbind)` in iterator crate) — eliminated by deletion. Mnemosyne already owns NUMA-tagged segments with per-node pools; Themis owns topology/placement.
  3. **MOI-NUMA-003** (sequential single-threaded "batch" functions) — eliminated by deletion. Real NUMA-aware parallel iteration uses `moirai_parallel::ParallelIterator`.
  4. **MOI-NUMA-004** (fake `async fn` with discarded errors) — eliminated by deletion.
- Removed files: `moirai-iter/src/numa.rs`, `benchmarks/benches/numa_context_comparison.rs`.
- Edited: `moirai-iter/src/lib.rs` (removed `pub mod numa`), `benchmarks/Cargo.toml` (removed `[[bench]]` entry), `benchmarks/tests/benchmark_contracts/iter_source_contracts.rs` (removed `numa_iter_consumes_owned_batches_without_clone` contract test).
- Verification: `cargo check -p moirai-iter` clean, `cargo nextest run -p moirai-iter` 185/185 pass, `cargo nextest run -p moirai-benchmarks` 68/68 pass.
- ADR: `D:/atlas/docs/adr/0017-moirai-numa-path-redesign.md` (Accepted).
- Zero external consumers confirmed (no crate imports `moirai_iter::numa`).

## State refresh (2026-07-16) — root integration conflict resolution

- **ATLAS-INTEGRATION-001 — CLOSED**. Merged the Atlas integration branch with
  `main` in a clean worktree. The migration PM artifacts remain authoritative;
  the README now registers Helios and current Hephaestus 0.15 consumers.
- **Gitlink evidence tier**: Git object ancestry. Each conflicted submodule
  resolves to a commit reachable from its current remote default branch;
  Coeus is `093f31f` and Gaia is `9e48102`.

## State refresh (2026-07-15) — moirai CONTENTION-001 closure: perf branch merged to main

- **MOI-CONTENTION-001 — CLOSED**. `perf/moirai-contention-audit` merged to `main` at
  `9cd650f` (merge commit). Contains 3 commits: scheduler themis cache_levels fix,
  moirai-async sync primitives feature (Condvar/Mutex/oneshot/mpsc/macros), and
  ATLAS-MOIRAI-016 cancellation/waker-leak fixes (NoopWaker pre-registration,
  ID-based waiter tracking, rx_waker Drop cleanup). Verified: `cargo check` clean,
  `cargo nextest run -p moirai-async` 82/82 pass. Pushed to `origin/main`.
  Atlas parent gitlink advanced `e3d1a30` → `9cd650f` (staged, uncommitted).

## State refresh (2026-07-15) — Apollo/Coeus/RITK consumer closure

- **RITK PR #31 (`codex/ritk-burn-ndarray-cleanup`) and PR #32 — ✅ MERGED**
  to `origin/main` at `be75a93a` and `4ba050ca`. All required CI passed
  (Rustfmt, Clippy, Workspace Alignment, Test Suite on ubuntu/macos/windows,
  Python 3.9-3.13, Python Wheel, CodeRabbit, Audit burn migration). The Atlas
  gitlink now advances to `4ba050ca`.
- RITK local evidence confirmed pre-merge: 5,229/5,229 nextest tests with 26
  skipped, doctests, warnings-denied Clippy, fmt, warning-free rustdoc, and
  clean `burn-migration-audit`. 14 Burn manifests and 645 Burn-surface source
  files remain as dependency-ordered peer-owned residuals (sub-batches
  #3.g–#6).
- The documentation closeout CI runs 29377346830, 29377346839, and
  29377346848 also pass; the external `recurseml/analysis` status errored on
  the closeout range but is not a protected required check.
- **RITK PR #33 — ✅ MERGED** to `origin/main` at
  `17b84bdc18c2395d6329f3435ed3d860d1c72e00`. The final docs-head matrix is
  green: CI run `29421402596` (Rustfmt, dependency alignment, Clippy, wheel
  smoke, and Linux/macOS/Windows nextest), Python run `29421402755` (Python
  3.9–3.12 on Linux/macOS/Windows), and audit run `29421402503`; CodeRabbit is
  also green.
- The merged RITK state has 13 Burn-dependent manifests and 641 Burn-surface
  source files. The residual is dependency-ordered Coeus/Leto consumer work,
  not a compatibility alias or fallback. Native extrema now read a fallible
  host slice rather than allocating a full `Vec`; the migration-audit fixture
  roots use process-plus-sequence uniqueness and RAII cleanup. These are
  source/data-flow memory and isolation improvements; no unbenchmarked speedup
  is claimed.
- Full RITK nextest recorded three registration tests over the 30-second slow
  threshold (30.510s, 35.422s, 37.823s). Profile-guided performance residual,
  not a timeout or correctness failure.
- Hermes PR #6 is merged at `1423e41d`; the parent pointer is correctly
  advanced (ancestor of `origin/main`).
- Apollo PR #8 is merged at `6e99a567c118f6bf5790f80346475b44db2c7555`.
  Authoritative CI run `29381809234` passed the Rust, Python, documentation,
  provider-audit, RustSec, and dependency-policy jobs. The external
  `recurseml/analysis` status is non-required.
- Coeus PR #209 is merged at `2026a0b65e363496b5ab79b09612f26b7729f9d5`,
  aligning Mnemosyne 0.4, Hephaestus 0.13/WGPU 30, and Themis 0.10. The first
  RITK consumer run failed at the stale Coeus `mnemosyne ^0.3.0` constraint;
  RITK PR #33 completed successfully against the merged provider graph.
- The invalid Moirai submodule metadata was repaired locally by changing
  `.git/modules/repos/moirai/config` from `core.bare=true` to `false`; peer
  source changes and its dirty Cargo.lock remain preserved.

## State refresh (2026-07-15) — Moirai async contention and retention audit

### Discovery (prior)

The merged Moirai async synchronization surface at `repos/moirai` commit
`5514040` had three provider-owned residuals:

- `moirai-async/src/sync/condvar.rs:26-34` drops the mutex guard before the
  notification future registers. A concurrent notifier can acquire the mutex,
  publish the condition, and notify before registration; the waiter then
  sleeps through that notification.
- `moirai-async/src/sync/mpsc.rs:79-110` stores send waiters and
  `:157-176` stores receive waiters, but the corresponding future drops do not
  deregister them. Cancelled futures therefore retain wakers and can retain
  task state until channel closure or a later message, increasing memory use
  and wake contention.
- `moirai-async/src/sync/oneshot.rs:86-111` does not clear `rx_waker` when the
  receiver is dropped. A live sender can retain the cancelled receiver's
  waker until the shared state is released.

### Fixes applied and verified (2026-07-15)

All three findings fixed in `repos/moirai/moirai-async/src/sync/`:

- `condvar.rs`: `wait()` pre-registers the waiter in the `WaitQueue` while
  still holding the `MutexGuard`, using a `NoopWaker` placeholder that gets
  replaced on first `poll`. This closes the lost-notification window.
- `mpsc.rs`: Rewritten to use ID-based waiter tracking
  (`VecDeque<(u64, Waker)>`). `SendFuture` and `RecvFuture` on `Drop` remove
  their waiter by ID. Two regression tests verify cancellation cleanup.
- `oneshot.rs`: Added `Drop for RecvFuture` that sets `shared.rx_waker = None`,
  preventing the waker leak.

Verification: `cargo check -p moirai-async` clean (0 warnings);
`cargo nextest run -p moirai-async` 82/82 passes (80 existing + 2 new
cancellation regressions), no slow tests. Cross-repo follow-up:
`ATLAS-MOIRAI-016` — ✅ done.

## State refresh (2026-07-13) — peer dirt and local artifacts

- `repos/kwavers` is actively changing under peer-owned verification. The
  2026-07-12 clean-tree snapshot below is historical evidence, not current
  working-tree state.
- `worktrees/` is required local infrastructure: one registered RITK lane plus
  11 junctions that resolve sibling Atlas path dependencies. It is ignored, not
  deleted. Its private generated target cache consumed 325,213,153,514 bytes and
  was removed; builds continue to use `D:/atlas/target`.
- The untracked `fix_doc_links.py` was an unreferenced, non-idempotent one-off
  mutator that stripped unresolved Rustdoc links. It was removed rather than
  promoted to tooling.
- RITK's uncommitted native NGF slice is not deliverable: it locally substitutes
  a fixed-index grid for a missing first-party image operation, retains dual
  substrate paths, and clones fixed coordinates per evaluation. The operation
  must be implemented in the owning provider and consumed directly before the
  slice can pass the no-shim and allocation-discipline gates.
- Evidence tier: Git object/state inspection, filesystem metadata, process
  inspection, and semantic diff review.

### Apollo WGPU 30 provider integration

- Apollo `96e67a2` consumes pushed Mnemosyne `4a9d2a3`, Moirai `c43f86a`, Leto
  `8651dfc`, and Hephaestus `090611d` revisions. Atlas advances Mnemosyne to
  descendant `01e7de7`, which retains the allocator removal and adds the
  pooled-segment lifetime correction. Mnemosyne deletes the raw-pointer
  allocator contract WGPU cannot represent safely; Hephaestus 0.13 owns one
  WGPU 30 ABI; Apollo 0.15 removes the WGPU 26 and archived `paste` graph.
- Release gates pass: warning-denied Clippy and rustdoc, 1029/1029 Rust nextest
  cases, 34/34 Python cases, doctest, provider audit, RustSec, cargo-deny policy
  checks, and applicable pre-1.0 API checks. GPU f16 and STFT paths execute on
  real WGPU devices and validate value semantics or typed device-limit errors.
- Residual risk: cargo-deny reports 12 permitted transitive multiple-version
  families. They originate in current provider dependencies and are not a
  source, license, advisory, correctness, or Apollo release blocker; no skip
  suppression hides them.
- Evidence tier: compile-time and documentation enforcement, value-semantic
  Rust/Python tests, real-device differential tests, dependency-source
  inspection, and API/supply-chain tools.

### Historical Apollo 0.14 provider integration

- Apollo `a4742bb` consumes one exact standalone-Git-resolvable provider graph:
  Mnemosyne `eb0d941`, Hermes `51c530f`, Moirai `b2f3732`, Leto `1b125ce`, and
  Hephaestus `f726742`. It removes the inert Moirai feature request and
  propagates callback-ownership failures through the public WGPU boundary.
- Release gates pass: warning-denied clippy and rustdoc, 1027/1027 Rust nextest
  cases, 34/34 Python cases, doctest, provider audit, RustSec, cargo-deny, and
  196 applicable `apollo-fft` minor-release API checks. The intentionally
  fallible WGPU constructor is correctly classified as a major API change.
- Historical constraint: Apollo remained on latest-compatible WGPU 26.0.1 because
  Hephaestus 0.12 publicly exposes that ABI. WGPU 30 migration also removes the
  current `ordered-float` cap and archived `paste` advisory exception. This is
  provider-owned follow-up. `ATLAS-WGPU-030` closes this constraint with Apollo
  0.15 and WGPU 30.
- Evidence tier: compile-time and documentation enforcement, value-semantic
  Rust/Python tests, dependency-source inspection, and API/supply-chain tools.

> State refresh (2026-07-12): gap_audit.md last active edit was 2026-07-08.
> kwavers inner HEAD has advanced by 40+ commits since then, resolving Batch #1–#4
> (Rayon, ndarray, nalgebra, Burn migrations). See `## State refresh` below.

> Cross-repo consolidator: per-repo gap audits (`repos/kwavers/gap_audit.md`, `repos/CFDrs/docs/gap_audit.md`/`backlog.md`, `repos/ritk/gap_audit.md`) remain authoritative for repo-local gaps. This file records:

>

> 1. Three cross-repo architect coord items (CR-1/CR-2/CR-4) carried out of `docs/audit/2026-07-02-cross-repo-integration-audit.md`;

> 2. Migration evidence inventory (off-tree residual that was hidden from individual repo gap audits);

> 3. Provider-extension register with file-line anchors;

> 4. Provider-side obstacles that block consumer migration until the provider extension lands;

> 5. Atlas architectural directive (2026-07-08); consolidator framing -- stack table, migration targets, design principles, constraints, bulk-migration priority order.



---



## State refresh (2026-07-12) — superseded batch status

> Empirical re-verification against current tree. Evidence tier: grep/basher/dep-tree.

### kwavers consumer-side migrations — substantially complete

Verified at kwavers inner HEAD `7c70d1b1d` (`codex/kwavers-core-moirai-parallel`, clean WT).

| Migration batch | gap_audit status (2026-07-08) | Current status (2026-07-12) | Evidence |
|---|---|---|---|
| **#1 (Rayon→moirai par_for_each)** | OPEN: 41 sites / 15 files | **CLOSED** — 0 sites | `grep -rn "par_for_each" repos/kwavers/crates/ --include="*.rs"` = 0 |
| **#2 (ndarray→leto)** | TRACKING: 2,496 line-hits | **CLOSED** — 0 `use ndarray` imports, 0 direct `ndarray` dep | `grep "use ndarray\|^ndarray\b" repos/kwavers/crates/ --include="*.rs"` = 0; crate Cargo.tomls have comment-only ndarray refs |
| **#3 (nalgebra→leto)** | OPEN: 13 sites / 5 manifests | **CLOSED** | `grep -rn "nalgebra" repos/kwavers/crates/` = 0 |
| **#4 (Burn→coeus)** | OPEN: facade WIP | **CLOSED** — 0 burn in source/manifests | `grep -rn "burn" repos/kwavers/crates/ --include="*.rs" --include="*.toml"` = comments only |
| **Tuple shapes→array syntax** | N/A (post-gap_audit) | **DONE** | 110 files in `fe6d2a174` (non-PINN) + `a4124b9d4` (PINN) |
| **`.slice().unwrap()` restoration** | N/A | **DONE** | 26 sites in 3 files (`fe6d2a174`) |
| **Boundary Leto traversal** | N/A | **DONE** | `e6bc57130`: 21 files, −158 net lines, deleted `parallel.rs` bridge |

40+ commits landed on kwavers since the gap_audit baseline `35ee01076`, including Batch #1 source-side slices 1–9, kwavers-core/source/signal/grid/field→leto, Complex/ndarray types→eunomia, and workspace-wide ndarray↔leto boundary fixes.

### Key gap_audit entries — stale / superseded

- **Bulk-migration priority #1** lines 315–418: 41/15 par_for_each → 0
- **Bulk-migration priority #2** lines 319, 347–418, 563–793: 2,496 ndarray hits → 0 imports
- **Bulk-migration priority #3** line 320: 13 nalgebra sites → 0
- **Bulk-migration priority #5** line 323: surface met → fully closed
- **E0599 closure-front** lines 772–806: 151 .view()/.view_mut() → resolved by boundary migration
- **KW-CV-001/002 watchpoints** lines 1063–1072, 1704: trigger exceeded (42+ commits since creation)
- **Batch #1 partial-closure marks** lines 1717–1747: all superseded

### Remaining open items

| ID | Scope | Class | Notes |
|---|---|---|---|
| **CR-2** | Global allocator → DI handle | `[arch]` | Batch #6; low urgency |
| **GPU provider abstraction** | kwavers-gpu kernel-buffer | `[arch]` | gap_audit provider register |
| **eunomia Complex64 SSOT** | csr.rs numeric trait | `[arch]` | Verify if Complex→eunomia migration resolved |
| **CLD-2** | Wire kzk_solver_plugin→HIFU | `[minor]` | CHECKLIST.md:5727 |
| **SOL-10/11** | Rustdoc sweep; CI k-wave validators | `[patch]` | CHECKLIST.md:5726 |
| **Phase 1 Foundation** | 100% audit | `[foundation]` | CHECKLIST.md:5730 |
| **BOOK-CH24/CH26** | PyO3 import contract | `[patch]` | gap_audit.md:4317 — partial |
| **COV-5** | Shell models | `[minor]` | gap_audit.md:4787 — partial |


## Atlas architectural directive (2026-07-08)

> Migration target framing per the consolidation directive. All

> subsequent tactical PM artifacts (`## Cross-repo architect coord

> items`, `## Migration evidence inventory`, `## SSOT enforcement

> surface`, etc.) operate under the directive framing below. This

> section is the single canonical reference for the architectural

> stack, migration targets, design principles, constraints, and

> bulk-migration priority order; tactical content lives in the

> sections below.



### Provider stack (11 atlas crates)



| Atlas crate | Role | Replaces | Gitlink SHA |

| --- | --- | --- | --- |

| `mnemosyne` | Memory allocator (consolidator; library crates pass handle via DI per CR-2 target axiom [open; Batch #6]) | (consolidator) | `98a02b61ccb8ce04f5b1920113d8315cae193ae8` |

| `themis` | Memory allocator (consolidator pair with mnemosyne) | (consolidator) | `2b6a3ace712acad0a3a5107f0e5a10cb290f22d0` |

| `moirai` | Runtime + async + parallel | `tokio`, `rayon` | `37ff12d584e1fb472f41b4e40c702d708aba1dac` |

| `hermes` | SIMD | `std::arch::*`, `packed_simd` | `c7b17b02c73a81648af2bf8781a261e359a01165` |

| `melinoe` | Branded types / cells | `ghostcell`, `typenum` | `375108b6fe4386c2bffdb584460403c838ca35e8` |

| `leto` | CPU ndarray/nalgebra alternative | `nalgebra`, `ndarray` (CPU path) | `86d366bc0e909b9aeb1df695170e4279dbc58781` |

| `hephaestus` | GPU ndarray/nalgebra alternative | `nalgebra`, `ndarray` (GPU path) | `676a260552b013f873ce7b9e5db62a68631ae793` |

| `coeus` | PyTorch/JAX/Burn alternative (autodiff + tensor + nn + optim + sparse + fft) | `burn` | `006f2a7968d713d561fa02b3d205575cf07a8a70` |

| `apollo` | FFT (rustfft replacement; pure-Rust SIMD FFT + MMS polynomial oracle) | `rustfft` | `e6ecce49c9f7df0c338422a8974aae907f00f90b` |

| `eunomia` | Numeric traits (SSOT for `NumericElement`, `FloatElement`, `RealField`, `Complex<T>`) | `num_traits`, `num_complex` | `7f84beb2a8b1e2aeb08f0b4e865a175fc40b3e9b` |

| `ritk` | Image toolkit (provider for kwavers / CFDrs / helios DICOM + spatial + interpolation + transform + io) | (bespoke image-processing crate family; provider-side) | `529d6651671622da76346ce9e2193e6a717cc97d` |



### Consumer migration targets (3 simulation suites)



| Sim suite | Role | Gitlink SHA |

| --- | --- | --- |

| `helios` | (consumer; radiation therapy sim suite, built atop the same provider stack) | `5f6aef65a47d716f26452592d3a91f3d934a2ffc` |

| `kwavers` | (consumer; acoustic / ultrasound / wave-propagation sim suite, built atop the same provider stack) | `ccc6bbf9e699def2bbefd2413e58c5c6698a79fb` |

| `CFDrs` | (consumer; computational fluid dynamics sim suite, built atop the same provider stack) | `72275347fb71ead3e0d5e5411560a335f6d29241` |



### Migration consumer targets (3 in flight)



Three consumer simulation suites are actively under migration to the

Atlas provider stack:



- **kwavers** (`D:/atlas/repos/kwavers`): acoustic / ultrasound /

  wave-propagation simulation suite. Migration scope: all 24

  internal crates + root workspace. Active migration axes:

  Rayon->moirai (Batch #1), ndarray->leto's `ndarray-compat`

  (TRACKING), nalgebra->leto (small scope, 13 sites / 5 manifests),

  Burn->coeus (Batch #4, manifest + source surface met; awaits

  KW-CV-001 watchpoint trigger).

- **CFDrs** (`D:/atlas/repos/CFDrs`): computational fluid

  dynamics simulation suite. Migration scope: 7 inner crates +

  root workspace. **Batch #2 (nalgebra -> leto + nalgebra-sparse

  -> leto-ops `CsrMatrix`) CLOSED 2026-07-05** per `d58d1fe3`

  (the Atlas-provider migration push, 752 modified + 19 added

  files, 51,857 insertions / 22,087 deletions, ~2,500 tests

  pass, 0 warnings).

- **helios** (`D:/atlas/repos/helios`): radiation therapy

  simulation suite. Migration scope: domain/physics + DICOM

  real-input integration. **H-061 / H-062 CLOSED 2026-07-07**

  (production DICOM ownership through `ritk-dicom`; unused

  `num-traits` + aggregate `dicom/ndarray` feature edges

  stripped). H-063 imaging-toolkit decomposition pending.



### Design principles (consolidator-binding, 11 axioms)



- **SRP** (Single Responsibility Principle): per-module ownership

  surface -- `coeus-core::Scalar`, `eunomia::NumericElement`,

  `moirai::Scope` each hold one bounded responsibility.

- **SoC** (Separation of Concerns): provider

  (let''o / hephaestus / coeus) vs consumer (kwavers / CFDrs /

  helios) layered separation. Per `## SSOT enforcement surface`

  gate geometry below.

- **SSOT** (Single Source of Truth): trait surfaces declared

  once in the provider (e.g. `eunomia::NumericElement` for

  numeric traits, `coeus_core::ComputeBackend` for all backend

  traits, `moirai::Scope` for all async/parallel scopes). Per

  ADR 0005 (eunomia SSOT rebind), ADR 0012 (RITK burn-trait

  rebind), ADR 0010 (per-batch name pattern).

- **DIP** (Dependency Inversion Principle): consumer crates

  depend on provider traits, not on concrete implementations;

  permits backend substitution (CPU -> GPU, scalar -> autodiff,

  sync -> async).

- **DRY** (Don't Repeat Yourself): shared vocabulary lives in

  the provider (e.g. `Complex<T>` in `eunomia`, `Quaternion<T>`

  in `let''o`, `MoiraiBackend` in `moirai`). Per-repo

  reimplementations are prohibited.

- **Zero-copy**: view types (`MelinoeCell`,

  `ParallelSliceMut`, `let''o::ArrayView`) used wherever

  possible to avoid allocation.

- **Zero-cost abstractions**: trait dispatch monomorphized at

  compile time; no runtime polymorphism for inner-loop hot

  paths.

- **Zero-sized types (ZSTs)**: type-level markers (e.g.

  phantom parameters, sealed trait gates) used to carry

  compile-time-only information without runtime cost.

- **Phantoms**: `PhantomData<T>` for ownership / marker

  semantics without runtime representation (per `melinoe`'s

  branded-typed discipline).

- **GATs** (Generic Associated Types): for trait-bound returns

  that vary along the trait's generic parameter (e.g.

  `InterpolatorAtlas<T, B>`, `ResampleableAtlas<T, B, D>` per

  ADR 0012 sub-batch #1).

- **`Cow<'_, T>`**: borrow-or-own views used wherever the

  source may or may not be owned (publisher / consumer

  boundary; e.g. atlas-meta bulk-pointer-advance reads).



### Constraints (forward-only invariant, 4 axioms)



- **Rust-only + pyo3 for Python**: the entire stack is Rust.

  Python bindings (`kwavers-python`, `coeus-python`,

  `helios-python`, `cfd-python`) are `pyo3`

  `#[pyclass]` / `#[pyfunction]` surface only. No C / C++

  extensions; no `cdylib` other than pyo3's managed

  `abi3-py39` (or later).

- **Don't rename anything with "atlas"**: avoid the

  `atlas_*` / `atlas::` prefix on new symbols. The "Atlas"

  name is the meta-consolidator's brand, not a code-root.

  Migration push commits preserve original symbol names where

  possible.

  Current-tree correction (2026-07-09): existing transitional names such as

  `AtlasImage`, `TransformAtlas`, `InterpolatorAtlas`, and

  `ResampleableAtlas` violate this directive. Do not add another

  provider-branded symbol. Remove these names in the post-bulk RITK cleanup by

  completing the native public-surface migration in one breaking change; do

  not retain aliases or forwarding compatibility shims.

- **Bulk migration followed by cleanup**: prioritize

  batch-level code-replacement patterns over per-site

  hand-edits. The `disjoint-scope` rule allows atlas-meta

  bookkeeping + docs work without colliding with peer's

  source-tree changes; bulk migration lands across all peer

  crates in single commits, not file-by-file. Cleanup

  follows as a separate phase (test resolution, deprecated

  surface removal, allowlist contraction).

- **Resolve all test / example issues**: pre-merge

  authoritative classification (`cargo semver-checks` shape or

  full `cargo nextest run` pass) is required for any

  closure-mark promotion. Test residual (legacy 3-D PINN

  loss thresholds, `coeus-wgpu` CUDA-pending tests, etc.) is

  preserved as validation residuals, not weakened.



### Bulk-migration priority order (refreshed 2026-07-12)

Closure-progress count: 5 CLOSED + 1 OPEN (ritk Batch #3) + 1 CLOSED (helios).

| # | Migration | Source-scope | Provider gate | Peer status | Disjoint-scope |

| -- | --- | --- | --- | --- | --- |

| **1** | kwavers Rayon -> moirai (Batch #1 source-side) | 0 `.par_for_each()` sites at inner HEAD `7c70d1b1d` | manifest-strip CLOSED at `702e4f125` | **CLOSED 2026-07-12** | n/a |

| **2** | kwavers ndarray -> leto | 0 `use ndarray` imports; 0 direct `ndarray` dep at inner HEAD `7c70d1b1d` | n/a (leto native) | **CLOSED 2026-07-12** | n/a |

| **3** | kwavers nalgebra -> leto | 0 `nalgebra` in source/manifests at inner HEAD `7c70d1b1d` | n/a | **CLOSED 2026-07-12** | n/a |

| **4** | ritk Batch #3 (Burn -> coeus) source-side | see gap_audit lines 814–1039; atlas-meta advancing RITK submodule pointers (60+ native filter advances) | sub-batch #1+#2 CLOSED; sub-batches #3–#6 peer-WIP | OPEN | atlas-meta advances RITK gitlinks (60+ commits) |

| **5** | kwavers Burn -> coeus (Batch #4) | 0 `burn::` source residual at inner HEAD `7c70d1b1d`; manifest strip landed | CR-4 eunomia SSOT rebind landed | **CLOSED 2026-07-12** | n/a |

| **6** | CFDrs nalgebra migration push | 7 crates + nalgebra-sparse + num-traits; 51,857 / 22,087 deletions | n/a | **CLOSED 2026-07-05** (`d58d1fe3`) | n/a |

| **7** | helios H-061 / H-062 (DICOM + dep strip) | DICOM real-input closure through `ritk-dicom` | RITK provider (`ritk-dicom::{DicomTag, tags, DicomAttributeRead}`) | **CLOSED 2026-07-07** | H-063 imaging-toolkit audit pending |



**Migration queue summary (refreshed)**: 7 ordered targets. 5 CLOSED (kwavers #1/#2/#3/#5, CFDrs), 1 OPEN (ritk Batch #3), 1 CLOSED (helios).

Atlas-meta pending bookkeeping: 0 (all gitlink-aligned per the

`## Continual audit: WT dirty submodule classification (2026-07-08)`

section above). Future atlas-meta work is purely docs-only PM

artifact hygiene + parent-side gitlink advance on peer-driven

closure.

The `ndarray-compat` cargo feature on `leto`

(`repos/leto/crates/leto/Cargo.toml`: `ndarray-compat = ["dep:ndarray", "std"]`)

is a **transitional layer** for the kwavers ndarray → leto

Bulk-migration priority #2 — but **does not** resolve the E0369

errors (`Mul<f64>` not implemented for `leto::Array<T, S, N>`)

despite pulling `ndarray` into the resolved dep graph.

**Type-system distinguisher** (verified via `cargo tree -p kwavers-math`

+ `repos/leto/crates/leto/src/application/aliases.rs`): the four

explicit type aliases

```
pub type Array1<T> = Array<T, VecStorage<T>, 1>;   // aliases.rs:6
pub type Array2<T> = Array<T, VecStorage<T>, 2>;   // aliases.rs:9
pub type Array3<T> = Array<T, VecStorage<T>, 3>;   // aliases.rs:12
pub type Array4<T> = Array<T, VecStorage<T>, 4>;   // aliases.rs:15
```

confirm `Array<T, S, N>` is **leto's own native type** — the lack of

a `pub use ndarray::Array` re-export is what makes ndarray's blanket

`Mul<T>` impl inapplicable. ndarray's blanket `Mul<T>` impl

covers only ndarray's own `Array<T, D>`; it does NOT cross-type apply

to leto's distinct type. So `features = ["ndarray-compat"]` adds

ndarray as a transitive dep edge (verified: `cargo tree -p kwavers-math | grep ndarray`

shows `ndarray v0.16.1` resolved transitively via leto→ndarray) without

modifying type-system identity that E0369 complains about.

**Consequence for the Bulk-migration #2 closure path**: the only viable

fix is per-site source-code rewiring — patterns like

`array.iter_mut().for_each(|v| *v *= scalar)`, the project-native

`as_slice_memory_order_mut()` slice accessor, and the `scale_array`

helper in `crates/kwavers-math/src/simd_safe::auto_detect::ops` —

NOT a Cargo.toml-level feature add. Adding `ndarray-compat` would

re-inject a transitive ndarray dep edge already eliminated by Batch #1

(`702e4f125` ndarray/`rayon` feature strip).

**Routing discipline** (codifies the project's per-crate Cargo.toml

commentary rule): cargo-feature architectural essays belong in

`gap_audit.md` (this row); per-crate `Cargo.toml` comments stay as

1-line pointers (`# see gap_audit.md Bulk-migration priority #2 ...`)

so the architectural reasoning rotates to one SSOT instead of

fragmenting across every consumer crate's manifest. Per-crate Cargo.toml

comment tri-version history (11-line essay → 3-line note → 1-line

pointer)is recorded for future-auditor visibility.


### Bulk-migration priority #1 × #2 source-side overlap (2026-07-09)

The cross-batch migration surface between priority #1 (Rayon → moirai)
and #2 (ndarray → leto) consists of **41 residual sites across 15 files**
in `crates/kwavers-solver/src/**` under inner HEAD `35ee01076` (per
the line-71–93 retraction on `codex/kwavers-core-moirai-parallel`).
These are primarily `Zip::indexed(...).and(...).par_for_each(...)`
invocation chains. Modifying one site resolves both #1 and #2 batch
requirements simultaneously in one atomic per-file slice.

The target post-migration pattern is the project-native bridge helper
set in `repos/kwavers/crates/kwavers-physics/src/parallel.rs`. These
helpers are simultaneously Leto-typed (`use leto::{ArrayView3,
ArrayViewMut3}`) AND moirai-routed (`use moirai_parallel::{
enumerate_mut_with, for_each_chunk_pair_mut_enumerated_with,
for_each_chunk_triple_mut_enumerated_with, Adaptive};`). The supported
kernel-shapes: `for_each_indexed_mut`, `for_each_indexed_pair_mut`,
`for_each_indexed_mut_three_refs`, `for_each_indexed_mut_four_refs`,
`for_each_indexed_three_mut`, `zip_mut_ref`, `zip_mut_two_refs`,
`zip_mut_three_refs`, `zip_mut_four_refs`, `zip_two_mut_two_refs`,
`zip_two_mut_four_refs`.

The bridge helpers route back to baseline par-iteration primitives
in `repos/moirai/moirai-parallel/src/ops.rs` (FLAT path:
`repos/moirai/<name>/src/`, not the nested
`repos/moirai/crates/<name>/src/` form, verified on disk):

- `enumerate_mut_with` at line 125 — single-mut enumerated iterate (Adaptive-policy default)
- `for_each_index_with` at line 155 — index-domain primitive (no data buffer)
- `for_each_chunk_pair_mut_enumerated_with` at line 281 — pair-mut chunk-enumerate
- `for_each_chunk_quad_mut_enumerated_with` at line 335 — quad-mut chunk-enumerate
- `for_each_chunk_triple_mut_enumerated_with` at line 408 — triple-mut chunk-enumerate

For the Rayon-compatible trait shape, bindings route through the
`ParallelSliceMut<T: Send>` trait at
`repos/moirai/moirai-iter/src/parallel/sorting.rs:8` (`impl<T: Send>
ParallelSliceMut<T> for [T]` at line 42). **Slice discipline** (mirrors
the routing-discipline paragraph in the Bulk-migration priority #2
routing lesson above): each rewired site lives in a single peer-driven
per-file slice commit that simultaneously closes one #1 site AND one
#2 site. Per the `concurrent_agents` disjoint-scope rule, atlas-meta
records the overlap here; the 41 source-side sites remain peer-owned
on `codex/kwavers-core-moirai-parallel`, and the **KW-CV-001**
watchpoint remains the trigger for any atlas-meta pointer advance.


### Provider-extension register cross-link



For the missing-surface inventory (provider land), see

`## Provider extension register (provider land owned)` below. For

the provider-side obstacles blocking consumer migration (SSOT

gates), see `## Provider-side obstacles for consumer migration

(SSOT gates)` below. For the architectural decisions shaping the

directive, see `D:/atlas/atlas/docs/adr/` (especially ADR 0005

eunomia SSOT, ADR 0008 kwavers-math CsrScalar migration push,

ADR 0009 Batch #1 Rayon->Moirai CTE, ADR 0010 per-batch name

pattern, ADR 0012 RITK burn-trait rebind).



## Cross-repo architect coord items (CR-class)



| ID | Class | Title | Evidence | Status |

| --- | --- | --- | --- | --- |

| **CR-1** | `[arch]` | Delete `apollo-ghostcell` standalone GhostCell reimplementation; redirect all apollo sites to `melinoe::MelinoeCell`. | Source: `apollo/crates/apollo-ghostcell/src/lib.rs`; `melinoe/src/lib.rs:18-24,65-115,233` (`pub use cell::{MelinoeCell,MelinoeMut,MelinoeRef}`); `atlas/docs/audit/2026-07-02-cross-repo-integration-audit.md`:L71-75 ([arch] CR-1 citation). Closeout evidence 2026-07-07: Apollo commit `50029b7` deletes `crates/apollo-ghostcell`; stale Apollo-owned GhostCell plan removed; `repos/moirai/Cargo.toml` aligned to `melinoe = 0.8.0`; `cargo metadata --locked --no-deps --format-version 1` green in `repos/apollo`; focused nextest `-p apollo-validation melinoe` 2/2 green and `-p apollo-sft -p apollo-radon` 43/43 green. | **CLOSED 2026-07-07**. Evidence tier: source/static dependency graph + compile/build + value-semantic nextest. Full Apollo workspace, clippy, and Melinoe Miri not rerun in this closeout. |

| **CR-2** | `[arch]` | Consolidate `#[global_allocator]` to a single binary-level registration. Strip library crate presence. Library crates pass Mnemosyne handle via DI. | Source citations T1: `cfd-core/src/lib.rs:45-53`; `ritk-core/src/lib.rs:15-17` (dead cfg gate per audits); `moirai/lib.rs`; `coeus/coeus-python/src/lib.rs:7-9`; `atlas/docs/audit/2026-07-02-cross-repo-integration-audit.md`:L76 (CR-2 [arch] citation, audit_id). | OPEN. Batch #6. |

| **CR-4** | `[major]` | Rebase `coeus-core::Scalar` + `let''o-ops::Scalar` over `eunomia::NumericElement` (NOT `NumericElement + RealField` — `RealField` is float-only and would orphan `coeus_core::Int` for i8/u8/.../u64). Delete duplicated vocabulary (`zero`/`one`/`to_f64`/`from_f64`/`from_usize`/`sqrt_val`/`abs_val`); keep backend slice-kernel surface. | **2026-07-05**: Implementation split across 3 commits. T1 evidence landed per repo sub-row: eunomia `57d7789` (SSOT trait doc + Complex<T>/isize/usize impls + private::Sealed + CastFrom<i32>); coeus `2b3f820` (`feat(scalar)!:` — coeus_core traits + 64-file call-site disambiguation across coeus-{autograd, ops, nn, fft, optim, tensor}, doctests, clippy `assign_op_pattern` adjacent fix); leto `b15439baf` (`feat(scalar)!:` on `codex/leto-cr4-ssot-rebind` — `pub trait Scalar: NumericElement` rebind; redundant UFCS removed; slice kernels to operator-syntax; `cargo` workspace `0.35.1 -> 0.36.0`). ADR: `atlas/docs/adr/0005-eunomia-scalar-ssot.md` (status **Accepted**).<br>**2026-07-05 (CR-4 closure)**: Atlas-meta submodule pointer for `repos/leto` bumped from `21681967e` to `b15439ba`; atlas-meta PM artifacts (`atlas/{backlog,checklist,gap_audit}.md`) updated to mark CR-4 closed and unblock Batches #2/#3/#4 as Definition-of-Ready. Pre-stage gates on the rebind: 270/270 nextest `-p leto-ops` + 189/189 `-p leto` + 8 doctests + clippy `-D warnings` `--lib --tests` scope; `cargo fmt` clean; `cargo doc --no-deps` warnings peer-scope only (not introduced). Net subtractive consolidation: 196 added / 622 removed across 5 files. RG-verified: zero `Scalar::add/sub/mul/div/ZERO/ONE/bitand/bitor/bitxor/count_ones/to_f64` UFCS in `crates/`. `cargo --workspace` scope on the rebind is blocked by peer-WIP `serde_json = { workspace = true }` in `repos/leto/crates/leto/Cargo.toml:39` without matching workspace dep declaration (peer claim stream; disjoint-scope rule prevents CR-4 from touching).<br>**2026-07-05 (alpha sync)**: `fb83d009 chore(atlas): Align submodule pointers to CR-4 eunomia/coeus/leto commits` aligned `repos/{coeus,eunomia,leto}` to the three landing SHAs (`1ae2f30c8` / `57d778930` / `21681967e`), records the kwavers-foundation GPU-error-boundary rule in `README.md`, pushes the chore to `origin/codex/kwavers-atlas-integration`. Re-verification at `fb83d009`: eunomia 29/29 + coeus `-p coeus-{core,tensor,ops,autograd,nn,sparse,dist,fft,optim,leto}` 758/758 nextest green; clippy `-D warnings` clean on the same set; doctests pass; `cargo doc --no-deps` warn-clean.<br>**2026-07-06 Hephaestus CUDA blocker refresh**: the earlier `coeus-wgpu`/`coeus-cuda` blocker is stale in the checked-out `repos/hephaestus` `ks5-cholesky-panel` tree. `hephaestus-cuda/src/application/decomposition/eigen.rs` converts `leto_ops::eigenvalues(&view)` output into `num_complex::Complex<f32>` before `device.upload(&e_host)`, and `rustup run nightly cargo check -p hephaestus-cuda --features decomposition` completed successfully against local `leto`/`leto-ops` `0.36.0`. Evidence tier: compile/build plus source inspection; runtime CUDA nextest coverage remains unclaimed. | **CLOSED 2026-07-05**. eunomia `57d7789` ✅, coeus `2b3f820` ✅, leto `b15439baf` ✅. Batches #2/#3/#4 now Definition-of-Ready. |



---



## Migration evidence inventory (residual surfaces scope-traced)



### CFDrs (`D:/atlas/repos/CFDrs`) — residual nalgebra surface



Source: xtask allowlist scanner `xtask/src/migration_audit.rs:6-23` (`LEGACY_MANIFEST_DEPS` + `LEGACY_SOURCE_TOKENS`); 185-line `xtask/legacy_surface.allowlist` auto-gen list.



- **Manifest residual**: 7 manifests × legacy deps:

  - `CFDrs/Cargo.toml:38,39,41` (`nalgebra 0.33 [serde-serialize]`, `nalgebra-sparse 0.10`, `num-traits 0.2`)

  - `crates/cfd-1d/Cargo.toml:21,22` (nalgebra + nalgebra-sparse via workspace)

  - `crates/cfd-3d/Cargo.toml:24,25`

  - `crates/cfd-core/Cargo.toml:21,22`

  - `crates/cfd-math/Cargo.toml:13,14`

  - `crates/cfd-validation/Cargo.toml:21,22`

  - `[simba 0.9]` workspace dep — auto-included via `nalgebra-simba` transitively; strips with nalgebra

- **Source residual**: 176 files (auto-allowlist); heaviest per-file:

  - `cfd-validation/src/geometry/mod.rs:55 hits`

  - `cfd-core/src/geometry/shapes.rs:52`

  - `cfd-3d/src/fem/projection_solver.rs:44`

  - `cfd-math/src/linear_solver/{conjugate_gradient:39, bicgstab:35, tests/mod:37, tests/extended_edge_case_tests:28, gmres/{arnoldi,solver}}`

  - `cfd-core/src/physics/boundary/geometry.rs:27`

  - `cfd-3d/src/{trifurcation/solver:27, fem/element:27, vof/reconstruction:24, ibm/forcing:22, trifurcation/geometry:20, fem/mesh_utils:19}/.rs`

  - `cfd-1d/src/solver/core/linear_system.rs:20`

- **Total nalgebra source impact T2**: ~1,900 symbol hits across cfdec topology.

- **Closure state**: ✅ **CLOSED 2026-07-05** — inner CFDrs HEAD advanced `0f578e1af110c5b8536476174bf266bf8b812c37` → **`d58d1fe320d046816425e1d20d16735fcfee7995`** via a single Atlas-provider migration push (subject `refactor(cfdrs): Atlas-provider migration push (Leto CSR + Eunomia scalar + Hephaestus GPU + cfd-math / cfd-2d / cfd-3d / cfd-1d / cfd-validation consumer cones)` — 752 modified + 19 added files, 51,857 insertions / 22,087 deletions, ~2,500 tests pass, 0 warnings). The pre-closure baseline (Sprint 1.96.126–1.96.137 trait-surface Leto-keyed; `_linear_system` / `_linear_operator` / `_preconditioner` / solver-chain internals / sparse storage / preconditioner internals still nalgebra-keyed) is consumed in this commit. Post-push `cargo tree -p CFDrs | grep nalgebra` returns zero production ops; the 185-line xtask `legacy_surface.allowlist` contracts to zero entries. Atlas-parent submodule pointer advance recorded at parent HEAD `51922a56c4d4acab3dbe786b90cc5acf92e22277`.



### kwavers (`D:/atlas/repos/kwavers`) — residual nalgebra / ndarray / Rayon / burn surface



Source: hand-verified grep over `crates/*/src` plus `Cargo.toml` per-file evidence.



- **Residual nalgebra** (13 source sites × 5 manifests):

  - `crates/kwavers-mesh/src/tetrahedral/mesh.rs:14` (`Matrix3,Vector3`)

  - `crates/kwavers-transducer/src/flexible/calibration/{types.rs:3, manager/mod.rs:80, manager/kalman.rs:5}` (`DMatrix,DVector` for Kalman filter)

  - `crates/kwavers-medium/src/anisotropic/{christoffel.rs:130, stiffness.rs:191,225}` (`Matrix3,SymmetricEigen` for Christoffel acoustic tensor; small-size LU)

  - `crates/kwavers-analysis/src/signal_processing/beamforming/three_dimensional/cpu/mvdr/mod.rs:62` (`DMatrix,DVector` for Capon covariance-matrix solve)

  - `crates/kwavers-solver/src/inverse/fwi/frequency_domain/cbs/solve.rs:58` (`DMatrix,DVector` for FWI-CBS frequency-domain solver)

  - `crates/kwavers-solver/src/forward/hybrid/bem_fem_coupling/interface/mod.rs:3` (`Vector3`)

  - `crates/kwavers-solver/src/forward/hybrid/bem_fem_coupling/coupler/struct_impl/solvers.rs:3` (`Matrix3,Vector3`)

  - `crates/kwavers-solver/src/forward/helmholtz/fem/solver/core/{interpolation.rs:3, element.rs:3}` (`Matrix3,Vector3`)



- **Residual ndarray** (top contributors):

  - `crates/kwavers-solver/src/**` 759 line-hits (`inverse/pinn/...`, `forward/{nonlinear,elastic,pstd,...}`, `inverse/{fwi,reconstruction/seismic/rtm/inherent}`, `multiphysics/...`)

  - `crates/kwavers-physics/src/**` 290 (acoustics, EM, optics, field_surrogate, chemistry)

  - `crates/kwavers-analysis/src/**` 261 (signal_processing/beamforming, ml, performance)

  - `crates/kwavers-therapy/src/**` 148

  - `crates/kwavers-math/src/**` 106 (tensor/fft/numerical/simd)

  - `crates/kwavers-python/src/**` 100 (PyO3 bindings)

  - All 24 crates declare `ndarray` dep; `kwavers-phantom/gpu/phantom` use `workspace = true` → inherits `ndarray = "0.16" [serde]` post-`702e4f125`.



- **Moirai-routed parallel iteration**:

  - **Batch #1 closure-mark retracted 2026-07-08 (post `566af324e` peer reconciliation, post `35ee01076` inner advance)**: per T1 fresh re-probe at inner HEAD `35ee01076` (2026-07-08): `git --no-pager grep "par_for_each" HEAD -- "crates/"` returns **41 sites across 15 files** in `crates/kwavers-solver/src/**` (down from 84 / 28 at `b605e2e74` baseline, −51%); the residual 41 sites are direct `Zip::indexed(...).and(...).par_for_each(...)` invocations on `ndarray` arrays (NOT the kwavers-medium adapter path). Total row discrepancy: `566af324e` cosmetically rewrote this line to `totals \`0\` across \`0\` files + **Batch #1 CLOSED 2026-07-08**` based on a measurement taken against an uncommitted working-tree snapshot, not the committed inner HEAD `35ee01076`. The numeric 0/0 reduction is retracted: the correct count at the committed HEAD is 41/15.

  - No `use rayon::*` direct imports in the kwavers tree (`rg -l 'use rayon' crates --type rust` returns zero hits); the residual `par_for_each` lexemes are direct `Zip::indexed(...).and(...).par_for_each(...)` invocations on `ndarray` arrays (NOT the kwavers-medium adapter path). **Closing-state discrepancy**: `5af6888ec`/peer stated `cargo tree -p kwavers-solver | grep rayon` returns zero (the Rayon entry into the kwavers dep graph is closed) but the actual T1 fresh probe at `35ee01076` shows `cargo tree -p kwavers-solver -i rayon` returns `rayon v1.11.0` (1 entry, transitively pulled in via `burn_common` -> `burn-autodiff` -> `burn` -> `ritk-image` -> `kwavers-{imaging,physics,solver}`). The ndarray-`rayon` feature strip (`702e4f125`) IS preserved (kwavers-{solver,physics}/Cargo.toml:{24,20} no longer declare the rayon feature), but the kwavers-solver direct dep tree still has `rayon` through the ritk -> burn edge (provider-side obstacle, not Batch #1 closure).

  - **Closing state**: the Batch #1 closure condition is **partially** met. The **manifest surface** (`702e4f125` strip on kwavers-{solver,physics} ndarray-`rayon` feature) IS CLOSED. The **source surface** (par_for_each call-sites in `crates/kwavers-solver/src/**`) is NOT CLOSED: 41 residual sites remain in the committed inner HEAD `35ee01076`. The 41-source-site par_for_each count represents direct ndarray `Zip::par_for_each` invocations (not kwavers-medium adapter calls), as detailed in the line-93 closure-mark retraction. The peer must continue the source-side migration through `moirai_parallel::*` (per the moirai API surface at `moirai-parallel/src/ops.rs:281,335,408,125,155`).

  - Historical baseline (T1 at inner HEAD `aa10a6e76`, 2026-07-06): 84 occurrences across 28 files (`kwavers-solver` 68 in 21 files; `kwavers-physics` 16 in 7 files). The pre-`ea7e09948` per-family header site-count breakdown (62 solver + 24 physics = 86) was over-counted by 2 sites and superseded by the 84/28 measurement at `aa10a6e76`.

  - `kwavers-solver` per-directory breakdown (68 sites at `aa10a6e76`):

    - `inverse/reconstruction/seismic/rtm/inherent/*` (6 files, 27 sites: `imaging.rs` 14, `wavefield.rs` 5, `laplacian.rs` 4, `mod.rs` 2, `illumination.rs` 1, `propagation.rs` 1).

    - `forward/nonlinear/kuznetsov/{diffusion,nonlinear,numerical,operator_splitting/mod,solver/{model_impl,rhs},spectral,workspace}.rs` (8 files, 17 sites: `solver/rhs.rs` 7, `spectral.rs` 2, `solver/model_impl.rs` 2, `numerical.rs` 2, `workspace.rs` 1, `operator_splitting/mod.rs` 1, `nonlinear.rs` 1, `diffusion.rs` 1).

    - `forward/nonlinear/westervelt_spectral/spectral.rs` (1 file, 2 sites).

    - `forward/elastic/swe/{integration/integrator/mod.rs, stress/divergence.rs}` (2 files, 14 sites: `integrator/mod.rs` 11, `stress/divergence.rs` 3).

    - `forward/pstd/extensions/{elastic.rs, elastic_orchestrator/pml/mod.rs}` (2 files, 5 sites: `elastic.rs` 4, `pml/mod.rs` 1).

    - `multiphysics/fluid_structure/{interface.rs, solver/struct_impl.rs}` (2 files, 3 sites: `interface.rs` 1, `solver/struct_impl.rs` 2).

  - `kwavers-physics` per-directory breakdown (16 sites):

    - `acoustics/conservation/heat.rs` (2 sites).

    - `acoustics/mechanics/acoustic_wave/nonlinear/{numerical_methods/{spectral/mod.rs (7), nonlinear_term.rs (1)}, wave_model.rs (1)}` (3 files, 9 sites).

    - `acoustics/mechanics/cavitation/damage/model.rs` (1 site).

    - `acoustics/therapy/sonogenetics/{arf_field.rs (2), channels/gating.rs (2)}` (2 files, 4 sites).

  - Per-directory scan tallies add to 84 (68+16), matching the global ripgrep total. The peer migration in `ea7e09948 refactor(kwavers-physics)!: Route Rayon dispatch through moirai-parallel` (2026-07-06 10:21) drained sub-families elsewhere (`thermal`, `sonoluminescence/{blackbody,bremsstrahlung,cherenkov}`, `transducer`, `RTM`, `Monte Carlo`, `bubble interactions`, `field_surrogate`, `chemistry/{reaction-kinetics,ros-plasma}`, `optics/polarization`) but the `acoustics/{conservation, mechanics/{acoustic_wave,cavitation}, therapy/sonogenetics}` families remain on the pre-migration `Zip::*().par_for_each()` chain at this HEAD.

  - Note: the per-family header site-count breakdown from the prior record (62 solver + 24 physics = 86) is the pre-`ea7e09948` snapshot; the peer migration drained 86 → 84 (-2 sites net).

- **Migration evidence for `ndarray` Rayon feature**:

  - Historical baseline (T1 grep at HEAD `aa10a6e76`, 2026-07-06): `crates/kwavers-solver/Cargo.toml:24` + `crates/kwavers-physics/Cargo.toml:20` retained `ndarray = { version = "0.16", features = ["rayon", "serde"] }`. The `rayon` feature activated `cargo tree -p kwavers-solver | grep rayon` returning `rayon v1.11.0`/`rayon-core v1.13.0`, so Batch #1's zero-Rayon dep-graph closure condition was UNMET at that point.

  - **✅ CLOSED 2026-07-07** per peer `702e4f125` (`chore(kwavers-solver): Drop unused ndarray/rayon feature from kwavers manifests`, on `codex/kwavers-core-moirai-parallel`). At inner HEAD `f678dc35e` (T1 grep 2026-07-07 19:56): both manifests now read `ndarray = { version = "0.16", features = ["serde"] }` — `rayon` feature stripped from `kwavers-{solver,physics}`; `cargo tree -p kwavers-solver | grep rayon` now returns zero (no Rayon entry into the kwavers dep graph). The closure condition is now MET on the manifest surface.

  - Related call-graph evidence: `kwavers-solver/src/inverse/same_aperture/operator/linear_op.rs` (6 sites) already routes through `moirai_parallel::ParallelSliceMut`; not a migration target (preserved for downstream-batch completeness).

  - **Batch #1 closure-mark RETRACTION 2026-07-08**: the prior `0060b1e10` closure-mark (`✅ Batch #1 CLOSED 2026-07-08`) is retracted. Per T1 re-verification at inner HEAD `35ee01076` (2026-07-08, after the peer's `0060b1e10` landed on origin and `35ee01076` advanced kwavers inner by one more `fix(solver): Preserve adaptive-error layout order` commit): **41 `.par_for_each()` sites across 15 files** remain in `crates/kwavers-solver/src/**` (counted via `git --no-pager grep "par_for_each" HEAD -- "crates/" | wc -l` = 41; sites concentrate in `forward/{elastic/swe/{integration/integrator/mod,stress/divergence}, nonlinear/{kuznetsov/{diffusion,nonlinear,numerical,operator_splitting/mod,solver/{model_impl,rhs},spectral,workspace}, westervelt_spectral/spectral}, pstd/extensions/{elastic,elastic_orchestrator/pml/mod}, multiphysics/fluid_structure/{interface,solver/struct_impl}}`). The 41 sites are direct `Zip::indexed(...).and(...).par_for_each(...)` calls on `ndarray` arrays (e.g. `crates/kwavers-solver/src/forward/pstd/extensions/elastic.rs` line 143+ uses `use ndarray::Zip; Zip::indexed(...)...par_for_each(...)`) — NOT the `kwavers-medium` adapter. **The peer `0060b1e10` claim of "0 sites" was incorrectly measured against an uncommitted working-tree snapshot**, not against the committed inner HEAD. **Dep-graph state**: `cargo tree -p kwavers-solver -i rayon` at inner HEAD `35ee01076` returns `rayon v1.11.0` (1 entry, transitively via `burn_common` `burn-autodiff` `burn` `ritk-*` -> `kwavers-{imaging,physics,solver}`). The ndarray-`rayon` feature strip (`702e4f125`) is preserved (manifest-only); the kwavers-solver direct dep tree still has `rayon` pulled in via the ritk -> burn path (provider-side obstacle, not Batch #1 closure). **Batch #1 closure status**: the **manifest surface** (`702e4f125` strip on kwavers-{solver,physics} ndarray-`rayon` feature) IS CLOSED. The **source surface** (par_for_each call-sites in `crates/kwavers-solver/src/**`) IS NOT CLOSED; the peer must continue migrating the residual `Zip::indexed().par_for_each()` chain through `moirai_parallel::*` (the kwavers-solver-side `crate::parallel::for_each_*` helpers + `moirai_parallel::enumerate_mut_with` already exist per the moirai API surface at `moirai-parallel/src/ops.rs:281,335,408,125,155`). The peer must then re-emit a corrected closure-mark once the source-side count actually drops to zero. **Atlas-meta path forward**: kwavers pointer advance remains deferred per the KW-CV-001 watchpoint trigger; the Batch #1 closure-mark must be reasserted by a future session after the peer lands the source-side migration.
  - **Batch #1 source-side migration — slice 1 partial-closure-mark 2026-07-08**: per the peer's `5cd8c708`
  chore (`refactor(kwavers-solver): Migrate struct_impl.rs par_for_each to
  moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 1)`,
  on `codex/kwavers-core-moirai-parallel` atop parent `ccc6bbf9`):
  **2/41 sites migrated in 1/15 files**. The 2 sites live in
  `crates/kwavers-solver/src/multiphysics/fluid_structure/solver/struct_impl.rs`
  (3D `Array3<f64>` element-wise relaxation on `p_fluid_ghost` +
  `p_fluid_ghost_prev`; plus a 1D sub-view relaxation on `t_solid_ghost` +
  `t_solid_ghost_prev`). The migration uses the idiomatic
  `moirai_parallel::ParallelSliceMut::par_mut().enumerate(closure)` trait
  form (auto-Adaptive policy; no `ExecutionPolicy` generic needed),
  preserves indentation via captured leading-whitespace group, and adds
  the trait import `use moirai_parallel::ParallelSliceMut;` ahead of the
  `ndarray` use-statement. Cargo-check pre-validate: `cargo check -p
  kwavers-solver --lib --no-default-features` clean at inner HEAD
  `5cd8c708`. The full-closure mark (`✅ Batch #1 CLOSED 2026-07-08`)
  remains retracted; this entry is a **partial-closure mark**, not a full
  reassertion. **39/41 sites / 14/15 files remain** for future slices per
  ADR 0009 Batch #1 CTE shape
  (`docs/adr/0009-kwavers-batch1-rayon-to-moirai-cte.md`). **Atlas-meta
  path forward**: kwavers pointer advance remains deferred per the
  KW-CV-001 watchpoint; the next slice(s) will be tracked via per-slice
  partial-closure marks until the source-side count actually drops to
  zero, at which point the full closure-mark can be reasserted.


- **Residual `burn`** (T1 re-verified 2026-07-07 against the dirty inner `repos/kwavers` working tree after the neutral-name Burn cleanup continuation):

  - Requested migration scope is clean: `rg -n "Burn|burn_|\bburn\b|burn-|CoeusPINN|coeus_wave" crates/kwavers-solver/src/inverse/pinn crates/kwavers/tests crates/kwavers/benches crates/kwavers/examples crates/kwavers/Cargo.toml Cargo.toml` returns zero hits.

  - Kwavers manifests are clean: `rg -n "\bburn\b|burn-" -g Cargo.toml .` returns zero hits under `repos/kwavers`.

  - The `crates/kwavers-solver/src/burn.rs` facade is absent and `rg -n "burn_compat|crate::burn|kwavers_solver::burn|pub mod burn|mod burn"` finds no `burn_compat` alias path. The 1-D, 2-D, and 3-D PINN module paths are now framework-neutral (`wave_equation_1d`, `wave_equation_2d`, `wave_equation_3d`), and the beamforming adapter path is `pinn_adapter`.

  - Whole-repo literal residual is **356 lines across 21 files**, concentrated in `Cargo.lock` and historical PM/audit prose rather than the requested PINN/top-level source scope. Scoped PINN/top-level source plus `xtask/legacy_surface.allowlist` residual is **0 lines across 0 files** after regenerating the allowlist.

  - `cargo tree -p kwavers-solver --features pinn -i burn` remains non-empty through RITK provider crates (`ritk-image`, `ritk-interpolation`, `ritk-spatial`, `ritk-wgpu-compat`, and downstream `ritk-*` paths), so full Burn graph closure is still blocked outside the kwavers manifest/source surface.

  - Verification evidence: `rustup run nightly cargo fmt -p kwavers-solver -p kwavers --check` passed; `rustup run nightly cargo check -p kwavers-solver --features pinn` passed; `rustup run nightly cargo check -p kwavers --features pinn --tests --benches --examples` passed with pre-existing warning noise in `kwavers-math`, `pinn_elastic_validation`, and `phase6_persistent_adam_benchmarks`; `rustup run nightly cargo run -p xtask -- legacy-migration-audit` passes with allowlist status clean after `refresh-legacy-allowlist`; `rustup run nightly cargo nextest run -p kwavers --features pinn --test pinn_bc_validation --test pinn_ic_validation --status-level fail --no-fail-fast` compiled and ran 16 tests: 12 passed, 4 failed on legacy 3-D PINN loss thresholds (`test_ic_loss_zero_field`, `test_ic_combined_loss_decreases`, `test_bc_loss_decreases_with_training`, `test_dirichlet_bc_zero_boundary`). These are retained as validation residuals; assertions were not weakened.

- **Provider-boundary closure (2026-07-04)**: the 3-D beamforming WGPU

  operation provider moved from `kwavers-analysis` to

  `kwavers-gpu::beamforming::three_dimensional::WgpuBeamformingProvider`.

  `kwavers-analysis` now keeps only `BeamformingGpuProvider` and the CPU

  reference, and `kwavers-analysis/gpu` no longer forwards WGPU/bytemuck/

  Hephaestus/pollster dependencies. Remaining GPU holdouts are exact:

  `kwavers-analysis/src/visualization/**` still owns WGPU visualization behind

  `gpu-visualization`; CUDA 3-D DAS kernels are not implemented; broader

  `kwavers-gpu` WGPU providers still need real CUDA operation-family kernels

  plus WGPU/CUDA differential tests; solver PINN Burn code is outside this

  provider-boundary slice.

- **Residual `num_complex`**: 12 crates declare `num-complex = "0.4"`; source-import sites 194 (kwavers-solver 55, kwavers-analysis 45, kwavers-physics 32). Apollo path is via `eunomia::Complex` already (`kwavers-math`).

- **Residual `num_traits`**: 5 manifests (`kwavers-{analysis,grid,math,physics,solver}`); 11 source-import sites.

- **Residual `std::arch::*` SIMD**: 27 line anchors across `kwavers-math/src/simd_*/...` (Hermes-routed), `kwavers-solver/src/forward/fdtd/avx512_stencil/{velocity,pressure}.rs` (libtargets for AVX-512), and `kwavers-analysis/src/performance/optimization/{config,cache}.rs` (`_mm_prefetch` hint). Stencil SIMD paths need separate [minor] migration to Hermes.

- **2026-07-08 — `ndarray` → `leto's ndarray-compat` migration tracking entry**: per fresh T1 verification via `rg -n 'ndarray' crates --type rust` at inner HEAD `35ee01076` (branch `codex/kwavers-core-moirai-parallel`):

  - **Migration scope**: numerically-array runtime surface — substituting direct `ndarray = { version = "0.16" }` usage with `leto::Array` re-exported via `leto = { features = ["ndarray-compat"] }`. Fundamentally DISTINCT from **Batch #1** Rayon parallel-runtime feature strip (CLOSED 2026-07-07 per `702e4f125`, the `ndarray/rayon` feature removal) and from **Batch #4** Burn→Coeus PINN migration; this targets the underlying numerical-array vocabulary, not the parallel iteration layer, not the autodiff/Backend surface. Per ADR 0010 §Decision §Per-batch name pattern: this would be a new `[minor]` Batch #N candidate if/when the peer's closeout commits land.

  - **Inventory (2026-07-06 baseline at the line-167 anchor)**: ~1,664 line-hits across 24 crates; top contributors are `kwavers-solver` (759), `kwavers-physics` (290), `kwavers-analysis` (261), `kwavers-therapy` (148), `kwavers-math` (106), `kwavers-python` (100). All 24 kwavers crates declare `ndarray = { version = "0.16" }` (or inherit via `workspace = true`).

  - **T1 fresh re-probe at HEAD `35ee01076` (2026-07-08)**: `rg -n 'ndarray' crates --type rust` totals **2,496 line-hits across 1,492 files** (delta vs 2026-07-06 baseline: +832 line-hits / +0 files; the hit-count delta reflects additional ndarray usage within the existing 1,492 files (no new files touched; +832 line-hits concentrated in the same surface)). Import breakdown at the committed HEAD: `use ndarray` (1,563 occurrences, the dominant source-side surface) + `use leto` (276 occurrences total) + `use leto::{array,ndarray_compat,Array}` (223 occurrences, the leto ndarray-compat import surface). Migration-upstream consumer: only `crates/kwavers-math/Cargo.toml` declares `leto = { workspace = true, features = ["ndarray-compat"] }`; **23 of 24 crates still directly consume `ndarray = { version = "0.16" }`** (i.e., leo's ndarray-compat coverage is currently N=1/24 — narrow footprint, valid upstream foothold, broad downstream gap).

  - **`ndarray/rayon` feature strip status**: CLOSED 2026-07-07 per `702e4f125 chore(deps): drop unused ndarray/rayon feature from kwavers manifests` (the feature-layer strip was the Batch #1 closure condition; this tracking entry is the substantive numerical-array migration, distinct from the feature strip).

  - **2026-07-08 `apply_acoustic_freq` test-mock ndarray slip (surfaced this session via `cargo nextest run --workspace --lib`)**: T1 verification at kwavers inner HEAD `ccc6bbf9e6` and again at the latest advanced inner `5cd8c7083` (`refactor(kwavers-solver): Migrate struct_impl.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 1)`) shows the bulk ndarray→leto migration commits this session closed 5 commits deep on the inner `codex/kwavers-core-moirai-parallel` branch; `cargo check -p kwavers-solver --workspace` succeeds with only 1 cosmetic dead-code warning (in `crates/kwavers-simulation/src/dispatch/elastic_pstd.rs:8:4`). However, `cargo nextest run --workspace --lib` continues to fail at compile due to the **broader** `kwavers-solver/src/plugin/mod.rs` ndarray-typed plugin interface: the file imports `use ndarray::Array4;` at top-level (line 28) and `use ndarray::Array3;` in test scope (line 182); the trait at line 107 (`fields: &mut Array4<f64>`) and the test-mock `NullBoundary::apply_acoustic_freq` at line 202-208 (`_field: &mut Array3<kwavers_math::fft::Complex64>`) both rely on ndarray types — while the `Boundary` trait (per `kwavers_boundary::Boundary`) now declares `_field: &mut leto::Array<eunomia::Complex<f64>, VecStorage<eunomia::Complex<f64>>, 3>`. Also line 223 (`PluginFields::new(Array3::zeros((grid.nx, grid.ny, grid.nz)))`) compiles only because the in-scope `use ndarray::Array3;` shadows leto. **The `apply_acoustic_freq` test-mock fix is insufficient — the entire plugin interface needs a trait-rewire from ndarray types to leto types**. A `[minor]` Bulk-Phase closure on `kwavers-solver/src/plugin/mod.rs` entails: (a) replace top-level ndarray `use ndarray::Array4;` with `use leto::Array4;`, (b) replace trait `fields: &mut Array4<f64>` with `leto::Array4<f64>`, (c) replace test-mock `Array3<kwavers_math::fft::Complex64>` with the trait's leto-typed signature, (d) propagate the new trait surface to all implementors (`kwavers_boundary::*` Boundary impls + NullBoundary mock). A second `let`_affected `kwavers-solver/src/forward/pstd/physics/residual_gas_absorption.rs:74` (`spectrum: &mut Array3<kwavers_math::fft::Complex64>`) ALREADY uses `use leto::{Array3, ArrayView3};` (L65) — its `Array3` resolves correctly to `leto::Array3`. Only the plugin file is broken across the closure. **Peer-owned per `concurrent_agents` disjoint-scope rule**: atlas-meta records the residual; the inner peer stream owns the `crates/kwavers-solver/src/plugin/mod.rs` refactor. The peer can drain this via a `[minor]` Bulk-Phase plugin-trait-rewire continuation commit OR a verbatim 4-line edit (top-of-file `use ndarray::Array4` → `use leto::Array4` + the trait method field-type) followed by per-implementor sweep. **Verification evidence (this turn)**:
    - kwavers `cargo check -p kwavers-solver --workspace` PASSES (49.88s)
    - kwavers `cargo check -p kwavers-solver --lib --no-default-features` PASSES at `5cd8c708` (28.12s) — kwavers-solver lib compiles cleanly
    - kwavers `cargo check --workspace` PASSES (49.88s) with single dead-code warning (`fn to_leto3` unused; resolve by `#[allow(dead_code)]` or removal)
    - ritk `cargo nextest run -p ritk-python --lib` PASSES 47/47 (1m 41s compile, 0.34s execute)
    - ritk `cargo check --workspace --all-targets` PASSES (42.10s, no warnings)
    - ritk `cargo nextest run --workspace --lib` PASSES **4612/4612** (4 skipped, 303s, 0 failed)
    - CFDrs `cargo check --workspace --all-targets` PASSES (1m 31s)
    - CFDrs `cargo nextest run --workspace --lib` PASSES 2177/2177 (1 skipped, 37s)
    - cfdrs subset `cargo nextest run -p cfd-math -p cfd-1d -p cfd-2d --lib` PASSES 1335/1335 (1 skipped, 24.9s)
    - kwavers `cargo nextest run --workspace --lib` fails at compile in 1 site (`crates/kwavers-solver/src/plugin/mod.rs`); requires peer-owned plugin trait-rewire

  - **Recent kwavers-internal migration-adjacent commits** (informational, NOT ndarray-compat-specific): `702e4f125` (ndarray/rayon feature strip) + `8b128c478` (Burn compatibility shim removal + burn dep drop, NOT ndarray-related despite the kwavers-solver scope) + `1f320cfe6` (build-level unused ndarray Rayon features removal, redundant with `702e4f125`).

  - **Closeout status**: **TRACKING** (not closure-marked). No `closeout|final|completion|close-batch` kwavers-internal commit has landed for the ndarray→leto's ndarray-compat migration; the source-side migration runs through `moirai-parallel::*` for parallel iteration (Batch #1) but the numerical-array vocabulary itself has no equivalent upstream-first migration push yet.

  - **Atlas-meta path forward**: per Surfacing risks **row 8** (BATCH #4 SLICE-INTEGRITY / kwavers-as-peer-claimed axiom) + the `concurrent_agents` disjoint-scope rule, atlas-meta does NOT advance `HEAD:repos/kwavers` gitlink until (a) the peer emits a formal `closeout|final|completion` commit for the ndarray-compat conversion (triggering the **KW-CV-001** watchpoint per `

- **12. CONTINUAL-AUDIT WT-DIRTY CLASSIFICATION (refreshed 2026-07-08)**: see

  the `## Continual audit: WT dirty submodule classification (2026-07-08)`

  section above for the per-submodule (a)/(b)/(c)/(d) classification of

  the 7 currently-dirty submodule paths. **Net effect**: 7/7 submodules

  aligned (no drift); 1 (a) stable/synced (coeus); 6 (b) clean-dirty

  (CFDrs, gaia, helios, hephaestus, kwavers, ritk); 0 (c) pointer-advance

  candidates; 0 (d) regressions. Per the `concurrent_agents`

  disjoint-scope rule, atlas-meta has zero pending bookkeeping for these

  7 submodules; all inner-state changes are peer-owned. Re-run probe

  cadence: weekly or per-chore-landing.



### E0599 Closure-Front Peer-Side Fix Brief (kwavers `.view*()` surface)

*External index alias: row 14.5.*

**Section 1 -- Context + disjoint-scope.** The E0369 3-item idiom set (`array.iter_mut().for_each(|v| *v *= scalar)` / `as_slice_memory_order_mut()` / project-native `scale_array` helper) is operationally complete for the E0369 front as of the prior-session proof-of-pattern work. This row documents the SEPARATE E0599 closure-front, maintaining strict `concurrent_agents` disjoint-scope; peer-side kwavers claims the actual `.view*()` site fixes (atlas-meta records-only).

**Section 2 -- Categorization + current-state.** Total **151 prefix-form call sites** across 27 distinct files on inner HEAD `7c42ba2dfbbe7b21e7ac17a3233fd74efe34df16` (live re-enumeration post-`a5134d8` gitlink advance). Breakdown:

- **Category A (bare `.view()`):** 138 sites (per `9deb4ab` baseline; current enumeration held flat)
- **Category B (`.view_mut()`):** 13 sites (NEW-visible post-`a5134d8`; previously not enumerated)
- **Category C (`.view_slice()` / `.view_axis()`):** 0 sites / 0 sites (empty surface)

**Section 3 -- Anchor cross-walk + baseline archival.** Baseline enumeration recorded in `9deb4ab` cited 138 `.view()` line-hits across 27 distinct files on the prior inner HEAD state. The current-state 151 count is the enumeration-scope expansion of that 138 baseline + 13 `.view_mut()` sites previously unenumerated by `9deb4ab`'s `rg '\.view\(\)'` regex (which matches `.view()`-strict but not `.view_mut(`); newly surfaced by the row 14.5 SSOT enumeration's inclusion of the `.view_mut()` regex variant. two-head diff verification (post-`74df54d` investigation): bare `.view()` = 138 + `.view_mut()` = 13 + `.view_slice()` = 0 + distinct files = 27 reported at BOTH inner HEAD `7c42ba2dfbbe7b21e7ac17a3233fd74efe34df16` (post-`a5134d8`) AND inner HEAD `445ab9b2a432e81325b103789974a4482e7e8d92` (pre-`a5134d8`) -- the 13 `.view_mut()` sites are LONG-STANDING callsites present at both heads, NOT net-added migration output. The 91-site planning-stage figure (referenced in prior-session context) is officially RETIRED: it never landed in `gap_audit.md` -- the prior-session apply attempts `python3 _apply_v3.py` and `python3 _apply_v4.py` failed on Windows path-translation + bash heredoc fragility, then again on the structural mismatch where `### Bulk-migration priority #2` is not a markdown H3 in the actual file structure (only paragraph-text mentions exist). 91 is superseded by 151.

**Section 4 -- Fix approach (peer-side).** Per-category strategy:

- **Category A (138 bare `.view()`):** manual per-site rewrite (each site is heterogeneous; canonical `boundary.rs` refactor does not fit all bare calls). Per-site approach matches the E0369 idiom-set triage conclusion in `### Bulk-migration priority #2: repos/kwavers crate migration (E0369)` above.
- **Category B (13 `.view_mut()`):** single atomic `Boundary<_>` refactor at `boundary.rs` (or per-site if heterogeneous). The `.view_mut()` calls have a more uniform carrier pattern (all ndarray `Array3`/`Array4` writable views on the kwavers-data plane).
- **Category C (slice / axis):** no action.

**Section 5 -- Atlas-meta pointer-advance gating.** Atlas-meta `repos/kwavers` gitlink is now stable at `7c42ba2dfbbe7b21e7ac17a3233fd74efe34df16` post-`a5134d8` (advanced by `a5134d8` chore). Any further kwavers peer-side commits that close E0599 sites should propagate to atlas-meta via chore-style gitlink-advances (mirror the existing `concurrent_agents` disjoint-scope pattern: atomic `git update-index --add --cacheinfo 160000,<sha>,repos/kwavers` parent-tree pointer advance ONLY, with the kwavers inner dirty state preserved as-is).

**Section 6 -- Disjoint-scope rule preserved.** This brief is informational / records-only. Atlas-meta documents the surface + count + per-category fix approach; peer stream claims actual closure work. Future-session audit of E0599 progress is via the KW-CV-001 watchpoint + per-bullet propagation per `### Bulk-migration #2 closure-front triage` discipline.

**Section 7 -- Migration-mechanism explanation.** The 138 -> 151 COUNTER is documented as an enumeration-scope expansion per the post-`74df54d` two-head diff verification (inner HEAD `7c42ba2dfbbe7b21e7ac17a3233fd74efe34df16` vs pre-`a5134d8` inner HEAD `445ab9b2a432e81325b103789974a4482e7e8d92`, both yielding bare `.view()` = 138 + `.view_mut()` = 13 + `.view_slice()` = 0 + `.view_axis()` = 0 + distinct files = 27). The transition is NOT a peer code-growth dynamic; the 13 `.view_mut()` callsites are LONG-STANDING (present at both heads). What changed between `9deb4ab` (cited 138 only) and the row 14.5 SSOT enumeration (138 + 13 = 151) is the enumeration regex scope (`.view()`-strict -> `.view()` + `.view_mut()`). The earlier framing in this row 14.5 Section 7 (originally written at `74df54d4f963b96d1b642ce89e77c9b019ad3de7`, pre-`536366e` 2-head diff verification) (peer-side migration cycles SIMULTANEOUSLY net-add `.view_mut()` through ndarray -> leto Axis-Typed view-mut conversions) is RETIRED in favor of the verified two-head diff finding. Future-session audits should re-derive the count via `rg --no-filename '\.view(\)\|'\.view_mut(\)' repos/kwavers/crates/kwavers-math/src/` at any inner HEAD to confirm the 138 + 13 = 151 enumeration stability (the `\\|` substring is the shell-quoted form for raw regex alternation `|`; raw regex is `\\.view()|\\.view_mut()`).

**Section 8 -- 91-site planning-stage figure archival.** The 91 number was a planning-stage estimate computed at a prior inner HEAD (before `a5134d8`'s gitlink advance). It is RETIRED here in favor of the state-verified 151 figure. Any future-session reference to "91 sites" should be interpreted as superseded by this SSOT (searchable via `rg -F "91 sites" gap_audit.md backlog.md` -- should return 0 hits post-`a96d46d` + this row).

**Section 9 -- Cross-link chain (audit-trail).** `9deb4ab` (the carrying in-flight bullet; kwavers math enum) + `b29cfa23ea467a7e2a52a4024c6a3b1168eb9acf` (the `backlog.md` patch-up closing front-matter enumeration drift; corrected CR-2 status from CLOSED to OPEN) + `93a0723177676ac56de38878fd44b26e7e02c026` (RN-CC-01..03 closeout -- CR-2 file-wide cite + 9-char SHA upgrade + Parent-SHA body discipline declaration) + `a96d46d7294a367fb8837aa256379bdb2ea644bc` (RN-CC-02 follow-up -- Bulk-migration case canonicalization; the parent-SHA of this row 14.5) + post-this-row commit (the inherited `backlog.md` ## In-flight claims bullet propagation chore cycle).

**Forward-only invariant:** Row 14.5 inserted injection-style BEFORE `## Forward-looking watchpoints` (stable grep anchor); per NO-AMEND atop the parent commit `a96d46d7294a367fb8837aa256379bdb2ea644bc`. 0 submodule gitlinks touched + 0 executable bit promotions + 0 `[UNDO]` / revert / amend / rebase / force-push.

### RN-CC-04 self-carry discipline: retroactive disclosure (post-536366e)

Commits `93a0723177` (RN-CC-01..03 closeout) + `a96d46d7294` (RN-CC-02 follow-up) declared the RN-CC-04 Parent-SHA body discipline but technically BREACHED their own declaration (the parent-SHA chunk-cite was inline in prose, not in the `Parent-SHA: <40-char-sha>` line-block placement at the body header). Per NO-AMEND, retroactive repair to commit bodies is forbidden; the breach is REVEALED VIA TRANSPARENCY instead. The RN-CC-04 line-block discipline was first truly self-carried at `74df54d4f963b96d1b642ce89e77c9b019ad3de7` + `74df54d4f` (backlog.md bullet update) + `536366e` (row 14.5 §3+§7 reframe). Parent-SHA: forward-propagation audit discipline (RN-CC-05 enforcement): run `rg -F "Parent-SHA:" gap_audit.md backlog.md checklist.md docs/coordination/` (expect >=2 line-hits) + `git log --grep "Parent-SHA:" --oneline` (expect >=2 entries). The audit predicates are cross-validated at `docs/coordination/INDEX.md` roster (per RN-CC-05 commit).

## Forward-looking watchpoints`), AND (b) post-batch pre-merge authoritative-classification (sev-tier via `cargo semver-checks` shape) lands. The action-sequence-on-trigger is the **row 11 DYNAMIC-SHA-EXTRACTION MANDATE** (`git update-index --add --cacheinfo 160000,$(cd repos/kwavers && git rev-parse <short-sha>^{commit}),repos/kwavers`) followed by atomic chore commit + force-with-lease push to `origin/codex/kwavers-atlas-integration`. Re-verify the trigger on every kwavers sub-bullet refresh; promote this tracking entry to a closure-mark form once the peer-side closeout emits.

- **Closure state**: per `kwavers/gap_audit.md`, `~50` prior Rayon edges closed 2026-07-02/03 across solver/physics/imaging/simulation/top-level. Residual is the trip above.



### ritk (`D:/atlas/repos/ritk`) — residual burn surface (provider side obstacle)



Source: hand-verified scan over all 27 crates plus `RITK/Cargo.toml:69-72` workspace burn feature set.



- **Manifest residual**:

  - ~~`RITK/Cargo.toml:69` retained `wgpu` in the workspace Burn feature list despite `DEP-496-01` being marked done.~~ **RETRACTED 2026-07-06**: `repos/ritk/Cargo.toml` now uses `features = ["std", "ndarray", "autodiff"]`. Verification: `rustup run nightly cargo tree --workspace -i burn-wgpu`, `-i burn-cuda`, and `-i burn-rocm` each reported no matching package; `rustup run nightly cargo metadata --locked --format-version 1` completed successfully. Evidence tier: dependency graph + locked metadata.

  - `RITK/Cargo.toml:70` `burn-ndarray = "0.19"`.

  - `RITK/Cargo.toml:88,112` `num-complex`, `num-traits` (manifest only; zero source uses detected).

- **Source residual** (764 burner-touching files; top contributors):

  - `ritk-filter`: 296

  - `ritk-registration`: 109–129 (autodiff metrics + classical spatial + backforms + optimizer/cgnostics)

  - `ritk-segmentation`: 88 (SurfaceExtraction `SignedDistanceTransformFilter`, `AntiAliasBinarySmoothFilter`, etc.)

  - `ritk-model`: 18–36 (DLSSM/TransMorph architectures)

  - `ritk-statistics`: 20–32

  - `ritk-{io,interpolation,transform}`: 24–30 each

  - `ritk-{python,cli,snap}`: 11–14 each (UI/thin bedrock)

  - `ritk-core/interpolation/trait_:20` public type `Interpolator<B: Backend>` (Provider-side obstacle; locks `Burn::Backend` trait surface for entire downstream).

  - `ritk-core/transform/trait_:19` public type `Transform<B: Backend, const D: usize>`.

  - `ritk-core/image/types:18` public type `Image<B: Backend, const D: usize>` (re-exported from `ritk_core::lib.rs:11`); downstream inherits Burn.

  - `ritk-spatial/{vector,point,direction,spacing}` impl `burn::module::{Module,AutodiffModule} + burn::record::Record` (Provider-side obstacle).

  - `ritk-io::{ImageReader,ImageWriter}<Image<f32,B,3>>` writes `B: Backend` parameter.

  - `ritk-deformer_field_ops::deformable_field_ops::CpuOrGpu<B>` defaults `burn::backend::NdArray` post `DEP-496-01`.

- **ndarray**: only 3 source sites, all in `ritk-python` for Python-side numpy interop (`use numpy::{ndarray::Array2, Array3, Array4}` etc.). Zero domain-side contact.

- **Closure state**: Sprint 495 (native writers for 9 formats — `MIGH, META, MINC, TIFF, JPEG, NRRD, Analyze, NIfTI, PNG`) merged into `ritk-io::ImageWriter<Image<f32,B,3>>` with Burn + native façade; `DEP-496-01` (default Burn features) is now file-literal consistent: `repos/ritk/Cargo.toml` removes Burn's `wgpu` feature and the workspace dependency graph selects no Burn GPU backend package.

- **2026-07-06 — Sub-batch #1 of Batch #3 closed per ADR 0012**: inner RITK atomic commit adds Atlas-typed parallel trait surface (`TransformAtlas<T: Scalar, B: ComputeBackend, D>`, `InterpolatorAtlas<T: Scalar, B: ComputeBackend>`, `ResampleableAtlas<T: Scalar, B: ComputeBackend, D>`) + `pub use native::Image as AtlasImage;` re-export + 2-crate Cargo.toml dep additions (`coeus-core` + `coeus-tensor` referenced as `{ workspace = true }`). **Purely additive**: no Burn-keyed surface mutation; `xtask/burn_surface.allowlist` unchanged; Burn GPU-default drift (closed by inner commit `65a1a0fd`) preserved. Sub-batches #2-#6 (`RITK-trait-deprecate`, `RITK-crate-migrate`, `RITK-spatial-rebind`, `RITK-burn-remove`, `RITK-xtask-ci`) reserved per `atlas/docs/adr/0012-ritk-burn-trait-rebind.md` §Decision.

- **2026-07-06 — Sub-batch #2 of Batch #3 closed per ADR 0012**: inner RITK atomic commit (docstring-only) appends soft deprecation callout to the four Burn-keyed foundational surfaces `Transform<B, D>`, `Resampleable<B, D>`, `Interpolator<B>`, and `Image<B, D>`. **Docstring-only**: no `#[deprecated]` attribute (which would emit ≥671 `#[warn(deprecated)]` warnings across `xtask/burn_surface.allowlist` source files); zero public Burn-keyed surface symbol removal/narrowing/renaming; zero `Cargo.toml` mutation; `xtask/burn_surface.allowlist` unchanged (auto-generated, signature-keyed). Forward-pointing intra-doc-links `[`TransformAtlas`]` / `[`ResampleableAtlas`]` / `[`InterpolatorAtlas`]` / `[`AtlasImage`]` resolve to the Atlas-side parallels added in sub-batch #1. Compile-gate: `cargo check -p ritk-core -p ritk-image` passes; `cargo doc -p ritk-core -p ritk-image --no-deps` intra-doc-link resolution passes; `cargo tree --workspace -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` each zero (Burn GPU-default state preserved from `65a1a0fd`). Sub-batches #3-#6 (`RITK-crate-migrate`, `RITK-spatial-rebind`, `RITK-burn-remove`, `RITK-xtask-ci`) reserved per ADR 0012 §Decision.

- **2026-07-06 — Sub-batch #3 of Batch #3 OPENED per ADR 0012**: per-crate Atlas-typed migrators, 7-per-crate sub-atomic increment queue. Each per-crate commit lands as its own subtractive-by-conversion atomic commit on `repos/ritk` (8-file pattern: 1 test source port + 1 atlas-meta inner PM sync + tag-chain references + atlas-meta chore commit on atlas-meta). Per-crate order: `ritk-filter` (`morphology/tests_binary_erode.rs`) → `ritk-registration` (`metric/histogram/parzen/tests/cache_property_tests.rs`) → `ritk-segmentation` (`morphology/binary_erosion/tests.rs`) → `ritk-model` (`ssmmorph/encoder/tests.rs`) → `ritk-statistics` (`tests_image_statistics.rs`) → `ritk-{io,interpolation,transform}` (`format/dicom/color/tests.rs` + `interpolation/tests_trilinear.rs` + `transform/affine/tests_affine.rs`) → `ritk-{python,cli,snap}` (one CLI command test + one snapshot handler test + one python binding test). Each per-crate commit ports one specific test from `burn_ndarray::NdArray<B>` to `AtlasImage<T: Scalar, B: ComputeBackend, D>` over `coeus_tensor::Tensor<T, MoiraiBackend>`, drops 1 source-row from `xtask/burn_surface.allowlist`, preserves every public Burn-keyed signature intact. Sub-batch #5 remains the only commit authorised to delete/rename `[dependencies]` lines; sub-batch #6 owns the allowlist refresh ritual. The `ritk/atlas-migration-push/batch3` annotated tag annotation body will enumerate the 7 per-crate SHAs per ADR 0010 §Decision §Per-batch name pattern. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 (amended 2026-07-06) + §atomic-boundary discipline §1.

- **2026-07-08 — Bulk provider pointer advance unblocks ritk-python test compile**: per fresh T1 verification at inner RITK HEAD `1f49278c` (post the `274a6a961` atlas-meta chore advance of `repos/ritk` gitlink from `00d57005` → `1f49278c`), the `cargo check -p ritk-python --lib --tests` and `cargo nextest run -p ritk-python --lib` commands now **both pass** at the committed inner HEAD. Prior to the bulk provider pointer advance (apollo → `2e6f9be`, coeus → `e36f95ff`, leto → `83e1693e1`, eunomia → `b3fd6f2`, hermes → `e4c6949`, mnemosyne → `170dd8ab`, helios → `5f6aef65a`, melinoe → `375108b`, ritk → `1f49278c`, themis → `2b6a3ace`), the ritk-python test compile failed with `error[E0308] mismatched types` at `crates/ritk-python/src/metrics/mod.rs:122:29` because `Arc::new(img)` expected `AtlasImage<f32, MoiraiBackend, 3>` but encountered `Image<NdArray, 3>` — the underlying root cause was actually `failed to select a version for the requirement "leto = \"^0.35.1\""` against the available `0.36.0` (the output that surfaced via `coeus-leto == 0.5.8` from inner coeus at `b2beec3e vs 5e3e639`) and `failed to select a version for the requirement "melinoe = \"^0.7.0\""` against `0.8.0`. Surfacing risks row 9 ([major] SEMVER-CHECKS RESOLUTION BLOCKER) decomposed these as version-skeew symptoms of the stale atlas-meta gitlink state. The bulk-migration cleanup pass at `2e1c4f2 ... 274a6a9 ... a12d1dd ... 715cff2 ... 02da066 ... ab71f08 ... 36acbbc` advanced each provider to a current inner HEAD, eliminating the dependency version mismatches and resolving the test compile path. Inner WT for ritk (65 dirty paths) remains at peer-WIP for sub-batches #3-#6; the test compile path resolves AT THE COMMITTED HEAD `1f49278c`. Tests: `cargo nextest run -p ritk-python --lib` returns `47 tests run: 47 passed, 0 skipped` per re-verification 2026-07-08.



- **2026-07-08 — Sub-batch #3 of Batch #3 closure-mark RETRACTION**: the prior peer `7cfe8a37d` closure-mark (`0 \`burn::\` occurrences in \`crates/\` (was 764)`) is retracted. Per T1 re-verification at inner HEAD `1f49278c` (2026-07-08, branch `main`, after the peer's `7cfe8a37d` landed on origin): `git --no-pager grep "burn::" HEAD -- "crates/"` returns **176 occurrences across 97 files** in `repos/ritk/crates/`; among them ~132 are real `use` statements (e.g. `crates/ritk-image/src/lib.rs` declares `pub use ::burn::{backend, module, nn, optim, prelude, record, tensor};` + 4 more `pub use burn::tensor::*` re-exports; `crates/ritk-image/src/host_extract.rs` declares `use crate::burn::backend::Autodiff;`; `crates/ritk-spatial/src/{direction,point,spacing}.rs` each re-declare `use crate::burn::module::{...};` + `use crate::burn::record::{...};` + `use crate::burn::tensor::backend::{...};`), ~6 are doc-comments (`crates/ritk-filter/src/morphology/tests_binary_erode.rs:54,140`, `crates/ritk-core/src/transform/trait_.rs:22`), and the remainder are in-line `burn::*` references in implementation. The working tree has 65 dirty paths (post-`7cfe8a37d`, sub-batch #5 RITK-spatial rebind work mid-flight per peer's dirty paths in `crates/ritk-spatial/src/{direction,point,spacing,vector}.rs` + Cargo.toml + Cargo.lock + CHANGELOG.md + gap_audit.md); the WIP diff is `65 files changed, 1352 insertions(+), 1448 deletions(-)` (the deletions include the `burn::module::*` + `burn::record::Record` impl removals on the 4 spatial types per sub-batch #5: 191 insertions-deletion reversal on `crates/ritk-spatial/src/{direction,point,spacing,vector}.rs`). **Sub-batch #3 closure status**: NOT CLOSED. The per-crate Atlas-typed migrator test-source ports have not landed in `1f49278c`; `burn::` is still the dominant backend surface for RITK (Burn-keyed re-exports in `ritk-image`, Burn-keyed type signatures in `ritk-spatial`, Burn-keyed implementation in `ritk-filter` morphology tests, etc.). **Sub-batches #4-#6 remain OPEN** per ADR 0012: #4 (RITK-crate-migrate per-crate Atlas-typed migrators' Cargo.toml dep strip) is not yet landed (the active inner-WIP reshapes `Ritk/Cargo.toml` but no per-crate stamp has landed); #5 (RITK-spatial-rebind + RITK-burn-remove) is the Burn-trait surface removal + `ritk-spatial` `burn::module` impl removal — actively in flight in the working tree at `1f49278c` (the `burn::module::{Module, AutodiffModule} + burn::record::Record` impls on `Direction/Point/Spacing/Vector` are deleted in the WIP commit but not committed); #6 (RITK-xtask-ci) is the `xtask/burn_surface.allowlist` refresh ritual. The overall Batch #3 is NOT yet closed — only sub-batches #1 + #2 are CLOSED. The peer's measurement of "0 \`burn::\` occurrences" was taken against an uncommitted working-tree snapshot, not against the committed inner HEAD `1f49278c`. **Atlas-meta path forward**: per the `concurrent_agents` disjoint-scope rule, atlas-meta continues to defer the parent-side gitlink for `repos/ritk` until the inner WIP lands; the ritk pointer advance must wait for the peer's sub-batches #3–#6 to actually complete (per the [major] blocker on `Mnemosyne.git?rev=...` + the themis-`^0.8.0` resolver issue per ritk handover notes), at which point a fresh closure-mark can replace this retraction.



### Anchor-evolution history (N1 nit follow-up, post-92cc1b62 basis-disclosure)



The basis-disclosure append at the row-7 COEUS Batch #4 figure-refresh paragraph

(originally a single chore `92cc1b62`) lived through a 3-version iteration arc

documented here for forward-auditor visibility:



- **v1 (failed)**: anchor_old = `"rule entry chain `min(22, 8)=8` → `min(22, 0)=0`)."`

  with mid-footnote Unicode arrow (`→` = `→` = U+2192). Failure mode: Windows

  console cp1252 UnicodeEncodeError when printing the arrow via `print()`;

  script aborted before git ops fired. Fix: `sys.stdout.reconfigure(encoding='utf-8')`.

- **v2 (failed)**: same anchor as v1, with two substitution modes tried (exact

  `text.replace()` + `text.count()`; then regex `re.sub()` + `re.findall()` with

  `\s*.\s*` flexibility). Failure mode: `anchor_old count = 0` despite the file

  containing the substring. The byte-level fragility of the multi-byte anchor

  string containing the Unicode arrow confused multiple escape paths.

- **v3 (LANDED)**: anchor_old FULLY-ASCII, anchored at the TAIL of the

  supersede-application footnote: `` `min(22, 0)=0`). `` — pure ASCII

  (backticks, digits, parens, period). The substitution replaced this short

  ASCII tail with `` `min(22, 0)=0`) (*basis note*: prior 8 measured at

  WT-vs-pre-715cff2-atlas-meta-gitlink; fresh-probe 0 measured at detached inner

  HEAD `5e3e63967`). `` -- inserting the basis-disclosure sentence inside the

  supersede-application footnote's paren frame, naming both measurement bases

  explicitly. Forward-only docs-only atop current HEAD per NO-AMEND; parent

  user_stated=559f7579 (lineage reference for row-7 figure refresh) with

  actual=HEAD~1 at runtime.



Per code-reviewer N2 nit (anchor_field_naming intent): when referencing the v3

design in future body-scratch fields, prefer naming intent-over-version --

i.e., use `anchor_tail_old` / `anchor_tail_new` rather than `anchor_old_v3` /

`anchor_new_v3` -- so future readers grepping for `anchor_tail_old` finds the

intended meaning (anchor at footnote TAIL) rather than a record-version sentinel.



Post-chore atomic loci (line-number enumeration; N1 nit apply):

- **L339 PRESERVED**: basis-disclosure inside the row-7 COEUS Batch #4

  figure-refresh supersede-application footnote (anchor_tail_old =

  `` `min(22, 0)=0`). ``, anchor_tail_new =

  `` `min(22, 0)=0`) (*basis note*: prior 8 measured at WT-vs-pre-715cff2-atlas-meta-gitlink;

  fresh-probe 0 measured at detached inner HEAD `5e3e63967`). ``;

  landed at chore `92cc1b62`; refines per ADR 0008 §0 framing of the

  supersede coefficient rule `min(reconciliation-fig, fresh-probe-fig)` so

  the `(*supersede application*:` footnote's paren frame now names both

  measurement bases explicitly).

- **L156 ADDED**: anchor-evolution history section (this section; N1 nit

  follow-up post-`92cc1b62`; closes the v1->v2->v3 iteration arc +

  documents the ASCII-only `anchor_tail_old`/`anchor_tail_new`

  intent-over-version naming per N2 nit so future readers grepping for

  `anchor_tail_old` find the intended meaning (anchor at footnote TAIL)

  rather than a record-version sentinel).

- **L152 ADDED**: ritk-python test-unblock record (sub-chore of `e237aca95`;

  bulk-provider pointer-advance sequence

  `2e1c4f2 ... 274a6a9 ... a12d1dd ... 715cff2 ... 02da066 ... ab71f08 ...

  36acbbc` unblocks `cargo nextest run -p ritk-python --lib` = `47 tests

  run: 47 passed, 0 skipped` at inner RITK HEAD `1f49278c`, post the

  `[major]` SEMVER-CHECKS RESOLUTION BLOCKER row 9 decomposition that

  attributed the original `Arc::new(img)` type-mismatch at

  `ritk-python/src/metrics/mod.rs:122` to provider-side version skew

  rather than `burn_compat`-shaped surface mutation).



Next-step probe targets (post-e237aca continuation; N5 nit apply):

- **Row 8 (CFDrs migration-evidence inventory @ L24; STABLE/SYNCED @ L318)**:

  re-probe inner HEAD `8aa7313f2980cdd9518b95e39f96487653c43148` on

  `codex/cfdrs-atlas-migration` + check Batch #2 (CFDrs nalgebra -> leto +

  nalgebra-sparse -> leto-ops `CsrMatrix`) closure persistence at the

  pre-closure baseline SHA `d58d1fe320d046816425e1d20d16735fcfee7995`;

  verify `cargo tree -p CFDrs | grep nalgebra` returns zero production ops

  invariant holds; cross-tree scope: clean WT (`0 ahead/behind @{u}` on

  `codex/cfdrs-atlas-migration`) with 2 dirty paths (active peer WIP).

- **Row 9 (eunomia stable/synced @ L346)**: re-probe gitlink alignment at

  `57d778930ecd25e77416c49ee10c9b6670f0ea70` + SSOT surface integrity

  (`eunomia::NumericElement` SSOT trait + `private::Sealed` + `CastFrom<i32>`

  + `Complex<T>`/`isize`/`usize` impls); confirm no regression on

  `eunomia::csr.rs` non-sealed `Scalar` trait per ADR 0008 Phase-1B gate

  (gating the kwavers-math `CsrScalar` migration push). Cross-tree scope:

  clean WT, ALIGNED with atlas-meta gitlink (`57d778930...`), 7 dirty

  paths (active peer WIP, unchanged from the 2026-07-06 inventory cut).





- **2026-07-08 — Sub-batches #4–#6 (Batch #3) inner advance reconciliation**: per fresh T1 verification at inner HEAD `7a66d1ee` (branch `main`, dirty count 58+, after per-sub-batch-#5 mid-flight WT reshaping logged in the line-251 retraction note), per-sub-batch-#3–#6 status inventory per ADR 0012 §Decision:

  - **Sub-batch #4 (RITK-crate-migrate Cargo.toml dep strip) — IN PROGRESS**: inner commit `7a66d1ee` (`Strip unused production burn dep across 17 leaf crates`) has landed; `rg -n '\bburn\b' --include 'Cargo.toml' /d/atlas/repos/ritk` returns 37 manifest entries at the committed HEAD (10+ confirmed, up from the baseline 37 entry count cited in the line-240 Manifest residual entry).

  - **Sub-batch #6 (RITK-xtask-ci allowlist refresh + CI gate) — ACTIVE**: inner commit `925fbf33` (`refresh burn allowlist + wire CI gate`) has landed; `xtask/burn_surface.allowlist` re-confirmed at 645 lines (intact, awaiting the ritual sub-batch #5 Burn-trait surface removal + per-crate stamp before the refresh-allowlist ritual actually contracts).

  - **Sub-batch #5 (RITK-spatial-rebind + RITK-burn-remove / Burn-trait surface removal + `ritk-spatial` `burn::module` impl removal) — PENDING / WIP IN TREE**: no formal commit landed yet. Per line-246 retraction note + the 65-dirty-path mid-flight WT decomposition (lines 152-155 area): the `burn::module::{Module,AutodiffModule} + burn::record::Record` impl removals on `Direction/Point/Spacing/Vector` in `crates/ritk-spatial/src/` are actively mid-flight in the uncommitted WT (≈191 insertion/deletion reversal on those four files), but still present at the committed HEAD `7a66d1ee`.

  - **Manifest surface state**: root `Cargo.toml:73` retains `burn = { version = "0.19", default-features = false, features = ["std", "ndarray", "autodiff"] }`; root `Cargo.toml:74` retains `burn-ndarray = "0.19" # For CPU testing`; sub-batch #4's per-crate stamp will trip the strip once the per-crate Atlas-typed migrators actually close out. Sub-batches #1+#2 remain CLOSED; sub-batches #3 (retracted at line 240 per the 0/764 `burn::` mismatch closure-mark retraction) + #4 + #5 + #6 remain OPEN. The overall Batch #3 is NOT yet closed.

  - **Atlas-meta path forward** (refines the parent-side tracker): per the `concurrent_agents` disjoint-scope rule + **Surfacing risks row 6 (peer-WIP collision)** axiom, atlas-meta does NOT advance the parent-side `HEAD:repos/ritk` gitlink; the ritk pointer advance remains deferred until (a) sub-batches #3+#4+#5+#6 actually close, (b) the peer emits a formal closeout reconciliation commit (analogous to the kwavers KW-CV-001 watchpoint structure), and (c) the [major] blocker on `Mnemosyne.git?rev=...` + themis-`^0.8.0` resolver issue per ritk handover notes (row 9 Surfacing risks §SEMVER-CHECKS RESOLUTION BLOCKER) is resolved to enable the post-batch `#5 [major]` standing reminder's pre-merge authoritative-classification gate per `atlas/backlog.md` §In-flight claims §Standing reminders §Sub-batch #5 [major].



### Cross-utility



- `tokio`: zero hits in any of CFDrs, kwavers, ritk — fully migrated.

- `rayon`: zero direct hits; transitive only via ndarray `rayon` feature (above).

- `rustfft`: zero hits — `apollo-fft` consumed instead.

- `packed_simd`: zero hits.



---




### KW-CV-002 [Enumeration Validation]: kwavers-math `.view()` site stability (child of KW-CV-001)

- **Identity**: KW-CV-002 derives from KW-CV-001 (the closure-style-trigger watchpoint). It validates the SSOT enumeration established in row 14.5 and the post-`536366e` reframe of §3 + §7.
- **Re-audit protocol**: future-session auditors re-run `rg --no-filename '\.view(\)\|\.view_mut(\)\|\.view_slice(\)\|\.view_axis(\)' repos/kwavers/crates/kwavers-math/src/` at each new kwavers inner HEAD advance.
- **Baseline expectation** (post-`a5134d8` + post-`536366e` reframe; inner HEAD `7c42ba2dfbbe7b21e7ac17a3233fd74efe34df16`): cross-file distinct = 27 files; matched-line counts = bare `.view()` = 138 + `.view_mut()` = 13 + `.view_slice()` = 0 + `.view_axis()` = 0, total = **151 sites** across 27 files.
- **Count-delta detection**: any drift in either (a) cross-file distinct count != 27, (b) matched-line breakdown != 138+13+0+0, or (c) total != 151 triggers investigation.
- **Recovery protocol**: open a fresh investigation chore cycle analogous to the post-`536366e` one. Execute 2-head diff verification between CURRENT inner HEAD and pre-`a5134d8` inner HEAD `445ab9b2a432e81325b103789974a4482e7e8d92`. If delta is peer code-growth dynamic (new `.view_mut()` callsites genuinely introduced by kwavers migration): reframe row 14.5 §3 + §7 + retire the prior enumeration-scope claim. If delta is enumeration-scope change (new regex variant): update baseline + the SSOT enumeration.
- **Cross-link chain**: `536366e9` (post-investigation reframe, `Parent-SHA: 74df54d4f963b96d1b642ce89e77c9b019ad3de7`) + `row 14.5` (SSOT) + `465ec10` (RN-CC-05 audit-discipline registration) + this KW-CV-002 registration. Cross-validation: gap_audit.md ## Forward-looking watchpoints self-audit via the `rg -F "Parent-SHA:" gap_audit.md` predicate at any future audit cycle.

**Forward-only invariant**: KW-CV-002 watchpoint registered atop current HEAD per NO-AMEND; pinned baseline inner HEAD `7c42ba2dfbbe7b21e7ac17a3233fd74efe34df16` is fp-pinned (does not drift on parent chore advance). Future-session recompute at each new kwavers inner HEAD advance is mandatory per the recovery protocol above.

## SSOT enforcement surface (per-repo migration-audit gate)



> The `.github/workflows/legacy-migration-audit.yml` gate enforces a per-repo **single SSOT enforcement surface** so every Atlas-provider migration push stays inside the allowlist contract. The gate is wired across 6 repos under the `kwavers-Atlas-migration-push` ceremony anchor: 3 original (cfdrs / ritk / kwavers), 3 added 2026-07-07 (apollo / gaia / helios).



| Repo | Workflow file | xtask subcommand | Allowlist path / state | Branch triggers | Commit anchors |

|------|---------------|------------------|------------------------|-----------------|----------------|

| **cfdrs** | `.github/workflows/legacy-migration-audit.yml` | `cargo run -p xtask -- legacy-migration-audit` | `xtask/legacy_surface.allowlist` (185 lines) | `[main, refactor/**, codex/**]` | per-submodule `d58d1fe3` Batch #2 closure (cfdrs `codex/cfdrs-atlas-migration`) |

| **ritk** | `.github/workflows/legacy-migration-audit.yml` | `cargo run -p xtask -- burn-migration-audit` | `xtask/burn_surface.allowlist` (~764 source-rows × 27 crates) | `[main, refactor/**, codex/**]` | per-submodule `8f8360ff` RITK pointer advance (post-Batch #3 sub-batch #3.f closeout) |

| **kwavers** | `.github/workflows/legacy-migration-audit.yml` | `cargo run -p xtask -- legacy-migration-audit` | `xtask/legacy_surface.allowlist` (84 `par_for_each` + nalgebra + ndarray + burn residual inventory) | `[main, refactor/**, codex/**]` | per-submodule peer-active (`codex/kwavers-core-moirai-parallel` Batch #1 + Batch #4 reservations per ADR 0010) |

| **apollo** | `.github/workflows/legacy-migration-audit.yml` | `cargo run -p xtask -- provider-audit` (native; hard-fails on forbidden ndarray references via `concat!("nd", "array")`) | (no `.allowlist` file — dynamic forbidden-pattern check + provider-usage matrix; consumes `xtask/src/provider_audit.rs` directly) | `[main, codex/**]`¹ | per-submodule `9df5294e + 2940d66 + cd05eac` (workflow + branch-narrowing + workflow-YAML fix) |

| **gaia** | `.github/workflows/legacy-migration-audit.yml` | `cargo run -p xtask -- legacy-migration-audit` | `xtask/legacy_surface.allowlist` (header-only baseline; 0 legacy surface items found by T1 grep over `nalgebra/ndarray/burn/tokio/rayon`) | `[main, refactor/**, codex/**]` | per-submodule `6a7b7d0 + d47d8a6` (scaffold + phantom-dep drop) |

| **helios** | `.github/workflows/legacy-migration-audit.yml` | `cargo run -p xtask -- legacy-migration-audit` | `xtask/legacy_surface.allowlist` (header-only baseline; 0 legacy surface items found by T1 grep) | `[main, refactor/**, codex/**]` | per-submodule `8a6637b + 065bf39` (scaffold + phantom-dep drop) |



¹ Excludes `refactor/**` to defer day-1 verdict damage on Apollo's in-flight `refactor/apollo-fft-eunomia` migration (~234 dirty files mid-migration); expand to `refactor/**` once that migration lands, matching the cfdrs/ritk/kwavers shape.



### Recently closed (2026-07-07)



- **Apollo / Gaia / Helios migration-audit gate lift** — landed under the `kwavers-Atlas-migration-push` ceremony anchor on 2026-07-07. Apollo's existing xtask exposes `provider-audit` (a forbidden-crater check + provider-usage matrix) and was added workflow-only; gaia and helios received fresh `xtask` workspace members (mirrored verbatim from `cfdrs/xtask` per the canonical pattern: `Cargo.toml` + clap-based `src/main.rs` + `src/migration_audit.rs` BTreeSet-diff scanner + header-only `xtask/legacy_surface.allowlist` baseline). Gate file path `.github/workflows/legacy-migration-audit.yml` is uniform across all 6 repos for ecosystem discoverability; the subcommand invoked differs only on apollo (its native `provider-audit` shape was preserved). Evidence tier: structural on-disk confirmation (file presence + workflow YAML schema-correct `on:` + `permissions:` + `concurrency:` + `jobs:` blocks per repo). First CI-run verdict target: day-1 exit 0 on the active inner branch tip of each repo.

- **Apollo workflow branch-list narrowing** — restricted triggers to `[main, codex/**]` (not `refactor/**`) so Apollo's active `refactor/apollo-fft-eunomia` branch (~234 dirty files mid-migration) does not flip the gate red on day-1. Once that migration lands, expand to `refactor/**` per the cfdrs/ritk/kwavers shape. Already-closed chore commit `2940d66` documented the narrowing rationale.

- **Phantom-dep drop on gaia + helios xtask** — the first-pass scaffold mirrored `kwavers/xtask/Cargo.toml` (with `walkdir 2.3` / `regex 1.8` / `chrono 0.4`), but `migration_audit.rs` only imports `anyhow::{bail, Context, Result}` + `std::{collections::BTreeSet, fs, path::{Path, PathBuf}}`. None of `walkdir`/`regex`/`chrono` are referenced from `src/`, so they're phantom deps that `cargo-deny` would flag. Chore commits `d47d8a69f` (gaia) + `065bf3941` (helios) replaced the kwavers-shaped dep set with the cfdrs-mirror set (anyhow + clap + serde + serde_json + toml).

- **Apollo workflow YAML fix commit** — chore commit `cd05eac` replaced a botched first-pass str_replace's malformed `pull_request:branches:` collapsed YAML with the corrected shape. GitHub Actions would have refused to parse the first-pass shape on first invocation (the `pull_request:` key would have been read as a literal `pull_request:branches` key without the per-mapping interpretation). First-pass `2940d66` retained the on-disk correction context; fix-commit `cd05eac` is the final, gate-runnable shape.



### Gate-internal mechanics (cfdrs / ritk / kwavers / gaia / helios canonical shape)



Per `cfdrs/xtask/src/{main.rs, migration_audit.rs}` (the canonical pattern the new scaffolds mirror):

- **`src/main.rs`**: `clap` derive-`Parser` binary with `enum Command { LegacyMigrationAudit, RefreshLegacyAllowlist }` (or `BurnMigrationAudit` / `RefreshBurnAllowlist` for ritk); each variant calls into `migration_audit` module functions.

- **`src/migration_audit.rs`**: walks `Cargo.toml` / `**/*.rs` files in the workspace root, computes `BTreeSet<Cow<str>>` of legacy-source tokens (e.g. `nalgebra::`, `ndarray::`, `burn::tensor::Backend`, `tokio::`, `rayon::`, `Zip::par_for_each`), compares against the per-repo `xtask/{legacy|burn}_surface.allowlist` set, and `bail!` with a non-zero exit code on any contained-but-not-allowlisted hit (or any allowlisted-but-now-absent row). Refresh path writes the allowlist file with the current surface, gated to the SSOT marker header.

- **`Cargo.toml` workspace edge**: each per-repo `xtask/Cargo.toml` declares `anyhow` + `clap` (v4.0–4.5 derive) + `serde` (derive) + `serde_json` + `toml` (0.8). `walkdir` / `regex` / `chrono` were dropped as phantom deps per the 2026-07-07 gaia/helios chore commits.

- **Apollo's asymmetric gate**: `xtask/src/provider_audit.rs` is structurally similar but exempts the `.allowlist` contract — it dynamically computes the forbidden-reference set (the only entry is `ndarray`, encoded via `concat!("nd", "array")` to bypass any in-file crate-name matching) and the provider-usage matrix (a structured `Vec<ProviderUsageRow>` enumerating each provider crate name + dependency direction + dependency-version constraint). Source-level nextest coverage at apollo HEAD `f1ddf7a` (per `repos/apollo/xtask/src/provider_audit.rs`).



### Cross-repo invariants



1. **File uniformity**: `.github/workflows/legacy-migration-audit.yml` on all 6 repos — centralized CI/CD query-ability + ecosystem discoverability.

2. **Subcommand uniformity**: `cargo run -p xtask -- legacy-migration-audit` is the canonical invocation; `burn-migration-audit` (ritk) and `provider-audit` (apollo) are explicit divergence points documented in the table above.

3. **Allowlist naming**: cfdrs/gaia/helios use `xtask/legacy_surface.allowlist`; ritk uses `xtask/burn_surface.allowlist`; apollo uses NO allowlist file (dynamic check).

4. **Buffering shape**: the first-pass scaffolds (gaia/helios) initially included `walkdir`/`regex`/`chrono` from the kwavers xtask pattern but the `migration_audit.rs` body uses only `std::fs::read_dir` recursively + `serde` for allowlist-parse — phantom deps were stripped to the cfdrs-shape (anyhow + clap + serde + serde_json + toml) per the 2026-07-07 chore commits.



### Limitations and forward-looking hooks



- Apollo's `xtask` exposes only `provider-audit` (no `legacy-migration-audit` / `refresh-legacy-allowlist` pair); a future `[minor]` Apollo-side chore may add the symmetric pair if phobos asks for the cfdrs/kwavers/ritk/helios-shape parity.

- `Cargo.lock` cache key uses `'Cargo.lock'` non-recursive on all 3 new workflows (already tight per the prior ceremony's micro-nit convention).

- First automated `cargo run -p xtask -- legacy-migration-audit` validation is deferred to CI day-1 (out-of-session for Atlas-meta); the per-repo workflow file presence + YAML schema-correctness is the Atlas-meta-side confirmation tier.



---



## In-flight claims (transient atlas-meta carryover)



Per `D:/atlas/backlog.md` `## In-flight claims (per concurrent_agents)` precedent, transient atlas-meta carryovers that resolve via a separate atomic chore (peer-claim resolution OR next-session followup) are surfaced here rather than in the persistent `Limitations and forward-looking hooks` inventory above. Items here resolve away once the named chore commits — they are not forward-looking TODOs.





---



## Provider extension register (provider land owned)



Source: provider capability baseline audit 2026-07-04.



| Provider | Missing surface | Owner | Refers |

| --- | --- | --- | --- |

| `let''o` | `Quaternion<T>` | `let''o` | `let''o/backlog.md` |

| `let''o` | `Matrix4<T>` typed-const + complete `Add/Sub/Mul` operator surface | `let''o` | `let''o/backlog.md` |

| `let''o-ops` | `CscMatrix<T>` | `let''o` (post leto-ops publishing) | `let''o/backlog.md` |

| `let''o-ops` | `CooMatrix<T>` | `let''o` | `let''o/backlog.md` |

| `let''o-ops` | `lu_batch` (batched-LU API to replace `rsparse` parity) | `let''o` | `let''o/backlog.md` |

| `let''o-ops` | `ExecutionStrategy::ParallelStrategy` → `MoiraiBackend::ParIter` trait-bounded seam (remove `ExecutionStrategy` enum-dispatch) | `let''o` | `let''o/backlog.md` |

| `moirai-async` | `mpsc::channel` (multi-producer single-consumer) | `moirai` | `moirai/docs/backlog.md` |

| `moirai-async` | `oneshot::channel` (one-reader one-message) | `moirai` | `moirai/docs/backlog.md` |

| `moirai-async` | `Condvar` primitive | `moirai` | `moirai/docs/backlog.md` |

| `moirai-async` | `Mutex` async primitive | `moirai` | `moirai/docs/backlog.md` |

| `moirai` | `#[moirai::main]` macro for binary entry (or document permanent `tokio::main` carriers) | `moirai` | `moirai/docs/backlog.md` |

| `apollo` | RustFFT-free differential oracle (MMS polynomial FFT) | `apollo` | `apollo/backlog.md` |

| `apollo` | Prune `rustfft = "6.4.1"` workspace pin (`apollo/Cargo.toml:84`); gate `apollo-validation` rustfft-only dep behind dev-feature | `apollo` | `apollo/backlog.md` |

| `apollo` | Verify GPU NUFFT path (`apollo-nufft-wgpu`) feature works downstream | `apollo` | `apollo/backlog.md` (testing RITKinsey/MIR) |

| `eunomia` | `NumericElement::zero()`/`one()` methods direct on the trait surface (today `Default`-derived only) | `eunomia` | `eunomia/backlog.md` |

| `eunomia` | Document `eunomia-gpu` aspirational claim status, or fold into `hephaestus::DialectScalar` and retire | `eunomia` | `eunomia/backlog.md` |

| `coeus-core` | `eq/ne/lt/gt` comparison free fn surface on `BackendOps` | `coeus` | `coeus/docs/backlog.md` |

| `coeus-autograd` | `Var<T,B>::{scatter_add}` autograd-side wrapper (frame-side ops-only today) | `coeus` | `coeus/docs/backlog.md` |

| `coeus-nn` | `Dataset`/`DataLoader` trait if PINN dataset code requires it (deferred if not) | `coeus` | `coeus/docs/backlog.md` |

| `hephaestus-wgpu` | `wgpu::PipelineCache` integration (perf, WG-P8 from substrate audit) | `hephaestus` | `hephaestus/backlog.md` |

| `hephaestus-cuda` | Close `CU-C1`, `CU-P1`, `WG-S1`, `BOTH-SCAN` HIGH-sev defects (substrate audit) | `hephaestus` | `hephaestus/backlog.md` |



---



## Provider-side obstacles for consumer migration (SSOT gates)



These are TypeScript-style locks that prevent consumer migration until the provider extension lands.



| Consumer migration batch | Obstacle | Required provider fix |

| --- | --- | --- |

| **Batch #2 (CFDrs nalgebra finish)** | `cfd-math::chain.rs:62-72` `LetoRealScalar` chain parallel-eunomia trait vocabulary; `RealField` bound currently `nalgebra::RealField`. | CR-4 (eunomia SSOT). |

| **Batch #3 (ritk Burn-trait rebind)** | `ritk-core::{Image<B,D>, Transform<B,D>, Interpolator<B>}` + `ritk-spatial::{Vector,Point,Direction}<D>` Burn `Module/Record` impls. | CR-4 (eunomia SSOT) + `eunomia::RealField` extended for backend/parametrized autograd. |

| **Batch #4 (kwavers-solver PINN)** | `burn::{Module,AutodiffBackend,Backend,optim::*,record::Record}` substitutions. | CR-4 + `coeus_autograd::scatter_add` + `coeus-ops::BackendOps::{eq,lt,...}`. |

| **Batch #1 (kwavers-solver/phys residual Rayon — already self-contained)** | `moirai-parallel::par_mut().enumerate()` rename pattern; chunk primitives naming distinction. | (None — verified by `moirai/moirai-parallel/src/lib.rs:106-181`.) |

| **Batch #8 (provider extensions — provider land)** | Provider-side extensions owned by provisioner repos. | Tracked above. |



---



## Imaging-side cross-cuts



- `kwavers-python`: numpy/numpy-npy + ndarray pinned on top-level (`crates/kwavers/Cargo.toml:46` `=0.16.1`); dev-test path bound through coeus or migration target.

- `kwavers-solvers-python` interaction with `ke-rma-wgpu`: `kwaver-plicity-wgpu` path uses `coeus-wgpu`/`hephaestus-wgpu`/`apollo-wgpu-helpers`; cutover depends on `coeus` GPU adapter reaching wgpu-26 step-up phase.

- `kwavers-pinn`: Coeus extension `scatter` + `eq/lt` for mask/vanishing_point/aggregating, post-CR-4.

- `helios` DICOM real-input path: **closed 2026-07-06** for production DICOM ownership. RITK inner commit `8f8360ff` adds `ritk-dicom::{DicomTag, tags, DicomAttributeRead}`; Helios H-061 now consumes RITK for parse, typed image attributes, transfer-syntax lookup, and pixel decode. Direct `dicom` remains only as a Helios dev-dependency for synthetic Part 10 fixture generation. Remaining audit H-063 covers `helios-imaging`: generic medical-image I/O/registration/toolkit operations move upstream to RITK first, while radiation-domain MVCT projection/reconstruction kernels stay in Helios.



---





## Continual audit: WT dirty submodule classification (2026-07-08)



Per fresh T1 probe of all 7 currently-dirty submodule paths at `D:/atlas`,

each submodule is classified by the (a) stable/synced / (b) clean-dirty /

(c) pointer-advance candidate / (d) regression taxonomy:



| Submodule | Branch | inner HEAD == atlas gitlink | WT dirty | ahead/behind @{u} | Classification |

| --- | --- | --- | --- | --- | --- |

| **CFDrs** | `codex/cfdrs-atlas-migration` | YES (aligned) | 4 | 0 / 506 | **(b) clean-dirty** — peer WIP, light touch |

| **coeus** | `main` | YES (aligned) | 0 | 0 / 676 | **(a) stable/synced** — perfect alignment, zero dirty |

| **gaia** | `refactor/migrate-to-leto-geometry` | YES (aligned) | 5 | 0 / 107 | **(b) clean-dirty** — peer WIP, light touch |

| **helios** | `main` | YES (aligned) | 10 | 0 / 68 | **(b) clean-dirty** — peer WIP, post-H-061/H-062 stabilization |

| **hephaestus** | `ks5-cholesky-panel` | YES (aligned) | 1 | 0 / 189 | **(b) clean-dirty** — peer WIP, near-stable (1 path) |

| **kwavers** | `codex/kwavers-core-moirai-parallel` | YES (aligned) | 81 | 0 / 1718 | **(b) clean-dirty** — peer WIP, heavy (Burn-compat facade + par_for_each residual consolidation) |

| **ritk** | `main` | YES (aligned) | 24 | 0 / 973 | **(b) clean-dirty** — peer WIP, heavy (Batch #3 sub-batches #3-#6 mid-flight) |



**Net effect**: 7/7 submodules are HEAD==gitlink aligned (zero drift, zero

pointer-advance candidates, zero regressions). 6/7 hold active peer WIP

(classification **b**) totalling 125 dirty paths across the workspace (4 +

0 + 5 + 10 + 1 + 81 + 24 = 125). Only **coeus** is fully clean (classification

**a**, zero dirty, stable/synced).



**Per-submodule notes**:



- **coeus (a)**: zero dirty, HEAD==gitlink. The user's prior turn's

  bookkeeping-advance at `2e1c4f20d` brought the gitlink forward; the 4

  files I previously saw as dirty (CHANGELOG.md, Cargo.toml, coeus-nn/benches/nn_bench.rs,

  docs/gap_audit.md) have since been committed. Atlas-meta has zero pending

  bookkeeping for coeus. **Stable/synced** — no reclamation action needed.

- **kwavers (b)**: 81 dirty paths. This is a **reduction** from the prior

  e0bf556 audit's 266 → 299 dirty path range. Peer is actively consolidating

  Burn-compat facade + par_for_each residual work. Per `concurrent_agents`

  disjoint-scope rule, atlas-meta defers to peer; await peer-side closeout

  commit + KW-CV-001 watchpoint trigger.

- **ritk (b)**: 24 dirty paths. This is a **reduction** from the prior

  e0bf556 audit's 65 dirty paths. Peer is mid-flight on Batch #3

  sub-batches #3-#6 (Burn-trait surface removal + Cargo.toml dep strip).

  Per disjoint-scope rule, atlas-meta defers to peer.

- **hephaestus (b)**: 1 dirty path — essentially stable. Negligible

  noise from peer-side work.

- **helios (b)**: 10 dirty paths. Post-H-061/H-062 stabilization, peer

  is iterating on H-063 (helios-imaging generic-toolkit audit).

- **gaia (b)**: 5 dirty paths. Light peer WIP, likely CSG source +

  benchmark files per the `refactor/migrate-to-leto-geometry` branch.

- **CFDrs (b)**: 4 dirty paths. Light peer WIP on the

  `codex/cfdrs-atlas-migration` branch.



**Disjoint-scope rule axiom (refreshed)**: atlas-meta does not own any

of the 125 dirty paths in the 6 clean-dirty submodules. Atlas-meta MUST NOT

execute `git clean`, `git reset`, or any destructive operation on these

inner paths. All inner-state changes are peer-owned per the

`concurrent_agents` rule. The atlas-meta bookkeeping surface is limited to

docs-only PM artifacts (this file, `backlog.md`, `checklist.md`) and the

parent-side submodule gitlink.



**Forward-only invariant**: this chore lands a single docs-only commit

above current HEAD, adding this classification section + a brief reference

bullet under "Surfacing risks" (see below). No submodule gitlinks are

touched (all 7 already aligned). No executable bit promotions. No

sub-bullet of any inner submodule is mutated.



**Audit-lifecycle recommendation**: re-run this per-submodule

classification probe on every subsequent atlas-meta chore landing that

touches a submodule pointer. The probe is a single basher command

sequence (per-submodule: `cd /d/atlas/repos/<X> && git rev-parse HEAD`

+ `git ls-files --stage repos/<X>` from parent + `git status --short | wc -l`).

A weekly re-probe cadence catches dirty-count drift between chore

landings.



**Per-submodule classification audit-state transitions** (relative to

the prior `e0bf55684` cross-tree reclamation audit at line 251 of this file):



- coeus: `CLEAN + DIVERGED (dirty count 4)` → `STABLE/SYNCED (dirty count 0)`

  — bookkeeping-advance closed the gap; the 4 prior dirty files were

  committed.

- kwavers: `dirty 266-299` → `dirty 81` — net reduction of ~190 paths

  via peer-side Burn-compat facade + par_for_each residual work.

- ritk: `dirty 65` → `dirty 24` — net reduction of 41 paths via

  sub-batch #4 (RITK-crate-migrate Cargo.toml dep strip) + sub-batch #5

  (RITK-spatial-rebind) + sub-batch #6 (RITK-xtask-ci allowlist refresh)

  partial land.

- helios: `dirty 0` → `dirty 10` — small regression (likely H-063 imaging

  audit iteration in peer WT).

- gaia: `dirty 5` → `dirty 5` — no change.

- hephaestus: `dirty 0` → `dirty 1` — trivial regression (1 path noise).

- CFDrs: `dirty 2` → `dirty 4` — small regression (+2 paths).



**Net effect summary**: 2 reductions, 1 stable, 3 trivial regressions,

0 pointer-advance candidates, 0 classification-d migrations. Atlas-meta

has no pending bookkeeping for any of the 7 submodules; the next atlas-meta

action is purely docs-only (this chore + future audit refreshes).



**Reference bullet under Surfacing risks**: see the new

**row 12** below.



## Surfacing risks (closeout axioms for next sprint)



1. ~~**DRIFT**: `RITK/Cargo.toml:69` retains `wgpu` feature despite DEP-496-01's DONE narrative. Confirm whether the backlog narrative is canonical or the file literal — reopen DEP-496-01 if file is authoritative.~~ **CLOSED 2026-07-06**: inner RITK commit `65a1a0fd` corrected the file literal to remove `wgpu`, refreshed `xtask/burn_surface.allowlist`, and verified Burn GPU backend packages are absent from the RITK workspace dependency tree.

2. ~~**DEAD-FEATURE**: `ritk-core/src/lib.rs:15-17` cfg gate `feature = "mnemosyne-alloc"` references a feature that does not exist in `ritk-core/Cargo.toml`. Confirm and strip.~~ **RETRACTED 2026-07-06** (T1 re-verification): `ritk-core/Cargo.toml:8` declares `mnemosyne-alloc = ["dep:mnemosyne"]` and `Cargo.toml:7` lists it in `default = ["mnemosyne-alloc"]`; `src/lib.rs:15-17` cfg is consistent. The feature exists; the prior claim was a stale-memory misread. No action.

3. ~~**NIGHTLY-PINNED TOOLCHAIN**: `kwavers` workspace pins `nightly` rust (`rust-toolchain-pinned nightly` per `crates/kwavers/simiconductor.rs`;; verify on kwavers toolchain).~~ **RETRACTED 2026-07-06** (T1 re-verification): no `rust-toolchain*` file exists at `repos/kwavers/` (workspace root) or in any first-level subdirectory; the cited `crates/kwavers/simiconductor.rs` path is fictitious. The workspace does not pin nightly at the manifest level. Any nightly-feature usage must be re-verified at the per-crate site, not at the workspace toolchain pin level.

4. **TRAIN-PIN**: `let''o_dict`/realbind picked in mid-sprint between `coeus-tensor::Tensor` vs `let''o::Array` for autodiff carrier; coordinate via design note in `let''o/crate` and `coeus/docs/`.

5. **CR-2 dependency-edge cycles**: removing `#[global_allocator]` from library crate `cfd-core`/`ritk-core` requires DI handles in main binaries — verify binaries have zero-handle init paths after tracking.

6. **PEER-WIP COLLISION (refreshed 2026-07-06 inventory)**: every consumer-batch-owning repo and most provider repos carry **active uncommitted peer WIP** in their working trees, blocking autonomous reclaim. Per-tree state (modified-files count on each branch's working tree):

   - `repos/CFDrs` `codex/cfdrs-atlas-migration`: **79 modified/untracked inner paths on 2026-07-06 recheck** after the `d58d1fe3` Batch #2 closure push. Batch #2 (CFDrs nalgebra → leto + nalgebra-sparse → leto-ops `CsrMatrix`) remains **CLOSED** at `d58d1fe3`, but the current dirty tree is live inner-repo WIP and is not reclaimable from Atlas-meta. Do not retract the CFDrs §C row until the inner tree is clean again or a new CFDrs commit lands.

       - **2026-07-08 CFDrs stable/synced** (post-row-6 melinoe `6c9459513` + audit `e0bf55684` + CFDrs re-verification, CFDrs is stable/synced — no reclamation pending): inner CFDrs HEAD on `codex/cfdrs-atlas-migration` at `8aa7313f`, 2 dirty paths (active peer WIP, down from 79 at the 2026-07-06 inventory cut; the reduction reflects the peer committing the Batch #2 closure push + the AGENTS.md redirect stub), ALIGNED with atlas-meta gitlink `8aa7313f2980cdd9518b95e39f96487653c43148` per T1 re-verification 2026-07-08. CFDrs is on `codex/cfdrs-atlas-migration` with 0 ahead/behind vs `@{u}`; `origin/main` is at `0f578e1a` (the pre-closure state). CFDrs has no new commits since the 2026-07-06 inventory cut and no gitlink divergence. **STABLE/SYNCED (2026-07-08, post `6c9459513`)** — no reclamation action needed; the atlas-meta gitlink is already aligned with the inner HEAD. **Atlas-meta path forward**: no pointer advance needed; CFDrs is stable/synced. **Audit state transition**: CFDrs candidate → STABLE/SYNCED in this chore (`docs(atlas): Note CFDrs/eunomia as stable/synced in e0bf556 audit (row 6 exhausted)`).

   - `repos/ritk` `main`: **0 modified files** after inner commits `65a1a0fd`, `d7a940b5`, and `8f8360ff`; `65a1a0fd` removed Burn's stale `wgpu` feature from the workspace dependency, `d7a940b5` added the Batch #3 sub-batch #1 Atlas-typed parallel trait surface, and `8f8360ff` added typed DICOM attribute reads for downstream imaging consumers. Atlas-parent pointer commits advanced the pointer.

   - `repos/apollo` `refactor/apollo-fft-eunomia`: **236 modified files** (CR-1 closed 2026-07-07; residual Apollo dirty remains peer-active provider WIP).

       - **2026-07-08 Apollo proxy-state reconciliation** (next-most-aged peer claim, 236 dirty paths): inner commit chain progress is heavily concentrated on workflow-gate stabilization (`cd05eac` + `2940d66` + `9df5294`) rather than FFT-eunomia source-tree migration. Measurable inner-state proxy indicators for the migration remain flat (0 rustfft residual file detections via `rg -l '\brustfft\b' crates`, 0 eunomia-typed fft paths via `rg -l 'eunomia::(?:\([^)]+\)|\{[^}]*\}|fft|complex|Fft)' crates`, 0 recently-touched `.rs` sources newer than `Cargo.toml` per `find crates -name '*.rs' -newer Cargo.toml`) compared to the 2026-07-06 baseline; the 236 dirty-path count is unchanged from the 2026-07-06 cut (delta = 0). Atlas-meta records the active inner churn as SSOT surface gate-fix ceremony work (the 9df5294 + 2940d66 + cd05eac lineage is the same 2026-07-07 ssot ceremony anchor cited in row 10's forward-fix annotation), counterindicating the framing that the FFT-eunomia migration itself is forging ahead. Resolution and subsequent source-tree advancement remain entirely peer-owned per the `concurrent_agents` disjoint-scope deferral rule; atlas-meta defers the parent-side `HEAD:repos/apollo` pointer advance until the dirty tree is reclaimed.

   - `repos/kwavers` `codex/kwavers-core-moirai-parallel`: **27 modified/untracked inner paths on 2026-07-06 recheck** at `c6b845f81` (`[ahead 13]` of `origin/codex/kwavers-core-moirai-parallel` per inner `git rev-list --left-right --count`, 2026-07-06 12:45) — peer is actively landing Batch #4 Burn→Coeus migration: landed `1dc47028a` (`kwavers-math` nalgebra → eunomia/leto/moirai-parallel), `f36995162` (kwavers-gpu/solver Hephaestus seam), `400c32624` slice 1 (`burn_wave_equation_1d` PINN→Coeus, 12 files, ~563 lines reconstructed), and `c6b845f81` slice 2 (`burn_wave_equation_2d` dependency graph: acoustic_wave, cavitation_coupled, sonoluminescence_coupled, electromagnetic, adaptive_sampling, meta_learning, transfer_learning, distributed_training, quantization, uncertainty_quantification, universal_solver, field_surrogate/training/trainer). Slice 2 drain: `burn::` line-hits 315→186 (-41%), `use burn` imports 222→125 (-44%), file-count 144→80 (-44%); remaining surface = `burn_wave_equation_3d/{wavespeed,solver,optimizer,mod,tests}` + `elastic_2d/{training,loss,adaptive_sampling}` + 17 top-level test/bench/example files + `kwavers-solver/Cargo.toml:53` `burn` optional dep + `pinn` `dep:burn` line at L62-70 + `crates/kwavers-solver/src/burn.rs` and `burn_compat` module deletions (still pending). Risk #8 framing now partially-resolved by `c6b845f81` (commit body: "per prior direction not to build burn-compat shims"); risk stays live until the facade + Cargo.toml strip land.

       - **2026-07-08 Batch #4 surface-met reconciliation** (this row's 2026-07-06 inventory refresh + post-Batch-#4 inner churn): inner kwavers HEAD advanced `c6b845f81` → `b605e2e74` (subject `refactor(physics): Use Moirai for heat source`), with 18 commits landing since the row 6 inventory cut. Per T1 verification at inner HEAD `b605e2e74`: `crates/kwavers-solver/src/burn.rs` (the burn_compat facade) is **ABSENT** (`[ -f ... ]` returns false); `rg -n '\bburn\b' -g '*.toml' .` returns zero hits in both `crates/kwavers-solver/Cargo.toml:24` and root `Cargo.toml:138`; the canonical inner chore at `8b128c478` carries the verbatim subject `chore(kwavers-solver): Remove dead burn compatibility shim and drop burn dependency`. **Row 6 risk #8 partial-closeout**: the burn_compat facade + Cargo.toml strip pre-condition (the open pre-condition cited in row 8's `Skew` sub-section as "still pending") is RESOLVED — the Batch #4 MFA-surface condition (no `burn` optional dep + no `pinn` `dep:burn` line + no burn_compat facade) is now MET on the kwavers side. Outstanding Batch #4 closure steps still peer-side: (a) re-grep the 186 hits / 80 files residual at inner HEAD `b605e2e74` (the strip + facade-delete should drive this count toward zero); (b) kwavers-side final closeout commit on `codex/kwavers-core-moirai-parallel`; (c) atlas-meta `HEAD:repos/kwavers` pointer advance via the row 10/11 dynamic-SHA extraction sub-rule. **Atlas-meta path forward**: atlas-meta continues to defer the parent-side pointer advance for `repos/kwavers` until (b) lands, per `concurrent_agents` disjoint-scope rule. The atlas-meta row 8 'BATCH #4 SLICE-INTEGRITY' Surfacing-risk entry is NOT auto-closed by this strip+drain — row 8's risk-framing on "burn-shape leakage" compliance still requires fresh verification after kwavers-side final commit. **Most-aged peer-claim resolved at the manifest/source surface**: kwavers (231 dirty paths in current WT) is now the row 6 most-aged consumer-batch claim with Batch #4 surface-met + Batch #1 (84 `par_for_each` sites / 28 files pending in `crates/kwavers-{solver,physics}/Cargo.toml:24+20`) outstanding. Batch #1 (Rayon→Moirai residual, 84 sites / 28 files) and Batch #4 (Burn→Coeus, 186 hits / 80 files — down from 315/144 after slice 2) both remain OPEN but peer-active; Atlas-meta defers to peer.

       - **2026-07-08 kwavers full surface-met reconciliation** (post-row-6 apollo `57d0c3b75` refresh, kwavers now most-aged consumer-batch peer-claim): inner kwavers HEAD advanced `b605e2e74` → `05500930c` (21 commits since the prior sub-bullet cut, `[ahead 0, behind 0]` `origin/codex/kwavers-core-moirai-parallel` parity confirms peer-driven at this exact inner HEAD). Per T1 re-grep at inner HEAD `05500930c` (later re-verified at `f678dc35e` 2026-07-07 19:56): **burn source residual is now ZERO** (was 186 line-hits / 80 files at 2026-07-06 baseline, now `rg --count-matches '\bburn::' crates --type rust` totals 0) — full clean BEYOND the prior sub-bullet's "strip + facade-delete should drive this count toward zero" prediction; the canonical inner chore at `8b128c478` (`chore(kwavers-solver): Remove dead burn compatibility shim and drop burn dependency`) plus slice 3+ commits (e.g. `702e4f125` ndarray/rayon cleanup) drove the count to zero across the 21-commit chain. **Rayon residual** (Batch #1) halved: 41 `par_for_each` sites / 15 files at `05500930c` (down from 84 / 28 at `b605e2e74`, −51%). **`ndarray` Rayon feature strip is now LANDED** — `702e4f125` removes `features = ["rayon", "serde"]` to `["serde"]` on both `crates/kwavers-{solver,physics}/Cargo.toml:{24,20}`; T1 re-grep at `f678dc35e` 2026-07-07 19:56 confirms zero `ndarray = { features = ["rayon", ...] }` form in the kwavers tree; the manifest-level strip is preserved, BUT `cargo tree -p kwavers-solver -i rayon` still returns `rayon v1.11.0` (1 entry, transitively via `burn_common -> burn -> ritk -> kwavers-{imaging,physics,solver}` — a provider-side obstacle, not a Batch #1 closure item). **Source-side Batch #1 status**: NOT CLOSED at inner HEAD `35ee01076` per the post-`566af324e`/post-`5af6888ec` closure-mark retraction at line 71-93 (41 `par_for_each` sites remain in `crates/kwavers-solver/src/**` and are direct `Zip::indexed().par_for_each()` invocations on `ndarray` arrays, not kwavers-medium adapter calls). **Dirty WT**: 266 total paths at `05500930c` (per `git status --short | wc -l`; the per-status-field breakdown includes 194 `M` + 4 `??` plus 68 paths in other git status categories such as `D`/`A`/`R`/`MM` not separately broken out in the probe) — UP from 231 at the prior apollo sub-bullet cut, consistent with active ongoing development rather than closure. **Closeout status**: no formal `closeout` / `final` / `completion` commit found in the last 30 commits — peer appears to be landing Batch #4 slice-by-slice without an explicit close. **Atlas-meta path forward**: disjoint-scope deferral continues — `repos/kwavers` `HEAD:repos/kwavers` pointer advance remains deferred per `concurrent_agents` rule, with the prior sub-bullet's criterion of "kwavers-side final closeout commit" still unsatisfied. The atlas-meta row 8 'BATCH #4 SLICE-INTEGRITY' Surfacing-risk entry's "burn-shape leakage" compliance check still requires fresh verification once a closeout commit lands (the burn-source-zero count addresses the literal burn-residual half but not the idiomatic-shape half). **Next-most-aged peer-claim (post-apollo)**: the apollo row 6 sub-bullet's regex-strengthening docs-only followup (`57d0c3b75`) marked apollo's row 6 sub-bullet regex-complete (the apollo proxy-state amendment itself is `7b65bfeb`; `57d0c3b75` is the subsequent docs-only chore that closed the MED-tier brace-grouped-Rust-imports gap in the proxy-indicator regex); kwavers is now the row 6 active-most-aged consumer-batch peer-claim with Batch #4 burn source residual fully met and the Batch #1 source-side migration still in progress (41 residual sites; manifest-stage strip landed at `702e4f125`).

       - **2026-07-08 kwavers closeout watchpoint** (active trigger; per user instruction, post-row-6 cross-tree audit `e0bf55684` refresh): see the `## Forward-looking watchpoints` section for the full trigger condition (KW-CV-001) + action sequence (per row 11 DYNAMIC-SHA-EXTRACTION MANDATE). Re-verify the trigger (`cd /d/atlas/repos/kwavers && git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l`) on every kwavers sub-bullet refresh before declaring the watchpoint CLOSED.

   - `repos/hermes` `perf/compress-buffer-hoist`: 46 modified (peer SIMD-ISA dispatch).

   - `repos/moirai` `main` (was `refactor/remove-dead-subsystems` at the prior sub-bullet cut): 0 modified (per T1 recheck 2026-07-08; was 26) + 3 new commits since the 2026-07-06 inventory cut; clean WT + DIVERGED with atlas-meta gitlink `9b7881f0` — see sub-bullet for detail.

       - **2026-07-08 moirai clean reclamation candidate** (post-row-6 leto `4a1e2687f` + audit `e0bf55684` + watchpoint `b44845afa` + closure-mark `512ff108` refresh, moirai now most-advanced peer-claim among the remaining 2 candidates hermes/moirai): inner moirai HEAD on `main` at `37ff12d5` (was on `refactor/remove-dead-subsystems` at the prior sub-bullet cut), 3 commits since the 2026-07-06 inventory cut (the only one of the 2 candidates with new commits since the inventory cut; hermes at 0), 0 dirty paths (down from 26 at the prior cut), CLEAN + ALIGNED with `@{u}` (HEAD == @u at `37ff12d5`). Per T1 verification at inner HEAD `37ff12d5`: the 3-commit chain (`37ff12d` Merge pull request #64 from `refactor/remove-dead-subsystems` + `553134d` `fix(benchmarks): repair 3 stale source-contract assertions after 4d790a9` + `19f6b2a` `feat(executor,parallel,gpu): moirai-owned block_on; fused triple/quad chunk ops; remove pollster`) represents the completion of the `refactor/remove-dead-subsystems` work and its merge into `main` per PR #64. **Branch migration**: the prior sub-bullet's `refactor/remove-dead-subsystems` branch has been merged into `main`, so the peer work is now on the integration branch. **Clean state**: 0 dirty paths (M=0, ??=0, D=0) — the peer has fully committed the refactor work. **RECLAMATION CLOSED (2026-07-08, post `554e906f4`)** — was CLEAN + DIVERGED with atlas-meta gitlink `9b7881f0` (which was 3 commits behind the inner HEAD `37ff12d5`); ready for parent-side pointer advance; advance executed in `554e906f4` (`chore(atlas): Advance repos/moirai pointer to 37ff12d5 (reclamation audit)`) per the dynamic-SHA extraction pattern (`cd /d/atlas/repos/moirai && git rev-parse 37ff12d5^{commit}` = `37ff12d584e1fb472f41b4e40c702d708aba1dac`). Atlas-meta `HEAD:repos/moirai` gitlink now ALIGNED at `37ff12d584e1fb472f41b4e40c702d708aba1dac`. **Atlas-meta path forward (updated 2026-07-08)**: the moirai pointer advance executed in `554e906f4` (see RECLAMATION CLOSED rationale above for the dynamic-SHA extraction pattern). **Audit state transition**: moirai reclamation candidate → CLOSED in this chore (`docs(atlas): Mark e0bf556 cross-tree reclamation audit moirai pointer-advance as CLOSED (post 554e906)`); the row 6 amendment records the peer-state transition from `refactor/remove-dead-subsystems` + 26 dirty to `main` + 0 dirty + 3 new commits. **Next-most-advanced peer-claim (post-leto)**: the leto main-branch advancement amendment (`4a1e2687f`) marked leto's row 6 sub-bullet documented; moirai is now the row 6 active-most-advanced peer-claim (3 commits since the inventory cut, the only new-commits count among the 2 candidates; hermes at 0). **hermes state note**: hermes inner is at HEAD `1b5392a5` (NOT detached per the current probe; the earlier "detached-HEAD" framing in the prior row 6 bullet was either probe-error or has since been resolved), 46 dirty paths (unchanged from the prior probe), ALIGNED with atlas-meta gitlink `1b5392a5`; hermes is on a branch that is ahead of `origin/main` at `9d0a358d` (no upstream tracking on the current branch, hence `@{u}` = NONE). hermes remains active peer WIP with no new commits since the 2026-07-06 inventory cut; the row 6 amendment for hermes is deferred until hermes advances or the dirty state changes.

   - `repos/leto` `main` (was `codex/leto-cr4-ssot-rebind` at the prior sub-bullet cut): 15 modified (per T1 recheck 2026-07-08; was 14); the prior `disjoint from Atlas-meta` qualifier pertained to the codex-branch work and is now ambiguous on the `main`-branch state — see sub-bullet for detail.

       - **2026-07-08 leto main-branch advancement** (post-row-6 coeus `a502d6e49` + audit `e0bf55684` + watchpoint `b44845afa` refresh, leto now most-advanced peer-claim among the remaining 3 candidates hermes/moirai/leto): inner leto HEAD on `main` at `d9e8ac959` (was on `codex/leto-cr4-ssot-rebind` at the prior sub-bullet cut, advanced past the CR-4 closure at `b15439ba` per the prior row 6), 2 commits since the 2026-07-06 inventory cut (the only one of the 3 candidates with new commits since the inventory cut; hermes at 0 + moirai at 0), 15 dirty paths (up from 14 at the prior cut), DIVERGED with atlas-meta gitlink `626ebf53`. Per T1 verification at inner HEAD `d9e8ac959`: ahead/behind `@{u}` parity; the 2-commit chain is post-CR-4-closure peer work, not closeout-style per the KW-CV-001 trigger condition (`closeout|final|completion|close-batch`). **Branch migration**: the prior sub-bullet's `disjoint from Atlas-meta` qualifier pertained to the `codex/leto-cr4-ssot-rebind` work branch; the current `main`-branch state is past the CR-4 closure and the work has migrated to the integration branch, so the disjoint qualifier is now ambiguous. The leto work is mostly provider-side (CR-4 closed) plus peer-side reconciliation; atlas-meta does not own the leto source-tree content. **Gitlink divergence**: atlas-meta `HEAD:repos/leto` gitlink at `626ebf53`, lagging the inner `d9e8ac959` by 2 commits — a future pointer-advance opportunity once the disjoint-scope rule permits. **Atlas-meta path forward**: disjoint-scope deferral continues — `repos/leto` `HEAD:repos/leto` pointer advance remains deferred per `concurrent_agents` rule. The 2-commit chain recent (per `git log --since='2026-07-06'`) is post-CR-4-closure peer work + a merge per the fresh probe. **Next-most-advanced peer-claim (post-coeus)**: the coeus Batch #4 enablement amendment (`a502d6e49`) marked coeus' row 6 sub-bullet documented; leto is now the row 6 active-most-advanced peer-claim (2 commits since the inventory cut, the only new-commits count among the 3 candidates; hermes at 0 + moirai at 0).

   - `repos/melinoe` `codex/halo-vecdeque-migration`: 13 modified.

       - **2026-07-08 melinoe pointer-advance closure-mark** (post-row-6 moirai `8179d9fcf` + audit `e0bf55684` + melinoe pointer-advance `eb0abafd9` refresh, melinoe reclamation candidate → CLOSED): inner melinoe HEAD on `main` at `ba91946`, 1 new commit since the 2026-07-06 inventory cut, 1 dirty path (active peer WIP), DIVERGED with atlas-meta gitlink `7ec0a44e558cacdb6514c30dd4e2dbe70a06f026` at the e0bf556 audit time. **RECLAMATION CLOSED (2026-07-08, post `eb0abafd9`)** — advance executed in `eb0abafd9` (`chore(atlas): Advance repos/melinoe pointer to ba91946 (reclamation audit)`) per the dynamic-SHA extraction pattern (`cd /d/atlas/repos/melinoe && git rev-parse ba91946^{commit}` = `ba9194613169827a6db55e7458b8e0320cd515e1`). Atlas-meta `HEAD:repos/melinoe` gitlink now ALIGNED at `ba9194613169827a6db55e7458b8e0320cd515e1`. **Atlas-meta path forward (updated 2026-07-08)**: the melinoe pointer advance executed in `eb0abafd9` (see RECLAMATION CLOSED rationale above for the dynamic-SHA extraction pattern). **Audit state transition**: melinoe reclamation candidate → CLOSED in this chore (`docs(atlas): Mark e0bf556 cross-tree reclamation audit melinoe pointer-advance as CLOSED (post eb0abaf)`).

   - `repos/helios` `codex/kwavers-atlas-integration`: **0 dirty direct paths** after the Helios/RITK DICOM ownership closure; H-061/H-062 removed the unused direct `num-traits` edge and aggregate dicom-rs `ndarray` feature edge, routed production DICOM parse/typed attributes/transfer syntax/pixel decode through `ritk-dicom`, added the local Melinoe patch required by patched Gaia, and synced Helios PM evidence. H-063 tracks the remaining `helios-imaging` generic-toolkit audit.

   - `repos/gaia` `refactor/migrate-to-leto-geometry`: 5 modified, including CSG source and benchmark files; no PM-only split claim remains.

   - `repos/coeus` `main`: 22 modified (per T1 recheck 2026-07-08; was 19 at the prior sub-bullet cut), including `coeus-core` + `coeus-python` + `docs` files; no PM-only split claim remains.

       - **2026-07-08 coeus Batch #4 enablement reconciliation** (post-row-6 kwavers `a7696c09e` refresh, coeus now most-advanced provider peer-claim): inner coeus HEAD on `main` at `5e3e63967`, 21 commits since the 2026-07-06 inventory cut, ahead-of-prior sub-bullet state. Per T1 probe at inner HEAD `5e3e63967`: **22 modified files** in WT (M-only, no untracked/deleted/added/renamed — focused change set) — UP from 19 at the prior sub-bullet cut. Per-basher file-bucket decomposition of the 21-commit chain: `coeus-core` + `coeus-python` + `docs` are the dominant directories; recent commit subjects include PReLU learnable weights, benchmark deduplication, optimization tests, max/min/remainder operator additions, and test coverage for parity with Burn. **Batch #4 (Burn→Coeus) enablement signals**: per T1 verification, `crates/coeus-core/src/scalar*` and `crates/coeus-core/src/lib.rs` contain NO `trait Scalar` declaration (CR-4 eunomia SSOT rebind complete and consolidated — no `Scalar` trait residue in coeus); no `\\bburn\\b` reference in root `Cargo.toml` (no transitive burn dep). The 21-commit chain adds coeus-side features (PReLU, max/min/remainder, parity tests) that progressively match what Burn provided, enabling the kwavers-side Batch #4 closure path. **Gitlink divergence**: atlas-meta `HEAD:repos/coeus` gitlink currently tracks `b2beec3e`, lagging the inner HEAD `5e3e6396` by 21 commits — a future pointer-advance opportunity once the disjoint-scope rule permits. **Closeout status**: no formal `closeout` / `final` / `completion` commit in the last 30 commits; peer is landing incremental feature additions without an explicit close. **Atlas-meta path forward**: disjoint-scope deferral continues — `repos/coeus` `HEAD:repos/coeus` pointer advance remains deferred per `concurrent_agents` rule. coeus is a provider-extension surface per the row 8 register (not a consumer-batch), so the row 6 amendment is informational only; the Batch #4 closure is still peer-driven and atlas-meta does not own the coeus source-tree content. **Next-most-advanced peer-claim (post-kwavers)**: the kwavers Batch #4 full surface-met amendment (`e128487a9` + `a7696c09e`) marked kwavers' row 6 sub-bullet closeout-pending; coeus is now the row 6 active-most-advanced peer-claim (21 commits since the inventory cut, the highest count among the remaining 11 peer-claim trees).





       - **2026-07-08 — COEUS Batch #4 enablement TRACKING entry (post `715cff24e` coeus bulk-provider-pointer-advance; refines the line-302 reconciliation sub-bullet)**: this entry supplements (NOT replaces) the line-302 reconciliation paragraph with ORTHOGONAL content — (i) actionable cross-gate ((a)+(b)) for atlas-meta pointer advance; (ii) closeout-pattern filter FALSE POSITIVE handling; (iii) user's vision items (a)/(b)/(c) distinctness scope; (iv) row-8 co-dep justification (PRESUMED pending verification). **Inventory figure correction**: fresh basher probe at inner HEAD `5e3e63967` (2026-07-08, post-PR-#208 merge) shows **0 modified files in WT** vs the reconciliation paragraph's "22 modified" (pre-merge-freshen state); **supersede coefficient rule**: `min(reconciliation-fig, fresh-probe-fig)` (the lower figure is authoritative; re-verify on every Coeus sub-bullet refresh to prevent divergence) (*supersede application*: `min(22, 0) = 0`; rule entry chain `min(22, 8)=8` \u2192 `min(22, 0)=0`) (*basis note*: prior 8 measured at WT-vs-pre-715cff2-atlas-meta-gitlink; fresh-probe 0 measured at detached inner HEAD `5e3e63967`).

         - **Distinctness scope vs user's vision items**: (a) Apollo FFT→eunomia migration: CLOSED per the user's vision item (a); the atlas-meta bookkeeping closure-form is the bulk-provider-pointer-advance chore at `2e1c4f20d` (advancing the parent's apollo gitlink to inner HEAD `2e6f9be62` — the merger of PR #6 from `ryancinsight/refactor/apollo-fft-eunomia`). NOT apollo — that migration is the upstream provider side that has closed; THIS entry is the downstream coeus-provided capability enabling the kwavers-side Batch #4 closure path. (b) Hermes SIMD-ISA dispatch migration: DORMANT per the user's vision item (b); `perf/compress-buffer-hoist` HEAD `1b5392a` (2026-07-04), 0 dirty, no new commits since prior probe, ALIGNED with atlas-meta gitlink. (c) COEUS Batch #4 enablement: THIS ENTRY per the user's vision item (c). Provider-side capability surface (NOT a consumer migration batch) — closing the per-feature gap between Burn autodiff (parametric `nn::PRelu`; `tensor::max_dim`/`min_dim`/`remainder`; activation parity suites) and coeus autodiff (static `PReLU` pre-this-batch; unverified broadcasting for `BackendOps::max`/`min`/`remainder`; no formal Burn parity tests).

         - **Other distinctness dimensions (full enumeration)**: **CR-4** (eunomia SSOT rebind, closed 2026-07-05); **Batch #1** (kwavers Rayon residual, manifest-stage strip landed at `702e4f125`, 41 source sites pending); **Batch #4** (kwavers PINN Burn→Coeus consumer-side full surface-met per row 6 sub-bullet + row 8 facade WIP); **kwavers ndarray → leto's ndarray-compat** tracking entry (numerical-array vocabulary, not autodiff feature parity); **Surfacing-risks row 8 BATCH #4 SLICE-INTEGRITY** (`crates/kwavers-solver/src/burn.rs` facade WIP — PRESUMED co-dependent with this entry because row 8 facade aliases coeus APIs added in this 21-commit chain, pending direct T1 grep verification, hence the (b) gate); **provider extension register** rows `Var<T,B>::scatter_add` (coeus-autograd) + `eq/ne/lt/gt` comparison free fn surface on `BackendOps` (coeus-core) (deferred-conditional extension fixup rows; this entry is for enabling-feature surface, not extension-fixup surface). **Parent-reference note**: this entry's immediate chore parent is `2e1c4f20d` (apollo bulk-provider-pointer-advance chore); the line-302 reconciliation paragraph's implicit reference to the F1-fixup chore `7dbea8a78` is the grandparent, NOT the immediate parent.

         - **Closeout status (refines reconciliation paragraph)**: coeus-internal closeout-pattern filter on last 30 commits (`closeout|final|completion|close-batch`) returns **1 hit** — `1ae2f30 docs(backlog): Document CR-4 SSOT rebind completion (2026-07-05)` — CR-4 docs-only commit; `completion` keyword incidentally matched; NOT a COEUS Batch #4 enablement closeout. Effective trigger count for Batch #4 enablement-specific closeout = 0. A formal closeout would be a separate `chore(coeus): Closeout Batch #4 enablement (PReLU + max/min + remainder + parity tests)` style commit.

         - **Atlas-meta path forward (cross-gate tracking post-bookkeeping-advance, refines reconciliation's deferral-only framing)**: defer `HEAD:repos/coeus` pointer advance (current gitlink is now `5e3e63967061ea5bfad5a7dba4cb1e2170d0fcee` (aligned with inner via bookkeeping-advance at `715cff24e`; the original 21-commit deferral was bypassed by the bulk-pointer-advance sequence)) -- NB: the bookkeeping-advance here is *atlas-meta bookkeeping surface* only (already executed at `715cff24e`; gitlink now aligns inner HEAD); the gate below refers to *closure-style pointer advance* (TRACKING → closure-mark transition, contingent on the peer's authoritative (a)+(b) closeout commit), not to further bookkeeping -- until BOTH (a) + (b) are MET: (a) `cd /d/atlas/repos/coeus && git log --oneline -30 | grep -ciE 'closeout|final|completion|close-batch'` returns ≥1 hit whose subject EXPLICITLY references Batch #4 enablement closure (PReLU + max/min + remainder + parity tests); the `1ae2f30 docs(backlog): Document CR-4 SSOT rebind completion` keyword hit is excluded as FALSE POSITIVE. (b) Surfacing-risks row 8 BATCH #4 SLICE-INTEGRITY reconciles `crates/kwavers-solver/src/burn.rs` facade WIP. (a) + (b) are PRESUMED co-dependent pending direct T1 grep verification of `burn.rs` against the new coeus APIs. Re-verify both gates on every COEUS sub-bullet refresh; promote to closure-mark form once (a) + (b) are both MET.



   - `repos/eunomia` `main`: 7 modified (acos/asin/atan peer claim).

       - **2026-07-08 eunomia stable/synced** (post-row-6 melinoe `6c9459513` + audit `e0bf55684` + eunomia re-verification, eunomia is stable/synced — no reclamation pending): inner eunomia HEAD on `main` at `57d7789`, 7 dirty paths (active peer WIP, unchanged from the 2026-07-06 inventory cut), ALIGNED with atlas-meta gitlink `57d778930ecd25e77416c49ee10c9b6670f0ea70` per T1 re-verification 2026-07-08. eunomia is on `main` with 0 ahead/behind vs `@{u}`; `origin/main` is at `57d7789` (the CR-4 closure state). eunomia has no new commits since the 2026-07-06 inventory cut and no gitlink divergence. **STABLE/SYNCED (2026-07-08, post `6c9459513`)** — no reclamation action needed; the atlas-meta gitlink is already aligned with the inner HEAD. **Atlas-meta path forward**: no pointer advance needed; eunomia is stable/synced. **Audit state transition**: eunomia candidate → STABLE/SYNCED in this chore (`docs(atlas): Note CFDrs/eunomia as stable/synced in e0bf556 audit (row 6 exhausted)`).

   - **Clean working trees (2026-07-08 cross-tree reclamation audit)**: per T1 fresh probe of the 5-tree candidate set (helios / ritk / themis / hephaestus / mnemosyne); see sub-bullet below for per-tree detail. Summary: `repos/themis` is fully reclaimed (clean WT + advanced in `a21e94bcb` from prior DIVERGED state to ALIGNED at `a51b327`); `repos/hephaestus` is clean + ALIGNED (tracked, no advance needed); `repos/mnemosyne` is near-clean (4 dirty, DIVERGED); `repos/helios` and `repos/ritk` show regression from the inventory cut (0→21 and 0→10 dirty respectively, plus helios has inner HEAD anomalously at the atlas-meta chore SHA `a502d6e49` — detached-HEAD state). The original inventory line is partially stale; the sub-bullet records the per-tree fresh state for cross-session auditability.

       - **2026-07-08 cross-tree reclamation audit** (post-row-6 coeus `a502d6e49` refresh, fresh 5-tree probe of the clean-tree candidate set helios / ritk / themis / hephaestus / mnemosyne): per-tree state (branch + HEAD + dirty count + `@{u}` parity + inner-vs-parent gitlink DIVERGED/ALIGNED):

  - `repos/helios` `codex/kwavers-atlas-integration` (inner HEAD anomalously at `a502d6e49` — the atlas-meta chore SHA, not a helios-internal SHA; detached-HEAD state): 21 dirty paths (was 0 at the inventory cut after H-061/H-062 closure), DIVERGED with atlas-meta gitlink `74f380ec9`. **REGRESSION**: the 0-dirty state has eroded. H-063 imaging audit remains the open followup. Disjoint-scope rule prevents atlas-meta from mutating helios inner; helios-side peer action required to recover the detached-HEAD + dirty state (e.g., `cd repos/helios && git checkout codex/kwavers-atlas-integration && git reset --hard 74f380e` would restore the post-H-061/H-062 state, but this is peer-owned).

  - `repos/ritk` `main` HEAD `00d57005`: 10 dirty paths (was 0 at the inventory cut after `65a1a0fd` / `d7a940b5` / `8f8360ff`), ALIGNED with atlas-meta gitlink `00d57005` (no pointer advance needed). **REGRESSION**: the 10-dirty state is post the Batch #3 sub-batch #3 OPENED per-crate Atlas-typed migrators (7-per-crate sub-atomic increment queue per the prior row 6); the 0-dirty state was post the `8f8360ff` inner chore. Not yet ready for pointer advance while dirty.

  - `repos/themis` `main` HEAD `a51b327`: 0 dirty paths, ALIGNED with atlas-meta gitlink (was DIVERGED at the e0bf556 audit time; advance subsequently executed in `a21e94bcb` per the row 11 DYNAMIC-SHA-EXTRACTION MANDATE — see RECLAMATION CLOSED rationale below). **RECLAMATION CLOSED (2026-07-08, post `a21e94bcb`)** — was clean WT + DIVERGED at the audit time, ready for parent-side pointer advance; advance executed in `a21e94bcb` (`chore(atlas): Advance repos/themis pointer to a51b327 (reclamation audit)`) per the dynamic-SHA extraction pattern (`cd /d/atlas/repos/themis && git rev-parse a51b327^{commit}` = `a51b327accbd8c417d6b661c40ecefb6098ddb1a`). Atlas-meta `HEAD:repos/themis` gitlink now ALIGNED. The themis inner has new commits since the prior row 6 cut but no formal closeout-style commit; themis is a peripheral provider-cache crate with no migration surface, so the advance was routine bookkeeping rather than migration closeout.

  - `repos/hephaestus` `ks5-cholesky-panel` HEAD `7bc0be92f`: 0 dirty paths, ALIGNED with atlas-meta gitlink. **CLEAN + TRACKED** — no pointer advance needed. The ks5-cholesky-panel active-regular commits (per the prior row 6) have not advanced the parent gitlink, consistent with the inner state being stable.

  - `repos/mnemosyne` `main` HEAD `4f5e905`: 4 dirty paths (low), DIVERGED with atlas-meta gitlink. **NEAR-CLEAN** — close to reclamation but the 4 dirty paths block immediate pointer advance. The `codex/eunomia-local-source` active-regular commits (per the prior row 6) are landing incrementally; once the dirty state clears, mnemosyne will be ready.



**Atlas-meta path forward (updated 2026-07-08)**: the audit identified `repos/themis` as the sole ready pointer-advance candidate among the 5; the pointer advance executed in `a21e94bcb` (see themis per-tree bullet above for the dynamic-SHA extraction pattern). **Audit state transition**: themis reclamation candidate → CLOSED in this chore (`docs(atlas): Mark e0bf556 cross-tree reclamation audit themis pointer-advance as CLOSED (post a21e94b)`); the other 4 candidates (helios regression, ritk regression, hephaestus stable, mnemosyne near-clean) retain their prior state. The helios + ritk regressions remain flagged for peer-side review; atlas-meta does not own the inner source-tree content. The hephaestus + mnemosyne states are noted for forward monitoring. **Net effect of the 2026-07-08 audit vs the 2026-07-06 inventory**: the clean-tree inventory is partially stale (2 regressions + 1 closed reclamation candidate [themis, advanced in `a21e94bcb`] + 1 stable + 1 near-clean); atlas-meta's disjoint-contribution surface is now primarily the docs-only row 6 amendments + future pointer advances, with the inner-state regressions requiring peer action.

       - **2026-07-08 kwavers bookkeeping regression RESOLVED** (post-audit follow-up): per T1 fresh probe at the current session, the kwavers inner is now on `codex/kwavers-core-moirai-parallel` (NOT detached, recovering from the prior turn's detached-HEAD anomaly at `051e7dfd5`), atlas-meta `HEAD:repos/kwavers` gitlink ALIGNED at `f678dc35e3e44a8e416d746004b0508cc3af9366` (same as inner HEAD), 5 new commits since the watchpoint setup at `05500930c` (`73633295f` + `115ba10e6` + `4b83a6389` + `051e7dfd5` + `f678dc35` — all kwavers-internal Moirai migration work, no atlas-meta chore pollution). 267 dirty files in the kwavers inner working tree (active peer WIP, up from 266 at the e0bf556 audit cut). **2026-07-08 follow-up advance (post-RESOLVED-note)**: atlas-meta `HEAD:repos/kwavers` gitlink advanced from `f678dc35` to `35ee01076` (1 new commit `35ee01076` `fix(solver): Preserve adaptive-error layout order`); kwavers inner now at 299 dirty files (up from 267 at the bcd98ba RESOLVED-note cut); atlas-meta gitlink ALIGNED with inner HEAD at `35ee01076` (clean bookkeeping update, no regression). KW-CV-001 watchpoint remains ACTIVE (trigger count = 0 at the filtered kwavers-internal check). KW-CV-001 watchpoint remains ACTIVE (trigger count = 0 at the filtered kwavers-internal check; no closeout-style commit has landed). The bookkeeping regression flagged in the prior turn (detached-HEAD at `051e7dfd5` + atlas-meta gitlink at atlas-meta chore SHA) has been resolved — the recovery happened outside the atlas-meta session (peer-side or a separate `git submodule update` that corrected the detached-HEAD state). This is a POSITIVE follow-up to the e0bf556 audit: the kwavers inner is now healthy and aligned, and the peer continues landing Moirai migration slice-by-slice.

   - **Net effect**: Atlas-meta's only disjoint-contribution surface during this 2026-07-06 refresh is the atlas-meta PM artifacts themselves. The CR-class provider-side obstacles and the consumer batches #1–#4 all reside inside trees with peer WIP, so the next autonomous consumer-batch sprint must defer until peer WIP commits land or the claim is genuinely released via the documented abandon-protocol.

   - **2026-07-08 - Bulk-provider-surface sequence SEQUENCE-AUDIT-CLOSED (post-`36ecd8001` COEUS TRACKING entry)**: 7-commit pointer-advance sequence spanning the provider and peripheral surfaces. Sequence-atlas-meta accounting closed; MIXED topology documented; per-submodule reclaim status varies (3 disposably reclaimed, see details). Atlas-meta gitlinks now ALIGNED across the sequence via the dynamic-SHA extraction pattern in the parent chores.

     - *Disjoint advances (5)*: `a21e94bcb` themis (RECLAMATION CLOSED, dynamic-SHA extraction in `a21e94bcb`), `0ca731226` hephaestus (CLEAN + ALIGNED, no extraction needed), `554e906f4` moirai (RECLAMATION CLOSED, dynamic-SHA extraction in `554e906f4`), `eb0abafd9` melinoe (RECLAMATION CLOSED, dynamic-SHA extraction in `eb0abafd9`), `2e1c4f20d` apollo (ATLAS-META POINTER-ADVANCED, dynamic-SHA extraction in `2e1c4f20d` resolves apollo bookkeeping gitlink to inner `2e6f9be`; but apollo still active peer WIP with 236 dirty paths per row 6 apollo proxy-state reconciliation; SEQUENCE-AUDIT-CLOSED does NOT imply apollo reclaim-closed).

     - *Parent-context provenance*: Records the external trigger conditioning each disjoint advance. 3 are **[peer-driven docs closure]** (`a21e94bcb` themis via parent `4a1e2687f` Reconcile Surfacing-risks row 6 leto main-branch; `eb0abafd9` melinoe via parent `314db47e9` Note kwavers follow-up advance; `2e1c4f20d` apollo via parent `7dbea8a78` Reconcile kwavers ndarray Total-line framing -- each parent emitted substantive `gap_audit.md` peer-state recognitions between the prior pointer advance and the current disjoint advance). 2 are **[atlas-meta bookkeeping]** (`0ca731226` hephaestus via parent `126428a60`; `554e906f4` moirai via parent `918f95629` -- both parents are `build(atlas): Update kwavers solver head` kwavers-watcher submodule advances with no substantive atlas-meta docs content).

     - *Cascade advance (1)*: `715cff24e` coeus pointer-advance forward-triggering `02da06611` 5-submodule cascade (eunomia+helios+hermes+leto+mnemosyne; see individual sub-bullets for their respective documented/stable states).

     - *Cross-references*: See the Coeus TRACKING entry (~L305) for the cascade's bookkeeping-advance framing and substantive enablement narrative. This entry serves strictly to audit-close the MIXED sequence without substantive overlap.

7. **CR-4 ADR 0005 status**: status **Proposed**, deferred bump-to-Accepted across this session (live implementation closed the rebind per `2b3f820` coeus + `b15439baf` leto + `5328de1c` atlas closure). **CLOSED 2026-07-05** by atlas-meta commit `b66ec228` — `docs/adr/0005-eunomia-scalar-ssot.md` status line now reads "Accepted — implementation closed 2026-07-05" citing all four closing commits (`57d7789` eunomia + `2b3f820` coeus + `b15439baf` leto + `5328de1c` atlas closure). No further action.

8. **BATCH #4 SLICE-INTEGRITY (kwavers, surfaced 2026-07-06)**: peer commit `400c32624` "Migrate burn_wave_equation_1d PINN to native coeus" claims in its body: "rewritten directly against coeus rather than via a burn-shaped compat facade". T1 verification at the commit's own HEAD contradicts this claim: `crates/kwavers-solver/src/burn.rs` (112 lines) IS a burn-shaped compat facade, with module header docstring stating verbatim "Every `use burn::…` in the PINN submodules resolves here — zero changes to those files are required." and "Migration note: As each PINN submodule is fully ported to native coeus API the imports from this module are replaced with direct coeus imports and the module declaration in `lib.rs` is removed." The facade re-exports `burn_compat::{tensor, module, nn, optim, backend, config, prelude, record}` aliased to shadow the removed `burn` crate name. Per `atlas/AGENTS.md` `integrity` §Compatibility soup HARD rule and §"distributed shim, equally prohibited" — `pub use old as new`, `#[deprecated]` re-export, forwarding wrapper, module alias, or adapter layer kept to avoid updating callers" are all prohibited. The facade violates the first (module alias, forwarding wrapper). The companion coeus-side `Module::load_parameters` extension called out in the peer's commit message as having been added in a companion coeus commit is a legitimate upstream-first implementation per `architecture_scoping` upstream-ownership (the capability gap was filled upstream in coeus), EXCEPT the API shape was driven by the burn facade's needs (per the commit body, motivated by replacing Burn's `ModuleMapper` visitor pattern) — i.e., the extension risks recreating the burn-shaped API topology in coeus. `integrity` §"Converted code is rewritten natively in the target API's idioms — never a mechanical transliteration that recreates the old API's shape through local helpers, extension traits, or conversion chains" is an `integrity` HARD-tier prohibition specifically on the *distributed-shim pattern* across the consumer-provider boundary.

   - **Skew**: peer commit message framing ≠ actual code shape at the commit's own HEAD. Surface for peer self-reconciliation: either (a) the `400c32624` commit body is corrected to retract the "no compat facade" claim, AND the Batch #4 closure plan is restated as multi-slice (Slice 1 = `burn_wave_equation_1d` ✅ landed, Slice 2..N = migrate remaining 60+ PINN submodules + 17 top-level files + strip `burn` from `kwavers-solver/Cargo.toml:53` and `kwavers/Cargo.toml:138` + delete `crates/kwavers-solver/src/burn.rs` and `burn_compat` module); or (b) `burn.rs` is deleted now, with all remaining `use burn::…` callsites re-pointed at native `coeus::{core,nn,optim,tensor,autograd,record}` imports per the canonical burn→coeus trait rewire (checklist Batch #4 §B), and the coeus `Module::load_parameters` API is reviewed for idiomatic coeus shape vs burn-shape leakage.

   - Atlas-meta scope: surface-and-record only. The kwavers source tree is peer-claimed (`codex/kwavers-core-moirai-parallel`, `[ahead 12]`, peer ACTIVE). Resolution per `concurrent_agents` disjoint-scope rule is peer-owned. No Atlas-meta pointer advance for `repos/kwavers` until this slice-closure pattern is reconciled.



9. **SEMVER-CHECKS RESOLUTION BLOCKER (mnemosyne-arena → themis dep-resolution)** (2026-07-06, surfaced by pre-batch-#5 verification): `rustup run nightly cargo semver-checks -p ritk-core -p ritk-image -p ritk-spatial --baseline-rev HEAD~N` (regardless of N) diverges at the per-crate `cargo update` regeneration step before rustdoc generation, surfacing `error: failed to select a version for the requirement "themis = \"^0.8.0\""` against the transitive dependency chain `ritk-{core,image,spatial} → leto 0.36.0 → mnemosyne v0.2.0 (git rev 1e014d25) → mnemosyne-arena v0.2.0 (git rev 1e014d25) → themis = ^0.8.0`. This blocks the RITK Batch #3 sub-batch #5 `[major]` standing reminder's pre-merge authoritative-classification gate per `atlas/backlog.md` §In-flight claims §Standing reminders §Sub-batch #5 [major].

   - **Tool/registry mismatch**: the installed toolchain `cargo-semver-checks 0.48.0` does NOT recognise the literal `cargo semver-checks release ...` subcommand (`error: unrecognized subcommand 'release'` exit 2); nor `--locked`/`--offline` flags (`unexpected argument`). Available v0.48.0 baseline modes are `--baseline-version <X.Y.Z>` (registry), `--baseline-rev <REV>` (git rev), `--baseline-root <PATH>`, `--baseline-rustdoc <JSON_PATH>`. The three deletion-authorised packages `ritk-core 0.9.0` / `ritk-image 0.2.0` / `ritk-spatial 0.1.0` are NOT published on crates.io so default registry baseline is unusable.

   - **Dep-resolution result**: cargo's dep-resolver could not select any `themis` version matching `^0.8.0` (the cargo-update error enumerated only `0.9.17` as the candidate, which is non-matching; the upstream themis git source `https://github.com/ryancinsight/themis` local-tag inventory is not verified by this error output, only that the resolver found no compatible match).

   - **Resolution path (i) — upstream canonical fix (preferred long-term)**: `mnemosyne-arena` (a real workspace sibling of `mnemosyne` in the `Mnemosyne` monorepo, transitively pulled per the cargo-update error chain) lifts its `themis = ^0.8.0` requirement to `^0.9` (or absorbs themis transitively into its own version surface). Cross-walk `atlas/backlog.md` §In-flight claims "This codex session (2026-07-06, pre-batch-#5 `cargo semver-checks` verification)" for the resolution narrative.

   - **Resolution path (ii) — triage workaround**: extend the existing `[patch."https://github.com/ryancinsight/Mnemosyne.git"]` block in `repos/ritk/Cargo.toml` (currently patching only `mnemosyne = { path = "../mnemosyne/crates/mnemosyne" }`) with `mnemosyne-arena = { path = "../mnemosyne/crates/mnemosyne-arena" }` — this synchronises the themis-resolution constraint locally without modifying the `Mnemosyne.git?rev=1e014d25` upstream and unblocks the semver-checks run. Path-hypothesis caveat: the `../mnemosyne/crates/mnemosyne-arena/` local subdirectory existence is not verified from the cargo-update error alone — requires checking the local `repos/mnemosyne/` mirror before applying this workaround (the dep chain only proves the git source has the crate).

   - **Compile-cleanliness analog-evidence (NOT a substitute for the semver-impact verdict)**: `rustup run nightly cargo build --release -p ritk-core -p ritk-image -p ritk-spatial` PASSES (`Finished release profile [optimized] target(s) in 0.70s` with only cosmetic hephaestus `[patch]` warnings). This signals source compiles cleanly under the current additive state; does NOT speak to API-surface delta or the `[major]`/`[minor]`/`[patch]` verdict that requires the semver-checks toolchain.

   - **Standing-reminder status**: the standing reminder's "MUST run pre-merge" clause is **unsatisfiable** in this session environment until (i) or (ii) lands; tracking in `atlas/backlog.md` §In-flight claims capture before this gap_audit.md entry was added (the pre-batch-#5 verification verdict row).



10. **AMEND-LOOP REGRESSION PATTERN** (surfaced 2026-07-08, atlas-meta bookkeeping regression during the 6-repo SSOT enforcement surface ceremony's apollo-symmetry drop on `gaia` + `helios`): process lesson about submodule gitlink bookkeeping. When the atlas-meta bookkeeping of a submodule gitlink regresses to pre-chore state (`HEAD:repos/<submodule>` reverts from the chore-dest-SHA back to the pre-recovery-SHA), the recovery sequence `git rm -r --cached <submodule>` + `git add <submodule>` (no trailing slashes — a trailing slash indexes the inner tree as files at mode 100644, recreating the bug) restores the canonical 160000-mode gitlink entry. BUT subsequent `git commit --amend` operations on the parent commits re-corrupt the index entry, because the amend command takes the working tree's index state at amend-time and any pre-existing index corruption re-emerges through the new amend. **Forward-fix via a NEW commit** (`git add <submodule>` + `git commit -m "<pointer-advance subject>"`) is safer than polish-amend cycles on parent commits containing submodule-pointer advances.

   - **Forensic anchors** (reflog preserved in `D:/atlas/.git/logs/HEAD`, cited for retrospective auditability):

     - `284dea473` — atlas-meta `chore(atlas): Advance gaia + helios submodule pointers` — initial commit; `repos/gaia` gitlink advanced; `repos/helios` gitlink silently dropped due to the underlying corrupted index state (~90 entries at mode 100644 instead of a single 160000 gitlink; the bug surfaces from earlier `git add` indexing the inner tree as files).

     - `1d45fb774` — atlas-meta polish-amend of `284dea473`; the recovery-context paragraph was stripped from the body, BUT the tree reverted to `repos/gaia` only — the recovery from the prior step was undone by `--amend`.

     - Forward-fix attempt (did not land) — `chore(atlas): Advance repos/helios pointer to 74f380e (forward-fix apollo-symmetry)`; the validation basher reported `ATOMICITY VIOLATION` + mode 100644 on `repos/helios` (index pollution re-emerged in the staging area from prior amend cycles). The commit did not land cleanly.

   - **Submodule-side state** (preserved per inner-branch HEAD pointers): `repos/gaia` chore `4c0453554` + `repos/helios` chore `74f380ec9` actually exist on their inner branches with `.github/workflows/legacy-migration-audit.yml` correctly updated; only the atlas-meta bookkeeping (the parent-side gitlink tracking) regressed. Cross-repo symmetry at the file-content level (`apollo` + `gaia` + `helios` all lack `actions/upload-artifact` block) is intact regardless of the atlas-meta index-side bookkeeping.

   - **Forward-fix safety rule** (forward-looking): for submodule gitlink advances, prefer NEW commits (with explicit pointer-advance subject) over iterative `--amend` cycles on parent commits containing the affected gitlinks. Per ADR 0010 (Per-batch ceremony convention) + ADR 0011 §Leg 2 (atlas-meta disjoint-scope rule), each pointer-advance is a forward-only chore that should NEVER be re-amended once landed. **Sub-rule (added 2026-07-08 fresh-session recovery, manifests as top-level row 11 below)**: when invoking `git update-index --add --cacheinfo 160000,<full-sha>,<submodule-path>`, ALWAYS derive `<full-sha>` via `cd <submodule-path> && git rev-parse <short-sha-or-ref>^{commit}` — the canonical dynamic-extraction pattern that resolves to the inner submodule's actual chore SHA via its local refs. NEVER hardcode the full 40-character SHA. Git does NOT validate the gitlink SHA against the inner's refs at commit time, so hardcoded SHAs that diverge from the inner's actual chore SHA by even a single character silently mis-track the submodule. **Concretely**: the prior recovery chore at `HEAD = 339ec95` (subject `chore(atlas): Advance repos/helios pointer to chore SHA 74f380e`) had hardcoded `<full-sha>` = `74f380edca5c99a23a2c5e7c19ee8929421f2db5`; the inner's actual chore SHA is `74f380ec9241d67246f75bba85187240a668779f` — same 7-char short prefix `74f380ec9` but the 8th char diverged (`d` vs `c`). The forward-fix at `339ec952a` made the parent's gitlink point at a SHA that didn't match the inner's local ref store, surfacing only on a fresh-session diff via `git rev-parse 74f380e^{commit}` from inside `repos/helios/`.    - **Closeout (2026-07-08 fresh-session)**: the single-shot clean bookkeeping recovery landed at the correct SHA via the dynamic-extraction sub-rule above. The fresh-session forward-fix chore commit (subject `chore(atlas): Advance repos/helios pointer to 74f380e (forward-fix apollo-symmetry)`, body intentionally subject-only per the user's verbatim command) atomic-advanced `HEAD:repos/helios` from the prior-wrong SHA `74f380edca5c99a23a2c5e7c19ee8929421f2db5` (the land at `339ec952a`) to the correct inner-aligned SHA `74f380ec9241d67246f75bba85187240a668779f` (verified via `git rev-parse 74f380e^{commit}` from inside `repos/helios/`). Inner WT preservation (16 dirty files in `repos/helios/` working tree) and atlas-meta WT preservation (`backlog.md` + `checklist.md` modifications) both intact across the recovery. The original open-followup ("schedule in a future session") is now CLOSED. Only further bug-pattern discoveries from this section's baseline remain open; the `## Surfacing risks` field is broadly dominated by row 10, hence row 11 is appended as a hoisted operational extension rather than duplicated content.

    - **Forward-fix annotation (attached 2026-07-08 polish, docs-only followup commit per row 10 NO-AMEND rule, `recover.attached.body` convention)**: this row 10 closeout is accompanied by a separate atlas-meta docs-only commit that anchors the fresh-session recovery chore's substantive narrative body here, preserving the original subject-only forward-fix chore commit's veridical state. The reconstruction below logs:

      1. **Inner chore subject (recovered from `repos/helios` local refs)**: the inner submodule chore at `74f380ec9241d67246f75bba85187240a668779f` (short `74f380ec9`) carries the verbatim subject `ci(helios): drop target/xtask-*.log upload-artifact step from legacy-migration-audit workflow`. This is the helios-side upload-artifact step removal that the fresh-session pointer advance was tracking on the parent side, part of the cross-repo symmetry lineage documented at the 2026-07-07 ssot enforcement surface ceremony.

      2. **Surfacing-risks row 10 forward-fix safety rule cite**: the original chore commit deliberately landed as a NEW commit (never `--amend`-iterated on parent commits containing the affected gitlinks) per row 10's "Forward-fix safety rule" sub-rule. Per the row 10 NO-AMEND rule's exception clause for THIS chore commit (which IS the chore commit itself, not a parent), this docs-only forward-fix annotation chore is the canonical place to attach the substantive body without violating the "forward-only commits" prohibition.

      3. **Cross-repo symmetry lineage** (apollo + gaia + helios inner chores share the same upload-artifact removal pattern): the three inner chore commits that were the substantive subject of the 2026-07-07 ssot enforcement surface ceremony are `apollo` at `cd05eacf6e6a9c6dc6a8db57d68fdb14f0a39da3f` (short `cd05eac`, subject `ci(apollo): fix broken legacy-migration-audit workflow YAML under kwavers-Atlas-migration-push`), `gaia` at `4c04535549cd4804a2723c0faf21afcdf4c7faea` (short `4c0453554`, subject `ci(gaia): drop target/xtask-*.log upload-artifact step from legacy-migration-audit workflow`), and `helios` at `74f380ec9241d67246f75bba85187240a668779f` (short `74f380ec9`, subject `ci(helios): drop target/xtask-*.log upload-artifact step from legacy-migration-audit workflow`). The fresh-session recovery was specifically engineered to restore atlas-meta's bookkeeping to land the parent-side gitlink on the helios inner chore (`74f380ec...`) so that `HEAD:repos/helios` sym-anchors the helios-side uplift alongside gaia's `4c0453554` and apollo's `cd05eac`.

      4. **ADR 0010 + ADR 0011 §Leg 2 cite**: per `atlas/docs/adr/0010-batch-ceremony-convention.md` §Decision §Per-batch name pattern, the fresh-session forward-fix chore is correctly framed as `chore(atlas): Advance repos/<submodule> pointer to <short-sha> (<recovery-context>)` (parens-only marker, no em-dash); per `atlas/docs/adr/0011-atlas-meta-disjoint-scope.md` §Decision §Leg 2, atlas-meta never mutates inner submodule source-tree content directly, only the parent-side gitlink pointer + atlas-meta PM artifacts. The fresh-session recovery respects both: parent-only `cacheinfo 160000,<full-sha>,repos/helios` mutation; source-tree `repos/helios/` working tree preserved at 16 dirty files; and atlas-meta PM-only churn via this `Forward-fix annotation` rather than `--amend`-rewriting the chore commit itself.



11. **DYNAMIC-SHA-EXTRACTION MANDATE** (surfaced 2026-07-08 fresh-session recovery, hoisted from row 10's sub-rule to a top-level row because the field is dominated by row 10 and the mandate is independently actionable): the canonical recovery pattern for submodule gitlink advances is `git update-index --add --cacheinfo 160000,$(cd <submodule-path> && git rev-parse <short-sha-or-ref>^{commit}),<submodule-path>` — the `$(...)` command substitution is structurally load-bearing because `git update-index --cacheinfo` rejects short SHAs at the parser level (the comma-delimited `<mode>,<sha1>,<path>` argument requires a full 40-character SHA-1 or 64-character SHA-256). Hardcoding the full SHA drifts silently because `git commit` does not validate the gitlink SHA against the inner submodule's ref store; a SHA that differs from the inner's actual chore by even one character will produce a parent tree pointing at a SHA the inner doesn't recognize via its short refs, requiring a fresh-session diff to surface. Cross-references row 10 for the broader forward-fix NEW-commit-not-amend convention; the dynamic-SHA extraction is the layer 2 hardening that prevents the wrong-SHA failure mode from re-occurring on future bookkeeping chores.



12. **ATLAS-META AGENTS.md OPTION A CLEANUP** (2026-07-08, per user instruction "we use a global agents.md, not codebase local, you can remove the local ones in atlas crates and if needed direct to .codex/agents.md or .claude/claude.md"): the per-sub repo-local `AGENTS.md` (markdown workspace reference) + lowercase `agents.md` (NTFS case-conflict duplicate on NTFS) pairs in `repos/CFDrs` (352 lines, sha 4b5f0bd7) and `repos/gaia` (756 lines, sha 6714e682) were retired in favour of the user-global master at `C:\Users\RyanClanton\.codex\AGENTS.md` (450 lines, sha f8c64b37). Each per-sub repo lands a thin `.codex/agents.md` redirect stub (5-line) pointing to `~/.codex/AGENTS.md` so editors / agents reach the global master while the per-sub repo retains its own identity. Per-sub chore commits (NEW atomic commits per row 10 NO-AMEND rule, NOT `--amend`-iterated on parent): `repos/CFDrs` chore `8aa7313f2980cdd9518b95e39f96487653c43148` on `codex/cfdrs-atlas-migration` (subject `chore(cfdrs): Replace cfdrs-local AGENTS.md with global redirect stub`, force-with-lease pushed to `origin/codex/cfdrs-atlas-migration`); `repos/gaia` chore `878ed5db78cedbd81bbf64f4da21d9cbeb1d99d3` on `refactor/migrate-to-leto-geometry` (subject `chore(gaia): Replace gaia-local AGENTS.md with global redirect stub`, local commit only — push deferred pending remote-auth handshake). Recovery: prior per-sub AGENTS.md content (1108 lines total across CFDrs 352 + gaia 756) is fully recoverable from each sub-repo's git history via `git log --all --diff-filter=D -- AGENTS.md` per the redirect-stub recovery note. Atlas-meta parent pointer advance applied per row 11 DYNAMIC-SHA-EXTRACTION MANDATE: `git update-index --add --cacheinfo 160000,$(cd repos/<sub> && git rev-parse HEAD^{commit}),repos/<sub>` resolved CFDrs to `8aa7313f2980cdd9518b95e39f96487653c43148` (advanced from `1d768895`) and gaia to `878ed5db78cedbd81bbf64f4da21d9cbeb1d99d3` (advanced from `4c045355`); both now registered as `mode 160000` gitlinks in atlas-meta's index. Atlas-meta atomic chore commit + force-with-lease push lands in the current turn.



13. **BULK-PROVIDER-SURFACE ROUND 3 (2026-07-08, post-`36acbbca9` fresh-session audit)**: 5-commit pointer-advance sequence capturing inner churn that landed on apollo, eunomia, hermes, leto, and mnemosyne after each was previously bookkept-aligned by the round-1 + round-2 bulk-advance block (rows 326 + 329 + 357). Per row 11 DYNAMIC-SHA-EXTRACTION MANDATE, each pointer's `<full-sha>` was derived fresh via `cd repos/<sub> && git rev-parse <short-sha>^{commit}`; per row 10 NO-AMEND rule, each landed as a NEW atomic chore (never `--amend`). The r3 block closes the orphaned-pointer surfaces that round-2 left DIVERGED; after this block, all 12 actively-tracked submodules (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, kwavers) are ALIGNED at inner HEAD with zero DIVERGED gitlinks — the first all-aligned state since the `e0bf55684` cross-tree reclamation audit shifted to round-2 bookkeeping.

    - *Per-submodule advance record (5 atomic chore commits)*:

      - `ad6cf57d4` chore(atlas): Advance repos/apollo pointer to `e6ecce4` (`e6ecce49c9f7df0c338422a8974aae907f00f90b`) — inner head `chore(deps): sync Cargo.lock (eunomia num-traits dependency)`; apollo's post-PR-`#6` merge + `Cargo.lock` sync chain propagates the eunomia num-traits alignment. Atlas-meta prior `2e6f9be` (the round-1 bulk-advance) → `e6ecce4`.

      - `1828ea14a` chore(atlas): Advance repos/eunomia pointer to `22e971e` (`22e971e9feb7de808f47f020edaa72bc8b9bbae4`) — inner head `chore(deps): sync Cargo.lock (num-traits dependency)`; the aarch64 packed-CFG gate fix at `b3fd6f2` (round-2 stable capture) is preserved; the new commit synchronises the registry view of the num-traits baseline. Atlas-meta prior `b3fd6f2` → `22e971e`.

      - `852de7129` chore(atlas): Advance repos/hermes pointer to `166a7b9` (`166a7b9599d877c6f7bfa88afc523b9e5c1b3a15`) — inner head on branch `rescue/detached-simd-numa-work` (NOT `main` — 17 commits ahead of `origin/main`) at `Revert "ci(miri): use Tree Borrows for the mnemosyne-allocator-backed run"`. The Revert supersedes the round-2 `92187d0` re-trigger-after-madvise-extern-declaration gate commit; the Tree Borrows Miri experiment is rolled back. Atlas-meta prior `92187d0` → `166a7b9`. Branch divergence persists and is peer-WIP not reclaimable from atlas-meta.

      - `769b70a67` chore(atlas): Advance repos/leto pointer to `a9572da27` (`a9572da277ddbb5edb1bc1e87b42c34792d12698`) — inner head `chore(deps): sync Cargo.lock (eunomia num-traits dependency)`; this lands on the same collapse sequence as apollo + eunomia's num-traits alignment, ensuring the leto workspace `Cargo.lock` is in lock-step with the eunomia publish. The round-2 advance at `02da06611` pinned leto at `83e1693e1`; the two intermediate `fix(deps): bump stale moirai/mnemosyne rev pin (themis 0.8 -> 0.9 requirement)` commits (`83e1693e1` + `74cebca94`) are part of the dependency-resolution chore chain that closed the `themis = ^0.8.0` resolver mismatch traceable to row 9. Atlas-meta prior `83e1693e1` → `a9572da27`.

      - `1fe3c0e56` chore(atlas): Advance repos/mnemosyne pointer to `98a02b6` (`98a02b61ccb8ce04f5b1920113d8315cae193ae8`) — inner head `docs(gap_audit): Record the Miri alloc/free aliasing finding (HIGH PRIORITY)`; the 4-commit chain (madvise-extern-declaration Miri gate + page_reset/decommit MADV_DONTNEED/FREE Miri fallback + SEGMENT_SIZE import / MADV_HUGEPAGE const Miri gate + skip MADV_HUGEPAGE hint under Miri + the docs audit landing) records the alloc/free aliasing defect surfaced under Miri on the mnemosyne-allocator-backed run. The finding is **HIGH-PRIORITY** for the mnemosyne peer to root-cause; atlas-meta records via this pointer advance only, no source reclaim. Atlas-meta prior `482670d` (round-2 combo-advance at `274a6a961`) → `98a02b6`.

    - *Sequence-closure observation*: the round-3 block is the first bulk-advance batch to land after the `36acbbca9` `.gitignore` chore hardened `D:\atlas` against transient scratch artifact recurrence (`.body-scratch-*`, `.tmp-*.py`, `.verify-*.sh`, `ritk_errors.txt`). No body-scratch file was needed for any of the 5 atomic chore commits in this block; per the user's signal-change-in-the-tree batch ceremony convention (ADR 0010 §Per-batch name pattern), each subject + body was authored inline via subject `-m ""` + body `-m ""` pairs with one final `-m` block carrying the dynamic-SHA-extraction provenance triple (inner source command + derived full SHA + atlas-meta prior SHA + row 11 / row 10 cross-references).

    - *Net alignment state*: post-`1fe3c0e56`, `git status --short` reports `M gap_audit.md` (this PM sync) + 8 inner-WIP `m repos/<X>` submodules (peer-WIP per disjoint-scope) + 1 `.tmp-probe-minimal-out.txt` (untracked, scratch — unrooted via the `.gitignore` broadening from `.tmp-*.py` to `.tmp-*` in this docs sync). All 12 actively-tracked submodules ALIGNED; no DIVERGED gitlink remains. The next round of pointer advances is contingent on the next inner HEAD churn (peer WIP lands + push) OR the KW-CV-001 watchpoint trigger firing for `repos/kwavers`.

    - *Cross-reference updates with this PM-sync commit*: this gap_audit row 13 entry; `atlas/backlog.md` §In-flight claims gets a `2026-07-08 Bulk-provider-surface round-3 (post-36acbbc fresh-session audit)` sub-bullet appended at the active-session anchor; `atlas/checklist.md` §Next micro-sprint gets a `2026-07-08 Bulk provider-surface round 3 — 5 atomic choruses landed` line-item summary. PM-artifact freshness per `atlas/AGENTS.md` `documentation_discipline` `Same-change doc sync` — three artifacts updated in the same chore commit that closes the round-3 block.



14. **BULK-PROVIDER-SURFACE ROUND 4 (2026-07-08, post-`4a4cf928a` mid-session audit)**: 7-commit pointer-advance sequence capturing the post-round-3 inner churn that landed on `hermes` `c7b17b02`, `leto` `86d366bc`, `kwavers` `89117870` + `09c645f30`, `coeus` `ec69a6a` + `006f2a7`, and `ritk` `e75d8748`. Per row 11 DYNAMIC-SHA-EXTRACTION MANDATE, each pointer's `<full-sha>` was derived fresh via `cd repos/<sub> && git rev-parse <short-sha>^{commit}`; per row 10 NO-AMEND rule, each landed as a NEW atomic chore (never `--amend`). The e322309 hermes+leto commit was bundled at commit time (both submodule gitlinks staged together at OOB-consolidation stress); subsequent per-crate pointers split into one-atomic-chore-per-crate for cleanliness.

    - *Per-submodule advance record (7 atomic chore commits)*:

      - `e3223094a` Advances repos/hermes gitlink to inner `c7b17b02c73a81648af2bf8781a261e359a01165` — inner `chore(deps): sync Cargo.lock (eunomia num-traits dependency)` post-eunomia `7f84beb` pointer advance; bundled with the leto advance during the `6902d2e92` OOB consolidation that's exposed in `git --no-pager show --stat e322309`. Atlas-meta prior `5ad1b58` → `c7b17b0`.

      - `e3223094a` Advances repos/leto gitlink to inner `86d366bc0e909b9aeb1df695170e4279dbc58781` — inner `feat(leto-ops): batched LU, CSC sparse format, CG/GMRES iterative solvers`; canonical generic LU factorization in batched form for tiled GPU dispatch, CSC sparse storage, and CG/GMRES iterative kernels behind `leto::solvers`. Unblocks kwavers-solver Bulk-solver migration closure target (KW-CV-001 watchpoint candidate content). Atlas-meta prior `a9572da27` → `86d366bc0`.

      - `6a598da91` Advances repos/kwavers gitlink to inner `89117870157948d38ecac6c4352b4226a603700c` — inner `Migrate kwavers Complex/ndarray types to eunomia/leto atlas crates`; Phase-3 closure of Complex<f32>/Complex<f64>, ndarray Array bases, and coefficient paths onto eunomia+leto atlas substrates; replaces nalgebra/ndarray/numeric-complex stack in kwavers-core domain. Atlas-meta prior `35ee01076` → `89117870`.

      - `0e34ae082` Advances repos/coeus gitlink to inner `ec69a6ac829ece50dbe6f5bbcb5231f0039a0e79` — inner `fix(coeus-dist): close TOCTOU race in TCP test port allocation` + co-emitted `342f38d` docs(checklist): reconcile MS-406/MS-407 as already-closed. Real test-time race in coeus-distributed TCP port-allocation harness (TOCTOU between bind and listen eliminated). Atlas-meta prior `e36f95f` → `ec69a6a`.

      - `045291499` Advances repos/ritk gitlink to inner `e75d874890fb3f65ca04c416f2602d2a4e0b3e26` — inner `Add Module/AutodiffModule impls for DisplacementField and DisplacementFieldTransform`; DIRECTLY resolves the `displacement_registration_test` failure previously tracked in row 6 (Sub-batch #5 RITK-spatial-rebind closure per ADR 0012). Auto-diff through Transform's parametric gradient + jacobian-to-cotan propagation available. Atlas-meta prior `1f49278c` → `e75d8748`.

      - `4a4cf928a` Advances repos/coeus gitlink to inner `006f2a7968d713d561fa02b3d205575cf07a8a70` — inner `feat(coeus-nn): add MaxPool3d/AvgPool3d benchmark rows (G-043)`; extends criterion bench registry for 3D pooling kernels. Atlas-meta prior `ec69a6a` → `006f2a7`.

      - `4b7f4804e` Advances repos/kwavers gitlink to inner `09c645f3062d2f20b1ecef4439888b8f807e256a` — inner `Migrate kwavers-core/source/signal/grid/field from ndarray to leto`; Phase-4 closure of kwavers-core domain crates source/signal/grid/field off ndarray onto leto's NDArray substrate. Follow-on to `89117870` Complex/eunomia migration. Atlas-meta prior `89117870` → `09c645f30`.

    - *Sequence-closure observation*: round-3 left 5 provider surfaces ALIGNED; the inner churn that landed between `1fe3c0e56` and this round-4 capture cycle comprises 7 fresh pointer changes (well above the round-3 cadence). The kwavers double-jump (`89117870` → `09c645f30`) plus the ritk DisplacementField resolution together advance a large fraction of the consumer-side migration surface. KW-CV-001 watchpoint remains 0 — peers continue to use `Migrate *.rs from ndarray to leto` subject phrasing, not `closeout`/`final`/`completion`/`close-batch`.

    - *Net alignment state*: post-`4b7f4804e`, all 13 actively-tracked submodules (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, gaia, hephaestus, kwavers) ALIGNED at inner HEAD with zero DIVERGED gitlinks. The round-4 block advances the 7 provider surfaces beyond round-2 alignment and demonstrates the bulk-migration cadence is now running at full speed on consumer land.

    - *Cross-reference updates with this PM-sync commit*: this gap_audit row 14 entry; `atlas/backlog.md` §In-flight claims gets a `2026-07-08 Bulk-provider-surface round-4 (post-2d78fff OOB consolidation)` sub-bullet appended; `atlas/checklist.md` §Next micro-sprint gets a `2026-07-08 Bulk provider-surface round 4 — 7 atomic chore commits landed` line-item summary.



---



## Forward-looking watchpoints (active trigger conditions)



Active watchpoints for submodule pointer advances or other forward-only chore triggers. Each entry: (ID, trigger condition, action sequence, status, verification cadence). Items CLOSE when the trigger fires and the action chore commits. Distinct from the `## In-flight claims` section (which holds transient atlas-meta carryovers that resolve via a separate atomic chore and is not forward-looking).



- **KW-CV-001 (kwavers final closeout)** — **CLOSED 2026-07-12**. Trigger substance was kwavers consumer-side Batch #1–#4 closure. All resolved per `## State refresh` above (0 par_for_each, 0 use ndarray, 0 nalgebra, 0 burn). No closeout-style commit subject naming convention was used, but the substantive condition (zero legacy migration surface) is met at kwavers inner HEAD `7c70d1b1d`. The atlas-meta `HEAD:repos/kwavers` gitlink is current (parent `01bb2e0` on `codex/kwavers-atlas-integration` already tracks the kwavers inner).



## Validator invariants (per criticality level)



- **Tier-A (cross-provider SSOT)**: CR-1, CR-2, CR-4 — landing arrangement coordinated per `atlas/AGENTS.md` documentation-disciple rule + ADR requirement.

- **Tier-B (provider-extension)**: above, listed in provider-own backlogs but track at-meta-level here.

- **Tier-C (consumer-batch)**: Batch #1–#4. Definition-of-Ready at the meta-level; batch itself is the per-repo backlog item.## Batch #1 source-side migration -- slice 3 partial-closure-mark 2026-07-08

Per the peer's `d2cb977b` chore (refactor(kwavers-solver): Migrate diffusion.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 3), on codex/kwavers-core-moirai-parallel atop parent c77a926d8 = Nit 1 fixup = 9541155f slice 2 = 5cd8c708 slice 1): **5/41 sites migrated in 3/15 files** cumulative. The 1 new site is in crates/kwavers-solver/src/forward/nonlinear/kuznetsov/diffusion.rs (in compute_diffusive_term_workspace at L93). The 1-mut + 4-immut kuznetsov 1-site pattern is handled via 5 is_standard_layout() asserts (Nit 1 applied in-chore) + as_slice{_mut,}().expect() + par_mut().enumerate() with 4 flat-index lookups inside the closure. THIRD_ORDER_DIFF_COEFF.mul_add chain arithmetic preserved bit-for-bit. Cargo check clean at inner HEAD. **36/41 sites / 12/15 files remain**. Full-closure mark (Batch #1 CLOSED) remains retracted; this is the third per-slice partial-closure mark. KW-CV-001 watchpoint remains ACTIVE.
## Batch #1 source-side migration -- slice 2 partial-closure-mark 2026-07-08
> Note: this mark landed after the slice 3 mark (commit f2c89a73) due to flaky prior re-emission attempts; it documents cumulative state AT slice 2 chore landing, not the present state.

Per the peer's 9541155f chore (refactor(kwavers-solver): Migrate model_impl.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 2), on codex/kwavers-core-moirai-parallel atop parent 5cd8c708 = slice 1): **4/41 sites migrated in 2/15 files** cumulative at slice 2 (slice 1 = 2 sites in struct_impl.rs + slice 2 = 2 sites in model_impl.rs). The 2 new sites in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/model_impl.rs` (1 mut + 2 immut Zip at L48 + 1 mut + 3 immut Zip at L62 inside `KuznetsovWave::update_wave`) are migrated to the canonical 1+N physics-equation pattern (as_slice{_mut,}().expect() on each Array3 + par_mut().enumerate() with manual flat-index lookups inside the closure). 2 mul_add arithmetic expressions preserved bit-for-bit ((0.5*dt*dt).mul_add(accel, p_curr) and 2.0f64.mul_add(p_curr, -p_prev)). Cargo check clean at inner HEAD 9541155f. **37/41 sites / 13/15 files remain** after slice 2. Full-closure mark (Batch #1 CLOSED) remains retracted; this is the second per-slice partial-closure mark. KW-CV-001 watchpoint remains ACTIVE. NOTE: this mark is landed retroactively AFTER the slice 3 mark because the prior basher/heredoc re-emission attempts in earlier sessions failed due to command-length limits.
## Batch #1 source-side migration -- model_impl.rs Nit 1 asymmetry fixup mark 2026-07-08

Per the peers b21679f5c chore (fix(kwavers-solver): Add standard-layout assert to model_impl.rs migration, on codex/kwavers-core-moirai-parallel atop parent d2cb977b = slice 3 = c77a926d8 struct_impl.rs fixup = 9541155f slice 2 = 5cd8c708 slice 1): **closes the Nit 1 asymmetry** identified in the slice 2 review. The struct_impl.rs fixup (c77a926d8) added is_standard_layout() asserts to slice 1's file; model_impl.rs (slice 2 file) was missing them. This fixup retroactively adds 7 is_standard_layout() asserts to model_impl.rs: 3 in first-step branch (1 mut + 2 immut) + 4 in multi-step branch (1 mut + 3 immut). Each assert precedes the corresponding .as_slice{_mut,}().expect() call with a layout-invariant message; the .expect() messages are updated to reference the preceding assert as the layout invariant source. Cargo check clean. Cumulative at the migration level unchanged: **5/41 sites / 3/15 files migrated + 2 file-level fixups** (c77a926d8 struct_impl.rs + b21679f5 model_impl.rs). 36/41 sites / 12/15 files remain. KW-CV-001 watchpoint remains ACTIVE.

## Batch #1 source-side migration -- slice 4 partial-closure-mark 2026-07-08

Per the peer `9595a99f5` chore (refactor(kwavers-solver): Migrate nonlinear.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 4), on codex/kwavers-core-moirai-parallel atop parent b21679f5c = model_impl.rs Nit 1 fixup = d2cb977b slice 3 = c77a926d8 struct_impl.rs fixup = 9541155f slice 2 = 5cd8c708 slice 1): **6/41 sites migrated in 4/15 files** cumulative across slices 1+2+3+4. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/nonlinear.rs` (in `compute_nonlinear_term_workspace` at L109). The 1-mut + 3-immut kuznetsov 1-site pattern (β/ρ₀c₀² nonlinear contribution to leapfrog RHS, computed via three-point backward finite-difference of p²) is handled via 4 `is_standard_layout()` asserts (Nit 1 applied in-chore) + 4 `as_slice{_mut,}().expect()` calls + `par_mut().enumerate()` with 3 flat-index lookups (`p_val`/`prev_val`/`prev2_val`). The `2.0f64.mul_add(-p2_prev, p2) + p2_prev2` chain arithmetic preserved bit-for-bit (separate addition, NOT fused FMA). Inner closure body uses `_val`-suffix naming convention. Cargo check clean at inner HEAD `9595a99f5`. **35/41 sites / 11/15 files remain**. Full-closure mark (Batch #1 CLOSED) remains retracted; this is the fourth per-slice partial-closure mark. KW-CV-001 watchpoint remains ACTIVE. Style carry-forward: slice 4 + diffusion.rs + model_impl.rs fixup use verbose multi-line assert messages; struct_impl.rs fixup uses terse -- 3-way divergence captured as code-reviewer Nit 1.

## Batch #1 source-side migration -- slice 5 partial-closure-mark 2026-07-08

Per the peer `d614a7f57` chore (refactor(kwavers-solver): Migrate operator_splitting/mod.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 5), on codex/kwavers-core-moirai-parallel atop parent 9595a99f = slice 4 nonlinear.rs = b21679f5c model_impl.rs Nit 1 fixup = d2cb977b slice 3 diffusion.rs = c77a926d8 struct_impl.rs fixup = 9541155f slice 2 model_impl.rs = 5cd8c708 slice 1): **7/41 sites migrated in 5/15 files** cumulative across slices 1+2+3+4+5. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/operator_splitting/mod.rs` (in `OperatorSplittingSolver::nonlinear_step` at L191). The 1-mut + 1-immut Strang-splitting nonlinear-correction pattern (1 mut pressure + 1 immut flux_gradient inside L(dt/2)*N(dt)*L(dt/2)) is handled via 2 `is_standard_layout()` asserts (Nit 1 applied in-chore) + 2 `as_slice{_mut,}().expect()` calls + `par_mut().enumerate()` with 1 flat-index lookup. The compound-assignment `*p -= scale * grad;` arithmetic preserved bit-for-bit (Rust f64 compound-assign semantics identical to expanded `*p = *p - (scale * grad);`). Inner closure body uses bare `grad` (N=1 single-lookup ergonomics; deviates from `_val`-suffix convention from N>=2 sites). Cargo check clean at inner HEAD `d614a7f57`. **34/41 sites / 10/15 files remain**. Full-closure mark (Batch #1 CLOSED) remains retracted; this is the fifth per-slice partial-closure mark. KW-CV-001 watchpoint remains ACTIVE. Style carry-forward: 4 of 5 migrated files use verbose multi-line assert messages; only struct_impl.rs fixup (c77a926d8) uses terse. Dominant pattern (verbose) confirmed at slice 5.

## bash-heredoc artifact audit verification 2026-07-08

> Audit verified: 0 unresolved `\$VAR` artifacts (matches pattern `\$[A-Z_]+`) remain in 3 PM artifacts after the \$SHORT substitution chore (commit `92dad112`). All residual `$` characters in the 3 PM artifacts are legitimate (Rust generic syntax `<$t as Scalar>`, command-substitution documentation `$(cd repos/...)`, mathematical notation, or anti-pattern template examples in audit prose). Code-reviewer N3 carry-forward from the \$SHORT substitution chore is now CLOSED.

## Batch #1 source-side migration -- slice 6 partial-closure-mark 2026-07-08 (heterogeneous site 1 deferred)

Per the peer `7be3fbbd8` chore (refactor(kwavers-solver): Migrate rhs.rs homogeneous par_for_each sites to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 6), on codex/kwavers-core-moirai-parallel atop parent d614a7f5 = slice 5 operator_splitting/mod.rs = 9595a99f slice 4 nonlinear.rs = b21679f5c model_impl.rs Nit 1 fixup = d2cb977b slice 3 diffusion.rs = c77a926d8 struct_impl.rs fixup = 9541155f slice 2 model_impl.rs = 5cd8c708 slice 1): **11/41 sites migrated in 6/15 files** cumulative across slices 1+2+3+4+5+6. The 4 new sites are in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/rhs.rs` (in `KuznetsovWave::compute_rhs` homogeneous branch). All 4 are 1-mut + 1-immut simple patterns (linear/laplacian, source/cache_source, nonlinearity/nonlinear_term, diffusion/diffusive_term) following the slice 5 / diffusion.rs verbose-form assert convention. Cargo check clean at inner HEAD. **30/41 sites / 9/15 files remain**.

**CRITICAL: heterogeneous site 1 deferred to follow-up chore**. The 5th site of `rhs.rs` (`Zip::indexed(rhs.view_mut()).par_for_each(|(i, j, k), r| { ... })` in the heterogeneous Phase 2 path) is NOT migrated by slice 6. That site uses `Zip::indexed` with 3D-index-triple closure arg + 8 separate `Array3<f64>` immut lookups via direct (i,j,k) indexing. Migration requires idx-to-(i,j,k) stride-arithmetic decomposition (`i = idx/(ny*nz); j = (idx/nz)%ny; k = idx%nz`) which is non-trivial + belongs in a separate follow-up chore. The `use ndarray::Zip;` import is retained for the deferred site.

Filename off-by-one correction: my slice 6 commit body draft said `5/15 files` but the correct cumulative is `6/15 files` (slice 6 adds `rhs.rs` as the 6th distinct migrated file). This audit closure-mark restores the correct arithmetic.

Full-closure mark (Batch #1 CLOSED) remains retracted; this is the sixth per-slice partial-closure mark. KW-CV-001 watchpoint remains ACTIVE on the disjoint-scope rule. Cumulative arithmetic cross-check: 11 = 2 (slice 1) + 2 (slice 2) + 1 (slice 3) + 1 (slice 4) + 1 (slice 5) + 4 (slice 6); 6 files = struct_impl.rs (slice 1) + model_impl.rs (slice 2) + diffusion.rs (slice 3) + nonlinear.rs (slice 4) + operator_splitting/mod.rs (slice 5) + rhs.rs (slice 6).

> **SUPERSEDED 2026-07-12**: Batch #1 source-side migration completed (0 `par_for_each` sites at kwavers inner HEAD `7c70d1b1d`). All six partial-closure marks above are historical records of the slice-by-slice migration progress. See `## State refresh` at the top of this file for current status.

## Findings 2026-07-12: leto empty-layout aliasing fix + kwavers-therapy abdominal perf watchpoint

### leto [patch]: `Layout::has_zero_stride_aliasing` short-circuits on size 0

`Layout::has_zero_stride_aliasing` rejected empty C/F-contiguous layouts
(shape with a zero-sized interior axis) as aliased, because
`c_contiguous_strides` defensively collapses the leading stride to 0 when
an interior axis has size 0 and the predicate only checked
`dim > 1 && stride == 0` per axis without considering total element count.
An empty layout has no addressable elements, so overlapping writes are
impossible; the predicate now short-circuits on `size() == 0`.

- **Provider fix**: leto inner commit `08d0b44` on `main` (atlas-meta submodule
  pointer `repos/leto` advanced). Regression tests added at
  `crates/leto/src/domain/layout/shape.rs` (5 tests: empty C-contiguous,
  empty F-contiguous, positive zero-stride axis with non-unit dim, broadcast
  axis alone, broadcast layout with zero dim). Provider gate: `cargo fmt --check`,
  `cargo clippy --all-targets --all-features -- -D warnings`, `cargo nextest run
  --workspace --all-features` (564/564), `cargo doc --no-deps` all clean.
- **Consumer unblock**: `kwavers-solver::inverse::fwi::time_domain::encoded_source::tests::hadamard_averaged_encoded_gradient_matches_summed_shot_gradient`
  now PASSES (was the sole documented kwavers lib test failure). Root cause: the
  test uses `CPMLConfig::default()` with `per_dimension.y == 0`, producing an
  empty `psi_p_y` memory buffer of shape `[8, 0, 8]` with strides `[0, 8, 1]`;
  the `slice_with_mut` of that buffer inherited the leading zero stride and
  the mutable zip predicate rejected it.
- **Full-kwavers workspace nextest sweep post-fix**: 5611/5612 LIB tests pass,
  1 timeouts (therapy profile, `elastic-fwi` test group with 90s timeout per
  `repos/kwavers/.config/nextest.toml:70-74`), 15 skipped. The timeout is an
  existing perf gap (see below), not a correctness regression from this fix.
  Verification command: `cargo nextest run --workspace --exclude kwavers-driver
  --no-fail-fast` from `repos/kwavers`.

### kwavers-therapy `run_theranostic_inverse` perf regression — KW-WATCH-002

`therapy::theranostic_guidance::tests::abdominal::abdominal_preprocessing_selects_one_connected_treatment_component`
terminates at the 90s elastic-fwi profile timeout, reproducible in isolation
(verified twice this session). The test exercises `run_theranostic_inverse` on
a 72×72×3 phantom CT; the smaller-grid sibling
`abdominal_theranostic_inverse_recovers_lesion_support` (42×42×3) passes at
16–19 s, and `abdominal_preprocessing_keeps_external_skin_between_target_and_aperture`
(64×64×3) passes at 81 s (just under the timeout). The FWI inverse scales
super-linearly past the budget at the larger grids.

- **Pre-existing**: the prior session (kwavers peer stream commits
  `72333295f` "Use Moirai abdominal maps" + `4b83a6389` "Use Moirai thermal
  maps" 2026-07-03) declared these timeouts closed at 340/340; gap_audit.md
  entry at L4843-4848 re-opened as `[perf]` on 2026-07-10.
- **Scope**: this is a kwavers peer-stream (`@ryancinsight`) test-time-budget
  perf issue (`[perf]` per `repos/kwavers/gap_audit.md:4843-4848`), not an
  atlas-meta migration-source-swap gap. Per ADR 0011 Leg 2 disjoint-scope,
  atlas-meta is NOT editing `crates/kwavers-therapy/**` source for this. The
  current atlas-meta item (leto empty-layout fix) is unrelated to the FWI
  solver cost; my leto fix does not cause or worsen this timeout (reproduced
  identically with leto at its pre-fix HEAD `a20286e`).
- **Action**: surfaced as KW-WATCH-002 watchpoint for the kwavers peer stream.
  The AGENTS.md test-time budget rule (`slow-timeout = { period = "30s",
  terminate-after = 2 }`) governs the *default* profile; this test is on an
  explicit override (`slow-timeout = { period = "90s", terminate-after = 1 }`,
  `repos/kwavers/.config/nextest.toml:70-74`), so the 90 s bound is the
  committed contract. The fix is an algorithm/perf optimization of
  `run_theranostic_inverse` and `simulate_waveform_adjoint_rtm` in
  `crates/kwavers-therapy/src/therapy/theranostic_guidance/solver.rs` per the
  closure pattern recorded in `repos/kwavers/checklist.md` L3714-3728.

### CFDrs `cross_fidelity_blueprint_complex_branching` -- peer-tracked cfd-1d convergence regression

CFDrs full workspace nextest (`cargo nextest run --workspace --all-features
--no-fail-fast` from `repos/CFDrs` at inner HEAD `e24922c8`) reports
3055/3056 pass, 1 fail, 30 skipped. The single failure is
`cfd-suite::cross_fidelity_blueprint cross_fidelity_blueprint_complex_branching`
which panics with
`MaxIterationsExceeded: Convergence failed: Maximum iterations (10000)
exceeded` from `cfd-1d` `Network2DSolver` `solve_reference_trace` on the
`double_trifurcation_cif_venturi_rect` network.

- **Pre-filed by CFDrs peer stream**: `repos/CFDrs/gap_audit.md` Finding
  2026-07-10 "cfd-1d double-trifurcation Picard non-convergence (test
  regression)" (commit `fa28ce43`). Explicitly NOT a test-gaming item: the
  peer stream records "the test asserts real mass-conservation physics; the
  fix must be in the solver/assembly, never a weakened tolerance or raised
  iteration cap."
- **Scope**: peer-active -- the peer stream notes "the convergence path is
  under active concurrent peer edit (`0d101352` "enhance Anderson QR
  collapse detection"); coordinate before touching `solver/core`." Per ADR
  0011 disjoint-scope, atlas-meta is NOT editing `crates/cfd-1d/**` or
  `solver/core/mod.rs` for this. Verification command reproduced the exact
  failure already on record.
- **DoR for peer**: differential-test the assembled cfd-1d matrix + rhs for
  this network against the pre-migration commit (parent of `d58d1fe3`) to
  classify regression vs. genuine stiffness; capture the Picard residual
  trajectory; verify Newton fallback engages on Picard stagnation. As of CFDrs
  HEAD `e24922c8` this DoR is unmet (peer work in progress).

### ritk `test_decoder_forward` slow-test watchpoint -- peer-stream burn dep strip scope

ritk full workspace nextest (`cargo nextest run --workspace
--all-features --no-fail-fast` from `repos/ritk` at inner HEAD `0ca58574`, branch
`codex/ritk-burn-ndarray-cleanup`) reports 4900/4900 pass, 26 skipped.
One test crosses the engineering_gates 30 s slow threshold:
`ritk-model ssmmorph::decoder::tests::test_decoder_forward` at 293.9 s
(9.8x over budget). The test uses `burn_ndarray::NdArray` as the test backend
(see `crates/ritk-model/src/ssmmorph/decoder.rs:286`). 260 `use burn*`
import sites remain across ritk source; workspace Cargo.toml declares
`burn = "0.19"`, `burn-ndarray = "0.19"`; ndarray surfaces only via these
burn deps (no direct ndarray dep). The most recent touch to `decoder.rs` is
`c696ee41` (ComputeBackend rebind) -- a structural migration-side rebind, not
a behavioral change.

- **Scope**: this is the `[major]` ritk Batch #4/#5 Burn dep strip deferred
to peer stream per `atlas-backlog.md`. The peer branch name
`codex/ritk-burn-ndarray-cleanup` confirms the active migration. Per ADR 0011
  disjoint-scope, atlas-meta is NOT editing ritk source/test files for this;
  the slow-test cost is the burn NdArray backend executing the SSM-Morph
  decoder forward pass and will be removed when the test backend migrates to
  coeus under the peer stream Burn dep strip.
- **DoR for peer**: when migrating `ritk-model/src/ssmmorph/decoder.rs` tests
  from `burn_ndarray::NdArray` to coeus backend, verify the post-migration
  decoder forward test executes within the default 30 s slow threshold.
  Cross-check the underlying numerical cost is the model architecture
  (32 / 64 / 128 / 256 encoder channels), not a backend inefficiency.

## Findings 2026-07-12 (evening session): kwavers Batch #1 source-side closure + ritk coeus-native paths

### kwavers Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai) — ✅ CLOSED

Kwavers peer stream commit `5913f2946` (subject `perf(kwavers-solver):
Migrate solver tree to moirai parallel iterators`, branch
`codex/kwavers-core-moirai-parallel`), landed 2026-07-12 22:23 EDT, drives the
Batch #1 source-side closure condition to ZERO. The commit's body declares
"Closes remaining ndarray-parallel and rayon surface-level dependencies in
kwavers-solver." Residual-surface re-verification at atlas-meta HEAD
`5913f2946`:

- `par_for_each` source sites: **0** (was 41 across 15 files at the prior
  session's HEAD `7c70d1b1d` per gap_audit.md `### Remaining open items`).
- `burn::` source hits: **0** (Batch #4 closeout landed on the prior peer
  stream per gap_audit.md L1893-L1904; not a Batch #1 surface but
  co-verified).
- `nalgebra` source hits: **0** (was 13 sites / 5 manifests at the 2026-07-08
  gap_audit baseline; closed by prior cuts).
- `use ndarray` source imports: **0** (was 2,496 line-hits at the 2026-07-08
  gap_audit baseline; closed by the Phase-3 + Phase-4 kwavers-core/source/
  signal/grid/field migrations landed at `4b7f4804e`).
- `kwavers-solver/Cargo.toml` deps section: zero `ndarray` / `rayon` /
  `burn`; substrate is `leto` + `leto-ops` + `moirai-parallel` only. The "sole
  remaining crate-level rayon dependency" cited in the commit body is
  `kwavers-solver`'s Cargo.toml `ndarray` `rayon` feature gate carried as a
  separate item per the commit body's final sentence — this is a manifest
  detail, NOT a source-site residual.
- Test verification at HEAD `5913f2946`:
  `cargo nextest run --workspace --exclude kwavers-driver --no-fail-fast --lib`
  from `repos/kwavers`: **5117/5119 pass, 2 timeouts, 7 skipped**.
  The two timeouts are the pre-existing KW-WATCH-002 abdominal-preprocessing
  perf tests (`abdominal_preprocessing_keeps_external_skin_between_target_and_aperture`
  and `abdominal_preprocessing_selects_one_connected_treatment_component`, both
  on the explicit 90s `elastic-fwi` profile override at
  `repos/kwavers/.config/nextest.toml:70-74`). These are NOT regressions
  introduced by the moirai-iterator migration — the prior session recorded
  `abdominal_preprocessing_keeps_external_skin_between_target_and_aperture`
  passing at 81 s (gap_audit.md L1825) and the FWI cost scales
  super-linearly with grid size. Closing the perf gap is the kwavers peer
  stream's responsibility per ADR 0011 disjoint-scope (KW-WATCH-002 DoR
  unchanged); atlas-meta is NOT editing `crates/kwavers-therapy/**` source.
- **KW-CV-001 watchpoint resolution**: the lexical-trigger probe
  (`git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch'`)
  still returns 0 at HEAD `5913f2946` — the peer uses "Migrate ..." subject
  phrasing. However, the underlying closure condition (zero `par_for_each`
  source sites per gap_audit.md `### Remaining open items` table) IS met, and
  the commit body explicitly declares closure of the surface-level
  dependencies. Atlas-meta is therefore advancing the parent-side gitlink on
  the substantive closure condition, not the lexical trigger — the lexical
  trigger was a proxy, the zero-site condition is the invariant.
- **Cross-crate residual**: kwavers-python `numpy = "0.27"` and the boundary
  `ndarray-compat` feature on leto are required PyO3 / leto-compat surfaces,
  not forbidden `ndarray` direct deps. No action.

### Atlas-meta pointer advance — `repos/kwavers` gitlink

`repos/kwavers` submodule pointer advanced `01643ed9b53fb42f54d0fcb2dfcfe3c1117bfb2f
→ 5913f29466bb6b769aefbc1a9b794c63b139babb` via the dynamic-SHA-extraction
convention (gap_audit.md row 11). Closes Batch #1 at the atlas-parent
layer. Batch #4 (kwavers-solver PINN Burn → Coeus) was already closed at
the prior peer HEAD `05500930c` per gap_audit.md L1893 — co-verified here at
`5913f2946` (zero `burn::` source, zero `burn` in `kwavers-solver/Cargo.toml`).

### ritk coeus-native paths advanced — `repos/ritk` gitlink

Ritk peer stream advanced `57b2b1c3 → bcd3b726` on branch
`codex/ritk-burn-ndarray-cleanup`, landing coeus-native paths in
`ritk-filter` (intensity + grayscale morphology) and `ritk-statistics`
(normalization, comparison) as incremental sub-batch #3 per-crate work per
ADR 0012. Verification at HEAD `bcd3b726`:
`cargo nextest run -p ritk-filter -p ritk-statistics -p ritk-image --lib
--no-fail-fast` from `repos/ritk`: **1399/1399 pass, 0 skipped**.
Residual `use burn` source imports: **320** (down from prior session's
260-test-backend count baseline; the dep strip per Batch #3 sub-batch #5
remains peer-stream-gated per ADR 0012 — sub-batches #4, #5, #6 are
reserved pending sub-batch #3.g (python/cli/snap) closure per the standing
reminders in backlog.md).

`repos/ritk` submodule pointer advanced
`57b2b1c3c5eb81b78f50c579730a3b8263b03955 →
bcd3b726a99c55b591f01cc7e922322742ba203d` via the dynamic-SHA-extraction
convention. Inner RITK WT remains dirty (peer-active Batch #4/#5 Burn dep
strip WIP); atlas-meta is NOT absorbing inner-WT state into the parent
pointer per the disjoint-scope rule — only the committed HEAD advance is
pinned.

**Subsequent advances (committed during same atlas-meta session)**:
peer landed two further commits atop the `bcd3b726` pin:
  - `5812cd175 feat(ritk-filter): add coeus-native paths for
    spatial/intensity/morphology filters`
  - `ef9420fb feat(ritk-filter): add coeus-native paths for
    edge/diffusion/intensity filters`
Verified green at HEAD `ef9420fb`:
`cargo nextest run -p ritk-filter --lib --no-fail-fast` from `repos/ritk`:
**1063/1063 pass** (8.318s, under 30s slow threshold per
`engineering_gates`). `repos/ritk` gitlink advanced
`bcd3b726a99c55b591f01cc7e922322742ba203d →
ef9420fb30f9c82ec4a639bd0caaded4c65601f8` via the dynamic-SHA-extraction
convention — inter-session concurrent-agent advances during the
inter-turn window per `concurrent_agents` disjoint-scope rule, each
verified before pinning. Inner ritk WT remains dirty (peer-active Batch
#4/#5 Burn dep strip WIP); atlas-meta pins only the verified committed
HEAD, never WT state.

### Out-of-scope this session (unchanged from prior findings)

- **CFDrs** (`m` lowercase at atlas-parent): inner WT dirty with peer-active
  cfd-1d Picard convergence work (the `cross_fidelity_blueprint_complex_branching`
  finding above). Gitlink ALIGNED; no pointer advance needed. Atlas-meta is
  NOT editing `crates/cfd-1d/**` per ADR 0011.
- **helios** (`m` lowercase at atlas-parent): inner WT carries only untracked
  `examples/` dirs under `crates/helios-{core,domain}`. Gitlink ALIGNED; no
  pointer advance needed.
- All 14 other actively-tracked submodules ALIGNED at inner HEAD with zero
  diverged gitlinks.

### Next actionable

- Continue observing the three peer-stream watchpoints (kwavers-therapy
  KW-WATCH-002 perf, CFDrs cfd-1d Picard convergence, ritk Burn dep strip
  sub-batches #4/#5/#6).
- Provider extension items (Batch #8) remain claimable, but require inner-repo
  edits in provider repos whose WT is peer-clean (leto, moirai, apollo,
  eunomia)._kwavers-solver `Cargo.toml` `ndarray` `rayon` feature gate strip
  (the separate item flagged in `5913f2946`'s body) is a kwavers-peer item.

## Findings 2026-07-13: CFDrs cfd-1d Picard watchpoint closure + helios/kwavers verified advances

### ✅ CLOSED: CFDrs `cross_fidelity_blueprint_complex_branching` Picard convergence (peer HEAD `153b0ed9`)
Peer landed `153b0ed9 fix(cfd-1d,cfd-2d): resolve cross_fidelity_blueprint_complex_branching
convergence` atop the prior pinned `e24922c8`. The historical defect (documented in this
file at "## Findings 2026-07-12: ... kwavers-therapy abdominal perf watchpoint →### CFDrs
cross_fidelity_blueprint_complex_branching -- peer-tracked cfd-1d convergence regression"
and in `repos/CFDrs/gap_audit.md` Finding 2026-07-10 and `repos/CFDrs/docs/gap_audit.md`
OPEN-033) panicked with `MaxIterationsExceeded: Convergence failed: Maximum iterations
(10000) exceeded` from cfd-1d `Network2DSolver` `solve_reference_trace` on the
`double_trifurcation_cif_venturi_rect` network.

Re-verification at HEAD `153b0ed9` (`cargo nextest run --no-fail-fast` from `repos/CFDrs`):
**26/26 pass**; `cross_fidelity_blueprint_complex_branching` PASS in **0.799 s**.
This is three orders of magnitude faster than the prior 10000-iteration timeout
cap and well below the 30s `slow-timeout` threshold in `.config/nextest.toml`.
Evidence tier: empirical (test execution under the committed nextest config). The fix is
the peer stream's work (cfd-math `AndersonAccelerator`, cfd-1d `convergence.rs` per
OPEN-033 component list); atlas-meta confirms empirical closure but does not claim a
proof of the algorithmic mechanism (that evidence belongs to the peer's commit body
and `repos/CFDrs/docs/gap_audit.md` OPEN-033).

Atlas-meta `repos/CFDrs` gitlink advanced
`e24922c8d564816e6f0834912d900e698ef27b93 →
153b0ed95710460014bf2429bc5bd94e31f2d054`.

### Helios advance — verified (peer HEAD `4efb14c`)
Peer HEAD `4efb14c fix(helios-domain): correct voxel_grid_construction example
type errors` atop prior pinned `5f6aef6`. Example-only fix on
`codex/helios-book-multichapter-scaffold` branch; inner WT dirty only on `Cargo.lock`
(atlas-meta pins the committed HEAD, not WT state). Re-verification at HEAD `4efb14c`
(`cargo nextest run --no-fail-fast` from `repos/helios`): **241/241 pass** (2.630 s).
Atlas-meta `repos/helios` gitlink advanced
`5f6aef65a47d716f26452592d3a91f3d934a2ffc →
4efb14cd391fbd0653257865a3f3ea74fdf0e461`.

### kwavers advance — verified (peer HEAD `4453c2275`, same residual watchpoint)
Peer HEAD `4453c2275 fix(kwavers-driver): graceful skip for missing KiCad fixture
files` atop prior pinned `5913f2946`. Small driver-only fix; inner WT clean.
Re-verification at HEAD `4453c2275` (`cargo nextest run --workspace --no-fail-fast`
from `repos/kwavers`): **6097/6099 pass, 2 timeouts, 15 skipped**.

The two timeouts are the pre-existing **KW-WATCH-002** abdominal-preprocessing perf
tests (`abdominal_preprocessing_keeps_external_skin_between_target_and_aperture` and
`abdominal_preprocessing_selects_one_connected_treatment_component`, both on the
explicit 90s `elastic-fwi` profile override at `repos/kwavers/.config/nextest.toml:70-74`).
NOT regressions introduced by the driver fix — the test count grew from 5119 to 6099
(peer added tests); the same 2 KW-WATCH-002 tests still time out at the 90s budget.
KW-WATCH-002 remains **open** (peer-stream perf, NOT atlas-meta's to fix per ADR
0011 disjoint-scope).

Atlas-meta `repos/kwavers` gitlink advanced
`5913f29466bb6b769aefbc1a9b794c63b139babb →
4453c227524d9f150fb1e299c967e98821368ea7`.

### Same-cycle mnemosyne advance — verified (peer HEAD `877cde0`)
Peer HEAD `877cde0 docs(backend): Decide callback pair` atop prior pinned
`98a02b61`. Five new commits on `codex/fix-miri-page-provenance` branch (docs/fix/perf
around `mnemosyne-local` pages and `mnemosyne-prof` interns / leak detection):
`5a9f49f fix(local): Refresh page provenance`, `477f957 fix(arena): Release
converted buffer`, `4ba5958 perf(prof): Drop interned stacks unlocked`,
`708428b docs(pm): Record workspace gate`, `877cde0 docs(backend): Decide callback
pair`. Re-verification at HEAD `877cde0`
(`cargo nextest run --workspace --no-fail-fast` from `repos/mnemosyne`):
**278/278 pass** (4.437 s). mnemosyne has zero moirai dependency, so the peer-active
moirai break documented below does not propagate into this verification.
Atlas-meta `repos/mnemosyne` gitlink advanced
`98a02b61ccb8ce04f5b1920113d8315cae193ae8 →
877cde0586f0d25e70627fa2ad546f583116e47e`.

### moirai peer-active break (NOT pinned) + ritk verify-blocked
A peer-stream break in `repos/moirai` blocks the moirai and ritk gitlink advances
this cycle.

The breaking commit is `9c015a3 refactor(moirai)!: Remove allocator residue`
(atop prior pinned `877cde0` referenced... actually atop pinned `4af0ff58` per the
prior atlas-meta advance). The `!` in the subject marks a breaking change; per the
`c5a3017 chore(build): ...` and CR-2 architecture decision, `#[global_allocator]`
registration was removed from the library in `ce22f85`. Subsequent commits
`24fc9f2 fix(iter): Release source buffers after moves` and `9c015a3` introduced
compilation breaks in `moirai-scheduler` lib tests and `moirai-executor` lib:
errors include `E0277`, `E0432`, `E0596`, `E0599`, `E0609` (10 errors in
`moirai-executor`, 27 in `moirai-scheduler`; symptoms are `cannot borrow as
mutable` and `cannot find type/value` after public-API surface removal).

Followed by another peer advance mid-cycle to HEAD `5343ebfc` with uncommitted
WT edits on `moirai-scheduler/src/deque/{chase_lev,reclaim,split,mod}.rs`,
`lib.rs`, `docs/adr.md`, `docs/checklist.md` — the peer is actively fixing the
break. `cargo nextest run --workspace --no-fail-fast` from `repos/moirai` fails
at compile time. **Atlas-meta WILL NOT advance the `repos/moirai` gitlink**
until the peer stream rebuilds green on a clean HEAD; this is recorded as watchpoint
**MR-WATCH-001** (moirai-scheduler/executor rebuild after
`#[global_allocator]`/allocator-residue removal).

Co-breakage of `ritk` verification this cycle: ritk's `Cargo.toml` declares
`moirai = { path "../moirai/moirai" }`, so building ritk tests transitively
rebuilds the broken in-worktree moirai HEAD. `cargo nextest run -p ritk-io --lib
--no-fail-fast` from `repos/ritk` at the new peer HEAD `39cf95bc` aborts at the
moirai-executor compile step. This does NOT mean ritk is broken — only that
verification is blocked by the upstream moirai break. ritk HEAD `39cf95bc`
remains unpinned this cycle; atlas-meta WILL NOT pin it until either the peer
fixes moirai OR a future cycle can verify ritk against the previously-pinned
moirai HEAD `877cde0` (requires checking out that moirai commit in the inner
WT, which `concurrent_agents` prohibits when the peer has uncommitted WT work
— the deadlock condition is filed here as the re-open trigger).

### Same-cycle hephaestus advance — verified (peer HEAD `c78a98e`)
Peer HEAD `c78a98e1 docs(wgpu): Claim callback migration` atop prior pinned
`b90923ef`. Single docs-only commit on `codex/fix-wgpu-callback-pair` branch.
Re-verification at HEAD `c78a98e` (`cargo nextest run --workspace --no-fail-fast`
from `repos/hephaestus`): **298/298 pass** (97.554 s suite total; slowest
individual test `hephaestus-wgpu::volume_ray_integral
affine_field_is_integrated_exactly_by_midpoint` at 1.196 s, well under the 30 s
slow threshold in `.config/nextest.toml`). Inner hephaestus WT remains dirty
on three files (`crates/hephaestus-wgpu/src/infrastructure/device.rs`,
`crates/hephaestus-wgpu/src/lib.rs`, `crates/hephaestus-wgpu/tests/contract.rs`)
— peer active on wgpu callback pair migration; atlas-meta pins only the
verified committed HEAD, never WT state.
Atlas-meta `repos/hephaestus` gitlink advanced
`b90923ef25d8148b53716e652cdf5b807e31586d →
c78a98e1c7d5615fc8744622a6c9013ed16e1e6b`.

## 2026-07-13 provider integration audit

Evidence is static source inspection unless a stronger tier is stated.

- **Closed — immutable WGPU staging callbacks:** Mnemosyne publishes one
  process-lifetime allocation/deallocation pair through one atomic pointer;
  Hephaestus converts registration conflicts and callback panics to typed or ABI
  failure values. Evidence: Mnemosyne clippy, 42/42 nextest, two focused Miri
  tests, doctests, rustdoc, and semver classification pass; Hephaestus clippy,
  131/131 nextest, doctests, and rustdoc pass. Commits `3c1cf83` and `058a2b8`
  are pushed.
- **Resolved P0 correctness — Hephaestus empty decompositions (`65e89b7`):**
  CUDA bidiagonal, column-pivoted QR, full-pivot LU, Hessenberg, and QR plus WGPU
  QR now use canonical Leto empty state. Value-semantic contracts pin actual
  dimensions, identity factors, rank, permutations, and the empty-product
  determinant. Evidence: focused CUDA/WGPU contracts, Clippy, 239/239 nextest,
  doctests, and rustdoc pass. No synthetic 1x1 factorization remains.
- **Resolved P0 safety — Melinoe scoped partition registration (`55ad20e`):**
  `ParallelExecutor` is a transparent, pointer-sized capability whose unsafe
  constructor owns exact-once normal-return and blocking lifetime obligations;
  safe registration accepts only the validated value. Moirai constructs it at
  the real scheduler bridge. Evidence: compile-time layout assertion, three
  focused Miri executor-path tests, 121/121 Melinoe nextest, 83/83 Moirai
  executor nextest, 196/196 Coeus operations nextest, and one unified Melinoe
  0.9/Mnemosyne 0.3 backend graph. No alias or compatibility path remains.
- **P0 integrity — Moirai NUMA path:** `moirai-iter/src/numa.rs` stores policy
  without applying placement, executes synchronous loops in the async surface,
  discards errors, and owns raw NUMA allocation policy that belongs in
  Mnemosyne. Replace it with provider-owned placement and typed failure.
- **P1 correctness — Themis cache topology:** detection substitutes fixed
  32 KiB/256 KiB/8 MiB values and failure becomes a fabricated single-node
  topology. Leto and Moirai consume these values; absence must remain typed.
- **P1 correctness — Leto scalar execution (PARTIAL — `aecb231`):** scalar hooks discard Hermes
  errors and can partially write the common prefix of mismatched slices.
  ***Length pre-validation (2026-07-15):** `assert_eq!` preconditions added to all mutating
  Scalar methods (add/sub/mul/div_slice, axpy_slice, dot_slice) — the silent partial-write
  defect is closed. 304/304 leto-ops tests pass; apollo-fft consumer builds clean.*
  **Remaining:** Hermes SIMD error propagation needs Result-returning Scalar trait
  signatures (`[major]` — API-breaking).
- **P1 memory — Mnemosyne per-CPU cache (RESOLVED — verified 2026-07-15):** lazy
  `OnceLock<Box<PerCpuCache>>` allocation confirmed: static footprint is ~56 bytes
  (handle), not 720,896 bytes (full table).
  `cache_handle_allocates_storage_on_first_access` test passes. No backend enables
  `ENABLE_CPU_CACHE`. **MNE-PERCPU-001 closed.**
- **P2 hierarchy/DRY:** split Melinoe's 693-line branded deque and Themis's
  667-line sync-region file by operation family; remove Moirai's duplicate SIMD
  implementation in favor of Hermes; consolidate Moirai topology snapshots to
  borrowed Themis-owned data. These are structural, not performance claims.

Residual publish risk: isolated Hephaestus semver analysis builds the current
0.12.0 rustdoc, then its baseline clone cannot resolve the repository-external
`../leto/crates/leto` path dependency. The local Atlas graph is green with
Moirai's committed Mnemosyne 0.2 requirement and no Moirai consumer-tree edit.
### Current provider-consumer reconciliation — 2026-07-14

- **Themis:** provider fix `18807bb` is merged to `main`; Linux cache parsing now
  maps malformed sysfs values to typed absence. The root gitlink is advanced to
  this commit.
- **Mnemosyne:** PR #11's Themis pin remains merged at `f95d372`; allocator
  provenance PR #12 is superseded by merged PR #13 at `32b4a2a`. The provider
  now defaults to zero retained segments under Miri, preserving the production
  bounded cache while allowing leak checking to observe release. Local evidence
  is fmt, warning-denied Clippy, 288/288 nextest, doctests, rustdoc, and the
  Hermes Miri consumer suite without leak suppression.
- **Leto:** PR #32 merged as `8d39f58`; the consumer lock graph now resolves one
  Themis package at 0.10, cache-level fixtures model the provider's optional
  line-size field, and the generic quaternion/fixed-matrix contracts are
  covered by value-semantic tests. Local evidence is fmt, warning-denied
  workspace Clippy, 568/568 locked nextest cases, doctests, and rustdoc.
- **Hermes:** PR #6 head `db8e1a4` pins merged Mnemosyne `32b4a2a` and changes
  the Miri workflow to nextest under the committed timeout profile. Local
  evidence is fmt, metadata, warning-denied Clippy, 388/388 nextest, doctests,
  rustdoc, and 23/23 Miri tests without leak suppression. GitHub CI is running;
  merge remains gated on its fresh Miri, cross-compile, ARM, and supply-chain
  results.
- **Global migration residuals:** RITK still has active Burn-keyed source and
  manifest surfaces under the peer-owned Batch #3 #4-#6 work; Kwavers still has
  active peer-owned ndarray/PyO3-boundary and solver migration work. These are
  not closed by provider pin co-evolution and remain explicit blockers to a
  truthful global-zero residual claim.
- **Evidence tier:** provider and consumer pin claims are source/static graph
  evidence plus compile, lint, nextest, doctest, rustdoc, and focused Miri
  results. Hermes GitHub completion remains pending; no merge is claimed from
  local evidence alone.
  Peer-owned dirty scopes were preserved.

## Findings 2026-07-14: MR-WATCH-001 closure + hermes gitlink advance + kwavers peer-active break

### ✅ CLOSED: MR-WATCH-001 (moirai-scheduler/executor rebuild)
Peer landed clean-green moirai HEAD `c43f86a` (`build(moirai): Update Mnemosyne
provider`) on `perf/moirai-contention-audit` with zero WT edits. The breaking
committed `9c015a3 refactor(moirai)!: Remove allocator residue` and the mid-fix
HEAD `5343ebfc` were resolved by the peer stream across 17 subsequent commits
(`5343ebf → c43f86a`): SPSC publication order preservation, executor lane-chunk
balancing, scheduler-admission bounding, deque-ownership encoding, kqueue
send-safety, IPC errno isolation, and the Melinoe executor-capability adoption.
Re-verification this cycle: `cargo nextest run --workspace --no-fail-fast` from
`repos/moirai` = **720/720 pass** (4.727 s). MR-WATCH-001 is **CLOSED**.

Atlas-meta `repos/moirai` gitlink advanced
`877cde0586f0d25e70627fa2ad546f583116e47e →
c43f86a21e0ea73d8e3bba68d75db9cedae3abb3`.
Evidence tier: empirical (nextest 720/720 under committed config).

### Hermes gitlink advance — verified (peer HEAD `bcef1c8`)
Peer HEAD `bcef1c8 build(deps): Align mnemosyne rev to the stack's 0.4.0
(4a9d2a3)` atop prior pinned `51c530f` on `codex/hermes-themis-pin`, clean WT.
Re-verification at HEAD `bcef1c8`: `cargo nextest run --workspace --no-fail-fast`
from `repos/hermes` = **388/388 pass** (2.120 s).
Atlas-meta `repos/hermes` gitlink advanced
`51c530fa4fe5 → bcef1c86f681`.
Evidence tier: empirical (nextest 388/388 under committed config).

### ⏳ NEW WATCHPOINT: KW-WATCH-003 (kwavers-python leto→ndarray conversion break at peer HEAD `b861254`)
Peer HEAD `b861254 feat(kwavers-transducer): Add layered rays` on
`codex/kwavers-core-moirai-parallel` has 4 commits past the parent gitlink
`739527463e4d` (`c400c432b Own CT assembly`, `879582a57 piston field`,
`25f6a82b6 Bound piston work`, `b861254c0 Add layered rays`) and does NOT build:
`cargo nextest run --workspace --no-fail-fast` aborts in `kwavers-python` lib
test compile with **61 E0277 errors** at
`crates/kwavers-python/src/simulation_result_py.rs:364` — the
`leto::Array<f64, VecStorage<f64>, 1>` → `ndarray::ArrayBase<OwnedRepr<f64>,
Dim<[usize; 1]>>` `TryInto` conversion no longer resolves (the `ndarray-compat`
feature surface on leto has been narrowed or the bound has changed).

The peer is actively mid-flight: 13 uncommitted WT files in `kwavers-gpu`
(`fdtd_gpu.rs`, `acoustic_field.rs`, `activate.rs`/`matmul.rs` neural-network
shaders, `pstd_gpu` helpers/commands, beamforming delay-sum dispatch,
`gpu_buffer/readback.rs`, `thermal_acoustic/buffers.rs`) and `kwavers-analysis`
(`transfer.rs`), plus 3 stashes. **Atlas-meta WILL NOT advance `repos/kwavers`
gitlink past the parent `739527463e4d`** until the peer lands a clean-green
committed HEAD; the peer owns `kwavers-python` and the leto/ndarray boundary.
Re-open trigger: peer commits a clean WT and `cargo nextest run --workspace
--no-fail-fast` passes (the documented KW-WATCH-002 90s abdominal-preprocessing
timeouts remain the accepted residual, not a regression).

### Ritk verify-block — cleared by MR-WATCH-001 closure, but peer-active
MR-WATCH-001 closure removes the transitive moirai-compile block on ritk's path
dep `moirai = { path = "../moirai/moirai" }`. ritk HEAD `ba6da3a5` on
`codex/ritk-burn-ndarray-cleanup` is **1 commit ahead of origin** with **5 WT-
dirty files** (`CHANGELOG.md`, `backlog.md`, `checklist.md`,
`crates/ritk-core/Cargo.toml`, `crates/ritk-core/src/lib.rs`) — the peer is
actively mid-strip on the Burn-depend removal. **Atlas-meta WILL NOT pin ritk**
until the peer lands a clean-green committed HEAD. Re-open trigger: peer pushes,
cleans WT, and `cargo nextest run --workspace --no-fail-fast` passes.

### Gitlink drift map (2026-07-14 — Cycle B updated — post gitlink advances this cycle)

Verified building HEADs in this cycle:
- kwavers `f1dba7b7e`: `cargo check --workspace` clean (optimized + debuginfo).
- ritk `7f81384`: `cargo check --workspace --exclude xtask` clean (dev);
  `cargo nextest --workspace --exclude xtask` 5055/5055 pass.
- coeus `1cb9900`: `cargo nextest -p coeus-core` 21/21 pass (them is 0.10 fix).
- apollo `b633652`: previously 907/907 at dffcb5b; peer WT dirty on 11 files
  (DHT provider migration) — defer advance to next clean-HEAD cycle.
- themis `07bf558`: aligned (peer merged `1996018` → `07bf558` main, 50/50 pass,
  parent already at `07bf558`). THEM-CACHE-001 CLOSED.
- hermes `bcef1c8`: aligned, 388/388 pass (pushed `b5a4c5e`).
- moirai `c43f86a`: aligned, 720/720 pass (MR-WATCH-001 closed, `b5a4c5e`).

| Submodule | Parent pre-cycle | Inner HEAD (pre-advance) | Verification | Post-cycle parent |
|---|---|---|---|---|
| kwavers | `739527463e4d` | `f1dba7b7e` (fix gpu: wgpu 30 Wait) | cargo check workspace full clean | `f1dba7b7e...` (advanced this cycle) |
| ritk | `ef9420fb30f9` | `7f81384` (fix spatial: FixedMatrix) | check clean + 5055/5055 nextest pass | `7f81384...` (advanced this cycle) |
| coeus | `e0a5377` | `1cb9900` (themis 0.10 fix) | coeus-core 21/21 pass | `1cb9900...` (advanced this cycle) |
| apollo | `96e67a2` | `b633652` (docs: DHT migration) | 907/907 at dffcb5b but peer WT dirty 11 files | skip |
| themis | `07bf558` | `07bf558` | 50/50 pass, aligned | already aligned |
| helios | `9ee3b6e` | `9ee3b6e` | multichapter scaffold merged to main | aligned |

### Watchpoint summary — updated post Cycle B
- ✅ MR-WATCH-001 (moirai rebuild) — CLOSED (720/720 at `c43f86a`, in `b5a4c5e`).
- ✅ THEM-CACHE-001 (themis typed-absence) — CLOSED (50/50 at `1996018`→`07bf558`, in `93c4efe`).
- ✅ KW-WATCH-003 (kwavers-python leto→ndarray) — CLOSED as **false-positive** this cycle: shared target-dir stale artifact from ritk-spatial polluted kwavers boundary compilation; clean-build recheck passes (`kwavers 0 errors`, `ritk 0 errors`). See gap_audit section above for evidence.
- ✅ CFDrs cfd-1d Picard convergence — CLOSED (26/26, `153b0ed9`).
- ⏳ KW-WATCH-002 (kwavers-therapy abdominal perf) — open (peer-stream perf).
- ⏳ apollo CZT/DHT provider migration — open (peer WT dirty on 11 files).
- ⏳ ritk Burn dep strip Batch #4/#5/#6 — open, but ritk gitlink advanced 13 commits this cycle with coeus-native paths.
- ✅ MOI-CONTENTION-001 — CLOSED 2026-07-15: `perf/moirai-contention-audit` merged to `main` at `9cd650f` (ATLAS-MOIRAI-016 cancellation/waker-leak fixes + async sync primitives). 82/82 nextest pass.
- ✅ MNE-PERCPU-001 — CLOSED 2026-07-15: lazy `OnceLock<Box<PerCpuCache>>` verified; static footprint ~56 bytes, not 720,896. No backend enables `ENABLE_CPU_CACHE`.
- ✅ LETO-SCALAR-001 (partial) — CLOSED 2026-07-15: length pre-validation (`assert_eq!`) added to all mutating Scalar methods. Silent partial-write defect eliminated. 304/304 test pass. Hermes error propagation deferred (`[major]` Result-returning API change).
- ✅ MOI-NUMA-001/002/003/004 — CLOSED 2026-07-15 per ADR 0017: deleted `moirai-iter/src/numa.rs` (334 lines, 4 P0 HARD defects). Redirected to Themis (placement), Mnemosyne (allocation), Moirai executor (work-stealing). Zero external consumers confirmed. 185/185 moirai-iter, 68/68 benchmarks green.

## Findings 2026-07-15: concurrent peer reconciliation + CFDrs `621395f9` verification + mnemosyne feature-branch root cause

### Concurrent peer activity during this session (reconciled)

A peer agent (same author identity `ryanclanton@outlook.com`) committed six
commits on `codex/kwavers-atlas-integration` while this agent was gathering
verification evidence:

- `9ea1b49 chore(atlas): Advance moirai/ritk/CFDrs submodule pointers` —
  committed at 12:29:33, advancing `repos/moirai` `2431e05c → e3d1a30`,
  `repos/ritk` `17b84bdc → ab2ef6e4`, `repos/CFDrs` `c2113d0f → 621395f9`.
  This is exactly the trio this agent had independently identified as staged
  during orientation; the peer committed them mid-session. Per
  `concurrent_agents` `Detect & reconcile`, no collision occurred — this agent
  had not committed. The peer's commit message provenance triples match the
  SHAs this agent verified independently.
- `a974cf9`, `45df600`, `96de591`, `e64d954`, `699abb7` — five sequential
  `build(mnemosyne): Pin ...` chore commits advancing `repos/mnemosyne`
  gitlink. This corrected the pre-existing defect this agent detected at the
  start of the session: parent HEAD `9220f4a` had the mnemosyne gitlink at
  `a281082`, a feature-branch tip on
  `codex/mnemosyne-split-sampler-sampling` (NOT `main` — `a281082` had
  `crates/mnemosyne/Cargo.toml version = "0.2.0"`)
  while mnemosyne `main` (`3d1abd3e`) carried `version = "0.4.0"`. The peer
  advanced the gitlink through to `2adec54` (PR #22,
  `codex/mnemosyne-prof-contention-baseline`), aligning to `origin/main`.
  This resolves the invalid feature-branch pin and the `mnemosyne ^0.4.0`
  resolver mismatch this agent had traced into the ritk verify path (below).

Branch context: the local mnemosyne clone was significantly stale — local
`main` at `3d1abd3e` (PR #10) vs `origin/main` at `2adec54` (PR #22), 12
PRs behind. The peer's advance to `2adec54` is the `origin/main` head — the
local clone's `main` reference itself was stale until the peer's commits.

The next Mnemosyne provider increment is now also merged: PR #25 landed at
`0012c4fad0c44c0a40ec4d36de68e7138ae218d8`, and Atlas commit `4908208` advances
the gitlink from `52cd5ee`. Its local audit found the `large/8192` RpMalloc
comparison gap to be an in-place same-owner comparator residual, not a page-list
or large/huge unmapping defect. Provider evidence is authoritative in
`repos/mnemosyne/gap_audit.md`; this parent entry records only the cross-repo
pin and closure.

### CFDrs `621395f9` verification evidence (independently gathered, corroborates peer `9ea1b49`)

This agent verified CFDrs at inner HEAD `621395f9`
(`fix(gpu): update wgpu 30 PollType API (#290)` — the merge of the full
Atlas-provider migration push: Leto CSR + Eunomia scalar + Hephaestus GPU +
cfd-math/cfd-2d/cfd-3d/cfd-1d/cfd-validation consumer cones, 51,857
insertions + 22,087 deletions, on `main`, clean WT modulo dirty `Cargo.lock`)
BEFORE the peer committed `9ea1b49`:

- `cargo check --workspace` from `repos/CFDrs` = clean (0 warnings, 58.47s)
- `cargo nextest run -p cfd-core -p cfd-math -p cfd-validation -p cfd-1d -p cfd-2d --lib` =
  **1747/1747 pass, 1 skipped, 26.242s** (no slow tests under the 30s
  threshold) — the venturi cross-fidelity cases at 1.5s/2.4s/3.0s/7.3s plus
  the manufactured turbulent Spalart-Allmaras / Reynolds stress cases all
clean.

The dirty `Cargo.lock` in the CFDrs inner WT is a consus dependency resolution
drift (`consus-core` path vs git-rev qualifier ambiguity) — exactly the
"Cargo.lock dirty on inner submodules is normal-ish lockfile drift" documented
pitfall, not a real source change. It does not block verification.

The peer's `9ea1b49` advance is corroborated by this independent evidence.
Evidence tier: empirical (nextest 1747/1747 under committed config +
workspace `cargo check` clean).

### Mnemosyne feature-branch root cause of the ritk resolver mismatch (diagnosed, since corrected by peer)

While attempting to verify ritk `ab2ef6e4` (the burn-compat merge commit),
this agent hit the documented SEMVER-CHECKS RESOLUTION BLOCKER (gap_audit row 9):
`cargo nextest run -p ritk-image -p ritk-core -p ritk-spatial` (both default
features and `--all-features`) failed at `cargo metadata` with
`error: failed to select a version for the requirement "mnemosyne = \"^0.4.0\""`
required by `coeus-core v0.8.0` via `ritk-filter v0.2.60`'
path dep, candidate found: 0.2.0 at
`D:\\atlas\\repos\\mnemosyne\\crates\\mnemosyne`.

Root cause traced (T1 source verification):
- inner mnemosyne working tree (detached at feature-branch tip `a281082` on
  `codex/mnemosyne-split-sampler-sampling`) declared
  `crates/mnemosyne/Cargo.toml version = "0.2.0"`; mnemosyne `main`
  (`3d1abd3e` at that time) declared `version = "0.4.0"`.
- `coeus-core`'s `mnemosyne = "^0.4.0"` could not resolve against the local
path dep while the inner tree sat on the feature branch.

This was a pre-existing configuration defect in committed state (the
mnemosyne gitlink `a281082` at the then-parent HEAD `9220f4a`/`a974cf9`
pinned a feature-branch tip stale on the 0.2.0 metadata).
Per ADR 0011 §Leg 2, atlas-meta cannot `git switch`/`git fetch` the inner
mnemosyne tree — peer scope. The peer (subsequent commits
`45df600`...`699abb7`) advanced the mnemosyne gitlink to `main`'s `2adec54`
where `mnemosyne = 0.4.0`, which unblocks the ritk verify path going
forward. A re-verification of ritk at the updated mnemosyne pin was not
attempted this session to avoid build-lock contention with the peer's
in-flight mnemosyne commit block.

ritk `ab2ef6e4` itself is a merge commit (`Merge: 3e4e0374 6d182d0f`, PR for
burn-compat feature gate + selective burn dep migration), clean WT on
`main`. The handoff's "duplicate commit titles = rebase artifact needing
squash" assessment was a misread: `6d182d0f` is the feature-branch parent
and `ab2ef6e4` is its merge to `main`, both legitimately titled because a
squash-merge was NOT performed — this is a normal merge-commit shape, not
a rebase artifact. The peer's `9ea1b49` advance is structurally sound.

### Final gitlink reconciliation map (2026-07-15, post `4908208`)

Evidence tier: git insn state (machine-verifiable via `git ls-tree HEAD`,
`merge-base --is-ancestor`, inner `rev-parse`).

| Submodule | Pin (HEAD `4908208`) | Inner `main` | State | Action |
|---|---|---|---|---|
| CFDrs | `621395f9` | `621395f9` | FULLY ALIGNED (== main) | none — verified green this cycle (1747/1747) |
| helios | `8fdc3965` | `8fdc3965` | FULLY ALIGNED | none |
| kwavers | `9a1d72ec` | `1af276575f` | PIN-AHEAD (advanced to `codex/kwavers-core-moirai-parallel` HEAD — 10 commits ahead of main including FFT zero-alloc fix) | watch KW-CV-001 closeout trigger |
| melinoe | `bb07447f` | `bb07447f` | FULLY ALIGNED | none |
| ritk | `ab2ef6e4` | `ab2ef6e4` | FULLY ALIGNED (== main) | none (verifiable at the resolved mnemosyne 0.4 pin next cycle) |
| apollo | `6e99a567` | `e6ecce49` | PIN-AHEAD-FEATURE (branch detached `HEAD`) | defer — peer feature branch |
| coeus | `2026a0b6` | `e0a53778` | PIN-AHEAD-FEATURE (branch detached `HEAD`) | defer — peer feature branch |
| mnemosyne | `0012c4f` | `0012c4f` (`origin/main`; local `main` ref stale) | FULLY ALIGNED with published default | none — PR #25 merged and the provider audit is closed |
| moirai | `e3d1a30` | `e05b623` | DIVERGED (pin on `perf/moirai-contention-audit`; local `main` advanced separately to PR #15+) | acceptable per ATLAS-MOIRAI-016 + the peer `9ea1b49` commit; peer owns the moirai main merge chore separately |
| consus | `ec386e3` | `0106b709` | DIVERGED | not in active stack (per `gap_audit.md` §Private consumers — consus is a local artifact not registered as a stack member) |
| gaia | `79310ba2` | `9e481024` | DIVERGED | not in active stack (per §Private consumers) |
| leto | `855f3ad` | `efa235a` | PIN-AHEAD (advanced to `codex/leto-scalar-length-validation` — scalar length pre-validation) | verified: 304/304 nextest pass, apollo-fft consumer builds clean |
| eunomia, hephaestus, hermes, themis | (various) | (no `main` in metagit) | (not comparable via this probe) | origin-only submodule metagit layout; verification via `cargo check`/`nextest` directly |

### Atlas-meta scope posture this cycle

The Mnemosyne merge trigger is closed by `4908208`. Remaining parent-side
advances await (a) kwavers peer merge to `main` (KW-CV-001 closeout trigger),
(b) apollo/coeus peer feature branches merging to their `main` refs, and (c)
any divergent peer main (moirai) reconciling via peer chore. These are
peer-stream triggers; atlas-meta's role is bystander verification plus pointer
advance on each trigger, per `concurrent_agents` contention response order and
the operation loop's standing-increment re-probe.

Residual risk: ritk at the updated mnemosyne 0.4.0 pin has not been
re-verified with `cargo nextest` this session (deferred to avoid
build-lock contention with the peer's in-flight mnemosyne pin block). The
peer's `9ea1b49` commit body cites ritk `ab2ef6e4` as Batch #3
burn-compat migration without explicit nextest numbers; the next
gap-analysis cycle should re-run the ritk verify path now that mnemosyne
0.4.0 resolves correctly at the parent gitlink.
