#!/usr/bin/env python3
"""Read-only inventory of SENRAN KAGURA GameData assets; does not extract or modify files."""
import os, sys, hashlib
ROOT_DEFAULT="/storage/emulated/0/GAMES/PC/SENRAN KAGURA Burst Re Newal/GameData"
INTEREST={".cat",".gxt",".tmd",".dds",".png",".tga",".bmp",".jpg",".jpeg",".tex",".bin",".dat",".pak"}
MAGIC={
 b"DDS ": "DDS texture",
 b"\x89PNG\r\n\x1a\n": "PNG image",
 b"\xff\xd8\xff": "JPEG image",
 b"BM": "BMP image",
 b"DDS ": "DDS texture",
}
def main():
 root=sys.argv[1] if len(sys.argv)>1 else ROOT_DEFAULT
 if not os.path.isdir(root): raise SystemExit("ERROR: GameData folder not found: "+root)
 rows=[]; counts={}; ext_sizes={}
 for base,dirs,files in os.walk(root):
  dirs.sort(); files.sort()
  for name in files:
   path=os.path.join(base,name); ext=os.path.splitext(name)[1].lower()
   try:
    size=os.path.getsize(path)
    with open(path,"rb") as f: head=f.read(32)
   except OSError as e:
    rows.append((path,ext,-1,"READ_ERROR:"+str(e))); continue
   counts[ext]=counts.get(ext,0)+1
   ext_sizes[ext]=ext_sizes.get(ext,0)+size
   if ext in INTEREST:
    kind="unknown"
    for sig,label in MAGIC.items():
     if head.startswith(sig): kind=label; break
    if ext==".cat": kind="CAT container candidate"
    elif ext==".gxt": kind="GXT texture candidate"
    elif ext==".tmd": kind="TMD model candidate"
    rows.append((path,ext,size,kind+" | "+head.hex(" ")))
 out=["SENRAN KAGURA - GAMEDATA ASSET INVENTORY","READ ONLY: files are only listed and first 32 bytes sampled.","Root: "+root,"","EXTENSION SUMMARY (count | total MiB)"]
 for ext,n in sorted(counts.items()):
  out.append("%s | %d | %.3f MiB"%(ext or "[no extension]",n,ext_sizes[ext]/1048576))
 out += ["","CANDIDATE ASSETS"]
 for path,ext,size,desc in rows:
  out.append("%s | %s | %d bytes | %s"%(ext,path,size,desc))
 out += ["","No files were extracted, renamed, or modified."]
 dest=os.path.join(os.path.dirname(os.path.abspath(root)),"senran_gamedata_asset_inventory.txt")
 with open(dest,"w",encoding="utf-8") as f:f.write("\n".join(out)+"\n")
 print("\n".join(out)); print("\nReport: "+dest)
if __name__=="__main__": main()
