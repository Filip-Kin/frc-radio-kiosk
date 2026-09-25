"""Board integrity check that DRC cannot do: every schematic part present once,
and every footprint's pads identical (number, type, size) to its library land
pattern. A loon placeholder or a half-written footprint fails here.
Usage (in the kicad:10.0 container): verify.py board.kicad_pcb [schematic]"""
import re, sys, os, glob, collections
STD = "/usr/share/kicad/footprints"; LCSC = "/lcsc.pretty"
PAD = re.compile(r'\(pad\s+"?([^"\s()]*)"?\s+(\w+)\s+(\w+).*?\(size\s+([-\d.]+)\s+([-\d.]+)\)', re.S)
def pads(text):
    out = []
    for m in PAD.finditer(text):
        w, h = sorted((round(float(m.group(4)), 2), round(float(m.group(5)), 2)))
        out.append((m.group(1), m.group(2), w, h))
    return sorted(out)
cache = {}
def lib(fpid):
    if fpid in cache: return cache[fpid]
    lib_, _, name = fpid.rpartition(":")
    cands = [f"{LCSC}/{name}.kicad_mod"] if lib_ == "LCSC" else [f"{STD}/{lib_}.pretty/{name}.kicad_mod"] if lib_ else glob.glob(f"{STD}/*.pretty/{name}.kicad_mod") + [f"{LCSC}/{name}.kicad_mod"]
    for c in cands:
        if os.path.exists(c): cache[fpid] = pads(open(c).read()); return cache[fpid]
    cache[fpid] = None; return None
pcb = open(sys.argv[1]).read()
gen = re.search(r'\(generator "([^"]*)"\)', pcb).group(1)
blocks = re.findall(r'\n\t\(footprint "([^"]*)"\n(.*?)\n\t\)', pcb, re.S)
refs = collections.Counter(); bad = []; nolib = []
for fpid, body in blocks:
    r = re.search(r'\(property "Reference" "([^"]*)"', body); ref = r.group(1) if r else "?"
    refs[ref] += 1
    want = lib(fpid)
    if want is None: nolib.append(f"{ref}({fpid})"); continue
    have = pads(body)
    if have != want: bad.append(f"{ref}({fpid.split(':')[-1][:24]}: {len(have)} pads vs {len(want)})")
missing = []
if len(sys.argv) > 2:
    sch = set(re.findall(r'\(property "Reference" "([A-Z]+\d+)"', open(sys.argv[2]).read()))
    missing = sorted(sch - set(refs), key=lambda s: (re.sub(r'\d', '', s), int(re.sub(r'\D', '', s))))
dups = [r for r, n in refs.items() if n > 1]
print(f"{os.path.basename(sys.argv[1]):28} gen={gen:6} fps={len(blocks):3} badpads={len(bad):3} nolib={len(nolib):2} missing={len(missing):3} dups={len(dups)}")
if "-v" in sys.argv:
    print("  BAD:", " ".join(bad)); print("  NOLIB:", " ".join(nolib)); print("  MISSING:", " ".join(missing)); print("  DUPS:", dups)
