"""Tie a front pad to the back plane of its net: a front trace from the pad
to a via that sits inside the back plane's fill, clear of other-net copper."""
import json,re,math,uuid,sys
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
from shapely.prepared import prep
src,out=sys.argv[1],sys.argv[2]; targets=[t.split('.') for t in sys.argv[3].split(',')]; W=float(sys.argv[4]); NV=int(sys.argv[5]) if len(sys.argv)>5 else 1; VD,VDR=0.8,0.4; CL=0.2
s=open(src).read(); Z=json.load(open('zones.json')); G=json.load(open('padpoly.json')); N=r'(-?[\d.]+)'
new=[]
for ref,pn in targets:
  pad=[p for p in G['pads'] if p['ref']==ref and p['pad']==pn and p['layer']=='F'][0]; net=pad['net']
  plane=prep(unary_union([Polygon(p['outer'],p['holes']).buffer(0) for p in Z[net+'/B']]).buffer(-0.05))
  obs=[]
  for p in G['pads']:
    if p['layer']=='hole': obs.append(Point(p['x'],p['y']).buffer(p['r']+0.05)); continue
    if p['net']!=net and len(p['pts'])>=3: obs.append(Polygon(p['pts']))   # either side: the via goes through both
  for m in re.finditer(r'\n\t\((segment|via)\n.*?\n\t\)',s,re.S):
    x=m.group(0)
    if f'(net "{net}")' in x: continue
    if m.group(1)=='segment':
      a=tuple(map(float,re.search(r'\(start '+N+' '+N,x).groups())); e=tuple(map(float,re.search(r'\(end '+N+' '+N,x).groups())); w=float(re.search(r'\(width '+N,x).group(1))
      L=re.search(r'\(layer "(.)',x).group(1)
      obs.append((LineString([a,e]) if a!=e else Point(a)).buffer(w/2).union(Point(0,-999)) if True else None)
      obs[-1]=(obs[-1],L)
    else:
      at=tuple(map(float,re.search(r'\(at '+N+' '+N,x).groups())); d=float(re.search(r'\(size '+N,x).group(1)); obs.append(Point(at).buffer(d/2+0.05))
  both=prep(unary_union([o for o in obs if not isinstance(o,tuple)]+[o[0] for o in obs if isinstance(o,tuple)]).buffer(CL))
  front=prep(unary_union([o for o in obs if not isinstance(o,tuple)]+[o[0] for o in obs if isinstance(o,tuple) and o[1]=='F']).buffer(CL))
  own=prep(unary_union([Polygon(p['pts']) for p in G['pads'] if p['layer']=='F' and p['net']==net and len(p['pts'])>=3]).buffer(0.15))
  xs=[q[0] for q in pad['pts']]; ys=[q[1] for q in pad['pts']]; c=((min(xs)+max(xs))/2,(min(ys)+max(ys))/2)
  placed=[]
  for _n in range(NV):
   best=None
   for k in range(48):
    ang=2*math.pi*k/48
    for i in range(2,40):
      d=i*0.2; q=(round(c[0]+d*math.cos(ang),3),round(c[1]+d*math.sin(ang),3))
      if best and d>=best[0]: break
      v=Point(q).buffer(VD/2)
      if any(math.dist(q,p0)<VD+0.35 for p0 in placed): continue
      if not plane.contains(v) or both.intersects(v) or own.intersects(v): continue
      if front.intersects(LineString([c,q]).buffer(W/2)): break
      best=(d,q); break
   print(ref,pn,net,'pad',c,'->',best)
   if best:
    q=best[1]; placed.append(q)
    new.append(f'\n\t(via\n\t\t(at {q[0]} {q[1]})\n\t\t(size {VD})\n\t\t(drill {VDR})\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "{net}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
    new.append(f'\n\t(segment\n\t\t(start {c[0]} {c[1]})\n\t\t(end {q[0]} {q[1]})\n\t\t(width {W})\n\t\t(layer "F.Cu")\n\t\t(net "{net}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
k=s.index('\n\t(zone'); s=s[:k]+''.join(new)+s[k:]; open(out,'w').write(s)
