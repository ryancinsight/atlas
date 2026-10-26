# Validation and remaining definition work

Program 2026-10-26.1. Exact candidate identity and current hosted results belong
in the draft PR; local evidence here describes the authored tree and commands,
not a final merge/release certification. [Contracts](contracts.md).

## Recorded candidate surface

| Frozen reference | Candidate declarations | Distinct symbol spellings | Extraction state |
| --- | ---: | ---: | --- |
| NumPy 2.5.4 | 2,718 | 2,717 | Incomplete: 65 explicit declaration/expansion gaps and further prose/generated scope |
| JAX 0.12.0.1 | 1,678 | 1,678 | Incomplete: 119 autodoc expansion gaps and further prose/generated scope |
| PyTorch 2.14.1 | 9,066 | 9,066 | Complete parsing of 2.14 inventory; patch semantics, C++ and companion surfaces unclosed |
| TensorFlow 2.21.0 + Keras 3.15.1 | 24,589 | 23,379 | Complete parsing of selected source declarations; documentation drift/inheritance/companion scope unclosed |
| Total | 38,051 | 36,840 | Not a complete public API denominator |

PyTorch additionally retains 8,944 documentation/label records. Those are
source evidence for further capability extraction, not automatically API
obligations. Source-specific inventories retain unstable/private-spelling/
deprecated/legacy candidates for review. There are **zero reviewed API
mappings, zero qualification evidence records and no qualified repositories**.
The 66 family contracts route future work; they do not map these declarations.

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

The focused suite executes **57 tests, zero skips**: 40 gate/traceability tests
and 17 source-extractor tests collected by an import-only wrapper in
`scripts/tests`. Hosted `pytest scripts/tests` therefore collects the same
extractor tests without duplicating assertions. Source extractors regenerate
byte-identically from their independently hash-verified caches. Byte compilation
and whitespace checks pass. The board index is regenerated after correcting
an inherited malformed heading, retaining blocked ownership and the publisher
review link; the combined backlog stays at 999 lines within its 1,000-line
budget. Historical unrelated stale-citation reports remain advisory.

Local Markdown links added by this program are checked against actual paths.
An inherited gap-audit link to `repos/metis/docs/adr/0003-framework-conformance.md`
does not exist at its recorded Metis gitlink; it remains unchanged and is not
reported as a passing link. Inventory source links retain exact commits except the explicit
PyTorch minor-version inventory mismatch. Provider audit independently checks
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
layout/gradient/domain classes, cases and targets. WP-004 must obtain normal
review for all nine decisions. No API is removed because it is inconvenient,
unimplemented or unsupported on today's host.

Re-estimate and split the implementation envelopes after those classes are
known. The initial 110.4–324 engineer-week allowances and 70–205 week
unconstrained package-path calculation are neither a total-program bound nor a
delivery schedule; unknown extraction/semantic/hardware work can increase them.
The first implementation slice is WP-002's real validator, locally tested and
awaiting draft-PR integration. The next unowned execution is reference closure,
not a duplicate of the held Quinn/Apollo/provider repairs.
