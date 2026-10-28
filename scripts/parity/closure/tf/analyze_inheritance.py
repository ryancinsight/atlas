"""Infer selected-TensorFlow Keras member provenance from AST, not runtime."""
import ast, hashlib, json, warnings
from collections import defaultdict, Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'source/keras'
REV = '250b42181ce9f37df68319d8f4753ec89a349a43'

def qname(n):
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        p = qname(n.value)
        return p + '.' + n.attr if p else None
    if isinstance(n, ast.Subscript):
        return qname(n.value)
    return None

def module_of(p):
    return p.removesuffix('.py').replace('/', '.').removesuffix('.__init__')

def srcurl(p, line):
    repo, rev = ('keras-team/keras', REV) if p.startswith('keras/') else ('tensorflow/tensorflow', 'a481b10260dfdf833a1b16007eead49c1d7febf3')
    return f'https://github.com/{repo}/blob/{rev}/{p}#L{line}'
modules = {}
classes = {}
parse_errors = []
parse_warnings = []
unknown_conditions = []
dynamic_forms = []

def condition(n):
    if isinstance(n, ast.Constant):
        return bool(n.value)
    if isinstance(n, ast.Name) and n.id == 'TYPE_CHECKING':
        return False
    if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], (ast.Eq, ast.NotEq)) and (len(n.comparators) == 1):
        left, right = (n.left, n.comparators[0])
        if isinstance(left, ast.Call) and (qname(left.func) or '').split('.')[-1] == 'backend' and isinstance(right, ast.Constant) and isinstance(right.value, str):
            v = right.value == 'tensorflow'
            return not v if isinstance(n.ops[0], ast.NotEq) else v
    return None
source_pairs = [(p, SRC) for p in SRC.rglob('*.py')] + [(p, ROOT / 'source/tensorflow') for p in (ROOT / 'source/tensorflow/tensorflow').rglob('*.py')]
for p, source_root in sorted(source_pairs, key=lambda x: str(x[0])):
    rel = p.relative_to(source_root).as_posix()
    mod = module_of(rel)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            t = ast.parse(p.read_bytes(), filename=rel)
        parse_warnings.extend(({'path': rel, 'line': x.lineno, 'category': x.category.__name__, 'message': str(x.message)} for x in caught))
    except Exception as e:
        parse_errors.append({'path': rel, 'error': str(e)})
        continue
    info = {'path': rel, 'imports': defaultdict(list), 'aliases': defaultdict(list), 'wildcards': [], 'defs': {}, 'conditional': False}
    modules[mod] = info

    def walk(body, uncertain=False):
        for n in body:
            if isinstance(n, ast.If):
                v = condition(n.test)
                if v is True:
                    walk(n.body, uncertain)
                elif v is False:
                    walk(n.orelse, uncertain)
                else:
                    unknown_conditions.append({'module': mod, 'source': srcurl(rel, n.lineno), 'condition': ast.unparse(n.test)})
                    walk(n.body, True)
                    walk(n.orelse, True)
            elif isinstance(n, (ast.Try, ast.With)):
                walk(n.body, True)
                for handler in getattr(n, 'handlers', []):
                    walk(handler.body, True)
                walk(getattr(n, 'orelse', []), True)
                walk(getattr(n, 'finalbody', []), True)
            elif isinstance(n, ast.ImportFrom) and n.module:
                module = n.module
                if n.level:
                    parts = mod.split('.') if rel.endswith('__init__.py') else mod.split('.')[:-1]
                    module = '.'.join(parts[:len(parts) - n.level + 1] + [module])
                for a in n.names:
                    if a.name == '*':
                        info['wildcards'].append(module)
                    else:
                        info['imports'][a.asname or a.name].append(module + '.' + a.name)
            elif isinstance(n, ast.Import):
                for a in n.names:
                    info['imports'][a.asname or a.name.split('.')[0]].append(a.name if a.asname else a.name.split('.')[0])
            elif isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                ident = mod + '.' + n.name
                info['defs'][n.name] = ident
                if isinstance(n, ast.ClassDef):
                    members = {}
                    unhandled = []
                    for child in n.body:
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            decorators = [ast.unparse(x) for x in child.decorator_list]
                            if child.name.startswith('_') and child.name not in ['__init__', '__call__', '__iter__', '__getitem__', '__len__', '__enter__', '__exit__']:
                                continue
                            property_role = next(('setter' if x.endswith('.setter') else 'deleter' if x.endswith('.deleter') else 'getter' for x in decorators if x == 'property' or x.endswith(('.property', '.setter', '.deleter'))), None)
                            member = {'name': child.name, 'kind': 'property' if property_role else 'method', 'signature': ast.unparse(child.args), 'decorators': decorators, 'defining_class': ident, 'source': srcurl(rel, child.lineno), 'line': child.lineno}
                            if property_role:
                                member['accessor_role'] = property_role
                            if child.name in members:
                                previous = members[child.name]
                                decls = previous.get('declarations', [dict(previous)])
                                decls.append(dict(member))
                                previous['declarations'] = decls
                                if property_role:
                                    previous['kind'] = 'property'
                            else:
                                members[child.name] = member
                        elif isinstance(child, (ast.Assign, ast.AnnAssign)):
                            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
                            for target in targets:
                                if isinstance(target, ast.Name) and (not target.id.startswith('_')):
                                    members[target.id] = {'name': target.id, 'kind': 'class_attribute', 'defining_class': ident, 'source': srcurl(rel, child.lineno), 'line': child.lineno}
                        elif not isinstance(child, (ast.Expr, ast.Pass)):
                            unhandled.append({'line': child.lineno, 'form': type(child).__name__})
                    classes[ident] = {'module': mod, 'name': n.name, 'bases_expr': [ast.unparse(b) for b in n.bases], 'bases_nodes': n.bases, 'members': members, 'source': srcurl(rel, n.lineno), 'conditional_definition': uncertain, 'unhandled_class_body_forms': unhandled}
            elif isinstance(n, (ast.Assign, ast.AnnAssign)):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                expr = qname(n.value) if n.value else None
                if expr:
                    for target in targets:
                        if isinstance(target, ast.Name):
                            first, *tail = expr.split('.')
                            prefixes = info['imports'].get(first, [])
                            if prefixes:
                                info['aliases'][target.id].extend(('.'.join([x] + tail) for x in prefixes))
                            elif first in info['defs']:
                                info['aliases'][target.id].append('.'.join([info['defs'][first]] + tail))
                            elif info['wildcards'] and '.' not in expr:
                                info['aliases'][target.id].extend((x + '.' + expr for x in info['wildcards']))
                            else:
                                info['aliases'][target.id].append(mod + '.' + expr)
            elif isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and (qname(n.value.func) or '').endswith(('setattr', 'add_method')):
                dynamic_forms.append({'source': srcurl(rel, n.lineno), 'expression': ast.unparse(n.value)})
    walk(t.body)
public_aliases = defaultdict(list)
for group in json.loads((ROOT / 'declaration-relations.json').read_bytes())['tf_export_groups']:
    if group['target']:
        for endpoint in group['endpoints']:
            public_aliases['tensorflow.' + endpoint.removeprefix('tf.')].append(group['target'])

def resolve(ident, seen=()):
    if ident in classes:
        return [ident]
    if ident in seen:
        return []
    if ident in public_aliases:
        return sorted(set((x for target in public_aliases[ident] for x in resolve(target, seen + (ident,)))))
    if ident in ['object', 'builtins.object']:
        return ['builtins.object']
    mod, _, name = ident.rpartition('.')
    if mod not in modules:
        if ident.startswith('keras.') and (not ident.startswith(('keras.src.', 'keras.api.'))):
            return resolve('keras.api.' + ident.removeprefix('keras.'), seen + (ident,))
        return [ident]
    info = modules[mod]
    if name in info['defs']:
        return [info['defs'][name]]
    result = []
    for value in info['imports'].get(name, []) + info['aliases'].get(name, []):
        result.extend(resolve(value, seen + (ident,)))
    if not result:
        for module in info['wildcards']:
            candidate = module + '.' + name
            resolved = resolve(candidate, seen + (ident,))
            result.extend((x for x in resolved if x in classes or x.rpartition('.')[0] in modules))
    return sorted(set(result))

def resolve_base(mod, node):
    expr = qname(node)
    if not expr:
        return []
    first, *tail = expr.split('.')
    info = modules[mod]
    if first == 'object':
        return ['builtins.object']
    target = info['imports'].get(first, []) + info['aliases'].get(first, [])
    if not target:
        target = [info['defs'].get(first, mod + '.' + first)]
    return sorted(set((x for t in target for x in resolve('.'.join([t] + tail)))))
for ident, c in classes.items():
    c['bases'] = [resolve_base(c['module'], b) for b in c['bases_nodes']]

def mro(ident, stack=()):
    if ident in stack:
        raise ValueError('inheritance cycle ' + ident)
    c = classes.get(ident)
    if c is None:
        return [ident]
    if any((len(x) != 1 for x in c['bases'])):
        raise ValueError('unresolved/ambiguous base ' + ident)
    bases = [x[0] for x in c['bases']]
    seqs = [mro(x, stack + (ident,))[:] for x in bases] + [bases[:]]
    result = [ident]
    while any(seqs):
        seqs = [x for x in seqs if x]
        candidate = next((s[0] for s in seqs if all((s[0] not in x[1:] for x in seqs))), None)
        if candidate is None:
            raise ValueError('C3 conflict ' + ident)
        result.append(candidate)
        for s in seqs:
            if s and s[0] == candidate:
                s.pop(0)
    return result
reach = json.loads((ROOT / 'keras-reachable-exports.json').read_bytes())
public = []
unresolved_targets = []
unresolved_mro = []
for row in reach['records']:
    if row['kind'] != 'symbol_export':
        continue
    candidates = resolve(row['target'])
    class_candidates = [x for x in candidates if x in classes]
    if not class_candidates:
        if not candidates:
            unresolved_targets.append({'symbol': row['symbol'], 'target': row['target']})
        continue
    if len(class_candidates) != 1:
        unresolved_targets.append({'symbol': row['symbol'], 'target': row['target'], 'class_candidates': class_candidates})
        continue
    target = class_candidates[0]
    c = classes[target]
    try:
        order = mro(target)
        status = 'static_c3_resolved'
    except ValueError as e:
        order = [target]
        status = 'unresolved_inheritance'
        unresolved_mro.append({'symbol': row['symbol'], 'target': target, 'reason': str(e), 'bases': c['bases']})
    effective = {}
    for cls in order:
        for name, member in classes.get(cls, {}).get('members', {}).items():
            if name not in effective:
                effective[name] = {**member, 'symbol': row['symbol'] + '.' + name, 'inherited': cls != target}
    public.append({'symbol': row['symbol'], 'target': target, 'source': c['source'], 'mro_status': status, 'mro': order, 'bases': c['bases'], 'members': [effective[x] for x in sorted(effective)], 'unhandled_class_body_forms': c['unhandled_class_body_forms'], 'semantic_equivalence_asserted': False})
result = {'schema_version': 1, 'revision': REV, 'selected_backend': 'tensorflow', 'method': 'AST imports and explicit TensorFlow backend branch selection; C3 for statically resolved bases; no framework runtime execution. Private members are not enumerated except public protocol dunders listed in script. Unknown/dynamic branches remain unresolved.', 'class_exports': public, 'external_inheritance_boundaries': sorted(set((b for x in public for b in x['mro'] if b not in classes and b != 'builtins.object'))), 'inherited_member_surface_complete': False, 'member_scope': 'AST candidates with public spelling or selected protocol dunders; not all inherited members are necessarily documented public capabilities. Property accessor/overload declarations are preserved, external inheritance boundaries remain explicit.', 'unresolved_export_targets': unresolved_targets, 'unresolved_mro': unresolved_mro, 'parse_errors': parse_errors, 'parse_warnings': parse_warnings, 'dynamic_top_level_forms': dynamic_forms, 'unknown_source_conditions': unknown_conditions, 'counts': {'parsed_python_files': len(modules), 'source_classes': len(classes), 'public_class_exports': len(public), 'distinct_public_class_targets': len(set((x['target'] for x in public))), 'resolved_mro_exports': sum((x['mro_status'] == 'static_c3_resolved' for x in public)), 'member_declarations': sum((len(x['members']) for x in public)), 'inherited_member_declarations': sum((sum((y['inherited'] for y in x['members'])) for x in public)), 'unresolved_mro_exports': len(unresolved_mro), 'unresolved_symbol_targets': len(unresolved_targets), 'parse_errors': len(parse_errors)}}
p = ROOT / 'keras-inherited-members.json'
p.write_text(json.dumps(result, separators=(',', ':'), ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'counts': result['counts'], 'unresolved_examples': unresolved_mro[:8]}))
