"""Read-only: every pad (world center, bbox, net, smd?, layer), track, via, hole, edge."""
import pcbnew, json
MM=1e6; b=pcbnew.LoadBoard('/work/board.kicad_pcb'); o={'pads':[],'tracks':[],'vias':[]}
for f in b.GetFootprints():
    for p in f.Pads():
        bb=p.GetBoundingBox(); smd=p.GetAttribute()==pcbnew.PAD_ATTRIB_SMD
        o['pads'].append({'ref':f.GetReference(),'num':p.GetNumber(),'net':p.GetNetname(),'smd':smd,'back':f.IsFlipped(),
          'c':[p.GetPosition().x/MM,p.GetPosition().y/MM],'box':[bb.GetLeft()/MM,bb.GetTop()/MM,bb.GetRight()/MM,bb.GetBottom()/MM],
          'npth':p.GetAttribute()==pcbnew.PAD_ATTRIB_NPTH})
for t in b.GetTracks():
    if t.Type()==pcbnew.PCB_VIA_T: o['vias'].append({'c':[t.GetPosition().x/MM,t.GetPosition().y/MM],'r':t.GetWidth(pcbnew.F_Cu)/MM/2,'net':t.GetNetname()})
    else: o['tracks'].append({'a':[t.GetStart().x/MM,t.GetStart().y/MM],'b':[t.GetEnd().x/MM,t.GetEnd().y/MM],'w':t.GetWidth()/MM,'net':t.GetNetname(),'layer':t.GetLayerName()})
e=b.GetBoardEdgesBoundingBox(); o['edge']=[e.GetLeft()/MM,e.GetTop()/MM,e.GetRight()/MM,e.GetBottom()/MM]
json.dump(o,open('/work/padgeo.json','w')); print(len(o['pads']),'pads')
