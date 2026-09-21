<a id="atlas-consus-szip-bound-2026-08-20"></a>
## ATLAS-CONSUS-SZIP-BOUND-2026-08-20 — Bound SZIP allocation [security][patch] — in-progress
- outcome: the SZIP decoder rejects a malformed four-byte sample count with a typed error instead of trusting it into an unbounded allocation/abort.
- next: confirm post-merge CI and Documentation runs `32436374114` / `32436374130` reach terminal success before advancing the Consus gitlink.
