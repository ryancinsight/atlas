<a id="atlas-kwavers-book-fence-2026-08-19"></a>
## ATLAS-KWAVERS-BOOK-FENCE-2026-08-19 — restore truthful mdBook fence semantics [patch] — todo
- The linked source examples still need `cargo check -p kwavers --examples --locked` after the shared Atlas overlay lock mismatch is repaired. The current command stops before compilation because `--locked` refuses the overlay's requested lockfile update; no Rust-source result is claimed.
