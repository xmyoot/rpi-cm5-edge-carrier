"""Place reference designators so they clear pads, other silk and the board edge (KiCad python).

Each reference is tried above, below, left and right of its courtyard; the first
spot that collides with nothing wins, otherwise the reference is hidden (it
stays on the assembly drawing via F.Fab).

usage: silk_cleanup.py board.kicad_pcb
"""
import sys
import pcbnew

SIZE = 0.8
GAP = 0.25


def mm(v):
    return pcbnew.FromMM(v)


def box(b):
    return (b.GetLeft(), b.GetTop(), b.GetRight(), b.GetBottom())


def hit(a, b, pad=0):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def main(path):
    b = pcbnew.LoadBoard(path)
    edge = box(b.GetBoardEdgesBoundingBox())
    inset = mm(0.4)
    edge = (edge[0] + inset, edge[1] + inset, edge[2] - inset, edge[3] - inset)
    obstacles = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(pcbnew.F_Cu) or p.IsOnLayer(pcbnew.F_Mask):
                obstacles.append(box(p.GetBoundingBox()))
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS:
                obstacles.append(box(g.GetBoundingBox()))
    for v in b.GetTracks():
        if v.GetClass() == 'PCB_VIA':
            obstacles.append(box(v.GetBoundingBox()))
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.F_SilkS:
            obstacles.append(box(d.GetBoundingBox()))
    placed = hidden = 0
    fps = sorted(b.GetFootprints(), key=lambda f: -f.GetBoundingBox().GetArea())
    for fp in fps:
        ref = fp.Reference()
        if fp.GetReference().startswith(('H', 'FID')):
            continue
        ref.SetVisible(True)
        ref.SetTextSize(pcbnew.VECTOR2I(mm(SIZE), mm(SIZE)))
        ref.SetTextThickness(mm(0.15))
        ref.SetTextAngleDegrees(0)
        ref.SetLayer(pcbnew.F_SilkS)
        cy = fp.GetCourtyard(pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
        cx, cyy = bb.GetCenter().x, bb.GetCenter().y
        w = ref.GetBoundingBox().GetWidth()
        h = ref.GetBoundingBox().GetHeight()
        g = mm(GAP)
        cands = [(cx, bb.GetTop() - g - h // 2, 0), (cx, bb.GetBottom() + g + h // 2, 0),
                 (bb.GetLeft() - g - w // 2, cyy, 0), (bb.GetRight() + g + w // 2, cyy, 0),
                 (bb.GetLeft() - g - h // 2, cyy, 90), (bb.GetRight() + g + h // 2, cyy, 90),
                 (bb.GetLeft() - g - w // 2, bb.GetTop() - g - h // 2, 0),
                 (bb.GetRight() + g + w // 2, bb.GetTop() - g - h // 2, 0),
                 (bb.GetLeft() - g - w // 2, bb.GetBottom() + g + h // 2, 0),
                 (bb.GetRight() + g + w // 2, bb.GetBottom() + g + h // 2, 0),
                 (cx, bb.GetTop() - 2 * g - h, 0), (cx, bb.GetBottom() + 2 * g + h, 0)]
        ok = False
        for x, y, a in cands:
            ref.SetTextAngleDegrees(a)
            ref.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
            r = box(ref.GetBoundingBox())
            if r[0] < edge[0] or r[1] < edge[1] or r[2] > edge[2] or r[3] > edge[3]:
                continue
            if any(hit(r, o, mm(0.1)) for o in obstacles):
                continue
            ok = True
            break
        if ok:
            obstacles.append(box(ref.GetBoundingBox()))
            placed += 1
        else:
            ref.SetVisible(False)
            hidden += 1
    pcbnew.SaveBoard(path, b)
    print(f'references placed {placed}, hidden {hidden}')


if __name__ == '__main__':
    main(sys.argv[1])
