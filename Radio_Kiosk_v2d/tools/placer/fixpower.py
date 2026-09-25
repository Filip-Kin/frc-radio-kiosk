"""1 oz power pass. Widens full-width power segments to the 1 oz class width
and adds vias beside single power vias, each only where it clears every
other-net pad, track, via, hole and the board edge on its layers. Text edit;
geometry from padpoly.json (pads of the same board). Writes <out> and
fixpower.json (uuids of what changed, for a DRC revert pass)."""
import re,json,math,sys,uuid,fnmatch
from shapely.geometry import LineString,Point,Polygon,box
from shapely.strtree import STRtree
src,out=sys.argv[1],sys.argv[2]
skip=set(json.load(open(sys.argv[3]))) if len(sys.argv)>3 else set()
s=open(src).read(); G=json.load(open('padpoly.json'))
pro=json.load(open('Radio_Kiosk_v2b.kicad_pro'))['net_settings']
cw={c['name']:c for c in pro['classes']}
def cls(n):
  for p in pro['netclass_patterns']:
    if fnmatch.fnmatchcase(n,p['pattern']): return p['netclass']
  return 'Default'
TARGET={'Heavy':2.0,'Wide':1.6,'Power':0.8}
OLD={'Heavy':1.5,'Wide':1.2,'Power':0.6}
NVIA={'Heavy':3,'Wide':3,'Power':2}
CL=0.2; EDGE=0.3
N=r'(-?[\d.]+)'
items=[]  # dict(kind,net,layers,geom-params,span)
for m in re.finditer(r'\n\t\((segment|via)\n.*?\n\t\)',s,re.S):
  x=m.group(0); net=re.search(r'\(net "([^"]*)"',x).group(1); u=re.search(r'\(uuid "([^"]*)"',x).group(1)
  if m.group(1)=='segment':
    a=tuple(map(float,re.search(r'\(start '+N+' '+N,x).groups())); e=tuple(map(float,re.search(r'\(end '+N+' '+N,x).groups()))
    items.append(dict(kind='seg',net=net,layer=re.search(r'\(layer "([^"]*)"',x).group(1)[0],a=a,e=e,w=float(re.search(r'\(width '+N,x).group(1)),uuid=u,span=m.span()))
  else:
    at=tuple(map(float,re.search(r'\(at '+N+' '+N,x).groups()))
    items.append(dict(kind='via',net=net,at=at,d=float(re.search(r'\(size '+N,x).group(1)),drill=float(re.search(r'\(drill '+N,x).group(1)),uuid=u,span=m.span()))
def geom(it,w=None):
  if it['kind']=='seg':
    ww=w or it['w']
    return LineString([it['a'],it['e']]).buffer(ww/2) if it['a']!=it['e'] else Point(it['a']).buffer(ww/2)
  return Point(it['at']).buffer(it['d']/2)
# obstacle list: (geom, net, layers set)
obs=[]
for p in G['pads']:
  if p['layer']=='hole': obs.append((Point(p['x'],p['y']).buffer(p['r']+0.05),None,{'F','B'}))  # holes clash with any net
  elif len(p['pts'])>=3: obs.append((Polygon(p['pts']),p['net'],{p['layer']}))
for i,it in enumerate(items):
  obs.append((geom(it),it['net'],{it['layer']} if it['kind']=='seg' else {'F','B'},i))
e=G['edge']; inside=box(e[0]+0.05+EDGE,e[1]+0.05+EDGE,e[2]-0.05-EDGE,e[3]-0.05-EDGE)
tree=STRtree([o[0] for o in obs])
extra=[]  # obstacles added this run
def clear(g,net,layers,self_idx=None):
  if not inside.contains(g): return False
  for k in tree.query(g.buffer(CL)):
    o=obs[k]
    if len(o)>3 and o[3]==self_idx: continue
    if o[1]==net: continue
    if not (o[2]&layers): continue
    if o[0].distance(g)<CL-1e-6: return False
  for og,on,ol in extra:
    if on!=net and (ol&layers) and og.distance(g)<CL-1e-6: return False
  return True
changes={'widened':[],'vias':[]}
edits=[]
# #region widen
for i,it in enumerate(items):
  if it['kind']!='seg': continue
  c=cls(it['net'])
  if c not in TARGET or it['uuid'] in skip: continue
  if not (OLD[c]-0.01<=it['w']<TARGET[c]-0.01): continue
  for w in (TARGET[c],(TARGET[c]+it['w'])/2):
    g=geom(it,w)
    if clear(g,it['net'],{it['layer']},i):
      obs[[k for k,o in enumerate(obs) if len(o)>3 and o[3]==i][0]]=(g,it['net'],{it['layer']},i)
      tree=STRtree([o[0] for o in obs])
      x=s[it['span'][0]:it['span'][1]]
      edits.append((it['span'],re.sub(r'\(width '+N+r'\)',f'(width {w:g})',x,count=1)))
      changes['widened'].append((it['uuid'],it['net'],it['w'],w)); break
# #region vias
vias=[(i,it) for i,it in enumerate(items) if it['kind']=='via' and cls(it['net']) in NVIA]
done=set()
newtext=[]
for i,v in vias:
  if i in done: continue
  cl=[j for j,u in vias if u['net']==v['net'] and math.dist(u['at'],v['at'])<2.5]
  done.update(cl)
  c0=cls(v['net'])
  attw=max([it['w'] for it in items if it['kind']=='seg' and it['net']==v['net'] and any(math.dist(q,items[j]['at'])<0.05 for j in cl for q in (it['a'],it['e']))] or [0])
  if attw<OLD[c0]-0.01: continue
  need=NVIA[c0]-len(cl)
  if need<=0 or v['uuid'] in skip: continue
  c=cls(v['net']); sw=min(TARGET[c],v['d'])
  base=v['at']; r=v['d']+0.3
  placed=[]
  for k in range(24):
    if len(placed)>=need: break
    ang=2*math.pi*k/24
    p=(round(base[0]+r*math.cos(ang),3),round(base[1]+r*math.sin(ang),3))
    if any(math.dist(p,q)<v['d']+0.3 for q in placed): continue
    vg=Point(p).buffer(v['d']/2); st=LineString([base,p]).buffer(sw/2)
    # hole-to-hole with every other drill
    g=vg.union(st)
    if not clear(g,v['net'],{'F','B'}): continue
    if any(math.dist(p,u['at'])<v['d']/2+u['d']/2+0.25 for u in items if u['kind']=='via' and u is not v): continue
    placed.append(p); extra.append((g,v['net'],{'F','B'}))
    uid=lambda: str(uuid.uuid4())
    newtext.append(f'\n\t(via\n\t\t(at {p[0]} {p[1]})\n\t\t(size {v["d"]:g})\n\t\t(drill {v["drill"]:g})\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "{v["net"]}")\n\t\t(uuid "{(u1:=uid())}")\n\t)')
    ids=[u1]
    for L in ('F.Cu','B.Cu'):
      newtext.append(f'\n\t(segment\n\t\t(start {base[0]} {base[1]})\n\t\t(end {p[0]} {p[1]})\n\t\t(width {sw:g})\n\t\t(layer "{L}")\n\t\t(net "{v["net"]}")\n\t\t(uuid "{(u2:=uid())}")\n\t)'); ids.append(u2)
    changes['vias'].append((ids,v['net'],base,p))
  if len(placed)<need: changes.setdefault('short',[]).append((v['net'],base,len(cl)+len(placed),NVIA[c]))
for (a,b2),t in sorted(edits,reverse=True): s=s[:a]+t+s[b2:]
# insert new copper before the first zone
k=s.index('\n\t(zone'); s=s[:k]+''.join(newtext)+s[k:]
open(out,'w').write(s); json.dump(changes,open('fixpower.json','w'),indent=1)
print('widened',len(changes['widened']),'vias added',len(changes['vias']))
import collections
print('not widened', collections.Counter((it['net'],it['w']) for it in items if it['kind']=='seg' and cls(it['net']) in TARGET and OLD[cls(it['net'])]-0.01<=it['w']<TARGET[cls(it['net'])]-0.01 and it['uuid'] not in {w[0] for w in changes['widened']}).most_common(20))
print('short of vias',changes.get('short'))
