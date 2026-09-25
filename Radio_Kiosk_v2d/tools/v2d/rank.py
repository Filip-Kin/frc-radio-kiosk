import os,sys,json,math
files=sys.argv[1:]; sys.argv=['x']
exec(open('setup_d.py').read())
MACR={r for v in json.load(open('macros.json')).values() for r in v}
base={k:list(v) for k,v in state.items()}
def mst(pts):
  if len(pts)<2: return 0
  inn=[pts[0]]; rest=pts[1:]; L=0
  while rest:
    d,j=min((min(math.dist(a,b) for a in inn),j) for j,b in enumerate(rest))
    L+=d; inn.append(rest.pop(j))
  return L
for f in files:
  j=json.load(open(f)); state.update(j['state'])
  for n,g in j['pins'].items():
    for e in netpins[n]:
      if e[0]==MCU: e[1]=g
  cap=0
  for c,ic in CAP.items():
    if c in MACR or c not in state or ic not in state: continue
    cap+=max(0,math.dist(state[c][:2],state[ic][:2])-capd(c)-3)
  pw=sum(mst([pinpos(r,num) for r,num in netpins[n]]) for n in netpins if ncls(n) in ('Heavy','Wide'))
  print(f'{f} WL {sum(netcost(n) for n in netpins):.0f} powerMST {pw:.0f} capexcess {cap:.0f} bad {len(j.get("bad",[]))}')
