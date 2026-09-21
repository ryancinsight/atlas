<a id="atlas-cfdrs-jfnk-rerun-2026-08-19"></a>
## ATLAS-CFDRS-JFNK-RERUN-2026-08-19 — hosted infrastructure retry — in-progress
- Replacement run `32226998372` first failed in the runner's native-fontconfig setup after three bounded `apt-get` attempts against unreachable Ubuntu mirrors; no Rust or JFNK diagnostic ran. The failed job was rerun and is currently executing at the same provider head `bc18b095`.
- Atlas remains at CFDrs default `931ee3a0`; no hosted source result is claimed until the rerun reaches the Rust and figure gates.
