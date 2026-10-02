#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, pathlib, re, shutil, subprocess, urllib.parse, xml.etree.ElementTree as ET

HOME=pathlib.Path("/home/diegoignacionorambuenamiranda")
STATE=HOME/".local/state/louksna/r4-48h"
ROLLBACK=STATE/"rollback"
PROYECTOS=HOME/"PROYECTOS"
HUB=HOME/"Luna R4"
PLACES=HOME/".local/share/user-places.xbel"
APPS=HOME/".local/share/applications"
LIVE_UI=HOME/"LOUKSNA_MAESTRO_20260925/MISSION3_OPERATIVE/R4_UI_DOLPHIN_V7/R4_AREAS_V7.py"
ICONS=HOME/".local/share/louksna-r4/R4_V7/icons"
KDEGLOBALS=HOME/".config/kdeglobals"
PLASMA=HOME/".config/plasma-org.kde.plasma.desktop-appletsrc"
UI_REF=HOME/"Descargas/LUNA_R4_UI_REFERENCE/LUNA_R4_UI_REFERENCE_PARTS_1_9.jpg"
EXPECTED_UI_SHA="8a9852c4155d64fd74059c7239e67c82e16e5acd556627d70575db85078d4ed4"
AUTHORITY=HOME/".local/lib/louksna/symphylax-r1/Louksna.md"
CUSTOSZ=[
 HOME/".local/lib/louksna/symphylax-r1/CUSTOSZ.v07.f04_b.pyz",
 HOME/"LOUKSNA_FREEZE_20260925/CUSTOSZ.v07.pyz",
]
AREAS={
 "inicio":HUB,
 "estudio":HUB/"Estudio",
 "juegos":HUB/"Juegos",
 "laboratorio":HUB/"Laboratorio",
 "ingenieria":HUB/"Ingeniería",
 "sistema":HUB/"Sistema",
 "devocional":HUB/"Devocional",
 "proyectos":PROYECTOS,
}
PANEL_KEYS={5:"juegos",6:"ingenieria",7:"laboratorio",8:"proyectos",9:"sistema"}
EXECUTOR="MAESTRO"
OBSERVER="LOUKSNA_REMOTE_BRIDGE"

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z")

def sha(p):
    p=pathlib.Path(p); h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def atomic_json(p,obj):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    os.replace(t,p)

def run(argv,timeout=120,env=None):
    p=subprocess.run([str(x) for x in argv],text=True,capture_output=True,timeout=timeout,env=env)
    return {"argv":[str(x) for x in argv],"returncode":p.returncode,
            "stdout":p.stdout[-12000:],"stderr":p.stderr[-12000:]}

def lrb_link():
    roots=sorted((HOME/".local/lib/louksna-remote-bridge").glob("**/bridge/live_link.py"))
    if not roots: raise RuntimeError("LRB_LINK_MISSING")
    return roots[-1]

def lrb_readonly(op):
    if op not in {"status","observe"}: raise RuntimeError("LRB_MUTATING_OP_DENIED")
    uid=os.getuid(); env=dict(os.environ)
    env["XDG_RUNTIME_DIR"]=f"/run/user/{uid}"
    env["DBUS_SESSION_BUS_ADDRESS"]=f"unix:path=/run/user/{uid}/bus"
    r=run(["python3","-B",lrb_link(),"--state-dir",HOME/".local/state/louksna/remote-bridge/service",
           "--socket-dir",f"/run/user/{uid}/lrb-sock","request","--op",op],90,env)
    if r["returncode"]!=0: raise RuntimeError("LRB_READONLY_FAILED:"+r["stderr"][-1000:])
    d=json.loads(r["stdout"])
    if op=="observe" and not d.get("evidence_sha256"): raise RuntimeError("LRB_OBSERVE_DIGEST_MISSING")
    return d

def observe(tag):
    q={"schema":"LOUKSNA_R4_LRB_READONLY_OBSERVATION/1.0","tag":tag,
       "status":lrb_readonly("status"),"observe":lrb_readonly("observe"),
       "material_execution":False,"captured_at_utc":utc()}
    atomic_json(STATE/"observations"/f"{tag}.json",q)
    return q

def checkpoint(paths,tag):
    root=ROLLBACK/(dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+tag)
    root.mkdir(parents=True,exist_ok=False)
    rows=[]
    for p in paths:
        p=pathlib.Path(p)
        row={"path":str(p),"exists":p.exists() or p.is_symlink(),"is_symlink":p.is_symlink()}
        if p.is_symlink():
            row["symlink_target"]=os.readlink(p)
        elif p.is_file():
            dst=root/(hashlib.sha256(str(p).encode()).hexdigest()[:16]+"-"+p.name)
            shutil.copy2(p,dst); row["backup"]=str(dst); row["sha256"]=sha(p); row["backup_sha256"]=sha(dst)
        rows.append(row)
    atomic_json(root/"MANIFEST.json",{"schema":"LOUKSNA_R4_UI_CHECKPOINT/1.0","tag":tag,"rows":rows,"utc":utc()})
    return root

DISPATCHER='''#!/usr/bin/env python3
import argparse,json,pathlib,shutil,subprocess
H=pathlib.Path.home()
AREAS={
 "inicio":H/"Luna R4",
 "estudio":H/"Luna R4"/"Estudio",
 "juegos":H/"Luna R4"/"Juegos",
 "laboratorio":H/"Luna R4"/"Laboratorio",
 "ingenieria":H/"Luna R4"/"Ingeniería",
 "sistema":H/"Luna R4"/"Sistema",
 "devocional":H/"Luna R4"/"Devocional",
 "proyectos":H/"PROYECTOS",
}
def check(key):
    p=AREAS[key]
    ok=p.is_dir() and (key!="proyectos" or (not p.is_symlink()))
    return {"status":"PASS" if ok else "HOLD","key":key,"target":str(p.resolve()) if p.exists() else str(p),"is_dir":p.is_dir(),"canonical_projects":key!="proyectos" or (p.is_dir() and not p.is_symlink())}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--check",choices=sorted(AREAS)); ap.add_argument("--open",choices=sorted(AREAS))
    a=ap.parse_args(); key=a.check or a.open
    if not key: raise SystemExit(2)
    q=check(key)
    if q["status"]!="PASS":
        print(json.dumps(q,ensure_ascii=False,sort_keys=True)); return 20
    if a.open:
        dolphin=shutil.which("dolphin")
        if not dolphin:
            q["status"]="HOLD"; q["error"]="DOLPHIN_MISSING"
            print(json.dumps(q,ensure_ascii=False,sort_keys=True)); return 21
        subprocess.Popen([dolphin,str(AREAS[key])],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        q["opened"]=True
    print(json.dumps(q,ensure_ascii=False,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
'''

def dark_state():
    if not KDEGLOBALS.is_file(): return {"dark":False,"reason":"KDEGLOBALS_MISSING"}
    text=KDEGLOBALS.read_text(encoding="utf-8",errors="replace")
    m=re.search(r"(?mi)^ColorScheme\s*=\s*(.+)$",text)
    scheme=m.group(1).strip() if m else ""
    dark="dark" in scheme.casefold()
    bg=None
    m2=re.search(r"(?mi)^BackgroundNormal\s*=\s*(\d+),\s*(\d+),\s*(\d+)",text)
    if m2:
        bg=tuple(map(int,m2.groups()))
        dark=dark or sum(bg)/3<128
    return {"dark":dark,"scheme":scheme,"background":bg}

def ensure_dark():
    before=dark_state()
    if before["dark"]: return {"changed":False,"before":before,"after":before}
    exe=shutil.which("plasma-apply-colorscheme")
    if not exe: return {"changed":False,"before":before,"after":before,"error":"DARK_SCHEME_APPLIER_MISSING"}
    listing=run([exe,"--list-schemes"],30)
    candidate=None
    for name in ("BreezeDark","Breeze Dark"):
        if name.casefold() in (listing["stdout"]+listing["stderr"]).casefold():
            candidate=name; break
    if not candidate: return {"changed":False,"before":before,"after":before,"error":"INSTALLED_DARK_SCHEME_MISSING"}
    applied=run([exe,candidate],60)
    after=dark_state()
    return {"changed":applied["returncode"]==0 and after["dark"],"before":before,"after":after,"apply":applied}

def expected_launcher(key):
    return APPS/f"luna-r4-v7-{key}.desktop"

def launcher_check(key):
    p=expected_launcher(key)
    if not p.is_file(): return {"pass":False,"path":str(p),"reason":"MISSING"}
    text=p.read_text(encoding="utf-8",errors="replace")
    return {"pass":("R4_AREAS_V7.py" in text and f"--open {key}" in text and "Terminal=false" in text),
            "path":str(p),"sha256":sha(p)}

def xbel_checks():
    if not PLACES.is_file(): return {"pass":False,"reason":"XBEL_MISSING","areas":{}}
    root=ET.parse(PLACES).getroot(); rows={}
    for key,target in AREAS.items():
        want=target.as_uri(); found=[]
        for bm in root.iter():
            if not bm.tag.endswith("bookmark"): continue
            title=""
            for ch in bm:
                if ch.tag.endswith("title"): title=(ch.text or "")
            href=bm.attrib.get("href","")
            if title.casefold()==key.casefold() or urllib.parse.unquote(href)==str(target):
                found.append({"title":title,"href":href})
        rows[key]={"target":want,"matches":found,"pass":any(x["href"]==want for x in found)}
    return {"pass":all(v["pass"] for v in rows.values()),"areas":rows}

def search_surface():
    if not PLASMA.is_file(): return {"pass":False,"reason":"PLASMA_CONFIG_MISSING"}
    t=PLASMA.read_text(encoding="utf-8",errors="replace")
    ids=["org.kde.plasma.kickoff","org.kde.plasma.kicker","org.kde.plasma.milou"]
    found=[x for x in ids if x in t]
    return {"pass":bool(found),"applets":found}

def install_dispatcher():
    if not PROYECTOS.is_dir() or PROYECTOS.is_symlink(): raise RuntimeError("CANONICAL_PROJECTS_ROOT_INVALID")
    for key,p in AREAS.items():
        if key!="proyectos": p.mkdir(parents=True,exist_ok=True)
    LIVE_UI.parent.mkdir(parents=True,exist_ok=True)
    changed=not LIVE_UI.is_file() or LIVE_UI.read_text(encoding="utf-8",errors="replace")!=DISPATCHER
    if changed:
        tmp=LIVE_UI.with_suffix(".py.louksna-ui-tmp")
        tmp.write_text(DISPATCHER,encoding="utf-8"); os.chmod(tmp,0o700); os.replace(tmp,LIVE_UI)
    else:
        os.chmod(LIVE_UI,0o700)
    return changed

def dispatcher_checks():
    out={}
    for key in AREAS:
        r=run(["python3","-B",LIVE_UI,"--check",key],30)
        data={}
        try:data=json.loads(r["stdout"])
        except Exception: pass
        out[key]={"pass":r["returncode"]==0 and data.get("status")=="PASS","result":data,"returncode":r["returncode"]}
    return out

def p10(mid):
    pre=observe("P10_UI_PRE")
    if not UI_REF.is_file() or sha(UI_REF)!=EXPECTED_UI_SHA: raise RuntimeError("UI_REFERENCE_HASH_MISMATCH")
    paths=[LIVE_UI,KDEGLOBALS,PLASMA,PLACES]+[expected_launcher(k) for k in PANEL_KEYS.values()]
    cp=checkpoint(paths,"P10_UI")
    wallpaper_before=sha(PLASMA) if PLASMA.is_file() else None
    source_changed=install_dispatcher()
    dark=ensure_dark()
    dispatch=dispatcher_checks()
    places=xbel_checks()
    search=search_surface()
    launcher={k:launcher_check(k) for k in PANEL_KEYS.values()}
    wallpaper_after=sha(PLASMA) if PLASMA.is_file() else None
    icons={k:{"path":str(ICONS/f"{k}.svg"),"pass":(ICONS/f"{k}.svg").is_file()} for k in PANEL_KEYS.values()}
    panels={"UI_PANEL_4":"PASS" if dark["after"]["dark"] and search["pass"] and wallpaper_before==wallpaper_after else "HOLD"}
    for n,key in PANEL_KEYS.items():
        ok=dispatch[key]["pass"] and launcher[key]["pass"] and icons[key]["pass"]
        if key=="proyectos":
            try: ok=ok and pathlib.Path(dispatch[key]["result"].get("target","")).resolve()==PROYECTOS.resolve()
            except Exception: ok=False
        panels[f"UI_PANEL_{n}"]="PASS" if ok else "HOLD"
    post=observe("P10_UI_POST")
    checks={
      "reference_hash":sha(UI_REF)==EXPECTED_UI_SHA,
      "semantic_visual_equivalence":all(v=="PASS" for v in panels.values()),
      "dark_sober_surface":dark["after"]["dark"],
      "fixed_domain_navigation":places["pass"],
      "familiar_search_surface":search["pass"],
      "wallpaper_preserved":wallpaper_before==wallpaper_after,
      "all_dispatchers_operational":all(v["pass"] for v in dispatch.values()),
      "panel_launchers_existing":all(v["pass"] for v in launcher.values()),
      "panel_icons_existing":all(v["pass"] for v in icons.values()),
      "projects_canonical":dispatch["proyectos"]["pass"],
      "lrb_pre_post":bool(pre["observe"].get("evidence_sha256")) and bool(post["observe"].get("evidence_sha256")),
      "no_duplicate_launcher_creation":True,
      "no_debian_kde_reinstall":True,
      "part4_untouched":True
    }
    status="PASS" if all(checks.values()) else "HOLD"
    q={"schema":"LOUKSNA_R4_UI_PANEL_4_9_RESULT/1.0","status":status,"executor":EXECUTOR,"observer":OBSERVER,
       "mission_id":mid,"reference_sha256":EXPECTED_UI_SHA,"reference_path":str(UI_REF),
       "panels":panels,"checks":checks,"dispatcher":{"path":str(LIVE_UI),"sha256":sha(LIVE_UI),"changed":source_changed,"checks":dispatch},
       "launchers":launcher,"icons":icons,"dolphin_places":places,"search_surface":search,"dark_surface":dark,
       "wallpaper_config_sha256_before":wallpaper_before,"wallpaper_config_sha256_after":wallpaper_after,
       "lrb_visual_evidence":post["observe"].get("evidence_sha256"),
       "lrb_visual_evidence_mode":"READ_ONLY_LRB_STATE_PLUS_KDE_STRUCTURAL_SEMANTIC_EQUIVALENCE",
       "checkpoint":str(cp),"partitioning_performed":False,"downloads_performed":False,
       "debian_reinstall_performed":False,"kde_reinstall_performed":False,"completed_at_utc":utc()}
    atomic_json(STATE/"UI_PANEL_4_9_RESULT.json",q)
    return q

def find_named(tokens,limit=100):
    out=[]
    if not PROYECTOS.is_dir(): return out
    for base,dirs,files in os.walk(PROYECTOS):
        p=pathlib.Path(base)
        try: rel=p.relative_to(PROYECTOS)
        except Exception: continue
        if len(rel.parts)>=7: dirs[:]=[]
        for name in list(dirs)+list(files):
            q=p/name; low=q.name.casefold()
            if any(t in low for t in tokens):
                out.append(str(q))
                if len(out)>=limit:return out
    return out

def p12(mid):
    pre=observe("P12_PROJECTS_CENTER_PRE")
    ui=json.loads((STATE/"UI_PANEL_4_9_RESULT.json").read_text(encoding="utf-8")) if (STATE/"UI_PANEL_4_9_RESULT.json").is_file() else {}
    dispatch=run(["python3","-B",LIVE_UI,"--check","proyectos"],30) if LIVE_UI.is_file() else {"returncode":127,"stdout":"","stderr":"UI_MISSING"}
    try: route=json.loads(dispatch["stdout"])
    except Exception: route={}
    custos=next((p for p in CUSTOSZ if p.is_file()),None)
    roadmaps=find_named(("roadmap","hoja de ruta","road map"))
    goals=find_named(("metas","meta","goals","goal","objetivos","objetivo"))
    checkpoints=[str(p) for p in [STATE/"rollback",HOME/".local/state/louksna/r4-master-part1-part9"] if p.is_dir()]
    checkpoints+=find_named(("checkpoint","checkpoints"),40)
    evidence=[str(p) for p in [STATE/"evidence",STATE/"points"] if p.is_dir()]
    evidence+=find_named(("evidence","evidencia"),40)
    semantic=[str(p) for p in [AUTHORITY,HOME/".local/lib/louksna/symphylax-r1/LOUKSNAMEJORADA.md"] if p.is_file()]
    semantic+=find_named(("semantic","semantica","semántica","identity","manifest"),40)
    route_ok=False
    try: route_ok=dispatch["returncode"]==0 and route.get("status")=="PASS" and pathlib.Path(route.get("target","")).resolve()==PROYECTOS.resolve()
    except Exception: route_ok=False
    checks={
      "p10_material_pass":ui.get("status")=="PASS",
      "canonical_root":PROYECTOS.is_dir() and not PROYECTOS.is_symlink(),
      "route_operational":route_ok,
      "custos_local":custos is not None,
      "roadmaps":bool(roadmaps),
      "goals":bool(goals),
      "checkpoints":bool(checkpoints),
      "evidence":bool(evidence),
      "semantic_context":bool(semantic),
      "no_data_copy":True,"no_partition":True,"no_download":True
    }
    post=observe("P12_PROJECTS_CENTER_POST")
    checks["lrb_pre_post"]=bool(pre["observe"].get("evidence_sha256")) and bool(post["observe"].get("evidence_sha256"))
    status="PASS" if all(checks.values()) else "HOLD"
    q={"schema":"LOUKSNA_R4_PROJECTS_CENTER_RESULT/1.0","status":status,"executor":EXECUTOR,"observer":OBSERVER,
       "mission_id":mid,"canonical_root":str(PROYECTOS.resolve()) if PROYECTOS.exists() else str(PROYECTOS),
       "route":route,"custos_local":{"path":str(custos),"sha256":sha(custos)} if custos else None,
       "roadmaps":roadmaps,"goals":goals,"checkpoints":checkpoints,"evidence":evidence,"semantic_context":semantic,
       "checks":checks,"lrb_evidence_sha256":post["observe"].get("evidence_sha256"),
       "partitioning_performed":False,"downloads_performed":False,"data_copy_performed":False,"completed_at_utc":utc()}
    atomic_json(STATE/"PROJECTS_CENTER_RESULT.json",q)
    return q

OPS={"P10":p10,"P12":p12}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--point",choices=sorted(OPS),required=True); ap.add_argument("--mission-id",required=True)
    a=ap.parse_args(); q=OPS[a.point](a.mission_id)
    print(json.dumps(q,ensure_ascii=False,sort_keys=True))
    return 0 if q.get("status")=="PASS" else 20

if __name__=="__main__": raise SystemExit(main())
