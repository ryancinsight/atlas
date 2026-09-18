<a id="atlas-overlay-005"></a>
## ATLAS-OVERLAY-005 — Clear first-party rev pins across the stack [patch] — in-progress

- Owner: session-808504af. Decision: pin discipline (`architecture_scoping`) —
  a `rev =` is quarantine with a removal trigger, not a durable source form.
- Root cause: a rev-qualified git source is a **distinct package** to Cargo, so
  the stack `[patch]` overlay — which matches the bare URL — can never unify it.
  Sixteen first-party pins had accumulated across five repos at three different
  `aequitas` commits and two `eunomia` commits, so any crate reaching a provider
  by both forms received two incompatible copies of the same trait. Hyperion
  could not multiply two `Quantity` values for exactly this reason.
- ✅ Cleared and pushed: proteus `9a8655d` (also restored its manifest from a
  local path-dep leak to git+version), asclepius `ccffb6b`, tyche `996b649`,
  kwavers `df9008d93`.
- **Current residual**: `python scripts/atlas-stack-overlay.py check` now
  reports one coherence defect: Athena's peer-dirty checkout is three commits
  behind `origin/main` and its lock still pins the five-package Hermes
  `0.6.0` closure while the local provider is `0.7.0`. Athena is outside this
  named provider set and is not edited through the Atlas integration slice.
  The former CFDrs requirement lag is cleared at the current provider closure;
  re-run the check after CFDrs merges and when Athena's own work is
  reconciled.
- **Mechanism worth mechanizing**: depinning alone is insufficient. Every lock
  move needs `python scripts/atlas-stack-overlay.py generate` to re-derive the
  patch block, otherwise the graph keeps a local-vs-git split. This is the
  mechanism behind the recurring "local X cannot replace git-sourced Y" failures
  on this board. `atlas-stack-overlay.py check` already exits nonzero on lag, so
  wiring it into CI would catch the class at the source.
- Evidence: `cargo tree -d` in kwavers reports no duplicate first-party crates;
  the current overlay check provides the two residuals above rather than an
  aligned result.

