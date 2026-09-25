"""v2c placer with rigid macros. A body is one part or one power-stage macro;
moves shift/rotate/swap bodies, overlap uses each body's union mask."""
import os,sys
seed,ITER,OUT=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]; sys.argv=[sys.argv[0]]
os.environ.pop('INIT',None)
exec(open('setup5.py').read())
random.seed(seed)
occ[:]=0
MAC=json.load(open('macfinal.json'))
inmac={r:m for m,v in MAC.items() for r in v['rel']}
bodies={}
for p in mov:
  r=p['ref']
  if r in inmac: continue
  bodies[r]=dict(mem=[(r,0.0,0.0,0.0)])
for m,v in MAC.items():
  bodies[m]=dict(mem=[(r,d[0],d[1],d[2]) for r,d in v['rel'].items()])
# masks per rotation, in cells, relative to the body origin
def mkmask(b,a):
  boxes=[]
  for r,dx,dy,dr in b['mem']:
    px,py=rot(dx,dy,a); p=parts[idx[r]]; bb=rbox(p['crt'],(dr+a)%360); m=M[r]
    boxes.append((px+bb[0]-m,py+bb[1]-m,px+bb[2]+m,py+bb[3]+m))
  x0=min(t[0] for t in boxes);y0=min(t[1] for t in boxes);x1=max(t[2] for t in boxes);y1=max(t[3] for t in boxes)
  i0=int(math.floor(x0/G));j0=int(math.floor(y0/G));i1=int(math.ceil(x1/G));j1=int(math.ceil(y1/G))
  mk=np.zeros((j1-j0,i1-i0),np.int16)
  for t in boxes:
    a0=int(math.floor(t[0]/G))-i0;b0=int(math.floor(t[1]/G))-j0;a1=int(math.ceil(t[2]/G))-i0;b1=int(math.ceil(t[3]/G))-j0
    mk[b0:b1,a0:a1]=1
  return (i0,j0,mk)
for k,b in bodies.items():
  b['masks']={a:mkmask(b,a) for a in (0,90,180,270)}
  b['tht']=any(r in THT for r,*_ in b['mem'])
bst={}
def place_members(k):
  x,y,a=bst[k]
  for r,dx,dy,dr in bodies[k]['mem']:
    px,py=rot(dx,dy,a); state[r]=[x+px,y+py,(dr+a)%360]
def win(k):
  x,y,a=bst[k]; i0,j0,mk=bodies[k]['masks'][a]
  ci=int(round(x/G))+i0; cj=int(round(y/G))+j0
  return ci,cj,mk
def ovl_b(k):
  ci,cj,mk=win(k); h,w=mk.shape
  if ci<0 or cj<0 or ci+w>NX or cj+h>NY: return 10**6
  pen=int((mk*(occ[cj:cj+h,ci:ci+w]+keep[cj:cj+h,ci:ci+w])).sum())
  if bodies[k]['tht']: pen+=int((mk*backcrt[cj:cj+h,ci:ci+w]).sum())
  return pen
def add_b(k,v):
  ci,cj,mk=win(k); h,w=mk.shape
  if ci<0 or cj<0 or ci+w>NX or cj+h>NY: return
  occ[cj:cj+h,ci:ci+w]+=v*mk
def reg_b(k): return sum(regpen(r,*state[r][:2]) for r,*_ in bodies[k]['mem'])
bnets={k:set().union(*[nets_of.get(r,set()) for r,*_ in b['mem']]) for k,b in bodies.items()}
# caps tied to a macro member: their penalty moves with the macro
capof={}
for c,ic in CAP.items():
  if ic in inmac and c in bodies: capof.setdefault(inmac[ic],[]).append(c)
  elif ic in bodies and c in bodies: capof.setdefault(ic,[]).append(c)
def reg_full(k): return reg_b(k)+sum(regpen(c,*state[c][:2]) for c in capof.get(k,[]))
# start: macros at their block region centre, singles in their regions
REGC={'LBUCK':'LAPTOP','B12':'B12','B5':'B5','BOOST':'BOOST','LOUT':'LOUT'}
for k,b in bodies.items():
  if k in MAC:
    x0,y0,x1,y1=REG[REGC[k]]; bst[k]=[random.uniform(x0+8,x1-8),random.uniform(y0+8,y1-8),random.choice((0,90,180,270))]
  else:
    r=k; bl=BLK.get(r)
    if bl and r not in FREEMCU: x0,y0,x1,y1=REG[bl]; bst[k]=[random.uniform(x0+2,x1-2),random.uniform(y0+2,y1-2),random.choice((0,90,180,270))]
    else: bst[k]=[random.uniform(12,90),random.uniform(12,128),random.choice((0,90,180,270))]
  place_members(k); add_b(k,1)
keys=list(bodies)
NC={n:netcost(n) for n in netpins}
def total_ovl(): return sum(1 for k in keys if (add_b(k,-1),ovl_b(k),add_b(k,1))[1])
def setpin(n,old,new):
  for e in netpins[n]:
    if e[0]==MCU and e[1]==old: e[1]=new
def pinswap(T):
  n1=random.choice(list(pin_of)); g=random.choice(ALLOW[n1])
  if g==pin_of[n1]: return
  n2=next((k for k,v in pin_of.items() if v==g),None)
  if n2 and pin_of[n1] not in ALLOW[n2]: return
  a1=pin_of[n1]; setpin(n1,a1,g)
  if n2: setpin(n2,g,a1)
  ch={n:netcost(n) for n in [n1]+([n2] if n2 else [])}; dW=sum(ch[n]-NC[n] for n in ch)
  if dW<0 or random.random()<math.exp(-dW/T):
    pin_of[n1]=g
    if n2: pin_of[n2]=a1
    NC.update(ch)
  else:
    setpin(n1,g,a1)
    if n2: setpin(n2,a1,g)
RW=15.0
def trymove(k,new,T,lam,hard):
  add_b(k,-1); po=ovl_b(k); r0=reg_full(k); old=bst[k]; bst[k]=new; place_members(k); pn=ovl_b(k)
  if hard and pn>0 and pn>=po:
    bst[k]=old; place_members(k); add_b(k,1); return False
  ch={n:netcost(n) for n in bnets[k]}
  d=sum(ch[n]-NC[n] for n in ch)+lam*(pn-po)*G*G+RW*(reg_full(k)-r0)-(20*(po-pn)*G*G if hard else 0)
  if d<0 or random.random()<math.exp(-d/T):
    NC.update(ch); add_b(k,1); return True
  bst[k]=old; place_members(k); add_b(k,1); return False
def phase(n,T0,T1,L0,L1,sig0,hard):
  for it in range(n):
    f=it/n; T=T0*(T1/T0)**f; lam=L0*(L1/L0)**f; sig=max(0.1,sig0*(1-f)**2)
    mv=random.random()
    if mv<0.05: pinswap(T); continue
    k=random.choice(keys); x,y,a=bst[k]
    if mv<0.2: new=[x,y,(a+random.choice((90,180,270)))%360]
    else: new=[round(min(93,max(2,x+random.gauss(0,sig)))/0.05)*0.05,round(min(138,max(2,y+random.gauss(0,sig)))/0.05)*0.05,a]
    trymove(k,new,T,lam,hard)
evicted=[]
def legalize():
  bad=[k for k in keys if (add_b(k,-1),ovl_b(k),add_b(k,1))[1]]
  bad.sort(key=lambda k:-bodies[k]['masks'][0][2].size)
  while bad or evicted:
    if not bad: bad=list(dict.fromkeys(evicted)); evicted.clear()
    k=bad.pop(0)
    add_b(k,-1)
    if not ovl_b(k): add_b(k,1); continue
    x0,y0,a0=bst[k]; best=None
    for rad in [q*0.25 for q in range(0,220)]:
      steps=max(1,int(2*math.pi*rad/0.25))
      for s_ in range(steps):
        t=2*math.pi*s_/steps; x=round((x0+rad*math.cos(t))/0.05)*0.05; y=round((y0+rad*math.sin(t))/0.05)*0.05
        for a in (a0,(a0+90)%360,(a0+180)%360,(a0+270)%360):
          bst[k]=[x,y,a]; place_members(k)
          if ovl_b(k)==0:
            sc=sum(netcost(n)-NC[n] for n in bnets[k])+RW*reg_full(k)+1.5*rad
            if best is None or sc<best[0]: best=(sc,x,y,a)
      if best and rad>best[0]/1.5+2: break
    if best: bst[k]=list(best[1:])
    else:
      # no hole this big: take the spot with no keep-out clash and the least
      # overlap with other bodies, then evict whatever sits there
      cand=None
      for rad in [q*0.5 for q in range(0,90)]:
        steps=max(1,int(2*math.pi*rad/0.5))
        for s_ in range(steps):
          t=2*math.pi*s_/steps; x=round((x0+rad*math.cos(t))/0.05)*0.05; y=round((y0+rad*math.sin(t))/0.05)*0.05
          for a in (0,90,180,270):
            bst[k]=[x,y,a]; place_members(k); ci,cj,mk=win(k); h,w=mk.shape
            if ci<0 or cj<0 or ci+w>NX or cj+h>NY: continue
            if int((mk*keep[cj:cj+h,ci:ci+w]).sum()) or (bodies[k]['tht'] and int((mk*backcrt[cj:cj+h,ci:ci+w]).sum())): continue
            o=int((mk*occ[cj:cj+h,ci:ci+w]).sum()); sc=o+RW*reg_full(k)+2*rad
            if cand is None or sc<cand[0]: cand=(sc,x,y,a)
      if cand:
        bst[k]=list(cand[1:]); place_members(k); ci,cj,mk=win(k); h,w=mk.shape
        for k2 in keys:
          if k2==k or k2 in MAC: continue
          c2,d2,m2=win(k2); hh,ww=m2.shape
          a0_,b0_=max(ci,c2),max(cj,d2); a1_,b1_=min(ci+w,c2+ww),min(cj+h,d2+hh)
          if a1_>a0_ and b1_>b0_ and (mk[b0_-cj:b1_-cj,a0_-ci:a1_-ci]*m2[b0_-d2:b1_-d2,a0_-c2:a1_-c2]).any():
            add_b(k2,-1); evicted.append(k2); bst[k2]=[bst[k2][0],bst[k2][1],bst[k2][2]]; add_b(k2,1)
      else: bst[k]=[x0,y0,a0]
    place_members(k)
    for n in bnets[k]: NC[n]=netcost(n)
    add_b(k,1)
INIT=os.environ.get('INITM')
if INIT:
  j=json.load(open(INIT)); occ[:]=0
  for k,b in bodies.items():
    r0,dx,dy,dr=b['mem'][0]; x,y,a=j['state'][r0]; a0=(a-dr)%360; px,py=rot(dx,dy,a0); bst[k]=[x-px,y-py,round(a0/90)*90%360]
    place_members(k); add_b(k,1)
  for n,g in j['pins'].items():
    for e in netpins[n]:
      if e[0]==MCU: e[1]=g
  pin_of.update(j['pins']); NC.update({n:netcost(n) for n in netpins})
  for spec in filter(None,os.environ.get('FORCE','').split(';')):
    k,xy=spec.split(':'); x,y=map(float,xy.split(','))
    add_b(k,-1); bst[k]=[x,y,bst[k][2]]; place_members(k); add_b(k,1)
  NC.update({n:netcost(n) for n in netpins})
  phase(ITER,float(os.environ.get('T0','1')),0.05,float(os.environ.get('L0','5')),300.0,float(os.environ.get('SIG','5')),False)
else:
  phase(ITER,8.0,0.05,0.3,300.0,12,False)
print('phase1 WL %.0f overlapping %d'%(sum(NC.values()),total_ovl()),flush=True)
for cyc in range(3):
  legalize(); print('legalized, overlapping',total_ovl(),flush=True)
  phase(400000,0.8,0.01,300,300,2.5,True)
  print('cycle',cyc,'refined WL %.0f overlapping %d'%(sum(NC.values()),total_ovl()),flush=True)
  if not total_ovl(): break
json.dump(dict(state=state,pins=pin_of,wl=sum(NC.values()),bad=[k for k in keys if (add_b(k,-1),ovl_b(k),add_b(k,1))[1]]),open(OUT,'w'))
