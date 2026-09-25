"""A GND via for every front SMD ground pad: short 0.4 mm stub to a 0.6/0.3 via
into the back pour, at the first spot around the pad that clears every other
net on both layers (0.2 mm), holes, other vias and the board edge."""
import json, math, re, uuid
g = json.load(open("padgeo.json")); s = open("board.kicad_pcb").read()
import sys
NET = sys.argv[1]
VIA_R, DRILL, CL, STUB = 0.3, 0.3, 0.2, 0.4
def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = 0 if dx == dy == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)
def box_dist(p, bx):
    dx = max(bx[0] - p[0], 0, p[0] - bx[2]); dy = max(bx[1] - p[1], 0, p[1] - bx[3]); return math.hypot(dx, dy)
def seg_box_dist(a, b, bx):
    n = max(2, int(math.hypot(b[0]-a[0], b[1]-a[1]) / 0.1)); return min(box_dist((a[0]+(b[0]-a[0])*i/n, a[1]+(b[1]-a[1])*i/n), bx) for i in range(n+1))
others = [p for p in g["pads"] if p["net"] != NET or p["npth"]]
new = []; placed = []
targets = [p for p in g["pads"] if p["net"] == NET and p["smd"] and not p["back"]]
fail = []
def via_block(x, y):
    return f'\n\t(via\n\t\t(at {x:.4f} {y:.4f})\n\t\t(size {2*VIA_R})\n\t\t(drill {DRILL})\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "{NET}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)'
for p in targets:
    bx = p["box"]; cx, cy = p["c"]; hw, hh = (bx[2] - bx[0]) / 2, (bx[3] - bx[1]) / 2
    # exposed pads: thermal vias inside the pad (2 x 2), unless the footprint already has them
    if hw >= 1.0 and hh >= 1.0 and p["num"] in ("9", "15", "17", "EP", "21", "25", "33", "49"):
        own = [w for w in g["vias"] if w["net"] == NET and box_dist(w["c"], bx) == 0]
        hasth = any(q["net"] == NET and not q["smd"] and q["ref"] == p["ref"] for q in g["pads"])
        if not own and not hasth:
            for ox in (-0.5, 0.5):
                for oy in (-0.5, 0.5):
                    vx, vy = cx + ox * min(hw, 1.2), cy + oy * min(hh, 1.2)
                    new.append(via_block(vx, vy)); placed.append({"c": [vx, vy], "r": VIA_R, "net": NET})
            continue
    stub_w = min(STUB, 2 * hw, 2 * hh)
    # a pin beside its own part's exposed ground pad: a short stub into that pad, no via
    ep = [q for q in g["pads"] if q["ref"] == p["ref"] and q["net"] == NET and q is not p and (q["box"][2] - q["box"][0]) > 1.5 and (q["box"][3] - q["box"][1]) > 1.5]
    if ep and min(hw, hh) < 0.3:
        e = ep[0]["box"]; ex, ey = min(max(cx, e[0] + 0.3), e[2] - 0.3), min(max(cy, e[1] + 0.3), e[3] - 0.3)
        if abs(ex - cx) < 0.01 or abs(ey - cy) < 0.01:   # straight in along the pin axis
            gap = max(e[0] - bx[2], bx[0] - e[2], e[1] - bx[3], bx[1] - e[3])
            if gap < 0.8:
                new.append(f'\n\t(segment\n\t\t(start {cx:.4f} {cy:.4f})\n\t\t(end {ex:.4f} {ey:.4f})\n\t\t(width {min(0.3, 2 * min(hw, hh)):g})\n\t\t(layer "F.Cu")\n\t\t(net "{NET}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
                placed_ep = True
                continue
    fine = min(hw, hh) < 0.2      # 0.5-0.65 mm pitch pins: keep the via out of the neighbours' exits
    best = None
    for d in ((1.0, 1.4, 1.8, 2.2) if fine else (0.25, 0.6, 1.0, 1.5, 2.0)):
        for ang in range(0, 360, 15):
            ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            # distance from the center to the pad edge along this direction
            k = min(hw / abs(ux) if abs(ux) > 1e-6 else 1e9, hh / abs(uy) if abs(uy) > 1e-6 else 1e9)
            v = (cx + ux * (k + d + VIA_R), cy + uy * (k + d + VIA_R))
            s0 = (cx + ux * max(k - 0.05, 0), cy + uy * max(k - 0.05, 0))   # stub starts at the pad edge
            e = g["edge"]
            if not (e[0] + 0.6 < v[0] < e[2] - 0.6 and e[1] + 0.6 < v[1] < e[3] - 0.6): continue
            ok = True
            for q in others:
                if box_dist(v, q["box"]) < VIA_R + CL: ok = False; break
                if q["ref"] == p["ref"] and q["num"] == p["num"]: continue
                if seg_box_dist(s0, v, q["box"]) < stub_w / 2 + (0.3 if q["npth"] else CL): ok = False; break
            if not ok: continue
            for q in g["pads"]:   # other GND pads: not into the middle of another pad
                if q["net"] == NET and q is not p and box_dist(v, q["box"]) < VIA_R + 0.1: ok = False; break
            if not ok: continue
            for t in g["tracks"]:
                if t["net"] == NET: continue
                if seg_dist(v, t["a"], t["b"]) < VIA_R + t["w"] / 2 + CL: ok = False; break
                if t["layer"] == "F.Cu":
                    n = 6
                    for i in range(n + 1):
                        q = (s0[0] + (v[0] - s0[0]) * i / n, s0[1] + (v[1] - s0[1]) * i / n)
                        if seg_dist(q, t["a"], t["b"]) < stub_w / 2 + t["w"] / 2 + CL: ok = False; break
                    if not ok: break
            if not ok: continue
            for w in g["vias"] + placed:
                need = (VIA_R + w["r"] + (0.3 if w["net"] == NET else CL))
                if math.hypot(v[0] - w["c"][0], v[1] - w["c"][1]) < need: ok = False; break
            if not ok: continue
            best = v; break
        if best: break
    if not best: fail.append(f'{p["ref"]}.{p["num"]}'); continue
    placed.append({"c": list(best), "r": VIA_R, "net": NET})
    new.append(f'\n\t(segment\n\t\t(start {cx:.4f} {cy:.4f})\n\t\t(end {best[0]:.4f} {best[1]:.4f})\n\t\t(width {stub_w:g})\n\t\t(layer "F.Cu")\n\t\t(net "{NET}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
    new.append(f'\n\t(via\n\t\t(at {best[0]:.4f} {best[1]:.4f})\n\t\t(size {2*VIA_R})\n\t\t(drill {DRILL})\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "{NET}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
last = max(s.rfind("\n\t(segment\n"), s.rfind("\n\t(via\n")); end = s.index("\n\t)", last) + 3
s = s[:end] + "".join(new) + s[end:]
open("board.kicad_pcb", "w").write(s)
print(f"front {NET} pads {len(targets)}: vias added {len(placed)}, no spot {len(fail)}: {fail}")
