# ADR 0064: Shared build source and artifact identity

- Status: Accepted
- Date: 2026-09-24
- Revision: 2026-09-25 — Accepted the locked dependency-content, closure-lease, and artifact-package design.
- Revision: 2026-09-27 — A run reads its dependencies under shared leases and compares only the artifacts its record names; it runs exclusive whenever that record does not match exactly, and one wait bound covers the whole run. Every lease had been exclusive, so one hook's long test run blocked every other build that read the same dependency.
- Revision: 2026-09-27 — Lease requests are served in arrival order: a coeus hook re-running its steps re-took the aequitas lease the instant it released it, and a polling helios push waited out its full bound three times.
- Revision: 2026-09-27 — Leases gained shared and exclusive lock modes, and a check probes shared; a held lease file is never empty and its record is overwritten before it is cut, because an empty file let an earlier checker's opener fault on the locked byte.
- Revision: 2026-09-27 — Staleness is decided by content, never the source root path, and a fresh gate export is identified without re-hashing it: a new export path per push made every record stale and cleaned the whole non-registry closure, and kwavers's read-tree index re-hash passed the 60 s git timeout.
- Revision: 2026-09-27 — The pre-push gate builds an export of the pushed revision instead of refusing a push that differs from the checkout: private-index pushes from shared trees were refused on a peer's branch and dirt (ritk, kwavers).
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

Staleness compares content only: the revision, clean/dirty state and tree digest, the build dimensions, the dependency closure, and the artifacts. The source root is recorded for diagnostics and lease ownership but never compared, and path packages inside the workspace are named by their workspace-relative directory, because cargo spells a path package's ID with its absolute directory and the pre-push gate builds each push in a new temporary export. A gate export -- a repository borrowing the member's objects through `objects/info/alternates` whose index was read from `HEAD`'s tree and never stat'ed -- is the pushed tree by construction, so it is identified without `git diff HEAD`, which would re-hash every file.

The record path excludes the source revision deliberately. A source transition must contend with the existing owner of the same build scope; otherwise a second source tree could acquire a different lock and overwrite the first record.

### Mismatch and ownership

A missing, malformed, or mismatched record is stale. The gate resolves the package's reachable path and Git dependency closure, acquires the scope lease, cleans the affected non-registry packages plus the selected package, then runs the requested build command and writes the record only after success. Ordinary matching builds reuse the existing artifacts without cleaning. Registry package IDs and graph edges remain part of the closure digest without hashing registry checkout paths.

The lease stores owner root, revision, package, target directory, token, and expiry. The OS file lock is authoritative while a process is alive; the expiry is diagnostic only, since a crashed owner releases its lock and that alone makes the lease reclaimable. The lock covers byte 0 only and the owner record starts at byte 1, because a Windows byte-range lock refuses reads of the locked range from every other handle; keeping the lock on byte 0 keeps exclusion with holders that predate the offset. A lease is held shared or exclusive. A held lease file is never empty: an earlier checker that finds it empty writes byte 0 and crashes on the lock, so an opener writes a placeholder byte before it locks, and a write refused because a holder locked the byte meanwhile is left to that holder's byte. Only an exclusive holder writes the record, which it overwrites and then cuts to length rather than truncating first. Windows takes the byte-0 lock with `LockFileEx`, whose shared mode conflicts with the `msvcrt.locking` exclusive lock of earlier holders, and treats only `ERROR_LOCK_VIOLATION` as contention. POSIX takes it with `flock`, the call earlier holders used; `fcntl` record locks would not see theirs. A check only reads artifacts, so it probes shared.

Requests are served in arrival order. Each request creates a ticket file in the lease's queue directory, named by the system-wide monotonic clock at arrival, and holds an exclusive lock on it until it releases the lease. An exclusive request waits for every earlier live ticket; a shared request waits only for earlier exclusive tickets. Readers that arrive together therefore share, and a waiting writer holds back every later reader, so a stream of readers cannot starve it. A holder that releases and asks again gets a new ticket behind the requests already waiting, so a repeating holder cannot starve them either. A waiter keeps its ticket for its whole wait. Writer preference alone was rejected: it still lets a repeating writer win every race against a polling waiter, which is the failure observed. Liveness is probed with a shared lock, so concurrent probes never make a dead ticket look held to one another. A requester that loses the race between creating its ticket and locking it retries under a new name with the same arrival; it closes the losing handle on every path. On POSIX a peer that saw a new ticket unlocked can still unlink it after its requester locked it; each attempt checks that the ticket's path still names the locked file and re-creates it with the same arrival if not, so the ticket is missing for at most one polling interval. Every request scans the whole queue and removes each dead ticket, whatever its mode or position. A dead ticket that cannot be removed because a probe has it open at that moment, the only Windows case, is removed by the next request, so dead tickets never outlive the next request. Holders whose checker predates the queue take no ticket and are ordered by the lock alone until they fetch the current checker.

A live conflicting owner refuses the operation without cleaning, deleting, or overwriting artifacts; the command-line `run` entry point, which the pre-push gate invokes, first waits for that owner with backoff, bounded by `--lease-wait-seconds` for the whole run, across every lease and both phases below, and fails without the lease when the bound passes. The recorded expiry is reported but never ends the wait, and holders do not renew it: the lock already proves liveness, so renewal would only refresh a field nothing decides on. Leases are taken in sorted scope order, and a request waits only on holders of its own lease, which wait only on later leases, or on earlier requests for that lease, so no wait forms a cycle. An unlocked lease is reclaimed whatever its content: no live process can hold it, and a writer killed mid-record leaves a partial one. A malformed record fails closed.

A run takes the lease of the package its command builds exclusive and the leases of its clean-closure dependencies shared, then reads its record. Only when the record matches exactly (source, build dimensions, dependency closure, and every artifact file it names) does the run keep that shape. Otherwise it releases every lease, takes them all exclusive, and reads the record again, because a holder may have rebuilt the scope in between. It cleans only if the record still does not match. Releasing before asking again, rather than upgrading in place, keeps two upgraders from each holding the shared lease the other waits for. A missing record whose build a sibling command key already matched runs exclusive without cleaning.

Under a shared lease, Cargo can still write into a dependency's `deps/` and `.fingerprint`. It writes new metadata-hash variants for another profile, feature set, or check mode. It also rewrites the files a record names in place, under the same name, whenever it rebuilds that unit, and a changed modification time alone makes it rebuild; the rewritten file can be byte-identical. While rustc rewrites a file, a concurrent read of it on Windows fails with a permission error. The run therefore hashes shared dependency files only once, before its command, and only the files its record names, found by name and never by discovery; variants beside them are outside every comparison. A named file that cannot be read, or whose content changed, is a mismatch and sends the run through the exclusive path: a conservative rebuild, never an accepted artifact. After the command, the run hashes only the package it holds exclusive. The dependency entries it records are the digests it verified before the command, not a second reading, because another reader's Cargo may be rewriting those files at that moment. A dependency rewritten since, identical or not, is re-hashed by the next run's comparison. The alternative, an exclusive lease for any window in which the command may write a dependency, was rejected: Cargo decides that only while it builds, so every command would hold every dependency exclusive, the starvation this design removes. The exclusive window is therefore one stale run. Its clean, its rebuilding command, and the record written after it are a single step that cannot end earlier, and the hook's next step finds a matching record and reads shared. Concurrent readers still take turns at Cargo's own build-directory lock. A match guarantees that no run cleans a dependency underneath its readers. It does not guarantee that Cargo leaves the named files untouched, and nothing in the design relies on that.

The lease key is (package name, target directory), without the source revision or target triple. Two revisions of one source root produce the same artifact names, so a revision key would let them clean and overwrite each other; a cross-target build still compiles its proc-macro and build-script dependencies into the host directory, so a triple key would let two triples clean and rebuild one host artifact concurrently. The target resolver uses the Git common directory so a linked Atlas worktree still addresses the primary cache.

### Build entry points

The shared identity module is the single policy surface. The member pre-push gate builds an export of the pushed revision (`git archive <sha>^{tree}`) in a temporary directory outside the stack's `[patch]` overlay, never the checkout, which a shared tree holds on a peer's branch or dirty. The export is a repository whose `HEAD` is the pushed commit and whose object store is the member's, so the module records the pushed revision as the source; the gate invokes the module with the export as `--root` for each changed package before accepting clippy, tests, or documentation, all under `--locked` against the committed lock. One stable command key per package lets those steps share a record. The integration composes with the existing conformance push guard in PR #277; it must not duplicate that guard or hand-edit member hook copies. Other build entry points use the same module when they compile packages, rather than implementing a second provenance format.

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

The core regression suite covers a source transition, matching-source reuse, same-revision reuse from another export path, unrefreshed-export identification without a re-hash, dependency-closure transitions and cleanup, active-owner preservation, owner naming across processes, shared readers building beside one another, a shared reader blocking a dependency clean, a reader writing new dependency variants beside another reader's check, a dependency rewritten in place during a reader's command, the re-check after the exclusive retake, one wait bound across a run's leases, the pre-push wait for a live owner past its recorded expiry and its wait bound, expired and unlocked malformed lease recovery, dirty and ignored-source identity, build-environment dimensions, target-directory exclusion, and artifact-boundary rejection. The integrated hook regression additionally proves that a stale package is rebuilt once per source transition, an unrelated package artifact is preserved, a push from a checkout on another branch with dirty files and a divergent lock is judged on the pushed content, the export's manifest reaches every step, environment failures are not accepted, and a live owner blocks cleaning without changing source files. Focused Python tests, the full scripts suite, pre-push hook tests, conformance, the ARCH-008 oracle, and the pin-drift gate are required before merge.

## References

- [PR #295](https://github.com/ryancinsight/atlas/pull/295)
- [PR #296](https://github.com/ryancinsight/atlas/pull/296)
- [PR #277](https://github.com/ryancinsight/atlas/pull/277)
- [PR #299](https://github.com/ryancinsight/atlas/pull/299)
- [scripts/atlas_build_identity.py](../../scripts/atlas_build_identity.py)
- [scripts/atlas_build_lease.py](../../scripts/atlas_build_lease.py)
- [scripts/atlas_build_lock.py](../../scripts/atlas_build_lock.py)
- [scripts/atlas_build_queue.py](../../scripts/atlas_build_queue.py)
- [scripts/atlas_build_source.py](../../scripts/atlas_build_source.py)
- [scripts/atlas_build_artifacts.py](../../scripts/atlas_build_artifacts.py)
- [scripts/git-hooks/pre-push](../../scripts/git-hooks/pre-push)
- [Apollo ADR 0051](../../repos/apollo/docs/adr/0051-composite-phase-schedules.md)
