"""Static frozen-source NumPy audit. This never imports or builds NumPy."""
from __future__ import annotations
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parent
REV = 'a3d0ef1df045b858e68115001fdabc930bb3b68c'
SOURCE = ROOT / 'sources'

def read(path):
    return (SOURCE / path).read_text(encoding='utf-8')

def cite(path, line):
    return f'https://github.com/numpy/numpy/blob/{REV}/{path}#L{line}'

def line_of(path, token):
    return next((i for i, line in enumerate(read(path).splitlines(), 1) if token in line))

def options_at(path, line):
    lines = read(path).splitlines()
    indent = len(lines[line - 1]) - len(lines[line - 1].lstrip())
    result = {}
    for raw in lines[line:]:
        if not raw.strip():
            if result:
                break
            continue
        if len(raw) - len(raw.lstrip()) <= indent:
            break
        match = re.match('\\s*:([\\w-]+):\\s*(.*)', raw)
        if not match:
            break
        result[match[1]] = match[2]
    return result

def literal_exports(path):
    syntax = ast.parse(read(path))
    for node in syntax.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if any((isinstance(target, ast.Name) and target.id == '__all__' for target in targets)):
            try:
                return (ast.literal_eval(node.value), node.lineno)
            except (ValueError, TypeError):
                return (None, node.lineno)
    return (None, None)

def head(node):
    while isinstance(node, ast.Subscript):
        node = node.value
    return node.id if isinstance(node, ast.Name) else ast.unparse(node)

def function_signature(node):
    return f'{node.name}({ast.unparse(node.args)})'

def native_tables():
    result = {}
    for cls, path, tables in [('generic', 'numpy/_core/src/multiarray/scalartypes.c.src', ['gentype_methods', 'gentype_getsets']), ('ndarray', 'numpy/_core/src/multiarray/methods.c', ['array_methods']), ('ndarray', 'numpy/_core/src/multiarray/getset.c', ['array_getsetlist'])]:
        text = read(path)
        for table in tables:
            start = re.search('\\b' + table + '\\[\\]\\s*=\\s*\\{', text).start()
            end = text.index('\n};', start)
            for match in re.finditer('\\{\\s*"([^"]+)"\\s*,', text[start:end]):
                name = match.group(1)
                result.setdefault(cls, {})[name] = {'source': cite(path, text[:start + match.start()].count('\n') + 1), 'table': table}
    return result

def module_candidates(module):
    path = module.replace('.', '/')
    path = next((p for p in [path + '.py', path + '/__init__.py'] if (SOURCE / p).exists()), None)
    if path is None:
        return ([], {'module': module, 'status': 'source-not-present'})
    exports, export_line = literal_exports(path)
    tree = ast.parse(read(path))
    local = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    aliases = {target.id: (node, node.value) for node in tree.body if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name)}
    records = []
    names = list(exports) if exports is not None else list(local)
    for name in names:
        node = local.get(name)
        if node is not None:
            record = {'symbol': module + '.' + name, 'kind': 'class' if isinstance(node, ast.ClassDef) else 'function', 'source': cite(path, node.lineno), 'evidence_kind': 'static-source-export'}
            if isinstance(node, ast.FunctionDef):
                record['signature'] = function_signature(node)
            records.append(record)
        elif name in aliases:
            node, value = aliases[name]
            record = {'symbol': module + '.' + name, 'kind': 'alias', 'source': cite(path, node.lineno), 'alias_expression': ast.unparse(value), 'evidence_kind': 'static-source-export'}
            if module == 'numpy.f2py' and name == 'run_main':
                origin = 'numpy/f2py/f2py2e.py'
                definition = next((n for n in ast.parse(read(origin)).body if isinstance(n, ast.FunctionDef) and n.name == 'run_main'))
                record.update(signature=function_signature(definition), definition_source=cite(origin, definition.lineno))
            records.append(record)
        else:
            records.append({'symbol': module + '.' + name, 'kind': 'export-unresolved', 'source': cite(path, export_line), 'evidence_kind': 'literal-__all__-without-static-definition'})
    return (records, {'module': module, 'source': cite(path, 1), 'literal_exports': exports, 'export_source': cite(path, export_line or 1), 'declared_record_count': len(records)})

def scalar_and_array_candidates(targets):
    path = 'numpy/__init__.pyi'
    tree = ast.parse(read(path))
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    aliases = {target.id: (head(node.value), node.lineno) for node in tree.body if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name) and isinstance(node.value, (ast.Name, ast.Subscript))}
    native = native_tables()

    def resolve(name, visited=()):
        if name in visited:
            raise ValueError('stub alias cycle')
        return resolve(aliases[name][0], (*visited, name)) if name in aliases else name

    def members(name, visited=()):
        name = resolve(name)
        if name not in classes:
            return ({}, [name])
        if name in visited:
            raise ValueError('stub inheritance cycle')
        node = classes[name]
        result, external = ({}, [])
        for base in reversed(node.bases):
            inherited, other = members(head(base), (*visited, name))
            result.update(inherited)
            external.extend(other)
        for declaration in node.body:
            if isinstance(declaration, (ast.FunctionDef, ast.AsyncFunctionDef)):
                existing = result.get(declaration.name)
                signature = function_signature(declaration)
                item = {'defined_in': name, 'source': cite(path, declaration.lineno), 'signature': signature, 'kind': 'property' if any((ast.unparse(d) == 'property' for d in declaration.decorator_list)) else 'method'}
                if existing and existing['defined_in'] == name:
                    item['overloads'] = [*existing.get('overloads', [existing['signature']]), signature]
                result[declaration.name] = item
            elif isinstance(declaration, ast.AnnAssign) and isinstance(declaration.target, ast.Name):
                result[declaration.target.id] = {'defined_in': name, 'source': cite(path, declaration.lineno), 'kind': 'annotated-attribute', 'annotation': ast.unparse(declaration.annotation)}
        return (result, sorted(set(external)))
    records, coverage = ([], [])
    for target in sorted(targets):
        resolved = resolve(target)
        effective, external = members(target)
        c_parent = 'ndarray' if target == 'ndarray' else 'generic'
        for name, item in native.get(c_parent, {}).items():
            effective.setdefault(name, {'kind': 'native-member', 'defined_in': c_parent, 'source': item['source']})
        for name, details in sorted(effective.items()):
            record = {'symbol': f'numpy.{target}.{name}', **details, 'evidence_kind': 'type-stub-declaration-not-runtime-verification', 'name_visibility': 'private' if name.startswith('_') and (not name.startswith('__')) else 'protocol-or-special' if name.startswith('__') else 'public-name'}
            if name in native.get(c_parent, {}):
                record.update(native_registration=native[c_parent][name], evidence_kind='stub-and-native-base-registration' if 'signature' in details else 'native-base-registration')
            records.append(record)
        coverage.append({'class': 'numpy.' + target, 'stub_resolved_class': resolved, 'alias_source': cite(path, aliases[target][1]) if target in aliases else None, 'declared_or_inherited_candidate_count': len(effective), 'external_or_typing_bases_not_expanded': external, 'runtime_complete': False})
    return (records, coverage)

def ufunc_candidates():
    path = 'numpy/_core/code_generators/generate_umath.py'
    syntax = ast.parse(read(path))
    definition = next((n for n in syntax.body if isinstance(n, ast.Assign) and any((isinstance(t, ast.Name) and t.id == 'defdict' for t in n.targets))))
    assert isinstance(definition.value, ast.Dict)
    root_exports, root_export_line = literal_exports('numpy/__init__.pyi')
    assert root_exports is not None
    string_exports, _ = literal_exports('numpy/_core/strings.py')
    string_imports = {alias.name: (alias.asname or alias.name, node.lineno) for node in ast.parse(read('numpy/_core/strings.py')).body if isinstance(node, ast.ImportFrom) and node.module == 'numpy._core.umath' for alias in node.names}
    records = []
    for key, value in zip(definition.value.keys, definition.value.values):
        assert isinstance(key, ast.Constant) and isinstance(key.value, str)
        record = {'symbol': 'numpy._core.umath.' + key.value, 'kind': 'generated-ufunc-definition', 'source': cite(path, key.lineno), 'name_visibility': 'private-source-name' if key.value.startswith('_') else 'public-source-name', 'evidence_kind': 'static-generator-definition-not-instantiated-ufunc'}
        bindings = []
        if key.value in root_exports:
            bindings.append({'symbol': 'numpy.' + key.value, 'evidence_kind': 'root-type-stub-__all__', 'source': cite('numpy/__init__.pyi', root_export_line)})
        if key.value in string_imports:
            local, line = string_imports[key.value]
            if local in string_exports:
                bindings.append({'symbol': 'numpy.strings.' + local, 'source': cite('numpy/_core/strings.py', line), 'evidence_kind': 'explicit-umath-import-and-__all__-with-strings-reexport'})
            else:
                record['internal_string_binding'] = {'name': local, 'source': cite('numpy/_core/strings.py', line)}
        record['declared_public_bindings'] = bindings
        if isinstance(value, ast.Call) and head(value.func) == 'Ufunc':
            record.update(nin=ast.literal_eval(value.args[0]), nout=ast.literal_eval(value.args[1]), type_loop_expressions=[ast.unparse(a) for a in value.args[4:]], options={kw.arg: ast.unparse(kw.value) for kw in value.keywords})
        records.append(record)
    alias_path = 'numpy/_core/src/umath/umathmodule.c'
    for alias, target in [('true_divide', 'divide'), ('conj', 'conjugate'), ('mod', 'remainder')]:
        records.append({'symbol': 'numpy._core.umath.' + alias, 'kind': 'native-ufunc-alias', 'alias_target': 'numpy._core.umath.' + target, 'declared_public_bindings': [{'symbol': 'numpy.' + alias, 'evidence_kind': 'root-type-stub-__all__'}] if alias in root_exports else [], 'source': cite(alias_path, line_of(alias_path, f'PyDict_SetItemString(d, "{alias}"')), 'evidence_kind': 'static-native-alias-assignment'})
    return records

def main():
    baseline_bytes = (ROOT / 'baseline-inventory.json').read_bytes()
    baseline = json.loads(baseline_bytes)
    assert baseline['source_revision'] == REV
    assert len(baseline['extraction_gaps']) == 65
    assert baseline['extraction']['complete'] is False
    assert 'autodoc_default_options' not in read('doc/source/conf.py')
    assert 'numpydoc==1.10.0' in read('requirements/doc_requirements.txt')
    assert 'sphinx==7.2.6' in read('requirements/doc_requirements.txt')
    sources = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
    for entry in sources:
        data = (SOURCE / entry['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\x00' + data).hexdigest() == entry['git_blob_sha']
    dispositions, module_records, module_coverage = ([], [], [])
    protocol = {'object.__array_interface__': ('numpy.array-protocol.__array_interface__', 'duck-typed protocol attribute, not builtins.object or a NumPy callable'), 'object.__array_struct__': ('numpy.array-protocol.__array_struct__', 'duck-typed PyCapsule protocol attribute, not builtins.object or a NumPy callable'), 'ndarray.__array_finalize__': ('numpy.ndarray.__array_finalize__', 'ndarray subtype protocol; C method and stub corroborate owner'), 'ndarray.__array_priority__': ('numpy.ndarray.__array_priority__', 'ndarray precedence attribute; native getset corroborates owner'), 'ndarray.__array_wrap__': ('numpy.ndarray.__array_wrap__', 'ndarray wrapping protocol; C method and stub corroborate owner'), 'ndpointer': ('numpy.ctypeslib.ndpointer', "tutorial's ctypeslib context and pinned Python definition corroborate owner")}
    targets = {'ndarray', 'generic'}
    for gap in baseline['extraction_gaps']:
        item = {'gap_id': gap['path'] + '#L' + str(gap['line']), 'original': gap, 'source': cite(gap['path'], gap['line']), 'capabilities_verified': 0}
        if gap.get('directive'):
            options = options_at(gap['path'], gap['line'])
            item['scoped_options'] = options
            if options.get('members') == options.get('exclude-members') == '__init__':
                item.update(disposition='resolved-empty-explicit-selection', status='closed-directive-question', rationale='The only requested member is explicitly excluded; both Sphinx and pinned numpydoc respect the member/exclude sets. This does not waive inherited/source API coverage.')
                if gap['argument'].startswith('numpy.'):
                    targets.add(gap['argument'].removeprefix('numpy.'))
            elif 'no-members' in options:
                item.update(disposition='resolved-members-explicitly-disabled', status='closed-directive-question', rationale='This directive explicitly disables member expansion; module docstring/source exports remain audited separately.')
            elif 'members' not in options:
                item.update(disposition='resolved-no-default-member-expansion', status='closed-directive-question', rationale='No members option and no NumPy autodoc_default_options enable module-member recursion; inserted module docstring content has separate source coverage.')
            elif options['members'] == '':
                records, coverage = module_candidates(gap['argument'])
                assert records and all((r['kind'] != 'export-unresolved' for r in records))
                module_records.extend(records)
                module_coverage.append(coverage)
                item.update(disposition='resolved-static-literal-exports', status='closed-static-export-extraction', resolved_symbols=[r['symbol'] for r in records], export_evidence=coverage, rationale="Explicit member expansion is bounded by this module's literal __all__; each export resolves to a local or statically traced function definition. No runtime execution is implied.")
            else:
                raise AssertionError(f'unhandled directive {gap}')
        else:
            identity, rationale = protocol[gap['argument']]
            item.update(disposition='resolved-protocol-or-owner-qualification', status='closed-name-resolution', resolved_identity=identity, rationale=rationale, original_identifier_retained=True)
            if gap['argument'] == 'ndpointer':
                item['definition_source'] = cite('numpy/ctypeslib/_ctypeslib.py', line_of('numpy/ctypeslib/_ctypeslib.py', 'def ndpointer('))
        dispositions.append(item)
    inherited, inherited_coverage = scalar_and_array_candidates(targets)
    generated = ufunc_candidates()
    baseline_symbols = {r['symbol'] for r in baseline['records']}
    for record in [*module_records, *inherited, *generated]:
        record['baseline_declaration_present'] = record['symbol'] in baseline_symbols or any((binding['symbol'] in baseline_symbols for binding in record.get('declared_public_bindings', [])))
        record['capability_status'] = 'unmapped-semantic-candidate'
        record['implementation_verified'] = False
    result = {'schema_version': 1, 'framework': 'numpy', 'version': '2.5.4', 'revision': REV, 'baseline_inventory_sha256': hashlib.sha256(baseline_bytes).hexdigest(), 'tooling_source_provenance': json.loads((ROOT / 'tooling-sources.json').read_text(encoding='utf-8')), 'scope': '65 explicit questions only; static candidate supplement is not a public capability denominator', 'all_65_disposed': len(dispositions) == 65, 'full_public_inventory_complete': False, 'counts': dict(Counter((item['disposition'] for item in dispositions))), 'dispositions': dispositions, 'remaining_true_unknowns': ['Rendered Sphinx/numpydoc symbol index has not been built or imported; static closure does not prove equality to rendered objects.', 'Platform/ABI-dependent scalar identity, longdouble precision, builtin base inheritance and conditional native template members need exact target observations; stubs are not runtime authority.', 'Generated ufunc DSL loop definitions require full type-set/template/ISA expansion and per-loop signature/error analysis; definitions are not capability proofs.', 'Protocols are source-qualified but ownership, mutation/alias/lifetime/default/error semantics need separate contracts.', 'Notebook/prose/C-API multi-signature and data-driven dtype exports outside these65 questions remain in full inventory scope.', 'Constructor custom DTypes, user override protocols and user object arithmetic can execute arbitrary dispatch; exhaustive behavior is a protocol contract, not a finite dtype list.']}
    (ROOT / 'gap-dispositions.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    supplement = {'schema_version': 1, 'revision': REV, 'capabilities_verified': 0, 'module_exports': module_records, 'module_coverage': module_coverage, 'inherited_array_scalar_candidates': inherited, 'inherited_coverage': inherited_coverage, 'generated_ufunc_candidates': generated}
    (ROOT / 'static-candidates.json').write_text(json.dumps(supplement, separators=(',', ':')) + '\n', encoding='utf-8')
    assertions = {'source_files_git_blob_and_sha256_checked': len(sources), 'baseline_gap_count': 65, 'all_gap_ids_unique': len({x['gap_id'] for x in dispositions}) == 65, 'all_gap_ids_disposed': len(dispositions) == 65, 'literal_export_modules_resolved': len(module_coverage), 'new_static_export_records': len(module_records), 'inherited_candidate_records': len(inherited), 'ufunc_definition_and_alias_records': len(generated), 'no_framework_imports_or_builds': True, 'capabilities_verified': 0}
    assert assertions['all_gap_ids_unique']
    assert len(generated) == 133
    assert all((record['capability_status'] == 'unmapped-semantic-candidate' for record in inherited))
    (ROOT / 'machine-assertions.json').write_text(json.dumps(assertions, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'disposition_counts': result['counts'], **assertions}, sort_keys=True))
if __name__ == '__main__':
    main()
