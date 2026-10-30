# Independent review of public-scope admission design

Reviewed against Atlas `20ae8d85f6c3aa6a6712e4f0b823b5f066bdc008`, tree
`4741babc0cf80e7ca642f4f8e93006bd8724ead4`, and
`/tmp/atlas-public-scope-admission-plan-20261026.md`.
This is a design review. It changes no canonical file, admission, denominator,
evidence state or already reviewed PR #575 input. No network, framework import
or build is performed. The ongoing 498-row source audits are not repeated.

## Assessment and bounded design findings

The plan correctly separates raw retention from required public contracts and
rejects name-based exclusions. It needs the following interfaces before a gate
may stop requiring a literal internal declaration's API mapping.

1. **A candidate label cannot become an exemption.**
   `atlas_parity_scope_sources.classify()` currently turns NumPy
   `visibility="private"` into `internal_source_candidate`. In a detached object
   copy, changing only that field on the real `numpy.shape` source row changes
   the normalizer's result to the internal-candidate category without changing
   its source evidence. This is not a current gate bypass: all raw obligations
   remain retained and `definition_blockers()` still counts them. It proves why
   filtering those categories directly would be unsafe.
2. **Publicness, stability and intended use are different facts.**
   A private-stability or underscore spelling does not remove a documented
   extension or tooling workflow. The nine current Elastic protected methods
   remain required documented extension hooks. A future classification must
   distinguish their consumer contract from a genuine implementation-only
   declaration. Neither binary export nor public golden traversal alone proves
   intended public API; neither absence from generated docs nor a private label
   alone proves implementation-only scope.
3. **A private declaration correction must preserve observable functionality.**
   Removing an obligation to reproduce an internal type/layout is legitimate;
   removing public indexing, ufunc, extension, device or error behavior is not.
   A generic capability label or Atlas `PARITY-VALIDATOR` audit contract cannot
   stand in for concrete public/workflow clauses and their coverage. Reference
   implementation relationships must not mandate copying its runtime design.
4. **All gate readers need one derived requirement set.**
   Changing only `definition_blockers()` would leave snapshot semantics flags,
   mapping/report counts and release iteration with inconsistent meanings. A
   versioned admission interface and set-based migration are required. Stored
   aggregate counts must never control membership or qualification.
5. **The existing three internal candidates are not gate certificates.**
   They contain strong positive source metadata but no currently validated,
   row-bound admission certificate or concrete functionality-preservation
   links. Their source classification can be carried forward as evidence;
   `public_denominator_eligible=false` cannot discharge the present gate.

These are specifications needed for future implementation, not newly discovered
regressions in the conservatively approved `20ae8d85` gate.

## Current observations and count terminology

The current raw set is 38,096 exact reference identities. Its visibility audit
contains 18,396 documented-public rows, 19,190 export/view rows, nine documented
extension hooks, 498 unresolved rows and three internal candidates. Thus:

| Quantity | Current value | Meaning |
| --- | ---: | --- |
| Immutable retained raw identities | 38,096 | Extraction/history population, not a closed public denominator |
| Conservatively known-required candidate views | 37,595 | The three public/export/extension categories combined |
| Explicit publicness unresolved | 498 | JAX 3, PyTorch 3, TensorFlow 492; source audits remain in progress |
| Internal candidates awaiting admission proof | 3 | Still required by the current conservative raw gate |
| Proven internal exemptions accepted by current gate | 0 | No admission exemption interface exists yet |
| Conservative uncertain membership for a future interface | 501 | 498 unresolved plus three uncertified internal candidates |

The proposed 37,595 figure is not asserted to be the complete public API count.
All four extraction-completeness flags remain false. Known public additions
outside the admitted raw set, including the two underscored NumPy ufunc methods,
continue to block closure. Counting only an existing raw inventory cannot close
missing exports, generated/prose APIs, extension contracts or tooling workflows.

The current two source-specified mappings, 96 partial declaration views and
37,998 unmapped raw identities are unchanged. The existing conservative gate
still reports 38,094 incomplete raw semantic identities; no count is corrected
by this review.

## Recommended interface

Keep the primary inventories, original classifications, source/signature views
and captured audits immutable. Add a versioned admission sidecar bound to those
exact inputs. Require exactly one disposition per retained raw identity and
reject unknown, missing or duplicate identities. An old reader must not silently
accept a new admission protocol that changes its requirement semantics.

Each disposition should bind:

- Exact `reference_id` and the existing canonical `reference_sha256`, framework,
  reference release, source revision and inventory digest.
- Separate source facts: visibility evidence, intended consumer/use roles,
  stability/deprecation policy, aliases/views and contradictory evidence.
- A certificate ID where a literal API requirement would be discharged.
- A functionality-preservation disposition: concrete required targets and
  source-backed clauses, or an independently reviewed no-external-contract
  conclusion. A missing disposition is an open obligation.
- Audit custody separately from public/API/provider ownership. Atlas may own
  source triage; that does not assign implementation or prove functionality.

Derive, rather than trust a stored boolean, three disjoint admission sets:

```text
required_external_contracts
unresolved_membership
proven_internal_only

raw_ids = required_external_contracts ⊎ unresolved_membership ⊎ proven_internal_only
```

`required_external_contracts` preserves distinct roles for direct public APIs,
documented extension hooks and relevant tooling contracts. A source's private
stability label may coexist with a required extension/workflow contract.
Uncertified `internal_source_candidate` remains unresolved for this interface;
it does not become `proven_internal_only` by renaming its marker.

These three partition members are **raw reference-ID sets**. Separately maintain
`required_workflow_ids`, which can contain documented compound functionality
without a one-to-one raw declaration. The gate's typed obligation universe is
`required_reference_views ∪ required_workflow_ids`, with collision-free kinded
IDs. A required workflow cannot disappear merely because its supporting raw
helper is certified internal. Existing 24 workflow families are a starting
capture, not proof of a complete workflow denominator.

The common reader interface should return IDs and gaps, not just counts:

```text
validate_admission(raw_refs, source_audits, certificates, workflow_contracts)
  -> {raw_ids, required_reference_views, unresolved_membership,
      proven_internal_only, required_workflow_ids, preservation_gaps}
```

Only that validated result may feed report and qualification membership. An
unrecognized admission protocol must fail closed rather than falling back to
an old reader that silently ignores the new sidecar.

Keep semantic, implementation, test, differential, performance and release
states independent. Admission supplies no successful stage evidence.

### Source certificate requirements

A certificate that discharges a literal API obligation needs all of:

1. Exact row/signature/occurrence and baseline identity, not just a symbol name.
   A grouped certificate may cover several declarations only by explicitly
   enumerating each exact reference ID and record digest.
2. Positive source evidence that the named declaration is implementation-only,
   including bounded section context showing the assertion applies to that
   declaration. Adjacent public opaque structs must not inherit the assertion.
3. Frozen repository/path/revision, Git-blob and file SHA evidence, portable
   excerpt bytes with hashes and line bounds, and source-selection provenance.
   A URL and an asserted quote/hash are not independent content verification.
4. Separately recorded export, traversal/golden, documentation, intended-use
   and stability evidence. Record checked corpus boundaries and limitations;
   do not turn an incomplete search or unavailable rendered page into proof.
5. A disposition of every known conflicting public/extension use. Unresolved
   contradiction keeps membership unresolved; no majority vote or namespace
   heuristic resolves it.
6. An accepted independent source review bound to the exact certificate/packet
   content digest. Ordinary exact-candidate code review remains a separate gate;
   avoid a self-referential Git hash in the committed packet.
7. No `unsupported`/unimplemented/absent-hardware reason and no promotion credit.
   Reformatting cannot change the certificate's semantic assertion.

This needs ordinary source and code review under existing authorization, not a
new user permission request for a source-backed scope correction. A genuinely
irreconcilable public-behavior or architecture conflict remains explicit and
unresolved while other work continues.

### Functionality preservation

For each proven internal declaration, retain source-backed relationships to
actual required public/workflow clauses when it participates in their behavior.
Targets must exist, remain required and preserve the applicable signature,
value, effect/alias, error, dtype, device, gradient and execution distinctions.
Links to a family name alone, a triage record, another exempt-only cycle or a
nonexistent obligation cannot discharge this work.

Several helpers may support one public obligation without multiplying that
obligation; all source relationships remain retained. Conversely, a single
helper may support many framework-specific obligations. Sharing a target does
not prove their semantic equivalence or merge their tests.

A source-backed classification may establish that a literal private type is
not an API before all transitive functionality is fully specified. Report this
truthfully: internal classification can be accepted while functionality linkage
or required public coverage remains an explicit definition/release blocker.
Do not force an Atlas copy of a private reference runtime structure simply to
close a bookkeeping row. Public C ABI/protocol/extension contracts remain
required even when their implementation uses private structures.

## Required reader migration

| Reader | Required behavior |
| --- | --- |
| `references()` | Retain every original identity, occurrence and signature; extraction counts stay raw |
| `validate_bindings()` / `classify()` | Preserve candidate source facts; admission exemptions require validated certificates |
| Capture/regeneration tools | Add a separate deterministic admission overlay; do not rewrite sealed source audits |
| Scope inspector | Show raw classification, resolved admission, stability, certificate, required functionality and mapping independently |
| `load()` snapshot `semantics_complete` check | Use required external contracts plus required workflows; unresolved membership and incomplete source inventories block closure |
| `definition_blockers()` | Use set differences for required semantics, plus unresolved membership, incomplete preservation links, extraction gaps and existing decisions |
| Mapping/evidence validation | Preserve raw/history evidence and exact framework variants; only required coverage counts toward current qualification |
| Release gate | Qualify every required public/workflow coverage class, preserve repository/ADR/hardware/release gates; never filter an entire mixed mapping by one private variant |
| Report/index/docs | Derive each partition/count from IDs; report raw, required, unresolved, proven-internal and unresolved functionality separately |
| Committed-input/review gate | Include every certificate, source witness, review and overlay; ignored/untracked/stale evidence cannot qualify |

The new gate must not be `raw_count - internal_count`. It must prove all raw
identities are retained and classified, every unresolved membership still
blocks, all required public/workflow semantics are complete, preserved
functionality has no unresolved gaps, and the existing full-surface, review,
implementation and release gates still apply.

## Readiness of the existing three candidates

The exact records and canonical evidence are saved in
`three-internal-candidates.json`; the machine-readable assessment is in
`three-candidate-readiness.json`.

All three refer to NumPy 2.5.4 revision
`a3d0ef1df045b858e68115001fdabc930bb3b68c`,
`doc/source/reference/c-api/types-and-structures.rst`, Git blob
`2cd423fdd30a6f635415b22caf80cbc893fef4e3`, file SHA-256
`3a2fb5c06094bc8ff804417f7030e02f8afac616a93a9edcf3a6bbf10ab1685b`.
They preserve the internal-structures section at line1596 and a line1599
statement that they are inaccessible directly from Python and unexposed to the
C API. Their declarations are `PyUFunc_Loop1d` at1604,
`PyArrayMapIter_Type` at1610 and `PyArrayMapIterObject` at1616.

This is substantive positive private evidence, not an underscore heuristic.
The canonical audit, however, provides a declaration-line payload and an asserted
section statement/URL; it does not contain a validated admission certificate
with bounded section excerpts and functionality-preservation targets. Existing
independent review of the conservative classification is not a certificate
allowing the gate to discharge an API requirement. The generic private-audit
contract has no such concrete target links. All three are therefore promising
certificate candidates, not currently certified admission exemptions.

A follow-up can use those existing source pins to package and review the bounded
proof. This review does not fetch the source, invent missing links, re-audit the
498 unresolved rows or claim new source/API completeness.

## Evidence and recommended tests

`current-reader-observations.json` records the exact current counts and the
detached normalizer demonstration. `guard-test-matrix.json` supplies bounded
positive, negative, copied-artifact/reindex and migration cases. None has been
added to or executed as a new canonical admission gate.

The first implementation should follow accepted finite source packets, include
the whole reader migration and compare report/blocker output before/after.
Independent review must challenge certificate semantics as well as schema
validity. Tests should include the three candidates, the nine existing Elastic
extension hooks, a neighboring public opaque NumPy type, public aliases and the
known unadmitted underscored ufunc methods. No skipped test or source-only result
becomes runtime, hardware, performance or release verification.
