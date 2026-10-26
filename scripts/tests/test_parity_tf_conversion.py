"""Real copied/reindexed full-loader tests for the bounded TF conversion slice."""
import copy
from contextlib import contextmanager
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

from atlas_parity import load, report
from atlas_parity_schema import ParityError, read_json
from atlas_parity_tf_conversion import prepare_tf_conversion, validate_tf_conversion
from atlas_parity_tf_conversion_capture import PREFIX, SELECTED, PACKET_SHA
from atlas_parity_tf_conversion_model import round_target
from atlas_parity_public_capture import original_bytes

ROOT=Path(__file__).resolve().parents[2]/'docs/parity'
REPO=ROOT.parents[1]


def write(path,value):path.write_text(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n')
def by(rows,key):return next(r for r in rows if r['id']==key)


class TFConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=load(ROOT)
        cls.prepared=prepare_tf_conversion(ROOT,PREFIX+'index.json',cls.bundle['program'])
        cls.original=cls.prepared[2]

    @contextmanager
    def copied(self):
        with tempfile.TemporaryDirectory(prefix='atlas-tf-full-loader-') as tmp:
            root=Path(tmp)/'parity';shutil.copytree(ROOT,root);yield root

    def reindex(self,root):
        p=root/PREFIX/'index.json';d=read_json(p)
        for row in d['artifacts']:row['sha256']=hashlib.sha256((root/row['path']).read_bytes()).hexdigest()
        write(p,d)

    def mutate(self,name,change,pattern='TF conversion'):
        with self.copied() as root:
            p=root/PREFIX/name;d=read_json(p);change(d);write(p,d);self.reindex(root)
            with self.assertRaisesRegex(ParityError,pattern):load(root)

    def test_counts_stages_and_committed_input_roles_are_preserved(self):
        result=report(self.bundle);d=result['tensorflow_conversion_designs']
        self.assertEqual([result[k] for k in ['reference_declarations','mapped_declarations','partially_mapped_declarations','unmapped_declarations']],[38096,2,96,37998])
        self.assertEqual([d[k] for k in ['selected_source_blobs','portable_source_spans','future_cases_UNRUN','open_gap_groups']],[21,63,30,10])
        self.assertEqual([d[k] for k in ['existing_API_identities','existing_partial_API_identities','existing_unmapped_API_identities']],[10,4,6])
        self.assertEqual(d['primary_mapping_stage'],'unmapped');self.assertIsNone(d['actual_implementation_owner'])
        self.assertEqual(d['framework_execution_credit'],0)
        consumed={p.resolve() for p in self.bundle['extra_inputs']}
        self.assertIn((ROOT/PREFIX/'index.json').resolve(),consumed)
        for row in self.prepared[1]['artifacts']:self.assertIn((ROOT/row['path']).resolve(),consumed)
        self.assertEqual(self.prepared[1]['introduced_in_program'],'2026-10-26.12')

    def test_all24_selected_roles_reconstruct_the_exact_source_bytes(self):
        manifest=read_json(ROOT/PREFIX/'source-manifest.json')
        self.assertEqual(hashlib.sha256(original_bytes(manifest,'pretty-ascii')).hexdigest(),PACKET_SHA)
        rows={r['path']:r for r in manifest['artifacts']}
        capture=read_json(ROOT/PREFIX/'capture.json')
        self.assertEqual({r['original_path'] for r in capture['selected']},SELECTED)
        for item in capture['selected']:
            path=ROOT/item['path'];raw=original_bytes(read_json(path),'pretty-ascii') if item['storage']=='compact-json' else path.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),rows[item['original_path']]['sha256'])
            self.assertEqual(len(raw),rows[item['original_path']]['bytes'])

    def test001_002_003_captured_false_source_semantics_cannot_be_reindexed(self):
        for key,text in [('C05-SOFT-HINT','Normal None retries unhinted.'),('C04-REGISTRY','All Python numeric types are banned.'),('C07-NATIVE-IDENTITY','Capture invokes superclass afterwards.')]:
            with self.subTest(key=key):self.mutate('captured/proposal.json',lambda d,k=key,t=text:by(d['clauses'],k).update(contract=t))

    def test004_source_receipt_quote_capture_manifest_co_forgery_fails(self):
        with self.copied() as root:
            p=root/PREFIX/'captured/source-witnesses.json';d=read_json(p)
            row=next(w for w in d['records'] if 'return overload(dtype, name)' in w['text'])
            row['text']=row['text'].replace('return overload(dtype, name)','return None')
            row['sha256']=hashlib.sha256(row['text'].encode()).hexdigest();write(p,d)
            capture_path=root/PREFIX/'capture.json';capture=read_json(capture_path)
            role=next(r for r in capture['selected'] if r['original_path']=='source-witnesses.json')
            raw=original_bytes(d,'pretty-ascii');role['sha256']=hashlib.sha256(raw).hexdigest();write(capture_path,capture)
            manifest_path=root/PREFIX/'source-manifest.json';manifest=read_json(manifest_path)
            original=next(r for r in manifest['artifacts'] if r['path']=='source-witnesses.json')
            original.update(sha256=role['sha256'],bytes=len(raw));write(manifest_path,manifest)
            self.reindex(root)
            with self.assertRaisesRegex(ParityError,'independently fixed'):load(root)

    def test004_real_but_unrelated_span_cannot_prove_a_clause(self):
        self.mutate('source-proof.json',lambda d:d['clauses'][6].update(witness_refs=['keras:keras/src/backend/tensorflow/core.py:140-162']))

    def test005_typed_source_reference_case_and_clause_selectors(self):
        for name,collection,key in [('joins.json','records','source_entry'),('joins.json','records','reference_entry'),('joins.json','cases','source_entry'),('source-proof.json','clauses','source_entry')]:
            for bad in [False,0.0,-1,999999]:
                with self.subTest(name=name,collection=collection,bad=bad):
                    self.mutate(name,lambda d,c=collection,k=key,b=bad:d[c][0][k].__setitem__(1,b),'source selector|TF conversion')

    def test005_full_mapping_owner_revision_and_signature_drift_reject(self):
        def owner(d):
            r=next(r for r in d['records'] if r['symbol']=='tf.cast');r['canonical_API_mapping']['mapping'].update(owner='atlas',revision='f'*40)
        self.mutate('joins.json',owner)
        self.mutate('captured/inputs/existing-api-identities.json',lambda d:next(r for r in d['records'] if r['admitted_record']['symbol']=='tf.convert_to_tensor')['admitted_record'].update(signature="args=['value']"))

    def test_malformed_join_and_source_rows_fail_with_schema_diagnostics(self):
        for name,fn in [('joins.json',lambda d:d['records'].__setitem__(0,False)),
            ('joins.json',lambda d:d['cases'].__setitem__(0,0)),
            ('source-proof.json',lambda d:d['clauses'].__setitem__(0,None)),
            ('joins.json',lambda d:d['records'][0].update(canonical_API_mapping=[])),
            ('joins.json',lambda d:next(r for r in d['records'] if r['symbol']=='tf.cast')['canonical_API_mapping']['mapping'].update(source_contract=[]))]:
            with self.subTest(name=name,fn=fn):self.mutate(name,fn)

    def test005_live_capability_and_plan_DAG_co_mutation_rejects(self):
        b=self.bundle;caps=copy.deepcopy(b['capabilities']);caps['TEN-CORE']['prerequisites']=[]
        with self.copied() as root:
            p=root/PREFIX/'plan.json';plan=read_json(p);by(plan['existing_capability_dag'],'TEN-CORE')['prerequisites']=[];write(p,plan);self.reindex(root)
            prepared=prepare_tf_conversion(root,PREFIX+'index.json',b['program'])
            with self.assertRaisesRegex(ParityError,'owner/prerequisite'):
                validate_tf_conversion(prepared,b['program'],caps,b['repositories'],b['packages'],b['references'],b['mappings'],b['assigned'])

    def test006_credit_identity_error_shape_plan_and_gap_guards(self):
        mutations=[('index.json',lambda d:d['status'].update(framework_execution_credit=True)),
            ('index.json',lambda d:d['counts'].update(runtime_cases_executed=False)),
            ('index.json',lambda d:d.update(introduced_in_program='2026-10-26.11')),
            ('cases.json',lambda d:d['records'][0]['expected'].update(same_object=1)),
            ('cases.json',lambda d:by(d['records'],'TF-CVT-02-HARD-TENSOR-MISMATCH')['expected'].update(error='OverflowError')),
            ('cases.json',lambda d:by(d['records'],'TF-CVT-11-NOTIMPLEMENTED-SKIP')['expected'].update(first_call_dtype_sequence=['int64',None])),
            ('cases.json',lambda d:by(d['records'],'TF-CVT-15-SHAPE-CLASSES')['expected'].update(results=[])),
            ('cases.json',lambda d:d['records'][0].update(status='passed',framework_execution=True)),
            ('joins.json',lambda d:d['records'][0].update(workspace_kernel_implementation_owner='hephaestus')),
            ('plan.json',lambda d:d.update(state='execution_ready',actual_implementation_owner='coeus')),
            ('plan.json',lambda d:d['effort']['first_primal_cpu_implementation'].update(depends_on=[],low=0,high=0)),
            ('captured/remaining-gaps.json',lambda d:d.update(records=[],whole_api_complete=True))]
        for name,fn in mutations:
            with self.subTest(name=name,fn=fn):self.mutate(name,fn)

    def numeric_edit(self,root,key,left,expected):
        p=root/PREFIX/'cases.json';d=read_json(p);row=by(d['records'],key)
        if key=='TF-CVT-18-SAFE-ALL-ADD':row['input']['x']['values']=[left];out=row['expected']['all']
        else:row['input']['x_python_int_variants']=[left,2147483648];out=row['expected']['small']
        row['input']['y']['values']=[-16777216];out['values']=[expected];write(p,d);self.reindex(root)

    def test007_strong_and_weak_wrong_rational_cancellation_reject(self):
        for key in ['TF-CVT-18-SAFE-ALL-ADD','TF-CVT-19-WEAK-SCALAR-RANGE']:
            with self.subTest(key=key),self.copied() as root:
                self.numeric_edit(root,key,16777217,1)
                with self.assertRaisesRegex(ParityError,'analytical'):load(root)

    def test007_correct_changed_rounding_controls_pass_the_full_loader(self):
        for key,left,value in [('TF-CVT-18-SAFE-ALL-ADD',16777217,0),('TF-CVT-19-WEAK-SCALAR-RANGE',16777217,0),('TF-CVT-18-SAFE-ALL-ADD',16777219,4)]:
            with self.subTest(key=key,left=left),self.copied() as root:
                self.numeric_edit(root,key,left,value);self.assertEqual(load(root)['tensorflow_conversion_boundary']['runtime_cases_executed'],0)

    def vjp_edit(self,d,valid):
        maximum=int(struct.unpack('>f',bytes.fromhex('7f7fffff'))[0]);weight=maximum//2 if valid else maximum
        r=by(d['records'],'TF-CVT-09-PROTOCOL-AD');r['input']['value']['payload']['values']=[0,0,0];r['input']['loss_weights']=[weight,0,0]
        r['expected'].update(values=[0,0,0],loss=0,payload_vjp={'dtype':'float32','shape':[3],'values':[2*weight,0,0]})

    def test008_impossible_finite_cotangent_rejects(self):
        self.mutate('cases.json',lambda d:self.vjp_edit(d,False),'finite target overflow')

    def test008_valid_finite_cotangent_boundary_passes(self):
        with self.copied() as root:
            p=root/PREFIX/'cases.json';d=read_json(p);self.vjp_edit(d,True);write(p,d);self.reindex(root)
            self.assertEqual(load(root)['tensorflow_conversion_boundary']['runtime_cases_executed'],0)

    def test_valid_changed_identity_and_reformat_controls_remain_editable(self):
        with self.copied() as root:
            p=root/PREFIX/'cases.json';d=read_json(p);r=d['records'][0];r['input']['value']['values']=[2,-2,3.5];r['expected'].update(values=[2,-2,3.5],loss=0.5);p.write_text(json.dumps(d,indent=2)+'\n')
            p=root/PREFIX/'captured/source-receipts.json';p.write_text(json.dumps(read_json(p),indent=2)+'\n');self.reindex(root)
            self.assertEqual(load(root)['tensorflow_conversion_boundary']['runtime_cases_executed'],0)

    def test_cache_free_copy_reads_no_research_runtime_or_original_packet(self):
        with self.copied() as root:
            script="""import sys\nfrom pathlib import Path\nfrom atlas_parity import load\ndef guard(event,args):\n if event=='open' and isinstance(args[0],str):\n  p=args[0]\n  if '/research/' in p or 'atlas-parity-tf-closure' in p or 'tf-conversion-source-reviewed' in p: raise AssertionError('external source cache read')\nsys.addaudithook(guard)\nb=load(Path(sys.argv[1]));assert b['tensorflow_conversion_boundary']['future_cases_UNRUN']==30\n"""
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(REPO/'scripts'))
            result=subprocess.run([sys.executable,'-B','-c',script,str(root)],env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_rounding_helpers_remain_mathematical_not_runtime_evidence(self):
        self.assertEqual(round_target(Fraction(16777217),'float32'),16777216)
        self.assertEqual(round_target(Fraction(16777219),'float32'),16777220)
        self.assertEqual(round_target(Fraction(3,2**150),'float32'),Fraction(1,2**148))
        with self.assertRaisesRegex(ParityError,'overflow'):round_target(Fraction(2**128),'float32')


if __name__=='__main__':unittest.main()
