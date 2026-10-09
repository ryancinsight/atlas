# atlas — cross-repository integration gap audit

<!-- Compacted 2026-09-26 under the 1,000-line board budget: a risk entry holds risk/evidence/re-open-trigger/owner in ~5 lines; closed findings and delivery narrative are gone -- the record of a closed finding is the commit or PR that closed it. Recover removed narrative with `git log -p -- gap_audit.md`. -->

## Finding 2026-10-05: path-package identity follows repository revision

Risk: an unrelated commit can invalidate unchanged path-package records and trigger shared-target cleaning. Evidence: `atlas_build_inputs.py` assigns every path package one repository identity, and a clean tree's identity includes that repository's commit revision; observed contention is consistent with this static mechanism, but no benchmark attributes its runtime share. A replacement fingerprint must retain workspace/config, external, build-script, and Git-derived inputs rather than hashing `src/` alone. Owner: none. Re-open: a measured build-input redesign item is claimed.

## Finding 2026-10-02: no check enforces the bare-cast rule

Risk: new bare `as` casts land unmeasured; the cast rule (engineering_gates: lint floor) names a push-time check that does not exist (`git grep -i -E 'force-warn|as_conversions' -- scripts` is empty at origin/main 2026-10-02). Check that would catch it: the owned pre-push clippy run adds `--force-warn clippy::as_conversions --message-format=json`, dedupes by span, excludes by path the conversion module (`repos/eunomia/crates/eunomia/src/convert/count.rs`) and each crate's cast module, fails on a site on an added line or a crate count above its row in `scripts/conformance-baseline.json`. Owner: none. Re-open: the next hook change.

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
