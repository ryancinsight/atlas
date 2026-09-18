<a id="atlas-cfdrs-crlf-085"></a>
## ATLAS-CFDRS-CRLF-085 — CFDrs commits CRLF with no `.gitattributes` [patch] — blocked 2026-08-14

outcome: `.gitattributes` (`* text=auto`) normalizes CFDrs source to LF and the tree is renormalized in one dedicated commit, so `gitattributes_missing` is 0 for CFDrs and LF-writing tools stop reflowing whole files.

Confirmed still open and worse than filed: `core.autocrlf=true` is set globally while committed blobs are inconsistent per-directory (e.g. `crates/cfd-1d/Cargo.toml` stored LF vs `crates/cfd-python`/`crates/cfd-schematics` `Cargo.toml` stored CRLF), so a one-line edit to a CRLF-stored file stages as a whole-file rewrite. 1,702 of 2,411 tracked files are CRLF in the working tree (~70%).

Not safe to run now: the checkout sits on peer branch `codex/cfdrs-legacy-approx-cleanup` (2 ahead / 11 behind `origin/main`) with a second live lane at `worktrees/cfdrs-ci-workspace-rust`; renormalizing would conflict with both across nearly every file. Adding `.gitattributes` alone is rejected too — git honors it from the working tree, so it would LF-normalize files one at a time on every subsequent `add`.

Required sequence when unblocked: land on `main` directly — add `.gitattributes` and `git add --renormalize .` as one commit containing nothing else, with every lane closed or rebased across it.

Re-open trigger: the CFDrs working branch merges to `main` and no second lane is live. Scale tracked separately as `-208`.
