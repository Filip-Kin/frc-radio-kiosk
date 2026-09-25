"""v2c placer: simulated annealing over position, rotation and MCU pin map.
Cost = weighted pin-level wirelength + overlap of margin-inflated courtyards
(with each other and with keep-outs). Writes place.json."""
import json,math,random,re,fnmatch,sys,time
import numpy as np
random.seed(int(sys.argv[1]) if len(sys.argv)>1 else 1)
ITER=int(sys.argv[2]) if len(sys.argv)>2 else 200000
parts=json.load(open('parts.json'))
PRO=json.load(open('board.kicad_pro'))['net_settings']
def ncls(n):
  for p in PRO['netclass_patterns']:
    if fnmatch.fnmatchcase(n,p['pattern']): return p['netclass']
  return 'Default'
FIXED={'J1','J2','J3','J5','J6','J9','J11','J12','D30','D31','H1','H2','H3','H4','BT1','BT2','BT3','BT4'}
EXCL={'GND','+12V',''}
G=0.25; BW,BH=95.0,140.0; NX,NY=int(BW/G),int(BH/G)
# #region keep-out raster
keep=np.zeros((NY,NX),np.int16)
def rect(a,x0,y0,x1,y1,v=1):
  i0=max(0,int(math.floor(x0/G)));i1=min(NX,int(math.ceil(x1/G)));j0=max(0,int(math.floor(y0/G)));j1=min(NY,int(math.ceil(y1/G)))
  if i1>i0 and j1>j0: a[j0:j1,i0:i1]+=v
E=0.6
rect(keep,0,0,BW,E);rect(keep,0,BH-E,BW,BH);rect(keep,0,0,E,BH);rect(keep,BW-E,0,BW,BH)
def rot(lx,ly,a):
  t=math.radians(a); return lx*math.cos(t)+ly*math.sin(t), -lx*math.sin(t)+ly*math.cos(t)
def rbox(b,a):
  pts=[rot(x,y,a) for x in (b[0],b[2]) for y in (b[1],b[3])]
  return min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)
for p in parts:
  if p['ref'] in FIXED:
    if not p['back']:
      b=rbox(p['crt'],p['rot']); rect(keep,p['x']+b[0]-0.3,p['y']+b[1]-0.3,p['x']+b[2]+0.3,p['y']+b[3]+0.3)
    for q in p['pads']:
      if q['drill']>0 or p['back']:
        px,py=rot(q['lx'],q['ly'],p['rot']); r=max(q['w'],q['h'])/2+0.6
        rect(keep,p['x']+px-r,p['y']+py-r,p['x']+px+r,p['y']+py+r)
# Ethernet copper and the silk credit
s=open('board.kicad_pcb').read(); N=r'(-?[\d.]+)'
for m in re.finditer(r'\n\t\((segment|via)\n.*?\n\t\)',s,re.S):
  x=m.group(0)
  if '(net "ETH_' not in x: continue
  if m.group(1)=='segment':
    a=tuple(map(float,re.search(r'\(start '+N+' '+N,x).groups())); e=tuple(map(float,re.search(r'\(end '+N+' '+N,x).groups()))
    n=max(2,int(math.dist(a,e)/0.2))
    for k in range(n+1):
      cx=a[0]+(e[0]-a[0])*k/n; cy=a[1]+(e[1]-a[1])*k/n; rect(keep,cx-0.9,cy-0.9,cx+0.9,cy+0.9)
  else:
    at=tuple(map(float,re.search(r'\(at '+N+' '+N,x).groups())); rect(keep,at[0]-1.0,at[1]-1.0,at[0]+1.0,at[1]+1.0)
rect(keep,1.5,82,5.5,123)   # board credit text along the left edge
rect(keep,0,14,6.5,125.0)   # pairs down the left edge: front stays GND over them
keep=(keep>0).astype(np.int16)
# #region movable parts
mov=[p for p in parts if p['ref'] not in FIXED and not p['back']]
def margin(p):
  l=p['lib']
  if 'LQFP' in l: return 1.4
  if any(k in l for k in ('SOIC','TSSOP','ESSOP','HTSSOP','SOT-23-6','SOT-23-5','LFPAK','SOT-223')): return 0.8
  if any(k in l for k in ('TO-252','IND-SMD','L_12x12','SRP7028','CP_Elec','USB','CONN','SW_SPST','2512')): return 0.6
  return 0.4
idx={p['ref']:i for i,p in enumerate(parts)}
state={p['ref']:[p['x'],p['y'],p['rot']] for p in parts}
import os
if os.environ.get('INIT'):
  _j=json.load(open(os.environ['INIT'])); state.update({k:v for k,v in _j['state'].items()}); _pins=_j['pins']
else: _pins=None
M={p['ref']:margin(p) for p in mov}
occ=keep.copy()*0  # movable occupancy counts
def cells(ref,x,y,a):
  p=parts[idx[ref]]; b=rbox(p['crt'],a); m=M[ref]
  x0,y0,x1,y1=x+b[0]-m,y+b[1]-m,x+b[2]+m,y+b[3]+m
  i0=int(math.floor(x0/G));i1=int(math.ceil(x1/G));j0=int(math.floor(y0/G));j1=int(math.ceil(y1/G))
  return i0,j0,i1,j1
backcrt=np.zeros((NY,NX),np.int16)
for p in parts:
  if p['back']:
    b=rbox(p['crt'],p['rot']); rect(backcrt,p['x']+b[0],p['y']+b[1],p['x']+b[2],p['y']+b[3])
backcrt=(backcrt>0).astype(np.int16)
THT={p['ref'] for p in parts if any(q['drill']>0 for q in p['pads']) and not p['back']}
keep_default=keep
def ovl(c,r=None):
  i0,j0,i1,j1=c; pen=0
  # out of board counts as keep-out
  ci0,cj0,ci1,cj1=max(0,i0),max(0,j0),min(NX,i1),min(NY,j1)
  pen+=(i1-i0)*(j1-j0)-max(0,ci1-ci0)*max(0,cj1-cj0)
  if ci1>ci0 and cj1>cj0:
    pen+=int(keep[cj0:cj1,ci0:ci1].sum())+int(occ[cj0:cj1,ci0:ci1].sum())
    if r in THT: pen+=int(backcrt[cj0:cj1,ci0:ci1].sum())
  return pen
def add(c,v):
  i0,j0,i1,j1=c; occ[max(0,j0):min(NY,j1),max(0,i0):min(NX,i1)]+=v
C={}
for p in mov:
  c=cells(p['ref'],*state[p['ref']]); C[p['ref']]=c; add(c,1)
# #region nets and MCU pin map
MCU='U40'
ADC=[str(i) for i in range(10,20)]
ANALOG=['VIN_SENSE','PACK_SENSE','PASSIVE_IMON','TEMP_SENSE','FAN_SENSE','USB_ISENSE','DCIN_SENSE','PORT_SENSE','LAPTOP_ISENSE']
GPIO=[str(i) for i in [2,3,4,5,6]+list(range(10,23))+list(range(25,32))+[38,39,40,41,45,46]]
ALLOW={n:ADC for n in ANALOG}
ALLOW['FAN_PWM']=['16','17','18','19','40','41']
ALLOW['LAPTOP_ILIM_PWM']=['29','30','31']
for n in ['LAPTOP_OK','LAPTOP_BYP']: ALLOW[n]=GPIO
for n in ['LAPTOP_EN','TEST_LOAD','BOOST_SD','PASSIVE_EN','PSE_EN','PORT_SW','USB_DIS','BK_EN','BK_ON','PASSIVE_FLT','PSE_ON','PD_PG','PD_SCL','PD_SDA','LED_DATA']:
  ALLOW[n]=[g for g in GPIO if g not in ('2','3','4')]   # PC13-15 are weak; keep them for the two slow signals
mcu=parts[idx[MCU]]
padmap={q['num']:q for q in mcu['pads']}
pin_of={q['net']:q['num'] for q in mcu['pads'] if q['net'] in ALLOW}
if _pins:
  for n,g in _pins.items():
    for e in netpins.get(n,[]) if False else []: pass
netpins={}   # net -> list of (ref, padnum)
for p in parts:
  for q in p['pads']:
    if q['net'] in EXCL or q['net'].startswith('ETH_'): continue
    netpins.setdefault(q['net'],[]).append([p['ref'],q['num']])
def W(n):
  c=ncls(n)
  if n in ('U3_SW','U4_SW','U5_SW'): return 20
  if n=='BOOST_SW': return 10
  if n in ('U4_HG','U4_LG','U4_BOOT','U20_GATE','BOOST_GATE'): return 8
  return {'Heavy':3,'Wide':3,'Power':1.5}.get(c,1)
padxy={}
for p in parts: padxy[p['ref']]={q['num']:(q['lx'],q['ly']) for q in p['pads']}
def pinpos(ref,num):
  x,y,a=state[ref]; lx,ly=padxy[ref][num]; px,py=rot(lx,ly,a); return x+px,y+py
def netcost(n):
  pts=[pinpos(r,num) for r,num in netpins[n]]
  if len(pts)<2: return 0
  if len(pts)<=5:
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]; return W(n)*((max(xs)-min(xs))+(max(ys)-min(ys)))
  a=np.array(pts); d=np.sqrt(((a[:,None,:]-a[None,:,:])**2).sum(-1)); np.fill_diagonal(d,1e9)
  return W(n)*0.7*d.min(1).sum()
nets_of={}
for n,l in netpins.items():
  for r,_ in l: nets_of.setdefault(r,set()).add(n)
NC={n:netcost(n) for n in netpins}
WL=sum(NC.values())
OV=sum(ovl(C[r]) for r in C)//1  # approximate (counts pairs twice-ish)

BLK=json.load(open('blocks.json'))
REG={'LAPTOP':(7,14,50,49),'LOUT':(7,14,50,49),'LCC':(7,47,40,86),'BYP':(7,47,50,86),'BYPFET':(7,14,62,47),
 'USBIN':(50,14,95,47),'DCIN':(50,14,95,47),'LDO':(45,14,95,50),'LED':(62,14,95,47),
 'MCU':(30,47,82,86),'BATT':(7,47,82,86),'PACKDIODE':(7,47,82,86),'FAN':(80,45,95,95),'LID':(80,45,95,95),
 'EFUSE':(7,84,95,140),'BOOST':(7,84,95,140),'PSE':(7,84,95,140),'PORTSW':(7,84,95,140),'B12':(7,47,95,112),'B5':(50,14,95,52)}
ANCH=set(json.load(open('anchors.json')))
NEAR={'D1':'J1','D2':'J2','D22':'J5'}
CAP=json.load(open('capassoc.json'))
NEAR2={r:('J5',30,8) for r in ('U21','Q13','Q23','Q24','U22','Q22','D70','D71')}
NEAR2.update({'U6':('U3',12,15),'Q6':('U3',12,15)})
def capd(r):
  l=parts[idx[r]]['lib']
  return 12 if 'CP_Elec' in l else 6 if ('1210' in l or '1206' in l) else 4
BLK['Q44']='BYPFET'
FREEMCU={r for r,b in BLK.items() if b=='MCU' and r[0] in 'RC' and len(parts[idx[r]]['pads'])==2}
def regpen(r,x,y):
  pen=0.0
  if r in NEAR:
    q=parts[idx[NEAR[r]]]; d=math.dist((x,y),(q['x'],q['y']))
    pen+=10*max(0,d-12)
  if r in NEAR2:
    t,lim,w=NEAR2[r]; q=state[t]; d=math.dist((x,y),(q[0],q[1]))
    pen+=w*max(0,d-lim)
  if r in CAP and CAP[r] in idx:
    q=state[CAP[r]]; d=math.dist((x,y),(q[0],q[1]))
    pen+=60*max(0,d-capd(r)-3)
  if r in PAIRS:
    a0=state[r][2]%180
    for o in PAIRS[r]:
      if math.dist((x,y),state[o][:2])<8 and (state[o][2]%180)!=a0: pen+=0.2
  b=BLK.get(r)
  if b is None or r in FREEMCU: return pen
  x0,y0,x1,y1=REG[b]
  out=(max(0,x0-x)+max(0,x-x1)+max(0,y0-y)+max(0,y-y1))
  return pen+out*(40 if r in ANCH else 3)

RAILS2={'GND','+12V','+3V3','+5V','VIN','','VIN_USB','VIN_DC'}
two=[p['ref'] for p in parts if len(p['pads'])==2 and p['ref'][0] in 'RC' and not p['back']]
PAIRS={}
for r in two:
  ns={q['net'] for q in parts[idx[r]]['pads']}-RAILS2
  PAIRS[r]=[o for o in two if o!=r and ns&({q['net'] for q in parts[idx[o]]['pads']}-RAILS2)]
