<a id="atlas-book-figure-closure-2026-08-21"></a>
## ATLAS-BOOK-FIGURE-CLOSURE-2026-08-21 — Restore generated validation figures [patch] — in-progress

- **Audit evidence:** the independent provider generator dry-run found expected
  figure artifacts absent from the committed provider trees: RITK `77`,
  Kwavers `99`, Eunomia `17`, Coeus `12`, and Horae `8`. Tyche has a separate
  seven-figure gap. Helios's inspected generator dry-run found all `46`
  expected artifacts. The root Markdown-link check is a separate oracle and
  currently reports `missing-figures=0` at the committed Atlas gitlinks.
- **Acceptance:** each referenced figure is produced by the provider's
  canonical generator, committed at the provider source head, and covered by
  a deterministic existence check in the provider's book gate. No hand-made
  or placeholder assets are accepted.
- **Execution:** Tyche's isolated sidecar completed provider commit `4cd0899`
  and opened PR [#36](https://github.com/ryancinsight/tyche/pull/36) at that
  exact head. The Atlas gitlink commit `4ee9128` is held until the provider PR
  merges and its hosted checks complete; the remaining provider sets follow as
  disjoint increments.
- Eunomia's disjoint provider slice is committed at `01179a9` on branch
  `docs/eunomia-book-figures` and opened as PR
  [#73](https://github.com/ryancinsight/eunomia/pull/73). The commit adds the
  17 expected deterministic SVG outputs, one canonical generator, a local
  reference checker, reproducibility/negative tests, and a deployment
  prerequisite for the figure gate. Local generator/checker tests and
  `mdbook build docs/book` pass. The peer-dirty Eunomia main checkout remains
  untouched; the Atlas gitlink is held pending exact-head hosted checks and
  merge.
- Local `mdbook test` and `cargo build --locked -p eunomia` remain
  environment-blocked in the isolated lane because the inherited Atlas
  development overlay re-resolves the provider under `--locked`; this is
  recorded as a verification limit, not treated as a provider failure.
- **Eunomia hosted hold:** PR #73 is open at exact head
  `01179a9d98e7d3ccbf118b38b65e5c1c675490b8`, based on `834bd3b443dd050e9a1ec0c5d837645db33ac787`.
  It is `MERGEABLE` but `UNSTABLE`; figure, Rust, NumPy, supply-chain, and
  related checks remain queued, while `recurseml/analysis` is terminal error.
  Pages still serves the prior merged default `22a02b1`; no provider merge or
  Atlas pointer advance is authorized.
- **Eunomia merged and gitlink advanced (2026-08-23):** PR #73 reached
  terminal-success on figure, Rust, NumPy, and supply-chain checks at the
  exact head (`01179a9d98...`) and was merged at `35158d1`. Post-merge CI and
  Pages at the merged default are terminal (6/6 targets green) and the live
  book is HTTP 200. The Atlas eunomia gitlink advances `22a02b1` →
  `35158d1` (index-level pointer move; peer-dirty checkout untouched).
  Eunomia's set of the book-figure closure is closed by this increment.
- **Hosted hold:** PR #36 remains open at
  `4cd0899a301db4a934ae32bf40db00bb56836c64`; Deploy mdBook run
  `32492568641` and CI run `32492568124` are queued, with `recurseml/analysis`
  error and CodeRabbit pending. The live site is HTTP 200 but its
  `figures/ch01/fig01_1_parameter_spaces.svg` URL is HTTP 404 and its
  `Last-Modified` predates the PR, so no pointer advance is authorized.
- **Tyche merged and gitlink advanced (2026-08-23):** PR #36 reached
  terminal success on all required hosted checks at the exact head
  (`4cd0899a30`: Check book figures, verify, supply-chain, deploy/Build book)
  and was merged at `e5c6a39`. Post-merge CI and Pages at the merged default
  are terminal (8/8 checks green) and the live book is HTTP 200. The Atlas
  tyche gitlink advances `7d636471` → `e5c6a39` (index-level pointer move;
  peer-dirty checkout untouched). Tyche's set of ATLAS-BOOK-FIGURE-CLOSURE
  is closed by this commit.

