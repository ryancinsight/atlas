<a id="atlas-version-guard-001"></a>
## ATLAS-VERSION-GUARD-001 — Manifest-version guard and stack coherence check [patch] — in-progress (sub-delivery 1 done)

- **Sub-delivery 3 (coherence) peer-held 2026-08-07.** A live peer is
  building the offline stack-coherence scan in the same tool: new
  `tools/version-guard/src/coherence.rs` (`CoherenceFinding`,
  `CoherenceReport`, `scan_atlas` reading `.gitmodules` + checked-in
  manifests, no Cargo/registry), wired into `lib.rs`/`main.rs`/`error.rs`
  as a `coherence --atlas-root` subcommand. Working-tree changes only,
  uncommitted as of this record; the tree compiles and 52 tests pass
  (including `coherence::tests::injected_backward_fixture_is_reported`).
  Builds on the committed `a92a3c6` base. **Do not touch**
  `tools/version-guard/src/coherence.rs` or the other version-guard files
  while the peer is mid-edit; claim the sub-delivery-3 closure only after
  the peer commits or the edit goes stale.
- **Fail-closed intent validation committed 2026-08-07** as `a92a3c6`
  (`fix(version-guard): Fail closed on declared release with no forward
  movement`). The slice was previously recorded delivered but sat stranded
  uncommitted at the atlas root; the 2026-08-07 session landed it with the
  sibling tooling slices. Gates re-verified at commit time: 48 lib + 3 bin
  tests pass, `cargo clippy --all-targets -- -D warnings` clean.
- **Fail-closed intent validation 2026-08-06 (root tool slice).**
  `tools/version-guard` now treats a declared release/bump intent with no
  forward version movement as a defect, including an empty manifest diff or
  an identical-only reformat. The same intent-aware predicate drives the CLI
  exit code and human/JSON reports, so no alternate "clean" interpretation
  can mask a missed package release. Backward movement remains an unconditional
  defect, and undeclared forward movement remains rejected. Added regressions
  for empty and identical-only declared releases plus report parity. Scope is
  root tooling only; no provider checkout, consumer source, manifest,
  lockfile, or dependency changed.

- Policy: AGENTS.md git_discipline (version-bearing red-flag hunks) + architecture_scoping pin discipline (version metadata is sweep-triggering state). Motivating incident: `87ab265` (hermes) — a sed dep-conversion silently reverted the workspace release `0.5.0 -> 0.4.1` and internal requirements to `0.4.0`, unmentioned in its message; origin lied about versions for ~10 hours while integrators failed resolution, and coeus stacked 18 commits on the undeliverable base.
- Scope: (1) per-repo guard — CI step (and optional pre-commit hook) failing when a diff changes `version =` or first-party dependency version requirements without a declared release/bump intent (commit type `chore(release)`/`build(deps)` or an explicit footer); backward version movement always fails without the declaration; (2) stack coherence check — a meta-level check (home: tools/, sibling to criterion-regression) verifying every first-party requirement across allowlisted members resolves against the stack's current workspace versions, run in the integration sweep and on any version-touching commit; (3) wire both into member CI per repository convention.
- Acceptance: replaying `87ab265` against the guard fails it; coherence check passes on the current stack and fails on an injected backward-version fixture; guards live in committed CI/config, not agent memory.
- Sub-delivery 1 — per-member guard tool skeleton: **done 2026-07-31** at `
  c70af8b` (`fix(tools,scripts): Make version-guard build and retarget link tests`).
  `tools/version-guard/` (`atlas-version-guard`) parses both bare
  `version = "X"` lines and inline-table `dep = { ..., version = "X" }`
  entries from `git diff <range> -- '*.toml'`, pairs `+`/`-` per file by
  ordered position, classifies each as Identical / Forward / Backward, and
  flags a finding as a defect when backward (always) or forward-undeclared.
  Borrow-checker errors that surfaced in Session 32 (E0382 borrow-after-move
  of `v` in `scan_diff`; E0499 double `&mut` in `files_entry`) were
  resolved by capturing the side before the move and indexing the per-file
  slot, respectively (ownership fix, not a workaround). Live acceptance replay
  on `87ab265` produces **9 backward findings across 5 files**
  (`Cargo.toml` + `hermes-simd-core` + `hermes-simd-intrinsics` +
  `hermes-simd-types` + `hermes-simd`), exit 1. Tests 47/47 (44 lib + 3
  bin). Skeleton-scope: `[package].version` + inline-table first-party deps;
  third-party shorthand (`dep = "X.Y.Z"`) without surrounding `{...}` and
  TOML-section tracking (`[workspace.package]` vs `[package]`) deferred to
  sub-delivery 2.
- Sub-delivery 2 — CI wiring per member repo: **todo**. Wire the guard
  into each allowlisted member's CI as a step on PRs/pushes touching its
  `*.toml`; the guard runs once per repo against its own range.
- **Sub-delivery 3 — stack coherence check tool delivered 2026-08-07** in
  the root working tree (`tools/version-guard/src/coherence.rs`, with the
  `coherence --atlas-root <path> [--format human|json]` CLI subcommand).
  The scanner is offline and read-only: `.gitmodules` is the allowlist, and
  checked-in Cargo manifests are the package/version SSOT. It walks 235
  manifests, resolves `version.workspace = true`, dotted/workspace dependency
  inheritance, package aliases, multiline inline tables, and Cargo-style
  caret/tilde/comparator/wildcard requirements. It checks only path/git
  sources resolving to registered Atlas members, rejects missing member
  manifests, ambiguous package versions, unsupported prerelease/hyphen ranges,
  and malformed version components rather than reporting a false clean.
  Human and JSON reports share the same defect predicate; missing
  `--atlas-root` is an invocation error (exit 2).
- Sub-delivery 3 acceptance evidence: current Atlas scan is clean at
  **235 manifests / 215 packages / 898 first-party requirements / 0 defects**
  (human and JSON modes, exit 0); an injected backward-version fixture is
  detected; the missing-root CLI case exits 2. `cargo fmt --check`, strict
  `cargo clippy --all-targets --offline -- -D warnings`, `cargo nextest run`
  (59/59), `cargo test --doc --offline`, and `git diff --check` pass with
  ambient `RUSTC`/`RUSTDOC` overrides removed. Resolver-generated
  `Cargo.lock` patch churn was discarded; no lockfile or provider tree is
  part of this root tooling slice.
- Sub-delivery 2 — CI wiring per member repo: **todo**. Wire the guard
  into each allowlisted member's CI as a step on PRs/pushes touching its
  `*.toml`; the guard runs once per repo against its own range.

Toolchain-template drift corrected 2026-08-03 (Session 33 closure): the
peer's `1.95.0 -> 1.97.0` pin advance (ATLAS-TOOLCHAIN-COHERENCE-001
resolution) had been propagated to the three existing consumers but not to
`tools/_template/template-rust-toolchain.toml` (still `1.95.0`), so the
Session-32 version-guard skeleton copied the stale pin. Both files now
match `1.97.0`, `check-drift.sh` extended to a fourth consumer
(`tools/version-guard/`), and `template-Cargo.toml` / README consumers
list updated. `check-drift.sh` reports `4 consumers clean`.

