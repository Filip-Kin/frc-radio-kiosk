#!/bin/sh
# power first: labels + GND vias (run_d.sh stages), then Freerouting on the power
# classes alone (class width, then necked), then every other net with power
# locked, then the grid router for the rest.  Usage: full2.sh placement.json dir
set -e
PJ=$1; O=$2; H=120
cd /home/filip/tmp/v2d
T=/media/nas/filip/ncdata/filip/files/Electronics/loon-projects/Radio_Kiosk_v2c/tools
IMG=ghcr.io/kicad/kicad:10.0
KI="docker run --rm -v $PWD/$O/rt:/w -w /w -u 1000:1000 -e HOME=/tmp $IMG"
FR="docker run --rm --user root -v $PWD/$O/rt:/work ghcr.io/freerouting/freerouting:latest java -jar /app/freerouting-executable.jar --user_data_path=/work/.fr --gui-enabled=false -mt ${MT:-8}"
mkdir -p $O/lab
if [ ! -f $O/labeled.kicad_pcb ]; then
  python3 apply.py b$H.kicad_pcb $PJ $O/placed.kicad_pcb
  cp $O/placed.kicad_pcb $O/lab/board.kicad_pcb
  docker run --rm -v $PWD/$O/lab:/work -v $T:/t -u 1000:1000 -e HOME=/tmp $IMG python3 /t/dump.py
  (cd $O/lab && python3 $T/labels.py | tail -1)
  cp $O/lab/board.kicad_pcb $O/labeled.kicad_pcb
fi
cp $O/labeled.kicad_pcb $O/lab/board.kicad_pcb
docker run --rm -v $PWD/$O/lab:/work -v $T:/t -u 1000:1000 -e HOME=/tmp $IMG python3 /t/padgeo.py
(cd $O/lab && python3 /home/filip/tmp/v2d/netvias_d.py GND)
rm -rf $O/rt && mkdir -p $O/rt && chmod 777 $O/rt && cp rtk/dsn.py rtk/imp.py $O/rt/
stage() {  # stage name input.kicad_pcb classes widthscale
  N=$1; IN=$2; KEEP=$3
  python3 prep.py $IN $O/rt/$N.kicad_pcb
  python3 enlarge.py $O/rt/$N.kicad_pcb $O/rt/${N}dsn.kicad_pcb
  python3 - $O/rt/${N}dsn.kicad_pro $4 <<'P'
import json,sys
p=json.load(open('/home/filip/tmp/v2d/board.kicad_pro'))
if sys.argv[2]=='neck':
  for c in p['net_settings']['classes']:
    if c['name']=='Heavy': c['track_width']=1.0
    if c['name']=='Wide': c['track_width']=0.8
    if c['name']=='Power': c['track_width']=0.5
json.dump(p,open(sys.argv[1],'w'),indent=2)
P
  cp board.kicad_pro $O/rt/$N.kicad_pro
  $KI python3 dsn.py ${N}dsn.kicad_pcb $N.dsn
  python3 dsnfix.py $O/rt/$N.dsn
  python3 strip_keep.py $O/rt/$N.dsn $KEEP
  echo "[$(date +%H:%M)] stage $N"
  $FR -de /work/$N.dsn -do /work/$N.ses -mp ${MP:-20} > $O/rt/fr$N.log 2>&1 || true
  grep "score" $O/rt/fr$N.log | tail -1 | sed 's/.*final score: [0-9.]* (\([0-9]* unrouted\).*/\1/'
  $KI python3 imp.py $N.kicad_pcb $N.ses ${N}_out.kicad_pcb
  docker run --rm --user root -v $PWD/$O/rt:/work --entrypoint sh ghcr.io/freerouting/freerouting:latest -c "rm -rf /work/.fr; chown -R 1000:1000 /work"
}
MP=20 stage P $O/lab/board.kicad_pcb Heavy,Wide,Power full
MP=10 stage Q $O/rt/P_out.kicad_pcb Heavy,Wide,Power neck
MP=${MPS:-25} stage S $O/rt/Q_out.kicad_pcb Default,Heavy,Wide,Power,Ethernet neck
rm -rf $O/mz && mkdir $O/mz && chmod 777 $O/mz && cp $O/rt/S_out.kicad_pcb $O/mz/board.kicad_pcb
python3 zones_after.py $O/rt/S_out.kicad_pcb $O/mz/s.kicad_pcb 85 $H && cp board.kicad_pro $O/mz/s.kicad_pro
docker run --rm -v $PWD/$O/mz:/w -w /w -u 1000:1000 -e HOME=/tmp $IMG kicad-cli pcb drc --refill-zones --format json --severity-all -o drcS.json s.kicad_pcb | tail -1
docker run --rm -v $PWD/$O/mz:/work -v $T:/t -u 1000:1000 -e HOME=/tmp $IMG python3 /t/padgeo.py
(cd $O/mz && $HOME/.local/bin/uv run -q --no-project --with numpy python ../../mazefix.py board.kicad_pcb padgeo.json drcS.json fixed.kicad_pcb)
python3 zones_after.py $O/mz/fixed.kicad_pcb $O/mz/final.kicad_pcb 85 $H
cp board.kicad_pro $O/mz/final.kicad_pro
docker run --rm -v $PWD/$O/mz:/w -w /w -u 1000:1000 -e HOME=/tmp $IMG kicad-cli pcb drc --refill-zones --save-board --format json --severity-all -o drc.json final.kicad_pcb | tail -1
python3 -c "
import json,collections;d=json.load(open('$O/mz/drc.json'))
print('FINAL unconnected',len(d['unconnected_items']),dict(collections.Counter(v['type'] for v in d['violations'])))"
