# ADR 0064: Shared build source and artifact identity

- Status: Accepted
- Date: 2026-09-24
- Class: [arch]
- Revision: October 6, 2026 â€” Defined meta-root Cargo applicability and tooling authority.
- Driver: [Atlas PR #500](https://github.com/ryancinsight/atlas/pull/500) and
  [Moirai PR #596](https://github.com/ryancinsight/moirai/pull/596)

## Context
Atlas members share one target. Cargo fingerprints and dep-info omit the producing checkout, so different source bytes can
address the same artifact. Revisions omit dirty and untracked source, branches are mutable, and Cargo's fingerprint format is
internal. Concurrent roots need one protocol that prevents a clean or artifact rewrite from invalidating another build.

## Decision
### Tool source
Hooks normally extract conformance and build-identity tools from fetched Atlas default. A coordinated provider update may select
exactly one immutable Atlas commit for those tools with command-scoped `git -c atlas.preparedTools=<full-sha> push`. The value
must occur once, be a full 40-character commit ID, resolve in the registered Atlas object store, and contain a complete scripts
tree. Empty, malformed, unavailable, or incomplete values fail closed, and the hook prints the selected commit. Secret scanning,
artifact-budget checks, lockfile tools, and conformance baselines remain fetched-default inputs. `publish-hooks --source-ref`
forwards its resolved source as `atlas.preparedTools`; without that selection, every tool comes from fetched default.

### Record and input identity
`atlas_build_records.py` owns the record format, `atlas_build_inputs.py` owns dimensions and dependency data, and
`atlas_build_identity.py` owns the run protocol. Record version 6 stores one atomic record under `target/.atlas/source-identity`
per shared target, package, profile and target, features, toolchain, environment, Cargo configuration, dependency closure,
command key, and complete Cargo selection. Selection includes every package in one invocation because feature unification can
change all selected artifacts. Older, missing, malformed, or unsupported records are mismatches. Records contain the diagnostic
source root, revision, dirty-state digest, dependency closure, dimensions, and actual artifact hashes. The source root is not
compared; workspace path sources are workspace-relative. Revision is excluded from record paths and lease keys so transitions
contend for the same artifacts.

Repository identity hashes the revision, tracked dirty diff, and untracked or ignored source bytes. Target output is excluded;
an ignored overlay lockfile is excluded only after lock validation or restoration. Status and identity are read afresh at each
phase and final verification. The environment digest covers Cargo profile/build/target/unstable/host/alias namespaces, `CARGO`,
encoded Rust flags, incremental mode, compiler/bootstrap settings, compiler wrappers, Rust flags, and leading `env NAME=VALUE`
assignments. Rustdoc-only variables are excluded so clippy, tests, and rustdoc share a record; Cargo's own doc-unit fingerprint
still tracks them, and the run adopts newly written rustdoc fingerprint bytes. Any required environment identity command failure
fails closed and cannot create a verified artifact record.

The configuration digest covers both config filenames in every `.cargo` directory from repository root to filesystem root,
Cargo-home configuration, explicit path or inline `--config` arguments, and recursive include lists or tables. Includes are
cycle-guarded and paths are framed by depth and name, not machine-specific absolute roots. UTF-8 BOMs and Cargo's known
trailing-inline-table-comma, multiline-inline-table, `\e`, and `\xHH` divergences are accepted; other parse failures fail
closed.

Complete Cargo metadata supplies normal, build, and development edges; resolved manifests, features, target expressions and
kinds, editions, targets, dependency edges, and workspace manifest. Path, Git, and registry sources receive content identities.
The overlay-rewritten lockfile is not hashed because resolved package identities and revisions are recorded. Package-source
digests use a persistent cache under `.atlas/source-identity/package-source`, keyed by path, size, modification time, and
symlink-target stat data, and are written only when that fingerprint is stable before and after the read. Within one dependency
snapshot each distinct repository or package root is fingerprinted once; another snapshot repeats fresh fingerprint checks and
observes intervening mutations.

### Artifacts and cleaning
Managed artifacts must be inside the shared target. Explicit and discovered ownership matches exact Cargo target names, never
prefixes. A matching record hashes only named artifacts; an exclusive rebuild rediscovers names and drops retired artifacts. A
stable artifact needs two reads with unchanged size and modification time within a bounded deadline. Changed, unreadable, or
never-settling artifacts are not accepted; an unverified marker forces the next clean. Dependencies are rehashed after each
Cargo command because Cargo can rewrite them in place. Shared packages use recorded or sibling names; exclusive packages are
rediscovered.

An artifact-only mismatch cleans its owners. Source, configuration, or dependency-shape mismatch cleans affected path packages;
an unattributable changed file cleans every path package. Registry packages are never cleaned. One `cargo clean` receives the
union with profile and target dimensions. Git dependencies use stamps under `.atlas/source-identity/git-build`, keyed by build
directory, source/package identity, profile, and target. A building sentinel precedes cleaning and Cargo; only success plus a
stable final snapshot writes the digest. Failed or killed commands leave a stale sentinel, which is honored even when the record
matches or a custom clean command runs.

### Lease protocol
Each `(package name, target directory)` has one lease. Revision and target triple are omitted because host artifacts overlap;
linked worktrees use the Git common directory. Cross-platform shared/exclusive byte-range locks reserve byte 0 for the lock and
byte 1 onward for owner diagnostics. The operating-system lock is authoritative, only an exclusive holder writes owner data,
expiry is diagnostic, and unlocked malformed state is reclaimable.

Queue tickets carry a system-monotonic arrival, mode, and shared run ID; every scope orders `(arrival, run)` identically.
Exclusive claims wait behind earlier live tickets and shared claims behind earlier exclusive tickets. A run claims every phase
lease together or none, holds no lock while waiting, retains tickets at every scope, and shares one deadline. This removes
hold-and-wait deadlock and prevents later readers starving a multi-package writer, at the cost of a possible idle convoy.
`claims.jsonl` records run, order, leases and modes, wait and hold times, blocker, and phase, rotating at 1 MiB with one prior
file.

A first shared claim proceeds only on an exact record match. A mismatch releases all leases, acquires the complete set
exclusively, and re-reads before cleaning; there is no in-place upgrade. An equivalent sibling record can establish reuse.
Before Cargo starts, unchanged non-root packages downgrade to shared without losing queue position. Full/custom cleaning or
explicit artifacts retains exclusive leases; a failed conversion fails closed. Live-owner conflict is bounded by
`--lease-wait-seconds`, identifies the owner, and changes nothing. Command failure preserves the previous successful record and
releases all leases. Exact match prevents cleaning under readers but does not assume Cargo is read-only, so leases remain held
through the command and final source/dependency verification.

### Build entry points
Pre-push builds each pushed commit, not the working tree. It exports the commit's object store into one reusable short path by a
symlink-preserving, long-path-safe checkout outside the overlay and cleans it on interruption. Deletion refs need no build. One
identity sequence covers all gated packages and holds leases from clippy through nextest, rustdoc, and the final identity read.
Every step uses the committed lock; records require command success and unchanged final source and dependencies. Other build
entry points reuse the same modules and protocol.

Atlas has no root Cargo manifest and fabricates none. Secret/artifact-budget/lock/baseline checks use fetched default; only
conformance and build identity may use prepared scripts. `<meta>` carries revision and baseline without a repository. Changed
paths map to the nearest actual nested Cargo manifest before metadata. Owners: `tools/checkout-path-dependencies`,
`tools/criterion-regression`, `tools/gitlink-coherence`, and `tools/version-guard`; `tools/_template/template-Cargo.toml` is
excluded. Each selected owner runs the complete bounded locked metadata/fmt/clippy/nextest/rustdoc/final-identity sequence on
its actual manifest/export/lock/shared target. Cargo is inapplicable only after content gates find no owner.
Removed/unreadable/malformed selected manifests/locks and ownership/metadata/stage errors fail closed. Meta adds no legacy
relative `.githooks` switch or separate skip/bypass. The immutable fetched hook stays the trust root; prepared selection remains
public. Provider changes require all 28 executable member copies before pin advance; versions/releases remain unchanged.

## Known limits
- Alias-internal config paths are not followed unless present in executed arguments. Unhandled TOML 1.1 syntax fails closed.
- Cargo-internal build-script `rustc-env` and wrapper exports are not decomposed; configuration `[env]` stays covered.
- A package-source edit preserving both size and modification time can evade the persistent stat-keyed digest cache.
- External unstamped Git artifacts may be reused; one build directory is stamped; registry artifacts are not cleaned.
- A matched Git build can miss a source edit made and reverted during the command. `ATLAS-IDENTITY-MIDRUN-GIT-EDIT` tracks it.
- Cargo fingerprints remain part of rustdoc and external-artifact reuse. During mixed-version rollout, an old sequential lease
  holder can block the all-or-none protocol until its bounded deadline.

## Consequences
Equivalent exports and worktrees reuse exact-input artifacts. Changed inputs rebuild the narrowest sound package set; ambiguous
ownership fails closed and broadens cleaning. Concurrent roots cannot silently clean or overwrite managed artifacts. Records and
caches are derived state, so deletion causes conservative rebuilding. One shared target remains, with measurable hashing,
metadata, and lease cost exposed by claim histories and stage timings.

## Alternatives rejected
- Legacy `.githooks` lets the tip replace its gate and duplicates policy; immutable fetched tooling remains the trust boundary.
- Per-source targets fork the cache; manual cleaning has no ownership; Cargo fingerprint JSON is unstable. Whole-target or
  whole-closure cleaning discards unrelated reuse, and repository-name filters miss actual shared dependencies.
- Sequential lease acquisition permits deadlock. Relinquishing partial-claim queue position permits reader starvation; strict
  global FIFO delays nonconflicting runs without strengthening correctness.
- A longer lease wait only delays refusal. Holding every dependency exclusively serializes safe readers, so unchanged non-root
  packages downgrade to shared.
- Rehashing every package for every closure dominated dependency snapshots. The stable stat-keyed cache bounds that work and
  per-snapshot memoization removes duplicates while retaining fresh checks between snapshots. A persistent cache that skipped
  fresh fingerprint checks was rejected.

## Verification
Focused identity tests cover dirty, ignored, exported, and final-mutated source; environment and configuration inputs and
failures; dependency shape, features, manifests, and profiles; artifact attribution, settling, retirement, and ownership;
package-cache invalidation and snapshot deduplication; path/Git cleaning, stamps, sentinels, profiles, and custom cleans; and
shared/exclusive claims, fairness, all-or-none acquisition, downgrade, interoperability, deadlines, and dead owners. Real-Cargo
cases cover repeated exports, multi-package commands, and failures. Integrated hook tests cover pushed-revision export,
committed locks, manifest and live-owner changes, prepared-tool selection, and refusal paths. Configured identity, pre-push,
conformance, architecture, and pin-drift suites remain executable gates; final combined, normal-push, hosted, and independent
evidence remains pending.

## References
- `scripts/atlas_build_records.py`; `scripts/atlas_build_inputs.py`
- `scripts/atlas_build_source.py`; `scripts/atlas_build_artifacts.py`
- `scripts/atlas_build_lease.py`; `scripts/atlas_build_identity.py`
- `scripts/git-hooks/pre-push`; `scripts/tests/test_atlas_build_identity.py`; `scripts/tests/test_atlas_pre_push_gate.py`
