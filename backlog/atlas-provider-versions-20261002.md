<a id="atlas-provider-versions-20261002"></a>
## ATLAS-PROVIDER-VERSIONS-20261002 — Adopt eunomia 0.9 and leto 0.44 across consumers [correctness] — todo
- priority: correctness
- outcome: every allowlisted consumer's manifest accepts `eunomia` 0.9.0 (ryancinsight/eunomia#154) and `leto`/`leto-ops` 0.44.0 (ryancinsight/leto#318), and its lock resolves them outside the overlay.
- oracle: at fetched default heads, `python scripts/atlas-stack-overlay.py check` prints no `REQUIREMENT LAG` line naming eunomia, leto or leto-ops; each member's `cargo metadata --locked` resolves outside the overlay.
- measured 2026-10-02 at heads: 51 lag lines. `eunomia` 0.8.x is required by CFDrs, aequitas, apollo, ares, asclepius, athena, coeus, gaia, harmonia, helios, hephaestus, hermes, horae, hyperion, kwavers, leto, metis, mnemosyne, prometheus, proteus, ritk and tyche; `leto` 0.43 by CFDrs, apollo, ares, athena, coeus, gaia, helios, hephaestus, kwavers, prometheus and ritk.
- order: leto first, since every leto consumer resolves leto's own eunomia requirement; then the rest; members on `mnemosyne-memory` 0.7 follow [ATLAS-MNEMOSYNE-08-SWEEP](atlas-mnemosyne-08-sweep.md).
- scope: `Cargo.toml` and `Cargo.lock` of the members above; source edits only where a bump breaks a call site.
- next: one `build(deps)` PR per member in that order; each verifies `cargo build --locked` and its focused tests before its lock commits.
- basis: a92f185288e3a768b3efa2a4992578eb7ac74e9f
