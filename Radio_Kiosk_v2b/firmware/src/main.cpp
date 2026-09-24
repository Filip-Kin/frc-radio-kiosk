// FRC radio kiosk v2 firmware. STM32F072CBT6, Arduino (STM32duino).
//
// What it does, in order of importance:
//   1. Radio port: try 802.3at first (PSE), fall back to passive 12 V.
//      Never both. The boost is only enabled while the PSE is enabled.
//   2. Battery: the comparator closes the pack FET by itself; this code only
//      opens it again (BK_KILL) after 5 s of no radio load or 5 min, and runs
//      the loaded self-test at boot and every 24 h.
//   3. Laptop rail: on when the source can afford it, constant-current limited
//      to (allocation - measured box draw + 10 %) so a shared GaN charger never
//      trips, and derated by temperature.
//   4. Fan, LEDs, and a JSON status line on USB and UART every 500 ms.
//   5. Independent watchdog, 2 s.
//
// Pin map matches the schematic notes in build-radio-kiosk.ts.
#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>
#include <IWatchdog.h>
#include "stm32f0xx.h"

// Flash is 128 kB, but STM32duino's HAL I2C and HardwareTimer are 27 kB, so
// the I2C to the CH224A is bit-banged and the two PWMs talk to the timer
// registers directly.

// #region pins
static const int PIN_VIN_SENSE = PA0;      // 100k/14k: 1.65 V = 13.4 V
static const int PIN_PACK_SENSE = PA1;     // same divider
static const int PIN_PASSIVE_IMON = PA2;   // TPS26600 IMON into 10k: 0.78 V/A
static const int PIN_TEMP_SENSE = PA3;     // 10k / NTC 10k B3380 to GND
static const int PIN_FAN_SENSE = PA4;      // 1R shunt through 10k/10n
static const int PIN_USB_ISENSE = PA5;     // INA180A1 x20 on 20 mR: 0.4 V/A
static const int PIN_DCIN_SENSE = PA7;     // 100k/14k on the DC jack
static const int PIN_LAPTOP_ISENSE = PB1;  // INA180A2 x50 on 20 mR: 1 V/A

static const int PIN_LAPTOP_EN = PB2;
static const int PIN_TEST_LOAD = PB12;
static const int PIN_BOOST_SD = PB13;      // high = boost off (pulled up at reset)
static const int PIN_PASSIVE_EN = PB14;
static const int PIN_PSE_EN = PB15;
static const int PIN_FAN_PWM = PA6;        // TIM3_CH1
static const int PIN_LED_DATA = PA8;       // through the AHCT buffer to two WS2812B-4020
static const int PIN_BK_KILL = PA10;
static const int PIN_LAPTOP_ILIM = PA9;    // TIM1_CH2, filtered: 1 V per amp of limit

static const int PIN_BK_ON = PB3;          // comparator: high = on battery
static const int PIN_PASSIVE_FLT = PB4;    // eFuse fault, active low
static const int PIN_PSE_ON = PB5;         // LTC4279 LED pin, low = port powered
static const int PIN_PD_PG = PB8;          // CH224A PG, low = 20 V granted

// J11 is USART1 on PB6/PB7. STM32duino defaults USART1 to PA9/PA10, which are
// LAPTOP_ILIM and BK_KILL, so the pins are set before Serial1.begin().
static const int PIN_UART_TX = PB6;
static const int PIN_UART_RX = PB7;

static const uint8_t CH224_ADDR = 0x22;

// #region scaling
static const float ADC_V = 3.3f / 4095.0f;
static const float DIV_HV = 114.0f / 14.0f;   // 100k / 14k
static float vinV = 0, packV = 0, dcinV = 0, passiveA = 0, usbA = 0, laptopA = 0, tempC = 25, fanRipple = 0;
static bool tempFault = false;   // NTC open or shorted; tempC holds its last good value

static float readV(int pin) { return analogRead(pin) * ADC_V; }

static void sampleAnalog() {
  vinV = readV(PIN_VIN_SENSE) * DIV_HV;
  packV = readV(PIN_PACK_SENSE) * DIV_HV;
  dcinV = readV(PIN_DCIN_SENSE) * DIV_HV;
  passiveA = readV(PIN_PASSIVE_IMON) / 0.78f;
  usbA = readV(PIN_USB_ISENSE) / 0.4f;
  laptopA = readV(PIN_LAPTOP_ISENSE) / 1.0f;
  float vt = readV(PIN_TEMP_SENSE);
  tempFault = vt < 0.01f || vt > 3.29f;
  if (!tempFault) {
    float r = 10000.0f * vt / (3.3f - vt);
    float invT = 1.0f / 298.15f + logf(r / 10000.0f) / 3380.0f;
    tempC = 1.0f / invT - 273.15f;
  }
  // A spinning fan puts commutation ripple on its shunt; a stalled one is flat.
  float lo = 9, hi = 0;
  for (int i = 0; i < 32; i++) {
    float v = readV(PIN_FAN_SENSE);
    lo = min(lo, v); hi = max(hi, v);
    delayMicroseconds(200);
  }
  fanRipple = hi - lo;
}

// #region radio port state machine
enum PortMode { PORT_IDLE, PORT_DETECT, PORT_ACTIVE, PORT_PASSIVE };
static PortMode port = PORT_IDLE;
static uint32_t portSince = 0;
static bool backfeed = false;

static void portSet(bool pse, bool passive) {
  // Order matters: never have 54 V and the eFuse on together.
  if (!pse) { digitalWrite(PIN_PSE_EN, LOW); digitalWrite(PIN_BOOST_SD, HIGH); }
  if (!passive) digitalWrite(PIN_PASSIVE_EN, LOW);
  delay(5);
  if (passive) digitalWrite(PIN_PASSIVE_EN, HIGH);
  if (pse) { digitalWrite(PIN_BOOST_SD, LOW); delay(50); digitalWrite(PIN_PSE_EN, HIGH); }
}

static bool pseOn() { return digitalRead(PIN_PSE_ON) == LOW; }

static void portTick(uint32_t now) {
  switch (port) {
    case PORT_IDLE:
      // Ask the PSE. It runs detection on its own; if something with a valid
      // signature is there it powers it within a couple of seconds.
      portSet(true, false);
      port = PORT_DETECT; portSince = now;
      break;
    case PORT_DETECT:
      if (pseOn()) { port = PORT_ACTIVE; portSince = now; }
      else if (now - portSince > 3000) { portSet(false, true); port = PORT_PASSIVE; portSince = now; }
      break;
    case PORT_ACTIVE: {
      // PSE_ON must stay high for 500 ms before the port counts as unpowered,
      // so noise on the pin cannot drop the radio.
      static uint32_t offSince = 0;
      if (pseOn()) offSince = 0;
      else if (!offSince) offSince = now;
      if (offSince && now - offSince > 500) { portSet(false, false); port = PORT_IDLE; offSince = 0; }
      break;
    }
    case PORT_PASSIVE: {
      // Backfeed: a robot's PDH wired to the radio's raw leads pulls far more
      // through the port than a radio alone.
      backfeed = passiveA > 1.3f || digitalRead(PIN_PASSIVE_FLT) == LOW;
      static uint32_t noLoadSince = 0;
      if (passiveA < 0.05f) { if (!noLoadSince) noLoadSince = now; }
      else noLoadSince = 0;
      // Nothing drawn for 10 s: the radio is gone, go back and look again.
      if (noLoadSince && now - noLoadSince > 10000 && now - portSince > 15000) { portSet(false, false); port = PORT_IDLE; noLoadSince = 0; }
      break;
    }
  }
}

static bool radioLoaded() {
  return (port == PORT_ACTIVE && pseOn()) || (port == PORT_PASSIVE && passiveA > 0.05f);
}

// #region battery
static bool onBattery = false;
static uint32_t batterySince = 0, noLoadSince = 0;
static bool batteryKilled = false;
static uint32_t batteryCapMs = 300000;   // 5 min hard cap, settable over serial
static bool packOk = true;
static float packLoadedV = 0;
static uint32_t lastSelfTest = 0;

static void batteryTick(uint32_t now) {
  bool bk = digitalRead(PIN_BK_ON) == HIGH;
  if (bk && !onBattery) { batterySince = now; noLoadSince = 0; }
  onBattery = bk;
  if (!bk) { batteryKilled = false; digitalWrite(PIN_BK_KILL, LOW); return; }
  if (batteryKilled) return;
  if (!radioLoaded()) { if (!noLoadSince) noLoadSince = now; } else noLoadSince = 0;
  // 5 s is longer than the 3 s PSE detect window, so a port restart on
  // battery does not cut the pack before the radio is powered again.
  bool cut = (noLoadSince && now - noLoadSince > 5000) || (now - batterySince > batteryCapMs);
  if (cut) { digitalWrite(PIN_BK_KILL, HIGH); batteryKilled = true; }
}

// Two 200 ms pulses into the 12R dump; the first wakes lithium primaries from
// passivation, the second is the reading. Below 10 V loaded: replace the set.
static void selfTest(uint32_t now) {
  if (onBattery) return;
  for (int i = 0; i < 2; i++) {
    digitalWrite(PIN_TEST_LOAD, HIGH);
    delay(180);
    packLoadedV = readV(PIN_PACK_SENSE) * DIV_HV;
    delay(20);
    digitalWrite(PIN_TEST_LOAD, LOW);
    delay(300);
  }
  packOk = packLoadedV > 10.0f;
  lastSelfTest = now;
}

// #region PD sink (CH224A over I2C)
struct PdInfo { bool ok; uint8_t status; uint8_t currentReg; float maxA; };
static PdInfo pd = { false, 0, 0, 0 };

// #region bit-banged I2C on PB10 (SCL) / PB11 (SDA), ~50 kHz, open-drain
static const int PIN_SCL = PB10, PIN_SDA = PB11;
static inline void sclHi() { pinMode(PIN_SCL, INPUT_PULLUP); }
static inline void sclLo() { pinMode(PIN_SCL, OUTPUT); digitalWrite(PIN_SCL, LOW); }
static inline void sdaHi() { pinMode(PIN_SDA, INPUT_PULLUP); }
static inline void sdaLo() { pinMode(PIN_SDA, OUTPUT); digitalWrite(PIN_SDA, LOW); }
static inline void i2cDelay() { delayMicroseconds(5); }
static void i2cStart() { sdaHi(); sclHi(); i2cDelay(); sdaLo(); i2cDelay(); sclLo(); i2cDelay(); }
static void i2cStop() { sdaLo(); i2cDelay(); sclHi(); i2cDelay(); sdaHi(); i2cDelay(); }
static bool i2cWrite(uint8_t b) {
  for (int i = 7; i >= 0; i--) { if (b & (1 << i)) sdaHi(); else sdaLo(); i2cDelay(); sclHi(); i2cDelay(); sclLo(); }
  sdaHi(); i2cDelay(); sclHi(); i2cDelay();
  bool ack = digitalRead(PIN_SDA) == LOW;
  sclLo(); i2cDelay();
  return ack;
}
static uint8_t i2cRead(bool ack) {
  uint8_t v = 0;
  sdaHi();
  for (int i = 0; i < 8; i++) { sclHi(); i2cDelay(); v = (v << 1) | (digitalRead(PIN_SDA) == HIGH ? 1 : 0); sclLo(); i2cDelay(); }
  if (ack) sdaLo(); else sdaHi();
  i2cDelay(); sclHi(); i2cDelay(); sclLo(); sdaHi(); i2cDelay();
  return v;
}
static bool ch224Read(uint8_t reg, uint8_t &val) {
  i2cStart();
  bool ok = i2cWrite(CH224_ADDR << 1) && i2cWrite(reg);
  if (ok) { i2cStart(); ok = i2cWrite((CH224_ADDR << 1) | 1); if (ok) val = i2cRead(false); }
  i2cStop();
  return ok;
}

static void pdTick() {
  uint8_t st = 0, cur = 0;
  pd.ok = ch224Read(0x09, st) && ch224Read(0x50, cur);
  pd.status = st;
  pd.currentReg = cur;
  // The datasheet calls 0x50 "maximum current available under the current PD
  // gear". Its unit is not stated in the text we have; 50 mA per count is the
  // usual PD granularity. TODO: confirm on hardware against a known charger.
  pd.maxA = pd.ok ? cur * 0.05f : 0;
}

// #region PWM on the timer registers
// TIM3_CH1 on PA6 (AF1) for the fan at 25 kHz; TIM1_CH2 on PA9 (AF2) for the
// laptop current limit at 20 kHz into its RC filter. 48 MHz timer clock.
static void pwmInit() {
  RCC->AHBENR |= RCC_AHBENR_GPIOAEN;
  RCC->APB1ENR |= RCC_APB1ENR_TIM3EN;
  RCC->APB2ENR |= RCC_APB2ENR_TIM1EN;
  // PA6 -> AF1 (TIM3_CH1), PA9 -> AF2 (TIM1_CH2)
  GPIOA->MODER = (GPIOA->MODER & ~((3u << (6 * 2)) | (3u << (9 * 2)))) | (2u << (6 * 2)) | (2u << (9 * 2));
  GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFu << (6 * 4))) | (1u << (6 * 4));
  GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << ((9 - 8) * 4))) | (2u << ((9 - 8) * 4));
  TIM3->PSC = 0; TIM3->ARR = 1919; TIM3->CCR1 = 0;            // 48 MHz / 1920 = 25 kHz
  TIM3->CCMR1 = (6u << 4) | TIM_CCMR1_OC1PE;                    // PWM mode 1
  TIM3->CCER = TIM_CCER_CC1E; TIM3->CR1 = TIM_CR1_ARPE | TIM_CR1_CEN;
  TIM1->PSC = 0; TIM1->ARR = 2399; TIM1->CCR2 = 0;            // 20 kHz
  TIM1->CCMR1 = (6u << 12) | TIM_CCMR1_OC2PE;
  TIM1->CCER = TIM_CCER_CC2E; TIM1->BDTR = TIM_BDTR_MOE; TIM1->CR1 = TIM_CR1_ARPE | TIM_CR1_CEN;
}
static void fanPwm(int percent) { TIM3->CCR1 = (uint32_t)(constrain(percent, 0, 100) * 1919L / 100); }
static void laptopLimitPwm(float volts) { TIM1->CCR2 = (uint32_t)(constrain(volts / 3.3f, 0.0f, 1.0f) * 2399); }

// #region laptop rail
static bool laptopWanted = true;      // serial "laptop off" clears it
static float laptopLimitA = 3.0f;
static float laptopLimitManual = 0;   // >0 overrides the computed limit
static bool laptopOn = false;
static float boxA = 0;                // measured draw of everything but the laptop, at 20 V

static void laptopTick() {
  bool dcIn = dcinV > 13.5f;
  bool usbIn = digitalRead(PIN_PD_PG) == LOW;
  bool sourceOk = vinV > 13.5f && (dcIn || usbIn);
  float limit = 3.0f;
  if (!dcIn && usbIn) {
    // Budget: the charger's allocation minus what the box draws right now,
    // plus 10 %. The box draw is the USB input minus the laptop's share of it
    // (15.6 V out, ~90 % efficient), so nothing is held back for a radio that
    // is not plugged in.
    float allocA = pd.ok && pd.maxA > 0.5f ? pd.maxA : 3.25f;   // 65 W if we cannot read it
    float laptopInA = laptopA * 15.6f / 20.0f / 0.9f;
    boxA = max(0.1f, usbA - laptopInA);
    limit = max(0.0f, (allocA - boxA * 1.1f) * 20.0f / 15.6f * 0.9f);
  }
  // A dead NTC leaves tempC stale; the fan covers it, the laptop keeps running.
  if (!tempFault) {
    if (tempC > 85) limit = 0;
    else if (tempC > 70) limit *= 0.5f;
  }
  if (laptopLimitManual > 0) limit = min(limit, laptopLimitManual);
  laptopLimitA = min(limit, 3.0f);
  laptopOn = laptopWanted && sourceOk && !onBattery && laptopLimitA > 0.2f;
  digitalWrite(PIN_LAPTOP_EN, laptopOn ? HIGH : LOW);
  laptopLimitPwm(laptopLimitA);   // 1 V per amp
}

// #region fan
static int fanDuty = 0;
static bool fanStalled = false;
static void fanTick() {
  int duty = 0;
  if (onBattery) duty = 0;
  else if (tempFault) duty = 100;
  else if (tempC > 40) duty = (int)constrain((tempC - 40.0f) / 30.0f * 60.0f + 40.0f, 40.0f, 100.0f);
  fanDuty = duty;
  fanPwm(duty);
  fanStalled = duty > 30 && fanRipple < 0.02f;
}

// #region LEDs
// Two side emitters on the board, then J13 for two more on the lid (WS2812B
// carriers on a wire). The lid pair mirrors the side pair.
static const int LED_COUNT = 4;
Adafruit_NeoPixel leds(LED_COUNT, PIN_LED_DATA, NEO_GRB + NEO_KHZ800);
static const uint32_t OFF = 0, RED = 0x400000, GREEN = 0x004000, BLUE = 0x000040, AMBER = 0x402000, WHITE = 0x303030;

static void ledTick(uint32_t now) {
  bool blink = (now / 400) & 1;
  bool fast = (now / 150) & 1;
  // D30, power side.
  uint32_t p;
  if (!packOk) p = fast ? RED : BLUE;
  else if (!tempFault && tempC > 85) p = blink ? RED : OFF;
  else if (onBattery) p = blink ? AMBER : OFF;
  else if (vinV > 18) p = GREEN;
  else if (vinV > 13.5f) p = AMBER;
  else if (vinV > 4) p = RED;
  else p = OFF;
  // D31, radio side.
  uint32_t r;
  if (backfeed) r = fast ? RED : OFF;
  else if (port == PORT_ACTIVE) r = BLUE;
  else if (port == PORT_PASSIVE && passiveA > 0.05f) r = GREEN;
  else if (port == PORT_DETECT) r = blink ? WHITE : OFF;
  else r = RED;
  if (onBattery && !batteryKilled) r = blink ? r : OFF;
  leds.setPixelColor(0, p);
  leds.setPixelColor(1, r);
  leds.setPixelColor(2, p);   // lid, power side
  leds.setPixelColor(3, r);   // lid, radio side
  leds.show();
}

// #region serial
static bool wdtReset = false;   // last reset came from the watchdog

static const char *modeName() {
  switch (port) { case PORT_IDLE: return "idle"; case PORT_DETECT: return "detect"; case PORT_ACTIVE: return "active"; default: return "passive"; }
}

static void statusLine(Stream &s) {
  JsonDocument doc;
  doc["t"] = millis();
  doc["vin"] = serialized(String(vinV, 2));
  doc["dcin"] = serialized(String(dcinV, 2));
  doc["pack"] = serialized(String(packV, 2));
  doc["pack_loaded"] = serialized(String(packLoadedV, 2));
  doc["pack_ok"] = packOk;
  doc["battery"] = onBattery;
  doc["mode"] = modeName();
  doc["passive_a"] = serialized(String(passiveA, 3));
  doc["backfeed"] = backfeed;
  doc["usb_a"] = serialized(String(usbA, 3));
  doc["box_a"] = serialized(String(boxA, 3));
  doc["pd_ok"] = pd.ok;
  doc["pd_status"] = pd.status;
  doc["pd_max_a"] = serialized(String(pd.maxA, 2));
  doc["laptop"] = laptopOn;
  doc["laptop_a"] = serialized(String(laptopA, 3));
  doc["laptop_limit_a"] = serialized(String(laptopLimitA, 2));
  doc["temp_c"] = serialized(String(tempC, 1));
  doc["temp_fault"] = tempFault;
  doc["fan"] = fanDuty;
  doc["fan_stalled"] = fanStalled;
  doc["wdt_reset"] = wdtReset;
  serializeJson(doc, s);
  s.println();
}

static void command(char *line, Stream &s) {
  if (!strcmp(line, "laptop on")) laptopWanted = true;
  else if (!strcmp(line, "laptop off")) laptopWanted = false;
  else if (!strncmp(line, "limit ", 6)) laptopLimitManual = atof(line + 6);
  else if (!strncmp(line, "cap ", 4)) batteryCapMs = (uint32_t)atol(line + 4) * 1000UL;
  else if (!strcmp(line, "test")) selfTest(millis());
  else if (!strcmp(line, "redetect")) { portSet(false, false); port = PORT_IDLE; }
  else if (!strcmp(line, "help")) s.println("laptop on|off, limit <A>, cap <s>, test, redetect");
  else { s.print("? "); s.println(line); return; }
  s.println("ok");
}

struct LineBuf { char b[64]; uint8_t n; };
static void pollSerial(Stream &s, LineBuf &buf) {
  while (s.available()) {
    char c = s.read();
    if (c == '\n' || c == '\r') { if (buf.n) { buf.b[buf.n] = 0; command(buf.b, s); } buf.n = 0; }
    else if (buf.n < sizeof(buf.b) - 1) buf.b[buf.n++] = c;
  }
}

// #region setup / loop
static LineBuf usbBuf = {{0}, 0}, uartBuf = {{0}, 0};

void setup() {
  // Everything off before anything is measured.
  pinMode(PIN_BOOST_SD, OUTPUT); digitalWrite(PIN_BOOST_SD, HIGH);
  pinMode(PIN_PSE_EN, OUTPUT); digitalWrite(PIN_PSE_EN, LOW);
  pinMode(PIN_PASSIVE_EN, OUTPUT); digitalWrite(PIN_PASSIVE_EN, LOW);
  pinMode(PIN_LAPTOP_EN, OUTPUT); digitalWrite(PIN_LAPTOP_EN, LOW);
  pinMode(PIN_TEST_LOAD, OUTPUT); digitalWrite(PIN_TEST_LOAD, LOW);
  pinMode(PIN_BK_KILL, OUTPUT); digitalWrite(PIN_BK_KILL, LOW);
  pwmInit();
  pinMode(PIN_BK_ON, INPUT);
  pinMode(PIN_PASSIVE_FLT, INPUT_PULLUP);
  pinMode(PIN_PSE_ON, INPUT_PULLUP);
  pinMode(PIN_PD_PG, INPUT_PULLUP);
  analogReadResolution(12);

  Serial.begin(115200);   // USB CDC
  Serial1.setRx(PIN_UART_RX);
  Serial1.setTx(PIN_UART_TX);
  Serial1.begin(115200);  // UART on J11
  sclHi(); sdaHi();
  leds.begin(); leds.show();

  delay(200);
  sampleAnalog();
  selfTest(millis());

  // 2 s: longer than the ~1 s self-test, the longest block in loop().
  wdtReset = IWatchdog.isReset(true);
  IWatchdog.begin(2000000);
}

void loop() {
  static uint32_t lastFast = 0, lastSlow = 0;
  IWatchdog.reload();
  uint32_t now = millis();
  pollSerial(Serial, usbBuf);
  pollSerial(Serial1, uartBuf);
  if (now - lastFast >= 50) {
    lastFast = now;
    sampleAnalog();
    portTick(now);
    batteryTick(now);
    laptopTick();
    ledTick(now);
  }
  if (now - lastSlow >= 500) {
    lastSlow = now;
    pdTick();
    fanTick();
    statusLine(Serial);
    statusLine(Serial1);
    if (now - lastSelfTest > 86400000UL) selfTest(now);
  }
}