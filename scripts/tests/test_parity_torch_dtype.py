"""Copied/reindexed repaired Torch definitions and independent analytical controls."""
import copy
from contextlib import contextmanager
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from atlas_parity import load, report
from atlas_parity_schema import ParityError, read_json
from atlas_parity_torch_dtype import prepare_torch_dtype, validate_torch_dtype
from atlas_parity_torch_dtype_capture import PREFIX, reconstruct_model, ROW_FIELDS
from atlas_parity_torch_dtype_model import validate_model, result_type
from atlas_parity_torch_dtype_oracles import analytical_control, validate_complex_case
from atlas_parity_tables import pack, unpack
ROOT = Path(__file__).resolve().parents[2] / 'docs/parity'


def write(path, value, indent=None):path.write_text(json.dumps(value, indent=indent) + '\n')


class TorchDtypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load(ROOT)
        cls.prepared = prepare_torch_dtype(ROOT, PREFIX + 'index.json', cls.bundle['program'])
        _, cls.index, cls.original, cls.docs, _ = cls.prepared

    @contextmanager
    def tree(self):
        with tempfile.TemporaryDirectory(prefix='atlas-torch-dtype-reindex-') as directory:
            root = Path(directory);shutil.copytree(ROOT / PREFIX, root / PREFIX)
            (root / 'reference').mkdir();shutil.copyfile(ROOT / 'reference/pytorch.json', root / 'reference/pytorch.json')
            yield root

    def validate(self, root=ROOT):
        b = self.bundle;p = prepare_torch_dtype(root, PREFIX + 'index.json', b['program'])
        return validate_torch_dtype(p, b['program'], b['capabilities'], b['references'], b['mappings'], b['assigned'])[0]

    def reindex(self, root):
        path = root / PREFIX / 'index.json';index = read_json(path)
        for row in index['artifacts']:row['sha256'] = hashlib.sha256((root / row['path']).read_bytes()).hexdigest()
        write(path, index)

    def corrupt(self, name, mutate, message='Torch'):
        with self.tree() as root:
            path = root / PREFIX / name;value = read_json(path);mutate(value);write(path, value);self.reindex(root)
            with self.assertRaisesRegex(ParityError, message):self.validate(root)

    def test_program10_conserves_all_IDs_stages_and_source_counts(self):
        result = report(self.bundle);torch = result['torch_native_dtype_designs']
        self.assertEqual(result['program_version'], '2026-10-26.10')
        self.assertEqual([result[k] for k in ['reference_declarations', 'mapped_declarations', 'partially_mapped_declarations', 'unmapped_declarations']], [38096, 2, 96, 37998])
        self.assertEqual([torch[k] for k in ['source_receipts', 'source_line_witnesses', 'native_dtype_enums', 'core_promotion_cells', 'native_promotion_pairs', 'native_cast_permission_pairs']], [45, 88, 47, 196, 2209, 2209])
        self.assertEqual(torch['runtime_cases_executed'], 0);self.assertFalse(torch['public_denominator_changed'])
        self.assertEqual(torch['analytical_or_source_parametric_cases_unrun'], 66)
        self.assertEqual(torch['open_named_gaps'], 14)

    def test_lossless_model_reconstructs_original_insertion_order(self):
        model = reconstruct_model(self.docs[PREFIX + 'model.json'], {key:self.docs[PREFIX + key + '.json'] for key in ROW_FIELDS})
        self.assertEqual(model, self.original['dtype-model.json'])
        self.assertEqual(len(model['native_promotion_pairs']), 2209)

    def test_native_model_independently_reconstructs_source_and_opmath(self):
        categories, axis, table = validate_model(self.original['dtype-model.json'], self.original['source-witnesses.json'], self.original['computation-policies.json'])
        self.assertEqual(len(axis), 14);self.assertEqual(table['BFloat16','Half'], 'Float')
        self.assertEqual(table['Byte','Char'], 'Short');self.assertIn('Float8_e4m3fn', categories['float8'])
        for value in [False, 0.0]:
            model=copy.deepcopy(self.original['dtype-model.json']);model['native_enum_records'][0]['serialization_ordinal']=value
            with self.assertRaisesRegex(ParityError,'enum/classifier'):validate_model(model,self.original['source-witnesses.json'],self.original['computation-policies.json'])

    def test_ordered_equal_quantized_and_mixed_error_branches_are_distinct(self):
        pairs = {(r['left'],r['right']):r for r in self.original['dtype-model.json']['native_promotion_pairs']}
        self.assertEqual(pairs['QInt8','QInt8']['dtype'], 'QInt8')
        self.assertEqual(pairs['QInt8','Float']['branch'], 'quantized')
        self.assertEqual(pairs['Bits8','Float8_e4m3fn']['branch'], 'bits')

    def test_same_count_wrong_pair_fails_independent_model(self):
        model = copy.deepcopy(self.original['dtype-model.json']);model['native_promotion_pairs'][0]['dtype'] = 'Double'
        with self.assertRaisesRegex(ParityError, 'promotion pairs'):validate_model(model, self.original['source-witnesses.json'], self.original['computation-policies.json'])

    def test_helper_compute_type_cannot_be_invented(self):
        policies = copy.deepcopy(self.original['computation-policies.json']);policies['native_opmath_specializations'][0]['cpp_computation_type'] = 'double'
        with self.assertRaisesRegex(ParityError, 'computation specializations'):validate_model(self.original['dtype-model.json'], self.original['source-witnesses.json'], policies)

    def test_reindexed_false_aggregate_and_count_type_reject(self):
        for value in [True, 10.0, 11]:self.corrupt('index.json', lambda d,v=value:d['counts'].update(public_endpoint_partial_contracts=v), 'Torch aggregate')

    def test_reindexed_runtime_and_fullscope_credit_reject(self):
        for change in [lambda d:d['status'].update(reference_runtime_cases=1), lambda d:d['status'].update(whole_API_semantics_complete=True), lambda d:d['status'].update(external_verified=0)]:
            self.corrupt('index.json', change, 'cannot assert complete API')
        self.corrupt('source-proof.json', lambda d:d.update(whole_API_or_runtime_credit=True), 'source proof projection')

    def test_reindexed_unknown_header_or_role_reject(self):
        self.corrupt('index.json', lambda d:d.update(qualified=True), 'unexpected')
        self.corrupt('joins.json', lambda d:d['records'][0].update(actual_owner='atlas'), 'unexpected')

    def test_reindexed_false_runtime_case_role_reject(self):
        for value in [True, 0]:self.corrupt('joins.json', lambda d,v=value:d['cases'][0].update(runtime_executed=v))

    def test_actual_mapping_supplier_and_proposed_facade_are_separate(self):
        rows = self.docs[PREFIX + 'joins.json']['records']
        self.assertEqual(sum(r['canonical_API_mapping']['state']=='mapped' for r in rows),3)
        self.assertEqual(sum(r['canonical_API_mapping']['state']=='unmapped' for r in rows),7)
        for row in rows:
            self.assertEqual(row['policy_supplier']['owner'],'eunomia');self.assertEqual(row['facade_proposal']['owner'],'coeus')
            self.assertIsNone(row['actual_implementation_owner'])

    def test_reindexed_actual_owner_cannot_be_policy_or_facade_substitute(self):
        self.corrupt('joins.json',lambda d:d['records'][0]['canonical_API_mapping'].update(owner='eunomia'),'actual mapping')
        self.corrupt('joins.json',lambda d:d['records'][0]['facade_proposal'].update(role='canonical_API_owner'),'exact relation')
        self.corrupt('joins.json',lambda d:d['records'][0].update(actual_implementation_owner='coeus'),'NoneType')

    def test_actual_Eunomia_association_can_differ_from_Coeus_facade(self):
        from atlas_parity_torch_dtype_joins import expected_joins, validate_joins
        b=self.bundle;mappings=copy.deepcopy(b['mappings'])
        row=mappings['core-pytorch-torch-promote-types'];row.update(owner='eunomia',capability='NUM-PROMOTE')
        document=expected_joins(self.original['contracts.json'],self.original['acceptance-cases.json'],b['capabilities'],mappings,b['assigned'])
        validate_joins(document,self.original['contracts.json'],self.original['acceptance-cases.json'],self.original['admitted-bindings.json'],b['capabilities'],b['references'],mappings,b['assigned'])
        self.assertEqual(document['records'][0]['canonical_API_mapping']['owner'],'eunomia')
        self.assertEqual(document['records'][0]['facade_proposal']['owner'],'coeus')

    def test_reindexed_unmapped_ID_cannot_gain_mapping(self):
        self.corrupt('joins.json', lambda d:d['records'][2]['canonical_API_mapping'].update(state='mapped',mapping_id='invented',capability='TEN-OPS',owner='coeus'),'actual mapping')

    def test_reindexed_existing_ID_substitution_reject(self):
        self.corrupt('joins.json',lambda d:d['records'][0].update(reference_id=d['records'][1]['reference_id']))

    def test_reindexed_nested_source_selectors_require_exact_integer(self):
        for group in ['records','cases']:
            for value in [False, True, 0.0, -0.0, -1, '0', {}, []]:
                self.corrupt('joins.json',lambda d,g=group,v=value:d[g][0].update(source_entry=['records',v]),'typed source selector')
        for value in [False, 0.0, -1, '0']:
            self.corrupt('source-proof.json',lambda d,v=value:d['records'][0].update(source_entry=['records',v]),'typed source selector')

    def test_reindexed_shared_selectors_preserve_exact_source_row_identity(self):
        for name,group in [('joins.json','records'), ('joins.json','cases'), ('source-proof.json','records')]:
            for selector in [[], ['records', 1], ['records', 0, 'id'], ['records', 100000]]:
                with self.subTest(name=name, group=group, selector=selector):
                    self.corrupt(name,lambda d,g=group,s=selector:d[g][0].update(source_entry=s),'typed source selector')

    def test_reindexed_source_hash_or_quote_role_reject(self):
        self.corrupt('source-proof.json', lambda d:d['records'][0].update(sha256='0'*64),'source proof projection')
        self.corrupt('source-proof.json', lambda d:d['records'][0].update(span_ids=[]),'source proof projection')

    def test_reindexed_same_count_source_pair_corruption_reject(self):
        def mutate(d):
            rows=unpack(d);rows[0]['dtype']='Double';d.clear();d.update(pack(rows,{'role':'native_promotion_pairs','qualification':'source_only_not_public_kernel_registry'}))
        self.corrupt('native_promotion_pairs.json',mutate,'lossless accepted source')

    def test_reindexed_table_cannot_hide_unknown_runtime_fields(self):
        def change(document):
            rows = unpack(document)
            rows[0]['runtime_verified'] = True
            document.clear();document.update(pack(rows, {'role':'native_promotion_pairs','qualification':'source_only_not_public_kernel_registry'}))
        self.corrupt('native_promotion_pairs.json',change,'unknown fields')

    def test_conditional_policy_cannot_drop_cases(self):
        self.corrupt('acceptance-plan.json',lambda d:d['packages'][1]['acceptance_case_ids'].pop(),'operation/case domain')

    def test_reindexed_manifest_review_and_history_pins_reject(self):
        self.corrupt('independent-review.json',lambda d:d.update(result='runtime_qualified'),'immutable pin')
        self.corrupt('captured/manifest.json',lambda d:d['counts'].update(runtime_cases_executed=1),'immutable pin')
        self.corrupt('captured/correction-history.json',lambda d:d.update(framework_runtime_cases_executed=1),'lossless accepted source')

    def test_complex_original_case_and_six_real_coordinate_oracles(self):
        source=next(c for c in self.original['acceptance-cases.json']['records'] if c['id']=='ADD-COMPLEX-GRAD')
        self.assertEqual(validate_complex_case(source)['result'],(8,3))
        for control in self.docs[PREFIX+'acceptance-plan.json']['analytical_controls']:
            case=control['case'];observed=validate_complex_case(case);f=case['fixture']
            a,b=[f[k]['values'][0] for k in ['a','b']];alpha=f['alpha']['value'];seed=Fraction(f['loss']['upstream_cotangent']['value'])
            coords=[Fraction(a['real']),Fraction(a['imag']),Fraction(b['real']),Fraction(b['imag'])];ar,ai=Fraction(alpha['real']),Fraction(alpha['imag'])
            loss=lambda x:seed*(x[0]+ar*x[2]-ai*x[3]);epsilon=Fraction(1,1024);gradient=[]
            for i in range(4):
                left,right=list(coords),list(coords);left[i]-=epsilon;right[i]+=epsilon;gradient.append((loss(right)-loss(left))/(2*epsilon))
            self.assertEqual(observed['reverse_grad_a'],tuple(gradient[:2]));self.assertEqual(observed['reverse_grad_b'],tuple(gradient[2:]))

    def complex_corrupt(self, mutate):
        self.corrupt('acceptance-plan.json', lambda d:mutate(d['analytical_controls'][0]['case']))

    def test_reindexed_complex_alpha_decoder_rejects_array_or_tensor(self):
        self.complex_corrupt(lambda c:c['fixture'].update(alpha=[2,1]))
        self.complex_corrupt(lambda c:c['fixture']['alpha'].update(python_type='tensor'))

    def test_reindexed_complex_rank_dtype_and_grad_leaf_reject(self):
        for change in [lambda c:c['fixture']['a'].update(shape=[1]),lambda c:c['fixture']['a'].update(dtype='float64'),lambda c:c['fixture']['a'].update(requires_grad=False)]:self.complex_corrupt(change)

    def test_reindexed_complex_loss_and_cotangent_tags_reject(self):
        self.complex_corrupt(lambda c:c['fixture']['loss'].update(output_shape=[1]))
        self.complex_corrupt(lambda c:c['fixture']['loss']['upstream_cotangent'].update(kind='complex'))

    def test_reindexed_complex_stale_outputs_and_gradients_reject(self):
        self.complex_corrupt(lambda c:c['fixture']['a']['values'][0].update(real=2))
        self.complex_corrupt(lambda c:c['fixture']['alpha']['value'].update(imag=2))
        self.complex_corrupt(lambda c:c['fixture']['loss']['upstream_cotangent'].update(value=2))
        self.complex_corrupt(lambda c:c['expected']['reverse_grad_b']['values'][0].update(imag=1))

    def test_input_sensitive_rank_and_default_rule(self):
        categories,axis,table=validate_model(self.original['dtype-model.json'],self.original['source-witnesses.json'],self.original['computation-policies.json'])
        operands=[dict(kind='tensor',dtype='Float',rank=1),dict(kind='tensor',dtype='Double',rank=0)]
        self.assertEqual(result_type(operands,categories,axis,table),'Float');operands[1]['rank']=1
        self.assertEqual(result_type(operands,categories,axis,table),'Double');operands[1]['rank']=False
        with self.assertRaisesRegex(ParityError,'rank fixture'):result_type(operands,categories,axis,table)

    def test_reindexed_conditional_package_cannot_claim_ready_owner_or_runtime(self):
        self.corrupt('acceptance-plan.json',lambda d:d['packages'][1].update(readiness='ready'))
        self.corrupt('acceptance-plan.json',lambda d:d['packages'][1].update(planned_owner='atlas'))
        self.corrupt('acceptance-plan.json',lambda d:d.update(framework_runtime_cases_executed=1))

    def test_valid_reformat_reindex_control(self):
        with self.tree() as root:
            for name in ['joins.json','source-proof.json','acceptance-plan.json','model.json','core_lookup_cells.json']:
                path=root/PREFIX/name;write(path,read_json(path),indent=3)
            self.reindex(root);self.assertEqual(self.validate(root)['native_promotion_pairs'],2209)

    def test_valid_changed_complex_inputs_and_derived_outputs_control(self):
        with self.tree() as root:
            path=root/PREFIX/'acceptance-plan.json';d=read_json(path);d['analytical_controls'][0]['case']=analytical_control((2,-1),(0.5,2),(-2,0.5),-0.5)
            write(path,d);self.reindex(root);self.assertEqual(self.validate(root)['analytical_complex_controls'],6)

    def test_introduction_versions_are_immutable_and_source_specific(self):
        self.assertEqual(read_json(ROOT/'dtype-policy/jax-20261026/index.json')['parent_program_version'],'2026-10-26.8')
        self.assertEqual(read_json(ROOT/'dtype-policy/numpy-20261026/index.json')['parent_program_version'],'2026-10-26.9')
        self.assertEqual(self.index['parent_program_version'],'2026-10-26.10')
        self.corrupt('index.json',lambda d:d.update(parent_program_version='2026-10-26.9'),'introduction')


if __name__=='__main__':unittest.main()
