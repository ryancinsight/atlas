<a id="atlas-coeus-reduction-oracle-005"></a>
## ATLAS-COEUS-REDUCTION-ORACLE-005 — Independent Metal reduction and scan expectations [patch] — blocked
- outcome: check all five axis reductions and four inclusive scans against independent mathematical values; run the Leto expectation check without acquiring Metal.
- priority: verification
- needs: none
- scope: `repos/coeus/crates/coeus-metal/tests/reduction.rs`, its crate README, and the Metal test filter in `repos/coeus/.github/workflows/backend-parity.yml`.
- basis: Coeus main `b03ce737b740c04416d916a91f46f23f2b0d626c`; its bounded product/mean routing fix is incorporated while preserving existing local commits.
- acceptance: Leto and Metal independently match exact axis-1 values for the `[2, 3]` fixture; corrupting product, mean, or scan results fails their assertions; focused configured gates pass.
- blocker: unchanged `coeus-ops/src/reduction/variance.rs:63,140` fails with E0277 because `var_mean` and `var_mean_axis` lack the `RealScalar` bound required by sum dispatch. This occurs in the entry baseline and blocks Metal check, Clippy, nextest, and doctests.
- re-open trigger: the variance bound closure compiles against the committed standalone lock, then run the edited Metal tests on macOS with `HEPHAESTUS_METAL_REQUIRE_DEVICE=1`.
- evidence: format and diff checks pass; four existing Leto tests pass (nextest `e2b6b9b4-4837-48e3-9568-2586d8a37348`); the new CPU test body runs verbatim in a temporary export and passes (nextest `2481532b-4a1b-4e1d-bb0d-6d6d7145f042`). Rust 1.97.0, nextest 0.9.143, Windows; Metal execution and mutation acceptance remain unverified.
- next step: repair the variance bound closure, rerun the focused configured Metal gates, and integrate the preserved oracle diff only after the gates pass.
- links: [ATLAS-COEUS-NLLS-004](../backlog.md#atlas-coeus-nlls-004).
