#!/usr/bin/env python3
"""Dump EXIF and Ricoh maker-note tags of a GXR JPEG.

Maker note tag 0x1001 (224 bytes): byte 40 = Image Settings value, bytes
48-51 and 120-129 = the 15-byte Image Settings block (see docs/ADDRESSES.md).

Usage: gxr_exifdump.py <photo.jpg>
"""
import struct,sys
def load(p):
    d=open(p,'rb').read()
    i=2
    while i<len(d):
        assert d[i]==0xFF; m=d[i+1]; n=struct.unpack('>H',d[i+2:i+4])[0]
        if m==0xE1 and d[i+4:i+10]==b'Exif\0\0': return d[i+10:i+2+n]
        i+=2+n
def ifd(t,off,e,base=0,limit=400):
    out={}
    n=struct.unpack(e+'H',t[off:off+2])[0]
    if n>limit: return out
    for k in range(n):
        p=off+2+12*k
        tag,typ,cnt=struct.unpack(e+'HHI',t[p:p+8])
        sz={1:1,2:1,3:2,4:4,5:8,6:1,7:1,8:2,9:4,10:8}.get(typ,1)*cnt
        raw=t[p+8:p+12] if sz<=4 else t[base+struct.unpack(e+'I',t[p+8:p+12])[0]:][:sz]
        if typ==3: v=struct.unpack(e+'%dH'%cnt,raw[:2*cnt]) if cnt<64 else raw[:2*cnt].hex()
        elif typ==4: v=struct.unpack(e+'%dI'%cnt,raw[:4*cnt]) if cnt<64 else raw.hex()
        elif typ==2: v=raw.rstrip(b'\0')
        else: v=raw[:min(sz,200)].hex() if sz>4 or typ in(7,1) else raw.hex()
        out[tag]=(typ,cnt,v,p)
    return out
t=load(sys.argv[1]); e='>' if t[:2]==b'MM' else '<'
i0=ifd(t,struct.unpack(e+'I',t[4:8])[0],e)
ex=ifd(t,i0[0x8769][2][0],e)
for k,v in sorted(ex.items()): print('EXIF %04x'%k,v[:3] if k!=0x927c else (v[0],v[1]))
mn_typ,cnt,_,p=ex[0x927c]; off=struct.unpack(e+'I',t[p+8:p+12])[0]
mn=t[off:off+cnt]; print('MN head',mn[:16])
# Ricoh: "Ricoh\0\0\0" or "RICOH\0II*..."? find IFD
start=8 if mn[:5] in (b'Ricoh',b'RICOH') else 0
me=e
r=ifd(t,off+start,me,base=0)
for k,v in sorted(r.items()): print('MN %04x'%k,v[:3])
