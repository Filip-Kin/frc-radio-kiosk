#!/bin/sh
# placement -> labels, GND vias, pass A, B, C, maze fix, pours, DRC.  Usage: full.sh placement.json dir
set -e
PJ=$1; O=$2; H=120
cd /home/filip/tmp/v2d
T=/media/nas/filip/ncdata/filip/files/Electronics/loon-projects/Radio_Kiosk_v2c/tools
IMG=ghcr.io/kicad/kicad:10.0
MP=${MPA:-25} ./run_d.sh $PJ $H $O
MP=12 ./passB.sh $O $H
MP=10 ./passC.sh $O $H
rm -rf $O/mz && mkdir $O/mz && chmod 777 $O/mz && cp $O/rt/C_out.kicad_pcb $O/mz/board.kicad_pcb
docker run --rm -v $PWD/$O/mz:/work -v $T:/t -u 1000:1000 -e HOME=/tmp $IMG python3 /t/padgeo.py
(cd $O/mz && $HOME/.local/bin/uv run -q --no-project --with numpy python ../../mazefix.py board.kicad_pcb padgeo.json ../rt/drcC.json fixed.kicad_pcb)
python3 zones_after.py $O/mz/fixed.kicad_pcb $O/mz/final.kicad_pcb 85 $H
cp board.kicad_pro $O/mz/final.kicad_pro
docker run --rm -v $PWD/$O/mz:/w -w /w -u 1000:1000 -e HOME=/tmp $IMG kicad-cli pcb drc --refill-zones --save-board --format json --severity-all -o drc.json final.kicad_pcb | tail -1
python3 -c "
import json,collections;d=json.load(open('$O/mz/drc.json'))
print('FINAL unconnected',len(d['unconnected_items']),dict(collections.Counter(v['type'] for v in d['violations'])))"
