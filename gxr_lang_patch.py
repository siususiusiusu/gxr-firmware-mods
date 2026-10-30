#!/usr/bin/env python3
"""Ricoh GXR firmware tool: checksum verify + menu language redirect.

Firmware file layout (big-endian):
  0x012  u16  version, BCD (0x0151 = 1.51) -- header only, not checksummed
  0x020  u32  start address / checksum phase
  0x16c  u32  checksum
  0x200  ...  payload (checksummed region, to end of file)

Checksum (from the updater routine at 0x27e36118 in ilaunch0):
  sum( payload[i] * (((start + i) % 6) + 2) ) & 0xffffffff

Resource files (*launch4 / *firm4) contain a directory of 32-byte entries
(24-byte name, u32 offset, u32 size); offsets are relative to file 0x200.

Menu text is (font page, glyph) byte pairs. In ilaunch4, font_ctbl_00.res
holds u32 version, u32 count, then one u32 mask per language (order of
LANGS); bit k = load font_ctbl_<k+1>. The loader is 0x201d4f24 in ilaunch3.
patch copies the target language's mask too, or its glyph pages are never
loaded and the text renders garbled.

Strings are looked up by ordinal; the loader splits the text on every zero
byte (1870 strings per language in ilaunch4, a few use 3-byte codes).
Font page 1 is loaded for every language and holds
uppercase Latin, digits and some punctuation (P1 below), so text written
with it shows in any language. rename writes such a string.

Usage:
  gxr_lang_patch.py verify <file>...
  gxr_lang_patch.py patch <in> <out> [--from com_main_jpn.res] [--to com_main_chintrad.res] [--share]
  gxr_lang_patch.py version <in> <out> <x.yy>
  gxr_lang_patch.py rename <in> <out> <string#> <TEXT> [--res com_main_jpn.res]
  gxr_lang_patch.py addstring <in> <out> <TEXT>
"""
import re
import struct
import sys

VER_OFF = 0x12
CSUM_OFF = 0x16C
START_OFF = 0x20
PAYLOAD = 0x200
LANGS = ["jpn", "eng", "ger", "fre", "ita", "spa", "chinsimpl", "kor",
         "chintrad", "rus", "thai"]
P1 = {" ": 2, "!": 3, "&": 4, "'": 5, "(": 6, ")": 7, "+": 8, "-": 9, ".": 10,
      "/": 11, ":": 22, "*": 49, "_": 50, "~": 51, "[": 52, "]": 53, ",": 54}
P1.update({str(i): 12 + i for i in range(10)})
P1.update({chr(65 + i): 23 + i for i in range(26)})


def checksum(d):
    start = struct.unpack_from(">I", d, START_OFF)[0]
    p = d[PAYLOAD:]
    return sum((((start + k) % 6) + 2) * sum(p[k::6]) for k in range(6)) & 0xFFFFFFFF


def find_entry(d, name, required=True):
    key = name.encode().ljust(24, b"\0")
    i = d.find(key)
    if i < 0 or d.find(key, i + 1) >= 0:
        if not required:
            return None
        raise SystemExit(f"directory entry {name!r} not found or not unique")
    return i


def is_entry(d, k):
    return k >= 0 and k + 32 <= len(d) and re.fullmatch(
        rb"[A-Za-z0-9_]+\.(res|RES|rex)\0*", bytes(d[k:k + 24])) is not None


def entry_span(d, e):
    """(file offset, size, capacity) of a directory entry's data; capacity
    runs to the next entry's data, so a rewrite never overlaps a neighbour."""
    off, size = struct.unpack_from(">II", d, e + 24)
    k = e
    while is_entry(d, k - 32):
        k -= 32
    offs = []
    while is_entry(d, k):
        offs.append(struct.unpack_from(">I", d, k + 24)[0])
        k += 32
    later = [o for o in offs if o > off]
    end = min(later) if later else len(d) - PAYLOAD
    return PAYLOAD + off, size, end - off


def lang_of(resname):
    return LANGS.index(resname.removeprefix("com_main_").removesuffix(".res"))


def copy_font_mask(d, frm, to):
    e = find_entry(d, "font_ctbl_00.res", required=False)
    if e is None:
        print("no font_ctbl_00.res: font masks not patched")
        return
    base = PAYLOAD + struct.unpack_from(">I", d, e + 24)[0]
    count = struct.unpack_from(">I", d, base + 4)[0]
    a, b = lang_of(frm), lang_of(to)
    if count != len(LANGS):
        raise SystemExit(f"unexpected font mask count {count}")
    old = struct.unpack_from(">I", d, base + 8 + 4 * a)[0]
    new = struct.unpack_from(">I", d, base + 8 + 4 * b)[0]
    struct.pack_into(">I", d, base + 8 + 4 * a, new)
    print(f"font mask[{LANGS[a]}]: {old:08x} -> {new:08x} (from {LANGS[b]})")


def verify(paths):
    ok = True
    for path in paths:
        d = open(path, "rb").read()
        stored = struct.unpack_from(">I", d, CSUM_OFF)[0]
        calc = checksum(d)
        good = stored == calc
        ok &= good
        print(f"{path}: stored={stored:08x} calc={calc:08x} {'OK' if good else 'MISMATCH'}")
    return ok


def patch(src, dst, frm, to, share=False):
    d = bytearray(open(src, "rb").read())
    if struct.unpack_from(">I", d, CSUM_OFF)[0] != checksum(d):
        raise SystemExit("input checksum does not verify; refusing to patch")
    a = find_entry(d, frm)
    b = find_entry(d, to)
    old = struct.unpack_from(">II", d, a + 24)
    new = struct.unpack_from(">II", d, b + 24)
    if share:
        # Point the entry at the target's text (the hardware-tested v2 layout).
        struct.pack_into(">II", d, a + 24, *new)
    else:
        # Copy the text into the entry's own space (instead of sharing the target's)
        # so its strings can later be edited without touching the target language.
        a_off, _, a_cap = entry_span(d, a)
        b_off, b_size, _ = entry_span(d, b)
        if b_size > a_cap:
            raise SystemExit(f"{to} ({b_size:#x}) does not fit in {frm} ({a_cap:#x})")
        d[a_off:a_off + a_cap] = d[b_off:b_off + b_size] + b"\0" * (a_cap - b_size)
        struct.pack_into(">I", d, a + 28, b_size)
        new = (old[0], b_size)
    copy_font_mask(d, frm, to)
    struct.pack_into(">I", d, CSUM_OFF, checksum(d))
    open(dst, "wb").write(d)
    print(f"{frm}: offset/size {old[0]:#x}/{old[1]:#x} -> {new[0]:#x}/{new[1]:#x} (from {to})")
    print(f"new checksum {struct.unpack_from('>I', d, CSUM_OFF)[0]:08x} -> {dst}")


def rename(src, dst, index, text, resname):
    d = bytearray(open(src, "rb").read())
    if struct.unpack_from(">I", d, CSUM_OFF)[0] != checksum(d):
        raise SystemExit("input checksum does not verify; refusing to patch")
    bad = sorted({c for c in text if c not in P1})
    if bad:
        raise SystemExit(f"not in the all-language font page: {''.join(bad)!r}")
    e = find_entry(d, resname)
    off, size, cap = entry_span(d, e)
    data = bytes(d[off:off + size])
    strs, i = [], 0
    while i < len(data):
        j = i
        while j < len(data) and data[j] != 0:
            j += 2
        strs.append(data[i:j])
        i = j + 1
    if not 0 <= index < len(strs):
        raise SystemExit(f"string {index} out of range (0..{len(strs) - 1})")
    strs[index] = b"".join(bytes((1, P1[c])) for c in text)
    new = b"\0".join(strs) + b"\0"
    if len(new) > cap:
        raise SystemExit(f"new text ({len(new):#x}) exceeds space ({cap:#x})")
    d[off:off + cap] = new + b"\0" * (cap - len(new))
    struct.pack_into(">I", d, e + 28, len(new))
    struct.pack_into(">I", d, CSUM_OFF, checksum(d))
    open(dst, "wb").write(d)
    print(f"{resname} string {index} -> {text!r}; size {size:#x} -> {len(new):#x}")


def set_version(src, dst, ver):
    d = bytearray(open(src, "rb").read())
    if struct.unpack_from(">I", d, CSUM_OFF)[0] != checksum(d):
        raise SystemExit("input checksum does not verify; refusing to patch")
    major, minor = ver.split(".")
    bcd = int(f"{int(major):02d}{int(minor):02d}", 16)
    old = struct.unpack_from(">H", d, VER_OFF)[0]
    struct.pack_into(">H", d, VER_OFF, bcd)
    open(dst, "wb").write(d)
    print(f"{dst}: version {old:04x} -> {bcd:04x}")


def add_string(src, dst, text):
    """Append one string (all-language font page 1) to every com_main_*.res.

    The resource payload is u32 directory offset (relative to 0x200), data,
    then the directory at the end of the file. Data chunks are rebuilt in
    offset order; entries that share data (e.g. a redirected jpn entry) move
    together. Shifts are padded to 4 bytes with zeros past each entry's size,
    so the loader (which parses exactly `size` bytes) never sees them."""
    d = bytearray(open(src, "rb").read())
    if struct.unpack_from(">I", d, CSUM_OFF)[0] != checksum(d):
        raise SystemExit("input checksum does not verify; refusing to patch")
    bad = sorted({c for c in text if c not in P1})
    if bad:
        raise SystemExit(f"not in the all-language font page: {''.join(bad)!r}")
    new = b"".join(bytes((1, P1[c])) for c in text) + b"\0"
    dir_off = PAYLOAD + struct.unpack_from(">I", d, PAYLOAD)[0]
    ents = []
    k = dir_off
    while is_entry(d, k):
        name = bytes(d[k:k + 24]).rstrip(b"\0").decode()
        off, size = struct.unpack_from(">II", d, k + 24)
        ents.append([name, off, size])
        k += 32
    if k != len(d):
        raise SystemExit("directory does not end at end of file; unexpected layout")
    starts = sorted({off for _, off, _ in ents})
    grow = {off: any(n.startswith("com_main_") for n, o, _ in ents if o == off) for off in starts}
    out = bytearray(d[PAYLOAD + 4:PAYLOAD + starts[0]])
    moved = {}
    for i, off in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else dir_off - PAYLOAD
        moved[off] = 4 + len(out)
        size = max(s for _, o, s in ents if o == off)
        chunk = bytes(d[PAYLOAD + off:PAYLOAD + end])
        if grow[off]:
            chunk = chunk[:size] + new + chunk[size:]
            chunk += b"\0" * ((-len(chunk)) % 4)
        out += chunk
    for e in ents:
        if grow[e[1]]:
            e[2] += len(new)
        e[1] = moved[e[1]]
    directory = b"".join(n.encode().ljust(24, b"\0") + struct.pack(">II", o, s)
                         for n, o, s in ents)
    payload = struct.pack(">I", 4 + len(out)) + out + directory
    d = d[:PAYLOAD] + payload
    struct.pack_into(">II", d, 0x164, len(payload), len(d))
    struct.pack_into(">I", d, CSUM_OFF, checksum(d))
    open(dst, "wb").write(d)
    print(f"added {text!r} to {sum(grow.values())} text blocks; file {len(d):#x} bytes")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["addstring"] and len(args) == 4:
        add_string(args[1], args[2], args[3])
        sys.exit(0)
    if args[:1] == ["verify"] and len(args) > 1:
        sys.exit(0 if verify(args[1:]) else 1)
    if args[:1] == ["patch"] and len(args) >= 3:
        share = "--share" in args
        args = [a for a in args if a != "--share"]
        opts = dict(zip(args[3::2], args[4::2]))
        patch(args[1], args[2], opts.get("--from", "com_main_jpn.res"),
              opts.get("--to", "com_main_chintrad.res"), share)
        sys.exit(0)
    if args[:1] == ["rename"] and len(args) >= 5:
        opts = dict(zip(args[5::2], args[6::2]))
        rename(args[1], args[2], int(args[3]), args[4],
               opts.get("--res", "com_main_jpn.res"))
        sys.exit(0)
    if args[:1] == ["version"] and len(args) == 4:
        set_version(args[1], args[2], args[3])
        sys.exit(0)
    print(__doc__)
    sys.exit(2)
