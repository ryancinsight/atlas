"""Exact analytical fixtures from the independently reviewed workflow audit.

No framework import or runtime parity credit. Assertions require normal Python.
"""
import copy
from fractions import Fraction as F

SUPPORTED_FIXTURES = {'FX-ARRAY','FX-SCATTER','FX-AD','FX-TRAIN','FX-COMPLEX','FX-INFER','FX-SOLVE',
                      'FX-DFT','FX-DIST','FX-DATA','FX-EXPORT-SIGNATURES','FX-COUNTER','FX-AWQ','FX-ASYNC'}

def fixture_domains(fx):
 """These named witnesses have declared dimensions; reject ignored trailing inputs."""
 assert set(fx)==SUPPORTED_FIXTURES, 'fixture has no registered mathematical truth check'
 def vec(x,n):
  assert type(x) is list and len(x)==n,('fixture vector dimension',n)
  for value in x:
   assert type(value) in (int,float,str),('fixture numeric scalar',type(value).__name__)
   F(value)
 def mat(x,m,n):
  assert type(x) is list and len(x)==m,('fixture matrix rows',m)
  for row in x:vec(row,n)
 a=fx['FX-ARRAY'];mat(a['input'],2,3);vec(a['column_offset'],3)
 for name in ['broadcast_sum','reverse_last_axis']:mat(a[name],2,3)
 for name in ['row_sum','row_mean']:vec(a[name],2)
 s=fx['FX-SCATTER'];vec(s['initial'],5);vec(s['add_result'],5);vec(s['indices'],3);vec(s['values'],3)
 assert all(type(i) is int and 0<=i<5 for i in s['indices']), 'scatter index domain'
 a=fx['FX-AD'];mat(a['A'],2,2);mat(a['H'],2,2)
 for name in ['b','x','v','Hv']:vec(a[name],2)
 for state in [a['truth'],fx['FX-TRAIN']['step0'],fx['FX-TRAIN']['step1']]:
  for name in ['x','residual','gradient']:vec(state[name],2)
 vec(fx['FX-TRAIN']['x_after_step2'],2)
 c=fx['FX-COMPLEX'];vec(c['z'],2);vec(c['real_coordinate_gradient'],2)
 for value in c['complex_encodings'].values():vec(value,2)
 a=fx['FX-INFER'];mat(a['X'],2,2);mat(a['W'],2,2);mat(a['Y'],2,2);vec(a['b'],2)
 a=fx['FX-SOLVE'];mat(a['M'],2,2)
 for name in ['b','x','residual']:vec(a[name],2)
 a=fx['FX-DFT'];vec(a['input'],4);mat(a['forward_unscaled_output_real_imag'],4,2)
 a=fx['FX-DIST'];mat(a['gradient_contributions'],2,2);mat(a['row_shards'],2,1)
 assert all(type(i) is int and 0<=i<2 for row in a['row_shards'] for i in row), 'row shard domain'
 for name in ['sum','mean']:vec(a[name],2)
 a=fx['FX-DATA'];vec(a['records'],8);mat(a['explicit_even_odd_partition'],2,4)
 a=fx['FX-EXPORT-SIGNATURES'];mat(a['W'],2,2);vec(a['b'],2)
 assert len(a['batches'])==3, 'declared export batch witnesses'
 for batch,rows in zip(a['batches'],[1,2,3]):
  vec(batch['shape'],2);mat(batch['X'],rows,2);mat(batch['Y'],rows,2)
 a=fx['FX-COUNTER'];vec(a['input'],2);assert len(a['calls'])==3,'three repeated counter calls'
 for call in a['calls']:vec(call['output'],2)
 a=fx['FX-AWQ'];vec(a['explicit_scales'],2);vec(a['per_channel_max_abs'],2)
 for name in ['calibration_X','W','scaled_W','scaled_X','unquantized_Y']:mat(a[name],2,2)
 a=fx['FX-ASYNC'];vec(a['initial_x'],2);vec(a['worker_read_versions'],2)
 for name in ['worker_gradients','parameters_after_commits']:mat(a[name],2,2)
 assert len(a['commit_order'])==2,'two asynchronous commits'

def verify_fixture_truth(fx):
 fixture_domains(fx)
 def eq(a,b,label):assert a==b,(label,a,b)
 def qs(xs):return [F(x) for x in xs]
 def qm(xs):return [qs(row) for row in xs]
 a=fx['FX-ARRAY'];eq([sum(row) for row in a['input']],a['row_sum'],'FX-ARRAY.row_sum');eq([F(sum(row),len(row)) for row in a['input']],qs(a['row_mean']),'FX-ARRAY.row_mean');eq([list(reversed(row)) for row in a['input']],a['reverse_last_axis'],'FX-ARRAY.reverse');eq([[q+b for q,b in zip(row,a['column_offset'])] for row in a['input']],a['broadcast_sum'],'FX-ARRAY.broadcast')
 s=fx['FX-SCATTER'];out=s['initial'].copy()
 for i,v in zip(s['indices'],s['values']):out[i]+=v
 eq(out,s['add_result'],'FX-SCATTER.add')
 q=fx['FX-AD'];A=qm(q['A']);b=qs(q['b']);x=qs(q['x']);v=qs(q['v']);eq(A,[[F(1),F(2)],[F(-1),F(3)]],'FX-AD.A');eq(b,[F(1),F(-2)],'FX-AD.b')
 # Independently expanded polynomial, rather than the generator's A^T residual body.
 def truth(z):
  u,w=z;return {'x':z,'residual':[u+2*w-1,-u+3*w+2],'loss':u*u-u*w+F(13,2)*w*w-3*u+4*w+F(5,2),'gradient':[2*u-w-3,-u+13*w+4]}
 def state_eq(actual,z,label):
  expected=truth(z)
  for key in ['x','residual','gradient']:eq(qs(actual[key]),expected[key],label+'.'+key)
  eq(F(actual['loss']),expected['loss'],label+'.loss')
 state_eq(q['truth'],x,'FX-AD.truth');g=truth(x)['gradient'];H=[[F(2),F(-1)],[F(-1),F(13)]];eq(qm(q['H']),H,'FX-AD.H');eq(qs(q['Hv']),[2*v[0]-v[1],-v[0]+13*v[1]],'FX-AD.Hv');eq(F(q['JVP']),g[0]*v[0]+g[1]*v[1],'FX-AD.JVP')
 tr=fx['FX-TRAIN'];lr=F(tr['learning_rate']);state_eq(tr['step0'],x,'FX-TRAIN.step0');x1=[p-lr*d for p,d in zip(x,g)];state_eq(tr['step1'],x1,'FX-TRAIN.step1');eq(qs(tr['x_after_step2']),[p-lr*d for p,d in zip(x1,truth(x1)['gradient'])],'FX-TRAIN.step2')
 c=fx['FX-COMPLEX'];ar,ai=c['z'];eq(c['value'],ar*ar+ai*ai,'FX-COMPLEX.value');eq(c['real_coordinate_gradient'],[2*ar,2*ai],'FX-COMPLEX.real_gradient');eq(c['complex_encodings'],{'conjugate_style':[2*ar,2*ai],'nonconjugate_style':[2*ar,-2*ai]},'FX-COMPLEX.encodings')
 def affine(X,W,bias):return [[sum(row[i]*W[i][j] for i in range(len(W)))+bias[j] for j in range(len(bias))] for row in X]
 inf=fx['FX-INFER'];eq(inf['Y'],affine(inf['X'],inf['W'],inf['b']),'FX-INFER.Y')
 sol=fx['FX-SOLVE'];M=sol['M'];rhs=sol['b'];det=M[0][0]*M[1][1]-M[0][1]*M[1][0];assert det>0 and M[0][0]>0 and M[0][1]==M[1][0];expected=[F(rhs[0]*M[1][1]-M[0][1]*rhs[1],det),F(M[0][0]*rhs[1]-rhs[0]*M[1][0],det)];eq(qs(sol['x']),expected,'FX-SOLVE.x');eq(sol['residual'],[sum(a*b for a,b in zip(row,sol['x']))-y for row,y in zip(M,rhs)],'FX-SOLVE.residual')
 d=fx['FX-DFT'];a0,a1,a2,a3=d['input'];eq(d['forward_unscaled_output_real_imag'],[[a0+a1+a2+a3,0],[a0-a2,-a1+a3],[a0-a1+a2-a3,0],[a0-a2,a1-a3]],'FX-DFT.bins')
 di=fx['FX-DIST'];eq(sorted(sum(di['row_shards'],[])),list(range(len(A))),'FX-DIST.partition');per_rank=[]
 for shard in di['row_shards']:
  partial=[F(0),F(0)]
  for i in shard:
   residual=sum(A[i][j]*x[j] for j in range(2))-b[i]
   partial=[partial[j]+A[i][j]*residual for j in range(2)]
  per_rank.append(partial)
 eq(qm(di['gradient_contributions']),per_rank,'FX-DIST.per-rank');eq(qs(di['sum']),[sum(z) for z in zip(*per_rank)],'FX-DIST.sum');eq(qs(di['mean']),[sum(z)/len(per_rank) for z in zip(*per_rank)],'FX-DIST.mean')
 dat=fx['FX-DATA'];eq(dat['records'],list(range(8)),'FX-DATA.records');eq(dat['explicit_even_odd_partition'],[[z for z in dat['records'] if z%2==0],[z for z in dat['records'] if z%2==1]],'FX-DATA.parity-order-multiplicity')
 ex=fx['FX-EXPORT-SIGNATURES'];eq({row['shape'][0] for row in ex['batches']},{1,2,3},'FX-EXPORT.batchclasses')
 for row in ex['batches']:
  eq(row['shape'],[len(row['X']),len(ex['W'])],'FX-EXPORT.shape');eq(row['Y'],affine(row['X'],ex['W'],ex['b']),'FX-EXPORT.Y')
 co=fx['FX-COUNTER'];count=co['initial_counter']
 for call in co['calls']:
  count+=1;eq(call['counter'],count,'FX-COUNTER.state');eq(call['output'],[z+count for z in co['input']],'FX-COUNTER.output')
 eq(co['reload_after_call'],2,'FX-COUNTER.reload_boundary')
 aw=fx['FX-AWQ'];X=qm(aw['calibration_X']);W=qm(aw['W']);sc=qs(aw['explicit_scales']);assert all(z>0 for z in sc)
 eq(aw['per_channel_max_abs'],[max(abs(row[j]) for row in X) for j in range(len(sc))],'FX-AWQ.channel_max');eq(qm(aw['scaled_W']),[[W[i][j]*sc[i] for j in range(len(W[0]))] for i in range(len(W))],'FX-AWQ.scaled_W');eq(qm(aw['scaled_X']),[[row[i]/sc[i] for i in range(len(sc))] for row in X],'FX-AWQ.scaled_X');Y=affine(X,W,[F(0)]*len(W[0]));eq(qm(aw['unquantized_Y']),Y,'FX-AWQ.Y');eq(affine(qm(aw['scaled_X']),qm(aw['scaled_W']),[F(0)]*len(W[0])),Y,'FX-AWQ.scale_identity')
 ah=fx['FX-ASYNC'];eq(qs(ah['initial_x']),x,'FX-ASYNC.initial');eq(ah['worker_read_versions'],[0,0],'FX-ASYNC.reads');eq(qm(ah['worker_gradients']),[g,g],'FX-ASYNC.workergradients');eq(ah['commit_order'],['worker0','worker1'],'FX-ASYNC.order');z=x.copy();states=[]
 for worker in ah['commit_order']:
  gradient=qs(ah['worker_gradients'][int(worker[-1])]);z=[p-F(ah['learning_rate'])*d for p,d in zip(z,gradient)];states.append(z)
 eq(qm(ah['parameters_after_commits']),states,'FX-ASYNC.commitstates')

def negative_fixture_checks(fixtures):
 probes=[('unchecked_row_mean',lambda f:f['FX-ARRAY']['row_mean'].__setitem__(0,123)),('unchecked_residual',lambda f:f['FX-AD']['truth']['residual'].__setitem__(0,'100')),('unchecked_training_residual',lambda f:f['FX-TRAIN']['step1']['residual'].__setitem__(0,'100')),('unchecked_complex_encoding',lambda f:f['FX-COMPLEX']['complex_encodings'].__setitem__('conjugate_style',[9,9])),('compensating_wrong_rank_contributions',lambda f:(f['FX-DIST']['gradient_contributions'][0].__setitem__(0,'-2'),f['FX-DIST']['gradient_contributions'][1].__setitem__(0,'4'))),('wrong_parity_same_flat_set',lambda f:f['FX-DATA'].__setitem__('explicit_even_odd_partition',[[1,2,4,6],[0,3,5,7]])),('wrong_awq_channel_max',lambda f:f['FX-AWQ']['per_channel_max_abs'].__setitem__(0,0)),('wrong_awq_scaled_weights',lambda f:f['FX-AWQ']['scaled_W'][0].__setitem__(0,'99')),('wrong_export_batch_output',lambda f:f['FX-EXPORT-SIGNATURES']['batches'][2]['Y'][0].__setitem__(0,99)),('wrong_export_shape',lambda f:f['FX-EXPORT-SIGNATURES']['batches'][2]['shape'].__setitem__(0,1)),('frozen_export_counter',lambda f:f['FX-COUNTER']['calls'][1].__setitem__('counter',1)),('wrong_stale_worker_gradient',lambda f:f['FX-ASYNC']['worker_gradients'][1].__setitem__(0,'-2'))]
 results=[]
 for name,mutate in probes:
  altered=copy.deepcopy(fixtures);mutate(altered)
  try:verify_fixture_truth(altered)
  except AssertionError as e:results.append({'probe':name,'incorrect_fixture_rejected':True,'numerical_assertion':str(e.args[0][0] if isinstance(e.args[0],tuple) else e.args[0]),'runtime_parity_credit':0})
  else:raise AssertionError(('incorrect numerical fixture accepted',name))
 return results
