# ADR 0035: Atlas owns the release and documentation publication pipelines

- Status: Proposed
- Date: 2026-07-28
- Class: `[arch]` `[patch]`
- Revision 2026-10-29: crate publication can bind an independently reproduced
  artifact manifest to the candidate, selected cohort, staged archive, registry
  checksum, and tag gate. Cargo still packages the uploaded archive itself, so
  only the post-upload registry checksum proves uploaded artifact identity.
- Relates to: [ADR 0027](0027-provider-checkout-ssot.md),
  [ADR 0024](0024-criterion-regression-gate.md)

## Context

Crates.io, Python Package Index (PyPI), and Pages publication repeat the same
security and verification concerns across package repositories. Per-package
workflow copies had diverged in toolchain, dependency checkout, documentation
testing, and authentication behavior. Atlas already owns the provider graph and
the immutable `atlas-ref` contract, so it is the common owner for these release
pipelines.

Package identity remains caller-owned. A caller selects its package, toolchain,
registry project, documentation path, and Atlas revision. Atlas owns the shared
validation, packaging, authentication boundary, and release ordering.

## Decision

### Shared workflows

Atlas provides these reusable workflows:

| Concern | Workflow |
| --- | --- |
| Crate release | `crates-publish.yml` |
| Pending crate cohort release | `crates-publish-pending.yml` |
| Python wheel build and verification | `python-wheels.yml` |
| Book build and Pages deployment | `book-pages.yml` |

Callers pin the workflow to an exact Atlas commit and remain thin. Real
variation is an input to the owning workflow; a package does not copy or fork
the implementation. Package-specific release triggers and registry identities
stay in the caller.

### Registry authentication and bootstrap

Registry automation uses OpenID Connect trusted publishing. Workflows do not
read long-lived registry tokens. The caller's workflow filename and protected
environment identify the trusted publisher because the identity token names the
caller, not the reusable Atlas workflow.

Crates.io requires a crate to exist before its trusted publisher can be
registered. The first publish therefore uses the publisher's local Cargo
credential store under separate release authority. Later publishes use the
trusted publisher. PyPI may bootstrap through its pending-publisher flow.
Registry project names are caller identity and must be resolved before the
first publish; this ADR does not rename packages.

### Crate release identity

The ordinary crate workflow validates the requested package, version, clean
candidate commit, manifest metadata, generated archive, and release identity
before requesting credentials. A previously published version is accepted only
when its registry archive is identical to the regenerated archive for the exact
candidate.

The pending workflow derives a dependency-ordered publishable cohort and
supports partial-publish recovery. It freezes the ready set used by the publish
job so a registry change cannot silently select a different upload set.

The pending workflow also accepts an optional evidence manifest containing:

- the exact candidate commit, installed Rust toolchain, native target, and the
  semantic profile `cargo-package-verify`;
- the ordered package-name and version cohort; and
- a SHA-256 digest for every `<name>-<version>.crate` archive.

A caller supplies this manifest only after two independent clean
`cargo package --locked` builds agree. When evidence is present, Atlas rejects
a different candidate, dirty checkout, toolchain or host, package identity,
cohort order, ready set, archive digest, or registry re-filter.

Before OpenID Connect authentication, the publish job reruns verified
`cargo package --locked` for the frozen set and compares each staged archive
with the expected digest. This proves the staged candidate bytes. It does not
cryptographically constrain the later upload: `cargo publish` has no interface
for uploading that prebuilt archive and packages the crate again.

After upload, the sparse-index `cksum` must equal both the expected digest and
the digest of the archive staged in the publish job. Tag creation occurs only
after that equality holds. A mismatched archive can therefore reach the
registry, but this workflow cannot create release-completion tags for it.
Malformed or incomplete evidence and any source, selection, package, or index
drift fail closed before tags. Callers that omit evidence retain the existing
planner and recovery behavior without a weaker path for callers that opt in.

### Python wheels

Atlas builds the platform matrix, validates wheel and source-distribution
metadata, installs each artifact, and runs the caller's value tests. The caller
retains the short PyPI upload job because the PyPI project and protected
environment are package identity. Validation-only runs retain artifacts and
skip release attachment and upload. Free-threaded artifacts use the same source,
installation checks, and metadata validation as the ordinary matrix.

### Books and Pages

Each repository publishes one workspace-level book. Rustdoc remains the API
reference; the book owns tutorials and domain explanation. `book-pages.yml`
builds and deploys the caller-selected output path. A caller enables
`mdbook-test` only when its samples pass under the pinned toolchain, and keeping
the gate disabled after that point is a defect. Package dependency artifacts
retain their Cargo metadata hashes so rustdoc cannot select a different version
by an ambiguous filename.

## Consequences

- One Atlas fix updates each publication mechanism; callers adopt it by moving
  one immutable pin.
- Toolchain and package identity remain explicit caller inputs.
- Registry credentials remain outside repository and workflow configuration.
- Crate evidence supplies a fail-closed tag gate, not a pre-upload guarantee
  that Cargo transmits a caller-supplied archive.
- First-time crates.io bootstrap remains a separately authorized manual action.

## Alternatives rejected

**Keep per-package workflow copies.** This preserves divergent authentication,
ordering, and verification logic and requires every correction to land many
times.

**Create workflow copies per package family.** The same concern would still
have multiple owners. Inputs express the actual package and toolchain variation.

**Move workflows to a separate organization repository.** Publication depends
on the provider graph and immutable Atlas revision contract already owned here.
A second owner would add another pin without removing that dependency.

**Use long-lived registry secrets.** Trusted publishing provides narrower,
short-lived identity bound to the caller and protected environment.

**Claim the staged digest constrains Cargo's upload.** Cargo repackages during
`cargo publish`; the supported enforcement point for uploaded identity is the
registry checksum before any completion tag.
## Verification

Workflow tests parse each reusable workflow, assert least-privilege job order,
and exercise package planning, archive identity, registry errors, and tag gates.
Callers verify their exact Atlas pin, toolchain, package metadata, and protected
environment. A release additionally requires the repository's publication and
SemVer gates under separate release authority.
