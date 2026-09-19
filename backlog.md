# atlas — cross-repository integration backlog


## Landed from this sweep (2026-08-13)

| ID | Commit | Note |
| --- | --- | --- |
| ATLAS-APOLLO-FAKEGEN-036 | apollo `5749d104` | **Premise corrected.** The item claimed downstream f32 tolerances were derived against an f64-accumulated reference. False: every `dft_inverse` call site passes `Complex64`, where f64 accumulation *is* native precision, so no shipped result was wrong and no tolerance changed. The defect was latent — a trap for the first `Complex32` caller — and is closed with a derived-bound test plus a bitwise test, the latter being what actually discriminates a widened accumulator. Reclassified `[patch]` → **`[major]`**: closing it deleted `precise_re`/`precise_im` and `BLUESTEIN_NATIVE_PHASE_TRIG` from the public `KernelScalar`. |
| ATLAS-EUNOMIA-F64-SPECIALS-062 | eunomia `329fe85` | Confirmed as filed. Measured pre-fix error: `log10(2.0)` 1.43e-8, `lgamma(5.0)` 2.56e-8. |
| ATLAS-EUNOMIA-SUBBYTE-ORD-063 | eunomia `329fe85` | **Worse than filed.** With `Bf8::MIN_VALUE = 0xFC`, `max_scalar(MIN_VALUE, x)` returned `-Inf` for every finite `x` — a Max reduction over `Bf8` returned its own seed for all input. The fix also consolidated the hand-written `F16`/`Bf16` impls into one macro instead of adding four more copies. |
| ATLAS-EUNOMIA-ACCUMULATOR-064 | eunomia `329fe85` | Landed as `[minor]`, not breaking: `FloatElement` is sealed by a `pub(crate)` supertrait, so no out-of-crate implementor can exist. |
| ATLAS-LETO-TILES-048a | leto `7f80044` | `ExactSizeIterator` **did not hold as written** — `next` used `offset_of(...).ok()?`, which terminates early and would make `len()` lie. Fixed at the root with a constructor validation carrying its proof, rather than by declining the trait. |
| ATLAS-LETO-SVD-049 | leto `58b6eb3`, default `143696d` | Collapsed the obsolete duplicate SVD implementation: deleted one-sided Jacobi, moved pseudoinverse construction onto bidiagonal QR, removed the full-rank rejection, and rewrote ADR 0005 with the dated decision re-derivation. Focused SVD nextest passes 23/23. |
| ATLAS-THEMIS-TOKEN-032 | themis `8930489` | Reproduced first: the exploit compiled, a write through one reference changed what the other read, and miri gave a Stacked Borrows error. Fixed with **no new `unsafe`** — a `&mut` borrow discharges the disjointness obligation exactly as ownership does, so the tag-accepting constructors give way to `from_unique(&'a mut _)`. `project_static` became *safe*: its `# Safety` clause described an obligation the signature makes unviolatable. Zero downstream consumers, so the break needs no migration. |
| ATLAS-CONSUS-PARSE-LIMITS-035 — **closed 2026-08-14; premise was stale** | consus `03bb65e` | Parent-commit evidence: three crafted length fields panicked with `capacity overflow` and three 10 000-deep datatypes killed the process with `STATUS_STACK_OVERFLOW`. All six now return typed errors. **Two defects found beyond the item**: `find_huge_object_recursive` recursed on a loop-invariant `header.depth` so a self-referential child pointer recursed forever, and it indexed `len() - 1` on a possibly-empty vec. **Every one of the 11 line numbers in this item resolves against `03bb65e~1`, three commits behind the default head.** `03bb65e` plus `98d8ff2`/`0556918` had already bounded all of them, added `consus-core/src/parse/budget.rs`, threaded `descend(depth, ...)` through `parse_datatype_inner`, and landed the 10 adversarial tests in `consus-hdf5/tests/adversarial_input.rs` that satisfy this oracle. The item was measuring a superseded revision. What it did surface, by prompting a fresh sweep, is three sites the hardening pass itself missed, fixed in `3beb797`: **`collect_btree_v1_leaves` (`file/reader.rs`) recursed with no depth bound and re-reads `header.level` from each node instead of decrementing, so a child pointer addressing its own node recurses forever — reachable from `Hdf5File::open` on any v1 symbol-table group**, the exact twin of the `btree/v2.rs` defect sitting beside it; plus two FITS allocations sized from `TFIELDS` and `TFORMn`, each bounded exactly (a column needs its own `TFORMn` card; a repeat count cannot exceed the materialized cell) rather than by an invented ceiling. All three falsified by removing the bound: stack-overflow abort and two `capacity overflow` panics. A further ~12 sites are filed as consus `-036`/`-037` rather than widened into this item, the most exploitable being `heap/global.rs:122`'s unchecked `collection_size - header_size` underflow. **Lesson for this board: an item citing exact line numbers is a claim about a revision, and must be re-verified against the current head before it is worked.** |
| ATLAS-KWAVERS-KZK-LINEAR-080 — **closed 2026-08-17** | kwavers `5c553d36b` | **Retired buggy hand-rolled plugin onto correct existing `kzk/` module.** Created `KzkPlugin` adapter wrapping `KZKSolver`+`KZKConfig` behind the `Plugin` trait. Rewired `catalog.rs` and therapy `execution.rs` consumers. Deleted 430-line `kzk_solver_plugin/` with its three live physics defects (spectral/real-space conflation, real cos instead of complex exp, dimensionally wrong absorption). 3 regression tests (real-field evolution, plane-wave absorption oracle, focused-beam amplitude) all pass. `cargo check`/`clippy`/`nextest` 886/886 green at `5c553d36b`. | ~~[major]~~ [patch] | Oracle: plane-wave absorption decays as `exp(-alpha*z)` matching input `alpha`; focused-beam amplitude matches analytical parabolic propagator. Closed by deletion — the buggy code no longer exists.ed tolerance. Each test fails on the parent commit. **CORRECTION 2026-08-18: this closure overstates its evidence, and the retirement itself was right.** Independent verification against the deleted source at `5c553d36b^` confirms all three defects **and finds a fourth the row does not list**: the diffraction phase omitted `dz` entirely, so `(kx²+ky²)/(2k)` had units of 1/m rather than radians and reached ~1178 at 1 MHz in water — `cos(·)` was a sign-flipping pseudo-random real mask over real space. The absorption defect was also worse than described: `exp(-α·dz)` raised to `dz/2` gives an exponent of ~`α·5e-7` at `dz = 1e-3`, so absorption was **effectively disabled**, not mis-scaled. There was no FFT anywhere in the file. But **the "3 regression tests … all pass" and the stated `exp(-alpha*z)` oracle do not exist as described**: `kzk/plugin.rs:367` asserts `p000.is_finite() && p000 > 0.0`, and `:398`/`:450` assert `fields.iter().all(is_finite)`. `plane_wave_absorption_oracle` (`:335`) never checks a decay rate. All three would have passed against the buggy implementation, so they falsify nothing. Tracked as ATLAS-KWAVERS-KZK-TESTS-082. The reclassification `[major]` → `[patch]` is also wrong: `pub mod kzk_solver_plugin` was removed from `kwavers-solver`'s public surface, with no ADR, no CHANGELOG entry under Unreleased, and `cargo semver-checks` unrun. |
| ATLAS-CONSUS-SHUFFLE-038 — **closed 2026-08-18** | consus `ef439b2` | **Worse than filed: both directions were pass-through, not just the read.** `dataset/chunk.rs:311` (reverse) and `:374` (forward) each returned `Ok(data)` unchanged for filter ID 2, so fixing only the read — as the item specified — would have broken every round-trip that currently happens to work by symmetry. Original evidence stands: `h5py_shuffle_deflate_i32` returned `[50462976, 117835012, 0, 0, …]` against an expected `0..15`, which decodes to bytes `00 01 02 03 04 05 06 07` + 24 zeros — the shuffled plane layout, returned with **no error**. Not the v1 B-tree descent bound (that applies to *group* trees; the chunk path separately rejects `header.level != 0`), and deflate itself was never implicated — every pure-deflate case passed. Workspace baseline was **1 failure, not the 7 previously recorded**. |
| ATLAS-KWAVERS-KZK-TESTS-082 | **The KZK retirement replaced wrong physics with tests that cannot fail.** All three tests added to `kzk/plugin.rs` are existence-only assertions — `p000.is_finite() && p000 > 0.0` (`:367`) and `fields.iter().all(is_finite)` (`:398`, `:450`) — and **every one would have passed against the buggy implementation they replaced**, which is the mock-detection heuristic failing outright. Worse, `:335` is *named* `plane_wave_absorption_oracle` while asserting only finiteness, so it claims evidence it does not provide. This is the HARD existence-only-assertion prohibition, introduced by the fix for -080 and then reported as satisfied on the board. The one genuine analytical oracle, `kzk/validation/absorption.rs::test_absorption` (`exp(-α·d)` at 2%, exact-FFT-bin derivation, Szabo 1994), tests the **delegation target**, which the deleted plugin never called — it cannot serve as retroactive falsification. `test_gaussian_beam_diffraction` (radius vs `√2·w₀`) is `#[ignore]`d for exceeding the 60 s budget, and its non-ignored variant asserts only `center > corner`. | [major] | The three tests assert value semantics against an analytical oracle. A plugin-level `exp(-α·z)` axial decay **ratio** is feasible despite `extract_source`'s peak normalisation, since normalisation removes absolute scale but preserves the ratio; tolerance derived from the grid and operation count, not tuned. Each must be falsified by resurrecting the deleted plugin in a scratch branch and observing the failure. The `#[ignore]`d diffraction oracle either fits the committed budget or moves to a reviewed longer-budget profile — it does not stay ignored. Separately: the `pub mod` removal gets its ADR, its Unreleased CHANGELOG entry, and a `cargo semver-checks` run. |
| ATLAS-MNEMOSYNE-ALIAS-033 | mnemosyne `4c22fba` | **Premise disproved.** The reported sequence passes miri under both Stacked and Tree Borrows on the unfixed code. A control — the same aliasing with the exclusive reference *used* afterwards — is flagged immediately, so the method had detection power and the invalidation is real; the UB is not. `with_scratch` never touches `vec` after the closure, and the slice points into the heap buffer, a different allocation from the struct inside the `UnsafeCell`. Soundness held by accident of dead-code timing, so it was fixed anyway and `capacity()` is now safe code. **Reclassify: fragility, not UB.** The two secondary fixes were confirmed, and the leak-on-unwind had a *third* site (`Heap::free`) the item did not name. |
| ATLAS-CACHE-FORK-055 — **closed 2026-08-14** (partial) | — | **33.8 GB reclaimed** by deleting 22 stale `repos/*/target` forks. 25.1 GB remains in ritk, kwavers and mnemosyne, deferred because each showed activity within hours. The forks regrow unless whatever creates them is found, so the item stays open until the cause is identified. Verified 2026-08-14: zero real cargo caches under `repos/*`. The one surviving `repos/athena/target` holds only mdBook output from its Pages workflow's `output-path: target/book/athena`; the `target_forks` metric was counting any dir named `target*` and is corrected in `977e009` to require a cargo marker (`.rustc_info.json`/`CACHEDIR.TAG`/`debug`/`release`), tested in both directions so suffixed evasions like `target_isolated` still count. **Regrew and was cleared again 2026-08-18: 7.67 GB** (`repos/helios/target` 7.52 GB idle 16h, `repos/harmonia/target` 339 MB idle 6.5h), both carrying `.rustc_info.json` so both real caches rather than the athena false positive. The cause question the item left open is now answered as *no live override*: neither repo has a nested `.cargo/config.toml`, `CARGO_TARGET_DIR` is unset, and the root `target-dir = "target"` resolves config-relative to `D:\atlas\target` correctly — so these are residue from building the member standalone outside the umbrella, not a misconfiguration to remove. That makes recurrence expected rather than a defect, and the corrected `target_forks` metric is the standing control: it caught both within one scan. |
| ATLAS-HELIOS-STRAY-PNG-061 | Atlas `0023164` | **Premise stale.** The tracked `helios_workflow_output/{ct,dose,mu,recon}.png` files were already removed when the root was cleared to the sanctioned set; the current tree has no directory or tracked PNGs. No provider edit was required. |
| ATLAS-HORAE-EXACTNESS-069 | Horae PR #12 merged at default `41dcf00`; provider CI `31792859575` (verify and supply-chain) and book build `31792859919` are green. Event clipping now states the Sterbenz precondition and preserves the event endpoint as authoritative; ratio-three subcycling carries a derived floating-point reconstruction bound with value-semantic tests. |
| ATLAS-HYPERION-INTERP-068 | Hyperion PR #9 merged at default `41ef18e`; provider `verify` and `supply-chain` run `31794767546` are green. NIST reference intervals now use a native-`T` natural cubic spline in log-energy/log-coefficient space, with ten independently queried XCOM off-knot values as a method-regression oracle. XCOM's fourth displayed digit is documented as an interpolation aid rather than an accuracy guarantee; no unsupported global error bound is claimed. |
| ATLAS-HEPH-SEAM-043 / ATLAS-HEPH-ACCEL-044 / ATLAS-HEPH-DEADBUILD-060 | Hephaestus PR #208 merged at default `ff2ab47`; exact-head CUDA `31793963123`, ROCm `31793963119`, WGPU `31793963054`, and Metal `31793963181` checks pass. `KernelDialect` is open, scan is shared over `DeviceApi`, CUDA/ROCm scan copies and the unused root build script are deleted, and required Leto SVD lock/API co-evolution is aligned. Independent architectural review approved the final head; hardware jobs were skipped by the workflow. |
| ATLAS-LICENSE-FILES-039 | **Premise stale.** The current default heads of Moirai `e972174`, Leto `143696d`, Gaia `18349bc`, and Helios `152a66c` each carry both `LICENSE-APACHE` and `LICENSE-MIT`, and each manifest declares `MIT OR Apache-2.0`. No provider edit was required. |
| ATLAS-ADR-GOV-058-HYPERION | Hyperion PR #10 merged at default `d17e863`; its ADR 0001 index now records the existing canonical `Status: Accepted` header. Provider checklist and gap audit are synchronized; exact-head `verify` and `supply-chain` run `31795703287` pass, while recurseml analysis remains report-only. The broader ADR-governance item remains open for other members. |
| ATLAS-ADR-GOV-058-IRIS | Iris PR #15 merged at default `3c9dc85`; its generated ADR index now lists ADR 0001 and 0002 as `Accepted` and excludes the non-ADR `INDEX.md` overview. Exact-head `verify` and `supply-chain` run `31796011010` pass; recurseml analysis remains report-only. The broader ADR-governance item remains open for other members. |
| ATLAS-ADR-GOV-058-PROTEUS | Proteus PR #11 merged at default `3c64c8e`; both ADR status headers are canonical `Accepted` and the generated index matches them. Exact-head `verify` and `supply-chain` run `31796273743` pass; recurseml analysis remains report-only. The broader ADR-governance item remains open for other members. |
| ATLAS-ADR-GOV-058-AEQUITAS | Aequitas PR #30 merged at default `f7c9cf2`; its fifteen-ADR generated index now records canonical `Accepted` statuses with no anomalies. Exact-head `verify` and `supply-chain` run `31796547009` pass; recurseml analysis remains report-only. The broader ADR-governance item remains open for other members. |
| ATLAS-ADR-GOV-058-HORAE | Horae PR #13 merged at default `1b35d3f`; its ADR 0001 index now records the existing canonical `Status: Accepted` header. Provider checklist and gap audit are synchronized; exact-head `verify` and `supply-chain` run `31797039383` pass, while recurseml analysis reports an analyzer error and remains report-only. |
| ATLAS-ADR-GOV-058-EUNOMIA | Eunomia PR #67 merged at default `9c2d972`; its four-ADR generated index now records canonical `Accepted` statuses with no anomalies. Exact-head `Rust verification` and `Supply chain` run `31797566750` pass; recurseml analysis reports an analyzer error and remains report-only. |
| ATLAS-ADR-GOV-058-THEMIS | Themis PR #25 merged at default `8d6e83e`; its two-ADR generated index now records canonical `Accepted` statuses with no anomalies. Exact-head compile-fail, Ubuntu, Windows, and Miri checks pass in run `31797905436`; recurseml analysis reports an analyzer error and remains report-only. |
| ATLAS-ADR-GOV-058-RITK | Ritk PR #147 merged at provider default `d1087139`; ADR 0002 now records `Accepted` without claiming the Burn→Coeus consumer cutover is complete, ADR 0007/0008 use canonical status headers, and the generated index matches all ADR headers. PM-sync PR #148 merged at `37e46ef`. Final exact-head CI `31802349902` and Python CI `31802349905` pass; recurseml analysis remains report-only. | [patch] | ATLAS-ADR-GOV-058 |
| ATLAS-ADR-GOV-058-LETO | Leto PR #112 merged at provider default `2821a4b`; ADR 0001 is canonical `Rejected` after ADR 0004 shipped its replacement, ADR 0011 records the measured full-block regression without claiming that path shipped, ADR 0012 is `Proposed`, and ADR 0013 is canonical `Accepted`. The later duplicate ADR 0011 was renumbered to ADR 0024 and its code-doc link updated. The generated index has no anomalies or drift. Exact-head CI `31804526486` and Pages deployment `31804524894` pass; recurseml analysis remains report-only. | [patch] | ATLAS-ADR-GOV-058 |
| ATLAS-ADR-GOV-058-HEPHAESTUS | Hephaestus PR #209 merged at provider default `be7389e`; 52 ADR records now use canonical statuses and the generated index has zero anomalies or drift. ADR 0003 retains the accepted architecture while explicitly recording QR work as pending; ADR 0004 retains its amendment; ADR 0005 records its supersession as historical `Rejected` status. Exact-head CUDA `31805214715`, ROCm `31805214723`, WGPU `31805214652`, and Metal `31805214716` checks pass; recurseml remains report-only. Atlas points to the merged default head. | [patch] | ATLAS-ADR-GOV-058 |
| ATLAS-ADR-GOV-058-APOLLO | Apollo PR #93 merged at provider default `fca501f`; ADR 0001 is canonical `Rejected` while preserving its Hephaestus supersession, and ADR 0011 is canonical `Accepted` while preserving its dated benchmark decision. The 39-record generated index has zero anomalies and zero drift. Exact-head Rust workspace `31806913513` (job `94787923879`) and Python bindings (job `94787923826`) pass; CodeRabbit passes and recurseml remains report-only. Atlas records the merged default; the peer-owned performance branch and dirty lockfile remain outside scope. | [patch] | ATLAS-ADR-GOV-058 |
| ATLAS-RITK-DICOM-ORIENTATION-070 | **Closed at Atlas integration scope.** RITK owns `ImageOrientationPatient` (0020,0037) and Atlas now records merged defaults for both sides of the seam (`ritk` `bd43dbb3`, `helios` `152a66cd`). `python scripts/atlas-provider-integration-audit.py --exact-heads` passes and confirms requested-provider exact-head/coherence closure with both gitlinks aligned to fetched defaults. | [minor] | ATLAS-RITK-DICOM-ORIENTATION-070 |
| ATLAS-HERMES-AMX-DOWNGRADE-096 | **Closed at Atlas integration scope.** The Hermes AMX downgrade slice is integrated at merged default `fb36e0fe`, and `python scripts/atlas-provider-integration-audit.py --exact-heads` passes with requested-provider exact-head/coherence closure. Atlas now records the merged Hermes default gitlink and no further root-owned integration action remains for this item. | [patch] | ATLAS-HERMES-AMX-DOWNGRADE-096 |
| ATLAS-KWAVERS-MNEMOSYNE-LOCALITY-001 | **Closed at Atlas gitlink scope 2026-08-16.** Kwavers folds its hand-rolled NUMA memory-policy execution (`bind_memory_to_node` / `allocate_interleaved_memory` / `first_touch_memory` in `arena/numa/memory.rs`) onto mnemosyne-heap: commit `152c4a7d1` on `codex/kwavers-mnemosyne-numa` (head `08df5730f`) deletes the duplication (net −235 lines) and routes `NumaAwareAllocator` / `SoAFieldBuffer` / `first_touch_memory_parallel` through `mnemosyne_heap::numa::{bind_to_node, first_touch}`. Mnemosyne `5ca0461` owns the execution (`mnemosyne-heap::numa` + `TieredHeap::alloc` routing `PlacementHint::Numa` through `bind_to_node`); Themis owns the vocabulary; Moirai owns the parallel fan-out. PR #382 merges the fold and PR #383 normalizes the ADR statuses; Atlas now records merged Kwavers default `1d7c6899` (gitlink-only advance; the peer-dirty `codex/kwavers-floatelement-roots` working tree is left untouched per the concurrent-agents rule). The stale clean `kwavers-mnemosyne-numa` lane is removed and the lane audit is clean. | [patch] | ATLAS-KWAVERS-MNEMOSYNE-LOCALITY-001 |
| ATLAS-MOIRAI-ORDERING-052-PM-SYNC | Moirai PR #134 merged at provider default `9125837`; `CHECKLIST.md` now closes the SPSC, async wake-dedup, PAL reactor, and connection-pool reservation slices with their exact merged heads and hosted evidence. The provider remains clean and no production source changed. | [patch] | ATLAS-MOIRAI-ORDERING-052 |
| ATLAS-MOIRAI-ORDERING-052-INSTRUMENT | Atlas-side instrument correction: the conformance scanner counted path-redirected `#[cfg(test)]` sidecars as production (`declared_cfg_test` missed sibling-directory `#[path]` declarers; moirai-iter gates `../async_iter_tests.rs` from `src/async_iter/mod.rs`). Fixed at `9828ee8` with three regression tests; moirai `seqcst_production` ratchet drops 101 to 85, its honest value. Remaining production sites are documented decisions: the Chase-Lev thief gate needs one total order across increment/recheck versus the resizer drain (a Relaxed increment has no SC-order position, so relaxation requires protocol restructuring for no measured win on a locked-CAS path), and idle/blocking form the documented Dekker store-buffer pair. Full family sweep complete: worker.rs, scheduler/core.rs, futex_mutex.rs, and the mpmc waiter-count adds (channel.rs:172,261 - register-before-recheck Dekker halves, independently derived) are all recorded KEEP decisions; zero undocumented production sites remain and the item closes with no source change. Ritk follow-up candidate under its own claim: `crates/ritk-vtk/src/domain/mtime.rs:46` monotonic tick admits Relaxed. | [patch] | ATLAS-MOIRAI-ORDERING-052 |
| ATLAS-MOIRAI-ORDERING-052-SPSC | Moirai PR #130 merged at default `ac111b3`; the SPSC ring model uses a capacity-two wrap-around, three FIFO values, and preemption bound four. Hosted `Loom channel models` passes in run `31798789797`; the external recurseml analyzer error remains report-only. |
| ATLAS-MOIRAI-ORDERING-052-WAKER | Moirai PR #131 merged at default `fd517fe`; async `is_queued` clear/swap now use Relaxed ordering, with a Loom dequeue/clear versus wake/swap model. Exact-head workflow `31800148163` passes Loom and workspace gates; `31800148178` passes bindings and all wheel smoke tests; recurseml analysis remains report-only. The first model revision failed on a non-contractual cross-atomic observer assertion and was corrected before the passing head. | [patch] | ATLAS-MOIRAI-ORDERING-052 |
| ATLAS-MOIRAI-ORDERING-052-REACTOR | Moirai PR #132 merged at default `8830f1b` (change head `098e266`); the PAL reactor's three `running` accesses now use Relaxed ordering because the flag carries loop control only and `stop()` separately wakes the platform poller. Exact-head workflow `31800607186` passes Loom and workspace gates; `31800607152` passes bindings and all wheel smoke tests; recurseml analysis remains report-only. | [patch] | ATLAS-MOIRAI-ORDERING-052 |
| ATLAS-MOIRAI-ORDERING-052-POOL | Moirai PR #133 merged at default `f766c6d` (change head `04dc26e`); `ConnectionPool::reserved_connections` admission/release accounting now uses Relaxed operations, with a bounded Loom model covering two serialized admissions racing one paired cancellation. Exact-head workflow `31801180700` passes Loom and workspace gates; `31801180691` passes bindings and all wheel smoke tests; recurseml analysis remains report-only. | [patch] | ATLAS-MOIRAI-ORDERING-052 |

Completed provider slices from this sweep are recorded here so the residual
rows below retain their original audit scope:

| ID | Commit | Closed scope |
| --- | --- | --- |
| ATLAS-COEUS-LAYERNORM-SHAPE-031 | coeus `a2638c03` | Multi-dimensional trailing-shape LayerNorm across Rust core, autograd, GPU provider contracts, and thin Python bindings; provider workflows and book passed. |
| ATLAS-IRIS-COLORSPACE-072 | iris `eec98186` | Explicit sRGB encoded/linear-light RGB and opacity-alpha contract with byte round-trip coverage. |
| ATLAS-PROTEUS-DOMAIN-073 | proteus `6b9bd0b` | Temperature validity-domain newtype, finite-positive validation, typed errors, and boundary tests. |
| ATLAS-ASCLEPIUS-PARAM-074 (typed-parameter slice) | asclepius `5d528d2` | Closed: distinct `Gamma50` and `LymanSlope` types have compile-fail swap coverage; the proposed CEM43 restriction was withdrawn because sub-43 °C behavior is part of the canonical law contract. |
| ATLAS-THEMIS-CONFORMANCE-083 | themis `b1b671c`; Atlas `0922c58` | Replaced Themis's duplicate thread cache with Melinoe's `thread_cached!` provider, split the oversized static-cell leaf, and closed the value-semantic assertion and safety-comment findings. Hosted Ubuntu/Windows, Miri, compile-fail, documentation, and CodeRabbit checks pass. |
| ATLAS-POSTMERGE-HEAD-084 | Atlas `73974ee` | Advanced the Ritk and Eunomia gitlinks to fetched defaults `3f30cddf` and `2e0d724c` while preserving dirty provider worktrees. Ritk hosted CI is green; Eunomia's Rust and supply-chain checks are green and its external `recurseml/analysis` status remains report-only. |
| ATLAS-HELIOS-BENCHMARK-085 | Helios `152a66c` | Helios PR #54's benchmark regression job completed successfully; the merged default head is fully green across book, Rust, Python, and benchmark checks. The Atlas gitlink remains peer-owned at its staged integration head. |
| ATLAS-THEMIS-STD-FEATURE-086 | Themis PR #22; merged default `f879e71` | Fixed the optional-dependency feature closure: `themis/std` now activates Melinoe before referring to its `std` feature. Ubuntu, Windows, compile-fail, branded Miri, and local strict Clippy are green; `recurseml/analysis` is external/report-only. |
| ATLAS-THEMIS-STABLE-PROOFS-088 | Themis PR #23; merged default `fa8dc29` | Added stable trybuild enforcement for invalid shared-cell construction (`E0599`) and overlapping mutable borrows (`E0499`) with committed stderr fixtures. Ubuntu, Windows, compile-fail nightly, and branded Miri are green; `recurseml/analysis` is external/report-only. |
| ATLAS-THEMIS-GITATTRIBUTES-092 | Themis PR #24; merged default `17d3647` | Reconciled the stale provider PM claim: the tracked `.gitattributes` already contains `* text=auto`; no source or tree-wide renormalization was required. |
| ATLAS-AEQUITAS-CI-093 | Aequitas PRs #27–#29; merged default `770a369` | Replaced unlocked lock normalization with locked metadata verification, refreshed the standalone lock to Eunomia `b6f001a`, removed overlay-only patch entries, and reconciled the delivered 0.2.0 comparison label. Default-head CI `31786185235` is green. |
| ATLAS-PROTEUS-CI-094 | Proteus PR #10; merged default `671c9fa` | Added finite CI timeouts and concurrency, converted all lock-sensitive verification commands to `--locked`, synchronized the README, and refreshed the standalone lock to Aequitas `770a369` plus Eunomia `b6f001a`. Default-head CI `31786562412` is green. |
| ATLAS-MOIRAI-NUMA-095 | Moirai PR #128 plus PM closeout PR #129; merged default `e972174` | Forwarded `MoiraiBuilder::numa_aware` through the existing core/executor feature seams and one scheduler construction path. Default topology-aware behavior remains; explicit disablement skips worker NUMA assignment construction. Default-head Rust Workspace `31787962637` and Python Bindings `31787962649` are green. |
| ATLAS-HERMES-AMX-CONFIG-087 | Hermes PR #40 merged at `b95d19d` (head `5a8d718`) | Corrected the AMX irregular-width configuration and repacked row-major GEMM right-hand panels into the VNNI layouts required by the dot-product instructions: `K/4 × 4N` for INT8 and `K/2 × 2N` BF16 elements. The provider-owned packer covers fixed-tile and blocked-GEMM paths with independent value-semantic four-byte and two-element grouping tests. Follow-up cleanup closes Hermes `must_use_candidate` 162→0, `elidable_lifetime_names` 131→0, `missing_errors_doc` 83→0, `missing_safety_doc` 8→0, `semicolon_if_nothing_returned` 92→0, and `unreadable_literal` 180→0 with a documented generated-table exception, splits the SIMD view-cast and `SimdOps` blanket-implementation leaves, scopes the macro's unreachable-code expectation to Neon with a regression test, rejects zero NTT moduli with a typed error, validates bitboard squares before shift arithmetic, removes the conformance ratchet regressions introduced by the lint cleanup, and canonicalizes NTT residues before subtraction. The current local Hermes workspace all-target Clippy gate is clean, nextest is 454/454, the Hermes/core doctest gate is 18/18 with 7 ignored, and the benchmark-target smoke gate passes. Hosted run 31779776851 is green across all seven jobs. |

**Current exact-head status (2026-08-14):** the structural and exact-head
provider audits are clean. Moirai is advanced to hosted-green `e972174`, and
Leto is advanced to hosted-green `143696d`. Aequitas, Proteus, Helios,
Iris, Ritk, Eunomia, Gaia, Melinoe, Tyche, and Hermes now match
their fetched default heads. Helios PR #54 is merged at `152a66c` and its
benchmark regression job is green. Themis's stable-proof PR #23 is merged at
`fa8dc29`. Hermes PR #40 carries the AMX VNNI packer and follow-up
lint/docs/structure cleanup, merged at `b95d19d`; local contract gates and all
seven hosted checks are green at head `5a8d718`. Proteus and Iris default-head
checks are green across build, verification, deployment, and supply-chain
jobs. Moirai default-head Rust Workspace and Python Bindings runs
`31782344026` and `31782344151` are green. Leto default-head Rust verification
run `31782827546` and Pages deployment run `31782826144` are green. The prior
benchmark and Intel SDE AMX differential checks are green. Gaia's exact
default-head CI run `31784028179` is green at `18349bc`; Melinoe's default
head `0bc287a` carries the hosted MSRV run `31785253730` green at source head
`6e6a181`; the book run
`31783965823` is green at source head `c06504c`, and the replacement head only
adds documentation to the test crate outside the book workflow's source paths.
Themis's stable-proof source remains at `fa8dc29`; its PM closeout is merged at
default head `17d3647`. Aequitas's lock-gate PR #29 default is `770a369`; its
exact default-head CI run `31786185235` passes verify and supply-chain.
Proteus's bounded locked-gate PR #10 default is `671c9fa`; exact default-head
CI run `31786562412` passes verify and supply-chain. Moirai's NUMA policy PR #128
and PM closeout PR #129 are merged at default `e972174`; exact default-head Rust
Workspace run `31787962637` and Python Bindings run `31787962649` pass.
Horae PR #12 is merged at default `41dcf00`; exact-head CI run `31792859575`
passes verify and supply-chain, and the book build `31792859919` is green.
Hyperion PR #9 is merged at default `41ef18e`; exact-head CI run `31794767546`
passes verify and supply-chain. Its external `recurseml/analysis` status is
report-only and failed without affecting the provider-owned gates.



## Tier 0 — unsoundness and wrong numbers shipping

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-LETO-LAYOUT-034 — **closed 2026-08-15** | `Layout` (`crates/leto/src/domain/layout/mod.rs:13-20`) exposes `pub shape`/`pub strides`/`pub offset` with a non-validating `pub const fn new` (`:24`) and no `#[non_exhaustive]`. **84 `unsafe` blocks** in leto and every array in kwavers/CFDrs/ritk/gaia/coeus rest on its invariant; safe downstream code can construct an out-of-bounds layout today. | [major] | Zero `pub` fields on `Layout`; a validating `try_new`/`TryFrom` is the only construction path; adversarial tests per invalid class return a typed error; all five consumers build **The oracle in this row would not have fixed the defect it was filed for, and that is the finding.** Sealing `Layout` closes nothing on its own: a `Layout` carries no pointer and no length, so "fits the buffer" is not a property it can express. A proof-of-concept written before any code change had safe Rust read ~4 KiB past a 16-byte buffer **using a `Layout` from the validating `c_contiguous` constructor** - `c_contiguous([1000])` is perfectly self-consistent and simply does not fit a 4-element buffer. The real breaks, fixed in leto `580c859`: `ArrayViewMut`'s four `Index`/`IndexMut` impls dereferenced a computed offset with no `offset < len` check their `get`/`get_mut` siblings perform, and `trace`, `kron`'s strided branch and `matmul`'s `copy_back_to_out` reached `get_unchecked`/raw writes unvalidated - the last an operand mixup, validating the *scratch* view while writing through the caller's `dst`. The premise's other half was also off: the 84 unsafe blocks are exact, but about half are unrelated to layout and the layout-dependent ones rest on `validate_storage_len` at constructor/dispatch sites, not on `Layout`'s invariant. **The consumer list was wrong in both directions** - CFDrs, ritk and gaia have zero `leto::Layout` usage and were never affected; hephaestus (~270 sites), athena and apollo were, and none was listed. Sealing still shipped and still earns its place, making `size`/`min_max_offsets`/`offset_of` total: private fields, `#[non_exhaustive]`, `try_new`/`TryFrom` the only public path, validated `Deserialize`, and no struct literal anywhere outside a `pub(crate) from_parts_unchecked` serving ~15 internal derivations in hot iterator bodies. 27 adversarial tests each assert a typed `LetoError` with a positive control; the original PoC is pinned as three `#[should_panic]` regressions. **miri 182/182 clean.** `cargo semver-checks` reports 4 major breaks, declared in the CHANGELOG migration recipe and ADR 0025, not hidden. **Remainder filed, not half-done:** `ArrayView::new`/`ArrayViewMut::new` stay safe and non-validating, so today's safety is an enumeration over the current tree rather than a type-system guarantee - converting them to `unsafe fn new_unchecked` is 69 call sites across 7 repos and a second `[major]`, recorded in ADR 0025. |
| ATLAS-KWAVERS-REAL-COMPUTE-028 — **closed 2026-08-15** | *(already open — now with a fifth site and exact locations)* Five production paths return their input unchanged, three under real citations: `mixed_domain.rs:158-170` and `:219-231` (Hamilton & Blackstock 1998), `kzk_solver_plugin/solver.rs:301-310` (Jing et al. 2012), `transfer_learning/learner.rs:137-143` (live at `:43`), and newly found `kwavers-math/src/simd/interpolation_ops.rs:129-141` — an `avx2` `#[target_feature]` fn with a 5-line SAFETY comment whose body calls the scalar function. | [major] [arch] | `rg "Ok\(field\.clone\(\)\)" crates/kwavers-solver/src` → 0; each site has a differential/analytical test that **fails when the body is reverted to the clone**, demonstrated in the PR **Closed by deletion, because none of the five was a production path.** A repo-wide search over every `.rs` including examples, benches and tests, plus the plugin catalog, found **zero callers** for any of them - so there was no live call site whose physics to implement, and writing physics into uncalled code would have added ungrounded derivations rather than fixing a defect. A sixth unlisted identity mock (`DomainAdapter::adapt`, citing Ganin 2016 and Raissi 2019) went with them, and two citation attributions in this row were wrong. Removed in kwavers `7bf8eca48`. `mixed_domain` was deleted whole rather than repaired: its *remaining* method computes `k = 2*pi/(c*dt)` independent of the spectral index, so it applies one constant phase to every k-bin - a scalar attenuation dressed as an angular-spectrum propagator - and fixing only the two clones would have left that beside them. The AVX2 site was deleted rather than vectorized: its `#[target_feature]` body called the scalar function, making its five-line SAFETY comment false, and the dispatch was dead anyway on AVX-512 hosts. **The falsification evidence this oracle demands cannot exist and was not faked** - with no caller there is nothing to observe the difference, and no test was written that would have passed with the mock in place. nextest 6136/6136. **The live defect these mocks were sitting next to is filed as ATLAS-KWAVERS-KZK-LINEAR-080.** |
| ATLAS-CONSUS-PARSE-LIMITS-035 | HDF5 parse paths reachable from `Hdf5File::open` allocate on unbounded file-supplied lengths — `btree/v2.rs:685,761` (`with_capacity(total_records as usize)`, u64 straight from the header), `dataset/chunk.rs:110,126,166`, `datatype/compound.rs:336,522,550`, `consus-fits/src/table/data.rs:153,187,188` — and `parse_datatype_inner` (`datatype/compound.rs:80→329→360→446`) recurses with **no depth parameter anywhere in the chain**, so a nested compound overflows the stack (uncatchable abort). `try_reserve` appears once in the whole tree. | [minor] | A `total_records = u64::MAX` header, an oversized chunk size, and a 10 000-deep nested compound each return a typed error, not a panic or abort; each test fails on the parent commit |

The removed rows are closed findings, retained in the landed table above: Themis
`ATLAS-THEMIS-TOKEN-032`, Mnemosyne `ATLAS-MNEMOSYNE-ALIAS-033`, Apollo
`ATLAS-APOLLO-FAKEGEN-036`, and Eunomia `ATLAS-EUNOMIA-F64-SPECIALS-062`,
`ATLAS-EUNOMIA-SUBBYTE-ORD-063`, and `ATLAS-EUNOMIA-ACCUMULATOR-064`.
Their current provider source and evidence are not active Tier 0 work.



## Tier 3 — mechanical floor and stack hygiene

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-LINT-FLOOR-054 — **closed 2026-08-14** | **17 of 25 members have no `[workspace.lints]`.** Where a floor is declared it is then nullified: CFDrs correctly inherits `unwrap_used`/`print_stdout`/`print_stderr`/`dbg_macro` at deny in all 12 manifests, against **288 crate-level `#![allow]` and 5 `#[expect]` repo-wide, none with a ratchet reason** — which is why 402 library print sites survive a deny. coeus has 117 allow lines with **zero** `reason=`. | [patch] | **Complete: 25 of 25 members deny `clippy::pedantic`, none at `warn`, none without** - from zero at sweep start. Every floor carries a grouped allow-list recording total and production counts per class, so debt is measured rather than tolerated; blanket crate-level `#![allow]` is **zero stack-wide** (CFDrs 299 -> 0, apollo 47 -> 0, ritk 34 -> 0, coeus 22 -> 0, kwavers 13 -> 0), and surviving suppressions are `#[expect(..., reason = "ratchet <id>")]` that expire with their last site. **Two premises in the outcome column were wrong:** several "missing `[workspace.lints]`" members are single-package repos where a package-level `[lints]` table is the only correct home, and most members' CI already passed `-D warnings`, so `warn` was already a hard floor there - the promotion mattered locally, not in CI. **The exception was CFDrs, which had no clippy step in CI at all**, plus ten crates carrying in-source `#![warn(clippy::pedantic)]` that overrides manifest `--allow` flags and made its allow-list inert; a `lint` job was added in `c9073496`. **The floors paid for themselves in real defects:** a reachable hang in kwavers' driver manifest parser (unbounded `(len()..)` range, verified by falsification - reverting the fix times the new regression test out at 60s), reachable `Instant` panics in kwavers' clinical safety monitor and moirai's registry, an overflowing manual ceiling division in hermes, case-sensitive extension matching in hephaestus (`.DLL`) and kwavers (8 sites routing `.NII`/`.DCM` to "unsupported"), 353 dead imports in apollo behind a blanket allow, three ritk `#[expect(dead_code)]` masking genuinely dead production code, four discarded `SolveReport`s in CFDrs, and a CFDrs test file holding two empty `#[ignore]`d functions. **Three mechanics worth reusing:** a file-level `#![expect(clippy::unwrap_used)]` in a `src/` file whose unwraps are all `#[cfg(test)]` fails as `unfulfilled_lint_expectations`, so those need `#![cfg_attr(test, expect(...))]`; a member with its own `[lints.rust]` table cannot also inherit; and publishing a member's `[lints] workspace = true` before the root table exists breaks manifest parsing for the whole stack through the overlay. Census at `warn`, never `deny` - at `deny` clippy aborts each crate on its first error and undercounts. |
| ATLAS-COEUS-LINT-RATCHET-097 — **closed 2026-08-17 — already merged** | The stale floor finding is closed by Coeus PR #334, merged at provider default `a8ea12eb`. The production conformance scan at the lint-ratchet head reports `allow_sites=0`; exact-head hosted Backend parity run `31989331059` passes, and Atlas already records `a8ea12eb`. The stale lane claim is released without source edits. | [patch] | Production `#[allow(...)]` residue is zero at the merged default; provider and Atlas exact-head evidence is recorded. |
| ATLAS-CACHE-FORK-055 | **Mostly stale.** Only 2 trivially small target dirs remain (athena 1.7 MB, harmonia 1.4 MB — mdbook output, not build caches). All other 23 repos have zero target directory. Deleted in this sweep. | [patch] | Closed — 58.9 GB fork state reduced to near-zero |
| ATLAS-GITLINK-DRIFT-056 | **24 of 25 submodules are checked out off the commit atlas records** (only gaia matches), and 11 sit on `codex/*` or feature branches. **The drift direction is uniform: the recorded gitlinks are AHEAD of the working trees** — athena's gitlink is 3 commits ahead of HEAD, harmonia's 2, horae's 6, hyperion's 5, and leto's tree is 17 behind both `origin/main` and its pin. These are members behind atlas, not atlas behind members, so every local verification run tests superseded state. Two sub-cases need opposite handling: athena and harmonia sit on branches with **zero** unique commits (exhausted, deletable — re-point to `main`), while horae and hyperion each carry small real deltas that are green and mergeable now, hyperion's including an actual parallel-test-race fix (`35006fd`). | [patch] | Per member: exhausted branches deleted and re-pointed to `main`; real deltas merged and the gitlink advanced; a committed check fails when HEAD ≠ gitlink without a recorded reason |
| ATLAS-ROOT-SPRAWL-057 — **closed 2026-08-14** | Meta-root held 7 unfiled report-genre files. **Not all are deletable** — `scripts/check_mdbook_links.py:15,53,66,99,181,194,565` and `fix_link_depth.py:2` cite `MDBOOK_*.md` as the normative Pattern A–F taxonomy, `scripts/tests/test_smoke_fixture.py:34,46` reads `parity_artefacts/smoke_test_filters` as a live fixture, and `.github/workflows/docs.yml:19,20` path-filters both. `PATH_DEP_AUDIT_001_ENTRY.md` is a duplicate of the board entry at `backlog.md` with 367 unique lines that must merge first. | [patch] | All four clauses verified. The tracked root manifest is now exactly `README.md`, `CHANGELOG.md`, `backlog.md`, `checklist.md`, `gap_audit.md`, `Makefile`, `pytest.ini` and the four dotfiles — no report-genre file remains. The mdBook taxonomy lives under `docs/mdbook/` with zero `MDBOOK_` citations left in `scripts/*.py`. The smoke fixture moved to `scripts/tests/fixtures/smoke_test_filters/` in `42d1607`, all seven citations re-pointed (two test constants, four `docs.yml` sites, and the prose in the fixture README, its two chapters, and `docs/mdbook/detector-parity.md`); the move broke the fixture's own `../../../` root-relative links and the test caught it, re-depthed to `../../../../../` with each of the four targets resolved on disk. `pytest scripts/tests/` 183 passed / 74 subtests, the workflow's verbatim command reports `FILE_MISSING : 0`, and the pre-commit hook's stack-wide check passed all 24 books at zero. **Deliberately out of scope:** the rest of `parity_artefacts/` is the parity stream's archive, cited from two `docs/mdbook/` chapters, and this board already records its disposal as that stream's closure increment rather than a coordinator's unilateral commit. |
| ATLAS-ADR-GOV-058 — **closed 2026-08-14** | **Corrected against `scripts/adr-index.py check`, which is authoritative — my earlier grep-based count was wrong.** The meta-repo's own ADRs and index are **clean**. At the merged provider defaults, **9 of 24 member indexes are stale or missing**; remaining member anomalies include non-canonical status headers, duplicate or missing ADR numbers, and index drift in Asclepius, Coeus, Gaia, Harmonia, Helios, Horae, Kwavers, Melinoe, Mnemosyne, and Tyche. The generator already exists and reports all of this; what is missing is the burn-down plus a CI gate on `check`. Hyperion, Iris, Proteus, Aequitas, Horae, Eunomia, Themis, Ritk, Leto, Hephaestus, and Apollo slices are landed as their corresponding `ATLAS-ADR-GOV-058-*` entries; the remaining member anomalies stay open. | [patch] | **All four clauses met.** 62 anomalies burned to 0 — 27 status casing, 27 non-canonical status, 7 duplicate number, 1 missing status. (The "9 stale/missing indexes" in the outcome column did not reproduce: `check` already exited 0 on that class.) `check` now exits 0 with **zero stdout**, verified independently of the burn-down agent; `generate` run twice more is a silent no-op; an independent scan finds no repeated ADR number in any member; `scripts/tests/test_adr_index.py` still passes. Landed as `3775ac7` (asclepius), `d30a167` (harmonia), `3db1090` (helios), `7e27727` (tyche), `7d671c0e` (coeus), `f0cc9c9a8` (kwavers), `be2d19d` (mnemosyne); apollo's two were fixed by a peer mid-run. The two supersessions were decided per file, not by rule: kwavers 037 was **rewritten in place** because grepping ADR 040 for `FeatureNotAvailable`/`SimulationRunner`/`runner` returns zero hits, so 037 still solely owns the no-zero-arrays adapter contract; mnemosyne 0002 was **deleted** because ADR 0003 removes `WgpuStagingBackend` outright and no symbol from it survives anywhere in `.rs`. CI gate added to `atlas-conformance.yml` in `af3532e`, gating on exit code **or any stdout** — `check` exits 0 for duplicate numbers and bad statuses, so an exit-code-only gate would have caught none of the 62. **Two findings filed rather than fixed:** `repos/moirai` has no `docs/adr/` directory so the checker never scans it at all (see ATLAS-CONSUS-ADR015-076, respecified), and the pre-existing ratchet step's `… \| tee` masked its own exit status, fixed in the same commit. |
| ATLAS-KS9-SUPERSEDED-059 — **closed 2026-08-14** | `backlog.md` `[KS-9]` stood **done** asserting the decision to *retain* `hephaestus-metal`, superseded by Accepted ADR 0047 which retires it — the board asserted both positions. Its recorded rationale ("would be a breaking public-surface change") was also a prohibited tiebreaker. Separately: ATLAS-ARCH-011 needs **nothing from hephaestus** — removal was executed and verified green, then reverted solely for `repos/coeus`; it unblocks via ATLAS-SUBSTRATE-002. | [patch] | Both oracle clauses verified met at `repos/hephaestus` HEAD (committed, not working-tree state): `backlog.md:3187` carries the dated **Revision 2026-08-14** note pointing at ADR 0047, and additionally records that the crate never owned a native Metal path — `MetalDevice` is a newtype over `WgpuDevice::try_metal` with zero native Metal API calls across 5 449 lines — and that the breaking-surface rationale is a prohibited tiebreaker. ATLAS-ARCH-011's dependency reads `ATLAS-SUBSTRATE-002` with the blocker narrative naming `repos/coeus`/`coeus-metal`; hephaestus appears nowhere as a blocker. |

### ATLAS-APOLLO-PRINT-098 — **closed 2026-08-17 — premise false** [patch]

The hosted `apollo/print_dbg: 6 -> 9` finding is not an Apollo library defect.
The eight call sites are benchmark executable targets, and
`BenchmarkSuite::emit` is their shared output boundary; deleting it would break
real benchmark artifacts. The Atlas scanner classifies only `main.rs` and
`bin/` paths as executable, so it incorrectly counts `benches/` output as
production library output. No Apollo source change is authorized by this
finding; the instrument correction is tracked separately.



## Tier 2b — small domain repos (athena, harmonia, horae, hyperion)

These four are the cleanest in the stack on every mechanical axis — zero `dyn`
in any `src/`, zero fake-generic casts, zero `todo!()`, zero non-test `unwrap`,
`unsafe_code = "forbid"` and `missing_docs = "deny"` throughout, and both
LICENSE texts present and matching the manifest in all four. The findings are
about documentation truth and numerical evidence, not debt.

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-ATHENA-UNDOC-066 — **closed 2026-08-14** | **athena ships two undocumented solver families.** BiCGStab (575 lines) and LSQR (487) are implemented and publicly re-exported from `athena-core/src/lib.rs`, yet appear **zero times** in the README, whose headline (`:5`) calls PCG and GMRES "its complete vertical contracts". Compounding it, the architecture tree names a crate that does not exist (`:62` `athena-wgpu` vs the real `athena-hephaestus`), a feature that does not exist (`:71` `wgpu` vs the real `accelerator`), and asserts a 500-line ceiling (`:69`) that BiCGStab breaks. | [patch] | `rg 'athena-wgpu' README.md` → 0; README documents BiCGStab and LSQR; the line-count claim is removed or true per `wc -l` Verified 2026-08-14 at athena HEAD: `rg 'athena-wgpu' README.md` = 0, BiCGStab and LSQR both documented, and the line-count claim now names `bicgstab/algorithm.rs` (575 lines) as the sole stated exception. |
| ATLAS-BOOK-PLACEHOLDER-067 — **closed 2026-08-14** | **Placeholder chapters are shipped as books.** athena has 6 chapters and harmonia 3 — every one is the 3-line string `*Chapter prose deferred.*`. A placeholder chapter is documentation's mock: a chapter exists when its teaching content does. Separately, the shared Pages callers default `mdbook-test` to `false`, so books without a compiled-sample gate can rot. | [patch] | No `Chapter prose deferred` anywhere; athena and harmonia now contain source-grounded prose. The placeholder half is closed: athena's six stubs plus a seventh LSQR chapter landed in `39b6f0b`, harmonia's three plus its two-line introduction in `10e15ae`, and the stack scan is zero. Sample-gate work remains tracked independently in ATLAS-PUB-005; callers are not represented as tested unless they pass `mdbook-test: true`. |
| ATLAS-ATHENA-KRYLOV-070 — **closed 2026-08-14** | `gmres/workspace.rs:15-16` holds the Arnoldi basis as `Vec<B::Vector>` — on Leto that is `2·RESTART+1` scattered allocations, while every scalar array in the same struct is already flat (`hessenberg` is one `Vec<Scalar>` with an index fn). The only pointer-scattering instance found across these four repos. Allocated once at construction and natural per-buffer on WGPU, so this is a CPU-side layout defect, not a hot-loop allocation. Also: non-convergence returns `Ok(SolveReport)` with `Termination::MaxIterations` rather than a typed error, `SolveError` carries no residual history, and stagnation/divergence detection is absent entirely. | [minor] | `Vec<B::Vector>` gone from `gmres/workspace.rs` behind the existing `KrylovBackend` seam; the existing allocation-stability and f32/f64 contract tests unchanged and green; a stalling operator yields a `Termination::Stagnated`-class value with non-empty history Closed 2026-08-14. The layout half landed earlier in `d3a4afe` behind `KrylovBackend::VectorBlock`; the only remaining `Vec<B::Vector>` in `gmres/workspace.rs` is a doc comment explaining the type is no longer that. The correctness half landed in `39b6f0b`: `Termination::Stagnated`/`Diverged` detected per restart cycle against a derived floor `sqrt(n)*eps*||b||`, with the two rejected sub-requests argued in ADR 0004. |



## Deferred with a recorded reason

- **ATLAS-PRIVACY-NAMING-1** stays open and unchanged. `repos/leoneuro-rs` is a
  separate organisation's repository holding local commits `1b71a79` and
  `50bfcd9` on a branch whose remote is **gone**, so it carries unique unpushed
  work and must not be deleted. It is correctly gitignored; the violation is
  that it is *named* in board items, which is a rewrite of existing entries, not
  a tree change.
- **Detector residuals.** The `declared_cfg_test` fix does not yet recognise
  test modules gated through a `#[cfg(feature = "…")]` wrapper around a
  `#[cfg(test)]` block. consus still reports 334 production unwraps against an
  audited estimate near 34, so a second refinement pass is warranted before that
  number drives any burn-down.



## Session 17 closure (2026-07-23) — ATLAS-LETO-OPS-SPARSE-LU-001 → ✅ closed

- Owner: atlas-meta coordinator (codex agent); status flipped todo → ✅ closed.
- Outcome: real CSC sparse LU + partial-pivoting numeric phase in leto-ops
  landed at leto `origin/main` `687b670` via PR #74 squash-merge
  (`refactor(leto-ops): Remove ndarray/nalgebra, native iterative solvers
  (LETO-NDARRAY-BOUNDARY-1) (#74)`).
  The PR diff (41 files) bundled the ndarray/nalgebra dev-dep removal (peer
  origin-main HEAD `9346413` declared no production deps on ndarray/ndarray-rand/
  nalgebra; only parity examples consumed them) AND the in-place upgrade of
  `SparsLuSolver` to the real algorithm class.  Public surface preserved:
  `SparseLuSolver::solve_view`, `CscMatrix`, `CsrMatrix`, `CooMatrix`, and the
  re-exported `factor_numeric` / `factor_symbolic` / `NumericLu` API paths.
- Algorithm spec (matches ADR 0031 Option A): symbolic factorization is the
  sequential left-looking Gilbert/Peierls reach over CSC, computing the
  static L/U pattern (L rows strictly `> j`, U rows `≤ j` per column j) under
  natural column ordering for v0.40.0; numeric factorization is the
  slot-indexed left-looking phase with partial-pivoting row swaps against
  `row_perm[slot] = original row` (matches the dense
  `LuDecomposition::pivots` convention so downstream CFDrs
  `DirectSparseSolver` composes unchanged); solve =
  `P·A·x = L·U·x = P·b` ⟺ forward sub `Ly = Pb` then back sub `Ux = y`.
- Density-gated dispatch (per ADR 0031): `SparseLuSolver` carries a
  `small_switch = 32` and `density_threshold = 0.1` pair; small or near-dense
  matrices route to a dense-fallback path; large sparse matrices route to
  the new symbolic→numeric sparse path.
- Verification evidence (Windows ucrt64, rustc 1.95.0, eunomia
  https://github.com/ryancinsight/eunomnia#f6cd644b):
  - `cargo check -p leto-ops --tests` ✅ clean (Finished in 2m 15s).
  - `cargo nextest run --no-fail-fast -p leto-ops` ✅ 339/339 pass in 3.17s
    (well under the 30s slow-timeout hard cap; no threshold relaxation, no
    test shrinkage).
  - `cargo test --doc -p leto-ops` ✅ 11/11 pass in 54.64s.
  - Sparse-LU-targeted suite ✅ 16/16 pass:
    `factor_poisson_1d_laplacian_n16_roundtrip` 0.064s,
    `factor_banded_5_diagonal_n32` 0.026s,
    `factor_random_sparse_n64_diff_dense` 0.252s,
    `sparse_path_routes_correctly_for_tridiagonal_n64` 0.269s,
    `factor_f32_generic` 0.051s,
    `singular_matrix_yields_storage_error` 0.240s,
    `solver_is_generic_over_f32` 0.071s, plus 9 inherited solver-routing tests.
  - Differential cross-check: `factor_random_sparse_n64_diff_dense` asserts
    value-semantic equivalence between sparse and dense LU on a randomly
    populated 64×64 matrix at residual < ε (not existence-only).
- Residual / not-covered-in-this-closure (per ADR 0031 Consequences):
  (a) AMD (Approximate Minimum Degree) ordering deferred to
      `ATLAS-LETO-OPS-AMD-ORDERING-001` [patch] — natural ordering ships for
      v0.40.0; AMD ~300-line impl exceeds this session's context budget and
      a partial implementation would risk numerical defects per ADR 0031
      "AMD scope risk".
  (b) CFDrs `DirectSparseSolver` migration to the landed
      `SparseLuSolver::solve_view` is the follow-up
      `ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001` — depends on aequitas pin
      coherence and a leto bump at CFDrs; not in scope for Session 17.
  (c) Local clippy `-D warnings` against the FULL leto workspace cannot run
      clean on this coordinator's working tree because peer's untracked
      uncommitted sibling verticals
      (`crates/leto-ops/src/application/{diff,interpolation,quadrature}/`)
      contain `assign_op_pattern` and `complex_type` lint failures. PR
      #74's CI status (both `recurseml/analysis` post-push and
      `CodeRabbit`) was CLEAN before squash-merge; the merged commit's
      leto-ops scope is clippy-pedantic clean modulo peer-held untracked
      files not in the merged tree.
- Concurrent-agent record: peer session active on the same `codex/leto-real-sparse-lu`
  working tree during this closure, creating untracked siblings for diff/
  interpolation/ quadrature operation families (ts 21:53-22:02).  Per
  `concurrent_agents` assist-ladder rule: peer files skipped, not collided with.
  Coordinator scope-strictly-committed only `sparse/lu_numeric.rs` and
  `sparse/lu_symbolic.rs` (doctest-fixture correction + rustfmt-only reflow of
  pre-existing `for ... take().skip()` chains); peer's `Cargo.{lock,toml}`,
  `lib.rs`, `application/mod.rs`, `application/linalg/mod.rs`, and the new
  `diff/`/`interpolation/`/`quadrature/` untracked modules remained unstaged.
- Gitlink-state: atlas-meta's `repos/leto` gitlink advances to
  `687b67079c4e122264c17fd2eb3fd850d876a39f` in the same commit that
  synchronizes this backlog entry and ADR 0031's status flip.
- Refs: backlog.md#CFDRS-PERF-SLOW-001 (Session 13 upstream-cause filing),
  backlog.md#ATLAS-LETO-OPS-SPARSE-LU-001 (this item), ATLAS-LETO-OPS-AMD-ORDERING-001 [patch] (new follow-up below).



## Session 17 partial closure (2026-07-23) — ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 → partial closure

Coordinator (Session 17 follow-up) landed the doc-comment migration of
`crates/cfd-math/src/linear_solver/direct_solver.rs` to reflect the
real CSC sparse LU per ADR 0031 + leto origin/main `687b670` (PR #74
squash-merge).

- **CFDrs PR**: ryancinsight/CFDrs#316 — title
  "docs(cfdrs-math): Migrate direct_solver doc to ADR 0031 real sparse LU
  (ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 partial)" — squash-merged as
  `5ac713b3fdf5fd45dbd295f3887c6f58b88c63f8` on CFDrs origin/main at
  2026-07-24T03:43:21Z.
- **Diff surface**: +25/-6 in
  `crates/cfd-math/src/linear_solver/direct_solver.rs` — module doc
  rewrite + `ordering` field doc correction + convergence composition
  with peer's pending `..Default::default()` adaptation to the
  upstream `SparseLuSolver` struct expansion (`small_switch` +
  `density_threshold` fields per ADR 0031).
- **Doc claim corrected**: the pre-merge module doc claimed the
  atlas-native solver was "backed by dense partial-pivoting LU" — that
  misnomer was filed for the Session 13 `CFDRS-PERF-SLOW-001` timeout
  closure root cause; it is now stale per ADR 0031 since leto PR #74
  landed the real CSC sparse LU (symbolic = sequential left-looking
  Gilbert–Peierls reach per Davis 2006 §6.1; numeric = slot-indexed
  left-looking with row_perm[slot]=original-row matching dense
  `LuDecomposition::pivots`; density-gated dispatch `small_switch=32`,
  `density_threshold=0.1` in `SparseLuSolver`).
- **Safety net preserved**: the CFDrs-side `dense_threshold=1024`
  retry at `DirectSparseSolver::retry_dense_or_error` is preserved as
  the orthogonal catch case for the `max_size`-cap + small-`n`
  user-intent safety net; NOT a duplicate of the upstream internal
  fallback (which handles only `NumericalBreakdown` mid-sparse-path).

Gitlink: atlas-meta `repos/CFDrs` advances from `1b2c901` to
`5ac713b3` (submodule local working tree left at local main HEAD
`354266c0` with peer's WIP unmodified per concurrent_agents
preservation; the gitlink records the squash-merged origin/main tip).

Refs: backlog.md#ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 (above; this
entry closes the partial slice),
docs/adr/0031-leto-ops-real-sparse-lu.md (atlas-meta, Accepted),
leto PR #74 squash-merged as `687b670` (origin/main),
CFDrs PR #316 squash-merged as `5ac713b3` (origin/main).



## Session 18 closure (2026-07-24) — ATLAS-HELIOS-BOOK-001 → ✅ closed

- Owner: peer-helios (delivered the book across multiple PRs landing at
  `origin/main 433ddb6`); atlas-meta coordinator (this Session 18
  closure records the verification matrix and flips the backlog status
  from `todo` to `✅ closed`). No member-repo file edits by this agent —
  per `concurrent_agents` disjoint-scope primitive, peer-helios owns
  `repos/helios/...` files.
- Outcome: full multichapter mdBook at `repos/helios/docs/book/`, mapped
  onto the canonical kwavers Domain-book contract (governing equations
  → numerics → API mapping → worked examples with deterministic 
  figures). Spec verified via local inspection of `origin/main`:
  - `docs/book/SUMMARY.md` manifest: 8 Parts (I Foundations, II CT
    Imaging, III Dose, IV Treatment Delivery, V End-to-End Clinical
    Workflows, VI GPU Acceleration, VII Validation, VIII Atlas Stack
    Integration Migration Reference) across 37 chapters + 4 appendices
    (A Dependencies, B Glossary, C API Reference, D Changelog) +
    `BOOK_ORGANIZATION.md` forward roadmap.
  - 18 example markdown files under `docs/book/examples/` span the
    chapter families (validate_foundation_units, voxel_grid_construction,
    photon_attenuation, radon_sinogram, fbp_reconstruction, sirt_
    reconstruction, mvct_registration, compton_physics, collapsed_cone_3d,
    dvh_analysis, dvh_optimization, gamma_index, tomotherapy_workflow,
    linac_dose_accumulation, adaptive_rt_workflow, gpu_attenuation_
    projection, validation_regression, validation_clinical).
  - 7 deterministic SVG figures under `docs/book/figures/`
    (architecture_stack, ct_calibration_curve, dose_slice_heatmap,
    dvh_curve, helical_mlc_fluence, photon_attenuation_depth,
    radon_sinogram_disk) + `MANIFEST.json` byte-determinism registry.
  - `docs/book/book.toml` configured with `/helios/` site-url + MathJax.
  - `README.md` carries the canonical `[Published Helios book]
    (https://ryancinsight.github.io/helios/)` link.
- Acceptance verification (evidence match per ATLAS-HELIOS-BOOK-001 L2506–L2509):
  - (a) `mdbook build docs/book` exit 0 — verified locally via
    `mdbook v0.5.4` on the helios checkout at `433ddb6`; HTML written
    to `target/book/helios/index.html`. ✅
  - (b) SUMMARY.md entries each map to a committed chapter stub with
    H1 (`# Chapter N — …`) + `## Further Reading` backlink. Verified
    by sampling chapters across all 8 Parts (foundations Part I,
    dose_attenuation Part III, planning_mlc Part IV,
    workflow_tomotherapy Part V, gpu_dose Part VI, migration_arrays
    Part VIII). ✅
  - (c) Book deploys to GitHub Pages through the artifact flow.
    `repos/helios/.github/workflows/book-pages.yml` uses
    `actions/upload-pages-artifact@v4` → `actions/deploy-pages@v4`,
    with `pages: write` + `id-token: write` on the `deploy` job, and
    deploy gated on `github.event_name != 'pull_request'` (main-only). ✅
  - (d) Cross-book CI invariant gate (atlas-meta `.github/workflows/
    docs.yml` `docs-invariant` job runs dead-link detector +
    `mdbook build` on all three books) — green. ✅
- Helmholtz-style residual / not-covered-in-this-closure (peer-coordinated,
  NOT claimed by Session 18 — coordinator cannot edit member-repo
  workflow files per `concurrent_agents` disjoint-scope primitive):
  (a) ATLAS-PUBLISH-001 residual — `repos/helios/.github/workflows/
      book-pages.yml` runs `mdbook build` but does NOT run `mdbook test`.
      engineering_gates publish-pipelines mandate the mdbook test gate
      for the book-deploy workflow (ATLAS-PUBLISH-001 acceptance item).
      Peer-helios owns the workflow file; filed as a peer-coordinated
      sub-slice of ATLAS-PUBLISH-001.
  (b) ATLAS-BOOK-002 residual — the Part VIII Atlas-Stack Integration
      (Migration Reference) section in `repos/helios/docs/book/SUMMARY.md`
      (chapters 26–37) is in-scope for the cross-book migration-content
      evictionunder ATLAS-BOOK-002 (peer-kwavers holds the active
       eviction branch). Filed as a helios-side peer-coordinated
      sub-slice of ATLAS-BOOK-002.
  (c) Atlas-meta `repos/helios` gitlink stays at `433ddb6` (== `origin/main`).
      No gitlink advancement is required or performed by this closure
      — causal chain: peer-delivered → published on origin →
      coordinator verifies → backlog status flips. No regression
      surface.
- Concurrent-agent record: prior-session coordinator work committed as
  `04dee5c "docs(atlas): Close Aequitas metric audit gaps"` advanced the
  book-CI verification slice (now `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER`
  status `in-progress` after HELIOS PR #31 root-cause analysis). This
  Session 18 closure is disjoint in scope from that WIP slice — it touches
  only the `ATLAS-HELIOS-BOOK-001` section + this new Session 18 closure
  section, leaving the prior-session WIP + `ATLAS-CFDRS-COEQ-BLOCKER-1`
  + `ATLAS-PARITY-HTML-RETIRE-1` and all uncommitted peer-WIP untouched.
- Gitlink-state: atlas-meta's `repos/helios` gitlink remains at
  `433ddb6` — already equals `origin/main` so this closure makes no
  `backlog.md`-internal gitlink advancement. Diff signature: `backlog.md`
  only (no `.gitmodules`, no `gap_audit.md`, no member-repo path).
- Refs:
  - backlog.md#ATLAS-HELIOS-BOOK-001 (this closure)
  - backlog.md#ATLAS-BOOK-002 (kwavers master eviction scope — residual filed, not closed)
  - backlog.md#ATLAS-PUBLISH-001 (mdbook test gate peer-coordinated — residual filed, not closed)
  - helios `origin/main 433ddb6` `docs/book/` +
    `.github/workflows/book-pages.yml` + `README.md` (artifact evidence)
  - https://ryancinsight.github.io/helios/ (published book URL)



## Session 19 closure (2026-07-24) — ATLAS-AEQUITAS-001 gitlink advance + criterion-gate continuous verification

- Owner: atlas-meta coordinator (this Session 19 closure records the
  gitlink advance and the criterion-gate re-audit). No member-repo
  files touched per `concurrent_agents` disjoint-scope primitive.
- Outcome:
  (1) ATLAS-AEQUITAS-001 above — atlas-meta gitlink for
      `repos/aequitas` advances from `b86a55d` to `19fc384` (origin/main
      HEAD). Three peer commits, all CI-green via `gh api`. Linear
      advance (no merge-bubble), `[minor]` additive.
  (2) ATLAS-BENCH-BUDGET-001 continuous-verification re-audit of the
      meta-owned `tools/criterion-regression` tool:
      - `cargo check --all-targets` Finished clean.
      - `cargo clippy --all-targets -- -D warnings` clean (pedantic +
        `clippy::unwrap_used`).
      - `cargo fmt --check` clean.
      - `cargo nextest run --no-fail-fast` 21/21 pass (max 0.451s;
        well under the 30s slow / 60s terminate budget).
      - `cargo test --doc` 2/2 pass.
      The tool remains green for peer consumption; the residual
      full-stack sweep (164 benches across moirai/CFDrs/kwavers/hermes/
      ritk + per-repo CI wiring per `ATLAS-BENCH-BUDGET-001`) stays
      deferred until the live peer scopes integrate.
  (3) Stale-claim sweep + origin-sync-first per `concurrent_agents`:
      all five drifted gitlinks (CFDrs, coeus, aequitas, consus, kwavers)
      audited via authenticated `gh api` panel dispatched as a parallel
      subagent panel inspecting per-repo states via `git ls-remote`,
      `git --git-dir`, and authenticated `gh api` check-runs / status
      queries. Session 19 takes the single evidence-backable advance
      (aequitas); the other four are correctly rejected above with the
      recorded reason.
- Concurrent-agent record: peer-helios at `origin/main 433ddb6`
  (unchanged from Session 18 closeout). Peer-CFDrs at `origin/main
  99318bc` (advanced past Session 18 but CI red on check-figures job —
  same `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1` residual; the Venturi metric
  closure `ATLAS-CFDRS-PERF-045` already recorded separately on main).
  Peer-mnemosyne already integrated per Session 18's gitlink advance.
  Peer-aequitas freshly advanced now. Other peer activity: peer-leto at
  `origin/main 687b670` (stable — sparse LU landed Session 17). Peer
  kwavers eviction remains local-only (PR #325 DIRTY, eviction branch
  unpushed). Stale-claim sweep used the actual peer's published origin
  + `gh api` for CI conclusions; no speculative merges or assumptions
  about peer intent beyond their published state.
- Diff signature: `repos/aequitas` gitlink only (index-staged) + this
  backlog.md section. No `.gitmodules` URL change, no `gap_audit.md`
  edit (currency-current via Session 18 closeout), no member-repo files,
  no `tools/*` build (the continuous-verification re-audit ran
  read-only against the existing tool tree and produced no source delta).
- Refs: backlog.md#ATLAS-AEQUITAS-001 (the gitlink advance this closure
  records), backlog.md#ATLAS-PUBLISH-001 (mdbook test gate per-repo
  peers — unaffected), backlog.md#ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1
  (CFDrs advance blocker), backlog.md#ATLAS-LETO-OPS-AMD-ORDERING-001
  (leto peer work — peer-held, unclaimed here),
  backlog.md#ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 (CFDrs cfd-3d
  re-profile — partial closure, peer-held).
- Coordinator exhaustion reached after this advance: no further
  actionable gitlink atlases capable of evidence-backable advance at
  this session; all `in-progress`/`todo` items either peer-held
  (Codes `/root` peer) or peer-blocked on member-repo source files,
  per `concurrent_agents` disjoint-scope primitive. Next wake triggers
  documented at each rejected-advance entry above.



## Session 27 closure (2026-07-27) — peer-coordinator ATLAS-MODALITY advance + the persistent gitlink defect set

Re-oriented against `origin/main` at session open. The standing "next action"
from the Session 26 handoff (append Session 26 closure to `backlog.md`) had
already landed under peer-coordinator attribution: commit `1da7cea docs(pm):
Close GMRES fork ports; record athena zero-consumer evidence` wrote the
`## Session 26 closure` section at L4785. The math-SSOT audit content I drafted
in Session 26 also survived intact at L4542 (`ATLAS-MATH-SSOT-CONSOLIDATION-1`)
and the audit-pattern template in `gap_audit.md` at L5178 — peer commit
`fad8c9e` reused my commit subject but its diff was a CFDrs gitlink advance;
no content clobber. Same attribution-absorption pattern as Session 25
`e519928`; no remediation needed because the content is correct DoR-level PM
state.

### Peer-coordinator landings during the inter-session gap (10 commits, b3106f4..20b03b8)

A peer-coordinator session (same Ryan Clanton attribution) ran during the
~90-minute gap and landed 10 commits, of which 7 are substantive coordinator-
scope work on the modality-boundaries workstream and the CFDrs metric closure:

| Commit | Subject summary |
| :--- | :--- |
| `20b03b8` | Advance CFDrs gitlink to its consumer-side metric closure |
| `a802e0c` | Close CFDrs MET22 transient-composition metric gap in `gap_audit.md` |
| `b804449` | Split `ATLAS-MODALITY-002` — 2a (kwavers bioheat boundary) closed, 2b (SpecificAbsorptionRate provider-side gap) blocked on peer |
| `8571cc1` | Refresh Aequitas metric audit (reconcile CFDrs/Helios/Kwavers consumer closures) |
| `5711c0c` | Advance aequitas gitlink — `ATLAS-MODALITY-002` phase 1 |
| `537b22c` | Claim `ATLAS-MODALITY-002` phase 1 in aequitas |
| `35f41e9` | Record modality boundaries (optics / RF / photomedicine) in the stack map + kwavers bioheat deposition spine |
| `1da7cea` | (Session 26 carry-over) Close GMRES fork ports; record athena zero-consumer evidence; file `ATLAS-WORKTREE-CLONES-001` |
| `fad8c9e` | (Session 26 carry-over, peer-reused subject) CFDrs gitlink advance |
| `b3106f4` | (Session 26 close, peer-reused subject) Math SSOT audit pattern filed in `gap_audit.md` |

These landings are accepted (peer-coordinator authority is granted by the
standing Change intent on this allowlisted meta-repo; no clobber of my
Session 26 work). They advance `ATLAS-MODALITY-002` from `todo` to
`in-progress` (phase 1 delivered, phases 2b-4 open).

### Residual gitlink defects (re-probed this session)

`target/release/gitlink-coherence.exe audit` reports **5 defects + 1
stale-advanceable + 19 clean** (down from Session 26's 11 defects — peers
published `origin/main` for apollo/athena/gaia/helios/hermes/asclepius during
the gap, resolving the cat-a class).

Persistent defects, each blocked on peer recovery action the coordinator
cannot execute (no write access to `repos/<name>/...`):

| Repo | Category | Pin | origin/main | WT HEAD | Branch | Last commit | Recovery (peer-owned) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| coeus | cat-c | cdaf769 | e26ba668 | cdaf769 | `codex/coeus-error-function-parity` | 3h ago | peer-coeus: publish origin/main |
| hephaestus | no-origin-main | 47ca84a | (none) | 47ca84a | `codex/hephaestus-product-axis-reduction-parity` | 3h ago | peer-hephaestus: create `origin/main` (4-session persistent defect) |
| kwavers | cat-b | 81a40071 | dce38e26 | **a7922bcc** | `codex/kwavers-book-migration-eviction` | **59 min ago** | peer-kwavers: merge/rebase feature to origin/main OR roll WT to main; coordinator NOT advancing — peer is actively committing |
| leto | cat-b | c6ced81 | 5ba88cc | dcc5d54 | `codex/leto-real-sparse-lu` | 5h ago | peer-leto: merge feature to origin/main |
| ritk | cat-c | 65035908 | c05f84d5 | 65035908 | `codex/docs-ritk-n4-figure-only` | 3h ago | peer-ritk: merge feature + publish origin/main |

Stale-advanceable (still NOT safely advanceable):

- `mnemosyne`: pin=00c3f6d, origin-main=905909b, WT HEAD=ec1c000 on
  `codex/mnemosyne-tier-selection` (7h ago). `git add` would capture the
  feature-branch HEAD `ec1c000`, not `origin/main` `905909b`. Per pitfall #2,
  this remains blocked until peer-mnemosyne either publishes `origin/main`
  or rolls WT back to `main`.

### Assist-ladder actions taken this session

- **Audit recovery**: Verified peer-coordinator's Session 26 closure (L4785)
  and the math-SSOT inventory (L4542) survived intact — no remediation
  required.
- **No gitlink advances**: Every defect row is either a structurally
  peer-only recovery (publish `origin/main`, merge feature branch) or has
  the working tree on a feature branch that would capture the wrong SHA.
  `kwavers` peer committed 59 minutes ago — active, not stale; coordinator
  escalation inappropriate per `concurrent_agents` assist-or-skip rules.
- **Closure written**: This section.
- **No new board entries**: The 5 defect rows above are already covered by
  their prior-session backlog items; a louder board restate is not warranted
  until a true stale-claim (1h+ no commit signal) develops. Three defects
  (hephaestus, kwavers PR, leto) are at 3+ sessions persistence and would
  become candidates for user-direction escalation if they persist into
  Session 28.

### Stale-memory re-verification (this session)

- `rust-toolchain.toml` pinned, MSRV unchanged.
- `target/release/gitlink-coherence.exe` present and unchanged.
- 25 submodules in `.gitmodules` unchanged.
- Shared `target-dir = "target"` at `/d/atlas/.cargo/config.toml` unchanged.
- Re-confirmed: `repos/<name>/.git` is a `gitdir:` indirection file for the
  submodule members (except `leto`/`hephaestus`, which are full directories);
  the gitlink pin is what `atlas-meta`'s git index records, and it can differ
  from `repos/<name>` WT HEAD when a peer has moved their WT onto a feature
  branch without the coordinator committing the advance.

### Next-session handoff

- Re-fetch + re-probe at session open (utility `gitlink-coherence.exe audit`
  is the canonical state read).
- Watch for peer-kwavers landing the feature branch — if `origin/main`
  advances, the gitlink is a one-step advance.
- Watch for peer-coeus / peer-ritk / peer-mnemosyne / peer-leto feature
  merges — same one-step advance opportunity.
- Watch for peer-hephaestus publishing `origin/main` — would close the
  4-session persistent `no-origin-main` defect.
- If 3 of the 5 persistent defects are unchanged by Session 28 open,
  escalate to user with a single batched message naming the 2-3 worst
  blockers (likely hephaestus + the most-active-of-the-rest) and request
  direction on peer-side remediation.
- Stand-alone next coordinator items still `todo`:
  `ATLAS-OVERLAY-001` (generated patch overlay), `ATLAS-VERSION-GUARD-001`
  (manifest version guard), `ATLAS-MATH-SSOT-CONSOLIDATION-1` (audit filed;
  execution owned by peer-leto/peer-physics-crate), `ATLAS-WORKTREE-CLONES-001`
  (rescue the standalone clones under `worktrees/`). Review whether any
  becomes urgent next session.



## Session 28 closure (2026-07-27) — ADR 0033/0034 (Krylov/Accelerator re-architecture), coeus cat-b promotion, 1 defect escalation

Short session: re-oriented after peer-coordinator landings, integrated two new
ADRs into PM state, escalated the standing 4-session hephaestus defect as a
cross-referenced blocker on `ATLAS-ATHENA-ACCEL-BACKEND-001`, ended with no
new gitlink advances (5 defects + 1 stale-advanceable + 19 clean unchanged
this session).

### Peer-coordinator landings during the inter-session gap (6 commits, 5ed51fa..2cd4c01)

| Commit | Subject summary |
| :--- | :--- |
| `2cd4c01` | Propose one Hephaestus-backed Athena accelerator backend (ADR 0034, status `Proposed`) |
| `a454976` | Record `ATLAS-MODALITY-002` 2b progress + the unified heat-source field defect |
| `12d3fdf` | Reserve `ATLAS-DOWNSTREAM-COORDINATION-001` ticket for LeoNeuro-INC `50bfcd9` hand-off |
| `051d1af` | Reaffirm Athena as the Krylov owner (ADR 0033, `Accepted`, `[major] [arch]`) |
| `b23271b` / `eb3cdb9` | Refine STEP D axes table + alternatives-rejected grounds (PATH_DEP_AUDIT_001_ENTRY.md) |
| `1fd57ae` | Clarify STEP D orthogonal axes + alternatives rejected + push-handoff |

ADR 0033 supersedes the iterative-solver lane of my Session 26
`ATLAS-MATH-SSOT-CONSOLIDATION-1` audit (L4542). ADR 0033's reasoning is
correct: adoption-count inversion of a ratified boundary (ADR 0022 named
Athena Krylov SSOT; leto-ops's `ee6582d` reintroduction is a regression, not
a new SSOT, regardless of which has more current consumers). The
`ATLAS-MATH-SSOT-CONSOLIDATION-1` row's direct-decomposition lane (LU/QR/
Cholesky/SVD/eigen/Schur/Bunch-Kaufman/UDU — definitively leto-ops's
ownership per ADR 0033 §2) and sparse-interpolation-quadrature lanes remain
valid; only the iterative-solver recommendation is superseded by
ATLAS-ATHENA-KRYLOV-CAPABILITY-001 / ATLAS-GMRES-FORK-CONVERGE-001 /
ATLAS-ATHENA-ACCEL-BACKEND-001. The audit-inventory table itself (ssot-
baseline + cross-capability matrix) is unmodified and remains useful as the
broader cross-repon math consolidation inventory; it's just that one slice
of its recommended action set has been overtaken by a more authoritative
ADR.

### Gitlink state re-probed (post-peer-landings)

`target/release/gitlink-coherence.exe audit`: **5 defects + 1
stale-advanceable + 19 clean** (Session 27 had identical counts; this
session's only movement is the `coeus` defect upgrading from cat-c → cat-b).

| Repo | Category | Pin | origin/main | Movement vs Session 27 |
| :--- | :--- | :--- | :--- | :--- |
| coeus | cat-b | cdaf769 | 971fab9 | **upgraded** from cat-c: peer-coeus pushed `codex/coeus-error-function-parity` to a tracked remote branch (`origin/codex/coeus-error-function-parity`); still not merged to `origin/main` |
| hephaestus | no-origin-main | 47ca84a | (none) | unchanged (5-session persistent) |
| kwavers | cat-b | 81a40071 | dce38e26 | unchanged; WT HEAD moved to `a7922bcc` (peer kwavers-book-migration-eviction, 59 min ago at session open — peer is actively committing in their feature branch) |
| leto | cat-b | c6ced81 | 5ba88cc | unchanged |
| ritk | cat-c | 65035908 | c05f84d5 | unchanged |
| mnemosyne | stale-advanceable | 00c3f6d | 905909b | unchanged; WT on `codex/mnemosyne-tier-selection` |

### Assisted ACCEL-BACKEND row with the hephaestus-`origin/main` cross-reference

Appended a "Blocking upstream state" note at `ATLAS-ATHENA-ACCEL-BACKEND-001`
(L5127→L5137) naming the hephaestus 5-session persistent `no-origin-main`
defect as the upstream unblock for that [arch] item's deletion of
`athena-wgpu` and Hephaestus kernel additions. Recommend the user direct
peer-hephaestus to publish `origin/main` (or merge the feature branch) as
the unblock for both this row and the 4-session-persistent defect.

### Assist-ladder actions taken this session

- **No gitlink advances**: every defect is structurally peer-only recovery
  (publish/merge) or has the WT on a feature branch that would capture the
  wrong SHA per pitfall #2.
- **Doc-sync (anti-orphaning)**: cross-referenced the new ADR 0033/
  0034 chain into the existing `ATLAS-MATH-SSOT-CONSOLIDATION-1` audit row's
  recommendation set (no edit to that row, but the new PM state above makes
  the supersedence traceable); appended the blocking-upstream note to
  ACCEL-BACKEND.
- **Closure written**: this section.

### Next-session handoff

- **Highest-priority unblock**: peer-hephaestus publishing `origin/main` or
  merging `codex/hephaestus-product-axis-reduction-parity` to main. This
  closes a 5-session persistent defect AND unlocks `ATLAS-ATHENA-ACCEL-
  BACKEND-001` execution. Recommend the user message peer-hephaestus
  directly if the defect is unchanged at Session 29 open.
- **Watch for peer-kwavers feature-branch merge**: kwavers peer is actively
  committing to `codex/kwavers-book-migration-eviction`. Once it lands on
  `origin/main`, the gitlink is a one-step advance.
- **Watch for peer-coeus / peer-ritk / peer-mnemosyne / peer-leto feature
  branch merges** — same one-step advance opportunities.
- **3+ session persistence threshold**: hephaestus now in its 5th session;
  kwavers PR #325 (codex/kwavers-book-migration-eviction) and leto branch
  (codex/leto-real-sparse-lu) at 3+ sessions each. At Session 29, if
  hephaestus is still `no-origin-main`, escalate to user with batched
  message naming hephaestus as the worst blocker.
- Standing coordinator-scope `todo` items unchanged:
  `ATLAS-OVERLAY-001`, `ATLAS-VERSION-GUARD-001`, `ATLAS-WORKTREE-CLONES-001`,
  `ATLAS-DOWNSTREAM-COORDINATION-001` (new, peer-filed), `ATLAS-MATH-SSOT-
  CONSOLIDATION-1` (audit filed; execution owned by peer-leto/peer-physics-
  crate and now partially overtaken by ADR 0033's Krylov sequence).



## Session 29 closure (2026-07-27) — athena gitlink advance + hephaestus 6-session escalation threshold

### Re-orientation findings

- HEAD moved from Session 28 close (`73d3042`) to `ac20857` before this session
  opened via two peer-coordinator commits:
  - `3df60c1 build(atlas): Advance kwavers gitlink — ATLAS-MODALITY-002 phase
    2b closed` (peer-coordinator carried kwavers ATLAS-MODALITY-002 phase 2b
    close forward; kwavers gitlink was not actually advanced — see defect
    table below — the commit message subject and the kwavers gitlink advance
    it claimed did not coincide: pin remained `37d50b96`)
  - `ac20857 docs(pm): Record BiCGSTAB landing in Athena stage A` advanced
    the **leto** gitlink to `78d9e9e0` (peer-leto merged
    `codex/leto-real-sparse-lu` to `origin/main`, landing 17 commits since
    prior pin `c6ced81e`, including the boundary execution
    `687b670 refactor(leto-ops): Remove ndarray/nalgebra, native iterative
    solvers (LETO-NDARRAY-BOUNDARY-1)` — directly advancing the standing
    migration goal and aligning with ADR 0033's Krylov-ownership reaffirmation
    by retiring leto-ops native iterative solvers)
- Re-audited gitlink coherence: **4 defects | 2 stale-advanceable | 19
  clean**. Compared to Session 28 close: leto resolved (cat-b → advanced);
  athena newly stale-advanceable (peer-athena landed BiCGSTAB).

### Assist-ladder action executed: athena gitlink advance

- Verified: pin `a5fd8061` ancestral to origin/main `e965a95d` via
  `merge-base --is-ancestor`; **WT HEAD == origin/main byte-for-byte**;
  WT clean (`## main...origin/main`, no dirty files, not on feature branch).
  Pitfall #2 satisfied.
- Selective-staging discipline executed: `git reset HEAD -- .` →
  `git add repos/athena` → verified staged SHA == athena origin/main →
  verified only `repos/athena` staged (`git diff --cached --name-only` →
  CLEAN).
- Committed as `c38ca61 build(atlas): Advance athena gitlink to e965a95d`,
  pushed same cycle (`ac20857..c38ca61 main -> main`). Aligns with ADR 0033
  (Athena owns Krylov) and ATLAS-ATHENA-KRYLOV-CAPABILITY-001.

### Hephaestus `no-origin-main` — now 6-session persistent, escalation exercised

- Re-probed 2026-07-27 Session 29: hephaestus HEAD `47ca84a8`, last commit
  2026-07-27T12:22:02-04:00 (~6h prior). WT on
  `codex/hephaestus-product-axis-reduction-parity`, **ahead 1** of
  `origin/codex/hephaestus-product-axis-reduction-parity` with dirty
  `Cargo.lock`. Remote has only feature branches — **`origin/main` ref
  does not exist**; the structural cause is peer-hephaestus works
  exclusively on feature-branch flow and never publishes `main`.
- Per the standing ATLAS-ATHENA-ACCEL-BACKEND-001 cross-reference
  (L5139+) and the Session 28 next-session handoff instruction, the
  5-session threshold having been crossed at Session 28 close, Session 29
  confirms the defect is now **6-session persistent**.
- Coordinator authority (assist-ladder) does not authorize executing peer
  pushes. The escalation route is a **batched user-facing message** naming
  peer-hephaestus as the worst blocker; the cluster trio
  (`hephaestus`, `kwavers PR #325`, `ritk` `codex/docs-ritk-n4-figure-only`)
  as the user-actionable remediation set; and the gating relationship to
  `ATLAS-ATHENA-ACCEL-BACKEND-001` ([arch]) as the consequence of continued
  blockage. This message is delivered in the session response (not as a
  PM artifact, per no-report-file genre).

### Post-push gitlink-coherence state

| # | Repo | Category | Pin | origin/main | Last commit | Recovery (peer-owned) |
|---|---|---|---|---|---|---|
| 1 | coeus | cat-b | `cdaf769` | `971fab9` | 3h ago | peer-coeus: merge `codex/coeus-error-function-parity` to origin/main |
| 2 | hephaestus | no-origin-main | `47ca84a` | (none) | 6h ago | peer-hephaestus: publish origin/main — **6-session persistent, gating ACCEL-BACKEND-001** |
| 3 | kwavers | cat-b | `37d50b96` | `dce38e26` | <1h ago | peer-kwavers: merge/rebase `codex/kwavers-book-migration-eviction` (PR #325) |
| 4 | ritk | cat-c | `65035908` | `c05f84d5` | 3h ago | peer-ritk: merge `codex/docs-ritk-n4-figure-only` + publish origin/main |

**Stale-advanceable (this session close)**: `mnemosyne` only — pin `00c3f6d`,
origin/main `905909b`, WT on `codex/mnemosyne-tier-selection` HEAD
`ec1c000` (dirty `Cargo.lock`/`Cargo.toml`). NOT safely advanceable per
pitfall #2 (would capture peer's feature-branch HEAD, not origin/main).

**Athena — captured in two advances this session**:
- `c38ca61` advanced athena to `e965a95d` for the right-preconditioned
  BiCGSTAB landing.
- `24ad6ea` advanced athena again to `fef782cb` for the incomplete-LU /
  SuccessiveOverRelaxation preconditioner landing in `athena-leto`, which
  pairs with the Krylov family covered by ADR 0033. (Pin `e965a95d`
  stayed ancestral to `fef782cb`, so the second advance remained a clean
  one-step `git add` after verifying `WT HEAD == origin/main`.)
Both advances are attestable; the table above lists only the
still-defective and still-stale-advanceable rows.

### Next-session handoff

- **Primary escalation (carried)**: peer-hephaestus publishing `origin/main`
  or merging `codex/hephaestus-product-axis-reduction-parity` to main. This
  now closes a 6-session persistent defect AND unlocks
  `ATLAS-ATHENA-ACCEL-BACKEND-001` execution. A direct user → peer-hephaestus
  nudge is now warranted prior to a 7th session.
- **Cluster escalation (carried)**: kwavers PR #325 /
  `codex/kwavers-book-migration-eviction` (3+ sessions), ritk
  `codex/docs-ritk-n4-figure-only` (3+ sessions), coeus
  `codex/coeus-error-function-parity` (3+ sessions). Batch a single
  user-facing message if all are unchanged at Session 30 open.
- **Watch for one-step gitlink advance opportunities**: peer-mnemosyne,
  peer-coeus, peer-kwavers, peer-ritk if their feature branches merge to
  origin/main (verify `WT HEAD == origin/main` before `git add` per
  pitfall #2).
- Standing coordinator-scope `todo` items unchanged:
  `ATLAS-OVERLAY-001`, `ATLAS-VERSION-GUARD-001`,
  `ATLAS-WORKTREE-CLONES-001`, `ATLAS-DOWNSTREAM-COORDINATION-001`,
  `ATLAS-MATH-SSOT-CONSOLIDATION-1` (audit-only, partially overtaken by
  ADR 0033 Krylov sequence).



## Session 30 closure (2026-07-28) — atlas-stack-overlay CI wiring + peer math-SSOT PR 0008 audit artifacts tracked

Re-oriented against `origin/main` at session open; HEAD had moved from `d2e0ac9` to `182f346` through peer-coordinator landings during the inter-session gap. The persistent gitlink defect set shifted: hephaestus 8-session `no-origin-main` defect narrowed (peer published an `origin/main` ref, pin advanced to `bf24b873`), but the 4-defect cluster (coeus cat-b, hephaestus no-origin-main, kwavers cat-b, ritk cat-c) persists and remains blocked on peer-side branch merges.

### Landed

- `599ddca build(atlas): Advance athena/proteus/tyche/asclepius gitlinks` — four stale-advanceables cleared: athena `fef782cb` -> `1d24c643` (ADR 0034 stage 3 merge of feat/athena-hephaestus-backend, advancing the device-neutral accelerator backend per ADR 0034), proteus `9d7c1a8c` -> `9a8655d3`, tyche `1527964c` -> `996b649d`, asclepius `bbf38400` -> `ccffb6bc`. Each followed the safe-advance protocol (pin ancestor of origin/main, WT on `main` with HEAD == origin/main, single Cargo.lock dirt in each not captured by submodule gitlink staging). Reduces stale-advanceable from 6 to 2 (mnemosyne on feature branch, kwavers on cat-b).

### Tracked (peer-authored artifacts staged for review)

- `docs/pr/0008-math-ssot-adr-0031-0033-review-checklist.md` (138 lines, peer-drafted PR description for the math-SSOT consolidation; covers ADRs 0031/0032/0033 closure into leto-ops SSOT; cross-repo consumers `cfd-math`, `kwavers-math`, `kwavers-solver`; reserved tag `atlas/math-ssot-adr-0031-0033-closure`; per-ADR sign-off checklist spanning CFDrs / Kwavers / leto-ops module owners). Stage-only; substantive source changes in `repos/CFDrs/crates/cfd-math/...` and `repos/kwavers/crates/kwavers-{math,solver}/...` are peer-owned and out of coordinator scope.
- `docs/audit/math-ssot-ledger.md` (753 lines, peer-authored audit ledger documenting the leto SSOT surface and per-consumer redundancy inventory; provider-side already landed in leto-ops `StaggeredForward`/`StaggeredBackward`, `complex_solve`/`complex_inv`, `FiniteDifference3D`). Stage-only.

### Next-session handoff

- ATLAS-MATH-SSOT-CONSOLIDATION-1 closure gate: peer-CFDrs must commit and merge the `cfd-math` wrapper deletion (`cfd-math/src/differentiation/` removed, `fd_extensions` re-export added) before coordinator can advance the CFDrs gitlink and close the audit row. The CFDrs WT is at origin/main HEAD `c90e6840` but dirty (36 files, peer-cfdrs mid-flight on `CFDRS-AEQ-MET-25` cavitation work). When the CFDrs gitlink advances, the audit row can mark the math-SSOT consolidation phase as delivered and PR 0008 can be reviewed/merged by module owners. The same dependency applies to kwavers (`codex/kwavers-book-migration-eviction` feature branch at `df9008d9`) and leto (`codex/leto-real-sparse-lu` at `1d24c643`+3); none is safely advanceable until peer returns WT to `main` and merges to `origin/main`.
- Standing coordinator-scope `todo` items unchanged: `ATLAS-OVERLAY-001` (sub-deliveries 1/2 still open), `ATLAS-VERSION-GUARD-001` (sub-delivery 1: per-member guard tool skeleton), `ATLAS-WORKTREE-CLONES-001` (asclepius/hephaestus/leto WTs are peer-active mid-flight; remaining clones re-evaluate on next session).
- ~~The `repos/parity_artefacts/` directory has been physically removed from the working tree but the deletion is not staged~~ — **superseded 2026-08-18.** The removal did not hold: commit `5956d02`, a gitlink advance whose message describes a ritk `region.rs` split, re-added it as scope creep along with a second copy at the meta-repo root — 899 lines, 18 files, two archives where there should be one. Now resolved rather than re-deferred, because the deferral rationale ("belongs with the parity stream's closure increment") is what let it regrow: the duplicate is deleted, `INDEX.md` moved to the root copy with its relative links re-anchored one level up and verified to resolve, and `docs/mdbook/detector-parity.md` plus `gap_audit.md` corrected. The tracked pairs were byte-identical apart from line endings, so nothing unique was lost. Two truth defects were fixed alongside: INDEX.md claimed the archive "survives repo re-clones" when 33 of its 43 files are gitignored `*.log`, and the report claimed the `SUMMARY.md` path "resolves correctly" without the in-context-build qualifier that its own recorded CI failure contradicts.

### Post-session peer advances (attribution-absorption pattern)

Between my `599ddca` and the close of this session, peer landed a chain that absorbed the Session 30 closure intent and advanced the persistent defect set further:

- `9f92d94 docs(atlas): Refresh Aequitas gap audit` — peer-committed `docs/audit/math-ssot-ledger.md` and `docs/pr/0008-math-ssot-adr-0031-0033-review-checklist.md` under their subject. Content identical to what this session would have committed. Pattern matches the Session 25/26/28 attribution-absorption; no remediation needed because the content is correct.
- `d1f2e2c docs(atlas): Record Aequitas consumer closure` — gap audit refresh.
- `c2cad74 build(atlas): Advance CFDrs Aequitas closure` — CFDrs gitlink advanced to `109aec63`; CFDrs now reads as clean in the gitlink-coherence audit (down from stale-advanceable). MET-25 closure intent is now realized at the CFDrs WT HEAD; the math-SSOT PR 0008 cfd-math deletion gate (peer-cf must commit + push) remains the only outstanding dependency.
- `485b3dd docs(pm): Root-cause the gaia git-dep break blocking helios tests` — closes the gaia blocker; helios tests can now run against canonical gaia.
- `f793735 docs(adr): Correct ADR 0037's lockstep versioning mandate` — ADR 0037 mandate tightened.
- `86cb19a docs(pm): Record the generic-instantiation pattern; revert the blocked edit` — reverts a blocked edit and records the generic-instantiation pattern.

Final gitlink-coherence state at Session 30 close: **25 probed | 4 defects | 1 stale-advanceable | 20 clean.**

- **Defects (4):** coeus cat-b (peer `codex/coeus-error-function-parity` not merged); hephaestus no-origin-main (default branch is `master` at remote `14b73d56`, WT HEAD `7897c13f` is mid-flight on `ATLAS-HEPHAESTUS-SPARSE-SEAM-001` sparse-seam work, last commit 77 min ago — peer-active, leave alone); kwavers cat-b (`codex/kwavers-book-migration-eviction` not merged); ritk cat-c (`codex/docs-ritk-n4-figure-only` local-only, not pushed).
- **Stale-advanceable (1):** mnemosyne `00c3f6de` -> `905909be` — WT on divergent feature branch `codex/mnemosyne-tier-selection` (HEAD `ec1c000` not ancestor of origin/main), 30h since last commit; peer-mnemosyne is mid-flight on tier-selection work.

### Session 30 / Atlas-meta delivery summary

| Increment | SHA | Type | Coordinator-authored? |
|---|---|---|---|
| Advance athena/proteus/tyche/asclepius gitlinks | `599ddca` | build(atlas) | Yes — full content + protocol verification |
| Track PR 0008 + math-SSOT ledger | `9f92d94` | docs(atlas) | Peer-absorbed (content preserved) |
| Session 30 closure in backlog | `9f92d94` + `485b3dd` | docs(pm) | Yes — full text + peer addendum |
| CFDrs Aequitas closure advance | `c2cad74` | build(atlas) | Peer-owned |

<a id="atlas-hephaestus-host-seam-coverage"></a>- [ATLAS-HEPHAESTUS-HOST-SEAM-COVERAGE](backlog/atlas-hephaestus-host-seam-coverage.md) — `hephaestus-host` implements every seam the conformance suite is generic over [arch][major] — in-progress
<a id="atlas-hooks-follow-checkout-2026-09-18"></a>- [ATLAS-HOOKS-FOLLOW-CHECKOUT-2026-09-18](backlog/atlas-hooks-follow-checkout-2026-09-18.md) — The installed atlas hooks are whatever branch the shared tree holds [patch] — todo
<a id="atlas-solver-ownership-consolidation"></a>- [ATLAS-SOLVER-OWNERSHIP-CONSOLIDATION](backlog/atlas-solver-ownership-consolidation.md) — Complete ADR 0033: the Krylov forks and the only multigrid in the stack live in CFDrs [arch][major] — todo
<a id="atlas-prepush-hook-forked-across-members-2026-09-09"></a>- [ATLAS-PREPUSH-HOOK-FORKED-ACROSS-MEMBERS-2026-09-09](backlog/atlas-prepush-hook-forked-across-members-2026-09-09.md) — One gate, twenty-three copies, six versions [patch] [ci] — in-progress
<a id="atlas-coeus-branch-inventory-2026-09-09"></a>- [ATLAS-COEUS-BRANCH-INVENTORY-2026-09-09](backlog/atlas-coeus-branch-inventory-2026-09-09.md) — Fifteen coeus branches hold unique work nobody is finishing [patch] — in-progress
<a id="atlas-cwd-config-cost-2026-09-16"></a>- [ATLAS-CWD-CONFIG-COST-2026-09-16](backlog/atlas-cwd-config-cost-2026-09-16.md) — Cargo config discovery is all-or-nothing: the shared `target-dir` arrives with the whole-stack `[patch]` overlay [patch] — in-progress
<a id="atlas-third-party-check-always-red"></a>- [ATLAS-THIRD-PARTY-CHECK-ALWAYS-RED-2026-09-09](backlog/atlas-third-party-check-always-red.md) — A check that fails on every pull request [patch] — blocked
<a id="atlas-build-source-identity"></a>- [ATLAS-BUILD-SOURCE-IDENTITY](backlog/atlas-build-source-identity.md) — Detect stale artifacts across source trees [patch] — todo
<a id="kwavers-elastic-collision"></a>- [ATLAS-KWAVERS-ELASTIC-COLLISION-2026-09-03](backlog/kwavers-elastic-collision.md) — Step 2b is peer-owned; I collided with it [patch] — blocked
<a id="ares-promotion"></a>- [ATLAS-ARES-PROMOTION-2026-09-03](backlog/ares-promotion.md) — Create and register `ares` (solid momentum balance) [arch][minor] — in-progress
<a id="publish-order-optional-edges"></a>- [ATLAS-PUBLISH-ORDER-OPTIONAL-EDGES-2026-09-04](backlog/publish-order-optional-edges.md) — Decide whether optional dependencies constrain publish order [patch] — in-progress
<a id="prometheus-promotion"></a>- [ATLAS-PROMETHEUS-PROMOTION-2026-09-03](backlog/prometheus-promotion.md) — Create and register `prometheus` (species mass balance) [arch][minor] — in-progress
<a id="next-steps"></a>- [ATLAS-NEXT-STEPS-2026-09-03](backlog/next-steps.md) — Sequenced plan toward the suite [arch] — todo
<a id="substrate-contract-measured"></a>- [ATLAS-SUBSTRATE-CONTRACT-MEASURED-2026-09-03](backlog/substrate-contract-measured.md) — The contract is already satisfied; the guard is preventive [patch] — todo
<a id="proteus-elastic-ssot"></a>- [ATLAS-PROTEUS-ELASTIC-SSOT-2026-09-03](backlog/proteus-elastic-ssot.md) — Proteus owns the isotropic modulus conversion contract [minor] — in-progress
<a id="atlas-runner-starvation-2026-09-02"></a>- [ATLAS-RUNNER-STARVATION-2026-09-02](backlog/atlas-runner-starvation-2026-09-02.md) — Hosted runner queue starves every verification run [infra] — todo
<a id="atlas-overlay-worktree-keyed"></a>- [ATLAS-OVERLAY-WORKTREE-KEYED-2026-09-06](backlog/atlas-overlay-worktree-keyed.md) — The overlay gate compares a committed artifact against a generation from uncommitted inputs [arch] — review
<a id="atlas-default-branch-reds-2026-09-02"></a>- [ATLAS-DEFAULT-BRANCH-REDS-2026-09-02](backlog/atlas-default-branch-reds-2026-09-02.md) — Member default-branch workflows red with no collector [patch] — todo
<a id="atlas-provider-chain-quality-2026-08-27"></a>- [ATLAS-PROVIDER-CHAIN-QUALITY-2026-08-27](backlog/atlas-provider-chain-quality-2026-08-27.md) — Perf/memory/stability/safety audit + fix wave: apollo provider chain [patch]..[minor] — in-progress
<a id="atlas-ci-runner-saturation-2026-08-25"></a>- [ATLAS-CI-RUNNER-SATURATION-2026-08-25](backlog/atlas-ci-runner-saturation-2026-08-25.md) — Hosted-runner queue depth delays every merge gate [patch] — in-progress
<a id="atlas-hermes-consumer-entry-2026-08-25"></a>- [ATLAS-HERMES-CONSUMER-ENTRY-2026-08-25](backlog/atlas-hermes-consumer-entry-2026-08-25.md) — Restore Hermes as the stack's lane-kernel owner [arch] — in-progress
<a id="atlas-athena-allocation-contract"></a>- [ATLAS-ATHENA-ALLOCATION-CONTRACT](backlog/atlas-athena-allocation-contract.md) — warm solves allocate 4-6 small buffers per call on Linux [patch] — in-progress
<a id="atlas-kwavers-ci-coverage-opt-2026-08-25"></a>- [ATLAS-KWAVERS-CI-COVERAGE-OPT-2026-08-25](backlog/atlas-kwavers-ci-coverage-opt-2026-08-25.md) — Bound full-workspace test topology [perf][patch] — in-progress
<a id="atlas-kwavers-swe3d-baseline-regression-2026-08-26"></a>- [ATLAS-KWAVERS-SWE3D-BASELINE-REGRESSION-2026-08-26](backlog/atlas-kwavers-swe3d-baseline-regression-2026-08-26.md) — integration oracle regression on main [major] — in-progress
<a id="atlas-kwavers-hephaestus-contract-2026-08-21"></a>- [ATLAS-KWAVERS-HEPHAESTUS-CONTRACT-2026-08-21](backlog/atlas-kwavers-hephaestus-contract-2026-08-21.md) — Define the neutral visualization handoff [major][arch] — in-progress
<a id="atlas-kwavers-alloc-probe-deny-docs-2026-08-21"></a>- [ATLAS-KWAVERS-ALLOC-PROBE-DENY-DOCS-2026-08-21](backlog/atlas-kwavers-alloc-probe-deny-docs-2026-08-21.md) — Pilot deny(missing_docs) [patch] — in-progress
<a id="atlas-kwavers-python-generator-2026-08-21"></a>- [ATLAS-KWAVERS-PYTHON-GENERATOR-2026-08-21](backlog/atlas-kwavers-python-generator-2026-08-21.md) — Add defaults and NumPy protocols [minor] — in-progress
<a id="atlas-kwavers-python-gil-2026-08-21"></a>- [ATLAS-KWAVERS-PYTHON-GIL-2026-08-21](backlog/atlas-kwavers-python-gil-2026-08-21.md) — Detach Simulation.run [minor] — in-progress
<a id="atlas-book-figure-closure-2026-08-21"></a>- [ATLAS-BOOK-FIGURE-CLOSURE-2026-08-21](backlog/atlas-book-figure-closure-2026-08-21.md) — Restore generated validation figures [patch] — in-progress
<a id="atlas-cfdrs-python-gil-2026-08-21"></a>- [ATLAS-CFDRS-PYTHON-GIL-2026-08-21](backlog/atlas-cfdrs-python-gil-2026-08-21.md) — Complete PyO3 solver GIL boundaries [minor] — in-progress
<a id="atlas-kwavers-vis-config-2026-08-25"></a>- [ATLAS-KWAVERS-VIS-CONFIG-2026-08-25](backlog/atlas-kwavers-vis-config-2026-08-25.md) — Make visualization selection and quality single-source [major] — blocked
<a id="atlas-kwavers-bench-smoke-2026-08-25"></a>- [ATLAS-KWAVERS-BENCH-SMOKE-2026-08-25](backlog/atlas-kwavers-bench-smoke-2026-08-25.md) — Bound cold-build benchmark smoke [patch] — in-progress
<a id="atlas-kwavers-python-surface-2026-08-21"></a>- [ATLAS-KWAVERS-PYTHON-SURFACE-2026-08-21](backlog/atlas-kwavers-python-surface-2026-08-21.md) — Complete typed and concurrent PyO3 surface [minor] — in-progress
<a id="atlas-themis-region-module-2026-08-20"></a>- [ATLAS-THEMIS-REGION-MODULE-2026-08-20](backlog/atlas-themis-region-module-2026-08-20.md) — Split branded region implementation [arch][patch] — in-progress
<a id="atlas-helios-radon-oracle-2026-08-20"></a>- [ATLAS-HELIOS-RADON-ORACLE-2026-08-20](backlog/atlas-helios-radon-oracle-2026-08-20.md) — Remove existence-only sinogram assertion [patch] — in-progress
<a id="atlas-adr0033-stages"></a>- [ATLAS-ADR0033-STAGES](backlog/atlas-adr0033-stages.md) — Krylov ownership unwind, measured status [arch] — in-progress
<a id="atlas-book-staging-2026-08-20"></a>- [ATLAS-BOOK-STAGING-2026-08-20](backlog/atlas-book-staging-2026-08-20.md) — Preserve Cargo artifact identity in mdBook gates [patch] — in-progress
<a id="atlas-book-caller-pins-2026-08-20"></a>- [ATLAS-BOOK-CALLER-PINS-2026-08-20](backlog/atlas-book-caller-pins-2026-08-20.md) — Repin provider mdBook callers [patch] — in-progress
<a id="atlas-consus-szip-bound-2026-08-20"></a>- [ATLAS-CONSUS-SZIP-BOUND-2026-08-20](backlog/atlas-consus-szip-bound-2026-08-20.md) — Bound SZIP allocation [security][patch] — in-progress
<a id="atlas-apollo-python-surface-2026-08-20"></a>- [ATLAS-APOLLO-PYTHON-SURFACE-2026-08-20](backlog/atlas-apollo-python-surface-2026-08-20.md) — Ship the typed Python surface [patch] — in-progress
<a id="atlas-harmonia-field-exchange-050-2026-08-21"></a>- [ATLAS-HARMONIA-FIELD-EXCHANGE-050-2026-08-21](backlog/atlas-harmonia-field-exchange-050-2026-08-21.md) — Add typed physical-field exchange [major] [arch] — in-progress
<a id="atlas-moirai-accelerator-route-2026-08-21"></a>- [ATLAS-MOIRAI-ACCELERATOR-ROUTE-2026-08-21](backlog/atlas-moirai-accelerator-route-2026-08-21.md) — Execute accelerator routes [major] [arch] — in-progress
<a id="atlas-cfdrs-allocator-2026-08-20"></a>- [ATLAS-CFDRS-ALLOCATOR-2026-08-20](backlog/atlas-cfdrs-allocator-2026-08-20.md) — Remove library global allocator [major][arch] — in-progress
<a id="atlas-substrate-003-2026-08-20"></a>- [ATLAS-SUBSTRATE-003-2026-08-20](backlog/atlas-substrate-003-2026-08-20.md) — Give the Leto/Hephaestus decomposition pair one seam and one oracle [minor][arch] — in-progress
<a id="atlas-provider-closure-2026-08-20"></a>- [ATLAS-PROVIDER-CLOSURE-2026-08-20](backlog/atlas-provider-closure-2026-08-20.md) — Complete active provider slices [major][arch] — in-progress
<a id="atlas-kwavers-distributed-queue-2026-08-20"></a>- [ATLAS-KWAVERS-DISTRIBUTED-QUEUE-2026-08-20](backlog/atlas-kwavers-distributed-queue-2026-08-20.md) — close queue completion and deadline contracts [patch] — in-progress
<a id="atlas-cfdrs-hosted-fmt-2026-08-20"></a>- [ATLAS-CFDRS-HOSTED-FMT-2026-08-20](backlog/atlas-cfdrs-hosted-fmt-2026-08-20.md) — repair required Rust format gate [patch] — in-progress
<a id="atlas-hosted-recheck-2026-08-19-2"></a>- [ATLAS-HOSTED-RECHECK-2026-08-19-2](backlog/atlas-hosted-recheck-2026-08-19-2.md) — current provider state [patch] — in-progress
<a id="atlas-ritk-default-reconciliation-2026-08-19"></a>- [ATLAS-RITK-DEFAULT-RECONCILIATION-2026-08-19](backlog/atlas-ritk-default-reconciliation-2026-08-19.md) — docs-only merge [patch] — in-progress
<a id="atlas-horae-consumer-audit-2026-08-19"></a>- [ATLAS-HORAE-CONSUMER-AUDIT-2026-08-19](backlog/atlas-horae-consumer-audit-2026-08-19.md) — boundary finding [patch] — blocked
<a id="atlas-hosted-recheck-2026-08-19"></a>- [ATLAS-HOSTED-RECHECK-2026-08-19](backlog/atlas-hosted-recheck-2026-08-19.md) — moving-default evidence — in-progress
<a id="atlas-publish-graph-2026-08-19"></a>- [ATLAS-PUBLISH-GRAPH-2026-08-19](backlog/atlas-publish-graph-2026-08-19.md) — crates.io dependency closure — blocked
<a id="atlas-provider-integration-2026-08-18-current"></a>- [ATLAS-PROVIDER-INTEGRATION-2026-08-18-CURRENT](backlog/atlas-provider-integration-2026-08-18-current.md) — superseding recheck [patch] — in-progress
<a id="atlas-hosted-state-2026-08-18-2230"></a>- [ATLAS-HOSTED-STATE-2026-08-18-2230](backlog/atlas-hosted-state-2026-08-18-2230.md) — exact-head gate recheck [patch] — in-progress
<a id="atlas-multiphysics-adoption-100"></a>- [ATLAS-MULTIPHYSICS-ADOPTION-100](backlog/atlas-multiphysics-adoption-100.md) — CFDrs/Kwavers/Helios provider adoption and suite closure [major] [arch] — in-progress
<a id="atlas-cfdrs-crlf-085"></a>- [ATLAS-CFDRS-CRLF-085](backlog/atlas-cfdrs-crlf-085.md) — CFDrs commits CRLF with no `.gitattributes` [patch] — blocked
<a id="ritk-views-047"></a>- [RITK-VIEWS-047](backlog/ritk-views-047.md) — Collapse seven data accessors to two [major] — blocked
<a id="ritk-shared-tree-stale-basis-213"></a>- [RITK-SHARED-TREE-STALE-BASIS-213](backlog/ritk-shared-tree-stale-basis-213.md) — ritk's shared tree is checked out 58 commits behind origin [patch] — in-progress
<a id="ritk-doc-gate-210"></a>- [RITK-DOC-GATE-210](backlog/ritk-doc-gate-210.md) — `cargo doc` is red on ritk's default branch [patch] — in-progress
<a id="atlas-crate-level-allows-217"></a>- [ATLAS-CRATE-LEVEL-ALLOWS-217](backlog/atlas-crate-level-allows-217.md) — 502 blanket suppressions the ratchet never counted [major] — in-progress
<a id="atlas-lane-sprawl-222"></a>- [ATLAS-LANE-SPRAWL-222](backlog/atlas-lane-sprawl-222.md) — 26 lane directories against a two-per-repo bound [patch] — in-progress
<a id="ritk-peer-ratchet-211"></a>- [RITK-PEER-RATCHET-211](backlog/ritk-peer-ratchet-211.md) — Peer commits regressed three ratchet classes on ritk [patch] — todo
<a id="atlas-arch-008-running-in-place-225"></a>- [ATLAS-ARCH-008-RUNNING-IN-PLACE-225](backlog/atlas-arch-008-running-in-place-225.md) — The conversion converts and re-accumulates at the same rate [patch] — in-progress
<a id="atlas-unwired-gates-224"></a>- [ATLAS-UNWIRED-GATES-224](backlog/atlas-unwired-gates-224.md) — Instruments that exist, pass, and are never run [patch] — in-progress
<a id="atlas-stale-checkout-findings-223"></a>- [ATLAS-STALE-CHECKOUT-FINDINGS-223](backlog/atlas-stale-checkout-findings-223.md) — Gates measure the checkout, and 8 of 25 members are behind [patch] — in-progress
<a id="ritk-accessor-followups-212"></a>- [RITK-ACCESSOR-FOLLOWUPS-212](backlog/ritk-accessor-followups-212.md) — Two consequences the accessor migration exposed [patch] — blocked
<a id="atlas-cfdrs-lane-diverged-208"></a>- [ATLAS-CFDRS-LANE-DIVERGED-208](backlog/atlas-cfdrs-lane-diverged-208.md) — CFDrs lane holds 99 unpushed commits and is 18 behind its own remote [patch] — in-progress
<a id="atlas-apollo-lint-expect-rot-001"></a>- [ATLAS-APOLLO-LINT-EXPECT-ROT-001](backlog/atlas-apollo-lint-expect-rot-001.md) — Remove obsolete Windows Clippy expectations [patch] — in-progress
<a id="atlas-apollo-stockham-policy-050c"></a>- [ATLAS-APOLLO-STOCKHAM-POLICY-050C](backlog/atlas-apollo-stockham-policy-050c.md) — Parameterize the dispatch-policy matrix [minor] — todo
<a id="atlas-apollo-complex-seam-050b"></a>- [ATLAS-APOLLO-COMPLEX-SEAM-050B](backlog/atlas-apollo-complex-seam-050b.md) — Element-parameterize the complex seams [minor] — todo
<a id="atlas-kwavers-real-compute-028"></a>- [ATLAS-KWAVERS-REAL-COMPUTE-028](backlog/atlas-kwavers-real-compute-028.md) — Remove Kwavers production identity paths [major] [arch] — todo
<a id="atlas-usct-fwi-024"></a>- [ATLAS-USCT-FWI-024](backlog/atlas-usct-fwi-024.md) — Transmission-USCT FWI parity [minor] — in-progress
<a id="atlas-us-capability-023"></a>- [ATLAS-US-CAPABILITY-023](backlog/atlas-us-capability-023.md) — ITKUltrasound capability parity [arch] — in-progress
<a id="atlas-arch-011"></a>- [ATLAS-ARCH-011](backlog/atlas-arch-011.md) — Retire hephaestus-metal per ADR 0047 [arch] [major] — blocked
<a id="atlas-overlay-gen-stale-1"></a>- [ATLAS-OVERLAY-GEN-STALE-1](backlog/atlas-overlay-gen-stale-1.md) — Cross-repo path deps on member mainlines [arch] — todo
<a id="atlas-arch-005"></a>- [ATLAS-ARCH-005](backlog/atlas-arch-005.md) — Replace closed-set dyn dispatch in per-timestep paths [arch] — in-progress
<a id="atlas-arch-008"></a>- [ATLAS-ARCH-008](backlog/atlas-arch-008.md) — Replace pointer-scattered containers on traversal paths [patch] — in-progress
<a id="atlas-privacy-naming-1"></a>- [ATLAS-PRIVACY-NAMING-1](backlog/atlas-privacy-naming-1.md) — Private consumer named throughout stack artifacts [chore] — todo
<a id="atlas-pub-001"></a>- [ATLAS-PUB-001](backlog/atlas-pub-001.md) — Migrate 8 crate-release workflows to the Atlas-shared caller [patch] — blocked
<a id="atlas-pub-002"></a>- [ATLAS-PUB-002](backlog/atlas-pub-002.md) — Migrate 4 book workflows to the Atlas-shared caller and close the docs.yml gap [patch] — in-progress
<a id="atlas-pub-003"></a>- [ATLAS-PUB-003](backlog/atlas-pub-003.md) — Register trusted publishers and remove the unused PyPI token [chore] — todo
<a id="atlas-pub-006"></a>- [ATLAS-PUB-006](backlog/atlas-pub-006.md) — Stand up one facade crate per package [minor] — todo
<a id="atlas-pub-008"></a>- [ATLAS-PUB-008](backlog/atlas-pub-008.md) — Audit facade names immediately before each first publish [chore] — todo
<a id="atlas-pub-005"></a>- [ATLAS-PUB-005](backlog/atlas-pub-005.md) — Flip `mdbook-test` per book as samples become compilable [patch] — in-progress
<a id="atlas-modality-003"></a>- [ATLAS-MODALITY-003](backlog/atlas-modality-003.md) — Optical-transport and RF/EM promotion watchpoint [arch] — blocked
<a id="atlas-overlay-005"></a>- [ATLAS-OVERLAY-005](backlog/atlas-overlay-005.md) — Clear first-party rev pins across the stack [patch] — in-progress
<a id="atlas-overlay-004"></a>- [ATLAS-OVERLAY-004](backlog/atlas-overlay-004.md) — Worktree sprawl breaks stack dependency resolution [patch] — in-progress
<a id="atlas-downstream-coordination-001"></a>- [ATLAS-DOWNSTREAM-COORDINATION-001](backlog/atlas-downstream-coordination-001.md) — Notify LeoNeuro-INC maintainers about local leoneuro-rs `50bfcd9` [chore] — todo
<a id="atlas-check-figures-ci-verify-defer"></a>- [ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER](backlog/atlas-check-figures-ci-verify-defer.md) — End-to-end CI verification of `prebook check-figures` [minor] — in-progress
<a id="atlas-cfdrs-runner-mdbook-index-1"></a>- [ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1](backlog/atlas-cfdrs-runner-mdbook-index-1.md) — Close CFDrs runner-side mdBook index + ci.yml silent-drop [patch] — in-progress
<a id="atlas-worktree-001"></a>- [ATLAS-WORKTREE-001](backlog/atlas-worktree-001.md) — Canonical lane root consolidation [patch] — in-progress
<a id="atlas-target-001"></a>- [ATLAS-TARGET-001](backlog/atlas-target-001.md) — One build cache, one debug budget [patch] — in-progress
<a id="atlas-bench-budget-001"></a>- [ATLAS-BENCH-BUDGET-001](backlog/atlas-bench-budget-001.md) — Wall-clock budgets for benches and examples [patch] — in-progress
<a id="atlas-build-structure-001"></a>- [ATLAS-BUILD-STRUCTURE-001](backlog/atlas-build-structure-001.md) — Consolidate leaf binaries; compiler-last dev profiles [patch] — in-progress
<a id="atlas-publish-001"></a>- [ATLAS-PUBLISH-001](backlog/atlas-publish-001.md) — OIDC publish pipelines and Pages alignment [patch] — in-progress
<a id="atlas-publish-001-book-mdbook-test-001"></a>- [ATLAS-PUBLISH-001-BOOK-MDBOOK-TEST-001](backlog/atlas-publish-001-book-mdbook-test-001.md) — Cross-book `mdbook test` gate alignment [patch] — blocked
<a id="atlas-cfdrs-leto-sparse-migration-001"></a>- [ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001](backlog/atlas-cfdrs-leto-sparse-migration-001.md) — Migrate CFDrs direct_solver to SparseLuSolver::solve_view [minor] — todo
<a id="atlas-version-guard-001"></a>- [ATLAS-VERSION-GUARD-001](backlog/atlas-version-guard-001.md) — Manifest-version guard and stack coherence check [patch] — in-progress
<a id="atlas-overlay-001"></a>- [ATLAS-OVERLAY-001](backlog/atlas-overlay-001.md) — Generated [patch] overlay for local-vs-git coherence [patch] — in-progress
<a id="atlas-worktree-clones-001"></a>- [ATLAS-WORKTREE-CLONES-001](backlog/atlas-worktree-clones-001.md) — Reconcile standalone clones under `worktrees/` [patch] — in-progress
<a id="atlas-leto-peer-wip"></a>- [ATLAS-LETO-PEER-WIP](backlog/atlas-leto-peer-wip.md) — Leto uncommitted peer WIP [patch] — blocked
<a id="atlas-hygiene-baseline-001"></a>- [ATLAS-HYGIENE-BASELINE-001](backlog/atlas-hygiene-baseline-001.md) — Eleven-class conformance baseline and namespace hygiene [patch] — in-progress
<a id="atlas-lane-audit-001"></a>- [ATLAS-LANE-AUDIT-001](backlog/atlas-lane-audit-001.md) — Lane-root sweep results and residuals [patch] — in-progress
<a id="atlas-cfdrs-athena-migration-001"></a>- [ATLAS-CFDRS-ATHENA-MIGRATION-001](backlog/atlas-cfdrs-athena-migration-001.md) — Stage B: CFDrs to Athena [major] [arch] — in-progress
<a id="atlas-code-index-001"></a>- [ATLAS-CODE-INDEX-001](backlog/atlas-code-index-001.md) — Search-ladder infrastructure for context economy [patch] — in-progress
<a id="atlas-cfdrs-chain-ladder-001"></a>- [ATLAS-CFDRS-CHAIN-LADDER-001](backlog/atlas-cfdrs-chain-ladder-001.md) — Consolidate the two tiered ladders [patch] — in-progress
<a id="atlas-jfnk-matrix-free-gmres-001"></a>- [ATLAS-JFNK-MATRIX-FREE-GMRES-001](backlog/atlas-jfnk-matrix-free-gmres-001.md) — Converge JFNK onto Athena [minor] — todo
<a id="atlas-stack-leto-churn-017"></a>- [ATLAS-STACK-LETO-CHURN-017](backlog/atlas-stack-leto-churn-017.md) — Upstream working-tree churn blocks consumer verification — todo
<a id="atlas-dmri-io-001"></a>- [ATLAS-DMRI-IO-001](backlog/atlas-dmri-io-001.md) — Rank-generic acquisition-series I/O [minor] — in-progress
<a id="atlas-coeus-nlls-004"></a>- [ATLAS-COEUS-NLLS-004](backlog/atlas-coeus-nlls-004.md) — original specification — todo
<a id="atlas-apollo-realsh-005"></a>- [ATLAS-APOLLO-REALSH-005](backlog/atlas-apollo-realsh-005.md) — original specification — todo
<a id="atlas-dmri-denoise-008"></a>- [ATLAS-DMRI-DENOISE-008](backlog/atlas-dmri-denoise-008.md) — MP-PCA denoising and Gibbs unringing [minor] — todo
<a id="atlas-dmri-correct-009"></a>- [ATLAS-DMRI-CORRECT-009](backlog/atlas-dmri-correct-009.md) — Motion, eddy-current, and susceptibility correction [minor] — review
<a id="atlas-ritk-fssurf-013"></a>- [ATLAS-RITK-FSSURF-013](backlog/atlas-ritk-fssurf-013.md) — FreeSurfer surface formats and label table [minor] — todo
<a id="atlas-dmri-tractogram-fmt-014"></a>- [ATLAS-DMRI-TRACTOGRAM-FMT-014](backlog/atlas-dmri-tractogram-fmt-014.md) — Tractogram container ownership [arch] — todo
<a id="atlas-cfdrs-lint-floor-001"></a>- [ATLAS-CFDRS-LINT-FLOOR-001](backlog/atlas-cfdrs-lint-floor-001.md) — Adopt canonical Atlas lint floor in CFDrs workspace [patch] — in-progress
<a id="atlas-cfdrs-ci-workspace-rust-001"></a>- [ATLAS-CFDRS-CI-WORKSPACE-RUST-001](backlog/atlas-cfdrs-ci-workspace-rust-001.md) — Add Rust workspace CI gate to CFDrs [patch] — in-progress
<a id="atlas-kwavers-default-recheck-2026-08-18"></a>- [ATLAS-KWAVERS-DEFAULT-RECHECK-2026-08-18](backlog/atlas-kwavers-default-recheck-2026-08-18.md) — moving default remains open — todo
<a id="atlas-mnemosyne-default-recheck-2026-08-18"></a>- [ATLAS-MNEMOSYNE-DEFAULT-RECHECK-2026-08-18](backlog/atlas-mnemosyne-default-recheck-2026-08-18.md) — moving default remains open — in-progress
<a id="atlas-mnemosyne-default-recheck-2026-08-19"></a>- [ATLAS-MNEMOSYNE-DEFAULT-RECHECK-2026-08-19](backlog/atlas-mnemosyne-default-recheck-2026-08-19.md) — moving default remains open — todo
<a id="atlas-cfdrs-hosted-2026-08-19"></a>- [ATLAS-CFDRS-HOSTED-2026-08-19](backlog/atlas-cfdrs-hosted-2026-08-19.md) — exact default-head evidence — in-progress
<a id="atlas-kwavers-delivery-2026-08-19"></a>- [ATLAS-KWAVERS-DELIVERY-2026-08-19](backlog/atlas-kwavers-delivery-2026-08-19.md) — wheel and book gate closure — todo
<a id="atlas-kwavers-metadata-2026-08-19"></a>- [ATLAS-KWAVERS-METADATA-2026-08-19](backlog/atlas-kwavers-metadata-2026-08-19.md) — Python surface consistency — blocked
<a id="atlas-cfdrs-jfnk-rerun-2026-08-19"></a>- [ATLAS-CFDRS-JFNK-RERUN-2026-08-19](backlog/atlas-cfdrs-jfnk-rerun-2026-08-19.md) — hosted infrastructure retry — in-progress
<a id="atlas-kwavers-book-fence-2026-08-19"></a>- [ATLAS-KWAVERS-BOOK-FENCE-2026-08-19](backlog/atlas-kwavers-book-fence-2026-08-19.md) — restore truthful mdBook fence semantics [patch] — in-progress
<a id="atlas-conformance-submodule-status-2026-08-19"></a>- [ATLAS-CONFORMANCE-SUBMODULE-STATUS-2026-08-19](backlog/atlas-conformance-submodule-status-2026-08-19.md) — classify provider dirt after root status [patch] — in-progress
<a id="atlas-conformance-ratchet-2026-08-19"></a>- [ATLAS-CONFORMANCE-RATCHET-2026-08-19](backlog/atlas-conformance-ratchet-2026-08-19.md) — exact provider regressions [patch] — blocked
<a id="atlas-worktree-takeover-107"></a>- [ATLAS-WORKTREE-TAKEOVER-107](backlog/atlas-worktree-takeover-107.md) — stale-lane sweep across the stack [patch] — in-progress
<a id="atlas-cross-member-sweep-108"></a>- [ATLAS-CROSS-MEMBER-SWEEP-108](backlog/atlas-cross-member-sweep-108.md) — cross-member staleness and dirt sweep [patch] (2026-08-23) — in-progress
<a id="atlas-cfdrs-stale-example-pages-001"></a>- [ATLAS-CFDRS-STALE-EXAMPLE-PAGES-001](backlog/atlas-cfdrs-stale-example-pages-001.md) — Book example pages for deleted examples [docs] [patch] [S] — todo
<a id="atlas-board-closure-canon-001"></a>- [ATLAS-BOARD-CLOSURE-CANON-001](backlog/atlas-board-closure-canon-001.md) — Canonicalize historical closure markers [pm-hygiene] [patch] [M] — in-progress
<a id="kwavers-ci-pipeline-001"></a>- [KWAVERS-CI-PIPELINE-001](backlog/kwavers-ci-pipeline-001.md) — Consolidate kwavers CI to one verification pipeline [ci] [patch] — todo
<a id="atlas-runner-capacity-001"></a>- [ATLAS-RUNNER-CAPACITY-001](backlog/atlas-runner-capacity-001.md) — Size runner slots to fleet width [infra] [patch] — todo
<a id="atlas-branch-inventory-001"></a>- [ATLAS-BRANCH-INVENTORY-001](backlog/atlas-branch-inventory-001.md) — Burn down stack branch inventories [git-hygiene] [patch] — in-progress
<a id="cross-balance-remediation"></a>- [ATLAS-CROSS-BALANCE-EDGE-REMEDIATION-2026-09-04](backlog/cross-balance-remediation.md) — Route the four cross-balance edges through harmonia [minor] — todo
<a id="sibling-named-crates"></a>- [ATLAS-SIBLING-NAMED-CRATES-2026-09-04](backlog/sibling-named-crates.md) — Nine crates are named after a sibling member, not a concern [arch] [major] — todo
<a id="python-pipeline-pin-divergence"></a>- [ATLAS-PYTHON-PIPELINE-PINS-2026-09-04](backlog/python-pipeline-pin-divergence.md) — No published wheel covers ARM Linux or musl [patch] — in-progress
<a id="hook-fleet-duplication"></a>- [ATLAS-HOOK-FLEET-DUPLICATION-2026-09-06](backlog/hook-fleet-duplication.md) — Twenty-two hand-maintained copies of two git hooks [patch] — in-progress
<a id="mnemosyne-pin-campaign-stranded"></a>- [ATLAS-MNEMOSYNE-PIN-CAMPAIGN-STRANDED-2026-09-06](backlog/mnemosyne-pin-campaign-stranded.md) — A provider-pin campaign stalled undelivered in five members [patch] — todo
<a id="slop-burndown"></a>- [ATLAS-SLOP-BURNDOWN-2026-09-06](backlog/slop-burndown.md) — Measured debt burn-down against the conformance ratchet [patch] — in-progress
<a id="moirai-06-sweep"></a>- [ATLAS-MOIRAI-06-SWEEP-2026-09-06](backlog/moirai-06-sweep.md) — Moirai 0.6.0 landed without its forward sweep [patch] — in-progress
<a id="bare-git-pin-staleness"></a>- [ATLAS-BARE-GIT-PIN-STALENESS-2026-09-08](backlog/bare-git-pin-staleness.md) — A version-less git dependency freezes at its first resolution [patch] — todo
<a id="apollo-quarantine-lift"></a>- [ATLAS-APOLLO-QUARANTINE-LIFT-2026-09-08](backlog/apollo-quarantine-lift.md) — Apollo's moirai rev pin can now be removed [patch] — todo
<a id="crlf-stored-blobs"></a>- [ATLAS-CRLF-STORED-BLOBS-2026-09-08](backlog/crlf-stored-blobs.md) — Committed blobs contradict the declared line-ending policy [patch] — in-progress
<a id="ratchet-regression-set"></a>- [ATLAS-RATCHET-REGRESSION-SET-2026-09-08](backlog/ratchet-regression-set.md) — Seven ratchet regressions arrived with peers' merges [patch] — todo
<a id="atlas-helios-bench-local-instrument-2026-09-18"></a>- [ATLAS-HELIOS-BENCH-LOCAL-INSTRUMENT-2026-09-18](backlog/atlas-helios-bench-local-instrument-2026-09-18.md) — helios runs wall-clock benchmark regression on hosted CI [arch] — todo
