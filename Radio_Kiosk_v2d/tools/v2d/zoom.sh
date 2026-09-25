#!/bin/sh
# zoom.sh board out.png x0 y0 x1 y1 [layers] [px/mm]
B=$1; OUT=$2; X0=$3; Y0=$4; X1=$5; Y1=$6; L=${7:-F.Cu,In2.Cu,B.Cu,F.Silkscreen,Edge.Cuts}; S=${8:-30}
/home/filip/tmp/v2d/plot.sh $B /tmp/zoomfull.png "$L" $S >/dev/null
convert /tmp/zoomfull.png -crop $(python3 -c "print('%dx%d+%d+%d'%(($X1-$X0)*$S,($Y1-$Y0)*$S,$X0*$S,$Y0*$S))") +repage $OUT
echo $OUT
