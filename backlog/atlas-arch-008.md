<a id="atlas-arch-008"></a>
## ATLAS-ARCH-008 — Replace pointer-scattered containers on traversal paths [patch] — todo
- outcome: production `Vec<Vec<_>>`/per-node heap graphs on traversal paths become contiguous buffers with layout tests and criterion comparisons; measurement narratives live in the delivering PRs, never here.
- oracle: `scripts/atlas_scattered_containers_classify.py --pinned` + `scripts/oracles/arch-008-production-sites.txt`, `make verify-scattered-oracle`. `--pinned` reads the gitlink commits `HEAD` records straight from the object store, so the gate holds whatever any member has checked out; regeneration rides every pin advance.
- next: select the highest-traffic remaining production site from the regenerated pinned census for a criterion comparison; the `scattered_containers` ratchet (atlas#375) blocks new inflow.
- basis: atlas origin/main 54bd6e1be (2026-10-25)
