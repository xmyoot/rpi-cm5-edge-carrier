"""High-speed length / skew / via report from the routed board (KiCad python).

usage: si_report.py board.kicad_pcb out.json
"""
import sys
import json
import pcbnew

PAIRS = {
    'PCIe TX (85R)': ('PCIE_TX_P', 'PCIE_TX_N'), 'PCIe RX (85R)': ('PCIE_RX_P', 'PCIE_RX_N'),
    'PCIe REFCLK (85R)': ('PCIE_CLK_P', 'PCIE_CLK_N'),
    'USB3 SSTX (90R)': ('USB3_0_TX_P', 'USB3_0_TX_N'), 'USB3 SSRX (90R)': ('USB3_0_RX_P', 'USB3_0_RX_N'),
    'USB-A1 D+/D- (90R)': ('USB3_0_DP', 'USB3_0_DN'), 'USB-A2 D+/D- (90R)': ('USB3_1_DP', 'USB3_1_DN'),
    'USB-C svc D+/D- (90R)': ('USB2_P', 'USB2_N'),
    'GbE MDI0 (100R)': ('ETH_D0_P', 'ETH_D0_N'), 'GbE MDI1 (100R)': ('ETH_D1_P', 'ETH_D1_N'),
    'GbE MDI2 (100R)': ('ETH_D2_P', 'ETH_D2_N'), 'GbE MDI3 (100R)': ('ETH_D3_P', 'ETH_D3_N'),
}


def net_stats(b, name):
    length, vias, layers = 0.0, 0, set()
    for t in b.GetTracks():
        if t.GetNetname() != name:
            continue
        if t.GetClass() == 'PCB_VIA':
            vias += 1
        else:
            length += pcbnew.ToMM(t.GetLength())
            layers.add(t.GetLayerName())
    return length, vias, sorted(layers)


b = pcbnew.LoadBoard(sys.argv[1])
rows = []
for label, (p, n) in PAIRS.items():
    lp, vp, la = net_stats(b, p)
    ln, vn, lb = net_stats(b, n)
    rows.append(dict(pair=label, p_mm=round(lp, 2), n_mm=round(ln, 2), skew_mm=round(abs(lp - ln), 2),
                     vias=vp + vn, layers=sorted(set(la) | set(lb))))
json.dump(rows, open(sys.argv[2], 'w'), indent=1)
for r in rows:
    print(f"{r['pair']:24s} P {r['p_mm']:7.2f}  N {r['n_mm']:7.2f}  skew {r['skew_mm']:5.2f} mm  vias {r['vias']:2d}  {','.join(r['layers'])}")
