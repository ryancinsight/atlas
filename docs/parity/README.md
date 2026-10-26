# Four-framework functional parity program

Program revision: **2026-10-26.9**. Protocol: **1**. State: **definition in progress; no 1.0 qualification**.

This is the canonical Atlas program for the October 26 instruction to complete
Coeus and its providers to full NumPy, JAX, PyTorch and TensorFlow functional
parity under Atlas design principles. It does not change any package version.
The [backlog entry](../../backlog/atlas-full-parity-001.md) owns coordination;
repository backlogs continue to own implementation. Earlier displacement and
bounded-scope completion claims do not establish this program's completion.

| Artifact | Authority |
| --- | --- |
| [Program manifest](program.json) | Version, frozen reference snapshots, completeness and required gates |
| [Reference inventories](reference/) and [source closure](reference/closure/README.md) | Extracted public API identities, source versions, hashes and extraction gaps |
| [Public surface and reusable contracts](reference/public-scope/README.md) | Conserved declarations, source publicness/views, signature links and planned provider routes |
| [Core tensor semantics](core-tensor/README.md) | Source-backed shape/dtype/layout/alias/effect/AD contracts and bounded acceptance packages |
| [Dtype source policies](dtype-policy/README.md) | Separate frozen JAX graph and NumPy native relations, source/case/supplier/API-owner joins and open evidence gaps |
| [End-to-end workflows](workflows/README.md) | Source-backed acceptance programs, export profiles, analytical witnesses and unresolved companion obligations |
| [Capability contracts](capabilities.json) | Single accountable owner, provider prerequisites, semantics, tests and qualification obligations |
| [Contracts and evidence protocol](contracts.md) | Coverage axes, evidence states, equivalence and rejection rules |
| [Work packages](work-packages.json) and [execution program](execution.md) | Dependency order, readiness, estimates, acceptance and handoffs |
| [Repository criteria](repositories.json) | Each registered repository's 1.0 entry and exit obligations |
| [Provider audit](provider-audit.md) and [source evidence](provider-evidence.json) | Revision-specific reconciliation of existing claims |
| [Decisions](decisions.md) | Architectural conflicts that cannot silently reduce scope |
| [Validation](validation.md) | Reproduction commands, executed checks, limitations and independent review |

The inventory denominator is the union of each frozen framework's public
documented surface, with framework/version/symbol/kind retained. Matching names
are not evidence of matching semantics. A capability family is a routing and
acceptance contract, **not** an assertion that its API rows are mapped or
implemented. Extraction completeness, per-API semantic mapping and execution
coverage have separate denominators. Unknowns remain visible and block the
corresponding milestone. A finite starter inventory never establishes a
complete denominator.

Run `python3 scripts/atlas-parity.py check` to validate the inventory and program,
`python3 scripts/atlas-parity.py report` for counts, and
`python3 scripts/atlas-parity.py qualify --gate definition` to evaluate the
definition exit. A structurally valid program may still fail qualification.
Release qualification additionally requires exact-revision evidence and all
repository and cross-repository gates. Skips, absent hardware, silent CPU
fallback and exclusions are never successful qualification.

Current source accounting: **38,096 candidate identities; two source-specified,
96 partial and 37,998 unmapped**. Candidate relation tables remain separately
visible and all four public denominators remain open. No execution or release
state is promoted by source mapping.

The public-surface capture links every admitted raw identity to one of 147
framework-specific reusable contracts. It preserves 498 publicness questions,
three source-internal candidates and nine documented extension hooks without
excluding any obligation. Planned family routes are separate from verified
implementation ownership and complete semantic mapping.

The workflow slice adds 24 partial acceptance families, 58 unrun scenarios and
29 export profiles. Fourteen mathematical witnesses have independent exact
checks; they grant no framework execution credit. All 30 companion pin/scope
records and concrete provider ADR approvals remain open. CP02's derived
evidence-required disposition preserves its raw captured decision label.
Existing native generic policies resolve architectural direction without dropping capabilities
or authorizing a foreign production runtime.

The [bounded source dispositions](reference/closure/dispositions.md) preserve
member-selection, parser and package/import distinctions. They refine required
acceptance cases without excluding candidates or granting execution credit.

The selected first implementation slice is the Atlas traceability/evidence
validator (WP-002). It enforces this distinction with rejection tests. Provider
repairs remain with their existing owners; no protected branch is modified.

The dtype-policy slice retains eight source graph/config views, 9,256 symbolic
pairs, 18 source clauses and 18 unrun targets. These refine nine existing IDs
without changing mapping stages. Ten wider gaps and eight ordinary CP02 evidence
gaps remain; no runtime/backend or whole dtype-legality claim follows.

The NumPy native supplement adds 10 partial source families, 78 source receipts,
129 function bodies / 131 hashed spans, 576 symbolic safe-table cells and two
illustrative ABI profiles. It links three existing query IDs and five supporting
IDs while retaining all 47 acceptance cases unrun. Actual API mapping associations
and numeric policy suppliers remain separate; no mapping stage changes. Full
descriptor/callback/payload/ABI/device/AD/performance qualification remains open,
including the temporal 2001ms-to-2s integer-quotient source question.
