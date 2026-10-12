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

## Metis development build isolation

Metis's compiler commands retain `--locked`. Atlas's broad root overlay adds
unused patch records that Cargo 1.97 rewrites between commands; `atlas-metis.py`
derives an isolated overlay from the resolved package closure and Metis's direct
git dependencies. The root configuration remains authoritative for profiles,
provider paths and the shared target directory. A neutral temporary working
directory excludes unrelated inherited patches; it is removed on exit. Cargo
reconciles the development lock before the first locked compile. A stale actual
dependency still fails a subsequent locked compiler invocation.

This is local development orchestration. Provider delivery and standalone lock
regeneration remain required before a release; no path-overlay lock is a release
artifact. The existing stack build-identity metadata backlog item remains open
because this increment does not alter the identity runner's source policy.
