#!/usr/bin/env python3
"""Dump the FRU EEPROM on an HP Common Slot PSU as hex or parsed fields.

    ./eeprom.py /dev/tty.usbserial-0001          # hex
    ./eeprom.py /dev/tty.usbserial-0001 -p       # parsed
    ./eeprom.py dump.bin -p                      # decode a saved file

Tag rule (empirical, from a DPS-460MB): 0xC0|n introduces an n-byte
field, 0xD0|n a (16+n)-byte field.
"""
import argparse, os, re, sys

ADDR, SIZE, CHUNK = 0x57, 256, 16


def read_serial(port, baud=115200):
    import serial
    data = bytearray()
    with serial.Serial(port, baud, timeout=2) as ser:
        ser.write(f"ECHO OFF\r\n".encode())
        ser.read_until(b"\n", 4096).decode(errors="replace")
        ser.reset_input_buffer()
        for reg in range(0, SIZE, CHUNK):
            ser.write(f"I2C READ-REG 0x{ADDR:02x} 0x{reg:02x} {CHUNK}\r\n".encode())
            reply = ser.read_until(b"\n", 4096).decode(errors="replace")
            hexes = re.findall(r"(?:>>\s*)([0-9a-fA-F]{4,})", reply)
            if not hexes:
                sys.exit(f"no data at 0x{reg:02x}; got {reply!r}")
            got = bytes.fromhex(hexes[-1])[:CHUNK]
            if len(got) != CHUNK:
                sys.exit(f"short read at 0x{reg:02x}: {len(got)} bytes")
            data += got
    return bytes(data)


def show_hex(d):
    for off in range(0, len(d), 16):
        c = d[off:off + 16]
        print(f"{off:04x}  {' '.join(f'{b:02x}' for b in c):<47}  "
              + "".join(chr(b) if 32 <= b < 127 else "." for b in c))


def show_parsed(d):
    i = 0
    while i < len(d):
        t = d[i]
        if 0xC0 <= t <= 0xDF:
            n = (t & 0x0F) + (16 if t & 0x10 else 0)
            v = d[i + 1:i + 1 + n]
            txt = v.decode("ascii").rstrip() if v and all(32 <= b < 127 for b in v) else ""
            print(f"{i:04x}  {t:02x} [{n:2d}]  {v.hex(' ')}" + (f"   {txt!r}" if txt else ""))
            i += 1 + n
        else:
            j = i
            while j < len(d) and not 0xC0 <= d[j] <= 0xDF:
                j += 1
            print(f"{i:04x}  --      {d[i:j].hex(' ')}")
            i = j


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source", help="serial port, or a saved dump file")
    p.add_argument("-p", "--parsed", action="store_true", help="parse fields instead of hex")
    p.add_argument("-b", "--baud", type=int, default=115200)
    a = p.parse_args()

    if os.path.isfile(a.source):
        data = open(a.source, "rb").read()
    else:
        data = read_serial(a.source, a.baud)

    (show_parsed if a.parsed else show_hex)(data)


if __name__ == "__main__":
    main()
