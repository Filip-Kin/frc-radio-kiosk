#!/bin/sh
# pass C: what necked pass B left, on any layer at 0.4 mm (power) / 0.2 mm; locks all earlier copper
# Usage: passC.sh dir H
set -e
O=$1; H=$2
cd /home/filip/tmp/v2d
IMG=ghcr.io/kicad/kicad:10.0
KI="docker run --rm -v $PWD/$O/rt:/w -w /w -u 1000:1000 -e HOME=/tmp $IMG"
FR="docker run --rm --user root -v $PWD/$O/rt:/work ghcr.io/freerouting/freerouting:latest java -jar /app/freerouting-executable.jar --user_data_path=/work/.fr --gui-enabled=false -mt ${MT:-8}"
python3 clean.py $O/rt/B_out.kicad_pcb $O/rt/drcB.json $O/rt/C0.kicad_pcb
python3 prep.py $O/rt/C0.kicad_pcb $O/rt/C.kicad_pcb
python3 enlarge.py $O/rt/C.kicad_pcb $O/rt/Cdsn.kicad_pcb
python3 - $O/rt/Cdsn.kicad_pro <<'P'
import json,sys
p=json.load(open('/home/filip/tmp/v2d/board.kicad_pro'))
for c in p['net_settings']['classes']:
  if c['name'] in ('Heavy','Wide','Power'): c['track_width']=0.4; c['via_diameter']=0.8; c['via_drill']=0.4
json.dump(p,open(sys.argv[1],'w'),indent=2)
P
cp board.kicad_pro $O/rt/C.kicad_pro
$KI python3 dsn.py Cdsn.kicad_pcb C.dsn
python3 strip.py $O/rt/C.dsn
$FR -de /work/C.dsn -do /work/C.ses -mp ${MP:-15} > $O/rt/frC.log 2>&1 || true
$KI python3 imp.py C.kicad_pcb C.ses C_out.kicad_pcb
docker run --rm --user root -v $PWD/$O/rt:/work --entrypoint sh ghcr.io/freerouting/freerouting:latest -c "rm -rf /work/.fr; chown -R 1000:1000 /work"
python3 zones_after.py $O/rt/C_out.kicad_pcb $O/rt/routedC.kicad_pcb 85 $H
cp board.kicad_pro $O/rt/routedC.kicad_pro
$KI kicad-cli pcb drc --refill-zones --save-board --format json --severity-all -o drcC.json routedC.kicad_pcb | tail -1
grep "score" $O/rt/frC.log | tail -1 | cut -c60-200
