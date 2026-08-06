# PCjr Infrared Keyboard Emulator

A complete USB‑to‑IR keyboard adapter for the 1983 IBM PCjr, built around an Elegoo Mega2560 (ATmega2560).  
Transmits cycle‑accurate 40 kHz biphase‑Manchester encoded scan codes, verified against original hardware.  
Includes a modern Python driver, a unified control script, and optional RTSP camera streaming.

## Features

- **Bit‑perfect IR transmission** – hardware‑timer‑generated 40 kHz carrier with exact 62.5 µs bursts (2.5 carrier cycles), matching the IBM PCjr Technical Reference
- **Full PC/XT Set 1 scan code support** – all printable characters, modifier keys, function keys, arrows, and special combinations (Ctrl+Alt+Del, etc.)
- **Interactive Python driver** (`pcjrduino_tty.py`) – captures raw terminal keystrokes (including escape sequences, hex entry, and file‑injection mode) and converts them to raw scan codes sent over serial
- **Unified control script** (`pcjr.sh`) – a single command to:
  - Install system dependencies and Arduino CLI (`setup`)
  - Configure Arduino cores (`configure`)
  - Compile the firmware (`compile`)
  - Upload to the Mega2560 (`upload` or `cu` for both)
  - Start an RTSP camera viewer (`stream` – uses mpv)
  - Install and start a MediaMTX streaming server (`server-setup`, `server-start`)
- **Camera streaming** – included `mediamtx.yml` for a Raspberry Pi camera at 640×480, 5 fps, viewable anywhere on the network
- **Fully documented protocol** – reverse‑engineering log, lessons learned, and complete timing specification in `docs/`

## Hardware

| Component | Details |
|-----------|---------|
| Microcontroller | Elegoo Mega2560 (ATmega2560) – any board with Timer 3 on OC3A (Pin 5) |
| IR LED | TSAL6200 or similar 940 nm LED |
| NPN transistor | 2N2222 or 2N3904 for driving the LED |
| Resistors | 1 kΩ (base), 100 Ω (current‑limiting) |
| Power | 5 V via USB |

**Important:** The firmware uses ATmega2560 hardware registers directly. Clone boards may use different register names – verify against your board’s datasheet and the `hardware/PINMAP.md`.

Full schematic, BOM, and pin mapping are in [`hardware/`](hardware/).

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/axez0n/axez0n-pcjr_ir_kb.git
   cd axez0n-pcjr_ir_kb
   ```

2. Run the setup script to install Arduino CLI and dependencies:
   ```bash
   ./pcjr.sh setup
   ./pcjr.sh configure
   ```

3. Connect your Mega2560 via USB. Compile and upload the firmware:
   ```bash
   ./pcjr.sh cu
   ```

4. Start the interactive keyboard driver:
   ```bash
   ./pcjr.sh driver
   ```

   Type characters in the terminal – they appear on the PCjr!  
   (If a file name is given, the driver will “type” the entire file instead.)

5. **(Optional)** To view a Raspberry Pi camera stream, first install MediaMTX on the Pi:
   ```bash
   ./pcjr.sh server-setup   # on the Pi (downloads and configures MediaMTX)
   ./pcjr.sh server-start   # starts the streaming service
   ```
   Then on your viewing machine:
   ```bash
   ./pcjr.sh stream          # opens mpv with the RTSP feed
   ```

## Firmware Details

The sketch `pcjr_type/pcjr_ir_bridge.ino` receives raw PCjr scan codes over serial at 600 baud and transmits them as Manchester‑encoded 40 kHz IR signals. Key timing parameters (from the original IBM spec):

| Parameter | Value |
|-----------|-------|
| Carrier frequency | 40 kHz (12 µs on / 13 µs off) |
| Burst duration | 62.5 µs |
| Start bit silence | 310 µs |
| Logic 1 silence | 377.5 µs |
| Logic 0 silence | 220 µs (first half), 157.5 µs (second half) |
| Inter‑byte gap | 4840 µs (11 stop bits) |

The library `pcjr_type/pcjr_type.h` (from the original J.B. Langston project) provides higher‑level functions like `typeAscii()` and `typeString()` for direct ASCII‑to‑scan‑code translation; the current sketch uses raw scan codes for maximum flexibility.

## Protocol & Documentation

The PCjr wireless keyboard uses **biphase Manchester encoding** at 440 µs per bit with odd parity. The complete protocol specification is in [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

The reverse‑engineering effort is chronicled in [`docs/DEVLOG.md`](docs/DEVLOG.md) – including the critical discovery that community “pulse‑distance” code was incorrect, and the original IBM Technical Reference was right all along.

Key lessons learned during development are collected in [`docs/LESSONS.md`](docs/LESSONS.md) – essential reading if you plan to modify the firmware or adapt it to other clone boards.

## Repository Structure

```
├── pcjr.sh                     # Unified toolkit control script
├── pcjr.conf                   # Configuration file (serial, IP, etc.)
├── pcjrduino_tty.py            # Interactive Python keyboard driver
├── mediamtx.yml                # MediaMTX streaming server config
├── pyproject.toml              # Python project metadata
├── LICENSE                     # MIT license
├── README.md                   # This file
├── pcjr_ir_bridge/
│   └── pcjr_ir_bridge.ino      # Arduino sketch – IR bridge (raw scan codes)
├── docs/
│   ├── PROTOCOL.md             # PCjr IR protocol specification
│   ├── DEVLOG.md               # Reverse‑engineering diary
│   └── LESSONS.md              # Lessons learned from the project
└── hardware/
    ├── BOM.md                  # Bill of Materials
    └── PINMAP.md               # Pin mapping for Elegoo Mega2560
```

## License

MIT – see [`LICENSE`](LICENSE).
