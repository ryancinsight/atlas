<a id="prometheus-promotion"></a>
## ATLAS-PROMETHEUS-PROMOTION-2026-09-03 - Create and register `prometheus` (species mass balance) [arch][minor] - blocked
Charter: [ADR 0058](docs/adr/0058-prometheus-phase-0-charter.md). Path: [ADR 0056](docs/adr/0056-new-construction-promotion-path.md).
- **outcome:** `prometheus` owns homogeneous reaction networks (species, stoichiometry, rate laws, Arrhenius, net production, enthalpy) integrated 0-D through Horae. Registry: `prometheus-kinetics` (free).
- **done (basis 1412e1f9502c):** P2: `repos/prometheus` is a `.gitmodules` member and `aea52ff` and `4c176ef` are ancestors of its `origin/main`; `prometheus-kinetics` is absent from crates.io (registry lookup 2026-11-24).
- **next — P8 (queued):** replaces Kwavers chemistry network layer across two callers plus `kwavers-therapy`; Kwavers keeps its transport. Blocked: Kwavers at its two-tree bound.
- **next — P7, P9 (Ask-User):** register as A7; publish after P8.
- **Acceptance (standing):** no `nalgebra`/`ndarray`/`rayon`/`num-traits` in either repo's dependency graph (enforced by `deny.toml` bans); generic over `T: RealField` with every oracle at `f32`/`f64`; no dependency on an integrator or another balance domain except through Harmonia (architecture test).
