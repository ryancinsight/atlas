<a id="ritk-doc-gate-210"></a>
## RITK-DOC-GATE-210 — `cargo doc` is red on ritk's default branch [patch] — in-progress

- Found because `-047`'s evidence table had no rustdoc step.
  `cargo doc --workspace --no-deps` under `RUSTDOCFLAGS=-D warnings` fails at
  HEAD, independent of any branch work.
- Six links repaired in `5a5de0ef` (unresolved `[Image]`, `[Point<D>]`, a
  matrix written as `rows [0,-1,0], [1,0,0], [0,0,1]` that parsed as three
  link targets, and two public-to-private links to
  `non_negative_information`). **The gate is still red**: ritk-io fails on
  `MAX_SEQUENCE_DEPTH`, same public-to-private class.
- A repo sweep finds ~41 further candidates of that class. They are *not*
  all defects — rustdoc only errors when a **public** item's docs link a
  private one, and the sweep over-matches trait methods and test-only items.
  Fixing them blind would be churn, so the item is the sweep-then-verify,
  not a bulk edit.
- Acceptance: `cargo doc --workspace --no-deps` exits 0 under
  `-D warnings`, and a rustdoc step joins ritk's CI so it cannot go red
  unobserved again — the absence of that step is the actual defect here.

**Progress 2026-08-18: seven links fixed, gate still unconfirmed.**
`MAX_SEQUENCE_DEPTH` is delinked from `anonymize_object` in `4c55c57c`,
landed onto the branch through a private index so the shared tree's
checked-out branch was never touched. The two remaining references to that
const (lines 338, 376) are on private items and resolve fine.

The confirming run could not be made: partway through, `-213` moved the
shared tree onto a 58-behind `main`, which reverted the working copies of
the earlier fixes and the lockfile. **Two readings taken after that point
were wrong and are corrected here rather than left in the record:**

1. I reported ritk's `apollo-fft` requirement as still `^0.26` with my bump
   "orphaned". False — `origin/main` and this branch both carry `^0.27.0`.
   I was reading the peer's stale `main`. There is no requirement lag and
   nothing to re-apply.
2. I attributed the resulting `hermes-simd-core ^0.6` resolver failure to
   that lag. It was entirely the stale checkout: the 58-behind base pins
   `apollo-fft 0.26`, whose transitive `^0.6` cannot unify with the
   overlay's local hermes 0.7.

Both edits made under the mistaken reading were reverted; they were my own,
no peer state was touched. The remaining work is one clean run of the gate
from a current checkout, then the CI step.

