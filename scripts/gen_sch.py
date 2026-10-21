"""Generate the hierarchical KiCad schematic from design.py."""
import os
import collections
import schgen as g
from sexp import dump, Sym as S
import design

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hardware')
NAME = 'CM5_Edge_Carrier'
g.PROJECT = NAME

SHEETS = [('Power', 'power.kicad_sch', 'Power: USB-C PD Input, 5 V and 3.3 V Bucks'),
          ('Compute', 'compute.kicad_sch', 'Raspberry Pi Compute Module 5'),
          ('HighSpeed', 'highspeed.kicad_sch', 'High-Speed IO: PCIe NVMe, USB 3.0, GbE, USB-C Service'),
          ('PeriphIO', 'periph_io.kicad_sch', 'Peripheral IO: Mic-Array I2S, UARTs, I2C, Fan')]

SYM_LIBS = ['Device', 'power', 'Connector', 'Connector_Generic', 'Interface_USB', 'Regulator_Switching',
            'Diode', 'Switch', 'Mechanical', 'Power_Protection']
FP_LIBS = ['Resistor_SMD', 'Capacitor_SMD', 'LED_SMD', 'Package_TO_SOT_SMD', 'Package_SON', 'Package_SO',
           'Package_DFN_QFN', 'Connector_USB', 'Connector_JST', 'Connector_IDC', 'Connector_PinHeader_2.54mm',
           'Button_Switch_SMD', 'Diode_SMD', 'Inductor_SMD', 'MountingHole', 'Fiducial']


def lib_tables():
    sym = ['(sym_lib_table', '\t(version 7)']
    for l in SYM_LIBS:
        sym.append(f'\t(lib (name "{l}")(type "KiCad")(uri "${{KICAD10_SYMBOL_DIR}}/{l}.kicad_sym")(options "")(descr ""))')
    sym.append('\t(lib (name "CM5Carrier")(type "KiCad")(uri "${KIPRJMOD}/lib/CM5Carrier.kicad_sym")(options "")(descr "Project symbols (from Raspberry Pi CM5 IO board)"))')
    sym.append(')')
    fp = ['(fp_lib_table', '\t(version 7)']
    for l in FP_LIBS:
        fp.append(f'\t(lib (name "{l}")(type "KiCad")(uri "${{KICAD10_FOOTPRINT_DIR}}/{l}.pretty")(options "")(descr ""))')
    fp.append('\t(lib (name "CM5Carrier")(type "KiCad")(uri "${KIPRJMOD}/lib/CM5Carrier.pretty")(options "")(descr "Project footprints"))')
    fp.append(')')
    open(os.path.join(OUT, 'sym-lib-table'), 'w').write('\n'.join(sym) + '\n')
    open(os.path.join(OUT, 'fp-lib-table'), 'w').write('\n'.join(fp) + '\n')


def polyline(pts, width=0.3):
    return [S('polyline'), [S('pts')] + [[S('xy'), x, y] for x, y in pts],
            [S('stroke'), [S('width'), width], [S('type'), S('solid')]], [S('fill'), [S('type'), S('none')]],
            [S('uuid'), g.uid(f'root/pl/{pts}')]]


def root_extras(root):
    """Block diagram + design notes on the root sheet."""
    items = []
    root.text('CM5 Edge-Audio Carrier  -  System Block Diagram', (25.4, 30.48), 3.0)
    blocks = {
        'USB-C PD IN\n(CH224K, 12 V)': (30.48, 50.8, 45.72, 20.32),
        '5 V / 5 A BUCK\n(TPS565208)': (96.52, 50.8, 45.72, 20.32),
        '3.3 V / 2 A BUCK\n(AP3441, M.2 rail)': (162.56, 50.8, 45.72, 20.32),
        'RASPBERRY PI CM5\nBCM2712, 4x A76\nLPDDR4X, eMMC, GbE PHY': (96.52, 91.44, 111.76, 40.64),
        'M.2 KEY-M NVMe\nPCIe x1': (228.6, 91.44, 50.8, 17.78),
        'USB-A x2 (3.0 + 2.0)\n(1.5 A VBUS switch)': (228.6, 114.3, 50.8, 17.78),
        'RJ45 GbE MagJack\n(+ESD)': (30.48, 91.44, 50.8, 17.78),
        'USB-C SERVICE\nrpiboot / gadget': (30.48, 114.3, 50.8, 17.78),
        'MIC ARRAY HDR\nI2S + I2C + IRQ': (96.52, 147.32, 50.8, 17.78),
        'QWIIC / UARTs\nDEBUG + BARCODE': (162.56, 147.32, 45.72, 17.78),
        'FAN 4-pin\nPWM + TACH': (228.6, 147.32, 50.8, 17.78),
    }
    for label, (x, y, w, h) in blocks.items():
        items.append([S('rectangle'), [S('start'), x, y], [S('end'), x + w, y + h],
                      [S('stroke'), [S('width'), 0.4], [S('type'), S('solid')]],
                      [S('fill'), [S('color'), 230, 240, 255, 1]], [S('uuid'), g.uid('root/blk/' + label)]])
        for i, line in enumerate(label.split('\n')):
            items.append([S('text'), line, [S('exclude_from_sim'), S('no')],
                          [S('at'), g.snap(x + w / 2), g.snap(y + 6.35 + i * 3.81), 0], g.font(2.0 if i == 0 else 1.5, i == 0),
                          [S('uuid'), g.uid(f'root/bt/{label}/{i}')]])
    arrows = [((76.2, 60.96), (96.52, 60.96)), ((142.24, 60.96), (162.56, 60.96)),
              ((119.38, 71.12), (119.38, 91.44)), ((185.42, 71.12), (185.42, 91.44)), ((185.42, 91.44), (228.6, 100.33)),
              ((208.28, 100.33), (228.6, 100.33)), ((208.28, 123.19), (228.6, 123.19)),
              ((96.52, 100.33), (81.28, 100.33)), ((96.52, 123.19), (81.28, 123.19)),
              ((121.92, 132.08), (121.92, 147.32)), ((185.42, 132.08), (185.42, 147.32)), ((203.2, 132.08), (254.0, 147.32))]
    for a, b in arrows:
        items.append(polyline([a, b]))
    notes = [
        'DESIGN NOTES',
        '1. Input: USB-C PD sink requests 12 V / 3 A (36 W). Buck EN divider (100k/15k) holds the 5 V rail off below ~9 V,',
        '   so a non-PD 5 V source can never back-feed the CM5 at low voltage.',
        '2. CM5 CC1/CC2 left open: set usb_max_current_enable=1 in config.txt to allow 1.6 A on the USB-A ports.',
        '3. PCIe x1 (Gen2 default, Gen3 via dtparam=pciex1_gen=3): 85 ohm diff, length-matched P/N within 0.1 mm.',
        '   TX AC-coupling capacitors are on the CM5; RX caps are on the NVMe module.',
        '4. USB 3.0 SuperSpeed: 90 ohm diff; GbE MDI: 100 ohm diff; all on L1 referenced to solid GND on L2.',
        '5. ESD: TPD4EUSB30 on every GbE pair, USBLC6-2 on service USB-C, SMAJ15A on VBUS (USB-A per RPi reference).',
        '6. Stackup: JLCPCB JLC04161H-7628, 1.6 mm, L1 SIG / L2 GND / L3 PWR (+5V, +3V3_M2) / L4 SIG.',
        '7. Boot: hold nRPIBOOT while plugging USB-C SERVICE into a host to flash eMMC with rpiboot.',
    ]
    for i, n in enumerate(notes):
        root.text(n, (25.4, 190.5 + i * 5.08), 2.0 if i == 0 else 1.5, bold=(i == 0))
    return items


def main():
    os.makedirs(OUT, exist_ok=True)
    pr = g.Project(NAME, 'CM5 Edge-Audio Carrier', 'Raspberry Pi CM5 carrier for edge-AI audio',
                   'Hector Jimenez', '1.0', '2026-10-21')
    sheets = {n: pr.add_sheet(n, f, t) for n, f, t in SHEETS}
    for n, sh in sheets.items():
        meta = design.SHEET_META.get(n, {})
        sh.paper = meta.get('paper', 'A3')
        for a, b, title in meta.get('boxes', []):
            sh.box(a, b, title)
        for at, txt in meta.get('notes', []):
            sh.text(txt, at, 1.5, bold=False)
    # nets used on more than one sheet become global labels
    usage = collections.defaultdict(set)
    for p in design.PARTS:
        for n in p.pins.values():
            if n:
                usage[n].add(p.sheet_name)
    glob = {n for n, s in usage.items() if len(s) > 1}
    for p in design.PARTS:
        sheets[p.sheet_name].place(p, glob)
    for (n, f, t) in SHEETS:
        sh = sheets[n]
        sh.finalize()
        open(os.path.join(OUT, f), 'w').write(dump(sh.sexpr(pr)) + '\n')
    extras = root_extras(pr.root)
    pos = {'Power': ((304.8, 50.8), (63.5, 10.16)), 'Compute': ((304.8, 81.28), (63.5, 10.16)),
           'HighSpeed': ((304.8, 111.76), (63.5, 10.16)), 'PeriphIO': ((304.8, 142.24), (63.5, 10.16))}
    pr.root.text('Hierarchical sheets', (304.8, 40.64), 2.5)
    for n, f, t in SHEETS:
        (x, y), _ = pos[n]
        pr.root.text(t, (x, y + 19.05), 1.5, bold=False)
    root = pr.root.sexpr(pr, extras + pr.sheet_symbols(pos))
    open(os.path.join(OUT, NAME + '.kicad_sch'), 'w').write(dump(root) + '\n')
    lib_tables()
    print('parts', len(design.PARTS), 'global nets', len(glob))


if __name__ == '__main__':
    main()
