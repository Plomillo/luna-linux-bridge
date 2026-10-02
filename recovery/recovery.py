#!/usr/bin/env python3
import argparse,hashlib,json,pathlib,tempfile
def digest(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def checkpoint(root):
    root=pathlib.Path(root); root.mkdir(parents=True,exist_ok=True)
    state={"schema":"LOUKSNA_RECOVERY_CHECKPOINT/1.0","state":"CHECKPOINT","files":{}}
    for name in ("RECOVERY_CONTRACT.json","STATE_MACHINE.json","PROVIDERS.json","MANIFEST.json"):
        p=pathlib.Path(__file__).parent/name
        state["files"][name]=digest(p)
    out=root/"checkpoint.json"; out.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
    return out
def hold(reason):
    return {"state":"HOLD","blocker":reason,"next_authorized_action":"ACQUIRE_NEW_CAUSAL_EVIDENCE","resume_from":"LAST_VALID_CHECKPOINT"}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("command",choices=["selftest","checkpoint","hold"]); ap.add_argument("--root"); ap.add_argument("--reason",default="UNSPECIFIED")
    a=ap.parse_args()
    if a.command=="checkpoint":
        if not a.root: raise SystemExit("--root required")
        print(checkpoint(a.root)); return
    if a.command=="hold":
        print(json.dumps(hold(a.reason),sort_keys=True)); return
    for n in ("RECOVERY_CONTRACT.json","STATE_MACHINE.json","PROVIDERS.json","MANIFEST.json"):
        json.load(open(pathlib.Path(__file__).parent/n,encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        p=checkpoint(td); assert p.is_file()
    h=hold("TEST"); assert h["state"]=="HOLD" and h["resume_from"]=="LAST_VALID_CHECKPOINT"
    print("RECOVERY_SELFTEST=PASS")
if __name__=="__main__": main()
