<a id="prometheus-promotion"></a>
## ATLAS-PROMETHEUS-PROMOTION-2026-09-03 - Create and register `prometheus` (species mass balance) [arch][minor] - in-progress

Charter: [ADR 0058](docs/adr/0058-prometheus-phase-0-charter.md). Path:
[ADR 0056](docs/adr/0056-new-construction-promotion-path.md).
- **outcome:** `prometheus` owns homogeneous reaction networks (species,
  stoichiometry, rate laws, Arrhenius, net production, enthalpy)
  integrated 0-D through Horae. Registry: `prometheus-kinetics` (free).
- **status:** P0-P6 delivered, gate-green locally.
- **next — P2 (Ask-User):** create `ryancinsight/prometheus` repo; eleven
  local commits (`aea52ff..4c176ef`) push once it exists.
- **next — P8 (queued):** replaces Kwavers chemistry network layer
  across two callers plus `kwavers-therapy`; Kwavers keeps its
  transport. Blocked: Kwavers at its two-tree bound.
- **next — P7, P9 (Ask-User):** register as A7; publish after P8.
