# Radio kiosk v2 schematic audit, 2026-09-24

Six datasheet-checked section reviews. Full detail per section below this summary.


---

# Bucks and logic rails review (U3, U4, U5, U6/Q6, U51, U30, R112/C134/C135)

Sources: TI LMR33630 SNVSAN3F (ti.com), TI LM74700-Q1 SNOSD17G, Diodes AP2112 DS39724, Bourns SRP7028A (JLC file), VBsemi SI4470EY-T1-GE3-VB (JLC file), TI SN74AHCT1G125, ST STM32F072 datasheet. Copies in review/ds/.

## Findings

- BLOCKER | U5.2/U5.3 (VIN pins), C50, C51 | The 5 V buck is fed from `VIN`, not `+12V`. On input loss the pack holds +12V, but VIN decays, U5 stops, +5V and +3V3 die. U10 (the comparator that holds the pack on) is powered from +3V3, so BK_ON falls, Q9 turns off, Q8 opens and the pack disconnects within milliseconds. The MCU also resets. Battery backup cannot work. Spec power tree and the sheet note both say 5 V/3.3 V hang off the backed-up rail. | Fix: in build-radio-kiosk.ts line 687 `buck(5, 5, "24.9k", "25V", "+12V", "+5V", 80, 350)`. EN stays tied to its own input, now +12V. U5 at VIN 10-13 V to 5 V is inside the datasheet range (min on-time and dropout both fine).
- BLOCKER (outside my section, for the battery reviewer) | Q8 AOD4185: D=+12V, S=PACK_F | A P-FET body diode runs drain to source, so here it conducts from +12V into the pack. The comment "Body diode points pack -> rail" is backwards. With Q8 off and the buck at 12.0 V, the rail charges the CR123A primary cells through the diode (and F1) once the pack falls below about 11.3 V. That is a fire hazard. | Fix: two P-FETs back to back (sources joined, gates joined, drains to PACK_F and +12V), or an LM74700 + N-FET ideal diode in the pack path the same way U6 does for the buck.
- WRONG | L4 (U4, 15.6 V) | 10 uH is below the datasheet minimum. Eq. 5 (§9.2.2.4, p.22) gives LMIN >= 0.28 x VOUT / fSW = 0.28 x 15.6 / 400 kHz = 10.9 uH. With the part's ±20 % tolerance, and a further 20 % drop at Isat, the worst case is 8 uH. At D = 0.60-0.78 (VIN 20-26 V) this risks sub-harmonic oscillation in the peak-current loop. | Fix: 15 uH with Isat >= ISC max 5.05 A (Table 7.5). Example: MDA1040-150M, LCSC C2847554 (15 uH, 41 mOhm, 6.25 A rms, 7 A sat, 11x10 mm, 425 in stock). This needs a footprint change. Do not use SRP7028A-150M: its Isat is 4.0 A, below ILIMIT max 4.1 A and ISC.
- RISK | L3 (U3, 12 V) | Table 9-2 (p.20) specifies 15 uH for 12 V at 400 kHz. Eq. 5 gives LMIN = 8.4 uH, and 10 uH at -20 % is 8.0 uH, below that. Ripple at 24 V in is about 1.5 A p-p (50 %), so the peak is about 3.6 A at a 2.8 A load, close to ISC min 3.85 A. | Fix: the same 15 uH part as L4 (MDA1040-150M, C2847554). This brings ripple to about 1.0 A.
- RISK | U3 load vs current limit | +12V carries the 54 V boost. 802.3at allows 30 W at the PSE; at an assumed 90 % boost efficiency that is about 2.8 A at 12 V, plus the fan. The datasheet's max output (Eq. 1, p.15) is (ILIMIT + ISC)/2, which is 3.375 A using the minimums (2.9 A, 3.85 A). L3 Irms is 3.5 A (Bourns table). The margin is under 20 %. | Fix: the 15 uH inductor above. Measure the 12 V input current at full PSE load on the prototype. If it goes over 3 A, the part must change (the pin-compatible LMR33640 is 4 A).
- RISK | U3, U4 thermal (HSOIC-8, 2-layer board) | These are estimates, not measurements. Conduction loss at 2.8-3 A with the hot RDS(on) max values (160/110 mOhm, Table 7.5) is about 1.1-1.4 W per part, before switching loss. Figure 9-3 shows RθJA of 22-44 °C/W on a *4-layer* board depending on copper. On this 2-layer board inside an enclosure, with three bucks, the boost and the eFuse close together, Tj may approach the 125 °C limit (§9.2.2.11). | Fix: a solid GND pour top and bottom under each EP, >= 6 thermal vias per EP (already planned), and spread U3/U4 apart. Measure the case temperature at full load on the prototype.
- RISK | C97, C98 (2 x 470 uF) on +12V behind U6 | The total output capacitance U3 sees at start-up is about 88 uF + 940 uF + C22 + C61, over 1000 uF. §9.2.2.5 (p.23) limits Cout to 10x the design value (880 uF) or 1000 uF, whichever is smaller. It warns that start-up and loop stability then need study. Charging 1.03 mF in tSS min 2.9 ms (Table 7.5) takes about 4.2 A, which is above Iout max, so start-up runs in current limit. It is probably fine only because the boost, eFuse and fan are off at reset. | Fix: fit one 470 uF (drop C97) if the dropout hold-up allows it. Otherwise, on the prototype, check start-up with the load connected and do a 0-2 A load-step test.
- RISK | VIN net (C90, C91, C30, C40, C50: ceramics only) | The bricks are cable-fed and VIN has no damping capacitor. The Power Supply Recommendations section (p.32) warns that cable inductance plus ceramic input caps rings on hot-plug and recommends a 20-100 uF aluminium capacitor. The only clamp is the SMAJ28A (Vc 45.4 V), and LMR33630 VIN abs max is 38 V (Table 7.1). | Fix: add one 47-100 uF / 50 V aluminium electrolytic on VIN next to C90/C91.
- RISK | U4.3 EN = LAPTOP_EN, driven by U40.20 | Table 7.1 note 2: EN must not exceed VIN + 0.3 V. After the U5 fix the MCU stays up on battery while VIN falls to 0. Firmware only drops LAPTOP_EN on its next loop pass (vinV < 13.5), so for a short time EN is at 3.3 V with VIN at about 0. | Fix: put a 10 k series resistor between U40.20 and the U4.3/R92 node. That limits clamp current to about 0.3 mA, and EN still reaches 3.0 V (>1.26 V VEN-H max).
- RISK (laptop rail, for the CC reviewer) | U7 CATHODE = LAPTOP_OUT has no capacitor | LM74700 Recommended Operating Conditions (Table 6.3) call for >= 0.1 uF on CATHODE. | Fix: add 1 uF / 50 V from LAPTOP_OUT to GND next to U7/Q7.
- NOTE | U4 on the 15.6 V brick | The buck is set to 15.68 V (100k/6.81k), so from a 15.6 V brick it runs in dropout (§8.4.2, fSW folds to about 140 kHz, DMAX 98 %). The series path is Q2 12 mOhm, HS FET 95/160 mOhm, L4 75/85 mOhm, R96 20 mOhm and Q7 12 mOhm. At 3 A the laptop sees about 14.9 V typical and about 14.6 V hot, not the "~15.3 V" in the sheet note. The FB/CC arrangement (D40/R98 into U4_FB) works in dropout and cannot exceed FB abs max 5.5 V (the op-amp is on 3.3 V). No hiccup is possible because the loop holds FB at about 1 V. Fine. | Fix: correct the note only. Confirm the laptop accepts 14.5 V (the item already on the Open list).
- NOTE | C44-C47 22 uF/25 V X7R 1210 at 15.6 V | Voltage rating is fine (62 %). I could not verify the DC-bias loss: the vendor datasheet on JLC (C53084530) is a scanned image with no curve. Table 9-2 has no 15.6 V row. With 4x22 uF rated and loop crossover scaling as 1/(VOUT x COUT), this should be close to the 12 V row. | Fix: none required. Check the load transient on the prototype.
- NOTE | L3/L4/L5 value field "SRP7028A-100M 10u 5A" | The Bourns table gives 10 uH ±20 %, DCR 75/85 mOhm, Irms 3.5 A, Isat 6.0 A. No rating is 5 A. | Fix: change the value text to "10u 3.5A/6A" (or to the new 15 uH part for L3/L4).
- NOTE | Q6 (and Q1, Q2, Q7, Q11, Q13) C7568913 | This is SI4470EY-T1-GE3-VB, a VBsemi second-source, not Vishay. Pinout S1-3 G4 D5-8, 60 V, ±20 V VGS, 12 mOhm at 10 V all suit the LM74700 (GATE-ANODE <= 15 V). Stock is 172; 6 per board x 15 = 90. | Fix: none. Order before stock drops.
- NOTE | Unassigned passives in this section (LCSC "-") | These are C31/C41/C51, C32/C42/C52, C33/C43/C53, C6, R30-R51, C141, C142, R112, C134, C135. The minimum ratings from the datasheets are: CHF 220 nF 50 V X7R (§9.2.2.6); CVCC 1 uF >= 16 V X7R (§9.2.2.8); CBOOT 100 nF >= 10 V X7R (§9.2.2.7); C6 VCAP 100 nF >= 25 V (VCAP-ANODE up to 15 V, Table 6.1 abs max); FB resistors 1 %. | Fix: assign LCSC basic parts with these ratings before the JLC order.
- NOTE | R112 10R VDDA filter | The STM32F072 datasheet §3.5.1 requires VDDA >= VDD and that VDDA comes up first. With 10 Ohm and about 1 mA IDDA, VDDA sits about 10 mV below VDD and lags about 10 us at power-up. That is inside the 0.4 V abs max (Table 21), but outside the stated operating condition. | Fix: replace R112 with a ferrite bead (DCR < 0.1 Ohm, e.g. 600R at 100 MHz 0805) or 0R. Keep C134/C135.

## Verified clean

- LMR33630 pin map for DDA HSOIC-8 (Table 6-1, p.5): 1 PGND, 2 VIN, 3 EN, 4 PG, 5 FB, 6 VCC, 7 BOOT, 8 SW, EP = AGND. It matches parts.txt for U3/U4/U5. EP and pin 1 both go to GND. PG open is allowed.
- LMR33630 variant: C841384 = LMR33630ADDAR, "A" = 400 kHz (Device Comparison Table, p.4), which matches the design.
- Feedback (VREF 1.000 V ±1.5 %, RFBT 100k recommended, §9.2.2.3): U3 100k/9.09k = 12.00 V; U4 100k/6.81k = 15.68 V; U5 100k/24.9k = 5.02 V. All three match Table 9-2 or Eq. 3.
- CBOOT 100 nF BOOT-SW, CVCC 1 uF, CIN 10 uF/50 V X7R + 220 nF: all match Table 9-2. EN tied to VIN on U3/U5 is allowed (Table 6-1). Min on-time at 26 V to 5 V is 481 ns, well above the 108 ns max.
- Inductor saturation: SRP7028A-100M Isat 6 A > ISC max 5.05 A. L5 10 uH on 5 V: LMIN 3.5 uH OK, ripple about 33 % at 24 V.
- U6 LM74700 DBV pin map (Table 5-1): 1 VCAP, 2 GND, 3 EN, 4 CATHODE, 5 GATE, 6 ANODE. It matches. EN is tied to ANODE and VCAP cap to ANODE is 100 nF (>= 0.1 uF). Anode has 88 uF (>= 22 nF) and cathode has 940 uF.
- AP2112K-3.3 (C51118 = AP2112K-3.3TRG1) SOT-25 pin map: 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT. It matches. EN is tied to VIN, VIN is 5 V (6 V max), Cin 1 uF and Cout 10 uF ceramic (1 uF min). Dissipation is about 85 mW at 50 mA.
- U30 is not a regulator: C7484 = SN74AHCT1G125DBVR, pin map 1 OE, 2 A, 3 GND, 4 Y, 5 VCC matches, and OE to GND = enabled.
- LCSC codes confirmed: C841384 LMR33630ADDAR, C2687402 SRP7028A-100M, C2941042 LM74700QDBVRQ1, C7568913 SI4470EY-T1-GE3-VB, C51118 AP2112K-3.3TRG1, C7484 SN74AHCT1G125DBVR, C53084452 10 uF 50 V X7R 1210, C53084530 22 uF 25 V X7R 1210, C346948 470 uF 25 V 10x10.
- Footprint: the KiCad EP of 2.29x3.0 mm sits inside both TI DDA exposed-pad ranges (DDA0008J 2.0-2.6 x 2.5-3.1, DDA0008B 2.11-2.71 x 2.8-3.4).

## Could not verify

- DC-bias derating of C53084530 (the JLC datasheet is an image scan).
- Real RθJA and Tj on this board: this needs a measurement on the prototype.
- Which DDA package drawing (J or B) the C841384 reel uses.

---

# Power input and input selection: review

Scope: J1, U50 (CH224A), R120, R121, C140, C111, D1, J2, D2, U1/Q1, U2/Q2, C1, C2, R93, U41, C90, C91, R90/R91, R94/R95.
Datasheets used (in review/ds/): TI LM74700-Q1 SNOSD17G, TI INA180 SBOS741H, TI LMR33630 SNVSAN3F, WCH CH224 V2.0, Littelfuse SMAJ, VBsemi SI4470EY-T1-GE3-VB, CUI PJ-002BH.

No BLOCKER found in this section.

## Findings

- WRONG | U2 ANODE (pin 6) / net VIN_DC | VIN_DC has no capacitance to GND. C2 goes VCAP to ANODE, not to GND, and D2 is the only other part. The LM74700 needs at least 22 nF on ANODE (SNOSD17G sec. 6.3 Recommended Operating Conditions, "External capacitance ANODE 22 nF min"; sec. 10.1.1.2.3 "CIN: minimum 22 nF"). The DC side also hot-plugs a 24-26 V brick into VIN's all-ceramic bank (C90/C91 + C30/C40/C50), which rings. LMR33630 VIN abs max is 38 V (SNVSAN3F sec. 7.1), and D2 only starts at 31.1-34.4 V and clamps at up to 45.4 V. TI tells you to damp this with a 20-100 uF aluminium or tantalum cap (SNVSAN3F sec. 9.2.2.6 Input Capacitor Selection, and sec. 10 Power Supply Recommendations: "20 uF to 100 uF is usually sufficient"). Fix: add a 100 nF/50 V X7R 0805 VIN_DC to GND at U2, plus a 47 uF/63 V electrolytic (the C25 part, LCSC C970680, CP_Elec_8x10.5) VIN_DC to GND next to J2. Putting the electrolytic on VIN_DC rather than VIN keeps it off the USB-C VBUS.
- WRONG | firmware-main.cpp laptopTick() | `dcIn = dcinV > 13.5` skips the USB budget whenever the DC jack reads live. With the Toughbook 15.6 V brick in J2 and a 20 V PD charger in J1, U1 conducts and U2 blocks, so USB carries the whole load, but firmware sets limit = 3 A with no allocation check. That is the shared-charger overload the design exists to prevent. Fix: decide the active source by voltage or current, not by presence. For example `usbActive = usbIn && (usbA > 0.15f || !dcIn || dcinV < vinV - 0.3f)` and apply the budget whenever usbActive.
- RISK | D1 (SMAJ28A) on VIN_USB vs U50 VHV/VBUS and U41 IN+/IN- | SMAJ28A VBR is 31.1-34.4 V and Vc is 45.4 V (Littelfuse SMAJ table, SMAJ28A row). CH224A VHV/VBUS/CC abs max is 32.0 V (CH224 V2.0 sec. 8.1.1). INA180 common-mode abs max is 26 V (SBOS741H sec. 7.1). So the TVS does not start to conduct until both parts are past abs max. VIN_USB only ever carries 20 V PD (21 V at +5 %), so 28 V standoff is more than needed. Fix: D1 becomes SMAJ22A (standoff 22 V, VBR 24.4-26.9 V, Vc 35.5 V), LCSC C148220 (Littelfuse, same family). D2 stays SMAJ28A because the DC jack can see 26 V.
- RISK | U50 pins 2/3 (CFG2/SCL, CFG3/SDA), firmware sclHi()/sdaHi() | With no USB plugged in, the CH224A has no supply. The firmware idles both lines as INPUT_PULLUP (~40k to 3.3 V) into the chip's internal 7-15k pull-ups (CH224 sec. 8.2.1 RPUFB), which go to an unpowered rail. That back-feeds the dead chip. It also leaves SDA near 0.6 V, so i2cWrite() sees a false ACK and pd.ok goes true with status 0 / current 0. The datasheet does not say whether this back-feed is harmless. Fix (firmware only): drive "high" as INPUT (no pull-up), because the CH224A's own 10k pull-ups are enough for 50 kHz. Also call pdTick() only when PD_PG is low or VIN_USB is present (usbA > 0 or a VBUS sense), and clear pd.ok otherwise.
- RISK | firmware CH224_ADDR | The datasheet gives the 7-bit address as "0x22 or 0x23" with no strap to select it (CH224 sec. 5.2.3). Fix: on NACK at 0x22, retry 0x23 and keep the one that ACKs.
- RISK | Q1/Q2 SI4470EY, LCSC C7568913 | The LCSC part is a VBsemi clone (SI4470EY-T1-GE3-VB), not Vishay. VGS(th) is 1.0-3.0 V. TI recommends 2-2.5 V max for stable light-load regulation (SNOSD17G sec. 10.1.1.2.2). RDS(on) is 12 mR at 10 V, and TI's guideline for 5 A is 4-10 mR (20-50 mV/ILoad). At 5 A that is 60 mV drop and 0.3 W: it works, but the part is outside TI's window. Stock is 172, and the board uses 6 per unit (Q1, Q2, Q6, Q7, Q11, Q13), so 15 boards take 90. Fix: accept as is, or move to a 60 V, Vth ≤ 2.5 V, 5-10 mR SO-8 part.
- RISK | LCSC codes missing | C1, C2, C90, C91, C111, C140, R90, R91, R93, R94, R95, R120, R121 all read "LCSC -". A JLC assembly BOM needs a code for each. C1/C2 also carry no voltage rating: VCAP sits up to 15 V above ANODE (SNOSD17G sec. 6.1, VCAP to ANODE), so they must be ≥ 25 V X7R. Fix: assign codes. C1/C2 100 nF 50 V X7R 0805. R93 20 mR 1 % 2512 ≥ 1 W (0.5 W at 5 A). R120 120k 1 % (CH224 Table 5-1 value).
- NOTE | J2 PJ-002BH | CUI rates the jack at 24 Vdc / 5 A (PJ-002BH spec table). The 26 V top of the input window is 2 V over rating. The value field "DC in 18-26V" also disagrees with the 14-26 V window (the Toughbook brick is 15.6 V).
- NOTE | Hardware requests only 20 V (R120 = 120k, CH224 Table 5-1) | spec.md says the "PD 15 V profile" counts as a live input. The datasheet does not say what the CH224A does when the source has no 20 V PDO, or whether PG goes low then. If it falls back to 5 V, the box runs on battery. Optional fix: firmware writes 0x0A = 3 (15 V) when status shows PD active but PG stays high. Test this on a 45 W charger.
- NOTE | build-radio-kiosk.ts comment at U50 ("the source's PDO list (regs 0x60-0x8F)") | Table 5-3 and the 0x60 heading mark 0x60-0x8F as "Only CH224Q". The CH224A cannot read the PDO list. Firmware does not read those registers, so only the comment and spec.md are wrong.
- NOTE | firmware pdTick() TODO on the 0x50 unit | The datasheet states it: "Maximum current reference value (unit: 50mA)", CH224 sec. 5.2.3, register 0x50. The 0.05 A/count scaling is correct. The register is valid only while a PD contract is up.
- NOTE | 100 W needs a 5 A e-marked cable | The source reads the cable e-marker. With a 3 A cable, 0x50 will report 3 A and the firmware budget follows. CH224 sec. 5.3 (1k from CC2 to GND) applies only to a captive plug, so it does not apply here.
- NOTE | CH224 datasheet contradiction on VBUS (pin 8) | Sec. 7.1 says "VBUS of CH224A has 3.8V tolerant voltage". Table 4-1 ("needs to be shorted to VHV"), the sec. 6.1.1 reference schematic (pin 8 labelled VHV) and abs max table 8.1.1 (VBUS in the 32 V group) all say tie it to VHV. The design follows the majority (pin 8 = VIN_USB). Correct as drawn.
- NOTE | USB_ISENSE scaling | 20 mR × 20 V/V = 0.4 V/A, so 2.0 V at 5 A. ADC full scale is 8.25 A, the INA180 swings to VS-0.03 V, and the input offset of ±150 uV is ±7.5 mA. Firmware /0.4 matches. SBOS741H Fig. 9-1 note recommends an RC between OUT and the ADC. Optional: 1k series + 100 nF at PA5.
- NOTE | VIN_SENSE / DCIN_SENSE | 100k/14.0k = 0.1228, so full scale is 26.9 V at 3.3 V. 26 V reads 3.19 V, which leaves 3 % headroom. 13.4 V gives 1.646 V, matching the comparator reference note. Firmware DIV_HV = 114/14 matches. A 26 V supply running 4 % high will clip the reading (the comparator is unaffected). Changing R91 also moves the 13.4 V backup threshold, so leave it unless BK_REF changes with it.
- NOTE | C111 | This is +5V/GND decoupling for the LED chain (on the +5V net with D30/D31), not an input part. No issue.
- NOTE | No fuse on either input | A reversed DC plug forward-biases D2 and shorts the brick. The brick's OCP then trips, and the TVS may fail short. LM74700 itself tolerates -65 V (SNOSD17G sec. 6.1). Optional: 5 A polyfuse or 1812 fuse in series with J2 pin 1 ahead of D2.

## Verified clean against the datasheet

- LM74700-Q1 (U1, U2), SOT-23-6 DBV, SNOSD17G Table 5-1: 1 VCAP to cap to ANODE, 2 GND, 3 EN tied to ANODE (allowed: "Can be connected to ANODE for always ON"), 4 CATHODE to FET drain (VIN), 5 GATE to FET gate, 6 ANODE to FET source (input). No exposed pad, no NC pins. VCAP 100 nF meets both the 0.1 uF minimum and the ≥ 10 × Ciss rule (10 × 1.1 nF = 11 nF). CATHODE side has 44 uF (≥ 100 nF). FET orientation is correct: source toward the input, drain toward VIN, body diode pointing input to VIN. Q1/Q2 S = pads 1-3, G = 4, D = 5-8, which matches the VBsemi pinout. VDS 60 V and VGS ±20 V meet TI's 60 V / ≥ 15 V.
- INA180A1 (U41), pinout A, SBOS741H: 1 OUT, 2 GND, 3 IN+ on the supply side of R93 (VIN_USB), 4 IN- on the load side, 5 VS = 3.3 V with C115 100 nF (the required ≥ 0.1 uF). Common mode 20 V is within -0.2 to 26 V.
- CH224A (U50), CH224 V2.0 Table 4-1 and sec. 6.1.1: 1 VHV = VBUS with 1 uF (C140, 50 V), 2/3 CFG2/CFG3 to the MCU I2C (internal pull-ups, 6.5 V tolerant), 4/5 DP/DM to both rows of the receptacle, 6 CC2, 7 CC1, 8 VBUS shorted to VHV, 9 CFG1 120k to GND = 20 V (Table 5-1), 10 PG open drain with 10k to 3.3 V (PG is 32 V tolerant), EPAD = GND (footprint pad 11, 3.3 × 2.1 mm, pads 1-5 / 6-10 order checked in LCSC_ESSOP-10_CH224A.kicad_mod). CC pull-downs: the CH224A reference schematic has no external Rd, while the CH224D and CH221K references show external 5.1k. So Rd is internal and none is needed. CFG1 is not driven above 3.8 V.
- SMAJ28A (D2): 28 V standoff ≥ 26 V max DC input. Unidirectional, cathode (pad 1) on the rail.
- PJ-002BH (J2): pad 1 (3.5 mm slot, the centre-pin terminal) = V+, pad 2 = sleeve = GND, pad 3 (switch) NC. Slot sizes match the CUI PCB layout.
- MCU pins for these nets: PA0 = pin 10 VIN_SENSE, PA5 = 15 USB_ISENSE, PA7 = 17 DCIN_SENSE, PB10/PB11 = 21/22 PD_SCL/PD_SDA, PB8 = 45 PD_PG. These agree with firmware-main.cpp. The LQFP-48 pin numbers were checked against the firmware only, not the ST datasheet.
- LCSC codes that match their value: D1/D2 C148227 Littelfuse SMAJ28A. J1 C165948 Hroparts TYPE-C-31-M-12 (20 V 5 A). J2 C22359705 CUI PJ-002BH. U1/U2 C2941042 LM74700QDBVRQ1. U41 C122228 INA180A1IDBVR. U50 C42459160 CH224A ESSOP-10. Q1/Q2 C7568913 is a VBsemi clone (see above).

## Not verified

- TYPE-C-31-M-12 datasheet: the LCSC PDF will not extract (AutoCAD fonts). Pad mapping was checked only against the standard USB-C receptacle order and the footprint: A1B12/B1A12 GND, A4B9/B4A9 VBUS, A5 CC1, B5 CC2, A6/B6 D+, A7/B7 D-, A8/B8 SBU (NC), shell 1-4 GND. The 5 A rating comes from the LCSC listing only.
- CH224A behaviour: what it requests and what PG does when the source has no 20 V PDO. How the 0x22/0x23 address is chosen. Whether back-feeding CFG2/CFG3 while unpowered is harmless. Where its internal pull-ups go.
- USB-C sink bulk capacitance: VIN carries about 75 uF of ceramic straight onto VBUS through U1 at attach. My recollection is that USB limits sink VBUS capacitance at attach (10 uF, cSnkBulk / USB 2.0 7.2.4.1), but I have no spec text on this box. Most PD chargers tolerate it. Check against the USB PD spec, or measure inrush on the charger you plan to use.
- STM32F072 PA0/PA7 injection limits under DC-side transients (about 6 uA through 100k at 34 V) and ADC source-impedance limits for the 12.3k divider: no ST datasheet on this box.

---

# Laptop rail (15.6 V, CC limit) review

Note on refs: in the netlist U42 is the INA180A2 and U43 is the LMV321 (the brief had them swapped). Findings use the netlist refs.

## Findings

- BLOCKER | U43 pins 1/3 (LMV321, LCSC C395459 = IDCHIP clone) | The op-amp input common-mode range ends at V+ - 1.5 V = 1.8 V on +3V3. CMRR >= 50 dB holds only up to V+ - 2 V = 1.3 V (IDCHIP LMV321 datasheet, electrical table, VCM row and note 5). With INA180A2 at 1 V/A, both inputs sit at the setpoint voltage. Firmware uses up to 3.0 A = 3.0 V (firmware-main.cpp laptopTick, `min(limit, 3.0f)`). Above about 1.3-1.8 A the comparison is out of range, so the limit fails in the range where it is needed. | Fix: change U42 to INA180A1IDBVR (gain 20, LCSC C122228, already on the BOM as U41). This gives 0.4 V/A, so 3 A = 1.2 V, inside the 1.3 V range. Firmware: `laptopA = readV(PIN_LAPTOP_ISENSE) / 0.4f;` and `laptopLimitPwm(laptopLimitA * 0.4f);`. Fix the "1 V per amp" comments in the .ts and .cpp files. Other option: keep A2 and use a rail-to-rail-input op-amp. Its SOT-23-5 pinout is different, so check it before you swap.
- WRONG | U43, R97, C117 (loop compensation) | The circuit is not an integrator. With sense on IN+, R97 from the setpoint to IN- and C117 from OUT to IN-, the output is Vcc = Vs*(1 + 1/(s*tau)) - Vset/(s*tau), with tau = R97*C117 = 1 ms. This is a PI controller with a proportional gain of 1 that never rolls off. The high-frequency loop gain is (R40/R98) * g * (V/A) = (100k/4.7k) * g * 1 = 21.3*g. For a 5.2 ohm load (3 A at 15.6 V), g = 0.19 S, so the gain is about 4 (12 dB). It stays flat past the buck's own loop bandwidth, and past the INA180A2 bandwidth (210 kHz, INA180 datasheet 7.5) and the op-amp GBW (1 MHz). The crossover then lands where the buck loop, the output caps and the cable/laptop input LC add phase. Expect oscillation. | Fix: add a new R of 10k from LAPTOP_ISENSE to U43 pin 1 (new net LAPTOP_ISENSE_F) and a new C of 47 nF from U43 pin 1 to GND (tau_f = 0.47 ms). Change C117 from 10 nF to 4.7 nF (tau_i = 100k * 4.7 nF = 0.47 ms). With tau_f = tau_i the pole cancels the PI zero and the loop becomes a pure integrator, G/(s*tau), with 90 degrees of phase margin at any load. With the INA180A1 fix, G = 8.5*g: crossover is about 555 Hz at 5.2 ohm and about 2.9 kHz at a 1 ohm incremental load. Keep the ADC on the unfiltered LAPTOP_ISENSE. The series 10k also keeps the 47 nF off the INA output (1 nF maximum load, INA180 datasheet 7.5). Check it on the bench with a load step at 2.5-3 A.
- WRONG | L4 (SRP7028A-100M, 10 uH) on U4 | LMR33630 datasheet 9.2.2.4, Eq. 5: L_MIN >= 0.28 * VOUT / fSW = 0.28 * 15.68 / 0.4 MHz = 11.0 uH. 10 uH -20 % = 8 uH is below the minimum, at duty 0.6-0.78 (current-mode subharmonic risk). The 12 V row of Table 9-2 already uses 15 uH. | Fix: 15 uH with Isat >= 5.05 A (ISC max, datasheet 7.5). SRP7028A-150M (C1847948) has Isat 4 A, which is below ISC max and borderline against ILIMIT max 4.1 A. Pick a larger-body 15 uH part and check its Isat.
- WRONG | U7 pin 4 / LAPTOP_OUT; U7 pin 6 / +15V6_S | LM74700-Q1 Recommended Operating Conditions (6.3) and 10.1.1.2.3 require at least 0.1 uF on CATHODE and at least 22 nF on ANODE. LAPTOP_OUT has no capacitor. +15V6_S has only C7, which goes VCAP to ANODE and does not count. | Fix: add 1 uF/50 V X7R from LAPTOP_OUT to GND at J3, and 100 nF/50 V from +15V6_S to GND at U7 pin 6.
- RISK | CC loop vs U4 hiccup, Q7 body diode | In the limit, the loop holds FB at 1.0 V. The LMR33630 short-circuit hiccup needs FB < 0.4 V (datasheet 7.7 VHC, 8.3.3), so the hiccup never trips. A shorted J3 or plug gets the setpoint current (up to 3 A) with no end. The anode falls below the LM74700 POR (2.2-3.1 V falling, datasheet 6.5), Q7 turns off, and its body diode carries 3 A at VSD 0.8-1.2 V (VBsemi SI4470EY datasheet, IS = 2 A). That is 2.4-3.6 W in an SO-8. There is no voltage sense on this rail, so firmware cannot see it. | Fix: add a 100k/14.0k divider from LAPTOP_OUT to PB0 (U40 pin 18, ADC_IN8, now N$25, unused) with 100 nF to GND. Firmware: if laptopOn and V_LAPTOP_OUT < 13 V for more than 200 ms, drive LAPTOP_EN low and retry after 5 s. The same input also detects a brick plugged into J3 (voltage present while EN is low).
- RISK | Loop reaction time (dead zone) | At rest the op-amp output sits near 0 V. D40 conducts only when Vcc > VFB + Vf, about 1.0 + 0.55 = 1.55 V. After the fix above the integrator ramps at error/tau. With 0.4 V/A and tau = 0.47 ms: 0.25 A over the limit takes about 7 ms to engage, 1 A over takes about 1.8 ms. During that time the buck's own limit caps the output at (ILIMIT + ISC)/2 = 3.4-4.6 A (Eq. 1, 7.5). Whether the Anker 140 W rides through an overshoot of a few ms is unknown. | Plan: bench test with the Anker and a load step from 1 A to 4 A, scope the USB input current. If it trips, make firmware leave more headroom below the allocation (for example 10 % more margin), or shorten tau_i and tau_f together (keep them equal).
- RISK | Laptop as a constant-power load | The CC limit works only if the laptop's current falls when its input voltage falls. A laptop charger that holds constant power has negative incremental resistance: folding the rail raises its current, the rail collapses to the laptop's UVLO, the laptop drops to battery, and the cycle repeats. The spec already lists this as an open test. | Plan: bench test the Toughbook on a 15.6 V supply with the limit at 1.5 A and 2.5 A, and watch for hiccup. If it hiccups, firmware must keep the limit above the laptop's real demand and turn LAPTOP_EN off instead of limiting.
- RISK | U4 pin 3 EN, PB2 | LMR33630 absolute maximum: EN <= VIN + 0.3 V (7.1 note 2). +3V3 can stay up briefly while VIN collapses, and firmware drops EN only on its 50 ms tick. | Fix: add a 10k series resistor between PB2 and U4 pin 3, with R92 on the U4 side (EN leakage is 0.2 nA, datasheet 7.5, so the 10k has no effect on the threshold).
- NOTE | U43 VCC | C116 is the only 100 nF on this cluster, and it is placed at U42. | Fix: add 100 nF from U43 pin 5 to GND at the pin.
- NOTE | C44-C47 (22 uF/25 V X7R 1210, TORCH C53084530) at 15.6 V | These run at 62 % of their rated voltage. No DC-bias curve was found, so the effective output capacitance is unknown. The LMR33630 has internal compensation and depends on Cout (9.2.2.5). | Plan: get the TORCH DC-bias curve, or use 22 uF 1210 parts rated 35/50 V. Check the load step on the bench.
- NOTE | Outside this section | U5 (5 V buck to +3V3) is fed from VIN, not from +12V (nets: U5.2 = VIN). The spec says 5 V/3.3 V are on the backed-up +12V rail, so on battery the MCU loses power. Also, U3 (12 V) uses 10 uH against an Eq. 5 minimum of 8.4 uH (-20 % tolerance = 8 uH). Pass both to the power-tree reviewer.

## Verified

- INA180A2IDBVR pinout A (INA180 datasheet Table 6-1): 1 OUT, 2 GND, 3 IN+, 4 IN-, 5 VS. U42 matches: IN+ on +15V6_BUCK (bus side), IN- on +15V6_S (load side), so the sign is correct. VCM -0.2 to 26 V, so 15.6 V is fine. VS 2.7-5.5 V, so +3V3 is fine. Output swing reaches VS - 0.03 V. 20 mR x 50 = 1.0 V/A, so 3 A = 3.0 V. R96 dissipates 0.18 W at 3 A (1 W part).
- LMV321 (IDCHIP C395459) pinout: 1 IN+, 2 GND, 3 IN-, 4 OUT, 5 VCC, which matches U43. Supply 3.0-5.5 V. VOH is at least 2.7 V at 3 V with 10k.
- Loop sign: current above the setpoint makes the output rise. D40 (pad 1 K on LAPTOP_CC_D, pad 2 A on LAPTOP_CC, KiCad SOD-123 pad 1 = cathode) then sources current through R98 into FB, and the rail falls. The direction is correct.
- Authority: to fold the output to 0 V the loop must inject 1/6.81k + 1/100k = 0.157 mA. That needs Vcc = 1.0 + 0.55 + 0.157 mA x 4.7k = 2.29 V. The op-amp reaches about 2.8-3.0 V, so there is enough authority. When idle, D40 is reverse biased by about 1 V. Leakage of about 25 nA shifts Vout by about 2.5 mV. Capacitance of about 4 pF on FB (6.4k source) is a pole at 6 MHz. Normal regulation is not affected.
- U4 set point: 1.0 V x (1 + 100k/6.81k) = 15.68 V (VFB 0.985-1.015, datasheet 7.5). At J3 that is about 15.6 V after the 60 mV shunt drop and the 20 mV ideal-diode drop.
- PWM filter: 20 kHz (TIM1 ARR 2399 at 48 MHz). R99 10k x C118 1 uF gives 15.9 Hz. Ripple at D = 0.5 is 3.3 x 0.25 / (20 kHz x 10 ms) = 4.1 mV p-p. Resolution is 2400 steps (1.4 mV). Settling (5 tau = 50 ms) matches the 50 ms firmware tick. R97 carries no DC in regulation.
- Reset: R92 100k holds EN low (EN leakage 0.2 nA, datasheet 7.5; "must not float", 8.3.2). PA9 is high-Z but the buck is off. setup() drives EN low before pwmInit(), and CCR2 starts at 0. At enable the setpoint rises with tau = 10 ms, which acts as a soft start. If firmware hangs with EN high, the timer keeps the limit, and the 2 s IWDG resets the MCU, which drops EN.
- Firmware scaling as written (1 V/A for both read and setpoint) matches the INA180A2 hardware. It must change to 0.4 V/A with the BLOCKER fix. MCU pins: U40 pin 30 = PA9 (AF2 TIM1_CH2), pin 20 = PB2, pin 19 = PB1 (ADC_IN9).
- U7/Q7: SOT-23-6 pinout 1 VCAP, 2 GND, 3 EN, 4 CATHODE, 5 GATE, 6 ANODE (LM74700-Q1 Table 5-1) matches. Q7 S (pins 1-3) is on +15V6_S (anode) and D (pins 5-8) is on LAPTOP_OUT, so the body diode points forward and reverse current is blocked. C7 100 nF is VCAP to ANODE (0.1 uF minimum). EN is tied to ANODE (always on). Q7 VGS is +/-20 V, above the 15 V required (6.3). RDS(on) is 12 mR, 0.11 W at 3 A.
- J3 (CUI PJ-002BH): datasheet drawing gives pin 1 = centre pin (1.0x3.5 slot), 2 = sleeve (1.0x3.0), 3 = switch (1.0x3.0, 4.7 mm offset). The LCSC footprint pads match in size and position. J3.1 = LAPTOP_OUT (centre positive), J3.2 = GND, J3.3 open. The jack is rated 24 V, 5 A.

## Not verified

- Toughbook plug polarity and size (5.5x2.5 centre positive): no Panasonic document was checked. Measure the brick you have.
- LMR33630 closed-loop bandwidth: not in the datasheet. The loop margin above assumes it is well above about 3 kHz. Check with a load step.
- Anker 140 W overload trip time, and the Toughbook's behaviour when current-limited (see the RISK lines).
- Whether STM32duino's Serial1.begin() leaves PA9 in AF2 after setTx(PB6). Check on hardware that the PWM is present on PA9.
- Effective capacitance of C44-C47 at 15.6 V (no DC-bias data found).

---

# Battery backup review (BT1-BT4, F1, Q8-Q11, U10, R80-R89, C97-C99)

Sources: parts.txt, nets.txt, build-radio-kiosk.ts L698-751, firmware-main.cpp batteryTick/selfTest. Datasheets in review/ds: aod4185.txt, tlv7011.txt, si4470vb.txt (SI4470EY-T1-GE3-VB, the C7568913 part), ao3400a.txt, lm74700-q1.txt, fuse1206td.txt, bh123a.pdf, energizer123.pdf (EL123AP).

## Findings

BLOCKER | Q8 (AOD4185) pad 2 D=+12V, pad 3 S=PACK_F | The P-FET body diode has its anode on the drain (+12V) and its cathode on the source (PACK_F), so it conducts +12V -> pack. The code comment ("body diode points pack-to-rail") is backwards. When the buck holds +12V at 12.0 V, any pack below about 11.4 V resting (a used set at 2.85 V/cell, or a set with one cell reversed at about 6.4 V) is charged through the diode. The only limits are the cell resistance, the 2 A time-delay fuse (it holds 200 % of rating for 1-60 s, fuse1206td p1) and the LMR33630 current limit. The EL123AP datasheet allows 2 uA of reverse current ("Max Rev Current: 2 uA"). The same diode also feeds the self-test load from +12V (see the WRONG line on the self-test). | Fix: put an ideal diode in series between the pack and Q8, using a third copy of the U6/Q6 block. Add U11 LM74700-Q1 (C2941042): 6 ANODE=PACK_F, 4 CATHODE=BK_MID, 5 GATE=U11_GATE, 1 VCAP=U11_VCAP with 100n from U11_VCAP to PACK_F, 2 GND, 3 EN=BK_DRV. Add Q12 SI4470EY: S 1-3=PACK_F, G 4=U11_GATE, D 5-8=BK_MID. Move Q8.3 and R80.1 from PACK_F to BK_MID. R85/R88/R86 stay on PACK_F. Q8's body diode then blocks pack -> rail and Q12 blocks rail -> pack. Q12 IDSS is 1 uA max (si4470vb p2), inside the 2 uA cell limit. Shutdown draw is 1.5 uA max (lm74700 I(SHDN)). Q12 needs Vgs up to about 11 V from the LM74700 charge pump; SI4470EY is rated +-20 V. AO3400A is rated +-12 V, so do not use it here.

BLOCKER | Q8 channel, overlap window | Back-to-back FETs alone do not fix this. Q8 is on whenever VIN < 13.4 V. The LMR33630 12 V buck still regulates in that window: while VIN falls from 13.4 V to its dropout, and while VIN ramps up at power-up, when +3V3 is alive from about VIN 6 V and the comparator reads "low". An on-FET conducts both ways, so a used pack below 12 V is charged through the Q8 channel at up to the buck current limit. | Fix: the U11/Q12 ideal diode above. The LM74700 turns off on reverse current (V(AK) reverse threshold), which blocks this path. No back-to-back P-FET arrangement blocks it.

BLOCKER | U5 (LMR33630 5 V) pads 2 VIN and 3 EN are on net VIN, not on +12V | +5V, and +3V3 from it via U51, come from the input side, not from the backed-up rail. When the input goes away, VIN decays under the U4 laptop buck and U5 loads. Once VIN falls below about 5.5 V, +3V3 collapses and U10 loses supply. BK_ON goes low, R80 pulls Q8 off, and the radio drops. Ride-through is only the VIN hold-up (milliseconds), not 5 minutes. | Fix: move U5.2, U5.3 and its input caps C50/C51 from VIN to +12V. The LMR33630 accepts 3.8-36 V in. The loop this makes (Q8 on -> +12V -> +5V -> +3V3 -> U10 -> Q8 held on) is OK. U10 trips at VIN 13.4 V while the 12 V buck is still regulating, so +3V3 is up when Q8 closes. The pack alone cannot start the board, because R80 holds Q8 off with +3V3 at 0.

WRONG | firmware selfTest(), current netlist | Because of the Q8 body diode, during the test PACK_F = max(pack loaded ~10.1 V, +12V - Vf ~11.2 V). The test reads the +12V rail, not the pack. A dead pack or no pack passes. With the divider error below, every pack reads about 9.4 V and fails. | Fix: the U11/Q12 ideal diode (BLOCKER 1) makes PACK_F the pack alone.

WRONG | firmware `packV`/`packLoadedV` use DIV_HV = 114/14 = 8.143; R86/R87 = 100k/11.5k gives 111.5/11.5 = 9.696 | Pack voltage reads 16 % low. A real 10.0 V reads 8.40 V. The 10 V threshold is actually at 11.9 V, so every fresh pack fails. | Fix: add `static const float DIV_PACK = 111.5f / 11.5f;` and use it for PIN_PACK_SENSE in sampleAnalog() and selfTest(). If the resistors change as in the RISK below, use (R86+R87)/R87. Range check: 13.3 V -> 1.37 V, full scale about 32 V, no ADC overrange.

WRONG | selfTest threshold `packLoadedV > 10.0f` at 12R | Test current = 10.1 V / 12 R = 0.84 A with ~10 V loaded (1.07 A at open-circuit voltage). EL123AP datasheet, "Photoflash 1200 mA (3 s on/7 s off) at 21 C": a fresh cell is about 2.5 V loaded, falling to 2.0 V at the knee. Four fresh cells = about 10.0-10.2 V, minus 0.14 V across F1 (0.13 R cold, fuse1206td p1) = about 10 V at PACK_F. That is the threshold. Fresh packs fail at room temperature or below. | Fix: threshold 8.8 V (2.2 V/cell loaded). On the 1200 mA curve that is about 800 of 1300 pulses to the knee, about 40 % left, about 5 five-minute events at 1.1 A. Raise it only if the radio port needs more (see NOTE on the minimum rail). Log `pack_loaded` so the trend can be tuned. Below 10 C from the NTC, report and do not fail.

RISK | Q11 SI4470EY-VB, gate from TEST_LOAD (PB12, 3.3 V) | VGS(th) is 1.0-3.0 V at 250 uA and RDS(on) is only specified at 4.5 V and 10 V (si4470vb p2). At 3.3 V gate drive the 1 A test current is not guaranteed. A high-Vth part gives a weak load, so a worn pack passes. | Fix: change Q11 to AO3400A (C20917, SOT-23, G=1 S=2 D=3): 30 V, VGS(th) 0.65-1.45 V, RDS(on) < 48 mR at 2.5 V (ao3400a p1). At 1.07 A that is 55 mW.

RISK | Relatch after BK_KILL (applies once U5 is on +12V) | Kill sequence: Q10 opens Q8, +12V/+5V/+3V3 decay. At the STM32 PDR (about 1.8 V) PA10 goes Hi-Z and R89 pulls BK_KILL low. U10 still runs down to 1.6 V (tlv7011 VS range), with OUT high (IN- = 0 V), so Q9 sees Vgs of about 1.8 V. Q8 starts to conduct when Q9 sinks only 17 uA through R80 (1.7 V / 100k, AOD4185 VGS(th) min -1.7 V). If Q9 conducts at that Vgs, +12V comes back, the MCU reboots with BK_KILL low and a fresh 5 min cap, and the loop repeats until the pack is flat. I could not confirm this. It depends on the 2N7002 (C8545) VGS(th) spread, and I did not read that datasheet. | Fix: make the MCU an enable, not a kill. Move Q9.2 (S) to new net BK_LO. Q10: D=BK_LO, S=GND, G=BK_EN (PA10), keep R89 100k pulldown. The FET only closes when the comparator says "low" and the running MCU drives PA10 high, so a reset or dead MCU cannot close it. Firmware: PA10 HIGH once vinV > 13.5 V after boot; LOW to cut; HIGH again when BK_ON goes low. Trade-off: no backup while the MCU is in reset or DFU.

RISK | R86/R87 100k/11.5k always across PACK_F | 13 V / 111.5k = 117 uA constant drain. 1500 mAh (EL123AP) / 0.117 mA = 12,800 h = 1.5 years. Also, with the board off, PACK_SENSE (1.34 V from 10.3k) injects about 0.1 mA into the unpowered PA1 and +3V3. A kiosk stored off-season comes back with a flat pack. | Fix: R86 = 1M, R87 = 115k (1 %), plus 100 nF from PACK_SENSE to GND. Drain drops to 11.7 uA (about 15 years), the ratio is 9.70 (keep DIV_PACK = 1115/115), and tau = 10 ms is well settled at the 180 ms read.

RISK | Reversed or missing cell | One reversed cell gives about 6.4 V. The self-test and a backup event then drive load current backwards through that cell. F1 does not open at 0.5-1 A. | Fix (firmware): before TEST_LOAD, read packV unloaded. If it is below 11.5 V, skip the load, set packOk=false and report "pack fault". In batteryTick, if packV < 9.5 V while BK_ON is high, cut at once. Holder silk +/- is correct (see Verified).

RISK | R85/R88 24R "1W" 2512, LCSC "-" (no part chosen) | Each resistor takes 10.1^2/24 = 4.3 W (up to 13.3^2/24 = 7.4 W at the first instant) for 200 ms, twice, 300 ms apart. That is 4-7x its continuous rating. Whether a 2512 survives depends on the part's pulse-load chart, and no part is chosen. | Fix: choose a part with a published single-pulse curve of 8 W or more at 0.2 s (an anti-surge/pulse-rated 2512 1 W thick film). Otherwise use 2x 2512 2 W. Also rate-limit the serial `test` command (at most once per 60 s): today a looped command gives about 1.7 W average per resistor.

RISK | Radio load on battery vs cells and F1 | EL123AP: 1500 mA continuous max. At about 10 V pack, that is about 14 W into the rail after the boost/eFuse. A PoE Type 2 radio can draw up to 25.5 W, about 2.9 A from the pack, which is over the cell rating and over F1 (2 A; time-delay, 200 % opens in 1-60 s). The spec's 10 W assumption gives about 1.1 A, which is inside both. | Fix: measure the V2 radio's draw in both modes (already in spec "Open"). If it is above about 12 W, cap backup to passive mode or cut when PSE-powered on battery.

NOTE | U10 hysteresis | R84 1M against 10k||10k: ΔREF = 3.3 V x 5k/1005k = 16.4 mV, plus internal VHYS 1.2-14 mV (tlv7011 table). At VIN that is 0.14-0.25 V. The trip is 1.65 V x 114/14 = 13.44 V, release about 13.6 V. The code comments say "~50 mV" and "Vin < 16 V" (L722, L1035), which are wrong but do no harm. VIN_SENSE has no filter cap, and the TLV7011 is fast (260 ns). | Fix: add 10 nF from VIN_SENSE to GND (tau 0.12 ms, no real delay to handover) and correct the comments.

NOTE | Firmware timing vs spec | batteryTick cuts after 5 s with no load. Spec and brief say 2 s. The 5 s value is justified in the code (longer than the 3 s PSE detect). | Fix: update the spec to 5 s.

NOTE | Minimum +12V on battery | A worn pack under radio load puts about 9-10 V on +12V. I did not check whether the eFuse path, boost and radio work that low (other sections). | Fix: whoever owns U20/U21 confirms their minimum input voltage. Set the self-test threshold at or above it.

NOTE | DFU mode and PA10 | If the ST system bootloader configures USART1_RX (PA10) with a pull-up, BK_KILL goes to about 2.4 V (40k internal against R89 100k) and backup is disabled while in DFU. This is not a safety issue. I did not verify it in AN2606. | Fix: none needed. With the BK_EN change above this becomes "backup enabled in DFU", which is harmless.

NOTE | U6/Q6 | Q6 S=+12V_BUCK (anode side), D=+12V, U6 ANODE=+12V_BUCK, CATHODE=+12V. The body diode and controller block +12V -> +12V_BUCK, so the pack cannot back-drive the 12 V buck. No other path from +12V to VIN was found (U4/U5 are on VIN; after the U5 fix, U5 is fed from +12V and has no output path back to VIN).

## Verified

- Series wiring: BT1 1(+)=PACK_P, 2(-)=PACK_1; BT2 PACK_1/PACK_2; BT3 PACK_2/PACK_3; BT4 PACK_3/GND. Correct series order.
- Holder polarity: footprint pad 1 (x=-18.82) carries the silk "+" (two bars) and the locating peg; pad 2 carries "-". This matches the MYOUNG BH-123A-A1CJ002 drawing: "+" pin on the peg side, pitch 37.5 +-0.5 against 37.64 in the footprint. The drill is 1.2 mm against the drawing's 1.8 mm, which still fits the 0.8 x 0.3 mm tab. Check one physical holder.
- Q8 pinout: AOD4185 TO-252 G=1, S=3, D=tab. KiCad TO-252-2 pad 2 is the 6.4x5.8 tab. Matches.
- Q8 Vgs on battery: -10 to -13 V, inside the +-20 V rating. RDS(on) < 15 mR at -10 V, so fully on; 18 mW at 1.1 A.
- U10 TLV7011DBVR: SOT-23-5 pinout 1 OUT, 2 VEE, 3 IN+, 4 IN-, 5 VCC matches parts.txt. Push-pull output (TLV702x is the open-drain part). Polarity is right: VIN_SENSE < BK_REF -> OUT high -> Q9 on -> Q8 on.
- Q10 kill path: R81 1k keeps BK_ON readable at PB3 while Q10 shorts BK_DRV (3.3 mA, inside the TLV7011 VOH spec at 3 mA). At MCU reset, R89 holds BK_KILL low, so the kill is inactive. TEST_LOAD has R100 pulldown, so the load is off at reset.
- F1 1206TD-2A: time-delay, 0.13 R, never opens at 1.07 A/200 ms (53 % of rating). A short on PACK_F (1000 %) clears in 0.2-20 ms.
- C97/C98 470u/25V on +12V: voltage margin fine. Inrush at Q8 close is small (rail about 12 V against pack about 12.8 V).
- Power-up with no pack (after the fixes): PACK_F = 0 V, the self-test reads 0, packOk=false. Q8 may close during the VIN ramp, which does no harm.

## Not verified

- 2N7002 (C8545) VGS(th) spread, so the relatch loop is not proven either way.
- Pulse rating of R85/R88: no part is chosen.
- V2 radio power draw on battery, and the minimum +12V the eFuse/boost/radio accept.
- CR123A behaviour below 21 C, and for makers other than Energizer: only the EL123AP sheet was read.
- STM32 bootloader pin states (AN2606 not read).

---

# Radio port review: LM3478 boost, LTC4279 PSE, TPS26600 passive path, J5

Sources: LTC4279 4279fa (/home/filip/uploads/4279fa.pdf), TI TPS2660 SLVSDG2G, TI LM3478 SNVS085Y, AO4482 / PSMN075-100MSEX / RVT1J470M0810 / R-RJ45R08P-A004 datasheets from the JLC file endpoint, JLC part API for LCSC codes. Text copies in review/ds/.

## Findings

1. BLOCKER | U21.3 UVLO = GND | UVLO tied to RTN selects the internal UVLO: V(IN) rising 14.25-15.75 V, falling 13.25-14.75 V (TPS2660 EC table p7; 9.3.1 p22). IN is the 12 V rail, so the eFuse never turns on and passive PoE never works. | Fix: tie U21.3 to +12V (datasheet: "If the UVLO function is not needed, the UVLO terminal must be connected to the IN terminal"), or a divider +12V-732k-UVLO-100k-GND (on 9.9 V, off 9.2 V).

2. BLOCKER | firmware portSet() + PORT_P | Going from PSE detect to passive, firmware raises BOOST_SD, waits 5 ms, then raises PASSIVE_EN, and Q13 grounds PORT_N. PORT_P still holds about 54 V on C23/C24/C25/C62 (about 57 uF). The only guaranteed discharge path is R22+R23 (411.5k), so tau is about 23 s. The LTC4279 IEE (1.7 mA typ, 4279fa p3, not guaranteed in reset) may bring it down in about 1-2 s. The TPS26600 does not stop this: its reverse comparator keeps its FET off while OUT > IN (p8), so the radio in passive mode gets 54 V directly from the caps. This breaks the design's "never both" rule. Whether the radio survives 54 V on its passive input is unknown. The board also has no way to measure PORT_P. | Fix: (a) add a PORT_P sense divider, 1M / 56k + 100 nF, to PB0 (U40.18, now N$25); 54.4 V reads 2.88 V. (b) Add a bleeder: 2.2k 2512 plus a 100 V SOT-23 N-FET (BSS123 class) from PORT_P to GND, gate on PA15 (U40.38, now N$26), 100k pull-down. (c) In firmware: after BOOST_SD goes high, turn the bleed on, wait for PORT_P < 13 V (with a timeout that reports a fault), turn the bleed off, then raise PASSIVE_EN. Firmware-only stopgap: wait at least 40 s before PASSIVE_EN.

3. WRONG | L20/D20 -> PORT_P | A boost always has a DC path from input to output: +12V -> L20 -> D20 -> PORT_P, whatever BOOST_SD says. PORT_P therefore sits at 11.6 V whenever +12V is up, not only when the eFuse is on. In passive mode, once U21 reaches its 1.5 A limit or its circuit breaker trips (MODE open, tCB 4 ms, p8), PORT_P drops about 0.4 V and D20 carries the fault current with no limit and no IMON reading. Only the 12 V buck or the pack fuse then limits a robot pulling current through the port. Firmware makes this worse: `backfeed` only drives the LED and never drops PASSIVE_EN. | Fix: put a P-FET (AOD4185, already in the BOM) in series between +12V and L20.1. Gate 100k to +12V, pulled down by a 2N7002 driven from a new BOOST_PWR GPIO (PB9, U40.46, now N$27) with a 100k pull-down. BOOST_PWR is high only in PSE mode. In firmware, call portSet(false,false) and latch off when backfeed is detected. With the P-FET, PORT_P idles at 0 V, which also helps finding 2.

4. WRONG | D71 cathode on PSE_AGND | The datasheet requires "an S1B clamp diode (D3) from OUT to supply AGND", meaning the supply side of the 10R, with low-impedance paths to the port (4279fa p18, Fig 13). As drawn, a surge that lifts OUT goes through D71 into the chip side of R70, onto the AGND pin. | Fix: move D71.1 (K) from PSE_AGND to PORT_P. D71.2 stays on PORT_N.

5. WRONG | no bulk TVS PORT_P-GND | "Bulk transient voltage suppression (TVSBULK) and bulk capacitance (CBULK) are required across the main PoE supply" (4279fa p17-18). The main supply is PORT_P to GND. D22 sits across the port (PORT_P to PORT_N), and D70 is behind the 10R. Nothing clamps PORT_P to GND, and this node also feeds U21 OUT (62 V abs max). | Fix: change D22.2 (A) from PORT_N to GND. This gives Fig 13's topology: PORT_N above PORT_P clamps through D71 (after fix 4) and D22, PORT_N below GND through the Q22/Q13 body diodes.

6. WRONG | Q20 footprint | AO4482 is a plain SO-8 with no exposed pad (AO4482 datasheet p1 "SO8"). The part uses FP.soic8ep (SOIC-8-1EP ... EP2.41x3.3mm) with pad 9 on BOOST_SW. JLC will print paste on a pad the package cannot wet, and a solder slug under the body can lift the leads. | Fix: NMOS_100V footprint -> Package_SO:SOIC-8_3.9x4.9mm_P1.27mm and drop pin 9.

7. WRONG | R26 100k, BOOST_SD reset default | With the MCU pin floating, R26 100k feeds 1k + D21 into R21 40.2k: FA/SD = (3.3 - ~0.5) x 40.2 / 141.2, about 0.8 V. The LM3478 needs > 1.4 V (max) to be off and < 0.3 V (min) to be on (SNVS085Y EC p6, note 6). 0.8 V is undefined and below the 1.27 V typ threshold, so the boost probably runs during reset, DFU and watchdog restarts. This breaks the firmware comment "BOOST_SD up (boost off)". | Fix: R26 -> 10k. Floating then gives 2.1 V, and the MCU sinks 0.33 mA when it drives low.

8. RISK | R63 100k, U21.7 SHDN / Q13 gate | SHDN has an internal pull-up: 2-3.4 V open circuit, up to 10 uA at 0.4 V (TPS2660 p7). Into 100k that can be 1 V. The shutdown threshold is 0.55-0.94 V, and Q13 VGS(th) min is 1.0 V. So during MCU reset the eFuse is not guaranteed off (after fix 1) and Q13 can partly conduct. | Fix: R63 -> 10k (0.1 V worst case, 0.33 mA from the GPIO).

9. RISK | Q13 SI4470EY-T1-GE3-VB (VBsemi clone) | 60 V part. With the PSE port off, PORT_N is pulled to AGND (PORT_P, up to 56 V) by OUT's internal 500k (4279fa p3, p9), and boost OVP can reach 59.8 V. That leaves 0-4 V of margin and no surge margin. Its gate gets 3.3 V from the MCU, but VGS(th) max is 3.0 V and RDS(on) is only specified at 4.5 V and 10 V. | Fix: use a 100 V FET specified at 4.5 V (AO4482: 42 mOhm at 4.5 V, same footprint as fixed in 6). Drive its gate at 5 V from a +5V-powered SN74AHCT1G125 (already in the BOM for the LEDs) fed from PASSIVE_EN, with the input pull-down kept.

10. RISK | C25 47u/63V RVT1J470M0810 | 63 V rating on a 54.4 V rail (53.0-56.1 V worst case, OVP up to 59.8 V). Ripple rating is 125 mA at 120 Hz, x1.5 at 10 kHz and up, so about 190 mA (RVT datasheet). The spec asks for 80-100 V. | Fix: 47 uF 100 V electrolytic, 10x10.5 case or larger, low-ESR series.

11. RISK | PORT_P ripple vs LTC4279 requirement | "VEE supply ripple and noise must be less than 100 mVP-P at frequencies above 150 kHz" (4279fa p17). Estimate: dV = Iout x D / (fs x C). With C23+C24 derated to about 4-5 uF at 54 V (not verified, no DC-bias curve), 394 kHz, D 0.78: about 120 mV at 0.3 A (15 W) and 230 mV at 0.56 A. Too much ripple can upset DC disconnect. | Fix: add two more 4.7 uF/100 V 1210 X7R at D20/PORT_P, or an LC post-filter (ferrite plus 4.7 uF) before R70/J5. Measure on the bench.

12. RISK | U20/R20 boost capacity | Current limit per SNVS085Y Eq 19 at D = 0.78 with 20 mOhm: 2.84 A min, 4.8 A typ, 7.3 A max. Needed switch current (Eq 18) is 2.9 A for a full Type 2 PD (0.556 A at 54 V) and 3.55 A at the class 4 ICUT (638 mA, 4279fa Table 4). Guaranteed output is about 26 W at 12 V in and less on the pack at 10 V. The script says it is sized for 10-15 W. If the radio classifies as class 4 and pulls more than about 20 W, PORT_P sags. | Fix: get the radio's class and peak draw. If class 4 above 20 W, use R20 15 mOhm (max limit then about 9.7 A) and an inductor with Isat >= 10 A. Otherwise leave it.

13. RISK | U22.4 VSSK on GND, U22.5 SENSE on PSE_SENSE | Both pins must be Kelvin traces to R72's pads and must not touch the GND plane or the Q22 power path (4279fa p18-19 "Kelvin Sense"). On the shared GND net, the zone fill and Freerouting will join VSSK to the nearest ground copper. | Fix: give VSSK its own net joined to R72.2 through a net-tie footprint, and route SENSE only to the R72.1 pad.

14. RISK | U21 OUT abs max 62 V (TPS2660 p6) | OUT is PORT_P. SMAJ58A clamps at 93.6 V at 4.3 A (JLC data), so a port surge can exceed OUT's rating even after fix 5. | Fix: none cheap. Accept the risk, or put a series Schottky between U21 OUT and PORT_P. That also blocks PORT_P from ever reaching U21, but IMON still works.

15. NOTE | U22.1 MID low | The board passes data J6->J5 and injects power, so it is a midspan. The datasheet says "The MID pin should be logic high if the standalone application is a midspan" (p12). Low only skips the 2.5 s detection backoff that IEEE requires of midspans. Function is unaffected. | Fix: optional, tie R74 to +3V3 instead of GND. Then raise the firmware DETECT window from 3 s to 6 s.

16. NOTE | U21 RTN (pin 8) = GND | Tying RTN to GND disables the reverse input polarity protection (TPS2660 9.3.5.5). This is acceptable here because IN comes from the on-board 12 V rail and cannot be reversed.

17. NOTE | IMON scaling | 78.28 uA/A x 10k = 0.783 V/A, which matches firmware's 0.78. 1.5 A gives 1.17 V, and fast-trip 1.8x gives 2.1 V, both inside 3.3 V. R_IMON max per Eq 5 is 18.9k. ILIM: 8.06k gives 1.49 A (12 k/I, p7). The 1.3 A backfeed threshold works, with thin margin: at ILIM min 1.425 A and gain min 72 uA/A, firmware reads 1.316 A. Below 50 mA, IMON is only the 2 uA offset (20 mV, which reads as 0.026 A, Eq 7), so the 0.05 A no-load threshold is at the edge of the linear range. Reverse current (a robot at higher voltage) asserts FLT (p24), so firmware's FLT check flags that case.

18. NOTE | R72 C844904 is WSL2512R1000FEA: 1 W, +-75 ppm, 1% | The schematic label says 2 W. Dissipation is 0.85 A^2 x 0.1 = 72 mW, and the datasheet asks for 1% and <= 200 ppm. OK as is. Fix the label only.

19. NOTE | L20 MDA1365-330M | JLC lists 6 A rated, 7.3 A saturation, 66 mOhm (schematic value says 4.5 A). Worst-case LM3478 limit peak is about 7.3 A, right at Isat. Normal peak is 3.6 A at 0.64 A out. DCR loss is about 0.7 W at full load.

20. NOTE | LM3478 compensation R24 10k / C21 47n | Not verified. The datasheet defers to AN-1286. Rough estimate: crossover near 6 kHz, close to RHP-zero/3 (about 20-25 kHz / 3) at full load. Check with a load step on the bench.

21. NOTE | C70, C71, C62 have no LCSC code | They must be 100 V X7R (4279fa p17: C70 1 uF 100 V X7R, C71 0.22 uF 100 V X7R).

22. NOTE | C112 | It is +5V decoupling, not a port part. Nothing to check here.

## Verified correct

- LTC4279 SO-16 pinout, all 16 pins, against 4279fa p2. DNC pins 2/3/11/15 are open.
- PSE topology: VEE = GND, AGND = PORT_P through 10R (R70), Q22 drain on PORT_N, source to R72 0.1R to GND. This is the correct low-side PSE for a +54 V system.
- C70 1u/100V and D70 SMAJ58A across AGND-VEE. C71 0.22u across OUT-AGND. R71 200R RGATE. Q22 is the recommended PSMN075-100MSE; LFPAK33 pads 1-3 S, 4 G, 5 tab D match KiCad's LFPAK33 and the Nexperia pinning.
- PWRMODE 3.32k 1% = Type 2. LEGACY and DUALPD low. RESET: 100R series, 10k pull-down, so the PSE is off at MCU reset. 2.1 V logic high is OK from 3.3 V (logic is referenced to VEE = GND). LED is open drain with 10k to 3V3, low = powered, matching firmware.
- Supply: FB 402k/9.53k gives 54.4 V (53.0-56.1 V worst case with VFB +-2.5% and 1% resistors), inside the 51-57 V Type 2 range. D22 and D70 SMAJ58A standoff is 58 V. VBR min is 64.4 V for the standard SMAJ58A (the Ruilon sheet was not read), which is above the boost OVP max of 59.8 V.
- LM3478 SOIC-8 pinout. RFA 40.2k gives 394 kHz (Eq 7). Subharmonic check Eq 21: 20 mOhm < 39 mOhm at 10 V in. FA/SD driven high from the MCU gives 2.6 V > 1.4 V. Gate drive 7.2 V; AO4482 is 100 V, 42 mOhm at 4.5 V. D20 SS310 100 V 3 A. C23/C24 100 V X7R.
- TPS26600 HTSSOP pinout against TPS2660 p4-5. With PORT_P at 54 V and IN at 12 V, IN-OUT = -42 V (abs max -60 V) and OUT is under 62 V; the reverse comparator holds the FETs off. OVP = RTN selects the internal 33 V OVP, fine for 12 V. MODE open = circuit breaker with auto-retry. dVdT 10 nF gives 11.6 V/ms, about 0.66 A into 57 uF, below the 1.5 A limit.
- 12 V on PORT_P in passive mode only charges the boost output caps (63/100 V) and puts 0.28 V on FB. It is harmless. D20 blocks 54 V from the 12 V rail, and U21 blocks it too.
- J5: PORT_P on 4/5 and PORT_N on 7/8 is 802.3 Alternative B polarity. Data 1/2/3/6 go straight to J6, and J6 4/5/7/8 are open. Contacts are rated 1.5 A each (Ckmtw drawing).
- MCU nets: BOOST_SD PB13, PASSIVE_EN PB14, PSE_EN PB15, IMON PA2, FLT PB4, PSE_ON PB5 match the firmware pin map.

## Could not verify

- J5 pad-to-contact numbering. The Ckmtw drawing does not number the contacts. The footprint pads 1-8 zig-zag in order, and the same footprint was on v1. Check one v1 board with a meter: pad 1 to the contact on the clip-down right side.
- Real DC-bias capacitance of C337978 at 54 V and the ESR of C25, so finding 11 is an estimate.
- LM3478 loop stability (AN-1286 not read).
- The Vivid radio's PoE class, peak draw, and passive-input voltage limit. These decide how severe findings 2 and 12 are.
- Whether the LTC4279 draws IEE while held in RESET (sets real PORT_P discharge time).

---

# MCU section audit (U40 + USB J12 + LEDs + fan + ADC front ends + firmware)

Sources: ST DS9826 / DocID025004 Rev 5 (via JLC file endpoint, C81720), WS2812B-4020 (Worldsemi, C965557),
SN74AHCT1G125 (TI, C7484), USBLC6-2SC6 (ST, C7519), NCP18XH103 (Murata), AO3400A, SI4470EY, TPS2660,
CH224 v2.0, STM32duino core 4.30000.0 in ~/.platformio, Adafruit_NeoPixel.cpp (GitHub master).
Board file checked: Electronics/loon-projects/Radio_Kiosk_v2b/board.kicad_pcb.

## Findings

BLOCKER | J12 | LCSC C5143397 is GCT USB4110-GF-A, but the footprint is Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12. JLC will place a different connector on a land pattern drawn for another part. Source: build-radio-kiosk.ts line 1124 byLib "Connector:USB_C_Receptacle_USB2.0": "C5143397". | Fix: set J12 LCSC to C165948 (HRO TYPE-C-31-M-12, same as J1), or change the footprint to the USB4110-GF-A land pattern.

WRONG | firmware, USB (PA11/PA12) | CRS is never enabled. STM32duino's F072CB generic_clock.c runs SYSCLK and USB from HSI48 with no CRS, and no file in the core or USBDevice library touches CRS (grep). HSI48 factory accuracy is -2.8/+2.9 % at 25 C, -4.1/+3.7 % over -10..85 C (DS Table 43); USB FS needs +/-0.25 %. CDC enumeration will be unreliable. The ROM DFU bootloader does its own CRS, so DFU is not affected. | Fix: at the top of setup(): `__HAL_RCC_CRS_CLK_ENABLE(); RCC_CRSInitTypeDef c = {RCC_CRS_SYNC_DIV1, RCC_CRS_SYNC_SOURCE_USB, RCC_CRS_SYNC_POLARITY_RISING, __HAL_RCC_CRS_RELOADVALUE_CALCULATE(48000000, 1000), 34, 32}; HAL_RCCEx_CRSConfig(&c);` (HAL_RCCEx_CRSConfig exists in stm32f0xx_hal_rcc_ex.h).

WRONG | R86/R87, PA1, firmware DIV_HV | PACK_SENSE divider is 100k/11.5k (ratio 9.696), firmware uses "same divider" 114/14 (8.143). packV and packLoadedV read 16 % low. A good pack loaded to 11.0 V reads 9.2 V, so packOk = false and D30 flashes red/blue on every good pack. | Fix: `static const float DIV_PACK = 111.5f / 11.5f;` and use it in sampleAnalog() and selfTest(). (Or change R87 to 14.0k; 13 V pack = 1.60 V, fine.)

WRONG | R103, D30.1 | Both R103 pads are on LED_D0, in nets.txt and in board.kicad_pcb. The script asks for R103 LED_D0 -> LED_D0R and D30.1 on LED_D0R; LED_D0R is the only script net missing from the netlist. The 100R series resistor is shorted out. The LEDs still work. | Fix: find why the LED_D0R label merged into LED_D0 in the generator (label/wire at R103 pin 2 or D30 pin 1), regenerate, confirm nets.txt shows `LED_D0R: R103.2 D30.1`.

WRONG | Q11 (PB12 TEST_LOAD), Q13 (PB14 PASSIVE_EN) | Both SI4470EY gates are driven straight from 3.3 V GPIO. SI4470 VGS(th) is 1.0-3.0 V and RDS(on) is only specified at VGS = 4.5 V (SI4470 datasheet, static table). At 3.3 V a worst-case part is barely on: Q11 carries ~1 A self-test load, Q13 carries the passive PoE return (eFuse limit 1.5 A). | Fix: Q11 -> AO3400A (30 V, 48 mR at 2.5 V; TEST_NODE is only pack voltage). Q13 needs >= 60 V (PORT_N sees ~54 V in PSE mode): either a >=60 V FET with RDS(on) specified at VGS <= 2.5-3.3 V, or drive its gate from +12V through a small NPN/NFET level shifter with a gate clamp.

RISK | PA0 VIN_SENSE, U10 IN- | VIN_SENSE has no capacitor and is shared by the ADC and the TLV7011 (260 ns propagation). The ADC sample cap (~8 pF, DS ADC table) is left at the previous channel's voltage; sampleAnalog() reads PA0 right after 32 FAN_SENSE reads (~0.05 V). With ~10 pF on the node the kickback can pull VIN_SENSE from ~2.4 V toward ~1.4 V for ~0.2 us, below BK_REF 1.65 V, so BK_ON can pulse and Q8 can switch on for ~200 us (R80 100k recharge) every 50 ms. Estimate, not measured. | Fix: add 1 nF VIN_SENSE to GND at U10/PA0, or feed PA0 through 10k + 1 nF so the kickback never reaches the comparator.

RISK | firmware build config | (a) If the build does not define USBCON + USBD_USE_CDC ("CDC, generic Serial supersedes U(S)ART"), `Serial` is USART4 on PA0 TX / PA1 RX (variant_generic.h SERIAL_UART_INSTANCE 4, PIN_SERIAL_TX PA0). Serial.begin() would then drive VIN_SENSE, which is also the battery comparator input. (b) `Serial1` only exists with -DENABLE_HWSERIAL1 (WSerial.h); without it the sketch does not compile. | Fix: commit the platformio.ini with `-DUSBCON -DUSBD_USE_CDC -DENABLE_HWSERIAL1` and check the map file that USART4 is not initialised.

RISK | D30/D31, Adafruit_NeoPixel on PA8 | The STM32 path of Adafruit_NeoPixel sets T0H = F_CPU/2500000 = 0.4 us plus SysTick polling latency (Adafruit_NeoPixel.cpp, ARDUINO_ARCH_STM32 branch). WS2812B-4020 datasheet: T0H 220-380 ns. Out of spec; most parts still decode, some will read 0 as 1. | Fix: bench-check with a scope at U30.4 on the first boards; if colours are wrong, drive PA8 from TIM1_CH1 (AF2, legal on PA8) + DMA with T0H ~300 ns.

RISK | J13 pin 2 (LED_D2) | D31 DOUT goes straight out to a wire harness with no series resistor and no ESD part; a hot-plugged or shorted lid cable hits the D31 output directly. J13 pin 1 is unfused +5V (also the AHCT and MCU LDO rail). | Fix: 100-330R in series at J13.2; optionally a PTC or 0R + fuse on J13.1.

RISK | Q8 (outside this section, pass to battery reviewer) | Q8 AOD4185 is P-ch with S = PACK_F, D = +12V, so its body diode conducts from +12V into the pack. When the CR123A pack rests below ~11.3 V (12.0 V buck minus a diode drop), the 12 V buck charges lithium primary cells. The self-test then reads the rail through the diode instead of the pack. | Fix: back-to-back P-FETs (common source) or a series ideal diode so nothing flows into the pack.

RISK | FAN_SENSE (R104 1R, R105 10k, C113 10n), firmware fanStalled | 10k/10n is fc = 1.6 kHz. 25 kHz PWM ripple left after the filter is ~10 mV p-p at 50 % for a 0.1 A fan, and the stall threshold is 20 mV. Whether commutation ripple of a spinning 30 mm fan clears 20 mV is unknown. Hardware is correct; the threshold is a guess. | Fix: log fanRipple spinning vs held on the first board and set the threshold between them.

NOTE | U40 LCSC | C2969805 is STM32F072CBT6TR with 0 JLC stock (script comment says consign). JLC API today: C81720 (STM32F072CBT6 tray, genuine ST) 1997 in stock. | Fix: use C81720 and skip consignment.

NOTE | CH224A I2C (PB10/PB11) | CH224 v2.0 5.2.3: 7-bit address is "0x22 or 0x23"; firmware tries only 0x22. Reg 0x50 unit is 50 mA (datasheet), so the firmware TODO is answered and `cur * 0.05f` is correct. Regs 0x60-0x8F (PDO list) are CH224Q only, so the spec's "source's PDO list" is not available on CH224A. No external pull-ups: MCU INPUT_PULLUP (~40k) + CH224A internal PU is enough at ~50 kHz. | Fix: probe 0x23 if 0x22 NACKs; optional 10k pull-up footprints to +3V3 (datasheet allows 3.3 V).

NOTE | PA8 LED_DATA at reset/DFU | PA8 is a floating input until leds.begin(); the AHCT A input floats (TI note 3: inputs must not float). Only glitches the LEDs. | Fix: 100k LED_DATA to GND.

NOTE | ADC inputs without caps (PA1 PACK_SENSE, PA2 PASSIVE_IMON, PA7 DCIN_SENSE) | Source impedance 10-12k, STM32duino F0 sampling time is 13.5 cycles (analog.cpp chain). DS RAIN formula gives ~11-13k max, so readings are marginal by a few LSB. | Fix: 10 nF at each pin (IMON too; it feeds the 1.3 A backfeed decision from one sample).

NOTE | VDDA (R112 10R, C134 1u, C135 10n) | Matches DS 3.5.1 / Fig. 13 (10 nF + 1 uF). DS requires VDDA >= VDD and first; with 10R VDDA sits a few mV below VDD and lags ~10 us. Common practice, low risk. | Fix (optional): R112 -> ferrite bead or 0R.

NOTE | USB self-powered | J12 VBUS goes only to U52 pin 5 and C143 (10 uF = USB max). No VBUS sense, so the D+ pull-up is on with no host (USB back-drive rule) and USBLC6 lifts USB_VBUS to ~2.7 V through its diode. Works in practice. | Fix (optional): VBUS divider to a spare pin (PB0/PB9) and connect/disconnect the pull-up in firmware.

NOTE | DFU mode (BOOT0) | The F072 system bootloader also listens on USART1 PA9/PA10 (AN2606, from memory, re-check). PA9 = LAPTOP_ILIM_PWM (LAPTOP_EN still held off by R92), PA10 = BK_KILL: an internal pull-up against R89 100k could drive Q10 on and cut the pack while in DFU. Harmless off-battery. | Fix: none needed; do not enter DFU on battery.

NOTE | J9 SWD | No NRST pin, so "connect under reset" is not possible. Firmware never remaps PA13/PA14 and DFU is the primary path, so recovery is still possible. | Fix (optional): 5-pin header with NRST.

NOTE | spec.md | Says STM32F072C8T6; schematic and script say CBT6 (128 KB, needed). | Fix: correct spec.md.

## Verified correct

- Every U40 pin against DS Table 13 LQFP48 column: 1 VBAT, 2-4 PC13-15, 5/6 PF0/PF1, 7 NRST, 8 VSSA, 9 VDDA, 10-17 PA0-PA7, 18/19 PB0/PB1, 20 PB2, 21/22 PB10/11, 23 VSS, 24 VDD, 25-28 PB12-15, 29-33 PA8-PA12, 34 PA13, 35 VSS, 36 VDDIO2, 37 PA14, 38 PA15, 39-43 PB3-PB7, 44 BOOT0, 45/46 PB8/9, 47 VSS, 48 VDD. All VSS on GND; VDD 24/48, VDDIO2 36 and VBAT on +3V3. VDDIO2 = 3.3 V meets USB VDDIO2 >= 3.0 V (DS Table 70). PF0/PF1, PC13-15, PA15, PB0, PB9 unconnected: fine with HSI48.
- Decoupling: 3x 100n (C131-133) for the three VDD/VDDIO2 pins + 4.7u C130; VDDA 1u + 10n. NRST 100n C136 + SW1 to GND. BOOT0 R111 10k to GND, SW2 to +3V3.
- Every firmware pin constant matches the schematic net on that pin (all 24 checked). AFs vs DS Tables 14/15: PA6 AF1 TIM3_CH1, PA9 AF2 TIM1_CH2, PB6/PB7 AF0 USART1 (also in STM32duino PeripheralPins), PB10/PB11 AF1 I2C2 (not used, bit-banged), PA8 AF2 TIM1_CH1 (available). ADC channels PA0-PA7 = IN0-IN7, PB1 = IN9. TIM3 ARR 1919 = 25 kHz, TIM1 ARR 2399 = 20 kHz at 48 MHz; OC1M/OC2M bit positions, CCxE, TIM1 MOE correct.
- Scaling: VIN/DCIN 100k/14k = 8.143 matches; 26 V -> 3.19 V, under 3.3 V. IMON 78.28 uA/A x 10k = 0.783 V/A (TPS2660 GAIN(IMON)) matches 0.78. INA180A1 20 x 20 mR = 0.4 V/A, INA180A2 50 x 20 mR = 1 V/A match. NTC: NCP18XH103 is B25/50 3380 (XH code); divider maths and the 10k-top/NTC-bottom orientation match the firmware.
- Reset-state pulls: BOOST_SD up (R26), PASSIVE_EN (R63), PSE_EN (R78 via R77), TEST_LOAD (R100), LAPTOP_EN (R92), FAN_G (R101), BK_KILL (R89) down.
- USB: PA11 -> USB_D- -> U52.6/1 -> J12 A7/B7; PA12 -> USB_D+ -> U52.4/3 -> J12 A6/B6. USBLC6-2SC6 pinout (1/6 I/O1, 2 GND, 3/4 I/O2, 5 VBUS) matches the ST datasheet. CC1/CC2 each 5.1k to GND (R122/R123). No series resistors needed (internal transceiver, internal 1.5k D+ pull-up). HRO footprint pads A9/A12/B9/B12 overlap B4/B1/A4/A1 and carry the right nets in the PCB.
- U30 SN74AHCT1G125 DBV: 1 OE, 2 A, 3 GND, 4 Y, 5 VCC (TI); OE active low, tied to GND = enabled. VIH 2.0 V at 5 V, so 3.3 V drive is fine. VOH >= 3.8 V at 8 mA vs WS2812B-4020 VIH 2.7 V.
- WS2812B-4020: pin table 1 DIN, 2 VDD, 3 DOUT, 4 VSS; LCSC footprint pad order 1..4 at 0.84-0.86 mm pitch matches the datasheet land pattern (4-3-2-1 left to right). Chain U30 -> D30 -> D31 -> J13 correct; firmware pixel 0/1/2/3 = D30/D31/lid/lid, LED_COUNT 4. +5V = 1.0 x (1 + 100/24.9) = 5.02 V, inside 3.7-5.3 V. 100n on U30, D30, D31.
- Fan: D32 K on +12V, A on FAN_N (correct flyback); AO3400A VGS(th) max 1.45 V, fine at 3.3 V; PWM polarity (mode 1, CCR = duty) turns the FET on for duty.
- Firmware: I2C bit-bang is open-drain style (never drives high). USB CDC write does not block without a host (CDC_connected timeout). Watchdog 2 s vs ~1 s self-test.

## Not verified

- DS Figure 13 text is garbled in the PDF (font encoding). Decoupling values above are from DS 3.5.1 plus memory of Fig. 13 (VDD n x 100 nF + 4.7 uF, VDDIO2 100 nF + 4.7 uF, VDDA 10 nF + 1 uF). Re-check the figure visually.
- Cap placement next to each pin, USB pair routing, lens direction of the 4020 LEDs (layout, not netlist).
- AN2606 bootloader pin states (from memory).
- Fan ripple amplitude and real WS2812B-4020 decode threshold: bench only.
