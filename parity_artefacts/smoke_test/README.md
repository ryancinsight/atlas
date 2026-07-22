# SINGLE_CHAR_HREF_RE filter — regression smoke-test fixture

This directory holds the **regression fixture** that proves the
`SINGLE_CHAR_HREF_RE` filter in `scripts/check_mdbook_links.py` is
still suppressing finite-difference recurrence false positives on
every CI run.

## Contents

| File                              | Role                                                                   |
| --------------------------------- | ---------------------------------------------------------------------- |
| `README.md`                       | This file — fixture purpose + how to run + integration notes.          |
| `SUMMARY.md`                      | 1-line chapter index (detector scans it; confirms the indexer works). |
| `single_char_href_regression.md`  | The chapter. Contains math notation that exercises the filter.         |

## Why this fixture exists

The portable detector's inline-link regex
``\[[^\]]*\]\(([^)\n]+)\)`` over-grips finite-difference recurrence
notation like ``p[n+1](x)``, treating ``[n+1](x)`` as a markdown link
with href ``x``.  Without the ``SINGLE_CHAR_HREF_RE`` filter, every
kwavers chapter that uses FDTD or PDE recurrences would inflate the
``FILE_MISSING`` count with phantom broken links.

The filter:

```python
SINGLE_CHAR_HREF_RE = re.compile(r"^[a-zA-Z]$")
```

is applied inside ``extract_links()`` to skip single-character hrefs
that overwhelmingly come from math recurrence / indexed-call notation
rather than real markdown links.

Historical context: `MDBOOK_DETECTOR_PARITY_KWAVERS.md` §3.2 Issue B.
The filter landed as part of the §7 #5 strict-mode gate flip.

## How to run manually

```bash
# Positive test (filter ON): must report FILE_MISSING : 0 and exit 0
python3 scripts/check_mdbook_links.py parity_artefacts/smoke_test

# Negative test (filter OFF): must report FILE_MISSING > 0 and exit 1
PYTHONPATH=scripts python3 -c "
import re
import check_mdbook_links as m
m.SINGLE_CHAR_HREF_RE = re.compile(r'(?!)')   # never match
raise SystemExit(m.main(['parity_artefacts/smoke_test']))
"
```

If the positive test ever reports ``FILE_MISSING > 0``, the
``SINGLE_CHAR_HREF_RE`` filter has regressed — inspect
``extract_links()`` in ``scripts/check_mdbook_links.py`` before
merging any detector refactor.

## CI integration

This fixture is exercised by the ``docs-link-smoke-test`` job in
`.github/workflows/docs.yml`.  The job runs the detector on this
fixture and fails CI if ``FILE_MISSING > 0``.  The job triggers when
any of the following change:

- `scripts/check_mdbook_links.py` (detector edit)
- `parity_artefacts/smoke_test/**` (fixture edit)
- `.github/workflows/docs.yml` (workflow edit)
- `MDBOOK_DETECTOR_PARITY_KWAVERS.md` (historical-context edit)