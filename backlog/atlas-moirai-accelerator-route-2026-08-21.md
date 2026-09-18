<a id="atlas-moirai-accelerator-route-2026-08-21"></a>
## ATLAS-MOIRAI-ACCELERATOR-ROUTE-2026-08-21 — Execute accelerator routes [major] [arch] — in-progress

The current Moirai route contract preserves an accelerator label only as
metadata: `moirai-transport/src/route.rs` maps accelerator routes to the local
address, and `DevicePayloadRegion` retains a host `Vec<u8>` without device
allocation or dispatch. Moirai's own gap analysis records that no GPU/TPU/NPU
backend consumes `SchedulerRoute::Accelerator`.

Scope: a clean, dependency-ordered Hephaestus/Themis integration edge that
resolves an `AcceleratorId`, dispatches one existing kernel family, and proves
CPU/WGPU value equivalence plus unavailable-device failure. Preserve the DAG:
Hephaestus consumes Moirai route/planner contracts; Moirai does not depend on
Hephaestus. Non-goals: a new accelerator runtime in Moirai, Melinoe stream
ownership, or broad scheduler redesign.

Current slice: replace Moirai transport's metadata-only accelerator address
resolution with a typed resolution that preserves the scheduler route and
accelerator identity while retaining a transport address for the later
Hephaestus edge. The package lane is `worktrees/moirai-package`, claimed for
`moirai-transport` route source/tests, benchmark source contracts, the public
facade re-export, and synchronized provider ADR/checklist artifacts. Dispatch
and CPU/WGPU execution remain a later Hephaestus/Themis slice after their bases
are refreshed; this slice does not claim device execution.

Current-slice outcome: Moirai commit `2355d42a39ff85fd3efb075075c9a916f52fc8be`
(`feat(moirai): Retain accelerator identity`) merged through PR
https://github.com/ryancinsight/Moirai/pull/147 with the expected-head guard at
default commit `ff56d60218b6f418d8db0e42c30da8185b90b6bd`. `RouteResolution`
keeps the full `SchedulerRoute`, transport `Address`, and accelerator
placement together; `RoutedArchivedSender::send_route` returns that
resolution. Exact local verification: 807/807 nextest tests passed with 6
skipped, clippy passed, format check passed, doctests passed, and rustdoc
passed. `cargo-semver-checks` is unavailable in the environment. Post-merge
Rust Workspace `32475134603` and Python Bindings `32475134582` are queued; no
submodule-pointer advance is claimed until those default checks are terminal.
The merged clean package lane and its local branch were removed after the PR
merge; the dirty detached primary checkout remains untouched.

Acceptance: accelerator identity survives route resolution; a present device
executes a real kernel and returns its value-semantic result; a missing device
returns a typed error; CPU/WGPU differential tests, route-identity tests, and
a bounded transfer/dispatch smoke pass. Claim only after refreshing the
provider defaults and reconciling the existing dirty/detached checkouts.

Owner: codex-primary. Claimed scope: `worktrees/moirai-package`,
`moirai-transport/src/route.rs`, `moirai-transport/src/route/tests.rs`,
`benchmarks/tests/benchmark_contracts/`, `moirai/src/lib.rs`, and the provider
ADR/checklist artifacts needed for this route-contract replacement.
Dependencies: current Moirai origin route contract; Hephaestus/Themis clean
bases remain a dependency for the subsequent dispatch slice. Risk/change class:
`[major] [arch]`. Last update: 2026-08-21.

**Outcome:** close the remaining cross-cutting correctness and evidence
deficits in the order below, so that a green gate means what it claims.

**Non-goals:** raising per-repository completeness scores as such; peer-owned
in-flight PR work; any capability expansion. Every item is evidence or
correctness, not new scope.

- **P0 delivery-blocking correctness** (independent, dispatchable now):
  1. Kwavers `swe/gpu/solver.rs:92` `propagate_waves_gpu` ignores its inputs,
     launches no kernel, and returns hardcoded-constant timings. Acceptance:
     either a real kernel dispatch with a CPU-differential oracle, or the
     production-named surface is withdrawn and the performance model renamed and
     moved out of the solver path. `[major]`
  2. CFDrs `cfd-validation/src/benchmarking/memory.rs:93` ungated
     `#[global_allocator]` in a library crate. Acceptance: allocator confined to
     a bench/bin target or `cfg`-gated; a consumer crate declaring its own
     allocator compiles. `[major]`
  3. Consus `consus-compression/src/codec/szip.rs:226` reserves from an
     unvalidated `u32` reachable via HDF5 filter id 4. Acceptance: length bounded
     against remaining input, `try_reserve`, typed error, plus a fuzz target over
     a malformed corpus. `[patch]`
  4. Consus `-C target-cpu=native` in committed `.cargo/config.toml`. Acceptance:
     removed; runtime ISA detection is the dispatch mechanism. `[patch]`

  Consus PR [#51](https://github.com/ryancinsight/consus/pull/51) is the
  existing owner for P0-3/P0-4 at exact head
  `2e24e6adda663db67b4bf1d4e1614e2c3b06fc19`; its repository matrix remains
  queued in run `32408174545`. Do not start a competing patch. The dead
  `.cargo/config.toml` `xtask` alias remains a separate cleanup residual after
  this PR.

- **P1 make the accelerator seam verifiable** (the audit's single largest
  evidence gap, four independent confirmations):
  5. Hephaestus host/CPU reference device implements 1 of 18 operation seams:
     `HostDecompositionOps` is the only arithmetic-family implementation.
     The shared conformance crate exports 20 clauses, while the host invokes
     only the decomposition and transfer assertions; no host conformance job
     is present in the current backend workflows. Coeus binds ten operation
     families, Athena binds dense/sparse vector families, and Kwavers binds
     `Fdtd3dOps`, so the seam gap is consumer-reachable. Acceptance: host impls
     for the seams consumers bind, and a shared conformance suite running
     GPU-vs-CPU differential cases with tolerances derived per
     `numerical_discipline`. `[minor]` — unblocks 6 and 7. The next bounded
     slice is `SUBSTRATE-003`: consolidate the nine decomposition differential
     helpers into one parameterized clause, reconcile the stale 14-versus-15
     method count, and add an exact host gate for the complete decomposition
     surface. Evidence: fetched Hephaestus `origin/master`
     `607ce3f`; current hosted results were not queried.
  6. Apollo, Coeus, and Kwavers GPU suites report green having executed nothing.
     Acceptance: an executed-case counter that fails the job at zero, plus a
     software adapter (`lavapipe`/WARP) or an explicit recorded skip that is
     visible in the gate result rather than silent.
  7. RITK `GpuFieldSmoother`/`CpuOrGpu` have no reachable GPU backend and carry
     unbacked speedup claims. Acceptance: wired to the Hephaestus seam, or the
     claims withdrawn pending it. `[minor]`

- **P2 retire vacuous gates** (cheap, high signal-to-noise):
  8. `mdbook test` coverage is uneven. Gaia's direct gate is vacuous because
     its book has zero Rust fences; Tyche, Proteus, Mnemosyne, Asclepius, and
     Iris execute real samples but retain 37 ignored Rust fences across the
     audited books. Acceptance: Gaia gains one value-semantic executable book
     example, and ignored snippets are converted to `text` or real executable
     examples where their chapter claims a workflow. The shared gate itself is
     not removed. Book chapters documenting non-existent APIs (Hephaestus,
     Mnemosyne, Helios) were corrected in this sweep; re-verify at merge.
  9. Themis `tests/topology/cpu.rs` orphaned target (14 tests never compiled);
     CFDrs 54 files / 10,543 LOC under root `examples|benches|tests` in no cargo
     target; Hermes ADR-005 generator that deletes 14 shipped kernels when run.
     Acceptance: each either wired into a target and green, or deleted.

- **P3 adjudicate the open decisions** (blocking, not mechanical):
  10. Leto/Athena solver ownership is decided: root ADR 0033 is Accepted and
      names Athena as the Krylov owner. The remaining work is deletion of the
      duplicate Leto implementation and caller migration, not a decision
      question. Acceptance: revise the affected ADRs with the dated decision,
      delete the loser, and migrate callers in one change. `[arch]`
  11. The root corpus has 48 ADRs: 15 `Proposed`, 30 `Accepted`, and 3
      `Rejected`; six Proposed records are Kwavers-related. Acceptance: each
      Proposed record is Accepted with an as-built rationale, Rejected, or
      deleted with its reason in the commit. `[patch]`
  12. Centralized ADR indexing is closed as a blocker: the root generator scans
      the Atlas root plus 23 provider ADR directories, and root conformance CI
      runs the check. Provider index dirt remains a separate peer-owned
      cleanup, not a missing generator. `[patch]`
  13. Eighteen registered-provider root manifests (19 including the RITK member
      manifest) declare `rust-version = "1.95"`; nine providers lack an
      explicit 1.95 workflow pin: Aequitas, Apollo, Harmonia, Helios, Hermes,
      Horae, Hyperion, Proteus, and RITK. Acceptance: add an MSRV job at the
      declared floor or correct the declared floor to the toolchain actually
      built. `[patch]`

**Dependencies:** 6 and 7 depend on 5. 1 through 4 are independent. 10 gates any
further Leto or Athena solver work.

**Risk:** items 1, 2, and 10 are `[major]`; 1 and 10 need an ADR before
implementation per `versioning`.

**Verification plan:** each item's acceptance oracle above, run through the
owning repository's committed gate. No stack-wide claim is made until the
per-repository gates run; this audit executed none.

**Meta-repository residual:** 16 of 25 submodule checkouts drift from their
committed gitlink; kwavers (5), consus (3), and helios (3) exceed the two-tree
lane bound; 8 empty `worktrees/kwavers-*` orphans remain. Filed here rather than
actioned, since every one of those trees holds peer state.

