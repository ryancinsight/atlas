<a id="atlas-mnemosyne-default-recheck-2026-08-18"></a>
## ATLAS-MNEMOSYNE-DEFAULT-RECHECK-2026-08-18 — moving default remains open — in-progress

- Mnemosyne `origin/main` advanced to
  `43cdf04769d4ab8701dea657b282c4a189175d48`. The Atlas gitlink remains at
  the previously verified `64f0d2ebe58e14705ca2345cad2c705f99a6b611`.
- Default CI run `32206977029` has Rust verification, Rust 1.95, Loom,
  aarch64, and ThreadSanitizer successful; Miri remains in progress. Do not
  advance the pointer until that exact default-head run completes; the
  peer-dirty primary checkout remains untouched.

