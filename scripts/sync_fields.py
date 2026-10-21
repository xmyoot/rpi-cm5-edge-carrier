"""Push design.py field values (MPN, LCSC, ...) onto the routed board without re-routing (KiCad python)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
import design

path = sys.argv[1]
b = pcbnew.LoadBoard(path)
n = 0
for p in design.PARTS:
    fp = b.FindFootprintByReference(p.ref)
    if fp is None:
        continue
    for k, v in p.fields.items():
        if fp.HasField(k):
            fp.GetField(k).SetText(v)
        else:
            fp.SetField(k, v)
            f = fp.GetField(k)
            f.SetVisible(False)
            f.SetLayer(pcbnew.F_Fab)
        n += 1
pcbnew.SaveBoard(path, b)
print('fields synced:', n)
