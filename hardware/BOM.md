# Bill of Materials

| Component | Value / Part | Notes |
|-----------|--------------|-------|
| Microcontroller | Elegoo Mega2560 (ATmega2560) | Any ATmega2560 board with Timer 3 on OC3A (Pin 5) |
| IR LED | TSAL6200 or similar | 940 nm, forward voltage ~1.3 V |
| NPN Transistor | 2N2222 or 2N3904 | For driving the LED |
| Base Resistor | 1 kΩ | Limits GPIO current into transistor base |
| Current‑Limiting Resistor | 100 Ω | In series with IR LED, value depends on supply voltage |
| Power Supply | 5 V (USB) | Powers the Mega2560 |
| Jumper Wires | – | For breadboard connections |
