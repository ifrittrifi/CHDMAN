#!/usr/bin/env python3
"""Read-only topology and cross-block proximity diagnostic for SENRAN bg00.cat."""
import os, sys, math, struct
from collections import Counter, defaultdict

BLOCKS = [("block4", 0x24F200, 24336, 28392), ("block5", 0x335100, 46032, 33291)]
STRIDE = 28
CELL = 0.1
TOLS = (0.001, 0.01, 0.05)

def u32(d, o): return struct.unpack_from("<I", d, o)[0]

def load(d, spec):
    name, base, nt, nv = spec
    is0, is1, vs = base+u32(d,base+0x70), base+u32(d,base+0x78), base+u32(d,base+0x90)
    if u32(d,base+0xDC) != nv: raise ValueError(name+" vertex count mismatch")
    raw = d[is0:is1]
    if len(raw) != nt*6: raise ValueError(name+" index byte count mismatch")
    ix = struct.unpack("<%dH" % (len(raw)//2), raw)
    if max(ix) >= nv: raise ValueError(name+" index out of range")
    pts = [struct.unpack_from("<3f",d,vs+i*STRIDE) for i in range(nv)]
    if any(not all(math.isfinite(x) for x in p) for p in pts): raise ValueError(name+" non-finite XYZ")
    edge = Counter(); used = Counter(); adj = [set() for _ in range(nv)]
    for k in range(0,len(ix),3):
        a,b,c = ix[k:k+3]
        used.update((a,b,c))
        for x,y in ((a,b),(b,c),(c,a)):
            e=(x,y) if x<y else (y,x)
            edge[e]+=1
            adj[x].add(y); adj[y].add(x)
    hist=Counter(edge.values())
    boundary=sorted({v for e,n in edge.items() if n==1 for v in e})
    # Connected components among referenced vertices.
    seen=set(); comps=[]
    for start in used:
        if start in seen: continue
        stack=[start]; seen.add(start); count=0
        while stack:
            v=stack.pop(); count+=1
            for w in adj[v]:
                if w not in seen: seen.add(w); stack.append(w)
        comps.append(count)
    return dict(name=name,pts=pts,ix=ix,edge_hist=hist,boundary=boundary,
                used=used,components=sorted(comps,reverse=True),triangles=nt,vertices=nv)

def key(p): return tuple(math.floor(v/CELL) for v in p)
def grid(points):
    g=defaultdict(list)
    for i,p in enumerate(points): g[key(p)].append(p)
    return g
def nearest(query, target):
    g=grid(target); out=[]
    for p in query:
        c=key(p); best=None
        for x in (-1,0,1):
          for y in (-1,0,1):
           for z in (-1,0,1):
            for q in g.get((c[0]+x,c[1]+y,c[2]+z),()):
             d2=sum((p[j]-q[j])**2 for j in range(3))
             if best is None or d2<best: best=d2
        out.append(math.sqrt(best) if best is not None else None)
    return out

def report_block(out,b):
    h=b["edge_hist"]; out += [b["name"],"  triangles=%d vertices=%d referenced=%d unreferenced=%d"%(b["triangles"],b["vertices"],len(b["used"]),b["vertices"]-len(b["used"])),"  unique undirected edges=%d"%sum(h.values()),"  edge-use histogram: "+", ".join("%d edge(s) used %d time(s)"%(n,c) for n,c in sorted(h.items())),"  boundary edges(use=1)=%d"%h.get(1,0),"  nonmanifold edges(use>2)=%d"%sum(c for n,c in h.items() if n>2),"  boundary vertices=%d"%len(b["boundary"]),"  connected components=%d; largest component sizes=%s"%(len(b["components"]),b["components"][:10]),""]

def cross(out,a,b):
    q=[a["pts"][i] for i in a["boundary"]]
    ds=nearest(q,b["pts"])
    valid=[x for x in ds if x is not None]
    out += [a["name"]+" boundary vertices -> ALL "+b["name"]+" vertices","  boundary vertices=%d; with nearby grid candidates=%d"%(len(q),len(valid))]
    if valid: out.append("  nearest min/median/max=%.8g / %.8g / %.8g"%(min(valid),sorted(valid)[len(valid)//2],max(valid)))
    for t in TOLS:
        n=sum(x is not None and x<=t for x in ds)
        out.append("  <= %.3g units: %d (%.2f%%)"%(t,n,100*n/len(ds) if ds else 0))
    out.append("")

def main():
    default="/storage/emulated/0/GAMES/PC/SENRAN KAGURA Burst Re Newal/GameData/Model/Field/bg00.cat"
    src=sys.argv[1] if len(sys.argv)>1 else default
    if not os.path.isfile(src): raise SystemExit("ERROR: CAT not found: "+src)
    with open(src,"rb") as f: data=f.read()
    bs=[load(data,s) for s in BLOCKS]
    out=["SENRAN KAGURA - BLOCK4/BLOCK5 TOPOLOGY DIAGNOSTIC v2","READ ONLY: source CAT is never modified.","Source: "+src,"Boundary-to-other-block comparison uses ALL target vertices, not only target boundary vertices.","Original XYZ retained; terrain is not flattened.",""]
    for b in bs: report_block(out,b)
    out += ["CROSS-BLOCK PROXIMITY"]
    cross(out,bs[0],bs[1]); cross(out,bs[1],bs[0])
    out += ["INTERPRETATION","- A high edge-use=1 count can indicate open surfaces, disconnected triangle topology, or an index interpretation issue; inspect the histogram and components together.","- Boundary-to-all-vertices proximity can detect a boundary near the interior of the other block, but proximity alone does not prove a welded seam.","- No CAT bytes, coordinates, or indices are changed."]
    dest=os.path.join(os.path.dirname(os.path.abspath(src)),"senran_block4_5_topology_v2_report.txt")
    with open(dest,"w",encoding="utf-8") as f: f.write("\n".join(out)+"\n")
    print("\n".join(out)); print("\nReport: "+dest)
if __name__=="__main__": main()
