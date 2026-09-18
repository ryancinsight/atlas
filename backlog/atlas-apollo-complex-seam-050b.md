<a id="atlas-apollo-complex-seam-050b"></a>
## ATLAS-APOLLO-COMPLEX-SEAM-050B — Element-parameterize the complex seams [minor] — todo

- Census corrected on re-run; the original count of eight was wrong.
  `FftPrecision` and `TwiddleOutput` already carry **three** impls including
  `Complex<f16>` — a seam admitting three element types is element-parameterized
  already, not a `Complex64`/`Complex32` fork. `StockhamKernel` is on the scalar
  axis and belongs to 050C.
- Genuine two-impl complex pairs: **five** — `KernelScalar`, `PlanScratch`,
  `TwiddleStore`, `NormalizeSlice`, `ScratchDispatch`.
- Independent of 050A: type-level and crate-wide versus x86 leaf codegen.

