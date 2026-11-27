<a id="atlas-judge-status-workflow"></a>
## ATLAS-JUDGE-STATUS-WORKFLOW — No stack workflow posts the `judge` commit status [verification] [patch] — todo
- outcome: a stack-owned pull-request workflow posts `judge` per git_discipline: cadence (success on a ready PR without the `judge-required` label, nothing on a labeled head, failure on `labeled`).
- evidence (origin/main b334401f2fcf): `git grep -n -E 'statuses: write|context=judge' origin/main -- .github` prints nothing, so no status exists for a ruleset to require; athena `main` requires
  `Lockfile integrity / Lockfile integrity`, `supply-chain` and `verify` (read 2026-11-27), and its item `ATHENA-JUDGE-REQUIRED-20261127` stays blocked.
- oracle: `git grep -l 'statuses: write' -- .github/workflows` lists the workflow (nothing today); a test of its parsed YAML asserts no other write scope, no `pull_request_target`, no PR checkout, and the table above.
- basis: b334401f2fcf; priority: verification; needs: none; scope: `.github/workflows/`, `scripts/tests/`; next step: write the decision-table test, then the workflow; labels are read through the API.
