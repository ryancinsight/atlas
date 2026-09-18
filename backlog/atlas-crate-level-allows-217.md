<a id="atlas-crate-level-allows-217"></a>
## ATLAS-CRATE-LEVEL-ALLOWS-217 — 502 blanket suppressions the ratchet never counted [major] — in-progress

**Specified 2026-08-19, and the severity in the original filing was
overstated.** Measured with the scanner's own classification rather than a
grep: `missing_docs` (243 mentions) and `clippy::unwrap_used` (31) are
**almost entirely test-scoped** — inner attributes inside
`#[cfg(test)] mod tests`, which is the correct way to scope a test exemption,
and which `split_test_region` already excludes from the count. The seven
`unwrap_used` sites I first flagged as production are six `src/**/tests.rs`
sidecars plus one correctly-scoped test module. **Zero production violations
of the unwrap ban.** My grep counted test files; the committed detector does
not, and the detector was right.

What production actually holds, and it is **not** one pile of 502:

**CFDrs carries 349 of the ~433 production sites, in 62 files, and its
workspace already has a curated 53-entry `[workspace.lints]` table.** Against
that table:

| pile | mentions | disposition |
|---|---|---|
| already `allow` workspace-wide | **204** | pure redundancy — delete, zero behavioural change |
| `clippy::print_stdout` | **42** | overrides a workspace **`deny`**, in library crates — the real violation |
| everything else | ~105 | per-crate escalations needing individual judgement |

So the bulk is not debt at all, it is duplication of a decision already
recorded once at the workspace level — the same SSOT failure as any other
copied constant. And the genuine finding is small and sharp: **42 blanket
allows silently re-enabling `print_stdout` in library crates whose own
workspace table denies it**, spread over cfd-validation (21), cfd-core (10),
cfd-2d (10), cfd-3d (5), cfd-1d (4), cfd-schematics (1) — all libraries, so
the CLI exemption does not apply.

**Root cause found 2026-08-19, and it inverts the plan. The "redundant"
mentions are not redundant — they are load-bearing, because the workspace
table is inert.**

moirai-core and moirai-gpu both carried `#![warn(clippy::all)]` and
`#![warn(clippy::pedantic)]` **in source**. A source attribute outranks the
manifest `[lints]` table, which cargo delivers as command-line flags, so the
workspace allow-list had no effect on those crates despite
`[lints] workspace = true` — and the per-crate `#![allow(...)]` lines were
the only thing suppressing pedantic. Deleting them alone reddened clippy with
**92 diagnostics**; that is how the premise was caught.

The same in-source escalation is present in **nine CFDrs crates** (cfd-1d,
-2d, -3d, -core, -io, -math, -optim, -python, -validation), which is where
349 of the ~433 sites live. So the CFDrs "204 redundant" figure above is
wrong for exactly those crates, and the correct order is inverted: **remove
the in-source `warn(all)`/`warn(pedantic)` first**, which makes the table
authoritative, and only then are the per-crate allows genuinely deletable.

**Second member done: apollo** (`style/apollo-butterfly-lint-consolidation-217`,
pushed). Different shape, because apollo has **no** in-source escalation — its
table was already authoritative, so the redundancy analysis held. Two
butterfly modules each carried the same pair of blanket allows;
`too_many_arguments` was already in the table (pure duplication) and
`many_single_char_names` moved into it with its reason recorded once —
butterfly kernels name radix inputs a, b, c, d after the signal-flow diagrams
they implement. **Four blanket file allows → one reviewed table entry.**

Verified with `clippy -p apollo-fft --all-targets -D warnings`: nine errors
remain and **none** names either removed lint. All nine are
`missing_const_for_thread_local` in cache/scratch/twiddle modules this change
does not touch — the documented windows-gnu false positive, filed below.

**Apollo residual, found in passing:** three `thread_local!` sites
(`radix_composite/cache.rs:119`, `mixed_radix/caches/scratch.rs:10`,
`mixed_radix/caches/twiddle.rs:16`) lack the `#[expect(clippy::missing_const_for_thread_local)]`
that `adaptive.rs`, `winograd/traits.rs` and `orchestration/cache/plans.rs`
already carry, so apollo's clippy is red on gnu independently of this item.
Two of the three already use `const { … }` initializers, making the lint a
false positive there; `twiddle.rs` allocates via
`with_capacity_and_hasher`, so its case is a real design question rather than
a suppression. Left alone deliberately: that is a kernel-cache decision on a
peer's tree, not part of a lint-hygiene item.

**First member done: moirai** (`0746861`, branch
`style/moirai-workspace-lint-authority-217`, pushed). `crate_level_allows`
**39 → 20**, clippy `--all-targets -D warnings` 0, nextest 104/104. The floor
gets *stricter*, not laxer: the workspace table sets
`pedantic = { level = "deny" }` where the source attribute said `warn`.

- Revised sequence: (1) per member, drop the in-source `warn(all)` /
  `warn(pedantic)` so `[workspace.lints]` governs, then delete the
  now-genuinely-redundant allows — verified by clippy, which is what proves
  redundancy;
  (2) fix or justify the 42 `print_stdout` sites, since a per-crate allow
  overriding a workspace deny is the strongest form of the pattern the floor
  prohibits; (3) adjudicate the ~105 remainder, promoting recurring ones into
  the workspace table with a comment and converting the rest to per-site
  `#[expect(..., reason)]`.
- Non-CFDrs remainder is small and can follow: moirai 39, coeus 17, apollo 8,
  consus 6.
- The lesson, again: an ad-hoc grep and the committed instrument disagreed by
  nearly 2×, and the instrument was correct both times. Measure with the
  scanner.

Detector fixed in `d9c8c60`; the debt itself is the open work.

`allow_sites` counts the substring `#[allow(`, and `#![allow(` does not
contain it — the `!` breaks the match. So the **blanket form was invisible**,
which is precisely the form the lint floor singles out as never acceptable:
"suppressions are per-site `#[expect(lint, reason = "...")]`, never blanket or
crate-level". An inner attribute silences a lint across every item in its
module or crate, *including code written after it*, so it cannot be reviewed
where it takes effect — strictly worse than the per-item form the ratchet did
count.

Production-code counts now seeded into the baseline (502 total):

| CFDrs | moirai | apollo | coeus | consus | kwavers | ritk | gaia | mnemosyne | hermes | leto |
|---|---|---|---|---|---|---|---|---|---|---|
| 367 | 47 | 34 | 18 | 10 | 10 | 8 | 4 | 2 | 1 | 1 |

Found while checking `e31065b`, which raised CFDrs `allow_sites` 88→90 to
absorb a Clippy PR that added `#![allow(...)]` attributes — the ratchet
recorded the two per-item allows and none of the crate-level ones. CFDrs'
`crates/cfd-1d/src/lib.rs` alone opens with a run of ten, several carrying
justifications that read as deferrals ("Error documentation deferred for
internal APIs").

- Acceptance: ratchet burn-down, CFDrs first. Each removal either fixes the
  underlying lint or converts to a per-site `#[expect(lint, reason = "...")]`
  that expires when the site is fixed. No `--accept-raises`.

**CFDrs member — steps 1–2/3 delivered 2026-08-25** (branch
  `fix/cfdrs-lint-authority-217`, CFDrs PR #372 at head `0155d8f4`,
  MERGEABLE):

  - **Step 1** (`2244e3a1`): removed the in-source `#![warn(clippy::all)]` /
    `#![warn(clippy::pedantic)]` escalation in **all ten** crates (the
    previously-claimed nine plus cfd-schematics in combined form), making the
    47-entry `[workspace.lints.clippy]` table the single authority — the
    moirai-verified shape. Then deleted **108 blind allow lines across 31
    files** whose every lint is already workspace-allowed (pure copies;
    lines mixing rust lints like `missing_docs` kept). Clippy-verified as
    the redundancy oracle: all-targets zero real warnings, nextest
    3256/3256, fmt clean, 31 files / 125 pure deletions, CRLF byte-preserved.
  - **Step 2** (`0155d8f4`): the `print_stdout`/`print_stderr` blanket
    overrides of the workspace deny → self-expiring `#[expect]`. The
    detector's "42 sites" undercounted once more (the real surface is
    ~100 files once tests/examples are included), so each file was
    classified: src test-sidecars and integration tests narrowed to the
    lint that actually fires (`print_stderr` for `eprintln!` skip-notes,
    both where stdout prints exist); cfd-3d `bifurcation/validation.rs` +
    `venturi/analysis.rs` keep an unconditional file-level expect because
    `print_summary`/flow diagnostics are real library report APIs;
    files whose prints live only in doc comments dropped the attribute
    entirely. Clippy 0 warnings (expects are self-expiring — any stale
    suppression surfaces as an unfulfilled-expect warning), nextest
    3256/3256, fmt clean.
  - Remaining: step 3 (~105 per-crate escalations needing individual
    adjudication, separate PR).

**kwavers member delivered 2026-08-25** (branch
  `fix/kwavers-lint-leftover-217`, PR #646 at head `f9c124c53`, MERGEABLE):
  the last 4 crate-level allows — 3 were pure duplicates of the workspace
  table (`doc_markdown`, `module_inception`, `needless_range_loop`, all
  already `allow` in `[workspace.lints.clippy]`) and were deleted; the
  python-binding `type_complexity` allow became a self-expiring
  `#[expect]` with the binding-surface reason (`too_many_arguments` stays
  allowed — documented Python mirror surface). Clippy 0 warnings, fmt
  clean; the single `pstd_finite_window_born` failure reproduces at main
  (pre-existing, unrelated).

**consus member removed 2026-08-25** (branch
  `fix/consus-lint-expect-217`, PR #55 at head `2c97deb`, MERGEABLE):
  consus's floor is `pedantic = deny`, so every remaining crate-level
  allow suppresses a genuinely firing lint — converted all 6 to
  self-expiring `#[expect]` with the documented reason
  (`empty_line_after_doc_comments`, `too_many_arguments` ×2,
  `needless_range_loop`, `collapsible_match`, `useless_conversion`).
  `budget.rs` untouched (already the correct test-scoped pattern). Clippy
  0 warnings, nextest 2582/2582, fmt clean (CRLF preserved).

  Remaining members: coeus 18 (peer branch `codex/coeus-lint-ratchet`
  claims it — not actionable), ritk 8, gaia 4, mnemosyne 2, hermes 1,
  leto 1.

  **Merge status 2026-08-25 (hosted checks, exact-head policy — nothing
  merged yet):** CFDrs #372: lockfile pass, Rust-workspace-gate + book
  figures still pending. kwavers #641 (`84ba553ef`) and stacked #642
  (`e1ecdd231`) each expose five initial preflight/review checks rather than 26
  immediately queued jobs; duplicate
  coverage PR #645 is closed as superseded, releasing its queued matrix.
  kwavers #646: no checks observed (fresh push).
  consus #55: no checks observed. kwavers #644 (gpu ratchet): **21/31
  checks SUCCESS** — only the 8 long legs remain pending (Build & Test
  stable/beta, Heavy Validation, Miri, Lockfile integrity, PINN
  Convergence, Benchmark smoke, feature-combination plotting); heads all
  confirmed unchanged and MERGEABLE. Merge each at its exact head the
  moment its checks go terminal.

