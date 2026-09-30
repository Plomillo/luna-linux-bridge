#!/usr/bin/env python3
import argparse,collections,json,os,pathlib,time

LX={"$LXUID","$LXGID","$LXMOD","$LXDEV"}
ACL={"system.posix_acl_access","system.posix_acl_default"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    root=pathlib.Path(a.root); out=pathlib.Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    names=collections.Counter(); unexpected=[]; scanned=0; lx_paths=0; acl_paths=0
    stack=[root]
    while stack:
        d=stack.pop()
        for e in os.scandir(d):
            p=pathlib.Path(e.path); rel=p.relative_to(root).as_posix(); scanned+=1
            try: xs=sorted(os.listxattr(p,follow_symlinks=False))
            except OSError as ex:
                unexpected.append({"path":rel,"reason":"LISTXATTR_ERROR","errno":ex.errno,"error":str(ex)})
                xs=[]
            if any(n in LX for n in xs): lx_paths+=1
            if any(n in ACL for n in xs): acl_paths+=1
            for n in xs:
                names[n]+=1
                if n not in LX and n not in ACL and len(unexpected)<200:
                    unexpected.append({"path":rel,"reason":"UNCLASSIFIED_XATTR","name":n})
            if e.is_dir(follow_symlinks=False): stack.append(p)
    ok=not unexpected
    result={"schema":"LOUKSNA_R4_PART4_R2_XATTR_INVENTORY/1.0","root":str(root),"status":"PASS" if ok else "HOLD",
            "policy":{"reserved_wsl_ntfs_xattrs":sorted(LX),"posix_acl_xattrs":sorted(ACL),
                      "transport":"LX_UID_GID_MODE_ARE_MATERIALIZED_BY_NTFS3_AS_POSIX_STAT; ACLS_VIA_RSYNC_A; RAW_XATTRS_DISABLED; UNKNOWN_XATTR_FAIL_CLOSED"},
            "records_scanned":scanned,"paths_with_lx_metadata":lx_paths,"paths_with_posix_acl":acl_paths,
            "xattr_name_counts":dict(sorted(names.items())),"unexpected_count":len(unexpected),"unexpected":unexpected[:200],
            "finished_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if ok else 23
if __name__=="__main__": raise SystemExit(main())
