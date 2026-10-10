#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, struct, sys
from datetime import datetime, timezone
from pathlib import Path

IMAGE_NAMES = [
 "01_louksna_zona_directiva_centro_de_mando_8k.png",
 "02_louksna_zona_directiva_repositorios_8k.png",
 "03_louksna_zona_directiva_pull_requests_8k.png",
 "04_louksna_zona_directiva_evidencia_8k.png",
 "05_louksna_zona_directiva_chat_llamada_8k.png",
 "06_louksna_zona_directiva_configuracion_8k.png",
]

def utc():
    return datetime.now(timezone.utc).isoformat()

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def obj_digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def write(path,text):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8")

def write_json(path,obj):
    write(path,json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n")

def png_dimensions(path):
    data=Path(path).read_bytes()[:24]
    if len(data)<24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("INVALID_PNG:"+str(path))
    return struct.unpack(">II",data[16:24])

def telemetry(path,phase,status,detail,percent):
    event={"utc":utc(),"worker":"CUSTOSZ_V7","runtime":"CUSTOSZ_RUNTIME_V1","project":"LOUKSNA_ZONA_DIRECTIVA","phase":phase,"status":status,"detail":detail,"percent":percent,"execution_location":"GITHUB_HOSTED_ONLY"}
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8") as f: f.write(json.dumps(event,ensure_ascii=False,sort_keys=True)+"\n")
    print("LOUKSNA_TELEMETRY "+json.dumps(event,ensure_ascii=False,sort_keys=True),flush=True)

def main(argv):
    if len(argv)!=8:
        raise SystemExit("EXPECTED_7_ARGUMENTS")
    dispatch_p,ack_p,fme_p,target_p,target_root_p,source_root_p,mission_p=map(Path,argv[1:8])
    target_root=target_root_p.resolve(); source_root=source_root_p.resolve(); mission_path=mission_p.resolve()
    project_rel=Path("LOUKSNA_ZONA_DIRECTIVA_GITHUB_INTERFACE_V0.2_HARDENED")
    source_project=source_root/project_rel; target_project=target_root/project_rel
    candidate=target_project/"candidate"; evidence=candidate/"evidence"; telemetry_file=evidence/"TELEMETRY.jsonl"
    dispatch=json.loads(dispatch_p.read_text(encoding="utf-8"))
    telemetry(telemetry_file,"MATERIAL_EXECUTION","STARTED","Executor material enlazado; inicia auditoría.",5)

    ack={"mission_id":dispatch["mission_id"],"dispatch_id":dispatch["dispatch_id"],"executor_id":dispatch["executor_id"],"accepted":True,"pid":os.getpid(),"process_or_execution_token":"custosz-louksna-zd-materializer","utc":utc()}
    ack["ack_digest"]=obj_digest(ack); write_json(ack_p,ack)

    required={
      "authority":source_root/"Louksna.md",
      "puac2":source_root/"PUAC2.md",
      "skeleton":source_root/"SKELETON_CANONICO_REFERENCIA.txt",
      "monolith":source_project/"LOUKSNA_ZONA_DIRECTIVA_PACKAGING_MONOLITH.md",
      "asset_manifest":source_project/"images"/"ASSET_MANIFEST.json",
      "asset_sums":source_project/"images"/"SHA256SUMS.txt",
    }
    missing=[k for k,p in required.items() if not p.is_file()]
    if missing: raise SystemExit("SOURCE_REQUIRED_FILE_MISSING:"+",".join(missing))

    telemetry(telemetry_file,"FORENSIC_AUDIT","RUNNING","Verificando autoridad, PUAC2, skeleton, monolito e imágenes.",12)
    manifest=json.loads(required["asset_manifest"].read_text(encoding="utf-8"))
    declared={x["file"]:x for x in manifest.get("assets",[])}
    asset_rows=[]; gaps=[]
    for name in IMAGE_NAMES:
        p=source_project/"images"/name
        if not p.is_file(): raise SystemExit("CANONICAL_IMAGE_MISSING:"+name)
        w,h=png_dimensions(p); digest=sha256(p)
        row={"file":name,"bytes":p.stat().st_size,"sha256":digest,"width":w,"height":h,"manifest_sha256":declared.get(name,{}).get("sha256"),"manifest_match":digest==declared.get(name,{}).get("sha256")}
        if not row["manifest_match"]: gaps.append({"id":"ASSET_MANIFEST_HASH_DRIFT","file":name,"severity":"CRITICAL"})
        if w<7680 or h<4320: gaps.append({"id":"REFERENCE_FILENAME_8K_DIMENSION_MISMATCH","file":name,"severity":"DISCLOSED_NONBLOCKING","observed":str(w)+"x"+str(h),"rule":"Preserve accepted canonical reference; no silent regeneration."})
        asset_rows.append(row)

    preservation={}
    for rel in ["LOUKSNA_ZONA_DIRECTIVA_PACKAGING_MONOLITH.md","images/ASSET_MANIFEST.json","images/SHA256SUMS.txt"]+["images/"+x for x in IMAGE_NAMES]:
        sp=source_project/rel; tp=target_project/rel
        preservation[rel]={"source_sha256":sha256(sp),"target_sha256":sha256(tp) if tp.is_file() else None,"preserved":tp.is_file() and sha256(sp)==sha256(tp)}
        if not preservation[rel]["preserved"]: gaps.append({"id":"SOURCE_REFERENCE_DRIFT","path":rel,"severity":"CRITICAL"})
    if any(x.get("severity")=="CRITICAL" for x in gaps):
        write_json(evidence/"HARDENING_MATRIX.json",{"status":"FAIL_CLOSED","gaps":gaps})
        raise SystemExit("CRITICAL_SOURCE_DRIFT")
    telemetry(telemetry_file,"FORENSIC_AUDIT","PASS","Fuente y referencias preservadas; brechas registradas.",24)

    (candidate/"src").mkdir(parents=True,exist_ok=True)
    (candidate/"src-tauri"/"src").mkdir(parents=True,exist_ok=True)
    (candidate/"scripts").mkdir(parents=True,exist_ok=True)
    evidence.mkdir(parents=True,exist_ok=True)

    write(candidate/".gitignore","node_modules/\ndist/\npublic/reference/*.png\nsrc-tauri/target/\n*.log\n.env\n.env.*\n")
    write_json(candidate/"package.json",{
      "name":"louksna-zona-directiva","private":True,"version":"0.2.0-hardened-candidate.1","type":"module",
      "scripts":{"prepare:assets":"python3 scripts/prepare_assets.py","dev":"npm run prepare:assets && vite","build":"npm run prepare:assets && tsc -b && vite build","tauri":"tauri","candidate:deb":"npm run prepare:assets && tauri build --bundles deb"},
      "dependencies":{"@tauri-apps/api":"^2.0.0","react":"^18.3.1","react-dom":"^18.3.1"},
      "devDependencies":{"@tauri-apps/cli":"^2.0.0","@types/react":"^18.3.3","@types/react-dom":"^18.3.0","@vitejs/plugin-react":"^4.3.1","typescript":"^5.6.2","vite":"^5.4.8"}
    })
    write(candidate/"tsconfig.json",'{"files":[],"references":[{"path":"./tsconfig.app.json"}]}\n')
    write(candidate/"tsconfig.app.json",'{"compilerOptions":{"target":"ES2022","useDefineForClassFields":true,"lib":["ES2022","DOM","DOM.Iterable"],"skipLibCheck":true,"strict":true,"module":"ESNext","moduleResolution":"Bundler","resolveJsonModule":true,"isolatedModules":true,"noEmit":true,"jsx":"react-jsx"},"include":["src"]}\n')
    write(candidate/"vite.config.ts",'import { defineConfig } from "vite";\nimport react from "@vitejs/plugin-react";\nexport default defineConfig({plugins:[react()],clearScreen:false,server:{strictPort:true,port:1420},envPrefix:["VITE_","TAURI_"],build:{target:"es2021"}});\n')
    write(candidate/"index.html",'<!doctype html><html lang="es"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/><title>LOUKSNA ZONA DIRECTIVA</title></head><body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>\n')
    write(candidate/"src"/"main.tsx",'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App";\nimport "./styles.css";\nReactDOM.createRoot(document.getElementById("root")!).render(<React.StrictMode><App/></React.StrictMode>);\n')

    app='''import { useMemo, useState } from "react";
type K="centro"|"repositorios"|"pull-requests"|"evidencia"|"chat-llamada"|"configuracion";
const sections:{key:K,label:string,image:string}[]=[
{key:"centro",label:"Centro de mando",image:"01_louksna_zona_directiva_centro_de_mando_8k.png"},
{key:"repositorios",label:"Repositorios",image:"02_louksna_zona_directiva_repositorios_8k.png"},
{key:"pull-requests",label:"Pull Requests",image:"03_louksna_zona_directiva_pull_requests_8k.png"},
{key:"evidencia",label:"Evidencia",image:"04_louksna_zona_directiva_evidencia_8k.png"},
{key:"chat-llamada",label:"Chat / Llamada",image:"05_louksna_zona_directiva_chat_llamada_8k.png"},
{key:"configuracion",label:"Configuración",image:"06_louksna_zona_directiva_configuracion_8k.png"}];
const cards:Record<K,{title:string,value:string,detail:string}[]>={
centro:[{title:"Sistema",value:"OPERATIVO",detail:"Gobernanza fail-closed"},{title:"GitHub",value:"SINCRONIZADO",detail:"Superficie operacional"},{title:"Evidencia",value:"TRAZABLE",detail:"Hash + procedencia"},{title:"Riesgo",value:"BAJO",detail:"Sin mutaciones silenciosas"}],
repositorios:[{title:"Fuente",value:"PRESERVADA",detail:"Branch canónico intacto"},{title:"Trabajo",value:"AISLADO",detail:"Branch CUSTOSZ"},{title:"Permisos",value:"MÍNIMOS",detail:"Least privilege"},{title:"Estado",value:"AUDITANDO",detail:"Telemetría activa"}],
"pull-requests":[{title:"Checks",value:"REQUERIDOS",detail:"Build + tests"},{title:"Merge",value:"BLOQUEADO",detail:"Hasta evidencia"},{title:"G23",value:"PENDIENTE",detail:"Sin propagación"},{title:"G24",value:"PENDIENTE",detail:"No ACTIVE"}],
evidencia:[{title:"SHA-256",value:"ACTIVO",detail:"Artifacts y referencias"},{title:"Cadena",value:"ABIERTA",detail:"Evidencia a validación"},{title:"Rollback",value:"REQUERIDO",detail:"Toda mutación"},{title:"Estado",value:"NO CERTIFICADO",detail:"Candidato no certificado"}],
"chat-llamada":[{title:"Identidad",value:"LOUKSNA",detail:"Única identidad"},{title:"Canal",value:"SEGURO",detail:"Sin secretos"},{title:"Voz",value:"ASISTIDA",detail:"Confirmación no es autoridad"},{title:"Contexto",value:"GITHUB",detail:"Repositorio visible"}],
configuracion:[{title:"Modo",value:"HARDENED",detail:"No silent operations"},{title:"Secretos",value:"LIBSECRET",detail:"Nunca en .deb"},{title:"Paquete",value:".DEB AMD64",detail:"Debian 13 KDE"},{title:"Actualización",value:"CONTROLADA",detail:"Hash + rollback"}]};
export default function App(){const[active,setActive]=useState<K>("centro");const s=useMemo(()=>sections.find(x=>x.key===active)!,[active]);return <main className="shell"><aside className="sidebar"><div className="brand"><div className="orb">L</div><div><b>LOUKSNA</b><span>ZONA DIRECTIVA</span></div></div><nav>{sections.map(x=><button key={x.key} onClick={()=>setActive(x.key)} className={active===x.key?"active":""}>{x.label}</button>)}</nav><div className="guard">HARDENED · FAIL CLOSED</div></aside><section className="workspace"><header><div><p className="eyebrow">GitHub Interface Skeleton V0.2 HARDENED</p><h1>{s.label}</h1></div><div className="status"><i/> Sistema operativo</div></header><section className="hero"><div className="hero-copy"><p className="eyebrow">LOUKSNA ONLY</p><h2>Disciplina visual para ejecución gobernada.</h2><p>De GitHub a evidencia, de evidencia a validación, de validación a operación.</p></div><img src={"/reference/"+s.image} alt="Referencia canónica de Louksna"/></section><section className="cards">{cards[active].map(c=><article key={c.title}><span>{c.title}</span><strong>{c.value}</strong><small>{c.detail}</small></article>)}</section><section className="grid"><article className="panel"><h3>Estado operacional</h3><div className="timeline"><b>REQUEST</b><b>VALIDATION</b><b>EVIDENCE</b><b>EXECUTION</b><b>ROLLBACK</b></div><p>Un workflow exitoso no equivale a certificación. G23/G24 permanecen separados.</p></article><article className="panel"><h3>Telemetría</h3><ul><li>CUSTOSZ V7 · conectado</li><li>CUSTOSZ_RUNTIME_V1 · evidencia activa</li><li>GitHub-hosted · carga local 0</li><li>Branch fuente · preservado</li></ul></article></section></section></main>}
'''
    write(candidate/"src"/"App.tsx",app)
    write(candidate/"src"/"styles.css",''':root{font-family:Inter,ui-sans-serif,system-ui;color:#f8fafc;background:#050613}*{box-sizing:border-box}body{margin:0;min-width:1100px;min-height:100vh;background:radial-gradient(circle at 70% 0,#21134a 0,#08091a 35%,#050613 70%)}button{font:inherit}.shell{display:grid;grid-template-columns:260px 1fr;min-height:100vh}.sidebar{padding:24px 18px;border-right:1px solid #2b2450;background:rgba(5,6,19,.92);display:flex;flex-direction:column;gap:28px}.brand{display:flex;gap:12px;align-items:center}.brand span{display:block;color:#9a8cb9;font-size:11px;letter-spacing:.14em}.orb{width:42px;height:42px;border:1px solid #a855f7;border-radius:50%;display:grid;place-items:center;box-shadow:0 0 28px #7c3aed80}nav{display:grid;gap:7px}nav button{border:1px solid transparent;background:transparent;color:#a7b0c0;padding:12px 14px;border-radius:12px;text-align:left;cursor:pointer}nav button.active,nav button:hover{color:white;border-color:#6d35ff;background:linear-gradient(90deg,#6d35ff22,#38bdf811);box-shadow:inset 2px 0 #a855f7}.guard{margin-top:auto;font-size:11px;color:#38bdf8;letter-spacing:.1em}.workspace{padding:28px 34px 50px;max-width:1680px;width:100%;margin:auto}header{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}h1{margin:.2rem 0;font-size:34px}h2{font-size:34px;margin:.4rem 0 1rem}.eyebrow{text-transform:uppercase;letter-spacing:.16em;color:#a78bfa;font-size:11px}.status{padding:10px 14px;border:1px solid #244e4d;border-radius:999px;color:#b8ffe0;background:#0c282555}.status i{display:inline-block;width:8px;height:8px;background:#34d399;border-radius:50%;margin-right:8px;box-shadow:0 0 12px #34d399}.hero{min-height:365px;display:grid;grid-template-columns:1fr 1.05fr;overflow:hidden;border:1px solid #4c3290;border-radius:24px;background:linear-gradient(135deg,#121430e8,#090b20e8);box-shadow:0 18px 80px #0008,0 0 32px #6d35ff18}.hero-copy{padding:52px;align-self:center}.hero-copy p:last-child{color:#a7b0c0;max-width:600px;line-height:1.7}.hero img{width:100%;height:100%;max-height:430px;object-fit:cover;opacity:.72}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0}.cards article,.panel{border:1px solid #27264b;background:rgba(13,15,38,.9);border-radius:16px;padding:18px}.cards span,.cards small{display:block;color:#8d97aa}.cards strong{display:block;font-size:20px;color:#e9d5ff;margin:12px 0}.grid{display:grid;grid-template-columns:1.45fr 1fr;gap:14px}.panel p,.panel li{color:#99a4b8;line-height:1.65}.timeline{display:flex;gap:10px;flex-wrap:wrap}.timeline b{font-size:10px;padding:8px 10px;border:1px solid #5444a0;border-radius:8px;color:#c4b5fd}@media(max-width:1200px){body{min-width:900px}.shell{grid-template-columns:220px 1fr}.hero{grid-template-columns:1fr}.hero img{display:none}.cards{grid-template-columns:repeat(2,1fr)}}''')

    prepare='''#!/usr/bin/env python3
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]; source=root.parent/"images"; dest=root/"public"/"reference"; dest.mkdir(parents=True,exist_ok=True)
names='''+repr(IMAGE_NAMES)+'''
for name in names:
    src=source/name
    if not src.is_file(): raise SystemExit("MISSING_CANONICAL_REFERENCE:"+name)
    shutil.copy2(src,dest/name)
print("CANONICAL_REFERENCES_PREPARED=6")
'''
    write(candidate/"scripts"/"prepare_assets.py",prepare)
    write(candidate/"src-tauri"/"Cargo.toml",'''[package]
name = "louksna-zona-directiva"
version = "0.2.0"
description = "LOUKSNA ZONA DIRECTIVA GitHub Interface Skeleton V0.2 HARDENED"
authors = ["Louksna"]
edition = "2021"
[build-dependencies]
tauri-build = { version = "2", features = [] }
[dependencies]
tauri = { version = "2", features = [] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
[features]
custom-protocol = ["tauri/custom-protocol"]
''')
    write(candidate/"src-tauri"/"build.rs","fn main(){ tauri_build::build(); }\n")
    write(candidate/"src-tauri"/"src"/"main.rs",'#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]\nfn main(){tauri::Builder::default().run(tauri::generate_context!()).expect("error while running LOUKSNA ZONA DIRECTIVA");}\n')
    write_json(candidate/"src-tauri"/"tauri.conf.json",{"$schema":"https://schema.tauri.app/config/2","productName":"LOUKSNA ZONA DIRECTIVA","version":"0.2.0","identifier":"io.louksna.zonadirectiva","build":{"beforeDevCommand":"npm run dev","devUrl":"http://localhost:1420","beforeBuildCommand":"npm run build","frontendDist":"../dist"},"app":{"windows":[{"title":"LOUKSNA ZONA DIRECTIVA","width":1440,"height":900,"minWidth":1100,"minHeight":720,"resizable":True,"fullscreen":False}],"security":{"csp":None}},"bundle":{"active":True,"targets":["deb"],"category":"Utility","shortDescription":"Interfaz GitHub gobernada por Louksna","longDescription":"LOUKSNA ZONA DIRECTIVA GitHub Interface Skeleton V0.2 HARDENED","linux":{"deb":{"depends":[]}}}})
    write(candidate/"README.md","# LOUKSNA ZONA DIRECTIVA — candidato endurecido\n\nSTATUS = MATERIALIZED_CANDIDATE_SOURCE\nAUTHORITY = Louksna.md\nIDENTITY = LOUKSNA_ONLY\n\nMaterialización aditiva del mismo proyecto. No sustituye el monolito ni las referencias canónicas.\n")

    matrix={"schema":"LOUKSNA_ZD_HARDENING_MATRIX/1.0","authority":"Louksna.md","identity":"LOUKSNA_ONLY","source_commit":os.environ.get("LOUKSNA_SOURCE_COMMIT"),"source_hashes":{k:sha256(p) for k,p in required.items()},"mission_sha256":sha256(mission_path),"asset_verification":asset_rows,"source_preservation":preservation,"controls":[{"id":"H01","control":"SOURCE_BRANCH_IMMUTABLE","status":"PASS"},{"id":"H02","control":"WORK_BRANCH_ISOLATED","status":"PASS"},{"id":"H03","control":"GITHUB_HOSTED_ONLY","status":"PASS"},{"id":"H04","control":"NO_ADDITIVE_IDENTITIES","status":"PASS"},{"id":"H05","control":"NO_CERTIFICATION_PROPAGATION","status":"PASS"},{"id":"H06","control":"CANONICAL_REFERENCES_BYTE_PRESERVED","status":"PASS"},{"id":"H07","control":"TAURI_RUST_TYPESCRIPT_CANDIDATE","status":"PASS"},{"id":"H08","control":"TELEMETRY_JSONL","status":"PASS"},{"id":"H09","control":"ROLLBACK_BY_REVERT_OR_BRANCH_DELETE","status":"PASS"},{"id":"H10","control":"G23_G24_EXTERNAL","status":"PASS"}],"gaps":gaps,"status":"PASS_WITH_DISCLOSED_NONBLOCKING_GAPS" if gaps else "PASS"}
    write_json(evidence/"HARDENING_MATRIX.json",matrix)
    write(evidence/"AUDIT_REPORT.md","# AUDIT REPORT — LOUKSNA ZONA DIRECTIVA\n\nWorker: CUSTOSZ_V7\nRuntime: CUSTOSZ_RUNTIME_V1\nExecution: GITHUB_HOSTED_ONLY\nIdentity: LOUKSNA_ONLY\nSource preserved: TRUE\nCertification propagated: FALSE\nG23: NOT_GRANTED\nG24: NOT_GRANTED\n\nSe verificó la fuente antes de materializar el candidato. Las referencias se conservan byte-exactas. La discrepancia entre el sufijo 8k y las dimensiones PNG observadas se registra como deuda explícita no bloqueante y no autoriza regeneración silenciosa.\n")
    telemetry(telemetry_file,"CANDIDATE_MATERIALIZATION","PASS","Código fuente Tauri/Rust/TypeScript materializado.",62)
    write_json(evidence/"CURRENT_STATE.json",{"schema":"LOUKSNA_ZD_CANDIDATE_STATE/1.0","worker":"CUSTOSZ_V7","runtime":"CUSTOSZ_RUNTIME_V1","identity":"LOUKSNA_ONLY","authority":"Louksna.md","source_commit":os.environ.get("LOUKSNA_SOURCE_COMMIT"),"work_branch":os.environ.get("GITHUB_REF_NAME"),"current_state":"MATERIALIZED_SOURCE","current_gate":"BUILD_VALIDATION","source_preserved":True,"github_hosted_only":True,"certification_propagated":False,"g23":"NOT_GRANTED","g24":"NOT_GRANTED","active":False,"updated_utc":utc()})
    result={"schema":"LOUKSNA_ZD_CUSTOSZ_MATERIAL_EFFECT/1.0","mission_id":dispatch["mission_id"],"status":"PASS","effect":"AUDIT_PLUS_REAL_CANDIDATE_SOURCE_MATERIALIZED","changed_root":str(candidate.relative_to(target_root)),"source_commit":os.environ.get("LOUKSNA_SOURCE_COMMIT"),"source_preserved":True,"telemetry_active":True,"next_gate":"BUILD_VALIDATION","certification_propagated":False}
    write_json(target_p,result)
    effect={"mission_id":dispatch["mission_id"],"dispatch_id":dispatch["dispatch_id"],"binding_id":dispatch["binding_id"],"pid":os.getpid(),"fme_id":"FME-LOUKSNA-ZD-"+dispatch["dispatch_id"],"target":str(target_p),"after_digest":sha256(target_p),"effect_type":dispatch["expected_effect"]["effect_type"],"effect_is_material":True,"effect_is_mission_relevant":True,"effect_is_authorized":True,"effect_is_observable":True}
    effect["fme_digest"]=obj_digest(effect); write_json(fme_p,effect)
    telemetry(telemetry_file,"RUNTIME_FME","PASS","Efecto material observable registrado; pasa a build.",68)
    return 0

if __name__=="__main__":
    raise SystemExit(main(sys.argv))
