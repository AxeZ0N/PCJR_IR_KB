/*
 * pcjr_ir_bridge.ino
 * ------------------
 * Receives PCjr scan codes over serial (600 baud) and transmits them
 * via an infrared LED using the PCjr's wireless keyboard protocol.
 *
 * Hardware:
 *   - Arduino Mega 2560 (or compatible ATmega2560 board)
 *   - IR LED + 100 Ω resistor connected between pin 5 and GND
 *     (active‑low: HIGH = LED off, LOW = LED on)
 *
 * How it works:
 *   Serial.read() provides raw scan codes (one byte per keystroke).
 *   The sketch Manchester‑encodes each byte with odd parity and
 *   modulates a 40 kHz carrier on pin 5 (Port E, bit 3).
 *
 * Timing (all values in microseconds, from PCjr Technical Reference):
 *   - Burst duration:       62.5  (carrier ON)
 *   - Logic 1 silence:     377.5  (carrier OFF for "1" bit)
 *   - Logic 0 silence 1:   220.0  (carrier OFF, first half of "0")
 *   - Logic 0 silence 2:   157.5  (carrier OFF, second half of "0")
 *   - Start bit silence:   310    (after start burst)
 *   - Inter‑byte gap:     4840    (10 stop bits)
 */

#define __DELAY_ROUND_CLOSEST__   // required for floating‑point _delay_us()
#include <util/delay.h>
#include "PowerPCJr.h"

// --- Pin definitions ---
const int irPin = 5;            // PE3 on ATmega2560

// --- Manchester encoding parameters (µs, must be #define) ---
#define BURST_DURATION     62.5
#define LOGIC_1_SILENCE   377.5
#define LOGIC_0_SILENCE_1 220.0
#define LOGIC_0_SILENCE_2 157.5
#define START_BIT_SILENCE 310
#define INTER_BYTE_GAP    4840

// --- 40 kHz carrier generation with Timer 3 ---
#define TIMER3_TOP  24   // 16 MHz / (2 * 40 kHz) / 8 - 1 = 24

void setup() {
  Serial.begin(600);
	setup_PowerPCJr();

  pinMode(irPin, OUTPUT);
  // Idle state: HIGH = IR LED off (active‑low circuit)
  PORTE |= (1 << 3);             // force pin high

  // Configure Timer 3 for CTC mode, prescaler /8 (not started yet)
  TCCR3A = 0;
  TCCR3B = 0;
  TCNT3  = 0;
  OCR3A  = TIMER3_TOP;
  TCCR3B = (1 << WGM32);        // CTC mode, clock stopped
}

// --- Inline functions for carrier control ---
inline void carrierOn() {
  TCCR3A |= (1 << COM3A0);      // toggle pin 5 on each match
  TCCR3B |= (1 << CS31);        // start clock (prescaler /8)
}

inline void carrierOff() {
  TCCR3B &= ~(1 << CS31);       // stop clock
  TCCR3A &= ~(1 << COM3A0);     // disconnect timer from pin
  TCNT3 = 0;                     // reset counter
  PORTE |= (1 << 3);            // force pin HIGH (LED off)
}

// --- Manchester encoding primitives ---
inline void sendOne() {
  carrierOn();   _delay_us(BURST_DURATION);
  carrierOff();  _delay_us(LOGIC_1_SILENCE);
}

inline void sendZero() {
  carrierOff();  _delay_us(LOGIC_0_SILENCE_1);
  carrierOn();   _delay_us(BURST_DURATION);
  carrierOff();  _delay_us(LOGIC_0_SILENCE_2);
}

inline void sendStart() {
  carrierOn();   _delay_us(BURST_DURATION);
  carrierOff();  _delay_us(START_BIT_SILENCE);
}

// --- Transmit a single scan code byte with ODD parity ---
void sendByte(uint8_t data) {
  noInterrupts();               // timing‑critical section

  sendStart();

  uint8_t parity = 0;
  for (uint8_t i = 0; i < 8; ++i) {
    if (data & 1) {
      sendOne();
      ++parity;
    } else {
      sendZero();
    }
    data >>= 1;
  }

  // Odd parity: if number of ones is odd, send 0; else send 1
  if (parity & 1) sendZero();
  else            sendOne();

  interrupts();

  // Inter‑byte gap (10 stop bits = 4840 µs)
  _delay_us(INTER_BYTE_GAP);
}

void loop() {
	digitalWrite(irPin, LOW);
  while (Serial.available()) {
    sendByte(Serial.read());
  }
	digitalWrite(irPin, LOW);
}
