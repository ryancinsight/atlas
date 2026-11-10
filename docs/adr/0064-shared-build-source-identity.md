# ADR 0064: Shared build source, artifact, and gate identity

- Status: Accepted
- Date: 2026-09-24
- Class: [arch]
- Driver: [Atlas PR #626](https://github.com/ryancinsight/atlas/pull/626), [Atlas PR #623](https://github.com/ryancinsight/atlas/pull/623), [Atlas PR #588](https://github.com/ryancinsight/atlas/pull/588), [Atlas PR #500](https://github.com/ryancinsight/atlas/pull/500) and [Moirai PR #596](https://github.com/ryancinsight/moirai/pull/596)
- Item: ATLAS-BUILD-SOURCE-IDENTITY (closed by [PR #295](https://github.com/ryancinsight/atlas/pull/295), [PR #296](https://github.com/ryancinsight/atlas/pull/296), and [PR #299](https://github.com/ryancinsight/atlas/pull/299))
- Revision: 2026-11-10 — A root `Cargo.toml` change confined to `[workspace.dependencies]` gates only the members `atlas_cast_gate.py resolved-changes` names (new members, signature changes, and members that are or reach a package a changed entry names or one that package reaches, at either revision, since metadata's unified features can hide the entry's effect from every signature) plus path-rule owners; any other root change, a toolchain, cargo or nextest config change, a manifest Python cannot parse, or a revision cargo cannot resolve gates every member, and a base the hook cannot export, any other scope failure, or a scope naming a non-member blocks the push. The lockfile check exports into the reused export root, rebuilt once when a killed run left it unusable. The ritk#849 branch tip 33e8a4499, which drops three table entries, gated 43 members; on 52ef00f99..33e8a4499 `resolved-changes` names only `ritk-snap`.
- Revision: 2026-11-10 — Added revision-bound lock-owner inventories that disable promisor lazy fetch and fail when a committed Cargo input is missing locally.
- Revision: 2026-11-10 — Lock updates resolve one graph against simultaneous immutable provider commits, then remove the temporary transport and verify full locked metadata.
- Revision: 2026-11-09 — A killed run's rebuilt artifacts are resumed, not cleaned again: per-package writer marks (below), after a cold ritk push outlasted the 600-second deadline four times, each rerun cleaning what the killed run had rebuilt.
- Revision: 2026-11-09 — Compacted the as-built contract and required hook installation and publication to materialize the same source-keyed immutable supervisor family; publication keeps that runtime invocation-local so preparing a publication cannot replace the live installed gate.

## Context

Atlas members share one Cargo target. Cargo fingerprints and dep-info do not identify the producing checkout, revisions omit dirty and untracked source, branches move, and Cargo's fingerprint format is internal.
Concurrent roots therefore need one protocol that prevents a clean or rewrite from invalidating another build while preserving one cache.

## Decision

The lock sweep inventory reads every committed standalone lock owner at one Atlas revision, including nested and excluded workspaces, without consulting checkouts or fetching. Every Git process disables promisor lazy fetch, so a missing committed object fails instead of mutating the object store. It retains fixture exemptions and missing sibling-lock diagnostics; every first-party Git package identity must name a registered provider.
The update sweep creates temporary bare views whose object alternates point at registered provider stores and whose sole advertised head is the selected commit. Per-process Git URL rewrites expose all selected heads to one narrowed Cargo update; no global configuration, manifest, or source URL changes. Query-constrained sources refuse. After the views and rewrites are removed, full locked offline metadata must report every selected package version, original URL spelling, and exact revision.

### Tool and runner source

The fetched immutable Atlas hook remains the trust root. Hooks normally extract conformance and build-identity tools from fetched Atlas default.
A coordinated provider update may select exactly one immutable Atlas commit for those tools with command-scoped `git -c atlas.preparedTools=<full-sha> push`.
The value occurs once, is a full 40-character commit ID in the registered Atlas object store, names a complete scripts tree, and is printed; empty, malformed, unavailable, or incomplete selection fails closed.
Prepared member source never selects credential or secret scanners, artifact-budget or lockfile checkers, or conformance baselines; those remain fetched-default inputs.
`publish-hooks --source-ref` passes its resolved immutable source as `atlas.preparedTools` only to the publication push; without it all tools come from fetched default.

Hook installation and publication use one source-keyed materializer for the complete immutable runner family: `pre_push_gate.py`, `process_tree.py`, platform process-tree modules, `atlas_build_lock.py`, and the exact Python interpreter.
Installation stores that family beside the immutable shims under the Git common directory, keyed by hook-source commit; the installed pre-push shim enters it before source-ref lookup.
`install-hooks --source-ref <full-commit>` stages a judged future bootstrap immediately before landing, without moving the fetched trust ref. The pre-push shim rejects fetched sources outside the staged commit's descendants; prelanding invocation and rollback below that floor refuse before hook execution. After landing, rollback to the staged commit remains supported.
The shim snapshots the fetched commit once; the hook and its default-owned companions use that same immutable source. Publication uses its own committed runtime and does not require staging the installed shims first.
Publication materializes the same family in its temporary hook directory and passes that runtime only to that one Git invocation.
Publication does not change installed shims, installed runtime references, or the live fetched hook-source ref to select prepared tools.
Publication extends a safe prior head and checks the entire divergence with rename detection disabled. Its real Git merge tree must equal the current default with exact owned hook blobs, executable modes and retirements; conflicts or combined noncanonical content refuse. Readiness binds that prediction to the live `baseRef.target.oid`, PR head, hosted merge object and final matching-head request. GitHub's cached `baseRefOid` retained an older base in 21 rollout PRs despite current merge parents; it cannot establish the live target. Merging default into every publication head instead puts unrelated landed Rust changes into its real push range: Apollo and Helios exceeded the unchanged 600-second gate during the #588 rollout. Exact landing-tree comparison preserves those changes without altering the configured push range or gates. A base movement invalidates the prediction.
A missing, mixed, or incomplete runner family fails closed; setup never occurs inside the supervised push.
Hook cache writers prepare verified bytes privately, then hold the same native OS blob lock across revalidation and publication. A completed matching publication is reused; cache directories refuse without deletion. Kernel lock release covers normal exit and caller death.
One 600-second process-tree deadline covers every pushed ref, helper, ref guard, interpreter probe, cache cleanup, archive, and gate stage; timeout identifies the active stage and bounded final log bytes.

### Source-identity invariant and records

An artifact is accepted only after one successful leased run proves that its package source, recorded external inputs, resolved dependency shape, build dimensions, and named artifact bytes match one atomic record and remain stable at final verification.
Source-root paths and revisions never partition lease or record keys for overlapping artifacts: equivalent exports reuse, while different content contends and rebuilds.
`atlas_build_records.py` owns record format, `atlas_build_inputs.py` dimensions and dependency data, and `atlas_build_identity.py` the run, clean, and lease protocol; operation-family modules under References own their stated parts.
Record version 7 stores one record under `target/.atlas/source-identity` per shared target, package, profile, target, features, toolchain, environment, Cargo configuration, dependency closure, stable command key, and complete multi-package selection.
Every package selected in one Cargo invocation participates because feature unification can change all selected artifacts; one gate step issues one command with every `-p`, reads metadata once, holds the union of leases, cleans one union, and keeps one record per package under command key `atlas-pre-push` without a package suffix.
Older, missing, malformed, or unsupported records mismatch; versions 1–6 are stale. Records are atomic and contain diagnostic root and revision, dirty state, path-package identities and inputs, resolved closure and dimensions, and actual artifact hashes.
Revision remains diagnostic and guards declared-artifact runs but is absent from record paths and lease keys. Workspace path sources use workspace-relative identity.

Each path package is identified by files in its own directory, never its whole repository: tracked `HEAD` entries plus its share of tracked, untracked, and ignored working-tree changes, assigned to the deepest containing path-package directory.
The repository revision and tree digest remain for diagnostics, lease ownership, the mid-build guard, and declared-artifact runs. Target output is excluded; an overlay lock rewrite is excluded only after pushed-lock validation and restoration.
`inputs` records files outside the package named by rustc dep-info, build-script dep-info, or `rerun-if-changed`, excluding target, Cargo home, and toolchain; directories are hashed whole.
Inputs are rehashed every run under leases. An unreadable path or path outside every known tree is `unverified`, forcing that package's next clean.

Complete Cargo metadata supplies normal, build, and development edges; manifests after workspace inheritance, features, targets, kinds, editions, dependency edges, workspace manifest, and path/Git/registry content identities form the snapshot shape.
The overlay lockfile is not hashed because resolved package identities, versions, and revisions are recorded.
Package-source digests use a persistent stat-keyed cache over path, size, modification time, and symlink-target stat; a value is stored only when the fingerprint is unchanged across the read.
One snapshot memoizes each package or repository root, while every later snapshot performs fresh stat checks.

The environment digest covers Cargo profile/build/target/unstable/host/alias namespaces; Cargo, encoded Rust flags, incremental mode, compiler/bootstrap, wrappers, Rust flags, `__CARGO_DEFAULT_LIB_METADATA`; and a leading `env NAME=VALUE` overlay.
`CARGO_TARGET_DIR` is already the canonical target dimension. Rustdoc-only variables are excluded so Clippy, Nextest, and Rustdoc share one record; Cargo's doc-unit fingerprints force Rustdoc freshness and the run adopts the resulting fingerprint bytes.
The configuration digest covers both config filenames from execution root to filesystem root, Cargo home, explicit file or inline `--config`, and recursively cycle-guarded include lists of strings or `{ path, optional }` tables. Non-list includes are not traversed; Cargo remains responsible for rejecting them.
Relative config paths resolve against Cargo's execution root; framing uses directory depth and filename, not export-specific absolute paths. UTF-8 BOM is removed before Python's `tomllib` parses configuration. Unsupported TOML syntax and read failures are source-identity failures and cannot create a record.

### Artifacts, cleaning, and leases

Managed artifacts stay inside the shared target and belong to exact Cargo target names, never prefixes. A source path or artifact outside the shared target is rejected before any clean. Stable acceptance requires two reads with unchanged size and modification time within the run deadline.
A matching record hashes only its named artifacts; exclusive rebuilds rediscover names and remove retired ones. Changed, unreadable, or unsettled files are unverified and force a later clean.
An artifact-only mismatch cleans its owners. A shape or dimension change cleans every path package; otherwise source/input movement cleans only affected path packages and exact recorded-file owners, while unattributable movement cleans every path package.
One `cargo clean` receives the union plus profile and target. Registry packages are never cleaned.
Git packages use build-directory stamps keyed by package/source identity, profile, and target. A building sentinel precedes clean and Cargo; only command success plus a stable final snapshot writes the content digest.
A failed or killed command leaves a stale sentinel. Unstamped external Git artifacts remain trusted; a stale stamp is cleaned even under a matching or sibling record, including after an opaque custom clean.
Path packages carry a writer mark, `.atlas/source-identity/writers/<package>.json`, written under the run's exclusive lease: `cleaning` before a clean, `building` for every package the command writes once the clean has returned, `complete` after the records land. The mark names a run identity: the digest of the source content, build dimensions and every selected package's dependency digest, excluding checkout path. A mismatched record cleans as above, except that a package still marked `building` with this run's identity is held exclusive and rediscovered but not cleaned: a killed run's rebuilt artifacts came from the same source. While the command runs the identity process refreshes each `building` mark's heartbeat every 5 seconds, and a rerun resumes a package only if none of its `deps`, `.fingerprint` or `build` entries (matched by package name and hash suffix) is newer than that heartbeat: a lease-less peer's later write, and the killed run's own last interval, clean. Cargo does not repair a peer's write: with unchanged source mtimes it reported `Fresh` over artifacts built from other source (probe: one fingerprint directory, rerun printed the peer's output), and `.d` files cannot tell writers apart. Any other identity, a `cleaning` or `complete` mark, and a missing or unreadable mark clean as before; a stale Git stamp cleans regardless. Marks are derived state; the supervisor deadline, lease semantics and one command per phase are unchanged.

Each `(package name, canonical target directory)` has one lease; revision and target triple are excluded because revisions share artifact names and cross-target builds share host artifacts. Linked worktrees resolve the Git common directory.
Cross-platform shared/exclusive byte-range locks make the operating-system lock authoritative; owner text and expiry are diagnostic, only an exclusive holder writes them, and unlocked malformed state is reclaimable.
Queue tickets carry monotonic arrival, mode, and run ID. Exclusive requests wait behind earlier live requests; shared requests wait behind earlier exclusive requests.
A run acquires every lease or none, holds no lock while waiting, preserves queue position, and shares one bounded wait deadline. Claims and wait/hold evidence rotate in `claims.jsonl` at 1 MiB with one prior file.
A live owner causes a bounded refusal naming owner and revision, with no clean or write. Recorded expiry never overrides a live operating-system lock.

Each commanded package starts exclusive and closure dependencies shared. An exact record match keeps that shape; a mismatch releases all leases, reacquires the complete set exclusive, rechecks, and cleans only if still stale.
An equivalent sibling-command record may establish reuse. Before Cargo, a verified record lets unchanged, uncleaned non-root packages downgrade in place to shared without losing queue position.
Full/custom clean and declared-artifact runs retain exclusive leases; a failed downgrade releases everything and fails closed.
Windows downgrades with an overlapping `LockFileEx` shared lock before releasing exclusive; POSIX converts `flock` under the original queue ticket once and fails closed if a racer takes the lock.
Leases remain held through Cargo and final source, input, dependency, and artifact verification. Shared dependencies are checked only by record-named files, so new Cargo variants beside them do not mismatch.
After Cargo, named dependency files are rehashed until two reads settle; unreadable or unstable results are never accepted. Command failure preserves the prior successful record and releases leases.

### Build entry points and Cargo applicability

Pre-push judges each non-deletion pushed commit, not the working tree, through `read-tree -u --reset` in the member object store with long paths enabled, producing a symlink-preserving repository checkout at one short reusable path outside the development overlay; interruption releases its claim and leaves the checkout for reuse.
One sequence covers all selected packages and holds leases through warning-denied Clippy, Nextest, Rustdoc, and final identity verification, all with the committed lock.
`workspace.metadata.atlas.documentation-phase` is either `"pre-push"` (default) or `"pre-merge"`. The latter is valid only when required CI documents the candidate and moves only Rustdoc to `pre-push documentation <candidate> [<base>]`, using the same hook, export, selection, target, leases, and final read; required CI remains merge authority.
No record substitutes for executing documentation. Other build entry points reuse the same identity modules and format.

Atlas has no root Cargo manifest and fabricates none. `<meta>` carries revision and baseline without a repository; changed paths map to the nearest real nested manifest.
Cargo owners are `tools/checkout-path-dependencies`, `tools/criterion-regression`, `tools/gitlink-coherence`, and `tools/version-guard`; `tools/_template/template-Cargo.toml` is excluded.
Selected owners run bounded locked metadata and identity around fmt, Clippy, Nextest, and the applicable Rustdoc phase. Cargo is inapplicable only after content gates pass and selection finds no owner.
Missing, removed, unreadable, or malformed manifests/locks and ownership, metadata, or stage errors fail closed. Meta adds no relative `.githooks` switch, skip, or bypass.
Provider changes require all 28 executable member hook copies before pin advance; versions and releases remain unchanged.

## Known limits

- Resume loses up to one heartbeat interval of the killed run's output. A peer write that preserves file mtimes at or before the heartbeat is invisible; a completed run's mark never resumes, so rewrites after completion still clean.
- Untracked proc-macro/build-script reads are absent from `inputs`; another-repository inputs outside every package are guarded only by the post-command snapshot; excluded non-member path packages may clean once per changed export path.
- Alias-expanded `--config` paths are unseen unless otherwise reached. Unknown Cargo/TOML 1.1 grammar fails closed rather than being parsed.
- `[env]` values, build-script `rustc-env`, and wrapper exports are not decomposed; config-file changes remain covered. A stat-preserving package-source edit can evade the persistent cache.
- A Git artifact built outside this checker from other bytes may be reused when unstamped; stamps cover one build directory and package directory only. Registry artifacts are not cleaned.
- A matched Git build can miss a source edit made and reverted during its command (`ATLAS-IDENTITY-MIDRUN-GIT-EDIT`). Cargo fingerprints remain part of Rustdoc and external-artifact reuse.
- During mixed-version rollout an old sequential lease holder can block the all-or-none protocol until the bounded deadline; fair all-or-none acquisition can also form an idle convoy.

## Consequences

Equivalent exports and worktrees reuse exact-input artifacts in one target. Changed inputs rebuild the narrowest sound package set; ambiguous ownership fails closed and broadens cleaning.
Concurrent roots cannot silently clean or overwrite managed artifacts. Records, stamps, and digest caches are derived state, so deletion causes conservative rebuild rather than acceptance.
Hashing, metadata, queueing, and lease costs remain observable through claim histories and stage timings.

## Alternatives rejected

- Progressive per-stage records, or recording after a partial command, either split a phase into several commands, which lets a peer replace artifacts between them, or record artifacts Cargo has not finished writing. A mark written before the command and honored only for an identical identity keeps one command per phase and records nothing unverified.
- Raising the 600-second deadline or skipping the clean after any kill hides the cold-build cost or trusts artifacts of any writer; the mark is bound to one identity and replaced by every other writer.
- Working-tree `.githooks`, hand-copied member hooks, or changing live installed refs let the candidate replace its judge or duplicate policy; immutable fetched tooling plus invocation-local prepared selection preserves the trust boundary.
- Per-source targets fork the cache; manual cleaning has no ownership; Cargo fingerprint JSON and missing `.fingerprint` directories are not stable identity APIs.
- Whole-target/closure cleaning, repository-name filters, cleaning every path package on any root change, and record-local snapshot narrowing either discard unrelated reuse or miss feature, dependency-kind, edition, profile, and manifest-driven variant renames.
- Source-root, revision, or target-triple lease keys permit overlapping host artifacts to race. `HEAD:<dir>` cannot identify a root package without absorbing members; exact package files and targets avoid both errors.
- Sequential lease acquisition and in-place upgrades can deadlock; surrendering queue position can starve writers; strict global FIFO delays nonconflicting runs. All-or-none per-scope fairness is the bounded tradeoff.
- Longer waits only delay refusal. Holding every dependency exclusive serializes safe readers; releasing and reacquiring during downgrade lets a queued writer clean between this run's clean and command.
- Carrying pre-command artifact digests records bytes Cargo may have rewritten. Exclusive discovery for every shared dependency recreates serialization; only named-file settling plus post-command rehash is sound.
- Rehashing every package dominated snapshots; a persistent cache without fresh stat checks missed changes. Stable stat-keyed caching plus per-snapshot memoization retains both bounds.
- `git archive | tar`, a new export path per push, an unrefreshed export, and repository-prefix artifact ownership failed symlinks, partial-clone/path bounds, reuse, dirty-export detection, or exact attribution; the reusable `read-tree` checkout and exact targets replace them.

## Evidence and verification

The design responds to measured failures: a 405-second Rustdoc phase; 36 identity runs for one 12-package step and a 00:17–01:53 gate; four 900-second lease refusals; a 35-package clean with 34 unchanged Git packages; dependency snapshots over 25 minutes reduced from 71 seconds warm to 5.4 seconds; repeated 2.5-minute clean walks; 13 partial clones, 260-character path failures, a 1.5 GB interrupted export, and live-expiry/35-hour stale-lease failures.
Evidence identifiers remain `ATLAS-IDENTITY-MEMBER-SCOPE`, `ATLAS-GATE-STEP-BATCH`, `ATLAS-BUILD-IDENTITY-SPLIT`, `ATLAS-GATE-LEASE-HOLD-001`, `ATLAS-IDENTITY-NARROW-ADDED-DEPS`, `ATLAS-IDENTITY-MIDRUN-GIT-EDIT`, and `ryancinsight/atlas#418`.
Real-Cargo regression cases cover exact reuse across exports; package-local and external inputs; dirty/ignored/final-mutated source; shape, feature, profile, manifest, Git-stamp, sentinel, custom-clean, artifact-retirement, and registry behavior; multi-package batching and failure; settled post-command hashes; and repeat pushes that clean nothing after the first.
Lease tests cover shared readers, dependency rewrites, all-or-none fairness, owner diagnostics, expiry, malformed recovery, exclusive retake, downgrade queue position, sibling records, deadlines, and dead owners. Hook tests cover pushed-revision export, committed locks, owner changes, documentation phases, prepared tools, runner bootstrap, and refusal paths.
The configured focused identity, full scripts, pre-push, conformance, architecture/ARCH-008, and pin-drift suites are merge gates; pin readiness also requires the exact combined candidate's normal push, hosted checks, and independent acceptance recorded by the driver PR.

## References

- [PR #277](https://github.com/ryancinsight/atlas/pull/277); [PR #295](https://github.com/ryancinsight/atlas/pull/295); [PR #296](https://github.com/ryancinsight/atlas/pull/296); [PR #299](https://github.com/ryancinsight/atlas/pull/299)
- [records](../../scripts/atlas_build_records.py); [check](../../scripts/atlas_build_check.py); [inputs](../../scripts/atlas_build_inputs.py); [identity](../../scripts/atlas_build_identity.py); [stale packages](../../scripts/atlas_build_stale_packages.py); [stamps](../../scripts/atlas_build_stamps.py); [writer marks](../../scripts/atlas_build_writers.py); [snapshot](../../scripts/atlas_build_snapshot.py)
- [lease](../../scripts/atlas_build_lease.py); [lock](../../scripts/atlas_build_lock.py); [queue](../../scripts/atlas_build_queue.py); [source](../../scripts/atlas_build_source.py); [artifacts](../../scripts/atlas_build_artifacts.py)
- [package source](../../scripts/atlas_build_package_source.py); [package identity](../../scripts/atlas_build_package_identity.py); [dep-info](../../scripts/atlas_build_dep_info.py); [pre-push hook](../../scripts/git-hooks/pre-push)
- [identity tests](../../scripts/tests/test_atlas_build_identity.py); [pre-push tests](../../scripts/tests/test_atlas_pre_push_gate.py); [hook publisher tests](../../scripts/tests/test_atlas_hook_publisher.py); [Apollo ADR 0051](../../repos/apollo/docs/adr/0051-composite-phase-schedules.md)
