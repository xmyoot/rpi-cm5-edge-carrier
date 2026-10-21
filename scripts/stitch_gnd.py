"""GND stitching vias on a grid wherever both outer GND pours have copper (KiCad python).

usage: stitch_gnd.py board.kicad_pcb [pitch_mm]
"""
import sys
import pcbnew


def main(path, pitch=4.0):
    b = pcbnew.LoadBoard(path)
    gnd = b.FindNet('GND')
    zones = {pcbnew.F_Cu: None, pcbnew.B_Cu: None}
    for z in b.Zones():
        if z.GetNetname() == 'GND' and z.GetLayer() in zones and z.GetAssignedPriority() == 0:
            zones[z.GetLayer()] = z
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    bb = b.GetBoardEdgesBoundingBox()
    step = pcbnew.FromMM(pitch)
    margin = pcbnew.FromMM(0.5)   # via radius 0.225 + clearance + slack
    holes = [(v.GetPosition(), v.GetDrillValue()) for v in b.GetTracks() if v.GetClass() == 'PCB_VIA']
    pads = []
    for fp in b.GetFootprints():
        for pd in fp.Pads():
            if pd.GetDrillSizeX() > 0:
                holes.append((pd.GetPosition(), max(pd.GetDrillSizeX(), pd.GetDrillSizeY())))
            pads.append(pd.GetBoundingBox())
    min_gap = pcbnew.FromMM(0.35)

    def clear(p):
        for q, d in holes:
            if (p - q).EuclideanNorm() < d // 2 + pcbnew.FromMM(0.125) + min_gap:
                return False
        for bx in pads:
            r = pcbnew.BOX2I(bx.GetPosition(), bx.GetSize())
            r.Inflate(pcbnew.FromMM(0.5))
            if r.Contains(p):
                return False
        return True
    added = 0
    y = bb.GetTop() + step // 2
    while y < bb.GetBottom():
        x = bb.GetLeft() + step // 2
        while x < bb.GetRight():
            p = pcbnew.VECTOR2I(int(x), int(y))
            if clear(p) and all(z.HitTestFilledArea(l, p, margin) for l, z in zones.items()) and \
                    all(z.GetFilledPolysList(l).Contains(pcbnew.VECTOR2I(int(x + dx), int(y + dy)))
                        for l, z in zones.items() for dx, dy in ((margin, 0), (-margin, 0), (0, margin), (0, -margin))):
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(p)
                v.SetWidth(pcbnew.FromMM(0.45))
                v.SetDrill(pcbnew.FromMM(0.25))
                v.SetNet(gnd)
                b.Add(v)
                holes.append((p, pcbnew.FromMM(0.25)))
                added += 1
            x += step
        y += step
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    others = [t for t in b.GetTracks() if t.GetNetname() != 'GND']

    def near_other(p, layer):
        # the via also lands on the opposite outer layer: keep it off foreign copper there
        opp = pcbnew.B_Cu if layer == pcbnew.F_Cu else pcbnew.F_Cu
        for t in others:
            if t.IsOnLayer(opp) and t.HitTest(p, pcbnew.FromMM(0.225 + 0.15 + (t.GetWidth() / 2e6 if t.GetClass() != 'PCB_VIA' else 0))):
                return True
        for fp in b.GetFootprints():
            for pd in fp.Pads():
                if pd.GetNetname() != 'GND' and pd.IsOnLayer(opp) and pd.HitTest(p, pcbnew.FromMM(0.4)):
                    return True
        return False

    # every GND pour island without a via gets one (e.g. the buck GND pin pocket)
    fine = pcbnew.FromMM(0.25)
    for l, z in zones.items():
        polys = z.GetFilledPolysList(l)
        for i in range(polys.OutlineCount()):
            ol = polys.Outline(i)
            if any(ol.PointInside(q) for q, _ in holes):
                continue
            bbx = ol.BBox()
            best = None
            yy = bbx.GetTop()
            while yy < bbx.GetBottom() and best is None:
                xx = bbx.GetLeft()
                while xx < bbx.GetRight():
                    p = pcbnew.VECTOR2I(int(xx), int(yy))
                    ring = [pcbnew.VECTOR2I(int(xx + dx), int(yy + dy)) for dx, dy in
                            ((margin, 0), (-margin, 0), (0, margin), (0, -margin))]
                    if clear(p) and ol.PointInside(p) and all(ol.PointInside(r) for r in ring) and \
                            not near_other(p, l):
                        best = p
                        break
                    xx += fine
                yy += fine
            if best is not None:
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(best)
                v.SetWidth(pcbnew.FromMM(0.45))
                v.SetDrill(pcbnew.FromMM(0.25))
                v.SetNet(gnd)
                b.Add(v)
                holes.append((best, pcbnew.FromMM(0.25)))
                added += 1
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(path, b)
    print('GND stitching vias added:', added)


if __name__ == '__main__':
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 4.0)
