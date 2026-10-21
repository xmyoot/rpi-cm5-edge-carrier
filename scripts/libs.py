"""Symbol library access: load symbols from .kicad_sym / embedded lib_symbols."""
import os, copy, glob
from sexp import parse, find, find1, Sym

KICAD = '/Users/hector/Applications/KiCad/KiCad.app/Contents/SharedSupport'
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
_cache = {}


def _lib_file(lib):
    p = os.path.join(KICAD, 'symbols', lib + '.kicad_sym')
    if os.path.exists(p):
        return p
    p = os.path.join(PROJ, 'hardware', 'lib', lib + '.kicad_sym')
    if os.path.exists(p):
        return p
    raise FileNotFoundError(lib)


def _load_lib(lib):
    if lib not in _cache:
        tree = parse(open(_lib_file(lib)).read())
        _cache[lib] = {s[1]: s for s in find(tree, 'symbol')}
    return _cache[lib]


def get_symbol(lib_id):
    """Return a flattened symbol definition named lib_id (handles extends)."""
    lib, name = lib_id.split(':')
    syms = _load_lib(lib)
    s = copy.deepcopy(syms[name])
    ext = find1(s, 'extends')
    if ext:
        base = copy.deepcopy(syms[ext[1]])
        # take properties from derived, graphics/pins from base
        props = find(s, 'property')
        out = [Sym('symbol'), name]
        for x in base[2:]:
            if isinstance(x, list) and x[0] == 'property':
                continue
            if isinstance(x, list) and x[0] == 'symbol':
                x[1] = x[1].replace(ext[1], name, 1)
            out.append(x)
        # insert properties after flags
        idx = 2
        while idx < len(out) and isinstance(out[idx], list) and out[idx][0] in ('pin_names', 'pin_numbers', 'exclude_from_sim', 'in_bom', 'on_board', 'power', 'in_pos_files', 'duplicate_pin_numbers_are_jumpers'):
            idx += 1
        out[idx:idx] = props
        s = out
    s[1] = lib_id
    return s


def pins(sym, unit=None):
    """List of (number, name, x, y, angle, length, etype) for a symbol (lib coords, y up)."""
    res = []
    for sub in find(sym, 'symbol'):
        parts = sub[1].rsplit('_', 2)
        u = int(parts[-2])
        if unit is not None and u not in (0, unit):
            continue
        for p in find(sub, 'pin'):
            at = find1(p, 'at')
            ln = find1(p, 'length')
            nm = find1(p, 'name')[1]
            num = find1(p, 'number')[1]
            res.append((num, nm, float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, float(ln[1]), str(p[1]), u))
    return res


def units(sym):
    us = set()
    for sub in find(sym, 'symbol'):
        u = int(sub[1].rsplit('_', 2)[-2])
        if u:
            us.add(u)
    return sorted(us) or [1]


if __name__ == '__main__':
    import sys
    for lid in sys.argv[1:]:
        s = get_symbol(lid)
        print('==', lid, 'units', units(s), 'fp:', [p[2] for p in find(s, 'property') if p[1] == 'Footprint'])
        for p in sorted(pins(s), key=lambda p: (p[7], p[0].zfill(4))):
            print('  ', p)
