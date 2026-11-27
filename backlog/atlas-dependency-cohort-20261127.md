<a id="atlas-dependency-cohort-20261127"></a>
## ATLAS-DEPENDENCY-COHORT-20261127 — Land the Melinoe 0.10.1 dependency cohort [patch] — blocked
- priority: correctness; needs: none; scope: repos/*, .cargo/config.toml
- outcome: Atlas records the landed Moirai, Metis, RITK, and Melinoe changes as one reproducible gitlink cohort whose first-party package versions agree with every selected standalone lock.
- evidence (basis: ddf18d670ace9e74f1ba935563e7259f4780cc3c): CFDrs default b76f00a72132087e6805516cac1b5c4a7c7e2ae3 pins harmonia-coupling at 228279dfb8a623ffe7cabaa5f7cc4c8e4140290b, whose manifest requires horae-time ^0.2.2; selected Horae 6e517ccf77f04714c74fc36f80bd5d1a524bcf70 provides 0.4.0, so that edge cannot resolve until CFDrs advances its Harmonia contract.
- blocker: CFDrs must advance its Harmonia requirement and lock to horae-time 0.4.0, and Metis PR #605 must reach its default branch; re-open when fetched defaults contain those changes.
- oracle: in every affected registered root Cargo.lock, each first-party Git Melinoe record is 0.10.1 and no first-party Git horae-time record is 0.2.2; registry packages and nested-workspace locks are outside this pointer-coherence check; atlas-stack-overlay.py check --pinned, atlas-pin-drift.py, and atlas-conformance.py check --revision <head> pass.
- next step: after the blocker revisions land, recompute the immutable provider closure, regenerate the overlay from that root candidate, and advance only the gitlinks the passing closure names.
