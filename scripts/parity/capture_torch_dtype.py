"""Local lossless repaired Torch source capture; no framework or network execution."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlas_parity_dtype import NO_CREDIT
from atlas_parity_torch_dtype import counts
from atlas_parity_torch_dtype_capture import PREFIX, PACKET_SHA, REVIEW_SHA, REVISION, SELECTED, ROW_FIELDS, original_bytes
from atlas_parity_torch_dtype_joins import expected_joins
from atlas_parity_torch_dtype_oracles import analytical_control
from atlas_parity_torch_dtype_sources import proof
from atlas_parity_tables import pack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, required=True);parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--atlas-root', type=Path, default=Path(__file__).resolve().parents[2]);args = parser.parse_args()
    root = args.atlas_root.resolve() / 'docs/parity';target = root / PREFIX;target.mkdir(parents=True, exist_ok=True)
    packet = args.packet.resolve();manifest_bytes = (packet / 'manifest.json').read_bytes();review_bytes = args.review.read_bytes()
    sha = lambda b: hashlib.sha256(b).hexdigest()
    assert sha(manifest_bytes) == PACKET_SHA and sha(review_bytes) == REVIEW_SHA
    manifest = json.loads(manifest_bytes)
    for row in manifest['files']:
        b = (packet / row['file']).read_bytes();assert sha(b) == row['sha256'] and len(b) == row['bytes'], row['file']
    def write(name, value):
        p = target / name;p.parent.mkdir(parents=True, exist_ok=True);p.write_bytes(original_bytes(value))
    def raw(name, data):
        p = target / name;p.parent.mkdir(parents=True, exist_ok=True);p.write_bytes(data)
    raw('captured/manifest.json', manifest_bytes);raw('independent-review.json', review_bytes)
    selected, captured = {}, []
    for name in sorted(SELECTED):
        data = (packet / name).read_bytes()
        if name == 'README.md':
            paths, storage = [PREFIX + 'captured/README.source.txt'], 'original-bytes';raw('captured/README.source.txt', data)
        else:
            value = json.loads(data);selected[name] = value
            if name == 'dtype-model.json':
                metadata = copy.deepcopy(value)
                for key in ROW_FIELDS:
                    rows, metadata[key] = metadata[key], []
                    write(key + '.json', pack(rows, {'role': key, 'qualification': 'source_only_not_public_kernel_registry'}))
                write('model.json', metadata)
                paths = [PREFIX + x for x in ['model.json'] + [key + '.json' for key in ROW_FIELDS]];storage = 'model-column-tables'
            else:
                paths = [PREFIX + 'captured/' + name];storage = 'compact-json' if original_bytes(value) == data else 'original-bytes'
                if storage == 'compact-json':write('captured/' + name, value)
                else:raw('captured/' + name, data)
        captured.append(dict(original_path=name, paths=paths, storage=storage, sha256=sha(data)))
    write('capture.json', dict(schema_version=1, source_manifest_sha256=PACKET_SHA, independent_review_sha256=REVIEW_SHA,
        captured=captured, full_source_files_vendored=False, full_history_vendored=False,
        capture_complete_for_selected_artifacts=True, research_source_files=45, research_sealed_files=156,
        original_json_serialization='compact_insertion_order_ensure_ascii_false_newline_or_original_bytes'))
    caps = {r['id']: r for r in json.loads((root / 'capabilities.json').read_bytes())}
    mappings = {r['id']: r for r in json.loads((root / 'mappings.json').read_bytes())}
    assigned = {i: r['id'] for r in mappings.values() for i in r['reference_ids']}
    write('joins.json', expected_joins(selected['contracts.json'], selected['acceptance-cases.json'], caps, mappings, assigned))
    write('source-proof.json', proof(selected['source-registry.json'], selected['source-witnesses.json']))
    cases = selected['acceptance-cases.json']['records'];gaps = selected['remaining-gaps.json']['records']
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
    configs = [((1,2),(3,-1),(2,1),1),((-2,0),(1,3),(-1,0.5),2),((0,0),(0,0),(0,0),0),
               ((0.5,-1),(2,0.5),(0.5,-2),-0.5),((-4,2),(0.25,-0.5),(4,0),0.25),((0,-0.5),(-1,2),(0,1),-2)]
    controls = [dict(id='TORCH-COMPLEX-ANALYTICAL-' + str(i), source_case_id='ADD-COMPLEX-GRAD',
        case=analytical_control(*values), runtime_executed=False) for i, values in enumerate(configs, 1)]
    write('acceptance-plan.json', dict(schema_version=1, scope='conditional_native_acceptance_not_implementation_or_ADR_approval',
        parent_work_packages=['WP-001', 'WP-003', 'WP-004'], packages=packages, analytical_controls=controls,
        framework_runtime_cases_executed=0, whole_API_credit=False))
    records = [dict(original_path=name, original_text=(args.review.parent / name).read_text())
               for name in ['independent-model-and-replay.json', 'independent-repair-checks.json']]
    write('review-proof.json', dict(schema_version=1, role='original_source_review_proof_not_canonical_or_runtime_approval', records=records))
    artifacts = [dict(path=p.relative_to(root).as_posix(), sha256=sha(p.read_bytes())) for p in sorted(target.rglob('*')) if p.is_file() and p.name != 'index.json']
    write('index.json', dict(schema_version=1, version='2026-10-26.1', parent_program_version='2026-10-26.10',
        framework='pytorch', reference_version='2.14.1', reference_revision=REVISION, source_manifest_sha256=PACKET_SHA,
        independent_review_sha256=REVIEW_SHA, artifacts=artifacts, counts=counts(selected), status=NO_CREDIT,
        original_source_review_scope='accepted_repaired_source_only_not_canonical_candidate_review'))
    print(json.dumps(dict(selected_original_roles=len(captured), indexed_artifacts=len(artifacts), full_foreign_source_files_vendored=0)))


if __name__ == '__main__':main()
