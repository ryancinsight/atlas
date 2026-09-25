# ADR 0064: Shared build source and artifact identity

- Status: Proposed
- Date: 2026-09-24
- Class: `[arch]`
- Item: [ATLAS-BUILD-SOURCE-IDENTITY](../../backlog.md#atlas-build-source-identity)

## Context

Atlas intentionally gives members one shared Cargo target directory. Cargo's fingerprint and dep-info records do not identify the source checkout that produced a proc-macro or other package artifact. Two exports with identical relative dependency names can therefore reuse an artifact compiled from different source bytes. Apollo's retained release-macro incident recorded a scratch-checkout path and an obsolete parser diagnostic while the canonical source accepted the new syntax.

A Git revision alone is insufficient for a dirty checkout, a branch name is not an identity, and a Cargo fingerprint is an implementation detail rather than a stable contract. A second source tree must not silently overwrite the first tree's record or artifact.

## Decision

### Stable scope and record

`scripts/atlas_build_identity.py` owns one record for each build scope: shared target directory, package, profile, target triple, feature set, and toolchain identity. The record is stored atomically under `target/.atlas/source-identity/`, inside the existing cache root. It contains the canonical source root, full Git revision, clean/dirty state, source-tree digest, build dimensions, and hashes of the discovered or explicitly supplied package artifacts.

The record path excludes the source revision deliberately. A source transition must contend with the existing owner of the same build scope; otherwise a second source tree could acquire a different lock and overwrite the first record.

### Mismatch and ownership

A missing, malformed, or mismatched record is stale. The gate acquires the scope lease before running `cargo clean -p <package> --manifest-path <manifest>`, then runs the requested build command and writes the record only after success. Ordinary matching builds reuse the existing artifact without cleaning.

The lease stores owner root, revision, package, target directory, token, and expiry. A live conflicting owner refuses the operation without cleaning, deleting, or overwriting artifacts. An expired lease is recoverable after a crash; a malformed lease fails closed. The target resolver uses the Git common directory so a linked Atlas worktree still addresses the primary cache.

### Build entry points

The shared identity module is the single policy surface. The member pre-push gate must invoke it for the changed package scope before accepting clippy, tests, or documentation. The integration composes with the existing conformance push guard in PR #277; it must not duplicate that guard or hand-edit member hook copies. Other build entry points use the same module when they compile packages, rather than implementing a second provenance format.

The module records artifact hashes after the command. It does not treat Cargo fingerprint JSON as a public schema, and it does not claim that a missing `.fingerprint` directory proves source identity.

## Failure modes

- A dirty tree is identified by a digest of its Git diff and untracked source files; a matching revision with different content is stale.
- A source path or artifact outside the shared target is rejected.
- A live owner conflict returns a diagnostic naming the owner and revision and performs no destructive action.
- A failed build leaves the previous record unchanged and releases the lease.
- A missing or malformed record fails closed rather than accepting an unknown artifact.

## Consequences

- Shared-cache reuse remains ordinary and fast when source and build dimensions match.
- A source transition rebuilds the selected package and its dependency closure without creating a second target tree.
- Concurrent source trees cannot silently clean or overwrite each other's artifacts.
- The provenance record is derived cache state; removing it causes a conservative rebuild, not a false pass.
- The gate adds one deterministic identity check before compilation and retains the existing shared target root.

## Alternatives rejected

- A per-source target directory prevents reuse but forks the cache and violates the one-target budget.
- Manual `cargo clean -p` repairs one incident but does not protect a concurrent owner or record identity.
- Cargo fingerprint JSON as a public contract couples Atlas to an unstable internal schema.
- Cleaning the entire target on every source transition destroys unaffected artifacts and violates the rebuild-scope requirement.

## Verification

The core regression suite covers a source transition, matching-source reuse, different-root identity, active-owner preservation, expired-lease recovery, dirty-tree identity, and artifact-boundary rejection. The integrated hook must additionally prove that a stale package is rejected before acceptance, an unrelated package artifact is preserved, and a live owner blocks cleaning without changing source files. Focused Python tests, the full scripts suite, pre-push hook tests, conformance, the ARCH-008 oracle, and the pin-drift gate are required before merge.

## References

- [ATLAS-BUILD-SOURCE-IDENTITY](../../backlog.md#atlas-build-source-identity)
- [PR #277](https://github.com/ryancinsight/atlas/pull/277)
- [scripts/atlas_build_identity.py](../../scripts/atlas_build_identity.py)
- [scripts/git-hooks/pre-push](../../scripts/git-hooks/pre-push)
- [Apollo ADR 0051](../../repos/apollo/docs/adr/0051-composite-phase-schedules.md)
