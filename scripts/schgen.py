"""Schematic writer: places library symbols and connects every pin with a short
wire stub ending in a net label, global label, power symbol or no-connect flag.

Coordinates are in mm on a 1.27 mm grid. Library coordinates are y-up,
schematic coordinates are y-down.
"""
import math
import uuid as _uuid
from sexp import dump, find, find1, Sym
from libs import get_symbol, pins, units

S = Sym
GRID = 1.27
STUB = 2.54
POWER_NETS = {'GND': 'power:GND', '+5V': 'power:+5V', '+3V3': 'power:+3V3', 'VBUS': 'power:VBUS',
              '+3V3_M2': 'CM5Carrier:+3V3_M2', 'VBUS_USB': 'CM5Carrier:VBUS_USB'}
PROJECT = 'CM5_Edge_Carrier'


def uid(seed):
    return str(_uuid.uuid5(_uuid.NAMESPACE_URL, 'cm5carrier/' + seed))


def snap(v):
    return round(round(v / GRID) * GRID, 3)


def font(size=1.27, bold=False, hide=False, justify=None):
    e = [S('effects'), [S('font'), [S('size'), size, size]] + ([[S('bold'), S('yes')]] if bold else [])]
    if justify:
        e.append([S('justify')] + [S(j) for j in justify.split()])
    if hide:
        e.append([S('hide'), S('yes')])
    return e


def xform(px, py, rot):
    r = math.radians(rot)
    x = px * math.cos(r) - py * math.sin(r)
    y = px * math.sin(r) + py * math.cos(r)
    return x, -y


class Sheet:
    def __init__(self, name, filename, title, page, paper='A3'):
        self.name, self.filename, self.title, self.page, self.paper = name, filename, title, page, paper
        self.items = []
        self.lib = {}
        self.uuid = uid('sheet/' + name)
        self.path = None  # set by Project
        self.symbols = []  # (ref, uuid, lib_id, value, footprint)
        self._pwr = 0
        self.pending, self.points, self.segs, self.bodies = [], [], [], []

    # ------------------------------------------------------------------ helpers
    def _use_lib(self, lib_id):
        if lib_id not in self.lib:
            self.lib[lib_id] = get_symbol(lib_id)
        return self.lib[lib_id]

    def wire(self, a, b):
        self.items.append([S('wire'), [S('pts'), [S('xy'), a[0], a[1]], [S('xy'), b[0], b[1]]],
                           [S('stroke'), [S('width'), 0], [S('type'), S('default')]],
                           [S('uuid'), uid(f'{self.name}/w/{a}/{b}')]])

    def label(self, net, at, angle, glob=False):
        just = 'left' if angle in (0, 90) else 'right'
        if glob:
            self.items.append([S('global_label'), net, [S('shape'), S('bidirectional')],
                               [S('at'), at[0], at[1], angle], [S('fields_autoplaced'), S('yes')],
                               font(justify=just), [S('uuid'), uid(f'{self.name}/gl/{net}/{at}')],
                               [S('property'), 'Intersheetrefs', '${INTERSHEET_REFS}', [S('at'), at[0], at[1], 0],
                                font(hide=True)]])
        else:
            self.items.append([S('label'), net, [S('at'), at[0], at[1], angle], [S('fields_autoplaced'), S('yes')],
                               font(justify=just + ' bottom'), [S('uuid'), uid(f'{self.name}/l/{net}/{at}')]])

    def noconnect(self, at):
        self.items.append([S('no_connect'), [S('at'), at[0], at[1]], [S('uuid'), uid(f'{self.name}/nc/{at}')]])

    def power(self, net, at, direction):
        """direction: unit vector of the stub (outward from the pin)."""
        lib_id = POWER_NETS[net]
        self._use_lib(lib_id)
        dx, dy = direction
        if net == 'GND':
            rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[(dx, dy)]
        else:
            rot = {(0, -1): 0, (0, 1): 180, (1, 0): 270, (-1, 0): 90}[(dx, dy)]
        self._pwr += 1
        ref = f'#PWR{self.page:02d}{self._pwr:03d}'
        sym = get_symbol(lib_id)
        val_at = [p for p in find(sym, 'property') if p[1] == 'Value'][0]
        vy = float(find1(val_at, 'at')[2])
        vx, vyy = xform(0, vy, rot)
        u = uid(f'{self.name}/pwr/{net}/{at}')
        self.items.append([S('symbol'), [S('lib_id'), lib_id], [S('at'), at[0], at[1], rot], [S('unit'), 1],
                           [S('exclude_from_sim'), S('no')], [S('in_bom'), S('yes')], [S('on_board'), S('yes')],
                           [S('dnp'), S('no')], [S('uuid'), u],
                           [S('property'), 'Reference', ref, [S('at'), at[0], at[1], 0], font(hide=True)],
                           [S('property'), 'Value', net, [S('at'), snap(at[0] + vx), snap(at[1] + vyy), 0], font()],
                           [S('property'), 'Footprint', '', [S('at'), at[0], at[1], 0], font(hide=True)],
                           [S('property'), 'Datasheet', '', [S('at'), at[0], at[1], 0], font(hide=True)],
                           [S('pin'), '1', [S('uuid'), uid(u + '/p1')]],
                           [S('instances'), [S('project'), PROJECT,
                                             [S('path'), self.path, [S('reference'), ref], [S('unit'), 1]]]]])

    def text(self, s, at, size=2.0, bold=True):
        self.items.append([S('text'), s, [S('exclude_from_sim'), S('no')], [S('at'), at[0], at[1], 0],
                           font(size, bold, justify='left bottom'), [S('uuid'), uid(f'{self.name}/t/{s}/{at}')]])

    def box(self, a, b, title=None):
        self.items.append([S('rectangle'), [S('start'), a[0], a[1]], [S('end'), b[0], b[1]],
                           [S('stroke'), [S('width'), 0.254], [S('type'), S('dash')]],
                           [S('fill'), [S('type'), S('none')]], [S('uuid'), uid(f'{self.name}/box/{a}/{b}')]])
        if title:
            self.text(title, (a[0] + 1.27, a[1] + 3.81), 2.0)

    # ------------------------------------------------------------------ parts
    def place(self, part, glob_nets):
        sym = self._use_lib(part.lib_id)
        X, Y, rot = snap(part.at[0]), snap(part.at[1]), part.rot
        ulist = units(sym)
        u_sym = uid('sym/' + part.ref)
        part.sym_uuid = u_sym
        part.sheet = self
        for unit in ulist:
            ux, uy = (X, Y) if unit == 1 else (snap(part.unit_at[unit][0]), snap(part.unit_at[unit][1]))
            uu = u_sym if unit == 1 else uid(f'sym/{part.ref}/{unit}')
            node = [S('symbol'), [S('lib_id'), part.lib_id], [S('at'), ux, uy, rot]]
            if part.mirror:
                node.append([S('mirror'), S(part.mirror)])
            node += [[S('unit'), unit], [S('exclude_from_sim'), S('no')],
                     [S('in_bom'), S('no') if part.ref.startswith(('H', 'FID', '#')) else S('yes')],
                     [S('on_board'), S('yes')], [S('dnp'), S('yes') if part.dnp else S('no')],
                     [S('fields_autoplaced'), S('yes')], [S('uuid'), uu]]
            # properties
            props = {p[1]: p for p in find(sym, 'property')}
            ref_at = find1(props['Reference'], 'at')
            val_at = find1(props['Value'], 'at')
            two_pin = len(pins(sym, unit)) == 2
            fang = 90 if rot in (90, 270) else 0
            if two_pin and rot in (90, 270):
                rx, ry, vx, vy = ux, snap(uy - 2.54), ux, snap(uy + 2.54)
                rj = vj = None
            elif part.label_side == 'right' or rot in (90, 270):
                bb = self._bbox(sym, unit, rot)
                rx, ry = snap(ux + max(bb[2], 0) + 1.27), snap(uy - 1.27)
                vx, vy = rx, snap(uy + 1.27)
                rj = vj = 'left'
            else:
                ax, ay = xform(float(ref_at[1]), float(ref_at[2]), 0)
                bx, by = xform(float(val_at[1]), float(val_at[2]), 0)
                rx, ry, vx, vy = snap(ux + ax), snap(uy + ay), snap(ux + bx), snap(uy + by)
                rj = self._just(props['Reference'])
                vj = self._just(props['Value'])
            node.append([S('property'), 'Reference', part.ref, [S('at'), rx, ry, fang], font(justify=rj)])
            node.append([S('property'), 'Value', part.value, [S('at'), vx, vy, fang], font(justify=vj)])
            node.append([S('property'), 'Footprint', part.footprint, [S('at'), ux, uy, 0], font(hide=True)])
            node.append([S('property'), 'Datasheet', part.datasheet or '~', [S('at'), ux, uy, 0], font(hide=True)])
            desc = props.get('Description')
            node.append([S('property'), 'Description', part.desc or (desc[2] if desc else ''), [S('at'), ux, uy, 0], font(hide=True)])
            for k, v in part.fields.items():
                node.append([S('property'), k, v, [S('at'), ux, uy, 0], font(hide=True)])
            for p in pins(sym, unit):
                node.append([S('pin'), p[0], [S('uuid'), uid(f'{part.ref}/pin/{p[0]}')]])
            node.append([S('instances'), [S('project'), PROJECT,
                                          [S('path'), self.path, [S('reference'), part.ref], [S('unit'), unit]]]])
            self.items.append(node)
            self._connect(part, sym, unit, ux, uy, rot, glob_nets)
        self.symbols.append(part)

    @staticmethod
    def _just(prop):
        eff = find1(prop, 'effects')
        j = find1(eff, 'justify') if eff else None
        return ' '.join(str(x) for x in j[1:]) if j else None

    def _bbox(self, sym, unit, rot):
        xs, ys = [], []
        for p in pins(sym, unit):
            x, y = xform(p[2], p[3], rot)
            xs.append(x)
            ys.append(y)
        return (min(xs), min(ys), max(xs), max(ys)) if xs else (-2.54, -2.54, 2.54, 2.54)

    def _connect(self, part, sym, unit, X, Y, rot, glob_nets):
        seen = {}
        body = self._bbox(sym, unit, rot)
        self.bodies.append((part.ref, X + body[0] + 0.6, Y + body[1] + 0.6, X + body[2] - 0.6, Y + body[3] - 0.6))
        for num, name, px, py, ang, ln, etype, u in pins(sym, unit):
            sx, sy = xform(px, py, rot)
            at = (snap(X + sx), snap(Y + sy))
            net = part.pins.get(num)
            if at in seen:
                if seen[at] != net and net is not None and seen[at] is not None:
                    raise ValueError(f'{part.ref}: stacked pin {num} net {net} != {seen[at]}')
                continue
            seen[at] = net
            if net is None:
                if etype != 'no_connect':
                    self.noconnect(at)
                self.points.append((at, '__nc__' + part.ref + num))
                continue
            dx, dy = xform(math.cos(math.radians(ang + 180)), math.sin(math.radians(ang + 180)), rot)
            dx, dy = round(dx), round(dy)
            stub = part.stub.get(num, STUB) if isinstance(part.stub, dict) else part.stub
            self.pending.append(dict(net=net, at=at, d=(dx, dy), stub=stub, ref=part.ref, glob=net in glob_nets,
                                     style=part.pin_style.get(num)))
            self.points.append((at, net))

    # -------------------------------------------------------------- auto wiring
    @staticmethod
    def _on_seg(p, a, b):
        if a[0] == b[0] == p[0]:
            return min(a[1], b[1]) - 1e-6 <= p[1] <= max(a[1], b[1]) + 1e-6
        if a[1] == b[1] == p[1]:
            return min(a[0], b[0]) - 1e-6 <= p[0] <= max(a[0], b[0]) + 1e-6
        return False

    @staticmethod
    def _cross(a, b, c, d):
        """Proper crossing of a horizontal and a vertical segment."""
        if a[1] == b[1] and c[0] == d[0]:
            h, v = (a, b), (c, d)
        elif a[0] == b[0] and c[1] == d[1]:
            h, v = (c, d), (a, b)
        else:
            return False
        hx0, hx1 = sorted((h[0][0], h[1][0]))
        vy0, vy1 = sorted((v[0][1], v[1][1]))
        x, y = v[0][0], h[0][1]
        return hx0 < x < hx1 and vy0 < y < vy1

    def _seg_ok(self, a, b, net, refs):
        if a == b:
            return True
        for p, n in self.points:
            if n != net and self._on_seg(p, a, b):
                return False
        for (c, d, n) in self.segs:
            if n == net:
                continue
            if self._on_seg(a, c, d) or self._on_seg(b, c, d) or self._on_seg(c, a, b) or self._on_seg(d, a, b):
                return False
            # collinear overlap
            if (a[0] == b[0] == c[0] == d[0] and max(min(a[1], b[1]), min(c[1], d[1])) < min(max(a[1], b[1]), max(c[1], d[1]))) or \
               (a[1] == b[1] == c[1] == d[1] and max(min(a[0], b[0]), min(c[0], d[0])) < min(max(a[0], b[0]), max(c[0], d[0]))):
                return False
            if self._cross(a, b, c, d):
                return False
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        for ref, bx0, by0, bx1, by1 in self.bodies:
            if x0 <= bx1 and x1 >= bx0 and y0 <= by1 and y1 >= by0:
                return False
        return True

    def _try_edge(self, A, B, net):
        """A, B: pending pin dicts. Returns list of segments or None."""
        a1 = (snap(A['at'][0] + A['d'][0] * A['stub']), snap(A['at'][1] + A['d'][1] * A['stub']))
        b1 = (snap(B['at'][0] + B['d'][0] * B['stub']), snap(B['at'][1] + B['d'][1] * B['stub']))
        cands = []
        if a1[0] == b1[0] or a1[1] == b1[1]:
            cands.append([(A['at'], a1), (a1, b1), (b1, B['at'])])
        # direct pin-to-pin straight line when pins face each other
        if A['at'][0] == B['at'][0] or A['at'][1] == B['at'][1]:
            cands.insert(0, [(A['at'], B['at'])])
        cands.append([(A['at'], a1), (a1, (b1[0], a1[1])), ((b1[0], a1[1]), b1), (b1, B['at'])])
        cands.append([(A['at'], a1), (a1, (a1[0], b1[1])), ((a1[0], b1[1]), b1), (b1, B['at'])])
        for c in cands:
            segs = [(p, q) for p, q in c if p != q]
            # the stubs themselves may touch their own pin bodies; skip body test for first/last stub
            ok = True
            for i, (p, q) in enumerate(segs):
                stub = (p == A['at'] or q == B['at']) and len(segs) > 1
                if stub:
                    saved = self.bodies
                    self.bodies = []
                    r = self._seg_ok(p, q, net, None)
                    self.bodies = saved
                else:
                    r = self._seg_ok(p, q, net, None)
                if not r:
                    ok = False
                    break
            if ok:
                return segs
        return None

    def _reserve_stubs(self):
        for pd in self.pending:
            for stub in (pd['stub'], 1.27):
                end = (snap(pd['at'][0] + pd['d'][0] * stub), snap(pd['at'][1] + pd['d'][1] * stub))
                if self._seg_ok_nobody(pd['at'], end, pd['net']):
                    break
            else:
                raise ValueError(f"stub conflict at {pd['ref']} {pd['net']} {pd['at']}")
            pd['stub'] = stub
            self.points.append((end, pd['net']))
            self.segs.append((pd['at'], end, pd['net']))

    def _seg_ok_nobody(self, a, b, net):
        saved, self.bodies = self.bodies, []
        r = self._seg_ok(a, b, net, None)
        self.bodies = saved
        return r

    def finalize(self, limit=80):
        self._reserve_stubs()
        bynet = {}
        for pd in self.pending:
            bynet.setdefault(pd['net'], []).append(pd)
        drawn = set()
        ends = {}

        def draw(p, q):
            key = (min(p, q), max(p, q))
            if p == q or key in drawn:
                return
            drawn.add(key)
            self.wire(p, q)
            ends[p] = ends.get(p, 0) + 1
            ends[q] = ends.get(q, 0) + 1

        for net, pts in sorted(bynet.items(), key=lambda kv: len(kv[1])):
            if net == 'GND' or len(pts) == 1 or any(pd['style'] for pd in pts):
                for pd in pts:
                    self._terminal(pd, draw)
                continue
            lim = 40 if net in POWER_NETS else limit
            # MST over manhattan distance, shortest edges first
            done, rest, edges = [pts[0]], pts[1:], []
            while rest:
                best = min(((abs(x['at'][0] - y['at'][0]) + abs(x['at'][1] - y['at'][1]), i, x, y)
                            for i, x in enumerate(done) for y in rest), key=lambda t: (t[0], t[1]))
                edges.append(best)
                done.append(best[3])
                rest.remove(best[3])
            parent = {id(pd): id(pd) for pd in pts}

            def find_(k):
                while parent[k] != k:
                    k = parent[k]
                return k
            for dist, _, x, y in sorted(edges, key=lambda e: e[0]):
                if dist > lim:
                    continue
                segs = self._try_edge(x, y, net)
                if segs is None:
                    continue
                for p, q in segs:
                    self.segs.append((p, q, net))
                    draw(p, q)
                parent[find_(id(y))] = find_(id(x))
            clusters = {}
            for pd in pts:
                clusters.setdefault(find_(id(pd)), []).append(pd)
            if True:
                for members in clusters.values():
                    if net in POWER_NETS:
                        rep = min(members, key=lambda m: (m['d'] != (0, -1), m['at'][1], m['at'][0]))
                    else:
                        rep = min(members, key=lambda m: (m['d'][1] != 0, m['at'][1], m['at'][0]))
                    self._terminal(rep, draw)
        pin_pts = {pd['at'] for pd in self.pending}
        for p, c in ends.items():
            if c >= 3 or (c >= 2 and p in pin_pts):
                self.items.append([S('junction'), [S('at'), p[0], p[1]], [S('diameter'), 0],
                                   [S('color'), 0, 0, 0, 0], [S('uuid'), uid(f'{self.name}/j/{p}')]])

    def _terminal(self, pd, draw):
        at, (dx, dy), net = pd['at'], pd['d'], pd['net']
        end = (snap(at[0] + dx * pd['stub']), snap(at[1] + dy * pd['stub']))
        draw(at, end)
        if pd.get('style') == 'glabel':
            angle = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
            self.label(net, end, angle, glob=True)
        elif net in POWER_NETS:
            self.power(net, end, (dx, dy))
        else:
            angle = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
            self.label(net, end, angle, glob=pd['glob'])

    # ------------------------------------------------------------------ output
    def sexpr(self, project, extra=()):
        tb = [S('title_block'), [S('title'), self.title], [S('date'), project.date], [S('rev'), project.rev],
              [S('company'), project.company],
              [S('comment'), 1, project.subtitle], [S('comment'), 2, 'Sheet: ' + self.name]]
        out = [S('kicad_sch'), [S('version'), S('20250114')], [S('generator'), 'eeschema'],
               [S('generator_version'), '10.0'], [S('uuid'), self.uuid], [S('paper'), self.paper], tb,
               [S('lib_symbols')] + [self.lib[k] for k in sorted(self.lib)]]
        out += list(extra)
        out += self.items
        if self.page == 1:
            out.append([S('sheet_instances'), [S('path'), '/', [S('page'), '1']]])
        out.append([S('embedded_fonts'), S('no')])
        return out


class Part:
    def __init__(self, ref, lib_id, value, footprint, at, pins, rot=0, fields=None, desc=None,
                 datasheet=None, dnp=False, mirror=None, unit_at=None, label_side=None, stub=STUB, pcb=None,
                 pin_style=None):
        self.ref, self.lib_id, self.value, self.footprint = ref, lib_id, value, footprint
        self.at, self.rot, self.pins = at, rot, {str(k): v for k, v in pins.items()}
        self.fields = fields or {}
        self.desc, self.datasheet, self.dnp, self.mirror = desc, datasheet, dnp, mirror
        self.unit_at = unit_at or {}
        self.label_side = label_side
        self.stub = stub
        self.pin_style = {str(k): v for k, v in (pin_style or {}).items()}
        self.pcb = pcb
        self.sym_uuid = None
        self.sheet = None


class Project:
    def __init__(self, name, title, subtitle, company, rev, date):
        self.name, self.title, self.subtitle, self.company, self.rev, self.date = name, title, subtitle, company, rev, date
        self.root = Sheet('Root', name + '.kicad_sch', title, 1)
        self.root.path = '/' + self.root.uuid
        self.sheets = []

    def add_sheet(self, name, filename, title):
        sh = Sheet(name, filename, title, len(self.sheets) + 2)
        sh.uuid_sheetsym = uid('sheetsym/' + name)
        sh.path = f'/{self.root.uuid}/{sh.uuid_sheetsym}'
        self.sheets.append(sh)
        return sh

    def sheet_symbols(self, positions):
        out = []
        for sh in self.sheets:
            (x, y), (w, h) = positions[sh.name]
            out.append([S('sheet'), [S('at'), x, y], [S('size'), w, h], [S('exclude_from_sim'), S('no')],
                        [S('in_bom'), S('yes')], [S('on_board'), S('yes')], [S('dnp'), S('no')],
                        [S('fields_autoplaced'), S('yes')],
                        [S('stroke'), [S('width'), 0.1524], [S('type'), S('solid')]],
                        [S('fill'), [S('color'), 255, 255, 225, 1]],
                        [S('uuid'), sh.uuid_sheetsym],
                        [S('property'), 'Sheetname', sh.name, [S('at'), x, snap(y - 0.7), 0],
                         font(1.6, True, justify='left bottom')],
                        [S('property'), 'Sheetfile', sh.filename, [S('at'), x, snap(y + h + 0.6), 0],
                         font(justify='left top')],
                        [S('instances'), [S('project'), PROJECT,
                                          [S('path'), self.root.path, [S('page'), str(sh.page)]]]]])
        return out
