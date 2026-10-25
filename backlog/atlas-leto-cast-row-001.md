<a id="atlas-leto-cast-row-001"></a>
## ATLAS-LETO-CAST-ROW-001 — The kwavers-math cast row is below the count at its pin [tightening][patch] — todo
- outcome: `kwavers-math`'s committed row covers the count measured at the pinned kwavers revision, so a kwavers-math-touching push is judged against a row the pin has not exceeded.
- delivered 2026-10-25: the leto half closed. The finite-range recovery campaign (leto 3ebe92c) drove leto-ops from 715 bare casts to 543, and the same sweep regenerated the leto rows at the recorded pin 7dbbb7e: leto 116 -> 111, leto-ops 590 -> 543, leto-python 10 unchanged. A leto push now passes the cast gate on content, not on row slack.
- remaining: kwavers-math measures 186 at the pin against a committed row of 183 — the three signed-index conversions (`idx as isize`), whose correct form is a checked `isize::try_from`; that needs the surrounding functions to report the failure, so it is its own increment. kwavers held live peer lanes when measured; claim the increment when the member quiets.
- oracle: `python scripts/atlas_cast_gate.py --cargo-config <overlay-free> measure --member kwavers --export <export of the pin>` reports kwavers-math at or below 183, or the row falls to the measured count.
- priority: correctness; needs: none; scope: `repos/kwavers/crates/kwavers-math`, `scripts/cast-baseline.json`
- basis: kwavers pin 65e666f82 (2026-10-25)
