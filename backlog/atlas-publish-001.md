<a id="atlas-publish-001"></a>
## ATLAS-PUBLISH-001 — OIDC publish pipelines and Pages alignment [patch] — in-progress

outcome: (1) crates.io — trusted-publishing workflows (`rust-lang/crates-io-auth-action`, `id-token: write`) on publishable stack crates, dependency-ordered with `cargo package` dry-run + semver gates, no long-lived registry token in CI; (2) PyPI — maturin-action matrix (manylinux2014 floor, abi3 where the surface permits, sdist) with install/import/pytest smoke before trusted-publisher upload for Python-binding crates; (3) Books — CFDrs/kwavers/helios book workflows on the artifact flow (build + `mdbook test` → upload-pages-artifact → deploy-pages).

acceptance: no long-lived registry token in any CI secret; each wired pipeline dry-run green; book deployments artifact-based with the test gate; registry-enforcement-toggle checklist recorded on the board.

open — ATLAS-PUBLISH-001-CFDRS-PYPI: CFDrs abi3 PyPI trusted-publishing caller (`repos/CFDrs/.github/workflows/python-release.yml`). PR #360 ships the abi3 typed boundary + GIL-release changes (installed-wheel pytest 4/4, strict mypy, `cfd_python.pyi`+`py.typed`); follow-up `a5a92bfc` pins the caller's `atlas-ref` to Atlas `ad22ec5e`. Hosted exact-head verification, merge, and post-merge evidence remain open; Atlas CFDrs gitlink unchanged.

closed: ATLAS-HELIOS-BOOK-TEST-002 (Helios `mdbook test` in the shared Pages caller) — done 2026-08-17, merged at Helios default `679402ae166ce2b227d8d629bab877f1dcc45131`.
