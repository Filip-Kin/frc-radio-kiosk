import json,collections
parts=json.load(open('parts.json')); P={p['ref']:p for p in parts}
ANCH={'LAPTOP':['U4','Q40','Q41','L4'],'LCC':['U42','U43'],'LOUT':['U7','Q7'],'BYP':['Q44','Q45','U45'],
 'USBIN':['J1','U50','U41','U1','Q1','D1'],'DCIN':['J2','U2','Q2','D2'],'B12':['U3','L3','U6','Q6'],'B5':['U5','L5'],
 'BATT':['Q8','Q9','Q10','Q11','U10','F1'],'PACKDIODE':['U12','Q12'],'EFUSE':['U21','Q13','U31'],'BOOST':['U20','Q20','L20','D20'],
 'PSE':['U22','Q22','D70','D71'],'PORTSW':['Q23','Q24','D23'],'MCU':['U40','SW1','SW2','U52'],'LDO':['U51'],'LED':['U30'],'FAN':['J8','Q30','D32'],'LID':['J13']}
FIX={'J3','J5','J6','J9','J11','J12','D30','D31','H1','H2','H3','H4','BT1','BT2','BT3','BT4'}
nets=collections.defaultdict(set)
for p in parts:
  for q in p['pads']: nets[q['net']].add(p['ref'])
BIG={n for n,v in nets.items() if len(v)>7 or n in ('GND','+12V','') or n.startswith('ETH')}
blk={r:b for b,l in ANCH.items() for r in l}
for _ in range(10):
  ch=0
  for p in parts:
    r=p['ref']
    if r in blk or r in FIX: continue
    sc=collections.Counter()
    for q in p['pads']:
      if q['net'] in BIG: continue
      for o in nets[q['net']]:
        if o!=r and o in blk: sc[blk[o]]+=1
    if sc: blk[r]=sc.most_common(1)[0][0]; ch+=1
  if not ch: break
un=[p['ref'] for p in parts if p['ref'] not in blk and p['ref'] not in FIX]
print('unassigned',un)
by=collections.defaultdict(list)
for r,b in blk.items(): by[b].append(r)
for b in ANCH: 
  a=sum((P[r]['crt'][2]-P[r]['crt'][0]+0.8)*(P[r]['crt'][3]-P[r]['crt'][1]+0.8) for r in by[b])
  print(f'{b:10} {a:5.0f}mm2',' '.join(sorted(by[b])))
json.dump(blk,open('blocks.json','w'))
