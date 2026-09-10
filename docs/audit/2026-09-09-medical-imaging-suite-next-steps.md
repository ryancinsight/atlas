# Audit 2026-09-09: next steps toward a medical-imaging-capable multiphysics suite

- Scope: the Atlas meta-repository and the members that carry imaging, imaging
  simulation, image-driven physics, and presentation.
- Method: read-only. Board and doctrine from `backlog.md`, `checklist.md`,
  `gap_audit.md`, `README.md`, `docs/adr/`; capability claims checked against
  source in `repos/ritk`, `repos/helios`, `repos/kwavers`, `repos/metis`,
  `repos/leoneuro-rs`.
- Status: findings only. No source was modified and no gitlink was advanced.

## Summary

The stack is not missing a medical-imaging package and does not need one. It
already owns the bounded context: `ritk` is a 41-crate, ~358k-line, zero-stub
medical-image platform on Coeus tensors with real DICOM, registration,
diffusion, tractography, and connectome capability. What is missing is narrower
and more specific: **no integrator closes the loop from a physics solve to a
reconstructed image**, and **the image-to-material bridge is first-order and
duplicated**. Both are seam work, not new packages, and both already have an
owner or an ADR waiting on implementation.

A second, separable finding: the machine that would carry that work is red.
The stack overlay gate is failing on every push to main behind one `rev` pin,
and two members have working trees that cannot be gated. That is the first
thing to clear, because nothing below is verifiable until it is.

## 1. What exists today

| Capability | Owner | State | Evidence |
| --- | --- | --- | --- |
| Image I/O, 15+ formats | `ritk` | strong | `ritk-io`, `ritk-dicom`, `ritk-nifti`, `ritk-nrrd`, `ritk-mgh`, `ritk-minc`, `ritk-vtk`, `ritk-mif`, `ritk-trk`/`tck`/`trx` |
| DICOM read | `ritk` | strong | ~30 SOP classes incl. RTSTRUCT/RTPLAN/RTDOSE; all major transfer syntaxes incl. JPEG-LS/JPEG2000/JXL; DICOMDIR validation delivered (`ATLAS-RITK-DICOMDIR-001`, done) |
| Registration | `ritk` | strong | rigid, affine, Demons x5, SyN/diffeomorphic, B-spline FFD, LDDMM, metrics MSE/NCC/LNCC/MIND/NGF |
| Diffusion, tractography, connectome | `ritk` | real | `ritk-diffusion` (DTI/DKI/NODDI/CSD/ODF), `ritk-tractography`, `ritk-connectome`, `ritk-parcellation` — ADR 0036 satisfied in placement |
| Radiographic reconstruction | `helios-imaging` | real, narrow | parallel-beam Radon, spatial-domain FBP, SIRT, MVCT Poisson noise, whole-voxel translation SSD/NCC |
| Beamforming and Doppler | `kwavers-analysis` | strong | DAS, MVDR/Capon/MUSIC/SMI, SLSC, 3-D, GPU; color-flow/PW/CW/vector Doppler; TGC, envelope, log-compress, scan conversion |
| Ultrasound physics | `kwavers` | strong | 680k LOC, ~7.2k tests, zero `todo!` |
| Therapy dose and planning | `helios` | real, unvalidated | source → transport → TERMA → collapsed-cone → DVH/gamma → Asclepius TCP/NTCP |
| Presentation shell | `metis` | in development | explicitly does not parse DICOM or define volume semantics; hands bytes to RITK |
| Shared deposition spine | `aequitas` + integrators | delivered | `ATLAS-MODALITY-002`, recorded with five commits in the closed ledger (`backlog.md:13031`) |

## 2. The four findings that define the remaining work

### F1 — No integrator runs solve → raw data → image

This is the gap that separates "a physics stack that can read an image" from a
suite that *supports medical imaging*.

- `kwavers` has excellent beamforming and no pipeline feeding it. RF is
  synthesized: `crates/kwavers/examples/advanced_ultrasound_imaging.rs`
  (`generate_synthetic_sa_rf_data`, `generate_synthetic_pw_rf_data`), and
  `crates/kwavers-diagnostics/src/workflows/simulation.rs::generate_realistic_rf_volume`.
- Worse, `crates/kwavers/examples/comprehensive_clinical_workflow/execution.rs:101`
  — `perform_b_mode_imaging` — is a hardcoded zero-filled `Array3` with literal
  0.3 mm / 0.8 mm / 25.0 constants. A function named for the clinical output
  returns a fake. This is a correctness defect before it is a roadmap item.
- The only genuine end-to-end B-mode is analytical IVUS:
  `crates/kwavers-physics/src/analytical/imaging.rs` → `ivus_polar_bmode_rf` →
  `ivus_bmode_image` → `ivus_scan_convert`.
- `helios` has no cone- or fan-beam projection at all, so no CT/CBCT
  acquisition simulation, no DRR, and no statistical reconstruction
  (MLEM/OS-SEM).

### F2 — The image-to-material bridge is first-order and duplicated

This is the seam where a medical image becomes a physics domain. It is currently
the weakest link in the stack and it is copy-pasted.

- `crates/helios-physics/src/ct_calibration.rs:11` —
  `relative_electron_density_from_hu` is `max(0, 1 + HU/1000)`. No
  stoichiometric calibration, no stopping-power table.
- `crates/helios-solver/src/attenuation_map.rs:58` — "material-segmented model
  is a later refinement". There is no HU → material segmentation.
- `helios` does this without `ritk` or `proteus`. `kwavers-imaging` carries its
  own `medical/ct_loader` and `medical/dicom_loader`; `repos/leoneuro-rs`
  carries a third CT → acoustic-medium path.

Three consumers of one conversion is exactly the promotion-gate condition that
ADR 0055 exists to catch. Under that axis the conversion is a **closure**
(pointwise, no field advance), so it belongs in `proteus`, not in `helios`.

### F3 — Two accepted ADRs are unimplemented, and they are the load-bearing ones

- **ADR 0048** (B-mode scan conversion through the `ritk` `CoordinateMap` seam)
  is Accepted. It is not done. `crates/kwavers-imaging/src/medical/ritk_bridge.rs`
  is a NIfTI/DICOM *volume* bridge, not scan conversion. The bespoke
  `ScanConverter` still exists in `kwavers-analysis`; `kwavers-analysis` depends
  on `ritk-spatial` only, never `ritk-image`. Deletion plus the differential
  oracle (≤ 0.5 intensity unit) are pending.
- **ADR 0042 / 0047** (acquisition coordinate maps, slice-series maps) are
  Accepted and are **spec-only in kwavers**: zero occurrences of
  `CoordinateMap`, `AcquisitionCoordinateMap`, or `SliceSeries` in any `.rs`
  file under `crates/`. Only `CurvilinearArray` is consumed. Until these are
  real, every beam-space acquisition geometry gets reinvented per modality,
  which is the duplication the ADRs were written to end.

### F4 — Nobody owns interpolation, and imaging is the case where that binds

ADR 0059 records it: Harmonia's transfers are `IdentityTransfer` and
`IndexTransfer`, index-shaped, no interpolation, and ADR 0050 states plainly
that Harmonia does not interpolate nonmatching meshes. ADR 0059 accepted that
as a Phase 0 precondition for fluid-structure coupling.

For imaging it is not a precondition, it is the daily case. Registering an
image grid to a solver mesh is inherently non-conforming. Today the answer is
"the caller resamples first", which means each integrator grows its own
resample-and-transfer path — the duplication that produced F2.

## 3. Blockers to clear before any of the above

| Item | Board | Why it blocks |
| --- | --- | --- |
| Apollo's `rev` pin on Moirai | [`ATLAS-APOLLO-MOIRAI-QUARANTINE-LIFT`](../../backlog.md#atlas-apollo-moirai-quarantine-lift) — **blocked** | The stack overlay gate is red on every push to main. `athena`'s lock cannot regenerate at all (`failed to select a version for the requirement moirai-runtime = "^0.5.0"`). Eight members carry the transitive pin. Highest-leverage item in the repo. |
| 61 files of stale unique work in the coeus tree | `ATLAS-COEUS-ABANDONED-WIP-2026-09-09` — todo | `repos/coeus` sits on a merged branch with 67 uncommitted paths; 61 differ from `origin/main`, so it is unique work, not scratch. Nothing in coeus can be gated, and `ritk` and `helios` both run on coeus. |
| Cargo outside the overlay forks the cache | [`ATLAS-TARGET-FORK-REGRESSION-2026-09-09`](../../backlog.md#atlas-target-fork-regression-2026-09-09) — review | Regrowth: a 7.5 GB `target/` returned after cleanup. Build results are not trustworthy across the overlay boundary. |
| `ryancinsight/prometheus` does not exist | [`ATLAS-PROMETHEUS-PROMOTION-2026-09-03`](../../backlog.md#prometheus-promotion) — in-progress | Phase 0 computation is done locally (11 commits, Robertson stiff benchmark through the Horae implicit seam). Nothing can be pushed, registered, or CI-wired. **Requires a user decision.** |
| `proteus-mat` is not on crates.io | checklist, Ares A9 | `cargo publish --dry-run` fails for `ares-solid`. Ares A0–A8 are done; A9 is blocked on a dependency, not on authority. |
| Six members have no branch protection | `gap_audit.md`, Finding 2026-09-09 | hermes, eunomia, leto, mnemosyne, moirai, themis enforce no merge gate. Do not import `strict` without `allow_update_branch` — that is the stall the same finding just cured. |
| A check that fails on every PR | `ATLAS-THIRD-PARTY-CHECK-ALWAYS-RED-2026-09-09` — todo | Nine of ten sampled members show a red `recurseml/analysis` X on every PR. Each reviewer pays to learn to ignore it, which is the habit the merge gate depends on nobody having. |

## 4. Sequenced next steps

### Gate 0 — make the stack verifiable again

1. **Lift the Apollo Moirai `rev` pin.** Drop `rev = "83aa411"`, move
   `moirai-runtime` 0.5.0 → 0.6.0 across the root manifest and the nineteen
   crate manifests, regenerate the lock outside the overlay, then one
   `atlas-lock-sweep.py apollo-fft --rev <new head>`. Acceptance:
   `scripts/atlas-stack-overlay.py check` prints `stack aligned:`. Blocked on
   the apollo tree; disjoint from both live apollo lanes.
2. **Resolve the coeus working tree.** Infer the 61-file delta from the diff and
   either land it under its own item or show it superseded. Do not revert.
3. **Decide the two asks:** create `ryancinsight/prometheus`; publish
   `proteus-mat` (or record a decision to defer Ares A9).

### Gate 1 — close the imaging loop (F1, F3)

4. **Delete the fake.** Replace `perform_b_mode_imaging` in
   `comprehensive_clinical_workflow/execution.rs` with real receiver output into
   the beamformer, or delete the example. Shipping a fabricated B-mode under a
   clinical name is the kind of defect that discredits everything around it.
5. **Build solver → RF → B-mode** as a real path in `kwavers`: receiver output
   → TGC → envelope → log-compress → scan conversion. Oracle: the analytical
   IVUS path that already exists and is correct.
6. **Implement ADR 0042/0047 coordinate maps**, then **ADR 0048**: attach
   `CoordinateMap::CurvilinearArray` to the RF `ritk_image::Image`, resample
   through `ritk-image`, delete `ScanConverter`, keep the differential oracle.
   Order matters — 0048 without 0042 means composing against a seam that does
   not exist yet.
7. **Persist RF and B-mode through `consus-hdf5`.** ADR 0046 is honoured for
   input only (`breast_ust_fwi/phantom_hdf5/`); there is no output writer.
8. **Decide harmonic imaging.** The `UltrasoundMode::Harmonic` variant exists
   and is unused. Either implement or remove the variant; do not leave an enum
   promising a capability the suite does not have.

### Gate 2 — the image-to-material seam (F2)

9. **Move HU → material into `proteus`.** Three consumers now exist
   (`helios-physics`, `kwavers-imaging`, `leoneuro`), which is the second-consumer
   condition. Scope: stoichiometric calibration, stopping-power table, and
   HU → material segmentation — the three things `helios` explicitly lacks
   today. Classify it as a closure domain per ADR 0061's test: read the public
   surface for a balance operator; a calibration curve has none.
10. **Reconcile helios's declared-but-unconsumed edges.** `helios` declares
    `ritk-core`, `ritk-io`, `ritk-registration`, and `apollo`, and consumes
    none of them, while hand-rolling registration in
    `helios-imaging/src/registration.rs` and building a spatial ramp in
    `fbp.rs`. Either consume and delete, or drop the edge. A declared edge that
    no one uses is worse than no edge: it makes the provider graph lie.

### Gate 3 — interpolation ownership (F4)

11. **Write the ADR before the code.** The options are a conservative or
    superelement projection in `harmonia` — which contradicts ADR 0050's stated
    scope and needs an amendment — or a geometry-owned transfer in `gaia`.
    ADR 0059 rejected putting it in a balance package. This needs a decision
    record, not a pull request.

### Gate 4 — verification credibility

12. **Give `helios` one external reference.** Today its verification tier is
    analytical-oracle and differential only: no measured beam data, no TG-119,
    no TOPAS/GATE/EGSnrc comparison, and all ten GPU tests are `#[ignore]`d.
    For a product adjacent to clinical use, one published dataset comparison
    moves it from "internally consistent" to "comparable".
13. **Close the `ritk-snap` P0s.** `RITK-SNAP-FUSION-001` and
    `RITK-SNAP-COORDINATES-001` are todo; `RITK-SNAP-FRAMES-001` is in
    progress. Multiframe opening remains open. Add DICOM write on the native
    substrate (`ritk-io/src/dispatch.rs:281`) — a suite that can read every
    format and write none is a viewer, not a pipeline.

## 5. One decision to make explicitly

`repos/leoneuro-rs` is a **private external code drop** (LeoNeuro-INC), absent
from `.gitmodules` and therefore not part of the recorded stack; that rule was
confirmed as intentional. But it is the only place in this workspace where the
whole chain actually runs:

```text
brain CT + MRI (NIfTI/DICOM) → ritk registration (multi-res rigid→affine, cross-modal MI)
  → SSS lumen mask → centerline polyline (leoneuro-vessel)
  → stent-conformal transducer array (leoneuro-array)
  → acoustic field: analytical Rayleigh–Sommerfeld (leoneuro-field) + kwavers PSTD (leoneuro-sim)
  → neuromodulation (leoneuro-neuromod)
  → NIfTI pressure field + device STL/GIFTI
```

Two options, and the current state — carrying it locally while the board records
it as out of contract — is the worse third one:

- **(a) Treat it as the first-consumer specification.** Upstream its reusable
  seams into the owning members: vessel centerline and polyline geometry to
  `gaia` (ADR 0036 already names the missing polyline type as an upstream gap),
  CT → acoustic medium to `proteus` (Gate 2 step 9), transducer-on-centerline
  to `kwavers-transducer`. Its gaps are the stack's gaps.
- **(b) Record it formally as out of contract** and stop carrying its tree in
  the stack checkout.

Recommendation: (a), because its four reusable seams are precisely F1, F2, and
the `gaia` polyline gap, and because it is the only end-to-end evidence that the
suite's compositions work at all.

## 6. What not to build

Recorded so the next audit does not reopen them:

- **No neuroimaging package.** ADR 0036 placed diffusion, tractography, and
  connectomics as `ritk` workspace crates. The crates exist. Gate 1 and 6
  remain unmet for a separate repository — `ritk` is the only consumer.
- **No optics, RF, or MR-acquisition package.** ADR 0032 and ADR 0036 defer all
  three with named triggers. MR *acquisition* simulation (Bloch, k-space,
  sequence timing) is demand-gated and has no consumer; MR *image processing*
  is `ritk`'s and is done.
- **No in-stack UI framework and no universal model tree.** Retracted on
  verification under `ATLAS-APPLICATION-LAYER-GAP`; the frontend/backend split
  is the asset.
- **No `astrape` (electromagnetics) or `daedalus` (parametric CAD) yet.** Both
  are recorded with provisional names and neither meets the first gate
  condition. Do not widen `hyperion` into `astrape` — ADR 0032 already declined
  that.

## 7. Evidence index

- Board: `backlog.md#next-steps` (the sequenced plan toward the suite, status
  `planning`), `backlog.md#prometheus-promotion`.
- Doctrine: ADR 0032, 0036, 0042, 0047, 0048, 0050, 0055, 0056, 0057, 0058,
  0059, 0061 in `docs/adr/`; navigation at `docs/adr/INDEX.md`.
- Capability: `README.md` §Substrate composition, §Modality boundary decision,
  §Neuroimaging diffusion MRI and MR physics, §Suite coverage.
- Ratchet and audit: `gap_audit.md`, `checklist.md`,
  `scripts/atlas-conformance.py`, `scripts/atlas_architecture_test.py`.
