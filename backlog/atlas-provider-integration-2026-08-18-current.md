<a id="atlas-provider-integration-2026-08-18-current"></a>
## ATLAS-PROVIDER-INTEGRATION-2026-08-18-CURRENT — superseding recheck [patch] — in-progress

- **Kwavers metadata correction:** provider commit `308d91594` separates the
  MATLAB-free `k-wave-python` comparison extra from the MATLAB Engine extra,
  repairs the repository-root `maturin` commands, and is recorded by Atlas
  pointer commit `ad977c6`. The compiled extension and hosted comparator remain
  open.
- **Kwavers guidance cleanup:** provider commit `498f38a3e` removes the last
  stale `cd pykwavers` and `pykwavers-*.whl` instructions from test diagnostics
  and examples; Atlas records the pointer in `0a3e2dd`. The compiled extension
  and hosted comparator remain open.
- **Kwavers workflow closure:** provider commit `2bc5dd161` repins the book,
  Python-wheel, and crates.io callers to Atlas reusable-workflow revision
  `2f17abc`; the Python `atlas-ref` now names the pushed provider graph. Atlas
  records the exact provider head in `55d8b8d`. YAML parsing passes; the local
  extension and hosted comparator remain open.
- **Kwavers comparator gate:** provider commit `4e0135c76` adds a bounded
  Ubuntu/Python 3.10 wheel job that installs the declared k-Wave Python range
  and executes the real comparison suite with slow tests enabled. Atlas records
  the provider head in `2e00759`; closure is pending its value-semantic result.
- **Kwavers comparator dispatch:** provider commit `a10183c80` adds an explicit
  manual trigger to the wheel-smoke workflow, and Atlas records the exact head
  in `4073b1f`. The hosted parity run is still pending.
- **CFDrs rerun:** PR #358 now points at `5e13018a` after a hosted Clippy
  failure found and the provider fixed `clippy::inconsistent_struct_constructor`
  in `newton_fallback.rs`. Rust and figure jobs are pending; the pointer stays
  at the prior verified integration head until both pass.
- **Status:** Tyche cleanup, Aequitas integration, and the Aequitas/Themis
  hosted closures are complete for this increment. The remaining integration
  residuals are Apollo PR #107's rerun, Mnemosyne's moving default, CFDrs's
  figure/hosted closure, Kwavers's missing local Python extension, Helios's
  provider PM drift, and four peer-owned lane-topology violations. The
  structural provider audit, overlay, and standalone lock-form gates pass;
  exact-head is blocked only by Mnemosyne's unadvanced default.
- **Tyche evidence:** provider commit `de925e6` consolidates the shared
  Latin-hypercube/Sobol checked index conversions, removes five production
  type-suffixed helper names, and merged through PR #26 at default
  `7e55ff8f`. Nextest 51/51, doctests 18/18, warning-denied Clippy, rustdoc,
  and the conformance report all pass; every tracked conformance class is
  zero.
- **Atlas evidence:** the root pointer now matches fetched RITK default
  `9fa4981e`, a docs-only merge on top of the audited `f9d04a79`. Lock-form
  passes for 27 standalone locks and conformance passes 12/12. The latest
  exact-head audit is `OK` and the overlay reports aligned requirements and
  locks; the earlier RITK Apollo/Hermes local residual is superseded by the
  current peer checkout state.
- **Hephaestus evidence:** its default branch is `master`; head `607ce3f`
  passes CUDA `32083561386`, WGPU `32083561356`, ROCm `32083561357`, and Metal
  `32083561389`. The prior absence-of-run classification is superseded.
- **Coeus evidence:** PR #339 merged its Apollo FFT 0.27 lock resolution at
  default `5adc2d1649bfd2bf68c529b011308e150375810d`; Atlas stages that exact
  gitlink without touching the dirty primary checkout. The former backend
  parity failure at `79f05dfd` is superseded by the merged provider closure.
- **CFDrs evidence:** PR #355 carries provider commit `1bebb5e1`. The
  previous Rust-gate timeout is addressed by caching the normalized parabolic
  inlet profile once per solve. Exact-head run `32197696210` now fails in the
  hosted Clippy job at `cfd-2d/src/solvers/ns_fvm/solver/solve.rs:218` for
  `clippy::if_not_else`; the book-figure job passes. The provider branch needs
  that warning-denied correction before merge; no CFDrs checkout was changed.
- **Aequitas evidence:** PR #35 merged the provider structure cleanup at
  default `260ad10dd5480eef8c82958d1d148199656db59e`; its verify,
  supply-chain, post-merge CI `32198085105`, and Pages
  `32198084983` checks pass, with RecurseML report-only. Atlas advances the
  Aequitas gitlink to the exact merge commit without modifying the provider
  checkout.
- **RITK evidence:** fetched default `9fa4981e` is the docs-only merge of PR
  #176 (`backlog.md` correction). The Atlas gitlink is staged to that exact
  commit; the previously collected CI/Python runs remain attached to `f9d04a79`
  and do not establish the new default head. No run is currently attached to
  `9fa4981e`.
- **Gaia polyline/direction evidence:** Atlas now advances the gitlink to
  merged provider default `dbed97a63434a21b1b9dcd01d634276aaec99e37`, which
  contains the validated `gaia::Polyline` contract and the new
  `UnitSphereDirectionSet` backed by the existing `GeodesicSphere` and Leto
  `UnitVector3`; RITK's TCK/TRX consumers import Gaia's canonical type
  directly. Provider local nextest 972/972, warning-denied Clippy, doctests
  9/9, format, and Rustdoc pass. PR #32 hosted CI `32206596573` and mesh-book
  verification `32206596795` pass; CodeRabbit passes and `recurseml/analysis`
  remains report-only error.
- **Mnemosyne evidence:** PR #62 source head `0022926` passed Rust
  verification, MSRV, Loom, Miri, aarch64, ThreadSanitizer, and CodeRabbit;
  `recurseml/analysis` is report-only. The provider default moved from
  `43cdf047` to `cbccb7ee826b387e4e0ccc4499beb57a88bb51c7` after the first
  exact-head run `32206977029` failed Miri compilation on the missing
  `SEGMENT_SIZE` import. Exact-head run `32208332797` is now in progress for
  the provider's corrected Miri-gate topology; Loom, aarch64, and
  ThreadSanitizer are green while Rust verification and Miri remain
  uncollected. Atlas remains at `64f0d2e` until that exact default-head run
  completes.
- **Hosted recheck:** Aequitas CI `32198085105` and Pages `32198084983` pass
  at `260ad10`; Themis CI `32194584768`, MSRV `32194584736`, and Pages
  `32194583598` pass at `0484a333`. CFDrs run `32197696210` fails only in
  Clippy at the provider source location recorded above.
- **Acceptance:** collect Apollo PR #107's rerun, the corrected CFDrs exact-head
  run, the absent RITK default run classification, Horae PR #19's exact-head
  checks, and Mnemosyne run `32208332797`; then reconcile only verified
  provider heads. The overlay and standalone lock-form gates pass; the current
  exact-head gate is blocked by the unadvanced Mnemosyne default. Preserve
  peer-owned checkout and lane state.
- **Documentation evidence:** the stack-wide link detector passes for all 23
  registered provider books with zero missing files, missing anchors, or read
  failures. Its fixture regression suite passes 43/43 with the intentional
  missing-link case covered.
- **Automation cleanup:** the committed fast Python tier had one collection
  defect because `test_atlas_scattered_containers_classify.py` imported through
  `scripts.*` while `pytest.ini` exposes `scripts` as the module root. The
  import now matches the configured namespace; the fast tier passes 225 tests,
  17 deselected tests, and 74 subtests in 13.75 seconds.
- The committed slow Python/book tier also passes 17/17 in 1.62 seconds;
  documentation helper coverage is green at the delivered root revision.
- **Horae result:** provider lock commit `9cc9fd8` plus PM synchronization
  `aefe641` and evidence-boundary correction `91a020c` pass post-merge CI
  `32202560133` (`verify` and `supply-chain`) and Pages deployment
  `32202559349` at exact default `1ed6a172aa1ef57765c4d07ae740e6c297913567`.
  Local-graph format, locked metadata, both feature configurations, Clippy,
  20/20 Nextest, doctest, rustdoc, and cargo-deny pass; the root gitlink now
  records the merged default. The root-overlay rejection remains a
  development diagnostic rather than standalone proof.
- **Hyperion lock slice:** provider commit `880eb8c` refreshes the clean
  standalone lock to Aequitas `260ad10`, Eunomia `85e590b`, and Proteus
  `f612c99`; hosted `verify` and `supply-chain` pass at exact head
  `880eb8cce28d1e887942fbeb185a1cf4173c776a`, and PR #15 merged at default
  `0156f59f78aba1e3b06d4511ffb1ce30d5c0c6d4`. Local format and locked
  all-feature metadata pass. The root-overlay `cargo check --locked` rejection
  remains a pre-compilation development-overlay diagnostic, so Atlas advances
  only to the verified provider merge commit. Provider-local HYPERION-006
  closeout passed hosted `verify` and `supply-chain` at exact head
  `86486139120243e0b6cae84143d7a914eb51a8a3`; PM-only PR #16 merged at
  default `93157c235d1bfabd88a4720b4a02370ff2a00cc2`.
- **Clean-checkout evidence:** after fast-forwarding the owned Horae and
  Hyperion checkouts to their merged defaults, the fresh
  `--require-clean-checkouts` audit reports 23 findings across 17 peer-owned
  provider checkouts. Head drift is present in Themis, Tyche, Aequitas,
  Moirai, RITK, Hephaestus, Coeus, and Apollo; tracked or untracked dirt is
  present in Themis, Proteus, Consus, Helios, Harmonia, Eunomia, Moirai,
  Melinoe, Leto, Hephaestus, Coeus, Apollo, Hermes, and Iris. RITK also has
  an `apollo-fft 0.26.0` requirement that does not accept the current 0.27.0
  package. No peer checkout was changed.

**Current lane residual:** `python scripts/atlas-lane-audit.py` reports five
violations: Consus has four trees plus a lane outside the canonical root,
Kwavers has four trees with a detached lane, and RITK has four trees. These
are peer coordination state; no lane or checkout was changed by this pass.

**Cache-fork residual:** the fresh provider conformance scan reports one real
Cargo cache fork at `repos/horae/target` (`.rustc_info.json` present). The
configured shared target is `D:\atlas\target`; the repo-local cache is derived
state, not source. Its exact recursive deletion was refused by the shell safety
policy in this pass, so it remains open under ATLAS-CACHE-FORK-055.

