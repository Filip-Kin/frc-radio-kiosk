"""v2c outline: 95 x 140. Right-edge parts out 11 mm, bottom parts up 1 mm,
Ethernet copper below y 100 up 1 mm (only vertical runs cross that line).
All other copper and the zone fills removed: v2c is placed and routed anew."""
import re
s=open('v2b-start.kicad_pcb').read(); N=r'(-?[\d.]+)'
MOVE={'J1':(11,0),'J2':(11,0),'D30':(11,0),'H2':(11,0),'H4':(11,-1),'J5':(0,-1),'D31':(0,-1),'H3':(0,-1)}
def fp(m):
  b=m.group(0); ref=re.search(r'\(property "Reference" "([^"]*)"',b).group(1)
  if ref not in MOVE: return b
  dx,dy=MOVE[ref]
  return re.sub(r'^(\t\t\(at )'+N+' '+N,lambda q:f'{q.group(1)}{float(q.group(2))+dx:g} {float(q.group(3))+dy:g}',b,count=1,flags=re.M)
s=re.sub(r'\n\t\(footprint "[^"]*"\n.*?\n\t\)',fp,s,flags=re.S)
kept=0;dropped=0
def cu(m):
  global kept,dropped
  x=m.group(0)
  if '(net "ETH_' not in x: dropped+=1; return ''
  kept+=1
  def sh(q):
    X,Y=float(q.group(2)),float(q.group(3))
    return f'{q.group(1)}{X:g} {Y-1 if Y>100 else Y:g}'
  return re.sub(r'(\((?:start|end|at) )'+N+' '+N,sh,x)
s=re.sub(r'\n\t\((?:segment|via|arc)\n.*?\n\t\)',cu,s,flags=re.S)
s=re.sub(r'\n\t\t\(filled_polygon\n.*?\n\t\t\)','',s,flags=re.S)
s=s.replace('(xy 0 0) (xy 84 0) (xy 84 141) (xy 0 141)','(xy 0 0) (xy 95 0) (xy 95 140) (xy 0 140)')
for a,b in [('(start 84 0)\n\t\t(end 84 141)','(start 95 0)\n\t\t(end 95 140)'),('(start 84 141)\n\t\t(end 0 141)','(start 95 140)\n\t\t(end 0 140)'),('(start 0 141)\n\t\t(end 0 0)','(start 0 140)\n\t\t(end 0 0)'),('(start 0 0)\n\t\t(end 84 0)','(start 0 0)\n\t\t(end 95 0)')]:
  assert a in s,a; s=s.replace(a,b)
s=re.sub(r'\n\t\(gr_text "[^"]*"\n\t\t\(at [-\d.]+ (3[0-9]{2}(?:\.\d+)?)[^\n]*\n.*?\n\t\)','',s,flags=re.S)
open('v2c-0.kicad_pcb','w').write(s)
print('eth copper kept',kept,'dropped',dropped, 'texts',len(re.findall(r'\n\t\(gr_text ',s)))
