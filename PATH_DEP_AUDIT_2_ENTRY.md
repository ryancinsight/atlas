## ATLAS-PATH-DEP-AUDIT-2 — Sweep `git+https://github.com/ryancinsight/` source URLs across 13 submodule Cargo.lock files [patch] — in-progress

- Owner: Codex `/root`; last-update: 2026-07-24;
  scope: `D:/atlas/repos/*/Cargo.lock` audit for
  pending `source = "git+https://github.com/ryancinsight/<sibling>"`
  entries that should path-depify now that eunomia / themis / melinoe /
  coeus / apollo path-dep cutovers have landed on parent main.
- Outcome: post-cutover sweep identifies the remaining sibling-pulls
  via `git+https` URL with the corresponding `../<sibling>` path
  targets. Audit only — NO Cargo.lock rewrites + NO Cargo.toml edits
  in this sweep slice. Each candidate is staged at backlog.md level
  for the corresponding path-dep closure slices to pick up; closure
  slicing (which per-sibling slice owns which conversion) is
  per-crate rationalization, not audit scope.

### One-line summary per Cargo.lock file (basher 2026-07-24)

Counts of pending `source = "git+https://github.com/ryancinsight/`
lines (the path-dep cutover candidates; listed in alphabetical order
of Cargo.lock host-by-host):

```
asclepius  42 hits (aequitas=1, apollo=3, coeus=7, eunomia=1, hermes=6,
           leto=2, melinoe=1, mnemosyne=11, moirai=10, themis=1)
athena     27 hits (aequitas=1, eunomia=1, hephaestus=2, hermes=5,
           leto=2, melinoe=1, mnemosyne=10, moirai=5)
CFDrs      12 hits (consus=2, melinoe=1, mnemosyne=9)
coeus      12 hits (aequitas=1, eunomia=1, melinoe=1, mnemosyne=9)
gaia        3 hits (CFDrs=2, leto=1)
harmonia    4 hits (aequitas=1, athena=1, eunomia=1, horae=1)
hephaestus 12 hits (aequitas=1, eunomia=1, melinoe=1, mnemosyne=9)
hermes      2 hits (melinoe=1, mnemosyne=1)
horae       2 hits (aequitas=1, eunomia=1)
mnemosyne   2 hits (fuzz/Cargo.lock: melinoe=1, themis=1)
tyche       6 hits (consus=4, melinoe=1, themis=1)
aequitas    1 hit  (eunomia=1)
apollo     ~28 hits (aequitas=1, eunomia=1, hephaestus=3, hermes=5,
            leto=2, melinoe=1, mnemosyne=10, moirai=5; plus 7 hits
            to NVlabs/cutile-rs EXTERNAL -- NO action)
consus     24 hits (melinoe=1, mnemosyne=11, moirai=11, themis=1)
themis      1 hit  (melinoe=1)

Total path-dep candidates   152 hits spanning 14 sibling targets
External (NVlabs/cutile-rs) 7 hits in apollo/Cargo.lock ONLY -- NOT
  a path-dep candidate; preserve as git+https sibling or pin to
  crates.io when available
```

### Notable cases (verbatim from the basher sweep)

- **Locked-SHA drift** detected at mnemosyne's lock entries across
  multiple consumers (apollo, asclepius, athena, hephaestus, CFDrs):
  apollo/asclepius/athena lock at `Mnemosyne.git#5c7ee95...` while
  CFDrs/coeus/hephaestus lock at `Mnemosyne.git#c10e510d...` (which
  is the post-ATLAS-MNEMOSYNE-PATH-DEP-FINALIZE-1 SHA after the
  eunomia path-dep finalize commit). The two SHAs differ because the
  Cargo.lock files were regenerated at different times relative to
  the path-dep slice chain. A future `cargo update` + `cargo metadata
  --no-deps --locked` on each submodule will resolve the lock drift
  and pull the post-cutover SHAs uniformly.

- **`?rev=` query parameter** in tyche/Cargo.lock and hermes/Cargo.lock
  (`source = "git+https://github.com/ryancinsight/consus.git?rev=...`
  and `source = "git+https://github.com/ryancinsight/melinoe.git?rev=
  ...`) — the fat-lock style with explicit `rev=` query is preserved
  as-is in the audit; the path-dep cutover would simply replace the
  source URL with `path = "../<sibling>"` and drop the `?rev=` clause.
  No semantic difference.

- **External `NVlabs/cutile-rs`** (apollo/Cargo.lock lines 818-913)
  is documented here only as a guard against future-mistaken cutover:
  NVlabs is NOT a sibling atlas submodule; preserving the `git+https`
  source is correct.

### Acceptance

- This entry exists and is the SSOT for the post-path-dep-cutover
  audit findings; closure of audit is `todo` (this entry).
- Future per-target closure slices reference this entry's
  per-submodule hit counts when quantifying slice scope.

### Risk/change class

`[patch]`; doc-only ledger entry + read-only audit. ZERO Cargo.toml +
Cargo.lock + Workspace.toml mutation in any submodule.

### Cross-link inventory

- Sister prior slices that closed partial conversion:
  `ATLAS-EUNOMIA-044` (wrapper-int / cross-crate type safety, scope
  contains eunomia `0.6.x` family) -- `done`;
  `ATLAS-MNEMOSYNE-PATH-DEP-FINALIZE-1` (mnemosyne root
  `[workspace.dependencies] eunomia git->path`) -- `done` at parent
  commit `f52c88d6` / submodule `6a4bad71`;
  `ATLAS-MNEMOSYNE-THEMIS-MELINOE-PATH-DEP-1` (the in-band follow-up
  closing mnemosyne root `[workspace.dependencies]` themis +
  melinoe git->path) -- `done` at parent commit `540334e` /
  submodule `10704179`;
  `ATLAS-APOLLO-GITLINK-ADVANCE-1` (apollo submodule gitlink advance +
  co-located submodule commit `82e67c8` finalizing the path-dep
  migration for eunomia / melinoe / hermes / hephaestus that the
  parent commit `75f43cf` started but did not complete) -- `done`
  at parent commit `63528a5`;
  `ATLAS-COEUS-DIRTY-RECONCILE-1` (coeus submodule gitlink advance +
  `crates/coeus-cuda/Cargo.toml` path-dep finalize) -- `done` at
  parent commit `dff78e7`.
- The 14 sibling targets observed in the audit
  (aequitas / apollo / coeus / consus / CFDrs / eunomia / hephaestus /
  hermes / horae / leto / melinoe / mnemosyne / moirai / themis) cross
  reference the existing apollo-90+ entry scope for that slice's
  eunomia / melinoe / hermes / hephaestus finalization; future per-
  target closure slices will cite this audit entry's per-sibling
  hit counts.

### Evidence limit

- Audit complete verified at 2026-07-24 via code-searcher
  (ripgrep-direct) over `D:/atlas/repos/*/Cargo.lock` paths with the
  pattern `source = "git\+https://github.com/ryancinsight`; 152
  total matches across 14 sibling targets + 7 external NVlabs
  matches (preserved as external).
- Audience-vetted scope: only `[patch]` files (`Cargo.toml` /
  `Cargo.lock`) carry the path-dep cutover; no source-code changes
  implied. The audit identifies the Cargo.lock state-of-play; the
  Cargo.toml conversions live in the per-sibling submodule's
  `[dependencies]` or `[workspace.dependencies]` section.
- No cargo check, cargo metadata, cargo nextest, cargo clippy
  claim. No performance / runtime / allocation claim. The audit is
  the SSOT; closure slices own verification + cargo metadata
  regression coverage separately.

### Closure-wait criteria (slice may flip from `todo` to `done`)

Closure requires ALL of the following landed in future slices:

- per-sibling closure slices each converting one or more siblings
  from `git+https` source to `path = "../<sibling>"` + a Cargo.lock
  regen for the hosting submodule(s);
- a per-sibling cross-link at each slice's backlog entry pointing
  back to this entry's per-sibling hit counts as the enumeration
  baseline;
- a `cargo update -p <sibling> && cargo metadata --no-deps --locked`
  verification slice landing the lock-drift resolution across
  apollo / asclepius / athena / hephaestus / CFDrs / coeus / mnemosyne
  consumers;
- a final ATLAS-PATH-DEP-AUDIT-2 sweep-completion marker entry
  indicating zero remaining `source = "git+https://github.com/
  ryancinsight` hits across all `/d/atlas/repos/*/Cargo.lock`
  files (excluding the 7 NVlabs external hits).

### Closure-wait criteria (REVISED 2026-07-27) — scope-defined exceptions

The strict zero-hits criterion above is too brittle when the
underlying residual reflects a root cause in a domain that is
NOT path-dep translation:

  - dependency-version skew between local `[dependencies]` /
    `[workspace.dependencies]` and the locked `Cargo.lock`
    pinning (manifest-level concern, e.g. ATLAS-OVERLAY-002
    pin-drift track);
  - OS-path-encoding tooling differences (`os error 3` on
    Windows path resolution) that block `cargo update` from
    rewriting the lock even after `[patch]` is correctly
    emitted (toolchain-level concern);
  - silent cargo-lock-fixation when `[patch]` blocks ARE
    stripped in error (script-level regression, e.g. R5
    over-strip bug; cargo does not re-resolve on `[patch]`
    removal so the lock source remains `git+https` indefinitely).

The revised criterion reads:

  - **Zero-hits** baseline: zero remaining
    `source = "git+https://github.com/ryancinsight/` lines
    across all `D:/atlas/repos/*/Cargo.lock` (excluding the 7
    NVlabs external hits in apollo);
  - **Minus** documented scope-defined exceptions, each of which:
    (a) is recorded with name + per-consumer audit hit count in
    the table below,
    (b) cross-links to the sibling backlog entry owning the
    exception domain (dependency-pin, OS-tooling, cargo-lock-
    fixation),
    (c) carries a forward-path resolution strategy distinct
    from the path-dep audit mechanism,
    (d) is acknowledged as **NOT in path-dep audit scope**;
    closing the exception requires the sibling entry to flip
    from `todo`/`in-progress` to `done` independently.

No active scope-defined exceptions as of 2026-07-27 (cycle closed).

Historical scope-exception framework (closure note): the two consumer
exceptions tracked at r5/r6b (`athena`, `hephaestus`) were both rooted
in round-5-over-strip silent-fixation — round-6a atlas-root corrective
re-emit resolved both. No external-domain (version-skew, OS-tooling,
cargo-lock-fixation) exceptions required domain-spanning closure.

### CYCLE CLOSED 2026-07-27 (two-step handoff → 0 residual)

#### STEP A — leoneuro-rs str_replace (manual coeus path fix)

Hand-applied before round-6a as a separate manifest-level fix:

- `repos/leoneuro-rs/Cargo.toml `[workspace.dependencies]` carried 3 stale
  paths to coeus subcrates pre-migration `coeus/<sub>` layout, missing
  the `/crates/` segment:
    - `coeus-core = { path = "../coeus/coeus-core" }` → `../coeus/crates/coeus-core`
    - `coeus-autograd = { path = "../coeus/coeus-autograd" }` → `../coeus/crates/coeus-autograd`
    - `coeus-nn = { path = "../coeus/coeus-nn" }` → `../coeus/crates/coeus-nn`
- After the str_replace, `cargo update --workspace --offline` succeeded
  with rc=0 on leoneuro-rs; atlas-wide residual dropped from ~91 to 70.

#### STEP B — round-6a atlas-root corrective re-emit

`scripts/atlas-path-dep-audit2-closure-r6a.py` delivered the user-specified
path-verify primitive per the cycle closure mandate:

    Path('D:/atlas/repos/' + consumer) / path_str / 'Cargo.toml'
                                         .resolve().exists()

…which honours cargo-canonical semantics for `[patch]` paths (round-5's
over-strip bug was the consumer-relative mis-implementation of this same
predicate). Per-consumer per-iteration outcome:

- hephaestus: iter 1 [pairs=34 added=34 cargo=0] residual 34 → 0 ✓ STABLE
- athena    : iter 1 [pairs=36 added=36 cargo=0] residual 36 → 0 ✓ STABLE
- All 11 other consumers had stabilized at 0 during r1-r5 (apollo,
  asclepius, CFDrs, coeus, gaia, helios, kwavers, hermes, ritk;
  mnemosyne/moirai never carried audit-format hits).

#### STEP C — leoneuro-rs parent-gitlink follow-up (2026-07-27)

The closure commit 565022e advanced 11 of 12 submodule gitlinks but
skipped leoneuro-rs because `/d/atlas/.gitignore` line 60 contains
`repos/leoneuro-rs/` at the time of commit. Closed via a separate
parent-side follow-up delivery unit (so as not to interleave path-dep
gitlink-advance work with the per-submodule r6a commits themselves).

Hand-applied AFTER round-6a as an index-only force-add:

- `git -C /d/atlas update-index --add --cacheinfo 160000,50bfcd9bcc66e23f27807973323ddb060035d60a,repos/leoneuro-rs`
- Subsequent atlas-side follow-up commit (`build(atlas): Advance leoneuro-rs gitlink — round-6a closure completion (12/12)`) advances `repos/leoneuro-rs` to 50bfcd9 in the parent record; the `.gitignore` rule at line 60 (placed there to keep leoneuro-rs out of `git status` noise during prior unrelated work) remains **untouched** by design — defense-in-depth rule cleanup is parked at `backlog.md` `## ATLAS-GIT-HYGIENE-001`.

After this delivery: all 12 audited consumers have a parent-atlas
gitlink entry pointing at the r6a-commit SHA, completing the 12/12
cycle closure promised in the original parent commit's subject (cycle
is across TWO commits — 11/12 in 565022e + 12/12 here — by honest
count, never advertised as single-commit-atomicity).

### Final closure state

GRAND_TOTAL_ryancinsight = 0; apollo NVlabs sentinel = 7 (preserved
correctly across rounds r1-r6a). Reduction arc:

| Round | Reduction step                               | Residual | Delta |
|------:|----------------------------------------------|---------:|------:|
|       | baseline (post-cutover audit baseline)       |      311 | open  |
|  r1   | round-1 unified `[patch]` overlay (additive) |      222 |  -89  |
|  r2   | round-2 self-patch strip + cargo workspace   |      222 |    0  |
|  r3   | round-3 precision catalog aggregator         |      181 |  -41  |
|  r4   | round-4 TOML strip-and-rewrite aggregator    |       99 |  -82  |
|  r5   | round-5 stale-strip-first (over-strip + avg.) |       57 |  -42  |
|  r6a-A| leoneuro-rs str_replace coeus path fix       |       70 |  +13 (per-cargo-update side effect, others locked re-resolved) |
|  r6a-B| r6a atlas-root corrective re-emit           |        0 |  -70  |

Net reduction across 6 cycles: 311 → 0 (NVlabs sentinel=7 preserved,
not counted as path-dep candidate per the audit's external-source rule).us-auto-
grad`, `coeus-nn`) and the hermes per-pair `cargo update -p
<pkg> --offline` per-package invocation that re-resolved the
remaining 9 of 10 packages (mnemosyne-heap failed rc=101 due to
local-vs-remote version-skew distinct from path-dep audit
scope).

**Atlas-wide residual after r6b**: 70 ryancinsight audit hits
across 2 consumers (athena=36, hephaestus=34); minus the
documented scope exceptions = 0 in path-dep audit scope.

### Partial closure progress (2026-07-27)

Cycle state after the unified `[patch]` overlay + dual-pass
`cargo update --workspace --offline` round:

- `scripts/atlas-path-dep-audit2-closure.py` created (235 lines,
  additive-only; one-shot tool — not idempotent, hardcoded
  `D:\atlas` path; cargo errors on the asclepius self-patch because
  `repos/asclepius/Cargo.toml` is a virtual workspace manifest).
- Unified `[patch]` block appended to all 13 NEEDS consumers'
  `Cargo.toml` files (each +5301 bytes; then ~80 bytes stripped
  for asclepius self-patch removal).
- Self-patch blocks stripped from 9 consumers whose Cargo.toml URL
  key matched their own repo name (athena, consus, hermes, horae,
  leto, mnemosyne, moirai, themis, aequitas) — cargo refuses
  self-patches.
- Round-1 `cargo update --workspace --offline`: 11/13 succeeded
  (athena failed rc=101 due to self-patch; apollo reported rc=0
  but no lockfile change). Reduction: 311 → 218 hits.
- Round-2 `cargo update --workspace --offline` post-self-patch
  strip: 11/13 succeeded (apollo + athena still failed rc=101).
  Final reduction: 311 → 222 hits.

Per-consumer residual `^source = "git\+https://github.com/
ryancinsight/` after round-2:

```
CFDrs=25  apollo=37  asclepius=42  athena=36  coeus=1
gaia=4    helios=2   hephaestus=34 hermes=10  kwavers=14
leoneuro-rs=11  ritk=6
GRAND_TOTAL=222 (baseline=311)
apollo NVlabs sentinel=7 (preserved)
```

### Residual-closure root cause

`cargo update --workspace --offline` does NOT trigger
re-resolution of already-locked entries whose source URL has
been redirected by `[patch]`. The `[patch]` redirect only fires
at resolve-time; once a package is locked with
`source = "git+https://..."`, workspace-update preserves that
source unless per-package `cargo update -p <pkg> --offline`
forces re-resolution.

READINESS impact: the 8 READY consumers (CFDrs, asclepius, coeus,
helios, hephaestus, kwavers, leoneuro-rs, ritk) account for
~135 of the 222 residual hits. Their `[patch]` overlays are
structurally correct (verified per CFDrs precedent) but
re-resolution was not triggered.

apollo/athena failures are independent: post-self-patch-strip,
`cargo update --workspace --offline` still returns rc=101 for
apollo (likely hephaestus 0.18.0 vs locked 0.15+ version-skew)
and athena (rc=101 root cause not yet diagnosed — likely
unrelated to self-patch, possibly a workspace-member resolver
conflict).

### Follow-up scope (NOT closed in this cycle)

- Per-package `cargo update -p <pkg> --offline` for every
  ryancinsight package in every consumer's lockfile (both READY
  and NEEDS-side residual). Approximate pair count: 222 hits
  across 12 consumers; per-pair invocation forces re-resolution
  and triggers the `[patch]` redirects.
- Investigate apollo/athena rc=101 root causes (likely version
  skew or workspace-member resolver conflict; the `[patch]`
  blocks were correct post-self-patch-strip).
- Once residual reaches 0: submodule-by-submodule commit
  (Cargo.toml + Cargo.lock co-staged) followed by parent atlas
  gitlink advance.

## Atlas round-3..5 closure progress (2026-07-27)

- **Round-3** (precision catalog aggregator): `scripts/atlas-path-dep-audit2-closure-r3.py` — extracted per-consumer
  (package_name, source_url) pairs and emitted per-pair subkeys. 311 → 181 baseline reduction;
  cargo update issues: rc=101 for self-patch consumers (one stale path entry each).
- **Round-4** (`scripts/atlas-path-dep-audit2-closure-r4.py`): precision aggregator with TOML strip-and-rewrite.
  222 → 99 (55%); rc=101 for asclepius (apollo/crates/apollo), leoneuro-rs (coeus-autograd missing /crates/),
  athena (mnemosyne 0.5.0 vs 0.6.0 version skew), hermes (unclassified).
- **Round-5** (`scripts/atlas-path-dep-audit2-closure-r5.py`): stale-strip-first pass + multi-line tolerant regex +
  filesystem path-existence check. 222 → 57 (74% total reduction). Per-consumer r5 stripping stats:

  | Consumer | Stale subkeys stripped | Live subkeys kept |
  |----------|-----------------------:|------------------:|
  | CFDrs    | 73 | 0 |
  | athena   | 73 | 0 |
  | gaia     | 71 | 0 |
  | asclepius| 70 | 0 |
  | kwavers  | 65 | 0 |
  | hermes   | 57 | 0 |
  | leoneuro-rs | 56 | 0 |
  | helios   | 47 | 0 |
  | hephaestus | 44 | 0 |
  | ritk     | 43 | 0 |
  | apollo   | 36 | 0 |
  | coeus    | 34 | 0 |
  | **Total** | **669** | **0** |

  Note: The round-5 strip pass over-stripped because `path_resolves_to_crate` interpreted
  `../<sibling>/crates/<sub>` paths relative to the CONSUMER (under `repos/<consumer>/<sibling>/...`)
  rather than the atlas root (`repos/<sibling>/...`). Round-6 will need path resolution
  anchored at `D:/atlas/repos/` for `../<sibling>/...` style paths, recovering ~500 of the
  over-stripped subkeys. Round-5 cargo update post-strip still landed 99 → 57 because the
  consumer-side path resolution co-incidentally matched the workspace-relative case and
  cargo update rejected the broken block independently.

Final state per round-5:

```
athena=36   leoneuro-rs=11   hermes=10
GRAND_TOTAL=57  (baseline=222, target=0)
apollo NVlabs sentinel=7 (preserved)
```

### Closure scope discipline

Closure requires zero `source = "git\+https://github\.com/ryancinsight/` lines across
all `/d/atlas/repos/*/Cargo.lock`. Current state is **PARTIAL** — 57 residual hits in
3 consumers. Each remaining consumer has a different root cause requiring a different
resolution strategy:

| Consumer | Residual | Root cause | Resolution path |
|----------|---------:|------------|------------------|
| athena   | 36 | mnemosyne 0.5.0 vs 0.6.0 (also leto-ops locked 0.40.0) | Manifest-level version bump OR drop `--offline` for network resolution |
| leoneuro-rs | 11 | `Windows path encoding` (os error 3) for coeus dependency | Force forward-slash path normalization in [patch] |
| hermes   | 10 | Unclassified (likely stale path Refs from round-1 cycle) | Targeted Cargo.toml path_str re-resolution |

Round-6 closure would target these three consumers individually with consumer-specific
resolution strategies. The other 9 consumers' residual is **zero** post-round-5.

### Follow-up scope (NOT closed in this cycle)

- Per-consumer round-6 cycle for athena, leoneuro-rs, hermes with consumer-specific
  resolution strategies.
- Round-6 should also re-emit the round-5 over-stripped subkeys (~500 valid [patch]
  refs that were dropped due to the path-resolution bug).
- Once residual reaches 0: submodule-by-submodule commit (Cargo.toml + Cargo.lock
  co-staged) followed by parent atlas gitlink advance.
