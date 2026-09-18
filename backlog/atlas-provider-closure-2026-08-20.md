<a id="atlas-provider-closure-2026-08-20"></a>
## ATLAS-PROVIDER-CLOSURE-2026-08-20 — Complete active provider slices [major][arch] — in-progress

- **Themis executable book gate:** current Atlas session claims the provider
  workflow caller only, on the reusable `themis-book-test` lane. The existing
  book already has two included executable examples; acceptance is a provider
  PR adding the shared `mdbook-test` inputs, exact-head hosted book success,
  and post-merge default verification. PR [#27](https://github.com/ryancinsight/themis/pull/27)
  merged at default `c76a55e5eb9988b48bba69e67d6e07ce5fe55ea8` after exact
  PR CI `32399070177`, MSRV `32399070178`, and book build `32399070626`
  passed. Post-merge CI `32402753573`, MSRV `32402753617`, and Pages/book
  run `32402752669` now pass, including deployment job `96545229314`; the
  live page returns HTTP 200. The Atlas gitlink equals that merged default.

- **RITK executable book gate:** current Atlas session claims the provider
  workflow caller and existing executable samples only, on the reusable
  `ritk-book-test` lane. Open PR #201 owns source, lockfile, and connectome
  chapter changes; this item does not overlap those paths. PR #202 merged at
  default `ad5085257b6dee9110375bbca29e20d676c83f58` from exact head
  `dc9bf9cda2fd007597205312645038bc48727d0c`; local mdBook build and strict
  links pass, but the PR provider CI, Python, and book runs
  `32402257906`/`32402258085`/`32402259004` were still queued at merge. Default
  CI, Python, and book runs `32404089256`/`32404089147`/`32404089897` are now
  queued. Acceptance remains terminal passing evidence on the merged default;
  Atlas does not advance the gitlink from `d4a978f` until then. The book run
  failed with `E0460` because the shared workflow selected a hashless
  dependency artifact by directory order; root `20c9398` preserves Cargo
  artifact hashes, and RITK PR [#204](https://github.com/ryancinsight/ritk/pull/204)
  adopts it at `9bc47d42`. Its CI and book runs `32410451435`/`32410452203`
  pass; the current default `b35c9331` has terminal CI and Pages deployment
  success, and live Pages returns HTTP 200. The Atlas pointer advances from
  `d4a978f` to `b35c9331` without switching the dirty primary checkout.

- **Apollo executable book gate:** current Atlas session claims only
  `apollo/.github/workflows/book-pages.yml` on a clean `apollo-book-test` lane.
  The existing FFT round-trip and Parseval examples are included by the book
  and already carry value-semantic assertions. Acceptance is the shared
  `mdbook-test` caller against `apollo-fft`, exact hosted book evidence, and
  post-merge default verification. Apollo's peer-owned Cargo.lock, backlog,
  and CHANGELOG work remain outside this item; the hosted gate is sequenced
  after the active RITK collection. Local commit `27f0c4c3` passes mdBook build,
  strict links across 14 Markdown files, and workflow-shape checks. PR
  [#108](https://github.com/ryancinsight/apollo/pull/108) merged after its
  exact-head Rust/Python, benchmark, and book runs passed. The provider default
  is now `a0c3da9`; post-merge CI `32421484168`, mdBook `32421484508`, and
  Pages `32421483175` are terminal `success` at the merged default. The Atlas
  gitlink is advanced from `0c6ffb9` to `a0c3da9` without switching the dirty
  primary checkout.

- **Hyperion chromophore provenance:** the source audit disproved the
  unsupported ×4 premise: OMLC presents the retained hemoglobin values as
  molar extinction coefficients using 64,500 g/mol hemoglobin, so the provider
  uses those values directly. Commit `0213f947` adds the resolvable OMLC
  locator, independent source-knot oracle, accepted ownership ADR, and
  synchronized docs. Local formatting, ADR-index, mdBook-build, and strict-link
  checks pass; locked Cargo gates stop before compilation at the shared overlay
  lock-form mismatch. PR [#21](https://github.com/ryancinsight/hyperion/pull/21)
  merged at provider default `4df62f63`. Post-merge CI run
  `32415389400`, mdBook run `32415390244`, and Pages workflow
  `32415388456` are queued. The Atlas pointer remains at `e2dbc9b` until the
  merged-default gates are terminal and the deployed page is verified.

- **Hephaestus executable book gate:** the current Atlas session owned only
  `hephaestus/.github/workflows/book-pages.yml` and the included HostDevice
  and capabilities examples. The exact-head fix added the missing explicit
  crate declarations, removed two unused imports, and repinned Atlas staging
  to `20c9398`; local diff-check, mdBook build, strict links (14 files/13
  links), and workflow-shape checks passed. PR [#214](https://github.com/ryancinsight/hephaestus/pull/214)
  merged at provider `master` `7e09efa`. Post-merge provider jobs for WGPU,
  CUDA, ROCm, and Metal pass; the mdBook build and Pages deployment pass; and
  live Pages returns HTTP 200 with the expected Hephaestus title. The Atlas
  pointer advances to `7e09efa` without switching the dirty primary checkout.

- **Coeus executable book gate:** current Atlas session claims only
  `coeus/.github/workflows/book-pages.yml` on a clean `coeus-book-test` lane
  based on provider `origin/main`. The existing Tensor Basics and Matrix
  Multiplication examples are real included programs; acceptance is the shared
  `mdbook-test` caller for `coeus-ops`, exact hosted book evidence, and
  post-merge default verification. The detached primary checkout's provider
  implementation, lockfile, and PM dirt remain outside this item. Local lane
  commit `fc05cb75453bbb36d0f5b59f73b40dea0c432f44` passes diff-check, mdBook
  build, strict links (14 files/13 links), and workflow-shape checks. The
  locked package build is blocked before compilation by the shared Atlas
  overlay resolving primary-tree patches from the clean lane; hosted Linux is
  the package gate. Push and hosted collection remain sequenced behind the
  active merged-default runs.
  The failed exact-head book job was caused by missing explicit crate
  declarations in the included examples. The lane now adds those declarations
  and repins Atlas staging to `20c9398`. PR
  [#340](https://github.com/ryancinsight/Coeus/pull/340) merged after its
  provider-contract and book runs passed. The provider default is now
  `5108ed0082fc5c5ed02bc95c4bfa4ad9cdf8133b`; post-merge backend parity
  `32421487491` and mdBook `32421487793` are terminal `success` at the merged
  default. The Atlas gitlink is advanced from `5adc2d1` to `5108ed00` without
  switching the detached dirty primary checkout.

- **Live-tree conformance residual:** the local `python
  scripts/atlas-conformance.py check --worktree` sweep at audit revision
  `72cc6eb` plus live peer state exits 1 with 13 regressions and 27
  tightening classes against the committed baseline. The regressions are
  CFDrs oversized files and existence-only assertions; stale Consus classes
  from a checkout 49 commits behind origin; Moirai production `SeqCst`; and
  stale RITK implementation, type-suffixed, and commented-code classes from a
  checkout five commits behind origin. The run raises no baseline and does
  not discard peer or derived state.

- **Stack formatting sweep:** `scripts/atlas-fmt-check.py` passes for 23 of 24
  registered members. CFDrs reports 42 pre-existing unformatted files on the
  peer-owned `codex/cfdrs-tvd-test-integration` branch; no formatting rewrite
  was applied across that dirty claim. The corrected environment also passes
  toolchain preflight, version coherence, standalone lock-form (27 locks),
  registry metadata (253 manifests), board-ID lint, and strict book links.
  The full Atlas script suite passes `278` tests and `74` subtests in `8.77s`.
  The lane audit now ignores sanctioned `worktrees/.archive` metadata after
  pruning the stale Helios reference; only Kwavers's three peer-held trees
  remain reported.

- **Kwavers moving default:** fetched `origin/main` is now
  `0e786481cbcf3adad41ccb1f3efa6c94f6dc3f53`, after merged PR #436. Earlier
  hosted runs at `58b51ef3` cannot authorize the stale Atlas pointer
  `459f18ce8248ea91ace62a2f8f89a02b861a56fe`. Current PR #439 remains at
  exact head `2fa5f4d8a88d2ff16df866f15c5a1c4dd5d58b44` and is now `CLEAN` after
  a merge commit that preserves KW-CI-115 beside KW-GPU-200/201/202. No
  provider source or dirty worktree was overwritten.  The merged-default
  Pages run `32419107056`, CI run `32419106520`, architecture run
  `32419106681`, and legacy audit run `32419106514` are all terminal
  `success` at `0e786481`, and the live page returns HTTP 200. The Atlas
  pointer is advanced `459f18ce`→`0e786481` without switching or modifying
  the dirty primary checkout.
  Full exact-head/coherence audit now reports one remaining pointer drift:
  RITK `d4a978f`→`ad508525` (held: its merged-default Deploy mdBook gate
  `32404089897` is red on the E0460 hashless-artifact staging defect; the fix
  is RITK PR #204 at `9bc47d42` adopting Atlas `20c9398`, still open). Hermes
  PR #55 merged at `05441dd1`; its post-merge CI `32418079699` and Pages
  `32418078426` are terminal `success`, and the Atlas Hermes pointer is
  advanced `c5e4c2dc`→`05441dd1`.

- **RITK DTI frame contract:** PR [#198](https://github.com/ryancinsight/ritk/pull/198)
  merged at default `2d159850636a6539db61109533f399d31cc7c6f4`. Post-merge CI
  `32387951529`, Python CI `32387951635`, and Pages `32387952289` all pass.
  Live Pages `https://ryancinsight.github.io/ritk/` returns HTTP 200 with title
  `Introduction - atlas/RITK: Medical Image Processing and Registration`.
  PM closure PR [#199](https://github.com/ryancinsight/ritk/pull/199) merged at
  `ee76393fff7aaeae1a0c9f2712bcf8b8062c5303`; its docs-only closure records
  the same hosted evidence. Follow-up safety PR [#200](https://github.com/ryancinsight/ritk/pull/200)
  merged at `d4a978fce40f37b3668afa5d98783626aaf74cff`; post-merge Rust/Python
  CI `32395213485`/`32395213488` pass. Atlas advances its gitlink to the
  verified current default.
- **Tyche publication boundary:** PR
  [#30](https://github.com/ryancinsight/tyche/pull/30) merged at provider
  default `bfe6ab72915ff1d29357dd6895c39a11baecfbc0`. Post-merge CI
  `32386013998` and dynamic Pages `32386011656` both pass. Atlas gitlink
  advances to `bfe6ab72`. The facade, Consus-adapter, and Moirai-adapter
  packages are explicitly private; `tyche-core` remains the only publishable
  package. External registry/release configuration remains a separate residual.
- **Kwavers distributed queue:** PR
  [#427](https://github.com/ryancinsight/kwavers/pull/427) merged at
  `33a980acb4695500dd154111aa05a2947af4ad4d`. All 28 non-null CI gates pass;
  `WorkQueue::wait_all` waits for both queued and executing tasks; workers
  block on scheduler state notification. Atlas gitlink advances to the merged
  default.
- **Consus ADR-0045 P4 benchmark gate:** PR
  [#50](https://github.com/ryancinsight/consus/pull/50) merged at
  `e121b9d4258bab09144dfda68813aa9178090c0c`. All non-infra gates pass on
  rerun. Atlas gitlink advances to the merged default.
- **Helios Apollo lock sweep:** branch `codex/helios-apollo-lock-sweep` at
  `25f04b6` published as PR [#68](https://github.com/ryancinsight/helios/pull/68).
  Advances Apollo `d585e0f5`→`0c6ffb91`, Moirai `3d5d4c66`→`3b812865`, Themis
  `d0fcce7a`→`0484a333` in `Cargo.lock`; no Helios source or manifest change.
  Exact-head MSVC verification passes: format, locked metadata, full workspace
  check, warning-denied workspace Clippy, and Nextest run
  `4bfa9901-c55a-4cc1-a23f-b90d8f1542f8` with 262/262 tests and 9 skips.
  Hosted PR #68 required checks pass: Rust workspace, Python bindings, book
  build, and benchmark regression check. The `recurseml/analysis` context is
  report-only and remains an analysis error. PR #68 merged as
  `7ff72e37889594b6592e1f8b8b169834765f7851`; Atlas advances its gitlink to
  that merged default.
- **Tyche checklist reconciliation:** docs-only PRs #31 and #32 close stale
  TYCHE-006 and TYCHE-004 checklist entries; the merged default is
  `10410f2de1ce1529ecbff50fa740b23a1c8f77b9`. Pages run `32394886461` passes;
  current default CI `32394888136` passes at the same exact head. Atlas advances
  its gitlink to the merged default; no Tyche hosted verification residual
  remains for this item.
- **Requested-provider structural recheck:** at root commit `2fb4409`,
  `python scripts/atlas-provider-integration-audit.py --structural-only
  --provider-set requested-2026-08-14 --format json` reports `status: ok`,
  `provider_count: 20`, and `issues: []`. This validates registration and
  integration markers only; exact remote heads, checkout cleanliness, and
  hosted workflow terminality remain separate evidence classes.
- **Requested-provider exact-head recheck:** the bounded remote run at the
  same root revision exits non-zero with six pointer drifts: Hyperion, Hermes,
  RITK, Coeus, Apollo, and Kwavers. No Atlas gitlink advances are authorized
  from this run; each requires terminal hosted evidence at the fetched default
  before pointer reconciliation.

