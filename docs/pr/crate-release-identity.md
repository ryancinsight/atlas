# Exact crate release retry identity [patch]

A GitHub Release can follow a successful version-change publisher. The shared
release workflow currently requests an OIDC token and retries an already
published version after its validation job succeeds. A version-only skip would
also hide different source. This correction permits a skip only for the exact
complete archive and clean release revision.

## Contract and placement

The existing validation job and caller SemVer policy run unchanged. In the
publish job, before authentication, a pinned composite action regenerates a
Cargo-verified package. A clean checkout must equal the release event commit;
metadata selects exactly one workspace package at the validated version.
Archive VCS commit and package path must match that checkout. The original
manifest and every nongenerated packaged source/readme/license file must equal
committed Git bytes. The workspace lock must be committed and unchanged.
The normalized manifest, generated lock and VCS record stay in the full archive
checksum; no file or byte is removed to force equality.

Public unauthenticated API, sparse-index and archive reads are bounded at 30s
per request. Metadata is bounded at 16MiB; the download is bounded at the local
archive size. HTTP framing must be complete and unambiguous, including 404
responses. Redirects, other statuses, network failures, malformed JSON,
duplicate keys/versions, inconsistent names/versions/checksums and empty index
responses fail closed. No downloaded tar path is extracted.

- API 404 plus a valid 200 index without the exact version, or index 404,
  permits the existing token request and upload.
- API 200 requires the exact index version/checksum, the locally generated
  complete checksum, and a downloaded archive identical byte for byte.
  This decision skips both authentication and upload.
- Every other result fails the action. An explicit workflow assertion rejects
  missing or unrecognized action output before either conditional step.

The reusable workflow checks out the member repository. The composite action
therefore uses its own immutable Atlas action path, not a member-relative
helper. Workflow commit B pins helper commit A
`8df6f30d7fb6d65d6ac639c5323ddac1c1897d75`; a regression compares both helper
files at that exact pin with the exercised bytes.

## Preservation and acceptance

Workflow inputs, events, permissions, environment, timeouts, validation commands
and actual `cargo publish --locked --package` command remain unchanged.
No pending-publisher or SemVer-owner file changes. The Cargo subprocess bound
matches the existing 30min job budget, which remains authoritative. A fresh
temporary verification target adds compile work; this correction preserves
verification rather than weakening gates or selecting older dependencies.
Regeneration can fail closed for packages whose source depends on uncommitted
or externally generated content, and nonreproducible historical archives do
not qualify for a skip even if their source trees appear equal.

The test leaves use real Git/Cargo workspace packages, computed archive checksums,
registry transport boundaries and raw stdlib HTTPResponse framing. It covers absence,
identity, byte/VCS differences, different commits with equal source trees,
registry failures and unknown workflow decisions. The baseline wiring test
fails on unconditional authentication; helper imports are not the red proof.
Independent exact-head review and real saved/public registry artifact checks
remain acceptance requirements; raw private receipts accompany the candidate.
PR #547 carries the implementation; final-head hosted acceptance remains open.
Immutable comparison commits are fetched from origin without object filtering
into a separate bare store. A local commit probe cannot prove a blobless
checkout can serve its promised blobs. Real shallow and full-depth blobless
fixtures verify exact comparison bytes and unchanged checkout objects/refs/config.
The Git history leaf is `scripts/tests/test_crates_release_identity_history.py`;
the publication-decision leaf imports its shared Git fixtures.

## Owning repository and private acceptance checklist

Atlas owns this reusable workflow and composite action. Horae only selects an
immutable Atlas recipe; its source correction cannot fix shared publisher
control flow. This candidate changes only that Atlas publisher, its new action,
test leaf and records. Future caller adoption needs its own reviewed immutable
pin; no Horae checkout, provider store or pending-publisher lane changes here.

- [x] Preserve current validation, caller SemVer policy, permission scopes and upload command.
- [x] Reproduce unconditional authentication and exercise complete archive/source and HTTP boundaries.
- [ ] Finish final-head local checks, independent review and saved/public artifact compatibility.
- [ ] Complete separate final-head caller, publication and deployment gates before adoption.

The default sandbox denies loopback listeners. The earlier scoped approved
local TCP run passes55 cases before later task steering. Final proofs retain
all decision assertions and feed raw wire bytes through the real stdlib HTTP
parser at the transport boundary, with no listener or permission expansion.
Full-stack baseline fixture/store failures are separate from guard correctness;
the private receipt identifies executed, baseline-failing and blocked checks.
