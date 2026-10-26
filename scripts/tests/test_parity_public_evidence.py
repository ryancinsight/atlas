"""Copied, physically reindexed attacks on accepted public-evidence integration."""
import ast
import copy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from atlas_parity import load, report
from atlas_parity_public_capture import PREFIX, PACKETS, NO_CREDIT, capture, manifest_files, original_bytes, sha
from atlas_parity_public_evidence import prepare_public_evidence, validate_public_evidence
from atlas_parity_schema import ParityError, read_json
from atlas_parity_tables import pack, unpack

ROOT = Path(__file__).resolve().parents[2] / 'docs/parity'


def write(path, value, indent=None):
    path.write_text(json.dumps(value, sort_keys=True, indent=indent, ensure_ascii=False) + '\n')


class PublicEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load(ROOT)
        cls.prepared = prepare_public_evidence(ROOT, PREFIX + 'index.json', cls.bundle['program'])

    def validate(self, root):
        b = self.bundle
        prepared = prepare_public_evidence(root, PREFIX + 'index.json', b['program'])
        return validate_public_evidence(prepared, b['program'], b['references'], b['public_scope'],
                                        b['capabilities'], b['mappings'], b['assigned'])[0]

    @contextmanager
    def actual_tree(self, full=False):
        with tempfile.TemporaryDirectory(prefix='atlas-public-evidence-reindex-') as directory:
            root = Path(directory)
            shutil.copytree(ROOT if full else ROOT / PREFIX, root if full else root / PREFIX,
                            dirs_exist_ok=True)
            yield root

    def reindex(self, root):
        for config in PACKETS.values():
            path = root / PREFIX / config['directory'] / 'index.json'
            value = read_json(path)
            for row in value['artifacts']:
                row['sha256'] = hashlib.sha256((root / row['path']).read_bytes()).hexdigest()
            write(path, value)
        path = root / PREFIX / 'index.json'
        value = read_json(path)
        for row in value['artifacts']:
            row['sha256'] = hashlib.sha256((root / row['path']).read_bytes()).hexdigest()
        write(path, value)

    def corrupt(self, relative, mutate, expected='public evidence'):
        with self.actual_tree() as root:
            path = root / PREFIX / relative
            value = read_json(path)
            mutate(value)
            write(path, value)
            self.reindex(root)
            with self.assertRaisesRegex(ParityError, expected):
                self.validate(root)

    def rewrite_selected(self, root, key, name, mutate):
        """Alter actual selected bytes and self-consistent capture claims, not read mocks."""
        directory = PACKETS[key]['directory']
        index_path = root / PREFIX / directory / 'index.json'
        index = read_json(index_path)
        selected = next(r for r in index['capture']['selected'] if r['original_path'] == name)
        value = copy.deepcopy(self.prepared[2][key][name])
        mutate(value)
        if selected['storage'] == 'column-records':
            collection = selected['collection']
            write(root / selected['paths'][0], {k:v for k,v in value.items() if k != collection})
            table = read_json(root / selected['paths'][1])
            write(root / selected['paths'][1], pack(value[collection], table['metadata']))
        else:
            write(root / selected['paths'][0], value)
        data = original_bytes(value, selected['serialization'])
        selected['original_sha256'] = sha(data)
        write(index_path, index)
        return data

    def rebind_manifest_and_review(self, root, key, name, data):
        directory = root / PREFIX / PACKETS[key]['directory']
        manifest = read_json(directory / 'source-manifest.json')
        receipt = manifest_files(manifest)[name]
        receipt.update(bytes=len(data), sha256=sha(data))
        write(directory / 'source-manifest.json', manifest)
        review = read_json(directory / 'independent-review.json')
        review['reviewed_manifest_sha256'] = sha((directory / 'source-manifest.json').read_bytes())
        write(directory / 'independent-review.json', review)
        path = directory / 'index.json'; index = read_json(path)
        index['source_manifest_sha256'] = review['reviewed_manifest_sha256']
        index['source_review_sha256'] = sha((directory / 'independent-review.json').read_bytes())
        write(path, index)

    def test_selected_roles_roundtrip_to_each_independently_reviewed_manifest(self):
        for key, config in PACKETS.items():
            index = read_json(ROOT / PREFIX / config['directory'] / 'index.json')
            original, paths = capture(ROOT,key,PREFIX + config['directory'] + '/index.json')
            manifest = manifest_files(read_json(ROOT / PREFIX / config['directory'] / 'source-manifest.json'))
            self.assertEqual(set(original), set(config['selected']))
            self.assertEqual(set(paths), set(p for p in self.bundle['extra_inputs'] if p in paths))
            for selected in index['capture']['selected']:
                name = selected['original_path']
                data = (ROOT / selected['paths'][0]).read_bytes() if selected['storage']=='original-bytes' else original_bytes(original[name], selected['serialization'])
                self.assertEqual((sha(data),len(data)),(manifest[name]['sha256'],manifest[name]['bytes']))

    def test_reindexed_missing_duplicate_extra_IDs_or_unknown_source_roles_reject(self):
        changes = [lambda rows: rows.pop(), lambda rows: rows.__setitem__(1,rows[0]),
                   lambda rows: rows.append(copy.deepcopy(rows[0])),
                   lambda rows: rows[0].update(reference_id='invented@1|function|x|1234'),
                   lambda rows: rows[0].update(source_artifact='ownership-route-comparison.json'),
                   lambda rows: rows[0].update(packet='tensorflow'),
                   lambda rows: rows[0].update(source_entry=['records','0'])]
        for mutate in changes:
            def change(table, mutate=mutate):
                rows=unpack(table); mutate(rows); table.clear();table.update(pack(rows,table_metadata()))
            self.corrupt('joins.json',change)

    def test_frozen_source_path_and_blob_cannot_be_co_mutated_with_capture_claim(self):
        for field, replacement in [('path','tensorflow/python/other.py'),('git_blob_sha','0'*40)]:
            with self.actual_tree() as root:
                self.rewrite_selected(root,'tf492','source-registry.json',
                    lambda d,f=field,v=replacement: d['sources'][0].update({f:v}))
                self.reindex(root)
                with self.assertRaisesRegex(ParityError,'lossless accepted source'):
                    self.validate(root)

    def test_frozen_source_and_output_owner_claims_cannot_rebind_independent_certificate(self):
        for key, name, mutate in [
            ('six','inputs/original-six.json',lambda d:d[0]['binding'].update(contract='jax:numpy-create-zeros')),
            ('tf492','ownership-route-comparison.json',lambda d:d['records'][0].update(proposed_owner='atlas'))]:
            with self.actual_tree(full=True) as root:
                data=self.rewrite_selected(root,key,name,mutate)
                path=root/PREFIX/'joins.json';table=read_json(path);rows=unpack(table)
                row=next(r for r in rows if r['packet']==key)
                if key=='six':row['frozen_binding']['contract']='jax:numpy-create-zeros'
                else:row['frozen_source_route']['proposed_owner']='atlas'
                write(path,pack(rows,table_metadata()))
                # Even a new self-consistent manifest, claimed source certificate and physical
                # index cannot replace the independently pinned original review/manifest.
                self.rebind_manifest_and_review(root,key,name,data);self.reindex(root)
                with self.assertRaisesRegex(ParityError,'public evidence packet metadata/no credit'):
                    load(root)

    def test_review_role_capture_count_or_nonoperative_design_cannot_promote(self):
        for key,config in PACKETS.items():
            for mutate in (lambda d:d.update(frozen_atlas_revision='0'*40),
                           lambda d:d['capture'].update(complete_for_selected_roles=1),
                           lambda d:d['capture'].update(source_files=False),
                           lambda d:d['status'].update(route_owner_verifications=1)):
                self.corrupt(config['directory']+'/index.json',mutate)
        self.corrupt('index.json',lambda d:d['admission_design'].update(applied=True))
        self.corrupt('index.json',lambda d:d.update(full_public_surface_complete=0))

    def test_canonical_validation_needs_no_original_cache_or_foreign_runtime(self):
        # An actual copy contains neither original packet directory nor foreign source files.
        with self.actual_tree() as root:
            self.assertFalse((root/'sources').exists())
            self.assertFalse((root/'tooling').exists())
            self.assertEqual(self.validate(root)['existing_reference_links'],498)
        scripts=ROOT.parents[1]/'scripts'
        modules=list(scripts.glob('atlas_parity_public_*.py'))+[scripts/'parity/capture_public_evidence.py']
        for path in modules:
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node,(ast.Import,ast.ImportFrom)):
                    names=[n.name for n in node.names] if isinstance(node,ast.Import) else [node.module]
                    self.assertTrue(all(n.split('.')[0] not in {'numpy','jax','torch','tensorflow','keras','sphinx'} for n in names),path)
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
                    self.assertNotIn(node.func.id,{'eval','exec','compile','__import__'},path)

    def test_real_baseline_accounting_is_not_promoted(self):
        r = report(self.bundle)
        self.assertEqual([r[k] for k in ('reference_declarations', 'mapped_declarations',
                         'partially_mapped_declarations', 'unmapped_declarations')], [38096, 2, 96, 37998])
        p = r['public_evidence']
        self.assertEqual(p['existing_reference_links'], 498)
        self.assertEqual(p['unresolved_publicness_retained'], 498)
        self.assertEqual(p['TF_proposal_categories'], {'internal_implementation_identity': 6,
            'required_operator_extension_or_protocol_view': 5,
            'required_extension_namespace_grouping_view': 1, 'publicness_unresolved': 480})
        self.assertEqual(p['new_reference_IDs'], 0)
        self.assertEqual(p['framework_execution_credit'], 0)
        self.assertEqual(p['tooling_callable_views_not_new_IDs'], 974)
        self.assertEqual(p['TF_whole_small_golden_quotes'], 13)
        self.assertEqual(p['admission_certificates_applied'], 0)
        self.assertEqual(r['public_scope']['visibility']['internal_source_candidate'], 3)
        self.assertTrue(all(not s['public_surface_complete'] for s in r['snapshots']))

    def test_498_live_and_frozen_roles_and_all_proposals_remain_separate(self):
        rows = unpack(read_json(ROOT / PREFIX / 'joins.json'))
        self.assertEqual(len({r['reference_id'] for r in rows}), 498)
        for row in rows:
            self.assertEqual(row['live_binding']['visibility'], 'publicness_unresolved')
            self.assertTrue(row['live_binding']['retained_obligation'])
            self.assertEqual(row['live_API_mapping']['state'], 'unmapped')
            self.assertIsNone(row['actual_implementation_owner'])
            self.assertFalse(row['out_of_scope_admission_applied'])
            self.assertEqual(row['status'], NO_CREDIT)
        self.assertEqual({r['packet'] for r in rows}, {'tf492', 'six'})

    def test_reindexed_typed_selectors_do_not_accept_python_numeric_aliases(self):
        for value in (False, 0.0, -0.0, -1, 498):
            def change(table, value=value):
                rows = unpack(table)
                rows[0]['source_entry'] = ['records', value]
                table.clear(); table.update(pack(rows, table_metadata()))
            with self.subTest(value=value):
                self.corrupt('joins.json', change)

    def test_reindexed_valid_other_row_is_not_the_same_reference(self):
        def change(table):
            rows = unpack(table); rows[0]['source_entry'] = ['records', 1]
            table.clear(); table.update(pack(rows, table_metadata()))
        self.corrupt('joins.json', change)

    def test_reindexed_output_owner_source_role_or_credit_mutation_rejects(self):
        changes = [lambda r:r.update(actual_implementation_owner='coeus'),
                   lambda r:r['live_API_mapping'].update(owner='coeus'),
                   lambda r:r['live_contract_route'].update(planned_owner='atlas'),
                   lambda r:r['frozen_binding'].update(contract='jax:numpy-create-zeros'),
                   lambda r:r.update(out_of_scope_admission_applied=True),
                   lambda r:r['status'].update(semantic_completion_credit=1),
                   lambda r:r.update(runtime_verified=True)]
        for mutate in changes:
            def change(table, mutate=mutate):
                rows = unpack(table); mutate(rows[0]); table.clear(); table.update(pack(rows, table_metadata()))
            self.corrupt('joins.json', change)

    def test_reindexed_count_status_and_unknown_metadata_rejects(self):
        for mutate in (lambda d:d['counts'].update(existing_reference_links=498.0),
                       lambda d:d['status'].update(new_reference_IDs=False),
                       lambda d:d['status'].update(whole_public_surface_complete=True),
                       lambda d:d.update(integration_review_approved=True)):
            self.corrupt('index.json', mutate)

    def test_manifest_and_independent_certificate_cannot_be_rebound_together(self):
        key = 'six'; config = PACKETS[key]; directory = config['directory']
        with self.actual_tree() as root:
            path = root / PREFIX / directory
            manifest = read_json(path / 'source-manifest.json')
            manifest['claimed_revision'] = '0' * 40
            write(path / 'source-manifest.json', manifest)
            review = read_json(path / 'independent-review.json')
            review['reviewed_manifest_sha256'] = hashlib.sha256((path/'source-manifest.json').read_bytes()).hexdigest()
            write(path / 'independent-review.json', review)
            index = read_json(path / 'index.json')
            index['source_manifest_sha256'] = review['reviewed_manifest_sha256']
            index['source_review_sha256'] = hashlib.sha256((path/'independent-review.json').read_bytes()).hexdigest()
            write(path / 'index.json', index)
            self.reindex(root)
            with self.assertRaisesRegex(ParityError, 'public evidence'):
                self.validate(root)

    def test_reindexed_source_path_blob_or_line_identity_cannot_change(self):
        for mutate in (lambda d:d['spans'][0].update(text='invented\n'),
                       lambda d:d['spans'][0].update(source_key='pytorch:other.py'),
                       lambda d:d['spans'][0].update(end=False),
                       lambda d:d['tooling_AST'][0].update(AST_dump='invented')):
            self.corrupt('six-portable-witnesses.json', mutate)

    def test_lossless_selected_input_and_output_cannot_justify_each_other(self):
        directory = PACKETS['six']['directory']
        # Mutate an accepted original input plus a derived join and recompute all physical index hashes.
        with self.actual_tree() as root:
            path = root / PREFIX / directory / 'captured/inputs/original-six.json'
            value = read_json(path)
            value[0]['binding']['contract'] = 'jax:numpy-create-zeros'
            write(path, value)
            joins = root / PREFIX / 'joins.json'; table = read_json(joins); rows = unpack(table)
            next(r for r in rows if r['packet']=='six')['frozen_binding']['contract']='jax:numpy-create-zeros'
            write(joins, pack(rows, table_metadata())); self.reindex(root)
            with self.assertRaisesRegex(ParityError, 'public evidence'):
                self.validate(root)

    def test_valid_json_reformat_and_column_dictionary_reindex_controls(self):
        with self.actual_tree() as root:
            joins = root / PREFIX / 'joins.json'; table = read_json(joins)
            for column in table['columns']:
                values = table['tables'][column]; count = len(values)
                table['tables'][column] = list(reversed(values))
                position = table['columns'].index(column)
                for row in table['rows']:
                    if row[position] >= 0:row[position] = count - row[position] - 1
            write(joins, table, indent=3)
            index = root / PREFIX / PACKETS['six']['directory'] / 'captured/configuration-selection-evidence.json'
            write(index, read_json(index), indent=3)
            self.reindex(root)
            self.assertEqual(self.validate(root)['existing_reference_links'], 498)

    def test_full_load_rejects_typed_selector_after_actual_reindex(self):
        with self.actual_tree(full=True) as root:
            path = root / PREFIX / 'joins.json'; table = read_json(path); rows = unpack(table)
            rows[0]['source_entry'] = ['records', False]
            write(path, pack(rows, table_metadata())); self.reindex(root)
            with self.assertRaisesRegex(ParityError, 'public evidence'):
                load(root)


def table_metadata():
    return {'role': 'source_evidence_not_scope_or_semantic_admission', 'introduced_in_program': '2026-10-26.11'}
