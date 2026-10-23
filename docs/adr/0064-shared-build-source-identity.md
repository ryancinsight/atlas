# ADR 0064: Shared build source and artifact identity

- Status: Accepted
- Date: 2026-09-24
- Class: [arch]
- Revision: 2026-10-23 - Consolidated duplicate delivery narratives into the current record-v7 contract; retained exact root exports and prepared cast-tool selection from [PR #551](https://github.com/ryancinsight/atlas/pull/551), as covered by the identity and pre-push suites.
- Driver: [Atlas PR #500](https://github.com/ryancinsight/atlas/pull/500) and [Moirai PR #596](https://github.com/ryancinsight/moirai/pull/596)
- Item: ATLAS-BUILD-SOURCE-IDENTITY, delivered by [PR #295](https://github.com/ryancinsight/atlas/pull/295), [PR #296](https://github.com/ryancinsight/atlas/pull/296), and [PR #299](https://github.com/ryancinsight/atlas/pull/299)

## Context

Atlas members share one target. Cargo fingerprints and dep-info omit the producing checkout, so different source bytes can address the same artifact. Revisions omit dirty and untracked source, branches are mutable, and Cargo's fingerprint format is internal. Concurrent roots need one protocol that prevents a clean or artifact rewrite from invalidating another build.

## Decision

### Tool source and safety boundary

Hooks extract conformance, build-identity, and cast tools from fetched Atlas default. A coordinated provider update may select one immutable Atlas commit with command-scoped `git -c atlas.preparedTools=<full-sha> push`. The value must occur once, be a full 40-character commit ID, resolve in the registered Atlas object store, and contain the complete required scripts; every failure rejects the push. `publish-hooks --source-ref` forwards its resolved source through this setting.

Secret scanning, artifact budgets, lockfile tools, and conformance baselines remain fetched-default inputs. The immutable fetched hook remains the trust root, and prepared selection is printed publicly. Provider changes update all 28 executable member copies before the pin advances; this decision changes no package version or release state.

### Record and input identity

`scripts/atlas_build_records.py` owns record version 7, `scripts/atlas_build_inputs.py` owns dimensions and dependency data, and `scripts/atlas_build_identity.py` owns the run protocol. One atomic record per package under the canonical shared target's `target/.atlas/source-identity` identifies package, profile and target triple, feature set, complete Cargo package selection, compiler and toolchain, build environment, effective Cargo configuration, dependency closure, and stable command key. It records the diagnostic source root, full Git revision, clean or dirty state, source-tree digest, resolved closure, actual artifact hashes, and external package inputs.

Versions 1 through 6 are stale; missing, malformed, unsupported, or incomplete current records fail closed. The source root is diagnostic and is never compared; workspace path sources are workspace-relative. Revision is absent from record paths and lease keys so competing revisions contend for the artifacts they share.

A path package is identified by files in its own deepest package directory, never by its repository revision. One repository `ls-tree` supplies tracked path, mode, and object identity; dirty identity uses each package's share of the raw tracked diff plus untracked and ignored source bytes and explicit deletion markers. Each file belongs to the deepest source-less metadata package containing it, so a root package does not absorb member files. The repository revision and tree digest remain diagnostic, identify lease owners, guard mid-build source stability, and decide runs of declared artifact paths.

The `inputs` field covers files outside a path package named by `deps/*.d`, build-unit dep-info, or build-script output `rerun-if-changed` entries; a watched directory is hashed whole. Own-package files, target, Cargo home, and toolchain content are excluded. Paths stay workspace-relative where rustc emits them that way and otherwise remain absolute; a path outside every owned tree or unreadable dep-info becomes `unverified`. Every run rehashes recorded inputs under lease, and a moved or unverified input makes only its package stale. Inputs are learned from the prior record rather than included in the pre-record snapshot. Record version 7 replaced repository-wide path-package identity, so earlier records receive one conservative rebuild.

Repository identity includes revision, tracked dirty changes, and untracked or ignored source bytes. Target output is excluded; an overlay-rewritten lock is excluded only after the pushed lock is checked or restored. Status, source, dependencies, inputs, and artifacts are read again for final verification.

The environment digest covers `CARGO_PROFILE_*`, `CARGO_BUILD_*`, `CARGO_TARGET_*`, `CARGO_UNSTABLE_*`, `CARGO_HOST_*`, `CARGO_ALIAS_*`, `CARGO`, `CARGO_ENCODED_RUSTFLAGS`, `CARGO_INCREMENTAL`, `__CARGO_DEFAULT_LIB_METADATA`, `RUSTC`, `RUSTC_BOOTSTRAP`, `RUSTC_WORKSPACE_WRAPPER`, `RUSTC_WRAPPER`, `RUSTFLAGS`, and leading `env NAME=VALUE` assignments. `CARGO_TARGET_DIR` is excluded because canonical target identity already records it. Rustdoc-only variables, including their `CARGO_BUILD_*` spellings, are excluded so clippy, tests, and rustdoc use the same command key and record. Cargo's doc-unit fingerprint tracks them, and the run adopts newly written rustdoc fingerprint bytes. A required identity command failure cannot create a verified record.

The configuration digest covers `.cargo/config` and `.cargo/config.toml` at every level from the command root to the filesystem root, both Cargo-home names, and explicit file or inline `--config` arguments. Cargo prefers the extensionless file when both names exist, but identity hashes both. Cargo home comes from the command's merged environment, and relative arguments resolve from Cargo's command directory. Recursive include lists of strings or `{ path, optional }` tables are cycle-guarded; a bare-string include remains invalid, and optional missing files are skipped. Entries are framed by depth and name instead of machine-specific export paths. UTF-8 BOMs and the known Cargo parser divergences for trailing inline-table commas, multiline inline tables, `\e`, and `\xHH` are accepted. Other parse failures identify the source and fail closed as source-identity failures.

Complete Cargo metadata supplies normal, build, and development edges; manifests, features, target expressions and kinds, editions, targets, dependency edges, and the workspace manifest. Path, Git, and registry sources receive content identities. The overlay-rewritten lock is not hashed because the resolved package identities and revisions are recorded. Snapshot shape comprises package names, versions, features, sources, resolved manifests, dependency edges, and the workspace manifest, excluding source-content fields.

Package-source helpers cache digests under `.atlas/source-identity/package-source`, keyed by path, size, modification time, and symlink-target stat data. They write only after that fingerprint is stable before and after reading. A dependency snapshot memoizes each distinct repository or package root once; the next snapshot performs fresh fingerprint checks.

### Artifacts, cleaning, and leases

Managed artifacts must remain inside the shared target and belong to exact Cargo target names, never name prefixes. Shared artifacts settle after two equal reads with unchanged size and modification time inside the bounded deadline. Successful but unsettled reads are unverified; if no read succeeds, the pre-command verified digest is preserved. Exclusive rebuilds rediscover names and discard retired ones. Dependencies and inputs are rehashed after Cargo because the command may rewrite them in place.

An artifact-only mismatch cleans its owners. A dimension or snapshot-shape change and a missing record clean every path package because the renamed variants cannot be inferred. Otherwise content changes clean only path packages whose identity or input moved, or which own a changed recorded artifact; ambiguous ownership cleans every path package. Registry packages are never cleaned. One `cargo clean` receives the union with the build directory's profile and target dimensions.

Git packages use stamps keyed by build directory, package and source identity, profile, and target. A building sentinel is written before cleaning and Cargo; only command success plus a stable final snapshot replaces it with the content digest. A failed or killed run therefore remains stale even beside a matching or sibling record or after a custom clean. An unstamped Git package is trusted as an artifact from a build outside this checker, and registry packages are never cleaned. Records name path-package artifacts; Git stamps own Git provenance.

Each `(package name, target directory)` has one lease; revision and target triple are omitted because revisions share names and cross targets share host artifacts. Linked worktrees resolve the primary target through the Git common directory. Cross-platform shared or exclusive byte-range locks reserve byte 0 for the operating-system lock and later bytes for owner diagnostics. The lock owns liveness, only an exclusive holder writes owner state, expiry is diagnostic, and unlocked malformed state is reclaimable.

Queue tickets carry monotonic arrival, mode, and shared run ID, and every scope orders them identically. Exclusive claims wait behind earlier live tickets; shared claims wait behind earlier exclusive tickets. A run claims all phase leases or none, holds no lock while waiting, retains tickets at every scope, and shares one deadline across both acquisition phases. `claims.jsonl` records order, scopes, modes, waits, holds, blockers, and phases and rotates at 1 MiB with one prior file.

A run first claims its built package exclusively and closure dependencies shared. On a mismatch it releases the leases and reclaims cumulative clean targets exclusively, retaining unaffected dependencies shared. Rechecking may widen the clean set before acquisition repeats; it never upgrades in place. An equivalent sibling command record may establish reuse. Before Cargo, scopes named by a verified record that were not cleaned and are not the built package downgrade in place to shared without losing queue position; full or custom cleaning and declared artifact paths remain exclusive.

Windows conversion overlays a shared lock before releasing the exclusive range. POSIX conversion is guarded by the original queue position; a competing legacy or queued holder makes the single conversion attempt fail closed with no retry. Releasing and reacquiring after cleaning is forbidden because another writer could clean between this run's clean and command.

A live owner wait uses backoff and is bounded by `--lease-wait-seconds` across every lease and both phases; reported expiry never overrides a live lock. Conflict identifies the owner and changes nothing. Command failure preserves the previous successful record and releases every lease. Leases remain held through Cargo and final source, dependency, input, and artifact verification. Shared scopes compare only artifact names from their own or a sibling record; they never discover peer variants.

### Build entry points and meta-root applicability

Pre-push judges every non-deletion pushed commit, not the working tree. `read-tree -u --reset` checks it out through the member's object store into one lock-claimed, reusable short repository outside the development overlay with `core.longpaths`; this supports partial clones, preserves symlinks, index stat data, and unchanged file times, and cleans interrupted exports. Each clippy, nextest, or rustdoc step runs one Cargo command naming every gated package, reads metadata once, holds the union of package leases, and keeps one record per package under command key `atlas-pre-push`. Every step uses the committed lock and final identity verification. Other build entry points reuse the same modules and record format.

Root exports retain their tracked Cargo configuration unchanged. Cargo runs from a mirrored ancestor chain outside the export, where development `[patch]` tables are removed while configuration precedence and original relative-path roots remain intact. Each independent tool workspace receives its own rebuilt mirror. Candidate and base checks select their own manifest, configuration, and toolchain; identity records the compiler selected at the actual Cargo command directory.

Atlas fabricates no root Cargo manifest. Secret, artifact-budget, lock, and baseline checks use fetched default; conformance, build identity, and cast checks may use the selected prepared scripts. `<meta>` carries revision and baseline without pretending to be a repository. Changed paths map to the nearest real nested manifest.

A root config edit adds no global owners only when both committed entries are regular files, parse without `include`, and have identical types and values after removing top-level `patch`. That table is absent from exported Cargo configuration. Added, deleted, unreadable, malformed, or symlink configs retain global selection or fail closed; other `.cargo/`, toolchain, and nextest inputs remain global.

Cargo owners are `tools/checkout-path-dependencies`, `tools/criterion-regression`, `tools/gitlink-coherence`, and `tools/version-guard`; `tools/_template/template-Cargo.toml` is excluded. Each selected owner runs bounded locked metadata, fmt, clippy, nextest, rustdoc, and final identity checks against its actual manifest, export, lock, and shared target. Cargo is inapplicable only after content gates pass and owner selection finds none. Missing, malformed, or unreadable selected inputs and every ownership, metadata, or stage error fail closed. Meta adds no relative `.githooks` switch, skip, or bypass.

The shared identity modules are the only provenance policy surface and compose with the conformance guard; member hooks do not copy or reimplement it. Artifact hashes are recorded after the command. Cargo fingerprint JSON is not treated as a public schema, and a missing `.fingerprint` directory never proves source identity.

## Failure modes

- A source or artifact path outside the shared target is rejected before cleaning.
- Implicit artifact discovery requires the complete metadata graph; unresolved or name-ambiguous ownership fails closed, and targets match exact names only.
- A build-affecting environment, compiler, toolchain, or configuration change moves record scope.
- A live owner reports its owner and revision without destructive action; failed commands preserve the last successful record and release leases.
- Missing or malformed identity state causes conservative cleaning or refusal, never acceptance of unknown artifacts.

## Known limits

- Files read without dep-info or `rerun-if-changed` are outside `inputs`; an external-repository input is guarded only by the post-command hash. An excluded non-member path package can clean once per new export when absolute dep-info paths go stale.
- Alias-expanded config paths are not followed unless the executed arguments or ordinary config search also reaches them. Unrecognized TOML 1.1 syntax fails closed rather than being interpreted.
- Build-script `rustc-env`, wrapper exports, and other non-ambient environment mutation are not decomposed. Config `[env]` remains covered as configuration content.
- A package-source edit that preserves size and modification time can evade the persistent stat cache.
- External unstamped Git artifacts may be reused; the stamp covers one build directory, and registry artifacts are not cleaned. A matched Git source edited, built, and restored during one command can also escape the final snapshot (`ATLAS-IDENTITY-MIDRUN-GIT-EDIT`).
- Cargo fingerprints remain part of rustdoc and external-artifact reuse. During mixed-version rollout, an old sequential lease holder can block the all-or-none protocol until the bounded deadline.

## Consequences

Equivalent exports and worktrees reuse exact-input artifacts. Changed inputs rebuild the narrowest sound package set; ambiguous ownership fails closed and broadens cleaning. Concurrent roots cannot silently clean or overwrite managed artifacts. Record loss causes conservative rebuilding; source-cache loss causes rehashing and need not rebuild unchanged content. Missing Git stamps retain the external-build trust limitation stated above. One shared target remains, with hashing, metadata, and lease cost exposed by claim histories and stage timings.

## Alternatives rejected

- Legacy `.githooks` lets the pushed tip replace its gate and duplicates policy; immutable fetched tooling remains the trust boundary.
- Per-source targets fork the cache, while manual cleaning has no ownership. Cargo fingerprint JSON is not a stable interface. Whole-target or whole-closure cleaning discards unrelated reuse, and repository-name filters miss shared dependencies.
- Sequential lease acquisition permits deadlock. Relinquishing partial-claim queue position permits reader starvation; strict global first-in-first-out delays nonconflicting runs without strengthening correctness.
- A longer wait only delays refusal. Holding every dependency exclusively serializes safe readers, so unchanged non-root scopes downgrade to shared.
- Rehashing every package for every closure dominated dependency snapshots. The stable stat cache and per-snapshot memoization retain fresh checks without that repeated work; a persistent cache that skipped fresh fingerprint checks was rejected.

## Overturning evidence

Replace this protocol if Cargo supplies a stable checkout-aware artifact identity and locking contract that covers the source, configuration, compiler, and dependencies recorded here. Revise an individual rule if the regression suite demonstrates stale reuse under an exact match, deadlock or starvation under all-or-none leasing, or an input Cargo consumes outside the recorded and explicitly bounded sources.

## Verification

Focused identity tests cover record compatibility; dirty, ignored, exported, and final-mutated source; package and external-input identity; environment and configuration inputs and failures; compiler and toolchain selection; dependency shape, manifests, features, profiles, artifacts, stamps, caches, and cleaning; and shared or exclusive claims, fairness, downgrade, deadlines, interoperability, and dead owners. Real-Cargo cases cover repeated exports, multi-package commands, ownership changes, and failure preservation.

Integrated hook tests cover pushed-revision exports, exact root configuration outside the overlay, committed locks, meta Cargo owners, prepared tool and cast-checker selection, and refusal paths. Configured identity, pre-push, conformance, architecture, and pin-drift suites remain executable gates. Pin readiness requires the exact combined candidate's normal push, hosted checks, and independent acceptance; the driver PR records those results.

## References

- [PR #277](https://github.com/ryancinsight/atlas/pull/277)
- [record and identity modules](../../scripts/atlas_build_identity.py): `atlas_build_records.py`, `atlas_build_inputs.py`, `atlas_build_check.py`, `atlas_build_stale_packages.py`, `atlas_build_stamps.py`, and `atlas_build_snapshot.py`
- [source and artifact modules](../../scripts/atlas_build_source.py): `atlas_build_artifacts.py`, `atlas_build_package_source.py`, `atlas_build_package_identity.py`, and `atlas_build_dep_info.py`
- [lease module](../../scripts/atlas_build_lease.py): `atlas_build_lock.py` and `atlas_build_queue.py`
- [pre-push hook](../../scripts/git-hooks/pre-push), [identity tests](../../scripts/tests/test_atlas_build_identity.py), and [pre-push tests](../../scripts/tests/test_atlas_pre_push_gate.py)
