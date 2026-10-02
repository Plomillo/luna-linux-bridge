#!/usr/bin/env python3
import argparse, hashlib, json, os, pathlib, sys, tempfile
PIN="dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2"

def emit(out,data):
    p=pathlib.Path(out)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("envelope")
    ap.add_argument("source")
    ap.add_argument("--custosz")
    ap.add_argument("--out",required=True)
    ns=ap.parse_args()
    env=json.loads(pathlib.Path(ns.envelope).read_text(encoding="utf-8"))
    raw=pathlib.Path(ns.source).read_bytes()
    actual=hashlib.sha256(raw).hexdigest()
    base={
      "schema":"LOUKSNA_CONSULTA_RESULT/1.0",
      "consulta_id":env.get("consulta_id"),
      "source_sha256":env.get("source_sha256"),
      "authority":"Louksna.md",
      "execution_authorized":False,
      "mutation_authorized":False,
      "provider":"CUSTOSZ_V7_READ_ONLY"
    }
    if env.get("kind")!="CONSULTA" or env.get("execution_authorized") is not False or env.get("mutation_authorized") is not False:
        emit(ns.out,{**base,"state":"REJECTED","blocker":"INVALID_CONSULTA_ENVELOPE"})
        return
    if actual!=env.get("source_sha256"):
        emit(ns.out,{**base,"state":"REJECTED","blocker":"SOURCE_SHA256_MISMATCH"})
        return
    if not ns.custosz:
        emit(ns.out,{**base,"state":"HOLD","blocker":"CUSTOSZ_PROVIDER_NOT_BOUND","next":"BIND_PINNED_CUSTOSZ_READ_ONLY_PROVIDER"})
        return
    cp=pathlib.Path(ns.custosz)
    if not cp.is_file() or hashlib.sha256(cp.read_bytes()).hexdigest()!=PIN:
        emit(ns.out,{**base,"state":"HOLD","blocker":"CUSTOSZ_PIN_MISMATCH","next":"BIND_EXACT_PINNED_CUSTOSZ_PROVIDER"})
        return
    os.environ["CUSTOSZ_STATE_DIR"]=tempfile.mkdtemp(prefix="louksna-consulta-")
    sys.path.insert(0,str(cp))
    import custosz_v05_legacy as w
    root=pathlib.Path.cwd()
    w.workspace=lambda: root
    w.discover=lambda: {"workspace":str(root),"projects":{"LUNA_PROJECT":{"status":"RESOLVED","path":str(root),"score":999}}}
    prompt=raw.decode("utf-8","replace")
    try:
        architecture=w.architect(prompt,"LUNA_PROJECT")
        policy=w.reasoning_policy(prompt,"LUNA_PROJECT")
        emit(ns.out,{**base,"state":"ANSWERED","architecture":architecture,"reasoning_policy":policy,"certification_propagated":False})
    except Exception as e:
        emit(ns.out,{**base,"state":"HOLD","blocker":type(e).__name__+":"+str(e),"next":"ACQUIRE_MISSING_PROVIDER_OR_EVIDENCE_AND_RETRY_WITH_NEW_CAUSAL_EVIDENCE"})

if __name__=="__main__":
    main()
