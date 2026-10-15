# Atlas workflow correction checklist

Target version: Unreleased shared-workflow interface [minor]; no package release.

Sprint phase: Closure — ATLAS-BOOK-PUBLICATION-AUTHORIZATION; review pending

- [x] [minor] Inspect current remote bases, owners and caller; use isolated
  standalone review clones without changing active stack lanes.
- [x] [minor] Specify the publication predicate and existing-consumer
  equivalence in ADR 0035 before adopting it in Aequitas.
- [x] [minor] Reproduce the missing authorization guard on the unchanged base.
- [x] [minor] Add the optional deployment gate without changing book tests,
  output validation, artifact integrity, permissions or environment protection.
- [x] [minor] Pass six focused static contracts, all 56 workflow regression
  cases (zero skips), 17 book-audit cases and actionlint 1.7.12 on the shared
  workflow. YAML differential verification finds only the three authorization
  additions: input declaration, Pages configuration guard and deployment guard.
- [ ] [minor] Review the exact diff and publish independent draft review changes.
- [ ] [minor] Complete hosted checks and separately authorized integration.

Release boundary: this checklist grants no merge, package-publication or
Pages-deployment authorization. Publication acceptance remains unexecuted.

Executed locally at the candidate based on `799880c2`:
`python3 -m unittest discover -s scripts/tests -p '*workflow*.py'`,
`python3 -m unittest discover -s scripts/tests -p 'test_atlas_book_gate_audit.py'`,
`actionlint .github/workflows/book-pages.yml`, and `git diff --check`.
Test subprocesses have a 60-second bound. Shellcheck/pyflakes are unavailable;
no shared shell or Python step changes. The full Atlas script suite and live
book/deployment jobs are outside this local workflow-only verification.
