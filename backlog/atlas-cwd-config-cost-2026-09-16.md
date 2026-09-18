<a id="atlas-cwd-config-cost-2026-09-16"></a>
## ATLAS-CWD-CONFIG-COST-2026-09-16 — Cargo config discovery is all-or-nothing: the shared `target-dir` arrives with the whole-stack `[patch]` overlay [patch] — in-progress

- **Same generator as
  `ATLAS-TARGET-FORK-REGRESSION-2026-09-09`,
  opposite outcome.** Cargo resolves configuration by walking up from the
  working directory. Every case in that item *lost* the stack config and forked
  a target; this is the first one that *kept* it — and inherited a 136-row
  overlay it had no use for. That item's guard ("an invocation that leaves the
  overlay carries `CARGO_TARGET_DIR`") does not cover this direction, because
  nothing left the overlay.
- **Observed 2026-09-16 in `test_atlas_stack_overlay.py::LagAwarePatchEmissionTestCase::test_cargo_unifies_current_closure_and_retains_old_git_revision`.**
  `CargoOverlayFixture` ran cargo with `cwd` = the Atlas root *on purpose*, so
  the fixture would inherit the stack's single shared `target/`. One literal
  `timeout=30` bounded both `cargo metadata` (resolves in about a third of a
  second) and `cargo check` (compiles), so the compile tripped a
  resolution-sized bound and the test failed as though it had hung.
- **What the cwd choice actually did, measured.** The same `cwd` that supplies
  `target-dir` also applies the root `.cargo/config.toml` in full: **46
  `[patch]` tables, 136 patched package rows, 23 member roots**, against a
  fixture graph of two dependency-free packages that share none of it. There is
  no `cwd` that yields one key of the stack config and not the other.

  | cwd | `CARGO_TARGET_DIR` | `target_directory` |
  | --- | --- | --- |
  | `/d/atlas` | unset | `D:\atlas\target` |
  | fixture tmpdir | unset | `<tmpdir>\target` |
  | fixture tmpdir | `D:/atlas/target` | `D:/atlas/target` |

- **Correction: the 362.89s first reported here is not the cwd's doing, and the
  cwd change buys no time.** Re-running the old arm (cwd = Atlas root, no
  `CARGO_TARGET_DIR`, budgets unchanged) measures **1.28s**; the arm shipped at
  that point (fixture `cwd`, `CARGO_TARGET_DIR` = the shared `target/`) measures
  **1.60s**, and the module then passed its 19 tests in 1.23s. None of the
  overlay's patched sources occur in the fixture's graph, so its patch registry
  is never consulted and the overlay costs nothing here. The attribution
  written into the fixture comment at the time ("minutes of unrelated
  resolution per run") is withdrawn by that measurement; the comment now says
  what was measured.
- **What the 362.89s and the 30s failure most plausibly were — unverified.**
  Both arms build into `D:\atlas\target`, the stack-wide cache the root config
  documents as serializing concurrent builds. A fixed bound on a command that
  can block on another process's build lock reports contention as a defect,
  which is the shape of the failure that opened this item. Recorded as the
  leading explanation because no reproduction of the stall was obtained — not
  as a finding. Provided for anything else that builds in that cache; the
  fixture stopped building there on 2026-09-16, per the residual below.
- **Fixed in the tree 2026-09-16.** `resolve`/`check` run from the fixture's own
  directory, so the stack overlay no longer applies. Budgets split per operation
  (`RESOLUTION_TIMEOUT_SECONDS = 30`, `COMPILE_TIMEOUT_SECONDS = 120`), and an
  over-budget command raises the fixture's own `AssertionError` naming the
  budget and the command. No assertion, package selection or lock check was
  relaxed, and no timeout was raised to cover slowness.
- **Residual closed 2026-09-16 — the fixture no longer builds into the shared
  cache at all.** The first cut pinned `CARGO_TARGET_DIR` to the shared
  `target/`, which bought the isolation from `cwd` at the price of the very
  property that raised this item: the fixture's duration stayed a function of
  every other cargo build on the machine, so a fixed bound on its compile could
  still report another process's build lock as a defect. The fixture now owns a
  `target` inside the tempdir it already owns (`CargoOverlayFixture.target`),
  set in its environment beside the `CARGO_HOME` and Git config it already
  redirected, so its scope is uniform: nothing it invokes reads or contends for
  machine-global state. It also *pins* the value rather than inheriting it, which
  matters because the stack's own bootstrap scripts export `CARGO_TARGET_DIR` —
  an unpinned fixture in a developer shell lands back in the shared cache.
- **Measured 2026-09-16 with that export in place** (`CARGO_TARGET_DIR=D:/atlas/target`):
  the shared cache gains no `overlay*` entry and the fixture passes; the module's
  20 tests pass in 2.0-2.4s across runs, `check`'s build is 1.5s and cold every run by
  construction, so the fixture's duration no longer depends on other cargo
  activity. The added second of wall time against the shared-cache arm (1.23s) is
  the price of owning the cache, paid per run.
- **No route back.** `stack_root` is gone from `resolve`/`check` and the
  `target_dir` override from `run`, so pointing the fixture at the shared cache
  again requires reintroducing the argument, not just changing a default. A
  regression test (`test_fixture_builds_in_its_own_target_not_the_shared_stack_cache`)
  constructs the fixture under a decoy `CARGO_TARGET_DIR` and asserts the pinned
  one wins; the cargo test additionally asserts its build produced a real cache
  there (`CACHEDIR.TAG`) and that no `target` appeared under `consumer`/`source`.
- **Acceptance:** no fixture or test invocation in the meta-repo depends on
  `cwd` for a stack config key it needs — target directory included — and a
  cargo command in this suite either owns its target directory or sizes its
  bound as a hang guard rather than a performance assertion.
- **Verified 2026-09-16:** `pytest scripts/tests/test_atlas_stack_overlay.py` →
  20 passed in 2.35s, 2.19s of it with `CARGO_TARGET_DIR` exported as the
  bootstrap scripts do; `pytest scripts/tests` → 702 passed, 3 skipped, 89
  subtests.

