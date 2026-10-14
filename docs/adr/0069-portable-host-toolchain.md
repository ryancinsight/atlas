# ADR 0069: Resolve the pinned compiler on the native host

- Status: Accepted
- Date: 2026-10-11
- Change class: [patch]
- Scope: Apple platform setup requested for Metis.

## Contract

The root and member pins select Rust 1.97.0 for the installed Rustup host.
Cargo, rustc, and rustdoc must resolve through that same toolchain. An iOS
target changes the generated program, not the operating system of the compiler.
All builds use the existing Atlas target directory; Cargo separates explicit
cross-compilation targets within it.

## Decision

Replace the root's Windows-only channel with its version-only channel, matching
the member repositories. Preserve the compiler version and required components.
Keep the bootstrap's removal of RUSTC/RUSTDOC overrides and the existing
toolchain preflight. Windows CUDA builds still require the native MSVC Rustup
host. This supersedes ADR 0043's proposed global Windows host selection; its
compiler-coherence invariant remains required.

An environment override or a second compiler distribution can violate compiler
coherence regardless of a committed triple. Pinning a Windows executable on
every host does not establish that invariant and prevents native Apple builds.
Separate compiler versions or per-member caches are unnecessary.

## Verification

From the root, `rustup show active-toolchain`, `rustc -Vv`, and `cargo -V` must
resolve Rust 1.97.0 on aarch64-apple-darwin. Member builds must use the same
compiler version. Apple target builds select their target explicitly. Build,
runtime, and device evidence are recorded in the Apple setup checklist.

## Metis locked source isolation

The runner's invariant is `Cargo.lock_after = Cargo.lock_before` for every
successful build. Dependency sources come from the committed Git lock; current
Metis workspace/frontend edits remain local. All metadata and compilation
commands use `--locked`. A stale dependency fails before source substitution.

The former graph-scoped overlay violates that invariant: its unlocked metadata
step removes Git source identities from the canonical lock. A scoped path
overlay still changes source identity. Restoring the lock after the build would
mask the mutation and race other commands; a snapshot would break live frontend
watching and the CLI's native-host workspace path. Neither is selected.

`atlas-metis.py` runs from a neutral temporary directory with the root's build
profiles, shared target directory and other non-patch configuration. It omits
dependency patch tables and removes its temporary configuration on exit.
Provider changes enter through the published Git revisions and canonical lock.
No source workspace is copied, and native CLI workspace paths stay live.

Verification compares both locks before/after real Atlas Apple bundling,
validates the package signature and exact resource bytes from that build, and
checks input-sensitive Greet and native exit behavior. Configuration tests
preserve every non-patch field and the shared cache. The stack build-identity
metadata backlog remains independently open.
