<a id="apollo-quarantine-lift"></a>
## ATLAS-APOLLO-QUARANTINE-LIFT-2026-09-08 - Apollo's moirai rev pin can now be removed [patch] - todo

Parent: [`#moirai-06-sweep`](backlog.md#moirai-06-sweep).

- **outcome:** `apollo/Cargo.toml` drops `rev = "83aa411"` from its `moirai`
  dependency, requires `0.6.0`, and regenerates its lock — closing the last
  item in the Moirai 0.6 sweep.
- **the trigger has fired.** The pin's own comment says *"remove `rev` after
  Moirai's hook lands on main and regenerate Cargo.lock."* The hook landed as
  [moirai#290](https://github.com/ryancinsight/Moirai/pull/290) on 2026-09-08,
  a takeover of #257 which had sat four days behind a CI webhook that never
  delivered.
- **this is a quarantine expiring on schedule, not debt.** Worth recording as
  the positive case: the pin carried its removal trigger in a comment beside
  it, so lifting it required reading one line rather than reconstructing intent
  — which is exactly why pin discipline asks for the trigger to be written
  down.
- **blocked on a lease, not on a tree.** Both apollo trees are held by live
  peers, and the lane's board block explicitly leases its regions to
  `codex/main_integration` with a contributor lease inside it, dated
  2026-09-08. More to the point, that item's own dependency line reads
  *"preserve each tree's dependency lock"* — and this lift is exactly a
  manifest edit plus a lock regeneration. Taking it now would break the
  condition their in-flight work states it needs.
- **re-open trigger:** `APOLLO-CODELET-SCHEDULE-CONTROLS` completes, or its
  integrator confirms the lock may move. This is a genuine wait on a peer's
  stated precondition rather than a scheduling inconvenience, so it parks
  rather than being worked around.

