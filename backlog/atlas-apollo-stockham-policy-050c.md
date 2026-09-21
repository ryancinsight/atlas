<a id="atlas-apollo-stockham-policy-050c"></a>
## ATLAS-APOLLO-STOCKHAM-POLICY-050C — Parameterize the dispatch-policy matrix [minor] — todo
- outcome: `StockhamPrecision`'s six hand-written ZST markers ({Precise,Reduced} x {scalar,AvxFma,Avx512}) collapse to one generic parameterized over `B: StockhamAvxBackend`; `StockhamAvxBackend`'s three `unreachable!` provided-body methods become a capability const or split trait instead of a panicking default.
- next: reduce `precision/{precise,reduced}.rs` line count with the marker set derived, not enumerated; zero `unreachable!` provided bodies on the backend trait; bit-identical FFT outputs against the pre-change build on the existing differential suite.
