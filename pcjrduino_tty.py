#!/usr/bin/env python3
"""
PCjr keyboard driver – fixed by using unbuffered os.read().
Cleaned-up, modular version with no duplication.
"""

import sys
import os
import termios
import serial
import select
import time

SERIAL = '/dev/ttyACM0'
BAUD = 600

# ----------------------------------------------------------------------
# Scan code tables
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
# Low‑level serial helpers
# ----------------------------------------------------------------------
def send_code(ser, scan, mod=0):
    """Send a make/break scan code pair, optionally with a modifier."""
    if mod:
        ser.write(bytes([mod]))
    ser.write(bytes([scan, scan | 0x80]))
    if mod:
        ser.write(bytes([mod | 0x80]))
    ser.flush()
    time.sleep(0.002)


def send_ctrl_alt_del(ser):
    """Send the three‑finger salute (Ctrl+Alt+Del)."""
    # press Ctrl, press Alt
    ser.write(bytes([0x1D, 0x38]))                       # make Ctrl, make Alt
    # press and release Delete
    ser.write(bytes([0x53, 0x53 | 0x80]))                # Delete make/break
    # release Alt, release Ctrl (reverse order)
    ser.write(bytes([0x38 | 0x80, 0x1D | 0x80]))         # break Alt, break Ctrl

# ----------------------------------------------------------------------
# Character → scan code translation
# ----------------------------------------------------------------------
def send_char(ser, ch):
    """
    Translate a single character to the appropriate PCjr scan code(s)
    and send them over the serial port.
    """
    b = ord(ch)

    if ch in SCAN:
        send_code(ser, SCAN[ch])
    elif ch.isupper() and ch.lower() in SCAN:
        send_code(ser, SCAN[ch.lower()], 0x2A)     # left Shift
    elif ch in SHIFT and SHIFT[ch] in SCAN:
        send_code(ser, SCAN[SHIFT[ch]], 0x2A)
    elif 0x01 <= b <= 0x1A:                         # Ctrl+letter
        letter = chr(b + 0x60)
        if letter in SCAN:
            send_code(ser, SCAN[letter], 0x1D)     # Ctrl

# ----------------------------------------------------------------------
# Terminal & serial setup
# ----------------------------------------------------------------------
def set_raw_mode(fd):
    """Put the terminal into raw mode and return the previous settings."""
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
    """Restore terminal settings."""
    termios.tcsetattr(fd, termios.TCSADRAIN, old)


def connect_serial(mode='1'):
    """Open the serial port with a short connection animation."""
    ser = serial.Serial(SERIAL, BAUD, timeout=0, dsrdtr=False)
    ser.dtr = False
    time.sleep(0.1)
    ser.dtr = True
    print("Connecting", flush=True, end='')
    for _ in range(3):
        print(".", end='', flush=True)
        time.sleep(1)

    send_char(ser, '1')
    send_char(ser, mode)
    print(f"\nArduino mode: {mode}")
    print("Ready!", flush=True)
    return ser

# ----------------------------------------------------------------------
# Main interactive loop
# ----------------------------------------------------------------------
def main(ser):
    fd = sys.stdin.fileno()
    old = set_raw_mode(fd)

    try:
        esc_buf = b''
        last_esc = 0.0
        hex_mode = False
        hex_buf = ''

        while True:
            now = time.time()

            # Flush stale escape sequence
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
            print(f"\rGOT: {ord(ch):02X} {repr(ch)}", flush=True, end='')

            # Quit on Ctrl+C
            if ch == '\x03':
                break

            # Hex entry mode
            if hex_mode:
                if ch == '!':                     # send Ctrl+Alt+Del
                    send_ctrl_alt_del(ser)
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

                # Invalid hex digit – cancel hex mode and fall through
                hex_mode = False
                hex_buf = ''

            # Enter hex mode on Ctrl+\
            if ch == '\x1c':
                hex_mode = True
                continue

            # Escape sequence handling
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

            # Regular printable / control character
            send_char(ser, ch)

    except KeyboardInterrupt:
        pass
    finally:
        restore_mode(fd, old)
        print(file=sys.stderr)

# ----------------------------------------------------------------------
# File‑to‑keyboard mode
# ----------------------------------------------------------------------
def write_program(ser, fname):
    """Read a file and ‘type’ its contents through the PCjr keyboard."""
    with open(fname, 'r') as f:
        data = f.read()          # whole file as a single string

    fd = sys.stdin.fileno()
    old = set_raw_mode(fd)

    try:
        for ch in data:
            send_char(ser, ch)
            print(f"\rGOT: {ord(ch):02X} {repr(ch)}", flush=True, end='')
    except KeyboardInterrupt:
        pass
    finally:
        restore_mode(fd, old)
        print(file=sys.stderr)

# ----------------------------------------------------------------------
if __name__ == '__main__':
    # Args mean pre-processing
    if len(sys.argv) > 1:

        # mode 0 == alt, mode 1 == normal
        # state 0 == off, state 1 == on
        mode = '0' if sys.argv[1] in ["ON","OFF"] else '1'
        state = '0' if sys.argv[1] == "OFF" else '1'
    else:
        mode = '1'

    ser = connect_serial(mode)

    # Either send state or write program
    if mode == '0': 
        print(f"PCJr state: {state}")
        send_char(ser, state)
    elif len(sys.argv) > 1: 
        print(f"Writing {sys.argv[1]}")
        write_program(ser, sys.argv[1])

    # Either way, fall through to normal mod
    print("Enter bridge mode")
    main(ser)
