"""Convert kicad-cli BOM / position exports to JLCPCB SMT upload format."""
import csv
import os
import sys

F = sys.argv[1]
rows = list(csv.DictReader(open(os.path.join(F, 'bom_raw.csv'))))
with open(os.path.join(F, 'CM5_Edge_Carrier_BOM_JLC.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Comment', 'Designator', 'Footprint', 'Quantity', 'Manufacturer Part', 'JLCPCB Part #'])
    for r in rows:
        refs = [x for x in r['Reference'].replace(' ', '').split(',') if x and not x.startswith(('H', 'FID', '#'))]
        if not refs:
            continue
        w.writerow([r['Value'], ','.join(refs), r['Footprint'].split(':')[-1], len(refs), r.get('MPN', ''),
                    r.get('LCSC', '')])
pos = list(csv.DictReader(open(os.path.join(F, 'pos_raw.csv'))))
with open(os.path.join(F, 'CM5_Edge_Carrier_CPL_JLC.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
    for r in pos:
        if r['Ref'].startswith(('H', 'FID')):
            continue
        w.writerow([r['Ref'], r['PosX'] + 'mm', r['PosY'] + 'mm', 'Top' if r['Side'] == 'top' else 'Bottom', r['Rot']])
os.remove(os.path.join(F, 'bom_raw.csv'))
os.remove(os.path.join(F, 'pos_raw.csv'))
print('JLC BOM lines:', len(rows), 'CPL parts:', len(pos))
