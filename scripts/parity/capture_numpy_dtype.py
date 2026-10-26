"""Capture an accepted local NumPy source packet; no acquisition or framework import."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlas_parity_dtype import NO_CREDIT
from atlas_parity_numpy_dtype_capture import PREFIX, PACKET_SHA, REVIEW_SHA, SELECTED
from atlas_parity_numpy_dtype_joins import expected_joins
from atlas_parity_numpy_dtype_sources import expected_bindings
from atlas_parity_tables import pack


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--atlas-root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    packet, root = args.packet.resolve(), args.atlas_root.resolve() / 'docs/parity'
    destination = root / PREFIX
    destination.mkdir(parents=True, exist_ok=True)
    manifest_bytes, review_bytes = (packet / 'manifest.json').read_bytes(), args.review.read_bytes()
    assert sha(manifest_bytes) == PACKET_SHA and sha(review_bytes) == REVIEW_SHA
    manifest = json.loads(manifest_bytes)
    for name, receipt in manifest['files'].items():
        data = (packet / name).read_bytes()
        assert sha(data) == receipt['sha256'] and len(data) == receipt['bytes'], name
    def write(name, value):
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n')
    def raw(name, data):
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    raw('captured/manifest.json', manifest_bytes)
    raw('independent-review.json', review_bytes)
    captured, documents = [], {}
    for name in sorted(SELECTED):
        data = (packet / name).read_bytes()
        if name == 'README.md':
            paths, storage = [PREFIX + 'captured/README.source.txt'], 'original-bytes'
            raw('captured/README.source.txt', data)
        elif name == 'inputs/frozen-tree.json':
            paths, storage = [PREFIX + 'captured/' + name], 'original-bytes'
            raw('captured/' + name, data)
            documents[name] = json.loads(data)
        elif name == 'policy-tables.json':
            value = json.loads(data)
            cells = value['safe_policy'].pop('cells')
            write('table-policy.json', value)
            write('safe-pairs.json', pack(cells, {'role': 'symbolic_source_relation_not_descriptor_or_runtime_legality', 'source_cells': 576}))
            value['safe_policy']['cells'] = cells
            documents[name] = value
            paths, storage = [PREFIX + 'table-policy.json', PREFIX + 'safe-pairs.json'], 'policy-with-column-cells'
        else:
            value = json.loads(data)
            encoded = (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()
            if encoded == data:
                write('captured/' + name, value)
                storage = 'compact-json'
            else:
                raw('captured/' + name, data)
                storage = 'original-bytes'
            documents[name] = value
            paths = [PREFIX + 'captured/' + name]
        captured.append(dict(original_path=name, paths=paths, sha256=sha(data), storage=storage))
    capture = dict(schema_version=1, source_manifest_sha256=PACKET_SHA, independent_review_sha256=REVIEW_SHA,
        captured=captured, full_source_files_vendored=False, capture_complete_for_selected_artifacts=True,
        original_json_serialization='json.dumps(sort_keys=True,separators=compact,ensure_ascii=False)+newline',
        research_source_files=78, research_sealed_files=211,
        original_review_scope='accepted_bounded_source_definition_only_not_canonical_candidate_review')
    write('capture.json', capture)
    capabilities = {r['id']: r for r in json.loads((root / 'capabilities.json').read_bytes())}
    mappings = {r['id']: r for r in json.loads((root / 'mappings.json').read_bytes())}
    assigned = {identity: r['id'] for r in mappings.values() for identity in r['reference_ids']}
    write('joins.json', expected_joins(documents['native-contracts.json'], documents['acceptance-cases.json'],
        documents['source-witnesses.json'], capabilities, mappings, assigned))
    write('source-bindings.json', expected_bindings(documents['source-witnesses.json']))
    correction = documents['gap-disposition.json']['corrections'][2]
    write('correction-disposition.json', dict(schema_version=1, raw_mapping_id='core-numpy-numpy-result-type',
        raw_source_contract=mappings['core-numpy-numpy-result-type']['source_contract'],
        correction_entry=['corrections', 2], previous_statement=correction['previous'], corrected_scope=correction['correct'],
        history_mutated=False, mapping_stage_changed=False, whole_API_credit=False))
    artifacts = [dict(path=path.relative_to(root).as_posix(), sha256=sha(path.read_bytes()))
                 for path in sorted(destination.rglob('*')) if path.is_file() and path.name != 'index.json']
    write('index.json', dict(schema_version=1, version='2026-10-26.1', parent_program_version='2026-10-26.9',
        framework='numpy', reference_version='2.5.4', reference_revision='a3d0ef1df045b858e68115001fdabc930bb3b68c',
        artifacts=artifacts, status=NO_CREDIT, source_manifest_sha256=PACKET_SHA, independent_review_sha256=REVIEW_SHA,
        original_source_review_scope='accepted_source_only_not_exact_canonical_candidate_review',
        counts=dict(source_files=78, source_functions=129, source_spans=131, symbolic_safe_cells=576,
            illustrative_ABI_profiles=2, source_families=10, primary_IDs=3, supporting_IDs=5, unrun_cases=47, open_gaps=8)))
    print(json.dumps({'captured_original_roles': len(captured), 'indexed_artifacts': len(artifacts),
                      'full_foreign_source_files_vendored': 0, 'framework_cases_executed': 0}))


if __name__ == '__main__':
    main()
