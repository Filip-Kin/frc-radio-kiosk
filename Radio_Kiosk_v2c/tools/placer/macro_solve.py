"""Lay out one power stage alone: members only, internal nets (GND and rails
included, they form the hot loop), switch node and gate drive weighted hard,
hard no-overlap at the end. Output: member offsets from the first anchor."""
import json,math,random,sys
import numpy as np
parts={p['ref']:p for p in json.load(open('parts.json'))}
MACS=json.load(open('macros.json')); name=sys.argv[1]; random.seed(int(sys.argv[2]) if len(sys.argv)>2 else 1)
mem=MACS[name]
G=0.25; S=70.0; NX=NY=int(S/G)
def rot(lx,ly,a):
  t=math.radians(a); return lx*math.cos(t)+ly*math.sin(t), -lx*math.sin(t)+ly*math.cos(t)
def rbox(b,a):
  pts=[rot(x,y,a) for x in (b[0],b[2]) for y in (b[1],b[3])]
  return min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)
def margin(p):
  l=p['lib']
  if any(k in l for k in ('SOIC','TSSOP','ESSOP','HTSSOP','SOT-23-6','SOT-23-5','LFPAK','SOT-223')): return 0.8
  if any(k in l for k in ('TO-252','IND-SMD','L_12x12','SRP7028','CP_Elec','2512')): return 0.6
  return 0.4
occ=np.zeros((NY,NX),np.int16)
st={r:[S/2+random.uniform(-8,8),S/2+random.uniform(-8,8),random.choice((0,90,180,270))] for r in mem}
def cells(r,x,y,a):
  p=parts[r]; b=rbox(p['crt'],a); m=margin(p)
  return int(math.floor((x+b[0]-m)/G)),int(math.floor((y+b[1]-m)/G)),int(math.ceil((x+b[2]+m)/G)),int(math.ceil((y+b[3]+m)/G))
def ovl(c):
  i0,j0,i1,j1=c
  if i0<0 or j0<0 or i1>NX or j1>NY: return 10**6
  return int(occ[j0:j1,i0:i1].sum())
def add(c,v): i0,j0,i1,j1=c; occ[j0:j1,i0:i1]+=v
C={r:cells(r,*st[r]) for r in mem}
for r in mem: add(C[r],1)
nets={}
for r in mem:
  for q in parts[r]['pads']:
    if q['net']: nets.setdefault(q['net'],[]).append((r,q['lx'],q['ly']))
nets={n:v for n,v in nets.items() if len({e[0] for e in v})>1}
def W(n):
  if n.endswith('_SW') or n=='BOOST_SW': return 20
  if n in ('GND',): return 3
  if n in ('U4_HG','U4_LG','U4_BOOT','U20_GATE','BOOST_GATE') or n.endswith('_BOOT'): return 8
  return 2
def ncost(n):
  pts=[]
  for r,lx,ly in nets[n]:
    x,y,a=st[r]; px,py=rot(lx,ly,a); pts.append((x+px,y+py))
  if n=='GND' or len(pts)>5:
    a=np.array(pts); d=np.sqrt(((a[:,None,:]-a[None,:,:])**2).sum(-1)); np.fill_diagonal(d,1e9); return W(n)*0.7*d.min(1).sum()
  xs=[p[0] for p in pts]; ys=[p[1] for p in pts]; return W(n)*((max(xs)-min(xs))+(max(ys)-min(ys)))
of={}
for n,v in nets.items():
  for r,_,_ in v: of.setdefault(r,set()).add(n)
NC={n:ncost(n) for n in nets}
def bbox():
  xs=[];ys=[]
  for r in mem: i0,j0,i1,j1=C[r]; xs+=[i0,i1]; ys+=[j0,j1]
  return (max(xs)-min(xs))*G+(max(ys)-min(ys))*G
IT=int(sys.argv[3]) if len(sys.argv)>3 else 300000
for it in range(IT):
  f=it/IT; T=5*(0.01/5)**f; lam=0.5*(400/0.5)**f; hard=f>0.7
  r=random.choice(mem); x,y,a=st[r]
  if random.random()<0.25: new=[x,y,(a+random.choice((90,180,270)))%360]
  else: sg=max(0.1,6*(1-f)**2); new=[x+random.gauss(0,sg),y+random.gauss(0,sg),a]
  add(C[r],-1); po=ovl(C[r]); nc=cells(r,*new); pn=ovl(nc)
  if hard and pn>0 and pn>=po: add(C[r],1); continue
  old=st[r]; b0=bbox(); st[r]=new; oc=C[r]; C[r]=nc
  ch={n:ncost(n) for n in of.get(r,())}; b1=bbox()
  d=sum(ch[n]-NC[n] for n in ch)+lam*(pn-po)*G*G+0.5*(b1-b0)
  if d<0 or random.random()<math.exp(-d/T): NC.update(ch)
  else: st[r]=old; C[r]=oc
  add(C[r],1)
bad=[]
for r in mem:
  add(C[r],-1)
  if ovl(C[r]): bad.append(r)
  add(C[r],1)
# offsets from the first anchor
a0=mem[0]
ref={'LBUCK':'U4','B12':'U3','B5':'U5','BOOST':'U20','LOUT':'U7'}[name]
bx,by,ba=st[ref]
rel={r:[*rot(st[r][0]-bx,st[r][1]-by,-ba),(st[r][2]-ba)%360] for r in mem}
sw=[n for n in nets if n.endswith('_SW') or n=='BOOST_SW']
def span(n):
  pts=[]
  for r,lx,ly in nets[n]:
    x,y,a=st[r]; px,py=rot(lx,ly,a); pts.append((x+px,y+py))
  return max(math.dist(p,q) for p in pts for q in pts)
print(name,'overlap',bad,'bbox %.1f'%bbox(),'cost %.0f'%sum(NC.values()),{n:round(span(n),1) for n in sw+[n for n in nets if n.endswith(('_HG','_LG'))]})
json.dump(dict(ref=ref,rel=rel,cost=sum(NC.values()),bad=bad,abs=st),open(f'mac_{name}_{sys.argv[2]}.json','w'))
