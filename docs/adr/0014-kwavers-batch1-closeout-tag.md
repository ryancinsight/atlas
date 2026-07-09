# ADR 0014 — `kwavers` Batch #1 closeout-tag ceremony (`kwavers/atlas-migration-push/batch1` + KW-CV-001 watchpoint retirement)

- Status: **Proposed** — Achievement of the closeout-tag ceremony depends on the kwavers peer stream emitting the 3 inner commits (items `a` + `b` + closeout-style commit) referenced in §Sequencing. The Status flips to `Accepted` once (i) the 3 inner commits land on the kwavers peer stream, AND (ii) the atlas-meta pointer-advance chore commit (item `c`) has retired the KW-CV-001 watchpoint by removing it from `atlas/backlog.md` §In-flight claims per the §Sequencing withdrawal block.
- Date: 2026-07-09.
- Drivers: KW-CV-001 watchpoint (per `atlas/backlog.md` §In-flight claims `repos/kwavers` row: `git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l` returns 0 at the kwavers peer inner HEAD `949e5a39`, blocking atlas-meta Batch #1 status-flip per `atlas/docs/coordination/concurrent_agents.md` disjoint-scope rule); 1,315-file mechanical working-tree drift on `repos/kwavers` per `atlas/backlog.md` §Atlas-root working-tree dirty triage `kwavers` row; the `is_standard_layout` vs `is_c_contiguous` predicate divergence in `crates/kwavers-solver/src/forward/elastic/swe/stress/divergence.rs` per ADR 0013 §Failure modes / risks.
- Anchors: `atlas/docs/adr/0009-batch1-rayon-to-moirai-cte.md` (Batch #1 ancestor closure-gate logic, slice-side); `atlas/docs/adr/0010-cfdrs-atlas-pointer-advance.md` (Per-batch name pattern + tag convention — the SSOT reservation `kwavers/atlas-migration-push/batch1`); `atlas/docs/adr/0011-atlas-root-working-tree-hygiene-ritual.md` (disjoint-scope rule §Decision §Leg 2 — atlas-meta touches ONLY `atlas/**` files; the chore implementation commits live on the kwavers peer stream); `atlas/docs/adr/0012-ritk-burn-trait-rebind.md` (atomic-boundary discipline §Decision §1 — strict additive OR strict subtractive per sub-batch, joint alignment with the helper SSOT `crates/kwavers-solver/src/safety/mod.rs:84-130`); `atlas/docs/adr/0013-kwavers-batch1-source-side-closure.md` (immediate predecessor — captures the slice 1-9 source-side closure mark that ADR 0014 elevates to full closure).
- Supersedes: the `slice 9 partial-closure-mark 2026-07-09` limbo state in `atlas/backlog.md` §In-flight claims (already SUPERSEDED 2026-07-09 by ADR 0013 §Supersedes field, but the post-ADR-0013 limbo persists while the kwavers peer stream's closeout-style commit has not landed); the per-slice partial-closure marks recorded by the prior ATLAS-META chore commits (`4f344f8` through `91541b1b`) are secondarily superseded once item (c)'s pointer advance lands the kwavers peer stream closeout commit.

- Index: docs/adr/INDEX.md#ADR-0014

## Context

### Subject of ceremony

The kwavers Batch #1 source-side migration is recorded as `slice-by-slice partial closure` by ADR 0013 (Accepted 2026-07-09). The status flip from `partial closure` to `full closure` requires the `kwavers/atlas-migration-push/batch1` closeout-tag ceremony per ADR 0010 §Per-batch name pattern. Atlas-meta's hands are tied by the KW-CV-001 watchpoint per `atlas/backlog.md` §In-flight claims `repos/kwavers` row: the watchpoint fires whenever the kwavers peer stream emits a commit whose subject matches the regex `closeout|final|completion|close-batch` (case-insensitive substring match on the inner commit's subject line). Until that watchpoint fires, atlas-meta DOES NOT advance the `repos/kwavers` parent-tree gitlink past the slice 9 inner HEAD `949e5a39` — the disjoint-scope rule (ADR 0011 §Leg 2) prevents atlas-meta from doing source-side retracts.

This ADR adopts the doctrine for the 3-item closeout ceremony. The 3 items are owned by disjoint scopes:

- **Item (a) — kwavers peer stream commit**: flushes the 1,315-file mechanical working-tree drift on `repos/kwavers` (CRLF/whitespace/trailing-newline artefacts from prior codex-session turnover). Recorded in `atlas/backlog.md` §Atlas-root working-tree dirty triage `kwavers` row.
- **Item (b) — kwavers peer stream commit**: unifies the `is_standard_layout()` vs `is_c_contiguous()` predicate surface in `crates/kwavers-solver/src/forward/elastic/swe/stress/divergence.rs` (slice 7's Pass 1a/1b/2 mut outs). The unification eliminates the category-mismatch documented in ADR 0013 §Failure modes / risks as `slice 7 `is_c_contiguous` vs slice 6b/8/9 `is_standard_layout` predicate divergence`. The unification brings slice 7 into alignment with slices 6b / 8 / 9 (all three use the verbose-form `is_standard_layout` predicate) AND aligns the divergence.rs site with the helper SSOT surface (`crates/kwavers-solver/src/safety/mod.rs:84-130`, which uses `is_standard_layout` as the canonical predicate).
- **Item (c) — atlas-meta chore commit**: advances `repos/kwavers` parent-tree gitlink from inner HEAD `949e5a39` (slice 9) to the kwavers peer stream's emitted closeout-style commit SHA. The atlas-meta chore commit body MUST withdraw the KW-CV-001 watchpoint from `atlas/backlog.md` §In-flight claims (delete the row OR mark `RETIRED` per §Sequencing withdrawal block). The atlas-meta chore commit is conditional on items (a) + (b) having landed on the kwavers peer stream.

### KW-CV-001 watchpoint retirement trigger

Per the watchpoint rule: the inner kwavers peer commit must match the regex `closeout|final|completion|close-batch` (case-insensitive substring on the subject line) for the watchpoint to fire. The kwavers peer stream's commit naming convention per §Sequencing names item (kwavers closeout) as `chore(kwavers): Close Batch #1 atlas-migration-push/batch1 per ADR 0014` — the substring `close` matches the regex `closeout|close-batch`. The detector runs:

```bash
git -C /d/atlas/repos/kwavers log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l
```

Expected: returns 1 (or more) after the closeout-style commit lands. Pre-chore: returns 0 (the historical "stuck ACTIVE" state).

### Bundled 3-item chore decomposition

Per `atlas/docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §atomic-boundary discipline §1 (strict additive OR strict subtractive per sub-batch): each item is its own atomic commit. The 3-item decomposition as `1 + 1 + 1` (one commit per item) is preferred over splitting item (b) further into 3 per-Pass commits because the predicate unification's joint alignment with the helper SSOT surface `crates/kwavers-solver/src/safety/mod.rs:84-130` requires all 3 sites in divergence.rs to be re-migrated together (splitting them would create a transient state where slice 7 has 1-of-3 sites using `is_standard_layout` + 2-of-3 sites using `is_c_contiguous`, which violates atomic-boundary discipline §1's joint-alignment rule).

## Decision

This ADR formally adopts the 3-item closeout-tag ceremony doctrine to elevate the kwavers Batch #1 source-side migration from its ADR 0013 limbo state to full verifiable closure. The implementation is stringently decomposed across two disjoint scopes per ADR 0011: the kwavers peer stream shall sequentially emit a 1,315-file mechanical triage flush commit (item `a`), an atomic slice 7 `is_standard_layout` predicate unification eliminating documented category-mismatches (item `b`), and the `kwavers/atlas-migration-push/batch1` annotated closeout tag. Upon detection of this specific closeout signature from the peer stream, atlas-meta is authorized to unconditionally advance the submodule pointer and fully retire the KW-CV-001 watchpoint (item `c`), permanently closing the Batch #1 migration ledger.

The atomic-boundary discipline (ADR 0012 §Decision §1 + ADR 0011 §Decision §Leg 2 disjoint-scope) governs the choreography: each of the 3 items is one atomic commit; atlas-meta commits execute only on atlas-meta-side files (`D:/atlas/docs/adr/**` + `D:/atlas/backlog.md` + `D:/atlas/checklist.md` + `D:/atlas/gap_audit.md` + `D:/atlas/.gitmodules` parent-side gitlink); the kwavers peer stream commits execute only on `D:/atlas/repos/kwavers/**` files.

The Status field flips from `Proposed` to `Accepted` once item (a) + item (b) + the closeout-style commit have landed on the kwavers peer stream AND item (c)'s atlas-meta pointer-advance chore commit has retired the KW-CV-001 watchpoint in `atlas/backlog.md` §In-flight claims (the row is either deleted or marked `RETIRED 2026-07-09+`).

## Alternatives considered

### Alternative A — Single mega-chore commit bundling items a + b + kwavers closeout

Rejected because: (a) violates atomic-boundary discipline §1 — bundling 3 conceptually-distinct changes (drift flush + predicate unification + closeout-style commit) into one commit makes per-change bisect impossible; (b) bloats one commit's review surface to an unreviewable magnitude (1,315-file drift flush alone is a substantial diff already); (c) the closeout-style commit then cannot be cleanly annotated with the tag (it would have to reference the other 2 bundled changes, defeating ADR 0010 §Per-batch tag annotation body simplicity).

### Alternative B — Atlas-meta emits all 3 items on atlas-meta-only files

Rejected per ADR 0011 §Decision §Leg 2 disjoint-scope rule: items (a) + (b) + the kwavers closeout-style commit require non-atlas-meta files (`D:/atlas/repos/kwavers/src/**` + `D:/atlas/repos/kwavers/Cargo.toml` for the unify predicate site; `D:/atlas/repos/kwavers/<every-folder>` for the 1,315-file drift flush). Atlas-meta is forbidden from touching `D:/atlas/repos/<X>/` files per disjoint-scope. The chore ownership is by definition kwavers peer stream for items (a) + (b) + closeout-style commit.

### Alternative C — Keep slice 7 `is_c_contiguous` predicate as-is in divergence.rs

Rejected per ADR 0013 §Failure modes / risks: the predicate divergence creates a category-mismatch in the helper SSOT's audit surface; future Batch #2 Entry Point #1 (N>5 closure-captured immuts ergonomics) work would have to special-case the divergence.rs site to satisfy the helper's `is_standard_layout` precondition. The unification brings slice 7 into alignment with slices 6b / 8 / 9 + aligns the helper SSOT surface — strictly additive from the source-reading perspective.

### Alternative D — Defer the closeout-tag ceremony to Batch #4 (kwavers-solver PINN Burn → Coeus)

Rejected per `atlas/backlog.md` ##Migration batches §Token batch ordering: Batch #4 and Batch #1 are in different positions in the dependency chain (Batch #4 depends on CR-4 + Batch #3; Batch #1 is the residual Rayon → Moirai that closes after CR-4 lands per the §Token batch ordering). Per `atlas/backlog.md`: "items ride under the established `codex/kwavers-atlas-integration` branch through that batch's owner". Closing Batch #1 does not wait for Batch #4; the closeout-tag ceremony is a Batch #1 closure ritual, not a Batch #4 prerequisite.

## Failure modes / risks

- **kwavers peer stream does not emit the closeout-style commit**: the KW-CV-001 watchpoint remains ACTIVE indefinitely; the closeout-tag ceremony cannot complete. Mitigation: the kwavers peer stream is owned by `repos/kwavers` claim stream per disjoint-scope (ADR 0011 §Leg 2) — atlas-meta CANNOT emit this commit on the kwavers peer stream's behalf. Standing-reminder in `atlas/backlog.md` §In-flight claims row forms the persistent visibility surface for the unfinished ceremony.

- **Item (b) predicate unification breaks cargo check** (i.e., the rewrite of slice 7 from `is_c_contiguous()` to `is_standard_layout()` introduces a regression in the divergence.rs test suite or a sibling site). Mitigation: per ADR 0012 §Decision §atomic-boundary discipline §4 (compile gate per sub-batch): `cargo test -p kwavers-solver --lib` must remain rc=0 post-item-(b); if it breaks, item (b) is rolled back via `git revert` (kwavers peer stream commit); the ceremony pauses until item (b) is reattempted.

- **Item (a)'s 1,315-file drift flush contains substantive non-mechanical changes** (e.g., the prior codex-session CRLF/normalization was contaminated with intent-changing whitespace edits). Mitigation: the flush is intentionally-scoped to mechanical CRLF/whitespace/trailing-newline normalization only; substantive intent changes are caught in code-reviewer pre-commit per Atlas-meta's standard discipline.

- **KW-CV-001 watchpoint strikes out the row** instead of using a residual "RETIRED" marker — this is the thinker's actionable recommendation. The §Sequencing withdrawal block below specifies the precise mechanism (delete row OR replace with `RETIRED` marker; atlas-meta is free to choose which preserves traceability).

- **Atlas-meta commits item (c) BEFORE items (a) + (b) + closeout land on the kwavers peer stream**: violates disjoint-scope (ADR 0011 §Leg 2) because item (c)'s pointer advance depends on the kwavers peer stream having emitted the closeout-style commit. The atlas-meta chore commit body MUST include the inner SHA of the kwavers peer stream's closeout-style commit, which can only be cross-referenced after that commit lands.

- **Cross-stream peer-WIP collision**: items (a) + (b) + the closeout-style commit are 3 separate atomic commits on the kwavers peer stream's `codex/kwavers-core-moirai-parallel` branch. Per `atlas/docs/coordination/concurrent_agents.md` disjoint-scope: atlas-meta commits ONLY touch atlas-meta files (`D:/atlas/docs/**`, `D:/atlas/backlog.md`, `D:/atlas/.gitmodules`); the kwavers peer stream commits ONLY touch `D:/atlas/repos/kwavers/**`. No claim-stream collision expected.

## Verification plan

Per ADR 0009 §Verification plan (8-step paragraph-collapse closure gate) + the KW-CV-001 watchpoint rule:

1. ✅ ADR 0009 CTE pattern bits: inner HEAD reconciliation between kwavers peer stream's slice 9 inner HEAD `949e5a39` + atlas-meta's gitlink pin at the matched inner SHA. (Status as of ADR 0013 landing: matched.)
2. 🟡 Item (a) lands on kwavers peer stream: `cd /d/atlas/repos/kwavers && git log --oneline -1 949e5a39..HEAD` enumerates the flush commit; the file-touch count matches the 1,315-file drift surface in `atlas/backlog.md` §Atlas-root working-tree dirty triage `kwavers` row.
3. 🟡 Item (b) lands on kwavers peer stream: `rg -nFc 'is_c_contiguous' /d/atlas/repos/kwavers/crates/kwavers-solver/src/forward/elastic/swe/stress/divergence.rs` returns 0 (was 6 pre-item-b per ADR 0013 §matrix divergence.rs row); `rg -nFc 'is_standard_layout' <same>` returns 8 (was 0 pre-item-b; matches the slice 6b / 8 / 9 verbose-form predicate count).
4. 🟡 The kwavers peer stream's closeout-style commit lands: `git -C /d/atlas/repos/kwavers log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l` returns ≥1 (was 0 historically; the closeout commit's subject `chore(kwavers): Close Batch #1 atlas-migration-push/batch1 per ADR 0014` matches the regex).
5. 🟡 Item (c) lands on atlas-meta: `git diff --cached -p` shows only `repos/kwavers` parent-tree gitlink advance + `backlog.md` KW-CV-001 row withdrawal; no `repos/<other>/` file changes (per disjoint-scope).
6. 🟡 KW-CV-001 watchpoint retirement: `rg -n 'KW-CV-001' /d/atlas/backlog.md` returns 0 OR the row is marked `RETIRED 2026-07-09+` per §Sequencing withdrawal block.
7. Status field flips: ADR 0014 §head of file from `Proposed` to `Accepted` in a follow-up atlas-meta chore commit (when items (a) + (b) + closeout + (c) all land).
8. CI scanner hardening: the `is_c_contiguous` removal item from ADR 0013 §Failure modes / risks reconciliation is satisfied (post-item-(b) `cargo test -p kwavers-solver --lib` regression-clean).

## Sequencing (implementation increments, atomic commits)

Per ADR 0011 §Decision §Leg 2 disjoint-scope + ADR 0010 §Per-batch tag convention + ADR 0012 §Decision §atomic-boundary discipline §1:

### Atomic inner-side slice commits + closeout (kwavers peer stream ownership)

1. **Item (a) — kwavers peer stream atomic commit**: `chore(kwavers): Flush mechanical dirty triage (1,315-file CRLF/whitespace batch)` — emits one commit on `repos/kwavers` `codex/kwavers-core-moirai-parallel` that captures the 1,315-file drift flush. Single atomic commit, no intermixed substantive changes.
2. **Item (b) — kwavers peer stream atomic commit**: `refactor(kwavers-solver): Unify divergence.rs is_standard_layout predicate (eliminate is_c_contiguous divergence from slice 7)` — rewrites slice 7's 3 mut outs in `crates/kwavers-solver/src/forward/elastic/swe/stress/divergence.rs` (Pass 1a / 1b / 2) from `is_c_contiguous()` to `is_standard_layout()` verbose-form. Aligns slice 7 with slices 6b / 8 / 9. Compile gate: `cargo test -p kwavers-solver --lib` remains rc=0.
3. **Item (kwavers closeout) — kwavers peer stream atomic commit**: `chore(kwavers): Close Batch #1 atlas-migration-push/batch1 per ADR 0014` — emits the closeout-style commit that triggers KW-CV-001 retirement. Commit subject matches the watchpoint regex `closeout|close-batch` (substring `Close` + `closeout`).
4. **Annotated tag — kwavers peer stream tag pointer**: `git -C /d/atlas/repos/kwavers tag -a kwavers/atlas-migration-push/batch1 <closeout-sha>` — annotates the closeout-style commit's SHA with the 9-slice chain enumerated in the tag annotation body per ADR 0010 §Per-batch tag convention.

### Atlas-meta closure chore commit (atlas-meta ownership)

5. **Item (c) — atlas-meta chore commit**: `chore(atlas): Advance repos/kwavers submodule pointer to <closeout-sha> + KW-CV-001 watchpoint retirement` (current turn cannot complete this step because the kwavers peer stream's closeout-style commit (item 3) has not landed yet — this sequencing step is the next chore whose trigger is the kwavers peer stream emitting items 1-3). When executed, the chore commit MUST:
   - (i) Stage ONLY `repos/kwavers` parent-tree gitlink + `atlas/backlog.md` §In-flight claims KW-CV-001 row (delete OR mark `RETIRED 2026-07-09+`).
   - (ii) Commit body MUST cross-reference the kwavers peer stream's inner closeout SHA + the annotated tag `kwavers/atlas-migration-push/batch1`.
   - (iii) Optional: amend ADR 0014 Status field from `Proposed` to `Accepted` via a follow-up atlas-meta chore commit (keeps the ADR achievement-timestamp accurate).

### Watchpoint withdrawal block (KW-CV-001 retirement mechanism)

Per the thinker's actionable recommendation #1, the precise mechanism for KW-CV-001 retirement is documented here so the next codex session can execute it deterministically:

- **Option (i) — DELETE the KW-CV-001 row from `atlas/backlog.md` §In-flight claims** (more aggressive; removes the visibility surface entirely).
- **Option (ii) — REPLACE the KW-CV-001 row with a one-line `RETIRED 2026-07-09+` marker** (`git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l` returns 1 → watchpoint row → `RETIRED 2026-07-09` per ADR 0014 §closeout-tag ceremony acknowledgement; see `D:/atlas/docs/adr/0014-kwavers-batch1-closeout-tag.md`).
- Default: option (i) — DELETE. The watchpoint is a transient observation device; once retired, the row has no semantic value in `atlas/backlog.md`. Option (ii) is reserved for the audit-disciplined reader who wants to trace KW-CV-001's historical record.

### Atlas-meta claim scope per this turn

This turn's atlas-meta chore commit bundles:
- New file `D:/atlas/docs/adr/0014-kwavers-batch1-closeout-tag.md` (this ADR, Proposed status).
- `D:/atlas/docs/adr/INDEX.md` row addition for ADR 0014.
- `D:/atlas/backlog.md` §In-flight claims forward-looking note indicating "ADR 0014 active; kwavers peer stream chore sequence pending per disjoint-scope (ADR 0011 §Leg 2)".

Items 1-4 in the kwavers peer stream sequence are FORBIDDEN from atlas-meta per disjoint-scope. The atlas-meta author publishes ADR 0014 as a forward-looking artifact; the chore implementation commits live on the kwavers peer stream.

## Out of scope (explicit non-goals)

This ADR does NOT address — and the closeout-tag ceremony does NOT include — the following carried-forward pre-existing blockers (per ADR 0013 §Out of scope items 1-5):

1. **`repos/ritk/crates/ritk-wgpu-compat/Cargo.toml` burn workspace-manifest** — per ADR 0012 §Sub-batch #5 major Burn remove cycle.
2. **`repos/ritk/crates/ritk-registration/Cargo.toml` burn dep strip** — per ADR 0012 §Sub-batch #5 `[major]`.
3. **`repos/ritk/crates/ritk-image` autodiff-module syntax** — per ADR 0012 §Sub-batch #3 per-crate test ports (excluded per the 2026-07-07 amendment; deferred to sub-batch #5).
4. **1,315-file mechanical working-tree drift on `repos/kwavers`** — item (a)'s flush commit IS the resolution mechanism for this item; once item (a) lands, this carryover is retired.
5. **`kwavers-math` Phase-3 / Phase-4 ndarray → leto array migration breakage (post-slice-9)** — per ADR 0013 §Failure modes / risks line 1; per `atlas/backlog.md` ##In-flight claims row; the kwavers peer stream's continuing Phase-3 / Phase-4 workstream is its own orthogonal carve-out. The item (b) predicate unification is narrowly the SLICE 7 divergence.rs predicate unification; it does NOT block on the broader Phase-4 ndarray → leto workstream.

Additionally, the closeout-tag ceremony does NOT include:
- Locking the kwavers peer stream's `codex/kwavers-core-moirai-parallel` branch after item 3 (the closeout-style commit); the kwavers claim stream retains ownership post-closeout per disjoint-scope.
- Closing Batch #4 (kwavers-solver PINN Burn → Coeus); Batch #4 closure is a separate ceremony owned by the `kwavers/atlas-migration-push/batch4` reservation per ADR 0010 §Per-batch tag convention.
- Authoring subsequent ADRs (Batch #2 entry point work + helper ergonomic validation); those ADRs are filed independently once Batch #2 entry-point validation work begins.
