<a id="slop-burndown"></a>
## ATLAS-SLOP-BURNDOWN-2026-09-06 - Measured debt burn-down against the conformance ratchet [patch] - in-progress

Parent: [`#atlas-hygiene-baseline-001`](backlog.md#atlas-hygiene-baseline-001).

outcome: every class in `scripts/atlas-conformance.py` sits at or below its recorded baseline, measured against each member's live default branch (not a stale pinned gitlink), with the scan running in CI so the next increase fails immediately.

Largest classes measured 2026-09-06 (~4,000 sites, 26 members): `unwrap_production` 724, `manifest_implementation` 662, `oversized_files` 614, `allow_sites` 508 — kwavers alone holds a large share of each.

Open: the ratchet instrument must measure each member's actual default branch, and gitlink advances must be routine not an occasional sweep, or the gate reports on stale history (advancing 9 gitlinks surfaced kwavers +2 oversized files/+3 existence-only assertions and hephaestus +1 allow site the gate had missed). `type_suffixed_fns` needs an exemption mechanism first: many of ritk's 71 are protocol-fixed (e.g. `read_u8`/`read_u32` on a JPEG-2000 codestream), which `standards` already exempts. `apollo/excess_worktrees`: three trees, two peer-held with commits in the last 20 minutes — migrate at item completion, never under a running process. Shared build cache is 779 GB with no eviction cadence; filed as `#shared-cache-unbounded`.
