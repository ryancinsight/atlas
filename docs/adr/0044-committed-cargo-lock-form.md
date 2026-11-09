# ADR 0044: Committed Cargo.lock is the standalone form

- Status: Accepted
- Date: 2026-08-17
- Revision: 2026-11-09 - Compact the decision; bind complete lock checks to
  immutable input bytes and the shared process owner.
- Driver: [PR #616](https://github.com/ryancinsight/atlas/pull/616),
  [PR #588](https://github.com/ryancinsight/atlas/pull/588), and
  [PR #622](https://github.com/ryancinsight/atlas/pull/622).

## Context

The development overlay redirects first-party Git dependencies to local paths.
Cargo can then remove their Git sources from working locks and add
`[[patch.unused]]` entries. Those locks describe the overlay, while standalone
consumers and CI resolve without it. Local build success cannot establish
standalone lock correctness.

A repository can contain several independent lock owners, including excluded
fuzz workspaces and tools. Checking only its root manifest misses those inputs.
A shared checkout can also hold another branch or overlay-derived lock changes,
so the pushed commit, rather than the live tree, is the input being certified.

## Decision

Commit the standalone lock form throughout the stack:

1. A package resolved through a Git dependency retains its Git source.
2. No standalone lock contains `[[patch.unused]]` overlay residue.

The rule matches actual lock packages against resolved manifest declarations;
counting Git source lines alone is insufficient. Unused workspace dependencies
need not appear in a lock, and packages defined within the workspace are local.
Dependency renames, inherited declarations, target/build/development edges, and
local dependency closure participate in owner classification.

The checker retains full-root fixture classification for owners whose active
path dependencies require files outside the repository. It reports each exempt
lock explicitly. Such fixtures receive no standalone Cargo resolution evidence.
Missing sibling metadata, unparseable inputs, and candidate directory or metadata
links fail closed. Immutable candidate scans include committed pairs beneath
normally ignored directory names.

### Input and process ownership

`scripts/lockfile.py` owns the rule, staged and committed sweeps, standalone
resolution, and regeneration. Hooks do not maintain independent predicates.

The staged check reads the index and performs no Cargo resolution. The committed
sweep reads Git objects and establishes lock form. Push and CI checks additionally
run native `cargo metadata --locked` for every selected standalone lock owner.

`--check --check-tree` selects an immutable candidate export. `--tree-source`
binds its metadata to an actual commit object, with replacement objects ignored.
Cargo inputs decode as strict UTF-8; comparison permits CRLF/LF checkout
normalization only. It neither replaces invalid bytes nor normalizes bare CR.
An export cannot omit or alter committed metadata through archive attributes,
text conversion, symlinks, or an unrelated working tree.

Cargo runs outside the development overlay and uses the shared target. The
canonical process-tree runner bounds each command and owns its descendants,
including caller-death cleanup. Timeout diagnostics preserve cleanup failures.
Hook exporters materialize `lockfile.py`, `process_tree.py`, `windows_process.py`,
and `darwin_process.py` from the same trusted revision.

### Repair

Treat a working lock produced solely by the overlay as derived state. The restore
command replaces only a proven pure overlay rewrite; it refuses unique changes.
Regeneration uses `cargo metadata`, rather than `cargo generate-lockfile`, to
reuse valid locked choices while repairing resolution. Review the resulting
standalone diff and rerun the checker before committing it.

## Rejected alternatives

- Commit the stripped form: it depends on a development-only overlay.
- Stop committing locks: standalone builds lose their reproducible source set.
- Hide locks through per-worktree index exceptions: unverified state persists
  across branch changes and shared-tree operations.
- Rely on documentation or Git source counts: neither selects every owner nor
  distinguishes legitimate local packages from stripped Git dependencies.

## Consequences and verification

One predicate serves index, committed-tree, and filesystem inputs. Static lock
form evidence and native locked-resolution evidence remain distinct.

The hook, staged, parser, and committed-tree suites cover independent and nested
owners, fixture boundaries, inherited/renamed declarations, altered exports,
non-commit source IDs, invalid UTF-8, checkout line endings, symlinks, and process
cleanup. Native Cargo cases assert resolution results and diagnostic failures.

Overturn this decision only if standalone consumers no longer require committed
locks, or if a replacement mechanism provides the same exact-source and native
resolution evidence for every owner.
