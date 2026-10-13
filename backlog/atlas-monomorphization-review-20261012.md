<a id="atlas-monomorphization-review-20261012"></a>
## ATLAS-MONOMORPHIZATION-REVIEW-20261012 — Stack redundancy review: adjudicated families + open twins [patch] — todo
outcome: every counted type_suffixed_fns family is either consolidated or adjudicated with evidence; the two open twin sets have owners and verification paths.
background: measured review 2026-10-12 with the checker's own detector (TYPE_NAME + split_test_region, never crude grep — crude `fn *type*` greps overcount 2-5x via tests/probes/conversions); hephaestus already consolidated 29 -> 0 via UpdateWidth genericization + 8 role renames + 4 wrapper deletions.
adjudicated (keep; churning = negative value): ritk jpeg2000/dicom/nifti readers (format-dictated widths are distinct format tokens); consus thrift zigzag/field/readers (merging pushes type codes to call sites); consus hdmf typed dataset entry points (caller-visible dtype API); apollo pinned_probe/plan_tests/lib_tests (test-gated scaffolding); apollo python require_profile_matches_* (boundary validators); eunomia/coeus to_/from_ conversions (detector-exempt by design).
open twins (apollo DONE, consus landing): apollo fwht/gft consolidated in #652 (merged aa5adba1) - wht_inplace_f32/f64 wrappers deleted, 20 per-crate validators collapsed into 2 apollo-fft owner entry points, instrument 16 -> 14 with per-site adjudication of the remaining 14 (single-kernel f64 slice paths, pool-arity workspaces, boundary validators, lone layout parsers). consus hdmf in #171 (armed green) - decode arms delegate to core decode_to_u64, 5 readers share one helper, public dtype names kept as caller-visible API.
acceptance: open sets consolidated or re-adjudicated with counts from the instrument at the landing rev.
priority: tightening
needs: none
scope: repos/apollo, repos/consus
next: collect consus #171 auto-merge, verify the landing rev with the instrument, then close.
basis: apollo aa5adba1 (merged #652); consus main cf30dc2 plus PR #171 (open, green, auto-merge armed).
progress 2026-10-13: corrects the 2026-10-12 line - PR #650 never merged (still open draft), so nothing credited to it is delivered; the validator collapse landed instead as #652. Main verified on this date with zero cp1252 double-encoding hits and none of the four orphaned NUFFT GPU siblings present. Residuals in gap_audit.md (profile tier conflation; whole-file-writer encoding) stand; leto bessel_k0 still duplicates under ATLAS-BESSEL-CORE-001; kwavers k0 typo still live under ATLAS-KWAVERS-K0-COEFFICIENT-001.
parked: apollo rescue ref refs/rescue/apollo-scratch-order-isolation holds a defect-masking scratch_hook weakening that must not be applied (see apollo-fft-scratch-test-order-dependence-2026-10-08); its isolation hunk belongs to that item.
co-evolution note: hephaestus 0.20.2 requires moirai ^0.8.2 while leto 0.45.x required moirai ^0.7.0, blocking any single-sweep advance; resolved via build/apollo-moirai-0.8 (#648) and leto 0.45.2.
