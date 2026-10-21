"""Build project symbol library lib/CM5Carrier.kicad_sym from the CM5 IO board sources."""
import os
from sexp import parse, dump, find, find1, Sym
REF = os.path.join(os.path.dirname(__file__), '..', 'ref', 'cm5io')
OUT = os.path.join(os.path.dirname(__file__), '..', 'hardware', 'lib', 'CM5Carrier.kicad_sym')

want_lib = ['ComputeModule5-CM5', 'MagJack-A70-112-331N126', 'TPD4EUSB30', 'AP2553W6']
want_sch = ['CM5IO:USB3_A', 'CM5IO:SolderNut', 'CM5IO:M.2_Screw']
syms = {}
lib = parse(open(os.path.join(REF, 'CM5IO.kicad_sym')).read())
for s in find(lib, 'symbol'):
    if s[1] in want_lib:
        syms[s[1]] = s
for f in os.listdir(REF):
    if f.endswith('.kicad_sch'):
        t = parse(open(os.path.join(REF, f)).read())
        for s in find(find1(t, 'lib_symbols'), 'symbol'):
            if s[1] in want_sch:
                name = s[1].split(':')[1]
                s[1] = name
                syms[name] = s
# AP2553 GND pin is mis-typed as power output in the source library
for sub in find(syms['AP2553W6'], 'symbol'):
    for p in find(sub, 'pin'):
        if find1(p, 'name')[1] == 'GND':
            p[1] = Sym('power_in')
# Host-side M.2 socket: stock KiCad symbol with signal pins typed passive (the stock
# symbol types them from the card's point of view, which trips ERC on a host board)
std = parse(open('/Users/hector/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/Connector.kicad_sym').read())
m2 = [s for s in find(std, 'symbol') if s[1] == 'Bus_M.2_Socket_M'][0]
m2[1] = 'M.2_Socket_M_Host'
for sub in find(m2, 'symbol'):
    sub[1] = sub[1].replace('Bus_M.2_Socket_M', 'M.2_Socket_M_Host')
    for p in find(sub, 'pin'):
        if p[1] in ('input', 'output', 'bidirectional'):
            p[1] = Sym('passive')
syms['M.2_Socket_M_Host'] = m2
# Project power-rail symbols cloned from power:+3V3
pw = parse(open('/Users/hector/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/power.kicad_sym').read())
base = [s for s in find(pw, 'symbol') if s[1] == '+3V3'][0]
import copy
for rail in ('+3V3_M2', 'VBUS_USB'):
    s2 = copy.deepcopy(base)
    s2[1] = rail
    for p in find(s2, 'property'):
        if p[1] == 'Value':
            p[2] = rail
        if p[1] == 'Description':
            p[2] = f'Power symbol creates a global label with name "{rail}"'
    for sub in find(s2, 'symbol'):
        sub[1] = sub[1].replace('+3V3', rail)
        for pin in find(sub, 'pin'):
            find1(pin, 'name')[1] = rail
    syms[rail] = s2
out = [Sym('kicad_symbol_lib'), [Sym('version'), Sym('20241209')], [Sym('generator'), 'cm5carrier'], [Sym('generator_version'), '10.0']]
out += [syms[k] for k in sorted(syms)]
open(OUT, 'w').write(dump(out) + '\n')
print(sorted(syms))
