# Ricoh GXR firmware mods

Patch scripts for Ricoh GXR firmware **1.51** that add three Image Settings entries:

| | Entry | What it is |
| --- | --- | --- |
| 8 | **Sepia** | A working sepia mode Ricoh left hidden in the firmware |
| 9 | **KODACHROME** | A fixed colour look (contrast +2, rich reds and blues) |
| 10 | **PORTRA 400** | A fixed colour look (low contrast, warm, soft greens and blues) |

The new entries work like the stock ones:
- They're selectable from the MENU, the ADJ lever and dial cycling.
- They stay highlighted.
- They survive power-off.

Optionally, the Japanese menu language slot can show **Traditional Chinese**, for Japanese-market cameras that offer only Japanese and English.

The scripts patch Ricoh's original firmware files on your computer. **This repository contains no Ricoh firmware**; download it from Ricoh yourself.

## Status

Tested on hardware: a GXR body with all six camera units, 2026-10. The default build is byte-identical to the tested set, and `build.py` confirms this when it finishes.

| | |
| --- | --- |
| Works | All 10 entries in the MENU and ADJ lever; selection, highlight and dial cycling; KODACHROME and PORTRA 400 looks; Sepia; the Chinese menu slot |
| Cosmetic | The shooting-screen icon is missing for Sepia and KODACHROME, and PORTRA 400 shows a legacy icon |
| Not offered | An adjustments page for the three new entries. The firmware hard-codes that page to B&W, B&W (TE), Setting1 and Setting2. |
| Unverified | Whether the looks render the same on the S10 and P10 compact units |

## ⚠️ Read this first

- **Flashing modified firmware can brick your camera.** There is no warranty of any kind. You use this at your own risk.
- Use a fully charged battery and never interrupt an update.
- Build the **recovery set** before you flash anything, and keep it on hand (see below).

## Requirements

- Python 3.8 or later. It uses only the standard library and runs on macOS, Linux and Windows.
- Ricoh's GXR firmware 1.51 (`gxr-151.zip`), from the [Ricoh GXR firmware page](https://www.ricoh-imaging.co.jp/english/r_dc/download/firmware/gxr/). Unzip it and keep the 29 files (`ilaunch0` … `qlaunch8`) together in one folder.

`build.py` checks every input file against the SHA-256 list in `checksums/stock-1.51.sha256`. It refuses to build from anything else.

## Build

```
python3 build.py path/to/gxr-151 out
```

This writes 29 files to `out/`:

| File | Change |
| --- | --- |
| `ilaunch3` | Body program with 10 entries (version 1.72) |
| `ilaunch4` | Text, with the two new labels |
| `l08firm3`, `jlaunch3`, `klaunch3`, `nlaunch3`, `qlaunch3`, `l06firm3` | Every camera unit's program with the looks (version 1.69) |
| All others | Stock |

Options:

| Option | Effect |
| --- | --- |
| `--no-cht` | Keep the Japanese slot in Japanese. This build is untested on hardware, but the only difference is that the language redirect is left out. |
| `--label9 TEXT`, `--label10 TEXT` | Rename the new entries. Labels may use only A–Z, 0–9, space and `! & ' ( ) + - . / : * _ ~ [ ] ,`, because that font page is loaded in every language. |
| `--body-version`, `--unit-version` | Version numbers to write. They must be higher than what's installed (see below). |

## Flash

1. Copy the 29 files from `out/` to the SD card, following Ricoh's update instructions for the stock firmware.
2. Attach a camera unit and run the update.
3. **Repeat step 2 with each of your other camera units attached.** Each unit stores its own copy of the body program, so a body change only shows with the units that were attached while you flashed.

Two update rules matter:
- **The camera installs a program module (`*3`) only if its version is newer than the installed one.** Stock is 1.51 and this build is 1.72 / 1.69. If you rebuild with changes, raise the version each time.
- **Text modules (`*4`) install at any version.**

## Undo

```
python3 build.py recovery path/to/gxr-151 recovery
```

This gives stock programs for the body and every unit, labelled version **1.90** so the camera accepts them over the patched ones. Flash it the same way: once per unit attached. Add `--cht` to keep the Chinese menu slot.

## Customise the looks

The looks are 15-byte Image Settings blocks in `LOOKS` in `gxr_imgset_patch.py`. They're keyed by setting value: 8 = KODACHROME, 2 = PORTRA 400.

To make your own look:

1. Dial the look into **Setting1** on the camera and take a photo.
2. Run `python3 gxr_exifdump.py photo.jpg`. Maker note tag 0x1001 contains the block (layout in [docs/ADDRESSES.md](docs/ADDRESSES.md#the-15-byte-image-settings-block)).
3. Put those bytes in `LOOKS`, then rebuild with a higher `--unit-version`.

## Tools

| Script | Purpose |
| --- | --- |
| `build.py` | Builds the full set, or the recovery set |
| `gxr_lang_patch.py` | Checksum `verify`, version, language redirect `patch`, `addstring`, `rename` |
| `gxr_imgset_patch.py` | Image Settings patches: `films` (body), `filmslens` (units), plus earlier experiments |
| `gxr_exifdump.py` | Dumps EXIF and the Ricoh maker note of a JPEG |
| `gxr_patchmap.py` | Lists every changed address between a stock and a patched `*3` |

Every patch step checks the bytes it expects before writing, and refuses to run on other firmware versions.

## Documentation

- [docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md): the file format and checksum, how updates install, and how each patch works
- [docs/ADDRESSES.md](docs/ADDRESSES.md): every changed address, the code caves, and the tables
- [docs/DEVELOPMENT-LOG.md](docs/DEVELOPMENT-LOG.md): the full investigation, including the dead ends

## Legal

This is an independent hobby project, not affiliated with or endorsed by Ricoh or Kodak.
- **Trademarks:** "Ricoh" and "GXR" are trademarks of Ricoh. "Kodachrome" and "Portra" are trademarks of Kodak, used here only to describe the look the presets imitate. Use `--label9` / `--label10` to name them differently.
- **No firmware:** the repository contains no Ricoh firmware or code. It holds only the scripts, documentation, the checksums of Ricoh's files, and the short byte sequences needed to verify and patch them.
- **Don't publish builds:** don't commit Ricoh's files or the files the build produces.

Licensed under the [MIT License](LICENSE).
