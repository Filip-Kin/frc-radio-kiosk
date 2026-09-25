"""Greedy placer: for each named part find the free spot nearest its target. Usage: kiosk-place.py geo.json REF:w,h,tx,ty ... (w,h = part bbox at the wanted rotation). Prints REF=x,y for kiosk-move.py."""
import json, sys, math
g=json.load(open(sys.argv[1])); want=[]
for a in sys.argv[2:]:
    ref,v=a.split(':'); w,h,tx,ty=map(float,v.split(',')); want.append((ref,w,h,tx,ty))
skip={r for r,_,_,_,_ in want}
boxes=[f['box'] for f in g['fp'] if not f['back'] and f['ref'] not in skip]
L,T,R,B=g['edge']; M=0.35
def seg_dist(px,py,x1,y1,x2,y2):
    dx,dy=x2-x1,y2-y1; t=0 if dx==dy==0 else max(0,min(1,((px-x1)*dx+(py-y1)*dy)/(dx*dx+dy*dy)))
    return math.hypot(px-(x1+t*dx),py-(y1+t*dy))
def rect_seg_clear(l,t,r,b,seg):
    x1,y1,x2,y2,w=seg
    # sample the segment
    n=max(2,int(math.hypot(x2-x1,y2-y1)/0.5)+1)
    for i in range(n+1):
        x=x1+(x2-x1)*i/n; y=y1+(y2-y1)*i/n
        if l-w/2-0.25<x<r+w/2+0.25 and t-w/2-0.25<y<b+w/2+0.25: return False
    return True
def free(l,t,r,b):
    if l<L+1 or t<T+1 or r>R-1 or b>B-1: return False
    for bl,bt,br,bb in boxes:
        if l-M<br and r+M>bl and t-M<bb and b+M>bt: return False
    for x,y,rad in g['holes']+g['vias']:
        if l-rad-0.3<x<r+rad+0.3 and t-rad-0.3<y<b+rad+0.3: return False
    for s in g['tracks']:
        if not rect_seg_clear(l,t,r,b,s): return False
    return True
for ref,w,h,tx,ty in sorted(want,key=lambda k:-k[1]*k[2]):
    best=None
    r=0.0
    while r<60 and best is None:
        cands=[]
        steps=max(8,int(2*math.pi*r/0.5)) if r>0 else 1
        for i in range(steps):
            a=2*math.pi*i/steps; x=tx+r*math.cos(a); y=ty+r*math.sin(a)
            x=round(x*2)/2; y=round(y*2)/2
            if free(x-w/2,y-h/2,x+w/2,y+h/2): cands.append((math.hypot(x-tx,y-ty),x,y))
        if cands: best=min(cands)
        r+=0.5
    if best is None: print(f'# {ref}: no spot'); continue
    _,x,y=best; boxes.append([x-w/2,y-h/2,x+w/2,y+h/2]); print(f'{ref}={x},{y}  # {w}x{h} target {tx},{ty} dist {best[0]:.1f}')
