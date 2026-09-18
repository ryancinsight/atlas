<a id="moirai-06-sweep"></a>
## ATLAS-MOIRAI-06-SWEEP-2026-09-06 - Moirai 0.6.0 landed without its forward sweep [patch] - in-progress

- **outcome:** every first-party requirement on a `moirai-*` crate resolves
  against Moirai's current workspace version, and each member's lock is
  regenerated and green.
- **the defect:** Moirai's workspace version is **0.6.0**; members still
  require `^0.5.0`, so the resolver rejects the only version that exists.
  `architecture_scoping` (pin discipline) makes the forward sweep part of the
  same co-evolution unit as the version advance, precisely because "a patch
  unifies only when the local version satisfies the declared requirement".
  It never fired. The second cost is quieter: under the stack overlay a local
  crate replaces a git one only when the version satisfies the requirement, so
  the lag silently disables the `[patch]` beneath it.
- **measured 2026-09-06, third attempt, and the first two were wrong.** Scan
  one read only root manifests (6 members). Scan two added nested manifests but
  its pattern required `version` immediately after `{`, so it missed every
  dependency written `git = ..., version = ...` — including coeus, the one
  blocking three others (10 members). An order-independent parse of every
  `Cargo.toml` in every member's default branch gives the real set. Recording
  the method, not just the number, because the number moves as peers land legs:

  | Member | Requirements | State |
  | --- | --- | --- |
  | leto | `moirai-runtime` | landed, [leto#176](https://github.com/ryancinsight/leto/pull/176) |
  | coeus | `moirai-runtime`, `moirai-async` | peer holds it, bump applied uncommitted |
  | helios | `moirai-runtime`, `moirai-parallel` | bumped `75aab40`, blocked on coeus |
  | ritk | `moirai-runtime` | bumped `7b1cc5b3`, blocked on coeus |
  | kwavers | `moirai-parallel` | landed |
  | CFDrs | `moirai-runtime` | landed, [CFDrs#419](https://github.com/ryancinsight/CFDrs/pull/419) |
  | apollo | `moirai-runtime` | **not sweep debt — see below** |

  gaia, hephaestus, consus, tyche were in an earlier count and are already
  clean — peers swept them in parallel.

- **2026-09-08: two members remain, and one of them should not be swept.**
  `apollo` pins `rev = "83aa411"` under a comment that names its own removal
  trigger: *"Temporary co-evolution pin for the worker-idle reclamation seam;
  remove `rev` after Moirai's hook lands on main."* That commit is not on
  moirai's `main`, and the pull request carrying it —
  [moirai#257](https://github.com/ryancinsight/Moirai/pull/257), open since
  2026-09-04 — is `CONFLICTING` with no CI ever run. So apollo is a documented
  quarantine whose trigger has not fired, exactly as pin discipline prescribes,
  and bumping it would break its dependency on an unlanded hook. Counting it as
  sweep debt was my error: the scan cannot tell a quarantine from a lag, and I
  did not read the comment above the line before listing it as unclaimed.
- **the real remaining work is moirai#257**, not apollo. Landing it fires
  apollo's trigger; until then apollo is correct as it stands.
- **helios** carries the last plain lag: the requirement bump and lock are
  committed on `build/helios-moirai-06` ([helios#92](https://github.com/ryancinsight/helios/pull/92)),
  held by one remaining `helios-gpu` error that a peer is mid-edit on.
- **the order is forced, not a preference.** A member's lock resolves its
  first-party git dependencies from their `origin/main`, so a bump cannot be
  verified until every dependency it pulls has landed its own. Bumping `ritk`
  alone fails on `coeus-core`'s `^0.5.0`; bumping `kwavers` alone fails on
  `ritk-io`'s; bumping `helios` alone fails on `coeus-core`'s. **coeus unblocks
  three of the remaining five.**
- **bumps are committed before they can be verified**, deliberately: the
  manifest edit is the executable remainder and the lock regeneration is the
  blocked substep. Leaving the edit as uncommitted state in a shared tree is
  what produced the two-day-old duplicated dirt found in kwavers earlier today.
- **it is blocking real work:** kwavers cannot advance its resolved `ritk`
  revision, so it cannot pick up ritk#238, so `cargo check --workspace` on
  kwavers `main` is red and
  [kwavers#727](https://github.com/ryancinsight/kwavers/pull/727) cannot run
  `clippy --all-targets` and stays draft.
- **Corrected 2026-09-08 (kwavers#725 landed):** the rev-advance path is open
  *now*, without waiting on the Moirai 0.6 sweep. [ritk#238](https://github.com/ryancinsight/ritk/pull/238)
  merged (`1b9d4d86`) and [kwavers#725](https://github.com/ryancinsight/kwavers/pull/725)
  pinned the fixed rev and landed (`56ea403d`); kwavers `main` CI is green at
  `96819eae`, Integration Suite included. The blocker above applies to
  *version-requirement* bumps (Moirai `^0.5.0` → `0.6.0`), which do force
  global re-resolution; a bare git *rev* re-selection moves one source and
  leaves the rest of the lock untouched, so it clears the `RandomScalar`
  break independently of the sweep. kwavers#727's premise should be
  re-judged against the green main.

