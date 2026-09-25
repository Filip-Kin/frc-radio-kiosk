"""Fourth pass: drop the short pad-to-pad stubs (GND, +3V3, U4_*) that dangle
after their part moved. DRC lists them; the GND pour and the autorouter
cover what they did. Ethernet, PORT_N and the unnamed orphan stay."""
import json, re, sys
BOARD, DRC = sys.argv[1], sys.argv[2]
d = json.load(open(DRC))
pts = set()
for v in d["violations"]:
    if v["type"] == "track_dangling":
        for i in v["items"]:
            desc = i["description"]
            if "PORT_N" in desc or "ETH" in desc or "<no net>" in desc:
                continue
            pts.add((round(i["pos"]["x"], 2), round(i["pos"]["y"], 2)))
text = open(BOARD).read()
NUM = r"(-?\d+(?:\.\d+)?)"
gone = []
def edit(m):
    b = m.group(0)
    s = re.search(r"\(start " + NUM + " " + NUM + r"\)", b); e = re.search(r"\(end " + NUM + " " + NUM + r"\)", b)
    ps = (round(float(s.group(1)), 2), round(float(s.group(2)), 2)); pe = (round(float(e.group(1)), 2), round(float(e.group(2)), 2))
    if ps in pts or pe in pts:
        gone.append((ps, pe, re.search(r'\(net "([^"]*)"\)', b).group(1))); return ""
    return b
text = re.sub(r"\n\t\(segment\n.*?\n\t\)", edit, text, flags=re.S)
open(BOARD, "w").write(text)
print("dangling stubs removed:", len(gone), sorted({g[2] for g in gone}))
