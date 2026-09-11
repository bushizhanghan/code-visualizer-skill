#!/usr/bin/env python3
"""
code_graph.py — 解析源码并输出 Mermaid 图表文本（零依赖，仅用标准库）。

子命令:
  deps    : 整个项目的 import/依赖关系图（文件级）
  classes : 单个文件的类图（属性/方法/继承）
  calls   : 单个文件内函数调用关系图
  tree    : 目录/文件结构树

输出 Mermaid 文本到 stdout。
加 --html <path> 还会额外写一个可直接用浏览器打开的自包含 HTML 文件。
加 --limit N 限制节点数（默认 60，防止图过大）。

语言支持:
  .py          全部支持（ast 解析）
  .js/.jsx/.ts/.tsx  依赖图 + 类图（正则解析，尽力而为）
"""
import argparse
import ast
import os
import re
import sys

IGNORE_DIRS = {
    '.git', 'node_modules', 'venv', '.venv', '__pycache__', 'dist', 'build',
    '.next', '.idea', '.vscode', 'target', 'bin', 'obj', '.workbuddy',
}
PY_EXT = ('.py',)
JS_EXT = ('.js', '.jsx', '.ts', '.tsx')
ALL_EXT = PY_EXT + JS_EXT


def slug(s):
    out = re.sub(r'[^0-9A-Za-z_]', '_', s)
    return out or 'n'


def walk_files(root, exts):
    res = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            if any(f.endswith(e) for e in exts):
                res.append(os.path.join(dirpath, f))
    return res


def rel_of(path, root):
    return os.path.relpath(path, root).replace(os.sep, '/')


def module_name_of(pyfile, root):
    rel = rel_of(pyfile, root)
    if rel.endswith('__init__.py'):
        rel = rel[:-len('__init__.py')]
    else:
        rel = rel[:-3]
    return rel.rstrip('.').replace('/', '.')


# ---------- 解析层 ----------

def py_imports(path, root):
    out = []
    try:
        src = open(path, encoding='utf-8').read()
        tree = ast.parse(src)
    except Exception:
        return out
    cur_mod = module_name_of(path, root)
    parts = cur_mod.split('.') if cur_mod else []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.append(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            base = parts[:len(parts) - node.level] if node.level > 0 else []
            resolved = '.'.join(base + ([node.module] if node.module else []))
            out.append(resolved)
    return out


def js_imports(path):
    try:
        src = open(path, encoding='utf-8', errors='ignore').read()
    except Exception:
        return []
    imps = []
    pats = [
        r'import\s+[^;]*?from\s+[\'"]([^\'"]+)[\'"]',
        r'export\s+[^;]*?from\s+[\'"]([^\'"]+)[\'"]',
        r'(?:require|import)\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
    ]
    for p in pats:
        for m in re.finditer(p, src):
            imps.append(m.group(1))
    return imps


def resolve_js_target(imp, path, all_files):
    if not imp.startswith(('.', '/')):
        return None  # 裸包名（npm），跳过
    d = os.path.dirname(path)
    cand = os.path.normpath(os.path.join(d, imp))
    cands = [cand]
    for ext in JS_EXT:
        cands.append(cand + ext)
    cands.append(os.path.join(cand, 'index.ts'))
    cands.append(os.path.join(cand, 'index.tsx'))
    cands.append(os.path.join(cand, 'index.js'))
    cands.append(os.path.join(cand, 'index.jsx'))
    for c in cands:
        if c in all_files:
            return c
    return None


def py_classes(path):
    try:
        tree = ast.parse(open(path, encoding='utf-8').read())
    except Exception:
        return []
    res = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = [ast.unparse(b) for b in node.bases]
            methods = [n.name for n in node.body
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            attrs = [n.targets[0].id for n in node.body
                     if isinstance(n, ast.Assign)
                     and n.targets and isinstance(n.targets[0], ast.Name)]
            res.append((node.name, bases, methods, attrs))
    return res


def js_classes(path):
    try:
        src = open(path, encoding='utf-8', errors='ignore').read()
    except Exception:
        return []
    res = []
    for m in re.finditer(r'class\s+(\w+)(?:\s+extends\s+([\w.<>]+))?', src):
        name = m.group(1)
        base = m.group(2)
        methods = [x.group(1) for x in re.finditer(r'(?:^|\n)\s*(?:async\s+)?(\w+)\s*\(', src[m.end():])][:12]
        res.append((name, [base] if base else [], methods, []))
    return res


def py_calls(path):
    try:
        tree = ast.parse(open(path, encoding='utf-8').read())
    except Exception:
        return [], set()
    top_funcs = {n.name for n in tree.body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    top_classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
    edges = []
    for fn in tree.body:
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            callees = set()
            for node in ast.walk(fn):
                if isinstance(node, ast.Call):
                    f = node.func
                    if isinstance(f, ast.Name):
                        callees.add(f.id)
                    elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                            and f.value.id in top_classes:
                        callees.add(f'{f.value.id}.{f.attr}')
            for c in callees:
                if c in top_funcs or c in top_classes or '.' in c:
                    edges.append((fn.name, c))
    return edges, top_funcs | top_classes


# ---------- 输出层 ----------

def emit(diagram, html_path):
    print(diagram)
    if html_path:
        html = (
            '<!doctype html><html><head><meta charset="utf-8">'
            '<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>'
            '<style>body{font-family:system-ui,sans-serif;background:#fff;padding:24px}'
            '.mermaid{background:#fff}</style></head><body>'
            '<div class="mermaid">\n' + diagram + '\n</div>'
            '<script>mermaid.initialize({startOnLoad:true,theme:"default"});</script>'
            '</body></html>'
        )
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        sys.stderr.write(f'[code_graph] HTML 已写入: {html_path}\n')


def cmd_deps(args):
    root = os.path.abspath(args.path)
    py_files = walk_files(root, PY_EXT)
    js_files = walk_files(root, JS_EXT)
    all_files = set(py_files) | set(js_files)

    module_map = {}
    for pf in py_files:
        module_map[module_name_of(pf, root)] = pf

    edges = set()
    nodes = {}  # relpath -> id
    for f in all_files:
        rid = slug(rel_of(f, root))
        nodes[rel_of(f, root)] = rid
        if f.endswith(PY_EXT):
            for mod in py_imports(f, root):
                tgt = module_map.get(mod)
                if tgt and tgt != f:
                    edges.add((rel_of(f, root), rel_of(tgt, root)))
        else:
            for imp in js_imports(f):
                tgt = resolve_js_target(imp, f, all_files)
                if tgt and tgt != f:
                    edges.add((rel_of(f, root), rel_of(tgt, root)))

    lines = ['flowchart LR']
    for rel in nodes:
        lines.append(f'  {nodes[rel]}["{rel}"]')
    # 裁剪
    if len(nodes) > args.limit:
        keep = set(list(nodes)[:args.limit])
        edges = {e for e in edges if e[0] in keep and e[1] in keep}
        lines = ['flowchart LR'] + [f'  {nodes[r]}["{r}"]' for r in keep]
        sys.stderr.write(f'[code_graph] 节点超 {args.limit}，已截断。\n')
    for a, b in sorted(edges):
        lines.append(f'  {nodes[a]} --> {nodes[b]}')
    emit('\n'.join(lines), args.html)


def cmd_classes(args):
    if args.path.endswith(PY_EXT):
        data = py_classes(args.path)
    else:
        data = js_classes(args.path)
    lines = ['classDiagram']
    for name, bases, methods, attrs in data:
        lines.append(f'  class {name}')
        for m in methods:
            lines.append(f'    {name} : +{m}()')
        for a in attrs:
            lines.append(f'    {name} : -{a}')
        for b in bases:
            lines.append(f'  {b} <|-- {name}')
    emit('\n'.join(lines), args.html)


def cmd_calls(args):
    edges, tops = py_calls(args.path)
    lines = ['flowchart TD']
    for n in sorted(tops):
        lines.append(f'  {slug(n)}["{n}"]')
    for a, b in sorted(edges):
        lines.append(f'  {slug(a)} --> {slug(b)}')
    emit('\n'.join(lines), args.html)


def cmd_tree(args):
    root = os.path.abspath(args.path)
    lines = ['flowchart TD']
    counter = [0]

    def add(d, parent):
        try:
            entries = sorted(os.listdir(d))
        except Exception:
            return
        entries = [e for e in entries if e not in IGNORE_DIRS][:args.limit]
        for e in entries:
            p = os.path.join(d, e)
            counter[0] += 1
            nid = f'n{counter[0]}'
            if os.path.isdir(p):
                lines.append(f'  {nid}["📁 {e}/"]')
                add(p, nid)
            else:
                lines.append(f'  {nid}["{e}"]')
            if parent:
                lines.append(f'  {parent} --> {nid}')

    lines.append('  root["📦 ' + os.path.basename(root) + '"]')
    add(root, 'root')
    emit('\n'.join(lines), args.html)


def main():
    ap = argparse.ArgumentParser(description='code_graph: 源码可视化')
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('deps', 'classes', 'calls', 'tree'):
        sp = sub.add_parser(name)
        sp.add_argument('path', help='文件或目录路径')
        sp.add_argument('--html', help='额外输出自包含 HTML 文件')
        sp.add_argument('--limit', type=int, default=60, help='节点上限')
        sp.set_defaults(func=globals()['cmd_' + name])
    args = ap.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
