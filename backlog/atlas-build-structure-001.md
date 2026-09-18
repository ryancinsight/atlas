<a id="atlas-build-structure-001"></a>
## ATLAS-BUILD-STRUCTURE-001 — Consolidate leaf binaries; compiler-last dev profiles [patch] — in-progress

- outcome: flat `tests/*.rs` integration binaries per repo consolidate into
  one-or-few hierarchical harnesses (nextest still isolates per test), and
  wildcard dev-profile opt-level overrides become named, measured per-package
  exceptions — shrinking the shared debug-tree with no coverage loss. Coeus
  is fully consolidated across all crates with test-count parity proven.
- next: (1) whole-workspace debug-tree size delta, unmeasured; (2) remaining
  repos (CFDrs, kwavers, consus, ritk, hermes), worst-offender first; (3)
  helios's peer-held wildcard `opt-level = 3` override; (4) Aequitas split,
  provider PR #35 on `5428584`, awaiting hosted gates.
- acceptance: per-repo binary census reduced/recorded; debug-tree delta
  measured; test count unchanged; no unjustified wildcard dev overrides.
