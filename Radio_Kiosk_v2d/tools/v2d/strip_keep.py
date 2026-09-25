"""Keep only the listed net classes in the DSN network (GND always goes: the
plane and the pad vias carry it). Usage: strip_keep.py file.dsn Heavy,Wide,Power"""
import re, sys, json, fnmatch
t = open(sys.argv[1]).read(); keep = set(sys.argv[2].split(','))
PRO = json.load(open('/home/filip/tmp/v2d/board.kicad_pro'))['net_settings']
def ncls(n):
    for p in PRO['netclass_patterns']:
        if fnmatch.fnmatchcase(n, p['pattern']): return p['netclass']
    return 'Default'
k = 0
def f(m):
    global k
    n = m.group(1).strip('"')
    if n == 'GND' or ncls(n) not in keep: k += 1; return ''
    return m.group(0)
t = re.sub(r'\(net\s+("[^"]*"|[^\s()]+)\s*\(pins[^()]*(?:\([^()]*\)[^()]*)*\)\s*\)', f, t)
open(sys.argv[1], 'w').write(t); print('nets dropped from routing', k)
