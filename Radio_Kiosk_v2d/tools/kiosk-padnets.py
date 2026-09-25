"""Set pad nets in board.kicad_pcb from netlist.net (text pass; no track changes)."""
import re, sys
net=open(sys.argv[1]).read(); path=sys.argv[2]; pcb=open(path).read()
padnet={}
for n in re.finditer(r'\(net\n\t\t\t\(code "[^"]*"\)\n\t\t\t\(name "([^"]*)"\)(.*?)\n\t\t\)', net, flags=re.S):
    name=n.group(1).lstrip('/')
    if name.startswith('unconnected-'): continue
    for node in re.finditer(r'\(ref "([^"]+)"\)\n\t\t\t\t\(pin "([^"]+)"\)', n.group(2)): padnet[(node.group(1),node.group(2))]=name
ALIAS={"A9":"A4","B9":"B4","A12":"A1","B12":"B1"}
changed=[]
def edit(m):
    b=m.group(0); r=re.search(r'\(property "Reference" "([^"]*)"', b)
    if not r: return b
    ref=r.group(1)
    def pad(pm):
        blk=pm.group(0); num=pm.group(1); want=padnet.get((ref,num)) or padnet.get((ref,ALIAS.get(num,num)))
        cur=re.search(r'\(net "([^"]*)"\)', blk)
        if want is None or not cur or cur.group(1)==want: return blk
        changed.append((ref,num,cur.group(1),want)); return blk.replace(cur.group(0),'(net "%s")'%want,1)
    return re.sub(r'\n\t\t\(pad "([^"]*)"[^\n]*\n(?:\t\t\t[^\n]*\n)*?\t\t\)', pad, b)
pcb=re.sub(r'\n\t\(footprint "[^"]*"\n.*?\n\t\)', edit, pcb, flags=re.S)
open(path,'w').write(pcb); print('pad nets changed:', changed)
