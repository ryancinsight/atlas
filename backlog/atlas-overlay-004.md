<a id="atlas-overlay-004"></a>
## ATLAS-OVERLAY-004 — Worktree sprawl breaks stack dependency resolution [patch] — in-progress

- Owner: unclaimed; scope: `worktrees/`, the root `.cargo/config.toml`, and the
  13 lane-local `.cargo/config.toml` files. **Not** the lane branches' source.
- Blocker evidence (2026-07-27): `cargo check -p kwavers-physics` fails before
  compiling anything:
  - `failed to select a version for smallvec` — `hephaestus-wgpu v0.18.0` at
    `worktrees/hephaestus-unary-math-parity` requires `^1.15.2`; the kwavers lock
    pins `1.15.1`.
  - `cargo update -p smallvec --precise 1.15.2` then fails harder:
    `package collision in the lockfile: packages aequitas v0.1.0
    (D:/atlas/worktrees/aequitas) and aequitas v0.1.0
    (D:/atlas/worktrees/aequitas-energy-temperature) are different, but only
    one can be written to lockfile unambiguously`.
- Two distinct defects behind it:
  1. ✅ **resolved 2026-07-28** — `worktrees/aequitas` was an **orphaned linked
     worktree**, not a standalone clone: its `.git` file pointed at
     `repos/aequitas/.git/worktrees/aequitas`, whose admin directory had been
     pruned, leaving the checkout on disk with no git registration. Cargo still
     discovered it as a path source, giving two providers for `aequitas v0.1.0`.
     Contents were byte-identical to `repos/aequitas` (`diff -r` clean excluding
     `target`, `Cargo.lock`, `.git`), so nothing unique was lost. Removed with
     user authorization; `git worktree prune` run. `cargo check` across
     kwavers-physics and kwavers-solver resolves again, and the `smallvec`
     conflict cleared with it.
  2. **13 lane-local `.cargo/config.toml` files.** Config-layer ownership
     (`performance_engineering`) puts `target-dir` and the `[patch]` overlay at
     the stack root only; a nested config re-declaring either forks resolution
     and, as here, resolves a relative provider path into a second copy.
- Also: `worktrees/` holds 28 entries against a documented bound of one main
  tree plus one lane per repository. aequitas, coeus, hephaestus, kwavers, and
  ritk each have two or more.
- Acceptance: `cargo check -p kwavers-physics` resolves; `git worktree list` per
  repo is within bound; no lane-local `.cargo/config.toml` re-declares
  `target-dir` or `[patch]`; `worktrees/aequitas` removed after confirming no
  unique commits.
- **Ask-User gate**: removing `worktrees/aequitas` and other agents' lane
  directories is destructive to possibly-live peer setups. Confirm before
  deleting rather than reconciling unilaterally.

