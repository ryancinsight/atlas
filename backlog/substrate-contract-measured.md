<a id="substrate-contract-measured"></a>
## ATLAS-SUBSTRATE-CONTRACT-MEASURED-2026-09-03 - The contract is already satisfied; the guard is preventive [patch] - todo
- outcome: a `cargo deny` `[bans]` guard locks in ADR 0055's substrate contract — deny `nalgebra`/`ndarray`/`rayon`/`num-traits` in runtime `[dependencies]` only, permitting dev-deps/benches/examples (interop/comparison-baseline role). Measured: zero violations across the 25 registered members; unregistered consumers are outside this stack scan.
- implementation: no new tool — `cargo deny` `[bans]` exists per member already; the work is one stack-level `[bans]` definition members inherit.
- blocked: region occupancy, not design — both candidate homes (`scripts/atlas-conformance.py`, `tools/version-guard/`) are under live peer edit. Re-open: script frees, or shared `[bans]` ownership decided.
