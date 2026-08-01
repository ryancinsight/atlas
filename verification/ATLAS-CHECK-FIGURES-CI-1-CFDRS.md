# ATLAS-CHECK-FIGURES-CI-1-CFDRS — Local closeout capture

## 1. Context

User spec called for an Option α closeout branch `codex/cfdrs-book-figures-
closeout` rooted at SHA `2686b86`. **Both deviations were intentional:**

- PR #315 (squash-merged at `80f8611f`) had already delivered the book-figures
  structural closeout + ci.yml wiring + `check-figures` SSOT lint to CFDrs
  main. The work that remained in this turn was a parallel `fix(cfd)`-style
  WIP consolidation.
- A Copilot-authored sweep commit `0fc64b0e` (`fix(cfd): migrate tests and
  cascade to local proteus with Quantity types`) landed ahead of the branch
  cut, absorbing the 21-file CFD-AEQUITAS-CASCADE-METRICS-1 WIP into the
  local history ahead of this branch.

Actual branch created: **`codex/cfdrs-dirty-wip-closeout`** rooted at
**`0fc64b0e`** (1 commit ahead of `f04b1d75`). A future agent grepping
`git branch -a | grep book-figures` will NOT find this branch — that
semantic divergence is documented here for SSOT traceability (reviewer
bullet Q7, must-have).

## 2. Execution

- **Branch**:    `codex/cfdrs-dirty-wip-closeout`
- **Base**:      `0fc64b0e` (Copilot `fix(cfd)`; absorbs 21-file WIP sweep)
- **Final HEAD**:  `1efc7fcf` (after `git commit --amend -F` with proper
  multi-line body; the initial round had escape-stuffed `\n` literals)
- **Commit subject**:
  `docs(cfdrs): Aequitas cascade metric final slice + retire legacy parity_archive.html`
- **Branch-localized commit (vs base 0fc64b0e)**: **1 file deleted, 366
  deletions(-)** — `parity_artefacts/INDEX.html` is the only localized
  change on this branch (reviewer bullet Q3, must-have).
- **Branch-vs-f04b1d75 (user-cited base) stat**: 21 M + 1 A + 1 D — most
  of those 21 M/A entries are absorbed upstream by 0fc64b0e, not by 1efc7fcf.
- **Absorbed via 0fc64b0e** (NOT in our branch): CHANGELOG, CHECKLIST,
  gap_audit, `docs/atlas-migration/cascade-physical-metrics.md` (NEW — 33-line
  Aequitas-cascade-boundary design note), Cargo.toml (`[patch]` for local
  proteus), Cargo.lock (proteus git-source row removed), 19 cfd-3d +
  cfd-validation src/test/example changes, 4 root `tests/cfd-*` rewrites.
- **Branch-localized (in 1efc7fcf)**: `parity_artefacts/INDEX.html` deletion
  (30 KB legacy artefact; canonical parity archive lives at parent
  `D:/atlas/parity_artefacts/INDEX.md`).

## 3. Cargo workspace blocker (real, pre-existing)

Local `cargo run -p xtask -- check-figures` exits 101 with the full chain:
```
error: failed to get `coeus-core` as a dependency of package
  `ritk-vtk v0.1.0 (...\repos\ritk\crates\ritk-vtk)`
  ... which satisfies path dependency `ritk-vtk` (locked to 0.1.0) of package
  `cfd-io v0.3.0 (...\repos\CFDrs\crates\cfd-io)`
Caused by: failed to read `D:\atlas\repos\coeus\coeus-core\Cargo.toml` (os error 3)
```
Affects: local `cargo run -p xtask -- check-figures` AND the CFDrs CI gate
(the only job in `.github/workflows/ci.yml` runs the same broken invocation).
Root cause: the `D:/atlas/repos/coeus/` checkout has no `coeus-core/Cargo.toml`,
so the cfd-io → ritk-vtk → coeus-core path-dependency chain cannot resolve.
**Pre-existing at f04b1d75** — the `0fc64b0e` proteus `[patch]` does not
touch this chain. Tracked under **ATLAS-CFDRS-COEQ-BLOCKER-1** (new entry
appended to `D:/atlas/backlog.md` by this slice).

## 4. SSOT cross-references

- **Canonical parity archive**: parent `D:/atlas/parity_artefacts/INDEX.md`.
- **CFDrs-local reference**: `docs/book/SUMMARY.md` Appendix F is preserved
  and already points to `../../../parity_artefacts/INDEX.md` — retirement is
  safe (no orphan backlink inside the mdbook).
- **Backlog IDs**: `ATLAS-CHECK-FIGURES-CI-1` (state amend appended), `ATLAS-
  CFDRS-AEQUITAS-CASCADE-METRICS-1` (closed via 0fc64b0e + this slice), and
  new `ATLAS-CFDRS-COEQ-BLOCKER-1`.
- **Parent-side gitlink advance**: deferred to the future slice that lands
  the coeus-core restoration (so the gitlink only moves when the cargo
  workspace compiles).

## 5. Forward plan (Option α deferred to λ parked)

- **Option A** *(prefer)*: open `ATLAS-CFDRS-COEQ-BLOCKER-1` slice that
  restores `D:/atlas/repos/coeus` submodule + verifies cfd-io → ritk-vtk →
  coeus-core path chain compiles locally. Once GREEN, push
  `codex/cfdrs-dirty-wip-closeout` and open PR. The branch carries zero
  code-graph changes so the CFDrs ci.yml `check-figures` job will pass the
  same SSOT_IN_SYNC gate as f04b1d75 once cargo metadata resolves.
- **Option B** *(park)*: leave `codex/cfdrs-dirty-wip-closeout` local-only.
  Push the `INDEX.html` retirement into a separate slice alongside the
  coeus-core fix. Defer the closeout confirmation until the blocker lands.
- **External GitHub backlink risk** *(minor)*: any URL pointing at
  `parity_artefacts/INDEX.html` will 404 after a destructive push (Appendix F
  in the mdbook continues to point at the canonical parent INDEX.md via
  the relative `../../../` path; verified).

## 6. Backlog pointer

This file backs two `D:/atlas/backlog.md` mutations shipped in this slice:

1. Append a new top-level `## ATLAS-CFDRS-COEQ-BLOCKER-1` entry documenting
   the cfd-io → ritk-vtk → coeus-core cargo workspace break.
2. One-line state amend on the existing `ATLAS-CHECK-FIGURES-CI-1` entry
   marking CFDrs as `partial-verify (parked on coeus-core blocker)` with
   breadcrumb to this evidence file.

## 7. Reproduction commands

```bash
# Branch creation state (verbatim from this slice):
cd /d/atlas/repos/CFDrs
git switch -c codex/cfdrs-dirty-wip-closeout           # from 0fc64b0e
git rm parity_artefacts/INDEX.html                      # 366-line artifact retire
git commit --amend -F /tmp/cfdrs_commit_msg.txt         # 1efc7fcf final HEAD

# Local pre-push verification (currently BLOCKED):
cargo run -p xtask -- check-figures                     # exits 101 — coeus-core missing

# Forward / Option A:
cd /d/atlas/repos/coeus && git status                   # diagnose coeus-core checkout
# (restore coeus-core Cargo.toml + retry cargo check + push branch)
```
