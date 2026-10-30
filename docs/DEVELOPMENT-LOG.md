# Development log

This is the working log of the investigation, kept as written (2026-10-27 to 2026-10-29), including the theories that turned out wrong.
- **Builds:** folder names refer to the author's local builds.
- **Missing files:** photos and screenshots mentioned here are not in the repository.
- **Superseded details:** some early findings were corrected later. Most notably, string numbers before the "Breakthrough" section are off. [HOW-IT-WORKS.md](HOW-IT-WORKS.md) and [ADDRESSES.md](ADDRESSES.md) hold the corrected picture.
- **Scripts:** `gxr_imgset_patch.py` keeps the older commands (`probe`, `count`, `label`, `eighth`, `film2`, `film2lens`, `filmsswap`) so every step here can be reproduced.


### Stage 1: FILM(1) label (superseded)

- Font page 1 is loaded for every language. It holds space, `! & ' ( ) + - . / : * _ ~ [ ] ,`, 0–9 and A–Z (glyph = 12+digit, 23+letter). Uppercase text written with it displays in any language. Lowercase exists only on page 2 (English).
- Strings are numbered in order and NUL-terminated (the `ilaunch` unit has 1,850; the other units 1,654). String 494 is "Setting2" (Chinese 設定2) on all seven units.
- `gxr_lang_patch.py patch` now copies the target language's text into the Japanese entry's own space, instead of pointing at the shared copy. `rename <in> <out> 494 'FILM(1)'` then rewrites that one string (only page-1 characters are accepted).
- Output: `Patched 1.51 v3 (JPN->CHT, font fix, FILM(1))/`. All 29 files pass the checksum; only the `*4` files differ from the originals. Decoded check: only string 494 differs from Traditional Chinese, and the other language entries are unchanged.

### Stage 2: film look research (superseded)

- No 3×3 colour matrices (rows summing to a power of two) anywhere in `ilaunch3`.
- 0x2025CF00–0x2025D6B0 looks like sine/cosine curves (0 → 4096 → 0), but **correction:** it's read by 0x2021FAC4, a UTF-8 decoder, and 0x2021E324/0x2021E49C. It's not hue maths.
- The function at 0x200F78A0–0x200F7B70 builds a hardware register block at 0x201086E4 from 33-point byte curves. It picks the curve by number from a settings record (bytes 2, 3 and 4).
    - 0x20101DDC: two curves, an S-curve `0 1 2 6 10 17 … 250 251 … 255` and a straight line.
    - 0x20101E1E and 0x20101E3F: two further curve tables.
    - Unknown whether this affects live view, JPEG output or something else, or how Image Settings selects it.
- Next: a probe flash (change the S-curve to something obvious, shoot every Image Settings mode) to find out what it controls, or keep tracing the code from the Image Settings menu.
- Adding a seventh Image Settings entry: the menu's string numbers aren't stored as a plain table, so the menu code hasn't been found yet.

### Seventh Image Settings entry (research, 2026-10-27)

Goal: a seventh Image Settings entry that behaves like Vivid. Not built yet; the menu code hasn't been found.

- The option labels are not stored as string numbers. Vivid (1116), Standard (1117), B&W (413/599), B&W (TE) (755), Setting1/2 (493/494) and the title (490) were searched as 16- and 32-bit values, in both byte orders, aligned and unaligned, with ±3 offsets, in `ilaunch3` and in every `ilaunch4` resource. Every hit was inside code or bitmap data.
- `ldi`/`ld24`/`add3` immediates: no instruction loads 1116, 1117, 755, 493 or 413 as a string number.
- Other menus (Color Space sRGB/AdobeRGB, Quality Normal/Fine) also have no data tables, so menus appear to be generated code. The only table of string numbers found is the exposure-value one at 0x202243C8 (pairs of x position and string number).
- String loader: 0x201D1F40 fills the pointer array at 0x205BE300 (≤ 2,500 strings, split on any zero byte). 36 code sites read that array.
- There are almost no debug names for image settings in `ilaunch3`.
- Next: trace from those 36 string-array readers to the menu framework, or from the processing side (a branch on the image-setting value 0–5). Needs a call-graph tool and several test flashes.

### Breakthrough (2026-10-27, later): string numbering fixed, menu found

**String numbering correction.** The loader (`0x201D1F40`) splits the text on *every* zero byte, so there are 1,870 strings per language (the `ilaunch` unit), not 1,850. A few strings use 3-byte codes (strings 410–421, 537–556, 678), which threw off the pair-based parser. Every string number earlier in these notes from string 410 onward is off. Correct numbers:

| String | Number | Slot address (`0x205BE300 + 4×n`) |
| --- | --- | --- |
| Image Settings (title) | 502 | 0x205BEAD8 |
| Vivid | 1136 | 0x205BF4C0 |
| Standard | 1137 | 0x205BF4C4 |
| Natural | 1397 | 0x205BF8D4 |
| Black & White | 425 | 0x205BE9A4 |
| B&W (TE) | 775 | 0x205BEF1C |
| Setting1 / Setting2 | 505 / 506 | 0x205BEAE4 / 0x205BEAE8 |

(The FILM(1) build still replaced the right string: `rename` works by content and keeps all other bytes the same.)

**Menus store string slot addresses, not string numbers.** A shooting-menu item is a 28-byte record:

| Offset | Field | Image Settings |
| --- | --- | --- |
| +0 | title string slot | 0x205BEAD8 |
| +4 | option list pointer | 0x2022D610 |
| +8 | u8 option count, u8 flags ×3 | `07 01 00 00` |
| +12 | per-option data pointer | 0x20236048 |
| +16 | `01FFFFFF` | |
| +20, +24 | pointer / 0 | |

- Option list at **0x2022D610** (7 × u32 slot addresses): Vivid, Standard, Natural, Black & White, B&W (TE), Setting1, Setting2, i.e. values 0–6. It's packed between other menus' lists, so there's no room to append.
- **27 menu records** point at that list (one per mode or menu variant): 0x2022DB70, 0x2022E024, 0x2022E3A4, 0x2022E740, 0x2022EAA4, 0x2022EE40, 0x2022EF3C, 0x2022F098, 0x2022F5A8, 0x20230A90, 0x2023152C, 0x20231C10, 0x202322F4, 0x202329A0, 0x20232F88, 0x2023668C, 0x202368BC, 0x20236BE8, 0x20237710, 0x202379E8, 0x20237FEC, 0x2023828C, 0x20239310, 0x202398C0, 0x2023A4C8, 0x2023B15C, 0x2023B7B4 (each address is the +4 field; the count byte is at +4 from it).
- Quick-menu (ADJ) label list at **0x2023F620**, same 7 entries, read at 0x201FC5B4 as `list[settings[45]]` when `settings[8] == 10`.
- **The image setting is byte 45 of the camera settings record** (byte 44 is metering). No code compares the settings byte against 6 or 7.
- 0x2023EBF0: a 10-slot colour-mode name table (Vivid, Standard, Natural, Setting1, Setting2, then 5 × Standard as filler), used by the Recall Settings screen (0x201E3F0C).
- Processing side: the parameter record at RAM 0x204F04F8 (getter 0x200F4FF0) is applied to hardware by 0x200F5350. Its bytes 44/45 are separate pipeline fields (0 = factory default, 255 → 6, tables at 0x20101858 / 0x20101C0E), filled per capture mode (18, 80–85, 96, 98, 99) by 0x200F41A0 / 0x200F4700 / 0x200F4878 / 0x200F4BCC.
- Cross-reference tool: `xref.py` pairs `seth`/`or3` (and `add3`/load/store offsets) into full addresses. It lives in the scratchpad.

**Plan for an 8th value (7 = "like Vivid"):**
1. Put a new 8-entry option list somewhere free in the image, repoint the 27 records, and set their count bytes to 8.
2. Add a label string (index 1870, past the current last string) to the language file(s), or reuse an existing string.
3. Extend or repoint the quick-menu list (0x2023F620) and the image-setting icon table, so value 7 doesn't show a neighbouring entry.
4. Find where settings byte 45 is turned into processing parameters, and map 7 → 0 (Vivid) there. Not found yet.
5. Check the per-option data at 0x20236048 (8-byte entries?) and anything else indexed by the value (EXIF, My Settings save).

**Further findings (same session):**
- Image-setting icon table: **0x2023FC52** (4 bytes per value, 7 values), read at 0x201FCDA0 / 0x201FCDBC from UI byte 45. (0x2023FC46 is metering, UI byte 44.)
- Global settings record: RAM **0x20575558**. 0x2016721C copies a compact/UI layout into it: UI[45] low nibble → G[42], UI[45] high nibble → G[228], UI[44] → G[215]. Called from 0x20173DD4; the reverse copy is probably 0x20167358. So the image setting is **G+42 = 0x20575582**, but nothing reads it at a fixed address; it's always reached through a base register.
- The compiler emits jump tables only for 8 or more cases, so 7-value settings are handled by compare chains. No 7-way switch to patch.
- The processing consumer of the image setting is still unknown. The pipeline record writers in 0x200F3000–0x200F5400 only set defaults (−1/0).
- Next: trace callers of the settings get/set functions that take 0x20575558 (0x20167A0C, 0x20156310, 0x20155A90, …), or find the Vivid/Standard/Natural preset parameter table.
- Lead: the GXR-recipes idea page (github awesome-REA-cases) has no technical content. A linked X post reportedly shows success, but it couldn't be fetched (HTTP 402).

### Reference: the @Davidwuuu92 X post (2026-10-15), from screenshots

Files: `Screenshot 2026-10-27 at 13.08.06.png`, `13.09.27.png`, `13.10.18.png` (frames from the post's video).

- Post text: "this REA hype brought back my Ricoh GXR. I can make a new firmware with modern GR recipe in it!!!!!"
- The video shows a GXR body (ADJ. lever, DIRECT / OPEN / VF/LCD buttons) in English. The ADJ quick bar shows ISO, **image settings (highlighted)**, AF/MF, metering, move, so the list is the Image Settings item opened from the ADJ lever.
- The list scrolls and has at least 16 numbered entries, mixed case (so custom strings on the English font page):
  01 Neutral, 02 Low Contrast, 03 High Contrast, 04 Soft Detail, 05 Crisp Detail, 06 Muted Color, 07 Rich Color, 08 Orange Plus, 09 Green Plus, 10 Blue Plus, 11 Red Plus, 12 Magenta Plus, 13 WB Axis0 Plus, 14 WB Axis0 Minus, 15 WB Axis1 Plus, 16 WB Axis1 Min…
  The footer "Move Slctn" / "OK Ok" is the stock UI.
- What this suggests:
    - Each entry changes one parameter that already exists in the GXR's Setting1/Setting2 adjustments: contrast, sharpness ("detail"), vividness ("color"), the individual colour settings (Orange, Greens, Blues, Reds, Magenta, the table at 0x2023EBAC) and the two white-balance compensation axes.
    - So the new entries are most likely fixed-parameter versions of the custom-settings mechanism, rather than new processing.
    - The option list and count can grow well past 7 (the list scrolls), and new label strings can be added.
- Unit and firmware family unknown; no files or method published.

### Round 3 (2026-10-27): tracing the processing side

- **Global settings record → processing:** following 0x20575558 through the call graph (22 functions receive it, 3 levels deep) found only the layout conversion reading offset 42. The value isn't read straight from the global record; it's copied into other structures first.
- **Byte 45 means different things in different layouts.** 0x20166944 copies src[45] → G[35] (signed, a different setting), 0x20166DC0 copies src[45] → dst[7] and src[42] → dst[529]. The image-setting meaning of byte 45 holds only for the UI/menu layout (0x201FC2A8, 0x201FCAAC).
- **Pipeline record (0x204F04F8) selectors** in 0x200F5350, each 0 = factory calibration (via 0x200C0D9C → adjustment data), 1–6 = built-in table, 255 → 6:
    - byte 42: 24 words from rows of 96 bytes at 0x20101274 → registers 0x20108290+624.
    - byte 43: 16 words from rows of 64 bytes at 0x201014B4.
    - bytes 44 and 45: u16 from 0x20101858, u8 from 0x20101C0E.
    - The row contents look like edge/noise knee curves with unity gains (0x40), not colour matrices.
- **Next approach (practical):** a probe flash, since static tracing of the colour path is slow. Add value 7 to the menu only (new 8-entry list, count 8, label), with the quick-menu and icon tables extended so value 7 points at Vivid's label and icon. Then see on the camera what value 7 produces. If it already behaves like Vivid, or like Standard, that tells us where the mapping is.

### Round 3 result: a hidden 8th image setting, and the probe build

- **The firmware already has an 8th image-setting slot (value 7):**
    - The ADJ quick-menu label list 0x2023F620 has 8 entries; the 8th (0x2023F63C → string 667 "Sepia") isn't referenced anywhere else. 0x2023F640 is the separate Auto-Bracket list (read at 0x201FC5E0).
    - The image-setting icon table 0x2023FC52 has 8 entries; entry 7 is `360C350C`.
    - The main option list 0x2022D610 has only 7 (its 8th slot starts another menu's list, "Color / B&W / Sepia / Off", used by 0x2022F6A4).
    - Likely a leftover from an earlier Ricoh model. Whether the processing still handles value 7 is unknown, which is what the probe tests.
- **The 27 records that use 0x2022D610:**
    - 23 normal (`07 01 00 00`), plus 1 with `07 02 00 00` (0x20236BE8).
    - 2 with count 6 (0x2022EE40, 0x2022EF3C: modes that hide an option).
    - 1 compact entry 0x2022F5A8 (`list, 07FFFFFF, 0`) in a table of (list, count|FFFFFF, ptr) entries at about 0x2022F560, probably what ADJ/Fn assignment uses.
- **`gxr_imgset_patch.py probe`:** repoints the 25 count-7 records (including the compact one) to 0x2023F620 and sets the count to 8. The count-6 records are left alone. Optional `--label <string#>` relabels the 8th entry. Checksum recalculated.
- **Output:** `Probe 1.51 imgset8 (ilaunch, JPN->CHT)/` = the v2 set (the language patch that works) plus the probe `ilaunch3` (102 bytes differ: 25 × 4 + checksum). All 29 files pass verification. Only valid for the `ilaunch` unit: the record addresses are specific to `ilaunch3`.
- **What the test should show:** whether Image Settings lists 8 entries with "Sepia" last, and what a photo taken with it looks like (sepia, Vivid, Standard, unchanged, or a hang). That tells us whether value 7 already has a processing path, and so where the Vivid mapping goes.

### Probe 1 test result (2026-10-27)

- Flashed `Probe 1.51 imgset8`. **No 8th entry**: Setting2 was still the last item in both the menu and the ADJ lever. The camera otherwise worked.
- So the 25 patched records (list → 0x2023F620, count 8) don't control the visible list in the mode tested. Possible reasons:
    1. The mode uses one of the 2 count-6 records left unpatched (0x2022EE40, 0x2022EF3C). Six visible entries = Vivid, Standard, B&W, B&W (TE), Setting1, Setting2 if Natural is filtered out.
    2. Visibility is decided per option by code (a filter or a position → value map), not by the count.
- **Menu engine:** 0x20281C74–0x202D3328 works on page arrays of 28-byte records, e.g. the shooting page at 0x2022DAC4 (10 items: Picture Quality/Size, Focus, Snap Focus Distance, Full Press Snap, Pre-AF, Exposure Metering, **Image Settings (item 7)**, Continuous Mode, Auto Bracket, Flash Exp. Comp.).
    - Record byte +9 = current selection (1-based).
    - Per-item index variables live around 0x205D9DFC–0x205D9E92.
    - Selections become values through small 1-based tables at about 0x2037F3C8–0x2037F5A7 (e.g. 0x2037F57B = identity 0–7, 0x2037F43C = 0,6,1,2,3,7) and then setter functions.
- **Settings structure** behind the pointer 0x200C0DAC (also loaded via `ld @(3500,0x200C0000)`): many one-line getters/setters. Several offsets repeat at stride 10 (3199–3249, 3279/3289, 3792–3922), probably one copy per shooting mode. 0x20270E14 stores the 0x2037F57B identity value at +3289.
- 0x2026E634 / 0x2026E69C are getters for +1757 / +1758: range 1–17 (else reset to 9), returning value − 9 (signed −8…+8). They fill UI bytes 44/45 in 0x202D4484, so byte 45 is not the image setting in every UI structure.

### Round 4 (2026-10-27): the real Image Settings value and mapping

Answers from the camera: the list shows **7 entries including Natural** (Vivid, Standard, Natural, B&W, B&W (TE), Setting1, Setting2), tested in A/S/M.

- **Internal value:** settings structure (pointer at 0x200C0DAC) **+878**.
    - Setter 0x20268768 (68 callers).
    - Getters end at 0x202688B0 / 0x20268988 / 0x2027206C / 0x2026877C. Some normalise: in certain modes, or for values 11–14, they return 1.
    - Other copies: 0x2025EC5C copies +878 onward into the My Settings slots; 0x2011D728 copies +878… into another structure at +4….
- **Position → value table** 0x2037F492 (1-based, used by 20 functions / 76 sites):

  | Position | 1 | 2 | 3 | 4 | 5 | 6 | 7 | (8) |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | Entry | Vivid | Standard | Natural | B&W | B&W (TE) | Setting1 | Setting2 | – |
  | Value | **9** | 1 | 10 | 3 | 6 | 4 | 5 | 0x2037F49A = 00 (not referenced) |

  So values 0, 2, 7, 8 are unused by this menu; values 11–14 exist elsewhere.
- **Value → position (reverse):** the compare chain at 0x20281FE0 only produces positions 1–7 (default 1) and stores the result in record byte 9 of item var 0x205D9E0C (page 0x2022DAC4).
- **Hard-coded position limit:** 0x202871D8 keeps an ADJ/current position byte at 0x2022F726 and resets it to 1 if it's not in 1–7 (`cmpui r0,#8` at 0x20287264). It maps via 0x2037F492 and a second 1-based table at 0x2037F46A.
- **Item position variables:** 0x202B1300 onward assigns each menu item its position per page layout. Image Settings (position 7) vars: 0x205D9E0C, E28, E49, E4F, E67, E7A, E9E, EBF, EE0.
- **Page builder:** 0x202934F0–0x2029792C rewrites some items' counts at run time (from count vars at 0x205D9B7x, minus one per unsupported option via the capability check 0x2037362C(id), with hidden-flag bytes at 0x2022FB8x). No count write was found for Image Settings.
- **Why probe 1 showed nothing is still open.** No loop resets counts, and there's no second copy of the records.

**Probe 2** (`Probe2 1.51 imgset count6 (ilaunch, JPN->CHT)/`, `gxr_imgset_patch.py count <in> <out> 6`): the 24 titled Image Settings records get count 7 → 6; nothing else changes (26 bytes incl. checksum).
- If the menu then ends at Setting1, the count is honoured, and probe 1 failed for another reason (e.g. labels or per-option data).
- If it still shows 7, the count byte is ignored or overwritten.

**Planned "8th entry = Vivid" design, once the cap is understood:**
- Option list with 8 labels (0x2023F620, relabel the 8th slot).
- Position 8 → value 9 at 0x2037F49A, so it is Vivid by construction and needs no processing change.
- Bound at 0x20287264 `#8` → `#9`.
- 0x2037F46A entry 8.
- Reverse chain: value 9 maps back to position 1, so after selection the menu will show Vivid highlighted. A truly distinct entry needs an unused value plus a processing mapping (later).

### Probe 2 result and the body/unit split (2026-10-27)

- **Probe 2 result:** the Image Settings count changed to 6 in 24 records. **No change**: Setting2 still shows in both the menu and the ADJ lever, in all of P/A/S/M.
- **The user's unit is the GXR MOUNT A12.**
- **Which family is which**, from model strings in each `*3` file:

  | Family | Unit |
  | --- | --- |
  | jlaunch | A12 50mm Macro |
  | klaunch | S10 24-72mm |
  | nlaunch | P10 28-300mm |
  | qlaunch | A12 28mm |
  | l06firm | A16 24-85mm |
  | l08firm | **GXR MOUNT A12** |
  | **ilaunch** | **the GXR body** |

  `ilaunch3` contains "--AVU BODY--", "--AVU CUNIT--", "--BOOT BODY--", "--BOOT CUNIT--".
- **The body (ilaunch) runs the UI:**
    - menus, fonts, bitmaps and the language/font mask (`ilaunch4`);
    - the Image Settings menu structures found in rounds 3–4.
- **Each camera unit does the sensor and image processing.** `l08firm3` contains no resource names (`.res`), so it doesn't draw menus. Its `l08firm4` still carries a 1,674-string text table with the same numbers up to at least 1397 (Vivid 1136, Natural 1397). How it's used is unknown.
- **Why both probes did nothing (hypothesis):** the camera unit reports to the body at run time which image settings (and how many) it supports, and the body rebuilds the option count or visibility from that, overriding the record count. "Natural" being unit-dependent fits.
- **Implications for the 8th entry:**
    1. Body side: the menu needs the unit-reported capability, or the code that applies it, patched, not just the records.
    2. Unit side (`l08firm3`): the selected value (9 = Vivid, etc.) is applied there. Mapping the new position to value 9 needs no unit change, because the unit already knows 9.
- **Capability table:** 0x2037362C(id) returns `byte[0x205E5328 + id]`, a RAM table filled at run time, presumably from the camera unit's capability report. IDs 0–62 are queried, mostly by the page builder 0x202934F0 and by 0x20262EF0, 0x202DE2C8, 0x20330020 and 0x2036AD90. Who fills 0x205E5328, and which IDs gate Image Settings options (e.g. Natural), is still to be found.
- **Next:** in `ilaunch3`, find where the body receives unit capability data for Image Settings (the page builder's capability check 0x2037362C(id), the hidden-flag bytes 0x2022FB8x, and the body↔unit communication handlers), and see how it sets the visible options.

**User note:** only body firmware has been flashed; the lens unit (MOUNT A12, `l08firm`) is stock. The language change came from the body's `ilaunch4`, which confirms the body renders the UI.

**Probe 3** (`Probe3 1.51 Vivid-label (body ilaunch, JPN->CHT)/`, `gxr_imgset_patch.py label <in> <out> 667`): in `ilaunch3`, Vivid's label slot in both option lists (0x2022D610 and 0x2023F620) is pointed at string 667 ("Sepia"); 6 bytes change including the checksum. Purpose: confirm the body really installs and runs a modified `ilaunch3`, and that labels come from these lists.
- If the first entry reads "Sepia" (in the Japanese slot: the Traditional Chinese for Sepia) → `ilaunch3` is applied, and the count is overridden at run time.
- If it still reads "Vivid" → either `ilaunch3` isn't being written by the updater, or these lists aren't what's drawn.

### Probe 3 result and why ilaunch3 changes don't show (2026-10-27)

- **Probe 3 result:** Vivid relabelled to "Sepia" in both option lists. **No change** in the menu or ADJ, in either the English or the Japanese slot. So no `ilaunch3` change has ever taken effect, while `ilaunch4` changes (language, font mask) did.
- **Ruled out:**
    - The menu runs in the lens unit. `l08firm3` and `qlaunch3` have 0 menu-like records, `ilaunch3` has 1,207. The UI is the body's `ilaunch3`.
    - The boot loader rejects a changed main program at start-up. Its main-program validator 0x27E35E90 (called via 0x27E37828 from the main-load path) checks only both model-code headers (0x27E357F4, +496 via 0x27E358F4) and module type ∈ {2, 3, 7}. **No checksum at boot.** The fallback messages ("booted with Backup Prog, Because a MainLoad error occurred", "main is Broken.") come from that same check.
    - The boot-loader updater compares versions: header version/date fields are only printed (0x27E395EC…).
- **Remaining hypothesis:** the update performed by the running body program (AVU, 0x2008D4FC in `ilaunch3`) writes the MAIN module only when its version is newer than the installed one. If the body already holds 1.52 (an early 1.52 set was built), 1.51 `ilaunch3` files would be skipped, while resource modules are written anyway.
- **Probe 4:** `Probe4 ilaunch3 v1.60 Vivid-label (JPN->CHT)/`. Same label change, `ilaunch3` header version 1.60 (7 bytes differ). The `*4` files are the v2 language set at 1.51.
- **Recovery set:** `Recovery stock code ilaunch3 v1.61 (JPN->CHT)/`. Stock `ilaunch3` code relabelled 1.61 (1 byte differs), so original body code can be restored even if only newer versions are accepted.

### Probe 4 result (2026-10-27)

- The body showed **1.51** before flashing. Flashed only the body files (`ilaunch0/3/4/8`).
- After flashing: **version 1.60**, but **Vivid is still Vivid** in the menu and ADJ. So the new `ilaunch3` header was installed, but the option-list label change had no visible effect.
- Two possibilities: the lists 0x2022D610 / 0x2023F620 aren't what the menu draws, or the body isn't executing the new `ilaunch3` code (e.g. running another copy) even though the header/version updated.

**Probe 5** (`Probe5 ilaunch3 v1.62 ENG->GER + Vivid-label (body only)/`, body files only):
- In the language file-name table at 0x20222334 (jpn, eng, ger, fre, …; read by the string loader at 0x201D1F08), the English entry (0x20222338) is pointed at `com_main_ger.res`. The Vivid → Sepia label change from probe 3 is kept. Version 1.62.
- **If English shows German**, the patched `ilaunch3` code runs, and the option lists are simply not the label source.
- **If English stays English**, the body isn't running the flashed main program.
- Recovery: `Recovery stock code ilaunch3 v1.90 (body only)/` (stock code, version 1.90).

### Probe 5 result: two copies of the body program (2026-10-27)

- **Flashed with the MOUNT A12 detached.** Version 1.62.
    - **Lens detached → English shows German.** The patched `ilaunch3` runs from the body's own flash.
    - **Lens attached → English is English and Vivid unchanged.** A different, stock copy runs.
- `l08firm3` has no font, language or resource code (font 0, lang 0, .res 0, against 63/1/94 in `ilaunch3`), and none of the body's menu or label patterns. So the lens program doesn't draw the UI itself.
- All boot loaders, including the lens ones, contain "Body Main Prog is download booted now", and `ilaunch3` has "BOOT BODY" / "BOOT CUNIT" paths.
- **Working theory:** each camera unit stores its own copy of the body main program (`ilaunch3`). With a unit attached, the body boots that copy; with no unit, it boots the copy in its own flash. The early language patch reached the lens copy because those full sets were flashed with the lens attached.
- **Next test:** flash Probe 5 (body files only) with the MOUNT A12 **attached**, then check English → German and the Vivid → Sepia label with the lens on.

### Probe 5 with the lens attached: confirmed, and the 8th entry v1 (2026-10-27)

- **Flashed with the MOUNT A12 attached.** The camera required the lens files too, so stock `l08firm0/3/4/8` were included.
    - With the lens on, English → **German**, and the first entry → **Sepia**. The Japanese slot still shows **Traditional Chinese** even with the stock lens `l08firm4`.
    - Conclusions: (a) a flash with the lens attached updates the copy of the body program that runs with that lens; (b) the option lists 0x2022D610 / 0x2023F620 really are the label source; (c) **all menu text comes from the body's `ilaunch4`.**
    - One-off: the first time Image Settings was opened after the flash, a German message starting "Die …" appeared, apparently an error. After a reboot it worked normally.
- **New tools:**
    - `gxr_lang_patch.py addstring <in> <out> <TEXT>`: appends one string (font page 1, all languages) to every `com_main_*.res` in a `*4` file. It rebuilds the data area (shared entries move together), the directory, the payload/total size fields (0x164 / 0x168) and the checksum. Verified: all 11 languages go 1870 → 1871 strings, the last one is the new text, and every other resource is byte-identical.
    - `gxr_imgset_patch.py eighth <ilaunch3 in> <out> <label string#> [--value N]`:
        - repoints the 25 count-7 records (incl. the compact ADJ entry) to 0x2023F620 and sets the count to 8;
        - sets the 8th label slot (0x2023F63C) to the given string;
        - sets 0x2037F49A (position 8) to value N (default 9 = Vivid);
        - widens the 0x20287264 position check from `cmpui #8` to `#9`.
- **8th entry v1:** `8th entry v1 FILM 1 = Vivid (flash with MOUNT A12 attached)/`
    - `ilaunch3`: stock code + `eighth … 1870`, version 1.63, 108 bytes differ.
    - `ilaunch4`: v2 language set + "FILM 1" as string 1870.
    - `ilaunch0/8`: v2. `l08firm0/3/4/8`: stock.
    - Expected: Image Settings lists 8 entries, the last "FILM 1"; selecting it stores value 9, so it shoots exactly like Vivid. Known limitation: reopening the menu highlights **Vivid** (the reverse map 0x20281FE0 sends value 9 to position 1). A distinct entry needs a free value (0, 2, 7, 8) plus processing mapping, which is the next step.
    - Position 8 also reads 0x2037F472 (= 04) through the 0x2037F46A table used by 0x202871D8; semantics unknown.
- **Recovery set (lens attached):** `Recovery stock body v1.70 + stock MOUNT A12 (lens attached)/` = stock body code at 1.70 + v2 `ilaunch4` + stock lens files.

**8th entry v1 test result (2026-10-27): works.** Flashed with the MOUNT A12 attached.
- Image Settings shows **8 entries, "FILM 1" last**, in both the menu and the ADJ lever.
- A photo taken with FILM 1 looks like Vivid. No crash.
- As expected, after selecting FILM 1 the menu and ADJ lever highlight **Vivid** (value 9 maps back to position 1).
- So the menu side is solved: the record count, the 8-entry list, position table entry 8, the widened limit check and the new string all work.

**Next (v2, a distinct entry):**
1. Use a free internal value (0, 2, 7 or 8) for position 8.
2. Extend the value → position reverse map (0x20281FE0 compare chain) so that value → position 8. FILM 1 then stays highlighted, and the ADJ/icon tables (0x2023F620 / 0x2023FC52 already have 8 slots) show it.
3. On the processing side, make that value behave like Vivid (9). This means finding where +878 is turned into processing parameters (the getters at 0x2026877C / 0x202688B8 and the copies at 0x2011D728 / 0x2025EC5C). The simplest version: translate value X → 9 in the readers used by processing, but not in the UI readers.
4. Later: give it its own look via Setting-style parameters (contrast, sharpness, vividness, per-colour, white-balance compensation), as in the reference video.

### Round 5 (2026-10-27): mapping everything a separate FILM 1 value needs

The plan: FILM 1 stores its own internal value **X = 8** (free; 7 is the old "Sepia" leftover). Body-side places found that would need to know about 8:

| What | Where | Today for 7/8 | Fix |
| --- | --- | --- | --- |
| Validator (28 callers; result written back by getter 0x2026877C) | 0x20271FEC; the 6..8 path ends `bra 0x20272050` (reset) at 0x20272040 | **resets to 1 (Standard)** | divert: 8 → ok (0x20272060) |
| Menu value → position (sets record byte 9, item var 0x205D9E0C) | 0x20281C2C chain; `bra 0x20282000` at 0x20281FD8 | position 1 | 8 → position 8 |
| ADJ value → position (0x2022F725/F726) | 0x20287080 chain; `bra 0x20287114` at 0x202870EC | position 1 | 8 → position 8 |
| ADJ position → value switch (var 0x2022F726, 1-based) | 0x202BB4BC: 1→9, 2→1, 3→10, 4→3, 5→6, 6→4, else→5; `bra 0x202BBA20` at 0x202BB9BC | **position 8 → 5 (Setting2)** (the v1 ADJ selection gave Setting2) | position 8 → value 8 |
| Cycling UI index (var 0x2022F9D5, 0-based) set from value | 0x20284A8C chain: 9→0, 10→2, 3→3, 6→4, 4→5, 5→6, else→1; `bra 0x20285120` at 0x202850F8 | index 1 | 8 → index 7 |
| Cycling UI index → value switch | 0x202DC2A0: 0→9, 2→10, 3→3, 4→6, 5→4, 6→5, else→1; `bra 0x202DD230` at 0x202DD1CC | Standard | index 7 → value 8 |
| Cycling wrap | 0x202DE2C8: forward wraps to 0 when value == 5 (`ldi r3,#5` at 0x202DEB4C); backward wraps to index 6 when value == 9 (`ldi r3,#6` at 0x202DEB7C) | stops at Setting2 | 5 → 8 and 6 → 7 |
| Display-only chains (~20 functions, e.g. 0x2005A06C, 0x20298254, 0x2034B340…) | | default (Standard/Vivid icons) | cosmetic, later |

None of the chains has room for an extra case in place, so each diversion needs a short helper routine in a code cave. The idea is to reuse an unused debug-shell handler (e.g. 0x2010D960, registered only as serial-console command 60). An M32R assembler and linker were built (`gas/as-new`, `ld/ld-new` in the scratchpad binutils build).

**Processing side, the blocker:** no body code turns +878 into image-processing parameters.
- The non-UI readers are: the My Settings slot copy (0x2025EC5C), card settings serialisation (0x2011D728, called around "Register/Recall My Settings [Card]"), a settings backup/restore pair (0x20357544 / 0x203580A8 into 0x205E4F1x), B&W-toning logic (0x2033588C…, values 3/6), and My Settings edit screens (0x2034B340…).
- So the colour look is applied in the **lens unit program `l08firm3`**, which must receive the raw value and interpret it.
- `l08firm3` has about 28 compare chains on {3,4,5,6,9,10}, not yet analysed.
- So a separate value 8 would currently be processed by the lens as "unknown" (default, possibly Standard), not as Vivid.

**Options:**
- **A, body-only alias + flag:** keep storing 9 (Vivid) for processing, and store a "FILM selected" flag in a spare persistent settings byte, which the UI maps check to show FILM 1 highlighted. No lens patch. But a real custom look still needs processing work later.
- **B, lens-side:** find where `l08firm3` maps the value to processing, make 8 behave like 9, and later define FILM looks there. This is the route the custom film looks need anyway.

### Round 6 (2026-10-27): FILM 1 v2, its own value 8

**Architecture confirmed from strings:** `l08firm3` contains `SysUnit_FileSendBodyFw()`, `SysUnit_FileSendLensFw()` and `UnitComm_Snd_ViewData`.
- The **camera unit** is the main computer: it stores and sends the body firmware and streams live view to the body.
- The **body** (`ilaunch3`) runs the menus and display, and sends settings to the unit in UnitComm packets.
- The unit (`l08firm3`) does capture and processing.

**Lens-side image-setting converter:** `l08firm3` 0x20199B30 is a jump table (0x2021B93C, base 0x20199B50) mapping the body value (0–11) to a unit colour-mode code:

| Body value | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unit code | 0 | 2 | 3 | 9 | 5 | 6 | 7 | 8 | **9 (= B&W)** | **1 (Vivid)** | 10 | 4 |

- It's used with RAM 0x2043753D → `0x201B013C(code, byte 0x2043753F, byte 0x2043753E)` (probably the colour-mode call), and by 0x20199CE8 / 0x201A9680, which read byte 33 of the lens settings structure.
- **Without the lens patch, body value 8 would shoot B&W.**
- Lens patch: table entry 8 (0x2021B94C) 0x0020 → 0x0000, so 8 → unit 1 (Vivid).

**Body patches for value 8** (`gxr_imgset_patch.py film2 <ilaunch3> <out> 1870`, on top of `eighth --value 8`):
- Six `bra <default> || nop` sites are replaced by 24-bit `bra` into helper code at **0x2010D960** (the unused debug-shell handler for serial command 60; 0x84 of its 0x88 bytes are used):

  | Routine | Site | Purpose | Exits |
  | --- | --- | --- | --- |
  | c1 | 0x20272040 | validator: 8 is valid | ok 0x20272060 / reset 0x20272050 |
  | c2 | 0x20281FD8 | menu: 8 → position 8 | 0x20282004 / default 0x20282000 |
  | c3 | 0x202870EC | ADJ: 8 → position 8 | 0x20287118 / 0x20287114 |
  | c4 | 0x202BB9BC | ADJ position 8 → setter(8) | 0x202BBA2C / 0x202BBA20 |
  | c5 | 0x202850F8 | dial: 8 → index 7 | 0x20285124 / 0x20285120 |
  | c6 | 0x202DD1CC | dial index 7 → setter(8) | 0x202DD23C / 0x202DD230 |

- Dial wrap: 0x202DEB4C `ldi r3,#5` → `#8` (forward wrap after FILM 1); 0x202DEB7C `ldi r3,#6` → `#7` (backward wrap from Vivid to index 7).
- The helper bytes are embedded in the script (`CAVE_CODE`) and were checked against M32R gas/ld output. Source:

```
c1: ldi r0,#8 / bne r2,r0,c1_def / bra 0x20272060 / c1_def: bra 0x20272050
c2: ldi r0,#8 / bne r2,r0,d / ldi r8,#8 / bra 0x20282004 / d: bra 0x20282000
c3: ldi r0,#8 / bne r2,r0,d / ldi r8,#8 / bra 0x20287118 / d: bra 0x20287114
c4: ldi r0,#8 / bne r11,r0,d / seth r0,#0x2026 / or3 r0,r0,#0x8768 / ldi r4,#8 / jl r0 / bra 0x202bba2c / d: bra 0x202bba20
c5: ldi r0,#8 / bne r2,r0,d / ldi r8,#7 / bra 0x20285124 / d: bra 0x20285120
c6: ldi r0,#7 / bne r10,r0,d / seth r0,#0x2026 / or3 r0,r0,#0x8768 / ldi r4,#8 / jl r0 / bra 0x202dd23c / d: bra 0x202dd230
```

**Set:** `FILM 1 v2 separate value (flash with MOUNT A12 attached)/`
- `ilaunch3`: stock + film2, version **1.64**, 260 bytes differ.
- `ilaunch4`: v2 language + "FILM 1" (string 1870).
- `l08firm3`: stock + film2lens, version **1.64**, 3 bytes differ.
- Other files: v2/stock.
- Verified by disassembling the patched file.

**Recovery:** `Recovery stock body+lens v1.70 (lens attached)/` (stock body code and stock lens code, both marked 1.70).

**Expected:** FILM 1 stays highlighted after selection, in the menu, the ADJ lever and dial cycling, and shoots like Vivid. Known cosmetic gap: around 20 display-only chains (e.g. playback info / My Settings screens) don't know value 8 and may show a default label or icon.

**Hardware test of v2 (2026-10-27):** ADJ lever selection and highlight OK, dial cycling OK, shoots like Vivid, stable, and FILM 1 survives a power cycle. **Failed:** opening the menu always highlighted Vivid.

### Round 7 (2026-10-27): FILM 1 v3, menu highlight fix

**Cause:** the menu has 17 copies of the value → highlighted-position chain (one per shooting mode or menu context). They all have the same shape: getter 0x20271FEC, then compares 5/3/1/4/9/6/10, then `ldi r8,#2..#7`, with a default of `ldi r8,#1` (= Vivid). v2 fixed only two of them: c2 (0x20281FD8, records 0x2022DAC4) and c3 (ADJ). The other 15 sent value 8 to position 1.

**Fix:** each remaining chain's `bra <ldi r8,#1> || nop` (the path for values 7 and 8) now branches to a 16-byte helper. The helpers live in a second cave, **0x2010D9EC**: the unused debug-shell handler for serial command 64, 436 bytes, of which 0xF0 are used. Helper template:

```
ldi r0,#8 [-> ldi r8,#8]   ; second ldi only when the tested register isn't r8
bne <reg>,r0,d
bra <default>+4            ; join, with r8 = position 8
d: bra <default>           ; original ldi r8,#1
```

The chain sites are listed in `MENU_CHAINS` in `gxr_imgset_patch.py` (r3 at 0x2027F1FC, r7 at 0x20283044, r8 at the rest). Among them:
- 0x2027F1B0 and 0x20282FF8 set the selection per shooting mode (records 0x202365E0, 0x2022E694 and others).
- 0x2028446C uses records 0x2022EFEC.
- 12 routines at 0x2034B454–0x20355BF4 write directly into the selection bytes of records 0x20230A8C, 0x20231528, … The `eighth` patch had already given all of these list 0x2023F620 with count 8.

A scan for this chain shape found exactly 18 chains. 17 are image-setting chains; the 18th (0x202DC0F4) belongs to a different setting with values 12/8/5/2/1/4.

**Set:** `FILM 1 v3 menu fix (flash with MOUNT A12 attached)/`
- `ilaunch3`: stock + film2 (now including the menu chains), version **1.65**.
- All other files are the same as v2, including `l08firm3` 1.64. That file is already installed, so it doesn't matter if the updater skips it.
- Verified by disassembling the patched file.

**Hardware test of v3 (2026-10-27):** the menu highlight is now correct in all modes, Vivid and Setting2 still highlight correctly, and ADJ, the dial and stability are fine. **But FILM 1 photos look like Standard, not Vivid.**

### Round 8 (2026-10-27): FILM 1 v4, lens colour fix

**Cause:** the body sends the setting unchanged (e.g. `ilaunch3` 0x2011DB54 copies +878 into the packet), so value 8 reaches the unit as 8. `l08firm3` has a **second** converter for the same byte (lens settings +33): **0x2019E784**, a jump table at 0x2021BCFC with base 0x2019E7A4. It is called from the settings-block builder at 0x2019EB54 (result stored at +33 of the output block).

| Body value | 0 | 1–7 | 8 | 9 | 10 | 11 |
| --- | --- | --- | --- | --- | --- | --- |
| Output | 0 | same | **8** | 9 | 0 | 3 |

So the first converter (patched in v2) gave Vivid's colour code, but this block still carried 8, which its consumer evidently treats as Standard.

**Fix:** entry 8 of 0x2021BCFC (0x2021BD0C) 0x001C → 0x0020, so 8 → 9 (Vivid). `film2lens` now patches both tables (`LENS_TABLES8`).

Other lens reads of +33 compare only against 0, 6 and 9:
- The 9 checks (0x20199B8C, 0x20199F3C) gate scene-mode handling via 0x20199B7C, which only matters for scene codes 1–6, 18, 19, 28 and 29.
- Those 9 checks are not patched.

**Set:** `FILM 1 v4 lens colour fix (flash with MOUNT A12 attached)/`
- `l08firm3`: stock + both lens tables, version **1.65**.
- Everything else is the same as v3 (`ilaunch3` 1.65).

**Hardware test of v4 (2026-10-27):** body and lens both show 1.65, but FILM 1 still looks like Standard. Neither lens table explains the look.

**Re-reading the v2 result:** v2 reset the menu selection to Vivid whenever the menu was opened, so the "looks like Vivid" photos were probably real Vivid (value 9). Value 8 has most likely looked like Standard in every build.

**Ruled out (static analysis):**
- **Body conversion:** the body has no other value lookup or conversion before sending.
  - Getter and +878 reads: no table indexing.
  - The only Vivid-specific (value 9) check is the dial wrap.
  - 0x2011DB54 copies +878 raw, and 0x2026F3FC is a save/restore.
- **Lens 0x201F7FB0:** it has 58 cases, so it handles scene modes, not Image Settings.
- **Lens 0x201B013C** (colour-mode switch on the table-1 code): its cases are 2/3/4/5/6/9/10. Code 1 (Vivid) and 0 use the default path.

### Round 9 (2026-10-27): maker notes solve it; FILM 1 v5 lens block override

**Photos:** `vivid.jpg`, `standard.jpg`, `film1.jpg` (same scene, v4 firmware). The Ricoh maker note tag 0x1001 is a 224-byte block:
- Byte 40 = Image Settings value: Vivid 9, Standard 1, FILM 1 **8**. So value 8 reaches the unit intact.
- Bytes 48–51 and 120–129 come from a **15-byte Image Settings block** that the body sends. The lens copies it into its settings struct at +267..+281 (0x2019787C / 0x20197E20), and the routine **0x201999E4** returns it for both processing (it calls 0x200A9248 with 15 bytes) and the maker note (builder 0x2019B8xx, then 0x201735xx).

  | | setting | | levels | trailing 10 |
  | --- | --- | --- | --- | --- |
  | Vivid | 9 | 0 | 5 5 5 | 3 3 3 3 3 3 3 2 2 2 |
  | Standard | 1 | 0 | 3 4 3 | 3 3 3 3 3 3 3 2 2 2 |
  | FILM 1 | 8 | 0 | 3 3 3 | 3 3 3 3 3 3 3 3 3 3 |

- EXIF Sharpness: Vivid hard, the others normal.
- The body fills the block per setting, and FILM 1 gets all neutral defaults (3). That's the "Standard-like" look. Where the body builds the block isn't found yet; a search for the obvious row tables found nothing.

**The byte-33 assumption was wrong.** Lens +33 is a different field (maker note byte 38, 0 in all three shots). The v2/v4 lens table patches (0x2021B94C, 0x2021BD0C) changed that unrelated field's value 8, so **v5 drops them**.

**v5 lens patch** (`film2lens`, `l08firm3` **1.66**):
- 0x20199B14 (`seth r0,#0x200a`, just before the 15-byte copy-out) → `bra` to a helper at **0x20078548**. That is the lens serial-console `ver` command handler, referenced only by the command table at 0x200C6F90.
- If the block's setting byte (sp+4) is 8, the helper writes `VIVID_BLOCK` over sp+4..sp+18. Either way it then runs the original `seth` and branches back to 0x20199B18. The helper is 140 bytes, verified by disassembly.
- FILM 1 now gets exactly Vivid's block, so its maker note will also say 9. To give FILM 1 its own look later, change `VIVID_BLOCK` (levels at bytes 2–4, trailing bytes 5–14).

**Set:** `FILM 1 v5 lens block fix (flash with MOUNT A12 attached)/`
- `l08firm3` is stock + this block override, version 1.66.
- All other files are the same as v4 (`ilaunch3` 1.65).

**Hardware test of v5 (2026-10-27):** FILM 1 looks like Vivid. The maker notes of `vivid2.jpg` and `film1_2.jpg` have identical blocks: 0 / 5 5 5 / 3 3 3 3 3 3 3 2 2 2, with EXIF Sharpness hard. Byte 40 still records 8.

### Round 10 (2026-10-27): renamed to KODACHROME; decoding the block

**What the block bytes mean.** The menu strings and the [Ricoh GXR FAQ](https://www.ricoh-imaging.co.jp/english/r_dc/support/faq/bp/gxr/06/gxr06013.html) describe Setting1/2 as:
- Vividness, Contrast and Sharpness.
- Individual Color Settings: Hue and Vividness for five colours (Orange, Greens, Blues, Reds, Magenta).

So the block is most likely: setting, 0, three levels (Vividness / Contrast / Sharpness in some order), then 5 + 5 colour bytes. The lens unpacks these from nibbles at 0x201998DC. Value 3 is neutral. The exact order and scale are **not confirmed**.

**Plan:** the user dials a Kodachrome recipe into Setting1 and shoots it. The maker note of that shot then gives the exact block bytes, which become the KODACHROME block (`VIVID_BLOCK` → a new block).

**Set:** `KODACHROME v6 label (flash with MOUNT A12 attached)/`
- `ilaunch4` = v2 + string 1870 "KODACHROME" (`addstring`), version 1.51.
- Everything else is the same as v5. The block is still Vivid's.

### Round 11 (2026-10-28): KODACHROME look from a Setting1 recipe (v7)

**Recipe:** the user dialled the suggested recipe into Setting1 and shot `Test photos/setting1_kodachrome.JPG`.

**Maker note result:** setting 4, block 0 / 5 4 4 / 4 2 5 5 2 / 3 4 3 3 3, EXIF sharpness normal. This confirms the block layout in "How it works": contrast +2 → 5, vividness/sharpness +1 → 4, colour vividness in the order Orange, Greens, Blues, Reds, Magenta, then colour hue in the same order.

**Patch:** `KODACHROME_BLOCK = [4, 0, 5, 4, 4, 4, 2, 5, 5, 2, 3, 4, 3, 3, 3]` (`FILM_BLOCK` points at it). `film2lens` writes it in place of the value-8 block. Verified by reading back the helper's immediates.

**Set:** `KODACHROME v7 look (flash with MOUNT A12 attached)/`
- `l08firm3` is version 1.67.
- Everything else is the same as v6 (`ilaunch3` 1.65, `ilaunch4` with KODACHROME).

**Hardware test of v7 (2026-10-28): works.** KODACHROME looks the same as the Setting1 recipe. After Setting1 was changed to very different values, KODACHROME stayed the same. So the lens uses the block itself, and a setting byte of 4 is a safe base for fixed looks.

### Round 12 (2026-10-28): 9th entry PORTRA 400 (v8)

**Recipe research.** Community Portra 400 recipes (Fuji X Weekly v2, Shuttergroove) share these traits:
- a muted base (Classic Chrome)
- highlights −1 and shadows −1, i.e. lower contrast
- colour +2 on that muted base, so moderate overall
- warm white balance (Daylight, about +1 red, −5 blue)

The look is known for soft contrast, natural warm skin tones, and gentle greens and blues.

**GXR translation** (`PORTRA400_BLOCK = [4, 0, 2, 3, 3, 4, 2, 2, 3, 2, 3, 4, 3, 3, 3]`):

| Setting | Value |
| --- | --- |
| Contrast | −1 |
| Vividness | 0 |
| Sharpness | 0 |
| Orange vividness | +1 |
| Greens vividness / hue | −1 / +1 (toward yellow) |
| Blues vividness | −1 |
| Reds vividness | 0 |
| Magenta vividness | −1 |

White balance is not in the block. Suggested on the camera: Daylight with a slight amber shift, exposure +1/3 to +2/3.

**Body (`films`):** see "How it works". The generated helpers are 0x60 bytes in cave 1 and 0x10C in cave 2, including the two tables. Verified by disassembly:
- each chain branch goes to its helper, with joins identical to v3
- ADJ position 8/9 → setter(8/7), dial index 7/8 → setter(8/7)
- 25 records → new list, count 9
- position table 1–9 = 9 1 10 3 6 4 5 8 7

**Lens (`filmslens`):** a helper of 276 bytes. 8 → KODACHROME block (unchanged), 7 → PORTRA 400 block.

**Set:** `KODACHROME + PORTRA 400 v8 (flash with MOUNT A12 attached)/`
- `ilaunch3` 1.66, `l08firm3` 1.68.
- `ilaunch4` has strings 1870 KODACHROME and 1871 PORTRA 400.
- All 8 files pass verification.

**Risk:** value 7 was the leftover "Sepia" slot. No body or lens code was found treating it specially, but display-only screens may show a default icon or label.

### Round 13 (2026-10-28): Sepia restored, 10 entries, all units (v9)

**User report on v8:** PORTRA 400, which used value 7 (the hidden Sepia slot), offered Setting1/2-style adjustments. So value 7 is a real, working Sepia mode.

**Request:** restore Sepia, order Setting2 → Sepia → KODACHROME → PORTRA 400, and support all units (the user owns all six).

**Body:**
- Sepia = value 7 at position 8, with the original label (string 667).
- KODACHROME = value 8 at position 9.
- PORTRA 400 moves to value 2 at position 10.
- See "How it works" for the helper scheme. 40 branches are redirected; cave 1 is exactly full (0x88), cave 2 uses 0x180 of 0x1B4.
- Verified by disassembly: every cave entry branch (39 external) lands in the caves.

**Bug found and fixed:** six of the 15 extra menu chains test **r2**, not r8: 0x2034E88C, 0x2034FE28, 0x203505EC, 0x20351B78, 0x20352640, 0x20355C40. Since v3 those screens (likely My Settings) would have highlighted Vivid for value 8. `films` now checks each chain's register in the code (`ldi r0,#6 / beq <reg>,r0`) and refuses to build on a mismatch.

**All units:** the block routine and the serial-console `ver` handler exist in every unit's code module, with the same layout:

| Unit | Code module | Block call site | `ver` handler (helper) |
| --- | --- | --- | --- |
| MOUNT A12 | l08firm3 | 0x20199B14 | 0x20078548 |
| A12 50mm | jlaunch3 | 0x2019A320 | 0x20078544 |
| S10 | klaunch3 | 0x20199424 | 0x20078514 |
| P10 | nlaunch3 | 0x201A160C | 0x20078544 |
| A12 28mm | qlaunch3 | 0x2019D720 | 0x20078544 |
| A16 | l06firm3 | 0x2019C428 | 0x20078480 |

Each unit's helper is 276 bytes. The S10 helper was checked by disassembly.

**Not verified:** the compact units (S10, P10) have different image engines. If their block meaning differs, the looks may render differently there. Compare their maker notes.

**Sets:**
- `Sepia + KODACHROME + PORTRA 400 v9 (all units - flash once per unit attached)/`: 29 files.
- `Recovery stock all units v1.90 (flash once per unit attached)/`: 29 files.
- All 58 files pass verification.

### Round 14 (2026-10-28): v9 result, per-option table fix (v10)

**v9 result (user):** all 10 entries are in place. But:
- An adjustments page appeared on **KODACHROME** (position 9) and didn't work. In v8 it had appeared on PORTRA 400, which was also at position 9.
- Shooting-screen icons: PORTRA 400 shows a Sepia-like icon; Sepia and KODACHROME show none.

**Cause of the adjustment page:** each Image Settings record's +12 points at per-option data at 0x20236048. The table has 8 bytes per option, and byte 6 = 1 means "no adjustments": Vivid/Standard/Natural 1, B&W/TE/S1/S2 0. It has only 7 entries, so positions 8–10 read the bytes that follow it, and position 9 happened to get 0. The adjustment page is position-driven, not a Sepia feature.

**Fix (v10):** a 10-entry copy of the table in cave 3 (0x2010D70C, the unused serial command-9 handler, 0x12C bytes; the function at 0x2010D838 after it is in use and untouched). Entries 8–10 copy Vivid's. The 24 records' +12 pointers are repointed; the compact ADJ entry has no per-option data. Verified: byte 6 for entries 1–10 = 1 1 1 0 0 0 0 1 1 1.

**Icons (open):**
- [ExifTool's Ricoh ImageInfo table](https://exiftool.org/TagNames/Ricoh.html) lists byte 40 values 0 = High, 1 = Normal, 2 = Low saturation, 3 = B&W, 6 = Toning, 9 = Vivid, 10 = Natural. So value 2 is a legacy "low saturation" mode with its own icon, not Sepia.
- 0x202E673C maps value → state code (0→1, 2→3, 3→4, 6→5, 4→6, 5→7, 9→14, 10→15, else 2) for a "setting at default?" check (0x202E863C). It's not the icon drawer.
- The shooting-screen icon index (layout byte 45, via the global record G+42) is filled by bulk copies. Its value → index source isn't found yet.

**Sets:**
- `Sepia + KODACHROME + PORTRA 400 v10 (all units - flash once per unit attached)/`: `ilaunch3` 1.68; everything else identical to v9.
- v9 is archived.

### Round 15 (2026-10-29): ADJ lever hint (v11)

**v10 result (user):** the MENU no longer shows an adjustment page on KODACHROME. The ADJ lever still shows an "adjustments available" hint on it, and pressing does nothing.

**Findings:**
- The adjustments *action* is hard-coded in both paths. MENU: cursor positions 4–7 only (0x202C84CC `cmpui #4` / `cmpui #8`, then 6→1, 7→2, 4→4, 5→3 into 0x2028A04C). ADJ lever: values 4, 5, 3, 6 only (0x202BE240). So the new entries (and Sepia) can never open a working adjustment page without new code; the hint must simply be off for them.
- Besides the 24 count-10 records, two **count-6** Image Settings records (0x2022EE40, 0x2022EF3C, stock list 0x2022D610) still pointed their per-option data at the old 7-entry table 0x20236048. Reading past its end gives byte 6 = 1, 0, 1 for positions 8, 9, 10, exactly the reported pattern (hint on KODACHROME only).

**Fix (v11):** `films` also repoints those two records' per-option pointer to the 10-entry table in cave 3 (count left at 6). Diff against v10: only those two pointers, version and checksum.

**Sets:**
- `Sepia + KODACHROME + PORTRA 400 v11 (all units - flash once per unit attached)/`: `ilaunch3` 1.69; everything else identical to v10 (units stay 1.69, so only the body module installs).
- v10 is archived.

### Round 16 (2026-10-29): v11 result, swap test

**v11 result (user, body 1.69 confirmed):** B&W, TE, Setting1, Setting2 hints and adjustments fine. KODACHROME still shows the ADJ-lever hint "press DISP for detailed settings" (DISP does nothing). Sepia and PORTRA 400 show no hint. So the two six-entry records weren't the source.

**Ruled out:** every Image Settings record (24 + 2 + the ADJ entry) now uses the 10-entry per-option table; icons, labels and per-option bytes are identical for entries 8–10; the ADJ per-item flag lists (12-byte entries at 0x2022F560, `[count, flags…]`) give Image Settings none; the DISP action 0x202BE240 is value-based (3/4/5/6). The hint is decided by code not yet found, reading either value 8 or position 9 out of range.

**Test build:** `TEST swap - PORTRA 400 at 9, KODACHROME at 10 (flash with one unit only)/` (`gxr_imgset_patch.py filmsswap`, body 1.70). Helpers: 7/8 → position 2v − 6 (8, 10), 2 → 9; dial index 2v − 7 (7, 9), 2 → 8; dial wraps after value 8. If the hint moves to PORTRA 400, it's position 9; if it stays on KODACHROME, it's value 8.

**Recovery relabelled** from 1.70 to 1.90 (code `*3` files only; folders renamed) so test and final builds can use 1.70+.

### Round 17 (2026-10-29): swap result, Auto Bracket table (v12)

**Swap test result (user):** the hint moved to PORTRA 400 (now 9th). So it follows **list position 9**, not the setting value.

**Finding:** the hint pattern for positions 8/9/10 (no/yes/no) matches the bytes just past the old 7-entry per-option table 0x20236048. Those bytes are Auto Bracket's per-option table 0x20236080 (6 entries; 12 records, list 0x2022D560), whose entries 1/2/3 have byte 6 = 1/0/1. Nothing in the file still points at 0x20236048, so the reader's route is unknown (possibly a base pointer built at run time). This is still a hypothesis.

**v12 (`films`):** Auto Bracket's table is copied to cave 3 right after the 10-entry Image Settings table (0x2010D75C, 48 bytes) and its 12 records are repointed. The old area's first three entries (0x20236080..97) are then written as "no adjustments" (only 0x2023608E changes, 0 → 1). Diff against v11: those bytes, 12 pointers, version and checksum. If the hint stays, the hypothesis is wrong and nothing else is affected (Auto Bracket uses an identical copy).

**Sets:**
- `Sepia + KODACHROME + PORTRA 400 v12 (all units - flash once per unit attached)/`: `ilaunch3` 1.71; units unchanged at 1.69.
- v11 and the swap test are archived.

### Round 18 (2026-10-29): the "Detail [DISP]" hint table (v13)

**v12 result (user):** hint still on KODACHROME, so the Auto Bracket theory was wrong. v13 drops that change.

**Found via screen photos** (`Test photos/IMG_1301/1302/1306.HEIC`): the hint is the text "Detail" (string 501, slot 0x205BEAD4) plus a DISP icon beside the highlighted row. Searching data for that string pointer found per-position hint tables of 12-byte rows `(string, icon 0x2023FFCA, 0)`:
- 0x2023FD38: Image Settings, 8 rows (positions 4–7 = Detail). Read at 0x201FEBE4/E8 when the ADJ item (r11) is 5.
- 0x2023FD8C: the next table (item 9). Its row 2 (= Image Settings position 9) is "Detail", and row 3 (position 10) is empty. That's why only position 9 showed the hint.

**Fix (v13, `films`):** a 10-row copy in cave 3 after the 10-entry per-option table (0x2010D75C, 120 bytes; rows 8–10 empty), and the seth/or3 at 0x201FEBE4/E8 repointed. Diff against v11: those 120 bytes, the reference, version and checksum.

**Sets:** `Sepia + KODACHROME + PORTRA 400 v13 (all units - flash once per unit attached)/`: `ilaunch3` 1.72; units unchanged at 1.69. v12 is archived.

**v13 result (user, 2026-10-30): works fine.** The ADJ lever hint is gone from KODACHROME.

### Test log (language patch)


- 2026-10-27: patched 1.51 `*4` files flashed fine. Selecting Japanese showed garbled text. Cause: font page mask (see Text encoding). Fixed in the v2 set. The same 1.51 version flashed fine, so v2 is kept at 1.51.
- 2026-10-27: flashed `Patched 1.51 v2`. **Works:** selecting Japanese now shows Traditional Chinese menus correctly.

