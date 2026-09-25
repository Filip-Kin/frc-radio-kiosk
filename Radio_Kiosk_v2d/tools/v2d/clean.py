"""Drop copper the DRC flagged: tracks/vias in clearance or short violations,
dangling vias and tracks. Matched by net and position (track start / via at).
Usage: clean.py board.kicad_pcb drc.json out.kicad_pcb"""
import json, re, sys
s = open(sys.argv[1]).read(); d = json.load(open(sys.argv[2]))
N = r"(-?[\d.]+)"
hits = []   # (kind, net, x, y)
for v in d["violations"]:
    if v["type"] not in ("clearance", "shorting_items", "via_dangling", "track_dangling", "tracks_crossing", "hole_clearance"): continue
    for it in v["items"]:
        m = re.match(r"(Track|Via) \[([^\]]*)\]", it["description"])
        if m: hits.append((m.group(1), m.group(2), it["pos"]["x"], it["pos"]["y"]))
gone = 0
def f(m):
    global gone
    b = m.group(0); kind = m.group(1)
    net = re.search(r'\(net "([^"]*)"\)', b); net = net.group(1) if net else ""
    if kind == "segment":
        a = re.search(r"\(start " + N + " " + N, b); e = re.search(r"\(end " + N + " " + N, b)
        pts = [(float(a.group(1)), float(a.group(2))), (float(e.group(1)), float(e.group(2)))]
        pts.append(((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2))
        for k, n, x, y in hits:
            if k == "Track" and n == net and any(abs(px - x) < 0.02 and abs(py - y) < 0.02 for px, py in pts):
                gone += 1; return ""
    else:
        a = re.search(r"\(at " + N + " " + N, b); p = (float(a.group(1)), float(a.group(2)))
        for k, n, x, y in hits:
            if k == "Via" and n == net and abs(p[0] - x) < 0.02 and abs(p[1] - y) < 0.02:
                gone += 1; return ""
    return b
s = re.sub(r"\n\t\((segment|via)\n.*?\n\t\)", f, s, flags=re.S)
open(sys.argv[3], "w").write(s); print("flagged", len(hits), "removed", gone)
