#!/usr/bin/env python3
"""Read-only vertex attribute probe for SENRAN KAGURA Burst Re:Newal CAT/TMD blocks 4 and 5.
Does not modify the input archive. Writes a UTF-8 text report.
Usage:
  python probe_vertex_attributes.py "/storage/emulated/0/GAMES/PC/SENRAN KAGURA Burst Re Newal/GameData/Model/Field/bg00.cat"
"""
import os, sys, struct, math
from collections import Counter

BLOCKS = [
    ("block4", 0x24F200, 24336, 28392),
    ("block5", 0x335100, 46032, 33291),
]
STRIDE = 28

def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]

def f32(data, off):
    return struct.unpack_from("<f", data, off)[0]

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else (
        "/storage/emulated/0/GAMES/PC/SENRAN KAGURA Burst Re Newal/"
        "GameData/Model/Field/bg00.cat"
    )
    if not os.path.isfile(path):
        raise SystemExit("ERROR: file not found: " + path)
    with open(path, "rb") as f:
        data = f.read()

    out = []
    out += ["SENRAN KAGURA - BLOCK 4/5 VERTEX ATTRIBUTE PROBE",
            "READ ONLY - input CAT is never modified",
            "File: " + path, "File size: %d bytes" % len(data),
            "Candidate layout (to be validated): XYZ float32 @+0x00, packed normal @+0x0C, RGBA @+0x10, UV0 uint16x2 @+0x14, UV1 uint16x2 @+0x18",
            "NOTE: offsets after XYZ are hypotheses, not confirmed format documentation.", ""]
    for name, base, tri_count, vertex_count in BLOCKS:
        if base + 0xDC + 4 > len(data):
            raise SystemExit("ERROR: block header outside file: " + name)
        rel_start = u32(data, base + 0x90)
        start = base + rel_start
        header_count = u32(data, base + 0xDC)
        if header_count != vertex_count:
            out.append("WARNING %s: header vertex count %d != expected %d" % (name, header_count, vertex_count))
            vertex_count = header_count
        end = start + vertex_count * STRIDE
        if start < base or end > len(data):
            raise SystemExit("ERROR: vertex span outside file for %s: 0x%X..0x%X" % (name, start, end))
        records = [data[start+i*STRIDE:start+(i+1)*STRIDE] for i in range(vertex_count)]
        out += ["="*72, "%s base=0x%X vertex_start=0x%X count=%d stride=%d" %
                (name, base, start, vertex_count, STRIDE),
                "Triangles: %d; vertex bytes: %d" % (tri_count, vertex_count*STRIDE), "",
                "FIRST 12 RAW RECORDS"]
        for i, r in enumerate(records[:12]):
            xyz = struct.unpack_from("<3f", r, 0)
            nraw = struct.unpack_from("<4b", r, 12)
            rgba = tuple(r[16:20])
            uv0 = struct.unpack_from("<2H", r, 20)
            uv1 = struct.unpack_from("<2H", r, 24)
            nxyz = tuple(max(-1.0, x/127.0) for x in nraw[:3])
            mag = math.sqrt(sum(x*x for x in nxyz))
            out.append("v%02d XYZ=%s N_s8=%s N_norm=%s |N|=%.5f RGBA=%s UV0=%s UV1=%s RAW=%s" %
                (i, tuple(round(x,6) for x in xyz), nraw, tuple(round(x,5) for x in nxyz),
                 mag, rgba, uv0, uv1, r.hex(" ")))
        out += ["", "ATTRIBUTE STATISTICS (all vertices)"]
        for label, fn in [
            ("normal byte +0C..+0E", lambda r: tuple(struct.unpack_from("<3b",r,12))),
            ("color +10..+13", lambda r: tuple(r[16:20])),
            ("UV0 uint16 +14", lambda r: struct.unpack_from("<2H",r,20)),
            ("UV1 uint16 +18", lambda r: struct.unpack_from("<2H",r,24)),
        ]:
            vals = [fn(r) for r in records]
            flat = [x for v in vals for x in v]
            out.append("%s: min=%s max=%s unique=%d" %
                       (label, min(flat), max(flat), len(set(vals))))
            out.append("  common=%s" % Counter(vals).most_common(8))
        xyzs = [struct.unpack_from("<3f",r,0) for r in records]
        bad = sum(not all(math.isfinite(x) and abs(x)<1e20 for x in p) for p in xyzs)
        out.append("Invalid XYZ records: %d" % bad)
        ns = []
        for r in records:
            n = struct.unpack_from("<3b",r,12)
            nv = tuple(max(-1.0,x/127.0) for x in n)
            ns.append(math.sqrt(sum(x*x for x in nv)))
        out.append("Packed-normal candidate length: min=%.5f max=%.5f mean=%.5f" %
                   (min(ns), max(ns), sum(ns)/len(ns)))
        out.append("")
    report = "\n".join(out) + "\n"
    dest = os.path.join(os.path.dirname(os.path.abspath(path)), "senran_block4_5_vertex_probe.txt")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print("\nSAVED:", dest)

if __name__ == "__main__":
    main()
