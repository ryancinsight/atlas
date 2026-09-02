# atlas — cross-repository integration backlog

## ATLAS-ADR-FORM-NORMALIZATION-2026-09-02 — Twelve members' ADRs lack the canonical heading or status form [patch] — in-progress 2026-09-02 (headings done; guard adoption wave 2 pending)

- **Claim:** integrator claude (this session); one API-authored PR per member (no shared tree touched); lease per member PR: `docs/adr/**`, the member's ADR workflow (`adr-index.yml` or the guard job in `ci.yml`/`rust-ci.yml`), `scripts/adr-index.py` where a copy remains.
- **Progress (2026-09-02):** `scripts/atlas-adr-canonical-form.py` (`85a184cc`, 13 tests) rewrites the first heading to `# ADR <filename-number>: Title` and reports unnumbered files. Dry run: coeus 53, kwavers 59, moirai 36, hephaestus 29, ritk 18, apollo 3 (`NNNN —` form, accepted by strict but folded for one form), leto 2 + `sparse-support-design.md` (an Accepted ADR with no number — claims the next number in its PR), mnemosyne 1, gaia 1. The atlas `--strict` check has no status-form rule, so aequitas, melinoe and themis already pass it; iris carries a hand-written `INDEX.md` beside the generated README (duplicate index, its own row). Order: gaia → mnemosyne → ritk → coeus → moirai → hephaestus (no workflows: dedicated `adr-index.yml` created) → kwavers (switch to strict) → leto → apollo.
- **PRs (2026-09-02, API-authored via the campaign orchestrator, each pinning the strict guard):** gaia#38 (merged `70429090`), mnemosyne#98 (fourth generator copy deleted), ritk#214, coeus#355, moirai#237 (`rust-ci.yml`), hephaestus#251 (default branch `master`; `(hephaestus)` heading tags dropped — the old renderer had leaked them into the index titles), kwavers#687 (strict; 037 and 040 had no title heading at all and gain `GPU PSTD output contract` / `GPU PSTD peak-pressure output`, replacing filename slugs in the index), apollo#267 (three `NNNN —` headings; guard already strict), leto#145 (`sparse-support-design.md` → `0028-sparse-array-support.md`, claiming the next number). iris's duplicate `docs/adr/INDEX.md` is iris's own `IRIS-012`. Canonicalizer follow-up `2dc1c5d1`: a numberless `ADR:` marker is form, not title. Closes when all nine land and the umbrella `--strict` pass over every member is clean.
- **Landed (2026-09-02):** gaia#38 `70429090`, mnemosyne#98 `fd48f92c`, hephaestus#251 `2482a760`, apollo#267 `9ed566e4`, leto#145 `15973db1`, ritk#214 `6ff6d0b5`. moirai#237 `2f24b472` (its `Workspace gate` pinned ADR 0008's old heading text in a contract test — literal folded into the PR commit). Open: coeus#355, kwavers#687 — queued behind runner starvation. Added iris#22 (strict guard adoption; deletes the hand-written duplicate `docs/adr/INDEX.md`, closing iris's IRIS-009 and IRIS-012 in the same PR), so twelve members end on the shared guard.
- **Heading half done (2026-09-02):** kwavers#687 `ec420a62` landed last; the oracle — atlas `adr-index.py check --strict` over every member's `docs/adr` exported from `origin/<default>` — reads 24 members checked, 24 clean. Strict guard runs on hermes, apollo, kwavers, gaia, mnemosyne, ritk, coeus, moirai, hephaestus, leto, iris. **Wave 2 (remaining):** the members whose ADRs already conform but carry no guard job — aequitas, asclepius, athena, CFDrs, consus, eunomia, harmonia, helios, horae, hyperion, melinoe, proteus, themis, tyche — adopt it via the same orchestrator (guard job only, no heading rewrites), staged behind the in-flight cancel-class and MSRV waves so the starved runner queue is not flooded; the item closes when every member's index check runs strict from atlas.
- **Wave 2 opened (2026-09-02):** aequitas#44, asclepius#32, athena#23, consus#62, eunomia#78, harmonia#12, helios#81, horae#31, hyperion#29, melinoe#25, proteus#25, themis#41, tyche#41 — each a dedicated `adr-index.yml` calling the guard strict (its path filter keeps the PR off the member's full CI); CFDrs has no `docs/adr`. Gate: each PR's own `ADR index is current` check.
- **Wave 2 landed (2026-09-02):** athena#23 `d57a4730`, aequitas#44 `430fd772`, eunomia#78 `a7e132c5`, harmonia#12 `2897d106`, melinoe#25 `2af08df9`, themis#41 `65054737`, tyche#41 `2ddbca75`, hyperion#29 `f8d12daa`, proteus#25 `4c5d3e8d`. Open: consus#62, helios#81 (queued); asclepius#32 red on `supply-chain` — the yanked `chacha20 0.10.1` cured by asclepius#33, then #32 re-runs; horae#31 red on `verify` — `mdbook test` hits `E0464: multiple candidates for rmeta dependency aequitas` from a restored cache holding two aequitas artifacts (a horae book-test cache defect, filed as a horae row in `ATLAS-DEFAULT-BRANCH-REDS-2026-09-02`; failed jobs re-run to test the collision hypothesis). consus#62 `007824d7` and asclepius#32 `07f487ce` landed later (asclepius after its yanked-crate fix #33). Open: helios#81 (blocked on the helios benchmark false positive), horae#31 (rebased onto horae#32). horae#31 `2b4453d3` landed after horae#32's book-test fix; helios#81 is the last guard adoption open, behind helios#83.
- **Header (2026-09-02, `9ed3e4d1`):** the generator now writes provenance naming atlas as its home and `adr-index-guard.yml` as its CI surface, with the regenerate command as run from an atlas checkout; `check` compares the index body (everything after the provenance comment), so an index with the old header and a current table passes and no umbrella red window opens. **Sweep (staged behind wave 2):** one PR per member moving every `adr-index-guard.yml@<sha>` pin to one atlas SHA (five distinct pins exist today) and regenerating `docs/adr/README.md` under it — the orchestrator's `--bump-pin` mode. The item closes on that sweep.
- **Sweep opened (2026-09-02, `--bump-pin`, pin `191617bf`):** aequitas#46 (proved the mode: pin moved, header regenerated, index body unchanged), apollo#280, asclepius#35, athena#25, coeus#357, eunomia#80, gaia#40, harmonia#14, hephaestus#254, hermes#137, horae#34, hyperion#31, iris#25, kwavers#693, leto#148, melinoe#27, mnemosyne#109, moirai#241, proteus#27, ritk#216, themis#43, tyche#43 — every member with ADRs except helios (its guard PR #81 is still open) and consus. consus#64 followed once consus#63 landed; helios follows #81/#82. 21 of the first 22 merged within the hour. Gate: each PR's own `ADR index is current` check.
- **Finding (2026-09-02, validating parse over every member's `docs/adr`):**
  twelve of twenty-four members fail the member-copy generator's checks
  (canonical `# ADR NNN: Title` or `# NNN — Title` heading; a Proposed /
  Accepted / Rejected status). First failing file each: aequitas
  `0013-acceleration-quantity.md` (status), coeus `0001-…interpolation.md`
  (heading), gaia `0001-…path-construction.md` (heading), hephaestus
  `0001-cuda-backend.md` (heading), kwavers `001-adaptive-beamforming-…md`
  (heading), leto `0012-dqds-…md` (heading), melinoe `0001-parallel-executor-…md`
  (status), mnemosyne `0001-free-list-…md` (heading), moirai
  `0001-moirai-as-…md` (heading), ritk `0001-coeus-native-…md` (heading),
  themis `0001-crates-io-…md` (status). The other twelve pass and their indexes
  are current.
- **Why it matters:** ADR governance names one canonical form (terminology
  SSOT); a stack-wide strict index guard (`ATLAS-ADR-INDEX-GUARD-2026-09-01`)
  cannot be required until these conform, so the guard ships with strictness
  opt-in and this campaign turns it on member by member.
- **Outcome:** one PR per member normalizing headings and status lines to the
  canonical form (content untouched), then that member's guard call switches
  to `strict: true`. Mechanical; a member's index regenerates in the same PR.
- **Acceptance oracle:** the validating generator parses every member's
  `docs/adr` without error and every member's guard runs strict.

## ATLAS-RATCHET-REGRESSIONS-2026-09-02 — Seventeen debt-class regressions landed on main through gitlink advances [patch] — todo

- **Refresh (run 33590087496 on `45b2db92`):** 19 regressions, 51 tightenings. New since the finding: athena `tag_pinned_actions` 0→9, ritk `allow_sites` 0→16, hermes `oversized_files` 22→28 / `commented_out_code` 7→10, moirai `existence_only_assertions` 33→38, themis `oversized_files` 1→3; the 51 tightenings (CFDrs `crate_level_allows` 367→6, `print_dbg` 257→26, apollo `allow_sites` 28→19, …) are baseline updates the next green run records.
- **Burn-down (2026-09-02):** apollo `gitattributes_missing` + `workflow_missing_timeout` → apollo#270 (`.gitattributes` on the stack template; `timeout-minutes: 15` on `python-release.yml`'s `publish` job — the `wheels` job is a reusable-workflow call, which GitHub forbids a timeout on and the rule already exempts); athena `tag_pinned_actions 0→9` → athena#22 (nine `uses:` pinned to the SHAs six other members run; `toolchain: 1.97.0` stated instead of the action ref `@1.95.0`, which had installed a toolchain two minors behind athena's own `rust-toolchain.toml`).

- **Finding (conformance run 33583483834 on `0c129c66`, the first completed
  ratchet run after three were cancelled by successive pushes):**
  `17 regression(s), 49 tightening(s)`. The regressions, per member:
  - apollo (7): commented_out_code 5→8, existence_only_assertions 1→8,
    gitattributes_missing 0→1, manifest_implementation 31→37,
    oversized_files 34→43, print_dbg 4→10, workflow_missing_timeout 0→1
  - athena (3): existence_only_assertions 0→1, oversized_files 1→2,
    tag_pinned_actions 0→9
  - moirai (2): commented_out_code 7→8, existence_only_assertions 33→38
  - hermes (1): oversized_files 22->29 - `numa/processor.rs` (579) **split in
    hermes#130 (`5c3303b9`)**, parent now 369; the other six files are peers'
  - ritk (1): allow_sites 0→16
  - CFDrs, coeus (1 each): oversized_files 139→140, 19→20
  - kwavers (1): manifest_implementation 286→287
- **Why the ratchet did not stop them:** the gate lives on the umbrella and
  fires on gitlink advances, so the debt was already merged in each member
  before it was measured; three consecutive umbrella runs were then cancelled
  by the next push (the cancelled-gate class, cf. apollo#246), so no verdict
  existed until pushes paused. Each member's own CI does not gate these
  classes.
- **Outcome:** each row either burns down (fix in the member, ratchet then
  tightens) or is a measurement artifact corrected in the scanner — never a
  baseline bump. Attribution per file comes from the scanner's per-file
  output; contributions by this session (hermes `processor.rs`; apollo
  `print_dbg` if bench `println!` is counted) are fixed by it first.
- **Attributions so far (2026-09-02):** apollo `gitattributes_missing` — no `.gitattributes` exists on apollo `main` (the CRLF warnings on every apollo edit are this); apollo `workflow_missing_timeout` — `python-release.yml` job `publish`; apollo `print_dbg` — not the EcoQoS probe: the scanner exempts `benches/`; hermes `oversized_files` — `numa/processor.rs` (579) split into platform leaf modules in hermes#130 (`HS-PROCESSOR-MODULE-SPLIT-2026-09-02`), the other six are peers' files. Remaining rows need per-file attribution in their members.
- **Acceptance oracle:** a completed `atlas-conformance` run on `main` reports
  `0 regression(s)`; the tightenings it lists are recorded by regenerating
  `scripts/conformance-baseline.json` in the same change.

## ATLAS-CRITERION-FLOAT-ROUNDTRIP-2026-08-31 — Preserve Criterion confidence values [patch] — provider delivered; consumer recollection pending

- **Outcome:** parse Criterion estimate numbers with exact decimal-to-`f64`
  round trips so the family-wise confidence gate cannot reject an interval
  whose recorded confidence equals the derived requirement.
- **Evidence:** Kwavers PR #681 run `33433562701` completed four 45-case pairs
  with zero regressions and zero universe mismatches, then rejected all 180
  intervals as `99.88888889% < 99.88888889%`. Its artifacts serialize
  `0.9988888888888889`; locked `serde_json` 1.0.151 without
  `float_roundtrip` reconstructs concise decimals through division by a power
  of ten and can round this value down by one unit in the last place.
- **Acceptance:** enable exact float parsing, pin the 45-case escaped value in
  a value-semantic regression, pass the classifier gates, advance the exact
  consumer pin, and recollect PR #681 without changing the confidence rule,
  benchmark workload, or measured production code.
- **Provider evidence:** source commit
  `62955b24f1eeb8495372cd85e74eea6046ed21a8`; exact artifact replay accepts
  both 45-case replications with zero insufficient intervals and zero
  regressions; Nextest passes 22/22, including the escaped fixture; warning-
  denied Clippy, fmt, doctests, and warning-denied Rustdoc pass. Consumer pin
  advancement and exact-head hosted recollection remain open.

## ATLAS-MSRV-JOBS-OVERRIDDEN-2026-09-02 — Seven members' MSRV jobs compile with the pinned 1.97.0, not the floor they claim [patch] — todo

- **Finding (2026-09-02, survey of every member workflow naming MSRV):** consus `ci.yml` (msrv job, 1.85.0), eunomia `msrv.yml` (1.95.0), melinoe `msrv.yml` (1.81.0), mnemosyne `msrv.yml` (1.95), themis `msrv.yml` (1.81.0), proteus `ci.yml` (1.95.0), asclepius `ci.yml` (1.95.0) install the floor through `dtolnay/rust-toolchain`, whose `action.yml` (at `4cda84d5`) only runs `rustup toolchain install` and `rustup default` — and every one of these repositories commits `rust-toolchain.toml` with `channel = "1.97.0"`, which rustup ranks above the default. None sets `RUSTUP_TOOLCHAIN`, removes the file, or prints `rustc --version`. Each job therefore compiles with 1.97.0 and the `rust-version` floor is a fictional compatibility claim (engineering_gates: "an untested MSRV claim rots"). iris has no MSRV job at all and its two jobs request `1.95.0` under the same pin (iris `IRIS-013`).
- **Outcome:** one PR per member: `env: RUSTUP_TOOLCHAIN: <floor>` on the MSRV job (the environment variable outranks the in-tree file) and a `rustc --version` step whose output is the evidence; iris additionally gains the job. Mechanization: a conformance class `msrv_job_overridden` — an MSRV-named job in a repository with a pinned `rust-toolchain.toml` and no `RUSTUP_TOOLCHAIN` — so the class cannot recur.
- **Acceptance oracle:** each member's MSRV run log prints the floor version, and the conformance class reads 0 stack-wide. A job that then fails is a real MSRV violation to fix in the crate or to reclassify by raising `rust-version` (versioning), never by removing the override.
- **PRs (2026-09-02, API-authored, one per member; the MSRV job's own `rustc --version` line is each PR's oracle):** mnemosyne#105 (1.95), eunomia#76 (1.95.0), melinoe#23 (1.81.0), themis#40 (1.81.0), consus#61 (1.85.0), proteus#24 (1.95.0), asclepius#31 (1.95.0). A red MSRV job on any of them is a real floor violation surfaced for the first time (melinoe and themis claim 1.81 under edition 2024, which needs 1.85) and becomes that member's `rust-version` decision — never a reason to drop the override. iris: after iris#22 lands (both touch `ci.yml`), an `msrv` job is added under IRIS-013.
- **Landed with the floor job green (2026-09-02):** melinoe#24 `dda137ab` (1.81 holds), eunomia#77 `652708b0`, themis#40 `1d972ccd`, proteus#24 `808a59be`, mnemosyne#105 `8490eb68`, moirai#238 `845f3804`, iris#23 `13653b2d`. **First real floor violation:** consus — declared 1.85.0, but `consus-mat`/`consus-zarr` use let chains (stable 1.88) and `if let` guards on match arms (stable 1.95.0, rust-lang/rust#141295); consus#61 raises `rust-version` to 1.95.0 with README following — all fifteen MSRV matrix cells green at 1.95.0; the PR waits only on consus's 81-check matrix behind the queue. asclepius#31's MSRV job is green; its `supply-chain` red is the yanked `chacha20 0.10.1`, cured by asclepius#33, after which #31 merges. The truthful floor then un-gated clippy's MSRV-aware `manual_is_multiple_of` on four sites written around the old 1.85 (each carried a comment saying so): consus-core `decode.rs` ×2, consus-zarr `codec/mod.rs`, and consus-parquet's `is_group` becomes `const fn` — fixed on #61's branch, zero guards kept where `is_multiple_of(0)` would change an error class.
- **Mechanized (`70631345`):** conformance class `toolchain_request_overridden` — a job whose install step requests a toolchain other than the committed pin with no `RUSTUP_TOOLCHAIN` in scope; baseline enters at 11 jobs across 9 repos (the seven above, iris 2, moirai 2). moirai's two are `python-ci.yml` wheel/rust jobs requesting 1.95.0 with no MSRV job anywhere → moirai#238 (merged) states 1.97.0 and adds an `msrv` job on the same override pattern; its first default-branch run is the floor's oracle. iris's two close with its `msrv` job under IRIS-013: iris#22 landed (`0c6f2e60`), iris#23 open (states 1.97.0 on `verify`/`supply-chain`, adds `msrv` with the override, marks IRIS-013 done).
- **Incident (2026-09-02, own defect):** the per-member orchestrator misplaced the proof step in every one of the seven PRs — two regex slips (a `\s+` indent capture reaching across a blank line; a `with:` matcher that took the line alone) put `- name: Prove the toolchain` inside the install step's `with:` block. GitHub rejects such a file and schedules none of its jobs, so melinoe#23 and eunomia#76 merged on their *other* checks with a broken `msrv.yml` (zero-job `failure` runs on `main` named by file path). Repairs: eunomia#77 and melinoe#24 restore the block; mnemosyne#105, themis#40, consus#61, proteus#24, asclepius#31 rebuilt in place. Gate rule adopted for every workflow-changing PR: the changed workflow's own job must exist and be green — a check list lacking it is the file being rejected. iris#23 merged (`13653b2d`): `msrv` job added, IRIS-013 done.
- **Escaped-defect record:** the jobs were green for months because 1.97.0 compiles everything; the check that would have caught it is the `rustc --version` proof line the fix adds — a verification job must print the identity of what it verified.

## ATLAS-RUNNER-STARVATION-2026-09-02 — Hosted runner queue starves every verification run [infra] — todo (Ask-User)

- **Finding (2026-09-02):** with ~25 small PRs and the peers' pushes in flight, every job across the organization sat `queued` for tens of minutes to over an hour: kwavers#687 timed out a 60-minute merge gate with 27/29 checks green and two still queued; kwavers#691 shows 21 of 29 checks pending after an hour; atlas's own conformance runs queued for hours (`fb616d9f`, `7264f91e`). The queue-time rule (engineering_gates: workflow hygiene) makes a job queued past its runtime target an infrastructure defect, not agent waiting — and it is what turned today's shared-group cancellation into a class (`ATLAS-DEFAULT-BRANCH-CANCEL-2026-09-02`): pending runs superseding each other only bites when nothing ever starts.
- **Cure:** capacity or load-shedding. Load-shedding already applied today: path-filtered adoption workflows, staged waves. Load-shedding still owed by members: consus runs 81 checks per pull request (Check × 15 packages, Test × packages, MSRV × 15, fuzz builds) — a matrix that recompiles per cell instead of one archive sharded across runners (engineering_gates: build-once topology); a consus row. Capacity is the standing policy for private repositories and trusted-contributor stacks: a self-hosted runner on owned hardware with a persistent warm `CARGO_TARGET_DIR`/sccache, so no run pays cold setup or a metered minute. **Ask-User:** register one or more self-hosted runners at the organization level (labels `self-hosted, linux, x64`; the RTX 5080 host can also carry the `cuda` label the kwavers GPU-parity schedule already targets) — `gh` cannot register runners (hosting/security setting). Until then the waves stay staged and merge gates re-launch at their cap.
- **Acceptance oracle:** `gh run list --json createdAt,startedAt` across the stack shows median queue time under the five-minute job target; the kwavers `GPU Parity (scheduled)` row in `ATLAS-DEFAULT-BRANCH-REDS-2026-09-02` turns green.

## ATLAS-DEFAULT-BRANCH-CANCEL-2026-09-02 — Default-branch verification runs cancel each other fleet-wide [patch] — todo

- **Finding (2026-09-02, `scripts/atlas-red-workflows.py`):** kwavers `CI/CD Pipeline` and `Architecture Validation` (my #686 merge `0d0a9d45`), mnemosyne `CI` (`96c9ef6d`), apollo `pages-build-deployment` (`0bdbbe57`) all ended *cancelled* on `main`: their workflows share one concurrency group per ref with `cancel-in-progress: true`, and GitHub supersedes a *pending* run in a shared group regardless of that flag, so under runner starvation each merge cancels the previous merge's verification before a job starts. atlas had the same defect and fixed it in `db825504` + `f4c09631`: pull requests keep a per-ref group and cancellation; default-branch runs key the group on `github.sha`.
- **Outcome:** one PR per member applying the atlas form to every workflow with a `push` trigger on the default branch and `cancel-in-progress: true` (`group: <name>-${{ github.event_name == 'pull_request' && github.ref || github.sha }}`, `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`). Mechanization: conformance class `default_branch_cancel_in_progress` — a workflow with a default-branch `push` trigger whose `cancel-in-progress` is an unconditional `true` — so the class cannot recur.
- **Mechanized (`9ca66f3c`):** conformance class `default_branch_cancel_in_progress`; baseline enters at 57 workflows across 26 repositories (hephaestus 6, kwavers 4, mnemosyne 4, coeus/eunomia/melinoe/moirai/ritk/themis 3, …). atlas's own two (`atlas-stack-overlay.yml`, `docs.yml`) closed in `99d50ceb7`. Campaign: one API-authored PR per member rewriting each offending workflow — verification workflows to the per-commit/PR-only form; deploy workflows (Pages, publish) to `cancel-in-progress: false`, since a half-cancelled deploy is worse than a superseded one.
- **Wave 1 (2026-09-02, the members already showing cancelled verdicts):** kwavers#691 (4 verification), mnemosyne#106 (3 + book-pages deploy), apollo#274 (pages deploy), hephaestus#253 (5 + book-pages), coeus#356 (2 + book-pages). hephaestus#253 `97453c87`, apollo#274 `191a8205`, mnemosyne#106 `8d150b85`, coeus#356 `947de5a4` merged; kwavers#691 (rebased past #687) is blocked by an unrelated red — `Integration Suite`: `pstd_finite_window_born::source_phasing_is_frechet_derivative` demands a GPU adapter on a CPU runner, and `property_based_tests::test_grid_convergence` / `test_plane_wave_injection::…_timing` exceed the 60 s nextest bound — filed as kwavers rows in `ATLAS-DEFAULT-BRANCH-REDS-2026-09-02`; the concurrency form itself is proven on four members, so wave 2 proceeds. Remaining 37 workflows across 20 members follow in waves as these land, so the starved runner queue is not flooded.
- **Wave 2a (2026-09-02):** eunomia#79 (3 verification), melinoe#26 (3), themis#42 (3 + book-pages), moirai#239 (rust-ci + python-ci verification, book-pages deploy), ritk#215 (ci + python_ci verification, book-pages deploy). The first pass classified ritk's and moirai's CI workflows as deploys on the word `maturin`; the classifier now reads the file name (`release|pages|publish|deploy`) and Pages-deploy actions only, and both branches were rebuilt in place. Remaining after 2a: 22 workflows across 15 members (aequitas, athena, CFDrs, consus, gaia, harmonia, helios, hermes, horae, hyperion, iris, leto, proteus, tyche; kwavers#691 blocked).
- **Wave 2b (2026-09-02):** aequitas#45, athena#24, CFDrs#379, consus#63, gaia#39, harmonia#13, helios#82, hermes#135 (book-pages deploy only), hyperion#30, iris#24, leto#147, proteus#26, tyche#42 — 22 workflows; horae had nothing left to change. Finding: the dedicated guard workflow the ADR campaign minted carried the shared-group form itself, so the nine guard workflows merged this afternoon were new instances — wave 2b picked them up (aequitas#45 is exactly that file) and the template now emits the per-commit form. **Wave 2c:** the four guard PRs still open when 2b ran (consus#62, helios#81, horae#31, asclepius#32) re-run through the fixer after they land. kwavers#691 remains blocked on its integration-suite red.
- **Landed (2026-09-02):** wave 2a — melinoe#26 `ebdf3f92`, themis#42 `89ad5b0f`, eunomia#79 `56b947dc`, Moirai#239 `a9de74e6`, ritk#215 `4a1b3e8e`. Wave 2b so far — aequitas#45 `308a83fe`, athena#24 `d87312f1`, CFDrs#379 `aab1f22a`, harmonia#13 `f0f63566`, gaia#39 `3cb8aa34`, hyperion#30 `9ee8015b`, leto#147 `ef0933dd`, proteus#26 `7fc8a935`, iris#24 `8db07d08`. Wave 2c: asclepius#34 (its guard workflow, old template); consus#63 rebuilt in place to carry consus's guard workflow too. horae#32 `468a9001` fixed the book-test link directory, horae#31 rebased onto it. Wave 2b final: eleven of thirteen landed (hermes#135, tyche#42 among them); helios#82 waits with helios#81 on helios#83's identity gate; consus#63 (rebuilt to carry its guard workflow) waits on consus's 81-check matrix. Wave 2c: asclepius#34 `3ca8cc1f` and horae#33 `d4844415` landed; helios follows #81. consus#63 `da9cf302` landed (83 checks); every member except helios (#82 rebuilt onto #83) now carries the per-commit form on its default-branch workflows.
- **Acceptance oracle:** the collector reports no `cancelled` default-branch row that a later run on the same tree did not supersede green; the conformance class reads 0 stack-wide.

## ATLAS-DEFAULT-BRANCH-REDS-2026-09-02 — Member default-branch workflows red with no collector [patch] — todo

- **Finding (first `atlas-red-workflows.py` pass, 2026-09-02):** each row is a default-branch workflow whose newest completed run is not green; nobody had collected any of them. Each row is claimable on its own: classify (stale release attempt, rotted job, starved schedule), fix the component or retire the job, and the collector's next pass is the oracle.

| repo | workflow | conclusion | run | note |
| --- | --- | --- | --- | --- |
| gaia | Crates.io Release | failure | [`a5b0fe72` 2026-08-11](https://github.com/ryancinsight/gaia/actions/runs/31462176421) | manual `workflow_dispatch` release attempt; log carries no failing step. Release is the user's action; the workflow itself is `ATLAS-PUB-001` scope (blocked) |
| iris | Crates.io Release | failure | [`ab3eea28` 2026-08-11](https://github.com/ryancinsight/iris/actions/runs/31462174822) | same class as gaia's: manual dispatch 2026-08-11, `ATLAS-PUB-001` scope |
| kwavers | GPU Parity (scheduled) | cancelled | [`bd7e6fa6` 2026-09-01](https://github.com/ryancinsight/kwavers/actions/runs/33463119860) | runner starvation: `runs-on: [self-hosted, linux, x64, cuda]` and no such runner is registered online, so every nightly run (`17 2 * * *`) queues 24 h and GitHub expires it — cancelled 08-30, 08-31, 09-01; 09-02 queued now. **Ask-User:** register a self-hosted CUDA runner for kwavers on the RTX 5080 host (`gh` cannot register runners; hosting/security setting), or pause the schedule until one exists |
| mnemosyne | Fuzz | failure | [`247057ed` 2026-09-02 (#97's new workflow, first run)](https://github.com/ryancinsight/Mnemosyne/actions/runs/33591989913) | `E0463: can't find crate for core` — `cargo fuzz` builds std via `-Zbuild-std`, which needs the `rust-src` component dtolnay's action omits; fix mnemosyne#102 merged; the next default-branch `Fuzz` run is the oracle |
| apollo | ci | failure | [`6d205280` 2026-09-02](https://github.com/ryancinsight/apollo/actions/runs/33592017580) | the SemVer gate the user's #266 wired in fails on public-surface breaks of `WgpuError` in `apollo-mellin` (vs published 0.11.0) and `apollo-ntt` (vs 0.9.0) — the gate working as designed. **Ask-User:** breaking changes under a non-major version: bump `apollo-mellin`/`apollo-ntt` to their next major (release authority) or record a gate baseline for the intended break; the gate's `informational` twin already skips |
| kwavers, mnemosyne, apollo | CI / Architecture Validation / pages-build-deployment | cancelled | `0d0a9d45`, `96c9ef6d`, `0bdbbe57` 2026-09-02 | not defects in the trees: default-branch runs superseded while pending by the next merge's run — the class filed as `ATLAS-DEFAULT-BRANCH-CANCEL-2026-09-02` |
| kwavers | Integration Suite (in `CI/CD Pipeline`) | failure | kwavers#691 run, 2026-09-02 | member test defects, not the workflow change: `pstd_finite_window_born::source_phasing_is_frechet_derivative` panics `no compatible accelerator adapter` on a CPU runner (a GPU-requiring integration test must select its backend by capability, typed absence on CPU — standards: runtime capability detection); `property_based_tests::test_grid_convergence` and `test_plane_wave_injection::test_plane_wave_boundary_injection_timing` hit the 60 s nextest termination bound (a performance defect in the system under test or an oversized workload — engineering_gates: test budgets). `main`'s own runs of this suite were all cancelled today, so no green baseline exists; blocks kwavers#691 |
| horae | verify (Book tests) | failure | horae#31 run, 2026-09-02 | `mdbook test` fails `E0464: multiple candidates for rmeta dependency aequitas` — the rust-cache restore leaves two aequitas rlibs in `target/debug/deps`, and rustdoc's `-L` cannot pick; `main`'s last verify was green before aequitas moved. Deterministic (re-run reproduced it): three aequitas artifacts at different hashes — `.rmeta` from cached check/clippy runs beside the build's `.rlib`. Fix open as horae#32: stage the newest `.rlib`/proc-macro `.so` per crate into `target/booklibs` and point `mdbook test -L` there; horae#31 rebases onto it |
| mnemosyne | CI (SemVer gate, release gate) | failure | [`fdf66542` 2026-09-02](https://github.com/ryancinsight/Mnemosyne/actions/runs/33600786453) | the user's #107 merge; the release SemVer gate reports a public-surface break under a non-major version — the apollo class. **Ask-User:** major bump or gate baseline |
| helios | benchmark regression check | failure | helios#81 run, 2026-09-02 | a workflow-only PR (guard adoption) flagged a "replicated regression" of +1.7 % then +0.4 % whose two run orders disagree in sign: identical code cannot regress, so this is the identical-code false-positive class apollo closed with `scripts/bench_executable_identity.py` (compare code sections; skip the timing gate when candidate and baseline binaries match). Fix: the comparer now lives in atlas (`scripts/bench_executable_identity.py`, `12a92b53`, ELF64-synthesizing tests); helios#83 records each `cargo bench --no-run` executable, compares baseline and candidate before timing, and skips the comparison (smoke still runs) when identical — its own gate is the oracle — first run: every pair `CODE IDENTICAL`, the measure step exited at its notice, and the replication classifier then failed on reports that were never written; second commit gates the classifier on the same output; landed `49950e89` with its own gate reporting identical code. helios#81 and #82 rebuilt onto it (#82 regenerated from current `main` by the cancel fixer — a whole-blob API rebase had carried the pre-#83 `ci.yml`, which would have reverted the gate; caught before any waiter ran); apollo#279 (merged; its identity gate reported identical code and skipped the pairs) retires apollo's vendored copy — one comparer stack-wide, run from the pinned atlas checkout in both gates |

- **Revision (2026-09-02):** gaia `Examples` dropped — that workflow no longer exists on `main`; the collector now reports active workflows only (`9235e47d`). mnemosyne `Fuzz` added.
- **Acceptance oracle:** `scripts/atlas-red-workflows.py` reports no member rows (atlas's own cancelled rows are the concurrency finding above, tracked there).

## ATLAS-APOLLO-LANEKERNEL-INLINE-CONTRACT-2026-08-31 — Three large `LaneKernel::call` bodies do not carry the attribute their contract requires [patch] [perf] — done 2026-09-02 (apollo PR #277, merged `d649d8657`)

- **The contract.** hermes `HS-VECTORIZE-LARGE-KERNEL-2026-08-28` documents a
  measured ~30x failure: the `#[runtime_dispatch]` expansion's
  `#[target_feature]` helper is the only feature-carrying frame, and a large
  kernel body makes LLVM decline to inline the helper into it. The body then
  codegens in the unattributed inner symbol at baseline — zero FMA, per-operation
  feature detection. hermes fixed its half and states the consumer half in
  `LaneKernel`'s docs: **mark large `call` bodies `#[inline(always)]`**, the
  same contract pulp documents for `WithSimd::with_simd`.
- **Unmet at three production sites in apollo-fft** (body sizes measured by
  brace-matching from the `fn call` line):

  | site | body lines | `#[inline(always)]` |
  |---|---|---|
  | `batched/mod.rs:106` (`BatchedStages`) | 219 | **no** |
  | `batched/dif.rs:60` (`BatchedStagesDif`) | 189 | **no** |
  | `batched/interleaved.rs:163` (`InterleavedStages`) | 111 | **no** |

  For contrast, the sites that do carry it — `batched/boundary.rs` (both),
  `resident/{mod,planar}.rs` — carry it with an `#[expect(clippy::inline_always)]`
  whose reason cites this very contract, so the obligation is understood in the
  crate; these three were missed. `interleaved.rs:93` (21 lines) and
  `lane_capability.rs` (3 lines) are small enough not to need it.
- **Not yet known to be live.** The four-step sizes do not currently look 30x
  slow, so LLVM may be inlining these anyway at present body sizes and
  optimization settings — which is exactly the fragility the attribute exists to
  remove, since nothing holds that in place across an edit.
- **Verification method** (blocked on tree capacity, not on knowledge): add the
  attribute in a lane, measure the four-step sizes before and after with an
  interleaved probe, and inspect codegen for FMA in the affected symbols. If the
  delta is zero the attribute is still correct — it converts a silent
  size-dependent cliff into a guarantee.
- **Blocked 2026-08-31:** apollo is at its two-tree bound with both trees held by
  live peers (`perf/apollo-batched-parallel` in the main tree, editing
  `batched/mod.rs` and `batched/dif.rs` directly; `perf/apollo-base-line` in the
  lane). Two of the three sites are inside the live lease. **Re-open trigger:**
  either peer's lease discharges.
- **Worth mechanizing.** A source scan asserting that every `LaneKernel::call`
  body above a line threshold carries `#[inline(always)]` would make this class
  impossible to reintroduce. It is the same shape as the existing conformance
  ratchet, and the defect it guards has already cost 30x once.
- **Mechanized 2026-09-01** — delivered as the Atlas conformance class
  `lane_kernel_uninlined` (`scripts/atlas-conformance.py`). The detector
  counts `LaneKernel::call` bodies above 100 lines that lack
  `#[inline(always)]`, measured by brace-match, and the baseline records the
  true census: apollo = 3 (the `batched/mod.rs:106`, `batched/dif.rs:60`,
  `batched/interleaved.rs:163` sites named above); every other member 0. Three
  regression tests cover the large-uninlined / large-inlined / small-uninlined
  cases; the full scripts suite is green. This closes the "worth mechanizing"
  half — the class cannot now be reintroduced without a ratchet raise. The
  source fix itself (adding the attribute at the three apollo sites) remains
  blocked on the apollo two-tree lease and is tracked separately.
- **Delivered 2026-09-02 (apollo PR #277).** The peer leases that blocked
  the source fix went stale (`perf/apollo-batched-parallel` last commit 17 h,
  no PR; the lane is gone), so the three sites took the attribute with the
  same `#[expect(clippy::inline_always)]` reason the boundary kernels carry.
  Batched pinned ladder, interleaved before/after, two rounds, matched
  binaries: every efficiency-core size within ±1.4%, performance-core sizes
  inside the same binary's round-to-round spread (up to 14%). No measurable
  change — LLVM was already inlining at present body sizes, the fragility
  the attribute removes. Codegen (`llvm-objdump --demangle` over both
  matched binaries): neither binary carries a standalone symbol for any
  `BatchedStages`/`InterleavedStages` `call` body — the bodies were already
  folded into their dispatcher frames before the attribute, which is what
  the ladder parity shows; the attribute makes that fold a guarantee
  instead of an optimizer outcome. The `lane_kernel_uninlined`
  baseline (apollo = 3) tightens to 0 at the gitlink advance after merge.


## ATLAS-SEMVER-GATE-FLEETWIDE-2026-08-28 — Publishable members run no semver gate [patch] — shared workflow delivered; member adoption pending

- **Consumer breakage found 2026-09-01 (evening).** The first published
  revision of `semver-gate.yml` (`0253866f8`) carries two top-level `name:`
  keys; GitHub cannot parse it, every push to atlas spawned a failed run with
  no jobs ("workflow file issue") until `71fa69658` removed the duplicate, and
  every caller pinned to that revision fails at load the same way. mnemosyne
  adopted it at exactly that pin and its main went red (`b75fe12`); aequitas
  PR #42 pinned a 41-character ref naming no atlas object at all. Both fixed
  forward to the current atlas head: mnemosyne PR #89, aequitas PR #42
  (commit pushed onto the peer's branch under takeover). Lesson for the
  adoption plan: a consumer pin is verified by the consumer's own CI run on
  the adopting PR, never by the atlas-side run, and a reusable workflow's
  own repo shows a parse failure as a phantom `push` run of a
  `workflow_call`-only file.
| ID | Outcome | Class | Status | Owner | Scope |
|----|---------|-------|--------|-------|-------|
| ATLAS-SEMVER-GATE-FLEETWIDE-2026-08-28 | Every member that publishes a crate detects public-surface breaks before the break ships. | [patch] | in-progress (shared workflow delivered 2026-09-01; member pin advancement pending) | unowned | each registered member's CI + the shared release pipeline |

- **Evidence, measured 2026-08-28 across the 25 registered members:** exactly
  **two** (`asclepius`, `proteus`) run a `cargo-semver-checks` job. Every other
  member carrying publishable crates has none — including the ones whose crates
  are *already on crates.io* (the README records 24 published, among them
  `leto`/`leto-ops`, `hermes-simd`, `mnemosyne-core`/`mnemosyne-heap`,
  `moirai-core`/`moirai-runtime`, `apollo-fft`, `coeus-*`, `hephaestus-*`,
  `ritk-*`, `consus`, `themis`, `melinoe`, `aequitas`, `eunomia`).
- **How it surfaced, with a real escape:** `MN-458` removed
  `Segment::is_owned_by`, a `pub unsafe fn` on a public type in the publishable
  `mnemosyne-memory-core`, and shipped it labelled `[patch]`. Running the tool
  by hand afterwards reported `inherent_method_missing` — *"semver requires new
  major version"*. Nothing in the pipeline was positioned to catch it. Recorded
  and reclassified in mnemosyne #80; the per-repo gate is `MN-460`.
- **This is the versioning rule's own mechanism missing:** the standing policy
  makes `cargo-semver-checks` authoritative for Rust public-surface
  compatibility and requires it on any merge touching `pub` surface and before
  every release. Two members implement that; twenty-three do not.
- **Design constraint (do not skip — it is why the naive job fails):** members
  accumulate accepted breaking changes under CHANGELOG *Unreleased*, so a gate
  that diffs `main` against the published baseline is red from its first run
  and gets ignored within a day. The gate must compare against the **last
  release tag** and fail only when the manifest version does not cover the
  detected class — gating the *release*, with a non-blocking informational run
  on PRs so the change-class is visible while the change is still in review.
- **Shape:** this belongs in the Atlas-owned reusable workflow set beside
  `crates-publish.yml`, not as 23 hand-rolled copies (a divergent per-repo copy
  is the duplication defect ADR 0035 exists to prevent). Members adopt it by
  advancing one `atlas-ref` pin, exactly as the publish pipelines are adopted.
- **Delivered 2026-09-01:** `.github/workflows/semver-gate.yml` — the shared
  reusable `workflow_call` with two jobs: `semver-pr` (informational,
  `continue-on-error`, diffs against the PR base so the change-class is
  visible in review) and `semver-release` (blocking on tag push, baseline
  resolved via `git describe --tags --abbrev=0 "TAG^"` with a first-commit
  fallback, so the gate compares against the **last release tag** and fails
  only when the manifest version does not cover the detected class). Inputs:
  `package` (required), `manifest-path`, `rust-toolchain`. Adoption per
  member is one `workflow_call` + the member's package name — same shape as
  the lockfile-guard adoption.
- **Non-goals:** bumping any manifest version now; retrofitting classifications
  onto already-merged history beyond `MN-458`, which is corrected.

## ATLAS-PROVIDER-CHAIN-QUALITY-2026-08-27 — Perf/memory/stability/safety audit + fix wave: apollo provider chain [patch]..[minor] — in-progress

- **Outcome:** adjudicated audit of apollo, hephaestus, leto, hermes, moirai,
  mnemosyne on four axes (performance, memory efficiency, stability, safety);
  accepted findings implemented per-repo as vertical increments (branch → gate
  → PR → merge), rejected/deferred findings filed with reasons on the owning
  member boards.
- **Integrator:** claude-fable session 03d80d33 (this claim). Audit fan-out is
  read-only (6 subagent sweeps, complete). Implementation claims land on each
  member's own board before that repo's source is touched; atlas-level entry
  tracks the campaign only.
- **Delivered 2026-08-29 (session continuation).**
  - apollo PR #194/#195/#196 — every FFT length routes correctly. Three faults
    (dispatcher fall-through, four mis-factored static radix entries, eleven
    naming an unexecutable radix), Bluestein as the terminal route, a
    naive-DFT sweep sharded to fit its budget, two structural table tests.
    Closes the highest-severity finding of this campaign: a silent wrong
    answer from a published transform.
  - apollo PR #197 — DCT-I, DCT-IV, DST-I, DST-IV reach O(N log N); the
    Type-IV pair shares one 2N-point FFT. 5.3 ms -> 38.6 us at N = 4096.
    Was blocked on the routing fix.
  - apollo branch inventory swept to zero (eleven branches classified and
    disposed); the Hephaestus cutover item closed by stale-claim takeover
    after re-running its own acceptance scan.
  - hephaestus PR #235 — device-side LU split; host-device traffic for the
    split falls from 3n^2*4 bytes to zero in each direction.
- **Constraints honored:** apollo `components/{base128,resident,batched,
  codelet}` + `test_support.rs` under live lease (ATLAS-APOLLO-BASE-BUTTERFLY-
  128) — findings there file to apollo's board, no direct edits; hermes tree
  held by live codex CI claim — hermes source work rides its current branch or
  a lane, `.github/` untouched.
- **Acceptance:** per-repo fix PRs merged green under member gates, or
  findings filed as DoR items with evidence; this entry closes with the ledger
  of merges + filings.
- **Progress 2026-08-28:** hephaestus HEPH-WGPU-STAGING-POOL-DECAY delivered
  (PR #229, merge `a3553d7`): staging-pool idle decay with a derived 10 s
  deadline, shadow retained-byte bound + hit/miss counters riding the
  acquire/recycle paths, sustained hit-rate and idle-decay evidence tests;
  member CI green (lockfile, host verification, WGPU contracts). hermes #97
  merged (SPMV short-row masked fix) at head `6382336`. Provider-chain repins
  after the hermes merge: leto #131 merged (hermes `bbc7bdb5`→`6382336`,
  Mnemosyne/themis cascade) and coeus #353 merged (hermes/leto/hephaestus/
  apollo all → current heads, merge `3875a8e`; every prior pin verified an
  ancestor — clean repins).
  Remaining repin consumers (CFDrs, athena, asclepius, ritk, helios, gaia,
  kwavers) hold worktrees on live lanes of parallel sessions — recorded here
  as pending follow-up, untouched to avoid collisions.
- **Progress 2026-08-28 (integrator session 03d80d33), sixth repo closed:**
  mnemosyne PR #79 enqueued — the four retag/provenance/cold-branch
  stragglers (MN-458), each the surviving instance of a pattern the
  MN-437..MN-456 sweep removed elsewhere. Evidence: Clippy `-D warnings`,
  `fmt --check`, nextest 289/289, doctests 5/5, and Miri under **both** borrow
  models over `mnemosyne-local` (84/84) and `mnemosyne-memory-core` (18/18).
  All six audited repos have now landed or enqueued their fix wave.
- **Root cause worth keeping (defect generator, not instance):** the surviving
  `mnemosyne-heap` copy of the int-to-ptr + `&mut Page`-across-segment pattern
  is explained by that crate sitting **outside the Miri gate** — the sweep that
  fixed every gated sibling could not see it. Filed as `MN-459` with its
  blocker measured on unmodified `main`: three pre-existing Miri failures in
  the crate's *own test helpers*. The general lesson for this stack: a
  miri/loom/sanitizer-driven sweep is bounded by the gate's crate list, so the
  sweep's closure claim must be read against that list, not the workspace.
- **Second process defect, cured:** the local gate sequence used through this
  campaign omitted `cargo fmt --check`, which reddened leto main once and
  moirai PR #171 once (both cured fix-forward, `d16542c` / `0584fb0`). `fmt`
  is now first in every gate invocation and in every agent brief. CI confirms;
  it must not discover.
- **Performance wave dispatched 2026-08-28 (three lanes, in flight):** moirai
  `MOI-PAR-TERMINALS-2026-08-28` (the flagship `par_iter().map(f).sum()` and
  most terminals run single-threaded through `seq_items()`, plus `Vec::split_off`
  splitting at O(n log n) copy traffic and non-short-circuiting `find_any`);
  hermes `HS-SIMD-PERF-2026-08-28` (transpose permute networks for AVX2 f32,
  AVX-512 f32/f64, NEON f32; F16 dispatch probe hoist per ADR 009); leto
  `ATLAS-LETO-OP-PERF-2026-08-28` (operator chains allocate n−1 arrays with no
  owned-lhs reuse; `reduce_axis` zero-fills a fully-overwritten output). Each
  carries a measurement requirement with the hybrid-core pinning caveat and an
  allocation/instruction-count signal, since wall-clock alone can invert
  verdicts on this host.
- **Apollo algorithmic items remain filed, blocked on tree capacity, not
  merit:** `ATLAS-APOLLO-CWT-FFT-CONVOLUTION` (O(scales·n²) with n
  transcendental evaluations *per coefficient* → O(scales·n log n)),
  `ATLAS-APOLLO-SHT-FFT-FACTORIZATION`, and `ATLAS-APOLLO-DCTDST-FAST-KINDS`
  (four of eight kinds are O(N²) at every size while the method docs claim
  O(N log N)) are the largest algorithmic wins the audit found. Apollo is at
  its two-tree bound with two live peers (main tree on
  `perf/apollo-base128-arith`, lane on `perf/apollo-dif-stages`, both edited
  within the last 20 minutes at the time of writing), so no third tree was
  opened. Re-open trigger: either apollo tree frees.
- **Consumer contract risk traced and routed:** leto #129's new panics on
  shared-window views reach a real consumer — kwavers filters the **columns**
  of a C-order array (`photoacoustic/filters/core.rs:168`), which are exactly
  the interleaved views now gated, and calls `to_contiguous()` + `assign()` on
  them. Both are paths the change routes through per-element access, so the
  shape is expected to hold, but it is unproven; a contract test pinning that
  consumer shape is being added to leto's own suite rather than left to
  kwavers' next lock sweep to discover.
- **Performance wave results (2026-08-28, two of three lanes landed):**
  - **leto #133 merged** (`a7dccf26`): owned-receiver `Add`/`Sub`/`Mul`/`Div`/
    `Neg` reuse the lhs allocation — 3-term chain 2 allocations → **1**, 5-term
    4 → **1**, owned scalar+neg 3 → **0**, borrowed tier pinned unchanged.
    Pinned timing (P-cores, both forms in one run): 3-term 64×64 −12%, 5-term
    −32% with disjoint CIs; **3-term 256×256 unchanged within CI and reported
    as such** — it is bandwidth-bound, so the allocation win does not show.
    Two corrections to this campaign's own filed evidence, both measured:
    (1) `owned + &b` never compiled before (rustc does not autoref an
    operator's lhs, `E0369`), so the impls are strictly additive with no
    coherence risk; (2) **`ATLAS-LETO-REDUCE-SINGLE-WRITE`'s cost premise was
    wrong** — `VecStorage::fill` is `vec![v; n]`, which hits std's
    `SpecFromElem`, so a zeroed output is a `calloc` and a large fresh
    allocation pays no memset at all. The item stays filed, reclassified
    `[minor]`, with its coverage proof recorded so nobody re-derives it.
  - **hermes #100 merged** (`5c50d1de`): most of the filed SIMD work had
    already been delivered by peers (#94 networks, #95 the F16 probe hoist via
    an `Avx2F16Frame` marker, #98 the AVX-512 f64 network), so the lane wrote
    only the genuinely missing **AVX-512 f32 16×16 network** — the exact item
    #98 recorded as its "Not done" follow-on. The larger win was unbriefed and
    came out of the required codegen inspection: **both** AVX-512 networks
    indexed their tile as a slice under a `debug_assert`, leaving a panic path
    per access (24 `ud2` for f32, 30 for f64) where AVX2/NEON already used the
    `try_into` fixed-array idiom; adopting it drops both to **1** and collapses
    the f64 body from ~3400 asm lines to **64**. The bit-exactness oracle was
    falsified before use (a no-op `_mm256_add_ps` injection fails it).
  - **Evidence standard for un-runnable ISA paths, settled rather than
    re-litigated:** #94 excluded AVX-512 networks for want of a real-silicon
    baseline; #98 landed one anyway. That reads as a contradiction but is not
    — this development host is an Arrow Lake Ultra 9 285K reporting
    `avx512f: false`, so no AVX-512 timing is *ever* possible here, and
    requiring it would mean the stack never ships an AVX-512 kernel. The
    operative split is: a **semantic** claim is verifiable (symbolic
    permutation algebra + the CI SDE job executing the real intrinsics) and a
    **performance** claim is not, so the latter is withheld explicitly rather
    than asserted. Both merged networks state their limits in-tree.
- **Gitlink hazard hit and corrected in the same cycle:** `git add repos/leto`
  stages the *submodule worktree HEAD*, which under concurrent agents was a
  peer's in-flight `perf/leto-matmul-parity-verdict` (`a8d9ae93`), not the
  merged head — and it silently skipped hermes, whose worktree trailed its
  published head. Corrected in `15292cb5` by setting both from `origin/main`
  via `update-index --cacheinfo` and verifying with `ls-tree`. Advancing a
  gitlink from a worktree HEAD is how an unmerged peer branch becomes the
  recorded stack revision.
- **Downstream integration verified, not assumed:** coeus `3875a8e1` is green
  on `main` with leto pinned at `14394eff`, which contains both leto soundness
  PRs — so the injectivity gates and window-exclusivity panics hold for the
  stack's largest leto consumer. The narrower kwavers risk (it filters the
  **columns** of a C-order array, exactly the interleaved views now gated) is
  closed by a contract test now in leto's own suite naming kwavers and its two
  file paths; both shapes pass, no leto defect surfaced.
- **Public-surface audit of the campaign's own output (2026-08-28):** ran
  `cargo semver-checks` over every crate this campaign touched, against each
  repo's pre-campaign baseline. `leto`, `leto-ops`, `hermes-simd`, and
  `hermes-simd-core` all report *no semver update required*. One real break:
  MN-458's removal of `Segment::is_owned_by` from the publishable
  `mnemosyne-memory-core` is `inherent_method_missing` — *"semver requires new
  major version"* — and it shipped labelled `[patch]`. Corrected in mnemosyne
  #80: recorded under CHANGELOG *Unreleased → Breaking* with the caller
  migration, item reclassified `[minor]`, no manifest bump (a completed item
  does not authorize a release). The removal itself stands — a forwarding
  wrapper keeps the whole-header retag reachable, which is the defect — and a
  stack-wide source scan finds no caller in any member.
  The generator is filed as **MN-460**: the repo publishes a crate but runs no
  semver gate. The item carries why it is not a one-line job — the Unreleased
  section already holds accepted breaking changes, so a gate diffing `main`
  against the published baseline is red on its first run and gets ignored; it
  must compare against the last release tag and fail only when the manifest
  version does not cover the detected class. Worth checking whether the other
  publishable members share this gap.
- **Third performance lane landed — the campaign's largest win (moirai #193):**
  the `ParallelIterator` terminal set stopped routing through `seq_items()`,
  which collected the whole stream and then ran a std sequential pass. At
  131072 elements, pinned to 8 P-cores: `par_iter().map(f).sum()`
  **391.25 µs → 11.18 µs (35×)**, `find_any` with an early match
  **412.92 µs → 5.13 µs (80×)**, `count`+`min`+`max` **1.156 ms → 36.93 µs
  (31×)**. The flagship rayon-displacement call was single-threaded with an
  O(n) allocation; the green comparison benchmarks had never covered it,
  because they exercise `map_reduce_indexed`, a different API.
  Terminals left sequential are recorded with reasons rather than quietly
  skipped (`fold`/`try_reduce` have one threaded accumulator and a doc-stated
  ordering contract; `position_*` cannot be given a correct logical offset
  because `Consumer::split_at` carries a *source* split point that a
  length-changing adapter invalidates). `sum`/`product` merge in index order,
  so results stay reproducible, but they are re-associated and therefore not
  bit-identical for floats — stated, not glossed.
  Measurement discipline worth keeping: the lane **quantified the noise band
  before claiming anything** (two runs of identical code differed by up to
  32%, so every ≤1.6× movement in that PR is unresolved and the headline
  numbers are one to two orders outside it), and **two optimizations were
  reverted because measurement rejected them** — an `Option`-slot owned split
  (2.79× slower: `Option<u64>` is 16 bytes where `u64` is 8) and folding
  `partition`/`unzip` across shards (2.3–2.4× slower, and slower even below
  the dispatch threshold, locating the cost in the accumulator rather than in
  parallelism). Both are recorded in-code so the attempts are not repeated.
- **Audit-contract change reviewed, not waved through:** that PR edited
  `benchmarks/tests/benchmark_contracts`, which pins parallel-iterator source
  text — the kind of edit that can quietly retire the guard for the defect
  being fixed. Verified: the removed markers pinned the *old* shape
  (`split_off(mid)`, the single-element base case, the reference-vector
  materialization) and their replacements pin the new one, with the
  reference-vector rebuild now explicitly prohibited. The `FoldConsumer` ban
  was narrowed rather than dodged by a rename: `8cd4286` is confirmed to have
  introduced `pub struct FoldConsumer<T, F>` as a two-field placeholder with
  **zero** `Consumer` impls, and the contract now bans that exact shape while
  *requiring* the trait implementation — strictly stronger than the name ban
  it replaced.
- **Moirai `main` was intermittently red before this wave, now fixed
  (moirai #194):** `scheduler_join_waits_for_queued_and_active_work` asserted
  `has_work()` after scheduling eight atomic increments on a two-worker pool,
  with nothing ordering the assertion before the workers drained them. It
  failed PR #191's merge run at `tests.rs:994`, and SHA `ff41a098` appears in
  the run list as both a success and a failure. The jobs now park on a gate
  the test holds until it has observed the work. Local repetition could not
  prove the race (60/60 on this 24-CPU host, which wins where a 2-core runner
  loses), so the variable was isolated instead: an identical 50 ms delay
  before the assertion makes the original **fail** and the gated version
  **pass**.
- **Last update:** 2026-08-28 22:20 EDT (session 03d80d33).

## ATLAS-LOCKFILE-GUARD-FLEETWIDE-2026-08-27 — Pre-commit lockfile guard delivered to every member with first-party deps [patch] — delivered 2026-08-27

- **Outcome:** the apollo pilot (`5602a20d`) is now fleet-wide: 21 PRs add the
  `check_staged()` surface to each member's `scripts/lockfile.py` (index-only,
  runs no cargo) plus the `.githooks/pre-commit` hook, so a lock flattened by
  the stack overlay can never enter a commit (`ATLAS-LOCKFILE-POISONING-
  GENERATOR-2026-08-26`'s cheapest option). One mechanical PR per member;
  content byte-identical to the pilot.
- **Delivered to (21):** hermes #75, leto #126, hephaestus #224, kwavers #662,
  aequitas #41, asclepius #29, athena #21, CFDrs #378, coeus #351, consus #57,
  gaia #36, helios #77, horae #30, hyperion #27, Mnemosyne #74, Moirai #169,
  proteus #22, ritk #213, themis #33, tyche #40, plus the harmonia regeneration
  #10 below. apollo already carried the pilot. Excluded: eunomia, iris,
  melinoe — true leaf members with no first-party git deps, so the guard's
  zero-source signature would false-positive.
- **Cross-repo defect found and fixed while the wave ran:** coeus main was red
  (E0432/E0425: `hermes_simd::LaneKernel`/`vectorize` unresolved) because its
  lock pinned hermes `ef40f43d`, which predates the `LaneKernel` API (hermes
  `0578c54`). The 2026-08-26 repin to `bbc7bdb5` was undone by coeus #350's
  later lockfile sweep. `cargo update -p hermes-simd` from outside the overlay
  advances hermes to `bc48334` plus four sibling providers (eunomia, melinoe,
  Mnemosyne, themis) to current heads; lock resolves under `--locked` and the
  full workspace checks clean. coeus #352. coeus #351's guard checks were red
  only on this pre-existing mainline break and go green once #352 lands.
- **harmonia was live-poisoned:** its committed `Cargo.lock` had 0 first-party
  sources against 4 declared git deps — flattened by the overlay and invisible
  because harmonia CI never passes `--locked` (and has no lockfile-guard job).
  harmonia #10 regenerates the lock outside the overlay (4 sources restored),
  adds `scripts/lockfile.py` (canonical Atlas copy) and the pre-commit hook.
  Harmonia also lacks the shared `lockfile-guard.yml` CI call — follow-up item
  if it wants CI parity with the fleet.
- **Tooling kept:** `scripts/apply-lockfile-guard.py` (the splice, verified
  byte-identical to the pilot) and `scripts/deliver-lockfile-guard-wave.sh`
  (the wave driver) are in atlas so the next guard update is one command, and
  serve as the freshness baseline for the member-local copies.
- **Merged 2026-08-27, same session:** all 21 guard PRs + harmonia #10 + coeus
  #352 (repin) merged green; atlas gitlinks advanced for all 22 members. All
  changes are tooling-only (local hook + script flag + one lockfile
  regeneration), so no downstream consumer lockfile updates are required.
  Post-merge CI confirmation on the moving heads is the standard hosted
  follow-up; coeus's post-merge runs were queued on runner starvation at
  record time, not failing.
- **Non-goals:** regenerating the other members' locks (none were poisoned);
  adding the lockfile-guard CI job to harmonia/eunomia/iris/kwavers/melinoe
  (separate item; kwavers' is peer-held #641).

## ATLAS-GITATTRIBUTES-DRIFT — line-ending policy differs across 26 members [patch] — in-progress (7 delivered 2026-08-29)

| ID | Outcome | Class | Status | Owner | Scope |
|----|---------|-------|--------|-------|-------|
| ATLAS-GITATTRIBUTES-DRIFT | One line-ending policy across the stack, applied to the blobs as well as declared. | [patch] | in-progress | unowned | every member's `.gitattributes` |

- **Delivered 2026-08-29 (7 members):** consus #58, gaia #37, helios #78,
  proteus #23, harmonia #11 — all `Normalize line endings to LF` PRs merged
  green (`.gitattributes` + renormalize + `.git-blame-ignore-revs`); atlas
  gitlinks advanced for all five. hephaestus already carries the policy
  (committed blobs were already 100% LF). Remaining without any policy:
  **apollo** (969 CRLF blobs, peer lane `perf/apollo-base128-arith` active on
  the tree — wait for a quiet point) and any member whose variant still
  differs from `* text=auto eol=lf`.
- **proteus #23 also fixed two real defects found on the branch:**
  book-pages.yml pointed `cargo-package` at `proteus` (an unrelated
  third-party crate on crates.io — package is `proteus-mat`, same root cause
  as the SemVer fix in proteus #20), and the shared workflow's default crate
  derivation (`pkg.replace('-','_')` → `proteus_mat`) does not match the
  `[lib] name = proteus` target, so `mdbook test` staged no rlib and every
  `extern crate proteus;` sample failed E0463. Fixed with an explicit
  `cargo-crate: proteus` input. Any other member whose `[lib]` name diverges
  from its package name needs the same input checked.
- **Evidence, measured 2026-08-26:** three members carry no `.gitattributes` at
  all -- apollo, consus, hephaestus -- and the 23 that do run eight distinct
  variants. Two dominate: `* text=auto eol=lf` (8 members) and `* text=auto`
  (9). The remaining six are elaborations of the same intent, not exceptions;
  nothing in the stack protects CRLF. `hermes` and `ritk` list per-extension
  rules, `ritk` additionally declares binary types.
- **Why it matters here specifically:** this fleet runs Windows and Linux
  agents against the same repositories. Without a declared policy the two
  produce different blobs for identical content, which surfaces as phantom
  diffs, merge conflicts on untouched files, and `warning: CRLF will be
  replaced by LF` on every commit. `ATLAS-CR-PATH-MANGLING-2026-08-25` was the
  same root cause reaching further -- it renamed every path on main with a
  trailing CR.
- **The declaration is the cheap half.** The blobs are already CRLF:
  969 of 1039 tracked files in apollo, 429 of 522 in consus, 641 of 659 in
  hephaestus. Adding `.gitattributes` without renormalising leaves git wanting
  to convert each file the next time anything touches it, so the churn arrives
  scattered through unrelated diffs, which is worse than the status quo.
- **Shape of the fix, per member:** `.gitattributes` and
  `git add --renormalize .` in one commit, plus a `.git-blame-ignore-revs`
  entry so the renormalisation does not bury `git blame`. Roughly 2000 files
  across the three that have none.
- **Sequencing:** not while a member has a live lane. apollo had a peer with 23
  uncommitted files when this was filed; a 969-file renormalisation under them
  would be hostile. Take each member at a quiet point, and prefer
  `* text=auto eol=lf` -- the worktree then holds LF on every platform, so
  tooling never has to detect which it is reading.

## ATLAS-LOCKFILE-POISONING-GENERATOR-2026-08-26 — Stale branches are downstream of overlay lockfile rewrites [patch] — delivered 2026-08-27

- **Finding.** Apollo carried 14 local branches with unique commits and zero open
  PRs. Four existed **only on this disk**: `cascade/hermes-07`,
  `codex/apollo-arch-006-junk-drawer-rename`, `codex/fix-apollo-package-sources`
  and `fix/apollo-fft-workspace-buffers` — junk-drawer renames, composite DFT
  wiring, lint gating, GPU workspace buffers. All four are now pushed to origin,
  so the work is no longer one cleanup script away from gone.
- **They share one cause, and it is not carelessness.** Every one of the four is
  refused by the `pre-push` lockfile guard: its committed `Cargo.lock` has no
  first-party git sources, because the stack overlay resolved them to local
  paths. Cargo reads config from the *workspace root* as well as the working
  directory, so any `cargo` invocation against a tree under `/d/atlas` picks up
  `/d/atlas/.cargo/config.toml` — including from a worktree lane, and including
  when the command itself is issued from outside the stack, which is the
  documented workaround and is **not sufficient**.
- **So the loop is:** agent builds, the lockfile is silently rewritten, a commit
  sweeps it in, the push is refused, the branch is abandoned. The stale-branch
  pile is the visible residue; the rewrite is the generator. Guarding at push
  time is late — the work is already committed and the agent has moved on.
- **Outcome:** the rewrite cannot happen silently. Options, cheapest first: a
  pre-commit guard so a poisoned lockfile never enters a commit; making the
  overlay not rewrite locks; or a wrapper that regenerates before commit.
  Whichever lands, `scripts/lockfile.py --regenerate` stays the repair path.
- **Delivered 2026-08-27:** the pre-commit guard is now fleet-wide — see
  `ATLAS-LOCKFILE-GUARD-FLEETWIDE-2026-08-27` for the 21-PR wave, the coeus
  cross-repo repin it surfaced, and the harmonia live-poisoning repair.
- **Acceptance oracle:** a build against a tree under the stack root, from any
  working directory, leaves `Cargo.lock` resolving under `--locked`; and a
  deliberately poisoned lockfile is refused before it can be committed.
- **Risk / change class:** [patch], tooling. **Non-goals:** integrating the four
  preserved branches — separate takeover items, each needing its lockfile
  regenerated before it can be pushed for merge.
- **Remaining inventory:** ten further apollo branches carry unique content and
  are already on origin, so they are visible integration debt rather than loss
  risk; `codex/apollo-stockham-throughput` is a live peer lane.

## ATLAS-CR-PATH-MANGLING-2026-08-25 — Every path renamed with a trailing CR on main [patch] — fixed 2026-08-25

- **Impact:** `main` was unusable for roughly the length of two commits. Every
  path in the repository carried a trailing carriage return — `repos` was
  `repos<CR>`, `.gitmodules` was `.gitmodules<CR>` — 274 names across 43 trees,
  recursively. Nothing resolved at the path it is declared at: no submodule
  could be read or advanced, and the workflows were not under
  `.github/workflows` where Actions looks for them.
- **Introduced by** `67df89bb`. **Not corrected by** `32fed8f7`, whose subject
  says it de-quotes root file names. The quoting in `git ls-tree` output
  (`".cargo\r"`) is a *display artifact* of a real CR byte inside the name, so
  removing quotation marks was never the fix and the tree stayed mangled.
- **Cause:** paths reaching `git` with a trailing `\r`, which is what a
  PowerShell pipeline produces when command output is split on `\n` without
  stripping the `\r` of a CRLF pair. Any `git add`/`update-index` fed from such
  a pipeline records the CR as part of the name — git accepts it, because a CR
  is a legal filename byte on the object side.
- **Fix** (`df375365`): every tree rebuilt with the CR stripped from each entry
  name, as a forward commit rather than a history rewrite. Content untouched —
  the repaired tree is byte-identical to the tree at `daadd057`, the last commit
  before the mangling. That equality also shows the two intervening commits
  changed no file content at all; whatever board edits `67df89bb` intended were
  not in the tree either before or after the repair.
- **Verified before pushing:** zero quoted entries recursively
  (`git ls-tree -r -t`), and an empty `git diff` against `daadd057`'s tree.
- **Guard worth adding, not yet filed as work:** a `pre-receive` or CI check
  rejecting any tree entry whose name contains a control character would have
  caught this at the push that introduced it, and is a few lines. The local
  `pre-commit` hooks did not, because they check *which* files are staged rather
  than what the names contain.
- **For agents on this stack:** when deriving paths from command output in
  PowerShell, strip `\r` before handing anything to git. `git status --porcelain`
  and `git ls-tree -z` are NUL-terminated and safe to parse; line-split output
  is not.


## ATLAS-CFDRS-SCHEMATICS-LAYOUT-ALLOCATION-2026-08-26 [perf] — implemented

The automatic schematic layout previously grouped node indices in a
`Vec<Vec<usize>>`, creating one heap-backed bucket per depth column before
computing coordinates. `cfd-schematics/src/visualizations/schematic/layout.rs`
now uses flat per-depth counts and row cursors with a second authored-order
pass. This preserves the existing depth ordering and every computed position
while removing the per-column bucket allocations and their index storage.
The existing indexed-layout and blueprint-materialization tests pass; no
rendering, topology, or layout semantics changed.

## ATLAS-PROVIDER-API-REPINS-2026-08-26 [integration] - Apollo/Hermes LaneKernel migration completed

Hermes now owns the capability-argument `LaneKernel::call(self, simd)` API,
and Apollo's merged `be10c9f2` implementation matches it. The downstream
consumer locks for Apollo, CFDrs, Coeus, Asclepius, Athena, Helios, Hephaestus,
Leto, and Ritk were repinned to Apollo `be10c9f27010435ee1fae2e08284a3e64e5971c3`
and Hermes `bbc7bdb593dc0bc95de7c6fb7840f92199c86fea`. The consumer scan found
no direct downstream `LaneKernel` implementations requiring source edits.

## ATLAS-APOLLO-FFT-LANEKERNEL-SIGNATURE-2026-08-26 [patch] - BatchedStages now matches the capability-arg trait

`apollo-fft` `BatchedStages::call` was implemented with one parameter; the
`hermes_simd::LaneKernel::call` trait now requires two
(`fn call(self, simd: Simd<T, A>) -> Self::Output;`). Every consumer that
compiled against `hermes_simd::vectorize(BatchedStages { ... })` on the new
trait signature broke at this single mismatch
(`error[E0050]: method 'call' has 1 parameter but the declaration in trait
'hermes_simd::LaneKernel::call' has 2`), so the kwavers-solver, hephaestus,
and coeus provider graphs all stopped compiling on top of the recent
`81e7de3a4fb36dce87cc2dc25e99420cb7165fd3` Apollo repin. Long-running PRs on
those providers were already blocked by the queue, and the signature
mismatch was the next wall behind it.

**Fix (commit `e9e5da80`, merged into apollo main at `2a447209`):** accept
the `simd: Simd<T, A>` capability token and use it. The implementation was
already pure-load/pure-store via `Vector::<T, A>::load_unaligned` and
`store_unaligned`, so the token is the only missing argument. The merge with
upstream apollo PR #121 (which was independently fixing the same trait
mismatch) replaced the placeholder with `simd.splat(twr)` for the
twiddle broadcasts — a clean improvement that the same diff carries.

**Local evidence at `2a447209`:** `apollo-fft --lib` 400/400 pass, all
`apollo-fft --tests` (5/5) pass, `cargo check -p apollo-fft --lib` clean,
`cargo check -p kwavers-solver --tests` clean, `cargo check -p kwavers
--tests --features full` clean. The Windows MSVC linker error in
`kwavers-solver` test build (`unresolved external symbol ... leto::iter`)
is a pre-existing kwavers-vs-leto integration issue, not caused by this
change — `cargo check` and the apollo-fft suite both pass on the same tree.

**Atlas integration:** atlas `repos/apollo` gitlink unchanged from its
existing `2a447209`; the apollo-fft fix rides the merge that already
absorbed PR #121.

Standalone lock guards pass for all affected consumers, with first-party source
counts of `64` (CFDrs), `41` (Coeus), `41` (Asclepius), `35` (Athena), `59`
(Helios), `33` (Hephaestus), `30` (Leto), and `51` (Ritk). Live-overlay checks
also pass for CFDrs `cfd-3d` trifurcation tests (`2 passed`), Coeus
`coeus-autograd/core/ops`, Asclepius, Athena, Helios, Hephaestus, Leto, and
Ritk focused package surfaces. No solver workload, timeout, numerical assertion,
or feature budget changed. Hosted full-workspace verification remains the
normal follow-up after these provider revisions are consumed in CI.

## ATLAS-CI-RUNNER-SATURATION-2026-08-25 — Hosted-runner queue depth delays every merge gate [patch] — in progress

- **Outcome:** a merge-gate run starts within its own runtime target, so a merge
  to a default branch is verified in minutes rather than landing unverified for
  the length of a queue.
- **Claim (2026-08-25, second session):** measurement instrument first.
  `scripts/atlas-ci-queue-report.py` pulls per-repository workflow-run metrics
  (queue minutes = created→run_started_at, run minutes = started→updated,
  event mix, conclusion mix) over a window and writes a gitignored report plus
  a stdout summary; the capacity-vs-load-shedding decision consumes its output.
  Kwavers CI scope itself stays with the first session's claims (PRs #641/#642).
- **Measured, full week ending 2026-08-25T21:00Z (`report-20260825T210157Z.json`,
  gitignored run output; stdout table reproducible via the script):**
  - Fleet total **3,164 runs / 491,507 work-minutes (~8,190 runner-hours)**;
    queue starvation is real but bursty: **4,796 queue-minutes**, concentrated
    in consus (3,142m), CFDrs (747m), kwavers (629m across 10 runs queued >5m),
    ritk (92m), Moirai (105m).
  - **kwavers alone burns ~330,900 work-minutes/week — 67% of the fleet** on
    ≥1,000 runs. Its consolidation is the first session's live claim (#641/#642
    preflight stack); no second actor enters that scope.
  - Next consumers with no active claim: hephaestus 14.2kh, Moirai 11.8kh,
    CFDrs 9.6kh, eunomia 9.3kh, tyche/horae/helios ~7–7.7kh each.
  - Event mix: pull_request 1,413 + push 1,195 (+553 dynamic-class); the PR
    matrix is the dominant consumer, matching load-shedding levers
    (path filters, draft skipping, scheduled heavy suites) before capacity.
- **Decision inputs now exist; next increment:** pick one non-kwavers heavy
  consumer and apply the cheapest lever with before/after numbers from this
  report as the baseline.
- **First lever applied (2026-08-25):** hephaestus — the largest unclaimed
  consumer (14.2kh/wk) — path-filters its four hardware workflows to their own
  crate + core + manifests + workflow file
  ([hephaestus PR #220](https://github.com/ryancinsight/hephaestus/pull/220) at
  `9977801`). Hosted runners skip hardware execution but were compiling each
  backend stack per unrelated PR (~26 min/PR across four workflows per #218
  evidence). workflow_dispatch retained for on-demand self-hosted runs;
  common-surface gates untouched. Before/after rides the report's weekly rerun.
- **Collected:** Mnemosyne PR #70 merged at `e9adfe8` (all real checks green;
  only recurseml report-only); Atlas mnemosyne gitlink advanced (`0a926abe3`).
  leto #123 merged (`1d4d687`, gitlink since advanced past it to `98486ebd`).
- **Second lever wave merged 2026-08-26:** CFDrs **#374** (concurrency
  cancel — its queue-to-work ratio was the fleet's worst at 828m queued vs
  741m worked) at `7df28ccd`; Moirai **#167** (Python-bindings path filter,
  was 61 runs × ~22 min/wk on Rust-only changes) at `a63a7153`; ritk **#209**
  (leto-linalg chapter → Athena, closing the ADR-0033 residue-scan doc drift)
  at `f444f3b3`. All three gitlinks advanced in one batch
  (`c259ddb58`). kwavers **#642** closed-superseded by the first session's
  #641 stack; its `Cargo.toml` O3 coverage-profile half is on kwavers main
  (confirmed `opt-level = 3` under `[profile.coverage]`), and the workflow
  wiring rides the peer's open #641 consolidation.
- **Measured 2026-08-25, ~20:00Z:** 27 runs queued across the fleet with one in
  progress — kwavers 14, hermes 7, helios 3, ritk 2, CFDrs 1. Hermes CI on
  `main` sat queued for over 50 minutes. Three merges landed during that window
  with their gate runs still unstarted.
- **Finding:** this is the queue-time rule's case — a job queued past its own
  runtime target is runner starvation, cured by capacity or load-shedding, and
  filed rather than absorbed as agent waiting. The dominant consumer is
  `pull_request`-triggered: kwavers alone had 3 Architecture Validation, 2
  benchmark regression, 2 Legacy Migration Audit, 2 Deploy mdBook, and 2 CI/CD
  Pipeline runs queued, several of them on the same PRs.
- **Third lever (2026-08-26): helios** — the board's next unclaimed consumer
  (~7–7.7kh/wk). Step-level measurement of its "slow" main runs shows the
  wall time is queue starvation *inside* the run, not compute: run 32436531185
  created 01:30Z with first job started 03:02Z — **92 queued minutes for ~5.7
  minutes of compute** across both jobs; run 32892598325's book build took
  2.6 minutes and its Pages deploy waited ~57 minutes to publish. Helios
  `ci.yml` carried no concurrency group, so superseded pipelines held queue
  positions behind live ones. The CFDrs-#374 lever applied verbatim:
  [helios PR #74](https://github.com/ryancinsight/helios/pull/74)
  (`ci/helios-ci-concurrency`, head `eb08279`), `group: ci-${{ github.ref }}`
  + cancel-in-progress; no gate, job, timeout, or trigger changes; all four
  PR checks green at open. Before/after rides the weekly report rerun.
- **Build-cache lever, fourth wave (2026-08-26): shared-key rust-cache.** The
  queue/load levers above cut queue time; this cuts the *work* time inside a
  green run. The destructive pattern is `actions/cache` keyed on
  `hashFiles('**/Cargo.lock')` caching `target/`: any first-party repin wipes
  the whole build cache and forces a full workspace rebuild on exactly the
  routine dependency-bump PRs. Mirrors the CFDrs #375 precedent
  (`Swatinem/rust-cache@6323deb1`, `shared-key`, `save-if` on `main` only).
  Applied to the two highest-remaining CI-gate consumers:
  - **ritk PR #211** (`perf/ritk-shared-rust-cache`, head `625ba675`): the
    3-OS nextest matrix (5,675 tests, 14.6kh/wk on the 2026-08-25 report)
    used the destructive lockfile-hash cache; now shared-key rust-cache with
    `workspaces: ritk` (checkout is a subdir).
  - **helios PR #75** (`perf/helios-shared-rust-cache`, head `e6de680`): the
    rust workspace job (~12 min build) used the destructive cache; now
    shared-key with `workspaces: .` (root checkout). Adds to #74's
    concurrency lever.
  - Already converged / correctly scoped elsewhere: Coeus (`6323deb1`,
    save-if), CFDrs (#375), python_ci rust-cache; apollo benchmark and helios
    benchmark keep their lockfile-keyed *source-only* caches (registry+git
    only, no `target/` wipe — correct for benchmark-baseline reproducibility);
    kwavers CI is peer-held (#641 consolidation).
  - **Starvation event 2026-08-26, ~16:00Z:** both ritk #211 and helios #75
    first check-runs died to `startup_failure`/`cancelled` with **every job
    `started_at: null` and no logs** — pure runner starvation, no check ever
    started, no code touched. This is the queue-time rule's case, not a PR
    defect; GitHub's auto-requeue has since re-enqueued both runs. Converge
    only on a terminal green after a runner is actually acquired.
  - **Recheck 16:35Z:** both PR runs (helios 32985441518, ritk 32985093134)
    still `queued`, but `ritk main`'s Deploy mdBook and Python CI completed in
    the same window — capacity is draining unevenly (main-push ahead of PR).
    Both PRs are MERGEABLE, CodeRabbit-passed, single-file workflow changes
    with validated YAML; convergence needs only runner capacity, no further
    code. Merge on terminal green, then delete both `perf/*-shared-rust-cache`
    lanes/branches.
  - **Fleet-wide build-cache audit complete (2026-08-26):** the shared-key
    rust-cache / `save-if` on-main pattern is now correct across every
    non-peer-held member — CFDrs #375, Coeus, apollo (with its deliberate
    `cache-targets: false`), plus the in-flight ritk #211 and helios #75.
    `hashFiles('Cargo.lock')`-keyed `target/`-wiping caches remain only in
    the correctly-scoped benchmark baselines (apollo, helios — source-only,
    no `target/`) and kwavers (peer-held #641).
  - **Build-cache wave delivered (2026-08-26, ~19:20Z):** both re-triggered
    (amended SHA against the drained fleet) and merged green on default:
    - **ritk #211** merged `7b6f22157`; post-merge `main` CI `33002036618`
      and Python CI `33002034936` both `success` (the cancelled `33000606*`
      legs were earlier starvation, auto-re-ran on the merged default).
    - **helios #75** merged `850db7bf`; post-merge gates green (rust
      workspace, python bindings, Lockfile).
    Lanes and remote/local branches (`perf/*-shared-rust-cache`) reclaimed.
    Both defaults now warm their shared-key caches from `main`, so the next
    first-party dependency-bump PR on each avoids a full `target/` rebuild.
    Atlas gitlink advancement for ritk/helios is the provider-graph step, done
    after the recorded post-merge CI is confirmed terminal.
  - **Fifth lever (2026-08-26): helios CI job split.** The `rust` job was a
    monolith running 11 sequential steps (fmt → clippy → tests → doctests →
    docs → book-check → mdbook-test → audit → deny) in one job, wall time
    ~27 minutes. Split into three parallel jobs sharing `shared-key: helios`
    cache:
    - `fast-lint` (timeout 10m): fmt, clippy, audit, deny — fails in ~3min,
      surfaces lint/dependency issues immediately.
    - `tests` (timeout 30m): nextest + doctests — the heavy path, writes
      cache from main only.
    - `docs` (timeout 15m): documentation + book-figure check + mdbook test.
    All three share one `Swatinem/rust-cache` entry via `shared-key: helios`;
    only `tests` writes (`save-if` on main). Wall time drops from ~27min
    sequential to ~18min (tests-bounded). Removed unnecessary `fetch-depth: 0`
    from all jobs (nothing reads git history). `python-bindings` and
    `benchmark-regression` unchanged.
  - **Sixth lever (2026-08-26): kwavers parallel-suite split.** The
    Architecture Validation `test-coverage` job serially ran the full test
    suite (lib 1224s + integration baseline 1017s) inside one 2284s ~38min
    job. Split into two parallel jobs — `test-coverage` (the lib suite) and a
    new `integration-suite` job — each keyed to the shared `kwavers` cache, so
    the integration baseline and unit coverage run concurrently. Expected wall
    ~21min from ~38min. [kwavers PR #661](https://github.com/ryancinsight/kwavers/pull/661)
    merged `e2485a03e`; distinct from the peer-held #641 consolidation
    (build-matrix/duplication work), which remains theirs. kwavers build-matrix
    (~17min) and CUDA (~11min) jobs are follow-up candidates after #661 lands
    green.
  - **Seventh lever wave (2026-08-27): the next unclaimed consumers.** The
    queue report's remaining heavy consumers without a lever were eunomia
    (9.3kh/wk) and tyche/horae (~7-7.7kh/wk each). eunomia's cache was
    default-keyed Swatinem (destructive on any lockfile repin) and tyche/horae
    had **no cache at all** — every PR rebuilt from scratch. All three got the
    shared-key rust-cache lever (one entry per repo, `save-if` on main only):
    eunomia #74, tyche #39, horae #29. themis #32 (the same lever on its
    two-OS verify job) was the fleet's only open PR at session start and merged
    green — gitlink advanced to `8c2e2cd`. All four merged same-session;
    eunomia's numpy job also gained the shared entry (it cold-compiled the
    workspace).
  - **Eighth lever (2026-08-27): consus shared-key rust-cache.** The weekly
    report rerun (`run-wall`) put consus as the fleet's **worst queue consumer —
    3,374 queue-minutes/wk** (ahead of kwavers' 1,207) plus ~7.7k work-min, the
    next heavy consumer without a lever (kwavers/hephaestus/CFDrs/Moirai/ritk/
    helios/eunomia/tyche/horae/themis all already claimed). consus's CI had a
    `concurrency` group already, but all six `Swatinem/rust-cache` sites were
    **default-keyed** — the default key hashes `Cargo.lock`, so every first-party
    provider repin (which consus does routinely via its "Normalize lock onto
    current provider heads" steps) wiped `target/` and forced a full 15-package
    rebuild across the 3-OS test matrix on exactly the routine dependency-bump
    PRs. Applied the shared-key lever (main-only `save-if`): root matrices
    (`check`/`test`/`msrv`/`test-mat-features`) → `shared-key: consus`, fuzz
    workspace (`fuzz-build`/`fuzz-run`) → `shared-key: consus-fuzz`
    ([consus PR #59](https://github.com/ryancinsight/consus/pull/59), head
    `808c816`, branch `perf/consus-shared-rust-cache`). YAML validated;
    `recurseml/analysis` report-only, gate jobs pending on the starved runner
    pool (the queue-time rule; converge on terminal green). Before/after rides
    the weekly report rerun.
- **Scope:** measure per-repository queue depth and minutes over a week, then
  choose between capacity (a self-hosted runner on owned hardware, which the
  workflow-hygiene rule already prefers for private repositories and would also
  give a warm shared `CARGO_TARGET_DIR`) and load-shedding (path- and
  scope-filtered triggers, draft-PR skipping, moving heavy suites to schedule).
  **Non-goals:** disabling a gate to shorten a queue.
- **Acceptance oracle:** queue time for a merge-gate run stays under its own
  runtime target on a normal fleet day, with the per-repository minutes report
  showing where the reduction came from.
- **Risk / change class:** [patch], infrastructure. **Dependencies:** none.
- **Note:** every increment delivered today was verified locally against its
  exact tree with the sanctioned runners, so the queue delayed confirmation
  rather than blocking delivery. That is the tolerable case; a red gate
  discovered an hour after merge would not be.

## ATLAS-HERMES-CONSUMER-ENTRY-2026-08-25 — Restore Hermes as the stack's lane-kernel owner [arch] — in progress

- **Outcome:** a consumer anywhere in the stack writes one generic lane kernel
  against `hermes-simd` and gets per-ISA machine code for it, so the provider
  table's assignment of "CPU lane-parallel kernels and ISA dispatch" to `hermes`
  holds in fact and not only on paper.
- **Finding:** four members carry lane-parallel ISA kernels outside Hermes —
  `apollo` (28 files, 90 `#[target_feature]`), `kwavers` (AVX-512 FDTD
  stencils), `CFDrs` (`cfd-core/src/compute/simd/`), and `moirai`
  (`moirai-utils/src/simd/arch/`). The common cause is upstream and is not a
  preference: Hermes exports no route into a `#[target_feature]` scope, so a
  consumer's generic kernel compiles at baseline features — the outcome Hermes
  ADR 009 exists to prevent. Full scan and per-file classification in
  `gap_audit.md`, finding 2026-08-25.
- **Sequence** (upstream first; a consumer migrated before the capability exists
  would have to invent a second abstraction over the first):
  1. `HS-FEARLESS-TOKEN-2026-08-25` in `hermes` — value-carrying capability
     token, a `vectorize`-class entry, and a safe operation surface over the
     existing facets. Filed, hermes PR #62 merged the audit that drives it.
  2. `ATLAS-APOLLO-ISA-FORK-2026-08-25` in `apollo` — largest consumer, filed
     and blocked on step 1.
  3. `kwavers` and `CFDrs` — file per-repo items once step 1 lands and step 2
     has established the migration shape. Not filed yet on purpose: their
     migration pattern should follow a worked example, not precede it.
  4. `moirai` — blocked on a topology question, not on step 1. The README
     places `moirai` below `hermes`, so it cannot take that edge without
     inverting the documented order, and neither crate depends on the other
     today. Settle the direction first; an ADR revision may be the deliverable
     rather than a migration.
- **Open ownership question:** `eunomia`'s packed-unpack intrinsics
  (`packed/unpack/intrinsics/{avx2,avx512,neon}.rs`) sit in Eunomia while the
  provider table gives packed-lane representation to Hermes, which re-exports
  them. Resolve when step 1 lands; Eunomia's F16C conversion path is its own
  bounded context and is not in question.
- **Acceptance oracle:** the `core::arch` and `#[target_feature]` census in the
  finding above is re-run and every consumer row is zero or a recorded
  sanctioned remainder, with each migrated family carrying differential tests
  against its scalar path and no benchmark regression against a recorded
  baseline. The census is the tracked metric and ratchets downward.
- **Risk / change class:** [arch] at stack level; each member's own increment is
  classified in that member.
- **Required authority:** Change on allowlisted repositories; no release.
- **Status 2026-08-25:** **step 1 delivered** — hermes PR #63 merged as
  `85655c05`, gitlink advanced. `hermes_simd::vectorize` plus `LaneKernel<T>`
  give a consumer one route into a `#[target_feature]` scope, and nine safe
  operations (`mul_add` and the cross-lane permutes) complete `Vector`'s
  surface for multiply-accumulate kernels. Codegen measured: 41 ymm-bearing
  instructions including `vfmadd213ps` with no call into the backend
  operations through the entry, against zero ymm and five outlined calls
  without it. ADR 016.

  Two things narrowed against the filed plan, both recorded in the hermes audit
  amendment: the safe surface already existed on `Vector` so only FMA and the
  permutes were missing, and ADR 011 needed no revision because it already puts
  the safe layer above unsafe facets. One unforeseen blocker was cleared on the
  way: `#[runtime_dispatch]` dropped doc comments, which is why no dispatcher in
  that crate could be `pub`.

  **Step 2 ran, and changed the campaign.** `apollo-fwht` was migrated onto the
  entry, measured, and reverted: 1.6x to 8.8x slower than the code it would
  replace across three dispatch placements (apollo PR #112, measurements in
  `repos/apollo/gap_audit.md#fwht-vectorize-negative`). Two structural
  mechanisms, now recorded upstream in hermes ADR 016 and its README:

  - The `#[target_feature]` scope does not follow a closure onto another thread,
    so wrapping a work-partitioning call applies the ADR 009 penalty by way of
    the mechanism meant to remove it.
  - Hermes' `Scalar` backend is a plain array loop the optimizer inlines and
    auto-vectorizes at the build's baseline ISA. For a bandwidth-bound
    elementwise kernel it beats an explicit backend path, because there is no
    arithmetic for wider registers to save and the dispatch boundary is pure
    overhead.

  **This item is therefore rescoped from a census to a measurement gate.** The
  `core::arch` counts identify candidates; they do not establish that migrating
  one is an improvement. Each family needs a before/after measurement, and a
  family that measures slower stays as it is with the measurement recorded.

  On that criterion `kwavers`' AVX-512 FDTD stencils are the most promising
  remaining candidate — compute-dense, large per-call work units — and `CFDrs`'
  elementwise `cfd-core` kernels the least. Steps 3 and 4 stay unfiled: filing
  them as migrations would presume the conclusion this measurement removed.
  Step 4 (`moirai`) remains gated on the layering question, not on the
  capability.

  The acceptance oracle above is revised accordingly: the census ratchets toward
  zero only for families a measurement supports converting, and a recorded
  sanctioned remainder now includes "measured slower under the entry".

## ATLAS-ATHENA-ALLOCATION-CONTRACT — warm solves allocate 4-6 small buffers per call on Linux [patch] — reopened 2026-08-26 (instrument PR open)

- **Owner:** current session (investigation + closure); pre-existing on `main`
  (4c8a9dc); blocked ryancinsight/athena#18 only by sharing the `verify` job.
  Unrelated to the LSQR damping work.
- **Symptom.** `crates/athena-leto/tests/allocation.rs`:
  ```
  repeated_cpu_solves_allocate_nothing_after_initialization     FAILED
  repeated_bicgstab_solves_allocate_nothing_after_initialization FAILED
  repeated_gmres_solves_allocate_nothing_after_initialization    FAILED
  ```
  Each failure reports `Stats { allocations: 4-6, deallocations: 17,
  reallocations: 2-6, bytes_allocated: 9-11 KB, bytes_deallocated: 881 }`.
  Local Windows runs of the same tests in isolation pass; the failure
  appears on the Linux hosted runner. The test contract is "warm solves
  must not touch the heap after the first call", which the GMRES and
  BiCGSTAB solvers do not currently satisfy.
- **Where to look first.** `crates/athena-core/src/solver/gmres/cycle.rs`
  (Arnoldi basis construction) and
  `crates/athena-core/src/solver/bicgstab/algorithm.rs` are the
  candidates; a `debug_assert!`-gated path or a small per-iteration
  allocation (rotation scratch, Givens pair, observer state) is the
  likely source. The exact `4-6 allocations` and `17 deallocations`
  pattern suggests a `Drop`-driven cycle (every iter creates and drops
  one or two small heap objects).
- **Acceptance.** The three `repeated_*_solves_allocate_nothing_...`  tests pass on the hosted Linux runner with `0, 0, 0` allocations,  deallocations, reallocations. CI gate green.
- **Investigation 2026-08-25 — verdict: no solve-path allocation exists.**
  - Line-level audit of `athena-core/src/solver/gmres/` (workspace.rs
    allocates once in `GmresWorkspace::new`; algorithm.rs only reads/writes
    pre-allocated fields: `hessenberg`, `cosine`/`sine`, `transformed_residual`,
    `coefficients`, block views; reset_cycle/rotation/back_substitute are
    index arithmetic) and `bicgstab/algorithm.rs` (same pattern): every warm
    call is statically zero-alloc on the happy path.
  - Backend primitives (`LetoBackend` copy/scale/axpy/dot/norm/residual) are
    plain slice loops with no Vec/alloc; `LetoVectorBlock` views are always
    contiguous (`as_slice` succeeds; `to_contiguous()` materialization in
    `spmv_into` is dead); `Identity` preconditioner is a passthrough;
    `residual_noise_floor` is scalar math. No `debug_assert!`-gated heap
    path, no Drop-driven per-iteration allocation anywhere in the measured
    region.
  - Local runs on Windows: `repeated_cpu…`, `repeated_bicgstab…` 0-alloc
    pass; `repeated_gmres…` 0-alloc passes at `--run-ignored` in both debug
    and release. The `4-6 allocs / 17 deallocations` Linux signature has
    more frees than allocs, which no drop cycle of owned buffers can
    produce — it is allocator-internal churn (glibc per-thread arenas)
    observed via `stats_alloc::Region` under a multi-threaded nextest
    runner, not solver-heap traffic.
  - CI at the merged head `21318ae` (post-PR #18) is green (`success`),
    with the GMRES test `#[ignore]`d per `fce0f5b` (`ATLAS-ATHENA-ALLOC-001`);
    the flake is gone from the hosted gate. The original acceptance oracle
    (0/0/0 on the hosted runner) is not independently re-verifiable from
    this Windows host, so the ignore remains the safe gate until a Linux
    runner confirms it.
- **Not in scope of ATLAS-LSQR-STAGE-C-INCOMPLETE.** Closed with the
  evidence above; reopen only if a hosted Linux run re-reports non-zero
  allocations (then instrument with `MALLOC_ARENA_MAX=1` / trace before
  touching solver code).
- **Reopened 2026-08-26 — the closed state was gate-vacuous, and the reopen
  trigger fired.** Two findings:
  1. **Vacuity:** with the GMRES contract `#[ignore]`d, hosted CI reported
     "80 passed, 1 skipped" — the skip *is* this contract, so the allocation
     guarantee had no hosted coverage between 2026-08-25 and today. The
     prior closure's own condition ("safe gate until a Linux runner
     confirms it") was never discharged because no job ran the test.
  2. **Trigger:** the 2026-08-26 instrument rerun (below) passed the strict
     contract — confirming nondeterminism — but nothing in the gate would
     have caught a recurrence.
- **Correction delivered (athena PR
  [#20](https://github.com/ryancinsight/athena/pull/20), head `9963804`):
  instrument, don't guess.**
  - Classifier test `warm_solve_heap_traffic_is_bounded_and_not_retained`:
    measures 16 then 32 warm solves in separate regions; fails only when
    traffic *scales* with repetitions (solve-path allocation) or bytes are
    *retained* (leak). An environment-fixed burst passes with its shape in
    the report. This operationalizes the glibc-arena verdict: if that
    verdict is wrong and a solve path allocates, the doubling measurement
    catches it; if it is right, the burst stays fixed-size and balanced.
  - New `allocation-instrument` CI job runs both ignored contracts with
    `--run-ignored ignored-only`, so the strict zero-traffic expectation
    and the bounded-noise classification are both permanent hosted evidence
    on every push instead of skipped silently.
- **Hosted evidence at PR head:** Allocation instrument job green on Linux —
  including the strict zero-traffic GMRES contract, which reproduced no
  allocations on this rerun. Combined with the original failure and the
  Windows passes, this confirms the flake is nondeterministic environment
  noise, now permanently discriminated from a real defect by the classifier
  without human triage. Local Windows at `9963804`: default suite 2/2,
  ignored suite 2/2, clippy `-D warnings` clean, YAML validated.
- **Acceptance update:** strict contract enforced on hosted Linux every
  push via the instrument job; classifier red = real defect, classifier
  green + strict red = bounded environment burst (shape recorded).
  Unconditional re-enable of the strict test remains blocked until the
  environment cause is named (`MALLOC_ARENA_MAX=1` experiment still the
  first probe).
- **Investigation 2026-08-31 — full root-cause audit, solver path exonerated.**
  Line-level audit of every allocation site the warm solve can reach:
  - `athena-core` is `#![no_std]`; `GmresWorkspace::new` allocates once
    (hessenberg, cosine, sine, transformed_residual, coefficients, work_basis_dot);
    `reset_cycle` fills in place; `SolveReport` and `Termination` are
    `#[derive(Copy)]`; `ConvergencePolicy` is `#[derive(Copy)]`; `SolveError`
    is a stack enum with no `Vec`/`String`; `NoObserver` is a ZST.
  - `athena-leto` backend: `LetoPreparedDot`/`LetoPreparedNorm` are ZSTs;
    `copy`/`scale`/`axpy`/`dot_prepared`/`norm_l2_prepared`/`residual`/
    `fused_cg_update`/`combine_direction` are plain slice loops with no `Vec`/
    `format!`/`Box` on the happy path. `LetoVectorBlock` is `VecStorage<T>`
    (plain `Vec<T>`); `view`/`view_mut` return `as_slice` slices — no alloc.
  - `leto_ops::dot`: shape comparison is stack (`[usize; N]`), `as_slice`
    path calls `T::dot_slice`; `ShapeMismatch` allocates `Vec<usize>` only on
    the error path, never taken in warm solves.
  - `leto_ops::spmv_into`: shape checks allocate only on error; happy path
    goes to `spmv_slice_into` (plain row loop); `to_contiguous()` fallback
    is dead for workspace vectors (always contiguous).
  - `hermes_simd::dot` via `#[runtime_dispatch]`: generates
    `std::is_x86_feature_detected!` per dispatch site, cached in
    `OnceLock<bool>` — no heap allocation (inline storage). `SimdView::new`
    stores a pointer + `PhantomData`; `is_runtime_supported` calls CPUID
    directly on x86_64 — no allocation.
  - `stats_alloc::Region` and `Stats` are `#[derive(Copy)]`; `StatsAlloc`
    wraps `System::alloc`/`dealloc` with atomic counter increments — no
    allocation from the instrumentation itself.
  - **Verdict:** the solver path is provably zero-allocation. The 17
    deallocs with only 4 allocs (more frees than allocs) cannot be produced
    by any `Drop` cycle of owned buffers — it is glibc per-thread arena
    cleanup of pre-region allocations observed through the `stats_alloc`
    global wrapper. The companion classifier test already discriminates
    correctly: fixed-size burst = environment noise, scaling = real defect.
  - **Experiment delivered:** `MALLOC_ARENA_MAX=1` env var added to the
    `allocation-instrument` CI job (athena `.github/workflows/ci.yml`).
    Pinning glibc to a single arena eliminates per-thread tcache churn.
    If the strict zero-traffic contract passes under this pin on hosted
    Linux, it names glibc arena churn as the environment cause and clears
    the way for unconditionally re-enabling the strict test. If it still
    reports non-zero traffic, the investigation reopens with a named
    non-arena source to trace.
  - **Local Windows verification** at `d433d34`: default suite 2/2,
    ignored suite 2/2 (both GMRES strict + classifier), YAML validated.

## ATLAS-KWAVERS-CI-COVERAGE-OPT-2026-08-25 — Bound full-workspace test topology [perf][patch] — hosted verification pending

- **Owner:** current session; lane `worktrees/kwavers-ci-coverage-opt`,
  branch `perf/kwavers-test-coverage-profile`, PR
  [#642](https://github.com/ryancinsight/kwavers/pull/642) at `e1ecdd231`,
  stacked on PR #641 head `84ba553ef`.
- **Evidence (measured on ryancinsight/kwavers main, successful runs):**
  Architecture Validation wall 33–67m across recent runs, with the job's
  own queueing adding ~30m beyond its longest member; inside it,
  **Test Suite Coverage 35m19s** dominates (next: feature-matrix jobs
  9–14m each, Validate Clean Architecture 11m41s). CI/CD Pipeline runs
  ~37m. All far past the five-minute verification target.
- **Root causes found in Test Suite Coverage:** it had no rust-cache, serialized
  independent tests to one process, and rebuilt the disjoint full-feature
  doctest graph after the large workspace suite.
- **Hosted falsification and correction:** head `5c49bb2c` completed the
  5,759-test suite in 9m43s after an 18m53s cold compile, PINN in 4m01s,
  and bounded full-grid simulations in 4m26s, then exhausted the unchanged
  45-minute cap rebuilding the disjoint full-feature doctest graph. Commits
  `63513fca1` + `ed44d3d52` first moved that doctest to Documentation and
  bounded nextest/Rayon concurrency. Commit `27c88e88b` then corrected the
  profile strategy: Test Suite Coverage stays on the shared dev graph, both
  initial nextest invocations run at two processes with two Rayon workers,
  bounded full-grid binaries retain the default profile's complete
  `full-grid-sim` grouping, and artifact measurement remains `target/debug`.
- **Correctness correction (workload/timeout unchanged):** the proposed O3
  coverage-profile change is removed. Rust instrumentation coverage warns that
  optimized-out functions can make coverage results unprocessable, so an O3
  timing win is not coverage-correctness evidence. `Cargo.toml` has no remaining
  behavior delta; speed comes from the pinned shared cache, bounded 2x2
  concurrency, and eliminating duplicate doctest compilation. YAML, locked
  metadata, diff checks, and independent static review pass.
- **Next:** collect PR #642's hosted rerun; if green, record the new
  Test Suite Coverage duration and tighten the 45-minute timeout toward
  measured + 20% variance in a follow-up commit (bound tightening follows
  evidence, never precedes it).
- **Follow-up sweep 2026-08-25 — full pipeline job-time baseline measured**
  (CI/CD Pipeline run `32877332731`, the successful proteus-mat adoption
  run; own times, sorted):
  | job | own time |
  |---|---|
  | Heavy Validation (reviewed profile) | 41.6 m |
  | Code Coverage | 33.4 m |
  | Build & Test (beta) | 20.2 m |
  | Build & Test (nightly) | 18.6 m |
  | Build & Test (stable) | 17.4 m |
  | PINN Convergence / Benchmark Smoke / Solver Validation / PINN Feature | 11.5–12.9 m each |
  | Code Quality / Miri / Security Audit / Lockfile / Python Surface | 0.9–5.0 m |
  Pipeline wall 136 m, Architecture Validation wall 110 m on the same
  evening — both dominated by hosted-runner queueing (24+ ubuntu-latest
  jobs per PR across the two workflows), not by any single job's work.
  Live confirmation the same hour: PR #647's ci.yml run sat queued
  26 minutes and PR #642's Architecture Validation run 34 minutes
  before their first job started — with every workflow already carrying
  cancel-in-progress concurrency. The residual lever is structural:
  consolidate jobs or add runners; that is a user decision. A same-hour
  snapshot found **25 active workflow runs across seven concurrent peer
  branches** (`fix/kwavers-run-compiled-tests`, `test/kwavers-spectral-
  laplacian`, `ci/kwavers-build-matrix-timings`, and this session's three)
  — the queue is contention between parallel agent lanes on one repo, so
  lane scheduling is part of the fix alongside any job consolidation.
  Two cache defects found and fixed:
  - **Heavy Validation** used a private branch-scoped `actions/cache`
    whose key never matches on PR checkouts — every PR run recompiled the
    workspace from an empty `target/`, which is exactly the cold-cache
    budget its 45 m timeout was sized against (the 2026-08-23 note).
    Switched to the shared-key rust-cache (PR #647, `7cb10de8f`); timeout
    deliberately unchanged until a warm-cache measurement confirms.
  - **Code Coverage** had no cache at all: every run compiled tarpaulin
    0.37.0 from source and refetched registry/git before the instrumented
    build. Added a coverage-dedicated actions/cache (registry + git +
    tarpaulin binary, key separate from the uninstrumented shared key) and
    skip-if-installed (PR #648, `135d1ab89`).
- nextest timeout topology (`nextest.toml`) audited in the same sweep:
  default 60 s per-test / 15 m suite, ci 10 m, heavy 300 s with a
  documented 600 s override for `nl_swe_workflow` — already evidence-based,
  no change.
- **Outcome 2026-08-25 late:** PR #647 (Heavy Validation shared rust-cache)
  merged at `e78a4e8`; its first hosted run already showed Heavy Validation
  41.6 m → 33.6 m with the shared entry restored. PR #642 was folded into the
  peer lane #641 by its owner (`ea504bf`) to avoid a duplicate CI matrix —
  workload preserved. PR #648 (coverage cache) was briefly auto-closed in the
  #647 merge race and reopened; checks re-running.
- **Queue-time quantified across members 2026-08-25 night.** The bottleneck is
  not job duration anywhere anymore — it is hosted-runner wait:
  - athena: wall 30.4 m, own work 3.3 m (queue 15–30 m per job);
  - CFDrs: max queue 59 m against 15 m of own work;
  - ritk: max queue 74 m;
  - coeus: 60 m queue on a single-job run;
  - kwavers: PR #650's checks sat queued 36+ minutes before first start.
  Every workflow already carries cancel-in-progress. The levers are (a) job
  consolidation across the per-member matrices, (b) larger runner quota or
  self-hosted runners, and (c) lane-scheduling discipline between concurrent
  agent sessions. All three are user decisions; the data above is the input.
  Cache fixes like #647/#648/#375 remove the *work* side; queueing now
  dominates every member's PR wall time.
## ATLAS-KWAVERS-SWE3D-BASELINE-REGRESSION-2026-08-26 — integration oracle regression on main [major] — diagnosed locally 2026-08-26

- **Owner:** unclaimed; scope: `repos/kwavers` (integration baseline + SWE 3D
  validation test).
- **Symptom.** Architecture Validation → Test Suite Coverage on **main**
  fails with: `integration regression: kwavers::swe_3d_validation
  volumetric_tracking_covers_non_pml_domain` (1 of 681 integration tests;
  "Refresh with: scripts/integration_tests.py --update" suggested by the
  gate). Present in main runs 32921558574 and 32914486868 — the check has
  been red on the default branch across at least two runs.
- **Not caused by any open PR:** kwavers PR #650 (CSR interpolator) shows the
  identical failure while its 5,764-test lib suite passes; evidence comment
  recorded on the PR.
- **Decision needed before mechanical refresh:** the gate offers
  `--update`, but refreshing an oracle to make a red gate green hides a real
  numerical change if one occurred. First diff the stored baseline against a
  local run of `volumetric_tracking_covers_non_pml_domain`: if the delta is a
  genuine solver-behavior change, find the merging commit that moved it
  (`git bisect` over recent main merges: #622 run-compiled-tests, #638 viz
  config unify, #640 learning-rate schedule are candidates); if it is
  platform noise (the baseline was regenerated on a different runner), then
  `--update` is the correct fix and should note that in its commit.
- **Local diagnosis 2026-08-26:** the current Kwavers main tree has an empty
  integration baseline, and the focused test passes unchanged:
  `volumetric_tracking_covers_non_pml_domain` reports `100.0%` coverage and
  `12,544` valid points, matching `(40 - 2*6) * (40 - 2*6) * (28 - 2*6)`.
  The failure is therefore not reproducible from the current source and no
  baseline refresh is justified. The hosted runs remain historical evidence;
  the item stays open until a fresh full hosted integration run confirms the
  baseline is green.
- **Full local integration run 2026-08-26 (head `9982b37f`, the merge that
  absorbed the right-sized-grid fix `252d86716`):** `cargo nextest run -p kwavers
  --tests --no-default-features --features full --test-threads=1 --no-fail-fast`
  reports `681 tests run: 681 passed (9 slow), 27 skipped`, `Summary [266.087s]`,
  zero `FAIL` and zero `TIMEOUT` lines. The 60×60×40 grid that timed out hosted
  runners is gone; the 40×40×28 grid keeps every non-PML voxel asserted by the
  test and the sweep runs in 4 m 26 s locally, comfortably below the 25-minute
  script bound and the 45-minute coverage job bound. The local
  `scripts/integration_tests.py` cannot enforce here because the Atlas overlay
  Cargo.lock is stale against the `--locked` flag it carries; that is an
  environment blocker, not a regression.
- **Status:** local evidence closes the diagnosis; the item stays open until a
  fresh hosted integration run at the merge head returns `success`. A
  `--update` is not justified, because no test is currently failing and an
  empty baseline is the correct shape.
- **Local escape restored (kwavers PR #653 at `8165488c2`, merged 2026-08-26):**
  `scripts/integration_tests.py` was made unconditionally `--locked` when the
  baseline was eliminated, which makes the gate unrunnable on a tree under
  the Atlas development overlay (the overlay redirects first-party crates to
  local paths, so cargo refuses before the suite starts). The PR adds an
  `--unlocked` flag that drops the flag for local runs; CI keeps the locked
  default, so the committed-lockfile check is unchanged. All 24 real hosted
  checks pass on the exact head (lockfile 1m36s, audit burn 8m, audit legacy
  2m, all feature combinations 5–19m, build stable/beta/nightly 1–7m, CUDA
  10m, code coverage 32m, code quality 10m, doc 14m, heavy validation split
  legs 7–14m, integration runner windows 1m, layer boundary 21s, miri 4m, PINN
  feature 12m, python typed 1m, security 2m, solver validation 6m, test suite
  coverage 40m, validate clean architecture 3m). The local `--unlocked` run
  reproduces the canonical evidence from the prior diagnosis:
  `integration suite: 681 tests run, 0 failed; no regressions; 0 known
  failures unchanged` (matching the empty baseline). The command-form check
  that earned its place — splitting `--color --locked` at the wrong index
  produces a silent nonsense value with no `--locked` — is now part of the
  test surface. `recurseml/analysis` is the always-report-only error.
- **Acceptance:** main's Test Suite Coverage green; either the baseline is
  refreshed with a justification, or the solver change that moved the result
  is identified and reviewed. The local escape is now in place so the next
  hosted regression can be diagnosed against the same gate the CI runs,
  without reconstructing the command by hand.
- **Two new integration regressions observed locally 2026-08-26** at
  the post-`#653` / `apollo-fft`-signature-fix tip `dddb75c12` (the same
  tip the SWE 3D sweep is run from):
  1. `pstd_finite_window_born source_phasing_is_frechet_derivative`
     panics with `full=6.675873e-3, half=1.121181e-2`. The test asserts
     `half.normalized_residual < full.normalized_residual` (Born residual
     must converge under contrast refinement) and the half-resolution
     residual is now larger than the full. The test was added in commit
     `586f16858 fix(kwavers): Eliminate integration baseline` and has no
     history of passing, but no prior sweep caught it because the
     integration runner was only running four named binaries before
     #653. The PSTD solver has had six recent refactors
     (`b2cd15d37 fix(kwavers-physics): a caller's absorption coefficient
     reach the solver`, `b20158763 fix(kwavers-solver): give plugins the
     sources they are handed`, `247b0e97c refactor(kwavers-solver): slice
     fill for CPML scratch`, `4ea703892 refactor(kwavers-solver): remove
     elastic config placeholder`, `a81f8a6e6 refactor(kwavers-solver):
     complete debug field coverage`, plus the elastic/config placeholder
     removal); one of these likely changed the source-phasing path
     without the Born contrast test catching it because the prior runner
     was only running `swe_3d_validation`/`nl_swe_workflow`/`kuznetsov`/
     `absorption_decay`. Bisect is the next step, not a `--update`.
  2. `pinn_ic_validation test_ic_combined_loss_decreases` panics on
     `kwavers-solver` link errors under the dev overlay — the Windows
     rust-lld 17.1 link line and `pyo3-ffi 0.29.2` symbol resolution
     cannot produce the test binary in the local 60s window. The
     integration runner invokes the same `cargo nextest run` invocation
     that compiles the test binary, so the same link error is what
     the CI runner hits. A separate clean-room build with no
     overlay resolves it; the defect is the overlay, not the test.
- **Optimisation lever applied in this item: kwavers PR
  [#664](https://github.com/ryancinsight/kwavers/pull/664) at head
  `03ca874b` switches `scripts/integration_tests.py` from
  `--test-threads=1` to `--profile ci --no-fail-fast`. The committed `ci`
  profile carries `test-threads=4`, the `integration` group cap of
  `max-threads=2`, and the `full-grid-sim` / `gpu` groups'
  `max-threads=1`. The 4-core hosted runner's 681-test sweep went from
  17m28s to (projected) ~8m; the local run was 4m26s of which all but
  2s was the single-threaded serialization. The no-fail-fast intent is
  preserved (`--no-fail-fast` overrides the profile's `fail-fast=true`).
  Re-enable trigger: the test pair above must be passing on the
  current main before the lever can land.

- **ARCH-008 gaia CSG assessment 2026-08-25 — recorded correct-as-jagged.**
  `gaia/src/application/csg/boolean/indexed.rs` sites (`remap_binary_face_soups`
  :254, `components` :1130/:1304) are per-operand face-soup groupings built
  once per boolean operation, each operand's list growing independently — the
  moirai `channel_fusion` pattern. No traversal-hot path; conversion would add
  complexity without a win. Not claimed.
- **ARCH-008 seventh conversion opened off this sweep** — kwavers conservative
  interpolator transfer matrix → CSR (PR #650). The bench's byte-parity gate
  caught that `leto::Array3` indexing is x-major before any timing ran; the
  per-entry unravel stays. Measured: −22% at refine_4, +5% at refine_2
  (win grows with entries-per-row), recorded honestly on the PR.

## ATLAS-KWAVERS-HEPHAESTUS-CONTRACT-2026-08-21 — Define the neutral visualization handoff [major][arch] — in progress

- **Owner:** Atlas integration coordination with Hephaestus provider review.
- **Decision record:** `docs/adr/0054-kwavers-hephaestus-visualization-contract.md`.
- **Current evidence:** Kwavers `kwavers-analysis` still constructs WGPU
  instances, adapters, devices, queues, buffers, and `pollster` waits in its
  visualization transfer/renderer modules. Hephaestus exposes backend-neutral
  `ComputeDevice` and backend-specific WGPU implementations, but no existing
  visualization-specific role contract was found.
- **Contract increment:** the proposed seam is limited to backend acquisition,
  typed field upload, dimensions/range metadata, transfer receipts, and typed
  unavailable-capability errors. It deliberately excludes renderer/shader API,
  CPU fallback, and raw device/resource handles.
- **Ownership:** analysis computes neutral field metadata; Hephaestus owns all
  concrete WGPU objects and synchronization. The implementation must be placed
  at the deepest existing shared contract boundary to avoid the current
  `kwavers-gpu -> kwavers-analysis` dependency cycle.
- **Next gate:** provider owners must review the role signatures and create
  clean lanes from fetched defaults before any provider source edit. No dirty
  checkout, branch, lockfile, or Atlas gitlink is changed by this design step.

## ATLAS-KWAVERS-ALLOC-PROBE-DENY-DOCS-2026-08-21 — Pilot deny(missing_docs) [patch] — in progress

The `missing_deny_docs` assessment found 114 of 118 flagged crates have
undocumented public items, so the directive cannot be safely added without
per-crate provider work. This pilot picks the one crate that is trivially
safe — `kwavers-alloc-probe` — a single-file crate (no submodules) with
every public item already documented, to demonstrate the pattern and drop
the count by one.

**Scope:** `crates/kwavers-alloc-probe/src/lib.rs` on a clean lane based on
fetched `origin/main` `377a98c8`, plus root PM records.

**Acceptance:** `#![deny(missing_docs)]` compiles without missing-docs errors;
format, check, warning-denied Clippy, nextest, doctests, and rustdoc pass;
the branch is published for review.

**Implementation evidence (2026-08-21):** clean lane branch
`fix/kwavers-alloc-probe-deny-docs` is based on fetched `origin/main`
`377a98c8670bb4c8c2750a032b1418ceeab60172` and publishes commit
`aa5ab2bc` — one line added after the existing
`#![doc = include_str!("../README.md")]` attribute. Format, check, clippy
(`-D warnings`), nextest (0 tests — probe library), doctests (1 ignored),
and rustdoc all pass on the clean lane.

Published as PR
[#598](https://github.com/ryancinsight/kwavers/pull/598) at exact head
`aa5ab2bc94ba31dbd5f7438aaef41195e9bf5c8e`. Hosted checks are the
acceptance oracle; merge only at the exact PR head after terminal required
checks. The dirty primary Kwavers checkout and Atlas gitlink remain
unchanged.

- **Hosted hold (2026-08-21):** PR #598 is `MERGEABLE` but `UNSTABLE`; all
  25 workflow runs (CI/CD Pipeline `32521893944`, Architecture Validation
  `32521893980`, benchmark regression `32521893996`, Legacy Migration Audit
  `32521894011`, Deploy mdBook `32521894392`) remain `queued` after 56
  minutes of observation across two re-check cycles. CodeRabbit passed;
  `recurseml/analysis` is errored (report-only). No runner has picked up a
  single job. No pointer advance or bypass is authorized; re-open on
  terminal provider checks or a hosted state transition.

## ATLAS-KWAVERS-PYTHON-GENERATOR-2026-08-21 — Add defaults and NumPy protocols [minor] — in progress

- The generator now records PyO3 defaults and keyword-only markers, translates
  registered NumPy array parameters/results to `numpy.ndarray`, and records
  unresolved defaults explicitly in the inventory.
- The generated surface covers 384 functions and 25 module-registered
  classes with class method/property surfaces including `Grid` constructors
  and getters. It has zero unresolved defaults, contains no `Any` or ellipsis
  placeholders, and the facade now has zero missing registered imports or
  `__all__` exports; only intentional `__author__`/`__version__` metadata
  extras remain.
- Generator-focused pytest passes `5/5` without loading the unavailable native
  extension. Native wheel smoke and runtime export execution remain open.

## ATLAS-KWAVERS-PYTHON-GIL-2026-08-21 — Detach Simulation.run [minor] — in progress

- `Simulation::run` now accepts the hidden PyO3 `Python<'_>` token, clones the
  backend-neutral grid/medium/config inputs, and executes `SimulationRunner::run`
  inside `py.detach`. The detached closure captures no pyclass or Python handle.
- Added `tests/test_simulation_gil.py`, an event-based Python-thread regression
  that requires concurrent Python progress and verifies the returned result's
  time-step count, sensor shape, and finite values.
- Provider `cargo check -p kwavers-python --lib` passes. The full provider
  formatter remains blocked by pre-existing peer-owned formatting drift in
  `kwavers-medium/src/absorption/stokes.rs`; no unrelated formatting was
  applied. Native wheel/runtime execution remains pending until a built
  extension is available.

## ATLAS-BOOK-FIGURE-CLOSURE-2026-08-21 — Restore generated validation figures [patch] — in progress

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

## ATLAS-CFDRS-PYTHON-GIL-2026-08-21 — Complete PyO3 solver GIL boundaries [minor] — in progress

- Provider commit `575375e85ef0e4344461e3eb2635d28d10ad5997` adds
  `Python::detach` around every remaining input-sensitive cfd-python solver
  computation, keeps NumPy conversion under the GIL, and adds bounded
  Python-thread regression coverage. Local formatting, locked check, warning
  denied Clippy, Rustdoc, abi3 wheel build, and the new concurrency test pass.
- Full wheel tests pass `4`; one pre-existing dirty-main mismatch remains at
  the Casson/Newtonian branch constant (`0.0035` versus a peer expectation of
  `0.00345`). Mypy is unavailable and cdylib doctests are unsupported.
- PR [#365](https://github.com/ryancinsight/CFDrs/pull/365) is published at
  that exact head. The worker temporarily reused the clean CFDrs format lane;
  after publishing, the lane was restored to `fix/cfdrs-format-gate` at
  `c1e4fdcf`, preserving PR #361's scope. Atlas's CFDrs pointer is unchanged.
- **Hosted hold:** PR #365 is `mergeable=false`/`dirty` with no Actions runs
  returned for the exact head; `recurseml/analysis` is errored and CodeRabbit
  is rate-limited. The live Pages book is HTTP 200, but docs.rs/crates.io have
  no `cfd-python` artifact and the existing PyPI name belongs to an unrelated
  package, so release identity remains unresolved. The stale `0.0035` versus
  `0.00345` test expectation and an unrelated existing Clippy blocker remain
  provider-side residuals.
- **Verification residual:** the new Python-thread test detects progress with
  bounded waits and a large deterministic workload, but does not yet meet the
  repository's event/barrier-only synchronization preference. Re-open on a
  clean CFDrs lane; do not displace PR #361's restored format lane.

## ATLAS-KWAVERS-VIS-CONFIG-2026-08-25 — Make visualization selection and quality single-source [major] — blocked

- **Owner:** current session. **Scope:** Kwavers visualization configuration,
  renderer quality propagation, focused tests, Rustdoc/README/CHANGELOG, and an
  indexed Kwavers ADR. **Non-goals:** no provider ownership change, fallback,
  rendering algorithm change, or backend-specific configuration in
  `kwavers-analysis`.
- **Outcome:** top-level Kwavers `VisualizationBackend::{Leto, Hephaestus}` is
  the only backend-selection source. The ignored `gpu_enabled` boolean and
  duplicate `render_quality` field are deleted; adaptive quality changes the
  renderer configuration that subsequent frames use.
- **Acceptance oracle:** stack-wide search finds no `gpu_enabled` or
  `render_quality`; backend conformance and real Hephaestus pipeline tests
  remain value-correct; focused analysis tests prove quality transition and
  renderer propagation; formatting, warning-denied Clippy, Nextest, doctests,
  Rustdoc, and SemVer classification pass on the exact delivered revision.
- **Risk/dependencies:** `[major]` because two public configuration fields are
  removed. The active Proteus package-rename branch touches only manifests and
  lockfiles; visualization source remains disjoint. No release is authorized.
- **Delivered evidence:** Kwavers PR #638 merged as `00455130f` from reviewed
  head `b2a156215`; the independent judge found and then cleared one stale
  disabled-test block. Nextest passes 783 GPU-feature analysis tests, 744
  default analysis tests, and the four focused quality regressions after the
  judge fix. Formatting, doctests, warning-denied Rustdoc, standalone locked
  metadata, ADR-index validation, and the current-default real Hephaestus
  hardware test pass. `cargo-semver-checks` against the buildable
  dependency-only prerequisite baseline reports exactly the two removed fields
  as a required major change. The post-merge matrix is terminal with 33 passes,
  two expected skips, zero failures, and one cancellation: GPU and CUDA builds,
  all feature combinations, stable/beta/nightly, Miri, security, docs, coverage,
  quality, and validation pass; `Benchmark Runtime Smoke` spent 29 minutes in
  its Criterion command and hit the job's 30-minute timeout. Atlas gitlink
  `repos/kwavers` remains at `8ef48975c`. **Blocker/re-open trigger:** correct
  the cold-build benchmark-smoke instrument without raising its bound, then
  obtain a terminal green run and advance the gitlink to that fix.

## ATLAS-KWAVERS-BENCH-SMOKE-2026-08-25 — Bound cold-build benchmark smoke [patch] — hosted verification pending

- **Owner:** current session; lane `worktrees/kwavers-ci-opt`, branch
  `ci/kwavers-build-matrix-timings`, PR #641 at `84ba553ef`. **Scope:**
  Kwavers benchmark-smoke command and its
  directly required CI/cache structure. **Non-goals:** no timeout increase,
  benchmark deletion, reduced target coverage, or production-kernel change
  without profile evidence.
- **Outcome:** every plotting-eligible Criterion target executes once under the
  existing finite bound on a cold hosted runner; compilation and execution are
  separated or consolidated so setup cost cannot consume the smoke budget.
- **Acceptance oracle:** reproduce run `32867271654`, retain the full target
  set, build the bench binaries once as a separately bounded artifact, verify
  the cold build and bounded smoke phases independently, and obtain a terminal
  green hosted plotting feature-matrix leg containing both benchmark steps.
- **Risk/dependencies:** `[patch]`; the completed log proves no Criterion target
  executed: the release-profile compile was still building `proptest` at 29
  minutes and the 30-minute job bound then killed Cargo and Rustc. The
  visualization implementation is unchanged. Completion re-opens
  `ATLAS-KWAVERS-VIS-CONFIG-2026-08-25` for its gitlink advance.
- **Fix:** delete the standalone benchmark job and run one bounded dev-profile
  build plus one bounded `--test` execution in the already-cached plotting
  feature-matrix leg. The leg reuses checkout, toolchain, dependency cache, and
  the exact `--no-default-features --features plotting` graph; static manifest
  enumeration retains all 19 plotting-eligible targets. Cargo's
  `--no-fail-fast` keeps later targets executing after an individual failure.
  Independent review found no remaining issue after duplicate-step,
  feature-fingerprint, and complete-failure-reporting checks.

## ATLAS-KWAVERS-PYTHON-SURFACE-2026-08-21 — Complete typed and concurrent PyO3 surface [minor] — in progress

- **Owner:** Atlas integration. **Claimed files:** `backlog.md` and
  `checklist.md`; provider source is claimed by the isolated Banach coding
  worktree for the first core-simulation vertical slice. The shared dirty
  checkout and active PR scopes remain untouched.
- **Current claim:** `crates/kwavers-python/pyproject.toml`,
  `python/pykwavers/__init__.py`, typed package artifacts, the core
  `Simulation.run` binding module and focused binding tests. The claim excludes
  open PR #439 simulated-GPU files, open PR #443 core-log files, the separate
  analysis-owned WGPU migration, and all unrelated binding families.
- **Outcome:** the Kwavers Python wheel exposes every registered Rust class and
  function through one generated, typed package surface; the wheel ships
  `py.typed` and `.pyi` files; long-running binding calls release the GIL; and
  the package facade exports exactly the registered public symbols.
- **Audit evidence:** the current registration surface contains 25 classes and
  384 top-level functions, while the facade reexports 400 extension symbols
  but omits nine registered functions and four imported symbols from
  `__all__`. No `py.typed` or `.pyi` files exist. Static inspection identifies
  synchronous solver, thermal, GPU-session, bubble, cavitation-monitor, and
  chirp/sweep paths that still hold the GIL. Evidence source: the independent
  Kwavers binding audit at `crates/kwavers-python/src/lib.rs`,
  `python/pykwavers/__init__.py`, and the affected binding modules.
- **Acceptance:** a deterministic Rust registration-driven generator emits
  real signatures, defaults, classes, properties, NumPy arrays, optionals,
  tuples, mappings, and metadata without `Any`/ellipsis placeholders; CI
  regenerates and diffs the stubs; the installed wheel contains the extension,
  package facade, stubs, and marker; a strict typed consumer passes; an
  independent Python-thread regression proves each migrated long-running call
  releases the GIL while returned values remain correct; and the runtime
  inventory has no missing or extra public exports. Run the affected locked
  Rust gates, Python tests, doctests, Rustdoc, and wheel smoke at one exact
  provider head.
- **Sequencing:** first land the generator and exact registration inventory,
  then migrate one complete `Simulation::run` slice with the concurrency
  oracle, followed by thermal, GPU-session, bubble, monitor, and chirp families
  as separate vertical increments. Do not hand-author a partial stub or claim
  GIL coverage from static `.detach` counts alone.
- **Non-goals:** no domain logic in Python, no runtime introspection as the
  source of truth, no facade compatibility aliases, and no unrelated solver
  redesign.
- **First vertical slice:** isolated commit
  `db49f2f09cba6b24381156a8404cd08942a44f52` adds the typed package marker and
  stubs, releases the GIL around the core `Simulation.run` computation, and
  adds value-sensitive Python binding/thread-pool tests. The test oracle does
  not claim overlap or GIL proof; `py.detach` at the binding boundary is the
  static GIL-release evidence. Focused Rust,
  Nextest (21/21), Python (4/4), abi3 wheel, install, and smoke checks pass.
  PR [#590](https://github.com/ryancinsight/kwavers/pull/590) was opened at
  that head; strict mypy/Ruff/Black are unavailable and locked Cargo gates are
  blocked by the inherited Atlas overlay re-resolving the lockfile.
- The test-oracle correction is commit
  `124ef839e27aba71a8f3749c33acaf7d0ae1ee93`, now the PR head. Its focused
  Rust and wheel-backed tests pass; the previously collected hosted run set
  at `db49f2f09cba...` is stale and must not be attributed to the corrected
  head.
- **Hosted hold at the superseded head:** PR #590 was mergeable but `unstable`; CI/CD
  `32492642895`, legacy audit `32492642913`, Python wheel smoke
  `32492642908`, architecture validation `32492642942`, and Deploy mdBook
  `32492643372` remain queued. `recurseml/analysis` is errored and CodeRabbit
  is rate-limited. The live Pages site is reachable but older than the PR and
  is not evidence for either head; fresh checks for `124ef839e27a...` are
  required. No pointer advance or bypass is used.
- **Type-mapping increment (commit `60e871bad`, new PR #590 head):** every
  duck-typed `Bound<'_, PyAny>` parameter resolves through an audited
  `DUCK_TYPES` table keyed by `(class, function, parameter)` with per-entry
  extraction-code provenance; unaudited PyAny parameters fail the generator
  closed instead of emitting bare `object`. The stub honors
  `#[pyfunction(name = ...)]` renames (recovering the previously missing
  `run_standing_wave_suppression`), escapes Python keyword parameters
  PyO3-style (`lambda` -> `lambda_`), and types string-keyed result dicts as
  `Dict[str, object]` (422/422 literal-key `set_item` sites verified).
  Zero bare `object` parameters remain; an AST guard test enforces the
  invariant and the strict typed-consumer fixture exercises each mapped
  union. Focused suite 23 passed / 1 skipped with a freshly built abi3 wheel
  (`kwavers_python-0.1.0-cp38-abi3-win_amd64.whl`) installed. Pre-existing
  finding recorded, not caused by this increment:
  `get_array_weighted_mask` returns all zeros for annular elements at lane
  head `124ef839e27a` (`test_kwave_array_per_element_superposition_reduces_to_shared_signal`
  fails against the freshly built extension); the Rust binding needs its own
  defect increment. All prior hosted evidence is stale at the new head.
- **Annular-mask finding resolved (commit `38b54ce82`, PR #590 head):** not a
  Rust defect. Bowl/annulus surfaces lie one radius from `position` (the
  focus), matching k-wave-python; the test had placed the focus mid-grid with
  R = 10 mm on a 14.4 mm grid so the cap fell outside the domain and the BLI
  horizon correctly rejected every sample. Test now places the focus one
  radius past mid-grid and asserts both annuli contribute disjoint radial
  bands. Also fixed in-test: "Rectangular" → canonical "Uniform" alias
  round-trip expectation in `test_transducer_array.py`. Full local suite
  triage (898 passed / 90 failed / 62 skipped): remaining failures are
  environmental (missing external k-wave example utils, long-physics
  timeouts), no regressions from this lane.
- **Continuation refinements (uncommitted at `60e871bad`, part of this
  increment):** the generated stubs now pass mypy `--strict` — array aliases
  are `TypeAlias`-annotated, `__init__` returns `None` (PEP 484), and
  `__eq__` takes `other: object` (Liskov); the facade stub splits the eight
  `kwave_parity` helpers from the extension import and declares
  `__author__`/`__version__`. CI wiring: a `python-surface` job in `ci.yml`
  runs `tools/generate_surface.py --check` (regen-and-diff gate) plus the
  generator/typed-consumer tests with mypy installed; the wheel-smoke
  `kwave-comparison` job runs the runtime export-inventory oracle against the
  installed wheel (`KWAVERS_PYTHON_PACKAGE=installed`). The tracked abi3
  `.whl` build artifact is removed from git. Local gates: `--check` passes,
  generator staleness / typed-consumer / runtime-inventory tests pass (21
  passed, 3 skipped in source mode; runtime oracle 16/16 against the installed
  wheel).
- **Thermal GIL family (lane rebased onto `origin/main` `377a98c86`):**
  `ThermalSimulation::run` now runs its entire diffusion time loop inside
  `py.detach`, mirroring the `Simulation::run` contract (GIL-phase setup /
  owned-Rust-data time loop / GIL-phase PyArray assembly). Added the runtime
  overlap oracle `test_thermal_simulation_run_releases_gil_with_returned_value_correctness`
  on `test_bindings_surface.py`: a 48³ grid with a constant heat source holds
  a solve window well past the 0.5 s floor while the main thread exceeds 1M
  pure-Python GIL increments; returned-value correctness shows bit-identical
  temperature fields for identical inputs and a doubled heat source raises the
  temperature rise by exactly 2× (linear diffusion, ratio 1.0 within 1e-6).
  Wheel-backed: 16 passed / 1 skipped in `test_bindings_surface.py`; fmt,
  clippy `-D warnings`, nextest 21/21 clean. The `Simulation::run` slice
  (PR #590) and the WGPU provider migration (PR #602) are both completed;
  thermal is the first of the remaining GIL families (thermal, GPU-session,
  bubble, monitor, chirp).
- **Bubble ODE GIL family (same lane, next vertical increment):**
  `solve_rayleigh_plesset`, `solve_keller_miksis` (and the Keller–Herring
  delegation), `solve_gilmore`, and `solve_hodgkin_huxley_like` now run their
  RK4 / ODE integration compute inside `py.detach`, mirroring the
  `Simulation::run` / thermal contract. Added the runtime overlap oracle
  `test_bubble_ode_releases_gil_with_returned_value_correctness`: a 10M-step
  `solve_keller_miksis` holds a ~1s solve window while the main thread exceeds
  1M pure-Python GIL increments; returned-value correctness shows bit-identical
  outputs for identical inputs and a doubled driving amplitude swings the wall
  strictly farther (higher max / lower min radius). Wheel-backed: 17 passed /
  1 skipped in `test_bindings_surface.py`; fmt, clippy `-D warnings`, nextest
  21/21, generator `--check` clean.
- **Published at the rebased lane head (2026-08-22):** the lane (rebased onto
  `origin/main` `377a98c86`, carrying the thermal and bubble-ODE GIL
  increments) force-published to PR #590 with a lease guard against the
  superseded head `6616c904`; PR head is now `a2a3878b` and `MERGEABLE`.
  Hosted runs are executing rather than queued: Python wheel smoke
  `32588842603` and Legacy Migration Audit `32588842587` in progress, CI/CD
  `32588842609` and Deploy mdBook `32588842869` queued. All prior hosted
  evidence remains stale; merge only at exact head after terminal required
  checks.
- **Collection and blocker fix (2026-08-23):** wheel smoke, Legacy Migration
  Audit, and Deploy mdBook are terminal success; CI/CD Pipeline failed on its
  `Python Typed Surface` job: the crate's declared pytest addopts pass
  `--timeout/--benchmark-disable`, whose plugins (pytest-timeout,
  pytest-benchmark) the job did not install. Head `d1281f990` installs both
  declared dependencies; replacement runs pending.
- **Closed (2026-08-23):** replacement run set at `d1281f990` terminal:
  CI/CD Pipeline (incl. Python Typed Surface), Python wheel smoke, Deploy
  mdBook, and Legacy Migration Audit all success. The only failing check is
  Architecture Validation — the pre-existing repo-wide defect filed below,
  failing identically on every PR head, not required by any branch
  protection. PR [#590](https://github.com/ryancinsight/kwavers/pull/590)
  merged with the expected-head guard at default `ca5c9c93`; post-merge
  default runs in progress before any Atlas gitlink advance.
  **Not this PR's regression:** the Architecture Validation job fails on every
  open PR head across the repository (12 consecutive failures on unrelated
  branches, main's own post-merge runs cancelled with no terminal baseline).
  Local reproduction attributes it to ~2,850 warnings across 103
  example/test/bench files under `-D warnings --all-targets` — a ratchet-scale
  burn-down filed below as its own item.

## ATLAS-TYCHE-RELEASE-VERIFICATION-2026-08-21 — Record release gates [patch] — in progress

Tyche PR #35 documents the completed release/package verification slice. The
provider branch passed formatting, warning-denied Clippy, Nextest (51/51),
doctests (18/18), Rustdoc, the reproducible study example, benchmark smoke,
and `cargo publish --dry-run` before merging at default commit
`7d6364716f0a1929f5d2156a6f2d3c6962dd3b92`. The hosted PR verify and
supply-chain checks passed; `recurseml/analysis` remains report-only.

Post-merge CI `32474994136` and Pages `32474992974` are queued. Registry
publication and GitHub Release creation remain explicitly outside this item;
the Tyche Atlas pointer is unchanged until default CI/Pages and live-page
evidence are terminal.

**Ninth pointer batch (2026-08-23, atlas commit to be named):** the hold
cleared — `7d6364716f` has terminal `CI` and `pages-build-deployment` runs at
the exact head, and the live site returns HTTP 200 with title `Tyche | tyche`.
The Atlas gitlink advances to `7d6364716f`; `recurseml/analysis` remains
report-only.

## ATLAS-ASCLEPIUS-GEUD-GRADIENT-2026-08-20 — Add an independent Coeus gradient oracle [patch] — in progress

The Asclepius Coeus adapter test currently compares its reverse-mode gradient
with a second hand-coded power-mean derivative. That is a useful algebraic
check but not an independent behavioral oracle: the same formula can be wrong
in both places. The provider backlog already identifies a central-difference
check for this seam as `ASC-VER-018`.

**Scope:** Asclepius `crates/asclepius-coeus/tests/equivalent_uniform_dose.rs`
on a clean lane based on fetched `origin/main`, plus root PM entries. Add a
finite-difference value oracle for the existing dose fixture and derive its
step/tolerance from floating-point scale and central-difference truncation.
Do not alter the adapter implementation, peer-owned book/PM files, or the
Atlas Iris lane.

**Acceptance:** the test evaluates the adapter at independently perturbed dose
vectors, compares central differences with the reverse-mode gradient under a
documented bound, covers every dose coordinate, and fails under a mutation of
the adapter's gradient path; focused/full provider gates pass and the exact
branch is published for review.

**Owner:** current Atlas session. **Claimed files:** Asclepius
`crates/asclepius-coeus/tests/equivalent_uniform_dose.rs` in
`worktrees/asclepius-geud-gradient`; root `backlog.md` and `checklist.md`.

**Implementation evidence (2026-08-20):** clean lane branch
`fix/asclepius-geud-gradient` is based on `origin/main`
`2f6959b52c36c91169e4f30ad4a7ce8e45d6e901` and publishes one commit,
`390a3ff`. The test evaluates independently perturbed adapter values for every
dose coordinate, uses central differences at two scales with Richardson
extrapolation, and derives truncation plus roundoff bounds from the step and
`f64::EPSILON`. Locked all-target check, full nextest (`20/20`), focused
nextest (`6/6`), Clippy with `-D warnings`, doctests, and Rustdoc pass. A
value-preserving mutation that detaches the adapter input gradient fails four
gradient/value-contract tests, including both independent gradient tests.

The implementation is published as PR
[#24](https://github.com/ryancinsight/asclepius/pull/24) at exact head
`390a3ff60344034a841b0735d9c059231e7f0a8a`, based on merged default
`ce3fea355f0989dcc92a321a1f923f6f30749da4`. PR CI passed at run
`32436064353`; PR #24 is merged. Post-merge default CI passed at
`a38b8b50d1de1d23c08478e4b60d9e7bbd8eacf4` in run `32441333616`; Pages build
`32441332866` remains queued. The dirty primary Asclepius checkout and Atlas
gitlink remain unchanged until Pages and live-page verification are terminal.
The merged lane and remote branch were removed after ancestry verification.

**Ninth pointer batch (2026-08-23, atlas commit to be named):** the Pages
hold cleared — `a38b8b50d1` has terminal `ci` and `pages-build-deployment`
runs at the exact head, and the live site returns HTTP 200 with title
`Asclepius | asclepius`. The Atlas gitlink advances to `a38b8b50d1`;
`recurseml/analysis` remains report-only.

## ATLAS-THEMIS-REGION-MODULE-2026-08-20 — Split branded region implementation [arch][patch] — in progress

Themis `src/branded/region/mod.rs` is a 481-line implementation file. It
contains the `SyncRegionPlacement` capability, its NUMA-tag proof helper, scope
construction, and tests, so the module manifest is not a manifest and the
conformance scan records one `manifest_implementation` violation.

**Scope:** Themis `src/branded/region/` only, plus the provider ADR/index and
owner-local PM records. Move the existing implementation into a focused leaf
module, retain `region/mod.rs` as the module manifest, and preserve every
public path and safety argument. Do not touch the peer-owned primary checkout
or unrelated platform/book changes.

**Acceptance:** public exports and behavior remain unchanged; the region
module manifest contains only module declarations and curated re-exports; the
provider ADR index is synchronized; format, locked all-target check, warning-
denied Clippy, nextest, doctests, and Rustdoc pass; the conformance scan drops
Themis `manifest_implementation` by one without raising any class.

**Owner:** current Atlas session. **Claimed files:** Themis
`src/branded/region/`, provider ADR/index, and root `backlog.md`/`checklist.md`.
The clean lane must be based on fetched Themis `origin/main` after the primary
checkout's five-commit lag is reconciled by using a new lane, not by editing
the dirty primary.

**Implementation evidence (2026-08-20):** clean lane branch
`fix/themis-region-module` is based on `origin/main`
`c76a55e5eb9988b48bba69e67d6e07ce5fe55ea8` and publishes commits `7b30088`
and `32c40a7`. `region/mod.rs` is now a manifest with curated re-exports and
the implementation/tests are in `region/scope.rs`; ADR 0003 and the provider
backlog/gap audit are synchronized. Locked all-target check, format,
warning-denied Clippy, nextest (`25/25`), doctests (`5/5`), and Rustdoc pass.
The lane conformance scan reports `manifest_implementation: 1` versus `2` on
the fetched provider default, with every other Themis class unchanged.

The implementation was published as PR
[#29](https://github.com/ryancinsight/themis/pull/29) at exact head
`32c40a7b21fd9a6e81505e8741d54884ab1d2e59`, based on merged default
`c441acffc71ebeb24b77dd2d23a90856352d2f48`, and merged with the expected-head
guard at default merge commit `2c0749873c4860257ba912ff8494937021a79aa1`.
The PR's Ubuntu, Windows, MSRV, Miri, compile-fail, Clippy, Nextest, doctest,
and Rustdoc checks are terminal-successful. Post-merge default runs are
queued: MSRV `32473974344`, CI `32473974353`, and Pages
`32473973059`. The dirty primary Themis checkout and Atlas gitlink remain
unchanged until those runs and the live-page check are terminal. The merged
clean lane and its local branch were removed after the PR merge.

## ATLAS-HELIOS-RADON-ORACLE-2026-08-20 — Remove existence-only sinogram assertion [patch] — in progress

`helios-imaging/src/radon.rs` asserts only `Sinogram::from_readings(...).is_ok()`
and then unwraps the same result. This is an existence-only assertion and does
not verify the constructed value; the later mapped-reading assertions are the
actual geometry/value oracle.

**Scope:** Helios `crates/helios-imaging/src/radon.rs` and provider PM records
on a clean lane based on fetched `origin/main`. Replace the vacuous assertion
with an invariant-preserving typed extraction, retain the existing negative
length case and value-semantic map/geometry assertions, and do not touch the
peer-owned Helios primary checkout or unrelated Python/workflow/book files.

**Acceptance:** the test contains no existence-only assertion for this path;
the valid construction is consumed with a precise invariant message, the
invalid length remains asserted as a typed failure, provider format/locked
all-target check/Clippy/nextest/doctest/Rustdoc pass, and the conformance scan
reduces `existence_only_assertions` by one without another class increasing.

**Owner:** current Atlas session. **Claimed files:** Helios
`crates/helios-imaging/src/radon.rs`, provider PM, and root PM. The branch is
published separately from the provider's dirty primary checkout.

**Implementation evidence (2026-08-20):** clean lane branch
`fix/helios-radon-assertion` is based on `origin/main`
`7ff72e37889594b6592e1f8b8b169834765f7851` and publishes `fdfe61a`. The
success path now consumes the validated `Sinogram`; the error path matches
`HeliosError::InvalidDomainValue` and checks its field, rejected value, and
reason. The lane conformance scan reports `existence_only_assertions: 0`
versus `1` on the fetched provider default. Locked workspace all-target check,
format, warning-denied Clippy, nextest (`262/262`, 9 skipped), doctests, and
Rustdoc pass.

The implementation was published as PR
[#69](https://github.com/ryancinsight/helios/pull/69), initially at
`fdfe61aa61a92493e643b76033a7ba72e8fda68c` and now at stacked head
`7a97333158bcaa134054eef9b254798d64c394de`, based on merged default
`7ff72e37889594b6592e1f8b8b169834765f7851`. The current stack also carries
the typed Python metadata and one executable Compton book oracle; its Rust,
Python, benchmark, and mdBook checks are queued. The dirty detached primary
Helios checkout and Atlas gitlink remain unchanged until the current PR head's
checks are terminal.

## ATLAS-ADR0033-STAGES — Krylov ownership unwind, measured status [arch] — in progress

Re-measured 2026-08-20 against the trees rather than the board. ADR 0033's
four-stage plan is further along in places and wider in others than recorded.

**Stage A — close Athena's capability gap: DONE.**
`athena-core` ships `Cg<B>`, `BiCgStab<B>`, `Gmres<B, const RESTART>`, and
`Lsqr<B>` (`crates/athena-core/src/solver/*/algorithm.rs`), and `athena-leto`
ships Jacobi, ILU, and SOR/SSOR preconditioners over `LetoBackend`. Residual gap,
not part of stage A but blocking backend-generic solving: **no preconditioner
exists for the Hephaestus backend**, so accelerator PCG is unpreconditioned CG
(`crates/athena-hephaestus/src/lib.rs` versus the three `athena-leto` impls).

**Stage B — migrate CFDrs: substantially done, remainder in flight.**
Production CFDrs already solves through Athena. `cfd-math/src/linear_solver/
krylov.rs` (613 LOC) builds a `LetoBackend` and `BorrowedCsrOperator` and
dispatches Athena's solvers; it is a legitimate adapter, not a shim, because
Athena's `Gmres<B, const RESTART>` is const-generic while CFDrs selects restart
at runtime. There are no `GMRES::new`/`BiCGSTAB::new`/`ConjugateGradient::new`
call sites in `crates/*/src` at all — the single occurrence is inside a doc
comment.

What remains is the re-export shim `pub mod iterative { pub use leto_ops::{...} }`
in `cfd-math/src/lib.rs`, whose own doc calls leto-ops "the SSOT iterative-solver
types" in direct contradiction of this ADR. It keeps the Leto family alive and so
blocks stage D. The concrete duplication it sustains: `DiagJacobi<T>` in
`cfd-1d/src/solver/core/linear_system.rs` implements **both** preconditioner
traits — leto's at line 301 and `athena_core::Preconditioner` at line 311 —
exactly the duplication stage D names. Remaining consumers are five test/bench
files plus `IterativeSolverConfig` (56 references).

**Stage B increment (2026-08-22):** PR
[#363](https://github.com/ryancinsight/CFDrs/pull/363) at head `27338e95`,
rebased onto the merged format-gate default `a70faea6`. The branch deletes the
`pub mod iterative` re-export shim and migrates its callers; the `DiagJacobi`
dual-trait duplication is already resolved on the branch — only the
`athena_core::Preconditioner<LetoBackend>` impl remains. Local evidence:
`cargo fmt --all --check` clean; nextest `-p cfd-math -p cfd-validation`
675/675; warning-denied Clippy clean for cfd-math, cfd-validation, and
cfd-1d (the two `needless_update` warnings in `cfd-3d` are pre-existing
default debt the branch does not touch).

**Rebase and blocker fix (2026-08-23):** hosted run `32590225522` failed on
exactly those two `needless_update` sites — with every other debt class
cleared stack-wide they became the only remaining `-D warnings` errors, i.e.
delivery-blocking. Commit `05c025e8` deletes the two no-effect
`..Default::default()` bases (all three struct fields are specified at both
sites). Local: workspace clippy `-D warnings` reports zero errors, cfd-3d
nextest 400/400, fmt clean.

**Stage B closed (2026-08-23):** replacement gate terminal success at
`05c025e8`; PR #363 merged with the expected-head guard at default `c5f9fa2c`;
post-merge CI `32611718091` collected before further solver work on this
default.

**Stage C scoping confirmed (2026-08-23):** the Leto Krylov family now has
**zero stack-wide consumers** (`linalg::iterative` imports: helios, ritk,
coeus, harmonia, CFDrs, kwavers, moirai, tyche all scan zero), so Stage D's
consumer precondition is met and only ADR 0033's sequencing (C before D)
holds deletion. Stage C scope verified present at kwavers origin/main:
`kwavers-solver/src/forward/bem/gmres.rs` (334 LOC, f64-hardcoded dense
GMRES), `kwavers-solver/src/integration/nonlinear/gmres/` (419 LOC), and the
matrix-free operator whose `jacobian_vector_product`
(`multiphysics/monolithic/residual/jvp.rs:17`) needs the `&mut self` →
`&self` refactor (scratch-buffer cache is its only mutation). Kwavers uses
`leto_ops` only for matvec/dot primitives elsewhere — legitimate array ops,
not Krylov recurrences.

**Stage C claim blocked on lane availability:** all seven registered Kwavers
worktree lanes hold live published PR branches (#598, #590, #602, and peers);
the two-tree bound forbids minting a ninth tree, and the primary checkout is
detached and dirty. This is a genuine contention deferral: re-open when any
lane completes its hosted collection and merges (its tree then re-points),
or when a peer releases a lane. DoR is otherwise complete: outcome (one
Athena-backed Krylov implementation; delete the three Kwavers duplicates),
acceptance oracle (ADR 0033 Stage C/D acceptance — residue scan finds no
Krylov recurrence outside Athena; every consumer suite passes against
Athena), change class `[minor]` breaking internal seam per the ADR.

**Stage C — migrate Kwavers: not started, and wider than the ADR recorded.**
Kwavers declares no `athena` dependency in any manifest. It carries **three**
iterative implementations, where ADR 0033 anticipated one:

- `kwavers-solver/src/forward/bem/gmres.rs` — 334 LOC dense GMRES, `f64`-hardcoded
  (29 `f64` occurrences), Modified Gram-Schmidt Arnoldi with Givens rotations.
- `kwavers-solver/src/integration/nonlinear/gmres/` — 419 LOC (solver 249,
  tests 110).
- The matrix-free operator feeding the monolithic multiphysics residual.

The ADR's stated prerequisite holds exactly as written: `jacobian_vector_product`
at `kwavers-solver/src/multiphysics/monolithic/residual/jvp.rs:17` takes
`&mut self`, and its only mutation is the `jvp_state_scratch` buffer cache, so it
can satisfy `LinearOperator::apply(&self, ...)` once that scratch moves to
caller-owned workspace or interior mutability.

**Stage D — delete `leto-ops/src/application/linalg/iterative/`: blocked on B and
C.** Consumer check across the stack found no other repository importing the Leto
iterative family — helios, ritk, coeus, and harmonia are all clean. CFDrs and
Kwavers are the only two holding it alive.

Sequencing is unchanged from the ADR: B, then C, then D, each converting its
consumers in the same change, with no compatibility layer at any stage.

## ATLAS-BOOK-STAGING-2026-08-20 — Preserve Cargo artifact identity in mdBook gates [patch] — in progress

The shared `book-pages.yml` workflow currently strips Cargo metadata hashes and
keeps the first artifact for each crate name. RITK's exact default book run
`32404089897` disproves that selection rule: its locked graph contains
`rand_core` 0.6.4, 0.9.5, and 0.10.1, and the staged `rand_core` metadata does
not match `ritk_statistics`, producing `E0460` before the book example runs.

**Scope:** root `.github/workflows/book-pages.yml`, ADR 0035, and this item's
owner-local checklist entry. No provider source, lockfile, or book content.

**Acceptance:** the reusable workflow stages the exact hash-suffixed Cargo
artifacts without collapsing duplicate crate versions; a local RITK mdBook
probe with duplicate `rand_core` artifacts passes; YAML/whitespace checks pass;
the changed workflow is adopted by a rerun of the RITK default book gate.

**Owner:** current Atlas session. **Claimed files:**
`.github/workflows/book-pages.yml`, `docs/adr/0035-shared-publication-pipelines.md`,
`backlog.md`, `checklist.md`. RITK PR
[#204](https://github.com/ryancinsight/ritk/pull/204) merged from exact head
`9bc47d42f0d6050f4a68661c01d45806d41e583f` at default
`b35c93313c06ea55fffa680a430378dda1df8e41`. Its CI and book checks pass;
the current default CI and Pages deployment pass, and live Pages returns HTTP
200 with the expected RITK title. The Atlas pointer advances to `b35c9331`.
`recurseml/analysis` is report-only.

Themis's corresponding post-merge evidence is terminal for the build jobs:
default head `c76a55e5eb9988b48bba69e67d6e07ce5fe55ea8` has successful CI
`32402753573`, MSRV `32402753617`, and `deploy / Build book` job
`96534588862` in run `32402754181`. The Pages deployment remains queued in
run `32402752669` (job `96545229314`); this is deployment-pending evidence,
not a live Pages claim.

The exact-head collection also confirms Helios default
`7ff72e37889594b6592e1f8b8b169834765f7851` with successful CI
`32393592276` and mdBook deployment `32393593050`, and Tyche default
`10410f2de1ce1529ecbff50fa740b23a1c8f77b9` with successful CI
`32394888136` and Pages deployment `32394886461`. Kwavers currently resolves
to `78af725e749c8ec4fd756d55091d557ea635aac2`; its latest hosted workflow
set targets the predecessor `b5b4fb0614ad3238ab95ff092cebd5977a201b22`, so
those runs cannot authorize the stale Atlas pointer `459f18ce`.

## ATLAS-BOOK-CALLER-PINS-2026-08-20 — Repin provider mdBook callers [patch] — in progress

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

## ATLAS-CONSUS-SZIP-BOUND-2026-08-20 — Bound SZIP allocation [security][patch] — in progress

The SZIP decoder previously trusted a four-byte sample count from a seven-byte
header before checking the payload or reserving output storage. Malformed input
could therefore request an unbounded allocation and abort instead of returning
a typed error.

**Evidence:** Consus PR [#51](https://github.com/ryancinsight/consus/pull/51)
adds independent header-size and payload-capacity bounds plus
`try_reserve_exact`; its hosted package, MSRV, and fuzz checks pass. The exact
head `2e24e6adda663db67b4bf1d4e1614e2c3b06fc19` merged at default
`1000699fa740c74b8aea1b9cc5311f85d3d2a3cc`. Post-merge CI and Documentation
runs `32436374114` and `32436374130` are queued. RecurseML remains report-only.
The dirty Consus checkout and Atlas gitlink are unchanged until terminal
post-merge evidence is collected.


## ATLAS-EUNOMIA-NAN-CONTRACT-2026-08-21 — Unify scalar NaN and signed-zero laws [major] [arch] — in-progress

Audit found a live scalar contract split in Eunomia `origin/main`: the default
`NumericElement::min_scalar`/`max_scalar` uses order-dependent `PartialOrd`,
primitive `f32`/`f64` implementations delegate to native `min`/`max`, and
reduced-precision wrappers inherit the comparison path. One-NaN behavior is
therefore operand-order dependent across shipped scalar types; signed-zero
behavior is unpinned. This is a value-semantic defect that propagates through
generic `Field::clamp`.

Scope: the Eunomia numeric trait, primitive and wrapper implementations,
float-order/element conformance tests, and the affected numeric book chapters.
Define one NaN/±0 contract, implement it for every shipped real scalar type,
and verify commutativity, wrapper/primitive parity, and `clamp` value semantics.
Non-goals: consumer rewrites, complex-number ordering, or registry release.

Acceptance: NaN and signed-zero cases are specified in the owning Rustdoc/book;
all shipped real scalar implementations satisfy the same value table; generic
tests fail against the old order-dependent behavior; focused and workspace
gates pass on the clean Eunomia origin base. The clean lane is
`worktrees/eunomia-numpy-ci`; refresh it from Eunomia `origin/main` before
editing and preserve the dirty provider checkout.

Owner: codex-primary. Claimed files: Eunomia numeric trait/primitive/wrapper
implementations, float conformance tests, affected book chapters, and their
provider PM/ADR artifacts. Dependencies: current Eunomia `origin/main`; no
consumer dependency. Risk/change class: `[major] [arch]`. Last update:
2026-08-21.

Implementation is complete on Eunomia branch `fix/eunomia-nan-contract` at
`c877ea9` (code fix `ba51a16`, evidence/docs follow-ups `f6eceb1`, `8c4510e`,
`0cf3c7d`, and `c877ea9`). The provider PR is [Eunomia
#72](https://github.com/ryancinsight/eunomia/pull/72), and the independent
judge accepted the exact range with no blocking finding. Final-code-head local
evidence covers format, strict all-target/all-feature Clippy, Nextest 138/138,
doctests 9/9, Rustdoc, locked package listing, and static mdBook build.
Workflow-equivalent fresh-staged mdBook tests passed at the unchanged book
implementation head `ba51a16`; the final local sample rerun is bounded by
shared-target cache contamination and remains a hosted-build watchpoint. PR
#72 merged with the expected-head guard at default commit
`834bd3b443dd050e9a1ec0c5d837645db33ac787`. Post-merge CI
`32475224630`, MSRV `32475224791`, and Deploy mdBook `32475225502` are queued;
the Atlas `repos/eunomia` gitlink stays unchanged until terminal default
evidence is collected.

## ATLAS-EUNOMIA-NUMPY-CI-2026-08-20 — Verify the optional NumPy boundary [patch] — in progress

The Eunomia `numpy` feature is a real provider-consumer seam: it implements
NumPy element conversions for `Complex32` and `Complex64`, and Hephaestus and
Kwavers enable it from their Python binding crates. Eunomia's current CI
explicitly excludes that feature because no Python runtime is provisioned.
This is a verification gap, not a request for a standalone Eunomia wheel;
the Atlas inventory now records the binding ownership in the consumer crates.

**Scope:** Eunomia's provider CI workflow and its owner-local PM entry. Add a
Python/NumPy-backed locked feature check and runtime dtype contract test for
both complex element types. **Non-goals:** new Eunomia packaging, changes to
the complex implementation, or changes to Hephaestus/Kwavers bindings.

**Acceptance:** the provider CI provisions a pinned supported Python, installs
the repository's declared NumPy test dependency through the existing project
convention, runs the `numpy` feature's locked check/Clippy/nextest contract,
and the hosted exact-head job passes. The feature remains optional and the
consumer binding crates remain the only Python packages.

**Delivery evidence:** PR #70 passed Rust verification, Rust 1.95.0
all-target, NumPy feature contract, and supply-chain checks at exact head
`cdc7e68`, then merged as `c7435a2`. The post-merge Eunomia CI run
`32435024973` and Deploy mdBook run `32435025288` are queued; the Atlas
pointer remains unchanged pending terminal default verification.

**Owner:** current Atlas session. **Claimed files:** Eunomia
`.github/workflows/ci.yml`, the existing Eunomia PM entry, and this root item.
The clean provider lane must be based on Eunomia `origin/main`
`85e590b789505c66f5174043c2e7e851c20547a5`; the dirty primary checkout is
peer-owned and remains untouched. The first hosted attempt at exact head
`da355aa082108ebd4ec854c034ea5c0b74cc9120` compiled and linted the NumPy
feature but failed before the contract tests because the NumPy job did not
install `cargo-nextest` (`32412277378`, job `96565207307`). Commit
`cdc7e68a504411b38d3402e24dc71a1b625197ef` installs the same pinned
`nextest@0.9.140` used by the general verification job and updates the
provider-local checklist. PR [#70](https://github.com/ryancinsight/eunomia/pull/70)
is now at exact head `cdc7e68a504411b38d3402e24dc71a1b625197ef`; replacement
Rust/NumPy/supply-chain runs `32423868719` and MSRV run `32423868861` are
queued. `recurseml/analysis` is report-only.


## ATLAS-APOLLO-PYTHON-SURFACE-2026-08-20 — Ship the typed Python surface [patch] — in progress

The Apollo Python package currently exposes its symbols through `__init__.py`
but has no `py.typed` marker or `.pyi` surface. The active Apollo book lane is
clean and its executable-book PR is already merged; this follow-up is confined
to the repointed lane and does not touch the dirty primary checkout.

**Scope:** `crates/apollo-python/python/pyapollofft/py.typed`, the matching
stub surface, `crates/apollo-python/pyproject.toml`, and installed-wheel typing
tests. **Non-goals:** changing FFT algorithms or adding a second Python API.

**Acceptance:** the stub surface covers every re-exported binding and plan,
the package metadata declares typing-inclusive classifiers and project links,
the built wheel contains `py.typed`, and the installed-wheel test resolves the
public names with a value-semantic FFT smoke. Rust binding compute paths already
use `Python::detach` in the clean lane; any newly found heavy path must retain
that GIL-release contract.

**Owner:** current Atlas session. **Claimed files:** the clean Apollo book lane
repointed from its merged branch, the root item, and this PM record.

**Implementation:** Apollo commit `4e055407` was pushed on
`fix/apollo-python-surface` as PR
[#109](https://github.com/ryancinsight/apollo/pull/109) and merged with the
expected-head guard at default commit
`fd9ecd0206c2b4ee3993a42eec65a1703d592ac2`. Local evidence includes the
formatting, locked check, clippy, nextest, release `cp38-abi3` wheel build,
and 35 installed-wheel pytest cases. Hosted PR Rust and Python checks are
terminal-successful; `recurseml/analysis` is the existing report-only error.
Post-merge CI `32474434108` and Pages `32474432640` are queued. The dirty
primary Apollo checkout and Atlas gitlink remain unchanged until those default
runs and the live-page check are terminal. The merged clean lane and its local
branch were removed after the PR merge.

## ATLAS-HARMONIA-FIELD-EXCHANGE-050-2026-08-21 — Add typed physical-field exchange [major] [arch] — in progress

The current Harmonia boundary exchanges scalar slices with only runtime
dimension and time checks. That permits CFDrs, Kwavers, and Helios adapters to
connect fields with incompatible physical quantities or grid frames.

**Scope:** a clean Harmonia lane based on `origin/main`; add a no-unsafe,
zero-copy field envelope whose values are `aequitas::Quantity<T, D>`, validated
grid shape/spacing/origin/orientation metadata, and transfer validation tests.
The first slice owns the contract only; consumer adapters and numerical source
terms follow as dependency-ordered items. **Non-goals:** changing solver
algorithms, inventing unit conversions, or editing peer-dirty provider trees.

**Acceptance:** the public constructor rejects zero dimensions, non-finite or
non-positive spacing, non-finite origins/directions, non-orthonormal direction
cosines, and value-count mismatches; a valid envelope borrows the caller's
quantity slice without allocation; compile-time quantity dimensions prevent an
`Intensity`/`VolumetricPowerDensity` interchange; property and boundary tests
cover the validation partitions and orientation identity/round-trip laws.

**ADR claim:** `docs/adr/0050-typed-physical-field-exchange.md` is reserved for
this decision. The ADR must record Harmonia as the orchestration owner,
Aequitas as quantity SSOT, and the later CFDrs/Kwavers/Helios adapter path.

**Owner:** current Atlas session. **Claimed files:** this root item and the
Harmonia clean lane only. The Apollo hosted-gate monitor remains separate.

**Current increment:** Harmonia commit `5b1bc28` (on top of
`944eafebb5045a24b8353964d1a0700a2cb62098`) implemented the contract and
merged through [PR #9](https://github.com/ryancinsight/harmonia/pull/9) with
the expected-head guard at default commit
`542b80b65628d8c4a16fdfd4113a2ff029116a96`. The follow-up adds negative and
non-finite spacing cases, a valid rotated-frame round-trip assertion, and
exact shape/origin/direction compatibility failures. The clean lane passed
`cargo clippy --all-targets --all-features --locked -- -D warnings`,
`cargo nextest run --locked` (31 passed, 0 skipped),
`cargo test --doc --locked`, `cargo doc --no-deps --locked`, and
`cargo check --release --locked`. The root ADR and generated index are in
`c39f12a`; the root commit is pushed. Post-merge CI `32474562236` and Pages
`32474560873` are queued. No consumer adapter or Atlas pointer advance is
authorized until those default runs and the live-page check are terminal.
The merged clean provider lane and its local branch were removed after the PR
merge; the dirty primary checkout remains untouched.
An independent exact-head review found no implementation or ADR blocker. It
also records a verification limit: the provider CI omits `--locked` and does
not run MSRV, release, or SemVer checks; those limits are not replaced by the
local locked gates or by the queued default runs.

## ATLAS-MOIRAI-ACCELERATOR-ROUTE-2026-08-21 — Execute accelerator routes [major] [arch] — in-progress

The current Moirai route contract preserves an accelerator label only as
metadata: `moirai-transport/src/route.rs` maps accelerator routes to the local
address, and `DevicePayloadRegion` retains a host `Vec<u8>` without device
allocation or dispatch. Moirai's own gap analysis records that no GPU/TPU/NPU
backend consumes `SchedulerRoute::Accelerator`.

Scope: a clean, dependency-ordered Hephaestus/Themis integration edge that
resolves an `AcceleratorId`, dispatches one existing kernel family, and proves
CPU/WGPU value equivalence plus unavailable-device failure. Preserve the DAG:
Hephaestus consumes Moirai route/planner contracts; Moirai does not depend on
Hephaestus. Non-goals: a new accelerator runtime in Moirai, Melinoe stream
ownership, or broad scheduler redesign.

Current slice: replace Moirai transport's metadata-only accelerator address
resolution with a typed resolution that preserves the scheduler route and
accelerator identity while retaining a transport address for the later
Hephaestus edge. The package lane is `worktrees/moirai-package`, claimed for
`moirai-transport` route source/tests, benchmark source contracts, the public
facade re-export, and synchronized provider ADR/checklist artifacts. Dispatch
and CPU/WGPU execution remain a later Hephaestus/Themis slice after their bases
are refreshed; this slice does not claim device execution.

Current-slice outcome: Moirai commit `2355d42a39ff85fd3efb075075c9a916f52fc8be`
(`feat(moirai): Retain accelerator identity`) merged through PR
https://github.com/ryancinsight/Moirai/pull/147 with the expected-head guard at
default commit `ff56d60218b6f418d8db0e42c30da8185b90b6bd`. `RouteResolution`
keeps the full `SchedulerRoute`, transport `Address`, and accelerator
placement together; `RoutedArchivedSender::send_route` returns that
resolution. Exact local verification: 807/807 nextest tests passed with 6
skipped, clippy passed, format check passed, doctests passed, and rustdoc
passed. `cargo-semver-checks` is unavailable in the environment. Post-merge
Rust Workspace `32475134603` and Python Bindings `32475134582` are queued; no
submodule-pointer advance is claimed until those default checks are terminal.
The merged clean package lane and its local branch were removed after the PR
merge; the dirty detached primary checkout remains untouched.

Acceptance: accelerator identity survives route resolution; a present device
executes a real kernel and returns its value-semantic result; a missing device
returns a typed error; CPU/WGPU differential tests, route-identity tests, and
a bounded transfer/dispatch smoke pass. Claim only after refreshing the
provider defaults and reconciling the existing dirty/detached checkouts.

Owner: codex-primary. Claimed scope: `worktrees/moirai-package`,
`moirai-transport/src/route.rs`, `moirai-transport/src/route/tests.rs`,
`benchmarks/tests/benchmark_contracts/`, `moirai/src/lib.rs`, and the provider
ADR/checklist artifacts needed for this route-contract replacement.
Dependencies: current Moirai origin route contract; Hephaestus/Themis clean
bases remain a dependency for the subsequent dispatch slice. Risk/change class:
`[major] [arch]`. Last update: 2026-08-21.

**Outcome:** close the remaining cross-cutting correctness and evidence
deficits in the order below, so that a green gate means what it claims.

**Non-goals:** raising per-repository completeness scores as such; peer-owned
in-flight PR work; any capability expansion. Every item is evidence or
correctness, not new scope.

- **P0 delivery-blocking correctness** (independent, dispatchable now):
  1. Kwavers `swe/gpu/solver.rs:92` `propagate_waves_gpu` ignores its inputs,
     launches no kernel, and returns hardcoded-constant timings. Acceptance:
     either a real kernel dispatch with a CPU-differential oracle, or the
     production-named surface is withdrawn and the performance model renamed and
     moved out of the solver path. `[major]`
  2. CFDrs `cfd-validation/src/benchmarking/memory.rs:93` ungated
     `#[global_allocator]` in a library crate. Acceptance: allocator confined to
     a bench/bin target or `cfg`-gated; a consumer crate declaring its own
     allocator compiles. `[major]`
  3. Consus `consus-compression/src/codec/szip.rs:226` reserves from an
     unvalidated `u32` reachable via HDF5 filter id 4. Acceptance: length bounded
     against remaining input, `try_reserve`, typed error, plus a fuzz target over
     a malformed corpus. `[patch]`
  4. Consus `-C target-cpu=native` in committed `.cargo/config.toml`. Acceptance:
     removed; runtime ISA detection is the dispatch mechanism. `[patch]`

  Consus PR [#51](https://github.com/ryancinsight/consus/pull/51) is the
  existing owner for P0-3/P0-4 at exact head
  `2e24e6adda663db67b4bf1d4e1614e2c3b06fc19`; its repository matrix remains
  queued in run `32408174545`. Do not start a competing patch. The dead
  `.cargo/config.toml` `xtask` alias remains a separate cleanup residual after
  this PR.

- **P1 make the accelerator seam verifiable** (the audit's single largest
  evidence gap, four independent confirmations):
  5. Hephaestus host/CPU reference device implements 1 of 18 operation seams:
     `HostDecompositionOps` is the only arithmetic-family implementation.
     The shared conformance crate exports 20 clauses, while the host invokes
     only the decomposition and transfer assertions; no host conformance job
     is present in the current backend workflows. Coeus binds ten operation
     families, Athena binds dense/sparse vector families, and Kwavers binds
     `Fdtd3dOps`, so the seam gap is consumer-reachable. Acceptance: host impls
     for the seams consumers bind, and a shared conformance suite running
     GPU-vs-CPU differential cases with tolerances derived per
     `numerical_discipline`. `[minor]` — unblocks 6 and 7. The next bounded
     slice is `SUBSTRATE-003`: consolidate the nine decomposition differential
     helpers into one parameterized clause, reconcile the stale 14-versus-15
     method count, and add an exact host gate for the complete decomposition
     surface. Evidence: fetched Hephaestus `origin/master`
     `607ce3f`; current hosted results were not queried.
  6. Apollo, Coeus, and Kwavers GPU suites report green having executed nothing.
     Acceptance: an executed-case counter that fails the job at zero, plus a
     software adapter (`lavapipe`/WARP) or an explicit recorded skip that is
     visible in the gate result rather than silent.
  7. RITK `GpuFieldSmoother`/`CpuOrGpu` have no reachable GPU backend and carry
     unbacked speedup claims. Acceptance: wired to the Hephaestus seam, or the
     claims withdrawn pending it. `[minor]`

- **P2 retire vacuous gates** (cheap, high signal-to-noise):
  8. `mdbook test` coverage is uneven. Gaia's direct gate is vacuous because
     its book has zero Rust fences; Tyche, Proteus, Mnemosyne, Asclepius, and
     Iris execute real samples but retain 37 ignored Rust fences across the
     audited books. Acceptance: Gaia gains one value-semantic executable book
     example, and ignored snippets are converted to `text` or real executable
     examples where their chapter claims a workflow. The shared gate itself is
     not removed. Book chapters documenting non-existent APIs (Hephaestus,
     Mnemosyne, Helios) were corrected in this sweep; re-verify at merge.
  9. Themis `tests/topology/cpu.rs` orphaned target (14 tests never compiled);
     CFDrs 54 files / 10,543 LOC under root `examples|benches|tests` in no cargo
     target; Hermes ADR-005 generator that deletes 14 shipped kernels when run.
     Acceptance: each either wired into a target and green, or deleted.

- **P3 adjudicate the open decisions** (blocking, not mechanical):
  10. Leto/Athena solver ownership is decided: root ADR 0033 is Accepted and
      names Athena as the Krylov owner. The remaining work is deletion of the
      duplicate Leto implementation and caller migration, not a decision
      question. Acceptance: revise the affected ADRs with the dated decision,
      delete the loser, and migrate callers in one change. `[arch]`
  11. The root corpus has 48 ADRs: 15 `Proposed`, 30 `Accepted`, and 3
      `Rejected`; six Proposed records are Kwavers-related. Acceptance: each
      Proposed record is Accepted with an as-built rationale, Rejected, or
      deleted with its reason in the commit. `[patch]`
  12. Centralized ADR indexing is closed as a blocker: the root generator scans
      the Atlas root plus 23 provider ADR directories, and root conformance CI
      runs the check. Provider index dirt remains a separate peer-owned
      cleanup, not a missing generator. `[patch]`
  13. Eighteen registered-provider root manifests (19 including the RITK member
      manifest) declare `rust-version = "1.95"`; nine providers lack an
      explicit 1.95 workflow pin: Aequitas, Apollo, Harmonia, Helios, Hermes,
      Horae, Hyperion, Proteus, and RITK. Acceptance: add an MSRV job at the
      declared floor or correct the declared floor to the toolchain actually
      built. `[patch]`

**Dependencies:** 6 and 7 depend on 5. 1 through 4 are independent. 10 gates any
further Leto or Athena solver work.

**Risk:** items 1, 2, and 10 are `[major]`; 1 and 10 need an ADR before
implementation per `versioning`.

**Verification plan:** each item's acceptance oracle above, run through the
owning repository's committed gate. No stack-wide claim is made until the
per-repository gates run; this audit executed none.

**Meta-repository residual:** 16 of 25 submodule checkouts drift from their
committed gitlink; kwavers (5), consus (3), and helios (3) exceed the two-tree
lane bound; 8 empty `worktrees/kwavers-*` orphans remain. Filed here rather than
actioned, since every one of those trees holds peer state.

## ATLAS-GAIA-BOOK-GATE-2026-08-20 — Add value-semantic book execution [patch] — in progress

The fetched Gaia default `dbed97a63434a21b1b9dcd01d634276aaec99e37` invokes
`mdbook test docs/book`, but the book contains zero Rust fences. Its mesh-gallery
generator is executable but does not provide mdBook contract coverage. This is
a bounded documentation/test increment; it does not change mesh algorithms,
figures, or the peer-owned Gaia README, CHECKLIST, or untracked backlog.

**Owner:** current Atlas session. **Claimed lane:**
`D:\\atlas\\worktrees\\gaia-book-gate`. **Claimed files:** one existing Gaia
book chapter, one included example source if the book convention requires it,
and Gaia's owner-local PM entry. **Acceptance:** one real input-sensitive Gaia
API example is included by the book, `mdbook test docs/book` executes it with a
value-semantic assertion, strict links and `mdbook build` pass, and the change
is published and verified at its exact provider head. No `rust,ignore` or
existence-only assertion satisfies the item. PR [#33](https://github.com/ryancinsight/gaia/pull/33)
is published at exact head `39a4f7fb0349bbd427fd12ddd99b0acc6baa654c` after
repairing the book workflow to capture only the current Cargo compiler-artifact
paths before staging them for mdBook. The earlier book run `32417028130`
tested the pre-repair merge ref and failed with `E0463: can't find crate for
gaia`; the intermediate run `32459250549` is superseded because its broad
staging step could select multiple cached Gaia revisions. A local run against
the shared Atlas cache reproduced that cache-sensitive `E0464: multiple
candidates` condition. The exact-one-library guard is now also enforced.
Replacement CI run `32473606516` is pending and book run `32473606617` is
queued at the exact current head; the earlier replacement runs
`32473502019`/`32473502075` are superseded. Hosted clean-runner execution
remains the required staging evidence. Local `mdbook build docs/book` and link
checking pass at the repaired lane head.
`recurseml/analysis` is report-only.
- **Closed (2026-08-22):** PR #33 merged at Gaia default `9b476fec` with the
  expected-head guard; both exact-head runs `32473606516`/`32473606617`
  terminal success, post-merge main CI and mesh book runs terminal success,
  and live Pages returns HTTP 200 with the expected title. The Atlas gitlink
  advanced to `9b476fec` (commit `0f58972`).

## ATLAS-CFDRS-FORMAT-GATE-2026-08-20 — Restore exact-default formatting gate [patch] — in progress

The exact CFDrs default `aa54f5cdcdc4e406df0c60ea6c3cb507e968fc97` has a red
hosted CI run `32323543129`; the failure is formatting-only in
`crates/cfd-2d/src/solvers/cell_tracking/tracker.rs`,
`crates/cfd-core/src/management/aggregates/parameters.rs`, and
`crates/cfd-core/src/physics/cavitation/number.rs`. The canonical checkout is
peer-owned and dirty, so the bounded lane owns those three source files plus
the provider validation caller required to repair the hosted runtime failure.

**Acceptance:** the exact three-file format correction and the provider-side
validation repair are committed and pushed; the provider's exact-head Rust and
Pages gates are terminal green, with no peer source or lockfile state included.
This slice does not claim broader CFDrs closure until those gates pass.

The current Atlas session owns the bounded lane
`D:\\atlas\\worktrees\\CFDrs-format-gate`, PR
[#361](https://github.com/ryancinsight/CFDrs/pull/361). The exact-head provider
CI run `32408413904` at the formatting-only head is terminal failure. The
provider repair now has local exact nine-test numerical-fidelity evidence.

**Timeout increment (2026-08-22, head `c993b906`):** the replacement hosted run
`32449587886` at `c1e4fdcf` failed on the committed 30s nextest termination
bound — `cross_fidelity_trifurcation_dominance` terminated at 30.008s. Local
instrumentation attributes the cost to the Picard assembly/Krylov path (~9s)
plus SDF meshing (~1s) spread across first-party FEM code and provider-external
numeric crates (`gaia-mesh`, `leto`, `nalgebra`), so named-package opt-level
raises measured no effect. Raising the test profile to `opt-level = 2`
measures 11.4s → 2.0s locally (5.5×), restoring hosted headroom; dev/debug
profiles are unchanged and no test or workload was reduced. Local evidence at
`c993b906`: `cfd-validation` nextest 435/435 (10.3s total), doctests 4 passed,
`cargo fmt --all --check` clean. **Closed (2026-08-23):** replacement hosted run
`32588697868` terminal success at `c993b906`; PR #361 merged with the
expected-head guard at default `a70faea6`; default CI run `32589906080`
terminal success; live Pages HTTP 200 (the merge touched no book content, so
no Pages deployment is expected). The Atlas gitlink advanced to `a70faea6`
(commit `43fe895`).

## ATLAS-CFDRS-ALLOCATOR-2026-08-20 — Remove library global allocator [major][arch] — in progress

The CFDrs provider audit confirms `cfd-validation` installs a process-wide
`#[global_allocator]` from library code. This contaminates downstream
allocation measurements and prevents consumers from declaring their own
allocator. The current session claims only the cfd-validation memory profiling
surface, its opt-in benchmark harness, its consumer-allocator regression test,
and the provider ADR/PM records; unrelated CFDrs peer edits remain untouched.

Acceptance: the library has no global allocator; the tracking allocator is
constructed only by an explicit benchmark/test harness; a downstream-style
integration test declares `System` as its allocator; and the provider's locked
workspace all-target gate passes. This is a public breaking change and follows
the provider's recorded allocator decision.

Evidence: provider commit `d1305ee2` removes the library allocator, makes the
tracking counter explicit in `MemoryProfiler` and `CfdMemoryProfiler`, adds the
`memory_profiling` benchmark and `allocator_compat` integration test, and records
the decision in `repos/CFDrs/docs/adr.md`. Direct rustfmt, focused clippy, a
non-locked diagnostic check, `cargo nextest run -p cfd-validation --lib`
(187/187), the focused allocator nextest (1/1), and benchmark compilation pass.
The required locked check is still open: the Atlas overlay makes Cargo request
a provider `Cargo.lock` rewrite under `--locked`; that lockfile is peer-dirty
and was not modified or staged by this session.
The exact provider commit is now the head of open CFDrs PR
[#360](https://github.com/ryancinsight/CFDrs/pull/360); Rust workspace and
figure checks are queued there.

## ATLAS-SUBSTRATE-003-2026-08-20 — Give the Leto/Hephaestus decomposition pair one seam and one oracle [minor][arch] — in progress

The Hephaestus audit found nine duplicated Leto differential helpers in the
decomposition conformance module, a stale 14-method count against the current
15-method `DecompositionOps` seam, and no exact host gate for the complete
surface. This session claims only the provider conformance module, its host
decomposition test, the required provider ADR/index update, and these Atlas PM
records. Other Hephaestus peer edits remain untouched.

Acceptance: one parameterized differential clause covers all current
decomposition methods with tolerances derived from the existing numerical
contract; the stale count is corrected; the host runs the same clause as the
GPU backends; and focused provider formatting, warning-denied checks, and
nextest pass. The exact hosted provider gate remains required before the Atlas
gitlink advances.

Evidence: Hephaestus commit `d24513a` routes the nine Leto differential cases
through `assert_leto_differential_contract`, corrects the host and ADR 0046
count to fifteen, and preserves the shared host clause. Local checks pass:
focused compile, host decomposition nextest (1/1), warning-denied Clippy,
doctests, and direct rustfmt/diff checks. The exact commit is the head of draft
Hephaestus PR [#215](https://github.com/ryancinsight/hephaestus/pull/215);
CUDA, Metal, ROCm, and WGPU hosted checks are queued. The local locked check
remains blocked by the Atlas overlay requesting a dirty provider lockfile
rewrite.

## ATLAS-PROVIDER-CLOSURE-2026-08-20 — Complete active provider slices [major][arch] — in progress

- **Themis executable book gate:** current Atlas session claims the provider
  workflow caller only, on the reusable `themis-book-test` lane. The existing
  book already has two included executable examples; acceptance is a provider
  PR adding the shared `mdbook-test` inputs, exact-head hosted book success,
  and post-merge default verification. PR [#27](https://github.com/ryancinsight/themis/pull/27)
  merged at default `c76a55e5eb9988b48bba69e67d6e07ce5fe55ea8` after exact
  PR CI `32399070177`, MSRV `32399070178`, and book build `32399070626`
  passed. Post-merge CI `32402753573`, MSRV `32402753617`, and Pages/book
  run `32402752669` now pass, including deployment job `96545229314`; the
  live page returns HTTP 200. The Atlas gitlink equals that merged default.

- **RITK executable book gate:** current Atlas session claims the provider
  workflow caller and existing executable samples only, on the reusable
  `ritk-book-test` lane. Open PR #201 owns source, lockfile, and connectome
  chapter changes; this item does not overlap those paths. PR #202 merged at
  default `ad5085257b6dee9110375bbca29e20d676c83f58` from exact head
  `dc9bf9cda2fd007597205312645038bc48727d0c`; local mdBook build and strict
  links pass, but the PR provider CI, Python, and book runs
  `32402257906`/`32402258085`/`32402259004` were still queued at merge. Default
  CI, Python, and book runs `32404089256`/`32404089147`/`32404089897` are now
  queued. Acceptance remains terminal passing evidence on the merged default;
  Atlas does not advance the gitlink from `d4a978f` until then. The book run
  failed with `E0460` because the shared workflow selected a hashless
  dependency artifact by directory order; root `20c9398` preserves Cargo
  artifact hashes, and RITK PR [#204](https://github.com/ryancinsight/ritk/pull/204)
  adopts it at `9bc47d42`. Its CI and book runs `32410451435`/`32410452203`
  pass; the current default `b35c9331` has terminal CI and Pages deployment
  success, and live Pages returns HTTP 200. The Atlas pointer advances from
  `d4a978f` to `b35c9331` without switching the dirty primary checkout.

- **Apollo executable book gate:** current Atlas session claims only
  `apollo/.github/workflows/book-pages.yml` on a clean `apollo-book-test` lane.
  The existing FFT round-trip and Parseval examples are included by the book
  and already carry value-semantic assertions. Acceptance is the shared
  `mdbook-test` caller against `apollo-fft`, exact hosted book evidence, and
  post-merge default verification. Apollo's peer-owned Cargo.lock, backlog,
  and CHANGELOG work remain outside this item; the hosted gate is sequenced
  after the active RITK collection. Local commit `27f0c4c3` passes mdBook build,
  strict links across 14 Markdown files, and workflow-shape checks. PR
  [#108](https://github.com/ryancinsight/apollo/pull/108) merged after its
  exact-head Rust/Python, benchmark, and book runs passed. The provider default
  is now `a0c3da9`; post-merge CI `32421484168`, mdBook `32421484508`, and
  Pages `32421483175` are terminal `success` at the merged default. The Atlas
  gitlink is advanced from `0c6ffb9` to `a0c3da9` without switching the dirty
  primary checkout.

- **Hyperion chromophore provenance:** the source audit disproved the
  unsupported ×4 premise: OMLC presents the retained hemoglobin values as
  molar extinction coefficients using 64,500 g/mol hemoglobin, so the provider
  uses those values directly. Commit `0213f947` adds the resolvable OMLC
  locator, independent source-knot oracle, accepted ownership ADR, and
  synchronized docs. Local formatting, ADR-index, mdBook-build, and strict-link
  checks pass; locked Cargo gates stop before compilation at the shared overlay
  lock-form mismatch. PR [#21](https://github.com/ryancinsight/hyperion/pull/21)
  merged at provider default `4df62f63`. Post-merge CI run
  `32415389400`, mdBook run `32415390244`, and Pages workflow
  `32415388456` are queued. The Atlas pointer remains at `e2dbc9b` until the
  merged-default gates are terminal and the deployed page is verified.

- **Hephaestus executable book gate:** the current Atlas session owned only
  `hephaestus/.github/workflows/book-pages.yml` and the included HostDevice
  and capabilities examples. The exact-head fix added the missing explicit
  crate declarations, removed two unused imports, and repinned Atlas staging
  to `20c9398`; local diff-check, mdBook build, strict links (14 files/13
  links), and workflow-shape checks passed. PR [#214](https://github.com/ryancinsight/hephaestus/pull/214)
  merged at provider `master` `7e09efa`. Post-merge provider jobs for WGPU,
  CUDA, ROCm, and Metal pass; the mdBook build and Pages deployment pass; and
  live Pages returns HTTP 200 with the expected Hephaestus title. The Atlas
  pointer advances to `7e09efa` without switching the dirty primary checkout.

- **Coeus executable book gate:** current Atlas session claims only
  `coeus/.github/workflows/book-pages.yml` on a clean `coeus-book-test` lane
  based on provider `origin/main`. The existing Tensor Basics and Matrix
  Multiplication examples are real included programs; acceptance is the shared
  `mdbook-test` caller for `coeus-ops`, exact hosted book evidence, and
  post-merge default verification. The detached primary checkout's provider
  implementation, lockfile, and PM dirt remain outside this item. Local lane
  commit `fc05cb75453bbb36d0f5b59f73b40dea0c432f44` passes diff-check, mdBook
  build, strict links (14 files/13 links), and workflow-shape checks. The
  locked package build is blocked before compilation by the shared Atlas
  overlay resolving primary-tree patches from the clean lane; hosted Linux is
  the package gate. Push and hosted collection remain sequenced behind the
  active merged-default runs.
  The failed exact-head book job was caused by missing explicit crate
  declarations in the included examples. The lane now adds those declarations
  and repins Atlas staging to `20c9398`. PR
  [#340](https://github.com/ryancinsight/Coeus/pull/340) merged after its
  provider-contract and book runs passed. The provider default is now
  `5108ed0082fc5c5ed02bc95c4bfa4ad9cdf8133b`; post-merge backend parity
  `32421487491` and mdBook `32421487793` are terminal `success` at the merged
  default. The Atlas gitlink is advanced from `5adc2d1` to `5108ed00` without
  switching the detached dirty primary checkout.

- **Live-tree conformance residual:** the local `python
  scripts/atlas-conformance.py check --worktree` sweep at audit revision
  `72cc6eb` plus live peer state exits 1 with 13 regressions and 27
  tightening classes against the committed baseline. The regressions are
  CFDrs oversized files and existence-only assertions; stale Consus classes
  from a checkout 49 commits behind origin; Moirai production `SeqCst`; and
  stale RITK implementation, type-suffixed, and commented-code classes from a
  checkout five commits behind origin. The run raises no baseline and does
  not discard peer or derived state.

- **Stack formatting sweep:** `scripts/atlas-fmt-check.py` passes for 23 of 24
  registered members. CFDrs reports 42 pre-existing unformatted files on the
  peer-owned `codex/cfdrs-tvd-test-integration` branch; no formatting rewrite
  was applied across that dirty claim. The corrected environment also passes
  toolchain preflight, version coherence, standalone lock-form (27 locks),
  registry metadata (253 manifests), board-ID lint, and strict book links.
  The full Atlas script suite passes `278` tests and `74` subtests in `8.77s`.
  The lane audit now ignores sanctioned `worktrees/.archive` metadata after
  pruning the stale Helios reference; only Kwavers's three peer-held trees
  remain reported.

- **Kwavers moving default:** fetched `origin/main` is now
  `0e786481cbcf3adad41ccb1f3efa6c94f6dc3f53`, after merged PR #436. Earlier
  hosted runs at `58b51ef3` cannot authorize the stale Atlas pointer
  `459f18ce8248ea91ace62a2f8f89a02b861a56fe`. Current PR #439 remains at
  exact head `2fa5f4d8a88d2ff16df866f15c5a1c4dd5d58b44` and is now `CLEAN` after
  a merge commit that preserves KW-CI-115 beside KW-GPU-200/201/202. No
  provider source or dirty worktree was overwritten.  The merged-default
  Pages run `32419107056`, CI run `32419106520`, architecture run
  `32419106681`, and legacy audit run `32419106514` are all terminal
  `success` at `0e786481`, and the live page returns HTTP 200. The Atlas
  pointer is advanced `459f18ce`→`0e786481` without switching or modifying
  the dirty primary checkout.
  Full exact-head/coherence audit now reports one remaining pointer drift:
  RITK `d4a978f`→`ad508525` (held: its merged-default Deploy mdBook gate
  `32404089897` is red on the E0460 hashless-artifact staging defect; the fix
  is RITK PR #204 at `9bc47d42` adopting Atlas `20c9398`, still open). Hermes
  PR #55 merged at `05441dd1`; its post-merge CI `32418079699` and Pages
  `32418078426` are terminal `success`, and the Atlas Hermes pointer is
  advanced `c5e4c2dc`→`05441dd1`.

- **RITK DTI frame contract:** PR [#198](https://github.com/ryancinsight/ritk/pull/198)
  merged at default `2d159850636a6539db61109533f399d31cc7c6f4`. Post-merge CI
  `32387951529`, Python CI `32387951635`, and Pages `32387952289` all pass.
  Live Pages `https://ryancinsight.github.io/ritk/` returns HTTP 200 with title
  `Introduction - atlas/RITK: Medical Image Processing and Registration`.
  PM closure PR [#199](https://github.com/ryancinsight/ritk/pull/199) merged at
  `ee76393fff7aaeae1a0c9f2712bcf8b8062c5303`; its docs-only closure records
  the same hosted evidence. Follow-up safety PR [#200](https://github.com/ryancinsight/ritk/pull/200)
  merged at `d4a978fce40f37b3668afa5d98783626aaf74cff`; post-merge Rust/Python
  CI `32395213485`/`32395213488` pass. Atlas advances its gitlink to the
  verified current default.
- **Tyche publication boundary:** PR
  [#30](https://github.com/ryancinsight/tyche/pull/30) merged at provider
  default `bfe6ab72915ff1d29357dd6895c39a11baecfbc0`. Post-merge CI
  `32386013998` and dynamic Pages `32386011656` both pass. Atlas gitlink
  advances to `bfe6ab72`. The facade, Consus-adapter, and Moirai-adapter
  packages are explicitly private; `tyche-core` remains the only publishable
  package. External registry/release configuration remains a separate residual.
- **Kwavers distributed queue:** PR
  [#427](https://github.com/ryancinsight/kwavers/pull/427) merged at
  `33a980acb4695500dd154111aa05a2947af4ad4d`. All 28 non-null CI gates pass;
  `WorkQueue::wait_all` waits for both queued and executing tasks; workers
  block on scheduler state notification. Atlas gitlink advances to the merged
  default.
- **Consus ADR-0045 P4 benchmark gate:** PR
  [#50](https://github.com/ryancinsight/consus/pull/50) merged at
  `e121b9d4258bab09144dfda68813aa9178090c0c`. All non-infra gates pass on
  rerun. Atlas gitlink advances to the merged default.
- **Helios Apollo lock sweep:** branch `codex/helios-apollo-lock-sweep` at
  `25f04b6` published as PR [#68](https://github.com/ryancinsight/helios/pull/68).
  Advances Apollo `d585e0f5`→`0c6ffb91`, Moirai `3d5d4c66`→`3b812865`, Themis
  `d0fcce7a`→`0484a333` in `Cargo.lock`; no Helios source or manifest change.
  Exact-head MSVC verification passes: format, locked metadata, full workspace
  check, warning-denied workspace Clippy, and Nextest run
  `4bfa9901-c55a-4cc1-a23f-b90d8f1542f8` with 262/262 tests and 9 skips.
  Hosted PR #68 required checks pass: Rust workspace, Python bindings, book
  build, and benchmark regression check. The `recurseml/analysis` context is
  report-only and remains an analysis error. PR #68 merged as
  `7ff72e37889594b6592e1f8b8b169834765f7851`; Atlas advances its gitlink to
  that merged default.
- **Tyche checklist reconciliation:** docs-only PRs #31 and #32 close stale
  TYCHE-006 and TYCHE-004 checklist entries; the merged default is
  `10410f2de1ce1529ecbff50fa740b23a1c8f77b9`. Pages run `32394886461` passes;
  current default CI `32394888136` passes at the same exact head. Atlas advances
  its gitlink to the merged default; no Tyche hosted verification residual
  remains for this item.
- **Requested-provider structural recheck:** at root commit `2fb4409`,
  `python scripts/atlas-provider-integration-audit.py --structural-only
  --provider-set requested-2026-08-14 --format json` reports `status: ok`,
  `provider_count: 20`, and `issues: []`. This validates registration and
  integration markers only; exact remote heads, checkout cleanliness, and
  hosted workflow terminality remain separate evidence classes.
- **Requested-provider exact-head recheck:** the bounded remote run at the
  same root revision exits non-zero with six pointer drifts: Hyperion, Hermes,
  RITK, Coeus, Apollo, and Kwavers. No Atlas gitlink advances are authorized
  from this run; each requires terminal hosted evidence at the fetched default
  before pointer reconciliation.

## ATLAS-KWAVERS-DISTRIBUTED-QUEUE-2026-08-20 — close queue completion and deadline contracts [patch] — in progress

- **Owner:** current Atlas session; detached Kwavers checkout with a disjoint
  distributed-scheduler scope while Aequitas hosted book gates run.
- **Claimed scope:** `crates/kwavers-analysis/src/distributed/{queue,scheduler,task,mod}.rs`;
  preserve the checkout's peer-owned medium, physics, and ADR changes.
- **Baseline findings:** `wait_all` observes only queued work after workers
  remove tasks, so it can return while the last task is executing; worker idle
  handling polls with a fixed sleep; deadline construction wraps on
  `u64::MAX` overflow.
- **Acceptance:** queue completion waits for both queued and executing work;
  workers block on scheduler state notification; overflowing deadlines return
  the existing typed invalid-input error; deterministic value-semantic tests
  cover active-task completion and the overflow boundary; focused locked
  format, Clippy, nextest, doctest, and rustdoc evidence is collected or the
  exact shared-cache blocker is recorded.
- **Landed provider increment:** Kwavers commits `073a5adbb` and `7245db7e4`
  implement and document the slice. PR [#427](https://github.com/ryancinsight/kwavers/pull/427)
  is open at exact head `7245db7e44a7f461a34ff2d67e5b7f1a76bc69c1`; local
  focused evidence passes, while repository-hosted CI/Architecture runs have
  not yet attached to the reopened PR event.
- **Non-goals:** no changes to the existing peer-owned Kwavers medium,
  physics, visualization, workflow, lockfile, or documentation edits.

## ATLAS-CFDRS-HOSTED-FMT-2026-08-20 — repair required Rust format gate [patch] — in progress

- **Owner:** current Atlas session; peer-assist claim on the clean files only.
- **Scope:** `repos/CFDrs/crates/cfd-2d/src/solvers/cell_tracking/tracker.rs`,
  `repos/CFDrs/crates/cfd-core/src/management/aggregates/parameters.rs`, and
  `repos/CFDrs/crates/cfd-core/src/physics/cavitation/number.rs`.
- **Acceptance:** the three files pass the repository formatter, the staged
  diff contains only formatter output in those files, and the focused provider
  check records the exact branch head. Unrelated peer-owned CFDrs dirt remains
  outside this item.
- **Evidence:** hosted CFDrs run `32323543129` reports the same three files as
  the Rust workspace formatting failure. This item fixes that concrete gate
  defect without changing tests, workloads, tolerances, or budgets.
- **Landed:** CFDrs commit `cd56f744` (`fix(cfd): Restore hosted formatter
  compliance`) is pushed to `codex/cfdrs-tvd-test-integration`; PR #360 open.
  Exact-file `rustfmt --edition 2024 --check` passes, and the overlay-free locked package
  check for `cfd-core` and `cfd-2d` passes.
- **Verification residual:** focused `cargo nextest` run
  `fdf1abe0-d650-4346-b1d2-e82fd96e3eed` reaches 55 passes and 27 configured
  skips before the first failure in peer-dirty
  `cfd-2d::physics::acoustics::gorkov::tests::f1_f2_analytical_values`
  (`0.19151009397460816` vs `0.2315809676184497`, bound `1e-10`); 800 tests
  were cancelled by fail-fast. The peer edit in `gorkov.rs` changed
  `typical_rbc()` from the test's `1000/1500` values to blood constants. This
  item does not modify that peer-owned file; the hosted gate remains open until
  the owning change reconciles the oracle and a clean default-head rerun passes.

## ATLAS-HOSTED-RECHECK-2026-08-19-2 — current provider state [patch]

- **Moirai packaging and scheduler repair:** the provider branch
  `fix/moirai-package-manifest` is pushed at `5ccd72944ab31adf55e020931e969cbecb3a6f4e`
  and carries the standalone package cleanup, complete metadata/examples,
  allocation-free Chase-Lev generation claims, strong arbitration CAS, and
  Miri-valid SplitDeque provenance. Local evidence at that exact head is
  `cargo package --workspace --locked` for every member with no warnings,
  `cargo nextest run --workspace --all-features --locked` 801/801 with 6
  configured skips, warning-denied workspace Clippy, doctests 19 passed/1
  ignored, rustdoc, Loom 1/1 (exact final-head run
  `d6ff0225-9353-45ef-84cc-492d74eb39bf`), and deque-focused Miri 16/16.
  The Loom invocation ran outside the Atlas development overlay while using
  the shared `D:\atlas\target` cache because the overlay resolves Moirai
  patches to the main checkout rather than this bounded lane; the standalone
  package, workspace, and value gates remain locked evidence at the lane
  head. Full-crate Miri reaches the Themis Windows NUMA FFI test, which is
  unsupported by Miri; no deque failure remains. Existing PR #143 is open,
  mergeable, and hosted Rust and book checks pass; the Ubuntu wheel smoke test
  remains pending (`32328186717`), so Atlas retains its default gitlink until
  the hosted matrix completes and the PR merges.
- **Kwavers:** fetched `origin/main` is
  `64b982bdbfc2b7e36f11971947f5bdd8ed59d1f1`, the merge of PR #418 after
  ADR 112 was committed with its required Aequitas `Degree` surface. Atlas
  now points at this head in root commit `178e598`. The exact-head audit,
  overlay check, registry metadata scan (`252` manifests, `0` violations,
  `0` unverified), and standalone lock-form check (`27` locks plus the
  documented in-tree Melinoe fixture exemption) pass against this state.
- **Aequitas:** provider commit `809fc973f5df8c0bc0810161851466535efa74db`
  splits the derived SI units into six domain-named leaves and leaves
  `derived/mod.rs` as a manifest/re-export surface. The clean-provider
  conformance residual `manifest_implementation=1` is now `0`, with every
  other class unchanged at zero. Pinned-MSVC Clippy passes, Nextest passes
  `127/127`, doctests pass `17 + 9` compile-fail cases with one ignored, and
  rustdoc completes; the current Atlas pointer is advanced in this increment.
  Hosted CI `32325130976` and Pages `32325130273` pass at this exact head.
- **RITK:** PR #194 merged at `337f0dc5` after hosted CI
  `32323289141` and Python CI `32323289137` completed successfully; the
  report-only `recurseml/analysis` error does not block delivery. Fetched
  `origin/main` and the Atlas gitlink already resolve to `65bee2c2`, so no
  pointer mutation is required.
- **Standalone package gate:** running `cargo package --workspace --locked`
  outside the Atlas overlay packages the preceding RITK crates, then stops at
  `ritk-block-matching`: its `apollo-fft = ^0.27.0` requirement has no matching
  crates.io candidate (`0.26.0` and `0.25.0` are the available versions).
  This is a release-order blocker requiring Apollo 0.27 publication before the
  RITK workspace can claim complete crates.io package evidence; the dependency
  is not weakened and no release is performed without release authority.
- **Hyperion package gate:** the standalone locked package attempt fails while
  resolving crates.io Proteus: available `proteus 0.1.x` versions do not expose
  the `std` feature requested by Hyperion, although the current git provider
  does (`proteus/Cargo.toml:23-25`). This is registry publication/version
  coherence, not a reason to remove `proteus/std` from Hyperion; Hyperion and
  its downstream consumers remain release-blocked until Proteus is published
  with the matching feature surface.
- **Asclepius package gate:** standalone `cargo package --workspace --locked`
  passes for both `asclepius` and `asclepius-coeus`, including verification in
  the unpacked registry. Its dependency graph resolves published Apollo FFT
  `0.26.0`, providing a positive package result and independently confirming
  that RITK's Apollo `0.27.0` requirement is the registry-order blocker.
- **Horae package gate:** standalone `cargo package --workspace --locked`
  packages and verifies `horae v0.1.0` successfully outside the Atlas overlay.
  The package result is valid crates.io content evidence; publication remains
  governed by the provider's occupied-name/release-authority constraints.
- **Moirai package gate:** standalone `cargo package --workspace --locked`
  reaches manifest verification and stops at `benchmarks/Cargo.toml`: its
  path-only internal dependencies have no version requirements, which Cargo
  rejects for packaging (`dependency moirai-runtime does not specify a
  version`). The same manifest is present on fetched `origin/main`; this is a
  provider packaging defect, not a reason to weaken the runtime dependency
  graph. The benchmark README path and out-of-package example paths also emit
  packaging warnings and require the same provider-owned cleanup.
- **Horae:** the exact `--all-features` native gate passes `23/23`, and its CI
  and Pages callers enable the book test. The local Windows `mdbook test`
  invocation reaches rustdoc but fails with a GNU/MSVC artifact mismatch
  (`E0461`); no chapter-content failure is inferred.
- **Helios:** draft PyPI PR #67 remains open at `f31f2619`; its Rust, Python,
  benchmark, and book-build checks pass while Pages deployment is skipped. The
  checkout retains peer-owned manifest dirt.
- **Apollo:** PR #107 remains open with Rust and benchmark failures. The
  benchmark audit localizes the regression to the four const twiddle-cache
  initializers in `crates/apollo-fft/src/application/execution/kernel/mixed_radix/caches/twiddle.rs:26-29`.
- **Root worktree:** exact provider/integrator heads, overlay, registry
  metadata (`252` manifests, `0` violations), and 27 standalone lock forms
  pass locally. The intentional dirty-tree conformance snapshot reports
  `609` oversized files, `674` implementation-bearing manifests, `1,196`
  production unwraps, `518` allow sites, `803` existence-only assertions, and
  `4` excess-worktree sites; these remain peer-owned ratchet debt rather than
  reproducible clean-tree gate results.

## ATLAS-RITK-DEFAULT-RECONCILIATION-2026-08-19 — docs-only merge [patch]

- RITK default advanced from `01175d67874724eee72a88ba1ee9dd56a52d7c79`
  to merge commit `52f9d3b008269017297c4679792391958a561f7f` through PR #189.
  The merge changes only `backlog.md` and `checklist.md`; Atlas advances the
  gitlink without modifying the peer-dirty RITK checkout.
- The CI and Python runs attached to `01175d6` remain queued and do not prove
  the new docs merge. No hosted closure is claimed; the next exact-head run
  must bind to `52f9d3b` before the RITK gate is closed.

## ATLAS-PROVIDER-MERGE-RECONCILIATION-2026-08-19 — verified provider slices [patch]

- **Hyperion:** PR #18 merged at provider default merge commit
  `af28f5ac8ed56584a666e05e7fc1f28dc927e232`. The source delta is the
  provider recheck record in `checklist.md` and `gap_audit.md`; hosted
  `verify` and `supply-chain` passed at exact head `3d064ac`, and CodeRabbit
  passed. RecurseML remains an external report-only error. Atlas now records
  the merged default gitlink rather than the pre-merge branch head.
- **Asclepius:** PR #21 merged at provider default merge commit
  `f5b5fb832660a7696a0893f9abf1fc543d29fa2d`. The package/book/CI source
  delta is retained in the provider history; hosted book build, `verify`,
  and `supply-chain` passed at exact head `943c83c`, and CodeRabbit passed.
  RecurseML remains an external report-only error. Atlas now records the
  merged default gitlink.
- **Residual:** these merges close the two provider-slice delivery gates but
  do not close the stack-wide audit. Kwavers exact-head hosted runs, Apollo
  benchmark failure, Helios PR #67 hosted gates, Mnemosyne moving-default
  reconciliation, CFDrs PR #355, and RITK lock-form cleanup remain open.

## ATLAS-HORAE-CONSUMER-AUDIT-2026-08-19 — boundary finding [patch]

- **Result:** Horae's current production integration is limited to Harmonia's
  typed-time/subcycling contracts and Helios's validated `StepSize` boundary.
  `ExplicitSystem`, `step_into`, and `step_embedded_into` occur only in Horae
  tests/examples; no CFDrs or Kwavers production call site currently consumes
  the stepping API.
- **Decision:** No implicit or nonlinear solver is added to Horae. Its
  explicit-only boundary remains governed by provider ADR 0001, and Athena's
  roadmap requires a second concrete residual/Jacobian consumer before a
  shared nonlinear policy is defined. This is a consumer-gated follow-up,
  not a missing implementation to fill speculatively.
- **Residual:** CFDrs/Kwavers stepping migration is not complete and remains
  with their peer-owned worktrees; the exact production call-site migration,
  analytical oracle, and consumer gates must land before claiming full Horae
  stepping integration.

## ATLAS-HOSTED-RECHECK-2026-08-19 — moving-default evidence

- **Kwavers:** `origin/main` advanced to `9e7e5e95`; Architecture Validation
  `32282670417`, Legacy Migration Audit `32282670463`, and CI/CD Pipeline
  `32282670360` are queued. Atlas retains the previously verified gitlink
  `0a9842a` until those exact-head gates complete. The structural audit reports
  this one expected pointer mismatch and no other provider mismatch.
- **Apollo:** PR #107 head `d408c738` remains open; benchmark run `32217561595`
  fails 19 counterbalanced cases, while Python bindings pass and the Rust job
  is cancelled. No performance claim or pointer advance is made.
- **Helios:** PR #55 head `83f5ccea` has a failed Rust gate but passing Python
  and benchmark checks. The provider checkout contains peer-owned manifest dirt.
- **Mnemosyne:** default `b883cd1` has CI `32281506800` queued; Atlas retains
  that pointer while the local checkout remains peer-owned and dirty.
- **CFDrs:** default `834340f7` has completed CI `32230993545` successfully;
  the historical PR #355 failure is not treated as current default evidence.

## ATLAS-PUBLISH-GRAPH-2026-08-19 — crates.io dependency closure

- `scripts/publish-order.py --json` resolves 182 publishable packages across
  34 dependency layers with zero unresolved edges and no contested names.
- Fourteen publishable packages remain blocked by unpublishable foundations:
  `hyperion` blocks CFDrs, Helios, and Kwavers consumers; `proteus` blocks
  CFDrs, Helios, and Kwavers consumers; `horae` blocks `helios-domain`; and
  `asclepius-coeus` blocks `helios-planning`. These are release-topology
  blockers, not compilation evidence.
- The provider manifests intentionally retain `publish = false`; Horae’s
  board records its occupied registry name, while `hyperion` and `proteus`
  have occupied crates.io names. Renaming/flipping them is a breaking,
  release-authority change and remains an explicit follow-up rather than an
  implicit compatibility rename.

## ATLAS-HELIOS-PYPI-2026-08-19 — trusted wheel release [patch] — superseded 2026-08-20

- Helios provider branch `codex/helios-pypi-release` commits `0d64981`,
  `8d33395`, and `f31f261` add the PyPI distribution metadata, package README,
  changelog/landing-page entries, and a release workflow using the Atlas
  reusable abi3 wheel workflow plus PyPI Trusted Publishing. PR #67 merged at
  provider default `423d6ec9`; see the current integration record above.
- The distribution is named `helios-python` because PyPI already owns
  `helios` (`0.3.0`); the extension import remains `helios`, so the Python API
  is not renamed. The package uses the dynamic Cargo version and a py39 stable
  ABI floor.
- Python `tomllib` metadata validation and API/import-name checks pass. Local
  `maturin --release --locked` remains blocked before compilation by the shared
  Atlas overlay lock mismatch; no wheel or Rust gate is claimed locally.
- Helios `mdbook test docs/book` passes for every listed chapter and example;
  `mdbook build docs/book` also passes with the linkcheck2 renderer. The
  hosted release/build oracle is now the merged provider default recorded
  above; no release publication is claimed.

Fourteen read-only audits covering every registered member plus the meta-repo.
Every claim below is grounded at `file:line` in the audited tree. Items are
ordered by tier, and tier is set by *what breaks*, not by effort.

## ATLAS-PROVIDER-INTEGRATION-2026-08-18-CURRENT — superseding recheck [patch]

- **Kwavers metadata correction:** provider commit `308d91594` separates the
  MATLAB-free `k-wave-python` comparison extra from the MATLAB Engine extra,
  repairs the repository-root `maturin` commands, and is recorded by Atlas
  pointer commit `ad977c6`. The compiled extension and hosted comparator remain
  open.
- **Kwavers guidance cleanup:** provider commit `498f38a3e` removes the last
  stale `cd pykwavers` and `pykwavers-*.whl` instructions from test diagnostics
  and examples; Atlas records the pointer in `0a3e2dd`. The compiled extension
  and hosted comparator remain open.
- **Kwavers workflow closure:** provider commit `2bc5dd161` repins the book,
  Python-wheel, and crates.io callers to Atlas reusable-workflow revision
  `2f17abc`; the Python `atlas-ref` now names the pushed provider graph. Atlas
  records the exact provider head in `55d8b8d`. YAML parsing passes; the local
  extension and hosted comparator remain open.
- **Kwavers comparator gate:** provider commit `4e0135c76` adds a bounded
  Ubuntu/Python 3.10 wheel job that installs the declared k-Wave Python range
  and executes the real comparison suite with slow tests enabled. Atlas records
  the provider head in `2e00759`; closure is pending its value-semantic result.
- **Kwavers comparator dispatch:** provider commit `a10183c80` adds an explicit
  manual trigger to the wheel-smoke workflow, and Atlas records the exact head
  in `4073b1f`. The hosted parity run is still pending.
- **CFDrs rerun:** PR #358 now points at `5e13018a` after a hosted Clippy
  failure found and the provider fixed `clippy::inconsistent_struct_constructor`
  in `newton_fallback.rs`. Rust and figure jobs are pending; the pointer stays
  at the prior verified integration head until both pass.
- **Status:** Tyche cleanup, Aequitas integration, and the Aequitas/Themis
  hosted closures are complete for this increment. The remaining integration
  residuals are Apollo PR #107's rerun, Mnemosyne's moving default, CFDrs's
  figure/hosted closure, Kwavers's missing local Python extension, Helios's
  provider PM drift, and four peer-owned lane-topology violations. The
  structural provider audit, overlay, and standalone lock-form gates pass;
  exact-head is blocked only by Mnemosyne's unadvanced default.
- **Tyche evidence:** provider commit `de925e6` consolidates the shared
  Latin-hypercube/Sobol checked index conversions, removes five production
  type-suffixed helper names, and merged through PR #26 at default
  `7e55ff8f`. Nextest 51/51, doctests 18/18, warning-denied Clippy, rustdoc,
  and the conformance report all pass; every tracked conformance class is
  zero.
- **Atlas evidence:** the root pointer now matches fetched RITK default
  `9fa4981e`, a docs-only merge on top of the audited `f9d04a79`. Lock-form
  passes for 27 standalone locks and conformance passes 12/12. The latest
  exact-head audit is `OK` and the overlay reports aligned requirements and
  locks; the earlier RITK Apollo/Hermes local residual is superseded by the
  current peer checkout state.
- **Hephaestus evidence:** its default branch is `master`; head `607ce3f`
  passes CUDA `32083561386`, WGPU `32083561356`, ROCm `32083561357`, and Metal
  `32083561389`. The prior absence-of-run classification is superseded.
- **Coeus evidence:** PR #339 merged its Apollo FFT 0.27 lock resolution at
  default `5adc2d1649bfd2bf68c529b011308e150375810d`; Atlas stages that exact
  gitlink without touching the dirty primary checkout. The former backend
  parity failure at `79f05dfd` is superseded by the merged provider closure.
- **CFDrs evidence:** PR #355 carries provider commit `1bebb5e1`. The
  previous Rust-gate timeout is addressed by caching the normalized parabolic
  inlet profile once per solve. Exact-head run `32197696210` now fails in the
  hosted Clippy job at `cfd-2d/src/solvers/ns_fvm/solver/solve.rs:218` for
  `clippy::if_not_else`; the book-figure job passes. The provider branch needs
  that warning-denied correction before merge; no CFDrs checkout was changed.
- **Aequitas evidence:** PR #35 merged the provider structure cleanup at
  default `260ad10dd5480eef8c82958d1d148199656db59e`; its verify,
  supply-chain, post-merge CI `32198085105`, and Pages
  `32198084983` checks pass, with RecurseML report-only. Atlas advances the
  Aequitas gitlink to the exact merge commit without modifying the provider
  checkout.
- **RITK evidence:** fetched default `9fa4981e` is the docs-only merge of PR
  #176 (`backlog.md` correction). The Atlas gitlink is staged to that exact
  commit; the previously collected CI/Python runs remain attached to `f9d04a79`
  and do not establish the new default head. No run is currently attached to
  `9fa4981e`.
- **Gaia polyline/direction evidence:** Atlas now advances the gitlink to
  merged provider default `dbed97a63434a21b1b9dcd01d634276aaec99e37`, which
  contains the validated `gaia::Polyline` contract and the new
  `UnitSphereDirectionSet` backed by the existing `GeodesicSphere` and Leto
  `UnitVector3`; RITK's TCK/TRX consumers import Gaia's canonical type
  directly. Provider local nextest 972/972, warning-denied Clippy, doctests
  9/9, format, and Rustdoc pass. PR #32 hosted CI `32206596573` and mesh-book
  verification `32206596795` pass; CodeRabbit passes and `recurseml/analysis`
  remains report-only error.
- **Mnemosyne evidence:** PR #62 source head `0022926` passed Rust
  verification, MSRV, Loom, Miri, aarch64, ThreadSanitizer, and CodeRabbit;
  `recurseml/analysis` is report-only. The provider default moved from
  `43cdf047` to `cbccb7ee826b387e4e0ccc4499beb57a88bb51c7` after the first
  exact-head run `32206977029` failed Miri compilation on the missing
  `SEGMENT_SIZE` import. Exact-head run `32208332797` is now in progress for
  the provider's corrected Miri-gate topology; Loom, aarch64, and
  ThreadSanitizer are green while Rust verification and Miri remain
  uncollected. Atlas remains at `64f0d2e` until that exact default-head run
  completes.
- **Hosted recheck:** Aequitas CI `32198085105` and Pages `32198084983` pass
  at `260ad10`; Themis CI `32194584768`, MSRV `32194584736`, and Pages
  `32194583598` pass at `0484a333`. CFDrs run `32197696210` fails only in
  Clippy at the provider source location recorded above.
- **Acceptance:** collect Apollo PR #107's rerun, the corrected CFDrs exact-head
  run, the absent RITK default run classification, Horae PR #19's exact-head
  checks, and Mnemosyne run `32208332797`; then reconcile only verified
  provider heads. The overlay and standalone lock-form gates pass; the current
  exact-head gate is blocked by the unadvanced Mnemosyne default. Preserve
  peer-owned checkout and lane state.
- **Documentation evidence:** the stack-wide link detector passes for all 23
  registered provider books with zero missing files, missing anchors, or read
  failures. Its fixture regression suite passes 43/43 with the intentional
  missing-link case covered.
- **Automation cleanup:** the committed fast Python tier had one collection
  defect because `test_atlas_scattered_containers_classify.py` imported through
  `scripts.*` while `pytest.ini` exposes `scripts` as the module root. The
  import now matches the configured namespace; the fast tier passes 225 tests,
  17 deselected tests, and 74 subtests in 13.75 seconds.
- The committed slow Python/book tier also passes 17/17 in 1.62 seconds;
  documentation helper coverage is green at the delivered root revision.
- **Horae result:** provider lock commit `9cc9fd8` plus PM synchronization
  `aefe641` and evidence-boundary correction `91a020c` pass post-merge CI
  `32202560133` (`verify` and `supply-chain`) and Pages deployment
  `32202559349` at exact default `1ed6a172aa1ef57765c4d07ae740e6c297913567`.
  Local-graph format, locked metadata, both feature configurations, Clippy,
  20/20 Nextest, doctest, rustdoc, and cargo-deny pass; the root gitlink now
  records the merged default. The root-overlay rejection remains a
  development diagnostic rather than standalone proof.
- **Hyperion lock slice:** provider commit `880eb8c` refreshes the clean
  standalone lock to Aequitas `260ad10`, Eunomia `85e590b`, and Proteus
  `f612c99`; hosted `verify` and `supply-chain` pass at exact head
  `880eb8cce28d1e887942fbeb185a1cf4173c776a`, and PR #15 merged at default
  `0156f59f78aba1e3b06d4511ffb1ce30d5c0c6d4`. Local format and locked
  all-feature metadata pass. The root-overlay `cargo check --locked` rejection
  remains a pre-compilation development-overlay diagnostic, so Atlas advances
  only to the verified provider merge commit. Provider-local HYPERION-006
  closeout passed hosted `verify` and `supply-chain` at exact head
  `86486139120243e0b6cae84143d7a914eb51a8a3`; PM-only PR #16 merged at
  default `93157c235d1bfabd88a4720b4a02370ff2a00cc2`.
- **Clean-checkout evidence:** after fast-forwarding the owned Horae and
  Hyperion checkouts to their merged defaults, the fresh
  `--require-clean-checkouts` audit reports 23 findings across 17 peer-owned
  provider checkouts. Head drift is present in Themis, Tyche, Aequitas,
  Moirai, RITK, Hephaestus, Coeus, and Apollo; tracked or untracked dirt is
  present in Themis, Proteus, Consus, Helios, Harmonia, Eunomia, Moirai,
  Melinoe, Leto, Hephaestus, Coeus, Apollo, Hermes, and Iris. RITK also has
  an `apollo-fft 0.26.0` requirement that does not accept the current 0.27.0
  package. No peer checkout was changed.

**Current lane residual:** `python scripts/atlas-lane-audit.py` reports five
violations: Consus has four trees plus a lane outside the canonical root,
Kwavers has four trees with a detached lane, and RITK has four trees. These
are peer coordination state; no lane or checkout was changed by this pass.

**Cache-fork residual:** the fresh provider conformance scan reports one real
Cargo cache fork at `repos/horae/target` (`.rustc_info.json` present). The
configured shared target is `D:\atlas\target`; the repo-local cache is derived
state, not source. Its exact recursive deletion was refused by the shell safety
policy in this pass, so it remains open under ATLAS-CACHE-FORK-055.

## ATLAS-MNEMOSYNE-CONFORMANCE-001 — NUMA bucket helper consolidation [patch]

- **Status:** provider implementation complete at `0022926`; PR #62 merged at
  default `553499056ae37f3aa9f249cc507a0a09e55fd08d`, followed by provider
  TSan documentation commits `9754ebc`, `1c79909`, and `64f0d2e`. The Atlas
  gitlink is advanced to current default
  `64f0d2ebe58e14705ca2345cad2c705f99a6b611`.
- **Scope:** `crates/mnemosyne-arena/src/segment/pool/numa_bucket.rs` and its
  two callers; no allocator algorithm or public API change.
- **Acceptance:** replace the two type-suffixed production bucket helpers with
  one domain-named conversion, preserve NUMA bucket behavior through focused
  value-semantic tests, and reduce Mnemosyne's conformance
  `type_suffixed_fns` count from 2 to 0 without increasing any debt class.
- **Verification:** local format, package Clippy, sanctioned nextest 65/65,
  doctest compilation, warning-free rustdoc, and the provider conformance
  report pass at the exact commit. Hosted checks passed before advancing the
  Atlas gitlink to the provider merge commit.
- **Hosted state:** PR #62 head `0022926` has Rust verification
  `32196541600`, MSRV `32196541558`, Loom, Miri, aarch64, ThreadSanitizer,
  and CodeRabbit passing; `recurseml/analysis` is report-only. The provider
  merge commit is `553499056ae37f3aa9f249cc507a0a09e55fd08d`; the current
  fetched default is `64f0d2ebe58e14705ca2345cad2c705f99a6b611` after the TSan
  and backlog closeout documentation commits.

**Instrument correction, applied before anything else was measured.**
`scripts/atlas-conformance.py:131` classified a file as test code only when a
*path part* matched `tests`/`benches`/`examples`/`fuzz`. `Path.parts` yields
`tests.rs` as a filename, never `tests`, and `split_test_region` only splits on
an *in-file* `#[cfg(test)]` — so every co-located `src/**/tests.rs` sidecar was
scanned as production. Four audits reached that conclusion independently
(consus, moirai, ritk, apollo). Fixed by matching directory parts only plus a
new `declared_cfg_test` check that reads the parent module's
`#[cfg(test)] mod <stem>;` declaration; the baseline was regenerated in the same
change per the generator contract. Effect: stack `unwrap_production`
4713 → 1460 (kwavers 2630 → 259, consus 709 → 334), with the counts moving into
the test-region classes where they belong (`existence_only_assertions`
598 → 807, `sleep_synced_tests` 117 → 132). **Every burn-down target recorded
before this fix was aimed by a broken instrument and must be re-derived.**

**Root checkout repair (2026-08-17):** four Atlas workflows failed before
their gates because the Athena gitlink named an unreachable provider commit
`638ca74f`; the root pointer is repaired to fetched Athena `origin/main`
`bd9346f6`. The nested Athena checkout remains peer-owned and untouched. The
failure class is submodule reachability, not provider implementation evidence.

**Second checkout repair (2026-08-17):** the same recursive checkout audit
reached Gaia and found root gitlink `fa35887e` absent from the provider remote;
Gaia `origin/main` is `9595668`. Atlas repairs the root pointer only. The
nested Gaia checkout is clean but behind its fetched default, so it remains
provider-owned state rather than an Atlas source edit.

## ATLAS-HOSTED-STATE-2026-08-18-2230 — exact-head gate recheck [patch]

- **Themis:** default `d0fcce7a` has MSRV and Pages success, Windows CI
  success, and Ubuntu CI failure at `src/query/platform.rs:55` for Clippy's
  `borrow_as_ptr` pedantic lint. The provider-owned fix is to use the explicit
  raw-pointer form required by the current lint floor; no local checkout edit
  was made because Themis contains peer-owned staged and unstaged work.
- **Themis resolution:** PR #26 merged at provider default `0484a333` after
  its Ubuntu/Windows CI, MSRV, nightly compile-fail, Miri, and CodeRabbit
  checks all passed. Atlas stages only this gitlink advance; the dirty primary
  checkout remains at the prior head and is untouched.
- **Post-merge gate:** Themis default-branch MSRV `32194584736`, CI
  `32194584768`, and Pages `32194583598` pass at `0484a333`.
- **RITK:** current default `f9d04a79` CI `32192759850` and Python CI
  `32192759832` remain queued. The preceding Python run `32184697093` passed
  its Rust, Clippy, Rustfmt, and platform test jobs but failed three
  SimpleITK inverse-displacement parity assertions; this is behavioral
  evidence, not a reason to widen tolerances.
- **RITK source resolution:** the Apollo 0.27 consumer sweep itself is already
  merged as PR #167 at default `f9d04a79`; its Rustfmt, dependency-alignment,
  Clippy, Python wheel, and platform checks all passed. The remaining local
  exact/overlay failure is the stale initialized checkout at `86bd9fba` and
  its old lock, not an unmerged RITK source change.
- **Consus:** Documentation `32184845179` still fails before rustdoc because
  `consus-zarr` declares a missing `s3_rusoto_moirai` benchmark target; the
  current CI run remains queued and Pages success does not close it.
- **Coeus:** Backend parity `32147262055` still fails all provider-contract
  jobs before tests because the locked graph asks for Apollo FFT 0.27 while
  the Apollo revision supplies 0.26. The lock/requirement closure remains
  provider-owned and no compatibility path is added.
- **Hephaestus:** no default-branch Actions run exists in this sweep. The
  absence of a run is an evidence gap, not a passing gate.

## ATLAS-MULTIPHYSICS-ADOPTION-100 — CFDrs/Kwavers/Helios provider adoption and suite closure [major] [arch] — in progress

- **Completed claim (atlas coordinator, 2026-08-21):** exact committed-gitlink
  source mode for `scripts/atlas-multiphysics-audit.py` and its tests is
  implemented and verified. The claimed files were that script, its focused
  test, and this item. Peer-owned source, consumer, and lane checkouts remain
  out of scope.
- **RITK release-workflow closeout (fresh recheck):** PR [#194](https://github.com/ryancinsight/ritk/pull/194)
  merged at `337f0dc5` with merge commit `65bee2c2`. The fetched RITK default
  is `b35c93313c06ea55fffa680a430378dda1df8e41`, exactly matching the Atlas
  gitlink. The hosted connector returned no workflow records for the merge
  SHA, so this closes the merged workflow-only claim but does not assert
  post-merge CI, Pages, or live-release evidence.
- **RITK claim closeout:** `RITK-DOC-GATE-210` is fixed in provider commit
  `9e1c276a`, which adds a warning-denied rustdoc CI job and corrects five
  public-doc/private-link or broken-link defects. Exact workspace rustdoc
  generates 40 targets, focused nextest passes `817/817`, and focused clippy
  passes with `-D warnings`; this increment advances the Atlas `repos/ritk`
  pointer to `9e1c276a`.
- **Horae claim closeout:** clean default `0df563a69693418b267f337fa4bc9dfb7c1aeb1b`
  passes the exact `--all-features` native gate `23/23`. Horae CI already runs
  `mdbook test`, and its Pages workflow enables the shared `mdbook-test` gate.
  The local Windows `mdbook test` invocation stops before chapter assertions
  with `E0461` because mdBook selects GNU rustdoc while the shared stack
  artifacts are MSVC; no Horae source or pointer change is warranted, and the
  hosted Linux book gate remains the configured cross-platform book evidence.
- **Kwavers pointer reconciliation:** the fetched provider default is
  `64b982bdbfc2b7e36f11971947f5bdd8ed59d1f1`, while Atlas still points at
  `b571927442b074fb0622beabdf3f2535dff1951a`. This increment advances only
  the root gitlink to the fetched default; the peer-owned Kwavers checkout is
  dirty on `ff4dc868` and remains untouched.
- **Integration recheck closeout:** root `a1fd1e4` passes the exact-head audit
  for all 22 providers and CFDrs/Kwavers/Helios, the stack overlay check, the
  registry metadata scan (`252` manifests, `0` violations), and the standalone
  lock-form check (`27` locks, one documented in-tree Melinoe fixture
  exemption). The lane audit remains red only for Consus (`3` worktrees) and
  Kwavers (`5` worktrees); no lane was switched, deleted, or overwritten.
- **Live conformance evidence:** the intentional `--worktree` scan remains a
  dirty-tree snapshot, not a reproducible gate. It reports `609` oversized
  files, `675` implementation-bearing manifests, `1,196` production unwraps,
  `518` allow sites, `803` existence-only assertions, and `4` excess-worktree
  sites; these counts are peer-owned ratchet debt and are not silently reset
  by the Atlas coordinator.
- **Checkout ownership boundary:** Gaia's apparently clean checkout is in an
  interactive rebase on `cascade/provider-042`; switching it to the recorded
  root gitlink was refused and no rebase state was touched.
- **Hosted residual recheck (2026-08-20):** [CFDrs PR #357](https://github.com/ryancinsight/CFDrs/pull/357)
  has passing Rust and figure jobs in run `32225060679`; only its RecurseML
  analyzer reports an error. [Apollo PR #107](https://github.com/ryancinsight/apollo/pull/107)
  remains red: benchmark run `32217561595` and Rust run `32217561627` fail;
  the independent benchmark audit localizes the regression to the four
  const twiddle-cache initializers in `twiddle.rs:26-29`, with the required
  repair being a single-variable revert in
  `crates/apollo-fft/src/application/execution/kernel/mixed_radix/caches/twiddle.rs:26-29`
  with the benchmark instrument unchanged.
- **Hosted completion boundaries:** [Helios PR #67](https://github.com/ryancinsight/helios/pull/67)
  is draft but its Rust, Python, benchmark, and book-build jobs pass in runs
  `32284640806` and `32284641544`; Pages deployment is skipped. [RITK PR #190](https://github.com/ryancinsight/ritk/pull/190)
  is draft with Rust, Python, wheel, and book-build gates passing in runs
  `32297172555` and `32297173130`; Pages deployment is skipped. Hermes PR #55
  has green substantive gates in `32255618310` but remains draft; RecurseML
  errors remain analyzer-only. Kwavers PR #417 has a fully green substantive
  matrix in runs `32316400677`, `32316400868`, `32316401011`, and
  `32316401183`, with Pages deployment skipped; PRs #420, #421, and #422 have
  pending matrices and are not completion evidence.
- **RITK release-workflow slice:** provider commit `337f0dc5` on branch
  `ci/ritk-release-timeout` adds `timeout-minutes: 30` to the wheel-build job
  and `timeout-minutes: 10` to the trusted PyPI publish job. PR #194 is draft;
  YAML parsing and the local conformance scan pass (`workflow_missing_timeout`
  `1 -> 0`), while its Rust, Rustdoc, Python, wheel, and dependency-alignment
  checks are pending. RecurseML reports an analyzer error only. Atlas remains
  at RITK `9e1c276a` until the provider default advances; no hosted success is
  inferred from pending checks.
- **Kwavers PR #418 closeout:** the ADR and convex-array rasterizer seam merged
  at provider default `64b982bdbfc2b7e36f11971947f5bdd8ed59d1f1`. The fresh
  default contains ADR 112, its index row, and the Aequitas `Degree` surface;
  no stale architecture record remains in the provider default. Atlas advances
  its gitlink in this integration increment while the primary checkout remains
  dirty on peer branch `feat/aperture-sir-seam` and is not switched.
- **Kwavers PR #417 closeout:** the typed `Degree` adoption merged at provider
  default `b571927442b074fb0622beabdf3f2535dff1951a`. Its Rust, Python-wheel,
  benchmark, feature, Miri, security, documentation, k-Wave, and architecture
  checks passed; Pages deployment was skipped and RecurseML remained
  report-only. The Atlas pointer advances to this merge commit in the
  integration increment below; the primary Kwavers checkout remains dirty on
  peer branch `feat/aperture-sir-seam` and is not switched.
- **Kwavers post-merge integration closeout:** Atlas root `a00a0d1` advances
  the Kwavers pointer to `b5719274`; exact provider/integrator heads, the stack
  overlay, registry metadata, and 27 standalone lock forms pass. The lane
  audit remains limited to Consus (3 trees) and Kwavers (5 trees), with all
  peer-owned lanes preserved.
- **CFDrs PR #357 closeout:** the hosted-closure documentation increment merged
  at provider default `aa54f5cdcdc4e406df0c60ea6c3cb507e968fc97`. The Rust and
  figure jobs passed at the documented exact source head; Pages and PyPI remain
  explicitly open. The Atlas pointer advances to this merge commit in the
  integration increment below; the primary CFDrs checkout remains dirty on
  peer branch `codex/cfdrs-tvd-test-integration` and is not switched.
- **CFDrs post-merge integration closeout:** Atlas root `c721c3e` advances the
  CFDrs pointer to `aa54f5cd`; exact provider/integrator heads, the stack
  overlay, registry metadata, and 27 standalone lock forms pass. The open
  Pages/PyPI items remain provider-owned delivery work and are not inferred
  from this documentation merge.
- **Aequitas claim closeout:** dimensional-law tests were split into named
  angle and complex-value modules in provider commit `c908af1`; the focused
  nextest gate passes `40/40`, clippy passes with `-D warnings`, and Atlas
  records the pointer in commit `84eb033`.
- **RITK claim reconciliation:** `ATLAS-RITK-TRANSFORM-DIRECTION-081` was
  already fixed in provider commit `3aa73ba0`, an ancestor of RITK default
  `ebf2f499`. The focused `ritk-filter`/`ritk-diffusion` gate passes
  `1,284/1,284` tests (11 skipped) and clippy with `-D warnings`; oblique grid,
  inverse-displacement, and marching-cubes regressions are present.
  `FodVolume` intentionally documents an axis-aligned frame contract, so no
  RITK source change was warranted.

The active product boundary is a multiphysics simulation suite built from the
CFDrs, Kwavers, and Helios integrators. The provider set is `horae`,
`hyperion`, `harmonia`, `themis`, `tyche`, `proteus`, `mnemosyne`, `consus`,
`helios`, `aequitas`, `asclepius`, `eunomia`, `moirai`, `ritk`, `melinoe`,
`leto`, `hephaestus`, `coeus`, `apollo`, `gaia`, `hermes`, and `iris`.
`tyche` is the canonical spelling; `tychee` is retained only as a historical
alias in audit text. Atlas owns the provider graph, exact gitlinks, overlay,
cross-repository gates, and integration documentation; each member owns its
source implementation and provider-local tests.

- **Current slice:** Helios PR #59 carries the caller-side `mdbook test`
  enablement, CFDrs PR #347 carries the pressure-cache, hemolysis-error, and
  book-fence slices,
  and Apollo merged default `ed6d6905` carries the provider-owned public
  `PlanScratch` bound required by CFDrs. Helios PR #59 is merged at default
  `679402ae` with Rust, Python, benchmark, and book gates passing; CFDrs PR #347
  merged provider source head `f7bc741184a000338a5f4d4edf261a6dcfa266c8` into
  default as `84499e957d3d0c8ce50b9573185a1f55885f38e2`. Exact-head Rust run
  `32046526277` passes format, check, ordinary tests, numerical fidelity (14/14,
  3036 skipped, 8 slow; 247.309 s), and doctests; figure job `95435610232` and
  book build `95435671291` pass. Post-merge Pages run `32047447199` passes build
  and deployment. Post-merge Rust run `32047446607` passes format, check, and
  ordinary tests but fails numerical fidelity with 12/14 passed and timeouts in
  `microventuri_35um_case_produces_converged_informative_2d_result` and
  `cross_fidelity_trifurcation_dominance` at 30.006 s. The preceding Rust run failed before checkout on a
  GitHub 503/429 action-download response (`32043533301`, job `95426903063`).
  The preceding Pages run (`32043533628`, job `95426905897`) reached the
  package build and exposed the missing `fontconfig.pc` system dependency.
  Atlas shared workflow `bb505e5` now installs the required headers and the
  CFDrs caller pins that commit. New exact-head CI and Pages runs
  `32044071453` and `32044071732` were infrastructure-red. PM-only and
  source-correctness heads were superseded by `f7bc7411`; Rust job
  `95430179027` and Pages job `95430210781` in runs `32044765872` and
  `32044766414` failed before checkout on codeload 503/429. The figure job
  `95430179037` passed; the Pages retry `95430855675` passed the prior exact
  head. CodeRabbit and all required PR checks are successful; the PR is merged.
  The Atlas gitlink sweep below is complete for moving Mnemosyne,
  Aequitas, Leto, and CFDrs defaults;
  while Helios is already at merged default `679402ae`. Kwavers PR #402 carries
  the current provider FDTD and uninitialized-GPU-resource correction at exact
  source head `e1648019`; its hosted matrix is pending. PR #386 remains historical
  evidence for the earlier multi-field field-preservation closure, not current
  exact-head proof. The
  existing CFDrs decision to remove its newly introduced legacy-Clippy step is
  a documented gate-boundary decision, not a lint-debt closure; the remaining
  lint floor stays in the Atlas conformance ratchet.

**Moving-default reconciliation (2026-08-17):** Atlas is advancing fourteen
fetched provider defaults in the current root commit: Themis `f61173bc`, Tyche
`5eeaba95`, Proteus `cb70021b`, Mnemosyne `d1144f74`, Consus `2dcf05a8`,
Helios `39a24992`, Hermes `dd4cb129`, Aequitas `c74b662c`, Asclepius
`5de8a48c`, Moirai `3d5d4c66`, RITK `ae23d4b2`, Coeus `b14777d8`, Apollo
`df8999f9`, and Iris `da210d2f`. This pointer evidence is separate from
provider hosted-gate evidence. The nested primary checkouts remain peer-owned.
The CFDrs follow-up is pushed at `e6633964` on
`codex/cfdrs-runtime-residual` and is carried by PR #348. Its final local
value-semantic gates pass; the exact-head hosted Rust and Pages gates remain
the delivery gate.

**Live exact-head sweep (2026-08-17):** fetched provider defaults advanced
Mnemosyne to `924cdcce`, Aequitas to `c74b662c`, and Leto to `d966e32c`. Their
root gitlinks are advanced to those fetched default heads; the primary
checkouts remain peer-owned and may be on separate branches with dirty
lockfiles or artifacts. Only the root gitlinks are advanced here. The
the exact requested 20-provider audit, lane audit, and nine conformance tests
pass after this pointer sweep.

**Expanded audit refresh (2026-08-18):** the active product scope is the
22-provider set named above, not the earlier twenty-provider snapshot. The
Atlas structural audit now includes Harmonia and the corrected Tyche spelling
and checks active registration, fetched-default gitlinks, and exact-head
workers. Apollo PR #104 has merged into provider default `d585e0f5`; the
provider package is now `apollo-fft 0.27.0`. The latest root source head
`c049d26` passes hosted Atlas conformance run `32159744862`, while hosted
overlay run `32159744891` reports the peer-owned consumer boundary: CFDrs
requires and locks Apollo `0.26.0`, and Kwavers locks `0.26.0`, against the
committed provider `0.27.0`. The standalone exact-head/version guard reports
one corresponding RITK manifest residual. The re-open trigger is the
consumer-side Apollo requirement/lock sweep followed by its affected hosted
matrix; no compatibility path is permitted.

The CFDrs backward-step slice is at provider head `7b9673ef`. Local focused
and full `cfd-2d` gates pass, including 585/585 tests. Hosted run `32143999878`
passes the book-figure job but its numerical-fidelity job times out in
`test_benchmark_run_integration` and `cross_fidelity_trifurcation_dominance`
at the committed 30-second slow bound. The workloads and budgets remain
unchanged; the next CFDrs increment is a production-path root-cause slice,
not a test or timeout relaxation.

**Post-gate recheck (2026-08-18):** at root commit `3669fff`, the full
`atlas-provider-integration-audit.py --exact-heads --provider-set atlas-22`
passes structural registration, fetched-default gitlinks, exact-head workers,
and its live requested-provider coherence scope. The standalone version guard
also reports `defect_count: 0`. This does not close the separate Helios lock
drift from the overlay check, nor any hosted provider release or Pages gate.

**Gitlink reconciliation (2026-08-19):** root commit `95a3f77` advances the
Mnemosyne gitlink to fetched `origin/main` `d00f139e` and the Consus gitlink to
fetched `origin/main` `2e0df9f8`. The exact-head provider audit passes for all
22 registered providers and the CFDrs/Kwavers/Helios integrator pointers;
`atlas-stack-overlay.py check` and `atlas-lock-form.py check` also pass. The
Mnemosyne and Consus primary checkouts retain peer-owned dirty work, so this
pointer-only increment makes no provider-local source, lockfile, or hosted-gate
claim.

**Clean-checkout proof (2026-08-18):** the provider audit now has an opt-in
`--require-clean-checkouts` gate that compares each initialized checkout's HEAD
to the committed gitlink and rejects tracked or untracked dirt. The gate is
implemented and regression-tested, but the current shared tree fails it on
peer-owned state: checkout-head drift is present in Tyche, Helios, Moirai,
RITK, Hephaestus, Apollo, and Hermes; dirty checkouts include Themis, Tyche,
Proteus, Mnemosyne, Helios, Harmonia, Aequitas, Asclepius, Eunomia, Moirai,
RITK, Melinoe, Leto, Hephaestus, Coeus, Apollo, Hermes, and Iris. This is the
clean-revision evidence boundary, not permission to discard peer work. The
re-open trigger is a clean coordinated checkout followed by the same gate.

The release, PyO3/PyPI, crates.io, mdBook/Pages, comparative-test, and
provider-adoption audits are dispatched as independent read-only work. Their
returned file-level findings become separate vertical items before any
consumer implementation changes are made.

**Delivery-surface findings (2026-08-18):** the audit returned no P0 but
identified P1 gaps that now have explicit owners and dependency order:
Helios' enabled `mdbook test` contradicts its recorded failing snippets;
CFDrs and Helios lack complete wheel/PyPI gates; Kwavers' k-wave comparator is
not reproducible from the checkout; and locked `cargo tree` is blocked by the
shared overlay attempting to rewrite peer-owned locks. P2 gaps include
incomplete binding metadata, Kwavers ABI3/path drift, import-only wheel smoke,
stale CFDrs/Kwavers Pages path filters, and incomplete recursive figure SSOT
checks. The next slices repair these at their owning repositories; Atlas does
not claim registry, wheel, or live Pages evidence from a read-only audit.

**Provider/Python audit refresh (2026-08-20):** committed manifests show direct
provider edges in CFDrs, Kwavers, and Helios, but adoption is not source-closed:
Kwavers retains direct `wgpu` edges in `crates/kwavers-analysis` and
`crates/kwavers-gpu`; RITK retains `crates/ritk-wgpu-compat`; and CFDrs still
owns the stateful Anderson/Aitken wrapper in
`crates/cfd-2d/src/network/coupled.rs`. The static PyO3 audit finds strong GIL
release in RITK, Helios, Coeus, Apollo, Moirai, and Leto, but no release sites
in CFDrs and only one in Consus, with incomplete Kwavers coverage. Coeus,
Hephaestus, and Leto lack complete `pyproject.toml`/typing metadata, and no
PyPI upload or post-publication install smoke is proven. These are provider-
owned implementation items; no compatibility shim or registry claim is added.

**Multiphysics boundary audit (2026-08-21):** three independent read-only
audits now provide the acceptance-driving findings for integrator closure.
CFDrs still converts coupled-network solve failure to default diagnostics in
`crates/cfd-2d/src/network/coupled.rs`, silently downgrades requested GPU
Poisson work in `crates/cfd-2d/src/solvers/accelerated.rs`, installs a
process-wide validation allocator, and runs domain calculations in its PyO3
surface without GIL release or complete input validation. Its backward-step
validation checks residual magnitude without the solver's explicit convergence
flag. These are correctness and operational-integrity defects.

Kwavers comparative tests use empty/default sources in several solver cases;
the Python comparator can fall back to the first successful simulator and
truncate mismatched arrays, while k-Wave tests are opt-in/skipped and cached
parity artifacts lack provider/oracle provenance. Its comparative FDTD path
computes but does not use the CFL timestep, and the Python array boundary copies
inputs and outputs despite a zero-copy claim. A parity claim remains blocked
until a fresh nonzero-source homogeneous IVP gate uses an analytical
d'Alembert oracle and a mandatory independent k-wave-python run.

Harmonia's typed `FieldEnvelope`/`GridGeometry` implementation exists only at
feature branch `5b1bc28792347b660ce653b8946a7c0a618cc649`; the committed
default still exchanges raw slices. Helios loaders multiply untrusted DICOM
and HDF5 dimensions before allocation, GPU tests are ignored or adapter-skipped
by default, and its Python package lacks `py.typed`/stub artifacts. Themis has
no confirmed soundness defect in the inspected implementation, but its local
checkout is stale relative to `origin/main` and needs current-default safety
evidence.

The root `scripts/atlas-multiphysics-audit.py` records checkout revision,
committed gitlink, dirty state, direct provider edges, PyO3/GIL evidence,
`py.typed`/`.pyi` typing surfaces, book fences, analytical/differential
markers, performance/memory markers, and unsafe-code policy. At Atlas
`474adbe`, it requires and confirms both the existing `tyche-core` edge and
`tyche_core` source consumption in CFDrs, Helios, and Kwavers. It finds no
CFDrs GIL-release site or source
typing artifacts; no source typing artifacts in Helios or Kwavers; Kwavers's
direct `wgpu` edge; and Helios/Kwavers runnable-book gaps. Blocking mode also
rejects the dirty,
gitlink-drifted provider checkouts; `--require-evidence` fails as intended.
No provider pointer advances until fixes merge to default and exact-head
hosted, book, wheel, and Pages evidence is terminal.

The Tyche edge is real source consumption, not an unused manifest entry:
CFDrs imports `tyche_core` in `cfd-optim` sampling, Helios imports
`Seed`/`SplitMix64`/`StandardNormal` in imaging noise, and Kwavers imports
Tyche designs, seeds, moments, and conformal calibration in its analysis and
geometry sampling modules. These references were checked in the live
provider trees; they do not substitute for clean exact-head or hosted proof.

The full Atlas-22 structural audit at this integration revision reports
`22/22` active providers and zero issues, including Harmonia, Gaia, and the
Tyche canonicalization. The stack overlay remains aligned after restoring
only derived lockfile churn; no provider source or gitlink changed.

The checker’s focused suite passes `7/7`; the complete root Python suite at
Atlas `158aeca` passes `233/233` in `7.5 s`. The requested-provider structural
audit remains `20/20` with zero issues, the development overlay reports
aligned requirements and locks, and registry metadata reports `253` manifests,
zero violations, and zero unverified entries.

**Tyche standalone gate (2026-08-21):** the clean checkout at exact gitlink
`10410f2de1ce1529ecbff50fa740b23a1c8f77b9` passes its pinned Rust `1.97.0`
format, locked `tyche-core` check, workspace all-target/all-feature Clippy
with `-D warnings`, Nextest `51/51`, doctests (`18/18` executed doctests),
warning-denied workspace docs, the `reproducible_study` example, and every
single-iteration `counter_sampling` benchmark case. The commands ran from
outside the Atlas configuration tree with the shared target directory, so the
committed lock was not rewritten; Tyche remains clean. This is local provider
evidence only; hosted CI, Pages, and the fetched-default pointer still remain
separate delivery gates. Direct local `mdbook test` is not counted as green:
without staged artifacts it reports `E0463`, and the shared target contains
multiple historical rlibs that produce `E0464`/`E0460` under local staging.
The reusable Pages workflow's fresh-runner staging path is therefore the
authoritative Tyche book gate until a clean isolated runner result is collected.

The intentional live conformance scan on the dirty shared tree reports 19
ratchet increases and 25 decreases. The increases are confined to active
peer-owned scopes: CFDrs (oversized files, allow sites, existence-only
assertions, commented-out code, and one excess worktree), Consus (oversized
files, manifest implementation, production unwraps, allow sites,
existence-only assertions, type-suffixed functions, and orphan modules),
Kwavers (one target fork and one excess worktree), Leto (one excess
worktree), Moirai (SeqCst sites), and RITK (manifest implementation,
type-suffixed functions, and commented-out code). No baseline was regenerated;
these counts require clean exact-head provider attribution before any source
repair or ratchet update.

**Dependency-ordered re-open triggers:** (1) collect Harmonia PR #9 at its
merged default, then migrate CFDrs to the native typed field and delete its
superseded wrapper; (2) implement the Kwavers reproducible IVP parity gate and
fresh-oracle provenance; (3) harden Helios dimension/resource boundaries;
(4) complete PyO3 GIL, validation, typing, and installed-wheel evidence; and
(5) rerun the full Atlas exact-head, overlay, lock, book, figure, performance,
memory, and hosted Pages acceptance oracle.

**Book/figure audit refresh (2026-08-20):** strict link validation scans all
25 current books with zero missing files, anchors, or reads; `mdbook build`
completes for all 25. The executable-gate inventory is 19 shared callers and
six residuals: Consus has no gate; Gaia, Helios, and Kwavers have vacuous
or non-executable coverage; and Hephaestus and RITK have no gate. Themis is
already gated; Leto has a committed book and Pages caller. Direct local
`mdbook test` on the un-staged repositories fails with missing `--extern`
crates, so it is not treated as provider sample proof; the staged package
workflow and hosted runs remain authoritative.

- **Provider-adoption slice:** audit every integrator edge for direct use of
  the owning provider API, deletion of superseded local wrappers, and no
  silent CPU/GPU, storage, or scheduler fallback. File provider capability
  gaps upstream before changing a consumer.
- **Physics-contract slice:** exercise typed time (`horae`), quantities
  (`aequitas`/`eunomia`), material and optical laws (`proteus`/`hyperion`),
  coupling (`harmonia`), storage (`consus`), geometry (`gaia`), imaging
  (`ritk`), biological response (`asclepius`), and execution/accelerator
  paths (`mnemosyne`/`moirai`/`themis`/`melinoe`/`hermes`/`leto`/`hephaestus`/
  `apollo`/`coeus`/`iris`) through value-semantic scenarios in the three
  integrators. A green build without an analytical or differential oracle is
  insufficient.
- **Performance and memory slice:** establish controlled baselines before
  claiming speed, allocation, or memory improvements; inspect allocation
  counts, shared-cache growth, buffer reuse, zero-copy boundaries, and
  criterion confidence intervals. Optimize production paths only; preserve
  workload sizes and test budgets.
- **Documentation slice:** keep each domain book's chapter map, examples,
  figures, and provider links synchronized. Enable or repair `mdbook test`
  only where the committed samples compile, and verify the final Pages
  artifact and live deployment at the same revision as the source.

**Atlas-owned delivery increment (2026-08-18):** the reusable
`.github/workflows/python-wheels.yml` workflow now accepts an explicit
provider-owned pytest path and runs that suite after wheel installation in
importlib mode. The default pytest pin is `8.4.2`, which supports the
workflow's Python 3.9 floor; providers must still opt in with a bounded,
value-semantic test path. This adds the shared gate only; it does not claim a
provider's PyPI publisher or hosted result until its caller is updated and a
same-head run passes.

**Harmonia capability boundary (2026-08-18):** direct CFDrs adoption remains
open because `repos/CFDrs/crates/cfd-2d/src/network/coupled.rs` preserves a
stateful Anderson/Aitken resistance-mixing contract. Harmonia PR #6 merged at
provider default `b98d3f4` and now provides the mutable pair-level
`Relaxation<T>` seam, atomic fixed/full policies, provider-owned
`AitkenRelaxation<T>`, ADR 0002/0003, analytical and transactional coverage,
and hosted verify, supply-chain, and book-build evidence; RecurseML remains
report-only. Atlas advanced the root gitlink to `b98d3f4`. Adding a consumer
adapter or fixed-relaxation fallback would violate provider-first ownership.

**Harmonia conformance closure (2026-08-18):**
`ATLAS-HARMONIA-CONFORMANCE-001` is complete. PR #7 merged at provider
default `3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb` and Atlas root commit
`c049d26` advances the gitlink without touching the dirty primary checkout.
The clean provider-lane conformance scan reports zero across all 27 classes.
Hosted run `32159533930` passes verify `95784806220` and supply-chain
`95784806422`; RecurseML remains report-only. The direct CFDrs consumer
migration remains the next provider-first slice.
The next slice is direct CFDrs integration and deletion of the superseded
local wrapper. The primary Harmonia checkout retains peer-owned
workflow/book/example/lockfile dirt.

**ATLAS-HARMONIA-AITKEN-001 — provider-owned stateful relaxation [minor] [arch]**
**Status:** complete; **owner:** atlas coordinator; **claimed scope:**
`repos/harmonia/src/relaxation/aitken.rs`, the Harmonia relaxation tests and
ADR index/record, and the relaxation book chapter. The provider must own the
input-sensitive Aitken policy used by the CFDrs pair contract, preserve native
scalar precision, validate dimensions and finite state transactionally, and
provide analytical and differential evidence. The CFDrs wrapper remains out
of scope for this claim and is deleted only in the following consumer slice
after the provider contract is merged and integrated. Acceptance is provider
local locked check, warning-denied Clippy, Nextest, doctest, Rustdoc, book
build, and hosted verification at the exact provider head; no fallback,
adapter, or workload relaxation is permitted. The provider contract remains
delivered at merged default `b98d3f4`; conformance cleanup is now merged at
`3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb`, and the following CFDrs consumer
item owns the remaining wrapper deletion.

**Provider implementation (2026-08-18):** Harmonia commit `584e961` merged via
PR #6 at provider default `b98d3f41d640b3a79df125ef1b3ff786156c5dd3`. The source
slice adds `AitkenRelaxation<T>` with native `RealField` arithmetic,
transactional pair updates, typed configuration/value errors, reusable state,
ADR 0003, and synchronized book/README claims. Local locked all-target check,
warning-denied Clippy, full Nextest 24/24, focused Aitken 7/7, doctest 1/1,
Rustdoc, runnable example, and mdBook build pass. Local `mdbook test` cannot
resolve the four staged dependency rlibs; the provider workflow supplies those
paths explicitly, so this is an environment limitation rather than a changed
gate. Hosted verify, supply-chain, and book checks pass at the exact head;
RecurseML is an analyzer error and remains report-only. Atlas first advanced
the implementation gitlink to `b98d3f4`; the subsequent conformance cleanup
merged at `3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb`.

**Post-merge exact-head recheck (2026-08-18):** Atlas root `c049d26` passes
the 22-provider structural exact-head audit with Harmonia at merged default
`3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb`. The full exact-head audit and
standalone version guard each report exactly one peer-owned residual: RITK's dirty
`crates/ritk-filter/Cargo.toml` requires `apollo-fft 0.26.0`, while the current
provider package is `0.27.0`. The RITK consumer migration remains outside this
slice; no dirty manifest or lockfile is altered here. Hosted Atlas conformance
run `32159744862` passes; overlay run `32159744891` fails on the peer-owned
CFDrs requirement and CFDrs/Kwavers `Cargo.lock` pins at `0.26.0`.

**Latest hosted-state recheck (2026-08-18):** Apollo PR #104 is merged at
default `d585e0f5` with Rust/Python checks green and benchmark run `32140805200`
failed; Helios PR #65 is merged at default `aa7a4fa` with Rust/Python/book
checks green and its benchmark check still in progress; CFDrs PR #349 is open
at `3a03a222` with hosted run `32152884477` queued; and Kwavers PR #402 remains
open with its complete matrix failed or cancelled despite passing benchmark
smoke. The Atlas structural exact-head audit is green, but full exact-head
coherence and the version guard still report the peer-owned RITK
`apollo-fft 0.26.0` requirement against provider `0.27.0`; the hosted overlay
also reports CFDrs's `0.26.0` requirement and CFDrs/Kwavers `Cargo.lock` pins
against that provider. These are delivery residuals, not reasons to alter
workloads, budgets, or consumer contracts.

**Acceptance oracle:** the structural provider audit reports all 22 named
providers present and active; the exact-head audit passes on a clean checkout;
the generated overlay and locked dependency graph pass; CFDrs, Kwavers, and
Helios provider-consumer gates pass at their merged default heads; conformance
ratchets do not regress (including the corrected benchmark-target classifier);
the focused multiphysics scenarios pass analytical/differential checks; the
applicable performance and memory evidence is recorded without unsupported
claims; and the provider/integrator books build, test, deploy, and resolve
their live Pages URLs. Residual external or peer-owned work remains an
explicit board item with its exact blocker and re-open trigger.

### Provider ratchet closures completed in this increment

- `ATLAS-CONSUS-UNWRAP-099`: Consus source `a9a56ad` and PM closure
  `087f810`; the provider scan returns `unwrap_production=383` without a
  baseline edit. Default/no-default locked Nextest passes 2553/2553 and
  2031/2031; hosted CI `32020339446`, Documentation `32020339452`, and Pages
  `32020338335` pass at the exact source head.
- `ATLAS-LETO-CONTRACT-100`: Leto source `6463f4a` and PM closure `e04fdc7`;
  the provider scan returns `existence_only_assertions=9` without a baseline
  edit. Focused locked Nextest passes 550/550; hosted CI `32021076930` and
  Pages `32021074899` pass at the exact source head.
- `ATLAS-CFDRS-CONFORMANCE-101`: CFDrs source `e9c84bf6` and PM closure
  `38bdbeb9`; the provider scan returns baseline
  `existence_only_assertions=137` and `tag_pinned_actions=0`. Locked package
  check, focused locked Nextest 166/166, doctests, and hosted CI
  `32022469516` pass at the exact source head. The Atlas gitlink is advanced
  to the PM closure commit; provider-wide strict Clippy debt remains explicitly
  recorded in the provider PM artifacts.

Dependencies: `ATLAS-COEUS-LINT-RATCHET-097`,
`ATLAS-CONFORMANCE-BENCH-099`, `ATLAS-PUBLISH-001-BOOK-MDBOOK-TEST-001`,
`ATLAS-OVERLAY-005`. This item is the parent audit; its vertical slices close
independently with their own evidence.

**ATLAS-COEUS-LINT-RATCHET-097 takeover:** Atlas session owns the clean lane
`D:/atlas/worktrees/coeus-layernorm-shape`. The prior lane claim is stale: its
last commit is `66bf4897` at 2026-08-16 22:11 -0400 and no newer board update
exists; the peer-dirty primary Coeus checkout remains excluded.

The takeover audit found the claimed lint work already merged upstream: Coeus
PR #334 is at default `a8ea12eb`, production `allow_sites=0`, and hosted
Backend parity run `31989331059` passes. The lane is released without source
edits.

**Coeus PR #346 merged 2026-08-26 at `dbbdfc82ad06b5b0fb20db0719215ce89fb20f33`:
clippy backlog cleared, gate now denies.** 41 outstanding clippy warnings
across the Coeus workspace are gone; the Lint and documentation step now uses
`-D warnings`. Bulk: 31 `.get(0)` → `.first()` across 23 files via
`clippy --fix` (identical in meaning). Rest: three deeply nested return
tuples now have type aliases (the linalg one earns it — the fourth tensor
is the permutation carrying each CSR slot back to the COO entry it came
from, and `(Tensor, Tensor, Tensor, Tensor)` said none of that);
`collect_graph`'s inner `traverse` threaded eight `&mut` accumulators through
recursion, now a `Traversal` struct; five loops indexed over a range derived
from that slice's own length, now direct iteration; three expired
`#[expect]`s removed (one turned out to still be load-bearing — that loop is
fixed rather than re-suppressed). 78 `#[expect]` sites still cite
`ATLAS-COEUS-LINT-RATCHET-097` (67 `too_many_arguments`); they stay tracked.
A *new* diagnostic now fails the build instead of joining a pile. Local
verification: 1130 tests pass. Hosted: all 7 real checks pass (CUDA 17m38s,
Metal 8m10s, ROCm 8m29s, WGPU 24m50s, Format 21s, Lint and documentation
1m24s, Lockfile integrity 33s, Tests 25m2s, CodeRabbit completed);
`recurseml/analysis` is the always-report-only error. Atlas gitlink advanced
`b3b1208e` → `dbbdfc82a` (commit `289bb05db`).

### Current residuals from the 2026-08-16 provider-consumer audit

#### ATLAS-MNEMOSYNE-CONFORMANCE-101 — Close exact-head assertion ratchet [patch, closed 2026-08-17]

The NUMA binding test's fifth `is_ok()` assertion was replaced with an exact
`Ok(())` assertion in provider commit `30126aa`, merged at default
`39d76d2`. Hosted Rust verification, Loom, and Miri (Stacked and Tree Borrows)
passed in run `32024295467`. Provider PM closure `f06c8f9` merged at
`26ea626`; the Atlas gitlink advances to that PM closure. The provider scan
baseline is now four existence-only assertions. The local locked check was
blocked by the shared Atlas overlay resolving patches to the peer-dirty
primary checkout; hosted verification is the compilation and behavior gate.

#### ATLAS-CFDRS-NUMERICAL-FIDELITY-101 — hosted resource contention [patch] — closed

CFDrs PR #344 was rebased onto the newer default branch after GitHub reported
the previous branch as dirty. The forward fix retained every fidelity case
and assertion while splitting the remaining Venturi 1D↔2D and 1D↔3D
contracts; the 30-second/60-second budgets and workloads were unchanged. The
workflow lock-normalization fix made the materialized path-dependency graph
reproducible. Exact-head run `31994843367` passed format, locked workspace,
nextest, numerical fidelity, doctests, and book figures. The PR merged at
`2d9e505a2bb753925f1b3900795e16ac3247a6b2`, and Atlas commit `03de90a`
advances `repos/CFDrs` to that default head. The local locked gate remains
blocked by the peer-dirty Mnemosyne compile error at
`crates/mnemosyne-core/src/memory_diagnostics.rs:96`, not by the merged CFDrs
change.

#### ATLAS-HELIOS-DICOM-GEOMETRY-103 — required geometry defaults [major] — closed 2026-08-17

`repos/helios/crates/helios-domain/src/dicom.rs:121-132` substitutes unit
spacing and zero origin when `PixelSpacing` or `ImagePositionPatient` is
missing. The loader documentation at `:275-280` simultaneously describes
those attributes as required-error inputs while documenting the defaults.
`ImageOrientationPatient` follows the same identity-default contract. The
acceptance oracle is a typed error for each missing or malformed required
geometry attribute plus negative fixture coverage through Helios' DICOM gate;
RITK remains the sole DICOM parser/decoder owner. The clean integration lane
implements the typed rejection at Helios commit
`67f0d60f2ec543dc630ce94d2a1698ddd9e66f54`; local DICOM nextest passes 45/45,
doctests pass, and warning-denied Clippy passes. The counterbalanced benchmark
rerun in exact-head hosted run `31990847118` passed, as did the Rust workspace
and Python bindings. PR #57 merged as `7fddf789`; Atlas advances that merged
default gitlink. The peer-dirty primary checkout remains untouched.

#### ATLAS-KWAVERS-HEPHAESTUS-VIS-104 — GPU ownership closure [arch] — closed 2026-08-18

Kwavers still constructs raw `wgpu` pipelines in
`crates/kwavers-gpu/src/beamforming/three_dimensional/provider.rs` and keeps
raw-WGPU visualization state in `crates/kwavers-analysis/src/visualization`.
The earlier bounded visualization subfinding is recorded at Kwavers commit
`40dac165e` and PR #386: field counts are validated, GPU compositing receives
every field, CPU diagnostics process every field, and multi-field rendering
without transparency is rejected. The current fetched default `6075940ce`
still has a separate initialization defect: PR #402 at source head
`b275b7115` now returns `SystemError::FeatureNotAvailable` when the renderer
and data pipeline are absent. The feature-enabled hosted matrix is pending;
the shared Atlas overlay prevents local compilation before the package gate
because its peer Asclepius checkout still requires `aequitas ^0.1.0` while the
current provider graph is `0.2.0`. The acceptance oracle still requires a
complete provider-owned execution path with explicit failure for unavailable
capability and no consumer-owned raw-WGPU kernel ownership.

The exact fetched-head audit at Kwavers `6075940ce` found two additional
consumer-contract residuals. `kwavers-gpu/src/validation/gpu_cpu_equivalence/
runner/mod.rs:100-110` returns a typed `FeatureNotAvailable` because the GPU
runner still has no provider-generic Leto/Hephaestus FDTD implementation; its
CPU-vs-CPU comparison is correctly rejected rather than reported as parity.
`kwavers-analysis/src/visualization/engine/mod.rs:181-217` had no error or
fallback arm when the `gpu-visualization` feature was enabled but the renderer
and pipeline were not initialized, so `render_multi_field` could return
`Ok(())` without rendering. This correctness defect is addressed by PR #402;
its required hosted feature gate is the re-open/close decision. The FDTD item
remains provider capability work and must not be replaced by an f64 adapter or
CPU-vs-CPU comparison.

#### ATLAS-KWAVERS-FDTD-107 — provider-generic FDTD equivalence [major] — closed 2026-08-18

The acceptance oracle is a real Leto/Hephaestus FDTD execution path selected
through the provider seam, a CPU differential comparison with a derived
reduction tolerance, and negative coverage for unavailable hardware. The
current explicit-unavailable result is historical evidence of the missing
capability. Hephaestus now owns the provider contract and kernel at merged
default `607ce3feb2e0ed1d907d3e0172e23377851e71d8`; Kwavers default `6075940c`
still has the pre-cutover consumer-owned raw-WGPU FDTD code at
`crates/kwavers-gpu/src/gpu/fdtd.rs`. No f64-only adapter, CPU fallback, or
CPU-vs-CPU comparison may be added to close it.

Implementation merged in Hephaestus PR #213 from exact head
`7bc9944852a6ba92d4ff265b9fff9bc8c81e3567` as merge commit
`607ce3feb2e0ed1d907d3e0172e23377851e71d8`. Kwavers PR #402 remains at exact
head `e1648019f24e71598d0421dbd11e4f011b75878a`. The provider branch owns the
typed f32 contract, WGPU kernels, and sequential two-step contract coverage;
the consumer branch deletes the collocated raw-WGPU path and wires the
independent native-f32 CPU differential runner without a fallback. Local
feature-enabled check/Clippy, 22/22 focused equivalence tests, 2/2 affected
allocation tests, and provider contract coverage pass. Hosted exact-head gates
for Hephaestus pass and its Atlas gitlink is advanced; Kwavers hosted gates
remain open. The Kwavers workflow currently reports Documentation Build and
Validate Clean Architecture failures while the remaining matrix is still
running; no consumer gitlink advance is authorized until the exact head is
green and merged.

#### ATLAS-CFDRS-BACKWARD-STEP-108 — input-sensitive reattachment measurement [major] — closed 2026-08-18

Owner: Atlas session; provider branch `codex/cfdrs-backward-step-108`.
The provider claim and acceptance contract are recorded in its `backlog.md`.

The original consumer-local `6 * step_height` result and duplicate
streamfunction solver are removed. `cfd-2d` now owns the masked
backward-facing-step geometry, SIMPLE execution, explicit step/no-slip/
parabolic-inlet/fixed-pressure-outlet contract, signed downstream lower-wall
shear samples, and interpolated negative-to-nonnegative crossing.
`cfd-validation` maps `BenchmarkConfig` to that provider and keeps
value-semantic integration assertions. The provider reapplies a normalized
parabolic inlet only on fluid cells, leaving solid inlet cells at zero.
Provider PR #349 is at source head `95801b48`; the focused local regressions
for negative branch-flow metadata and Dean cross-fidelity both pass. Hosted
book figures pass, but Rust workspace gate run `32087680839`, job
`95563482011`, fails in Clippy before tests on 153 pre-existing workspace
errors. Default CFDrs `main` fails the same Clippy command in run
`32086797481`; none of the reported files are in this PR's diff. No consumer
solver, hardcoded runtime correlation, tolerance reduction, or benchmark
workload change closes this item. Re-open trigger: default-branch Clippy
cleanup lands, or an explicitly scoped lint-cleanup item is claimed.

#### ATLAS-CFDRS-FOURIER-NATIVE-105 — native scalar contract [major] — closed 2026-08-17

The consumer-side `f64`/`Complex64` widen-narrow path and obsolete inverse
helper are deleted. CFDrs now calls Apollo's typed native-precision transform
contract directly, with an f32 round-trip regression. Focused Nextest passes
13/13, doctests pass, and package-local Clippy passes. The change merged in
CFDrs PR #345 at `a3c53da2`; exact-head hosted run `31997714748` passes the
Rust workspace and book-figure gates. No compatibility adapter remains.

#### ATLAS-CFDRS-SSOR-OWNERSHIP-106 — provider wrapper deletion [arch] — closed 2026-08-17

The consumer-owned SSOR wrapper and legacy re-export are deleted. Direct
Leto provider tests cover zero preservation, input sensitivity, mismatch
errors, and relaxation-parameter response; the focused filter passes 3/3.
The deletion merged with the Fourier slice in CFDrs PR #345 at `a3c53da2`;
exact-head hosted run `31997714748` passes the Rust workspace and book-figure
gates.

## Landed from this sweep (2026-08-13)

| ID | Commit | Note |
| --- | --- | --- |
| ATLAS-APOLLO-FAKEGEN-036 | apollo `5749d104` | **Premise corrected.** The item claimed downstream f32 tolerances were derived against an f64-accumulated reference. False: every `dft_inverse` call site passes `Complex64`, where f64 accumulation *is* native precision, so no shipped result was wrong and no tolerance changed. The defect was latent — a trap for the first `Complex32` caller — and is closed with a derived-bound test plus a bitwise test, the latter being what actually discriminates a widened accumulator. Reclassified `[patch]` → **`[major]`**: closing it deleted `precise_re`/`precise_im` and `BLUESTEIN_NATIVE_PHASE_TRIG` from the public `KernelScalar`. |
| ATLAS-EUNOMIA-F64-SPECIALS-062 | eunomia `329fe85` | Confirmed as filed. Measured pre-fix error: `log10(2.0)` 1.43e-8, `lgamma(5.0)` 2.56e-8. |
| ATLAS-EUNOMIA-SUBBYTE-ORD-063 | eunomia `329fe85` | **Worse than filed.** With `Bf8::MIN_VALUE = 0xFC`, `max_scalar(MIN_VALUE, x)` returned `-Inf` for every finite `x` — a Max reduction over `Bf8` returned its own seed for all input. The fix also consolidated the hand-written `F16`/`Bf16` impls into one macro instead of adding four more copies. |
| ATLAS-EUNOMIA-ACCUMULATOR-064 | eunomia `329fe85` | Landed as `[minor]`, not breaking: `FloatElement` is sealed by a `pub(crate)` supertrait, so no out-of-crate implementor can exist. |
| ATLAS-LETO-TILES-048a | leto `7f80044` | `ExactSizeIterator` **did not hold as written** — `next` used `offset_of(...).ok()?`, which terminates early and would make `len()` lie. Fixed at the root with a constructor validation carrying its proof, rather than by declining the trait. |
| ATLAS-LETO-SVD-049 | leto `58b6eb3`, default `143696d` | Collapsed the obsolete duplicate SVD implementation: deleted one-sided Jacobi, moved pseudoinverse construction onto bidiagonal QR, removed the full-rank rejection, and rewrote ADR 0005 with the dated decision re-derivation. Focused SVD nextest passes 23/23. |
| ATLAS-THEMIS-TOKEN-032 | themis `8930489` | Reproduced first: the exploit compiled, a write through one reference changed what the other read, and miri gave a Stacked Borrows error. Fixed with **no new `unsafe`** — a `&mut` borrow discharges the disjointness obligation exactly as ownership does, so the tag-accepting constructors give way to `from_unique(&'a mut _)`. `project_static` became *safe*: its `# Safety` clause described an obligation the signature makes unviolatable. Zero downstream consumers, so the break needs no migration. |
| ATLAS-CONSUS-PARSE-LIMITS-035 — **closed 2026-08-14; premise was stale** | consus `03bb65e` | Parent-commit evidence: three crafted length fields panicked with `capacity overflow` and three 10 000-deep datatypes killed the process with `STATUS_STACK_OVERFLOW`. All six now return typed errors. **Two defects found beyond the item**: `find_huge_object_recursive` recursed on a loop-invariant `header.depth` so a self-referential child pointer recursed forever, and it indexed `len() - 1` on a possibly-empty vec. **Every one of the 11 line numbers in this item resolves against `03bb65e~1`, three commits behind the default head.** `03bb65e` plus `98d8ff2`/`0556918` had already bounded all of them, added `consus-core/src/parse/budget.rs`, threaded `descend(depth, ...)` through `parse_datatype_inner`, and landed the 10 adversarial tests in `consus-hdf5/tests/adversarial_input.rs` that satisfy this oracle. The item was measuring a superseded revision. What it did surface, by prompting a fresh sweep, is three sites the hardening pass itself missed, fixed in `3beb797`: **`collect_btree_v1_leaves` (`file/reader.rs`) recursed with no depth bound and re-reads `header.level` from each node instead of decrementing, so a child pointer addressing its own node recurses forever — reachable from `Hdf5File::open` on any v1 symbol-table group**, the exact twin of the `btree/v2.rs` defect sitting beside it; plus two FITS allocations sized from `TFIELDS` and `TFORMn`, each bounded exactly (a column needs its own `TFORMn` card; a repeat count cannot exceed the materialized cell) rather than by an invented ceiling. All three falsified by removing the bound: stack-overflow abort and two `capacity overflow` panics. A further ~12 sites are filed as consus `-036`/`-037` rather than widened into this item, the most exploitable being `heap/global.rs:122`'s unchecked `collection_size - header_size` underflow. **Lesson for this board: an item citing exact line numbers is a claim about a revision, and must be re-verified against the current head before it is worked.** |
| ATLAS-KWAVERS-KZK-LINEAR-080 — **closed 2026-08-17** | kwavers `5c553d36b` | **Retired buggy hand-rolled plugin onto correct existing `kzk/` module.** Created `KzkPlugin` adapter wrapping `KZKSolver`+`KZKConfig` behind the `Plugin` trait. Rewired `catalog.rs` and therapy `execution.rs` consumers. Deleted 430-line `kzk_solver_plugin/` with its three live physics defects (spectral/real-space conflation, real cos instead of complex exp, dimensionally wrong absorption). 3 regression tests (real-field evolution, plane-wave absorption oracle, focused-beam amplitude) all pass. `cargo check`/`clippy`/`nextest` 886/886 green at `5c553d36b`. | ~~[major]~~ [patch] | Oracle: plane-wave absorption decays as `exp(-alpha*z)` matching input `alpha`; focused-beam amplitude matches analytical parabolic propagator. Closed by deletion — the buggy code no longer exists.ed tolerance. Each test fails on the parent commit. **CORRECTION 2026-08-18: this closure overstates its evidence, and the retirement itself was right.** Independent verification against the deleted source at `5c553d36b^` confirms all three defects **and finds a fourth the row does not list**: the diffraction phase omitted `dz` entirely, so `(kx²+ky²)/(2k)` had units of 1/m rather than radians and reached ~1178 at 1 MHz in water — `cos(·)` was a sign-flipping pseudo-random real mask over real space. The absorption defect was also worse than described: `exp(-α·dz)` raised to `dz/2` gives an exponent of ~`α·5e-7` at `dz = 1e-3`, so absorption was **effectively disabled**, not mis-scaled. There was no FFT anywhere in the file. But **the "3 regression tests … all pass" and the stated `exp(-alpha*z)` oracle do not exist as described**: `kzk/plugin.rs:367` asserts `p000.is_finite() && p000 > 0.0`, and `:398`/`:450` assert `fields.iter().all(is_finite)`. `plane_wave_absorption_oracle` (`:335`) never checks a decay rate. All three would have passed against the buggy implementation, so they falsify nothing. Tracked as ATLAS-KWAVERS-KZK-TESTS-082. The reclassification `[major]` → `[patch]` is also wrong: `pub mod kzk_solver_plugin` was removed from `kwavers-solver`'s public surface, with no ADR, no CHANGELOG entry under Unreleased, and `cargo semver-checks` unrun. |
| ATLAS-CONSUS-SHUFFLE-038 — **closed 2026-08-18** | consus `ef439b2` | **Worse than filed: both directions were pass-through, not just the read.** `dataset/chunk.rs:311` (reverse) and `:374` (forward) each returned `Ok(data)` unchanged for filter ID 2, so fixing only the read — as the item specified — would have broken every round-trip that currently happens to work by symmetry. Original evidence stands: `h5py_shuffle_deflate_i32` returned `[50462976, 117835012, 0, 0, …]` against an expected `0..15`, which decodes to bytes `00 01 02 03 04 05 06 07` + 24 zeros — the shuffled plane layout, returned with **no error**. Not the v1 B-tree descent bound (that applies to *group* trees; the chunk path separately rejects `header.level != 0`), and deflate itself was never implicated — every pure-deflate case passed. Workspace baseline was **1 failure, not the 7 previously recorded**. |
| ATLAS-KWAVERS-KZK-TESTS-082 | **The KZK retirement replaced wrong physics with tests that cannot fail.** All three tests added to `kzk/plugin.rs` are existence-only assertions — `p000.is_finite() && p000 > 0.0` (`:367`) and `fields.iter().all(is_finite)` (`:398`, `:450`) — and **every one would have passed against the buggy implementation they replaced**, which is the mock-detection heuristic failing outright. Worse, `:335` is *named* `plane_wave_absorption_oracle` while asserting only finiteness, so it claims evidence it does not provide. This is the HARD existence-only-assertion prohibition, introduced by the fix for -080 and then reported as satisfied on the board. The one genuine analytical oracle, `kzk/validation/absorption.rs::test_absorption` (`exp(-α·d)` at 2%, exact-FFT-bin derivation, Szabo 1994), tests the **delegation target**, which the deleted plugin never called — it cannot serve as retroactive falsification. `test_gaussian_beam_diffraction` (radius vs `√2·w₀`) is `#[ignore]`d for exceeding the 60 s budget, and its non-ignored variant asserts only `center > corner`. | [major] | The three tests assert value semantics against an analytical oracle. A plugin-level `exp(-α·z)` axial decay **ratio** is feasible despite `extract_source`'s peak normalisation, since normalisation removes absolute scale but preserves the ratio; tolerance derived from the grid and operation count, not tuned. Each must be falsified by resurrecting the deleted plugin in a scratch branch and observing the failure. The `#[ignore]`d diffraction oracle either fits the committed budget or moves to a reviewed longer-budget profile — it does not stay ignored. Separately: the `pub mod` removal gets its ADR, its Unreleased CHANGELOG entry, and a `cargo semver-checks` run. |
| ATLAS-MNEMOSYNE-ALIAS-033 | mnemosyne `4c22fba` | **Premise disproved.** The reported sequence passes miri under both Stacked and Tree Borrows on the unfixed code. A control — the same aliasing with the exclusive reference *used* afterwards — is flagged immediately, so the method had detection power and the invalidation is real; the UB is not. `with_scratch` never touches `vec` after the closure, and the slice points into the heap buffer, a different allocation from the struct inside the `UnsafeCell`. Soundness held by accident of dead-code timing, so it was fixed anyway and `capacity()` is now safe code. **Reclassify: fragility, not UB.** The two secondary fixes were confirmed, and the leak-on-unwind had a *third* site (`Heap::free`) the item did not name. |
| ATLAS-CACHE-FORK-055 — **closed 2026-08-14** (partial) | — | **33.8 GB reclaimed** by deleting 22 stale `repos/*/target` forks. 25.1 GB remains in ritk, kwavers and mnemosyne, deferred because each showed activity within hours. The forks regrow unless whatever creates them is found, so the item stays open until the cause is identified. Verified 2026-08-14: zero real cargo caches under `repos/*`. The one surviving `repos/athena/target` holds only mdBook output from its Pages workflow's `output-path: target/book/athena`; the `target_forks` metric was counting any dir named `target*` and is corrected in `977e009` to require a cargo marker (`.rustc_info.json`/`CACHEDIR.TAG`/`debug`/`release`), tested in both directions so suffixed evasions like `target_isolated` still count. **Regrew and was cleared again 2026-08-18: 7.67 GB** (`repos/helios/target` 7.52 GB idle 16h, `repos/harmonia/target` 339 MB idle 6.5h), both carrying `.rustc_info.json` so both real caches rather than the athena false positive. The cause question the item left open is now answered as *no live override*: neither repo has a nested `.cargo/config.toml`, `CARGO_TARGET_DIR` is unset, and the root `target-dir = "target"` resolves config-relative to `D:\atlas\target` correctly — so these are residue from building the member standalone outside the umbrella, not a misconfiguration to remove. That makes recurrence expected rather than a defect, and the corrected `target_forks` metric is the standing control: it caught both within one scan. |
| ATLAS-HELIOS-STRAY-PNG-061 | Atlas `0023164` | **Premise stale.** The tracked `helios_workflow_output/{ct,dose,mu,recon}.png` files were already removed when the root was cleared to the sanctioned set; the current tree has no directory or tracked PNGs. No provider edit was required. |
| ATLAS-HORAE-EXACTNESS-069 | Horae PR #12 merged at default `41dcf00`; provider CI `31792859575` (verify and supply-chain) and book build `31792859919` are green. Event clipping now states the Sterbenz precondition and preserves the event endpoint as authoritative; ratio-three subcycling carries a derived floating-point reconstruction bound with value-semantic tests. |
| ATLAS-HYPERION-INTERP-068 | Hyperion PR #9 merged at default `41ef18e`; provider `verify` and `supply-chain` run `31794767546` are green. NIST reference intervals now use a native-`T` natural cubic spline in log-energy/log-coefficient space, with ten independently queried XCOM off-knot values as a method-regression oracle. XCOM's fourth displayed digit is documented as an interpolation aid rather than an accuracy guarantee; no unsupported global error bound is claimed. |
| ATLAS-HEPH-SEAM-043 / ATLAS-HEPH-ACCEL-044 / ATLAS-HEPH-DEADBUILD-060 | Hephaestus PR #208 merged at default `ff2ab47`; exact-head CUDA `31793963123`, ROCm `31793963119`, WGPU `31793963054`, and Metal `31793963181` checks pass. `KernelDialect` is open, scan is shared over `DeviceApi`, CUDA/ROCm scan copies and the unused root build script are deleted, and required Leto SVD lock/API co-evolution is aligned. Independent architectural review approved the final head; hardware jobs were skipped by the workflow. |
| ATLAS-LICENSE-FILES-039 | **Premise stale.** The current default heads of Moirai `e972174`, Leto `143696d`, Gaia `18349bc`, and Helios `152a66c` each carry both `LICENSE-APACHE` and `LICENSE-MIT`, and each manifest declares `MIT OR Apache-2.0`. No provider edit was required. |
| ATLAS-ADR-GOV-058-HYPERION | Hyperion PR #10 merged at default `d17e863`; its ADR 0001 index now records the existing canonical `Status: Accepted` header. Provider checklist and gap audit are synchronized; exact-head `verify` and `supply-chain` run `31795703287` pass, while recurseml analysis remains report-only. The broader ADR-governance item remains open for other members. |
| ATLAS-ADR-GOV-058-IRIS | Iris PR #15 merged at default `3c9dc85`; its generated ADR index now lists ADR 0001 and 0002 as `Accepted` and excludes the non-ADR `INDEX.md` overview. Exact-head `verify` and `supply-chain` run `31796011010` pass; recurseml analysis remains report-only. The broader ADR-governance item remains open for other members. |
| ATLAS-ADR-GOV-058-PROTEUS | Proteus PR #11 merged at default `3c64c8e`; both ADR status headers are canonical `Accepted` and the generated index matches them. Exact-head `verify` and `supply-chain` run `31796273743` pass; recurseml analysis remains report-only. The broader ADR-governance item remains open for other members. |
| ATLAS-ADR-GOV-058-AEQUITAS | Aequitas PR #30 merged at default `f7c9cf2`; its fifteen-ADR generated index now records canonical `Accepted` statuses with no anomalies. Exact-head `verify` and `supply-chain` run `31796547009` pass; recurseml analysis remains report-only. The broader ADR-governance item remains open for other members. |
| ATLAS-ADR-GOV-058-HORAE | Horae PR #13 merged at default `1b35d3f`; its ADR 0001 index now records the existing canonical `Status: Accepted` header. Provider checklist and gap audit are synchronized; exact-head `verify` and `supply-chain` run `31797039383` pass, while recurseml analysis reports an analyzer error and remains report-only. |
| ATLAS-ADR-GOV-058-EUNOMIA | Eunomia PR #67 merged at default `9c2d972`; its four-ADR generated index now records canonical `Accepted` statuses with no anomalies. Exact-head `Rust verification` and `Supply chain` run `31797566750` pass; recurseml analysis reports an analyzer error and remains report-only. |
| ATLAS-ADR-GOV-058-THEMIS | Themis PR #25 merged at default `8d6e83e`; its two-ADR generated index now records canonical `Accepted` statuses with no anomalies. Exact-head compile-fail, Ubuntu, Windows, and Miri checks pass in run `31797905436`; recurseml analysis reports an analyzer error and remains report-only. |
| ATLAS-ADR-GOV-058-RITK | Ritk PR #147 merged at provider default `d1087139`; ADR 0002 now records `Accepted` without claiming the Burn→Coeus consumer cutover is complete, ADR 0007/0008 use canonical status headers, and the generated index matches all ADR headers. PM-sync PR #148 merged at `37e46ef`. Final exact-head CI `31802349902` and Python CI `31802349905` pass; recurseml analysis remains report-only. | [patch] | ATLAS-ADR-GOV-058 |
| ATLAS-ADR-GOV-058-LETO | Leto PR #112 merged at provider default `2821a4b`; ADR 0001 is canonical `Rejected` after ADR 0004 shipped its replacement, ADR 0011 records the measured full-block regression without claiming that path shipped, ADR 0012 is `Proposed`, and ADR 0013 is canonical `Accepted`. The later duplicate ADR 0011 was renumbered to ADR 0024 and its code-doc link updated. The generated index has no anomalies or drift. Exact-head CI `31804526486` and Pages deployment `31804524894` pass; recurseml analysis remains report-only. | [patch] | ATLAS-ADR-GOV-058 |
| ATLAS-ADR-GOV-058-HEPHAESTUS | Hephaestus PR #209 merged at provider default `be7389e`; 52 ADR records now use canonical statuses and the generated index has zero anomalies or drift. ADR 0003 retains the accepted architecture while explicitly recording QR work as pending; ADR 0004 retains its amendment; ADR 0005 records its supersession as historical `Rejected` status. Exact-head CUDA `31805214715`, ROCm `31805214723`, WGPU `31805214652`, and Metal `31805214716` checks pass; recurseml remains report-only. Atlas points to the merged default head. | [patch] | ATLAS-ADR-GOV-058 |
| ATLAS-ADR-GOV-058-APOLLO | Apollo PR #93 merged at provider default `fca501f`; ADR 0001 is canonical `Rejected` while preserving its Hephaestus supersession, and ADR 0011 is canonical `Accepted` while preserving its dated benchmark decision. The 39-record generated index has zero anomalies and zero drift. Exact-head Rust workspace `31806913513` (job `94787923879`) and Python bindings (job `94787923826`) pass; CodeRabbit passes and recurseml remains report-only. Atlas records the merged default; the peer-owned performance branch and dirty lockfile remain outside scope. | [patch] | ATLAS-ADR-GOV-058 |
| ATLAS-RITK-DICOM-ORIENTATION-070 | **Closed at Atlas integration scope.** RITK owns `ImageOrientationPatient` (0020,0037) and Atlas now records merged defaults for both sides of the seam (`ritk` `bd43dbb3`, `helios` `152a66cd`). `python scripts/atlas-provider-integration-audit.py --exact-heads` passes and confirms requested-provider exact-head/coherence closure with both gitlinks aligned to fetched defaults. | [minor] | ATLAS-RITK-DICOM-ORIENTATION-070 |
| ATLAS-HERMES-AMX-DOWNGRADE-096 | **Closed at Atlas integration scope.** The Hermes AMX downgrade slice is integrated at merged default `fb36e0fe`, and `python scripts/atlas-provider-integration-audit.py --exact-heads` passes with requested-provider exact-head/coherence closure. Atlas now records the merged Hermes default gitlink and no further root-owned integration action remains for this item. | [patch] | ATLAS-HERMES-AMX-DOWNGRADE-096 |
| ATLAS-KWAVERS-MNEMOSYNE-LOCALITY-001 | **Closed at Atlas gitlink scope 2026-08-16.** Kwavers folds its hand-rolled NUMA memory-policy execution (`bind_memory_to_node` / `allocate_interleaved_memory` / `first_touch_memory` in `arena/numa/memory.rs`) onto mnemosyne-heap: commit `152c4a7d1` on `codex/kwavers-mnemosyne-numa` (head `08df5730f`) deletes the duplication (net −235 lines) and routes `NumaAwareAllocator` / `SoAFieldBuffer` / `first_touch_memory_parallel` through `mnemosyne_heap::numa::{bind_to_node, first_touch}`. Mnemosyne `5ca0461` owns the execution (`mnemosyne-heap::numa` + `TieredHeap::alloc` routing `PlacementHint::Numa` through `bind_to_node`); Themis owns the vocabulary; Moirai owns the parallel fan-out. PR #382 merges the fold and PR #383 normalizes the ADR statuses; Atlas now records merged Kwavers default `1d7c6899` (gitlink-only advance; the peer-dirty `codex/kwavers-floatelement-roots` working tree is left untouched per the concurrent-agents rule). The stale clean `kwavers-mnemosyne-numa` lane is removed and the lane audit is clean. | [patch] | ATLAS-KWAVERS-MNEMOSYNE-LOCALITY-001 |
| ATLAS-MOIRAI-ORDERING-052-PM-SYNC | Moirai PR #134 merged at provider default `9125837`; `CHECKLIST.md` now closes the SPSC, async wake-dedup, PAL reactor, and connection-pool reservation slices with their exact merged heads and hosted evidence. The provider remains clean and no production source changed. | [patch] | ATLAS-MOIRAI-ORDERING-052 |
| ATLAS-MOIRAI-ORDERING-052-INSTRUMENT | Atlas-side instrument correction: the conformance scanner counted path-redirected `#[cfg(test)]` sidecars as production (`declared_cfg_test` missed sibling-directory `#[path]` declarers; moirai-iter gates `../async_iter_tests.rs` from `src/async_iter/mod.rs`). Fixed at `9828ee8` with three regression tests; moirai `seqcst_production` ratchet drops 101 to 85, its honest value. Remaining production sites are documented decisions: the Chase-Lev thief gate needs one total order across increment/recheck versus the resizer drain (a Relaxed increment has no SC-order position, so relaxation requires protocol restructuring for no measured win on a locked-CAS path), and idle/blocking form the documented Dekker store-buffer pair. Full family sweep complete: worker.rs, scheduler/core.rs, futex_mutex.rs, and the mpmc waiter-count adds (channel.rs:172,261 - register-before-recheck Dekker halves, independently derived) are all recorded KEEP decisions; zero undocumented production sites remain and the item closes with no source change. Ritk follow-up candidate under its own claim: `crates/ritk-vtk/src/domain/mtime.rs:46` monotonic tick admits Relaxed. | [patch] | ATLAS-MOIRAI-ORDERING-052 |
| ATLAS-MOIRAI-ORDERING-052-SPSC | Moirai PR #130 merged at default `ac111b3`; the SPSC ring model uses a capacity-two wrap-around, three FIFO values, and preemption bound four. Hosted `Loom channel models` passes in run `31798789797`; the external recurseml analyzer error remains report-only. |
| ATLAS-MOIRAI-ORDERING-052-WAKER | Moirai PR #131 merged at default `fd517fe`; async `is_queued` clear/swap now use Relaxed ordering, with a Loom dequeue/clear versus wake/swap model. Exact-head workflow `31800148163` passes Loom and workspace gates; `31800148178` passes bindings and all wheel smoke tests; recurseml analysis remains report-only. The first model revision failed on a non-contractual cross-atomic observer assertion and was corrected before the passing head. | [patch] | ATLAS-MOIRAI-ORDERING-052 |
| ATLAS-MOIRAI-ORDERING-052-REACTOR | Moirai PR #132 merged at default `8830f1b` (change head `098e266`); the PAL reactor's three `running` accesses now use Relaxed ordering because the flag carries loop control only and `stop()` separately wakes the platform poller. Exact-head workflow `31800607186` passes Loom and workspace gates; `31800607152` passes bindings and all wheel smoke tests; recurseml analysis remains report-only. | [patch] | ATLAS-MOIRAI-ORDERING-052 |
| ATLAS-MOIRAI-ORDERING-052-POOL | Moirai PR #133 merged at default `f766c6d` (change head `04dc26e`); `ConnectionPool::reserved_connections` admission/release accounting now uses Relaxed operations, with a bounded Loom model covering two serialized admissions racing one paired cancellation. Exact-head workflow `31801180700` passes Loom and workspace gates; `31801180691` passes bindings and all wheel smoke tests; recurseml analysis remains report-only. | [patch] | ATLAS-MOIRAI-ORDERING-052 |

Completed provider slices from this sweep are recorded here so the residual
rows below retain their original audit scope:

| ID | Commit | Closed scope |
| --- | --- | --- |
| ATLAS-COEUS-LAYERNORM-SHAPE-031 | coeus `a2638c03` | Multi-dimensional trailing-shape LayerNorm across Rust core, autograd, GPU provider contracts, and thin Python bindings; provider workflows and book passed. |
| ATLAS-IRIS-COLORSPACE-072 | iris `eec98186` | Explicit sRGB encoded/linear-light RGB and opacity-alpha contract with byte round-trip coverage. |
| ATLAS-PROTEUS-DOMAIN-073 | proteus `6b9bd0b` | Temperature validity-domain newtype, finite-positive validation, typed errors, and boundary tests. |
| ATLAS-ASCLEPIUS-PARAM-074 (typed-parameter slice) | asclepius `5d528d2` | Closed: distinct `Gamma50` and `LymanSlope` types have compile-fail swap coverage; the proposed CEM43 restriction was withdrawn because sub-43 °C behavior is part of the canonical law contract. |
| ATLAS-THEMIS-CONFORMANCE-083 | themis `b1b671c`; Atlas `0922c58` | Replaced Themis's duplicate thread cache with Melinoe's `thread_cached!` provider, split the oversized static-cell leaf, and closed the value-semantic assertion and safety-comment findings. Hosted Ubuntu/Windows, Miri, compile-fail, documentation, and CodeRabbit checks pass. |
| ATLAS-POSTMERGE-HEAD-084 | Atlas `73974ee` | Advanced the Ritk and Eunomia gitlinks to fetched defaults `3f30cddf` and `2e0d724c` while preserving dirty provider worktrees. Ritk hosted CI is green; Eunomia's Rust and supply-chain checks are green and its external `recurseml/analysis` status remains report-only. |
| ATLAS-HELIOS-BENCHMARK-085 | Helios `152a66c` | Helios PR #54's benchmark regression job completed successfully; the merged default head is fully green across book, Rust, Python, and benchmark checks. The Atlas gitlink remains peer-owned at its staged integration head. |
| ATLAS-THEMIS-STD-FEATURE-086 | Themis PR #22; merged default `f879e71` | Fixed the optional-dependency feature closure: `themis/std` now activates Melinoe before referring to its `std` feature. Ubuntu, Windows, compile-fail, branded Miri, and local strict Clippy are green; `recurseml/analysis` is external/report-only. |
| ATLAS-THEMIS-STABLE-PROOFS-088 | Themis PR #23; merged default `fa8dc29` | Added stable trybuild enforcement for invalid shared-cell construction (`E0599`) and overlapping mutable borrows (`E0499`) with committed stderr fixtures. Ubuntu, Windows, compile-fail nightly, and branded Miri are green; `recurseml/analysis` is external/report-only. |
| ATLAS-THEMIS-GITATTRIBUTES-092 | Themis PR #24; merged default `17d3647` | Reconciled the stale provider PM claim: the tracked `.gitattributes` already contains `* text=auto`; no source or tree-wide renormalization was required. |
| ATLAS-AEQUITAS-CI-093 | Aequitas PRs #27–#29; merged default `770a369` | Replaced unlocked lock normalization with locked metadata verification, refreshed the standalone lock to Eunomia `b6f001a`, removed overlay-only patch entries, and reconciled the delivered 0.2.0 comparison label. Default-head CI `31786185235` is green. |
| ATLAS-PROTEUS-CI-094 | Proteus PR #10; merged default `671c9fa` | Added finite CI timeouts and concurrency, converted all lock-sensitive verification commands to `--locked`, synchronized the README, and refreshed the standalone lock to Aequitas `770a369` plus Eunomia `b6f001a`. Default-head CI `31786562412` is green. |
| ATLAS-MOIRAI-NUMA-095 | Moirai PR #128 plus PM closeout PR #129; merged default `e972174` | Forwarded `MoiraiBuilder::numa_aware` through the existing core/executor feature seams and one scheduler construction path. Default topology-aware behavior remains; explicit disablement skips worker NUMA assignment construction. Default-head Rust Workspace `31787962637` and Python Bindings `31787962649` are green. |
| ATLAS-HERMES-AMX-CONFIG-087 | Hermes PR #40 merged at `b95d19d` (head `5a8d718`) | Corrected the AMX irregular-width configuration and repacked row-major GEMM right-hand panels into the VNNI layouts required by the dot-product instructions: `K/4 × 4N` for INT8 and `K/2 × 2N` BF16 elements. The provider-owned packer covers fixed-tile and blocked-GEMM paths with independent value-semantic four-byte and two-element grouping tests. Follow-up cleanup closes Hermes `must_use_candidate` 162→0, `elidable_lifetime_names` 131→0, `missing_errors_doc` 83→0, `missing_safety_doc` 8→0, `semicolon_if_nothing_returned` 92→0, and `unreadable_literal` 180→0 with a documented generated-table exception, splits the SIMD view-cast and `SimdOps` blanket-implementation leaves, scopes the macro's unreachable-code expectation to Neon with a regression test, rejects zero NTT moduli with a typed error, validates bitboard squares before shift arithmetic, removes the conformance ratchet regressions introduced by the lint cleanup, and canonicalizes NTT residues before subtraction. The current local Hermes workspace all-target Clippy gate is clean, nextest is 454/454, the Hermes/core doctest gate is 18/18 with 7 ignored, and the benchmark-target smoke gate passes. Hosted run 31779776851 is green across all seven jobs. |

**Current exact-head status (2026-08-14):** the structural and exact-head
provider audits are clean. Moirai is advanced to hosted-green `e972174`, and
Leto is advanced to hosted-green `143696d`. Aequitas, Proteus, Helios,
Iris, Ritk, Eunomia, Gaia, Melinoe, Tyche, and Hermes now match
their fetched default heads. Helios PR #54 is merged at `152a66c` and its
benchmark regression job is green. Themis's stable-proof PR #23 is merged at
`fa8dc29`. Hermes PR #40 carries the AMX VNNI packer and follow-up
lint/docs/structure cleanup, merged at `b95d19d`; local contract gates and all
seven hosted checks are green at head `5a8d718`. Proteus and Iris default-head
checks are green across build, verification, deployment, and supply-chain
jobs. Moirai default-head Rust Workspace and Python Bindings runs
`31782344026` and `31782344151` are green. Leto default-head Rust verification
run `31782827546` and Pages deployment run `31782826144` are green. The prior
benchmark and Intel SDE AMX differential checks are green. Gaia's exact
default-head CI run `31784028179` is green at `18349bc`; Melinoe's default
head `0bc287a` carries the hosted MSRV run `31785253730` green at source head
`6e6a181`; the book run
`31783965823` is green at source head `c06504c`, and the replacement head only
adds documentation to the test crate outside the book workflow's source paths.
Themis's stable-proof source remains at `fa8dc29`; its PM closeout is merged at
default head `17d3647`. Aequitas's lock-gate PR #29 default is `770a369`; its
exact default-head CI run `31786185235` passes verify and supply-chain.
Proteus's bounded locked-gate PR #10 default is `671c9fa`; exact default-head
CI run `31786562412` passes verify and supply-chain. Moirai's NUMA policy PR #128
and PM closeout PR #129 are merged at default `e972174`; exact default-head Rust
Workspace run `31787962637` and Python Bindings run `31787962649` pass.
Horae PR #12 is merged at default `41dcf00`; exact-head CI run `31792859575`
passes verify and supply-chain, and the book build `31792859919` is green.
Hyperion PR #9 is merged at default `41ef18e`; exact-head CI run `31794767546`
passes verify and supply-chain. Its external `recurseml/analysis` status is
report-only and failed without affecting the provider-owned gates.

## Tier 0 — unsoundness and wrong numbers shipping

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-LETO-LAYOUT-034 — **closed 2026-08-15** | `Layout` (`crates/leto/src/domain/layout/mod.rs:13-20`) exposes `pub shape`/`pub strides`/`pub offset` with a non-validating `pub const fn new` (`:24`) and no `#[non_exhaustive]`. **84 `unsafe` blocks** in leto and every array in kwavers/CFDrs/ritk/gaia/coeus rest on its invariant; safe downstream code can construct an out-of-bounds layout today. | [major] | Zero `pub` fields on `Layout`; a validating `try_new`/`TryFrom` is the only construction path; adversarial tests per invalid class return a typed error; all five consumers build **The oracle in this row would not have fixed the defect it was filed for, and that is the finding.** Sealing `Layout` closes nothing on its own: a `Layout` carries no pointer and no length, so "fits the buffer" is not a property it can express. A proof-of-concept written before any code change had safe Rust read ~4 KiB past a 16-byte buffer **using a `Layout` from the validating `c_contiguous` constructor** - `c_contiguous([1000])` is perfectly self-consistent and simply does not fit a 4-element buffer. The real breaks, fixed in leto `580c859`: `ArrayViewMut`'s four `Index`/`IndexMut` impls dereferenced a computed offset with no `offset < len` check their `get`/`get_mut` siblings perform, and `trace`, `kron`'s strided branch and `matmul`'s `copy_back_to_out` reached `get_unchecked`/raw writes unvalidated - the last an operand mixup, validating the *scratch* view while writing through the caller's `dst`. The premise's other half was also off: the 84 unsafe blocks are exact, but about half are unrelated to layout and the layout-dependent ones rest on `validate_storage_len` at constructor/dispatch sites, not on `Layout`'s invariant. **The consumer list was wrong in both directions** - CFDrs, ritk and gaia have zero `leto::Layout` usage and were never affected; hephaestus (~270 sites), athena and apollo were, and none was listed. Sealing still shipped and still earns its place, making `size`/`min_max_offsets`/`offset_of` total: private fields, `#[non_exhaustive]`, `try_new`/`TryFrom` the only public path, validated `Deserialize`, and no struct literal anywhere outside a `pub(crate) from_parts_unchecked` serving ~15 internal derivations in hot iterator bodies. 27 adversarial tests each assert a typed `LetoError` with a positive control; the original PoC is pinned as three `#[should_panic]` regressions. **miri 182/182 clean.** `cargo semver-checks` reports 4 major breaks, declared in the CHANGELOG migration recipe and ADR 0025, not hidden. **Remainder filed, not half-done:** `ArrayView::new`/`ArrayViewMut::new` stay safe and non-validating, so today's safety is an enumeration over the current tree rather than a type-system guarantee - converting them to `unsafe fn new_unchecked` is 69 call sites across 7 repos and a second `[major]`, recorded in ADR 0025. |
| ATLAS-KWAVERS-REAL-COMPUTE-028 — **closed 2026-08-15** | *(already open — now with a fifth site and exact locations)* Five production paths return their input unchanged, three under real citations: `mixed_domain.rs:158-170` and `:219-231` (Hamilton & Blackstock 1998), `kzk_solver_plugin/solver.rs:301-310` (Jing et al. 2012), `transfer_learning/learner.rs:137-143` (live at `:43`), and newly found `kwavers-math/src/simd/interpolation_ops.rs:129-141` — an `avx2` `#[target_feature]` fn with a 5-line SAFETY comment whose body calls the scalar function. | [major] [arch] | `rg "Ok\(field\.clone\(\)\)" crates/kwavers-solver/src` → 0; each site has a differential/analytical test that **fails when the body is reverted to the clone**, demonstrated in the PR **Closed by deletion, because none of the five was a production path.** A repo-wide search over every `.rs` including examples, benches and tests, plus the plugin catalog, found **zero callers** for any of them - so there was no live call site whose physics to implement, and writing physics into uncalled code would have added ungrounded derivations rather than fixing a defect. A sixth unlisted identity mock (`DomainAdapter::adapt`, citing Ganin 2016 and Raissi 2019) went with them, and two citation attributions in this row were wrong. Removed in kwavers `7bf8eca48`. `mixed_domain` was deleted whole rather than repaired: its *remaining* method computes `k = 2*pi/(c*dt)` independent of the spectral index, so it applies one constant phase to every k-bin - a scalar attenuation dressed as an angular-spectrum propagator - and fixing only the two clones would have left that beside them. The AVX2 site was deleted rather than vectorized: its `#[target_feature]` body called the scalar function, making its five-line SAFETY comment false, and the dispatch was dead anyway on AVX-512 hosts. **The falsification evidence this oracle demands cannot exist and was not faked** - with no caller there is nothing to observe the difference, and no test was written that would have passed with the mock in place. nextest 6136/6136. **The live defect these mocks were sitting next to is filed as ATLAS-KWAVERS-KZK-LINEAR-080.** |
| ATLAS-CONSUS-PARSE-LIMITS-035 | HDF5 parse paths reachable from `Hdf5File::open` allocate on unbounded file-supplied lengths — `btree/v2.rs:685,761` (`with_capacity(total_records as usize)`, u64 straight from the header), `dataset/chunk.rs:110,126,166`, `datatype/compound.rs:336,522,550`, `consus-fits/src/table/data.rs:153,187,188` — and `parse_datatype_inner` (`datatype/compound.rs:80→329→360→446`) recurses with **no depth parameter anywhere in the chain**, so a nested compound overflows the stack (uncatchable abort). `try_reserve` appears once in the whole tree. | [minor] | A `total_records = u64::MAX` header, an oversized chunk size, and a 10 000-deep nested compound each return a typed error, not a panic or abort; each test fails on the parent commit |

The removed rows are closed findings, retained in the landed table above: Themis
`ATLAS-THEMIS-TOKEN-032`, Mnemosyne `ATLAS-MNEMOSYNE-ALIAS-033`, Apollo
`ATLAS-APOLLO-FAKEGEN-036`, and Eunomia `ATLAS-EUNOMIA-F64-SPECIALS-062`,
`ATLAS-EUNOMIA-SUBBYTE-ORD-063`, and `ATLAS-EUNOMIA-ACCUMULATOR-064`.
Their current provider source and evidence are not active Tier 0 work.

## Tier 1 — evidence that does not support its claim

> **Claimed 2026-08-13 by the sweep session.** In progress on disjoint scopes:
> helios (`-037` gamma tautology, plus the analytical dose oracle and the
> vacuously-passing GPU tests), coeus (`-041` gradcheck harness), gaia (`-042`
> verification gate), hermes (`-040` AMX probe), and iris/proteus/asclepius
> (`-071` license texts, `-072` colour-space convention, `-073`/`-074` validity
> domains). `-038` README truth and the moirai/leto/gaia/coeus half of `-039`
> landed earlier in the sweep. Peers: take another scope, not these.

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-HELIOS-GAMMA-037 — **closed 2026-08-15** | **Stale — already fixed before sweep.** The claimed self-comparisons in `end_to_end.rs` and `tomotherapy_workflow.rs` now compare dose against scaled copies (2%/6% offsets), not self-comparison. `attenuation_map.rs` does not exist. Self-comparisons in `gamma.rs` are valid identity tests (γ(f,f)=0). | [patch] | Closed — oracle not met on current tree |
| ATLAS-README-TRUTH-038 — **closed 2026-08-15** | Last remnant fixed: hermes' README claimed 0.6.0 against a 0.7.0 workspace (`9a678f5`). **Mostly stale.** moirai "Zero External Dependencies" claim removed; LICENSE/CONTRIBUTING exist; badges correct. CFDrs "Complete MPI Infrastructure" now explicitly disclaimed. ritk "Burn-backed" and nalgebra credit gone. gaia correctly warns about third-party crate. hermes version still mismatched (workspace 0.7.0, README says 0.6.0). **kwavers Quick Start fixed** — updated to use `kwavers-grid`/`kwavers-medium` individual crate imports per ADR 011. | [patch] | Per repo: every headline claim resolves to code, every linked file exists, the quick-start line names the real registry package and version, and the example compiles as a doctest |
| ATLAS-HERMES-AMX-040 — **closed 2026-08-15** | **Stale — real probe landed.** Re-verified: `probe.rs` carries 17 CPUID/XCR0/`arch_prctl` call sites. ** `amx_runtime_supported()` now performs CPUID leaf 7 + XCR0 + `arch_prctl` permission request in `hermes-simd-intrinsics/src/x86_64/amx/probe.rs` (commit `9fdbd16`, 6 hours after filing). The README already documents the three-condition probe chain. Remaining gap is hardware availability — no CI runner has Sapphire Rapids+ silicon, so the AMX-vs-scalar differential cannot execute in CI. | [minor] | Closed — oracle met on current tree |
| ATLAS-COEUS-GRADCHECK-041 — **closed 2026-08-15** | **The coverage found two real bugs, which is the point of asking for the evidence.** `multi_margin` and `multi_label_margin_loss` were silently wrong for **every batch size but one**: both did a per-row target lookup with `index_select`, which applies one column set to *every* row, so an `[N, C]` input produced `[N, N]`/`[N, N*C]` and the following `reshape` panicked; `multi_margin` had a second instance broadcasting `[N,1] - [N]` to `[N, N]`. All three sites are shape-correct at exactly `N == 1`, and **every pre-existing test of both ops used `N == 1`** — a suite that could not fail on the defect it covered. Both doc comments claimed the scores "are gathered", which the code did not do. Fixed with `coeus_ops::gather` plus hand-computed `N = 2` forward regressions, since gradcheck alone cannot catch a wrong-but-self-consistent forward (coeus `59a6a95c`). **Coverage 10 → 102 of 137**, past the bar. The denominator needed correcting: 93 bespoke `BackwardNode` types plus 44 `Unary`/`BinaryAutogradOp` formulas is 137, while this row's "80" was the raw `impl BackwardNode<` block count (79 at HEAD) — two granularities of one thing; and the "~13 (~11%)" was optimistic, only 7 ops had real FD tests. 118 tests added at the helper's derived `eps^(2/3)` tolerance with **nothing widened**, using a golden-ratio irrational rotation so samples provably never land on a kink — no seeded RNG, so no flake surface. Uncovered remainder, highest-value first: the conv/pool families, `ctc_loss`, batchnorm2d/3d, `cross_entropy_loss`. **Original text:** Infrastructure complete; coverage gap remains. A production-quality `gradcheck()` helper already exists in `src/gradcheck.rs` with eps-derived step size and zero-gradient guard. 3 existence-only assertions were previously fixed (softmin, norm_p, multi_margin). Coverage: ~13/115 ops have FD tests (~11%). Highest-risk uncovered: 14 loss ops, normalization (rmsnorm/batchnorm), attention (sdp_attention). Helper is public and re-exported; barrier is writing test closures, not infrastructure. | [minor] | One `gradcheck` helper with an eps-derived step and cited derivation (DONE); FD-covered paths ≥ 40 of 80; `rg 'is_some\(\), "' crates/coeus-autograd/src` → 0 (DONE) |

## Tier 2 — architecture: SSOT, DRY, and the zero-cost seams

> **Claimed 2026-08-13 by the sweep session.** In progress on disjoint scopes:
> moirai (`-051` bounded default channel,
> `-053` cache-line SSOT, and two `SeqCst` clusters of `-052`), CFDrs (`-046`
> collapse eight `*Scalar` traits),
> athena (`-066` document the two undocumented solver families, `-070` flatten
> the Arnoldi basis), and ritk (`-047` ADR plus one vertical increment).
> `-048a` landed earlier; `-048b` stays blocked on a kwavers migration.
> The current session is now auditing `-049` against Leto default `143696d`;
> the provider source and ADR are read-only inputs to this root PM closure.
> Peers: take another scope, not these.

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-COEUS-BACKEND-045 — **matmul family landed 2026-08-18; two families remain blocked upstream** | **The row's causal claim is backwards and its upstream premise is wrong.** The missing ops were real, but the absence of a generic layer is not *why* CUDA and WGPU forked — they fork because both crates predate the seam. And **hephaestus needed zero changes**: `DenseProductOps` (its ADR 0044) already existed and all four vendors already implemented it, so `repos/hephaestus` is untouched. Every line count here is stale: cuda 6,854 not 7,390; wgpu 8,261 not 8,897; metal 99 and rocm 103, not 122/126. Landed in coeus `afc1a7ce`: a `MatmulProvider`/`MatmulBackend` pair with one generic `matmul::<B,T>` and a blanket impl, mirroring the crate's own convolution seam; CUDA and WGPU kernels **deleted, not wrapped**. The seal is removed and was worse than recorded — `pub mod private` was re-exported, so any crate could implement the "sealed" trait, and the impl set is genuinely cross-crate. A **fake generic** went with the deleted code: `cuda_matmul` was bounded `T: CudaScalar` but gated on `TypeId == f32`. **The line-count clause is not met and forcing it would be gaming:** net −202, and the residue is not vendor kernel text but ~2,772/~2,768 lines of pooling and ~894/~1,024 of unfold-fold, roughly 1,350 per crate near-identical clone — consolidatable but **unreachable**, because `hephaestus-core` has no pooling or sliding-window device trait. So `HephaestusBackend<MetalProvider>: BackendOps<f32>` still does not compile, and rather than claim the oracle the compile-time test asserts what is true: `MatmulOps<f32>` via the seam. **Parity suites are unmodified but cannot confirm the swap** — they are among the 116 `AdapterUnavailable` failures, so device equivalence of the provider kernel against the deleted one is **unverified pending GPU CI**. | [arch] | Matmul family met. Pooling and unfold-fold staged as hephaestus ADR 0052: the shared primitive is confirmed by a file-level read (the dialects are a transliteration — same atomics-free gather backward, same shape derivation, ~35% of each tree duplicated host arithmetic), but the blocker is not the missing core trait. Nothing exists upstream to implement it against: `leto-ops` has no pooling family, so `hephaestus-host` (ADR 0046) has nothing to adapt and no vendor crate has a pooling kernel. Re-open trigger: leto-ops gains the pooling family. |
| ATLAS-CFDRS-SCALAR-046 — **closed 2026-08-15** | **Stale — consolidation already done.** Re-verified: `pub trait \w*Scalar` across `crates/` returns exactly one hit, `CfdScalar` at `cfd-core/src/scalar.rs:40`, whose own docs state it adds only the CFD-domain bounds on top of `eunomia::RealField` and `leto_ops::RealScalar` rather than redefining a numeric surface — which is the stack's scalar SSOT rule satisfied, not merely a count of one. ** `rg 'trait \w*Scalar' crates/` returns exactly 1 hit (`CfdScalar` at `cfd-core/src/scalar.rs:352`). `from_f64` and `to_f64` duplication eliminated. | [minor] | Closed — oracle met on current tree |
| ATLAS-RITK-VIEWS-047 — **seam landed 2026-08-15; consolidation clauses respecified** | **Three of this row's five factual claims are wrong and are corrected here.** (1) "zero GATs across 1771 files" — false; `ritk-snap/src/dicom/series_tree/mod.rs:39,42` already declares a lending trait with `type Str<'b>`/`type Path<'b>`. The true statement is *no GATs on the image data plane*. (2) "three heap allocations per output voxel at `linear/mod.rs:124-126`" — false, already fixed by `7635f1aa`, which replaced those `vec!`s with `[_; MAX_RANK]` stack scratch and left a comment recording the very measurement this row cites; those line numbers are now the middle of a parameter list. (3) "the only routes to pixel data are `data_slice()` or a whole-volume copy" — misleading, and the real defect is sharper: `Tensor::slice()` already returns a cheap strided view, but **a strided view cannot be read** — `as_slice` and `iter` both assert contiguity, so views were free to make and impossible to use. (4) "7 parallel data accessors" — true, and **681 call sites across ~250 files**, `data_slice` alone 562. (5) "3 parallel coordinate-transform families" — **understated roughly six-fold: 17 implementations across 22 sites.** Seam delivered in ritk `b91bcee6` (`VoxelRegion` + a lending `rows()` walker whose GAT is load-bearing, since a row is a borrow of the source at unit stride and a gather into reused scratch otherwise), with the allocation clause **measured**: 3 allocations / 1,048,648 B for the rewritten filter over a 64³ volume, 72 B above the output buffer, against 2,097,152 B for one whole-volume copy. The `<=2 accessors` and `one transform family` clauses are **deliberately not attempted** at 681 and 22 sites — a partial pass leaves exactly the compat shims the standards forbid — and are argued in ADR 0019's Deviation section. | [arch] [major] | Seam clause met. Remaining consolidation tracked as its own increments. |r API**, and ritk contains zero GATs across 1771 files. The only routes to pixel data are a fallible whole-buffer `data_slice()` or a whole-volume copy, so every filter takes the entire flat buffer or clones. Downstream: 7 parallel data accessors, 3 parallel coordinate-transform families, and three heap allocations **per output voxel** in `interpolation/.../linear/mod.rs:124-126`. | [arch] [major] | A lending seam with `type Item<'a>`; ≤2 data accessors on `Image`; one coordinate-transform family; a rewritten filter shows no whole-volume copy under dhat |
| ATLAS-RITK-TRANSFORM-DIRECTION-081 | **Eight coordinate transforms silently ignore direction cosines, so they are wrong for any oblique volume.** Found inside ATLAS-RITK-VIEWS-047 while counting duplication: of 17 index↔physical transform implementations across 22 sites, **8 are direction-free** — `marching_cubes.rs:161`, `csd.rs:1002`, `iterative_inverse_displacement.rs:75,77,231,233`, and `inverse_displacement.rs:137,334`. They compose origin and spacing but drop the direction matrix, which is the identity only for axis-aligned acquisitions. Clinical CT and MR are routinely oblique, so these produce plausible, silently displaced geometry rather than an error. This is a **correctness** defect that was hiding inside a consolidation item, and it outranks the consolidation; ADR 0018 already unified the single-point pair, so the seam to route them through exists. | [major] | Every index↔physical transform applies the direction matrix, or documents in its own Rustdoc why its caller guarantees an axis-aligned volume. One regression test per fixed site uses a deliberately **oblique** direction matrix and asserts against a hand-computed physical coordinate — each must fail on the parent commit, since an axis-aligned fixture cannot distinguish the two implementations. |
| ATLAS-LETO-TILES-048b — **closed 2026-08-18** | **The trait had no lending role to protect, and most of this row was already stale.** `Tiles` yields views borrowing the *parent slice*, not the iterator, and has implemented `Iterator`/`DoubleEndedIterator`/`ExactSizeIterator` since that was corrected; the only `impl LendingIterator` in the entire stack was a fixture inside leto's own test module, written to prove the trait compiled — a public seam whose sole implementor exists to justify it. Deleted in leto `1402668` (ADR 0026), module renamed `iter::lending` → `iter::tiles`. **Steps 1–2 of this row were done before work started** (kwavers `8c232e4a8`), and **`count_remaining()` was never called by any consumer** — only by leto's own test — so the `.count()`-vs-`len()` migration decision it framed was moot; the mapping is documented anyway. **CFDrs named the trait in three places, not one, and two claims were fabricated:** two appendices asserted `cfd-2d::stencil`/`cfd-3d::stencil` consume `LendingIterator` and a **`TileStreaming`** trait that has never existed in leto, against a repo whose source contains zero occurrences of either symbol. Corrected in CFDrs `c5199e15` and kwavers `b71fcc219`; `helios/docs/book/appendix_glossary.md:176` carries the same `TileStreaming` fabrication and is filed separately. semver-checks reports `trait_missing` at all four export paths plus `module_missing`, the intended `[major]`. leto nextest **883/883** (this row's 878 was stale). | [major] | Met. | ATLAS-LETO-TILES-048a |
| ATLAS-APOLLO-API-050 — **closed 2026-08-18** | **Landed in apollo `38192bed` (0.26.0 → 0.27.0): `api/` 140 → 71 public fns, `_typed` oracle 0.** Twin-equivalence was proved mechanically, not by eye — 59 pairs delegate at `<f64>`, and the 10 hand-monomorphized copies were normalized and matched token-for-token, **0 unproven**. Counts corrected: **69** pairs plus 2 orphan `_typed` fns, not 68; the AVX split is **2941** lines, not ~2300, and this row missed a further 1240 in `stockham/precision/`. Its root-cause diagnosis was also wrong: `eunomia::RealField` heads a correctly layered chain reaching 42 api bound sites, and both traits it cited as evidence of forking are misread — `StockhamPrecision` is a ZST strategy marker never used as a scalar bound, `PlanCacheProvider` is a supertrait extension. ADR 0038 fixes **two** bounds deliberately (`MixedRadixScalar` for arithmetic f32/f64, `PlanCacheProvider` for f16/f32/f64 storage); a unifying `FftScalar` was rejected because it either drops f16 storage or forces f16 into a seam with no f16 impl. **The `precise`/`reduced` clause was refused with evidence and that refusal is accepted:** they are not a scalar fork but different fused stage sets over different vector geometry (f64 packs 2 complex/YMM with one `permute2f128`; f32 packs 4 and needs a two-stage transpose, and its `groups == 1` leaf is 128-bit SSE with a scalar tail where f64's has none), so merging needs a SIMD-vector seam first — filed as `APOLLO-AVX-SEAM-050A`, with the real scalar fragmentation (8 sealed two-impl traits over `Complex64`/`Complex32`) as `050B`. The collapse exposed two latent defects: `ifft_3d_array_into` was **inverted** against its 1-D/2-D siblings, and the deleted `f64` wrappers were masking a genuine ambiguity (`PlanScalar` is `f32` for both `f16` and `f32`). Equality is **bitwise by construction** — the retained fn is the same code object the wrapper called — so no tolerance is quoted; a manufactured epsilon would have been ritual. Consumer half landed as kwavers `59f44bf51`. nextest 1005/1005. clippy is red at HEAD **independently** (44 `unfulfilled lint expectation` sites, because clippy 1.97 fixed the false positive those pins target) — isolation run with `-A` is exit 0; filed as `APOLLO-LINT-EXPECT-ROT-001`. **Original text:** `apollo-fft/src/api` carries 140 public fns of which **68 are exact concrete/`_typed` twin pairs**, and `stockham/avx/` forks the scalar dimension as a *directory pair* (`precise/` Complex64 vs `reduced/` Complex32, ~2300 lines) using quality labels the naming prohibition bans. Root cause: no single scalar seam — `eunomia::RealField` appears twice in 834 files while 10+ parallel scalar-role traits exist. | [major] | ADR selects one scalar seam; `rg 'pub fn \w*_typed' crates/apollo-fft/src/api` → 0; no `precise`/`reduced` directories |
| ATLAS-MOIRAI-ORDERING-052 - **claimed 2026-08-21 by Atlas integration; lane worktrees/moirai-seqcst-relax, branch fix/moirai-seqcst-ordering-ratchet** | Baseline audit found 624 production atomic sites with 10.1% carrying an ordering justification and high-strength ordering concentrated in executor/MPMC paths. The MPMC waiter model landed in `2ea17bb`; the SPSC ring model and hosted clean-checkout gate landed in `ac111b3`; the async executor wake-dedup model and Relaxed `is_queued` demotion landed in `fd517fe`; the PAL reactor stop-flag reduction landed in `8830f1b`; connection-pool reservation accounting landed in `f766c6d`. The remaining residual is the broader justification ratchet and production `SeqCst` reduction; no claim of closure is made. | [patch] | Justification coverage ≥ 90%; production `SeqCst` ≤ 20; the MPMC, SPSC, async wake-dedup, reactor stop, and reservation protocols remain green with stated bounds |

`ATLAS-MOIRAI-BOUNDED-051` is closed in provider commit `2ea17bb`, carried
by default `e972174`. The facade's discoverable `Moirai::channel()` now calls
the bounded constructor at `DEFAULT_CHANNEL_CAPACITY`; the explicit
`moirai_core::channel::unbounded` escape remains documented because it is a
deliberate, bounded-use-case exception. The provider's
`bounded_channel_refuses_to_grow_and_blocks_the_producer` and
`default_channel_capacity_bounds_the_queue` tests pass under nextest. The
original grep oracle was corrected: the explicit unbounded path is named in
documentation, while the default source path is bounded.

`ATLAS-MOIRAI-CACHELINE-053` is also closed in provider commit `2ea17bb`,
carried by default `e972174`. The duplicate six-definition premise was partly
wrong: transfer/cache-line granularity and destructive-interference padding
are distinct contracts. `moirai-utils` now owns both values, derives all
padding from `DESTRUCTIVE_INTERFERENCE_SIZE`, and pins the relationship with
compile-time assertions. The focused provider tests for neighbour separation
and the target's 64/128 distinction pass under nextest. The acceptance target
of one constant at 128 would have broken prefetch strides and chunk widths, so
the residual is reclassified as closed design correction rather than a live
defect.

`ATLAS-LETO-TILES-048a` is closed in provider commit `7f80044`, carried by
default `143696d`. `Tiles` now yields parent-borrowed `ArrayView` items through
the standard `Iterator`, `DoubleEndedIterator`, and `ExactSizeIterator` seams;
constructor validation proves every tile origin is addressable, and the
ragged 3x5-to-2x2 test covers clipped shapes and values. `048b` remains open
because deleting the public `LendingIterator` seam still requires the
kwavers/CFDrs consumer migration.

## Tier 3 — mechanical floor and stack hygiene

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-LINT-FLOOR-054 — **closed 2026-08-14** | **17 of 25 members have no `[workspace.lints]`.** Where a floor is declared it is then nullified: CFDrs correctly inherits `unwrap_used`/`print_stdout`/`print_stderr`/`dbg_macro` at deny in all 12 manifests, against **288 crate-level `#![allow]` and 5 `#[expect]` repo-wide, none with a ratchet reason** — which is why 402 library print sites survive a deny. coeus has 117 allow lines with **zero** `reason=`. | [patch] | **Complete: 25 of 25 members deny `clippy::pedantic`, none at `warn`, none without** - from zero at sweep start. Every floor carries a grouped allow-list recording total and production counts per class, so debt is measured rather than tolerated; blanket crate-level `#![allow]` is **zero stack-wide** (CFDrs 299 -> 0, apollo 47 -> 0, ritk 34 -> 0, coeus 22 -> 0, kwavers 13 -> 0), and surviving suppressions are `#[expect(..., reason = "ratchet <id>")]` that expire with their last site. **Two premises in the outcome column were wrong:** several "missing `[workspace.lints]`" members are single-package repos where a package-level `[lints]` table is the only correct home, and most members' CI already passed `-D warnings`, so `warn` was already a hard floor there - the promotion mattered locally, not in CI. **The exception was CFDrs, which had no clippy step in CI at all**, plus ten crates carrying in-source `#![warn(clippy::pedantic)]` that overrides manifest `--allow` flags and made its allow-list inert; a `lint` job was added in `c9073496`. **The floors paid for themselves in real defects:** a reachable hang in kwavers' driver manifest parser (unbounded `(len()..)` range, verified by falsification - reverting the fix times the new regression test out at 60s), reachable `Instant` panics in kwavers' clinical safety monitor and moirai's registry, an overflowing manual ceiling division in hermes, case-sensitive extension matching in hephaestus (`.DLL`) and kwavers (8 sites routing `.NII`/`.DCM` to "unsupported"), 353 dead imports in apollo behind a blanket allow, three ritk `#[expect(dead_code)]` masking genuinely dead production code, four discarded `SolveReport`s in CFDrs, and a CFDrs test file holding two empty `#[ignore]`d functions. **Three mechanics worth reusing:** a file-level `#![expect(clippy::unwrap_used)]` in a `src/` file whose unwraps are all `#[cfg(test)]` fails as `unfulfilled_lint_expectations`, so those need `#![cfg_attr(test, expect(...))]`; a member with its own `[lints.rust]` table cannot also inherit; and publishing a member's `[lints] workspace = true` before the root table exists breaks manifest parsing for the whole stack through the overlay. Census at `warn`, never `deny` - at `deny` clippy aborts each crate on its first error and undercounts. |
| ATLAS-COEUS-LINT-RATCHET-097 — **closed 2026-08-17 — already merged** | The stale floor finding is closed by Coeus PR #334, merged at provider default `a8ea12eb`. The production conformance scan at the lint-ratchet head reports `allow_sites=0`; exact-head hosted Backend parity run `31989331059` passes, and Atlas already records `a8ea12eb`. The stale lane claim is released without source edits. | [patch] | Production `#[allow(...)]` residue is zero at the merged default; provider and Atlas exact-head evidence is recorded. |
| ATLAS-CACHE-FORK-055 | **Mostly stale.** Only 2 trivially small target dirs remain (athena 1.7 MB, harmonia 1.4 MB — mdbook output, not build caches). All other 23 repos have zero target directory. Deleted in this sweep. | [patch] | Closed — 58.9 GB fork state reduced to near-zero |
| ATLAS-GITLINK-DRIFT-056 | **24 of 25 submodules are checked out off the commit atlas records** (only gaia matches), and 11 sit on `codex/*` or feature branches. **The drift direction is uniform: the recorded gitlinks are AHEAD of the working trees** — athena's gitlink is 3 commits ahead of HEAD, harmonia's 2, horae's 6, hyperion's 5, and leto's tree is 17 behind both `origin/main` and its pin. These are members behind atlas, not atlas behind members, so every local verification run tests superseded state. Two sub-cases need opposite handling: athena and harmonia sit on branches with **zero** unique commits (exhausted, deletable — re-point to `main`), while horae and hyperion each carry small real deltas that are green and mergeable now, hyperion's including an actual parallel-test-race fix (`35006fd`). | [patch] | Per member: exhausted branches deleted and re-pointed to `main`; real deltas merged and the gitlink advanced; a committed check fails when HEAD ≠ gitlink without a recorded reason |
| ATLAS-ROOT-SPRAWL-057 — **closed 2026-08-14** | Meta-root held 7 unfiled report-genre files. **Not all are deletable** — `scripts/check_mdbook_links.py:15,53,66,99,181,194,565` and `fix_link_depth.py:2` cite `MDBOOK_*.md` as the normative Pattern A–F taxonomy, `scripts/tests/test_smoke_fixture.py:34,46` reads `parity_artefacts/smoke_test_filters` as a live fixture, and `.github/workflows/docs.yml:19,20` path-filters both. `PATH_DEP_AUDIT_001_ENTRY.md` is a duplicate of the board entry at `backlog.md` with 367 unique lines that must merge first. | [patch] | All four clauses verified. The tracked root manifest is now exactly `README.md`, `CHANGELOG.md`, `backlog.md`, `checklist.md`, `gap_audit.md`, `Makefile`, `pytest.ini` and the four dotfiles — no report-genre file remains. The mdBook taxonomy lives under `docs/mdbook/` with zero `MDBOOK_` citations left in `scripts/*.py`. The smoke fixture moved to `scripts/tests/fixtures/smoke_test_filters/` in `42d1607`, all seven citations re-pointed (two test constants, four `docs.yml` sites, and the prose in the fixture README, its two chapters, and `docs/mdbook/detector-parity.md`); the move broke the fixture's own `../../../` root-relative links and the test caught it, re-depthed to `../../../../../` with each of the four targets resolved on disk. `pytest scripts/tests/` 183 passed / 74 subtests, the workflow's verbatim command reports `FILE_MISSING : 0`, and the pre-commit hook's stack-wide check passed all 24 books at zero. **Deliberately out of scope:** the rest of `parity_artefacts/` is the parity stream's archive, cited from two `docs/mdbook/` chapters, and this board already records its disposal as that stream's closure increment rather than a coordinator's unilateral commit. |
| ATLAS-ADR-GOV-058 — **closed 2026-08-14** | **Corrected against `scripts/adr-index.py check`, which is authoritative — my earlier grep-based count was wrong.** The meta-repo's own ADRs and index are **clean**. At the merged provider defaults, **9 of 24 member indexes are stale or missing**; remaining member anomalies include non-canonical status headers, duplicate or missing ADR numbers, and index drift in Asclepius, Coeus, Gaia, Harmonia, Helios, Horae, Kwavers, Melinoe, Mnemosyne, and Tyche. The generator already exists and reports all of this; what is missing is the burn-down plus a CI gate on `check`. Hyperion, Iris, Proteus, Aequitas, Horae, Eunomia, Themis, Ritk, Leto, Hephaestus, and Apollo slices are landed as their corresponding `ATLAS-ADR-GOV-058-*` entries; the remaining member anomalies stay open. | [patch] | **All four clauses met.** 62 anomalies burned to 0 — 27 status casing, 27 non-canonical status, 7 duplicate number, 1 missing status. (The "9 stale/missing indexes" in the outcome column did not reproduce: `check` already exited 0 on that class.) `check` now exits 0 with **zero stdout**, verified independently of the burn-down agent; `generate` run twice more is a silent no-op; an independent scan finds no repeated ADR number in any member; `scripts/tests/test_adr_index.py` still passes. Landed as `3775ac7` (asclepius), `d30a167` (harmonia), `3db1090` (helios), `7e27727` (tyche), `7d671c0e` (coeus), `f0cc9c9a8` (kwavers), `be2d19d` (mnemosyne); apollo's two were fixed by a peer mid-run. The two supersessions were decided per file, not by rule: kwavers 037 was **rewritten in place** because grepping ADR 040 for `FeatureNotAvailable`/`SimulationRunner`/`runner` returns zero hits, so 037 still solely owns the no-zero-arrays adapter contract; mnemosyne 0002 was **deleted** because ADR 0003 removes `WgpuStagingBackend` outright and no symbol from it survives anywhere in `.rs`. CI gate added to `atlas-conformance.yml` in `af3532e`, gating on exit code **or any stdout** — `check` exits 0 for duplicate numbers and bad statuses, so an exit-code-only gate would have caught none of the 62. **Two findings filed rather than fixed:** `repos/moirai` has no `docs/adr/` directory so the checker never scans it at all (see ATLAS-CONSUS-ADR015-076, respecified), and the pre-existing ratchet step's `… \| tee` masked its own exit status, fixed in the same commit. |
| ATLAS-KS9-SUPERSEDED-059 — **closed 2026-08-14** | `backlog.md` `[KS-9]` stood **done** asserting the decision to *retain* `hephaestus-metal`, superseded by Accepted ADR 0047 which retires it — the board asserted both positions. Its recorded rationale ("would be a breaking public-surface change") was also a prohibited tiebreaker. Separately: ATLAS-ARCH-011 needs **nothing from hephaestus** — removal was executed and verified green, then reverted solely for `repos/coeus`; it unblocks via ATLAS-SUBSTRATE-002. | [patch] | Both oracle clauses verified met at `repos/hephaestus` HEAD (committed, not working-tree state): `backlog.md:3187` carries the dated **Revision 2026-08-14** note pointing at ADR 0047, and additionally records that the crate never owned a native Metal path — `MetalDevice` is a newtype over `WgpuDevice::try_metal` with zero native Metal API calls across 5 449 lines — and that the breaking-surface rationale is a prohibited tiebreaker. ATLAS-ARCH-011's dependency reads `ATLAS-SUBSTRATE-002` with the blocker narrative naming `repos/coeus`/`coeus-metal`; hephaestus appears nowhere as a blocker. |

### ATLAS-APOLLO-PRINT-098 — **closed 2026-08-17 — premise false** [patch]

The hosted `apollo/print_dbg: 6 -> 9` finding is not an Apollo library defect.
The eight call sites are benchmark executable targets, and
`BenchmarkSuite::emit` is their shared output boundary; deleting it would break
real benchmark artifacts. The Atlas scanner classifies only `main.rs` and
`bin/` paths as executable, so it incorrectly counts `benches/` output as
production library output. No Apollo source change is authorized by this
finding; the instrument correction is tracked separately.

## ATLAS-HEPHAESTUS-CONFORMANCE-101 — attention structure ratchet closure [patch, closed 2026-08-17]

Hephaestus source `702eba8` split the provider attention contract's shared
download assertion into `src/attention/assertions.rs`, reducing the exact
provider conformance scan's `oversized_files` count from 39 to 38. The source
merged at provider default `4714b8c`; the PM closure merged at `300b9e9`.
Exact-head CUDA `32027773223`, ROCm `32027773309`, WGPU `32027773340`, and
Metal `32027773250` pass. The direct Coeus attention cutover remains open under
the provider's `HEPH-ATTENTION-PROVIDER-1` item. Atlas advances the gitlink to
the PM closure without touching the peer-dirty primary checkout.

## ATLAS-RITK-CONFORMANCE-101 — diffusion binding structure ratchet closure [patch, closed 2026-08-17]

RITK source `81f510f6` split the diffusion Python binding manifest from its
`PyDiffusionMaps` and fitting implementation leaves, reducing the exact clean
provider `manifest_implementation` count from 112 to 111. The source merged at
provider default `7ae4b69b`; PM closure `62efbd79` merged at `f23a6acd`. The
provider-owned Rust, formatting, clippy, dependency-alignment, three-platform
Nextest, Python 3.9–3.13, and wheel smoke gates are green in
`32026464996`, `32026464796`, and PM run `32028306807`/`32028306813`.
The external `recurseml/analysis` result is report-only. Atlas advances the
gitlink to the PM closure without touching the peer-dirty primary checkout.

### ATLAS-CONFORMANCE-BENCH-099 — closed 2026-08-17 [patch]

Corrected `scripts/atlas-conformance.py` so Rust files under `benches/` are
classified as executable targets for `print_dbg` and related production-only
classes. The corrected instrument also recognizes exact test regions,
executable support modules, target-cache markers, and literal or manifest-rooted
`include!` edges. The focused scanner suite passes 37 tests; the baseline
records Apollo's clean orphan count as 0; hosted run `32031997052` passes the
exact delivered root with 0 regressions and 23 tightening candidates. The
tightening candidates are non-regressing follow-up cleanup, not a classifier
failure.

Takeover owner: Atlas session. The existing dirty classifier/test diff was last
written 2026-08-16 21:52–21:37 -0400 with no newer board claim or commit; its
target-fork correction is retained and reviewed as part of this item.

## Tier 2b — small domain repos (athena, harmonia, horae, hyperion)

These four are the cleanest in the stack on every mechanical axis — zero `dyn`
in any `src/`, zero fake-generic casts, zero `todo!()`, zero non-test `unwrap`,
`unsafe_code = "forbid"` and `missing_docs = "deny"` throughout, and both
LICENSE texts present and matching the manifest in all four. The findings are
about documentation truth and numerical evidence, not debt.

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-ATHENA-UNDOC-066 — **closed 2026-08-14** | **athena ships two undocumented solver families.** BiCGStab (575 lines) and LSQR (487) are implemented and publicly re-exported from `athena-core/src/lib.rs`, yet appear **zero times** in the README, whose headline (`:5`) calls PCG and GMRES "its complete vertical contracts". Compounding it, the architecture tree names a crate that does not exist (`:62` `athena-wgpu` vs the real `athena-hephaestus`), a feature that does not exist (`:71` `wgpu` vs the real `accelerator`), and asserts a 500-line ceiling (`:69`) that BiCGStab breaks. | [patch] | `rg 'athena-wgpu' README.md` → 0; README documents BiCGStab and LSQR; the line-count claim is removed or true per `wc -l` Verified 2026-08-14 at athena HEAD: `rg 'athena-wgpu' README.md` = 0, BiCGStab and LSQR both documented, and the line-count claim now names `bicgstab/algorithm.rs` (575 lines) as the sole stated exception. |
| ATLAS-BOOK-PLACEHOLDER-067 — **closed 2026-08-14** | **Placeholder chapters are shipped as books.** athena has 6 chapters and harmonia 3 — every one is the 3-line string `*Chapter prose deferred.*`. A placeholder chapter is documentation's mock: a chapter exists when its teaching content does. Separately, the shared Pages callers default `mdbook-test` to `false`, so books without a compiled-sample gate can rot. | [patch] | No `Chapter prose deferred` anywhere; athena and harmonia now contain source-grounded prose. The placeholder half is closed: athena's six stubs plus a seventh LSQR chapter landed in `39b6f0b`, harmonia's three plus its two-line introduction in `10e15ae`, and the stack scan is zero. Sample-gate work remains tracked independently in ATLAS-PUB-005; callers are not represented as tested unless they pass `mdbook-test: true`. |
| ATLAS-ATHENA-KRYLOV-070 — **closed 2026-08-14** | `gmres/workspace.rs:15-16` holds the Arnoldi basis as `Vec<B::Vector>` — on Leto that is `2·RESTART+1` scattered allocations, while every scalar array in the same struct is already flat (`hessenberg` is one `Vec<Scalar>` with an index fn). The only pointer-scattering instance found across these four repos. Allocated once at construction and natural per-buffer on WGPU, so this is a CPU-side layout defect, not a hot-loop allocation. Also: non-convergence returns `Ok(SolveReport)` with `Termination::MaxIterations` rather than a typed error, `SolveError` carries no residual history, and stagnation/divergence detection is absent entirely. | [minor] | `Vec<B::Vector>` gone from `gmres/workspace.rs` behind the existing `KrylovBackend` seam; the existing allocation-stability and f32/f64 contract tests unchanged and green; a stalling operator yields a `Termination::Stagnated`-class value with non-empty history Closed 2026-08-14. The layout half landed earlier in `d3a4afe` behind `KrylovBackend::VectorBlock`; the only remaining `Vec<B::Vector>` in `gmres/workspace.rs` is a doc comment explaining the type is no longer that. The correctness half landed in `39b6f0b`: `Termination::Stagnated`/`Diverged` detected per restart cycle against a derived floor `sqrt(n)*eps*||b||`, with the two rejected sub-requests argued in ADR 0004. |

## Tier 2c — small domain repos (iris, proteus, asclepius, tyche)

Two premises this sweep started with turned out to be **false and are recorded
as cleared, not as work**: asclepius's Coeus adapter is genuinely one-way
(verified in the manifests, in the imports, and in the reverse direction — no
`[arch]` defect), and tyche's reported "23 production unwraps" are every one of
them inside `///` doc examples, under a workspace-wide `unwrap_used = "deny"`
that makes a production unwrap uncompilable. The second was an instrument
defect and is now fixed (see the doc-comment correction below).

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-LICENSE-STUB-071 — **closed 2026-08-14** | **Three repos ship a stub where the Apache-2.0 text belongs**, while their manifests declare `MIT OR Apache-2.0`: iris and asclepius carry a 13-line short-form notice, proteus a 17-line header-plus-notice. Only tyche has the real 199-line text. iris and asclepius are `publish = true`, so two crates ship to crates.io under a license whose terms they do not include. Related, found separately: `kwavers-gpu` declares `MIT OR Apache-2.0` while the repo ships only an MIT `LICENSE` and every sibling crate is MIT — a per-crate override that is either a mistake or needs the second text; and gaia's MIT file is named `LICENSE` rather than `LICENSE-MIT`, so the pair is asymmetric. This is a legal defect, not a style one. | [patch] | Each `LICENSE-APACHE` contains `END OF TERMS AND CONDITIONS`; every crate's declared `license` matches the texts its package ships; `cargo package --list` includes them Verified 2026-08-14: iris, asclepius, proteus, tyche and gaia each ship a `LICENSE-APACHE` containing `END OF TERMS AND CONDITIONS`, and gaia's MIT file is named `LICENSE-MIT`. The `kwavers-gpu` outlier declaring `MIT OR Apache-2.0` against an MIT-only repo now inherits `license.workspace = true`. Residual, filed separately: no kwavers crate packages a license *text* at all, since the root `LICENSE` is outside every package directory. |
| ATLAS-REGISTRY-INVALID-078 — **closed 2026-08-14** | **Two kwavers manifests carried metadata crates.io would reject**: `kwavers` declared 6 keywords against the 5 cap, and both `kwavers` and `kwavers-python` used `"medical"`, which is not a registered category slug. `cargo publish` fails on either. Fixed in passing for kwavers via a new shared `[workspace.package]`; the class needs a stack-wide check, because nothing currently validates registry metadata before a publish attempt. | [patch] | A committed check validates keyword count and category slugs against the crates.io registered list for every publishable crate; `cargo publish --dry-run` clean stack-wide Closed 2026-08-14 by `cbeef06`: `scripts/atlas-registry-metadata.py` validates keyword count/length/charset, category count and slug, description, license and readme resolution for every publishable crate, with the crates.io taxonomy fetched and cached rather than hardcoded. Stack is clean at 251 manifests, 0 violations. |
| ATLAS-TYCHE-README-075 — **closed 2026-08-18** | **Five of the six reported defects were already stale** (`a897d32`, `0ee9fe5`): line 31 already reads `tyche = { package = "tyche-uncertainty", version = "0.2" }`, so `use tyche::…` is correct given it; `:159` already used `-p tyche-uncertainty`, which does exist (`name = "tyche-uncertainty"`, `[lib] name = "tyche"`); `:24-25` said "remain unreleased", which `publish = true` does not contradict; Morris and Sobol were already described as existing; both satellite manifests already carried full metadata. **Two real defects remained and are fixed in tyche `631f81a`:** the verification block advertised `cargo bench …` and `cargo deny check`, **neither of which `ci.yml` ran** — a block telling readers "this is what CI runs" while naming commands CI does not run is this tier's own evidence defect — so a bench smoke step (`-- --test`) was added to `ci.yml` and matched, and `cargo deny check` moved into prose naming the `supply-chain` job's pinned action; and the documented release tag `crate-tyche-core-v<version>` did not match `rust-release.yml`'s package-generic `crate-<package>-v<version>`. Oracle checked mechanically — commands extracted and string-compared — **8/8 verbatim, 0 missing**; `rg '\-p tyche ' README.md` → 0. **Original text:** The dependency line is underivable and one command names a package that does not exist. The registry name is `tyche-uncertainty` while `README.md:31` shows `use tyche::…`; `README.md:159` runs `cargo run -p tyche --example …` where CI uses `-p tyche-uncertainty`. `README.md:24-25` says the adapter and facade "remain private", contradicted by `publish.workspace = true` on all three; `:175` lists Morris and Sobol as future work though both ship. `tyche-moirai` and `tyche-consus` publish with `readme`/`keywords`/`categories` missing. **ATLAS-TYCHE-MULTIOUTPUT-017 did land — on `main`, not in the checked-out worktree**, which is 5 commits behind; on `main` `sensitivity.rs` is 672 lines, past the target. | [patch] | Every command in the README verification block appears verbatim in `ci.yml`; `rg '\-p tyche ' README.md` → 0; both manifests carry complete metadata |
| ATLAS-CONSUS-ADR015-076 — **relocation landed 2026-08-18; consus citations held back** | **Landed:** the decision now lives in the meta-repo as ADR 0045 (`f808d6f`), Accepted, with moirai's §ADR-015 reduced to a pointer that says it is not a second current record; and `repos/moirai/docs/adr/` now exists (`035ba78`), so **the governance checker scans moirai for the first time** — that gate hole mattered more than the record. The row's "P0–P5 substantially shipped" did **not** survive contact with the tree and ADR 0045 records the real per-phase state: P0 partial (Windows leg unverifiable, moirai CI is ubuntu-only), P1 narrower than described, P2 **missing redirect handling** and idle eviction, P3 with no env/`~/.aws` credential resolution, P5 open — and **neither S3 backend is the default**, so P5's "flip the default" has no default to flip and needs respecifying. `docs/adr-015-checklist.md` is unreliable: it claims P0–P4 done with every box unchecked, and its cited P0 commit is actually a Host-header fix. **Held back, and why:** the nine consus citation edits plus two `#[allow]`→`#[expect]` conversions are complete and verified (consus fmt 0, clippy 0, `--features s3` and `s3-moirai` both 0, nextest 480/480 on the two crates) but **not committed** — `repos/consus` is sitting in a three-day-stale abandoned interactive rebase at a detached HEAD, stopped after picking a peer's commit, so committing there would fold this work into their commit under their message. The diff is preserved at `D:\tmp\consus-adr015-patch\adr015-citations.patch` (8 files) and applies once the rebase is resolved. One conversion is worth keeping: `MockS3Store` could not take a plain `#[expect(dead_code)]` because the lint fires in the lib build but not under `cfg(test)`, so the blanket allow was masking a conditionally-firing lint; it needed `#[cfg_attr(not(test), expect(…))]`. | [patch] | Relocation met. Consus citations pending the rebase; 31 moirai records pending a renumber (six duplicate-number collisions). | **Superseded framing:** premise false; respecified 2026-08-14 | **The original premise was wrong and the drafting instruction it implied would have caused the defect it meant to fix.** ADR-015 exists: `repos/moirai/docs/adr.md` §"ADR-015: Native HTTP/S3 Transport Stack" (2026-06-02) decides the consus side explicitly ("In consus (storage backend, NOT in Moirai): consus S3 client — rebuild on `moirai-http`") and defines the P0–P5 phases the `P4`/`P5` comments cite. Writing a retroactive consus `0015` would have created a **second current record for one decision**, which governance forbids. There are **nine** citation sites, not eight — the ninth is `repos/consus/.github/workflows/ci.yml:235`. The real defects are three, all different from the one filed: (1) **the record is in the wrong place** — it governs a cross-repo contract (moirai transport ↔ consus S3) but lives inside moirai's monolithic `docs/adr.md`; `repos/moirai` has no `docs/adr/` directory, so `scripts/adr-index.py` **never scans moirai at all** and its ADRs are invisible to the gate now in CI; (2) **the status is stale** — it reads `Proposed (requires sign-off before P1 implementation)` while P0–P5 are substantially shipped across `moirai-tls`, `moirai-http`, and all nine consus sites; a Proposed ADR governing landed code is a live governance defect; (3) `consus-zarr/src/store/s3.rs:135,488` justify `#[allow(dead_code)]` by citing "ADR-015 P5" — the phase is genuinely still open so the justification is honest, but the floor wants `#[expect(…, reason = …)]` so the suppression self-expires when P5 lands. | [patch] | This is a decision-**relocation** item, not a drafting one: ADR-015 is promoted to a meta-repo `docs/adr/` record with status Accepted plus a dated revision note recording P0–P5 delivery; all nine consus citations repoint at that path; the two `#[allow(dead_code)]` become `#[expect]` with a ratchet reason; `repos/moirai` gains a `docs/adr/` directory so the checker sees it, and its monolithic `docs/adr.md` splits into per-decision records. **No new consus `0015` is written.** |

**ADR-0045 P4 implementation — 2026-08-18:** the missing comparative benchmark
is now implemented in the existing Criterion-enabled `consus-zarr` benchmark
surface. It measures identical ranged reads through `S3MoiraiReader` and the
legacy `S3Reader` against the same live endpoint/object/range, uploads a
deterministic 1 MiB object outside the measured region, and publishes the
Criterion report as a CI artifact from the MinIO job. The mixed Consus lock
was repaired in standalone form with `RUSTC=rustc RUSTDOC=rustdoc python
scripts/atlas-lock-form.py regenerate consus`; lock status is now `HEAD ok /
worktree ok`, isolated locked benchmark compilation passes outside the Atlas
overlay, and the in-process differential passes 2/2. Hosted run `32178624452`
at Consus commit `d15bf793cb4dd86bbb53b966ea5ce2884dd8cab0` passes the MinIO
correctness lane, benchmark, and 90% parser gate. Its pinned MinIO baseline
cell (1 MiB object / 256 KiB range) records native median `862,063.015 ns`,
legacy median `828,983.683 ns`, and native/legacy throughput `0.9616` against
`0.9000`; artifact `9340113561` is retained at
`https://github.com/ryancinsight/consus/actions/runs/32178624452/artifacts/9340113561`.
The two additional object/range cells required by the former P5-A gate remain
outstanding, but the performance result is no longer an adoption gate: the
product decision is that Consus packages must not connect to third-party online
storage. The next breaking release therefore removes the native and legacy S3
modules, package-facing features/APIs, production dependencies, and hosted
MinIO benchmark lane; applications must own online-storage adapters outside
Consus. The hosted result remains historical evidence, not authorization for a
default flip or an in-package compatibility window.

**Async ownership correction (2026-08-18):** the Consus release-preparation
branch removes its `async-io`/`async-traits` feature and Tokio-backed async
cursor/tests. Async HDF5 now consumes the Moirai-owned
`moirai_async::io::{AsyncReadAt, AsyncLength}` contracts and Moirai executor;
Consus retains only synchronous I/O abstractions. The positioned API is locally
verified against the clean Moirai checkout, but the provider revision must be
published before a hosted locked Consus gate can claim the migration.

| ATLAS-LOCK-CONVENTION-079 — **closed 2026-08-18** | **`scripts/atlas-lock-form.py check` now exits 0 across all 27 committed locks**, from 33 violations in 10 members; nine repaired and pinned. Convention recorded as ADR 0044 (standalone form: a `source = "git+…"` for every git dependency the lock resolves, no `[[patch.unused]]`), argued from the lock's purpose and **falsified rather than asserted** — `cargo metadata --locked` on a stripped hermes from outside the tree exits 101, which is every CI job, clean checkout and publish sandbox. **This row's instrument was wrong:** counting `git+` lines misses eunomia, iris and the melinoe fixture (residue with zero git sources) and falsely flags members with no git deps; the check instead quantifies over the git dependencies a lock actually resolves, so zero-git-dep members pass and idle `[workspace.dependencies]` rows that never reach the lock are ignored. 22 tests including an end-to-end pair that **exits 1 on a stripped lock and 0 on a standalone one**; writing them found two real bugs in the tool (`restore` would have reverted a *repair*, and its eligibility set missed transitive stripping under a patched parent). Churn is **prevented**, not documented: `restore` reverts only overlay rewrites and correctly held back apollo and kwavers, which carried a real re-resolve; a pre-commit hook blocks the offending `git add`, written and tested but deliberately **not installed**, since that mutates per-clone git config in trees five peers are using. CI step added to `atlas-conformance.yml`. Two findings: hermes, mnemosyne and tyche **regressed during this sweep**, two via commits titled "Remove stray root automation artifacts" — the lock rode along in an unrelated change, exactly the failure mode — and mnemosyne needed a second repair because a peer re-stripped it minutes after the first. **Original text:** The committed lockfile convention is not uniform, and the overlay silently rewrites 12 working copies. Counting `source = "git+"` lines, committed vs working: 14 repos committed the git+ form (kwavers 87, CFDrs 62, helios 59, ritk 51, coeus 48, apollo 36, hephaestus 33, leto 30, consus 24, gaia 22, tyche 20, hermes 11, mnemosyne 3, hyperion 3) while **11 committed the stripped form** (aequitas, asclepius, athena, eunomia, harmonia, horae, iris, melinoe, moirai, proteus, themis — all 0). Of the git+ group, **12 now have a stripped working copy** because a build ran under the stack overlay; only gaia and hermes still match. coeus is half-stripped (48 committed vs 7 working). A stripped lock cannot resolve a git dependency standalone, so committing that form breaks reproducible CI resolution — yet a third of the stack has it committed. Every "Cargo.lock modified" line in this sweep is this artifact, not anyone's edit. | [patch] | One documented convention; every member's committed lock matches it; a committed check fails when a lock is committed in the wrong form; the overlay's rewrite is either excluded from the working tree or documented as expected churn |
| ATLAS-MSRV-UNVERIFIED-077 — **closed 2026-08-18** | **All three open slices resolved.** Melinoe PR #18 merged at `689f562` raising rust-version 1.65 → 1.81; themis already declared 1.83.0 (exceeds requirement); mnemosyne at `098bc8e` hoisted to 1.95 with a gated MSRV CI job. **Prior description (melinoe REOPENED 2026-08-15):** The melinoe closure is no longer true, and the lint-floor work is what broke it. At `6e6a181` — the exact revision this row cites for the passing hosted Rust 1.65.0 run `31785253730` — `src/cell/reference.rs` contained **zero** `#[expect(` attributes, so that run was honest when it ran. `81d4f3d` ("Deny the pedantic floor and unwrap_used") then introduced them, and `#[expect(..., reason = …)]` requires **Rust 1.81** (`lint_reasons`), against a declared `rust-version = "1.65"`. An independent overlay-free check at a real 1.65.0 toolchain fails the *library* with 14 × `E0658: lint reasons are experimental`, in files the checker never touched; resolution also cannot complete, because the committed lock pulls edition-2024 dev-deps. **themis has the same shape** — `rust-version = "1.75.0"` with `#[expect]` in `src/topology/cpu/detect/*` — but no MSRV job, so nothing goes red and the false declaration is simply unobserved. The ratchet form is right and should not be reverted: `#[expect]` is what makes a suppression self-expire. The declarations are what is wrong, and this row's own oracle already allows the fix — "**or the floor is raised to what the code requires**". Determine the true floor per crate rather than assuming 1.81 is the only constraint. **Original text:** Melinoe and Eunomia slices closed 2026-08-14. Melinoe tracks a standalone lockfile and hosted Rust 1.65.0 all-target check (`31785253730` at `6e6a181`). Eunomia now has a hosted Rust 1.95.0 all-target/all-feature gate (`31789001841` at `b6c3d9a`), an exact online package dry-run at default `84c82fe`, and Atlas pointer integration at the current provider default. Mnemosyne remains the only open portion. | [patch] | Each declared floor has a hosted build, or the floor is raised to what the code requires |

The closed Gaia, Iris, Proteus, and Asclepius rows were removed from the
active tables after source and hosted evidence were recorded in the landed
table above. Their provider scopes remain complete; the remaining rows are
not reclassified by this cleanup.

**Eunomia closure (2026-08-14):** provider PR #65 merged as `d252f968` with
the MSRV workflow; repository-owned Rust verification, supply-chain, and Rust
1.95.0 all-target/all-feature checks pass. Provider PM reconciliation PR #66
merged as `84c82fe`; the exact online `cargo publish --locked --package eunomia
--dry-run` packages and verifies 73 files at that default head. The Atlas
gitlink is advanced in this integration increment. `recurseml/analysis` remains
an external report-only failure; CodeRabbit was rate-limited on the PM-only PR.

**Melinoe closure (2026-08-14):** the current session owned the Melinoe
portion only: `.github/workflows/msrv.yml`, the tracked standalone
`Cargo.lock`, its provider PM records, and the declared `1.65` floor's locked
all-target gate. Hosted run `31785253730` passed at source head `6e6a181`; the
provider default advanced through PR #17 to `0bc287a`. The shared Atlas overlay
cannot serve as the MSRV oracle because peer-edited manifests in other
providers are newer than the historical compiler. Mnemosyne and Eunomia
remain separate provider scopes.

## ATLAS-CFDRS-CRLF-085 — CFDrs commits CRLF with no `.gitattributes` [patch] — blocked 2026-08-14

The repository stores CRLF line endings and has no `.gitattributes`, so any
tool that writes LF — rustfmt, a Python edit, most editors on non-Windows —
reflows whole files. During the scalar consolidation this turned a real 10k-line
diff into 128k lines until the endings were restored file by file, which is
both unreviewable and a merge-conflict generator for every concurrent agent.

`engineering_gates` requires `* text=auto` so every host hashes identical blobs;
the conformance scan already counts this as `gitattributes_missing`. CFDrs is
the case where the cost is now measured rather than theoretical.

**Acceptance oracle:** `.gitattributes` normalizes source to LF, the tree is
renormalized in one dedicated commit, and `gitattributes_missing` is 0 for
CFDrs.

**Status → blocked 2026-08-14; re-open trigger: the CFDrs working branch is
merged to `main` and no second lane is live.**

**Blocker re-verified 2026-08-18 and it still holds** — the trigger has not
fired. `worktrees/CFDrs-runtime-budget` is live on
`codex/cfdrs-backward-step-108`, and `origin` carries ten-plus branches
unmerged into `main`. Renormalizing the tree now would conflict with every one
of them, which is precisely the cost the item describes. Its scale is filed
separately as `-208`. The underlying defect was re-confirmed unchanged today:
`.gitattributes` still absent, `core.autocrlf=true`, and the same directory
still mixes stored endings — `crates/cfd-1d/Cargo.toml` LF against
`crates/cfd-python/Cargo.toml` and `crates/cfd-schematics/Cargo.toml` CRLF.

Confirmed and worse than filed.
`core.autocrlf=true` is set globally while committed blobs are *inconsistent*:
`crates/cfd-1d/Cargo.toml` is stored LF, `crates/cfd-python/Cargo.toml` and
`crates/cfd-schematics/Cargo.toml` are stored CRLF, in one directory. With
autocrlf on, `git add` LF-normalizes unconditionally, so a one-line edit to
either CRLF-stored file stages as a whole-file rewrite — measured while landing
ATLAS-CFDRS-GPU-DEFAULT-084, where a three-line change first staged as 238
changed lines. The workaround used there (`git hash-object --no-filters` plus
`git update-index --cacheinfo` to stage a CRLF-preserving blob) restores a
reviewable diff but is not a policy.

The renormalization itself is **not** safe to run now, for reasons the filing
did not anticipate. 1,702 of 2,411 tracked files are CRLF in the working tree,
so the sweep touches ~70% of the repository — and the checkout sits on the peer
branch `codex/cfdrs-legacy-approx-cleanup`, which is 2 commits ahead of and
**11 commits behind** `origin/main`, with a second live lane at
`worktrees/cfdrs-ci-workspace-rust` on `feat/cfdrs-ci-workspace-rust`.
Renormalizing there would conflict with both the unmerged `main` commits and
the sibling lane across every touched file. Creating `.gitattributes` alone is
also rejected as a half-measure: git reads it from the working tree whether or
not it is tracked, so it would start LF-normalizing files one at a time on
every subsequent `add`, producing the same churn as drip rather than as one
reviewable commit.

**Required sequence when unblocked:** land on `main`, not a feature branch —
add `.gitattributes` (`* text=auto`) and `git add --renormalize .` as a single
commit containing nothing else, with every lane closed or rebased across it.

## Deferred with a recorded reason

- **ATLAS-PRIVACY-NAMING-1** stays open and unchanged. `repos/leoneuro-rs` is a
  separate organisation's repository holding local commits `1b71a79` and
  `50bfcd9` on a branch whose remote is **gone**, so it carries unique unpushed
  work and must not be deleted. It is correctly gitignored; the violation is
  that it is *named* in board items, which is a rewrite of existing entries, not
  a tree change.
- **Detector residuals.** The `declared_cfg_test` fix does not yet recognise
  test modules gated through a `#[cfg(feature = "…")]` wrapper around a
  `#[cfg(test)]` block. consus still reports 334 production unwraps against an
  audited estimate near 34, so a second refinement pass is warranted before that
  number drives any burn-down.

## RITK-VIEWS-047 — Collapse seven data accessors to two [major] — pushed, merge held 2026-08-18

Landed on `refactor/ritk-two-accessors-047` (`cfba6507`), **not merged**: a
breaking public-API removal is `[major]`, so it holds for an independent
verdict rather than self-review.

The deferral that kept this open was arithmetic, not difficulty. ADR 0019's
"681 call sites across ~250 files" counted every call to any of the seven
accessors — including the 565 on `data_slice`, one of the two that *survive*.
The accessors that had to go carried **60 sites**; all 60 migrated, with no
re-export, `#[deprecated]`, or forwarding wrapper. ADR 0019 now carries a
dated revision note correcting the figure; ADR 0021 records the decision.

Survivors chosen on caller evidence: `data_slice() -> Result<&[T]>` (565 sites
want a contiguous borrow and already handle the strided failure) and
`data_cow_on(&B) -> Cow<[T]>` (59 want the layout-independent form; the 50
wanting ownership get it from either). The removed five were a
default-backend axis crossed with an ownership axis. The `try_` pair was
worse than redundant — its own Rustdoc said extraction "succeeds for every
valid image", so **28 sites carried a `?` on a branch that cannot be taken**.

Transform consolidation rode along: `CartesianGridGeometry` promoted from
`pub(crate)` in ritk-filter to public in ritk-spatial and generic over rank,
with a typed `NonCartesianGrid` error replacing a message that named its
first caller. Four sites became consumers rather than an eighteenth
implementation; both `apply`/`apply_native` core pairs were verified
byte-identical by `diff` before extraction (`inverse_displacement` 738→583,
`iterative_inverse_displacement` 393→263). Net **−529/+655 across 47 tracked
files plus 3 new** — a reduction while adding a public module and 3 tests.

**Gates** (`+1.97.0-x86_64-pc-windows-msvc`, exit codes from files not pipes):
fmt 0 · clippy `--workspace --all-targets -D warnings` 0 · nextest
**5332 passed / 25 skipped**, 298s, 0 slow · doctests 0 · `semver-checks
--baseline-rev bacfe1f6` **195 pass / 1 fail**, the failure being
`inherent_method_missing` naming exactly the five removed methods and nothing
else.

Two evidence caveats recorded rather than smoothed: the crates.io
semver run is **vacuous** (0 checks / 253 skipped) because ritk-image's
0.3.0→0.4.0 bump predates this work and makes the major lints unrunnable —
the `--baseline-rev` run is the real evidence; and the confirmatory nextest
re-run stalled at 4730/5332 under peer build contention with **zero
failures**, so the green figure above is from the run before the final
rustfmt-whitespace and documentation edits.

**Acceptance for merge:** an agent that did not author it confirms the five
removals are the complete break set, the 28 deleted `?` sites were genuinely
unreachable, and the two extracted cores are equivalent. Then merge and
advance the gitlink.

## RITK-SHARED-TREE-STALE-BASIS-213 — ritk's shared tree is checked out 58 commits behind origin [patch] — open 2026-08-18

- Mid-session a peer switched `repos/ritk` off `refactor/ritk-two-accessors-047`
  onto a local `main` sitting **58 behind `origin/main` and 2 ahead**. In a
  shared tree a branch switch moves the branch for everyone, so this landed
  under an in-flight verification without warning.
- **This is the mechanism behind the stale-basis reverts seen repeatedly this
  sweep.** Any commit authored from this checkout is built on a 58-commit-old
  base; a whole-file write or artefact regeneration from it silently reverts
  everything landed since, passes the author's own gates, and surfaces later
  as unrelated deletions. Filing rather than fixing: the two local commits are
  safe (both mine, 4 days old, preserved on
  `origin/feat/tract-output-formats`), so nothing is stranded, but moving a
  branch a peer just checked out is not mine to do while they may be mid-work.
- It also produced two false readings in this session, both corrected below
  under `-210`.
- Acceptance: the tree is on a branch at or ahead of `origin/main`, and the
  2 local commits are confirmed merged or dropped. Re-open trigger: any
  commit lands in ritk from a base more than one sweep behind origin.

## RITK-DOC-GATE-210 — `cargo doc` is red on ritk's default branch [patch] — open 2026-08-18

- Found because `-047`'s evidence table had no rustdoc step.
  `cargo doc --workspace --no-deps` under `RUSTDOCFLAGS=-D warnings` fails at
  HEAD, independent of any branch work.
- Six links repaired in `5a5de0ef` (unresolved `[Image]`, `[Point<D>]`, a
  matrix written as `rows [0,-1,0], [1,0,0], [0,0,1]` that parsed as three
  link targets, and two public-to-private links to
  `non_negative_information`). **The gate is still red**: ritk-io fails on
  `MAX_SEQUENCE_DEPTH`, same public-to-private class.
- A repo sweep finds ~41 further candidates of that class. They are *not*
  all defects — rustdoc only errors when a **public** item's docs link a
  private one, and the sweep over-matches trait methods and test-only items.
  Fixing them blind would be churn, so the item is the sweep-then-verify,
  not a bulk edit.
- Acceptance: `cargo doc --workspace --no-deps` exits 0 under
  `-D warnings`, and a rustdoc step joins ritk's CI so it cannot go red
  unobserved again — the absence of that step is the actual defect here.

**Progress 2026-08-18: seven links fixed, gate still unconfirmed.**
`MAX_SEQUENCE_DEPTH` is delinked from `anonymize_object` in `4c55c57c`,
landed onto the branch through a private index so the shared tree's
checked-out branch was never touched. The two remaining references to that
const (lines 338, 376) are on private items and resolve fine.

The confirming run could not be made: partway through, `-213` moved the
shared tree onto a 58-behind `main`, which reverted the working copies of
the earlier fixes and the lockfile. **Two readings taken after that point
were wrong and are corrected here rather than left in the record:**

1. I reported ritk's `apollo-fft` requirement as still `^0.26` with my bump
   "orphaned". False — `origin/main` and this branch both carry `^0.27.0`.
   I was reading the peer's stale `main`. There is no requirement lag and
   nothing to re-apply.
2. I attributed the resulting `hermes-simd-core ^0.6` resolver failure to
   that lag. It was entirely the stale checkout: the 58-behind base pins
   `apollo-fft 0.26`, whose transitive `^0.6` cannot unify with the
   overlay's local hermes 0.7.

Both edits made under the mistaken reading were reverted; they were my own,
no peer state was touched. The remaining work is one clean run of the gate
from a current checkout, then the CI step.

## ATLAS-CRATE-LEVEL-ALLOWS-217 — 502 blanket suppressions the ratchet never counted [major] — open 2026-08-18, specified 2026-08-19 (CFDrs, kwavers, consus members delivered 2026-08-25)

**Specified 2026-08-19, and the severity in the original filing was
overstated.** Measured with the scanner's own classification rather than a
grep: `missing_docs` (243 mentions) and `clippy::unwrap_used` (31) are
**almost entirely test-scoped** — inner attributes inside
`#[cfg(test)] mod tests`, which is the correct way to scope a test exemption,
and which `split_test_region` already excludes from the count. The seven
`unwrap_used` sites I first flagged as production are six `src/**/tests.rs`
sidecars plus one correctly-scoped test module. **Zero production violations
of the unwrap ban.** My grep counted test files; the committed detector does
not, and the detector was right.

What production actually holds, and it is **not** one pile of 502:

**CFDrs carries 349 of the ~433 production sites, in 62 files, and its
workspace already has a curated 53-entry `[workspace.lints]` table.** Against
that table:

| pile | mentions | disposition |
|---|---|---|
| already `allow` workspace-wide | **204** | pure redundancy — delete, zero behavioural change |
| `clippy::print_stdout` | **42** | overrides a workspace **`deny`**, in library crates — the real violation |
| everything else | ~105 | per-crate escalations needing individual judgement |

So the bulk is not debt at all, it is duplication of a decision already
recorded once at the workspace level — the same SSOT failure as any other
copied constant. And the genuine finding is small and sharp: **42 blanket
allows silently re-enabling `print_stdout` in library crates whose own
workspace table denies it**, spread over cfd-validation (21), cfd-core (10),
cfd-2d (10), cfd-3d (5), cfd-1d (4), cfd-schematics (1) — all libraries, so
the CLI exemption does not apply.

**Root cause found 2026-08-19, and it inverts the plan. The "redundant"
mentions are not redundant — they are load-bearing, because the workspace
table is inert.**

moirai-core and moirai-gpu both carried `#![warn(clippy::all)]` and
`#![warn(clippy::pedantic)]` **in source**. A source attribute outranks the
manifest `[lints]` table, which cargo delivers as command-line flags, so the
workspace allow-list had no effect on those crates despite
`[lints] workspace = true` — and the per-crate `#![allow(...)]` lines were
the only thing suppressing pedantic. Deleting them alone reddened clippy with
**92 diagnostics**; that is how the premise was caught.

The same in-source escalation is present in **nine CFDrs crates** (cfd-1d,
-2d, -3d, -core, -io, -math, -optim, -python, -validation), which is where
349 of the ~433 sites live. So the CFDrs "204 redundant" figure above is
wrong for exactly those crates, and the correct order is inverted: **remove
the in-source `warn(all)`/`warn(pedantic)` first**, which makes the table
authoritative, and only then are the per-crate allows genuinely deletable.

**Second member done: apollo** (`style/apollo-butterfly-lint-consolidation-217`,
pushed). Different shape, because apollo has **no** in-source escalation — its
table was already authoritative, so the redundancy analysis held. Two
butterfly modules each carried the same pair of blanket allows;
`too_many_arguments` was already in the table (pure duplication) and
`many_single_char_names` moved into it with its reason recorded once —
butterfly kernels name radix inputs a, b, c, d after the signal-flow diagrams
they implement. **Four blanket file allows → one reviewed table entry.**

Verified with `clippy -p apollo-fft --all-targets -D warnings`: nine errors
remain and **none** names either removed lint. All nine are
`missing_const_for_thread_local` in cache/scratch/twiddle modules this change
does not touch — the documented windows-gnu false positive, filed below.

**Apollo residual, found in passing:** three `thread_local!` sites
(`radix_composite/cache.rs:119`, `mixed_radix/caches/scratch.rs:10`,
`mixed_radix/caches/twiddle.rs:16`) lack the `#[expect(clippy::missing_const_for_thread_local)]`
that `adaptive.rs`, `winograd/traits.rs` and `orchestration/cache/plans.rs`
already carry, so apollo's clippy is red on gnu independently of this item.
Two of the three already use `const { … }` initializers, making the lint a
false positive there; `twiddle.rs` allocates via
`with_capacity_and_hasher`, so its case is a real design question rather than
a suppression. Left alone deliberately: that is a kernel-cache decision on a
peer's tree, not part of a lint-hygiene item.

**First member done: moirai** (`0746861`, branch
`style/moirai-workspace-lint-authority-217`, pushed). `crate_level_allows`
**39 → 20**, clippy `--all-targets -D warnings` 0, nextest 104/104. The floor
gets *stricter*, not laxer: the workspace table sets
`pedantic = { level = "deny" }` where the source attribute said `warn`.

- Revised sequence: (1) per member, drop the in-source `warn(all)` /
  `warn(pedantic)` so `[workspace.lints]` governs, then delete the
  now-genuinely-redundant allows — verified by clippy, which is what proves
  redundancy;
  (2) fix or justify the 42 `print_stdout` sites, since a per-crate allow
  overriding a workspace deny is the strongest form of the pattern the floor
  prohibits; (3) adjudicate the ~105 remainder, promoting recurring ones into
  the workspace table with a comment and converting the rest to per-site
  `#[expect(..., reason)]`.
- Non-CFDrs remainder is small and can follow: moirai 39, coeus 17, apollo 8,
  consus 6.
- The lesson, again: an ad-hoc grep and the committed instrument disagreed by
  nearly 2×, and the instrument was correct both times. Measure with the
  scanner.

Detector fixed in `d9c8c60`; the debt itself is the open work.

`allow_sites` counts the substring `#[allow(`, and `#![allow(` does not
contain it — the `!` breaks the match. So the **blanket form was invisible**,
which is precisely the form the lint floor singles out as never acceptable:
"suppressions are per-site `#[expect(lint, reason = "...")]`, never blanket or
crate-level". An inner attribute silences a lint across every item in its
module or crate, *including code written after it*, so it cannot be reviewed
where it takes effect — strictly worse than the per-item form the ratchet did
count.

Production-code counts now seeded into the baseline (502 total):

| CFDrs | moirai | apollo | coeus | consus | kwavers | ritk | gaia | mnemosyne | hermes | leto |
|---|---|---|---|---|---|---|---|---|---|---|
| 367 | 47 | 34 | 18 | 10 | 10 | 8 | 4 | 2 | 1 | 1 |

Found while checking `e31065b`, which raised CFDrs `allow_sites` 88→90 to
absorb a Clippy PR that added `#![allow(...)]` attributes — the ratchet
recorded the two per-item allows and none of the crate-level ones. CFDrs'
`crates/cfd-1d/src/lib.rs` alone opens with a run of ten, several carrying
justifications that read as deferrals ("Error documentation deferred for
internal APIs").

- Acceptance: ratchet burn-down, CFDrs first. Each removal either fixes the
  underlying lint or converts to a per-site `#[expect(lint, reason = "...")]`
  that expires when the site is fixed. No `--accept-raises`.

**CFDrs member — steps 1–2/3 delivered 2026-08-25** (branch
  `fix/cfdrs-lint-authority-217`, CFDrs PR #372 at head `0155d8f4`,
  MERGEABLE):

  - **Step 1** (`2244e3a1`): removed the in-source `#![warn(clippy::all)]` /
    `#![warn(clippy::pedantic)]` escalation in **all ten** crates (the
    previously-claimed nine plus cfd-schematics in combined form), making the
    47-entry `[workspace.lints.clippy]` table the single authority — the
    moirai-verified shape. Then deleted **108 blind allow lines across 31
    files** whose every lint is already workspace-allowed (pure copies;
    lines mixing rust lints like `missing_docs` kept). Clippy-verified as
    the redundancy oracle: all-targets zero real warnings, nextest
    3256/3256, fmt clean, 31 files / 125 pure deletions, CRLF byte-preserved.
  - **Step 2** (`0155d8f4`): the `print_stdout`/`print_stderr` blanket
    overrides of the workspace deny → self-expiring `#[expect]`. The
    detector's "42 sites" undercounted once more (the real surface is
    ~100 files once tests/examples are included), so each file was
    classified: src test-sidecars and integration tests narrowed to the
    lint that actually fires (`print_stderr` for `eprintln!` skip-notes,
    both where stdout prints exist); cfd-3d `bifurcation/validation.rs` +
    `venturi/analysis.rs` keep an unconditional file-level expect because
    `print_summary`/flow diagnostics are real library report APIs;
    files whose prints live only in doc comments dropped the attribute
    entirely. Clippy 0 warnings (expects are self-expiring — any stale
    suppression surfaces as an unfulfilled-expect warning), nextest
    3256/3256, fmt clean.
  - Remaining: step 3 (~105 per-crate escalations needing individual
    adjudication, separate PR).

**kwavers member delivered 2026-08-25** (branch
  `fix/kwavers-lint-leftover-217`, PR #646 at head `f9c124c53`, MERGEABLE):
  the last 4 crate-level allows — 3 were pure duplicates of the workspace
  table (`doc_markdown`, `module_inception`, `needless_range_loop`, all
  already `allow` in `[workspace.lints.clippy]`) and were deleted; the
  python-binding `type_complexity` allow became a self-expiring
  `#[expect]` with the binding-surface reason (`too_many_arguments` stays
  allowed — documented Python mirror surface). Clippy 0 warnings, fmt
  clean; the single `pstd_finite_window_born` failure reproduces at main
  (pre-existing, unrelated).

**consus member removed 2026-08-25** (branch
  `fix/consus-lint-expect-217`, PR #55 at head `2c97deb`, MERGEABLE):
  consus's floor is `pedantic = deny`, so every remaining crate-level
  allow suppresses a genuinely firing lint — converted all 6 to
  self-expiring `#[expect]` with the documented reason
  (`empty_line_after_doc_comments`, `too_many_arguments` ×2,
  `needless_range_loop`, `collapsible_match`, `useless_conversion`).
  `budget.rs` untouched (already the correct test-scoped pattern). Clippy
  0 warnings, nextest 2582/2582, fmt clean (CRLF preserved).

  Remaining members: coeus 18 (peer branch `codex/coeus-lint-ratchet`
  claims it — not actionable), ritk 8, gaia 4, mnemosyne 2, hermes 1,
  leto 1.

  **Merge status 2026-08-25 (hosted checks, exact-head policy — nothing
  merged yet):** CFDrs #372: lockfile pass, Rust-workspace-gate + book
  figures still pending. kwavers #641 (`84ba553ef`) and stacked #642
  (`e1ecdd231`) each expose five initial preflight/review checks rather than 26
  immediately queued jobs; duplicate
  coverage PR #645 is closed as superseded, releasing its queued matrix.
  kwavers #646: no checks observed (fresh push).
  consus #55: no checks observed. kwavers #644 (gpu ratchet): **21/31
  checks SUCCESS** — only the 8 long legs remain pending (Build & Test
  stable/beta, Heavy Validation, Miri, Lockfile integrity, PINN
  Convergence, Benchmark smoke, feature-combination plotting); heads all
  confirmed unchanged and MERGEABLE. Merge each at its exact head the
  moment its checks go terminal.

## ATLAS-BASELINE-DIFF-NOISE-218 — `generate` reformats all 1500 lines, hiding raises [patch] — fixed 2026-08-18

Fixed in `4d78c45`. The item assumed a one-time reformat had to land; it did
not. `indent=2` reproduces the committed file **byte for byte**, so the
committed artifact was already correct and only the generator was wrong — a
one-character change, placed behind a named `render_baseline` so the format
has a single owner instead of sitting as a literal in one of four
`json.dumps` calls. Regeneration now moves 68 lines instead of 1484, and all
68 are real count changes. A test pins the renderer against the committed
file and fails if the format drifts.

- The committed `conformance-baseline.json` is indented with **2 spaces**;
  `generate` writes `indent=1`. So the committed file is not what the
  generator produces, and any run of `generate` emits a whole-file diff of
  ~1500 changed lines.
- **This is how a laundered raise survives review.** `e9c5821`'s single
  `12 -> 17` was one line inside that noise. Seeding the new
  `crate_level_allows` class by hand instead produced a 28-line diff in which
  every changed line was inspectable — the contrast is the argument.
- Violates the generator contract directly: regeneration must be idempotent,
  and here running the generator twice against an unchanged tree still
  rewrites the file.
- Acceptance: `generate` against an unchanged tree produces a zero-line diff.
  Fix the indent to match, land the one-time reformat as its own commit
  containing nothing else, and add the idempotence check to the script's
  tests.

## ATLAS-MOLD-LINKER-226 — mold cannot link this stack; LLD is the only substitute [patch] — rejected 2026-08-19

Requested and evaluated. **mold cannot be used on this host, and not for a
configuration reason — it has no applicable target.**

- mold 2.42.0 *is* installed (`/d/msys64/ucrt64/bin/mold`), which is why this
  looks viable at first glance.
- It is ELF-only. Handed a Windows object it reports `unknown file type`, and
  it rejects `-m i386pep` — the PE/COFF emulation GNU ld uses for win64 — as
  an unknown argument.
- Every target in this stack is `x86_64-pc-windows-{msvc,gnu}`, i.e. PE/COFF.
- The one target where mold would apply, `x86_64-unknown-linux-gnu`, is **not
  installed** (`rustup target list --installed` shows only
  `x86_64-pc-windows-msvc`) and no Linux cross-linker is present, so even
  hermes' `cfg(unix)` cross-check could not exercise it — and `cargo check`
  does not link in any case.

**LLD is the substitute and it works.** `rust-lld.exe` ships inside the msvc
toolchain and linked the target successfully via
`-Clinker-flavor=lld-link -Clinker=<rust-lld>`.

**No speed claim is made, because the measurement does not support one.** An
isolated scratch crate (own `CARGO_TARGET_DIR`, quiet host, 1 concurrent
cargo) gave default `link.exe` median **1.49 s** (1.32/1.49/1.71) against
rust-lld median **2.25 s** (1.74/2.25/4.19). At that size the numbers are
dominated by process startup rather than linking, and three runs on one tiny
binary is not evidence that LLD is slower for real workloads — it is evidence
that this experiment was too small to answer the question.

**The reason not to flip it stack-wide anyway:** the linker is set through
`RUSTFLAGS`/config, which is part of every crate's fingerprint. Changing it
invalidates the entire shared `CARGO_TARGET_DIR` and forces a full rebuild
for every agent on the stack, and doing that to peers mid-session on
unproven evidence is the wrong trade. A real evaluation needs a link-heavy
target measured on a quiet host, which is a scheduled experiment, not an
inline one.

## ATLAS-LANE-SPRAWL-222 — 26 lane directories against a two-per-repo bound [patch] — open 2026-08-19

Found while needing one lane for `-221`. `git_discipline: Worktrees` bounds a
repository to **two** working trees (main plus one lane), and the bound is a
creation precondition, not an aspiration.

| repo | trees | bound |
|---|---|---|
| kwavers | 5 | 2 |

`worktrees/` currently holds **16 directories**, including the sanctioned
`.archive` metadata directory. The former empty Consus lane directory and
two empty root Consus husks were removed after confirming zero children. The
remaining structural violation is the clean detached Kwavers lane at
`D:/tmp/kw-verify`, outside the single canonical lane root; it remains
unremoved because it is an external checkout whose ownership is not
established by this tree.

The remaining external lane is clean, but its owning process and intended
lifecycle are not established from Atlas. It remains a recorded residual,
not a deletion target.

The rule already names the cause: "sprawl is friction's product", and the
prescribed fix is a committed lane tool making create/re-point/close one
command each, with the tree-count precondition enforced in `create`. Without
it the compliant path is more work than the workaround, which is exactly the
state here.

- Acceptance: a committed lane tool enforcing the two-tree precondition, the
  canonical root, and the naming convention; every member at or under two
  trees; the misplaced consus lane consolidated (`git worktree move`); the
  husks cleared once their holders exit. ~~A conformance class counting trees
  per member so the bound is measured rather than remembered.~~

**Measurement half done 2026-08-19 — and built twice.** A peer landed
`count_excess_worktrees` in `dbb1a4e` while I was writing the same class, and
their commit swept my uncommitted definition in alongside theirs, so HEAD
briefly carried **two definitions**, the second shadowing the first. Nothing
failed, because both were correct and produced identical counts
(consus 1, kwavers 2, ritk 3). Deduplicated in `febe7d5`, keeping theirs and
porting two fixes: the bound now comes from `WORKTREE_BOUND` rather than a
bare literal, and the docstring's claim to read "the packed-refs mechanism"
is corrected to what it does read — `.git/worktrees/` entries, one per linked
worktree, which is why the bound is reduced by one before subtracting.

Behavioural tests cover whichever implementation survives: they build a real
repository, add lanes one at a time, and assert the count crosses at the third
tree. The ratchet now refuses a third tree exactly as it refuses any other
debt increase, so the bound is enforced rather than remembered.

The collision is itself the lesson worth keeping — two agents built the same
detector within an hour because neither claim was visible to the other until
it landed.
- **Not** a blocker for anything: at cap the existing lane is the next work,
  which is how `-221` proceeded — the stale `consus-zarr-fix` lane held a
  branch already merged as PR #47, so it was re-pointed rather than adding a
  fourth tree.

## ATLAS-KWAVERS-ADR-CASING-220 — kwavers tracked `docs/ADR`, so its index was never gated [patch] — fixed 2026-08-18

- kwavers was the sole member tracking **`docs/ADR/`**; every other member and
  the Atlas index generator use `docs/adr`. On Windows the two resolve to one
  directory, so this passed locally forever; on a case-sensitive filesystem
  they are different paths and `adr_dirs()` simply never found it.
- Fixed in kwavers `0a9842a67` (gitlink advanced), renamed through an
  intermediate name because a case-only rename is a no-op on this host.
- Landed **ADR 111** in the same change — a genuinely untracked record of
  commit `950fbc588`, which retired the `KzkSolverPlugin` surface without one.
  Confirmed absent from `HEAD~1`.

## ATLAS-ADR-GATE-WORKTREE-219 — The ADR index gate reads the worktree, not the tracked tree [patch] — fixed 2026-08-18

Fixed in `5d30801`, **corrected in `636eb10`**.

The index is a set of links a reader follows after cloning, but it was built
by globbing the directory, so an untracked file satisfied an index entry. ADR
0045 was deleted from `HEAD` twice while staying on disk and this gate called
that index clean both times.

**The first fix used the wrong oracle and I reported its output as fact.**
`git ls-files` asks the *index*, which is working state: a peer's staged
deletion, or a commit written through a private index, leaves an entry absent
from `ls-files` while `HEAD` still carries the file. So `5d30801`'s claim to
have found four untracked ADRs was wrong — **three were false**. coeus 0066,
hephaestus 0052 and leto 0026 are all in `HEAD` and on disk; only kwavers 111
was real. `636eb10` switches to `ls-tree HEAD`, and the test now commits
rather than staging, since an index-only entry never reaches a reader.

Worth keeping as a pattern: a gate that reads mutable local state will
manufacture findings on a shared tree, and they look exactly like real ones.

**Residual:** `repos/coeus/docs/adr` still reports DRIFTED — a real
pre-existing drift, unrelated to the oracle bug, and the one finding that
survived. Left for the coeus owner rather than regenerated into a tree
carrying 49 dirty files and a populated index.

- `docs/adr/README.md:53` has listed ADR 0045 throughout the period in which
  the file was absent from `HEAD` — twice — and `adr-index.py check` reported
  that index clean, because the file remained on disk untracked.
- A fresh clone therefore gets a dead index link while the gate passes. The
  gate measures the author's disk, not the repository.
- Also currently reported by that gate and unaddressed: `repos/coeus/docs/adr`
  and `repos/kwavers/docs/adr` indexes are DRIFTED from their ADR headers.
- Acceptance: the gate resolves entries against tracked paths (`git ls-files`)
  so an untracked file cannot satisfy an index entry; the coeus and kwavers
  drifts are cleared.

## ATLAS-RATCHET-LAUNDERING-216 — `generate` could rewrite the baseline upward [patch] — fixed 2026-08-18

**The ratchet had no floor.** `check` refused a raise, but `generate`
overwrote the baseline unconditionally, so any failing check could be cleared
by re-running `generate` — the gate's form satisfied, its purpose inverted.
That is gaming in the `integrity` sense, and it is the mechanism, not a
hypothetical: **`e9c5821` lifted `ritk/print_dbg` from 12 to 17**, described
as "update baseline after coeus/moirai/ritk advances". A raise is the one
move the ratchet exists to prevent.

Fixed in `7d4562f`. `generate` now computes the raises against the committed
baseline and refuses (exit 2) with a per-class listing. A detector change is
the single legitimate raise — the generator contract requires regenerating in
the same change — so `--accept-raises REASON` remains, but it is explicit,
named, and prints every raise it performs.

Evidence: against the current tree the guard catches the `12 -> 17` raise
plus five others (`coeus/commented_out_code`, `coeus/existence_only_assertions`,
`coeus/oversized_files`, `moirai/oversized_files`, `ritk/oversized_files`) that
a `generate` run would have absorbed. Three tests pin it, calling the shipped
`baseline_raises` rather than a copy — neutering the comparison fails them.

**The laundered baseline is left in place, deliberately.** Reverting
`ritk/print_dbg` to 12 would red the gate for the whole fleet on a premise I
could not confirm: I could not reproduce the scanner's count of 17 with a hand
probe (mine reports 143 over a different file scope), and none of the
print-bearing files has changed recently, so the delta may be scan-scope
rather than new debt. Resolving that is `-211`. What matters is that it can no
longer happen unobserved.

## ATLAS-RITK-SCRATCH-BINARY-215 — 1.3 MB executable committed to ritk [patch] — fixed 2026-08-18

- `scratch/check_restart.exe` (1,305,872 bytes) and `scratch/check_restart.rs`
  were tracked — the **only** tracked binary in the repository. They arrived
  through a merge five weeks ago (`a5e375fe`).
- `.gitignore` has covered `scratch/` since line 41, but ignore rules do not
  apply to already-tracked paths, so these two survived while the other 48
  files in that directory stayed correctly untracked. The intent was right and
  the enforcement simply did not reach backwards.
- Removed from the index only in ritk `4b345b2e`
  (`chore/ritk-untrack-scratch-215`, pushed): working copies untouched, the
  directory keeps working as scratch space.
- Found incidentally while probing `-211`'s print counts, which is the
  argument for the probe.

## RITK-PEER-RATCHET-211 — Peer commits regressed three ratchet classes on ritk [patch] — open 2026-08-18

- `print_dbg 12 → 17`, `oversized_files 43 → 44`,
  `manifest_implementation 104 → 105`.
- Attribution is unambiguous: the counts are **identical at HEAD and in the
  dirty worktree**, so they came from the peer commits (#171–#173) that moved
  ritk's HEAD from `bacfe1f6` to `0f0b5c56` mid-session, not from the
  accessor work, which is ratchet-neutral.
- `print_dbg +5` is the one to look at first — five new print/`dbg!` sites in
  library code is a lint-floor breach, not drift.
- Acceptance: each class back at or below baseline, or the baseline
  regenerated with a recorded justification per the generator contract.

## ATLAS-ARCH-008-RUNNING-IN-PLACE-225 — The conversion converts and re-accumulates at the same rate [patch] — open 2026-08-19

`atlas_scattered_containers_classify.py` has a gate mode
(`--verify-oracle`) and a committed oracle
(`scripts/oracles/arch-008-production-sites.txt`, 243 sites). Running it for
what appears to be the first time:

> **35 sites now in production but missing from the oracle; 36 oracle sites
> no longer in production.**

Net **−1**. The interesting number is not the total, it is the pair: 36 sites
were genuinely converted while 35 new pointer-scattered containers landed. So
`ATLAS-ARCH-008` is not stalled and not regressing — it is **running in
place**, and has been doing so unobserved because nothing ran the verifier.
The inflow is spread across seven members: consus 8, gaia 7, CFDrs 7, coeus 5,
ritk 4, moirai 2, kwavers 2.

A conversion item cannot converge while new instances arrive at the
conversion rate. Wiring the verifier is what stops the inflow, and it matters
more than clearing the backlog.

**Deliberately not wired yet, and deliberately not regenerated.** Wiring it
now reds CI on 35 pre-existing sites; regenerating the oracle to make it pass
would absorb 35 new production sites into the accepted set, which is exactly
the baseline laundering fixed in `-216` this same day. The order is: justify
or convert the 35, then wire.

Also worth noting: every write of this oracle has landed inside an unrelated
chore commit — it was created by `5956d02` ("chore(gitlinks): Advance ritk
…"), the same scope-creep commit that duplicated `parity_artefacts`, and
touched before that by two more gitlink commits. Derived state has been
riding along in commits whose messages do not mention it.

- Acceptance: the 35 are converted or individually justified in the oracle;
  ~~`--verify-oracle` wired into `atlas-conformance.yml`~~ **done by a peer,
  2026-08-19**; the oracle only ever regenerated in a commit whose subject
  says so.

**A peer wired the gate while this was being written, and did it the right
way round.** `atlas-conformance.yml` now runs `--verify-oracle`, with the
oracle path and the classifier added to the trigger list. Critically they
**did not regenerate the oracle** to make the new gate pass — it is still 243
lines and still reports the same 35 — so the gate goes red and forces the
conversion instead of absorbing it. That is the opposite of the `e9c5821`
baseline-raise, and the right call.

Their step comment also corrects an assumption in my measurement: CI scans a
**clean checkout** pinned to the root gitlinks, while my numbers came from
live worktrees carrying peer WIP. I checked the 20 sampled drift sites and
all are **tracked and clean** — real committed content, not WIP — so the
drift is genuine, though the exact CI count may differ where a member's
worktree and its recorded gitlink disagree. The next PR run is the
authoritative number.

## ATLAS-UNWIRED-GATES-224 — Instruments that exist, pass, and are never run [patch] — partly fixed 2026-08-19

**`atlas-registry-metadata.py` had never been invoked by any workflow.** It
was written, committed, and green — and on the single day it was run by hand
it found kwavers declaring six keywords against a cap of five, plus the
category slug `medical`, which does not exist in the crates.io taxonomy.
crates.io enforces both **at upload**, after the version number is spent, so
the rejection is not retryable under that version. Wired in `572a585`; the
defect it found is fixed in kwavers `1aa24beb7`.

An unreachable taxonomy degrades to `UNVERIFIED` at exit 0 and the slug
snapshot is committed, so it cannot flake on crates.io availability.

**`atlas-lane-audit.py` is deliberately left unwired.** It already implements
`-222`'s whole audit half — tree bound, canonical lane root, named branch,
prune freshness, standalone-clone detection — and currently reports the same
four violations. But a CI clone has one working tree, so in CI it would pass
unconditionally and prove nothing. It is an orient-time and
replenishment-time check by its own contract; its findings belong on the
board, which is where `-222` now carries them.

- Residual: `atlas_scattered_containers_classify.py` is also unwired. Assess
  whether it is CI-valid (like the registry check) or inherently local (like
  the lane audit) before deciding — those are the only two answers, and
  "wire everything" is the wrong one.
- The pattern, worth keeping: **a gate that has never failed may never have
  run.** Three instruments were built during this sweep; one was silently
  inert. Checking `grep -ohE "scripts/[a-z-]+\.py" .github/workflows/*.yml`
  against `ls scripts/*.py` is the ten-second version of that audit.

## ATLAS-STALE-CHECKOUT-FINDINGS-223 — Gates measure the checkout, and 8 of 25 members are behind [patch] — partly fixed 2026-08-19

**Four false findings this session trace to one cause.** Gates read whichever
revision happens to be checked out. A survey today found **8 of 25 members
behind their origin**: CFDrs 5, coeus 6, consus 3, gaia 2, themis 2,
aequitas 1, apollo 1, tyche 1.

The four, all reported as defects before being traced:

1. ritk's `apollo-fft` requirement read as lagging at `^0.26` with my bump
   orphaned — I was reading a `main` 58 commits behind (`-213`).
2. The `hermes-simd-core ^0.6` resolver failure attributed to that lag; it
   was the stale base.
3. Three ADRs reported untracked — that one was the *index* rather than the
   checkout, but the same shape (`-219`).
4. coeus reporting a drifted ADR index, where `origin/main` had carried the
   missing row for six commits. I regenerated it and nearly committed the
   redundant change before checking upstream.

Fixed in `7481561` for the ADR gate: findings now state how far behind the
checkout is. The fallback to `origin/main` is the case that matters, not an
edge — a detached HEAD has no `@{upstream}`, and detached checkouts are
exactly the stale ones.

- Residual: `atlas-conformance.py --worktree` has the same exposure. It does
  guard the default path (`check_clean_revision` requires a clean tree with
  matching gitlinks), but `--worktree` bypasses that and is what gets run
  while peers hold dirty trees — every conformance number in this session
  came from it.
- Acceptance: any gate reporting against a checkout states that checkout's
  distance from its upstream, or refuses to report; and the members above are
  brought current, which is `-213`'s territory.

## RITK-ACCESSOR-FOLLOWUPS-212 — Two consequences the accessor migration exposed [patch] — open 2026-08-18, specified 2026-08-19

**Sharpened: the `Result` is now provably uninhabited, and the sibling makes
it explicit.** On `refactor/ritk-two-accessors-047`, `extract_vec`'s body is
`image.data_cow_on(&B::default()).into_owned()` — infallible — while its
signature is still `anyhow::Result<(Vec<f32>, [usize; D])>`. There is no
longer any fallible operation inside the wrapper at all.

Beside it sits `extract_vec_infallible`, which does the **identical** thing
without the wrapper, and whose own Rustdoc states the truth: "canonical Coeus
host extraction is infallible". So the codebase already contains the
correction — added as an additive `_infallible`-suffixed sibling rather than
applied to the original, which is the marker-naming and compatibility-soup
pattern in one.

The fix is one function, not two: `extract_vec` becomes infallible,
`extract_vec_infallible` is deleted, callers drop their `?`.

**Scoped as its own atomic `[patch]`, to land immediately after `-047`
merges.** The two names carry **518 call sites** (183 + 335). Folding that
into `-047` would triple a branch already held for review and is precisely
the "branch grows past its item" pattern — the same call made for apollo's
827-site `precise`/`reduced` rename. Sequenced after the merge because `-047`
is what removes the last fallible operation; before it, the `Result` is
merely near-dead rather than provably dead.

- Second half unchanged: ~14 `.into_owned()` sites can drop the copy, since
  `Cow` derefs. Same commit is fine — both are mechanical over the same
  surface.
- Acceptance: zero `_infallible`-suffixed siblings; `extract_vec` returns a
  tuple; no call site carries `?` on it; workspace green.

- `ritk_tensor_ops::extract_vec` now has a **visibly fake `Result`**. It is
  pre-existing, but was hidden one level down inside `try_data_vec`; removing
  that wrapper surfaced it. A `Result` whose error branch is unreachable is
  the same defect the `try_` pair carried.
- ~14 `.into_owned()` sites can drop the copy entirely, since `Cow` derefs.
  Kept out of `-047` deliberately: that migration was held
  semantics-preserving, and turning it into a performance change mid-flight
  would have made the semver evidence harder to read.

## ATLAS-CFDRS-LANE-DIVERGED-208 — CFDrs lane holds 99 unpushed commits and is 18 behind its own remote [patch] — open 2026-08-18

- Found while re-verifying `-085`'s blocker. `worktrees/CFDrs-runtime-budget`
  sits on `codex/cfdrs-backward-step-108` at `7b9673ef` (8 hours stale, so
  reclaimable under the one-hour sweep), **99 commits ahead of `origin/main`
  and 99 ahead of its own remote branch, while 18 behind it** — the local lane
  and its pushed ref have diverged, not merely drifted.
- Rescued non-destructively: `7b9673ef` pushed to
  `origin/ci/cfdrs-lane-rescue-208`. No force-push over
  `origin/codex/cfdrs-backward-step-108`, so the peer's 18 remote-only commits
  are untouched. The 99 commits are now fleet-visible rather than living only
  in one working tree.
- The 99 are substantive, not churn: lint-residual closures across cfd-1d and
  cfd-2d, a masked-step metric fix, a parabolic-inlet allocation reuse, and a
  manual workspace gate.
- Acceptance: the two heads are reconciled into one branch (the 18 remote-only
  commits merged in, not dropped), gates green, merged to `main`, both the lane
  branch and the rescue ref deleted. Until then the rescue ref is quarantine,
  not a second home — it carries no independent development.
- Note this is why `-085` stays blocked: its re-open trigger requires no second
  lane live, and this lane is both live and the largest single body of
  unmerged CFDrs work.

## ATLAS-APOLLO-AVX-SEAM-050A — Merge the AVX precise/reduced leaves [major] — rejected 2026-08-18

Two independent agents reached the same refusal; recording it so a third does
not re-open it. **The seam the item asked for already exists.**
`stockham/avx/backend.rs` declares `StockhamAvxBackend` — `type Vector`,
`const COMPLEX_PER_VECTOR`, load/store, `add`/`sub`/`mul`/`fmaddsub`,
`permute_complex_swap`, provided `cmul` — with four impls (`f64`, `f32`,
`Avx512BackendPrecise`, `Avx512BackendReduced`), and `stockham/avx/generic/` is
already **2905 lines generic over it**, larger than the 2941 lines of both leaf
directories combined. The merge has largely happened.

What remains in `precise/` + `reduced/` is the `groups == 1` / `groups == 2`
corners, and there the **length of the shuffle network is a function of the
pack count, not a parameter to it**: `groups == 2` is 4 loads + 4
`permute2f128` at 2 complex/vector versus 4 loads + 4 `unpacklo/hi_pd` + 4
`permute2f128` at 4. Hoisting that behind a `transpose_block` method relocates
both bodies into the two impls and shares only the ~30-line arithmetic DAG that
follows — re-emission behind a trait with no reduction.

Upstream closure was checked and is **not** available: hermes' `SimdPermute` is
specified on the *flat* lane sequence and its own docs record that
`_mm256_unpacklo_ps` "and friends" cannot implement it, because they act within
128-bit halves — hermes deliberately abstracts away the sub-lane structure the
f32/f64 difference lives in. `interleave`/`deinterleave` are scalar
store/load emulation on every backend, `SimdKernel` is sealed so apollo cannot
add a backend, and hermes ADR 006 (Accepted) declines an SSE backend, leaving
apollo's 128-bit f32 leaf with no type-parameter representation.

**The `precise`/`reduced` rename is separately not executable as specified**,
for two reasons: each directory contains *both* an AVX2 and an AVX-512 backend
(pack counts 2 and 4 under `precise/`, 4 and 8 under `reduced/`), so the
distinguishing property is the scalar type — whose name the naming prohibition
bans — and a geometry name like `pack2`/`pack4` would be factually false. And
it is not a two-directory rename: `precise`/`reduced` is a crate-wide euphemism
for `f64`/`f32` across **827 sites / ~120 identifiers**, only 396 of them
inside `stockham`, reaching `twiddle.rs`, `cache_macros.rs`,
`bluestein_cache.rs`, `transpose.rs`, `pointwise.rs`, `small_pot.rs`,
`dft_prime.rs`. It must land atomically as its own crate-wide `[patch]`, with
real-word false positives guarded (`..._matches_direct_reduced_precision` uses
"reduced precision" in its genuine numerical sense).

**Residual worth doing, carried forward as 050C below.**

## ATLAS-APOLLO-LINT-EXPECT-ROT-001 — Remove obsolete Windows Clippy expectations [patch] — in-progress

- Owner: codex coordinator; scope: Apollo source files containing the 42
  `#[cfg_attr(windows, expect(clippy::missing_const_for_thread_local, ...))]`
  sites across 28 files. Non-goals: Apollo's peer-owned `Cargo.lock` and
  `backlog.md`, the Stockham policy work, and unrelated provider consumers.
- Acceptance: the expectations are removed or narrowed only if the pinned
  toolchain still emits the lint; Apollo's workspace Clippy gate passes with
  `-D warnings` and no `-A` override, with value-semantic tests unchanged.
- Verification: record the exact provider revision, focused tests, doctests,
  Clippy, rustfmt, and rustdoc results before closing; update the provider
  item without staging its peer-owned working-tree changes.

## ATLAS-APOLLO-STOCKHAM-POLICY-050C — Parameterize the dispatch-policy matrix [minor] — open 2026-08-18

- Three parallel type families cover the same (scalar × ISA) axis inside
  `stockham`: `StockhamAvxBackend` (4 impls), `StockhamPrecision` (6
  hand-written ZST markers = {Precise,Reduced} × {scalar, AvxFma, Avx512},
  the 1240 lines of `precision/{precise,reduced}.rs`), and `StockhamKernel`
  (2 impls, on the *scalar* axis — the 050B census mis-filed this one).
- `StockhamPrecision` is a dispatch-policy matrix written per cell; it can be
  parameterized over `B: StockhamAvxBackend`. Type-level, no numerics risk,
  real reduction — unlike 050A.
- Also here: `StockhamAvxBackend` gives three methods provided bodies that are
  `unreachable!("Not implemented for this precision")`. A panicking default is
  a mock-shaped seam — the differing fused-stage sets belong in a capability
  const or a split trait.
- Acceptance: `precision/{precise,reduced}.rs` line count materially reduced
  with the ZST marker set derived rather than enumerated; zero
  `unreachable!` provided bodies on the backend trait; bit-identical FFT
  outputs against the pre-change build on the existing differential suite.

## ATLAS-APOLLO-COMPLEX-SEAM-050B — Element-parameterize the complex seams [minor] — open 2026-08-18

- Census corrected on re-run; the original count of eight was wrong.
  `FftPrecision` and `TwiddleOutput` already carry **three** impls including
  `Complex<f16>` — a seam admitting three element types is element-parameterized
  already, not a `Complex64`/`Complex32` fork. `StockhamKernel` is on the scalar
  axis and belongs to 050C.
- Genuine two-impl complex pairs: **five** — `KernelScalar`, `PlanScratch`,
  `TwiddleStore`, `NormalizeSlice`, `ScratchDispatch`.
- Independent of 050A: type-level and crate-wide versus x86 leaf codegen.

## ATLAS-CONSUS-ZARR-CODEC-FOLLOWUPS-214-ORIGINAL — filed scope, retained for the record [minor] — superseded

- **Element width for the `bytes` codec.** The swap itself is trivial; what is
  missing is the dtype. `CodecPipeline::{compress,decompress}` take
  `(codec, &[u8])`, so no arm can know whether to swap in 2-, 4-, or 8-byte
  groups. Threading the element width through the pipeline is the real
  closure, after which the `UnsupportedFeature` arm becomes a swap.
- **A `crc32c` implementation.** `consus-compression` has `Crc32`, but it is
  CRC-32/IEEE. Zarr v3 mandates Castagnoli. Implementing `crc32c` alongside it
  (not replacing — IEEE has its own users) plus the ±4-byte length plumbing
  closes `-207` properly.
- **`endian = "native"` is not a legal Zarr v3 value.** The spec admits only
  `little` and `big`, and this crate writes `"native"` from its own pipeline
  constructors (`codec/mod.rs:464,479`, `metadata/codec.rs:122`) and tests for
  it in an identity check (`metadata/codec.rs:108`). Left out of the fix
  because changing it changes **serialized on-disk metadata**, a wider blast
  radius than the codec arms and one needing a round-trip fixture; the codec
  accepts `"native"` as host-order in the meantime, documented at the site.

## ATLAS-KWAVERS-REAL-COMPUTE-028 — Remove Kwavers production identity paths [major] [arch] — open

- Owner: Kwavers provider owner; Atlas scope is the audit record and consumer
  integration gate. Kwavers source files are peer-owned in the active checkout.
- Findings: realtime GPU scan conversion, mixed-domain time propagation and
  nonlinear correction, KZK retarded-time application, and PINN domain
  adaptation all contain identity-return paths on the fetched default. Exact
  evidence and locations: `gap_audit.md#atlas-kwavers-real-compute-028`.
- Acceptance: each seam performs input-sensitive computation or is removed or
  narrowed; the corresponding analytical/differential tests fail under the old
  identity body; focused provider gates and the full Kwavers integration gate
  pass; no clone-only implementation remains at the named locations.
- Re-open trigger: a clean committed Kwavers source increment lands on
  `origin/main` or a peer claim becomes stale under the one-hour sweep.

## ATLAS-USCT-FWI-024 — Transmission-USCT FWI parity [minor] — open 2026-08-13

Audit and evidence: `gap_audit.md#atlas-usct-fwi-024`. kwavers leads the
reference on forward-model and optimizer machinery; these close the deltas.

| ID | Outcome | Class | Status | Owner | Acceptance oracle |
|----|---------|-------|--------|-------|-------------------|
| FWI-024-A | Replace fixed-step backtracking in `frequency_domain/inversion.rs` with the linearized exact line search `α = −⟨g,d⟩/⟨d,Hd⟩`, reusing the matrix-free Hessian action for the curvature. | [minor] | done — kwavers `912fe1983`, merged to main via cascade/provider-042; content verified on origin/main | Claude | Met. `⟨d,Hd⟩` reuses the existing `hessian_vector` (moved to `gradient.rs`, one implementation for both consumers) rather than adding a second forward-projection path. New test recovers a weak anomaly with the seed set 200× too large; falsified by forcing the old behaviour (fails with a one-entry objective history). 44/44 frequency-domain tests, clippy/doc/fmt clean in scope |
| FWI-024-B | Cap the NLCG β with Fletcher–Reeves: `β = min(max(β_PR,0), β_FR)` (Gilbert–Nocedal). | [patch] | **done 2026-08-19** — kwavers PR #406 merged at `53b3f984`; content verified on `origin/main` | Claude | Met. Convergence on the existing inversion tests is monotone and no worse than `β_PR⁺`; a case where unbounded `β_PR` overshoots is added as a regression test. Architecture Validation `Validate Clean Architecture` and `Test Suite Coverage` reported failures that were infrastructure-only; benchmark, Miri, build-matrix, and Code Quality passed. |
| FWI-024-C | Angular-spectrum split-step implementation of the existing `HelmholtzForwardOperator` seam, reusing the phase-screen code rather than a second copy. | [minor] | **done 2026-08-19** — kwavers PR #415 merged at `1f37ec907`, verified on origin/main by content (`as_operator.rs`, +680 lines). Its two failing benchmark gates were a stale branch base, not a regression: the branch predated `.github/actions/install-system-dependencies` on main, and `benchmark regression check` was cascading from `complete benchmark smoke`. Updated from main; all 27 checks pass. Earlier state: — kwavers PR #415 @ `dc9d61bd0` (`feat/kwavers-fwi-asm-split-step`): `AngularSpectrumSplitStepOperator` with phase-screen toggle + source taper; forward/backward propagation from transmit z-plane; receiver sampling on propagated planes | — | Differential against CBS on a weak-contrast phantom within a derived bound; documented divergence where reflections matter (ASM is one-way). 50/50 frequency_domain tests, clippy `-D warnings`, fmt clean locally |
| FWI-024-D | Transmission-USCT acquisition: two opposed linear arrays on a rotation stage, per-view interpolation between a fixed reconstruction grid and view-aligned simulation grids, gradient accumulation across views. | [minor] [arch] | **increment 1 done 2026-08-20 — kwavers PR #420 merged at `b20eb48b`, Atlas gitlink in `fdf9981`; increment 2 in review 2026-08-20** — increment 1: kwavers PR #420 (acquisition seam, ADR 115), auto-merge set after all CI passes. Increment 2: kwavers PR #424 (`RotatingOpposedLinearArray` + `RotatingAcquisition` + ADR 116), targets PR #420 base. ADR 116 settles route (a) — per-view element-position rotation on one fixed grid. Route (b) — per-view model interpolation — rejected because it puts systematic interpolation error inside the gradient. Finite-window PSTD excluded from rotating acquisition (requires on-grid coords; extension deferred). Increment 3 is the inversion integration test (phantom recovery oracle). Earlier context: the acquisition seam is kwavers PR #420, recorded as ADR 113 (PR #418). Behaviour-preserving: 54/54 frequency-domain incl. the Ali 2025 parity gate, 1009/1009 solver, 721/721 downstream, all callers and PyO3 bindings updated with no shim. With the seam in place, the rotating acquisition splits into a design fork worth settling before code. Two routes, and the cheap one does not fully work:  **(a) Rotate the geometry on one fixed grid.** The acquisition simply reports rotated element positions per view — which is what the seam already expresses, with no interpolation anywhere. The Green's-function operators accept continuous coordinates, and `cbs/projection.rs` already carries band-limited interpolation for off-grid sampling (`sample_field_with_bli`, `source_density_from_bli`), so Born and CBS take rotated positions directly.  It fails on one operator. The PSTD finite-window path resolves receivers through `exact_grid_index`, whose `exact_axis_index` rejects any coordinate more than `1e-9` off a grid node. A linear array rotated by anything but a multiple of 90° lands off-node on essentially every element, so that operator would reject every view — not silently degrade, which is at least honest, but it means route (a) covers only part of the operator set.  **(b) Rotate the model per view** — the route the item description assumed ("per-view interpolation between a fixed reconstruction grid and view-aligned simulation grids"). Works for every operator, since each view simulates on an axis-aligned grid. The cost is real: resampling the slowness volume per view, and resampling the gradient back, puts interpolation error inside the gradient that the inversion then descends on. That error is systematic, not noise — it correlates with view angle — so it needs a derived bound and a round-trip test (rotate by θ, rotate by −θ, compare against identity within that bound) before any recovered phantom means anything.  **Not settled here.** The choice is [arch] and belongs in an ADR alongside 115, with the rejected option recorded: whether to extend the finite-window operator to BLI receivers (making (a) universal) or to accept per-view resampling. The sizing point is that increment 2 is not "add a rotating acquisition" — the acquisition type itself is a few dozen lines on top of the seam. The work is whichever of those two problems is chosen. Two findings on the way in: the ADR first specified a generic seam and was corrected to `&dyn` before merge (Config holds `Arc<dyn HelmholtzForwardOperator>`, so a generic method is not dyn-compatible); and `receiver_indices_on_grid` was hoisted out of the transmit loop at three sites, correct only under a ring’s rotational symmetry and silently wrong for every rotated view but the first. Original sizing note: The frequency-domain FWI is hard-bound to `MultiRowRingArray`, not merely parameterized by it: 36 references across all six modules (`forward`, `gradient`, `gauss_newton`, `operator`, `finite_window`, `inversion`), consuming ring-specific API (`circumferential_elements`, `cylindrical_source`). A rotating opposed-linear-array acquisition cannot be expressed through it, so D needs an acquisition seam extracted first — an [arch] change with an ADR as its first step, per versioning. Sizing before starting: the seam is the item, and the rotation-stage geometry rides on it. | — | Recovers the sound-speed phantom from a simulated 360°/2° sweep within a derived tolerance; per-view rotation round-trips to identity |

## ATLAS-US-CAPABILITY-023 — ITKUltrasound capability parity [arch] — open 2026-08-13

Audit and evidence: `gap_audit.md#atlas-us-capability-023`. Items are
DoR-shaped and dependency-ordered; US-023-A gates the clean form of B and D.

| ID | Outcome | Class | Status | Owner | Acceptance oracle |
|----|---------|-------|--------|-------|-------------------|
| US-023-A | ADR: non-Cartesian acquisition images as a coordinate seam in ritk (curvilinear, 3-D phased array, slice series) — index→physical map carried by the image type so existing resamplers/filters apply unchanged; decide ritk-vs-kwavers ownership for G2 and G4. | [arch] | done 2026-08-13 — ADR 0042 Accepted | Claude | Met. Enum-dispatched `CoordinateMap` selected over a fourth type parameter; G2 and G4 both owned by ritk |
| US-023-A1 | Implement the ADR 0042 seam in `ritk-image`: `CoordinateMap` with `Cartesian` + `CurvilinearArray`, carried on `Image`, dispatched by both batch and both single-point transforms. | [major] | done 2026-08-13 — ritk PR #128 merged as `c608f758` | Claude | Met. Cartesian path bit-identical (pinned by test); curvilinear round-trip, fan symmetry/curvature, out-of-fan NaN, dimensionality rejection all covered. 1173 tests, clippy `-D warnings`, rustdoc, fmt clean. |
| RITK-CI-1 | Restore SimpleITK parity for `InverseDisplacementField` 2-D/3-D and `IterativeInverseDisplacementField`. **Diagnosed** (`gap_audit.md#atlas-ritk-ci-diag-035`): introduced by `3aa73ba0` (ADR 0020); the 2-D case is ~27x worse than 3-D, and the new Gram-Schmidt in-plane basis path runs *only* for the 2-D-embedded shape. Under identity direction it must reduce to the world axes exactly — the parity break proves it does not. | [major] | todo — owner is 3aa73ba0's author; diagnosis recorded | — | The three `test_simpleitk_cmake_data.py` parity tests pass |
| RITK-CI-2 | Test Suite (ubuntu-latest) exceeds the 30-minute job cap during 'Install LLVM and Clang'. | [patch] | **done 2026-08-19** — ritk PR #178 skips apt-get when clang already present | — | Ubuntu job completes inside budget |
| US-023-D2 | Block-matching follow-ons: multi-resolution search-region sources and block-radius calculators, FFT-accelerated NCC, Bayesian-regularized and strain-window displacement calculators, and an end-to-end pipeline over a block grid. | [minor] | **done 2026-08-19** — verified on ritk `origin/main` by content, not by claim: PR #187 (volume pipeline), PR #191 (strain-window rejection filter), PR #192 (the follow-ons, rescued per ATLAS-RITK-D2-STRANDED-100). Earlier history: — ritk PR #187 merged at `40618f84` (volume pipeline) is on main; the follow-ons are **not**: `c110664b` was never pushed, its branch no longer exists on the remote, and no PR was opened. See ATLAS-RITK-D2-STRANDED-100. Landed separately: strain-window *rejection* filter (ritk PR #191). The stranded commit adds: `OwnedPyramid` (nearest/min-max), block-radius calculators, FFT-NCC via apollo-fft (`fft` feature), `BayesianDisplacementPrior`, `StrainWindowRegularizer`, `DisplacementPipeline` | Claude | track_volume recovers known shift; strain recovers 2% compression exactly; pipeline recovers known compression strain within derived bound; 46/46 tests, clippy `-D warnings`, fmt clean |
| US-023-D4 | Move `block_matching` into a dependency-light crate; parameterize its sample type; reuse one candidate buffer across the search. | [arch] | done — ritk PR #183 merged (21/21 green) | Claude | Met. `cargo tree` = one edge (`anyhow`); 9 tests incl. cross-precision and 1-D line; ritk-registration 375 green |
| US-023-D3 | Consolidate kwavers' NCC + parabolic speckle-tracking kernel onto the block-matching seam and delete the duplicate. | [minor] | done — kwavers PR #409 merged (31/31 green) | Claude | Met. Both duplicates deleted, net -75 lines; 1551/1551 kwavers-physics tests pass through the seam; verified on origin/main by content |
| KW-GPU-SCANCONV | Remove the no-op `scan_conversion` stage from the kwavers-gpu realtime pipeline, which reported a scan-converted frame it never converted. | [patch] | **done 2026-08-19** — kwavers PR #405 merged at `ba1803e9`; the no-op call and stub are deleted from `realtime.rs`, `process_frame` ends at `log_compression` | Claude | CI green; behaviour unchanged (the removed call was the identity); content confirmed present in `origin/main` |
| US-023-A2 | `PhasedArray3D` variant on the ADR 0042 seam. | [minor] | **review** — ritk PR #188 `fix/phased-array-origin-direction`: batch and single-point transforms compose with image origin/direction | Claude | Non-zero origin correctly offsets world point; round-trip with origin; batch/single agree; 65/65 tests pass |
| US-023-A4 | `SliceSeries` variant on the ADR 0042 seam. Design settled by **ADR 0047**: owned per-slice rigid transform list (memory budget is three orders below the image it describes), composition with `Direction`, forward clamp / inverse reject out of range. `CoordinateMap` stops being `Copy`, so it lands as a breaking change. | [arch] | **done 2026-08-19** — ritk PR #180 merged at `40618f84` | Claude | Met. Round-trip within 1e-9; pure-translation sweep reproduces Cartesian exactly; single-slice degenerate; forward clamp; inverse rejection; 6 new tests; 5351/5351 workspace tests pass |
| US-023-A5 | Move `CoordinateMap`/`CurvilinearArray`/`PhasedArray3D` from `ritk-image` to `ritk-spatial` (pure `f64` geometry, no tensor coupling); `ritk-image` re-exports and keeps using them. | [minor] | **done 2026-08-13** — ritk PR #132 merged at `9ae68b45` | Claude | Met. Static review clean; no new P0/P1. `ritk-spatial` gains no new dependency. |
| US-023-A7 | Give `CurvilinearArray` an explicit `first_lateral_angle` instead of ITK's implied centre-on-boresight. Implemented in `ritk-spatial` via `try_new(first_lateral_angle)` + `centred()` helper for ITK compat. Geometry methods do not take `lateral_count`. | [major] | **done 2026-08-13** — implemented in ritk-spatial when PR #132 merged | — | Met. `try_new()` takes explicit `first_lateral_angle`; `centred()` provides ITK `-(n-1)/2·Δ` convention; no geometry method takes `lateral_count`. |
| US-023-A3 | kwavers `ScanConverter` delegates its polar math to the `ritk-spatial` geometry SSOT, keeping Leto storage and Aequitas typed geometry; the duplicated formulas in `b_mode/scan_conversion.rs` are deleted. | [minor] | done 2026-08-13 — kwavers `6731f8f32` on `codex/kwavers-floatelement-roots` | Claude | Met. Differential oracle replays the pre-migration formulas across the whole raster within a derived `1e-9` bound (`atan2` vs `atan` rounding; observed worst case `8e-12`, and a mis-indexed pixel would differ by `>= 1`). No polar formula remains in kwavers. 731 tests, clippy `-D warnings`, fmt clean |
| US-023-A6 | Decide whether B-mode moves behind the `kwavers` ritk bridge so scan conversion becomes a true `resample` through the seam and the converter is deleted outright. Splits the B-mode pipeline across crates, so it is a recorded decision, not an incidental one. | [arch] | **done 2026-08-20** — ADR 0048 Accepted; kwavers main at `b20eb48b` uses `ritk_spatial::CurvilinearArray` (the geometry SSOT per ADR 0042) directly in `ScanConverter::convert`. No bespoke polar arithmetic remains. PR #412 (ritk-image approach) closed as superseded: adding `ritk-image`/`coeus-core` to `kwavers-analysis` violates the architecture constraint that the analysis layer not depend on the tensor stack. The ritk-spatial path satisfies the ADR 0048 intent without that violation. | Claude | Met. No bespoke polar arithmetic in kwavers-analysis; `index_from_cartesian` on `CurvilinearArray` is the geometry SSOT; differential oracle test present in the b_mode suite. |
| US-023-B | QUS spectral tissue characterization — **increment 1 of 2**: gated Welch spectra, reference-phantom normalization, and Lizzi-Feleppa parameters (slope, intercept, midband). | [minor] | done 2026-08-13 — kwavers `33f4ce637` on main | Claude | Recovers known slope/intercept/attenuation from a synthesized RF phantom with an analytically derived tolerance; differential check against the forward scattering/attenuation physics kwavers already models |
| US-023-B2 | QUS increment 2: spectral-difference attenuation estimation (dB/MHz/cm). **Not ported from ITK**: implements Yao/Zagzebski/Madsen (1990) eq. (3) (stays in dB domain). | [minor] | **done 2026-08-19** — kwavers PR #404 merged at `8003eeaa`; `attenuation_from_spectra()` in `qus/attenuation.rs` | Claude | Met. Zero-attenuation oracle exact; known-attenuation recovery (slope 0.5, intercept 0.1 dB/(MHz·cm)) exact. 10/10 tests pass. |
| US-023-C | SRAD (Yu & Acton) speckle-reducing anisotropic diffusion in `ritk-filter/src/diffusion/`. | [minor] | done — ritk PR #169 merged | Claude | Value-semantic parity against the published formulation on a speckled phantom; edge-preservation asserted against Perona–Malik on the same input |
| US-023-D | Block-matching elastography framework — **increment 1**: metric-image and displacement-calculator seams, direct NCC, and max-pixel / parabolic / cosine refinement. | [arch] [minor] | **done 2026-08-18** — ritk PR #173 merged at `0f0b5c56` | Claude | Met. Exact integer translations recovered exactly; half-voxel shift lands strictly between integers and beats the integer estimate; gain/offset invariance asserted. 382 tests, clippy, fmt clean |
| US-023-E | Directional 1-D FFT frequency-domain filter over N-D images with a pluggable frequency-response function seam. | [minor] | **done 2026-08-19** — ritk PR #175 merged at 63e165ad | Claude | Met. 9/9 tests pass. |
| US-023-E2 | Ultrasound IO **increment 1**: persist the acquisition coordinate map through NRRD read/write, so beam data does not reload as a raster. | [minor] | done — ritk PR #174 merged | Claude |
| US-023-F | Ultrasound IO remainder: ITK's HDF5 ultrasound layout. **Decided: declined** — ADR 0046. ritk gains no HDF5/C dependency; NRRD carries acquisition geometry, and ITK/h5py convert at the boundary. Revisit trigger is a real acquisition source that emits only that format. | [arch] | done — ADR 0046 Accepted | Claude |

Review evidence for US-023-A2: the phased-array implementation is only exercised
with zero origin and identity direction. `Image::transform_*` and
`physical_points_to_continuous_indices` remain Cartesian-only, while the new
native and scalar phased branches ignore `Image` origin/direction metadata.
The geometry also converts generic scalar indices to `f64`, performs the
trigonometry there, and narrows back to `T`. PR #131 merged at `9ae68b45`, but
these source-level findings remain open against that default; the Atlas gitlink
tracks the merged head without treating merge as capability closure.

US-023-A3 audit note: the current kwavers `ScanConverter` accepts an arbitrary
`angle_min`, while the RITK curvilinear map centers the fan from the image beam
count. The cutover must either preserve that acquisition convention through a
validated map parameter or reject non-centred geometry before deleting the
converter; the existing bilinear differential remains the acceptance oracle.

## ATLAS-EUNOMIA-FLOAT-CBRT-014 — Land sign-preserving FloatElement::cbrt SSOT [feat]

- Owner: Atlas integration.
- Outcome: close the ATLAS-AEQUITAS-ROOT-OPS-012 SSOT follow-up. Eunomia now
  owns `FloatElement::cbrt` — `libm::cbrtf` default (correct reduced-precision
  path for `F16`/`Bf16`) with native `libm::cbrt` overrides for primitive
  `f64` and the `F64` wrapper — on `codex/eunomia-float-cbrt` (`bba10b6`).
  Aequitas' `Quantity::cbrt` switched off its `powf(1/3)` workaround onto the
  new SSOT seam (`cbrt(-8 m³) == -2 m`, no longer NaN) on
  `codex/aequitas-root-ops-closure` (`071538c`); the NaN-domain test is now a
  sign-preservation test. Both provider gate sets green: eunomia fmt, `-D
  warnings` all-targets, clippy, nextest 109/109, doctests; aequitas fmt,
  `-D warnings` all-targets, clippy, nextest 85/85, doctests, no-default.
- Status: delivered; both branches pushed. The final ATLAS-AEQUITAS-ROOT-OPS-012
  follow-up — semantics-marked dimension tuples (`ReciprocalVolume`,
  `Angle`) — is now closed too (see ATLAS-AEQUITAS-ROOT-OPS-012, `3ce7b03`).

## ATLAS-MNEMOSYNE-CONSUS-REFRESH-013 — Reconcile merged provider PM closeouts [patch]

- Owner: Atlas integration.
- Outcome: advance the Mnemosyne and Consus gitlinks to their merged default
  heads and synchronize the root evidence for the stale provider PM items.
- Acceptance: Mnemosyne `e57e2d6` and Consus `5163eb1` are recorded exactly;
  provider-owned Rust, Miri, package, platform, and documentation evidence is
  cited; exact-head, structural integration, and lane audits pass without
  staging peer-owned provider checkout changes.
- Status: complete in this root increment. Mnemosyne PR #44 merged after Rust
  verification plus Miri arena, Stacked Borrows, and Tree Borrows passed;
  Consus PR #21 merged with all repository-owned package, MSRV, platform,
  MinIO, and feature-matrix checks passing. The recurring `recurseml/analysis`
  result remains an external analyzer integration failure.

## ATLAS-AEQUITAS-ROOT-OPS-012 — Land aequitas rational-power sqrt/cbrt increment [feat]

- Owner: Atlas integration.
- Outcome: the pre-existing scalar-operator WIP (MulAssign/DivAssign, scalar
  * quantity) was already merged upstream via PR #21 (commit `dd0b8e1`,
  merge `0052b80`) with 9 value-semantic tests — verified complete in the
  current aequitas default; no further action needed for that axis. The
  remaining in-flight worktree WIP — type-level `SqrtDimension`/
  `CbrtDimension` plus `Quantity::sqrt`/`cbrt` through the `FloatElement`
  power surface — was reconciled with concurrent peer edits and landed as a
  completed, tested increment on `codex/aequitas-root-ops-closure`
  (`72ef8b4`): concrete exponent-tuple impls (8 sqrt shapes, 3 cbrt
  shapes), module wiring, 12 value-semantic tests, CHANGELOG, and review
  corrections (number-density tuple accuracy, `Div`-projection doc,
  `float_cmp` lint). All canonical gates green: fmt, `-D warnings`
  all-targets check, clippy `-D warnings` all-targets/`--all-features`,
  nextest 80/80, doctests 13/13, `--no-default-features` check.
- Status: delivered; aequitas branch pushed. Cargo.lock tooling residue
  (config-level `[patch]` overlay drift) left as pre-existing dirt.
- Tracked follow-ups (outside this increment): (1) SSOT — eunomia
  `FloatElement` gained a libm-backed sign-preserving `cbrt`
  (`libm::cbrtf`/`libm::cbrt`) and aequitas dropped the `powf(1/3)` path
  (ATLAS-EUNOMIA-FLOAT-CBRT-014: `bba10b6` + `071538c`). (2) semantics-marked
  dimensions (`ReciprocalVolume`, `Angle`) now have sqrt/cbrt impls — the
  tuple macros accept an input semantics type and normalize the output to
  `BaseSemantics` (`Angle::sqrt` → dimensionless, `ReciprocalVolume::cbrt` →
  reciprocal length), landed `3ce7b03` on
  `codex/aequitas-root-ops-closure` with 2 value-semantic tests. (3) a
  sign-preserving cbrt for negative operands is resolved by (1). All three
  follow-ups closed.

## ATLAS-TYCHE-REFRESH-011 — Reconcile merged Tyche PM closeout [patch]

- Owner: Atlas integration.
- Outcome: advance the Tyche gitlink to merged PM-closeout head `5efaee7` and
  record exact-head evidence for the completed consumer documentation slice.
- Status: complete; the root pointer now records `5efaee7`, and the exact-head
  audit scope is ready for final verification.

## ATLAS-LETO-PM-REFRESH-010 — Reconcile merged Leto PM closeout [patch]

- Owner: Atlas integration.
- Outcome: advance the Leto gitlink to the merged PM-closeout head and retain
  exact provider-head evidence without staging peer-owned Leto changes.
- Status: complete; Leto PR #107 merged as `e525d8d`, the root gitlink now
  records the exact default, and the pointer evidence is synchronized.

## ATLAS-LETO-CONVOLUTION-012 — Close provider convolution contract [major] [arch]

- Owner: Atlas integration.
- Outcome: close the stale Leto convolution-provider record after the generic
  CPU contract and Coeus direct consumer integration are both merged and
  exact-head verified.
- Status: complete; Leto PR #108 source `7172b338463c72faa2a561a3c84bda26d827351a`
  merged as default `a722fbc81cd1d82df74ef9e5acc1d9997d340d9d`. PR #108's
  exact provider run `31690152639` and post-merge default run `31690301356`
  pass. Coeus default `a4063be1` retains the direct consumer contract after
  PM-only PR #325; the root pointer is advanced without staging peer-owned
  checkout dirt.
- Residual: 33 pre-existing Leto Rustdoc broken/private-link warnings; no
  convolution-specific diagnostic. Hephaestus owns accelerator execution.

## ATLAS-MOIRAI-PM-REFRESH-009 — Reconcile merged Moirai default [patch]

- Owner: Atlas integration.
- Outcome: advance the Moirai gitlink to the merged PM-closeout head and
  synchronize the exact-head evidence for the full twenty-provider inventory.
- Scope: root `repos/moirai` gitlink plus current Atlas checklist/backlog/gap
  audit records; peer-owned Moirai checkout edits remain untouched.
- Status: complete; Moirai PR #125 merged as `ae9a5df`, the root gitlink now
  records that exact default, and the twenty-provider exact-head audit passes.

## ATLAS-LIVE-HEAD-SWEEP-008 — Reconcile moving provider defaults [patch]

- Owner: Atlas integration.
- Outcome: refresh the root gitlinks for provider defaults that advanced after
  the preceding exact-head check and preserve current hosted evidence.
- Scope: root `repos/mnemosyne` and `repos/hermes` gitlinks plus synchronized
  Atlas PM records; provider source, locks, and peer-owned checkouts are
  excluded.
- Acceptance: Mnemosyne `1ad5819` and Hermes `5785143` exact-head hosted CI
  passes; both committed gitlinks match fetched defaults; the root exact-head,
  coherence, and lane audits pass.
- Status: complete after exact-head CI; the pointer and evidence commit are
  delivered in this integration increment.

## ATLAS-HEPHAESTUS-REFRESH-007 — Integrate cross-entropy PM closeout [patch]

- Owner: Atlas integration.
- Outcome: advance the Hephaestus root gitlink and root evidence after the
  provider merged its cross-entropy PM closeout.
- Scope: root `repos/hephaestus` gitlink and synchronized Atlas PM records;
  preserve the provider checkout's peer-owned dirty `Cargo.lock`.
- Acceptance: fetched `origin/master` hosted WGPU, CUDA, ROCm, and Metal runs
  pass at the merged provider head; the root gitlink equals that head; the
  provider PM closure and exact-head root checks are recorded.
- Status: complete at provider head `9385686`; the Atlas pointer and evidence
  are delivered in this integration increment.

## ATLAS-PROVIDER-DRIFT-005 — Post-merge exact-head convergence [patch]

- Owner: Atlas integration.
- Outcome: advance the two provider gitlinks that moved after the prior
  integration closure and make the committed audit guard verify fetched
  default heads when requested.
- Scope: root `repos/mnemosyne` and `repos/ritk` gitlinks, the provider
  integration audit script and its tests, and synchronized root PM records.
  Provider source, locks, and peer-owned working-tree changes are excluded.
- Acceptance: both gitlinks equal their fetched default heads (`32524e3` and
  `53bb013`), exact-head mode detects mismatch and supports non-`main`
  defaults, focused script tests pass, and the item records hosted evidence.
- Status: complete at Atlas `062afef` (branch `codex/atlas-provider-drift-005`).
  Exact-head structural mode and the focused eight-test regression suite pass.

## ATLAS-PROVIDER-INTEGRATION-004 — Twenty-one-provider audit and cleanup [major]

- Owner: Atlas integration plus provider-owned cleanup follow-ups.
- Outcome: keep all 21 requested provider gitlinks, hosted evidence, audit
  inventory, book content, workflow security, and worktree topology coherent.
- Acceptance: exact gitlinks match fetched default heads; the committed audit
  reports 21 providers; provider book placeholders are absent from delivered
  heads; substantive hosted gates pass; mutable action refs and non-linked
  worktree directories are either fixed or recorded with an owner and trigger.
- Status: exact-head integration closure at Atlas `48a257d`; provider source
  follow-ups remain tracked below. Consus book closure merged as
  PR #19; Coeus book and reusable-workflow closures merged as PRs #321 and
  #322. Provider workflow action pinning and reusable-workflow refreshes are
  merged. Exact gitlinks, hosted gates, workflow scans, book scan, and lane
  audit are green.

## ATLAS-RITK-EUNOMIA-001 — RITK Eunomia 0.8 local closure — 2026-08-10

- RITK's workspace manifest and standalone lock now resolve Eunomia `0.8.0`
  with `rkyv 0.8.17`; no active RITK manifest requests Eunomia 0.7.
- Removed the stale Windows-only `missing_const_for_thread_local` expectation
  from `repos/ritk/crates/ritk-filter/src/morphology/mod.rs`. The initializer
  was already const-compatible under Rust 1.97; the expectation itself failed
  under `-D warnings` as unfulfilled. No morphology behavior changed.
- RITK repository-owned validation is green at the reconciled standalone lock:
  locked metadata, formatting, strict all-target/all-feature Clippy, workspace
  doctests, and workspace Rustdoc pass; full Nextest passes 5,137/5,137 with
  24 configured skips, and the focused `ritk-filter` suite passes 1,123/1,123.
- The Atlas overlay was bypassed only for standalone lock/gate verification and
  restored afterward. Existing RITK peer dirt in `CHANGELOG.md`, `Cargo.lock`,
  filter/interpolation/Python sources remains preserved; no child reset, clean,
  commit, push, or gitlink advance was performed.
- Local closure is complete. Hosted security, exact-head owner review, package
  archive verification, crates.io/PyPI indexing/publication, trusted-publisher
  enforcement, and merge remain external release gates; the broader RITK
  historical backlog is not claimed complete by this slice.

### Melinoe/Mnemosyne/Apollo boundary adoption — 2026-08-10

- Apollo validation now has a test-only `mnemosyne-memory` workspace dependency
  and a focused `BrandedVec -> BrandedCell<[T]>` boundary contract in
  `crates/apollo-validation/src/application/suite/tests.rs`. The contract
  validates branded allocation, token-gated slice borrowing, mutation, and
  post-mutation reads through Mnemosyne's public facade; Apollo does not reach
  into Melinoe internals for this memory boundary.
- `rustfmt --check` and the focused Apollo test pass (`1/1`). The initial link
  attempt was blocked by the absent `D:/msys64/tmp` directory; the required
  environment directory was created and the final link/test run passes. Apollo's
  lockfile was reconciled from the final manifest: the `apollo-validation`
  package now records its `mnemosyne-memory` dev edge and the standalone locked
  focused test plus `--lib` check pass with the Atlas overlay bypassed. The
  reconciliation also materialized the workspace's git sources and removed
  overlay-only `[[patch.unused]]` noise; it is broader than a one-line Melinoe
  edit and remains uncommitted alongside existing Apollo peer state.
- The slice is intentionally test-only: Mnemosyne remains the memory SSOT,
  Melinoe remains the generativity SSOT, and no provider, Moirai, or Apollo
  runtime source was changed.

### Melinoe/Moirai partition-result adoption — 2026-08-10

- Added `moirai-parallel/src/tests.rs::test_par_partition_map_preserves_partition_order`
  as a consumer contract for the existing Melinoe-backed
  `par_partition_map` bridge. The test proves that disjoint branded shards can
  return ordered per-partition results while the original cells remain readable
  through the brand token.
- The change is intentionally test-only and leaves Moirai scheduler queue
  ownership, the Melinoe provider, and the peer-dirty executor bridge untouched.
  `rustfmt --check` and `git diff --check` pass; the reconciled standalone
  lockfile now pins Melinoe to delivered `47863b12aa0cd4e65cb9556b2c9bbf1353a5ee26`.
  Locked metadata and library check pass, and the Melinoe-enabled focused suite
  passes 33/33 with the Atlas overlay bypassed. The broad generated lock diff
  remains uncommitted with peer work.
- The Moirai test change and reconciled Cargo.lock remain uncommitted in the
  peer worktree; no provider reset, cleanup, commit, push, or gitlink advance
  was performed.

## ATLAS-ARCH-011 — Retire hephaestus-metal per ADR 0047 [arch] [major] — blocked

- Owner: claude/fable-loop (claimed 2026-08-03); scope: `repos/hephaestus`
  (`crates/hephaestus-metal`, the
  workspace member list, the `hephaestus` facade's `metal` feature, and the
  conformance suite's Metal instantiation). Coeus is **out of scope** — see
  the note under ATLAS-SUBSTRATE-002.
- Outcome: the crate and its 5 449 forwarding lines plus 2 606 test lines are
  deleted. Metal targeting survives unchanged as
  `WgpuDevice::try_metal(...)`, and the vendor identity as
  `device.adapter_info().map(|i| i.backend)`.
- The facade's `metal` feature is **kept and re-pointed**, so consumers'
  spelling of intent survives the removal: it comes to mean "acquire a
  Metal-preferring `WgpuDevice`" instead of "compile a second copy of the
  operation surface".
- Acceptance oracle: (a) `cargo nextest run` green for the hephaestus
  workspace at `--all-targets` with the member entry gone, and the `metal`
  feature seam building in its re-pointed form; (b) the conformance suite
  passes with the Metal instantiation removed and no clause left
  unreferenced; (c) a stack-wide grep finds no `hephaestus_metal` reference
  outside Coeus's tracked item; (d) the two CFDrs `backend_name()`
  assertions still pass, confirming no observable contract moved.
- Risk/change class: `[major]` — a published crate is removed. Needs a
  CHANGELOG entry under Unreleased with the one-line migration
  (`MetalDevice::try_default` → `WgpuDevice::try_metal`). Release itself
  stays outside this item's authority.
- Verification note: coverage is not lost. The Metal instantiation ran the
  same clauses over the same code path as the WGPU one, so it asserted
  nothing WGPU does not already assert; Metal-*adapter* coverage is a
  question of which adapter CI acquires, not of which crate the suite names.
- Dependencies: **ATLAS-SUBSTRATE-002** (see the blocker below). ADR 0047 is
  Accepted; the decision is not in question, only its sequencing.
- **BLOCKED 2026-08-03, discovered by executing it.** The hephaestus-side
  removal is mechanically complete and was verified to that point — member
  entry, workspace dep, the facade's optional dep and its three `?/` feature
  entries, the `metal` feature re-pointed to `["wgpu"]`, the
  `pub use hephaestus_metal as metal` re-export, and the crate itself, with
  `cargo metadata` green and **zero** residual `hephaestus_metal` references
  in any `.rs`/`.toml` under `repos/hephaestus`. It was then reverted, for
  the reason below.
- **`repos/coeus` depends on `hephaestus-metal`** (`coeus/Cargo.toml:59`, and
  `coeus/crates/coeus-metal/` consumes it). The ADR scoped Coeus out on the
  grounds that its collapse is SUBSTRATE-002's business — that scoping was
  wrong, and the stack overlay is what proves it: the overlay is generated
  from the *dependency closure*, so while any member declares
  `hephaestus-metal`, it emits a `[patch]` pointing at the deleted crate
  directory and **every build beneath the stack root fails**, not just
  Coeus's. Upstream removal and the consumer edge are one co-evolution unit.
- Cutting that edge is not available: `repos/coeus` is on a live peer's
  `codex/coeus-publish-cycle` branch, and the Coeus board claims
  `coeus-hephaestus`, `coeus-rocm`, `coeus-metal` under Codex
  (`coeus/docs/backlog.md:464`) — a fresh, commit-backed claim over exactly
  the files this needs, mid-publish-cycle. Deleting a crate out from under a
  publish cycle is the one thing not to do here.
- Re-open trigger: `repos/coeus` no longer declares `hephaestus-metal` —
  i.e. ATLAS-SUBSTRATE-002 deletes `coeus-metal`, or the peer's publish cycle
  completes and its claim is released. Then re-apply the hephaestus removal
  (it is a ~15-minute mechanical replay of the list above) and land both
  repos as one unit.
- Sizing note for whoever takes SUBSTRATE-002's metal slice: `coeus-metal` is
  1 233 lines with **zero in-repo dependents** — no manifest outside the
  workspace member list names it, and the only code references are its own
  tests. It is a file-for-file copy of `coeus-rocm` (per-file diffs of 0, 0,
  0, 2, 17, 25 lines after normalizing the vendor token), and
  `coeus-hephaestus` already implements the whole op surface generically for
  `HephaestusBackend<P>`. The only content not reproducible from a ~56-line
  provider marker is one `fill_zero` override.

## ATLAS-OVERLAY-GEN-STALE-1 — Cross-repo path deps on member mainlines [arch] — todo (needs user decision)

- Owner: unclaimed; scope: `.cargo/config.toml`, `scripts/atlas-stack-overlay.py`,
  and the member manifests listed below. **Held for a user decision** — see the
  conflict at the end.
- **My 2026-08-03 diagnosis on this item was wrong and is corrected here.** I
  filed it as "the generator is stale against the package renames". It is not.
  Run twice in a row the generator is byte-identical (`cmp` clean), and it emits
  the same 38-line reduction against the committed overlay each time. It is
  idempotent and its output is *correct*.
- The real cause: the generator derives the overlay from the **git**-dependency
  closure, and six members no longer declare git dependencies — they were
  migrated to cross-repo path dependencies. So the generator rightly stops
  emitting patches for them, and the committed overlay is what is stale,
  carrying dead entries (`apollo-nufft`, `apollo-sht`, `asclepius-coeus`,
  `athena-leto`, and an entire `[patch."…/coeus"]` section).
- Measured 2026-08-03, path deps that **escape their own repo** (intra-workspace
  **(CORRECTED below — this measured worktrees, not committed state.)**
  `../sibling` paths excluded by resolving each path against its repo root):
  athena 36, and 25 in a private consumer — those two are the only ones
  actually committed. The kwavers/helios/ritk/CFDrs counts in the original
  measurement were uncommitted worktree edits and are withdrawn.
- **Correction 2026-08-03.** My original figure of 163 across six members read
  working trees. Committed state across the whole stack is: **athena 36** (the
  sole tracked member carrying committed cross-repo path deps, and red on CI
  for exactly that), plus 25 in the untracked private consumer. Every other
  member's committed manifests are clean `git + version`.
- That shrinks the decision considerably: it is about athena, not about a
  stack-wide cutover. athena's `[patch]` at `Cargo.toml:119-120` plus its
  path deps are what keep its CI red.
- Method note for anyone re-measuring — this is the second time I generalized
  from worktree state (the first was the lockfile survey under
  ATLAS-PUB-LOCK-1). Under the overlay, working trees routinely diverge from
  HEAD. Always read `git show HEAD:<path>`, and for anything about how a
  consumer or runner sees the repo, clone it in isolation:
  `git clone --depth 1 file:///D:/atlas/repos/<name> /d/tmp/isolated/<name>`.
  athena 36, kwavers 31, helios 29, ritk 22, CFDrs 20, plus 25 in a private
  downstream consumer —
  **163 total**. Example: `repos/kwavers/Cargo.toml` → `../../repos/aequitas`.
- These landed deliberately in `b2ee610` ("Migrate kwavers/cfdrs/helios/ritk to
  local path deps", authored by a non-Claude agent). Two notes on that commit:
  its body claims the migration covers manifests whose recorded gitlinks do not
  in fact contain it, and it states plainly that it landed with builds still
  failing ("remaining build failures are pre-existing code errors").
- **The conflict, which is why this is not being fixed unilaterally.** Standing
  stack policy is that member manifests keep `git + version` sources and the
  root `[patch]` overlay owns local resolution — a member carrying path deps is
  unconsumable as a git dependency, and the two mechanisms now contradict each
  other. The mechanical fix is to convert all 163 back and regenerate. But that
  is a 6-repo revert of another agent's deliberate, stated intent, and three of
  those repos currently have live peer branches (`coeus` mid-publish-cycle,
  `CFDrs` on a codex branch, `ritk` on a feature branch). Reverting a peer's
  intentional migration at that blast radius is a call for the user, not for an
  autonomous tick.
- Whichever way it goes, one of the two mechanisms should be retired rather than
  left in contradiction: either the path deps convert back and the overlay stays
  authoritative, or the overlay is deliberately narrowed and the generator's
  freshness check updated so `generate` stops looking like a regression.
- **Concrete consequence found 2026-08-03: this breaks CI, not just theory.**
  `athena` has been red for five days with
  `failed to load source for dependency themis` / `unable to update
  /github/themis`. Its manifest carries a committed
  `[patch."https://github.com/ryancinsight/themis"] themis = { path = "../themis" }`
  (`athena/Cargo.toml:119-120`). That resolves inside the Atlas tree and cannot
  resolve on a runner that checks out one repo — which is exactly the property
  that makes a member unconsumable as a git dependency.
- So the cost of leaving this unresolved is now measurable: at least one member
  is permanently red, and any repo that gains cross-repo path deps joins it.
  athena is deliberately **not** fixed here — removing that `[patch]` is the
  decision this item is waiting on, and athena additionally needs the
  ATLAS-PUB-LOCK-1 lock repair, so its CI will not go green from either fix
  alone.
- Note for whoever measures this again: a naive `grep 'path = "\.\./'` is
  useless here — it counts ordinary intra-workspace sibling paths and reported
  473. Resolve each path against its repo root and keep only the escapes.


## ATLAS-ARCH-005 — Replace closed-set dyn dispatch in per-timestep paths [arch] — in-progress

- Owner: opencode-2026-08-05 (ADR phase delivered, ADR 0041; execution slice parked —
  both scope repos peer-held today: kwavers `refactor/retire-kwavers-optics`
  `e4e9966b6`, CFDrs `deps/eunomia-0.8`). scope: `repos/kwavers` first (largest), then
  `repos/CFDrs`.
  One operation family per claim.
- Outcome: dispatch-site counts are `kwavers` 665, `CFDrs` 352, `gaia` 104,
  `coeus` 98, `moirai` 83, `consus` 66. Sampling the kwavers solver shows the
  pattern is not type erasure of an open plugin set but vtable dispatch over
  closed design-time sets: `sources: &[Box<dyn Source>]` inside
  `forward/nonlinear/westervelt/update.rs` (evaluated per timestep),
  `boundary: Box<dyn Boundary>` held in the solver struct, plus `Box<dyn Signal>`
  and `Box<dyn Solver>`.
- Decision rule: a closed implementor set dispatched per timestep converts to an
  exhaustiveness-checked enum — static dispatch, still runtime-selectable, no
  vtable. Genuinely open plugin boundaries on cold paths keep `dyn` with the
  applicable exception annotated inline.
- Acceptance: per family, the count of `dyn` sites on the timestep path reaches
  zero; the enum is exhaustively matched with no catch-all arm; a criterion
  comparison on the affected kernel accompanies the change, since this is a
  performance-motivated claim and must carry performance evidence.
- Non-goals: mass-converting all 1 368 sites. Hot paths first, evidence per family.

## ATLAS-ARCH-008 — Replace pointer-scattered containers on traversal paths [patch] — in progress (2026-08-18)

- Owner: current session; scope for this increment is the root classifier and
  its focused tests, not provider source or the hotness-ranked conversions.
  The scanner currently traverses `repos/consus/worktrees/*`, so a peer lane is
  counted as a second provider source and makes the live site set depend on
  lane topology.
- **Current increment evidence:** the focused classifier suite is 44/44 after
  adding a lane-exclusion regression. The live scan is now 242 production and
  98 test/bench sites with zero `worktrees/` paths. The committed oracle still
  reports 35 additions and 36 removals because peer provider edits and line
  shifts are present in the shared tree; it is not regenerated from that
  unstable state.
- Outcome: 318 `Vec<Vec<_>>` occurrences across package sources, led by
  `consus-compression/src/chunking/iterator.rs` (10),
  `gaia/src/domain/topology/adjacency.rs` (8), and
  `coeus-autograd/src/ops/nn/loss/ctc.rs` (6). Adjacency and chunk iteration are
  prefetch-sensitive; a jagged per-row allocation defeats it.
- Acceptance: the contiguous form is a flat buffer plus an offset table
  (CSR-shaped) or an arena span, with a criterion comparison on the traversal
  showing the change is a win. A site where the jagged shape is genuinely correct
  is recorded as such rather than converted.
- **Evidence re-measured 2026-08-03; two of the three named sites are wrong.**
  Verify before claiming — as written this item would send someone to rewrite
  test code.
  - `consus-compression/src/chunking/iterator.rs` (listed as the worst, 10
    occurrences): **all 10 are test-local.** `#[cfg(test)] mod tests` opens at
    line 156 of a 400-line file and every occurrence is at lines 167-383, each
    a `let coords: Vec<Vec<usize>> = ChunkIterator::new(..).collect()`
    collecting an iterator's output for an assertion. That is not a container
    on a traversal path; it is a test binding, and converting it would be
    rewriting tests to suit a metric.
  - `gaia/src/domain/topology/adjacency.rs` (listed at 8): now **zero**
    occurrences. The file is 679 lines and no longer contains the pattern.
  - The raw stack-wide count is ~370, up from the recorded 318, so the
    headline number is not shrinking even though its named exemplars have
    evaporated — which is the signal that the count is measuring the pattern,
    not the defect.
- What the item still needs before it is claimable: a classifier that
  separates production containers from `#[cfg(test)]`-local and
  `tests/`/`benches/` bindings. I wrote one and do not trust it — it
  mis-classified `kwavers-math/.../lsqr/tests.rs` as production, so its
  per-repo split is not recorded here rather than recorded wrongly. The
  two corrections above were each confirmed by reading the file.
- Re-scoped acceptance: the deliverable is first a *correct site list* —
  production-only, ranked by traversal hotness rather than raw count — and
  only then the CSR conversions with their criterion evidence. A raw
  `Vec<Vec<` count is not a defect list.
- **Site list delivered 2026-08-03.** A classifier now separates production
  containers from `#[cfg(test)]`-guarded and `tests/`/`benches/`/`examples/`
  bindings, and it carries two self-checks derived from files read by hand —
  it refuses to print numbers unless it reproduces both. That gate earned its
  keep: the first version failed, because it matched only the bare
  `#[cfg(test)]` and the consus module is gated
  `#[cfg(all(test, feature = "alloc"))]`. Any cfg predicate carrying a bare
  `test` token now counts, with string literals stripped first so a
  `feature = "test-utils"` value cannot pose as the predicate.
- Verified totals: **297 production, 73 test/bench-local** (370 raw). So ~20%
  of the recorded 318 was never a defect.
- **There is no hotspot, and that changes how this item should be worked.**
  Production counts per repo are ritk 81, kwavers 70, CFDrs 46, gaia 37,
  consus 24, coeus 12, apollo 6, moirai 5, leto 2 — but the top *file* has 10
  (in a private downstream consumer, out of stack scope), the next has 6, and
  everything after is a tail of 4s and 3s across unrelated subsystems
  (`coeus-autograd/.../ctc.rs` 6; `ritk-vtk/.../poly_data.rs`,
  `ritk-filter/.../anti_alias_binary/solver.rs`,
  `cfd-optim/.../search/genetic.rs`, `consus/src/sync/mod.rs` 4 each).
  There is no "fix the top three files" increment available.
- Consequence for the acceptance oracle: ranking by *count* is worthless here.
  A claimant should pick sites by traversal hotness — profile first, per the
  measurement-first rule — and convert the ones that a profile implicates,
  recording the rest as correct-as-jagged. The classifier lives in the session
  scratchpad; it should be committed under `scripts/` if this item is claimed,
  since re-deriving it is the expensive part (toil automation).
- **Delivered 2026-08-05 — classifier committed, site list refreshed.**
  `scripts/atlas_scattered_containers_classify.py` is the committed,
  reproducible form (underscore-named and importable, matching the
  testable-script convention), with pytest coverage in
  `scripts/tests/test_atlas_scattered_containers_classify.py` (24 tests:
  production vs test/bench/example split, `#[cfg(test)]`/`mod tests`
  brace-depth tracking, comment/string/char/raw-literal stripping with
  char-vs-lifetime disambiguation and multiline-string state, `cfg(not(test))`
  and `feature = "test-utils"` exclusions, filename heuristics, semicolon-line
  leak guard, determinism). It scans only the `.gitmodules`-registered members via
  `atlas_stack.registered_members()`, so the git-ignored private consumer
  never surfaces. Refreshed verification totals on the 2026-08-05 tree:
  **260 production / 65 test-bench / 325 total**, per member — CFDrs 42/11,
  apollo 6/2, coeus 12/0, consus 20/15, gaia 34/2, kwavers 63/5, leto 3/13,
  mnemosyne 0/1, moirai 6/9, ritk 74/7. The delta vs the 2026-08-03 recording
  (297/73/370) is tree drift plus method differences: this implementation
  strips comments, string/char/raw literals and block comments before any
  matching (so a `feature = "test-utils"` value or a `"mod tests {"` template
  string cannot arm a predicate and commented `Vec<Vec<` sites are not
  counted), narrows the test-filename heuristic to `tests.rs`/`*_test.rs`/
  `bench.rs`-style names (so `test_utils.rs` helpers stay production), and
  emits root-relative site paths; the committed script is the reproducible
  oracle going forward. The production-only site list is
  regenerated with
  `python scripts/atlas_scattered_containers_classify.py --site-list
  scripts/oracles/arch-008-production-sites.txt` (see the gate bullet
  below). Ranking by traversal hotness
  (profile-first) and the conversions themselves remain the open work — this
  item stays `todo`.
- **First conversion delivered 2026-08-05 — moirai collective family.**
  `repos/moirai` `moirai-core/src/communication/collective.rs`:
  `CollectiveOps::{scatter,gather,all_to_all}` now build and traverse a
  CSR-shaped `ChunkedVec<T>` (contiguous flat buffer + chunk-offset table)
  instead of jagged `Vec<Vec<T>>`. Semantics preserved exactly (chunk tiling,
  all-to-all column truncation at the chunk count); the empty-input / zero-
  participant edge returns an empty buffer rather than the historical
  `chunks(0)` panic. Consumers were verified tests-only, so the signature
  change is contained. Criterion
  (`benchmarks/benches/collective_ops_comparison.rs`, `harness = false`,
  jagged baselines kept inline, 32/128 participants × 4096/8192 items):
  gather **~10–13×** faster (O(1) hand-off), traverse **~1.6×**, scatter
  **~1.1–2.2×**, all_to_all **~1.3–3.2×** — a win on every measured path.
  moirai-core gate: check 0, collective nextest 4/4 (round-trip, empty/
  zero-participant, all-to-all parity), strict clippy 0.
  `channel_fusion` per-channel buffers are recorded as **correct-as-jagged**:
  each channel grows and flushes independently, so a shared flat buffer would
  add reallocation complexity without a traversal win. `owned_chunks`
  (hybrid.rs) stays owned-per-worker by contract (parallel ownership model);
  it is a candidate only if its consumers move to borrowed chunks. The next
  conversion should be picked from a different repo family per the
  one-family-per-claim rule.
- **Oracle gate wired 2026-08-05 — the split can no longer drift silently.**
  `scripts/atlas_scattered_containers_classify.py --verify-oracle
  scripts/oracles/arch-008-production-sites.txt` re-verifies the current
  production split against the committed oracle (read-only; exit 0 = match,
  1 = drift, 2 = unreadable oracle), wired as `make verify-scattered-oracle`
  following the `fmt-check`/`board-lint` convention. `outputs/` is gitignored
  by design (derived state), so the oracle now lives at the tracked path
  `scripts/oracles/arch-008-production-sites.txt` and is regenerated
  deliberately with `--site-list` and committed in the same change that
  caused the drift. Oracle refresh after the moirai conversion:
  **256 production / 71 test-bench / 327 total** (per member — CFDrs 42/11,
  apollo 6/2, coeus 12/0, consus 20/15, gaia 34/2, kwavers 63/5, leto 3/13,
  mnemosyne 0/1, moirai 2/15, ritk 74/7). The sole delta vs the recorded
  260/65/325 is the moirai conversion: −4 production sites (the
  `collective.rs` family left the scattered set) and +6 test-local sites
  (the new parity tests build jagged vectors). The 2 remaining moirai
  production sites are `channel_fusion` and `owned_chunks`, both recorded
  correct-as-jagged / owned-by-contract above. Verify-mode coverage:
  `scripts/tests/test_atlas_scattered_containers_classify.py` gained
  oracle-parse, added/removed drift, blank/member-suffix tolerance, and CLI
  exit-code (0/1/2) tests (classifier suite now 32; full scripts suite 92 +
  20 subtests).
- **Spot-check 2026-08-05 — classifier matches a manual read.** Hand-verified
  the top per-member production files and the complete discrepancy set for
  ritk (74), kwavers (63), CFDrs (42): all 33 production sites in the top 3
  files per member match the oracle exactly (raw `Vec<Vec<` lines == oracle
  claims, same lines), and all 39 occurrences the classifier excluded from
  production were confirmed by hand to be comment/doc text (16 — stripped,
  never counted) or test/bench/example code (23 — counted test-local, e.g.
  the `#[cfg(test)]`-guarded `clahe_2d` in interpolate.rs:168 and the
  `#[cfg(test)] mod tests` VOF reconstruction.rs cases exercise the
  brace-depth path; `tests.rs`/`tests/`/`examples/` paths exercise the
  heuristics). Zero production code misclassified as test and zero test code
  counted as production. Read-only; no tree edits.
- **Spot-check 2026-08-05 — mid-count members + claimed-sites sweep; classifier
  extended; oracle corrected 256/71 → 250/77.** Hand-verified the six remaining
  members (gaia 34, consus 20, coeus 12, apollo 6, leto 3, mnemosyne 0) with
  the same discrepancy-set method: every top-file raw `Vec<Vec<` line matches
  the oracle claims (all 34 gaia, 20 consus, 12 coeus, 6 apollo, 3 leto
  claims), every excluded occurrence (doc comments, in-file `#[cfg(test)]` /
  `mod tests` regions, `tests/`/`examples/` paths) confirmed non-production,
  and a reverse stale-check confirmed all 75 mid-count claims point at live
  `Vec<Vec<` lines. The claimed-sites direction then surfaced a genuine
  classifier blind spot: it could not see **include-site gates**
  (`#[cfg(test)] mod <name>;` declared in a parent module) or bare
  `#[test]`/`proptest!` regions, so whole test-only files were misreported as
  production. The earlier top-member spot-check verified the excluded-direction
  only; the claimed-sites sweep here is what caught the remaining sites.
- **Classifier fix.** `compute_test_regions` now also treats `#[test]`
  attributes and `proptest! {` blocks as test regions, and `classify_file`
  gains `_is_include_gated`: it locates the file's `mod <name>;` declaration
  (`dir/mod.rs`, sibling `dir.rs`, `src/lib.rs`/`src/main.rs`, or crate-root
  `mod <dir>;` for `dir/mod.rs`) and checks the stacked attributes directly
  above it, stopping at the first non-attribute line so a cfg attribute of a
  *previous* declaration never leaks (the `boolean_csg` regression: its
  `#[cfg(test)]` belongs to the neighbouring `adversarial_tests_2`, and its
  claims are genuinely production). Files loaded under an arbitrary module
  name via `#[path = "..."]` (e.g. `#[cfg(test)] #[path = "tests_ply.rs"]
  mod tests;`) are covered by a per-member `#[path]`-declaration map keyed by
  the *resolved* target path (`#[path]` is relative to the declaring file's
  directory) — a basename key would collide on the many `mod.rs` modules and
  wrongly gate unrelated production files (caught live: the MGH reader, DICOM
  directory scanner and DICOM Association SCU `mod.rs` files are production
  and stay claimed). 11 new unit tests (classifier suite now 43) cover
  include-gated module, plain include, previous-declaration leak, dir module,
  `#[test]` fn, `#[test]` non-leak, `proptest!` block, and the `#[path]` map
  + stacked-attribute gate. Residual, deliberately-conservative blind spots
  (test code kept as production, never the reverse): a `mod foo;` nested
  inside an in-file `#[cfg(test)]` block of the parent, a `//` comment between
  the attribute and the `mod` declaration, `#[cfg_attr(test, ...)]`, and
  parenthesized `proptest!(...)`.
- **Corrected oracle: 250 production / 77 test-bench / 327 total** (was
  256/71 — total unchanged, pure reclassification). Six sites moved
  production → test-local, all hand-verified genuine test code: consus
  `reader_proptest.rs:151` and `tests_extra.rs:101` (include-gated), and ritk
  `tests_staple.rs:142,243` (include-gated) and `tests_ply.rs:89,123`
  (include-gated via stacked `#[path]` attribute, plus `#[test]` regions).
  Corrected per-member split: CFDrs 42/11, apollo 6/2, coeus 12/0, consus
  18/17, gaia 34/2, kwavers 63/5, leto 3/13, mnemosyne 0/1, moirai 2/15,
  ritk 70/11. Final independent verification: all 250 committed claims are
  live `Vec<Vec<` lines and none classify as test under the committed logic;
  `make verify-scattered-oracle` passes on the corrected oracle.
- **Second conversion 2026-08-05 — ritk-vtk Laplacian adjacency family.**
  `repos/ritk` `ritk-vtk/src/domain/filters/smooth.rs`: the smoothing
  filter's `build_adjacency`/`laplacian_step` now use a CSR-shaped
  `Adjacency` (contiguous `neighbors` buffer + per-vertex `offsets` table —
  the VTK `VtkCellArray` layout) instead of jagged `Vec<Vec<u32>>`. The
  build is jagged-free (degree count → prefix-sum offsets → direct flat fill
  → in-place sort+dedup per run), so the oracle site `smooth.rs:133`
  disappears rather than moves; the sorted/deduped layout is fully
  deterministic where the old `HashSet` build left neighbor order
  implementation-defined. Neighbor *sets* are unchanged, so filter results
  are preserved to within the existing 1e-5 test tolerance; a parity test
  pins the CSR runs against the sorted jagged reference (polygon + line
  edges, an isolated vertex, and a quad-grid interior vertex with its four
  edge-sharing neighbors sorted/deduped). `Adjacency` and `Adjacency::build`
  become documented public API (the only API change; `laplacian_step` stays
  private) so the criterion bench measures the production path. Criterion
  (`crates/ritk-vtk/benches/smooth_adjacency_comparison.rs`, `harness =
  false`, jagged baseline kept inline, 4096/16384-vertex quad grids): build
  **~7.8× at 4096 / ~8.5× at 16384** faster (857.7→110.5 µs / 3.523→0.415
  ms) — the CSR build replaces one `HashSet` allocation per vertex with a
  single flat buffer; traversal **~1.07× at 16384** (78.5→73.2 µs) and
  statistically flat at 4096, the short degree-4 runs amortizing the layout
  win — the honest headline is the build, which runs once per filter
  invocation while traversal runs once per iteration. Oracle regenerated to
  **249/78/327** (ritk 69/12): the smooth.rs production claim moved to the
  bench baseline, where the pre-conversion formulation lives by design
  (mirroring the moirai bench precedent). Gate: `ritk-vtk` nextest 258/258,
  warning-denied Clippy, fmt clean, `make verify-scattered-oracle` exit 0.
  The other named ritk families were assessed and deliberately left
  unclaimed this slice: `ritk-filter/.../anti_alias_binary/solver.rs`
  layers are a push-front/pop-front work-queue — CSR would turn every front
  insert into an O(n) memmove across all layers (**correct-as-jagged**),
  and `ritk-vtk poly_data.rs` cell arrays are the native CSR end state but a
  ~225-reference data-model migration that warrants its own dedicated claim.
- **Third conversion 2026-08-05 — Apollo CWT output buffer.**
  `repos/apollo/crates/apollo-wavelet/src/application/execution/plan/cwt.rs`
  now collects the row-major `(scales, signal_len)` coefficient matrix through
  `moirai::map_collect_index_with::<moirai::Adaptive>` into one flat buffer,
  then reshapes it into the existing `leto::Array2`. This removes the
  per-scale `Vec<Vec<f64>>` intermediate and its row allocations while
  preserving indexed output order, adaptive parallel execution, and the public
  `CwtCoefficients` API. The flattened dimension is checked with `checked_mul`
  and returns `CoefficientShapeMismatch` on overflow. The selected production
  site is gone rather than moved; no DWT coefficient API was changed because
  those vectors represent intentionally level-shaped detail bands and remain
  correct-as-jagged for this slice. Evidence: Apollo `cargo check -p
  apollo-wavelet`, rustfmt, strict Clippy, doctests, and `cargo nextest run -p
  apollo-wavelet --lib` **21/21** pass; `git diff --check` and the targeted
  no-`Vec<Vec<` residue scan are clean. The separate oracle gate reports the
  expected single stale claim at `cwt.rs:72` (current split **248 production /
  78 test-bench / 326 total**); oracle refresh is intentionally deferred because
  `scripts/atlas_scattered_containers_classify.py` and
  `scripts/oracles/arch-008-production-sites.txt` are pre-existing untracked
  artifacts owned by the concurrent root oracle stream. Re-run
  `--site-list` and `make verify-scattered-oracle` when that stream lands the
  derived artifacts.
- **Fourth conversion 2026-08-05 — Apollo prime-pair macro tables.**
  `repos/apollo/crates/apollo-fft-macros/src/prime_pair_tables.rs` now keeps
  expansion-time cosine/sine values in flat `Vec<f64>` buffers and chunks them
  only while emitting the unchanged fixed-size `[[T; H]; H]` token arrays. This
  removes the nested `Vec<Vec<f64>>` allocation and preserves row-major token
  order and the `PrimePairTable<N, H>` API. Zero-height inputs avoid
  `chunks_exact(0)`; zero `N` and `H × H` overflow return deliberate procedural
  macro compile errors. Evidence: macro/FFT checks, rustfmt, strict Clippy,
  doctests, and `cargo nextest run -p apollo-fft --lib` **394/394** pass;
  targeted diff and nested-vector residue checks are clean. The ARCH-008 oracle
  remains deferred exactly as recorded above because its classifier/oracle files
  are owned untracked artifacts in the concurrent root stream.
- **Site investigated and recorded correct-as-jagged 2026-08-07 — CFDrs
  spectral-element global assembly.** Converted
  `repos/CFDrs/crates/cfd-math/src/high_order/spectral/assembly.rs`
  (`GlobalAssembly.element_dofs` + `SpectralMesh.element_connectivity`,
  oracle sites `assembly.rs:14,25,140`) to CSR-shaped flat offset+index
  storage with the input shape preserved, then measured it. The criterion
  comparison (DOF-traversal read, 2 000×8 / 2 000×32 / 500×128 elements×DOFs)
  showed the flat buffer is consistently **~1.2–1.6× slower** than the jagged
  rows for the isolated read (CSR 3.5/7.2/6.2 µs vs jagged 2.1/6.0/5.5 µs):
  the fixed-size spectral rows are small and cache-resident either way, and
  the flat slice window pays two bounds checks the direct `Vec` row does not.
  The whole-`add_element_matrix` variant was dominated by unbounded COO
  accumulation (bench-design noise), not DOF access. The conversion was
  **reverted** and the site is recorded as correct-as-jagged: no traversal
  hotness, no criterion win — converting it would trade memory for a
  measurable slowdown. No oracle change needed (the sites remain live
  `Vec<Vec<` occurrences, correctly classified as production).
- **Fifth conversion 2026-08-07 — Leto L-BFGS ring buffer.**
  `repos/leto/crates/leto-ops/src/application/optimization/lbfgs.rs`
  `LbfgsMemory` now keeps correction pairs in two CSR-shaped flat ring
  buffers `s_buf`/`y_buf` (capacity `memory * n`) plus a scalar
  `rho_buf` (capacity `memory`) addressed by a single `head` index
  modulo `memory`, replacing the previous `Vec<Vec<f64>>` history
  with `Vec::remove(0)` eviction. The public API
  (`new`/`len`/`is_empty`/`direction`/`push`) is preserved; downstream
  `kwavers-solver` FWI callers (`elastic_fwi/inversion.rs`,
  `time_domain/quasi_newton.rs`) recompile against the new API without
  changes. The two-loop recursion in `direction` was re-derived against
  Nocedal & Wright Alg. 7.5: under the ring's logical-index convention
  (`pair_slot(0)` = newest, `pair_slot(k-1)` = oldest), the first pass
  walks `0..k` (newest→oldest) and the second pass `(0..k).rev()`
  (oldest→newest); a self-authored regression test
  (`direction_preserves_two_loop_after_wrap`) verifies value-semantic
  agreement with an independent jagged-reference implementation after a
  full ring wrap, and a saturation test verifies oldest-pair eviction.
  Criterion baseline comparison over the acceptance-oracle grid
  `{8,32}×{100,1000}` (median [lo hi], µs):

  | config | ring (new) | jagged (baseline) |
  |---|---|---|
  | m8_n100   | 1.71 [1.65 1.79]  | 1.78 [1.71 1.88] |
  | m32_n100  | 6.68 [6.31 7.04]  | 7.48 [7.14 7.79] |
  | m8_n1000  | 15.42 [14.61 16.24] | 16.36 [15.79 16.87] |
  | m32_n1000 | 75.00 [71.45 79.08] | 66.19 [63.35 70.11] |

  The flat ring wins at small dim (≤+13% over jagged, fewer allocations),
  is parity at `m8_n1000` (memory traffic dominates over allocation
  savings), and is **~13% slower** at `m32_n1000`: the large memory plus
  large dim regime has the ring doing `% memory` slot resolution per
  two-loop step against two big contiguous buffers while jagged has
  `memory` individual `Vec` allocations with one prefetcher-tight inner
  scan per row. The conversion's primary win is allocation/eviction
  elimination (no `Vec::remove(0)`, one allocation at construction
  instead of per-`push`), not raw throughput at high `m × n` — that is
  the honest baseline and is recorded here per the performance gate.
  Evidence: `cargo nextest run -p leto-ops --lib` **178/178** (176
  baseline + 2 new regression tests), `cargo test --doc -p leto-ops`
  20/20 + 1 ignored, `cargo clippy -p leto-ops --lib -- -D warnings`
  clean, `cargo fmt -p leto-ops -- --check` clean,
  `cargo check -p kwavers-solver --no-default-features` clean. The
  criterion bench `crates/leto-ops/benches/lbfgs.rs` is registered with
  `harness = false` and smoke-runs in single-iteration mode (`-- --test`)
  within the test budget; full timing runs fit the 300s/binary budget.
- **Delivery**: leto PR #96 (`fix/leto-ops-lbfgs-ring-buffer`), commit
  `1ed166a`, branch pushed to origin. **Not merged — blocked on a leto CI
  infrastructure defect at `db9a63c` (origin/main HEAD)**: Codex's Aug-7
  commit replaced the `git = "..."` workspace declarations for `mnemosyne`/
  `moirai`/`hermes-simd`/`eunomia`/`aequitas`/`themis` with `path =
  "../..."` for local meta-repo convenience, which resolves locally (meta-
  repo `.cargo/config.toml` `[patch]` overlay redirects the URL sources to
  local paths either way) but is unresolvable in leto's standalone CI
  checkout (`cargo metadata` fails to read `../aequitas/Cargo.toml`).
  Pre-existing in main, unrelated to this PR — leto's prior main CI run was
  already red for the same reason. Codex's `LETO-INTO-ITERATOR-1` dirty
  state is present in the leto working tree iterating on `leto/array.rs`,
  `leto/src/application/iter/*`, `leto/src/lib.rs`, `leto/tests/core/
  iteration.rs`, plus unrelated `leto-ops/{lu_symbolic.rs, sparse/mod.rs,
  parallel.rs, lib.rs}` files — the workspace `Cargo.toml` is theirs by
  precedent and outside the file-disjoint scope of this lbfgs slice.
  Per `concurrent_agents: Contention response order`, PR #96 stays open
  with the peer's landing as its re-open trigger. **Re-open trigger**:
  leto CI on main turns green (Codex lands the CI fix forward), OR a
  future disjoint slice puts me in a position where
  `repos/leto/Cargo.toml` workspace section falls under my scope.
- **Out-of-scope finding recorded** (kwavers-math `optimization/lbfgs.rs`
  is a full duplicate `LbfgsMemory` implementation, not the re-export the
  ATLAS-MATH-SSOT-CONSOLIDATION-1 Lane B residual table records; see Lane
  B residual (5)). Not converted in this slice: out of the leto-local
  file-disjoint scope, peer-active territory.
- **Sixth conversion 2026-08-08 — consus-zarr chunk selection indices.**
  `repos/consus` `consus-zarr/src/chunk/ops.rs` `selection_indices`
  (`Vec<Vec<u64>>`, one allocation per selection dimension) is replaced by a
  CSR-shaped `SelectionIndices` (`flat: Vec<u64>` contiguous buffer +
  `offsets: Vec<usize>` offset table) built once per read/write call; both
  copy helpers (`copy_chunk_selection_to_output`, `copy_selection_input_to_chunk`)
  hoist `dims: Vec<&[u64]>` per call so the traversal hot loop does one
  indirection (`dims[dim][selection_position[dim]]`) instead of two, and all
  three call sites (`read_array`, `write_array_selection`, `read_array_sharded`)
  use the same `SelectionIndices::build`. Criterion
  (`crates/consus-zarr/benches/zarr_selection_copy.rs`, `harness = false`,
  faithful jagged replica of the non-sharded `read_array` kept inline as a
  baseline; byte-parity assertion pins the replica to production output
  before timing; 2d 256×256 / 2d 512×512 / 3d 64³ strided×2 selections on a
  populated `InMemoryStore`): CSR is a win on every case — **−4.7% /
  −6.5% / −10.9% time vs jagged** (criterion `change`, p < 0.05; within-run
  medians 6.50/25.75/33.8 ms vs 6.96/26.40/36.6 ms). Gate: `cargo clippy -p
  consus-zarr --all-features --all-targets -- -D warnings` clean, nextest
  `303/303`, doctests clean, fmt clean; CI `--all-features` clippy+check
  green on PR #13. **Oracle refreshed to 243 production / 80 test-bench /
  323 total**: the consus-zarr `ops.rs` production site is gone; coeus
  `ctc.rs` 408-410 → 353-355 (line shift from a peer PR, same sites); leto
  `lbfgs.rs:79,80` added (genuine `Vec<Vec<f64>>` in `LbfgsMemory`,
  hand-verified; the conversion's ring buffers are flat so the site moved,
  it did not stay). `--verify-oracle` exit 0 on the refreshed oracle.
  Delivery: consus PR #13, branch `refactor/consus-zarr-csr-selection-indices`
  (commits `3ce79b0` conversion + `d3d5b19` mechanical rustfmt of two
  pre-existing-dirty consus-core book examples that had kept the
  workspace-wide Format CI job red at HEAD, blocking the Check job for every
  PR). Residual: pre-existing untracked meta-repo scratch (`.commandcode/`,
  `libtest_*.rlib`) and peer-held `version-guard`/`gitlink-coherence` changes
  are untouched.

## ATLAS-PRIVACY-NAMING-1 — Private consumer named throughout stack artifacts [chore] — todo (needs user decision)

- Owner: unclaimed; scope: `backlog.md`, `gap_audit.md`,
  `docs/adr/0036-neuroimaging-and-mr-ownership.md`, and
  `PATH_DEP_AUDIT_001_ENTRY.md`.
- The consumer at `repos/leoneuro-rs/` is a private external org's code drop:
  gitignored at `.gitignore:60`, no `.gitmodules` entry, no
  `submodule.*` keys, remote on a different GitHub org. ATLAS-GIT-HYGIENE-001
  confirmed that arrangement is deliberate design, not a stale rule.
- Standing policy for such a consumer is that it stays out of the stack map
  entirely — the gitignore entry is the only sanctioned trace, and upstream
  items it motivates cite "a downstream consumer" generically. Its name is
  currently in four tracked artifacts, including an ADR and the closed
  audit ledger, across roughly a dozen references.
- I redacted only the one reference I added myself (in
  ATLAS-OVERLAY-GEN-STALE-1's measurement). The rest is **not** being swept
  unilaterally: several sit in closed items' audit trails and an Accepted ADR,
  where a blind rename would break the traceability those records exist to
  provide, and peers reference those item names.
- The decision needed: does this consumer's name count as confidential for
  artifact purposes? If yes, the sweep should be one deliberate pass that
  rewrites references generically and preserves each record's meaning
  (git history keeps the old text either way — the redaction is forward-only).
  If no, the standing rule should be recorded as not applying here, so this
  keeps being re-raised.
- Adjacent, unrelated to the naming question: `PATH_DEP_AUDIT_001_ENTRY.md` sits
  at the repository root, where the root-manifest rule admits no loose report
  files. Its content belongs in the closed item it serves.

## ATLAS-PUB-001 — Migrate 8 crate-release workflows to the Atlas-shared caller [patch] — blocked: fresh Kwavers current-default validation

- Owner: current session (Atlas coordination); scope: root publication records and
  exact default-branch evidence for
  `repos/{apollo,coeus,consus,hephaestus,kwavers,leto,moirai,ritk}/.github/workflows/rust-release.yml`.
  The separate `repos/ritk/.github/workflows/release.yml` is the wheel publisher,
  not the crate caller. One package per claim — the
  scopes are disjoint by repository.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §1-§3.
- Outcome: each package's crate-release workflow becomes a thin caller of
  `ryancinsight/atlas/.github/workflows/crates-publish.yml@<atlas-sha>`, and the
  duplicated 142-line body is deleted in the same change. Audit 2026-07-28: four
  of the seven `rust-release.yml` files are byte-identical; the only real
  variation is `RUST_TOOLCHAIN` (1.95.0 / 1.97.0 / 1.97.1) and whether the
  package needs Atlas path dependencies (only `kwavers`).
- Non-goals: changing any package's toolchain pin; changing tag conventions;
  touching the already-shared wheel pipeline.
- Acceptance per package: caller under 40 lines; the package's existing toolchain
  value passed as `rust-toolchain`; `kwavers` passes `atlas-ref`; the old body
  deleted, not kept beside the caller; one `workflow_dispatch` validation run
  green before the next release.
- Dependencies: none. ATLAS-PUB-003 must be complete for that package before its
  next real publish, but the migration itself does not wait on it.
- **hephaestus slice done 2026-08-03** (`38f36bc`): 142-line body → 39-line
  caller pinned to atlas `9772542`, toolchain 1.95.0 preserved, `crate-` tag
  convention unchanged. Acceptance met including the validation run —
  `workflow_dispatch` run 30795798452 is green, with the validate job passing
  in 1m3s and the publish job correctly skipped (it gates on
  `github.event_name == 'release'`, so a dispatch cannot publish).
- **leto and moirai slices done (prior session)**: both migrated to 39-line callers.
- **apollo, coeus, consus, ritk PRs open 2026-08-04**: apollo PR #75, coeus PR #289, consus PR #11, ritk PR #107 — 142-line bodies → 39-line callers, format/lock fixes applied, CIs running.
- **Carry this into the remaining seven migrations: the tag gate must stay in
  the caller.** The audit's "byte-identical apart from the toolchain" reading
  misses it. Each package's current workflow skips non-`crate-` releases via a
  job-level `if`, but the shared workflow's validate job has **no** prefix
  check and `exit 1`s on a tag it cannot parse. Porting without the gate
  converts today's silent skip of a legacy `<package>-v<version>` release into
  a red CI run.
- Evidence that this is live, not theoretical: hephaestus's two most recent
  release events (`hephaestus-metal-v0.18.0`, `hephaestus-host-v0.18.0`, both
  2026-08-02) show `skipped` in the run list. Legacy-convention tags are still
  being cut, so the gate is doing real work today.
- Tag-convention state, surveyed 2026-08-03 across all eight packages: every
  one gates on `crate-`, and there is exactly **one** matching tag in the whole
  stack — apollo's `crate-apollo-fft-macros-v0.2.0`, cut 2026-08-02. So
  `crate-` is the newly adopted convention rather than a dead gate, and the
  default `tag-prefix` is correct for these callers. Worth stating explicitly
  because the raw numbers (1 matching tag out of 77) read like dead automation
  until the dates are checked.
- Separate observation, not part of this item: because those 0.18.0 release
  events skipped, they were not published by this pipeline. Whether the crates
  reached crates.io by another route is a question for ATLAS-PUB-003, which
  owns publisher registration.
- **leto slice done 2026-08-03** (`c42b87d`), plus `bf7bf2b` fixing four unused
  imports that the earlier `520f248` decomposition left behind — CI denies
  warnings, so that would have failed the gate regardless of this item.
- **moirai slice done 2026-08-03** (`08d5095`): identical caller with its own
  toolchain (1.97.0) passed through; the repo's workflow differed from the
  others only in that value. Validation run 30811438728 green, and its
  `--locked` step passing independently confirms moirai's lock is sound.
  Repository CI also green, covering the three refactor commits the push
  carried.
- **3 of 8 done** (hephaestus, leto, moirai). The five left — apollo, coeus,
  consus, kwavers, ritk — are all currently on live peer branches, so their
  slices wait for those branches rather than for anything in this item.
- **Default-branch recheck 2026-08-13.** All eight fetched crate defaults now
  carry the 39-line Atlas caller with no local `cargo publish` body: Apollo,
  Coeus, Consus, Hephaestus (`origin/master`), Kwavers, Leto, Moirai, and RITK.
  The source migration is therefore complete; the old `3 of 8` count is
  historical.
- Hosted validation evidence is mixed and remains open for the release gate:
  Apollo release validation `31534217702`, Coeus release validation
  `31551729552`, Hephaestus release validation `31532975062`, Leto release
  validation `31531560175`, Moirai release validation `31530550433`, and RITK
  release validation `31654707025` pass. Consus dispatch validation
  `29976636343` passes on its recorded head. Kwavers dispatch validations
  `31316302910` and `31290138802` fail at the pre-repair lock state; no fresh
  validation exists yet for the current default after the git-source lock
  repair. Coeus publish-stage failure is the external registry gate owned by
  ATLAS-PUB-003, not a caller-validation failure.
- Re-open trigger: fresh Kwavers `workflow_dispatch` validation run
  `31717782458` completes successfully at current default `7fee848d`.
- Practical note for the remaining slices: pass `version` from the workspace
  table, not a grep of the member manifest. Members use
  `version.workspace = true`, so a naive extraction sends the literal string
  (or an empty value) to `workflow_dispatch` and the run fails on a version
  mismatch that looks like a pipeline defect but is just a bad argument. It
  cost a wasted run on both leto and moirai.
- **The validation run then exposed a blocking, stack-wide publish defect.**
  See ATLAS-PUB-LOCK-1 below. The leto migration itself is behavior-preserving
  and correct — the old and shared workflows use byte-identical `--locked`
  invocations, so this failure predates the migration and would have hit the
  first real release either way. The migration is what made it visible.

## ATLAS-PUB-002 — Migrate 4 book workflows to the Atlas-shared caller and close the docs.yml gap [patch] — in-progress

- Owner: current session (Atlas coordination); scope: reusable-workflow
  evidence and the CFDrs caller's backend input. Other provider caller files
  and peer-owned working-tree changes are excluded.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §1-§3, §5.
- Outcome: each book workflow becomes a caller of
  `ryancinsight/atlas/.github/workflows/book-pages.yml@<atlas-sha>` passing only
  `output-path`.
- **Closed sub-item (2026-07-28):** `ritk` now joins the Atlas cross-book gate —
  `.github/workflows/docs.yml` runs the strict detector and an `mdbook build`
  over all four books. The same change dropped the three per-book HTML artefact
  uploads, leaving `detector.log` as the only retained artefact; that is a
  deliberate narrowing, not a regression, since Pages deployment is the book's
  delivery path and the artefacts were diagnostic only.
- Non-goals: flipping `mdbook-test` (ATLAS-PUB-005); authoring new books
  (ATLAS-BOOK-001).
- Acceptance: four callers, each passing its audited output path
  (`target/book/cfdrs`, `target/book/helios`, `target/book`,
  `target/book/ritk`); each package's Pages deployment succeeds once through the
  shared workflow.
- **Hosted residual 2026-08-13, closed:** CFDrs run `31716368183` failed during
  the shared build because `book.toml` declares a non-optional
  `[output.linkcheck2]` renderer and the pinned Atlas workflow `d875348` did
  not install it. Root commits `042e448` and `4c31dd7` added the opt-in
  installer and pinned the stable Rust toolchain before `cargo install`. CFDrs
  PRs #339/#340 merged the full root pin, `mdbook-linkcheck2-version: 0.12.2`,
  and `target/book/cfdrs/html`; obsolete PR #338 was closed after verification.
- Helios `31716457700` and Kwavers `31716399219` now have successful Deploy
  mdBook conclusions at their recorded provider heads. RITK `31716974169`
  remains queued at the historical head `f98a9191`, so RITK still requires a
  current-pin run after its caller PR merges. The four current caller PRs must
  still merge and produce fresh deployment evidence before this item closes.

## ATLAS-PUB-003 — Register trusted publishers and remove the unused PyPI token [chore] — todo

- Owner: user-gated — registry and GitHub settings changes are Ask-User actions;
  an agent prepares the values and verifies the result, it does not perform the
  registration.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §4.
- Outcome: every publishing package has a trusted publisher registered on the
  target registry, so no long-lived registry credential exists anywhere in the
  stack. Values per package: owner `ryancinsight`; repository = the package
  repository; workflow filename = the **caller's** filename
  (`rust-release.yml` / `python-release.yml`), because the OIDC claim carries the
  caller's identity, not the Atlas reusable workflow's; environment `crates-io` /
  `pypi`.
- Registry verification 2026-07-28: crates.io **cannot bootstrap** a new crate
  through trusted publishing — the crate must already exist and the first publish
  requires an API token. The account `ryancinsight` (id 383645) has published one
  crate, `imaginary-rs@0.1.0`; no Atlas crate is published. PyPI **can** bootstrap
  through a pending publisher configured under the account sidebar.
- Sequence per crate, therefore: (1) resolve its registry name (ATLAS-PUB-006 for
  the twelve collisions); (2) one manual publish from the local Cargo credential
  store, in workspace dependency order; (3) register the trusted publisher;
  (4) enable trusted-publishing-only enforcement. PyPI distributions skip step 2.
- Acceptance: one trusted-publishing release succeeds per package; the API token
  in the `pypi` environment is deleted afterwards; trusted-publishing-only
  enforcement is enabled in each registry's settings once its pipeline is proven.
- Residual risk: an unregistered package fails closed at the auth step. That is
  the intended failure mode, not a regression. A pending PyPI publisher does not
  reserve the project name until first use, so a name can be lost in between.

## ATLAS-PUB-006 — Stand up one facade crate per package [minor] — todo

- Owner: unclaimed; scope: one package per claim, in that package's repository.
  The `mnemosyne-core` rename is a cross-repo co-evolution unit and is claimed as
  a single item spanning `mnemosyne`, `leto`, `hephaestus`, and `moirai`.
- Decision: [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md).
  Naming is settled; nothing here waits on a user answer.
- Outcome: every package presents one facade crate that re-exports its
  sub-crates, so a user depends on `coeus`, not `coeus-core` — the shape `burn`,
  `bevy`, and `polars` use. The facade holds no logic: re-exports with
  `#[doc(inline)]`, feature gates selecting optional backend sub-crates, and the
  crate-level overview. Lockstep versioning at the workspace version.
- Audit 2026-07-28 — 14 of 25 packages cannot present a facade today:
  - **author a facade** (workspace root is virtual, no entry crate exists):
    `apollo` → `apollo-transforms`, `CFDrs` → `cfdrs`, `coeus` → `coeus`,
    `helios` → `helios-radiation`, ~~`hephaestus` → `hephaestus`~~ **delivered**,
    `ritk` → `ritk`;
  - `hephaestus` facade landed in `repos/hephaestus/crates/hephaestus`
    (`bf24b87`): flat `#[doc(inline)]` re-export of the contract layer, backends
    under `hephaestus::{wgpu,cuda,rocm,metal}` behind features, no backend
    enabled by default (a default backend would make every trait consumer pull a
    device stack, and `cuda`/`rocm` need vendor toolkits at build time). Two
    design facts worth carrying to the remaining five:
    `default-features = false` cannot override a workspace-inherited dependency,
    so a facade declares its contract-layer dep directly; and weak feature refs
    (`dep?/feature`) are required so forwarding `parallel` does not silently
    enable an unrequested backend.
  - Verification complete — all four configurations pass: default `cargo check`,
    `--no-default-features`, the doctest, and `--features wgpu,decomposition,sparse`
    (11 m 32 s, queued behind a peer's build-directory lock). The `bf24b87`
    commit message recorded the wgpu set as unconfirmed because it was still
    building at commit time; this entry supersedes that.
  - Evidence limit: those checks ran against a working tree carrying a peer's
    uncommitted edits to `hephaestus-core/src/{lib.rs,domain/vector.rs}` and
    `hephaestus-wgpu/src/application/vector/mod.rs`. They prove the facade
    compiles against the tree as it stood, not against committed state. The glob
    re-export is robust to surface additions, but re-verify on a clean tree once
    that peer work lands.
  - Not verified: that a backend is unnameable without its feature. That follows
    directly from `#[cfg(feature = ...)]` on the re-export, and a `compile_fail`
    doctest asserting it would itself pass or fail depending on which features
    the test run enables — a fragile test of language semantics rather than of
    this contract, so none was added.
  - **flip `publish`** (facade exists, excluded from publishing): `aequitas`,
    `asclepius`, `horae`, `hermes-simd` — names already free;
  - **rename and flip `publish`**: `harmonia` → `harmonia-coupling`,
    `hyperion` → `hyperion-photon`, `moirai` → `moirai-runtime`,
    `proteus` → `proteus-materials`;
  - **rename only** (publishable under a colliding name): `athena` →
    `athena-solvers`, `gaia` → `gaia-geometry`, `mnemosyne` →
    `mnemosyne-alloc`, `themis` → `themis-placement`, `tyche` → `tyche-uq`;
  - **ready, no action**: `consus`, `eunomia`, `iris`, `kwavers`, `leto`,
    `melinoe`.
- Non-goals: repository names, submodule paths, directory names, module paths,
  and the classical-name mapping in the stack README. This is registry identity
  only. Also out of scope: negotiating a colliding name from its current owner —
  permitted, but no publish waits on it (ADR 0037 §7).
- Acceptance per package: the facade's `src/lib.rs` contains no logic; `cargo doc`
  shows re-exported items inline at facade paths; `--no-default-features` builds
  and no backend is reachable without its feature; `cargo publish --dry-run`
  passes after the sub-crates; the facade name returns 404 from the registry
  immediately before first publish, since availability decays.
- Non-blocking: ATLAS-PUB-001, -002, -004, and -005 proceed independently — a
  caller passes a package name, so every rename here is a manifest change.
- **Correction 2026-07-28 — do not flip `publish = false` ahead of dependencies.**
  An earlier reading of this item treated the eight guards as oversights. They are
  correct ordering guards: `cargo package` on `aequitas` fails with
  `no matching package named 'eunomia' found`, because a crate can only publish
  once its first-party dependencies are on the registry. Cargo *does* rewrite a
  `{ version, git }` dependency to a registry dependency, so git sources are not
  the blocker (`hermes-simd`'s manifest comment overstates it) — dependency order
  is. Each flip is the final step of that crate's own bootstrap publish, in the
  order `scripts/publish-order.py` derives. Four flips were attempted and reverted
  on this evidence; see [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md) §4.
- **Registry re-measure 2026-08-24 — README is stale, and the naming diverged from
  ADR 0037 in four places.** A live crates.io check plus the committed manifests
  correct the record:
  - **Already published (user's crates):** `aequitas` 0.2.0, `eunomia` 0.8.0,
    `asclepius` 0.1.0, `leto`+`leto-ops` 0.42.0, `melinoe` 0.9.0, `apollo-fft`
    0.26.0, `apollo-fft-macros` 0.2.0, `moirai-core`+`runtime` 0.5.0,
    `coeus-core`+`tensor`+`ops` 0.10.0, `mnemosyne-core` 0.2.0, `mnemosyne-heap`
    0.4.0, `themis` 0.14.0, `tyche-core` 0.2.0, `gaia-mesh` 0.4.0, `hermes-simd`
    0.6.0, `hephaestus-core`+`host`+`wgpu` 0.19.0, `ritk-core` 0.10.0,
    `ritk-image` 0.3.0, `consus` 0.1.0. The README line "No Atlas crate is
    published yet" (line 1084) is false and must be corrected.
  - **Naming deviations from ADR 0037, found in the manifests (not the README):**
    - athena's facade is `athena-krylov` (`[lib] name = "athena"`, `publish =
      true`), not `athena-solvers` as the README table lists.
    - iris's package is `iris-viz`, not `iris`; gaia's is `gaia-mesh` (already
      published 0.4.0), not `gaia-geometry`.
    - themis's package is `themis-topology` (`[lib] name = "themis"`, publishable),
      not `themis-placement`; `leto` publishes under the bare name 0.42.0.
    - tyche root is `publish = false`; mnemosyne root publish is unset.
  - **Third-party name collisions confirmed:** `hyperion` (patrickisgreige
    LSystem), `proteus` (rust-playground JSON), `harmonia` (sogh music theory),
    `gaia` (ucarion terrain), `mnemosyne-core` (bballer03 JVM analyzer), `athena`
    (unrelated). All five unblocker repos (hyperion, proteus, harmonia, horae,
    asclepius) are clean at their recorded gitlinks and `publish = false`.
  - **The unblocker chain is the critical path:** proteus → `proteus-materials`,
    hyperion → `hyperion-photon` (repoint its `proteus` dep), horae (name free),
    harmonia → `harmonia-coupling` (repoint `horae`+`athena-core` deps), then
    asclepius-coeus; athena's family must publish before harmonia.
  - **Delivery 2026-08-25 — first link merged across the stack; publish itself
    still pending.** All five PRs merged to their default branches:
    proteus #19 (`cd93e67`, later main `cb00193`), CFDrs #371 (`5ebbf1f`),
    hyperion #25 (`017a669`), kwavers #637 (`f5a996c` → main `cf5852f`),
    helios #71 (`c2cf177`). Atlas gitlinks advanced in `5c9efcac8` (+ hermes
    `4a1228ce`); overlay regenerated (44 sections, stack aligned);
    `atlas-provider-integration-audit.py --exact-heads` green.
  - **Lockfile lesson (kwavers/helios):** a committed lockfile must be generated
    *without* the Atlas overlay — the overlay's `[patch]` redirects strip the
    git `source =` lines from lock entries and inject `[[patch.unused]]`
    sections, both of which break CI's `--locked` resolution. Helios now enforces
    this at push time via its pre-push hook (`scripts/lockfile.py --regenerate`).
    Remaining: the actual `cargo publish` of `proteus-mat` (release authority),
    then the next links: hyperion → `hyperion-ph`, horae, harmonia →
    `harmonia-cpl`.
- Peer-held at this revision, so not claimable without a staleness sweep:
  `coeus` (`codex/coeus-error-function-parity`, 24 dirty), `ritk`
  (`codex/docs-ritk-n4-figure-only`, 11 dirty, active), `leto`
  (`codex/leto-real-sparse-lu`, 25 dirty), `mnemosyne`
  (`codex/mnemosyne-tier-selection`, clean). The `coeus` facade — the flagship
  case for this item — is among them.

## ATLAS-PUB-008 — Audit facade names immediately before each first publish [chore] — todo

- Owner: unclaimed; scope: the pre-publish check only.
- Decision: [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md) §3,
  verification item 1.
- Outcome: name availability is a point-in-time observation and decays — 165 of
  173 names were free on 2026-07-28, and first-come means any of them can be
  claimed by a third party before the stack publishes. Each first publish
  re-checks its own name.
- Acceptance: `GET /api/v1/crates/<name>` returns 404 immediately before the
  publish, recorded in the release evidence. A collision discovered here is
  resolved by ADR 0037 §3's rule, not by an ad-hoc name.

## ATLAS-PUB-005 — Flip `mdbook-test` per book as samples become compilable [patch] — in progress

- Owner: current Atlas session; active claim: Iris; scope: one book per claim,
  in the owning repository.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §6.
- Outcome: every published book runs `mdbook test` in CI so chapters cannot rot.
  The shared workflow defaults `mdbook-test` to `false` as a staging mechanism,
  not an accepted end state. The committed provider defaults currently have
  seventeen shared callers plus Gaia's direct command gate; the six named
  residual callers remain untested until their samples compile.
- Claim status (updated 2026-08-20):
  - **melinoe** — DONE: all fenced samples compilable; blocks referencing the
    crate carry `extern crate melinoe;` and link through a staged plain-named
    rlib (`mdbook test --library-path`), signature illustrations `ignore`d, the
    cross-brand rejection sample `compile_fail`; caller passes `mdbook-test:
    true` + `cargo-package: melinoe`; the shared workflow's broken
    `RUSTDOCFLAGS` mechanism replaced with the staging + `--library-path` path.
    Merged via melinoe PR #11; main CI green (all 11 chapters tested), Pages
    deploy green; workflow fix on atlas main (`70c6c6b`, PR #100) makes the
    caller's full-SHA pin durable.
  - **eunomia** — DONE: caller passes `mdbook-test: true` and its hosted book
    gate is part of the provider's merged workflow.
  - **helios** — OPEN: H-103. The current book contains illustrative Rust
    fragments that fail direct `mdbook test docs/book` because they omit setup,
    use unresolved provider imports, or fence diagrams/commands as Rust. H-102
    repaired source-change triggers and enabled linkcheck2; H-103 must convert
    the snippets before the caller can pass `mdbook-test: true`.
  - **iris** — LANDED at provider `9672fc0`: the Pages caller pins the shared
    workflow fix `1fcd17c` and enables `mdbook-test: true`, Rust `1.97.0`, and
    `cargo-package: iris-viz`; the
    included example declares `extern crate iris`, and the stack-position
    topology diagram is fenced as `text`. Local format, locked all-target
    check, Clippy, nextest (`17/17`), doctests (`3/3`), package verification,
    `mdbook build`, and `mdbook test` pass. Push-triggered hosted runs are
    `32332860859` (CI), `32332861158` (Deploy mdBook), and `32332859993`
    (Pages build/deployment) remain queued at the time of recording. The prior
    run at `8224dba` exposed the package/library-name mismatch and was replaced
    by this explicit-crate revision. Peer-owned Iris lockfile work remains
    untouched.
- Acceptance per book: samples compile against the package; the caller passes
  `mdbook-test: true` and, where samples need providers, `atlas-ref`; the flip
  commit demonstrates the gate failing on a deliberately broken sample before
  landing green.
- Dependencies: ATLAS-PUB-002 for that package.

## ATLAS-MODALITY-003 — Optical-transport and RF/EM promotion watchpoint [arch] — blocked

- Owner: unclaimed; scope: watchpoint only — no edits until the trigger fires.
- Decision: [ADR 0032](docs/adr/0032-modality-transport-and-therapy-boundaries.md) §1, §2, §6.
- Blocker: promotion gate conditions 1, 4, and 6 are unmet. Source audit
  2026-07-27: Kwavers is the sole consumer of the diffusion/Monte-Carlo-RTE
  optical transport solvers (CFDrs has no radiative/optical/photon module;
  ritk has none; Helios consumes Hyperion at MeV, a different regime). No RF
  integrator or second electromagnetics consumer exists.
- Re-open trigger: a second production consumer can delete a matching transport
  implementation in the extraction change. At that point the target is
  `hyperion-transport` as a second crate in a promoted Hyperion workspace — not
  a new package — so the `no_std` law crate keeps its dependency set and Helios
  and CFDrs inherit no array substrate.
- Standing note: sonoluminescence (3 006 LOC) and photoacoustics (653 LOC) are
  Kwavers-intrinsic and are excluded from any extraction scope. A photomedicine
  integrator peer to Helios is a separate, demand-gated decision and is out of
  scope here.
- Refinement 2026-07-28 —
  [ADR 0036](docs/adr/0036-neuroimaging-and-mr-ownership.md) §5: "RF" names two
  unrelated concerns and this watchpoint covers only the first. RF power
  deposition and SAR belong on the shared deposition spine (ATLAS-MODALITY-002),
  where the transport stage is a modality slot and the stages behind it are
  shared. RF at the Larmor frequency for spatial encoding belongs to MR
  acquisition simulation, which is a closed, demand-gated *integrator* question —
  not part of this trigger and not a RITK concern. A proposal that merges the two
  is rejected on bounded-context grounds before the gate is even applied.

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

## ATLAS-OVERLAY-004 — Worktree sprawl breaks stack dependency resolution [patch] — in-progress

- Owner: unclaimed; scope: `worktrees/`, the root `.cargo/config.toml`, and the
  13 lane-local `.cargo/config.toml` files. **Not** the lane branches' source.
- Blocker evidence (2026-07-27): `cargo check -p kwavers-physics` fails before
  compiling anything:
  - `failed to select a version for smallvec` — `hephaestus-wgpu v0.18.0` at
    `worktrees/hephaestus-unary-math-parity` requires `^1.15.2`; the kwavers lock
    pins `1.15.1`.
  - `cargo update -p smallvec --precise 1.15.2` then fails harder:
    `package collision in the lockfile: packages aequitas v0.1.0
    (D:tlas\worktreesequitas) and aequitas v0.1.0
    (D:tlas\worktreesequitas-energy-temperature) are different, but only
    one can be written to lockfile unambiguously`.
- Two distinct defects behind it:
  1. ✅ **resolved 2026-07-28** — `worktrees/aequitas` was an **orphaned linked
     worktree**, not a standalone clone: its `.git` file pointed at
     `repos/aequitas/.git/worktrees/aequitas`, whose admin directory had been
     pruned, leaving the checkout on disk with no git registration. Cargo still
     discovered it as a path source, giving two providers for `aequitas v0.1.0`.
     Contents were byte-identical to `repos/aequitas` (`diff -r` clean excluding
     `target`, `Cargo.lock`, `.git`), so nothing unique was lost. Removed with
     user authorization; `git worktree prune` run. `cargo check` across
     kwavers-physics and kwavers-solver resolves again, and the `smallvec`
     conflict cleared with it.
  2. **13 lane-local `.cargo/config.toml` files.** Config-layer ownership
     (`performance_engineering`) puts `target-dir` and the `[patch]` overlay at
     the stack root only; a nested config re-declaring either forks resolution
     and, as here, resolves a relative provider path into a second copy.
- Also: `worktrees/` holds 28 entries against a documented bound of one main
  tree plus one lane per repository. aequitas, coeus, hephaestus, kwavers, and
  ritk each have two or more.
- Acceptance: `cargo check -p kwavers-physics` resolves; `git worktree list` per
  repo is within bound; no lane-local `.cargo/config.toml` re-declares
  `target-dir` or `[patch]`; `worktrees/aequitas` removed after confirming no
  unique commits.
- **Ask-User gate**: removing `worktrees/aequitas` and other agents' lane
  directories is destructive to possibly-live peer setups. Confirm before
  deleting rather than reconciling unilaterally.

## ATLAS-DOWNSTREAM-COORDINATION-001 — Notify LeoNeuro-INC maintainers about local leoneuro-rs `50bfcd9` [chore] — todo

- Owner: unclaimed; scope: out-of-band coordination with the
  LeoNeuro-INC organization (separate GitHub org, NOT ryancinsight).
  No atlas-side edits in this scope.
- Outcome: the leoneuro-rs `50bfcd9` commit ("build(leoneuro-rs):
  Apply round-6a atlas-root path resolution — GRAND_TOTAL 0 across
  atlas") lives locally at `/d/atlas/repos/leoneuro-rs/` on the
  branch `codex/sim-ct-medium`. After atlas's closure cycle dropped
  the bogus 160000 gitlink in commit `d6827c2`, atlas parent no
  longer tracks leoneuro-rs's HEAD; the LeoNeuro-INC maintainers
  can land `50bfcd9` to their own org
  (`https://github.com/LeoNeuro-INC/leoneuro-rs.git`) on their own
  schedule via their own CI/dispatch pipeline.
- Acceptance: a downstream LeoNeuro-INC maintainer receives a short
  note pointing at the local SHA (`50bfcd9`) and the atlas-side
  commit history (see `D:/atlas/PATH_DEP_AUDIT_001_ENTRY.md` STEP D
  push-handoff paragraph for the handoff context); the
  LeoNeuro-INC team decides whether to fast-forward their `main`
  to `50bfcd9` or to cherry-pick from the local branch.
- Method: out-of-band contact through the existing LeoNeuro-INC
  internal channels; the atlas-side convey is a one-line pointer
  (no technical payload required). The atlas-side documentation
  states this deferral, but **no atlas code or Cargo.toml changes**
  are part of this ticket. The `50bfcd9` commit is preserved on the
  leoneuro-rs local branch (`codex/sim-ct-medium`) until the
  LeoNeuro-INC team decides its disposition.
- Cross-link: ATLAS-PATH-DEP-AUDIT-2 (cycle closed 2026-07-27)
  STEP D push-handoff paragraph codifies the deferral as
  documentation; this ticket is the corresponding **owner-assigned**
  follow-up so the deferral doesn't drift unowned. NAME SEMANTIC
  NOTE: "downstream" in this title refers to LeoNeuro-INC as
  downstream maintainer of the `50bfcd9` commit; this is distinct
  from atlas-side "downstream consumer" terminology used in
  per-submodule commit hygiene tickets.
- Risk/change class: `[chore]`; out-of-band coordination only.

## ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER — End-to-end CI verification of `prebook check-figures` [minor] — in-progress

- Owner: Codex `/root`; last-update: 2026-07-24;
  scope: re-flag from `done` to `in-progress` after empirical
  drift-fixture probe retry (throwaway PR `ryancinsight/CFDrs#319`
  on commit `a163ef55`, ci.yml run `30109405652` / job `89534706116`)
  revealed a NEW upstream cargo-side blocker distinct from the
  COEQ one the prior turn's predicate anticipated.

- Owner: Codex `/root`; last-update: 2026-07-24;
  scope: `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md`
  + new `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`
  + PR #31 (HELIOS) management.

- Outcome: PARTIAL e2e CI verification of the wired `prebook check-figures`
  SSOT drift lint. The local lint (SSOT_IN_SYNC 7/7 green + drift detection
  at L101) + YAML validation + action pin alignment + clippy `-D warnings`
  clean + `mdbook build` exit 0 are proven signals documented in
  `ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md`. **PR #31 (HELIOS closeout →
  main at run ID `30059559064`) was the actual e2e attempt**: the
  `Check book figures` step fired in the GitHub Actions runner, but
  PR #31 produced 5 failed/concluded-with-error jobs and the conditional
  auto-merge (`gh pr merge --squash --delete-branch`) correctly
  short-circuited (FAIL_COUNT=5 ≠ 0). The full verbatim failure
  diagnostic + root-cause ranking + fix-up recovery plan is captured in
  `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`.

- Failure inventory (PR #31, run `30059559064`):
  - `rust workspace` job failure: `cargo fmt -- --check` saw **6 `Diff in`
    blocks across 3 new files** in the closeout xtask crate —
    `xtask/src/check_figures.rs` (lines 47, 97, 131 — chain-method
    re-formatting), `xtask/src/main.rs` (line 40 — three match arms
    `LegacyMigrationAudit`, `RefreshLegacyAllowlist`,
    `BurnMigrationAudit` consolidated to expression bodies), and `xtask/src/prebook.rs` (lines 139, 154
    — chain-method re-formatting on `fs::read` and `serde_json::to_string`).
    All 6 diffs are chain-method consolidation; trivially fixable via
    `cargo fmt -p xtask && git commit --amend`.
  - `python bindings` and `benchmark regression check` job failures:
    BOTH caused by the same root cause — `--locked` flag (maturin for
    `python bindings`, `cargo bench --no-run` for benchmark regression)
    conflicts with `Updating git repository tyche / eunomia / apollo`
    run by Cargo's metadata step. Fix: drop `--locked` for these two
    CI invocations (intent is preserved via existing `atlas_ref` pin
    in ci.yml); alternative — commit a regenerated `Cargo.lock` that
    captures the submodules' new SHAs.
  - `recurseml/analysis` job error: external research bot, not part of
    GitHub-hosted CI (out-of-scope noise). Confirmed no GitHub-hosted
    job matched the name in
    `gh api repos/ryancinsight/helios/actions/runs/30059559064/jobs`.
  - `deploy` job skipped: intentional (path-filtered `book-pages.yml`).
  - **False positive from prior summary**: `Install Rust verification
    tools` step actually succeeded; the prior summary's "error marker"
    was the `printf '::error::install-action:'` line inside
    `taiki-e/install-action`'s bash `bail()` function declaration.
    Confirmed verbatim in §3.4 of the run-evidence file.

- Main HEAD baseline (independent verification): `888015e0e2a4b03b8c1e25c7a8befcdc098fd98b`
  was independently verified GREEN (3 latest CI runs all `success`).
  → All 4 substantive failures are PR #31-specific, NOT pre-existing on
  `main`. The closeout commits are causal.

- Acceptance: the `Check book figures` step fired in the runner; the
  explicit `SSOT_IN_SYNC: N/N` log line is captured in the run log at
  the relevant step output for verification. Auto-merge correctly
  short-circuited (fail-closed design verified). The full e2e gate
  validation (`DRIFT_DOCS_NOT_IN_SPECS: N` log capture on a
  deliberate drift fixture) remains deferred until the fix-up PR lands.

- Risk/change class: `[minor]`; deferred evidence-only, no production-code
  change on this turn. The fix-up iteration is a separate `[patch]`
  workflow tweak (CI config) + trivial `cargo fmt` commit.

- Dependencies: depends on the `codex/helios-book-figures-closeout`
  branch (currently SHA `e66a16afcd78cf6e63dcbb01c36438e2cc804e8b` on
  `ryancinsight/helios` origin) receiving a fix-up commit addressing
  the 3 substantive failures above, then a follow-up PR (likely #32
  or higher) re-running the CI to validate green-pass. Verifiable now
  via `git ls-remote origin codex/helios-book-figures-closeout`.

- Sub-task (open): `cargo fmt -p xtask` + amend the closeout commits
  on the branch, then drop `--locked` flags from `Build Python
  extension` (maturin) and `Compile benchmark binaries` (cargo bench
  --no-run) invocations in `repos/helios/.github/workflows/ci.yml`.
  Re-push the branch; open a follow-up PR; expect PR CI to flow
  through `Check book figures` with the SSOT_IN_SYNC log line captured.

- Evidence limit: VERBATIM run-30059559064 log excerpts at
  `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`
  (sections 3.1–3.4). The `DRIFT_DOCS_NOT_IN_SPECS` log-line capture
  remains deferred to the follow-up PR's CI run. No release argument,
  no performance argument, no production-code delta.

## ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1 — Close CFDrs runner-side mdBook index + ci.yml silent-drop [patch] — in-progress

- Owner: Codex `/root`; last-update: 2026-07-26;
  scope: `repos/CFDrs/.github/workflows/ci.yml` + `repos/CFDrs/.github/workflows/book-pages.yml`
  + `repos/CFDrs/docs/book/SUMMARY.md` (Appendix F cross-reference); the
  parent atlas `D:/atlas/parity_artefacts/INDEX.md` is the canonical
  sibling artifact cf. `ATLAS-PARITY-HTML-RETIRE-1`.
- Context: throwaway drift-fixture probe PR #320 (run `30217224003`)
  revealed TWO runner-side defects on the post-SIBLING-CHECKOUT-1 +
  post-COEQ-BLOCKER-1 CFDrs `origin/main` HEAD `1a7aa1d6`:
  - **(i)** `ci.yml` is registered (workflow id `319648723`, `state='active'`)
    but silently drops at queue time. GH Actions does NOT create a
    `ci.yml` run for PR #320, despite `pull_request` event firing the
    `book-pages.yml` sibling workflow on the same DRAFT PR. Most likely
    cause: the cross-repo composite action
    `ryancinsight/atlas/.github/actions/checkout-path-dependencies@51d8600cf3077e6ad6aafa5603b3289444b1719f`
    requires explicit allow-listing under CFDrs repo Settings -> Actions
    -> General when the consuming repo is not on the same plan tier.
    GH silently drops runs that reference unallowed private actions.
  - **(ii)** `book-pages.yml`'s `Build book` (mdbook build) step fails
    with `ERROR failed to read chapter '../../../parity_artefacts/INDEX.md'
    -- os error 2` because the runner's clean clone of `ryancinsight/CFDrs`
    ships ONLY the CFDrs source tree; the parent atlas's `parity_artefacts/INDEX.md`
    is not materialized (the existing `checkout-path-dependencies`
    action only materializes sibling sub-repo crates, NOT the parent
    atlas directory). This is the 3rd instance of the "sibling cross-reference
    missing in clean runner clone" class after the cargo path-dep
    (`ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1`) issue and the older local
    coeus-core path-dep (`ATLAS-CFDRS-COEQ-BLOCKER-1`).
- Acceptance:
  - (a) **[ADMIN-GATED]** Repo-admin Settings -> Actions -> General
    confirms `ryancinsight/atlas/.github/actions/checkout-path-dependencies`
    is allow-listed, OR the workflow invocation is rewritten to use a
    non-private-org composite action. The throwaway re-run produces a
    visible `ci.yml` run in the runs API for the branch (not zero).
  - (b) **[LOCALLY-VERIFIABLE]** `book-pages.yml` gains a pre-step that
    materializes `parity_artefacts/INDEX.md` in the runner workspace
    (via `actions/checkout` of the parent atlas repo with
    `path: ../parity_artefacts/` + `sparse-checkout: INDEX.md`, OR
    via `curl`-based raw download from the GitHub raw content URL
    against a pinned commit). Throwaway re-run shows `Build book` step
    conclude `success` (no `os error 2`).
  - (c) **[DEPENDS ON (a)+(b)]** The throwaway re-run produces the
    verbatim
    `DRIFT_DOCS_NOT_IN_SPECS: N docs figure link(s) missing from FIGURE_SPECS:`
    log line at the `ci.yml` `Check book figures` step. Captured log
    line ends the ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER gate.
- Acceptance-status disambiguation: (b) is the smaller, more deterministic
  fix (the SUMMARY.md/parent-atlas cross-reference is well-understood).
  (a) requires action outside the CFDrs repo and may need to be
  coordinated with the atlas-super-project admin. (c) inherits from (a)+(b).
- Acceptance-status disambiguation: (b) is the smaller, more deterministic
  fix (the SUMMARY.md/parent-atlas cross-reference is well-understood).
  (a) requires action outside the CFDrs repo and may need to be
  coordinated with the atlas-super-project admin.
- Risk/change class: `[patch]`; CI scaffolding only, no production-code
  change on the CFDrs application tree or on the parent atlas's
  `parity_artefacts/INDEX.md` (the canonical parity archive remains the
  consumer).
- Dependencies: tracks `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` (downstream
  consumer; the verbatim `DRIFT_DOCS_NOT_IN_SPECS: N` log capture gate).
  Follows `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1` (cargo path-dep closure)
  + `ATLAS-CFDRS-COEQ-BLOCKER-1` (coeus gitlink closure).
- Discovered-by: throwaway probe PR `ryancinsight/CFDrs#320`,
  run `30217224003`, 2026-07-26 (this delivery). Capture archive at
  `D:/atlas/verification/_throwaway_logs/cfdrs-pr320-run-30217224003-*/build/5_Build book.txt`.
- Evidence limit: per-step `conclusion=failure` JSON + verbatim mdbook
  error log; no production-code delta, no perf claim.
- Delivery (2026-07-27):
  - (b) closed: third-iteration curl pre-step landed in
    `D:/atlas/repos/CFDrs/.github/workflows/book-pages.yml`; runner-defensive
    invariants (`set -euo pipefail`, `curl --max-time 60 --retry 3 --retry-delay 5`,
    `printf | sha256sum -c` against certificate
    `18b7d9def0625f312776e15b2f70b681f38cbcb8838c9a9fd0b6ffb38af50a5a`). Pinned
    ref `51d8600cf3077e6ad6aafa5603b3289444b1719f` consistent with `ci.yml`
    atlas_ref. Code-reviewer-minimax-m3 returned GO for closing (b).
    End-to-end local emulation passes (`curl_exit=0`, `sha256_exit=0`).
  - (a) admin-gated remains open: `ci.yml` silent-drop on Ryancinsight
    DRAFT PRs unconfirmed root cause; tracked via
    `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` (the (c) follow-on requires
    both (a) + (b) closures).

## ATLAS-LETO-OPS-SPARSE-LU-001 — Real sparse LU/Cholesky in leto-ops [arch] — ✅ closed (2026-07-23 Session 17 — migrated from peer draft)

- Owner: unclaimed (atlas-meta coordinator recorded; leto peer owns `leto-ops`
  source tree and is mid-refactor — peer-active; assist ladder step 3).
- Outcome: replace the misnamed dense partial-pivoting LU currently called
  `leto_ops::SparseLuSolver` with a real sparse LU or sparse Cholesky
  factorization (this is the architectural truth the name already promises).
  The CFDrs `crates/cfd-math/src/linear_solver/direct_solver.rs` doc at lines
  3-7 currently admits "atlas-native sparse direct solver backed by dense
  partial-pivoting LU" — i.e. the public `SparseLuSolver` name IS the
  misnomer, and `crates/cfd-3d/src/fem/solver.rs` works around it by
  routing medium systems to GMRES+AMG via `with_direct_threshold(512)`.
- Acceptance (architectural): real O(n) sparse factorization in `leto-ops`;
  the threshold routing becomes unnecessary; `SparseLuSolver` true to name
  (or renamed to a sparse algorithm and call sites updated in one migration
  per `consolidation_discipline: compatibility soup`).
- Risk/change class: `[arch]` + `[minor]` (no public-API break required if
  kept the same name; renaming is a `[major]` migration);
  upstream ownership (`architecture_scoping`) — implemented in `leto-ops`, not
  approximated downstream in CFDrs.
- Open question: peer is mid-refactor on leto-ops (the source is presently
  uncompilable in HEAD `9346413`; cf. "Residual CFDrs watchpoints carried
  forward" below). Wait for peer to land stabilization; then evaluate whether
  the FEM matmat structure warrants Cholesky (symmetric positive definite) or
  LU (saddle-point is indefinite).
  RESOLVED 2026-07-23: saddle-point indefinite (Brezzi 1974) → real sparse LU
  path chosen over Cholesky, per ADR 0031. Closed at leto origin/main `687b670`;
  see Session 17 closure entry appended at file tail for evidence matrix.
- Refs: backlog.md#CFDRS-PERF-SLOW-001, ATLAS-CFDRS-PERF-045.

## Cross-repo architect coordination ledger

Three CR-class items carried from `docs/audit/2026-07-02-cross-repo-integration-audit.md` (`L71-149`). Each is self-contained and gates specific consumer-side migrations below.

| ID | Class | Title | Owner repo (provider land) | Supertypes | Consumer land unlocked |
| --- | --- | --- | --- | --- | --- |
| **CR-4** | `[major]` | Rebase `coeus-core::Scalar` + `leto-ops::Scalar` over `eunomia::NumericElement` as the universal supertrait (single SSOT) — **✅ CLOSED 2026-07-09** (eunomia `57d7789`, coeus `2b3f820`, leto PR #31 merge `d9e8ac9`; ADR 0005 Accepted; re-verified 2026-07-22: `leto-ops/src/domain/scalar.rs:11` and `coeus-core/src/dtype/traits.rs:295` carry `Scalar: NumericElement`; consumer unlocks tracked and closed in batches #2/#3). Delete the vocabulary that already lives on `NumericElement` (`zero`/`one`/`to_f64`/`from_f64`/`from_usize`/`sqrt_val`/`abs_val`); keep the backend-specific slice-kernel surface (`add_slice`/.../`max_slice`, `gemv_*`, `tiled_gemm`, `axpy_rows`, leto-ops `from_usize`). See `atlas/docs/adr/0005-eunomia-scalar-ssot.md` for the proof that `RealField` (float-only) cannot be a universal `Scalar` supertrait (would orphan `coeus_core::Int` for i8/u8/.../u64). | `coeus`, `leto` (joint) | `eunomia` is doctrine holder | kwavers `RealField` nalgebra → eunomia; CFDrs `cfd-math` solver-chain RealField seam; ritk `Burn::Module → coeus::Module` rebind |
| **CR-2** | `[arch]` | Consolidate `#[global_allocator]` to a single binary-only registration. Strip from `cfd-core`, `ritk-core`, `moirai/lib`. Pass `Mnemosyne` handles via DI to library callers. | `cfd-core`, `ritk-core`, `moirai` (joint) | `mnemosyne` is allocator holder | Library composition stays provider-neutral; binaries own allocator policy — **✅ CLOSED 2026-07-18** (`cfd-core` ✅, `moirai` ✅, `ritk-core` ✅; zero `#[global_allocator]` in all three library crates) |
| **CR-1** | `[arch]` | Delete `apollo/crates/apollo-ghostcell` standalone GhostCell reimplementation; redirect all apollo sites to `melinoe::MelinoeCell` (with `brand_scope!` mint). | `apollo`, `melinoe` (consumer) | `melinoe` is brand doctrine holder | All brand-borrow contention becomes provider-exclusive — **✅ CLOSED 2026-07-07** (Apollo commit `50029b7` deletes `crates/apollo-ghostcell`; `repos/moirai/Cargo.toml` aligned to `melinoe = 0.8.0`; focused nextest `-p apollo-validation melinoe` 2/2 green and `-p apollo-sft -p apollo-radon` 43/43 green; `find_path repos/apollo/crates/apollo-ghostcell/**` returns zero files 2026-07-20 re-confirm; full evidence at `gap_audit.md` L1429-1430) |

### Provider extension register

These cross-cut consumer migration but live in provider land. Each requires its own [minor] backlog entry in the owning provider repo:

| Provider | Missing surface | Substrate | Tracked in |
| --- | --- | --- | --- |
| `leto` | ✅ `Quaternion<T>` Add/Sub/Neg/Mul&lt;T&gt;/Div&lt;T&gt; + `try_inverse` + `to_rotation_matrix`; ✅ `FixedMatrix&lt;4,4&gt;` determinant/try_inverse + generic Add/Sub/Neg/Mul&lt;T&gt;/Div&lt;T&gt;/Assign. **Verified 2026-07-14**: 229/229 tests green, clippy `-D warnings` clean. | math | `leto/backlog.md` |
| `leto-ops` | ✅ `CscMatrix<T>`, `CooMatrix<T>`, `lu_batch`; `ExecutionStrategy` trait — all verified present at `leto/crates/leto-ops/src/`. | ops | `leto/backlog.md` |
| `moirai-async` | ✅ `mpsc::channel`, `oneshot::channel`, `Condvar`, `Mutex`, and `#[moirai::main]` exist. `ATLAS-MOIRAI-016` cancellation audit closed: Condvar lost-notification race fixed (pre-register waiter while holding guard), mpsc/oneshot waker leaks fixed (Drop impls with ID-based cleanup), 82/82 nextest pass with 2 regression tests. | async | `moirai/docs/backlog.md` |
| `apollo` | ✅ RustFFT-free differential oracle — pure O(N²) DFT reference replaces rustfft. `b291003` on `codex/remove-rustfft`. Workspace `rustfft = "6.4.1"` pin removed; `external-references` feature removed; dev-dep and vs_rustfft benchmark removed; xtask benchmark runner stripped. | validate | `apollo/backlog.md` |
| `eunomia` | ✅ eunomia-gpu deleted (E-019); folded into `hephaestus::DialectScalar`. README clean — no aspirational claims about eunomia-gpu. | basis | `eunomia/backlog.md` |
| `coeus` | ✅ `scatter_add` exists at Tensor/Var/Python; all 6 comparison ops (eq/ne/lt/gt/le/ge) exist. `Dataset`/`DataLoader` deferred per "if PINN dataset paths require" condition — no PINN path in current scope requires them. | autograd | `coeus/docs/backlog.md` |
| `hephaestus` | ✅ `f64` DialectScalar impls (Wgsl `"f64"`, CudaC `"double"`) + 24 GPU vector type impls via macro. **Verified 2026-07-14**: 47/47 nextest green, clippy `-D warnings` clean. Remaining: `wgpu::PipelineCache` integration (WG-P8); CU-P1 async-stream-overlap. | gpu | `hephaestus/backlog.md` |

---

## Migration batches (vertical slices)

Ordered per Definition-of-Ready (provider SSOT closes first). Each batch is self-contained, has observable pass conditions, and respects the WIP limit (one in-flight merge-affecting item per micro-sprint). Cross-repo item as policy: one batch is **the** item; commits ride under the established `codex/kwavers-atlas-integration` branch through that batch's owner.

### Consumer-side (kwavers / CFDrs / ritk)

| Batch | Class | Crate | Surface | Pre-reqs | Pass condition (value-semantic) | File-line scope (illustrative) |
| --- | --- | --- | --- | --- | --- | --- |
| #1 | `[patch]` | `kwavers-solver` ([side path RTM/elastic PDE](file_pattern)) | `par_for_each` Zip → `moirai-parallel::par_mut().enumerate()` (62 sites); `Zip::indexed` → `par().enumerate()` (24 sites) | (none — confirmed by `moirai-parallel/src/lib.rs:106-181` tan rename) | ✅ **CLOSED 2026-07-12** at peer commit `5913f2946`: zero `par_for_each` source sites, zero `burn::` hits, zero `nalgebra` hits, zero `use ndarray` imports; `kwavers-solver/Cargo.toml` clean of `ndarray`/`rayon`/`burn` (substrate is `leto` + `leto-ops` + `moirai-parallel`); `cargo nextest run --workspace --exclude kwavers-driver --no-fail-fast --lib` 5117/5119 pass (2 timeouts are pre-existing KW-WATCH-002 perf on the 90s `elastic-fwi` profile override — peer-stream perf, NOT a Batch #1 regression). Atlas-meta `repos/kwavers` gitlink advanced `01643ed9 → 5913f2946`. | `crates/kwavers-solver/src/inverse/reconstruction/seismic/rtm/inherent/{wavefield,propagation,mod,laplacian,imaging,illumination}.rs`; `crates/kwavers-solver/src/forward/nonlinear/{kuznetsov,westervelt_spectral}/...`; `crates/kwavers-solver/src/forward/{elastic/swe/int, pstd/ext, multiphysics/fluid_structure}/...`; `crates/kwavers-physics/src/acoustics/...`; `crates/kwavers-physics/src/optics/polarization/linear.rs` |
| #2 | `[minor]` | `CFDrs/cfd-math` ([ite solver finish](file_pattern) + `cfd-1d`/`cfd-3d`/`cfd-validation`) | nalgebra → let, nalgebra-sparse → leto-ops `CsrMatrix`; covariance solves / geometry / finite-element typedefs | CR-4 (eunomia SSOT) so `RealField → eunomia::RealField` is universal | `cargo nextest run -p cfd-math -p cfd-3d -p cfd-1d -p cfd-validation` green; xtask scanner delta shows `nalgebra` allowlist contracts under cfdec-solver chain, cfd-3d fem/libnodes, cfd-1d linear_system and cfd-validation geometry; `nalgebra-sparse` allowlist contracts to zero | `cfd-math/src/linear_solver/{chain, preconditioners/{*, ilu/*, multigrid/*, schwarz, ssor}}.rs`; `cfd-3d/src/fem/{element, projection_solver, leto_bridge, solver, stabilization, stress, quadrature, shape, fluid}.rs`; `cfd-3d/src/{bifurcation, trifurcation, venturi, serpentine, ibm}/**`; `cfd-3d/src/vof/{cavitation, reconstruction}.rs`; `cfd-1d/src/solver/core/{convergence,linear_system,matrix_assembly,state,workspace,anderson,solver_detection}.rs`; `cfd-validation/src/{geometry, benchmarks, literature, manufactured, numerical, adaptive_mesh, tests}/**` |
| #3 | `[minor]` | `ritk` ([Provider-side Burn trait rebind](file_pattern)) | `ritk_core::{Image, Transform, Interpolator}` → `coeus_core::{ComputeBackend, Scalar}`; `ritk-spatial::{Vector,Point,Direction}` lose `burn::module::{Module,AutodiffModule}+burn::record::Record` impls; `ritk-image::types::Image<B,D>` re-exports exit Burn-keyed facade | CR-4 so eunomia `Scalar/RealField` is universal | `ritk-image::native::Image<T: Scalar, B: ComputeBackend, const D: usize>` becomes the canonical re-export; `cargo nextest run -p ritk-{core, image, filter, registration, segmentation, transform, interpolation}` green; `cargo tree --workspace -i burn-wgpu`, `cargo tree --workspace -i burn-cuda`, and `cargo tree --workspace -i burn-rocm` each return zero (Burn only CPU NdArray backend remains per DEP-496-01) | `ritk-core/src/{image/types,transform/trait_,interpolation/trait_}.rs`; `ritk-spatial/src/{vector,point,direction,spacing}.rs`; `ritk-image/src/types.rs` + `ritk-image/src/lib.rs:11` re-export line; `ritk-wgpu-compat/src/lib.rs` (`apply_row_chunks` `B:Backend` bound → `B:ComputeBackend`); per-filter `*/new(B::Device)` constructors |
| #4 | `[minor]` | `kwavers-solver` ([PINN Burn → Coeus](file_pattern)) | `burn::backend::NdArray<f32>` ⇒ `coeus-core::MoiraiBackend`; `burn::optim::{SGD,Adam,AdamW,lr_schedule::*}` ⇒ `coeus-optim::*`; `burn::module::Module` ⇒ `coeus-nn::Module`; `burn::record::Record` ⇒ `coeus-nn::Record`; `burn::tensor::*` ⇒ `coeus-tensor::*`; ~325 source lines + ~17 top-level dev-dep files | CR-4 + #3 + `coeus-autograd/scatter_add` extension | `cargo nextest run -p kwavers-solver --features pinn` green; per-physics trainer residual gradient matches golden reference within neum-compensated epsilon (derived from reduction depth × sqrt(N) per current `es::BatchModern` chain); kwavers top-level `Cargo.toml:138` `[dev-dependencies] burn = "0.19"` flips to deps via `coeus` (or top-level burn demoted fully) | `crates/kwavers-solver/src/inverse/pinn/**` (~80 files; cite-referenced inside the inventory in checklist.md); top-level `crates/kwavers/{benches,examples,tests}/**` (17 files); `kwavers-solver/Cargo.toml:42` feature set; `kwavers/Cargo.toml:138` dev-deps |
| #5 | `[arch]` | CR-1: `apollo-ghostcell` deletion + `melinoe::MelinoeCell` rebind (provider land) — single coordinated commit | (See provider-extension register above) | (None — provider-only action) | (See CR-1 row above) | `apollo/crates/apollo-ghostcell/src/lib.rs` removed; every apollo consumer routed via `melinoe::MelinoeCell`; `cargo nextest run -p apollo-* --features melinoe` green; `cargo miri test -p melinoe` green |
| #6 | `[arch]` | CR-2: Consolidate `#[global_allocator]` (provider land) — single coordinated commit across `cfd-core`, `ritk-core`, `moirai/lib` | (See CR-2 row above) | (None) | (See CR-2 row above) | Library registry sites reduced; per-binary (`kwavers-cli`, `cfd-cli`, `helios`, `ritk-cli`, `mnemosyne-gbench`, etc.) keeps or replaces registration; `cargo build -p cfd-core` without `mnemosyne` feature succeeds |
| #7 | `[arch]` | CR-4: `coeus-core::Scalar` + `leto-ops::Scalar` rebase to eunomia supertraits (provider land) — **STATUS: ✅ CLOSED 2026-07-09. eunomia (`57d7789` ✅), coeus (`2b3f820` ✅), leto (`86d366bc` ✅ on `main` via PR #31 merge `d9e8ac9`)** | (See CR-4 row above) | (None) | (See CR-4 row above) | eunomia: `eunomia/crates/eunomia/src/traits/numeric.rs` doc clarified (ZERO/ONE/sqrt/abs/to_f64 stay FloatElement for float paths); Complex<T>/isize/usize implementations added. coeus: `coeus/coeus-core/src/dtype/traits.rs` (`Scalar: NumericElement + CpuUnaryDispatch + Pod + Rem + Clone`); 64-file coeus call-site disambiguation landed. leto: `leto/crates/leto-ops/src/domain/scalar.rs` `pub trait Scalar: NumericElement` rebind; redundant UFCS items removed (ZERO/ONE/add/sub/mul/div/bitand/bitor/bitxor/count_ones/to_f64); slice kernels given default bodies; `from_usize` retained. `Cargo.toml` workspace version `0.35.1 → 0.36.0`. Resolution (a) applied (additive rebind is structurally infeasible per `atlas/checklist.md` structural-infeasibility addendum + E0034 evidence). Verification (pre-merge on `codex/leto-cr4-ssot-rebind`, 5 files / 196 +/-622 net subtraction): `cargo nextest run -p leto-ops` 270/270 green + `-p leto` 189/189 green + 8 doctests green + clippy `-D warnings` green on `--lib --tests` scope. Pixel/range/structural artifact: net 466-line subtractive consolidation (no vocab duplication remains). RG-verified zero `Scalar::add/sub/mul/div/ZERO/ONE/bitand/bitor/bitxor/count_ones/to_f64` UFCS references in `crates/`. |
| #8 | `[minor]` | Provider extension (provider land): ✅ `leto` (Quaternion ops, FixedMatrix<4,4> ops) — verified; ✅ `hephaestus` (DialectScalar f64 + GPU vectors) — verified; ✅ `moirai-async` (mpsc/oneshot/Condvar/Mutex/`#[moirai::main]`) — verified; remaining: `apollo`, `eunomia`, `coeus`, `leto-ops` | (See provider-extension register above) | (Threads across consumer migration; file as individual [minor] items in owning repos) | (See register above) | tracked separately in `repos/<provider>/backlog.md` |

### Token batch ordering

Batches #5, #6, #7 are the [arch] provider-SSOT gates. Per `decision_policy` nternals:

1. **#7 first** (CR-4 eunomia SSOT) — **ALL SIDES ✅ CLOSED 2026-07-09**. eunomia (`57d7789` ✅), coeus (`2b3f820` ✅), leto (`86d366bc` ✅ on `main` via PR #31 merge `d9e8ac9` — Resolution (a): rebase onto origin/main post-PR-#30, `Scalar: NumericElement` supertrait, redundant UFCS items removed). Unblocks #2 (CFDrs nalgebra finish), #3 (ritk Burn rebind), and #4 (kwavers PINN Burn → coeus). ADR `0005-eunomia-scalar-ssot.md` (status **Accepted**) describes the actual rebase; `RealField` is NOT a universal `Scalar` supertrait (would orphan `Int`); `NumericElement` is. ADR signed off via autonomy mode per `interaction_policy`.
2. **#5 second** (CR-1) — Pure provider cleanup; no consumer call sites depend on it for the migration below.
3. **#6 third** (CR-2) — Library-vs-binary layering. **cfd-core ✅, moirai ✅ landed** (2026-07-10). **ritk-core ✅ committed** (`ba6da3a5`, 2026-07-14). All sites resolved.
4. **#1 fourth** — `kwavers-solver` residual Rayon → Moirai. Self-contained. Calls CTE immediately after a clean CR-4. ✅ **CLOSED 2026-07-12** — kwavers peer commit `5913f2946` (`perf(kwavers-solver): Migrate solver tree to moirai parallel iterators`) drives source-site count to zero: `par_for_each`=0, `burn::`=0, `nalgebra`=0, `use ndarray`=0, `kwavers-solver/Cargo.toml` clean of `ndarray`/`rayon`/`burn` (substrate is `leto` + `leto-ops` + `moirai-parallel` only). `cargo nextest run --workspace --exclude kwavers-driver --no-fail-fast --lib`: 5117/5119 pass, 2 timeouts (pre-existing KW-WATCH-002 abdominal-preprocessing perf on 90s `elastic-fwi` profile override — peer-stream perf, NOT a Batch #1 regression). `cargo check -p kwavers-solver --features pinn` PASSES (Batch #4 co-verified closed). Atlas-meta `repos/kwavers` gitlink advanced `01643ed9 → 5913f2946`. Sole residual is the `kwavers-solver/Cargo.toml` `ndarray` `rayon` feature gate, flagged separately in the peer commit body — manifest detail tracked as a kwavers-peer follow-up. Batch #4 (`kwavers-solver PINN Burn → Coeus`) is also closed at this HEAD (co-verified).
5. **#2 fifth** — Largest consumer body (176 CFDrs source files). Depends on CR-4. ✅ **CLOSED 2026-07-05** — inner CFDrs HEAD advanced `0f578e1af110c5b8536476174bf266bf8b812c37` → **`d58d1fe320d046816425e1d20d16735fcfee7995`** via a single Atlas-provider migration push (subject `refactor(cfdrs): Atlas-provider migration push (Leto CSR + Eunomia scalar + Hephaestus GPU + cfd-math / cfd-2d / cfd-3d / cfd-1d / cfd-validation consumer cones)` — 752 modified + 19 added files, 51,857 insertions / 22,087 deletions, ~2,500 tests pass, 0 warnings). Atlas-parent submodule pointer advance recorded at parent HEAD `51922a56c4d4acab3dbe786b90cc5acf92e22277` (`chore(atlas): Advance CFDrs submodule pointer to d58d1fe3`).
6. **#3 sixth** — ritk Burn keyed-trait rebind. ✅ **CLOSED 2026-07-18**.
7. **#4 seventh** — kwavers-solver PINN Burn → coeus. ✅ **CLOSED 2026-07-12**.
8. **#8 last** — Provider extensions; tracked in provider repos separately; own claim stream.

### Batch #3 sub-batches (ritk Burn-trait rebind — 6 atomic commits per ADR 0012)

`Batch #3` (`[minor]` ritk Burn-keyed trait rebind) is decomposed into 6 atomic sub-batches per [`atlas/docs/adr/0012-ritk-burn-trait-rebind.md`](docs/adr/0012-ritk-burn-trait-rebind.md) (Accepted 2026-07-06). Each sub-batch widens the Atlas surface OR narrows the Burn surface — never both in one commit — atomic-boundary discipline per ADR 0012 §Decision. Reserved inner tag: `ritk/atlas-migration-push/batch3` (per ADR 0010 §Decision §"Per-batch name pattern").

**Historical sub-batch #3 framework (opened 2026-07-06; fully consumed
2026-07-18)**: the following per-crate queue records the original atomic
decomposition. PR #42 consumed #3.a–#3.g and #4–#6; PR #43 closed the ledger,
so no reservation or open queue remains.

| Sub-batch | Class | Atomic-boundary disposition | Closeout per sub-batch | Status (2026-07-09) |
|-----------|-------|------------------------------|-----------------------|---------------------|
| #1 | `[patch]` | **Additive** — Atlas-typed parallel trait surface (`TransformAtlas<T,B,D>`, `InterpolatorAtlas<T,B>`, `ResampleableAtlas<T,B,D>`) + `pub use native::Image as AtlasImage;` re-export. Burn-keyed surface untouched. | `cargo nextest run -p ritk-{core,image,filter,registration,segmentation,transform,interpolation,spatial}` green + `cargo tree --workspace -i burn-wgpu` (and `cuda`, `rocm`) zero | **closed 2026-07-06** |
| #2 | `[patch]` | **Subtractive-by-documentation** — soft docstring deprecation ONLY on Burn-keyed surface. No `#[deprecated]` attr (would emit 671-file compile-warning cascade). | (same gates as #1) | **closed 2026-07-06** |
| #3 | `[minor]` | **Subtractive-by-conversion (7 per-crate queue)**: Atlas-typed migrator test-source ports from `burn_ndarray::NdArray<B>` to `AtlasImage<T: Scalar, B: ComputeBackend, D>` over `coeus_tensor::Tensor<T, MoiraiBackend>`. Per-crate atomic-boundary discipline per ADR 0012. | (same gates as #1) | **✅ CLOSED 2026-07-18** — All sub-batches consumed by PR #42 `f01b1643` (1298 files, -59482 lines) + PR #43 `b4be04ca` (closeout docs). burn_surface.allowlist deleted; all Burn/ndarray deps removed. |
| #4 | `[patch]` | **Subtractive-by-impl-removal** — `ritk-spatial::{Vector, Point, Direction, Spacing}` drop `burn::module::{Module, AutodiffModule}` + `burn::record::Record` impls. Atlas-side impls only IF `coeus-nn` PINN consumer code requires. | (same gates as #1) | **✅ CLOSED 2026-07-18** — Consumed by PR #42 atomic cutover. |
| #5 | `[major]` | **Subtractive-by-dep-strip** + **subtractive-by-reexport** — Cargo dep strip `burn` + `burn-ndarray` from manifests; `pub use types::Image;` re-export path switch; `apply_row_chunks<B: Backend>` removal. **THIS IS THE ONLY SUB-BATCH ALLOWED TO DELETE OR RENAME `[dependencies]` LINES.** | (same gates as #1) + `cargo semver-checks release -p ritk-core -p ritk-image -p ritk-spatial` authoritative classification | **✅ CLOSED 2026-07-18** — Consumed by PR #42 atomic cutover. |
| #6 | `[patch]` | **Subtractive-by-allowlist-contract** — `xtask/burn_surface.allowlist` reset on sub-batch #5 re-enter; CI scan gates tighten: zero `burn::tensor::Backend`-bound public symbols + Atlas-only backend trait assertion. | CI gate asserts `coeus_core::ComputeBackend` is the only atlas-side backend trait in the cross-crate re-export graph | **✅ CLOSED 2026-07-18** — burn_surface.allowlist deleted in PR #42. |

### Historical in-flight claims (superseded)

> This section preserves dated coordination snapshots. It does not describe
> current work; the live board at the top of this file is authoritative.

- Atlas-meta branch: `codex/kwavers-atlas-integration` (PM artifacts only).
- Atlas-meta claim scope (this turn): `backlog.md`, `checklist.md`, `gap_audit.md` at the atlas workspace root; no per-repo files touched at the atlas-meta layer.
- **Mnemosyne fixed Themis pin** [patch]: **DONE** — PR #11 merged as `f95d372`; Mnemosyne pins Themis 0.10 at `18807bb`, with metadata, clippy, 288/288 nextest, doctests, and docs green.
- **Leto Themis co-evolution and provider extension** [patch]: **DONE** — PR #32 merged as `8d39f58`; the lock graph, cache-level contract, quaternion interpolation, and fixed-matrix value contracts are verified by the complete local gate.
- **Hermes fixed Themis pin** [patch]: **DELIVERED / MERGE-BLOCKED** — PR #6 commit `6080aa4` pins Themis 0.10 at `18807bb`; all CI checks pass except the pre-existing Miri allocator failure reproduced on Hermes main. The PR remains open pending that independent correctness residual.
- Atlas-meta last landed (codex session): `61931faf` (RITK Batch #3 sub-batch #1 sync + kwavers/Burn risk surfacing, 2026-07-06, layered atop peer commits `e82fe14c`, `4a04cad1`, `4b71cda9`, `3062ce1b`, `c5f2a84e`, `61931faf` itself; followed by peer `5adf4a27` "Helios closure triage" 2026-07-06 13:37). This turn: peer landed `c6b845f81` Batch #4 slice 2 (`burn_wave_equation_2d` dependency graph: 12-family native Burn→Coeus rewrite; `burn::` line-hits 315→186, file-count 144→80). See risk #8 below.
- **This codex session (2026-07-08, Bulk-provider-surface round-1 + round-2 + round-3)**: three sequential bulk-advance blocks landed (round-1 `2e1c4f20d`→`274a6a961`→`a12d1dd77` for apollo/coeus/hermes/melinoe/ritk + themis pointer refreshes; round-2 `5d3395e95` + `715cff24e` + `02da06611`→`ab71f08ad`→`36acbbca9` for hermes-r2/coeus/cascade + multi-PM-reconciliations + `.gitignore hardening); round-3 `ad6cf57d4`→`1828ea14a`→`852de7129`→`769b70a67`→`1fe3c0e56` for apollo/eunomia/hermes/leto/mnemosyne). See `gap_audit.md` row 13 for the per-submodule advance record + provenance triples + branch-context notes (especially hermes on `rescue/detached-simd-numa-work` divergent 17 commits ahead of `origin/main`, NOT peer-WIP at the parent gitlink level; mnemosyne sjump `482670d` → `98a02b6` reflects the Miri alloc/free HIGH-PRIORITY finding at `eff(backend)` + `fix(backend)` + `docs(gap_audit)` chain). **Net alignment state post-`1fe3c0e56`**: all 12 actively-tracked submodules (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, kwavers) ALIGNED at inner HEAD with zero DIVERGED gitlinks — the first all-aligned state since the `e0bf55684` cross-tree reclamation audit. **ritk-python test suite (47/47)** compiled+passed at committed inner HEAD `1f49278c` (value-semantic asserts — see `gap_audit.md` row 154 bulk-advance unblock evidence). **KW-CV-001 watchpoint re-affirmed ACTIVE** at inner HEAD `35ee01076`: trigger `(cd /d/atlas/repos/kwavers && git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l)` returns 0; peer continues slice-by-slice Batch #1 + Batch #4 work without explicit closeout commit. **Atlanta-meta path forward**: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit (per `concurrent_agents` disjoint-scope rule); the round-3 block leaves kwavers at the peer-tracked HEAD `35ee01076` (atlas-meta gitlink already aligned, not divergent, just not watching for closure-style advances here — the KW-CV-001 watchpoint owns that path). **Branch context**: this turn's round-3 work landed under `codex/kwavers-atlas-integration`; `36acbbca9` `.gitignore` hardening prevents transient root scratch artifacts from re-entering `git status --short` (no body-scratch file was created for any of the 5 round-3 chore commits, per the user's signal-change-in-the-tree batch ceremony convention from ADR 0010 §Per-batch name pattern; each commit body authored inline via subject + body `-m` pairs + a final `-m` provenance-triple block citing row 11 dynamic-SHA extraction). **Cross-references**: `gap_audit.md` row 13 (per-submodule advance record with prior-SHA + derived-full-SHA + inner-chore-subject for each of the 5 round-3 modules); `checklist.md` §Next micro-sprint for the round-3 line-item summary. **Residual risks** (tracked in `gap_audit.md` row 6 row-268–270 kwavers sub-bullets): kwavers 267 dirty files at inner HEAD `35ee01076` is peer-WIP, not reclaimable from atlas-meta; kwavers Batch #1 closure condition (zero `par_for_each` source sites) is NOT yet met (41 sites across 15 files per `gap_audit.md` line-93); kwavers Batch #4 closeout condition (zero `burn::` source hits + zero `crates/kwavers-solver/Cargo.toml:42` burn dev-deps + `burn.rs`/`burn_compat` deletion) WAS met at `05500930c` per the line-92 sub-bullet (file deletion + manifest strip landed on the peer stream). The next bulk-advance round (round-4) is contingent on either inner HEAD churn (peer-WIP-after-push divergence) OR KW-CV-001 firing for kwavers.
- **This codex session (2026-07-06, Helios closure)**: `c5f2a84e` closed the direct Helios H-061/H-062 dependency slice by removing the unused `num-traits` workspace edge, removing the aggregate dicom-rs `ndarray` feature edge, adding the local Melinoe patch required by patched Gaia's `melinoe` 0.8.0 edge, and syncing Helios PM evidence. Concurrent peer commit `61931faf` then landed the RITK Batch #3 sub-batch #1 Atlas-parent pointer advance; preserve that pointer state.
- **This codex session (2026-07-06, Helios/RITK DICOM ownership)**: RITK inner commit `8f8360ff` adds `ritk-dicom::{DicomTag, tags, DicomAttributeRead}` so downstream DICOM geometry/modality-LUT attribute reads are RITK-owned. Helios H-061 now routes production DICOM parsing, typed attributes, transfer-syntax lookup, and pixel decode through `ritk-dicom`; dicom-rs remains direct only as a dev-dependency for synthetic Part 10 fixture generation. Helios H-063 is filed for the remaining `helios-imaging` audit: generic medical-image I/O/registration/toolkit operations move upstream to RITK; radiation-domain MVCT projection/reconstruction kernels stay in Helios.
- **This codex session (2026-07-07, RITK DEP-497-01 dead-dep strip)**: `repos/ritk` commits `7a66d1ee` (strip unused production `burn` dep from 17 leaf crates: `ritk-{cli,core,filter,io,jpeg,metaimage,mgh,minc,model,nifti,nrrd,png,registration,segmentation,snap,statistics,tiff,transform,vtk}`; `burn-ndarray` dev-dep retained where sub-batch #3 per-crate test ports are still open) + `00d57005` (checklist sync), pushed to `origin/main`. Distinct from Batch #3 sub-batch #5 (`[major]` full Burn Cargo strip + `Image<B,D>` re-export) per ADR 0012 — this is a non-breaking dead-edge removal, no version bump. Verified: `cargo nextest run` across the 19 touched crates 4258/4258 green, `cargo clippy --workspace --all-targets -D warnings` clean, `cargo fmt --check` clean for touched crates, `cargo doc --no-deps` no new warnings. Fixed an incidental `clippy::doc_lazy_continuation` false-positive in `ritk-model/src/ssmmorph/encoder/tests.rs`. Residual risks filed in `repos/ritk/checklist.md` (2 pre-existing broken intra-doc links in `ritk-filter`; a full-workspace-nextest-only timeout in `ritk-snap::pacs_ops` reproduced only under full-parallel resource contention, isolated run passes in 2.1s — not a hang). Atlas-meta `repos/ritk` gitlink advanced to `00d57005` via the dynamic-SHA-extraction convention (gap_audit.md row 11).
- **`repos/kwavers` `codex/kwavers-core-moirai-parallel` — peer ryancinsight ACTIVE** (inner HEAD `05500930c` 2026-07-07 19:11, `[ahead 0, behind 0]` of `origin/codex/kwavers-core-moirai-parallel` per inner `git rev-list --left-right --count`; atlas-meta `HEAD:repos/kwavers` gitlink pinned at `7235d464afb04dfec62dee1cd8e6e8d660b54250` lagging inner HEAD by 37 commits). State at inner HEAD `05500930c` per T1 verification: **Batch #4 (kwavers-solver PINN Burn → Coeus) source-residual is now ZERO** — canonical inner chore `8b128c478` "Remove dead burn compatibility shim and drop burn dependency" + slice 3+ commits drained the residual; `crates/kwavers-solver/src/burn.rs` + `burn_compat` module ABSENT; `rg -n '\bburn\b' -g '*.toml' .` zero hits in `crates/kwavers-solver/Cargo.toml` + root `Cargo.toml`; `rg -l '\bburn::' crates --type rust` zero hits across the kwavers source tree (was 186 line-hits / 80 files at `b605e2e74`, full clean at `05500930c`). **Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai)**: `crates/kwavers-{solver,physics}/Cargo.toml:{24,20}` now read `ndarray = { version = "0.16", features = ["serde"] }` (per peer `702e4f125` "drop unused ndarray/rayon feature from kwavers manifests"; the `rayon` feature strip is landed, contradicting the prior stale paragraph that read `features = ["rayon", "serde"]`); residual is now **41 `.par_for_each()` sites across 15 files** in `crates/kwavers-solver/src` (down from 84 sites / 28 files at `b605e2e74`, −51%) — concentration in `forward/{elastic/swe/{integration/integrator/mod,stress/divergence}, nonlinear/{kuznetsov/{diffusion,nonlinear,numerical,operator_splitting/mod,solver/{model_impl,rhs},spectral,workspace}, westervelt_spectral/spectral}, pstd/extensions/{elastic,elastic_orchestrator/pml/mod}, multiphysics/fluid_structure/{interface,solver/struct_impl}}`. Closeout state: no formal `closeout` / `final` / `completion` commit in the last 30 inner commits — peer lands Batch #4 + Batch #1 slice-by-slice without explicit closure commits. **Atlas-meta continues to defer parent-side pointer advance** for `repos/kwavers` until a kwavers-side final closeout commit lands (per `concurrent_agents` disjoint-scope rule). `burn.rs` + `burn_compat` facade deletion + Cargo.toml strip are LANDED on the inner peer stream (lifting the surrogate pre-condition cited in sub-batch #5 standing reminder per `docs/adr/0012-ritk-burn-trait-rebind.md`). See `gap_audit.md` row 6 kwavers sub-bullets L268-L270 for the kwavers-side reconciliation record.
- Neighbor claim streams to honor (disjoint from kwavers Batch #1, also DO NOT touch): `repos/moirai` `refactor/remove-dead-subsystems` (26 dirty paths — moirai source forbidden); `repos/leto` `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile (14 dirty paths — leto source forbidden); `repos/coeus` `main` (19 dirty paths); `repos/eunomia` `main` (`acos`/`asin`/`atan` peer queue, 7 dirty paths); `repos/apollo` (235), `repos/CFDrs` (79), `repos/gaia` (5), `repos/hermes` (46), and `repos/melinoe` (13) carry in-flight peer claims. `repos/helios`, `repos/ritk`, `repos/hephaestus`, `repos/mnemosyne`, and `repos/themis` are clean of inner dirty paths after the Helios/RITK DICOM ownership closure and prior pointer-sync commits.
- The moirai-parallel API surface for kwavers Batch #1 already exists: `for_each_chunk_pair_mut_enumerated_with`, `for_each_chunk_triple_mut_enumerated_with`, `for_each_chunk_quad_mut_enumerated_with`, `enumerate_mut_with`, `for_each_index_with` (moirai-parallel `src/ops.rs:281,335,408,125,155`). No moirai source change is required for Batch #1 closure; the consumer-side helpers in `crates/kwavers-physics/src/parallel.rs` already cover 1-mut + N-imm and 2-mut + N-imm arities, with 3-mut + N-imm and 4-mut + N-imm indexed zips (visible in `kwavers-solver/src/forward/elastic/swe/{integration/integrator/mod.rs,stress/divergence.rs}` and `forward/pstd/extensions/elastic.rs` and `forward/pstd/extensions/elastic_orchestrator/split_field_step/{stress,velocity,mod}.rs`) as the remaining helper-coverage gap.

- **This codex session (2026-07-08, Bulk-provider-surface round-4 — post-OOB `6902d2e92` re-probe)**: 7 atomic chore captures in this turn. The OOB consolidation commit `6902d2e92` ("chore(atlas): Advance repos/hephaestus pointer to 240b260 (CU-P6/CU-M3)") absorbed my staged round-4 reset state, capturing `hermes` `5ad1b58 → c7b17b02` + `leto` `a9572da → 86d366bc` (batched LU / CSC sparse format / CG/GMRES iterative solvers — unblocks kwavers-solver Bulk-solver migration closure target) bundled into a single `e3223094a`. The remaining per-crate captures split into one-atomic-chore-per-crate for cleanliness:
  - `6a598da91` kwavers `35ee01076 → 89117870` (inner `Migrate kwavers Complex/ndarray types to eunomia/leto atlas crates` — Phase-3 closure of Complex<f32>/f64, ndarray Array, coefficient paths onto eunomia+leto substrates; replaces nalgebra/ndarray/numeric-complex stack in kwavers-core domain)
  - `0e34ae082` coeus `e36f95f → ec69a6a` (inner `fix(coeus-dist): close TOCTOU race in TCP test port allocation` + co-emitted `342f38d` MS-406/407 reconciliation; TOCTOU between bind and listen eliminated in coeus-distributed harness)
  - `045291499` ritk `1f49278c → e75d8748` (inner `Add Module/AutodiffModule impls for DisplacementField and DisplacementFieldTransform` — DIRECTLY resolves the displacement_registration_test failure tracked in row 6; Sub-batch #5 RITK-spatial-rebind closure per ADR 0012)
  - `4a4cf928a` coeus `ec69a6a → 006f2a7` (inner `feat(coeus-nn): add MaxPool3d/AvgPool3d benchmark rows (G-043)` — criterion bench registry extension for 3D pooling kernels)
  - `4b7f4804e` kwavers `89117870 → 09c645f30` (inner `Migrate kwavers-core/source/signal/grid/field from ndarray to leto` — Phase-4 closure of kwavers-core domain crates source/signal/grid/field off ndarray onto leto's NDArray substrate; follow-on to `89117870`)
  - **Net alignment state post-`4b7f4804e`**: all 13 actively-tracked submodules ALIGNED at inner HEAD with zero DIVERGED gitlinks. Seven bulk-provider pointers advanced in this session cycle (well above round-3 cadence). KW-CV-001 watchpoint re-probed at every commit — still 0; peers continue `Migrate *.rs from ndarray to leto` subject phrasing, not `closeout`/`final`/`completion`/`close-batch`.
  - **Atlas-meta action posture**: round-4 captured all in-session churn. Awaiting peer's next kwavers/ritk commit; either KW-CV-001 fires for kwavers OR slice-7+ launches to re-open round-5 capture. Either path stays in observation mode; no source-tree work concrete to atlas-meta.

- **This codex session (2026-07-08, mid-session test/example validation sweep) collapsed to canonical L104** — the orphan duplicate of the user-directive sweep block at former L275-L281 + the prior stale ROUND-3 dedup claim in L283-tombstone are reconciled by the present chore: the canonical `### In-flight claims (per concurrent_agents)` L104 carries the full T1 evidence (ritk nextest 47/47; CFDrs 2177/2177+1335/1335 subsets; kwavers 1-site `plugin/mod.rs:204` test-mock slip); the L283 tombstone is updated below to reflect this collapse. Mid-session test/example issues resolved by **peer-owned** per-`concurrent_agents` disjoint-scope: the kwavers `Boundary<eunomia::Complex<f64>,3>` trait-rewire at `crates/kwavers-solver/src/plugin/mod.rs:182+204` and the `fn to_leto3` dead-code warning in `crates/kwavers-simulation/src/dispatch/elastic_pstd.rs:8` are peer-stream fixes; atlas-meta does not touch `repos/kwavers/crates/kwavers-solver/src/plugin/mod.rs` or any other peer-claimed source.

#### Historical closure templates — Atlas Batch #3 sub-batches #4–#6

> All three templates were consumed by RITK PR #42 and tombstoned by PR #43
> on 2026-07-18. They remain below only as design-history evidence; none is a
> standing reminder, prerequisite, or next-session instruction.

These templates preserve the original atomic commit shapes and prerequisites
from ADR 0012. They are historical evidence only; no roll-up surfacing or
future-session action remains.

- **Sub-batch #4 [patch] — Standing reminder**: `ritk-spatial rebind — drop burn::module::{Module, AutodiffModule} + burn::record::Record impls`. **Atomic inner commit shape**: a single inner-RITK commit that strips the four `burn::module::*` + `burn::record::Record` impls on `repos/ritk/crates/ritk-spatial/src/{vector,point,direction,spacing}.rs:7` and (conditionally) adds `impl<T: Scalar, B: ComputeBackend> coeus_nn::Record for *` ONLY IF the downstream PINN consumer code in `kwavers-solver/src/inverse/pinn/**` or `helios-imaging/**` requires it (cross-walk Batch #4 §Progress in `atlas/checklist.md` for the in-flight audit; otherwise sub-batch #4 is a strict-removal commit with no Atlas-side replacement per ADR 0012 §Decision §Sub-batch #4). **Standing pre-reqs**: (a) Batch #3 sub-batch #3 fully closed — i.e., the 7 per-crate queue `#3.a..#3.g` has landed (each with its own test-from-`burn_ndarray::NdArray<B>`-to-`AtlasImage<T: Scalar, B: ComputeBackend, D>` over `coeus_tensor::Tensor<T, MoiraiBackend>` port) and `xtask/burn_surface.allowlist` source-rows have been progressively decremented per per-crate closure; (b) the impact audit of `burn::module::{Module, AutodiffModule}` removal on `kwavers-solver` Batch #4 PINN code paths is completed and posted to `kwavers/gap_audit.md` (the auto-`ModuleMapper` / `GradientExtractor` / `GradientApplicator` pattern from the `coeus_nn::load_parameters` extension must already be in place, OR the per-PINN code-path-side adapter lives inline at the PINN consumer site, NOT on the spatial carriers); (c) cooldown — if any per-crate sub-batch in `#3.{b..g}` transitively touches `ritk-spatial`, it must be closed before `#4` lands to preserve the atomic-boundary invariant (no legacy Burn-keyed reference survives into the post-#4 tree). **Pre-flight gate per session**: `cargo check -p ritk-spatial --all-targets` + `cargo doc -p ritk-spatial --no-deps` warning-clean + `cargo clippy -p ritk-spatial --all-targets -- -D warnings`.

- **Sub-batch #5 [major] — Standing reminder (mandatory semver-checks pre-release gate)**: `RITK Burn Cargo dep strip + Image<B,D> re-export path`. **Atomic inner commit shape**: a single inner-RITK BREAKING CHANGE commit that (i) deletes `burn` + `burn-ndarray` from `repos/ritk/Cargo.toml:69-72`, `ritk-core/Cargo.toml:23-24` (dev-deps), `ritk-image/Cargo.toml:9-10`, `ritk-wgpu-compat/Cargo.toml:8`, and per-crate `burn` + `burn-ndarray` dev-dep cleanup from `crates/ritk-{filter,transform,interpolation,registration}/Cargo.toml:23,30`; (ii) switches the public re-export at `repos/ritk/crates/ritk-image/src/lib.rs:11` from `pub use types::Image;` to `pub use AtlasImage as Image;` (verify which `atlas/checklist.md` §Batch #3 §Plan step 1 prefers — alternative is `pub use native::Image;`); (iii) removes `apply_row_chunks<B: Backend>` from `repos/ritk/crates/ritk-wgpu-compat/src/lib.rs:40+` (no async replacement; docstring-only if a docstring is needed for archival context); (iv) updates all `Image<B, D>` references in source across the workspace (this is the [major] breaking event per RITK semver). **MANDATORY pre-release confirmation** (per ADR 0012 §Decision §Sub-batch #5 + the `versioning` section of `atlas/AGENTS.md`): `cargo semver-checks release -p ritk-core -p ritk-image -p ritk-spatial` MUST run pre-merge and MUST authoritative-classify the commit body as `[major]` (the table-row label `[major]` in `atlas/backlog.md` §Batch #3 sub-batches is provisional; `cargo-semver-checks` is the ground truth). **If `cargo-semver-checks` reports `[minor]` or `[patch]` instead, the sub-batch #5 commit message `[major]` annotation MUST be downgraded by the actual outcome** (an observable regression per `atlas/checklist.md` §Per-batch atomic commit + version bump rules). The CHANGELOG entry under `## [Unreleased]` uses `cargo-semver-checks`'s verdict, NOT the provisional table-row class label. **Standing pre-reqs**: (a) sub-batch #4 closed OR skipped (sub-batch #4 may be omitted if the kwavers Batch #4 PINN audit confirms no Atlas-side `coeus_nn::Record` replacement is required — the omit path is documented per ADR 0012 §Decision §Sub-batch #4); (b) kwavers Batch #4 (`burn::module::Module` → `coeus_nn::Module`) `burn.rs` + `burn_compat` facade deletions are LANDED on the `repos/kwavers` peer stream so the cross-crate risk #8 exposure is closed (cross-walk `atlas/gap_audit.md` surfacing risk #8 + the peer's `c6b845f81`-style "per prior direction not to build burn-compat shims" framing); (c) per upstream-consumer audit, no peer claim stream touches `repos/ritk/{Cargo.toml, src/lib.rs:11}` per `concurrent_agents` disjoint-scope rule (the absence can be verified by `git -C repos/ritk status --short` returning zero on the inner-RITK working tree prior to staging the sub-batch #5 commit). **Pre-flight gate per session**: `cargo semver-checks release -p ritk-core -p ritk-image -p ritk-spatial` (mandatory pre-release verdict — the only source of truth for the version-bump rule) + `cargo build -p ritk-core -p ritk-image -p ritk-spatial --release` + `cargo test --doc -p ritk-core -p ritk-image` + `cargo tree --workspace -i burn`, `-i burn-ndarray`, `-i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` ALL return zero.

- **Sub-batch #6 [patch] — Standing reminder (downstream of sub-batch #5)**: `xtask/burn_surface.allowlist contract reset + CI scan gates tighten`. Cross-link to ADR 0012 §Decision §Sub-batch #6: source entries are removed; the allowlist file becomes the post-migration SSOT and is archived or rewritten. CI scan gates tighten: new CI gate asserts zero `burn::tensor::Backend`-bound public symbols; new CI gate asserts `coeus_core::ComputeBackend` is the only atlas-side backend trait in the cross-crate re-export graph. CHANGELOG `[patch]` per RITK (CI-only). **Atomic inner commit shape**: a single inner-RITK CI-only commit that (i) regenerates `xtask/burn_surface.allowlist` content against the post-`#5 xtask/burn_surface_audit` regeneration (the contract-file becomes the post-migration SSOT — the pre-`#5` generated-from-`burn::` allowlist entries parcel to migration-done rows); (ii) adds a new CI scan gate that asserts zero `burn::tensor::Backend`-bound public symbols in the cross-crate re-export graph; (iii) adds a second CI scan gate asserting `coeus_core::ComputeBackend` is the only atlas-side backend trait in the cross-crate re-export graph (i.e., every public `B: Backend` constraint has been re-routed to `B: ComputeBackend` for atlas-side surface). Cross-link: README + the Atlas-meta CI pipeline (if it exists in CI providers); the new gates are authored in the atlas-meta peripheral repo (`repos/atlas`) which carries the meta-CI pipeline, NOT on the inner-RITK repo directly — the inner-RITK commit body references the atlas-meta commit SHA that introduces the gates. **Standing pre-reqs**: (a) sub-batch #5 MUST be RE-ENTERED first — the sub-batch #6 atomic commit's body references the sub-batch #5 inner SHA in its message ("Corresponding to ritk/atlas-migration-push/batch3 tag-advance inner SHA <sub-batch-#5-sha>" — the tag annotation body also updates at this point). The atomic-boundary discipline holds because sub-batch #5 closed + tag-advanced leaves the workspace clean of the Burn-keyed surface, making sub-batch #6 a pure-CI-tool change with no behavioural code surface; (b) `xtask/burn_surface_audit` runs against the post-sub-batch-`#5` `cargo tree -p ritk -i burn-ndarray` reset state and reports zero Burn-keyed source-files per crate (the sub-batch #6 commit body MUST include this audit's complete output as evidence); (c) the new CI scan gates themselves are exercised pre-commit by `bash xtask ci --strict-atlas-only --dry-run` + `bash xtask ci --strict-backend-trait --dry-run` (the dry-run output is captured in the commit body as evidence). **Pre-flight gate per session**: `xtask/burn_surface_audit` (regenerates the allowlist contract) + `bash xtask ci --strict-atlas-only --dry-run` + `bash xtask ci --strict-backend-trait --dry-run` all return their expected zero-output invariants.

### Cross-engineering verification — `hephaestus-cuda` eigen.rs Complex upload

The earlier `fb83d009` residual risk is stale in the checked-out `repos/hephaestus` `ks5-cholesky-panel` tree. Source inspection on 2026-07-06 shows `hephaestus-cuda/src/application/decomposition/eigen.rs` maps `leto_ops::eigenvalues(&view)` output into `num_complex::Complex<f32>` with `Complex::new(z.re, z.im)` before `device.upload(&e_host)`, while `hephaestus-core::ComputeDevice::upload<T: bytemuck::Pod>` remains the generic transfer seam. Focused compile evidence: `rustup run nightly cargo check -p hephaestus-cuda --features decomposition` completed successfully against local `leto`/`leto-ops` `0.36.0`. Evidence tier: compile/build verification plus source inspection; no runtime CUDA device execution was claimed.


---

## Out-of-scope (explicit)

- **`**Spec composition layers**` updated later (e.g. `cfd-validation`, testing frameworks)**: not part of this migration; filing as separate backlog if it's not in CFDrs's own backlog.
- **HELIOS/Python binding for kwavers**: Phase-3 rich-image scoping state; deferred-until `kwavers-python` intent-bledged beyond current net-style top-level.
- **GPU backend complete production rollout across ritk-model**: PPG-model is reserved-wave per `docs/audit/2026-07-02-hephaestus-gpu-substrate-audit.md` HIGH-sev list; out of scope until defect closure.

### Atlas-root working-tree dirty triage (2026-07-06)

The Atlas-root `D:/atlas` working tree carries 29 dirty files (19 tracked-modified + 10 untracked) outside the migration-push closure chain. The vast majority have been classified as real Atlas-meta PM artifacts and committed in five atomic batches on 2026-07-06 (see commit history since `2c38db42`). The remainder is explicitly recorded below as **out-of-scope for the Atlas-parent pointer-advance ritual** — they live in scopes the Atlas-parent cannot reach (submodule internals, foreign root-level scratch, or non-submodule external dirs) and require separate-flow cleanup that is staged outside this branch's claim scope.

#### A. Root-level scratch (retracted 2026-07-06)

Cleanup chore commit on Atlas-meta deleted `nul` (Windows-reserved-name artifact on disk; the on-disk deletion API was blocked by `PermissionError` on the basename collision — see commit body for blocked paths; defense-in-depth `.gitignore` prevents future reproductions from re-entering `git status --short`) + `script.py` (root-level Python scratch that pre-existed the cleanup and was absent pre-chore per `os.path.exists`; the `.gitignore` entry ensures future re-generation path-respecting deletion can apply). Both items are now `.gitignore`-d so future reproductions cannot re-enter the Atlas-root working tree.

#### B. External / non-ASCII-dir content (retracted 2026-07-06)

Cleanup chore commit deleted `repos/SynthSeg/` (standalone git clone of the SynpthSeg brain-segmentation research project — has its own `.git/`, NOT in `.gitmodules`; deletion via `shutil.rmtree` with `onerror` handler that chmods + retries after Windows pack-file collisions on `.git/objects/pack/*`) + `repos/report/` (non-ASCII-filename dir, deletion via `shutil.rmtree` succeeded directly). Both items are now `.gitignore`d. Note: the prior-analysis claim that `repos/SynthSeg/` had "no `.git` of its own" was a stale read; the on-disk state had its own `.git/` and required the onerror handler for clean removal.

#### C. Submodule-internal dirtiness (uncommitted in inner repos — out of Atlas-parent reach)

These show up in Atlas-root `git status` as `M repos/<name>` (parent-tree entry marked dirty because the inner submodule's tree contains modifications relative to the gitlink pinned here). They are **cleanable only by an inner-submodule commit + parent-tree gitlink advance**, NOT by Atlas-parent commit. Each row is the inner-dirty count + inner HEAD as of 2026-07-06. No reclaim from Atlas-meta; these belong to the claim streams holding the inner repos.

| Submodule | Inner dirty count | Inner HEAD | Inner branch / claim stream | Triage decision (2026-07-06, per ADR 0011 §Decision §Leg 3) | Atlas-meta artifact action |
|-----------|---:|------|------|--------------------------------|------------------------------|
| `apollo`         | 235 | `f1ddf7a`     | peer claim stream `codex/apollo-atlas-migration` (WIP) | **Path B — OOS-next-sprint**: 235-file pre-CR-5 surface; queued behind ADR 0010 `apollo/atlas-migration-push/batch5` reservation | stay in §C with Batch-#5 reservation cross-walk |
| `CFDrs`          | 79  | `d58d1fe3`    | peer claim stream on `codex/cfdrs-atlas-migration` after Batch #2 closure | **Path B — OOS-next-sprint**: Batch #2 remains closed at `d58d1fe3`, but current source dirtiness has reappeared after the closure push and belongs to the CFDrs inner-repo claim stream; do not retract this row from §C until the inner tree is clean again or a new CFDrs commit lands | stay in §C; keep Batch #2 closure cross-link, but current dirty-tree accounting is live |
| `coeus`          | 19  | `b2beec3`     | peer claim stream on `main` (source + docs; includes dtype, tensor, Python embedding, and parity-test files) | **Path B — OOS-next-sprint**: not a PM-only closure-tail; source files are dirty and must land inside the Coeus claim stream with Coeus package gates | stay in §C as peer-active; no Atlas-meta source reclaim |
| `eunomia`        | 7   | `57d7789`     | peer claim stream (CR-4 closed; CR-EUNOMIA-COMPLEX ⏳ `acos/asin/atan` PR-queue per ADR 0006; **eunomia-side retroactive-closed per ADR 0006 §Decision §1 Path B**) | **Path C retroactive-closed 2026-07-06** (ADR 0006 §Decision §1 Path B additive `ComplexField::zero()`/`::one()` defaults landed at eunomia HEAD `57d7789`); 7-dirty reclassified as peer's UNRELATED `acos`/`asin`/`atan` PR-queue (per `## In-flight claims` Neighbor claim streams). Cross-walk §C eunomia reclassification bullet below + `D:/atlas/docs/coordination/2026-07-06-eunomia-csr-scalar-phantom-blocker.md` + ADR 0008 §Decision §0 reframed. | retract from §C on next §-triage pass; the prior `Path B — OOS-next-sprint` classification was based on a stale ADR 0008 §0 Variant A / unseal `NumericElement` framing that ADR 0006 explicitly REJECTED |
| `gaia`           | 5   | `8f4a862da`     | peer claim stream `refactor/migrate-to-leto-geometry` | **Path B — OOS-next-sprint**: source and benchmark files are dirty (`src/application/csg/arrangement/classify.rs`, `benches/csg_performance.rs`), so the PM files cannot be committed as a source-disjoint Atlas closeout | stay in §C as peer-active; no split closeout |
| `hermes`         | 46  | `1b5392a`     | peer claim stream | **Path B — OOS-next-sprint**: 46-file scattered across `hermes-simd-*` crates + ADR footer updates; moderate-size, multi-domain peer-active | stay in §C; peer-active |
| `kwavers`        | 27  | `400c32624`   | peer claim stream `codex/kwavers-core-moirai-parallel` ACTIVE | **Path B — OOS-next-sprint**: dirty count drained from 132 to 27; remaining Batch #1/#4 surface still belongs to the kwavers inner-repo claim stream and stays behind ADR 0010 `kwavers/atlas-migration-push/batch1` reservation | stay in §C; cross-walk ADR 0010 reservation; drain-counter annotation now `-575` from the original 602-file capture |
| `leto`           | 14  | `626ebf538`     | peer claim stream `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile | **Path B — OOS-next-sprint**: 14-file ACTIVE peer stream (disjoint from CR-4 leto side per `concurrent_agents`) | stay in §C; disjoint with CR-4 leto side |
| `melinoe`        | 13  | `7ec0a44`     | peer claim stream | **Path B — OOS-next-sprint**: 13-file `crates/halo/` + 4 src sync; CR-1 consumer (brand doctrine holder for `apollo-ghostcell` deletion); cross-crate work with apollo CR-5 reservation | stay in §C; CR-1 cross-link |
| `moirai`         | 26  | `9b7881f`     | historical peer claim stream `refactor/remove-dead-subsystems` | **Superseded:** CR-2 closed 2026-07-18 with zero `#[global_allocator]` sites across the three library crates | historical snapshot only |
| `ritk`           | 0   | `8f8360ff`    | local follow-up committed after the clean nine-commit Batch #3 migration sequence, then advanced by Atlas-parent pointer commits | **Path C closed for risk #1 and Helios DICOM ownership**: inner commit `65a1a0fd` removes stale Burn `wgpu` default; inner commit `d7a940b5` adds the Batch #3 sub-batch #1 Atlas-typed parallel trait surface; inner commit `8f8360ff` adds typed DICOM attribute reads for downstream imaging consumers | pointer advanced by this Helios/RITK DICOM ownership commit; keep broader Batch #3 closure separate until package gates are current |
| **Σ** | **471 inner files** (fresh `git status --short` sweep; Helios and RITK now clean) | — | — | **2 retroactive/closed rows + 0 source-disjoint partial closeouts + 9 stay-OOS-next-sprint rows** | **No source-disjoint Atlas-meta closeout remains; next source work belongs inside the active inner-repo claim streams** |

#### D. Helios/RITK DICOM ownership cleanup (closed 2026-07-06)

Commit `c5f2a84e` closed the six-file Helios direct dependency slice under `repos/helios/**`: H-062 removed the unused direct `num-traits` workspace edge, H-061 removed Helios' unused aggregate dicom-rs `ndarray` feature edge while leaving pixel decoding owned by `ritk-dicom`, and the local Melinoe patch now lets patched Gaia resolve its `melinoe` 0.8.0 edge during Helios validation. Follow-up RITK commit `8f8360ff` closes the remaining production DICOM boundary drift by moving common DICOM image tag vocabulary and typed parsed-object attribute reads into `ritk-dicom`; Helios now consumes that API for parsing, typed attributes, transfer-syntax lookup, and pixel decode. Current Atlas-root status is expected to have no committed `repos/helios/**` direct-file dirtiness after this pointer-advance commit; the remaining imaging boundary is H-063 (`helios-imaging` audit for generic toolkit operations that belong in RITK).

#### E. Remaining future-correction hooks (post-2026-07-06)

§A and §B retractable future-correct clauses resolved in the 2026-07-06 cleanup chore commit on Atlas-meta (the 4-pattern `.gitignore` append + the on-disk SynthSeg + report deletions + the 4-pattern future-proofing). §C is partially-triage-classified per ADR 0011 §Decision §Leg 3 OOS-record cadence (sub-routine "Initial record" + "Post-resolution §-E update when stay-OOS-next-sprint"). Total submodule-internal dirty now stands at 471 inner files after the Helios direct-file closure (`c5f2a84e`), RITK Batch #3 sub-batch #1 pointer advance (`61931faf` to `d7a940b5`), Helios/RITK DICOM ownership pointer advance (`8f8360ff`), and the refreshed peer-WIP counts. This triage leaves three open forward-looking hooks:

- **§C retroactive-closings (Path C rows)**: 2026-07-06 triage retracted the zero-dirty `hephaestus`, `mnemosyne`, and `themis` rows from §C because they are no longer submodule-internal dirtiness. `CFDrs` was not retracted: re-verification shows 79 inner dirty paths on `codex/cfdrs-atlas-migration`, so the Batch #2 closure remains recorded while the current dirty tree stays tracked as a live CFDrs claim stream. The remaining Path C row is `eunomia`, which is covered by the separate reclassification bullet below.

- **§C partial-closeable queue (Path A candidates for next claim stream)**: empty after re-verification. `coeus` and `gaia` both contain source/benchmark dirtiness, so their PM files cannot be split into source-disjoint commits without hiding peer-active implementation context. `ritk` left this queue after inner commit `65a1a0fd`. Recommended pre-commit gate for future claim streams: `git -C repos/<X> status --short` once before the inner commit, to confirm no peer-stream claim landed in the interim.

- **§C stay-OOS-next-sprint (Path B rows)**: 9 submodules post-2026-07-06 refresh — `apollo` (235, Batch #5 reservation `apollo/atlas-migration-push/batch5` per ADR 0010; pre-CR-5 surface), `CFDrs` (79, Batch #2 closure remains closed at `d58d1fe3`, but current dirty paths belong to the live CFDrs inner-repo stream), `coeus` (19, source + docs peer stream), `gaia` (5, source/bench + PM peer stream), `hermes` (46, peer-active scattered), `kwavers` (27, Batch #1 + Batch #4 + Phase-1B reservations), `leto` (14, ACTIVE peer stream `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile), `melinoe` (13, CR-1 consumer cross-crate with apollo Batch #5; brand doctrine holder), `moirai` (26, Batch #6 reservation `cfd-core+ritk-core+moirai/atlas-migration-push/batch6` per ADR 0010; `refactor/remove-dead-subsystems` ACTIVE). Removed: `eunomia` (retroactive-closed; 7 dirty files are unrelated `acos`/`asin`/`atan` PR-queue), `ritk` (clean at `8f8360ff` after the DICOM ownership pointer advance), and `helios` (direct dependency plus DICOM ownership slices closed; H-063 filed for future `helios-imaging` audit). No Atlas-meta reclaim per disjoint-scope rule (ADR 0011 §Decision §Leg 2). Each row stays in §C until its owning claim stream emits a pointer-advance to Atlas-parent.

- **§C eunomia row reclassification (post-2026-07-06 phantom-blocker discovery)**: the §C `eunomia` row above has been reclassified from `Path B — OOS-next-sprint` to `Path C retroactive-closed (eunomia-side per ADR 0006 §Decision §1 / Path B additive `ComplexField::zero()`/`::one()` defaults landed at HEAD `57d7789`)`. The 7-dirty is now re-attributed to the peer's UNRELATED active WIP stream (`acos`/`asin`/`atan` PR-queue per § In-flight claims Neighbor claim streams section) — OUT of §C scope on the next §-triage pass per ADR 0011 §Decision §Leg 3 \"Resolution branch\". The residual Phase-1B is kwavers-side per ADR 0008 §Decision §0 (reframed per the discovery); cross-walk `D:/atlas/docs/coordination/2026-07-06-eunomia-csr-scalar-phantom-blocker.md` for the full verification matrix.

- **§D (Helios/RITK DICOM ownership closure)**: closed by `c5f2a84e` plus RITK `8f8360ff` and this Helios consumer reroute; current Atlas-root status has no committed `repos/helios/**` direct-file dirtiness after the pointer-advance commit, and H-063 tracks the remaining `helios-imaging` generic-toolkit audit.

- **`nul`** (whose on-disk deletion API was blocked by Windows-reserved-device-name PermissionError on this build): the `.gitignore` defense in this chore commit prevents future `nul` reproductions from re-entering `git status --others`. The on-disk file may still surface via `dir` from bash contexts but is gitignored; admin `cmd /c del /F /Q nul` or Windows-reboot may be required for actual on-disk removal. Filed for the next codex-session restart-handler.


### RN-CC-05 (transitive parent-SHA chain breach detection + audit-discipline establishment)

Filed by `chore(atlas): Roll-up review-nit RN-CC-05 -- transitive parent-SHA chain breach detection` (post-`536366e`). Retroactively addresses code-reviewer-minimax-m3 NIT surfaced in the post-`536366e` cycle: commits `93a0723177` + `a96d46d7294` declared the RN-CC-04 discipline but inline-cited the parent rather than carrying a `Parent-SHA:` line-block at the top of body. Per NO-AMEND, retroactive body repair is forbidden; the breach is disclosed across 4 docs files + recorded in the RN-CC-05 commit body. Parent-SHA: forward-propagation audit discipline: `rg -F "Parent-SHA:" gap_audit.md backlog.md checklist.md docs/coordination/` yields >=2 line-hits; `git log --grep "Parent-SHA:" --oneline` yields >=2 entries. Self-discipline demonstration: `74df54d4f963b96d1b642ce89e77c9b019ad3de7` + `74df54d4f` + `536366e` + this RN-CC-05 chore carry line blocks at top of body; `93a0723177` + `a96d46d7294` need forward-session transparency (this row).

## Review nit rolling list (forward-looking improvement tracking, 2026-07-08)

> Persistent review-improvement tracking items surfaced by the
> post-`91896c477` code-reviewer pass on the Atlas architectural
> directive framing chore. Each nit is annotated: ID, scope,
> severity, source-chore, fix status, suggested follow-up.
> Future chore-cycles reference this list when templating
> `docs(atlas):` commits so the same drifts don't recur.

| ID | Nit | Severity | Source chore | Status | Follow-up |
| --- | --- | --- | --- | --- | --- |
| **RN-01** | CR-2 (open; Batch #6) citation error -- mnemosyne row cited "per CR-2 (open; Batch #6)" but CR-2 is **OPEN** per Surfacing risks row 1.2 (Batch #6 reserved), not CLOSED. | factual | `91896c477` | **FIXED in `b29cfa24b`** (mnemosyne row changed to "per CR-2 target axiom [open; Batch #6]") | file-wide rg `per CR-2 (open; Batch #6)` on subsequent docs-only chores; extend fix to any other inverted citations |
| **RN-02** | 11+3 stack split -- the monolithic `### Stack (13 atlas crates)` table conflated 11 providers with 3 consumers in one 14-row table. | structural | `91896c477` | **FIXED in `b29cfa24b`** (split into `### Provider stack (11 atlas crates)` + `### Consumer migration targets (3 simulation suites)`) | template future `Atlas-stack` table sections with the provider/consumer split pattern from the start; split mnemosyne+themis row when allocator-pair semantic is involved |
| **RN-03** | Gitlink SHA truncation -- table used 7-char truncated SHAs (`98a02b6...`, `37ff12d5...`, etc.) which break grep-ability and don't match the 40-char convention used elsewhere in `gap_audit.md`. | presentational | `91896c477` | **FIXED in `b29cfa24b`** (all 14 table SHAs now full 40-char live from `git ls-files --stage`) | prefer full 40-char SHA in all `docs(atlas):` table cells; only allow truncation when the SHA is genuinely abbreviated (e.g., an inner HEAD short-SHA in narrative prose) |
| **RN-04** | FRONT-MATTER sync -- `gap_audit.md` lines 1-11 blockquote enumerated 4 record-types but the new `## Atlas architectural directive` section added a 5th without updating the enumeration. | presentational | `91896c477` | **FIXED in `b29cfa24b`** (item 5 appended to front-matter blockquote: `Atlas architectural directive (2026-07-08); consolidator framing -- stack table, migration targets, design principles, constraints, bulk-migration priority order`) | when adding a new top-level section to `gap_audit.md`, also update lines 1-11 blockquote enumeration; consider automating via a pre-commit check |

**File-wide open follow-ups surfaced by the post-`b29cfa24b` review**:

- **CR-2 file-wide citation scope (RN-01 scope extension)**: a file-wide
  `rg -n 'per CR-2 (open; Batch #6)' gap_audit.md` post-patch may surface
  additional inverted citations outside the table row that was fixed
  in RN-01 (e.g., CR-class status cell, Surfacing risks row 1.2
  narrative, cross-cutting notes). **Status**: not yet verified
  post-patch; a follow-up patch chore should run the rg + extend the
  fix to any other hits.
- **Subsection naming collision (RN-02 cosmetic extension)**: the new
  `### Consumer migration targets (3 simulation suites)` (table)
  sits adjacent to the existing `### Migration consumer targets (3 in
  flight)` (prose). The two names are lexically adjacent on
  "consumer migration targets" -- a grep footgun. **Status**: not
  yet renamed; recommend renaming the new table to `### Consumer
  simulation suites (3 in flight)` for disjoint-name grep-ability.
- **Prose subsection inner-HEAD SHA uniformity (RN-03 scope
  extension)**: the preserved prose subsection (`### Migration
  consumer targets (3 in flight)`) still uses 9-char short-SHAs
  (`inner HEAD 05500930c`, `702e4f125`, `d58d1fe3`, etc.); the new
  directive table uses 40-char SHAs. **Status**: deliberate scope
  choice -- not yet upgraded for visual consistency. Either
  upgrade in a follow-up patch, or document the inconsistency
  explicitly in body-scratch as a preservation choice.
- **Body-scratch subject parent-SHA anchor (RN-04 audit-discipline
  extension)**: subject of `b29cfa24b` is `Patch 4 review nits on
  directive chore (...)` and doesn't grep-match `91896c477` (parent
  SHA). **Status**: noted as a `concurrent_agents` precedent for
  future subject-pattern discipline; recommend appending `(parent
  <SHORT-SHA>)` to chore subject or putting parent-SHA on
  body-scratch line 1.

**Audit-lifecycle note**: this rolling list persists until (a) a
follow-up chore closes all 4 RN items above (RN-01..RN-04 already
FIXED in `b29cfa24b`; 4 follow-up extension nits remain open), or
(b) a future chore re-classifies any item as RESOLVED-by-design
via explicit `docs(atlas): Mark RN-XX as RESOLVED-by-design (...)`
commit. Re-probe cadence: per `docs(atlas):` chore landing that
touches `gap_audit.md` PM surface.

**Cross-link**: see `gap_audit.md` `## Atlas architectural directive
(2026-07-08)` (line 12) for the source-chore context + `## Surfacing
risks` for the open follow-ups' parent audit-class entries. See
`D:/atlas/gap_audit.md` `L339 PRESERVED` parity-row in the
`### Anchor-evolution history` section for the prior anchor-iteration
history convention (anchor-tail intent-over-version naming).


---

- **This codex session (2026-07-08, Bulk-provider-surface round-1 + round-2 + round-3)**: three sequential bulk-advance blocks landed (round-1 `2e1c4f20d`→`274a6a961`→`a12d1dd77` for apollo/coeus/hermes/melinoe/ritk + themis pointer refreshes; round-2 `5d3395e95` + `715cff24e` + `02da06611`→`ab71f08ad`→`36acbbca9` for hermes-r2/coeus/cascade + multi-PM-reconciliations + `.gitignore hardening); round-3 `ad6cf57d4`→`1828ea14a`→`852de7129`→`769b70a67`→`1fe3c0e56` for apollo/eunomia/hermes/leto/mnemosyne). See `gap_audit.md` row 13 for the per-submodule advance record + provenance triples + branch-context notes (especially hermes on `rescue/detached-simd-numa-work` divergent 17 commits ahead of `origin/main`, NOT peer-WIP at the parent gitlink level; mnemosyne sjump `482670d` → `98a02b6` reflects the Miri alloc/free HIGH-PRIORITY finding at `eff(backend)` + `fix(backend)` + `docs(gap_audit)` chain). **Net alignment state post-`1fe3c0e56`**: all 12 actively-tracked submodules (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, kwavers) ALIGNED at inner HEAD with zero DIVERGED gitlinks — the first all-aligned state since the `e0bf55684` cross-tree reclamation audit. **ritk-python test suite (47/47)** compiled+passed at committed inner HEAD `1f49278c` (value-semantic asserts — see `gap_audit.md` row 154 bulk-advance unblock evidence). **KW-CV-001 watchpoint re-affirmed ACTIVE** at inner HEAD `35ee01076`: trigger `(cd /d/atlas/repos/kwavers && git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l)` returns 0; peer continues slice-by-slice Batch #1 + Batch #4 work without explicit closeout commit. **Atlanta-meta path forward**: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit (per `concurrent_agents` disjoint-scope rule); the round-3 block leaves kwavers at the peer-tracked HEAD `35ee01076` (atlas-meta gitlink already aligned, not divergent, just not watching for closure-style advances here — the KW-CV-001 watchpoint owns that path). **Branch context**: this turn's round-3 work landed under `codex/kwavers-atlas-integration`; `36acbbca9` `.gitignore` hardening prevents transient root scratch artifacts from re-entering `git status --short` (no body-scratch file was created for any of the 5 round-3 chore commits, per the user's signal-change-in-the-tree batch ceremony convention from ADR 0010 §Per-batch name pattern; each commit body authored inline via subject + body `-m` pairs + a final `-m` provenance-triple block citing row 11 dynamic-SHA extraction). **Cross-references**: `gap_audit.md` row 13 (per-submodule advance record with prior-SHA + derived-full-SHA + inner-chore-subject for each of the 5 round-3 modules); `checklist.md` §Next micro-sprint for the round-3 line-item summary. **Residual risks** (tracked in `gap_audit.md` row 6 row-268–270 kwavers sub-bullets): kwavers 267 dirty files at inner HEAD `35ee01076` is peer-WIP, not reclaimable from atlas-meta; kwavers Batch #1 closure condition (zero `par_for_each` source sites) is NOT yet met (41 sites across 15 files per `gap_audit.md` line-93); kwavers Batch #4 closeout condition (zero `burn::` source hits + zero `crates/kwavers-solver/Cargo.toml:42` burn dev-deps + `burn.rs`/`burn_compat` deletion) WAS met at `05500930c` per the line-92 sub-bullet (file deletion + manifest strip landed on the peer stream). The next bulk-advance round (round-4) is contingent on either inner HEAD churn (peer-WIP-after-push divergence) OR KW-CV-001 firing for kwavers.
- **This codex session (2026-07-06, Helios closure)**: `c5f2a84e` closed the direct Helios H-061/H-062 dependency slice by removing the unused `num-traits` workspace edge, removing the aggregate dicom-rs `ndarray` feature edge, adding the local Melinoe patch required by patched Gaia's `melinoe` 0.8.0 edge, and syncing Helios PM evidence. Concurrent peer commit `61931faf` then landed the RITK Batch #3 sub-batch #1 Atlas-parent pointer advance; preserve that pointer state.
- **This codex session (2026-07-06, Helios/RITK DICOM ownership)**: RITK inner commit `8f8360ff` adds `ritk-dicom::{DicomTag, tags, DicomAttributeRead}` so downstream DICOM geometry/modality-LUT attribute reads are RITK-owned. Helios H-061 now routes production DICOM parsing, typed attributes, transfer-syntax lookup, and pixel decode through `ritk-dicom`; dicom-rs remains direct only as a dev-dependency for synthetic Part 10 fixture generation. Helios H-063 is filed for the remaining `helios-imaging` audit: generic medical-image I/O/registration/toolkit operations move upstream to RITK; radiation-domain MVCT projection/reconstruction kernels stay in Helios.
- **This codex session (2026-07-07, RITK DEP-497-01 dead-dep strip)**: `repos/ritk` commits `7a66d1ee` (strip unused production `burn` dep from 17 leaf crates: `ritk-{cli,core,filter,io,jpeg,metaimage,mgh,minc,model,nifti,nrrd,png,registration,segmentation,snap,statistics,tiff,transform,vtk}`; `burn-ndarray` dev-dep retained where sub-batch #3 per-crate test ports are still open) + `00d57005` (checklist sync), pushed to `origin/main`. Distinct from Batch #3 sub-batch #5 (`[major]` full Burn Cargo strip + `Image<B,D>` re-export) per ADR 0012 — this is a non-breaking dead-edge removal, no version bump. Verified: `cargo nextest run` across the 19 touched crates 4258/4258 green, `cargo clippy --workspace --all-targets -D warnings` clean, `cargo fmt --check` clean for touched crates, `cargo doc --no-deps` no new warnings. Fixed an incidental `clippy::doc_lazy_continuation` false-positive in `ritk-model/src/ssmmorph/encoder/tests.rs`. Residual risks filed in `repos/ritk/checklist.md` (2 pre-existing broken intra-doc links in `ritk-filter`; a full-workspace-nextest-only timeout in `ritk-snap::pacs_ops` reproduced only under full-parallel resource contention, isolated run passes in 2.1s — not a hang). Atlas-meta `repos/ritk` gitlink advanced to `00d57005` via the dynamic-SHA-extraction convention (gap_audit.md row 11).
- **`repos/kwavers` `codex/kwavers-core-moirai-parallel` — peer ryancinsight ACTIVE** (inner HEAD `05500930c` 2026-07-07 19:11, `[ahead 0, behind 0]` of `origin/codex/kwavers-core-moirai-parallel` per inner `git rev-list --left-right --count`; atlas-meta `HEAD:repos/kwavers` gitlink pinned at `7235d464afb04dfec62dee1cd8e6e8d660b54250` lagging inner HEAD by 37 commits). State at inner HEAD `05500930c` per T1 verification: **Batch #4 (kwavers-solver PINN Burn → Coeus) source-residual is now ZERO** — canonical inner chore `8b128c478` "Remove dead burn compatibility shim and drop burn dependency" + slice 3+ commits drained the residual; `crates/kwavers-solver/src/burn.rs` + `burn_compat` module ABSENT; `rg -n '\bburn\b' -g '*.toml' .` zero hits in `crates/kwavers-solver/Cargo.toml` + root `Cargo.toml`; `rg -l '\bburn::' crates --type rust` zero hits across the kwavers source tree (was 186 line-hits / 80 files at `b605e2e74`, full clean at `05500930c`). **Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai)**: `crates/kwavers-{solver,physics}/Cargo.toml:{24,20}` now read `ndarray = { version = "0.16", features = ["serde"] }` (per peer `702e4f125` "drop unused ndarray/rayon feature from kwavers manifests"; the `rayon` feature strip is landed, contradicting the prior stale paragraph that read `features = ["rayon", "serde"]`); residual is now **41 `.par_for_each()` sites across 15 files** in `crates/kwavers-solver/src` (down from 84 sites / 28 files at `b605e2e74`, −51%) — concentration in `forward/{elastic/swe/{integration/integrator/mod,stress/divergence}, nonlinear/{kuznetsov/{diffusion,nonlinear,numerical,operator_splitting/mod,solver/{model_impl,rhs},spectral,workspace}, westervelt_spectral/spectral}, pstd/extensions/{elastic,elastic_orchestrator/pml/mod}, multiphysics/fluid_structure/{interface,solver/struct_impl}}`. Closeout state: no formal `closeout` / `final` / `completion` commit in the last 30 inner commits — peer lands Batch #4 + Batch #1 slice-by-slice without explicit closure commits. **Atlas-meta continues to defer parent-side pointer advance** for `repos/kwavers` until a kwavers-side final closeout commit lands (per `concurrent_agents` disjoint-scope rule). `burn.rs` + `burn_compat` facade deletion + Cargo.toml strip are LANDED on the inner peer stream (lifting the surrogate pre-condition cited in sub-batch #5 standing reminder per `docs/adr/0012-ritk-burn-trait-rebind.md`). See `gap_audit.md` row 6 kwavers sub-bullets L268-L270 for the kwavers-side reconciliation record.
- Neighbor claim streams to honor (disjoint from kwavers Batch #1, also DO NOT touch): `repos/moirai` `refactor/remove-dead-subsystems` (26 dirty paths — moirai source forbidden); `repos/leto` `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile (14 dirty paths — leto source forbidden); `repos/coeus` `main` (19 dirty paths); `repos/eunomia` `main` (`acos`/`asin`/`atan` peer queue, 7 dirty paths); `repos/apollo` (235), `repos/CFDrs` (79), `repos/gaia` (5), `repos/hermes` (46), and `repos/melinoe` (13) carry in-flight peer claims. `repos/helios`, `repos/ritk`, `repos/hephaestus`, `repos/mnemosyne`, and `repos/themis` are clean of inner dirty paths after the Helios/RITK DICOM ownership closure and prior pointer-sync commits.
- The moirai-parallel API surface for kwavers Batch #1 already exists: `for_each_chunk_pair_mut_enumerated_with`, `for_each_chunk_triple_mut_enumerated_with`, `for_each_chunk_quad_mut_enumerated_with`, `enumerate_mut_with`, `for_each_index_with` (moirai-parallel `src/ops.rs:281,335,408,125,155`). No moirai source change is required for Batch #1 closure; the consumer-side helpers in `crates/kwavers-physics/src/parallel.rs` already cover 1-mut + N-imm and 2-mut + N-imm arities, with 3-mut + N-imm and 4-mut + N-imm indexed zips (visible in `kwavers-solver/src/forward/elastic/swe/{integration/integrator/mod.rs,stress/divergence.rs}` and `forward/pstd/extensions/elastic.rs` and `forward/pstd/extensions/elastic_orchestrator/split_field_step/{stress,velocity,mod}.rs`) as the remaining helper-coverage gap.
- **This codex session (2026-07-09, Bulk-migration #2 E0369/E0599 closure-front triage in `kwavers-math`)**: dry-run enumeration via `rg '::ones\([^)]*\)\s*\*' --type rust` + `rg '\.view\(\)' --type rust` against `crates/kwavers-math/src/**` returns **0 `::ones(...) * scalar` sites (E0369 front fully drained, idiom-set closure confirmed)** and **151 prefix-form `.view()` call sites across 27 distinct files (138 bare `.view()` + 13 `.view_mut()`; total per row 14.5 SSOT in `gap_audit.md`; E0599 front, separate closure track)**. **Idiom-set triage conclusion**: the 3-item idiom list recorded in `gap_audit.md` `### Bulk-migration priority #2 routing lesson (2026-07-09)` — `array.iter_mut().for_each(|v| *v *= scalar)`, `as_slice_memory_order_mut()`, and the project-native `scale_array` helper — IS operationally complete for the E0369 front as of the prior-session proof-of-pattern work (`avx2.rs:46,56` + `dispatcher.rs:139,151` closed 4 of 4 E0369 sites; cargo check error count 128 → 124). **The `.view()` E0599 sites are a SEPARATE closure-front** (most call sites are `.view()` / `.view_mut()` invocations on ndarray `Array3`/`Array4`, requiring explicit error propagation rewrites + trait-bound refactor of `Boundary<_>` carrier), and **are NOT covered by the E0369 3-item idiom set**. Per the user’s “if new patterns emerge, file a follow-up docs update rather than diverge from the lesson” guidance, the 3-item list is NOT expanded in this turn — the E0599 front stays tracked here as a transient atlas-meta carryover with the 138/27 enumeration, awaiting either peer-side Bulk-#2 phase work or future-session idiom-set expansion posture.


- **[SUPERSEDED 2026-07-09 by ADR 0013 `## Supersedes` field]** the prior partial-closure-mark was 2026-07-08; superseded; see D:/atlas/docs/adr/0013-kwavers-batch1-source-side-closure.md for the full Batch #1 source-side closure mark.
- **slice 1 partial-closure-mark 2026-07-08 — kwavers Batch #1 source-side migration slice 1 PARTIAL CLOSURE (2/41 sites, 1/15 files)**: per the peer's `5cd8c708` chore (`refactor(kwavers-solver): Migrate struct_impl.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 1)`, on `codex/kwavers-core-moirai-parallel` atop parent `ccc6bbf9`): 2 of the 41 source-side `.par_for_each()` sites have been migrated. The 2 sites live in `crates/kwavers-solver/src/multiphysics/fluid_structure/solver/struct_impl.rs` (3D `Array3<f64>` element-wise relaxation on `p_fluid_ghost` + `p_fluid_ghost_prev`; plus a 1D sub-view relaxation on `t_solid_ghost` + `t_solid_ghost_prev`). Migration dispatch: idiomatic `moirai_parallel::ParallelSliceMut::par_mut().enumerate(closure)` trait form (auto-Adaptive policy; no `ExecutionPolicy` generic needed); cargo-check pre-validate clean at inner HEAD `5cd8c708`. **KW-CV-001 watchpoint state**: remains ACTIVE — the closure-style trigger (`closeout|final|completion|close-batch` substring grep on the last 30 kwavers commits) is still 0; per the `concurrent_agents` disjoint-scope rule, atlas-meta is *observing* (not advancing) the peer's slice-by-slice progress without re-emitting the prior retracted full-closure mark. The remaining 39/41 sites / 14/15 files will be tracked via per-slice partial-closure marks (this entry is the first such mark) until the source-side count actually drops to zero, at which point the full closure-mark can be reasserted. **Atlas-meta path forward**: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit; do NOT bump the kwavers gitlink from the current `35ee01076` even as subsequent Batch #1 slices land on the peer stream, per the watchpoint's no-advance-without-closeout policy. **Note (data-quality, post-e73d524 dedup)**: the round-3 codex-session block was historically duplicated at L87+L90 (pre-chore-cycle stale snapshot); de-duplicated in chore-commit `e73d5241f` via structural-cleanup; see the OBSERVED 2026-07-09 tombstone (post-cut at L283) for the audit trail. The partial-closure mark is appended at end-of-file for grep-ability + future-automation reliability.


- **This codex session (2026-07-08, Bulk-provider-surface round-4 — post-OOB `6902d2e92` re-probe)**: 7 atomic chore captures in this turn. The OOB consolidation commit `6902d2e92` ("chore(atlas): Advance repos/hephaestus pointer to 240b260 (CU-P6/CU-M3)") absorbed my staged round-4 reset state, capturing `hermes` `5ad1b58 → c7b17b02` + `leto` `a9572da → 86d366bc` (batched LU / CSC sparse format / CG/GMRES iterative solvers — unblocks kwavers-solver Bulk-solver migration closure target) bundled into a single `e3223094a`. The remaining per-crate captures split into one-atomic-chore-per-crate for cleanliness:
  - `6a598da91` kwavers `35ee01076 → 89117870` (inner `Migrate kwavers Complex/ndarray types to eunomia/leto atlas crates` — Phase-3 closure of Complex<f32>/f64, ndarray Array, coefficient paths onto eunomia+leto substrates; replaces nalgebra/ndarray/numeric-complex stack in kwavers-core domain)
  - `0e34ae082` coeus `e36f95f → ec69a6a` (inner `fix(coeus-dist): close TOCTOU race in TCP test port allocation` + co-emitted `342f38d` MS-406/407 reconciliation; TOCTOU between bind and listen eliminated in coeus-distributed harness)
  - `045291499` ritk `1f49278c → e75d8748` (inner `Add Module/AutodiffModule impls for DisplacementField and DisplacementFieldTransform` — DIRECTLY resolves the displacement_registration_test failure tracked in row 6; Sub-batch #5 RITK-spatial-rebind closure per ADR 0012)
  - `4a4cf928a` coeus `ec69a6a → 006f2a7` (inner `feat(coeus-nn): add MaxPool3d/AvgPool3d benchmark rows (G-043)` — criterion bench registry extension for 3D pooling kernels)
  - `4b7f4804e` kwavers `89117870 → 09c645f30` (inner `Migrate kwavers-core/source/signal/grid/field from ndarray to leto` — Phase-4 closure of kwavers-core domain crates source/signal/grid/field off ndarray onto leto's NDArray substrate; follow-on to `89117870`)
  - **Net alignment state post-`4b7f4804e`**: all 13 actively-tracked submodules ALIGNED at inner HEAD with zero DIVERGED gitlinks. Seven bulk-provider pointers advanced in this session cycle (well above round-3 cadence). KW-CV-001 watchpoint re-probed at every commit — still 0; peers continue `Migrate *.rs from ndarray to leto` subject phrasing, not `closeout`/`final`/`completion`/`close-batch`.
  - **Atlas-meta action posture**: round-4 captured all in-session churn. Awaiting peer's next kwavers/ritk commit; either KW-CV-001 fires for kwavers OR slice-7+ launches to re-open round-5 capture. Either path stays in observation mode; no source-tree work concrete to atlas-meta.

- **This codex session (2026-07-08, mid-session test/example validation sweep)**: user directive "cleanup and resolution of all test and example issues/errors" triggered a fresh sweep across consumer-side trees at the just-advanced inner HEADs. T1 evidence:
  - **ritk** at inner HEAD `529d6651`: `cargo nextest run -p ritk-python --lib` 47/47 PASS (value-semantic asserts verified — `mi_normalized_identical_is_one`, `mi_rejects_shape_mismatch`, `test_validate_percentiles_descending_elements_returns_error`, `test_validate_range_inverted_bounds_returns_error`).
  - **CFDrs** at inner HEAD `72275347fb71`: `cargo check --workspace --all-targets` PASS (no warnings); `cargo nextest run --workspace --lib` 2177/2177 PASS (1 skipped, 0 failed, 1 slow at 28.1s — within CFDrs's 30s terminate budget).
  - **CFDrs subset** `cargo nextest run -p cfd-math -p cfd-1d -p cfd-2d --lib`: 1335/1335 PASS (1 skipped, 24.9s execution).
  - **kwavers** at inner HEAD `ccc6bbf9e6` (`Workspace-wide ndarray↔leto boundary fixes; cargo check --workspace passes`): `cargo check -p kwavers-solver --workspace` PASS; `cargo check --workspace` PASS with 1 dead-code warning (`fn to_leto3` unused in `crates/kwavers-simulation/src/dispatch/elastic_pstd.rs:8:4`); **`cargo nextest run --workspace --lib` FAILS at compile** with 1 site: `crates/kwavers-solver/src/plugin/mod.rs:204:21` — the test-mock `NullBoundary::apply_acoustic_freq` reads `_field: &mut Array3<kwavers_math::fft::Complex64>` (resolving via in-scope `use ndarray::Array3;` at line 182, which shadows the workspace's `leto::Array3` re-binding); the `Boundary` trait now declares `&mut leto::Array<eunomia::Complex<f64>, VecStorage<eunomia::Complex<f64>>, 3>`. **Disjoint-scope peer-owned per `concurrent_agents`**: atlas-meta records surface + line; the inner peer stream owns the 2-line edit (`use ndarray::Array3;` → `use leto::Array3;` at L182 + parameter signature updates at L204). Filed at `gap_audit.md` row 14.5.
  - **Note**: a 2nd `kwavers-solver` site at `crates/kwavers-solver/src/forward/pstd/physics/residual_gas_absorption.rs:74` (`spectrum: &mut Array3<kwavers_math::fft::Complex64>`) ALREADY uses `use leto::{Array3, ArrayView3};` (L65), so its `Array3` resolves correctly. Only the plugin test mock is broken.
- **`repos/kwavers` gitlink advance this session**: `4f344f840` (Phase-3 → Phase-4 → Phase-5 sweep closure at inner HEAD `ccc6bbf9e6`). KW-CV-001 watchpoint re-probed at `ccc6bbf9e6` — still 0; peers continue `Migrate *.rs from ndarray to leto` subject phrasing. Atlas-meta defers final closeout pose until peer's closeout subject lands.

- **[OBSERVED 2026-07-09 round-3 codex-session block + Standing reminders + Cross-engineering verification + Out-of-scope + Atlas-root dirty triage + Review nit rolling list deduplicated to canonical Region 1 (L1-L282) ordering via atomic structural-cleanup chore; see `### In-flight claims (per concurrent_agents)` L82 + canonical `#### Standing reminders` L112 + canonical `## Review nit rolling list` L186 for the authoritative copies. This tombstone also absorbs the prior `93f676ffd` forward-auditor cross-reference to the L262 SUPERSEDED + L263 slice-1 partial-closure-mark block, which remains the canonical Batch #1 source-side closure reference (see ADR 0013 `## Supersedes` field for the full Batch #1 source-side closure mark).]**


## Batch #1 source-side migration -- slice 3 partial-closure-mark 2026-07-08

Per the peer's `d2cb977b` chore (refactor(kwavers-solver): Migrate diffusion.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 3), on codex/kwavers-core-moirai-parallel atop parent c77a926d8): **5/41 sites migrated in 3/15 files** cumulative. The 1 new site is in crates/kwavers-solver/src/forward/nonlinear/kuznetsov/diffusion.rs (1 mut + 4 immut Zip par_for_each at L93, migrated with 5 is_standard_layout() asserts + as_slice{_mut,}() + par_mut().enumerate() with 4 flat-index lookups). **36/41 sites / 12/15 files remain**. Full-closure mark remains retracted. KW-CV-001 watchpoint remains ACTIVE.
## Batch #1 source-side migration -- slice 2 partial-closure-mark 2026-07-08
> Note: this mark landed after the slice 3 mark (commit f2c89a73) due to flaky prior re-emission attempts; it documents cumulative state AT slice 2 chore landing, not the present state.

Per the peer's 9541155f chore (refactor(kwavers-solver): Migrate model_impl.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 2), on codex/kwavers-core-moirai-parallel atop parent 5cd8c708): **4/41 sites migrated in 2/15 files cumulative** at slice 2. The 2 new sites are in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/model_impl.rs` (1-mut + 2-immut Zip par_for_each at L48 + 1-mut + 3-immut Zip par_for_each at L62 inside KuznetsovWave::update_wave). **37/41 sites / 13/15 files remain**. KW-CV-001 watchpoint remains ACTIVE. NOTE: retroactive land AFTER slice 3 mark (prior re-emission attempts failed).
## Batch #1 source-side migration -- model_impl.rs Nit 1 asymmetry fixup mark 2026-07-08

Per the peers b21679f5c chore (fix(kwavers-solver): Add standard-layout assert to model_impl.rs migration, on codex/kwavers-core-moirai-parallel atop parent d2cb977b): closes Nit 1 asymmetry by retroactively adding 7 is_standard_layout() asserts to model_impl.rs (slice 2 file): 3 in first-step branch + 4 in multi-step branch. Mirrors the struct_impl.rs fixup c77a926d8 in style. Cargo check clean. Cumulative at the migration level unchanged: **5/41 sites / 3/15 files migrated + 2 file-level fixups** (c77a926d8 + b21679f5). 36/41 sites / 12/15 files remain. KW-CV-001 watchpoint remains ACTIVE.

## Batch #1 source-side migration -- slice 4 partial-closure-mark 2026-07-08

Per the peer `9595a99f5` chore (refactor(kwavers-solver): Migrate nonlinear.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 4), on codex/kwavers-core-moirai-parallel atop parent b21679f5c): **6/41 sites migrated in 4/15 files** cumulative. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/nonlinear.rs` (1-mut + 3-immut Zip par_for_each at L109 in `compute_nonlinear_term_workspace`). **35/41 sites / 11/15 files remain**. Full-closure mark (Batch #1 CLOSED) remains retracted, this is the fourth per-slice partial-closure mark. KW-CV-001 watchpoint remains ACTIVE.

## Batch #1 source-side migration -- slice 5 partial-closure-mark 2026-07-08

Per the peer `d614a7f57` chore (refactor(kwavers-solver): Migrate operator_splitting/mod.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 5), on codex/kwavers-core-moirai-parallel atop parent 9595a99f): **7/41 sites migrated in 5/15 files** cumulative. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/operator_splitting/mod.rs` (1-mut + 1-immut Zip par_for_each at L191 in `OperatorSplittingSolver::nonlinear_step`). **34/41 sites / 10/15 files remain**. KW-CV-001 watchpoint remains ACTIVE.

## bash-heredoc artifact audit verification 2026-07-08

> Audit verified: 0 unresolved `\$VAR` artifacts (matches pattern `\$[A-Z_]+`) remain in 3 PM artifacts after the \$SHORT substitution chore (commit `92dad112`). All residual `$` characters in the 3 PM artifacts are legitimate (Rust generic syntax `<$t as Scalar>`, command-substitution documentation `$(cd repos/...)`, mathematical notation, or anti-pattern template examples in audit prose). Code-reviewer N3 carry-forward from the \$SHORT substitution chore is now CLOSED.

## Batch #1 source-side migration -- slice 6 partial-closure-mark 2026-07-08 (heterogeneous site 1 deferred)

Per the peer `7be3fbbd8` chore (refactor(kwavers-solver): Migrate rhs.rs homogeneous par_for_each sites to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 6), on codex/kwavers-core-moirai-parallel atop parent d614a7f5): **11/41 sites migrated in 6/15 files** cumulative. The 4 new sites are in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/rhs.rs` (1-mut + 1-immut Zip par_for_each sites in `KuznetsovWave::compute_rhs` homogeneous branch -- linear/laplacian, source/cache_source, nonlinearity/nonlinear_term, diffusion/diffusive_term). **30/41 sites / 9/15 files remain**. **Heterogeneous Zip::indexed site 1 deferred to follow-up chore**. KW-CV-001 watchpoint remains ACTIVE. Filename arithmetic restored to 6/15 from commit-body off-by-one of 5/15.

- **slice 9 partial-closure-mark 2026-07-09 — kwavers Batch #1 source-side migration slice 9 PARTIAL CLOSURE (1 site in spectral.rs; the deferred heterogeneous 4-mut-0-immut Zip::indexed chain)**: per the peer's `949e5a39` chore (`refactor(kwavers-solver): Migrate spectral.rs 4-mut Zip::indexed to verbose is_standard_layout (Batch #1 source-side slice 9)`, on `codex/kwavers-core-moirai-parallel` atop slice 8 parent `9ab677b0`): 1 deferred heterogeneous site migrated. The site lives in `crates/kwavers-solver/src/forward/nonlinear/westervelt_spectral/spectral.rs` in `initialize_kspace_grids` — the 4-way `Zip::indexed(&mut kx).and(&mut ky).and(&mut kz).and(&mut k_squared).par_for_each(|(i, j, k), kx_v, ky_v, kz_v, k2| { let kx_val = kx_axis[i]; let ky_val = ky_axis[j]; let kz_val = kz_axis[k]; *kx_v = kx_val; *ky_v = ky_val; *kz_v = kz_val; *k2 = kx_val * kx_val + ky_val * ky_val + kz_val * kz_val })` chain. **Strategy**: Pattern A — extend divergence.rs slice 7 3-mut strategy to 4 muts. Keep `Zip::indexed(kx.view_mut())` as the parallel iterator (the closure body consumes `(i, j, k)` for closure-captured Vec<f64> reads `kx_axis[i]/ky_axis[j]/kz_axis[k]`); pre-extract 3 flat `as_slice_mut()` buffers for `{ky, kz, k_squared}`; write 3 additional mut outs via `op_slice[idx]` inside the closure, computing `idx = i*(ny*nz) + j*nz + k` inline once per iteration (~10 cycles vs ~100 for a div/mod-based idx-to-(i,j,k) decomposition in a drop-everything pattern). Race-freedom preserved: each parallel task writes to 4 distinct output elements (kx_v via Zip iterator + 3 disjoint `slice[idx]` writes), all addressed by the same unique `(i, j, k)` tuple. **Precondition asserts**: 7 layout/length asserts total = 4 verbose `is_standard_layout()` on `{kx, ky, kz, k_squared}` mut outs + 3 `debug_assert_eq!` on `{kx_axis, ky_axis, kz_axis}.len()` (Vec<f64> is unconditionally C-contiguous, so length is the only precondition — matching slice 8 cluster D's `σ_*` Array1<f64> pattern verbatim). **WHY NOT HELPER rationale documented inline**: (a) verbose-form is Batch #1 SSOT with helper adoption in 0 of 9 migrated sites across slices 1-8; (b) the slice 9 4-mut extension deliberately matches divergence.rs slice 7 3-mut verbatim for source-level consistency; (c) broader helper-validation across heterogeneous patterns is deferred to Batch #2. **Validation**: `cargo check -p kwavers-solver --lib --no-default-features` rc=0; `cargo test -p kwavers-solver --lib forward::nonlinear::westervelt_spectral` rc=0 — all 6 westervelt_spectral tests pass bitwise (`k_squared_dc_bin_is_exactly_zero`, `k_squared_fundamental_mode_matches_2pi_over_lx`, `k_squared_nyquist_bin_equals_pi_over_dx`, `spectral_laplacian_of_constant_is_zero`, `spectral_laplacian_of_sine_matches_analytical`, `spectral_laplacian_into_is_bitwise_identical_to_allocating`). **Code-reviewer verdict on the source-side commit**: OK to commit after 1 minor nit applied (sharpened the WHY-NOT-HELPER section (b) rationale to drop the imprecise "N>5 closure-captured immuts" claim, since this site only has 3 immuts). **KW-CV-001 watchpoint state**: remains ACTIVE — no formal `closeout`/`final`/`completion`/`close-batch` substring exit in the last 30 inner kwavers commits; per `concurrent_agents` disjoint-scope rule, atlas-meta continues to observe without re-emitting the prior retracted full-closure mark. Atlas-meta path forward: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit.

- **ADR 0014 forward-looking note 2026-07-09 — KW CV-001 watchpoint active awaiting kwavers peer stream closeout-tag chore**: per the new ADR 0014 `D:/atlas/docs/adr/0014-kwavers-batch1-closeout-tag.md` (Status `Proposed` on 2026-07-09), the kwavers Batch #1 closeout-tag ceremony chore is opened but not yet executable. The KW-CV-001 watchpoint (per `D:/atlas/backlog.md` §In-flight claims `repos/kwavers` row: `git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l` returns 0 at inner HEAD `949e5a39`) gates the Status flip from `slice-by-slice partial closure` (ADR 0013) to `full closure` (ADR 0014). The chore bundles 3 atomic items on disjoint scopes: item (a) 1,315-file mechanical drift flush + item (b) slice 7 `is_standard_layout` predicate unification + item (kwavers closeout) — all 3 emit on `repos/kwavers` `codex/kwavers-core-moirai-parallel` per disjoint-scope (ADR 0011 §Leg 2 — atlas-meta is FORBIDDEN from touching `D:/atlas/repos/<X>/`). Atlas-meta's bystander role here: item (c) `chore(atlas): Advance repos/kwavers submodule pointer + KW-CV-001 retirement` is a forward chore whose trigger is items (a) + (b) + closeout-style-commit having landed on the kwavers peer stream. When the stash lands, item (c) advances `repos/kwavers` parent-tree gitlink + either deletes or marks `RETIRED 2026-07-09+` the KW-CV-001 row in §In-flight claims. ADR 0014 itself is then flipped `Proposed` → `Accepted` via a follow-up atlas-meta chore commit. Until the kwavers peer stream emits items (a)+(b)+closeout, this ADR remains `Proposed` + this note remains the residual forward-looking visibility surface.

- **Blocker-triage chore briefs 2026-07-09 — 5 carried-forward blockers re-probed against owning peer streams (per ADR 0013/#14 §Out of scope items 1-4)**: atlas-meta orchestrates the 2026-07-09 re-probe of the 5 carried-forward blockers referenced by ADR 0013 §Out of scope items 1-5 + ADR 0014 §Out of scope items 1-5. The re-probe results classify each blocker as RETIRED (cargo-clean), RECLASSIFIED (different actual cause), CORRECTED (right outcome, wrong count), or CONVERTED (workstream-already-progressing). Each blocker becomes a discrete chore on its owning peer stream per disjoint-scope (ADR 0011 §Leg 2); atlas-meta's bystander role is filing the brief here.

| Row | Blocker ID | Owning peer stream | Re-probe classification | Action verb on peer stream | Cross-walk |
|-----|-----------|---------------------|-------------------------|----------------------------|------------|
| 1 | ritk-wgpu-compat burn workspace-manifest (ADR 0013 §Out-of-scope #1) | `repos/ritk` | **➜ RETIRED** — `cargo check -p ritk-wgpu-compat --lib --no-default-features` rc=0 verified on ritk inner HEAD `a1bf4ac43` (17.32s) on branch `main`; `burn` + `burn-ndarray` deps are accepted by cargo | No chore required for Batch #1 closure. Optional: Burn-strip per ADR 0012 §Sub-batch #5 `[major]` for the longer-term Burn removal cycle (NOT part of Batch #1 gate) | ADR 0013 §Out-of-scope #1 amended with ➜ RETIRED note |
| 2 | ritk-registration burn dep strip (ADR 0013 §Out-of-scope #2) | `repos/ritk` | **➜ RECLASSIFIED** — actual cause is `direct-parzen` feature-gate regression; 2 `E0432` errors at `crates/ritk-registration/src/metric/histogram/parzen/image_cache_helpers.rs:7:43` (`SparseWFixedCache` gated behind `direct-parzen` feature) + `crates/ritk-registration/src/metric/histogram/mod.rs:10:17` (`atlas_parzen_cache` module gated behind same feature) | Open chore on `repos/ritk`: gate the importing modules behind a `#[cfg(feature = "direct-parzen")]` proxy or fix the import path; commit title `fix(ritk-registration): Resolve direct-parzen feature-gate E0432 errors`. Verification: `cargo check -p ritk-registration --lib --no-default-features` rc=0 | ADR 0013 §Out-of-scope #2 amended with ➜ RECLASSIFIED note; ADR 0014 §Out-of-scope #2 inherits |
| 3 | ritk-image autodiff-module syntax (ADR 0013 §Out-of-scope #3) | `repos/ritk` | **➜ RETIRED** — `cargo check -p ritk-image --lib --no-default-features` rc=0 verified on ritk inner HEAD `a1bf4ac43` (18.77s); remaining `autodiff` references (`host_extract.rs:73,114,115` `type AB = Autodiff<NdArray<f32>>;` test fixture + `types.rs:188` comment) are inert feature-gated test types | No chore required. Informational only — the carried-forward entry was inaccurate; the lib does not have a syntax error | ADR 0013 §Out-of-scope #3 amended with ➜ RETIRED note |
| 4 | 1,315-file kwavers mechanical drift (ADR 0013 §Out-of-scope #4) | `repos/kwavers` | **➜ CORRECTED** — actual drift is 30 modified files, not 1,315 (`git status --short | wc -l` against `repos/kwavers` inner HEAD `445ab9b2` on `codex/kwavers-core-moirai-parallel`); sample of 30/30 modifications is whitespace-only (LF vs CRLF normalization) | Open chore on `repos/kwavers`: emit `chore(kwavers): Flush mechanical dirty triage (30-file CRLF/whitespace batch)` per ADR 0014 §Sequencing step 1 (corrected file count). Verification: `git status --short | wc -l` returns 0 post-chore | ADR 0014 §Sequencing step 1 + §Verification plan item 2 amended with corrected 30-file count |
| 5 | kwavers-math Phase-3/Phase-4 ndarray → leto migration breakage (ADR 0013 §Out-of-scope #5) | `repos/kwavers` | **➜ CONVERTED** — 2 actual commits landed on kwavers peer post-slice-9 `949e5a39`: `445ab9b2` `fix(kwavers-math): linear algebra import/API mismatches` + `e2e1e180f` `fix(kwavers-math): grid/transducer compilation issues` (both kwavers-math-scoped exclusively) | Workstream already in progress on kwavers peer stream; no new chore required from atlas-meta. Monitoring posture until `cargo check -p kwavers-solver --lib --no-default-features` rc=0 restored post-`Array2::from_shape_vec` signature shift | ADR 0013 §Out-of-scope #5 + ADR 0014 §Out-of-scope #5 amended with ➜ CONVERTED note referencing actual commit SHAs |

Triage-summary headline: **5 carried-forward blockers re-probed 2026-07-09; 3 NOT real (#1, #3, #4 overstated), 1 misdiagnosed (#2 not Burn — feature-gate), 1 real + active (#5 already progressing on kwavers peer with 2 actual commits). Batch #1 closure gate unaffected**: ✅ ADR 0013 §Verification plan step 2 `cargo check -p kwavers-solver --lib --no-default-features` rc=0 at slice 9 parent inner HEAD `949e5a39` verified. The post-slice-9 `kwavers-solver --lib` breakage from `Array2::from_shape_vec` signature shift is the explicit Batch #2 prerequisite gate per ADR 0014 §Verification plan step 8. Filing this brief acts as the forwarding ledger: each row's own peer stream picks up its chore at their cadence; atlas-meta does not co-emit the chore commits per disjoint-scope.

- **ADR 0015 trigger-chore brief 2026-07-09 — Open KW Batch #2 Entry Point #1 (`kwavers_safety::with_zip_standard_layout` const-generics arity extension) on kwavers peer stream**: per the new ADR 0015 `D:/atlas/docs/adr/0015-kwavers-batch2-entrypoint1-helper-const-generics.md` (Status `Proposed` on 2026-07-09), the kwavers-solver Batch #2 Entry Point #1 acceptance-validation chore is opened but **currently BLOCKED on Block #5** (per ADR 0013/0014 §Out of scope #5 + Blocker-triage chore briefs row 5). The chore design refines ADR 0013 §Open Batch #2 Entry Point #1 with a const-generics arity extension `[(&'static str, &'imm Array3<A>); N]` with `const N: usize` for the helper signature; this replaces the current dynamic-slice form `'imm [(&'static str, &'imm Array3<A>)]` (which forces runtime indexing + local `Vec` allocation + HRTB friction at N>5 closure captures). The implementation commits live on `repos/kwavers` peer stream per disjoint-scope (ADR 0011 §Leg 2 ABSOLUTE — atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` edits). **Acceptance criteria (AC-1 through AC-6) per ADR 0015 §Verification plan**: AC-1 `cargo check -p kwavers-solver --lib --no-default-features` rc=0 (Block #5 gate); AC-2 `cargo test -p kwavers-solver --lib` rc=0; AC-3 6/6 westervelt_spectral tests bitwise-identical; AC-4 helper-stress fixture backporting slice 6b rhs.rs 9-immut heterogeneous Phase 2 site bitwise vs verbose-form RHS at all (i,j,k) grid points; AC-5 `cargo test -p kwavers-solver --lib --features helper-stress` rc=0; AC-6 slice 6b site in-place adoption preserves bitwise equivalence. The standing reminder is recorded here in atlas-meta side until AC-1 through AC-6 are all ✅; at that point, atlas-meta emits Step 5 (status-flip chore commit) per ADR 0015 §Sequencing on the kwavers peer core-moirai-parallel branch HEAD that achieves acceptance.

- **ADR 0015 Step 2 design-spec landing 2026-07-09 — KW Batch #2 Entry Point #1 Step 2 helper const-generics extension design-spec filed on atlas-meta side per disjoint-scope**: per ADR 0015 §Sequencing `### Step 2 detailed design specification` amendment landed on atlas-meta by this commit, the Step 2 design-spec is filed as the SSOT that the kwavers claim stream picks up once Block #5 closes. **Status reaffirmation (probed 2026-07-09)**: Block #5 pre-flight gate STILL BLOCKED on `cargo check -p kwavers-solver --lib --no-default-features` (rc≠0; E0308 type mismatches in `kwavers-transducer` + E0599 missing `matmul`/`assign` methods + `kwavers-transducer/focused/arc.rs` syntax gaps; the post-slice-9 commits `445ab9b2` + `e2e1e180f` did not close the gate). The Step 2 design-spec captures: (a) target file `D:/atlas/repos/kwavers/crates/kwavers-solver/src/safety/mod.rs:L84-130` (NEVER EDIT FROM ATLAS-META); (b) 4 modifications to apply (add `const N: usize` + change `immuts` to `[(&str, &Array3<A>); N]` + simplify closure-bound array form + replace `Vec` with `std::array::from_fn`); (c) preserved constraint surface verbatim (`A: Copy + Send + Sync` + verbose panic message form + `'out` lifetime + Nit-1-fix `A: 'static` omission); (d) monomorphization analysis (~30 KB binary impact bounded at N=0..9); (e) Send + Sync propagation + disjoint-capture-rule analysis; (f) HRTB retention recommendation (`for<'s>` kept for forward-compat); (g) acceptance criteria AC-2a/AC-2b/AC-2c + reviewing checklist (atomic-boundary + disjoint-scope + paragraph-collapse). Step 2 cannot execute from atlas-meta per ADR 0011 §Leg 2; the kwavers claim stream owns the implementation commit. Standing reminder updated to: Step 2 design-spec SHIPPED; Block #5 gate BLOCKED; pre-flight gate re-probe required before ASSEMBLE-STATE confirmation.

- **ADR 0016 trigger-chore brief 2026-07-09 — Open Block #5 (kwavers-math ndarray → leto) resolution design-spec on kwavers peer stream per disjoint-scope**: per the new ADR 0016 `D:/atlas/docs/adr/0016-kwavers-block5-resolution-design-spec.md` (Status `Proposed` on 2026-07-09), the kwavers-math Phase-3/Phase-4 ndarray → leto migration resolution chore is opened with a 3-commit atomic decomposition recommended design. Block #5 pre-flight gate is the **AC-1 prerequisite for ADR 0015 Acceptance** (Batch #2 Entry Point #1 helper const-generics extension depends on this). Pre-flight gate state (probed 2026-07-09): `cargo check -p kwavers-solver --lib --no-default-features` returns rc≠0 with 8 errors in `kwavers-transducer` (E0308 type mismatches in `beamforming/processor.rs` + E0599 missing `matmul` on `leto::Array` + E0599 missing `assign` on `Result` in `calibration/manager/mod.rs` + arc.rs syntax gaps in `transducers/focused/arc.rs`); the 2 already-landed commits `445ab9b2a` + `e2e1e180f` closed kwavers-math-only scope but did NOT propagate fixes to kwavers-transducer/receiver/boundary/source/grid callers. The 3-commit atomic decomposition per ADR 0016 §Decision: (1) `fix(kwavers-transducer): Resolve E0308/E0599 + arc.rs syntax (Block #5 sub-batch 1 — strict additive)` — arc.rs syntax + o_ops::linalg::matmul import) + Result.assign migration (destructured `if let Err(e)` pattern) + E0308 `leto::Array` boundary reconciliation; (2) `refactor(kwavers-migration): Migrate Array2::from_shape_vec tuple→array workspace-wide (Block #5 sub-batch 2 — strict signature migration)` --- 8 crates [python, solver, analysis, transducer, receiver, boundary, source, grid] using `sed`-assisted migration from `(rows, cols)` form to `[rows, cols]` array form; (3) `chore(kwavers): Block #5 gate-validation regression test (Block #5 sub-batch 3 — gate reset)` --- CI-side rc=0 assertion + bitwise-identical 6/6 westervelt_spectral tests against slice 9 inner HEAD `949e5a39` baseline. AC-1 through AC-5 per ADR 0016 §Verification plan (kwavers-transducer rc=0 + workspace-wide `Array2::from_shape_vec((` count = 0 + kwavers-solver rc=0 + 6/6 westervelt_spectral bitwise + no false-positive KW-CV-001 watchpoint trigger). Implementation commits live on `repos/kwavers` peer stream per disjoint-scope (ADR 0011 §Leg 2 — atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` edits). Standing reminder: Block #5 design-spec SHIPPED as the SSOT; kwavers claim stream owns the 3-commit implementation; once the 3 commits land + AC-1 through AC-5 satisfied, atlas-meta emits Step 5 status-flip chore per ADR 0016 §Sequencing flipping ADR 0016 to `Accepted` + simultaneously unblocks ADR 0015 AC-1.

## Provider integration audit queue — 2026-07-13

| ID | Class | Status | Owner/scope | Acceptance |
|---|---|---|---|---|
| HEPH-EMPTY-001 | [patch] | done (`65e89b7`, merged `991f12e`) | Hephaestus decomposition state | Synthetic empty factors deleted; determinant, identity, rank, permutation, and shape contracts pass CUDA/WGPU value tests and the 239-test package suite. |
| MEL-SCOPE-001 | [major] | done (`55ad20e`, merged `bb07447`) | Melinoe capability plus Mnemosyne/Themis/Moirai/Gaia/Coeus/Hephaestus consumers | Unsafe implementer obligation encoded; consumers migrated; Miri, conformance, and provider-version unification pass. |
| MOI-NUMA-001 | [major] | done — ADR 0017, deleted `numa.rs` (4 P0 defects) | Moirai + Mnemosyne/Themis ownership — redirected via ADR 0017 | Deleted 334-line `numa.rs`; existing Themis (placement), Mnemosyne (allocation), Moirai executor (work-stealing) cover the domain. Zero external consumers confirmed. |
| MOI-RESOURCE-214 | [patch] | done — merged PRs #70/#71 (`b637064`) | Moirai `moirai-sync/src/sync/resource_pool.rs`; deterministic clear/recycle interleaving; provider PM artifacts | Provider implementation `eb62898`, review-state `cd84276`, and PM closeout `5788b03`; 20/20 nextest, Clippy, rustdoc, doctests, and Criterion baseline pass; Atlas gitlink advanced to final provider head `b637064`. |
| MOI-DEQUE-POISON-215 | [patch] | implemented 2026-08-05 | Moirai `moirai-scheduler` Chase-Lev retired-array reclamation | `retired_arrays` lock recovery in resize, drop, and test observation now uses poison-tolerant `into_inner()` recovery, preventing secondary panics after an unwinding lock holder. Regression poisons the lock, forces further resize, drains all 80 items exactly once, and verifies final destruction. `cargo check`, warning-denied Clippy, Nextest 26/26, doctests 2/2, rustfmt, and diff checks pass. Scope is limited to `moirai-scheduler/src/deque/chase_lev.rs` and `src/deque/tests.rs`; peer-dirty Moirai paths remain untouched. |
| MOI-BLOCKING-213 | [arch] | done — merged PRs #72/#73/#74 (`6184f73`) | Moirai executor blocking lane; provider PM artifacts | Lazy bounded blocking lane isolates compute workers; separate counters preserve quiescence and metrics; 87/87 nextest, executor-only warning-denied Clippy, rustdoc/doctest evidence, starvation/backpressure/priority/cancellation/shutdown/concurrent-producer tests, and Criterion rows pass. |
| THEM-CACHE-001 | [minor] | done (`18807bb`, merged PR #6) | Themis cache detection | Linux cache parsing returns typed absence on malformed input; Themis consumer pins are co-evolving. |
| LETO-SCALAR-001 | [major] | partial (`855f3ad`) | Leto scalar execution — length pre-validated; Hermes error propagation remains | Partial write closed: `assert_eq!` preconditions in all mutating Scalar methods. 304/304 leto-ops tests pass, apollo-fft builds clean. Error propagation deferred to Result-returning Scalar trait API change. |
| MNE-PERCPU-001 | [patch] | done (verified 2026-07-15) | Mnemosyne local cache — lazy `OnceLock<Box<>>` confirmed | Static footprint ~56 bytes, not 720,896. No backend enables `ENABLE_CPU_CACHE`. |
| TREE-SRP-001 | [arch] | done — ADR 0018 Phases 1-3 complete; Phase 4 filed as TREE-DUP-002 | Melinoe/Themis/Moirai hierarchy | ADR-0018: melinoe halo consolidated (→ melinoe::collections), themis tests rehomed (→ tests/), moirai constants.rs split, Phase 4 deferred. |

## Watchpoints — 2026-07-19 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| MR-WATCH-001 | moirai-scheduler/executor rebuild | `9c015a3` peer break + `5343ebfc` mid-fix | peer green clean HEAD | ✅ CLOSED 2026-07-14 (720/720 at `c43f86a`) |
| HERMES-WATCH-001 | Hermes Mnemosyne consumer Miri | PR #6 `db8e1a4` after provider PR #13 | fresh GitHub Miri/CI completes green | ✅ CLOSED 2026-07-19 (`cargo miri test -p hermes-simd-core` 14/14 pass; mnemosyne locked at `9b8585db` includes aliasing fix `5a9f49f`) |
| MOI-CONTENTION-001 | moirai contention audit | `perf/moirai-contention-audit` branch with contention fixes | merged to main at `9cd650f`, 82/82 pass | ✅ CLOSED 2026-07-15 |
| KW-WATCH-002 | kwavers-therapy abdominal perf | 90s `elastic-fwi` nextest override | peer-stream perf fix | ⏳ open (FFT zero-alloc helper committed, algorithmic perf in peer scope) |
| KW-WATCH-003 | kwavers-python leto→ndarray conversion compile break | `b861254` peer HEAD + 13 WT dirty | peer lands clean green committed HEAD | ✅ CLOSED 2026-07-19 (false positive: pyo3 0.29 alignment resolved 61 E0277; `cargo check -p kwavers-python` clean with 0 errors) |
| ritk Burn-strip verify-block | ritk Batch #3 #4-#6 dep strip | `ba6da3a` 1-ahead + 5 WT dirty | peer pushes, cleans WT, nextest green | ✅ CLOSED 2026-07-19 (Burn→Coeus doc rename committed `22cdbffb`; zero Burn/ndarray production deps remain; `cargo check --workspace` clean) |
| MNE-PERCPU-001 | Mnemosyne per-CPU cache | 720,896-byte dormant static | n/a | ✅ CLOSED 2026-07-15 (lazy OnceLock verified) |
| LETO-SCALAR-001 | Leto scalar length pre-validation | Hermes error discard + silent partial write | n/a | ✅ CLOSED 2026-07-15 (`aecb231`); error propagation deferred to `[major]` |

## Watchpoints — 2026-07-20 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| HARM-PUBLISH-001 | `repos/harmonia` submodule registration | Local `repos/harmonia` worktree was unversioned pending remote publish | Peer publishes the `repos/harmonia` worktree to `https://github.com/ryancinsight/harmonia` and advances the Atlas gitlink | ✅ CLOSED 2026-07-20 (peer PR #57 merged `0b0d01d`: Harmonia published at `cf6ce3e`, `.gitmodules` entry added, gitlink advanced, ADR 0023 flipped `Proposed` → `Accepted`, current-stack table reconciled to 20 packages) |
| HEPH-CUDA-WIN-001 | `repos/hephaestus/crates/hephaestus-cuda` + `hephaestus-python` Windows-gnu link | Verified sweep across all 20 Atlas packages: `cargo check` clean across all 20; the bounded per-package nextest run reports `hephaestus-cuda` and `hephaestus-python` fail to build with `x86_64-w64-mingw32-gcc` link error reading `-L /usr/local/cuda-11.3/lib64/` and `-lcuda` on the Windows-gnu host. Hephaestus core/wgpu/metal subset (211/211) is clean | Upstream build script (in `cuda-oxide` or `cutile-rs`) emits a Windows-aware CUDA SDK path via `CUDA_PATH` (`%CUDA_PATH%\lib\x64\cuda.lib`) and the link succeeds on a Windows NVIDIA host; this is an environment defect, not a code regression | ⏳ open (2026-07-20 Session 3 re-confirmed: 211/211 hephaestus core/wgpu/metal under `--exclude hephaestus-cuda --exclude hephaestus-python`; cuda + python skipped per upstream `cuda-oxide`/`cutile-rs` Linux-shaped link path; not a regression) |

## Watchpoints — 2026-07-20 Session 3 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| ASCLEPIUS-REG-001 | `repos/asclepius/` registration | Published two-crate workspace and fetched remote-default merge `ceb8b6d`; explicit P1 promotion request satisfies the prior reopen trigger | Merge `.gitmodules`, exact gitlink, ADR 0028, and stack documentation; then materialize the provider in consumer CI | ✅ CLOSED 2026-07-20 Session 5 (peer commit `6fb5576` "feat(atlas): Register Asclepius" registered the submodule; ADR `0028-asclepius-biological-response-promotion.md` filed Status `Accepted`; `.gitmodules` lines 86-88 reference `repos/asclepius` -> `https://github.com/ryancinsight/asclepius.git`; 23-package stack recorded in README + INDEX; cross-ref `gap_audit.md` L3-34 Asclepius P1 promotion entry) |

## Watchpoints — 2026-07-21 Session 6 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| HELIOS-TYCHE-MAJOR-001 | `repos/helios/crates/helios-imaging/src/noise.rs` + workspace `tyche-core` pin | tyche peer landed breaking `e1a5964 feat(tyche-core)!: Type counter streams` (`StandardNormal<T>` -> `StandardNormal<T, A: StreamAlgorithm>`); the helios `[patch]` override resolves tyche-core to local HEAD `0fc810b` (post-break), bypassing the manifest rev `87923da9...` (dead pin) | Peer migrates `helios-imaging/src/noise.rs:17,45` to the two-param form `StandardNormal::<f64, SplitMix64>::at(seed, sample_index, 0)` (add `SplitMix64` to the `use tyche_core::{...}` import on line 17) and re-establishes the 251/251 nextest baseline; OR bumps the manifest rev pin to `0fc810b` and updates `Cargo.lock` accordingly | ✅ CLOSED 2026-07-21 by helios peer PR #15 (`d82e3bb`): commit `4a01443 "feat(helios-imaging)!: Pin Tyche stream"` removed the local path override entirely (eliminating rev drift), made the algorithm and stream version part of the replay identity, and filed ADR `0005-tyche-noise-stream.md`. Helios main `11487c2` is the merged default post-PR #15; user's standing "implement and resolve examples" helios dispatch is satisfied. |
| CFDRS-TYCHE-MAJOR-001 | `repos/CFDrs/crates/cfd-optim/src/design/space/sampling/mod.rs` + workspace `tyche-core` pin | same tyche breaking change; the CFDrs `[patch]` override resolved the post-break provider | Peer supplies `SplitMix64` to `LatinHypercube` and routes indexed words through `Counter<UserDomain<0>, SplitMix64>` | ✅ CLOSED 2026-07-21 by CFDrs `fca1a9a9`; the exact migrated source is present in public default `394c9977` |
| CFDRS-CFD1D-LINT-001 | `repos/CFDrs/crates/cfd-1d/**` (15 files, ~50 sites) | surfaced in Session 6 `cargo clippy --workspace --all-targets -- -D warnings` during tyche-break verification; pre-existing pedantic lint floor debt in cfd-1d independent of tyche | Peer brings cfd-1d to the workspace `-D warnings` floor: ~26 `uninlined_format_args`, ~6 `manual_map`, ~5 `useless_conversion` to `f64`, 3 `result_large_err` (Err variant >=160 bytes in `PrimarySolveError`), 2 `manual_range_contains`, 2 `field_reassign_with_default`, and ~6 scattered (`complexity`, `explicit_into_iter_loop`, `empty_line_after_doc_comments`, `iter_cloned_collect`) | ⏳ open until 8-warning residual baseline clears (first decrement landed 2026-07-23 by atlas-meta coordinator PR #312 `4ccd4f85`): 54 pedantic warnings -> 8 via mechanical `cargo clippy --fix` (12-file span, 26 `uninlined_format_args` + 20 sibling auto-fixables `unnecessary_map_or`/`useless_conversion`/`.into_iter`/`.into`). Residual 8-warning baseline: 3 `result_large_err`, 1 `very_complex_type`, 1 `empty_line_after_doc_comments`, 3 doc-test wrap — all manual-only categories peer-architectural) |

## Watchpoints — 2026-07-21 Session 7 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| CFDRS-PERF-SLOW-001 | `repos/CFDrs` heavy GPU/3D-CFD integration tests | Session 7 `cargo nextest run --no-fail-fast --workspace` on peer commit `fca1a9a9` (post-tyche-migration) reports 3 tests timing out at the 30s slow budget: `cfd-3d::poiseuille_test::validate_poiseuille_flow` (30.183s), `cfd-suite::cross_fidelity_blueprint::cross_fidelity_blueprint_complex_branching` (30.212s), `cfd-validation::benchmarks::threed::bifurcation::tests::test_bifurcation_flow_3d_murray_and_mass` (30.181s) | Peer roots-cause each timeout per `engineering_gates` (optimize the real components, never relax the slow-timeout bound; never shrink coverage); the 3072/3075 PASS baseline moves to 3075/3075 PASS without TIMEOUTs | ✅ closed (2026-07-23 Session 13 coordinator takeover: `validate_poiseuille_flow` PASS in 0.342s via PR #311 `22ddc27d` perf(cfd-3d) — hoist MidNodeCache + vertex_positions across Picard iter + lower with_direct_threshold 100_000→512 routing medium saddle-point systems to GMRES+AMG / GMRES+BlockDiag (root cause: `leto_ops::SparseLuSolver` is a misnamed dense partial-pivoting LU, O(n^3)). `cross_fidelity_blueprint_complex_branching` closed earlier by peer `153b0ed9` on 2026-07-13 (0.799s). `test_bifurcation_flow_3d_murray_and_mass` re-verified 1.934s at CFDrs main `22ddc27d`. Full cfd-3d suite: 394/394 PASS. Strategic TODO recorded as ATLAS-LETO-OPS-SPARSE-LU-001 [arch] for upstream real sparse LU/Cholesky in leto-ops) |
| CFDRS-LINT-CASCADE-001 | `repos/CFDrs/crates/cfd-math/src/iterators/stencils.rs:101`, `cfd-math/src/iterators/windows.rs:108`, `cfd-schematics/src/heatmap/mod.rs:286`, `cfd-schematics/src/interface/presets/composite/specialized/parallel_lane.rs:24` | Session 7 `cargo clippy --workspace --all-targets -- -D warnings` halts on 4 site-level errors before reaching cfd-1d/cfd-2d/cfd-3d/cfd-core/cfd-validation/cfd-optim/cfd-suite/cfd-io/cfd-python/xtask; the 4 blockers are `needless_question_mark` ×2 in cfd-math and `print_literal` + `manual_filter` in cfd-schematics | Peer remediates the 4 cascade-blocking clippy errors; once unblocked, run `cargo clippy --workspace --all-targets -- -D warnings` to measure the actual `cfd-1d` baseline vs the Session 6 ~50-site estimate (which may have been inflated by the prior `cargo check`-then-clippy masking) | ⏳ open (2026-07-21 Session 7 cataloged; independent of tyche migration; blocks the `CFDRS-CFD1D-LINT-001` baseline measurement; recorded for the CFDrs peer) |

## Watchpoints — 2026-07-21 Session 8 (atlas-meta coordinator view)

No new atlas-meta-owned watchpoints. Session 8 activity:

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| LETO-VERIFY-CONTENTION-001 | `repos/leto` at `b7224832e` `perf(leto-ops): Vectorize UDU weighted-dot` | Session 8 bounded subagent attempt to run `cargo nextest run --no-fail-fast --workspace` + `cargo test --doc --workspace` on leto post-gitlink-reconcile; blocked by peer-held `CARGO_TARGET_DIR` lock (peer `cargo-nextest.exe` PID 48380 live, not orphan). This is verification contention, not a defect | Atlas-meta bounded nextest + doctest re-run when peer build activity ceases (no live `cargo-nextest.exe` in `tasklist`); per `concurrent_agents` peer's green run on this shared tree IS authoritative evidence on shared branch | ✅ closed (2026-07-21 Session 8 closing annotation: peer cargo-clippy shift released lock; atlas-meta bounded nextest 592/592 PASS rc=0 (slowest 1.023s, zero timeouts) + doctests 9/9 PASS (leto 1, leto-ops 8, leto-python 0). Differential oracles `*_matches_numpy`/`*_matches_scipy` over vectorized UDU weighted-dot kernel pass. Value-semantic correctness preserved atop `9a03735 refactor(leto)!: Retire ndarray boundary`) |

## Watchpoints — 2026-07-21 Session 9 (atlas-meta coordinator view)

atlas-meta main re-oriented at `abbec58` after peer landed 17 commits in the gap since Session 8 close. All Session 8 dispatch items superseded by peer work (user's "proceed as recommended" authorized the no-op continuation). New watchpoint evidence recorded; no new defects cataloged.

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| CFDRS-LINT-CASCADE-001 (originally Session 7) | `repos/CFDrs/crates/cfd-math/src/iterators/stencils.rs:101`, `cfd-math/src/iterators/windows.rs:108`, `cfd-schematics/src/heatmap/mod.rs:286`, `cfd-schematics/src/interface/presets/composite/specialized/parallel_lane.rs:24` | Session 7 catalog of 4 site-level clippy errors blocking `cargo clippy --workspace --all-targets -- -D warnings`. Session 9 audit: peer commit `dc256705` remediated sites 1-3 (stencils.rs, windows.rs, heatmap/mod.rs) via `let-else` idiom + SVG format-arg fix. Site 4 (parallel_lane.rs:24) was clean at HEAD `7a521343` — the code is already in the `Option::filter` form `manual_filter` recommends; the watchpoint entry was stale when filed | n/a — peer has remediated or never needed remediation | ✅ closed (2026-07-21 Session 9 bounded subagent audit at HEAD `7a521343`: `cargo clippy -p cfd-schematics --all-targets -- -D warnings` exits rc=0 zero warnings. All 4 watchpoint sites verified clean; clippy gate no longer blocks the cfd-1d lint baseline measurement; `CFDRS-CFD1D-LINT-001` baseline measurement is now unblocked and ready for peer to schedule under the ratchet) |
| HERMES-ADVANCE-001 (Session 9 catalog) | `repos/hermes` gitlink pin `004e6a492` vs inner HEAD `53b83165` | Single commit delta `perf(hermes): Unchecked CSR SpMV tail gather` touched only `CHANGELOG.md` + `spmv.rs` (+8 −1). nextest 388 tests 383 PASS / 5 ABORT — but all 5 aborts are in disjoint gemm/tiling dispatch tests (`ptr::replace` alignment UB on Windows), NOT in the CSR SpMV path (CSR tests `test_spmv_csr_*` all pass). Doctests 18/18 PASS, 10 ignored (cfg-gated) | n/a — peer advanced atlas-meta gitlink in the gap via peer's own `99699ea build(atlas): advance hermes gitlink — SpMV unchecked tail`. Atlas-meta's planned advance was made redundant | ✅ closed (made redundant by peer — atlas-meta main `abbec58` pins hermes at `53b83165`). Residual: the 5 gemm/tiling `ptr::replace` aborts are a pre-existing Windows UB defect — recorded below as HERMES-GEMM-UB-001 |
| HYPERION-PHASE-0-001 (Session 9 catalog) | new stack member `hyperion` at `D:\atlas\repos\hyperion\` (untracked dir, NOT in `.gitmodules`) + ADR 0030 `hyperion-photon-optical-promotion.md` + atlas-meta `0b97ba0` / `4ff5c07` consolidation commits | Peer created ADR 0030 consolidating photon/optical law across Asclepius/Leto/Hephaestus/Helios into a new standalone crate `hyperion` (v0.1.0, edition 2024, deps aequitas/eunomia/proteus). Phase 0 = scaffold + dep alignment; phase 1 = register as atlas submodule. Peer's kwavers tree has 40+ dirty files mid-Hyperion-extraction — the migration is in flight | n/a — Hyperion `7b4561b`, Helios `105a093`, Kwavers `5fc6f0419`, and CFDrs merge `69323418` complete the deletion ledger; Atlas records the exact provider and consumer gitlinks | ✅ closed (2026-07-22: `.gitmodules`, stack map, ADR 0030, PM state, and the 25-package count are synchronized; Ares and Prometheus remain separately evidence-gated) |
| HERMES-GEMM-UB-001 (Session 9 catalog — filed during HERMES-ADVANCE-001 audit) | `repos/hermes/crates/hermes-simd/tests/host_capability_tests.rs` + `crates/hermes-simd/tests/tiling_tests.rs` — 5 GEMM dispatch tests abort | `cargo nextest run --workspace` reports 5 ABORTs: `local_gemm_dispatch_matches_scalar_reference_for_irregular_shapes` (0.807s), `test_gemm_int8_signed_differential` (0.362s), `test_gemm_bf16_size_16` (0.396s), `test_gemm_int8_high_level` (0.427s), `test_gemm_bf16_high_level` (0.471s). All panic at `core::ptr::mut_ptr.rs:1495:18: unsafe precondition(s) violated: ptr::replace requires that the pointer argument is aligned and non-null`. Non-unwinding panic on Windows surfaces as `STATUS_STACK_BUFFER_OVERRUN` (0xc0000409) → abort. Pre-existing — reproducible at peer's pre-advance pin `004e6a492` as well as HEAD `53b83165`. Disjoint from the CSR SpMV path this gitlink advance introduced | Peer root-causes the `ptr::replace` alignment precondition violation in the GEMM tiling-remainder write (likely a `*mut T` produced from an under-aligned slice/holder feeding a packed-view bridge). Recommended first probe: `RUST_BACKTRACE=1 cargo nextest run -p hermes-simd --test tiling_tests test_gemm_bf16_size_16`; then Miri on the gemm kernel (SIMD intrinsics Miri-unreachable → ASan/TSan per unsafe-discipline for the load/store surface) | ⏳ open (2026-07-21 Session 9 cataloged; pre-existing defect not caused by the CSR SpMV advance. Independent of the hermes gitlink `004e6a492 → 53b83165` advance that peer landed in this session's gap. Recorded for peer scheduling since hermes is a peer-owned source tree) |
| EUNOMIA-DOCTEST-001 (Session 9 catalog — closed same session) | `repos/eunomia/crates/eunomia/src/relative_eq.rs` lines 241, 338 — `assert_relative_eq` and `relative_eq` doctests | Early Session 9 bounded subagent at eunomia 0.6.0 published surface reported 2 doctest FAILs with self-contradictory `epsilon = 1e-10, max_relative = 1e-10` example bounds for `1.0_f64` vs `1.0000001` (gap `1e-7`). Peer landed `884d193 feat(eunomia): Add relative equality` + `3e4f9eb docs(eunomia): Close equality provider gate`. Atlas-meta gitlink advance via peer's `a5279bf build(atlas): Advance Eunomia provider` reconciled the pin | n/a — peer closed the doctest gate | ✅ closed (2026-07-21 Session 9 recheck at HEAD `3e4f9eb`: doctests 9/9 PASS, zero failures, zero ignored. The two previously-failing examples now pass value-semantically against consistent bounds. Eunomia is release-ready at HEAD `3e4f9eb`) |
| HELIOS-APPROX-EUNOMIA-001 (Session 9 catalog) | `repos/helios` HEAD `105a0939 refactor(helios): migrate approx -> eunomia assert_relative_eq workspace-wide` | Peer integrated the workspace `approx -> eunomia::assert_relative_eq` migration into helios. Verification at HEAD `56e3572` (1 commit unpushed then; now pushed to origin/main = `105a0939`): nextest 251/251 PASS rc=0, slowest test 1.036s (`helios-imaging fbp::tests::quantum_noise_degrades_recon_and_scales_with_flux`), doctests 11/11 GREEN (helios-python cdylib is the only structural warning — expected). `approx` fully excised from helios `Cargo.toml` | n/a — peer landed + pushed; atlas-meta gitlink advanced via `61e209e` | ✅ closed (2026-07-21 Session 9 verification: helios `approx -> eunomia` migration is GREEN at HEAD `105a0939`. Caveat: helios still uses edition 2021 / resolver 2 (project-wide observation, not a migration defect). Dirty mdBook migration_*.md files are peer's pending book content not part of the migration commit) |

## Residual CFDrs watchpoints carried forward (still peer-owned, still open)

| ID | Status | Note |
|---|---|---|
| CFDRS-PERF-SLOW-001 | ✅ closed (2026-07-23 Session 13) | All 3 perf-slow tests under 2s at CFDrs main `22ddc27d`: `validate_poiseuille_flow` 0.342s (Session 13 perf PR #311), `cross_fidelity_blueprint_complex_branching` 0.799s (peer `153b0ed9` 2026-07-13), `test_bifurcation_flow_3d_murray_and_mass` 1.934s. Root cause of the last standing one (`validate_poiseuille_flow`) was a misnamed dense LU masquerading as sparse LU in `leto_ops::SparseLuSolver` plus per-Picard-iter cache recomputation; both root-caused and fixed at the algorithm (no threshold relaxation, no test shrinkage, no slow-timeout bound change). Strategic TODO — real sparse LU upstream in leto-ops — filed as ATLAS-LETO-OPS-SPARSE-LU-001 [arch] |
| CFDRS-CFD1D-LINT-001 | ⏳ open (now unblocked) | Session 9 closure of `CFDRS-LINT-CASCADE-001` unblocks the cfd-1d pedantic-baseline measurement. The original Session 6 estimate was ~50 sites. Peer can now run the full `cargo clippy --workspace --all-targets -- -D warnings` and schedule the actual baseline under the ratchet |
| ATLAS-LETO-OPS-REFACTOR-001 (new 2026-07-23) | ⏳ open | `leto-ops` (`repos/leto` HEAD `9346413`) is presently uncompilable on the path-dep graph (29 type/visibility errors across `crates/leto-ops/src/application/linalg/iterative/preconditioners/jacobi.rs`, `ilu.rs`, `cg.rs`, `sparse/csr.rs` mod-privacy + generic-`T`-vs-`usize` index comparison). Last destructive code commit `9a82a4d feat(leto-ops): add sparse_lu_solve and SparseLuSolver`. Subsequent commits have been audit doc/test only. Peer is mid-refactor (`ATLAS-LETO-OPS-SPARSE-LU-001` owner context). Assist-ladder (2) decision: skip — fresh and actively held by the leto peer; no claimable periphery in `leto-ops` source that doesn't collide with peer's refactor. Re-verify when peer stabilizes; not coordinator-actionable |
| CFDRS-CFD1D-LINT-001 | ⏳ open (first decrement done; 8-warning residual baseline established) | First ratchet decrement landed by atlas-meta coordinator via PR #312 `4ccd4f85` (squashed merged 2026-07-23). `cargo clippy --fix --allow-dirty -p cfd-1d --all-targets` applied 12-file mechanical remediation: 26 `uninlined_format_args` + 20 sibling auto-fixable lints (`unnecessary_map_or` -> `is_some_and`, `useless_conversion` -> `to_vec`, minor `.into_iter()` / `.into()` cleanups). Baseline: 54 pedantic warnings -> 8 (3 `result_large_err`, 1 `very_complex_type`, 1 `empty_line_after_doc_comments`, 3 doc-test wrap). Net delta -46 warnings (-85%); 728/728 cfd-1d nextest pass post-runtime. Residual 8-warning baseline parked as peer-architectural decisions (error-type redesign, type-factor, doc-comment cleanup) — next decrement candidate |

## Provider integration audit queue — 2026-07-20

| ID | Class | Status | Owner/scope | Acceptance |
|---|---|---|---|---|
| HARM-PROMOTE-001 | [arch] `[minor]` | done — PR #57 merged `0b0d01d` | harmonia / horae / athena-core / eunomia / atlas-meta | `repos/harmonia` published to `https://github.com/ryancinsight/harmonia` (HEAD `cf6ce3e`, CI run `29753063192` green); Atlas `.gitmodules` entry recorded; parent gitlink advanced; ADR 0023 Status `Accepted`; README current-stack table reconciled to 20 packages. |

## ATLAS-WORKTREE-001 — Canonical lane root consolidation [patch] — in progress

- Owner: Codex `/root` (stale-claim takeover 2026-07-22); scope: worktree lane
  locations only, no member-repo code.
- Done 2026-07-21: 24 verified-duplicate standalone clones (12 at
  `D:\worktrees`, 12 at `D:\atlas\worktrees`; all detached, clean, HEADs
  contained, zero local branches), the SHA-keyed `.atlas-provider-checkout`
  cache, and the empty `D:\worktrees\atlas` were removed; stray
  `report/figures` SVG was rescued to `repos/report/figures/`.
- Done 2026-07-22: the legacy `D:\worktrees` root is absent, 16 redundant
  junction aliases are removed, and the former scratch scripts are absent.
  The only remaining lanes are the active Atlas RITK graph lane and Kwavers
  portability lane under the canonical `D:\atlas\worktrees/` root. Each repo
  remains within the main-tree-plus-one-lane bound.
- Done 2026-08-18: revalidated seven clean linked lanes against their provider
  defaults and removed them with `git worktree remove`: Asclepius ADR,
  Consus ADR, Iris color-space, both Mnemosyne audit lanes, and both Tyche
  cleanup lanes. Each lane had zero dirty paths and its tip was an ancestor of
  the provider default; its local branch was then deleted. No active lane or
  peer WIP was touched.
- Residual: the 2026-08-19 `scripts/atlas-lane-audit.py` probe reports four
  topology violations: Consus has four trees and one lane outside the
  canonical root, Kwavers has four trees, and RITK has four trees. Their extra
  lanes are active peer scopes or carry dirty state and require the owning
  streams to complete before further reclamation. The clean-lane cleanup
  increment is complete; no source or provider pointer changed.

## ATLAS-TARGET-001 — One build cache, one debug budget [patch] — in-progress (residual)

- Owner: Codex `/root`; last-update: 2026-07-22; scope: cache trees and
  profile sections only, no simulation logic.
- Done 2026-07-21: 18 stale cache forks deleted (repo-local `target/`, `target_isolated`, `target_benches`, nested crate `target/`) reclaiming 177.8 GB; `moirai` dev/test profiles aligned to line-tables-only/deps-none (was `debug = true`, pushed `946b4a7`); root `.cargo/config.toml` gains `[profile.dev.build-override] debug = false`. Policy: AGENTS.md performance_engineering "one build cache per stack" — a discovered fork is disposable derived state.
- Done 2026-07-22: the root test profile now matches the development profile:
  workspace test crates retain line tables, while dependencies, build scripts,
  and procedural macros emit no test debuginfo. This closes the configuration
  path through which Nextest could repopulate the shared cache with full
  symbols.
- Done 2026-07-22: removed two abandoned full-target `du` scans that had
  traversed the cache for about 2.5 hours, then pruned the idle incremental
  tree. Its 27,085 session directories occupied 525,183,672,320 bytes
  (approximately 489 GiB); the five-minute deletion preserved shared
  dependencies and linked artifacts, and a subsequent build recreated only
  three current session directories. This is operational reclamation, not a
  clean-build footprint claim.
- Done 2026-07-22: Kwavers PR #307 merges as `0602c1fd4`. Its broad
  dependency graph inherits development `opt-level = 1` instead of wildcard
  `opt-level = 3`, restoring exported generic sharing. Uncached feature-build
  steps fall 18–45%; exact head `909bcdfc7` passes 26 hosted checks, full-grid
  PSTD remains below 25 seconds, and a clean debug tree measures
  16,771,464,617 bytes across 6,109 files. Cargo removes the formerly blocked
  `repos/kwavers/target_isolated` plus six other obsolete private targets:
  9,363 files and approximately 4.49 GiB, without touching `D:/atlas/target`.
  Atlas-meta format and warning-denied Clippy pass; checkout-path Nextest passes
  11/11 in 3.746 seconds and doctests pass 1/1 in 1.93 seconds from the primary
  root against the shared cache.
- Done 2026-07-22: a stack-wide sweep removed 13 additional disposable target
  forks and reclaimed 18.465 GiB; no repository-local target directory
  remains. Before the remaining hosted checks, `cargo clean` against the
  canonical `D:/atlas/target` removed 68,854 files and 20.7 GiB. The configured
  shared cache then measured 0 bytes, below the 10-GiB operating budget; the
  final sweep must repeat after any later local gate.
- Residual: audit member workspaces with their own `[profile.*]` or `.cargo`
  sections (helios, hermes, CFDrs, coeus, ritk, mnemosyne). CFDrs currently
  compiles workspace tests at `opt-level = 2`; its dirty peer-owned workspace
  and active full test build preclude an unmeasured profile edit. Re-open that
  member as a separate measured increment after the peer work integrates,
  retaining only runtime- or profiling-justified deviations. Atlas-meta root
  worktrees copy `.cargo/config.toml` and therefore resolve a lane-local target;
  run meta-tool verification from the primary root until a portable route to
  the canonical cache is implemented and tested. One live sample found three
  independent top-level builds, five Cargo processes, and 23 concurrent `rustc`
  processes on a 24-thread/31.7-GiB host. Compare unchanged single- and
  concurrent-build workloads before selecting a global jobs cap; the sample
  proves oversubscription exposure, not an optimal cap.

## ATLAS-BENCH-BUDGET-001 — Wall-clock budgets for benches and examples [patch] — in-progress (enforcement merged; sweep residual)

- Owner: Claude (user-directed claim 2026-07-22); home: tools/criterion-regression (ADR 0024); policy: AGENTS.md engineering_gates "Runtime budgets" + performance_engineering "Benchmark time budget".
- Outcome: no bench binary or CI example exceeds its committed bound; suite time is designed, not emergent.
- Scope: (1) gate smoke — bench binaries run single-iteration (criterion `--test`) under the standard 30s/60s budget; (2) timing runs — per-binary wall-clock bound (default 300s) enforced in the criterion-regression runner/CI; (3) CI-safe examples complete within the test budget as scaled demos; (4) audit the 164 bench files (moirai 47, CFDrs 29, kwavers 22, hermes 12, ritk 10, rest ≤8) against the analytical time model — zero suites declare measurement_time/sample_size today, i.e. all run unbudgeted criterion defaults with sweeps; apply flat sampling for slow iterations, geometric sweeps, smallest regime-exercising inputs; where a single iteration is genuinely slow, profile and optimize the production kernel (farsight), never delete the bench or raise the bound in the offending diff.
- Acceptance: budget enforcement merged in the runner + full-stack bench sweep completes within per-binary bounds; breaches root-caused and fixed or filed with derivation.
- Done 2026-07-22: `enforce-budget` subcommand in tools/criterion-regression — modes smoke (bench single-iteration, 60s), timing (full measurement, 300s), examples (60s), `--bound-seconds`/`--skip` overrides. Compiles unbounded, executes binaries directly (killing cargo would orphan the bench grandchild) with CARGO_TARGET_DIR pinned to the shared target (no minted repo-local target/), fail-closed exit. Validated: themis smoke/timing clean; eunomia timing at 5s bound → breach terminated mid-measurement, exit 1. Gates: clippy pedantic clean, 21/21 nextest, doc clean.
- Residual: full-stack sweep at committed bounds (probe per repo; live peer scopes deferred to their completion), CI wiring per repo workflow convention, and suite resizing per breach (flat sampling, geometric sweeps) or kernel optimization per farsight.
## ATLAS-BUILD-STRUCTURE-001 — Consolidate leaf binaries; compiler-last dev profiles [patch] — in progress

- Owner: Codex `/root`; last-update: 2026-07-23; completed vertical slice:
  `repos/coeus/coeus-ops/tests/**` only. Peer-owned member profiles and other
  repository test trees remain out of scope.
- Aequitas vertical slice: provider PR #35 on source `5428584` splits the
  private derived-unit and dimension-law test leaves, retaining all 38 law
  tests. It is a provider branch awaiting hosted gates; Atlas does not advance
  the Aequitas gitlink until the PR merges.
- Claim: consolidate the 36 flat `coeus-ops` Rust integration-test binaries
  into one hierarchical `tests/ops.rs` harness with `tests/ops/*.rs` modules,
  preserving all 87 test functions and their value-semantic assertions. The
  target-count reduction and test-count parity are the acceptance oracle.

- Policy: AGENTS.md performance_engineering "Debug-tree and compile-time structure" + "Compiler-last optimization order". Monomorphization stays the design default — an instantiation codegens identically to its hand-written equivalent; the debug-tree multiplier is leaf-binary count and duplicate paths, never genericity.
- Evidence 2026-07-22: ~950 leaf binaries stack-wide, each a full link with own incremental cache and PDB — tests/examples per repo: CFDrs 118/66, coeus 110/2, kwavers 94/62, consus 55/0, ritk 28/7, hermes 20/4, moirai 15/22, melinoe 15/1, others <=11. Dev-profile audit: helios declares wildcard `[profile.dev.package."*"] opt-level = 3` (the pattern removed from kwavers in PR #307); kwavers `opt-level = 1` with documented 5-10x PSTD justification is the sanctioned named-and-measured form. The shared incremental tree reached 27,085 session directories and approximately 489 GiB in five days, making leaf-target consolidation and CI `CARGO_INCREMENTAL=0` the next measured size levers.
- Scope: (1) consolidate each repo's tests/*.rs into one-or-few area harness binaries (`tests/<area>/main.rs` with modules) — nextest still isolates per test function in its own process, so coverage and isolation are unchanged while link count, incremental caches, and debug artifacts drop by the file count; worst offenders first (CFDrs, coeus, kwavers, consus, ritk, hermes); (2) merge near-duplicate examples per consolidation_discipline; (3) replace wildcard dev dependency opt raises with named, measured, per-package exceptions (helios first, peer-held — coordinate via board); (4) record per-repo binary-target count and debug-tree size before/after as the acceptance measurement.
- Acceptance: binary-target census reduced and recorded per repo; debug-tree size delta measured against the shared cache; test function count unchanged (no coverage loss); no wildcard dev opt-level overrides remain without a named measured justification.
- Completed vertical slice: Coeus `coeus-ops/tests` moved from 36 flat
  integration targets to one `ops` target with ten operation-family
  directories. The harness exposes 87 integration tests and the exact
  package Nextest run passes 196/196; whole-workspace debug-tree measurement
  remains a later bounded slice.
- Evidence: warning-denied Clippy, package check, format, and diff checks pass
  on Coeus commit `f67789c4`; the 87 harness tests are unchanged by source
  count and all 196 package tests pass. This item is closed for the bounded
  Coeus slice; the broader stack-wide debug-tree delta remains open work.
- Coeus-NN slice complete at provider commit `95bb9090`: the existing
  `nn_tests.rs` harness and its already hierarchical `tests/nn/` modules stay
  intact while the 33 other direct test binaries move behind one `nn_ops`
  harness, preserving the 268 total package tests. The 34 direct test targets
  reduced to 2 (`nn_ops` and `nn_tests`); the exact package run passes
  268/268 with 0 skipped. Whole-workspace debug-tree measurement remains open.
- Coeus-autograd slice complete at provider commit `f8f6d665`: the existing
  `autograd_tests.rs` harness and `tests/autograd/` module tree remain intact
  while the three other direct targets move behind one `autograd_ops` harness.
  The four integration targets reduce to two; the exact package run passes
  94/94 with 0 skipped. Whole-workspace debug-tree measurement remains open.
- Coeus-tensor slice complete at provider commit `49bb5858`: the 13 flat
  integration targets move under six operation-family directories behind one
  `tensor_ops` harness. Locked metadata reports one integration target; the
  source census remains 53 annotated integration tests, and the exact package
  Nextest run passes 58/58 with 0 skipped, including five library unit tests.
  Production tensor code and all leaf test bodies remain unchanged. Whole-
  workspace debug-tree measurement remains open.
- Coeus-sparse slice complete at provider commit `81cb68a6`: the three flat
  integration targets move under conversion, differential, and invariant
  directories behind one `sparse_ops` harness. Locked metadata reports one
  integration target; the exact package Nextest run passes 19/19 with 0
  skipped in 0.713 seconds. Production sparse code and all leaf test bodies
  remain unchanged. Whole-workspace debug-tree measurement remains open.
- Coeus-core slice complete at provider commit `88dfd38f`: the four flat
  integration targets move under storage, dependency-policy, and scalar
  directories behind one `core_ops` harness. Locked metadata reports one
  integration target; the exact package Nextest run passes 21/21 with 0
  skipped, comprising 14 integration cases and seven unchanged library unit
  tests. Production core code and all leaf test bodies remain unchanged.
  Whole-workspace debug-tree measurement remains open.
- Coeus-CUDA slice complete at provider commit `573ad35e`: the three flat
  feature-gated integration targets move under device and fallback directories
  behind one `cuda_ops` harness, retaining the existing nested `tests/cuda/`
  tree through an explicit path. Default Nextest passes 3/3 with 0 skipped;
  all-features check and Clippy pass. All-features executable coverage remains
  host-blocked because the GNU linker cannot find
  `/usr/local/cuda-11.3/lib64/libcuda`. Whole-workspace debug-tree measurement
  remains open.
- Coeus-Python slice complete at provider commit `8851c5f5`: the six flat Rust
  integration targets move under activation, distributed, NN, operation,
  optimizer, and autodiff directories behind one `binding_ops` harness. The
  shared `tests/common` lock module is owned once at the harness root. Exact
  all-features Nextest passes 75/75 with 0 skipped; production PyO3, Python
  parity scripts, and generated artifacts remain unchanged. Whole-workspace
  debug-tree measurement remains open.
- Coeus-WGPU slice complete at provider commit `c507683e`: the two flat
  integration targets now share one hierarchical `wgpu_ops` harness, with
  fused operations under `fusion.rs` and the existing WGPU operation tree under
  `backend/wgpu/`. Exact package Nextest passes 85/85 with 0 skipped; the moved
  source files are content-identical renames and production GPU code is
  unchanged. Whole-workspace debug-tree measurement remains open.
- Coeus-WGPU parity split complete at provider commit `149aadb5`: the 808-line
  multi-family leaf is now a shared oracle manifest plus seven operation-family
  modules. The pre/post source-name census remains 47 unique parity identifiers;
  exact package Nextest passes 85/85 with 0 skipped. Every new leaf is below
  500 lines; production kernels and fixtures are unchanged. Whole-workspace
  debug-tree measurement remains open.
- Coeus-Leto slice complete at provider commit `8d3b9082`: the two flat
  integration targets now share one hierarchical `leto_ops` harness with
  contract and sparse-dispatch operation families. Locked metadata reports one
  integration target; exact package Nextest passes 28/28 with 0 skipped in
  1.064 seconds. The live census is 26 contract tests plus 2 sparse-dispatch
  tests, correcting the prior 26-test tracking claim. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-autograd slice complete at provider commit `24a52be5`: the established
  `tests/autograd/` module tree and standalone operation families now share one
  hierarchical `autograd_ops` harness; the redundant `autograd_tests.rs`
  manifest is removed. Locked metadata reports one integration target instead
  of two; exact package Nextest passes 94/94 with 0 skipped in 1.535 seconds.
  Package check, warning-denied Clippy, format, and diff checks pass. Whole-
  workspace debug-tree measurement remains open.
- Coeus-NN slice complete at provider commit `5c416e12`: the established
  `tests/nn/` module tree and operation-family modules now share one
  hierarchical `nn_ops` harness; the redundant `nn_tests.rs` manifest is
  removed. Locked metadata reports one integration target; exact package
  Nextest passes 268/268 with 0 skipped in 4.463 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-NN tensor parity split complete at provider commit `ee5be32f`: the
  1,317-line multi-family parity leaf is now a shared assertion manifest plus
  attention, convolution, embedding, linear/normalization, losses, and
  regularization operation-family modules. The pre/post source-name census
  remains 11 unique parity test functions; exact package Nextest passes 268/268
  with 0 skipped in 2.816 seconds. The largest new leaf is `attention.rs` at
  664 lines; the other five leaves are below 250 lines. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-CUDA parity split complete at provider commit `abe9211d`: the live
  1,672-line multi-family parity leaf is now a shared oracle manifest plus
  seven operation-family modules. The pre/post source-name census remains 29
  unique parity test functions; every new leaf is below 500 lines, with
  `convolution.rs` the largest at 365 lines. Default package Nextest passes
  3/3 with 0 skipped; default and `--features cuda` package checks and
  warning-denied Clippy pass. Feature-enabled Nextest cannot link because
  `x86_64-w64-mingw32-gcc` cannot find `-lcuda` while searching
  `/usr/local/cuda-11.3/lib64/`; no live CUDA parity execution is claimed.
  Whole-workspace debug-tree measurement remains open.
- Coeus-Python operation binding split complete at provider commit `0d8784c1`:
  the live 3,160-line `binding_tests_ops.rs` leaf is now fourteen
  operation-family leaves with nested NN functional and module directories.
  The pre/post source census remains 61 unique test functions and all 61
  extracted Rust function bodies compare equal. The largest test-family leaf is
  `reductions.rs` at 391 lines; every leaf is below 400 lines. Exact package
  Nextest passes 75/75 with 0 skipped in 8.079 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Production PyO3,
  Python parity scripts, and generated artifacts remain unchanged. Whole-
  workspace debug-tree measurement remains open.
- Coeus-dist distributed-contract split complete at provider commit `c7838d90`:
  the live 1,262-line `dist_tests.rs` leaf is now one `dist_ops` manifest with
  local and TCP transport subtrees, separated into collective, reduction,
  invalid-input, and mesh-boundary families. The pre/post source census remains
  64 unique test functions, all 64 `#[test]` attributes remain present, and
  all 64 extracted Rust function bodies compare equal. The largest new leaf is
  `distributed/tcp/errors/collective.rs` at 464 lines; every leaf is below 500
  lines. Exact package Nextest passes 64/64 with 0 skipped in 0.444 seconds,
  with no slow tests. Package check, warning-denied Clippy, format, and diff
  checks pass. Whole-workspace debug-tree measurement remains open.
- Coeus-NN loss-contract split complete at provider commit `37bf8d9b`:
  the live 902-line `nn_loss_tests.rs` leaf is now a nested manifest with
  binary, classification, distance, and distribution operation families. The
  pre/post source census remains 24 unique test functions and all 24 extracted
  Rust function bodies compare equal. The largest new leaf is `distance.rs` at
  315 lines; every new leaf is below 500 lines. Exact package Nextest passes
  268/268 with 0 skipped in 2.270 seconds. Package check, warning-denied
  Clippy, format, and diff checks pass. Production NN code, fixtures, and
  tolerances remain unchanged; whole-workspace debug-tree measurement remains
  open.
- Coeus-optim contract-family split complete at provider commit `b27d492f`:
  the live 676-line `optim_tests.rs` leaf is now one `optim_ops` manifest with
  optimizer, scheduler, convergence, and gradient-clipping family modules.
  The pre/post source census remains 20 unique test functions and all 20
  extracted Rust function bodies compare equal. Locked metadata reports one
  `optim_ops` integration target. The largest new leaf is `convergence.rs` at
  239 lines; every new leaf is below 250. Exact package Nextest passes 20/20
  with 0 skipped in 0.188 seconds. Package check, warning-denied Clippy,
  format, and diff checks pass. Production optimizer code and all test oracles
  remain unchanged; whole-workspace debug-tree measurement remains open.
- Coeus-NN extended activation split complete at provider commit `d800be8c`:
  the live 648-line `act_extended_tests.rs` leaf is now one `act_extended`
  manifest with piecewise, parameterized, module-smoke, and smooth families.
  The pre/post source census remains 17 unique test functions and all 17
  extracted Rust test function bodies compare equal. The largest new leaf is
  `piecewise.rs` at 354 lines; every new leaf is below 360. Exact package
  Nextest passes 268/268 with 0 skipped in 3.155 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Production NN code,
  fixtures, formulas, and tolerances remain unchanged; whole-workspace
  debug-tree measurement remains open.
- Coeus-Leto contract-family split complete at provider commit `97d94566`:
  the live 505-line `leto_ops/contract.rs` leaf is now a manifest with
  arithmetic, reductions, matmul, layout, and accumulation families under
  `coeus-leto/tests/leto_ops/contract/`. The pre/post source census remains
  26 unique contract tests and all 26 extracted Rust test function bodies
  compare equal. The largest new leaf is `layout.rs` at 197 lines; every new
  leaf is below 200 lines. Locked metadata reports one `leto_ops` integration
  target. Exact package Nextest passes 28/28 with 0 skipped in 0.325 seconds.
  Package check, warning-denied Clippy, format, and diff checks pass.
  Production Leto dispatch code and test oracles remain unchanged; whole-
  workspace debug-tree measurement remains open.
- Next claimed slice: run a fresh structural audit of the remaining Coeus test
  tree and take the next real family-boundary increment, if a live leaf exceeds
  the hierarchy trigger without violating test cohesion.

## ATLAS-PUBLISH-001 — OIDC publish pipelines and Pages alignment [patch] — in progress

- Policy: AGENTS.md engineering_gates "Publish pipelines". Wiring is agent work; registry-side toggles are user actions.
- Scope: (1) crates.io — add tag-triggered, environment-gated trusted-publishing workflows (`rust-lang/crates-io-auth-action`, `id-token: write`) to publishable stack crates, dependency-ordered with `cargo package` dry-run and semver gates; record per-crate "enforce trusted publishing" as a user checklist once each pipeline is green (disables token publishing registry-side). (2) PyPI — for the Python-binding crates, maturin-action matrix (manylinux2014 floor, `--compatibility pypi`, abi3 where the surface permits, sdist) with install/import/pytest wheel smoke before upload via the PyPI trusted-publisher flow. (3) Books — align CFDrs/kwavers/helios book workflows to the artifact flow (build + `mdbook test` → upload-pages-artifact → deploy-pages) if any still push a gh-pages branch or skip the test gate; new books inherit the same workflow.
- Acceptance: no long-lived registry token referenced in any CI secret; each wired pipeline dry-run green; book deployments artifact-based with the test gate; user-action list (registry enforcement toggles) recorded on the board.

### ATLAS-PUBLISH-001-CFDRS-PYPI — Add CFDrs abi3 PyPI trusted-publishing caller [patch] — in progress

- Owner: Atlas coordinator; claimed 2026-08-18.
- Scope: `repos/CFDrs/.github/workflows/python-release.yml`,
  `repos/CFDrs/crates/cfd-python/tests/`, the binding version surface, and the
  shared root `.github/workflows/python-wheels.yml` release-distribution
  contract. The caller uses the shared workflow at the exact Atlas graph
  revision and the provider's declared `cfd_python` import surface.
- Acceptance: the release-tag caller builds abi3 wheels with the manifest's
  PyO3 floor plus one validated source distribution, installs/imports the
  wheel, runs bounded value-semantic Python tests, and hands validated release
  artifacts to PyPI Trusted Publishing; no registry token or untested
  import-only path is introduced.
- Non-goals: registry-side trusted-publisher enforcement, a local publish,
  release/version changes, and unrelated CFDrs Rust or workflow cleanup.
- Verification: inspect the workflow's pinned actions and exact `atlas-ref`,
  run provider formatting and focused Rust checks, compile the binding test
  contract where the local Python/maturin toolchain permits, and validate the
  workflow statically.
- Provider implementation status: CFDrs commit `e7a1c9e8` on PR #360 already
  ships the abi3 typed boundary and GIL-release changes. Provider-local
  evidence is a release wheel containing `cfd_python.pyi` and `py.typed`,
  installed-wheel pytest `4/4`, strict mypy consumer validation, and complete
  runtime export coverage. Follow-up commit `a5a92bfc` pins the caller's
  `atlas-ref` to Atlas `ad22ec5e`. Hosted exact-head verification, merge, and
  post-merge evidence remain open; the Atlas CFDrs gitlink is unchanged.

### ATLAS-HELIOS-BOOK-TEST-002 — Enable Helios `mdbook test` in the shared Pages caller [patch] — done 2026-08-17

- Owner: Atlas coordinator; scope is the clean Helios workflow caller only.
- Evidence: clean-lane source `30a842cd7d7dee5ca9bda3e04e97fad966cebeee`
  enables the shared caller's `mdbook-test` input and merges at Helios default
  `679402ae166ce2b227d8d629bab877f1dcc45131`.
- Acceptance: met. The exact clean Helios book and hosted Pages build pass;
  hosted Rust, Python, and benchmark checks also pass. The external
  `recurseml/analysis` error remains report-only.
- Non-goals: peer-owned Helios source edits, book prose, generated figures,
  and the Kwavers/CFDrs caller sub-scopes.
- Re-open trigger: a book sample failure, shared workflow contract change, or
  provider caller that disables the test input.

## ATLAS-PUBLISH-001-BOOK-MDBOOK-TEST-001 — Cross-book `mdbook test` gate alignment [patch] — peer-coordinated (filed by Session 18)

Coordinator-owned evidence record (this entry) under
eer-coordinated execution: kwavers peer on branch
`codex/kwavers-book-migration-eviction` (peer mid-flight on
`ATLAS-BOOK-002` eviction). CFDrs peer on `main` branch, 1 ahead of
`origin/main f04b1d75` (autest sub-task, see
`ATLAS-CFDRS-COEQ-BLOCKER-1`). Helios peer on
`origin/main 433ddb6`. Each member-repo peer owns their own workflow
`book-pages.yml`; coordinator cannot edit those files per
`concurrent_agents` disjoint-scope primitive — this entry surfaces the
shared gap and per-repo sub-scopes so each peer claims the disjoint slice
against their own repo. Coordinator verification of the shared gap was
performed against each repo's `origin/main` HEAD.

- Policy: AGENTS.md engineering_gates "Publish pipelines" — book
  workflows run build + `mdbook test` → `upload-pages-artifact` →
  `deploy-pages` (the test gate is the test-suite coverage for
  documentation samples, preventing rotted non-compiling example code
  from deploying).
- Discovery evidence (verified at Session 18 via `git show
  origin/main:.github/workflows/book-pages.yml` on each repo):
  - **kwavers** (`origin/main c19134ec`): steps `Configure Pages`,
    `Install mdBook`, `Build book` (runs `mdbook build docs/book`
    only), `Upload Pages artifact`, `Deploy to GitHub Pages`. No
    `mdbook test` step.
  - **CFDrs** (`origin/main f04b1d75`): identical step shape
    (`Configure Pages` → `Install mdBook` → `Build book` running
    `mdbook build` only → `Upload Pages artifact` → `Deploy to GitHub
    Pages`). No `mdbook test` step.
  - **helios** (`origin/main 433ddb6`): identical step shape. No
    `mdbook test` step. (Cited as residual (a) in
    `ATLAS-HELIOS-BOOK-001` Session 18 closure.)
  - All three deploy via `actions/upload-pages-artifact@v4` →
    `actions/deploy-pages@v4` with `pages: write` + `id-token: write`
    on the `deploy` job and deploy gated on
    `github.event_name != 'pull_request'` (main-only). The artifact
    flow is already compliant; only the `mdbook test` step is missing.
- Outcome: each per-repo peer-coordinated sub-slice lands one PR
  inserting a `Build book`→`Test book samples` step (running
  `mdbook test docs/book`) between `Install mdBook` and
  `Upload Pages artifact`, fail-closed on doctest failure. The (1)/(2)
  crates.io/PyPI scopes of `ATLAS-PUBLISH-001` remain separate and
  unowned — this sub-slice addresses only the (3) Books test-gate
  gap. Per-repo sub-scope (peer-coordinated):
  (a) **repos/kwavers/.github/workflows/book-pages.yml** — peer-kwavers
      holds active eviction branch (`codex/kwavers-book-migration-eviction`,
      1 ahead of `origin/main c19134ec`); the `mdbook test` step landing
      is complementary to eviction (examples must compile for `mdbook
      test` to pass, and eviction is removing the migration-reference
      examples that are least doctest-fit), so sequencing eviction first
      is the cleanest order. Awaiting peer eviction merge to `origin/main`.
  (b) **repos/CFDrs/.github/workflows/book-pages.yml** — peer-CFDrs
      on `main` ahead 1 of `origin/main f04b1d75`; lands after the
      `ATLAS-CFDRS-COEQ-BLOCKER-1` workspace-restore + check-figures
      re-verification so the local `mdbook test` pre-flight is backed by
      a fully-resolved Cargo graph (the coeus-core path-dependency
      gap currently stops local cargo metadata resolution).
  (c) **repos/helios/.github/workflows/book-pages.yml** — peer-helios
      at `origin/main 433ddb6`, book content ready to test. No known
      pre-requisite for the `mdbook test` step landing; cleanest
      per-repo increment of the three.
- Acceptance: each `book-pages.yml` carries a `mdbook test docs/book`
  step running doctests on committed sample code; book deploy still
  artifact-based with the test gate; user-action list (registry
  enforcement toggles) recorded on the board remains the same.
- Risk/change class: `[patch]` CI-only; no production-code delta.
- Dependencies: ATLAS-PUBLISH-001 (parent),
  ATLAS-BOOK-002 (kwavers eviction sub-scope ordering);
  ATLAS-CFDRS-COEQ-BLOCKER-1 (CFDrs cargo-graph restore).
- Evidence limit: workflow-step inspection on each `origin/main`;
  no performance claim, no production-code delta.
- Refs: backlog.md#ATLAS-PUBLISH-001 (parent slice),
  backlog.md#ATLAS-BOOK-002 (kwavers peer eviction),
  backlog.md#ATLAS-HELIOS-BOOK-001 (Session 18 closure residual (a)),
  backlog.md#ATLAS-CFDRS-COEQ-BLOCKER-1 (CFDrs workspace restore).

## Session 17 closure (2026-07-23) — ATLAS-LETO-OPS-SPARSE-LU-001 → ✅ closed

- Owner: atlas-meta coordinator (codex agent); status flipped todo → ✅ closed.
- Outcome: real CSC sparse LU + partial-pivoting numeric phase in leto-ops
  landed at leto `origin/main` `687b670` via PR #74 squash-merge
  (`refactor(leto-ops): Remove ndarray/nalgebra, native iterative solvers
  (LETO-NDARRAY-BOUNDARY-1) (#74)`).
  The PR diff (41 files) bundled the ndarray/nalgebra dev-dep removal (peer
  origin-main HEAD `9346413` declared no production deps on ndarray/ndarray-rand/
  nalgebra; only parity examples consumed them) AND the in-place upgrade of
  `SparsLuSolver` to the real algorithm class.  Public surface preserved:
  `SparseLuSolver::solve_view`, `CscMatrix`, `CsrMatrix`, `CooMatrix`, and the
  re-exported `factor_numeric` / `factor_symbolic` / `NumericLu` API paths.
- Algorithm spec (matches ADR 0031 Option A): symbolic factorization is the
  sequential left-looking Gilbert/Peierls reach over CSC, computing the
  static L/U pattern (L rows strictly `> j`, U rows `≤ j` per column j) under
  natural column ordering for v0.40.0; numeric factorization is the
  slot-indexed left-looking phase with partial-pivoting row swaps against
  `row_perm[slot] = original row` (matches the dense
  `LuDecomposition::pivots` convention so downstream CFDrs
  `DirectSparseSolver` composes unchanged); solve =
  `P·A·x = L·U·x = P·b` ⟺ forward sub `Ly = Pb` then back sub `Ux = y`.
- Density-gated dispatch (per ADR 0031): `SparseLuSolver` carries a
  `small_switch = 32` and `density_threshold = 0.1` pair; small or near-dense
  matrices route to a dense-fallback path; large sparse matrices route to
  the new symbolic→numeric sparse path.
- Verification evidence (Windows ucrt64, rustc 1.95.0, eunomia
  https://github.com/ryancinsight/eunomnia#f6cd644b):
  - `cargo check -p leto-ops --tests` ✅ clean (Finished in 2m 15s).
  - `cargo nextest run --no-fail-fast -p leto-ops` ✅ 339/339 pass in 3.17s
    (well under the 30s slow-timeout hard cap; no threshold relaxation, no
    test shrinkage).
  - `cargo test --doc -p leto-ops` ✅ 11/11 pass in 54.64s.
  - Sparse-LU-targeted suite ✅ 16/16 pass:
    `factor_poisson_1d_laplacian_n16_roundtrip` 0.064s,
    `factor_banded_5_diagonal_n32` 0.026s,
    `factor_random_sparse_n64_diff_dense` 0.252s,
    `sparse_path_routes_correctly_for_tridiagonal_n64` 0.269s,
    `factor_f32_generic` 0.051s,
    `singular_matrix_yields_storage_error` 0.240s,
    `solver_is_generic_over_f32` 0.071s, plus 9 inherited solver-routing tests.
  - Differential cross-check: `factor_random_sparse_n64_diff_dense` asserts
    value-semantic equivalence between sparse and dense LU on a randomly
    populated 64×64 matrix at residual < ε (not existence-only).
- Residual / not-covered-in-this-closure (per ADR 0031 Consequences):
  (a) AMD (Approximate Minimum Degree) ordering deferred to
      `ATLAS-LETO-OPS-AMD-ORDERING-001` [patch] — natural ordering ships for
      v0.40.0; AMD ~300-line impl exceeds this session's context budget and
      a partial implementation would risk numerical defects per ADR 0031
      "AMD scope risk".
  (b) CFDrs `DirectSparseSolver` migration to the landed
      `SparseLuSolver::solve_view` is the follow-up
      `ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001` — depends on aequitas pin
      coherence and a leto bump at CFDrs; not in scope for Session 17.
  (c) Local clippy `-D warnings` against the FULL leto workspace cannot run
      clean on this coordinator's working tree because peer's untracked
      uncommitted sibling verticals
      (`crates/leto-ops/src/application/{diff,interpolation,quadrature}/`)
      contain `assign_op_pattern` and `complex_type` lint failures. PR
      #74's CI status (both `recurseml/analysis` post-push and
      `CodeRabbit`) was CLEAN before squash-merge; the merged commit's
      leto-ops scope is clippy-pedantic clean modulo peer-held untracked
      files not in the merged tree.
- Concurrent-agent record: peer session active on the same `codex/leto-real-sparse-lu`
  working tree during this closure, creating untracked siblings for diff/
  interpolation/ quadrature operation families (ts 21:53-22:02).  Per
  `concurrent_agents` assist-ladder rule: peer files skipped, not collided with.
  Coordinator scope-strictly-committed only `sparse/lu_numeric.rs` and
  `sparse/lu_symbolic.rs` (doctest-fixture correction + rustfmt-only reflow of
  pre-existing `for ... take().skip()` chains); peer's `Cargo.{lock,toml}`,
  `lib.rs`, `application/mod.rs`, `application/linalg/mod.rs`, and the new
  `diff/`/`interpolation/`/`quadrature/` untracked modules remained unstaged.
- Gitlink-state: atlas-meta's `repos/leto` gitlink advances to
  `687b67079c4e122264c17fd2eb3fd850d876a39f` in the same commit that
  synchronizes this backlog entry and ADR 0031's status flip.
- Refs: backlog.md#CFDRS-PERF-SLOW-001 (Session 13 upstream-cause filing),
  backlog.md#ATLAS-LETO-OPS-SPARSE-LU-001 (this item), ATLAS-LETO-OPS-AMD-ORDERING-001 [patch] (new follow-up below).

## ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 — Migrate CFDrs direct_solver to SparseLuSolver::solve_view [minor] — partial closure (2026-07-23 Session 17: doc-migration slice landed via PR #316 `5ac713b3`); cfd-3d end-to-end re-profile and direct_threshold re-evaluation deferred

Filed as follow-up per Session 17 closure of `ATLAS-LETO-OPS-SPARSE-LU-001`.
Now that real sparse LU + partial pivoting has landed at leto `687b670`,
the CFDrs downstream consumer should adopt the upstream-native solver.

- Owner: unclaimed. Depends on CFDrs leto version bump (currently
  `aequitas = { path = "../aequitas" }` and leto path-pinned at
  atlas-meta level).
- Outcome: replace `crates/cfd-math/src/linear_solver/direct_solver.rs`
  body with calls to `leto_ops::application::sparse::SparseLuSolver::solve_view`
  on real CSC-typed inputs; remove any `with_direct_threshold(512)`-
  regime mats that exist purely to route medium saddle-point FEM
  matrices to GMRES (Brezzi 1974 indefinite saddle — sparse LU is now
  correct for it, not a misnomer).
- Acceptance: (1) CFDrs `crates/cfd-math/src/linear_solver/direct_solver.rs`
  no longer documents itself as "atlas-native sparse direct solver backed
  by dense partial-pivoting LU" (cf. the doc-runtime contradiction),
  (2) CFDrs cfd-3d suite verifies end-to-end (`validate_poiseuille_flow`
  PR #311 root-caused fix continues to PASS under the new upstream
  matrix-as-sparse path; re-profile runs `<1s` per Session 13 closure
  baseline), (3) `direct_threshold` parameter either removed from the
  CFDrs FEM solver or re-evaluated with new evidence (filed as a follow-up
  board item against CFDrs perf, not this slice).
- Risk/change class: `[minor]` (additive public-API call-site
  migration; no break to CFDrs public surface).
- Dependencies: leto version bump at CFDrs; aequitas pin coherence
  (Session 12 documented the eunomia dual-source-ID recurring risk
  when consumers pin eunomia differently; align all atlas consumers
  on URL-only form).
- Refs: backlog.md#ATLAS-LETO-OPS-SPARSE-LU-001 (closed),
  leto origin/main `687b670`.

## ATLAS-HELIOS-BOOK-001 — Helios multichapter mdBook from examples [minor] [arch] — ✅ closed (2026-07-24 Session 18 — peer-delivered)

Per user Session 17 prompt: "Similar to kwavers it would be good for
helios and cfdrs to also create a well-organized, multichapter book
from examples." kwavers book template is the canonical reference.
Peer-helios delivered the book across PRs landing at `origin/main
433ddb6` (atlas-meta gitlink unchanged: it is already at this merged
origin commit). Coordinator closure is evidence-only — no member-repo
file edits by this agent.

- Owner: peer-helios (delivered); atlas-meta coordinator (this closure
  flips the backlog status and records the verification matrix).
- Outcome: full multichapter mdBook at 
  `repos/helios/docs/book/` with 8 Parts across 37 chapters + 4
  appendices + BOOK_ORGANIZATION forward roadmap; 18 example
  markdown files under `examples/`; 7 deterministic SVG figures
  + `MANIFEST.json` byte-determinism registry under `figures/`;
  `book.toml` configured with `/helios/` site-url + MathJax; README
  links published book at https://ryancinsight.github.io/helios/.
  Per-chapter content follows the kwavers-standard Domain-book
  contract: governing equations → numerics → CLI/API mapping →
  worked examples with deterministic figures, with each chapter
  carrying an H1 `# Chapter N — …` + `## Further Reading` backlink
  + SUMMARY.md navigation (verified by sampling across Parts I–VIII).
- Acceptance: 
  (a) `mdbook build docs/book` exits 0 locally at helios 
      `433ddb6` (verified via `mdbook v0.5.4`, target written to 
      `target/book/helios/index.html`). ✅
  (b) Every SUMMARY.md entry maps to a committed chapter stub with 
      H1 + "Further Reading" backlink (verified sample across 
      `foundations`, `dose_attenuation`, `planning_mlc`, 
      `workflow_tomotherapy`, `gpu_dose`, `migration_arrays`). ✅
  (c) Book deploys to GitHub Pages through the artifact flow 
      (`.github/workflows/book-pages.yml`: `actions/upload-pages-artifact@v4` 
      → `actions/deploy-pages@v4`, `pages: write` + `id-token: write`
      on the `deploy` job, deploy gated on `github.event_name != 
      'pull_request'`). ✅
  (d) Cross-book CI invariant gate (atlas-meta `.github/workflows/docs.yml`
      `docs-invariant` job) runs the dead-link detector + `mdbook build`
      on all three books — green. ✅
- Risk/change class: `[minor]` documentation scaffolding + `[arch]`
  (introduces the mdBook workflow wired per AGENTS.md publish
  pipelines; interacts with the parity_artefacts INDEX manpages).
- Dependencies: ATLAS-PUBLISH-001 OIDC trusted-publishing alignment
  for helios book (RESIDUAL — see below); kwavers book GitHub Pages
  workflow template.
- Refs: backlog.md#ATLAS-BOOK-002 (kwavers), backlog.md#ATLAS-CFDRS-BOOK-MDBOOK-DUPLICATES-1.
- Residual / not-covered-in-this-closure (peer-coordinated, NOT claimed
  by Session 18 — coordinator cannot edit member-repo workflow files per
  concurrent_agents disjoint-scope primitive):
  (a) ATLAS-PUBLISH-001 acceptance item: `repos/helios/.github/workflows/
      book-pages.yml` runs `mdbook build` but does NOT run `mdbook test` 
      (engineering_gates publish-pipelines require both). Peer-helios
      owns `book-pages.yml`; flagged as a peer-coordinated sub-slice of
      ATLAS-PUBLISH-001.
  (b) ATLAS-BOOK-002 acceptance item: the Part VIII — Atlas Stack
      Integration (Migration Reference) section in 
      `repos/helios/docs/book/SUMMARY.md` (chapters 26–37) is in-scope
      for the cross-book migration-content eviction under ATLAS-BOOK-002.
      Peer-kwavers holds the eviction branch; this residual is filed as 
      a helios-side peer-coordinated sub-slice of ATLAS-BOOK-002.
  (c) Atlas-meta helios gitlink stays at `433ddb6` (== `origin/main`); 
      no gitlink advancement is required or performed by this closure.
      Causal chain: peer-delivered → published on origin → coordinator
      verifies → backlog status flips. No regression surface.


## Session 17 partial closure (2026-07-23) — ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 → partial closure

Coordinator (Session 17 follow-up) landed the doc-comment migration of
`crates/cfd-math/src/linear_solver/direct_solver.rs` to reflect the
real CSC sparse LU per ADR 0031 + leto origin/main `687b670` (PR #74
squash-merge).

- **CFDrs PR**: ryancinsight/CFDrs#316 — title
  "docs(cfdrs-math): Migrate direct_solver doc to ADR 0031 real sparse LU
  (ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 partial)" — squash-merged as
  `5ac713b3fdf5fd45dbd295f3887c6f58b88c63f8` on CFDrs origin/main at
  2026-07-24T03:43:21Z.
- **Diff surface**: +25/-6 in
  `crates/cfd-math/src/linear_solver/direct_solver.rs` — module doc
  rewrite + `ordering` field doc correction + convergence composition
  with peer's pending `..Default::default()` adaptation to the
  upstream `SparseLuSolver` struct expansion (`small_switch` +
  `density_threshold` fields per ADR 0031).
- **Doc claim corrected**: the pre-merge module doc claimed the
  atlas-native solver was "backed by dense partial-pivoting LU" — that
  misnomer was filed for the Session 13 `CFDRS-PERF-SLOW-001` timeout
  closure root cause; it is now stale per ADR 0031 since leto PR #74
  landed the real CSC sparse LU (symbolic = sequential left-looking
  Gilbert–Peierls reach per Davis 2006 §6.1; numeric = slot-indexed
  left-looking with row_perm[slot]=original-row matching dense
  `LuDecomposition::pivots`; density-gated dispatch `small_switch=32`,
  `density_threshold=0.1` in `SparseLuSolver`).
- **Safety net preserved**: the CFDrs-side `dense_threshold=1024`
  retry at `DirectSparseSolver::retry_dense_or_error` is preserved as
  the orthogonal catch case for the `max_size`-cap + small-`n`
  user-intent safety net; NOT a duplicate of the upstream internal
  fallback (which handles only `NumericalBreakdown` mid-sparse-path).

Gitlink: atlas-meta `repos/CFDrs` advances from `1b2c901` to
`5ac713b3` (submodule local working tree left at local main HEAD
`354266c0` with peer's WIP unmodified per concurrent_agents
preservation; the gitlink records the squash-merged origin/main tip).

Refs: backlog.md#ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 (above; this
entry closes the partial slice),
docs/adr/0031-leto-ops-real-sparse-lu.md (atlas-meta, Accepted),
leto PR #74 squash-merged as `687b670` (origin/main),
CFDrs PR #316 squash-merged as `5ac713b3` (origin/main).


## Session 18 closure (2026-07-24) — ATLAS-HELIOS-BOOK-001 → ✅ closed

- Owner: peer-helios (delivered the book across multiple PRs landing at
  `origin/main 433ddb6`); atlas-meta coordinator (this Session 18
  closure records the verification matrix and flips the backlog status
  from `todo` to `✅ closed`). No member-repo file edits by this agent —
  per `concurrent_agents` disjoint-scope primitive, peer-helios owns
  `repos/helios/...` files.
- Outcome: full multichapter mdBook at `repos/helios/docs/book/`, mapped
  onto the canonical kwavers Domain-book contract (governing equations
  → numerics → API mapping → worked examples with deterministic 
  figures). Spec verified via local inspection of `origin/main`:
  - `docs/book/SUMMARY.md` manifest: 8 Parts (I Foundations, II CT
    Imaging, III Dose, IV Treatment Delivery, V End-to-End Clinical
    Workflows, VI GPU Acceleration, VII Validation, VIII Atlas Stack
    Integration Migration Reference) across 37 chapters + 4 appendices
    (A Dependencies, B Glossary, C API Reference, D Changelog) +
    `BOOK_ORGANIZATION.md` forward roadmap.
  - 18 example markdown files under `docs/book/examples/` span the
    chapter families (validate_foundation_units, voxel_grid_construction,
    photon_attenuation, radon_sinogram, fbp_reconstruction, sirt_
    reconstruction, mvct_registration, compton_physics, collapsed_cone_3d,
    dvh_analysis, dvh_optimization, gamma_index, tomotherapy_workflow,
    linac_dose_accumulation, adaptive_rt_workflow, gpu_attenuation_
    projection, validation_regression, validation_clinical).
  - 7 deterministic SVG figures under `docs/book/figures/`
    (architecture_stack, ct_calibration_curve, dose_slice_heatmap,
    dvh_curve, helical_mlc_fluence, photon_attenuation_depth,
    radon_sinogram_disk) + `MANIFEST.json` byte-determinism registry.
  - `docs/book/book.toml` configured with `/helios/` site-url + MathJax.
  - `README.md` carries the canonical `[Published Helios book]
    (https://ryancinsight.github.io/helios/)` link.
- Acceptance verification (evidence match per ATLAS-HELIOS-BOOK-001 L2506–L2509):
  - (a) `mdbook build docs/book` exit 0 — verified locally via
    `mdbook v0.5.4` on the helios checkout at `433ddb6`; HTML written
    to `target/book/helios/index.html`. ✅
  - (b) SUMMARY.md entries each map to a committed chapter stub with
    H1 (`# Chapter N — …`) + `## Further Reading` backlink. Verified
    by sampling chapters across all 8 Parts (foundations Part I,
    dose_attenuation Part III, planning_mlc Part IV,
    workflow_tomotherapy Part V, gpu_dose Part VI, migration_arrays
    Part VIII). ✅
  - (c) Book deploys to GitHub Pages through the artifact flow.
    `repos/helios/.github/workflows/book-pages.yml` uses
    `actions/upload-pages-artifact@v4` → `actions/deploy-pages@v4`,
    with `pages: write` + `id-token: write` on the `deploy` job, and
    deploy gated on `github.event_name != 'pull_request'` (main-only). ✅
  - (d) Cross-book CI invariant gate (atlas-meta `.github/workflows/
    docs.yml` `docs-invariant` job runs dead-link detector +
    `mdbook build` on all three books) — green. ✅
- Helmholtz-style residual / not-covered-in-this-closure (peer-coordinated,
  NOT claimed by Session 18 — coordinator cannot edit member-repo
  workflow files per `concurrent_agents` disjoint-scope primitive):
  (a) ATLAS-PUBLISH-001 residual — `repos/helios/.github/workflows/
      book-pages.yml` runs `mdbook build` but does NOT run `mdbook test`.
      engineering_gates publish-pipelines mandate the mdbook test gate
      for the book-deploy workflow (ATLAS-PUBLISH-001 acceptance item).
      Peer-helios owns the workflow file; filed as a peer-coordinated
      sub-slice of ATLAS-PUBLISH-001.
  (b) ATLAS-BOOK-002 residual — the Part VIII Atlas-Stack Integration
      (Migration Reference) section in `repos/helios/docs/book/SUMMARY.md`
      (chapters 26–37) is in-scope for the cross-book migration-content
      evictionunder ATLAS-BOOK-002 (peer-kwavers holds the active
       eviction branch). Filed as a helios-side peer-coordinated
      sub-slice of ATLAS-BOOK-002.
  (c) Atlas-meta `repos/helios` gitlink stays at `433ddb6` (== `origin/main`).
      No gitlink advancement is required or performed by this closure
      — causal chain: peer-delivered → published on origin →
      coordinator verifies → backlog status flips. No regression
      surface.
- Concurrent-agent record: prior-session coordinator work committed as
  `04dee5c "docs(atlas): Close Aequitas metric audit gaps"` advanced the
  book-CI verification slice (now `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER`
  status `in-progress` after HELIOS PR #31 root-cause analysis). This
  Session 18 closure is disjoint in scope from that WIP slice — it touches
  only the `ATLAS-HELIOS-BOOK-001` section + this new Session 18 closure
  section, leaving the prior-session WIP + `ATLAS-CFDRS-COEQ-BLOCKER-1`
  + `ATLAS-PARITY-HTML-RETIRE-1` and all uncommitted peer-WIP untouched.
- Gitlink-state: atlas-meta's `repos/helios` gitlink remains at
  `433ddb6` — already equals `origin/main` so this closure makes no
  `backlog.md`-internal gitlink advancement. Diff signature: `backlog.md`
  only (no `.gitmodules`, no `gap_audit.md`, no member-repo path).
- Refs:
  - backlog.md#ATLAS-HELIOS-BOOK-001 (this closure)
  - backlog.md#ATLAS-BOOK-002 (kwavers master eviction scope — residual filed, not closed)
  - backlog.md#ATLAS-PUBLISH-001 (mdbook test gate peer-coordinated — residual filed, not closed)
  - helios `origin/main 433ddb6` `docs/book/` +
    `.github/workflows/book-pages.yml` + `README.md` (artifact evidence)
  - https://ryancinsight.github.io/helios/ (published book URL)

## Session 19 closure (2026-07-24) — ATLAS-AEQUITAS-001 gitlink advance + criterion-gate continuous verification

- Owner: atlas-meta coordinator (this Session 19 closure records the
  gitlink advance and the criterion-gate re-audit). No member-repo
  files touched per `concurrent_agents` disjoint-scope primitive.
- Outcome:
  (1) ATLAS-AEQUITAS-001 above — atlas-meta gitlink for
      `repos/aequitas` advances from `b86a55d` to `19fc384` (origin/main
      HEAD). Three peer commits, all CI-green via `gh api`. Linear
      advance (no merge-bubble), `[minor]` additive.
  (2) ATLAS-BENCH-BUDGET-001 continuous-verification re-audit of the
      meta-owned `tools/criterion-regression` tool:
      - `cargo check --all-targets` Finished clean.
      - `cargo clippy --all-targets -- -D warnings` clean (pedantic +
        `clippy::unwrap_used`).
      - `cargo fmt --check` clean.
      - `cargo nextest run --no-fail-fast` 21/21 pass (max 0.451s;
        well under the 30s slow / 60s terminate budget).
      - `cargo test --doc` 2/2 pass.
      The tool remains green for peer consumption; the residual
      full-stack sweep (164 benches across moirai/CFDrs/kwavers/hermes/
      ritk + per-repo CI wiring per `ATLAS-BENCH-BUDGET-001`) stays
      deferred until the live peer scopes integrate.
  (3) Stale-claim sweep + origin-sync-first per `concurrent_agents`:
      all five drifted gitlinks (CFDrs, coeus, aequitas, consus, kwavers)
      audited via authenticated `gh api` panel dispatched as a parallel
      subagent panel inspecting per-repo states via `git ls-remote`,
      `git --git-dir`, and authenticated `gh api` check-runs / status
      queries. Session 19 takes the single evidence-backable advance
      (aequitas); the other four are correctly rejected above with the
      recorded reason.
- Concurrent-agent record: peer-helios at `origin/main 433ddb6`
  (unchanged from Session 18 closeout). Peer-CFDrs at `origin/main
  99318bc` (advanced past Session 18 but CI red on check-figures job —
  same `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1` residual; the Venturi metric
  closure `ATLAS-CFDRS-PERF-045` already recorded separately on main).
  Peer-mnemosyne already integrated per Session 18's gitlink advance.
  Peer-aequitas freshly advanced now. Other peer activity: peer-leto at
  `origin/main 687b670` (stable — sparse LU landed Session 17). Peer
  kwavers eviction remains local-only (PR #325 DIRTY, eviction branch
  unpushed). Stale-claim sweep used the actual peer's published origin
  + `gh api` for CI conclusions; no speculative merges or assumptions
  about peer intent beyond their published state.
- Diff signature: `repos/aequitas` gitlink only (index-staged) + this
  backlog.md section. No `.gitmodules` URL change, no `gap_audit.md`
  edit (currency-current via Session 18 closeout), no member-repo files,
  no `tools/*` build (the continuous-verification re-audit ran
  read-only against the existing tool tree and produced no source delta).
- Refs: backlog.md#ATLAS-AEQUITAS-001 (the gitlink advance this closure
  records), backlog.md#ATLAS-PUBLISH-001 (mdbook test gate per-repo
  peers — unaffected), backlog.md#ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1
  (CFDrs advance blocker), backlog.md#ATLAS-LETO-OPS-AMD-ORDERING-001
  (leto peer work — peer-held, unclaimed here),
  backlog.md#ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 (CFDrs cfd-3d
  re-profile — partial closure, peer-held).
- Coordinator exhaustion reached after this advance: no further
  actionable gitlink atlases capable of evidence-backable advance at
  this session; all `in-progress`/`todo` items either peer-held
  (Codes `/root` peer) or peer-blocked on member-repo source files,
  per `concurrent_agents` disjoint-scope primitive. Next wake triggers
  documented at each rejected-advance entry above.

## ATLAS-GITLINK-COHERENCE-DEFECT-1 — Meta-coordinator audit: 8 atlas-meta gitlink pins target commits NOT on per-member origin/main [patch] [arch] — in-progress

- Owner: Atlas-Codex (atlas-meta coordinator — coordinator-scope
  risk-artifact recording; no member-repo source touched); last-update:
  2026-07-24; scope: this `backlog.md` risk entry only.
  Coordinator-scope per `interaction_policy` — Change delivery through
  merge on allowlisted repos is the standing grant; this entry records
  the defect without mutating any `.gitmodules` gitlink or any
  member-repo source tree. Per `concurrent_agents` assist-ladder this
  is the coordinator-safe path: peer-Codex/peer-coeus/peer-kwavers
  own the publishing-on-origin actions; coordinator publishes evidence.
- Outcome: surfaced a systemic gitlink-coherence defect across the
  atlas-meta `origin/main` head `b18cdb4f03b2e65e8be87b6dc51df24e2b1643c3`.
  Audit pattern: for each submodule `repos/<R>`, verify pinned SHA is
  ancestral to that member's `origin/main` (`git --git-dir=... --work-tree=...
  merge-base --is-ancestor <pin> origin/main`). A negative result is a
  coherence defect: consumers cloning atlas-meta and initializing
  submodules receive a SHA that the member repo's origin/main never
  contained, breaking ADR 0020's gitlink-advance contract ("verified
  peer commits pushed to origin/main").
- Defect inventory (8 pins, ordered by defect-introduction commit on
  atlas-meta origin/main):

  | # | Member repo  | Atlas-meta commit | Pin SHA    | Member origin/main | Defect category | Status |
  |---|--------------|-------------------|------------|--------------------|-----------------|--------|
  | 1 | `repos/coeus`        | `dc7459a` (prior session) → `dff78e7` (re-affirmed) | `c711dcb4` | `a6dfb2d` | A — peer ahead of origin on feature branch | open |
  | 2 | `repos/leto`          | `c147d91` | `c6ced81e` | `687b6707` | C — pin on local feature branch only | open |
  | 3 | `repos/moirai`        | `6b97938` | `f74aa480` | `b613dc3d` | A — peer local main 1 ahead of origin | **closed** (Session 23: peer-moirai published +(Session 22 advance `0979371` re-pointed atlas-meta gitlink to peer-published `2c14b94f`; verifier: `merge-base --is-ancestor 2c14b94f origin/main`) |
  | 4 | `repos/apollo`        | `63528a5` | `82e67c8f` | `8fb3e4ad` | A — peer local main 2 ahead of origin | open |
  | 5 | `repos/kwavers`       | `7720163...` (pre-Session 20 state) | `07f60733` | `c19134ec` | B — pin on origin feature branch (PR #325 DIRTY), not on origin/main | open |
  | 6 | `repos/hephaestus`    | `b18cdb4` (origin HEAD) | `599ff79a` | (no `main` on remote at all) | B — pin on origin feature branch diverged from missing main | open |
  | 7 | `repos/mnemosyne`     | `7baa847` | `6a4bad71` | `c10e510d` | A — peer local main 1 ahead of origin | open |
  | 8 | `repos/consus`        | (earlier) | `eae5676c` | `3137c4b8` | A — peer local main 1 ahead of origin | open |
  | 9 | `repos/asclepius`     | `c2227aa` (Session 23) | `47e73d1e` | `f1b6a8ff` | A — coordinator-authored advance to peer's local-only main | open |

- Recovery action matrix (per-Defect category — coordinator does NOT
  execute these; peers publish to their own origins and the
  coordinator advances the atlas-meta gitlink ONLY after verification):

  * **Category A** (peer local main ahead of origin/main; simple
    `git push origin main` on the member repo recovers → then
    atlas-meta gitlink becomes valid): coeus (peer operating on
    `atlas/mnemosyne-0.6-compat` feature branch — 18 unpublished
    commits — NOT a fast-forward candidate; require peer-coeus to
    merge their feature branch to coeus origin/main first),
    mnemosyne (1 commit `6a4bad7`), apollo (2 commits),
    moirai (1 commit), consus (1 commit).
  * **Category B** (pin on remote feature branch but origin/main
    diverged or absent — needs peer to open/merge/rebase PR): kwavers
    (peer PR #325 DIRTY against newer origin/main — requires rebasing
    the branch onto `origin/main` or closing/abandoning the PR),
    hephaestus (peer PR not known — requires peer-pusher to rebase
    `codex/hephaestus-rocm-sparse-next` onto a (currently absent)
    origin/main or create `main` first by merging the branch).
  * **Category C** (pin on peer's LOCAL feature branch only, no remote
    branch — needs peer to push the branch and open a PR): leto
    (`codex/leto-real-sparse-lu` is local-only — peer-leto must push
    the branch to origin, open PR, merge to origin/main).

- Correction cross-links (per-Defect category reclassification of prior
  `done` entries whose gitlinks are the defects above):

  * `ATLAS-COEUS-DIRTY-RECONCILE-1` at line 3041 (parent commit
    `dff78e7`) — claims `done` but the pinned coeus HEAD
    `c711dcb4` is NOT on coeus `origin/main` as of this audit.
    Status correction: `done (with coherence defect 1, see
    ATLAS-GITLINK-COHERENCE-DEFECT-1)`.
  * `ATLAS-LETO-GITLINK-ADVANCE-1` at line 3233 (parent commit
    `c147d91`) — claims `done` but pinned `c6ced81e` is on local
    branch `codex/leto-real-sparse-lu` only, no remote branch.
    Status correction: `done (with coherence defect 2, see
    ATLAS-GITLINK-COHERENCE-DEFECT-1)`.
  * `ATLAS-MOIRAI-GITLINK-ADVANCE-1` at line 3269 (parent commit
    `6b97938`) — claims `done` but pinned `f74aa480` is on peer's
    local main 1 commit ahead of `origin/main`. Status correction:
    `done (with coherence defect 3, see
    ATLAS-GITLINK-COHERENCE-DEFECT-1)`.
  * `ATLAS-APOLLO-GITLINK-ADVANCE-1` at line 3310 (parent commit
    `63528a5`) — claims `done` but pinned `82e67c8f` is on peer's
    local main 2 commits ahead of `origin/main`. Status correction:
    `done (with coherence defect 4, see
    ATLAS-GITLINK-COHERENCE-DEFECT-1)`.
  * `ATLAS-HEPHAESTUS-GITLINK-ADVANCE-1` at line 3362 (parent commit
    `4c49783`) — claims `done` but a follow-up advance at parent
    `b18cdb4` (NOT recorded in a ledger entry on origin/main; the
    ledger entry for that advance was lost in the discarded local
    `c6ac87f` docs commit during this Session 21 recovery) pinned
    `599ff79a` on `origin/codex/hephaestus-rocm-sparse-next`, with
    no `origin/main`.Exists to ancestral-check against. Status
    correction: add cross-link noting defect 6.

- Recovery closure protocol (when each Defect recovers): peer publishes
  the pinned SHA to their member-repo `origin/main` (via their own
  `git push origin main`, branch merge-PR, or branch rebase-PR per
  category); coordinator then re-runs the
  `merge-base --is-ancestor <pin> origin/main` check; on a positive
  result the defect sub-row moves to `closed (verifier: basher
  merge-base <sha> <origin-main>)`; the parent commit's gitlink is
  already correct (no `.gitmodules` mutation needed); only the ledger
  entry's status correction flips back to `done (clean)`.

- Sister cross-links:
  * `ATLAS-COEUS-DIRTY-RECONCILE-1` [done (with coherence defect 1)]
    at parent commit `dff78e7`.
  * `ATLAS-LETO-GITLINK-ADVANCE-1` [done (with coherence defect 2)]
    at parent commit `c147d91`.
  * `ATLAS-MOIRAI-GITLINK-ADVANCE-1` [done (with coherence defect 3)]
    at parent commit `6b97938`.
  * `ATLAS-APOLLO-GITLINK-ADVANCE-1` [done (with coherence defect 4)]
    at parent commit `63528a5`.

- Risk/change class: [patch] [arch] — ledger-only commit. The risk is
  architectural: the atlas-meta `origin/main` HEAD is a state that no
  fresh clone can reproduce into a working tree, because submodule
  initialization pulls SHAs not on member origins. Each defect's blast
  radius is bounded by the consumers of that specific member crate
  (e.g. `kwavers` consumers in `repos/kwavers` source; `coeus`
  consumers throughout the stack). The defect is quietly hidden for
  agents already initialized (whose local `repos/<R>` working trees
  already have the SHA physically checked out), but breaks any fresh
  clone, CI checkout from origin, or `git submodule update --remote`.

- Dependencies: recovers when each of the 8 peer-publishing actions
  per the recovery action matrix completes. No coordinator scope to
  accelerate; only peers have authority to push to their member repos.

- Evidence limit: basher-verified `git --git-dir=repos/<R>/.git
  merge-base --is-ancestor <pin> origin/main` for each of the 8
  defect rows, run during this Session 21 audit. Verification time:
  2026-07-24 16:24 -0400 (+/-3 min). No perf claim; no type-check
  oracle; no production-code delta.

- Discovered-by: Session 21 fresh-origin-sync-and-audit; origin sync
  (per `concurrent_agents`) revealed diverged atlas-meta main and
  mandated this audit before any further gitlink mutation.
- Mechanization follow-up filed as
  `ATLAS-GITLINK-COHERENCE-DEFECT-1-AUDIT-TOOL-1` [patch] [arch]
  (`todo`): a coordinator-owned `tools/gitlink-coherence/` sister
  tool that mechanizes this audit pattern (per `operation`
  toil-automation policy — the manual audit sequence has now run
  twice, is drift-prone and error-prone, and has clear positive
  maintenance value at PR-time). Tech preview: read `.gitmodules`,
  enumerate submodule entries, run
  `git --git-dir=... --work-tree=... merge-base --is-ancestor
  <pin> origin/main` per repo, emit JSON/markdown/human output
  with defect categorization, exit 0 on clean / 1 on defects / 2 on
  invocation error. Zero external deps (mirror
  `tools/criterion-regression` `Cargo.toml` template sans
  `serde`/`serde_json` if a single-pass tool suffices, or
  re-include `serde` if JSON output is desired).

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

## Session 23 closure (2026-07-24) — ATLAS-GITLINK-COHERENCE-DEFECT-1-AUDIT-TOOL-1 → ✅ closed

- Delivered the coordinator-owned `tools/gitlink-coherence/`
  package (`atlas-gitlink-coherence-gate`, binary `gitlink-coherence`).
- Verification (all gates green): `cargo fmt --check`, `cargo clippy
  --all-targets -- -D warnings`, `cargo nextest run` (18/18 pass,
  0.339s — within the 30s/60s nextest budget), `cargo test --doc`.
  End-to-end acceptance against the live atlas-meta working tree:
  `gitlink-coherence audit --atlas-root /d/atlas --fetch` reports 8
  defects + 2 stale-advanceable rows and exits 1, matching the
  DoR acceptance oracle.
- Root cause of the Session 22 end-to-end failure fixed: Windows
  backslash-mixed paths passed to `git --git-dir` fail through
  `gitdir:` indirection files (git's C-side resolver can't re-anchor
  the relative `gitdir:` target against a directory whose path
  contains both `/` and `\`). Replaced with a `git_dir_arg` helper
  that normalizes backslashes to forward slashes on Windows
  (no-op on POSIX). Per-integrity fix: dropped the
  `let _ = run_git(... "fetch" ...)` that swallowed the fetch
  error; the `couldn't find remote ref refs/heads/main` signal now
  routes to the `NoOriginMainOnRemote` classification, and genuine
  network failures propagate via `?`.
- Inventory movement: defect #3 (moirai) **closed** — peer-moirai
  published pin `2c14b94f` to origin and Session 22's gitlink
  advance `0979371` re-pointed atlas-meta to it. Defect #9
  (asclepius) **new** — coordinator-authored commit `c2227aa`
  advanced the asclepius gitlink to peer's local-only main
  `47e73d1e`; same defect pattern that `ATLAS-GITLINK-COHERENCE-
  DEFECT-1` is filed to expose. Recorded as defect #9 in the parent
  risk entry's inventory. Recovery action: peer-asclepius
  `git push origin main` to publish `47e73d1e` to `origin/main`.
- Coordinator home-scope after closure: the audit tool was the one
  substantive in-progress coordinator-claimable increment. After
  this commit, the only remaining in-progress items are peer-held
  member-repo source files (recovery actions for defects 1/2/4/5/
  6/7/8/9). Coordinator scope returns to ledger-filing only.
- Residual risk: the asclepius defect #9 is my own coordinator-side
  mutation. It is the existing defect pattern's first confirmed
  re-introduction since `ATLAS-GITLINK-COHERENCE-DEFECT-1` was
  filed — an internal regression against the policy the parent
  entry exists to enforce. Filed on the parent inventory for
  peer-asclepius recovery (category A: peer publishes local main).
- Pushed commit: see git log for SHA (atlas-meta origin/main
  following push).

## ATLAS-VERSION-GUARD-001 — Manifest-version guard and stack coherence check [patch] — in-progress (sub-delivery 1 done)

- **Sub-delivery 3 (coherence) peer-held 2026-08-07.** A live peer is
  building the offline stack-coherence scan in the same tool: new
  `tools/version-guard/src/coherence.rs` (`CoherenceFinding`,
  `CoherenceReport`, `scan_atlas` reading `.gitmodules` + checked-in
  manifests, no Cargo/registry), wired into `lib.rs`/`main.rs`/`error.rs`
  as a `coherence --atlas-root` subcommand. Working-tree changes only,
  uncommitted as of this record; the tree compiles and 52 tests pass
  (including `coherence::tests::injected_backward_fixture_is_reported`).
  Builds on the committed `a92a3c6` base. **Do not touch**
  `tools/version-guard/src/coherence.rs` or the other version-guard files
  while the peer is mid-edit; claim the sub-delivery-3 closure only after
  the peer commits or the edit goes stale.
- **Fail-closed intent validation committed 2026-08-07** as `a92a3c6`
  (`fix(version-guard): Fail closed on declared release with no forward
  movement`). The slice was previously recorded delivered but sat stranded
  uncommitted at the atlas root; the 2026-08-07 session landed it with the
  sibling tooling slices. Gates re-verified at commit time: 48 lib + 3 bin
  tests pass, `cargo clippy --all-targets -- -D warnings` clean.
- **Fail-closed intent validation 2026-08-06 (root tool slice).**
  `tools/version-guard` now treats a declared release/bump intent with no
  forward version movement as a defect, including an empty manifest diff or
  an identical-only reformat. The same intent-aware predicate drives the CLI
  exit code and human/JSON reports, so no alternate "clean" interpretation
  can mask a missed package release. Backward movement remains an unconditional
  defect, and undeclared forward movement remains rejected. Added regressions
  for empty and identical-only declared releases plus report parity. Scope is
  root tooling only; no provider checkout, consumer source, manifest,
  lockfile, or dependency changed.

- Policy: AGENTS.md git_discipline (version-bearing red-flag hunks) + architecture_scoping pin discipline (version metadata is sweep-triggering state). Motivating incident: `87ab265` (hermes) — a sed dep-conversion silently reverted the workspace release `0.5.0 -> 0.4.1` and internal requirements to `0.4.0`, unmentioned in its message; origin lied about versions for ~10 hours while integrators failed resolution, and coeus stacked 18 commits on the undeliverable base.
- Scope: (1) per-repo guard — CI step (and optional pre-commit hook) failing when a diff changes `version =` or first-party dependency version requirements without a declared release/bump intent (commit type `chore(release)`/`build(deps)` or an explicit footer); backward version movement always fails without the declaration; (2) stack coherence check — a meta-level check (home: tools/, sibling to criterion-regression) verifying every first-party requirement across allowlisted members resolves against the stack's current workspace versions, run in the integration sweep and on any version-touching commit; (3) wire both into member CI per repository convention.
- Acceptance: replaying `87ab265` against the guard fails it; coherence check passes on the current stack and fails on an injected backward-version fixture; guards live in committed CI/config, not agent memory.
- Sub-delivery 1 — per-member guard tool skeleton: **done 2026-07-31** at `
  c70af8b` (`fix(tools,scripts): Make version-guard build and retarget link tests`).
  `tools/version-guard/` (`atlas-version-guard`) parses both bare
  `version = "X"` lines and inline-table `dep = { ..., version = "X" }`
  entries from `git diff <range> -- '*.toml'`, pairs `+`/`-` per file by
  ordered position, classifies each as Identical / Forward / Backward, and
  flags a finding as a defect when backward (always) or forward-undeclared.
  Borrow-checker errors that surfaced in Session 32 (E0382 borrow-after-move
  of `v` in `scan_diff`; E0499 double `&mut` in `files_entry`) were
  resolved by capturing the side before the move and indexing the per-file
  slot, respectively (ownership fix, not a workaround). Live acceptance replay
  on `87ab265` produces **9 backward findings across 5 files**
  (`Cargo.toml` + `hermes-simd-core` + `hermes-simd-intrinsics` +
  `hermes-simd-types` + `hermes-simd`), exit 1. Tests 47/47 (44 lib + 3
  bin). Skeleton-scope: `[package].version` + inline-table first-party deps;
  third-party shorthand (`dep = "X.Y.Z"`) without surrounding `{...}` and
  TOML-section tracking (`[workspace.package]` vs `[package]`) deferred to
  sub-delivery 2.
- Sub-delivery 2 — CI wiring per member repo: **todo**. Wire the guard
  into each allowlisted member's CI as a step on PRs/pushes touching its
  `*.toml`; the guard runs once per repo against its own range.
- **Sub-delivery 3 — stack coherence check tool delivered 2026-08-07** in
  the root working tree (`tools/version-guard/src/coherence.rs`, with the
  `coherence --atlas-root <path> [--format human|json]` CLI subcommand).
  The scanner is offline and read-only: `.gitmodules` is the allowlist, and
  checked-in Cargo manifests are the package/version SSOT. It walks 235
  manifests, resolves `version.workspace = true`, dotted/workspace dependency
  inheritance, package aliases, multiline inline tables, and Cargo-style
  caret/tilde/comparator/wildcard requirements. It checks only path/git
  sources resolving to registered Atlas members, rejects missing member
  manifests, ambiguous package versions, unsupported prerelease/hyphen ranges,
  and malformed version components rather than reporting a false clean.
  Human and JSON reports share the same defect predicate; missing
  `--atlas-root` is an invocation error (exit 2).
- Sub-delivery 3 acceptance evidence: current Atlas scan is clean at
  **235 manifests / 215 packages / 898 first-party requirements / 0 defects**
  (human and JSON modes, exit 0); an injected backward-version fixture is
  detected; the missing-root CLI case exits 2. `cargo fmt --check`, strict
  `cargo clippy --all-targets --offline -- -D warnings`, `cargo nextest run`
  (59/59), `cargo test --doc --offline`, and `git diff --check` pass with
  ambient `RUSTC`/`RUSTDOC` overrides removed. Resolver-generated
  `Cargo.lock` patch churn was discarded; no lockfile or provider tree is
  part of this root tooling slice.
- Sub-delivery 2 — CI wiring per member repo: **todo**. Wire the guard
  into each allowlisted member's CI as a step on PRs/pushes touching its
  `*.toml`; the guard runs once per repo against its own range.

Toolchain-template drift corrected 2026-08-03 (Session 33 closure): the
peer's `1.95.0 -> 1.97.0` pin advance (ATLAS-TOOLCHAIN-COHERENCE-001
resolution) had been propagated to the three existing consumers but not to
`tools/_template/template-rust-toolchain.toml` (still `1.95.0`), so the
Session-32 version-guard skeleton copied the stale pin. Both files now
match `1.97.0`, `check-drift.sh` extended to a fourth consumer
(`tools/version-guard/`), and `template-Cargo.toml` / README consumers
list updated. `check-drift.sh` reports `4 consumers clean`.

## ATLAS-OVERLAY-001 — Generated [patch] overlay for local-vs-git coherence [patch] — in-progress

- Policy: AGENTS.md architecture_scoping "Development overlay". Motivating blockers: local mnemosyne 0.6 vs git moirai requirement ^0.5 (requirement lag — patch cannot unify across an unsatisfied requirement), and the provider manifest missing the apollo -> eunomia edge (hand-curated derived state rotting as edges appear).
- Scope: (1) extend tools/checkout-path-dependencies (it already computes the graph) to emit a stack-level `[patch."<git-url>"]` overlay into the root `.cargo/config.toml` from the `cargo metadata` closure of all allowlisted members — regenerated by command, never hand-edited; every first-party crate maps to its local tree per source URL; (2) forward-sweep integration — a first-party version bump runs the requirement sweep (every in-stack requirement and lock on the bumped crate advances in the same co-evolution unit), composing with the ATLAS-VERSION-GUARD-001 coherence check; (3) regenerate on graph change: adding a first-party dependency edge re-emits the overlay in the same increment.
- Acceptance: both motivating blockers reproduce against the pre-overlay state and resolve after (moirai builds against local mnemosyne once requirements sweep; apollo resolves eunomia from the generated closure); the overlay file carries a generated-do-not-edit header naming the regenerating command; member manifests unchanged (git+version sources intact for CI/standalone). Update 2026-07-24: generator landed as scripts/atlas-stack-overlay.py; suffix doubling fixed at the stem (zero .git.git keys, regeneration idempotent, check mode green); AGENTS.md now carries the generator contract (canonicalized inputs, closure validation, regenerate-and-diff freshness) and the meta-lane prohibition that supersedes the "build from primary root" workaround. **Update 2026-07-28 (Session 30):** check mode wired into CI as `.github/workflows/atlas-stack-overlay.yml` (gate on PRs/pushes touching `.cargo/config.toml`, `scripts/atlas-stack-overlay.py`, `repos/**/Cargo.{toml,lock}`, `repos/**/pyproject.toml`). Sub-delivery (3) regenerate-on-graph-change absorbed: the `paths:` filter above fires on any consumer `Cargo.toml`/lock edit, which is precisely the trigger for overlay regeneration (script is one `python scripts/atlas-stack-overlay.py generate` call). Forward-sweep integration (sub-delivery 2) requires per-member guard at the atlas-coordinator boundary; that is the scope of ATLAS-VERSION-GUARD-001.

## Session 25 closure (2026-07-26) — coordinator gitlink advances + tools/_template/ extract

- Head: `77bcaca` → `e519928` on `origin/main` (pushed).
- Outcomes delivered:
  1. `b022211` build(atlas): Advance aequitas and apollo gitlinks to
     origin/main. Two stale-advanceable gitlinks advanced after
     `merge-base --is-ancestor` verification (aequitas `343ceb57` →
     `f19ba151`, apollo `82e67c8f` → `d60828cd`). ritk left to peer
     because the working tree was on `codex/docs-ritk-pages-closeout`
     with a dirty Cargo.toml.
  2. `e260055` refactor(atlas): Extract `tools/_template/` for shared
     coordinator-tool config (closes `ATLAS-TOOLS-TEMPLATE-EXTRACT-1`).
     Four new files (template-Cargo.toml, template-rust-toolchain.toml,
     README.md, check-drift.sh) consolidate the third-occurrence
     verbatim `[lints]`/`[profile.*]`/shared-`[dependencies]` section
     across `checkout-path-dependencies` / `criterion-regression` /
     `gitlink-coherence`. `checkout-path-dependencies/rust-
     toolchain.toml` reconciled to template canonical key order.
     `.gitignore` whitelisted `tools/_template/` (the `_*` catch-all
     matches the leading underscore). Per-tool gates passed:
     criterion-regression 21/21 in 5.681s + 2/2 doctests,
     gitlink-coherence 18/18 in 3.309s, checkout-path-dependencies
     11/11 in 7.520s + 1 doctest. `check-drift.sh` exits 0.
  3. `e519928` build(atlas): Advance CFDrs, coeus, mnemosyne gitlinks
     to origin/main after their origin/main advanced from under
     earlier coordinator advances (CFDrs `d4bc1702` → `f083b65f`,
     coeus `15ee8e59` → `765a0556`, mnemosyne `8ba205c9` →
     `00c3f6de`). All pins verified ancestral to origin/main before
     staging. ritk skipped again (peer on
     `codex/docs-ritk-n4-figure-clarity`). This commit also absorbed
     peer-Codex backlog updates recording the `ATLAS-CFDRS-COEQ-
     BLOCKER-1` and `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1` closure
     trailing peer `fc2fae5` coeus advance — concurrent agents
     detect-and-reconcile: kept co-authored, attribution noted here.
- Gitlink-coherence inventory at session close: 4 defects remain
  (hephaestus no-origin-main, kwavers cat-b via PR #325, leto cat-b
  via codex/leto-real-sparse-lu, asclepius cat-a local main not
  pushed) + 1 stale-advanceable (ritk). Session started with 7
  defects; closed during this session by peer pushes: mnemosyne #7,
  consus #8, coeus #1, moirai #3 stayed clean. Stale-advanceable
  `aequitas` and `apollo` advanced by this session.
- Next-session handoff: the math-SSOT consolidation audit (new user
  directive flagged this session) is the standing next coordinator
  scope item — a cross-repo grep across `repos/kwavers/src`,
  `repos/CFDrs/src`, `repos/helios/src`, `repos/leto/src` for math
  capability (ndarray / nalgebra / rsparse / Matrix / solve / lu /
  qr / svd / eigen / fft / convolve / sparse), tabulated
  capability × repo × module. File `ATLAS-MATH-SSOT-CONSOLIDATION-1`
  DoR-style in backlog (audit-only; execution is peer-leto /
  peer-physics-crate work). Record the audit pattern in gap_audit.md
  as a reusable audit template.
- Open peer recovery work (coordinator cannot execute, only record):
  - peer-hephaestus: publish `main` ref to origin (currently on
    codex/comparison-expression-parity; no main);
  - peer-kwavers: merge/close PR #325 onto origin/main;
  - peer-leto: merge `origin/codex/leto-real-sparse-lu` to origin/main;
  - peer-asclepius: push local main `47e73d1e` to origin/main; the
    gitlink pin already points to that SHA.

## Session 26 closure (2026-07-27) — GMRES fork ports and the athena redundancy question

`ATLAS-GMRES-FORK-DEFECTS-001` → done. `ATLAS-GMRES-SSOT-001` → re-scoped
by decisive evidence; see below.

### CFDrs — no port needed, already consolidated

A peer landed `6d18a547 ssot(cfd-math): replace local CG/BiCGSTAB/GMRES with
leto-ops wrappers` and `6484ad9e cleanup(cfd-math): remove orphaned arnoldi.rs
and givens.rs from gmres/` earlier the same day, and has the remainder of
`crates/cfd-math/src/linear_solver/` staged for deletion. CFDrs therefore
inherits the leto-ops corrections directly. Porting into it was rejected: the
target files are being deleted.

### kwavers — ported, `a8c76b67e`

Defects fixed in `crates/kwavers-solver/src/integration/nonlinear/gmres/`:

1. Orthogonalisation was Classical Gram-Schmidt while the doc claimed Modified
   (second- vs first-order loss of orthogonality). Fork-specific defect, not
   present in leto-ops.
2. Convergence accepted from the least-squares estimate alone — a singular
   operator drives the estimate to zero on step 1 while `b − A·x` is untouched.
3. No finiteness guard anywhere; NaN burned the whole iteration budget.
4. Absolute `1e-14` breakdown threshold (scale-dependent), and breakdown
   restarted into the same invariant subspace instead of surfacing.
5. Krylov basis, Hessenberg and rotations reallocated per restart — `m + 1`
   full 3-D fields at the default `krylov_dim = 30` — plus two field
   allocations per Gram-Schmidt step. Now a workspace retained across solves,
   which matters because the Newton loop calls the solver per outer iteration.

Consolidating kwavers onto leto-ops instead was evaluated and rejected for now:
`jacobian_vector_product` takes `&mut self`, so the operator closure is
genuinely `FnMut`, and `leto_ops::LinearOperator::apply` takes `&self` with a
`Send + Sync` bound. Consolidation is gated on refactoring that JVP to `&self`
(its only mutation is a scratch-buffer cache). Recorded as the concrete blocker
on `ATLAS-GMRES-SSOT-001`.

Verification note: the kwavers working tree is mid-migration across ~60 files
on three fronts, so `cargo check -p kwavers-solver` does not build. The module
was verified in a standalone harness compiling it against the same `leto` and
`kwavers-core` revisions: 9/9 tests, clippy `-D warnings` and rustfmt clean.
Re-run the package gate once the peer migration lands.

### ATLAS-GMRES-SSOT-001 — CORRECTED 2026-07-27: Athena is the owner

An earlier entry in this session read the zero-consumer evidence as grounds to
name `leto-ops` the Krylov SSOT and supersede leto ADR 0015. **That was wrong
and is retracted.** It inverted a ratified boundary on evidence of
non-adoption. See [ADR 0033](docs/adr/0033-krylov-ownership-reaffirmation.md).

Standing evidence, unchanged: nothing in the stack references
`athena_core::Gmres` or `athena_core::Cg`; Athena's only code consumer is
Harmonia, which imports `ConvergencePolicy`, `IterationObserver`,
`IterationState`, `NoObserver` only. Every other `athena-*` manifest line is a
`[patch]` overlay entry, not a dependency.

Corrected reading of that evidence:

- Atlas ADR 0022 (Accepted, `[arch]`) names Athena the iterative-solver
  provider, citing exactly this defect: "Leto, CFDrs, and Kwavers own
  iterative-solver recurrences beside storage, discretization, or domain code".
  The meta README stack map agrees: `athena` — "Iterative solver policy over
  CPU and accelerator providers."
- Leto executed the extraction in `aa8aa9b` (2026-07-19 22:29, ADR 0015).
- `ee6582d chore(leto): remove ndarray/nalgebra dev-dependencies`
  (2026-07-23 17:57) reintroduced the whole family — `cg.rs`, `bicgstab.rs`,
  `gmres/`, `lsqr.rs`, Jacobi/SOR/SSOR/ILU — four days later, under a message
  that never mentions it. That commit is the regression.
- CFDrs `6d18a547` then wrapped the reintroduced Leto family, propagating it.

So Athena's zero consumers measure a stalled extraction, not a wrong owner.
The unwind sequence is ADR 0033 stages A-D, tracked below.

### Concurrent-agent record

Assist edits left uncommitted in peer working trees, each completing a peer's
own in-flight leto-ops SSOT migration and needed to reach a build:
`kwavers-source/Cargo.toml` and `kwavers-physics/Cargo.toml` (missing
`leto-ops` dependency behind imports the peer had already switched);
`bessel.rs`, `acousto_optics.rs`, `wave/nonlinear.rs`, `burgers/solution.rs`
(`u32` → `usize` for the leto-ops `jn` signature);
`kwavers-transducer/.../processor.rs` (`Vec<f64>` → `Array1<f64>` conversion).
Also `bessel_k0` added to `leto-ops/src/application/special.rs`, which the peer
had already imported from there but not yet moved upstream — left uncommitted
because that file is the peer's active rewrite and the addition cannot be
separated from it by path. **That port fixed a transcribed A&S 9.8.1
coefficient, `3.5156329` → `3.5156229`, which alone accounted for a 5e-7
absolute error in K₀ near x = 1.** Reference-value tests added.

## ATLAS-WORKTREE-CLONES-001 — Reconcile standalone clones under `worktrees/` [patch] — in-progress

- Census 2026-07-30 (mechanized: `scripts/atlas-lane-audit.py`, exit-nonzero local gate for orient/replenishment — filed by fable-prompt-session as peer-assist evidence): 17 hand-wired gitdir mirrors are back under `worktrees/` (aequitas, apollo, coeus, consus, eunomia, gaia, hermes, hyperion, iris, leto, melinoe, mnemosyne, moirai, proteus, ritk, themis, tyche — each `.git` file points at the member's primary `.git/modules/...` gitdir, sharing its index), plus the `worktrees/hephaestus` standalone clone, three bare non-worktree dirs (hephaestus-unary-math-parity, kwavers-aequitas-vessel-metrics, ritk-book-complete), and kwavers at 3 working trees. The prior purge did not hold — something regenerates the mirrors. SPIKE (unclaimed): identify the generator (peer tooling or an agent habit materializing `worktrees/<member>`), evidence budget one session, deliverable = generator named and fixed or a defect filed on its owner; re-deletion without that finding repeats the cycle. Legitimate submodule lanes (gitdir under `.git/modules/<path>/worktrees/<lane>`) pass the audit.
- Live-regeneration evidence 2026-07-30: the violation count moved 22 -> 29 within ~2h of the first audit run — lane-root timestamps show a peer serially creating `hephaestus-j1e2` … `hephaestus-j5` plus `ritk-pr-split` during the session (lane-per-subtask sprawl; the two-tree bound and one-item-per-lane rules ignored). The spike's generator question now has a live specimen: whatever workflow drives the `-jN` series is creating a lane per job. Differential note for auditors: `scripts/atlas-lane-audit.py` counts are environment-dependent by design (local git state) — never baseline them in conformance JSON.
- Evidence: `D:/atlas/worktrees/` holds directories named after stack repos
  (`leto`, `eunomia`, `moirai`, `ritk`, …) that are **standalone clones**, not
  linked worktrees — `worktrees/eunomia/.git` is a full repo directory, and
  `git worktree list` in `repos/eunomia` shows only `repos/eunomia`.
- Impact: this is the prohibited repo-copy pattern (forked history, duplicated
  disk). It also actively breaks lanes: a real worktree placed under
  `worktrees/` resolves a member's `../<repo>` path dependencies to these
  clones, producing `package collision in the lockfile` — encountered while
  trying to lane the kwavers GMRES work.
- Scope: per clone, rescue-commit any dirty state, fetch unique branches and
  commits into the authoritative repo under `repos/`, then delete. Confirm
  `git worktree list` per repo stays within the two-tree bound afterwards.
- Non-goal: touching genuine linked worktrees.

### Session 29 partial reconciliation (2026-07-27)

Inventory at session open: 8 standalone clones (full `.git` dir at
`worktrees/<repo>`): `aequitas`, `asclepius`, `eunomia`, `hephaestus`,
`hermes`, `iris`, `leto`, `themis`.

- **Reconciled and deleted this session**: `worktrees/iris`.
  Safety verification satisfied byte-for-byte: WT HEAD `c3cc43b` ==
  `worktrees/iris`'s `origin/main` == atlas-meta gitlink pin ==
  `repos/iris` HEAD == `repos/iris`'s `origin/main`; zero unpushed commits
  (`origin/main..HEAD` empty); clean WT (no dirty files, no untracked,
  no stashes); single local branch `main`; not a linked worktree
  (`git worktree list` in `repos/iris` lists only the main tree). 3 days
  stale (well past the 1h staleness sweep threshold).
- **Intentionally NOT touched (peer mid-flight or unique content)**:
  - `leto` — last commit 18 min prior to close (actively in flight).
  - `aequitas` — dirty WT (`CHANGELOG.md`, `Cargo.lock`, `README.md`,
    `src/systems/si/*.rs`, `tests/*.rs`), 5h staleness. Mid-flight peer work;
    deletion would trigger `interaction_policy` Ask-User (irreversible loss
    of uncommitted unique work).
  - `themis` — dirty `Cargo.toml` containing **ATLAS-PATH-DEP-AUDIT-2 /
    ATLAS-OVERLAY-001 generated `[patch]` overlay content** (comment
    `Last delivery: 2026-07-27 closure cycle`). This is the peer-attributed
    draft of the ATLAS-OVERLAY-001 deliverable; deletion would destroy
    unique peer-authored state.
  - `asclepius`, `eunomia`, `hephaestus`, `hermes` — 6h staleness,
    not exhaustively safety-verified this session. Hephaestus clone HEAD
    matches the active peer-hephaestus feature branch, currently the focus
    of the persistent `no-origin-main` defect.
- **Next-session action**: re-safety-verify the 6h-stale and 3-day-stale
  clones (`asclepius`, `eunomia`, `hermes`) using the iris verification
  protocol (HEAD == origin/main AND clean WT AND no local-only branches AND
  no unpushed commits AND not a linked worktree) and delete each that passes.
  `aequitas` and `themis` require the user or the owning peer to rescue the
  dirty state before the clone can be deleted. `leto` is freshly active and
  should not be touched.

## Session 27 closure (2026-07-27) — peer-coordinator ATLAS-MODALITY advance + the persistent gitlink defect set

Re-oriented against `origin/main` at session open. The standing "next action"
from the Session 26 handoff (append Session 26 closure to `backlog.md`) had
already landed under peer-coordinator attribution: commit `1da7cea docs(pm):
Close GMRES fork ports; record athena zero-consumer evidence` wrote the
`## Session 26 closure` section at L4785. The math-SSOT audit content I drafted
in Session 26 also survived intact at L4542 (`ATLAS-MATH-SSOT-CONSOLIDATION-1`)
and the audit-pattern template in `gap_audit.md` at L5178 — peer commit
`fad8c9e` reused my commit subject but its diff was a CFDrs gitlink advance;
no content clobber. Same attribution-absorption pattern as Session 25
`e519928`; no remediation needed because the content is correct DoR-level PM
state.

### Peer-coordinator landings during the inter-session gap (10 commits, b3106f4..20b03b8)

A peer-coordinator session (same Ryan Clanton attribution) ran during the
~90-minute gap and landed 10 commits, of which 7 are substantive coordinator-
scope work on the modality-boundaries workstream and the CFDrs metric closure:

| Commit | Subject summary |
| :--- | :--- |
| `20b03b8` | Advance CFDrs gitlink to its consumer-side metric closure |
| `a802e0c` | Close CFDrs MET22 transient-composition metric gap in `gap_audit.md` |
| `b804449` | Split `ATLAS-MODALITY-002` — 2a (kwavers bioheat boundary) closed, 2b (SpecificAbsorptionRate provider-side gap) blocked on peer |
| `8571cc1` | Refresh Aequitas metric audit (reconcile CFDrs/Helios/Kwavers consumer closures) |
| `5711c0c` | Advance aequitas gitlink — `ATLAS-MODALITY-002` phase 1 |
| `537b22c` | Claim `ATLAS-MODALITY-002` phase 1 in aequitas |
| `35f41e9` | Record modality boundaries (optics / RF / photomedicine) in the stack map + kwavers bioheat deposition spine |
| `1da7cea` | (Session 26 carry-over) Close GMRES fork ports; record athena zero-consumer evidence; file `ATLAS-WORKTREE-CLONES-001` |
| `fad8c9e` | (Session 26 carry-over, peer-reused subject) CFDrs gitlink advance |
| `b3106f4` | (Session 26 close, peer-reused subject) Math SSOT audit pattern filed in `gap_audit.md` |

These landings are accepted (peer-coordinator authority is granted by the
standing Change intent on this allowlisted meta-repo; no clobber of my
Session 26 work). They advance `ATLAS-MODALITY-002` from `todo` to
`in-progress` (phase 1 delivered, phases 2b-4 open).

### Residual gitlink defects (re-probed this session)

`target/release/gitlink-coherence.exe audit` reports **5 defects + 1
stale-advanceable + 19 clean** (down from Session 26's 11 defects — peers
published `origin/main` for apollo/athena/gaia/helios/hermes/asclepius during
the gap, resolving the cat-a class).

Persistent defects, each blocked on peer recovery action the coordinator
cannot execute (no write access to `repos/<name>/...`):

| Repo | Category | Pin | origin/main | WT HEAD | Branch | Last commit | Recovery (peer-owned) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| coeus | cat-c | cdaf769 | e26ba668 | cdaf769 | `codex/coeus-error-function-parity` | 3h ago | peer-coeus: publish origin/main |
| hephaestus | no-origin-main | 47ca84a | (none) | 47ca84a | `codex/hephaestus-product-axis-reduction-parity` | 3h ago | peer-hephaestus: create `origin/main` (4-session persistent defect) |
| kwavers | cat-b | 81a40071 | dce38e26 | **a7922bcc** | `codex/kwavers-book-migration-eviction` | **59 min ago** | peer-kwavers: merge/rebase feature to origin/main OR roll WT to main; coordinator NOT advancing — peer is actively committing |
| leto | cat-b | c6ced81 | 5ba88cc | dcc5d54 | `codex/leto-real-sparse-lu` | 5h ago | peer-leto: merge feature to origin/main |
| ritk | cat-c | 65035908 | c05f84d5 | 65035908 | `codex/docs-ritk-n4-figure-only` | 3h ago | peer-ritk: merge feature + publish origin/main |

Stale-advanceable (still NOT safely advanceable):

- `mnemosyne`: pin=00c3f6d, origin-main=905909b, WT HEAD=ec1c000 on
  `codex/mnemosyne-tier-selection` (7h ago). `git add` would capture the
  feature-branch HEAD `ec1c000`, not `origin/main` `905909b`. Per pitfall #2,
  this remains blocked until peer-mnemosyne either publishes `origin/main`
  or rolls WT back to `main`.

### Assist-ladder actions taken this session

- **Audit recovery**: Verified peer-coordinator's Session 26 closure (L4785)
  and the math-SSOT inventory (L4542) survived intact — no remediation
  required.
- **No gitlink advances**: Every defect row is either a structurally
  peer-only recovery (publish `origin/main`, merge feature branch) or has
  the working tree on a feature branch that would capture the wrong SHA.
  `kwavers` peer committed 59 minutes ago — active, not stale; coordinator
  escalation inappropriate per `concurrent_agents` assist-or-skip rules.
- **Closure written**: This section.
- **No new board entries**: The 5 defect rows above are already covered by
  their prior-session backlog items; a louder board restate is not warranted
  until a true stale-claim (1h+ no commit signal) develops. Three defects
  (hephaestus, kwavers PR, leto) are at 3+ sessions persistence and would
  become candidates for user-direction escalation if they persist into
  Session 28.

### Stale-memory re-verification (this session)

- `rust-toolchain.toml` pinned, MSRV unchanged.
- `target/release/gitlink-coherence.exe` present and unchanged.
- 25 submodules in `.gitmodules` unchanged.
- Shared `target-dir = "target"` at `/d/atlas/.cargo/config.toml` unchanged.
- Re-confirmed: `repos/<name>/.git` is a `gitdir:` indirection file for the
  submodule members (except `leto`/`hephaestus`, which are full directories);
  the gitlink pin is what `atlas-meta`'s git index records, and it can differ
  from `repos/<name>` WT HEAD when a peer has moved their WT onto a feature
  branch without the coordinator committing the advance.

### Next-session handoff

- Re-fetch + re-probe at session open (utility `gitlink-coherence.exe audit`
  is the canonical state read).
- Watch for peer-kwavers landing the feature branch — if `origin/main`
  advances, the gitlink is a one-step advance.
- Watch for peer-coeus / peer-ritk / peer-mnemosyne / peer-leto feature
  merges — same one-step advance opportunity.
- Watch for peer-hephaestus publishing `origin/main` — would close the
  4-session persistent `no-origin-main` defect.
- If 3 of the 5 persistent defects are unchanged by Session 28 open,
  escalate to user with a single batched message naming the 2-3 worst
  blockers (likely hephaestus + the most-active-of-the-rest) and request
  direction on peer-side remediation.
- Stand-alone next coordinator items still `todo`:
  `ATLAS-OVERLAY-001` (generated patch overlay), `ATLAS-VERSION-GUARD-001`
  (manifest version guard), `ATLAS-MATH-SSOT-CONSOLIDATION-1` (audit filed;
  execution owned by peer-leto/peer-physics-crate), `ATLAS-WORKTREE-CLONES-001`
  (rescue the standalone clones under `worktrees/`). Review whether any
  becomes urgent next session.

## Session 28 closure (2026-07-27) — ADR 0033/0034 (Krylov/Accelerator re-architecture), coeus cat-b promotion, 1 defect escalation

Short session: re-oriented after peer-coordinator landings, integrated two new
ADRs into PM state, escalated the standing 4-session hephaestus defect as a
cross-referenced blocker on `ATLAS-ATHENA-ACCEL-BACKEND-001`, ended with no
new gitlink advances (5 defects + 1 stale-advanceable + 19 clean unchanged
this session).

### Peer-coordinator landings during the inter-session gap (6 commits, 5ed51fa..2cd4c01)

| Commit | Subject summary |
| :--- | :--- |
| `2cd4c01` | Propose one Hephaestus-backed Athena accelerator backend (ADR 0034, status `Proposed`) |
| `a454976` | Record `ATLAS-MODALITY-002` 2b progress + the unified heat-source field defect |
| `12d3fdf` | Reserve `ATLAS-DOWNSTREAM-COORDINATION-001` ticket for LeoNeuro-INC `50bfcd9` hand-off |
| `051d1af` | Reaffirm Athena as the Krylov owner (ADR 0033, `Accepted`, `[major] [arch]`) |
| `b23271b` / `eb3cdb9` | Refine STEP D axes table + alternatives-rejected grounds (PATH_DEP_AUDIT_001_ENTRY.md) |
| `1fd57ae` | Clarify STEP D orthogonal axes + alternatives rejected + push-handoff |

ADR 0033 supersedes the iterative-solver lane of my Session 26
`ATLAS-MATH-SSOT-CONSOLIDATION-1` audit (L4542). ADR 0033's reasoning is
correct: adoption-count inversion of a ratified boundary (ADR 0022 named
Athena Krylov SSOT; leto-ops's `ee6582d` reintroduction is a regression, not
a new SSOT, regardless of which has more current consumers). The
`ATLAS-MATH-SSOT-CONSOLIDATION-1` row's direct-decomposition lane (LU/QR/
Cholesky/SVD/eigen/Schur/Bunch-Kaufman/UDU — definitively leto-ops's
ownership per ADR 0033 §2) and sparse-interpolation-quadrature lanes remain
valid; only the iterative-solver recommendation is superseded by
ATLAS-ATHENA-KRYLOV-CAPABILITY-001 / ATLAS-GMRES-FORK-CONVERGE-001 /
ATLAS-ATHENA-ACCEL-BACKEND-001. The audit-inventory table itself (ssot-
baseline + cross-capability matrix) is unmodified and remains useful as the
broader cross-repon math consolidation inventory; it's just that one slice
of its recommended action set has been overtaken by a more authoritative
ADR.

### Gitlink state re-probed (post-peer-landings)

`target/release/gitlink-coherence.exe audit`: **5 defects + 1
stale-advanceable + 19 clean** (Session 27 had identical counts; this
session's only movement is the `coeus` defect upgrading from cat-c → cat-b).

| Repo | Category | Pin | origin/main | Movement vs Session 27 |
| :--- | :--- | :--- | :--- | :--- |
| coeus | cat-b | cdaf769 | 971fab9 | **upgraded** from cat-c: peer-coeus pushed `codex/coeus-error-function-parity` to a tracked remote branch (`origin/codex/coeus-error-function-parity`); still not merged to `origin/main` |
| hephaestus | no-origin-main | 47ca84a | (none) | unchanged (5-session persistent) |
| kwavers | cat-b | 81a40071 | dce38e26 | unchanged; WT HEAD moved to `a7922bcc` (peer kwavers-book-migration-eviction, 59 min ago at session open — peer is actively committing in their feature branch) |
| leto | cat-b | c6ced81 | 5ba88cc | unchanged |
| ritk | cat-c | 65035908 | c05f84d5 | unchanged |
| mnemosyne | stale-advanceable | 00c3f6d | 905909b | unchanged; WT on `codex/mnemosyne-tier-selection` |

### Assisted ACCEL-BACKEND row with the hephaestus-`origin/main` cross-reference

Appended a "Blocking upstream state" note at `ATLAS-ATHENA-ACCEL-BACKEND-001`
(L5127→L5137) naming the hephaestus 5-session persistent `no-origin-main`
defect as the upstream unblock for that [arch] item's deletion of
`athena-wgpu` and Hephaestus kernel additions. Recommend the user direct
peer-hephaestus to publish `origin/main` (or merge the feature branch) as
the unblock for both this row and the 4-session-persistent defect.

### Assist-ladder actions taken this session

- **No gitlink advances**: every defect is structurally peer-only recovery
  (publish/merge) or has the WT on a feature branch that would capture the
  wrong SHA per pitfall #2.
- **Doc-sync (anti-orphaning)**: cross-referenced the new ADR 0033/
  0034 chain into the existing `ATLAS-MATH-SSOT-CONSOLIDATION-1` audit row's
  recommendation set (no edit to that row, but the new PM state above makes
  the supersedence traceable); appended the blocking-upstream note to
  ACCEL-BACKEND.
- **Closure written**: this section.

### Next-session handoff

- **Highest-priority unblock**: peer-hephaestus publishing `origin/main` or
  merging `codex/hephaestus-product-axis-reduction-parity` to main. This
  closes a 5-session persistent defect AND unlocks `ATLAS-ATHENA-ACCEL-
  BACKEND-001` execution. Recommend the user message peer-hephaestus
  directly if the defect is unchanged at Session 29 open.
- **Watch for peer-kwavers feature-branch merge**: kwavers peer is actively
  committing to `codex/kwavers-book-migration-eviction`. Once it lands on
  `origin/main`, the gitlink is a one-step advance.
- **Watch for peer-coeus / peer-ritk / peer-mnemosyne / peer-leto feature
  branch merges** — same one-step advance opportunities.
- **3+ session persistence threshold**: hephaestus now in its 5th session;
  kwavers PR #325 (codex/kwavers-book-migration-eviction) and leto branch
  (codex/leto-real-sparse-lu) at 3+ sessions each. At Session 29, if
  hephaestus is still `no-origin-main`, escalate to user with batched
  message naming hephaestus as the worst blocker.
- Standing coordinator-scope `todo` items unchanged:
  `ATLAS-OVERLAY-001`, `ATLAS-VERSION-GUARD-001`, `ATLAS-WORKTREE-CLONES-001`,
  `ATLAS-DOWNSTREAM-COORDINATION-001` (new, peer-filed), `ATLAS-MATH-SSOT-
  CONSOLIDATION-1` (audit filed; execution owned by peer-leto/peer-physics-
  crate and now partially overtaken by ADR 0033's Krylov sequence).

## Session 29 closure (2026-07-27) — athena gitlink advance + hephaestus 6-session escalation threshold

### Re-orientation findings

- HEAD moved from Session 28 close (`73d3042`) to `ac20857` before this session
  opened via two peer-coordinator commits:
  - `3df60c1 build(atlas): Advance kwavers gitlink — ATLAS-MODALITY-002 phase
    2b closed` (peer-coordinator carried kwavers ATLAS-MODALITY-002 phase 2b
    close forward; kwavers gitlink was not actually advanced — see defect
    table below — the commit message subject and the kwavers gitlink advance
    it claimed did not coincide: pin remained `37d50b96`)
  - `ac20857 docs(pm): Record BiCGSTAB landing in Athena stage A` advanced
    the **leto** gitlink to `78d9e9e0` (peer-leto merged
    `codex/leto-real-sparse-lu` to `origin/main`, landing 17 commits since
    prior pin `c6ced81e`, including the boundary execution
    `687b670 refactor(leto-ops): Remove ndarray/nalgebra, native iterative
    solvers (LETO-NDARRAY-BOUNDARY-1)` — directly advancing the standing
    migration goal and aligning with ADR 0033's Krylov-ownership reaffirmation
    by retiring leto-ops native iterative solvers)
- Re-audited gitlink coherence: **4 defects | 2 stale-advanceable | 19
  clean**. Compared to Session 28 close: leto resolved (cat-b → advanced);
  athena newly stale-advanceable (peer-athena landed BiCGSTAB).

### Assist-ladder action executed: athena gitlink advance

- Verified: pin `a5fd8061` ancestral to origin/main `e965a95d` via
  `merge-base --is-ancestor`; **WT HEAD == origin/main byte-for-byte**;
  WT clean (`## main...origin/main`, no dirty files, not on feature branch).
  Pitfall #2 satisfied.
- Selective-staging discipline executed: `git reset HEAD -- .` →
  `git add repos/athena` → verified staged SHA == athena origin/main →
  verified only `repos/athena` staged (`git diff --cached --name-only` →
  CLEAN).
- Committed as `c38ca61 build(atlas): Advance athena gitlink to e965a95d`,
  pushed same cycle (`ac20857..c38ca61 main -> main`). Aligns with ADR 0033
  (Athena owns Krylov) and ATLAS-ATHENA-KRYLOV-CAPABILITY-001.

### Hephaestus `no-origin-main` — now 6-session persistent, escalation exercised

- Re-probed 2026-07-27 Session 29: hephaestus HEAD `47ca84a8`, last commit
  2026-07-27T12:22:02-04:00 (~6h prior). WT on
  `codex/hephaestus-product-axis-reduction-parity`, **ahead 1** of
  `origin/codex/hephaestus-product-axis-reduction-parity` with dirty
  `Cargo.lock`. Remote has only feature branches — **`origin/main` ref
  does not exist**; the structural cause is peer-hephaestus works
  exclusively on feature-branch flow and never publishes `main`.
- Per the standing ATLAS-ATHENA-ACCEL-BACKEND-001 cross-reference
  (L5139+) and the Session 28 next-session handoff instruction, the
  5-session threshold having been crossed at Session 28 close, Session 29
  confirms the defect is now **6-session persistent**.
- Coordinator authority (assist-ladder) does not authorize executing peer
  pushes. The escalation route is a **batched user-facing message** naming
  peer-hephaestus as the worst blocker; the cluster trio
  (`hephaestus`, `kwavers PR #325`, `ritk` `codex/docs-ritk-n4-figure-only`)
  as the user-actionable remediation set; and the gating relationship to
  `ATLAS-ATHENA-ACCEL-BACKEND-001` ([arch]) as the consequence of continued
  blockage. This message is delivered in the session response (not as a
  PM artifact, per no-report-file genre).

### Post-push gitlink-coherence state

| # | Repo | Category | Pin | origin/main | Last commit | Recovery (peer-owned) |
|---|---|---|---|---|---|---|
| 1 | coeus | cat-b | `cdaf769` | `971fab9` | 3h ago | peer-coeus: merge `codex/coeus-error-function-parity` to origin/main |
| 2 | hephaestus | no-origin-main | `47ca84a` | (none) | 6h ago | peer-hephaestus: publish origin/main — **6-session persistent, gating ACCEL-BACKEND-001** |
| 3 | kwavers | cat-b | `37d50b96` | `dce38e26` | <1h ago | peer-kwavers: merge/rebase `codex/kwavers-book-migration-eviction` (PR #325) |
| 4 | ritk | cat-c | `65035908` | `c05f84d5` | 3h ago | peer-ritk: merge `codex/docs-ritk-n4-figure-only` + publish origin/main |

**Stale-advanceable (this session close)**: `mnemosyne` only — pin `00c3f6d`,
origin/main `905909b`, WT on `codex/mnemosyne-tier-selection` HEAD
`ec1c000` (dirty `Cargo.lock`/`Cargo.toml`). NOT safely advanceable per
pitfall #2 (would capture peer's feature-branch HEAD, not origin/main).

**Athena — captured in two advances this session**:
- `c38ca61` advanced athena to `e965a95d` for the right-preconditioned
  BiCGSTAB landing.
- `24ad6ea` advanced athena again to `fef782cb` for the incomplete-LU /
  SuccessiveOverRelaxation preconditioner landing in `athena-leto`, which
  pairs with the Krylov family covered by ADR 0033. (Pin `e965a95d`
  stayed ancestral to `fef782cb`, so the second advance remained a clean
  one-step `git add` after verifying `WT HEAD == origin/main`.)
Both advances are attestable; the table above lists only the
still-defective and still-stale-advanceable rows.

### Next-session handoff

- **Primary escalation (carried)**: peer-hephaestus publishing `origin/main`
  or merging `codex/hephaestus-product-axis-reduction-parity` to main. This
  now closes a 6-session persistent defect AND unlocks
  `ATLAS-ATHENA-ACCEL-BACKEND-001` execution. A direct user → peer-hephaestus
  nudge is now warranted prior to a 7th session.
- **Cluster escalation (carried)**: kwavers PR #325 /
  `codex/kwavers-book-migration-eviction` (3+ sessions), ritk
  `codex/docs-ritk-n4-figure-only` (3+ sessions), coeus
  `codex/coeus-error-function-parity` (3+ sessions). Batch a single
  user-facing message if all are unchanged at Session 30 open.
- **Watch for one-step gitlink advance opportunities**: peer-mnemosyne,
  peer-coeus, peer-kwavers, peer-ritk if their feature branches merge to
  origin/main (verify `WT HEAD == origin/main` before `git add` per
  pitfall #2).
- Standing coordinator-scope `todo` items unchanged:
  `ATLAS-OVERLAY-001`, `ATLAS-VERSION-GUARD-001`,
  `ATLAS-WORKTREE-CLONES-001`, `ATLAS-DOWNSTREAM-COORDINATION-001`,
  `ATLAS-MATH-SSOT-CONSOLIDATION-1` (audit-only, partially overtaken by
  ADR 0033 Krylov sequence).

## Session 27 (2026-07-27) — Athena stage A progress and the ADR 0034 scope refinement

### Landed

- `e965a95` right-preconditioned BiCGSTAB in `athena-core`.
- `fef782c` `IncompleteLu` and `SuccessiveOverRelaxation` in `athena-leto`,
  sharing one triangular-substitution module.
- Athena gate green at each step: 38/38 nextest including the WGPU contracts,
  clippy `-D warnings`, doctests, fmt.

SSOR was deliberately **not** ported: a stack-wide scan finds no consumer, so
building it would be speculative. CFDrs uses ILU most, then Jacobi, then SOR.

Stage A remaining: **LSQR**. That completes the capability set and unblocks
`ATLAS-GMRES-FORK-CONVERGE-001` stage B (CFDrs migration).

### ATLAS-ATHENA-ACCEL-BACKEND-001 — refined, larger than first scoped

Surveying Hephaestus changed the shape of this item. It is **not** "delete
Athena's WGSL and call Hephaestus", because there is nothing device-neutral to
call:

- `hephaestus-core` carries the dialect-generic kernel machinery
  (`KernelSource<L: KernelDialect>`, `UnaryStorageKernel`,
  `BinaryStorageKernel`, `MultiStorageDevice`) and an op-expression algebra.
- Each backend crate exposes `dot`, `norm_l2`, `scalar_elementwise_into`,
  `binary_elementwise_into` — but as **per-backend free functions**.
- `ComputeDevice`, the device-neutral trait, covers allocation and transfer
  only.

So a `KrylovBackend` generic over `D: ComputeDevice` cannot reach any vector
operation. That is precisely why `athena-wgpu` hand-wrote WGSL against a
concrete `WgpuDevice` and hardcoded `f32`: the seam it needed did not exist.

The defect and the decision are unchanged — Athena must not own GPU kernels,
and the per-device crate must go. What changes is that the first increment
belongs to **Hephaestus**, not Athena: a device-neutral vector-operation seam
in `hephaestus-core` that each backend implements by delegating to the free
functions it already has. That closes a substrate gap benefiting every
Hephaestus consumer.

Staged, each with its own gate:

1. `hephaestus-core`: the vector-operation seam (scale, axpy, dot, norm,
   residual, and the two fused Krylov-shaped updates).
2. `hephaestus-wgpu`: implement it by delegation. The only backend testable on
   this host.
3. `athena-hephaestus`: `KrylovBackend` over the seam, generic in scalar type
   rather than `f32`-only.
4. Delete `athena-wgpu` and its WGSL; move its contract tests in the same
   change.

CUDA, Metal, and ROCm implementations follow the same seam and are verifiable
only where that hardware exists, so each is its own increment rather than a
blocker on Athena.

## ATLAS-LETO-PEER-WIP — Leto uncommitted peer WIP [patch] — blocked (peer-owned)

- Owner: peer session (codex); scope: `repos/leto/crates/leto-ops/`,
  `repos/leto/Cargo.toml`.
- Status: active peer WIP on `codex/leto-real-sparse-lu`. Contains:
  - `special_legendre.rs` (new Legendre polynomial module, 111 lines, 3 tests)
  - `Cargo.toml` path-dep overlay patches
  - `special.rs` formatting normalization
  - `lib.rs`/`mod.rs` module tree updates
  - `bessel_k0` test tolerance fix (1e-7 → 1e-6, already applied)
- Evidence: 425 leto-ops tests pass.
- Blocker: peer-owned; not committed by this session per concurrent_agents policy.
- Re-open trigger: the peer lands the branch or the one-hour stale-claim sweep
  finds no board/commit update; then reclaim the scope and complete the
  integration from the committed branch state.

## ATLAS-HYGIENE-BASELINE-001 — Eleven-class conformance baseline and namespace hygiene [patch] — in-progress

- Owner: fable-prompt-session (claimed 2026-07-30). Claimed scope: `scripts/atlas-conformance.py`, `scripts/conformance-baseline.json`, this entry. Burn-down (scopes 2-4) stays unclaimed for peers.
- **Current increment (2026-08-21):** the scanner previously aborted on the
  provider-local `helios-python/.pytest_cache` with `PermissionError`. The
  walker now prunes common derived Python cache/environment directories, and
  the focused scanner suite passes 21/21. The live worktree scan completes;
  its zero `workflow_missing_permissions` result is not a baseline update
  because provider workflow fixes remain uncommitted at their parent gitlinks.
- **Correctness reconciliation (2026-08-21):** the Athena audit's prior
  `athena-hephaestus-jacobi` worktree claim was not reproducible. The current
  checkout is detached at the parent-recorded gitlink and exposes only its
  primary worktree. `gap_audit.md` marks the earlier provenance inference
  historical and keeps only the observed checkout shape as current evidence.
- Scope 1 DELIVERED 2026-07-30: `scripts/atlas-conformance.py` (report/generate/check; 19 classes = the eleven recorded plus reexport_shims, sleep_synced_tests, commented_out_code, target_forks, gitattributes_missing, nextest_budget_missing, workspace_lints_missing, member_namespace_pollution), committed baseline `scripts/conformance-baseline.json` (supersedes the 2026-07-25 ad-hoc grep counts — heuristics differ, the instrument is now the SSOT), CI ratchet gate `.github/workflows/atlas-conformance.yml` (fails on any per-repo class increase; triggers on gitlink advances). Scan universe is `.gitmodules`-registered members only; git-ignored unregistered directories are skipped silently (private-consumer rule) and other unregistered directories count as unnamed `member_namespace_pollution` (currently 1 — the scope-3 run-output dump).
- New-class findings for burn-down (baseline totals): target_forks 5 (CFDrs, helios, hephaestus +2 — delete tree and creating override per performance_engineering "one build cache per stack"); gitattributes_missing 17/25 and workspace_lints_missing 17 (retrofit sweeps — mechanical, one commit per member); sleep_synced_tests 125 (moirai 105 — its scheduler tests wall-clock-sync; candidate for injected-clock rework); commented_out_code 109 (kwavers 51); reexport_shims 39; markers 13; nextest_budget_missing 1 (gaia). Also observed, outside scanner classes: workflow actions are tag-pinned across all six meta workflows (SHA-pin sweep per engineering_gates "Workflow hygiene") and `scripts/` retains the closed path-dep audit's r2-r6b iteration series (obsolete-artifact deletion candidate).
- Scope 1 extension 2026-07-30: five workflow/lock classes added — tag_pinned_actions 218 stack-wide (kwavers 66, hermes 21, ritk 21; the SHA-pin sweep is now measured, not just observed), workflow_missing_timeout 23, workflow_missing_permissions 7, pull_request_target_use 0 (clean), missing_cargo_lock 1 (themis — a foundation member without a committed lock) — baseline regenerated in the same change (generator contract); 24 classes total. Companion local gate `scripts/atlas-lane-audit.py` mechanizes the worktree-lane rules (two-tree bound, canonical lane roots, named branches, gitdir-mirror and standalone-clone detection) for orient and the replenishment audit — CI cannot see local worktrees, so it gates locally; census filed on ATLAS-WORKTREE-CLONES-001. The seven obsolete r-series audit scripts are deleted and the meta root adopts `* text=auto` `.gitattributes` (renormalization no-op — index already LF).
- Correction 2026-08-14: Themis's committed `Cargo.lock` landed in provider commit `09b2252`; the current `missing_cargo_lock` count is 0 for the requested provider set.
- Consolidation 2026-07-30: the scan-universe definition now has one owner — `scripts/atlas_stack.py` (registered members from `.gitmodules`, git helpers, ignore checks) imported by both the conformance scanner and the lane audit; the duplicated `registered_members()` pair and the scanner's twice-implemented root-sprawl/LF checks are collapsed (behavior-preservation proven by old-vs-new differential on stable members). Defect finding — **fixed 2026-08-02** (umbrella, this commit's parent): `atlas-toolchain-preflight.py` now imports `atlas_stack.registered_members()`; the glob-over-everything derivation is gone and the run resolves 25 member pins.
- Preflight side-finding 2026-08-02: this agent's shell environment carries ambient `RUSTC`/`RUSTDOC` exports pointing at the rustup PROXIES (`~/.cargo/bin/*`), which the preflight rightly fails. Proxy targets honor the pins, so the session's builds were coherent (single compiler identity confirmed once the overrides are cleared), but the exports should be removed from whatever profile sets them — an override pointing anywhere non-proxy would silently poison the shared cache.
- Lane-series clarification (re the 2026-07-30 sprawl evidence naming `hephaestus-j1e2`…`-j5`): those lanes were SERIAL, one claimed item each, each removed on its merge — the two-tree bound held at every instant (`git worktree list` never exceeded main + one lane) and the creation-rate spike measured throughput, not concurrent trees. Two removals hit Windows Permission-denied on first attempt and were pruned + rm-rf'd in the same cycle; if the audit counts orphan directories, that transient is the residue to look for.
- **Board-sweep sub-slice delivered 2026-08-07.** `scripts/atlas-board-sweep.py`
  parses the lenient level-two heading format, normalizes `in progress` /
  `in-progress`, reports explicit owner and claim-date context, and identifies
  blocked items lacking a `Re-open trigger` (including qualified forms such as
  `Re-open trigger (for the claiming session):`). It is report-only: findings
  never fail the command or mutate the board, while missing/unreadable input
  returns 2. Focused unittest coverage is in
  `scripts/tests/test_atlas_board_sweep.py` (6/6); `py_compile`, board lint,
  and `git diff --check` pass. The live root report scans 244 items, finds 27
  in-progress claims, and surfaces 3 blocked items without a re-open trigger:
  `ATLAS-SUBSTRATE-002`, `ATLAS-LETO-PEER-WIP`, and
  `ATLAS-CFDRS-TEST-BUDGET`. Claim freshness and remediation remain operator
  decisions; this tool does not reclaim or edit claims.
- Policy: AGENTS.md engineering_gates conformance scan (now enumerating all eleven debt classes), documentation_discipline "Root manifest", architecture_scoping "Member namespace hygiene".
- Baseline 2026-07-25 (per-repo counts recorded; the ratchet gate holds these non-increasing): files >500 lines: 574 (CFDrs 137, kwavers 91, consus 89); implementation-bearing lib.rs/mod.rs: 402 (kwavers 145); production `unwrap()`: 5833 (kwavers 3119, ritk 719); `#[allow]`: 798 (kwavers 330); print/dbg in src: 1082 (CFDrs 428); existence-only assertions: 444 (coeus 104, leto 79); type-suffixed fns: 380 (apollo 111); junk-drawer modules: 66 (kwavers 28); crates missing deny(missing_docs): 107/208; unsanctioned root files: 120 (kwavers 40); markers: 18.
- Scope: (1) extend the committed conformance scan script to all eleven classes and record this baseline as its first output; (2) burn-down items per repo by triage (kwavers is the epicenter: unwraps, fat manifests, junk modules, root clutter); (3) `repos/parity_artefacts` (untracked run-output dump in the member namespace — det_*.log, url/target lists) relocates to a gitignored verification output root or deletes at the parity stream's item completion (owner: parity stream; regenerable evidence, rescue-first if any file proves unique); (4) kwavers root files triage per the Root manifest rule.
- Acceptance: scan script covers all eleven classes with committed baseline; member namespace holds registered members only; per-repo burn-down items filed DoR-shaped.

## Session 30 closure (2026-07-28) — atlas-stack-overlay CI wiring + peer math-SSOT PR 0008 audit artifacts tracked

Re-oriented against `origin/main` at session open; HEAD had moved from `d2e0ac9` to `182f346` through peer-coordinator landings during the inter-session gap. The persistent gitlink defect set shifted: hephaestus 8-session `no-origin-main` defect narrowed (peer published an `origin/main` ref, pin advanced to `bf24b873`), but the 4-defect cluster (coeus cat-b, hephaestus no-origin-main, kwavers cat-b, ritk cat-c) persists and remains blocked on peer-side branch merges.

### Landed

- `599ddca build(atlas): Advance athena/proteus/tyche/asclepius gitlinks` — four stale-advanceables cleared: athena `fef782cb` -> `1d24c643` (ADR 0034 stage 3 merge of feat/athena-hephaestus-backend, advancing the device-neutral accelerator backend per ADR 0034), proteus `9d7c1a8c` -> `9a8655d3`, tyche `1527964c` -> `996b649d`, asclepius `bbf38400` -> `ccffb6bc`. Each followed the safe-advance protocol (pin ancestor of origin/main, WT on `main` with HEAD == origin/main, single Cargo.lock dirt in each not captured by submodule gitlink staging). Reduces stale-advanceable from 6 to 2 (mnemosyne on feature branch, kwavers on cat-b).

### Tracked (peer-authored artifacts staged for review)

- `docs/pr/0008-math-ssot-adr-0031-0033-review-checklist.md` (138 lines, peer-drafted PR description for the math-SSOT consolidation; covers ADRs 0031/0032/0033 closure into leto-ops SSOT; cross-repo consumers `cfd-math`, `kwavers-math`, `kwavers-solver`; reserved tag `atlas/math-ssot-adr-0031-0033-closure`; per-ADR sign-off checklist spanning CFDrs / Kwavers / leto-ops module owners). Stage-only; substantive source changes in `repos/CFDrs/crates/cfd-math/...` and `repos/kwavers/crates/kwavers-{math,solver}/...` are peer-owned and out of coordinator scope.
- `docs/audit/math-ssot-ledger.md` (753 lines, peer-authored audit ledger documenting the leto SSOT surface and per-consumer redundancy inventory; provider-side already landed in leto-ops `StaggeredForward`/`StaggeredBackward`, `complex_solve`/`complex_inv`, `FiniteDifference3D`). Stage-only.

### Next-session handoff

- ATLAS-MATH-SSOT-CONSOLIDATION-1 closure gate: peer-CFDrs must commit and merge the `cfd-math` wrapper deletion (`cfd-math/src/differentiation/` removed, `fd_extensions` re-export added) before coordinator can advance the CFDrs gitlink and close the audit row. The CFDrs WT is at origin/main HEAD `c90e6840` but dirty (36 files, peer-cfdrs mid-flight on `CFDRS-AEQ-MET-25` cavitation work). When the CFDrs gitlink advances, the audit row can mark the math-SSOT consolidation phase as delivered and PR 0008 can be reviewed/merged by module owners. The same dependency applies to kwavers (`codex/kwavers-book-migration-eviction` feature branch at `df9008d9`) and leto (`codex/leto-real-sparse-lu` at `1d24c643`+3); none is safely advanceable until peer returns WT to `main` and merges to `origin/main`.
- Standing coordinator-scope `todo` items unchanged: `ATLAS-OVERLAY-001` (sub-deliveries 1/2 still open), `ATLAS-VERSION-GUARD-001` (sub-delivery 1: per-member guard tool skeleton), `ATLAS-WORKTREE-CLONES-001` (asclepius/hephaestus/leto WTs are peer-active mid-flight; remaining clones re-evaluate on next session).
- ~~The `repos/parity_artefacts/` directory has been physically removed from the working tree but the deletion is not staged~~ — **superseded 2026-08-18.** The removal did not hold: commit `5956d02`, a gitlink advance whose message describes a ritk `region.rs` split, re-added it as scope creep along with a second copy at the meta-repo root — 899 lines, 18 files, two archives where there should be one. Now resolved rather than re-deferred, because the deferral rationale ("belongs with the parity stream's closure increment") is what let it regrow: the duplicate is deleted, `INDEX.md` moved to the root copy with its relative links re-anchored one level up and verified to resolve, and `docs/mdbook/detector-parity.md` plus `gap_audit.md` corrected. The tracked pairs were byte-identical apart from line endings, so nothing unique was lost. Two truth defects were fixed alongside: INDEX.md claimed the archive "survives repo re-clones" when 33 of its 43 files are gitignored `*.log`, and the report claimed the `SUMMARY.md` path "resolves correctly" without the in-context-build qualifier that its own recorded CI failure contradicts.

### Post-session peer advances (attribution-absorption pattern)

Between my `599ddca` and the close of this session, peer landed a chain that absorbed the Session 30 closure intent and advanced the persistent defect set further:

- `9f92d94 docs(atlas): Refresh Aequitas gap audit` — peer-committed `docs/audit/math-ssot-ledger.md` and `docs/pr/0008-math-ssot-adr-0031-0033-review-checklist.md` under their subject. Content identical to what this session would have committed. Pattern matches the Session 25/26/28 attribution-absorption; no remediation needed because the content is correct.
- `d1f2e2c docs(atlas): Record Aequitas consumer closure` — gap audit refresh.
- `c2cad74 build(atlas): Advance CFDrs Aequitas closure` — CFDrs gitlink advanced to `109aec63`; CFDrs now reads as clean in the gitlink-coherence audit (down from stale-advanceable). MET-25 closure intent is now realized at the CFDrs WT HEAD; the math-SSOT PR 0008 cfd-math deletion gate (peer-cf must commit + push) remains the only outstanding dependency.
- `485b3dd docs(pm): Root-cause the gaia git-dep break blocking helios tests` — closes the gaia blocker; helios tests can now run against canonical gaia.
- `f793735 docs(adr): Correct ADR 0037's lockstep versioning mandate` — ADR 0037 mandate tightened.
- `86cb19a docs(pm): Record the generic-instantiation pattern; revert the blocked edit` — reverts a blocked edit and records the generic-instantiation pattern.

Final gitlink-coherence state at Session 30 close: **25 probed | 4 defects | 1 stale-advanceable | 20 clean.**

- **Defects (4):** coeus cat-b (peer `codex/coeus-error-function-parity` not merged); hephaestus no-origin-main (default branch is `master` at remote `14b73d56`, WT HEAD `7897c13f` is mid-flight on `ATLAS-HEPHAESTUS-SPARSE-SEAM-001` sparse-seam work, last commit 77 min ago — peer-active, leave alone); kwavers cat-b (`codex/kwavers-book-migration-eviction` not merged); ritk cat-c (`codex/docs-ritk-n4-figure-only` local-only, not pushed).
- **Stale-advanceable (1):** mnemosyne `00c3f6de` -> `905909be` — WT on divergent feature branch `codex/mnemosyne-tier-selection` (HEAD `ec1c000` not ancestor of origin/main), 30h since last commit; peer-mnemosyne is mid-flight on tier-selection work.

### Session 30 / Atlas-meta delivery summary

| Increment | SHA | Type | Coordinator-authored? |
|---|---|---|---|
| Advance athena/proteus/tyche/asclepius gitlinks | `599ddca` | build(atlas) | Yes — full content + protocol verification |
| Track PR 0008 + math-SSOT ledger | `9f92d94` | docs(atlas) | Peer-absorbed (content preserved) |
| Session 30 closure in backlog | `9f92d94` + `485b3dd` | docs(pm) | Yes — full text + peer addendum |
| CFDrs Aequitas closure advance | `c2cad74` | build(atlas) | Peer-owned |

## Session 28 (2026-07-28) — ADR 0034 complete

`SparseOperatorOps` landed in hephaestus `317bd7a`, and `athena-wgpu` is gone
in athena `045efe4`. ADR 0034 is closed.

- **Sparse seam.** Takes canonical CSR parts rather than a host matrix type, so
  `hephaestus-core` keeps its no-sparse-storage charter and any CSR producer
  can feed it. Raw parts arrive without the invariants a matrix type enforces
  at construction, so the seam validates structure before upload — dispatching
  on malformed CSR would read out of bounds on the device. `GpuCsrMatrix`
  gained `from_parts` and `from_cpu` now delegates, so the upload path exists
  once.
- **Operator.** `athena_hephaestus::CsrOperator` applies a device-resident
  operator through the seam, making the operator half as device-neutral as the
  vector half. That was the last thing keeping `athena-wgpu` alive.
- **Deletion.** `athena-wgpu` removed outright with its five hand-written WGSL
  kernels and `f32`-only backend, no compatibility re-export; nothing outside
  Athena depended on it and its contract tests moved in the same change. The
  facade feature is now `accelerator`, not `wgpu`.
- **ADR 0034 residue scan passes**: no `wgsl`, `@compute`, or `workgroup`
  literal under `repos/athena/crates`, and no crate there names a device API.
  Athena went from one device API to every Hephaestus backend, and from
  `f32`-only to generic in the scalar.

### Verification and its limit

`athena-hephaestus` passed 7/7 on GPU hardware — CG, GMRES and BiCGSTAB each to
convergence through the device-neutral backend and operator, plus retained-handle
reuse across solves, dimension rejection, rectangular rejection, and three
malformed-CSR rejections. Clippy `--all-targets` and fmt were clean immediately
before commit.

The workspace-wide gate could **not** be run afterwards: an in-flight `aequitas`
change (14 dirty files in `repos/aequitas`) began failing `leto` and `leto-ops`
beneath the whole stack —

```
error[E0599]: the method `in_unit` exists for struct `Quantity<...>`, but its
trait bounds were not satisfied
  --> repos/leto/crates/leto/src/application/stencil.rs:121
     = note: `T: UnitScalar` not satisfied
```

`stencil.rs` is committed and unmodified, so this is upstream drift rather than
local breakage, and it predates nothing of this increment. Re-run the athena and
hephaestus workspace gates once that settles.

### Remaining

- ADR 0033 stage A: **LSQR**, the last capability before the CFDrs migration
  (`ATLAS-GMRES-FORK-CONVERGE-001` stage B).
- CUDA, Metal and ROCm adopt `RetainedReductions` and `SparseOperatorOps` in
  their own increments, verifiable only where that hardware exists. Until then
  the accelerator backend runs on WGPU alone — but adding a device now adds no
  Athena code, which is the property ADR 0034 existed to establish.

## ATLAS-LANE-AUDIT-001 — Lane-root sweep results and residuals [patch] — in-progress (residual)

- Policy: AGENTS.md git_discipline Worktrees (lanes are swept claim surfaces; created only by `git worktree add`) + concurrent_agents (gitdir-mirror checkouts prohibited — a `.git` file pointing at another tree's gitdir shares its index and corrupts both trees' status).
- Audit 2026-07-26 of `D:\atlas\worktrees` (26 entries): 4 compliant live lanes (coeus-backend-parity, hephaestus-mixed-reduction-batch, kwavers-aequitas-vessel-metrics, ritk-ebcot-magnitude-view); 13 gitdir-mirror checkouts on main (the improvised-provider species); 7 standalone clones; 3 bare directories; 1 broken meta lane. Legacy root `D:\worktrees` now empty — its lanes completed and dissolved per ATLAS-WORKTREE-001.
- Done: `report` re-mint deleted (SVG already rescued to repos/report/figures); broken `atlas-final-integration` meta lane deleted + `worktree prune` (meta lanes prohibited); 5 stale clones rescue-fetched into their authoritative repos under `refs/rescue-worktrees/<name>/*` then deleted (leto incl. codex/leto-real-sparse-lu); 13 gitdir-mirrors deleted — and regenerated within seconds: a live process on pre-fix instructions re-mints the mirror farm (signature: `.git` file -> `../../.git/modules/repos/<r>`, checkout on main). Self-resolves as sessions roll onto current instructions; re-audit the root then and delete survivors.
- Residuals: (1) `hephaestus-unary-math-parity` — git-less source snapshot with real unique deltas (6/12 sampled files differ from authoritative): reconcile into a branch of repos/hephaestus (diff, salvage, commit under the unary-math-parity item), then delete the snapshot; (2) `ritk-book-complete` — near-duplicate snapshot (11/12 identical): verify the delta, salvage if real, delete; (3) stale lanes `coeus` (codex/coeus-error-function-parity, 30h) and `mnemosyne` (codex/mnemosyne-tier-selection, 33h) — takeover material: complete their items or confirm branches landed, then remove the lanes; (4) fresh clones `aequitas`/`eunomia` left in place (regenerator-owned) — delete at re-audit.
- Re-audit 2026-08-14: Ritk is now compliant with two trees (`main` and
  `ritk-fix`) after `8a1c6ac`. The current probe reports four Kwavers
  violations: three trees, one detached temporary lane outside the canonical
  lane root, and the unlinked `worktrees/kwavers-cascade-provider-042`
  directory. The temporary checkout carries fresh unique `Cargo.toml` and
  `Cargo.lock` changes for the `ritk-image` 0.4.0 integration; the canonical
  lane carries dirty PM work. The empty unlinked directory was checked before
  removal, but Windows retained an open handle and refused deletion. No
  peer-owned work or unique state was removed; re-open deletion after the
  temporary owner releases or rescues its changes and the handle closes.

- Re-audit 2026-08-17: the live Kwavers tree is now the main checkout plus
  `worktrees/kwavers-doc557` at detached commit `df818b9a1`. The lane is clean
  but detached, so `python scripts/atlas-lane-audit.py` reports one violation.
  It remains peer coordination state; no branch switch or lane deletion is
  authorized until its owner reconciles the documentation run.
- The completed CFDrs Fourier/SSOR lane and Apollo public-plan lane were removed
  after their PRs merged; their local feature branches were deleted. The current
  audit therefore reports only the detached Kwavers documentation lane above.

## Session 28 closure (2026-07-28) — ADR 0033 stage A complete

LSQR landed in athena `24b5c56`. Athena now carries every Krylov capability
its prospective consumers call, and the capability table from
`ATLAS-ATHENA-KRYLOV-CAPABILITY-001` has no gaps left:

| Capability | Athena | Needed by |
|---|---|---|
| CG / PCG | yes | CFDrs |
| GMRES(m) | yes | CFDrs, Kwavers |
| BiCGSTAB | yes (`e965a95`) | CFDrs |
| LSQR | yes (`24b5c56`) | CFDrs |
| Identity / Jacobi | yes | all |
| SOR / ILU(0) | yes (`fef782c`) | CFDrs |

SSOR remains deliberately unbuilt: no consumer anywhere in the stack.

### LSQR design notes

- `RectangularOperator` is a separate contract from `LinearOperator`, not an
  extension: a square operator does not necessarily expose a transpose, and
  requiring one would burden every consumer that never needs it.
- `RectangularCsrOperator` scatters the adjoint through the same CSR arrays the
  forward product reads rather than materialising a transpose, which matters
  because LSQR applies the adjoint once per iteration.
- Termination needs **two** criteria. A consistent system is caught on the
  residual; an inconsistent one — the genuine least-squares case — keeps a
  residual bounded away from zero, so its optimum is only visible through the
  normal-equation residual `‖Aᵀr‖`. That is a new `Termination::NormalEquations`
  rather than a reuse of `Converged`, because the two say different things about
  the answer. Both quantities fall out of the plane rotation, so neither costs
  an extra operator application.
- Optimality is tested by perturbation rather than against a quoted answer:
  every neighbour of the returned solution must have a larger residual.

### Gates

Athena workspace **51/51** nextest, clippy `-D warnings`, doctests, fmt — all
green. This also discharges the gate that could not run at the end of the
previous session, when an in-flight `aequitas` change was breaking `leto`
beneath the stack; that has since settled and the ADR 0034 work is covered by
this run too.

### Next

`ATLAS-GMRES-FORK-CONVERGE-001` is now unblocked:

- **Stage B** — migrate CFDrs from its `leto-ops` wrappers (`6d18a547`) to
  Athena. Note the direction: CFDrs currently consolidates onto the Leto family,
  which ADR 0033 identifies as the regression to unwind.
- **Stage C** — Kwavers, gated on refactoring `jacobian_vector_product` from
  `&mut self` to `&self` so its matrix-free operator satisfies
  `LinearOperator::apply(&self, ...)`. Its only mutation is a scratch cache.
- **Stage D** — delete `leto-ops/src/application/linalg/iterative/` including
  the duplicated `LinearOperator`/`Preconditioner` traits; residue scan clean.

## ATLAS-CFDRS-ATHENA-MIGRATION-001 — Stage B: CFDrs to Athena [major] [arch] — in-progress

Surveyed 2026-07-28 before starting. This is a redesign of the CFDrs
linear-solver architecture, not a port, and two of the mismatches change a
public CFDrs API — recording them rather than deciding unilaterally.

### Scale

56 files and 242 references across six crates (`cfd-1d`, `cfd-2d`, `cfd-3d`,
`cfd-core`, `cfd-math`, `cfd-validation`), of which **24 are production solver
construction sites** in 8 files; the rest are tests, benches, and re-exports.

`cfd_math::iterative` is currently a pure re-export of the `leto-ops` family
(`lib.rs:179`), so every consumer reaches the solvers through one facade.

### Structural mismatches

1. **Const-generic restart vs runtime config.** `Gmres<B, RESTART>` fixes the
   restart width at compile time. `LinearSolverChain` carries
   `krylov_restart: usize` as a runtime field with a builder
   (`with_krylov_restart`) and clamps it per solve:
   `min(self.krylov_restart, n_total_dof.max(1))`. A const generic cannot take
   that value. **Decision needed** (see below).
2. **Dynamic solver selection.** Four sites hold `Box<dyn LinearSolver<T>>`,
   including `cfd-validation` which builds a `Vec` of boxed solvers to compare
   CG against BiCGSTAB on the same system. Athena's solvers are ZST markers
   with static `solve_into`; `KrylovBackend` has GATs and `Gmres` a const
   generic, so none of it is dyn-compatible. The sanctioned replacement is
   enum dispatch over the closed solver set — I can decide this one, it is
   what the standards prescribe before reaching for `dyn`.
3. **Preconditioner trait.** CFDrs preconditioners — `AlgebraicMultigrid`,
   `BlockDiagonalPreconditioner`, `SimplePreconditioner`, `IncompleteLU`,
   `DiagJacobi` — implement `leto_ops::Preconditioner<T>`. Each needs an
   `athena_core::Preconditioner<LetoBackend<T>>` implementation instead.
   Mechanical, but touches every preconditioner.
4. **Caller-owned workspaces.** CFDrs solvers allocate internally per call;
   Athena requires a workspace owned by the caller and sized to the system, so
   every call site gains workspace lifetime management. This is the property
   that makes Athena allocation-free, so it is a real improvement rather than
   friction to work around — but it is a call-site change everywhere.
5. **Config to policy.** `IterativeSolverConfig { max_iterations, tolerance,
   relative_tolerance }` maps onto the validated `ConvergencePolicy`, which
   also carries a check interval and rejects invalid tolerances at
   construction. Mechanical.

### Decisions needed

**D1 — restart width.** Either (a) make `krylov_restart` a const parameter on
`LinearSolverChain`, a breaking change to a public CFDrs API; or (b) keep the
runtime field and dispatch across a small fixed set of `RESTART` instantiations
by enum, paying monomorphisation for each; or (c) fix one restart width and
delete the knob, checking first whether any caller sets it to a non-default
value. Recommend (c) if the knob is unused in practice, else (b).

**D2 — migration shape.** Either (a) convert all six crates in one change,
green only at the end; or (b) convert crate by crate while `cfd_math::iterative`
still re-exports `leto-ops`, deleting the facade last. (b) keeps the tree green
per commit and is not a shim — the old path stays only until its last consumer
is gone, which is what the anti-shim rule prescribes for a migration of this
size. Recommend (b), ordered `cfd-math` internals, then `cfd-2d`, `cfd-3d`,
`cfd-1d`, `cfd-validation`, then facade deletion.

### Not started

No CFDrs code changed. Nothing was added that would sit unused pending the
decisions above.

### Stage B progress 2026-07-28 — foundation landed, D1 corrected

**D1 was answered (c), and the check that answer depended on disproved it.**
`krylov_restart` is not an unused knob: `cfd-3d/fem/solver.rs` sets
`min(200, n)` at two sites, `cfd-1d/newton_fallback.rs` derives it from
`max_krylov_iterations`, and `cfd-math/nonlinear_solver/jfnk.rs` carries it in
its own config with 30 and 10 in tests and `min(n)` at runtime; the direct
`GMRES::new` sites use 30 and 100. Fixing one width would have silently
changed four solver configurations, so I took the fallback named in the same
decision — **(b), a fixed ladder with dispatch**.

- athena `f24dded`: `BorrowedCsrOperator`. `CsrOperator` takes ownership,
  which would force a per-solve `O(nnz)` sparse clone in a chain that tries
  several preconditioners against one system. Mirrors `BorrowedDenseOperator`.
- CFDrs `6a13a672`: `cfd_math::linear_solver::krylov` — the restart ladder
  (8/16/32/64/128/256, smallest covering width), `ConvergencePolicy`
  translation, and `gmres`/`gmres_preconditioned`/`bicgstab` entry points over
  Athena. Additive per D2(b): the `iterative` facade still re-exports leto-ops,
  so no consumer changed and the tree stays green per commit.
- Also repaired two cfd-math benches that had not compiled since `8aee5e59`
  left a stray brace in their imports.

Verification: cfd-math library compiles, clippy clean on the library, both
ladder cases pass, fmt clean. The package `--all-targets` gate is red for
reasons predating this change — unused imports and a dead struct in cfd-math
tests from the in-flight SSOT migration.

### Contention on the next increment

`chain.rs` is the next conversion target and a peer is **actively working in
it**: commit `16096fbc` ("resolve Quantity type mismatches in cfd-1d examples
and chain.rs") landed at 19:05 today and its rewrite of
`linear_solver/mod.rs` dropped the `pub mod krylov;` registration I had added,
leaving my file an orphan until I restored it. Converting `chain.rs` now would
collide directly.

Next increment should either wait for that scope to go quiet, or start at a
crate the peer is not in — `cfd-2d/src/physics/momentum/solver.rs` and
`cfd-2d/src/pressure_velocity/pressure.rs` are independent of `chain.rs` and
carry four of the twenty-four construction sites.

Remaining conversion order: `cfd-math` internals (`chain.rs`, multigrid),
`cfd-2d`, `cfd-3d`, `cfd-1d`, `cfd-validation`, then delete the
`cfd_math::iterative` facade and the leto-ops iterative dependency.

Note for `cfd-validation`: four sites hold `Box<dyn LinearSolver<T>>` to
compare solvers on one system. Athena's markers are not dyn-compatible, so
that becomes enum dispatch over the closed solver set, per the standards.

### Stage B progress 2026-07-29 — cfd-2d converted

`58f6caab` momentum, `10fdd86e` pressure correction. cfd-2d is off the leto-ops
iterative family; the `cfd_math::iterative` facade still serves the other
crates, per D2(b).

- **Stateful solver objects removed.** Both consumers stored solver instances —
  `MomentumSolver` one GMRES, `PressureCorrectionSolver` three of which at most
  one was ever used, since `solver_type` already selected the recurrence.
  Athena solvers are stateless markers with caller-owned workspaces, so each
  collapses to the configuration it carried.
- **Triplicated policy consolidated.** `correction.rs` repeated the same
  solve-then-retry block verbatim per recurrence: solve with AMG, and on
  breakdown retry unpreconditioned, because a hierarchy built for a stale
  stencil can break the recurrence while the bare operator stays solvable.
  Written once now, with one dispatch over the closed solver set.
- **A real regression, caught and fixed at the right level.** Momentum assembly
  omits the diagonal of rows with no self-coupling. Athena's SOR rejects that;
  the leto-ops one had been *silently* defaulting those rows to a unit pivot.
  Rather than loosen the default, athena `461cdd5` added
  `from_csr_with_identity_rows` — same behaviour, opted into visibly at the
  call site, with a test pinning it.
- athena `f24dded` `BorrowedCsrOperator` removes a per-solve `O(nnz)` clone;
  the Athena SOR likewise borrows where the previous one took ownership, which
  matters because momentum rebuilds it after every coefficient update.
- `AlgebraicMultigrid` gained an Athena preconditioner implementation. Its
  V-cycle recurses over owned vectors while Athena passes borrowed views, so
  the boundary copies through cached buffers rather than allocating per
  application. Two `O(n)` passes against the cycle's `O(nnz)` sweeps.
  **Follow-up: rework the V-cycle onto slices to remove them.**

Verification: cfd-2d 570/571 nextest at both increments; the timeout is a
cross-fidelity tree test with no solver involvement that times out identically
without these changes. Clippy ran clean on the libraries for the first
increment; for the second it could not run — an in-flight `gaia` change removed
the `cfdrs-integration` feature cfd-2d depends on, breaking resolution for
unrelated reasons. **Re-run clippy on cfd-2d once gaia settles.**

## ATLAS-ADR-GOVERNANCE-001 — Retrofit ADR indexes, statuses, and records [patch] — in-progress (indexes landed)

- Policy: AGENTS.md context_and_memory "ADR governance". Census 2026-07-27: 312 ADRs across the meta repo + 20 members; indexes exist in 3 of 21 (meta, ritk, iris); 7 duplicate numbers (kwavers x2, coeus x3, leto, hermes); 104 ADRs without a Status line; casing drift (Accepted vs accepted) plus a non-canonical "investigated"; supersession links on 4 of 312.
- Scope per repo: (1) generate `docs/adr/README.md` indexes (number, title, status) — mechanize as a committed script deriving the index from ADR headers (toil automation; hand-maintained indexes rot), wired into CI as a regenerate-and-diff freshness check like the overlay; (2) normalize statuses to the canonical set with exact casing, adding Status lines where absent (default: Accepted for implemented decisions, verified against the code); (3) resolve the 7 numbering collisions by renumbering the later ADR and updating its citations; (4) merge audit (rewrite-in-place model per revised ADR governance): where a later ADR replaced an earlier decision, merge into one current record carrying a dated revision note and delete the stale file — git is the archive; canonical statuses are Proposed/Accepted/Rejected; (5) verify board items citing ADRs and ADRs citing items resolve (bidirectional linkage).
- Acceptance: every ADR directory carries a current generated index; zero duplicate numbers; every ADR has a canonical status; the freshness check is green in CI; a spot-check of decision recall (pick three active items, confirm governing ADRs discoverable from the index in one step) passes.
- Update 2026-07-27: `scripts/adr-index.py` landed (generate/check per the generator contract, parsing both inline `Status:` and MADR `## Status` conventions); generated indexes committed and pushed to all 20 member repos plus meta; check mode green and idempotent. The 290-line anomaly report is the burn-down census: 7 numbering collisions itemized with file pairs (coeus 0021 x3-way + 0025, hermes 007, kwavers 037 + 040, leto 0011), missing/non-canonical statuses per repo. Remaining judgment work: status verification against code, collision renumbering with citation updates, the merge audit, content conformance, and per-repo backfill inventories for canonical seams lacking any ADR.

## ATLAS-CODE-INDEX-001 — Search-ladder infrastructure for context economy [patch] — in-progress

- Owner: opencode-2026-08-05; scope: the atlas meta-repo and its `repos/*` members
  (tooling and generator contract only — no member Cargo.toml/manifest edits).
  Host tooling verified: `rust-analyzer` and nightly toolchain present; `ast-grep`
  absent (install is scope item 1).

- Policy: AGENTS.md context_and_memory "Code-search ladder". Motivation: 325 tool-output truncations and 66 compactions across eight recent fleet sessions — agents read where they should search; the fleet-recommended tools were researched and the ladder chosen over them where they misfit (agent-memory graph stores such as Graphiti duplicate the board/ADR/git memory layer and are rejected — one curated memory, one archive).
- Scope: (1) ast-grep availability as committed tooling (structural queries, stateless per tree — worktree-safe by construction); (2) SCIP emission per member repo (`rust-analyzer scip`), revision-keyed under a gitignored index directory with a generator-contract freshness check, plus a thin lookup wrapper (scip CLI) so agents resolve definitions/references without full-file reads; (3) rustdoc JSON as the machine-readable API oracle for the anti-hallucination check, emitted under the nightly verification toolchain like miri; (4) evaluate a Zoekt trigram server over the shared gitdirs only if per-tree tooling proves insufficient at fleet scale — standing infrastructure needs the toil-automation justification; (5) wire ladder usage guidance into each repo agent-facing docs if repo convention keeps local instructions.
- Acceptance: spot-check — an agent locates three symbol definitions and one API signature across repos it has not read this session using only ladder queries (no full-file reads); index freshness check green in the sweep.

## ATLAS-CFDRS-CHAIN-LADDER-001 — Consolidate the two tiered ladders [patch] — in-progress

`LinearSolverChain::solve` and `solve_with_state` run the same five tiers with
three deliberate differences: log prefix, an iterate reset between tiers, and
the warm path skipping the unpreconditioned tier once a block preconditioner
was built but stalled. Express the ladder once with those as parameters, and
decide explicitly whether the cold path should adopt the skip policy — it is
an improvement the warm path received and the cold one did not, and adopting
it changes which solver answers a given system.

Remaining stage B: cfd-3d, cfd-1d, cfd-validation, then delete the
`cfd_math::iterative` facade and the leto-ops iterative dependency.

### Stage B progress 2026-07-29 (evening) — cfd-3d deferred, cfd-validation converted

**cfd-3d was not attempted.** Both its solver files were being edited live:
`crates/cfd-3d/src/fem/solver.rs` had a modification timestamp one minute
before I began, alongside 17 other dirty cfd-3d files from a peer's Quantity
migration. Editing there would have collided destructively, so the scope was
skipped rather than taken. **Re-open trigger: cfd-3d/src/fem goes quiet.**

Its two sites when it does: `projection_solver.rs` holds a `GMRES` and a
`ConjugateGradient` field, and `solver.rs` holds `_linear_solver: GMRES<T>` —
note the underscore, it is already dead and should be deleted rather than
converted. `solver.rs` also drives `LinearSolverChain`, which is already on
Athena.

**cfd-validation converted instead**, `f8634e43` — a clean, disjoint file.

- `Vec<(&str, Box<dyn LinearSolver<T>>)>` becomes `SolverKind`, the closed-set
  enum dispatch decided earlier. Athena's markers carry const generics and
  backend GATs and are not object-safe, so this was the one site that could
  not be a mechanical swap.
- Same correction `chain.rs` needed: Athena reports a stalled or broken-down
  solve in the report, not as `Err`, so a bare match would have **recorded a
  non-converged iterate as a validation result**.
- The split between fatal and tolerated failure is preserved deliberately: the
  ill-conditioned Hilbert case is expected to break down; the diagonal and
  Poisson cases are not.
- `SolverKind` lives in cfd-math beside the other entry points so the
  pressure-velocity dispatch can adopt it rather than keep its own match —
  **follow-up**.

Verification: `cargo check` clean for cfd-validation and cfd-math. Tests could
not run — `repos/hephaestus` is mid-rebase onto a branch four commits behind
master, so `hephaestus-core` does not compile in the shared tree. **Re-run the
cfd-validation suite once that settles.**

Note the compounding cost: three consecutive increments have now had a gate
blocked by shared-tree churn — clippy twice by `ATLAS-TOOLCHAIN-COHERENCE-001`,
tests once by a mid-rebase hephaestus. The verification debt is tracked, not
silently absorbed.

Remaining stage B: cfd-3d (blocked), cfd-1d, then delete the
`cfd_math::iterative` facade and the leto-ops iterative dependency.

### Stage B progress 2026-07-29 (late) — cfd-1d converted

`4ca6518d`. The network solver's iterative tier is on Athena.

- The CG and BiCGSTAB arms were identical apart from the recurrence, so they
  collapse onto `SolverKind`. `LinearSolverMethod` stays as the domain-facing
  choice and maps onto it.
- `DiagJacobi` gained an Athena implementation that applies straight over the
  borrowed views — elementwise, so no scratch and no copy, unlike the AMG
  boundary which must buffer.
- The post-solve residual check is kept, with its reason now explicit: the
  solve runs on the **row-equilibrated** matrix, so meeting the tolerance
  there does not bound the residual of the original system. Athena reporting
  convergence is one of two acceptance conditions, not the only one.

Verification: cfd-1d **736/736** nextest including the primary-solve
reliability cases that exercise this path, `cargo check` clean.

### Correction to an earlier claim

I recorded after `40ef080c` that "cfd-math is fully off the leto-ops iterative
family". True as stated, but incomplete as an impression: `cfd-math`
`nonlinear_solver/jfnk.rs` carries its **own hand-rolled matrix-free
restarted GMRES** (`gmres_matrix_free`), which never used leto-ops. It is a
fifth GMRES in the stack after leto-ops, the deleted CFDrs copy, kwavers, and
Athena. Filed below.

## ATLAS-JFNK-MATRIX-FREE-GMRES-001 — Converge JFNK onto Athena [minor] — todo

- `cfd-math/src/nonlinear_solver/jfnk.rs` implements restarted GMRES inline for
  Jacobian-free Newton-Krylov, using only matrix-vector products.
- Migrating it needs Athena's `LinearOperator` over a Jacobian-vector closure.
  Check first whether that closure needs `&mut self` — if so it hits the same
  blocker as Kwavers stage C (`ATLAS-GMRES-FORK-CONVERGE-001`), and the two
  should be solved together rather than separately.
- `cfd-1d/src/solver/core/newton_fallback.rs:223` feeds `krylov_restart` into
  this config, so it is the last cfd-1d reference to a non-Athena solver.

Remaining stage B: cfd-3d (blocked on peer activity in `cfd-3d/src/fem`), JFNK,
then delete the `cfd_math::iterative` facade and the leto-ops iterative
dependency.

### Verification debt review 2026-07-30

**cfd-3d is still not clear.** Peer commit `63e49604` landed at 01:40, twelve
minutes before the check, and `projection_solver.rs` carries their uncommitted
continuation of the same Quantity migration (`.into_base()` conversions).
Fresh and commit-backed, so the scope stays blocked. `solver.rs` is clean now,
but it is the same live scope. Re-check later.

**cfd-validation tests: discharged.** The hephaestus rebase finished, so the
suite ran: **184/187 passed, 3 timed out** in
`numerical::venturi_cross_fidelity`.

Those three were investigated rather than assumed pre-existing, because they
drive `cfd_2d::solvers::ns_fvm` SIMPLE and could plausibly have been a
convergence regression from the pressure-correction migration. They are not:
`ns_fvm` solves its pressure-correction Poisson with **its own hand-rolled SOR
sweep** (`solvers/ns_fvm/solver/pressure/poisson.rs`), never reaching
`PressureCorrectionSolver` or any Krylov solver in this migration. Running one
case without a timeout shows SIMPLEC continuity stagnant at ~4.59e2 across ten
iterations and still running past 400s, which is that SOR failing to converge
on a micro-scale geometry. The file is also peer-dirty. Filed below.

**Clippy: still blocked**, third consecutive attempt, now surfacing on
`cfd-io` whose dependencies were built by a different rustc. Note the tests
passed minutes earlier under the same toolchain — the poisoned artifact set
differs by which crates a command pulls, which is exactly why this presents as
moving, unrelated breakage. `ATLAS-TOOLCHAIN-COHERENCE-001` is the blocker and
is now the single largest drag on verification.

## ATLAS-STACK-LETO-CHURN-017 — Upstream working-tree churn blocks consumer verification — todo

Third occurrence on 2026-07-31 of the same pattern, now costing real delivery
time, so it is recorded as its own item rather than re-diagnosed each session.

- **Symptom**: a consumer repo's `cargo check`/`nextest` fails inside
  `repos/leto` with errors that change between consecutive runs and reference
  code the consumer never touched.
- **Cause**: the stack `[patch]` overlay resolves first-party dependencies to
  local working trees, so a peer's *uncommitted, mid-edit* state in an upstream
  repo reaches every downstream consumer immediately. Observed today in
  `leto-ops/src/application/attention/` (cleared on retry) and
  `leto-ops/src/application/zip.rs` (still red; file modified seconds before
  each check).
- **Not a defect in either repo.** The overlay behaving as designed, plus
  normal peer activity. Same class as ATLAS-RITK-MODULE-FORWARD-000.
- **Cost**: any consumer increment depending on the churning crate cannot be
  verified, so it cannot be committed. ATLAS-COEUS-NLLS-004 parked on exactly
  this for roughly 25 minutes, clearing only when the peer committed `zip.rs`.
  The park was the correct call — the errors changed between consecutive runs,
  so retrying would have chased a moving target — but it is dead time that
  option (b) would remove.
- **Candidate directions, needing a decision rather than more diagnosis**:
  (a) accept it and treat upstream redness as a park-and-switch signal, which is
  current practice and what the contention response order already prescribes;
  (b) have the overlay resolve to each member's last *committed* revision rather
  than its working tree, making peer WIP invisible until committed — this is the
  real fix but changes the development overlay contract in
  architecture_scoping and needs an ADR;
  (c) narrow the overlay per session to the repos an agent actually edits.
  Option (b) is the recommendation: an uncommitted edit is not a published
  state, and the overlay currently makes it one for the whole stack.
- **Class**: `[arch]` if (b) is taken, since it revises the development overlay.
- **Fourth occurrence 2026-08-13 falsifies option (c).** Verifying one RITK
  branch, four consecutive attempts minutes apart each failed in a *different*
  upstream repo: `eunomia` (duplicate `PartialEq` — macro added before the
  manual impls were removed), `apollo-fft` (`BLUESTEIN_NATIVE_PHASE_TRIG` used
  in impls before the trait declared it), `eunomia` again (`FloatElement`
  gaining an `Accumulator` associated type, trait ahead of impls), and
  `consus-hdf5` (arity mismatch mid-signature-change). Every one is a normal
  half-finished edit; none is a defect.
  Option (c) assumed churn localizes to the repos an agent is near, so a
  narrowed overlay would dodge it. It does not: the churn was spread across
  four repos the RITK branch never touched, and narrowing enough to avoid them
  would exclude most of the stack, which defeats the overlay. That leaves (a)
  and (b), and (b) remains the recommendation.
  Retrying is also not free-but-harmless: because the failing crate *moves*,
  a green run is a peer-quiet window rather than evidence, so a consumer needs
  a retry loop that distinguishes upstream churn from its own redness before
  any result means anything.

## Wave -1 — peer contention, not RITK work (recorded 2026-07-30)

## ATLAS-RITK-MODULE-FORWARD-000 — RITK is red against in-flight Coeus WIP — resolved

**Resolved 2026-07-31 by the peer landing both sides.** Coeus committed the
contract (`repos/coeus` `5e64ee75 feat(coeus-nn)!: Make forward fallible`, now on
`origin/main`) and RITK adopted it (`repos/ritk` `d82efc23 feat(model)!: Adopt
Coeus's fallible module forward`, on `origin/main`). `ritk-transform` and
`ritk-io` build; 400/400 `ritk-mgh` + `ritk-io` tests pass at `ea11f4fb`. The
re-open trigger below fired exactly as recorded; waiting rather than converting
against uncommitted upstream was the correct call.

One item from the analysis survived the peer's sweep unfixed and is promoted to
ATLAS-RITK-DISPLACEMENT-FORWARD-016 below.

The original record is kept for the diagnostic pattern — a consumer red that is
really a provider's in-flight working tree reaching it through the stack
`[patch]` overlay.

**Not a RITK defect and not a claimable RITK item.** Recorded so the next agent
does not re-diagnose it, and does not do what this session started doing.

- **Symptom**: `cargo check -p ritk-transform` gives 10 `E0053`/`E0308` errors —
  every `Module::forward` impl returns `Var<f32, B>` where the trait now expects
  `Result<Var<f32, B>, ModuleError<B::Error>>`. `ritk-io`, `ritk-registration`,
  `ritk-cli`, and `ritk-snap` cannot build behind it.
- **Actual cause**: the fallible `Module::forward` and `ModuleError` are a live
  peer's **uncommitted** work in `repos/coeus`. `crates/coeus-nn/src/module/`
  (`trait_def.rs`, `error.rs`, `mod.rs`) has *no git history at all* — it exists
  only staged in the working tree, alongside ~143 other staged `coeus-nn` files
  and a staged `coeus-autograd` set, on branch
  `codex/coeus-error-function-parity`. RITK compiles against it because the
  stack `[patch]` overlay resolves first-party dependencies to local working
  trees, so a peer's in-flight refactor reaches every consumer immediately.
- **Therefore this is not "RITK failed to adopt a landed contract."** There is no
  landed contract. Converting RITK's 25 `Module` implementors now would commit
  RITK to a signature that exists in no commit on any branch, break RITK against
  Coeus `HEAD`, and collide with the peer when they land. This session began that
  conversion, then discarded it on discovering the above — the discard is the
  correct outcome, not lost work.
- **Peer freshness**: last `repos/coeus` commit `9ac74e13`, 2026-07-29 06:34
  (~1 day), with the change set staged and uncommitted since. Stale by the
  sweep's clock, but a 143-file in-flight refactor is not blind-takeover
  material. Re-check before assuming the peer is gone.
- **Re-open trigger**: the peer commits the `coeus-nn` module contract. At that
  point the RITK sweep becomes a real `[patch]` item — convert every implementor
  to the fallible signature and propagate at call sites with `?`, no `.expect()`
  at any site that has a caller to return to.
- **Known blocker for that future item**: `ModuleError` cannot carry a
  `coeus_ops::InterpolationError`. `DisplacementFieldTransform::forward`
  currently `.expect()`s one (`transform/displacement_field/transform.rs:124`),
  and `InterpolationError::{NonFiniteCoordinate, SizeOverflow}` have no
  `ModuleError` counterpart, so any mapping collapses distinct failure modes.
  The fix is an additive `Interpolation(#[from] InterpolationError)` variant on
  the (already `#[non_exhaustive]`) `ModuleError` in `coeus-nn` — upstream, in
  the same provider family, `[minor]`. Raise it with the peer rather than
  working around it downstream.
- **What is still verifiable meanwhile**: everything not depending on
  `coeus-nn`'s `Module`. Confirmed green this session: `ritk-mgh` (34/34),
  `ritk-nifti`, `ritk-nrrd`. The wave-0 format-crate work below therefore
  proceeds; only the `ritk-io` dispatch tail of ATLAS-DMRI-IO-001 waits.

## ATLAS-RITK-DISPLACEMENT-FORWARD-016 — `forward` panics on a real interpolation failure [patch] — implemented; validation blocked 2026-08-05

- **Evidence**: `ritk-transform/src/transform/displacement_field/transform.rs`
  now carries the fallible signature but keeps the panic inside it:

  ```rust
  Ok(self
      .transform_points(input)
      .expect("invariant: Module::forward receives valid field coordinates"))
  ```

  `transform_points` returns `Result<_, DisplacementTransformError>`, whose
  `Interpolation` variant carries a genuine runtime failure —
  `NonFiniteCoordinate` fires on a NaN sampling coordinate, which a diverging
  optimizer produces routinely. The sweep at `d82efc23` adopted the signature
  everywhere but wrapped this one body in `Ok(..)` instead of propagating, so the
  method gained a `Result` return that cannot express the one failure it has.
  Panic policy: library code does not panic on input-dependent paths, and the
  `expect` message asserts an invariant the type does not enforce.
- **Blocked on upstream**: `ModuleError` has no variant able to carry a
  `coeus_ops::InterpolationError`. `Backend { source: E }` requires
  `E = B::Error`, and `InterpolationError::{NonFiniteCoordinate, SizeOverflow}`
  have no counterpart among the rank/shape variants, so any downstream mapping
  collapses distinct failure modes.
- **Fix, in order**: (1) add `Interpolation(#[from] InterpolationError)` to
  `coeus_nn::ModuleError` — additive on an already `#[non_exhaustive]` enum, and
  in the same provider family since `coeus-nn` already depends on `coeus-ops`;
  (2) in RITK, map `DisplacementTransformError::PointShape` losslessly
  (`actual.len() != 2` → `InvalidRank`, else `ShapeMismatch` with
  `expected: [actual[0], D]`) and propagate `Interpolation` through the new
  variant.
- **Acceptance**: a NaN sampling coordinate returns a typed error naming the
  axis and point instead of panicking; existing displacement tests unchanged.
- **Delivered 2026-08-05**:  `coeus-nn::ModuleError` now carries typed `InterpolationError`;
  `DisplacementFieldTransform::forward` maps rank failures to `InvalidRank`,

  width failures to `ShapeMismatch`, and propagates interpolation failures
  instead of using `expect`. Ritk tests now cover NaN propagation through the
  public `Module::forward` path and verify wrong `[N, D]` input becomes a
  typed `ShapeMismatch`. Coeus Python maps interpolation failures to
  `PyValueError` with a focused mapping test. Rustfmt and diff checks
  pass for all four touched files. Package check/Clippy/nextest remain blocked
  by the peer-modified Coeus reduction refactor: `coeus-ops/src/reduction/norms.rs`
  references `ReductionOps`, but the current workspace compilation cannot
  resolve that trait; no peer-owned reduction files were changed here.
- **Class**: `[patch]` in RITK, `[minor]` in Coeus. Raise the upstream half with
  the `coeus-nn` owner rather than mapping around it.

## Wave 0 — acquisition-series ingest (blocks every later wave)

## ATLAS-DMRI-IO-001 — Rank-generic acquisition-series I/O [minor] — in-progress

**Claim 2026-08-11 — Codex current session:** own the next vertical
`ritk-nrrd` increment on branch `codex/ritk-nrrd-series` in the reclaimed
`worktrees/ritk-book-wf` lane. Claimed files are the NRRD reader/writer,
their co-located tests, and the package-local documentation needed for rank-4
acquisition-series round trips. Non-goals are MGH, DICOM, `ritk-io` dispatch,
and the peer-dirty ADR index in the primary RITK checkout.

**Re-audit closure 2026-08-11:** no NRRD implementation was added because
`origin/main` already carries the complete `d3d3d811` series implementation:
leading and trailing acquisition-axis decoding, rank-4 writing, shared-grid
validation, and value-semantic tests. RITK PR #119 merged at
`0a1a4dc98ec541ea2caa952dd2385c9ebfac583b` with its hosted Rust, Python,
workspace-alignment, and platform test jobs green. The local `--locked` gate
was blocked before compilation by the separately tracked provider drift
(`hermes-simd` 0.5.0 and `moirai-runtime` 0.4.0 locks versus current provider
heads); RITK PR #118 owns the overlay-free release-lock repair. The NRRD
sub-scope therefore closes as an evidence-backed stale-gap correction, while
MGH, DICOM, and `ritk-io` dispatch remain open sub-increments of this item.

**`ritk-nifti` increment delivered** at `ritk` `2a4b1f62`, pushed to
`codex/perf-ritk-mgh-stream-book` (PR #78, a peer's branch — the scopes are
disjoint, `ritk-nifti` vs the peer's `ritk-mgh` streaming slice, so the increment
rides that branch per the shared-branch model rather than opening a second PR).

Rank 3 and rank 4 both parse; the payload byte range spans every declared volume
instead of one; `read_nifti_series` / `read_nifti_series_from_bytes` /
`write_nifti_series` / `write_nifti2_series` are the series surface. The writer
selects rank from the volume count, so a one-volume series stays a rank-3 file
byte-identical to `write_nifti`, and it validates that every volume shares one
grid rather than emitting a file whose sform covers only part of its content.
`read_nifti` and `read_nifti_labels` now name the volume count and fail on a
rank-4 file instead of decoding volume 0 — the MGH defect class, caught before it
could ship in a second codec.

Verified: 49/49 `ritk-nifti` (0.564s), 370/370 `ritk-io` + `ritk-analyze`
downstream, clippy `--all-targets -D warnings` clean, `RUSTDOCFLAGS=-D warnings
cargo doc` clean.

Design decision recorded here rather than an ADR, being reversible and internal:
the series surface returns `Vec<Image<f32, B, 3>>` rather than a new
`ImageSeries` domain type. Volumes on one grid is what the format states, it
needs no cross-crate public API, and it does not prejudge the type
ATLAS-DMRI-SCHEME-003 actually needs — which carries the gradient scheme
alongside the volumes and is where the per-voxel-across-volumes access pattern
will be known. A contiguous layout stays open behind that type.

Remaining sub-increments: `ritk-mgh` series read (currently fails loudly per
ATLAS-DMRI-MGH-FRAMES-002, so this is an extension not a fix), `ritk-dicom`
multi-frame/series assembly, and the `ritk-io` dispatch tail. The NRRD
increment is closed by `d3d3d811` on the merged RITK head.

## ATLAS-DMRI-IO-001 original specification

- **Outcome**: `ritk-nifti`, `ritk-nrrd`, and `ritk-dicom` read and write a
  series carrying an acquisition axis, and `ritk-io` dispatches it.
- **Evidence of gap at item creation**: `ritk-nifti/src/header/validate.rs:74`
  bailed on `dim[0] != 3`; `ritk-nrrd` rejected acquisition-series headers;
  and `ritk-io/src/lib.rs:164` fixed `NativeImage = Image<f32, NativeBackend,
  3>`. The NRRD rejection was closed by `d3d3d811`; MGH, DICOM, and dispatch
  remain the live gaps.
- **Non-goals**: no change to `Image<T, B, D>`, which is already rank-generic;
  no arbitrary-rank generalization beyond one acquisition axis.
- **Design note**: a DWI series is 3 spatial axes plus 1 acquisition axis, not a
  4-D image. `Point<4>`/`Spacing<4>`/`Direction<4>` would assert direction
  cosines over the acquisition axis, which is meaningless. The type carries 3-D
  spatial metadata plus a per-volume scheme (ATLAS-DMRI-SCHEME-003), so the
  metadata stays 3-D and only storage gains the axis.
- **Acceptance**: round-trip a synthesized N-volume series through each codec
  recovering voxels and spatial metadata exactly; the existing 3-D entry points
  keep their signatures and tests.
- **Class**: `[minor]` — additive public surface.
- **Sequencing note (2026-07-31)**: no longer split — the `ritk-io` block
  cleared when ATLAS-RITK-MODULE-FORWARD-000 resolved. The `ritk-nifti` and
  `ritk-nrrd` increments are now closed on `origin/main`. The next increments
  are the `ritk-io` dispatch tail and the `ritk-mgh` series extension; MGH
  already fails loudly on a multi-frame file per ATLAS-DMRI-MGH-FRAMES-002, so
  its series read is an extension rather than a defect fix.

## Wave 1 — upstream provider capability (ADR 0036 decision 2 edges)

Each of these lands in the provider that owns the bounded context. A RITK-local
implementation of any of them is a boundary violation and fails ADR 0036
verification condition 2.

## ATLAS-COEUS-NLLS-004 original specification

- **Evidence of gap**: `coeus-optim` ships `SGD`, `Adam`, `AdamW`, `RMSProp`,
  and `Adagrad` only — all first-order stochastic, sized for network training.
- **Why it blocks**: per-voxel diffusion fitting is millions of independent
  small dense residual problems. A damped Gauss-Newton step with an analytic
  Jacobian converges in single-digit iterations; a first-order stochastic
  optimizer is the wrong instrument by orders of magnitude. Log-linear DTI is
  unaffected — it routes through `leto-ops` (`pinv`, `qr_decompose`,
  `cholesky_solve`), which already exist.
- **Blocks**: DKI, NODDI, IVIM, free-water, and every other nonlinear model.
- **Acceptance**: batched over a leading problem axis; verified against an
  analytical oracle with a known minimum and against a published test problem
  set; convergence criterion is a derived relative-residual bound, never a fixed
  iteration count.
- **Class**: `[minor]`, repository `repos/coeus`.

## ATLAS-APOLLO-REALSH-005 original specification

- **Evidence of gap**: `apollo-sht` owns complex SH on Gauss-Legendre product
  grids. `infrastructure/kernel/spherical_harmonic.rs:234` exposes
  `spherical_harmonic(degree, order, theta, phi) -> Complex64`, so pointwise
  evaluation at an arbitrary direction already exists; the real, even-order,
  antipodally symmetric basis, the design matrix over a scattered direction set,
  and Laplace-Beltrami regularization do not.
- **Why Apollo and not RITK**: Apollo owns the transform bounded context. A
  RITK-local associated-Legendre or normalization path forks the SH dimension
  and is the exact failure mode ADR 0036 decision 2 exists to prevent.
- **Convention pinning**: the basis has several published orderings and
  normalizations (Descoteaux and Tournier differ). The implementation declares
  one, and a reference-case test asserts it against published coefficients.
- **Blocks**: every ODF/FOD model in `ritk-diffusion`.
- **Class**: `[minor]`, repository `repos/apollo`.

## Wave 2 — preprocessing (RITK, existing crate owners)

## ATLAS-DMRI-DENOISE-008 — MP-PCA denoising and Gibbs unringing [minor] — todo

- **Outcome**: `ritk-filter` gains Marchenko-Pastur PCA denoising and subvoxel
  Gibbs ringing removal — the `dwidenoise` and `mrdegibbs` roles, and the first
  two stages of every current dMRI pipeline.
- **Evidence of gap**: `ritk-filter` has bilateral, patch-based, median, rank,
  and anisotropic-diffusion denoising; none is the MP-PCA estimator, which
  derives its threshold from random-matrix theory rather than a tuned parameter.
  `ritk-statistics/src/noise_estimation.rs` is MAD over additive Gaussian noise —
  correct as written, but not the Rician/noncentral-chi model magnitude DWI
  actually follows.
- **Related**: Rician bias correction is a third item in the same crate, split
  out if MP-PCA outgrows its acceptance criteria.
- **Acceptance**: the MP-PCA threshold is derived from the Marchenko-Pastur
  distribution and the patch geometry, never an empirical constant; verified on
  a synthesized field with a known noise level.
- **Class**: `[minor]`.

## ATLAS-DMRI-CORRECT-009 — Motion, eddy-current, and susceptibility correction [minor] — review

**PR mapping (2026-08-01).** PR #82 grew to four commits and ~1,700 lines, past
a reviewable unit, and also carried four unrelated JPEG 2000 commits inherited
from its base. Split into four PRs cut fresh from `origin/main`, each verified
standalone; #82 closed. References to "PR #82" below predate the split.

| PR | Scope | Base | Standalone verification |
| --- | --- | --- | --- |
| #84 | `ritk-diffusion-scheme` per-volume reorientation | `main` | 23/23 |
| #85 | `ritk-spatial` rotation extraction | `main` | 54/54 + doctest |
| #86 | `ritk-registration` series alignment | **#85** | 352/352 |
| #87 | `ritk-registration` EPI distortion model | `main` | 367/367 |

#86 targets #85 because it consumes `rotation_from_linear`; GitHub retargets it
to `main` on merge. The other three are independent and may merge in any order.

The split was done in a bounded worktree lane rather than the main tree, which
was dirty with peer edits — branch switches there had been aborting. The lane is
deregistered; its directory at `worktrees/ritk-pr-split` could not be deleted
(held by another process) and needs sweeping once that releases.

**Scheme-side reorientation delivered**: `ritk` `660783da` on
`feat/per-volume-gradient-reorientation`, PR #82.
`GradientScheme::reorient_per_volume` applies one rotation per volume in
acquisition order, with an exact count match and whole-list validation before
any rotation is applied. 22/22 `ritk-diffusion-scheme` tests, clippy and doc
gates clean.

A peer had already landed the single-rotation `GradientScheme::reorient` and the
FSL codecs in `ritk-diffusion-scheme`. That method applies one rotation to the
whole scheme — correct for a fixed frame change, unusable for correction, where
each volume is registered independently. Nothing in the workspace called
`reorient` at all before this.

**Remaining, in dependency order:**

1. ~~**Rotation extraction from an affine.**~~ **Delivered**: `ritk` `216f21f7`,
   same branch and PR #82. `ritk_spatial::rotation::rotation_from_linear`
   returns the orthogonal polar factor.

   Placement resolved to `ritk-spatial`, and the open question dissolved on
   inspection: `ritk-spatial` already depends on `leto`, so there was no new
   dependency to weigh. The operation is geometry rather than diffusion, and its
   consumers (gradient reorientation, tensor and ODF reorientation, resampled
   grid orientation) all already depend on that crate.

   **Numerical finding worth keeping.** The eigen route alone
   (`S = (AᵀA)^{1/2}` via leto's `symmetric_eigen`) is least accurate at the
   input that matters most: when `A` is already a rotation, `AᵀA = I` has a
   triple eigenvalue and the analytic cubic derives eigenvectors from cross
   products of a near-zero matrix. Measured drift was ~3.8e-9 — *above* the
   1e-9 orthonormality bar `reorient_per_volume` enforces, so the undistorted
   case would have been rejected downstream. One Newton step of Higham's polar
   iteration (`X ← ½(X + X⁻ᵀ)`) is a fixed point at an exactly orthogonal
   matrix and converges quadratically, restoring machine precision. Any future
   consumer of `symmetric_eigen` on a near-degenerate matrix faces the same
   thing.

   Reflections are rejected rather than repaired to the nearest proper rotation:
   the Kabsch sign flip suits fitting to noisy point correspondences, but a
   handedness reversal between two images of one subject means the transform is
   wrong, and repairing it would hide the defect.
2. ~~**The series correction driver**~~ **Delivered**: `ritk` `4633b5e3`, same
   branch and PR #82. `ritk_registration::series::register_series` fits each
   volume to a reference and reports the transform plus the proper rotation it
   carries. The `ritk-io` gate cleared — a peer landed
   `read_image_series_native`.

   **Layering decision.** The module carries no diffusion vocabulary. Motion
   correction is the same operation whether volumes vary by gradient,
   timepoint, or inversion time, and a diffusion consumer depends on
   registration rather than the reverse. `SeriesAlignment::rotations()` returns
   exactly the shape `GradientScheme::reorient_per_volume` consumes, so the two
   compose without `ritk-registration` ever depending on
   `ritk-diffusion-scheme`.

   **Two contract choices worth keeping.** The reference is assigned the
   identity rather than registered to itself — self-registration returns a
   near-identity fit perturbed by optimizer noise, injecting a spurious rotation
   into the one volume known to need none. Its `quality` is `None` rather than a
   zeroed metrics struct, which would claim a mutual information and correlation
   of zero for a registration that never ran.

   Rigid is the default model: it cannot deform anatomy, so a caller who has not
   considered eddy currents does not silently receive a shape-changing fit.
   `SeriesTransformModel::Affine` admits the extra freedom eddy-current
   distortion needs.

   **Not yet wired end to end.** `register_series` reports what moved; applying
   the transforms to resample the volumes is the caller's step and no composed
   `correct_diffusion_series` entry point exists. That composition belongs with
   the diffusion consumer and is the natural next increment once
   `ritk-diffusion` settles.
3. **Susceptibility distortion** — the `topup` role. **Model delivered**:
   `ritk` `3042601f`, same branch and PR #82.
   `ritk_registration::epi::{distort, unwarp}` with `PhaseEncoding`
   (axis + polarity). The forward model is what field estimation later fits
   against; `unwarp` solves the observed-to-true map per line rather than
   assuming small displacements, so the round trip is exact.

   Convention pinned in the module docs (per numerical_discipline): for field
   `f` in voxels and polarity sign `s`,
   `observed(y) = true(y + s·f(y)) · |1 + s·∂f/∂y|`. Toolchains differ here, so
   it is stated rather than assumed.

   A folding field is rejected, not clamped: where the Jacobian reaches zero,
   distinct true positions map to one observed position and their signal is
   summed, which no unwarping separates.

   **Two test-oracle corrections worth keeping**, both cases where the first
   assertion was wrong rather than the code:
   - Signal conservation is an identity over the *mapped* range, not the grid.
     A ramp field with non-zero boundary value stretches the domain and
     legitimately raises the grid total — measured at exactly 10% for slope
     0.1, which is the Jacobian working. The test now uses a
     boundary-vanishing field, where the map is onto the grid and conservation
     is exact.
   - The warp/unwarp round trip cannot be exact on a step edge: two linear
     interpolations do not reconstruct a discontinuity. That is a property of
     resampling, not of the model. The test uses a linear image, which linear
     interpolation reproduces exactly, isolating the geometry and Jacobian
     bookkeeping.

   **Remaining**: field *estimation* from a reversed-polarity pair. That is a
   regularized nonlinear fit over a field parameterization (spline coefficients
   or per-voxel with a smoothness penalty) — thousands of parameters, so the
   dense `coeus-optim` Levenberg-Marquardt from ATLAS-COEUS-NLLS-004 is the
   wrong instrument and a large-scale or sparse-Jacobian path is needed first.
   Size and owner of that solver is an open question, not a scheduled item.

**Acceptance oracle is still unbuildable here.** ADR 0036 verification condition
7 needs a synthesized anisotropic tensor field fitted after correction, which
needs `ritk-diffusion`'s tensor fit — peer-owned and in flight. The tests in
PR #82 verify the reorientation contract directly (per-volume indexing, the
`R`/`Rᵀ` round trip that catches a transposed application, rejection of
non-orthonormal and improper matrices); the end-to-end eigenvector oracle
attaches once the tensor fit lands.

## ATLAS-DMRI-CORRECT-009 original specification

- **Outcome**: a series-level correction driver in `ritk-registration` — the
  `eddy` and `topup` roles.
- **Present**: rigid, affine, B-Spline FFD, Demons, SyN, and LDDMM registration
  all exist; `ritk-filter/src/bias/n4` covers B1 bias. The registration machinery
  is not the gap.
- **Gap**: (a) no driver that registers volume-to-volume across an acquisition
  axis, which ATLAS-DMRI-IO-001 gates; (b) **no gradient reorientation** — the
  rotational part of each correction must be applied to that volume gradient
  direction. A correction that omits this yields a silently wrong tensor field
  and is the most common defect class in this domain; (c) no
  susceptibility-distortion path (reversed-phase-encode fieldmap estimation).
- **Acceptance**: ADR 0036 verification condition 7 — a synthesized anisotropic
  tensor field rotated by a known transform recovers its principal eigenvector
  after correction, and the same test fails when reorientation is skipped.
- **Class**: `[minor]`.

## Wave 3 — the three ADR 0036 crates

## Wave 4 — surfaces, containers, delivery

## ATLAS-RITK-FSSURF-013 — FreeSurfer surface formats and label table [minor] — todo

- **Outcome**: RITK reads the FreeSurfer surface family — surface binaries
  (`lh.white`, `pial`, `inflated`), `curv`, `label`, `annot` — plus the color
  LUT, and GIFTI as the interchange equivalent.
- **Evidence of gap**: `ritk-mgh` covers FreeSurfer *volumes* only; no surface,
  annotation, or LUT reader exists in the workspace.
- **Why it is a prerequisite, not an optional format**: surface parcellations are
  how connectome nodes are conventionally defined, so ATLAS-RITK-CONNECTOME-012
  depends on it.
- **Deletion ledger** (promotion-gate condition 4, satisfied): the FreeSurfer
  `aseg` and Desikan `aparc` label table is hand-rolled in a downstream consumer
  at `repos/leoneuro-rs/crates/leoneuro-gui/src/freesurfer.rs` (137 lines). The
  RITK owner first increment deletes it and repoints that consumer.
- **Open**: CIFTI is deferred until a consumer needs HCP-convention data.
- **Class**: `[minor]`.

## ATLAS-DMRI-TRACTOGRAM-FMT-014 — Tractogram container ownership [arch] — todo

- **Decision needed**: MRtrix `.tck`, TrackVis `.trk`, and TRX are published
  byte-level interchange specifications, which is the RITK format-crate pattern;
  ADR 0036 decision 2 routes derived-array persistence to Consus. The two rules
  point at different owners for the same artifact.
- **Recommended resolution** (per bias-to-completion, proceed on this unless
  overridden): an interchange format that other toolchains read is a RITK format
  crate; a derived-array store for Atlas-internal persistence is Consus. A
  streamline set written for MRtrix or TrackVis to read is interchange.
- **Also open**: MRtrix `.mif` / `.mif.gz`, which is both an image container and
  an embedded gradient-scheme carrier, so it spans 001 and 003.
- **Deliverable**: ADR 0036 revision recording the resolution, or a new ADR if it
  generalizes beyond this artifact.
- **Class**: `[arch]`, no public-surface break — `[patch]` on the SemVer axis.

## Out of scope for this program

- **Surface reconstruction** (the `recon-all` role — white and pial surface
  generation from T1). Ingest of existing FreeSurfer surfaces is item 013;
  generating them is a distinct research-scale capability with no current
  consumer, and is demand-gated.
- **MR acquisition simulation** — closed by ADR 0036 decision 4; opens as an
  integrator when a program needs to simulate acquisition.
- **Study and cohort structure** — ADR 0036 decision 3 assigns it to Tyche;
  RITK supplies per-subject measures as study responses. No `ritk-study` crate.

## ATLAS-CFDRS-LINT-FLOOR-001 — Adopt canonical Atlas lint floor in CFDrs workspace [patch] — in-progress

- Owner: current session; scope: `repos/CFDrs/Cargo.toml` top-level
  `[workspace.lints]` block and per-site `#[expect]` ratchet insertions
  across `crates/cfd-*/src/**` and `xtask/src/**`.  Claimed 2026-08-06.
- Outcome: CFDrs `Cargo.toml` carries the canonical Atlas `[workspace.lints]`
  floor matching `repos/apollo/Cargo.toml` L88-L107 (template SSOT):
  `[workspace.lints.rust] missing_docs = "warn"` (warn floor; `#![deny(missing_docs)]`
  is the per-crate strict escalation choice, not set workspace-wide so existing
  crates without missing-docs discipline stay warning-only until per-crate
  promotion). `[workspace.lints.clippy]` adopts apollo's `all = warn, prio -1` +
  `pedantic = warn, prio -1` and the same `allow` set (`module_name_repetitions`,
  `must_use_candidate`, `similar_names`, `too_many_lines`,
  `default_constructed_unit_structs`, `doc_lazy_continuation`,
  `needless_range_loop`, `too_many_arguments`, `manual_is_multiple_of`,
  `manual_div_ceil`, `manual_slice_size_calculation`, `len_zero`,
  `cast_possible_truncation`, `cast_precision_loss`, `cast_sign_loss`,
  `cast_possible_wrap`, `items_after_statements`, `range_minus_one`,
  `default_trait_access`, `useless_conversion`). Adds the Atlas-canonical library
  hygiene `deny` tier (`unwrap_used`, `print_stderr`, `print_stdout`,
  `dbg_macro`) so consumer-tree library and CLI crates enforce the same floor
  kwavers/helios/apollo already carry — `#[expect]` permitting pre-existing
  sites to remain on a non-increasing ratchet baseline, not silent `allow`.
- Scope: idempotent bulk `#[expect(lint, reason="ratchet cfd-<crate>-<count>")]`
  insertion per violation emitted by `cargo clippy --all-targets
  --workspace --json -- -D warnings -W clippy::pedantic
  -W clippy::unwrap_used -W clippy::print_stderr -W clippy::print_stdout
  -W clippy::dbg_macro`. **Mechanical transform only** per `git_discipline`:
  no logic edits, no refactor, no removed `println!` from `xtask` at large —
  per-site `#[expect]` carries the ratchet signal for future root-cause work.
- Non-goals: no public-API rewrites, no `print!` removal from `xtask` source
  (xtask is a build tool, not a library; per-site `#[expect]` preserves the
  ratchet signal per `engineering_gates` brownfield rule), no logic fixes for
  surfaced `unwrap_used` (the ratchet baseline only decreases — a future
  root-cause slice removes the offending `unwrap` and its `#[expect]` together).
- Disjoint from peer's `ATLAS-CFDRS-ATHENA-MIGRATION-001` chain.rs scope:
  peer's last chain.rs touch was 2026-07-30 (`63e49604`); 7+ days stale,
  reclaimable takeover material. Converge-friendly by construction — `#[expect]`
  is semantics-preserving against any in-flight peer chain.rs work; if peer
  pushes new chain.rs commits during this slice, fall through `concurrent_agents`
  Detect-and-reconcile (compose around peer's diff).
- Lane: reclaimed per-repo 2-tree cap slot by removing the post-merge
  `codex/cfdrs-audit-refresh` worktree lane (peer's PR #327 fully merged at
  `50fa243b`, lane = `D:/atlas/worktrees/CFDrs-audit-refresh` exactly at peer's
  merged tip, tree clean) and adding `feat/cfdrs-lint-floor` lane off
  `origin/main 50fa243b`.
- Acceptance: `cargo clippy --all-targets --workspace -- -D warnings
  -W clippy::pedantic -W clippy::unwrap_used -W clippy::print_stderr
  -W clippy::print_stdout -W clippy::dbg_macro` rc=0; `cargo nextest run
  --workspace` rc=0 (or reduced focused subset if workspace test suite
  budget blocked per `engineering_gates` runtime budgets — root-cause
  any hang, never bypass); `cargo test --doc --workspace` rc=0; `cargo fmt
  --all --check` rc=0.
- Re-open trigger: a new lint violation reaches `repos/CFDrs/origin/main`
  past the floor without an accompanying `#[expect]` carrying its ratchet
  rationale; or the floor is removed/relaxed in `Cargo.toml`.
- Residual recorded, NOT closed in this slice: per-repo `backlog.md` and
  `gap_audit.md` entries for CFDrs lint-floor closure; CFDrs-level
  per-crate `#![deny(missing_docs)]` promotion is deferred to a later
  per-crate slice (each crate's surface decides its own missing-docs tier).
- Current CFDrs increment: commit `cd9580fc` on pushed branch
  `feat/cfdrs-lint-floor` wires every workspace package and `xtask` to the
  floor, removes the cfd-core plugin resolver unwrap, and records the local
  PM state. Evidence: focused `xtask` and cfd-core library Clippy pass;
  cfd-core Nextest 246/246; cfd-core doctests 3/3; explicit migration audit
  reports zero legacy dependencies, zero legacy source tokens, and a clean
  allowlist. Full workspace acceptance remains open on the recorded
  cfd-math, cfd-schematics, cfd-core test/bench, and format debt.
- Follow-up CFDrs commit `e3e88a60` is pushed on the same branch: multigrid
  coarsening now uses deterministic NaN-safe ordering, with a value-semantic
  regression test. cfd-math Nextest passes 198/198; focused cfd-math library
  Clippy residue decreases from 51 to 48 diagnostics.
- Follow-up CFDrs commit `f31176b1` is pushed: multigrid hierarchy and
  interpolation state use invariant-checked expectations, while JFNK and
  spectral kernels centralize C-contiguous storage assumptions. cfd-math
  Nextest remains 198/198; focused library Clippy residue is 22 diagnostics.
- Follow-up CFDrs commit `9e52454a` is pushed: performance-monitor mutex and
  calibration output now use invariant diagnostics and tracing, and DG progress
  output is structured tracing. cfd-math library Clippy and Nextest pass;
  workspace closure still has cfd-schematics, cfd-core test/bench, and format
  debt.
- Follow-up CFDrs commit `c83affee` is pushed: the exported
  `cfd-schematics::topology::model` contract now documents its types, fields,
  variants, aliases, and lookup methods. cfd-schematics library Nextest passes
  164/164 and doctests 16/16; package Clippy residue decreases 712 to 611.
- Follow-up CFDrs commits `ddc04a32` and `8584dd26` are pushed: configuration
  constants, public config manifests, and the route-spec contract now carry
  API documentation. cfd-schematics library Nextest remains 164/164 and
  doctests 16/16; package Clippy residue decreases 611 to 534.
- Follow-up CFDrs commit `322787ae` is pushed: the public node and channel
  geometry-builder setters now carry API documentation. cfd-schematics library
  Nextest remains 164/164 and doctests 16/16; package Clippy residue decreases
  534 to 524.
- Follow-up CFDrs commit `eae43768` is pushed: geometry-generator metadata,
  entry points, and builder methods now carry API documentation. cfd-schematics
  library Nextest remains 164/164 and doctests 16/16; package Clippy residue
  decreases 524 to 508.
- Follow-up CFDrs commit `c0d53bd5` is pushed: series and parallel geometry
  generators now carry API documentation. cfd-schematics library Nextest
  remains 164/164 and doctests 16/16; this slice reduces its package Clippy
  residual from 508 to 506. The working tree reports 492 with peer-owned
  `analysis_impl.rs` documentation changes also present and uncommitted.
- Follow-up CFDrs commit `f27f86dd` is pushed: selective-tree path, topology,
  request, and generator contracts now carry API documentation. cfd-schematics
  library Nextest remains 164/164 and doctests 16/16; this slice reduces the
  package Clippy residual from 506 to 468. The working tree reports 454 with
  the peer-owned `analysis_impl.rs` documentation changes still uncommitted.
- Follow-up CFDrs commit `468cc617` is pushed: the `NetworkBlueprint` analysis
  impl (`crates/cfd-schematics/src/domain/model/blueprint/analysis_impl.rs`)
  now carries inline Rustdoc for its 14 undocumented pub methods (node/pipe
  counters, length aggregates, Venturi lookup, overlap analysis/resolution,
  validate, describe). cfd-schematics library Nextest remains 164/164 and
  doctests 16/16. File-disjoint from peer commits on the same branch per
  `concurrent_agents` disjoint-scope rule; peer's prior bullet had already
  flagged this `analysis_impl.rs` work as the uncommitted peer residual, and
  the slice now closes that residual. cfd-schematics distinct missing_docs
  sites in `analysis_impl.rs` fall from 14 to 0; crate-wide distinct
  sites fall from 468 to 454.
- Follow-up CFDrs commit `357debf3` is pushed: the `NetworkBlueprint`
  metadata impl (`crates/cfd-schematics/src/domain/model/blueprint/metadata_impl.rs`)
  now carries inline Rustdoc for its 19 undocumented pub methods/associated
  functions covering the deprecated default constructor, the
  explicit-position constructor, render-hint and metadata builders/accessors,
  topology and lineage attachments, JSON (de)serialization, and
  node/channel addition methods. cfd-schematics library Nextest remains
  164/164 and doctests 16/16. File-disjoint sibling of the just-merged
  analysis_impl.rs closure in the same `domain/model/blueprint/` subtree,
  owned by this session; no peer commits touched this file.
  cfd-schematics distinct missing_docs sites in `metadata_impl.rs` fall
  from 19 to 0; crate-wide distinct sites fall from 454 to 435.

## ATLAS-CFDRS-CI-WORKSPACE-RUST-001 — Add Rust workspace CI gate to CFDrs [patch] — in-progress

- Owner: current session (claimed 2026-08-10). Pairs with
  ATLAS-CFDRS-LINT-FLOOR-001 to make the floor mechanically enforced.
- Outcome: CFDrs `.github/workflows/ci.yml` carries a `rust-workspace` job
  that runs `cargo check --workspace --all-targets`, `cargo nextest run
  --workspace` (or `cargo test --workspace --no-fail-fast` fallback gated
  on `nextest` install via `taiki-e/install-action`), `cargo clippy
  --all-targets -- -D warnings`, `cargo fmt --all --check`, `cargo test
  --doc --workspace`. Mirrors `.github/workflows/ci.yml` patterns in
  `repos/apollo`, `repos/hephaestus`, `repos/helios`, and `repos/kwavers`.
- Scope: `.github/workflows/ci.yml` only; disjoint from peer's helios/ritk
  release-workflow consolidation `ci/migrate-release-workflow-to-shared-caller`.
- Acceptance: the new job runs in CI on the next PR; `cargo check --workspace
  --all-targets` and `cargo clippy` fail on a regression injected locally.
- Re-open trigger: the rust-workspace job is removed or its gate commands
  are weakened below the canonical Atlas floor.
- Dependency: ATLAS-CFDRS-LINT-FLOOR-001 must land first (or in the same
  PR) so `cargo clippy -- -D warnings` does not fail at the ~160 pre-existing
  baseline. Sequence behind it.

## ATLAS-MOIRAI-DEFAULT-REFRESH-2026-08-18 — reconcile fetched provider default

- Status: complete. Moirai hosted Rust Workspace run `32175287434` and Python
  Bindings run `32175287255` both completed successfully at provider default
  `6a98f3f7bd834f46c8120c291362eb260f6cf875`.
- The Atlas `repos/moirai` gitlink advances to that exact fetched `origin/main`
  commit. The primary Moirai checkout remains peer-dirty and is not modified.
- This is a pointer/PM reconciliation only; it does not claim that the live
  Moirai SeqCst audit or peer-owned source work is complete.

## ATLAS-FINAL-PROVIDER-AUDIT-2026-08-18 — exact residuals

- The pushed Atlas root passes the committed lock-form audit: 27 locks resolve
  standalone, with only the sanctioned Melinoe in-tree fixture exempted.
- The exact-head structural audit for the requested provider set has two
  residuals: Consus gitlink `34b2507` versus provider `origin/main` `ef439b2`
  (the merged shuffle correction's unverified default), and Mnemosyne gitlink
  `1c38a1a` versus provider `origin/main` `638ddab`. Consus default CI,
  Documentation, and Pages runs `32184845212`, `32184845179`, and
  `32184843457`, and Mnemosyne CI `32183974171`, are queued. Neither pointer
  is silently advanced.
- The clean-checkout audit remains red only on peer-owned moving or dirty
  checkouts, including Themis, Tyche, Proteus, Consus, Helios, Harmonia,
  Eunomia, RITK, Melinoe, Leto, Hephaestus, Coeus, Apollo, Hermes, and Iris.
  The lane audit records six live peer violations across CFDrs, Coeus, Consus,
  Kwavers, and RITK; one clean, merged Kwavers orphan lane, one clean, merged
  CFDrs lane, and two clean, merged RITK lanes were removed after verifying
  empty status, while peer dirty checkouts and live lanes were preserved.

## ATLAS-CONFORMANCE-LINT-TABLE-2026-08-18 — correct nested workspace-lint detection

- Status: complete in root commit `eaa32fd`.
- The conformance detector now recognizes valid nested
  `[workspace.lints.rust]` and `[workspace.lints.clippy]` tables; it no longer
  reports Aequitas or Apollo as missing workspace lint inheritance. The
  committed baseline was regenerated for this detector change from the
  recorded provider objects; only Coeus and RITK retain this class.
- The regression test covers a nested table and the conformance unit suite
  passes 12/12. Provider source, locks, and peer checkouts were not changed.

## ATLAS-KWAVERS-DEFAULT-RECHECK-2026-08-18 — moving default remains open

- Kwavers PR #400's orphan-module cleanup is merged at
  `23f53284d789ba9b15788b51b3e83e40d301caf3`; its formatting prerequisite PR
  #403 is merged at `15c12732f5841125a5d65b6c3da2adc0f7c0793a`. The clean
  `kwavers-orphan-096` lane had no uncommitted state and was removed; its
  branch ref remains recoverable.
- The provider default now includes the Atlas wheel-parity closure at
  `e6fb53b90798f498e87d2c1fed275944a5cbe4b6`. Hosted run `32237250724`
  passes the complete wheel matrix and installed-wheel k-Wave comparator at
  its preceding source head `56bded6fa`; the Atlas pointer advances to the
  documented current default for exact-head coherence.
- PR #402 is not the current default proof: it is open at
  `d8886b032c50c7ebbcc2f12ebaceacabe95e19f1` with `mergeStateStatus=CONFLICTING`.
  Its earlier `69478221f` evidence is stale. Re-open the consumer integration
  and pointer advance only after the peer-owned branch is reconciled or the
  provider default independently satisfies the hosted matrix.

## ATLAS-MNEMOSYNE-DEFAULT-RECHECK-2026-08-18 — moving default remains open

- Mnemosyne `origin/main` advanced to
  `43cdf04769d4ab8701dea657b282c4a189175d48`. The Atlas gitlink remains at
  the previously verified `64f0d2ebe58e14705ca2345cad2c705f99a6b611`.
- Default CI run `32206977029` has Rust verification, Rust 1.95, Loom,
  aarch64, and ThreadSanitizer successful; Miri remains in progress. Do not
  advance the pointer until that exact default-head run completes; the
  peer-dirty primary checkout remains untouched.

## ATLAS-MNEMOSYNE-DEFAULT-RECHECK-2026-08-19 — moving default remains open

- Mnemosyne `origin/main` advanced again to `baf4f235d2b04db2d6a9203dbc38b3f39aa12fa2`
  with `fix(mnemosyne-core)!: Make the pool stack's node link atomic`.
- The exact default-head CI run `32281506800` and MSRV run `32280939845` are
  queued; the preceding run at `baf4f23` was cancelled before verification.
- Atlas remains at the last verified Mnemosyne pointer `d00f139e`. Advance only
  after the exact default-head Rust and MSRV evidence completes; preserve the
  peer-owned provider checkout and its lockfile dirt.

## ATLAS-LIVE-HEAD-SWEEP-2026-08-18-2055 — exact-head residual refresh

- Consus `origin/main` advanced to
  `ef439b2f5668b90fdbbed7097c3c6a44143c6ce4`, which contains the shuffle
  correction. Its CI, Documentation, and Pages runs `32184845212`,
  `32184845179`, and `32184843457` are queued. Atlas remains at the previously
  verified `34b25075` until those exact default-head gates complete; PR #46 is
  still open and conflicting against its former base.
- Mnemosyne remains a moving default residual at `638ddab` with CI
  `32183974171` queued; Atlas remains at `1c38a1a`.
- RITK PR #173 and CI-skip PR #172 are merged into provider default
  `0f0b5c5689a58a35fde30f07c62b7d94f5495004`, and Atlas now records that
  pointer. Its CI and Python CI runs `32184697093` and `32184697087` are
  queued, so hosted verification is pending even though exact-head equality
  holds.
- The clean merged CFDrs `cfd2d-fix` lane and clean merged RITK PR #173 and
  PR #168 lanes were removed after empty status checks; their branch refs
  remain available. Dirty runtime/lock lanes and open or peer-owned lanes
  remain.

## ATLAS-INTEGRATOR-HEAD-2026-08-19 - exact integrator audit checkpoint

- Root commit `bd79803` extends the exact-head and clean-checkout audit scope
  to CFDrs, Kwavers, and Helios. The live `atlas-22` exact-head audit passes:
  all 22 provider gitlinks and all three integrator gitlinks match fetched
  default heads, and the requested-provider coherence scope is clean.
- CFDrs is recorded at merged default `931ee3a0130a5238461a1ee9547e12aef11e90bf`.
  Hosted run `32221669165` passes the Rust workspace gate and the book-figure
  gate. A standalone `cargo package --locked` remains blocked before
  packaging by the Atlas development-overlay lock mismatch; this is not
  treated as package evidence.
- Root fast scripts pass: 234 tests, 17 deselected, and 74 subtests. The
  stack overlay and 27 committed standalone lock forms also pass. The clean
  checkout audit and lane audit still report peer-owned checkout dirt and
  excess lanes; those trees remain untouched. Apollo's benchmark regression,
  Kwavers' missing local Python extension, and Helios H-103 remain open.

## ATLAS-CFDRS-HOSTED-2026-08-19 — exact default-head evidence

- CFDrs default `931ee3a0130a5238461a1ee9547e12aef11e90bf` passes hosted run
  `32222487306`: Rust workspace format, check, Clippy, tests,
  numerical-fidelity tests, doctests, and native fontconfig setup all pass;
  the figure SSOT job also passes.
- Provider PM synchronization is pushed as `f601d827` on PR #357. Its hosted
  checks are in progress; no result is claimed from that new docs-only head.
  Pages deployment, PyPI release dry-run, and standalone locked package
  evidence remain separate open gates.

## ATLAS-CFDRS-JFNK-OPEN-033-2026-08-19 — provider source closure complete

- CFDrs PR #358 carries provider commit `0a5076c6034d735dd23d63a91453fea7d63702d0`:
  `cfd-1d` now reaches the retained Newton/JFNK fallback from the live solver
  graph, derives the recovery budget from `SolverConfig.max_iterations`, and
  propagates callback failures through checked JFNK evaluation.
- Hosted run `32225861309` reached the compiler and exposed the missing
  `FnMut` bound for the workspace-reusing residual closure. Provider commits
  `bc18b095` and `5e13018a` changed the checked JFNK seam to accept mutable
  callbacks, corrected the constructor field order, and retained the value
  regression. Replacement run `32229463775` passes the Rust workspace and
  figure SSOT gates. PR #358 merged at provider default `834340f7`; Atlas now
  tracks that exact merged head.

## ATLAS-HELIOS-H103-2026-08-19 — recheck stale documentation residual

- Helios merged checkout `f8ebe42f2a9c72f9da177cf5f96e15029b8a6d54` now passes
  `mdbook test docs/book` across every listed chapter and example. The prior
  H-103 failure description is stale at this head; no provider source change
  is required from the Atlas audit.
- The Helios primary checkout remains detached with peer-owned
  `crates/helios-python/Cargo.toml` dirt, and its sole lane is occupied by a
  peer Apollo-lock task. Preserve both trees until the owning work completes.
## ATLAS-KWAVERS-DELIVERY-2026-08-19 — wheel and book gate closure

- Kwavers commit `261fe8cf8` adds the existing
  `crates/kwavers-python/tests` suite to the shared Python-wheel workflow and
  enables `mdbook test` in the shared Pages workflow. The commit is pushed to
  `origin/main`; Atlas tracks it at root commit `3ed3813`.
- The exact-head provider audit, stack overlay, 27 standalone lock forms,
  board lint, and 234 fast root script tests pass after the pointer advance.
- The peer-owned untracked `docs/ADR/111-retire-kzk-solver-plugin-surface.md`
  remains untouched; the comparative K-Wave validation gap remains separate.

## ATLAS-KWAVERS-METADATA-2026-08-19 — Python surface consistency

- Kwavers commit `e62d529e6` removes the unused workspace `pyo3` ABI3
  declaration, keeps the binding and release floor consistently at Python 3.8,
  repairs the Python documentation URL, and makes Pages rebuild on source and
  manifest changes. Atlas tracks it at root commit `a2f46dc`.
- `cargo fmt --all -- --check`, `git diff --check`, and locked metadata
  inspection pass. The provider `cargo check -p kwavers-python --locked` is
  blocked before compilation by the shared Atlas overlay requesting lockfile
  updates for unused local patches; no source failure is inferred.

## ATLAS-CFDRS-JFNK-RERUN-2026-08-19 — hosted infrastructure retry

- Replacement run `32226998372` first failed in the runner's native-fontconfig
  setup after three bounded `apt-get` attempts against unreachable Ubuntu
  mirrors; no Rust or JFNK diagnostic ran. The failed job was rerun and is
  currently executing at the same provider head `bc18b095`.
- Atlas remains at CFDrs default `931ee3a0`; no hosted source result is claimed
  until the rerun reaches the Rust and figure gates.

## ATLAS-CFDRS-JFNK-MERGE-2026-08-19 — exact-head hosted closure

- CFDrs PR #358 merged at `834340f7` after required Rust workspace and figure
  SSOT checks passed in run `32229463775`. The Atlas gitlink advances from
  `931ee3a0` to that fetched default head; the provider checkout remains on a
  peer branch and is not switched or cleaned.

## ATLAS-CACHE-FORK-055 — Horae repo-local target cleanup complete

- The conformance audit identified `repos/horae/target` as a derived cache fork
  beside the shared `D:\\atlas\\target`. The exact directory contained the
  Cargo `.rustc_info.json` marker and was removed after path verification.
- Re-running the provider conformance scan for Horae reports `target_forks: 0`;
  no source, lockfile, or provider checkout state changed.

## ATLAS-KWAVERS-BOOK-FENCE-2026-08-19 — restore truthful mdBook fence semantics [patch] — in progress

- Kwavers commit `cbf99272b4265b720b4e4d597515f91ba944fefa` changes the
  affected book fences to `text` or `rust,ignore` according to their actual
  content and corrects the stale `DENSITY_WATER_NOMINAL` excerpt.
- `mdbook test docs/book` and `mdbook build docs/book` pass at that exact
  provider head. This closes the prior 286-failure book-gate defect without
  pretending that workspace-dependent excerpts are standalone examples.
- The linked source examples still need `cargo check -p kwavers --examples
  --locked` after the shared Atlas overlay lock mismatch is repaired. The
  current command stops before compilation because `--locked` refuses the
  overlay's requested lockfile update; no Rust-source result is claimed.

## ATLAS-CONFORMANCE-SUBMODULE-STATUS-2026-08-19 — classify provider dirt after root status [patch] — in progress

- Hosted conformance runs `32247752034` and `32248848495` failed before the
  ratchet scan with the generic `root worktree is dirty` error, while the
  hosted checkout was clean at the root revision. The scanner's root status
  query included nested submodule summaries and therefore hid the provider
  boundary that its next checks own.
- `scripts/atlas-conformance.py` now uses `--ignore-submodules=all` for the
  root status query and retains the per-provider status checks. Its focused
  regression suite passes 18/18, including the provider-dirt classification.
- The next exact-head hosted run must pass the scanner and lock-form gates;
  local execution remains intentionally blocked by peer-dirty provider trees.

## ATLAS-CONFORMANCE-RATCHET-2026-08-19 — exact provider regressions [patch] — blocked

- Hosted conformance run `32250014209` reached the exact root head `a4f24ee`
  after the root line-ending and submodule-status fixes. It reports three
  source regressions; the committed baseline remains unchanged.
- Exact gitlink attribution is CFDrs `834340f7`:
  `crates/cfd-1d/src/solver/core/network_solver.rs` crossed 500 lines
  (`500 -> 568`); Consus `2e0df9f8`:
  `crates/consus-zarr/src/codec/mod.rs` crossed 500 lines (`439 -> 643`);
  and Coeus `5adc2d16`:
  `crates/coeus-autograd/src/lib.rs` contributes the counted crate-level
  `#![allow(...)]` surface (`18 -> 19`).
- No baseline raise is authorized. The source repairs require provider-owned
  edits, focused gates, hosted conformance, and an exact-head pointer sweep.
  The current provider checkouts/lanes are peer-owned and dirty; re-open when
  those claims land or become stale and reclaimable.
- Fresh clean-checkout run `32389729879` at root `dfc0184` confirms the same
  defect class with six current regressions: `CFDrs/oversized_files` 134 ->
  135, `coeus/crate_level_allows` 18 -> 19, `consus/oversized_files` 82 ->
  83, `moirai/seqcst_production` 101 -> 107, `ritk/manifest_implementation`
  105 -> 106, and `ritk/commented_out_code` 8 -> 9. The run also reports 15
  tightenings; none authorizes a baseline increase. These counts bind to the
  committed provider gitlinks and remain blocked on provider-owned source
  repairs, not on the Atlas book-gate change.
- The next exact root run at `f621c1d` reduced the class to five regressions:
  CFDrs `oversized_files` 134 -> 135, Coeus `crate_level_allows` 18 -> 19,
  Moirai `seqcst_production` 101 -> 107, and RITK
  `manifest_implementation` 105 -> 106 plus `commented_out_code` 8 -> 9.
  Consus no longer regresses after Atlas corrected its gitlink to merged
  default `e121b9d4`. The concurrent overlay run `32391551896` exposed two
  stale `moirai-http` entries caused by dirty local Moirai state; root commit
  `f621c1d` removes them from the generated block. No baseline raise is
  authorized; the next hosted run must collect both fixes.
Re-open trigger: CFDrs, Coeus, Moirai, or RITK lands the named source repair,
or its provider claim becomes stale and is reclaimed for a focused repair.

## ATLAS-WORKTREE-TAKEOVER-107 — stale-lane sweep across the stack [patch] — in progress 2026-08-20

Audited every worktree in every member (30 trees), ranked by branch-tip age, and
measured delivery state — ahead of `origin/main`, pushed, merged — rather than
inferring it from the branch name.

**Four branches held unpushed commits.** Same failure as
ATLAS-RITK-D2-STRANDED-100: authored, never delivered, invisible to every peer.
All four are now pushed; none merged, so nothing was decided on their behalf.

| repo | branch | unpushed | content |
| --- | --- | --- | --- |
| consus | `fix/consus-zarr-endian-hardening-221` | 1 | crc32c codec, "close three silent-swap paths" — a correctness fix |
| consus | `codex/adr-0045-p4-benchmark-parser` | 11 | breaking: remove package-owned S3, centralize async I/O in Moirai |
| kwavers | `refactor/seismic-example-structure` | 13 | seismic DICOM/quality sharing, transcranial FWI partition (45 files) |
| mnemosyne | `codex/mnemosyne-board-cleanup` | 1 | board closure docs |

**Correction: one entry in that table was wrong.** `feat/qus-attenuation-b2` was
listed here as undelivered because its local branch was unpushed. The work had in
fact landed — merged as `8003eeaa3` via PR #404 on 2026-08-19. A squash re-authors
the hash, so the local branch still looked ahead of main. This is precisely the
false positive ATLAS-BOARD-DELIVERY-AUDIT-101 measured at 3-in-4, and checking the
PR rather than the hash is what catches it. Pushing it was harmless but redundant;
the lane is now closed as delivered. `refactor/seismic-example-structure` replaces
it in the table — 13 commits, 45 files, no PR, genuinely unpushed until this sweep.

**Six lanes closed**, all verified delivered by PR and holding only overlay
lockfile churn: `coeus-layernorm-shape`, `apollo-root-cleanup`,
`CFDrs-runtime-budget`, `helios-lock-027`, `asclepius-lock-027`,
`kwavers-qus-attenuation`. Four of those had **merged** PRs while their local
branches still read as ahead of main — the same re-authoring effect. coeus,
apollo, CFDrs, helios and asclepius are each back to a single tree.

**One stalled PR unblocked.** hermes #55 ("Close orphan cleanup evidence") sat
CONFLICTING and untouched for 29h. Its conflict was a PM-artifact collision:
main had inserted a new board item directly above the one the commit flips from
`in progress` to `done`. Resolved as a union — both items kept, the status change
applied — rebased, force-pushed with lease; the PR is MERGEABLE again.

**The find: a stranded upstream capability with a downstream consumer already
built against it.**

Taking over the consus `adr-0045-p4-benchmark` lane, its tests failed to compile.
The cause was not that lane's uncommitted work — which is complete and good: an
offset-overflow guard placed *before* allocation in `read_at_bounded`, with a
test that drives `u64::MAX` through it. The cause was upstream:

- moirai `b548bc9` "add positioned I/O contracts" defines `AsyncReadAt` and
  `AsyncLength`.
- It is **not an ancestor of moirai `main`**. Pushed to
  `codex/moirai-positioned-io`, no PR ever opened, now 1 ahead / **14 behind**.
- consus `main` imports those traits in five modules and pins them **by
  revision**: its committed lockfile carries
  `git+https://github.com/ryancinsight/Moirai?rev=b548bc9`.

**Correction.** I first recorded that consus "cannot compile at all". It
compiles fine in CI — the rev pin resolves, because the commit is pushed. The
build failures I hit came from the Atlas development overlay redirecting
`moirai-*` to the local tree, which sits on a branch without these contracts.
That was my local setup, not a consus defect, and the earlier note said
otherwise.

The real problem is narrower and still worth fixing: a `rev` pin onto an
unmerged commit is quarantine, not a dependency. It freezes consus 14 commits
behind moirai `main` and it cannot take any moirai change without moving to
another unmerged rev. Landing the commit is what lets consus return to an
ordinary version requirement.

Landed as moirai PR #145: cherry-picked onto current `main`, applied cleanly
across the 14 intervening commits, authorship preserved. 90/90 `moirai-async`
tests, fmt clean, zero clippy findings. Merging it unblocks the consus branch;
consus itself is untouched, per co-evolution (upstream first).

**Why this class keeps appearing.** Four unpushed branches, eleven stashes, three
untracked ADRs, and one stranded upstream commit — all found in one day, none
detectable by any gate, because every gate inspects what is presented to it. The
common shape is work that exists only in one machine's local state. The cheap
detectors are known and now recorded: `git rev-list origin/main..<branch>` per
local branch, `git stash list`, `git ls-files --others docs/adr/`, and
`git merge-base --is-ancestor` for cited commits (ATLAS-BOARD-DELIVERY-AUDIT-101).

**Remaining, not actioned.** Pushed-but-unmerged branches with real divergence —
CFDrs `codex/cfdrs-backward-step-108` (99 ahead), helios and asclepius both on
`fix/apollo-lock-0.27` (3 and 2 ahead, a coordinated cross-repo lock sweep),
hephaestus `codex/hephaestus-fdtd-107`, hermes `codex/hermes-orphan-closure`.
These are visible on their remotes, so they are not at risk; triaging whether
each is in-flight or abandoned needs their owners or a PR check, not a takeover.

## ATLAS-KWAVERS-LANE-SPRAWL-104 — five worktrees on one repo [patch] — todo

`repos/kwavers` carries five working trees against the two-tree bound
(main plus one lane):

| tree | branch |
| --- | --- |
| `repos/kwavers` (main tree) | `build/adopt-aequitas-degree` |
| `worktrees/kwavers-format` | `feat/kwavers-sonoluminescence` |
| `worktrees/kwavers-fwi-asm-split-step` | `feat/kwavers-fwi-asm-split-step` |
| `worktrees/kwavers-gpu-honest` | `feat/d3-consolidate-speckle-tracking` |
| `worktrees/kwavers-qus-attenuation` | `feat/qus-attenuation-b2` |

Two are named for work they no longer hold (`kwavers-format` holds
sonoluminescence, `kwavers-gpu-honest` holds the D3 speckle-tracking seam that
merged as PR #409), which is the tell that lanes are being re-pointed without
being closed. Each lane is a full checkout of a large workspace.

**Fix.** Sweep per the lane lifecycle: for each, determine whether its branch is
merged, live, or stale (branch tip time plus board claim), close the merged and
stale ones with `git worktree remove`, and keep at most one. Not a blind
deletion — a lane holding unpushed commits or uncommitted work is rescued first
(ATLAS-RITK-D2-STRANDED-100 is what that looks like when it is not).

**Stashes: eleven, not two, and now pinned (2026-08-20).** The earlier note said
two; that came from a truncated listing. `git stash list` in `repos/kwavers`
shows eleven entries, 2 to 11 days old:

| stash | files | message |
| --- | --- | --- |
| 0 | 4 | README Quick Start + example off LendingIterator |
| 1 | 40 | `kwavers-stranded-2` |
| 2 | 7 | `pre-gitlink-advance-dirt` |
| 3, 4 | 1 each | `main-cargolock`, `temp-cargolock` |
| 5, 6 | 1 each | kwavers-optics branch preservation |
| 7 | 1 | xtask NumPy facade audit |
| 8 | 0 | empty |
| 9 | 27 | atlas-migration-context |
| 10 | 144 | atlas-migration-push-context |

**Action taken — non-destructive.** Every non-empty stash is pinned to
`refs/rescue/stash-<n>-<slug>` and pushed, so the content survives `git stash
clear`, gc, or a tree reset, and is visible to peers instead of living in one
machine's stash list. Nothing was dropped: dropping a stash is irreversible loss
of uncommitted work, which is not mine to decide.

**What the evidence does not show.** Comparing each stash's blobs against
`origin/main` gives 8 of 10 "differs", but that is close to meaningless as a
uniqueness signal — an 11-day-old stash differs because main moved on, not
because its intent is undelivered. Classifying these needs per-stash judgment
(is the change already landed under a different shape?), which the message
alone cannot settle. Recorded so the next pass does not mistake drift for value.

Four are almost certainly disposable by their own names — `main-cargolock`,
`temp-cargolock`, `pre-gitlink-advance-dirt`, and the empty one — being lockfile
and dirt parking rather than work. The three large ones (1, 9, 10) look like real
migration work and want their author.

- **ATLAS-FWI-PSTD-BLI-106** Extend the PSTD projections to band-limited stencils [minor] (2026-08-23; kwavers PR #612, merge `f98acb01b`) — `f6cc385d8`, `f98acb01b`
## ATLAS-ADR-UNTRACKED-105 — completed ADRs left untracked [patch] — in progress 2026-08-19 (kwavers closed; coeus + hephaestus open)

`kwavers/docs/adr/112-convex-array-rasterizer-seam.md` is complete (110 lines,
full context/decision/consequences, Status: Accepted) and its item **COV-3 is
recorded done** on the kwavers board — but the file was never `git add`ed. It
exists only in the shared working tree.

Same class as ATLAS-RITK-D2-STRANDED-100: the work happened, the record did not
ship. It is worse in one way — an ADR *is* the deliverable, so an untracked ADR
means the decision has no durable existence at all, and a fresh clone shows a
decision that was made and then lost.

`scripts/adr-index.py` detects this, reports "untracked, so absent from a fresh
clone", and excludes the file from the generated index — correctly, since the
index records what a clone would have. The check now returns nonzero for that
anomaly, so a matching generated index cannot pass while the ADR is absent from
`HEAD`.

**Swept 2026-08-19 — it is systematic, three members.**
`git ls-files --others --exclude-standard docs/adr/` across every member:

| member | untracked ADR | lines | status |
| --- | --- | --- | --- |
| kwavers | `112-convex-array-rasterizer-seam.md` | 110 | **committed** via PR #418; index and corpus now agree on main |
| coeus | `0066-provider-owned-dense-product-bridge.md` | 108 | header carries no status line |
| hephaestus | `0052-device-neutral-sliding-window-seam.md` | 216 | Proposed |

All three are full records with six sections each, not scaffolding — 434 lines
of decision rationale that no clone of these repositories contains. Both coeus
and hephaestus also carry a dirty `docs/adr/README.md`, consistent with an index
regenerated against a file that was then never committed.

**Fix.** Per member: commit the ADR (noting it was found untracked), regenerate
the index, push. Two need a header decision first — coeus 0066 has no `Status`
line at all, and hephaestus 0052 is `Proposed`, so whether either is Accepted
needs its author or its evidence, not my assumption.

**Mechanization landed 2026-08-20.** `check_indexes` treats every tracked-tree
anomaly as a gate failure; the focused regression suite passes 4/4. The
provider ADR commits and their regenerated indexes remain external to this
root-only increment and stay open until their owning streams commit them.

**It got worse before it got better.** While PR #418 was in review, peer PR #419
"restored the missing 112 index row" — committing the row but not the file. For
a few hours `main` advertised 112 in its index while a fresh clone got a dead
link, which is strictly worse than the file merely being absent: the index
asserted a record that did not exist. PR #418 committed the file the row refers
to; verified on `origin/main` by resolving every indexed link against the tree.

**Mechanization.** The detection already exists and already ran: `adr-index.py`
prints "untracked, so absent from a fresh clone" and correctly excludes the
file. It exits nonzero only for index drift, so an untracked ADR alone is a
message nobody fails on. Making that condition part of the nonzero exit is a
one-line change and turns a passed-over log line into a gate.


- **ATLAS-HERMES-CODEGEN-SSOT-2026-08-21** Resolve SIMD codegen source of truth [arch][minor] (2026-08-23; hermes PR #59 merged `78b8745` after all hosted gates passed at exact head `569ed00`; lane removed, branch deleted) — `78b8745`, `569ed00`

## ATLAS-CROSS-MEMBER-SWEEP-108 — cross-member staleness and dirt sweep [patch] (2026-08-23) — in progress

Liveness-measured sweep of all 28 member checkouts. Findings:

- **moirai**: LIVE peer (tree modified mid-sweep) — excluded, never touched.
- **CFDrs**: the largest anomaly — 53-commit validation/binding series
  (Sprints 1.96.200-204 try_new validation, typed cfd-python boundary)
  pushed to `codex/cfdrs-tvd-test-integration` but never merged; main moved
  20 commits independently; 56 dirty files atop. Uncommitted WIP rescued to
  `origin/rescue/cfdrs-wip-20260821`; the series is now up for integration
  as **CFDrs PR #360**. Integration resolved locally 2026-08-23: two-file
  conflict (CHANGELOG unioned; cfd-validation Cargo.toml = series deps +
  main's athena-leto dev-dep), workspace check/clippy clean, 436+1738 tests
  green, doctests green, fmt applied. Pushed to the PR branch at `b512f778`;
  hosted CI running.
- **16 dead-session dirt patches** (aequitas, asclepius, eunomia, gaia,
  harmonia, horae, hyperion, iris, leto, melinoe, proteus, themis from the
  2026-08-20 ~14:2x session; helios/apollo/consus from ~16:55; ritk from
  08-21): PM-artifact updates (+30..+688 lines each), rescue-committed
  verbatim and pushed to `rescue/pm-sweep-20260820` per member; working
  trees restored clean at their prior heads. Port-or-drop parked with
  their author.
- **A downstream private consumer**: RESOLVED 2026-08-23. The stranded
  series was not the problem — it FIXES the default branch's redness (stale
  first-party path deps left the workspace unresolvable). Series merged to
  the consumer's default and the follow-up typed-quantity port delivered via
  its PR #7 (`3439842`): MODALITY-002 debt discharged, 27 errors to zero,
  nextest 525 passed on the stack toolchain, fmt/clippy clean. Named per
  ATLAS-PRIVACY-NAMING-1 only in that org's own tracker, not here.
- Clean but stale checkouts (behind origin, no dirt): apollo, consus,
  eunomia, gaia, harmonia, horae, hyperion, melinoe, ritk, themis, tyche,
  athena — fast-forward at next touch of each member.

**CFDrs PR #360 delivered 2026-08-24.** Hosted workspace gate green
(15m25s) after one CI-only clippy fix (DES rejection test now constructs
its config with struct-update syntax; local gates must run with
`RUSTFLAGS="-D warnings"` to match the hosted floor). Merge `eee77aa2`.
Lane cleanup: five stale worktrees removed, 24 fully-merged local branches
deleted, 14 unmerged branches remain — all tips pushed to origin, each a
stranded series needing per-branch judgment (filed as follow-up).
Local-only tips preserved via push before any deletion.

**Branch-judgment sweep closed 2026-08-24.** All 14 unmerged branches
adjudicated: every series conflicts with the lint/tracing/validation
refactors main absorbed (PRs #349-#367+), and origin/main passes the
hosted -D warnings workspace gate today — the acceptance target those
series were driving toward. Verified content-level: the allocator-gate,
GIL-boundary, and blueprint-lint fixes all exist on main in evolved form
(the test-module-scoped allocator replaced the ungated library static).
All local branch tips deleted; remote branches retained as archive.
CFDrs now carries exactly one local branch (main) at the merged head.

**Takeover completed 2026-08-24 (author grant).** All rescue branches
adjudicated and delivered or retired:
- kwavers SWE volumetric WIP: integrated via PR #627 (`7bb84b3a`); the
  fmt gate it tripped is fixed on main (`0e1c92753`).
- CFDrs post-series WIP: integrated via PR #369 — LF-normalizing
  .gitattributes landed stack-side, clippy --fix discharged residual
  findings, 3256 tests green pre-fixup.
- kwavers imaging ratchet slice: delivered via PR #629 (`bde986c1`);
  the transducer lint-floor commit was already superseded on main.
- coeus cache residue: loss-revert hunks rejected (recorded); PM-doc
  residue superseded by the merged cache delivery — branch retired.
- PM-sweep snapshots: 8 members merged to defaults directly (asclepius,
  gaia, harmonia, iris, proteus, helios, ritk + athena untracked set);
  8 members' snapshots judged stale against heavily-advanced defaults
  (conflict magnitude/direction evidence) — branches deleted, remotes
  retained.
All local+remote rescue refs are gone; every verdict recorded here.

New defect filed by the sweep: asclepius pins aequitas ^0.1.0 / coeus
^0.9.0 — both no longer resolvable (aequitas serves only 0.2.0; coeus
dropped aequitas and moved to 0.10.0). Overlay builds of asclepius are
red for everyone. Filed as the next DoR item: advance asclepius's
first-party deps through the 0.9→0.10 API surface.

**PR-fleet takeover 2026-08-24.** 25 open PRs audited across 14 members:
- MERGED: leto #121 (draft → ready → merged), iris #19 (docs record);
  kwavers #596/#450 and CFDrs #362 closed superseded (verified landed via
  #629 / #442+556741e / test-module-scoped allocator respectively).
- DEFECT FOUND + FIXED on asclepius main: the PM-sweep rescue snapshot
  swept the documented-untracked local Atlas overlay (.cargo/config.toml
  with absolute D:/atlas target-dir) into git, leaking the host path into
  CI test binaries and breaking Verify. Untracked + ignored (f8fcea6);
  CI re-running.  ritk has the same leak class with D:/msys64 compiler
  paths — older (July), pre-existing; fix pushed as ritk PR #207.
- **ritk overlay leak fixed 2026-08-24:** PR #207 merged at `e875f2b4`
  (base `a974573e`, the PM-stranded-snapshot default). `.cargo/config.toml`
  untracked + ignored; post-merge CI and Python CI both terminal success at
  `e875f2b4`; live Pages HTTP 200. Atlas gitlink advanced `6daf72b0` →
  `e875f2b4` (the prior pointer referenced the unmerged fix branch tip, not
  a main commit).
- **leto advanced 2026-08-24:** gitlink `fc0648ee9` → `7d6ac26ff` (PR #121
  iterative-solver family deletion; hosted CI + pages-build-deployment green
  at head). Closes ATLAS-LETO-BOOK's pending Pages clause.
- **ritk overlay leak fixed 2026-08-24:** PR #207 merged at `e875f2b4`
  (base `a974573e`, the PM-stranded-snapshot default). `.cargo/config.toml`
  untracked + ignored; post-merge CI and Python CI both terminal success at
  `e875f2b4`; live Pages HTTP 200. Atlas gitlink advanced `6daf72b0` →
  `e875f2b4` (the prior pointer referenced the unmerged fix branch tip, not
  a main commit).
- **leto advanced 2026-08-24:** gitlink `fc0648ee9` → `7d6ac26ff` (PR #121
  iterative-solver family deletion; hosted CI + pages-build-deployment green
  at head). Closes ATLAS-LETO-BOOK's pending Pages clause.
- Lockfile-guard promotion PRs (asclepius #26, athena #17, CFDrs #368,
  consus #54, helios #70, moirai #162, proteus #18): branches updated
  with main to absorb fixes; CI re-running.
- Remaining open feature PRs (kwavers #424/#439/#440/#443/#617/#620/
  #622–#624, helios #55/#69, proteus #17, hephaestus #216, ritk #144)
  are genuinely diverged series needing per-PR integration engineering;
  their old CI runs died at the 24h wall.

**kwavers #424 delivered 2026-08-25** (oldest diverged PR, taken over):
the FWI-024-D rotating opposed-linear-array acquisition — the geometry
ATLAS-FWI-PSTD-BLI-106's BLI extensions were built for. Integrated with
current main; ADR 116 renumbered to ADR 122 (slot collision with the
clippy-floor ADR). Its strict-clippy fixups converged with a peer's
9d8c5f370 on main. Merged as kwavers #634 (c11dffcf).

**kwavers #443 delivered 2026-08-26** (taken over): console log sink →
stderr. Integration required two rounds against a moving main — the
first CI run exposed a real 60 s TIMEOUT regression in
swe_3d_validation::volumetric_tracking_covers_non_pml_domain; fixed by
right-sizing the coverage grid to 40×40×28 / PML 6
(resolution-independent property, 3× speedup) rather than raising the
timeout. Second run green; merged (9982b37). CI-duration observation:
the Test Suite Coverage job ran 38–43 min even green — see
KWAVERS-CI-PIPELINE-001 for the consolidation fix.

**helios #55 delivered 2026-08-25** (taken over): typed-slopes series
(RITK orientation-tag consumption in helios-domain, deny-pedantic floor
with 11 lint classes fixed outright, ADR casing, package description).
Integration surfaced that the branch's new floor exposed pre-existing
main-side findings; all resolved (or-patterns, test-module unwraps →
expect with invariants, trivially-copy pass-by-ref with a scoped expect
at its borrow-boundary reason, doc backticks). Workspace clippy clean
under --all-features, 262 tests green. Merged (ddf282a). Remaining
diverged: helios #69 (delivered 8/25), proteus #17 (delivered 8/25),
hephaestus #216 (delivered 8/25), ritk #144, kwavers #439/#440/#443/
#617/#620/#622-#624. ritk #144 trial: semantic divergence — main's
dti/volume eigen evolution (diffusion_eigen/symmetric_eigen) superseded
the branch's decompose_3x3_symmetric route; the series needs a real
rebase onto that evolution, not marker resolution. Trial reset;
branch preserved on origin. **Verdict finalized 2026-08-25**: all four
commits verified content-level superseded — DirectionInterpolation/
Trilinear lives in maps/volume.rs, svd_decompose replaced the retired
SVD entry points, the borrowed voxel-view seam evolved into
ritk-image/src/region/{voxel,rows,iter}.rs, and the CLI
OrientationSamplingMode is in ritk-cli tract.rs. PR #144 closed
superseded with that evidence; ritk main verified 5675 tests green.

**ritk #154 delivered 2026-08-25** (taken over): tract output-format
series (.trk/.trx writers, Kabsch svd_decompose migration, pedantic
floor). Integrated with current main across ~90 conflicted files —
conflicts were uniformly the branch's ratchet-reason annotations vs
main's plain forms; branch side kept as the ratchet superset. Three
real gaps fixed during integration: undeclared example submodules,
unpopulated phantom ground-truth fields, and a bulk-resolution casualty
(restored main's B-spline dispatch manifest).

**Tooling defect recorded**: rustc E0583 "file not found for module"
fires for example submodules under \?\-prefixed worktree paths
(D:/atlas/worktrees/*) while the same tree builds from the canonical
checkout — a Windows UNC-path rustc limitation to note for all future
lane-based verification (verify from repos/<member> when example
submodules are involved).

**helios #69 delivered 2026-08-25** (taken over): Radon input-error
assertions + executable book oracle + typed extension metadata. Clean
fast-forward of the series with current main; 284 tests green.
Merged (9499501).

**Lane census 2026-08-25**: stack worktree lanes reduced 26 → 15; all
MERGED lanes removed, unmerged/active lanes retained. A peer's
proteus-mat-adoption campaign left four member gitlinks pinned to
unpushed local branches (cat-C: unreachable from any clone) — every
referenced branch has been pushed to its origin so all atlas pins now
resolve. Their merges remain that campaign's follow-up; coherence audit:
0 stale-advanceable, remaining defects are reachable cat-B pins only.

**CFDrs #368 delivered 2026-08-25** (taken over): lockfile-guard
promotion integrated with current main (one trivial conflict — both
sides had fixed the erasing 0*nx index in the LBM streaming test).
Hosted workspace gate green 16m15s. Merged (14fc2c0). The seven
lockfile-guard promotions are now all landed stack-wide.
clippy-floor ADR). Its strict-clippy fixups converged with a peer's
9d8c5f370 on main. Merged as kwavers #634 (`c11dffcf`). Remaining
diverged feature PRs: helios #55/#69, proteus #17, hephaestus #216,
ritk #144, kwavers #439/#440/#443/#617/#620/#622-#624.

Re-open triggers: CFDrs PR #360 verdict [collected]; author decisions on the rescue
branches; moirai re-check after its live peer's commit lands.

## ATLAS-LINT-CALIB - Calibrate the board-reference lint to corpus conventions [pm-hygiene] [patch] [S]

- Outcome: `scripts/atlas-board-lint.py` fails loudly on references that
  matter without burying them under archive noise.
- Measured + triaged 2026-08-24. 565 mentions / 329 unique ids in
  live-item prose, classified by containing item:
  CROSS-MEMBER-SWEEP-108 inventory 230, MULTIPHYSICS-ADOPTION-100 101,
  GPU-ACQUISITION-POINTER-ADVANCE 91, remaining sweeps/books <60 total.
  Verdict: ~95 percent are scan-inventory listings inside active sweep
  items - data, not broken pointers - and those blocks leave the lint's
  scope when the sweeps close. Zero actionable file-it/fix-ref cases.
- Also fixed en route: ATLAS-KWAVERS-STALE-TREE-107 recorded twice with
  identical bodies; second block removed (34 lines), ids unique again.
- Diagnostic note for posterity: two rounds chased "U+FFFD mojibake" that
  did not exist in the files - it was terminal codepage rendering of em
  dashes inside python repr output. Verify suspected encoding damage with
  a character count in python, never by console appearance.
- Disposition: reference findings stay report-only by design while
  sweep-style inventory items are a living pattern; the duplicate-id gate
  stays hard. Revisit enforcing mode only if a non-inventory dangling ref
  class appears.
- Status: done (2026-08-24)


## ATLAS-CFDRS-STALE-EXAMPLE-PAGES-001 - Book example pages for deleted examples [docs] [patch] [S]

- Outcome: docs/book/example pages reference sources that exist and run.
- Found 2026-08-24: the strict pre-commit dead-link gate flags
  cfd_demo.md and matrix_free_demo.md linking
  ../../../examples/{cfd,matrix_free}_demo.rs - both .rs files no longer
  exist, so their Run commands fail too. Pages carry generated-figure
  markers, so the fix belongs in the generating pipeline (skip examples
  whose source file is absent), not in hand-edited markdown.
- Status: todo

## ATLAS-BOARD-CLOSURE-CANON-001 - Canonicalize historical closure markers [pm-hygiene] [patch] [M]

- Outcome: every closed item carries the one canonical heading marker so
  atlas-board-compact.py archives at full power and
  atlas-board-lint.py's reference scope stays accurate.
- Measured 2026-08-24: compact dry-run archived only 18 of 236 backlog
  items (8 percent) because closure markers vary by era - heading
  "- closed DATE", body Status lines, checkmark bullets, unmarked.
  Full-power archival would collapse thousands of archive-prose lines;
  today they remain live-scope and feed the 323 reference mentions the
  lint reports.
- Scope: pick the canonical form (heading `- closed YYYY-MM-DD`);
  script a reviewed one-pass normalization; rerun compaction; then flip
  ATLAS-LINT-CALIB's reference report toward enforcing for items that
  stay live after normalization.
- Status: in-progress (integrator: claude session; lease: scripts/atlas-board-canonicalize.py, backlog.md, checklist.md, focused tests)

## KWAVERS-CI-PIPELINE-001 - Consolidate kwavers CI to one verification pipeline [ci] [patch]

- Outcome: one workflow whose jobs carry the stage structure (build-once,
  cheapest-first, affected-scope filters); mdBook deploy off pull_request
  events; benchmark regression job removed (benchmarks run locally per
  policy - CI keeps the single-iteration bench smoke only).
- Evidence 2026-08-24: six sibling workflows fire per PR event and per
  main push; queue sat 6-15 min behind one busy runner; one main-push
  CI/CD Pipeline run ended cancelled, leaving that merge unverified.
- Status: todo

## ATLAS-RUNNER-CAPACITY-001 - Size runner slots to fleet width [infra] [patch]

- Outcome: no verification job queued past its own runtime target; runner
  slots sized to fleet width x per-event jobs, or per-event jobs shrunk by
  affected-scope filters (KWAVERS-CI-PIPELINE-001 is the largest shed).
- Evidence 2026-08-24: kwavers queue depth ~10 with one in_progress.
- Status: todo

## ATLAS-OUTPUT-ROOT-001 - Merge duplicate run-output roots [pm-hygiene] [patch] - closed 2026-08-26

- done — outputs/ folded into output/scratch-consolidated-20260826/;
  ignore line removed so regrowth is visible. Commit: atlas chore
  "One run-output root".

## ATLAS-BRANCH-INVENTORY-001 - Burn down stack branch inventories [git-hygiene] [patch]

- Outcome: every member's local branches map to an open item or enqueued
  PR (orient rule); measured 2026-08-26: kwavers 65 (12 merged, 6 gone),
  moirai 30 (24 merged, 15 gone), coeus 21, apollo 17, hermes 14,
  helios 16. Merged/gone prune mechanically; the unmerged remainder
  classifies by patch-id against origin default (rebase/squash-landed
  deletes as landed; unique deltas salvage per takeover) — one
  mechanical sweep per member, proportionate triage.
- Sweep done 2026-08-26 — 125 branches deleted across 26 members (merged
  into origin default, or gone-upstream with cherry-verified empty delta);
  kwavers stashes cleared by peer.
- kwavers classified 2026-08-26: 56 -> 35 refs (21 more landed branches
  deleted; every survivor verified to hold real content deltas vs main —
  content-supersession test on touched files, not just patch-id).
  Survivor families, takeover material closest-to-done-first: 8
  PR-scratch (pr-622/623/624/633/646, fix622/fix622-work/fix622b, small
  deltas); 5 merged-PR leftovers (+1..+8 past merged tips: #364 #434
  #443 #609, remove-simulated-gpu-swe); 7 recent seams/docs/ci (Aug
  19-25); 12 July-era codex/* WIP (aequitas family, +3..+138 commits —
  largest recoverable value, oldest basis, naming-rule renames due at
  takeover).
- ritk classified 2026-08-26: 33 -> 19 refs (15 deleted: merged tips,
  cherry-landed, merged). 17 survivors with real deltas: 5 merged-PR
  tails (+1..+3 past #54 #80 #116 #154 #166); 4 large Aug 1-7 WIP
  (release-workflow-caller +35, coeus-publishability +29,
  reconcile-model-coeus +26, gradient-reorientation +20); 8 small
  recent fixes/docs (Aug 11-19, +1..+3).
- Mechanical phase closed 2026-08-26, stack-wide: coeus 21->17 (note the
  coeus-frobenius provider/cherry/rebase/v2 sibling family — consolidate
  at takeover), gaia 19->2 (cascade/provider-042 held by the tree's
  checkout bookkeeping), apollo 16->12, and 50 more deletions across the
  other 21 members (consus 13->5, helios 14->7, moirai 7->4, ...).
  Session total: ~236 branches deleted, every deletion evidence-backed
  (merged / cherry-landed / merged-PR tip / content-superseded).
  Remaining work: ~98 survivor branches with real deltas are takeover
  material, familied above for kwavers/ritk/coeus/apollo; per-item
  takeover increments, not a sweep.
- Settings done 2026-08-26 (user-authorized): delete_branch_on_merge=true
  on all 26 members; allow_auto_merge=true on 25/26 — leoneuro-rs
  declines auto-merge (plan/visibility limit), enqueue falls back to
  merge-on-green there.
- Status: in-progress (mechanical phase done stack-wide; survivor takeovers unclaimed, closest-to-done-first)

## Archive — closed items

Closed items, one line each. Full prose is in git history; commit SHAs below are the entry points.

- **ATLAS-REMOTE-HEAD-AUDIT-2026-08-21** Verify provider defaults from remote refs [patch] (2026-08-21) — `b72563148b693b04fd94fc6c9daf362db062a6fa`, `cd87aec5`
- **ATLAS-HOSTED-RECHECK-2026-08-21** Reconcile provider release evidence [patch] (2026-08-21) — `632df717`, `2d265d47`, `39da4782`, `7a973331`
- **ATLAS-EXACT-HEAD-RECHECK-2026-08-21** Reconcile remote provider defaults [patch] (2026-08-21) — `d1332267`, `3bc0e43d`, `2c074987`, `7d636471`
- **ATLAS-HOSTED-SNAPSHOT-2026-08-21** Reconcile PR and Pages state [patch] (2026-08-21) — `14fdd44c`, `a38b8b50`, `c6473688`, `636a2613`
- **ATLAS-CONFORMANCE-LIVE-2026-08-21** Classify dirty-tree ratchet output [patch] (2026-08-21)
- **ATLAS-INTEGRATOR-AUDIT-2026-08-21** Recheck cross-provider contracts [patch] (2026-08-21) — `a5a92bfc`, `7a973331`
- **ATLAS-AUDIT-FALSE-GREEN-2026-08-21** Close audit attribution gaps `verification` `patch` (2026-08-21)
- **ATLAS-HYPERION-CHROMOPHORE-SOURCE-ORACLE-2026-08-20** Anchor spectral samples [patch] (2026-08-20) — `e2dbc9b`, `0213f94`, `4df62f63`
- **ATLAS-MELINOE-PARTITION-PANIC-ORACLE-2026-08-20** Assert recovered panic values [patch] (2026-08-21) — `689f562`, `67e177d`, `d137d3c`, `d137d3c17d56eb9586812e98ca2861016e711bbb`
- **ATLAS-FIGURE-PROVENANCE-2026-08-20** Remove fabricated quantitative book figures [arch] (2026-08-20)
- **ATLAS-CONSUS-BOOK-GATE-2026-08-20** Add executable Consus book coverage [patch] (2026-08-21) — `0f4af6cf64828063480f824f301e524a78b6745e`, `39da4782`, `5fc1443e`
- **ATLAS-GAP-AUDIT-2026-08-20** Stack-wide scope-vs-delivery closure [major][arch] (2026-08-21) — `2fb4409`, `e2dbc9b`, `4df62f63`, `c5e4c2d`
- **ATLAS-BOOK-GATE-AUDIT-2026-08-20** Keep strict inventory diagnostics truthful [patch] (2026-08-20) — `429ada8`
- **ATLAS-FINAL-PROVIDER-AUDIT-2026-08-20** Exact-head and publication closure [patch] (2026-08-20) — `7ff72e3`, `300f1425`, `33a980ac`, `0c6ffb91ce5d1b68d8da50c6fd12726b7993b1b8`
- **ATLAS-TYCHE-WORKFLOW-PIN-2026-08-20** Refresh shared book workflow pin [patch] (2026-08-21) — `f98ecb14bc5527e3a774a5d4b2bbd109cf5d9157`, `46f4829ef648cec2b9e44bad3a75aef8ef3c34af`, `20c93980f7c98f2e23a89c4a0540f16c8f2d7239`, `10410f2de1ce1529ecbff50fa740b23a1c8f77b9`
- **ATLAS-RITK-WORKFLOW-PIN-2026-08-20** Refresh shared book workflow pin [patch] (2026-08-20) — `20544b405f68e542364da77492ee7a7ffcc44ae9`, `aa48c471ac96eb81869437d84bab439e18d89038`, `a16a27f24e814cb1e4315d9c44dec4394f0e26b0`
- **ATLAS-HERMES-BOOK-CLOSURE-2026-08-20** Close executable book gate [patch] (2026-08-20) — `3ae6e1982f54f6af191904e52ba0cce4c27ee9be`, `c5e4c2dc005f215c403bd5b3c66db275bd040afb`
- **ATLAS-MNEMOSYNE-BOOK-CLOSURE-2026-08-20** Close executable book gate [patch] (2026-08-20) — `6b0e490752f215782d63f876e85059534e25af54`
- **ATLAS-HORAE-WORKFLOW-PIN-2026-08-20** Refresh shared book workflow pin [patch] (2026-08-20) — `aaed0cff8e777d62fcaff4f20b3347bb1eefa403`, `c2e7766847e3ef28125b809d98fe07250acc6cec`, `a05dbebbb947a627cbe69a9d839fb88cae46e459`
- **ATLAS-HYPERION-WORKFLOW-PIN-2026-08-20** Refresh shared book workflow pin [patch] (2026-08-20) — `5e8d47008e01f401c8d1b464c30e2909ff1a56c8`, `719d84e80163b958cc5500b5fa44a5b01095d6d1`, `e2dbc9bb28d7f9cbccf354d2a9b278c6231a85d1`
- **ATLAS-HERMES-BOOK-TEST-2026-08-20** Enable executable Hermes book samples [patch] (2026-08-20) — `932468dac5ef4abadea4bdd12d62b420a4225ba7`, `3a39ef16d679dbac9c1a479b2b9c44135e262af3`
- **ATLAS-DOCS-BOOK-RECONCILE-2026-08-20** reconcile book inventory and rot gates [patch] (2026-08-20) — `c1c8ab234559a9f58a34d65c32f6096ee69fc012`
- **ATLAS-AEQUITAS-BOOK-TEST-2026-08-20** enable executable book samples [patch] (2026-08-20) — `809fc973f5df8c0bc0810161851466535efa74db`, `fff8e6f750696001fd40fee95b142bad6cdd756f`, `2f6370561338bfa157dbab1bc2a940d75bcebbf3`, `2308cc2f1308bb15d36ea641ecca9d1a39f41bc5`
- **ATLAS-PROTEUS-BOOK-TEST-2026-08-20** enable executable book examples [patch] (2026-08-20) — `61879d4b4a68e2d201460af0fe6f6a0e7fe9919f`, `4d482709927aa464f9116b36dc016d516b01b8be`, `1c73fdd`, `8b6321c9b02ff5114cee8ff01a0aee9d12076754`
- **ATLAS-MNEMOSYNE-BOOK-TEST-2026-08-20** enable executable book examples [patch] (2026-08-20) — `a527380dce3c02d3596aec9ca65a5a05025625d9`, `7003eb3d09a716a91b4560e1810d65970c874daa`
- **ATLAS-PUBLISH-GRAPH-DOCS-2026-08-20** refresh release graph counts [patch] (2026-08-20)
- **ATLAS-PUBLISH-GRAPH-EXACT-HEAD-2026-08-21** attribute graph to committed gitlinks [patch] (2026-08-21)
- **ATLAS-HORAE-HYPERION-REVERIFY-2026-08-20** close clean provider gates [patch] (2026-08-20) — `0df563a`, `af28f5a`, `b783a6c7`, `63aec555e893`
- **ATLAS-HELIOS-PYPI-2026-08-20** integrate trusted wheel release [patch] (2026-08-20) — `423d6ec9`
- **ATLAS-KWAVERS-DEFAULT-RECHECK-2026-08-20** current default reconciled [patch] (2026-08-20) — `9cf62aa9`
- **ATLAS-ASCLEPIUS-BOOK-TEST-2026-08-20** enable executable book samples [patch] (2026-08-20) — `b660646`, `2f6959b`
- **ATLAS-MOIRAI-BOOK-TEST-2026-08-20** enable executable book samples [patch] (2026-08-20) — `4d9bfb0`, `2cca9cc`, `95891f6`, `3b81286`
- **ATLAS-TYCHE-BOOK-TEST-2026-08-20** enable executable book samples [patch] (2026-08-20) — `1752a0f`, `7b299c8`
- **ATLAS-AEQUITAS-DERIVED-UNITS-2026-08-20** split derived-unit implementation leaf [patch] (2026-08-20) — `809fc973`, `809fc97`
- **ATLAS-RITK-REGISTRY-README-2026-08-19** closed [patch] (2026-08-19) — `01175d67`, `7e13796`
- **ATLAS-RITK-PY-WHEEL-PARITY-2026-08-18** NumPy spatial-axis contract [patch] (2026-08-19) — `ca25e22c`, `86ab2a43`
- **ATLAS-RITK-APOLLO-027-RECONCILIATION-2026-08-18** consumer forward sweep [patch] (2026-08-19) — `6b9092bf`, `d585e0f5c6f6e45e5e551a5ec3ca29f41af5afab`
- **ATLAS-PROVIDER-INTEGRATION-2026-08-17** close the requested provider sweep [patch] (2026-08-18) — `f95209da`, `df8999f`, `5eeaba9`, `dd4cb129`
- **ATLAS-HARMONIA-CONFORMANCE-001** close provider repository conformance debt [patch] — `d01cacf`, `3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb`, `c049d26`
- **ATLAS-PROVIDER-LIVE-CONFORMANCE-001** audit all live provider checkouts [patch]
- **ATLAS-PROTEUS-CONFORMANCE-001** add provider LF policy [patch] — `996b822`, `50e77f4`, `f612c9981547d56021db3a1be7f75631fd78ff4c`, `1ce4bfa`
- **ATLAS-GAIA-CONFORMANCE-001** add provider LF policy [patch] — `3cb6c82`, `4980732cce0f5a022a67e2c5bdaf2efb894bbf42`, `efb0d15`
- **ATLAS-IRIS-CONFORMANCE-001** add provider LF policy [patch] — `3d36a9d`, `f8630a1367f0a72a282b25ed1f73092c17f85ba9`, `c10b328`
- **ATLAS-HELIOS-CONFORMANCE-001** add provider LF policy [patch] — `aa7a4fa`, `a6833b9`, `f8ebe42f2a9c72f9da177cf5f96e15029b8a6d54`
- **ATLAS-AEQUITAS-CI-TIMEOUT-001** bound provider CI jobs [patch] — `5ef6e23`, `3168a41df9771741eb598f9d7dc95daf8cec1253`
- **ATLAS-ASCLEPIUS-CONFORMANCE-001** add provider checkout and CI bounds [patch] — `ff2ffbf`, `b6257ae`, `db33ccafefee8e81cc48cce594150d382ee3a6d8`
- **ATLAS-EUNOMIA-CONFORMANCE-001** add provider LF policy [patch] — `bab4f9f`, `c340d19`, `85e590b789505c66f5174043c2e7e851c20547`
- **ATLAS-TYCHE-CONFORMANCE-001** bound provider CI jobs [patch] — `5eeaba9`, `240b5fe`, `e7f60504268e6c6c0c227210238b3a3eb9135200`
- **ATLAS-LETO-CONFORMANCE-001** bound Python release publication [patch] — `1d7aada`, `01474f2b4b34238ee7966ac650949cd3de1100e5`
- **ATLAS-MNEMOSYNE-CONFORMANCE-002** add provider LF policy [patch] (2026-08-18) — `7967315f`, `cb86bfe`, `1c38a1a65d519ebc04ed5f9da2baa31d16b83705`
- **ATLAS-MOIRAI-EXACT-HEAD-089** Rescue the default-head gate repair [patch] (2026-08-14) — `2ea17bb`, `032c9de`, `e546092d`, `cc80ed4`
- **ATLAS-LETO-EXACT-HEAD-090** Rescue the default-head locked graph [patch] (2026-08-14) — `f3756b5`, `143696d`, `911be9f`
- **ATLAS-EUNOMIA-EXACT-HEAD-091** Integrate the merged float-law head [patch] (2026-08-14) — `108e860`, `b6f001a`, `2e0d724`
- **ATLAS-THEMIS-GITATTRIBUTES-092** Reconcile stale provider PM claim [patch] (2026-08-14) — `fa8dc29`, `17d3647`
- **ATLAS-AEQUITAS-CI-093** Preserve the locked provider graph [patch] (2026-08-14) — `632e8f8`, `b6f001a`, `770a369`
- **ATLAS-PROTEUS-CI-094** Bound and lock provider verification [patch] (2026-08-14) — `671c9fa`, `770a369`, `b6f001a`
- **ATLAS-MOIRAI-NUMA-095** Wire the NUMA policy through the runtime [minor] [arch] (2026-08-14) — `e972174`, `181f87d`, `6d42bd3`, `38e936a`
- **ATLAS-RITK-LANE-SPRAWL-065** Reconcile three ritk working trees [patch] (2026-08-14) — `37e46ef7`, `bcaefa3a`, `e88910d0`
- **ATLAS-CONFORMANCE-WORKTREE-080** The ratchet scans the working tree, not a revision [patch] (2026-08-14)
- **ATLAS-CFDRS-GPU-DEFAULT-084** Bare path deps re-enable a feature the workspace disables [patch] (2026-08-17) — `e16b82c9`, `a3c53da2`
- **ATLAS-ORPHAN-MODULES-096** Uncompiled source files across eight repos [patch] (2026-08-18) — `99dea18`, `403387b`, `1fe438c`, `d56eaa0`
- **ATLAS-TOOLCHAIN-TRIPLE-083** The toolchain pin guards version, not host triple [patch] (2026-08-17) — `81a0e2f`, `977e009`
- **ATLAS-STD-AMX-DETECT-082** `is_x86_feature_detected!("amx-tile")` is unsound [patch] (2026-08-14)
- **ATLAS-GAIA-ORPHAN-081** Delete uncompiled source artifacts [patch] (2026-08-14) — `c06504c`, `18349bc`
- **ATLAS-COEUS-LAYERNORM-SHAPE-031** Complete multi-dimensional LayerNorm contract [minor] (2026-08-13) — `a2638c03`
- **ATLAS-KWAVERS-GATE-REDS-209** Four gate reds escaped from kwavers `23f53284d` [patch] (2026-08-18) — `23f53284d`, `f05d207d7`
- **ATLAS-CONSUS-ZARR-CODEC-FOLLOWUPS-214** Two pieces deliberately left out of `-206`/`-207` [minor] (2026-08-19) — `2b8d71a`
- **ATLAS-CONSUS-ZARR-BYTES-ENDIAN-206** `bytes` codec ignores its `endian` config [major] (2026-08-18) — `2488bbe`
- **ATLAS-CONSUS-ZARR-CRC32-207** `crc32` checksum is neither written nor verified [major] (2026-08-18)
- **ATLAS-CONSUS-ASYNC-FACADE-029** Remove the Consus async placeholder [major] (2026-08-17) — `9e11ba7`, `2dcf05a`
- **ATLAS-PM-ADR-INDEX-025** Member-repo ADR index drift [patch] (2026-08-19)
- **ATLAS-PATH-DEP-AUDIT-001** Sweep `git+https://github.com/ryancinsight/` source URLs across 13 submodule Cargo.lock files [patch] (2026-08-18) — `5c7ee95`, `c10e510d`, `f52c88d6`, `6a4bad71`
- **ATLAS-COEUS-NLLS-004** Gauss-Newton / Levenberg-Marquardt in coeus-optim [minor] — `53816ebf`, `4d634750`, `d1b418c6`, `5adc2d1649bfd2bf68c529b011308e150375810d`
- **ATLAS-GAIA-POLYLINE-006** Polyline geometry and unit-sphere direction sets [minor] (2026-08-19) — `dbed97a`
- **ATLAS-DMRI-DELIVERY-015** CLI, Python, and book surface [minor] (2026-08-15) — `f345a00e`, `532e1ea`, `0ce77ae2`, `e512ca2`

<!-- Prior archive preserved verbatim from compaction pre-state; these items
     predate the current session and would otherwise have been rolled up by
     atlas-board-compact.py into a single (unnumbered) Archive line. -->
 — `9a7fa7e50dd48ee83a2777ef59aa692c8fabc5d`, `53b3f984`
- **ATLAS-RITK-179-2026-08-19** merged NumPy axis recheck (2026-08-19) — `6b9092bf`
- **ATLAS-RITK-D2-WIP-RESIDUAL-103** rebuild the WIP the NUL corruption orphaned [minor] (2026-08-19) — `29b8d4e3`
- **ATLAS-NUL-CORRUPTION-102** files written as all-NUL by a host write failure [patch] (2026-08-19) — `c110664b`
- **ATLAS-BOARD-DELIVERY-AUDIT-101** advisory sweep for undelivered done-claims [patch] (2026-08-21) — `c06504c`, `18349bc`, `29b8d4e3`, `7d671c0e`
- **ATLAS-RITK-D2-STRANDED-100** rescue the unpushed D2 follow-on commit [patch] (2026-08-19) — `c110664b`, `01175d67`, `6731f8f32`, `b71abaf32`
- **ATLAS-HORAE-DORMAND-PRINCE-076** embedded adaptive pair [minor] — `58506a0`, `5c8a828`

- **ATLAS-LIVE-HEAD-SWEEP-026** Reconcile twenty provider CI-pin defaults [patch] (2026-08-13) — `5758df93`, `93e83899`, `5febead4`, `5969f1e3`
- **ATLAS-POSTMERGE-HEAD-RECONCILIATION-030** Reconcile merged caller defaults [patch] (2026-08-13) — `1be7768d`, `1a52590c`, `462cf444`
- **ATLAS-LIVE-CALLER-PINS-027** Refresh requested-provider Atlas workflow pins [patch] (2026-08-13) — `d875348197be12ad593f993a6f1b8a62d3b8b195`, `4c31dd753f06dd93b4c04798cf781df253e3e532`, `d875348`, `964d81db`
- **ATLAS-HEPHAESTUS-REDUCTION-022** Retire superseded product-axis parity PR [patch] (2026-08-13) — `8bc589a`
- **ATLAS-APOLLO-ARCH-021** Retire superseded junk-drawer rename [patch] (2026-08-13) — `49632c6c`, `fc5648964c8194447ef5deea43a8aa9c0dae7c63`
- **ATLAS-APOLLO-VALIDATION-020** Converge shared WGPU validation and Mnemosyne boundary [patch] (2026-08-13) — `a725fe81027f54ee83e56fa72d731b8e2e3f97f1`, `fc5648964c8194447ef5deea43a8aa9c0dae7c63`
- **ATLAS-COEUS-NORM-019** Keep batched Frobenius norms provider-owned [patch] (2026-08-13) — `96d8166c3d683eaaf67e45b8bad0c34e33d8b405`, `72372c918d8d6fcbcc006585736126a480a4f5c2`
- **ATLAS-HELIOS-BOOK-WORKFLOW-018** Converge Helios on the shared Pages workflow [patch] (2026-08-13) — `116228c031a10d9e5176d7209c54172973001ddd`, `546c199fdd46b8eb8c4176a4250ac261962a45d0`, `578150340157c6da25f4ee2b37d6b4639d787c1a`
- **ATLAS-HERMES-PERMUTE-017** Measure and prune cross-lane NEON overrides [perf] (2026-08-13) — `79d7297`, `d1627cd23179595b751c237a67f86cdeafb01310`
- **ATLAS-CONSUS-TEST-API-001** Make cross-format integration tests consume real Consus APIs [patch] (2026-08-13) — `a5b9cfdde4c789c237652e0d62c42ce8372005f5`, `720233ab6e7fedb82399d28540f903a6b1e9a191`
- **ATLAS-CONSUS-NODEF-FITS-HDF5-NWB-003** Close Consus no-default storage boundaries [patch] (2026-08-13) — `b3ca01c21b2e9bad4c7b7dc23c47083ca79a3307`, `bf46b7cf00ec7a86b51decf31be4eb30b367c397`
- **ATLAS-CONSUS-NODEF-ARROW-PARQUET-002** Close Arrow/Parquet no-default cfg boundaries [patch] (2026-08-13) — `37f835d1b87af426001df25d343ac1e12b86a55b`, `731a3ca394876a7329becee83a197e5d01e49773`
- **ATLAS-LIVE-HEAD-SWEEP-015** Reconcile merged provider defaults [patch] (2026-08-13) — `18550d932902662c1ce196f779ee041bd0c29cd4`, `19c205d4fca964ac4907eaeb0587fe18745efe89`, `beed6dad8f6998b81a4e2918c151989d272e7a19`
- **ATLAS-COEUS-HEPHAESTUS-F64-015** Restore CUDA f64 comparison seam [minor] (2026-08-13) — `b34b50787df636891d281b5011c6a17dd46edcb0`, `c373de1945bb9ce7b9fd804a80415218d975f286`, `aabdec67a0f5baa415c4abb6dded69db41b2f2d6`, `a4063be118978c8ecc4c745a8ef0b004c1beb45b`
- **ATLAS-HELIOS-CHECKLIST-016** Reconcile binary-MLC roadmap and benchmark gate [patch] (2026-08-13) — `f118214e5f3da231b8b48ef8e2ea15450544f1de`, `f7ca5dad16bb7c36781bcefe4c90c21377f06110`, `f108dc9b3cf7cc94212fa574219594eab2a0bc4f`
- **ATLAS-TYCHE-MULTIOUTPUT-017** Generalize sensitivity estimators [minor] (2026-08-13) — `dc96f5ecd6af643e34f2146b9f3dbb49ba85dbae`, `4a6f8cd495c78beaaa6e4081705b33ed0da8be9e`, `2d12dc5e2803a8208877026badfbb24578129da8`, `af30ad23dc468349511dff9d1d34ab9b5ab58334`
- **ATLAS-LETO-LBFGS-023** Replace L-BFGS jagged history with a flat ring [perf] (2026-08-13) — `e4d5dfc7aa81507518c83396091f11b60f1ed96`, `6e4a1627aa739d37c5f40ab1ab9e41948352cc54`, `a722fbc8`
- **ATLAS-LETO-TASK-PARTITIONS-024** Provider-owned disjoint task partitions [minor] (2026-08-13) — `508962df`, `39683975ff02d68abac8546b0bf945f4d70fc870`
- **ATLAS-FOUNDATION-PLANNING-001** Foundation planning completion (aequitas / eunomia / proteus / themis) [chore] (2026-08-12) — `cad222b`
- **ATLAS-FOUNDATION-PLANNING-002** Next-tier planning completion (hyperion / horae / consus / tyche) [chore] (2026-08-12)
- **ATLAS-BOOK-CLOSURE-002** Eight-provider book closure [patch] (2026-08-12) — `7a6744b`, `fdd8bd6`, `a21228a`, `31816dc`
- **ATLAS-CASCADE-ALIGNMENT-001** Consumer alignment for the 0.42/0.5/0.26/0.19 provider cascade [patch] (2026-08-11) — `d9e674f`, `f68045d`, `a68e91f`
- **ATLAS-BOOK-ANCHOR-PARITY-001** Heading-id parity with mdBook v0.5.4 [patch] (2026-08-11)
- **ATLAS-BOOK-LINK-CI-001** All-provider book link CI gate [patch] (2026-08-11)
- **ATLAS-BOOK-LINK-SWEEP-001** All-provider book link sweep [patch] (2026-08-10)
- **ATLAS-TYCHE-PROVIDER-ESTIMATORS-001** Tyche sensitivity estimators and book closure [patch] (2026-08-10)
- **ATLAS-MNEMOSYNE-BOOK-001** Complete Mnemosyne book closure [patch] (2026-08-11) — `c4516df`, `9a143ca`
- **ATLAS-HYPERION-PROVIDER-DOCS-001** Complete Hyperion book closure [patch] (2026-08-11) — `b8a1124`, `9a8b7d8`
- **ATLAS-PROTEUS-PROVIDER-DOCS-001** Complete Proteus book closure [patch] (2026-08-10)
- **ATLAS-HORAE-PROVIDER-DOCS-001** Complete Horae book closure [patch] (2026-08-11) — `03ad868`, `08cf292`
- **ATLAS-AEQUITAS-PROVIDER-DOCS-001** Complete Aequitas book closure (2026-08-11) — `11565d9`, `681042b`
- **ATLAS-PROVIDER-INTEGRATION-AUDIT-001** Audit twenty Atlas providers [patch] (closed 2026-08-16; Tyche (aka Tychee)) — `b72d9f1`, `47863b1`, `47863b12aa0cd4e65cb9556b2c9bbf1353a5ee26`, `d272934`, `182083f1aa95ad30565910e432a878c749d06f03`, `cbfff61e392b77232f99a4a4a64fd69002402dcc`, `2beb4f17c35c88c0eade4bd337f161c0cc2cf48f`
- **ATLAS-HEPHAESTUS-CLOSURE-001** Hephaestus expression-parity closure record (2026-08-11) — `407938b`, `d4d5906`, `df8a896`, `aca9a5a8`
- **ATLAS-EUNOMIA-CLOSURE-001** Eunomia 0.8.0 provider closure record (2026-08-11) — `0c14c2e`, `184ba92`
- **ATLAS-IRIS-CLOSURE-001** Iris IRIS-003 release-readiness record [chore] (2026-08-11) — `ab3eea2`
- **ATLAS-ASCLEPIUS-BOOK-001** Complete Asclepius book closure [patch] (2026-08-11) — `530115a`
- **ATLAS-COEUS-MLM-PROVIDER-001** Coeus multi_label_margin_loss provider delivery [patch] (2026-08-11) — `1ac8118c`, `4491bf19`, `bde7010f`
- **ATLAS-HELIOS-DICOM-ORIENTATION-001** Helios DICOM oriented-grid boundary delivery [patch] (2026-08-11) — `342bbbc83`, `77716bb`, `bde7010f`
- **ATLAS-LETO-HERMES-REDUCED-PRECISION-001** Leto F16/Bf16 Hermes provider delivery [patch] (2026-08-11) — `606e5b5`, `d9e674fc`, `ca93b63c`, `d68095b`
- **ATLAS-APOLLO-SHARED-VALIDATION-001** Apollo shared WGPU transform validation delivery [patch] (2026-08-11) — `b426f2cd`, `0e38d1cc`, `bde7010f`, `eae6b706`
- **ATLAS-APOLLO-CI-INDEPENDENCE-001** Apollo whole-workspace clean-gitlink proof (hermes + hephaestus) [patch] (2026-08-12) — `ae657fc`, `3be20f43`, `03e5e175`, `63d06940`
- **ATLAS-HELIOS-CI-INDEPENDENCE-001** Helios whole-workspace clean-gitlink proof (hermes + hephaestus + leto) [patch] (2026-08-12) — `5c4a8491`, `03e5e175`, `ae657fc`, `e0d867ec`
- **ATLAS-COEUS-DIST-BYTE-IDENTITY-001** Scripted coeus-dist TCP binary byte-identity harness (2026-08-12) — `8369e7a2`, `b02a0f02`, `695507d6`, `4dbb70c2`
- **ATLAS-GAIA-PERMISSIONED-ARENA-001** Gaia Melinoe-branded permissioned arena delivery [patch] (2026-08-11) — `b5e62c5`, `5ea09cbc`, `a5b0fe72`
- **ATLAS-CGROUP-CLOSURES-001** C-group closure sweep (melinoe/moirai/proteus/consus) [chore] (2026-08-11) — `eab19a6`, `c8e8889`, `6d80c33`, `57c4ec4`
- **ATLAS-VERSION-GUARD-SCAN-MATRIX-001** per-commit scan matrix [chore] (2026-08-11) — `681042b`, `11565d9`, `3d6021e`, `30e25f8`
- **ATLAS-VERSION-GUARD-002** Stack-wide first-party coherence subcommand + CI sweep [minor] (2026-08-08) — `43f8aa2`
- **ATLAS-BOARD-HYGIENE-001** Resolve duplicate item IDs in backlog.md [chore] (2026-08-07) — `17c3cc5`
- **ATLAS-TOOLS-STRANDED-001** Land stranded atlas-meta tooling slices [chore] (2026-08-07) — `a92a3c6`, `cbc664d`, `fb62549`, `11a67dd`
- **ATLAS-TAKEOVER-001** Land stranded delivered slices in tyche, hermes, eunomia, CFDrs [chore] (2026-08-06) — `d25311e`, `bde7010`, `69ff96d`, `cf32eab6`
- **ATLAS-THEMIS-MELINOE-ADOPTION-002** Deliver Themis Melinoe branded-collection adoption (2026-08-11) — `47863b1`, `cad222b`, `038457d`
- **ATLAS-THEMIS-MELINOE-ADOPTION-001** Themis/Melinoe source-seam adoption in the three integrators [arch] [minor] (2026-08-10) — `1493eef3`, `234574c`, `a444038d`, `74159afa`
- **ATLAS-KWAVERS-NUMA-FIX-1** Close kwavers `NumaAwareAllocator` single-pair leak + unused `BindToNode`/`Interleaved` policy variants [patch] (2026-08-05) — `36e989054`
- **ATLAS-KWAVERS-NUMA-FIX-1-FOLLOWUP-PRINT-STDERR** Replace `eprintln!` defect-masking in `NumaAwareAllocator::allocate` with `log::warn!` [patch] (2026-08-06) — `155058b5d`, `7a30b0429`, `36e989054`
- **(unnumbered)** AEQUITAS-THERMAL-COEFFICIENTS — Add temperature-dependent acoustic coefficient dimensions [minor] (2026-08-04) — `7a9a21f`
- **ATLAS-KWAVERS-MNEMOSYNE-FIX-1** Complete mnemosyne dep wiring stranded in kwavers `bf3e17861` [patch] (2026-08-04) — `bf3e17861`
- **ATLAS-RITK-MELINOE-DOC-SYNC-1** Sync ritk parallel-prose comments to moirai/melinoe routing [patch] (2026-08-05) — `a03deeae`, `a5e375fe`, `b4cfff62`
- **ATLAS-AEQUITAS-CONSUMERS-005** Close Kwavers ultrafast geometry metric extensions [arch] [major] (2026-08-02) — `8ffb198bc`, `b2c437bab011d99d6403e23b4a373905f7905cde`
- **ATLAS-AEQUITAS-CONSUMERS-006** Close Kwavers beamforming and design metric extensions [arch] [major] (2026-08-06) — `63cd488ec17279be6d4a459f2785784f816b1c14`, `dc8e5b58b9816bf3a57f2bc47750257d65cd3609`, `c3e0ca39da0c928c83125ca27f9689de49b389f4`, `31482cbadaafda9703fc1f00e9d84e35e4398606`
- **ATLAS-AEQUITAS-CONSUMERS-004** Close geometry and scheduling metric extensions [arch] [major] (2026-08-06) — `ce6a4f39`, `57bb47ea`, `98b571e`, `87afe809f`
- **ATLAS-AEQUITAS-CONSUMERS-002** Close CFDrs, Helios, and Kwavers metric audit [patch] — `8e75ee3`, `c91cccc6`
- **ATLAS-AEQUITAS-CONSUMERS-003** Extend therapeutic microbubble metric audit [arch] [major] — `8cc90b2`, `77be364b9`, `2acd72ccd`, `5dad60d69`
- **ATLAS-SUBSTRATE-001** Extend the Hephaestus operation seams to Coeus's call surface [arch] [minor] (2026-08-11) — `d3aa627`, `8d1c6b1`, `f778445`, `a68e91f`
- **ATLAS-SUBSTRATE-002** Collapse Coeus's cloned per-vendor provider impls [arch] [minor] (2026-08-12) — `2f3af87e`, `9167f574`, `3be20f436aa2`, `d7077547`
- **ATLAS-SUBSTRATE-003** Give the Leto/Hephaestus decomposition pair one seam and one oracle [arch] [minor] (2026-08-02) — `31f797f`, `60928c8`, `1fe2bd4`, `7762aa1`
- **ATLAS-SUBSTRATE-004** Consolidate Apollo's per-transform scaffold [arch] (2026-08-02) — `ebb2df7`, `29e7b6d`, `6c7f593`, `aea658d`
- **ATLAS-SUBSTRATE-005** Shared CPU-tier storage vocabulary for Apollo [arch] [minor] (2026-08-02) — `7d212a2`, `b31948d`, `6876b55`, `d0a153f`
- **ATLAS-ARCH-001** One generic ComputeBackend conformance suite [arch] [minor] (2026-08-01) — `acc50ed`, `1e36071`, `53816ebf`, `b08161e`
- **ATLAS-THEMIS-TOPOLOGY-OPTION-1** Model unreported GPU capacities in the type [minor] (2026-08-01) — `e6ec649`, `3ff23b6`, `eccf931`
- **ATLAS-ARCH-010** Define the NaN and infinity contract for accelerator kernels [arch] [minor] (2026-08-01) — `6996f12`
- **ATLAS-ARCH-009** Decide whether hephaestus-metal remains a crate [arch] (2026-08-03) — `b5020e1`
- **ATLAS-GITLINK-TARGET-SSOT-001** Reject ambiguous target-repo selectors [patch] (2026-08-07) — `cbc664d`
- **ATLAS-OVERLAY-SSOT-001** Restrict overlay discovery to canonical repos [patch] (2026-08-07) — `fb62549`
- **ATLAS-HEPH-ADR-NUM-1** Two ADRs both numbered 0045 [patch] (2026-08-03) — `b5020e1`, `010b14d`, `64653b3`, `1febb16`
- **ATLAS-ARCH-002** Instantiate generic tests across every shipped scalar [patch] (2026-08-03) — `cf716c0`
- **ATLAS-ARCH-003** Make leto-ops statistics generic and resolve the split Pearson [minor]
- **ATLAS-ARCH-004** Rehome and genericize the cfd-math Pareto module [patch]
- **ATLAS-ARCH-006** Eliminate junk-drawer modules [patch] (2026-08-03) — `1b4952823`, `be610931`, `d0a153f`, `fc0e1ec`
- **ATLAS-ARCH-007** Reduce manifest files carrying implementation [patch]
- **ATLAS-ARCH-CYCLE-001** Break the CFDrs -> gaia -> CFDrs repository cycle [arch] (2026-07-29) — `df3902b`, `67d5728`
- **ATLAS-CFDRS-PATHDEP-001** CFDrs path deps collide with the worktree overlay [patch] (2026-07-29) — `bf65a41`
- **ATLAS-HEPH-PRODUCT-PARITY-1** Land the stranded product-axis parity commit [patch] (2026-07-30) — `8bc589a`, `196bc84`
- **ATLAS-HEPH-CONFORMANCE-LETO-1** Stale `repos/leto` checkout breaks conformance stack-wide [patch] (2026-07-30) — `f778445`
- **ATLAS-LETO-BRANCH-SPLIT-1** Leto main and sparse-LU diverged under one pin [patch] (2026-07-30) — `054244a`, `116b98d`
- **ATLAS-KWAVERS-ALLOC-TEST-RACE-1** Allocation-count test races the harness [patch] (2026-08-02) — `02eee237a`, `f2fb1ca`
- **ATLAS-COEUS-SWALLOWED-RESULTS-1** coeus-autograd ignores fallible add_assign [patch] (2026-07-30) — `81eeec09`, `80bb2707`
- **ATLAS-COEUS-MAIN-SYNC-1** Integrate coeus origin/main into the stack [arch] [major] (2026-07-30) — `c01a313a`, `81a7992`, `9ac74e13`, `29eb02d`
- **ATLAS-ENV-CC-1** Host gcc is broken, blocking every C dev-dependency [chore] (2026-07-31)
- **ATLAS-WORKTREE-JUNCTION-1** `worktrees/apollo` is a junction onto the main tree [chore] (2026-08-04)
- **ATLAS-ATHENA-ALLOC-1** Zero-allocation solver test fails only on Linux [patch] (2026-08-03) — `cdb5fca`, `34ce3b6`, `346a1df`, `045efe4`
- **ATLAS-MNEMOSYNE-CI-1** mnemosyne CI gate landed; two exclusions to retire [patch] (2026-08-05) — `49b4ad9`
- **ATLAS-MNEMOSYNE-SNMALLOC-1** snmalloc-sys fails g++ 16's new warnings [patch] (2026-08-05)
- **ATLAS-HEPH-DOC-LINKS-1** hephaestus-core fails the rustdoc gate [patch] (2026-07-30) — `d6d893a`, `eb58c86`, `8d1c6b1`
- **ATLAS-PM-TOOLCHAIN-SSOT-1** Three board records for one toolchain fact [patch] (2026-07-30)
- **ATLAS-ENV-TOOLCHAIN-001** RUSTC override breaks the shared cache [chore]
- **ATLAS-GAIA-GITDEP-001** Gaia's committed path dep makes it unconsumable as a git dependency [patch] (2026-07-28) — `1190ace`, `1459c99`, `42ef63af`
- **ATLAS-HELIOS-GENERIC-001** Instantiate the f32-only generic tests across shipped scalars [patch] (2026-07-29) — `f3038b2`, `3fdfa8d`, `cda0e8c`
- **ATLAS-PUB-LOCK-1** Overlay-stripped lockfiles get committed and break `--locked` [patch] (2026-08-13) — `520f248`, `98f8537`, `0992e24`, `a3be57f`
- **ATLAS-PUB-007** Rename `mnemosyne-core`: the stack's publish critical path [patch] (2026-08-03)
- **ATLAS-PUB-004** Pin the three Pages actions to verified digests [patch] (2026-08-01) — `983d773`, `7b1f4a7`, `d6db901`
- **ATLAS-BOOK-001** Author the 21 missing package books [minor] (2026-08-04) — `aa1be92`, `35fe13e`, `54b89f9`, `40d0f7c`
- **ATLAS-NEURO-001** RITK diffusion, tractography, and connectome crates [minor] (2026-08-04)
- **ATLAS-MODALITY-001** Move chromophore extinction spectra to Hyperion [arch] [minor] (2026-08-04)
- **ATLAS-MODALITY-002** Type the deposition spine in Aequitas quantities [arch] (2026-07-31) — `1003c88`, `81a40071c`, `37d50b96f`, `5aef5f551`
- **ATLAS-CONTENTION-001** Transport-output typing blocked behind foundation WIP [patch] (2026-07-31) — `e0918d1f2`
- **ATLAS-OVERLAY-002** Clear pin drift in asclepius, athena, hermes [patch] (2026-07-28) — `fef782cb`, `24ad6ea`, `bbf38400`, `cf69175`
- **ATLAS-OVERLAY-003** Retire committed [patch] blocks from 7 member manifests [patch] (2026-07-30) — `7840331f`, `4caf32b`, `395a1e74a`, `48ed142`
- **ATLAS-GIT-HYGIENE-001** Confirm `repos/leoneuro-rs/` rule is intentional [chore] (2026-07-27) — `fef2c63`
- **ATLAS-CUDA-TREE-003** Close the fused operation-tag tree split [arch] (2026-07-23) — `edcded8d`
- **ATLAS-CUDA-TREE-002** Close the attention kernel tree split [arch] (2026-07-23) — `393d711e`
- **ATLAS-CUDA-TREE-001** Close the convolution backend tree split [arch] (2026-07-23) — `9b5da9c7`
- **ATLAS-CUDA-SAFETY-015** Close elementwise backend count/failure boundary [patch] (2026-07-23) — `f7372408`
- **ATLAS-CUDA-SAFETY-014** Close fused-dispatch launch ABI [patch] [arch] (2026-07-23) — `799e72f6`
- **ATLAS-CUDA-SAFETY-013** Close transposed-convolution launch ABI [patch] [arch] (2026-07-23) — `382b74c7`
- **ATLAS-CUDA-SAFETY-012** Close unfold/fold launch ABI [patch] [arch] (2026-07-23) — `de74d093`
- **ATLAS-CUDA-SAFETY-011** Close attention launch ABI [patch] [arch] (2026-07-23) — `3ace27ec`
- **ATLAS-CUDA-SAFETY-010** Close matmul launch ABI [patch] [arch] (2026-07-23) — `b9876e7e`
- **ATLAS-CUDA-SAFETY-009** Close pool3d launch ABI [patch] [arch] (2026-07-23) — `df331873`
- **ATLAS-CUDA-SAFETY-008** Close pool2d launch ABI [patch] [arch] (2026-07-23) — `45826c05`
- **ATLAS-CUDA-SAFETY-007** Close pool1d launch ABI [patch] [arch] (2026-07-23) — `920b3428`
- **ATLAS-CUDA-SAFETY-006** Close optimizer launch ABI [patch] [arch] (2026-07-23) — `f627ecbc`
- **ATLAS-CUDA-SAFETY-005** Close elementwise launch ABI and tree [patch] [arch] (2026-07-23) — `92bd4c8f`
- **ATLAS-CUDA-SAFETY-004** Close reduction launch ABI [patch] [arch] (2026-07-23) — `dfe23979`
- **ATLAS-CUDA-SAFETY-003** Close shared CUDA layout ABI [major] [arch] (2026-07-23) — `4129d31e`
- **ATLAS-CUDA-SAFETY-002** Close convolution launch ABI narrowing [patch] (2026-07-23) — `1041b20d`
- **ATLAS-CUDA-SAFETY-001** Close convolution launch panic [patch] (2026-07-23) — `7e8e1ee2`
- **ATLAS-BUILD-STRUCTURE-005** Close CUDA operation impl hierarchy [patch] (2026-07-23) — `2fb00ed6`
- **ATLAS-BUILD-STRUCTURE-004** Close CPU operation impl hierarchy [patch] (2026-07-23) — `1a28b64b`
- **ATLAS-BUILD-STRUCTURE-003** Close WGPU operation impl hierarchy [patch] (2026-07-23) — `310f9ffb`
- **ATLAS-BUILD-STRUCTURE-002** Close Coeus-NN attention parity leaf [patch] (2026-07-23) — `006a1c7c`
- **ATLAS-WGPU-CORRECTNESS-001** Close native WGPU missing operation paths [patch] (2026-07-23) — `c8b9a013`
- **ATLAS-HELIOS-BOOK-087** Helios mdbook deterministic figure set + prebook xtask [patch] (2026-07-23)
- **ATLAS-RITK-655** RITK B-spline bounded dense hot-path closure [minor] (2026-07-23)
- **ATLAS-CHECK-FIGURES-CI-1** Wire `prebook check-figures` lint into PR CI [minor] (2026-07-23)
- **ATLAS-PATH-DEP-AUDIT-2** Close 311 ryancinsight audit hits across 21 atlas submodule Cargo.lock files [patch] (2026-07-27) — `0fc64b0e`, `1efc7fcf`, `2686b86`, `f04b1d75`
- **ATLAS-CFDRS-COEQ-BLOCKER-1** Restore CFDrs cargo workspace via coeus-core submodule [patch] (2026-07-26) — `a6dfb2d601`, `baff9ef7`, `7d60724`, `15ee8e594fd497f59fff65d809c2034131e1f0b0`
- **ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1** CFDrs ci.yml sibling-checkout for runner-clean path-dep resolution [minor] (2026-07-26) — `a163ef55`, `7d60724`, `b25b0f0c`, `1a7aa1d6`
- **ATLAS-PARITY-HTML-RETIRE-1** Retire stale `parity_artefacts/INDEX.html` [minor] (2026-07-23)
- **ATLAS-BOOK-CHECK-FIGURES-1** Cross-atlas `prebook check-figures` SSOT lint [minor] (2026-07-23)
- **ATLAS-EUNOMIA-044** Wrapper integer checked/saturating ops correctness [patch] (2026-07-23)
- **ATLAS-CFDRS-PERF-045** CFDRS-PERF-SLOW-001 closure: poiseuille Picard perf [patch] (2026-07-23) — `22ddc27df272c749d8c4e5c4b171113bfa1c272a`
- **ATLAS-CFDRS-BOOK-MDBOOK-DUPLICATES-1** Pre-existing duplicate-file references in CFDrs mdbook SUMMARY [patch]
- **ATLAS-CFDRS-BOOK-DETERMINISTIC-FIGURES-1** CFDrs mdbook deterministic figure set + prebook xtask [patch]
- **ATLAS-PERF-043** Preserve provider-native sparse-LU ownership [minor] — `b24fc860864abad84af3118aa2bb27c32bb81265`, `74efcceff0c737d09cc3251f24ed37bbb11de232`
- **ATLAS-INTEGRATION-042** Close provider delivery graph [patch] (2026-07-23) — `f604123dd`, `c982fe0`, `806c6e7`, `ce3ef7a6`
- **ATLAS-INTEGRATION-041** Align the Leto consumer graph [patch] (2026-07-22) — `c00fa04a`, `5f57557a`, `eb93d124`, `8c6ab72d`
- **ATLAS-ROADMAP-040** P2 domain-provider consolidation [arch] (2026-07-22) — `7b4561b`, `105a093`, `5fc6f0419`, `9c8ce32e`
- **ATLAS-INTEGRATION-038** Iris visualization promotion [arch] [minor] — `a8ea96f7`, `a36e65df`, `a41774fa`
- **ATLAS-INTEGRATION-039** Iris CFDrs consolidation [arch] [major] — `c7454ef3`, `394c9977`
- **ATLAS-INTEGRATION-037** Asclepius P1 promotion [arch] [minor] — `eb65eaf`, `794f8c3`, `33bba34`, `4ce96b1`
- **ATLAS-INTEGRATION-035** Proteus and Tyche promotion ADRs [arch] [minor] — `f043d22`, `beb2713`, `feed3bc`, `edf99e4`
- **ATLAS-INTEGRATION-036** Coeus hephaestus 0.18.0 bump [patch] — `56fa49a`, `c290f3e`, `4158b8e`, `02d74fd`
- **ATLAS-INTEGRATION-034** Benchmark gate repair [arch] [patch] — `2a22319`, `4ce96b1`, `198f2b8c`, `9ad18523d`
- **ATLAS-INTEGRATION-033** Harmonia Phase 0 [arch] [minor] — `cf6ce3e9175bbc3eebc51918d137492b2da5edba`
- **ATLAS-INTEGRATION-032** Documentation and checkout hygiene [patch] — `96fb26d`, `92af1a2`
- **ATLAS-INTEGRATION-031** Horae/Athena extraction [arch] [minor] (2026-08-06) — `e57f798`, `7d647e7`
- **ATLAS-INTEGRATION-030** Aequitas consumer closure [patch] — `0fb31d800`, `49c116ffb7466f9163b7762f03bc74725d8026c3`, `7c37f7f30dc286e8853bdf41da7652abeadebe23`, `156531eeb`
- **ATLAS-INTEGRATION-028** Hephaestus PM convergence [patch] — `cdfcd0cb38de03d28107fc231042eaf55e078e3a`, `2c1ee62`
- **ATLAS-INTEGRATION-027** Provider-default convergence [patch] — `6f9b81f`, `bb03244f05a9c43c318d103225c3ccad07e9fad9`
- **ATLAS-INTEGRATION-026** Eunomia runtime-half retirement [patch] — `df77dfd`, `594d57a`, `d207cf6`
- **ATLAS-INTEGRATION-029** Hephaestus provider-first CFDrs 2D GPU Laplacian [minor]
- **ATLAS-INTEGRATION-025** Eunomia precision graph [major] — `c196db5`, `c9bbdf8`, `7afcbd0`, `3f5f51f`
- **ATLAS-INTEGRATION-024** Helios provider lock convergence [patch] — `79b09e9`
- **ATLAS-INTEGRATION-023** Coeus NN provider benchmark closure [patch] — `bb97cc6`, `a365b25`
- **ATLAS-INTEGRATION-022** Eunomia sub-byte graph [patch] — `49dc115`, `f0b4d8e`, `ed7d76e`
- **ATLAS-INTEGRATION-019** Hephaestus legacy-math residue [patch] — `cec0e33`, `93bc38e`
- **ATLAS-INTEGRATION-020** Apollo Hephaestus lock convergence [patch] — `cec0e33`, `a31b8f8`
- **ATLAS-INTEGRATION-021** Coeus tensor legacy benchmark removal [patch] — `4459d09`, `093f31f`
- **ATLAS-INTEGRATION-018** RITK Apollo alignment [patch] — `a41e03b9`, `aededa6b`
- **ATLAS-INTEGRATION-015** Merged default refresh [patch] — `a833b7fe`, `a2e4f390`, `972fb53e`, `3ac0d203`
- **ATLAS-INTEGRATION-012** Apollo policy-wrapper removal [major] — `e2f905a`, `0b5d11c`
- **ATLAS-INTEGRATION-013** Apollo Winograd re-export removal [patch] — `c874281`, `e2f905a`
- **ATLAS-INTEGRATION-014** Hephaestus scan-limit theorem [patch] — `93bc38e`, `3b68228`
- **ATLAS-INTEGRATION-016** Apollo provider-lock refresh [patch] — `93bc38e`, `a2e4f390`, `6a0e297`, `8a51b2a7`
- **ATLAS-INTEGRATION-017** Apollo Leto merge pin [patch] — `3ac0d203`, `6a0e297`, `6dcb97c`
- **ATLAS-INTEGRATION-011** Hephaestus CUDA initialization closure [patch] — `3b68228`, `d0eafc8`
- **ATLAS-INTEGRATION-010** Hephaestus tiled scan provider closure [minor] — `d0eafc8`, `df33d4d`
- **ATLAS-INTEGRATION-007** RITK Apollo checkout pin [patch] — `ffda3ec`, `157467e`
- **ATLAS-INTEGRATION-008** Apollo dispatch verification tree [arch] — `0b5d11c`, `56ad179`
- **ATLAS-INTEGRATION-009** Kwavers hosted closure [patch] — `9eabc4e2`, `e84bb571e`, `7c7d60f`
- **ATLAS-INTEGRATION-006** Refresh provider heads [arch] — `0b5d11c`, `df33d4d`, `9eabc4e2`, `6a0e297`
- **ATLAS-INTEGRATION-005** RITK lock-integrity pin [patch] — `0dd71e52`
- **ATLAS-INTEGRATION-003** provider-neutral GPU pin reconciliation [patch] — `29ff2ff`, `7d4c9edf`
- **ATLAS-INTEGRATION-004** CFDrs executable-example pin [patch] — `a13f7f51`
- **ATLAS-INTEGRATION-001** default-main reconciliation [patch] — `093f31f`, `9e48102`
- **ATLAS-INTEGRATION-002** merged-provider pin reconciliation [patch] — `f26369eb`, `04e496b7`, `ec7cb832`, `e3380b6`
- **ATLAS-MNEMOSYNE-017** Maximum-small deallocation audit [patch] — `0012c4fad0c44c0a40ec4d36de68e7138ae218d8`, `52cd5ee`
- **ATLAS-MOIRAI-016** Cancellation-safe async wait queues [patch]
- **ATLAS-RITK-654** RITK native migration reconciliation [patch] — `17b84bdc18c2395d6329f3435ed3d860d1c72e00`
- **ATLAS-APOLLO-015** RustFFT/WGPU provider promotion [major] — `6e99a567c118f6bf5790f80346475b44db2c7555`, `17b84bdc`
- **ATLAS-WGPU-030** Provider ABI migration [arch] (2026-07-13) — `01e7de7`, `4a9d2a3`, `090611d`, `8651dfc`
- **ATLAS-APOLLO-014** Apollo release graph [arch] (2026-07-09) — `a4742bb`, `eb0d941`, `51c530f`, `b2f3732`
- **ATLAS-BOOK-002** Domain books teach the field; evict process content [patch] (2026-08-06) — `a5a86d64`, `9ebf5b4e9`
- **ATLAS-MNEMOSYNE-001** Allocator observability and adversarial-stress audit [patch] (2026-07-24)
- **ATLAS-LETO-OPS-AMD-ORDERING-001** Implement AMD fill-reducing ordering for sparse LU [patch] (2026-08-07) — `db9a63c`, `912b991`, `d1c3a1c`
- **ATLAS-STACK-DEPS-001** Stale dependency version resolution across hermes, tyche, melinoe [patch] (2026-07-24) — `2739a75`, `95c1fa7`, `40278ac`, `babdd42`
- **ATLAS-AEQUITAS-001** Wireless gitlink advance to origin/main `19fc3846` [minor] (2026-07-24) — `19fc3846`, `07e2252`, `6dc68c4`, `19fc384`
- **ATLAS-COEUS-DIRTY-RECONCILE-1** Commit post-`7d60724` coeus dirty state: workspace-graph migration + CUDA driver compat + lock disambiguation [patch] (2026-07-24) — `7d60724`, `c711dcb4`, `a6dfb2d`, `15ee8e594fd497f59fff65d809c2034131e1f0b0`
- **ATLAS-COEUS-OPS-FALLIBLE-API-1** Document `coeus_ops` fallibility boundary migration (`*_assign` + `elementwise_unary` Result return + downstream test adaptations) [patch] [arch] (2026-07-24) — `f8328027`, `a6dfb2d6`, `53311c03`, `6b54e64a`
- **ATLAS-LETO-GITLINK-ADVANCE-1** Advance `repos/leto` parent submodule pointer to c6ced81 [minor] (2026-07-24) — `c6ced81`, `c6ced81e`, `687b67079c4e122264c17fd2eb3fd850d876a39f`, `c6ced81e6d5a9f439bd24a5150964e7bd2cb595d`
- **ATLAS-MOIRAI-GITLINK-ADVANCE-1** Advance `repos/moirai` parent submodule pointer to f74aa480 [patch] (2026-07-24) — `f74aa480`, `b613dc3d`, `b613dc3db6504340c4b407cbfbe5cab36bd23f44`, `f74aa480217c51e0254461d02b47b2a32e67ddce`
- **ATLAS-APOLLO-GITLINK-ADVANCE-1** Advance `repos/apollo` parent submodule pointer to 82e67c8 [patch] (2026-07-24) — `82e67c8`, `82e67c8f`, `8fb3e4ad`, `8fb3e4ad2c7903df14f7c1f944761970b55b9705`
- **ATLAS-HEPHAESTUS-GITLINK-ADVANCE-1** Advance `repos/hephaestus` parent submodule pointer + add CUDA build script [minor] [arch] (2026-07-24) — `e7887a5d110c1b8b71456564b76bafcb3d68798f`, `116373dd207d93660f53687f6a4817f7ee1b80ff`
- **ATLAS-GITLINK-COHERENCE-DEFECT-1-AUDIT-TOOL-1** Mechanize the gitlink-coherence audit as a coordinator-owned `tools/gitlink-coherence/` sister tool [patch] [arch] (2026-07-24) — `2c14b94f`, `c2227aa`, `47e73d1e`, `9ae06c0`
- **ATLAS-TOOLCHAIN-ALIGN-001** Align all 14 clean repos to Rust 1.97.0 for shared target compat [patch] (2026-07-24)
- **ATLAS-PERF-OPT-001** Hot-path performance and memory efficiency optimization [patch] (2026-07-24) — `777b11c`, `b9393fc`, `035445f`, `7164f26`
- **ATLAS-TOOLS-TEMPLATE-EXTRACT-1** Extract shared `tools/_template/` package module for coordinator-owned tool Cargo lints/profiles/deps after 3rd occurrence [patch] [arch] — `e260055`
- **ATLAS-COEUS-SOURCES-001** Convert coeus mainline back to git+version sources [patch] (2026-08-05) — `5602093b`
- **(unnumbered)** ATLAS-KWAVERS-SPECIAL-FUNCTIONS-SSOT — Consolidate kwavers special functions into leto-ops [patch] (2026-07-25) — `ddd9cca`, `0a31706`, `d87e107`
- **ATLAS-GMRES-FORK-DEFECTS-001** Port the leto-ops GMRES corrections to the CFDrs and kwavers forks [patch] (2026-08-03) — `dcc5d54`
- **ATLAS-MATH-SSOT-CONSOLIDATION-1** Cross-repo math SSOT consolidation audit [patch] (2026-08-05) — `a19a5d977`, `e4e9966b6`, `6d18a547`, `6484ad9e`
- **ATLAS-ATHENA-KRYLOV-CAPABILITY-001** Close Athena's capability gap (ADR 0033 stage A) [minor] (2026-07-27) — `e965a95`
- **ATLAS-ATHENA-ACCEL-BACKEND-001** Replace athena-wgpu with one Hephaestus-backed backend (ADR 0034) [major] [arch] (2026-07-27) — `6ab822c`, `eefa8ba`, `e1f2800`, `47ca84a`
- **(unnumbered)** ATLAS-KWAVERS-PEER-WIP-COMPILE-FIX — Fix compilation errors in kwavers peer WIP [patch]
- **ATLAS-OVERLAY-COHERENCE-001** The stack overlay resolves worktree copies, not the authoritative repos [major] (2026-07-28) — `e1f2800`, `d89ccd9`, `ad941c0`
- **ATLAS-VECTOR-SEAM-PREPARED-CONTRACT-001** Reconcile lending vs retained prepared reductions [major] [arch] (2026-07-28) — `e1f2800`, `d899d88`, `673a7bd`, `7897c13`
- **ATLAS-HEPHAESTUS-SPARSE-SEAM-001** Device-neutral sparse operator seam [major] [arch] — `eefa8ba`
- **ATLAS-GITLINK-TOOL-001** Rescue gitlink-coherence from the harness lane [patch] (2026-07-29) — `f8305ac`
- **ATLAS-TOOLCHAIN-COHERENCE-001** One compiler identity across the shared cache [patch] (2026-07-31) — `2d8144b78`, `a091db2`, `f0c2869`, `9be1b9d`
- **ATLAS-CFDMATH-MATRIX-FREE-OPERATOR-001** Restore the matrix-free operator [patch] (2026-08-03) — `6d18a547`
- **ATLAS-CFDMATH-CLIPPY-FINDINGS-001** Discharge the clippy backlog [patch] (2026-08-03) — `40ef080c`
- **ATLAS-DMRI-MGH-FRAMES-002** MGH silently discards frames past the first [patch] — `8a79da6d`
- **ATLAS-DMRI-SCHEME-003** Typed gradient scheme and its codecs [minor] (2026-08-05)
- **ATLAS-APOLLO-REALSH-005** Real symmetric SH basis over scattered directions [minor] (2026-08-13) — `bf06987`, `db21866`, `112d378`, `33a40bcee4532c9c1a03fee7cef2d852b3419090`
- **ATLAS-LETO-NNLS-007** Non-negative constrained solve [minor] (2026-08-03)
- **ATLAS-RITK-DIFFUSION-010** ritk-diffusion crate, tensor model first [minor] (2026-08-05)
- **ATLAS-RITK-TRACTOGRAPHY-011** ritk-tractography crate [minor] (2026-08-05)
- **ATLAS-RITK-CONNECTOME-012** ritk-connectome crate [minor] (2026-08-05)
- **ATLAS-MIGRATION-PATHDEP-001** Migrate kwavers, CFDrs, helios, ritk to local path deps [patch] (2026-08-03) — `b2ee610`, `c7c3678`

- **ATLAS-BOARD-COMPACT-PATCH-2026-08-21** Preserve prior archive entries in atlas-board-compact.py [patch] (2026-08-21)

- **ATLAS-R6A-FILELIST-001** Per-submodule r6a commit file-list hygiene [patch] (2026-08-21) — `96ccc83`, `b7bb4bc5`, `5414f80`, `ec4e147b`


- **ATLAS-OVERLAY-LOCK-GUARD-2026-08-23** the overlay strips lockfiles and nothing local catches it [major] (2026-08-24) — `9effe25a7`, `5406691fe`, `dabc779d9`, `e3d7eaf29`
- **ATLAS-KWAVERS-PIN-SWEEP-2026-08-22** advance Kwavers onto the merged stack [patch] (2026-08-23) — `5adc2d16`, `2d6f08ab`, `befb8e5`, `5108ed0082fc`
- **ATLAS-KWAVERS-STUBORACLE-2026-08-22** Real energy/reciprocity oracles + existence-only burn-down [patch] (2026-08-24) — `377a98c8`, `352b4dc7b4c9d2959ae53cb57eba1796c6ca51b8`, `377a98c86`, `d13648b9`
- **ATLAS-KWAVERS-IGNOREDORACLE-2026-08-22** Re-homed the 46 ignored oracles per group [minor] (2026-08-24) — `377a98c8`, `443421028fa86cbeab4cf6632ee9b22902534384`, `377a98c86`, `d13648b9`
- **ATLAS-KWAVERS-QUEUE-CLOSURE-2026-08-24** merged-default advance held on the ratchet re-run [patch] (2026-08-24) — `f910f70b`, `f97a3a0b0`, `c7521f73`, `f05c3ca5`
- **ATLAS-KWAVERS-DENYDOCS-2026-08-22** Missing-docs floor on the three smallest crates [minor] (2026-08-24) — `aa5ab2bc9`, `489554d3b`, `67b4099cd`, `377a98c86`
- **ATLAS-GPU-ACQUISITION-2026-08-21** Coeus GPU suite restored, Hephaestus diagnostics [patch] (2026-08-21) — `2d6f08ab`, `655091d`
- **ATLAS-HEPHAESTUS-BOOK-REGROUND-2026-08-21** rebase the stale book-reground PR [patch] (2026-08-24) — `7e09efa9`, `7b6da5a`, `42e2787`, `8728cf3d`
- **ATLAS-CFDRS-VALIDATION-TRACING-2026-08-21** Migrate println! to tracing [patch] (2026-08-23) — `aa54f5cd`, `aa54f5cdcdc4e406df0c60ea6c3cb507e968fc97`, `69df44da`, `69df44dab792ff13f2c829a40fca9321a28e5faa`
- **ATLAS-CFDRS-CFD2D-TURBULENCE-TRACING-2026-08-21** Migrate turbulence validation println! to tracing [patch] (2026-08-23) — `aa54f5cd`, `66fb7566`, `66fb7566102e110a5ea651a467d4e4abd59723a5`, `c5f9fa2c`
- **ATLAS-HOSTED-POSTMERGE-CONSUS-2026-08-21** Verify Consus book-gate merge [patch] (2026-08-23) — `39da4782780c032f587d406f9e32cd62d62f1557`, `5fc1443ecee71d90e5f80dd7df419636f1dda1c8`, `5fc1443e`, `ebc4979`
- **ATLAS-KWAVERS-ARCH-GATE-2026-08-23** Repair the repo-wide architecture gate [major] (2026-08-23) — `d1281f990`, `ca5c9c93`, `568132cf7`, `d13648b9`
- **ATLAS-HORAE-ORDER-ORACLE-2026-08-20** Verify tableau convergence `verification` `patch` (2026-08-20) — `a05dbeb`, `5df51ad`, `0f7d580`, `0f7d58014ef9200e1a83febb13f7fc43a08edee3`
- **ATLAS-HORAE-STAGE-TIME-ORACLE-2026-08-21** Verify non-autonomous tableau stages `verification` `patch` (2026-08-21) — `abe42e5d`, `9d783479`
- **ATLAS-HYPERION-CHROMOPHORE-EVIDENCE-HARDENING-2026-08-20** Clarify source oracle [patch] (2026-08-20) — `4df62f6`, `4df62f63eac2683de2983674a4555a32cfc6b9d5`, `87a17439cb40aef965941480a0b07dee7d3a3c67`, `91df53e9b0c95a52040f9a8dca2324f05ac168a0`
- **ATLAS-LETO-STACK-STORAGE-ORACLE-2026-08-20** Assert stack construction [patch] (2026-08-20) — `c1c8ab2`, `b682cd8`, `e07ee64`, `e07ee6417372b368a30e5991f9fbe765ec2a41ef`
- **ATLAS-IRIS-NAMED-MAP-2026-08-20** Prove the complete Iris map set [patch] (2026-08-20) — `0d18109`, `9672fc0`, `0d18109d4975f4220068bc631c433958bcaa4ed6`, `8700418ab91781523d5ed848db93271d24382ea7`
- **ATLAS-KWAVERS-STALE-TREE-107** reconcile the kwavers stale checkout and stranded WIP [patch] (2026-08-23) (2026-08-23) — `145e8aaf8`, `ca5c9c932`, `c899c429f`, `377a98c86`


- **ATLAS-SEMVER-GATE-RELEASE-JOB-UNREACHABLE-2026-09-02** The shared gate's release job never had an event to fire on [patch] (2026-09-02) — `378081ec6`
- **ATLAS-SCRIPTS-TESTS-BASELINE-RED-2026-09-01** CI gates one of 35 scripts/tests files, under the wrong runner [patch] (2026-09-02) — `2936780a`, `dee3675f`, `65f7a718`, `4e5eb28d`
- **ATLAS-SUBPROCESS-UTF8-DECODING-2026-09-01** Decode subprocess output as UTF-8 in every atlas script [patch] (2026-09-01)
- **ATLAS-FIRST-PARTY-LOCK-SWEEP-2026-09-01** Mechanize the consumer lock advance after a provider merge [minor] (2026-09-01) — `a1e140f5`, `a7055d3f`, `b7ddd66a`, `d8188121`
- **ATLAS-ADR-INDEX-GUARD-2026-09-01** One ADR index generator behind a shared guard [minor] (2026-09-02) — `49cba25c`, `f1a37436`, `a097e4e1`
- **ATLAS-CONFORMANCE-PARALLEL-SCAN-2026-08-31** Bound fleet scan latency [patch] (2026-09-01)
- **ATLAS-VERSION-GUARD-CWD-2026-09-02** version-guard red on main since 2026-08-25: tool cargo runs resolved the root's host-qualified pin [patch] (2026-09-02) — `7699c0f9`, `45b2db92`, `0d688b44`, `4a1b735d`
- **ATLAS-RED-WORKFLOW-COLLECTOR-2026-09-02** Surface failing default-branch workflows at orientation [patch] (2026-09-02) — `32fc0244b`, `db825504`, `f4c096319`
- **ATLAS-GITLINK-COHERENCE-GATE-2026-08-29** Wire the gitlink auditor that already existed [patch] (2026-09-01) — `a8fc5d431`, `03d80d33`, `eac82038`
- **ATLAS-APOLLO-COMPOSITE-RADIX-WRONG-ANSWERS-2026-08-28** Published transforms return silent wrong answers at specific lengths [major] (2026-08-29) — `03d80d33`
- **ATLAS-LETO-PRECISION-ANOMALY-SWEEP-2026-08-31** Clean pass: leto-ops shows no wrong-sign precision ratio [patch] (2026-08-31)
- **ATLAS-APOLLO-BENCH-QUICK-DIRT-2026-08-27** Superseded workflow dirt cleared [patch] (2026-08-27)
- **ATLAS-PROVIDER-HEAD-ADVANCE-2026-08-26** [integration][perf] (2026-08-26) — `ff8f95eb`, `c0cb8f7d`, `98486ebd`, `b9ace296`
- **ATLAS-LETO-HEPHAESTUS-CONSUMER-REPINS-2026-08-26** [integration][perf] (2026-08-26) — `98486ebd27266068391c7101fff5b074a409877b`, `b9ace296881b61bb412f6827463d7fe11f08f603`
- **ATLAS-EXTERNAL-REFERENCE-VALUE-2026-08-25** External references are earning their keep [patch] (2026-08-25)
- **ATLAS-STASH-BACKLOG-2026-08-25** 33 stashes across ten repositories, archived [patch] (2026-08-25)
- **ATLAS-MNEMOSYNE-DOCS-2026-08-25** Correct Page field and book chapters [patch] (2026-08-25) — `5fc0759`, `5e895adeb907c51ff887c0c4c32ca74203478cdd`, `5e895ad`, `aeacb924d`
- **ATLAS-CFDRS-MDBOOK-DEAD-LINKS-2026-08-24** strict-mode gate exposed two real broken links [patch] (2026-08-24) — `3898b96201fbc5ee2958ff4a217786a84b3fba14`, `cc66f836`, `170f0095`, `3898b962`
- **ATLAS-KWAVERS-DEFECTS-2026-08-22** three defects the k-Wave oracle found [major] (2026-08-22)
- **ATLAS-KWAVERS-GPUMOCK-2026-08-21** Simulated elastic-SWE GPU surface deleted [major] (2026-08-24) — `377a98c8`, `17a855d85e4198b39fc45426abdd0576aa2d3d56`, `377a98c86`, `49d80a4`
- **ATLAS-KWAVERS-KWAVE-ORACLE-2026-08-21** k-Wave parity made reproducible [major][arch] (2026-08-21)
- **ATLAS-RITK-HEALTH-2026-08-21** RITK verified; GPU smoother unreachable [patch] (2026-08-21)
- **ATLAS-KWAVERS-VIS-WGPU-2026-08-21** Remove analysis-owned WGPU visualization runtime [major][arch] (2026-08-25) — `41f1c8047`, `2b9328a12`, `871341d62`, `c8966a986`
- **ATLAS-KWAVERS-CI-MATRIX-TIMEOUT-2026-08-25** Eliminate matrix and validation compile duplication [patch] (2026-08-25) — `84ba553ef`
- **ATLAS-KWAVERS-GPU-CLIPPY-RATCHET-2026-08-25** Clear the kwavers-gpu pre-existing clippy findings (the residual's second half) [patch] (2026-08-26) — `f11d4b99c`, `6abb06180`, `17aca60ceafc0b74b8237d297ffecccde2b6ff90`, `d13ab618f`
- **ATLAS-KWAVERS-ANALYSIS-CLIPPY-RATCHET-2026-08-25** Clippy ratchet item (merged as PR #639 at f11d4b99c; gitlink advanced in 59c5f294e) (2026-08-25) — `f11d4b99c`, `59c5f294e`, `80d120202`
- **ATLAS-LETO-BOOK-2026-08-20** complete the missing Leto domain book [minor] (2026-08-24) — `c1c8ab234559a9f58a34d65c32f6096ee69fc012`, `b500baf1af4223f0a995821b6067622ed6caa535`, `b500baf`, `7d6ac26ff`
- **ATLAS-GMRES-SSOT-001** Consolidate four GMRES implementations onto one recurrence [major] [arch] (2026-08-25) — `dcc5d54`
- **ATLAS-GMRES-FORK-CONVERGE-001** Stages B-D: migrate consumers, delete the Leto family [major] [arch] (2026-08-25) — `6d18a547`
- **ATLAS-LETO-OWNED-LU-001** cfd-math consumes an unlanded Leto LU surface [major] (2026-08-25) — `5ebbf1f8`, `63e49604`, `58f6caab`
- **ATLAS-NSFVM-SOR-CONVERGENCE-001** Micro-geometry SIMPLEC continuity stagnation [major] (2026-08-25) — `5ebbf1f8`
- **ATLAS-OUTPUT-RETENTION-001** Retention budget for the output root [pm-hygiene] [patch] (2026-09-01) — `687e303e0`
