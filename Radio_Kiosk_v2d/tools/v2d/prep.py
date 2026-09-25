"""Routing input: lock existing copper, keep only the In1 GND plane (In2 and
outer pours are added after routing so Freerouting sees In2 as free)."""
import re,sys
s=open(sys.argv[1]).read()
def z(m):
  b=m.group(0)
  return b if '(layer "In1.Cu")' in b else ''
s=re.sub(r'\n\t\(zone\n.*?\n\t\)',z,s,flags=re.S)
s=s.replace('\n\t\t(locked yes)','')
s=re.sub(r'(\n\t\((?:segment|via)\n)',r'\1\t\t(locked yes)\n',s)
open(sys.argv[2],'w').write(s)
