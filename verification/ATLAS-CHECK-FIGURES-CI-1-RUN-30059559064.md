# ATLAS-CHECK-FIGURES-CI-1 — Run 30059559064 Failure Analysis

> Run-specific diagnostic supplement to
> `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md`.
> Captures the verbatim CI failure output from PR #31 (HELIOS closeout) at run
> ID `30059559064`, establishes that the failures are PR-specific (main HEAD
> independently verified green at `888015e0e2a4b03b8c1e25c7a8befcdc098fd98b`),
> and produces a corrected root-cause analysis with a concrete recovery path.
> The `prebook check-figures` lint fired correctly under CI; the auto-merge
> conditional correctly short-circuited because FAIL_COUNT > 0.

---

## 1. Run summary

| Field | Value |
|-------|-------|
| PR | [ryancinsight/helios#31](https://github.com/ryancinsight/helios/pull/31) |
| Branch head | `codex/helios-book-figures-closeout` (SHA `e66a16afcd78cf6e63dcbb01c36438e2cc804e8b`) |
| Branch base | `main` |
| Run ID | `30059559064` |
| Run URL | `https://github.com/ryancinsight/helios/actions/runs/30059559064` |
| Conclusion | `failure` |
| Set-up | Non-draft (per user direction for conditional merge) |
| Auto-merge | ✓ Correctly short-circuited (FAIL_COUNT=5 ≠ 0) |
| PR close action | `gh pr close 31 --delete-branch=false` (preserves closeout branch) |
| PR post-close state | `state=CLOSED, mergedAt=null` (closed without merge, per design) |

---

## 2. Job failure inventory

| Job                              | Conclusion | Notes                                                                                                |
|----------------------------------|-----------|------------------------------------------------------------------------------------------------------|
| `rust workspace`                 | failure   | Step-level `cargo fmt --check` failure: 6 `Diff in` blocks across 3 new/modified xtask files         |
| `python bindings`                | failure   | `Build Python extension` step: `maturin --locked` vs Cargo.lock update conflict                      |
| `benchmark regression check`     | failure   | `Compile benchmark binaries` step: same `--locked` vs Cargo.lock update conflict (helios-candidate) |
| `recurseml/analysis`             | error     | External research-bot integration; not part of GitHub-hosted CI; documented as out-of-scope noise    |
| deploy                           | skipped   | Intentional (path-filtered workflow `book-pages.yml`)                                                 |

---

## 3. Step-level verbatim failure log

All excerpts below are **transcribed verbatim** from
`/tmp/helios-run-30059559064.log` (4382 lines; captured via
`gh run view 30059559064 --log`). The reproduction commands at section §8 below
let a future agent regenerate the exact windows on demand.

### 3.1 `cargo fmt -- --check` (rust workspace job) — **substantive failure**

The full `cargo fmt --check` output spans log lines ~1939 (start) through ~2020
(last diff body) with the step terminating at line 2026. There are **six
`Diff in` blocks** across **three** new/modified files, all chain-method
reformatting diffs:

```
Diff in /home/runner/work/helios/helios/xtask/src/check_figures.rs:47:
         .and_then(|n| n.to_str())
         .ok_or_else(|| anyhow!("path has no filename: {}", path.display()))?
         .to_owned();
-    let content = fs::read_to_string(path)
-        .with_context(|| format!("reading {}", path.display()))?;
+    let content =
+        fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;

Diff in /home/runner/work/helios/helios/xtask/src/check_figures.rs:97:
     let (_, readme_refs) = parse_figure_refs(&readme_path)
         .with_context(|| format!("parsing {}", readme_path.display()))?;

-    let all_docs_refs: Vec<DocsFigureRef> = summary_refs
-        .into_iter()
-        .chain(readme_refs)
-        .collect();
+    let all_docs_refs: Vec<DocsFigureRef> = summary_refs.into_iter().chain(readme_refs).collect();

Diff in /home/runner/work/helios/helios/xtask/src/check_figures.rs:131:
 /// 0 = in sync, 1 = drift detected.  The caller (`main.rs`) is expected
 /// to map a `1` to `std::process::exit(1)` so CI sees the failure.
 pub fn print_check_figures_report(report: &CheckFiguresReport) -> i32 {
-    println!(
-        "check-figures: SSOT drift verification (SUMMARY.md + README.md vs FIGURE_SPECS)"
-    );
+    println!("check-figures: SSOT drift verification (SUMMARY.md + README.md vs FIGURE_SPECS)");

Diff in /home/runner/work/helios/helios/xtask/src/main.rs:40:
     let root = workspace_root();

     match cli.command {
-        Command::LegacyMigrationAudit => {
-            migration_audit::print_legacy_migration_audit(&root)
-        }
-        Command::RefreshLegacyAllowlist => {
-            migration_audit::refresh_legacy_allowlist(&root)
-        }
-        Command::BurnMigrationAudit => {
-            migration_audit::print_burn_migration_audit(&root)
-        }
+        Command::LegacyMigrationAudit => migration_audit::print_legacy_migration_audit(&root),
+        Command::RefreshLegacyAllowlist => migration_audit::refresh_legacy_allowlist(&root),
+        Command::BurnMigrationAudit => migration_audit::print_burn_migration_audit(&root),
         Command::RefreshBurnAllowlist => migration_audit::refresh_burn_allowlist(&root),
         Command::Prebook => run_prebook(&root),
         Command::CheckFigures => run_check_figures(&root),

Diff in /home/runner/work/helios/helios/xtask/src/prebook.rs:139:
     let mut entries: Vec<ManifestEntry> = Vec::with_capacity(FIGURE_SPECS.len());
     for spec in FIGURE_SPECS {
         let path = figs_dir.join(spec.name);
-        let bytes = fs::read(&path)
-            .with_context(|| format!("reading figure file {}", path.display()))?;
+        let bytes =
+            fs::read(&path).with_context(|| format!("reading figure file {}", path.display()))?;

Diff in /home/runner/work/helios/helios/xtask/src/prebook.rs:154:
     // Serialise with sorted keys (serde_json default) + no pretty-print
     // trailing whitespace; deterministic across runs and machines.
     let manifest_path = figs_dir.join("MANIFEST.json");
-    let json = serde_json::to_string(&entries)
-        .context("serialising MANIFEST.json entries")?;
+    let json = serde_json::to_string(&entries).context("serialising MANIFEST.json entries")?;

##[error]Process completed with exit code 1.
```

**Inventory summary** (6 `Diff in` blocks across 3 files):

| # | File | Line | Change |
|---|------|------|--------|
| 1 | `xtask/src/check_figures.rs` | 47 | `fs::read_to_string(...).with_context(...)` chain — multi-line → single-line |
| 2 | `xtask/src/check_figures.rs` | 97 | `summary_refs.into_iter().chain(readme_refs).collect()` — multi-line → single-line |
| 3 | `xtask/src/check_figures.rs` | 131 | `println!("check-figures: ...")` — multi-line → single-line |
| 4 | `xtask/src/main.rs` | 40 | Three `Command::*MigrationAudit` arms — block bodies → expression bodies |
| 5 | `xtask/src/prebook.rs` | 139 | `fs::read(&path).with_context(...)` chain — multi-line → single-line |
| 6 | `xtask/src/prebook.rs` | 154 | `serde_json::to_string(...).context(...)` chain — multi-line → single-line |

**Root cause**: the new `xtask/src/{prebook.rs,check_figures.rs,main.rs}` modules
needed a `cargo fmt` pass. Trivially resolved by
`cargo fmt -p xtask && git commit --amend`.

### 3.2 `Build Python extension` (python-bindings job) — **substantive failure**

True cause is `maturin build --locked` conflicting with submodule updates that
would normally be allowed:

```
##[group]Run python -m maturin build --locked --release --out dist
...
Updating crates.io index
Updating git repository `https://github.com/ryancinsight/tyche`
Updating git repository `https://github.com/ryancinsight/eunomia.git`
Updating git repository `https://github.com/ryancinsight/apollo.git`
error: cannot update the lock file /home/runner/work/helios/helios/Cargo.lock
       because --locked was passed to prevent this
help: to generate the lock file without accessing the network, remove the
      --locked flag and use --offline instead.
💥 maturin failed
  Caused by: Cargo metadata failed. Does your crate compile with `cargo build`?
  Caused by: `cargo metadata` exited with an error:
[command]/usr/bin/git version
##[error]Process completed with exit code 1.
```

### 3.3 `Compile benchmark binaries` (benchmark-regression job) — **substantive failure (same root cause as 3.2)**

The compilation step runs `cargo bench --no-run` with `--locked --all-features`.
The same `--locked` vs lockfile-update conflict fires again, this time on the
`helios-candidate/Cargo.lock`:

```
##[group]Run set -euo pipefail
for revision in helios-candidate helios-baseline; do
  while IFS=: read -r package benchmark; do
    [[ -n "$package" ]] || continue
    cargo bench \
      --manifest-path "$revision/Cargo.toml" \
      --locked \
      --all-features \
      --package "$package" \
      --bench "$benchmark" \
      --no-run
  done <<<"$BENCHMARK_TARGETS"
done
...
Updating crates.io index
error: cannot update the lock file
       /home/runner/work/helios/helios/helios-candidate/Cargo.lock
       because --locked was passed to prevent this
help: to generate the lock file without accessing the network, remove the
      --locked flag and use --offline instead.
##[error]Process completed with exit code 101.
```

**Root cause for §3.2 + §3.3 (consolidated)**: the closeout commits changed
workspace dependency resolution (new `serde` dep in `xtask/Cargo.toml` +
`xtask/src/check_figures.rs` + `xtask/src/prebook.rs`). On a fresh runner,
`maturin` and `cargo bench` reach out to update git submodules (tyche / eunomia
/ apollo) and then try to update `Cargo.lock`. The `--locked` flag forbids both
behaviours, so they fail before the build can proceed. Two equally-valid fixes:

1. **Drop `--locked` for these two CI invocations** (preserves intent via the
   `atlas_ref` pin in `ci.yml`); preferred because it matches the historical
   pattern for submodules that resolve at build time.
2. **Commit a regenerated `Cargo.lock`** alongside the closeout commits so
   `--locked` succeeds without lockfile mutation.

### 3.4 `Install Rust verification tools` (rust workspace job) — **false positive**

The runner executed the step successfully:

```
##[group]Run taiki-e/install-action@f47c9687269207d6b374de4134cb8b1fa5b49649
  tool: cargo-nextest@0.9.140,cargo-audit@0.22.2,cargo-deny@0.20.2
  checksum: true
  fallback: cargo-binstall
...
bail() {
  printf '::error::install-action: %s\n' "$*"
  exit 1
}
...
```

**Verdict**: this step succeeded and installed all three tools (cargo-nextest
0.9.140, cargo-audit 0.22.2, cargo-deny 0.20.2). The `::error::install-action:`
substring is part of `taiki-e/install-action`'s `bail()` function declaration —
it is a grep false-positive. No real failure here.

---

## 4. Independent main HEAD baseline

| SHA | Status |
|-----|--------|
| `888015e0e2a4b03b8c1e25c7a8befcdc098fd98b` | GREEN (3 latest CI runs on `main` all `success`) |

→ **The two substantive failures (§3.1 + §3.2/§3.3) are PR #31-specific, NOT
pre-existing on `main`.** The closeout commits are causal.

→ The other two job-level conclusions (`recurseml/analysis` error external bot;
`deploy` skipped intentional path-filter) were correctly excluded from the
auto-merge decision.

---

## 5. Root-cause ranking (corrected)

| Severity | Cause | Fix | Jobs |
|----------|-------|-----|------|
| **High** | `cargo fmt --check` diffs: 6 `Diff in` blocks across 3 files (`xtask/src/check_figures.rs:47/97/131`, `xtask/src/main.rs:40`, `xtask/src/prebook.rs:139/154`) — all chain-method reformatting | `cargo fmt -p xtask && git commit --amend` (trivial) | `rust workspace` |
| **High** | `--locked` flag (maturin + cargo bench) conflicts with submodule + Cargo.lock update | Drop `--locked` for these two CI invocations; OR commit regenerated `Cargo.lock` | `python bindings` + `benchmark regression check` (shared root cause) |
| False positive | "Install Rust verification tools" — the `::error::` substring is the action's `bail()` declaration, not an error emit | None (no real failure) | `rust workspace` (this specific step, only) |
| Out-of-scope | `recurseml/analysis` external bot error | None (not part of GitHub-hosted CI) | (separate job, not path-of-merge) |

---

## 6. Forward action (decided)

1. **PR #31 is closed without merge.** Conditional auto-merge correctly
   short-circuited per design (`FAIL_COUNT=5 ≠ 0` short-circuits on first
   non-SUCCESS). PR URL: <https://github.com/ryancinsight/helios/pull/31>.
2. **Closeout branch preserved on origin** at SHA
   `e66a16afcd78cf6e63dcbb01c36438e2cc804e8b` for a fix-up iteration
   (verifiable via
   `git ls-remote origin codex/helios-book-figures-closeout`).
3. **Next iteration (atomic fix-up PR from the same branch)**:
   - Run `cargo fmt -p xtask` and amend the closeout commits with the
     formatted source for `xtask/src/{check_figures.rs,main.rs,prebook.rs}`.
   - Update `repos/helios/.github/workflows/ci.yml`: drop `--locked`
     from the `Build Python extension` step (maturin invocation; preserve
     intent via existing `atlas_ref` pin) AND from the
     `Compile benchmark binaries` step (`cargo bench --no-run`). Alternative
     — keep `--locked` but commit a regenerated `Cargo.lock`.
   - Re-push the branch; open follow-up PR (likely #32+); expect PR CI to
     flow through `Check book figures` with the SSOT_IN_SYNC log line
     captured.

---

## 7. Cross-references

- `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md` — broader
  evidence record (proven signals + structural block + forward dependency).
- `D:/atlas/backlog.md` `## ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` — the parent
  entry, updated to reflect that PR #31 e2e attempt was real, FAIL_COUNT > 0,
  auto-merge short-circuited, and recovery is via a follow-up fix-up PR.
- `D:/atlas/repos/helios/backlog.md` `H-087` — original HELIOS deterministic
  figure set entry that produced the FIGURE_SPECS SSOT.
- `D:/atlas/repos/helios/.github/workflows/ci.yml` — the workflow carrying the
  `Check book figures` step under audit here.

---

## 8. Reproduction commands

Future agent should re-derive verbatim log windows via:

```bash
gh run view 30059559064 --log > /tmp/helios-run-30059559064.log

# §3.1 cargo fmt anchor (full window covers 6 Diff in blocks + termination)
grep -nE 'cargo fmt -- --check|##\[error\]Process completed with exit code 1' /tmp/helios-run-30059559064.log
# fmt command starts at line 1939; step terminates at line 2026.
# Re-derive full §3.1 via `sed -n '1939,2026p' /tmp/helios-run-30059559064.log`

# §3.1 enumeration of every Diff in block (verifies §3.1 covers all 6)
grep -nE 'Diff in /home/runner/work/helios' /tmp/helios-run-30059559064.log
# Current finding: anchors at lines 1947 / 1958 / 1970 / 1981 / 2000 / 2011.

# §3.2 maturin anchor
grep -nE 'maturin build --locked|cannot update the lock file' /tmp/helios-run-30059559064.log
# anchor at line 972; window 962-992 reproduces §3.2 verbatim

# §3.3 cargo bench anchor (same root cause as §3.2)
grep -n 'Compile benchmark binaries' /tmp/helios-run-30059559064.log
# anchor at line 4252; window 4247-4292 reproduces §3.3 verbatim

# §3.4 false-positive anchor
grep -n 'Install Rust verification tools' /tmp/helios-run-30059559064.log
# anchor at line 1842; window 1839-1862 reproduces §3.4 verbatim
```

> Note: ephemeral capture scripts used to derive these windows (e.g.
> `D:/atlas/verification/_anchors_raw.txt`,
> `D:/atlas/verification/_prebook_anchors.txt`,
> `D:/atlas/verification/_prebook_diff_body.txt`) are intentionally not
> retained; SSOT is this evidence file. The reproduction commands above
> regenerate the verbatim content on demand from the GitHub API.
