# Parity Artefacts Archive (CI Gate Evidence)

This directory archives the **detector ↔ mdbook parity evidence chain**
that supports the strict-mode CI gate introduced in
[`MDBOOK_DETECTOR_PARITY.md`](../../MDBOOK_DETECTOR_PARITY.md) §7 #5 +
[`MDBOOK_DETECTOR_PARITY_KWAVERS.md`](../../MDBOOK_DETECTOR_PARITY_KWAVERS.md)
§3 Issue B.

The atlas physics books (CFDrs, helios, kwavers) each link to this
INDEX from their `docs/book/SUMMARY.md` appendix:

- **CFDrs** → [Appendix F](INDEX.md)
- **helios** → [Appendix F](INDEX.md)
- **kwavers** → [Appendix D](INDEX.md)

The link target must be a file (not a directory), per mdbook v0.5.4's
`SUMMARY.md [Title](path)` convention; pointing at the bare directory
emits `Access is denied. (os error 5)` during `mdbook build`.  This
INDEX is the canonical landing page that satisfies mdbook's file-based
chapter resolution.

## Per-book figure manifests

Each atlas mdbook commits its deterministic figure set under
`docs/book/figures/`. The manifest written by the per-repository
`xtask prebook` subcommand pins every figure to the byte fingerprint
of the file on disk; re-running `prebook` on unchanged inputs produces
a byte-identical `MANIFEST.json`, satisfying the CI deterministic-
evidence chain.

- **CFDrs** -- seven deterministic figures under
  `repos/CFDrs/docs/book/figures/`, regenerated into `MANIFEST.json`
  by `cargo run -p xtask -- prebook`; full list in
  [`repos/CFDrs/docs/book/README.md`](../CFDrs/docs/book/README.md).
- **helios** -- seven deterministic figures under
  `repos/helios/docs/book/figures/`, regenerated into
  `MANIFEST.json` by `cargo run -p xtask -- prebook`; full list in
  [`repos/helios/docs/book/README.md`](../helios/docs/book/README.md).
- **kwavers** -- figure set under `repos/kwavers/docs/book/figures/`.

## What this archive contains

| Subset | Files | Purpose |
| --- | --- | --- |
| **mdbook build logs** | `mdbook_<book>.log` | Full stdout/stderr per atlas physics book (CFDrs / helios / kwavers) — confirms `[WARN]` rows are zero across all 3 builds. |
| **detector logs (default)** | `det_<book>.log`, `det_<book>_final.log` | Strict-mode detector runs (no `--advisory`) per atlas; FILE_MISSING / ANCHOR_MISSING / READ_FAIL counts + per-row pattern labels. |
| **detector logs (advisory)** | `det_<book>_advisory*.log` | Historical advisory-mode runs used during the §7 #4 / §7 #5 flip triage. |
| **target enumerations** | `det_<book>_targets*.txt` | Pre-fix and post-fix FILE_MISSING target lists per book, used for diffing between fix iterations. |
| **parity diffs** | `url_overlap.txt`, `mdbook_detector_diff*.txt` | `comm -12` overlap + side-by-side comparison of mdbook warnings vs detector findings. |
| **flight-test logs** | `p{1..13}_strict_<book>.log`, `p{1..13}_<book>_postfix.log` | Strict-mode flight-test iterations across the §7 #2 → #6 sequence. |
| **fix3 audit** | `det_kwavers_targets_postfix2.txt`, `p_q7_4_detector.log` | kwavers-only post-fix2 + post-fix3 evidence for the Pattern A LaTeX-noise resolution and Pattern G detection. |
| **link-check pre-flight** | `p10_strict_*.log`, `p11_strict_*.log`, `p12_strict_*.log`, `p13_strict_*.log` | Final strict-mode confirmation logs (exit 0, FILE_MISSING 0) across all 3 atlases. |

**Total**: 43 files / ~33.8 KB / 0 binary objects.

## How to use this archive

1. **Reproduce a CI run locally.**  Any developer can re-run the strict
   gate with:
   ```bash
   python3 scripts/check_mdbook_links.py \
     repos/CFDrs/docs/book \
     repos/helios/docs/book \
     repos/kwavers/docs/book
   mdbook build repos/CFDrs/docs/book
   mdbook build repos/helios/docs/book
   mdbook build repos/kwavers/docs/book
   ```
   The expected outcome is `exit 0` + `FILE_MISSING : 0` for each atlas,
   matching the archived `p13_strict_<book>.log` evidence.

2. **Audit a particular fix iteration.**  Compare
   `det_<book>_targets_prefix.txt` (broken links before fix) against
   `det_<book>_targets_postfix.txt` (after fix) — the difference is the
   set of broken links the fix resolved.

3. **Triage a future Pattern G-style false positive.**  Re-run the
   detector on the failing chapter and diff against
   `det_<book>_final.log`; if a row appears with a similar shape to a
   `[X](<single-char>)` recurrence, mirror the
   `SINGLE_CHAR_HREF_RE` precedent (see
   `MDBOOK_DETECTOR_PARITY_KWAVERS.md` §3 Issue B).

## CI gate pipeline summary

```
  pull_request (paths-filtered) ──► docs-invariant workflow
                                       │
                                       ├─► detector step (STRICT mode)
                                       │     exit 1 on FILE_MISSING > 0
                                       │
                                       ├─► mdbook build × 3
                                       │     exit 0 expected
                                       │
                                       └─► upload-artifact × 4
                                             detector-log + 3 × book/
```

The two evidence channels (this archive vs. CI-side artefacts) are
**independent**:

- **CI-side artefacts** (`.github/workflows/docs.yml`): `detector.log`
  at workspace root + 3 per-book `book/` HTML directories.  These are
  uploaded per-run for the specific PR/commit under review.
- **On-disk archive** (`repos/parity_artefacts/`): persistent snapshot
  of all detector + mdbook runs across the §7 #1 → §7 #6 sequence.
  Survives repo re-clones + provides reproducible baseline for local
  audits.

## Cross-references

- [`MDBOOK_DETECTOR_PARITY.md`](../../MDBOOK_DETECTOR_PARITY.md) — parent
  parity report (CFDrs + helios).  Headline: **Detector ⊇ mdbook
  HOLDS** post-§7-#5.
- [`MDBOOK_DETECTOR_PARITY_KWAVERS.md`](../../MDBOOK_DETECTOR_PARITY_KWAVERS.md)
  — kwavers-specific report.  Headline: same property after Issue B
  filter (FDTD-recurrence `[n+1](x)` false positive).
- [`scripts/check_mdbook_links.py`](../../scripts/check_mdbook_links.py)
  — the portable detector itself (anchored in the repo root).
- [`.github/workflows/docs.yml`](../../.github/workflows/docs.yml)
  — the CI gate wiring.
- [`.git/hooks/pre-commit`](../../.git/hooks/pre-commit)
  — the local-developer mirror of the gate.

## Maintenance

This archive is **append-only**.  When the next fix iteration lands
(e.g. adding `mdbook test` as a complementary validator per §6
Caveats), save the new logs as `p14_<book>.log` (or the next
sequence number) under this directory rather than overwriting existing
ones.  This preserves the evidence chain's audit trail.