<a id="atlas-book-staging-2026-08-20"></a>
## ATLAS-BOOK-STAGING-2026-08-20 — Preserve Cargo artifact identity in mdBook gates [patch] — in-progress

outcome: the shared `book-pages.yml` workflow stages the exact hash-suffixed Cargo artifacts without collapsing duplicate crate versions by name (RITK's locked graph carries three `rand_core` versions; the old collapse rule produced `E0460`).

scope: root `.github/workflows/book-pages.yml`, ADR 0035, owner-local checklist entry. No provider source, lockfile, or book content.

status: RITK PR [#204](https://github.com/ryancinsight/ritk/pull/204) merged at default `b35c93313c06ea55fffa680a430378dda1df8e41`; CI, book, and live Pages (HTTP 200, expected title) confirmed; Atlas pointer advanced to `b35c9331`. Helios and Tyche book/Pages deployments independently confirmed green at their exact heads.

next: Themis default `c76a55e5eb9988b48bba69e67d6e07ce5fe55ea8` has CI/MSRV/book-build green but its Pages deployment (run `32402752669`) is still queued — confirm terminal before treating as live. Kwavers resolves to `78af725e749c8ec4fd756d55091d557ea635aac2`; its latest hosted workflow set targets the predecessor `b5b4fb0614ad3238ab95ff092cebd5977a201b22`, so it cannot yet authorize advancing the stale Atlas pointer `459f18ce` — needs a fresh hosted run at the current head.
