"""Remove tracks/vias of nets not allowed inside keep-out boxes. Usage: ripbox.py in out keepout.json"""
import re, sys, json, math
s = open(sys.argv[1]).read(); K = json.load(open(sys.argv[3])); N = r"(-?[\d.]+)"; n = 0
def inside(p, b, m): return b[0] - m < p[0] < b[2] + m and b[1] - m < p[1] < b[3] + m
def f(m):
    global n
    b = m.group(0); net = re.search(r'\(net "([^"]*)"\)', b); net = net.group(1) if net else ''
    pts = [(float(q.group(1)), float(q.group(2))) for q in re.finditer(r'\((?:start|end|at) ' + N + ' ' + N, b)]
    w = float(re.search(r'\((?:width|size) ([\d.]+)', b).group(1))
    if len(pts) == 2:
        k = max(2, int(math.dist(*pts) / 0.1)); pts = [(pts[0][0] + (pts[1][0] - pts[0][0]) * i / k, pts[0][1] + (pts[1][1] - pts[0][1]) * i / k) for i in range(k + 1)]
    for z in K:
        if net in z['own']: continue
        if any(inside(p, z['box'], w / 2) for p in pts): n += 1; return ''
    return b
s = re.sub(r'\n\t\((?:segment|via)\n.*?\n\t\)', f, s, flags=re.S)
open(sys.argv[2], 'w').write(s); print('removed', n)
