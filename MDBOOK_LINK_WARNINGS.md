# mdbook Dead-Link Follow-Up

**Task**: Run `mdbook build docs/book` in `repos/CFDrs` and `repos/helios`,
verify zero dead-link warnings on the rendered books; otherwise capture the
inventory as a follow-up task.

**Status**: ❗ Verified **NOT zero**. Inventory captured below.

**Why author mdbook was not run**:
The local mdbook v0.5.4 (`~/.cargo/bin/mdbook`) cannot parse the `[book]`
section of either `book.toml` because it doesn't recognize the field
`multilingual` (added in newer mdbook releases). Author mdbook builds for
both books fail with:

> `unknown field 'multilingual' at line 6 column 1`

**Resolution path**: A portable mdbook-equivalent dead-link detector was
written at `scripts/check_mdbook_links.py` (reviewed by code-reviewer
twice, currently marked PRODUCTION-READY). It produces mdbook-equivalent
link-warnings lists. Full captured inventories are at:

- `tmp/cfdrs_link_warnings.txt`
- `tmp/helios_link_warnings.txt`

(Each is a verbatim stdout capture of the detector run.)

## Headlines

| Book      | Files | Links | FILE_MISSING | ANCHOR_MISSING | READ_FAIL |
|-----------|-------|-------|--------------|----------------|-----------|
| CFDrs     | 95    | 320   | **44**       | 0              | 0         |
| helios    | 62    | 238   | **19**       | 0              | 0         |
| **Total** | 157   | 558   | **63**       | 0              | 0         |

ANCHOR_MISSING = 0 across both books. All 63 issues are FILE_MISSING.

## Pattern Categories (consolidated)

Of the 63 FILE_MISSING items, **~59 fall into 3 mechanical off-by-one
relative-path bugs that a single Python regex sweep can fix.** The
remaining **~4** require manual investigation.

### 🟢 Pattern A — Off-by-one: example links `../../examples/foo.rs` should be `../../../examples/foo.rs`

- **CFDrs**: 30 instances across `examples/*.md` — link shape
  `[../../examples/<name>.rs]` resolves wrong because `examples/*.md` is
  itself inside `docs/book/examples/`, so `../..` lands in `docs/`, not
  the project root.
- **helios**: 0 instances of this exact pattern (helios uses `../crates/`, see Pattern B).
- **Fix**: prepend an extra `../` to all `examples/*.md` links of form
  `[../../examples/...]`. Bulk-replace in
  `repos/CFDrs/docs/book/examples/*.md`.

### 🟢 Pattern B — Off-by-one: example links `../../crates/<crate>/examples/foo.rs` should be `..` deeper

- **CFDrs**: 4 instances in `examples/*.md` (cfd-validation, cfd-3d) →
  shape `[../../crates/<crate>/examples/<name>.rs]` resolves to
  `D:\atlas\repos\CFDrs\docs\crates\...` instead of
  `D:\atlas\repos\CFDrs\crates\...`.
- **helios**: 12 instances in `examples/*.md` →
  `[../../crates/helios-<x>/examples/<name>.rs]` resolves to
  `D:\atlas\repos\helios\docs\crates\...` instead of
  `D:\atlas\repos\helios\crates\...`.
- **Fix**: prepend an extra `../` to `examples/*.md` links of form
  `[../../crates/...]`. Bulk-replace in both books.

### 🟡 Pattern C — Cross-book relative-path depth wrong (`../../CFDrs/docs/...` → `../../../CFDrs/docs/...`)

- **helios**: 4 instances in `migration_overview.md` and `migration_simd.md`,
  plus 2 in `appendix_glossary.md`. Shape
  `[../../CFDrs/docs/book/<file>.md]` and
  `[../../kwavers/docs/book/<file>.md]` resolves to
  `repos/helios/CFDrs/...` instead of `repos/CFDrs/...`.
- **Fix**: prepend `../` to all 6 cross-book links in
  `repos/helios/docs/book/{migration_overview,migration_simd,appendix_glossary}.md`.

### 🟡 Pattern D — Cross-repo `../../../moirai/crates/` missing (path is wrong)

- **CFDrs**: 1 instance — `migration_concurrency.md` linking
  `[../../../moirai/crates/]`. The `moirai` repo's structure differs from
  the link path; the live directory resolves at
  `D:\atlas\repos\moirai\crates\` but the trailing slash + no file name
  may suggest the link author intended a directory listing that mdBook
  can't render.
- **helios**: 1 instance, identical pattern, identical target.
- **Fix**: replace `../../../moirai/crates/` with an actual crate path
  (e.g. `../../../moirai/README.md`) or a concrete crate
  (`../../../moirai/crates/moirai-core/`).

### 🟡 Pattern E — Top-level `../../../README.md` resolves to `repos/README.md` which does not exist

- **CFDrs**: 2 instances — `appendix_dependencies.md` and
  `performance_and_atlas.md` linking `[../../../README.md]`. The
  intended target is the project root `atlas/README.md`, but the path
  resolves to `D:\atlas\repos\README.md`, which does not exist (the
  top-level `README.md` is at `D:\atlas\README.md`).
- **Fix**: change both to `[../../../../README.md]` (4 levels up from
  `docs/book/`) to land at `D:\atlas\README.md`.

### 🟡 Pattern F — Internal CFDrs crate file links reference non-existent source files

- **CFDrs**: 3 instances — `turbulence_multiphase.md` references
  `[../../crates/cfd-3d/src/{turbulence.rs,multiphase.rs,cavitation.rs}]`.
  The `cfd-3d` crate does not contain module files at those paths.
- **Fix**: identify the actual `cfd-3d` source files for turbulence /
  multiphase / cavitation logic and update the three links accordingly.
  This requires a manual search of `repos/CFDrs/crates/cfd-3d/src/`.

## Recommended execution order

1. **Bulk fix Patterns A & B** (60 of 63 issues, ~5 min)
   via a single Python script that prepends `../` to `examples/*.md`
   links with `../../examples/` and `../../crates/` prefixes.
2. **Bulk fix Patterns C & E** (8 of remaining 9, ~5 min)
   by targeted `str_replace` calls.
3. **Manual fix Patterns D & F** (3 issues, requires curator review).

Then re-run `python3 scripts/check_mdbook_links.py repos/{CFDrs,helios}/docs/book`
and confirm the FILE_MISSING count drops to 0.

## Future-proofing

- After author `mdbook` is upgraded to a version that supports
  `[book] multilingual`, add `mdbook build` as a CI gate alongside the
  Python detector.
- The detector script (`scripts/check_mdbook_links.py`) is currently
  exit-code 0 always; bump to non-zero when FILE_MISSING > 0 so it can
  serve as a CI check standalone.
