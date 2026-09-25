#!/bin/sh
# polish.sh dir/mz : drop what DRC flags (dangling, hole/clearance), re-run the grid router, pour, DRC
set -e
M=$1; cd /home/filip/tmp/v2d
T=/media/nas/filip/ncdata/filip/files/Electronics/loon-projects/Radio_Kiosk_v2c/tools
IMG=ghcr.io/kicad/kicad:10.0
KM="docker run --rm -v $PWD/$M:/w -w /w -u 1000:1000 -e HOME=/tmp $IMG"
for i in 1; do
  python3 clean.py $M/final.kicad_pcb $M/drc.json $M/p.kicad_pcb
  cp board.kicad_pro $M/p.kicad_pro
  $KM kicad-cli pcb drc --refill-zones --save-board --format json --severity-all -o drcP.json p.kicad_pcb | tail -1
  python3 - $M/p.kicad_pcb <<'P'
import re,sys
s=open(sys.argv[1]).read()
s=re.sub(r'\n\t\(zone\n.*?\n\t\)',lambda m: m.group(0) if '(layer "In1.Cu")' in m.group(0) else '',s,flags=re.S)
open(sys.argv[1].replace('p.kicad_pcb','board.kicad_pcb'),'w').write(s)
P
  docker run --rm -v $PWD/$M:/work -v $T:/t -u 1000:1000 -e HOME=/tmp $IMG python3 /t/padgeo.py
  (cd $M && $HOME/.local/bin/uv run -q --no-project --with numpy python ../../mazefix.py board.kicad_pcb padgeo.json drcP.json fixed.kicad_pcb | grep -v "^routed reroute")
  python3 zones_after.py $M/fixed.kicad_pcb $M/final.kicad_pcb 85 120
  cp board.kicad_pro $M/final.kicad_pro
  $KM kicad-cli pcb drc --refill-zones --save-board --format json --severity-all -o drc.json final.kicad_pcb | tail -1
  python3 -c "
import json,collections;d=json.load(open('$M/drc.json'))
print('POLISH $i unconnected',len(d['unconnected_items']),dict(collections.Counter(v['type'] for v in d['violations'])))"
done
