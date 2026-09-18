<a id="sibling-named-crates"></a>
## ATLAS-SIBLING-NAMED-CRATES-2026-09-04 - Nine crates are named after a sibling member, not a concern [arch] [major] - todo

- **outcome:** no crate in the stack carries a `<host>-<sibling>` name, and
  the required-dependency graph over publishable crates is closed and
  acyclic. Each renamed crate is named for the concern it owns; the
  dependency stays a manifest fact.
- **conflict, stated:** AGENTS.md `standards: Naming prohibition` and
  `architecture_scoping: Upstream ownership` prohibit the
  `<host>-<sibling>` shape, and `engineering_gates: Publish pipelines`
  makes a `publish = true` crate depending on a `publish = false` crate a
  topology defect. Both rules postdate the crates below and ares
  [ADR 0001](repos/ares/docs/adr/0001-athena-seam-as-a-separate-crate.md),
  which records `ares-athena` by name. Per `instruction_hierarchy` the
  higher-priority source wins and the ADR is revised, not the rule.
- **the nine, measured** (`scripts/publish-order.py` + crate-name scan, `769b044`):

  | Crate | Host | Sibling | Also closure-blocked |
  | --- | --- | --- | --- |
  | ~~`ares-athena`~~ → `ares-operator` | ares | athena | no — **renamed** |
  | ~~`ares-harmonia`~~ → `ares-coupling` | ares | harmonia | yes (`harmonia` is `publish = false`) — **renamed**; closure open |
  | `asclepius-coeus` | asclepius | coeus | no |
  | `athena-hephaestus` | athena | hephaestus | no |
  | `athena-leto` | athena | leto | no |
  | `coeus-hephaestus` | coeus | hephaestus | no |
  | `coeus-leto` | coeus | leto | no |
  | `tyche-consus` | tyche | consus | no |
  | `tyche-moirai` | tyche | moirai | no |

- **closure defect is wider than the naming one:** 14 publishable crates
  depend on a `publish = false` crate — `ares-harmonia`, `cfd-2d`,
  `cfd-optim`, five `helios-*`, five `kwavers-*` — blocked on `harmonia`,
  `hyperion`, `horae`, and `asclepius-coeus`. Graduating those four
  providers resolves 13 of the 14 without any rename.
- **acceptance:** the crate-name scan reports zero `<host>-<sibling>`
  names; `publish-order.py` reports an empty BLOCKED section; both
  checks land in `scripts/atlas-conformance.py` as counted classes so the
  ratchet holds them at zero.
- **method:** meta ADR first (the rename is a public-API break for any
  published member and the graduation decision per provider is not
  mechanical), then per-member items in dependency order. `ares` is the
  first increment — both its seam crates were created 2026-09-04 in this
  session, are unpublished, and have no external consumers, so they
  rename at zero migration cost.
- **ares delivered 2026-09-05:** `ares-athena` → `ares-operator` (it presents
  a linear operator), `ares-harmonia` → `ares-coupling` (it presents a coupling
  partition). Item names were already concern-named and did not move. ares
  ADR 0001 carries a dated revision note; the atlas architecture test, its
  fixtures, the stack diagram, and this board moved with it. Full ares gate
  green — fmt, no-default-features check, clippy `-D warnings`, 102 nextest,
  doctests, warning-clean rustdoc, `cargo deny`, mdbook build and link check —
  and the lock regenerated in standalone form.
- **remaining:** seven crates in `asclepius`, `athena`, `coeus`, and `tyche`,
  each with published or consuming surface, so each needs the meta ADR first.
  Plus the closure work: graduate `harmonia`, `hyperion`, `horae`, and
  `asclepius-coeus` to publishable, which clears 13 of the 14 blocked crates.

