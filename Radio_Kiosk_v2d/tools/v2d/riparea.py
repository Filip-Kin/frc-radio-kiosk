"""Remove tracks/vias of the given nets that come within R of (x,y). Usage: riparea.py in out NETS x y R"""
import re, sys, math
s = open(sys.argv[1]).read(); nets = set(sys.argv[3].split(',')); P = (float(sys.argv[4]), float(sys.argv[5])); Rr = float(sys.argv[6])
N = r"(-?[\d.]+)"; n = 0
def near(b):
    pts = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(r'\((?:start|end|at) ' + N + ' ' + N, b)]
    if len(pts) == 2:
        (ax, ay), (bx, by) = pts; dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
        t = 0 if L2 == 0 else max(0, min(1, ((P[0] - ax) * dx + (P[1] - ay) * dy) / L2))
        return math.hypot(P[0] - ax - t * dx, P[1] - ay - t * dy) < Rr
    return any(math.dist(p, P) < Rr for p in pts)
def f(m):
    global n
    b = m.group(0); net = re.search(r'\(net "([^"]*)"\)', b)
    if net and net.group(1) in nets and near(b): n += 1; return ''
    return b
s = re.sub(r'\n\t\((?:segment|via)\n.*?\n\t\)', f, s, flags=re.S)
open(sys.argv[2], 'w').write(s); print('removed', n)
