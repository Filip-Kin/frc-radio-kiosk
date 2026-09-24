"""Insert a horizontal band: everything below y = CUT moves down by H.
Footprints move by their origin only (pads and texts inside are relative);
tracks, vias, arcs, zones and board graphics move point by point, so a track
crossing the cut keeps its top end and stretches. Zone fills are dropped
(KiCad refills). Usage: stretch.py board.kicad_pcb CUT H"""
import re, sys
path, CUT, H = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
s = open(path).read()
NUM = r"(-?\d+(?:\.\d+)?)"
def fmt(v): return ("%.4f" % v).rstrip("0").rstrip(".")
def shift_pairs(text, keys):
    def f(m):
        x, y = m.group(2), float(m.group(3))
        return f"({m.group(1)} {x} {fmt(y + H) if y > CUT else m.group(3)}"
    return re.sub(r"\((" + keys + r") " + NUM + " " + NUM, f, text)

# split into top-level items
head_end = s.index("\n\t(")
items = re.split(r"(?=\n\t\()", s[head_end:])
out = [s[:head_end]]
stats = {}
for it in items:
    kind = re.match(r"\n\t\(([a-z_]+)", it)
    k = kind.group(1) if kind else ""
    stats[k] = stats.get(k, 0) + 1
    if k == "footprint":
        m = re.search(r"\n\t\t\(at " + NUM + " " + NUM, it)
        if m and float(m.group(2)) > CUT:
            it = it[:m.start()] + f"\n\t\t(at {m.group(1)} {fmt(float(m.group(2)) + H)}" + it[m.end():]
    elif k in ("segment", "via", "arc"):
        it = shift_pairs(it, "start|end|mid|at")
    elif k == "zone":
        it = re.sub(r"\n\t\t\(filled_polygon\n.*?\n\t\t\)", "", it, flags=re.S)
        it = shift_pairs(it, "xy")
    elif k.startswith("gr_") or k in ("dimension", "target"):
        it = shift_pairs(it, "start|end|mid|center|at|xy")
    out.append(it)
open(path, "w").write("".join(out))
print("items:", stats)
