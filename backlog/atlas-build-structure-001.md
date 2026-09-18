<a id="atlas-build-structure-001"></a>
## ATLAS-BUILD-STRUCTURE-001 — Consolidate leaf binaries; compiler-last dev profiles [patch] — in-progress

- Owner: Codex `/root`; last-update: 2026-07-23; completed vertical slice:
  `repos/coeus/coeus-ops/tests/**` only. Peer-owned member profiles and other
  repository test trees remain out of scope.
- Aequitas vertical slice: provider PR #35 on source `5428584` splits the
  private derived-unit and dimension-law test leaves, retaining all 38 law
  tests. It is a provider branch awaiting hosted gates; Atlas does not advance
  the Aequitas gitlink until the PR merges.
- Claim: consolidate the 36 flat `coeus-ops` Rust integration-test binaries
  into one hierarchical `tests/ops.rs` harness with `tests/ops/*.rs` modules,
  preserving all 87 test functions and their value-semantic assertions. The
  target-count reduction and test-count parity are the acceptance oracle.

- Policy: AGENTS.md performance_engineering "Debug-tree and compile-time structure" + "Compiler-last optimization order". Monomorphization stays the design default — an instantiation codegens identically to its hand-written equivalent; the debug-tree multiplier is leaf-binary count and duplicate paths, never genericity.
- Evidence 2026-07-22: ~950 leaf binaries stack-wide, each a full link with own incremental cache and PDB — tests/examples per repo: CFDrs 118/66, coeus 110/2, kwavers 94/62, consus 55/0, ritk 28/7, hermes 20/4, moirai 15/22, melinoe 15/1, others <=11. Dev-profile audit: helios declares wildcard `[profile.dev.package."*"] opt-level = 3` (the pattern removed from kwavers in PR #307); kwavers `opt-level = 1` with documented 5-10x PSTD justification is the sanctioned named-and-measured form. The shared incremental tree reached 27,085 session directories and approximately 489 GiB in five days, making leaf-target consolidation and CI `CARGO_INCREMENTAL=0` the next measured size levers.
- Scope: (1) consolidate each repo's tests/*.rs into one-or-few area harness binaries (`tests/<area>/main.rs` with modules) — nextest still isolates per test function in its own process, so coverage and isolation are unchanged while link count, incremental caches, and debug artifacts drop by the file count; worst offenders first (CFDrs, coeus, kwavers, consus, ritk, hermes); (2) merge near-duplicate examples per consolidation_discipline; (3) replace wildcard dev dependency opt raises with named, measured, per-package exceptions (helios first, peer-held — coordinate via board); (4) record per-repo binary-target count and debug-tree size before/after as the acceptance measurement.
- Acceptance: binary-target census reduced and recorded per repo; debug-tree size delta measured against the shared cache; test function count unchanged (no coverage loss); no wildcard dev opt-level overrides remain without a named measured justification.
- Completed vertical slice: Coeus `coeus-ops/tests` moved from 36 flat
  integration targets to one `ops` target with ten operation-family
  directories. The harness exposes 87 integration tests and the exact
  package Nextest run passes 196/196; whole-workspace debug-tree measurement
  remains a later bounded slice.
- Evidence: warning-denied Clippy, package check, format, and diff checks pass
  on Coeus commit `f67789c4`; the 87 harness tests are unchanged by source
  count and all 196 package tests pass. This item is closed for the bounded
  Coeus slice; the broader stack-wide debug-tree delta remains open work.
- Coeus-NN slice complete at provider commit `95bb9090`: the existing
  `nn_tests.rs` harness and its already hierarchical `tests/nn/` modules stay
  intact while the 33 other direct test binaries move behind one `nn_ops`
  harness, preserving the 268 total package tests. The 34 direct test targets
  reduced to 2 (`nn_ops` and `nn_tests`); the exact package run passes
  268/268 with 0 skipped. Whole-workspace debug-tree measurement remains open.
- Coeus-autograd slice complete at provider commit `f8f6d665`: the existing
  `autograd_tests.rs` harness and `tests/autograd/` module tree remain intact
  while the three other direct targets move behind one `autograd_ops` harness.
  The four integration targets reduce to two; the exact package run passes
  94/94 with 0 skipped. Whole-workspace debug-tree measurement remains open.
- Coeus-tensor slice complete at provider commit `49bb5858`: the 13 flat
  integration targets move under six operation-family directories behind one
  `tensor_ops` harness. Locked metadata reports one integration target; the
  source census remains 53 annotated integration tests, and the exact package
  Nextest run passes 58/58 with 0 skipped, including five library unit tests.
  Production tensor code and all leaf test bodies remain unchanged. Whole-
  workspace debug-tree measurement remains open.
- Coeus-sparse slice complete at provider commit `81cb68a6`: the three flat
  integration targets move under conversion, differential, and invariant
  directories behind one `sparse_ops` harness. Locked metadata reports one
  integration target; the exact package Nextest run passes 19/19 with 0
  skipped in 0.713 seconds. Production sparse code and all leaf test bodies
  remain unchanged. Whole-workspace debug-tree measurement remains open.
- Coeus-core slice complete at provider commit `88dfd38f`: the four flat
  integration targets move under storage, dependency-policy, and scalar
  directories behind one `core_ops` harness. Locked metadata reports one
  integration target; the exact package Nextest run passes 21/21 with 0
  skipped, comprising 14 integration cases and seven unchanged library unit
  tests. Production core code and all leaf test bodies remain unchanged.
  Whole-workspace debug-tree measurement remains open.
- Coeus-CUDA slice complete at provider commit `573ad35e`: the three flat
  feature-gated integration targets move under device and fallback directories
  behind one `cuda_ops` harness, retaining the existing nested `tests/cuda/`
  tree through an explicit path. Default Nextest passes 3/3 with 0 skipped;
  all-features check and Clippy pass. All-features executable coverage remains
  host-blocked because the GNU linker cannot find
  `/usr/local/cuda-11.3/lib64/libcuda`. Whole-workspace debug-tree measurement
  remains open.
- Coeus-Python slice complete at provider commit `8851c5f5`: the six flat Rust
  integration targets move under activation, distributed, NN, operation,
  optimizer, and autodiff directories behind one `binding_ops` harness. The
  shared `tests/common` lock module is owned once at the harness root. Exact
  all-features Nextest passes 75/75 with 0 skipped; production PyO3, Python
  parity scripts, and generated artifacts remain unchanged. Whole-workspace
  debug-tree measurement remains open.
- Coeus-WGPU slice complete at provider commit `c507683e`: the two flat
  integration targets now share one hierarchical `wgpu_ops` harness, with
  fused operations under `fusion.rs` and the existing WGPU operation tree under
  `backend/wgpu/`. Exact package Nextest passes 85/85 with 0 skipped; the moved
  source files are content-identical renames and production GPU code is
  unchanged. Whole-workspace debug-tree measurement remains open.
- Coeus-WGPU parity split complete at provider commit `149aadb5`: the 808-line
  multi-family leaf is now a shared oracle manifest plus seven operation-family
  modules. The pre/post source-name census remains 47 unique parity identifiers;
  exact package Nextest passes 85/85 with 0 skipped. Every new leaf is below
  500 lines; production kernels and fixtures are unchanged. Whole-workspace
  debug-tree measurement remains open.
- Coeus-Leto slice complete at provider commit `8d3b9082`: the two flat
  integration targets now share one hierarchical `leto_ops` harness with
  contract and sparse-dispatch operation families. Locked metadata reports one
  integration target; exact package Nextest passes 28/28 with 0 skipped in
  1.064 seconds. The live census is 26 contract tests plus 2 sparse-dispatch
  tests, correcting the prior 26-test tracking claim. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-autograd slice complete at provider commit `24a52be5`: the established
  `tests/autograd/` module tree and standalone operation families now share one
  hierarchical `autograd_ops` harness; the redundant `autograd_tests.rs`
  manifest is removed. Locked metadata reports one integration target instead
  of two; exact package Nextest passes 94/94 with 0 skipped in 1.535 seconds.
  Package check, warning-denied Clippy, format, and diff checks pass. Whole-
  workspace debug-tree measurement remains open.
- Coeus-NN slice complete at provider commit `5c416e12`: the established
  `tests/nn/` module tree and operation-family modules now share one
  hierarchical `nn_ops` harness; the redundant `nn_tests.rs` manifest is
  removed. Locked metadata reports one integration target; exact package
  Nextest passes 268/268 with 0 skipped in 4.463 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-NN tensor parity split complete at provider commit `ee5be32f`: the
  1,317-line multi-family parity leaf is now a shared assertion manifest plus
  attention, convolution, embedding, linear/normalization, losses, and
  regularization operation-family modules. The pre/post source-name census
  remains 11 unique parity test functions; exact package Nextest passes 268/268
  with 0 skipped in 2.816 seconds. The largest new leaf is `attention.rs` at
  664 lines; the other five leaves are below 250 lines. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-CUDA parity split complete at provider commit `abe9211d`: the live
  1,672-line multi-family parity leaf is now a shared oracle manifest plus
  seven operation-family modules. The pre/post source-name census remains 29
  unique parity test functions; every new leaf is below 500 lines, with
  `convolution.rs` the largest at 365 lines. Default package Nextest passes
  3/3 with 0 skipped; default and `--features cuda` package checks and
  warning-denied Clippy pass. Feature-enabled Nextest cannot link because
  `x86_64-w64-mingw32-gcc` cannot find `-lcuda` while searching
  `/usr/local/cuda-11.3/lib64/`; no live CUDA parity execution is claimed.
  Whole-workspace debug-tree measurement remains open.
- Coeus-Python operation binding split complete at provider commit `0d8784c1`:
  the live 3,160-line `binding_tests_ops.rs` leaf is now fourteen
  operation-family leaves with nested NN functional and module directories.
  The pre/post source census remains 61 unique test functions and all 61
  extracted Rust function bodies compare equal. The largest test-family leaf is
  `reductions.rs` at 391 lines; every leaf is below 400 lines. Exact package
  Nextest passes 75/75 with 0 skipped in 8.079 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Production PyO3,
  Python parity scripts, and generated artifacts remain unchanged. Whole-
  workspace debug-tree measurement remains open.
- Coeus-dist distributed-contract split complete at provider commit `c7838d90`:
  the live 1,262-line `dist_tests.rs` leaf is now one `dist_ops` manifest with
  local and TCP transport subtrees, separated into collective, reduction,
  invalid-input, and mesh-boundary families. The pre/post source census remains
  64 unique test functions, all 64 `#[test]` attributes remain present, and
  all 64 extracted Rust function bodies compare equal. The largest new leaf is
  `distributed/tcp/errors/collective.rs` at 464 lines; every leaf is below 500
  lines. Exact package Nextest passes 64/64 with 0 skipped in 0.444 seconds,
  with no slow tests. Package check, warning-denied Clippy, format, and diff
  checks pass. Whole-workspace debug-tree measurement remains open.
- Coeus-NN loss-contract split complete at provider commit `37bf8d9b`:
  the live 902-line `nn_loss_tests.rs` leaf is now a nested manifest with
  binary, classification, distance, and distribution operation families. The
  pre/post source census remains 24 unique test functions and all 24 extracted
  Rust function bodies compare equal. The largest new leaf is `distance.rs` at
  315 lines; every new leaf is below 500 lines. Exact package Nextest passes
  268/268 with 0 skipped in 2.270 seconds. Package check, warning-denied
  Clippy, format, and diff checks pass. Production NN code, fixtures, and
  tolerances remain unchanged; whole-workspace debug-tree measurement remains
  open.
- Coeus-optim contract-family split complete at provider commit `b27d492f`:
  the live 676-line `optim_tests.rs` leaf is now one `optim_ops` manifest with
  optimizer, scheduler, convergence, and gradient-clipping family modules.
  The pre/post source census remains 20 unique test functions and all 20
  extracted Rust function bodies compare equal. Locked metadata reports one
  `optim_ops` integration target. The largest new leaf is `convergence.rs` at
  239 lines; every new leaf is below 250. Exact package Nextest passes 20/20
  with 0 skipped in 0.188 seconds. Package check, warning-denied Clippy,
  format, and diff checks pass. Production optimizer code and all test oracles
  remain unchanged; whole-workspace debug-tree measurement remains open.
- Coeus-NN extended activation split complete at provider commit `d800be8c`:
  the live 648-line `act_extended_tests.rs` leaf is now one `act_extended`
  manifest with piecewise, parameterized, module-smoke, and smooth families.
  The pre/post source census remains 17 unique test functions and all 17
  extracted Rust test function bodies compare equal. The largest new leaf is
  `piecewise.rs` at 354 lines; every new leaf is below 360. Exact package
  Nextest passes 268/268 with 0 skipped in 3.155 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Production NN code,
  fixtures, formulas, and tolerances remain unchanged; whole-workspace
  debug-tree measurement remains open.
- Coeus-Leto contract-family split complete at provider commit `97d94566`:
  the live 505-line `leto_ops/contract.rs` leaf is now a manifest with
  arithmetic, reductions, matmul, layout, and accumulation families under
  `coeus-leto/tests/leto_ops/contract/`. The pre/post source census remains
  26 unique contract tests and all 26 extracted Rust test function bodies
  compare equal. The largest new leaf is `layout.rs` at 197 lines; every new
  leaf is below 200 lines. Locked metadata reports one `leto_ops` integration
  target. Exact package Nextest passes 28/28 with 0 skipped in 0.325 seconds.
  Package check, warning-denied Clippy, format, and diff checks pass.
  Production Leto dispatch code and test oracles remain unchanged; whole-
  workspace debug-tree measurement remains open.
- Next claimed slice: run a fresh structural audit of the remaining Coeus test
  tree and take the next real family-boundary increment, if a live leaf exceeds
  the hierarchy trigger without violating test cohesion.

