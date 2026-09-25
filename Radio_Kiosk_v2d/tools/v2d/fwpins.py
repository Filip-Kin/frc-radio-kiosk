"""Write the MCU pin map (net -> LQFP-48 pin number) into firmware main.cpp.
Usage: fwpins.py pins.json main.cpp"""
import json, re, sys
PORT = {2: "PC13", 3: "PC14", 4: "PC15", 5: "PF0", 6: "PF1", **{10 + i: f"PA{i}" for i in range(8)},
        18: "PB0", 19: "PB1", 20: "PB2", 21: "PB10", 22: "PB11", 25: "PB12", 26: "PB13", 27: "PB14", 28: "PB15",
        29: "PA8", 30: "PA9", 31: "PA10", 32: "PA11", 33: "PA12", 34: "PA13", 37: "PA14", 38: "PA15",
        39: "PB3", 40: "PB4", 41: "PB5", 42: "PB6", 43: "PB7", 45: "PB8", 46: "PB9"}
CONST = {"LAPTOP_ILIM_PWM": "LAPTOP_ILIM"}
pins = json.load(open(sys.argv[1])); src = open(sys.argv[2]).read()
for net, pin in pins.items():
    port = PORT[int(pin)]
    if net in ("PD_SCL", "PD_SDA"):
        name = "PIN_SCL" if net == "PD_SCL" else "PIN_SDA"
        src, n = re.subn(rf"({name} = )P[A-F]\d+", rf"\g<1>{port}", src)
    else:
        name = "PIN_" + CONST.get(net, net)
        src, n = re.subn(rf"(static const int {name} = )P[A-F]\d+", rf"\g<1>{port}", src)
    if n != 1: sys.exit(f"{net}: {n} matches for {name}")
scl, sda = PORT[int(pins["PD_SCL"])], PORT[int(pins["PD_SDA"])]
src = re.sub(r"// #region bit-banged I2C on \S+ \(SCL\) / \S+ \(SDA\)", f"// #region bit-banged I2C on {scl} (SCL) / {sda} (SDA)", src)
open(sys.argv[2], "w").write(src)
print("firmware pins:", {n: PORT[int(p)] for n, p in pins.items()})
