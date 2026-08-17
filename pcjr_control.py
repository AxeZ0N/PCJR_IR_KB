#!/usr/bin/env python3
"""
pcjr_control.py – Unified PCjr keyboard & 433 MHz outlet controller.

Usage:
  pcjr_control.py keyboard          # interactive keyboard mode
  pcjr_control.py on  <id>          # turn outlet ON  (id = 1..5)
  pcjr_control.py off <id>          # turn outlet OFF (id = 1..5)
  pcjr_control.py write <file>      # type a text file through the PCjr

All modes use a DTR-pulse reset to select the correct Arduino mode.
"""

import sys
import os
import time
import termios
import serial
import select

SERIAL_PORT = '/dev/ttyACM0'
BAUD = 600

# Arduino IR frame timing. Keep in sync with the sketch IBG setting.
IBG_US = 4840.0
FRAME_TIME_US = 4332.5 + IBG_US

# ----------------------------------------------------------------------
# PCjr scan code tables
# ----------------------------------------------------------------------
SCAN = {
    'a': 0x1E, 'b': 0x30, 'c': 0x2E, 'd': 0x20, 'e': 0x12, 'f': 0x21,
    'g': 0x22, 'h': 0x23, 'i': 0x17, 'j': 0x24, 'k': 0x25, 'l': 0x26,
    'm': 0x32, 'n': 0x31, 'o': 0x18, 'p': 0x19, 'q': 0x10, 'r': 0x13,
    's': 0x1F, 't': 0x14, 'u': 0x16, 'v': 0x2F, 'w': 0x11, 'x': 0x2D,
    'y': 0x15, 'z': 0x2C,
    '0': 0x0B, '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06,
    '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A,
    ' ': 0x39, '-': 0x0C, '=': 0x0D, '[': 0x1A, ']': 0x1B, ';': 0x27,
    "'": 0x28, '`': 0x29, '\\': 0x2B, ',': 0x33, '.': 0x34, '/': 0x35,
    '\n': 0x1C, '\r': 0x1C, '\t': 0x0F, '\b': 0x0E, '\x1b': 0x01,
    '\x7f': 0x0E,               # Backspace (DEL)
}

SHIFT = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7',
    '*': '8', '(': '9', ')': '0', '_': '-', '+': '=', '{': '[', '}': ']',
    ':': ';', '"': "'", '~': '`', '<': ',', '>': '.', '?': '/', '|': '\\',
}

ESC_MAP = {
    b'\x1b[A': 0x48, b'\x1b[B': 0x50, b'\x1b[C': 0x4D, b'\x1b[D': 0x4B,
    b'\x1bOA': 0x48, b'\x1bOB': 0x50, b'\x1bOC': 0x4D, b'\x1bOD': 0x4B,
    b'\x1b[H': 0x47, b'\x1b[F': 0x4F,
    b'\x1b[5~': 0x49, b'\x1b[6~': 0x51,
    b'\x1b[2~': 0x52, b'\x1b[3~': 0x53,
    b'\x1bOP': 0x3B, b'\x1bOQ': 0x3C, b'\x1bOR': 0x3D, b'\x1bOS': 0x3E,
    b'\x1b[15~': 0x3F, b'\x1b[17~': 0x40, b'\x1b[18~': 0x41,
    b'\x1b[19~': 0x42, b'\x1b[20~': 0x43, b'\x1b[21~': 0x44,
    b'\x1b[23~': 0x57, b'\x1b[24~': 0x58,
}

# ----------------------------------------------------------------------
# Terminal helpers
# ----------------------------------------------------------------------
def set_raw_mode(fd):
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)
    new[3] &= ~(termios.ICANON | termios.ECHO | termios.ISIG | termios.IEXTEN)
    new[0] &= ~(termios.INLCR | termios.ICRNL | termios.IGNCR)
    new[1] &= ~termios.OPOST
    new[6][termios.VMIN] = 1
    new[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, new)
    return old

def restore_mode(fd, old):
    termios.tcsetattr(fd, termios.TCSADRAIN, old)

# ----------------------------------------------------------------------
# Low-level serial send helpers
# ----------------------------------------------------------------------
def send_code(ser, scan, mod=0):
    """Send a make/break scan code pair, optionally with a modifier.

    A normal key produces 2 frames (make + break).
    A shifted or modified key produces 4 frames:
        [mod make] [key make] [key break] [mod break]

    After flushing, the routine paces by FRAME COUNT so that shifted
    characters receive proportionally more time than unshifted ones.
    At low baud (e.g. 600), the serial write itself already provides
    more than enough spacing, so this adds zero delay.
    """
    frames = []

    if mod:
        frames.append(mod)

    frames.append(scan)
    frames.append(scan | 0x80)

    if mod:
        frames.append(mod | 0x80)

    ser.write(bytes(frames))
    ser.flush()

    serial_time = len(frames) * (12.0 / BAUD)
    ir_time = len(frames) * (FRAME_TIME_US / 1_000_000.0)
    delay = ir_time - serial_time

    if delay > 0:
        time.sleep(delay)

def reset(ser):
    for ch in "new\nclear\ncls\n":
        send_char(ser, ch)

def send_ctrl_alt_del(ser):
    ser.write(bytes([0x1D, 0x38]))             # Ctrl down, Alt down
    ser.write(bytes([0x53, 0x53 | 0x80]))      # Del press + release
    ser.write(bytes([0x38 | 0x80, 0x1D | 0x80])) # Alt up, Ctrl up
    ser.flush()

def send_char(ser, ch):
    b = ord(ch)
    if ch in SCAN:
        send_code(ser, SCAN[ch])
    elif ch.isupper() and ch.lower() in SCAN:
        send_code(ser, SCAN[ch.lower()], 0x2A)   # left Shift
    elif ch in SHIFT and SHIFT[ch] in SCAN:
        send_code(ser, SCAN[SHIFT[ch]], 0x2A)
    elif 0x01 <= b <= 0x1A:
        letter = chr(b + 0x60)
        if letter in SCAN:
            send_code(ser, SCAN[letter], 0x1D)   # Ctrl

# ----------------------------------------------------------------------
# ArduinoLink – persistent serial + DTR-reset handshake
# ----------------------------------------------------------------------
class ArduinoLink:
    def __init__(self, port=SERIAL_PORT, baud=BAUD):
        self.port = port
        self.baud = baud
        self.ser = None

    def connect(self, mode_byte):
        """
        Reset the Arduino and wait for the mode-selection handshake.
        mode_byte must be b'0' (RF) or b'1' (IR).
        Returns the open serial object.
        """
        print("Connecting...",end="",flush=True)
        # 1. Open port with DTR held high to avoid spurious reset
        self.ser = serial.Serial(self.port, self.baud, timeout=3)
        self.ser.dtr = True
        time.sleep(0.2)
        self.ser.reset_input_buffer()

        # 2. Pulse DTR low for 10 ms (falling edge = reset)
        self.ser.dtr = False
        time.sleep(0.01)
        self.ser.dtr = True

        # 3. Wait for BOOT
        self._read_until('BOOT', timeout=5)

        # 4. Send mode byte
        self.ser.write(mode_byte)
        self.ser.flush()

        # 5. Wait for confirmation
        expected = 'MODE:RF' if mode_byte == b'0' else 'MODE:IR'
        self._read_until(expected, timeout=3)

        print("\rConnected!    ")
        return self.ser

    def _read_until(self, target, timeout):
        start = time.time()
        while time.time() - start < timeout:
            if self.ser.in_waiting:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line == target:
                    return
        raise TimeoutError(f"Did not receive '{target}' within {timeout}s")

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

# ----------------------------------------------------------------------
# Interactive keyboard loop
# ----------------------------------------------------------------------
def run_keyboard_loop(ser):
    fd = sys.stdin.fileno()
    old_term = set_raw_mode(fd)
    esc_buf = b''
    last_esc = 0.0
    hex_mode = False
    hex_buf = ''

    try:
        while True:
            now = time.time()
            if esc_buf and (now - last_esc > 0.2):
                send_code(ser, SCAN['\x1b'])
                esc_buf = b''

            r, _, _ = select.select([fd], [], [], 0.02)
            if not r:
                continue

            raw = os.read(fd, 1)
            if not raw:
                break
            ch = raw.decode('latin-1')
            print(f"\rGOT: {ord(ch):02X} {repr(ch)}          ", flush=True, end='')

            if ch == '\x03':    # Ctrl+C
                break

            if hex_mode:
                if ch == '!':
                    send_ctrl_alt_del(ser)
                    hex_mode = False
                    hex_buf = ''
                    continue
                if ch == '@':
                    reset(ser)
                    hex_mode = False
                    hex_buf = ''
                    continue
                if ch in '0123456789abcdefABCDEF':
                    hex_buf += ch
                    if len(hex_buf) == 2:
                        send_code(ser, int(hex_buf, 16))
                        hex_mode = False
                        hex_buf = ''
                    continue
                hex_mode = False
                hex_buf = ''

            if ch == '\x1c':     # Ctrl+\  → hex mode
                hex_mode = True
                continue

            if ch == '\x1b' or esc_buf:
                if not esc_buf:
                    esc_buf = b'\x1b'
                else:
                    esc_buf += ch.encode()
                last_esc = now
                if esc_buf in ESC_MAP:
                    send_code(ser, ESC_MAP[esc_buf])
                    esc_buf = b''
                elif len(esc_buf) > 8:
                    esc_buf = b''
                continue

            send_char(ser, ch)
    except KeyboardInterrupt:
        pass
    finally:
        restore_mode(fd, old_term)
        print(file=sys.stderr)

# ----------------------------------------------------------------------
# Outlet control commands
# ----------------------------------------------------------------------
def cmd_on(link, outlet_id):
    ser = link.connect(b'0')
    print("Toggle PCJr [ON]")
    ser.write(f"{outlet_id} 1\n".encode())
    ser.flush()
    time.sleep(0.5)   # let Arduino transmit + reset
    link.close()

def cmd_off(link, outlet_id):
    ser = link.connect(b'0')
    print("Toggle PCJr [OFF]")
    ser.write(f"{outlet_id} 0\n".encode())
    ser.flush()
    time.sleep(0.5)
    link.close()

# ----------------------------------------------------------------------
# File-typing command
# ----------------------------------------------------------------------
def cmd_write(link, filename):
    with open(filename, 'r') as f:
        data = f.read()
    ser = link.connect(b'1')
    print(f"Typing file: {sys.argv[2]}")
    for ch in data:
        send_char(ser, ch)
    link.close()

# ----------------------------------------------------------------------
# Command dispatcher
# ----------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    link = ArduinoLink()
    cmd = sys.argv[1].lower()

    if cmd == 'keyboard':
        ser = link.connect(b'1')
        print("Begin typing:")
        run_keyboard_loop(ser)
        link.close()
    elif cmd == 'on':
        if len(sys.argv) != 3:
            print("Usage: pcjr_control.py on <id>")
            sys.exit(1)
        cmd_on(link, int(sys.argv[2]))
    elif cmd == 'off':
        if len(sys.argv) != 3:
            print("Usage: pcjr_control.py off <id>")
            sys.exit(1)
        cmd_off(link, int(sys.argv[2]))
    elif cmd == 'write':
        if len(sys.argv) != 3:
            print("Usage: pcjr_control.py write <file>")
            sys.exit(1)
        cmd_write(link, sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)

if __name__ == '__main__':
    main()
