<a id="atlas-kwavers-real-compute-028"></a>
## ATLAS-KWAVERS-REAL-COMPUTE-028 — Remove Kwavers production identity paths [major] [arch] — todo

outcome: each flagged Kwavers seam performs real input-sensitive computation or is removed/narrowed — no clone-only identity-return implementation remains at the named locations.
- Owner: Kwavers provider owner; Atlas scope is the audit record and consumer integration gate (Kwavers source is peer-owned).
- Findings: realtime GPU scan conversion, mixed-domain time propagation and nonlinear correction, KZK retarded-time application, and PINN domain adaptation all contain identity-return paths on the fetched default. Exact evidence/locations: `gap_audit.md#atlas-kwavers-real-compute-028`.
- Acceptance: analytical/differential tests fail under the old identity body and pass after the fix; focused provider gates and the full Kwavers integration gate pass.
- Re-open trigger: a clean committed Kwavers source increment lands on `origin/main`, or a peer claim goes stale under the one-hour sweep.
