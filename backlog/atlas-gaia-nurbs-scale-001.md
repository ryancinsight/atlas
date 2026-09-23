<a id="atlas-gaia-nurbs-scale-001"></a>
## ATLAS-GAIA-NURBS-SCALE-001 — Preserve finite rational derivatives — todo
- outcome: Evaluate the complete finite weight and coordinate-difference ratio without intermediate overflow in Gaia NURBS derivatives.
- priority: correctness
- needs: none; Eunomia PR #104 merged at 5e2c496.
- scope: Eunomia FloatElement scaling; Gaia NURBS curve and surface derivatives; [ADR 0064](../docs/adr/0064-nurbs-derivative-scaling.md).
- acceptance oracle: f32/f64 degree-1 clamped curve and both surface partials at t=0 with coordinates [0, MIN_SUBNORMAL] and weights [MIN_SUBNORMAL, MAX] return MAX; ordinary surface bits match independent oracle 0x3f75c28f and 0xbda3d70c.
- next: update Gaia's standalone lock to Eunomia 5e2c496 and implement one product-ratio path for curve and surface derivatives with value-semantic regressions.
- basis: 0d3016899e9ff4ba3e83be1f601d131a554c390c.
