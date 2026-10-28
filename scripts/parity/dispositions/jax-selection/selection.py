"""Source-derived JAX member-selection dispositions; no JAX/Sphinx import/build."""
from __future__ import annotations
import os
import ast, collections, copy, functools, hashlib, inspect, json, re, sys
from pathlib import Path
ROOT = Path(__file__).parent
JAX_CACHE = Path(os.environ['ATLAS_REFERENCE_SOURCE_CACHE'])
OLD = Path(os.environ['ATLAS_REFERENCE_PRIOR_JAX_ADDITIONS'])
REV = 'dc4af684446e65ee98eee8090e1ff6f8211473fb'
JAX_BASE = 'https://github.com/jax-ml/jax/blob/' + REV + '/'

def function(path, name, cls=None):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = tree.body
    if cls:
        nodes = next((n.body for n in nodes if isinstance(n, ast.ClassDef) and n.name == cls))
    return next((n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == name))

def fingerprint(node):
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()

def citation(path, node, version=None):
    if version:
        return f'https://github.com/sphinx-doc/sphinx/blob/v{version}/' + path + '#L' + str(node.lineno) + '-L' + str(node.end_lineno)
    return JAX_BASE + path + '#L' + str(node.lineno) + '-L' + str(node.end_lineno)

def helpers(version):
    """Execute exact pure descriptor-inspection helpers against isolated fixtures.

 No Sphinx module, JAX module or JAX function body is imported or executed.
 """
    path = ROOT / 'tooling' / version / 'sphinx/util/inspect.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    selected = {'getmro', 'ispartial', 'isclassmethod', 'safe_getattr', 'getdoc', '_getdoc_internal'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in selected]
    assert {n.name for n in nodes} == selected
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
    namespace = {'__name__': 'isolated_sphinx_descriptor_helpers', 'inspect': inspect, 'ismethod': inspect.ismethod, 'isclass': inspect.isclass, 'partial': functools.partial, 'partialmethod': functools.partialmethod}
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), namespace)
    return namespace

def metadata_fixture_classes():
    """Preserve doc/descriptor structure, never execute source computations."""
    stages = ast.parse((JAX_CACHE / 'jax/_src/stages.py').read_text(encoding='utf-8'))
    export = ast.parse((JAX_CACHE / 'jax/_src/export/_export.py').read_text(encoding='utf-8'))
    wanted = {'Stage', 'Traced', 'Lowered', 'Compiled', 'Wrapped', 'DisabledSafetyCheck'}
    defs = []
    defs.extend(ast.parse('def _traced_out_info(self):\n pass\ndef _traced_args_info(self):\n pass\n').body)

    def strip(n):
        n = copy.deepcopy(n)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            n.decorator_list = [d for d in n.decorator_list if isinstance(d, ast.Name) and d.id in {'property', 'classmethod', 'staticmethod'}]
            n.returns = None
            for a in [*n.args.posonlyargs, *n.args.args, *n.args.kwonlyargs]:
                a.annotation = None
            if n.args.vararg:
                n.args.vararg.annotation = None
            if n.args.kwarg:
                n.args.kwarg.annotation = None
            n.args.defaults = [ast.Constant(None) for x in n.args.defaults]
            n.args.kw_defaults = [None if x is None else ast.Constant(None) for x in n.args.kw_defaults]
            doc = ast.get_docstring(n, clean=False)
            n.body = ([ast.Expr(ast.Constant(doc))] if doc is not None else []) + [ast.Pass()]
        return n
    for tree in [stages, export]:
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or node.name not in wanted:
                continue
            body = []
            for child in node.body:
                if isinstance(child, ast.Expr) and isinstance(child.value, ast.Constant) and isinstance(child.value.value, str):
                    body.append(copy.deepcopy(child))
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    body.append(strip(child))
                elif isinstance(child, ast.Assign):
                    if any((isinstance(t, ast.Name) and t.id == '__slots__' for t in child.targets)):
                        body.append(copy.deepcopy(child))
                    elif isinstance(child.value, ast.Call) and isinstance(child.value.func, ast.Name) and (child.value.func.id == 'property'):
                        copy_child = copy.deepcopy(child)
                        if copy_child.value.args and isinstance(copy_child.value.args[0], ast.Lambda):
                            copy_child.value.args[0].body = ast.Constant(None)
                        body.append(copy_child)
                elif isinstance(child, ast.AnnAssign):
                    copy_child = copy.deepcopy(child)
                    copy_child.annotation = ast.Constant(ast.unparse(child.annotation))
                    copy_child.value = None
                    body.append(copy_child)
            bases = [ast.Name('Stage', ast.Load())] if node.name in {'Traced', 'Lowered', 'Compiled'} else []
            defs.append(ast.ClassDef(name=node.name, bases=bases, keywords=[], body=body, decorator_list=[]))
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *defs], type_ignores=[])
    namespace = {'__name__': 'isolated_jax_descriptor_fixtures'}
    from types import ModuleType
    fixture = ModuleType(namespace['__name__'])
    sys.modules[fixture.__name__] = fixture
    exec(compile(ast.fix_missing_locations(module), 'isolated-descriptor-fixtures', 'exec'), fixture.__dict__)
    return {k: v for k, v in fixture.__dict__.items() if k in wanted}

def requested_options():
    stages = (JAX_CACHE / 'docs/jax.stages.rst').read_text(encoding='utf-8')
    export = (JAX_CACHE / 'docs/jax.export.rst').read_text(encoding='utf-8')
    return (stages, export)

def attribute_comment_evidence(class_name, member):
    text = (JAX_CACHE / 'jax/_src/stages.py').read_text(encoding='utf-8')
    tree = ast.parse(text)
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name))
    found = next((n for n in cls.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and (n.target.id == member) or (isinstance(n, ast.Assign) and any((isinstance(t, ast.Name) and t.id == member for t in n.targets)))), None)
    lines = text.splitlines()
    before = lines[found.lineno - 2] if found and found.lineno > 1 else ''
    line = lines[found.lineno - 1] if found else ''
    slot = next((n for n in cls.body if isinstance(n, ast.Assign) and any((isinstance(t, ast.Name) and t.id == '__slots__' for t in n.targets))), None)
    slots = ast.literal_eval(slot.value) if slot else []
    return {'direct_assignment_line': found.lineno if found else None, 'preceding_doc_comment': bool(re.match('\\s*#:', before)), 'inline_doc_comment': bool(re.search('#:', line)), 'slot_container': 'list' if isinstance(slots, list) else type(slots).__name__, 'slot_doc': slots.get(member) if isinstance(slots, dict) else None, 'slot_member': member in slots}

def verify_inputs():
    tooling = json.loads((ROOT / 'tooling-sources.json').read_text(encoding='utf-8'))
    for source in tooling['sources']:
        assert hashlib.sha256((ROOT / source['path']).read_bytes()).hexdigest() == source['sha256'], source['path']
    tree = json.loads((JAX_CACHE / 'tree.json').read_text(encoding='utf-8'))
    assert tree['sha'] == 'bb9547a8148e50cab9c20f8521bf7af7c752b6f6' and (not tree.get('truncated'))
    blobs = {row['path']: row['sha'] for row in tree['tree'] if row['type'] == 'blob'}
    for path in ['docs/requirements.txt', '.readthedocs.yml', '.github/workflows/documentation.yml', 'docs/conf.py', 'docs/jax.stages.rst', 'docs/jax.export.rst', 'jax/_src/stages.py', 'jax/_src/export/_export.py']:
        data = (JAX_CACHE / path).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\x00' + data).hexdigest() == blobs[path], path
    return tooling

def run():
    tooling = verify_inputs()
    versions = tooling['compatible_releases_observed']
    old = json.loads(OLD.read_text(encoding='utf-8'))
    classes = metadata_fixture_classes()
    groups = {}
    checks = []
    for rel, owner, name in [('sphinx/ext/autodoc/__init__.py', 'Documenter', 'filter_members'), ('sphinx/ext/autodoc/__init__.py', 'ClassDocumenter', 'get_object_members'), ('sphinx/util/inspect.py', None, 'getdoc'), ('sphinx/ext/autodoc/importer.py', None, 'get_class_members'), ('sphinx/ext/napoleon/__init__.py', None, '_skip_member')]:
        by_hash = {}
        for version in versions:
            n = function(ROOT / 'tooling' / version / rel, name, owner)
            by_hash.setdefault(fingerprint(n), []).append(version)
        groups[(owner + '.' if owner else '') + name] = by_hash
    assert len(groups['Documenter.filter_members']) == len(groups['getdoc']) == len(groups['get_class_members']) == 1
    baseline = '7.4.7'
    helpers_by_version = {v: helpers(v) for v in versions}
    rows = []
    for candidate in old['records']:
        symbol = candidate['symbol']
        parts = symbol.split('.')
        cls_name = parts[-2]
        member = parts[-1]
        cls = classes[cls_name]
        obj = getattr(cls, member)
        own_source_doc = ast.get_docstring(function(JAX_CACHE / 'jax/_src/stages.py', member, cls_name)) if cls_name in {'Wrapped', 'Lowered', 'Compiled'} and (not member in {'in_tree', 'out_tree'}) else None
        values = []
        for version in versions:
            raw = helpers_by_version[version]['getdoc'](obj, getattr, True, cls, member)
            cls_doc = getattr(getattr(obj, '__class__', None), '__doc__', None)
            doc = None if raw == cls_doc else raw
            values.append({'version': version, 'has_doc_after_class_doc_suppression': bool(doc), 'doc_sha256': hashlib.sha256(doc.encode()).hexdigest() if doc else None})
        assert len({v['has_doc_after_class_doc_suppression'] for v in values}) == 1
        has_doc = values[0]['has_doc_after_class_doc_suppression']
        state = 'selector_eligible_own_docstring'
        reason = 'Own callable/property docstring satisfies has_doc; public/explicit member selector requests it.'
        questions = []
        if member == 'in_tree':
            state = 'selector_eligible_explicit_inherited_property'
            reason = 'Explicit members list retrieves Stage.in_tree; its own property getter has a docstring. members is a finite list, so the ALL-only inherited exclusion does not apply.'
        if symbol == 'jax.stages.Compiled.__call__':
            state = 'selector_eligible_generic_metaclass_doc_fallback'
            reason = 'Own function has no docstring. With default autodoc_inherit_docstrings=True, getdoc visits Stage/object; getattr(base,"__call__") resolves type.__call__, whose generic nonempty doc survives function-class-doc suppression. This is not a functional execution contract.'
            questions.append('Actual Python3.12 patch and descriptor/doc metadata are not pinned; exact rendered output still needs receipt.')
        if not has_doc:
            state = 'selector_filtered_undocumented'
            reason = 'No own/inherited descriptor doc or #: attribute comment; undoc-members absent. Explicit members/special-members requests do not by themselves bypass has_doc.'
        row = {'symbol': symbol, 'original_candidate_preserved': candidate, 'source_requested': True, 'selection_state': state, 'basis': reason, 'configured_selection_verified': 'source-derived with stock Sphinx/Napoleon; not a render run', 'rendered_output_verified': False, 'public_scope_action': 'retain original candidate; selection filtering is not permission to exclude public/workflow capability', 'actual_tooling_version_pinned': False, 'descriptor_fixture_results': values, 'questions': questions, 'citations': [candidate['source'], citation('sphinx/ext/autodoc/__init__.py', function(ROOT / 'tooling' / baseline / 'sphinx/ext/autodoc/__init__.py', 'filter_members', 'Documenter'), baseline), citation('sphinx/util/inspect.py', function(ROOT / 'tooling' / baseline / 'sphinx/util/inspect.py', 'getdoc'), baseline)]}
        if cls_name in {'Traced', 'Lowered', 'Compiled'} and member in {'jaxpr', 'out_info', 'out_tree'}:
            row['attribute_source_evidence'] = attribute_comment_evidence(cls_name, member)
        if symbol == 'jax.stages.Traced.jaxpr':
            row['additional_public_prose_evidence'] = {'source': JAX_BASE + 'jax/_src/stages.py#L421-L430', 'basis': 'The class docstring explicitly names .jaxpr; filtering its individual member section does not erase this documented capability.'}
        rows.append(row)
    result = {'framework': 'jax', 'version': '0.12.0.1', 'source_revision': REV, 'original_candidate_count': len(old['records']), 'original_candidates_sha256': hashlib.sha256(OLD.read_bytes()).hexdigest(), 'configured_tooling': {'python': '3.12 minor only', 'sphinx': '>=7.3.2,<8.0', 'resolved_build_lock': 'not present in inspected configuration', 'compatible_source_releases_verified': versions, 'inherit_docstrings_default': True, 'undoc_members_for_five_sets': False, 'napoleon_flags_default_false': True, 'rendered_output_verified': False, 'stock_napoleon_hook': 'Default include-init/private/special flags areFalse; source hook returns no override for these22 representative descriptors.'}, 'counts': dict(collections.Counter((r['selection_state'] for r in rows))), 'semantic_api_closures': 0, 'supersedes_historical_claims': ['Original proposal new_documented_identities and selection_basis labels did not prove rendered inclusion. All originals are retained as source-requested candidates; these explicit dispositions supersede that stronger interpretation.'], 'rows': rows, 'tooling_method_ast_fingerprints': groups, 'remaining_questions': ['Exact resolved Python/Sphinx/third-party-extension environment and rendered docs receipt absent', 'Three official release-versioned JAX stage URLs returnHTTP403; no rendered page was obtained', 'External extension event hooks not fixed by an exact transitive lock; no claim all handlers were executed', 'Filtered metadata candidates remain scope obligations; workflow and prose evidence must be reconciled, not silently excluded'], 'jax_sources': []}
    for path in ['docs/requirements.txt', '.readthedocs.yml', '.github/workflows/documentation.yml', 'docs/conf.py', 'docs/jax.stages.rst', 'docs/jax.export.rst', 'jax/_src/stages.py', 'jax/_src/export/_export.py']:
        b = (JAX_CACHE / path).read_bytes()
        result['jax_sources'].append({'path': path, 'source': JAX_BASE + path, 'sha256': hashlib.sha256(b).hexdigest()})
    (ROOT / 'selection-dispositions.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'counts': result['counts'], 'total': len(rows), 'semantics_closed': 0, 'rendered_output_verified': False}, indent=2))
if __name__ == '__main__':
    run()
