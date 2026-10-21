import sys
from sexp import parse, find, find1
t = parse(open(sys.argv[1]).read())
comps = find1(t, 'components')
for c in find(comps, 'comp'):
    print('COMP', find1(c, 'ref')[1], find1(c, 'value')[1], (find1(c, 'footprint') or [0, ''])[1])
for n in find(find1(t, 'nets'), 'net'):
    nodes = [f"{find1(x,'ref')[1]}.{find1(x,'pin')[1]}" for x in find(n, 'node')]
    print('NET', find1(n, 'name')[1], ' '.join(nodes) if len(nodes) < 15 else f'<{len(nodes)} nodes> ' + ' '.join(x for x in nodes if not x.startswith('Module'))[:300])
