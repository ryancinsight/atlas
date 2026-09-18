<a id="atlas-gaia-book-gate-2026-08-20"></a>
## ATLAS-GAIA-BOOK-GATE-2026-08-20 — Add value-semantic book execution [patch] — in-progress

The fetched Gaia default `dbed97a63434a21b1b9dcd01d634276aaec99e37` invokes
`mdbook test docs/book`, but the book contains zero Rust fences. Its mesh-gallery
generator is executable but does not provide mdBook contract coverage. This is
a bounded documentation/test increment; it does not change mesh algorithms,
figures, or the peer-owned Gaia README, CHECKLIST, or untracked backlog.

**Owner:** current Atlas session. **Claimed lane:**
`D:\\atlas\\worktrees\\gaia-book-gate`. **Claimed files:** one existing Gaia
book chapter, one included example source if the book convention requires it,
and Gaia's owner-local PM entry. **Acceptance:** one real input-sensitive Gaia
API example is included by the book, `mdbook test docs/book` executes it with a
value-semantic assertion, strict links and `mdbook build` pass, and the change
is published and verified at its exact provider head. No `rust,ignore` or
existence-only assertion satisfies the item. PR [#33](https://github.com/ryancinsight/gaia/pull/33)
is published at exact head `39a4f7fb0349bbd427fd12ddd99b0acc6baa654c` after
repairing the book workflow to capture only the current Cargo compiler-artifact
paths before staging them for mdBook. The earlier book run `32417028130`
tested the pre-repair merge ref and failed with `E0463: can't find crate for
gaia`; the intermediate run `32459250549` is superseded because its broad
staging step could select multiple cached Gaia revisions. A local run against
the shared Atlas cache reproduced that cache-sensitive `E0464: multiple
candidates` condition. The exact-one-library guard is now also enforced.
Replacement CI run `32473606516` is pending and book run `32473606617` is
queued at the exact current head; the earlier replacement runs
`32473502019`/`32473502075` are superseded. Hosted clean-runner execution
remains the required staging evidence. Local `mdbook build docs/book` and link
checking pass at the repaired lane head.
`recurseml/analysis` is report-only.
- **Closed (2026-08-22):** PR #33 merged at Gaia default `9b476fec` with the
  expected-head guard; both exact-head runs `32473606516`/`32473606617`
  terminal success, post-merge main CI and mesh book runs terminal success,
  and live Pages returns HTTP 200 with the expected title. The Atlas gitlink
  advanced to `9b476fec` (commit `0f58972`).

