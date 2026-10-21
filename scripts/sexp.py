"""Minimal S-expression reader/writer for KiCad files."""
import re

_tok = re.compile(r'\s*(\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+)', re.S)


class Sym(str):
    """Unquoted atom."""


def parse(text):
    stack, cur = [], []
    for m in _tok.finditer(text):
        t = m.group(1)
        if t == '(':
            stack.append(cur)
            cur = []
        elif t == ')':
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif t.startswith('"'):
            cur.append(t[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        else:
            cur.append(Sym(t))
    return cur[0]


def dump(node, indent=0):
    if isinstance(node, list):
        if not node:
            return '()'
        simple = all(not isinstance(x, list) for x in node)
        if simple and len(node) < 12:
            return '(' + ' '.join(dump(x) for x in node) + ')'
        pad = '\t' * (indent + 1)
        head = dump(node[0])
        parts = [head]
        for x in node[1:]:
            parts.append('\n' + pad + dump(x, indent + 1))
        return '(' + ''.join(parts[:1]) + ''.join(parts[1:]) + '\n' + '\t' * indent + ')'
    if isinstance(node, Sym):
        return str(node)
    if isinstance(node, (int, float)):
        return fmt(node)
    s = str(node).replace('\\', '\\\\').replace('"', '\\"')
    return '"' + s + '"'


def fmt(v):
    if isinstance(v, int):
        return str(v)
    s = f'{v:.4f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def find(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def find1(node, key):
    r = find(node, key)
    return r[0] if r else None
