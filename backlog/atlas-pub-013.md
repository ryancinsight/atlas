<a id="atlas-pub-013"></a>
## ATLAS-PUB-013 — Advance member SemVer-gate pins to the bump guard [patch] — todo
- outcome: every member caller of `ryancinsight/atlas/.github/workflows/semver-gate.yml` on `pull_request` pins an Atlas commit that carries the `bump-guard` job (ATLAS-PUB-011), so a member PR that changes a published crate's source under an indexed version fails.
- scope: `repos/*/.github/workflows/*.yml` lines `uses: ryancinsight/atlas/.github/workflows/semver-gate.yml@<sha>` (consus `ci.yml` pins 50802ef4c975bdb1e668b94a700d8310f0348e9c, measured 2026-10-12). No committed tool advances these pins: `scripts/atlas-semver-gate-adopt.py` inserts the call and its `--update` rebuilds the adoption branch, not the SHA. Mechanize the advance there or in a sibling, per operation: toil automation.
- acceptance: per member, a PR run lists the `Version bump guard` job green, with its PR's touched crates in the run summary; a stack grep finds no `semver-gate.yml@` pin older than the guard commit.
- next: once the guard PR lands, record its merge commit here, then open one pin-advance PR per member in provider-first order.
- priority: correctness; needs: ATLAS-PUB-011's guard PR merged (the pin names its commit).
- links: [ATLAS-PUB-011](../backlog.md#atlas-pub-011), [ATLAS-PUB-010](../backlog.md#atlas-pub-010).
