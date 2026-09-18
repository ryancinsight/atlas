<a id="atlas-overlay-worktree-keyed"></a>
## ATLAS-OVERLAY-WORKTREE-KEYED-2026-09-06 — The overlay gate compares a committed artifact against a generation from uncommitted inputs [arch] — review

- **Integrator:** claude-opus-5; **branch:** none (atlas main);
  **lease:** `scripts/atlas-stack-overlay.py` 2026-09-06T21:40Z.
- **Last-update:** 2026-09-06.
- **Measured.** `atlas-stack-overlay` has failed on main at `57e2a81b`,
  `81dc17a9` and `be2d1444`, every time with the same body: `OVERLAY: overlay
  differs from a fresh generation`, `0 lagging requirement(s), 0 repo(s) with
  pin drift`. Regenerating locally and committing the result (`81dc17a9`, which
  added the missing Moirai `[patch]` sections) did not clear it.
- **Why it cannot clear.** The generator discovers the closure by globbing
  `**/Cargo.toml` under each `repos/<member>` **worktree**, and emits a patch
  entry only where the local version satisfies the consumer requirement
  (`LagAwarePatchEmissionTestCase`). CI checks the submodules out at their
  recorded gitlinks. Every member tree ahead of its gitlink — the normal state
  during development; nine of ten were ahead when this was measured — feeds the
  generator different versions than CI validates against, so a developer's
  regeneration and CI's disagree by construction. The gate is unsatisfiable in
  steady state, and each gitlink advance re-reds it.
- **Outcome.** Key the closure to the revision, as `atlas-conformance.py`
  already does with `--revision`: read each member's manifests at its recorded
  gitlink (`git show <sha>:<path>`) rather than from its worktree, so the
  overlay is a pure function of the superproject commit and both CI and any
  developer generate the same bytes. The emitted paths stay `repos/<name>` —
  the overlay still points at local trees, which is its purpose; only closure
  *discovery* becomes revision-keyed.
- **The stated outcome was built and falsified, 2026-09-06.** Revision-keyed
  closure was implemented (manifests via `git show <gitlink>:<path>`, listing
  via `ls-tree`, worktree fallback on an unreadable gitlink) and generated a
  deterministic overlay — 104 lines different from the committed one, because
  at the gitlinks Moirai is 0.5.0 where the worktree is 0.6.0, which flips
  every lag verdict that depends on it.
  
  That determinism is bought at the cost of the overlay's purpose. Its emission
  decision is "can the local tree satisfy this requirement", and cargo answers
  that question against the **worktree** when it resolves. Keying the decision
  to the gitlink makes the file describe a state cargo does not see: it can
  emit a patch the worktree cannot unify (a resolution failure) and, more
  commonly, withhold a patch that would have worked — so the overlay stops
  pointing at local trees exactly while those trees are being developed, which
  is the one case it exists for. The change is reverted, unlanded.
- **The unsatisfiability premise is falsified, 2026-09-09.** The claim above
  was that dev worktrees feed the generator different versions than CI
  validates against, so the gate can never clear. Measured directly across all
  26 members — every non-output `Cargo.toml`, worktree content against the same
  path at the member's `origin/HEAD`, comparing the generator's actual inputs
  (manifest path, package name, version) — **zero members differ**, with several
  trees sitting on feature branches at the time. Feature work does not move
  package versions or manifest paths; only a deliberate release bump does, and
  a bump is pushed. So developer and CI regenerations agree, and the earlier
  gitlink-keyed experiment was falsified for the right reason but generalized
  to the wrong conclusion: the gate is keyed to member *default heads*
  (`submodule update --remote`), not to gitlinks, and default heads are what
  the worktrees track.
- **What the gate was actually reporting.** The committed overlay carried no
  `[patch]` section for leto, ritk, coeus, hephaestus, consus or tyche. Each had
  been withheld by lag-aware emission while its local tree could not satisfy a
  consumer requirement, and nothing regenerated the file once the Moirai sweep
  made them satisfiable. Every local build in the stack was therefore resolving
  those six providers from git rather than the local trees — the overlay not
  applying to six of the providers it exists for, silently. Regenerated and
  committed at `49d633852`; the equality clause is kept, because it is the only
  clause that detects this state.
- **Standing risk this leaves.** A developer holding an unpushed version bump
  regenerates differently from CI. That is the gate working — the bump has to
  be pushed — not a contradiction, and it is transient by construction.
- **Confirmed by the gate itself, 2026-09-09.** The run on `49d633852` no
  longer emits the `OVERLAY:` clause at all; its failure is now one requirement
  lag and eight locks, both revision-meaningful and both owned by
  the apollo pin (apollo#385). CI's regeneration and
  the worktree regeneration agree byte for byte, which is what the equality
  clause asserts — so it is kept. Dropping it, as this item previously
  recommended, would have removed the only clause that detects an overlay
  silently withholding providers.
- **Risk / change class:** [arch] [patch]; derived-state definition, no
  member change.

