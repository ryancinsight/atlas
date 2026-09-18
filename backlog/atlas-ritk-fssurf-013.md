<a id="atlas-ritk-fssurf-013"></a>
## ATLAS-RITK-FSSURF-013 — FreeSurfer surface formats and label table [minor] — todo

- **Outcome**: RITK reads the FreeSurfer surface family — surface binaries
  (`lh.white`, `pial`, `inflated`), `curv`, `label`, `annot` — plus the color
  LUT, and GIFTI as the interchange equivalent.
- **Evidence of gap**: `ritk-mgh` covers FreeSurfer *volumes* only; no surface,
  annotation, or LUT reader exists in the workspace.
- **Why it is a prerequisite, not an optional format**: surface parcellations are
  how connectome nodes are conventionally defined, so ATLAS-RITK-CONNECTOME-012
  depends on it.
- **Deletion ledger** (promotion-gate condition 4, satisfied): the FreeSurfer
  `aseg` and Desikan `aparc` label table is hand-rolled in a downstream consumer
  at `repos/leoneuro-rs/crates/leoneuro-gui/src/freesurfer.rs` (137 lines). The
  RITK owner first increment deletes it and repoints that consumer.
- **Open**: CIFTI is deferred until a consumer needs HCP-convention data.
- **Class**: `[minor]`.

