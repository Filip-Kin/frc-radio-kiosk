# Radio Kiosk v2d

4-layer rework of v2c. Same schematic generator, same parts, same port
positions. Built overnight 2026-09-25 while v2c was still in progress in
parallel; v2d does not touch v2c's files.

## Board

- **85 x 120 mm**, 4 layers, 1.6 mm, 1 oz outer. v2c is 95 x 140 (-23 % area), v2b is 84 x 141.
  85 wide is the least that keeps the top-right mounting hole clear of the UART
  header; 115 tall did not legalise with v2c's part spacing, 120 does.
- Stackup: F.Cu parts, power, short signals, GND pour / In1.Cu solid GND
  plane / In2.Cu signals + GND fill / B.Cu power, signals, GND pour.
- Every front SMD ground pad has its own way into In1: a 0.4 mm stub and a
  0.6/0.3 via, or, for a 0.5-0.65 mm pitch pin next to its chip's exposed
  pad, a stub into that pad; fine-pitch vias sit 1 mm or more out so the
  neighbouring pins can leave. GND has no routed traces.
- Power classes (Heavy, Wide, Power) are kept to the outer layers. JLC's
  4-layer inner copper is 0.5 oz by default, and an inner trace carries about
  half the current of an outer one of the same width.
- Default net class is now 0.2 mm / 0.15 mm (v2c: 0.3 / 0.2) so the LQFP-48
  and the USB-C pads can escape. Board minimum clearance is 0.1 mm, for J1's
  own 0.1 mm pad gaps (JLC's 1 oz limit). J1 carries a 0.1 mm footprint
  clearance so DRC checks its pads against that and nothing else.

## Ports (same spots)

Top edge unchanged: J6 laptop RJ45, J3 DC out, J12 USB-C serial, J9 SWD, J11
UART. Right edge keeps its distance from the right edge: J1 USB-C PD in, D30,
J2 DC in (all moved 10 mm left with the edge). Bottom edge keeps its distance
from the bottom: J5 radio RJ45, D31 (moved up with the edge). Mounting holes at
the four corners, 4 mm in. The battery holders stay where they were on the back.

J8 (fan) and J13 (lid LEDs) are inside the box, so the placer moved them.

## Ethernet

The approved pair routing is kept exactly. The pairs sit on B.Cu down the left
edge. The board got shorter, so the long straight runs are shorter by the same
amount on every pair and the pair matching is unchanged. In2 under them is GND.

## Placement

v2c's placer (macro power stages, MCU pin map in the loop, cap-to-IC pull)
plus three changes:
1. a legalizer that finds every legal spot at once (FFT of the part's
   courtyard mask against the occupied raster), biggest parts first, each IC
   followed by its own decoupling caps;
2. swaps of same-footprint parts during refinement;
3. corrected cap-to-IC table (C3/C90/C91 were tied to Q25, a 2N7002 on
   USB_DIS; C1/C2/C6/C7/C12/C143 had no IC).
Courtyard margins are v2c's: 0.8 mm gap between small parts, 1.4 mm ring
round the MCU. The front keep-out over the Ethernet pairs now applies to power
parts and through-hole pins only: In1 and In2 sit between the front and the pairs.

## MCU pin map

Chosen by the placer. `mcu-pins.json` holds it, the schematic is regenerated
from it (`KIOSK_MCU_PINS`), and `firmware/src/main.cpp` pin constants are
rewritten from it. FAN_PWM (PB4) and LAPTOP_ILIM_PWM (PA8) are fixed because
the firmware drives those timers by register.

## Routing

Power first: Freerouting on the Heavy/Wide/Power nets alone at class width,
then again necked (Heavy 1.0, Wide 0.8, Power 0.5), then every other net with
the power copper locked, then a grid A* router with rip-up
(`tools/v2d/mazefix.py`) for the last few, then cleanup (dangling copper,
duplicate segments, grid staircases straightened within 0.02 mm).
The LM3150 block was re-solved with a 1.2 mm ring round U4 (v2c's packing
left U4's HG/LG/SW pins no way out).

Result (KiCad 10 DRC, zones refilled), 2026-09-25 midday:
- **0 unconnected**, 0 clearance, short, hole or dangling errors. loon's
  layout view also shows 0.
- Left as in v2c: 14 silk_edge_clearance (connector silk at the board edge),
  199 lib_footprint_issues (LCSC land patterns differ from KiCad's library),
  7 text_height (labels shrunk to 0.7 mm to fit).
- Schematic parity: no net differences. `tools/verify.py`: 239 parts, none
  missing. Firmware builds, 71 kB of 128 kB.
- Inductors (L3, L4, L5, L20): no foreign copper under them on F.Cu or In2,
  and no signal on any layer. Power nets may pass on B.Cu, under the In1
  plane; one does: FAN_N under L20.
- Pin swap to close the last net: USB_ISENSE moved PA0 -> PA3 (pin 13, bottom
  row, free exit); PORT_SW moved PA3 -> PC15 (pin 4, spare; PC15 is a low-drive
  pin, fine for a slow gate enable). PA0 is now unused. Schematic and firmware
  regenerated from `mcu-pins.json`.
- Fab files in `fab/`: gerbers + drill zip (4 layers), JLC BOM and CPL.

Review before ordering (machine routing):
- Power nets necked below class width in places: +12V 79 mm, VIN_USB 69 mm,
  PORT_P 50 mm, TEST_NODE 32 mm, PACK_F 27 mm (full width elsewhere). Most
  are short necks at pins; check the VIN_USB run from J1 through R93.
- TEST_NODE (self-test load, 1 A pulses) runs 45 mm on In2 at 0.8 mm.
- Long signal detours from the last-mile router: LAPTOP_EN ~40 mm,
  U4_EN ~35 mm, USB_VBUS sense 32 mm.
- USB D+/D- were re-routed separately near the MCU, so the pair is not
  length matched there (full-speed USB tolerates it).

## Open

1. JLC quote: 4 layers, 1.6 mm, 1 oz outer / 0.5 oz inner. Check part
   rotations in JLC's CPL preview (KiCad and JLC disagree on some packages).

## Rebuild

`tools/v2d/` (work dir was `~/tmp/v2d`): `make_base.py` (outline, layers,
ports), `place2d.py` (placer; seed 101 is this board), `full2.sh` (labels, GND
vias, power-first routing, pours, DRC), `polish.sh` / `mazefix.py` /
`final_clean.py` / `tidy.py` (finishing), `finish.sh` (copies into this
folder, regenerates schematic and firmware pin map).
