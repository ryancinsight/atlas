"""Lossless selected TF conversion source roles; historical context is inert."""
import hashlib
import json

from atlas_parity_dtype_headers import exact_fields
from atlas_parity_public_capture import original_bytes
from atlas_parity_schema import local_path, need, read_json

PREFIX = 'core-tensor/tf-conversion-20261026/'
PACKET_SHA = '67e6c982b00ed38936c66a65d0c192790c59db4da7b1337291c727022c2bc3a7'
REVIEW_SHA = 'c4de4542b6254a7ed1a056bd6b2f73c5b55fca7868a752492c39207a221de57d'
FROZEN_ATLAS = 'fd0efd9007235bede364fc6a4f26036a3bbe5204'
FROZEN_TREE = '3ec069926a406cbf3e22bf5fb9dac1108c36bded'
TF_REVISION = 'a481b10260dfdf833a1b16007eead49c1d7febf3'
KERAS_REVISION = '250b42181ce9f37df68319d8f4753ec89a349a43'
SELECTED = {'README.md', 'proposal.json', 'contract-specification.json', 'acceptance-cases.json',
    'implementation-plan.json', 'remaining-gaps.json', 'counts.json', 'source-receipts.json',
    'source-witnesses.json', 'correction-history.json', 'verification.json', 'mutation-results.json',
    'replay.json', 'canonical-joins.json', 'inputs/existing-api-identities.json',
    'inputs/capability-roles.json', 'inputs/atlas-observation.json', 'inputs/provider-snapshots.json',
    'inputs/existing-core-boundary.json', 'frozen-canonical/receipts.json',
    'history/predecessor-856a65a0/manifest.json', 'history/predecessor-e0759917/manifest.json',
    'review-history/856a65a0/FINAL_REVIEW_856a65a0.json',
    'review-history/e0759917/FINAL_REVIEW_e0759917.json'}
REVIEW_PROOFS = {'independent-git-source-audit.json', 'independent-math.json',
    'independent-valid-controls.json', 'original-attacks-recheck.json', 'numeric-recheck-summary.json'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def capture(root, index):
    paths, docs = [], {}
    for row in index['artifacts']:
        exact_fields(row, {'path': str, 'sha256': str}, 'TF conversion artifact')
        file = local_path(root, row['path'])
        need(row['path'].startswith(PREFIX) and file not in paths and sha(file.read_bytes()) == row['sha256'],
             'TF conversion indexed role/hash/duplicate drift')
        paths.append(file);docs[row['path']] = read_json(file) if file.suffix == '.json' else file.read_text()
    def get(name):
        need(PREFIX + name in docs, 'TF conversion artifact absent: ' + name)
        return docs[PREFIX + name]
    header, manifest, review = get('capture.json'), get('source-manifest.json'), get('independent-review.json')
    exact_fields(header, {'schema_version': int, 'source_manifest_sha256': str, 'independent_review_sha256': str,
        'selected': list, 'full_source_files_vendored': bool, 'full_history_vendored': bool,
        'capture_complete_for_selected_roles': bool, 'research_sealed_artifacts': int,
        'research_source_blobs': int, 'research_source_spans': int, 'original_serialization': str,
        'historical_context_role': str}, 'TF conversion capture')
    fixed = dict(schema_version=1, source_manifest_sha256=PACKET_SHA, independent_review_sha256=REVIEW_SHA,
        full_source_files_vendored=False, full_history_vendored=False, capture_complete_for_selected_roles=True,
        research_sealed_artifacts=320, research_source_blobs=21, research_source_spans=63,
        original_serialization='pretty_ascii_sorted_indent2_newline_or_original_bytes',
        historical_context_role='frozen_fd0_context_not_live_owner_mapping_or_approval')
    need({k: header[k] for k in fixed} == fixed, 'TF conversion capture provenance/scope differs')
    need(sha(original_bytes(manifest, 'pretty-ascii')) == PACKET_SHA and
         sha(local_path(root, PREFIX + 'independent-review.json').read_bytes()) == REVIEW_SHA,
         'TF conversion independently fixed manifest/review trust root differs')
    need(type(manifest['artifact_count']) is int and manifest['artifact_count'] == len(manifest['artifacts']) == 320,
         'TF conversion original320 artifact conservation differs')
    by_name = {r['path']: r for r in manifest['artifacts']}
    need(len(by_name) == 320 and review['result'] == 'accept_bounded_source_definition_only' and
         review['reviewed_manifest_sha256'] == PACKET_SHA and review['blocking_findings'] == [],
         'TF conversion accepted original source review differs')
    checks = review['checks']
    for key, value in {'source_blobs_unchanged':21, 'source_spans_unchanged':63, 'future_cases':30,
        'runtime_cases_executed':0, 'open_gap_groups':10, 'current_partial_ids':4, 'current_unmapped_ids':6,
        'canonical_files_git_proven':13, 'successor_sealed_artifacts_unchanged':320}.items():
        need(type(checks[key]) is int and checks[key] == value, 'TF conversion original source-review count differs')
    need(checks['canonical_git_commit'] == FROZEN_ATLAS and checks['canonical_git_root_tree'] == FROZEN_TREE and
         checks['actual_implementation_owner'] is None and checks['future_cases_status'] == 'all UNRUN',
         'TF conversion original source review identity/scope differs')
    original, selected_paths = {}, set()
    for row in header['selected']:
        exact_fields(row, {'original_path': str, 'path': str, 'storage': str, 'sha256': str}, 'TF conversion captured role')
        name = row['original_path'];need(name in SELECTED and name not in original, 'TF conversion source role duplicated/unknown')
        expected = PREFIX + 'captured/' + ('README.source.txt' if name == 'README.md' else name)
        need(row['path'] == expected and expected in docs, 'TF conversion exact selected coordinate differs')
        value = docs[expected]
        if row['storage'] == 'compact-json':
            need(name.endswith('.json'), 'TF conversion compact source role differs')
            data = original_bytes(value, 'pretty-ascii')
        else:
            need(row['storage'] == 'original-bytes' and name == 'README.md', 'TF conversion original-byte role differs')
            data = local_path(root, expected).read_bytes()
        need(row['sha256'] == by_name[name]['sha256'] == sha(data) and len(data) == by_name[name]['bytes'],
             'TF conversion lossless independently anchored source differs: ' + name)
        original[name] = value;selected_paths.add(expected)
    need(set(original) == SELECTED, 'TF conversion selected24 role conservation differs')
    proof = get('review-proof.json')
    exact_fields(proof, {'schema_version': int, 'role': str, 'original_texts': dict}, 'TF conversion review proof')
    need(proof['schema_version'] == 1 and proof['role'] == 'accepted_original_source_review_proofs_not_canonical_or_runtime_approval' and
         set(proof['original_texts']) == REVIEW_PROOFS, 'TF conversion review proof identity/scope differs')
    evidence = {r['path']:r for r in review['evidence']}
    for name, text in proof['original_texts'].items():
        need(type(text) is str and sha(text.encode()) == evidence[name]['sha256'] and len(text.encode()) == evidence[name]['bytes'],
             'TF conversion exact independent review proof differs')
        json.loads(text)
    expected = selected_paths | {PREFIX + p for p in ('capture.json', 'source-manifest.json', 'independent-review.json',
        'review-proof.json', 'joins.json', 'cases.json', 'plan.json', 'source-proof.json')}
    need(set(docs) == expected, 'TF conversion indexed active/captured role set differs')
    return original, docs, paths
