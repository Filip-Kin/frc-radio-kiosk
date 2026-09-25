"""Read-only geometry dump for the label placer (pcbnew load, no writes)."""
import pcbnew, json
MM=1e6; b=pcbnew.LoadBoard('/work/board.kicad_pcb')
def bb(x): return [x.GetLeft()/MM, x.GetTop()/MM, x.GetRight()/MM, x.GetBottom()/MM]
out={'fp':[], 'gr':[], 'holes':[]}
fps=b.GetFootprints()
for f in fps:
    back=f.IsFlipped(); cy=f.GetCourtyard(pcbnew.B_CrtYd if back else pcbnew.F_CrtYd)
    try: cb=bb(cy.BBox()) if cy.OutlineCount() else None
    except Exception: cb=None
    pads=[bb(p.GetBoundingBox()) for p in f.Pads()]
    silk=[]
    for g in f.GraphicalItems():
        ln=g.GetLayerName()
        if ln in ('F.Silkscreen','B.Silkscreen') and g.GetClass()!='PCB_TEXT': silk.append(bb(g.GetBoundingBox()))
    ref=f.Reference()
    out['fp'].append({'ref':f.GetReference(),'back':back,'x':f.GetPosition().x/MM,'y':f.GetPosition().y/MM,'rot':f.GetOrientationDegrees(),
        'crt':cb,'body':bb(f.GetBoundingBox(False,False)),'pads':pads,'silk':silk,'refsize':ref.GetTextHeight()/MM,'refvis':ref.IsVisible()})
    for p in f.Pads():
        if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH,pcbnew.PAD_ATTRIB_NPTH): out['holes'].append(bb(p.GetBoundingBox()))
for d in b.GetDrawings():
    if d.GetLayerName() in ('F.Silkscreen','B.Silkscreen'): out['gr'].append({'layer':d.GetLayerName(),'box':bb(d.GetBoundingBox())})
for t in b.GetTracks():
    if t.Type()==pcbnew.PCB_VIA_T: out['holes'].append(bb(t.GetBoundingBox()))
e=b.GetBoardEdgesBoundingBox(); out['edge']=bb(e)
json.dump(out,open('/work/geo2.json','w')); print('fp',len(out['fp']),'gr',len(out['gr']))
