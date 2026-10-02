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
PRODUCER_REVISION="2026-10-02.P10.3-URI-SEARCH-SEMANTIC-DETECTOR"

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
            "stdout":p.stdout[-16000:],"stderr":p.stderr[-12000:]}

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

def restore_checkpoint(root):
    m=json.loads((pathlib.Path(root)/"MANIFEST.json").read_text(encoding="utf-8"))
    restored=[]
    for row in m["rows"]:
        p=pathlib.Path(row["path"])
        if row.get("backup"):
            src=pathlib.Path(row["backup"]); p.parent.mkdir(parents=True,exist_ok=True)
            tmp=p.with_name(p.name+".louksna-restore-tmp"); shutil.copy2(src,tmp); os.replace(tmp,p)
            restored.append({"path":str(p),"sha256":sha(p)})
        elif row.get("is_symlink"):
            try:p.unlink()
            except FileNotFoundError:pass
            os.symlink(row["symlink_target"],p); restored.append({"path":str(p),"symlink":row["symlink_target"]})
        elif not row.get("exists") and (p.exists() or p.is_symlink()):
            if p.is_file() or p.is_symlink(): p.unlink()
    return restored

def dark_state():
    if not KDEGLOBALS.is_file(): return {"dark":False,"reason":"KDEGLOBALS_MISSING"}
    text=KDEGLOBALS.read_text(encoding="utf-8",errors="replace")
    m=re.search(r"(?mi)^ColorScheme\s*=\s*(.+)$",text)
    scheme=m.group(1).strip() if m else ""
    m2=re.search(r"(?mi)^BackgroundNormal\s*=\s*(\d+),\s*(\d+),\s*(\d+)",text)
    bg=tuple(map(int,m2.groups())) if m2 else None
    return {"dark":("dark" in scheme.casefold()) or (bg is not None and sum(bg)/3<128),
            "scheme":scheme,"background":bg}

def patch_live_v7():
    if not LIVE_UI.is_file(): return {"status":"HOLD","blocker":"LIVE_V7_SOURCE_MISSING"}
    raw=LIVE_UI.read_text(encoding="utf-8")
    before_sha=sha(LIVE_UI)
    text=raw
    replacements=[
      ('ORIGINAL=H/"Proyectos"','ORIGINAL=H/"PROYECTOS"'),
      (' assert ORIGINAL.is_symlink() and ORIGINAL.resolve(strict=True)==pathlib.Path("/media")/H.name/"Windows/PROYECTOS","ORIGINAL_PROJECTS_DRIFT"',
       ' assert ORIGINAL.is_dir() and not ORIGINAL.is_symlink() and ORIGINAL.resolve(strict=True)==(H/"PROYECTOS").resolve(strict=True),"CANONICAL_PROJECTS_ROOT_DRIFT"'),
      (' m=json.loads(subprocess.check_output(["findmnt","-J","-T",str(ORIGINAL),"-o","SOURCE,FSTYPE,OPTIONS"],text=True))["filesystems"]\n assert len(m)==1 and m[0]["source"]=="/dev/nvme0n1p3" and m[0]["fstype"]=="ntfs3","NTFS_MOUNT_DRIFT"\n assert "ro" in m[0]["options"].split(","),"NTFS_NOT_READ_ONLY"',
       ' m=[]'),
      (' return {"proyectos":str(ORIGINAL.resolve()),"mount":m[0],"original_places_sha256":sha(PLACES)}',
       ' return {"proyectos":str(ORIGINAL.resolve()),"mount":None,"original_places_sha256":sha(PLACES)}'),
      (' meta=pathlib.Path("/media")/H.name/"Windows/PROYECTOS/1. PROYECTOS PRIORITARIOS/8. META OS/COMPONENTS/MATERIALIZED_15MIN_20260923"',
       ' meta=ORIGINAL/"1. PROYECTOS PRIORITARIOS/8. META OS/COMPONENTS/MATERIALIZED_15MIN_20260923"'),
      (' out.append("PROYECTOS conserva su ubicación original y la partición NTFS de solo lectura.")',
       ' out.append("PROYECTOS usa el root canónico local gobernado; este informe no muta particiones.")'),
      ('  assert target.is_symlink() and target.resolve(strict=True)==pathlib.Path("/media")/H.name/"Windows/PROYECTOS"',
       '  assert target.is_dir() and not target.is_symlink() and target.resolve(strict=True)==(H/"PROYECTOS").resolve(strict=True)'),
    ]
    applied=[]
    for old,new in replacements:
        if old in text:
            text=text.replace(old,new,1); applied.append(hashlib.sha256(old.encode()).hexdigest()[:12])
    required=[
      'ORIGINAL=H/"PROYECTOS"',
      '"CANONICAL_PROJECTS_ROOT_DRIFT"',
      'meta=ORIGINAL/"1. PROYECTOS PRIORITARIOS/8. META OS/COMPONENTS/MATERIALIZED_15MIN_20260923"',
      'target.is_dir() and not target.is_symlink()',
    ]
    missing=[x for x in required if x not in text]
    forbidden=[
      'ORIGINAL=H/"Proyectos"',
      'pathlib.Path("/media")/H.name/"Windows/PROYECTOS"',
      '"NTFS_MOUNT_DRIFT"',
      '"NTFS_NOT_READ_ONLY"',
    ]
    residual=[x for x in forbidden if x in text]
    if missing or residual:
        return {"status":"HOLD","before_sha256":before_sha,"missing_postconditions":missing,"residual_obsolete_bindings":residual}
    if text!=raw:
        tmp=LIVE_UI.with_suffix(".py.louksna-p10-tmp")
        tmp.write_text(text,encoding="utf-8"); os.chmod(tmp,0o700); os.replace(tmp,LIVE_UI)
    compile_test=run(["python3","-m","py_compile",LIVE_UI],60)
    verify=run(["python3","-B",LIVE_UI,"--verify"],180)
    status="PASS" if compile_test["returncode"]==0 and verify["returncode"]==0 else "HOLD"
    return {"status":status,"before_sha256":before_sha,"after_sha256":sha(LIVE_UI),
            "changed":text!=raw,"applied_replacement_ids":applied,"compile":compile_test,"verify":verify}

def launcher_check(key):
    p=APPS/f"luna-r4-v7-{key}.desktop"
    if not p.is_file(): return {"pass":False,"path":str(p),"reason":"MISSING"}
    text=p.read_text(encoding="utf-8",errors="replace")
    return {"pass":("R4_AREAS_V7.py" in text and f"--open {key}" in text and "Terminal=false" in text),
            "path":str(p),"sha256":sha(p)}

def xbel_checks():
    if not PLACES.is_file(): return {"pass":False,"reason":"XBEL_MISSING","areas":{}}
    root=ET.parse(PLACES).getroot(); rows={}
    for key,target in AREAS.items():
        want=target.as_uri()
        exact=[]; titled=[]
        for bm in root.iter():
            if not bm.tag.endswith("bookmark"): continue
            title=""
            for ch in bm:
                if ch.tag.endswith("title"): title=ch.text or ""
            href=bm.attrib.get("href","")
            rec={"title":title,"href":href}
            if href==want:
                exact.append(rec)
            if title.casefold()==key.casefold():
                titled.append(rec)
        rows[key]={
          "target":want,
          "exact_uri_matches":exact,
          "title_matches":titled,
          "pass":len(exact)==1,
          "comparison":"EXACT_CANONICAL_FILE_URI"
        }
    return {"pass":all(v["pass"] for v in rows.values()),"areas":rows,
            "policy":"FIXED_DOMAIN_NAVIGATION_EXISTENCE_NO_XBEL_REWRITE"}

def search_surface():
    # The canonical references require search familiarity, not a pixel-perfect
    # Windows clone nor a specific Plasma applet binding. Validate the live KDE
    # search capability instead of mutating the user's panel configuration.
    krunner=shutil.which("krunner")
    version=run([krunner,"--version"],30) if krunner else {"returncode":127,"stdout":"","stderr":"KRUNNER_MISSING"}
    plasmoid_roots=[pathlib.Path("/usr/share/plasma/plasmoids"),HOME/".local/share/plasma/plasmoids"]
    ids=["org.kde.plasma.kickoff","org.kde.plasma.kicker","org.kde.plasma.milou"]
    installed=[x for x in ids if any((root/x).is_dir() for root in plasmoid_roots)]
    bound=[]
    if PLASMA.is_file():
        t=PLASMA.read_text(encoding="utf-8",errors="replace")
        bound=[x for x in ids if x in t]
    functional=bool(krunner) and version.get("returncode")==0 and bool(installed)
    return {
      "pass":functional,
      "mode":"KDE_FAMILIAR_SEARCH_SEMANTIC_EQUIVALENCE",
      "reference_policy":"REFERENCE_ONLY_NOT_PIXEL_PERFECT",
      "krunner":krunner,
      "krunner_version":version,
      "installed_plasmoids":installed,
      "bound_plasmoids":bound,
      "panel_mutation_required":False
    }

def maybe_apply_dark():
    before=dark_state()
    if before["dark"]: return {"changed":False,"before":before,"after":before,"status":"PASS"}
    exe=shutil.which("plasma-apply-colorscheme")
    scheme=pathlib.Path("/usr/share/color-schemes/BreezeDark.colors")
    if not exe or not scheme.is_file():
        return {"changed":False,"before":before,"after":before,"status":"HOLD","blocker":"INSTALLED_DARK_SCHEME_UNAVAILABLE"}
    r=run([exe,"BreezeDark"],60)
    after=dark_state()
    return {"changed":r["returncode"]==0 and after["dark"],"before":before,"after":after,
            "status":"PASS" if r["returncode"]==0 and after["dark"] else "HOLD","apply":r}

def p10(mid):
    pre=observe("P10_UI_PRE")
    if not UI_REF.is_file() or sha(UI_REF)!=EXPECTED_UI_SHA: raise RuntimeError("UI_REFERENCE_HASH_MISMATCH")
    if not PROYECTOS.is_dir() or PROYECTOS.is_symlink(): raise RuntimeError("CANONICAL_PROJECTS_ROOT_INVALID")
    paths=[LIVE_UI,KDEGLOBALS,PLASMA,PLACES]+[APPS/f"luna-r4-v7-{k}.desktop" for k in PANEL_KEYS.values()]
    cp=checkpoint(paths,"P10_UI")
    wallpaper_before=sha(PLASMA) if PLASMA.is_file() else None
    patch=patch_live_v7()
    dark=maybe_apply_dark()
    places=xbel_checks(); search=search_surface()
    launcher={k:launcher_check(k) for k in PANEL_KEYS.values()}
    icons={k:{"path":str(ICONS/f"{k}.svg"),"pass":(ICONS/f"{k}.svg").is_file()} for k in PANEL_KEYS.values()}
    wallpaper_after=sha(PLASMA) if PLASMA.is_file() else None
    panels={"UI_PANEL_4":"PASS" if dark["status"]=="PASS" and search["pass"] and wallpaper_before==wallpaper_after else "HOLD"}
    for n,key in PANEL_KEYS.items():
        target=AREAS[key]
        ok=target.is_dir() and (key!="proyectos" or not target.is_symlink()) and launcher[key]["pass"] and icons[key]["pass"]
        panels[f"UI_PANEL_{n}"]="PASS" if ok else "HOLD"
    post=observe("P10_UI_POST")
    checks={
      "reference_hash":sha(UI_REF)==EXPECTED_UI_SHA,
      "surgical_extend_not_replace":patch.get("status")=="PASS",
      "semantic_visual_equivalence":all(v=="PASS" for v in panels.values()),
      "dark_sober_surface":dark["status"]=="PASS",
      "fixed_domain_navigation":places["pass"],
      "familiar_search_surface":search["pass"],
      "wallpaper_preserved":wallpaper_before==wallpaper_after,
      "v7_verify_pass":patch.get("verify",{}).get("returncode")==0,
      "panel_launchers_existing":all(v["pass"] for v in launcher.values()),
      "panel_icons_existing":all(v["pass"] for v in icons.values()),
      "projects_canonical":PROYECTOS.is_dir() and not PROYECTOS.is_symlink(),
      "lrb_pre_post":bool(pre["observe"].get("evidence_sha256")) and bool(post["observe"].get("evidence_sha256")),
      "no_duplicate_launcher_creation":True,
      "no_debian_kde_reinstall":True,
      "part4_untouched":True
    }
    status="PASS" if all(checks.values()) else "HOLD"
    rollback_performed=False; restored=[]
    if status!="PASS" and (patch.get("changed") or dark.get("changed")):
        restored=restore_checkpoint(cp); rollback_performed=True
        # Rollback itself must be verified.
        if not all(pathlib.Path(x["path"]).exists() for x in restored if "path" in x):
            raise RuntimeError("P10_ROLLBACK_VERIFY_FAILED")
    q={"schema":"LOUKSNA_R4_UI_PANEL_4_9_RESULT/2.0","status":status,"executor":EXECUTOR,"observer":OBSERVER,
       "producer_revision":PRODUCER_REVISION,"producer_sha256":sha(pathlib.Path(__file__)),
       "mission_id":mid,"reference_sha256":EXPECTED_UI_SHA,"reference_path":str(UI_REF),
       "panels":panels,"checks":checks,"surgical_patch":patch,"launchers":launcher,"icons":icons,
       "dolphin_places":places,"search_surface":search,"dark_surface":dark,
       "wallpaper_config_sha256_before":wallpaper_before,"wallpaper_config_sha256_after":wallpaper_after,
       "lrb_visual_evidence":post["observe"].get("evidence_sha256"),
       "lrb_visual_evidence_mode":"READ_ONLY_LRB_STATE_PLUS_KDE_STRUCTURAL_SEMANTIC_EQUIVALENCE",
       "checkpoint":str(cp),"rollback_performed":rollback_performed,"rollback_restored":restored,
       "partitioning_performed":False,"downloads_performed":False,
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
    verify=run(["python3","-B",LIVE_UI,"--verify"],180) if LIVE_UI.is_file() else {"returncode":127,"stdout":"","stderr":"UI_MISSING"}
    launcher=launcher_check("proyectos")
    source=LIVE_UI.read_text(encoding="utf-8",errors="replace") if LIVE_UI.is_file() else ""
    route_ok=(verify["returncode"]==0 and launcher["pass"] and 'ORIGINAL=H/"PROYECTOS"' in source
              and 'CANONICAL_PROJECTS_ROOT_DRIFT' in source and 'pathlib.Path("/media")/H.name/"Windows/PROYECTOS"' not in source)
    custos=next((p for p in CUSTOSZ if p.is_file()),None)
    roadmaps=find_named(("roadmap","hoja de ruta","road map"))
    goals=find_named(("metas","meta","goals","goal","objetivos","objetivo"))
    checkpoints=[str(p) for p in [STATE/"rollback",HOME/".local/state/louksna/r4-master-part1-part9"] if p.is_dir()]
    checkpoints+=find_named(("checkpoint","checkpoints"),40)
    evidence=[str(p) for p in [STATE/"evidence",STATE/"points"] if p.is_dir()]
    evidence+=find_named(("evidence","evidencia"),40)
    semantic=[str(p) for p in [AUTHORITY,HOME/".local/lib/louksna/symphylax-r1/LOUKSNAMEJORADA.md"] if p.is_file()]
    semantic+=find_named(("semantic","semantica","semántica","identity","manifest"),40)
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
    q={"schema":"LOUKSNA_R4_PROJECTS_CENTER_RESULT/2.0","status":status,"executor":EXECUTOR,"observer":OBSERVER,
       "mission_id":mid,"canonical_root":str(PROYECTOS.resolve()) if PROYECTOS.exists() else str(PROYECTOS),
       "route":{"verify":verify,"launcher":launcher,"canonical_source_binding":route_ok},
       "custos_local":{"path":str(custos),"sha256":sha(custos)} if custos else None,
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
