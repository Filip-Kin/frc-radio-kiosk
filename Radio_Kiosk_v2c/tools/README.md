# Board update tooling

KiCad 10's Python bindings lose their type table after the first track add or
remove, so the pipeline is split: pcbnew for parts and pad nets, plain text for
copper. All run in `ghcr.io/kicad/kicad:10.0` with the project mounted at /work
and loon's LCSC footprints as a `.pretty` at /lcsc.pretty.

1. `kicad-cli sch export netlist --format kicadsexpr --output netlist.net board.kicad_sch`
2. `kiosk-update-pcb.py` (pcbnew): update pads' nets from the netlist, swap
   footprints whose land pattern changed, park new parts right of the board,
   re-net tracks by connectivity, report copper that now spans two nets.
3. `kiosk-layout.py` (pcbnew): placement table for the 2026-09-24 update.
4. `kiosk-copper.py` (text): spine edits, new vias, GND stitching vias under moved parts.
5. `kiosk-dangling.py` (text): drop pad-to-pad stubs DRC lists as dangling.
6. `kiosk-props.py` / `kiosk-padnets.py` / `kiosk-move.py` (text): push Value
   and LCSC fields, pad nets, and positions without touching pcbnew at all.

`jlc-check.ts <MPN or Cxxxx>` prints JLC library hits; `jlc-total.ts` prices the
BOM from the board's LCSC fields at the 5-board tier.
