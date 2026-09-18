<a id="atlas-adr0033-stages"></a>
## ATLAS-ADR0033-STAGES — Krylov ownership unwind, measured status [arch] — in-progress

outcome: one Athena-backed Krylov implementation stack-wide; delete the Leto
iterative family and Kwavers' three duplicate implementations (ADR 0033).
- Stage A done (Hephaestus-backend preconditioner still missing, residual gap).
- Stage B closed at `05c025e8`, PR [#363](https://github.com/ryancinsight/CFDrs/pull/363) merged at `c5f9fa2c`.
- next: Stage C — migrate Kwavers off 3 iterative impls (bem/gmres.rs,
  integration/nonlinear/gmres/, matrix-free jvp.rs — needs `&mut self` →
  `&self`, only mutation is a scratch-buffer cache).
- next: Stage D — delete `leto-ops/.../linalg/iterative/` once B+C land
  (zero other stack consumers).
- **blocked:** Stage C claim — all 7 Kwavers worktree lanes hold live PRs;
  two-tree bound forbids a ninth. Re-open: any lane completes and merges.
