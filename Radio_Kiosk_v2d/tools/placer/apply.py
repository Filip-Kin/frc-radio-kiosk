import re,json,sys
src,pj,out=sys.argv[1:4]
s=open(src).read(); J=json.load(open(pj)); st=J['state']; pins=J['pins']
N=r'(-?[\d.]+)'
FIXED={'J1','J2','J3','J5','J6','J9','J11','J12','D30','D31','H1','H2','H3','H4','BT1','BT2','BT3','BT4'}
moved=0
def edit(m):
  global moved
  b=m.group(0); ref=re.search(r'\(property "Reference" "([^"]*)"',b).group(1)
  if ref=='U40':
    # new pin map: every assignable pad gets its net (or none)
    netfor={v:k for k,v in pins.items()}
    def pad(pm):
      pb=pm.group(0); num=pm.group(1)
      cur=re.search(r'\(net "([^"]*)"\)',pb)
      if cur and cur.group(1) not in pins and num not in netfor: return pb
      if num in netfor:
        if cur: return pb.replace(cur.group(0),f'(net "{netfor[num]}")',1)
        return re.sub(r'(\n\t\t\t\(uuid )',f'\n\t\t\t(net "{netfor[num]}")\\1',pb,count=1)
      return pb.replace(cur.group(0),'',1) if cur else pb
    b=re.sub(r'\n\t\t\(pad "([^"]*)" \w+ \w+\n.*?\n\t\t\)',pad,b,flags=re.S)
  if ref in FIXED or ref not in st: return b
  x,y,rot=st[ref]; x=round(x,3); y=round(y,3); rot=rot%360
  at=re.search(r'\n\t\t\(at '+N+' '+N+r'(?: '+N+r')?\)',b)
  old=float(at.group(3) or 0)
  new='\n\t\t(at %g %g%s)'%(x,y,'' if rot==0 else ' %g'%rot)
  b=b.replace(at.group(0),new,1)
  d=(rot-old)%360
  if d:
    head=b.index(new)+len(new)
    b=b[:head]+re.sub(r'\(at '+N+' '+N+r'(?: '+N+r')?\)',lambda q:'(at %s %s %g)'%(q.group(1),q.group(2),(float(q.group(3) or 0)+d)%360),b[head:])
  moved+=1; return b
s=re.sub(r'\n\t\(footprint "[^"]*"\n.*?\n\t\)',edit,s,flags=re.S)
open(out,'w').write(s); print('moved',moved)
