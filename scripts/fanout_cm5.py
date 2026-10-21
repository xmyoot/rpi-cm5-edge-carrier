"""Escape-fanout for the two CM5 DF40 receptacles (run with KiCad's python).

Every connected pad that has no copper yet gets a short stub and a 0.4/0.2 mm
via. Inner-row pads drop their via toward the module interior; outer-row pads
drop it into the 2.4 mm channel between the two rows. Vias are staggered over
three levels so neighbours at 0.4 mm pitch keep >= 0.12 mm clearance.

usage: fanout_cm5.py in.kicad_pcb out.kicad_pcb
"""
import sys
import fnmatch
import pcbnew

DIFF = ('ETH_D*', 'USB3_0_*', 'USB2_*', 'PCIE_TX_*', 'PCIE_RX_*', 'PCIE_CLK_*')  # routed as coupled pairs instead

VIA_D, VIA_DRILL, TRACK = 0.4, 0.2, 0.15
LEVELS_INNER = (0.85, 1.55, 2.25)   # mm beyond the inner pad end, toward module interior
LEVELS_GAP = (0.34, 1.19, 2.04)     # mm beyond the outer pad end, into the inter-row channel


def mm(v):
    return pcbnew.FromMM(v)


def main(src, dst):
    b = pcbnew.LoadBoard(src)
    fp = b.FindFootprintByReference('Module1')
    used = set()
    for t in b.GetTracks():
        for p in fp.Pads():
            if t.GetNetCode() == p.GetNetCode() and (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd())):
                used.add(p.GetNumber())
    pads = [p for p in fp.Pads() if p.GetNetname() and not p.GetNetname().startswith('unconnected')]
    ys = sorted({round(pcbnew.ToMM(p.GetPosition().y), 2) for p in pads})
    # rows: A outer < A inner < B inner < B outer (board Y)
    a_out, a_in, b_in, b_out = ys
    added = 0
    for p in pads:
        if p.GetNumber() in used or any(fnmatch.fnmatch(p.GetNetname(), d) for d in DIFF):
            continue
        x = pcbnew.ToMM(p.GetPosition().x)
        y = round(pcbnew.ToMM(p.GetPosition().y), 2)
        n = int(p.GetNumber())
        idx = ((n - 1) // 2) % 3
        half = 0.35
        if y == a_in:
            start, d, lv = y + half, +1, LEVELS_INNER
        elif y == a_out:
            start, d, lv = y + half, +1, LEVELS_GAP
        elif y == b_in:
            start, d, lv = y - half, -1, LEVELS_INNER
        else:
            start, d, lv = y - half, -1, LEVELS_GAP
        vy = start + d * lv[idx]
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(mm(x), mm(y)))
        t.SetEnd(pcbnew.VECTOR2I(mm(x), mm(vy)))
        t.SetWidth(mm(TRACK))
        t.SetLayer(pcbnew.F_Cu)
        t.SetNet(p.GetNet())
        b.Add(t)
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(vy)))
        v.SetWidth(mm(VIA_D))
        v.SetDrill(mm(VIA_DRILL))
        v.SetNet(p.GetNet())
        b.Add(v)
        added += 1
    pcbnew.SaveBoard(dst, b)
    print('fanout vias added:', added)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
