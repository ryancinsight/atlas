# atlas — cross-repository integration gap audit

<!-- Compacted 2026-09-26 under the 1,000-line board budget: a risk entry holds risk/evidence/re-open-trigger/owner in ~5 lines; closed findings and delivery narrative are gone -- the record of a closed finding is the commit or PR that closed it. Recover removed narrative with `git log -p -- gap_audit.md`. -->

## Finding 2026-10-05: path-package identity follows repository revision

Risk: an unrelated commit can invalidate unchanged path-package records and trigger shared-target cleaning. Evidence: `atlas_build_inputs.py` assigns every path package one repository identity, and a clean tree's identity includes that repository's commit revision; observed contention is consistent with this static mechanism, but no benchmark attributes its runtime share. A replacement fingerprint must retain workspace/config, external, build-script, and Git-derived inputs rather than hashing `src/` alone. Owner: none. Re-open: a measured build-input redesign item is claimed.

## Finding 2026-10-02: the bare-cast gate runs only where the current hook runs

Risk: new bare `as` casts land unmeasured wherever the owned pre-push hook is not the current one. The gate (`scripts/atlas_cast_gate.py`, called from the hook's clippy step under the stack's identity leases) reaches only registered members of a stack whose fetched default carries the gate; a standalone clone resolves neither the stack scripts nor a registered member name, so its hook skips the gate; no CI job runs `atlas_cast_gate.py check`, so an admin merge or a push from an old hook lands casts no check counted. Check that would catch it: a member CI job running the gate on the pull-request range. Owner: none. Re-open: a merged cast on an added line in any member.

## Finding 2026-10-02: the bare-cast gate sees one configuration

Risk: clippy reports only casts it compiles: default features and the host target. A cast behind a non-default feature or another target's `cfg` passes on an added line, and a cast inside a `macro_rules!` body is one site at the body however many call sites expand it (probe 2026-10-02), so a new call of an existing casting macro adds none. Rows are measured `--workspace`, push counts `-p`. The push count is also held to the pushed base's count under the same selection when the range renames a file or changes a `Cargo.toml`, a package-root `build.rs`, `.cargo` config or `rust-toolchain` file (`base-triggers`; the base build costs one more closure build, 394-513 s for leto-ops measured 2026-10-03 under lock contention, so it does not run on every push): a moved file or a feature change cannot fill the difference. A source-level `cfg` flip, `#[path]`, `include!`, a new `mod` line naming a file not compiled before, or a build script at a custom `package.build` path or in a helper module triggers nothing and is held to the row alone. Only pushed packages are counted: a pushed package enabling a feature of an unpushed dependency compiles that dependency's casts unmeasured. A manifest whose base fails to compile in its own packages (a rustc error or a denied lint, with cargo naming one of them) leaves those packages to their rows (said on the push), so a fix to a default branch broken in its own source stays pushable; a base broken in a dependency, by unreadable or mismatched crate metadata, or by a compiler that exited abnormally (killed, out of memory, crashed, silent, or panicked: cargo's `Caused by: process didn't exit successfully`) refuses. Cargo's summary must say `due to N previous error`; a compiler fault that still prints that summary and no `Caused by` would pass as a compile error. Code under `cfg(not(feature = ...))` can lift a clean `-p` count above its row (the 2026-10-02 review found no row it breaks). Check that would catch it: run the gate under the feature matrix (`cargo hack --each-feature`) in the scheduled member CI job. Owner: none. Re-open: a cast found in feature- or target-gated code after merge, or a count failure on a push that adds no cast.

## Finding 2026-10-02: the pre-push gate skips the feature matrix CI checks

Risk: a change that compiles only with default features passes pre-push and fails CI. Evidence: ryancinsight/eunomia#143 (its pushed head before the no-std test fix) passed the owned pre-push gate; CI's `cargo check --all-targets --no-default-features` failed (`to_string` with no `std` in a test). The hook runs clippy and nextest with the default or CI-lint feature set only. Check that would catch it: the hook runs each member's committed feature-matrix list, as `cargo check` on the changed packages. Owner: none. Re-open: the next hook change, or the next CI-only feature failure.

## Finding 2026-09-28: staged revert of dependency-digest memoization in the shared main tree

Risk: `D:/atlas` (main, at `7b14277be`) carries staged, uncommitted changes that delete `scripts/atlas_build_package_source.py` and its tests and revert `6538f5b09`; a pathspec-free commit from that tree would clobber landed work. Evidence: `git status --porcelain -- scripts` shows `D  scripts/atlas_build_package_source.py`; index written 16:22 local, no lease line. Owner: none found. Re-open: the next orientation of the main tree; triage per fix-forward (the staged hunks are reverts, not landed work).

## Finding 2026-09-24: Dioxus joins the GUI comparator set

Metis [ADR 0003](repos/metis/docs/adr/0003-framework-conformance.md) now pins
Dioxus 0.7.10 as a comparator (closest Rust GUI framework: one component tree
to browser/desktop/mobile WebViews plus a native wgpu renderer). First pass
closed state/routing gaps in Metis (PR #400) and native menu bars in Moirai
(PR #468). Open: nested layouts with history, SSR/hydration, Rust hot
patching, mobile bundles. The stack owns no Dioxus dependency; it is an
evidence comparator, not a requirement. Re-open trigger: a Dioxus minor
release, when the ADR table is re-read against the new crates.

## Finding 2026-09-09: six members enforce no merge gate

hermes, eunomia, leto, mnemosyne, moirai, and themis carry neither branch
protection nor rulesets, so a PR merges whatever CI reports — their green
history is a property of who has been merging, not of the repository. Each
needs its required contexts named from its own workflow, and `strict` must
ship with `allow_update_branch = true` (the fix already applied to Apollo and
Hephaestus after `strict` alone stalled auto-merge on a `BEHIND` branch).
Re-open trigger: any member merging a red PR, or the next merge-mechanics
pass.

## Finding 2026-08-21: print_dbg — not a safe mechanical sweep

`print_dbg` counts ~285 real production sites (CFDrs 257, ritk 17, kwavers
44 minus overlap, hermes 4) behind `println!`/`eprintln!`/`dbg!`, plus ~31
`build.rs` Cargo-protocol false positives and ~50 xtask/scratch sites. Each
real site needs a per-crate migration to a logging facade (`tracing`); it is
provider-owned, not an Atlas-side mechanical sweep. Re-open trigger: a
provider crate adopts `tracing` and the scanner's `build.rs` false-positive
class is fixed (exempt `cargo:` protocol writes).

## Finding 2026-08-21: missing_deny_docs — not a safe editorial sweep

`missing_deny_docs` counts 118 `lib.rs` files across 12 repos; 114 have
undocumented public items even in `lib.rs` alone, so adding
`#![deny(missing_docs)]` would break compilation. Only 5 crates have `lib.rs`
fully documented, and `deny(missing_docs)` applies crate-wide, so submodules
still need verification. Per-crate doc work is provider-owned (tracked by
ATLAS-KWAVERS-ALLOC-PROBE-DENY-DOCS-2026-08-21 for the kwavers pilot). Not an
Atlas-side editorial sweep.

## Finding 2026-09-21: rev-pin churn silts up the shared cache

A `rev =` advance on a first-party git dependency is a new source identity:
cargo compiles a fresh generation and never reclaims the old one. Fingerprint
directories per distinct build unit run 3-14x over baseline for repeatedly
re-pinned crates (mnemosyne 140/9, moirai 197/15) against unchurned themis
(41/1). `scripts/atlas-cache-retention.py` names the general eviction problem
but its units (profiles, `incremental/` children) don't reach per-rev
`deps/`/`.fingerprint` generations, and nothing invokes it from CI. Re-open
trigger: fingerprint-directories-per-build-unit exceeds ~2x for any
first-party crate in the shared cache.

## Finding 2026-08-20: target_forks regrows faster than the ratchet can see it

`is_cargo_target_dir` correctly reads 0 for registered members, but the class
is in `HOST_OBSERVED_CLASSES` and forced to 0 in the baseline regardless —
so a real regrowth reads as resolved. Two structural causes, not config
holes: cargo resolves configuration from cwd upward, so `repos/.cargo/
config.toml` never reaches a `--manifest-path` invocation run from outside
`repos/`; and a per-purpose directory (`ci-wheel-target/`, `bench-
replicated/`) bypasses any shared-cache config by construction. A private
per-member `target-dir` (e.g. asclepius) also defeats sharing while reading
as 0. Re-open trigger: any `repos/<member>/target*` satisfies
`is_cargo_target_dir` again, or the class is moved out of
`HOST_OBSERVED_CLASSES`.

## Finding 2026-08-20: Kwavers distributed queue remains externally gated

[Kwavers PR #427](https://github.com/ryancinsight/kwavers/pull/427) has `mergeStateStatus=DIRTY` with no
required provider verification; the primary checkout is detached at that head
with nine peer-owned edits, and excess `worktrees/kwavers-*` lanes remain.
Atlas's Kwavers gitlink already matches hosted-green default `9cf62aa9`.
Rebasing, switching, or advancing would overwrite peer work. Owner: kwavers
PR author. Re-open trigger: PR #427 resolves or its branch goes stale under
the one-hour sweep.

## Finding 2026-08-19: Apollo PR #107 benchmark remains red

Apollo PR #107 (head `d408c738`) fails 17 counterbalanced benchmark cases
(sizes 64/96, Rader f32/31 and f64/53, composite primes), candidate slower in
all four orderings — an empirical performance residual, not a tolerance or
workload issue. No merge or instrument change is authorized until root-cause
profiling lands on the active branch. Re-open trigger: a profiled fix changes
the measured comparison.

## ATLAS-CFDRS-TEST-BUDGET — exact provider-head runtime residual (reopened 2026-08-17)

Two `cfd-validation` numerical-fidelity tests (`microventuri_35um_case_...`,
`cross_fidelity_trifurcation_dominance`) exceed the unchanged 30 s nextest
budget; the timeout is inherited from the production solver path, so no
workload or budget change is authorized. First bounded slice landed (CFDrs
PR #347, merged `84499e957`): removed a per-correction clone of the immutable
pressure CSR matrix, brought both cases to ~16.8 s locally. Re-open trigger:
the exact-head hosted run against the current budget; the broader
solver-budget residual remains open pending further profile-first slices.

<a id="atlas-us-capability-023"></a>
## ATLAS-US-CAPABILITY-023 — kwavers/ritk capability audit vs ITKUltrasound (open 2026-08-13)

Reference: `KitwareMedical/ITKUltrasound`, enumerated from its own tree (63
public headers) and verified per-capability against kwavers/ritk sources.
Present with no gap: analytic-signal, B-mode, TGC, box-sigma smoothing,
least-squares strain, block-matching parabolic interpolation, the VTK
structured-grid sink half, and the FFT backend role. Partial: curvilinear
scan conversion (2-D only, no inverse direction), 1-D frequency-domain
filtering (no N-D image seam), ultrasound HDF5 I/O, and block-matching
displacement estimation (ritk has only a scalar autodiff NCC metric).

Sub-findings, still open:
- **D3 placement (ATLAS-D3-PLACEMENT-034):** `block_matching` is
  dependency-light (imports only `anyhow`) but lives in `ritk-registration`,
  which pulls the full coeus autograd/nn/wgpu stack — forcing a physics
  crate to choose between a mandatory optional dependency or hiding a core
  kernel behind a feature flag. Corrective step (US-023-D4, not yet filed as
  its own item): move `block_matching` into a new dependency-light crate,
  the same pattern US-023-A5 used for the coordinate map into `ritk-spatial`.
- **Asymmetric fan (ATLAS-US-A3-FAN-028):** kwavers' and ritk's inverse
  curvilinear-fan maps agree on everything except the beam index; ritk's fan
  cannot express kwavers' asymmetric fan as filed. Unresolved as of last
  read.
- A3's original "delete the converter" plan was corrected: `CoordinateMap`/
  `CurvilinearArray`/`PhasedArray3D` moved to `ritk-spatial` (US-023-A5,
  merged via ritk PRs #132/#133), unblocking A3's remaining split (kwavers
  delegates polar math, keeps its own storage).

Open findings register (RITK-CI-1, US-023-A2) live on the owning item,
[ATLAS-US-CAPABILITY-023](backlog.md#atlas-us-capability-023).

<a id="atlas-ritk-ci-diag-035"></a>
## ATLAS-RITK-CI-DIAG-035 — RITK-CI-1 diagnosis (open)

Diagnosis, not a fix (another author's deliberate change): `3aa73ba0`
*fix(ritk-filter)!: Apply the direction matrix in index<->physical
transforms* (ADR 0020) is the origin. ADR 0020 claims axis-aligned tests
pass, but the three failing SimpleITK parity tests use identity
direction/zero origin/unit spacing — the axis-aligned case — contradicting
that claim; they run only in the Python-wheel smoke job, separate from Rust
suites, which is likely why they went unseen. Deviations: 2-D inverse
displacement field max error 2.23 (gate 1e-4), 3-D 0.082, iterative 0.171.
Owner: `3aa73ba0`'s author. Oracle: the three `test_simpleitk_cmake_data.py`
parity tests pass.

<a id="atlas-usct-fwi-024"></a>
## ATLAS-USCT-FWI-024 — kwavers audit vs FullWaveformInversionUSCT (open 2026-08-13)

Reference: `rehmanali1994/FullWaveformInversionUSCT` (Ali, SPIE Medical
Imaging 2022, Vol. 12038) — frequency-domain transmission-USCT FWI via the
angular-spectrum/split-step method, NLCG with Gilbert-Nocedal hybrid beta and
a linearized exact line search. Verdict: kwavers exceeds the reference on
forward-model rigor (convergent Born series beats split-step) and optimizer
machinery (source-scaling identifiability accounting), and is ahead overall;
residual gaps (F1/F2) are small and independently verifiable against the
reference. Owning item: [ATLAS-USCT-FWI-024](backlog.md#atlas-usct-fwi-024).

## Finding: kwavers legacy-migration residual (nalgebra/ndarray/burn/rayon)

Last measured 2026-07-08: kwavers still carried direct `nalgebra` at ~13
sites/5 manifests, `ndarray` at ~1,660+ line-hits across all 24 crates (only
1 crate on `leto`'s `ndarray-compat`), 41 residual `Zip::par_for_each` sites
pending a `moirai_parallel` migration, and a transitive `rayon` edge via
`ritk -> burn`. Three months of continuous kwavers development have passed
since this was measured — treat every count here as stale; re-measure via
`scripts/atlas-conformance.py` rather than trust this narrative. Owner:
unclaimed (provider-side). Re-open trigger: none filed; a re-audit is due
before this finding is cited as current.

## Finding: ATLAS-KWAVERS-REAL-COMPUTE-028's evidence is missing from this file

`backlog/atlas-kwavers-real-compute-028.md` cites
`gap_audit.md#atlas-kwavers-real-compute-028` for exact identity-return-path
locations, but that finding was dropped in the 2026-09-21 compaction pass and
never reconstructed here — the link is dangling. Do not fabricate the
locations; re-run the identity-path audit named in that item's outcome and
refile the finding under this anchor. Re-open trigger: the item is next
claimed.

## Shared incremental-cache growth — open

`target/debug/incremental` accumulated 27,085 session directories / 525 GB
in five days stack-wide; an idle-tree prune reclaimed the bytes but the
recurrence cause (no incremental-disable on clean CI runners, ~950 leaf
binary targets per ATLAS-BUILD-STRUCTURE-001) is unfixed. Re-open trigger:
the next clean Kwavers architecture run, to compare artifact bytes and peak
memory against the preferred 10 GiB clean-build budget.

## Finding 2026-08-18: three provider-consumer PRs unmergeable

Apollo PR #104/#106 (apollo-fft 0.26→0.27 lock drift; #106 has the fix, local
evidence green, hosted pending), Kwavers PR #402 (benchmark green, full
matrix red across architecture/validation/security/coverage/CUDA/wheel), and
Helios PR #64 (draft; Rust/Python/book green, benchmark in progress). No
Atlas gitlink advances from any of these until their own hosted gates are
terminal green. Re-open trigger: each PR's own hosted result.

## Finding 2026-09-04: apollo main red — triple-versioned mnemosyne (resolved)

**Resolved 2026-09-04:** apollo `ci` green on `8ce18e57` via Eunomia source
unification (#324). **Residual watchpoint:** apollo still carries the
temporary co-evolution pin `mnemosyne rev = "af7a23a"`, whose own comment
orders its removal after Mnemosyne PR #128 — if that PR has merged and the
pin remains, the quarantine has outlived its trigger. Verify against
mnemosyne's merge log before re-firing the sweep.

## Finding 2026-09-24: member pre-push reads the secret scanner from the live stack tree

`scripts/git-hooks/pre-push` runs the scanner checked out in the local stack
tree, not the one its debt ratchet extracts from the fetched default; a tree
on a branch older than the scanner lets member pushes skip the scan (CFDrs
#459, kwavers #850, Moirai #471 all did on 2026-09-24). Re-open trigger: the
hook extracts the scanner from `$stack_baseline`, as `sync-hooks --check`
already does.

## Finding 2026-09-25: cfd-math `ParallelAssembly::from_elements` is dead public surface

No stack consumer, caller, test, or doctest anywhere in the fleet
(`git grep from_elements` over CFDrs `origin/main` finds only the
definition). `cfd-math` is publishable, so removal is breaking. Re-open
trigger: a first consumer appears, or the next major removes it.

## Finding 2026-09-25: apollo-sft recovery bench fixture costs 137s against its 60s budget

`benches/recovery.rs` builds its input signal with O(N·K) trig at N=2^20,
K=16 before measurement starts — a fixture-design defect, not measured code.
Re-open trigger: the fixture drops the per-sample trig loop, or N shrinks
with the scaling-ratio claim preserved.

## Finding 2026-09-25: the hook publisher compares member working trees, not their defaults

`atlas-lock-form.py publish-hooks` diffs `repos/<member>/.githooks/` bytes
against a stale local checkout instead of `origin/HEAD`, so a reused sync
branch can republish another writer's hook — on 2026-09-25 this landed a
no-op hook over a UTF-16 copy on 24 members. Re-open trigger: the comparison
reads `origin/HEAD` in the member, as `sync-hooks --check` already
contracts.

## Finding 2026-10-08: `gh pr` subcommands without an explicit number act on the shared checkout's peer PR

`gh pr merge`/`view`/`ready`/`checks` with no `<number>` resolves to the
current branch's PR, and in shared trees the checkout routinely sits on a
peer's branch — so a bare invocation reads, readies, or auto-merges the
*peer's* PR. Observed twice in one session (2026-10-08): the peer PRs
atlas#512 and athena#99 were merged by commands aimed at freshly created
branches whose PRs the same shell had just failed to select. Both were
ready and green so landing matched their authors' intent, but the
invocation's target is what was hit-or-miss, and a draft or red peer PR
would not have been safe to touch. Root cause: the CLI's current-branch
default combined with checkout tenancy. Catching check: any agent-side
wrapper (or review grep) rejects `gh pr (merge|view|ready|checks)`
invocations lacking an explicit `<number>` when more than one open PR
exists. Re-open trigger: that wrapper lands in the stack tooling.

## Finding 2026-10-09: provider moves leave their exports below the crate root

Twice in one day a moved capability reached the owner's submodule
re-export list but not the crate-root `pub use` every sibling item
travels (leto#343: `solve_csr_via_dense_lu`; athena#103: the four saddle
preconditioners) — both first surfaced as consumer E0432s at the next
integration, not in the provider's own gates, because the provider's
tests import within the crate. Root cause: the moves edit the module
manifest but treat the root export list as untouched surface. Catching
check: for each moved pub item, the provider's PR checklist asserts the
crate-root `pub use` gained the name — mechanically, a one-line script
comparing the module's exports against the root list. Re-open trigger:
that check lands in the stack tooling.

## Finding 2026-10-13: leto-ops cast row 590 vs measured 715 blocks every leto-ops push

Risk: the cast-gate baseline row (590, basis 6d0eca392) is 125 sites behind current main (715, measured via atlas_cast_gate.py --present-only at origin/main): the growth arrived through rescue/secret-scan-only pushes and scripts-scoped landings whose changed-path scoping never selected leto-ops. The first leto-ops-touching push after them (the Bessel branch, leto#351) is blocked; every subsequent one will be. Rows only fall, so the 125 sites convert: the concentration is tests/ops/backward_error.rs (55) and tests/ops/migration_fixtures.rs (40), then matrix/generic_kernel (37), reduction/axis (33), reduction/topk (25). Owner: none. Re-open: the conversion lands and leto#351 pushes green.

## Metis Apple setup — 2026-10-11

Native host toolchain and local Metis build isolation are implemented; the same
browser assets package in macOS/iOS apps. Browser computed values and process
cleanup are verified; native macOS/simulator signing/plist and iPhone/iPad
simulator install/launch and packaged WASM delivery pass. Real-source native
reload, failed-compile preservation and child cleanup pass. After Mac unlock,
native Greet clicks return exact Rust results for normal, Unicode and empty
names; remaining native lifecycle and Safari evidence stay open. The physical iPhone is unavailable
and no valid signing identity exists. The iPad simulator reports duplicate Apple
accessibility classes; interactive validation remains required. Moirai sources
reach its default branch through PRs 606/607. Metis reaches its default branch
through PR 491 after Windows, Apple and full fuzz gates pass. Atlas's pointer
commit advances both defaults. Metis standalone workspace and
fuzz locks resolve the exact provider revision; path locks remain derived development
artifacts. The full overlay audit still reports RITK's three Metis 0.1 requirements
and older compatible Moirai pins in other consumers; the generated overlay leaves
incompatible edges on Git. Metis verification covers its scoped graph. Track the remaining
work in [ATLAS-METIS-APPLE-SETUP](backlog/metis-apple-setup.md).

Atlas [PR 530](https://github.com/ryancinsight/atlas/pull/530) is pushed and has
no merge conflicts; both component pointers match their published defaults.
Its Python suites and CodeQL checks pass. The integration checks fail on the
newer component hook versus the pinned fleet (`member_gate_versions: 1 -> 2`),
RITK's three Metis 0.1 requirements, 14 consumer lock drifts and 24 other stale
member pins. At that verification point, the hook's canonical source remains in draft Atlas PR 450; it later merges on 2026-10-12 at `b94ee304`.
These results prevent the Atlas default-branch merge; the Apple component
delivery does not establish whole-stack coherence.

The native Greet failure is reproduced on 2026-10-12: packaged WASM loads with
Fetch status zero, so wasm-bindgen rejects before binding the submit handler.
Merged Moirai PR 608 supplies moirai-webview 0.1.1's shared status-200/MIME/length
response contract; Metis 0.2.1 requires that version and resolves both locks to
the merged provider. Eight provider tests, 678 Metis tests, 42 documentation
tests and 60 consumer Python checks pass. Native macOS clicks verify the Rust
results; all three frozen Apple bundles build. CoreSimulator installs/launches
the corrected app, but its GUI client is absent from the installed Xcode tree.
Metis PR 492 merges after Windows, Apple and the complete fuzz campaign pass;
Atlas records both merged defaults in a separate pointer-only commit.

## Metis Rust browser increment — 2026-10-12

The workbench and HTTP page move policy, protocol and lifecycle behavior into
Rust. The authored application JavaScript count is 505→9; generated bindings
remain. Moirai PRs 611/612/613 deliver bounded Fetch, real stream dictionaries,
reply-listener ordering and bodyless response semantics through protected
checks. Gaia PR 169 admits the shared provider graph. Canonical Metis locks
pin Moirai `6c7f39dff127f1accfc02ede4a5d59cb34ec9cc5` and Gaia
`2279ae294ff76bc925a18c65a152bfe64f6e13f0` without unrelated source movement.

Local consumer checks pass: 686 Rust tests, 395 Python tool checks, native/WASM
diagnostics, 784 API comparisons against the actual committed baseline,
22 production wheel tests (four platform-specific skips), all three Apple
bundles and native macOS Greet. Live HTTP acceptance covers complete byte
values, bounds, 304 representation metadata, redirect refusal, deadlines and
peer-observed cancellation, plus reset and listener teardown. API comparison
uses compiler-produced locked rustdoc records because the automatic checker's
fresh baseline resolution cannot satisfy historical provider requirements.

The Tauri native inventory has 124 admitted pairs: 46 bounded implementations
with remaining acceptance and 78 open pairs. This does not establish full
framework parity, mobile permissions, signed updates or matched performance.
The root merges current main without conflicts; its conformance still reports
`member_gate_versions: 1 -> 2`. The refreshed overlay check reports 18
lagging requirements and 14 consumer repositories with lock drift. Root PR
530 retains its existing integration blockers. Remaining integration state lives in [ATLAS-METIS-APPLE-SETUP](backlog/metis-apple-setup.md).

Metis PR [493](https://github.com/ryancinsight/metis/pull/493) merges at
`aa04a4a9fdbc3d2a6f502ade18e2cf1c58c5de73` after the complete Windows, Apple
and parser campaign pass. Provider/source and artifact checks are green.
Browser runtime jobs are schedule/manual-only and skipped in this PR; local
in-app observations remain distinct from a new cross-engine run.

Delivery records merge through Metis PR 494, Moirai PR 614 and Gaia PR 170.
Atlas pointer-only commit `791d4789e5a7` records Metis
`26f5fe6596c2e4190736ca8655b61b1d315d2d44`, Moirai
`ddde64ef33a2fcd73773e22466fd60c52239f205` and Gaia
`a81f558e4ab1e1ed19b8f1fc6c4c33670a59f9d9` from their published defaults.
The completed Rust browser root item is retired; Root PR 530's
requirement/lock drift and remaining Apple/native evidence stay open.

## Merge reconciliation — 2026-10-12

Atlas merge `d852ab5b` incorporates fetched main `b94ee304` without conflicts,
including merged hook PR 450. All 13 component PRs attached to this task are
merged. The merged publishing, shared stack and Metis launcher checks pass
116 tests within the 60-second bound; the index has no unmerged entries or
added conflict markers. Current-head integration CI remains a separate gate.
The combined backlog reaches 1006 lines against its unchanged 1000-line limit;
duplicate Metis delivery rows and superseded lease findings leave the active
board, retaining its open acceptance criteria and the history below.

Identity-lease history retained from the active board: on 2026-09-30 eight
serial pushes fail the 900-second wait (helios, ritk, hephaestus, kwavers,
metis, CFDrs and Atlas #408 four times); hephaestus and both ritk pushes fail
again on 2026-10-01. A ritk gate holds hephaestus-rocm at ritk's revision.
The initial hypothesis attributes the wait to cross-source artifact records
and proposes source-keyed leases; the 2026-10-02 evidence refutes shared
records, confirms cross-member cleaning and establishes that Cargo 1.97.0
does not distinguish path checkouts in artifact names. The old acceptance
serializes all same-repository pushes and requires isolated before/after
timings; the active corrected acceptance instead excludes duplicate refs,
records each claim's wait/hold and counts the 36-to-3 identity-step reduction.

## Native Greet commands — 2026-10-12

[Moirai PR 615](https://github.com/ryancinsight/Moirai/pull/615) delivers
moirai-webview 0.1.2 with Rust-owned AppKit application, Edit and Window menus.
[Metis PR 495](https://github.com/ryancinsight/metis/pull/495) consumes that
provider in Metis 0.3.1. The installed macOS bundle returns exact Unicode and
empty-name greetings; focused ⌘Q and ⌘W each terminate its process. Native
notifications record minimize/restore, Zoom 800×632→1728×1034→800×632 and
full-screen transitions. The recording badge obscures standard button glyphs;
unobscured visual evidence remains open. All three Apple bundles build under
the canonical Git lock; physical-device signing remains unavailable.

Local acceptance passes 701 Rust tests without skips, 395 script tests,
native/WASM Clippy and both iOS target checks. Both dependency locks retain
their bytes across the locked test and bundle runs. No JavaScript is added.
The nine-line loader count excludes 213 existing JavaScript lines embedded
in Windows form/probe assets; METIS-WEBVIEW-RUST-001 owns their Rust migration.
General native window APIs, mobile permissions and the Tauri inventory's
remaining admitted pairs stay open.

Fetched Atlas main `714bdd16` merges without conflicts. Its four-line board
overflow is removed by consolidating duplicate Metis process-tree scope and
dependency prose and the Apple item's separator; all open acceptance remains.
PR 396 is merged, so its still-undelivered Metis consumer item becomes todo.
Root PR 530's requirement, lock, pin and conformance failures remain separate
from conflict resolution; current-head CI must re-evaluate them.

The real Atlas launcher exposes the canonical lock mutation: unlocked metadata
under its graph-scoped path overlay removes 40 Git source records. The corrected
runner omits dependency patches and locks metadata and compilation; providers
come from the canonical lock while frontend source paths stay live. The two
configuration regressions fail before the change and pass after it, with all
64 selected integration checks passing. Real launcher bundling then preserves
both lock files, verifies the signature and all seven copied resource hashes.
ADR 0069 records the source invariant and rejects restore-after-build masking.

Moirai PR 615 and Metis PRs 495/496 are merged through their protected checks.
The final fetched Metis default is `0abff1687ee178d99691f7d8e4720f1d90731809`;
the Moirai default is `10a828f7e0a8cace10dd30e88e47ce2e64aec6e0`. Atlas
records these defaults in pointer-only commits. The historical [overlay
run](https://github.com/ryancinsight/atlas/actions/runs/38343758270) reports
60 lagging requirements and 18 consumer lock drifts; the [conformance
run](https://github.com/ryancinsight/atlas/actions/runs/38343758462) reports
23 drifted/off-default members and `<meta>/member_gate_versions: 1 -> 2`.
Those results precede the default-branch reconciliation below. No baseline
or waiver changes are added.


## Native logo navigation — 2026-10-13

Moirai PR 616 merges moirai-webview 0.2.0 at
`81656cc6465edff88e1f4158b3be00721aef3118`. The starter's target-blank
logos have no popup handler before this change. A Rust WKUIDelegate now
opens only exact HTTPS destinations declared in signed bundle metadata and
returns no remote WebView. Metis PR 501 merges 0.4.0 at
`731b00d924eddccfdf50b9e17e699ba786f6c113` and declares both destinations. The real
installed macOS logo opens the exact repository URL in Safari and retains
the Unicode Rust greeting. Unlisted, existing-frame and subframe requests
and two executed onload popup attempts yield zero handoffs; the permitted
control yields one. LinkActivated does not prove trusted-event provenance.

Twenty provider tests, 707 consumer Rust tests, 424 script tests without skips
and native/WASM warning-denying checks pass. Ten consumer library surfaces and the provider pass all 196
applicable compatibility checks each; four consumer comparisons use actual
locked compiler rustdoc JSON because fresh Consus resolution has drifted.
All three Apple bundles build without modifying either canonical lock; signed
macOS/simulator metadata carries the exact two-link policy. Physical device
execution/signing and the remaining Tauri/native services stay open. No
authored application JavaScript is added; Windows's 213 existing lines remain.

The fetched Atlas defaults reconcile while preserving active component edits.
The Metis gitlink conflict resolves to its fetched default. The later PR 539
audit merges with an identical content tree, retaining both audit records.
Board content and pointers remain separate; integration CI remains its own gate.

The current Atlas ruleset requires workflow validity and the debt ratchet;
overlay/version coherence and default-pin drift are advisory checks. The
fetched default closes the old hook-version divergence. A full-history scan
against all 29 canonical stores identifies two raw citations to an unmerged
root branch as the entire remaining reference increase (58 to 60). The audit
now cites the actual hosted runs above, restoring 58 without changing the
resolver, baseline or waivers. Current-head CI remains authoritative.

Atlas records the verified Moirai revision above and the merged Metis default
in a gitlink-only commit. The later [Moirai PR 505](https://github.com/ryancinsight/Moirai/pull/505)
changes Windows capture files and leaves moirai-webview unchanged. Its first
verification fails solely because the request is draft; the subsequent
[ready-state run](https://github.com/ryancinsight/Moirai/actions/runs/38418696786)
passes all active gates before merge. The previous failed-result classification
is corrected. [Moirai PR 617](https://github.com/ryancinsight/Moirai/pull/617)
fixes the inclusive capture-byte law and production PNG dependency in 0.8.3.
All active CI passes, including four installed WebView2 preview scenarios and
both unchanged 100-host inputs; 1,278 local tests pass with nine existing
ignored probes. [Metis PR 502](https://github.com/ryancinsight/metis/pull/502)
merges 0.4.1 at `1ef9409b567458c50a547ba3c9257d8ca35b3cf5` after all active
Windows, Apple, compatibility and fuzz gates pass. It replaces PR 499's broken
historical fuzz baseline through the unchanged normal gate. Its 713 Rust/424
script tests, native/Windows/WASM checks and three Apple bundles pass; the
merged tree equals the verified branch. Rust decimal strings preserve full
audit identifiers. [Metis PR 504](https://github.com/ryancinsight/metis/pull/504) replaces the 213-line controllers with Rust; 759 Rust/447 script tests, strict Windows source checks and fresh asset mutation checks pass. [Current protected CI](https://github.com/ryancinsight/metis/actions/runs/38494216094) passes all 447 Windows script tests in 50.149s and Apple 759/42/three-bundle checks. Browser build reports Windows error 1, Incorrect function, before native acceptance; its operation/path remains unidentified. Captured tool diagnostics/status remain visible. Installed acceptance and the retained unattributed pipe leak stay open.
