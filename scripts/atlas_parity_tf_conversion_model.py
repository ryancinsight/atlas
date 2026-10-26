"""Typed source-contract projections and input-sensitive analytical oracles.

This executes only stdlib code written for the proposal. It neither imports nor
executes TensorFlow/Keras/NumPy source. Frozen ASTs are inspected as syntax.
"""
import copy
from fractions import Fraction
import itertools
import math
import struct

from atlas_parity_schema import need, source_entry_at

def exact(a, b):
    if type(a) is not type(b): return False
    if type(a) is dict: return a.keys() == b.keys() and all(exact(a[k], b[k]) for k in a)
    if type(a) is list: return len(a) == len(b) and all(exact(x, y) for x, y in zip(a, b))
    if type(a) is float: return struct.pack(">d", a) == struct.pack(">d", b)
    return a == b

FORMATS={'float16':'e','float32':'f','float64':'d'}
FORMAT_DOMAINS={'float16':(11,-14,15),'float32':(24,-126,127),'float64':(53,-1022,1023)}
def power2(exponent):
    return Fraction(1<<exponent) if exponent>=0 else Fraction(1,1<<(-exponent))
def round_target(value,dtype):
    """Exact rational -> binary finite value, round-nearest/ties-even.

    This is an analytical oracle, not observed TensorFlow execution. The selected
    finite model refuses nonfinite overflow; it does not assert a TF exception
    or remove eventual nonfinite/backend obligations.
    """
    value=Fraction(value);precision,emin,emax=FORMAT_DOMAINS[dtype]
    if not value:return Fraction(0)
    sign=-1 if value<0 else 1;positive=abs(value)
    exponent=positive.numerator.bit_length()-positive.denominator.bit_length()
    if positive<power2(exponent):exponent-=1
    quantum=power2(max(exponent,emin)-(precision-1))
    scaled=positive/quantum;integer,remainder=divmod(scaled.numerator,scaled.denominator)
    twice=2*remainder
    if twice>scaled.denominator or (twice==scaled.denominator and integer%2):integer+=1
    represented=integer*quantum
    maximum=(2**precision-1)*power2(emax-(precision-1))
    need(represented<=maximum,'analytical finite target overflow; nonfinite/native behavior remains an open obligation')
    return sign*represented

def target_add(left,right,dtype):
    """Model the source order: each target conversion, then target addition."""
    return round_target(round_target(left,dtype)+round_target(right,dtype),dtype)

def fraction(x,dtype=None):
    need(type(x) in (int,float) and math.isfinite(x),'exact finite real input, excluding bool')
    need(not(type(x) is float and x==0 and math.copysign(1,x)<0),'signed-negative-zero fixture semantics remain open; no public API exclusion or runtime error is inferred')
    if dtype in {'int32','int64'}:
        bits=int(dtype[3:]);need(type(x) is int and -(2**(bits-1))<=x<2**(bits-1),'integer input range/type')
    value=Fraction(x)
    if dtype in FORMATS:
        need(round_target(value,dtype)==value,'selected native input/output/cotangent must be exactly represented in its stated format')
    return value
def number(x):
    x=Fraction(x)
    if x.denominator==1:return x.numerator
    f=float(x);need(math.isfinite(f) and Fraction(f)==x,'analytical value not exactly binary64 representable');return f
def get(tree, path):
    return source_entry_at(tree, list(path), "TF conversion analytical selector")
def set_value(tree,path,value):
    get(tree,path[:-1])[path[-1]]=value
def numeric_shape(value,prototype,dtype):
    if type(prototype) is list:
        need(type(value) is list and len(value)==len(prototype),'complete analytical list/matrix shape')
        for x,y in zip(value,prototype):numeric_shape(x,y,dtype)
    else:fraction(value,dtype)

# Only these numerical leaves vary. All branch/type/mode/shape/axis/metadata fields
# are exact typed contracts, rather than ignored free-form JSON.
MUTABLE={
 'TF-CVT-01-IDENTITY':[(('value','values'),'float32'),(('loss_weights',),'float32')],
 'TF-CVT-09-PROTOCOL-AD':[(('value','payload','values'),'float32'),(('loss_weights',),'float32')],
 'TF-CVT-14-NUMPY-SNAPSHOT':[(('value','base_values'),'float32')],
 'TF-CVT-15-SHAPE-CLASSES':[(('variants',0,'value'),'int64'),(('variants',1,'value'),'int64')],
 'TF-CVT-16-NESTED-SHAPE':[(('value','values'),'float64')],
 'TF-CVT-18-SAFE-ALL-ADD':[(('x','values'),'int32'),(('y','values'),'float32')],
 'TF-CVT-19-WEAK-SCALAR-RANGE':[(('x_python_int_variants',),None),(('y','values'),'float32')],
 'TF-CVT-20-LEGACY-OPERATOR':[(('x','values'),'int32'),(('y','values'),'float32')],
 'TF-CVT-22-CONVERSION-THEN-CAST-AD':[(('x','values'),'float32'),(('loss_weights',),'float32')],
 'TF-CVT-23-KERAS-POLICY':[(('x_float','values'),'float16'),(('x_integer','values'),'int32')],
 'TF-CVT-24-KERAS-BACKEND-CONTRAST':[(('value_python_float',),'float32')],
}

def input_contract(case,prototype):
    value=case['input'];expected=copy.deepcopy(prototype['input'])
    for path,dtype in MUTABLE.get(case['id'],[]):
        actual=get(value,path);old=get(expected,path);numeric_shape(actual,old,dtype);set_value(expected,path,copy.deepcopy(actual))
    need(exact(value,expected),'input branch/type/schema changed: '+case['id'])
    if case['id']=='TF-CVT-19-WEAK-SCALAR-RANGE':
        small,large=value['x_python_int_variants']
        need(type(small) is int and type(large) is int,'Python int classifier excludes bool/float')
        need(-(2**31)<=small<2**31 and not -(2**31)<=large<2**31,'weak scalar small/overflow class')
    if case['id']=='TF-CVT-24-KERAS-BACKEND-CONTRAST':
        x=value['value_python_float'];need(type(x) is float and -(2**31)<=x<2**31,'selected Python float versus integer conversion class')

def dot(xs,weights,dtype):
    need(len(xs)==len(weights)>0,'complete cotangent/data lengths')
    terms=[Fraction(x)*Fraction(w) for x,w in zip(xs,weights)]
    # Every reduction order in this finite analytical subdomain is exact. This is
    # a fixture-domain guard, not a claim about arbitrary floating reductions.
    for count in range(1,len(terms)+1):
        for subset in itertools.combinations(terms,count):fraction(number(sum(subset)),dtype)
    return number(sum(terms))

def expected_case(case,prototype):
    input_contract(case,prototype)
    out=copy.deepcopy(prototype['expected']);i=case['input'];cid=case['id']
    if cid=='TF-CVT-01-IDENTITY':
        x=i['value'];w=i['loss_weights'];out.update(values=x['values'],loss=dot(x['values'],w,x['dtype']),vjp={'dtype':x['dtype'],'shape':x['shape'],'values':w})
    elif cid=='TF-CVT-04-DIRECT-VS-CAST':
        x=float.fromhex(i['python_float_binary64_hex']);y=struct.unpack('>f',struct.pack('>f',x))[0]
        need(x!=y,'precision-order witness must distinguish the routes');out.update(direct_hex=x.hex(),cast_hex=y.hex())
    elif cid=='TF-CVT-09-PROTOCOL-AD':
        x=i['value']['payload'];w=i['loss_weights'];y=[number(2*Fraction(v)) for v in x['values']]
        for v in y:fraction(v,x['dtype'])
        vjp=[number(2*Fraction(v)) for v in w]
        for v in vjp:fraction(v,x['dtype'])
        out.update(values=y,loss=dot(y,w,x['dtype']),payload_vjp={'dtype':x['dtype'],'shape':x['shape'],'values':vjp})
    elif cid=='TF-CVT-14-NUMPY-SNAPSHOT':
        x=i['value'];y=[row[::2] for row in x['base_values']];out.update(values_after_host_write=y,shape=[len(y),len(y[0])])
        need(exact(x['byte_strides'],[x['base_shape'][1]*4,8]),'ndarray host byte-stride calculation')
    elif cid=='TF-CVT-15-SHAPE-CLASSES':
        out['results']=[]
        for item in i['variants']:
            value=item['value'];shape=[len(value)] if type(value) is list else []
            out['results'].append({'shape':shape,'rank':len(shape),'values':value if type(value) is list else [value]})
    elif cid=='TF-CVT-16-NESTED-SHAPE':
        x=i['value']['values'];out.update(values=x,shape=[len(x),len(x[0])])
    elif cid in {'TF-CVT-18-SAFE-ALL-ADD','TF-CVT-20-LEGACY-OPERATOR'}:
        field='all' if cid=='TF-CVT-18-SAFE-ALL-ADD' else 'operator'
        if field=='all':value=number(target_add(Fraction(i['x']['values'][0]),Fraction(i['y']['values'][0]),'float32'))
        else:value=number(Fraction(i['x']['values'][0])+Fraction(i['y']['values'][0]));fraction(value,'float64')
        out[field]['values']=[value]
    elif cid=='TF-CVT-19-WEAK-SCALAR-RANGE':
        value=number(target_add(Fraction(i['x_python_int_variants'][0]),Fraction(i['y']['values'][0]),'float32'));out['small']['values']=[value]
    elif cid=='TF-CVT-22-CONVERSION-THEN-CAST-AD':
        x=i['x'];w=i['loss_weights'];out.update(loss=dot(x['values'],w,'float64'),x_vjp={'dtype':x['dtype'],'shape':x['shape'],'values':w})
    elif cid=='TF-CVT-23-KERAS-POLICY':out['float_autocast_true']['values']=i['x_float']['values']
    elif cid=='TF-CVT-24-KERAS-BACKEND-CONTRAST':out['keras_helper']['values']=[math.trunc(i['value_python_float'])]
    elif cid=='TF-CVT-26-HINTED-NONE':
        # None reaches a .dtype property load in the normal try-else, not the
        # converter exception handler. This is a protocol conformance design.
        out={'converter_calls':1,'error':'AttributeError','phase':'hint try-else ret.dtype access','later_converter_calls':0,'unhinted_retry':False}
    elif cid=='TF-CVT-27-UNHINTED-NONE':
        out={'converter_calls':1,'error':'RuntimeError','phase':'accepted_result_types','later_converter_calls':0,'unhinted_retry':False}
    elif cid=='TF-CVT-28-REGISTER-COMPLEX':
        need(not issubclass(complex,(int,float)),'Python complex type relation')
        out={'public_builtin_ban':False,'registration_type_callable_checks_accept':True,'default_matching_constant_conversion_priority_without_custom_registration':200,'new_custom_registration_priority':i['priority'],'conversion_runtime_result':'unrun and unresolved'}
    elif cid=='TF-CVT-29-REGISTER-TYPE-BOUNDARY':
        need(issubclass(bool,int),'Python bool subclass relation')
    elif cid=='TF-CVT-30-CAPTURE-DELEGATION':
        out={'source_call_expression':'graph.capture(self, name=name)','dtype_forwarded':False,'superclass_branch_invoked':False,'runtime_success_error_alias_dtype_result':'unresolved; capture own validation is not closed'}
    return out

def project_case(case,prototype):
    need(type(case) is dict and case.keys()==prototype.keys(),'complete exact acceptance case schema')
    output=copy.deepcopy(prototype);output['input']=copy.deepcopy(case['input']);output['expected']=expected_case(case,prototype)
    return output
