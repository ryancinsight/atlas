<a id="atlas-leto-cast-row-001"></a>
## ATLAS-LETO-CAST-ROW-001 — The leto-ops cast row is below the count at its pin [tightening][patch] — todo
- Outcome: the committed leto-ops row covers the count measured at the pinned leto revision, so the bare-cast gate judges a leto push against a row the pin has not exceeded.
- Evidence: the committed row is 590, measured at leto `6d0eca39`; the stack's leto pin is `5051cd957`, where a fresh workspace measurement reports 715. Regenerating the baseline to 715 is refused: `atlas_cast_gate.py ratchet` holds that "a row may fall or be dropped; it may not rise", and the conformance workflow runs that ratchet on every pushed range. A raw `as` count over leto-ops sources — a proxy for the lint count, not the lint count itself — rose 560 to 686 across the same two revisions, so the rise is in the sources and not in the measurement.
- Oracle: `python scripts/atlas_cast_gate.py measure --member leto` at the pinned revision reports a count at or below the committed row, or the committed row falls to the measured count.
- priority: correctness
- needs: none
- scope: `repos/leto/crates/leto-ops`, `scripts/cast-baseline.json`
- Next step: convert the bare `as` casts in leto-ops until the workspace-measured count is at or below the committed row, then regenerate the baseline so the row and its basis agree.
- basis: atlas origin/main 6b450d913, leto origin/main 5051cd957 (2026-10-20)
