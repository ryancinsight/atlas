<a id="crlf-stored-blobs"></a>
## ATLAS-CRLF-STORED-BLOBS-2026-09-08 - Committed blobs contradict the declared line-ending policy [patch] - in-progress 2026-09-08 (renormalizations in review)

Parent: [`#slop-burndown`](backlog.md#slop-burndown).

- **outcome:** every member's stored blobs match its `.gitattributes`, so an
  edit renders as the change it is rather than as a whole-file rewrite.
- **measured 2026-09-08 in CFDrs:** `.gitattributes` declares
  `* text=auto eol=lf`, and **61 of 141 `cfd-1d/src` `.rs` files are stored
  with CRLF**. The policy exists; the blobs predate it and were never
  renormalised.
- **the cost is review, not correctness.** Editing one such file with any
  LF-writing tool turns an 83-line change into a 1253-line diff. That is not a
  cosmetic annoyance: a reviewer cannot see the change, and an over-broad
  staging sweeps whole-file rewrites into unrelated commits. It is also the
  source of the CRLF warnings on nearly every commit in this stack.
- **the fix is one command per member** — `git add --renormalize .` — but it
  must land as its *own* change, on a quiet tree, because it touches every
  affected file and would swallow anything committed with it. That is the
  opposite of the situation it creates today, where it swallows things
  silently.
- **check the other members first:** the conformance scan reports
  `gitattributes_missing = 0` fleet-wide, so every member declares a policy.
  Whether the blobs match it is a different question and is not currently
  measured. Worth adding as a counted class before doing the renormalisation,
  so the ratchet holds it at zero afterwards.
- **measured fleet-wide 2026-09-08 (`git ls-files --eol`, index form):**
  **1,596 blobs across 7 members** — CFDrs 1,588 (the incident), leto 3,
  consus/helios/hephaestus/moirai/kwavers 1 each (the copy-propagated
  `.github/workflows/python-release.yml` template). The meta repo is clean.
- **counted class delivered:** `crlf_stored_blobs` in `atlas-conformance.py`,
  measured from the index, not the worktree. On the recorded-revision scan
  path it reads the pinned tree through a temporary `GIT_INDEX_FILE` against
  the live object store, so archived snapshots (which carry a resolving-nowhere
  `.git` marker) and behind/dirty checkouts both measure correctly — the first
  implementation read 0 for every archived member, which is exactly the kind
  of silent materialization-path dependence the fleet scan must not have.
  Baseline ratcheted at 1,596 via `--accept-raises` (new class, first
  measurement). moirai and kwavers carried live peer edits at scan time and
  are counted from their pinned revisions like everyone else.
- **renormalizations in review (one standalone PR per member, `git add
  --renormalize .` only, zero content change, must land alone):**
  CFDrs#422 (1,588 files, 945,678 lines each way, `--ignore-cr-at-eol` diff
  empty), consus#71, helios#95, hephaestus#294 (default branch is `master`),
  leto#179. moirai and kwavers follow once their trees go quiet.

