<a id="crlf-stored-blobs"></a>
## ATLAS-CRLF-STORED-BLOBS-2026-09-08 - Committed blobs contradict the declared line-ending policy [patch] - in-progress 2026-09-08 (renormalizations in review)
Parent: [`#slop-burndown`](backlog.md#slop-burndown).
outcome: every member's stored blobs match its declared `.gitattributes` policy, so an edit renders as the change it is rather than a whole-file rewrite (CFDrs measured: an 83-line change diffed as 1253 lines).
Measured fleet-wide 2026-09-08 (`git ls-files --eol`, index form): 1,596 CRLF-stored blobs across 7 members — CFDrs 1,588 (the incident), leto 3, consus/helios/hephaestus/moirai/kwavers 1 each (copy-propagated `python-release.yml`). Counted class `crlf_stored_blobs` added to `atlas-conformance.py`; baseline ratcheted at 1,596.
Open: renormalization PRs (`git add --renormalize .` only, zero content change, must land alone) are in review: CFDrs#422, consus#71, helios#95, hephaestus#294, leto#179. moirai and kwavers follow once their trees go quiet (peer edits in flight at scan time).
