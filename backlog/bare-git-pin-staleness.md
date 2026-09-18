<a id="bare-git-pin-staleness"></a>
## ATLAS-BARE-GIT-PIN-STALENESS-2026-09-08 - A version-less git dependency freezes at its first resolution [patch] - todo

Parent: [`#slop-burndown`](backlog.md#slop-burndown).

- **outcome:** no first-party dependency is declared as a bare `git = "..."`
  without a version requirement, so `cargo update` can advance it and the
  conformance scan counts any that reappear.
- **the mechanism:** `helios` declared `eunomia = { git = "..." }` with no
  `version`. Cargo then locks whatever revision resolved first and has no
  requirement that would ever make it move — not stale by a sweep's neglect but
  by construction. It sat at `3a8836e3`, a revision predating the
  `eunomia-derive` crate: helios's lock contained **no `eunomia-derive` entry
  at all**.
- **what it looked like from the outside.** `hephaestus-core` had moved on to
  using eunomia's `Pod`/`Zeroable` derive macros, so helios's build failed
  *inside a dependency* with `cannot find derive macro Pod in this scope`. That
  reads as a broken upstream, and it is not one — `hephaestus-core` compiles in
  its own tree at default features and at `--no-default-features`. Four
  diagnostic steps went past hephaestus before the lock was the suspect. Worth
  recording as a signature: **a derive macro missing from a dependency's build
  is a resolution question, not an upstream defect**, and the cheap check is
  whether the providing crate appears in the lock at all.
- **`cargo update -p eunomia`** advances it to `8e18d6d8`, adds
  `eunomia-derive`, and clears four of five errors in `helios-gpu`
  (`b525e8a`).
- **the class, not the instance:** a bare `git =` requirement is the pin-width
  rule's other failure mode. `architecture_scoping` covers over-tight (`=`)
  requirements manufacturing resolver conflicts; this is the opposite — no
  requirement at all, so nothing ever forces movement, and the divergence is
  invisible until a consumer needs something the frozen revision lacks. Both
  are the same defect in width. The scan should count version-less first-party
  git dependencies, and the sweep should treat them as it treats an `=` pin.

