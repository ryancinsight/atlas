<a id="atlas-publish-001"></a>
## ATLAS-PUBLISH-001 — OIDC publish pipelines and Pages alignment [patch] — in-progress

- Policy: AGENTS.md engineering_gates "Publish pipelines". Wiring is agent work; registry-side toggles are user actions.
- Scope: (1) crates.io — add tag-triggered, environment-gated trusted-publishing workflows (`rust-lang/crates-io-auth-action`, `id-token: write`) to publishable stack crates, dependency-ordered with `cargo package` dry-run and semver gates; record per-crate "enforce trusted publishing" as a user checklist once each pipeline is green (disables token publishing registry-side). (2) PyPI — for the Python-binding crates, maturin-action matrix (manylinux2014 floor, `--compatibility pypi`, abi3 where the surface permits, sdist) with install/import/pytest wheel smoke before upload via the PyPI trusted-publisher flow. (3) Books — align CFDrs/kwavers/helios book workflows to the artifact flow (build + `mdbook test` → upload-pages-artifact → deploy-pages) if any still push a gh-pages branch or skip the test gate; new books inherit the same workflow.
- Acceptance: no long-lived registry token referenced in any CI secret; each wired pipeline dry-run green; book deployments artifact-based with the test gate; user-action list (registry enforcement toggles) recorded on the board.

### ATLAS-PUBLISH-001-CFDRS-PYPI — Add CFDrs abi3 PyPI trusted-publishing caller [patch] — in progress

- Owner: Atlas coordinator; claimed 2026-08-18.
- Scope: `repos/CFDrs/.github/workflows/python-release.yml`,
  `repos/CFDrs/crates/cfd-python/tests/`, the binding version surface, and the
  shared root `.github/workflows/python-wheels.yml` release-distribution
  contract. The caller uses the shared workflow at the exact Atlas graph
  revision and the provider's declared `cfd_python` import surface.
- Acceptance: the release-tag caller builds abi3 wheels with the manifest's
  PyO3 floor plus one validated source distribution, installs/imports the
  wheel, runs bounded value-semantic Python tests, and hands validated release
  artifacts to PyPI Trusted Publishing; no registry token or untested
  import-only path is introduced.
- Non-goals: registry-side trusted-publisher enforcement, a local publish,
  release/version changes, and unrelated CFDrs Rust or workflow cleanup.
- Verification: inspect the workflow's pinned actions and exact `atlas-ref`,
  run provider formatting and focused Rust checks, compile the binding test
  contract where the local Python/maturin toolchain permits, and validate the
  workflow statically.
- Provider implementation status: CFDrs commit `e7a1c9e8` on PR #360 already
  ships the abi3 typed boundary and GIL-release changes. Provider-local
  evidence is a release wheel containing `cfd_python.pyi` and `py.typed`,
  installed-wheel pytest `4/4`, strict mypy consumer validation, and complete
  runtime export coverage. Follow-up commit `a5a92bfc` pins the caller's
  `atlas-ref` to Atlas `ad22ec5e`. Hosted exact-head verification, merge, and
  post-merge evidence remain open; the Atlas CFDrs gitlink is unchanged.

### ATLAS-HELIOS-BOOK-TEST-002 — Enable Helios `mdbook test` in the shared Pages caller [patch] — done 2026-08-17

- Owner: Atlas coordinator; scope is the clean Helios workflow caller only.
- Evidence: clean-lane source `30a842cd7d7dee5ca9bda3e04e97fad966cebeee`
  enables the shared caller's `mdbook-test` input and merges at Helios default
  `679402ae166ce2b227d8d629bab877f1dcc45131`.
- Acceptance: met. The exact clean Helios book and hosted Pages build pass;
  hosted Rust, Python, and benchmark checks also pass. The external
  `recurseml/analysis` error remains report-only.
- Non-goals: peer-owned Helios source edits, book prose, generated figures,
  and the Kwavers/CFDrs caller sub-scopes.
- Re-open trigger: a book sample failure, shared workflow contract change, or
  provider caller that disables the test input.

