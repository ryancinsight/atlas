"""Check static research artifacts; no NumPy execution/implementation evidence."""
import ast
import hashlib
import json
import math
from pathlib import Path
import re
import unittest
ROOT = Path(__file__).resolve().parent
REV = 'a3d0ef1df045b858e68115001fdabc930bb3b68c'

class ResearchArtifactTests(unittest.TestCase):

    def load(self, name):
        return json.loads((ROOT / name).read_text(encoding='utf-8'))

    def test_every_original_gap_has_one_disposition_and_immutable_source(self):
        before = self.load('baseline-inventory.json')
        after = self.load('gap-dispositions.json')
        expected = {item['path'] + '#L' + str(item['line']) for item in before['extraction_gaps']}
        actual = [item['gap_id'] for item in after['dispositions']]
        self.assertEqual(len(actual), 65)
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), len(set(actual)))
        self.assertTrue(all((REV in item['source'] for item in after['dispositions'])))
        self.assertFalse(after['full_public_inventory_complete'])
        self.assertTrue(all((item['capabilities_verified'] == 0 for item in after['dispositions'])))

    def test_scoped_init_exclusions_do_not_become_inherited_member_waivers(self):
        data = self.load('gap-dispositions.json')
        rows = [item for item in data['dispositions'] if item['disposition'] == 'resolved-empty-explicit-selection']
        self.assertEqual(len(rows), 44)
        self.assertTrue(all((item['scoped_options']['members'] == item['scoped_options']['exclude-members'] == '__init__' for item in rows)))
        supplement = self.load('static-candidates.json')
        self.assertTrue(any((item['symbol'] == 'numpy.generic.astype' for item in supplement['inherited_array_scalar_candidates'])))
        self.assertTrue(any((item['symbol'] == 'numpy.ndarray.__array_finalize__' for item in supplement['inherited_array_scalar_candidates'])))

    def test_exported_functions_are_defined_and_generated_private_candidates_retained(self):
        data = self.load('static-candidates.json')
        records = data['module_exports']
        self.assertEqual(len(records), 23)
        self.assertEqual({r['symbol'] for r in records if r['symbol'].startswith('numpy.f2py.')}, {'numpy.f2py.run_main', 'numpy.f2py.get_include'})
        self.assertTrue(all((r.get('signature') for r in records)))
        generated = data['generated_ufunc_candidates']
        self.assertEqual(len(generated), 133)
        private = next((r for r in generated if r['symbol'].endswith('._ones_like')))
        self.assertEqual(private['declared_public_bindings'], [])
        alpha = next((r for r in generated if r['symbol'].endswith('.isalpha')))
        self.assertTrue(any((r['symbol'] == 'numpy.strings.isalpha' for r in alpha['declared_public_bindings'])))
        self.assertFalse(any((r['symbol'] == 'numpy.isalpha' for r in alpha['declared_public_bindings'])))

    def test_all_cached_numpy_sources_match_declared_git_blob_and_content_hashes(self):
        records = self.load('sources.json')
        self.assertGreaterEqual(len(records), 435)
        for record in records:
            b = (ROOT / 'sources' / record['path']).read_bytes()
            self.assertEqual(hashlib.sha256(b).hexdigest(), record['sha256'])
            self.assertEqual(hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\x00' + b).hexdigest(), record['git_blob_sha'])

    def test_constructor_signature_variations_and_unverified_status_remain_visible(self):
        data = self.load('constructor-contracts.json')
        self.assertEqual(set(data['contracts']), {'zeros', 'ones', 'full', 'arange', 'linspace', 'logspace', 'geomspace'})
        self.assertIn('device=None', data['contracts']['linspace']['runtime_python_signature'])
        self.assertNotIn('device', data['contracts']['logspace']['runtime_python_signature'])
        self.assertNotIn('device', data['contracts']['geomspace']['runtime_python_signature'])
        self.assertIn('signature_discrepancy', data['contracts']['arange'])
        self.assertFalse(data['full_runtime_combination_matrix_verified'])
        self.assertTrue(all((not row['gradient']['native_autodiff'] for row in data['contracts'].values())))

    def test_native_metadata_shape_algebra_including_empty_axis_identity(self):
        data = self.load('metadata-contracts.json')
        self.assertEqual(set(data['operations']), {'ndim', 'shape', 'size'})
        for case in data['analytical_cases']:
            shape = case['actual_shape']
            self.assertEqual(case['expected']['ndim'], len(shape))
            self.assertEqual(case['expected']['size_axisNone'], math.prod(shape))
            self.assertEqual(case['expected']['size_axisEmptyTuple'], 1)
        selected_zero_free = next((c for c in data['negative_and_axis_cases'] if c.get('shape') == [2, 0, 5] and c.get('normalized') == [0, 2]))
        self.assertEqual(selected_zero_free['expected'], 10)
        self.assertFalse(data['verification_status']['full_parity_claim'])

    def test_old_official_inventory_is_not_relabeled_frozen_patch(self):
        inventory = self.load('mirror-inventory-2.5.0.json')
        self.assertEqual(inventory['reference_documentation_version'], '2.5.0')
        self.assertFalse(inventory['frozen2_5_4_equivalence_verified'])
        comparison = self.load('source-comparison-2.5.0-to-2.5.4.json')
        self.assertFalse(comparison['entire_rendered_symbol_inventory_equivalence_proven'])
        self.assertGreater(comparison['groups']['non_test_type_stubs']['counts']['changed'], 0)

    def test_axis_index_failure_falls_through_and_tuple_finishes_before_duplicates(self):
        data = self.load('metadata-checker-witnesses.json')
        index = data['axis_index_failure_witness']
        self.assertEqual(index['caught_exception_type'], 'TypeError')
        self.assertTrue(index['handler_is_pass'])
        self.assertEqual(index['stdlib_witness_normalized'], [0])
        self.assertEqual(index['stdlib_witness_events'], ['index', 'iter'])
        order = data['axis_materialization_order_witness']
        self.assertLess(order['tuple_statement_index'], order['duplicate_statement_index'])
        self.assertTrue(order['size_shape_then_normalize_then_product'])
        cases = self.load('metadata-contracts.json')['negative_and_axis_cases']
        self.assertTrue(any((case.get('axis') == [0, 0, 2] and case['error'].startswith('AxisError') for case in cases)))

    def test_special_lookup_boundary_and_exact_invocation_are_phase_scoped(self):
        data = self.load('metadata-checker-witnesses.json')
        lookup = data['special_lookup_witness']
        self.assertEqual(lookup['git_blob_sha'], '324a92c5ef0c454a5255d3293f587f23e11b8406')
        self.assertTrue(lookup['target_is_type_object'] and lookup['instance_only_attribute_ignored'])
        self.assertTrue(lookup['present_None_remains_present'] and lookup['no_callability_precheck_in_collection'])
        phase = data['phase_error_witness']
        self.assertTrue(phase['lookup_failure_clear_has_no_exception_kind_filter'])
        self.assertTrue(phase['invocation_does_not_clear_errors'])
        self.assertEqual(phase['exact_invocation_positional_arguments'], ['argument', 'public_api', 'types', 'args', 'kwargs'])
        contract = self.load('metadata-contracts.json')
        self.assertEqual(contract['policy_decisions'][0]['provider_design_status'], 'pending; no implementation or runtime evidence')

    def test_native_getter_proof_does_not_force_detach_or_cover_overridden_subtypes(self):
        data = self.load('metadata-contracts.json')
        for operation in data['operations'].values():
            self.assertIn('RELEVANT', operation['native_dtype_layout_value_equivalence']['domain'])
            self.assertIn('graph-bearing', operation['gradient']['delegated_identity'])
            self.assertIn('not apply', operation['gradient']['native_metadata'])
        witnesses = self.load('metadata-checker-witnesses.json')
        self.assertTrue(all((item['no_forced_conversion_or_detach_in_branch'] for item in witnesses['delegated_identity_witness'].values())))
        self.assertFalse(witnesses['runtime_differential_verified'])
        self.assertFalse(witnesses['ad_preservation_verified'])

    def test_contract_source_citations_have_real_paths_and_line_bounds(self):

        def visit(value):
            if isinstance(value, dict):
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)
            elif isinstance(value, str):
                match = re.fullmatch('https://github.com/numpy/numpy/blob/' + REV + '/(.+)#L(\\d+)', value)
                if match:
                    source = ROOT / 'sources' / match[1]
                    self.assertTrue(source.is_file(), str(source))
                    self.assertLessEqual(int(match[2]), len(source.read_text(encoding='utf-8').splitlines()))
        visit(self.load('constructor-contracts.json'))
        visit(self.load('metadata-contracts.json'))
        visit(self.load('metadata-checker-witnesses.json'))
if __name__ == '__main__':
    unittest.main()
