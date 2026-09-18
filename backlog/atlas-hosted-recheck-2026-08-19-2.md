<a id="atlas-hosted-recheck-2026-08-19-2"></a>
## ATLAS-HOSTED-RECHECK-2026-08-19-2 — current provider state [patch] — in-progress

- **Moirai packaging and scheduler repair:** the provider branch
  `fix/moirai-package-manifest` is pushed at `5ccd72944ab31adf55e020931e969cbecb3a6f4e`
  and carries the standalone package cleanup, complete metadata/examples,
  allocation-free Chase-Lev generation claims, strong arbitration CAS, and
  Miri-valid SplitDeque provenance. Local evidence at that exact head is
  `cargo package --workspace --locked` for every member with no warnings,
  `cargo nextest run --workspace --all-features --locked` 801/801 with 6
  configured skips, warning-denied workspace Clippy, doctests 19 passed/1
  ignored, rustdoc, Loom 1/1 (exact final-head run
  `d6ff0225-9353-45ef-84cc-492d74eb39bf`), and deque-focused Miri 16/16.
  The Loom invocation ran outside the Atlas development overlay while using
  the shared `D:\atlas\target` cache because the overlay resolves Moirai
  patches to the main checkout rather than this bounded lane; the standalone
  package, workspace, and value gates remain locked evidence at the lane
  head. Full-crate Miri reaches the Themis Windows NUMA FFI test, which is
  unsupported by Miri; no deque failure remains. Existing PR #143 is open,
  mergeable, and hosted Rust and book checks pass; the Ubuntu wheel smoke test
  remains pending (`32328186717`), so Atlas retains its default gitlink until
  the hosted matrix completes and the PR merges.
- **Kwavers:** fetched `origin/main` is
  `64b982bdbfc2b7e36f11971947f5bdd8ed59d1f1`, the merge of PR #418 after
  ADR 112 was committed with its required Aequitas `Degree` surface. Atlas
  now points at this head in root commit `178e598`. The exact-head audit,
  overlay check, registry metadata scan (`252` manifests, `0` violations,
  `0` unverified), and standalone lock-form check (`27` locks plus the
  documented in-tree Melinoe fixture exemption) pass against this state.
- **Aequitas:** provider commit `809fc973f5df8c0bc0810161851466535efa74db`
  splits the derived SI units into six domain-named leaves and leaves
  `derived/mod.rs` as a manifest/re-export surface. The clean-provider
  conformance residual `manifest_implementation=1` is now `0`, with every
  other class unchanged at zero. Pinned-MSVC Clippy passes, Nextest passes
  `127/127`, doctests pass `17 + 9` compile-fail cases with one ignored, and
  rustdoc completes; the current Atlas pointer is advanced in this increment.
  Hosted CI `32325130976` and Pages `32325130273` pass at this exact head.
- **RITK:** PR #194 merged at `337f0dc5` after hosted CI
  `32323289141` and Python CI `32323289137` completed successfully; the
  report-only `recurseml/analysis` error does not block delivery. Fetched
  `origin/main` and the Atlas gitlink already resolve to `65bee2c2`, so no
  pointer mutation is required.
- **Standalone package gate:** running `cargo package --workspace --locked`
  outside the Atlas overlay packages the preceding RITK crates, then stops at
  `ritk-block-matching`: its `apollo-fft = ^0.27.0` requirement has no matching
  crates.io candidate (`0.26.0` and `0.25.0` are the available versions).
  This is a release-order blocker requiring Apollo 0.27 publication before the
  RITK workspace can claim complete crates.io package evidence; the dependency
  is not weakened and no release is performed without release authority.
- **Hyperion package gate:** the standalone locked package attempt fails while
  resolving crates.io Proteus: available `proteus 0.1.x` versions do not expose
  the `std` feature requested by Hyperion, although the current git provider
  does (`proteus/Cargo.toml:23-25`). This is registry publication/version
  coherence, not a reason to remove `proteus/std` from Hyperion; Hyperion and
  its downstream consumers remain release-blocked until Proteus is published
  with the matching feature surface.
- **Asclepius package gate:** standalone `cargo package --workspace --locked`
  passes for both `asclepius` and `asclepius-coeus`, including verification in
  the unpacked registry. Its dependency graph resolves published Apollo FFT
  `0.26.0`, providing a positive package result and independently confirming
  that RITK's Apollo `0.27.0` requirement is the registry-order blocker.
- **Horae package gate:** standalone `cargo package --workspace --locked`
  packages and verifies `horae v0.1.0` successfully outside the Atlas overlay.
  The package result is valid crates.io content evidence; publication remains
  governed by the provider's occupied-name/release-authority constraints.
- **Moirai package gate:** standalone `cargo package --workspace --locked`
  reaches manifest verification and stops at `benchmarks/Cargo.toml`: its
  path-only internal dependencies have no version requirements, which Cargo
  rejects for packaging (`dependency moirai-runtime does not specify a
  version`). The same manifest is present on fetched `origin/main`; this is a
  provider packaging defect, not a reason to weaken the runtime dependency
  graph. The benchmark README path and out-of-package example paths also emit
  packaging warnings and require the same provider-owned cleanup.
- **Horae:** the exact `--all-features` native gate passes `23/23`, and its CI
  and Pages callers enable the book test. The local Windows `mdbook test`
  invocation reaches rustdoc but fails with a GNU/MSVC artifact mismatch
  (`E0461`); no chapter-content failure is inferred.
- **Helios:** draft PyPI PR #67 remains open at `f31f2619`; its Rust, Python,
  benchmark, and book-build checks pass while Pages deployment is skipped. The
  checkout retains peer-owned manifest dirt.
- **Apollo:** PR #107 remains open with Rust and benchmark failures. The
  benchmark audit localizes the regression to the four const twiddle-cache
  initializers in `crates/apollo-fft/src/application/execution/kernel/mixed_radix/caches/twiddle.rs:26-29`.
- **Root worktree:** exact provider/integrator heads, overlay, registry
  metadata (`252` manifests, `0` violations), and 27 standalone lock forms
  pass locally. The intentional dirty-tree conformance snapshot reports
  `609` oversized files, `674` implementation-bearing manifests, `1,196`
  production unwraps, `518` allow sites, `803` existence-only assertions, and
  `4` excess-worktree sites; these remain peer-owned ratchet debt rather than
  reproducible clean-tree gate results.

