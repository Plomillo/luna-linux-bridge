#!/usr/bin/env python3
"""V9 strict exclusion regression suite. Run as root in GitHub-hosted ephemeral fixture only."""
import contextlib,gzip,hashlib,importlib.util,io,json,os,pathlib,sys,tempfile
BASE=pathlib.Path(__file__).resolve().parent
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,BASE/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
v=load("verify_v9","part4_r2_verify_tree_ext4_v9.py")
p=load("posix_v9","part4_r2_posix_fingerprint_v9.py")
assert os.geteuid()==0,"fixture owner root is required"
with tempfile.TemporaryDirectory(prefix="v9_lost_found_test_") as d:
    base=pathlib.Path(d);root=base/"root";root.mkdir()
    lf=root/"lost+found";lf.mkdir(mode=0o700)
    note=root/"note.bin";note.write_bytes(b"VERIFIED")
    man=base/"manifest.jsonl.gz"
    record={"path":"note.bin","type":"file","size":8,"sha256":hashlib.sha256(b"VERIFIED").hexdigest()}
    with gzip.open(man,"wt",encoding="utf-8") as f:f.write(json.dumps(record)+"\n")
    v.EXPECTED_MANIFEST_SHA256=hashlib.sha256(man.read_bytes()).hexdigest()
    v.EXPECTED_COUNTS={"file":1,"dir":0,"symlink":0,"other":0}
    v.EXPECTED_BYTES=8
    v.EXPECTED_RECORDS=1
    orig=os.path.ismount
    os.path.ismount=lambda f: pathlib.Path(f)==root or orig(f)
    def run(module,args,name):
        old=sys.argv
        try:
            sys.argv=[name]+args
            with contextlib.redirect_stdout(io.StringIO()):
                try:return module.main()
                except SystemExit as e:return e.code
        finally:sys.argv=old
    def tree(flag,out):
        a=["--root",str(root),"--manifest",str(man),"--out",str(base/out)]
        if flag:a.append("--allow-root-empty-ext4-lostfound")
        return run(v,a,"tree"),json.loads((base/out).read_text())
    def posix(flag,out,expect=None):
        a=["--root",str(root),"--out",str(base/out)]
        if flag:a.append("--allow-root-empty-ext4-lostfound")
        if expect:a.extend(["--expect",str(base/expect)])
        code=run(p,a,"posix")
        path=base/out
        return code,json.loads(path.read_text()) if path.exists() else None
    a,t=tree(True,"tree_ok.json")
    assert a==0 and t["status"]=="PASS" and t["seen_records"]==1 and t["root_technical_exclusion"]["children"]==[]
    a,t=tree(False,"tree_default.json")
    assert a!=0 and t["mismatch_count"]>0 and any(x["path"]=="lost+found" for x in t["mismatches"])
    a,good=posix(True,"posix_good.json")
    assert a==0 and good["status"]=="PASS" and good["records"]==1
    a,bad=posix(False,"posix_default.json","posix_good.json")
    assert a!=0 and bad["status"]=="HOLD"
    (lf/"unsafe").write_text("nonempty")
    a,t=tree(True,"tree_nonempty.json")
    assert a!=0 and any(x["reason"]=="INVALID_EXT4_ROOT_LOST_FOUND" for x in t["mismatches"])
    code,_=posix(True,"posix_nonempty.json")
    assert code!=0
    (lf/"unsafe").unlink()
    extra=root/"unauthorized.txt";extra.write_text("surprise")
    a,t=tree(True,"tree_extra.json")
    assert a!=0 and any(x["path"]=="unauthorized.txt" for x in t["mismatches"])
    extra.unlink()
    note.write_bytes(b"TAMPERED")
    a,t=tree(True,"tree_modified.json")
    assert a!=0 and any(x["reason"]=="SHA256" for x in t["mismatches"])
    note.write_bytes(b"VERIFIED")
    lf.rmdir()
    external=base/"external_directory";external.mkdir()
    lf.symlink_to(external,target_is_directory=True)
    a,t=tree(True,"tree_symlink_lf.json")
    assert a!=0 and any(x["reason"]=="UNSAFE_ROOT_LOST_FOUND_TYPE_OR_MOUNT" for x in t["mismatches"])
    code,_=posix(True,"posix_symlink_lf.json")
    assert code!=0
    lf.unlink()
    a,t=tree(True,"tree_missing_lf.json")
    assert a!=0 and t["checks"]["technical_exclusion_strict"] is False
print("V9_REGRESSION_TESTS=PASS strict-only-root-empty-lostfound,default-HOLD,POSIX-exclusion,nonempty-HOLD,unexpected-HOLD,hash-HOLD,symlink-HOLD,missing-HOLD")
