# Validation and remaining definition work

Program 2026-10-26.11. Exact candidate identity and current hosted results belong
in the draft PR; local evidence here describes the authored tree and commands,
not a final merge/release certification. [Contracts](contracts.md).

The initial #575 head `20ae8d85` passed its serial conformance suite and slow
Python job, but two fast-job attempts failed in different native fixtures. The
second exposed `rustc -vV`: missing manifest in the pinned `1.97.0` toolchain;
the first helper's captured Cargo stderr was not exposed. Concurrent automatic
installation is an inference from parallel consumers and incomplete installation,
not an independently established cause. The fast workflow now prepares the root
fixture and coherence-auditor toolchain versions and declared components serially
before xdist starts. It uses the fixtures' existing version normalization; no pin,
test, job timeout or gate is weakened. Failed attempts remain failed evidence.
The resulting exact head needs independent review and fresh actual hosted checks;
serial/slow passes do not replace a failed fast gate.

Independent physical-file/reindex review also exposed Boolean/float source
offsets that Python compared equal to integers. A shared typed resolver now
requires string object keys and exact nonnegative integer list offsets, resolves
against the actual container and rejects scalar traversal. Semantic mappings,
public-scope contracts, core contracts/cases and JAX clauses use that resolver;
the old unchecked core helper is removed. Real copied-artifact tests preserve
consistent index and consuming-mapping hashes so rejection must come from the
selector contract. Frozen source, API stages and raw CP02 history remain intact.

The original planning/tooling slice is merged through #570 at `2dbfeabc` and
the bounded source-disposition slice through #571 at `03464d75`. Their exact
heads receive independent review and actual fast/slow Python, CodeQL and
conformance passes after readiness. All three post-merge #571 workflows pass;
the exact merge has no deployment records. Earlier draft-only skip observations
below are retained history, not passing validations or current merge blockers.
The public-surface/shared-contract increment subsequently merged through
[Atlas #572](https://github.com/ryancinsight/atlas/pull/572) at `60f32ba8`,
workflow contracts through [#573](https://github.com/ryancinsight/atlas/pull/573)
at `de9d428d`, and core tensor contracts through
[#574](https://github.com/ryancinsight/atlas/pull/574) at `f642337d`.
Each exact head passed independent review and actual fast/slow Python, CodeQL
and conformance checks; each merge's post-merge checks passed with no deployment
records. The current dtype policy increment requires its own exact-head review
and hosted checks. Full definition and release qualification remain blocked.

## Recorded candidate surface

| Frozen reference | Candidate declarations | Distinct symbol spellings | Extraction state |
| --- | ---: | ---: | --- |
| NumPy 2.5.4 | 2,741 | 2,740 | Original 65 gap payloads dispositioned; whole generated/public/prose scope remains incomplete |
| JAX 0.12.0.1 | 1,700 | 1,700 | 90 false-positive gaps resolved; five requested sets still need rendered selection, 24 other cases partial |
| PyTorch 2.14.1 | 9,066 | 9,066 | Minor header explained by source config; patch/device semantics and broader native/tooling scope remain open |
| TensorFlow 2.21.0 + Keras 3.15.1 | 24,589 | 23,379 | Source/export/inherited relations retained; generated/public/companion/documentation reconciliation remains open |
| Total | 38,096 | 36,885 | Not a complete public API denominator |

The original four inventory files (38,051 declarations) remain byte-identical.
The additional 45 source-bound candidates preserve their extraction and member-
selection obligations. Source-candidate tables also retain missing exports,
conditional bindings and inherited members; they overlap and are not an additive
capability count. PyTorch retains 8,944 documentation/label records separately.
See [the closure slice](reference/closure/README.md) for exact finite dispositions.

Two API contracts, `numpy.ndim` and `numpy.shape`, are independently reviewed
SOURCE `mapping=specified`. The historical #572 baseline had 36 constructor
contracts plus `numpy.size`, covering 59 partial declaration views and leaving
38,035 candidate identities unmapped. The #574 core increment added 37 partial
views while reusing both specified contracts. The current report therefore has
**96 partial and 37,998 unmapped identities**; all **38,094** without complete
semantic mappings continue to block definition completion. The dtype policy
slice changes none of these stages. There are zero runtime qualification
evidence records and no qualified repositories. The 67 family contracts route
ownership; they do not convert candidate declarations into implemented capabilities.

## Reproduction

From the Atlas root:

```sh
python3 scripts/atlas-parity.py check
python3 scripts/atlas-parity.py report
PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests -p 'test*parity*.py' -v
python3 scripts/atlas-board-index.py check
python3 scripts/atlas-artifact-budget.py check --base origin/main --rev HEAD
git diff --check
python3 scripts/atlas-parity.py qualify --gate definition
python3 scripts/atlas-parity.py qualify --gate release
```

`check` validates the frozen source hashes, identity/count/aggregate/source
traceability, repository/capability owners and exact target revisions, complete
work-package coverage, both DAGs and scheduling prerequisites, mapping schemas
and evidence schemas. It does not run framework computations. The qualifier
returns 1 for unmet gates, 2 for malformed input, and 0 only if its supplied
evidence meets all protocol obligations. Both qualification commands correctly
return 1 for this candidate. External exact-head review evidence is mandatory
for eventual qualification; a clean tracked tree alone does not qualify.

The public-scope slice executes **115 tests, zero skips**, including 28 new
public-scope/storage rejection and roundtrip checks. The earlier 87-test slice
contains 70 gate/traceability and 17 source-extractor tests collected by an import-only wrapper in
`scripts/tests`. Hosted `pytest scripts/tests` therefore collects the same
extractor tests without duplicating assertions. Source extractors regenerate
byte-identically from their independently hash-verified caches. Byte compilation
and whitespace checks pass. The board index is regenerated after correcting
an inherited malformed heading, retaining blocked ownership and the publisher
review link; the combined backlog stays at 1,000 lines within its 1,000-line
budget. Historical unrelated stale-citation reports remain advisory.

The first hosted run at `47a10521` exposed four board-schema regressions and
one UTF-8 subprocess-decoding guard failure introduced by this increment.
The ordinary fixes use canonical `todo`/`blocked` board states, restore the
cohort anchor and field priorities, and retain acceptance work in the existing
program instead of an introduced root `checklist.md`. Board schema counts now
match baseline: 0 status defects, 0 missing anchors, 85 inherited missing
priorities and no retired root checklist. The decoding regression reproduces
locally before the fix; all six decoding tests pass after explicit UTF-8
decoding. No baseline, guard, timeout or test assertion is weakened. Implementation/hold
blockers remain explicit release gates after definition closes, with an otherwise-
qualifying negative test. That
hosted run records 2,184 passing tests, 31 skips and one failure; the skips and
failed run provide no acceptance credit. Final-head hosted reruns remain required.

Local Markdown links added by this program are checked against actual paths.
An inherited gap-audit link to `repos/metis/docs/adr/0003-framework-conformance.md`
does not exist at its recorded Metis gitlink; it remains unchanged and is not
reported as a passing link. Inventory source links retain exact commits except the explicit
PyTorch minor-version label; exact source explains that label while the published build revision still needs reconciliation. Provider audit independently checks
77 immutable source links/line bounds and 13 manifest hashes. No provider
build/test/performance result is generated or credited by this change.

## Independent review challenges resolved

- Native C callback/member extraction had merged distinct APIs; scoped
  identities and release-derived regressions restore 53 distinct records.
- Mutable latest PyPI metadata prevented durable reproduction; extraction now
  uses exact-version metadata and retains latest-selection observations.
- The masked-array package lacked its reduction prerequisite; WP-011 now
  depends on WP-010 and the gate checks all such edges.
- Evidence must bind the actual comparator and companion versions, owner
  candidate revision, every coverage class and explicit execution device.
- Repository status labels require exact executed exit records; final reviews
  are external to avoid a Git-hash self-reference. Dirty/ignored input drift
  cannot acquire exact-head qualification; Git line-ending normalization is
  tested with a real CRLF checkout.
- Runtime profiler/debug APIs retain Coeus ownership and exact provider revisions;
  Atlas owns a separate benchmark/parity orchestration contract.
- Source manifest membership/aggregates and hosted extractor-test collection
  are enforced; generator reconciliation preserves existing owner holds and
  review pointers.
- A partial mapping cannot become specified by changing its status or deleting
  obligations: every mapping binds a hashed source entry and specification
  requires an explicit positive whole-API source-definition marker.
- Replay caches bind exact frozen tree identities, and NumPy metadata witnesses
  are regenerated from cached primary source rather than accepted as seeded JSON.
- Scanned NumPy/TF/Keras files also bind canonical manifest hashes and pinned
  tree blobs. Self-consistent stale manifests and undeclared files are rejected.
  Isolated-cache tests cover relative paths, the TF extra-source fetch entry
  point, and NumPy's flattened supplemental mirror artifact.

Independent review of the final committed diff and required hosted CI remain
mandatory before integration. The draft state is intentional. Existing global
CI may report fleet/provider failures outside this planning change; diagnose
those with their owners rather than weakening requirements.

## Definition blockers and next concrete work

WP-001 must enumerate and disposition every unexpanded autodoc/member,
guide/notebook/prose capability, version/patch mismatch and external namespace
(C++/extension APIs, Keras inheritance, legacy graph/session and companion
serving/mobile/browser/tooling). WP-003 must then map every retained public
identity to canonical operations and explicit framework semantics, dtype/device/
layout/gradient/domain classes, cases and targets. The ten recorded scope/behavior policies now
follow existing user/workspace direction, with rejected alternatives and impact
recorded; WP-004 still needs concrete provider design contracts and normal ADR
reviews where architecture changes. No API is removed because it is inconvenient,
unimplemented or unsupported on today's host.

Re-estimate and split the implementation envelopes after those classes are
known. The initial 110.4–324 engineer-week allowances and 70–205 week
unconstrained package-path calculation are neither a total-program bound nor a
delivery schedule; unknown extraction/semantic/hardware work can increase them.
WP-002's first validator slice is integrated through [Atlas #570](https://github.com/ryancinsight/atlas/pull/570)
at `2dbfeabc9f44de2d37e5cdfa2776bd272bb513bb`; public-surface/shared-contract
extensions remain active. Source closure and semantic mapping continue in separately reviewed slices;
no held Quinn/Apollo/provider repair is duplicated.

## Exact-head CI and bounded source checks

The preceding slice `756d2c80ed1a7b431cd26df2d4c1c8421d7b94dd` passes the
required [workflow/debt gates](https://github.com/ryancinsight/atlas/actions/runs/40283691029)
and [CodeQL](https://github.com/ryancinsight/atlas/runs/121442532253), with no
findings in independent exact-head review. The gitlink-policy job succeeds;
conditional provider compilation is skipped because pins are unchanged, with
no provider verification credit. Separate draft pytest jobs remain skipped.
New source/semantic changes require a new exact-head run.

Normal readiness executes the formerly draft-skipped fast and slow Python jobs
on `756d2c80`: both pass in [40292702283](https://github.com/ryancinsight/atlas/actions/runs/40292702283).
Fresh effective policy requires lint/debt and no GitHub approval rule; independent
source review remains mandatory and is completed. Merge #570 is verified at
`2dbfeabc`; only CI/security actions and no deployment record are observed.
The dependent #571 branch incorporates that main revision before its renewed
exact-head review and validation. This bounded tooling delivery does not close
the program definition or any provider's 1.0 qualification.

For the dependent source-disposition PR, feature-branch targeting did not start
Atlas's CodeQL analysis. Retargeting alone also left the observed `1ee5e596`
head without a CodeQL run. Keep the dependency on #570 explicit, target `main`,
and verify actual analysis on the subsequent head event. Neither absent checks
nor results belonging to a predecessor revision satisfy the final-revision gate;
no workflow/security configuration is weakened to obtain a passing label.

Four cached source-audit pipelines run without importing a framework. Independent
source checks verify 437 NumPy, 164 JAX, 40 PyTorch and 4,134 TF/Keras file
identities. NumPy's 11 static/artifact checks, JAX's six source checks, PyTorch's
four negative mutations and TF's 12 static/analytical checks are source-audit
evidence only. Replayed source/semantic tables match the captured bytes. These
checks do not replace reference execution, Atlas implementation tests, native
hardware qualification or benchmarks.

The [source-disposition follow-up](reference/closure/dispositions.md) adds JAX
selection, PyTorch parser/Storage/layout and Keras packaging/import distinctions.
Its four isolated cached replays compare stable outputs byte for byte; seventeen
NumPy, ten JAX, nine PyTorch and eleven Keras source checks pass. Those counts are separately
scoped and grant no runtime or semantic parity credit.

Public-scope independent code review reproduces and corrects audit release
relabeling, source/normalized route drift and Atlas triage counting as provider
ownership. Capture and validation now share source normalization, bind every
Torch row and audit header to the frozen release, and reject those false routes.

Draft PR creation for the public-scope branch is denied by GitHub integration
HTTP403 (Resource not accessible by integration). Readback finds no matching
PR. The source branch is pushed; no PR CI, merge or release is inferred. The
creation operation stays stopped without an alternate route. Independent code
review additionally checks predecessor compact-row/index/table integrity against
every frozen primary declaration, rejecting duplicate, null and mismatched rows.

The end-to-end workflow integration adds six focused tests, for 121 after
integration with the reviewed public-scope parent. It checks 24 workflow
contracts,58 unrun scenarios,29 export profiles,206 source receipts/217 anchors,
30 unresolved companion pins and eight planning directions. Fourteen named
mathematical witnesses have truth checks and 12 deliberately wrong numerical
fixtures fail; malformed dimensions and unregistered witnesses also reject.
Schema/traceability rejection tests preserve unrun states, compute/assertion
instructions, exact source/version joins and captured-review membership. None
is an executed framework or native target acceptance case.


## Core tensor semantic slice

The [core model](core-tensor/README.md) adds 39 source overlays and 37 partial
mappings, with no admissions or qualification promotions. Its 125 API targets
represent 118 distinct source programs, all unrun. Eight mathematical witnesses
check exact outputs and their defining boundary conditions; eight wrong outputs
reject. Source identity, owner, capture membership, original case binding, typed
no-credit states and line/hash bounds have adversarial guards. These are
analytical/schema checks, not framework/native execution.

Independent source review corrects JAX list-versus-array indexing inputs and
NumPy getter-versus-setter wording before acceptance. Independent model review
finds eager construction of unused coordinate pools and witnesses losing their
named boundaries. The fixes return an empty iterator before pool allocation and
validate each defining relational condition. Original findings remain recorded.
The historical connector denial remains recorded. Later explicit CLI direction
permits creation of PR#572 without retrying that connector. Local/source checks
supply no hosted CI or release gate. Definition qualification remains false.

Final local validation of the core slice passes139 parity tests with zero skips,
the canonical check/report, Markdown link checks and board lint. Independent
model checks cover7,225 broadcast pairs,9,261 triples,58,536 storage descriptors,
15,885 typed slices,655 storage adjoints and30,788 flatten cases. Those are
finite analytical checks of this model, not provider/reference API tests or an
exhaustive domain proof. Independent source reviews bind exact7c169acf and
875d1411 packet manifests; final Atlas revision review remains separate.

The public/workflow source deliveries are now merged as PR#572/#573, in order,
with unchanged package versions, gitlinks and CI workflows. Both execute actual
ready-state fast/slow pytest plus CodeQL/conformance at their reviewed heads.
Workflow integration preserves the entire reviewed da03 tree. Core integration
against main de9d428d also preserves the saved510410f2 tree before this status
receipt update. Fresh exact-head core review/hosted gates remain mandatory; no
whole-program qualification follows from the completed planning deliveries.

## Frozen JAX dtype policy increment

The [versioned policy](dtype-policy/README.md) losslessly captures reviewed packet
`72206a73` and review `364896a2`, preserving nine IDs, all 9,256 finite source-symbol
pairs, 18 unrun targets, ten wider gaps and eight ordinary CP02 evidence gaps.
The raw workflow record stays immutable; the derived disposition requests evidence,
not user scope reduction. Exact source/review pins, graph edges/joins/guards,
owner/prerequisite/API/case/source links and false-stage-credit rejection are
inputs to the actual checker/report and committed-input gate. Source-only
checks grant no API/runtime/backend/performance/release qualification.

Run `PYTHONPATH=scripts python3 -m unittest scripts/tests/test_parity_dtype.py -v`
for the bounded adversarial suite. Canonical validation uses portable exact span
bytes and signatures; original interpreter-specific AST-render hashes remain
immutable captured provenance. The original packet replay is recorded separately
and imports no numerical framework. No full third-party sources are vendored.

Core prerequisite #574 merges exact head `11406055` as `f642337d` after parent-verified
fast/slow40339245066, CodeQL40339117660 and conformance40339121408 passes and
mandatory exact-head review (139 tests, zero skips). The new local dtype candidate
requires separate final-head review and hosted checks before external delivery.

The authored dtype tree passes 155 parity tests with zero skips, including 16
new dtype conservation/adversarial methods. The checker/report, 19 added canonical
local links, board index and artifact budget pass. Expanded backlog remains1,000
lines and gap audit333; board lint retains advisory historical stale-item,
commit-reference and live-mention reports. No framework/provider or hardware test
is credited by these source checks.

Canonical review of saved `ba1faa3` then exposes two gaps the initial155 checks
did not cover: supplier/API ownership ambiguity (`astype` is canonically
Coeus/TEN-OPS while Eunomia supplies scalar policy), and a reindexed witness
header that claims API/runtime credit. Both regressions reproduce before repair.
The corrected joins distinguish policy suppliers from exact current mapping
associations (four mapped, five explicitly unmapped). Strict source-only wrapper
schemas reject unsupported credit, canonical-review approval labels, wrong
17/44 counts and duplicate CP02 IDs even after real artifact reindexing.

The corrected authored tree passes159 parity tests, zero skips, including20
dtype methods and copied-program full-loader adversaries with a valid reformat/
reindex control. Early wrapper validation retains all cases while reducing the
focused suite from65.7s to17.8s; the full suite completes in47.7s. Main mappings,
source722/review364, all9,256 graph pairs and raw CP02 history stay unchanged.
All18 acceptance targets remain unrun; exact-head clearance remains required.


## NumPy native dtype integration

Program .9 retains the .8 JAX index's immutable introduction version and every
JAX source/review/mapping/raw-CP02 byte. The new source-specific NumPy index
captures 16 accepted artifact roles with 78 file receipts, 129 functions / 131
spans, 576 symbolic relations, two illustrative unobserved ABI profiles, eight
existing IDs, ten partial families, 47 unrun cases and eight open gap groups.
No API denominator or mapping-stage changes occur. The three existing partial
query mappings remain Eunomia; five supporting IDs remain unmapped. Two source
families preserve the unregistered INTEROP-NATIVE prerequisite explicitly.

The initial NumPy integration suite runs 38 tests with zero skips. It rejects corrupted
physical artifacts after their index hashes are recomputed, validates exact
typed credit/count/role/provenance schemas, checks function quote/body hashes and
registered resolver phases, independently reconstructs source symbolic cells and
both illustrative matrices, and accepts a valid reformat/reindex control.
The combined initial parity suite passes 197 tests, zero skips, in 50.3 seconds. The
canonical capture regenerates 24 artifacts byte-identically. All 108 canonical
Markdown links pass with zero missing files/anchors; the combined backlog stays
at 1,000 lines and gap_audit at 333, within unchanged budgets. Changed Python
files byte-compile and whitespace checks pass.

Independent review of `78d7655d` then exposes nested source offsets that those
checks did not reject: Boolean/integral-float family/case indices, a float
correction index, and the copied mapping selector inside that correction.
The NumPy successor resolves all 196 selectors through exact typed source
containers and identity/position joins. The copied source contract has an exact
nested schema and resolves the actual canonical mapping's source hash and row;
consistent hashes cannot replace the mapping/reference identity check. Early
component preflight retains every later lossless capture and source check.

The focused NumPy suite now passes 45 methods with zero skips, including all
57 family/case float aliases, Boolean aliases, both correction selectors and
full copied-program reindex probes with valid integer/reformat controls. The
combined parity suite passes 210 tests with zero skips. Source packet `04e6d40c`,
review `710b8e1d`, JAX data/index, mappings, raw CP02 history and all API stages remain
unchanged. This local correction requires independent review of its final
committed head and supplies no framework/provider execution or release credit.

These are source/tooling checks. The accepted research review's 29 tests and
211-artifact replay remain original-packet evidence; they do not execute the
47 API/provider specifications or approve this canonical candidate.

The prior result_type wording receives a source-linked annotation rather than
history deletion: single-input Python-int discovery can depend on range, while
multi-input exact weak scalar abstraction is narrower. The temporal 2001ms-to-2s
integer-quotient behavior remains an unresolved frozen-binary comparison; no
reference-bug waiver or observed divergence is claimed. Callback programs,
complete descriptors, actual ABI/builds, payload conversions, device/AD,
performance and final-revision release gates stay open. No network/auth,
provider build/import, push, PR, merge or deployment occurs in this local slice.

The protected [#551 shared-tool handoff](execution.md#protected-shared-tool-prerequisite-observed-october-26) retains the exact Aequitas parser mismatch, last-observed failing draft head and original integrator/continuation as history. The user-approved replacement task `01a17995-4c0b-701d-8625-8650165230c2` now continues SAME #551 with existing work preserved; tooling/reviews/coherence/delivery remain unqualified and no current remote head is asserted; source presence is not authorization to adopt prepared tools. Earlier provider holds and historical receipts remain intact.


## Torch repaired native dtype integration

Program .10 retains the exact repaired `a34fc711` source packet and `013862e7`
same-reviewer source-only acceptance. Initial `697b0c74`/`3ac30501` history is
preserved, including both repaired material findings. The canonical capture
keeps selected source/receipt/proof artifacts rather than full foreign source
files or the 18 MiB source/history bundle.

Ten admitted partial contracts, 47 native enum identities, 196 core lookup cells,
2,209 promotion pairs, 2,209 cast-permission pairs, 45 receipts, 88 spans, 66
UNRUN framework cases and 14 open gaps retain separate denominators. Current
canonical API associations are three partial and seven unmapped; proposal,
scalar supplier and actual implementation ownership remain distinct. No API
mapping stage changes or execution/performance/release credit occurs.

The checker independently reconstructs finite source rules and helper maps,
checks exact typed aggregate/status/scope/ID/source/ownership roles, enforces
integer source selectors, and validates tagged rank-zero complex/gradient
fixtures with six input-sensitive exact-rational controls. Physical-file
corruption probes recompute artifact indexes before rejection. Valid reformat
and consistently changed analytical controls remain valid. Full public parsing,
registry, descriptor/payload/layout/device/AD/error and numerical qualification
remain open. Three subordinate native acceptance packages remain not ready;
ordinary evidence/design work does not become a new user scope decision.

JAX/NumPy source/index/review/mapping/raw-CP02 bytes and fixed .8/.9 introduction
versions remain consumed by the new enclosing program. The inherited CI setup
and #551 protected-owner handoff are retained. No network/auth, framework
imports/builds, provider or protected branch edits, PR/push/merge or publication
occurs. Independent canonical exact-head review and delivery remain parent-owned.

At original Torch author commit `3a06bed1`, canonical tooling verification runs
all **231 parity tests with zero skips** in 48.990 seconds. Thirty-one Torch tests include real copied-file,
reindexed corruptions, valid reformat controls, independently reconstructed
source relations and six input-sensitive complex controls. The repaired source
packet's original 28 tests remain separate historical evidence. All 66
framework/provider acceptance cases remain UNRUN.

Two earlier whole-suite attempts hit an incorrectly applied 60-second Python
bound; those failed observations are retained. The global strict 60-second rule
names `cargo nextest`; existing Python fast CI has a 10-minute whole-job bound.
No repository timeout changes. Measured table validation removes repeated
scalar JSON encodings and constructs invalid-cell diagnostics only on failure.
The original canonical serializer remains the equivalence oracle across scalar
subclasses, IntEnum, bool/int/float distinctions, huge integers, Unicode and
surrogate strings, empty and nested values. All ten canonical tables, containing
90,638 rows, retain exactly the original columns, value tables and row indices.
Profiled canonical calls fall from 592,794 to 174,516; this is tooling evidence,
not a provider performance claim or a waiver for an incomplete run.

The 32-file Torch capture regenerates byte-identically. All 46 protected prior
JAX/NumPy policy artifacts, mappings and raw CP02 retain their base bytes.
Canonical check/report, 129 Markdown links, board index, unchanged 1,000-line
combined backlog budget, byte-compilation and whitespace checks pass. Definition
and release qualification remain blocked by incomplete scope, unrun evidence
and pending independent review; exact committed-input checks follow the local
commit, without granting any parity qualification.

### Shared selector successor integration

The normal local merge of NumPy selector successor `010fc126` preserves the
Torch .10 source/optimization history and the NumPy .9/JAX .8 introduction
versions. The only backlog conflict retains both sets of obligations. Torch's
local selector function is removed; endpoint, case and receipt joins use shared
`source_entry_at` and its `source_selector` component checks. Each join also
requires the exact expected position and selected source-object identity.

Copied-file probes recompute artifact indexes before rejecting Boolean,
floating, negative, string and container offsets, empty paths, wrong rows,
overlong paths and out-of-range offsets. Shared root/leaf path semantics and
valid reformat controls remain accepted. No compatibility resolver alias or old
`core.entry_at` import remains. These checks repair traceability tooling only;
all 66 Torch source-target cases and 14 gaps retain their unqualified states.

The merged successor runs the unchanged complete parity discovery: **245 tests,
zero skips, 85.860 seconds**, within an explicit 600-second local verification
bound derived from the existing fast-Python CI job. Repository timeouts remain
unchanged. The 83 focused Torch/NumPy/shared-selector tests also pass. All 46
unique prior source/index/review/mapping/raw-CP02 artifacts match `010fc126`
bytes, and all 32 Torch capture artifacts match `3a06bed1` and regenerate
byte-identically. Markdown links, board index, unchanged 1,000-line backlog
budget, static compilation and whitespace checks pass. Independent canonical
exact-head review, hosted checks and source-target execution remain pending.

### Torch canonical review repairs

Independent review of `e09cb3b4` records P2 conditional-evidence weakening and
P3 scalar error normalization in receipt
`061f7d35998c1083842a6e6f020b0a66bc141d3d737499cad4ad48f799469f3d`.
New regressions first reproduce ten failed assertions and three raw TypeErrors;
that failed observation remains retained. The repaired focused suite passes all
45 Torch/table tests with zero skips in 24.659 seconds.

One shared construction supplies approved package gap/case/evidence obligations
to capture and validation. Ordered evidence roles require exact nonempty text;
missing, duplicate, substituted or weakened obligations reject after real file
copy/reindex, including the full loader. Valid analytical-input changes remain
accepted. Scalar base-accessor failures now preserve the original ParityError
boundary; accepted JSON subclasses and every source artifact remain unchanged.
These are canonical tooling repairs pending the same reviewer's final-head
assessment. All 66 target cases and 14 source gaps remain unqualified. Pending
provider qualifications and protected-owner approval receive no execution credit.

## Accepted public-surface evidence increment

The program.11 increment captures only the accepted TF 492 and JAX/Torch six-row source
packets and their exact independent review receipts. The existing 498 raw IDs,
publicness classifications, source signatures, required workflow relations and
unmapped canonical associations remain unchanged. The two original-source
reviews do not approve this canonical candidate or grant semantic/runtime credit.
The reviewed admission interface remains nonoperative; no internal-source label
or proposal subtracts an obligation. Live mapping owners are derived from actual
canonical mappings, separately from frozen `20ae8d85` source routing facts.

Source-only checks cover exact selected-byte reconstruction, source/path/blob
receipt lineage, portable spans/AST signatures, no-credit/count/schema guards,
and real copied/reindexed attacks and formatting controls. Four complete JAX
configuration spans remain digest-only rather than vendored source. Full source
analysis replay remains available through the explicit original local packets;
normal validation is portable and consumes only committed Atlas inputs. Local
check/test results and exact consumed-input commitment are recorded with the
local review handoff; independent exact-head review and actual hosted gates
remain mandatory before any external delivery. No provider or native execution,
new source acquisition, rendered-route retry, or GitHub action occurs here.

The source-capture checks at `5b0c92a5` pass 17 tests with zero skips: 45 physical-file
negative mutations are rejected after recomputing the relevant indexes; valid
JSON/column-dictionary reformatting and a cache-free copied-tree control pass.
The local producer replay verifies the original 199/265-file manifests and
reproduces all 48 captured canonical files byte-identically. Before actual-main integration, link checking scans
18 Markdown files /123 links with no missing files or anchors. The board index
and the combined 1,000-line backlog budget pass without changing the board count.
The historical-source regression now asserts immutable JAX.8/NumPy.9 role paths,
introductions and consumption of every indexed artifact independently of the
current program version; no source pin or validation obligation is weakened.

Before actual-main integration, local source-evidence commit `5b0c92a5` passes
**227 lightweight parity tests, zero skips**.
The previous run's one failure is retained in the local handoff: it was the
superseded latest-program.9 assertion, corrected by the stronger historical
introduction/consumed-input checks above. No native or framework computation ran.

The parent-directed integration includes actual merged main `05c8ccc8`, carrying
Torch program.10 from #577. All 32 incoming Torch capture files remain
byte-identical to that main revision; JAX.8 and NumPy.9 introductions and source
bytes remain fixed. Program.11 retains the separate public-evidence capture and
all 498 unresolved classifications without changing any API stage or denominator.
The exact final integrated commit, consumed-input proof and final lightweight
checks are recorded in the local review handoff. External delivery and fresh
hosted qualification remain parent-owned; no unrelated TF conversion packet is
admitted by this integration.

The first integrated run at `7f4e2674` executes 266 tests and retains one failed
latest-program.10 assertion in the incoming Torch harness. Its correction checks
the immutable Torch.10 index hash, source role, introduction and consumption of
every indexed artifact; all original ID/stage/source-count assertions remain.
No captured Torch source bytes or source/runtime status changes. The final
exact-head run belongs to the review handoff, rather than replacing that failed
run with passing evidence.

A later trusted parent ownership update admits the user-approved SAME-PR #551
replacement and retains the original owner/pending-decision record as history.
It grants no tooling, coherence, delivery or API qualification; Leto retains the
heavy-build slot. This lane performs no #551 lookup, contact or branch action.
