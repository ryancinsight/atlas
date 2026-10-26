"""Static, exact-source JAX autodoc audit. No JAX import or runtime execution."""
from __future__ import annotations
import argparse, ast, collections, hashlib, json, re, urllib.request
from dataclasses import dataclass
from pathlib import Path
REV = 'dc4af684446e65ee98eee8090e1ff6f8211473fb'
TREE = 'bb9547a8148e50cab9c20f8521bf7af7c752b6f6'
BASE = 'https://github.com/jax-ml/jax/blob/' + REV + '/'

@dataclass
class Located:
    module: str
    name: str
    path: str
    node: ast.AST
    chain: list

class Sources:

    def __init__(self, cache, fetch=False):
        self.cache = cache
        self.fetch = fetch
        self.used = {}
        self.modules = {}
        tree = json.loads((cache / 'tree.json').read_text(encoding='utf-8'))
        assert tree['sha'] == TREE and (not tree.get('truncated'))
        self.blobs = {e['path']: e for e in tree['tree'] if e['type'] == 'blob'}

    def read(self, path):
        file = self.cache / path
        if not file.exists():
            if not self.fetch:
                raise ValueError('uncached:' + path)
            file.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen('https://raw.githubusercontent.com/jax-ml/jax/' + REV + '/' + path, timeout=30) as r:
                file.write_bytes(r.read())
        data = file.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\x00' + data).hexdigest()
        assert blob == self.blobs[path]['sha'], ('source-mismatch', path)
        self.used[path] = {'path': path, 'git_blob_sha': blob, 'sha256': hashlib.sha256(data).hexdigest(), 'source': BASE + path}
        return data.decode()

    def module(self, module):
        if module in self.modules:
            return self.modules[module]
        prefix = module.replace('.', '/')
        path = next((p for p in [prefix + '.py', prefix + '/__init__.py', prefix + '.pyi', prefix + '/__init__.pyi'] if p in self.blobs), None)
        if path is None:
            raise ValueError('external-or-generated-module:' + module)
        source = self.read(path)
        tree = ast.parse(source)
        bindings = {}
        imports = []

        def scan(nodes):
            for n in nodes:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    bindings[n.name] = n
                elif isinstance(n, ast.ImportFrom):
                    if n.level:
                        parts = module.split('.') if path.endswith('/__init__.py') else module.split('.')[:-1]
                        prefix = '.'.join(parts[:len(parts) - n.level + 1])
                        m = '.'.join((x for x in (prefix, n.module) if x))
                    else:
                        m = n.module or ''
                    for a in n.names:
                        if a.name == '*':
                            imports.append(m)
                        else:
                            bindings[a.asname or a.name] = ('import', m, a.name, n)
                elif isinstance(n, ast.Import):
                    for a in n.names:
                        bindings[a.asname or a.name.split('.')[0]] = ('module', a.name if a.asname else a.name.split('.')[0], n)
                elif isinstance(n, ast.Assign):
                    for target in n.targets:
                        if isinstance(target, ast.Name):
                            bindings[target.id] = n
                elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                    bindings[n.target.id] = n
                elif isinstance(n, ast.If):
                    scan(n.body)
                    scan(n.orelse)
        scan(tree.body)
        result = (path, tree, bindings, imports)
        self.modules[module] = result
        return result

    def resolve(self, module, name, chain=None):
        chain = list(chain or [])
        key = module + '.' + name
        if key in chain:
            raise ValueError('alias-cycle:' + key)
        chain.append(key)
        path, tree, bindings, stars = self.module(module)
        first, sep, rest = name.partition('.')
        value = bindings.get(first)
        if value is None:
            if (module + '.' + first).replace('.', '/') + '.py' in self.blobs or (module + '.' + first).replace('.', '/') + '/__init__.py' in self.blobs:
                if rest:
                    return self.resolve(module + '.' + first, rest, chain)
            raise ValueError('unresolved-binding:' + key + (' star-imports:' + ','.join(stars) if stars else ''))
        if isinstance(value, tuple):
            if value[0] == 'import':
                _, m, n, _ = value
                return self.resolve(m, n + ('.' + rest if rest else ''), chain)
            _, m, _ = value
            if rest:
                return self.resolve(m, rest, chain)
            raise ValueError('module-not-class:' + key)
        if rest:
            if isinstance(value, ast.ClassDef):
                member = next((n for n in value.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == rest), None)
                if member:
                    return Located(module, name, path, member, chain)
            raise ValueError('unresolved-nested:' + key)
        if isinstance(value, (ast.Assign, ast.AnnAssign)):
            rhs = value.value
            if isinstance(rhs, (ast.Name, ast.Attribute)):
                expr = ast.unparse(rhs)
                head, *tail = expr.split('.')
                local = bindings.get(head)
                if isinstance(local, tuple):
                    if local[0] == 'module':
                        return self.resolve(local[1], '.'.join(tail), chain)
                    if local[0] == 'import':
                        return self.resolve(local[1], '.'.join([local[2], *tail]), chain)
                if expr != first:
                    return self.resolve(module, expr, chain)
        return Located(module, first, path, value, chain)

def options_at(source, line):
    lines = source.splitlines()
    indent = len(lines[line - 1]) - len(lines[line - 1].lstrip())
    opts = {}
    for following in lines[line:]:
        if not following.strip():
            continue
        if len(following) - len(following.lstrip()) <= indent:
            break
        m = re.match('\\s*:([\\w-]+):\\s*(.*)', following)
        if m:
            opts[m.group(1)] = m.group(2)
        elif following.lstrip().startswith('.. '):
            break
    return opts

def member_nodes(location, opts, sources=None):
    node = location.node
    if not isinstance(node, ast.ClassDef):
        return ([], ['target is static ' + type(node).__name__ + ', not class; generated/native/alias resolution required'])
    requested = opts.get('members', '').strip()
    explicit = [s.strip() for s in requested.split(',') if s.strip()]
    special = [s.strip() for s in opts.get('special-members', '').split(',') if s.strip()]
    known = {}
    for n in node.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(n) or ''
            if not n.name.startswith('_') or n.name in special:
                known[n.name] = {'symbol': n.name, 'kind': 'property' if any((ast.unparse(x).endswith('property') or ast.unparse(x).endswith('cached_property') for x in n.decorator_list)) else 'method', 'line': n.lineno, 'documented': bool(doc), 'signature': ast.unparse(n.args) if hasattr(n, 'args') else None, 'source': BASE + location.path + '#L' + str(n.lineno)}
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and (not n.target.id.startswith('_')):
            known[n.target.id] = {'symbol': n.target.id, 'kind': 'attribute', 'line': n.lineno, 'documented': 'selection-needs-class-doc-or-source-comment-review', 'annotation': ast.unparse(n.annotation), 'source': BASE + location.path + '#L' + str(n.lineno)}
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and (not t.id.startswith('_')):
                    known[t.id] = {'symbol': t.id, 'kind': 'attribute', 'line': n.lineno, 'documented': 'selection-needs-source-comment-review', 'source': BASE + location.path + '#L' + str(n.lineno)}
    names = set(explicit + special) if explicit else set(known)
    missing = sorted(names - set(known))
    if missing and sources:
        for base in node.bases:
            if isinstance(base, (ast.Name, ast.Attribute)):
                try:
                    parent = sources.resolve(location.module, ast.unparse(base))
                    inherited, _ = member_nodes(parent, {'members': ','.join(missing)}, None)
                    for item in inherited:
                        known[item['symbol']] = dict(item, inherited_from=parent.module + '.' + parent.name)
                except (ValueError, KeyError):
                    pass
        missing = sorted(names - set(known))
    out = [known[x] for x in sorted(names & set(known))]
    issues = ['member requires inherited/generated resolution: ' + x for x in missing]
    if 'inherited-members' in opts:
        issues.append('inherited-members requires full MRO resolution')
    if not explicit and any((x['documented'] is not True for x in out)):
        issues.append('default autodoc source-comment/dataclass/enum attribute selection requires review')
    return (out, issues)

def run(inventory, cache, fetch, out):
    sources = Sources(cache, fetch)
    data = json.loads(inventory.read_text(encoding='utf-8'))
    config = sources.read('docs/conf.py')
    config_ast = ast.parse(config)
    names = {t.id for n in config_ast.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    assert 'autodoc_default_options' not in names and 'autodoc_default_flags' not in names
    extension = sources.read('docs/sphinxext/jax_extensions.py')
    assert 'autodoc-process' not in extension and 'autodoc-skip' not in extension
    occurrences = {(o['path'], o['line']): r['symbol'] for r in data['records'] for o in r['occurrences']}
    dispositions = []
    new = []
    for number, gap in enumerate(data['extraction_gaps'], 1):
        source = sources.read(gap['path'])
        opts = options_at(source, gap['line'])
        symbol = occurrences[gap['path'], gap['line']]
        row = {'id': f'JAX-AUTODOC-{number:03d}', 'old_gap': gap, 'symbol': symbol, 'options': opts, 'source': BASE + gap['path'] + '#L' + str(gap['line']), 'generated_members': [], 'issues': []}
        if gap['directive'] == 'automodule' and (not any((x in opts for x in ['members', 'special-members', 'private-members', 'inherited-members']))):
            row['state'] = 'closed_false_positive_no_member_expansion_requested'
            row['basis'] = 'Exact docs/conf.py has no autodoc_default_options/flags; directive has no member options. Module docstring already scanned; public-surface completeness remains independently open.'
        elif gap['directive'] == 'automodule':
            try:
                path, tree, bindings, stars = sources.module(symbol)
                for name, node in bindings.items():
                    if name.startswith('_'):
                        continue
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        row['generated_members'].append({'symbol': symbol + '.' + name, 'kind': type(node).__name__, 'source': BASE + path + '#L' + str(node.lineno), 'signature': ast.unparse(node.args) if hasattr(node, 'args') else None, 'selection': 'local definition; :undoc-members: includes absent docstrings'})
                    elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                        row['issues'].append('assignment export requires callable/attribute __module__ and source-comment review: ' + name)
                if stars:
                    row['issues'].append('wildcard imports:' + ','.join(stars))
                row['state'] = 'partially_expanded_static_local_definitions'
            except ValueError as error:
                row['state'] = 'open'
                row['issues'].append(str(error))
        else:
            try:
                module, name = symbol.rsplit('.', 1)
                loc = sources.resolve(module, name)
                row['resolved_binding'] = {'path': loc.path, 'line': loc.node.lineno, 'node_kind': type(loc.node).__name__, 'alias_chain': loc.chain, 'source': BASE + loc.path + '#L' + str(loc.node.lineno)}
                members, issues = member_nodes(loc, opts, sources)
                row['generated_members'] = [dict(m, symbol=symbol + '.' + m['symbol']) for m in members]
                row['issues'] = issues
                row['state'] = 'expanded_requested_member_set' if not issues else 'partially_expanded_static_class'
            except (ValueError, KeyError) as error:
                row['state'] = 'open'
                row['issues'].append(str(error))
        new.extend(row['generated_members'])
        dispositions.append(row)
    out.mkdir(parents=True, exist_ok=True)
    result = {'framework': 'jax', 'version': data['version'], 'source_revision': REV, 'source_tree': TREE, 'input_inventory_sha256': hashlib.sha256(inventory.read_bytes()).hexdigest(), 'mode': 'read-only static proposal; not integrated inventory or runtime proof', 'public_surface_complete': False, 'original_gap_count': len(data['extraction_gaps']), 'states': dict(collections.Counter((r['state'] for r in dispositions))), 'generated_member_candidates': len(new), 'dispositions': dispositions, 'sources': sorted(sources.used.values(), key=lambda r: r['path']), 'remaining_scope': ['whole public export reconciliation', 'complete inherited/native/generated member selection', 'notebook/prose workflows and deprecation review', 'all API semantic axes and executed differential/device qualification']}
    (out / 'autodoc-dispositions.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ['dispositions', 'sources']}, indent=2))
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--fetch', action='store_true')
    a = p.parse_args()
    run(a.inventory, a.cache, a.fetch, a.out)
