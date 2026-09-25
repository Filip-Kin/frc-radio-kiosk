"""Power classes stay on the outer 1 oz layers (inner copper is 0.5 oz)."""
import re,sys
t=open(sys.argv[1]).read(); n=0
def f(m):
  global n; n+=1
  return m.group(1)+'\n        (use_layer F.Cu B.Cu)'
t=re.sub(r'(\(class (?:Heavy|Wide|Power) [^(]*\(circuit\n\s*\(use_via "[^"]*"\))',f,t)
open(sys.argv[1],'w').write(t); print('power classes pinned to outer layers:',n)
