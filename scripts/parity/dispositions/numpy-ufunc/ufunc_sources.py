"""Static frozen-source readers. Never imports NumPy or executes its generator."""
import ast
import hashlib
import json
from pathlib import Path
import re
import textwrap
ROOT = Path(__file__).resolve().parent
REV = 'a3d0ef1df045b858e68115001fdabc930bb3b68c'
GEN = 'numpy/_core/code_generators/generate_umath.py'
C = 'numpy/_core/src/umath/ufunc_object.c'
DOC = 'numpy/_core/_add_newdocs.py'
PAYLOAD = 'numpy/_core/code_generators/ufunc_docstrings.py'

def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))

def text(path):
    return (ROOT / 'sources' / path).read_text(encoding='utf-8')

def cite(path, line):
    return f'https://github.com/numpy/numpy/blob/{REV}/{path}#L{line}'

def find_line(path, token):
    return next((i for i, line in enumerate(text(path).splitlines(), 1) if token in line))

def syntax(path):
    return ast.parse(text(path))

def module_statements(nodes):
    """Visit module conditional blocks but never function/class bodies."""
    for node in nodes:
        yield node
        if isinstance(node, (ast.If, ast.Try, ast.With)):
            yield from module_statements(node.body)
            yield from module_statements(getattr(node, 'orelse', []))
            yield from module_statements(getattr(node, 'finalbody', []))
            for handler in getattr(node, 'handlers', []):
                yield from module_statements(handler.body)

def literal_all(path):
    for node in module_statements(syntax(path).body):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if any((isinstance(t, ast.Name) and t.id == '__all__' for t in targets)):
            try:
                result = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            if isinstance(result, list):
                return result
    return None

def generated_objects():
    definition = next((node for node in syntax(GEN).body if isinstance(node, ast.Assign) and any((isinstance(t, ast.Name) and t.id == 'defdict' for t in node.targets))))
    assert isinstance(definition.value, ast.Dict)
    identities = {'None': (None, False), 'ReorderableNone': (None, True), 'Zero': (0, True), 'One': (1, True), 'True_': (True, True), 'False_': (False, True), 'AllOnes': (-1, True), 'MinusInfinity': ('negative-infinity', True)}
    rows = {}
    for key, value in zip(definition.value.keys, definition.value.values):
        assert isinstance(key, ast.Constant) and isinstance(key.value, str)
        assert isinstance(value, ast.Call) and ast.unparse(value.func) == 'Ufunc'
        options = {kw.arg: ast.unparse(kw.value) for kw in value.keywords}
        core = next((ast.literal_eval(kw.value) for kw in value.keywords if kw.arg == 'signature'), None)
        identity_expression = ast.unparse(value.args[2])
        identity, reorderable = identities[identity_expression]
        rows[key.value] = {'object_id': f'numpy@2.5.4:generated:{key.value}', 'generated_name': key.value, 'native_origin': f'numpy._core._multiarray_umath.{key.value}', 'source': cite(GEN, key.lineno), 'nin': ast.literal_eval(value.args[0]), 'nout': ast.literal_eval(value.args[1]), 'core_signature': core, 'generalized': core is not None, 'default_identity_expression': identity_expression, 'default_identity_value': identity, 'generator_default_reorderable': reorderable, 'identity_warning': 'This is ufunc default metadata; the selected ArrayMethod/DType supplies actual reduction-initial behavior.', 'doc_lookup_expression': ast.unparse(value.args[3]), 'type_resolver_expression': ast.unparse(value.args[4]), 'type_loop_expressions': [ast.unparse(node) for node in value.args[5:]], 'generator_options': options, 'name_visibility': 'private-or-internal-source-name' if key.value.startswith('_') else 'public-looking-source-name', 'runtime_instantiation_verified': False, 'semantic_completeness': False}
    assert len(rows) == 130
    return rows

def native_aliases(objects):
    path = 'numpy/_core/src/umath/umathmodule.c'
    source = text(path)
    pattern = re.compile('(?P<get>\\b(?P<var>\\w+)\\s*=\\s*PyDict_GetItemString\\(d,\\s*"(?P<name>[^"]+)"\\))|(?P<put>PyDict_SetItemString\\(d,\\s*"(?P<alias>[^"]+)",\\s*(?P<value>\\w+)\\))')
    variables, rows = ({}, [])
    for match in pattern.finditer(source):
        line = source[:match.start()].count('\n') + 1
        if match['get']:
            variables[match['var']] = (match['name'], line)
        elif match['value'] in variables:
            target, origin_line = variables[match['value']]
            if target in objects:
                rows.append({'alias': match['alias'], 'target_name': target, 'object_id': objects[target]['object_id'], 'source': cite(path, line), 'origin_read_source': cite(path, origin_line), 'relation': 'explicit-native-dictionary-object-alias; no semantic row merge'})
    assert {r['alias'] for r in rows} == {'true_divide', 'conj', 'mod'}
    return rows

def generated_doc_payloads(objects):
    """Render only literal docs plus whitelisted stdlib text substitutions."""
    tree = syntax(PAYLOAD)
    substitution = next((node.value for node in tree.body if isinstance(node, ast.Assign) and any((isinstance(t, ast.Name) and t.id == 'subst' for t in node.targets))))

    def evaluate(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if ast.unparse(node.func) == 'textwrap.dedent' and len(node.args) == 1:
                return textwrap.dedent(evaluate(node.args[0]))
            if node.func.attr == 'strip' and (not node.args):
                return evaluate(node.func.value).strip()
        raise ValueError('unhandled doc substitution syntax: ' + ast.dump(node))
    assert isinstance(substitution, ast.Dict)
    values = {ast.literal_eval(key): evaluate(value) for key, value in zip(substitution.keys, substitution.values)}
    result = {}
    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call) or ast.unparse(node.value.func) != 'add_newdoc':
            continue
        place, name, raw = map(ast.literal_eval, node.value.args)
        assert place == 'numpy._core.umath'
        rendered = textwrap.dedent(raw).strip()
        for key, value in values.items():
            rendered = rendered.replace('$' + key, value)
        assert not re.search('\\$(?:PARAMS|BROADCASTABLE_2|OUT_SCALAR_[12])', rendered)
        assert name not in result, 'duplicate generated doc: ' + name
        result[name] = {'source': cite(PAYLOAD, node.lineno), 'raw_literal_sha256': hashlib.sha256(raw.encode()).hexdigest(), 'normalized_substituted_doc_sha256': hashlib.sha256(rendered.encode()).hexdigest(), 'first_line': rendered.splitlines()[0] if rendered else None, 'substitution_keys': sorted(values), 'payload_status': 'nonempty-source-doc-payload' if rendered else 'explicit-empty-source-doc-payload-retained', 'documentation_kind': 'exact-source-generated-object-doc-payload;not-runtime-import', 'raw_for_alias_checks': raw}
    assert set(result) == set(objects), (set(objects) - set(result), set(result) - set(objects))
    return result

def autosummary_selectors():
    path = 'doc/source/reference/ufuncs.rst'
    lines = text(path).splitlines()
    result = []
    for i, line in enumerate(lines):
        match = re.match('^(\\s*)\\.\\. autosummary::', line)
        if not match:
            continue
        indent = len(match[1])
        for j in range(i + 1, len(lines)):
            row = lines[j]
            if row.strip() and len(row) - len(row.lstrip()) <= indent:
                break
            if not row.strip() or row.strip().startswith(':'):
                continue
            name = row.strip().split()[0].lstrip('~')
            assert re.fullmatch('\\w+(?:\\.\\w+)*', name), name
            result.append({'selector_id': path + '#L' + str(j + 1), 'symbol': name if name.startswith('numpy.') else 'numpy.' + name, 'source': cite(path, j + 1)})
    return result

def table(path, name, native_type):
    source = text(path)
    start = re.search('\\b' + name + '\\[\\]\\s*=\\s*\\{', source).start()
    end = source.index('\n};', start) + 3
    body = source[start:end]
    matches = list(re.finditer('\\{\\s*"([^"]+)"\\s*,', body))
    result = {}
    for i, match in enumerate(matches):
        stop = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        entry = body[match.start():stop].split('}', 1)[0]
        result[match[1]] = {'member': match[1], 'native_kind': native_type, 'source': cite(path, source[:start + match.start()].count('\n') + 1), 'registration': entry.strip(), 'table': name}
    return (result, body)

def member_inventory():
    methods, _ = table(C, 'ufunc_methods', 'native-method')
    attrs, _ = table(C, 'ufunc_getset', 'native-getset')
    members, _ = table(C, 'ufunc_members', 'native-member')
    rows = {**methods, **attrs, **members}
    rows['__call__'] = {'member': '__call__', 'native_kind': 'native-vectorcall-slot', 'source': cite(C, find_line(C, '.tp_call = &PyVectorcall_Call'))}
    rows['__signature__'] = {'member': '__signature__', 'native_kind': 'installed-lazy-descriptor', 'source': cite('numpy/_globals.py', find_line('numpy/_globals.py', 'class _SignatureDescriptor')), 'installation_source': cite('numpy/_core/src/multiarray/multiarraymodule.c', find_line('numpy/_core/src/multiarray/multiarraymodule.c', 's = npy_import("numpy._globals", "_signature_descriptor")')), 'behavior': 'Class access raises AttributeError; instance access builds inspect.Signature lazily and writes it to the instance dict. Its convenience signature exposes only one out parameter and is not an exhaustive native parser schema.'}
    for node in syntax(DOC).body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if ast.unparse(call.func) != 'add_newdoc' or len(call.args) < 3:
            continue
        try:
            module, obj = (ast.literal_eval(call.args[0]), ast.literal_eval(call.args[1]))
        except (ValueError, TypeError):
            continue
        if module == 'numpy._core' and obj == 'ufunc':
            if isinstance(call.args[2], ast.Tuple):
                member, doc = ast.literal_eval(call.args[2])
                rows.setdefault(member, {'member': member, 'native_kind': 'doc-only-unresolved'})
                rows[member]['doc_source'] = cite(DOC, node.lineno)
                rows[member]['doc_sha256'] = hashlib.sha256(doc.encode()).hexdigest()
                rows[member]['documented_signatures'] = [line.strip() for line in doc.splitlines() if line.strip().startswith(member + '(')]
                rows[member]['stability'] = 'public-unstable-C-user-specific' if member in {'_get_strided_loop', '_resolve_dtypes_and_context'} else 'release-documented'
            else:
                rows['__call__']['doc_source'] = cite(DOC, node.lineno)
    ufclass = next((node for node in syntax('numpy/__init__.pyi').body if isinstance(node, ast.ClassDef) and node.name == 'ufunc'))
    for node in ufclass.body:
        if isinstance(node, ast.FunctionDef):
            name = node.name
            rows.setdefault(name, {'member': name, 'native_kind': 'stub-only-unresolved'})
            rows[name]['stub_source'] = cite('numpy/__init__.pyi', node.lineno)
            rows[name]['stub_signature'] = f'{name}({ast.unparse(node.args)})'
    rows['__module__'] = {'member': '__module__', 'native_kind': 'conditional-instance-dict-assignment', 'source': cite('numpy/_core/strings.py', find_line('numpy/_core/strings.py', 'ufunc.__module__ = "numpy.strings"')), 'behavior': 'Explicitly assigned for the selected string ufuncs in _override___module__; no universal instance value inferred.'}
    for name, row in rows.items():
        row.setdefault('stability', 'native-or-stub-candidate;publicness-reconciliation-required')
        row['member_id'] = 'numpy@2.5.4:ufunc-member:' + name
        row['semantic_status'] = 'partial-source-contract;dtype-layout-device-error-AD-evidence-required'
        if row['native_kind'] == 'native-getset':
            row['native_setter_present'] = name == '__doc__'
    rows['__doc__']['documentation_conflict'] = 'ufuncs.rst says attributes cannot be set, but frozen native table installs ufunc_set_doc and setter writes/deletes instance dict key without a type check. Retain conflict, not a readonly parity assumption.'
    rows['__qualname__']['runtime_status'] = 'Stub-declared globally; explicitly assigned to selected string ufuncs. General default runtime presence not proven from the getset table; do not count it verified.'
    return rows

def direct_bindings(objects, aliases):
    """Resolve this frozen, bounded import/alias graph; retain wrappers separately."""
    native = {name: {'object_id': row['object_id'], 'chain': [row['source']]} for name, row in objects.items()}
    for row in aliases:
        native[row['alias']] = {'object_id': row['object_id'], 'chain': [row['source'], row['origin_read_source']]}
    module_maps = {'numpy._core._multiarray_umath': native}
    export_maps = {'numpy._core._multiarray_umath': [name for name in native if not name.startswith('_')]}
    wrappers = []
    modules = [('numpy._core.multiarray', 'numpy/_core/multiarray.py'), ('numpy._core.umath', 'numpy/_core/umath.py'), ('numpy._core.numeric', 'numpy/_core/numeric.py'), ('numpy._core', 'numpy/_core/__init__.py'), ('numpy', 'numpy/__init__.py'), ('numpy._core.strings', 'numpy/_core/strings.py'), ('numpy.strings', 'numpy/strings/__init__.py'), ('numpy._core.defchararray', 'numpy/_core/defchararray.py')]
    for module, path in modules:
        bindings, module_aliases = ({}, {})
        package = module if path.endswith('/__init__.py') else module.rsplit('.', 1)[0]
        for node in module_statements(syntax(path).body):
            if isinstance(node, ast.ImportFrom):
                base = package.split('.')[:len(package.split('.')) - node.level + 1] if node.level else []
                origin = '.'.join([*base, *([node.module] if node.module else [])]) if node.level else node.module
                if node.module is None:
                    for alias in node.names:
                        module_aliases[alias.asname or alias.name] = origin + '.' + alias.name
                if origin in module_maps:
                    for alias in node.names:
                        names = export_maps.get(origin, []) if alias.name == '*' else [alias.name]
                        for name in names:
                            if name in module_maps[origin]:
                                local = name if alias.name == '*' else alias.asname or name
                                row = module_maps[origin][name]
                                bindings[local] = {'object_id': row['object_id'], 'chain': [cite(path, node.lineno), *row['chain']]}
            elif isinstance(node, ast.Assign):
                value = node.value
                source = bindings.get(value.id) if isinstance(value, ast.Name) else None
                if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name):
                    origin = module_aliases.get(value.value.id)
                    source = module_maps.get(origin, {}).get(value.attr)
                if source:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            bindings[target.id] = {'object_id': source['object_id'], 'chain': [cite(path, node.lineno), *source['chain']]}
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if node.name in bindings:
                    wrappers.append({'symbol': module + '.' + node.name, 'shadowed_native_object': bindings.pop(node.name)['object_id'], 'source': cite(path, node.lineno), 'relation': 'Python-wrapper-or-class-not-native-object-alias'})
        exports = literal_all(path)
        if module == 'numpy._core.numeric':
            exports = [*(exports or []), *export_maps['numpy._core.umath']]
        elif module == 'numpy._core':
            exports = [*(exports or []), *export_maps['numpy._core.numeric']]
        elif module == 'numpy':
            exports = literal_all('numpy/__init__.pyi')
        elif module == 'numpy.strings':
            exports = export_maps['numpy._core.strings']
        export_maps[module] = list(dict.fromkeys(exports or [name for name in bindings if not name.startswith('_')]))
        module_maps[module] = bindings
    result = []
    for module in ['numpy._core._multiarray_umath', 'numpy._core.umath', 'numpy._core.numeric', 'numpy._core', 'numpy', 'numpy._core.strings', 'numpy.strings', 'numpy._core.defchararray']:
        for name, row in sorted(module_maps[module].items()):
            public_namespace = module in {'numpy', 'numpy.strings'} and name in export_maps[module]
            result.append({'binding_id': 'numpy@2.5.4:binding:' + module + '.' + name, 'symbol': module + '.' + name, **row, 'public_namespace_export': public_namespace, 'relation': 'source-object-binding;spelling-and-workflow-retained', 'runtime_verified': False})
    return (result, wrappers, module_maps)
