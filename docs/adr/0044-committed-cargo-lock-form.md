# ADR 0044 — Committed Cargo.lock is the standalone form

- Status: Accepted
- Date: 2026-08-17
- Driver: backlog ATLAS-LOCK-CONVENTION-079

## Context

Two forms of a member `Cargo.lock` circulate in this stack.

The **standalone form** is what `cargo` writes when it resolves the repository
on its own: every git dependency carries
`source = "git+https://github.com/ryancinsight/…#<rev>"`, and there are no
`[[patch.unused]]` tables.

The **stripped form** is what the stack development overlay produces. The
`[patch]` block in the root `.cargo/config.toml` (ADR-0027,
`scripts/atlas-stack-overlay.py`) redirects first-party git dependencies to the
local working trees. Cargo records that by *dropping* the `source` line of every
redirected package and appending a `[[patch.unused]]` table for each patch entry
the build did not consume. Patching one crate to a path makes its whole
workspace resolve by path, so siblings the patch table never names lose their
source too.

The overlay applies to every build rooted anywhere beneath `D:\atlas`. It is
therefore not an occasional event: **every local build rewrites the lock of the
member it builds.** The measured consequence is that `Cargo.lock` is dirty in
most members most of the time, which trains everyone to skip past it in
`git status` — and that is how the stripped form reaches HEAD.

It had reached HEAD in ten of twenty-eight tracked locks when this was measured
(2026-08-17): asclepius, eunomia, harmonia, hermes, iris, mnemosyne, proteus,
themis, tyche, and `melinoe/contracts/atlas-device`. Three of those — hermes,
mnemosyne, tyche — had a correct committed lock a fortnight earlier and
regressed during the current sweep, two of them inside commits whose subject was
about something else entirely.

The stripped form is not a stylistic variant. It is unresolvable anywhere the
overlay does not exist:

```
$ cd /d/tmp && cargo metadata --locked --manifest-path D:/atlas/repos/hermes/Cargo.toml
error: cannot update the lock file … because --locked was passed
```

That is every CI job, every `cargo publish` sandbox, and every clean checkout.

## Decision

**A committed `Cargo.lock` is the standalone form.** Concretely, for every
tracked lock in every registered member:

1. Any package the lock resolves from a git dependency carries its
   `source = "git+…"` line.
2. The lock contains no `[[patch.unused]]` table.

The overlay's rewrite is **derived state, never an edit**. It is expected in the
working tree and is restored, not committed.

### Why standalone rather than stripped

The lock exists to make resolution reproducible for a consumer who does not
share the author's environment. The overlay is precisely an environment the
consumer does not share; a lock shaped by it reproduces nothing. The stripped
form's only advantage — matching what a local build happens to leave behind —
is an artifact-of-convenience argument, and the `restore` command removes even
that friction.

### What is *not* a violation

Two shapes look like a stripped lock to a naive `git+` line count and are
correct:

- **A member with no git dependencies.** eunomia, iris, and melinoe legitimately
  resolve zero git sources. Zero `git+` lines is the right answer for them; the
  rule is quantified over the git dependencies a lock actually resolves, not
  over a threshold.
- **A `[workspace.dependencies]` row no crate consumes.** It never reaches the
  lock at all. helios declares `ritk-core`/`ritk-io`/`ritk-registration` and
  kwavers declares `horae` this way; their absence from the lock is correct, not
  a dropped source.

The gate therefore flags only a package that is **present in the lock yet
resolved without a source** although no manifest in the workspace defines it —
a state reachable only through a `[patch]` — plus the `[[patch.unused]]`
signature, which no standalone resolve can produce.

### The one exemption

`melinoe/contracts/atlas-device` is a `publish = false` cross-repo contract
fixture whose dependencies are relative paths into *sibling repositories*
(`../../../hephaestus/crates/…`) and which carries its own `[patch]` table. It
cannot resolve outside a full Atlas checkout by construction, so the standalone
rule does not apply to it. The gate detects this structurally — a workspace with
a path dependency escaping its own repository — and prints the exemption rather
than skipping silently.

## Consequences

- Ten members need their committed lock repaired. Repair is
  `python scripts/atlas-lock-form.py regenerate <member>`, which runs `cargo
  metadata` from a scratch directory **outside** the Atlas tree. Cargo discovers
  `.cargo/config.toml` upward from the current directory, not from
  `--manifest-path`, so this resolves against git without toggling the shared
  overlay out from under concurrent agents. `cargo metadata` rather than `cargo
  generate-lockfile`: it re-resolves only what the lock cannot supply, so a
  restored source does not drag every unrelated pin forward with it.
- Repairing a lock **by rebuilding it under the overlay produces exactly the
  defect**. This is the single most likely wrong fix and is called out here for
  that reason.
- The working tree stays noisy between builds. `restore` collapses it: it
  reverts a lock whose only difference from HEAD is the overlay rewrite, and
  refuses on anything else, so what remains dirty is real.

## Alternatives rejected

- **Commit the stripped form uniformly.** It is the form local builds already
  produce, so the churn would vanish. Rejected: it makes every member
  unresolvable on a clean checkout, which is the lock's entire purpose.
- **Stop committing member locks.** Removes the conflict outright, but the stack
  publishes to crates.io and pins first-party dependencies by git rev;
  reproducible CI resolution needs the lock.
- **Untrack the locks with `skip-worktree`.** Hides the churn completely and
  makes it unstageable, which addresses the training-to-ignore problem at its
  root. Rejected as the default: it is per-clone index state that silently
  survives branch switches and confuses merges, and this stack has several
  agents switching branches in shared trees. Available to an individual who
  wants it; not the convention.
- **Document the churn and rely on review.** That is the status quo, and it
  produced ten violations and three mid-sweep regressions.

## Verification

- `python scripts/atlas-lock-form.py check` fails on any committed lock in the
  stripped form. Wired into `.github/workflows/atlas-conformance.yml`, which
  already triggers on `repos/**`, so every gitlink advance re-measures.
- `python scripts/atlas-lock-form.py staged` is the member-side pre-commit arm,
  installed per clone by `install-hooks`. It rejects the `git add` that would
  create the violation, rather than catching it after integration.
- `scripts/tests/test_atlas_lock_form.py` asserts both directions, including an
  end-to-end run over a synthetic member repository observed **failing** on a
  committed stripped lock and passing on a standalone one, and covers the two
  false positives named above.
- A repaired member is confirmed with `cargo metadata --locked` executed from
  outside the Atlas tree — the only place the committed form's claim is real.
