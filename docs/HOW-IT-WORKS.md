# How it works

This page explains the firmware format, how the camera installs updates, and what each patch does. Exact addresses are in [ADDRESSES.md](ADDRESSES.md), and the full investigation is in [DEVELOPMENT-LOG.md](DEVELOPMENT-LOG.md).

## Body and camera units

The GXR is a body plus interchangeable camera units, each with its own firmware family.

| Family | Unit |
| --- | --- |
| `ilaunch` | GXR body |
| `l08firm` | GXR MOUNT A12 |
| `jlaunch` | A12 50mm F2.5 Macro |
| `qlaunch` | A12 28mm F2.5 |
| `klaunch` | S10 24-72mm |
| `nlaunch` | P10 28-300mm |
| `l06firm` | A16 24-85mm |

The mapping comes from the model strings in each `*3` file.

Ricoh's 1.51 package holds 29 files: modules 0, 3, 4 and 8 of each family, plus `l06firm5`.

| Module | Header type byte | Contents |
| --- | --- | --- |
| `*0` | 0x08 | Boot loader and card updater. Loads at `0x27E00000`. |
| `*3` | 0x02 | Main program. Loads at `0x2004B000`. |
| `*4` | 0x06 | Resources: menu text, fonts, icons, start-up logo. |
| `*5` | 0x01 | Small extra module (`l06firm` only). |
| `*8` | 0x05 | Text register script (lines like `V0002` / `W0151`). |

**What each side does:**
- **The body** (`ilaunch3`/`ilaunch4`) runs the menus, display, fonts and all menu text. It sends settings to the camera unit.
- **The camera unit** does capture and image processing. It also stores the body's program and sends it to the body at start-up (`SysUnit_FileSendBodyFw`).

**Why this matters for flashing:**
- With a unit attached, the body runs the copy of its program that is stored in that unit.
- With no unit attached, it runs the copy in its own flash.
- So a body change only shows with a given unit if it was flashed with that unit attached.

## Flashing rules

These were learned on hardware:

1. **Flash once per camera unit, with that unit attached.** The camera installs the body files plus the attached unit's files, which is why the package always holds all 29 files.
2. **A code module (`*3`) installs only if its version is newer than the installed one.** The running camera skips older and same-version modules. Resource modules (`*4`) install at the same version.
3. **To go back to stock**, flash code at a version *higher* than the patched one. `build.py recovery` gives stock code version 1.90 by default.

   If you ever build a patched set above 1.90, build the recovery set higher first.

## File header

Every file starts with a 512-byte big-endian header, and the checksummed payload runs from 0x200 to the end.

| Offset | Size | Field |
| --- | --- | --- |
| 0x000 | 16 | Model code, stored bit-inverted (XOR 0xFF) |
| 0x010 | 1 | Module type |
| 0x011 | 1 | Module form (1 = binary) |
| 0x012 | 2 | **Version, BCD** (`0151` = 1.51) |
| 0x014 | 2 | Version low (0) |
| 0x016 | 2 | Compare version |
| 0x018 | 4 | Build date, BCD |
| 0x01C | 4 | Build time, BCD |
| 0x020 | 4 | Start address. Also sets the checksum phase. |
| 0x024 | … | Section table: ROM, load and zero-clear ranges |
| 0x164 | 4 | Payload size (file size − 0x200) |
| 0x168 | 4 | Total file size |
| 0x16C | 4 | **Checksum** |
| 0x1F0 | 16 | Second inverted model code |

The field names come from the updater's debug strings (`bcdUpdateVersionHigh`, `nUpdateCsum`, …).

### Checksum

The checksum comes from the updater in `ilaunch0`: the per-chunk loop is at `0x27E36118`, and the verify routine is at `0x27E3AC68`.

```
checksum = Σ payload[i] × (((start + i) mod 6) + 2)   (mod 2^32)
  payload = file[0x200 : end]
  start   = u32 at 0x020
  stored  = u32 at 0x16C
```

It reproduces the stored value in all 29 stock files. The version field is outside the payload, so changing it doesn't change the checksum.

### What the boot loader checks

When flashing, the boot loader's updater checks the model code, module type, size, ROM range and checksum. At boot it checks only the model code and module type. The version rule above is enforced by the running camera, not the boot loader.

## Menu text and languages

**Every language ships in every body image.**
- `ilaunch4` holds `com_main_<lang>.res` for jpn, eng, ger, fre, ita, spa, chinsimpl, kor, chintrad, rus and thai.
- Which languages the menu offers seems to depend on the market the camera was made for (not traced in code). Japanese-market cameras offer Japanese and English only, which is why the Japanese slot is the one redirected.

**Resource directory.**
- `*4` files hold a directory of 32-byte entries: a 24-byte name, a u32 offset (from file 0x200) and a u32 size.
- The directory sits at the end of the payload, and the payload's first u32 points to it.

**Text encoding.**
- Each character is a 2-byte code: (font page, glyph).
- Each language loads only some font pages. In `font_ctbl_00.res` there is `u32 version, u32 count (11)`, then one u32 mask per language; bit *k* loads `font_ctbl_<k+1>`. The loader is at `0x201D4F24`.
- Font page 1 is loaded for every language. It holds space, `! & ' ( ) + - . / : * _ ~ [ ] ,`, 0–9 and A–Z, so text written with it shows in any language. Lowercase letters exist only on the English page.

**String numbering.**
- Strings are numbered in order. The loader (`0x201D1F40`) splits each language's text on every zero byte, giving 1870 strings per language in stock 1.51.
- A few strings use 3-byte codes, so a parser that reads in pairs miscounts.

**Language redirect** (`gxr_lang_patch.py patch --share`):
- It points the `com_main_jpn.res` directory entry at the Traditional Chinese text.
- It copies the Chinese font mask into the Japanese slot. Without the mask the Chinese glyph pages never load, and the text is garbled.

**New labels** (`gxr_lang_patch.py addstring`):
- `addstring` appends one string, using font page 1, to every language block.
- It rebuilds the data area and directory (shared entries move together), and updates the size fields and checksum.

## The 10-entry Image Settings menu

The stock menu has 7 entries. The patched menu has 10:
- **Sepia:** value 7, a working mode Ricoh hid. Its label and icon are still in the firmware.
- **KODACHROME:** value 8.
- **PORTRA 400:** value 2.

### Menu side (body)

The changes:

- **Label list.**
  - The stock option list has no room to grow.
  - A new 10-entry label list (in a code cave) replaces it in the 24 normal menu records and the compact ADJ entry, which also get count 10.
  - The two 6-entry records, used by modes that hide an entry, keep their list and count.
- **Position → value.** The stock table at `0x2037F492` has spare bytes for positions 8–10; these become 7, 8, 2. The ADJ lever range check `cmpui #8` becomes `#11`.
- **Value → highlighted position.**
  - The compiler turned "which row is highlighted for this value" into compare chains, with 17 copies across menu contexts. None of them has room for new cases.
  - In each chain, the fall-through branch for the unhandled values (7/8 share one path, 2 has another) now goes to a 16-byte helper. The helper sets the position (8/9 for 7/8, 10 for 2) and jumps back.
- **ADJ lever and dial.**
  - The position → value switches and the dial's index ↔ value chains get helpers in the same way.
  - The validator, which resets unknown values to Standard, now accepts 2, 7 and 8.
  - The dial wrap constants make cycling go Setting2 → Sepia → KODACHROME → PORTRA 400 → Vivid.
- **Tables indexed by position.** Several tables are read by list position and have only 7 or 8 rows. Positions 8–10 read past their ends, into neighbouring data. Each table gets a 10-row copy:
  - **Per-option table:** byte 6 = "no adjustment page". Without the copy, an adjustment page appeared on position 9 and didn't work.
  - **ADJ lever icon table.**
  - **ADJ lever "Detail [DISP]" hint table:** 12-byte rows of (string, icon, 0). Without the copy, position 9 read the next table's "Detail" row and showed a hint that did nothing.

**Why the new entries have no adjustment page:** the adjustments page is hard-coded to B&W, B&W (TE), Setting1 and Setting2, by position in the MENU and by value on the ADJ lever. The new entries and Sepia can't open it without new code, so their hint and page are turned off.

### Look side (camera units)

**How a look reaches the processing.**
- The body sends the camera unit a 15-byte Image Settings block: the setting value, 0, three levels, and ten colour bytes.
- For Vivid, Standard and the other stock settings, the body fills in the preset.
- For Setting1/2 it sends your adjustments.
- For value 8 it sends neutral defaults.

**What the patch does.** In every unit, a helper runs just before the block goes to processing and to the maker note. When the value is 8 or 2, it overwrites the block with a fixed look.

**Base value.** The looks use base value 4 (Setting1), which renders the block exactly as given. Changing Setting1 on the camera doesn't affect them; this was tested on hardware.

**Reading a block back.** The block is recorded in the JPEG maker note (Ricoh tag 0x1001). Run `gxr_exifdump.py photo.jpg` to read it back.

**Making a new look:**
1. Dial a recipe into Setting1.
2. Shoot.
3. Copy the block bytes from the maker note into `LOOKS`.

Layout and the current looks: [ADDRESSES.md](ADDRESSES.md#the-15-byte-image-settings-block).

## Known gaps

- **Shooting-screen icons.**
  - Sepia and KODACHROME show no icon, and PORTRA 400 shows a legacy icon.
  - The value → icon mapping for the shooting screen hasn't been found.
- **Display-only screens.** Some screens, such as playback info and other display-only chains, may show a default label for the new values.
- **S10 and P10.** These compact units use a different image engine. The block patch is applied the same way, but whether the looks render identically there hasn't been verified.
- **Japanese slot on other units.** The other units' `*4` files have no font mask table. The language redirect is done in the body's `ilaunch4`, which draws all menu text, so this hasn't mattered in testing.
