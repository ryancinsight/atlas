<a id="ratchet-regression-set"></a>
## ATLAS-RATCHET-REGRESSION-SET-2026-09-08 - Seven ratchet regressions arrived with peers' merges [patch] - todo
Parent: [`#slop-burndown`](backlog.md#slop-burndown).
outcome: the fleet ratchet returns to zero regressions by fixing the debt, never by raising the baseline. Surfaced by advancing 23 gitlinks at `49db31fc9` — this debt already existed on members' default branches; the meta-repo simply could not see it while its pins were behind.
Regressions: aequitas `manifest_implementation` 0→2; apollo `existence_only_assertions` 0→1; apollo `manifest_implementation` 24→25; kwavers `oversized_files` 107→109; kwavers `target_forks` 0→1; ritk `oversized_files` 44→45; ritk `type_suffixed_fns` 69→76.
`aequitas`/`apollo` going 0→n matters most: a class at zero is a floor reached, and crossing back is worse than never clean. `kwavers/target_forks` is regrowth, not new: a deleted repo-local `target/` is back at 7.5 GB with a live cargo build in it — the generator survives cleanup and is the priority defect, not a repeat sweep (not deleted this time; build running).
