/*
 * outlet_control.h
 * ---------------
 * Self‑contained 433 MHz outlet control module.
 * Dependencies: RCSwitch library.
 *
 * Usage:
 *   #include "outlet_control.h"
 *   setupOutlets();              // use defaults
 *   sendOutletCommand(2, true);   // turn outlet #2 ON
 *
 * Extensible: just add more codes to the arrays and NUM_OUTLETS updates
 * automatically.
 */

#ifndef OUTLET_CONTROL_H
#define OUTLET_CONTROL_H

#include <RCSwitch.h>

// ---------- User‑editable code tables ----------
const unsigned long ON_CODES[] = {
  0x2F35A,   // 1  UNKNOWN
  0x2F35AA,  // 2  PCJrduino
  0x2F35A,   // 3  UNKNOWN
  0x2F35A,   // 4  UNKNOWN
  0x2F35AB   // 5  Klipptop (3D Printer)
};

const unsigned long OFF_CODES[] = {
  0x2F35A,   // 1  UNKNOWN
  0x2F35A2,  // 2  PCJrduino
  0x2F35A,   // 3  UNKNOWN
  0x2F35A,   // 4  UNKNOWN
  0x2F35A3   // 5  Klipptop (3D Printer)
};

// Auto‑computed array size
const int NUM_OUTLETS = sizeof(ON_CODES) / sizeof(ON_CODES[0]);

// ---------- Transmitter object ----------
RCSwitch myTX;

// ---------- Default parameters ----------
#define TX_PIN         10
#define TX_PROTOCOL    1
#define TX_PULSE_LEN   149
#define TX_REPEATS     15

/*
 * Initialise the transmitter.  Call once after entering RF mode.
 * Defaults match your existing hardware.
 */
void setupOutlets(int pin = TX_PIN, int protocol = TX_PROTOCOL,
                  int pulseLen = TX_PULSE_LEN, int repeats = TX_REPEATS) {
  myTX.enableTransmit(pin);
  myTX.setProtocol(protocol);
  myTX.setPulseLength(pulseLen);
  myTX.setRepeatTransmit(repeats);
}

/*
 * Send an ON (state=true) or OFF (state=false) code for outlet 1..NUM_OUTLETS.
 * Prints human‑readable confirmation to Serial.
 */
void sendOutletCommand(int id, bool state) {
  // -------- Bounds check (fixes old sizeof bug) --------
  if (id < 1 || id > NUM_OUTLETS) {
    Serial.print("ERR BAD ID ");
    Serial.println(id);
    return;
  }

  unsigned long code = state ? ON_CODES[id - 1] : OFF_CODES[id - 1];
  myTX.send(code, 24);                            // 24‑bit code
  Serial.print(id);
  Serial.print(state ? " ON  " : " OFF ");
  Serial.println(code, HEX);
}

#endif