#!/bin/sh
# pass B: drop what DRC flagged in pass A, lock the rest, neck the power
# classes, route what is left, then pours + DRC.   Usage: passB.sh dir H
set -e
O=$1; H=$2
cd /home/filip/tmp/v2d
IMG=ghcr.io/kicad/kicad:10.0
KI="docker run --rm -v $PWD/$O/rt:/w -w /w -u 1000:1000 -e HOME=/tmp $IMG"
FR="docker run --rm --user root -v $PWD/$O/rt:/work ghcr.io/freerouting/freerouting:latest java -jar /app/freerouting-executable.jar --user_data_path=/work/.fr --gui-enabled=false -mt ${MT:-8}"
python3 clean.py $O/rt/A_out.kicad_pcb $O/rt/drc.json $O/rt/B0.kicad_pcb
python3 prep.py $O/rt/B0.kicad_pcb $O/rt/B.kicad_pcb
python3 enlarge.py $O/rt/B.kicad_pcb $O/rt/Bdsn.kicad_pcb
python3 - $O/rt/Bdsn.kicad_pro <<'P'
import json,sys
p=json.load(open('/home/filip/tmp/v2d/board.kicad_pro'))
for c in p['net_settings']['classes']:
  if c['name']=='Heavy': c['track_width']=1.0
  if c['name']=='Wide': c['track_width']=0.8
  if c['name']=='Power': c['track_width']=0.5
json.dump(p,open(sys.argv[1],'w'),indent=2)
P
cp board.kicad_pro $O/rt/B.kicad_pro
$KI python3 dsn.py Bdsn.kicad_pcb B.dsn
python3 dsnfix.py $O/rt/B.dsn
python3 strip.py $O/rt/B.dsn
$FR -de /work/B.dsn -do /work/B.ses -mp ${MP:-15} > $O/rt/frB.log 2>&1 || true
$KI python3 imp.py B.kicad_pcb B.ses B_out.kicad_pcb
docker run --rm --user root -v $PWD/$O/rt:/work --entrypoint sh ghcr.io/freerouting/freerouting:latest -c "rm -rf /work/.fr; chown -R 1000:1000 /work"
python3 zones_after.py $O/rt/B_out.kicad_pcb $O/rt/routedB.kicad_pcb 85 $H
cp board.kicad_pro $O/rt/routedB.kicad_pro
$KI kicad-cli pcb drc --refill-zones --save-board --format json --severity-all -o drcB.json routedB.kicad_pcb | tail -1
grep "score" $O/rt/frB.log | tail -1 | cut -c60-200
