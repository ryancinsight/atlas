# ADR 0010 — Atlas-parent pointer advance + tag for the 771-file CFDrs provider migration push (Batch #2 closure)

- Status: **Accepted** — implementation closed 2026-07-05 (CFDrs HEAD `d58d1fe320d046816425e1d20d16735fcfee7995`; Atlas-parent pointer advance `51922a56c4d4acab3dbe786b90cc5acf92e22277`; Atlas-parent docs-rounding `dd676d13`; this ADR authoring commit TBD).
- Date: 2026-07-05.
- Driver: CFDrs Batch #2 closure — `cfd-math` / `cfd-2d` / `cfd-3d` / `cfd-1d` / `cfd-validation` nalgebra → leto + nalgebra-sparse → leto-ops `CsrMatrix` — is the first consumer migration batch to walk end-to-end through the eunomia scalar-SSOT rebind (ADR 0005). The Atlas-parent repo carries no ADR that documents the `inner-push → pointer-advance → docs-rounding → tag` ritual that closes such a batch. This ADR anchors the ceremony so subsequent batches (#3 ritk Burn → Coeus, #4 kwavers-solver PINN Burn → Coeus, #5 CR-1, #6 CR-2) inherit the same shape.
- Relates to: ADR 0005 (`eunomia::NumericElement` SSOT, CR-4, Accepted 2026-07-04 — the SSOT this batch consumed); ADR 0006 (`eunomia::ComplexField` SSOT, Approved 2026-07-05 — sets the per-batch `num_complex::Complex<T>` migration convention that Batch #1 of the kwavers complex sweep will inherit); ADR 0007 (`eunomia::Complex<T>` SSOT, CR-EUNOMIA-COMPLEX, Proposed 2026-07-06 — documents the per-subcrate `[patch]` sweep that ADR 0010's tag convention will reuse).
- Supersedes: the implicit `git add repos/<submodule> + commit + sync-PM` ritual carried inline in `atlas/backlog.md` `## In-flight claims` + `## Token batch ordering` sections, which had no explicit ADR anchor or tag convention.

## Context

`D:/atlas/repos/CFDrs` accumulated **771 dirty files** during the Atlas-provider migration (Sprint 1.96.126–1.96.137 carried the body migration; the migration push itself rolled them into one atomic commit). The closure is a 3-commit pair across CFDrs and the Atlas-parent repo, plus this ADR authoring commit as the 4th atom:

### Commit 1 (CFDrs-internal) — `d58d1fe320d046816425e1d20d16735fcfee7995`
- Branch: `repos/CFDrs` `codex/cfdrs-atlas-migration`.
- Subject: `refactor(cfdrs): Atlas-provider migration push (Leto CSR + Eunomia scalar + Hephaestus GPU + cfd-math / cfd-2d / cfd-3d / cfd-1d / cfd-validation consumer cones)`.
- Stats: 752 modified + 19 added files; 51,857 insertions(+); 22,087 deletions(-); ~2,500 tests pass, 0 warnings.
- Scope surfaces (named in the commit subject and enumerated in `repos/CFDrs/CHANGELOG.md`): cfd-math (linear-solver traits + preconditioner family ILU/SSOR/Jacobi/SOR/AMG/multigrid-restriction/workspaces + nonlinear/SIMD/DG/Spectral/WENO/differentiation/time-stepping + storage-slice + integration tests + upstream leto_ops::spgemm), cfd-2d (NS-FVM + SIMPLE/FDM/PIMPLE/Rhie-Chow/TVD/LBM/Venturi/Poiseuille/branching/cross-junction/problem/streamtube/Ghia scalers + `Cfd2dScalar` + num-traits removal), cfd-3d (spectral Poisson/Chebyshev + level-set + VOF cavitation + boundary vectors for cascade/bifurcation/trifurcation/serpentine/venturi + new `fem/leto_bridge.rs` + `Cfd3dScalar`), cfd-1d (vascular Bessel+Womersley Eunomia Complex + `SolverWorkspace` + `NetworkState` + `ConvergenceChecker` Leto Array1 + `Cfd1dScalar`), cfd-validation (SpMV + linear_solver + `ValidationScalar` + geometry/analytical/error-metrics/convergence/edge-case/manufactured/conservation/time-integration + numerical cones).
- Method: single atomic commit by the CFDrs claim stream.

### Commit 2 (Atlas-parent pointer advance) — `51922a56c4d4acab3dbe786b90cc5acf92e22277`
- Branch: `D:/atlas` `codex/kwavers-atlas-integration`.
- Subject: `chore(atlas): Advance CFDrs submodule pointer to d58d1fe3`.
- Diff: 1 file (`repos/CFDrs` gitlink entry advanced from `0f578e1af110c5b8536476174bf266bf8b812c37` to `d58d1fe320d046816425e1d20d16735fcfee7995`); 1 insertion(+), 1 deletion(-).
- Method: `git -C D:/atlas add repos/CFDrs` + structured commit.

### Commit 3 (Atlas-parent docs-rounding) — `dd676d13`
- Branch: `D:/atlas` `codex/kwavers-atlas-integration`.
- Subject: `chore(atlas): Sync CFDrs pointer d58d1fe3 + migration push record`.
- Diff: 3 files (`backlog.md`, `checklist.md`, `gap_audit.md`); 7 insertions(+), 5 deletions(-).
- Content: per-file cross-reference to `d58d1fe3` / `51922a56` / inner-commit subject / per-surface-statistics; flips CFDrs's PEER-WIP-COLLISION row in `gap_audit.md` from "peer-active, NOT reclaimable" → "closed, reclaimable by atlas-meta pointer advance".

### Commit 4 (this ADR authoring) — TBD
- Branch: `D:/atlas` `codex/kwavers-atlas-integration`.
- Subject: `docs(atlas): Author ADR 0010 for CFDrs pointer advance + tag`.
- Diff: 1 added file (`docs/adr/0010-cfdrs-atlas-pointer-advance.md`) + 2 modified files (cross-reference footers on `docs/adr/0005-eunomia-scalar-ssot.md` and `docs/adr/0007-eunomia-solver-csr-ssot.md`).
- Method: `write_file` + 2 `str_replace`; single atomic docs commit.

## Decision

The Atlas-parent repo carries **one canonical tag per consumer-batch closure**, anchored at the **inner consumer-repo commit** (the actual work product), with the tag name encoding `{consumer-repo}/atlas-migration-push/{batch-id}` and the tag annotation message body referencing this ADR by ID. Subsequent migration batches (#3 ritk Burn → Coeus, #4 kwavers-solver PINN) inherit the same name shape, so `git tag -l '*/atlas-migration-push/*'` produces a uniform audit trail across consumer-repo local clones.

### Tag command (for Batch #2)

```bash
git -C D:/atlas/repos/CFDrs tag -a cfdrs/atlas-migration-push/batch2 d58d1fe320d046816425e1d20d16735fcfee7995 \
  -m "Atlas-provider migration push for CFDrs Batch #2 (nalgebra -> leto + nalgebra-sparse -> leto-ops CsrMatrix across cfd-math / cfd-2d / cfd-3d / cfd-1d / cfd-validation).

Inner CFDrs commit: d58d1fe320d046816425e1d20d16735fcfee7995 on branch codex/cfdrs-atlas-migration.
Atlas-parent pointer advance: 51922a56c4d4acab3dbe786b90cc5acf92e22277 (chore(atlas): Advance CFDrs submodule pointer to d58d1fe3).
Atlas-parent docs-rounding: dd676d13 (chore(atlas): Sync CFDrs pointer d58d1fe3 + migration push record).
Diff: 752 modified + 19 added files; 51,857 insertions(+); 22,087 deletions(-).

See:
  - ADR 0010 (this tag's anchoring ADR)
  - ADR 0005 (eunomia::NumericElement SSOT rebind consumed by this push)
  - repos/CFDrs/CHANGELOG.md ## Unreleased 'Atlas-provider migration push' section"
git -C D:/atlas/repos/CFDrs push origin codex/cfdrs-atlas-migration --tags
```

The convention is **annotated tag** rather than lightweight so `git show <tag>` returns the closure narrative inline, without needing to consult this ADR separately. The convention also prefers the tag's name to omit the SHA and put the SHA only in the annotation message, to keep tag-name widths bounded.

### Tag pointer anchoring — why the inner consumer commit, not the Atlas-parent ceremony commits

- The **inner CFDrs commit** (`d58d1fe3`) is the unambiguous work product: its 771-file diff stat and the named subject are the auditable event.
- Tagging the Atlas-parent pointer advance (`51922a56`) or docs-rounding (`dd676d13`) instead would tag the **ceremony commits** rather than the work; such tags would be discoverable only against the Atlas-parent repo, not via `git tag | grep cfdrs` against a fresh clone of the inner CFDrs repo or via `git ls-remote` against the CFDrs origin.
- The Atlas-parent-side commits are documented in this ADR's `## Context` enumeration; they don't need their own tags because `git log --grep='cfdrs'` on Atlas-parent + this ADR + the inner-tag `git show` cross-walk give full traceability.

### Per-batch name pattern (generalization)

| Batch | Subject | Inner tag | Atlas-parent docs-rounding pointer |
|-------|---------|-----------|-------------------------------------|
| #1 (kwavers Rayon → Moirai) | `[patch]` | `kwavers/atlas-migration-push/batch1` | TBD |
| **#2 (CFDrs nalgebra → leto)** | `[minor]` | `cfdrs/atlas-migration-push/batch2` ✓ (this ADR's anchor) | `dd676d13` ✓ |
| #3 (ritk Burn → Coeus) | `[minor]` | `ritk/atlas-migration-push/batch3` | TBD |
| #4 (kwavers-solver PINN Burn → Coeus) | `[minor]` | `kwavers/atlas-migration-push/batch4` | TBD |
| #5 (CR-1: Apollo-ghostcell → Melinoe) | `[arch]` | `apollo/atlas-migration-push/batch5` | TBD |
| #6 (CR-2: `#[global_allocator]` consolidation) | `[arch]` | `cfd-core+ritk-core+moirai/atlas-migration-push/batch6` | TBD |

The `{consumer-repo}` is the leaf consumer responsible for the migration push. For multi-repo CR-class commits that touch several repos atomically (e.g., CR-2), the tag lives on the **primary repo** and the tag annotation enumerates the cross-repo commit chain.

## Alternatives considered

### Rejected Variant A — Tag the Atlas-parent docs-rounding commit instead of the inner consumer commit

Tag `dd676d13` with name `atlas-meta/cfdrs-pointer-advance/batch2`. **Rejected**: tags the ceremony commit rather than the work product. Auditing the actual CFDrs migration push would still require a `git --git-dir=repos/CFDrs/.git log <inner-tag>...d58d1fe3` cross-repo walk, defeating the purpose of having an inner-clone-discoverable tag.

### Rejected Variant B — Tag every commit in the 4-commit closure chain

Tag each of `d58d1fe3`, `51922a56`, `dd676d13`, and this ADR authoring commit independently. **Rejected**: tag noise. With ~10 migration batches anticipated across 2026 Q3/Q4, this scales to ~40 ceremony-side tags. `git tag -l` becomes unscannable, and `rg "atlas-migration-push"` (the audit query) returns noise. One tag per inner atomic push is the right granularity; Atlas-parent ceremony is documented per-batch in this ADR and `atlas/backlog.md` `## In-flight claims`.

### Rejected Variant C — No tag at all

Rejected per the user's explicit "tag" requirement in the ADR-driving brief. For completeness: tags are zero-behaviour-cost references (they don't change the codebase's compile-time, runtime, or test surface) and give a stable cross-repo audit anchor that humans and tooling (`rg "atlas-migration-push"`, `git ls-remote`) both can resolve with one query each.

### Rejected Variant D — Encode the SHA in the tag name (e.g., `cfdrs/atlas-migration-push/batch2-d58d1fe3`)

Rejected: tag-name widths become unbounded; the SHA is part of `git show <tag>` output; duplicating in the name is redundant. Keep SHA in the annotation message only.

### Rejected Variant E — Tag according to numeric version (e.g., `cfdrs/atlas-migration-push/v0.2.0`)

Rejected: the Atlas meta-version is `0.16.0` and increments per-batch under `versioning` policy; encoding the meta-version in the tag is misleading because a single migration batch may roll multiple per-crate versions. Use the per-`atlas/backlog.md` row number (`batch2`, `batch3`, ...) which is stable.

## Failure modes / risks

- **Tag created on the wrong commit.** If a follow-up fixup pushes the inner CFDrs HEAD past `d58d1fe3`, the existing tag still points at the original work-product commit (annotated tags are immutable commit references). Mitigation: follow-up fixups should land as a separate commit with a separate tag (or no tag if it's a follow-on cleanup). Don't amend `d58d1fe3`.
- **Tag created on the wrong branch.** The tag must be created from inside `repos/CFDrs/.git` while the working tree is on `codex/cfdrs-atlas-migration`. Mitigation: confirm `git -C D:/atlas/repos/CFDrs rev-parse --abbrev-ref HEAD` is `codex/cfdrs-atlas-migration` BEFORE running `git tag -a cfdrs/atlas-migration-push/batch2 d58d1fe3`.
- **Tag subject drift across batches.** If a future batch breaks the `*atlas-migration-push/batchN*` name shape, `git tag -l '*/batch*' | sort` would no longer group them. Mitigation: name-shape is enforced by this ADR for any migration batch that flows through the Atlas-parent pointer-advance ritual; batches that follow a different path (e.g., a follow-up fixup that doesn't roll a full migration push) use `(compat)` or `(fixup)` suffixes and are NOT classified as atlas-migration-pushes.
- **Tag annotation drift.** The annotation body references ADR 0010 by ID. If this ADR is ever repathed (extremely unlikely), the cross-reference becomes stale. Mitigation: any ADR repath must be accompanied by a `git tag -f <tag> <commit>` re-tag.
- **Cross-repo tag namespace collision.** Each submodule repo has its own `.git` directory; the `cfdrs/` prefix in the tag name disambiguates by repo no matter how many submodules adopt the same name pattern (`apollo/atlas-migration-push/batch5`, `ritk/atlas-migration-push/batch3`, etc.).
- **`git tag -a` requires tagger identity.** Annotated tags need `git config user.name`/`user.email` set; if either is unset, `git tag -a` fails. Mitigation: pre-flight `git -C repos/CFDrs config --get user.email`; if missing, the operator should configure it before tagging.
- **Pushing the tag requires `--tags`.** `git push origin codex/cfdrs-atlas-migration` does NOT push the tag by default. The convention includes `git push origin <branch> --tags` to ensure the tag reaches the remote. Mitigation: explicit `--tags` in the convention's command block.
- **Atlas-parent pointer advance on a stale snapshot.** If `git add repos/CFDrs` from Atlas root happens before the inner CFDrs commit `d58d1fe3` reaches the local submodule's `HEAD` (e.g., because the CFDrs-side commit was made on a different machine and `repos/CFDrs` hasn't been re-fetched), the pointer advance records the wrong SHA. Mitigation: the convention is "inner commit first, then pointer-advance", enforced by Atlas-side workflow ordering. A pre-flight `git -C repos/CFDrs rev-parse HEAD` BEFORE `git -C D:/atlas add repos/CFDrs` confirms the expected SHA.

## Verification plan

After tag creation (which is a write-only operation against `repos/CFDrs/.git/refs/tags/`), the following commands verify it landed correctly:

1. `git -C D:/atlas/repos/CFDrs show-ref --tags cfdrs/atlas-migration-push/batch2` — confirms the tag exists; output line format: `<SHA> refs/tags/cfdrs/atlas-migration-push/batch2`; the SHA on the left of the reference is the tagged commit, expected `d58d1fe320d046816425e1d20d16735fcfee7995`.
2. `git -C D:/atlas/repos/CFDrs show --no-patch --format='%H%n%s%n%ci%n%n%b' cfdrs/atlas-migration-push/batch2` — confirms the tag annotation captures the closure narrative + that the body references ADR 0010 by ID.
3. `git -C D:/atlas/repos/CFDrs cat-file -t cfdrs/atlas-migration-push/batch2` — confirms the tag object type is `tag` (annotated), not `commit` (lightweight). The convention here forbids lightweight tags for batch closures; lightweight is acceptable only for ad-hoc debugging tags.
4. `git -C D:/atlas/repos/CFDrs rev-parse --abbrev-ref HEAD` — must be `codex/cfdrs-atlas-migration` at tag-creation time (verify in the working tree AFTER `git status` shows clean). If HEAD is on a different branch, the tag was created from the wrong branch (mitigation: re-tag from the correct branch).
5. `git -C D:/atlas/show-ref | grep -E '(51922a56|dd676d13)'` — confirms Atlas-parent-side commits exist with the expected subjects; the Atlas-parent does NOT have a per-batch tag (the convention is "inner-only"), so this grep should show the *commit* records, not tag records.
6. `git -C D:/atlas/repos/CFDrs ls-remote --tags origin 'cfdrs/atlas-migration-push/*'` — confirms the tag reached the CFDrs remote after the `git push origin codex/cfdrs-atlas-migration --tags` step. The output line format: `<remote-SHA> refs/tags/cfdrs/atlas-migration-push/batch2`. If empty, the push step was skipped or rejected.

## Sequencing (atomic commits in this closure)

The 4-commit closure chain is sequential, with the tag creation as a 5th step that is not a commit (tags are commit-pointer metadata, recorded in the inner CFDrs `.git/refs/tags/` namespace).

1. **(✓ done 2026-07-05) CFDrs-internal**: commit `d58d1fe3` on `codex/cfdrs-atlas-migration`.
2. **(✓ done 2026-07-05) Atlas-parent pointer advance**: commit `51922a56` on `codex/kwavers-atlas-integration` (subject `chore(atlas): Advance CFDrs submodule pointer to d58d1fe3`).
3. **(✓ done 2026-07-05) Atlas-parent docs-rounding**: commit `dd676d13` on `codex/kwavers-atlas-integration` (subject `chore(atlas): Sync CFDrs pointer d58d1fe3 + migration push record`).
4. **(✓ done 2026-07-05) Atlas-parent ADR authoring + cross-reference footers**: this single docs commit lands ADR 0010 + updates ADR 0005 / 0007 with `See also:` / appended `Relates to:` lines pointing at ADR 0010.
5. **(next) Inner tag creation + push**: `git -C D:/atlas/repos/CFDrs tag -a cfdrs/atlas-migration-push/batch2 d58d1fe3 -m "<see Context>"` + `git -C D:/atlas/repos/CFDrs push origin codex/cfdrs-atlas-migration --tags`. Step 5 is staged separately from step 4 because tags are NOT commits and shouldn't ride on a docs commit.

## Out of scope

- Tagging the Atlas-parent-side commits (`51922a56`, `dd676d13`, this ADR authoring commit). The Atlas-parent is the ceremony repo, not the audit point; ceremony commits are documented in this ADR's `## Context` enumeration and discoverable via `git log --grep='cfdrs'`.
- Merging `codex/cfdrs-atlas-migration` into `main` in the inner CFDrs repo. The Atlas-parent submodule pointer advance to `d58d1fe3` already makes the work product visible to consumers of the Atlas checkout; the inner `main` merge is a CFDrs-side peer-claim concern, separate from the Atlas pointer-advance ritual.
- Pushing the `cfdrs/atlas-migration-push/batch2` tag without also pushing the branch. The convention includes both `git push origin codex/cfdrs-atlas-migration --tags` as a single command so the branch and tag reach the remote together.
- Pre-creating equivalent tags for batches #1 / #3 / #4 / #5 / #6. The convention's per-batch name pattern is documented in this ADR but each tag is authored at its own batch closure per §"Per-batch name pattern".
- Annotating this ADR with a `BREAKING CHANGE:` footer. No semantic change is enforced by this ADR.
- The CFDrs-internal `Cargo.toml:38-41` strip of `nalgebra 0.33 [serde-serialize]` / `nalgebra-sparse 0.10` / `num-traits 0.2` / `serde-serialize` feature — already consumed in commit `d58d1fe3`. Documented in `repos/CFDrs/CHANGELOG.md` not in this ADR.
- The `cargo semver-checks release -p cfd-math` per-crate semver classification. Filed under the cumulative Atlas-provider migration audit, not this ADR.
- Independent review of the inner CFDrs commit `d58d1fe3` (the migration push's full 771-file diff). Filed under the peer-claim stream; this ADR anchors the Atlas-parent-side closure, not the inner-diff quality.
- Future migrations that don't follow the Atlas-provider migration push shape (e.g., ad-hoc bug fixes, refactors that aren't tied to a CR-class provider-SSOT rebind). Such changes follow the per-repo conventional `fix(<crate>):` / `feat(<crate>):` subject pattern and do NOT consume an `atlas-migration-push/batchN` tag.
