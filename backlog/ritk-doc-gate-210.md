<a id="ritk-doc-gate-210"></a>
## RITK-DOC-GATE-210 — `cargo doc` is red on ritk's default branch [patch] — in-progress

- **outcome:** `cargo doc --workspace --no-deps` exits 0 under
  `RUSTDOCFLAGS=-D warnings`, with a rustdoc CI step joining ritk's
  pipeline so it cannot go red unobserved again.
- **delivered:** six links fixed in `5a5de0ef`; `MAX_SEQUENCE_DEPTH`
  delinked from `anonymize_object` in `4c55c57c`.
- **open:** gate still unconfirmed — a repo sweep finds ~41 further
  public-to-private link candidates, not all defects; needs
  sweep-then-verify, not a bulk edit. The last confirming run was
  corrupted by an unrelated branch move reverting the checkout to a
  58-behind `main`; two readings taken then are retracted as
  stale-checkout artifacts. Remaining: one clean gate run from a current
  checkout, then wire the CI step.
