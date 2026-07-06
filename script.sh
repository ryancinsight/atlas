set -e
cd 'D:/atlas'
PREHEAD=$(git rev-parse HEAD)
echo '=== PRE-HEAD: '$PREHEAD
echo
echo '=== UNTRACKED inventory to commit ==='
git ls-files --others --exclude-standard
echo
echo '=== Backlog OOS append already applied? ==='
grep -c 'Atlas-root working-tree dirty triage' backlog.md || echo '(not present)'
echo
echo
echo '########## COMMIT 1/6: ADRs 0003 + 0006 ##########'
git add 'docs/adr/0003-secure-accelerator-parallelization.md' 'docs/adr/0006-eunomia-complex-csr-ssot.md'
git diff --staged --stat
git commit -m 'docs(atlas): Add ADR 0003-secure-accelerator-parallelization + 0006-eunomia-complex-csr-ssot

- lands two untracked ADRs that fill pre-existing sequence gaps between
  ADR 0002 and ADR 0010. Both are real Atlas-meta architect-decision
  records (ADR 0003 = 197 lines Proposed; ADR 0006 = 298 lines Approved)
  that previously sat untracked at atlas-root since their original
  authoring dates (0003 = 2026-06-16; 0006 = 2026-07-05). No edits to
  file content; the file system is the source of truth.
- ADR 0003 lays out the single-owner CUDA context pattern for
  inter-process device-init race prevention (moirai lock-free owner
  election + melinoe branded intra-process sharing + hephaestus GPU
  work queue handoff). Status: Proposed; the GPU/accelerator substrate
  was superseded by ADR 0001 (moirai unified scheduler) ratification.
- ADR 0006 ratifies eunomia::ComplexField::zero()/::one() defaults as
  the SSOT swap-in for num_traits::Zero on kwavers-math csr.rs
  (CR-EUNOMIA-COMPLEX, Path B). Status: Approved 2026-07-05.
- Identifies ADR 0006 as the per-batch num_complex::Complex<T>
  migration convention that Batch #2 (CFDrs) consumed and Batch #1
  (kwavers-solver Rayon -> Moirai) will inherit on the csr.rs path.

Refs: repos/kwavers/backlog.md Phase-1B TODO; ADR 0005 (eunomia scalar
SSOT); docs/pr/eunomia-complex-field-zero-one.md (companion PR draft).'
HEAD1=$(git rev-parse --short HEAD)
echo 'HEAD after C1: '$HEAD1' ('$(git rev-parse HEAD)')'
echo
echo '########## COMMIT 2/6: 3 mnemosyne technical audits ##########'
git add 'docs/audit/2026-06-27-mnemosyne-topological-audit.md' 'docs/audit/2026-06-27-mnemosyne-workspace-bloat-audit.md' 'docs/audit/2026-06-27-mnemosyne-global-alloc-macro-audit.md'
git diff --staged --stat
git commit -m 'docs(atlas): Record 3 mnemosyne technical audits (2026-06-27 batch)

- lands three untracked mnemosyne audit artifacts that were authored on
  2026-06-27 by the cross-crate topological survey and never committed:
    * 2026-06-27-mnemosyne-topological-audit.md (191 lines) \
      Cluster verdict: Heap/tier/tiered-backend triple is already SoC-separated \
      by the Layered Façade pattern; the only real residual target is the
      TieredHeap routing boilerplate (3x match collapse via route_tier! macro).
    * 2026-06-27-mnemosyne-workspace-bloat-audit.md (212 lines) \
      Cluster verdict: HasSegmentPool lifts from mnemosyne-arena to mnemosyne-core \
      (DIP); mnemosyne-hardened folds to a hardened Cargo feature (SSOT). Both \
      zero codegen / benchmark delta; combined PR with 2 commits recommended.
    * 2026-06-27-mnemosyne-global-alloc-macro-audit.md (341 lines) \
      Cluster verdict: the two unsafe impl GlobalAlloc blocks (Mnemosyne + \
      MnemosyneAllocator<P,B>) in crates/mnemosyne/src/lib.rs are structurally \
      identical mod generic substitution; macro-ize via \
      impl_global_alloc_for_mnemosyne! for -80 LoC net, zero delta.
- All three are pre-Cluster-1/2/3 deferrals that were authored and
  queued for execution. The actual refactor commits are filed under
  repos/mnemosyne/backlog.md and are out of atlas-meta scope.

Refs: repos/mnemosyne/backlog.md (closed `[arch] Consolidate public heap
construction` row); repos/mnemosyne/gap_audit.md (`[patch] Mark
realloc_copy_grow as inline(always)` row for shared slow-path context).'
HEAD2=$(git rev-parse --short HEAD)
echo 'HEAD after C2: '$HEAD2' ('$(git rev-parse HEAD)')'
echo
echo '########## COMMIT 3/6: 2026-07-05 atlas-migration audit ##########'
git add 'docs/audit/2026-07-05-kwavers-cfdrs-ritk-atlas-migration-audit.md'
git diff --staged --stat
git commit -m 'docs(atlas): Add kwavers-CFDrs-RITK Atlas-migration audit (2026-07-05)

- lands the live-counts snapshot that maps the kwavers / CFDrs / ritk
  coexisting-with-Atlas-providers state into a human-readable roadmap.
  Distinct from the three 2026-06-27 mnemosyne technical audits: this
  is a status/roadmap tracker (25 sections including 1.1 workload table,
  1.2 allowlist drift per crate, 1.3 ritk Burn-token hits ranked, 1.4
  workspace legacy deps remaining, .. 6 cross-crate PM artifact
  crosslinks), regenerated periodically from
  `cargo run -p xtask -- legacy-migration-audit` /
  `burn-migration-audit` invocations.
- Locked-down numbers (as of 2026-07-05):
    kwavers: 22 manifests w/legacy, 1681 source files w/legacy tokens, \
      19 new allowlist-drift entries, 27 stale `already migrated` rows.
    CFDrs:    6 manifests w/legacy, 76 source files w/legacy tokens, \
      1 new allowlist-drift entry (cfd-1d/src/solver/core/vector_bridge.rs).
    ritk:    27 manifests w/legacy, 671 source files w/legacy tokens, \
      1 new allowlist-drift entry (ritk-image/src/lib.rs).
- 8 Atlas-side extension requests (CR-class items) are surfaced as
  blocked-by anchors for kwavers Batch #1 / #4 + ritk Batch #3 + CFDrs
  Batch #2 secrets. None of these are owned by atlas-meta; each is
  filed under its owning provider-repo backlog.

Refs: repos/kwavers/xtask/legacy_surface.allowlist;
repos/CFDrs/xtask/legacy_surface.allowlist;
repos/ritk/xtask/burn_surface.allowlist.'
HEAD3=$(git rev-parse --short HEAD)
echo 'HEAD after C3: '$HEAD3' ('$(git rev-parse HEAD)')'
echo
echo '########## COMMIT 4/6: feat(eunomia) PR draft ##########'
git add 'docs/pr/eunomia-complex-field-zero-one.md'
git diff --staged --stat
git commit -m 'docs(atlas): Add eunomia-complex-field-zero-one PR draft

- lands the eunomia-side PR draft that realizes ADR 0006 §1 (the
  ComplexField::zero() / ::one() defaults supporting kwavers-math
  csr.rs rebind). Tracked on branch codex/eunomia-complex-field-zero-one
  in repos/eunomia; this is the human-readable PR description, not
  the impl commit itself.
- Doc-only record of intent: the PR diff lives in repos/eunomia
  parent branch and lands through the eunomia-side claim stream
  (peers: codex + ryancinsight). Atlas-meta keeps this artifact
  because it cross-walks the eunomia-cluster extension request the
  atlas CR-4 infrastructure audit surfaces.

Refs: ADR 0006 §1 (ComplexField additive defaults);
docs/adr/0006-eunomia-complex-csr-ssot.md Status: Approved 2026-07-05.'
HEAD4=$(git rev-parse --short HEAD)
echo 'HEAD after C4: '$HEAD4' ('$(git rev-parse HEAD)')'
echo
echo '########## COMMIT 5/6: scripts/_wire_cpu_impl.py chore ##########'
PYTHON_SYNTAX=$(python3 -c "import ast,sys; ast.parse(open(r'scripts/_wire_cpu_impl.py').read()); print('OK')" 2>&1)
echo 'Python syntax check: '$PYTHON_SYNTAX
git add 'scripts/_wire_cpu_impl.py'
git diff --staged --stat
git commit -m 'chore(atlas): Add scripts/_wire_cpu_impl.py coeus-ops codemod

- lands a 318-line Python utility that batch-inserts 16 new PoolOps
  method impls (max_pool1d + back, avg_pool1d + back, adaptive_{max,
  avg}_pool{1,2,3}d + back) into the PoolOps blanket impl block at
  coeus-ops/src/backend_ops/cpu_impl.rs. Targets the G-036
  MS-189a/189b pool op family identified by the coeus-ops gap audit.
- The script locates a unique 2-line anchor (avg_pool3d_backward
  body close + impl-block close) and inserts the 16 new methods
  between them while preserving CRLF line endings (Windows).
- Idempotent: anchor uniqueness-asserted; assertion fails the run if
  the file has drifted from the structural fingerprint. Not yet
  executed against the live coeus-ops tree (that is the coeus-side
  claim stream'\''s call). This commit records the script itself, not
  the coeus-ops source diff.

Refs: repos/coeus/backlog.md (coeus-ops Pool op family);
repos/coeus/gap_audit.md (G-036 row).'
HEAD5=$(git rev-parse --short HEAD)
echo 'HEAD after C5: '$HEAD5' ('$(git rev-parse HEAD)')'
