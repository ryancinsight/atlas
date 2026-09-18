<a id="atlas-kwavers-real-compute-028"></a>
## ATLAS-KWAVERS-REAL-COMPUTE-028 — Remove Kwavers production identity paths [major] [arch] — todo

- Owner: Kwavers provider owner; Atlas scope is the audit record and consumer
  integration gate. Kwavers source files are peer-owned in the active checkout.
- Findings: realtime GPU scan conversion, mixed-domain time propagation and
  nonlinear correction, KZK retarded-time application, and PINN domain
  adaptation all contain identity-return paths on the fetched default. Exact
  evidence and locations: `gap_audit.md#atlas-kwavers-real-compute-028`.
- Acceptance: each seam performs input-sensitive computation or is removed or
  narrowed; the corresponding analytical/differential tests fail under the old
  identity body; focused provider gates and the full Kwavers integration gate
  pass; no clone-only implementation remains at the named locations.
- Re-open trigger: a clean committed Kwavers source increment lands on
  `origin/main` or a peer claim becomes stale under the one-hour sweep.

