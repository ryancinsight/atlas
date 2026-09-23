<a id="sibling-named-crates"></a>
## ATLAS-SIBLING-NAMED-CRATES-2026-09-04 - Nine crates are named after a sibling member, not a concern [arch] [major] - todo
outcome: no crate in the stack carries a `<host>-<sibling>` name; the required-dependency graph over publishable crates is closed and acyclic; each renamed crate is named for the concern it owns, the dependency staying a manifest fact.
open — 7 remaining renames (each needs the meta ADR first, since it's a public-API break for published members): `asclepius-coeus`, `athena-hephaestus`, `athena-leto`, `coeus-hephaestus`, `coeus-leto`, `tyche-consus`, `tyche-moirai`.
open — closure defect: 14 publishable crates depend on a `publish = false` crate (`ares-harmonia`/now `ares-coupling` still `publish=false`, `cfd-2d`, `cfd-optim`, 5 `helios-*`, 5 `kwavers-*`), blocked on graduating `harmonia`, `hyperion`, `horae`, `asclepius-coeus` to publishable — resolves 13 of the 14 without any rename.
acceptance: crate-name scan reports zero `<host>-<sibling>` names; `publish-order.py` reports an empty BLOCKED section; both counted in `scripts/atlas-conformance.py` as classes ratcheted to zero.
method: meta ADR first (rename + graduation decisions are not mechanical), then per-member items in dependency order.
