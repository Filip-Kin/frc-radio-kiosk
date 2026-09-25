"""Routing copy only: grow the copper pads of footprints that carry their own
clearance (KiCad's HTSSOP has 0.2 mm) by the difference to the net-class
clearance, so Freerouting, which ignores footprint clearances, keeps off them.
Usage: enlarge.py in.kicad_pcb out.kicad_pcb"""
import re, sys
s = open(sys.argv[1]).read(); BASE = 0.15; n = 0
def fp(m):
    global n
    b = m.group(0); c = re.search(r"\n\t\t\(clearance ([\d.]+)\)", b)
    if not c or float(c.group(1)) <= BASE: return b
    g = 2 * (float(c.group(1)) - BASE)
    def pad(pm):
        global n
        pb = pm.group(0)
        if '"F.Cu"' not in pb and '"*.Cu"' not in pb and '"B.Cu"' not in pb: return pb
        n += 1
        return re.sub(r"\(size ([\d.]+) ([\d.]+)\)", lambda q: "(size %.4f %.4f)" % (float(q.group(1)) + g, float(q.group(2)) + g), pb, count=1)
    return re.sub(r'\n\t\t\(pad "[^"]*" \w+ \w+\n.*?\n\t\t\)', pad, b, flags=re.S)
s = re.sub(r'\n\t\(footprint "[^"]*"\n.*?\n\t\)', fp, s, flags=re.S)
open(sys.argv[2], "w").write(s); print("pads grown", n)
