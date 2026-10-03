<a id="atlas-provider-versions-20261002"></a>
## ATLAS-PROVIDER-VERSIONS-20261002 — Adopt eunomia 0.9 and leto 0.44 across consumers [correctness] — todo
- priority: correctness
- outcome: every allowlisted consumer's manifest accepts `eunomia` 0.9.0 (ryancinsight/eunomia#154) and `leto`/`leto-ops` 0.44.0 (ryancinsight/leto#318), and its lock resolves them outside the overlay.
- oracle: at fetched default heads, `python scripts/atlas-stack-overlay.py check` prints no `REQUIREMENT LAG` line naming eunomia, leto or leto-ops, and `cargo update -p mnemosyne-memory` succeeds in coeus, asclepius and kwavers.
- measured at default heads, 2026-10-03 03:00 UTC (root `Cargo.toml`; asclepius at `crates/asclepius/Cargo.toml`): `eunomia` 0.8.x is still required by CFDrs, apollo, ares, asclepius, athena, coeus, gaia, harmonia, helios, kwavers, metis and ritk; `leto` 0.43 by CFDrs, apollo, ares, athena, coeus, helios, kwavers and ritk. aequitas, hyperion, leto and prometheus have since moved to eunomia 0.9, as have hephaestus, hermes, horae, mnemosyne, proteus and tyche.
- order: leto consumers first, since each resolves leto's own eunomia requirement; then the rest. Members on `mnemosyne-memory` 0.7 follow [ATLAS-MNEMOSYNE-08-SWEEP](atlas-mnemosyne-08-sweep.md), which this item gates.
- needs: none
- scope: `Cargo.toml` and `Cargo.lock` of the members above; source edits only where a bump breaks a call site.
- next: one `build(deps)` PR per member in that order; each verifies `cargo build --locked` and its focused tests before its lock commits. Re-measure the lag list first, since peers are landing these requirement bumps.
- basis: 3ea1f062969718a419bceac2dca48d4437878513
