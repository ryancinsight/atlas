"""Approved conditional package obligations derived from frozen source records.

Evidence lists are an ordered text schema: each position has the role below.
This is planning accountability, never provider readiness or execution credit.
Construction and validation consume this same definition; analytical controls
remain separate and may change when their computed values remain correct.
"""
from atlas_parity_schema import need

EVIDENCE_ROLES = (
    ('source_closure', 'coverage_domains'),
    ('typed_policy', 'query_oracles'),
    ('ownership_graph', 'precision_policy', 'qualification_gates'),
)


def conditional_packages(original):
    cases = original['acceptance-cases.json']['records'];gaps = original['remaining-gaps.json']['records']
    numeric = {'PT-DTYPE-PROMOTE', 'PT-DTYPE-CANCAST', 'PT-DTYPE-RESULT', 'PT-DTYPE-GET-DEFAULT', 'PT-DTYPE-SET-DEFAULT'}
    packages = []
    definitions = [
      ('TORCH-DTYPE-DEFINITION', 'atlas', [], cases, [g['id'] for g in gaps],
       ['Resolve public parsing/registry/default-context and native helper source gaps at exact revisions; all10 IDs remain partial.',
        'Materialize dtype/device/layout/AD/error valid and invalid domains before provider readiness; no unsupported exclusion or new user scope decision.']),
      ('TORCH-DTYPE-POLICY', 'eunomia', ['TORCH-DTYPE-DEFINITION'], [c for c in cases if c['contract_id'] in numeric],
       ['G-GENERATED-QUERY', 'G-DTYPE-REGISTRY', 'G-DEFAULT-DOC-CONFLICT', 'G-SCALAR-SYMBOLIC', 'G-CONTEXT'],
       ['Native typed representation and source-parametric promotion/cast/default policies with explicit ABI/context inputs.',
        'Execute exact enum/error/rank/wrapped/default analytical and pinned differential cases; metadata canCast is not value preservation or kernel availability.']),
      ('TORCH-DTYPE-TENSOR', 'coeus', ['TORCH-DTYPE-POLICY'], [c for c in cases if c['contract_id'] not in numeric],
       ['G-CONVERSION-KERNELS', 'G-TO-BACKWARD', 'G-ADD-GENERATED', 'G-ELEMENTWISE-LOOPS', 'G-REDUCTION-LOOPS', 'G-SUM-ORDER', 'G-DEVICE-LAYOUT', 'G-AD-BACKWARDS'],
       ['Preserve actual canonical API owners; Coeus facade is a proposal consuming Eunomia policy, Leto arrays, Hermes CPU and Hephaestus devices.',
        'Use explicit Storage/Compute/Accumulator/Result associated types with rounding, overflow, reduction and conjugation analysis; no hidden widening stand-in.',
        'Execute payload/alias/complex forward-reverse-higher AD cases and all legal device/layout branches with zero skips/fallback; qualify hardware benchmarks and exact-revision independent/registry/release gates.'])]
    for identity, owner, dependencies, subset, gap_ids, evidence in definitions:
        packages.append(dict(id=identity, planned_owner=owner, prerequisites=dependencies, readiness='not_ready_evidence_required',
            gap_ids=gap_ids, acceptance_case_ids=[c['id'] for c in subset], required_evidence=evidence, actual_implementation_owner=None))
    source_gaps = {gap['id'] for gap in gaps}
    source_contracts = {row['id'] for row in original['contracts.json']['records']}
    for package, roles in zip(packages, EVIDENCE_ROLES):
        need(set(package['gap_ids']) <= source_gaps and
             all(case['contract_id'] in source_contracts for case in cases) and
             len(package['required_evidence']) == len(roles),
             'Torch conditional source gap/case/evidence-role construction differs')
    return packages
