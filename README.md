# PCjr Infrared Keyboard Emulator

A USB‑to‑IR keyboard adapter for the 1983 IBM PCjr, built on an Elegoo Mega2560 (ATmega2560).  
Transmits precise 40 kHz biphase‑Manchester encoded scan codes, verified against original hardware.

## Features
- Cycle‑accurate 40 kHz carrier generation using hardware Timer 3 in CTC mode  
- Full PC/XT Set 1 scan code support, including make/break codes  
- 62.5 µs carrier bursts matching the original IBM PCjr Technical Reference  
- Tested and validated – character‑perfect output, zero error beeps  

## Hardware
- Elegoo Mega2560 (ATmega2560)  
- IR LED driver circuit (NPN transistor, current‑limiting resistor)  
- Analog oscilloscope for verification  

See [`hardware/`](hardware/) for schematic, BOM, and pin mapping.

## Firmware
The AVR C code is in [`firmware/`](firmware/). Key parameters:

| Parameter | Value |
|-----------|-------|
| Carrier frequency | 40 kHz (12 µs on / 13 µs off) |
| Burst duration | 62.5 µs |
| Start bit silence | 310 µs |
| Logic 1 silence | 377.5 µs |
| Logic 0 silence (first half) | 220 µs |
| Logic 0 silence (second half) | 157.5 µs |
| Stop bit silence | 4840 µs (11 extra stop bits) |

## Protocol
The PCjr infrared keyboard uses **biphase Manchester encoding** at 440 µs per bit.  
Full details in [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

## Reverse Engineering
The protocol was recovered through a forensic, lemma‑based approach.  
Read the dev log at [`docs/DEVLOG.md`](docs/DEVLOG.md) for the full story.

## Quick Start
1. Flash `firmware/pcjr_tx.ino` to your Elegoo Mega2560.
2. Connect the IR LED driver circuit as shown in `hardware/schematic.png`.
3. Power on the PCjr. Open a serial terminal at 600 baud.
4. Type characters – they appear on the PCjr!

## Repository Structure
- `firmware/` – AVR C transmitter code  
- `hardware/` – schematics, BOM, pin map  
- `docs/` – protocol spec, dev log, lessons learned, scope captures  
- `tools/` – Python test scripts (pigpio sweeps)  

## License
MIT – see `LICENSE`.
