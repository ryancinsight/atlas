# FDTD Recurrence Regression Test

This chapter is the **regression fixture** for the `SINGLE_CHAR_HREF_RE`
filter in `scripts/check_mdbook_links.py`.  The `docs-link-smoke-test`
job in `.github/workflows/docs.yml` runs the portable detector over
this file on every CI run that touches the detector or this fixture.

## Why this chapter exists

The portable detector's inline-link regex
``\[[^\]]*\]\(([^)\n]+)\)`` over-grips finite-difference recurrence
notation like ``p[n+1](x)``, treating ``[n+1](x)`` as a markdown link
with href ``x``.  Without the ``SINGLE_CHAR_HREF_RE`` filter, this
chapter (and every kwavers chapter that uses FDTD or PDE recurrences)
would inflate the ``FILE_MISSING`` counter with phantom broken links.

The filter is:

```python
SINGLE_CHAR_HREF_RE = re.compile(r"^[a-zA-Z]$")
```

applied inside ``extract_links()`` to drop single-character hrefs that
overwhelmingly come from math recurrence / indexed-call notation
rather than real markdown links.

Historical context: see `MDBOOK_DETECTOR_PARITY_KWAVERS.md` §3.2
Issue B.  The filter landed as part of the §7 #5 strict-mode gate
flip; this fixture is its permanent regression guard.

## Patterns this chapter exercises

Each line below contains a recurrence or math-bracket pattern that
**would** register as a broken markdown link if the filter were
disabled or refactored away.  With the filter enabled, every one is
silently dropped before reaching the ``FILE_MISSING`` counter:

- Finite-difference recurrence: $p^{n+1}(x) = p^n(x) + \Delta t \cdot f(x)$
- Indexed function call: ``p[n+1](x)`` evaluates the field at time n+1, position x
- Bracket notation: ``[F(m)](x)`` denotes the function F evaluated at index m, position x
- Single-letter variable: ``g(x)`` is a generic function at position x
- Temporal step: ``[u^{n+1}](y)`` updates field u at next time step
- Mixed: ``p[n](x)``, ``p[n-1](x)``, ``q[n+1](y)`` are all FDTD cells

## Real markdown links (positive control)

These are real markdown links that the detector must still scan and
validate.  They all resolve to existing files at atlas root or within
this fixture:

- See the [parent parity report](../../MDBOOK_DETECTOR_PARITY.md).
- See the [kwavers parity report](../../MDBOOK_DETECTOR_PARITY_KWAVERS.md).
- See the [allow-list](../../.check_mdbook_links_allowlist).
- See the [detector source](../../scripts/check_mdbook_links.py).
- See the [smoke-test README](README.md).

## Expected detector output

When the ``SINGLE_CHAR_HREF_RE`` filter is functioning correctly, the
detector must yield exactly:

```
== smoke_test ==
  files scanned : 3
  links scanned : 6
  FILE_MISSING  : 0
  ANCHOR_MISSING: 0
  READ_FAIL     : 0
```

If ``FILE_MISSING`` is non-zero, the filter has regressed — investigate
``extract_links()`` in ``scripts/check_mdbook_links.py`` immediately.
Do NOT silence the regression with an allow-list entry; the filter is
supposed to drop these patterns detector-wide.