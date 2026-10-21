#!/bin/bash
# Fabrication + documentation outputs (JLCPCB format) from the finished KiCad project.
set -e
cd "$(dirname "$0")/.."
CLI=/Users/hector/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
KPY=/Users/hector/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
PCB=hardware/CM5_Edge_Carrier.kicad_pcb
SCH=hardware/CM5_Edge_Carrier.kicad_sch
F=fab; D=docs/img
mkdir -p $F/gerbers $D
q() { "$@" 2>&1 | grep -v -i fontconfig || true; }
q $CLI pcb export gerbers --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,F.SilkS,B.SilkS,Edge.Cuts --no-protel-ext -o $F/gerbers/ $PCB
q $CLI pcb export drill --format excellon --excellon-separate-th --generate-map --map-format gerberx2 -o $F/gerbers/ $PCB
(cd $F/gerbers && rm -f ../CM5_Edge_Carrier_gerbers.zip && zip -q ../CM5_Edge_Carrier_gerbers.zip *)
q $CLI pcb export pos --side front --format csv --units mm --exclude-dnp -o $F/pos_raw.csv $PCB
q $CLI sch export bom --fields 'Reference,Value,Footprint,${QUANTITY},MPN,LCSC,${DNP}' --group-by 'Value,Footprint,MPN,LCSC' --ref-range-delimiter '' --exclude-dnp -o $F/bom_raw.csv $SCH
python3 scripts/jlc_format.py $F
q $CLI pcb export step --subst-models --force -o $F/CM5_Edge_Carrier.step $PCB
q $CLI sch export pdf -o $F/CM5_Edge_Carrier_schematic.pdf $SCH
q $CLI pcb export pdf --layers F.Cu,F.SilkS,Edge.Cuts --mode-single -o $F/CM5_Edge_Carrier_top_assembly.pdf $PCB
cp $F/CM5_Edge_Carrier_schematic.pdf docs/
# renders
q $CLI pcb render --side top -w 2000 -h 1700 --quality high --background opaque --floor --rotate "-40,0,-30" --zoom 0.85 -o $D/render_iso.png $PCB
q $CLI pcb render --side top -w 2000 -h 1700 --quality high --background opaque --rotate "-45,0,155" --zoom 0.85 -o $D/render_iso_rear.png $PCB
q $CLI pcb render --side top -w 2000 -h 1700 --quality high --background opaque -o $D/render_top.png $PCB
q $CLI pcb render --side bottom -w 2000 -h 1700 --quality high --background opaque -o $D/render_bottom.png $PCB
for L in F.Cu B.Cu In1.Cu In2.Cu; do
  q $CLI pcb export svg --mode-single --layers $L,Edge.Cuts --exclude-drawing-sheet --fit-page-to-board -o build/$L.svg $PCB
  magick -density 300 -background white build/$L.svg -flatten -resize 1600x $D/layer_${L%.Cu}.png
done
q $CLI sch export pdf -o build/sch.pdf $SCH
pdftoppm -r 110 -png build/sch.pdf $D/schematic
$KPY scripts/si_report.py $PCB build/si.json > /dev/null 2>&1 || true
echo done
