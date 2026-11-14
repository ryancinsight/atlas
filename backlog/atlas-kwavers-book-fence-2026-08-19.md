<a id="atlas-kwavers-book-fence-2026-08-19"></a>
## ATLAS-KWAVERS-BOOK-FENCE-2026-08-19 — restore truthful mdBook fence semantics [patch] — todo
- Kwavers commit `cbf99272b4265b720b4e4d597515f91ba944fefa` (an ancestor of kwavers origin/main, basis 2b000c51b) changes the affected book fences to `text` or `rust,ignore` according to their actual content and corrects the stale `DENSITY_WATER_NOMINAL` excerpt.
- The linked source examples still need `cargo check -p kwavers --examples --locked` after the shared Atlas overlay lock mismatch is repaired. The current command stops before compilation because `--locked` refuses the overlay's requested lockfile update; no Rust-source result is claimed.
