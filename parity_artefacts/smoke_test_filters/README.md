# Detector filter regression — consolidated smoke-test fixture

This directory holds the **regression fixture** that proves both
inline-link false-positive filters in
`scripts/check_mdbook_links.py` are still suppressing their respective
false-positive patterns on every CI run.

## Contents

| File                              | Role                                                                   |
| --------------------------------- | ---------------------------------------------------------------------- |
| `README.md`                       | This file — fixture purpose + how to run + integration notes.          |
| `SUMMARY.md`                      | 2-chapter index (detector scans both chapters in one book walk).       |
| `src/single_char_filter.md`       | Chapter exercising the `SINGLE_CHAR_HREF_RE` filter (FDTD recurrences). |
| `src/latex_filter.md`             | Chapter exercising the `LATEX_HREF_RE` filter (LaTeX-cmd math notation). |

## Why this fixture exists

The portable detector's inline-link regex
``\[[^\]]*\]\(([^)\n]+)\)`` over-grips math notation that happens to
look like markdown links.  Two detector-side filters suppress the
respective false-positive classes:

```python
SINGLE_CHAR_HREF_RE = re.compile(r"^[a-zA-Z]$")  # FDTD recurrence: [n+1](x)
LATEX_HREF_RE       = re.compile(r"^\\[A-Za-z]+")  # LaTeX-cmd: [F(m)](\mathbf{r}_s, t)
```

Both filters are applied inside ``extract_links()`` *before* the
``links_scanned`` counter increments, so a false-positive href that the
filter correctly drops contributes zero to ``FILE_MISSING``.

Historical context:
- `MDBOOK_DETECTOR_PARITY_KWAVERS.md §3.2 Issue B` — kwavers `[n+1](x)` FDTD recurrence
- `MDBOOK_DETECTOR_PARITY_KWAVERS.md §3 Issue A`    — kwavers `[F(m)](\mathbf{r}_s, t)` LaTeX-cmd math bracket

Both filters landed as part of §7 #1 / §7 #5 detector-side fixes; this
fixture is the consolidated permanent regression guard.

## How to run manually

```bash
# Positive test (both filters ON): must report FILE_MISSING : 0 and exit 0
python3 scripts/check_mdbook_links.py parity_artefacts/smoke_test_filters

# Negative test (both filters OFF): must report FILE_MISSING > 0 and exit 1
PYTHONPATH=scripts python3 -c "
import re
import check_mdbook_links as m
m.SINGLE_CHAR_HREF_RE = re.compile(r'(?!)')   # never match
m.LATEX_HREF_RE       = re.compile(r'(?!)')   # never match
raise SystemExit(m.main(['parity_artefacts/smoke_test_filters']))
"
```

If the positive test ever reports ``FILE_MISSING > 0``, one of the two
filters has regressed — inspect ``extract_links()`` in
``scripts/check_mdbook_links.py`` before merging any detector refactor.
Do NOT silence the regression with an allow-list entry; the filters
are supposed to drop these patterns detector-wide.

## CI integration

This fixture is exercised by the ``docs-link-smoke-test-filters`` job
in `.github/workflows/docs.yml`.  The job runs the detector on this
fixture and fails CI if ``FILE_MISSING > 0``.  The job triggers when
any of the following change:

- `scripts/check_mdbook_links.py` (detector edit)
- `parity_artefacts/smoke_test_filters/**` (fixture edit)
- `.github/workflows/docs.yml` (workflow edit)
- `MDBOOK_DETECTOR_PARITY_KWAVERS.md` (historical-context edit)

Replaces the earlier per-filter jobs (`docs-link-smoke-test` for
`SINGLE_CHAR_HREF_RE` + `docs-link-smoke-test-latex` for
`LATEX_HREF_RE`).