<a id="atlas-dependency-cohort-20261127"></a>
## ATLAS-DEPENDENCY-COHORT-20261127 — Land the Melinoe 0.10.1 dependency cohort [patch] — blocked
- priority: correctness; needs: none; scope: repos/*, .cargo/config.toml
- outcome: Atlas records the landed Moirai, Metis, RITK, and Melinoe changes as one reproducible gitlink cohort whose first-party package versions agree with every selected standalone lock.
- evidence (basis: ddf18d670ace9e74f1ba935563e7259f4780cc3c): selecting the 18 landed Melinoe consumer sweeps plus current CFDrs, Ares, Hephaestus, and Prometheus leaves one mismatch: CFDrs pins a harmonia-coupling manifest that requires horae-time ^0.2.2, while the selected Horae provider is 0.4.0.
- blocker: CFDrs must advance its Harmonia requirement and lock to horae-time 0.4.0, and Metis PR #605 and RITK PR #1151 must reach their default branches; re-open when fetched defaults contain those changes.
- oracle: the proposed root revision selects no Melinoe 0.10.0 or horae-time 0.2.2 package in the affected locks, and atlas-stack-overlay.py check --pinned, atlas-pin-drift.py, and atlas-conformance.py check --revision <head> pass.
- next step: after the blocker revisions land, recompute the immutable provider closure, regenerate the overlay from that root candidate, and advance only the gitlinks the passing closure names.
