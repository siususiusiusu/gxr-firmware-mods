#!/usr/bin/env python3
"""Ricoh GXR + MOUNT A12, fw 1.51: an 8th Image Settings entry with its own look.

Body (ilaunch3):
  eighth   repoints the 25 Image Settings menu records (count 7) at the 8-entry
           ADJ list 0x2023F620 with count 8, labels the 8th entry with a string
           number, maps position 8 to a value, and widens the ADJ position check.
  film2    eighth with value 8, plus helpers in two unused debug-shell handlers
           (0x2010D960, 0x2010D9EC) so the validator, menu/ADJ highlight
           (17 chains), ADJ selection and dial cycling all know value 8.
Lens (l08firm3):
  film2lens  when the 15-byte Image Settings block sent by the body has
           setting 8, replace it with FILM_BLOCK (helper in the unused "ver"
           debug-shell handler 0x20078548). Edit FILM_BLOCK to change the look.
Early probes (kept for reference): probe, count, label.

Both outputs keep version 1.51; bump with gxr_lang_patch.py version, since the
camera only installs a code module whose version is newer than the installed one.
See docs/HOW-IT-WORKS.md and docs/ADDRESSES.md.

10-entry build (Sepia = value 7 as stock, KODACHROME = 8, PORTRA 400 = 2):
  films      positions 8-10; new 10-entry label list and icon table in cave 2,
           all value<->position maps via generated helpers.
  filmslens  any unit's code module (auto-detected addresses): one block per
           value in LOOKS.

Usage:
  gxr_imgset_patch.py films <ilaunch3 in> <out> [<label9 string#> <label10 string#>]
  gxr_imgset_patch.py filmsswap <ilaunch3 in> <out> [...]   (test: PORTRA 400 at 9, KODACHROME at 10)
  gxr_imgset_patch.py filmslens <unit *3 in> <out>
  gxr_imgset_patch.py film2 <ilaunch3 in> <out> <label string#>
  gxr_imgset_patch.py film2lens <l08firm3 in> <out>
  gxr_imgset_patch.py eighth <ilaunch3 in> <out> <label string#> [--value N]
  gxr_imgset_patch.py probe <ilaunch3 in> <out> [--label 667]
  gxr_imgset_patch.py count <ilaunch3 in> <out> <count>
  gxr_imgset_patch.py label <ilaunch3 in> <out> <string#>
"""
import struct
import sys

from gxr_lang_patch import CSUM_OFF, checksum

BASE = 0x2004B000 - 0x200          # file offset = address - BASE
OLD_LIST = 0x2022D610
NEW_LIST = 0x2023F620
STR_SLOTS = 0x205BE300             # string pointer array: slot = base + 4*n
LABEL8 = NEW_LIST + 7 * 4
TITLE_SLOT = STR_SLOTS + 4 * 502   # "Image Settings"


def probe(src, dst, label=None):
    d = bytearray(open(src, "rb").read())
    if struct.unpack_from(">I", d, CSUM_OFF)[0] != checksum(d):
        raise SystemExit("input checksum does not verify; refusing to patch")
    if struct.unpack_from(">I", d, LABEL8 - BASE)[0] != STR_SLOTS + 4 * 667:
        raise SystemExit("unexpected 8th entry in 0x2023F620; wrong firmware?")
    old = struct.pack(">I", OLD_LIST)
    sites, i = [], d.find(old)
    while i >= 0:
        sites.append(i)
        i = d.find(old, i + 1)
    patched = skipped = 0
    for p in sites:
        title = struct.unpack_from(">I", d, p - 4)[0]
        count = d[p + 4]
        compact = d[p + 5:p + 8] == b"\xff\xff\xff"   # (list, count|ffffff, ptr) table
        if title == TITLE_SLOT and count == 6:
            skipped += 1                               # modes that hide options: leave alone
            continue
        if count != 7 or not (title == TITLE_SLOT or compact):
            raise SystemExit(f"unexpected record at {p + BASE:#x}: title {title:#x} count {count}")
        struct.pack_into(">I", d, p, NEW_LIST)
        d[p + 4] = 8
        patched += 1
    if label is not None:
        struct.pack_into(">I", d, LABEL8 - BASE, STR_SLOTS + 4 * label)
    struct.pack_into(">I", d, CSUM_OFF, checksum(d))
    open(dst, "wb").write(d)
    print(f"{patched} Image Settings records -> {NEW_LIST:#x}, count 7 -> 8; "
          f"{skipped} count-6 records left alone"
          + (f"; 8th label -> string {label}" if label is not None else ""))


def probe_count(src, dst, count):
    """Probe 2: change only the option count of the titled Image Settings
    records (list and compact ADJ entry untouched), to test whether the menu
    honours the record count at all."""
    d = bytearray(open(src, "rb").read())
    if struct.unpack_from(">I", d, CSUM_OFF)[0] != checksum(d):
        raise SystemExit("input checksum does not verify; refusing to patch")
    old = struct.pack(">I", OLD_LIST)
    patched, i = 0, d.find(old)
    while i >= 0:
        if struct.unpack_from(">I", d, i - 4)[0] == TITLE_SLOT and d[i + 4] == 7:
            d[i + 4] = count
            patched += 1
        i = d.find(old, i + 1)
    struct.pack_into(">I", d, CSUM_OFF, checksum(d))
    open(dst, "wb").write(d)
    print(f"{patched} titled Image Settings records: count 7 -> {count}")


def probe_label(src, dst, string_no):
    """Probe 3: relabel Vivid (entry 0) in both option lists, to confirm the
    body actually runs the flashed ilaunch3 and draws labels from these lists."""
    d = bytearray(open(src, "rb").read())
    if struct.unpack_from(">I", d, CSUM_OFF)[0] != checksum(d):
        raise SystemExit("input checksum does not verify; refusing to patch")
    vivid = STR_SLOTS + 4 * 1136
    for lst in (OLD_LIST, NEW_LIST):
        if struct.unpack_from(">I", d, lst - BASE)[0] != vivid:
            raise SystemExit(f"{lst:#x} does not start with Vivid; wrong firmware?")
        struct.pack_into(">I", d, lst - BASE, STR_SLOTS + 4 * string_no)
    struct.pack_into(">I", d, CSUM_OFF, checksum(d))
    open(dst, "wb").write(d)
    print(f"Vivid label in {OLD_LIST:#x} and {NEW_LIST:#x} -> string {string_no}")


POS_TO_VALUE = 0x2037F492    # 1-based: Vivid 9, Standard 1, Natural 10, B&W 3, TE 6, S1 4, S2 5
POS_LIMIT = 0x20287264       # cmpui r0,#8 (positions 1..7)
VIVID_VALUE = 9


def eighth(src, dst, label, value=VIVID_VALUE):
    """Add an 8th Image Settings entry: position 8 -> internal value `value`
    (default 9 = Vivid, so it shoots exactly like Vivid), labelled with
    string number `label` (add it to ilaunch4 with gxr_lang_patch addstring).

    The 25 count-7 records (incl. the compact ADJ entry) are repointed at the
    8-entry list 0x2023F620 and given count 8; the list's spare 8th slot gets
    the label; the 1-based position table gets entry 8; the 1..7 position
    check at 0x20287264 is widened to 1..8."""
    d = bytearray(open(src, "rb").read())
    if struct.unpack_from(">I", d, CSUM_OFF)[0] != checksum(d):
        raise SystemExit("input checksum does not verify; refusing to patch")

    def expect(addr, old):
        if bytes(d[addr - BASE:addr - BASE + len(old)]) != old:
            raise SystemExit(f"unexpected bytes at {addr:#x}; wrong firmware?")

    expect(POS_TO_VALUE, bytes((0, 9, 1, 10, 3, 6, 4, 5, 0)))
    expect(POS_LIMIT, bytes.fromhex("80500008"))
    expect(LABEL8, struct.pack(">I", STR_SLOTS + 4 * 667))
    tmp = dst + ".tmp"
    open(tmp, "wb").write(d)
    probe(tmp, tmp, label)                       # records + count + 8th label
    d = bytearray(open(tmp, "rb").read())
    import os
    os.remove(tmp)
    d[POS_TO_VALUE + 8 - BASE] = value
    d[POS_LIMIT + 3 - BASE] = 9
    struct.pack_into(">I", d, CSUM_OFF, checksum(d))
    open(dst, "wb").write(d)
    print(f"position 8 -> value {value}; position limit 7 -> 8")


FILM_VALUE = 8
CAVE = 0x2010D960   # unused debug-shell handler (serial console command 60), 136 bytes
# Assembled with M32R gas/ld at 0x2010D960 (source in GXR_firmware_notes.md):
#   c1 validator: value 8 is valid        c2 menu:  value 8 -> position 8
#   c3 ADJ: value 8 -> position 8         c4 ADJ:   position 8 -> value 8 (setter)
#   c5 dial: value 8 -> index 7           c6 dial:  index 7 -> value 8 (setter)
CAVE_CODE = bytes.fromhex(
    "6008f000b2100002ff0591beff0591b9"                                  # c1 @+0x00
    "6008f000b21000036808f000ff05d1a2ff05d1a0"                          # c2 @+0x10
    "6008f000b21000036808f000ff05e5e2ff05e5e0"                          # c3 @+0x24
    "6008f000bb100005d0c0202680e08768640 81ec0ff06b820ff06b81c".replace(" ", "")  # c4 @+0x38
    + "6008f000b21000036807f000ff05ddd9ff05ddd7"                        # c5 @+0x54
    "6007f000ba100005d0c0202680e087686408 1ec0ff073e18ff073e14".replace(" ", ""))  # c6 @+0x68
DIVERT = [  # (site, cave offset): each site holds `bra <default> || nop`
    (0x20272040, 0x00), (0x20281FD8, 0x10), (0x202870EC, 0x24),
    (0x202BB9BC, 0x38), (0x202850F8, 0x54), (0x202DD1CC, 0x68),
]
DIAL_WRAP = [(0x202DEB4C, 5, FILM_VALUE), (0x202DEB7C, 6, 7)]  # ldi r3,#imm
CAVE2 = 0x2010D9EC  # unused debug-shell handler (serial console command 64), 436 bytes
# Menu-open chains (value -> highlighted position in r8) that c2 doesn't cover:
# one per shooting mode / menu context. (site of `bra <ldi r8,#1> || nop`, tested reg)
MENU_CHAINS = [  # tested register read from `ldi r0,#6 / beq <reg>,r0` before each site
    (0x2027F1FC, 3), (0x20283044, 7), (0x202844C0, 8), (0x2034B4A0, 8),
    (0x2034C130, 8), (0x2034CE50, 8), (0x2034DBB0, 8), (0x2034E88C, 2),
    (0x2034FE28, 2), (0x203505EC, 2), (0x20351B78, 2), (0x20352640, 2),
    (0x20353B0C, 8), (0x2035521C, 8), (0x20355C40, 2),
]  # (v3-v8 had r8 for the six r2 chains: those My Settings screens showed Vivid for value 8)


def menu_helper(at, reg, default):
    """ldi r0,#8 [-> ldi r8,#8] / bne reg,r0,d / bra default+4 / d: bra default.
    default holds `ldi r8,#1`, so default+4 is the join; when reg is r8 it
    already holds 8 = position 8."""
    first = "6008f000" if reg == 8 else "60086808"
    return (bytes.fromhex(first) + bytes((0xB0 | reg, 0x10, 0, 2))
            + bra24(at + 8, default + 4) + bra24(at + 12, default))
# l08firm3: the body sends a 15-byte Image Settings block (setting, 0, three
# levels, ten more bytes; the lens settings struct +267..+281). 0x201999E4
# copies it to the stack (sp+4..sp+18) for both processing and the maker note,
# then calls 0x200A9248 at 0x20199B14. For value 8 the body sends neutral
# defaults, so the helper replaces the block with Vivid's (read from the maker
# notes of a Vivid shot). The helper lives in the unused serial-console "ver"
# command handler.
LENS_SITE = 0x20199B14     # seth r0,#0x200a
LENS_CAVE = 0x20078548     # debug shell "ver" handler, only referenced by the command table
# Block layout (decoded from maker notes, 3 = neutral, one step = 1):
#   [0] setting value, [1] 0, [2] contrast, [3]/[4] vividness and sharpness,
#   [5..9] colour vividness, [10..14] colour hue, colours in menu order:
#   Orange, Greens, Blues, Reds, Magenta.
VIVID_BLOCK = [9, 0, 5, 5, 5, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2]
# Setting1 recipe shot (Test photos/setting1_kodachrome.JPG): vividness +1,
# contrast +2, sharpness +1; colour vividness Orange +1, Greens -1, Blues +2,
# Reds +2, Magenta -1; Greens hue +1. Setting byte 4 = Setting1's base.
KODACHROME_BLOCK = [4, 0, 5, 4, 4, 4, 2, 5, 5, 2, 3, 4, 3, 3, 3]
# Portra 400 (from Fujifilm Portra 400 recipes: lower contrast, natural colour,
# warm skin, softer greens and blues): contrast -1; vividness/sharpness 0;
# colour vividness Orange +1, Greens -1, Blues -1, Reds 0, Magenta -1;
# Greens hue +1 (toward yellow). Untested starting point.
PORTRA400_BLOCK = [4, 0, 2, 3, 3, 4, 2, 2, 3, 2, 3, 4, 3, 3, 3]
FILM_BLOCK = KODACHROME_BLOCK
# Image Settings value -> block, for the films/filmslens build (9 entries).
LOOKS = {8: KODACHROME_BLOCK, 2: PORTRA400_BLOCK}   # value 7 (Sepia) is left alone


def lens_helper(block):
    """ldub r1,@(4,sp) / ldi r0,#8 / bne r1,r0,skip / stb <block[i]>,@(4+i,sp) ... /
    skip: seth r0,#0x200a / bra LENS_SITE+4"""
    code = bytes.fromhex("a19f0004" "6008f000") + b"\0" * 4   # bne patched below
    for i, v in enumerate(block):
        code += bytes((0x60, v, 0xF0, 0)) + bytes((0xA0, 0x0F, 0, 4 + i))  # ldi r0,#v / stb r0,@(4+i,sp)
    skip = len(code)
    code = code[:8] + bytes((0xB1, 0x10)) + struct.pack(">H", (skip - 8) // 4) + code[12:]
    code += bytes.fromhex("d0c0200a") + bra24(LENS_CAVE + skip + 4, LENS_SITE + 4)
    return code


def lens_find(d):
    """Find (site, cave) in any unit's *firm3 / *launch3: the 15-byte block
    copy-out call in the block routine, and the serial-console "ver" handler."""
    import re
    m = list(re.finditer(rb"\xd0\xc0\x20\x0a\x85\xaf\x00\x04\x80\xe0..\xa4\xcf\x00\x14\x66\x0f\x1e\xc0", d, re.S))
    v = list(re.finditer(rb"ver\x00{6}indicate version\. \[", d))
    if len(m) != 1 or len(v) != 1:
        raise SystemExit("block routine or ver handler not found (or not unique)")
    site = m[0].start() + BASE
    if bytes(d[m[0].start() - 0x12C:m[0].start() - 0x124]) != bytes.fromhex("a4cf001ca194010b"):
        raise SystemExit("unexpected block routine layout")
    cave = struct.unpack(">I", d[v[0].start() - 4:v[0].start()])[0]
    if d.count(struct.pack(">I", cave)) != 1 or bytes(d[cave - BASE:cave - BASE + 4]) != bytes.fromhex("4ff4287f"):
        raise SystemExit("unexpected ver handler")
    return site, cave


def lens_helper_multi(looks, site=LENS_SITE, cave=LENS_CAVE):
    """ldub r1,@(4,sp); for each (value, block): ldi r0,#value / bne r1,r0,next /
    stb block bytes / bra done; next: ... done: seth r0,#0x200a / bra LENS_SITE+4"""
    a = Asm(cave)
    a.raw("a19f0004")                                     # ldub r1,@(4,sp)
    for n, (value, block) in enumerate(looks.items()):
        a.raw(f"60{value:02x}f000")                       # ldi r0,#value || nop
        a.bne(1, 0, f"next{n}")
        for i, v in enumerate(block):
            a.raw(f"60{v:02x}f000" f"a00f00{4 + i:02x}")  # ldi r0,#v / stb r0,@(4+i,sp)
        a.bra("done")
        a.label(f"next{n}")
    a.label("done")
    a.raw("d0c0200a")                                     # seth r0,#0x200a (displaced)
    a.bra(site + 4)
    return a.assemble()


class Asm:
    """Tiny M32R assembler for 32-bit-aligned helper code: raw words,
    bne rA,rB,label (16-bit displacement) and bra to a label or address (24-bit)."""
    def __init__(self, org):
        self.org, self.items, self.labels = org, [], {}

    def here(self):
        return self.org + 4 * len(self.items)

    def label(self, name):
        self.labels[name] = self.here()

    def raw(self, hexwords):
        b = bytes.fromhex(hexwords)
        for i in range(0, len(b), 4):
            self.items.append(b[i:i + 4])

    def bne(self, ra, rb, target):
        self.items.append(("bne", ra, rb, target, self.here()))

    def bra(self, target):
        self.items.append(("bra", target, self.here()))

    def assemble(self):
        out = b""
        for it in self.items:
            if isinstance(it, bytes):
                out += it
            elif it[0] == "bne":
                _, ra, rb, t, at = it
                disp = (self.labels.get(t, t) - at) >> 2
                out += bytes((0xB0 | ra, 0x10 | rb)) + struct.pack(">h", disp)
            else:
                _, t, at = it
                out += bra24(at, self.labels.get(t, t))
        return out


def bra24(src, dst):
    disp = (dst - src) >> 2
    if not -(1 << 23) <= disp < (1 << 23):
        raise SystemExit(f"bra out of range {src:#x} -> {dst:#x}")
    return struct.pack(">I", 0xFF000000 | (disp & 0xFFFFFF))


def film2(src, dst, label):
    """FILM 1 as its own value 8 (body side). See notes, round 5/6."""
    tmp = dst + ".tmp"
    eighth(src, tmp, label, FILM_VALUE)
    d = bytearray(open(tmp, "rb").read())
    import os
    os.remove(tmp)
    if len(CAVE_CODE) != 0x84:
        raise SystemExit(f"cave code length {len(CAVE_CODE):#x}")
    if bytes(d[CAVE - BASE:CAVE - BASE + 4]) != bytes.fromhex("8faffdfc"):
        raise SystemExit("unexpected bytes at cave; wrong firmware?")
    d[CAVE - BASE:CAVE - BASE + len(CAVE_CODE)] = CAVE_CODE
    for site, off in DIVERT:
        if d[site - BASE] != 0x7F or bytes(d[site - BASE + 2:site - BASE + 4]) != b"\xf0\x00":
            raise SystemExit(f"unexpected bytes at {site:#x}")
        d[site - BASE:site - BASE + 4] = bra24(site, CAVE + off)
    for site, old, new in DIAL_WRAP:
        if bytes(d[site - BASE:site - BASE + 4]) != bytes((0x63, old, 0xF0, 0)):
            raise SystemExit(f"unexpected bytes at {site:#x}")
        d[site - BASE + 1] = new
    if bytes(d[CAVE2 - BASE:CAVE2 - BASE + 4]) != bytes.fromhex("4f80287f"):
        raise SystemExit("unexpected bytes at cave 2; wrong firmware?")
    at = CAVE2
    for site, reg in MENU_CHAINS:
        o = site - BASE
        default = site + 4 * struct.unpack_from(">b", d, o + 1)[0]
        if d[o] != 0x7F or bytes(d[o + 2:o + 4]) != b"\xf0\x00" or \
                bytes(d[default - BASE:default - BASE + 4]) != bytes.fromhex("6801f000"):
            raise SystemExit(f"unexpected bytes at {site:#x}")
        d[at - BASE:at - BASE + 16] = menu_helper(at, reg, default)
        d[o:o + 4] = bra24(site, at)
        at += 16
    struct.pack_into(">I", d, CSUM_OFF, checksum(d))
    open(dst, "wb").write(d)
    print(f"FILM value {FILM_VALUE}: {len(DIVERT)} diversions -> cave {CAVE:#x}, dial wrap patched, "
          f"{len(MENU_CHAINS)} menu chains -> cave 2 {CAVE2:#x}..{at:#x}")


# 10-entry build ("films"): position 8 = value 7 (Sepia, the firmware's own
# hidden entry, kept as is), 9 = value 8 (KODACHROME), 10 = value 2 (PORTRA 400).
# In every value -> position chain, values 7 and 8 reach one `bra <default>`
# (the 5 < v < 9, v != 6 path) and value 2 another (the v < 3, v != 1 path).
# Helpers: 7/8 -> position v + 1 (dial index v), 2 -> position 10 (index 9).
ENTRIES = [(8, 7, 667), (9, 8, 1870), (10, 2, 1871)]   # (position, value, label string)
POS9 = 0x2037F49B              # position table 0x2037F492 entries 9, 10 (spare, read only for those positions)
ADJ_LIST_REF = (0x201FC5B8, 0x201FC5BC)                        # seth/or3 of 0x2023F620
ICON_REFS = [(0x201FCDA4, 0x201FCDA8), (0x201FCDC0, 0x201FCDC4)]  # seth/or3 of 0x2023FC52
ICONS = 0x2023FC52             # 4 bytes per entry, 8 entries (entry 8 = Sepia's icon)
CHAIN_SITES = [(0x20281FD8, 2, 0x20282004), (0x202870EC, 2, 0x20287118)] + \
    [(site, reg, None) for site, reg in MENU_CHAINS]           # None: join = default + 4
VALIDATOR_SITE, VALIDATOR_SITE2 = 0x20272040, 0x2027201C        # 7/8 path, 0/2 path
VALIDATOR_OK, VALIDATOR_RESET = 0x20272060, 0x20272050
DIAL_SITE, DIAL_SITE2, DIAL_JOIN = 0x202850F8, 0x202850D4, 0x20285124  # value (r2) -> index (r8)
ADJ_SITE = 0x202BB9BC          # ADJ position (r11) -> setter; exits 0x202BBA2C / default 0x202BBA20
IDX_SITE = 0x202DD1CC          # dial index (r10) -> setter; exits 0x202DD23C / default 0x202DD230
SETTER = "d0c0202680e08768"    # seth r0,#0x2026 / or3 r0,r0,#0x8768
CAVE3 = 0x2010D70C             # unused debug-shell handler (serial console command 9), 0x12C bytes
PER_OPTION = 0x20236048        # record +12: 8 bytes per option, 7 entries; byte 6 = 1 means "no
                               # adjustments" (Vivid/Standard/Natural), 0 = has an adjustment page
DETAIL_ROWS = 0x2023FD38     # ADJ lever hint rows (string, icon, 0) per position, 8 rows
DETAIL_REF = (0x201FEBE4, 0x201FEBE8)  # seth r2 / or3 r2 of DETAIL_ROWS (ADJ item 5 = Image Settings)


def films(src, dst, label9=1870, label10=1871, swap=False):
    """Stock ilaunch3 -> 10 Image Settings entries: Sepia, KODACHROME, PORTRA 400.
    swap: PORTRA 400 (value 2) at position 9, KODACHROME (value 8) at 10."""
    entries = [(8, 7, 667), (9, 8, label9), (10, 2, label10)]
    if swap:
        entries = [(8, 7, 667), (9, 2, label10), (10, 8, label9)]
    pos2 = 9 if swap else 10
    tmp = dst + ".tmp"
    eighth(src, tmp, 667, 7)                   # records, position 8 = Sepia (value 7)
    d = bytearray(open(tmp, "rb").read())
    import os
    os.remove(tmp)

    def at(a, n=4):
        return bytes(d[a - BASE:a - BASE + n])

    def put(a, b):
        d[a - BASE:a - BASE + len(b)] = b

    def site(a):
        if at(a)[0] != 0x7F or at(a)[2:] != b"\xf0\x00":
            raise SystemExit(f"unexpected bytes at {a:#x}")
        return a + 4 * struct.unpack(">b", at(a)[1:2])[0]          # its default target

    def site2_of(s78, reg):
        """The `ldi r0,#1 / beq reg,r0 / bra <default>` path for v < 3, v != 1."""
        dflt = site(s78)
        for a in range(s78 - 4, s78 - 0x80, -4):
            if at(a - 8) == bytes.fromhex("6001f000") and at(a - 4)[:2] == bytes((0xB0 | reg, 0x00)) \
                    and at(a)[0] == 0x7F and site(a) == dflt:
                return a
        raise SystemExit(f"no value-2 path found before {s78:#x}")

    for a, old in [(CAVE, "8faffdfc"), (CAVE2, "4f80287f"), (POS9, "0103"), (POS_LIMIT, "80500009")]:
        if at(a, len(old) // 2) != bytes.fromhex(old):
            raise SystemExit(f"unexpected bytes at {a:#x}; wrong firmware?")
    # cave 2: 10-entry label list, icon table, value -> position helpers
    c2 = Asm(CAVE2)
    lst = c2.here()
    c2.raw(at(NEW_LIST, 32).hex() + "".join(f"{STR_SLOTS + 4 * lab:08x}" for _, _, lab in entries[1:]))
    icons = c2.here()
    c2.raw(at(ICONS, 32).hex() + at(ICONS + 28, 4).hex() * 2)     # new entries reuse entry 8's icon
    redirect = []
    for s78, reg, join in CHAIN_SITES:
        w = at(s78 - 8, 8)                                        # ldi r0,#6 / beq <reg>,r0
        if w[:2] != bytes.fromhex("6006") or w[4] >> 4 != 0xB or w[4] & 0xF != reg:
            raise SystemExit(f"chain at {s78:#x}: tested register is not r{reg}")
        join = join or site(s78) + 4
        s2 = site2_of(s78, reg)
        redirect += [(s78, c2.here())]
        if swap:                                                  # [mv r8,reg] / add r8,r8 / addi r8,#-6
            c2.raw("08a848fa" if reg == 8 else f"188{reg:x}08a848faf000")
        else:
            c2.raw("4801f000" if reg == 8 else f"188{reg:x}4801")  # [mv r8,reg ->] addi r8,#1
        c2.bra(join)
        redirect += [(s2, c2.here())]
        c2.raw(f"68{pos2:02x}f000")                               # ldi r8,#pos2
        c2.bra(join)
    redirect += [(DIAL_SITE, c2.here())]
    if swap:
        c2.raw("188208a848f9f000")                                # index = 2 * value - 7
    else:
        c2.raw("1882f000")                                        # mv r8,r2  (index = value)
    c2.bra(DIAL_JOIN)
    redirect += [(DIAL_SITE2, c2.here())]
    c2.raw(f"68{pos2 - 1:02x}f000")                               # ldi r8,#pos2-1
    c2.bra(DIAL_JOIN)
    redirect += [(VALIDATOR_SITE2, c2.here())]
    c2.raw("6002f000")                                            # ldi r0,#2
    c2.bne(2, 0, "reset")
    c2.bra(VALIDATOR_OK)
    c2.label("reset")
    c2.bra(VALIDATOR_RESET)
    # cave 1: position / dial index -> setter(value)
    c1 = Asm(CAVE)
    for name, reg, key, exit_, s in [("adj", 11, 0, 0x202BBA2C, ADJ_SITE),
                                     ("idx", 10, 1, 0x202DD23C, IDX_SITE)]:
        dflt = site(s)
        redirect += [(s, c1.here())]
        for n, (pos, value, _) in enumerate(entries):
            k = pos if key == 0 else pos - 1                      # dial index is 0-based
            c1.raw(f"60{k:02x}f000")                              # ldi r0,#k
            c1.bne(reg, 0, f"{name}n{n}")
            c1.raw(f"64{value:02x}f000")                          # ldi r4,#value
            c1.bra(f"{name}call")
            c1.label(f"{name}n{n}")
        c1.bra(dflt)
        c1.label(f"{name}call")
        c1.raw(SETTER + "1ec0f000")                               # jl r0
        c1.bra(exit_)
    code1, code2 = c1.assemble(), c2.assemble()
    if len(code1) > 0x88 or len(code2) > 436:
        raise SystemExit(f"helpers too big: {len(code1):#x}, {len(code2):#x}")
    for s, _ in redirect:
        site(s)
    for s, target in redirect:
        put(s, bra24(s, target))
    put(VALIDATOR_SITE, bra24(VALIDATOR_SITE, VALIDATOR_OK))     # 7 and 8 are valid
    put(CAVE, code1)
    put(CAVE2, code2)
    # per-option data with 10 entries (cave 3): the new entries copy Vivid's
    # (no adjustment page); past entry 7 the old table runs into other data
    if at(CAVE3) != bytes.fromhex("4fd4287f"):
        raise SystemExit("unexpected bytes at cave 3; wrong firmware?")
    put(CAVE3, at(PER_OPTION, 56) + at(PER_OPTION, 8) * len(entries))
    # records, tables, limits
    n = per = 0
    old, i = struct.pack(">I", NEW_LIST), d.find(struct.pack(">I", NEW_LIST))
    while i >= 0:
        if d[i + 4] == 8:
            struct.pack_into(">I", d, i, lst)
            d[i + 4] = 10
            n += 1
            if struct.unpack_from(">I", d, i + 8)[0] == PER_OPTION:
                struct.pack_into(">I", d, i + 8, CAVE3)
                per += 1
        i = d.find(old, i + 1)
    if n != 25 or per != 24:
        raise SystemExit(f"expected 25 records / 24 per-option pointers, found {n} / {per}")
    # two 6-entry records keep the stock list but also read per-option data by
    # position; the ADJ lever's adjustment hint comes from them
    six, i = 0, d.find(struct.pack(">I", OLD_LIST))
    while i >= 0:
        if d[i + 4] == 6 and struct.unpack_from(">I", d, i + 8)[0] == PER_OPTION:
            struct.pack_into(">I", d, i + 8, CAVE3)
            six += 1
        i = d.find(struct.pack(">I", OLD_LIST), i + 1)
    if six != 2:
        raise SystemExit(f"expected 2 six-entry records, found {six}")
    per += six
    # ADJ lever "Detail [DISP]" hint: 12-byte rows (string, icon, 0) per position at
    # 0x2023FD38, 8 rows; position 9 read the next table's "Detail" row. Use a
    # 10-row copy in cave 3 (new entries: no hint).
    det = CAVE3 + 8 * (7 + len(entries))
    put(det, at(DETAIL_ROWS, 12 * 8) + bytes(12 * (len(entries) - 1)))
    hi, lo = DETAIL_REF
    if at(hi) != bytes.fromhex("d2c02023") or at(lo) != bytes.fromhex("82e2fd38"):
        raise SystemExit("unexpected Detail table reference")
    put(hi + 2, struct.pack(">H", det >> 16))
    put(lo + 2, struct.pack(">H", det & 0xFFFF))
    if det + 12 * (7 + len(entries)) > CAVE3 + 0x12C:
        raise SystemExit("cave 3 full")
    for hi, lo in [ADJ_LIST_REF] + ICON_REFS:
        tgt = lst if (hi, lo) == ADJ_LIST_REF else icons
        put(hi + 2, struct.pack(">H", tgt >> 16))
        put(lo + 2, struct.pack(">H", tgt & 0xFFFF))
    put(POS9, bytes(v for _, v, _ in entries[1:]))
    d[POS_LIMIT + 3 - BASE] = 11
    for a, old_, new in [(0x202DEB4C, 5, entries[-1][1]), (0x202DEB7C, 6, 9)]:  # dial: wrap after the last value / back to index 9
        if at(a) != bytes((0x63, old_, 0xF0, 0)):
            raise SystemExit(f"unexpected bytes at {a:#x}")
        d[a + 1 - BASE] = new
    struct.pack_into(">I", d, CSUM_OFF, checksum(d))
    open(dst, "wb").write(d)
    print(f"10 entries: {n} records -> list {lst:#x} count 10, {per} -> per-option {CAVE3:#x}, icons {icons:#x}; "
          f"{len(redirect) + 1} branches; cave1 {len(code1):#x}/0x88, cave2 {len(code2):#x}/0x1b4 bytes")


def films_lens(src, dst):
    """Any unit's code module (l08firm3, jlaunch3, klaunch3, nlaunch3, qlaunch3,
    l06firm3): replace the Image Settings block for each value in LOOKS."""
    d = bytearray(open(src, "rb").read())
    if struct.unpack_from(">I", d, CSUM_OFF)[0] != checksum(d):
        raise SystemExit("input checksum does not verify; refusing to patch")
    site, cave = lens_find(d)
    code = lens_helper_multi(LOOKS, site, cave)
    if len(code) > 0x380:
        raise SystemExit("lens helper too big")
    d[cave - BASE:cave - BASE + len(code)] = code
    d[site - BASE:site - BASE + 4] = bra24(site, cave)
    struct.pack_into(">I", d, CSUM_OFF, checksum(d))
    open(dst, "wb").write(d)
    print(f"lens: looks for values {sorted(LOOKS)}, site {site:#x}, helper {len(code)} bytes at {cave:#x}")


def film2_lens(src, dst):
    """l08firm3 (MOUNT A12): image-setting block for value 8 -> Vivid's block."""
    d = bytearray(open(src, "rb").read())
    if struct.unpack_from(">I", d, CSUM_OFF)[0] != checksum(d):
        raise SystemExit("input checksum does not verify; refusing to patch")
    if bytes(d[LENS_SITE - BASE:LENS_SITE - BASE + 4]) != bytes.fromhex("d0c0200a") or \
            bytes(d[LENS_CAVE - BASE:LENS_CAVE - BASE + 4]) != bytes.fromhex("4ff4287f"):
        raise SystemExit("unexpected lens code; wrong firmware?")
    code = lens_helper(FILM_BLOCK)
    d[LENS_CAVE - BASE:LENS_CAVE - BASE + len(code)] = code
    d[LENS_SITE - BASE:LENS_SITE - BASE + 4] = bra24(LENS_SITE, LENS_CAVE)
    struct.pack_into(">I", d, CSUM_OFF, checksum(d))
    open(dst, "wb").write(d)
    print(f"lens: value-8 block -> {FILM_BLOCK}, helper {len(code)} bytes at {LENS_CAVE:#x}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["films"] and len(args) in (3, 5):
        films(args[1], args[2], *map(int, args[3:]))
        sys.exit(0)
    if args[:1] == ["filmsswap"] and len(args) in (3, 5):     # test: PORTRA 400 at 9, KODACHROME at 10
        films(args[1], args[2], *map(int, args[3:]), swap=True)
        sys.exit(0)
    if args[:1] == ["filmslens"] and len(args) == 3:
        films_lens(args[1], args[2])
        sys.exit(0)
    if args[:1] == ["film2"] and len(args) == 4:
        film2(args[1], args[2], int(args[3]))
        sys.exit(0)
    if args[:1] == ["film2lens"] and len(args) == 3:
        film2_lens(args[1], args[2])
        sys.exit(0)
    if args[:1] == ["eighth"] and len(args) >= 4:
        opts = dict(zip(args[4::2], args[5::2]))
        eighth(args[1], args[2], int(args[3]), int(opts.get("--value", VIVID_VALUE)))
        sys.exit(0)
    if args[:1] == ["label"] and len(args) == 4:
        probe_label(args[1], args[2], int(args[3]))
        sys.exit(0)
    if args[:1] == ["count"] and len(args) == 4:
        probe_count(args[1], args[2], int(args[3]))
        sys.exit(0)
    if args[:1] == ["probe"] and len(args) >= 3:
        opts = dict(zip(args[3::2], args[4::2]))
        probe(args[1], args[2], int(opts["--label"]) if "--label" in opts else None)
        sys.exit(0)
    print(__doc__)
    sys.exit(2)
