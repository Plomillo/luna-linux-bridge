#!/usr/bin/env python3
"""Publish CUSTOSZ runtime research evidence to the staging branch via GitHub API."""
import base64, json, os, urllib.request
from pathlib import Path

REPO="Plomillo/luna-linux-bridge"
BRANCH="staging/custosz-v7-metaos-20260927"
ROOT="docs/missions/LUNA_R4_CUSTOSZ_V7"

def request(method,url,headers,payload=None):
    data=None if payload is None else json.dumps(payload).encode("utf-8")
    req=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=40) as r:
        return json.load(r)

def main():
    token=os.environ["GH_TOKEN"]
    result_path=Path(os.environ["RESULT_FILE"])
    run_id=os.environ["GITHUB_RUN_ID"]
    if result_path.is_file():
        result=json.loads(result_path.read_text(encoding="utf-8"))
    else:
        result={"status":"RUNTIME_DISPATCH_NO_RESULT","run_id":run_id}
    headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "Content-Type":"application/json",
        "User-Agent":"CUSTOSZ-R4-runtime-publisher"
    }
    def get(path):
        return request("GET",f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}",headers)
    def put(path,text,message):
        url=f"https://api.github.com/repos/{REPO}/contents/{path}"
        try:
            old=get(path)
            sha=old["sha"]
        except Exception:
            sha=None
        payload={
            "message":message,
            "branch":BRANCH,
            "content":base64.b64encode(text.encode("utf-8")).decode("ascii")
        }
        if sha:
            payload["sha"]=sha
        return request("PUT",url,headers,payload)

    result_text=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    put(
        ROOT+"/CUSTOSZ_RUNTIME_R4_RESULT.json",
        result_text,
        "docs(custosz): publicar resultado material runtime R4"
    )

    readme_path=ROOT+"/README_CONCLUSIONES_CUSTOSZ_V7.md"
    old=get(readme_path)
    text=base64.b64decode(old["content"]).decode("utf-8")
    title="## Despacho material CUSTOSZ + Runtime run "+run_id
    if title not in text:
        summary={
            "status":result.get("status"),
            "mission_id":result.get("mission_id"),
            "started_utc":result.get("started_utc"),
            "ended_utc":result.get("ended_utc"),
            "runtime_dispatch":result.get("runtime_dispatch"),
            "user_host_ram_heavy_research":result.get("user_host_ram_heavy_research"),
            "host_installation":result.get("host_installation"),
            "host_disk_mutation":result.get("host_disk_mutation"),
            "g23":result.get("g23"),
            "g24":result.get("g24"),
            "research_result":result.get("research_result")
        }
        section=(
            "\n\n"+title+"\n\n"
            "Evidencia de ejecución: https://github.com/"+REPO+"/actions/runs/"+run_id+"\n\n"
            "El trabajo pesado de esta etapa se ejecutó en GitHub-hosted; no constituye activación de producción en LOUKSNA ni autorización F3-DISK.\n\n"
            "~~~json\n"+json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+"\n~~~\n"
        )
        put(readme_path,text+section,"docs(custosz): registrar resultado material runtime R4 "+run_id)
    print(json.dumps({"published":True,"status":result.get("status"),"run_id":run_id},sort_keys=True))

if __name__=="__main__":
    main()
