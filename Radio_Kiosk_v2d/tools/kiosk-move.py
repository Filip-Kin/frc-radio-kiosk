"""Move footprints by reference: text edit of the (at x y rot) line. Usage: kiosk-move.py board.kicad_pcb REF=x,y[,rot] ..."""
import re, sys
path=sys.argv[1]; pcb=open(path).read(); moves={}
for a in sys.argv[2:]:
    ref,v=a.split('='); parts=v.split(','); moves[ref]=(float(parts[0]),float(parts[1]),float(parts[2]) if len(parts)>2 else None)
done=[]
def edit(m):
    b=m.group(0); r=re.search(r'\(property "Reference" "([^"]*)"', b)
    if not r or r.group(1) not in moves: return b
    x,y,rot=moves[r.group(1)]
    at=re.search(r'\n\t\t\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)', b)
    oldrot=float(at.group(3) or 0); newrot=oldrot if rot is None else rot
    new='\n\t\t(at %g %g%s)'%(x,y,'' if newrot==0 else ' %g'%newrot)
    nb=b.replace(at.group(0),new,1)
    if newrot!=oldrot:
        # pads and texts carry their own absolute rotation: shift them by the delta
        d=newrot-oldrot
        def rot(mm):
            return '(at %s %s %g)'%(mm.group(1),mm.group(2),(float(mm.group(3) or 0)+d)%360)
        head=nb.index(new)+len(new)
        nb=nb[:head]+re.sub(r'\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)', rot, nb[head:])
    done.append((r.group(1),x,y,newrot)); return nb
pcb=re.sub(r'\n\t\(footprint "[^"]*"\n.*?\n\t\)', edit, pcb, flags=re.S)
open(path,'w').write(pcb); print('moved:', done)
