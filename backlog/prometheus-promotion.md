<a id="prometheus-promotion"></a>
## ATLAS-PROMETHEUS-PROMOTION-2026-09-03 - Create and register `prometheus` (species mass balance) [arch][minor] - in-progress

Charter: [ADR 0058](docs/adr/0058-prometheus-phase-0-charter.md). Path:
[ADR 0056](docs/adr/0056-new-construction-promotion-path.md).
Execution steps: `checklist.md` `ATLAS-PROMETHEUS-PROMOTION-2026-09-03`.

- **outcome:** `prometheus` owns homogeneous reaction networks - species,
  stoichiometry, mass-action rate laws, Arrhenius through Proteus, net
  production rates, reaction enthalpy - integrated 0-D through Horae.
- **non-goals:** reactive-transport discretization (stays with the balance
  owner of the field), combustion closure, surface and heterogeneous reactions,
  plasma chemistry, electrochemistry, phase equilibrium.
- **registry name:** `prometheus-kinetics`; bare `prometheus` on crates.io is
  the metrics client and is unavailable. Verified free (HTTP 404) 2026-09-04.

| Phase | Deliverable | Acceptance oracle | Depends on |
| --- | --- | --- | --- |
| P0 | aequitas gains `ReactionRate` and `MolarFlux` | `MolarConcentration / Time == ReactionRate` at the type level | `#aequitas-reaction-quantities` |
| P1 | Repository scaffold, same floor as A1 | same gate | P0 |
| P2 | **Ask-User:** create `ryancinsight/prometheus` | repository exists | P1 |
| P3 | Species and stoichiometry over Leto | transpose(nu) times M equals zero, structurally, for a balanced network | P2 |
| P4 | Rate laws; Arrhenius via `proteus::TemperatureResponse` | first and second-order closed forms; ln k against 1/T recovers Ea and A | P3 |
| P5 | Net production and reaction enthalpy | hand-computed networks | P4 |
| P6 | 0-D integration through Horae, including the stiff path | equilibrium reaches K_eq; **Robertson benchmark**; mass conserved; no negative concentrations; integrator order recovered | P5 |
| P7 | Register in atlas, as A7 | architecture test green | P6 |
| P8 | First consumer: Kwavers sonodynamic species kinetics across Harmonia | coupled therapy case runs | P7 |
| P9 | **Ask-User:** publish `prometheus-kinetics` | registry install and smoke; docs.rs | P8 |

- **status 2026-09-04:** P0 done (aequitas `#50`). The local `repos/prometheus/`
  tree carries the full Phase 0 computation — P1 floor, P3
  species/concentration/stoichiometry, P4 typed mass-action rates, P5
  net-production/reaction-enthalpy, P6 integration (first-/second-order decay,
  reversible equilibrium, convergence order, conservation, non-negativity, and
  the Robertson stiff benchmark against cited INdAM-Bari reference values via
  the Horae implicit seam). Gate green: fmt, clippy `-D warnings`, 33 tests,
  doc `-D warnings`. Eleven local commits `aea52ff..4c176ef`. **P2 (create
  `ryancinsight/prometheus`) is still Ask-User**; the commits push once it
  exists. Phase 0 computation is complete; the remainder is P2/P7/P9 delivery
  and the P8 Kwavers consumer.
- **P8 audit 2026-09-06 (corrected):** the two-file claim was a partial search.
  The real network is `kwavers-physics/src/chemistry/` — a full hand-rolled
  implementation: `reactions.rs` (`ChemicalReaction`, `Species`, `ReactionRate`
  as raw structs), `reaction_kinetics/`, `integrator/` (bespoke),
  `ros_species/` (a `ROSSpecies` enum + `ROSConcentrations` of `Array3` fields),
  `photochemistry/`, `radical_initiation/`, `ros_plasma/`, `validation/`.
  Prometheus replaces the network layer (`Species`, `ChemicalReaction` →
  `ReactionNetwork`, kinetics → mass-action + Arrhenius through
  `proteus::TemperatureResponse`, integrator → Horae); Kwavers keeps the
  transport layer (`Array3` spatial fields, `diffusion/` — the field owner's
  discretization per ADR 0058). The raw `constants/chemistry.rs` values and the
  bubble-dynamics Arrhenius are two inputs to the same module, not the whole.
  Consumer closure (the Species swap must convert atomically): the `chemistry/`
  network files themselves, two `kwavers-physics` callers (bubble-dynamics
  `chemical_reaction.rs`, sonoluminescence `spectrum.rs`), and the
  `kwavers-therapy` orchestrator (`chemical.rs`, `initialization/modalities.rs`).
  `diffusion/` and the `Array3` transport stay in Kwavers.
  **Queued:** the migration lands in a Kwavers lane, but Kwavers is at the
  two-tree bound — main plus a live `kwavers-elastic-computed` lane on
  `docs/kw-branch-inventory` (active seconds ago). Re-open when that lane's
  item completes or goes stale.
- **historical prerequisite retired:** the Kwavers reaction-vocabulary
  consolidation existed to produce a deletion ledger; under ADR 0056 that
  ledger arrives with the P8 consumer migration. It remains worthwhile on its
  own merits but no longer blocks.
- Prometheus is the first embedded-stepping consumer for Horae, retiring a
  capability recorded as consumer-gated with no caller.

