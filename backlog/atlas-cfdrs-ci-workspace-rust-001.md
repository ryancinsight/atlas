<a id="atlas-cfdrs-ci-workspace-rust-001"></a>
## ATLAS-CFDRS-CI-WORKSPACE-RUST-001 — Add Rust workspace CI gate to CFDrs [patch] — in-progress

- Owner: current session (claimed 2026-08-10). Pairs with
  ATLAS-CFDRS-LINT-FLOOR-001 to make the floor mechanically enforced.
- Outcome: CFDrs `.github/workflows/ci.yml` carries a `rust-workspace` job
  that runs `cargo check --workspace --all-targets`, `cargo nextest run
  --workspace` (or `cargo test --workspace --no-fail-fast` fallback gated
  on `nextest` install via `taiki-e/install-action`), `cargo clippy
  --all-targets -- -D warnings`, `cargo fmt --all --check`, `cargo test
  --doc --workspace`. Mirrors `.github/workflows/ci.yml` patterns in
  `repos/apollo`, `repos/hephaestus`, `repos/helios`, and `repos/kwavers`.
- Scope: `.github/workflows/ci.yml` only; disjoint from peer's helios/ritk
  release-workflow consolidation `ci/migrate-release-workflow-to-shared-caller`.
- Acceptance: the new job runs in CI on the next PR; `cargo check --workspace
  --all-targets` and `cargo clippy` fail on a regression injected locally.
- Re-open trigger: the rust-workspace job is removed or its gate commands
  are weakened below the canonical Atlas floor.
- Dependency: ATLAS-CFDRS-LINT-FLOOR-001 must land first (or in the same
  PR) so `cargo clippy -- -D warnings` does not fail at the ~160 pre-existing
  baseline. Sequence behind it.

