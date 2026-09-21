<a id="apollo-quarantine-lift"></a>
## ATLAS-APOLLO-QUARANTINE-LIFT-2026-09-08 - Apollo's moirai rev pin can now be removed [patch] - todo
Parent: [`#moirai-06-sweep`](backlog.md#moirai-06-sweep).
- **outcome:** `apollo/Cargo.toml` drops `rev = "83aa411"` from its `moirai` dependency, requires `0.6.0`, and regenerates its lock.
- **trigger fired:** hook landed as [moirai#290](https://github.com/ryancinsight/Moirai/pull/290) on 2026-09-08, satisfying the pin's own removal-trigger comment.
- **blocked:** both apollo trees are peer-held (lease to `codex/main_integration`), whose own item requires the dependency lock stay untouched until it completes.
- **re-open trigger:** `APOLLO-CODELET-SCHEDULE-CONTROLS` completes, or its integrator confirms the lock may move.
