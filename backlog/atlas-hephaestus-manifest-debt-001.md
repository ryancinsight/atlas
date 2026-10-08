<a id="atlas-hephaestus-manifest-debt-001"></a>
## ATLAS-HEPHAESTUS-MANIFEST-DEBT-001 — Clear the manifest-impl and type-suffixed-fn debt at the master tip [patch] — todo
- Outcome: hephaestus at its master tip measures `manifest_implementation` 14 and `type_suffixed_fns` 7 again, so the meta pin advances past 7f27fd4a and the drift waiver is deleted.
- Evidence: the meta pre-push conformance check (baseline a6e3ef22, revision with pin ae24d07c) reports `hephaestus/manifest_implementation: 14 -> 16` and `hephaestus/type_suffixed_fns: 7 -> 8` as ratchet violations; member CI at the tip is green, so this is lint debt, not breakage.
- Oracle: `python scripts/atlas-conformance.py check` on the member tip shows both classes back at 14/7, and the member's own lint gate stays green.
- priority: verification
- needs: none
- scope: repos/hephaestus at origin/master, the two new manifest implementation blocks and the one new type-suffixed fn.
- Next step: worktree at origin/master (the main checkout sits on a peer's 44-ahead feature branch — do not move it), relocate the impl blocks to leaf modules and rename the suffixed fn to its domain term, open a hephaestus PR, and on merge advance the meta pin and delete the waiver.
