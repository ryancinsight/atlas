<a id="atlas-arch-008-running-in-place-225"></a>
## ATLAS-ARCH-008-RUNNING-IN-PLACE-225 — The conversion converts and re-accumulates at the same rate [patch] — in-progress

`atlas_scattered_containers_classify.py --verify-oracle` against the committed oracle (`scripts/oracles/arch-008-production-sites.txt`, 243 sites) found: 35 sites now in production but missing from the oracle; 36 oracle sites no longer in production (net -1). The conversion cannot converge while new pointer-scattered containers arrive at the conversion rate; inflow spans consus 8, gaia 7, CFDrs 7, coeus 5, ritk 4, moirai 2, kwavers 2.

- **outcome:** the classifier runs in CI and blocks new pointer-scattered containers from landing unnoticed.
- **Gate wired by a peer** (`atlas-conformance.yml` now runs `--verify-oracle`) without regenerating the oracle to absorb the 35 — it stays 243 lines and red until they convert.
- **next:** the 35 sites are converted or individually justified in the oracle; the oracle is regenerated only in a commit whose subject says so (prior regenerations rode unrelated gitlink-advance chore commits, e.g. `5956d02`).
