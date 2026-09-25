# ADR 0064: Shared build source and artifact identity

- Status: Accepted
- Date: 2026-09-24
- Revision: 2026-09-25 — Accepted the implemented locked dependency-content and closure-lease design.
- Class: `[arch]`
- Item: [ATLAS-BUILD-SOURCE-IDENTITY](../../backlog.md#atlas-build-source-identity)

## Context

Atlas intentionally gives members one shared Cargo target directory. Cargo's fingerprint and dep-info records do not identify the source checkout that produced a proc-macro or other package artifact. Two exports with identical relative dependency names can therefore reuse an artifact compiled from different source bytes. Apollo's retained release-macro incident recorded a scratch-checkout path and an obsolete parser diagnostic while the canonical source accepted the new syntax.

A Git revision alone is insufficient for a dirty checkout, a branch name is not an identity, and a Cargo fingerprint is an implementation detail rather than a stable contract. A second source tree must not silently overwrite the first tree's record or artifact.

## Decision

### Stable scope and record

`scripts/atlas_build_identity.py` owns one record for each build scope: shared target directory, package, profile, target triple, feature set, toolchain identity, build-affecting environment digest, dependency-closure digest, and the caller's stable command key. The command key names the build-entry-point dimensions without treating `clippy`, tests, and documentation as different source identities. The record is stored atomically under `target/.atlas/source-identity/`, inside the existing cache root. It contains the canonical source root, full Git revision, clean/dirty state, source-tree digest, resolved dependency closure, build dimensions, and hashes of the discovered or explicitly supplied package artifacts. Version 1 and 2 records are stale; malformed or unsupported current records fail closed.

The record path excludes the source revision deliberately. A source transition must contend with the existing owner of the same build scope; otherwise a second source tree could acquire a different lock and overwrite the first record.

### Mismatch and ownership

A missing, malformed, or mismatched record is stale. The gate resolves the package's reachable path and Git dependency closure, acquires the scope lease, cleans the affected non-registry packages plus the selected package, then runs the requested build command and writes the record only after success. Ordinary matching builds reuse the existing artifacts without cleaning. Registry package IDs and graph edges remain part of the closure digest without hashing registry checkout paths.

The lease stores owner root, revision, package, target directory, token, and expiry. The OS file lock is authoritative while a process is alive; expiry is recovery metadata after a crash. A live conflicting owner refuses the operation without cleaning, deleting, or overwriting artifacts. A malformed lease or record fails closed. The target resolver uses the Git common directory so a linked Atlas worktree still addresses the primary cache.

### Build entry points

The shared identity module is the single policy surface. The member pre-push gate refuses a pushed revision that differs from the checkout, invokes the module for each changed package before accepting clippy, tests, or documentation, and passes the member manifest in linked-worktree mode. One stable command key per package lets those steps share a record. The integration composes with the existing conformance push guard in PR #277; it must not duplicate that guard or hand-edit member hook copies. Other build entry points use the same module when they compile packages, rather than implementing a second provenance format.

The module records artifact hashes after the command. It does not treat Cargo fingerprint JSON as a public schema, and it does not claim that a missing `.fingerprint` directory proves source identity.

## Failure modes

- A dirty tree is identified by a digest of its Git diff and untracked or ignored source files; generated files under the resolved target directory are excluded; a matching revision with different content is stale.
- A source path or artifact outside the shared target is rejected before any clean.
- A full Cargo metadata graph is required when artifacts are discovered implicitly; an unresolved or name-ambiguous dependency closure fails closed.
- A build-affecting environment change produces a different record scope.
- A lockfile rewrite caused by the development overlay is excluded from the source digest only after the pushed lock has been checked and the working copy is restored.
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

The core regression suite covers a source transition, matching-source reuse, different-root identity, dependency-closure transitions and cleanup, active-owner preservation, expired-lease recovery, dirty and ignored-source identity, build-environment dimensions, target-directory exclusion, and artifact-boundary rejection. The integrated hook regression additionally proves that a stale package is rebuilt once per source transition, an unrelated package artifact is preserved, a pushed-revision mismatch is refused, overlay lock rewrites are restored, linked worktrees receive the member manifest, environment failures are not accepted, and a live owner blocks cleaning without changing source files. Focused Python tests, the full scripts suite, pre-push hook tests, conformance, the ARCH-008 oracle, and the pin-drift gate are required before merge.

## References

- [ATLAS-BUILD-SOURCE-IDENTITY](../../backlog.md#atlas-build-source-identity)
- [PR #277](https://github.com/ryancinsight/atlas/pull/277)
- [PR #299](https://github.com/ryancinsight/atlas/pull/299)
- [scripts/atlas_build_identity.py](../../scripts/atlas_build_identity.py)
- [scripts/atlas_build_source.py](../../scripts/atlas_build_source.py)
- [scripts/atlas_build_artifacts.py](../../scripts/atlas_build_artifacts.py)
- [scripts/git-hooks/pre-push](../../scripts/git-hooks/pre-push)
- [Apollo ADR 0051](../../repos/apollo/docs/adr/0051-composite-phase-schedules.md)
