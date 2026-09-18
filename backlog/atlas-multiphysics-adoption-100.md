<a id="atlas-multiphysics-adoption-100"></a>
## ATLAS-MULTIPHYSICS-ADOPTION-100 — CFDrs/Kwavers/Helios provider adoption and suite closure [major] [arch] — in-progress

- **Completed claim (atlas coordinator, 2026-08-21):** exact committed-gitlink
  source mode for `scripts/atlas-multiphysics-audit.py` and its tests is
  implemented and verified. The claimed files were that script, its focused
  test, and this item. Peer-owned source, consumer, and lane checkouts remain
  out of scope.
- **RITK release-workflow closeout (fresh recheck):** PR [#194](https://github.com/ryancinsight/ritk/pull/194)
  merged at `337f0dc5` with merge commit `65bee2c2`. The fetched RITK default
  is `b35c93313c06ea55fffa680a430378dda1df8e41`, exactly matching the Atlas
  gitlink. The hosted connector returned no workflow records for the merge
  SHA, so this closes the merged workflow-only claim but does not assert
  post-merge CI, Pages, or live-release evidence.
- **RITK claim closeout:** `RITK-DOC-GATE-210` is fixed in provider commit
  `9e1c276a`, which adds a warning-denied rustdoc CI job and corrects five
  public-doc/private-link or broken-link defects. Exact workspace rustdoc
  generates 40 targets, focused nextest passes `817/817`, and focused clippy
  passes with `-D warnings`; this increment advances the Atlas `repos/ritk`
  pointer to `9e1c276a`.
- **Horae claim closeout:** clean default `0df563a69693418b267f337fa4bc9dfb7c1aeb1b`
  passes the exact `--all-features` native gate `23/23`. Horae CI already runs
  `mdbook test`, and its Pages workflow enables the shared `mdbook-test` gate.
  The local Windows `mdbook test` invocation stops before chapter assertions
  with `E0461` because mdBook selects GNU rustdoc while the shared stack
  artifacts are MSVC; no Horae source or pointer change is warranted, and the
  hosted Linux book gate remains the configured cross-platform book evidence.
- **Kwavers pointer reconciliation:** the fetched provider default is
  `64b982bdbfc2b7e36f11971947f5bdd8ed59d1f1`, while Atlas still points at
  `b571927442b074fb0622beabdf3f2535dff1951a`. This increment advances only
  the root gitlink to the fetched default; the peer-owned Kwavers checkout is
  dirty on `ff4dc868` and remains untouched.
- **Integration recheck closeout:** root `a1fd1e4` passes the exact-head audit
  for all 22 providers and CFDrs/Kwavers/Helios, the stack overlay check, the
  registry metadata scan (`252` manifests, `0` violations), and the standalone
  lock-form check (`27` locks, one documented in-tree Melinoe fixture
  exemption). The lane audit remains red only for Consus (`3` worktrees) and
  Kwavers (`5` worktrees); no lane was switched, deleted, or overwritten.
- **Live conformance evidence:** the intentional `--worktree` scan remains a
  dirty-tree snapshot, not a reproducible gate. It reports `609` oversized
  files, `675` implementation-bearing manifests, `1,196` production unwraps,
  `518` allow sites, `803` existence-only assertions, and `4` excess-worktree
  sites; these counts are peer-owned ratchet debt and are not silently reset
  by the Atlas coordinator.
- **Checkout ownership boundary:** Gaia's apparently clean checkout is in an
  interactive rebase on `cascade/provider-042`; switching it to the recorded
  root gitlink was refused and no rebase state was touched.
- **Hosted residual recheck (2026-08-20):** [CFDrs PR #357](https://github.com/ryancinsight/CFDrs/pull/357)
  has passing Rust and figure jobs in run `32225060679`; only its RecurseML
  analyzer reports an error. [Apollo PR #107](https://github.com/ryancinsight/apollo/pull/107)
  remains red: benchmark run `32217561595` and Rust run `32217561627` fail;
  the independent benchmark audit localizes the regression to the four
  const twiddle-cache initializers in `twiddle.rs:26-29`, with the required
  repair being a single-variable revert in
  `crates/apollo-fft/src/application/execution/kernel/mixed_radix/caches/twiddle.rs:26-29`
  with the benchmark instrument unchanged.
- **Hosted completion boundaries:** [Helios PR #67](https://github.com/ryancinsight/helios/pull/67)
  is draft but its Rust, Python, benchmark, and book-build jobs pass in runs
  `32284640806` and `32284641544`; Pages deployment is skipped. [RITK PR #190](https://github.com/ryancinsight/ritk/pull/190)
  is draft with Rust, Python, wheel, and book-build gates passing in runs
  `32297172555` and `32297173130`; Pages deployment is skipped. Hermes PR #55
  has green substantive gates in `32255618310` but remains draft; RecurseML
  errors remain analyzer-only. Kwavers PR #417 has a fully green substantive
  matrix in runs `32316400677`, `32316400868`, `32316401011`, and
  `32316401183`, with Pages deployment skipped; PRs #420, #421, and #422 have
  pending matrices and are not completion evidence.
- **RITK release-workflow slice:** provider commit `337f0dc5` on branch
  `ci/ritk-release-timeout` adds `timeout-minutes: 30` to the wheel-build job
  and `timeout-minutes: 10` to the trusted PyPI publish job. PR #194 is draft;
  YAML parsing and the local conformance scan pass (`workflow_missing_timeout`
  `1 -> 0`), while its Rust, Rustdoc, Python, wheel, and dependency-alignment
  checks are pending. RecurseML reports an analyzer error only. Atlas remains
  at RITK `9e1c276a` until the provider default advances; no hosted success is
  inferred from pending checks.
- **Kwavers PR #418 closeout:** the ADR and convex-array rasterizer seam merged
  at provider default `64b982bdbfc2b7e36f11971947f5bdd8ed59d1f1`. The fresh
  default contains ADR 112, its index row, and the Aequitas `Degree` surface;
  no stale architecture record remains in the provider default. Atlas advances
  its gitlink in this integration increment while the primary checkout remains
  dirty on peer branch `feat/aperture-sir-seam` and is not switched.
- **Kwavers PR #417 closeout:** the typed `Degree` adoption merged at provider
  default `b571927442b074fb0622beabdf3f2535dff1951a`. Its Rust, Python-wheel,
  benchmark, feature, Miri, security, documentation, k-Wave, and architecture
  checks passed; Pages deployment was skipped and RecurseML remained
  report-only. The Atlas pointer advances to this merge commit in the
  integration increment below; the primary Kwavers checkout remains dirty on
  peer branch `feat/aperture-sir-seam` and is not switched.
- **Kwavers post-merge integration closeout:** Atlas root `a00a0d1` advances
  the Kwavers pointer to `b5719274`; exact provider/integrator heads, the stack
  overlay, registry metadata, and 27 standalone lock forms pass. The lane
  audit remains limited to Consus (3 trees) and Kwavers (5 trees), with all
  peer-owned lanes preserved.
- **CFDrs PR #357 closeout:** the hosted-closure documentation increment merged
  at provider default `aa54f5cdcdc4e406df0c60ea6c3cb507e968fc97`. The Rust and
  figure jobs passed at the documented exact source head; Pages and PyPI remain
  explicitly open. The Atlas pointer advances to this merge commit in the
  integration increment below; the primary CFDrs checkout remains dirty on
  peer branch `codex/cfdrs-tvd-test-integration` and is not switched.
- **CFDrs post-merge integration closeout:** Atlas root `c721c3e` advances the
  CFDrs pointer to `aa54f5cd`; exact provider/integrator heads, the stack
  overlay, registry metadata, and 27 standalone lock forms pass. The open
  Pages/PyPI items remain provider-owned delivery work and are not inferred
  from this documentation merge.
- **Aequitas claim closeout:** dimensional-law tests were split into named
  angle and complex-value modules in provider commit `c908af1`; the focused
  nextest gate passes `40/40`, clippy passes with `-D warnings`, and Atlas
  records the pointer in commit `84eb033`.
- **RITK claim reconciliation:** `ATLAS-RITK-TRANSFORM-DIRECTION-081` was
  already fixed in provider commit `3aa73ba0`, an ancestor of RITK default
  `ebf2f499`. The focused `ritk-filter`/`ritk-diffusion` gate passes
  `1,284/1,284` tests (11 skipped) and clippy with `-D warnings`; oblique grid,
  inverse-displacement, and marching-cubes regressions are present.
  `FodVolume` intentionally documents an axis-aligned frame contract, so no
  RITK source change was warranted.

The active product boundary is a multiphysics simulation suite built from the
CFDrs, Kwavers, and Helios integrators. The provider set is `horae`,
`hyperion`, `harmonia`, `themis`, `tyche`, `proteus`, `mnemosyne`, `consus`,
`helios`, `aequitas`, `asclepius`, `eunomia`, `moirai`, `ritk`, `melinoe`,
`leto`, `hephaestus`, `coeus`, `apollo`, `gaia`, `hermes`, and `iris`.
`tyche` is the canonical spelling; `tychee` is retained only as a historical
alias in audit text. Atlas owns the provider graph, exact gitlinks, overlay,
cross-repository gates, and integration documentation; each member owns its
source implementation and provider-local tests.

- **Current slice:** Helios PR #59 carries the caller-side `mdbook test`
  enablement, CFDrs PR #347 carries the pressure-cache, hemolysis-error, and
  book-fence slices,
  and Apollo merged default `ed6d6905` carries the provider-owned public
  `PlanScratch` bound required by CFDrs. Helios PR #59 is merged at default
  `679402ae` with Rust, Python, benchmark, and book gates passing; CFDrs PR #347
  merged provider source head `f7bc741184a000338a5f4d4edf261a6dcfa266c8` into
  default as `84499e957d3d0c8ce50b9573185a1f55885f38e2`. Exact-head Rust run
  `32046526277` passes format, check, ordinary tests, numerical fidelity (14/14,
  3036 skipped, 8 slow; 247.309 s), and doctests; figure job `95435610232` and
  book build `95435671291` pass. Post-merge Pages run `32047447199` passes build
  and deployment. Post-merge Rust run `32047446607` passes format, check, and
  ordinary tests but fails numerical fidelity with 12/14 passed and timeouts in
  `microventuri_35um_case_produces_converged_informative_2d_result` and
  `cross_fidelity_trifurcation_dominance` at 30.006 s. The preceding Rust run failed before checkout on a
  GitHub 503/429 action-download response (`32043533301`, job `95426903063`).
  The preceding Pages run (`32043533628`, job `95426905897`) reached the
  package build and exposed the missing `fontconfig.pc` system dependency.
  Atlas shared workflow `bb505e5` now installs the required headers and the
  CFDrs caller pins that commit. New exact-head CI and Pages runs
  `32044071453` and `32044071732` were infrastructure-red. PM-only and
  source-correctness heads were superseded by `f7bc7411`; Rust job
  `95430179027` and Pages job `95430210781` in runs `32044765872` and
  `32044766414` failed before checkout on codeload 503/429. The figure job
  `95430179037` passed; the Pages retry `95430855675` passed the prior exact
  head. CodeRabbit and all required PR checks are successful; the PR is merged.
  The Atlas gitlink sweep below is complete for moving Mnemosyne,
  Aequitas, Leto, and CFDrs defaults;
  while Helios is already at merged default `679402ae`. Kwavers PR #402 carries
  the current provider FDTD and uninitialized-GPU-resource correction at exact
  source head `e1648019`; its hosted matrix is pending. PR #386 remains historical
  evidence for the earlier multi-field field-preservation closure, not current
  exact-head proof. The
  existing CFDrs decision to remove its newly introduced legacy-Clippy step is
  a documented gate-boundary decision, not a lint-debt closure; the remaining
  lint floor stays in the Atlas conformance ratchet.

**Moving-default reconciliation (2026-08-17):** Atlas is advancing fourteen
fetched provider defaults in the current root commit: Themis `f61173bc`, Tyche
`5eeaba95`, Proteus `cb70021b`, Mnemosyne `d1144f74`, Consus `2dcf05a8`,
Helios `39a24992`, Hermes `dd4cb129`, Aequitas `c74b662c`, Asclepius
`5de8a48c`, Moirai `3d5d4c66`, RITK `ae23d4b2`, Coeus `b14777d8`, Apollo
`df8999f9`, and Iris `da210d2f`. This pointer evidence is separate from
provider hosted-gate evidence. The nested primary checkouts remain peer-owned.
The CFDrs follow-up is pushed at `e6633964` on
`codex/cfdrs-runtime-residual` and is carried by PR #348. Its final local
value-semantic gates pass; the exact-head hosted Rust and Pages gates remain
the delivery gate.

**Live exact-head sweep (2026-08-17):** fetched provider defaults advanced
Mnemosyne to `924cdcce`, Aequitas to `c74b662c`, and Leto to `d966e32c`. Their
root gitlinks are advanced to those fetched default heads; the primary
checkouts remain peer-owned and may be on separate branches with dirty
lockfiles or artifacts. Only the root gitlinks are advanced here. The
the exact requested 20-provider audit, lane audit, and nine conformance tests
pass after this pointer sweep.

**Expanded audit refresh (2026-08-18):** the active product scope is the
22-provider set named above, not the earlier twenty-provider snapshot. The
Atlas structural audit now includes Harmonia and the corrected Tyche spelling
and checks active registration, fetched-default gitlinks, and exact-head
workers. Apollo PR #104 has merged into provider default `d585e0f5`; the
provider package is now `apollo-fft 0.27.0`. The latest root source head
`c049d26` passes hosted Atlas conformance run `32159744862`, while hosted
overlay run `32159744891` reports the peer-owned consumer boundary: CFDrs
requires and locks Apollo `0.26.0`, and Kwavers locks `0.26.0`, against the
committed provider `0.27.0`. The standalone exact-head/version guard reports
one corresponding RITK manifest residual. The re-open trigger is the
consumer-side Apollo requirement/lock sweep followed by its affected hosted
matrix; no compatibility path is permitted.

The CFDrs backward-step slice is at provider head `7b9673ef`. Local focused
and full `cfd-2d` gates pass, including 585/585 tests. Hosted run `32143999878`
passes the book-figure job but its numerical-fidelity job times out in
`test_benchmark_run_integration` and `cross_fidelity_trifurcation_dominance`
at the committed 30-second slow bound. The workloads and budgets remain
unchanged; the next CFDrs increment is a production-path root-cause slice,
not a test or timeout relaxation.

**Post-gate recheck (2026-08-18):** at root commit `3669fff`, the full
`atlas-provider-integration-audit.py --exact-heads --provider-set atlas-22`
passes structural registration, fetched-default gitlinks, exact-head workers,
and its live requested-provider coherence scope. The standalone version guard
also reports `defect_count: 0`. This does not close the separate Helios lock
drift from the overlay check, nor any hosted provider release or Pages gate.

**Gitlink reconciliation (2026-08-19):** root commit `95a3f77` advances the
Mnemosyne gitlink to fetched `origin/main` `d00f139e` and the Consus gitlink to
fetched `origin/main` `2e0df9f8`. The exact-head provider audit passes for all
22 registered providers and the CFDrs/Kwavers/Helios integrator pointers;
`atlas-stack-overlay.py check` and `atlas-lock-form.py check` also pass. The
Mnemosyne and Consus primary checkouts retain peer-owned dirty work, so this
pointer-only increment makes no provider-local source, lockfile, or hosted-gate
claim.

**Clean-checkout proof (2026-08-18):** the provider audit now has an opt-in
`--require-clean-checkouts` gate that compares each initialized checkout's HEAD
to the committed gitlink and rejects tracked or untracked dirt. The gate is
implemented and regression-tested, but the current shared tree fails it on
peer-owned state: checkout-head drift is present in Tyche, Helios, Moirai,
RITK, Hephaestus, Apollo, and Hermes; dirty checkouts include Themis, Tyche,
Proteus, Mnemosyne, Helios, Harmonia, Aequitas, Asclepius, Eunomia, Moirai,
RITK, Melinoe, Leto, Hephaestus, Coeus, Apollo, Hermes, and Iris. This is the
clean-revision evidence boundary, not permission to discard peer work. The
re-open trigger is a clean coordinated checkout followed by the same gate.

The release, PyO3/PyPI, crates.io, mdBook/Pages, comparative-test, and
provider-adoption audits are dispatched as independent read-only work. Their
returned file-level findings become separate vertical items before any
consumer implementation changes are made.

**Delivery-surface findings (2026-08-18):** the audit returned no P0 but
identified P1 gaps that now have explicit owners and dependency order:
Helios' enabled `mdbook test` contradicts its recorded failing snippets;
CFDrs and Helios lack complete wheel/PyPI gates; Kwavers' k-wave comparator is
not reproducible from the checkout; and locked `cargo tree` is blocked by the
shared overlay attempting to rewrite peer-owned locks. P2 gaps include
incomplete binding metadata, Kwavers ABI3/path drift, import-only wheel smoke,
stale CFDrs/Kwavers Pages path filters, and incomplete recursive figure SSOT
checks. The next slices repair these at their owning repositories; Atlas does
not claim registry, wheel, or live Pages evidence from a read-only audit.

**Provider/Python audit refresh (2026-08-20):** committed manifests show direct
provider edges in CFDrs, Kwavers, and Helios, but adoption is not source-closed:
Kwavers retains direct `wgpu` edges in `crates/kwavers-analysis` and
`crates/kwavers-gpu`; RITK retains `crates/ritk-wgpu-compat`; and CFDrs still
owns the stateful Anderson/Aitken wrapper in
`crates/cfd-2d/src/network/coupled.rs`. The static PyO3 audit finds strong GIL
release in RITK, Helios, Coeus, Apollo, Moirai, and Leto, but no release sites
in CFDrs and only one in Consus, with incomplete Kwavers coverage. Coeus,
Hephaestus, and Leto lack complete `pyproject.toml`/typing metadata, and no
PyPI upload or post-publication install smoke is proven. These are provider-
owned implementation items; no compatibility shim or registry claim is added.

**Multiphysics boundary audit (2026-08-21):** three independent read-only
audits now provide the acceptance-driving findings for integrator closure.
CFDrs still converts coupled-network solve failure to default diagnostics in
`crates/cfd-2d/src/network/coupled.rs`, silently downgrades requested GPU
Poisson work in `crates/cfd-2d/src/solvers/accelerated.rs`, installs a
process-wide validation allocator, and runs domain calculations in its PyO3
surface without GIL release or complete input validation. Its backward-step
validation checks residual magnitude without the solver's explicit convergence
flag. These are correctness and operational-integrity defects.

Kwavers comparative tests use empty/default sources in several solver cases;
the Python comparator can fall back to the first successful simulator and
truncate mismatched arrays, while k-Wave tests are opt-in/skipped and cached
parity artifacts lack provider/oracle provenance. Its comparative FDTD path
computes but does not use the CFL timestep, and the Python array boundary copies
inputs and outputs despite a zero-copy claim. A parity claim remains blocked
until a fresh nonzero-source homogeneous IVP gate uses an analytical
d'Alembert oracle and a mandatory independent k-wave-python run.

Harmonia's typed `FieldEnvelope`/`GridGeometry` implementation exists only at
feature branch `5b1bc28792347b660ce653b8946a7c0a618cc649`; the committed
default still exchanges raw slices. Helios loaders multiply untrusted DICOM
and HDF5 dimensions before allocation, GPU tests are ignored or adapter-skipped
by default, and its Python package lacks `py.typed`/stub artifacts. Themis has
no confirmed soundness defect in the inspected implementation, but its local
checkout is stale relative to `origin/main` and needs current-default safety
evidence.

The root `scripts/atlas-multiphysics-audit.py` records checkout revision,
committed gitlink, dirty state, direct provider edges, PyO3/GIL evidence,
`py.typed`/`.pyi` typing surfaces, book fences, analytical/differential
markers, performance/memory markers, and unsafe-code policy. At Atlas
`474adbe`, it requires and confirms both the existing `tyche-core` edge and
`tyche_core` source consumption in CFDrs, Helios, and Kwavers. It finds no
CFDrs GIL-release site or source
typing artifacts; no source typing artifacts in Helios or Kwavers; Kwavers's
direct `wgpu` edge; and Helios/Kwavers runnable-book gaps. Blocking mode also
rejects the dirty,
gitlink-drifted provider checkouts; `--require-evidence` fails as intended.
No provider pointer advances until fixes merge to default and exact-head
hosted, book, wheel, and Pages evidence is terminal.

The Tyche edge is real source consumption, not an unused manifest entry:
CFDrs imports `tyche_core` in `cfd-optim` sampling, Helios imports
`Seed`/`SplitMix64`/`StandardNormal` in imaging noise, and Kwavers imports
Tyche designs, seeds, moments, and conformal calibration in its analysis and
geometry sampling modules. These references were checked in the live
provider trees; they do not substitute for clean exact-head or hosted proof.

The full Atlas-22 structural audit at this integration revision reports
`22/22` active providers and zero issues, including Harmonia, Gaia, and the
Tyche canonicalization. The stack overlay remains aligned after restoring
only derived lockfile churn; no provider source or gitlink changed.

The checker’s focused suite passes `7/7`; the complete root Python suite at
Atlas `158aeca` passes `233/233` in `7.5 s`. The requested-provider structural
audit remains `20/20` with zero issues, the development overlay reports
aligned requirements and locks, and registry metadata reports `253` manifests,
zero violations, and zero unverified entries.

**Tyche standalone gate (2026-08-21):** the clean checkout at exact gitlink
`10410f2de1ce1529ecbff50fa740b23a1c8f77b9` passes its pinned Rust `1.97.0`
format, locked `tyche-core` check, workspace all-target/all-feature Clippy
with `-D warnings`, Nextest `51/51`, doctests (`18/18` executed doctests),
warning-denied workspace docs, the `reproducible_study` example, and every
single-iteration `counter_sampling` benchmark case. The commands ran from
outside the Atlas configuration tree with the shared target directory, so the
committed lock was not rewritten; Tyche remains clean. This is local provider
evidence only; hosted CI, Pages, and the fetched-default pointer still remain
separate delivery gates. Direct local `mdbook test` is not counted as green:
without staged artifacts it reports `E0463`, and the shared target contains
multiple historical rlibs that produce `E0464`/`E0460` under local staging.
The reusable Pages workflow's fresh-runner staging path is therefore the
authoritative Tyche book gate until a clean isolated runner result is collected.

The intentional live conformance scan on the dirty shared tree reports 19
ratchet increases and 25 decreases. The increases are confined to active
peer-owned scopes: CFDrs (oversized files, allow sites, existence-only
assertions, commented-out code, and one excess worktree), Consus (oversized
files, manifest implementation, production unwraps, allow sites,
existence-only assertions, type-suffixed functions, and orphan modules),
Kwavers (one target fork and one excess worktree), Leto (one excess
worktree), Moirai (SeqCst sites), and RITK (manifest implementation,
type-suffixed functions, and commented-out code). No baseline was regenerated;
these counts require clean exact-head provider attribution before any source
repair or ratchet update.

**Dependency-ordered re-open triggers:** (1) collect Harmonia PR #9 at its
merged default, then migrate CFDrs to the native typed field and delete its
superseded wrapper; (2) implement the Kwavers reproducible IVP parity gate and
fresh-oracle provenance; (3) harden Helios dimension/resource boundaries;
(4) complete PyO3 GIL, validation, typing, and installed-wheel evidence; and
(5) rerun the full Atlas exact-head, overlay, lock, book, figure, performance,
memory, and hosted Pages acceptance oracle.

**Book/figure audit refresh (2026-08-20):** strict link validation scans all
25 current books with zero missing files, anchors, or reads; `mdbook build`
completes for all 25. The executable-gate inventory is 19 shared callers and
six residuals: Consus has no gate; Gaia, Helios, and Kwavers have vacuous
or non-executable coverage; and Hephaestus and RITK have no gate. Themis is
already gated; Leto has a committed book and Pages caller. Direct local
`mdbook test` on the un-staged repositories fails with missing `--extern`
crates, so it is not treated as provider sample proof; the staged package
workflow and hosted runs remain authoritative.

- **Provider-adoption slice:** audit every integrator edge for direct use of
  the owning provider API, deletion of superseded local wrappers, and no
  silent CPU/GPU, storage, or scheduler fallback. File provider capability
  gaps upstream before changing a consumer.
- **Physics-contract slice:** exercise typed time (`horae`), quantities
  (`aequitas`/`eunomia`), material and optical laws (`proteus`/`hyperion`),
  coupling (`harmonia`), storage (`consus`), geometry (`gaia`), imaging
  (`ritk`), biological response (`asclepius`), and execution/accelerator
  paths (`mnemosyne`/`moirai`/`themis`/`melinoe`/`hermes`/`leto`/`hephaestus`/
  `apollo`/`coeus`/`iris`) through value-semantic scenarios in the three
  integrators. A green build without an analytical or differential oracle is
  insufficient.
- **Performance and memory slice:** establish controlled baselines before
  claiming speed, allocation, or memory improvements; inspect allocation
  counts, shared-cache growth, buffer reuse, zero-copy boundaries, and
  criterion confidence intervals. Optimize production paths only; preserve
  workload sizes and test budgets.
- **Documentation slice:** keep each domain book's chapter map, examples,
  figures, and provider links synchronized. Enable or repair `mdbook test`
  only where the committed samples compile, and verify the final Pages
  artifact and live deployment at the same revision as the source.

**Atlas-owned delivery increment (2026-08-18):** the reusable
`.github/workflows/python-wheels.yml` workflow now accepts an explicit
provider-owned pytest path and runs that suite after wheel installation in
importlib mode. The default pytest pin is `8.4.2`, which supports the
workflow's Python 3.9 floor; providers must still opt in with a bounded,
value-semantic test path. This adds the shared gate only; it does not claim a
provider's PyPI publisher or hosted result until its caller is updated and a
same-head run passes.

**Harmonia capability boundary (2026-08-18):** direct CFDrs adoption remains
open because `repos/CFDrs/crates/cfd-2d/src/network/coupled.rs` preserves a
stateful Anderson/Aitken resistance-mixing contract. Harmonia PR #6 merged at
provider default `b98d3f4` and now provides the mutable pair-level
`Relaxation<T>` seam, atomic fixed/full policies, provider-owned
`AitkenRelaxation<T>`, ADR 0002/0003, analytical and transactional coverage,
and hosted verify, supply-chain, and book-build evidence; RecurseML remains
report-only. Atlas advanced the root gitlink to `b98d3f4`. Adding a consumer
adapter or fixed-relaxation fallback would violate provider-first ownership.

**Harmonia conformance closure (2026-08-18):**
`ATLAS-HARMONIA-CONFORMANCE-001` is complete. PR #7 merged at provider
default `3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb` and Atlas root commit
`c049d26` advances the gitlink without touching the dirty primary checkout.
The clean provider-lane conformance scan reports zero across all 27 classes.
Hosted run `32159533930` passes verify `95784806220` and supply-chain
`95784806422`; RecurseML remains report-only. The direct CFDrs consumer
migration remains the next provider-first slice.
The next slice is direct CFDrs integration and deletion of the superseded
local wrapper. The primary Harmonia checkout retains peer-owned
workflow/book/example/lockfile dirt.

**ATLAS-HARMONIA-AITKEN-001 — provider-owned stateful relaxation [minor] [arch]**
**Status:** complete; **owner:** atlas coordinator; **claimed scope:**
`repos/harmonia/src/relaxation/aitken.rs`, the Harmonia relaxation tests and
ADR index/record, and the relaxation book chapter. The provider must own the
input-sensitive Aitken policy used by the CFDrs pair contract, preserve native
scalar precision, validate dimensions and finite state transactionally, and
provide analytical and differential evidence. The CFDrs wrapper remains out
of scope for this claim and is deleted only in the following consumer slice
after the provider contract is merged and integrated. Acceptance is provider
local locked check, warning-denied Clippy, Nextest, doctest, Rustdoc, book
build, and hosted verification at the exact provider head; no fallback,
adapter, or workload relaxation is permitted. The provider contract remains
delivered at merged default `b98d3f4`; conformance cleanup is now merged at
`3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb`, and the following CFDrs consumer
item owns the remaining wrapper deletion.

**Provider implementation (2026-08-18):** Harmonia commit `584e961` merged via
PR #6 at provider default `b98d3f41d640b3a79df125ef1b3ff786156c5dd3`. The source
slice adds `AitkenRelaxation<T>` with native `RealField` arithmetic,
transactional pair updates, typed configuration/value errors, reusable state,
ADR 0003, and synchronized book/README claims. Local locked all-target check,
warning-denied Clippy, full Nextest 24/24, focused Aitken 7/7, doctest 1/1,
Rustdoc, runnable example, and mdBook build pass. Local `mdbook test` cannot
resolve the four staged dependency rlibs; the provider workflow supplies those
paths explicitly, so this is an environment limitation rather than a changed
gate. Hosted verify, supply-chain, and book checks pass at the exact head;
RecurseML is an analyzer error and remains report-only. Atlas first advanced
the implementation gitlink to `b98d3f4`; the subsequent conformance cleanup
merged at `3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb`.

**Post-merge exact-head recheck (2026-08-18):** Atlas root `c049d26` passes
the 22-provider structural exact-head audit with Harmonia at merged default
`3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb`. The full exact-head audit and
standalone version guard each report exactly one peer-owned residual: RITK's dirty
`crates/ritk-filter/Cargo.toml` requires `apollo-fft 0.26.0`, while the current
provider package is `0.27.0`. The RITK consumer migration remains outside this
slice; no dirty manifest or lockfile is altered here. Hosted Atlas conformance
run `32159744862` passes; overlay run `32159744891` fails on the peer-owned
CFDrs requirement and CFDrs/Kwavers `Cargo.lock` pins at `0.26.0`.

**Latest hosted-state recheck (2026-08-18):** Apollo PR #104 is merged at
default `d585e0f5` with Rust/Python checks green and benchmark run `32140805200`
failed; Helios PR #65 is merged at default `aa7a4fa` with Rust/Python/book
checks green and its benchmark check still in progress; CFDrs PR #349 is open
at `3a03a222` with hosted run `32152884477` queued; and Kwavers PR #402 remains
open with its complete matrix failed or cancelled despite passing benchmark
smoke. The Atlas structural exact-head audit is green, but full exact-head
coherence and the version guard still report the peer-owned RITK
`apollo-fft 0.26.0` requirement against provider `0.27.0`; the hosted overlay
also reports CFDrs's `0.26.0` requirement and CFDrs/Kwavers `Cargo.lock` pins
against that provider. These are delivery residuals, not reasons to alter
workloads, budgets, or consumer contracts.

**Acceptance oracle:** the structural provider audit reports all 22 named
providers present and active; the exact-head audit passes on a clean checkout;
the generated overlay and locked dependency graph pass; CFDrs, Kwavers, and
Helios provider-consumer gates pass at their merged default heads; conformance
ratchets do not regress (including the corrected benchmark-target classifier);
the focused multiphysics scenarios pass analytical/differential checks; the
applicable performance and memory evidence is recorded without unsupported
claims; and the provider/integrator books build, test, deploy, and resolve
their live Pages URLs. Residual external or peer-owned work remains an
explicit board item with its exact blocker and re-open trigger.

### Provider ratchet closures completed in this increment

- `ATLAS-CONSUS-UNWRAP-099`: Consus source `a9a56ad` and PM closure
  `087f810`; the provider scan returns `unwrap_production=383` without a
  baseline edit. Default/no-default locked Nextest passes 2553/2553 and
  2031/2031; hosted CI `32020339446`, Documentation `32020339452`, and Pages
  `32020338335` pass at the exact source head.
- `ATLAS-LETO-CONTRACT-100`: Leto source `6463f4a` and PM closure `e04fdc7`;
  the provider scan returns `existence_only_assertions=9` without a baseline
  edit. Focused locked Nextest passes 550/550; hosted CI `32021076930` and
  Pages `32021074899` pass at the exact source head.
- `ATLAS-CFDRS-CONFORMANCE-101`: CFDrs source `e9c84bf6` and PM closure
  `38bdbeb9`; the provider scan returns baseline
  `existence_only_assertions=137` and `tag_pinned_actions=0`. Locked package
  check, focused locked Nextest 166/166, doctests, and hosted CI
  `32022469516` pass at the exact source head. The Atlas gitlink is advanced
  to the PM closure commit; provider-wide strict Clippy debt remains explicitly
  recorded in the provider PM artifacts.

Dependencies: `ATLAS-COEUS-LINT-RATCHET-097`,
`ATLAS-CONFORMANCE-BENCH-099`, `ATLAS-PUBLISH-001-BOOK-MDBOOK-TEST-001`,
`ATLAS-OVERLAY-005`. This item is the parent audit; its vertical slices close
independently with their own evidence.

**ATLAS-COEUS-LINT-RATCHET-097 takeover:** Atlas session owns the clean lane
`D:/atlas/worktrees/coeus-layernorm-shape`. The prior lane claim is stale: its
last commit is `66bf4897` at 2026-08-16 22:11 -0400 and no newer board update
exists; the peer-dirty primary Coeus checkout remains excluded.

The takeover audit found the claimed lint work already merged upstream: Coeus
PR #334 is at default `a8ea12eb`, production `allow_sites=0`, and hosted
Backend parity run `31989331059` passes. The lane is released without source
edits.

**Coeus PR #346 merged 2026-08-26 at `dbbdfc82ad06b5b0fb20db0719215ce89fb20f33`:
clippy backlog cleared, gate now denies.** 41 outstanding clippy warnings
across the Coeus workspace are gone; the Lint and documentation step now uses
`-D warnings`. Bulk: 31 `.get(0)` → `.first()` across 23 files via
`clippy --fix` (identical in meaning). Rest: three deeply nested return
tuples now have type aliases (the linalg one earns it — the fourth tensor
is the permutation carrying each CSR slot back to the COO entry it came
from, and `(Tensor, Tensor, Tensor, Tensor)` said none of that);
`collect_graph`'s inner `traverse` threaded eight `&mut` accumulators through
recursion, now a `Traversal` struct; five loops indexed over a range derived
from that slice's own length, now direct iteration; three expired
`#[expect]`s removed (one turned out to still be load-bearing — that loop is
fixed rather than re-suppressed). 78 `#[expect]` sites still cite
`ATLAS-COEUS-LINT-RATCHET-097` (67 `too_many_arguments`); they stay tracked.
A *new* diagnostic now fails the build instead of joining a pile. Local
verification: 1130 tests pass. Hosted: all 7 real checks pass (CUDA 17m38s,
Metal 8m10s, ROCm 8m29s, WGPU 24m50s, Format 21s, Lint and documentation
1m24s, Lockfile integrity 33s, Tests 25m2s, CodeRabbit completed);
`recurseml/analysis` is the always-report-only error. Atlas gitlink advanced
`b3b1208e` → `dbbdfc82a` (commit `289bb05db`).

### Current residuals from the 2026-08-16 provider-consumer audit

#### ATLAS-MNEMOSYNE-CONFORMANCE-101 — Close exact-head assertion ratchet [patch, closed 2026-08-17]

The NUMA binding test's fifth `is_ok()` assertion was replaced with an exact
`Ok(())` assertion in provider commit `30126aa`, merged at default
`39d76d2`. Hosted Rust verification, Loom, and Miri (Stacked and Tree Borrows)
passed in run `32024295467`. Provider PM closure `f06c8f9` merged at
`26ea626`; the Atlas gitlink advances to that PM closure. The provider scan
baseline is now four existence-only assertions. The local locked check was
blocked by the shared Atlas overlay resolving patches to the peer-dirty
primary checkout; hosted verification is the compilation and behavior gate.

#### ATLAS-CFDRS-NUMERICAL-FIDELITY-101 — hosted resource contention [patch] — closed

CFDrs PR #344 was rebased onto the newer default branch after GitHub reported
the previous branch as dirty. The forward fix retained every fidelity case
and assertion while splitting the remaining Venturi 1D↔2D and 1D↔3D
contracts; the 30-second/60-second budgets and workloads were unchanged. The
workflow lock-normalization fix made the materialized path-dependency graph
reproducible. Exact-head run `31994843367` passed format, locked workspace,
nextest, numerical fidelity, doctests, and book figures. The PR merged at
`2d9e505a2bb753925f1b3900795e16ac3247a6b2`, and Atlas commit `03de90a`
advances `repos/CFDrs` to that default head. The local locked gate remains
blocked by the peer-dirty Mnemosyne compile error at
`crates/mnemosyne-core/src/memory_diagnostics.rs:96`, not by the merged CFDrs
change.

#### ATLAS-HELIOS-DICOM-GEOMETRY-103 — required geometry defaults [major] — closed 2026-08-17

`repos/helios/crates/helios-domain/src/dicom.rs:121-132` substitutes unit
spacing and zero origin when `PixelSpacing` or `ImagePositionPatient` is
missing. The loader documentation at `:275-280` simultaneously describes
those attributes as required-error inputs while documenting the defaults.
`ImageOrientationPatient` follows the same identity-default contract. The
acceptance oracle is a typed error for each missing or malformed required
geometry attribute plus negative fixture coverage through Helios' DICOM gate;
RITK remains the sole DICOM parser/decoder owner. The clean integration lane
implements the typed rejection at Helios commit
`67f0d60f2ec543dc630ce94d2a1698ddd9e66f54`; local DICOM nextest passes 45/45,
doctests pass, and warning-denied Clippy passes. The counterbalanced benchmark
rerun in exact-head hosted run `31990847118` passed, as did the Rust workspace
and Python bindings. PR #57 merged as `7fddf789`; Atlas advances that merged
default gitlink. The peer-dirty primary checkout remains untouched.

#### ATLAS-KWAVERS-HEPHAESTUS-VIS-104 — GPU ownership closure [arch] — closed 2026-08-18

Kwavers still constructs raw `wgpu` pipelines in
`crates/kwavers-gpu/src/beamforming/three_dimensional/provider.rs` and keeps
raw-WGPU visualization state in `crates/kwavers-analysis/src/visualization`.
The earlier bounded visualization subfinding is recorded at Kwavers commit
`40dac165e` and PR #386: field counts are validated, GPU compositing receives
every field, CPU diagnostics process every field, and multi-field rendering
without transparency is rejected. The current fetched default `6075940ce`
still has a separate initialization defect: PR #402 at source head
`b275b7115` now returns `SystemError::FeatureNotAvailable` when the renderer
and data pipeline are absent. The feature-enabled hosted matrix is pending;
the shared Atlas overlay prevents local compilation before the package gate
because its peer Asclepius checkout still requires `aequitas ^0.1.0` while the
current provider graph is `0.2.0`. The acceptance oracle still requires a
complete provider-owned execution path with explicit failure for unavailable
capability and no consumer-owned raw-WGPU kernel ownership.

The exact fetched-head audit at Kwavers `6075940ce` found two additional
consumer-contract residuals. `kwavers-gpu/src/validation/gpu_cpu_equivalence/
runner/mod.rs:100-110` returns a typed `FeatureNotAvailable` because the GPU
runner still has no provider-generic Leto/Hephaestus FDTD implementation; its
CPU-vs-CPU comparison is correctly rejected rather than reported as parity.
`kwavers-analysis/src/visualization/engine/mod.rs:181-217` had no error or
fallback arm when the `gpu-visualization` feature was enabled but the renderer
and pipeline were not initialized, so `render_multi_field` could return
`Ok(())` without rendering. This correctness defect is addressed by PR #402;
its required hosted feature gate is the re-open/close decision. The FDTD item
remains provider capability work and must not be replaced by an f64 adapter or
CPU-vs-CPU comparison.

#### ATLAS-KWAVERS-FDTD-107 — provider-generic FDTD equivalence [major] — closed 2026-08-18

The acceptance oracle is a real Leto/Hephaestus FDTD execution path selected
through the provider seam, a CPU differential comparison with a derived
reduction tolerance, and negative coverage for unavailable hardware. The
current explicit-unavailable result is historical evidence of the missing
capability. Hephaestus now owns the provider contract and kernel at merged
default `607ce3feb2e0ed1d907d3e0172e23377851e71d8`; Kwavers default `6075940c`
still has the pre-cutover consumer-owned raw-WGPU FDTD code at
`crates/kwavers-gpu/src/gpu/fdtd.rs`. No f64-only adapter, CPU fallback, or
CPU-vs-CPU comparison may be added to close it.

Implementation merged in Hephaestus PR #213 from exact head
`7bc9944852a6ba92d4ff265b9fff9bc8c81e3567` as merge commit
`607ce3feb2e0ed1d907d3e0172e23377851e71d8`. Kwavers PR #402 remains at exact
head `e1648019f24e71598d0421dbd11e4f011b75878a`. The provider branch owns the
typed f32 contract, WGPU kernels, and sequential two-step contract coverage;
the consumer branch deletes the collocated raw-WGPU path and wires the
independent native-f32 CPU differential runner without a fallback. Local
feature-enabled check/Clippy, 22/22 focused equivalence tests, 2/2 affected
allocation tests, and provider contract coverage pass. Hosted exact-head gates
for Hephaestus pass and its Atlas gitlink is advanced; Kwavers hosted gates
remain open. The Kwavers workflow currently reports Documentation Build and
Validate Clean Architecture failures while the remaining matrix is still
running; no consumer gitlink advance is authorized until the exact head is
green and merged.

#### ATLAS-CFDRS-BACKWARD-STEP-108 — input-sensitive reattachment measurement [major] — closed 2026-08-18

Owner: Atlas session; provider branch `codex/cfdrs-backward-step-108`.
The provider claim and acceptance contract are recorded in its `backlog.md`.

The original consumer-local `6 * step_height` result and duplicate
streamfunction solver are removed. `cfd-2d` now owns the masked
backward-facing-step geometry, SIMPLE execution, explicit step/no-slip/
parabolic-inlet/fixed-pressure-outlet contract, signed downstream lower-wall
shear samples, and interpolated negative-to-nonnegative crossing.
`cfd-validation` maps `BenchmarkConfig` to that provider and keeps
value-semantic integration assertions. The provider reapplies a normalized
parabolic inlet only on fluid cells, leaving solid inlet cells at zero.
Provider PR #349 is at source head `95801b48`; the focused local regressions
for negative branch-flow metadata and Dean cross-fidelity both pass. Hosted
book figures pass, but Rust workspace gate run `32087680839`, job
`95563482011`, fails in Clippy before tests on 153 pre-existing workspace
errors. Default CFDrs `main` fails the same Clippy command in run
`32086797481`; none of the reported files are in this PR's diff. No consumer
solver, hardcoded runtime correlation, tolerance reduction, or benchmark
workload change closes this item. Re-open trigger: default-branch Clippy
cleanup lands, or an explicitly scoped lint-cleanup item is claimed.

#### ATLAS-CFDRS-FOURIER-NATIVE-105 — native scalar contract [major] — closed 2026-08-17

The consumer-side `f64`/`Complex64` widen-narrow path and obsolete inverse
helper are deleted. CFDrs now calls Apollo's typed native-precision transform
contract directly, with an f32 round-trip regression. Focused Nextest passes
13/13, doctests pass, and package-local Clippy passes. The change merged in
CFDrs PR #345 at `a3c53da2`; exact-head hosted run `31997714748` passes the
Rust workspace and book-figure gates. No compatibility adapter remains.

#### ATLAS-CFDRS-SSOR-OWNERSHIP-106 — provider wrapper deletion [arch] — closed 2026-08-17

The consumer-owned SSOR wrapper and legacy re-export are deleted. Direct
Leto provider tests cover zero preservation, input sensitivity, mismatch
errors, and relaxation-parameter response; the focused filter passes 3/3.
The deletion merged with the Fourier slice in CFDrs PR #345 at `a3c53da2`;
exact-head hosted run `31997714748` passes the Rust workspace and book-figure
gates.

