<a id="atlas-cfdrs-lint-floor-001"></a>
## ATLAS-CFDRS-LINT-FLOOR-001 — Adopt canonical Atlas lint floor in CFDrs workspace [patch] — in-progress

outcome: CFDrs `Cargo.toml` `[workspace.lints]` matches the canonical Atlas floor (apollo `Cargo.toml` L88-L107, template SSOT) — pedantic warn plus the shared allow set, plus the library-hygiene deny tier (`unwrap_used`, `print_stderr`, `print_stdout`, `dbg_macro`). Pre-existing violations carry per-site `#[expect(lint, reason="ratchet cfd-<crate>-<count>")]` on a non-increasing baseline — mechanical transform only, no logic edits or refactors.

acceptance: `cargo clippy --all-targets --workspace -- -D warnings -W clippy::pedantic -W clippy::unwrap_used -W clippy::print_stderr -W clippy::print_stdout -W clippy::dbg_macro` rc=0; `cargo nextest run --workspace` rc=0; `cargo test --doc --workspace` rc=0; `cargo fmt --all --check` rc=0.

next: cfd-schematics missing_docs burn-down in progress (crate-wide distinct sites down to 435 as of commit `357debf3`, from an initial ~508+); cfd-math, cfd-core test/bench, and format debt remain toward full-workspace acceptance.

residual, deferred (not this slice): per-crate `#![deny(missing_docs)]` promotion, decided per-crate later.

re-open trigger: a new violation lands past the floor without an `#[expect]` ratchet, or the floor is relaxed in `Cargo.toml`.

Owner: current session (claimed 2026-08-06); branch `feat/cfdrs-lint-floor` off `origin/main 50fa243b`; disjoint from peer's `ATLAS-CFDRS-ATHENA-MIGRATION-001` chain.rs scope.
