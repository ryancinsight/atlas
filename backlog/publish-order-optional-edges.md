<a id="publish-order-optional-edges"></a>
## ATLAS-PUBLISH-ORDER-OPTIONAL-EDGES-2026-09-04 - Decide whether optional dependencies constrain publish order [patch] - in-progress

outcome: a recorded decision (ADR) plus a publish-order tool that emits a usable total order for the whole stack instead of a 61-package cycle; a fixture cyclic-through-optional graph is handled per the ADR.
- Decision (drafting ADR 0060 `0060-publish-order-optional-dependencies.md`): optional dependencies are *not* ordering constraints for first publication — `cargo publish` doesn't require an optional dep to be registry-published, the only cycle (`moirai-gpu → hephaestus-wgpu → moirai-runtime`) is feature-gated and never co-enabled in a real build, and the required-only graph is already acyclic.
- next: the script currently exits 1 whenever unresolved SCCs exist; it should exit 0 when every unresolved SCC's edges are exclusively optional (`optional = true` in the source manifest) — the script already distinguishes required-only vs required-and-optional cycles in its messages but doesn't act on the distinction in the exit code.
- Class: `[patch]`. Risk: medium (gates first publication of the stack, and Ares A9). Depends on: nothing.
- Integrator: claude-opus-5 (this session).
