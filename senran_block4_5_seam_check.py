#!/usr/bin/env python3
"""Read-only seam diagnostic for Block4/Block5 in SENRAN bg00.cat.

Finds topological boundary vertices (edges used by one triangle), then checks
whether boundary vertices from the other block lie nearby in XYZ space.
It does NOT assume that the hill surface is flat and does NOT modify the CAT.
"""
import os
import sys
import math
import struct
from collections import Counter, defaultdict

BLOCKS = [
    ("block4", 0x24F200, 24336, 28392),
    ("block5", 0x335100, 46032, 33291),
]
STRIDE = 28
CELL = 0.1
TOLERANCES = (0.001, 0.01, 0.05)

def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]

def load_block(data, name, base, expected_triangles, expected_vertices):
    index_start = base + u32(data, base + 0x70)
    index_end = base + u32(data, base + 0x78)
    vertex_start = base + u32(data, base + 0x90)
    vertex_count = u32(data, base + 0xDC)
    if vertex_count != expected_vertices:
        raise ValueError("%s vertex count mismatch: %d != %d" %
                         (name, vertex_count, expected_vertices))
    if index_start < base or index_end < index_start or index_end > len(data):
        raise ValueError("%s invalid index span" % name)
    if vertex_start < base or vertex_start + vertex_count * STRIDE > len(data):
        raise ValueError("%s invalid vertex span" % name)
    nbytes = index_end - index_start
    if nbytes % 2:
        raise ValueError("%s odd index byte count" % name)
    indices = struct.unpack_from("<%dH" % (nbytes // 2), data, index_start)
    if len(indices) != expected_triangles * 3:
        raise ValueError("%s index count mismatch: %d" % (name, len(indices)))
    if indices and max(indices) >= vertex_count:
        raise ValueError("%s index out of range" % name)

    vertices = []
    for i in range(vertex_count):
        p = struct.unpack_from("<3f", data, vertex_start + i * STRIDE)
        if not all(math.isfinite(v) and abs(v) < 1e20 for v in p):
            raise ValueError("%s invalid XYZ at vertex %d" % (name, i))
        vertices.append(p)

    edge_use = Counter()
    for i in range(0, len(indices), 3):
        a, b, c = indices[i], indices[i+1], indices[i+2]
        for x, y in ((a, b), (b, c), (c, a)):
            edge_use[(x, y) if x < y else (y, x)] += 1
    boundary_edges = [e for e, count in edge_use.items() if count == 1]
    boundary_ids = sorted({v for e in boundary_edges for v in e})
    return {
        "name": name, "vertices": vertices, "indices": indices,
        "boundary_edges": boundary_edges, "boundary_ids": boundary_ids,
        "triangle_count": expected_triangles, "vertex_count": vertex_count,
    }

def bounds(points):
    return tuple((min(p[k] for p in points), max(p[k] for p in points))
                 for k in range(3))

def fmt_bounds(b):
    return "X %.6g..%.6g | Y %.6g..%.6g | Z %.6g..%.6g" % (
        b[0][0], b[0][1], b[1][0], b[1][1], b[2][0], b[2][1])

def cell_key(p):
    return tuple(math.floor(v / CELL) for v in p)

def build_grid(points):
    grid = defaultdict(list)
    for idx, p in enumerate(points):
        grid[cell_key(p)].append((idx, p))
    return grid

def nearby_distances(query_points, target_points):
    grid = build_grid(target_points)
    results = []
    for p in query_points:
        cx, cy, cz = cell_key(p)
        best2 = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for _, q in grid.get((cx+dx, cy+dy, cz+dz), ()):
                        d2 = ((p[0]-q[0])**2 + (p[1]-q[1])**2 +
                              (p[2]-q[2])**2)
                        if best2 is None or d2 < best2:
                            best2 = d2
        results.append(math.sqrt(best2) if best2 is not None else None)
    return results

def summarize_direction(report, source, target):
    a = [source["vertices"][i] for i in source["boundary_ids"]]
    b = [target["vertices"][i] for i in target["boundary_ids"]]
    ds = nearby_distances(a, b)
    valid = sorted(d for d in ds if d is not None)
    report.append("%s boundary vertices -> %s boundary vertices" %
                  (source["name"], target["name"]))
    report.append("  source boundary vertices: %d" % len(a))
    report.append("  with target candidates in local 0.1-unit grid: %d" % len(valid))
    if valid:
        report.append("  nearest-distance min/median/max (candidate subset): %.8g / %.8g / %.8g" %
                      (valid[0], valid[len(valid)//2], valid[-1]))
    else:
        report.append("  no target candidates in neighboring 0.1-unit grid cells")
    for tol in TOLERANCES:
        count = sum(1 for d in ds if d is not None and d <= tol)
        report.append("  boundary vertices with counterpart <= %.3g units: %d (%.2f%%)" %
                      (tol, count, 100.0 * count / len(ds) if ds else 0.0))
    report.append("")

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

    blocks = [load_block(data, *spec) for spec in BLOCKS]
    report = [
        "SENRAN KAGURA - BLOCK4/BLOCK5 SEAM DIAGNOSTIC",
        "READ ONLY: source CAT was not modified.",
        "Source: " + src,
        "Method: triangle edges used exactly once are treated as mesh boundaries.",
        "Coordinates are compared in original XYZ; terrain is NOT flattened.",
        "Grid cell: %.3g coordinate units; thresholds: %s" %
        (CELL, ", ".join(str(x) for x in TOLERANCES)),
        "IMPORTANT: proximity is diagnostic, not proof of a visual seam.",
        ""
    ]
    for block in blocks:
        pts = block["vertices"]
        report += [
            block["name"],
            "  triangles=%d vertices=%d" %
            (block["triangle_count"], block["vertex_count"]),
            "  boundary edges=%d boundary vertices=%d" %
            (len(block["boundary_edges"]), len(block["boundary_ids"])),
            "  XYZ bounds: " + fmt_bounds(bounds(pts)),
            ""
        ]

    b4, b5 = blocks
    report.append("BOUNDARY-TO-BOUNDARY PROXIMITY")
    report.append("Distances are Euclidean XYZ units; both directions are tested.")
    report.append("")
    summarize_direction(report, b4, b5)
    summarize_direction(report, b5, b4)

    # Axis-aligned bounding-box overlap is a coarse spatial clue only.
    bb4, bb5 = bounds(b4["vertices"]), bounds(b5["vertices"])
    overlap = []
    for axis in range(3):
        lo = max(bb4[axis][0], bb5[axis][0])
        hi = min(bb4[axis][1], bb5[axis][1])
        overlap.append(max(0.0, hi - lo))
    report += [
        "BBOX OVERLAP (coarse; not a seam verdict)",
        "  overlap extents X/Y/Z: %.8g / %.8g / %.8g" %
        (overlap[0], overlap[1], overlap[2]),
        "",
        "INTERPRETATION",
        "- High counterpart percentages at small tolerances suggest matching boundary positions.",
        "- Low percentages do not automatically mean a gap: blocks may contain separate terrain pieces.",
        "- A visual check is still needed to confirm actual surface continuity.",
        "- No coordinates, indices, or source bytes were changed.",
    ]

    out_dir = os.path.dirname(os.path.abspath(src))
    out_path = os.path.join(out_dir, "senran_block4_5_seam_report.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print("\n".join(report))
    print("\nReport: " + out_path)

if __name__ == "__main__":
    main()
