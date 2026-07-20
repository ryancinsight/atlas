# Changelog

## Unreleased

### Changed

- Clarify the parent-gitlink revision contract and safe submodule inspection in
  the Atlas README. Correct the roadmap so Harmonia composes Horae and Athena
  without depending on material-law ownership. Advance Athena to `96fb26d`
  with external observer construction and package documentation, and Horae to
  documentation merge `92af1a2`.

- Promote Horae and Athena as public Atlas packages. Horae owns typed
  time-integration policy over Aequitas. Athena owns shared PCG and restarted
  right-preconditioned GMRES recurrences over Leto CPU and Hephaestus WGPU,
  and Leto no longer exports duplicate iterative-solver recurrences. Record
  both public gitlinks, advance Leto to PR #54 merge `1752058`, and make
  `.gitmodules` the build-driver package-set SSOT.

- Advance Kwavers to PR #295 merge `49c116f`, replacing its bubble-energy
  `uom` ownership with Aequitas quantities and correcting the heat-capacity
  dimensional law. Pin CFDrs at PR #298 merge `7c37f7f`, where typed spacing
  reaches Hephaestus. Replace the parent graph's local-only `156531e` and
  `a34a01d` gitlinks with fetched merged defaults after their consumer gates
  pass.

- Advance Hephaestus to PM closeout PR #52 merge `cdfcd0c`; runtime code and the
  verified Eunomia 0.6 provider closure remain unchanged.

- Advance Hermes to PR #11 merge `6f9b81f`, locking Eunomia 0.6 after its
  raw-half retirement. Advance Leto to the exact PR #48 merge object
  `bb03244f05a9c43c318d103225c3ccad07e9fad9`, preserving the merged
  Box-Muller paired-normal performance increment.

- Advance Eunomia to PR #48 merge `df77dfd`, removing its production
  `half` dependency and foreign raw-half numeric/cast surface. Advance
  Hephaestus to PR #51 merge `594d57a`, whose reproducibility lock resolves
  Eunomia 0.6.0, Hermes 0.4.0, and Leto 0.39.0 with 312/312 provider tests.

- Tombstone superseded CR-2, RITK, and Kwavers migration queues after their
  recorded closures; refresh the provider/consumer stack table to the 16
  fetched remote-default gitlinks.

- Advance Eunomia to `c196db5`, Hermes to `c9bbdf8`, and Leto to `7afcbd0`.
  Eunomia owns exact reduced-format bit and float-element contracts; Hermes and
  Leto remove raw `half` public ownership in favor of Eunomia `F16`/`Bf16`.
  Reconcile the cumulative Coeus pointer at `5ee07a2` and RITK pointer at
  projection-hardening PR #44 merge `688eb8e`; peer working state remains
  outside the parent commit.

- Advance Helios to PR #7 merge `79b09e9`; its reproducibility lock now
  resolves Apollo 0.25.0, Eunomia 0.4.0, Leto 0.38.2, and Hephaestus 0.17.0
  and contains no `num-complex` package.

- Record Coeus PR #212 merge `bb97cc6` as the NN benchmark-provider closure.
  Burn is absent while all 211 operation groups and 424 native
  Sequential/Moirai measurements remain. The locked graph resolves Eunomia
  0.4.0, Leto 0.38.2, and Hephaestus 0.17.0.

- Record Eunomia PR #39 merge `49dc115` as the canonical sub-byte conversion
  cutover, then advance Leto PR #44 `f0b4d8e` and Hephaestus PR #50 `ed7d76e`
  after their reproducibility locks and full consumer gates resolve Eunomia
  0.4.0. The Atlas graph advances only these three merged defaults.

- Record Coeus PR #211 merge `4459d09` as the tensor legacy-benchmark removal;
  the consumer commits `Cargo.lock`, aligns Hephaestus `0.16.1`, and retains
  only Coeus Sequential/Moirai and Leto benchmark paths. Locked package
  verification, 56/56 Nextest, warning-denied Clippy, doctests, rustdoc,
  metadata, and residue scan pass.

- Record Apollo PR #53 merge `a31b8f8` as the Hephaestus lock convergence;
  `hephaestus-core`, `hephaestus-wgpu`, and `hephaestus-cuda` now select
  provider `cec0e33` after its Leto-owned legacy-math cleanup. Locked compile,
  402/402 Nextest, warning-denied Clippy, doctests, rustdoc, provider audit,
  hosted Rust/Python, and CodeRabbit checks pass.

- Record Hephaestus PR #47 merge `cec0e33` as the Leto-only CPU reference
  cleanup. Its WGPU/CUDA tests and comparative benches no longer depend on
  legacy array or linear-algebra crates; provider execution remains owned by
  Hephaestus and the Python `numpy` bridge remains an FFI-only edge.

- Record Apollo PR #52 merge `7303423` as the Leto merge-pin correction; both
  Leto packages now select Atlas default `3ac0d203` rather than parent
  `6a0e297`. Hosted Rust/Python/CodeRabbit checks pass; the external analyzer
  remains non-required.

- Advance RITK to PR #41 merge `a41e03b9`, aligning its lockfile and composite
  provider checkout with Apollo 0.25. All 22 repository and review checks pass,
  including cross-platform Nextest, Python 3.9–3.13, wheel, lint, dependency
  alignment, and migration audit.

- Record Apollo PR #51 merge `6dcb97c` as the provider-lock refresh; the
  consumer now resolves Hephaestus `93bc38e`, Eunomia `a2e4f390`, Leto
  `6a0e297`, and Moirai `8a51b2a7` from default sources. Locked 402/402
  Nextest and hosted Python/Rust/CodeRabbit checks pass.

- Advance CFDrs, Eunomia, Helios, Leto, and RITK to their merged
  default-branch commits while preserving active Apollo, Kwavers, and RITK
  feature work. The parent graph records only fetched remote defaults; Leto
  owns the remaining sparse-direct capability item needed to remove CFDrs
  `rsparse` without replacing its independent direct tier with GMRES.

- Record Hephaestus PR #46 merge `93bc38e` as the scan-limit theorem closure;
  provider ADR 0009 proves shared storage is `W` partials independent of line
  length, and the existing `L=513`, `W=256` WGPU/CUDA contracts cover the
  long-line path. KS-5b remains a measured performance follow-up.

- Record Apollo PR #50 merge `c874281` as the canonical Winograd trait
  ownership cutover; the obsolete internal `mixed_radix` re-export is deleted,
  all callers use `components::winograd`, and local 402/402 plus hosted Python,
  Rust, and CodeRabbit checks pass. The external `recurseml/analysis` error is
  non-required.

- Record Apollo PR #49 merge `e2f905a` as the obsolete execution-policy-wrapper
  removal; `apollo-fft` now uses Moirai's canonical threshold policy and keeps
  the provider boundary on Hephaestus. Local 393/393 package evidence and the
  hosted Python and Rust workspace lanes pass; the external
  `recurseml/analysis` failure is non-required.

- Advance the Hephaestus provider gitlink to PR #45 merge `3b68228`; memoized
  CUDA driver initialization and serialized context creation close the
  Windows concurrent-acquisition abort, with the full 109/109 CUDA suite
  passing while transfers and kernels remain concurrent.

- Advance the Hephaestus provider gitlink to PR #44 merge `d0eafc8` for the
  shared-memory tiled axis-scan kernels; the provider ADR and long-line
  WGPU/CUDA contracts remain the theorem and behavioral SSOT.

- Record Kwavers PR #294 merge `9eabc4e2` as the clean Hephaestus
  backend-kernel ownership increment; obsolete buffer and pipeline managers
  are deleted, the MVDR wall-clock assertion lives in Criterion, and the
  parent pin advances from `7c7d60f`.
- Record Kwavers `11e577c` as the clean Leto medium-accessor and abdominal
  geometry-contract head; Architecture Validation passes, while CI/CD coverage
  is blocked only by an external Codecov HTTP 429 upload response; PR #293
  retains the generated report gate and makes that transport non-blocking.
- Mark the Apollo `eb46e77` parent pin complete after Atlas PR #18; the
  verified Apollo `main` head is now `0b5d11c` after PR #48.
- Merge Apollo PR #46 and PM closure PR #47 at `eb46e77`; partition GPU
  dispatch verification into a deep private leaf and retain Hephaestus/Leto
  provider ownership.
- Advance the Atlas Apollo gitlink in PR #18 at `56ad179`.
- Keep Kwavers PR #292 at `54575460c` pending hosted coverage diagnosis and
  the remaining matrix; no dirty parent gitlink is advanced.
- Advance the RITK gitlink to its verified Apollo 0.24 source-checkout repair
  on `main`.
- Refresh Apollo, Hephaestus, Kwavers, Leto, and RITK gitlinks to the current
  provider graph; add ADR 0020 with the exact provider-graph closure theorem.
- Align public Atlas submodule pins with their fetched default branches.
- Advance Apollo, Helios, and RITK gitlinks to their merged default-branch
  commits after their provider and cross-platform CI closure.
- Advance the Apollo submodule pin after its concurrent provider-boundary merge.
- Advance the CFDrs and Hephaestus gitlinks after their typed GPU boundary
  closure.
- Advance the CFDrs gitlink after executable one- and two-dimensional
  validation examples replaced static reports on `main`.
- Advance the RITK gitlink after its merged lock metadata repair aligned the
  Hephaestus patch entries with the current provider graph.
- Register Kwavers and Helios in the Atlas public submodule roster.
- Reject bare `cargo test` in cross-stack drivers while retaining doctests.
