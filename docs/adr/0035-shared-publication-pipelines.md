# ADR 0035: Atlas owns the release and documentation publication pipelines

- Status: Proposed
- Date: 2026-07-28
- Class: `[arch]` `[patch]`
- Relates to: [ADR 0027](0027-provider-checkout-ssot.md),
  [ADR 0024](0024-criterion-regression-gate.md),
  [ADR 0011](0011-atlas-root-hygiene-ritual.md)

## Context

Three publication concerns exist across the stack: crates to crates.io, wheels to
PyPI, and package books to GitHub Pages. Each is currently wired per repository,
and the copies have started to diverge.

### Source audit (2026-07-28)

**Crate publishing.** Seven packages carry `rust-release.yml`: `apollo`, `coeus`,
`consus`, `hephaestus`, `kwavers`, `leto`, `moirai`. `ritk` carries the same
concern under `release.yml`. Four of the seven are byte-identical at 142 lines
(`coeus`, `hephaestus`, `leto`, `moirai`). The real variation is two dimensions:

| Package | `RUST_TOOLCHAIN` | Atlas path dependencies |
| --- | --- | --- |
| `leto` | 1.95.0 | no |
| `coeus`, `hephaestus`, `moirai` | 1.95.0 | no |
| `apollo` | 1.97.0 | no |
| `consus` | 1.97.1 | no |
| `kwavers` | 1.97.1 | yes (12 extra lines) |

Every other line — release-tag parsing, package-name validation, manifest-version
agreement, `publish = false` rejection, the `--dry-run` content gate, the OIDC
token request, and the publish call — is identical logic duplicated eight times.

**Book publishing.** Four packages carry `book-pages.yml`: `CFDrs`, `helios`,
`kwavers`, `ritk`. Three are 70 lines and one is 86. The only substantive
difference is the built output directory (`target/book/cfdrs`,
`target/book/helios`, `target/book`, `target/book/ritk`). None of the four runs
`mdbook test`, so no book's code samples are currently protected against rot.

**Wheel publishing.** Already consolidated: Atlas owns
[`python-wheels.yml`](../../.github/workflows/python-wheels.yml) as a
`workflow_call` workflow, and package `python-release.yml` files are thin callers
pinned to an exact Atlas commit. This ADR generalizes that proven shape to the
other two concerns rather than inventing one.

**Authentication.** Both registries already authenticate by OIDC trusted
publishing — `rust-lang/crates-io-auth-action` for crates.io and
`pypa/gh-action-pypi-publish` for PyPI — under `id-token: write` with an
environment gate. No workflow in the stack reads a registry token from a secret.
A PyPI API token was nonetheless added to the `pypi` environment; it is unused by
the current workflows.

**Book coverage.** Four of 25 packages have a book. Twenty-one have none.

## Decision

### 1. Atlas owns all three pipelines as reusable workflows

Publication logic lives once, in Atlas, as `workflow_call` workflows:

| Concern | Atlas workflow | Status |
| --- | --- | --- |
| Wheel build, validation, attestation, release assets | `python-wheels.yml` | existing |
| Crate publish | `crates-publish.yml` | added by this ADR |
| Book build and Pages deploy | `book-pages.yml` | added by this ADR |

Wheel *upload* stays in the caller as a short job after `python-wheels.yml`,
because the PyPI project URL and environment are package identity, not shared
logic. That split already exists and is retained.

### 2. Package workflows are thin callers pinned to an exact Atlas commit

A package workflow declares its triggers, its identity inputs, and the
permissions the called workflow needs — nothing else. It pins Atlas by commit,
matching the `atlas-ref` contract of ADR 0027, so a pipeline fix lands once in
Atlas and each package adopts it by advancing one pin.

Re-implementing pipeline logic in a package is a defect, not a local choice. This
is the compatibility-soup rule applied to CI: the duplicate is deleted in the
same change that adopts the shared workflow, never kept beside it.

### 3. Variation is expressed as inputs, never as a forked copy

The audit's two real crate-publishing dimensions become inputs
(`rust-toolchain`, `atlas-ref`), and the book dimension becomes one input
(`output-path`). A future divergence is an input or it is a defect; the third
copy of a workflow is the signal that the seam was wrong, not that a copy was
needed.

### 4. Registry authentication stays tokenless

Trusted publishing is the only sanctioned authentication path. Each package
registers once, in the registry's own interface:

crates.io, under the crate's **Settings → Trusted Publishing**:

```text
Repository owner:   ryancinsight
Repository name:    <package repository>
Workflow filename:  rust-release.yml
Environment:        crates-io
```

PyPI, under the project's **Publishing → Trusted publisher**:

```text
Owner:              ryancinsight
Repository name:    <package repository>
Workflow name:      python-release.yml
Environment:        pypi
```

The workflow filename registered is the **caller's** filename, not the Atlas
reusable workflow's, because the OIDC claim carries the caller's identity. This
is the most likely setup error: registering the Atlas filename rejects every
publish.

Registry verification 2026-07-28 (crates.io and PyPI documentation plus the
crates.io API) establishes two constraints that decide the order of operations:

| | crates.io | PyPI |
| --- | --- | --- |
| Trusted publishing can create a new package | **No** — the crate must already exist; the first publish requires an API token | **Yes** — a *pending publisher* under the account sidebar creates the project on first use |
| Token lifetime | 30 minutes | short-lived, per publish |
| Registration path | crate **Settings → Trusted Publishing** | project **Manage → Publishing**, or account sidebar when pending |

crates.io therefore cannot bootstrap. The account `ryancinsight` (user id
383645) has published exactly one crate, `imaginary-rs@0.1.0`; **no Atlas crate
is published**. Each crate's first publish is a manual publish from the local
Cargo credential store, after which its trusted publisher is registered and the
pipeline owns every subsequent release. PyPI needs no such step.

A pending PyPI publisher does not reserve the project name until it is used, so a
name can still be lost between configuration and first publish.

Two consequences follow. First, the `crates-io` and `pypi` GitHub environments
hold no secrets; they exist to scope the OIDC claim and carry deployment
protection rules. Second, the unused PyPI API token in the `pypi` environment is
removed once a trusted-publishing release has succeeded — a long-lived registry
token in CI is precisely the exposure trusted publishing exists to eliminate.
Once a package's pipeline is proven, trusted-publishing-only enforcement is
enabled in its registry settings.

### 5. Every package publishes a book; the gate grows with it

A book at `docs/book/` is required of every package, not only integrators. The
book teaches its field from governing equations through numerical method to the
crate's abstractions, with runnable worked examples. Rustdoc remains the
item-contract layer; the two layers do not duplicate each other.

The book is **workspace-level: one per repository, never one per crate.** A
sub-crate contributes a chapter to its package's book. Per-crate books would
fragment one field's theory across 173 crates and force every shared derivation
to be restated, which is the duplication this stack exists to avoid; the
consolidation rule applies to prose exactly as it does to code.

Twenty-one missing books are board work sequenced provider-first, so a domain
chapter can cite the substrate chapter it depends on. A new book joins the Atlas
cross-book dead-link and build gate
([`docs.yml`](../../.github/workflows/docs.yml)) in the change that creates it.
`ritk` has a book that is absent from that gate; adding it is part of this ADR's
work.

### 6. `mdbook test` is adopted per book, not flipped globally

Book code samples must be tested so chapters cannot rot. No book currently runs
`mdbook test`, and enabling it stack-wide in one change would fail every book
whose samples are illustrative rather than compilable — a regression authored
blind.

The shared workflow therefore exposes `mdbook-test`, defaulting to `false`. Each
book flips it to `true` in the change that makes its samples compilable. The
default is a staging mechanism with a per-book completion item, not an accepted
end state; a book left at `false` after its samples compile is a defect.

### 7. Twelve crate names collide; the decision precedes the first publish

crates.io has no namespaces, and publishable names are first-come. Checked
2026-07-28 against the registry API:

| Status | Package names |
| --- | --- |
| Available | `aequitas`, `asclepius`, `coeus`, `consus`, `eunomia`, `hephaestus`, `horae`, `iris`, `kwavers`, `leto`, `melinoe`, `ritk` |
| Taken by unrelated owners | `apollo` (`0.0.2`), `athena` (`0.0.0`, owner `zakarumych`), `gaia` (`0.2.1`), `harmonia` (`0.1.0`, `sogh`), `helios` (`0.1.0`), `hermes` (`0.1.0`, `YeluriKetan`), `hyperion` (`0.2.1`, `patrickisgreene`), `mnemosyne` (`0.3.1`, `elde-n`), `moirai` (`0.8.5`, `PsichiX`), `proteus` (`0.5.0`, 367 550 downloads), `themis` (`0.14.0`), `tyche` (`0.3.1`, `Gawdl3y`) |

Sub-crate names are mostly free (`apollo-fft`, `athena-core`, `coeus-core`,
`hephaestus-core`, `hermes-simd`, `leto-ops`, `moirai-async`, `ritk-core`,
`tyche-core`) but not universally — `mnemosyne-core` is taken.

This ADR does not decide the twelve names. A published crate name is permanent
and the choice is a public-identity decision with several defensible answers, so
it is recorded as an open decision (`ATLAS-PUB-006`) that gates the first publish
of the affected packages and nothing else. Repository names, submodule paths,
directory names, and internal crate paths are out of scope: this is a registry
namespace question only, and the classical-name mapping in the stack README
stands regardless.

The pipelines are unaffected — a caller passes a package name, so a rename is a
manifest change, not a workflow change. Consequently ATLAS-PUB-001 and
ATLAS-PUB-002 proceed independently of ATLAS-PUB-006.

### 8. Pages action pins are a recorded gap, not an invented digest

The three first-party Pages actions (`configure-pages`, `upload-pages-artifact`,
`deploy-pages`) are referenced by major-version tag in `book-pages.yml`, matching
the four existing package workflows. Commit-pinning them requires resolving each
digest against its upstream repository; a digest that has not been resolved is
fabricated evidence and must not be committed. The gap is tracked as
`ATLAS-PUB-004`.

## Consequences

- The first crates.io publish per crate stays manual by registry constraint, not
  by choice. The pipeline owns every release after that one.
- Twelve packages need a registry name decision before their first publish
  (`ATLAS-PUB-006`). Nothing else in this ADR waits on it.

- Eight duplicated crate-release workflows collapse to eight thin callers plus
  one Atlas workflow; four book workflows collapse to four callers plus one.
- A pipeline defect is fixed once. Adoption is explicit and auditable: each
  package's Atlas pin says which pipeline revision it runs.
- Toolchain pins stay per package. The audit's 1.95.0/1.97.0/1.97.1 spread is
  preserved as input values, so consolidation does not silently move any
  package's toolchain.
- `kwavers` keeps its path-dependency materialization through the `atlas-ref`
  input rather than 12 extra lines in a forked copy.
- Books gain a rot gate as each becomes testable, and the stack gains a stated
  requirement that every package has a book.
- No secret is introduced. The one existing registry token becomes removable.

### Adoption ledger

Migration is per package and independently verifiable. A row is done when the
caller is pinned to Atlas, the duplicated logic is deleted, and one release or
book build has succeeded through the shared pipeline.

| Package | Crate publish | Book | Wheel |
| --- | --- | --- | --- |
| `apollo` | migrate (toolchain 1.97.0) | absent | shared |
| `CFDrs` | absent | migrate (`target/book/cfdrs`) | no release workflow |
| `coeus` | migrate (1.95.0) | absent | shared |
| `consus` | migrate (1.97.1) | absent | shared |
| `helios` | absent | migrate (`target/book/helios`) | no release workflow |
| `hephaestus` | migrate (1.95.0) | absent | shared |
| `kwavers` | migrate (1.97.1, `atlas-ref`) | migrate (`target/book`) | shared |
| `leto` | migrate (1.95.0) | absent | shared |
| `moirai` | migrate (1.95.0) | absent | shared |
| `ritk` | migrate (from `release.yml`) | migrate (`target/book/ritk`) + join `docs.yml` | shared |
| remaining 15 packages | when first published | author book | when a binding crate exists |

## Alternatives rejected

**Keep per-repository workflows.** The audit already shows divergence with no
functional cause: four byte-identical copies, three toolchain values, and one
copy carrying an extra concern inline. Every future fix would be applied eight
times or, in practice, fewer than eight times.

**A shared workflow per package family.** Would produce two or three copies
instead of eight, and reintroduces the same question at the next divergence. The
input seam handles the real variation at one copy.

**A GitHub organization `.github` repository for shared workflows.** Would work
for workflow reuse, but splits publication ownership away from Atlas, which
already owns the provider graph, the `atlas-ref` contract, the composite
checkout action, and the benchmark gate. Publication depends on the gitlink graph
that Atlas owns; a second location would need its own pin to Atlas anyway.

**A long-lived registry token in a shared secret.** Rejected on the standing
policy: trusted publishing exists to remove exactly this credential, and a shared
token widens blast radius across 25 repositories.

**Enable `mdbook test` for every book immediately.** Rejected as a blind
regression; no evidence exists that any current book's samples compile. Staged
per book with a completion item instead.

**Composite actions instead of reusable workflows.** A composite action cannot
own job structure, environments, or per-job permissions, all of which the publish
gate needs. `python-wheels.yml` already proves the reusable-workflow shape in
this stack.

## Verification

1. `crates-publish.yml` and `book-pages.yml` parse as valid `workflow_call`
   workflows with the audited variation exposed as inputs — verified locally:
   `crates-publish.yml` declares jobs `validate`/`publish` with `rust-toolchain`
   required; `book-pages.yml` declares `build`/`deploy` with `output-path`
   required.
2. Every action reference in both workflows is either reused verbatim from an
   existing stack workflow or carries the major-version tag already in use. No
   commit digest is introduced that has not been resolved.
3. Per migrated package: the duplicated workflow file is deleted in the adopting
   change, and the resulting caller is under 40 lines.
4. Per migrated package: one release publishes through the shared pipeline, and
   the crate's `--dry-run` gate plus the semver gate run before the publish job.
5. The `pypi` environment holds no secret after the first successful
   trusted-publishing release.
6. `docs.yml` builds every registered book, `ritk` included.
7. A book that flips `mdbook-test` to `true` fails CI when a sample stops
   compiling — verified by the flip commit, not asserted.

## References

- [ADR 0027](0027-provider-checkout-ssot.md) — the `atlas-ref` gitlink contract
  the callers reuse.
- [ADR 0024](0024-criterion-regression-gate.md) — the precedent for Atlas owning
  a cross-package CI gate rather than duplicating package scripts.
- [`python-wheels.yml`](../../.github/workflows/python-wheels.yml) — the existing
  reusable-workflow shape this ADR generalizes.
- [Publication](../../README.md#publication) and
  [Documentation](../../README.md#documentation) — the stack-facing summary.
