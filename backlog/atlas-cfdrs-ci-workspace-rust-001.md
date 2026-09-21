<a id="atlas-cfdrs-ci-workspace-rust-001"></a>
## ATLAS-CFDRS-CI-WORKSPACE-RUST-001 — Add Rust workspace CI gate to CFDrs [patch] — in-progress
outcome: CFDrs `.github/workflows/ci.yml` gains a `rust-workspace` job running `cargo check --workspace --all-targets`, `cargo nextest run --workspace` (or `cargo test --workspace --no-fail-fast` fallback gated on `nextest` install via `taiki-e/install-action`), `cargo clippy --all-targets -- -D warnings`, `cargo fmt --all --check`, `cargo test --doc --workspace` — mirroring `repos/{apollo,hephaestus,helios,kwavers}/.github/workflows/ci.yml`.
acceptance: the job runs on the next PR; `cargo check --workspace --all-targets` and `cargo clippy` fail on a locally injected regression.
dependency: ATLAS-CFDRS-LINT-FLOOR-001 must land first (or in the same PR) so `clippy -- -D warnings` does not fail at the pre-existing ~160 baseline. Sequence behind it.
re-open trigger: the job is removed or its gate commands weaken below the canonical Atlas floor.
Owner: current session (claimed 2026-08-10); scope disjoint from peer's helios/ritk release-workflow consolidation.
