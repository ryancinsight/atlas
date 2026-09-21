<a id="atlas-overlay-005"></a>
## ATLAS-OVERLAY-005 — Clear first-party rev pins across the stack [patch] — in-progress
- **outcome:** no first-party dependency is pinned via `rev =`; the stack `[patch]` overlay unifies every crate via bare-URL git+version sources.
- **open:** `atlas-stack-overlay.py check` reports one coherence defect — Athena's peer-dirty checkout is 3 commits behind `origin/main`, lock pins Hermes `0.6.0` vs. local provider `0.7.0`. Outside this item's provider set; re-run after CFDrs merges and Athena reconciles.
- **mechanism to land:** wire `atlas-stack-overlay.py check` into CI so a lock move without a re-derived patch block is caught at the source.
