import os,sys,json,math
PJ=sys.argv[1]; sys.argv=[sys.argv[0]]
os.environ.pop('INIT',None)
exec(open('setup5.py').read())
j=json.load(open(PJ)); state.update(j['state'])
for n,g in j['pins'].items():
  for e in netpins[n]:
    if e[0]==MCU: e[1]=g
worst=[]
for c,ic in CAP.items():
  if c in state and ic in state:
    d=math.dist(state[c][:2],state[ic][:2]); lim=capd(c)+3
    if d>lim: worst.append((round(d,1),c,ic,lim))
print('caps past their limit:',sorted(worst,reverse=True)[:15])
for n in ['U3_SW','U4_SW','U5_SW','BOOST_SW','U4_HG','U4_LG']:
  pts=[pinpos(r,num) for r,num in netpins.get(n,[])]
  if pts: print(n,'span %.1f mm'%max(math.dist(a,b) for a in pts for b in pts),[r for r,_ in netpins[n]])
far=[]
for p in mov:
  r=p['ref']; ds=[]
  for n in nets_of.get(r,()):
    if n in ('+3V3','+5V','VIN','VIN_USB','VIN_DC') : continue
    mine=[pinpos(r,num) for rr,num in netpins[n] if rr==r]
    oth=[pinpos(rr,num) for rr,num in netpins[n] if rr!=r]
    if mine and oth: ds.append(min(math.dist(a,b) for a in mine for b in oth))
  if ds: far.append((round(max(ds),1),r))
print('longest single connection per part (top 20):',sorted(far,reverse=True)[:20])
print('WL %.0f'%sum(netcost(n) for n in netpins))
