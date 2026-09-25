"""Remove dangling tracks/vias, and one of two same-net vias that sit on top of each other.
Usage: final_clean.py board drc.json out"""
import json, re, sys, math
s = open(sys.argv[1]).read(); d = json.load(open(sys.argv[2])); N = r"(-?[\d.]+)"
kill_t, kill_v = [], []
for v in d['violations']:
    it = v['items']
    if v['type'] == 'track_dangling': kill_t.append((re.search(r'\[([^\]]*)\]', it[0]['description']).group(1), it[0]['pos']['x'], it[0]['pos']['y']))
    if v['type'] == 'via_dangling': kill_v.append((re.search(r'\[([^\]]*)\]', it[0]['description']).group(1), it[0]['pos']['x'], it[0]['pos']['y']))
    if v['type'] == 'hole_to_hole' and all(i['description'].startswith('Via') for i in it):
        n1 = re.search(r'\[([^\]]*)\]', it[0]['description']).group(1); n2 = re.search(r'\[([^\]]*)\]', it[1]['description']).group(1)
        if n1 == n2: kill_v.append((n2, it[1]['pos']['x'], it[1]['pos']['y']))
n = 0
def f(m):
    global n
    b = m.group(0); net = re.search(r'\(net "([^"]*)"\)', b); net = net.group(1) if net else ''
    if m.group(1) == 'via':
        a = re.search(r'\(at ' + N + ' ' + N, b); p = (float(a.group(1)), float(a.group(2)))
        if any(k[0] == net and math.dist(p, k[1:]) < 0.01 for k in kill_v): n += 1; return ''
    else:
        a = re.search(r'\(start ' + N + ' ' + N, b); e = re.search(r'\(end ' + N + ' ' + N, b)
        pa, pe = (float(a.group(1)), float(a.group(2))), (float(e.group(1)), float(e.group(2)))
        mid = ((pa[0] + pe[0]) / 2, (pa[1] + pe[1]) / 2)
        if any(k[0] == net and min(math.dist(q, k[1:]) for q in (pa, pe, mid)) < 0.01 for k in kill_t): n += 1; return ''
    return b
s = re.sub(r'\n\t\((segment|via)\n.*?\n\t\)', f, s, flags=re.S)
open(sys.argv[3], 'w').write(s); print('removed', n)
