#!/bin/bash
# Reproducible routing chain (KiCadRoutingTools + project fanout). Run from scripts/.
#   1) impedance-controlled diff pairs, one interface at a time
#   2) CM5 DF40 escape fanout (staggered 0.4/0.2 mm vias)
#   3) everything else, standard JLC fab tier, power nets wide
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
KRT=$HERE/../ref/KiCadRoutingTools
KPY=/Users/hector/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
W=${WORK:-$HERE/../build/route}
mkdir -p "$W"; cd "$W"; rm -f b*.kicad_*
python3 "$KRT/py_router/copy_board.py" "$HERE/../hardware/CM5_Edge_Carrier.kicad_pcb" b00.kicad_pcb >/dev/null
$KPY "$HERE/fanout_cm5.py" b00.kicad_pcb b0.kicad_pcb 2>/dev/null | grep -v -i fontconfig || true
cp b00.kicad_pro b0.kicad_pro
ln -sfn "$HERE/../hardware/lib" lib
cp "$HERE/../hardware/fp-lib-table" "$HERE/../hardware/sym-lib-table" .
DIFF="python3 -X utf8 $KRT/py_router/route_diff.py --clearance 0.12 --via-size 0.45 --via-drill 0.25 --no-gnd-vias --escalation off --fab-tier standard --diff-pair-intra-match"
# 5 Gb/s SuperSpeed + PCIe TX/RX: top layer only, referenced to the solid GND plane (In1), no vias
$DIFF b0.kicad_pcb b1.kicad_pcb --layers F.Cu --nets "USB3_0_TX_*" "USB3_0_RX_*" --track-width 0.18 --diff-pair-gap 0.15 --polarity-swap-nets "USB3_*" > log1_ss.txt 2>&1
$DIFF b1.kicad_pcb b2.kicad_pcb --layers F.Cu --nets "PCIE_TX_*" "PCIE_RX_*" --track-width 0.20 --diff-pair-gap 0.15 --polarity-swap-nets "PCIE_TX_*" "PCIE_RX_*" > log2_pcie.txt 2>&1
# REFCLK must cross the TX/RX pairs (pin order), so it alone may change layer
$DIFF b2.kicad_pcb b3a.kicad_pcb --layers F.Cu B.Cu --nets "PCIE_CLK_*" --track-width 0.20 --diff-pair-gap 0.15 > log3_clk.txt 2>&1
$DIFF b3a.kicad_pcb b3.kicad_pcb --layers F.Cu B.Cu --nets "ETH_D*" --track-width 0.16 --diff-pair-gap 0.18 --polarity-swap-nets "ETH_D*" > log3_eth.txt 2>&1
$DIFF b3.kicad_pcb b4.kicad_pcb --layers F.Cu B.Cu --nets "USB3_0_D*" "USB3_1_D*" "USB2_*" --track-width 0.18 --diff-pair-gap 0.15 > log4_usb2.txt 2>&1
python3 -X utf8 $KRT/py_router/route.py b4.kicad_pcb b6.kicad_pcb --nets "*" --layers F.Cu B.Cu \
  --track-width 0.15 --clearance 0.12 --via-size 0.45 --via-drill 0.25 --escalation off --fab-tier standard \
  --power-nets "+5V" "VBUS" "VBUS_USB" "+3V3_M2" "/Power/SW_5V" "/Power/LX_M2" "GND" "+3V3" "SVC_VBUS" \
  --power-nets-widths 0.6 0.6 0.5 0.5 0.6 0.5 0.3 0.3 0.3 > log6_all.txt 2>&1 || true
# repair pass: anything the main pass left open gets a second attempt with rip-up
python3 -X utf8 $KRT/py_router/route.py b6.kicad_pcb b7.kicad_pcb --nets "*" --layers F.Cu B.Cu \
  --track-width 0.13 --clearance 0.12 --via-size 0.4 --via-drill 0.2 --escalation off --fab-tier standard \
  --max-ripup 8 > log7_repair.txt 2>&1 || true
cp b7.kicad_pcb final.kicad_pcb
for f in log1_ss log2_pcie log3_clk log3_eth log4_usb2; do echo "$f: $(grep -o 'Diff pairs:.*' $f.txt) | $(grep -o 'Total vias:.*' $f.txt)"; done
grep -E "^  Single-ended|^  Multi-point:" log6_all.txt | tail -2
grep -E "^  Single-ended|^  Multi-point:" log7_repair.txt | tail -2
grep -o '"failed_single": \[[^]]*\]' log6_all.txt | tail -1
true
