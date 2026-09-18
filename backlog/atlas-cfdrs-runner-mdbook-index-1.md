<a id="atlas-cfdrs-runner-mdbook-index-1"></a>
## ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1 — Close CFDrs runner-side mdBook index + ci.yml silent-drop [patch] — in-progress

- Owner: Codex `/root`; last-update: 2026-07-26;
  scope: `repos/CFDrs/.github/workflows/ci.yml` + `repos/CFDrs/.github/workflows/book-pages.yml`
  + `repos/CFDrs/docs/book/SUMMARY.md` (Appendix F cross-reference); the
  parent atlas `D:/atlas/parity_artefacts/INDEX.md` is the canonical
  sibling artifact cf. `ATLAS-PARITY-HTML-RETIRE-1`.
- Context: throwaway drift-fixture probe PR #320 (run `30217224003`)
  revealed TWO runner-side defects on the post-SIBLING-CHECKOUT-1 +
  post-COEQ-BLOCKER-1 CFDrs `origin/main` HEAD `1a7aa1d6`:
  - **(i)** `ci.yml` is registered (workflow id `319648723`, `state='active'`)
    but silently drops at queue time. GH Actions does NOT create a
    `ci.yml` run for PR #320, despite `pull_request` event firing the
    `book-pages.yml` sibling workflow on the same DRAFT PR. Most likely
    cause: the cross-repo composite action
    `ryancinsight/atlas/.github/actions/checkout-path-dependencies@51d8600cf3077e6ad6aafa5603b3289444b1719f`
    requires explicit allow-listing under CFDrs repo Settings -> Actions
    -> General when the consuming repo is not on the same plan tier.
    GH silently drops runs that reference unallowed private actions.
  - **(ii)** `book-pages.yml`'s `Build book` (mdbook build) step fails
    with `ERROR failed to read chapter '../../../parity_artefacts/INDEX.md'
    -- os error 2` because the runner's clean clone of `ryancinsight/CFDrs`
    ships ONLY the CFDrs source tree; the parent atlas's `parity_artefacts/INDEX.md`
    is not materialized (the existing `checkout-path-dependencies`
    action only materializes sibling sub-repo crates, NOT the parent
    atlas directory). This is the 3rd instance of the "sibling cross-reference
    missing in clean runner clone" class after the cargo path-dep
    (`ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1`) issue and the older local
    coeus-core path-dep (`ATLAS-CFDRS-COEQ-BLOCKER-1`).
- Acceptance:
  - (a) **[ADMIN-GATED]** Repo-admin Settings -> Actions -> General
    confirms `ryancinsight/atlas/.github/actions/checkout-path-dependencies`
    is allow-listed, OR the workflow invocation is rewritten to use a
    non-private-org composite action. The throwaway re-run produces a
    visible `ci.yml` run in the runs API for the branch (not zero).
  - (b) **[LOCALLY-VERIFIABLE]** `book-pages.yml` gains a pre-step that
    materializes `parity_artefacts/INDEX.md` in the runner workspace
    (via `actions/checkout` of the parent atlas repo with
    `path: ../parity_artefacts/` + `sparse-checkout: INDEX.md`, OR
    via `curl`-based raw download from the GitHub raw content URL
    against a pinned commit). Throwaway re-run shows `Build book` step
    conclude `success` (no `os error 2`).
  - (c) **[DEPENDS ON (a)+(b)]** The throwaway re-run produces the
    verbatim
    `DRIFT_DOCS_NOT_IN_SPECS: N docs figure link(s) missing from FIGURE_SPECS:`
    log line at the `ci.yml` `Check book figures` step. Captured log
    line ends the ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER gate.
- Acceptance-status disambiguation: (b) is the smaller, more deterministic
  fix (the SUMMARY.md/parent-atlas cross-reference is well-understood).
  (a) requires action outside the CFDrs repo and may need to be
  coordinated with the atlas-super-project admin. (c) inherits from (a)+(b).
- Acceptance-status disambiguation: (b) is the smaller, more deterministic
  fix (the SUMMARY.md/parent-atlas cross-reference is well-understood).
  (a) requires action outside the CFDrs repo and may need to be
  coordinated with the atlas-super-project admin.
- Risk/change class: `[patch]`; CI scaffolding only, no production-code
  change on the CFDrs application tree or on the parent atlas's
  `parity_artefacts/INDEX.md` (the canonical parity archive remains the
  consumer).
- Dependencies: tracks `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` (downstream
  consumer; the verbatim `DRIFT_DOCS_NOT_IN_SPECS: N` log capture gate).
  Follows `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1` (cargo path-dep closure)
  + `ATLAS-CFDRS-COEQ-BLOCKER-1` (coeus gitlink closure).
- Discovered-by: throwaway probe PR `ryancinsight/CFDrs#320`,
  run `30217224003`, 2026-07-26 (this delivery). Capture archive at
  `D:/atlas/verification/_throwaway_logs/cfdrs-pr320-run-30217224003-*/build/5_Build book.txt`.
- Evidence limit: per-step `conclusion=failure` JSON + verbatim mdbook
  error log; no production-code delta, no perf claim.
- Delivery (2026-07-27):
  - (b) closed: third-iteration curl pre-step landed in
    `D:/atlas/repos/CFDrs/.github/workflows/book-pages.yml`; runner-defensive
    invariants (`set -euo pipefail`, `curl --max-time 60 --retry 3 --retry-delay 5`,
    `printf | sha256sum -c` against certificate
    `18b7d9def0625f312776e15b2f70b681f38cbcb8838c9a9fd0b6ffb38af50a5a`). Pinned
    ref `51d8600cf3077e6ad6aafa5603b3289444b1719f` consistent with `ci.yml`
    atlas_ref. Code-reviewer-minimax-m3 returned GO for closing (b).
    End-to-end local emulation passes (`curl_exit=0`, `sha256_exit=0`).
  - (a) admin-gated remains open: `ci.yml` silent-drop on Ryancinsight
    DRAFT PRs unconfirmed root cause; tracked via
    `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` (the (c) follow-on requires
    both (a) + (b) closures).

