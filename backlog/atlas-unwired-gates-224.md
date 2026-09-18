<a id="atlas-unwired-gates-224"></a>
## ATLAS-UNWIRED-GATES-224 — Instruments that exist, pass, and are never run [patch] — in-progress

outcome: every committed verification script is either actually wired into a workflow, or deliberately documented as an orient-time/local-only check — so a green, unrun gate can't hide a real defect. Pattern to keep applying: "a gate that has never failed may never have run" — check `grep -ohE "scripts/[a-z-]+\.py" .github/workflows/*.yml` against `ls scripts/*.py`.

delivered: `atlas-registry-metadata.py` wired in `572a585` (had never run; on first run found kwavers exceeding the crates.io keyword cap and using a nonexistent category slug, fixed in kwavers `1aa24beb7`; degrades to `UNVERIFIED` at exit 0 on unreachable taxonomy so it can't flake on crates.io availability). `atlas-lane-audit.py` confirmed deliberately unwired — a CI clone has one working tree so it would pass vacuously in CI; it stays an orient-time/replenishment-time check, findings carried on the board via `-222`.

open: `atlas_scattered_containers_classify.py` — assess whether it's CI-valid (wire it) or inherently local (document it like the lane audit); those are the only two valid answers.
