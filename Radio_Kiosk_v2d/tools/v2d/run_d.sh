#!/bin/sh
# v2d: placement json -> placed board with labels -> Freerouting on 4 layers -> pours + DRC
# Usage: run_d.sh placement.json H outdir
set -e
PJ=$1; H=$2; O=$3
cd /home/filip/tmp/v2d
T=/media/nas/filip/ncdata/filip/files/Electronics/loon-projects/Radio_Kiosk_v2c/tools
IMG=ghcr.io/kicad/kicad:10.0
if [ -z "$KEEPLAB" ]; then rm -rf $O; fi
rm -rf $O/rt && mkdir -p $O/lab $O/rt && chmod 777 $O/rt
echo "[$(date +%H:%M)] apply + labels"
if [ -z "$KEEPLAB" ]; then
python3 apply.py b$H.kicad_pcb $PJ $O/placed.kicad_pcb
cp $O/placed.kicad_pcb $O/lab/board.kicad_pcb
docker run --rm -v $PWD/$O/lab:/work -v $T:/t -u 1000:1000 -e HOME=/tmp $IMG python3 /t/dump.py
(cd $O/lab && python3 $T/labels.py | tail -1)
cp $O/lab/board.kicad_pcb $O/labeled.kicad_pcb
else cp $O/labeled.kicad_pcb $O/lab/board.kicad_pcb; fi
docker run --rm -v $PWD/$O/lab:/work -v $T:/t -u 1000:1000 -e HOME=/tmp $IMG python3 /t/padgeo.py
(cd $O/lab && python3 $T/netvias.py GND)
python3 prep.py $O/lab/board.kicad_pcb $O/rt/A.kicad_pcb
python3 enlarge.py $O/rt/A.kicad_pcb $O/rt/Adsn.kicad_pcb
cp board.kicad_pro $O/rt/Adsn.kicad_pro
cp board.kicad_pro $O/rt/A.kicad_pro
cp rtk/dsn.py rtk/imp.py $O/rt/
KI="docker run --rm -v $PWD/$O/rt:/w -w /w -u 1000:1000 -e HOME=/tmp $IMG"
FR="docker run --rm --user root -v $PWD/$O/rt:/work ghcr.io/freerouting/freerouting:latest java -jar /app/freerouting-executable.jar --user_data_path=/work/.fr --gui-enabled=false -mt ${MT:-6}"
echo "[$(date +%H:%M)] route"
$KI python3 dsn.py Adsn.kicad_pcb A.dsn
python3 dsnfix.py $O/rt/A.dsn
python3 strip.py $O/rt/A.dsn
$FR -de /work/A.dsn -do /work/A.ses -mp ${MP:-20} > $O/rt/frA.log 2>&1 || true
$KI python3 imp.py A.kicad_pcb A.ses A_out.kicad_pcb
docker run --rm --user root -v $PWD/$O/rt:/work --entrypoint sh ghcr.io/freerouting/freerouting:latest -c "rm -rf /work/.fr; chown -R 1000:1000 /work"
python3 zones_after.py $O/rt/A_out.kicad_pcb $O/rt/routed.kicad_pcb 85 $H
cp board.kicad_pro $O/rt/routed.kicad_pro
$KI kicad-cli pcb drc --refill-zones --save-board --format json --severity-all -o drc.json routed.kicad_pcb | tail -2
grep -o "unrouted.\{0,80\}" $O/rt/frA.log | tail -1
echo "[$(date +%H:%M)] done"
