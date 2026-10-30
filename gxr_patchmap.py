#!/usr/bin/env python3
"""List the bytes a patch changed in a code module (*3), by address.

Changed bytes are grouped into 4-byte-aligned runs; a run is printed as
address, length, old -> new (long runs show only the length). Branches
written by the patch (24-bit `bra`) are decoded to their target.

Usage: gxr_patchmap.py <stock *3> <patched *3>
"""
import struct
import sys

BASE = 0x2004B000 - 0x200          # file offset = address - BASE


def runs(a, b):
    out, i = [], 0x200
    while i < min(len(a), len(b)):
        if a[i:i + 4] != b[i:i + 4]:
            j = i
            while j < len(a) and a[j:j + 4] != b[j:j + 4]:
                j += 4
            out.append((i, j))
            i = j
        else:
            i += 4
    return out


def bra_target(word, addr):
    w = struct.unpack(">I", word)[0]
    if w >> 24 != 0xFF:
        return None
    disp = w & 0xFFFFFF
    disp -= (1 << 24) if disp & 0x800000 else 0
    return addr + 4 * disp


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    a, b = (open(p, "rb").read() for p in sys.argv[1:])
    print(f"header version {a[0x12:0x14].hex()} -> {b[0x12:0x14].hex()}, "
          f"checksum {a[0x16C:0x170].hex()} -> {b[0x16C:0x170].hex()}")
    for i, j in runs(a, b):
        addr, n = i + BASE, j - i
        if n > 8:
            print(f"{addr:#010x} {n:4d}  (block)")
            continue
        note = ""
        if n == 4 and (t := bra_target(b[i:j], addr)) is not None:
            note = f"  bra {t:#010x}"
        print(f"{addr:#010x} {n:4d}  {a[i:j].hex()} -> {b[i:j].hex()}{note}")
