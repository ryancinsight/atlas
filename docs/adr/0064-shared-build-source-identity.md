# ADR 0064: Shared build source and artifact identity

- Status: Accepted
- Date: 2026-09-24
- Revision: 2026-09-25 — Accepted the locked dependency-content, closure-lease, and artifact-package design.
- Revision: 2026-09-27 — Leases gained shared and exclusive modes served in arrival order: every lease was exclusive, so a coeus hook re-running its steps held a dependency lease through each long test run and a helios push waited out its full bound three times.
- Revision: 2026-09-27 — The waiter no longer ends at the owner's recorded expiry: a live helios hook build outlived its lease and a waiting push was refused although the OS lock proved the owner alive.
- Revision: 2026-09-26 — The owner record moved past the locked byte, the pre-push entry point waits for a live owner up to its expiry, and an unlocked lease is reclaimed whatever its content; Windows pushes were refused against owners that read as unknown and against 35-hour-old probe leases with no expiry.
- Class: `[arch]`
- Item: ATLAS-BUILD-SOURCE-IDENTITY (closed; delivered by [PR #295](https://github.com/ryancinsight/atlas/pull/295), [PR #296](https://github.com/ryancinsight/atlas/pull/296) and [PR #299](https://github.com/ryancinsight/atlas/pull/299))

## Context

Atlas intentionally gives members one shared Cargo target directory. Cargo's fingerprint and dep-info records do not identify the source checkout that produced a proc-macro or other package artifact. Two exports with identical relative dependency names can therefore reuse an artifact compiled from different source bytes. Apollo's retained release-macro incident recorded a scratch-checkout path and an obsolete parser diagnostic while the canonical source accepted the new syntax.

A Git revision alone is insufficient for a dirty checkout, a branch name is not an identity, and a Cargo fingerprint is an implementation detail rather than a stable contract. A second source tree must not silently overwrite the first tree's record or artifact.

## Decision

### Stable scope and record

`scripts/atlas_build_identity.py` owns one record for each build scope: shared target directory, package, profile, target triple, feature set, toolchain identity, build-affecting environment digest, dependency-closure digest, and the caller's stable command key. The command key names the build-entry-point dimensions without treating `clippy`, tests, and documentation as different source identities. The record is stored atomically under `target/.atlas/source-identity/`, inside the existing cache root. It contains the canonical source root, full Git revision, clean/dirty state, source-tree digest, resolved dependency closure, build dimensions, and hashes of the discovered or explicitly supplied package artifacts. Version 1 through 3 records are stale; malformed or unsupported current records fail closed.

The record path excludes the source revision deliberately. A source transition must contend with the existing owner of the same build scope; otherwise a second source tree could acquire a different lock and overwrite the first record.

### Mismatch and ownership

A missing, malformed, or mismatched record is stale. The gate resolves the package's reachable path and Git dependency closure, acquires the scope lease, cleans the affected non-registry packages plus the selected package, then runs the requested build command and writes the record only after success. Ordinary matching builds reuse the existing artifacts without cleaning. Registry package IDs and graph edges remain part of the closure digest without hashing registry checkout paths.

The lease stores owner root, revision, package, target directory, token, and expiry. The OS file lock is authoritative while a process is alive; the expiry is diagnostic only, since a crashed owner releases its lock and that alone makes the lease reclaimable. The lock covers byte 0 only and the owner record starts at byte 1, because a Windows byte-range lock refuses reads of the locked range from every other handle; keeping the lock on byte 0 keeps exclusion with holders that predate the offset. A live conflicting owner refuses the operation without cleaning, deleting, or overwriting artifacts; the command-line `run` entry point, which the pre-push gate invokes, first waits for that owner with backoff, bounded by `--lease-wait-seconds` alone, and fails without the lease when the bound passes. The recorded expiry is reported but never ends the wait, and holders do not renew it: the lock already proves liveness, so renewal would only refresh a field nothing decides on. An unlocked lease is reclaimed whatever its content: no live process can hold it, and a writer killed mid-record leaves a partial one. A malformed record fails closed.

A lease is held shared or exclusive. A run takes its own package exclusive, because its command writes that package's artifacts, and every dependency in the clean closure shared, because a dependency whose record matches is only read. Once the record shows the scope stale, the run releases every lease and asks again with all of them exclusive, then re-checks staleness before cleaning. Releasing instead of upgrading in place keeps two upgraders from each holding the shared lease the other waits for. Exclusivity therefore covers only a stale run, whose command is the rebuild, and the one package a command writes. It cannot end earlier, since the clean, the rebuilding command, and the record written after it are one step. The next hook step finds a matching record and reads its dependencies shared. Concurrent builds that read one dependency still take turns at Cargo's own build-directory lock, which also serializes a rebuild Cargo decides on without us. A matching record guarantees only that no run cleans that dependency underneath them. Windows takes the byte-0 lock with `LockFileEx`, which has a shared mode and conflicts with the `msvcrt.locking` exclusive locks of earlier holders. POSIX takes it with `flock` shared or exclusive, the call earlier holders used; `fcntl` record locks would not see theirs.

Requests are served in arrival order. Each request writes a ticket file named by the system-wide monotonic clock into the lease's queue directory and locks it until it releases the lease, so an unlocked ticket belongs to a process that has gone. That ticket is ignored, and deleted once it is 10 s old; a younger one may belong to a requester that has not locked it yet. An exclusive request waits for every earlier live ticket, and a shared request for earlier exclusive tickets only. Readers that arrive together therefore share, while a waiting writer holds back every later reader and cannot be starved by a stream of them. A holder that releases and asks again gets a new ticket and queues behind requests already waiting, so a repeating holder cannot starve them either. Writer preference alone was rejected: it still lets a repeating writer win every race against a polling waiter, which is the failure observed. A waiter keeps one ticket for its whole wait. Leases are taken in sorted scope order, and a request waits only on its own lease's holders or on earlier requests for that lease; holders wait only on later leases, so no wait forms a cycle. Holders whose checker predates the queue take no ticket and are ordered by the lock alone until the fleet runs the queued code.

The lease key is (package name, target directory), without the source revision or target triple. Two revisions of one source root produce the same artifact names, so a revision key would let them clean and overwrite each other; a cross-target build still compiles its proc-macro and build-script dependencies into the host directory, so a triple key would let two triples clean and rebuild one host artifact concurrently. The target resolver uses the Git common directory so a linked Atlas worktree still addresses the primary cache.

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

The core regression suite covers a source transition, matching-source reuse, different-root identity, dependency-closure transitions and cleanup, active-owner preservation, owner naming across processes, the pre-push wait for a live owner past its recorded expiry and its wait bound, shared readers proceeding together, shared and exclusive holders excluding each other and a shared reader blocking a dependency clean, a repeating exclusive holder and a stream of shared readers not starving a waiter, crashed holders and waiters releasing their place, expired and unlocked malformed lease recovery, dirty and ignored-source identity, build-environment dimensions, target-directory exclusion, and artifact-boundary rejection. The integrated hook regression additionally proves that a stale package is rebuilt once per source transition, an unrelated package artifact is preserved, a pushed-revision mismatch is refused, overlay lock rewrites are restored, linked worktrees receive the member manifest, environment failures are not accepted, and a live owner blocks cleaning without changing source files. Focused Python tests, the full scripts suite, pre-push hook tests, conformance, the ARCH-008 oracle, and the pin-drift gate are required before merge.

## References

- [PR #295](https://github.com/ryancinsight/atlas/pull/295)
- [PR #296](https://github.com/ryancinsight/atlas/pull/296)
- [PR #277](https://github.com/ryancinsight/atlas/pull/277)
- [PR #299](https://github.com/ryancinsight/atlas/pull/299)
- [scripts/atlas_build_identity.py](../../scripts/atlas_build_identity.py)
- [scripts/atlas_build_source.py](../../scripts/atlas_build_source.py)
- [scripts/atlas_build_artifacts.py](../../scripts/atlas_build_artifacts.py)
- [scripts/git-hooks/pre-push](../../scripts/git-hooks/pre-push)
- [Apollo ADR 0051](../../repos/apollo/docs/adr/0051-composite-phase-schedules.md)
