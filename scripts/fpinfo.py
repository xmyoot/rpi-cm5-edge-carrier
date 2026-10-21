import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
import design
A = '/Users/hector/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hardware', 'lib', 'CM5Carrier.pretty')


def load(fpid):
    lib, name = fpid.split(':')
    path = P if lib == 'CM5Carrier' else os.path.join(A, lib + '.pretty')
    return pcbnew.FootprintLoad(path, name)


if __name__ == '__main__':
    seen = set()
    for p in design.PARTS:
        if not p.footprint or p.footprint in seen:
            continue
        seen.add(p.footprint)
        fp = load(p.footprint)
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else fp.GetBoundingBox()
        mm = pcbnew.ToMM
        print(f'{p.footprint:80s} crtyd x[{mm(bb.GetLeft()):7.2f},{mm(bb.GetRight()):7.2f}] y[{mm(bb.GetTop()):7.2f},{mm(bb.GetBottom()):7.2f}]')
