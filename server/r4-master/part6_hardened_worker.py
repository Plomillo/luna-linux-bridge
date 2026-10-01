#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, datetime as dt, hashlib, json, os, pathlib, shutil, subprocess, sys, tarfile, time, urllib.parse

HOME=pathlib.Path("/home/diegoignacionorambuenamiranda")
STATE=HOME/".local/state/louksna/r4-master-part1-part9"
D=STATE/"PART_6_HARDENED"
SOURCES=HOME/".local/share/louksna/r4-part6/sources"
COMPONENTS=HOME/".local/share/louksna/r4-part6/components"
BIN=HOME/".local/bin"
REPO="Plomillo/luna-linux-bridge"
BRANCH="staging/luna-r4-master-part1-part9-20260929"

STEAM_URL="https://repo.steampowered.com/steam/archive/stable/steam_latest.deb"
STEAM_DEB_SHA256="765aba9a0ed339a50226ceb614fcc9879a991ba184098bc8de920efb12c714a4"
STEAMCMD_URL="https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
STEAMCMD_SHA256="cebf0046bfd08cf45da6bc094ae47aa39ebf4155e5ede41373b579b8f1071e7c"
PROTON_RELEASE="proton-11.0-2"
PROTON_APP_ID=4628710
PROTON_REPO_URL="https://github.com/ValveSoftware/Proton.git"
PROTON_COMMIT="db9e6ffbf24a95b104fb699dd62532c70a2f9a51"
PROTON_BUILD_NAME="louksna-proton-11.0-2"
LUTRIS_URL="https://github.com/lutris/lutris/releases/download/v0.5.22/lutris_0.5.22_all.deb"
LUTRIS_SHA256="88a350357e0438b423cdf93108f27942de094dc19f973df73839f3b0b0bafaa0"
PRISM_URL="https://github.com/PrismLauncher/PrismLauncher/releases/download/11.1.1/PrismLauncher-Linux-x86_64.AppImage"
PRISM_SHA256="bb81038c56a09e944659e4b808dbfbc52d52d5e3a3ffe32216689a3ca1508d3d"
WAYDROID_REPO_URL="https://repo.waydro.id"
WAYDROID_SCRIPT_SHA256="2cf79f3cc82adb8c235faca0240c1312867afab0221e9aaf7a539a8614a503fd"
FLATHUB_REPO="https://dl.flathub.org/repo/flathub.flatpakrepo"
BOTTLES_APP="com.usebottles.bottles"

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z")

def sha(p):
    p=pathlib.Path(p)
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def atomic_json(p,obj):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    os.replace(t,p)

def read_json(p,default=None):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default

def run(argv,timeout=120,check=False,env=None,cwd=None):
    p=subprocess.run(argv,text=True,capture_output=True,timeout=timeout,env=env,cwd=cwd)
    r={"argv":[str(x) for x in argv],"returncode":p.returncode,"stdout":p.stdout[-12000:],"stderr":p.stderr[-8000:]}
    if check and p.returncode:
        raise RuntimeError("COMMAND_FAILED:"+json.dumps(r,ensure_ascii=False))
    return r

def command(name):
    return shutil.which(name)

def pkg_version(name):
    r=run(["dpkg-query","-W","-f=${Status}|${Version}",name],timeout=30)
    if r["returncode"]==0 and r["stdout"].startswith("install ok installed|"):
        return r["stdout"].split("|",1)[1].strip()
    return None

def apt_install(items,timeout=2400):
    if not items:
        return {"argv":[],"returncode":0,"stdout":"NOOP","stderr":""}
    env=dict(os.environ); env["DEBIAN_FRONTEND"]="noninteractive"
    return run(["sudo","-n","/usr/bin/apt-get","install","-y",*map(str,items)],timeout=timeout,check=True,env=env)

def download(url,path,timeout=900):
    path=pathlib.Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".part")
    r=run(["curl","-fL","--retry","3","--retry-delay","2","--connect-timeout","30","-o",str(tmp),url],timeout=timeout,check=True)
    os.replace(tmp,path)
    return {"url":url,"path":str(path),"bytes":path.stat().st_size,"sha256":sha(path),"curl":r}

def require_privilege():
    r=run(["sudo","-n","/usr/local/sbin/louksna-sudo-governance","status"],timeout=30)
    if r["returncode"]!=0:
        raise RuntimeError("PRIVILEGE_GOVERNANCE_STATUS_FAILED")
    try:
        d=json.loads(r["stdout"])
    except Exception as e:
        raise RuntimeError("PRIVILEGE_GOVERNANCE_JSON:"+str(e))
    root=run(["sudo","-n","id","-u"],timeout=15)
    ok=(d.get("status")=="ACTIVE" and d.get("policy_exact") is True and d.get("g24_certificate_local") is True
        and d.get("scope")=="UNRESTRICTED_ROOT_VIA_SUDO" and root["returncode"]==0 and root["stdout"].strip()=="0")
    if not ok:
        raise RuntimeError("CERTIFIED_PRIVILEGE_BRIDGE_REQUIRED")
    return d

def root_layout():
    src=run(["findmnt","-n","-o","SOURCE","/"],check=True)["stdout"].strip()
    fs=run(["findmnt","-n","-o","FSTYPE","/"],check=True)["stdout"].strip()
    start=int(pathlib.Path("/sys/class/block/nvme0n1p3/start").read_text().strip())
    size=int(pathlib.Path("/sys/class/block/nvme0n1p3/size").read_text().strip())
    return {"root_source":src,"root_fstype":fs,"p3_start_sector":start,"p3_size_sectors":size}

def installed_flatpak_apps():
    if not command("flatpak"):
        return []
    r=run(["flatpak","--user","list","--app","--columns=application"],timeout=60)
    return sorted(x.strip() for x in r["stdout"].splitlines() if x.strip()) if r["returncode"]==0 else []

def flatpak_commit(app):
    r=run(["flatpak","--user","info","--show-commit",app],timeout=60)
    return r["stdout"].strip() if r["returncode"]==0 else None

def checkpoint():
    p=D/"ROLLBACK_CHECKPOINT.json"
    if p.is_file():
        return read_json(p,{}) or {}
    archs=run(["dpkg","--print-foreign-architectures"],timeout=30)["stdout"].split()
    packages=["wine","wine64","wine32:i386","flatpak","steam-launcher","lutris","waydroid","curl","ca-certificates",
              "libc6:i386","libstdc++6:i386","libgcc-s1:i386","libgl1-mesa-dri:i386","podman"]
    cp={
        "schema":"LOUKSNA_R4_PART6_ROLLBACK_CHECKPOINT/1.0",
        "created_at_utc":utc(),
        "foreign_architectures":archs,
        "packages":{x:pkg_version(x) for x in packages},
        "flatpak_apps":installed_flatpak_apps(),
        "paths":{
            "sources":SOURCES.exists(),
            "components":COMPONENTS.exists(),
            "prism_link":(BIN/"prismlauncher").exists() or (BIN/"prismlauncher").is_symlink(),
            "waydroid_data":pathlib.Path("/var/lib/waydroid").exists(),
            "waydroid_source_list":pathlib.Path("/etc/apt/sources.list.d/waydroid.list").exists(),
            "waydroid_keyring":pathlib.Path("/usr/share/keyrings/waydroid.gpg").exists(),
        },
        "layout":root_layout(),
        "master_status_sha256":sha(STATE/"MASTER_STATUS.json") if (STATE/"MASTER_STATUS.json").is_file() else None,
    }
    atomic_json(p,cp)
    return cp

def write_rollback(cp):
    p=D/"ROLLBACK.sh"
    lines=[
        "#!/usr/bin/env bash",
        "set -Eeuo pipefail",
        "# PART_6 rollback: remove only artifacts introduced after the recorded checkpoint.",
        "# User-created game/application data is intentionally preserved.",
    ]
    preapps=set(cp.get("flatpak_apps",[]))
    if BOTTLES_APP not in preapps:
        lines.append("flatpak --user uninstall -y com.usebottles.bottles || true")
    for pkg in ["podman","waydroid","lutris","steam-launcher","wine32:i386","wine64","wine","flatpak"]:
        if not cp.get("packages",{}).get(pkg):
            lines.append("sudo -n /usr/bin/apt-get remove -y "+pkg+" || true")
    if "i386" not in cp.get("foreign_architectures",[]):
        lines.append("sudo -n /usr/bin/dpkg --remove-architecture i386 || true")
    if not cp.get("paths",{}).get("prism_link"):
        lines.append("rm -f "+str(BIN/"prismlauncher"))
    # These exact governed Proton paths were absent in the certified PART6 discovery.
    lines.append("rm -rf "+str(COMPONENTS/"Proton-11.0"))
    lines.append("rm -rf "+str(COMPONENTS/"Proton-source-11.0-2"))
    if not cp.get("paths",{}).get("components"):
        lines.append("rm -rf "+str(COMPONENTS))
    if not cp.get("paths",{}).get("waydroid_source_list"):
        lines.append("sudo -n rm -f /etc/apt/sources.list.d/waydroid.list || true")
    if not cp.get("paths",{}).get("waydroid_keyring"):
        lines.append("sudo -n rm -f /usr/share/keyrings/waydroid.gpg || true")
    lines += [
        "# /var/lib/waydroid is deliberately preserved even when newly initialized.",
        "# It may contain user data and requires explicit recovery authorization before deletion.",
        "sudo -n /usr/bin/apt-get update || true",
    ]
    p.write_text("\n".join(lines)+"\n",encoding="utf-8")
    p.chmod(0o700)
    return p

def publish_candidate(candidate_path):
    marker=D/"CANDIDATE_PUBLISHED.json"
    prior=read_json(marker,{}) or {}
    digest=sha(candidate_path)
    if prior.get("candidate_sha256")==digest and prior.get("commit_sha"):
        return prior
    c=json.loads(candidate_path.read_text(encoding="utf-8"))
    rel=c["repo_candidate_path"]
    raw=candidate_path.read_bytes()
    payload=base64.b64encode(raw).decode()
    get=run(["gh","api",f"repos/{REPO}/contents/{rel}?ref={urllib.parse.quote(BRANCH,safe='')}","--jq",".sha"],timeout=60)
    if get["returncode"]==0 and get["stdout"].strip():
        rec={"status":"PUBLISHED_EXISTING","candidate_sha256":digest,"repo_candidate_path":rel,
             "commit_sha":"EXISTING_CONTENT:"+get["stdout"].strip(),"published_at_utc":utc()}
        atomic_json(marker,rec); return rec
    msg="evidence(PART6): hardened actual-state candidate"
    r=run(["gh","api","--method","PUT",f"repos/{REPO}/contents/{rel}",
           "-f",f"message={msg}","-f",f"content={payload}","-f",f"branch={BRANCH}"],timeout=120,check=True)
    info=json.loads(r["stdout"])
    rec={"status":"PUBLISHED","candidate_sha256":digest,"repo_candidate_path":rel,
         "commit_sha":info["commit"]["sha"],"published_at_utc":utc()}
    atomic_json(marker,rec)
    return rec

def safe_test(argv,timeout=120,env=None):
    try:
        return run(argv,timeout=timeout,env=env)
    except Exception as e:
        return {"argv":[str(x) for x in argv],"returncode":999,"stdout":"","stderr":type(e).__name__+":"+str(e)}

def run_logged(argv,log_path,timeout,cwd=None,env=None):
    log_path=pathlib.Path(log_path); log_path.parent.mkdir(parents=True,exist_ok=True)
    started=utc()
    with log_path.open("w",encoding="utf-8",errors="replace") as f:
        p=subprocess.run(argv,text=True,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,cwd=cwd,env=env)
    raw=log_path.read_bytes()
    tail=raw[-12000:].decode("utf-8","replace")
    rec={
        "argv":[str(x) for x in argv],
        "returncode":p.returncode,
        "stdout_tail":tail,
        "stderr":"",
        "log_path":str(log_path),
        "log_sha256":sha(log_path),
        "log_bytes":log_path.stat().st_size,
        "started_at_utc":started,
        "ended_at_utc":utc(),
    }
    if p.returncode:
        raise RuntimeError("COMMAND_FAILED_LOGGED:"+json.dumps(rec,ensure_ascii=False))
    return rec

def build_proton_from_official_source(actions):
    if not command("podman"):
        actions.append(apt_install(["podman"],timeout=2400))
    pinfo=run(["podman","info","--format","json"],timeout=180)
    if pinfo["returncode"]!=0:
        raise RuntimeError("PODMAN_ROOTLESS_UNAVAILABLE:"+pinfo.get("stderr","")[-4000:])

    src=COMPONENTS/"Proton-source-11.0-2"
    if src.exists() and not (src/".git").is_dir():
        quarantine=src.with_name(src.name+".incomplete-"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
        src.rename(quarantine)
        actions.append({"operation":"QUARANTINE_INCOMPLETE_PROTON_SOURCE","from":str(src),"to":str(quarantine)})

    if not (src/".git").is_dir():
        actions.append(run([
            "git","clone","--branch",PROTON_RELEASE,"--depth","1",
            PROTON_REPO_URL,str(src)
        ],timeout=3600,check=True))
    else:
        actions.append(run(["git","-C",str(src),"fetch","--depth","1","origin","tag",PROTON_RELEASE],timeout=1800,check=False))

    actions.append(run(["git","-C",str(src),"checkout","--detach",PROTON_COMMIT],timeout=180,check=True))
    head=run(["git","-C",str(src),"rev-parse","HEAD"],timeout=30,check=True)["stdout"].strip()
    if head!=PROTON_COMMIT:
        raise RuntimeError("PROTON_SOURCE_COMMIT_MISMATCH:"+head)

    sub=run(["git","-C",str(src),"submodule","update","--init","--recursive","--depth","1"],timeout=7200)
    actions.append(sub)
    if sub["returncode"]!=0:
        actions.append(run(["git","-C",str(src),"submodule","update","--init","--recursive"],timeout=7200,check=True))

    substatus=run(["git","-C",str(src),"submodule","status","--recursive"],timeout=300,check=True)
    substatus_path=D/"PROTON_SUBMODULE_STATUS.txt"
    substatus_path.write_text(substatus["stdout"],encoding="utf-8")

    redist=src/"build"/PROTON_BUILD_NAME
    runtime_wine=redist/"files/bin/wine64"
    launcher=redist/"proton"
    if not launcher.is_file() or not runtime_wine.is_file():
        env=dict(os.environ)
        env["MAKEFLAGS"]="-j2"
        build_log=D/"PROTON_BUILD.log"
        actions.append(run_logged(
            ["make",f"build_name={PROTON_BUILD_NAME}","enable_ccache=0","redist"],
            build_log,timeout=14400,cwd=str(src),env=env
        ))
    if not launcher.is_file():
        raise RuntimeError("PROTON_SOURCE_BUILD_LAUNCHER_MISSING:"+str(launcher))
    if not runtime_wine.is_file() and not (redist/"files/bin/wine").is_file():
        raise RuntimeError("PROTON_SOURCE_BUILD_WINE_MISSING:"+str(redist))

    meta={
        "source":"VALVE_OFFICIAL_SOURCE_BUILD",
        "release_tag":PROTON_RELEASE,
        "source_commit":head,
        "source_repository":PROTON_REPO_URL,
        "submodule_status_sha256":sha(substatus_path),
        "build_name":PROTON_BUILD_NAME,
        "build_engine":"podman-rootless",
        "build_jobs":2,
        "steam_app_id":PROTON_APP_ID,
        "steamcmd_no_subscription_fallback":True,
    }
    return redist,meta

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mission-id",required=True)
    args=ap.parse_args()
    D.mkdir(parents=True,exist_ok=True); SOURCES.mkdir(parents=True,exist_ok=True); COMPONENTS.mkdir(parents=True,exist_ok=True); BIN.mkdir(parents=True,exist_ok=True)

    result=D/"RESULT.json"
    if result.is_file() and (read_json(result,{}) or {}).get("status")=="PASS":
        print("PART6_RESULT_ALREADY_PASS")
        return 0

    ms=read_json(STATE/"MASTER_STATUS.json",{}) or {}
    if ms.get("current_part")!="PART_6":
        raise RuntimeError("PART6_NOT_CURRENT:"+str(ms.get("current_part")))
    if not (STATE/"certificates/PART_5.json").is_file():
        raise RuntimeError("PART5_CERTIFICATE_MISSING")
    if os.uname().nodename!="LOUKSNA" or os.getuid()!=1000:
        raise RuntimeError("HOST_OR_UID_MISMATCH")

    candidate=D/"FULL_CANDIDATE_V2.json"
    if candidate.is_file() and (read_json(candidate,{}) or {}).get("status")=="PASS":
        rec=publish_candidate(candidate)
        print(json.dumps(rec,indent=2,sort_keys=True))
        return 0

    last_fail=read_json(D/"LAST_FAILURE.json",{}) or {}
    if last_fail.get("worker_version")=="2.2" and last_fail.get("recorded_epoch"):
        if time.time()-float(last_fail["recorded_epoch"]) < 600:
            print("PART6_BACKOFF_ACTIVE")
            return 23

    privilege=require_privilege()
    cp=checkpoint()
    rollback=write_rollback(cp)
    actions=[]

    try:
        before=root_layout()
        expected={"root_source":"/dev/nvme0n1p3","root_fstype":"ext4","p3_start_sector":567296,"p3_size_sectors":999647887}
        if before!=expected:
            raise RuntimeError("ROOT_LAYOUT_DRIFT:"+json.dumps(before,sort_keys=True))

        archs=run(["dpkg","--print-foreign-architectures"],timeout=30)["stdout"].split()
        if "i386" not in archs:
            actions.append(run(["sudo","-n","/usr/bin/dpkg","--add-architecture","i386"],timeout=60,check=True))
        env=dict(os.environ); env["DEBIAN_FRONTEND"]="noninteractive"
        actions.append(run(["sudo","-n","/usr/bin/apt-get","update"],timeout=900,check=True,env=env))
        base_pkgs=["wine","wine64","wine32:i386","flatpak","curl","ca-certificates","libc6:i386","libstdc++6:i386","libgcc-s1:i386","libgl1-mesa-dri:i386"]
        actions.append(apt_install(base_pkgs,timeout=2400))

        steam_deb=SOURCES/"steam_latest.deb"
        if not steam_deb.is_file() or sha(steam_deb)!=STEAM_DEB_SHA256:
            download(STEAM_URL,steam_deb)
        if sha(steam_deb)!=STEAM_DEB_SHA256:
            raise RuntimeError("STEAM_DEB_SHA256_MISMATCH")
        steam_meta=run(["dpkg-deb","-f",str(steam_deb),"Package","Version"],timeout=30,check=True)
        if not pkg_version("steam-launcher"):
            actions.append(apt_install([steam_deb],timeout=2400))

        lutris_deb=SOURCES/"lutris_0.5.22_all.deb"
        if not lutris_deb.is_file() or sha(lutris_deb)!=LUTRIS_SHA256:
            download(LUTRIS_URL,lutris_deb)
        if sha(lutris_deb)!=LUTRIS_SHA256:
            raise RuntimeError("LUTRIS_SHA256_MISMATCH")
        if pkg_version("lutris")!="0.5.22":
            actions.append(apt_install([lutris_deb],timeout=1800))

        if BOTTLES_APP not in installed_flatpak_apps():
            actions.append(run(["flatpak","--user","remote-add","--if-not-exists","flathub",FLATHUB_REPO],timeout=180,check=True))
            actions.append(run(["flatpak","--user","install","-y","flathub",BOTTLES_APP],timeout=3600,check=True))

        prism=COMPONENTS/"PrismLauncher.AppImage"
        if not prism.is_file() or sha(prism)!=PRISM_SHA256:
            download(PRISM_URL,prism,timeout=1200)
        if sha(prism)!=PRISM_SHA256:
            raise RuntimeError("PRISM_SHA256_MISMATCH")
        prism.chmod(0o755)
        link=BIN/"prismlauncher"
        if not link.exists() and not link.is_symlink():
            link.symlink_to(prism)

        way_script=SOURCES/"waydroid-repo-bootstrap.sh"
        if not way_script.is_file() or sha(way_script)!=WAYDROID_SCRIPT_SHA256:
            download(WAYDROID_REPO_URL,way_script,timeout=180)
        if sha(way_script)!=WAYDROID_SCRIPT_SHA256:
            raise RuntimeError("WAYDROID_BOOTSTRAP_SHA256_MISMATCH")
        way_script.chmod(0o700)
        if not pkg_version("waydroid"):
            actions.append(run(["sudo","-n","bash",str(way_script),"trixie"],timeout=300,check=True))
            actions.append(run(["sudo","-n","/usr/bin/apt-get","update"],timeout=900,check=True,env=env))
            policy=run(["apt-cache","policy","waydroid"],timeout=60,check=True)
            if not any(x in policy["stdout"] for x in ("Candidate:","Candidato:")):
                raise RuntimeError("WAYDROID_NO_APT_CANDIDATE")
            actions.append(apt_install(["waydroid"],timeout=1800))
        way_version=pkg_version("waydroid")
        if not way_version or not way_version.startswith("1.6."):
            raise RuntimeError("WAYDROID_UNEXPECTED_VERSION:"+str(way_version))
        if not pathlib.Path("/var/lib/waydroid/waydroid.cfg").is_file():
            actions.append(run(["sudo","-n","/usr/bin/waydroid","init","-f"],timeout=3600,check=True))
        actions.append(run(["sudo","-n","/usr/bin/systemctl","enable","--now","waydroid-container.service"],timeout=180,check=False))

        steamcmd_tar=SOURCES/"steamcmd_linux.tar.gz"
        if not steamcmd_tar.is_file() or sha(steamcmd_tar)!=STEAMCMD_SHA256:
            download(STEAMCMD_URL,steamcmd_tar,timeout=900)
        if sha(steamcmd_tar)!=STEAMCMD_SHA256:
            raise RuntimeError("STEAMCMD_SHA256_MISMATCH")
        steamcmd_dir=COMPONENTS/"steamcmd"
        steamcmd_dir.mkdir(parents=True,exist_ok=True)
        steamcmd=steamcmd_dir/"steamcmd.sh"
        if not steamcmd.is_file():
            with tarfile.open(steamcmd_tar,"r:gz") as tf:
                tf.extractall(steamcmd_dir)
        proton_dir=COMPONENTS/"Proton-11.0"
        proton_dir.mkdir(parents=True,exist_ok=True)
        proton_launcher=proton_dir/"proton"
        proton_wine=proton_dir/"files/bin/wine64"
        proton_provenance={
            "source":"VALVE_STEAM_DEPOT",
            "steam_app_id":PROTON_APP_ID,
            "release_tag":PROTON_RELEASE,
            "release_reference":"https://github.com/ValveSoftware/Proton/releases/tag/"+PROTON_RELEASE,
            "steamcmd_url":STEAMCMD_URL,
            "steamcmd_archive_sha256":sha(steamcmd_tar),
        }
        if not proton_launcher.is_file() or not proton_wine.is_file():
            known_no_subscription="No subscription" in json.dumps(last_fail,ensure_ascii=False)
            steam_attempt=None
            if not known_no_subscription:
                steam_attempt=run([str(steamcmd),
                    "+@sSteamCmdForcePlatformType","linux",
                    "+force_install_dir",str(proton_dir),
                    "+login","anonymous",
                    "+app_update",str(PROTON_APP_ID),"validate",
                    "+quit"],timeout=3600)
                actions.append(steam_attempt)
            if known_no_subscription or (steam_attempt and steam_attempt["returncode"]!=0):
                combined="" if steam_attempt is None else steam_attempt.get("stdout","")+"\n"+steam_attempt.get("stderr","")
                if known_no_subscription or "No subscription" in combined:
                    proton_dir,proton_provenance=build_proton_from_official_source(actions)
                    proton_launcher=proton_dir/"proton"
                    proton_wine=proton_dir/"files/bin/wine64"
                else:
                    raise RuntimeError("PROTON_STEAMCMD_FAILED:"+json.dumps(steam_attempt,ensure_ascii=False))

        tests={}
        tests["wine"]=safe_test(["wine","--version"],timeout=60)
        steam_exec=command("steam")
        steam_integrity=run(["dpkg","-V","steam-launcher"],timeout=60) if pkg_version("steam-launcher") else {"returncode":127,"stdout":"","stderr":"steam-launcher not installed"}
        tests["steam"]={"argv":["dpkg","-V","steam-launcher"],"returncode":steam_integrity["returncode"],
                        "stdout":steam_integrity["stdout"],"stderr":steam_integrity["stderr"],"executable":steam_exec}
        if proton_wine.is_file():
            tests["proton"]=safe_test([str(proton_wine),"--version"],timeout=90)
        elif (proton_dir/"files/bin/wine").is_file():
            proton_wine=proton_dir/"files/bin/wine"
            tests["proton"]=safe_test([str(proton_wine),"--version"],timeout=90)
        else:
            tests["proton"]={"returncode":127,"stdout":"","stderr":"PROTON_WINE_MISSING"}
        tests["bottles"]=safe_test(["flatpak","run","--command=bottles-cli",BOTTLES_APP,"--version"],timeout=180)
        tests["lutris"]=safe_test(["lutris","--version"],timeout=90)
        penv=dict(os.environ); penv["APPIMAGE_EXTRACT_AND_RUN"]="1"; penv["QT_QPA_PLATFORM"]="offscreen"
        tests["prism"]=safe_test([str(prism),"--version"],timeout=180,env=penv)
        tests["waydroid"]=safe_test(["waydroid","--version"],timeout=90)
        way_service=run(["systemctl","is-active","waydroid-container.service"],timeout=30)
        tests["waydroid"]["container_service"]=way_service

        wine_ver=pkg_version("wine")
        steam_ver=pkg_version("steam-launcher")
        lutris_ver=pkg_version("lutris")
        bottles_commit=flatpak_commit(BOTTLES_APP)
        prism_ver="11.1.1"
        proton_version=(tests["proton"].get("stdout") or tests["proton"].get("stderr") or "").strip().splitlines()[:1]
        proton_version=proton_version[0] if proton_version else PROTON_RELEASE

        functional={
            "wine":tests["wine"].get("returncode")==0 and bool(command("wine")),
            "steam":tests["steam"].get("returncode")==0 and bool(steam_exec),
            "proton":tests["proton"].get("returncode")==0 and proton_launcher.is_file() and proton_wine.is_file(),
            "bottles":tests["bottles"].get("returncode")==0 and bool(bottles_commit),
            "lutris":tests["lutris"].get("returncode")==0 and bool(command("lutris")),
            "prism":tests["prism"].get("returncode")==0 and prism.is_file(),
            "waydroid":tests["waydroid"].get("returncode")==0 and way_service["stdout"].strip()=="active",
        }

        components={
            "wine":{
                "status":"PASS" if functional["wine"] else "HOLD","functional_test_pass":functional["wine"],"version":wine_ver,
                "test":tests["wine"],"provenance":{"source":"DEBIAN_TRIXIE_OFFICIAL_APT","package":"wine","version":wine_ver,
                "repository":"http://deb.debian.org/debian trixie main"}},
            "steam":{
                "status":"PASS" if functional["steam"] else "HOLD","functional_test_pass":functional["steam"],"version":steam_ver,
                "executable":steam_exec,"artifact_path":str(steam_deb),"artifact_sha256":sha(steam_deb),"test":tests["steam"],
                "provenance":{"source":"VALVE_OFFICIAL_STEAM_REPOSITORY","url":STEAM_URL,"artifact_sha256":sha(steam_deb),
                "package":"steam-launcher","version":steam_ver,"dpkg_metadata":steam_meta["stdout"].strip()}},
            "proton":{
                "status":"PASS" if functional["proton"] else "HOLD","functional_test_pass":functional["proton"],"version":proton_version,
                "runtime_path":str(proton_dir),"runtime_wine":str(proton_wine),"test":tests["proton"],
                "provenance":proton_provenance},
            "bottles":{
                "status":"PASS" if functional["bottles"] else "HOLD","functional_test_pass":functional["bottles"],
                "version":tests["bottles"].get("stdout","").strip() or bottles_commit,"flatpak_commit":bottles_commit,"test":tests["bottles"],
                "provenance":{"source":"BOTTLES_SUPPORTED_FLATPAK","remote":"flathub","app_id":BOTTLES_APP,
                "flatpak_commit":bottles_commit,"repo":FLATHUB_REPO}},
            "lutris":{
                "status":"PASS" if functional["lutris"] else "HOLD","functional_test_pass":functional["lutris"],"version":lutris_ver,
                "artifact_path":str(lutris_deb),"artifact_sha256":sha(lutris_deb),"test":tests["lutris"],
                "provenance":{"source":"LUTRIS_OFFICIAL_GITHUB_RELEASE","release_tag":"v0.5.22","url":LUTRIS_URL,
                "artifact_sha256":sha(lutris_deb)}},
            "prism":{
                "status":"PASS" if functional["prism"] else "HOLD","functional_test_pass":functional["prism"],"version":prism_ver,
                "artifact_path":str(prism),"artifact_sha256":sha(prism),"test":tests["prism"],
                "provenance":{"source":"PRISMLAUNCHER_OFFICIAL_GITHUB_RELEASE","release_tag":"11.1.1","url":PRISM_URL,
                "artifact_sha256":sha(prism)}},
            "waydroid":{
                "status":"PASS" if functional["waydroid"] else "HOLD","functional_test_pass":functional["waydroid"],"version":way_version,
                "test":tests["waydroid"],"provenance":{"source":"WAYDROID_OFFICIAL_APT_REPOSITORY","url":WAYDROID_REPO_URL,
                "repo_bootstrap_sha256":sha(way_script),"package":"waydroid","version":way_version}},
        }

        after=root_layout()
        layout_ok=(after==before)
        checkpoint_path=D/"ROLLBACK_CHECKPOINT.json"
        checks={
            "all_components_functional":all(functional.values()),
            "rollback_checkpoint":checkpoint_path.is_file(),
            "rollback_script":rollback.is_file(),
            "root_layout_preserved":layout_ok,
            "part5_certificate_present":(STATE/"certificates/PART_5.json").is_file(),
            "privilege_chain_active":privilege.get("status")=="ACTIVE",
            "component_set_exact":set(components)=={"wine","steam","proton","bottles","lutris","prism","waydroid"},
        }
        status="PASS" if all(checks.values()) else "HOLD"
        stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rel=f"evidence/r4-master-part6/{stamp}-{args.mission_id}/FULL_CANDIDATE_V2.json"
        candidate_obj={
            "schema":"LOUKSNA_R4_PART6_FULL_CANDIDATE_V2/1.0",
            "status":status,
            "host":"LOUKSNA",
            "mission_id":args.mission_id,
            "repo_candidate_path":rel,
            "components":components,
            "checks":checks,
            "actions":actions,
            "rollback_ready":True,
            "rollback_checkpoint_path":str(checkpoint_path),
            "rollback_checkpoint_sha256":sha(checkpoint_path),
            "rollback_script_path":str(rollback),
            "rollback_script_sha256":sha(rollback),
            "root_source":after["root_source"],
            "root_fstype":after["root_fstype"],
            "p3_start_sector":after["p3_start_sector"],
            "p3_size_sectors":after["p3_size_sectors"],
            "disk_partition_mutation_performed":False,
            "filesystem_format_or_resize_performed":False,
            "unrelated_user_data_deleted":False,
            "certification_propagated":False,
            "worker_version":"2.2",
            "recorded_at_utc":utc(),
        }
        atomic_json(candidate,candidate_obj)
        if status!="PASS":
            atomic_json(D/"LAST_FAILURE.json",{"schema":"LOUKSNA_R4_PART6_WORKER_FAILURE/1.0","worker_version":"2.2",
                "recorded_epoch":time.time(),"recorded_at_utc":utc(),"reason":"FUNCTIONAL_OR_INVARIANT_GATE_FAILED",
                "candidate_sha256":sha(candidate),"checks":checks,"functional":functional})
            print(json.dumps(candidate_obj,indent=2,sort_keys=True))
            return 23
        if (D/"LAST_FAILURE.json").exists():
            (D/"LAST_FAILURE.json").unlink()
        pub=publish_candidate(candidate)
        print(json.dumps({"status":"PASS","candidate_sha256":sha(candidate),"published":pub},indent=2,sort_keys=True))
        return 0

    except Exception as e:
        rec={"schema":"LOUKSNA_R4_PART6_WORKER_FAILURE/1.0","worker_version":"2.2","recorded_epoch":time.time(),
             "recorded_at_utc":utc(),"error":type(e).__name__+":"+str(e),"actions_tail":actions[-5:],
             "rollback_checkpoint_path":str(D/"ROLLBACK_CHECKPOINT.json"),"rollback_script_path":str(rollback)}
        atomic_json(D/"LAST_FAILURE.json",rec)
        print(json.dumps(rec,indent=2,sort_keys=True))
        return 24

if __name__=="__main__":
    raise SystemExit(main())
