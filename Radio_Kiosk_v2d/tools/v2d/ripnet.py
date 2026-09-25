"""Remove every track and via of the given nets. Usage: ripnet.py in out NET[,NET]"""
import re, sys
s = open(sys.argv[1]).read(); nets = set(sys.argv[3].split(',')); n = 0
def f(m):
    global n
    net = re.search(r'\(net "([^"]*)"\)', m.group(0))
    if net and net.group(1) in nets: n += 1; return ''
    return m.group(0)
s = re.sub(r'\n\t\((?:segment|via)\n.*?\n\t\)', f, s, flags=re.S)
open(sys.argv[2], 'w').write(s); print('removed', n)
