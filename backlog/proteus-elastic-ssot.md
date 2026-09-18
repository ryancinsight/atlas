<a id="proteus-elastic-ssot"></a>
## ATLAS-PROTEUS-ELASTIC-SSOT-2026-09-03 — Proteus owns the isotropic modulus conversion contract [minor] — in-progress

- **integrator:** claude-opus-5 (this session)
- **regions:** `repos/proteus/src/elastic/**`, `repos/proteus/tests/elastic.rs`
  (provider). Consumer regions are unleased and unclaimed; both consumer trees
  verified clean (`git status -s` empty in each).
- **outcome:** the `(E, nu) <-> (lambda, mu) <-> (c_p, c_s)` contract and the
  named isotropic-solid catalog land in Proteus, and CFDrs plus Kwavers delete
  their copies. This is the recorded P2-B `ares` prerequisite in the stack map
  (README "Required consolidation result"), not a repository promotion.
- **acceptance oracle:** zero isotropic modulus-conversion arithmetic outside
  `proteus::elastic`; consumer differentials agree with the provider inside the
  derived tolerance; `rg 'lame_from_speeds|E / \(2 \* \(1'` returns provider
  hits only.

### Provider slice — merged

`ryancinsight/proteus` PR #29, merged to `main` as `1726082`. Local gate at the
identical tree: `cargo fmt --check` clean; `cargo clippy --all-targets` clean at
the pedantic floor; `cargo nextest run` 44/44 (24 new, 20 pre-existing
unaffected); `cargo test --doc` 2/2; `cargo doc --no-deps` clean.

**Collection pending:** the merge-gate CI run on proteus `main` was still queued
at hand-off; collect it at the next orientation and treat a red as the priority
item.

**Infrastructure finding — proteus has no required status checks.** `gh pr merge
--auto` landed #29 immediately while `verify`, `MSRV`, `SemVer gate`,
`supply-chain`, and `Lockfile integrity` were all still QUEUED, so the merge gate
did not gate anything. This is the same class as
`ATLAS-SEMVER-GATE-FLEETWIDE-2026-08-28` (checks adopted fleet-wide) but at the
branch-protection layer: adopting the workflow does not enforce it. Ruleset
configuration is a Change-grant merge-mechanic via `gh api`; audit every member
for the same gap rather than fixing proteus alone.

**Atlas gitlink:** `repos/proteus` still points at `930208f` and needs advancing
to `1726082`. Not done here — the meta-repo gitlinks are mid-flight under a live
peer (`MM repos/*` staged at 2026-09-03 14:30).

### Evidence correction to the stack map

**SUPERSEDED 2026-09-03 by a fuller source audit — see the correction note at
the end of this section.** The original text follows.

The README P2-B `ares` row records that "CFDrs and Kwavers duplicate isotropic
modulus conversions **and steel/aluminum catalogs**". The first half holds; the
second does not. The catalogs name **different alloys**:

| | CFDrs `ElasticSolid` | Kwavers `constants/implants.rs` |
| --- | --- | --- |
| "steel" | plain carbon steel, rho 7850, E 200 GPa, nu 0.30 | stainless 316L, rho 8000, c 5960 m/s |
| aluminium | 6061, rho 2700, E 70 GPa | alumina (a ceramic), rho 3970 |

Kwavers's implant constants carry density and sound speed, not `(E, nu)`, so
they are not elastic-catalog duplicates at all. Consolidating the two catalogs
under one "steel" entry would have silently substituted alloy constants. The
provider therefore keys entries by grade (`CarbonSteel`, `StainlessSteel316L`,
`Aluminium6061`, `TitaniumGrade5`) and a regression test asserts the two steel
grades stay distinct. **The genuine duplication is the conversion algebra
only.** The stack-map row should be corrected when the consumer slices land.

### Remaining — consumer deletion slices

1. `CFDrs`: `crates/cfd-core/src/physics/material/{solid.rs,traits.rs}` — delete
   the `shear_modulus` default and the `steel()`/`aluminum()` elastic constants;
   `ElasticSolid` composes `proteus::IsotropicModuli`.
2. `kwavers`: `crates/kwavers-medium/src/elastic.rs` `lame_from_speeds` and
   `crates/kwavers-medium/src/properties/elastic/constructors.rs`
   `try_from_engineering`/`new` — delegate to the provider, keeping the
   `ElasticProperties`/`ElasticArrayAccess` grid traits, which are operators and
   stay consumer-side.

**Ordering constraint (co-evolution protocol):** both consumers depend on
`proteus-mat` by `git`+`version`, so the provider branch must merge to proteus
`main` before either slice can resolve standalone or in CI. Under the stack
development overlay the local tree already resolves, which would hide the gap —
so the slices are sequenced after the provider merge, not run against the
overlay.

Blast radius measured, not assumed: `cfd-core` already declares
`proteus.workspace = true`, and `ElasticSolid`/`SolidProperties` have exactly
one caller outside their defining module
(`crates/cfd-core/src/physics/mod.rs:81`, a re-export). Slice 2 additionally
needs a review pass: the provider's positive-definite domain admits `lambda < 0`
where Kwavers's `ElasticPropertyData::new` rejects it, so any Kwavers caller
relying on that rejection changes behaviour.

### Non-goals

Creating `prometheus` or `ares`. `prometheus` is the stack's reaction-network
candidate, not the structural-mechanics one; `ares` is the solid-mechanics
candidate and its gate stays unmet until a second integrator can consume the
same solid-kinematics or balance operator. See ADR 0030 and the README P2-B
table.

### Kwavers slice — pushed

`ryancinsight/kwavers` branch `refactor/elastic-ssot-consumer`, commits
`ab9ddf8fb` and `051afb1e2` (Cargo.lock regen), PR #707 open. Deletes
`lame_from_speeds` in `kwavers-medium/src/elastic.rs`; delegates
`ElasticPropertyData::new` to `IsotropicModuli::from_lame` and
`try_from_engineering` to `from_young_poisson`; updates the three call
sites in `homogeneous/implementation/constructors.rs`,
`heterogeneous/factory/general/elastic.rs`, and the elastic_plugin test.
The `elastic_homogeneous` constructor preserves its `c_shear * c_shear *
2.0 > c_compression * c_compression` rejection (kept at the call site,
not delegated) so auxetic solids stay rejected there; the heterogeneous
constructor's per-voxel rejection agrees on the same boundary; the fluid
limit `c_s = 0 ⇒ μ = 0, λ = ρ·c_p²` short-circuits before the provider
because `from_wave_speeds` requires finite-positive shear-wave speed.
`ElasticPropertyData::new` accepts `lambda < 0` (provider's positive-
definite domain is `K = lambda + 2mu/3 > 0`, wider than kwavers's old
`lambda >= 0`); callers that need the stricter bound check at the call
site or use `set_lame_parameters`, which still rejects. Gates: 215/215
`kwavers-medium` tests, 1562/1562 `kwavers-physics` tests, 4/4
`elastic_plugin` tests. Acceptance oracle `rg 'lame_from_speeds|E /
\(2 \* \(1'` in `repos/kwavers/crates` and `repos/CFDrs/crates` returns
zero hits; the only remaining reference is the kwavers-bodied
differential test comment in `proteus/tests/elastic.rs` (kwavers's
`lame_from_speeds` body that this test replaced).

### Collection pending — CFDrs slice + atlas gitlinks

The CFDrs slice (`f063be4b refactor(cfd-core): Delete the elastic copy;
compose Proteus`) sits on `refactor/elastic-ssot-consumer` in
`ryancinsight/CFDrs`, unmerged to CFDrs `main`. Atlas's recorded
`repos/CFDrs` pin is still pre-slice (`f7fb9b5f`); advancing it requires
the CFDrs PR to merge first. The atlas gitlink for `repos/proteus`
already advanced to `1726082` via `7224f505f chore(atlas): Advance the
members that moved`. Both atlas pin advances land in the same co-
evolution unit when CFDrs merges.

