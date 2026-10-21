"""Final board pass (run with KiCad's python): drop dangling router leftovers, fill zones.

One pass per process (pcbnew's SWIG board handle does not survive a second
fill/remove cycle); build_all.sh runs it until nothing is removed.
usage: finish_pcb.py board.kicad_pcb
"""
import sys
import json
import os
import subprocess
import tempfile
import pcbnew

CLI = '/Users/hector/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'


def dangling(path):
    out = os.path.join(tempfile.mkdtemp(), 'drc.json')
    subprocess.run([CLI, 'pcb', 'drc', '--format', 'json', '-o', out, path], capture_output=True)
    d = json.load(open(out))
    return {i['uuid'] for v in d['violations'] if v['type'] in ('track_dangling', 'via_dangling') for i in v['items']}


def polish(b):
    """M.2 footprint ships 2230/2242 labels in both orientations; keep only the upright copy."""
    fp = b.FindFootprintByReference('J2')
    for g in list(fp.GraphicalItems()):
        if g.GetClass() == 'PCB_TEXT' and g.GetText() in ('2230', '2242') and \
                int(round(g.GetDrawRotation().AsDegrees())) % 360 != 0:
            fp.Remove(g)


def main(path):
    b = pcbnew.LoadBoard(path)
    for z in b.Zones():
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())   # planes must be filled or every plane via reads as dangling
    pcbnew.SaveBoard(path, b)
    bad = dangling(path)
    doomed = [t for t in b.GetTracks() if t.m_Uuid.AsString() in bad]
    for t in doomed:
        b.Remove(t)
    removed = len(doomed)
    polish(b)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(path, b)
    print(f'removed dangling items: {removed}; zones filled: {len(b.Zones())}')
    sys.exit(0 if removed == 0 else 3)


if __name__ == '__main__':
    main(sys.argv[1])
