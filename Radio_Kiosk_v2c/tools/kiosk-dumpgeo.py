"""Dump front-side obstacles from board.kicad_pcb to geo.json: footprint bboxes, through-holes, F.Cu tracks, vias, edge."""
import pcbnew, json
MM=1e6
b=pcbnew.LoadBoard('/work/board.kicad_pcb')
out={'fp':[], 'holes':[], 'tracks':[], 'vias':[]}
for f in b.GetFootprints():
    bb=f.GetBoundingBox(False,False)
    out['fp'].append({'ref':f.GetReference(),'back':f.IsFlipped(),'box':[bb.GetLeft()/MM,bb.GetTop()/MM,bb.GetRight()/MM,bb.GetBottom()/MM]})
    for p in f.Pads():
        if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            out['holes'].append([p.GetPosition().x/MM,p.GetPosition().y/MM,max(p.GetSize().x,p.GetSize().y)/MM/2])
for t in b.GetTracks():
    if t.Type()==pcbnew.PCB_VIA_T: out['vias'].append([t.GetPosition().x/MM,t.GetPosition().y/MM,0.5])
    elif t.GetLayerName()=='F.Cu' and not (t.GetNetname()=='GND' and t.GetWidth()<=int(0.5*MM)): out['tracks'].append([t.GetStart().x/MM,t.GetStart().y/MM,t.GetEnd().x/MM,t.GetEnd().y/MM,t.GetWidth()/MM])
e=b.GetBoardEdgesBoundingBox(); out['edge']=[e.GetLeft()/MM,e.GetTop()/MM,e.GetRight()/MM,e.GetBottom()/MM]
json.dump(out,open('/work/geo.json','w'))
print('fp',len(out['fp']),'holes',len(out['holes']),'tracks',len(out['tracks']),'vias',len(out['vias']))
