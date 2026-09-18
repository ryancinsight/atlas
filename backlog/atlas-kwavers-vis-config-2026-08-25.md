<a id="atlas-kwavers-vis-config-2026-08-25"></a>
## ATLAS-KWAVERS-VIS-CONFIG-2026-08-25 — Make visualization selection and quality single-source [major] — blocked

outcome: top-level Kwavers `VisualizationBackend::{Leto, Hephaestus}` is the only backend-selection source; the ignored `gpu_enabled` boolean and duplicate `render_quality` field are deleted; adaptive quality changes the renderer configuration subsequent frames use.

Acceptance oracle: stack-wide search finds no `gpu_enabled` or `render_quality`; backend conformance and real Hephaestus pipeline tests stay value-correct; focused tests prove quality transition and renderer propagation; formatting, Clippy `-D warnings`, nextest, doctests, Rustdoc, and SemVer classification pass on the exact revision.

Delivered and merged: PR #638 at `00455130f`; SemVer confirms exactly the two removed fields as the required major change; post-merge matrix terminal (33 passes, 2 expected skips, 0 failures) except one cancellation.

Blocker / re-open trigger: `Benchmark Runtime Smoke` hit its 30-minute job timeout on a cold build (29 min spent in the Criterion command) — correct the cold-build benchmark-smoke instrument without raising its bound, then obtain a terminal green run and advance Atlas gitlink `repos/kwavers` (currently `8ef48975c`) to it.
