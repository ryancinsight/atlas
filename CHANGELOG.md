# Changelog

## Unreleased

- Close `ATLAS-VERSION-COHERENCE-SWEEP-2026-09-30`. Its outcome — the
  overlay reports **aligned** on the recorded pins — now holds: every
  consumer of the Leto 0.50.0 cohort admits it and locks it. `kwavers`
  (#1100, `4a8e1aa2`) widened its requirement, `CFDrs` (#565, `4b3ec85e9`)
  moved the gaia-mesh lock with it, and `coeus` (#664), `ritk` (#937),
  `asclepius` (#122, `1dbc3459`) and `metis` (#544, `d3f6c5a7`) had already
  landed. Verified at the pushed pins: `scripts/atlas-stack-overlay.py check
  --pinned` reports "stack aligned: requirements satisfiable and locks match
  the local trees", `scripts/atlas-version-guard-sweep.py` reports the
  toolchain preflight, coherence, governance and provider-integration guards
  clean, and `scripts/atlas-pin-drift.py` reports 28 members within one sweep
  with only the ritk waiver. The remaining pin work is the per-sweep advance,
  not a version-coherence gap.

- Admit Leto 0.50.0 across the last three lagging consumers and advance
  their pins. `asclepius` (`1dbc3459`, asclepius#122) and `metis` (`d3f6c5a7`,
  metis#544) are lock-only moves — Coeus `7e1ded59` with Apollo `b7bffe1c`,
  and Gaia-Mesh `4c69a978`, each onto the default-branch revision whose Leto
  bounds admit 0.50, with Leto itself at `6483eac3` — while `kwavers`
  (`4a8e1aa2`, kwavers#1100) widens its requirement from `>=0.47.1, <0.49.0`
  to `>=0.47.1, <0.51.0` and moves the same six-provider cohort in one lock
  delta. `scripts/atlas-stack-overlay.py check --pinned` now reports "stack
  aligned: requirements satisfiable and locks match the local trees", the
  version-guard sweep leaves no requirement that excludes 0.50, and
  `scripts/atlas-pin-drift.py` reports all 28 members within one sweep.

- Hold the ritk pin at `596b7afc` and retire the metis pin waiver. ritk#943
  grows `crates/ritk-snap/src/presentation/native_session/window_controls/
  layout/construction.rs` from 498 to 507 lines, so the default tip raises
  `oversized_files` 38 -> 39 and the conformance ratchet rejects it;
  `scripts/pin-drift-waivers.json` now records that regression and the file
  split that reopens the pin. The metis entry it replaces was re-measured
  against that member's current default and no longer reproduces (0
  unresolved references, no `checklist.md`), so it was deleted rather than
  renewed.

- Two more `ATLAS-ARCH-008` sites in kwavers. #1107: the IR-drop solver's
  private `Vec<(usize, f64)>`-per-node power-net graph is one CSR pair
  (neighbour run + conductance run behind an offset table) built in two passes
  from the edge list; each node's edges are inserted in the original order, so
  the Gauss–Seidel summation order is unchanged and the result is pinned
  bit-exactly (`4591621414013336774`). #1108: `gaussian_elim_flat` and
  `symmetric_eigenvalues` in `kwavers-physics` now work on one row-major block
  each (strides `n + 1` and `n`) instead of re-jagging a flat input per solve,
  with the singular values and L-curve residual/solution norms pinned
  bit-exactly, and the pivot search's bare `unwrap` replaced by an invariant
  `expect`. Verified: 5 `ir_drop` tests, 1577 kwavers-physics tests, strict
  clippy and fmt clean; the push gates measured `kwavers/scattered_containers
  54 -> 51` then `54 -> 50` and `unwrap_production 183 -> 181`, with 0
  regressions. No wall-clock claim.

- Hold the genetic search's candidate batches in one buffer and one round-robin
  (CFDrs#569), another `ATLAS-ARCH-008` site. `cfd-optim`
  built a `Vec<BlueprintCandidate>` per parent for its mutations, crossovers and
  local perturbations — four production `Vec<Vec<_>>` sites rebuilt every
  generation — and walked them with a round-robin that existed twice (the
  helper plus an open-coded copy in the seed path). A new `CandidateBatches`
  leaf module stores every batch back to back behind an offset table,
  appending batch by batch so no jagged intermediate is built, and the one
  helper now serves both walks. The full-optimizer oracle, the mutation and
  crossover validity oracles and `cfd-optim`'s 109 unit tests pass; the push
  gate measured `CFDrs/scattered_containers 24 -> 18` with 0 regressions. No
  wall-clock claim.

- Count board items with no `milestone:` assignment once a repository carries a
  `backlog/milestones.md` ladder, closing `ATLAS-BOARD-LINT-MILESTONE`. The
  lint's schema check had four classes (status set, anchors, priorities,
  checklist files) and no milestone class, so the ladder rollout could not
  tell which items its ladders had left unassigned. `MILESTONE_LINE` mirrors
  `PRIORITY_LINE`'s two placement forms — its own field line or a
  `;`-separated one (`- Status: todo; priority: feature; milestone: M-1.0`) —
  and adds the bold `**Milestone:** M-x` label one member's ladder used. The
  new `board_items_without_milestone` class is gated on the ladder file, so a
  repository with nothing to assign to counts 0; the value is the ladder's
  free-form `M-<slug>`, so unlike `priority:` there is no closed set and only
  presence is counted. The conformance baseline is regenerated from the
  recorded pins in the same change, as the generator contract requires: the
  class measures 50 across the stack (`horae` 14, `iris` 9, `hyperion` 8).
  Two new tests pin both spellings landing and a third item counting once, and
  the detector's non-vacuity was checked by disabling the regex (1 expected vs
  3 reported). `scripts/tests/test_atlas_board_lint.py` +
  `test_atlas_conformance.py`: 236 tests pass; the root board still lints
  clean and `atlas-conformance.py check` reports 0 regressions.

- Close `ATLAS-RITK-SPATIAL-FINITE-INVERSE` and delete the item: ritk
  `6414a16a` makes `try_inverse` reject a non-finite input entry up front and
  then check every pivot, every normalized row entry and every updated entry
  of both the working matrix and the inverse, so a NaN pivot — which made the
  old `pivot_value < threshold` comparison false and returned `Some` of a
  NaN-filled matrix — is now refused. The pivot threshold and elimination
  order are unchanged, and `grid_geometry.rs` needed no code change because
  `CartesianGridGeometry::new` already maps `None` to
  `NonCartesianGrid::SingularDirection`. The item's original oracle claimed a
  `2^1023`/`2^-1023` diagonal stays accepted; it does not and never did,
  because `2^-1023` sits below `PIVOT_SINGULARITY_THRESHOLD`, so the landed
  tests pin the real boundary (accepted at `2^-9`, refused at `2^-1023`).
  ritk-spatial: 101 tests, strict clippy and rustfmt clean.

- Close `ATLAS-ATHENA-AMG-VCYCLE-SLICES` and delete the item: athena's default
  branch now runs the V-cycle on the borrowed views Athena passes, in two
  commits — `5e1722a` moves the smoother fixtures into `smoothers/tests.rs`,
  and `9352b5c` turns `Preconditioner::apply` into a call into a `cycle`
  generic over a `Vector` seam that `[T]`, `Array1` and `ArrayViewMut1` all
  implement, with the new `vector.rs` giving contiguous operands a slice fast
  path through `dense()`. The two O(n) boundary copies and the
  `athena_boundary` buffer cache are gone while the public
  `apply_to(&Array1, &mut Array1)` signature and the patch scope stay put.
  The branch variant that removed the trait outright (PR #175) was closed in
  favour of this one; the record follows the landed mechanism, not the
  closed branch.

- Widen the board lint's duplicate-id gate to the item-id grammar instead of
  the `ATLAS-` prefix. `scripts/atlas-board-lint.py` matched
  `^#{2,3}\s+(ATLAS-[A-Z0-9-]+)`, so on a member board whose ids are named
  after the member the hard gate reported "all item ids unique" over any
  duplicated `ATHENA-*` or `KWAVERS-*` heading; a judge's negative control
  reproduced it with two `ATHENA-GITCONFIG-20261113` headings and exit 0. One
  `ID_BODY` grammar now feeds `HEADING_ID` (the duplicate gate and the
  `--next` suggestions) and `ITEM_HEADING` (the schema scan), beside the
  `ATLAS-`-only `HEADING_ANY` that the dangling-reference scan keeps by
  design. Tests in `scripts/tests/test_atlas_board_lint.py`: a duplicated
  member-family id is reported with both lines and `main` exits 1, distinct
  member-family ids and prose headings are not flagged, a duplicate split
  across two item files is caught, and `next_free` reads an `ATHENA-*`
  family; 39 tests pass.

- Regenerate the ARCH-008 pinned oracle after the gitlink advances:
  `scripts/oracles/arch-008-production-sites.txt` now records 169 production
  sites (158 test/bench, 327 total, from 177/335) and
  `make verify-scattered-oracle` passes. The eight-site drop is the five
  landed deliveries plus one provider conversion: apollo `a48821db` removes
  the four `Vec<Vec<u64>>` twiddle levels from
  `apollo-ntt/.../kernel/circle.rs` (70, 74, 142, 150), kwavers `93f6fecd5`
  removes the two `Vec<Vec<f64>>` cost matrices from
  `kwavers-analysis/.../ulm/tracking/tracker.rs` (63, 170), CFDrs `74e269a5`
  folds the three element-to-node copies into one `ElementNodes` (three
  sites out of `assembly.rs` and `element.rs`, one new site in
  `element_nodes.rs:51`), and leto `bd349c5e` had already flattened
  `amd_order`'s adjacency so `leto-ops/.../sparse/amd.rs:126` is gone.
  ritk `09c254e4` shifted `ritk-mgh/src/reader/mod.rs` (69 to 83) and
  `ritk-mif/src/reader.rs` (282 to 300) without converting either
  `Vec<Vec<f32>>`.

- Advance the ritk gitlink to `596b7afc`, the merge of ritk#946, which moved
  that member's `main` 13 commits past the recorded pin while pin drift
  allows one; `scripts/atlas-pin-drift.py` now reports all 28 members within
  one sweep. The advance leaves the ARCH-008 census unchanged at 169
  production sites (158 test/bench, 327 total), so
  `scripts/oracles/arch-008-production-sites.txt` is untouched and
  `make verify-scattered-oracle` still passes.

- Close ATLAS-V1-MILESTONE-LADDERS-001 and delete the item: all 28 members
  hold a 1.0 ladder at their default branch — the 12 original
  `backlog/milestones.md` ladders plus eunomia, aequitas, ritk, helios,
  metis, CFDrs and gaia merged during the rollout wave, and hermes, apollo,
  athena, ares, coeus and prometheus carrying member-native ladder shapes
  with milestone-tagged boards. The recorded lesson rides the closure:
  `## M-1.0` rung headings parse as board items because `M-1` matches the id
  grammar, so rungs are written `## Milestone M-1.0` where a member runs the
  board lint.

- Close ATLAS-PUB-002 and delete the item: RITK's caller was the last
  outstanding book workflow and Deploy mdBook run `43534192587` (2026-11-14)
  succeeded on main at `e4bd3567` through the shared caller pinned at
  `book-pages.yml@20c93980`, with CFDrs, helios and kwavers callers already
  in place (`bb505e5e`, `6ed29a95`, `ddee9af1`). ATLAS-PUB-005's dependency
  line now names the landed caller rather than the deleted id, and
  ATLAS-PUB-012 returns to `todo` because the board's default-branch
  statuses are `todo` and `blocked` only while its merge is outstanding.

- One element-to-node map for CFDrs's spectral meshes and global assembly
  (CFDrs `74e269a5`, CFDrs#568), three more
  sites of `ATLAS-ARCH-008`. `SpectralMesh1D` and `SpectralMesh` each held a
  `Vec<Vec<usize>>` element→node map and `GlobalAssembly` held a third — `E + 1`
  heap blocks for `E` elements, a pointer hop before any element's nodes, and
  the same offset arithmetic three times. They now share one `ElementNodes`
  leaf type (index buffer behind an ascending offset table), both meshes build
  it through one `from_uniform` formula (`element * (nodes_per_element - 1) +
  local_node`, the layout that shares boundary nodes), and the assembly
  flattens its caller-supplied lists once. Both meshes also drop their separate
  `num_elements` field in favour of the count the map owns. Public surface is
  unchanged and 17 spectral tests, strict clippy and fmt pass. No wall-clock
  claim.

- Hold the ULM assignment problem in one row-major matrix (kwavers
  `93f6fecd5`, kwavers#1106), two more sites of `ATLAS-ARCH-008`. The
  multi-frame tracker built its cost matrix as `Vec<Vec<f64>>` (one heap block
  per track) and `hungarian` copied it into a second square `Vec<Vec<f64>>`
  padded to `max(m, n)`; the solver touches that matrix `O(sz²)` per
  augmentation round through two pointer hops per element. The cost matrix is
  now one buffer with stride `n`, the padded square one buffer with stride
  `sz` (row reduction walks `sz`-sized slices), and `hungarian` takes `&[f64]`
  with the stride documented. Assignment results are unchanged — the identity,
  minimum-cost, linear-motion, crossing-bubble and termination oracles pass —
  and kwavers-analysis's 26 ULM tests, strict clippy and fmt pass. No
  wall-clock claim: allocation/locality shape only, no paired benchmark.

- Flatten the circle FFT's twiddle levels (apollo `a48821db`, landed as
  apollo#718), one site of `ATLAS-ARCH-008`. The circle
  domain carried its `x` twiddles as one `Vec<u64>` per level in each
  direction — a pointer table plus a heap block per level, and a transform
  that followed one pointer per butterfly pass. Those four sites
  (`apollo-ntt` `kernel/circle.rs` lines 70, 74, 142, 150) are now two
  `LevelTwiddles`: one contiguous value buffer behind an ascending offset
  table per direction, in a new leaf module `kernel/circle/twiddles.rs`, with
  construction filling the flat buffer directly instead of a jagged
  intermediate. Arithmetic, level order and twiddle values are unchanged — the
  exact round-trip and basis-evaluation oracles pass untouched — and a new
  structural test pins level count, per-level lengths (`N/4, N/8, …, 1`) and
  the `N/2 − 1` value total for `n = 2^1..2^8`. `apollo-ntt`'s 38 tests, strict
  clippy and fmt pass; the `circle` bench completes inside its 60 s budget
  (19.8 s). No wall-clock win is claimed — no paired baseline was taken.
  The census keeps listing those sites until the `repos/apollo` gitlink
  advances, because `--pinned` reads the recorded revision.

- Refuse non-finite direction inverses in `ritk-spatial` (ritk `6414a16a`,
  ritk#941), delivering the code half of
  `ATLAS-RITK-SPATIAL-FINITE-INVERSE`. `Direction::try_inverse` rejected only a
  pivot below `PIVOT_SINGULARITY_THRESHOLD`, so a NaN pivot made the comparison
  false and the routine returned a NaN-filled matrix; arithmetic that overflowed
  mid-elimination likewise surfaced as a plausible-looking inverse. It now
  rejects a non-finite input entry up front and checks every pivot, normalized
  row entry, and updated working/inverse entry as it is computed, with the
  threshold and elimination order unchanged. `CartesianGridGeometry::new`
  already maps `None` to `NonCartesianGrid::SingularDirection`, so it reports
  that instead of keeping an invalid index/world pair. Covered by the 42
  non-finite input cases across ranks one to three plus overflow, pivoted-shear
  and dyadic-diagonal fixtures; ritk-spatial's 101 tests, strict clippy and fmt
  pass. One oracle claim was corrected rather than implemented: a `2^-1023`
  diagonal is below the unchanged threshold and is refused as singular, which
  the tests now pin. The ritk pull request and the gitlink advance remain open.

- Run Athena's algebraic-multigrid V-cycle on borrowed slices (athena
  branch `build/athena-leto-049`), delivering the code half of
  `ATLAS-ATHENA-AMG-VCYCLE-SLICES`. `athena-leto`'s
  Athena `Preconditioner::apply` copied the residual view into an owned
  `Array1`, ran the cycle, and copied the result back out, and carried a
  cached `athena_boundary` buffer pair to do it; the cycle and its level
  helpers only ever needed element slices. `v_cycle`, both smoothing
  dispatches, and `sparse_apply_into` now take `&[T]` / `&mut [T]`, the
  per-level workspace holds plain `Vec`s, and the seam hands the caller's
  views straight through, so a preconditioner application makes no copy in or
  out and the boundary cache is deleted. Each smoother keeps one sweep kernel
  with its public owned `apply` as a thin adapter, so no public signature
  moves and the change stays patch-scoped. Equivalence is pinned by the
  pre-change cycle's digest on a three-level SPD fixture plus an
  adapter-versus-kernel sweep oracle; no wall-clock win is claimed, because
  the two removed passes were `O(n)` beside the cycle's `O(nnz)` sweeps.
  Athena's workspace suite, `cargo clippy -D warnings`, and `cargo fmt
  --check` pass. The gitlink advance awaits the member commit reaching the
  Athena default branch.

- Widen every registered consumer's `leto` / `leto-ops` requirement to admit
  the 0.48 provider line: apollo, ares, athena, CFDrs, coeus, gaia, helios,
  hephaestus, kwavers, prometheus and ritk now unify with the local Leto 0.48.0
  working tree under the stack overlay. Each lower bound is unchanged and no
  `Cargo.lock` is rewritten, because 0.48.0 is not yet published: standalone
  `--locked` builds keep resolving the recorded provider revision. The
  remaining version lags are Eunomia 0.11 / Hermes 0.9, not Leto.

- Advance all 28 stack gitlinks to their fetched default heads plus three
  provider improvements: leto 0.48.0 adds `concat_into` / `stack_into`
  zero-copy caller-owned assembly, `CooMatrix::into_csr`, and a flattened
  contiguous `amd_order` adjacency buffer (single allocation, no per-vertex
  heap headers); hermes 0.10.0
  adds `Copy` for borrowed sparse views and bounded bench budgets;
  mnemosyne fixes a flaky leak-detector temp-dir race. Version lags for
  eunomia 0.11 / leto 0.46-0.47 / hermes 0.9 remain as consumer-advance
  requirements on the overlay.

- Catch a quantity accessor whose name claims a unit the returned value does
  not carry: the Aequitas audit compares the final scale token of a public
  getter's name with the canonical unit of the quantity it returns, so an
  accessor named `..._mm` that returns a metre-valued `Length` is reported.
  Compound unit names (`..._m_per_s`) are not read as a single scale, and the
  audit's subject is the member set `.gitmodules` records, so a local directory
  under `repos/` is no longer measured as a cohort outlier.

- Keep the crate release-identity tests hermetic on a Windows host: the
  fixture repository pins `core.autocrlf=false` and the committed-content
  comparison normalizes line endings, so the byte-identity proof no longer
  fails on the host's line-ending translation alone.

- Materialize CI member worktrees concurrently after serial registration, not
  only their initial clones. Freeze committed pins/mappings, reject existing
  or overlapping destinations, preserve root state, and retire owned children
  on failure/interruption through the existing process-tree supervisor. Retain
  all Python tests, timeouts, full member history and blob filtering.

- Fix the shared cast checker's optional `--command-cwd` interface for Clippy,
  metadata and package enumeration. Preserve the export directory default and
  cast/compiler failure handling, and record the compiler selected from the
  actual execution directory. This prerequisite leaves #551's provider cohort,
  hooks, pins, overlay, locks and required gates unchanged. Materialize recorded
  Python-CI members with parallel blobless clones and full history so checkout
  does not consume the unchanged test-job budgets.

- Integrate the independently reviewed TF conversion source boundary in parity
  program 2026-10-26.12, with lossless selected captures, typed live owner/API
  joins and input-sensitive rounding/cotangent controls. Preserve all 30 UNRUN
  cases, ten open gaps, existing mappings and prior source-policy editions;
  no package version, public scope or execution/release qualification changes.

- Preserve the two independently accepted public-surface source packets in parity
  program 2026-10-26.11 with lossless selected captures, 498 exact reference joins,
  typed provenance/owner guards and portable witnesses. All classifications,
  required functionality, mapping stages and runtime/release credit are unchanged;
  no public-scope admission exemptions or package version changes. Reconcile the
  user-approved SAME-PR #551 replacement while retaining historical ownership,
  unqualified delivery gates and Leto heavy-slot ownership.

- Add repaired Torch native dtype source definitions to parity program
  2026-10-26.10, with lossless finite tables, typed source/owner/status guards
  and input-sensitive complex/gradient analytical controls. All 66 framework
  cases and 14 wider gaps remain open; prior framework captures stay unchanged.
  Merge the NumPy selector repair and use its shared typed resolver for Torch
  source-row identity checks without retaining a local compatibility alias.
  Reject weakened conditional evidence/gap obligations and normalize malformed
  scalar-access errors after independent canonical review; preserve source bytes.

- Add the accepted NumPy native dtype source supplement to parity program
  2026-10-26.9 with lossless source capture, independently reconstructed symbolic
  relations, exact source/role guards and 47 unrun targets. Preserve JAX history,
  existing API owners and mapping stages; no package version changes.

- Define the versioned four-framework functional-parity program, release-pinned
  candidate API inventories, provider evidence reconciliation, capability owners,
  repository exit criteria and dependency-ordered work packages. Add the parity
  traceability/evidence validator with rejection tests. Extraction and all
  per-API semantic mappings remain incomplete; no package version changes.

- Advance the Atlas gitlinks for the six members whose provider-cohort pull
  requests merged, and regenerate the stack overlay from the recorded stack.
  Tyche, RITK, Harmonia, Prometheus, Coeus and Kwavers move to their merged
  revisions -- Consus 0.4.0 for the first two, the 0.10 cohort for the rest.
  Only merged members are advanced: a gitlink records a published revision,
  and an open pull request's head is not one. The pull requests merged by
  rebase, so the revision recorded is the default branch's tip, and the
  proof that it carries the change is per file the pull request touched -- a
  tree-wide comparison also catches whatever else landed on the default
  branch since, which says nothing about this change.
- The regenerated overlay drops the dead `coeus-leto` mapping, which failed
  every cargo command beneath the stack root, and carries `coeus-cpu` in
  both Coeus sections and `consus-zip` in both Consus sections: 42 patch
  sections against the 22 the dead mapping left behind. The dangling-path
  check now reads the manifest set the generation read rather than the
  filesystem: a pinned or tips read describes the recorded stack, so a path
  the recorded stack carries is present even when the checkout behind it
  does not have it, and the filesystem test reported
  `repos/consus/crates/consus-zip` as dangling when it was not.
  Recorded under ATLAS-COESUS-CPU-OVERLAY and
  ATLAS-VERSION-COHERENCE-SWEEP-2026-09-30.

- Identify a first-party package by its member, not by its name alone, in the
  version-guard coherence scan. The scan indexed every package in the stack
  under its bare name, so two members declaring a package with the same name
  read as one package at two versions -- and every member carries an `xtask`
  whose version drifts. The scan refused the whole stack on
  `repos/apollo/xtask/Cargo.toml` before it reported a single real
  requirement, and the real requirement was invisible behind it. The index is
  now keyed by member and name, and a dependency resolves through the member
  its `git =` URL or `path =` names, which is the member that says which
  package it means. Two versions of one package inside one member still
  refuse: the member disambiguates a name between members, not within
  itself. Two new tests pin both rules. The gate now reports the genuine
  cohort lag -- 1247 first-party requirements over 269 manifests, with
  Athena's `hephaestus-core = ">=0.22.2, <0.26.0"` range among them, which
  the old refusal had hidden.
  Recorded under ATLAS-VERSION-COHERENCE-SWEEP-2026-09-30.

- Read the stack overlay's member manifests from the recorded stack instead of
  from whichever branch a developer has parked a member on. The generator
  gained `--pinned`, which reads each member's manifests from the gitlink
  commit `HEAD` records, and `--tips`, which reads them from the member's
  fetched default branch. The first makes a generation reproducible from the
  recorded stack without a checkout; the second measures the provider graph a
  gitlink advance would record, which is what told the version-coherence
  sweep that four members had already advanced past their Atlas pins. A
  failed `git ls-tree` now raises naming the member and the revision instead
  of yielding an empty file list, so a member cannot quietly leave the
  overlay behind a green generation. Three new tests pin the contract: a
  pinned read that ignores a checkout the gitlink does not name, a tips read
  that follows the default branch, and the loud failure. Recorded under
  ATLAS-COESUS-CPU-OVERLAY and ATLAS-VERSION-COHERENCE-SWEEP-2026-09-30.

- Read `cargo metadata` once per unchanged workspace in the build-identity
  gate. The answer is a pure function of the workspace's manifests and its
  lockfile, but the gate asked for it sixty-two times over four manifests
  per test — the dependency snapshot, the package layout and the artifact
  owners each wanted one — and every ask cost a cargo process. The read is
  now keyed by the manifest and cargo's directory and validated by the
  content of every file that decides the answer, so a changed dependency
  graph is still read and the identity still sees it. One traced test: 309
  subprocesses and 56.11 s of child time before, 251 and 39.50 s after,
  with `cargo metadata` down from 62 calls to 4. A new test file pins the
  contract. Recorded under ATLAS-IDENTITY-SUITE-RUNTIME.

- Stop the Atlas Python fixtures from leaking directories under the OS temp
  directory: every `mkdtemp` fixture in `scripts/tests/` now removes its tree
  through the shared read-only-safe helper instead of
  `shutil.rmtree(ignore_errors=True)` — which swallowed the refusal to
  delete a fixture's read-only Git objects — or no cleanup at all. That
  covers the CRLF detector's repository fixture, the safety census's
  repository fixture, the build-claim and queue-order fixtures, the
  shared-target fixture whose cleanup was a no-op, and the lockfile
  checker's symlink fixture. A new oracle,
  `scripts/tests/test_atlas_tempdir_leaks.py`, runs those fixture suites
  against a private temporary root and asserts that root is empty
  afterward, so a suite running concurrently on the same host cannot be
  blamed for a tree it did not create; a second oracle reads the sources
  and fails on any fixture that removes its own tree with
  `ignore_errors=True` or never removes it, in the spellings this
  repository's fixtures use. Neither is vacuous: with one
  cleanup reverted the first fails and names the leaked trees, and the
  second names the reverted fixture in every form the six converted
  fixtures used -- a direct `rmtree` call carrying `ignore_errors=True` as
  the keyword or in `rmtree`'s positional slot, the same removal handed
  to `addCleanup`, a `weakref.finalize` that passes `True` as
  `rmtree`'s `ignore_errors`, and a fixture with no cleanup at all. A
  removal of a path inside the tree is not a leak and is not flagged.
  Recorded under ATLAS-TEST-TEMPDIR-LEAKS.

- Fix the conformance gate's crash on a root push: `link_snapshot` took a
  fixed directory per checkout, so materializing one checkout twice into one
  scratch — the pushed content and the baseline config root — collided with
  `FileExistsError [WinError 183]` on `<scratch>/atlas` and aborted the
  member scan, which the ratchet then read as a phantom raise. The snapshot
  now takes a free directory, and the member's identity travels with the
  scan rather than being read back from the snapshot path, which is what the
  sanctioned-root allowance was doing. Reproduced on this Windows host
  (`check --repo apollo --member-path D:/atlas --member-revision HEAD`):
  the error before the fix, a completed scan with unchanged fleet counts
  after it. Recorded under ATLAS-ROOT-CONFORMANCE-MATERIALIZE-CRASH.

- [patch] Verify complete crate archive and exact clean VCS identity before a
  GitHub Release retry can skip both authentication and upload. Consistent
  exact-version absence retains the existing publish path; ambiguous registry
  results fail closed. PR #547 remains gated; immutable comparison fixtures use
  a separate unfiltered origin store for shallow and blobless checkouts.
  Existing validation, SemVer policy and credentials are unchanged.

- [minor] Add opt-in exact package/version cohorts to pending publication.
  Explicit `{}` leaves installation unarmed; planning, publish and tagging
  cannot expand into unrelated pending versions. Existing verification,
  SemVer and trusted-publishing requirements remain unchanged.

- [patch] Close `ATLAS-PYTHON-WHEEL-ATTESTATION-CONTEXT` after
  [#542](https://github.com/ryancinsight/atlas/pull/542) merges as `03f818ce`.
  Workflow lint, conformance, fast/slow scripts and default CodeQL pass;
  four regressions fail before repair, then all 16 workflow tests and 12
  credential-free contexts pass. Independent re-review finds no blocking code
  finding. [Leto #365](https://github.com/ryancinsight/leto/pull/365) selects the
  immutable recipe and merges as `747d0bbb`; its reviewed head passes all 40
  checks and 30 wheel rows. Remove only this completed active backlog item.
  The additional non-required managed scan cannot start its configured model;
  the owner explicitly accepts it as nonblocking. No security setting changes.

- [patch] Keep shared wheel build/value/source validation available to fork
  and Dependabot pull requests without attempting privileged attestation.
  Trusted release attestation is retained; untrusted release mode fails closed.
  Token permissions, platform matrices, tests and time limits are unchanged.

- Compact Atlas's own PM boards under the 1,000-line budget: `checklist.md`
  2,312 → 853 and `gap_audit.md` 10,274 → 772, keeping all 113 open
  checkboxes and all 15 open-marked findings. `backlog.md` 1,896 → 1,100 keeps
  all 147 live items and stays 100 lines over: 147 items need 147 generated
  index lines, 147 own-line anchors and 147 headings before any body.

- Merge Tyche PR #28 and PM closure PR #29 at defaults
  `46f4829ef648cec2b9e44bad3a75aef8ef3c34af` and
  `a2d15f058a29142844396c934362d84ce207d32f`. Exact CI/Pages, post-merge CI
  `32343825023`, Deploy mdBook `32343825746`, dynamic Pages `32343823918`,
  and live Pages HTTP 200 pass; Atlas records the closure gitlink.

- Merge RITK PR #196 at provider default
  `aa48c471ac96eb81869437d84bab439e18d89038` after refreshing the shared Pages
  workflow pin. Exact Rust, Python, and Pages checks pass; post-merge CI
  `32344964253`, Python CI `32344964345`, Deploy mdBook `32344964522`, and live
  Pages HTTP 200 pass. Provider PM closure PR #197 merged at
  `a16a27f24e814cb1e4315d9c44dec4394f0e26b0`; Atlas records that closure
  revision.

- Merge Hermes PR #57 at provider default
  `c5e4c2dc005f215c403bd5b3c66db275bd040afb` after repairing AVX-512
  generic-default compilation by gating the three hardware permute imports per
  scalar backend. Exact rerun `32343803367`, post-merge CI `32344922231`,
  dynamic Pages `32344921591`, and live Pages HTTP 200 pass.

- Merge Mnemosyne book-gate PR #66 at provider default
  `6b0e490752f215782d63f876e85059534e25af54`. Post-merge CI `32344048512`
  passes including Miri; the existing book run `32341400004` and live Pages
  `https://ryancinsight.github.io/Mnemosyne/` HTTP 200 check pass. Atlas records
  the closure gitlink.

- Merge Apollo PR #107 at provider default
  `0c6ffb91ce5d1b68d8da50c6fd12726b7993b1b8` after restoring the
  benchmark-qualified lazy twiddle-cache initialization and documenting the
  four per-site Clippy expectations. Exact CI `32347865828`, counterbalanced
  benchmark `32347865841`, post-merge CI `32348784876`, Pages
  `32348782338`, and live Pages HTTP 200 pass; Atlas records the default
  gitlink.

- Reconcile the publication documentation with the committed provider inventory:
  24 book-bearing registered members carry a book and Pages caller, 17 use the shared
  `mdbook-test` input, and Gaia's custom workflow runs `mdbook test` directly.
  Six remain tracked for executable sample coverage (`apollo`, `coeus`,
  `consus`, `hephaestus`, `ritk`, `themis`). Root docs build and strict link
  checks cover all 24 books; `scripts/atlas-book-gate-audit.py --check`
  mechanically classifies that inventory. Leto remains a separate unmerged
  book-closure residual.

- Merge Aequitas PR #37 at provider default `c0542bf8` after its executable
  book examples and API snippets pass CI `32337268558` and the shared Pages
  build `32337268946`; the pull-request deployment is skipped.

- Merge Horae PR #22 at source `aaed0cff8e777d62fcaff4f20b3347bb1eefa403`
  as provider default `c2e7766847e3ef28125b809d98fe07250acc6cec` after its
  shared-workflow pin checks and book build pass. Post-merge CI, book, and
  Pages deployment runs pass; live Pages returns HTTP 200.

- Merge Hyperion PR #19 at source `5e8d47008e01f401c8d1b464c30e2909ff1a56c8`
  as provider default `719d84e80163b958cc5500b5fa44a5b01095d6d1` after its
  shared-workflow pin checks and book build pass. Post-merge CI, book, and
  Pages deployment runs pass; live Pages returns HTTP 200.

- Reconcile Kwavers to hosted-green default `9cf62aa98364e8f00cba0ca4a5d431b90a0ab55a`;
  Architecture Validation `32333948199`, CI/CD `32333948192`, Legacy Migration
  Audit `32333948196`, and Pages `32333948521` pass. The open queue-contract
  PR #427 remains a separate branch residual.

- Merge Hermes PR #56 at source `932468dac5ef4abadea4bdd12d62b420a4225ba7`
  as provider default `3a39ef16d679dbac9c1a479b2b9c44135e262af3` after its
  executable book examples, SIMD snippet, and benchmark runtime gate pass.
  Post-merge CI, book, and Pages runs pass; live Pages returns HTTP 200.

- Merge Mnemosyne PR #65 at source `a527380a15e8979c3b773a4e9891f1d53b0bc45c`
  as provider default `7003eb3d09a716a91b4560e1810d65970c874daa` after its
  executable allocator examples and Miri gate pass. Post-merge CI, MSRV, and
  book runs pass; live Pages returns HTTP 200.

- Merge the provider-owned PM closure PRs for Horae #23 and Hyperion #20 at
  defaults `a05dbebbb947a627cbe69a9d839fb88cae46e459` and
  `e2dbc9bb28d7f9cbccf354d2a9b278c6231a85d1`; Atlas records both closure
  revisions after their exact documentation-only verification passes.

- Merge Proteus PR #14 and its PM closure PR #15 after the executable book gate
  passes: CI run `32338237653` and Pages build `32338238163` validate both
  included material examples; the pull-request Pages deployment is skipped.

- Integrate Helios PR #67 at provider default `423d6ec9`, including the
  `helios-python` abi3-py39 trusted-publishing workflow and package metadata;
  no PyPI release is performed.

- Record the Kwavers moving-default boundary at `9cf62aa9`: its current
  default-head Architecture and CI/CD gates remain queued, so Atlas retains
  the last verified pointer `b20eb48b`.

- Make the ADR index check fail when an on-disk ADR is absent from `HEAD`,
  with a focused regression covering a matching generated index.

- Extend the default provider-integration audit to all 22 active Atlas domain
  providers, including Harmonia; update its focused inventory and output tests.

- Activate Harmonia in `.gitmodules` and advance its Atlas gitlink to fetched
  default `02ffd14`, preserving the nested peer-owned worktree changes.

- Merge Horae PR #18 at source `cded674` as `0631da0` and Hyperion PR #14 at
  source `b8d4fb8` as `fd752c7`. Their exact-head hosted `verify`,
  `supply-chain`, and shared Pages book-build gates pass; the Atlas gitlinks
  now point to the merged default heads. Horae enables executable mdBook
  samples and Hyperion completes its CI-bound and line-ending cleanup. The
  root conformance baseline records Hyperion's zero measured residuals. The
  Horae RecurseML analyzer error remains report-only. Helios PR #64 remains
  open pending its benchmark regression gate. Post-merge Pages runs
  `32103884266` and `32103884853` deploy both books successfully; live HTTP
  checks return 200 with the expected titles.

- Correct the conformance scanner at root commit `78c7880` so pure reusable
  workflow callers are evaluated through the called workflow's bounded jobs;
  GitHub disallows `timeout-minutes` on the caller job. Mixed workflows retain
  the local timeout requirement. The focused scanner suite passes 11/11 and
  Horae's false `workflow_missing_timeout` baseline entry is removed.

- Bound the shared Pages workflow at root commit `6ed29a9`: network downloads,
  package installation, package builds, metadata resolution, mdBook tests, and
  mdBook rendering now have explicit termination bounds; the package build and
  metadata query use the committed lockfile. The local mdBook link-contract
  suite passes 43/43. Helios already enables `mdbook-test`; its caller and the
  Kwavers/CFDrs callers still pin earlier shared-workflow revisions and remain
  separate peer-owned integration work.

- Push the Atlas exact-head audit correction at `d496297`. The structural
  requested-provider audit passes for all 20 providers and preserves the
  `Tyche`/`Tychee` normalization. Hosted conformance run `32101488985` now
  reports only the genuine RITK `oversized_files` regression (`43 -> 44`) from
  the committed 540-line `crates/ritk-image/src/region.rs`; the peer-owned
  RITK checkout already has in-flight edits to that region and remains
  untouched. Root overlay run `32101202278` records the separate Apollo
  `0.26.0` versus Kwavers `0.27.0` requirement lag. Kwavers PR #402 remains
  blocked at `69478221f` until Apollo's `0.27.0` default lands; no consumer
  downgrade or compatibility path is added.

- Reconcile moving provider defaults by advancing the Atlas Aequitas gitlink
  to `c74b662c`, Hermes gitlink to `c6265cb4`, and Mnemosyne gitlink to
  current `d48f4842` through the previously recorded `bfe76db0`. The changes
  touch only committed submodule pointers; nested provider checkout dirt
  remains peer-owned and excluded. The structural exact-head audit passes.
  Full coherence reaches the requested scope but reports only the peer-owned
  Apollo checkout's in-flight `0.27.0` manifest against committed Coeus and
  RITK `0.26.0` requirements; Apollo `origin/main` remains `0.26.0`. Root
  hosted gates are re-collected for this pointer advance once the moving
  provider work is stable.

- Reconcile the second moving-default sweep by advancing the Atlas Themis,
  Proteus, Mnemosyne, Hermes, Asclepius, Eunomia, RITK, and Iris gitlinks to
  their fetched default heads. The structural requested-provider audit passes;
  the full coherence limitation is the separately recorded peer-owned Apollo
  `0.27.0` worktree against committed consumer `0.26.0` requirements. Nested
  checkout dirt remains excluded and root hosted gates are pending for the
  resulting root head.

- Merge Hephaestus PR #213 at default `607ce3f`, adding the provider-owned
  typed f32 FDTD contract, WGPU velocity/pressure kernels, and sequential
  contract coverage. Kwavers PR #402 carries the consumer cutover at final
  head `5155f32e8`; its benchmark-regression run `32095365142` is executing,
  and the remaining exact-head matrix is required before the Atlas gitlink
  advances.

- Advance fourteen requested-provider gitlinks to their fetched defaults after
  peer merges; the structural exact-head audit passes. Full coherence remains
  blocked only by the locally materialized Asclepius manifest lag, which still
  requires Aequitas `0.1.0` and Coeus `0.9.0`.

- Close the conformance classifier correction with 37 focused scanner tests,
  Apollo's clean orphan baseline at 0, and hosted root run `32031997052`
  reporting zero ratchet regressions at `f84beec`.

- Advance RITK to PM closure `f23a6acd` after splitting the diffusion Python
  binding leaves. The exact provider `manifest_implementation` count reduces
  from 112 to 111; provider-owned Rust, Nextest, Python matrix, and wheel
  smoke gates pass.

- Advance Hephaestus to PM closure `300b9e9` after the attention structure
  ratchet cleanup and exact-head CUDA/ROCm/WGPU/Metal gates. The provider
  `oversized_files` count is 38; direct Coeus attention cutover remains open.

- Correct the orphan-module conformance graph to follow literal and
  `CARGO_MANIFEST_DIR`-rooted `include!` sources. Apollo's clean exact count
  tightens from 3 to 0 without changing provider source.

- Advance the Helios and CFDrs integrator gitlinks to merged PR #57
  `7fddf789` and PR #345 `a3c53da2`. Helios now rejects incomplete required
  DICOM geometry; CFDrs uses Apollo's native-precision Fourier API and Leto's
  SSOR provider directly. Exact-head hosted gates pass for both consumers.

- Advance the Tyche provider gitlink to merged PR #22 `b1c5cc9f`; the provider
  correction aligns package-distribution and reproducible-study verification
  claims. Advance Mnemosyne to merged PR #51 `997ec088` with event-driven
  decay-test synchronization. The staged root exact-head/coherence audit
  passes for all 20 requested providers.

- Correct the conformance instrument and regenerate its baseline in the same
  change. `scripts/atlas-conformance.py` classified a file as test code only
  when a path *part* matched `tests`/`benches`/`examples`/`fuzz`, but
  `Path.parts` yields `tests.rs` as a filename and never `tests`, and
  `split_test_region` splits only on an *in-file* `#[cfg(test)]` — so every
  co-located `src/**/tests.rs` sidecar was scanned as production code. Four
  independent repo audits reached that conclusion separately. Matching now
  covers directory parts only, plus a new `declared_cfg_test` check that reads
  the parent module's `#[cfg(test)] mod <stem>;` declaration. Stack
  `unwrap_production` moves 4713 → 1460 (kwavers 2630 → 259, consus 709 → 334)
  with the counts landing in the test-region classes where they belong
  (`existence_only_assertions` 598 → 807, `sleep_synced_tests` 117 → 132). The
  ratchet returns to 0 regressions / 0 tightenings. Every burn-down target
  recorded before this fix was aimed by a broken instrument.

- Second conformance correction: `.unwrap()` inside `///` and `//!` doc-comment
  bodies is doctest code, not production. Counting it reported 23 "production
  unwraps" for tyche, whose workspace denies `unwrap_used` outright — every one
  was a doc example, and tyche now correctly reports 0. Stack
  `unwrap_production` 1460 → 1242. Also added `.git` to the sanctioned root set,
  since a submodule's `.git` is a gitlink *file* and was counted as unfiled
  sprawl in every member.

- Add `scripts/atlas-board-compact.py` and apply it. `backlog.md` 13,399 →
  5,369 lines and `checklist.md` 5,810 → 4,170, collapsing 299 closed items to
  one-line archive entries carrying their commit SHAs. Verified no item ID was
  lost in either file. The collapse is mechanical so it is reproducible rather
  than a one-off hand edit; it anchors the closed-status marker to the final
  em-dash segment of a heading, because matching anywhere after an em-dash
  archives live items whose *title* contains a status word.

- File the 2026-08-13 full-stack audit on the board: fourteen read-only audits
  covering all 25 registered members plus the meta-repo, opening 33 DoR-shaped
  items across four tiers. Tier 0 carries two safe-code paths to undefined
  behaviour (`themis` duplicating a melinoe capability token; a `mnemosyne`
  scratch-pool aliasing hole), an unvalidated public `Layout` under 84 leto
  unsafe blocks, unbounded parser allocation and recursion in consus, and two
  precision-contract violations in eunomia — one silently computing five `F64`
  transcendentals in `f32`, one ordering sub-byte floats by raw bit pattern so
  every min/max reduction over them is sign-inverted.

- Remove `helios_workflow_output/{ct,dose,mu,recon}.png` from tracking. They
  are run output of `tomotherapy_workflow.rs:102-104,209-212`, referenced by no
  test, xtask, workflow, Makefile or script, and `.gitignore:74` already names
  that exact path as derived state. helios itself tracks zero PNGs, so no fresh
  clone ever had them.

- Remove nine unfiled work products from `tools/` (~1.5 MB of `_probe_meta*`
  JSON, `cfdrs-lint*.stderr` dumps, one-shot `_fix_apostrophe.py` and
  `_insert_meta_docs.py`) and the Windows reserved-name `nul` artifact at the
  repository root.

- Advance all twenty requested provider gitlinks to their fetched default
  heads after CI-only Atlas workflow-pin merges. Exact-head, provider
  coherence, stack-overlay, and lane audits pass; peer-owned child checkout
  dirt remains excluded from the root change.

- Pin the shared Pages linkcheck2 installer to the stable Rust toolchain before
  `cargo install`; hosted caller validation exposed that the reusable workflow
  must not rely on the runner's ambient Cargo selection. Caller repinning and
  hosted reruns remain open.

- Close the publication-lock residual at the Atlas boundary. Exact committed
  kwavers and CFDrs gitlinks have complete first-party Git lock sources (33/33
  and 22/22); peer-owned overlay lock churn remains uncommitted and excluded.
  The shared crates.io workflow retains `--locked` validation.

- Advance Leto to merged default `39683975` after PR #109 added provider-owned
  disjoint mutable task partitions and the Moirai scheduler boundary. Exact
  PR Rust verification `31714562863`, post-merge Rust CI `31715060346`, and
  Pages deployment `31715059328` pass. Local Leto and Leto-ops Nextest passed
  286/286 and 527/527; the external recurseml analyzer remains report-only.

- Advance Leto to merged default `6e4a1627` after PR #96 replaced the
  production L-BFGS jagged history with a flat CSR-shaped ring and head
  eviction. Exact PR Rust run `31710403431`, post-merge Rust run
  `31710771815`, and Pages deployment `31710771170` pass. The task-partition
  API remains a separate provider-owned residual; superseded PR #103 is
  closed because Hermes 0.6 is already present in default `a722fbc8`.

- Close Hephaestus PR #113 as superseded: product-axis parity already exists
  in current history as `8bc589a`, while its obsolete round-6a path-lock
  rewrite is not compatible with the current git+version source model. The
  current default provider runs `31691399110`, `31691399171`, `31691399196`,
  and `31691399214` pass.

- Close Apollo PR #86 as superseded by the broader current-default cleanup
  `49632c6c` (ADR 0039 s5); the affected `helpers.rs` modules are already
  dissolved into concern-specific leaves. No duplicate rename is integrated.

- Advance Apollo to merged default `fc564896` after PR #83 converged the
  shared WGPU validation surface and real Mnemosyne branded-slice integration
  test. Duplicate GFT validators were removed; the `mnemosyne-memory` lock
  edge and benchmark candidate-manifest synchronization were completed.
  Exact PR Rust/Python run `31708004091`, benchmark run `31708004087`,
  post-merge CI `31708720285`, and Pages deployment `31708718632` pass.

- Advance Coeus to merged default `72372c91` after PR #320 removed the
  host-side batched Frobenius-norm fold. Provider square, last-two-axis
  reduction, square root, and batch reshape now remain in the provider graph;
  rank-two and non-contiguous paths retain their value-semantic contracts.
  Exact PR run `31701736189`, post-merge Backend parity run `31704377695`, and
  Pages run `31704377431` pass the applicable gates. Required-device CUDA and
  ROCm jobs remain unverified.

- Advance Helios to merged default `546c199f` after PR #48 converged its Pages
  caller on the Atlas shared workflow. The caller passes the actual rendered
  output `target/book/helios/html`; PR Rust, Python, book, and 45-minute
  benchmark gates passed. Post-merge Rust/Python and Pages deployment runs
  `31700981248` and `31700981609` passed.

- Advance Hermes to merged default `d1627cd2` after PR #37's native aarch64
  permute A/B gate. Neutral NEON reverse overrides were removed; large f32
  interleave and deinterleave wins of 1.27% and 1.40% remain. PR run
  `31695534571` and post-merge default run `31696261625` pass the applicable
  provider-owned gates. AVX-512 timing remains open under HS-429 real-silicon
  infrastructure.

- Advance Hephaestus to PM-closeout default `c373de19` and Coeus to
  PM-closeout default `a4063be1` for the CUDA `f64` comparison seam. Exact
  Hephaestus default runs `31691399110`, `31691399171`, `31691399196`, and
  `31691399214`, plus Coeus default run `31672329963`, pass their software
  provider contracts; required-device jobs remain unverified.

- Advance Leto to provider default `a722fbc8`. Close the generic convolution
  provider PM record after exact-head provider runs `31690152639` and
  `31690301356`, with Coeus direct-consumer evidence in `31672329963`.

- Advance Helios to provider default `f108dc9b`. The stale H-098 provider PM
  record is closed; exact-head hosted run `31686100896` passes Rust, Python,
  and the phase-reversed benchmark regression gate.

- Advance Apollo to provider default `36f2f364`. The real symmetric spherical-
  harmonic basis and scattered-direction design matrix are now recorded as
  integrated with RITK's diffusion and tractography consumers; the exact
  current-default hosted Rust/Python verification is `31684967756`.

- Merge Consus cross-format test closure PRs #24 and #25. Cross-format
  integration tests now call provider-owned HDF5, Zarr, NetCDF, and in-memory
  contracts directly with deterministic value-semantic fixtures; hosted run
  `31684429085` passes all 68 repository-owned jobs at the exact source head.

- Merge Consus PR #23 (`b3ca01c2`) to close the FITS, HDF5, and NWB
  no-default storage boundaries. Alloc-backed modules, re-exports, tests, and
  benchmark surfaces are gated consistently; the exact-head hosted matrix
  `31681611017` passes.

- Merge Consus PR #22 (`37f835d1`) to close the `consus-arrow` and
  `consus-parquet` no-default cfg boundaries. Alloc-backed bridges, wire paths,
  tests, and benches are gated consistently while descriptor-only no-alloc APIs
  retain value-semantic coverage; the exact-head hosted matrix passes.

- Pin shell scripts to LF so the Bash toolchain bootstrap remains executable
  after Windows checkouts.

- Merge Kwavers PR #341 (`e3389e79`) for typed two-dimensional transducer-array
  geometry, curvature, focus, frequency, velocity, steering, and delay
  contracts through Aequitas. Center-to-center pitch generation is corrected;
  Python retains SI/degree scalars only at serialization boundaries. Eunomia
  real/quadrature values retain one observable signal unit with no imaginary SI
  unit. Hosted Code Coverage `91842334110` and Test Suite Coverage
  `91842333977` pass; the RecurseML analyzer remains report-only.

- [minor] Advance the Leto/CFDrs provider graph to merged sparse-LU native-view
  ownership. CFDrs direct solves no longer stage the native RHS or returned
  solution through consumer-owned `Vec` buffers; no release is performed.

- Apply the shared line-table-only debug budget to test builds as well as
  development builds. Dependencies, build scripts, and procedural macros emit
  no ordinary test debuginfo, reducing Nextest artifact size and linker memory
  without changing optimization, assertions, or test workloads.

- Merge Kwavers PR #335 (`c3e0ca39`) to type sensor-beamformer positions,
  sampling and steering frequencies, angles, sound speed, spacing, aperture,
  F-number, and spatial-frequency metrics through Aequitas. The corrected
  LLVM coverage workflow selects targets by Cargo feature requirements and
  preserves Eunomia's real/quadrature shared-unit representation without an
  imaginary SI unit.

- Merge Kwavers PR #337 (`d5d2d964`) to type PAM delay-and-sum and neural sensor
  geometry, timing, frequency, angle, event-coordinate, and coherence metrics
  through Aequitas. Uncalibrated PAM threshold/intensity remain representation
  values; Eunomia complex FFT data retains one observable unit with no
  imaginary SI unit. Final hosted coverage, architecture, safety, feature,
  benchmark, and platform gates pass.

- Merge Kwavers MET-60 for typed transducer design and focused propagation
  contracts: geometry, wavelength, frequency, velocity, calibration,
  impedance, pressure, intensity, and extents now use Aequitas through the
  driver boundary. Focused real/quadrature accumulators remain components of
  one observable pressure signal; no imaginary SI unit is introduced. PR #338
  merged at `7ec566b6` and PM closure PR #339 merged at
  `3f96514d`; hosted Code Coverage `91794809116` and Test Suite Coverage
  `91794808091` pass, with the external RecurseML analysis remaining
  report-only.

- Merge Kwavers MET-61 for typed acquisition geometry: element coordinates,
  bowl radius, ring diameter and row spacing, breast-FWI geometry, and CBS/
  Born numerical callers now use Aequitas `Length` through PR #340. The
  absorption reference assertion uses a scale-relative 16-ulp bound. Eunomia
  real/quadrature values retain one observable signal unit with no imaginary SI
  unit. PR #340 merged at `9a6aac1c`; hosted Code Coverage `91827476450` and
  Test Suite Coverage `91827477067` pass with the complete repository-owned
  matrix.

### Added

- Generalize Tyche correlation, Morris, and Saltelli sensitivity estimators
  and reports over a const-generic output dimension while preserving the
  single-output API. Add analytical and seeded two-output law coverage.

- File ADR 0030 to promote published Hyperion as the bounded photon/optical
  transport owner. The decision records the Aequitas → Proteus/Hyperion →
  integrator hierarchy, per-consumer deletion ledger, measurable consolidation
  effects, and the rule that P2 does not add Ares or Prometheus without a second
  production consumer and net deletion.

- Promote public Iris as the twenty-fourth Atlas package and file ADR 0029.
  Iris owns normalized color laws, fixed lookup tables, borrowed scientific
  views, and static render-backend contracts. RITK Snap and VTK consume the
  public provider directly and delete their independent color engines. CFDrs
  consumes `NamedColorMap` directly, deletes its local enum and formulas, and
  reduces each overlay range once while borrowing existing field maps. File
  formats, domain interpretation, UI state, and GPU mechanics remain local.

- Register public Asclepius remote default
  `eb65eaf7bf83bbd6ad38778fc5e2b534b01ac6aa` as the twenty-third Atlas
  package and file ADR 0028. The law core and one-way Coeus adapter merge at
  `794f8c3`; Asclepius owns typed gEUD, TCP, NTCP, CEM43, Arrhenius damage,
  and independent-response composition over Aequitas and Eunomia. Helios
  `33bba34` and Kwavers `1cb01fe` consume the public provider directly, with no
  sibling-directory source patch. The stack map, dependency graph, provider
  table, naming registry, roadmap, layout, ADR index, backlog, checklist, and
  gap audit share that boundary. Hephaestus `74dec5d` aligns its Aequitas
  response quantities with the registered provider graph.

- File ADR 0025 (`docs/adr/0025-proteus-material-property-promotion.md`) at
  `Accepted` to record the Proteus promotion decision. Proteus owns shared
  material-property and constitutive-law contracts: validated thermophysical
  newtypes (`MassDensity`, `SpecificHeatCapacity`, `ThermalConductivity`)
  over Aequitas quantities and Eunomia scalars with a GAT-based static
  constitutive seam (`ConstitutiveLaw<Law>`, `ConstantLaw`, `NoState`) and
  `Cow<str>` material identity. Cross-references Proteus ADR 0001, ADR 0002,
  0005, 0021, and 0023 in the ADR INDEX cross-walk.

- File ADR 0026 (`docs/adr/0026-tyche-uq-promotion.md`) at `Accepted` to
  record the Tyche promotion decision. Tyche owns reproducible uncertainty
  studies: counter-stream random-access Latin hypercube designs,
  index-addressed ensemble execution, online Welford/Chan moments, Pearson
  screening, finite-sample split-conformal calibration, and Moirai/Consus
  provider adapters over a `no_std + alloc` core with GAT response seams
  and const-generic numeric widths. Cross-references Tyche ADR 0001, ADR
  0002, 0005, 0023, and 0025 in the ADR INDEX cross-walk.

- Add a `build(atlas)` entry advancing the coeus gitlink from `56fa49a` to
  `c290f3e` after bumping the hephaestus path-dep pins 0.17.0 -> 0.18.0 to
  restore Atlas graph closure following Peer's v0.18.0 hephaestus tag
  advance. Add a matching leto gitlink advance 4158b8e -> 02d74fd wrapping
  PR #55 (perf/leto-ziggurat-normal).

- Add ADR 0027, the Atlas-owned
  `tools/checkout-path-dependencies` Rust engine, and its composite action.
  Consumer Cargo dependency, patch, and replacement paths resolve through exact
  Atlas gitlinks; moving refs, duplicated provider lists, dirty or
  wrong-revision reuse, unknown providers, missing provider URLs, missing
  manifests, and destination escapes fail closed.

- Add ADR 0024 and the Atlas-owned `tools/criterion-regression` Rust gate for
  phase-reversed, counterbalanced Criterion median regressions, 5% family-wise
  error control, and fail-closed missing or mismatched evidence.

- File ADR 0023 (`docs/adr/0023-harmonia-coupling-promotion.md`) at `Proposed`
  to promote `harmonia` as the Atlas coupling-mechanics provider. Phase 0
  contract is two-partition synchronous Jacobi `PartitionedPair<M, T,
  FIRST_SUBSTEPS, SECOND_SUBSTEPS>` with const-generic heterogeneous
  subcycling over Horae subcycle plans and Athena Core convergence policy;
  static transfer and relaxation policies are ZSTs and the workspace
  allocates only at construction. Local Phase 0 evidence (14/14 nextest,
  1/1 doctest, clippy/rustdoc clean) is recorded but the promotion is
  blocked until `repos/harmonia` publishes to a public remote.

- Add a `harmonia` row to the Atlas current-stack table and a coupling
  entry to the Provider ownership table in `README.md`. Retire `harmonia`
  from the Candidate packages roadmap. Add ADR 0023 to the ADR INDEX with
  the topic-tag cross-walk. Surface the pending publish as the
  `HARM-PROMOTE-001` audit row and `HARM-PUBLISH-001` watchpoint in the
  2026-07-20 PM sections of `backlog.md`, and as a 2026-07-20 State refresh
  row in `gap_audit.md`.

### Changed

- Advance Apollo to PR #64 merge `614939fd`, Hephaestus to portable-wheel PR
  #63 merge `b726b39f`, and Moirai to PR #83 merge `ddb665e9`. The Moirai head
  preserves saturated indexed work on the caller and adds a borrowing parallel
  scope; the follow-on Kwavers lock and serialization cleanup remains tracked
  by ATLAS-INTEGRATION-042.

- Advance Moirai through PR #84 merge `e4d2855` and default closeout
  `c870eed`. The cleanup removes only the unused `moirai-core` nightly TLS
  build gate while retaining the platform and executor fast paths; exact
  default run `29963043374` passes Rust and all three wheel platforms.

- Advance Kwavers to PR #307 merge `0602c1fd4` and close its debug build
  budget. Removing wildcard dependency `opt-level = 3` restores generic sharing
  and reduces uncached feature-build stages by 18–45% while full-grid PSTD
  remains below 25 seconds. Record the 16,771,464,617-byte clean debug baseline
  and remove approximately 4.49 GiB from seven obsolete private target trees;
  the shared `D:/atlas/target` cache remains intact. A subsequent stack sweep
  removes 13 more target forks (18.465 GiB), verifies zero repository-local
  targets, and cleans 68,854 files / 20.7 GiB from the canonical cache after
  the completed local gates, leaving the measured shared tree at 0 bytes.

- Close the Atlas Criterion consumer rollout and advance Kwavers to PR #308
  merge `402d9695`. Kwavers PR #306's bounded same-path head passes complete
  candidate smoke, four counterbalanced 21–23 minute pair jobs, and aggregate
  classification while every non-critical benchmark remains covered by one
  candidate execution. PR #304's Tyche collocation integration passes its
  exact-head ordinary CI, architecture, and legacy-audit workflows. PR #308's
  exact documentation head `8373c8bb0` passes CI `29890089765`, architecture
  `29890089803`, and legacy audit `29890089797`.

- Advance P2 from specification to execution. Hyperion `064a189` is public,
  anonymously readable, and hosted-green. Helios `105a093` completes the first
  photon/optical deletion ledger and passes hosted run `29883200466`; Kwavers
  and CFDrs remain. Ares remains
  blocked on Proteus elastic-property consolidation and a second structural
  consumer; Prometheus remains
  blocked on Kwavers/Horae cleanup and a second production reaction-network
  consumer. Package count is not an acceptance criterion.

- Document the supported four-job schedule for long consumer benchmark
  instruments: two isolated, co-located base-first pairs and two isolated,
  co-located candidate-first pairs. The Atlas classifier still requires
  unanimous direction, identical benchmark universes, complete estimates, and
  the derived 5% family-wise confidence bound; no comparison mixes
  measurements from different runners or fixed checkout identities.

- Add the registered Proteus and Tyche packages to the README naming registry.

- Move the shared Cargo target configuration from `repos/.cargo` to the Atlas
  root so root tools, provider repositories, and linked worktrees beneath
  `worktrees/` resolve one `target` cache. Reconcile Apollo, Helios,
  Hephaestus, Leto, and Tyche gitlinks with their fetched public defaults.

- Promote public Harmonia as the twentieth Atlas package. Phase 0 owns
  transactional two-partition Jacobi coupling, borrowed interface transfer,
  relaxation, and heterogeneous subcycling over Horae and Athena Core. Record
  the fetched remote-default gitlink and ADR 0023.

- Clarify the parent-gitlink revision contract and safe submodule inspection in
  the Atlas README. Correct the roadmap so Harmonia composes Horae and Athena
  without depending on material-law ownership. Advance Athena to `96fb26d`
  with external observer construction and package documentation, and Horae to
  documentation merge `92af1a2`.

- Promote Horae and Athena as public Atlas packages. Horae owns typed
  time-integration policy over Aequitas. Athena owns shared PCG and restarted
  right-preconditioned GMRES recurrences over Leto CPU and Hephaestus WGPU,
  and Leto no longer exports duplicate iterative-solver recurrences. Record
  both public gitlinks, advance Leto to PR #54 merge `1752058`, and make
  `.gitmodules` the build-driver package-set SSOT.

- Advance Kwavers to PR #295 merge `49c116f`, replacing its bubble-energy
  `uom` ownership with Aequitas quantities and correcting the heat-capacity
  dimensional law. Pin CFDrs at PR #298 merge `7c37f7f`, where typed spacing
  reaches Hephaestus. Replace the parent graph's local-only `156531e` and
  `a34a01d` gitlinks with fetched merged defaults after their consumer gates
  pass.

- Advance Hephaestus to PM closeout PR #52 merge `cdfcd0c`; runtime code and the
  verified Eunomia 0.6 provider closure remain unchanged.

- Advance Hermes to PR #11 merge `6f9b81f`, locking Eunomia 0.6 after its
  raw-half retirement. Advance Leto to the exact PR #48 merge object
  `bb03244f05a9c43c318d103225c3ccad07e9fad9`, preserving the merged
  Box-Muller paired-normal performance increment.

- Advance Eunomia to PR #48 merge `df77dfd`, removing its production
  `half` dependency and foreign raw-half numeric/cast surface. Advance
  Hephaestus to PR #51 merge `594d57a`, whose reproducibility lock resolves
  Eunomia 0.6.0, Hermes 0.4.0, and Leto 0.39.0 with 312/312 provider tests.

- Tombstone superseded CR-2, RITK, and Kwavers migration queues after their
  recorded closures; refresh the provider/consumer stack table to the 16
  fetched remote-default gitlinks.

- Advance Eunomia to `c196db5`, Hermes to `c9bbdf8`, and Leto to `7afcbd0`.
  Eunomia owns exact reduced-format bit and float-element contracts; Hermes and
  Leto remove raw `half` public ownership in favor of Eunomia `F16`/`Bf16`.
  Reconcile the cumulative Coeus pointer at `5ee07a2` and RITK pointer at
  projection-hardening PR #44 merge `688eb8e`; peer working state remains
  outside the parent commit.

- Advance Helios to PR #7 merge `79b09e9`; its reproducibility lock now
  resolves Apollo 0.25.0, Eunomia 0.4.0, Leto 0.38.2, and Hephaestus 0.17.0
  and contains no `num-complex` package.

- Record Coeus PR #212 merge `bb97cc6` as the NN benchmark-provider closure.
  Burn is absent while all 211 operation groups and 424 native
  Sequential/Moirai measurements remain. The locked graph resolves Eunomia
  0.4.0, Leto 0.38.2, and Hephaestus 0.17.0.

- Record Eunomia PR #39 merge `49dc115` as the canonical sub-byte conversion
  cutover, then advance Leto PR #44 `f0b4d8e` and Hephaestus PR #50 `ed7d76e`
  after their reproducibility locks and full consumer gates resolve Eunomia
  0.4.0. The Atlas graph advances only these three merged defaults.

- Record Coeus PR #211 merge `4459d09` as the tensor legacy-benchmark removal;
  the consumer commits `Cargo.lock`, aligns Hephaestus `0.16.1`, and retains
  only Coeus Sequential/Moirai and Leto benchmark paths. Locked package
  verification, 56/56 Nextest, warning-denied Clippy, doctests, rustdoc,
  metadata, and residue scan pass.

- Record Apollo PR #53 merge `a31b8f8` as the Hephaestus lock convergence;
  `hephaestus-core`, `hephaestus-wgpu`, and `hephaestus-cuda` now select
  provider `cec0e33` after its Leto-owned legacy-math cleanup. Locked compile,
  402/402 Nextest, warning-denied Clippy, doctests, rustdoc, provider audit,
  hosted Rust/Python, and CodeRabbit checks pass.

- Record Hephaestus PR #47 merge `cec0e33` as the Leto-only CPU reference
  cleanup. Its WGPU/CUDA tests and comparative benches no longer depend on
  legacy array or linear-algebra crates; provider execution remains owned by
  Hephaestus and the Python `numpy` bridge remains an FFI-only edge.

- Record Apollo PR #52 merge `7303423` as the Leto merge-pin correction; both
  Leto packages now select Atlas default `3ac0d203` rather than parent
  `6a0e297`. Hosted Rust/Python/CodeRabbit checks pass; the external analyzer
  remains non-required.

- Advance RITK to PR #41 merge `a41e03b9`, aligning its lockfile and composite
  provider checkout with Apollo 0.25. All 22 repository and review checks pass,
  including cross-platform Nextest, Python 3.9–3.13, wheel, lint, dependency
  alignment, and migration audit.

- Record Apollo PR #51 merge `6dcb97c` as the provider-lock refresh; the
  consumer now resolves Hephaestus `93bc38e`, Eunomia `a2e4f390`, Leto
  `6a0e297`, and Moirai `8a51b2a7` from default sources. Locked 402/402
  Nextest and hosted Python/Rust/CodeRabbit checks pass.

- Advance CFDrs, Eunomia, Helios, Leto, and RITK to their merged
  default-branch commits while preserving active Apollo, Kwavers, and RITK
  feature work. The parent graph records only fetched remote defaults; Leto
  owns the remaining sparse-direct capability item needed to remove CFDrs
  `rsparse` without replacing its independent direct tier with GMRES.

- Record Hephaestus PR #46 merge `93bc38e` as the scan-limit theorem closure;
  provider ADR 0009 proves shared storage is `W` partials independent of line
  length, and the existing `L=513`, `W=256` WGPU/CUDA contracts cover the
  long-line path. KS-5b remains a measured performance follow-up.

- Record Apollo PR #50 merge `c874281` as the canonical Winograd trait
  ownership cutover; the obsolete internal `mixed_radix` re-export is deleted,
  all callers use `components::winograd`, and local 402/402 plus hosted Python,
  Rust, and CodeRabbit checks pass. The external `recurseml/analysis` error is
  non-required.

- Record Apollo PR #49 merge `e2f905a` as the obsolete execution-policy-wrapper
  removal; `apollo-fft` now uses Moirai's canonical threshold policy and keeps
  the provider boundary on Hephaestus. Local 393/393 package evidence and the
  hosted Python and Rust workspace lanes pass; the external
  `recurseml/analysis` failure is non-required.

- Advance the Hephaestus provider gitlink to PR #45 merge `3b68228`; memoized
  CUDA driver initialization and serialized context creation close the
  Windows concurrent-acquisition abort, with the full 109/109 CUDA suite
  passing while transfers and kernels remain concurrent.

- Advance the Hephaestus provider gitlink to PR #44 merge `d0eafc8` for the
  shared-memory tiled axis-scan kernels; the provider ADR and long-line
  WGPU/CUDA contracts remain the theorem and behavioral SSOT.

- Record Kwavers PR #294 merge `9eabc4e2` as the clean Hephaestus
  backend-kernel ownership increment; obsolete buffer and pipeline managers
  are deleted, the MVDR wall-clock assertion lives in Criterion, and the
  parent pin advances from `7c7d60f`.
- Record Kwavers `11e577c` as the clean Leto medium-accessor and abdominal
  geometry-contract head; Architecture Validation passes, while CI/CD coverage
  is blocked only by an external Codecov HTTP 429 upload response; PR #293
  retains the generated report gate and makes that transport non-blocking.
- Mark the Apollo `eb46e77` parent pin complete after Atlas PR #18; the
  verified Apollo `main` head is now `0b5d11c` after PR #48.
- Merge Apollo PR #46 and PM closure PR #47 at `eb46e77`; partition GPU
  dispatch verification into a deep private leaf and retain Hephaestus/Leto
  provider ownership.
- Advance the Atlas Apollo gitlink in PR #18 at `56ad179`.
- Keep Kwavers PR #292 at `54575460c` pending hosted coverage diagnosis and
  the remaining matrix; no dirty parent gitlink is advanced.
- Advance the RITK gitlink to its verified Apollo 0.24 source-checkout repair
  on `main`.
- Refresh Apollo, Hephaestus, Kwavers, Leto, and RITK gitlinks to the current
  provider graph; add ADR 0020 with the exact provider-graph closure theorem.
- Align public Atlas submodule pins with their fetched default branches.
- Advance Apollo, Helios, and RITK gitlinks to their merged default-branch
  commits after their provider and cross-platform CI closure.
- Advance the Apollo submodule pin after its concurrent provider-boundary merge.
- Advance the CFDrs and Hephaestus gitlinks after their typed GPU boundary
  closure.
- Advance the CFDrs gitlink after executable one- and two-dimensional
  validation examples replaced static reports on `main`.
- Advance the RITK gitlink after its merged lock metadata repair aligned the
  Hephaestus patch entries with the current provider graph.
- Register Kwavers and Helios in the Atlas public submodule roster.
- Reject bare `cargo test` in cross-stack drivers while retaining doctests.
