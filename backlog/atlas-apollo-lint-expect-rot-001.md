<a id="atlas-apollo-lint-expect-rot-001"></a>
## ATLAS-APOLLO-LINT-EXPECT-ROT-001 — Remove obsolete Windows Clippy expectations [patch] — in-progress
- Owner: codex coordinator; scope: Apollo source files containing the 42 `#[cfg_attr(windows, expect(clippy::missing_const_for_thread_local, ...))]` sites across 28 files. Non-goals: Apollo's peer-owned `Cargo.lock` and `backlog.md`, the Stockham policy work, and unrelated provider consumers.
- Acceptance: the expectations are removed or narrowed only if the pinned toolchain still emits the lint; Apollo's workspace Clippy gate passes with `-D warnings` and no `-A` override, with value-semantic tests unchanged.
- Verification: record the exact provider revision, focused tests, doctests, Clippy, rustfmt, and rustdoc results before closing; update the provider item without staging its peer-owned working-tree changes.
