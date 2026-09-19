<a id="atlas-consus-szip-bound-2026-08-20"></a>
## ATLAS-CONSUS-SZIP-BOUND-2026-08-20 — Bound SZIP allocation [security][patch] — in-progress

- outcome: the SZIP decoder rejects a malformed four-byte sample count with
  a typed error instead of trusting it into an unbounded allocation/abort.
- delivered: [Consus PR #51](https://github.com/ryancinsight/consus/pull/51)
  adds independent header-size and payload-capacity bounds plus
  `try_reserve_exact`; merged at default `1000699fa740c74b8aea1b9cc5311f85d3d2a3cc`.
- next: confirm post-merge CI and Documentation runs `32436374114` /
  `32436374130` reach terminal success before advancing the Consus gitlink.
