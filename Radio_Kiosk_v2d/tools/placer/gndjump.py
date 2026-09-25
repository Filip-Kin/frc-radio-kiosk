"""Join each cut-off front GND region to the main one: a GND via inside the
region, a GND via inside the main region, a straight B.Cu segment between
them. Everything on B.Cu except the +12V pour is an obstacle."""
import json,re,math,uuid,sys
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
src,out=sys.argv[1],sys.argv[2]
s=open(src).read(); Z=json.load(open('zones.json')); G=json.load(open('padpoly.json'))
N=r'(-?[\d.]+)'
polys=[Polygon(p['outer'],p['holes']) for p in Z['GND/F']]
polys.sort(key=lambda p:-p.area); main,isl=polys[0],polys[1:]
VD,VDR,W,CL=0.6,0.3,0.4,0.2
obsB=[];obsAll=[]
for p in G['pads']:
  if p['layer']=='hole': obsAll.append(Point(p['x'],p['y']).buffer(p['r']+0.05)); continue
  if p['layer']=='B' and len(p['pts'])>=3: obsB.append(Polygon(p['pts']))
  if p['layer']=='F' and len(p['pts'])>=3 and p['net']=='GND': pass
for m in re.finditer(r'\n\t\((segment|via)\n.*?\n\t\)',s,re.S):
  x=m.group(0)
  if m.group(1)=='segment':
    if '(layer "B.Cu")' not in x: continue
    a=tuple(map(float,re.search(r'\(start '+N+' '+N,x).groups())); e=tuple(map(float,re.search(r'\(end '+N+' '+N,x).groups())); w=float(re.search(r'\(width '+N,x).group(1))
    obsB.append(LineString([a,e]).buffer(w/2) if a!=e else Point(a).buffer(w/2))
  else:
    at=tuple(map(float,re.search(r'\(at '+N+' '+N,x).groups())); d=float(re.search(r'\(size '+N,x).group(1))
    obsAll.append(Point(at).buffer(d/2+0.05))  # vias: copper both sides + hole spacing
import time;T=time.time();print("obs",len(obsB),len(obsAll),flush=True)
OB=unary_union(obsB+obsAll);print("union",time.time()-T,flush=True)
OBP=None
def obp():
  global OBP
  if OBP is None: OBP=prep(OB.buffer(CL-1e-3))
  return OBP
from shapely.prepared import prep
SH={}
def ok_via(p,region):
  k=id(region)
  if k not in SH: SH[k]=prep(region.buffer(0).buffer(-0.02))
  c=Point(p).buffer(VD/2)
  return SH[k].contains(c) and not obp().intersects(c)
new=[]
from shapely.prepared import prep
gv=[tuple(map(float,m.groups())) for m in re.finditer(r'\n\t\(via\n\t\t\(at '+N+' '+N+r'\).*?\(net "GND"\)',s,re.S)]
for R in isl:
  if any(R.contains(Point(v)) for v in gv): print('has via, skip',[round(c,1) for c in R.centroid.coords[0]]); continue
  global_=0
  best=None
  mnx,mny,mxx,mxy=R.bounds
  cand=[(mnx+i*0.25,mny+j*0.25) for i in range(int((mxx-mnx)/0.25)+1) for j in range(int((mxy-mny)/0.25)+1)]
  cand=[p for p in cand if ok_via(p,R)]
  print('cand',len(cand),flush=True)
  for p in cand:
    # nearest main-region spot along directions
    for k in range(32):
      ang=2*math.pi*k/32
      for dist in [x*0.25 for x in range(4,48)]:
        q=(round(p[0]+dist*math.cos(ang),3),round(p[1]+dist*math.sin(ang),3))
        if best and dist>=best[0]: break
        if not ok_via(q,main): continue
        seg=LineString([p,q]).buffer(W/2)
        if obp().intersects(seg): break
        best=(dist,p,q); break
  print('island %.1f mm2'%R.area, 'at', [round(v,1) for v in R.centroid.coords[0]], '->', best)
  if best:
    _,p,q=best
    for c in (p,q): new.append(f'\n\t(via\n\t\t(at {c[0]:.3f} {c[1]:.3f})\n\t\t(size {VD})\n\t\t(drill {VDR})\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "GND")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
    new.append(f'\n\t(segment\n\t\t(start {p[0]:.3f} {p[1]:.3f})\n\t\t(end {q[0]:.3f} {q[1]:.3f})\n\t\t(width {W})\n\t\t(layer "B.Cu")\n\t\t(net "GND")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
    OBP=None
    OB=OB.union(LineString([p,q]).buffer(W/2)).union(Point(p).buffer(VD/2)).union(Point(q).buffer(VD/2))
k=s.index('\n\t(zone'); s=s[:k]+''.join(new)+s[k:]; open(out,'w').write(s)
