<a id="atlas-arch-008-running-in-place-225"></a>
## ATLAS-ARCH-008-RUNNING-IN-PLACE-225 — The conversion converts and re-accumulates at the same rate [patch] — in-progress

`atlas_scattered_containers_classify.py` has a gate mode
(`--verify-oracle`) and a committed oracle
(`scripts/oracles/arch-008-production-sites.txt`, 243 sites). Running it for
what appears to be the first time:

> **35 sites now in production but missing from the oracle; 36 oracle sites
> no longer in production.**

Net **−1**. The interesting number is not the total, it is the pair: 36 sites
were genuinely converted while 35 new pointer-scattered containers landed. So
`ATLAS-ARCH-008` is not stalled and not regressing — it is **running in
place**, and has been doing so unobserved because nothing ran the verifier.
The inflow is spread across seven members: consus 8, gaia 7, CFDrs 7, coeus 5,
ritk 4, moirai 2, kwavers 2.

A conversion item cannot converge while new instances arrive at the
conversion rate. Wiring the verifier is what stops the inflow, and it matters
more than clearing the backlog.

**Deliberately not wired yet, and deliberately not regenerated.** Wiring it
now reds CI on 35 pre-existing sites; regenerating the oracle to make it pass
would absorb 35 new production sites into the accepted set, which is exactly
the baseline laundering fixed in `-216` this same day. The order is: justify
or convert the 35, then wire.

Also worth noting: every write of this oracle has landed inside an unrelated
chore commit — it was created by `5956d02` ("chore(gitlinks): Advance ritk
…"), the same scope-creep commit that duplicated `parity_artefacts`, and
touched before that by two more gitlink commits. Derived state has been
riding along in commits whose messages do not mention it.

- Acceptance: the 35 are converted or individually justified in the oracle;
  ~~`--verify-oracle` wired into `atlas-conformance.yml`~~ **done by a peer,
  2026-08-19**; the oracle only ever regenerated in a commit whose subject
  says so.

**A peer wired the gate while this was being written, and did it the right
way round.** `atlas-conformance.yml` now runs `--verify-oracle`, with the
oracle path and the classifier added to the trigger list. Critically they
**did not regenerate the oracle** to make the new gate pass — it is still 243
lines and still reports the same 35 — so the gate goes red and forces the
conversion instead of absorbing it. That is the opposite of the `e9c5821`
baseline-raise, and the right call.

Their step comment also corrects an assumption in my measurement: CI scans a
**clean checkout** pinned to the root gitlinks, while my numbers came from
live worktrees carrying peer WIP. I checked the 20 sampled drift sites and
all are **tracked and clean** — real committed content, not WIP — so the
drift is genuine, though the exact CI count may differ where a member's
worktree and its recorded gitlink disagree. The next PR run is the
authoritative number.

