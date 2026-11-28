#!/usr/bin/env python3
"""Diagnostic OBJ exporter for SENRAN KAGURA Burst Re:Newal bg00.cat.
READ ONLY: the source CAT is never modified.
Exports each selected block with two alternative UV interpretations:
  *_uv1.obj       UV pair at vertex +0x18, interpreted as unsigned 10-bit / 1023
  *_uv0_signed.obj UV pair at vertex +0x14, interpreted as signed int16 / 1024
Both variants include XYZ and normalized signed-byte normal candidates.
Usage:
  python senran_uv_diagnostic_export.py
  python senran_uv_diagnostic_export.py "/path/to/bg00.cat"
"""
import os
import sys
import struct
import math

BLOCKS = [
    ("block4", 0x24F200, 24336, 28392),
    ("block5", 0x335100, 46032, 33291),
]
STRIDE = 28

def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]

def write_obj(path, name, vertices, normals, uvs, indices):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# SENRAN KAGURA diagnostic export: %s\n" % name)
        f.write("# Vertex attributes are candidates; UV interpretation is stated in filename.\n")
        for x, y, z in vertices:
            f.write("v %.8g %.8g %.8g\n" % (x, y, z))
        for u, v in uvs:
            f.write("vt %.8g %.8g\n" % (u, v))
        for nx, ny, nz in normals:
            f.write("vn %.8g %.8g %.8g\n" % (nx, ny, nz))
        for i in range(0, len(indices), 3):
            a, b, c = (indices[i] + 1, indices[i+1] + 1, indices[i+2] + 1)
            f.write("f %d/%d/%d %d/%d/%d %d/%d/%d\n" %
                    (a, a, a, b, b, b, c, c, c))

def main():
    default_path = (
        "/storage/emulated/0/GAMES/PC/SENRAN KAGURA Burst Re Newal/"
        "GameData/Model/Field/bg00.cat"
    )
    src = sys.argv[1] if len(sys.argv) > 1 else default_path
    if not os.path.isfile(src):
        raise SystemExit("ERROR: CAT file not found: " + src)

    with open(src, "rb") as f:
        data = f.read()

    out_dir = os.path.dirname(os.path.abspath(src))
    report = [
        "SENRAN KAGURA - UV DIAGNOSTIC OBJ EXPORT",
        "READ ONLY: source CAT was not modified.",
        "Source: " + src,
        "File size: %d bytes" % len(data),
        "UV1 candidate: uint16 pair at +0x18 divided by 1023.",
        "UV0 candidate: int16 pair at +0x14 divided by 1024.",
        "Normal candidate: signed int8 XYZ at +0x0C, normalized to unit length.",
        "These are test interpretations, not confirmed format documentation.",
        ""
    ]

    total_files = 0
    for name, base, expected_triangles, expected_vertices in BLOCKS:
        if base + 0xDC + 4 > len(data):
            raise SystemExit("ERROR: header outside file for " + name)

        index_start = base + u32(data, base + 0x70)
        index_end = base + u32(data, base + 0x78)
        vertex_start = base + u32(data, base + 0x90)
        vertex_count = u32(data, base + 0xDC)

        if vertex_count != expected_vertices:
            raise SystemExit("%s vertex count mismatch: header=%d expected=%d" %
                             (name, vertex_count, expected_vertices))
        if index_start < base or index_end < index_start or index_end > len(data):
            raise SystemExit("%s invalid index span: 0x%X..0x%X" %
                             (name, index_start, index_end))
        if vertex_start < base or vertex_start + vertex_count * STRIDE > len(data):
            raise SystemExit("%s invalid vertex span" % name)

        index_bytes = index_end - index_start
        if index_bytes % 2:
            raise SystemExit(name + ": odd index byte count")
        indices = list(struct.unpack_from("<%dH" % (index_bytes // 2), data, index_start))
        if len(indices) != expected_triangles * 3:
            raise SystemExit("%s index count mismatch: %d" % (name, len(indices)))
        if indices and max(indices) >= vertex_count:
            raise SystemExit("%s out-of-range index: %d >= %d" %
                             (name, max(indices), vertex_count))

        vertices = []
        normals = []
        uv1 = []
        uv0_signed = []
        for i in range(vertex_count):
            off = vertex_start + i * STRIDE
            x, y, z = struct.unpack_from("<3f", data, off)
            if not all(math.isfinite(v) and abs(v) < 1e20 for v in (x, y, z)):
                raise SystemExit("%s invalid XYZ at vertex %d" % (name, i))
            vertices.append((x, y, z))

            nx, ny, nz = struct.unpack_from("<3b", data, off + 12)
            nx, ny, nz = nx / 127.0, ny / 127.0, nz / 127.0
            mag = math.sqrt(nx*nx + ny*ny + nz*nz)
            if mag > 1e-12:
                normals.append((nx/mag, ny/mag, nz/mag))
            else:
                normals.append((0.0, 0.0, 1.0))

            u1, v1 = struct.unpack_from("<2H", data, off + 24)
            uv1.append((u1 / 1023.0, v1 / 1023.0))

            u0, v0 = struct.unpack_from("<2h", data, off + 20)
            uv0_signed.append((u0 / 1024.0, v0 / 1024.0))

        p1 = os.path.join(out_dir, name + "_uv1.obj")
        p0 = os.path.join(out_dir, name + "_uv0_signed.obj")
        write_obj(p1, name + " UV1 uint16/1023", vertices, normals, uv1, indices)
        write_obj(p0, name + " UV0 int16/1024", vertices, normals, uv0_signed, indices)
        total_files += 2

        report += [
            "%s" % name,
            "  triangles=%d vertices=%d indices=%d" %
            (expected_triangles, vertex_count, len(indices)),
            "  index span=0x%X..0x%X (%d bytes)" %
            (index_start, index_end, index_bytes),
            "  vertex start=0x%X stride=%d" % (vertex_start, STRIDE),
            "  max index=%d; out-of-range=0" % max(indices),
            "  UV1 OBJ: %s" % os.path.basename(p1),
            "  UV0 signed OBJ: %s" % os.path.basename(p0),
            ""
        ]

    report_path = os.path.join(out_dir, "senran_uv_diagnostic_export_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print("\n".join(report))
    print("Created %d OBJ files." % total_files)
    print("Report: " + report_path)
    print("All outputs are separate from and do not modify the source CAT.")

if __name__ == "__main__":
    main()
