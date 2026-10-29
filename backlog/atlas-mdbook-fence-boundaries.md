## ATLAS-MDBOOK-FENCE-BOUNDARIES — Keep code-indented fences inside examples [patch]

- Owner: Codex task `01a17995-4c0b-701d-8625-8650165230c2`; isolated
  continuation of the October 29 uncovered-subsystem correctness pass.
- Base: Atlas `6e495c8246be86bfd4c30613326f77294fd26dc9`.
- Defect: the documentation-link validator strips arbitrary whitespace from
  closing fences. A four-space or tab-indented fence therefore ends an example
  early, exposes example links/headings, and hides real destinations after the
  actual closing fence. Unicode padding has the same effect.
- Contract: closing fences permit zero to three leading ASCII spaces, a run
  matching the opener's character and at least its length, then ASCII spaces
  or tabs. Preserve CRLF, valid fence controls, and genuine missing-file failures.
- Evidence: the new boundary and CLI regressions fail against the unchanged
  base. An independent mdBook 0.4.40 render of the four-space fixture keeps the
  example inside code and emits only the real link and heading. This renderer
  observation does not qualify a reusable workflow's configured tool version.
- Implementation: retain the standalone validator and its original root symbols;
  share the corrected existing mask between links and headings. Move historical
  rationale to docs/mdbook/link-detector-internals.md to keep modified files
  below 500 lines. Preserve classifications, allowlists, exit policies, copied
  validator fixtures, and existing gate activation paths.
- Acceptance: focused regressions, unchanged full Python suite, normal hooks,
  exact-head independent review and applicable hosted checks.
- Status: focused validation passes (53 tests, 68 subtests); final qualification
  and independent review pending. No member figure-generation closure is claimed.
- Scope excludes #583, hooks, pins, dependency/lock changes, publication settings,
  and protected Apollo/Moirai work.
