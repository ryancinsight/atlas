<a id="atlas-book-staging-2026-08-20"></a>
## ATLAS-BOOK-STAGING-2026-08-20 — Preserve Cargo artifact identity in mdBook gates [patch] — in-progress

The shared `book-pages.yml` workflow currently strips Cargo metadata hashes and
keeps the first artifact for each crate name. RITK's exact default book run
`32404089897` disproves that selection rule: its locked graph contains
`rand_core` 0.6.4, 0.9.5, and 0.10.1, and the staged `rand_core` metadata does
not match `ritk_statistics`, producing `E0460` before the book example runs.

**Scope:** root `.github/workflows/book-pages.yml`, ADR 0035, and this item's
owner-local checklist entry. No provider source, lockfile, or book content.

**Acceptance:** the reusable workflow stages the exact hash-suffixed Cargo
artifacts without collapsing duplicate crate versions; a local RITK mdBook
probe with duplicate `rand_core` artifacts passes; YAML/whitespace checks pass;
the changed workflow is adopted by a rerun of the RITK default book gate.

**Owner:** current Atlas session. **Claimed files:**
`.github/workflows/book-pages.yml`, `docs/adr/0035-shared-publication-pipelines.md`,
`backlog.md`, `checklist.md`. RITK PR
[#204](https://github.com/ryancinsight/ritk/pull/204) merged from exact head
`9bc47d42f0d6050f4a68661c01d45806d41e583f` at default
`b35c93313c06ea55fffa680a430378dda1df8e41`. Its CI and book checks pass;
the current default CI and Pages deployment pass, and live Pages returns HTTP
200 with the expected RITK title. The Atlas pointer advances to `b35c9331`.
`recurseml/analysis` is report-only.

Themis's corresponding post-merge evidence is terminal for the build jobs:
default head `c76a55e5eb9988b48bba69e67d6e07ce5fe55ea8` has successful CI
`32402753573`, MSRV `32402753617`, and `deploy / Build book` job
`96534588862` in run `32402754181`. The Pages deployment remains queued in
run `32402752669` (job `96545229314`); this is deployment-pending evidence,
not a live Pages claim.

The exact-head collection also confirms Helios default
`7ff72e37889594b6592e1f8b8b169834765f7851` with successful CI
`32393592276` and mdBook deployment `32393593050`, and Tyche default
`10410f2de1ce1529ecbff50fa740b23a1c8f77b9` with successful CI
`32394888136` and Pages deployment `32394886461`. Kwavers currently resolves
to `78af725e749c8ec4fd756d55091d557ea635aac2`; its latest hosted workflow
set targets the predecessor `b5b4fb0614ad3238ab95ff092cebd5977a201b22`, so
those runs cannot authorize the stale Atlas pointer `459f18ce`.

