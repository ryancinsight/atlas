<a id="atlas-judge-status-workflow"></a>
## ATLAS-JUDGE-STATUS-WORKFLOW — No stack workflow posts the `judge` commit status [verification] [patch] — todo
- outcome: a stack-owned pull-request workflow posts `judge` per git_discipline: cadence (success on a ready PR without the `judge-required` label, nothing on a labeled head, failure on `labeled`).
- evidence (origin/main b334401f2fcf): `git grep -n -E 'statuses: write|context=judge' origin/main -- .github` prints nothing, so no workflow posts `judge` (statuses exist only where a judge posts one by hand, e.g. `success` on e493b47b385c); athena `main` requires
  `Lockfile integrity / Lockfile integrity`, `supply-chain` and `verify` (read 2026-11-27), and its item `ATHENA-JUDGE-REQUIRED-20261127` stays blocked.
- oracle: `git grep -l 'statuses: write' -- .github/workflows` lists it (nothing today); a parsed-YAML test asserts no other write scope, no `pull_request_target`, no PR checkout, no `github.event.pull_request.labels`, a labels read through the API, and that API labels override payload labels.
- basis: b334401f2fcf; priority: verification; needs: none; scope: `.github/workflows/`, `scripts/tests/`; next step: write the decision-table test, then the workflow.
