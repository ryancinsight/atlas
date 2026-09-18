<a id="atlas-kwavers-book-fence-2026-08-19"></a>
## ATLAS-KWAVERS-BOOK-FENCE-2026-08-19 — restore truthful mdBook fence semantics [patch] — in-progress

- Kwavers commit `cbf99272b4265b720b4e4d597515f91ba944fefa` changes the
  affected book fences to `text` or `rust,ignore` according to their actual
  content and corrects the stale `DENSITY_WATER_NOMINAL` excerpt.
- `mdbook test docs/book` and `mdbook build docs/book` pass at that exact
  provider head. This closes the prior 286-failure book-gate defect without
  pretending that workspace-dependent excerpts are standalone examples.
- The linked source examples still need `cargo check -p kwavers --examples
  --locked` after the shared Atlas overlay lock mismatch is repaired. The
  current command stops before compilation because `--locked` refuses the
  overlay's requested lockfile update; no Rust-source result is claimed.

