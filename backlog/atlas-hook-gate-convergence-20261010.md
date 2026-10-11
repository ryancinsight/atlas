<a id="atlas-hook-gate-convergence-20261010"></a>
## ATLAS-HOOK-GATE-CONVERGENCE-20261010 — Converge the hook-gate rollout, then sweep gitlinks [arch] — todo
outcome: one hook version stack-wide, hephaestus tip debt cleared, and every member gitlink at its default tip with a green atlas gate.
background: 2026-10-10 sweep measured 26 members on hook `42b9a37d` (shipped by unmerged atlas#450 `feat/atlas-cast-gate`, itself ratchet-red), owned gate plus hephaestus/leto on `ce9d73f9`, and hephaestus tip `07ca9f80` raising oversized_files 36→48, manifest_implementation 14→18, existence_only_assertions 0→3, type_suffixed_fns 7→29. No green subset exists; the ratchet is correctly blocking. CFDrs `4bf18cc6` CI is success; kwavers lock dirt was proven overlay-derived and restored.
acceptance: `member_gate_versions` = 1 at the sweep revision; hephaestus rows at or below baseline; atlas PR CI green; gitlinks = fetched default tips.
priority: correctness
needs: ATLAS-MEMBER-WIP-20261010-HEPHAESTUS
scope: scripts/git-hooks, repos/hephaestus, repos/leto, atlas#450
next: take over atlas#450 (stale since 2026-10-08): rebase onto origin/main, fix the ratchet failure, land; sync hephaestus+leto hooks; clear hephaestus debt at the owner; then land the gitlinks sweep.
basis: atlas `2038cfb70` (origin/main 2026-10-10); branch `build/gitlinks-sweep-20261010` holds the unpushed 27-member sweep.
