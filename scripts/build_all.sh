#!/bin/bash
# Full regeneration: schematic -> netlist check -> board -> route -> finish -> DRC
set -e
cd "$(dirname "$0")"
KPY=/Users/hector/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
CLI=/Users/hector/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
python3 build_lib.py >/dev/null
python3 fix_footprints.py >/dev/null
python3 gen_sch.py
python3 check_netlist.py
$CLI sch erc --exit-code-violations -o ../build/erc.rpt ../hardware/CM5_Edge_Carrier.kicad_sch 2>&1 | grep -v -i fontconfig
$KPY gen_pcb.py 2>&1 | grep -v -i "fontconfig\|wxapp\|stdpbase"
./route_chain.sh
cp ../build/route/final.kicad_pcb ../hardware/CM5_Edge_Carrier.kicad_pcb
for i in 1 2 3 4 5 6; do
  if $KPY finish_pcb.py ../hardware/CM5_Edge_Carrier.kicad_pcb > ../build/finish.log 2>&1; then break; fi
done
grep "removed" ../build/finish.log
$KPY stitch_gnd.py ../hardware/CM5_Edge_Carrier.kicad_pcb 2>&1 | grep added
$KPY finish_pcb.py ../hardware/CM5_Edge_Carrier.kicad_pcb 2>&1 | grep removed || true
$KPY silk_cleanup.py ../hardware/CM5_Edge_Carrier.kicad_pcb 2>&1 | grep references
$CLI pcb drc --schematic-parity --exit-code-violations -o ../build/drc.rpt ../hardware/CM5_Edge_Carrier.kicad_pcb 2>&1 | grep -v -i fontconfig
