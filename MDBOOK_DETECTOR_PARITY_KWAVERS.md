# mdbook ↔ Portable Detector Parity Report — kwavers (Third Atlas Physics Book)

**Generated:** post-§7-#1 re-validation pass; kwavers appended after
the CFDrs/helios runs were complete.  Cross-references the parent
report at `MDBOOK_DETECTOR_PARITY.md`; this document records only
what is kwavers-specific.

---

## Headline

**Detector is strictly stricter than mdbook v0.5.4 on kwavers.**
Under `mdbook build repos/kwavers/docs/book`, the renderer reports
**0 [WARN] lines**.  The portable detector, after Issue B
(`SINGLE_CHAR_HREF_RE` filter — FDTD-recurrence false positive),
also emits **0 FILE_MISSING** for kwavers.  **Detector ⊇ mdbook
HOLDS** (both axes report ∅ — the property still holds, with the
strict-mode CI gate flipping cleanly per §7 #5).

This pass documented and resolved two kwavers false-positives, both
detector-side:

- **Issue A** (LaTeX-noise) — backslash-cmd hrefs
- **Issue B** (FDTD-recurrence single-char href) — `[n+1](x)` math

…as well as **Pattern C hardening** (hyphenated book names).  All
three corrections are detector-side and affect all three books; the
kwavers CFDrs/helios invariants are unchanged.

---

## 1. Methodology

```
1. mdbook build repos/kwavers/docs/book
2. python3 scripts/check_mdbook_links.py repos/kwavers/docs/book (default; strict exit code)
3. python3 scripts/check_mdbook_links.py --advisory repos/kwavers/docs/book (exit 0 + warnings printed)
4. Diff mdbook WARN rows vs detector FILE_MISSING + ANCHOR_MISSING counts
5. Direct python ground-truth: classify_pattern() applied to each
   FILE_MISSING row to verify per-row labels
```

Artefacts under `parity_artefacts/`:
- `mdbook_kwavers.log` — full mdbook build (4 lines, no warnings)
- `det_kwavers_final.log` — full detector run (post-fix3)
- `det_kwavers_targets.txt` — pre-fix2 verbatim noise + real targets
- `det_kwavers_targets_postfix2.txt` — post-fix2 verbatim (1 row)

Cross-references: `MDBOOK_DETECTOR_PARITY.md` §1 for the parent
methodology, `MDBOOK_LINK_WARNINGS.md` for Patterns A–F.

---

## 2. Raw Metrics

| Metric                              | kwavers (mdbook) | kwavers (detector) |
| ----------------------------------- | ---------------- | ------------------ |
| exit code (default run)             | 0                | **0 (strict)**     |
| exit code (`--advisory`)            | n/a              | 0                  |
| raw log lines                       | 4 (3 mdbook INFO + 1 `echo EXIT=$?`) | n/a |
| `[WARN]` rows                       | **0**            | n/a                |
| UNRESOLVED-file rows                | 0                | n/a                |
| detector FILE_MISSING (raw count)   | n/a              | **0**              |
| detector FILE_MISSING (unique after dedup) | n/a      | **0**              |
| ANCHOR_MISSING                      | 0                | 0                  |
| READ_FAIL                           | 0                | 0                  |

**Files scanned**: 110 *(from post-fix detector log)*
**Links scanned**: 512 *(from post-fix detector log)*
**Inline link density**: 537 raw `(...)` patterns, ~25 filtered by
external/`is_external`/LaTeX-noise heuristics.

The 110 files / 512 scanned-links metric is post-everything (the
post-fix detector scanned these before the LATEX_HREF_RE filter
discarded the 7 noise rows internally).

---

## 3. The Missing Target

### After all detector-side fixes

| # | Source                                              | Target | Pattern | Placeholder? |
| - | --------------------------------------------------  | ------ | ------- | ------------ |
| 1 | `examples/theranostic_fwi_platforms.md`            | `D:\atlas\repos\kwavers\docs\book\x` | (G / unclassified — see §3.2) | real bug |

### 3.1 Issue A — LaTeX-noise (resolved)

The pre-fix detector emitted **10 FILE_MISSING** rows for kwavers.
Manual inspection of the source markdown revealed 7 of those rows were
**LaTeX-math brackets, not real links**:

| Source                                          | href                                  | Verdict |
| ----------------------------------------------- | ------------------------------------- | ------- |
| `examples/inverse_problems_and_pinns.md`        | `\mathbf{r}_s, t`                     | noise — LaTeX math |
| `examples/inverse_problems_and_pinns.md`        | `\Gamma_{sr}`                         | noise   |
| `examples/inverse_problems_and_pinns.md`        | `\mathbf{r}\cdot\hat{n}_\phi`         | noise   |
| `examples/photoacoustics.md`                    | `\mathbf{r}_s, R`                     | noise   |
| `examples/photoacoustics.md`                    | `\mathbf{r}_s, c_s t`                 | noise   |
| `examples/photoacoustics.md`                    | `\mathbf{r}`                          | noise   |
| `examples/photoacoustics.md`                    | `\mathbf{r}_s,\lambda`                | noise   |
| `examples/theranostic_fwi_platforms.md`         | `[n+1](x)` → `x` (FDTD recurrence)    | **noise** — finite-difference math (see Issue B) |

Each of the noise hrefs from `\mathbf`-family sources starts with a
backslash followed by an ASCII letter (`\mathbf`, `\Gamma`, `\hat`,
`\lambda`, `\cdot`) — the LaTeX command shape.  The author wrote math,
not a link target; the detector's link regex was over-eager.

**Resolution**: added `LATEX_HREF_RE = re.compile(r"^\\[A-Za-z]+")`
at module level in `scripts/check_mdbook_links.py`.  Hrefs that match
this regex are silently skipped before path resolution.  After the
filter, the 7 LaTeX-noise rows are gone; kwavers FILE_MISSING drops
10 → 1.

### 3.2 Issue B — FDTD-recurrence single-char href (resolved)

The surviving kwavers row was originally classified as **"real — kept"**
in this report (`[x](x)` → `x`).  Re-investigation after §7 #5
strict-mode flight-test showed this is also a **false positive**.

The actual offending line in `theranostic_fwi_platforms.md`:

```text
P_peak(x) <- max(P_peak(x), |p[n+1](x)|)
```

The author wrote a **finite-difference recurrence** — `p[n+1]` is
"the pressure array at step n+1" and `(x)` is "evaluated at spatial
coordinate x" — a standard FDTD math notation.  The detector's
inline-link regex `\[\[^\]]*\]\(([^)\n]+)\)` greedily matches it as
a markdown link:

- `\[n+1\]\((x)\)` ← bracket `n+1` followed by paren `x` on the same line
- hyperlink text: `n+1`
- hyperlink href: `x`

The href `x` resolves to a non-existent chapter, hence FILE_MISSING.
But the author did not write a link; they wrote array-indexing math.

**Resolution**: added `SINGLE_CHAR_HREF_RE = re.compile(r"^[a-zA-Z]$")`
at module level in `scripts/check_mdbook_links.py` (mirrors LATEX_HREF_RE
precedent).  Single-character hrefs are skipped before path resolution.
Real chapter hrefs are always named (multi-char, contain `/` or
`.md`).  Verification:

| Book    | Before filter | After filter |
| ------- | -----------: | -----------: |
| kwavers | 1            | **0** (the `[n+1](x)` FDTD match is silently dropped) |
| CFDrs   | 0            | 0 (no regression) |
| helios  | 0            | 0 (no regression) |
| **Sum** | 1            | **0**        |

After this filter, no legitimate href is suppressed — verified by
enumerating all `classify_pattern` matches across the 3 atlases
post-filter (every real chapter href is multi-char).

### 3.3 Pattern G — REASSIGNED as-is (not a real pattern)

Following Issue B's resolution, the surviving single-char-href row
is no longer reported, so Pattern G-with-real-target is moot.  The
remaining single-character local references like `[n+1](x)`
should continue to be filtered out — they are *not* a new taxonomy
class but a sub-case of inline-math-false-positives that the
detector's existing `SINGLE_CHAR_HREF_RE` filter now handles.

If a future kwavers-style session encounters an `[X](<multi-char>)`
href where `<multi-char>` is missing, that *would* be a new pattern
("missing-local-equation-reference stub").  For now, no such row
exists, so no bootstrap is needed.  Pattern G as proposed in earlier
versions of this report is hereby **withdrawn**; the surviving kwavers
classification is `noise — FDTD recurrence` (Issue B).

### 3.4 Pattern C hardening (incidental)

`PATTERN_C_RE` was changed from `r"^(?:\.\./)+\w+/docs/book/"` to
`r"^(?:\.\./)+(?:[\w-]+)/docs/book/"`.  This is a forward-safety fix:
a future sister-book named `cfd-validation` or `cmake-rs` (with
hyphens) now classifies as Pattern C correctly.  Today's kwavers
classification benefit is zero (no such book exists yet), but the fix
is cheap and prevents a future regression.  See
`MDBOOK_LINK_WARNINGS.md` § PATTERN C for the updated spec.

### Post-fix delta across all three books

| Book    | Pre-fix FILE_MISSING | Post-fix FILE_MISSING | Δ       |
| ------- | -------------------: | --------------------: | ------: |
| kwavers | 10                   | **1**                 | −9      |
| CFDrs   | 6                    | 6                     | 0       |
| helios  | 6                    | 6                     | 0       |

The kwavers delta is the LaTeX-noise reduction.  CFDrs and helios are
unchanged because none of their 12 known rows contain backslashes in
the href (verifiable from `parity_artefacts/det_cfdrs_final.log` and
`parity_artefacts/det_helios_final.log`).

---

## 4. Why mdbook is silent (kwavers-specific)

Identical rationale to CFDrs/helios (see `MDBOOK_DETECTOR_PARITY.md`
§4): `mdbook build` does not validate file-existence on content
hyperlinks.  Per Issue B, the kwavers `[n+1](x)` was actually a
finite-difference recurrence (`p[n+1]` = "pressure array at step n+1"
evaluated at `x`) that the detector mis-gripped; once `SINGLE_CHAR_HREF_RE`
filters it, mdbook and detector both report ∅.  `mdbook test` is the
closest mdbook-native validator and would still pass the chapter's
real content links.

---

## 5. Parity Verdict

| Interpretation                                | Holds? | Note                                       |
| --------------------------------------------- | ------ | ------------------------------------------ |
| Exact equality                                | ❌      | mdbook=0, detector=1                       |
| Detector ∩ mdbook                             | ✅ (∅) | vacuously true (mdbook reports 0)          |
| Detector ⊇ mdbook (CI-gate utility)          | ✅      | detector's 1 finding covers mdbook's ∅     |
| Detector ⊆ mdbook                             | ❌      | detector flags 1 issue mdbook missed       |
| **Pre-condition for strict-mode CI gate**    | ✅      | detector-side regex/filter fixes landed; verdict is stable |

**Verdict: HOLDS.**  The kwavers ⊇ mdbook property is preserved
post-fix.  This means the §7 #1 gate-widening from CFDrs/helios
only to all-three (kwavers included) is now safe.

---

## 6. Recommendation

**STATUS — §7 #5 LANDED.**  All three original recommendations are
resolved:

1. ~~Bootstrap Pattern G in `MDBOOK_LINK_WARNINGS.md`~~.  Withdrawn
   per §3.3 — Pattern G is no longer needed because the single-char
   href filter (`SINGLE_CHAR_HREF_RE`) silently drops the underlying
   false positive.
2. ~~Author `theranostic_fwi_platforms → x.md`~~  ~OR~  ~~delete the
   offending inline link~~.  Resolved by Issue B detector-side
   filter (§3.2): kwavers FILE_MISSING drops 1 → 0 without any
   chapter-side change.
3. **Widen the §7 #4 CI wiring** — LANDED at
   `.github/workflows/docs.yml` and `.git/hooks/pre-commit`.  The
   three atlases are scanned; `--advisory` removed per §7 #5; the
   detector's exit-1 on FILE_MISSING > 0 IS the strict gate.  All 3
   books now pass strict mode with 0 FILE_MISSING (CFDrs+helios
   cleared by §7 #2 of the parent report; kwavers cleared by Issue B
   of this report).

---

## 7. Outstanding issues (kwavers-only)

**RESOLVED.**  Section §7 #5 strict-mode gate flips on this empty
list.  The previous outstanding row:

| Row | Source                                  | Target | Action                                       | Resolution |
| --- | ---                                     | ---    | ---                                          | ---        |
| 1   | `examples/theranostic_fwi_platforms.md` | `x`    | Author chapter `<book>/x.md` (or rename link) | Issue B filter (`SINGLE_CHAR_HREF_RE`) silently drops this FDTD-recurrence false positive |

---

## Appendix A — Detector-side changes during this pass

Four corrections in `scripts/check_mdbook_links.py`:

| File                                     | Change                                                                              |
| ---------------------------------------- | ----------------------------------------------------------------------------------- |
| `scripts/check_mdbook_links.py` (regex)  | `[^)]+` → `[^)\n]+` in inline-link href span; enforces single-line bounds           |
| `scripts/check_mdbook_links.py` (filter) | New `LATEX_HREF_RE = re.compile(r"^\\[A-Za-z]+")` at module level; skips LaTeX cmd hrefs |
| `scripts/check_mdbook_links.py` (regex)  | `PATTERN_C_RE` regex updated: `\w+` → `(?:[\w-]+)` for hyphenated book-name support  |
| `scripts/check_mdbook_links.py` (filter) | New `SINGLE_CHAR_HREF_RE = re.compile(r"^[a-zA-Z]$")` at module level; skips single-char hrefs from FDTD recurrence notation `f[n+1](x)` (Issue B) |

Plus the previously landed `§7 #3` machinery (exit-code bump,
`--advisory`, `--strict-placeholder`, per-row `[Pattern X]` labels)
is in production here.

---

## Appendix B — Cross-book parity summary (post-fix3)

| Book    | Files | Links | FILE_MISSING | ANCHOR_MISSING | READ_FAIL | Adapter exit |
| ------- | ----: | ----: | -----------: | -------------- | --------- | :----------- |
| kwavers | 110   | 512   | **0**        | 0              | 0         | **0 (strict), 0 (advisory)** |
| CFDrs   | 132   | 366   | **0**        | 0              | 0         | **0 (strict), 0 (advisory)** |
| helios  | 76    | 273   | **0**        | 0              | 0         | **0 (strict), 0 (advisory)** |
| **Sum** | 318   | 1151  | **0**        | 0              | 0         | —            |

0 findings across all 3 atlases post-§7-#5 — the strict-mode CI
gate flips cleanly.  12 CFDrs+helios Patterns C/D/E/F were cleared
by §7 #2 of the parent report; the 1 kwavers \[n+1\](x) FDTD-recurrence
false positive was cleared by Issue B of this report.

---

## Appendix C — Per-row Pattern × book matrix (post-fix3)

```
                 |  C  |  D  |  E  |  F  |  G/unclassified
CFDrs            |  0  |  0  |  0  |  0  |  0
helios           |  0  |  0  |  0  |  0  |  0
kwavers          |  0  |  0  |  0  |  0  |  0
Sum              |  0  |  0  |  0  |  0  |  0
```
**Total: 0** post-§7-#5 — strict-mode CI gate flips cleanly.  Pre-fix
totals (12 CFDrs+helios Patterns C/D/E/F + 1 kwavers Pattern G / FDTD
noise) were all resolved: 12 by §7 #2 of the parent report, 1 by Issue B
of this report.

Pattern G as proposed in earlier versions of this report is **withdrawn**;
the kwavers [n+1](x) match was an FDTD-recurrence false positive handled
by `SINGLE_CHAR_HREF_RE`.  `MDBOOK_LINK_WARNINGS.md`'s A–F taxonomy
remains intact (no A→G augmentation needed).
