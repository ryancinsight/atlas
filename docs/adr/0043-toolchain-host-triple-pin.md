# ADR 0043 — Pin the toolchain host triple, not just the version

- Status: Proposed
- Date: 2026-08-14
- Driver: backlog ATLAS-TOOLCHAIN-TRIPLE-083

## Context

Every member repository pins `channel = "1.97.0"` in `rust-toolchain.toml`. That
is a **version** pin. `rustup` resolves it against whichever host toolchain is
default in the invoking shell, so an msvc shell and a gnu shell both satisfy the
pin — and both write into the one shared `CARGO_TARGET_DIR` that
`.cargo/config.toml` mandates for the whole stack.

Both are doing so now. Sampling recent `.rmeta` in `D:\atlas\target` finds
**96 tagged `pc-windows-msvc` against 140 tagged `pc-windows-gnu`**.

The failure this produces is `E0461` — "couldn't find crate X with expected
target triple" — reported against dependencies nobody touched (`der`,
`lazy_static`, `digest`, `pem`, `time`). It reads as dependency breakage, it
survives `cargo clean -p`, and it recurs as soon as the other host builds again.
It blocked a full-workspace clippy run during the Tier 2 sweep and cost real
diagnosis time before being traced to the cache rather than to any code.

The existing pin comment anticipates the neighbouring failure and stops one step
short: it explains that rustc rejects artifacts from a different compiler
*version* (E0514), which a version pin does prevent. Host-triple drift produces
E0461 instead, and no version pin can prevent it.

## Decision

Pin the full triple — `1.97.0-x86_64-pc-windows-msvc` — in every member's
`rust-toolchain.toml`, and add one at the meta-repo root, which currently has
none.

**msvc rather than gnu**, on three grounds:

1. It is what the CUDA toolkit expects on Windows. hephaestus builds real CUDA
   kernels and its conformance suite runs on an actual device; that path is the
   least substitutable thing in the stack.
2. It is the platform default, so it is what a fresh clone gets and what CI
   images provide without extra setup.
3. It is already the host of record for the meta-repo checkout.

## Consequences

The gnu-tagged half of the shared cache becomes unusable and should be deleted
outright rather than debugged — it is derived state, and a poisoned artifact
generation is disposable by definition.

**This costs hermes something real, and the cost is accepted rather than
overlooked.** hermes cross-checks its Linux code paths through a gnu toolchain,
and that specific capability does not survive verbatim. The replacement is
`rustup target add x86_64-unknown-linux-gnu` on the msvc host plus
`cargo check --target x86_64-unknown-linux-gnu`, which type-checks the
`cfg(unix)` branches — the actual goal. Linking a Linux binary still needs a
Linux host or container, but that was never available here either, and CI
already runs the real aarch64 and Linux jobs.

Migration is disruptive and should land on a quiet tree: every agent building
against the surviving generation will rebuild once. Doing it mid-sweep with
several agents in flight would strand each of them behind a full recompile.

## Alternatives rejected

- **Pin gnu instead.** Preserves hermes' current cross-check shape, but puts the
  CUDA path on the non-default toolchain for its platform and makes every fresh
  clone require setup before it can build the accelerator crates. The
  substitutable capability should bear the cost, not the unsubstitutable one.
- **Separate `CARGO_TARGET_DIR` per host triple.** Removes the collision without
  choosing a toolchain, but forks the build cache the stack deliberately shares,
  and the fork was measured at 58.9 GB when it last existed across members.
- **Leave it and document the symptom.** Rejected: the failure is
  indistinguishable from dependency breakage at the point of use, which is
  precisely why it consumed diagnosis time instead of being recognised.

## Verification

- Every `rust-toolchain.toml` in the stack names a full triple.
- A committed check fails when more than one host triple appears in the shared
  cache, so the condition cannot silently return.
- `cargo check --target x86_64-unknown-linux-gnu` succeeds in hermes from the
  msvc host, confirming the cross-check replacement before the gnu toolchain is
  retired.
