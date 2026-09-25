"""Tidy grid-router copper: drop exact duplicate segments, then straighten
chains of short same-net segments (Douglas-Peucker, tol mm) whose inner joints
touch nothing else. Usage: tidy.py in out tol"""
import re, sys, math, collections, uuid
s = open(sys.argv[1]).read(); TOL = float(sys.argv[3]); N = r"(-?[\d.]+)"
segs = []
for m in re.finditer(r'\n\t\(segment\n(.*?)\n\t\)', s, re.S):
    b = m.group(1)
    a = re.search(r'\(start ' + N + ' ' + N, b); e = re.search(r'\(end ' + N + ' ' + N, b)
    segs.append(dict(txt=m.group(0), a=(round(float(a.group(1)), 4), round(float(a.group(2)), 4)), b=(round(float(e.group(1)), 4), round(float(e.group(2)), 4)),
                     w=re.search(r'\(width ([\d.]+)\)', b).group(1), l=re.search(r'\(layer "([^"]*)"', b).group(1), n=re.search(r'\(net "([^"]*)"\)', b).group(1)))
seen = set(); keep = []; dup = 0
for g in segs:
    k = (g['n'], g['l'], g['w'], min(g['a'], g['b']), max(g['a'], g['b']))
    if k in seen: dup += 1; s = s.replace(g['txt'], '', 1); continue
    seen.add(k); keep.append(g)
# joints: points where exactly two same-net/layer/width segments meet and nothing else (no via, no third seg)
vias = set()
for m in re.finditer(r'\n\t\(via\n.*?\(at ' + N + ' ' + N, s, re.S): vias.add((round(float(m.group(1)), 4), round(float(m.group(2)), 4)))
deg = collections.Counter(); byp = collections.defaultdict(list)
for i, g in enumerate(keep):
    for p in (g['a'], g['b']): deg[(g['n'], g['l'], p)] += 1; byp[(g['n'], g['l'], p)].append(i)
def dp(pts):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1e-9
    dists = [abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / L for p in pts[1:-1]]
    k = max(range(len(dists)), key=lambda i: dists[i])
    if dists[k] <= TOL: return [a, b]
    return dp(pts[:k + 2])[:-1] + dp(pts[k + 1:])
used = set(); newtxt = []; merged = 0
for i, g in enumerate(keep):
    if i in used: continue
    # walk a chain through clean joints
    def inner(p, gg): return deg[(gg['n'], gg['l'], p)] == 2 and p not in vias and all(keep[j]['w'] == gg['w'] for j in byp[(gg['n'], gg['l'], p)])
    chain = [i]; used.add(i); pts = [g['a'], g['b']]
    for end in (1, 0):
        while True:
            p = pts[-1] if end else pts[0]
            if not inner(p, g): break
            nxt = [j for j in byp[(g['n'], g['l'], p)] if j not in used]
            if not nxt: break
            j = nxt[0]; used.add(j); chain.append(j); q = keep[j]['b'] if keep[j]['a'] == p else keep[j]['a']
            pts = pts + [q] if end else [q] + pts
    if len(chain) < 3: continue
    simp = dp(pts)
    if len(simp) >= len(pts): continue
    for j in chain: s = s.replace(keep[j]['txt'], '', 1)
    for a, b in zip(simp, simp[1:]):
        newtxt.append(f'\n\t(segment\n\t\t(start {a[0]:.4f} {a[1]:.4f})\n\t\t(end {b[0]:.4f} {b[1]:.4f})\n\t\t(width {g["w"]})\n\t\t(layer "{g["l"]}")\n\t\t(net "{g["n"]}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
    merged += len(chain) - (len(simp) - 1)
last = max(s.rfind("\n\t(segment\n"), s.rfind("\n\t(via\n")); end = s.index("\n\t)", last) + 3
s = s[:end] + "".join(newtxt) + s[end:]
open(sys.argv[2], 'w').write(s); print('duplicates', dup, 'segments saved by straightening', merged)
