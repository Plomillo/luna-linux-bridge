#!/usr/bin/env python3
"""PART4-R2 strict tree verifier with an explicit ext4 root lost+found exception.

The exception is intentionally narrow: only a real, non-symlink directory named
"lost+found" directly under the verified root, on the same st_dev, while the
verified root is proven ext4. It is excluded from dataset counts. Any other
extra remains a mismatch.
"""
import argparse
import gzip
import hashlib
import json
import os
import pathlib
import stat
import subprocess
import time

EXPECTED_MANIFEST_SHA256="99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e"
EXPECTED_COUNTS={"file":436072,"dir":62016,"symlink":4,"other":0}
EXPECTED_BYTES=200490852057
EXPECTED_RECORDS=498092

def sha256_file(path,chunk=8*1024*1024):
    h=hashlib.sha256()
    with open(path,"rb",buffering=0) as f:
        for b in iter(lambda:f.read(chunk),b""):
            h.update(b)
    return h.hexdigest()

def detected_fstype(root):
    p=subprocess.run(
        ["findmnt","-n","-o","FSTYPE","-T",str(root)],
        text=True,capture_output=True,check=False
    )
    return p.stdout.strip() if p.returncode==0 else ""

def allowed_ext4_admin_entry(root, entry, fstype):
    if fstype != "ext4":
        return False
    if entry.name != "lost+found":
        return False
    try:
        est=entry.stat(follow_symlinks=False)
        rst=os.stat(root,follow_symlinks=False)
    except OSError:
        return False
    if stat.S_ISLNK(est.st_mode) or not stat.S_ISDIR(est.st_mode):
        return False
    if est.st_dev != rst.st_dev:
        return False
    try:
        rel=pathlib.Path(entry.path).relative_to(root).as_posix()
    except Exception:
        return False
    return rel == "lost+found"

def selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        lf=root/"lost+found"; lf.mkdir()
        class E:
            def __init__(self,path): self.path=str(path); self.name=path.name
            def stat(self,follow_symlinks=False): return os.stat(self.path,follow_symlinks=follow_symlinks)
        assert allowed_ext4_admin_entry(root,E(lf),"ext4")
        assert not allowed_ext4_admin_entry(root,E(lf),"xfs")
        other=root/"other"; other.mkdir()
        assert not allowed_ext4_admin_entry(root,E(other),"ext4")
        nested=root/"x"; nested.mkdir(); nlf=nested/"lost+found"; nlf.mkdir()
        assert not allowed_ext4_admin_entry(root,E(nlf),"ext4")
        lf.rmdir()
        target=root/"target"; target.mkdir()
        os.symlink(target,lf)
        assert not allowed_ext4_admin_entry(root,E(lf),"ext4")
    print("PART4_R2_VERIFY_TREE_V2_SELFTEST=PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--manifest")
    ap.add_argument("--out")
    ap.add_argument("--allow-ext4-root-lost-found",action="store_true")
    ap.add_argument("--selftest",action="store_true")
    a=ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    if not (a.root and a.manifest and a.out):
        ap.error("--root --manifest --out required unless --selftest")
    root=pathlib.Path(a.root).resolve()
    man=pathlib.Path(a.manifest).resolve()
    out=pathlib.Path(a.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    fstype=detected_fstype(root)
    result={
        "schema":"LOUKSNA_R4_PART4_R2_TREE_VERIFY/2.0",
        "root":str(root),
        "root_fstype":fstype,
        "manifest":str(man),
        "manifest_sha256":sha256_file(man),
        "status":"HOLD",
        "mismatches":[],
        "ignored_filesystem_admin_entries":[],
        "counts":{"file":0,"dir":0,"symlink":0,"other":0},
        "regular_file_bytes":0,
        "seen_records":0,
        "started_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    }
    if result["manifest_sha256"]!=EXPECTED_MANIFEST_SHA256:
        result["mismatches"].append({"reason":"MANIFEST_DIGEST_MISMATCH"})
    expected={}
    with gzip.open(man,"rt",encoding="utf-8") as f:
        for line in f:
            rec=json.loads(line)
            expected[rec["path"]]=rec
    seen=set()
    stack=[root]
    while stack:
        d=stack.pop()
        for e in os.scandir(d):
            p=pathlib.Path(e.path)
            rel=p.relative_to(root).as_posix()
            exp=expected.get(rel)
            if exp is None:
                if (
                    a.allow_ext4_root_lost_found
                    and d==root
                    and allowed_ext4_admin_entry(root,e,fstype)
                ):
                    result["ignored_filesystem_admin_entries"].append({
                        "path":"lost+found",
                        "reason":"EXT4_ROOT_ADMIN_DIRECTORY",
                        "same_device":True,
                        "symlink":False
                    })
                    continue
                result["mismatches"].append({"path":rel,"reason":"EXTRA"})
                continue
            seen.add(rel)
            st=e.stat(follow_symlinks=False)
            typ=(
                "file" if stat.S_ISREG(st.st_mode)
                else "dir" if stat.S_ISDIR(st.st_mode)
                else "symlink" if stat.S_ISLNK(st.st_mode)
                else "other"
            )
            result["counts"][typ]+=1
            if typ!=exp.get("type"):
                result["mismatches"].append({
                    "path":rel,"reason":"TYPE",
                    "expected":exp.get("type"),"actual":typ
                })
                continue
            if typ=="file":
                result["regular_file_bytes"]+=st.st_size
                if st.st_size!=exp.get("size"):
                    result["mismatches"].append({
                        "path":rel,"reason":"SIZE",
                        "expected":exp.get("size"),"actual":st.st_size
                    })
                    continue
                h=sha256_file(p)
                if h!=exp.get("sha256"):
                    result["mismatches"].append({
                        "path":rel,"reason":"SHA256",
                        "expected":exp.get("sha256"),"actual":h
                    })
            elif typ=="dir":
                stack.append(p)
            elif typ=="symlink":
                try:
                    target=os.readlink(p)
                except Exception as ex:
                    result["mismatches"].append({
                        "path":rel,"reason":"READLINK","error":repr(ex)
                    })
                    continue
                if target!=exp.get("target"):
                    result["mismatches"].append({
                        "path":rel,"reason":"SYMLINK_TARGET",
                        "expected":exp.get("target"),"actual":target
                    })
            if len(result["mismatches"])>1000:
                break
        if len(result["mismatches"])>1000:
            break
    missing=sorted(set(expected)-seen)
    if missing:
        result["mismatches"].extend(
            {"path":p,"reason":"MISSING"} for p in missing[:1000]
        )
    result["seen_records"]=len(seen)
    checks={
        "manifest_digest":result["manifest_sha256"]==EXPECTED_MANIFEST_SHA256,
        "root_fstype_ext4":fstype=="ext4",
        "mismatch_count_zero":len(result["mismatches"])==0,
        "record_count":len(seen)==EXPECTED_RECORDS,
        "counts":result["counts"]==EXPECTED_COUNTS,
        "regular_file_bytes":result["regular_file_bytes"]==EXPECTED_BYTES,
        "admin_exception_cardinality":(
            len(result["ignored_filesystem_admin_entries"]) in (0,1)
        )
    }
    result["checks"]=checks
    result["status"]="PASS" if all(checks.values()) else "HOLD"
    result["mismatch_count"]=len(result["mismatches"])
    result["mismatches"]=result["mismatches"][:100]
    result["finished_at_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    raw=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    out.write_text(raw,encoding="utf-8")
    print(raw)
    return 0 if result["status"]=="PASS" else 3

if __name__=="__main__":
    raise SystemExit(main())
