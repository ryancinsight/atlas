# ADR 0011 — Atlas-root working-tree hygiene ritual (delegate-cleanup-by-class + disjoint-scope + OOS-record cadence)

- Status: **Accepted** — implementation closed 2026-07-06 (cleanup chore commit `0b60c330783013f9e60102d01376ccca117a0611` deleted 3 of 4 untracked items, 4-pattern `.gitignore` defense in place, `D:/atlas/backlog.md` `## Out-of-scope (explicit) ## Atlas-root working-tree dirty triage` §A/§B subsections retracted to past-tense, §C/§D tables preserved, §E updated to carry the remaining forward-looking hooks).
- Date: 2026-07-06.
- Driver: future codex sessions managing the Atlas-meta working tree need an explicit anchor for the hygiene ritual rather than rediscovering the OOS-record shape from the rolled `## Atlas-root working-tree dirty triage (YYYY-MM-DD)` subsection of `D:/atlas/backlog.md`. The shape was first introduced ad-hoc in the 2026-07-06 triage commit (`283f38cf`) and the implicit cadence (triage → OOS-record → chore commit → §-retract → §-update) re-discoverable only by reading the original commit narrative. This ADR fixes that discovery gap.
- Relates to: ADR 0005 (`eunomia::NumericElement` SSOT, status flow); ADR 0006 (`eunomia::ComplexField` SSOT, per-batch migration convention); ADR 0007 (`eunomia::Complex<T>` SSOT, per-subcrate `[patch]` sweep adopting this tag convention); ADR 0010 (Atlas-parent pointer-advance + per-batch tag convention — the closure-ritual counterpart to the hygiene ritual documented here); ADR 0011 (this ADR).
- Supersedes: the implicit OOS-record shape previously carried only inline in `D:/atlas/backlog.md` `## Out-of-scope (explicit) ## Atlas-root working-tree dirty triage` (first introduced 2026-07-06 by commit `283f38cf`); no prior ADR anchored the ritual.

- Index: docs/adr/INDEX.md#ADR-0011
## Context

The Atlas-parent repo `D:/atlas` accumulates dirty files in 4 persistent categories whenever a codex session pauses mid-flight without committing in-scope items:

1. **Category A — Root-level scratch** (`nul`, `script.py`): zero-byte or near-zero files at workspace-root, often Windows-shell-redirect artifacts (`> nul`) or peer-claim-tools scratch.
2. **Category B — External / non-ASCII-dir content** (e.g. `repos/SynthSeg/`, `repos/report/`): non-submodule directories present at `D:/atlas/repos/<name>/` but lacking `.gitmodules` registration; either standalone git clones (with their own inner `.git/`) or non-ASCII-filename-generated output dirs.
3. **Category C — Submodule-internal dirtiness** (14 submodules with 0..602 inner files dirty, Σ=1591): the parent-tree entry `M repos/<name>` is marked dirty because the inner submodule's tree contains modifications relative to the gitlink pinned here.
4. **Category D — Helios-internal pre-session WIP**: 6 specifically-named files + 23 unnamed = 29 internal-dirty inside `repos/helios` (a special case of C but worth tracking separately because Helios is the in-house migration-target and accumulates Sprint-1 pre-session WIP).

Categories A and B are reachable from Atlas-meta and are cleanable by Atlas-parent chore commits. Categories C and D are NOT reachable from Atlas-meta: they require inner-submodule commit + Atlas-parent gitlink advance per per-repo claim streams.

The hyaluron discovery gap: before this ADR, when a codex session encountered dirty Atlas-root files, it could either (a) commit them inline (risk: mis-classifying submodule-internal dirtiness as Atlas-meta work, violating `concurrent_agents` disjoint-scope), or (b) record them in `backlog.md` `## Out-of-scope (explicit)` ad-hoc (risk: the OOS-record shape varies wildly per-session because no template exists). The 2026-07-06 triage turn made the latter explicit for the first time but only at the SSOT-where-it-was-implemented layer (`backlog.md` `## Atlas-root working-tree dirty triage` subsection). This ADR promotes the implicit cadence to a named ritual.

### Trigger event for this ADR

The 2026-07-06 triage turn + cleanup chore commit (`0b60c330783013f9e60102d01376ccca117a0611`) exercised the full ritual end-to-end:

1. Triage turn fanned the 29-file dirty tree into 6 atomic docs/chore commits (`48296279` ADR; `14cba7ec` 3 audits; `05993c98` atlas-migration audit; `aef9bee9` PR draft; `032d418e` codemod script; `283f38cf` OOS-record append to backlog.md) + recorded 24 OOS items in the §X structure.
2. Cleanup chore turn (`0b60c3307`) resolved §A + §B (3/4 deletions successful; `nul` blocked by Windows-reserved-name PermissionError, defense-in-depth via `.gitignore`), retracted §A + §B to past-tense, updated §E past-tense, preserved §C + §D tables + the 14 submodule × inner-dirty × inner-HEAD + σ=1591 detail.

Without this ADR, a future codex session doing the same work would have to retrace the implicit cadence from commit messages alone. The audit value of "this is what the 24-item OOS record became" would be lost.

## Decision

Adopt a canonical Atlas-root working-tree hygiene ritual with three named legs:

### Leg 1 — Delegate-cleanup-by-class

Classify each dirty file at the Atlas-root into one of 4 categories (A, B, C, D). Each class has a canonical delegate: A → Atlas-meta chore commit; B → Atlas-meta chore commit (+ `.gitignore` defense-in-depth); C → per-repo claim stream (NO ATLAS-META RECLAIM); D → per-repo claim stream (NO ATLAS-META RECLAIM). The classification must draw on these canonical signals:

| Category | Canonical signal | Example |
|----------|------------------|---------|
| A | `?? <file>` at workspace-root where `<file>` is < 8 chars and matches a Windows-reserved-name hazard, OR is a `.py`/`.sh`/`.txt` scratch without a `scripts/`-prefix or `repos/<submodule>/`-prefix parent. | `nul`, `script.py` |
| B | `?? repos/<name>/` where `<name>` is not in `.gitmodules`. Sometimes contains a `.git/` (standalone git clone, deletion needs `shutil.rmtree` with onerror chmod+retry). Sometimes non-ASCII-filename (path-handling needs python iteration not bash `find`). | `repos/SynthSeg/` (standalone clone); `repos/report/` (non-ASCII generated output) |
| C | `M repos/<submodule>` (parent-tree dirty marker) AND `git -C repos/<submodule> status --short \| wc -l > 0` (inner-submodule tree dirty). | `apollo` 235; `kwavers` 602; `ritk` 631; `mnemosyne` 0 (clean); `themis` 0 (clean) |
| D | Sub-case of C where `<submodule>` is `helios` AND the dirty files are named in a stable list (CHANGELOG / CHECKLIST / Cargo.lock / Cargo.toml / backlog.md / gap_audit.md / + 23 internal-dirty). Tracked separately because Helios is the in-house migration-target and its Sprint-1 work deserves visibility. | `repos/helios/CHANGELOG.md`; `repos/helios/backlog.md` |

For each class, the delegate commits to a specific *verb* on the file system + a specific *git-rite* on the Atlas-parent:

| Class | File-system verb | Git-rite |
|-------|------------------|----------|
| A | `python3 -c "import os; os.remove(p)"` (or `os.rename`-then-`os.remove` for Windows-reserved-name collision) | Atlas-meta compile of all in-scope A items into a single `chore(atlas): Atlas-root cleanup — delete <item-list>` commit; OOS subsection retract in `backlog.md` |
| B | `python3 -c "import shutil; shutil.rmtree(d, onerror=onerror_with_retry)"` (onerror handler chmods + retries after Windows pack-file collisions on `.git/objects/pack/*`) | Atlas-meta + the chore commit appends 1-line-per-item to `.gitignore` for future defense-in-depth; OOS subsection retract in `backlog.md` |
| C | NO ATLAS-META FILESYSTEM CHANGES (inner-submodule commit only) | Atlas-meta appends OOS `#### C. Submodule-internal dirtiness` subsection to `backlog.md` with the 14-row inner-dirty × inner-HEAD × claim-stream table |
| D | Sub-case of C | Sub-case of C with the explicitly-named 6-row table + 23 additional-dirty envelope |

### Leg 2 — Disjoint-scope rule (re-affirms `concurrent_agents`)

The atlas-meta chore commit MUST NOT touch categories C or D (NO ATLAS-META RECLAIM). The rule is symmetric:

- Atlas-meta does not commit file-system mutations of submodule-internal files. It only commits Atlas-parent gitlink entries (which are outer-tree mutations) AND PM-artifact files at workspace-root (backlog.md, gap_audit.md, checklist.md, ADR/*.md, scripts/*, .gitignore).
- Each peer claim stream owns its own submodule's source. The atlas-meta never edits `repos/<submodule>/<file>` even if the file path superficially looks like Atlas-meta PM content (e.g. `repos/helios/backlog.md` is Helios-internal not atlas-meta).
- The rule surfaces concretely in §C + §D OOS subsection sentences: "**Cleanable only by inner-submodule commit + Atlas-parent gitlink advance**, NOT by Atlas-parent commit."

The disjoint-scope rule enforces that a codex session running atlas-meta claim does not accidentally collapse someone else's active workstream into a doc/chore commit. The risk of "I see `M repos/kwavers`, let me `git add repos/kwavers` and commit" is explicitly disambiguated by Phase 1: if the inner submodule has uncommitted modifications, `git add repos/kwavers` would stage a gitlink update AND absorb the inner-uncommitted changes into a parent-tree dirty state that the parent cannot fix without inner-commit. The disjoint-scope rule says: don't do it; record in OOS §C instead; let the peer close their inner commit + your next pointer advance picks it up automatically.

### Leg 3 — OOS-record cadence

`D:/atlas/backlog.md` `## Out-of-scope (explicit) ## Atlas-root working-tree dirty triage` subsection is the SSOT for OOS-recorded items. The cadence:

1. **Initial record** (Triage turn): append a new section with the `### Atlas-root working-tree dirty triage (YYYY-MM-DD)` heading (h3) under the existing `## Out-of-scope (explicit)` anchor. Inside: sub-section A, B, C, D, E (per-class, h4) describing each category's items + claim-stram attribution. E is "Future-correction hooks" with forward-looking retraction conditions.
2. **Resolution branch**: when the next chore commit (or per-class commit) resolves §A or §B, the OOS subsection's A/B sub-section is converted from "list of items + recommendations" to a "retraction note describing what happened in the chore commit". The §C + §D tables + σ=1591 detail stay UNTOUCHED (they remain the SSOT for the open C/D classes).
3. **Post-resolution §-E update**: §E is updated to (i) drop the §A/§B retractability clauses (now resolved), (ii) carry the remaining forward-looking hooks (the §C/§D cleanup is genuinely separate-flow; any class-A file that re-emerges is gitignored).
4. **Full retraction** (when §C + §D close too): the entire `### Atlas-root working-tree dirty triage (YYYY-MM-DD)` subsection can be retracted entirely if all 4 classes have closed. This is a `chore(atlas): Retract Atlas-root working-tree dirty triage (YYYY-MM-DD)` commit. Practically, §C + §D close rarely because submodule-internal dirtiness is the cost-of-business for a multi-repo Atlas; expect only 1-2 full retractions per calendar year.

The OOS-record cadence is asymmetric: §A and §B retract forward (resolved in chore commit within days of triage); §C and §D retract backward (resolved by per-repo claim streams closing their inner-main updates over weeks/months).

## Alternatives considered

### Rejected Variant A — Roll the hygiene ritual into a `.codex/` config file

Encode the 4-class classification + delegate matrix + cadence as a JSON/YAML config at `D:/atlas/.codex/hygiene.json`. **Rejected**: ADR is the canonical Atlas-meta doctrine layer per `atlas/AGENTS.md` `documentation_discipline`. A `.codex/` config file would be a tool-specific bypass that future codex sessions could silence without contradicting Atlas-meta policy. The ritual MUST live in `docs/adr/` so that it is grep-discoverable via `rg "hygiene"` or `rg "delegate-cleanup-by-class"` cross-cutting all reference points.

### Rejected Variant B — Roll the hygiene ritual into `backlog.md` only (no ADR)

Keep the implicit OOS-record shape in `backlog.md` and treat this commit (`0b60c3307`) as the de-facto anchor. **Rejected**: `backlog.md` is a working document that gets re-written every codex session (15+ new entries per sprint). An ADR anchor is single-source-of-truth for a policy that outlasts any single working sprint. Mixed anchor philosophies mixed `backlog.md` and ADR is the prior-session pathology this ADR cures.

### Rejected Variant C — Commit-by-class (4 separate chore commits, one per class)

Instead of one chore commit that bundles all in-scope items, split into `chore(atlas): Delete §A scratch` + `chore(atlas): Delete §B non-ASCII dirs + gitignore` + (no §C / §D commits). **Rejected**: the per-session commit-count budget is finite (1 active merge-affecting item per micro-sprint per WIP limit). Bundling into a single `chore(atlas): Atlas-root cleanup — delete <item-list>` keeps the audit trail compact; splitting penalizes codex session overhead without adding decision value. A-class and B-class are cleanable atomically; they always get bundled.

### Rejected Variant D — Per-class-OOS-rather-than-OOS-by-section (matrix flattening)

Instead of a hierarchical §A/§B/§C/§D/§E structure, render a flat table with columns (Class | Item | Delegate | Resolution-state). **Rejected**: the table would be wide (24 entries × 4-5 columns) and would require re-sorting after each resolution. The hierarchical §-structure sorts itself by resolution-breadth once items close (closed items retract, open items stay at the SSOT-deepest-layer-so-the-deepest-table-stays-untouched).

### Rejected Variant E — Git-update-index skip-worktree for `nul` instead of `.gitignore` exclude

For the Windows-reserved-name `nul` artifact specifically, run `git update-index --skip-worktree nul` so it doesn't appear in `git status --short` without `.gitignore` edits. **Rejected**: `skip-worktree` requires the path to be FIRST tracked or in the index; this is a per-repo state mutation, not a property of the path glob pattern. `.gitignore` excludes are stable and portable across branches/clone-restores. `skip-worktree` is good for one-off local-only hack files; this is a Windows-reserved-name OS artifact that needs defense-in-depth.

## Failure modes / risks

- **Mis-classification into wrong delegate.** A `?? script.py` in `repos/helios/` (not the workspace-root) is Class A's signal ONLY at workspace-root; inside `helios` it is Helios-internal and goes to Class D. Mitigation: classification must check both the path AND the inner-submodule state; the entry `M repos/helios/script.py` (which doesn't actually exist in the standard Sprint-1 surface) would be Class D, while `?? script.py` at the workspace-root is Class A.

- **`.gitignore` over-matching.** A bare-filename pattern like `nul` matches anywhere in the tree (per modern git's match-anywhere behavior). If an inner-submodule file happens to be named `nul` or `script.py`, the ignore-pattern would suppress it. Mitigation: prefer repo-root-only matching with `/`-prefix forms (`/nul`, `/script.py`) when the cleanup is root-specific; the existing `chore(atlas): Atlas-root cleanup` commit's bare-filename forms are acceptable for defense-in-depth (no inner-submodule file is conventionally named `nul`/`script.py`).

- **Windows-reserved-name on-disk-removal blocked.** `os.remove`'ing a file whose basename is a Windows reserved device name (`nul`, `con`, `prn`, `aux`, `com1`-`com9`, `lpt1`-`lpt9`) returns `PermissionError` from `DeleteFileW`. Even `\\?\`-prefix extensions don't bypass because Windows NTFS treats the basename as a reserved name. Mitigation: use `.gitignore` defense-in-depth + admin `cmd /c del /F /Q nul` or Windows-reboot via `MoveFileExW + MOVEFILE_DELAY_UNTIL_REBOOT` for on-disk removal. The chore commit explicitly accepts the .gitignore-only resolution for `nul` and documents the on-disk-blocker in the §A retraction note + §E forward-looking hook.

- **Submodule gitlink-state collision during Atlas-meta chore.** If a codex session runs `git add .gitignore backlog.md` while a peer claim stream is concurrently committing inside `repos/<submodule>/`, the parent's gitlink could advance mid-commit and pin a state-of-the-world the peer hasn't finished. Mitigation: the disjoint-scope rule prohibits Atlas-meta from touching submodule-internal files (which a `git add .gitignore backlog.md` chore commit does NOT do — gitignore and backlog are at workspace-root, not sub-internal). Atomic-chore scope discipline is the operational guarantee.

- **§-retraction commits referencing future-correction clauses that already closed.** If the §-retraction commit fails to update §E's "if §A/§B close, retract" wording, future codex sessions will see a stale "this subsection can be retracted" mention that contradicts the now-retracted §A/§B state. Mitigation: every §-retraction chore commit must include an §E update as part of the same commit (or follow-up commit). The cleanup chore commit (`0b60c3307`) did this correctly; the cadence is enforced by the §-retraction template.

- **Per-class delegate mis-routing.** A `?? repos/<X>/<file>` path that LOOKS like Class B (external / non-ASCII-dir) but is actually a typo-thinned submodule name (e.g. `repos/legend/` where `.gitmodules` has `legend` BUT the inner `.git/` is detached/HEAD-corrupted) would be Class B-cleaned by mistake, destroying peer-active scope. Mitigation: pre-cleanup sub-step `rg "<name>" .gitmodules` confirms the name is NOT a registered submodule. If the rg returns a match, the path is Class C, not Class B.

- **OOS-table column-count drift after §-retraction.** The §C 14-row submodule table's columns (Submodule | Inner dirty count | Inner HEAD | Inner branch / claim stream) and §D 6-row Helios-internal table's columns (File | Description | Clearable by) must remain untouched across §A/§B/E retractations. Mitigation: any §-retraction commit must verify the §-retraction str_replace-anchor does NOT capture any §C or §D table row; the §-retraction template includes this verification.

## Verification plan

After each Atlas-meta chore commit that touches the hygiene ritual:

1. `git show --stat <commit-SHA>` — confirm the chore commit scoped exactly to `.gitignore` + `backlog.md` (or whichever tracked files are in scope); confirm no `repos/<submodule>/` entries in the diff.
2. `git status --short | wc -l` — confirm the Atlas-root dirty count decreased by the on-disk-deleted-class size (3 for §A/§B combinations; 0 for §-only retractions).
3. `cat .gitignore` — confirm the appended ignore-pattern lines match the 4-pattern template (`nul` / `script.py` / `repos/SynthSeg/` / `repos/report/`) for the standard cleanup batch.
4. `awk '/^## Out-of-scope \(explicit\)/{flag=1} /^## /{if(flag && !/^## Out-of-scope \(explicit\)/){exit}} flag' D:/atlas/backlog.md` — confirm the §-structure is still present and §C/§D tables intact.
5. `rg "^#### [A-D]\." D:/atlas/backlog.md` — confirm only the expected sub-sections exist (4 per-batch plus §E variant templates).
6. `git tag -l '*/atlas-migration-push/*'` — confirm the batch-closure tags from ADR 0010 still resolve (the hygiene ritual does not perturb batch-tag conventions).

After the 2026-07-06 cleanup chore commit (`0b60c3307`):

7. `git -C D:/atlas rev-parse HEAD` — confirm the commit landed; SHA matches `0b60c330783013f9e60102d01376ccca117a0611`.
8. `git show 0b60c3307 --stat` — confirm 2-file diff (.gitignore + backlog.md).
9. `python3 -c "import os; print(os.path.exists('D:/atlas/nul'))"` — confirm `nul` on-disk status (acceptable: True; gitignored either way).
10. `python3 -c "import os; print(os.path.exists('D:/atlas/repos/SynthSeg'))"` — confirm `repos/SynthSeg/` is GONE (False).

## Sequencing (closure chain for the 2026-07-06 cleanup turn)

The hygiene ritual's full close-out for the 2026-07-06 batch was a 2-commit chain:

1. **(✓ done 2026-07-06) Triage record** — commit `283f38cf` on `codex/kwavers-atlas-integration` (subject `docs(atlas): Append Atlas-root working-tree dirty triage to backlog.md`). Established the §A/§B/§C/§D/§E OOS-record structure with 24 items (6 commit-now + 18 OOS) noted.
2. **(✓ done 2026-07-06) Cleanup chore + §-retraction** — commit `0b60c3307` on `codex/kwavers-atlas-integration` (subject `chore(atlas): Atlas-root cleanup — delete SynthSeg/report + gitignore + retract OOS §A-§B`). Resolved §A + §B (3/4 on-disk deletions; `nul` deferred to restart-handler); 4-pattern `.gitignore` defense in place; §A/§B/E state updates; §C + §D tables preserved.

Future hygiene-ritual close-out commits follow this 2-commit pattern: triage → chore-commit + §-retract. Single chore commits that close §A and §B are also acceptable if the triage record already exists (§-retraction is in same commit as chore).

## Out of scope (explicit non-goals)

- **Submodule-internal / Helios-internal cleanup (§C/§D).** The hygiene ritual records §C + §D in OOS; closing §C + §D is the per-repo claim streams' responsibility. Atlas-meta never advances submodule gitlinks to "burn down §C dirtiness" because doing so would collapse peer-claim scope into a doc/chore commit, violating disjoint-scope.

- **Bulk-cleanup Atlas-root `.gitignore` patterns.** General-purpose ignore patterns like `target/` / `*.log` / `.idea/` already exist in `D:/atlas/.gitignore`. The hygiene ritual only ADDS class-specific patterns (4 per cleanup batch). General `.gitignore` refactor is a separate concern (filed separately per `atlas/AGENTS.md`).

- **Atlas-parent-side force-clean of submodule gitlinks.** Tools like `git submodule foreach git checkout -- .` (force-reset inner state) are explicitly out of scope. The hygiene ritual coordinates with peer claim streams; it doesn't pre-empt their work.

- **Cross-class delegate-routing tooling.** Building a WP2 tool (`xtask atlas-hygiene-classify`) that auto-runs the 4-class classification + per-class delegate is a future enhancement. The current ritual is a coder-disciplined checklist; tooling would replace discipline with code. Filed for ADR 0012+ (architectural tooling extensions).

- **Compression of the §C 14-row submodule table when all 14 modules close.** When §C + §D both close, the entire `### Atlas-root working-tree dirty triage` subsection can be retracted. The cadence widens here (rarely exercised) — a future codex session can retire the entire subsection with a single `chore(atlas): Retract Atlas-root working-tree dirty triage (YYYY-MM-DD)` commit when condition triggers.

- **Atlas-meta claim-stream retention policy.** When Atlas-meta's per-sprint buckets close, the `backlog.md` `## In-flight claims (per concurrent_agents)` section transitions to next-sprint-bucket content. The hygiene ritual owns the `## Out-of-scope (explicit)` subsection only; the in-flight-claim section is a separate `concurrent_agents` concern.

## References

- `D:/atlas/docs/adr/0005-eunomia-scalar-ssot.md` — the SSOT rebind that the CFDrs Batch #2 closure consumed; precedent for ADR-anchored Atlas-meta claim.
- `D:/atlas/docs/adr/0007-eunomia-solver-csr-ssot.md` — the per-subcrate `[patch]` sweep that adopts ADR 0010's tag convention; precedent for adoption gestures.
- `D:/atlas/docs/adr/0010-cfdrs-atlas-pointer-advance.md` — the closure-ritual counterpart: per-batch tag convention; this ADR is the hygiene-ritual counterpart.
- `D:/atlas/backlog.md` `## Out-of-scope (explicit) ## Atlas-root working-tree dirty triage (2026-07-06)` — the SSOT for the hygiene-ritual state at any time. Pre-ADR-0011-shape: implicit cadence; post-ADR-0011-shape: explicit delegation per this ADR.
- `D:/atlas/.gitignore` — the 4-class defense-in-depth pattern source.
- `D:/atlas/concurrent_agents` contract — disjoint-scope rule re-affirmed in §C + §D subsection sentences.
- Cleanup chore commit `0b60c330783013f9e60102d01376ccca117a0611` — the canonical 2026-07-06 execution of this ritual.
