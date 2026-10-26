# Core tensor model and framework contracts

The [TF conversion follow-up](tf-conversion-20261026/README.md), introduced in
program **2026-10-26.12**, complements the preserved cast/add/shape snapshot below.
It retains ten existing IDs, four partial/six unmapped associations, 30 UNRUN
targets and ten open gaps. Its primary API remains unmapped; source review and
mathematical controls grant no implementation, native execution or release credit.

Model **2026-10-26.1**, program **2026-10-26.7**. This slice defines source branches
for 39 existing public identities: 37 new partial mappings and two reused NumPy
metadata mappings. The inventory remains **38,096 candidates: two source-specified,
96 partial and 37,998 unmapped**. All four full public inventories stay open.
No implementation, runtime or release stage is promoted.

| Artifact | Definition and evidence boundary |
| --- | --- |
| [State model](model.json) | Nine reusable shape, promotion, cast, broadcast, view, reshape, indexing, effects and AD laws |
| [Endpoint contracts](contracts.json) | Exact ID, one accountable owner, source, law, mapping, cases and remaining obligations |
| [Case views](cases.json) | 125 API targets from 118 distinct source programs, all unrun |
| [Analytical fixtures](analytical-fixtures.json) | Eight mathematical witnesses; no framework/provider execution credit |
| [Implementation packages](implementation-program.json) | Five subordinate packages, dependency order, acceptance, conditional estimates |
| [Provider boundaries](core-tensor-boundaries.json) | 12 proposals, 49 selected source files and 48 anchors at cached canonical pins |
| [Gamma audit](gamma-source-audit.json) | Separate locally qualified CPU candidate; no default/released-cohort integration |
| [Capture index](index.json) | Artifact hashes and validator inputs |

The frozen references remain NumPy 2.5.4 (`a3d0ef1df045b858e68115001fdabc930bb3b68c`),
JAX 0.12.0.1 (`dc4af684446e65ee98eee8090e1ff6f8211473fb`), PyTorch 2.14.1
(`5c4886908584029761b579af026dcfb627c84070`) and TensorFlow 2.21.0
(`a481b10260dfdf833a1b16007eead49c1d7febf3`). These are frozen releases, not
newly selected rolling defaults.

[NumPy](numpy-jax/contracts/numpy.json)/[JAX](numpy-jax/contracts/jax.json) retain
19 endpoints, 80 portable excerpts and 44 verified Git blobs.
[PyTorch/TensorFlow](torch-tf/contracts.json) retain 20 endpoints,
[58 witnesses](torch-tf/line-witnesses.json) and 32 provenance receipts. Every
source URL has an exact official revision/path/line. Supporting internal functions
remain source dependencies rather than public IDs. Framework signatures, native
versus delegated branches and differences remain distinct. Generated/inherited/
alias extraction stays open.

Canonical captures retain analysis, excerpts and original manifest metadata;
full third-party sources and research generators are not vendored. Captured
research READMEs describe their original complete packets; replay commands apply
there. Canonical reproduction uses `python3 scripts/atlas-parity.py check` and the
parity tests. Portable hash/bounds checks verify receipt consistency; independent
review of original cached blobs verifies correspondence.

The coordinate law begins after framework argument conversion. Concrete broadcast
joining chooses the non-unit extent: **0 joined with 1 is 0**. Signed-stride views
address `offset + sum(index * stride)`; rank-zero values retain their offset and
empty shapes load nothing. A transposed enumeration need not fit a flat affine
view. Gather VJPs **add** repeated-position cotangents; signed nonunit seeds detect
assignment/mean errors. Integers `2**53` and `2**53+1` demonstrate f64's int64
information loss. Each fixture requires its defining boundary and exact output.
Empty views never construct unused coordinate pools. The checker bound is not an
API size limit.

Arbitrary byte/zero-itemsize/managed layouts, symbolic dimensions, rank bounds,
full casting tables, Python admission, errors and resource safety remain explicit.
Promotion retains framework policy, weak/strong category, array rank, defaults,
X64 and strictness. Cast conversion, alias/copy and AD conventions are separate.
Native NumPy/Torch mutable views, JAX values and TensorFlow Tensor/Variable effects
require different policies. JAX wrappers can delegate to NumPy/custom objects;
shape warning/doc differences and reshape delegation remain separate branches.

NumPy getter outcomes and setter effects are separate. Positive JAX `.at` cases
construct native integer-index arrays; bare-list rejection is separate. The
[initial findings](independent-review/numpy-jax-core-initial-findings.json) and
[corrected review](independent-review/numpy-jax-core-final-review.json) preserve
this correction. [Torch/TF re-review](independent-review/torch-tf-core-final-review.json)
clears format-dependent alias, AD validation order and layout-case corrections.
Source review does not execute those cases.

Existing native generic policy assigns Eunomia scalar policy, Leto layout/index
algebra, Mnemosyne storage, Melinoe access proofs, Themis placement, Hephaestus
devices and Coeus tensor/AD/effects composition. Proof-branded scoped mutation and
explicit copy modes must preserve observable aliases. Silent copying, widening or
CPU fallback cannot fill a missing contract. Six concrete boundary decisions need
normal provider ADR review. No new user scope reduction is requested.

Provider pins are cached canonical observations, not freshly fetched defaults.
Their 49 selected files match older detached planning worktrees; those older HEADs
are not current defaults. Coeus's f64 facade, integer round-trips, unsigned layout
bridge, COW aliases, gradient access and host staging remain gaps.

The CPU gamma candidate uses Eunomia `ebb1923feed7e416cbb97a9fcb19423922ae09d2`,
Leto `93e2a8c653252dfc943339c1bcec143a663a77d6` and Coeus
`068a5ff0ba74db9fde4d8bbe7c90f493222a0480`. Exact source review, bounded CPU tests
and locked API comparisons pass; 57 skipped checks per API package receive no
credit. A task-private Git cache is not fresh remote/registry availability. Device,
full AD, performance and coherent release gates stay open. Its existing owner
retains delivery. The audit records prior invalid CLI authentication/policy reads403;
the existing CLI identity is now verified and Eunomia/Leto feature pushes are
reported successful. Exact downstream/registry/release qualification stays open.

Reviewed snapshots `f09f078e`/`da03f4ea` remain preserved. The historical connector
attempt returned403 and is not retried. Explicit user direction authorizes the
existing `gh` CLI session. [PR#572](https://github.com/ryancinsight/atlas/pull/572)
is merged at `60f32ba8` after actual fast/slow pytest, CodeQL, conformance and
independent exact-head review. All three post-merge runs pass; deployments are
empty, Pages is disabled and hooks are empty.

[PR#573](https://github.com/ryancinsight/atlas/pull/573) refreshes the workflow
snapshot against that prerequisite; its tree remains identical to reviewed da03.
It is merged at `de9d428d` after121 zero-skip focused tests, independent review
and actual hosted gates. The [provider ledger](../provider-evidence.json) retains
exact heads, merge commits, source reviews and run IDs. Those planning deliveries
do not qualify framework execution, full definition or1.0. The core snapshot
`510410f2` remains saved and independently reviewed. The final prerequisite
[PR#574](https://github.com/ryancinsight/atlas/pull/574), exact head
`11406055bc424500c98fb37b2e59456696a9f87b`, merges as
`f642337d67a7853e9c81a2f6fb07cd45a5691d83` at 2026-10-26T14:33:57Z.
Parent-verified fast/slow run40339245066, CodeQL40339117660 and
conformance40339121408 pass, with mandatory exact-head review (139 tests,
zero skips; 43 links; expanded board1,000). This delivered planning prerequisite
does not qualify framework execution, the native cohort, full definition or1.0.
The [dtype policy follow-up](../dtype-policy/README.md) has its own exact-head
review/delivery boundary.
