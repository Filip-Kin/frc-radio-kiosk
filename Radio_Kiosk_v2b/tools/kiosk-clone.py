"""Add footprints by cloning an existing block: kiosk-clone.py board.kicad_pcb NEW:SRC:x,y,rot:Value:LCSC ..."""
import re, sys, uuid
path=sys.argv[1]; pcb=open(path).read()
blocks={}
for m in re.finditer(r'\n\t\(footprint "[^"]*"\n.*?\n\t\)', pcb, flags=re.S):
    r=re.search(r'\(property "Reference" "([^"]*)"', m.group(0))
    if r: blocks[r.group(1)]=m.group(0)
added=[]
for a in sys.argv[2:]:
    new,src,pos,val,lc=a.split(':'); x,y,rot=map(float,pos.split(','))
    b=blocks[src]
    at=re.search(r'\n\t\t\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)', b); oldrot=float(at.group(3) or 0)
    nb=b.replace(at.group(0),'\n\t\t(at %g %g%s)'%(x,y,'' if rot==0 else ' %g'%rot),1)
    if rot!=oldrot:
        d=rot-oldrot; head=nb.index('(at %g %g'%(x,y))+10
        nb=nb[:head]+re.sub(r'\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)', lambda mm:'(at %s %s %g)'%(mm.group(1),mm.group(2),(float(mm.group(3) or 0)+d)%360), nb[head:])
    nb=re.sub(r'\(property "Reference" "[^"]*"','(property "Reference" "%s"'%new,nb,1)
    nb=re.sub(r'\(property "Value" "[^"]*"','(property "Value" "%s"'%val,nb,1)
    if re.search(r'\(property "LCSC" "',nb): nb=re.sub(r'\(property "LCSC" "[^"]*"','(property "LCSC" "%s"'%lc,nb,1)
    nb=re.sub(r'\(uuid "[^"]*"\)', lambda mm:'(uuid "%s")'%uuid.uuid4(), nb)
    nb=re.sub(r'\(net "[^"]*"\)','(net "")',nb)  # nets come from the netlist pass
    nb=re.sub(r'\(path "[^"]*"\)','(path "")',nb)
    pcb=pcb.replace(b, b+nb,1); added.append(new)
open(path,'w').write(pcb); print('cloned:', added)
