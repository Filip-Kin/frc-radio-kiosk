"""v2d base board from the v2c board: 85 wide, H tall, 4 layers.
- right-edge parts (J1, J2, D30, H2, H4) keep their distance from the right edge
- bottom-edge parts (J5, D31, H3, H4) keep their distance from the bottom edge
- the Ethernet pairs keep their route: the band below CUT moves up rigidly and
  the long vertical runs down the left edge get shorter
- In1.Cu = GND plane, In2.Cu = signals with a GND fill; old zones dropped
- board name and credit moved to one block on the left edge at y 48
Usage: make_base.py src.kicad_pcb H out.kicad_pcb"""
import re, sys, uuid
src, H, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
W0, H0, W = 95.0, 140.0, 85.0
DX, DY, CUT = W - W0, H - H0, 95.0
RIGHT = {'J1', 'J2', 'D30', 'H2', 'H4'}
BOTTOM = {'J5', 'D31', 'H3', 'H4'}
N = r"(-?\d+(?:\.\d+)?)"
def fmt(v): return ("%.4f" % v).rstrip("0").rstrip(".")
s = open(src).read()

# #region layers
s = s.replace('\t\t(0 "F.Cu" signal)\n\t\t(2 "B.Cu" signal)\n',
              '\t\t(0 "F.Cu" signal)\n\t\t(4 "In1.Cu" power)\n\t\t(6 "In2.Cu" signal)\n\t\t(2 "B.Cu" signal)\n', 1)
assert '"In1.Cu" power' in s
# #endregion

head_end = s.index("\n\t(")
items = re.split(r"(?=\n\t\()", s[head_end:])
outl = [s[:head_end]]
for it in items:
    k = re.match(r"\n\t\(([a-z_]+)", it)
    k = k.group(1) if k else ""
    if k == "footprint":
        ref = re.search(r'\(property "Reference" "([^"]*)"', it).group(1)
        m = re.search(r"\n\t\t\(at " + N + " " + N, it)
        x, y = float(m.group(1)), float(m.group(2))
        if ref in RIGHT: x += DX
        if ref in BOTTOM: y += DY
        it = it[:m.start()] + f"\n\t\t(at {fmt(x)} {fmt(y)}" + it[m.end():]
    elif k in ("segment", "via", "arc"):
        it = re.sub(r"\((start|end|mid|at) " + N + " " + N,
                    lambda m: f"({m.group(1)} {m.group(2)} {fmt(float(m.group(3)) + DY) if float(m.group(3)) > CUT else m.group(3)}", it)
    elif k == "zone":
        continue
    elif k == "gr_line":
        continue  # outline rebuilt below
    elif k == "gr_text":
        name = re.match(r'\n\t\(gr_text "([^"]*)"', it).group(1)
        at = {"FRC Radio Kiosk Thinggy v2": "(at 2.6 48 270)",
              "Made By Filip Kin <3": "(at 4.8 48 270)",
              "filipkin.com": "(at 4.8 67 270)"}[name]
        it = re.sub(r"\(at [^)]*\)", at, it, count=1)
    outl.append(it)
s = "".join(outl)

def U(): return str(uuid.uuid4())
edge = "".join(f"""
\t(gr_line
\t\t(start {a[0]} {a[1]})
\t\t(end {b[0]} {b[1]})
\t\t(stroke
\t\t\t(width 0.1)
\t\t\t(type default)
\t\t)
\t\t(layer "Edge.Cuts")
\t\t(uuid "{U()}")
\t)""" for a, b in [((0, 0), (fmt(W), 0)), ((fmt(W), 0), (fmt(W), fmt(H))), ((fmt(W), fmt(H)), (0, fmt(H))), ((0, fmt(H)), (0, 0))])

def zone(layer, prio=0):
    return f"""
\t(zone
\t\t(net "GND")
\t\t(layer "{layer}")
\t\t(uuid "{U()}")
\t\t(priority {prio})
\t\t(hatch edge 0.5)
\t\t(connect_pads yes
\t\t\t(clearance 0.2)
\t\t)
\t\t(min_thickness 0.2)
\t\t(fill yes
\t\t\t(thermal_gap 0.5)
\t\t\t(thermal_bridge_width 0.5)
\t\t\t(island_removal_mode 0)
\t\t)
\t\t(polygon
\t\t\t(pts
\t\t\t\t(xy 0 0) (xy {fmt(W)} 0) (xy {fmt(W)} {fmt(H)}) (xy 0 {fmt(H)})
\t\t\t)
\t\t)
\t)"""
tail = s.rindex("\n)")
s = s[:tail] + edge + zone("In1.Cu") + zone("In2.Cu") + s[tail:]
open(out, "w").write(s)
print("board %gx%g, 4 layers ->" % (W, H), out)
