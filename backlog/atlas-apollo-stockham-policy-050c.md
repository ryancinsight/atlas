<a id="atlas-apollo-stockham-policy-050c"></a>
## ATLAS-APOLLO-STOCKHAM-POLICY-050C — Parameterize the dispatch-policy matrix [minor] — todo

- Three parallel type families cover the same (scalar × ISA) axis inside
  `stockham`: `StockhamAvxBackend` (4 impls), `StockhamPrecision` (6
  hand-written ZST markers = {Precise,Reduced} × {scalar, AvxFma, Avx512},
  the 1240 lines of `precision/{precise,reduced}.rs`), and `StockhamKernel`
  (2 impls, on the *scalar* axis — the 050B census mis-filed this one).
- `StockhamPrecision` is a dispatch-policy matrix written per cell; it can be
  parameterized over `B: StockhamAvxBackend`. Type-level, no numerics risk,
  real reduction — unlike 050A.
- Also here: `StockhamAvxBackend` gives three methods provided bodies that are
  `unreachable!("Not implemented for this precision")`. A panicking default is
  a mock-shaped seam — the differing fused-stage sets belong in a capability
  const or a split trait.
- Acceptance: `precision/{precise,reduced}.rs` line count materially reduced
  with the ZST marker set derived rather than enumerated; zero
  `unreachable!` provided bodies on the backend trait; bit-identical FFT
  outputs against the pre-change build on the existing differential suite.

