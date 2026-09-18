<a id="atlas-lane-audit-001"></a>
## ATLAS-LANE-AUDIT-001 — Lane-root sweep results and residuals [patch] — in-progress (residual)

- Policy: AGENTS.md git_discipline Worktrees (lanes are swept claim surfaces; created only by `git worktree add`) + concurrent_agents (gitdir-mirror checkouts prohibited — a `.git` file pointing at another tree's gitdir shares its index and corrupts both trees' status).
- Audit 2026-07-26 of `D:\atlas\worktrees` (26 entries): 4 compliant live lanes (coeus-backend-parity, hephaestus-mixed-reduction-batch, kwavers-aequitas-vessel-metrics, ritk-ebcot-magnitude-view); 13 gitdir-mirror checkouts on main (the improvised-provider species); 7 standalone clones; 3 bare directories; 1 broken meta lane. Legacy root `D:\worktrees` now empty — its lanes completed and dissolved per ATLAS-WORKTREE-001.
- Done: `report` re-mint deleted (SVG already rescued to repos/report/figures); broken `atlas-final-integration` meta lane deleted + `worktree prune` (meta lanes prohibited); 5 stale clones rescue-fetched into their authoritative repos under `refs/rescue-worktrees/<name>/*` then deleted (leto incl. codex/leto-real-sparse-lu); 13 gitdir-mirrors deleted — and regenerated within seconds: a live process on pre-fix instructions re-mints the mirror farm (signature: `.git` file -> `../../.git/modules/repos/<r>`, checkout on main). Self-resolves as sessions roll onto current instructions; re-audit the root then and delete survivors.
- Residuals: (1) `hephaestus-unary-math-parity` — git-less source snapshot with real unique deltas (6/12 sampled files differ from authoritative): reconcile into a branch of repos/hephaestus (diff, salvage, commit under the unary-math-parity item), then delete the snapshot; (2) `ritk-book-complete` — near-duplicate snapshot (11/12 identical): verify the delta, salvage if real, delete; (3) stale lanes `coeus` (codex/coeus-error-function-parity, 30h) and `mnemosyne` (codex/mnemosyne-tier-selection, 33h) — takeover material: complete their items or confirm branches landed, then remove the lanes; (4) fresh clones `aequitas`/`eunomia` left in place (regenerator-owned) — delete at re-audit.
- Re-audit 2026-08-14: Ritk is now compliant with two trees (`main` and
  `ritk-fix`) after `8a1c6ac`. The current probe reports four Kwavers
  violations: three trees, one detached temporary lane outside the canonical
  lane root, and the unlinked `worktrees/kwavers-cascade-provider-042`
  directory. The temporary checkout carries fresh unique `Cargo.toml` and
  `Cargo.lock` changes for the `ritk-image` 0.4.0 integration; the canonical
  lane carries dirty PM work. The empty unlinked directory was checked before
  removal, but Windows retained an open handle and refused deletion. No
  peer-owned work or unique state was removed; re-open deletion after the
  temporary owner releases or rescues its changes and the handle closes.

- Re-audit 2026-08-17: the live Kwavers tree is now the main checkout plus
  `worktrees/kwavers-doc557` at detached commit `df818b9a1`. The lane is clean
  but detached, so `python scripts/atlas-lane-audit.py` reports one violation.
  It remains peer coordination state; no branch switch or lane deletion is
  authorized until its owner reconciles the documentation run.
- The completed CFDrs Fourier/SSOR lane and Apollo public-plan lane were removed
  after their PRs merged; their local feature branches were deleted. The current
  audit therefore reports only the detached Kwavers documentation lane above.

