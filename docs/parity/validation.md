# Validation and remaining definition work

Program 2026-10-26.3. Exact candidate identity and current hosted results belong
in the draft PR; local evidence here describes the authored tree and commands,
not a final merge/release certification. [Contracts](contracts.md).

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
SOURCE `mapping=specified`. Thirty-six constructor contracts plus `numpy.size`
remain partial, covering 59 declaration views. Another 38,035 candidate
identities are unmapped. All 38,094 not-fully-specified identities continue to
block definition completion. There are zero runtime qualification evidence
records and no qualified repositories. The 67 family contracts route ownership;
they do not convert candidate declarations into implemented capabilities.

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

The focused suite executes **87 tests, zero skips**: 70 gate/traceability tests
and 17 source-extractor tests collected by an import-only wrapper in
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
