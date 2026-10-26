"""Real reindexed corruption guards for source-only NumPy dtype integration."""
import copy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from atlas_parity import load, report
from atlas_parity_dtype import prepare_dtype_policy
from atlas_parity_dtype_capture import PREFIX as JAX_PREFIX
from atlas_parity_numpy_dtype import prepare_numpy_dtype, validate_numpy_dtype
from atlas_parity_numpy_dtype_capture import PREFIX, PACKET_SHA, REVIEW_SHA, original_bytes, policy_from_table
from atlas_parity_numpy_dtype_relations import predicate, source_cells, validate_relations
from atlas_parity_schema import ParityError, read_json
from atlas_parity_tables import pack, unpack

ROOT = Path(__file__).resolve().parents[2] / 'docs/parity'


def write(path, value, indent=None):
    path.write_text(json.dumps(value, sort_keys=True, indent=indent, ensure_ascii=False) + '\n')


class NumpyDtypeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load(ROOT)
        cls.prepared = prepare_numpy_dtype(ROOT, PREFIX + 'index.json', cls.bundle['program'])
        _, cls.index, cls.original, cls.documents, _ = cls.prepared
        cls.policy = cls.original['policy-tables.json']
        cls.citations = cls.original['source-witnesses.json']['citations']

    def validate(self, root=ROOT, program=None, mappings=None, assigned=None):
        b = self.bundle
        program = b['program'] if program is None else program
        prepared = prepare_numpy_dtype(root, program['files']['numpy_native_dtype_policy'], program)
        return validate_numpy_dtype(prepared, program, b['capabilities'], b['references'],
                                    b['mappings'] if mappings is None else mappings,
                                    b['assigned'] if assigned is None else assigned)[0]

    @contextmanager
    def actual_tree(self, jax=False):
        with tempfile.TemporaryDirectory(prefix='atlas-numpy-dtype-reindex-') as directory:
            root = Path(directory)
            shutil.copytree(ROOT / PREFIX, root / PREFIX)
            (root / 'reference').mkdir()
            shutil.copyfile(ROOT / 'reference/numpy.json', root / 'reference/numpy.json')
            if jax:
                shutil.copytree(ROOT / JAX_PREFIX, root / JAX_PREFIX)
            yield root

    def reindex(self, root):
        path = root / PREFIX / 'index.json'
        index = read_json(path)
        for row in index['artifacts']:
            row['sha256'] = hashlib.sha256((root / row['path']).read_bytes()).hexdigest()
        write(path, index)

    def corrupt(self, relative, mutate, message='NumPy'):
        # These are physical files with recomputed index hashes, not mocked reads.
        with self.actual_tree() as root:
            path = root / PREFIX / relative
            value = read_json(path)
            mutate(value)
            write(path, value)
            self.reindex(root)
            with self.assertRaisesRegex(ParityError, message):
                self.validate(root)

    def test_report_conserves_denominator_mapping_stages_and_no_credit(self):
        result = report(self.bundle)
        self.assertEqual([result[k] for k in ('reference_declarations', 'mapped_declarations',
                         'partially_mapped_declarations', 'unmapped_declarations')], [38096, 2, 96, 37998])
        native = result['numpy_native_dtype_designs']
        self.assertEqual([native[k] for k in ('source_files', 'source_functions', 'source_spans',
                         'symbolic_safe_cells', 'illustrative_ABI_profiles', 'unrun_cases', 'open_gaps')],
                         [78, 129, 131, 576, 2, 47, 8])
        self.assertEqual((native['existing_mapped_API_associations'], native['explicitly_unmapped_API_associations']), (3, 5))
        self.assertEqual(native['source_packet_sha256'], PACKET_SHA)
        self.assertEqual(native['source_review_sha256'], REVIEW_SHA)
        self.assertFalse(native['public_denominator_changed'])
        self.assertEqual(native['framework_execution_credit'], 0)

    def test_all_selected_original_roles_roundtrip_exactly(self):
        manifest = read_json(ROOT / PREFIX / 'captured/manifest.json')
        capture = read_json(ROOT / PREFIX / 'capture.json')
        self.assertEqual(len(capture['captured']), 16)
        for row in capture['captured']:
            name = row['original_path']
            if row['storage'] == 'policy-with-column-cells':
                value = policy_from_table(self.documents[PREFIX + 'table-policy.json'], self.documents[PREFIX + 'safe-pairs.json'])
                data = original_bytes(value)
            elif row['storage'] == 'compact-json':
                data = original_bytes(self.original[name])
            else:
                data = (ROOT / row['paths'][0]).read_bytes()
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256(data).hexdigest(), manifest['files'][name]['sha256'])
                self.assertEqual(len(data), manifest['files'][name]['bytes'])

    def test_source_expansion_reconstructs_all_cells_and_two_profiles(self):
        cells = source_cells(self.citations[self.policy['safe_policy']['source']]['text'])
        self.assertEqual(len(cells), 576)
        self.assertEqual({tuple(c['ordinal']) for c in cells}, {(i, j) for i in range(24) for j in range(24)})
        self.assertEqual(validate_relations(self.policy, self.citations), 576)
        self.assertEqual(cells[0]['predicate'], 1)
        self.assertEqual(cells[21]['predicate'], 0)

    def test_symbolic_expression_and_AST_cannot_both_lie_about_source(self):
        policy = copy.deepcopy(self.policy)
        policy['safe_policy']['cells'][0].update(c_expression='0', predicate=0)
        with self.assertRaisesRegex(ParityError, 'independently expanded pinned source'):
            validate_relations(policy, self.citations)

    def test_symbolic_AST_cannot_disagree_with_expression(self):
        policy = copy.deepcopy(self.policy)
        policy['safe_policy']['cells'][0]['predicate'] = 0
        with self.assertRaises(ParityError):
            validate_relations(policy, self.citations)

    def test_symbolic_relations_cannot_drop_or_duplicate_a_cell(self):
        for change in (lambda d: d['safe_policy']['cells'].pop(),
                       lambda d: d['safe_policy']['cells'].__setitem__(-1, d['safe_policy']['cells'][0])):
            document = copy.deepcopy(self.policy)
            change(document)
            with self.assertRaisesRegex(ParityError, 'conservation'):
                validate_relations(document, self.citations)

    def test_illustrative_profiles_cannot_claim_observation_or_change_values(self):
        for change in (lambda d: d.update(build_generated_abi_values_observed=True),
                       lambda d: d['illustrative_abi_profiles'][0]['safe_table'][0].__setitem__(0, False),
                       lambda d: d['illustrative_abi_profiles'][0]['promotion_initializer_table'][0].__setitem__(0, 1)):
            document = copy.deepcopy(self.policy)
            change(document)
            with self.assertRaises(ParityError):
                validate_relations(document, self.citations)

    def test_symbolic_predicate_types_do_not_alias_boolean_and_integer(self):
        for value in (True, 1.0):
            document = copy.deepcopy(self.policy)
            document['safe_policy']['cells'][0]['predicate'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ParityError, 'independently expanded'):
                validate_relations(document, self.citations)

    def test_profile_matrix_types_do_not_alias_boolean_and_integer(self):
        for field, replacement in [('safe_table', 1), ('promotion_initializer_table', False)]:
            document = copy.deepcopy(self.policy)
            document['illustrative_abi_profiles'][0][field][0][0] = replacement
            with self.subTest(field=field), self.assertRaisesRegex(ParityError, 'ABI source relation'):
                validate_relations(document, self.citations)

    def test_closed_symbolic_grammar_rejects_calls_and_boolean_literals(self):
        for expression in ('__import__("numpy")', 'True', 'x + 1', '1 != 0', 'NPY_SIZEOF_LONG[0]'):
            with self.subTest(expression=expression), self.assertRaises(ParityError):
                predicate(expression)

    def test_reindexed_wrong_table_cell_rejects_lossless_capture(self):
        def change(table):
            rows = unpack(table)
            rows[0]['predicate'] = 0
            table.clear()
            table.update(pack(rows, {'role': 'symbolic_source_relation_not_descriptor_or_runtime_legality', 'source_cells': 576}))
        self.corrupt('safe-pairs.json', change, 'lossless accepted capture')

    def test_reindexed_source_binding_hash_and_signature_reject(self):
        for change in (lambda d: d['functions'][0].update(body_sha256='0' * 64),
                       lambda d: d['functions'][0].update(signature_source='different()')):
            self.corrupt('source-bindings.json', change, 'function binding')

    def test_reindexed_source_binding_cannot_move_to_another_existing_function(self):
        self.corrupt('source-bindings.json', lambda d: d['functions'][0].update(source_citation=d['functions'][1]['source_citation']), 'function binding')

    def test_reindexed_registered_resolver_phases_cannot_reorder(self):
        self.corrupt('source-bindings.json', lambda d: d['registered_resolver_phases'][1]['ordered_source_markers'].reverse(), 'registered phase')

    def test_reindexed_temporal_source_question_stays_unresolved(self):
        self.corrupt('source-bindings.json', lambda d: d['temporal_quotient_disposition'].update(exact_binary_comparison='verified'), 'temporal role')

    def test_temporal_integer_quotient_is_not_duration_equality(self):
        question = self.documents[PREFIX + 'source-bindings.json']['temporal_quotient_disposition']
        self.assertEqual(2001 // 2, 1000)
        self.assertNotEqual(2001, 2 * 1000)
        self.assertEqual(question['source_integer_quotient'], 1000)
        self.assertEqual(question['exact_binary_comparison'], 'unrun')
        self.assertFalse(question['reference_bug_waiver_or_exclusion'])

    def test_reindexed_unknown_binding_metadata_rejects(self):
        self.corrupt('source-bindings.json', lambda d: d['functions'][0].update(runtime_verified=True), 'unexpected')

    def test_reindexed_false_as_integer_does_not_satisfy_source_roles(self):
        self.corrupt('source-bindings.json', lambda d: d['registered_resolver_phases'][0].update(runtime_executed=0), 'expected bool')

    def test_reindexed_exact_count_requires_integer_not_bool_or_float(self):
        for value in (True, 78.0):
            self.corrupt('index.json', lambda d, v=value: d['counts'].update(source_files=v), 'expected int')

    def test_reindexed_top_status_cannot_add_credit_or_unknown_keys(self):
        for change in (lambda d: d['status'].update(reference_runtime_cases=1),
                       lambda d: d['status'].update(released=True),
                       lambda d: d['status'].update(external_verified=0),
                       lambda d: d['status'].update(runtime_qualified=True)):
            self.corrupt('index.json', change, 'cannot assert complete API')

    def test_reindexed_actual_mapping_owner_cannot_be_policy_fallback(self):
        self.corrupt('joins.json', lambda d: d['endpoints'][0]['canonical_API_mapping'].update(owner='atlas'), 'actual API mapping association')

    def test_reindexed_unmapped_supporting_ID_cannot_invent_mapping(self):
        def change(d):
            row = next(r for r in d['endpoints'] if r['canonical_API_mapping']['state'] == 'unmapped')
            row['canonical_API_mapping'] = dict(state='mapped', reference_id=row['reference_id'], mapping_id='invented', owner='eunomia', capability='NUM-PROMOTE')
        self.corrupt('joins.json', change, 'actual API mapping association')

    def test_reindexed_supplier_prerequisites_cannot_be_replaced(self):
        self.corrupt('joins.json', lambda d: d['endpoints'][0]['policy_supplier'].update(prerequisites=[]), 'supplier')

    def test_reindexed_case_relation_cannot_select_another_valid_case(self):
        self.corrupt('joins.json', lambda d: d['families'][0]['case_ids'].__setitem__(0, 'numpy-dtype:single-huge-int-discovery'), 'exact family')

    def test_unregistered_source_prerequisites_remain_explicit(self):
        rows = self.documents[PREFIX + 'joins.json']['families']
        unresolved = [r for r in rows if r['unresolved_source_prerequisites']]
        self.assertEqual({r['id'] for r in unresolved}, {'native:descriptor-coercion', 'native:new-and-custom-dtypes'})
        self.assertTrue(all(r['unresolved_source_prerequisites'] == ['INTEROP-NATIVE'] for r in unresolved))
        self.assertTrue(all(r['actual_implementation_owner'] is None for r in rows))
        self.assertTrue(all(r['planned_owner'] == 'leto' for r in unresolved))

    def test_reindexed_unregistered_prerequisite_cannot_disappear(self):
        self.corrupt('joins.json', lambda d: next(r for r in d['families'] if r['unresolved_source_prerequisites']).update(unresolved_source_prerequisites=[]), 'exact family')

    def test_reindexed_source_family_cannot_approve_implementation_owner(self):
        self.corrupt('joins.json', lambda d: d['families'][0].update(actual_implementation_owner='leto'), 'expected NoneType')

    def test_reindexed_case_execution_boolean_is_strict(self):
        self.corrupt('joins.json', lambda d: d['cases'][0].update(runtime_executed=0), 'expected bool')

    def test_reindexed_selected_source_receipt_tampering_rejects(self):
        self.corrupt('captured/source-receipts.json', lambda d: next(iter(d['source_files'].values())).update(git_blob='0' * 40), 'lossless accepted capture')

    def test_reindexed_review_and_manifest_pins_remain_exact(self):
        self.corrupt('independent-review.json', lambda d: d.update(outcome='whole_API_approved'), 'accepted source manifest/review pin')
        self.corrupt('captured/manifest.json', lambda d: d.update(scope='whole_API_approved'), 'accepted source manifest/review pin')

    def test_reindexed_capture_role_substitution_rejects(self):
        self.corrupt('capture.json', lambda d: d['captured'][0].update(original_path='foreign-role.json'), 'role duplicated/unknown')

    def test_reindexed_unknown_index_or_role_fields_reject(self):
        self.corrupt('index.json', lambda d: d.update(complete_API=True), 'unexpected')
        self.corrupt('joins.json', lambda d: d['endpoints'][0].update(api_owner='atlas'), 'unexpected')

    def test_source_correction_preserves_old_mapping_and_discovery_distinction(self):
        correction = self.documents[PREFIX + 'correction-disposition.json']
        self.assertEqual(correction['raw_mapping_id'], 'core-numpy-numpy-result-type')
        self.assertIn('Single-input discovered descriptor', correction['corrected_scope'])
        self.assertIn('multi-input exact Python scalar', correction['corrected_scope'])
        self.assertFalse(correction['history_mutated'])
        self.assertFalse(correction['mapping_stage_changed'])

    def test_reindexed_correction_cannot_erase_history_or_change_mapping_stage(self):
        self.corrupt('correction-disposition.json', lambda d: d.update(history_mutated=True), 'preserve history')
        self.corrupt('correction-disposition.json', lambda d: d.update(mapping_stage_changed=True), 'preserve history')

    def test_valid_reformatted_canonical_artifacts_pass_after_real_reindex(self):
        with self.actual_tree() as root:
            for name in ('joins.json', 'source-bindings.json', 'table-policy.json', 'safe-pairs.json', 'capture.json'):
                path = root / PREFIX / name
                write(path, read_json(path), indent=3)
            self.reindex(root)
            result = self.validate(root)
            self.assertEqual(result['symbolic_safe_cells'], 576)
            self.assertEqual(result['existing_mapped_API_associations'], 3)

    def test_JAX_introduction_and_all_historical_bytes_stay_consumed_by_current_program(self):
        b = self.bundle
        self.assertEqual(read_json(ROOT / PREFIX / 'index.json')['parent_program_version'], '2026-10-26.9')
        path = ROOT / JAX_PREFIX / 'index.json'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), '9ba4444ce793edf0d90d106d95b6140e6216f9a1be8adcfe1987a792952e3774')
        self.assertEqual(read_json(path)['parent_program_version'], '2026-10-26.8')
        prepared = prepare_dtype_policy(ROOT, b['program']['files']['dtype_policy'], b['program'])
        self.assertEqual(prepared[1]['source_pairs'], 9256)

    def test_JAX_mutated_introduction_is_rejected_in_real_tree(self):
        with self.actual_tree(jax=True) as root:
            path = root / JAX_PREFIX / 'index.json'
            document = read_json(path)
            document['parent_program_version'] = '2026-10-26.9'
            write(path, document)
            with self.assertRaisesRegex(ParityError, 'version/pin drift'):
                prepare_dtype_policy(root, JAX_PREFIX + 'index.json', self.bundle['program'])

    def test_program_source_specific_files_roles_cannot_be_swapped(self):
        program = copy.deepcopy(self.bundle['program'])
        program['files']['dtype_policy'], program['files']['numpy_native_dtype_policy'] = (
            program['files']['numpy_native_dtype_policy'], program['files']['dtype_policy'])
        with self.assertRaisesRegex(ParityError, 'role association'):
            prepare_numpy_dtype(ROOT, program['files']['numpy_native_dtype_policy'], program)
        with self.assertRaisesRegex(ParityError, 'role association'):
            prepare_dtype_policy(ROOT, program['files']['dtype_policy'], program)


if __name__ == '__main__':
    unittest.main()
