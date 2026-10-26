"""Real copied/reindexed artifact probes for source-only dtype wrappers."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from atlas_parity import load
from atlas_parity_dtype_capture import PREFIX
from atlas_parity_schema import ParityError

ROOT = Path(__file__).resolve().parents[2] / 'docs/parity'


class DtypeHeaderTests(unittest.TestCase):
    @staticmethod
    def reindex(copied):
        index_path = copied / PREFIX / 'index.json'
        index = json.loads(index_path.read_text())
        for row in index['artifacts']:
            row['sha256'] = hashlib.sha256((copied / row['path']).read_bytes()).hexdigest()
        index_path.write_text(json.dumps(index, sort_keys=True) + '\n')

    def test_policy_supplier_and_actual_API_mapping_are_separate(self):
        bundle = load(ROOT)
        joins = json.loads((ROOT / PREFIX / 'joins.json').read_text())
        mapped = 0
        for row in joins['endpoints']:
            self.assertIn('policy_supplier', row)
            self.assertIn('canonical_API_mapping', row)
            identity = row['reference_id']; association = row['canonical_API_mapping']
            mapping_id = bundle['assigned'].get(identity)
            if mapping_id:
                mapping = bundle['mappings'][mapping_id]; mapped += 1
                self.assertEqual(association, dict(state='mapped', reference_id=identity,
                    mapping_id=mapping_id, capability=mapping['capability'], owner=mapping['owner']))
            else:
                self.assertEqual(association, dict(state='unmapped', reference_id=identity))
            if row['symbol'] == 'jax.numpy.astype':
                self.assertEqual(row['policy_supplier']['owner'], 'eunomia')
                self.assertEqual(association['owner'], 'coeus')
                self.assertEqual(association['capability'], 'TEN-OPS')
        self.assertEqual(mapped, 4)
        self.assertEqual(len(joins['endpoints']) - mapped, 5)

    def test_copied_reindexed_source_credit_claim_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            copied = Path(folder) / 'parity'
            shutil.copytree(ROOT, copied)
            leaf = copied / PREFIX / 'source-witnesses.json'
            value = json.loads(leaf.read_text());value['whole_api_or_runtime_credit'] = True
            leaf.write_text(json.dumps(value, sort_keys=True) + '\n')
            index_path = copied / PREFIX / 'index.json'
            index = json.loads(index_path.read_text())
            row = next(r for r in index['artifacts'] if r['path'] == PREFIX + 'source-witnesses.json')
            row['sha256'] = hashlib.sha256(leaf.read_bytes()).hexdigest()
            index_path.write_text(json.dumps(index, sort_keys=True) + '\n')
            with self.assertRaisesRegex(ParityError, 'source witness.*credit'):
                load(copied)

    def test_all_normalized_wrapper_claims_reject_after_real_reindex(self):
        cases = [
            ('source-witnesses.json', lambda d: d.update(whole_api_or_runtime_credit=0)),
            ('source-witnesses.json', lambda d: d.update(tested='passed')),
            ('source-witnesses.json', lambda d: next(iter(d['witnesses'].values())).update(tested='passed')),
            ('index.json', lambda d: d.update(original_source_review_scope='exact_canonical_candidate_approved')),
            ('index.json', lambda d: d['artifacts'][0].update(tested='passed')),
            ('capture.json', lambda d: d.update(research_source_files=1)),
            ('capture.json', lambda d: d.update(research_sealed_files=43)),
            ('capture.json', lambda d: d['captured'][0].update(tested='passed')),
            ('capture.json', lambda d: d['source_packet_replay'].update(framework_cases_executed=1)),
            ('companion-disposition.json', lambda d: d['ordinary_evidence_gap_ids'].append('CP02-E01')),
            ('companion-disposition.json', lambda d: d.update(tested='passed')),
            ('pairs.json', lambda d: d.update(runtime_verified=True)),
            ('joins.json', lambda d: d.update(tested='passed')),
        ]
        with tempfile.TemporaryDirectory() as folder:
            copied = Path(folder) / 'parity';shutil.copytree(ROOT, copied)
            # Reformatting plus a real reindex is a valid positive control.
            leaf = copied / PREFIX / 'source-witnesses.json'
            leaf.write_text(json.dumps(json.loads(leaf.read_text()), indent=1) + '\n')
            self.reindex(copied)
            self.assertEqual(load(copied)['dtype_policy']['existing_mapped_API_associations'], 4)
            index = copied / PREFIX / 'index.json'
            index_original = index.read_bytes()
            for name, mutate in cases:
                leaf = copied / PREFIX / name;original = leaf.read_bytes()
                value = json.loads(original);mutate(value)
                leaf.write_text(json.dumps(value, sort_keys=True) + '\n')
                self.reindex(copied)
                with self.subTest(name=name), self.assertRaises(ParityError):
                    load(copied)
                leaf.write_bytes(original);index.write_bytes(index_original)


if __name__ == '__main__':
    unittest.main()
