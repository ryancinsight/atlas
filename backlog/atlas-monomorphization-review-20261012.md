<a id="atlas-monomorphization-review-20261012"></a>
## ATLAS-MONOMORPHIZATION-REVIEW-20261012 — Stack redundancy review: adjudicated families + open twins [patch] — todo
outcome: every counted type_suffixed_fns family is either consolidated or adjudicated with evidence; the two open twin sets have owners and verification paths.
background: measured review 2026-10-12 with the checker's own detector (TYPE_NAME + split_test_region, never crude grep — crude `fn *type*` greps overcount 2-5x via tests/probes/conversions).
adjudicated (keep; churning = negative value): ritk jpeg2000/dicom/nifti readers (format-dictated widths, e.g. read_u8/u16/u32 are distinct format tokens); consus thrift zigzag/field/readers (merging pushes type codes to call sites — worse API); consus hdmf typed dataset entry points (caller-visible dtype API); apollo pinned_probe/plan_tests/lib_tests (test-gated scaffolding); apollo python require_profile_matches_* (boundary validators); eunomia/coeus to_/from_ conversions (detector-exempt by design).
consolidated: hephaestus 29 -> 0 via UpdateWidth genericization (owner, post review) + 8 role renames + 4 wrapper deletions.
open twins (not started): apollo fwht/gft wht_inplace_f32/f64 + forward/inverse_f64_slice_into + with_f64/f32_workspaces (dirty checkout, owner slice); consus hdmf read/decode_as per-dtype families (needs owner dtype-dispatch design call).
acceptance: open sets consolidated or re-adjudicated with counts from the instrument at the landing rev.
priority: tightening
needs: none
scope: repos/apollo, repos/consus
next: claim one open set with a clean tree; verify with the instrument + affected crate gates.
basis: atlas 547d87b2; tips measured 2026-10-12 (ritk 117e00a1, consus a239db4d, apollo f97fc7ae-era, hephaestus 39eb7f3).
