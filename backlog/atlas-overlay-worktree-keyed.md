<a id="atlas-overlay-worktree-keyed"></a>
## ATLAS-OVERLAY-WORKTREE-KEYED-2026-09-06 — The overlay gate compares a committed artifact against a generation from uncommitted inputs [arch] — review

outcome: the `atlas-stack-overlay` gate is satisfiable in steady state — closure discovery matches what CI validates against, so a regeneration by any developer and by CI produce the same bytes.
- Resolution: the gate is keyed to member *default heads* (`submodule update --remote`), not to gitlinks — a gitlink-keyed experiment was tried and reverted (it made the overlay stop pointing at local trees, defeating its purpose) before the correct key was found. Regenerated and committed at `49d633852`.
- Root cause found: six providers (leto, ritk, coeus, hephaestus, consus, tyche) had their `[patch]` sections silently withheld by lag-aware emission and never regenerated after the Moirai sweep made them satisfiable — the overlay was silently not applying to six providers.
- Confirmed 2026-09-09: the gate run on `49d633852` no longer emits the `OVERLAY:` clause; remaining failure is one requirement lag and eight locks, both owned by the apollo pin (apollo#385).
- Standing risk: a developer holding an unpushed version bump regenerates differently from CI — expected and transient (the bump must be pushed).
- Lease: `scripts/atlas-stack-overlay.py`, integrator claude-opus-5, last-update 2026-09-06.
