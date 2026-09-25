# v2c placement and routing (2026-09-24/25)

Placement is `place_m.py`: simulated annealing over bodies (single parts or
rigid power-stage macros from `macfinal.json`), pin-level wirelength with the
switch nodes weighted, block regions (`setup5.py` REG), decoupling caps tied to
their IC (`capassoc.json`), TVS diodes at their connector, THT parts off the
back battery holders, and the MCU GPIO map as a search variable (ADC/timer
constraints in `setup5.py` ALLOW). Chosen result: `ps_93.json`.
`apply.py` writes it into the board; `../labels.py` places silk.

Routing: `route_all.sh` pass A at class widths, then a pass at 0.2 mm signals /
0.5 mm power (0.3 mm at 0.2 clearance has no slack on 0.5 mm pitch, the MCU and
USB-C pins never escape). GND stripped from the DSN (front pour); `gndjump.py`
joins cut-off GND regions through the back; `clean.py` drops dangling leftovers.
