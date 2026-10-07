#!/usr/bin/env python3
"""Governed content-addressed, resumable downloader for remaining Luna/Linux artifacts."""
import argparse,hashlib,json,os,pathlib,shutil,urllib.request
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def atomic_copy(src,dst):
 dst=pathlib.Path(dst);dst.parent.mkdir(parents=True,exist_ok=True);tmp=dst.with_suffix(dst.suffix+".tmp");shutil.copy2(src,tmp);os.replace(tmp,dst)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--manifest",required=True);ap.add_argument("--cas",required=True);ap.add_argument("--apply",action="store_true");ap.add_argument("--report",required=True);q=ap.parse_args()
 m=json.load(open(q.manifest,encoding="utf-8"));cas=pathlib.Path(q.cas);cas.mkdir(parents=True,exist_ok=True);rows=[];seen={}
 for it in m.get("items",[]):
  eid=it["id"];exp=it["sha256"].lower();target=pathlib.Path(it["target"]).expanduser();url=it["url"];size=it.get("size")
  if len(exp)!=64:raise SystemExit("INVALID_SHA256:"+eid)
  obj=cas/exp[:2]/exp;obj.parent.mkdir(parents=True,exist_ok=True)
  if target.is_file():
   got=sha(target)
   if got==exp:rows.append({"id":eid,"status":"SKIP_EXACT_TARGET","sha256":exp});seen[exp]=str(target);continue
   raise SystemExit("TARGET_HASH_CONFLICT:"+eid)
  if exp in seen or (obj.is_file() and sha(obj)==exp):
   src=pathlib.Path(seen.get(exp,str(obj)))
   if q.apply:
    target.parent.mkdir(parents=True,exist_ok=True)
    try:os.link(src,target)
    except OSError:atomic_copy(src,target)
   rows.append({"id":eid,"status":"DEDUP_REUSE","sha256":exp});seen[exp]=str(src);continue
  if not q.apply:
   rows.append({"id":eid,"status":"PENDING","sha256":exp,"url":url});continue
  part=obj.with_suffix(".part");start=part.stat().st_size if part.exists() else 0
  req=urllib.request.Request(url,headers={"Range":f"bytes={start}-"} if start else {})
  r=None
  try:
   r=urllib.request.urlopen(req,timeout=60);code=getattr(r,"status",200)
   if start and code!=206:
    r.close();part.unlink(missing_ok=True);start=0;r=urllib.request.urlopen(urllib.request.Request(url),timeout=60)
   with open(part,"ab" if start else "wb") as f:shutil.copyfileobj(r,f,1024*1024)
  finally:
   if r is not None:r.close()
  if size is not None and part.stat().st_size!=int(size):raise SystemExit("SIZE_MISMATCH:"+eid)
  if sha(part)!=exp:raise SystemExit("HASH_MISMATCH:"+eid)
  os.replace(part,obj);target.parent.mkdir(parents=True,exist_ok=True)
  try:os.link(obj,target)
  except OSError:atomic_copy(obj,target)
  rows.append({"id":eid,"status":"DOWNLOADED_VERIFIED","sha256":exp});seen[exp]=str(obj)
 report={"schema":"LOUKSNA_LINUX_REMAINDER_FETCH/1.0","apply":q.apply,"count":len(rows),"rows":rows,"duplicate_content_objects":0}
 pathlib.Path(q.report).parent.mkdir(parents=True,exist_ok=True);pathlib.Path(q.report).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
 print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
