<a id="atlas-pub-005"></a>
## ATLAS-PUB-005 — Flip `mdbook-test` per book as samples become compilable [patch] — in-progress

- Owner: current Atlas session; active claim: Iris; scope: one book per claim,
  in the owning repository.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §6.
- Outcome: every published book runs `mdbook test` in CI so chapters cannot rot.
  The shared workflow defaults `mdbook-test` to `false` as a staging mechanism,
  not an accepted end state. The committed provider defaults currently have
  seventeen shared callers plus Gaia's direct command gate; the six named
  residual callers remain untested until their samples compile.
- Claim status (updated 2026-08-20):
  - **melinoe** — DONE: all fenced samples compilable; blocks referencing the
    crate carry `extern crate melinoe;` and link through a staged plain-named
    rlib (`mdbook test --library-path`), signature illustrations `ignore`d, the
    cross-brand rejection sample `compile_fail`; caller passes `mdbook-test:
    true` + `cargo-package: melinoe`; the shared workflow's broken
    `RUSTDOCFLAGS` mechanism replaced with the staging + `--library-path` path.
    Merged via melinoe PR #11; main CI green (all 11 chapters tested), Pages
    deploy green; workflow fix on atlas main (`70c6c6b`, PR #100) makes the
    caller's full-SHA pin durable.
  - **eunomia** — DONE: caller passes `mdbook-test: true` and its hosted book
    gate is part of the provider's merged workflow.
  - **helios** — OPEN: H-103. The current book contains illustrative Rust
    fragments that fail direct `mdbook test docs/book` because they omit setup,
    use unresolved provider imports, or fence diagrams/commands as Rust. H-102
    repaired source-change triggers and enabled linkcheck2; H-103 must convert
    the snippets before the caller can pass `mdbook-test: true`.
  - **iris** — LANDED at provider `9672fc0`: the Pages caller pins the shared
    workflow fix `1fcd17c` and enables `mdbook-test: true`, Rust `1.97.0`, and
    `cargo-package: iris-viz`; the
    included example declares `extern crate iris`, and the stack-position
    topology diagram is fenced as `text`. Local format, locked all-target
    check, Clippy, nextest (`17/17`), doctests (`3/3`), package verification,
    `mdbook build`, and `mdbook test` pass. Push-triggered hosted runs are
    `32332860859` (CI), `32332861158` (Deploy mdBook), and `32332859993`
    (Pages build/deployment) remain queued at the time of recording. The prior
    run at `8224dba` exposed the package/library-name mismatch and was replaced
    by this explicit-crate revision. Peer-owned Iris lockfile work remains
    untouched.
- Acceptance per book: samples compile against the package; the caller passes
  `mdbook-test: true` and, where samples need providers, `atlas-ref`; the flip
  commit demonstrates the gate failing on a deliberately broken sample before
  landing green.
- Dependencies: ATLAS-PUB-002 for that package.

