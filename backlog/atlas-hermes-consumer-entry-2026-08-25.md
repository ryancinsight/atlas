<a id="atlas-hermes-consumer-entry-2026-08-25"></a>
## ATLAS-HERMES-CONSUMER-ENTRY-2026-08-25 — Restore Hermes as the stack's lane-kernel owner [arch] — in-progress
- **outcome:** a consumer anywhere in the stack writes one generic lane kernel against `hermes-simd` and gets per-ISA machine code for it.
- **step 1 delivered:** hermes PR #63 merged (`85655c05`, ADR 016) — `vectorize` + `LaneKernel<T>` give a `#[target_feature]` entry point.
- **step 2 rescoped the item:** `apollo-fwht` migrated onto the entry, measured 1.6x-8.8x slower, reverted (PR #112) — `#[target_feature]` doesn't survive cross-thread closures, and Hermes' scalar backend already auto-vectorizes bandwidth-bound kernels at baseline.
- **rescoped acceptance:** a measurement gate, not a census — a slower family stays as-is, recorded.
- **open:** kwavers AVX-512 FDTD stencils are the most promising candidate; steps 3-4 stay unfiled pending measurement.
