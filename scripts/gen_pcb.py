"""Build the unrouted PCB from design.py + the schematic netlist (run with KiCad's python).

Placement is hand-planned (see PLACE). Nets come from the netlist that
kicad-cli exports from the schematic, so pad nets match the schematic exactly
and footprint paths are linked for schematic<->PCB parity.
"""
import os
import sys
import json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew
from sexp import parse, find, find1
import design
import schgen
from libs import get_symbol

HW = os.path.join(HERE, '..', 'hardware')
STOCK = '/Users/hector/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
PROJ_LIB = os.path.join(HW, 'lib', 'CM5Carrier.pretty')
OUT = os.path.join(HW, 'CM5_Edge_Carrier.kicad_pcb')
OX, OY = 100.0, 100.0          # board origin on the page
W, H = 100.0, 85.0             # board size (mm)

# ref: (x, y, rot)   board coordinates, mm from the top-left corner, all top side
PLACE = {
    # --- compute module + mounting
    'Module1': (9.0, 26.0, 270),
    'H1': (4.0, 4.0, 0), 'H2': (96.0, 4.0, 0), 'H3': (4.0, 81.0, 0), 'H4': (96.0, 81.0, 0),
    'H5': (9.0, 26.0, 0), 'H6': (9.0, 59.0, 0), 'H7': (57.0, 26.0, 0), 'H8': (57.0, 59.0, 0),
    'FID1': (2.5, 36.0, 0), 'FID2': (97.5, 48.0, 0), 'FID3': (57.5, 83.0, 0),
    # --- USB-C PD input + 5 V buck (top-left). Hand-placed power stage:
    #     J1 -> TVS/bulk caps -> U2 VIN, SW -> L1 -> output caps, all on short F.Cu pours
    'J1': (3.1, 13.0, 270),
    'D1': (9.8, 4.6, 90), 'C1': (12.8, 4.6, 90), 'C2': (15.4, 4.6, 90), 'C4': (18.0, 4.6, 90),
    'C5': (20.2, 4.9, 90),
    'U2': (18.0, 9.6, 180), 'L1': (25.2, 9.6, 0), 'C6': (18.8, 12.4, 0),
    'R7': (14.6, 7.55, 0), 'R6': (14.6, 8.65, 0), 'R4': (14.6, 9.75, 0), 'R5': (14.6, 10.85, 0),
    'C11': (19.2, 15.8, 270), 'C7': (21.0, 15.8, 270), 'C8': (23.2, 15.8, 270), 'C9': (25.4, 15.8, 270),
    'C10': (27.6, 15.8, 270),
    'U1': (12.2, 16.2, 0),
    'R1': (9.4, 20.6, 0), 'C3': (11.3, 20.6, 0), 'R2': (13.2, 20.6, 0), 'R3': (15.1, 20.6, 0), 'D2': (17.8, 20.6, 0),
    # --- CM5 bulk decoupling / misc on the left strip
    'C20': (2.6, 41.0, 90), 'C21': (2.6, 45.0, 90), 'C22': (2.6, 48.5, 90), 'C23': (2.6, 50.5, 90),
    'R11': (2.6, 30.5, 90),
    # --- Ethernet (rear edge)
    'J4': (39.0, 10.8, 180),
    'U8': (50.2, 18.6, 0), 'U9': (28.0, 20.4, 0),
    'R22': (50.6, 6.6, 0), 'R23': (50.6, 8.2, 0), 'C35': (50.6, 10.2, 0),
    # --- mic-array header + I2S termination + rear connectors
    'J6': (58.0, 8.0, 90),
    'R30': (57.0, 13.6, 0), 'R31': (59.2, 13.6, 0), 'R32': (61.4, 13.6, 0),
    'J7': (80.3, 3.4, 180), 'R33': (79.6, 8.8, 0), 'R34': (81.8, 8.8, 0),
    'J9': (88.4, 3.4, 180),
    'J8': (97.5, 11.0, 0),
    'J10': (96.5, 23.0, 90), 'R35': (92.0, 21.0, 90),
    # --- front edge: USB 3.0, service USB-C
    'J3': (29.0, 75.5, 0),
    'U4': (17.5, 74.0, 0), 'C31': (14.2, 74.0, 90), 'R21': (17.5, 77.0, 0),
    'C32': (15.2, 69.2, 0), 'C33': (19.5, 66.6, 0), 'C34': (16.5, 66.6, 0),
    'J5': (44.0, 81.9, 0), 'U10': (44.0, 71.0, 90), 'R24': (39.5, 75.0, 90), 'R25': (48.5, 75.0, 90),
    # --- status LEDs and buttons (front-left)
    'D3': (3.2, 64.6, 0), 'R12': (6.6, 64.6, 0), 'D4': (3.2, 67.0, 0), 'R13': (6.6, 67.0, 0),
    'SW1': (9.4, 71.0, 0), 'SW2': (9.4, 76.0, 0),
    # --- M.2 NVMe + its 3.3 V buck (right)
    'J2': (80.0, 68.5, 180),
    'D5': (65.6, 64.4, 0), 'R20': (68.2, 64.4, 0), 'C30': (71.0, 64.4, 0),
    # mirrored so LX/EN face the inductor on the left and the PCIe pairs keep a clear channel under J2
    'U3': (78.0, 80.0, 180), 'L2': (71.0, 79.75, 180), 'C12': (80.6, 80.0, 270), 'R8': (76.0, 82.8, 270),
    'R9': (83.2, 79.4, 90), 'R10': (83.2, 82.0, 90), 'C13': (84.6, 80.6, 90),
    'C14': (65.8, 79.75, 270), 'C15': (63.8, 79.75, 270), 'C16': (61.8, 79.75, 270), 'C17': (59.9, 79.75, 270),
}

NETCLASSES = {
    # name: (track, clearance, via_dia, via_drill, diff_width, diff_gap, patterns)
    'Default': (0.15, 0.12, 0.45, 0.25, None, None, []),
    'Power': (0.6, 0.12, 0.6, 0.3, None, None, ['+5V', 'VBUS', 'VBUS_USB', '+3V3_M2', '/Power/SW_5V',
                                              '/Power/LX_M2', 'SVC_VBUS', '+3V3']),
    'GND': (0.3, 0.12, 0.45, 0.25, None, None, ['GND']),
    # widths solved for JLC04161H-3313 (L1 over 0.0994 mm 3313 prepreg, er 4.1)
    'USB_90R': (0.18, 0.12, 0.45, 0.25, 0.18, 0.15, ['USB3_*', 'USB2_*']),
    'PCIe_85R': (0.20, 0.12, 0.45, 0.25, 0.20, 0.15, ['PCIE_TX_*', 'PCIE_RX_*', 'PCIE_CLK_*']),
    'ETH_100R': (0.16, 0.12, 0.45, 0.25, 0.16, 0.18, ['ETH_D*']),
}


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def load_fp(fpid):
    lib, name = fpid.split(':')
    path = PROJ_LIB if lib == 'CM5Carrier' else os.path.join(STOCK, lib + '.pretty')
    fp = pcbnew.FootprintLoad(path, name)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def netlist_map():
    t = parse(open(os.path.join(HW, 'CM5_Edge_Carrier.net')).read())
    pins = {}
    for n in find(find1(t, 'nets'), 'net'):
        name = find1(n, 'name')[1]
        for node in find(n, 'node'):
            pins[(find1(node, 'ref')[1], find1(node, 'pin')[1])] = name
    return pins


# ESD arrays are flow-through parts: tie each channel's paired pads straight under the body
FLOW = {ref: (('1', '10'), ('2', '9'), ('4', '7'), ('5', '6')) for ref in ('U8', 'U9')}
FLOW['U10'] = (('1', '6'), ('3', '4'))


def add_flow_through(board):
    for ref, links in FLOW.items():
        fp = board.FindFootprintByReference(ref)
        pads = {p.GetNumber(): p for p in fp.Pads()}
        for a, b in links:
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pads[a].GetPosition())
            t.SetEnd(pads[b].GetPosition())
            t.SetWidth(mm(0.15 if ref != 'U10' else 0.2))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(pads[a].GetNet())
            t.SetLocked(True)
            board.Add(t)


def add_outline(board):
    r = 3.0
    k = r * (1 - 0.70710678)
    segs = [((r, 0), (W - r, 0)), ((W, r), (W, H - r)), ((W - r, H), (r, H)), ((0, H - r), (0, r))]
    for a, b in segs:
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(*a))
        s.SetEnd(pt(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)
    arcs = (((0, r), (k, k), (r, 0)), ((W - r, 0), (W - k, k), (W, r)),
            ((W, H - r), (W - k, H - k), (W - r, H)), ((r, H), (k, H - k), (0, H - r)))
    for a0, am, a1 in arcs:
        a = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        a.SetArcGeometry(pt(*a0), pt(*am), pt(*a1))
        a.SetLayer(pcbnew.Edge_Cuts)
        a.SetWidth(mm(0.1))
        board.Add(a)


def add_zone(board, net, layer, poly, priority=0, clearance=0.25, min_w=0.2, solid=False):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet(net))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in poly:
        ol.Append(mm(OX + x), mm(OY + y))
    z.SetAssignedPriority(priority)
    z.SetLocalClearance(mm(clearance))
    z.SetMinThickness(mm(min_w))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid else pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.25))
    z.SetThermalReliefSpokeWidth(mm(0.3))
    board.Add(z)
    return z


def add_via(board, net, x, y, d=0.45, drill=0.25):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pt(x, y))
    v.SetWidth(mm(d))
    v.SetDrill(mm(drill))
    v.SetNet(board.FindNet(net))
    board.Add(v)


def add_track(board, net, pts, w, layer=pcbnew.F_Cu):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pt(*a))
        t.SetEnd(pt(*b))
        t.SetWidth(mm(w))
        t.SetLayer(layer)
        t.SetNet(board.FindNet(net))
        board.Add(t)


def power_stage(board):
    """Top-layer pours and stitching for both buck converters (hand layout)."""
    Z = dict(priority=2, clearance=0.2, min_w=0.2, solid=True)
    # 5 V buck: VBUS input strip, switch node, local +5V output
    add_zone(board, 'VBUS', pcbnew.F_Cu, [(8.3, 5.1), (20.0, 5.1), (20.0, 9.0), (18.3, 9.0), (18.3, 7.4),
                                          (9.4, 7.4), (9.4, 11.0), (6.4, 11.0), (6.4, 10.3), (8.3, 10.3)], **Z)
    add_track(board, 'GND', [(6.78, 9.8), (6.2, 8.68)], 0.3)
    add_zone(board, '/Power/SW_5V', pcbnew.F_Cu, [(19.6, 9.1), (23.6, 9.1), (23.6, 10.1), (21.2, 10.1), (21.2, 12.9),
                                                  (18.95, 12.9), (18.95, 11.9), (20.3, 11.9), (20.3, 10.1), (19.6, 10.1)], **Z)
    add_zone(board, '+5V', pcbnew.F_Cu, [(26.9, 7.6), (29.4, 7.6), (29.4, 15.4), (18.6, 15.4), (18.6, 13.3),
                                         (26.9, 13.3)], **Z)
    for x, y in ((20.2, 13.75), (22.1, 13.75), (24.3, 13.75), (26.5, 13.75), (28.6, 12.0), (28.6, 13.75)):
        add_via(board, '+5V', x, y)
    for x, y in ((19.1, 11.35), (12.8, 1.5), (15.4, 1.5), (18.0, 1.5), (21.0, 2.6), (19.2, 17.6), (22.1, 17.9), (24.3, 17.9),
                 (26.5, 17.9), (28.7, 17.9)):
        add_via(board, 'GND', x, y)
    # 3.3 V M.2 buck (U3 mirrored): LX straight left into L2, EN down to its pull-down, +3V3_M2 pour on the left
    add_track(board, '/Power/LX_M2', [(77.0, 79.75), (76.0, 79.75)], 0.35)
    add_track(board, '/Power/LX_M2', [(76.0, 79.75), (73.25, 79.75)], 0.8)
    add_track(board, 'PCIE_PWR_EN', [(77.0, 80.25), (76.45, 80.25), (76.0, 80.7), (76.0, 82.32)], 0.15)
    add_zone(board, '+3V3_M2', pcbnew.F_Cu, [(59.0, 77.3), (70.3, 77.3), (70.3, 81.4), (67.4, 81.4), (67.4, 79.2),
                                             (59.0, 79.2)], **Z)
    for x, y in ((59.6, 77.65), (61.6, 77.65), (63.6, 77.65), (65.6, 77.65), (67.6, 77.65)):
        add_via(board, '+3V3_M2', x, y)
    for x, y in ((59.9, 81.6), (61.8, 81.6), (63.8, 81.6), (65.8, 81.6), (76.0, 84.1), (80.6, 82.4), (83.2, 83.9)):
        add_via(board, 'GND', x, y)
    add_via(board, '+5V', 80.6, 77.9)


def add_text(board, txt, x, y, size=1.2, layer=pcbnew.F_SilkS, bold=False, rot=0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetPosition(pt(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * (0.2 if bold else 0.15)))
    t.SetTextAngleDegrees(rot)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


def setup_stackup(board):
    board.SetCopperLayerCount(4)
    board.SetLayerName(pcbnew.In1_Cu, 'In1.Cu')
    board.SetLayerName(pcbnew.In2_Cu, 'In2.Cu')
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(mm(1.6))
    ds.m_TrackMinWidth = mm(0.1)
    ds.m_MinClearance = mm(0.1)
    ds.m_ViasMinSize = mm(0.4)
    ds.m_MinThroughDrill = mm(0.2)
    ds.m_ViasMinAnnularWidth = mm(0.1)
    ds.m_CopperEdgeClearance = mm(0.3)
    ds.m_HoleClearance = mm(0.15)
    ds.m_HoleToHoleMin = mm(0.25)
    ds.m_SolderMaskMinWidth = mm(0.1)


def main():
    nets = netlist_map()
    board = pcbnew.NewBoard(OUT)
    setup_stackup(board)
    # nets
    for name in sorted(set(nets.values())):
        board.Add(pcbnew.NETINFO_ITEM(board, name))
    sheet_uuid = {n: schgen.uid('sheetsym/' + n) for n in ('Power', 'Compute', 'HighSpeed', 'PeriphIO')}
    missing = []
    for p in design.PARTS:
        if not p.footprint:
            continue
        fp = load_fp(p.footprint)
        fp.SetReference(p.ref)
        fp.SetValue(p.value)
        sym = get_symbol(p.lib_id)
        desc = p.desc or next((x[2] for x in find(sym, 'property') if x[1] == 'Description'), '')
        fp.GetField(pcbnew.FIELD_T_DESCRIPTION).SetText(desc)
        if p.ref.startswith(('H', 'FID')):
            fp.Reference().SetVisible(False)
        for k, v in p.fields.items():
            if True:
                fp.SetField(k, v)
                f = fp.GetField(k)
                f.SetVisible(False)
                f.SetLayer(pcbnew.F_Fab)
        sym_uuid = schgen.uid('sym/' + p.ref)
        fp.SetPath(pcbnew.KIID_PATH(f'/{sheet_uuid[p.sheet_name]}/{sym_uuid}'))
        fp.SetSheetname(p.sheet_name)
        fp.SetSheetfile({'Power': 'power.kicad_sch', 'Compute': 'compute.kicad_sch',
                         'HighSpeed': 'highspeed.kicad_sch', 'PeriphIO': 'periph_io.kicad_sch'}[p.sheet_name])
        if p.ref.startswith(('H', 'FID')):
            fp.SetExcludedFromBOM(True)
        if p.ref not in PLACE:
            missing.append(p.ref)
            x, y, r = W + 10, 10 + len(missing) * 6, 0
        else:
            x, y, r = PLACE[p.ref]
        board.Add(fp)
        fp.SetPosition(pt(x, y))
        fp.SetOrientationDegrees(r)
        for pad in fp.Pads():
            n = nets.get((p.ref, pad.GetNumber()))
            if n:
                pad.SetNet(board.FindNet(n))
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
        fp.Reference().SetTextThickness(mm(0.12))
    if missing:
        print('NOT PLACED:', missing)
    add_flow_through(board)
    add_outline(board)
    full = [(0, 0), (W, 0), (W, H), (0, H)]
    add_zone(board, 'GND', pcbnew.In1_Cu, full)
    add_zone(board, '+5V', pcbnew.In2_Cu, full, priority=0)
    add_zone(board, '+3V3_M2', pcbnew.In2_Cu, [(58.5, 63.5), (93.0, 63.5), (93.0, 78.0), (58.5, 78.0)], priority=1)
    power_stage(board)
    add_zone(board, 'GND', pcbnew.F_Cu, full, priority=0)
    add_zone(board, 'GND', pcbnew.B_Cu, full, priority=0)
    add_text(board, 'CM5 EDGE-AUDIO CARRIER', 75.0, 16.2, 1.5, bold=True)
    add_text(board, 'Rev 1.0  |  H. Jimenez  |  2026', 75.0, 18.8, 1.0)
    pcbnew.SaveBoard(OUT, board)
    add_stackup(OUT)
    write_project()
    print('saved', OUT)


STACKUP = '''		(stackup
			(layer "F.SilkS" (type "Top Silk Screen"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (color "Green") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 1" (type "prepreg") (thickness 0.0994) (material "3313") (epsilon_r 4.1) (loss_tangent 0.02))
			(layer "In1.Cu" (type "copper") (thickness 0.0152))
			(layer "dielectric 2" (type "core") (thickness 1.265) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
			(layer "In2.Cu" (type "copper") (thickness 0.0152))
			(layer "dielectric 3" (type "prepreg") (thickness 0.0994) (material "3313") (epsilon_r 4.1) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.035))
			(layer "B.Mask" (type "Bottom Solder Mask") (color "Green") (thickness 0.01))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen"))
			(copper_finish "ENIG")
			(dielectric_constraints yes)
		)
'''


def add_stackup(path):
    """JLCPCB JLC04161H-3313 (1.6 mm, 4 layer, impedance controlled)."""
    t = open(path).read()
    if '(stackup' not in t:
        t = t.replace('\t(setup\n', '\t(setup\n' + STACKUP, 1)
    t = t.replace('(4 "In1.Cu" signal)', '(4 "In1.Cu" power "GND")').replace('(6 "In2.Cu" signal)', '(6 "In2.Cu" power "PWR")')
    open(path, 'w').write(t)


def write_project():
    pro = os.path.join(HW, 'CM5_Edge_Carrier.kicad_pro')
    d = json.load(open(pro))
    ns = d.setdefault('net_settings', {})
    classes = []
    for name, (tw, cl, vd, vdr, dw, dg, pats) in NETCLASSES.items():
        c = {'name': name, 'track_width': tw, 'clearance': cl, 'via_diameter': vd, 'via_drill': vdr,
             'microvia_diameter': 0.3, 'microvia_drill': 0.1, 'wire_width': 6, 'bus_width': 12,
             'line_style': 0, 'schematic_color': 'rgba(0, 0, 0, 0.000)', 'pcb_color': 'rgba(0, 0, 0, 0.000)',
             'priority': 2147483647 if name == 'Default' else len(classes)}
        if dw:
            c['diff_pair_width'] = dw
            c['diff_pair_gap'] = dg
            c['diff_pair_via_gap'] = 0.25
        classes.append(c)
    ns['classes'] = classes
    ns['netclass_patterns'] = [{'netclass': n, 'pattern': p} for n, v in NETCLASSES.items() for p in v[6]]
    ns['netclass_assignments'] = None
    sev = d.setdefault('board', {}).setdefault('design_settings', {}).setdefault('rule_severities', {})
    sev['silk_edge_clearance'] = 'ignore'  # USB-A / RJ45 bodies intentionally overhang the board edge
    rules = d.setdefault('board', {}).setdefault('design_settings', {}).setdefault('rules', {})
    rules.update({'min_clearance': 0.1, 'min_track_width': 0.1, 'min_via_diameter': 0.4, 'min_through_hole_diameter': 0.2,
                  'min_via_annular_width': 0.1, 'min_copper_edge_clearance': 0.3, 'min_hole_clearance': 0.15,
                  'min_hole_to_hole': 0.25})
    json.dump(d, open(pro, 'w'), indent=2)


if __name__ == '__main__':
    main()
