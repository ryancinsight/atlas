<a id="atlas-book-caller-pins-2026-08-20"></a>
## ATLAS-BOOK-CALLER-PINS-2026-08-20 — Repin provider mdBook callers [patch] — in-progress

**Coordinator claim (2026-08-21):** Atlas-Codex owns the root-only pointer and
evidence synchronization for Proteus, Aequitas, and Hermes. Claimed scope is
`repos/proteus`, `repos/aequitas`, `repos/hermes`, and this item in
`backlog.md`; provider source, nested checkout work, and peer PM files are
excluded.

The provider workflow audit found 20 current `main` callers still pinned to
pre-fix revisions of the reusable Atlas book workflow. Apollo and Coeus now
carry the repin on their merged defaults; Hephaestus and RITK carry it in
their active PRs. The
remaining 16 provider-scoped workflow PRs are published from each current
default without touching the dirty nested checkouts:

- Aequitas [#38](https://github.com/ryancinsight/aequitas/pull/38),
  Asclepius [#23](https://github.com/ryancinsight/asclepius/pull/23),
  Athena [#16](https://github.com/ryancinsight/athena/pull/16),
  Consus [#52](https://github.com/ryancinsight/consus/pull/52),
  Eunomia [#71](https://github.com/ryancinsight/eunomia/pull/71),
  Harmonia [#8](https://github.com/ryancinsight/harmonia/pull/8),
  Hermes [#58](https://github.com/ryancinsight/hermes/pull/58),
  Horae [#24](https://github.com/ryancinsight/horae/pull/24),
  Hyperion [#22](https://github.com/ryancinsight/hyperion/pull/22),
  Iris [#17](https://github.com/ryancinsight/iris/pull/17),
  Melinoe [#19](https://github.com/ryancinsight/melinoe/pull/19),
  Mnemosyne [#67](https://github.com/ryancinsight/Mnemosyne/pull/67),
  Moirai [#146](https://github.com/ryancinsight/Moirai/pull/146),
  Proteus [#16](https://github.com/ryancinsight/proteus/pull/16),
  Themis [#28](https://github.com/ryancinsight/themis/pull/28), and
  Tyche [#33](https://github.com/ryancinsight/tyche/pull/33).

**Acceptance:** every registered provider workflow resolves the exact shared
staging implementation `20c9398`; each provider's required hosted book gate
is terminal green; then close the PRs and record the merged defaults before
advancing any Atlas pointer. No source or book behavior changes are in scope.

**Exact-head collection (2026-08-20):** Horae #24 at
`a3b79fb` has CI `32418584339` and Deploy mdBook `32418584938` green;
Hyperion #22 at `7dca41e` has CI `32418586348` and Deploy mdBook `32418586803`
green; Themis #28 at `28bf210` has CI `32418600576` and Deploy mdBook
`32418601066` green; Proteus #16 at `653772e` has CI `32418598026` and Deploy
mdBook `32418598676` green; and Tyche #34 at `c481e05` has CI `32425417532`
and Deploy mdBook `32425418118` green. These results are bound to the exact
PR heads and do not authorize default-pointer updates.

**Integration:** the authenticated GitHub CLI merged all five exact-green PRs
with expected-head guards: Horae #24 → `d014929`, Hyperion #22 → `91df53e`,
Themis #28 → `c441acf`, Proteus #16 → `73c6c81`, and Tyche #34 → `89194f3`.
The connector's parallel merge calls returned HTTP 403, but no merge was
claimed until the authenticated merge results were verified. Post-merge CI,
Deploy mdBook, and Pages runs are queued at each exact merge commit:
Horae `32434846095`/`32434846467`/`32434845162`, Hyperion
`32434851255`/`32434851473`/`32434850406`, Themis
`32434855247`/`32434855744`/`32434854004`, Proteus
`32434859559`/`32434860258`/`32434857538`, and Tyche
`32434861620`/`32434862314`/`32434860567`. No Atlas pointer is advanced until
these post-merge runs are terminal and the deployed pages are verified.
Tyche's superseded duplicate PR #33 was closed and its branch deleted.

**Second integration batch (2026-08-20):** exact-head green PRs merged with
expected-head guards: Mnemosyne #67 → `9da9f92`, Aequitas #38 → `14fdd44`,
Asclepius #23 → `ce3fea3`, Eunomia #70 (NumPy feature contract) → `c7435a2`
followed by #71 (workflow pin) → `22a02b1`, and Moirai #145 (positioned I/O)
→ `c186fd9` followed by #146 (workflow pin) → `7f75f5e`. Post-merge runs are
queued at the exact defaults: Mnemosyne CI/Deploy `32435012042`/
`32435012409`, Aequitas CI/Deploy/Pages `32435015846`/`32435016154`/
`32435015448`, Asclepius CI/Deploy/Pages `32435020135`/`32435020483`/
`32435018341`, Eunomia CI/Deploy `32435024973`/`32435025288`, and Moirai
Python/Deploy `32435032989`/`32435033356`. Atlas pointers remain unchanged
until terminal post-merge evidence is collected.

**Third integration batch (2026-08-20):** the stacked RITK pipeline was
merged in dependency order: #201 → `3bf61e3`, #203 was retargeted from the
merged feature branch to `main` and then merged → `8196809`. Hephaestus #214
→ `7e09efa`, Hermes #58 → `c647368`, Iris #17 → `8700418`, and Melinoe #19
→ `8a67d14` also merged with expected-head guards. Post-merge runs are queued:
RITK CI/Python/Deploy `32435204760`/`32435204737`/`32435205077`, Hephaestus
WGPU/Metal/ROCm/CUDA/Deploy `32435207406`/`32435207407`/`32435207414`/
`32435207429`/`32435207800`, Hermes CI/Deploy/Pages
`32435209980`/`32435210250`/`32435209388`, Iris CI/Deploy/Pages
`32435213271`/`32435213613`/`32435212802`, and Melinoe Deploy/Pages
`32435216434`/`32435215430`. Atlas pointers remain unchanged until those
default-head gates are terminal and live pages are checked.

RITK's stacked book adoption is now the same merged-default gate: the prior
`8196809` snapshot was superseded by #204's `b35c9331`; its three post-merge
runs above remain uncollected.

**Helios caller integration:** workflow PR
[#64](https://github.com/ryancinsight/helios/pull/64) was marked ready after
its Rust workspace, Python bindings, benchmark, and book-build checks passed,
then merged from exact head `9a590ffaa65b3afc61b36f0aec2239014b6d17ae` at
default `e886754d369c56925bab558dae7c6cebf94a0df1`. The post-merge CI run
`32436531185` is queued. The workflow-only change did not trigger a new Pages
run; the next default book deployment remains the required live-page check.

**Fourth integration batch (2026-08-21):** the post-merge default gates for
Proteus, Aequitas, and Hermes are terminal-successful. Proteus run
`32434857538`, Aequitas run `32435015448`, and Hermes run `32435209388` have
completed CI, book deployment, and reporting jobs successfully. Their live
Pages endpoints return HTTP 200 with the expected titles at
`https://ryancinsight.github.io/proteus/`,
`https://ryancinsight.github.io/aequitas/`, and
`https://ryancinsight.github.io/hermes/`. Atlas advances the three gitlinks to
the exact current defaults `73c6c813`, `14fdd44c`, and `c6473688` respectively.
No provider source or nested checkout is changed. Themis has terminal build
jobs but its live endpoint could not complete TLS verification in the audit;
Horae, Hyperion, Asclepius, Melinoe, Leto, and Iris still have queued deploy
jobs, while Mnemosyne and Moirai returned 404 at their Pages endpoints. None
of those pointers advances in this increment.

**Coordinator claim (2026-08-21, second slice):** Atlas-Codex now owns the
root-only pointer and evidence synchronization for Themis, Consus, and
Eunomia. Claimed scope is their three root gitlinks plus this item in
`backlog.md`; no provider source, nested checkout, or Consus peer checklist is
included.

**Fifth integration batch (2026-08-21):** exact current-default evidence is
now terminal for Themis, Consus, and Eunomia. Themis CI, book, and Pages runs
`32434855247`, `32434855744`, and `32434854004` all succeeded; Consus CI,
documentation, and Pages runs `32436374114`, `32436374130`, and
`32436372915` all satisfied their jobs; Eunomia CI and book/Pages runs
`32435024973` and `32435025288` succeeded. Live Pages checks return HTTP 200
with expected titles for `https://ryancinsight.github.io/themis/`,
`https://ryancinsight.github.io/consus/`, and
`https://ryancinsight.github.io/eunomia/`. Atlas advances their gitlinks to
`c441acff`, `1000699f`, and `22a02b18`. No nested checkout or provider source
is changed. The remaining queued or 404 endpoints stay unadvanced.

**Live URL correction (2026-08-21):** the prior lowercase probes for Mnemosyne
and Moirai were not canonical GitHub Pages paths. Their repository names are
case-sensitive in the deployed paths: `/Mnemosyne/` and `/Moirai/` return HTTP
200 with the expected book titles. The earlier 404 observation is retained as
the lowercase-probe result, not as a deployment failure.

**Coordinator claim (2026-08-21, third slice):** Atlas-Codex owns the
root-only pointer and evidence synchronization for Mnemosyne and Moirai.
Claimed scope is their two root gitlinks plus this item in `backlog.md`; no
provider source, nested checkout, or peer PM file is included.

**Sixth integration batch (2026-08-21):** Mnemosyne's Rust verification run
`32435012042` and book/Pages run `32435012409` completed all jobs
successfully; Moirai's binding checks `32435032989` and book/Pages run
`32435033356` also completed successfully. Canonical live Pages checks return
HTTP 200 with the expected titles at
`https://ryancinsight.github.io/Mnemosyne/` and
`https://ryancinsight.github.io/Moirai/`. Atlas advances the two gitlinks to
`9da9f92e3` and `7f75f5e6`. No provider source or nested checkout changes.

**Residual exact-head sweep (2026-08-21):** after refreshing all provider
remotes, the exact-head audit reports 13 intentional drifts. The held defaults
are Horae `d1332267`, Hyperion `3bc0e43d`, Themis `2c074987`, Tyche
`7d636471`, Helios `e886754d`, Harmonia `c762c8ad`, Asclepius `a38b8b50`,
Eunomia `834bd3b4`, Moirai `ff56d602`, Leto `fc0648ee`, Apollo `fd9ecd02`,
Iris `636a2613`, and Kwavers `4d61dbfb`. The merged-default required runs for
Themis, Tyche, Eunomia, Moirai, and Apollo are queued; Harmonia CI remains
queued while its Pages run `32474560873` is cancelled. The earlier Horae,
Hyperion, Asclepius, Leto, and Iris Pages runs remain the only evidence for
those held defaults. Helios's default CI
`32436531185` is terminal, but its current source PR #69 is at stacked head
`7a973331` and remains queued. Kwavers current-default workflows
remain unverified at `4d61dbfb`; the earlier workflows at `8fc69970` and
older heads do not prove the current default. No pointer advances until each
provider's exact hosted evidence and canonical live-page check satisfy the
acceptance oracle.

**Eighth integration batch (2026-08-23):** Horae `abe42e5d`, Hyperion
`3bc0e43d`, Leto `fc0648ee`, and Iris `636a2613` each carry terminal CI and
Pages deployment success at the exact current head with live Pages HTTP 200
and expected titles; Atlas advanced all four gitlinks (commit `d9e7315`).
CFDrs advanced separately to `a70faea6` (commit `43fe895`) and, after Stage B
merged, awaits post-merge CI `32611718091` before advancing to `c5f9fa2c`.

**Seventh integration batch (2026-08-22):** Gaia PR #33 merged at default
`9b476fec` (post-merge CI + mesh book terminal, live Pages 200 with expected
title) and Harmonia's repin default `c762c8ad` reached terminal main CI,
Deploy mdBook, and pages-build-deployment success (live Pages 200 with
expected title). Atlas advanced both gitlinks in commit `0f58972`. A peer's
staged Moirai pointer to `bd70d29b` was left uncommitted: that default has no
hosted runs yet and fails its acceptance oracle. Athena `1c7a7f94` still
holds: its Deploy mdBook succeeded but its push CI run is cancelled with no
successor. Eunomia `834bd3b4`: MSRV and Deploy mdBook terminal success, but
its push CI is cancelled with no successor; Apollo `fd9ecd02`: ci terminal
success but the dynamic pages-build-deployment was cancelled.
The same refresh's structural-only audit remains `status: ok` with zero
issues across all 22 registered providers; the failure is pointer/hosted
evidence state, not a detected registration or coherence defect.

**Athena workflow repin (2026-08-21):** Athena PR #16 merged with the exact
head guard at provider default `1c7a7f94`. The change only updates the shared
book workflow reference. Post-merge CI `32476210608` and Pages `32476211063`
are queued; the nested Atlas pointer remains unchanged until those runs and
the canonical live-page check are terminal.

**Harmonia workflow repin (2026-08-21):** Harmonia PR #8 merged with the exact
head guard at provider default `c762c8ad`. The provider's post-merge CI
`32476381283`, mdBook build `32476382038`, and Pages run `32476380137` are
queued; the nested Atlas pointer remains unchanged until the current default
evidence and canonical live-page check are terminal.

