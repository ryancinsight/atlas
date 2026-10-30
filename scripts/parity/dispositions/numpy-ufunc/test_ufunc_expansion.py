"""Source witnesses and adverse mutations of the complete generated bundle."""
import ast
import copy
import unittest
from validate_expansion import ROOT, ValidationError, bundle, validate

class ExpansionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.original = bundle()

    def rejects(self, mutate, expected):
        data = copy.deepcopy(self.original)
        mutate(data)
        with self.assertRaisesRegex(ValidationError, expected):
            validate(data, source_hashes=False)

    def test_complete_bounded_bundle_and_source_hashes(self):
        result = validate(self.original)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['framework_imports_or_builds'], 0)

    def test_dropping_private_generator_object_is_rejected(self):
        self.rejects(lambda d: d['ufunc-objects.json']['objects'].remove(next((r for r in d['ufunc-objects.json']['objects'] if r['generated_name'] == '_arg'))), 'object identities')

    def test_dropping_public_underscored_c_user_method_is_rejected(self):
        self.rejects(lambda d: d['ufunc-members.json']['members'].remove(next((r for r in d['ufunc-members.json']['members'] if r['member'] == '_get_strided_loop'))), 'member identities')

    def test_omitted_native_alias_is_rejected(self):
        self.rejects(lambda d: d['ufunc-bindings.json']['explicit_native_alias_relations'].pop(), 'native alias omission')

    def test_dropped_original_occurrence_is_rejected(self):
        self.rejects(lambda d: d['ufunc-objects.json']['original_input_dispositions']['original_rows_retained'].pop(), 'original133')

    def test_alias_retargeting_is_rejected(self):

        def change(data):
            row = next((r for r in data['ufunc-bindings.json']['bindings'] if r['symbol'] == 'numpy.bitwise_not'))
            row['object_id'] = 'numpy@2.5.4:generated:negative'
        self.rejects(change, 'alias relation')

    def test_one_rejected_workflow_must_remain_as_a_candidate(self):
        self.rejects(lambda d: d['ufunc-expansions.json']['object_member_expansions'].remove(next((r for r in d['ufunc-expansions.json']['object_member_expansions'] if r['generated_name'] == 'matmul' and r['member'] == 'reduce'))), 'cross-product omission')

    def test_alias_spelling_workflow_cannot_be_collapsed(self):
        self.rejects(lambda d: d['ufunc-expansions.json']['public_spelling_member_expansions'].remove(next((r for r in d['ufunc-expansions.json']['public_spelling_member_expansions'] if r['symbol'] == 'numpy.abs.outer'))), 'public spelling expansion')

    def test_multioutput_outer_is_not_reduction_guard(self):

        def change(data):
            row = next((r for r in data['ufunc-expansions.json']['object_member_expansions'] if r['generated_name'] == 'divmod' and r['member'] == 'outer'))
            row['descriptor_gate'] = {'status': 'descriptor-rejected', 'first_error': 'ValueError'}
        self.rejects(change, 'multi-output outer incorrectly rejected')

    def test_old_official_documentation_cannot_be_relabelled(self):

        def change(data):
            row = next((r for r in data['documentation-dispositions.json']['public_bindings'] if r['official_index_supplement']))
            row['official_index_supplement']['documentation_version'] = '2.5.4'
        self.rejects(change, 'older docs relabeled')

    def test_source_candidate_cannot_be_promoted_to_runtime_evidence(self):
        self.rejects(lambda d: d['ufunc-objects.json'].update(implementation_or_runtime_evidence=True), 'promoted to verification')

    def test_full_scope_overclaim_is_rejected(self):
        self.rejects(lambda d: d['bounded-completeness.json'].update(full_numpy_surface_complete=True), 'completion overclaim')

    def test_empty_docs_are_preserved_as_empty(self):

        def change(data):
            row = next((r for r in data['ufunc-objects.json']['objects'] if r['generated_name'] == '_strip_chars'))
            row['generated_documentation']['payload_status'] = 'nonempty-source-doc-payload'
        self.rejects(change, 'empty source docs hidden')

    def test_native_guard_source_witnesses(self):
        source = (ROOT / 'sources/numpy/_core/src/umath/ufunc_object.c').read_text(encoding='utf-8')
        outer = source.split('ufunc_outer(PyUFuncObject', 1)[1].split('static PyObject *', 1)[0]
        self.assertIn('ufunc->core_enabled', outer)
        self.assertIn('ufunc->nin != 2', outer)
        self.assertNotIn('ufunc->nout', outer)
        self.assertLess(outer.index('ufunc->core_enabled'), outer.index('ufunc->nin != 2'))
        self.assertLess(outer.index('ufunc->nin != 2'), outer.index('len_args != 2'))
        reduce = source.split('PyUFunc_GenericReduction(', 1)[1].split('/* Interpret parameters */', 1)[0]
        for fragment in ['ufunc->core_enabled', 'ufunc->nin != 2', 'ufunc->nout != 1', 'PyExc_RuntimeError', 'PyExc_ValueError']:
            self.assertIn(fragment, reduce)
        self.assertLess(reduce.index('ufunc->core_enabled'), reduce.index('ufunc->nin != 2'))
        self.assertLess(reduce.index('ufunc->nin != 2'), reduce.index('ufunc->nout != 1'))
        resolve = source.split('py_resolve_dtypes_generic(PyUFuncObject', 1)[1].split('/*', 1)[0]
        self.assertIn('reduction && (ufunc->nin != 2 || ufunc->nout != 1)', resolve)
        self.assertNotIn('core_enabled', resolve)

    def test_documented_public_underscored_source_witness(self):
        source = (ROOT / 'sources/numpy/_core/src/umath/ufunc_object.c').read_text(encoding='utf-8')
        table = source.split('ufunc_methods[] = {', 1)[1].split('\n};', 1)[0]
        comment = table.split('"resolve_dtypes"', 1)[1].split('{"_resolve_dtypes_and_context"', 1)[0]
        self.assertRegex(comment, '(?s)public API.*underscored.*C-user specific.*API stability')

    def test_real_aliases_not_just_mathematical_resemblance(self):
        objects = {r['generated_name']: r for r in self.original['ufunc-objects.json']['objects']}
        self.assertNotEqual(objects['radians']['object_id'], objects['deg2rad']['object_id'])
        aliases = self.original['ufunc-bindings.json']['explicit_native_alias_relations']
        self.assertIn(('mod', 'remainder'), {(r['alias'], r['target_name']) for r in aliases})

    def test_extractor_does_not_import_or_execute_framework_code(self):
        for path in ROOT.glob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse(any((alias.name.split('.', 1)[0] in {'numpy', 'jax', 'torch', 'tensorflow'} for alias in node.names)), path.name)
                elif isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or '').split('.', 1)[0], {'numpy', 'jax', 'torch', 'tensorflow'}, path.name)
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {'eval', 'exec', 'compile', '__import__'}, path.name)
if __name__ == '__main__':
    unittest.main(verbosity=2)
