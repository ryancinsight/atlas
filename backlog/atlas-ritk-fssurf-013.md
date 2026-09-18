<a id="atlas-ritk-fssurf-013"></a>
## ATLAS-RITK-FSSURF-013 — FreeSurfer surface formats and label table [minor] — todo

- outcome: RITK reads the FreeSurfer surface family — surface binaries
  (`lh.white`, `pial`, `inflated`), `curv`, `label`, `annot` — plus the color
  LUT, and GIFTI as the interchange equivalent. `ritk-mgh` covers FreeSurfer
  *volumes* only; no surface/annotation/LUT reader exists yet.
- why a prerequisite: surface parcellations are how connectome nodes are
  conventionally defined, so `ATLAS-RITK-CONNECTOME-012` depends on it.
- next: the FreeSurfer `aseg`/Desikan `aparc` label table is hand-rolled in
  a downstream consumer at
  `repos/leoneuro-rs/crates/leoneuro-gui/src/freesurfer.rs` (137 lines) — the
  RITK owner's first increment deletes it and repoints that consumer.
- open: CIFTI deferred until a consumer needs HCP-convention data.

