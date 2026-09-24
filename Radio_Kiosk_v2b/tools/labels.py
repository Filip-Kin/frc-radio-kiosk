"""Silkscreen label placer.

Every visible front-silk field (reference, or a value Filip put on silk such as
"UART") goes just outside its part's courtyard: above, below, left or right,
horizontal first, vertical only if nothing horizontal fits. A spot is taken only
if the text box clears every pad, every courtyard, every other label, part
silk, board graphics, holes and the board edge. Parts are served most
constrained first. Anything with no spot is reported, never hidden.
Text edit of board.kicad_pcb; geometry from geo2.json (dump.py).
"""
import json, math, re, sys

BOARD = "board.kicad_pcb"
g = json.load(open("geo2.json"))
s = open(BOARD).read()
NUM = r"(-?\d+(?:\.\d+)?)"
CLEAR = 0.12            # text box to anything
GAP = 0.2               # text to its own courtyard
EDGE = 0.5              # text to board edge

def rot(x, y, a):
    t = math.radians(a)
    return x * math.cos(t) + y * math.sin(t), -x * math.sin(t) + y * math.cos(t)

def hit(a, b, m=0.0):
    return a[0] - m < b[2] and a[2] + m > b[0] and a[1] - m < b[3] and a[3] + m > b[1]

# #region fields to place: (ref, prop name, text, size, thickness)
fields = []
blocks = {}
for m in re.finditer(r'\n\t\(footprint "[^"]*"\n.*?\n\t\)', s, re.S):
    b = m.group(0)
    ref = re.search(r'\(property "Reference" "([^"]*)"', b).group(1)
    blocks[ref] = b
    for p in re.finditer(r'\n\t\t\(property "(Reference|Value)" "([^"]*)"\n\t\t\t\(at [^)]*\)\n\t\t\t\(layer "[FB]\.SilkS"\)(.*?)\n\t\t\)', b, re.S):
        if "(hide yes)" in p.group(3): continue
        sz = re.search(r"\(size " + NUM + " " + NUM + r"\)", p.group(3))
        th = re.search(r"\(thickness " + NUM + r"\)", p.group(3))
        fields.append((ref, p.group(1), p.group(2), float(sz.group(2)) if sz else 0.8, float(th.group(1)) if th else 0.12))

fp = {f["ref"]: f for f in g["fp"]}
def crt(ref):
    """courtyard grown to the pads: some library parts put pads past the courtyard"""
    f = fp[ref]
    b = list(f["crt"] or f["body"])
    for p in f["pads"]:
        b = [min(b[0], p[0]), min(b[1], p[1]), max(b[2], p[2]), max(b[3], p[3])]
    return b

# #region obstacles common to everyone
edge = g["edge"]
# obstacles per side: pads of both sides (through-hole pads show on both), the
# side's courtyards and part silk, board graphics, holes
static = {"F": [], "B": []}
for f in g["fp"]:
    side = "B" if f["back"] else "F"
    for sd in ("F", "B"): static[sd] += [(p, f["ref"]) for p in f["pads"]] if (sd == side) else []
    static[side].append((crt(f["ref"]), f["ref"]))
    static[side] += [(sb, f["ref"]) for sb in f["silk"]]
for f in g["fp"]:   # through-hole pads of the other side
    other = "F" if f["back"] else "B"
    static[other] += [(p, None) for p in f["pads"] if (p[2] - p[0]) > 1.0 and (p[3] - p[1]) > 1.0 and f["ref"][:2] in ("BT", "J1", "J2", "J3", "J5", "J6", "J8", "J9", "J1", "H1", "H2", "H3", "H4")]
for sd in ("F", "B"):
    static[sd] += [(h, None) for h in g["holes"]]
static["F"] += [(t["box"], None) for t in g["gr"] if t["layer"] == "F.Silkscreen"]
static["B"] += [(t["box"], None) for t in g["gr"] if t["layer"] == "B.Silkscreen"]

def text_box(cx, cy, text, size, th, vertical):
    w = len(text) * size * 0.92 + th; h = size + th
    if vertical: w, h = h, w
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

def candidates(ref, text, size, th):
    l, t, r, b = crt(ref)
    out = []
    for vertical in (False, True):
        tw = len(text) * size * 0.92 + th; tt = size + th
        w, h = (tt, tw) if vertical else (tw, tt)
        cxs = [(l + r) / 2, l + w / 2, r - w / 2, l - w / 2 + 1.0, r + w / 2 - 1.0]
        cys = [(t + b) / 2, t + h / 2, b - h / 2]
        for gi, gap in enumerate((GAP, 0.6, 1.1)):
            sides = [("above", [(cx, t - gap - h / 2) for cx in cxs]), ("below", [(cx, b + gap + h / 2) for cx in cxs]),
                     ("left", [(l - gap - w / 2, cy) for cy in cys]), ("right", [(r + gap + w / 2, cy) for cy in cys])]
            for si, (name, pts) in enumerate(sides):
                for pi, (cx, cy) in enumerate(pts):
                    score = si + 0.3 * pi + (4 if vertical else 0) + 2.5 * gi
                    out.append((score, cx, cy, vertical, name))
    return sorted(out)

def ok(box, ref, placed):
    if box[0] < edge[0] + EDGE or box[1] < edge[1] + EDGE or box[2] > edge[2] - EDGE or box[3] > edge[3] - EDGE: return False
    side = "B" if fp[ref]["back"] else "F"
    for ob, owner in static[side]:
        if hit(box, ob, CLEAR): return False
    for (r2, _), pb in placed.items():
        if ("B" if fp[r2]["back"] else "F") == side and hit(box, pb, CLEAR + 0.05): return False
    return True

# #region most-constrained-first greedy
placed = {}; choice = {}; todo = list(fields); failed = []; shrunk = set()
while todo:
    opts = []
    for f in todo:
        ref, prop, text, size, th = f
        c = [x for x in candidates(ref, text, size, th) if ok(text_box(x[1], x[2], text, size, th, x[3]), ref, placed)]
        opts.append((len(c), f, c))
    opts.sort(key=lambda o: o[0])
    n, f, c = opts[0]
    todo.remove(f)
    if not c and f[3] > 0.71:
        # last resort for this one part: 0.7 mm text
        f2 = (f[0], f[1], f[2], 0.7, 0.1)
        c = [x for x in candidates(f2[0], f2[2], 0.7, 0.1) if ok(text_box(x[1], x[2], f2[2], 0.7, 0.1, x[3]), f2[0], placed)]
        if c: shrunk.add((f[0], f[1])); f = f2
    if not c: failed.append(f); continue
    sc, cx, cy, vertical, side = c[0]
    placed[(f[0], f[1])] = text_box(cx, cy, f[2], f[3], f[4], vertical)
    choice[(f[0], f[1])] = (cx, cy, vertical, side)

# #region write positions back (local frame of the part, absolute angle)
def edit(m):
    b = m.group(0)
    ref = re.search(r'\(property "Reference" "([^"]*)"', b).group(1)
    f = fp.get(ref)
    if not f: return b
    for prop in ("Reference", "Value"):
        if (ref, prop) not in choice: continue
        cx, cy, vertical, side = choice[(ref, prop)]
        lx, ly = rot(cx - f["x"], cy - f["y"], -f["rot"])
        if f["back"]: lx = -lx   # a flipped part stores its fields mirrored
        ang = 90 if vertical else 0
        b = re.sub(r'(\(property "' + prop + r'" "[^"]*"\n\t\t\t)\(at [^)]*\)',
                   lambda mm: mm.group(1) + f"(at {lx:.3f} {ly:.3f} {ang})", b, count=1)
        if (ref, prop) in shrunk:
            b = re.sub(r'(\(property "' + prop + r'" "[^"]*"\n.*?\(size )[\d.]+ [\d.]+(\)\n\t+\(thickness )[\d.]+',
                       lambda mm: mm.group(1) + "0.7 0.7" + mm.group(2) + "0.1", b, count=1, flags=re.S)
    return b
s = re.sub(r'\n\t\(footprint "[^"]*"\n.*?\n\t\)', edit, s, flags=re.S)
open(BOARD, "w").write(s)
sides = {}
for v in choice.values(): sides[v[3] + (" vertical" if v[2] else "")] = sides.get(v[3] + (" vertical" if v[2] else ""), 0) + 1
print(f"shrunk to 0.7 mm: {sorted(r for r, _ in shrunk)}")
print(f"placed {len(choice)} labels {sides}; no spot for {len(failed)}: {[f[0] + ('' if f[1] == 'Reference' else ' ' + f[2]) for f in failed]}")
