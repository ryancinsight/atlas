<a id="atlas-adr0069-stages"></a>
## ATLAS-ADR0069-STAGES — Eunomia–Leto–Coeus vertical consolidation, measured status [arch] — in progress
outcome: one scalar element surface (eunomia), one slice-kernel surface (leto-ops), one sparse vocabulary (leto), one validation site per op (ADR 0069).
- PARITY-1 CLOSED 2026-10-08 (leto topk): parity matrix audited; leto-ops topk_axis (leto main 0539736).
- PARITY-2 CLOSED 2026-10-08 (leto cross/triangular): cross_into + triangular module (leto main a748936).
- PARITY-3 CLOSED 2026-10-08 (leto embedding gather): embedding_gather (leto main 4c25043).
- PARITY-4 CLOSED 2026-10-08 (leto ray integrals): ray_line_integrals (leto main 8d01d0b).
- PARITY-5 CLOSED 2026-10-08 (sinc both sides): SincOp leto-ops + hephaestus (leto main 2b84f7a, hephaestus master b059c27).
- PARITY-6 CLOSED 2026-10-08 (optimization pass): triangular fast path + const (leto main 47603e5).
- PARITY-7 CLOSED 2026-10-08 (bessel j0/j1 both sides): J0Op/J1Op (leto main 645f49e, hephaestus master f6d9748).
- PARITY-8 CLOSED 2026-10-08 (bessel k0 both sides): K0Op A&S 9.8.5/9.8.6 + NaN guard (leto main f347abf, hephaestus master 07ca9f8); host/CUDA/WGPU hardware-green.
- PARITY-9 CLOSED 2026-10-08 (leto unary math markers): 22 UnaryOps mirroring hephaestus UnaryExprs (method-routed trig/inverse/hyperbolic/exp-log/rounding + custom ExpNeg/Sign per ADR 0061); hephaestus side pre-existed (leto main 8a4e314); 464/464 ops suite.
- PARITY-10 CLOSED 2026-10-08 (leto activation markers): 23 UnaryOps transcribing hephaestus activation_value (relu/elu/sigmoid/tanh-grad/softplus/softsign/hard-sigmoid-swish/gelu/tanh-gelu/silu/mish forward+grad, identical formulas/branches/crossovers/NaN-inf policies; RealField-only methods as equivalent branches preserving F16/BF16); hephaestus side pre-existed (leto main 49c7734); 469/469 ops suite.
- PARITY-11 CLOSED 2026-10-08 (leto pad_into): PadOps counterpart in leto core (constant-fill pad into caller strided views, checked padded_shape with Overflow, ShapeMismatch; allocating pad now uninit+delegates, fixing its overflow panic); hephaestus side pre-existed (leto main 850ec85); 223/223 core + 469/469 ops suites.
- PARITY-12/13 CLOSED 2026-10-08 (asymmetry audits): jn/legendre (runtime-trip recurrences, no straight-line device form), statistics (host quality metrics), windows (one-time host setup), L-BFGS/Anderson (host-sequential drivers), quadrature (caller closures); rationale at all leto sites, no fleet device need (leto main 50679e6); 296 lib + 469 ops green. Deferred joint gaps: yn, i0.
