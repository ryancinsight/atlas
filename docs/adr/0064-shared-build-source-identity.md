# ADR 0064: Shared build source and artifact identity

- Status: Accepted
- Date: 2026-09-24
- Revision: 2026-09-26 — Validate Git source identities in persisted records and retain bounded build execution.
- Class: `[arch]`
- Item: [ATLAS-BUILD-RECORD-001](../../backlog.md#atlas-build-record-001)
- Delivery: [PR #314](https://github.com/ryancinsight/atlas/pull/314)

## Context

Atlas intentionally gives members one shared Cargo target directory. Cargo's fingerprint and dep-info records do not identify the source checkout that produced a proc-macro or other package artifact. Two exports with identical relative dependency names can therefore reuse an artifact compiled from different source bytes. Apollo's retained release-macro incident recorded a scratch-checkout path and an obsolete parser diagnostic while the canonical source accepted the new syntax.

A Git revision alone is insufficient for a dirty checkout, a branch name is not an identity, and a Cargo fingerprint is an implementation detail rather than a stable contract. A second source tree must not silently overwrite the first tree's record or artifact.

## Decision

### Stable scope and record

`scripts/atlas_build_identity.py` describes one record for each build scope: shared target directory, package, profile, target triple, feature set, toolchain identity, build-affecting environment digest, dependency-closure digest, and the caller's stable command key. The command key distinguishes build-affecting entry-point dimensions without treating clippy, tests, and documentation as different source identities. The record is stored atomically under `target/.atlas/source-identity/`, inside the existing cache root. It contains the canonical source root, full Git revision, clean/dirty state, source-tree digest, resolved dependency closure, build dimensions, and hashes of discovered or explicit package artifacts. Versions 1 through 5 are stale; malformed or unsupported current records fail closed.

The record path excludes the source revision deliberately. A source transition must contend with the existing owner of the same build scope; otherwise a second source tree could acquire a different lock and overwrite the first record.

### Mismatch and ownership

A missing, malformed, or mismatched record is stale. The gate resolves the package's reachable path and Git dependency closure, acquires the scope lease, cleans the affected non-registry packages plus the selected package, runs the requested build command, and writes the record only after success. Ordinary matching builds reuse the existing artifacts without cleaning. Path packages and Git checkouts use compiler-visible source identities; Git identity covers the checkout repository, including files outside a dependency package directory. Registry package IDs and graph edges remain in the closure digest, while registry packages use a content digest rather than checkout-path identity.

The lease stores owner root, revision, package, target directory, token, and expiry. The OS file lock is authoritative while a process is alive; expiry is recovery metadata after a crash. A live conflicting owner refuses the operation without cleaning, deleting, or overwriting artifacts. An unlocked but unexpired owner record also refuses takeover; an expired record may be recovered after acquiring the OS lock. Successful release clears owner metadata before unlocking. Lease file and record operations are relative to the already-open target-directory handle; each path component rejects symlinks or reparse points. This is cooperative same-user locking: a process with the same OS identity that deliberately replaces the lease directory or file can create a second lock inode, and the mechanism does not isolate hostile same-user processes.

Build commands have a finite five-minute timeout. Captured stdout and stderr share a 64 MiB limit; exceeding it terminates the process boundary and returns a typed error instead of retaining unbounded output. Build output is inherited rather than captured, so the byte limit applies only to captured streams. POSIX stdin uses a temporary file so a large input does not block process startup. On Windows, the child is suspended until assigned to a Job Object; contained descendants are terminated and drained before the parent result returns. A Windows Cargo check left an MSVC `vctip.exe` process in the job after Cargo exited, so the runner drains such survivors rather than returning while they remain.

On Linux, the runner observes direct-child exit with `waitid(WNOWAIT)`, keeping its PID reserved while it terminates remaining process-group members. It checks group membership through procfs and reaps adopted zombies by exact PID without consuming the group leader. Captured pipes are drained with selectors, and unreadable process entries fail cleanup. Commands inherit the held target-directory descriptor and use `/proc/self/fd/<n>` for `CARGO_TARGET_DIR`, so renaming the original target path cannot redirect build output. Other POSIX hosts are rejected before process launch because this implementation cannot verify group termination there without probing a potentially reused process-group ID after reaping the leader. A Linux descendant can leave the initial group with `setpgid()` or `setsid()`; this runner is not a sandbox. Python documents that `start_new_session` calls `setsid()` before exec, and POSIX defines process-group membership and lifetime ([Python subprocess](https://docs.python.org/3/library/subprocess.html#popen-constructor), [POSIX `setpgid()`](https://pubs.opengroup.org/onlinepubs/009604599/functions/setpgid.html), [POSIX process-group lifetime](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap03.html#tag_03_283)). A malformed lease or record fails closed. The target resolver uses the Git common directory so a linked Atlas worktree still addresses the primary cache.

### Build entry points

`atlas_build_source.py`, `atlas_build_artifacts.py`, and `atlas_build_record.py` own source, dependency/artifact, and persisted-record contracts. `atlas_build_run.py` and `atlas_build_check.py` share those contracts without duplicating record formats. The member pre-push gate refuses a pushed revision that differs from the checkout, invokes the build workflow for each changed package before accepting clippy, tests, or documentation, and passes the member manifest in linked-worktree mode. One stable command key per package lets those steps share a record. The integration composes with the existing conformance push guard in PR #277; it does not duplicate that guard or hand-edit member hook copies.

The module records artifact hashes after the command. Artifact ownership follows Rustc's target and crate filename forms, including WebAssembly files in target-profile roots, platform-specific extensions, and only the exact 16-hex-digit disambiguator suffix. It does not treat Cargo fingerprint JSON as a public schema, and it does not claim that a missing `.fingerprint` directory proves source identity.

## Failure modes

- A Git dependency record contains checkout source identity; a registry record contains package content digest. Versions 1 through 5 are stale.
- A Git dependency's identity covers its checkout root, not only its package directory, so included source files outside that package change the dependency digest.
- Source identity anchors at the full Git revision and adds a sorted manifest of compiler-visible deltas, including distinct missing tracked paths and empty directories. Every included regular file is read and hashed from its raw working bytes; its Git object identity is compared with the committed tree to detect changes even when Git's stat cache or worktree-status output misses them. Staged and `HEAD` gitlink pointers plus initialized child checkouts are included; uninitialized gitlinks are explicit identity deltas. `.git` metadata, a root-level `target`, conventional dependency/runtime cache directories, and caller-supplied excluded roots do not participate. Other source directories, including a nested directory named `target`, remain part of identity unless explicitly excluded.
- A source symlink must resolve inside the identified tree and may not point into `.git` metadata, an implicitly excluded generated/cache directory, or another excluded root, whose bytes are outside the identity contract.
- A source path or artifact outside the shared target is rejected before any clean.
- A full Cargo metadata graph is required when artifacts are discovered implicitly; an unresolved or name-ambiguous dependency closure fails closed.
- A build-affecting environment change produces a different record scope.
- A lockfile rewrite caused by the development overlay is excluded from the source digest only after the pushed lock has been checked and the working copy is restored.
- A live owner conflict returns a diagnostic naming the owner and revision and performs no destructive action.
- An unexpired unlocked lease cannot be overwritten, an expired lease can be recovered after its lock is acquired, and normal release clears owner metadata.
- A target-root symlink, `.atlas` link/junction, or lease-file link cannot redirect record or lock operations outside the target handle.
- Rustc package artifact names match exact package/target stems and platform extensions; arbitrary suffixes and neighboring package names do not match.
- Build commands stay within the committed five-minute bound. Windows Job Objects and Linux process groups terminate and drain contained descendants; non-Linux POSIX hosts fail before launch. A same-user process that deliberately replaces the lease directory is outside the cooperative-locking threat model.
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

The regression suite covers source transitions and reuse, different roots, dependency-closure changes, Git dependency record write/read/check, checkout-root changes outside a package directory, live/expired leases, dirty and ignored files, missing paths, excluded-link boundaries, generated-directory exclusions, presentation-independent fingerprints, staged and uninitialized gitlinks, reparse-safe target access, exact artifact naming and content hashing (including WebAssembly), bounded pipe capture and closure, output-limit termination, target-path replacement during a build command, Windows Job cleanup, Linux descendant cleanup, Linux non-ASCII process names, and adopted-zombie reaping under a subreaper. Hook tests verify their declared call boundaries; they do not substitute for running the pre-push gate itself. The full Python suite, pre-push gate tests, conformance, the ARCH-008 oracle, and the pin-drift gate remain required verification.

## References

- [Current delivery PR #314](https://github.com/ryancinsight/atlas/pull/314)
- [PR #277](https://github.com/ryancinsight/atlas/pull/277)
- [PR #299](https://github.com/ryancinsight/atlas/pull/299)
- [scripts/atlas_build_identity.py](../../scripts/atlas_build_identity.py)
- [scripts/atlas_build_source.py](../../scripts/atlas_build_source.py)
- [scripts/atlas_build_artifacts.py](../../scripts/atlas_build_artifacts.py)
- [scripts/git-hooks/pre-push](../../scripts/git-hooks/pre-push)
- [Apollo ADR 0051](../../repos/apollo/docs/adr/0051-composite-phase-schedules.md)
- [Python subprocess Popen: start_new_session](https://docs.python.org/3/library/subprocess.html#popen-constructor)
