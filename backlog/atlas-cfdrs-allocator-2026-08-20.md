<a id="atlas-cfdrs-allocator-2026-08-20"></a>
## ATLAS-CFDRS-ALLOCATOR-2026-08-20 — Remove library global allocator [major][arch] — in-progress

The CFDrs provider audit confirms `cfd-validation` installs a process-wide
`#[global_allocator]` from library code. This contaminates downstream
allocation measurements and prevents consumers from declaring their own
allocator. The current session claims only the cfd-validation memory profiling
surface, its opt-in benchmark harness, its consumer-allocator regression test,
and the provider ADR/PM records; unrelated CFDrs peer edits remain untouched.

Acceptance: the library has no global allocator; the tracking allocator is
constructed only by an explicit benchmark/test harness; a downstream-style
integration test declares `System` as its allocator; and the provider's locked
workspace all-target gate passes. This is a public breaking change and follows
the provider's recorded allocator decision.

Evidence: provider commit `d1305ee2` removes the library allocator, makes the
tracking counter explicit in `MemoryProfiler` and `CfdMemoryProfiler`, adds the
`memory_profiling` benchmark and `allocator_compat` integration test, and records
the decision in `repos/CFDrs/docs/adr.md`. Direct rustfmt, focused clippy, a
non-locked diagnostic check, `cargo nextest run -p cfd-validation --lib`
(187/187), the focused allocator nextest (1/1), and benchmark compilation pass.
The required locked check is still open: the Atlas overlay makes Cargo request
a provider `Cargo.lock` rewrite under `--locked`; that lockfile is peer-dirty
and was not modified or staged by this session.
The exact provider commit is now the head of open CFDrs PR
[#360](https://github.com/ryancinsight/CFDrs/pull/360); Rust workspace and
figure checks are queued there.

