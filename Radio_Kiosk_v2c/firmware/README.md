# Radio kiosk v2 firmware

STM32F072CBT6, Arduino (STM32duino) through PlatformIO.

```
uvx --from platformio pio run              # build
uvx --from platformio pio run -t upload    # USB DFU: hold BOOT0, tap RESET first
uvx --from platformio pio device monitor   # or any terminal at 115200 on the USB-C or J11
```

## What it does

- **Radio port.** Enables the PSE first (boost on, LTC4279 out of reset). If
  the LTC4279 powers the port within 3 s the radio is in 802.3at mode. If not,
  the PSE and boost go off and the eFuse puts passive 12 V on the port. The
  two are never on together. Passive current above 1.3 A, or an eFuse fault,
  is reported as backfeed. Ten seconds of no current in passive mode goes back
  to detection.
- **Battery.** The comparator closes the pack FET on its own when the input
  drops below 13.4 V. Firmware opens it again (`BK_KILL`) after 2 s with no
  radio load, or after the cap (5 min, `cap <s>`), and only re-arms when the
  input returns. Self-test at boot and every 24 h: two 200 ms pulses into the
  12 R dump, the second reading counts; below 10 V loaded the pack is flagged.
- **Laptop rail.** On when the source is a DC brick or a USB-C PD source that
  granted 20 V, off on battery. The constant-current limit is
  (granted current − 0.8 A for the box) × 20 / 15.6 × 0.9, capped at 3 A,
  halved above 70 °C, off above 85 °C. `limit <A>` caps it by hand,
  `laptop off` disables the rail.
- **PD.** CH224A read over bit-banged I2C (0x22): status register 0x09 and
  the granted-level current in 0x50. The unit of 0x50 is assumed to be 50 mA
  per count until checked against a known charger.
- **Fan.** Off below 40 °C, 40 % at 40 °C rising to 100 % at 70 °C, 25 kHz.
  A stall is a flat shunt voltage while the fan is commanded on.
- **LEDs.** D30 (power inputs): green 20 V, amber 14-18 V, red 5 V, blinking
  amber on battery, blinking red overheat, red/blue alternating pack failed.
  D31 (radio): blue active, green passive with load, white blink detecting,
  red nothing, fast red backfeed; blinking while on battery.

## Serial

A JSON line every 500 ms on both ports:

```
{"t":12345,"vin":19.98,"dcin":0.12,"pack":12.61,"pack_loaded":11.9,"pack_ok":true,
 "battery":false,"mode":"passive","passive_a":0.62,"backfeed":false,"usb_a":1.4,
 "pd_ok":true,"pd_status":2,"pd_max_a":3.25,"laptop":true,"laptop_a":2.1,
 "laptop_limit_a":2.2,"temp_c":41.5,"fan":43,"fan_stalled":false}
```

Commands: `laptop on`, `laptop off`, `limit <A>`, `cap <s>`, `test`,
`redetect`, `help`.

## Not yet verified on hardware

Every scaling factor (dividers, IMON, INA180 gains, NTC constants), the
CH224A register unit, the PSE timing, the WS2812B-4020 lens direction, and
whether the Toughbook backs off on a current-limited supply.
