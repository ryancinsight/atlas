"""Per-object workflow rows; shared templates never merge semantic identities."""
from ufunc_sources import C, DOC, cite, find_line, text
import re

def parser_schemas():
    source = text(C)
    result = {}
    for name in ['reduce', 'accumulate', 'reduceat', 'resolve_dtypes', '_get_strided_loop']:
        match = re.search('npy_parse_arguments\\("' + name + '".*?\\)\\s*<\\s*0', source, re.S)
        if match:
            result[name] = {'raw_parameter_markers': re.findall('\\{"([^"\\n]*)"\\s*,', match.group()), 'source': cite(C, source[:match.start()].count('\n') + 1), 'status': 'literal-manual-parser-schema;not-assumed-equivalent-to-published-inspect-signature'}
    return result

def templates():
    doc = 'doc/source/reference/ufuncs.rst'
    common = {'definition_status': 'partial-source-workflow;not-full-dtype-device-layout-AD-contract', 'verification': {'implemented': False, 'tested': False, 'differentially_verified': False, 'performance_qualified': False}, 'remaining_axes': ['per-DType/loop casts/promotion/accumulation/error bounds', 'shape/stride/overlap/empty/rank0/alias and mutability cases', 'override/effect/error-order and subclass protocols', 'native CPU/ISA/ABI and Atlas device/provider coverage', 'operation-specific gradient/transform behavior and mutation policy', 'benchmarks and exact-version differential evidence'], 'ad_policy': 'Native NumPy has no AD implementation. Do not infer one universal derivative. Delegated __array_ufunc__ outputs/object arithmetic may carry their own graphs and cannot be detached or universally classified nondifferentiable.'}
    specs = {'__call__': {'workflow': 'scalar-broadcast-or-generalized-core-call', 'sources': [cite(C, find_line(C, 'ufunc_generic_fastcall(')), cite(doc, find_line(doc, 'Optional keyword arguments'))], 'obligations': ['Distinguish scalar-ufunc broadcasting from each gufunc core signature, optional core dimensions and axes/axis/keepdims admissibility.', 'Preserve nin/nout, multiple outputs, scalar return versus out=Ellipsis, positional/keyword outputs and input/output overlap behavior.', 'where false with provided out retains that region; where false with newly allocated out leaves it uninitialized. Verify only source-defined values and preservation/alias effects, never fabricate numerical equality of uninitialized bytes.', 'Retain casting/order/dtype/signature/subok and sig backward-compatible spelling. Gufunc where/axis/keepdims restrictions remain per-core signature, not global flags.', 'Convenience inspect.Signature is not the full native parser schema, especially multiple positional output slots.']}, 'reduce': {'workflow': 'fold-with-identity-initial-mask-and-axes', 'sources': [cite(C, find_line(C, 'PyUFunc_GenericReduction(')), cite(DOC, find_line(DOC, '    reduce($self'))], 'obligations': ['Require scalar binary single-output ufunc before parser/override; retain the precise first failure for gufunc/nin/nout.', 'Distinguish axis=None/scalar/tuple/empty tuple, keepdims, initial and where; preserve order/reorderability and non-associative semantics.', 'Default ufunc.identity metadata is not a complete selected-DType reduction identity. Empty/all-masked reductions, accumulator dtype and custom ArrayMethod initial slots need separate contracts.', 'Manual parser markers and published positional-only/inspect signature can differ; retain both.']}, 'accumulate': {'workflow': 'ordered-prefix-scan', 'sources': [cite(C, find_line(C, 'PyUFunc_GenericReduction(')), cite(DOC, find_line(DOC, '    accumulate($self'))], 'obligations': ['Same initial scalar/binary/single-output descriptor guards as reduce.', "Native path rejects rank0 TypeError and naxes!=1 ValueError after input/axis processing; do not reuse reduce's multi-axis/initial/where API.", 'Preserve ordered prefix values, output and dtype/accumulator/empty behavior per ufunc.']}, 'reduceat': {'workflow': 'indexed-segment-reduction', 'sources': [cite(C, find_line(C, 'PyUFunc_GenericReduction(')), cite(DOC, find_line(DOC, '    reduceat($self'))], 'obligations': ['Same descriptor guards; native path rejects scalar input and non-single-axis requests.', 'Indices are converted to a1-D intp array. Retain interval/end rules, the single-element result for nonincreasing consecutive indices, bounds errors, output-axis length and casts.', 'Do not model reduceat as a generic reduction over disjoint sorted segments; unsorted/repeated indices are semantically significant.']}, 'outer': {'workflow': 'pairwise-binary-outer-with-possibly-multiple-outputs', 'sources': [cite(C, find_line(C, 'ufunc_outer(PyUFuncObject')), cite(DOC, find_line(DOC, '    outer($self'))], 'obligations': ['C guard is non-gufunc then nin==2, then exactly2 positional inputs. There is NO nout==1 guard: binary multi-output outer remains a candidate, despite typing comments/NoReturn declarations.', 'Forward common ufunc keyword/output options and concatenate logical operand dimensions. Preserve output tuple arity, dtype/layout/overlap and subclass behavior.', 'Matrix inputs trigger explicit source TypeError; no old matrix-special-case compatibility behavior is assumed.']}, 'at': {'workflow': 'unbuffered-indexed-in-place-update', 'sources': [cite(C, find_line(C, 'ufunc_at(PyUFuncObject')), cite(DOC, find_line(DOC, '    at($self'))], 'obligations': ['Reject gufunc first, then nin>2, then nout!=1, before argument parsing/override. Require b for binary and reject b for unary.', 'Repeated indices accumulate unbuffered effects; add.at(a,[0,0],1) is not buffered a[[0,0]]+=1.', 'Preserve indices/slices/broadcast, writeability/casting/overlap, exact mutation and None native return; no silent copies counted as in-place parity.']}, 'resolve_dtypes': {'workflow': 'dtype-only-NEP50-resolution', 'sources': [cite(C, find_line(C, 'py_resolve_dtypes_generic(')), cite(DOC, find_line(DOC, '    resolve_dtypes($self'))], 'obligations': ['Input dtypes must be exact tuple of nargs length; preserve None and weak Python int/float/complex type roles, signature/casting and returned calculation dtypes.', 'reduction=True only checks nin2/nout1, NOT absence of gufunc core signature. Do not equate accepting dtype-resolution reduction mode with a valid actual .reduce workflow.', 'No numeric values are supplied; dtype-resolution semantics still depend on registered loops/promoters and supported DTypes.']}, '_resolve_dtypes_and_context': {'workflow': 'unstable-C-user-dtype-resolution-and-call-context', 'sources': [cite(C, find_line(C, 'py_resolve_dtypes_and_context(')), cite(DOC, find_line(DOC, '    _resolve_dtypes_and_context($self'))], 'obligations': ['PUBLIC, underscored, version-specific C-user API; retain rather than filter by underscore.', 'Shares resolve_dtypes parameter handling and reduction descriptor check; also returns versioned call-info capsule.', 'Capsule identity/lifetime/ownership/ABI and selected method/context need exact-version qualification.']}, '_get_strided_loop': {'workflow': 'unstable-C-user-strided-loop-context-selection', 'sources': [cite(C, find_line(C, 'py_get_strided_loop(')), cite(DOC, find_line(DOC, '    _get_strided_loop($self'))], 'obligations': ['PUBLIC underscored C-user API; consumes correct call-info capsule and optional fixed strides.', 'Retain capsule version/lifetime, stride contracts, selected loop pointers, Python API requirement and floating-error flags. No loop execution or ABI completeness is inferred from method presence.']}}
    return {name: {**common, **value} for name, value in specs.items()}

def structural_gate(obj, member):
    """First descriptor-only gate, not full argument/dtype validity."""
    g, ni, no = (obj['generalized'], obj['nin'], obj['nout'])
    if member in {'reduce', 'accumulate', 'reduceat'}:
        if g:
            return {'status': 'descriptor-rejected', 'first_error': 'RuntimeError', 'reason': 'reduction not defined for nontrivial gufunc signature', 'before_override': True}
        if ni != 2:
            return {'status': 'descriptor-rejected', 'first_error': 'ValueError', 'reason': 'only binary functions', 'before_override': True}
        if no != 1:
            return {'status': 'descriptor-rejected', 'first_error': 'ValueError', 'reason': 'only single-output functions', 'before_override': True}
    if member == 'outer':
        if g:
            return {'status': 'descriptor-rejected', 'first_error': 'TypeError', 'reason': 'nontrivial gufunc signature', 'before_override': True}
        if ni != 2:
            return {'status': 'descriptor-rejected', 'first_error': 'ValueError', 'reason': 'outer requires binary function', 'before_override': True}
    if member == 'at':
        if g:
            return {'status': 'descriptor-rejected', 'first_error': 'TypeError', 'reason': 'nontrivial gufunc signature', 'before_override': True}
        if ni > 2:
            return {'status': 'descriptor-rejected', 'first_error': 'ValueError', 'reason': 'only unary and binary', 'before_override': True}
        if no != 1:
            return {'status': 'descriptor-rejected', 'first_error': 'ValueError', 'reason': 'only single-output', 'before_override': True}
    if member in {'resolve_dtypes', '_resolve_dtypes_and_context'}:
        return {'status': 'descriptor-conditionally-eligible', 'reduction_false': 'no nin/nout/core descriptor rejection at this guard', 'reduction_true': 'descriptor-eligible' if ni == 2 and no == 1 else 'ValueError-nin/nout', 'gufunc_core_not_a_guard': True}
    return {'status': 'descriptor-conditionally-eligible', 'warning': 'Arity/core descriptor guard only; argument, dtype, shape, protocol and runtime admissibility remain to specify/verify.'}

def expand(objects, members, bindings):
    workflows = templates()
    object_rows, public_binding_rows = ([], [])
    for obj in objects.values():
        for member, definition in members.items():
            row = {'expansion_id': obj['object_id'] + ':member:' + member, 'object_id': obj['object_id'], 'generated_name': obj['generated_name'], 'member_id': definition['member_id'], 'member': member, 'native_presence': definition['native_kind'], 'semantic_merge': False, 'status': 'declaration-expansion-only;unmapped-semantics', 'source': obj['source']}
            if member in workflows:
                row['workflow_template'] = member
                row['descriptor_gate'] = structural_gate(obj, member)
            elif member == '__qualname__':
                row['runtime_presence_status'] = 'stub or conditional string assignment; not universally proven'
            elif member == '__module__':
                row['runtime_presence_status'] = 'conditional instance-dict metadata; no universal value inferred'
            object_rows.append(row)
    for binding in bindings:
        if not binding['public_namespace_export']:
            continue
        for member in members:
            public_binding_rows.append({'binding_expansion_id': binding['binding_id'] + ':member:' + member, 'binding_id': binding['binding_id'], 'symbol': binding['symbol'] + '.' + member, 'object_expansion_id': binding['object_id'] + ':member:' + member, 'alias_relation_not_semantic_merge': True, 'status': 'retained-spelling-specific-workflow;not-verified'})
    return (object_rows, public_binding_rows, workflows)
