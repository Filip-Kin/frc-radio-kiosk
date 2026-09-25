"""Third pass, plain text on board.kicad_pcb (KiCad 10 syntax): fix the
hand-routed spine where the netlist moved (buck 5 now on +12V, D22 to GND, the
VIN tap by C41), double the single vias on the 4.5 A paths, widen the USB-C
VBUS stubs, and drop GND stitching vias that ended up under moved parts.
Ethernet is not touched. The pcbnew SWIG bindings in KiCad 10 lose their type
table after the first track add/remove, which is why this is text.
"""
import json, re, uuid, sys

BOARD = sys.argv[1] if len(sys.argv) > 1 else "/work/board.kicad_pcb"
BOXES = sys.argv[2] if len(sys.argv) > 2 else "/work/moved-boxes.json"
text = open(BOARD).read()
boxes = json.load(open(BOXES))

def seg(x1, y1, x2, y2):
    return (round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2))

kill_segs = {
    seg(43.30, 37.00, 42.50, 37.80), seg(42.50, 37.80, 42.50, 38.90), seg(42.50, 38.90, 44.85, 36.78),  # VIN tap by C41
    seg(57.40, 123.50, 58.45, 122.45), seg(58.45, 122.45, 58.45, 122.03),  # VIN into buck 5 (now +12V)
    seg(8.80, 112.00, 10.20, 112.00), seg(10.20, 112.00, 11.00, 111.20), seg(11.00, 111.20, 11.00, 108.25), seg(8.00, 112.80, 8.80, 112.00),  # PORT_N to D22 (now GND)
}
kill_vias = {(42.50, 38.90), (57.40, 123.50), (13.70, 15.50), (13.70, 31.30)}
# LAPTOP_OUT's back-side run moves from x 13.7 (under U4's thermal vias) to x 17.6
kill_segs.add(seg(13.70, 31.30, 13.70, 15.50))
NUM = r"(-?\d+(?:\.\d+)?)"
removed, seen = [], set()

# #region edit existing copper
def edit_segment(m):
    block = m.group(0)
    s = re.search(r"\(start " + NUM + " " + NUM + r"\)", block)
    e = re.search(r"\(end " + NUM + " " + NUM + r"\)", block)
    x1, y1, x2, y2 = map(float, s.groups() + e.groups())
    net = re.search(r'\(net "([^"]*)"\)', block).group(1)
    k, kr = seg(x1, y1, x2, y2), seg(x2, y2, x1, y1)
    if k in kill_segs or kr in kill_segs:
        removed.append(("seg", k, net)); return ""
    # VIN row on the back ends at the C41 tap via, clear of C7's pad
    if net == "VIN" and seg(80.00, 37.00, 43.30, 37.00) in (k, kr):
        block = block.replace(s.group(0), "(start 80 37)").replace(e.group(0), "(end 46.6 37)")
    # the VIN spine now stops at the buck-12 tap; buck 5 below it is on +12V
    if net == "VIN" and seg(57.40, 37.00, 57.40, 123.50) in (k, kr):
        block = block.replace(s.group(0), "(start 57.4 37)").replace(e.group(0), "(end 57.4 101.53)")
    if net == "LAPTOP_OUT" and seg(13.70, 15.50, 34.00, 15.50) in (k, kr):
        block = block.replace(s.group(0), "(start 17.6 15.5)").replace(e.group(0), "(end 34 15.5)")
    if net == "LAPTOP_OUT" and seg(13.70, 31.30, 13.70, 34.22) in (k, kr):
        block = block.replace(s.group(0), "(start 13.7 32.6)").replace(e.group(0), "(end 13.7 34.22)")
    # USB-C VBUS pins: two 0.3 mm stubs cannot carry 5 A
    if net == "VIN_USB" and "(width 0.3)" in block:
        block = block.replace("(width 0.3)", "(width 0.5)")  # 0.6 clips the receptacle's GND pads
    return block

def edit_via(m):
    block = m.group(0)
    a = re.search(r"\(at " + NUM + " " + NUM + r"\)", block)
    x, y = map(float, a.groups())
    net = re.search(r'\(net "([^"]*)"\)', block).group(1)
    k = (round(x, 2), round(y, 2))
    if k in kill_vias or (k in seen and net == "+12V"):  # the +12V via at 59.9,112.5 was there twice
        removed.append(("via", k, net)); return ""
    seen.add(k)
    if net == "GND" and any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in boxes):
        removed.append(("gnd-via", k)); return ""
    return block

text = re.sub(r"\n\t\(segment\n.*?\n\t\)", edit_segment, text, flags=re.S)
text = re.sub(r"\n\t\(via\n.*?\n\t\)", edit_via, text, flags=re.S)

# #region new copper
new = []
def add_seg(net, layer, x1, y1, x2, y2, w):
    new.append(f'\n\t(segment\n\t\t(start {x1:g} {y1:g})\n\t\t(end {x2:g} {y2:g})\n\t\t(width {w:g})\n\t\t(layer "{layer}")\n\t\t(net "{net}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
def add_via(net, x, y, dia=1.0, drill=0.5):
    new.append(f'\n\t(via\n\t\t(at {x:g} {y:g})\n\t\t(size {dia:g})\n\t\t(drill {drill:g})\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "{net}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')

# VIN tap to C41: via just below the pad at the end of the back-side row
add_via("VIN", 46.60, 37.00); add_seg("VIN", "F.Cu", 46.60, 37.00, 44.85, 36.78, 1.2)
# +12V down to buck 5 (C50 pad 1), plus a second via for the boost feed
add_seg("+12V", "B.Cu", 59.90, 112.50, 59.90, 122.15, 2.0)
add_seg("+12V", "B.Cu", 59.90, 122.15, 58.45, 123.60, 2.0)
add_via("+12V", 58.45, 123.60); add_seg("+12V", "F.Cu", 58.45, 123.60, 58.45, 122.03, 1.2)
add_via("+12V", 59.90, 111.20); add_seg("+12V", "F.Cu", 59.90, 111.20, 59.90, 112.50, 1.2)
# LAPTOP_OUT 4.5 A: back-side run at x 17.6, two vias at each end
add_seg("LAPTOP_OUT", "B.Cu", 17.60, 15.50, 17.60, 32.60, 1.2)
add_via("LAPTOP_OUT", 17.60, 15.50); add_via("LAPTOP_OUT", 18.90, 15.50); add_seg("LAPTOP_OUT", "B.Cu", 17.60, 15.50, 18.90, 15.50, 1.2)
add_via("LAPTOP_OUT", 17.60, 32.60); add_seg("LAPTOP_OUT", "F.Cu", 17.60, 32.60, 13.70, 32.60, 1.2)
add_via("LAPTOP_OUT", 15.20, 32.60); add_seg("LAPTOP_OUT", "B.Cu", 17.60, 32.60, 15.20, 32.60, 1.2)
# VIN 5 A from either input FET: second via beside each
add_via("VIN", 80.80, 45.00); add_seg("VIN", "F.Cu", 80.80, 43.74, 80.80, 45.00, 1.5)
add_via("VIN", 80.80, 55.60); add_seg("VIN", "F.Cu", 80.80, 56.84, 80.80, 55.60, 1.5)

# GND stitching vias that sit on the new copper go too (the pour reconnects around them)
new_geo = []
for item in new:
    m = re.search(r"\(start " + NUM + " " + NUM + r"\)\n\t\t\(end " + NUM + " " + NUM + r"\)\n\t\t\(width " + NUM + r"\)", item)
    if m:
        new_geo.append(tuple(map(float, m.groups())))
    m = re.search(r"\(via\n\t\t\(at " + NUM + " " + NUM + r"\)", item)
    if m:
        x, y = map(float, m.groups()); new_geo.append((x, y, x, y, 1.0))
def near_new(x, y):
    for x1, y1, x2, y2, w in new_geo:
        dx, dy = x2 - x1, y2 - y1
        t = 0 if dx == dy == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        px, py = x1 + t * dx, y1 + t * dy
        if ((x - px) ** 2 + (y - py) ** 2) ** 0.5 < w / 2 + 0.5 + 0.25:
            return True
    return False
def drop_gnd_via(m):
    block = m.group(0)
    a = re.search(r"\(at " + NUM + " " + NUM + r"\)", block)
    x, y = map(float, a.groups())
    if '(net "GND")' in block and near_new(x, y):
        removed.append(("gnd-via", (x, y))); return ""
    return block
text = re.sub(r"\n\t\(via\n.*?\n\t\)", drop_gnd_via, text, flags=re.S)

# insert after the last existing segment or via block
last = max(text.rfind("\n\t(segment\n"), text.rfind("\n\t(via\n"))
end = text.index("\n\t)", last) + len("\n\t)")
text = text[:end] + "".join(new) + text[end:]
open(BOARD, "w").write(text)
print("removed copper:", [r for r in removed if r[0] != "gnd-via"])
print("GND stitching vias dropped under moved parts:", sum(1 for r in removed if r[0] == "gnd-via"))
print("added:", len(new), "items")
