"""Second pass after kiosk-update-pcb.py: place the new and swapped parts,
re-lay the laptop rail block (LM3150 + two DPAKs + a bigger inductor), and
write the keep-out boxes of everything moved for kiosk-copper.py.
Runs in the kicad:10.0 container, /work = project.
"""
import collections
import pcbnew

MM = 1_000_000
BOARD = "/work/board.kicad_pcb"
board = pcbnew.LoadBoard(BOARD)
# keep the footprint list alive: proxies from a discarded GetFootprints() go stale
fps = board.GetFootprints()
fp_of = {fp.GetReference(): fp for fp in fps}
P = lambda x, y: pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM)))
nets = board.GetNetInfo()
net = lambda name: nets.GetNetItem(name)

# #region placement
# ref: (x, y, rot). Laptop block rows are described in the notes at the end.
place = {
    # laptop rail, row A (y 21): VIN cap by pin 2, controller with SW/HG/LG facing the FETs, high side, low side, RON, RLIM
    "C40": (7.15, 21.0, 90), "U4": (13.63, 21.0, -90), "Q40": (24.06, 21.0, 0), "Q41": (36.35, 21.0, 0),
    "R44": (44.07, 21.0, 90), "R45": (47.22, 21.0, 90),
    # under the controller: shunt (Kelvin pads up/down), VCC and BST caps, sense amp with its cap
    "R96": (7.5, 29.0, 90), "C42": (11.7, 26.2, 90), "C43": (11.7, 29.8, 90), "U42": (16.3, 26.5, 0), "C116": (16.3, 30.0, 0),
    # inductor, output caps, second VIN cap (row B1)
    "L4": (25.1, 30.75, 0), "C45": (33.95, 27.5, 90), "C46": (38.35, 27.5, 90), "C47": (42.75, 27.5, 90), "C44": (46.5, 27.5, 90),
    # row B2: integrator, its cap, its feedback cap; row below: FB injection diode + resistor, U7's cap
    "U43": (34.4, 33.4, 0), "C120": (37.7, 33.4, 90), "C117": (40.8, 33.4, 90),
    "D40": (33.7, 36.9, 0), "R98": (38.0, 36.9, 0), "C7": (42.0, 36.9, 0),
    # the band between the ideal diode and Q8, between the battery pins: LM74700 caps, FB divider
    "C5": (9.6, 40.0, 0), "C8": (18.4, 40.0, 0), "R40": (22.5, 40.0, 0), "R41": (27.05, 40.0, 0), "C49": (31.4, 40.0, 0),
    # above Q13: its 5 V gate driver and cap
    "U31": (57.3, 38.3, 0), "C16": (60.5, 38.3, 90),
    # pack ideal diode row (y 57.66)
    "C13": (21.5, 57.66, 90), "C14": (24.5, 57.66, 90), "U12": (28.6, 57.66, 0), "C12": (32.7, 57.66, 90), "Q12": (38.0, 57.66, 0),
    # VIN bulk cap under the buck-12 input caps; port switch beside it with its gate parts
    "C4": (40.0, 71.8, 0), "Q23": (50.6, 70.3, 0), "D23": (57.0, 70.5, 90), "R27": (59.8, 70.5, 90),
    "R28": (48.2, 75.4, 0), "R29": (52.0, 75.4, 0),
    # strip under the bulk caps: laptop EN divider, integrator input filters
    "R46": (7.0, 75.2, 0), "R92": (15.9, 75.2, 0), "R47": (19.6, 75.2, 0), "C119": (26.5, 75.2, 0), "R97": (31.0, 75.2, 0),
    # strip below the PD block: USB input disable pull-ups
    "R5": (63.9, 78.0, 0), "R6": (68.1, 78.0, 0),
    # above the PSE resistor row: port-switch driver FET, Q13 gate pulldown, USB disable FET; PWM filter, SS cap
    "Q24": (50.7, 85.6, 0), "Q25": (55.0, 85.6, 0), "R99": (59.2, 85.6, 0),
    "C118": (50.7, 88.8, 0), "C48": (55.0, 88.8, 0), "R66": (45.0, 88.5, 0),
    # third boost output cap; shutdown parts shift right to make room
    "C26": (75.7, 88.03, 90), "R25": (78.6, 88.03, 90), "D21": (81.6, 88.03, 90),
    # the 15 uH inductor is wider than the 10 uH: left, off U3's pads
    "L3": (36.2, 100.05, 0),
    # lid LED series resistor, port sense divider by the port TVS, DC input cap
    "R113": (31.0, 88.2, 0), "R64": (17.4, 108.25, 90), "R65": (20.0, 108.25, 90), "C15": (22.6, 108.25, 90),
    "C3": (76.2, 50.76, 90),
}
for ref, (x, y, rot) in place.items():
    fp = fp_of[ref]
    fp.SetPosition(P(x, y))
    fp.SetOrientationDegrees(rot)

# #region geometry (before any copper edit: SWIG proxies go stale after board.Remove)
def rect(fp, margin=0.0):
    bb = board.FindFootprintByReference(fp.GetReference()).GetBoundingBox(False, False)
    m = int(margin * MM)
    return (bb.GetLeft() - m, bb.GetTop() - m, bb.GetRight() + m, bb.GetBottom() + m)
def inside(r, p):
    return r[0] <= p.x <= r[2] and r[1] <= p.y <= r[3]
boxes = [rect(fp_of[r], 0.3) for r in place]

# #region overlap check
front = [(fp.GetReference(), rect(fp)) for fp in fps if not fp.IsFlipped()]
overlaps = []
for i, (ra, a) in enumerate(front):
    for rb, b in front[i + 1:]:
        w = min(a[2], b[2]) - max(a[0], b[0]); h = min(a[3], b[3]) - max(a[1], b[1])
        if w > 0 and h > 0:
            overlaps.append((ra, rb, round(w / MM, 2), round(h / MM, 2)))
edge = board.GetBoardEdgesBoundingBox()
outside = [r for r, b in front if b[0] < edge.GetLeft() or b[2] > edge.GetRight() or b[1] < edge.GetTop() or b[3] > edge.GetBottom()]

u4 = fp_of["U4"]
print("U4 pads:", [(p.GetNumber(), round(p.GetPosition().x / MM, 2), round(p.GetPosition().y / MM, 2)) for p in u4.Pads() if p.GetNumber() in ("1", "7", "8", "14")])

# copper edits happen in kiosk-copper.py as text edits: the SWIG bindings in
# KiCad 10 lose their type table after the first track is added or removed
import json
json.dump([[v / MM for v in b] for b in boxes], open("/work/moved-boxes.json", "w"))
board.Save(BOARD)
print(f"footprint overlaps ({len(overlaps)}):", overlaps)
print("outside the edge:", outside)
