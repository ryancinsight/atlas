# atlas — cross-repository integration gap audit

<!-- Compacted 2026-09-21 under the 1,000-line board budget: a board is a queue, never a ledger, so closed sections and delivery narrative are gone -- the record of a closed item is the PR that closed it and its `Item:` trailer. Live items, open checkboxes, anchors and open-marked findings are kept. Recover removed narrative with `git log -p -- <this file>`. -->

## Finding 2026-09-24: Dioxus joins the GUI comparator set

The stack's GUI gap analysis lives in one place, Metis
[ADR 0003](repos/metis/docs/adr/0003-framework-conformance.md), and compares
Metis against egui, GPUI, Tauri, Iced, Svelte/SvelteKit and Axum. Dioxus was
missing, although it is the closest Rust comparator: one Rust component tree
styled with HTML/CSS, rendered to the browser, desktop and mobile WebViews,
the server and a native wgpu renderer (Blitz).

Dioxus 0.7.10 is now a pinned comparator there, read from its published
crates (`dioxus`, `-desktop`, `-signals`, `-stores`, `-hooks`, `-router`,
`-fullstack`, `-native`, `blitz-*`). The first pass closed its state and
routing gaps in Metis (`derived2`, field projections, async resources, a
typed router; metis PR #400) and its native menu bars through Moirai
(Moirai PR #468). Nested layouts with history, SSR/hydration, Rust hot
patching and mobile bundles remain open in the ADR's Dioxus table. The stack
still owns no Dioxus dependency: comparators are evidence, not
requirements. Re-open trigger: a Dioxus minor release, when the table is
re-read against the new crates.

## Finding 2026-09-09: auto-merge stalls behind `strict` protection, and six members enforce nothing

Two facts about merge mechanics across the stack, one fixed and one open.

**Fixed — the stall was a generator, not incidents.** Apollo and Hephaestus set
`required_status_checks.strict = true` ("require branches to be up to date").
With several PRs open, every merge invalidates its siblings: they go
`mergeStateStatus: BEHIND`, and an armed auto-merge then sits indefinitely
because auto-merge does not update a behind branch. Observed on
hephaestus#293 (a day), then on apollo #355/#356/#359 twice in one afternoon —
hand-fixed with `gh pr update-branch` four times before the pattern was
root-caused rather than treated.

Cure applied: `allow_update_branch = true` on both repositories, which is what
lets GitHub update an auto-merge PR's branch when its base moves. The gate is
not weakened — `strict` stays on, and the required contexts (`rust workspace`,
`Lockfile integrity`) are unchanged. Setting `strict = false` would have been
the cheaper fix and the wrong one: it merges code never tested against the
trunk it lands on.

The other six members (hermes, eunomia, leto, mnemosyne, moirai, themis) have
no protection, so nothing stalls there — and nothing gates there either, which
is the second finding.

**Open — six members enforce no merge gate.** They carry neither branch
protection nor rulesets, so a PR merges whatever CI reports. Their green
history is a property of who has been merging, not of the repository. Adding
protection is not a mechanical sweep: each needs its required contexts named
from its own workflow, and turning on `strict` without `allow_update_branch`
would import the stall this finding just cured. Re-open trigger: any member
merging a red PR, or the next authorized pass over merge mechanics.

## Finding 2026-08-21: print_dbg assessment — not a safe mechanical sweep

The live conformance scan reports `print_dbg = 366` across 11 repos. The
scanner matches `println!`, `eprintln!`, `print!`, `eprint!`, and `dbg!` in
production (non-test, non-binary) source regions. A per-site assessment
found that the 366 sites fall into three categories, **none of which can be
mechanically swept**:

### Category 1: `build.rs` Cargo protocol (31 sites, false positive)

### Category 2: xtask CLI tooling and scratch files (~50 sites)

### Category 3: Library production code (~285 sites, real debt)

- **CFDrs (257):** `cfd-validation` crate's benchmarking and conservation verification modules print progress output via `println!`. These should use a logging facade (`log` or `tracing`) instead of direct stdout writes.
- **ritk (17):** `ritk-cli` commands (`viewer`, `stats`, `filter`) print user-facing output via `println!`. These are borderline — a CLI library module printing to stdout is architecturally questionable but may be intentional for user-facing command output.
- **kwavers (44):** `xtask` migration audit and architecture validation modules, plus a `fallback` visualization module.
- **hermes (4):** SIMD intrinsic modules print `eprintln!` for hardware capability warnings.

### Classification

### Recommended scanner improvement

## Finding 2026-08-21: missing_deny_docs assessment — not a safe editorial sweep

The Step 4 "Outstanding debt after this turn" section names
`missing_deny_docs = 118` as the natural next Step 5 in the audit-sweep plan.
A per-site assessment across the 118 counted `lib.rs` files (12 repos) found
that **114 of 118** have undocumented public items in the `lib.rs` file alone.
Adding `#![deny(missing_docs)]` to any such crate would break compilation,
since the lint requires every public item in the entire crate (including
submodules) to carry a doc comment.

Only 5 crates have all `pub` items documented in `lib.rs` itself — but even
those require submodule-level verification before the directive can be safely
added, because `deny(missing_docs)` applies crate-wide, not just to `lib.rs`.

**Classification:** unlike Steps 1–4 (structural overlays that don't change
compilation behavior), `missing_deny_docs` requires per-crate source
documentation work owned by each provider. It is not a safe Atlas-side
editorial sweep. The 118-site count is a watchpoint for provider-level
doc-discipline adoption, not a mechanical ratchet the Atlas audit-sweep can
close.

## Finding 2026-08-20: rescued lane dirt still sits in the lane root

The Phase 1 lane inventory this finding carried is superseded: every lane it
named is gone. Counted 2026-09-21: `repos/kwavers` has 2 registered trees,
`repos/CFDrs` 1 and `repos/consus` 1, and none of the eight unregistered
`worktrees/kwavers-*` filesystem residues survive.

Phase 3's archive does survive. `worktrees/.archive/` holds 19 entries -- 17
`MANIFEST.txt` provenance files and 18 rescued working-tree files -- written
2026-08-20 and 2026-08-21, gitignored, untouched since. Per the manifests the
rescued content is almost entirely `Cargo.lock` copies, which are derived state
and drop on sight; the one substantive entry is
`consus-primary-codex-consus-parse-limits-035-ebc4979`, six files including the
three board files, from a branch whose upstream was already `[gone]`.

Two residuals, neither of them the lane count: the archive is a non-worktree
directory in the canonical lane root, which holds linked worktrees only; and
`scripts/atlas-snapshot-worktrees.py`, the script this finding credits with
producing it, is not tracked on `main`.

re-open trigger: `worktrees/.archive` is non-empty.

## Finding 2026-09-21: rev-pin churn silts up the shared cache, and retention does not reach it

Measured while tracing a member target fork to its cause, then found in the
shared cache at the same rate. A `rev =` advance on a first-party git
dependency is a new source identity: cargo compiles a fresh generation of that
crate and its dependents, and never reclaims the previous one. Counting
fingerprint directories against distinct build units in `target/debug` gives
the multiplier directly -- themis 41 directories for **1** unit, mnemosyne 140
for 9, moirai 197 for 15, leto 29 for 2, hermes 58 for 5.
`target/release/.fingerprint` holds 10,546 build-unit directories.

`scripts/atlas-cache-retention.py` exists and names the general problem in its
own docstring -- "Cargo never garbage-collects it" -- but its eviction units
are containers (profiles, nested target directories) and the children of
`incremental` directories. Per-rev generations live in `deps/` and
`.fingerprint`, so the tool does not reach the dominant term. Nothing in
`.github/` invokes it either, so it runs only by hand.

This is the second, unmeasured cost of a `rev =` pin. The scan already counts
those pins as quarantine (lint floor); the cache sediment they leave is not
counted anywhere.

re-open trigger: fingerprint directories per distinct build unit above ~2x for
any first-party crate in the shared cache.

## Finding 2026-08-20: target_forks regrew, and the ratchet cannot see it

The residual this finding recorded as fixed -- "residual dropped to 0 ...
stack `target_forks` total 0" -- is back. Counted 2026-09-21 with the scan's
own predicate (`is_cargo_target_dir`: a `target*` directory carrying
`.rustc_info.json`, `CACHEDIR.TAG`, `debug` or `release`): five directories,
33.5 GB together. Dating each against the guard that was supposed to prevent
them splits the list in two.

`repos/.cargo/config.toml`, generated by `scripts/atlas-member-target-dir.py`,
landed 2026-09-09 23:00. It is installed and correct today: gitignored as
designed, carrying the absolute `target-dir`.

| directory | last written | contents | size |
|---|---|---|---|
| a gitignored non-member checkout | 2026-09-03 | `book/`, `debug/`, `doc/`, `release/`, `tmp/`, four rendered images | **30.9 GB** |
| helios | 2026-09-21 18:58 | `bench-replicated/`, `debug/xtask.*` | 1.1 GB |
| eunomia | 2026-09-21 09:50 | `debug/{deps,examples,incremental}` | 596 MB |
| CFDrs | 2026-09-21 17:16 | `debug/`, `doc/` | 579 MB |
| aequitas | 2026-09-21 14:37 | `book/`, `ci-python-dist/`, `ci-python-env/`, `ci-wheel-target/{debug,maturin}` | 355 MB |

The 30.9 GB is 24.6 GB of `debug/` and 5.6 GB of `release/`; `doc/`, `book/`
and the renders are 13 MB between them, so the size is a build tree and
nothing else. Its shape says how it got there: `target/debug/.fingerprint`
holds 5,096 build-unit directories, among them **205 for mnemosyne across
only 9 distinct build units** and 181 for moirai across 12, against 4 for
themis across 1. That repository carries 35 `rev =` advances of mnemosyne. A
rev advance is a new source identity, so cargo compiles a fresh generation of
that dependency and everything downstream of it and never reclaims the
previous one; themis, never re-pinned, is the control that shows what an
unchurned dependency costs.

It predates the guard by six days and nothing has touched it since.
It is also the one row nobody should sweep: that checkout belongs to a
separate organisation, is gitignored by design, and carries unique unpushed
work on a branch whose remote is gone -- `ATLAS-PRIVACY-NAMING-1` governs how
it may be referred to at all. Inert history, not a leak.

The other four were each written on 2026-09-21 with the guard installed,
2.6 GB together, and all four were gone by 2026-09-22 09:16 -- removed by
someone unrecorded, since an untracked cache leaves no commit. The class reads
0 for registered members now. The risk stays open because nothing about the
mechanism changed: the same invocation recreates them. Two mechanisms, both structural rather than
a hole in the config. Cargo discovers configuration from the *current
directory* upward, so `repos/.cargo/config.toml` reaches only invocations
whose cwd is under `repos/`; a `cargo --manifest-path <member>` run from
outside the stack -- the documented way to build against a committed lock --
never sees it. Measured with `cargo metadata --no-deps` on eunomia, the
variable unset: cwd `/d/atlas` and `/d/atlas/repos` both resolve
`target_directory` to `D:/atlas/target`, cwd `/c/Users` resolves it to the
member's own `target`. The cause is not a mis-resolved relative path -- from
outside the stack no atlas config is discovered at all, so cargo falls back to
its default of `<workspace root>/target`, and the workspace root is the
member. And an explicit per-purpose
directory beats any config: `ci-wheel-target/` is maturin's, `bench-replicated/`
a benchmark runner's, and neither name appears in a tracked script here or in
the members' own.

One quieter variant: `repos/asclepius/.cargo/config.toml` sets
`target-dir = "D:/atlas/target/asclepius"`. That keeps `repos/asclepius/target`
empty, so the class does not count it, while still giving the member a private
cache inside the shared tree -- the dependency artifacts the one cache exists
to compile once are not shared with it.

The ratchet reports zero for the class regardless, and always will:
`target_forks` is in `HOST_OBSERVED_CLASSES`, so `scripts/atlas-conformance.py`
forces its baseline entry to 0 and reports it apart from regressions. That
zero is why this finding read as resolved for a month.

The junction alternative stays rejected for the reason recorded here
originally: `Path.exists()` follows an NTFS junction, so linking a moved cache
back re-activates the predicate and the fork re-counts. That constraint now
lives with the predicate it constrains, in `is_cargo_target_dir`'s docstring.

re-open trigger: any `repos/<member>/target*` satisfies `is_cargo_target_dir`.

## Finding 2026-08-20: Kwavers distributed queue remains externally gated

Kwavers PR #427 remains open at head `7245db7e44a7f461a34ff2d67e5b7f1a76bc69c1`
with `mergeStateStatus=DIRTY`; its current status rollup has no required
provider verification. The primary Kwavers checkout is detached at that head
with nine peer-owned source/ADR edits. Four linked lanes remain present under
`worktrees/kwavers-*`, including one whose remote branch is gone; the live
conformance scan reports three excess lanes. The Atlas Kwavers gitlink already
matches hosted-green default `9cf62aa98364e8f00cba0ca4a5d431b90a0ab55a`.
Rebasing, switching, removing lanes, or advancing the pointer would overwrite
or bypass peer work, so PR #427 remains a separate external integration
requirement.

## Finding 2026-08-19: Apollo PR #107 benchmark remains red

Apollo PR #107 remains open at source head `d408c738`. Its hosted benchmark
run `32217561595` fails 17 counterbalanced cases, not only the two
`mixed_precision_f16_auto` cases recorded by the earlier audit. The failures
include sizes 64 and 96, Rader `f32/31` and `f64/53`, and multiple composite
prime cases; the comparison reports the candidate slower in all four ordering
comparisons for each failure. The Rust job is cancelled and the Python job
passes. This is an empirical performance residual, so no merge, tolerance
change, workload reduction, or benchmark-instrument change is authorized by
the audit. The Apollo checkout retains peer-owned `Cargo.lock` and
`backlog.md` dirt; the next action is root-cause profiling on the active PR
branch.

## Finding 2026-08-19: clean-checkout exact-head gate remains peer-held

## Finding 2026-08-19: Mnemosyne default moved after the first Miri failure

## Finding 2026-08-18: RITK Apollo forward-sweep residual

## ATLAS-CFDRS-TEST-BUDGET — exact provider-head runtime residual (reopened 2026-08-17)

The final CFDrs PM head is `174e332ce816dd6dfe98b125669a292126ebd51f`.
Hosted run `32037758079` reaches the numerical-fidelity suite but fails the
unchanged 30-second nextest budget in
`cfd-validation::numerical::venturi_cross_fidelity::tests::microventuri_35um_case_produces_converged_informative_2d_result`
and
`cfd-validation::cross_fidelity_trifurcation::cross_fidelity_trifurcation_dominance`.
The book-figure job passes. The timeout is inherited from the production solver
path, not from the orphan cleanup or PM documentation, and no workload,
assertion, or budget reduction is acceptable. The next bounded increment is a
profile-first production optimization of the two paths; acceptance is the
unchanged tests completing within the committed budget with their existing
value-semantic assertions.

The first bounded production slice landed through CFDrs PR #347. Source head
`f7bc741184a000338a5f4d4edf261a6dcfa266c8` merges as
`84499e957d3d0c8ce50b9573185a1f55885f38e2`. It removes the
per-correction clone of the immutable cfd-2d pressure CSR matrix. The exact
35 µm and trifurcation cases pass locally in 16.785 s and 16.903 s under
locked Nextest, runs `5c15ba54-0b90-47a8-ab4c-f0eaf7b55d6c` and
`913a79da-d89d-4440-a12e-52c575483be6`. This is local value/runtime evidence,
not a cross-machine speedup claim. The same commit removes the silent
`unwrap_or(0.0)` hemolysis-model error path; existing negative-input and
reference-value tests cover the changed contract. Commit `c86dc33f` additionally
flattens the Leto-backed backward-facing-step stencil and hoists invariant
coefficients. The caller also pins Atlas shared workflow `bb505e5`, which
installs the fontconfig headers required by the Plotters `ttf` feature. The
provider PR gate is green with the unchanged workload and 30-second budget;
the broader solver-budget residual remains open and is not represented as
closed by this bounded slice.

## ATLAS-D3-PLACEMENT-034 — Block matching is in the wrong crate; D3 is blocked on relocating it (open)

Found starting US-023-D3, the consolidation of kwavers' NCC + parabolic
speckle-tracking kernel onto the ritk block-matching seam. This is my own
misplacement from US-023-D, and it repeats the mistake US-023-A5 corrected for
the coordinate map.

`block_matching` is **dependency-light**. Its three source files import nothing
beyond `anyhow`; the API takes `&[f32]` buffers plus `dims`, and never touches
`Image`, a tensor, or a backend. But it was placed in `ritk-registration`, whose
manifest pulls `ritk-core`, `ritk-image` (and through it the coeus
autograd/nn/wgpu stack), `ritk-filter`, `ritk-segmentation`, `ritk-model`,
`ritk-statistics`, `ritk-interpolation`, `ritk-transform` and
`ritk-wgpu-compat`.

The consumer makes the cost concrete. `kwavers-physics` declares
`ritk-registration = { workspace = true, optional = true }`, enabled only by its
`clinical-imaging` feature, while the kernel to be consolidated —
`.../elastography/thermal_strain/tracking.rs` — is **not** feature-gated. So D3
as filed has only bad options:

- force `clinical-imaging` on, making an optional dependency mandatory and pulling coeus into a physics crate for every build; or
- feature-gate core elastography tracking behind it, which hides a core capability behind a build flag and makes it an untested path.

Neither is acceptable, so D3 does not proceed as filed.

**Corrective step (US-023-D4).** Move `block_matching` out of
`ritk-registration` into a dependency-light home, exactly as A5 moved the
coordinate map into `ritk-spatial`. `ritk-spatial` is *not* the right
destination this time: it holds spatial vocabulary (`Point`, `Spacing`,
`Direction`, `CoordinateMap`), and block matching is an algorithm over sampled
data, so putting it there would be a junk-drawer placement. The
architecture_scoping promotion trigger "module → crate: another crate needs to
consume it" has fired, so a small dedicated crate is the warranted destination,
with `ritk-registration` re-exporting it so its own consumers are unaffected.

Once that lands, D3 is the mechanical consolidation it was meant to be: kwavers
takes the light dependency, `tracking.rs` delegates, and the duplicate NCC and
parabolic-peak implementations are deleted.

## Finding 2026-08-19: integrator exact-head coverage was missing from the audit

## ATLAS-RITK-CI-DIAG-035 — RITK-CI-1 diagnosis: the in-plane basis path, not the direction fix itself (open)

Investigated the standing SimpleITK parity failure recorded in
ATLAS-RITK-CI-RED-033. Not fixed here — it is another author's deliberate,
documented change — but narrowed to a specific code path so the owner does not
have to repeat the search.

**Origin.** `3aa73ba0` *fix(ritk-filter)!: Apply the direction matrix in
index<->physical transforms* (2026-08-18 14:01, on `main`, 1107 insertions,
carrying its own ADR 0020). The first observed parity failure is later the same
day, and the file's previous commits are older, so this is the change in scope.

**Why the fix's own evidence did not catch it.** ADR 0020 states "the
axis-aligned tests were confirmed to pass". The three failing parity tests use
**identity** direction, origin `[0,0,0]` and spacing `[1,1,1]` — the
axis-aligned case — so they contradict that claim. The likely reason they were
not seen is that they are Python tests in `crates/ritk-python/tests/`, which run
only in the `Python Wheel (smoke test)` job, separate from the Rust suites.

**Where the divergence most likely is.** The error magnitudes are strongly
asymmetric:

| Test | Max deviation | Gate |
| --- | --- | --- |
| `test_cmake_inverse_displacement_field_2d` | 2.2323646545410156 | 1e-4 |
| `test_cmake_inverse_displacement_field_3d` | 0.08209633827209473 | 1e-4 |
| `test_cmake_iterative_inverse_displacement_field` | 0.17078542709350586 | 1e-4 |

## ATLAS-PEER-WIP-030 — Uncommitted peer refactors stalled verification five times (open 2026-08-13)

Recorded as process debt, not as a defect in any one change. In a single
session, downstream verification was blocked five separate times by
*uncommitted* work in the local trees the development overlay resolves to:

- `repos/mnemosyne` — four occurrences. `crates/mnemosyne-local` left uncompilable mid-refactor (`is_allocating` field removal, a `record_defrag_operation` arity change, `with_allocator_unguarded` bindings). Blocks everything downstream of coeus, which is most of ritk.
- `repos/apollo` — one occurrence. `crates/apollo-fft/src/api/irfft.rs` changed `ifft_3d_array_into` to take three arguments while the committed `kwavers-math/src/fft/mod.rs` still calls the two-argument form. Blocks all of kwavers.

In each case the consuming crate was clean and correct; the break came from a
neighbour's working tree. Because the overlay points every first-party
dependency at these trees rather than at a git revision, an in-flight refactor
in one repo makes its consumers uncompilable stack-wide, and there is no
committed revision to fall back to locally — the hosted CI, which resolves from
git, stayed unaffected throughout.

This is inherent to the overlay's purpose (synchronized editing) and is not
worth removing. What is worth having is a way to keep working: the practical
mitigations are (a) landing refactors of a widely-consumed API as one
compiling commit rather than leaving the tree broken between edits, and (b)
treating hosted CI as authoritative when a local block is an overlay artifact,
which is what this session did.

No item filed against any peer. Recorded so the pattern is visible if it
persists, since each occurrence costs a downstream agent a full gate cycle.

## ATLAS-US-A3-OVERLAY-029 — A3 is blocked by the shared ritk tree's branch (open 2026-08-13)

US-023-A5 and A7 are merged to ritk `main` (PRs #132, #133), so the geometry
seam kwavers needs now exists. A3 still cannot be implemented, for a structural
reason rather than a design one.

The Atlas development overlay patches every first-party ritk crate — including
`ritk-spatial` — to the canonical tree at `repos/ritk`:

```toml
```

otherwise ready: the design question it was blocked on (A7) is settled and

## ATLAS-US-A3-FAN-028 — ritk's curvilinear fan cannot express kwavers' asymmetric fan (open 2026-08-13)

Found starting US-023-A3, by reading both inverse maps rather than assuming
they agree. They agree on everything except the beam index.

kwavers (`b_mode/scan_conversion.rs::convert`):

```text
```

```text
```

## ATLAS-KW-FWI-STRANDED-027 — FWI-024-A is delivered but not on kwavers main (open 2026-08-13)

The kwavers shared tree moved to `codex/kwavers-floatelement-roots`, so the
frequency-domain FWI files there no longer show the curvature-scaled step
(`model_minimizer_step` absent, `hessian_vector` back in `gauss_newton.rs`).
That reads as a revert and is not one: commit `912fe1983` is intact on
`origin/cascade/provider-042` — both halves verified present on that branch tip
— and a peer's `git switch` moves the shared tree's branch for everyone.

The issue is delivery, not loss. `cascade/provider-042` is unmerged, has
advanced under other work since, and FWI-024-A reaches kwavers `main` only when
that branch merges. Not merged here: it is a peer's branch carrying their work
alongside one commit of mine, and carrying my commit is not sufficient reason to
integrate theirs. Recorded as integration debt, with that branch's merge as the
re-open trigger.

Two process notes from the same session. The recorded shared-tree branch-switch
memory held — the surprise was diagnosed from it rather than mistaken for peer
data loss. And verification for coeus-dependent crates was blocked twice by one
peer's uncommitted mnemosyne refactor, which stalls every gate downstream of
coeus in the stack; worth raising with that owner if it recurs.

## ATLAS-US-A3-BLOCKER-026 — Scan-conversion migration is an [arch] change, not a [minor] one (open 2026-08-13)

Recorded while starting US-023-A3. Three findings, the first two decisive.

**The seam works as ADR 0042 promised.** `ritk-filter`'s
`sample_moving_at_world` (`crates/ritk-filter/src/resample/native.rs:51`)
already calls `moving.world_to_index_native(&world)`. Since that now dispatches
on `CoordinateMap`, resampling a beam-space image onto Cartesian world points
*is* scan conversion, with no change to the resampler. That half of the ADR is
confirmed in the existing code, not just in principle.

**But kwavers cannot reach it from where the converter lives.**
`kwavers-analysis` has no ritk dependency at all — the `ritk-*` edges exist only
in the top-level `kwavers` crate, behind the documented
`domain::imaging::medical::ritk_bridge` boundary. Worse, `ritk-image` pulls
`coeus-core`, `coeus-tensor`, `coeus-ops`, `coeus-autograd`, `coeus-nn`,
`coeus-optim` and `ritk-wgpu-compat`; `kwavers-analysis` resolves **zero** coeus
today. Adding it would drag an autograd/neural-network/wgpu stack into a
signal-processing crate to obtain polar geometry — the domain-to-infrastructure
coupling the standards prohibit. US-023-A3's "migrate and delete the converter"
was filed assuming a mechanical migration; that premise is false.

**Corrected plan.** `CoordinateMap`, `CurvilinearArray` and `PhasedArray3D` are
pure `f64` geometry — `coordinate_map.rs` imports nothing but `anyhow` and never
touches a tensor. Their canonical home is `ritk-spatial`, which already owns
`Point`/`Spacing`/`Direction`/rotation and depends only on `leto`, `serde` and
`thiserror` — and `kwavers-analysis` already depends on `leto`. Moving them
there (with `ritk-image` re-exporting and continuing to use them) puts the
geometry at the deepest common ancestor of its consumers per
architecture_scoping, and makes the kwavers side a cheap `ritk-spatial`
dependency instead of an impossible one. That move is US-023-A5 and gates A3.

Once it lands, A3 splits honestly: kwavers' `ScanConverter` delegates its polar
math to the one SSOT while keeping its Leto storage and Aequitas typed geometry
(a differential test against current output is the oracle), and the fuller
"delete the converter, resample through ritk" version stays a separate [arch]
question about whether B-mode moves behind the ritk bridge — which would split
the B-mode pipeline across crates and should not be decided incidentally.

### US-023-A5 — `ritk-spatial` move is implemented, merge-gated

```rust
```

## ATLAS-USCT-FWI-024 — kwavers audit vs FullWaveformInversionUSCT (open 2026-08-13)

Reference: `rehmanali1994/FullWaveformInversionUSCT` at `master` — a compact
single-method implementation (117-line `Functions.py`, 163-line
`BreastTomography.py`, MATLAB twin). Method read in full, not summarized from
its README. Citation: Ali, R., "Open-Source Full-Waveform Ultrasound Computed
Tomography Based on the Angular Spectrum Method Using Linear Arrays", SPIE
Medical Imaging 2022, Vol. 12038.

Reference method: frequency-domain transmission-USCT FWI. Two opposed linear
arrays rotate around the object (360° in 2° steps). Forward operator is the
**angular spectrum method with split-step (phase-screen) correction**, downward
continuation from Tx to Rx; the adjoint is upward continuation of the data
residual. Per view the slowness model is interpolated from a fixed
reconstruction grid onto a view-aligned simulation grid, and the resulting
gradient image is interpolated back. Optimizer is **NLCG with the Gilbert–Nocedal
hybrid** `β = min(max(β_PR, 0), β_FR)` and a **linearized exact line search**
`α = −⟨g,d⟩ / ⟨Jd, Jd⟩`, where `Jd` is obtained by one extra forward projection
of the search direction. A per-view per-frequency complex source scaling is
estimated by projection before the residual is formed. Frequency bins are
decimated 10:1; a lateral anti-aliasing window is applied.

Verdict: **kwavers is ahead of this reference on forward-model rigor and
optimizer machinery, and behind it on three specific points.** kwavers already
has, verified in source:

| Reference feature | kwavers |
|---|---|
| Frequency-domain FWI with adjoint gradient | `kwavers-solver/src/inverse/fwi/frequency_domain/{gradient,inversion,operator}.rs` |
| Forward operator seam | `HelmholtzForwardOperator` with single-scatter Born **and** convergent Born series (`frequency_domain/cbs/`) — strictly stronger than split-step ASM, which is a one-way non-reflecting approximation |
| NLCG with Polak–Ribière | `frequency_domain/inversion.rs:37` — `β_PR` with `max(β,0)` restart and a descent-direction safeguard |
| Per-view/frequency source scaling | `FrequencyDomainConfig::with_source_scaling`; tests `source_scaled_gradient_is_descent_direction`, `inversion_with_source_scaling_converges_for_consistent_model`; identifiability DOF accounting in `breast_ust_fwi/diagnostics/identifiability.rs` (`BreastUstSourceScalingPolicy::{Fixed, Estimated}`) — **exceeds** the reference, which scales inline with no identifiability accounting |
| Beyond the reference | truncated Newton-CG/Gauss-Newton with Levenberg–Marquardt damping (`gauss_newton.rs`), L-BFGS time-domain FWI, adjoint-state, frequency continuation, breast-UST phantom IO |

### Gaps

Residual risk: F1/F2 are small and independently verifiable against the

## ATLAS-US-CAPABILITY-023 — kwavers/ritk capability audit vs ITKUltrasound (open 2026-08-13)

Reference: `KitwareMedical/ITKUltrasound` at `master`, enumerated from its own
tree (63 public headers under `include/`, plus the 1D FFT filters it upstreamed
into ITK proper). Method: header enumeration via the GitHub tree API, then
per-capability verification by reading the corresponding kwavers/ritk sources —
keyword census alone was treated as a locator, not as evidence, per the
recorded name-collision pattern in `repos/kwavers/gap_audit.md`.

Scope note. ITKUltrasound is an **image formation and analysis** module: it
starts from acquired RF and ends at displayed/quantified images. kwavers is a
**simulation** stack that also owns the RF back-end; ritk is the **image
processing/registration** stack. Several ITKUltrasound classes are therefore
correctly absent from kwavers (they are ritk-shaped) and vice versa. The
verdicts below record the *stack* gap, and name the owning repo.

### Present — no gap

| ITKUltrasound | Our implementation |
|---|---|
| `AnalyticSignalImageFilter` | `kwavers-signal/src/analytic.rs::hilbert_transform` (single SSOT, Apollo-backed) |
| `BModeImageFilter` | `kwavers-analysis/.../b_mode/detection.rs::{envelope, log_compress}` |
| `TimeGainCompensationImageFilter` | `kwavers-analysis/.../b_mode/tgc.rs::TgcConfig` |
| `BoxSigmaSqrtNMinusOneImageFilter` | `ritk-filter/src/smoothing/box_sigma.rs` (+ `local_noise.rs`) |
| `LinearLeastSquaresGradientImageFilter` | `kwavers-physics/.../elastography/thermal_strain/strain.rs::least_squares_strain` (axial/1D) |
| `BlockMatchingParabolicInterpolationDisplacementCalculator` | `.../thermal_strain/tracking.rs::parabolic_subsample` |
| `SpecialCoordinatesImageToVTKStructuredGridFilter` (VTK sink half) | `ritk-vtk/src/domain/vtk_data_object/structured_grid.rs` |
| clFFT/FFTW 1D FFT backends | Apollo/`kwavers-gpu` FFT providers (different provider, same role) |

### Partial

| ITKUltrasound | State | Missing part |
|---|---|---|
| `CurvilinearArraySpecialCoordinatesImage` | `kwavers-analysis/.../b_mode/scan_conversion.rs` converts sector **and** convex fans (typed `ScanGeometry.radius_offset`), 2-D, bilinear | It is a standalone resampling function, not a coordinate-system-carrying image type; 2-D only; no inverse (Cartesian→polar) direction |
| `FrequencyDomain1DImageFilter` + `ButterworthBandpass1DFilterFunction` | `kwavers-analysis/.../filtering::FrequencyFilter` does FFT band/low/high-pass on 1-D lines; Butterworth exists as an IIR wall/clutter filter | No directional 1-D FFT filter over an N-D image, and no pluggable frequency-response function seam |
| `HDF5UltrasoundImageIO`, `UltrasoundImageFileReader` | kwavers reads HDF5 only for the breast-UST phantom; ritk's HDF5 is MINC-specific | No ultrasound HDF5 layout, and no special-coordinates-aware reader |
| BlockMatching displacement estimation | kwavers has NCC speckle tracking with parabolic sub-sample peak refinement (`thermal_strain/tracking.rs`, `elastography/displacement.rs`); ritk has an autodiff NCC **scalar** registration metric | See the block-matching gap below |

### Gaps

Residual risk: G1 and G4 are multi-item efforts; G2 is an `[arch]` decision

## Migration evidence inventory (residual surfaces scope-traced)

### CFDrs (`D:/atlas/repos/CFDrs`) — residual nalgebra surface

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
  - **Batch #1 source-side migration — slice 1 partial-closure-mark 2026-07-08**: per the peer's `5cd8c708` chore (`refactor(kwavers-solver): Migrate struct_impl.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 1)`, on `codex/kwavers-core-moirai-parallel` atop parent `ccc6bbf9`): **2/41 sites migrated in 1/15 files**. The 2 sites live in `crates/kwavers-solver/src/multiphysics/fluid_structure/solver/struct_impl.rs` (3D `Array3<f64>` element-wise relaxation on `p_fluid_ghost` + `p_fluid_ghost_prev`; plus a 1D sub-view relaxation on `t_solid_ghost` + `t_solid_ghost_prev`). The migration uses the idiomatic `moirai_parallel::ParallelSliceMut::par_mut().enumerate(closure)` trait form (auto-Adaptive policy; no `ExecutionPolicy` generic needed), preserves indentation via captured leading-whitespace group, and adds the trait import `use moirai_parallel::ParallelSliceMut;` ahead of the `ndarray` use-statement. Cargo-check pre-validate: `cargo check -p kwavers-solver --lib --no-default-features` clean at inner HEAD `5cd8c708`. The full-closure mark (`✅ Batch #1 CLOSED 2026-07-08`) remains retracted; this entry is a **partial-closure mark**, not a full reassertion. **39/41 sites / 14/15 files remain** for future slices per ADR 0009 Batch #1 CTE shape (`docs/adr/0009-kwavers-batch1-rayon-to-moirai-cte.md`). **Atlas-meta path forward**: kwavers pointer advance remains deferred per the KW-CV-001 watchpoint; the next slice(s) will be tracked via per-slice partial-closure marks until the source-side count actually drops to zero, at which point the full closure-mark can be reasserted.

- **Residual `burn`** (T1 re-verified 2026-07-07 against the dirty inner `repos/kwavers` working tree after the neutral-name Burn cleanup continuation):

  - Requested migration scope is clean: `rg -n "Burn|burn_|\bburn\b|burn-|CoeusPINN|coeus_wave" crates/kwavers-solver/src/inverse/pinn crates/kwavers/tests crates/kwavers/benches crates/kwavers/examples crates/kwavers/Cargo.toml Cargo.toml` returns zero hits.

  - Kwavers manifests are clean: `rg -n "\bburn\b|burn-" -g Cargo.toml .` returns zero hits under `repos/kwavers`.

  - The `crates/kwavers-solver/src/burn.rs` facade is absent and `rg -n "burn_compat|crate::burn|kwavers_solver::burn|pub mod burn|mod burn"` finds no `burn_compat` alias path. The 1-D, 2-D, and 3-D PINN module paths are now framework-neutral (`wave_equation_1d`, `wave_equation_2d`, `wave_equation_3d`), and the beamforming adapter path is `pinn_adapter`.

  - Whole-repo literal residual is **356 lines across 21 files**, concentrated in `Cargo.lock` and historical PM/audit prose rather than the requested PINN/top-level source scope. Scoped PINN/top-level source plus `xtask/legacy_surface.allowlist` residual is **0 lines across 0 files** after regenerating the allowlist.

  - `cargo tree -p kwavers-solver --features pinn -i burn` remains non-empty through RITK provider crates (`ritk-image`, `ritk-interpolation`, `ritk-spatial`, `ritk-wgpu-compat`, and downstream `ritk-*` paths), so full Burn graph closure is still blocked outside the kwavers manifest/source surface.

  - Verification evidence: `rustup run nightly cargo fmt -p kwavers-solver -p kwavers --check` passed; `rustup run nightly cargo check -p kwavers-solver --features pinn` passed; `rustup run nightly cargo check -p kwavers --features pinn --tests --benches --examples` passed with pre-existing warning noise in `kwavers-math`, `pinn_elastic_validation`, and `phase6_persistent_adam_benchmarks`; `rustup run nightly cargo run -p xtask -- legacy-migration-audit` passes with allowlist status clean after `refresh-legacy-allowlist`; `rustup run nightly cargo nextest run -p kwavers --features pinn --test pinn_bc_validation --test pinn_ic_validation --status-level fail --no-fail-fast` compiled and ran 16 tests: 12 passed, 4 failed on legacy 3-D PINN loss thresholds (`test_ic_loss_zero_field`, `test_ic_combined_loss_decreases`, `test_bc_loss_decreases_with_training`, `test_dirichlet_bc_zero_boundary`). These are retained as validation residuals; assertions were not weakened.

- **Provider-boundary closure (2026-07-04)**: the 3-D beamforming WGPU

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

  disjoint-scope rule, atlas-meta has zero pending bookkeeping for these

### E0599 Closure-Front Peer-Side Fix Brief (kwavers `.view*()` surface)

- **Category A (bare `.view()`):** 138 sites (per `9deb4ab` baseline; current enumeration held flat)
- **Category B (`.view_mut()`):** 13 sites (NEW-visible post-`a5134d8`; previously not enumerated)
- **Category C (`.view_slice()` / `.view_axis()`):** 0 sites / 0 sites (empty surface)

- **Category A (138 bare `.view()`):** manual per-site rewrite (each site is heterogeneous; canonical `boundary.rs` refactor does not fit all bare calls). Per-site approach matches the E0369 idiom-set triage conclusion in `### Bulk-migration priority #2: repos/kwavers crate migration (E0369)` above.
- **Category B (13 `.view_mut()`):** single atomic `Boundary<_>` refactor at `boundary.rs` (or per-site if heterogeneous). The `.view_mut()` calls have a more uniform carrier pattern (all ndarray `Array3`/`Array4` writable views on the kwavers-data plane).
- **Category C (slice / axis):** no action.

### RN-CC-04 self-carry discipline: retroactive disclosure (post-536366e)

## Shared incremental-cache growth — open

The shared `target/debug/incremental` tree accumulated 27,085 session
directories and 525,183,672,320 bytes in five days across the multi-repository
stack. An idle-tree prune reclaimed those bytes but does not prevent recurrence.
The corrective plan preserves local incremental edit builds, disables
incremental compilation on clean CI runners, and consolidates the approximately
950 leaf binary targets tracked by `ATLAS-BUILD-STRUCTURE-001`. Re-open on the
next clean Kwavers architecture run to compare artifact bytes and peak memory;
do not claim the preferred 10 GiB clean-build budget until that runner records
it. Local shared-cache size is a separate multi-repository retention metric.

## Finding 2026-08-18: Provider PR hosted closure remains open

The refreshed hosted audit leaves three active provider-consumer closures
unmergeable; no Atlas gitlink was advanced from these results.

- [Apollo PR #104](https://github.com/ryancinsight/apollo/pull/104) is open at exact head `38192bed48032c3cce0222f95551f1ef3b1328b6` and reports `UNSTABLE`. Rust workspace run [`32096086258`](https://github.com/ryancinsight/apollo/actions/runs/32096086258) fails before compilation because `--locked` attempts to update the lockfile; benchmark run [`32096086273`](https://github.com/ryancinsight/apollo/actions/runs/32096086273) fails resolving fixed benchmark executables because `apollo-fft ^0.26.0` has only a `0.27.0` candidate in the graph. Python bindings and CodeRabbit pass. Dependent [Apollo PR #106](https://github.com/ryancinsight/apollo/pull/106) at commit `7d56dc2b` updates the PR-head lock entry to `0.27.0` and makes the benchmark instrument copy every candidate manifest that directly requires `apollo-fft`, including the previously failing transform consumers. Its local evidence is `cargo check --locked --workspace --all-targets`, 494/494 focused `nextest` tests, clean formatting, and passing workspace doctests; hosted acceptance remains pending on #106 and the subsequent #104 rerun. At the current live provider state, PR #106 is mergeable with Rust and benchmark checks in progress, Python bindings green, CodeRabbit green, and the external RecurseML status `ERROR`. The full Atlas coherence audit also reports exactly three consumer-lag findings: Coeus `coeus-autograd`, Coeus `coeus-fft`, and RITK `ritk-filter` still require `apollo-fft` `0.26.0` while the live Apollo provider is `0.27.0`. The provider default/version/API sweep and lockfile regeneration must land before those consumer requirements move.
- [Kwavers PR #402](https://github.com/ryancinsight/kwavers/pull/402) remains open at exact head `69478221f0f8d601614323b0e12f175971e7fdba` and reports `UNSTABLE`. Benchmark smoke and regression pass in run `32099808182`, but the exact matrix run `32099808162` has terminal failures across architecture, validation, security, coverage, documentation, feature, CUDA, and wheel jobs, with additional cancelled jobs. The consumer gitlink stays at its committed Atlas pin until a complete hosted matrix is green.
- [Helios PR #64](https://github.com/ryancinsight/helios/pull/64) remains draft at exact head `9a590ffaa65b3afc61b36f0aec2239014b6d17ae` and reports `UNSTABLE`. Rust and Python pass in run [`32102725325`](https://github.com/ryancinsight/helios/actions/runs/32102725325), the book build passes while deployment is skipped, benchmark regression is still in progress, and the external RecurseML analyzer reports `ERROR`. Atlas retains the existing Helios gitlink until the hosted acceptance gate is terminal and green.

## Finding 2026-08-18: Apollo large-codelet expansion failed benchmark gate

## Finding 2026-08-19: CFDrs OPEN-033 JFNK source integration

CFDrs PR #358 (`0a5076c6034d735dd23d63a91453fea7d63702d0`) declares the
retained `newton_fallback.rs` module, invokes one finite-budget recovery after
bounded-amplitude stagnation, and moves the residual callback through a typed
`JfnkSolver::solve_checked` seam. Hosted run `32226574871` at CFDrs
`6f60dd4d` passed formatting and figure SSOT but failed the locked workspace
check with E0525: the retained fallback's workspace-reusing residual closure is
`FnMut`, while `JfnkSolver::solve_checked` required `Fn`. Provider commit
`bc18b095` changes the JFNK operator and GMRES seams to reborrow a mutable
callback and adds a value-semantic initial-root regression. Replacement run
`32226998372` is pending; Atlas remains at `931ee3a0` until its hosted gates

## Finding 2026-08-20: exact-head clean-checkout residual recheck

## Finding 2026-08-20: shared book-workflow pin drift inventory

## Finding 2026-09-03: new oversized crossings at the fc4b6c463 pointer advance

- **CFDrs `oversized_files` 140 → 141.** Exactly one new crossing since `8f088bce`: `crates/cfd-schematics/src/geometry/generator/generator_impl.rs` (502 lines, 2 over target). Also grown but already counted: `geometry/generator/selective/mod.rs` 570 → 631. Owner lane: `perf/cfd-schematics-serpentine-shape-scan`.
- **mnemosyne `oversized_files` 6 → 7–8 plus `manifest_implementation` 8 → 9.** New ~500-line arena files (`scratch/aligned_vec`, `segment/alloc`, `backends/unix`, plus manifest bodies in the new `scratch`, `segment/alloc`, `segment/pool`, `cuda` and `page` manifests) arriving with the owner's Phase 10–14 AlignedVec/scratch-bank work — the exact file set churns per advance, so consult the instrument, not this entry, for the current list. Owner lanes active nightly; the user is landing this wave personally (`#127` and follow-ups).

## Finding 2026-09-04: apollo main red — triple-versioned mnemosyne in one graph

`apollo/ci` run `33871853343` (`59f202c6`, merge #320) fails `rust workspace`
(plus cascading `python bindings` and 4 `rustdoc` shards, all downstream of
the same broken build) with `E0277: eunomia::Complex<f64>:
mnemosyne::scratch::ScratchElement is not satisfied` at
`apollo-fft/.../radix_composite/cache.rs:118` (`TL_COMPOSITE_SCRATCH_64`)
and `winograd/traits.rs:33`. The compiler note is explicit: **three
different `mnemosyne_arena` revisions coexist** —
`af7a23a` (expected trait), `da5c6be`, `7f1737513c` (found trait).

Requirement map from `59f202c6:Cargo.lock` (all `mnemosyne-memory 0.7.0`):

- `af7a23a` — apollo workspace pin (`Cargo.toml:67`, temporary co-evolution pin for Mnemosyne PR #128). This rev HAS the `ScratchElement for Complex` impls (`element.rs:59/66`), gated on `all(feature = "eunomia", not(feature = "bytemuck"))`.
- `da5c6be` — required by `hermes-simd-core` and `leto` (their manifests still pin the older rev).
- `7f1737513c` — required by `moirai-core/-executor/-runtime/-scheduler`.
- eunomia is likewise dual-versioned: branch pin `02397fa4` alongside the workspace `rev = "fdbf122"`.

No manifest in apollo declares `da5c6be` — it arrives transitively, so the
fix is a forward sweep, not a local edit: advance the hermes/leto/moirai
mnemosyne pins to the workspace rev, unify the eunomia pins, regenerate
apollo's lock (which prunes the stale copies). Reverting #320 instead
would need explicit user instruction (fix-forward rule) and would only
hide the drift until the next Complex-scratch use. This is the
requirement-lag sweep defect class: a `rev =` quarantine that outlived
its removal trigger now fractures trait identity graph-wide.

Re-open trigger: apollo `ci` green on main. All four consumers hot
(apollo `perf/apollo-rader-width-probe` + `apollo-f16` lanes, hermes
dirty tree, leto PRs #159/#164, moirai PR #256) — recorded for the
owners, not fixed from the umbrella.

**Resolved 2026-09-04:** apollo `ci` green on main at `8ce18e57`
(success 19:21 UTC) via the Eunomia source unification (#324: the
workspace `rev = "fdbf122"` eunomia pin is gone, back to branch pin)
plus follow-up perf landings. The E0277 fracture is closed.
**Residual watchpoint (not a finding):** apollo still carries the
temporary co-evolution pin `mnemosyne rev = "af7a23a"` whose own
comment orders its removal after Mnemosyne PR #128 — if that PR has
merged and the pin remains, the quarantine has outlived its trigger
and the sweep should re-fire. Verify against mnemosyne's merge log,
not this entry.

## Finding 2026-09-04: conformance gate down on in-flight architecture check

## Finding 2026-09-04: ares release dispatch failed on package allowlist

## Finding 2026-09-05: committed stack overlay missing moirai sections

## Finding 2026-09-24: member pre-push reads the secret scanner from the live stack tree

`scripts/git-hooks/pre-push` runs `$repo_root/../../scripts/atlas-secret-scan.py`, the file checked out in the shared stack tree, while its debt ratchet extracts the checker from the stack's fetched default. With the tree on a branch older than the scanner, member pushes skip the scan: CFDrs#459, kwavers#850 and Moirai#471 all did on 2026-09-24. Re-open trigger: the hook extracts the scanner from `$stack_baseline`, as it does the checker.
