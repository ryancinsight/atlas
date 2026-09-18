<a id="publish-order-optional-edges"></a>
## ATLAS-PUBLISH-ORDER-OPTIONAL-EDGES-2026-09-04 - Decide whether optional dependencies constrain publish order [patch] - in-progress

- **outcome:** a recorded decision, and a publish order that emits a usable
  sequence for the whole stack rather than a 61-package cycle.
- **found:** `#publish-order-workspace-deps` restored dependency edges the
  order had been dropping, and the restored graph is cyclic - but only through
  optional edges. `moirai-gpu` optionally depends on `hephaestus-wgpu`/`-cuda`,
  which reach `moirai-runtime`, closing a loop that no build ever realizes
  because the features are not co-enabled. Recomputed without optional
  dependencies the graph is acyclic and every crate orders.
- **the question:** `cargo publish` records optional dependencies in the
  registry index, so an optional first-party dependency arguably must publish
  first; but an optional edge that closes a cycle cannot be satisfied in any
  order, so treating them as ordering constraints makes first publication
  impossible. Both readings cannot hold.
- **acceptance:** an ADR recording the decision; the tool emits a total order
  under it; a fixture cyclic-through-optional graph is handled as the ADR says.
- **class:** `[patch]`. **risk:** medium - it gates any first publication of
  the stack, and therefore Ares A9. **depends on:** nothing.

- **integrator:** claude-opus-5 (this session). **Drafting ADR 0060
  `0060-publish-order-optional-dependencies.md`**; the decision is that
  optional dependencies are *not* ordering constraints for first publication
  because (a) `cargo publish` does not require an optional dependency to be on
  the registry at publish time — the published metadata records the dep string
  and an `optional` flag, and the dependency is unresolved while the feature
  is off, which is the entire purpose of `optional = true`; (b) the
  cycle-through-optional is a fixture of feature co-activation patterns that
  no real build ever co-enables (the peer-recorded case is `moirai-gpu →
  hephaestus-wgpu → moirai-runtime`, where `moirai-gpu`'s GPU feature and
  `moirai-runtime`'s GPU transport are independently gated and never on in
  the same `cargo build`); (c) the required-only graph is already acyclic, so
  the cycle only exists when feature-gated edges are *counted* as ordering
  constraints. The script's exit code should be 0 when the only unresolved
  SCCs are reachable exclusively through optional dependencies; today it is
  1, which makes the tool refuse the legitimate order it printed.

- **expected fixture behavior:** the optional-edges cycle's member count is
  `len(order_edges[n] & selected) > 0` for every `n in unresolved`, AND every
  edge in the SCC carries `optional = true` in its source manifest. The
  script separates the two cases today (it prints different messages for
  required-only vs required-and-optional cycles); it just does not act on
  the separation at the exit code.

