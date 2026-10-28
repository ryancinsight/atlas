"""Source-selection regressions; no JAX/Sphinx import or framework execution."""
import os
import ast, json, unittest, inspect
from types import SimpleNamespace
from pathlib import Path
from selection import ROOT, JAX_CACHE, OLD, helpers, metadata_fixture_classes, verify_inputs, function, fingerprint

class SelectionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'selection-dispositions.json').read_text(encoding='utf-8'))
        cls.rows = {r['symbol']: r for r in cls.data['rows']}
        cls.versions = cls.data['configured_tooling']['compatible_source_releases_verified']

    def test_every_original_candidate_remains_in_scope(self):
        old = json.loads(OLD.read_text(encoding='utf-8'))
        self.assertEqual(set(self.rows), {r['symbol'] for r in old['records']})
        self.assertEqual(len(self.rows), 22)
        self.assertTrue(all((r['public_scope_action'].startswith('retain original candidate') for r in self.rows.values())))
        self.assertTrue(all((not r['rendered_output_verified'] for r in self.rows.values())))
        self.assertEqual(self.data['semantic_api_closures'], 0)

    def test_four_undocumented_members_are_not_falsely_promoted(self):
        names = {s for s, r in self.rows.items() if r['selection_state'] == 'selector_filtered_undocumented'}
        self.assertEqual(names, {'jax.stages.Traced.jaxpr', 'jax.stages.Traced.out_info', 'jax.stages.Lowered.out_tree', 'jax.stages.Compiled.out_tree'})
        for s in names:
            e = self.rows[s]['attribute_source_evidence']
            self.assertFalse(e['preceding_doc_comment'])
            self.assertFalse(e['inline_doc_comment'])

    def test_explicit_slot_and_property_request_does_not_supply_doc(self):
        classes = metadata_fixture_classes()
        for version in self.versions:
            h = helpers(version)
            self.assertIsNone(h['getdoc'](classes['Traced'].jaxpr, getattr, True, classes['Traced'], 'jaxpr'))
            self.assertIsNone(h['getdoc'](classes['Traced'].out_info, getattr, True, classes['Traced'], 'out_info'))
            for name in ('Lowered', 'Compiled'):
                self.assertIn('out_tree', classes[name].__slots__)
                raw = h['getdoc'](classes[name].out_tree, getattr, True, classes[name], 'out_tree')
                self.assertIsNone(raw)

    def test_generic_metaclass_doc_is_not_mistaken_for_own_execution_doc(self):
        c = metadata_fixture_classes()['Compiled']
        self.assertIsNone(c.__call__.__doc__)
        for version in self.versions:
            h = helpers(version)
            doc = h['getdoc'](c.__call__, getattr, True, c, '__call__')
            self.assertEqual(doc, type.__call__.__doc__)
            self.assertIsNone(h['getdoc'](c.__call__, getattr, False, c, '__call__'))
        r = self.rows['jax.stages.Compiled.__call__']
        self.assertEqual(r['selection_state'], 'selector_eligible_generic_metaclass_doc_fallback')
        self.assertTrue(r['questions'])

    def test_explicit_inherited_property_keeps_its_own_doc(self):
        classes = metadata_fixture_classes()
        for version in self.versions:
            h = helpers(version)
            for name in ('Lowered', 'Compiled'):
                self.assertNotIn('in_tree', classes[name].__dict__)
                self.assertEqual(h['getdoc'](classes[name].in_tree, getattr, True, classes[name], 'in_tree'), classes['Stage'].in_tree.__doc__)

    def test_filter_rule_rejects_missing_docs_even_for_requested_member(self):
        for version in self.versions:
            node = function(ROOT / 'tooling' / version / 'sphinx/ext/autodoc/__init__.py', 'filter_members', 'Documenter')
            rules = [n.value for n in ast.walk(node) if isinstance(n, ast.Assign) and any((isinstance(t, ast.Name) and t.id == 'keep' for t in n.targets))]
            self.assertTrue(any((isinstance(v, ast.BoolOp) and isinstance(v.op, ast.Or) and (ast.unparse(v) == 'has_doc or self.options.undoc_members') for v in rules)))

    def test_all_allowed_release_source_rules_are_accounted_for(self):
        self.assertEqual(len(self.versions), 14)
        for name in ('Documenter.filter_members', 'getdoc', 'get_class_members'):
            groups = self.data['tooling_method_ast_fingerprints'][name]
            self.assertEqual(len(groups), 1)
            self.assertEqual(set(next(iter(groups.values()))), set(self.versions))

    def test_toolchain_is_a_range_not_a_claimed_lock(self):
        cfg = self.data['configured_tooling']
        self.assertEqual(cfg['sphinx'], '>=7.3.2,<8.0')
        self.assertEqual(cfg['python'], '3.12 minor only')
        self.assertFalse(cfg['rendered_output_verified'])

    def test_stock_napoleon_defaults_do_not_override_any_candidate(self):
        classes = metadata_fixture_classes()
        app = SimpleNamespace(config=SimpleNamespace(napoleon_include_init_with_doc=False, napoleon_include_private_with_doc=False, napoleon_include_special_with_doc=False))
        for version in self.versions:
            path = ROOT / 'tooling' / version / 'sphinx/ext/napoleon/__init__.py'
            node = function(path, '_skip_member')
            module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), node], type_ignores=[])
            scope = {'inspect': inspect}
            exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), scope)
            for symbol, row in self.rows.items():
                cls_name, member = symbol.split('.')[-2:]
                obj = getattr(classes[cls_name], member)
                self.assertIsNone(scope['_skip_member'](app, 'class', member, obj, row['selection_state'] == 'selector_filtered_undocumented', {}))

    def test_sources_match_recorded_identities(self):
        meta = verify_inputs()
        self.assertEqual(len(meta['sources']), 74)
if __name__ == '__main__':
    unittest.main()
