# LATEX_HREF_RE Regression Test

This chapter exercises the `LATEX_HREF_RE` filter in
`scripts/check_mdbook_links.py`.  The `docs-link-smoke-test-filters`
job in `.github/workflows/docs.yml` runs the portable detector over
this file on every CI run that touches the detector or this fixture.

## Why this chapter exists

The portable detector's inline-link regex
``\[[^\]]*\]\(([^)\n]+)\)`` over-grips LaTeX math notation like
``[F(m)](\mathbf{r}_s, t)``, treating ``[F(m)]`` as a markdown link
with href ``\mathbf{r}_s, t``.  Without the ``LATEX_HREF_RE`` filter,
this chapter (and every kwavers chapter that uses PDE / operator /
transform notation) would inflate the ``FILE_MISSING`` counter with
phantom broken links.

The filter is:

```python
LATEX_HREF_RE = re.compile(r"^\\[A-Za-z]+")
```

applied inside ``extract_links()`` to drop hrefs that start with a
LaTeX command (``\alpha``, ``\mathbf``, ``\nabla``, ``\partial``,
``\mathcal``, ``\hat``, etc.) — they are math notation, not real
markdown links.  Real chapter hrefs almost never start with a backslash.

Historical context: see `MDBOOK_DETECTOR_PARITY_KWAVERS.md §3 Issue A`.
The filter landed as part of the §7 #1 detector-side fix; this chapter
is its permanent regression guard.

## Patterns this chapter exercises

7 categories (8 patterns) of LaTeX-cmd math-bracket notation below
exercise the ``LATEX_HREF_RE`` filter.  Each **would** register as a
broken markdown link if the filter were disabled or refactored away;
with the filter enabled, every one is silently dropped before reaching
the ``FILE_MISSING`` counter:

- Operator notation: ``[F(m)](\mathbf{r}_s, t)`` is the force on particle m at position $\mathbf{r}_s$ and time $t$
- Greek-letter notation: ``[G(x)](\alpha + \beta)`` evaluates the function $G$ with parameters $\alpha + \beta$
- Gradient notation: ``[u(t)](\nabla f)`` is the field $u$ at time $t$, driven by the gradient of $f$
- Partial derivative: ``[p](\partial_t q)`` is the pressure rate-of-change, defined by the partial time-derivative of $q$
- Hat notation: ``[H](\hat{x}_i)`` is the Hamiltonian evaluated at the unit vector $\hat{x}_i$
- Fourier transform: ``[K(x,y)](\mathcal{F}\{f\}(x,y))`` is the kernel at $(x,y)$, given by the Fourier transform of $f$
- Mixed: ``[D](\nabla \cdot \mathbf{E})``, ``[B](\nabla \times \mathbf{B})`` are Maxwell-equation operators

## Real markdown links (positive control)

These are real markdown links that the detector must still scan and
validate.  They all resolve to existing files at atlas root or within
the fixture tree:

- See the [parent parity report](../../../MDBOOK_DETECTOR_PARITY.md).
- See the [kwavers parity report](../../../MDBOOK_DETECTOR_PARITY_KWAVERS.md).
- See the [sibling chapter](single_char_filter.md) (the SINGLE_CHAR_HREF_RE regression test).

## Expected detector output (consolidated fixture)

When the ``LATEX_HREF_RE`` filter is functioning correctly, the
detector must report ``FILE_MISSING : 0`` across the whole
`parity_artefacts/smoke_test_filters/` fixture (this chapter +
`single_char_filter.md` + SUMMARY.md + README.md).  If ``FILE_MISSING``
is non-zero, the filter has regressed — investigate
``extract_links()`` in ``scripts/check_mdbook_links.py`` immediately.
Do NOT silence the regression with an allow-list entry; the filter is
supposed to drop these patterns detector-wide.