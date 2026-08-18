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

**Revision 2026-08-15 — the mechanism is narrower and more fixable than "two
shells".** Measured on this host, a *single* environment produces both triples:

```
RUSTC   = …\.rustup\toolchains\1.97.0-x86_64-pc-windows-msvc\bin\rustc.exe
RUSTDOC = …\.rustup\toolchains\1.97.0-x86_64-pc-windows-msvc\bin\rustdoc.exe
rustup default host                      = x86_64-pc-windows-gnu
rust-toolchain.toml resolves to          = 1.97.0-x86_64-pc-windows-gnu
```

Cargo comes from the **gnu** toolchain but is told by `RUSTC` to invoke the
**msvc** compiler, so it emits msvc rlibs; anything that spawns `rustc`/`rustdoc`
through rustup or PATH instead — `mdbook test`, and clippy, which has its own
fingerprint and re-drives dependency builds — gets gnu. Both write into the one
shared cache. That is exactly the environment-override case
`engineering_gates`'s toolchain-coherence rule names: "an environment override
(`RUSTC`/`RUSTDOC` pointing at a shim, a cargo and rustc from different
distributions, a rustup default differing from the pin) silently substitutes
another compiler."

It reproduced twice on 2026-08-15 as `E0461` in `mnemosyne_core`, `backtrace`,
`serde`, `futures-util` and others, and `RUSTUP_TOOLCHAIN=1.97.0-x86_64-pc-windows-msvc`
cleared it in both cases. Per-package `cargo clean` does **not** converge: one
pass removed 8228 files / 1.8 GiB and merely exposed the next layer.

This matters for the decision below, because it means the triple pin is
necessary but **not sufficient**. Whatever triple the stack chooses, the
`RUSTC`/`RUSTDOC` overrides and the rustup default host must agree with it, or
the same split recurs under a pin that looks correct. The likely origin of the
override is the documented Windows-host trick for type-checking `cfg(unix)`
code by pointing `RUSTC` at a specific toolchain proxy — a useful technique
that must be scoped to the one command that needs it, never exported into the
environment every build inherits.

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

**A different fix is in flight, uncommitted, 2026-08-18.** A peer has added
`[build] target = "x86_64-pc-windows-gnu"` to the shared `.cargo/config.toml`
(working tree only; not in HEAD). That routes every build into
`target/<triple>/debug` instead of the plain host directory, so the two host
toolchains segregate their artifacts and **cannot contaminate each other even
if both run** — which addresses the same failure from the opposite direction to
this ADR. It is arguably the better fix: it does not force the stack to give up
either toolchain, and it removes the coupling between "which rustup default an
agent happens to have" and "whose artifacts get clobbered".

Two consequences to settle before this ADR is applied, because the two
approaches interact badly if landed blind:

1. With an explicit `[build] target`, the correct local invocation becomes the
   toolchain **matching that triple** — running msvc against a gnu-targeted
   config now fails with `E0463 … the x86_64-pc-windows-gnu target may not be
   installed`, which is a *new* confusing symptom, not the old one. Verified
   directly: mnemosyne's suite fails that way under msvc and passes 290/290
   under `RUSTUP_TOOLCHAIN=1.97.0-x86_64-pc-windows-gnu`.
2. `RUSTC`/`RUSTDOC` are exported by the shell profile and **come back in every
   new process**, so clearing them in one command does not persist to the next.
   Any recipe here must set the environment in the same invocation as the cargo
   call, or it silently measures the wrong compiler.

If the peer's segregation lands, this ADR should be re-decided rather than
applied on top of it: pinning the triple *and* segregating by triple is
redundant, and the pin's real remaining value would be uniformity for CI and
fresh clones rather than cache protection.

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

- The environment agrees with the pin: `RUSTC`/`RUSTDOC` are unset (or point at
  the pinned triple), and `rustup show` reports a default host matching it.
  Verified per the 2026-08-15 revision — this is the condition a triple pin
  alone does not establish, and the one that actually produced the split.
- Every `rust-toolchain.toml` in the stack names a full triple.
- A committed check fails when more than one host triple appears in the shared
  cache, so the condition cannot silently return.
- `cargo check --target x86_64-unknown-linux-gnu` succeeds in hermes from the
  msvc host, confirming the cross-check replacement before the gnu toolchain is
  retired.
