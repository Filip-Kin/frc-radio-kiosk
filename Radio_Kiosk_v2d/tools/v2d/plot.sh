#!/bin/sh
# KiCad plot of a board to PNG: plot.sh board.kicad_pcb out.png [layers] [scale]
set -e
B=$(readlink -f $1); OUT=$(readlink -f $2); L=${3:-F.Cu,F.Silkscreen,F.Courtyard,Edge.Cuts}; S=${4:-10}
D=$(mktemp -d /tmp/plotXXXX); chmod 777 $D; cp $B $D/b.kicad_pcb
docker run --rm -v $D:/w -w /w -u 1000:1000 -e HOME=/tmp ghcr.io/kicad/kicad:10.0 kicad-cli pcb export svg --mode-single --layers "$L" --page-size-mode 2 --exclude-drawing-sheet -o b.svg b.kicad_pcb >/dev/null
W=$(python3 -c "import re;s=open('$D/b.svg').read();m=re.search(r'width=\"([\d.]+)mm\" height=\"([\d.]+)mm\"',s);print(int(float(m.group(1))*$S),int(float(m.group(2))*$S))")
set -- $W
printf '<html><body style="margin:0;background:#101216"><img src="b.svg" style="width:%spx;height:%spx"></body></html>' $1 $2 > $D/i.html
chromium --headless --no-sandbox --disable-gpu --hide-scrollbars --window-size=$1,$(( $2 + 110 )) --screenshot=$OUT file://$D/i.html 2>/dev/null
convert $OUT -crop ${1}x${2}+0+0 +repage $OUT
rm -rf $D; echo $OUT
