#!/bin/sh
# v2d: routed board + placement -> loon project Radio_Kiosk_v2d
# Usage: finish.sh routed.kicad_pcb placement.json
set -e
R=$(readlink -f $1); PJ=$(readlink -f $2)
V=/home/filip/tmp/v2d
LP=/media/nas/filip/ncdata/filip/files/Electronics/loon-projects
C=$LP/Radio_Kiosk_v2c; D=$LP/Radio_Kiosk_v2d
LOON=/media/nas/filip/ncdata/filip/files/Projects/loon
mkdir -p $D
cp $R $D/board.kicad_pcb
cp $V/board.kicad_pro $D/board.kicad_pro
python3 -c "import json;json.dump(json.load(open('$PJ'))['pins'],open('$D/mcu-pins.json','w'),indent=1,sort_keys=True)"
# schematic: the same generator as v2c, with this board's pin map
(cd $LOON && LOON_FS_DIR=$LP KIOSK_MCU_PINS=$D/mcu-pins.json bun run scripts/build-radio-kiosk.ts Radio_Kiosk_v2d | tail -1)
# firmware: v2c's, pin constants from the map
rm -rf $D/firmware && mkdir -p $D/firmware && cp -r $C/firmware/src $C/firmware/platformio.ini $C/firmware/README.md $D/firmware/
python3 $V/fwpins.py $D/mcu-pins.json $D/firmware/src/main.cpp
# tools: v2c's board tools plus the v2d pipeline
rm -rf $D/tools && cp -r $C/tools $D/tools && mkdir -p $D/tools/v2d
cp $V/make_base.py $V/setup_d.py $V/place_d.py $V/place2d.py $V/apply.py $V/extract.py $V/prep.py $V/dsnfix.py $V/zones_after.py $V/run_d.sh $V/fwpins.py $V/plot.sh $V/zoom.sh $V/finish.sh $V/full.sh $V/passB.sh $V/passC.sh $V/mazefix.py $V/clean.py $V/enlarge.py $V/strip.py $V/rank.py $V/NOTES.md $V/full2.sh $V/strip_keep.py $V/polish.sh $V/polish1.sh $V/final_clean.py $V/tidy.py $V/riparea.py $V/ripnet.py $V/netvias_d.py $V/macro_solve_d.py $V/Y101/placement_final.json $V/keepout.json $V/ripbox.py $V/macros.json $V/macfinal.json $V/capassoc.json $V/anchors.json $V/blocks.json $D/tools/v2d/
[ -d $D/lcsc.3dshapes ] || cp -r $C/lcsc.3dshapes $D/
[ -f $D/board.loon.json ] || cp $C/board.loon.json $D/board.loon.json
echo "project files in $D"
