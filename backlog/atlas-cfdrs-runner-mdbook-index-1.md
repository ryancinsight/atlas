<a id="atlas-cfdrs-runner-mdbook-index-1"></a>
## ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1 — Close CFDrs runner-side mdBook index + ci.yml silent-drop [patch] — in-progress

- outcome: CFDrs `ci.yml` reliably schedules on PRs (no silent drop from an
  unallowlisted private composite action), and `book-pages.yml` builds
  without missing the parent atlas's `parity_artefacts/INDEX.md`.
- (b) closed: curl pre-step materializing `INDEX.md` landed in
  `book-pages.yml`; end-to-end emulation passes.
- next (a), admin-gated: allow-list `checkout-path-dependencies` (atlas
  composite action) in CFDrs Settings, or rewrite to a non-private-org
  action; acceptance is a visible `ci.yml` run in the branch's runs API.
- next (c), depends on (a)+(b): a re-run must produce the verbatim
  `DRIFT_DOCS_NOT_IN_SPECS: N ...` line at `Check book figures`, closing
  `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` (also the depends-on/follows link).
