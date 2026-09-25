"""Find each power stage's members: anchors plus every part whose signal nets
stay inside the stage (rails and GND do not count)."""
import json,collections
parts=json.load(open('parts.json')); P={p['ref']:p for p in parts}
RAIL={'GND','+12V','+3V3','+5V','VIN','VIN_USB','VIN_DC','+12V_BUCK','+15V6_BUCK','+15V6_S','LAPTOP_OUT','BOOST_OUT',''}
CAP=json.load(open('capassoc.json'))
MAC={'LBUCK':['U4','Q40','Q41','L4'],'B12':['U3','L3'],'B5':['U5','L5'],'BOOST':['U20','Q20','L20','D20'],'LOUT':['U7','Q7']}
nets=collections.defaultdict(set)
for p in parts:
  for q in p['pads']: nets[q['net']].add(p['ref'])
out={}
for m,anch in MAC.items():
  mem=set(anch)
  ic=set(anch)
  for c,i in CAP.items():
    if i in ic and not P[c]['back']: mem.add(c)
  for _ in range(3):
    for p in parts:
      r=p['ref']
      if r in mem or p['back'] or r.startswith(('J','H','BT')): continue
      sig={q['net'] for q in p['pads']}-RAIL
      S={q['ref'] for q in parts if len(q['pads'])==2 and q['ref'][0] in 'RC'}
      if sig and all(nets[n]<=mem|S|{r} and nets[n]&mem for n in sig): mem.add(r)
  mem|=set({'LBUCK':['C46'],'B12':[],'B5':[],'BOOST':[],'LOUT':['C5','C8']}[m])
  out[m]=sorted(mem)
  print(m,len(mem),' '.join(sorted(mem)))
json.dump(out,open('macros.json','w'))
