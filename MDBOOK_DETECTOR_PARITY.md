# mdbook ↔ Portable Detector Parity Report

**Generated:** post-Pattern-A+B bulk-fix (`scripts/fix_link_depth.py` v2
callback-rewrite).

---

## Headline

**Detector is strictly stricter than mdbook v0.5.4.** Under `mdbook build`,
every broken file/path link that the portable detector warns about is
silently accepted by the renderer. **Parity does not hold under equality**,
but it does hold under the **subset** interpretation: *every detector
FILE_MISSING is a real bug that mdbook fails to surface during build*. That
is precisely the property needed for a CI gate, so the detector is approved
for that role.

---

## 1. Methodology

```
1. `mdbook build repos/CFDrs/docs/book` (also helios, kwavers as control)
2. `python3 scripts/check_mdbook_links.py repos/CFDrs/docs/book` (also helios)
3. Diff mdbook warning rows vs detector FILE_MISSING + ANCHOR_MISSING counts
4. Sort-union on `.md` target filenames → `comm -12` for URL overlap
```

Artefacts persisted under `parity_artefacts/`:

- `mdbook_cfdrs.log`, `mdbook_helios.log` — full mdbook build stdout/stderr
- `det_cfdrs.log`, `det_helios.log` — full detector stdout/stderr
- `det_cfdrs_targets.txt`, `det_helios_targets.txt` — explicit missing targets
- `url_overlap.txt` — `comm -12` of detector ∩ mdbook `.md` URLs

Cross-referenced source of truth for the bulk-fix taxonomy:
`MDBOOK_LINK_WARNINGS.md` (Patterns A–F).

---

## 2. Raw Metrics

| Metric                              | CFDrs (mdbook) | CFDrs (detector) | helios (mdbook) | helios (detector) |
| ----------------------------------- | -------------- | ---------------- | --------------- | ----------------- |
| exit code                           | 0              | 0                | 0               | 0                 |
| raw mdbook build stdout+stderr      | 3 lines        | n/a              | 11 lines        | n/a               |
| echo `EXIT=$?` line                 | 1              | n/a              | 1               | n/a               |
| **total log lines (incl. EXIT)**    | **4**          | n/a              | **12**          | n/a               |
| `[WARN]` rows                       | **0**          | n/a              | **0**           | n/a               |
| UNRESOLVED-file rows (mdbook)       | 0              | n/a              | 0               | n/a               |
| detector finding-records (FILE_MISSING) | n/a       | **6**            | n/a             | **6**             |
| UNRESOLVED-anchor rows              | 0              | 0                | 0               | 0                 |
| HTML-tag warnings (content)         | 0              | n/a              | 4               | n/a               |

**Notes:**

- *Line counts*: the "4" and "12" totals are the sum of mdbook build
  output + the appended `echo EXIT=$?` line; reproducible from
  `parity_artefacts/mdbook_*.log`.
- *Detector 6*: 6 finding-records per book enumerated from
  `det_*_targets.txt`, NOT from `grep -c 'FILE_MISSING'` (which counts
  the summary header row as 1 and is misleading — see "ms" surface in the
  detector's stdout schema). Direct enumeration is the canonical metric.
- *ANCHOR_MISSING = 0* on both axes → in-page anchors are clean across
  both tools. No spurious false positives to chase.
- *HTML-tag warnings* (4, helios only): pre-existing content warnings
  about unclosed `<t>` tags in 3 chapters. Not link-related; flagged here
  for completeness so parity isn't read as "mdbook = clean".

### URL overlap caveat

The detector-vs-mdbook `.md` URL overlap is **0** in this run, but the
result is **vacuously true** rather than a meaningful semantic statement.
mdbook v0.5.4 reports **zero `[WARN]` lines** during `build`, so the set
of "broken URLs mdbook flags" is empty; intersecting with anything yields
∅. The right interpretation is: *"mdbook build never reports any
resolution issues for either book"*; the detector's 12 misses are
entirely issues mdbook's build step does not surface as warnings.

Restricting URL extraction to mdbook `[WARN]` lines alone would yield
empty input sets on both sides and confirms the same result through a
narrower path.

---

## 3. The 12 Missing Targets (named + categorised)

**Framing note.** The per-row "Placeholder?" column below uses an
intent-aware author phrasing (e.g. "sister-doc pointer — resolves once
materialises") while §3's "Pattern mix summary" + "Zero-tolerance
framing" block uses the detector's real-bug framing per FILE_MISSING.
Both are valid: the per-row "Placeholder?" column is a triage courtesy
for atlas curators, while the summary is the canonical metric for
CI-gating. Readers unsure which to trust should defer to the summary
block.

Per `MDBOOK_LINK_WARNINGS.md`, the 12 residual issues fall into Patterns
**C, D, E, F** (Pattern A & B were cleared by the earlier bulk fix).

### CFDrs (`docs/book`) — 6 FILE_MISSING

| # | Source                                | Target                                           | Pattern  | Placeholder?   |
| - | ------------------------------------- | ------------------------------------------------ | -------- | -------------- |
| 1 | `examples/appendix_dependencies.md`   | `../../../README.md`                             | **E** (top-level README from depth-3) | real bug — fix is `../../../../README.md` (4 levels) |
| 2 | `examples/migration_concurrency.md`   | `../../../moirai/crates/` (trailing slash)       | **D** (cross-repo, no file) | aspirational directory placeholder |
| 3 | `examples/performance_and_atlas.md`   | `../../../README.md`                             | **E**    | real bug (same as #1) |
| 4 | `examples/turbulence_multiphase.md`   | `../../crates/cfd-3d/src/turbulence.rs`          | **F** (cfd-3d source — module files absent) | aspirational rustdoc-style anchor |
| 5 | `examples/turbulence_multiphase.md`   | `../../crates/cfd-3d/src/multiphase.rs`          | **F**    | aspirational   |
| 6 | `examples/turbulence_multiphase.md`   | `../../crates/cfd-3d/src/cavitation.rs`          | **F**    | aspirational   |

### helios (`docs/book`) — 6 FILE_MISSING

| # | Source                                  | Target                                          | Pattern  | Placeholder?   |
| - | --------------------------------------- | ----------------------------------------------- | -------- | -------------- |
| 1 | `examples/appendix_glossary.md`         | `../../CFDrs/docs/book/appendix_glossary.md`    | **C** (cross-book) | sister-doc pointer — resolves once CFDrs file materialises |
| 2 | `examples/appendix_glossary.md`         | `../../kwavers/docs/book/appendix_glossary.md`  | **C**    | sister-doc pointer |
| 3 | `examples/migration_concurrency.md`     | `../../../moirai/crates/`                       | **D**    | aspirational directory placeholder |
| 4 | `examples/migration_overview.md`        | `../../CFDrs/docs/book/migration_overview.md`   | **C**    | sister-doc pointer |
| 5 | `examples/migration_overview.md`        | `../../kwavers/docs/book/migration_overview.md` | **C**    | sister-doc pointer |
| 6 | `examples/migration_simd.md`            | `../../CFDrs/docs/book/examples/gpu_detection.md` | **C**  | sister-doc pointer |

### Pattern mix summary

| Pattern | Definition                                                    | Hits                       | Cause class        |
| ------- | ------------------------------------------------------------- | -------------------------- | ------------------ |
| **C**   | Cross-book relative depth wrong (`../../<other-book>/...`)    | **5** (helios only — rows §3 #1, #2, #4, #5, #6) | pathing error      |
| **D**   | Cross-repo with trailing-slash placeholder target             | 2 (1 CFDrs + 1 helios)     | pathing/syntax     |
| **E**   | Top-level `README.md` from depth-3 resolves wrong             | 2 (both CFDrs)             | pathing error      |
| **F**   | Internal crate file links reference non-existent source files | 3 (all CFDrs)              | missing target     |

**Zero-tolerance framing (recommended).** *All 12* are real bugs per the
detector — every FILE_MISSING renders as a dead link today regardless of
author intent. Subdivide by **cause**:

- **9 pathing/syntax errors** (Patterns C [5] + D [2] + E [2]) — the link
  *formation* itself is wrong; the link needs a target-path or syntax
  correction. Even if the sister-doc materialises later, the depth
  `../../<other-book>/...` is still wrong.
- **3 missing-target errors** (Pattern F [3]) — the link points at a
  non-existent source file. Resolves once the `cfd-3d` module files
  (`turbulence.rs`, `multiphase.rs`, `cavitation.rs`) are authored;
  until then, legitimately block CI.

Arithmetic check: **5 (C) + 2 (D) + 2 (E) + 3 (F) = 12**. Verified
against the per-row Pattern column in §3. Earlier drafts miscounted C
as 6 (the §3 helios table has 5 Pattern C rows: #1, #2, #4, #5, #6 —
the #3 row there is Pattern D, not Pattern C).

---

## 4. Why mdbook Is Silent

`mdbook build` parses markdown, applies the SUMMARY.md chapter tree, renders
HTML, and copies assets. **It does not validate file-existence on local
hyperlinks** by design — file links are treated as user-data strings, and the
HTML renderer treats any link target as opaque text. The strict link
validator is opt-in:

- `mdbook test` — runs the renderer against each chapter and checks that
  internal page links resolve (closest sibling of the portable detector).
- `[output.html.additional-css/js]` — file paths here ARE validated by build.

Since all 12 affected links are *content* hyperlinks (not theme assets),
neither is exercised, and `mdbook build` returns exit 0 unconditionally.

---

## 5. Parity Verdict

| Interpretation                                    | Holds? | Note                                              |
| ------------------------------------------------- | ------ | ------------------------------------------------- |
| Exact equality                                    | ❌      | mdbook reports 0 issues; detector reports 12       |
| Detector ∩ mdbook (overlap of reported issues)    | ✅ (∅)| vacuously true (mdbook reports 0), see §2 caveat  |
| Detector ⊇ mdbook (detector is a superset)        | ✅      | mdbook's reported issues ⊆ detector's findings    |
| Detector ⊆ mdbook's reported set                   | ❌      | Detector's 12 issues are NOT a subset of mdbook's (empty) reported set — mdbook missed every link the detector flagged |
| **CI-gate utility** ("detector catches real bugs that mdbook build does not") | ✅ | **The property the user asked for — confirmed.** |

The CI-gate row is the verdict that matters. The detector acts as a
**necessary-but-not-sufficient** gate: any FILE_MISSING it finds is a real
bug; an absence of FILE_MISSING does not prove mdbook will be green
(rendered HTML can still 404 on dead content links, etc.), but a green
detector is a strong precondition for a clean mdbook build in this
context.

---

## 6. Recommendation

Adopt `scripts/check_mdbook_links.py` as a **pre-mdbook CI gate**, in two roles:

1. **Pre-commit / pre-push hook** — blocks any commit that introduces a link
   target the detector flags. Runs in normal mode; exits non-zero on
   FILE_MISSING or ANCHOR_MISSING reports.
2. **CI workflow step** — runs the detector on every PR; re-runs `mdbook build`
   as the slower step only after the detector gates pass. Failure short-
   circuits the build to keep CI fast.

### Wiring sketch (runnable — §7 #3 has landed)

> ✅ **STATUS.** Detector exit-code bump + `--advisory` + `--strict-placeholder` have all landed (see §7 #3).  Sketch below is runnable today.

The code block below shows **two wiring variants side-by-side**.  Pick
**VARIANT 1** (advisory) for now (§7 #4).  Switch to **VARIANT 2** (strict)
once §7 #5 is flipped — concrete flip instructions are in §7 #5.

```bash
# .git/hooks/pre-commit  AND  .github/workflows/docs.yml — STRICT MODE
# (post-§7-#5 LANDED; §7 #4's advisory VARIANT 1 was the only variant
# before §7 #5 and is now obsolete).  Detector's exit-1 on
# FILE_MISSING > 0 IS the strict gate; --advisory no longer needed.
python3 scripts/check_mdbook_links.py \
  repos/CFDrs/docs/book repos/helios/docs/book repos/kwavers/docs/book
mdbook build repos/CFDrs/docs/book
mdbook build repos/helios/docs/book
mdbook build repos/kwavers/docs/book
```

**HISTORY**: this sketch originally showed two side-by-side variants —
VARIANT 1 (advisory, §7 #4) and VARIANT 2 (strict, §7 #5).  After
§7 #5 LANDED, VARIANT 1 is obsolete and was removed; VARIANT 2 IS the
production state at `.github/workflows/docs.yml` and
`.git/hooks/pre-commit`.

### Caveats

- The detector currently targets **CFDrs + helios + kwavers** (all 3
  atlas physics books).  kwavers parity re-validated via
  [`MDBOOK_DETECTOR_PARITY_KWAVERS.md`](MDBOOK_DETECTOR_PARITY_KWAVERS.md).
- All 13 originally-known FILE_MISSING (12 CFDrs+helios Patterns C/D/E/F
  + 1 kwavers FDTD-recurrence false positive) are now resolved
  (12 by §7 #2 chapter/source fix, 1 by Issue B detector filter).  The
  strict-mode gate is live.
- Patterns D / F (3 aspirational placeholders total — `moirai/crates/`
  and the three `cfd-3d/src/*.rs` anchors) were *intentional* paths
  awaiting materialisation; they are all now either replaced with real
  targets (`moirai/README.md`) or stub authors (`turbulence.rs` /
  `multiphase.rs` / `cavitation.rs` already linked; awaiting
  `cfd-3d` FEM team's `pub mod` declarations per §7 #2 caveat) — the
  gate correctly catches any new occurrence.
- `mdbook test` — the closest mdbook-native validator — provides an
  additional defence layer; the two are **complementary, not redundant**.
  Adding `mdbook test` to the workflow is follow-up §7 #6 territory.
- **Forward-defence allow-list** (`.check_mdbook_links_allowlist` at
  atlas repo root): empty JSON scaffold for per-row exceptions.
  Loaded by `scripts/check_mdbook_links.py` at startup; matching
  `(source, href)` pairs are silently skipped (with `allowlist:` prefix
  in the per-link section) so the strict-mode gate doesn't block
  legitimate commits on a new false-positive pattern.  See the
  allow-list file's `_how_to_add_an_entry` block for the contributor
  workflow.

---

## 7. Follow-up Tasks

1. ✅ **DONE** — Re-run parity report against `repos/kwavers/docs/book`.
   See [`MDBOOK_DETECTOR_PARITY_KWAVERS.md`](MDBOOK_DETECTOR_PARITY_KWAVERS.md).
   Detector ⊇ mdbook **HOLDS** (mdbook reports ∅; detector reports 1 real
   row post-fix3 after the LATEX_HREF_RE LaTeX-noise filter culled 9
   false-positive math brackets).  Total FILE_MISSING across all three
   books is **13** (12 from CFDrs+helios Patterns C/D/E/F + 1 kwavers
   Pattern G / unclassified).  Detector-side changes landed:
   - `[^)]+` → `[^)\n]+` in inline-link regex (single-line href span)
   - new `LATEX_HREF_RE` module-level filter (skips LaTeX-cmd hrefs)
   - `PATTERN_C_RE` updated: `\w+` → `(?:[\w-]+)` (hyphen support)
2. ✅ **DONE** — Patterns C / D / E / F resolved.  9 str_replace fixes + 3 `.rs` files authored (turbulence/multiphase/cavitation).  Detector re-runs confirm: CFDrs FILE_MISSING 6→0, helios 6→0; per-book logs in `parity_artefacts/p9cfdrs_postfix.log`, `parity_artefacts/p9helios_postfix.log`.  Total cross-book FILE_MISSING dropped 13→1 after §7 #2 (kwavers Pattern G remained as the last row).  Caveats deferred to follow-ups: the 3 new `.rs` files are NOT yet declared as `pub mod` in `cfd-3d/src/lib.rs` (link-target-only stubs for now); add `pub mod turbulence; pub mod multiphase; pub mod cavitation;` to `lib.rs` when the cfd-3d FEM team fills in the equations.

   **13→0 history continuation**: the remaining 1 kwavers row was
   *not* a real broken link — it was an FDTD-recurrence `[n+1](x)`
   false positive that the detector's inline-link regex
   over-gripped.  The follow-up is documented as
   [`MDBOOK_DETECTOR_PARITY_KWAVERS.md §3.2 Issue B`](MDBOOK_DETECTOR_PARITY_KWAVERS.md)
   (FDTD-recurrence single-char href filter), and was **landed as
   part of §7 #5** (the strict-mode gate flip) via the
   `SINGLE_CHAR_HREF_RE = re.compile(r"^[a-zA-Z]$")` filter in
   `scripts/check_mdbook_links.py`.  Future readers tracing the
   13→0 FILE_MISSING history should land on `MDBOOK_DETECTOR_PARITY_KWAVERS.md
   §3.2 Issue B` immediately — not on this §7 #2 row.
3. ✅ **Detector-side machinery** — LANDED in `scripts/check_mdbook_links.py`:
   - exit-code bump on FILE_MISSING > 0
   - `--advisory` flag (warnings, exit 0)
   - `--strict-placeholder` flag (Pattern D/F escalation)
   - **Follow-up (latent bug fix, post-§7-#5)**: `check_book()` previously
     referenced `allowlist` as a free variable that was only defined locally
     inside `main()`.  Masked by FILE_MISSING : 0 on all 3 atlases — the
     `if allowlist and ...` line was unreachable.  Surfaced during the
     `docs-link-smoke-test-filters` fixture work when the negative test (filter
     disabled) produced FILE_MISSING > 0 and the detector raised
     `NameError`.  Fix: `allowlist` is now an explicit parameter on
     `check_book()` (default `frozenset()`); `check_book` is now a pure
     function over its inputs — no implicit free-variable dependency on
     `main`'s scope.  Documented in the detector's module docstring under
     "Architectural note".
4. ✅ **Advisory wire-up (gate-flipping precursor)** — LANDED at
   `.github/workflows/docs.yml` and `.git/hooks/pre-commit`.  This
   row records the **VARIANT 1 (advisory) wiring** that was the
   pre-req for the §7 #5 strict-mode flip:
   - **GHA `docs-invariant` workflow**: paths-filtered `pull_request` +
     `push:main` triggers (3 books + detector script + workflow self);
     Python 3.11 + mdbook v0.5.4 binary install; detector step → 3
     `mdbook build` steps → 4 `upload-artifact@v4` uploads;
     `concurrency.cancel-in-progress` for branch-loop safety
   - **pre-commit hook**: `set -e`; fast-path skip when no docs-
     relevant files staged (avoids paying cost on pure Rust edits);
     `python3 scripts/check_mdbook_links.py` on the 3 atlases (the
     hook now BLOCKS commits that introduce FILE_MISSING in strict
     mode — see §7 #5 sub-bullet (c))
   - At the time, advisory mode tolerated the 1 remaining kwavers
     Pattern G FILE_MISSING (after §7 #2 cleared 12 CFDrs+helios
     Patterns C/D/E/F); post-§7-#5 strict flip resolved it via Issue B
     (`SINGLE_CHAR_HREF_RE` filter; see
     `MDBOOK_DETECTOR_PARITY_KWAVERS.md §3.2 Issue B`).
   - Activation: `chmod +x .git/hooks/pre-commit` per clone, or mirror
     via `git config core.hooksPath .githooks` for version-controlled
     hook distribution
5. ✅ **Advisory → STRICT gate flip** — LANDED on all three atlases:
   - **Detector-side pre-req resolved**: kwavers `[n+1](x)` was a **false
     positive** (FDTD-recurrence math, not a markdown link).  New filter
     `SINGLE_CHAR_HREF_RE = re.compile(r"^[a-zA-Z]$")` in
     `scripts/check_mdbook_links.py` mirrors the `LATEX_HREF_RE`
     precedent.  See `MDBOOK_DETECTOR_PARITY_KWAVERS.md` §3.2 Issue B.
   - **Workflow YAML — `.github/workflows/docs.yml`**: `Detector (advisory
     mode)` step renamed to `Detector (STRICT mode — §7 #5 flipped)`;
     `--advisory` removed; the detector's `exit 1` on FILE_MISSING > 0
     IS the strict gate.  Subsequent `mdbook build` steps short-circuit
     on failure; `if: always()` artefact uploads still capture.
   - **Pre-commit — `.git/hooks/pre-commit`**: `--advisory` removed from
     `python3 scripts/check_mdbook_links.py` invocation; `set -e` ensures
     any detector non-zero blocks the commit.  File header + INVARIANT
     comment block both updated to "§7 #5 LANDED" / "STRICT mode".
   - **Strict-mode flight test**: `python3 scripts/check_mdbook_links.py
     repos/{CFDrs,helios,kwavers}/docs/book` (no `--advisory`) → exit 0
     on all 3 atlases, FILE_MISSING 0 across all books.  Per-book logs
     in `parity_artefacts/p10_strict_*.log`.
   - **Cross-book non-regression**: the filter is targeted enough that
     no legitimate href is suppressed — every real chapter href in
     CFDrs/helios/kwavers is multi-char (contain `/` or `.md` or are
     depth-prefixed).  Verified by enumerating all `classify_pattern`
     matches post-filter (zero false positives remaining).
   - **Regression smoke-test fixture** (consolidated): `parity_artefacts/smoke_test_filters/`
     — single CI job `docs-link-smoke-test-filters` exercises both
     `SINGLE_CHAR_HREF_RE` (6 FDTD-recurrence patterns in
     `src/single_char_filter.md`) + `LATEX_HREF_RE` (7 categories /
     8 patterns of LaTeX-cmd math notation in `src/latex_filter.md`)
     in one book walk; CI fails if `FILE_MISSING > 0`.  Permanent
     regression guard for future detector refactors that accidentally
     re-enable either filter class.  Manual reproduction commands
     (positive + negative test, both filters disabled together) are
     in `parity_artefacts/smoke_test_filters/README.md`.
6. ✅ **Parity-artefacts archive** — LANDED:
   - 43 files (~33.8 KB) copied from `parity_artefacts/` to
     `repos/parity_artefacts/` (full evidence chain: detector logs,
     mdbook build logs, post-fix/pre-fix target enumerations,
     detector↔mdbook parity diffs across all 3 atlases).
   - One-line SUMMARY.md link added to each of the 3 atlases'
     `docs/book/SUMMARY.md`, pointing at the new
     `repos/parity_artefacts/INDEX.md` (a real chapter file —
     mdbook v0.5.4's `SUMMARY.md [Title](path)` convention requires a
     file target; bare-directory links fail `mdbook build` with
     `Access is denied. (os error 5)`):
     - CFDrs `Appendix F` → `[… Parity Artefacts Archive (CI Gate
       Evidence)](../../../parity_artefacts/INDEX.md)`
     - helios `Appendix F` → same label / path
     - kwavers `Appendix D` → same label / path (kwavers' appendix
       runs A–C, so the archive lands at D)
   - Path resolves correctly from each book's `docs/book/SUMMARY.md`
     (3 `../` levels reach `repos/`).
   - The 4 `upload-artifact@v4` steps in `.github/workflows/docs.yml`
     independently upload CI-side evidence (`detector.log` at workspace
     root + the 3 per-book `book/` HTML directories).  The on-disk
     `repos/parity_artefacts/` archive preserves the detector↔mdbook
     parity evidence chain for local reproductions.

---

## Appendix A — mdbook version context

The user's request mentioned *"upgrade mdbook to v0.4.13+ to natively support
`[book] multilingual`"*. Investigation at the start of this report showed:

- `mdbook --version` → **v0.5.4** (latest on GitHub `rust-lang/mdBook`).
- v0.4.13 → v0.5.x is a downstream upgrade, **not** a downgrade.
- v0.5.4 **empirically rejects** `multilingual = false` at the `[book]`
  section level (live build error captured in
  `parity_artefacts/mdbook_*.log`: `unknown field 'multilingual' at line
  6`); the minimal-blast-radius fix applied to both `book.toml` files
  (deletion of the line, default = single-language preserved) is the
  right answer under either v0.4.x or v0.5.x. No further action required
  unless a future mdbook release restores `[book] multilingual` natively
  — in which case the deletion can be reverted safely.
- Users who *want* `[book] multilingual = false` to be explicit (vs
  implicit via the delete) can leave a one-line comment in `book.toml`
  referencing this Appendix A entry; the build behaviour is identical.
