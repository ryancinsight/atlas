# Atlas coordinator-tool template

`tools/_template/` is the single source of truth for the shared Cargo
configuration pasted across every coordinator-owned tool package under
`tools/`. It is a substrate, not a buildable crate: nothing compiles
here, and there is no `[package]`.

## Contents

- `template-Cargo.toml` — shared `[lints]` / `[profile.*]` /
  `[dependencies]` sections extracted from the three consumers below.
  The file carries only shared sections plus a header comment naming the
  consumers; never add a `[package]` body to it.
- `template-rust-toolchain.toml` — the pinned toolchain
  (`channel = "1.95.0"`, `components = ["clippy", "rustfmt"]`,
  `profile = "minimal"`) shared by every coordinator tool.
- `check-drift.sh` — bash scanner that byte-diffs each consumer's
  lint/profile sections against the template and fails on divergence.
  Run it locally before committing a Cargo.toml policy change and wire
  it into coordinator-tool CI per `engineering_gates`.

## Consumers (verified by `check-drift.sh`)

- `tools/checkout-path-dependencies/` — `atlas-provider-checkout`, exact
  gitlink checkout for sibling path dependencies; no serde deps.
- `tools/criterion-regression/` — `atlas-criterion-gate`, statistical
  Criterion regression gate; uses `serde` + `serde_json`.
- `tools/gitlink-coherence/` — `atlas-gitlink-coherence-gate`,
  gitlink coherence auditor for the meta-repo; uses `serde` +
  `serde_json`.

## SSOT policy — copy-as-new, then fill

A new coordinator tool is derived from this template by copy, never by
re-implementation of the lint/profile/toolchain choice from scratch:

1. `cp tools/_template/template-Cargo.toml tools/<new-tool>/Cargo.toml`
   then fill a real `[package]` body (name, `version = "0.1.0"`,
   `edition = "2024"`, `rust-version = "1.95"`, authors, description,
   `repository = "https://github.com/ryancinsight/atlas"`,
   `license = "MIT OR Apache-2.0"`, `publish = false`), a `[lib]` and/or
   `[[bin]]` declaration matching the crate shape, and any tool-specific
   `[dependencies]` (or drop the shared `[dependencies]` block if the
   tool needs no serde).
2. `cp tools/_template/template-rust-toolchain.toml
   tools/<new-tool>/rust-toolchain.toml` verbatim.
3. Add the new tool path to the consumer list in both template files and
   in this README's "Consumers" section above.
4. Add the new tool path to `tools/_template/check-drift.sh` consumer
   list so drift is gated from the first commit.

Do NOT add this directory as a workspace member. The meta-repo workspace
does not build `tools/_template/`; it builds each tool directly via its
own Cargo manifest.

## Lint-config derivation

The lint/profile policy is not invented here — it expresses the
binding directives of `agent.md`:

- `unsafe_code = "forbid"` and `missing_docs = "deny"` —
  `standards`: Unsafe discipline / Documentation tests.
- `clippy::pedantic` warn-baseline and `clippy::unwrap_used` denied —
  `engineering_gates`: Lint floor; `integrity`: error-handling restraint.
- `debug = "line-tables-only"` with `profile.dev.package."*".debug =
  false`, `profile.release.debug = false` and `strip = "symbols"` —
  `performance_engineering`: Debuginfo & profile discipline (dependency
  debuginfo dominates; keep release small; confine full debuginfo to a
  dedicated `[profile.profiling]`).
- `overflow-checks = true` in dev and test — `numerical_discipline`:
  Overflow and invariant checks.

A policy change edits this template first, then propagates the same
byte-diff to every consumer in one atomic change; `check-drift.sh`
guards against partial propagation. Backlog Refs:
`backlog.md#ATLAS-TOOLS-TEMPLATE-EXTRACT-1`.
