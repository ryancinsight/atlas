<a id="atlas-pub-006"></a>
## ATLAS-PUB-006 — Stand up one facade crate per package [minor] — todo
- **outcome:** every package presents one facade crate re-exporting its sub-crates (the `burn`/`bevy`/`polars` shape), decided per [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md); naming is settled, nothing waits on a user answer.
- **next: unblocker chain** — proteus → `proteus-materials`, hyperion → `hyperion-photon`, horae (name free), harmonia → `harmonia-coupling`, then asclepius-coeus; athena's family must publish before harmonia. Remaining facades to author: apollo, CFDrs, coeus, helios, ritk.
- **Correction on record:** the `publish = false` guards on 8 packages are correct dependency-ordering guards, not oversights — each flips at the final step of that crate's own bootstrap publish (`scripts/publish-order.py` order).
- **Peer-held, not claimable without a staleness sweep:** coeus (flagship facade case), ritk, leto, mnemosyne.
- **README correction owed:** "No Atlas crate is published yet" (line 1084) is false — 18+ crates are already on crates.io.
