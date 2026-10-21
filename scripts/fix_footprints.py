"""Post-process copied CM5IO footprints for this project."""
import os
from sexp import parse, dump, find, find1, Sym as S
LIB = os.path.join(os.path.dirname(__file__), '..', 'hardware', 'lib', 'CM5Carrier.pretty')


def load(n):
    return parse(open(os.path.join(LIB, n + '.kicad_mod')).read())


def save(n, t):
    open(os.path.join(LIB, n + '.kicad_mod'), 'w').write(dump(t) + '\n')


def model(path, off, rot):
    return [S('model'), path, [S('offset'), [S('xyz')] + list(off)], [S('scale'), [S('xyz'), 1, 1, 1]],
            [S('rotate'), [S('xyz')] + list(rot)]]


# CM5 module: rename, add module STEP above the two DF40 receptacles
t = load('RPi_CM5_DF40')
t[1] = 'RPi_CM5_DF40'
t = [x for x in t if not (isinstance(x, list) and x[0] == 'model' and 'RPi_CM5' in x[1])]
t = [x for x in t if not (isinstance(x, list) and x and x[0] == 'pad' and x[2] == 'np_thru_hole')]
t.append(model('${KIPRJMOD}/lib/3dmodels/RPi_CM5.step', (36.5, -3.5, 1.5), (0, 0, -90)))
for p in find(t, 'property'):
    if p[1] == 'Footprint':
        p[2] = 'CM5Carrier:RPi_CM5_DF40'
attr = find1(t, 'attr')
if attr and 'allow_soldermask_bridges' not in [str(a) for a in attr]:
    attr.append(S('allow_soldermask_bridges'))
save('RPi_CM5_DF40', t)

# M.2: keep 2230/2242 standoffs only, drop 2260/2280 graphics
t = load('M.2_M_Key_2242')
t[1] = 'M.2_M_Key_2242'


def ys(node):
    out = []
    for k in ('start', 'end', 'at', 'center', 'mid'):
        e = find1(node, k)
        if e:
            out.append(float(e[2]))
    for pts in find(node, 'pts'):
        out += [float(xy[2]) for xy in find(pts, 'xy')]
    return out


keep = []
for x in t:
    if isinstance(x, list) and x and x[0] == 'pad' and x[1] in ('M3', 'M4'):
        continue
    if isinstance(x, list) and x and x[0] == 'fp_text' and x[2] in ('2260', '2280'):
        continue
    if isinstance(x, list) and x and x[0] in ('fp_line', 'fp_rect', 'fp_poly', 'fp_arc', 'fp_circle'):
        if ys(x) and max(ys(x)) > 46:
            continue
    keep.append(x)
for p in find(keep, 'property'):
    if p[1] == 'Footprint':
        p[2] = 'CM5Carrier:M.2_M_Key_2242'
attr = find1(keep, 'attr')
if attr is None:
    keep.append([S('attr'), S('smd'), S('allow_soldermask_bridges')])
elif 'allow_soldermask_bridges' not in [str(a) for a in attr]:
    attr.append(S('allow_soldermask_bridges'))
save('M.2_M_Key_2242', keep)
print('ok')
