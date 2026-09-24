"""Update board.kicad_pcb from netlist.net the way KiCad's "Update PCB from
schematic" does, without touching routing: pads get their new nets, tracks and
vias follow the pads they touch, new parts are parked right of the board, and a
footprint is swapped only where the land pattern really changed. Anything the
script cannot decide (a run of copper that now spans two nets) is printed, not
cut. Runs inside the kicad:10.0 container with /work = project, /lcsc.pretty =
loon's LCSC footprints.
"""
import os, re, sys, collections
import pcbnew

BOARD = "/work/board.kicad_pcb"
NETLIST = "/work/netlist.net"
KEEP_FOOTPRINT = {"Q20"}  # AO4482 on the EP land pattern: the pad is just unused
MM = 1_000_000

# #region netlist parser
def parse(text):
    tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text)
    def build(i):
        out = []
        while i < len(tok):
            t = tok[i]
            if t == "(":
                sub, i = build(i + 1); out.append(sub)
            elif t == ")":
                return out, i + 1
            else:
                out.append(t[1:-1].replace('\\"', '"') if t.startswith('"') else t); i += 1
        return out, i
    return build(0)[0][0]

def kids(node, key):
    return [n for n in node[1:] if isinstance(n, list) and n and n[0] == key]

def kid(node, key):
    k = kids(node, key)
    return k[0] if k else None

nl = parse(open(NETLIST).read())
comps = {}
for c in kids(kid(nl, "components"), "comp"):
    ref = kid(c, "ref")[1]
    fields = {kid(f, "name")[1]: (f[2] if len(f) > 2 and isinstance(f[2], str) else "") for f in kids(kid(c, "fields") or ["fields"], "field")}
    comps[ref] = {"value": (kid(c, "value") or ["", ""])[1], "footprint": (kid(c, "footprint") or ["", ""])[1], "fields": fields}
padnet = {}
netnames = []
for n in kids(kid(nl, "nets"), "net"):
    name = kid(n, "name")[1].lstrip("/")  # local labels come out as "/NAME"
    nodes = kids(n, "node")
    if not nodes or name.startswith("unconnected-"):
        continue
    netnames.append(name)
    for node in nodes:
        padnet[(kid(node, "ref")[1], kid(node, "pin")[1])] = name
print(f"netlist: {len(comps)} parts, {len(netnames)} nets, {len(padnet)} pins")

# #region footprint libraries
STD = "/usr/share/kicad/footprints"
def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    path = "/lcsc.pretty" if lib == "LCSC" else f"{STD}/{lib}.pretty"
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"footprint not found: {fpid}")
    return fp

board = pcbnew.LoadBoard(BOARD)
by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}
edge = board.GetBoardEdgesBoundingBox()

# #region parts
swapped, added, removed = [], [], []
park_x0 = edge.GetRight() + 8 * MM
px, py, row_h = park_x0, edge.GetTop() + 2 * MM, 0
PARK_W = 70 * MM

# reference text like the rest of the board (loon sets 0.8 mm); value stays on F.Fab
sample = by_ref["R96"].Reference()
def ref_style(fp):
    fp.Reference().SetTextSize(sample.GetTextSize())
    fp.Reference().SetTextThickness(sample.GetTextThickness())

def set_fields(fp, c):
    fp.SetValue(c["value"])
    lcsc = c["fields"].get("LCSC")
    if lcsc:
        fp.SetField("LCSC", lcsc)
        for f in fp.GetFields():
            if f.GetName() == "LCSC":
                f.SetVisible(False)

for ref, c in sorted(comps.items(), key=lambda kv: (re.sub(r"\d+", "", kv[0]), int(re.sub(r"\D", "", kv[0]) or 0))):
    fp = by_ref.get(ref)
    if fp is not None:
        old = fp.GetFPIDAsString()
        if old != c["footprint"] and ref not in KEEP_FOOTPRINT:
            new = load_fp(c["footprint"])
            new.SetReference(ref)
            new.SetPosition(fp.GetPosition())
            if fp.IsFlipped():
                new.Flip(new.GetPosition(), False)
            new.SetOrientation(fp.GetOrientation())
            ref_style(new)
            set_fields(new, c)
            board.Remove(fp)
            board.Add(new)
            by_ref[ref] = new
            swapped.append(f"{ref}: {old} -> {c['footprint']}")
        else:
            set_fields(fp, c)
    else:
        new = load_fp(c["footprint"])
        new.SetReference(ref)
        ref_style(new)
        set_fields(new, c)
        bb = new.GetBoundingBox(False, False)
        w, h = bb.GetWidth() + 2 * MM, bb.GetHeight() + 2 * MM
        if px + w > park_x0 + PARK_W:
            px, py, row_h = park_x0, py + row_h, 0
        new.SetPosition(pcbnew.VECTOR2I(int(px + w // 2), int(py + h // 2)))
        px += w
        row_h = max(row_h, h)
        board.Add(new)
        by_ref[ref] = new
        added.append(ref)

# board-only parts (mounting holes, logos) are not in the schematic: keep them
for ref, fp in list(by_ref.items()):
    if ref not in comps and any(p.GetNetname() for p in fp.Pads()):
        board.Remove(fp)
        del by_ref[ref]
        removed.append(ref)

# #region nets
nets = board.GetNetInfo()
def net_of(name):
    n = nets.GetNetItem(name)
    if n is None or n.GetNetCode() <= 0 and name:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
    return n

# loon's USB-C USB2.0 symbol carries one pin per ganged pair; the footprint has both
ALIAS = {"A9": "A4", "B9": "B4", "A12": "A1", "B12": "B1"}
changed_pads = []
for ref, fp in by_ref.items():
    for pad in fp.Pads():
        num = pad.GetNumber()
        name = padnet.get((ref, num), "") or padnet.get((ref, ALIAS.get(num, num)), "")
        old = pad.GetNetname()
        if old != name:
            changed_pads.append((ref, pad.GetNumber(), old, name))
        if name:
            pad.SetNet(net_of(name))
        else:
            pad.SetNetCode(0)

# #region copper follows pads
# Own connectivity: a track end that lands on a pad, a via or another track of
# the same layer joins them. Every cluster with exactly one pad net takes it.
tracks = [t for t in board.GetTracks()]
pads = [(fp.GetReference(), p) for fp in by_ref.values() for p in fp.Pads()]
parent = {}
def find(a):
    while parent.setdefault(a, a) != a:
        parent[a] = parent[parent[a]]; a = parent[a]
    return a
def union(a, b):
    parent[find(a)] = find(b)

def is_via(t):
    return t.Type() == pcbnew.PCB_VIA_T

def layers_of(t):
    if is_via(t):
        return None  # all copper
    return {t.GetLayer()}

def ends(t):
    return [t.GetPosition()] if is_via(t) else [t.GetStart(), t.GetEnd()]

track_id = {id(t): i for i, t in enumerate(tracks)}
for i, t in enumerate(tracks):
    for p in ends(t):
        for j, u in enumerate(tracks):
            if i == j:
                continue
            if not is_via(t) and not is_via(u) and t.GetLayer() != u.GetLayer():
                continue
            if u.HitTest(p, 0):
                union(("t", i), ("t", j))
        for k, (ref, pad) in enumerate(pads):
            if (is_via(t) or pad.IsOnLayer(t.GetLayer())) and pad.HitTest(p, 0):
                union(("t", i), ("p", k))

clusters = collections.defaultdict(lambda: {"tracks": [], "nets": [], "pads": []})
for i, t in enumerate(tracks):
    clusters[find(("t", i))]["tracks"].append(t)
for k, (ref, pad) in enumerate(pads):
    if ("p", k) in parent:
        c = clusters[find(("p", k))]
        c["nets"].append(pad.GetNetname())
        c["pads"].append(f"{ref}.{pad.GetNumber()}")

renamed, conflicts, orphans = 0, [], 0
for c in clusters.values():
    nets_ = {n for n in c["nets"] if n}
    if len(nets_) == 1:
        name = next(iter(nets_))
        for t in c["tracks"]:
            if t.GetNetname() != name:
                t.SetNet(net_of(name)); renamed += 1
    elif len(nets_) > 1:
        # name the pads on the minority net: that is the stub to cut
        count = collections.Counter(n for n in c["nets"] if n)
        minority = [n for n in nets_ if count[n] < max(count.values())] or sorted(nets_)
        stubs = []
        for k, (ref, pad) in enumerate(pads):
            if ("p", k) in parent and find(("p", k)) == find(("t", tracks.index(c["tracks"][0]))) and pad.GetNetname() in minority:
                stubs.append(f"{ref}.{pad.GetNumber()} ({pad.GetNetname()}) at {round(pad.GetPosition().x / MM, 2)},{round(pad.GetPosition().y / MM, 2)}")
        conflicts.append((sorted(nets_), len(c["tracks"]), stubs))
    else:
        orphans += len(c["tracks"])

board.Save(BOARD)

print(f"swapped footprints ({len(swapped)}):"); [print("  " + s) for s in swapped]
print(f"added ({len(added)}), parked right of the board: {' '.join(added)}")
print(f"removed ({len(removed)}): {' '.join(removed)}")
print(f"pads re-netted: {len(changed_pads)}")
for ref, num, old, new in changed_pads:
    if old and new and old != new and ref not in added:
        print(f"  {ref}.{num}: {old} -> {new}")
print(f"tracks/vias re-netted by connectivity: {renamed}; copper touching no pad: {orphans}")
print(f"CONFLICTS ({len(conflicts)}): copper now spanning more than one net, left as is")
for nets_, n, stubs in conflicts:
    print(f"  nets {nets_}: {n} copper items; cut the stub to " + "; ".join(stubs))
