"""Typed source paths reject Python index aliases after real artifact reindexing."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from atlas_parity import load
from atlas_parity_dtype_capture import PREFIX
from atlas_parity_schema import ParityError, source_entry_at

ROOT = Path(__file__).resolve().parents[2] / 'docs/parity'


class SourceSelectorTests(unittest.TestCase):
    @staticmethod
    def read(path):
        return json.loads(path.read_text())

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, sort_keys=True) + '\n')

    @classmethod
    def reindex(cls, root, index):
        path = root / index
        value = cls.read(path)
        for row in value['artifacts']:
            row['sha256'] = hashlib.sha256((root / row['path']).read_bytes()).hexdigest()
        cls.write(path, value)

    @contextmanager
    def copied(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'parity'
            shutil.copytree(ROOT, destination)
            yield destination

    def test_resolver_preserves_typed_keys_leaves_and_root_selection(self):
        document = {'rows': [{'values': [3, 8]}, 9], '0': False}
        self.assertEqual(source_entry_at(document, ['rows', 0, 'values', 1], 'valid'), 8)
        document['rows'][0]['values'][1] = 17
        self.assertEqual(source_entry_at(document, ['rows', 0, 'values', 1], 'valid'), 17)
        self.assertIs(source_entry_at(document, [], 'root'), document)
        self.assertIs(source_entry_at(document, ['0'], 'boolean leaf'), False)

    def test_resolver_rejects_wrong_component_and_container_types(self):
        document = {'rows': [4, 7], '0': 8}
        paths = [['rows', False], ['rows', True], ['rows', 0.0], ['rows', -0.0],
                 ['rows', -1], ['rows', 2], ['rows', '0'], [0], ['missing'],
                 ['rows', 0, 'value'], ['rows', {}], ['rows', []], 'rows', ('rows', 0)]
        for path in paths:
            with self.subTest(path=path), self.assertRaisesRegex(ParityError, 'source selector'):
                source_entry_at(document, path, 'malformed')

    def test_JAX_reindexed_integer_aliases_fail_full_loading(self):
        with self.copied() as copied:
            path = copied / PREFIX / 'joins.json'
            original = path.read_bytes()
            # A changed serialization with the correct integer is a valid control.
            path.write_text(json.dumps(self.read(path), indent=1) + '\n')
            self.reindex(copied, PREFIX + 'index.json')
            self.assertEqual(load(copied)['dtype_policy']['source_clauses'], 18)
            for position, value in [(0, False), (0, 0.0), (0, -0.0), (1, True), (1, 1.0)]:
                document = json.loads(original)
                document['clauses'][position]['source_entry'] = ['rules', value]
                self.write(path, document)
                self.reindex(copied, PREFIX + 'index.json')
                with self.subTest(position=position, value=value), self.assertRaisesRegex(
                        ParityError, 'source selector'):
                    load(copied)

    def test_semantic_mapping_boolean_alias_fails_full_loading(self):
        with self.copied() as copied:
            path = copied / 'mappings.json'
            rows = self.read(path)
            row = next(row for row in rows if row.get('source_contract', {}).get('entry', [])[-1:] == [0]
                       and type(row['source_contract']['entry'][-1]) is int)
            row['source_contract']['entry'][-1] = False
            self.write(path, rows)
            with self.assertRaisesRegex(ParityError, 'source selector'):
                load(copied)

    def test_public_scope_reindexed_boolean_alias_fails_full_loading(self):
        with self.copied() as copied:
            path = copied / 'reference/public-scope/contracts.json'
            rows = self.read(path)
            row = next(row for row in rows if row['source_entry'] == ['contracts', 0])
            row['source_entry'][-1] = False
            self.write(path, rows)
            self.reindex(copied, 'reference/public-scope/index.json')
            with self.assertRaisesRegex(ParityError, 'source selector'):
                load(copied)

    def test_core_reindexed_boolean_alias_fails_full_loading(self):
        with self.copied() as copied:
            relative = 'core-tensor/contracts.json'
            path = copied / relative
            document = self.read(path)
            row = next(row for row in document['contracts']
                       if row['source_endpoint']['entry'] == ['endpoints', 0])
            row['source_endpoint']['entry'][-1] = False
            self.write(path, document)
            self.reindex(copied, 'core-tensor/index.json')
            # Keep every consuming mapping hash consistent with the changed file.
            mappings = self.read(copied / 'mappings.json')
            for mapping in mappings:
                contract = mapping.get('source_contract', {})
                if contract.get('path') == relative:
                    contract['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            self.write(copied / 'mappings.json', mappings)
            with self.assertRaisesRegex(ParityError, 'source selector'):
                load(copied)


if __name__ == '__main__':
    unittest.main()
