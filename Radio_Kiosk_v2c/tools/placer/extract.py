import re,json,sys
s=open(sys.argv[1]).read(); N=r'(-?[\d.]+)'
parts=[]
for m in re.finditer(r'\n\t\(footprint "([^"]*)"\n(.*?)\n\t\)',s,re.S):
  lib,b=m.group(1),m.group(2)
  ref=re.search(r'\(property "Reference" "([^"]*)"',b).group(1)
  at=re.search(r'^\t\t\(at '+N+' '+N+r'(?: '+N+r')?\)',b,re.M)
  x,y,rot=float(at.group(1)),float(at.group(2)),float(at.group(3) or 0)
  back=bool(re.search(r'^\t\t\(layer "B\.',b,re.M))
  pads=[]
  for p in re.finditer(r'\n\t\t\(pad "([^"]*)" (\w+) (\w+)\n(.*?)\n\t\t\)',b,re.S):
    pb=p.group(4)
    pa=re.search(r'\(at '+N+' '+N+r'(?: '+N+r')?\)',pb); sz=re.search(r'\(size '+N+' '+N,pb)
    net=re.search(r'\(net "([^"]*)"\)',pb)
    dr=re.search(r'\(drill (?:oval )?'+N,pb)
    pads.append(dict(num=p.group(1),type=p.group(2),lx=float(pa.group(1)),ly=float(pa.group(2)),w=float(sz.group(1)),h=float(sz.group(2)),net=net.group(1) if net else '',drill=float(dr.group(1)) if dr else 0,pang=float(pa.group(3) or 0)))
  pts=[]
  for g in re.finditer(r'\n\t\t\((fp_line|fp_rect|fp_poly|fp_circle|fp_arc)\n(.*?)\n\t\t\)',b,re.S):
    gb=g.group(2)
    if 'CrtYd' not in gb: continue
    for q in re.finditer(r'\((?:start|end|xy|center|mid) '+N+' '+N+r'\)',gb): pts.append((float(q.group(1)),float(q.group(2))))
    if g.group(1)=='fp_circle':
      c=re.search(r'\(center '+N+' '+N,gb); e=re.search(r'\(end '+N+' '+N,gb)
      r=((float(c.group(1))-float(e.group(1)))**2+(float(c.group(2))-float(e.group(2)))**2)**.5
      pts+= [(float(c.group(1))-r,float(c.group(2))-r),(float(c.group(1))+r,float(c.group(2))+r)]
  if pts: crt=[min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)]
  else: crt=None
  pb_=[min(p['lx']-p['w']/2 for p in pads),min(p['ly']-p['h']/2 for p in pads),max(p['lx']+p['w']/2 for p in pads),max(p['ly']+p['h']/2 for p in pads)] if pads else [0,0,0,0]
  if crt: crt=[min(crt[0],pb_[0]),min(crt[1],pb_[1]),max(crt[2],pb_[2]),max(crt[3],pb_[3])]
  else: crt=[pb_[0]-0.25,pb_[1]-0.25,pb_[2]+0.25,pb_[3]+0.25]
  parts.append(dict(ref=ref,lib=lib,x=x,y=y,rot=rot,back=back,pads=pads,crt=crt))
json.dump(parts,open('parts.json','w'),indent=0)
import collections
print(len(parts),'back',[p['ref'] for p in parts if p['back']])
area=sum((p['crt'][2]-p['crt'][0])*(p['crt'][3]-p['crt'][1]) for p in parts if not p['back'])
print('front courtyard area %.0f mm2 of %d'%(area,84*141))
print('nocrt',[p['ref'] for p in parts if not p['pads']])
