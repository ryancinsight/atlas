<a id="ares-promotion"></a>
## ATLAS-ARES-PROMOTION-2026-09-03 - Create and register `ares` (solid momentum balance) [arch][minor] - in-progress
Charter: [ADR 0057](../docs/adr/0057-ares-phase-0-charter.md). Path: [ADR 0056](../docs/adr/0056-new-construction-promotion-path.md). Boundary: [ADR 0055](../docs/adr/0055-continuum-domain-decomposition.md).
- **outcome:** `ares` owns small-strain linear elastostatics on Gaia meshes, closed by Proteus, solved by Athena, verified against analytical oracles.
- **non-goals:** plasticity, contact, finite deformation, dynamics, fracture; no material constants, no direct edge to another balance domain.
- **next: A9 — publish `ares-solid` (Ask-User).** Closure `eunomia -> aequitas -> proteus-mat -> ares-solid`; `eunomia`/`aequitas` already on crates.io. Remaining: account owner runs token-authenticated first publish (`proteus-mat` then `ares-solid` — crates.io requires the crate to exist before Trusted Publishing can be configured), then wires Trusted Publishing (owner `ryancinsight`, workflow `rust-release.yml`, env `crates-io`). `ares-operator`/`ares-coupling` are out of A9 scope (harmonia is `publish = false`).
- **Open findings:** ADR 0059 marshalling wording needs correction (traction is per-facet); Harmonia's `Substep` has no public constructor, forcing an inherent-method workaround in `ares-coupling`.
- **integrator:** claude-opus-5.
- Kwavers elastic-wave migration is Phase 1; Phase 0 does not block on it.
[ares ADR 0001]: https://github.com/ryancinsight/ares/blob/main/docs/adr/0001-athena-seam-as-a-separate-crate.md
