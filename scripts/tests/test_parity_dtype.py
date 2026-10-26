"""Reject corrupted symbolic policy, source joins and false execution credit."""
import ast
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from atlas_parity import load, report
from atlas_parity_dtype import no_credit, prepare_dtype_policy, validate_dtype_policy, validate_joins
from atlas_parity_dtype_capture import PREFIX, graphs_from_tables, original_bytes, validate_capture
from atlas_parity_dtype_graph import validate_graphs
from atlas_parity_schema import ParityError, read_json

ROOT = Path(__file__).resolve().parents[2] / 'docs/parity'


class DtypePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load(ROOT)
        cls.index = read_json(ROOT / PREFIX / 'index.json')
        cls.original, cls.docs, _ = validate_capture(ROOT, cls.index)
        cls.graph = cls.original['promotion-graph.json']
        cls.catalog = cls.original['dtype-catalog.json']
        cls.policy = cls.original['policy-contracts.json']
        cls.cases = cls.original['acceptance-targets.json']
        cls.joins = cls.docs[PREFIX + 'joins.json']
        cls.citations = set(cls.original['source-receipts.json']['citations'])

    def validate(self, mutate=None):
        def altered_read(path):
            value = read_json(path)
            if mutate:
                mutate(path.relative_to(ROOT).as_posix(), value)
            return value
        b = self.bundle
        with patch('atlas_parity_dtype.read_json', side_effect=altered_read), \
             patch('atlas_parity_dtype_capture.read_json', side_effect=altered_read):
            prepared = prepare_dtype_policy(ROOT, b['program']['files']['dtype_policy'], b['program'])
            return validate_dtype_policy(prepared, b['program'], b['capabilities'], b['references'],
                                         b['mappings'], b['assigned'])

    def test_report_conserves_denominator_and_unrun_targets(self):
        result = report(self.bundle)
        self.assertEqual([result[k] for k in ['reference_declarations', 'mapped_declarations',
                         'partially_mapped_declarations', 'unmapped_declarations']], [38096, 2, 96, 37998])
        dtype = result['dtype_policy_designs']
        self.assertEqual(dtype['finite_source_pairs'], 9256)
        self.assertEqual(dtype['unrun_acceptance_targets'], 18)
        self.assertEqual(dtype['open_wider_gaps'], 10)
        self.assertEqual(dtype['ordinary_companion_evidence_gaps'], 8)
        self.assertEqual(dtype['framework_execution_credit'], 0)
        self.assertEqual(dtype['existing_mapped_API_associations'], 4)
        self.assertEqual(dtype['explicitly_unmapped_API_associations'], 5)
        self.assertFalse(dtype['public_denominator_changed'])

    def test_lossless_pair_table_reconstruction(self):
        reconstructed = graphs_from_tables(self.docs[PREFIX + 'graph.json'], self.docs[PREFIX + 'pairs.json'])
        self.assertEqual(reconstructed, self.graph)
        self.assertEqual(len(reconstructed['graphs']), 8)
        self.assertEqual(validate_graphs(reconstructed, self.catalog), 9256)

    def test_changed_edge_fails_even_with_unchanged_pair_count(self):
        graph = copy.deepcopy(self.graph)
        graph['graphs'][0]['adjacency']['strong:uint32'] = ['strong:int64', 'strong:uint64']
        with self.assertRaisesRegex(ParityError, 'source edges'):
            validate_graphs(graph, self.catalog)

    def test_wrong_join_and_missing_or_duplicated_pairs_fail(self):
        for change in [lambda rows: rows[0].update(lub_source_symbol='weak:float'),
                       lambda rows: rows.pop(), lambda rows: rows.append(rows[0])]:
            graph = copy.deepcopy(self.graph);change(graph['graphs'][0]['pair_table'])
            with self.subTest(change=change), self.assertRaises(ParityError):
                validate_graphs(graph, self.catalog)

    def test_profile_guards_and_config_relations_fail_closed(self):
        for change in [lambda d: d['graphs'][0]['source_branch_selections'][0].update(selected=True),
                       lambda d: d['profiles'][1].update(source_error='success'),
                       lambda d: d['graphs'][0].update(strict=True),
                       lambda d: d['profiles'][0]['companion_attributes'].update(uint1=True)]:
            graph = copy.deepcopy(self.graph);change(graph)
            with self.subTest(change=change), self.assertRaises(ParityError):
                validate_graphs(graph, self.catalog)

    def test_weak_nodes_are_not_final_numpy_dtype_or_API_legality(self):
        graph = copy.deepcopy(self.graph)
        graph['graphs'][0]['pair_table'][0]['final_numpy_dtype_or_api_legality_verified'] = True
        with self.assertRaisesRegex(ParityError, 'falsely qualifies'):
            validate_graphs(graph, self.catalog)

    def test_pair_metadata_cannot_claim_runtime_credit(self):
        pairs = copy.deepcopy(self.docs[PREFIX + 'pairs.json'])
        pairs['metadata']['role'] = 'verified_runtime_dtype_matrix'
        with self.assertRaisesRegex(ParityError, 'source-only'):
            graphs_from_tables(self.docs[PREFIX + 'graph.json'], pairs)

    def test_category_and_valid_sets_cannot_be_promoted_to_dtype_legality(self):
        for change in [lambda c: c.update(full_api_legality_complete=True),
                       lambda c: c['profiles'][0]['weak_nodes'].append('weak:bool'),
                       lambda c: c['profiles'][0]['valid_native_dtype_symbols'].remove('strong:float16'),
                       lambda c: c['profiles'][0]['category_members']['numeric'].append('strong:float0')]:
            catalog = copy.deepcopy(self.catalog);change(catalog)
            with self.subTest(change=change), self.assertRaises(ParityError):
                validate_graphs(self.graph, catalog)

    def test_no_credit_uses_exact_boolean_and_integer_types(self):
        for key, value in self.index['status'].items():
            for replacement in [True, 1] if value == 0 else [True]:
                changed = copy.deepcopy(self.index['status']);changed[key] = replacement
                with self.subTest(key=key, replacement=replacement), self.assertRaises(ParityError):
                    no_credit(changed)

    def check_joins(self, document, mappings=None, assigned=None):
        b = self.bundle
        validate_joins(document, self.policy, self.cases, b['capabilities'], b['references'], self.citations,
                       b['mappings'] if mappings is None else mappings,
                       b['assigned'] if assigned is None else assigned)

    def test_owner_prerequisite_source_case_and_ID_joins_reject_mutation(self):
        changes = [lambda d: d['clauses'][0]['policy_supplier'].update(owner='atlas'),
                   lambda d: d['clauses'][0]['policy_supplier'].update(prerequisites=[]),
                   lambda d: d['clauses'][0].update(source_entry=['rules', 1]),
                   lambda d: d['clauses'][0].update(source_citations=[]),
                   lambda d: d['clauses'][0].update(case_ids=[]),
                   lambda d: d['endpoints'][0].update(reference_id='unadmitted'),
                   lambda d: d['endpoints'][0].update(clause_ids=['JP99']),
                   lambda d: d['endpoints'][0].update(complete_API_mapping_credit=True)]
        for change in changes:
            document = copy.deepcopy(self.joins);change(document)
            with self.subTest(change=change), self.assertRaises(ParityError):
                self.check_joins(document)

    def test_actual_mapping_associations_and_suppliers_cannot_substitute_each_other(self):
        def astype(document):
            return next(r for r in document['endpoints'] if r['symbol'] == 'jax.numpy.astype')
        def unmapped(document):
            return next(r for r in document['endpoints'] if r['symbol'] == 'jax.grad')
        changes = [lambda d: astype(d)['canonical_API_mapping'].update(owner='eunomia'),
                   lambda d: astype(d)['canonical_API_mapping'].update(capability='NUM-PROMOTE'),
                   lambda d: astype(d)['canonical_API_mapping'].update(mapping_id='core-jax-jax-numpy-can-cast'),
                   lambda d: astype(d).update(canonical_API_mapping=dict(state='unmapped', reference_id=astype(d)['reference_id'])),
                   lambda d: astype(d)['policy_supplier'].update(capability='TEN-OPS', owner='coeus', prerequisites=['TEN-CORE']),
                   lambda d: astype(d).update(single_accountable_owner='eunomia'),
                   lambda d: unmapped(d).update(canonical_API_mapping=dict(state='mapped', reference_id=unmapped(d)['reference_id'], mapping_id='invented', capability='AD-REVERSE', owner='coeus'))]
        for change in changes:
            document = copy.deepcopy(self.joins);change(document)
            with self.subTest(change=change), self.assertRaises(ParityError):
                self.check_joins(document)
        row = astype(self.joins); identity = row['reference_id']
        assigned = dict(self.bundle['assigned']);assigned[identity] = 'core-jax-jax-numpy-can-cast'
        with self.assertRaisesRegex(ParityError, 'actual API assignment'):
            self.check_joins(self.joins, assigned=assigned)
        mappings = copy.deepcopy(self.bundle['mappings'])
        mappings[self.bundle['assigned'][identity]]['reference_ids'] = []
        with self.assertRaisesRegex(ParityError, 'actual API assignment'):
            self.check_joins(self.joins, mappings=mappings)

    def test_self_consistent_wrong_existing_clause_association_rejects(self):
        document = copy.deepcopy(self.joins)
        document['endpoints'][0]['clause_ids'] = ['JP08']
        for clause in document['clauses']:
            clause['related_existing_reference_ids'] = [r['reference_id'] for r in document['endpoints']
                                                       if clause['id'] in r['clause_ids']]
        with self.assertRaisesRegex(ParityError, 'endpoint clause join'):
            self.check_joins(document)

    def test_changed_source_pin_and_review_cannot_pass_actual_validator(self):
        changes = [('captured/source-receipts.json', lambda d: next(iter(d['sources'].values())).update(revision='a' * 40)),
                   ('independent-review.json', lambda d: d.update(reviewed_manifest_sha256='b' * 64)),
                   ('capture.json', lambda d: d.update(source_manifest_sha256='c' * 64)),
                   ('source-witnesses.json', lambda d: next(iter(d['witnesses'].values())).update(text='invented'))]
        for suffix, change in changes:
            with self.subTest(suffix=suffix), self.assertRaises(ParityError):
                self.validate(lambda path, d: change(d) if path == PREFIX + suffix else None)

    def test_changed_capture_roles_and_false_stage_credit_are_rejected(self):
        changes = [('capture.json', lambda d: d['captured'][0].update(original_path='scope.json')),
                   ('index.json', lambda d: d['status'].update(reference_runtime_cases=9256)),
                   ('joins.json', lambda d: d['clauses'][0].update(runtime_cases_executed=1)),
                   ('captured/acceptance-targets.json', lambda d: d['acceptance_targets'][0].update(reference_runtime='passed'))]
        for suffix, change in changes:
            with self.subTest(suffix=suffix), self.assertRaises(ParityError):
                self.validate(lambda path, d: change(d) if path == PREFIX + suffix else None)

    def test_CP02_raw_history_and_derived_evidence_status_are_distinct(self):
        raw = self.original['CP02-evidence-audit.json']['canonical_record']
        disposition = self.docs[PREFIX + 'companion-disposition.json']
        self.assertEqual(raw['pin_status'], 'decision_required_no_resolved_artifact_set')
        self.assertEqual(disposition['derived_pin_status'], 'evidence_required_no_resolved_artifact_set')
        self.assertIsNone(raw['selected_versions'])
        self.assertIsNone(raw['selected_artifact_sha256'])
        changes = [lambda d: d.update(resolved_artifacts=True),
                   lambda d: d.update(raw_record_sha256='a' * 64),
                   lambda d: d.update(true_user_scope_decisions_identified_now=['reduce_scope'])]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ParityError):
                self.validate(lambda path, d: change(d) if path == PREFIX + 'companion-disposition.json' else None)

    def test_original_reviewed_AST_text_is_parseable_by_CI_python_grammar(self):
        witnesses = self.docs[PREFIX + 'source-witnesses.json']['witnesses']
        for clause in self.policy['rules']:
            for function in clause['source_functions']:
                # Grammar compatibility check; portable exact spans, rather than
                # version-sensitive ast.unparse output, bind original bodies.
                ast.parse(witnesses[function['source']]['text'], feature_version=(3, 11))

    def test_new_artifacts_are_all_qualification_inputs(self):
        _, paths = self.validate()
        names = {p.relative_to(ROOT).as_posix() for p in paths}
        self.assertIn(PREFIX + 'index.json', names)
        self.assertIn('workflows/companion-inventory.json', names)
        self.assertTrue({r['path'] for r in self.index['artifacts']} <= names)


if __name__ == '__main__':
    unittest.main()
