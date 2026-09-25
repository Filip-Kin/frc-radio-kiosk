"""Push Value and LCSC from netlist.net into board.kicad_pcb footprint properties (text pass)."""
import re, uuid, sys
net=open(sys.argv[1]).read(); path=sys.argv[2]; pcb=open(path).read()
props={}
for m in re.finditer(r'\(comp\n\t\t\t\(ref "([^"]+)"\)\n\t\t\t\(value "([^"]*)"\)(.*?)\n\t\t\)', net, flags=re.S):
    ref,val,rest=m.groups(); lc=re.search(r'\(name "LCSC"\) "([^"]*)"', rest); props[ref]=(val, lc.group(1) if lc else None)
changed=[]
def edit(m):
    b=m.group(0); r=re.search(r'\(property "Reference" "([^"]*)"', b)
    if not r or r.group(1) not in props: return b
    val,lc=props[r.group(1)]; nb=b
    old=re.search(r'\(property "Value" "([^"]*)"', nb)
    if old and old.group(1)!=val: nb=nb.replace(old.group(0), '(property "Value" "%s"'%val,1); changed.append((r.group(1),'value',old.group(1),val))
    if lc:
        oldl=re.search(r'\(property "LCSC" "([^"]*)"', nb)
        if oldl:
            if oldl.group(1)!=lc: nb=nb.replace(oldl.group(0),'(property "LCSC" "%s"'%lc,1); changed.append((r.group(1),'lcsc',oldl.group(1),lc))
        else:
            vm=re.search(r'\n\t\t\(property "Value" "[^"]*"\n.*?\n\t\t\)', nb, flags=re.S)
            blk=vm.group(0).replace('(property "Value" "%s"'%val,'(property "LCSC" "%s"'%lc,1)
            blk=re.sub(r'\(uuid "[^"]*"\)', lambda x: '(uuid "%s")'%uuid.uuid4(), blk)
            if '(hide yes)' not in blk: blk=blk.replace('\n\t\t\t(layer', '\n\t\t\t(hide yes)\n\t\t\t(layer',1)
            nb=nb.replace(vm.group(0), vm.group(0)+blk,1); changed.append((r.group(1),'lcsc',None,lc))
    return nb
pcb=re.sub(r'\n\t\(footprint "[^"]*"\n.*?\n\t\)', edit, pcb, flags=re.S)
open(path,'w').write(pcb); print('changed:', changed)
