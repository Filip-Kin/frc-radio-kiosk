"""Finish what Freerouting leaves: grid A* over F.Cu / In2.Cu / B.Cu for each
connection KiCad's DRC lists as unconnected, between the two copper islands it
names. Power classes stay on the outer layers; signals may use In2. Each
connection tries its class width first, then narrower. Emits segments and vias.
Usage (from the board's dir): mazefix.py board.kicad_pcb padgeo.json drc.json out.kicad_pcb"""
import heapq, json, math, re, sys, uuid, fnmatch
import numpy as np
B, PG, DRC, OUT = sys.argv[1:5]
s = open(B).read(); g = json.load(open(PG)); d = json.load(open(DRC))
PRO = json.load(open('/home/filip/tmp/v2d/board.kicad_pro'))['net_settings']
def ncls(n):
    for p in PRO['netclass_patterns']:
        if fnmatch.fnmatchcase(n, p['pattern']): return p['netclass']
    return 'Default'
CLS = {c['name']: c for c in PRO['classes']}
R = 0.05                      # grid, mm
X0, Y0, X1, Y1 = g['edge']
NX, NY = int((X1 - X0) / R) + 1, int((Y1 - Y0) / R) + 1
LAY = ['F.Cu', 'In2.Cu', 'B.Cu']; LI = {l: i for i, l in enumerate(LAY)}
EDGE = 0.35
import os
KEEP = json.load(open(os.environ['KEEPOUT'])) if os.environ.get('KEEPOUT') else []
def gx(x): return int(round((x - X0) / R))
def gy(y): return int(round((y - Y0) / R))
XX, YY = None, None

# #region copper model: every item with its net, layers and a distance function
items = []   # dict(kind, net, layers(set of idx), shape)
for p in g['pads']:
    lays = {0} if (p['smd'] and not p['back']) else ({2} if p['smd'] else {0, 1, 2})
    items.append(dict(kind='pad', net=p['net'], layers=lays, box=p['box'], ref=p['ref'], num=p['num'], hole=not p['smd'], npth=p.get('npth', False)))
for t in g['tracks']:
    if t['layer'] not in LI: continue
    items.append(dict(kind='track', net=t['net'], layers={LI[t['layer']]}, a=t['a'], b=t['b'], w=t['w']))
for v in g['vias']:
    items.append(dict(kind='via', net=v['net'], layers={0, 1, 2}, c=v['c'], r=v['r'], hole=True))

def dist_field(it, x0, y0, x1, y1):
    """distance from item copper to grid cell centres in the window [x0..x1) x [y0..y1)."""
    xs = X0 + np.arange(x0, x1) * R; ys = Y0 + np.arange(y0, y1) * R
    X, Y = np.meshgrid(xs, ys)
    if it['kind'] == 'pad':
        b = it['box']
        dx = np.maximum(np.maximum(b[0] - X, 0), X - b[2]); dy = np.maximum(np.maximum(b[1] - Y, 0), Y - b[3])
        return np.hypot(dx, dy)
    if it['kind'] == 'via':
        return np.maximum(np.hypot(X - it['c'][0], Y - it['c'][1]) - it['r'], 0)
    a, b = it['a'], it['b']; dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
    t = np.zeros_like(X) if L2 == 0 else np.clip(((X - a[0]) * dx + (Y - a[1]) * dy) / L2, 0, 1)
    return np.maximum(np.hypot(X - a[0] - t * dx, Y - a[1] - t * dy) - it['w'] / 2, 0)

def bbox(it, m):
    if it['kind'] == 'pad': b = it['box']; return b[0] - m, b[1] - m, b[2] + m, b[3] + m
    if it['kind'] == 'via': c, r = it['c'], it['r'] + m; return c[0] - r, c[1] - r, c[0] + r, c[1] + r
    a, b, w = it['a'], it['b'], it['w'] / 2 + m
    return min(a[0], b[0]) - w, min(a[1], b[1]) - w, max(a[0], b[0]) + w, max(a[1], b[1]) + w

def win(bx):
    return max(0, gx(bx[0]) - 1), max(0, gy(bx[1]) - 1), min(NX, gx(bx[2]) + 2), min(NY, gy(bx[3]) + 2)

def blocked_map(net, width, clr, viar):
    """per layer: cells where a track of this width cannot go; plus where a via cannot go."""
    need_t = width / 2 + clr + 0.03
    need_v = viar + clr + 0.03
    trk = np.zeros((3, NY, NX), bool); via = np.zeros((NY, NX), bool)
    for it in items:
        if it['net'] == net and net: continue
        hx = 0.3 if it.get('npth') else (0.1 if it.get('hole') else 0)
        m = max(need_t, need_v) + hx
        x0, y0, x1, y1 = win(bbox(it, m))
        if x1 <= x0 or y1 <= y0: continue
        D = dist_field(it, x0, y0, x1, y1)
        for l in it['layers']: trk[l, y0:y1, x0:x1] |= D < need_t + (hx if it.get('npth') else 0)
        via[y0:y1, x0:x1] |= D < (need_v + hx)
    for z in KEEP:   # no foreign copper under an inductor, on any layer
        if net in z['own']: continue
        m_ = width / 2 + clr
        x0, y0, x1, y1 = win((z['box'][0] - m_, z['box'][1] - m_, z['box'][2] + m_, z['box'][3] + m_))
        # power may pass on B.Cu, under the In1 plane; signals keep off every layer
        if ncls(net) in ('Heavy', 'Wide', 'Power'): trk[0:2, y0:y1, x0:x1] = True
        else: trk[:, y0:y1, x0:x1] = True
        x0, y0, x1, y1 = win((z['box'][0] - viar - clr, z['box'][1] - viar - clr, z['box'][2] + viar + clr, z['box'][3] + viar + clr))
        via[y0:y1, x0:x1] = True
    e = int(math.ceil((EDGE + width / 2) / R))
    for l in range(3):
        trk[l, :e, :] = trk[l, -e:, :] = True; trk[l, :, :e] = trk[l, :, -e:] = True
    ev = int(math.ceil((EDGE + viar) / R)); via[:ev, :] = via[-ev:, :] = True; via[:, :ev] = via[:, -ev:] = True
    return trk, via
# #endregion

# #region islands of one net
def islands(net):
    mine = [it for it in items if it['net'] == net]
    par = list(range(len(mine)))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    for i in range(len(mine)):
        for j in range(i + 1, len(mine)):
            a, b = mine[i], mine[j]
            if not (a['layers'] & b['layers']): continue
            ba, bb = bbox(a, 0.01), bbox(b, 0.01)
            if ba[0] > bb[2] or bb[0] > ba[2] or ba[1] > bb[3] or bb[1] > ba[3]: continue
            x0, y0, x1, y1 = win((max(ba[0], bb[0]), max(ba[1], bb[1]), min(ba[2], bb[2]), min(ba[3], bb[3])))
            if x1 <= x0 or y1 <= y0: continue
            if ((dist_field(a, x0, y0, x1, y1) < 0.01) & (dist_field(b, x0, y0, x1, y1) < 0.01)).any(): par[f(i)] = f(j)
    return mine, [f(i) for i in range(len(mine))]

def cells_of(group, width):
    """grid cells (layer, j, i) inside the copper of these items, far enough in for a track end."""
    out = set()
    for it in group:
        x0, y0, x1, y1 = win(bbox(it, 0))
        D = dist_field(it, x0, y0, x1, y1)
        js, is_ = np.nonzero(D < 0.001)
        for l in it['layers']:
            for j, i in zip(js, is_): out.add((l, y0 + j, x0 + i))
    return out
# #endregion

def find_item(desc, pos):
    m = re.match(r'(?:PTH |NPTH )?[Pp]ad (\S+) \[([^\]]*)\] of (\S+)', desc)
    if m:
        for it in items:
            if it['kind'] == 'pad' and it['ref'] == m.group(3) and it['num'] == m.group(1): return it
    m = re.match(r'(Track|Via) \[([^\]]*)\]', desc)
    if m:
        best = None
        for it in items:
            if it['net'] != m.group(2): continue
            if m.group(1) == 'Via' and it['kind'] == 'via': dd = math.dist(it['c'], (pos['x'], pos['y']))
            elif m.group(1) == 'Track' and it['kind'] == 'track':
                mid = ((it['a'][0] + it['b'][0]) / 2, (it['a'][1] + it['b'][1]) / 2)
                dd = min(math.dist(p, (pos['x'], pos['y'])) for p in (it['a'], it['b'], mid))
            else: continue
            if best is None or dd < best[0]: best = (dd, it)
        return best[1] if best and best[0] < 0.05 else None
    return None

STEPS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
def astar(starts, goals, trk, via, layers, viacost):
    goal = {c for c in goals if c[0] in layers and not trk[c]}
    st = [c for c in starts if c[0] in layers and not trk[c]]
    if not goal or not st: return None
    gl = np.array([(j, i) for _, j, i in goal])
    def h(j, i): return float(np.min(np.abs(gl[:, 0] - j) + np.abs(gl[:, 1] - i))) * 0.8 if len(gl) < 400 else 0.0
    cy, cx = gl[:, 0].mean(), gl[:, 1].mean()
    def h2(j, i): return math.hypot(j - cy, i - cx) * 0.7
    openl = []; came = {}; cost = {}
    for c in st: cost[c] = 0.0; heapq.heappush(openl, (h2(c[1], c[2]), 0.0, c)); came[c] = None
    n = 0
    while openl:
        f, gc, c = heapq.heappop(openl)
        if gc > cost.get(c, 1e18): continue
        if c in goal:
            path = []
            while c is not None: path.append(c); c = came[c]
            return path[::-1]
        n += 1
        if n > 3_000_000: return None
        l, j, i = c
        for dj, di, w in STEPS:
            q = (l, j + dj, i + di)
            if not (0 <= q[1] < NY and 0 <= q[2] < NX) or trk[q]: continue
            ng = gc + w
            if ng < cost.get(q, 1e18): cost[q] = ng; came[q] = c; heapq.heappush(openl, (ng + h2(q[1], q[2]), ng, q))
        if not via[j, i]:
            for l2 in layers:
                if l2 == l or trk[l2, j, i]: continue
                q = (l2, j, i); ng = gc + viacost
                if ng < cost.get(q, 1e18): cost[q] = ng; came[q] = c; heapq.heappush(openl, (ng + h2(j, i), ng, q))
    return None

def emit(path, net, width, vd, vdr):
    out = []; segs = []
    def P(c): return (X0 + c[2] * R, Y0 + c[1] * R)
    run = [path[0]]
    for a, b in zip(path, path[1:]):
        if b[0] != a[0]:
            segs.append((run, a[0])); x, y = P(a)
            out.append(f'\n\t(via\n\t\t(at {x:.4f} {y:.4f})\n\t\t(size {vd:g})\n\t\t(drill {vdr:g})\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "{net}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
            items.append(dict(kind='via', net=net, layers={0, 1, 2}, c=[x, y], r=vd / 2, hole=True, txt=out[-1]))
            run = [b]
        else: run.append(b)
    segs.append((run, path[-1][0]))
    for run, l in segs:
        if len(run) < 2: continue
        pts = [run[0]]
        for k in range(1, len(run) - 1):
            d1 = (run[k][1] - run[k - 1][1], run[k][2] - run[k - 1][2]); d2 = (run[k + 1][1] - run[k][1], run[k + 1][2] - run[k][2])
            if d1 != d2: pts.append(run[k])
        pts.append(run[-1])
        for a, b in zip(pts, pts[1:]):
            (xa, ya), (xb, yb) = P(a), P(b)
            out.append(f'\n\t(segment\n\t\t(start {xa:.4f} {ya:.4f})\n\t\t(end {xb:.4f} {yb:.4f})\n\t\t(width {width:g})\n\t\t(layer "{LAY[l]}")\n\t\t(net "{net}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
            items.append(dict(kind='track', net=net, layers={l}, a=[xa, ya], b=[xb, yb], w=width, txt=out[-1]))
    return out

new = []; report = []; ripped_text = []
def join(net, A, Bb, label):
    """route between two islands of one net; True on success"""
    cls = ncls(net); c = CLS[cls]
    power = cls in ('Heavy', 'Wide', 'Power')
    layers = [0, 2] if power else [0, 1, 2]
    widths = [c['track_width']] + [w for w in (1.2, 0.8, 0.5, 0.3) if w < c['track_width']] if power else [c['track_width']]
    def small_only(isl):
        pads = [it for it in isl if it['kind'] == 'pad']
        return pads and all(not it['ref'].startswith('J') and (it['box'][2] - it['box'][0]) * (it['box'][3] - it['box'][1]) < 1.2 for it in pads)
    lowcur = power and (small_only(A) or small_only(Bb))
    if lowcur: layers = [0, 1, 2]; widths = [0.4, 0.3, 0.2]
    tries = [(w, layers) for w in widths]
    if cls == 'Power' and not lowcur: tries += [(0.8, [0, 1, 2]), (0.6, [0, 1, 2])]   # pulse and sense paths may dive to In2
    for w, layers in tries:
        vd, vdr = (0.8, 0.4) if power and not lowcur else (0.6, 0.3)
        trk, via = blocked_map(net, w, 0.15 if lowcur else c['clearance'], vd / 2)
        path = astar(cells_of(A, w), cells_of(Bb, w), trk, via, layers, 3.0 / R)
        if path:
            global new
            L = sum(math.hypot(p[1] - q[1], p[2] - q[2]) for p, q in zip(path, path[1:]) if p[0] == q[0]) * R
            direct = math.hypot(path[0][1] - path[-1][1], path[0][2] - path[-1][2]) * R
            if power and L > 2.5 * direct + 12:   # a power detour round half the board is not a route
                report.append(('detour refused', label, net, round(L, 1), round(direct, 1))); continue
            new += emit(path, net, w, vd, vdr)
            new += anchor(path[0], A, net, w) + anchor(path[-1], Bb, net, w)
            report.append(('routed', label, net, w, round(L, 1), sum(1 for p, q in zip(path, path[1:]) if p[0] != q[0]), 'pin branch' if lowcur else '', sorted({LAY[p[0]] for p in path})))
            return True
    return False

def anchor(cell, group, net, w):
    """a short stub from a path end to the exact centre line of the copper it lands on,
    so KiCad sees the join (a grid point inside a track is not always on it)"""
    l, j, i = cell; P = (X0 + i * R, Y0 + j * R); best = None
    for it in group:
        if l not in it['layers']: continue
        if it['kind'] == 'track':
            a, b = it['a'], it['b']; dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
            t = 0 if L2 == 0 else max(0, min(1, ((P[0] - a[0]) * dx + (P[1] - a[1]) * dy) / L2))
            q = (a[0] + t * dx, a[1] + t * dy)
        elif it['kind'] == 'via': q = tuple(it['c'])
        else:
            bx = it['box']; q = (min(max(P[0], bx[0] + 0.05), bx[2] - 0.05), min(max(P[1], bx[1] + 0.05), bx[3] - 0.05))
        d_ = math.dist(P, q)
        cap = it['w'] if it['kind'] == 'track' else (2 * it['r'] if it['kind'] == 'via' else min(it['box'][2] - it['box'][0], it['box'][3] - it['box'][1]))
        if best is None or d_ < best[0]: best = (d_, q, cap)
    if not best or best[0] < 0.005 or best[0] > 0.4: return []
    q = best[1]; w = min(w, best[2])
    return [f'\n\t(segment\n\t\t(start {q[0]:.4f} {q[1]:.4f})\n\t\t(end {P[0]:.4f} {P[1]:.4f})\n\t\t(width {w:g})\n\t\t(layer "{LAY[l]}")\n\t\t(net "{net}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)']

def rip_near(group, keep_net, rad=0.45):
    """remove foreign tracks within 0.45 mm of the small pads in these islands; returns their nets"""
    pads = [it for it in group if it['kind'] == 'pad' and (it['box'][2] - it['box'][0]) * (it['box'][3] - it['box'][1]) < 1.2]
    gone = []
    for it in list(items):
        if it['kind'] not in ('track', 'via') or it['net'] in (keep_net, '') or it['net'].startswith('ETH'): continue
        if it['net'] == 'GND' and rad < 1.0: continue
        for pd in pads:
            if not (it['layers'] & pd['layers']): continue
            x0, y0, x1, y1 = win(bbox(pd, rad))
            if x1 <= x0 or y1 <= y0: continue
            if (dist_field(it, x0, y0, x1, y1)[:, :] < 0.001).any():
                items.remove(it); gone.append(it); break
    return gone

def reconnect(net, label):
    for _ in range(40):
        mine, root = islands(net)
        groups = {}
        for it, r in zip(mine, root): groups.setdefault(r, []).append(it)
        if len(groups) < 2: return True
        gl = sorted(groups.values(), key=len, reverse=True)
        if not join(net, gl[0], [it for g2 in gl[1:] for it in g2], label): return False
    return False

def gnd_orphans():
    """front GND SMD pads with no GND track or via touching them"""
    out = []
    gi = [it for it in items if it['net'] == 'GND' and it['kind'] in ('track', 'via')]
    for pd in items:
        if pd['kind'] != 'pad' or pd['net'] != 'GND' or pd.get('hole') or pd['layers'] != {0}: continue
        b = pd['box']
        if (b[2] - b[0]) > 1.5 and (b[3] - b[1]) > 1.5: continue      # exposed pads carry their own vias
        touch = False
        for it in gi:
            x0, y0, x1, y1 = win(bbox(pd, 0.01))
            if x1 > x0 and y1 > y0 and (dist_field(it, x0, y0, x1, y1) < 0.005).any(): touch = True; break
        if not touch: out.append(pd)
    return out

def via_escape(pd):
    """a short F.Cu stub from a GND pad to the nearest spot a via fits: the In1 plane does the rest"""
    global new
    trk, via = blocked_map('GND', 0.25, 0.15, 0.3)
    cx, cy = (pd['box'][0] + pd['box'][2]) / 2, (pd['box'][1] + pd['box'][3]) / 2
    goal = set()
    for j in range(max(0, gy(cy - 3)), min(NY, gy(cy + 3))):
        for i in range(max(0, gx(cx - 3)), min(NX, gx(cx + 3))):
            if not via[j, i] and not trk[0, j, i]: goal.add((0, j, i))
    path = astar(cells_of([pd], 0.25), goal, trk, via, [0], 1e9)
    if not path: return False
    new += emit(path, 'GND', 0.25, 0.6, 0.3)
    x, y = X0 + path[-1][2] * R, Y0 + path[-1][1] * R
    new.append(f'\n\t(via\n\t\t(at {x:.4f} {y:.4f})\n\t\t(size 0.6)\n\t\t(drill 0.3)\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "GND")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
    items.append(dict(kind='via', net='GND', layers={0, 1, 2}, c=[x, y], r=0.3, hole=True))
    return True

def seg_key(it):
    return (round(it['a'][0], 3), round(it['a'][1], 3), round(it['b'][0], 3), round(it['b'][1], 3))

def _cls_of(u):
    m = re.search(r'\[([^\]]*)\]', u['items'][0]['description'])
    return 1 if m and ncls(m.group(1)) in ('Heavy', 'Wide', 'Power') else 0
for u in sorted(d['unconnected_items'], key=_cls_of):   # signals first: power can go round, a pin cannot
    a, b = u['items'][0], u['items'][1]
    ia, ib = find_item(a['description'], a['pos']), find_item(b['description'], b['pos'])
    if ia is None or ib is None: report.append(('no item', a['description'][:40], b['description'][:40])); continue
    net = ia['net']
    mine, root = islands(net)
    ka = root[mine.index(ia)]; kb = root[mine.index(ib)]
    if ka == kb: report.append(('already joined', net)); continue
    A = [it for it, r in zip(mine, root) if r == ka]; Bb = [it for it, r in zip(mine, root) if r == kb]
    if join(net, A, Bb, 'direct'): continue
    success = False
    for rad in (0.45, 1.2, 2.0, 3.0, 4.5):
        snap_items = list(items); snap_new = len(new); snap_rep = len(report)
        gone = rip_near([x for x in (ia, ib) if x['kind'] == 'pad'], net, rad)
        if not gone: continue
        ok = join(net, A, Bb, 'after rip-up %.2f' % rad)
        fixed = ok and all(reconnect(n, 'reroute ' + n) for n in sorted({g['net'] for g in gone}) if n != 'GND')
        if fixed and any(g['net'] == 'GND' for g in gone):
            fixed = all(via_escape(pd) for pd in gnd_orphans())
        if ok and fixed:
            for g_ in gone:
                if 'txt' in g_ and g_['txt'] in new: new.remove(g_['txt'])
            ripped_text += [g_ for g_ in gone if 'txt' not in g_]; success = True
            report.append(('ripped', rad, [g['net'] for g in gone], 'target ok', 'reroutes ok')); break
        items[:] = snap_items; del new[snap_new:]; del report[snap_rep:]
    if not success: report.append(('FAILED even with rip-up', net, a['description'][:40], b['description'][:40]))

# drop the ripped segments from the file
N_ = r"(-?[\d.]+)"
dead = {(g['net'], LAY[next(iter(g['layers']))], seg_key(g)) for g in ripped_text if g['kind'] == 'track'}
deadv = {(g['net'], round(g['c'][0], 3), round(g['c'][1], 3)) for g in ripped_text if g['kind'] == 'via'}
def killv(m):
    b_ = m.group(0)
    net_ = re.search(r'\(net "([^"]*)"\)', b_); net_ = net_.group(1) if net_ else ''
    at = re.search(r"\(at " + N_ + " " + N_, b_)
    return '' if (net_, round(float(at.group(1)), 3), round(float(at.group(2)), 3)) in deadv else b_
s = re.sub(r"\n\t\(via\n.*?\n\t\)", killv, s, flags=re.S)
def kill(m):
    b_ = m.group(0)
    net_ = re.search(r'\(net "([^"]*)"\)', b_); net_ = net_.group(1) if net_ else ''
    lay = re.search(r'\(layer "([^"]*)"', b_).group(1)
    st = re.search(r"\(start " + N_ + " " + N_, b_); en = re.search(r"\(end " + N_ + " " + N_, b_)
    k = (round(float(st.group(1)), 3), round(float(st.group(2)), 3), round(float(en.group(1)), 3), round(float(en.group(2)), 3))
    return '' if (net_, lay, k) in dead else b_
s = re.sub(r"\n\t\(segment\n.*?\n\t\)", kill, s, flags=re.S)
last = max(s.rfind("\n\t(segment\n"), s.rfind("\n\t(via\n")); end = s.index("\n\t)", last) + 3
s = s[:end] + "".join(new) + s[end:]
open(OUT, 'w').write(s)
for r in report: print(*r)
