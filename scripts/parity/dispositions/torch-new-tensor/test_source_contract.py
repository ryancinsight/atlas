"""Source-contract acceptance assertions; no PyTorch runtime is imported."""
import os
from pathlib import Path
import copy, hashlib, json, unittest
import source_contract as contract

class NewTensorSourceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((contract.ROOT / 'sources.json').read_text(encoding='utf-8'))
        cls.sources = {r['path']: (contract.P / r['path']).read_text(encoding='utf-8') for r in cls.rows}

    def test_frozen_source_blob_and_content_integrity(self):
        self.assertEqual(len(self.rows), 26)
        for row in self.rows:
            raw = (contract.P / row['path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
            self.assertEqual(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\x00' + raw).hexdigest(), row['blob_sha'])

    def test_effective_builtin_signature_and_copy_scope(self):
        result = contract.analyze(self.sources)
        self.assertEqual(result['accepted_parameter_names'], ['data', 'dtype', 'device', 'requires_grad'])
        self.assertFalse(result['universal_copy_proven'])
        self.assertFalse(result['universal_strided_proven'])

    def test_unreviewed_layout_argument_change_rejected(self):
        changed = dict(self.sources)
        name = 'torch/csrc/utils/tensor_new.cpp'
        changed[name] = changed[name].replace('new_tensor(PyObject* data, *, ScalarType dtype=None, Device? device=None, bool requires_grad=False)', 'new_tensor(PyObject* data, *, ScalarType dtype=None, Device? device=None, bool requires_grad=False, Layout layout=None)')
        with self.assertRaises(AssertionError):
            contract.analyze(changed)

    def test_torch_function_routing_loss_rejected(self):
        changed = dict(self.sources)
        name = 'tools/autograd/templates/python_variable_methods.cpp'
        fragment = contract.body(changed[name], 'static PyObject * THPVariable_new_tensor(')
        changed[name] = changed[name].replace(fragment, fragment.replace('has_torch_function(self)', 'false'))
        with self.assertRaises(AssertionError):
            contract.analyze(changed)

    def test_tensor_copy_detach_loss_rejected(self):
        changed = dict(self.sources)
        name = 'torch/csrc/utils/tensor_new.cpp'
        fragment = contract.body(changed[name], 'Tensor new_from_data_copy(')
        changed[name] = changed[name].replace(fragment, fragment.replace('/*copy_variables=*/true', '/*copy_variables=*/false'))
        with self.assertRaises(AssertionError):
            contract.analyze(changed)

    def test_storage_path_change_requires_new_contract(self):
        changed = dict(self.sources)
        name = 'torch/csrc/utils/tensor_new.cpp'
        fragment = contract.body(changed[name], 'if (isStorage(data))')
        changed[name] = changed[name].replace(fragment, fragment.replace('tensor.set_(storage);', 'tensor.set_(storage); tensor = tensor.clone();'))
        with self.assertRaises(AssertionError):
            contract.analyze(changed)

    def test_global_strided_claim_loses_source_support(self):
        changed = dict(self.sources)
        name = 'aten/src/ATen/native/TensorConversions.cpp'
        fragment = contract.body(changed[name], 'Tensor _to_copy(')
        changed[name] = changed[name].replace(fragment, fragment.replace('options = self.options().merge_in(options)', 'options = options.layout(kStrided)'))
        with self.assertRaises(AssertionError):
            contract.analyze(changed)

    def test_partial_status_and_exact_outstanding_questions_preserved(self):
        record = json.loads((contract.ROOT / 'contract.json').read_text(encoding='utf-8'))
        self.assertFalse(record['public_api_mapping_complete'])
        self.assertEqual(record['runtime_verification'], 'not_run')
        self.assertEqual(len(record['contradictions']), 3)
        self.assertEqual(len(record['input_protocols']), 7)
        self.assertEqual(len(record['source_test_definitions']), 3)
        self.assertTrue(all((r['execution'] == 'not_run' for r in record['source_test_definitions'])))
        self.assertGreaterEqual(len(record['remaining_whole_api_questions']), 6)

    def test_prior_replay_artifacts_unchanged(self):
        root = Path(os.environ['ATLAS_REFERENCE_BASE_CLOSURE'])
        expected = {'source-supplement.json': '0f7769acf9159e9e41c421ee97cd6a43cf696978fcf35dc6b6d81f728fc96878', 'constructor-contracts.json': '779576b6d6ed3a3c59c62d22fc0b0f3f7512f8883bfbc7e072866841220d2b59'}
        for name, value in expected.items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), value)
if __name__ == '__main__':
    unittest.main()
