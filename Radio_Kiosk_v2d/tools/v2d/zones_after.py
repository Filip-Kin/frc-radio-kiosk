"""Add In2, F.Cu and B.Cu GND pours (In1 is already there)."""
import re,sys,uuid
s=open(sys.argv[1]).read(); W,H=float(sys.argv[3]),float(sys.argv[4])
def fmt(v): return ("%.4f"%v).rstrip("0").rstrip(".")
def zone(layer):
  return f'''
\t(zone
\t\t(net "GND")
\t\t(layer "{layer}")
\t\t(uuid "{uuid.uuid4()}")
\t\t(hatch edge 0.5)
\t\t(connect_pads yes
\t\t\t(clearance 0.2)
\t\t)
\t\t(min_thickness 0.2)
\t\t(fill yes
\t\t\t(thermal_gap 0.5)
\t\t\t(thermal_bridge_width 0.5)
\t\t\t(island_removal_mode 0)
\t\t)
\t\t(polygon
\t\t\t(pts
\t\t\t\t(xy 0 0) (xy {fmt(W)} 0) (xy {fmt(W)} {fmt(H)}) (xy 0 {fmt(H)})
\t\t\t)
\t\t)
\t)'''
s=s.replace('\n\t\t(locked yes)','')
t=s.rindex('\n)'); s=s[:t]+zone('In2.Cu')+zone('F.Cu')+zone('B.Cu')+s[t:]
open(sys.argv[2],'w').write(s)
