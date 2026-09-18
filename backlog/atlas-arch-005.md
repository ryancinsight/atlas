<a id="atlas-arch-005"></a>
## ATLAS-ARCH-005 — Replace closed-set dyn dispatch in per-timestep paths [arch] — in-progress

- Owner: opencode-2026-08-05 (ADR phase delivered, ADR 0041; execution slice parked —
  both scope repos peer-held today: kwavers `refactor/retire-kwavers-optics`
  `e4e9966b6`, CFDrs `deps/eunomia-0.8`). scope: `repos/kwavers` first (largest), then
  `repos/CFDrs`.
  One operation family per claim.
- Outcome: dispatch-site counts are `kwavers` 665, `CFDrs` 352, `gaia` 104,
  `coeus` 98, `moirai` 83, `consus` 66. Sampling the kwavers solver shows the
  pattern is not type erasure of an open plugin set but vtable dispatch over
  closed design-time sets: `sources: &[Box<dyn Source>]` inside
  `forward/nonlinear/westervelt/update.rs` (evaluated per timestep),
  `boundary: Box<dyn Boundary>` held in the solver struct, plus `Box<dyn Signal>`
  and `Box<dyn Solver>`.
- Decision rule: a closed implementor set dispatched per timestep converts to an
  exhaustiveness-checked enum — static dispatch, still runtime-selectable, no
  vtable. Genuinely open plugin boundaries on cold paths keep `dyn` with the
  applicable exception annotated inline.
- Acceptance: per family, the count of `dyn` sites on the timestep path reaches
  zero; the enum is exhaustively matched with no catch-all arm; a criterion
  comparison on the affected kernel accompanies the change, since this is a
  performance-motivated claim and must carry performance evidence.
- Non-goals: mass-converting all 1 368 sites. Hot paths first, evidence per family.

