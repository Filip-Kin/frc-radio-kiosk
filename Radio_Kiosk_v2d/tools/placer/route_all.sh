#!/bin/sh
set -e
cd /home/filip/tmp/v2c
T=/media/nas/filip/ncdata/filip/files/Electronics/loon-projects/Radio_Kiosk_v2c/tools
KI="docker run --rm -v $PWD/rt:/w -w /w -u 1000:1000 -e HOME=/tmp ghcr.io/kicad/kicad:10.0"
FR="docker run --rm --user root -v $PWD/rt:/work ghcr.io/freerouting/freerouting:latest java -jar /app/freerouting-executable.jar --user_data_path=/work/.fr --gui-enabled=false -mt 8"
echo "[$(date +%H:%M)] apply + labels"
python3 apply.py v2c-0.kicad_pcb ps_93.json v2c-6.kicad_pcb
rm -rf lab && mkdir lab && cp v2c-6.kicad_pcb lab/board.kicad_pcb
docker run --rm -v $PWD/lab:/work -v $T:/t -u 1000:1000 -e HOME=/tmp ghcr.io/kicad/kicad:10.0 python3 /t/dump.py
(cd lab && python3 $T/labels.py | tail -1)
rm -rf rt && mkdir rt && chmod 777 rt && cp lab/board.kicad_pcb rt/base.kicad_pcb && cp board.kicad_pro rt/A.kicad_pro && cp board.kicad_pro rt/B.kicad_pro && cp rt/dsn.py rt/ 2>/dev/null || true
cat > rt/dsn.py <<'P'
import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]); print('fp',len(b.GetFootprints()),'tracks',len(list(b.Tracks())))
print('dsn',pcbnew.ExportSpecctraDSN(b,sys.argv[2]))
P
cat > rt/imp.py <<'P'
import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]); pcbnew.ImportSpecctraSES(b,sys.argv[2]); pcbnew.SaveBoard(sys.argv[3],b)
print('fp',len(b.GetFootprints()),'tracks',len(list(b.Tracks())))
P
cat > rt/prep.py <<'P'
import re,sys,json
s=open(sys.argv[1]).read()
s=re.sub(r'\n\t\(zone\n.*?\n\t\)',lambda m:m.group(0).replace('(clearance 0.1524)','(clearance 0.25)',1),s,flags=re.S)
s=s.replace('\n\t\t(locked yes)','')
s=re.sub(r'(\n\t\((?:segment|via)\n)',r'\1\t\t(locked yes)\n',s)
open(sys.argv[2],'w').write(s)
P
cat > rt/strip.py <<'P'
import re,sys
t=open(sys.argv[1]).read()
t,k=re.subn(r'\(net\s+"?GND"?\s*\(pins[^()]*(?:\([^()]*\)[^()]*)*\)\s*\)','',t); open(sys.argv[1],'w').write(t); print('GND stripped',k)
P
python3 - <<'P'
import json
p=json.load(open('rt/B.kicad_pro'))
for c in p['net_settings']['classes']:
  if c['name'] in ('Heavy','Wide','Power'): c['track_width']=0.5; c['via_diameter']=0.8; c['via_drill']=0.4
json.dump(p,open('rt/B.kicad_pro','w'),indent=2)
P
echo "[$(date +%H:%M)] pass A (class widths)"
python3 rt/prep.py rt/base.kicad_pcb rt/A.kicad_pcb
$KI python3 dsn.py A.kicad_pcb A.dsn
python3 rt/strip.py rt/A.dsn
$FR -de /work/A.dsn -do /work/A.ses -mp 20 > rt/frA.log 2>&1 || true
$KI python3 imp.py A.kicad_pcb A.ses A_out.kicad_pcb
echo "[$(date +%H:%M)] pass B (0.5 mm necks for what is left)"
python3 rt/prep.py rt/A_out.kicad_pcb rt/B.kicad_pcb
$KI python3 dsn.py B.kicad_pcb B.dsn
python3 rt/strip.py rt/B.dsn
$FR -de /work/B.dsn -do /work/B.ses -mp 20 > rt/frB.log 2>&1 || true
$KI python3 imp.py B.kicad_pcb B.ses B_out.kicad_pcb
docker run --rm --user root -v $PWD/rt:/work --entrypoint sh ghcr.io/freerouting/freerouting:latest -c "rm -rf /work/.fr; chown -R 1000:1000 /work"
python3 -c "
s=open('rt/B_out.kicad_pcb').read().replace('\n\t\t(locked yes)',''); open('rt/routed.kicad_pcb','w').write(s)"
cp board.kicad_pro rt/routed.kicad_pro
$KI kicad-cli pcb drc --refill-zones --save-board --format json --severity-all -o drc.json routed.kicad_pcb | tail -2
echo "[$(date +%H:%M)] done"
