<a id="atlas-kwavers-vis-config-2026-08-25"></a>
## ATLAS-KWAVERS-VIS-CONFIG-2026-08-25 — Make visualization selection and quality single-source [major] — blocked

- **Owner:** current session. **Scope:** Kwavers visualization configuration,
  renderer quality propagation, focused tests, Rustdoc/README/CHANGELOG, and an
  indexed Kwavers ADR. **Non-goals:** no provider ownership change, fallback,
  rendering algorithm change, or backend-specific configuration in
  `kwavers-analysis`.
- **Outcome:** top-level Kwavers `VisualizationBackend::{Leto, Hephaestus}` is
  the only backend-selection source. The ignored `gpu_enabled` boolean and
  duplicate `render_quality` field are deleted; adaptive quality changes the
  renderer configuration that subsequent frames use.
- **Acceptance oracle:** stack-wide search finds no `gpu_enabled` or
  `render_quality`; backend conformance and real Hephaestus pipeline tests
  remain value-correct; focused analysis tests prove quality transition and
  renderer propagation; formatting, warning-denied Clippy, Nextest, doctests,
  Rustdoc, and SemVer classification pass on the exact delivered revision.
- **Risk/dependencies:** `[major]` because two public configuration fields are
  removed. The active Proteus package-rename branch touches only manifests and
  lockfiles; visualization source remains disjoint. No release is authorized.
- **Delivered evidence:** Kwavers PR #638 merged as `00455130f` from reviewed
  head `b2a156215`; the independent judge found and then cleared one stale
  disabled-test block. Nextest passes 783 GPU-feature analysis tests, 744
  default analysis tests, and the four focused quality regressions after the
  judge fix. Formatting, doctests, warning-denied Rustdoc, standalone locked
  metadata, ADR-index validation, and the current-default real Hephaestus
  hardware test pass. `cargo-semver-checks` against the buildable
  dependency-only prerequisite baseline reports exactly the two removed fields
  as a required major change. The post-merge matrix is terminal with 33 passes,
  two expected skips, zero failures, and one cancellation: GPU and CUDA builds,
  all feature combinations, stable/beta/nightly, Miri, security, docs, coverage,
  quality, and validation pass; `Benchmark Runtime Smoke` spent 29 minutes in
  its Criterion command and hit the job's 30-minute timeout. Atlas gitlink
  `repos/kwavers` remains at `8ef48975c`. **Blocker/re-open trigger:** correct
  the cold-build benchmark-smoke instrument without raising its bound, then
  obtain a terminal green run and advance the gitlink to that fix.

