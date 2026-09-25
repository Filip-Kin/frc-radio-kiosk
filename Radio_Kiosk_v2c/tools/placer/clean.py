import json,re,sys
d=json.load(open('dc/drc.json')); s=open('dc/Radio_Kiosk_v2b.kicad_pcb').read(); base=open('Radio_Kiosk_v2b.kicad_pcb').read()
N=r'(-?[\d.]+)'
def key(x): return re.sub(r'\s*\(uuid "[^"]*"\)','',re.sub(r'\s*\(locked yes\)','',x))
basekeys={key(m.group(0)) for m in re.finditer(r'\n\t\((?:segment|via)\n.*?\n\t\)',base,re.S)}
dv=[];dt=[]
for x in d['violations']:
  for i in x['items']:
    if x['type']=='via_dangling': dv.append((i['pos']['x'],i['pos']['y']))
    if x['type']=='track_dangling': dt.append((i['pos']['x'],i['pos']['y']))
rm=0
def ed(m):
  global rm
  x=m.group(0)
  if key(x) in basekeys: return x
  if m.group(1)=='via':
    p=tuple(map(float,re.search(r'\(at '+N+' '+N,x).groups()))
    if any(abs(p[0]-q[0])<0.01 and abs(p[1]-q[1])<0.01 for q in dv): rm+=1; return ''
  else:
    a=tuple(map(float,re.search(r'\(start '+N+' '+N,x).groups())); e=tuple(map(float,re.search(r'\(end '+N+' '+N,x).groups()))
    if any(abs(p[0]-q[0])<0.01 and abs(p[1]-q[1])<0.01 for q in dt for p in (a,e)): rm+=1; return ''
  return x
s=re.sub(r'\n\t\((segment|via)\n.*?\n\t\)',ed,s,flags=re.S)
open('dc/Radio_Kiosk_v2b.kicad_pcb','w').write(s); print('removed',rm)
