<a id="mnemosyne-pin-campaign-stranded"></a>
## ATLAS-MNEMOSYNE-PIN-CAMPAIGN-STRANDED-2026-09-06 - A provider-pin campaign stalled undelivered in five members [patch] - todo

- **outcome:** the mnemosyne pin advances land on each member's default branch,
  or are deliberately discarded as superseded. No member sits on an unmerged
  provider-pin branch, and the atlas gitlinks that depend on them stop being
  unpushable.
- **surfaced from the far end.** An atlas commit advancing gaia's gitlink pinned
  `8060ef0e`, which is on `fix/gaia-lock-stale-rev` and not on gaia's
  `origin/main`. The meta-repo's gitlink guard refused the push — correctly: a
  gitlink naming a commit outside the member's default branch breaks resolution
  for every consumer. The pin was not the defect; the undelivered branch was.
- **measured 2026-09-06**, pushed branches with no merge:

  | Member | Branch | Commits ahead of main | PR |
  | --- | --- | --- | --- |
  | gaia | `fix/gaia-lock-stale-rev` | 25 | [#47](https://github.com/ryancinsight/gaia/pull/47) opened 2026-09-06, **conflicting** |
  | hermes | `build/mnemosyne-phase12` | 17 | none |
  | leto | `build/leto-mnemosyne-source-identity` | 17 | none |
  | kwavers | `chore/kwavers-xtask-mnemosyne-allocator` | 8 | none |
  | athena | `feat/mnemosyne-global-allocator-integration` | 2 | none |

  69 commits of provider-pin work across five members, none of it delivered,
  four of them without even a pull request. `git_discipline: cadence` calls an
  unmerged branch integration debt precisely because it compounds: gaia's is
  now conflicting with its own `main`, so the first cost of the delay is a
  rebase that did not exist when the work was done.
- **the shape is one campaign, not five coincidences.** Each branch is a run of
  `build(deps): Advance mnemosyne rev to <sha> (Phase N)` commits. Advancing a
  provider across the stack is a co-evolution sweep
  (`architecture_scoping`: pin discipline) — it lands per member in dependency
  order or it is not a sweep, and a per-member branch that accumulates phases
  without merging is the sweep's defect output.
- **correction, 2026-09-06: the framing above is wrong for gaia, and the
  rebase is what showed it.** gaia's branch chased `f532b0e`, the pre-merge tip
  of mnemosyne's `perf/mnemosyne-scratch-release`. That branch has since landed
  — mnemosyne PR #128, merged to `main` as `e8e825f` — and gaia's `main`
  already pins `e8e825f`. So the single `Cargo.toml` conflict was `main`
  holding the published commit against the branch holding an unpublished
  ancestor of it, and merging would have moved gaia *off* mnemosyne's default
  branch. gaia#47 is closed, the branch deleted, the atlas gitlink repointed at
  gaia `origin/main` (`ba5a8fd83`). Nothing lost: every earlier phase is an
  ancestor of the same landed work.
- **the real defect the campaign left behind.** Two members' *default branches*
  pin a mnemosyne rev that is not on mnemosyne's `main`:

  | Member | Pinned rev | Lives on |
  | --- | --- | --- |
  | `coeus` | `03fe32f4` | `feat/phase10-improvements`, unmerged |
  | `kwavers` | `03fe32f4` | `feat/phase10-improvements`, unmerged |

  This is the metis and gaia-gitlink defect one level down: a dependency
  resolving to a commit outside the provider's default branch. Either
  mnemosyne's `feat/phase10-improvements` lands, or both members repoint at
  `e8e825f`. Each repoint carries a lockfile regeneration.
- **resolved 2026-09-06.** mnemosyne #123 is *closed*, not pending, so there
  was nothing to wait for. Both members repointed to `e8e825f4`:
  [Coeus#376](https://github.com/ryancinsight/Coeus/pull/376) and
  [kwavers#723](https://github.com/ryancinsight/kwavers/pull/723), each with its
  lock regenerated outside the overlay and verified under `--locked`.
- **the kwavers pin was breaking the build, not only the provenance.** Resolving
  `03fe32f4` needed a network fetch that libgit2 could not complete, so
  `cargo check -p kwavers-medium` failed with `class=Net (12); code=Eof (-20)`
  while `git ls-remote` against the same URL succeeded. The error named the
  network; the cause was a rev on a dead branch. Worth recording as a
  diagnostic signature: a cargo transport error on a first-party git source is
  a pin question before it is a connectivity question.
- **a two-day-old increment was recovered on the way.** Both kwavers checkouts
  held byte-identical uncommitted work delegating the six derived elastic
  identities to `proteus::elastic::IsotropicModuli` — the residual copy
  [`#proteus-elastic-ssot`](backlog.md#proteus-elastic-ssot) is about.
  Rebased onto the repointed `main` and delivered as
  [kwavers#724](https://github.com/ryancinsight/kwavers/pull/724). Only
  `CHANGELOG.md` conflicted — an append against an append — and both entries
  were kept. The gate it could never run then passes now: clippy clean, 215
  nextest, 4 doctests.

  Clippy earned its place on the way. Delegating made the accessors
  fallible-underneath, so six public functions gained a reachable panic and
  none documented it; `missing_panics_doc` caught the two with `expect`
  directly in their own body, and the other four differ only in that the panic
  is one call deeper. All six now carry `# Panics`. The duplicate copy in the
  second kwavers checkout was verified superseded by what landed — a strict
  subset — and cleared.
- **remaining branches** (`hermes` 17, `leto` 17, `athena` 2, and kwavers's 23)
  are phase series with no PR. gaia's turned out to be superseded rather than
  stalled, so each of these needs the same check — does `main` already pin the
  merged result? — before anyone rebases 17 commits.
- **then:** a PR per remaining member, in dependency order, each gated by its
  own lockfile check — these branches change dependency resolution, so that
  check is the one that matters and must not be skipped.
- **open question for the ADR:** whether these advances should ride per-member
  branches at all, or be produced by the mechanized integration sweep
  (`toil automation`) that pin discipline already calls for. Five stalled
  branches is evidence for the latter.

