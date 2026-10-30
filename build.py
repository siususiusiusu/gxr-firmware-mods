#!/usr/bin/env python3
"""Build the patched Ricoh GXR firmware set from Ricoh's stock 1.51 files.

  build.py <stock dir> <out dir> [options]
      --no-cht               keep Japanese in the Japanese menu slot
                             (default: it shows Traditional Chinese)
      --body-version X.YY    ilaunch3 version (default 1.72)
      --unit-version X.YY    camera unit *3 versions (default 1.69)
      --label9 TEXT          9th entry label (default KODACHROME)
      --label10 TEXT         10th entry label (default PORTRA 400)
      --force                build even if the input isn't stock 1.51

  build.py recovery <stock dir> <out dir> [--version 1.90] [--cht]
      stock code for the body and every unit, relabelled with a higher
      version so the camera accepts it over a patched build

<stock dir> holds the 29 files from Ricoh's gxr-151.zip. Labels may use
A-Z, 0-9, space and ! & ' ( ) + - . / : * _ ~ [ ] , only.
With the defaults the output is byte-identical to the hardware-tested v13 set.
"""
import contextlib
import hashlib
import io
import os
import shutil
import sys
import tempfile

import gxr_imgset_patch as img
import gxr_lang_patch as lang

HERE = os.path.dirname(os.path.abspath(__file__))
UNITS = ["l08firm3", "jlaunch3", "klaunch3", "nlaunch3", "qlaunch3", "l06firm3"]


def manifest(name):
    with open(os.path.join(HERE, "checksums", name)) as f:
        return {fn: h for h, fn in (line.split() for line in f if line.strip())}


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def quiet(fn, *args, **kw):
    """Run a patch step, showing its output only if it fails."""
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            return fn(*args, **kw)
    except SystemExit:
        sys.stdout.write(out.getvalue())
        raise


def check_stock(src, force):
    stock = manifest("stock-1.51.sha256")
    missing = [f for f in stock if not os.path.isfile(os.path.join(src, f))]
    if missing:
        raise SystemExit(f"{src}: missing {', '.join(missing)}")
    changed = [f for f in stock if sha256(os.path.join(src, f)) != stock[f]]
    if changed and not force:
        raise SystemExit(f"not stock 1.51: {', '.join(changed)} (use --force to build anyway)")
    return list(stock)


def start(src, dst, force):
    files = check_stock(src, force)
    if os.path.exists(dst) and os.listdir(dst):
        raise SystemExit(f"{dst} is not empty")
    os.makedirs(dst, exist_ok=True)
    for f in files:
        shutil.copyfile(os.path.join(src, f), os.path.join(dst, f))
    return files


def string_count(path):
    d = open(path, "rb").read()
    off, size, _ = lang.entry_span(d, lang.find_entry(d, "com_main_eng.res"))
    return d[off:off + size].count(0)


def finish(dst, files):
    if not quiet(lang.verify, [os.path.join(dst, f) for f in files]):
        raise SystemExit("checksum verification failed")
    print(f"{len(files)} files written to {dst}, all checksums OK")


def build(src, dst, cht=True, body="1.72", unit="1.69",
          label9="KODACHROME", label10="PORTRA 400", force=False):
    for label in (label9, label10):
        bad = sorted({c for c in label if c not in lang.P1})
        if bad or not label:
            raise SystemExit(f"label {label!r}: not in the all-language font page: {''.join(bad)!r}")
    files = start(src, dst, force)
    with tempfile.TemporaryDirectory() as t:
        tmp = lambda n: os.path.join(t, n)
        # text: language redirect, then the two new labels
        l4 = os.path.join(src, "ilaunch4")
        if cht:
            quiet(lang.patch, l4, tmp("l4a"), "com_main_jpn.res", "com_main_chintrad.res", share=True)
            l4 = tmp("l4a")
        n = string_count(l4)
        quiet(lang.add_string, l4, tmp("l4b"), label9)
        quiet(lang.add_string, tmp("l4b"), os.path.join(dst, "ilaunch4"), label10)
        print(f"ilaunch4: {'Japanese slot -> Traditional Chinese, ' if cht else ''}"
              f"labels {label9!r} (string {n}), {label10!r} (string {n + 1})")
        # body: 10 Image Settings entries
        quiet(img.films, os.path.join(src, "ilaunch3"), tmp("il3"), n, n + 1)
        quiet(lang.set_version, tmp("il3"), os.path.join(dst, "ilaunch3"), body)
        print(f"ilaunch3: 10 Image Settings entries, version {body}")
        # every camera unit: the looks
        for u in UNITS:
            quiet(img.films_lens, os.path.join(src, u), tmp(u))
            quiet(lang.set_version, tmp(u), os.path.join(dst, u), unit)
        print(f"{', '.join(UNITS)}: looks, version {unit}")
    finish(dst, files)
    tested = manifest("v13-tested.sha256")
    if all(sha256(os.path.join(dst, f)) == tested[f] for f in files):
        print("identical to the hardware-tested v13 build")


def recovery(src, dst, version="1.90", cht=False, force=False):
    files = start(src, dst, force)
    for f in ["ilaunch3"] + UNITS:
        quiet(lang.set_version, os.path.join(dst, f), os.path.join(dst, f), version)
    if cht:
        p = os.path.join(dst, "ilaunch4")
        quiet(lang.patch, p, p, "com_main_jpn.res", "com_main_chintrad.res", share=True)
    print(f"stock code for the body and all units at version {version}"
          + (", Japanese slot -> Traditional Chinese" if cht else ""))
    finish(dst, files)


def version_ok(v):
    try:
        major, minor = v.split(".")
        return len(minor) == 2 and 0 <= int(major) <= 99 and int(minor) >= 0
    except ValueError:
        return False


def main(args):
    flags = {"--no-cht", "--cht", "--force"}
    opts, pos, i = {}, [], 0
    while i < len(args):
        if args[i] in flags:
            opts[args[i]] = True
            i += 1
        elif args[i].startswith("--") and i + 1 < len(args):
            opts[args[i]] = args[i + 1]
            i += 2
        else:
            pos.append(args[i])
            i += 1
    for k in ("--body-version", "--unit-version", "--version"):
        if k in opts and not version_ok(opts[k]):
            raise SystemExit(f"{k} must look like 1.72")
    if pos[:1] == ["recovery"] and len(pos) == 3:
        recovery(pos[1], pos[2], opts.get("--version", "1.90"), "--cht" in opts, "--force" in opts)
    elif len(pos) == 2:
        build(pos[0], pos[1], "--no-cht" not in opts, opts.get("--body-version", "1.72"),
              opts.get("--unit-version", "1.69"), opts.get("--label9", "KODACHROME"),
              opts.get("--label10", "PORTRA 400"), "--force" in opts)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
