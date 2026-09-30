<a id="atlas-version-coherence-sweep-2026-09-30"></a>
## ATLAS-VERSION-COHERENCE-SWEEP-2026-09-30 — Follow melinoe, themis and the horae rename into every consumer [correctness] — todo
- priority: correctness
- outcome: `scripts/atlas-stack-overlay.py check` reports **aligned** on the stack's own pins, so the `Stack overlay coherence` and `Toolchain preflight` jobs go green on atlas `main`.
- scope: the `Cargo.toml` requirement and `Cargo.lock` of the twelve members named below. No source change.
- **why (measured, 2026-09-30 from the atlas `main` run `36775327684`):** two providers advanced their workspace version and a third renamed its registry package, and no consumer followed. The gate reports **15 requirement lags** and **3 unresolved edges**.
  - `melinoe` is at **0.10.0**; five members still require `0.9.0`: CFDrs, apollo, gaia, mnemosyne, moirai.
  - `themis-topology` is at **0.11.0**; eleven members still require `0.10.1`: CFDrs, apollo, coeus, consus, helios, hephaestus, hermes, kwavers, leto, mnemosyne, moirai.
  - `horae` now publishes its registry package as **`horae-time` 0.1.0** (the *library* keeps the name `horae`, so every `use horae::` path is unchanged). harmonia, helios and kwavers still request `horae`, so the overlay cannot resolve those edges at all. This is the **rename half** of a cargo dependency rename: the consumer needs `package = "horae-time"`, and the dependency key stays `horae`.
- **dependency order, which is the whole difficulty.** A git dependency resolves against the *published* manifest of its provider, so a consumer cannot be fixed until the provider's own requirement has landed. Measured while attempting it:
  1. **mnemosyne** — its `mnemosyne-local` still requires `melinoe = "^0.9.0"`, which blocks *gaia*.
  2. **gaia** — blocked by (1).
  3. **helios, kwavers** — blocked by (2) through `helios-math -> gaia`, plus their own `themis` and `horae` edits.
  4. **CFDrs, apollo, moirai** — each carries both a `melinoe` and a `themis` bump; check whether mnemosyne or themis gates them before starting.
  5. **coeus, consus, hephaestus, hermes, leto** — `themis` only, so the shallowest links in the chain.
- **done:** harmonia (#56, merged) — the only member of the three with nothing gating it, because harmonia has no `melinoe` or `themis` requirement at all.
- **the measurement trap, recorded because it already cost a wrong conclusion.** `atlas-stack-overlay.py check` run in the shared working tree reports **aligned**, and it is wrong: the local member checkouts sit *behind* their pins (horae at `fe3c4d7` against a pin of `5b559423`), so the local tool measures a tree in which horae still publishes `horae`. CI materialises the **pins**. Every overlay verdict must be taken against the pins — read each member's manifest with `git show <pin>:Cargo.toml`, never from the checkout.
- next: start at (1) and land one member at a time; each unlock is a published requirement, so several can be in flight but the verification of each depends on its predecessors landing.
