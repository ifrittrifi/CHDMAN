#!/usr/bin/env python3
"""Read-only component/geometry audit for Block4 and Block5 in SENRAN bg00.cat."""
import os, sys, math, struct
from collections import Counter, defaultdict

BLOCKS = [("block4", 0x24F200, 24336, 28392), ("block5", 0x335100, 46032, 33291)]
STRIDE = 28

def u32(d,o): return struct.unpack_from("<I",d,o)[0]

def load(d,spec):
    name,base,nt,nv=spec
    i0=base+u32(d,base+0x70); i1=base+u32(d,base+0x78); v0=base+u32(d,base+0x90)
    if u32(d,base+0xDC)!=nv: raise ValueError(name+" vertex count mismatch")
    if i1-i0 != nt*6: raise ValueError(name+" index span mismatch")
    ix=struct.unpack_from("<%dH"%(nt*3),d,i0)
    if max(ix)>=nv: raise ValueError(name+" index out of range")
    pts=[struct.unpack_from("<3f",d,v0+i*STRIDE) for i in range(nv)]
    if any(not all(math.isfinite(x) for x in p) for p in pts): raise ValueError(name+" invalid XYZ")
    parent=list(range(nv)); rank=[0]*nv
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(a,b):
        a=find(a); b=find(b)
        if a==b:return
        if rank[a]<rank[b]:a,b=b,a
        parent[b]=a
        if rank[a]==rank[b]:rank[a]+=1
    edge=Counter(); used=set(); tri_areas=[]; repeated=0
    for k in range(0,len(ix),3):
        a,b,c=ix[k:k+3]; used.update((a,b,c))
        if len({a,b,c})<3: repeated+=1
        union(a,b); union(b,c)
        for x,y in ((a,b),(b,c),(c,a)):
            edge[(x,y) if x<y else (y,x)]+=1
        p,q,r=pts[a],pts[b],pts[c]
        ux,uy,uz=(q[j]-p[j] for j in range(3))
        vx,vy,vz=(r[j]-p[j] for j in range(3))
        cx=uy*vz-uz*vy; cy=uz*vx-ux*vz; cz=ux*vy-uy*vx
        tri_areas.append(0.5*math.sqrt(cx*cx+cy*cy+cz*cz))
    groups=defaultdict(list)
    for v in used: groups[find(v)].append(v)
    comps=sorted(groups.values(),key=len,reverse=True)
    return dict(name=name,pts=pts,ix=ix,used=used,edge=edge,comps=comps,
                areas=tri_areas,repeated=repeated,triangles=nt,vertices=nv)

def quantiles(vals):
    a=sorted(vals)
    if not a:return "n/a"
    def q(p): return a[min(len(a)-1,int((len(a)-1)*p))]
    return "min/median/p90/max = %.9g / %.9g / %.9g / %.9g"%(a[0],q(.5),q(.9),a[-1])

def main():
    default="/storage/emulated/0/GAMES/PC/SENRAN KAGURA Burst Re Newal/GameData/Model/Field/bg00.cat"
    src=sys.argv[1] if len(sys.argv)>1 else default
    if not os.path.isfile(src): raise SystemExit("ERROR: CAT not found: "+src)
    with open(src,"rb") as f:d=f.read()
    blocks=[load(d,s) for s in BLOCKS]
    out=["SENRAN KAGURA - COMPONENT STRUCTURE AUDIT","READ ONLY: original CAT is not modified.","Source: "+src,"Component connectivity is derived from triangle index sharing.","Triangle area is calculated from original XYZ coordinates.",""]
    for b in blocks:
        sizes=[len(c) for c in b["comps"]]
        size_hist=Counter(sizes)
        edge_hist=Counter(b["edge"].values())
        zero=sum(x<=1e-12 for x in b["areas"])
        tiny=sum(x<=1e-8 for x in b["areas"])
        out += [b["name"],"  triangles=%d vertices=%d referenced=%d unreferenced=%d"%(b["triangles"],b["vertices"],len(b["used"]),b["vertices"]-len(b["used"])),"  connected components=%d"%len(sizes),"  component vertex-size "+quantiles(sizes),"  component size histogram (vertices: number of components):"]
        for n,c in sorted(size_hist.items()): out.append("    %d: %d"%(n,c))
        out += ["  largest component sizes: "+", ".join(map(str,sizes[:20])),"  unique edges=%d"%len(b["edge"]),"  edge-use histogram (uses: edges): "+", ".join("%d: %d"%(n,c) for n,c in sorted(edge_hist.items())),"  repeated-index triangles=%d"%b["repeated"],"  triangle area "+quantiles(b["areas"]),"  zero/nearly-zero area triangles (<=1e-12)=%d"%zero,"  very small area triangles (<=1e-8)=%d"%tiny,""]
    out += ["NOTES","- Many small components can be intentional disconnected patches; component counts alone do not prove corruption.","- Triangle area thresholds are diagnostic and depend on the asset's coordinate scale.","- Edge-use=1 indicates an open topological edge; edge-use>2 indicates non-manifold sharing.","- This audit does not infer material, texture, or intended terrain continuity.","- No coordinates, indices, or source bytes were changed."]
    dest=os.path.join(os.path.dirname(os.path.abspath(src)),"senran_component_structure_audit.txt")
    with open(dest,"w",encoding="utf-8") as f:f.write("\n".join(out)+"\n")
    print("\n".join(out)); print("\nReport: "+dest)
if __name__=="__main__":main()
