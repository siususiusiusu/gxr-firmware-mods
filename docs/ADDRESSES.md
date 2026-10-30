# Address reference

This page lists every byte the build changes, and the firmware locations the patch depends on. It covers Ricoh GXR firmware **1.51** only: other versions have different addresses, and the scripts refuse to patch them.

To see the changes yourself:

```
python3 gxr_patchmap.py <stock ilaunch3> <patched ilaunch3>
```

## Conventions

- **CPU:** Renesas M32R, big-endian.
- **Code modules (`*3`)** load at `0x2004B000`, which is file offset 0x200.
  - file offset = address − `0x2004AE00`
  - This applies to the body and every camera unit's `*3`.
- **Header:** the first 0x200 bytes of every file are a header that holds the version and checksum. See [HOW-IT-WORKS.md](HOW-IT-WORKS.md#file-header).
- **Strings:** menu text is looked up through a pointer array at `0x205BE300` in RAM. Slot *n* is at `0x205BE300 + 4n`, and the menus store slot addresses rather than string numbers.
- **"Image Settings value":** the number stored in the camera settings (settings structure +878). It is what the body sends to the camera unit and what the JPEG maker note records.
- **"Position":** the 1-based row in the Image Settings list.

### Image Settings values and positions

| Position | Entry | Value | Label string (slot) |
| --- | --- | --- | --- |
| 1 | Vivid | 9 | 1136 (0x205BF4C0) |
| 2 | Standard | 1 | 1137 (0x205BF4C4) |
| 3 | Natural | 10 | 1397 (0x205BF8D4) |
| 4 | Black & White | 3 | 425 (0x205BE9A4) |
| 5 | B&W (TE) | 6 | 775 (0x205BEF1C) |
| 6 | Setting1 | 4 | 505 (0x205BEAE4) |
| 7 | Setting2 | 5 | 506 (0x205BEAE8) |
| **8** | **Sepia** (hidden in stock firmware) | **7** | 667 (0x205BED6C) |
| **9** | **KODACHROME** (new) | **8** | 1870 (0x205C0038), added |
| **10** | **PORTRA 400** (new) | **2** | 1871 (0x205C003C), added |

- **Value 2:** a legacy "low saturation" mode that the stock menu doesn't offer. The unit patch replaces its look.
- **Value 8:** has no look of its own. Without the unit patch it shoots with neutral settings.
- **Value 7:** a working sepia mode that Ricoh left out of the menu.

## Body: `ilaunch3`

`build.py` changes 1,037 bytes in 78 runs, plus the version and checksum. They fall into the groups below.

### Code caves

The new code and tables live in three handlers of the serial debug console. Nothing in normal camera use calls them; each is referenced only from the console's command table.

| Cave | Original content | Size | Used |
| --- | --- | --- | --- |
| 1: `0x2010D960` | Debug command 60 ("indicate version" of a card file) | 0x88 | 0x88 (full) |
| 2: `0x2010D9EC` | Debug command 64 | 0x1B4 | 0x180 |
| 3: `0x2010D70C` | Debug command 9 | 0x12C | 0xC8 |

The function at `0x2010D838`, right after cave 3, is in use and is not touched.

#### Cave 1 (`0x2010D960`): position or dial index to value

| Address | Contents |
| --- | --- |
| `0x2010D960` | **ADJ lever helper.** Position (r11) 8/9/10 → calls the setter with value 7/8/2, then exits to `0x202BBA2C`. Any other position goes to the stock default `0x202BBA20`. |
| `0x2010D9A4` | **Dial helper.** Dial index (r10, 0-based) 7/8/9 → setter with value 7/8/2, then exits to `0x202DD23C`. Any other index goes to the default `0x202DD230`. |

Each helper is three `ldi r0,#k / bne rX,r0 / ldi r4,#value / bra call` tests, then `bra default`, then `call: seth/or3 r0,0x20268768 / jl r0 / bra exit`.

#### Cave 2 (`0x2010D9EC`): tables and value to position

| Address | Size | Contents |
| --- | --- | --- |
| `0x2010D9EC` | 40 | **10-entry label list:** stock `0x2023F620` (8 entries, the 8th is Sepia) plus slots for strings 1870 and 1871. |
| `0x2010DA14` | 40 | **10-entry icon table:** stock `0x2023FC52` (8 × 4 bytes). Entries 9 and 10 copy entry 8 (Sepia's icon). |
| `0x2010DA3C` | 17 × 16 | **Value → position helpers,** one pair per compare chain (next table). For value 7/8: position = value + 1 (`mv r8,rX / addi r8,#1`). For value 2: position 10 (`ldi r8,#10`). Both branch to the chain's join. |
| `0x2010DB4C` | 8 | **Dial, value 7/8:** index = value (`mv r8,r2`), then branch to `0x20285124`. |
| `0x2010DB54` | 8 | **Dial, value 2:** index 9, then branch to `0x20285124`. |
| `0x2010DB5C` | 16 | **Validator, value 2:** if r2 = 2, go to OK (`0x20272060`); otherwise go to reset (`0x20272050`). |

#### Cave 3 (`0x2010D70C`): per-position data

| Address | Size | Contents |
| --- | --- | --- |
| `0x2010D70C` | 10 × 8 | **Per-option table.** Copies the stock 7-entry table at `0x20236048`; entries 8–10 copy entry 1 (Vivid). Byte 6 = 1 means "no adjustment page": it reads 1 1 1 0 0 0 0 1 1 1. |
| `0x2010D75C` | 10 × 12 | **ADJ lever "Detail [DISP]" hint table.** Copies the stock 8-row table `0x2023FD38`, plus 2 empty rows. Each row is (string slot, icon, 0). Rows 4–7 are `0x205BEAD4` ("Detail", string 501) with icon `0x2023FFCA`; the other rows are empty. |

### Data references repointed (`seth` / `or3` pairs)

| Site | Stock target | New target | Read by |
| --- | --- | --- | --- |
| `0x201FC5B8` / `0x201FC5BC` | `0x2023F620` (ADJ label list) | `0x2010D9EC` | ADJ lever label drawing |
| `0x201FCDA4` / `0x201FCDA8` | `0x2023FC52` (icon table) | `0x2010DA14` | Image Settings icon drawing |
| `0x201FCDC0` / `0x201FCDC4` | `0x2023FC52` | `0x2010DA14` | Image Settings icon drawing |
| `0x201FEBE4` / `0x201FEBE8` | `0x2023FD38` (hint rows) | `0x2010D75C` | ADJ lever hint, when the ADJ item (r11) is 5 = Image Settings |

### Menu records

A menu item is a 28-byte record:

| Offset | Field |
| --- | --- |
| +0 | Title string slot (`0x205BEAD8` = "Image Settings") |
| +4 | Option list pointer |
| +8 | Option count; flags ×3 |
| +12 | Per-option data pointer |
| +16 | `01FFFFFF` |
| +20 | Pointer |
| +24 | 0 |

In stock firmware, 27 places point at the Image Settings option list `0x2022D610`. Each address below is the list pointer (+4), so the record starts 4 bytes earlier.

| List pointer at | Stock | Patched |
| --- | --- | --- |
| `0x2022DB70`, `0x2022E024`, `0x2022E3A4`, `0x2022E740`, `0x2022EAA4`, `0x2022F098`, `0x20230A90`, `0x2023152C`, `0x20231C10`, `0x202322F4`, `0x202329A0`, `0x20232F88`, `0x2023668C`, `0x202368BC`, `0x20236BE8`¹, `0x20237710`, `0x202379E8`, `0x20237FEC`, `0x2023828C`, `0x20239310`, `0x202398C0`, `0x2023A4C8`, `0x2023B15C`, `0x2023B7B4` (24 records) | list `0x2022D610`, count 7, per-option `0x20236048` | list `0x2010D9EC`, count 10, per-option `0x2010D70C` |
| `0x2022EE40`, `0x2022EF3C` (2 records, count 6: modes that hide an entry) | list `0x2022D610`, count 6, per-option `0x20236048` | per-option `0x2010D70C` only |
| `0x2022F5A8` (compact ADJ entry: list, `count\|FFFFFF`, 0) | list `0x2022D610`, count 7 | list `0x2010D9EC`, count 10 |

¹ Its flags are `02 00 00` instead of `01 00 00`.

### Tables and constants

| Address | Stock | Patched | Meaning |
| --- | --- | --- | --- |
| `0x2037F49A`–`9C` | `00 01 03` | `07 08 02` | Position → value table (`0x2037F492`, 1-based), entries 8–10. Entries 1–7 = 9 1 10 3 6 4 5. |
| `0x20287267` | `08` | `0B` | `cmpui r0,#8` → `#11`. The ADJ position range check: positions 1–10 instead of 1–7. |
| `0x202DEB4D` | `05` | `02` | `ldi r3,#5` → `#2`. Dial cycling wraps forward after the last entry's value (stock: after Setting2 = 5). |
| `0x202DEB7D` | `06` | `09` | `ldi r3,#6` → `#9`. Dial cycling wraps backward from Vivid to index 9 (PORTRA 400). |

### Branch redirects

Each site held `bra <default> \|\| nop` (`7Fxx F000`), the fall-through for values the stock code doesn't handle. The patch replaces it with a 24-bit `bra` to a helper.

**Value → position chains.** The body has 17 copies of this compare chain, one per menu context. Each chain has two sites:
- the **7/8 site:** the path where 5 < value < 9 and value ≠ 6
- the **value-2 site:** the path where value < 3 and value ≠ 1, 0x24 bytes earlier

| Context | 7/8 site → helper | Value-2 site → helper | Tested reg |
| --- | --- | --- | --- |
| MENU, shooting page (records `0x2022DAC4`) | `0x20281FD8` → `0x2010DA3C` | `0x20281FB4` → `0x2010DA44` | r2 |
| ADJ lever | `0x202870EC` → `0x2010DA4C` | `0x202870C8` → `0x2010DA54` | r2 |
| Per shooting mode | `0x2027F1FC` → `0x2010DA5C` | `0x2027F1D8` → `0x2010DA64` | r3 |
| Per shooting mode | `0x20283044` → `0x2010DA6C` | `0x20283020` → `0x2010DA74` | r7 |
| Records `0x2022EFEC` | `0x202844C0` → `0x2010DA7C` | `0x2028449C` → `0x2010DA84` | r8 |
| Settings screens (probably My Settings) | `0x2034B4A0` → `0x2010DA8C` | `0x2034B47C` → `0x2010DA94` | r8 |
| Settings screens (probably My Settings) | `0x2034C130` → `0x2010DA9C` | `0x2034C10C` → `0x2010DAA4` | r8 |
| Settings screens (probably My Settings) | `0x2034CE50` → `0x2010DAAC` | `0x2034CE2C` → `0x2010DAB4` | r8 |
| Settings screens (probably My Settings) | `0x2034DBB0` → `0x2010DABC` | `0x2034DB8C` → `0x2010DAC4` | r8 |
| Settings screens (probably My Settings) | `0x2034E88C` → `0x2010DACC` | `0x2034E868` → `0x2010DAD4` | r2 |
| Settings screens (probably My Settings) | `0x2034FE28` → `0x2010DADC` | `0x2034FE04` → `0x2010DAE4` | r2 |
| Settings screens (probably My Settings) | `0x203505EC` → `0x2010DAEC` | `0x203505C8` → `0x2010DAF4` | r2 |
| Settings screens (probably My Settings) | `0x20351B78` → `0x2010DAFC` | `0x20351B54` → `0x2010DB04` | r2 |
| Settings screens (probably My Settings) | `0x20352640` → `0x2010DB0C` | `0x2035261C` → `0x2010DB14` | r2 |
| Settings screens (probably My Settings) | `0x20353B0C` → `0x2010DB1C` | `0x20353AE8` → `0x2010DB24` | r8 |
| Settings screens (probably My Settings) | `0x2035521C` → `0x2010DB2C` | `0x203551F8` → `0x2010DB34` | r8 |
| Settings screens (probably My Settings) | `0x20355C40` → `0x2010DB3C` | `0x20355C1C` → `0x2010DB44` | r2 |

- **Joins:** the helpers rejoin each chain at the instruction after its default (`ldi r8,#1`). The two exceptions are the MENU and ADJ chains, which join at `0x20282004` and `0x20287118`.
- **Check:** `films` reads the tested register from each chain's `ldi r0,#6 / beq rX,r0` and refuses to build if it doesn't match.

**Other redirects:**

| Site | Stock | Patched | Purpose |
| --- | --- | --- | --- |
| `0x20272040` | `bra 0x20272050` (reset to Standard) | `bra 0x20272060` (OK) | Validator: 7 and 8 are valid |
| `0x2027201C` | `bra` to reset | `bra 0x2010DB5C` | Validator: 2 is valid |
| `0x202850F8` | `bra 0x20285120` | `bra 0x2010DB4C` | Dial: value 7/8 → index |
| `0x202850D4` | `bra` default | `bra 0x2010DB54` | Dial: value 2 → index 9 |
| `0x202BB9BC` | `bra 0x202BBA20` (→ Setting2) | `bra 0x2010D960` | ADJ lever: position → value |
| `0x202DD1CC` | `bra 0x202DD230` (→ Standard) | `bra 0x2010D9A4` | Dial: index → value |

### Key locations the patch reads but does not change

| Address | What |
| --- | --- |
| `0x2022D610` | Stock option list, 7 entries. It's packed between other lists, so it can't be extended in place. |
| `0x2023F620` | Stock ADJ label list, 8 entries; the 8th is Sepia (string 667). |
| `0x2023F640` | Auto Bracket label list. |
| `0x2023FC52` | Stock icon table, 8 × 4 bytes. |
| `0x20236048` | Stock per-option table, 7 × 8 bytes. Byte 6 = 1 means no adjustment page. |
| `0x20236080` | Auto Bracket per-option table, right after the above. |
| `0x2023FD38` | ADJ lever hint rows for Image Settings, 8 × 12 bytes. |
| `0x2023FD8C` | The next hint table (ADJ item 9). Its row 2 is "Detail", which is what stock position 9 read before v13. |
| `0x2022F560` | Compact ADJ item table: (list, `count\|FFFFFF`, flags pointer). |
| `0x2037F492` | Position → value table (1-based). |
| `0x20268768` | Image Settings setter. Takes the value in r4 and stores it at settings +878. |
| `0x20271FEC` | Image Settings getter and validator. |
| `0x200C0DAC` | Pointer to the settings structure (Image Settings at +878). |
| `0x202BE240` | ADJ lever DISP action. It opens adjustments for values 3, 4, 5 and 6 only. |
| `0x202C84CC` | MENU detail action. It opens adjustments for positions 4–7 only. |
| `0x202DE2C8` | Dial cycling routine. |
| `0x2011DB54` | Copies +878 unchanged into the packet sent to the camera unit. |
| `0x201D1F40` | String loader. It splits each language's text on every zero byte, giving 1870 strings in stock. |
| `0x201D4F24` | Font page loader; reads `mask[language]` from `font_ctbl_00.res`. |
| `0x20222334` | Language resource file-name table (jpn, eng, ger, …). |
| `0x202E673C` | Value → "setting at default?" state code. Not the shooting-screen icon. |

## Body text: `ilaunch4`

`ilaunch4` is a resource module, not code. It has no load address; the offsets below are file offsets.

| Change | Where | Stock → patched |
| --- | --- | --- |
| Japanese slot shows Traditional Chinese (skipped with `--no-cht`) | Directory entry `com_main_jpn.res` at file 0x384D2C: offset and size | `0x083A80 / 0x8CD8` → `0x0EAA7C / 0x677E` (shares the `com_main_chintrad.res` text) |
| Japanese font page mask | `font_ctbl_00.res` (file 0x346D20) + 8, `mask[0]` | `60000F01` → `60010031` (the chintrad mask) |
| Labels 1870 "KODACHROME" and 1871 "PORTRA 400" | Appended to every `com_main_*.res` | The data area and directory are rebuilt, along with payload/total size (0x164/0x168) and the checksum. The file grows from 3,691,596 to 3,692,076 bytes. |

The labels are written with font page 1, which every language loads. That is why they can use only uppercase A–Z, digits, space and `! & ' ( ) + - . / : * _ ~ [ ] ,`.

## Camera units: `*3`

The colour processing happens in the camera unit, not the body.
- **What the body sends:** a 15-byte Image Settings block.
- **The routine:** it copies the block to the stack (sp+4…sp+18) for both processing and the maker note. For MOUNT A12 this is `0x201999E4`, with its copy-out at `0x20199B14`.
- **The patch:** it replaces the `seth r0,#0x200a` at that site with a `bra` to a helper.
- **The helper:** it lives in the unit's serial console `ver` command handler, which only the console's command table references.

| Unit | Code module | Site (`seth r0,#0x200a` → `bra`) | Helper (`ver` handler) |
| --- | --- | --- | --- |
| GXR MOUNT A12 | `l08firm3` | `0x20199B14` | `0x20078548` |
| A12 50mm F2.5 Macro | `jlaunch3` | `0x2019A320` | `0x20078544` |
| S10 24-72mm | `klaunch3` | `0x20199424` | `0x20078514` |
| P10 28-300mm | `nlaunch3` | `0x201A160C` | `0x20078544` |
| A12 28mm F2.5 | `qlaunch3` | `0x2019D720` | `0x20078544` |
| A16 24-85mm | `l06firm3` | `0x2019C428` | `0x20078480` |

`filmslens` finds both addresses by pattern and checks the surrounding bytes:
- **Site:** the byte pattern `d0c0200a 85af0004 80e0.... a4cf0014 660f 1ec0`
- **Helper:** the pointer stored before the string `ver\0…indicate version. [`

Each helper is 276 bytes:

```
ldub r1,@(4,sp)                 ; block[0] = Image Settings value
ldi r0,#8 / bne r1,r0,next0     ; value 8 -> KODACHROME
  15 x (ldi r0,#b / stb r0,@(4+i,sp))
  bra done
next0: ldi r0,#2 / bne r1,r0,done  ; value 2 -> PORTRA 400
  15 x (ldi r0,#b / stb r0,@(4+i,sp))
  bra done
done: seth r0,#0x200a           ; the displaced instruction
      bra site+4
```

Value 7 (Sepia) and all stock values pass through unchanged.

### The 15-byte Image Settings block

The block is also recorded in the JPEG maker note (Ricoh tag 0x1001), so `gxr_exifdump.py` can read it back from a photo. Levels use 3 = neutral, and each menu step is ±1.

| Block byte | Maker note byte | Meaning |
| --- | --- | --- |
| 0 | 40 | Image Settings value (base). The looks use 4 (Setting1), which renders the block as given. |
| 1 | 48 | 0 |
| 2 | 49 | Contrast |
| 3, 4 | 50, 51 | Vividness and sharpness (their order isn't confirmed) |
| 5–9 | 120–124 | Colour vividness: Orange, Greens, Blues, Reds, Magenta |
| 10–14 | 125–129 | Colour hue, same order (+ moves Greens toward yellow) |

| Look | Block |
| --- | --- |
| Vivid (stock, for comparison) | `9 0 5 5 5 3 3 3 3 3 3 3 2 2 2` |
| Standard (stock) | `1 0 3 4 3 3 3 3 3 3 3 3 2 2 2` |
| KODACHROME (value 8) | `4 0 5 4 4 4 2 5 5 2 3 4 3 3 3` |
| PORTRA 400 (value 2) | `4 0 2 3 3 4 2 2 3 2 3 4 3 3 3` |

Other unit locations (MOUNT A12, `l08firm3`):
- `0x20199B30`: a value → colour-mode jump table.
- `0x2019E784`: a second converter for an unrelated field.

The patch doesn't use either. Changing them in early builds had no effect on the look.

## Boot loader: `*0` (not changed)

| Address (`ilaunch0`, base `0x27E00000`) | What |
| --- | --- |
| `0x27E36118` | Per-chunk checksum loop: Σ byte × ((pos mod 6) + 2) |
| `0x27E3AC68` | File checksum verify ("CHECK SUM ERROR!") |
| `0x27E357F4` | Model code check |
| `0x27E3613C` | Header, size and ROM range check |
| `0x27E35E90` | Boot-time main program check. It checks only the model code and module type; there is no checksum check at boot. |
| `0x27E395EC` | Prints the version fields; doesn't compare them |
