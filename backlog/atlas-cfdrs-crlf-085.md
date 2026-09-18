<a id="atlas-cfdrs-crlf-085"></a>
## ATLAS-CFDRS-CRLF-085 — CFDrs commits CRLF with no `.gitattributes` [patch] — blocked 2026-08-14

The repository stores CRLF line endings and has no `.gitattributes`, so any
tool that writes LF — rustfmt, a Python edit, most editors on non-Windows —
reflows whole files. During the scalar consolidation this turned a real 10k-line
diff into 128k lines until the endings were restored file by file, which is
both unreviewable and a merge-conflict generator for every concurrent agent.

`engineering_gates` requires `* text=auto` so every host hashes identical blobs;
the conformance scan already counts this as `gitattributes_missing`. CFDrs is
the case where the cost is now measured rather than theoretical.

**Acceptance oracle:** `.gitattributes` normalizes source to LF, the tree is
renormalized in one dedicated commit, and `gitattributes_missing` is 0 for
CFDrs.

**Status → blocked 2026-08-14; re-open trigger: the CFDrs working branch is
merged to `main` and no second lane is live.**

**Blocker re-verified 2026-08-18 and it still holds** — the trigger has not
fired. `worktrees/CFDrs-runtime-budget` is live on
`codex/cfdrs-backward-step-108`, and `origin` carries ten-plus branches
unmerged into `main`. Renormalizing the tree now would conflict with every one
of them, which is precisely the cost the item describes. Its scale is filed
separately as `-208`. The underlying defect was re-confirmed unchanged today:
`.gitattributes` still absent, `core.autocrlf=true`, and the same directory
still mixes stored endings — `crates/cfd-1d/Cargo.toml` LF against
`crates/cfd-python/Cargo.toml` and `crates/cfd-schematics/Cargo.toml` CRLF.

Confirmed and worse than filed.
`core.autocrlf=true` is set globally while committed blobs are *inconsistent*:
`crates/cfd-1d/Cargo.toml` is stored LF, `crates/cfd-python/Cargo.toml` and
`crates/cfd-schematics/Cargo.toml` are stored CRLF, in one directory. With
autocrlf on, `git add` LF-normalizes unconditionally, so a one-line edit to
either CRLF-stored file stages as a whole-file rewrite — measured while landing
ATLAS-CFDRS-GPU-DEFAULT-084, where a three-line change first staged as 238
changed lines. The workaround used there (`git hash-object --no-filters` plus
`git update-index --cacheinfo` to stage a CRLF-preserving blob) restores a
reviewable diff but is not a policy.

The renormalization itself is **not** safe to run now, for reasons the filing
did not anticipate. 1,702 of 2,411 tracked files are CRLF in the working tree,
so the sweep touches ~70% of the repository — and the checkout sits on the peer
branch `codex/cfdrs-legacy-approx-cleanup`, which is 2 commits ahead of and
**11 commits behind** `origin/main`, with a second live lane at
`worktrees/cfdrs-ci-workspace-rust` on `feat/cfdrs-ci-workspace-rust`.
Renormalizing there would conflict with both the unmerged `main` commits and
the sibling lane across every touched file. Creating `.gitattributes` alone is
also rejected as a half-measure: git reads it from the working tree whether or
not it is tracked, so it would start LF-normalizing files one at a time on
every subsequent `add`, producing the same churn as drip rather than as one
reviewable commit.

**Required sequence when unblocked:** land on `main`, not a feature branch —
add `.gitattributes` (`* text=auto`) and `git add --renormalize .` as a single
commit containing nothing else, with every lane closed or rebased across it.

