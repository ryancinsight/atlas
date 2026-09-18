<a id="ares-promotion"></a>
## ATLAS-ARES-PROMOTION-2026-09-03 - Create and register `ares` (solid momentum balance) [arch][minor] - in-progress

Charter: [ADR 0057](docs/adr/0057-ares-phase-0-charter.md). Path:
[ADR 0056](docs/adr/0056-new-construction-promotion-path.md) new-construction.
Boundary: [ADR 0055](docs/adr/0055-continuum-domain-decomposition.md).
Execution steps: `checklist.md` `ATLAS-ARES-PROMOTION-2026-09-03`.

- **outcome:** `ares` owns small-strain linear elastostatics on Gaia meshes,
  closed by Proteus and solved by Athena, verified against analytical oracles.
- **non-goals:** plasticity, contact, finite deformation, dynamics, fracture,
  fatigue, anisotropy, buckling. No integrator dependency, no material
  constants, no direct edge to another balance domain.
- **registry name:** `ares-solid`, import path `ares` via `[lib] name`. Verify
  availability on crates.io before creating the repository.
- **required authority:** repository creation (A2) and publication (A9) sit
  outside the standing Change grant.

| Phase | Deliverable | Acceptance oracle | Depends on |
| --- | --- | --- | --- |
| A0 | Prerequisites: Proteus elastic consumer deletions; aequitas stress semantics marker | both closed | `#aequitas-mechanics-semantics` |
| A1 | Repository scaffold at the full lint and gate floor | fmt, clippy, nextest, doc green; conformance scan clean | A0 |
| A2 | **Ask-User:** create `ryancinsight/ares` | repository exists, name reserved | A1 |
| A3 | Kinematics: symmetric tensors, invariants, small strain | rigid-body motion gives exactly zero strain | A2 |
| A4 | Constitutive coupling: isotropic Hooke over `IsotropicModuli`; Cauchy, von Mises, principal stresses | closed-form stress from a known `(E, nu)`; no material constant in `ares` | A3 |
| A5 | FEM assembly: linear simplices, isoparametric mapping, quadrature, Dirichlet and Neumann, Athena assembly | **patch test exact to machine precision**; hand-computed element matrices | A4 |
| A6 | Solve and end-to-end verification | Lame cylinder; cantilever tip deflection; MMS; `O(h^2)` L2 convergence; strain energy equals external work | A5 |
| A7 | Register in atlas: gitmodules, stack table, naming, roadmap, dependency order, architecture test | inward-only edges asserted | A6 |
| A8 | First consumer: CFDrs FSI structural side across Harmonia per [ADR 0050](docs/adr/0050-typed-physical-field-exchange.md) | interface work conserved | A7 |
| A9 | **Ask-User:** publish `ares-solid` | registry install and smoke; docs.rs builds | A8 |

- **integrator:** claude-opus-5. **A0-A6 done 2026-09-04**, pushed to
  `ryancinsight/ares` main through `f8cb9eb`. Gate green: fmt, clippy at the
  pedantic floor, 96 tests, doctests, `cargo doc`.
- **A5 acceptance met.** Patch test exact to machine precision on distorted 2-D
  and 3-D patches, under pure shear and pure dilation, at `f32` and `f64`;
  element stiffness columns agree with hand computation through the Voigt
  `B^T D B` route, which shares no code with the tensor formulation used.
- **A6 acceptance met.** Manufactured solution at rates 1.65, 1.88, 1.97
  approaching second order; Lame cylinder; cantilever approaching beam theory
  from below; strain energy equals external work. Accuracy and identity oracles
  also run at `f32` - the rate studies do not, because `f32` reaches its
  precision floor before the study leaves the asymptotic regime.
- **[arch] `ares` is now a workspace** ([ares ADR 0001]): `crates/ares` is the
  `no_std` allocation-free core, `crates/ares-operator` the operator seam.
  Athena's `LinearOperator` fixes the error to `B::Error` and its views are
  backend-associated, so the seam is implementable only against a named
  backend, and the only host backend links `std`. A7's architecture test must
  assert the split's edge set, not a single-crate one.
- **A7 done 2026-09-04.** `.gitmodules` (26 packages), stack table, classical
  -names table, provisional note, suite-coverage row, dependency order, and the
  R7 boundary set, at gitlink `8ca1f52`. The oracle is met mechanically: the
  conformance scan reports `balance_domain_edges = 0` and
  `substrate_contract_violations = 0` for `ares`, and every other class zero,
  so the member enters the ratchet with no debt. Two gaps found and filed:
  R7 still omits the live balance owners (`#archtest-live-balance-domains`),
  since closed by a peer; and the book gap (`#ares-book`), closed 2026-09-04.
- **A8 done 2026-09-04** at ares `64a12f6`: `ares-coupling` presents the
  structural solve as a Harmonia `Partition`, with no edge to CFDrs or any
  other balance domain. Interface work conservation is exact and mutation
  -measured - a lumped load of the same resultant force breaks it and nothing
  else. Two findings against ADR 0059 and Harmonia recorded below.
- **A9 in progress**, authorised 2026-09-04. An earlier note here said the
  chain needed "the whole first-party stack" published; that was wrong, and it
  was wrong in a way that made A9 look far larger than it is. It counted the
  *sizes* of publish waves 0-3 rather than `ares-solid`'s dependency closure.
  The closure is **five crates**:
  `eunomia-derive -> eunomia -> aequitas -> proteus-mat -> ares-solid`.
- **Of those, `eunomia` 0.8.0 and `aequitas` 0.2.0 are already on crates.io**,
  published 2026-08-02 from this account. `proteus-mat` is the only unpublished
  link, and `cargo publish --dry-run -p proteus-mat` packages and verifies
  cleanly against the published `eunomia` and `aequitas`. The optional-edge
  cycle (`#publish-order-optional-edges`) does not touch this closure, so it
  does not gate A9 either - an earlier note said it did.
- **Delivered toward A9:** `rust-release.yml` in `proteus` (`2092f43`) and in
  `ares` (`30707d7`), matching the pipeline `eunomia` and `aequitas` already
  run: release-gate SemVer, `--dry-run` validation, and OIDC trusted publishing
  rather than a stored token. The `crates-io` deployment environment now exists
  on both repositories. `ares` needed a tag-parsing `identify` job because it
  ships three crates and the SemVer gate's package cannot be a constant.
- **Found by running the pipeline: the release SemVer gate could not pass a
  first publication.** It baselines against the latest published version, so
  for a crate not yet on crates.io `cargo-semver-checks` fails with "not found
  in registry" — making the gate unpassable for exactly one release per crate,
  its first, with the only ways past being to delete it or publish around it.
  Fixed in the shared workflow at atlas `744acdf83`: the gate asks crates.io
  whether the crate exists and skips only in that case. It asks rather than
  catching the failure, because "not published" and "registry unreachable"
  produce the same failure and must not produce the same decision. Both member
  pins advanced to pick it up (`proteus` `98eade5`, `ares` `677dc84`).
- **Pipelines verified end to end by dispatch, 2026-09-04.** `proteus-mat`'s
  release validation is **green**: the SemVer gate skips as a first
  publication and `cargo publish --dry-run` packages and verifies it, so it is
  publish-ready. `ares-solid`'s validation reaches the same gate green and
  fails only at `no matching package named proteus-mat`, which is the registry
  link and not a pipeline defect. A deliberate bad-tag dispatch confirmed
  `identify` rejects a package this repository does not ship and skips every
  downstream job.
- **Remaining, and Trusted Publishing cannot be the first step.** crates.io's
  own documentation states the prerequisite outright: *"Your crate must already
  be published to crates.io (initial publish requires an API token)"*. There is
  no pending-publisher concept as PyPI has, so a not-yet-published name cannot
  be configured.
- **This was already documented, and I did not read it.** The atlas README's
  Publication section carries the same fact in a two-registry comparison table
  — crates.io "**No.** The crate must already exist; the first publish requires
  an API token", against PyPI's "**Yes**, through a *pending publisher*". I
  established it from the crates.io source after two failed documentation
  fetches instead of reading the stack's own map first, which is the first rung
  of the comprehension ladder. The finding is right; the route to it was waste,
  and the same table answers the Python-side ordering question directly.
- **Therefore the order is:** one token-authenticated first publish per new
  crate — `cargo publish -p proteus-mat`, then once that is on the index
  `cargo publish -p ares-solid` — performed by the account owner, since no
  credential exists in this environment and entering one is out of scope. Then
  Trusted Publishing is configured on each crate's Settings page (owner
  `ryancinsight`, repository `proteus` / `ares`, workflow `rust-release.yml`,
  environment `crates-io`), and every release from the second onward runs
  through the pipelines already built and validated.
- **The pipelines are not wasted work by that ordering.** Their `--dry-run`
  validation is what establishes the package is publishable, and it is green
  for `proteus-mat` today; they are the mechanism for every subsequent release
  and for `ares-operator` and `ares-coupling` when those become publishable.
- **`ares-operator` and `ares-coupling` are not part of A9** and cannot publish
  yet regardless: `ares-coupling` depends on `harmonia`, which the publish scan
  reports as `publish = false`.
- **ADR 0059 correction owed:** it states the marshalling contract as
  "interface node index major, component minor" throughout. That is right for
  displacement and wrong for traction, which is per facet because the fluid
  side computes one per face. The implementation carries both orderings and the
  ADR should be revised to match rather than the code bent to it.
- **Harmonia finding:** `Substep` has no public constructor, so an external
  partition's `advance` is reachable only through Harmonia's own two-partition
  driver. `ares-coupling` routes the work through an inherent method so a test
  about the physics need not stand up a driver first; a public test constructor
  or a single-partition driver would remove the workaround.
- **known gap closed:** CI, hooks, and the lockfile guard landed at `45f3eec`
  under `#ares-ci-floor`, which is in review pending its first hosted run.

[ares ADR 0001]: https://github.com/ryancinsight/ares/blob/main/docs/adr/0001-athena-seam-as-a-separate-crate.md

- **risk:** analytical oracles are the only safety net; no reference
  implementation exists to difference against. Mitigated by oracle breadth and
  by the exactness of the patch and rigid-body tests.
- Kwavers elastic-wave migration is Phase 1; Phase 0 does not block on it.

