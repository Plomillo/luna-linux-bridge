#!/usr/bin/env python3
"""Independent V9 assessment of exact postboundary read-only host evidence."""
import argparse,datetime as dt,hashlib,json,pathlib,re
MAN="99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e"
FP="fa50cabb73c9fdb450af4fb3450959672418bd76015239a722d040c1c5603401"
P3="e084ec2a-af39-48b5-bb89-db2dc6a98332"
EXP={1:(2048,532480),2:(534528,32768),3:(567296,853842233),
     4:(998832128,1368064),5:(854411576,144420552)}
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--probe",required=True);a.add_argument("--v8",required=True);a.add_argument("--out",required=True)
    x=a.parse_args();root=pathlib.Path(x.probe);v8=pathlib.Path(x.v8);out=pathlib.Path(x.out);out.parent.mkdir(parents=True,exist_ok=True)
    p=json.loads((root/"PROBE_V9.json").read_text())
    v=json.loads((root/"TREE_V9.json").read_text())
    m=json.loads((root/"POSIX_V9.json").read_text())
    before=(root/"PARTITION_TABLE_BEFORE.sfdisk").read_bytes()
    after=(root/"PARTITION_TABLE_AFTER.sfdisk").read_bytes()
    geom={}
    for line in before.decode(errors="replace").splitlines():
        z=re.match(r"^/dev/nvme0n1p(\d+)\s*:\s*start=\s*(\d+),\s*size=\s*(\d+)",line)
        if z:geom[int(z.group(1))]=(int(z.group(2)),int(z.group(3)))
    lf=v.get("root_technical_exclusion") or {}
    lm=m.get("root_technical_exclusion") or {}
    base=pathlib.Path(__file__).resolve().parent
    vb=json.loads((v8/"VERIFY_P3_PREEXPAND.json").read_text())
    vp=json.loads((v8/"POSIX_P3_PREEXPAND.json").read_text())
    vs=json.loads((v8/"POSIX_SOURCE.json").read_text())
    checks={
        "probe":p.get("status")=="PASS" and p.get("source_run")==36687767779,
        "phase":p.get("boundary")=="P3_ALREADY_EXT4_EXPANDED",
        "root":p.get("root_partition")=="/dev/nvme0n1p5" and p.get("projects_partition")=="/dev/nvme0n1p3" and p.get("projects_uuid")==P3,
        "geometry":geom==EXP and before==after and p.get("partition_sha256")==sha(root/"PARTITION_TABLE_BEFORE.sfdisk"),
        "manifest":p.get("manifest_sha256")==MAN and v.get("manifest_sha256")==MAN,
        "content":v.get("status")=="PASS" and v.get("mismatch_count")==0 and v.get("seen_records")==498092
                  and v.get("regular_file_bytes")==200490852057 and p.get("tree_sha256")==sha(root/"TREE_V9.json"),
        "lostfound":v.get("checks",{}).get("technical_exclusion_strict") is True
                    and lf.get("path")=="lost+found" and lf.get("owner")==0 and lf.get("group")==0
                    and lf.get("mode")=="0o700" and lf.get("children")==[]
                    and lf.get("same_device") is True and lf.get("root_is_mount") is True
                    and lf.get("not_nested_mount") is True and lf.get("not_symlink") is True,
        "posix":m.get("status")=="PASS" and m.get("matches_expected") is True and m.get("records")==498092
                and m.get("fingerprint_sha256")==FP and lm.get("path")=="lost+found" and lm.get("empty") is True
                and p.get("posix_sha256")==sha(root/"POSIX_V9.json"),
        "v9_code":p.get("verifier_sha256")==sha(base/"part4_r2_verify_tree_ext4_v9.py")
                   and p.get("posix_verifier_sha256")==sha(base/"part4_r2_posix_fingerprint_v9.py"),
        "probe_script_bound":p.get("probe_script_sha256")==sha(base/"part4_r2_postboundary_probe_v9.sh"),
        "v8_checkpoint":vb.get("status")=="PASS" and vb.get("mismatch_count")==0
                         and vb.get("seen_records")==498092 and vb.get("regular_file_bytes")==200490852057
                         and vp.get("status")=="PASS" and vp.get("matches_expected") is True
                         and vp.get("fingerprint_sha256")==vs.get("fingerprint_sha256")==FP
                         and p.get("v8_source_posix_sha256")==sha(v8/"POSIX_SOURCE.json")
                         and p.get("v8_p3_preexpand_sha256")==sha(v8/"VERIFY_P3_PREEXPAND.json"),
        "fstab":p.get("fstab_before_sha256")==sha(root/"fstab.before"),
        "no_mutation":p.get("irreversible_mutation_authorized") is False
                      and p.get("p2_p4_retirement_authorized") is False
    }
    valid=all(checks.values())
    result={"schema":"LOUKSNA_R4_PART4_R2_POSTBOUNDARY_V9_G23/1.0",
      "status":"PASS" if valid else "HOLD","scope":"READONLY_POSTBOUNDARY_P3_VALIDATION_ONLY",
      "checks":checks,"probe_sha256":sha(root/"PROBE_V9.json"),
      "tree_sha256":sha(root/"TREE_V9.json"),"posix_sha256":sha(root/"POSIX_V9.json"),
      "probe_script_sha256":sha(base/"part4_r2_postboundary_probe_v9.sh"),
      "v8_checkpoint_sha256":sha(v8/"VERIFY_P3_PREEXPAND.json"),
      "g24_allowed":valid,"fstab_mutation_authorized":False,"retirement_authorized":False,
      "verified_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()}
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if valid else 23
if __name__=="__main__":raise SystemExit(main())
