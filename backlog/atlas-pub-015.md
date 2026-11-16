<a id="atlas-pub-015"></a>
## ATLAS-PUB-015 - Resolve helios-planning's dependency on unpublishable asclepius-coeus [architecture] - todo
- priority: architecture; needs: none; scope: `repos/asclepius/crates/asclepius-coeus/Cargo.toml`, asclepius ASC-REL-008/ASC-ARCH-017, `repos/helios/crates/helios-planning/Cargo.toml`
- outcome: the publishable closure is dependency-closed. Either asclepius-coeus graduates to `publish = true` (reversing ASC-REL-008), or helios-planning (and helios-python, which needs it) stops requiring it or becomes `publish = false`.
- evidence (2026-10-12): ordering the 68 never-published crates for first publish left exactly these two unorderable; ASC-ARCH-017's fixed `Var<f64, B>` bears on publishing the adapter's API. Acceptance: decision recorded in asclepius (ADR or board revision); no publishable helios crate depends on an unpublishable one.
