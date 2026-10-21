"""Export the schematic netlist with kicad-cli and compare it to design.py."""
import os, subprocess, sys, collections
from sexp import parse, find, find1
import design

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hardware')
CLI = '/Users/hector/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'


def export(path):
    subprocess.run([CLI, 'sch', 'export', 'netlist', '-o', path, os.path.join(HW, 'CM5_Edge_Carrier.kicad_sch')],
                   check=True, capture_output=True)
    return parse(open(path).read())


def main():
    net = export(os.path.join(HW, 'CM5_Edge_Carrier.net'))
    got = {}
    for n in find(find1(net, 'nets'), 'net'):
        nodes = frozenset(f"{find1(x, 'ref')[1]}.{find1(x, 'pin')[1]}" for x in find(n, 'node'))
        got[nodes] = find1(n, 'name')[1]
    want = collections.defaultdict(set)
    for p in design.PARTS:
        if p.ref.startswith('#'):
            continue
        for pin, n in p.pins.items():
            if n:
                want[n].add(f'{p.ref}.{pin}')
    bad = 0
    got_sets = {s for s in got if len(s) > 1 or not got[s].startswith('unconnected')}
    for n, nodes in want.items():
        if frozenset(nodes) not in got:
            bad += 1
            match = [got[s] for s in got if nodes & s]
            print('MISMATCH', n, sorted(nodes)[:6], '->', match[:4])
    extra = [got[s] for s in got_sets if not any(frozenset(v) == s for v in want.values())]
    for e in extra:
        bad += 1
        print('EXTRA', e)
    print('nets checked', len(want), 'problems', bad)
    return bad


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
