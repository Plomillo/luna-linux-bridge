"""Oracle for OS cases 345-384. Does not import worker or probes."""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path


def expect(n: int, inp: dict) -> dict:
    return TABLE[n](inp)


def blocked(inp):
    return {"blocked": True, "probe": inp["probe"]}


def e345(inp):
    if shutil.which("strace") or shutil.which("perf"):
        return {"blocked": False, "probe": inp["probe"]}
    return blocked(inp)


def e346(_inp):
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    alive = proc.poll() is None
    proc.kill()
    proc.wait(timeout=5)
    return {"alive_before": alive, "reaped": proc.poll() is not None}


def e347(inp):
    path = Path(str(inp["path"]) + ".oracle")
    ready = path.with_suffix(".ready")
    code = "import signal,sys,time\np,r=sys.argv[1],sys.argv[2]\n\ndef h(*_a):\n open(p,'w').write('term')\n raise SystemExit(0)\nsignal.signal(signal.SIGTERM,h)\nopen(r,'w').write('up')\ntime.sleep(30)\n"
    proc = subprocess.Popen([sys.executable, "-c", code, str(path), str(ready)])
    import time
    for _ in range(50):
        if ready.exists() or proc.poll() is not None:
            break
        time.sleep(0.05)
    if ready.exists():
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
    else:
        proc.kill()
        proc.wait(timeout=5)
    return {"handled": path.exists() and path.read_text() == "term", "signal": int(inp["signal"])}


def e348(inp):
    seen = []
    threads = [threading.Thread(target=seen.append, args=(i,)) for i in range(1, inp["n"] + 1)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    return {"started": inp["n"], "joined": all(not thread.is_alive() for thread in threads), "saw": sorted(seen)}


def e349(inp):
    if inp.get("probe") == "user-namespace":
        proc = subprocess.run(["unshare", "--user", "--map-root-user", "true"], capture_output=True, text=True)
        if proc.returncode != 0:
            return blocked(inp)
        return {"blocked": False, "probe": inp["probe"]}
    proc = subprocess.run(["unshare", "--user", "--map-root-user", "true"], capture_output=True, text=True)
    return {"exit_zero": proc.returncode == 0}


def e350(inp):
    return blocked(inp)


def e351(_inp):
    eff = prm = ""
    text = Path("/proc/self/status").read_text().splitlines()
    for line in text:
        if line[:7] == "CapEff:":
            eff = line.split(":", 1)[1].strip()
        elif line[:7] == "CapPrm:":
            prm = line.split(":", 1)[1].strip()
    return {"eff": eff, "prm": prm, "both_present": bool(eff and prm)}


def e352(_inp):
    return {"euid": os.geteuid(), "uid": os.getuid(), "groups": len(os.getgroups())}


def e353(inp):
    if shutil.which("getfacl") and shutil.which("setfacl"):
        return {"blocked": False, "probe": inp["probe"]}
    return blocked(inp)


def e354(_inp):
    before = len(os.listdir("/proc/self/fd"))
    handle = open("/tmp/mra-oracle-fd", "w")
    mid = len(os.listdir("/proc/self/fd"))
    handle.close()
    after = len(os.listdir("/proc/self/fd"))
    return {"opened": mid > before, "closed": after < mid}


def e355(_inp):
    fstype = ""
    for raw in Path("/proc/mounts").read_text().splitlines():
        bits = raw.split(" ")
        if len(bits) > 2 and bits[1] == "/":
            fstype = bits[2]
            break
    return {"fstype": fstype, "has_root": fstype != ""}


def e356(inp):
    return blocked(inp)


def e357(inp):
    mode = Path(inp["path"]).stat().st_mode & 0o777
    return {"mode": mode, "not_world": (mode & 0o002) == 0}


def e358(inp):
    link = Path(inp["link"])
    resolved = (link.parent / os.readlink(link)).read_text()
    cur = Path(inp["a"])
    hops = 0
    cycle = False
    seen = []
    while hops < 6:
        if str(cur) in seen:
            cycle = True
            break
        seen.append(str(cur))
        if not cur.is_symlink():
            break
        cur = (cur.parent / os.readlink(cur)).resolve() if False else cur.parent / os.readlink(cur)
        hops += 1
    return {"resolved": resolved, "cycle": cycle}


def e359(inp):
    a = Path(inp["a"])
    b = Path(inp["b"])
    return {"same_inode": a.samefile(b), "names": 2}


def _own_tmpfs(options: str, name: str):
    mnt = Path("/tmp") / name
    if mnt.exists():
        subprocess.run(["umount", str(mnt)], capture_output=True)
    mnt.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(["mount", "-t", "tmpfs", "-o", options, "tmpfs", str(mnt)], capture_output=True, text=True)
    return proc.returncode == 0, mnt


def e360(inp):
    if inp.get("probe"):
        return blocked(inp)
    ok, mnt = _own_tmpfs("size=64k", "mra-oracle-enospc")
    if not ok:
        return {"enospc": False}
    try:
        enospc = False
        try:
            for i in range(64):
                (mnt / f"o{i}").write_bytes(b"y" * 4096)
        except OSError as exc:
            enospc = exc.errno == 28
        return {"enospc": enospc}
    finally:
        subprocess.run(["umount", str(mnt)], capture_output=True)


def e361(inp):
    if inp.get("probe"):
        return blocked(inp)
    ok, mnt = _own_tmpfs("size=1m,nr_inodes=8", "mra-oracle-inodes")
    if not ok:
        return {"inode_fail": False, "bytes_left": False}
    try:
        failed = False
        try:
            for i in range(32):
                (mnt / f"p{i}").write_text("q")
        except OSError:
            failed = True
        return {"inode_fail": failed, "bytes_left": shutil.disk_usage(mnt).free > 0}
    finally:
        subprocess.run(["umount", str(mnt)], capture_output=True)


def e362(inp):
    return blocked(inp)


def e363(_inp):
    lines = Path("/proc/swaps").read_text(encoding="utf-8", errors="replace").splitlines()
    rows = [line for line in lines[1:] if line.strip()]
    return {"rows": len(rows), "header": lines[0].startswith("Filename") if lines else False}


def e364(inp):
    return blocked(inp)


def _status_field(package: str, field: str) -> str:
    text = Path("/var/lib/dpkg/status").read_text(encoding="utf-8", errors="replace")
    blocks = text.split("\n\n")
    for block in blocks:
        if f"Package: {package}\n" in block or block.startswith(f"Package: {package}\n"):
            for line in block.splitlines():
                if line.startswith(field + ": "):
                    return line.split(": ", 1)[1]
    return ""


def e365(inp):
    version = _status_field(inp["package"], "Version")
    arch = _status_field(inp["package"], "Architecture")
    return {"name": inp["package"] if version else "", "has_version": bool(version), "arch": arch}


def e366(inp):
    depends = _status_field(inp["package"], "Depends")
    return {"depends_nonempty": bool(depends), "force_depends": False}


def e367(inp):
    return blocked(inp)


def e368(inp):
    proc = subprocess.run(["apt-get", "update"], capture_output=True, text=True, timeout=180)
    root = Path("/var/lib/apt/lists")
    lists = sorted(p.name for p in root.iterdir() if p.is_file() and p.name.endswith("_Packages")) if root.is_dir() else []
    ok = proc.returncode == 0 and len(lists) > 0
    return {
        "blocked": not ok,
        "probe": "apt-indexes",
        "update_rc": proc.returncode,
        "lists": len(lists),
        "used_install": False,
        "force_depends": False,
    }


def e377(_inp):
    portal = Path("/usr/bin/xdg-desktop-portal").is_file() or Path("/usr/libexec/xdg-desktop-portal").is_file()
    kde_bin = Path("/usr/bin/xdg-desktop-portal-kde").is_file() or Path("/usr/libexec/xdg-desktop-portal-kde").is_file()
    if not kde_bin:
        lib = Path("/usr/lib")
        kde_bin = lib.is_dir() and any(lib.glob("*/libexec/xdg-desktop-portal-kde"))
    bins = portal and kde_bin
    portal_running = kde = False
    for pid in Path("/proc").iterdir():
        if not pid.name.isdigit():
            continue
        try:
            cmd = (pid / "cmdline").read_bytes().replace(b"\x00", b" ").decode(errors="replace")
        except OSError:
            continue
        if "xdg-desktop-portal-kde" in cmd:
            kde = True
        elif "xdg-desktop-portal" in cmd:
            portal_running = True
    ok = bins and portal_running and kde
    return {"blocked": not ok, "probe": "xdg-portals", "running": ok}


def e378(inp):
    stamp = inp.get("stamp")
    nonce = inp.get("nonce")
    opened = bool(stamp and nonce and Path(stamp).is_file() and Path(stamp).read_text().strip() == nonce)
    if not opened:
        return {"blocked": True, "probe": "desktop-integration", "opened": False}
    return {"blocked": False, "probe": "desktop-integration", "opened": True}


def e369(inp):
    one = subprocess.run([inp["script"], inp["stamp"], inp["keep"]], capture_output=True, text=True)
    two = subprocess.run([inp["script"], inp["stamp"], inp["keep"]], capture_output=True, text=True)
    return {"first": one.returncode, "second": two.returncode, "kept": Path(inp["keep"]).read_text() == "keep"}


def e370(inp):
    if inp.get("probe") == "systemd" and shutil.which("systemctl"):
        proc = subprocess.run(["systemctl", "is-system-running"], capture_output=True, text=True)
        state = (proc.stdout or "").strip()
        if proc.returncode == 0 and state == "running":
            return {"running": True}
    return blocked(inp)


def e371(inp):
    proc = subprocess.run(["journalctl", "-n", "1", "--no-pager"], capture_output=True, text=True)
    if proc.returncode != 0 or inp.get("probe") != "journald":
        if inp.get("probe") == "journald" and proc.returncode != 0:
            return blocked(inp)
        if proc.returncode != 0:
            return blocked(inp)
    return {"readable": proc.returncode == 0}


def e372(_inp):
    tokens = [tok for tok in Path("/proc/cmdline").read_text().split() if tok]
    return {"observed": len(tokens) > 0, "token_count": len(tokens)}


def e373(inp):
    if shutil.which("lsinitramfs") or shutil.which("unmkinitramfs"):
        return {"blocked": False, "probe": inp.get("probe", "initramfs")}
    return blocked(inp)


def e374(inp):
    session = os.environ.get("XDG_SESSION_TYPE", "")
    if session != inp.get("session", ""):
        session = os.environ.get("XDG_SESSION_TYPE", "")
    return {"wayland": session == "wayland", "x11": session == "x11", "headless": session == "", "simulated": False}


def e375(inp):
    desktop = (os.environ.get("XDG_CURRENT_DESKTOP", "") + os.environ.get("DESKTOP_SESSION", "")).upper()
    real = "KDE" in desktop and (Path("/usr/bin/plasmashell").exists() or Path("/usr/bin/startplasma-wayland").exists())
    if real:
        return {"blocked": False, "probe": inp["probe"]}
    return blocked(inp)


def e376(inp):
    display = os.environ.get("WAYLAND_DISPLAY", "")
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    real = bool(display and runtime and Path(runtime, display).exists() and os.environ.get("XDG_SESSION_TYPE") == "wayland")
    if real:
        return {"blocked": False, "probe": inp["probe"]}
    return blocked(inp)


def e379(inp):
    if Path("/dev/snd").exists() or shutil.which("pactl"):
        return {"blocked": False, "probe": inp["probe"]}
    return blocked(inp)


def e380(inp):
    def read_ns(pid: str):
        try:
            os.readlink("/proc/%s/ns/pid" % pid)
            return 0
        except OSError as exc:
            return exc.errno or 1
    self_err = read_ns("self")
    init_err = read_ns("1")
    if inp.get("probe") == "pid-ns" or self_err or init_err:
        if self_err or init_err:
            return {"blocked": True, "probe": "pid-ns"}
    self_ns = os.readlink("/proc/self/ns/pid")
    init_ns = os.readlink("/proc/1/ns/pid")
    euid = os.geteuid()
    return {"same_pid_ns": self_ns == init_ns, "euid": euid, "weak_isolation": self_ns == init_ns and euid == 0}


def e381(inp):
    virt = ""
    if shutil.which("systemd-detect-virt"):
        proc = subprocess.run(["systemd-detect-virt"], capture_output=True, text=True)
        virt = (proc.stdout or "").strip()
    text = Path("/proc/cpuinfo").read_text(errors="replace")
    flag = "hypervisor" in text.split()
    mem = 0
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemTotal:"):
            mem = int(line.split()[1])
            break
    if inp.get("probe") == "vm" and not virt and not flag:
        return {"blocked": True, "probe": "vm"}
    if not virt and not flag:
        return {"blocked": True, "probe": inp.get("probe", "vm")}
    return {"virt": virt or "none", "hypervisor_flag": flag, "mem_total_kb": mem}


def e382(inp):
    return blocked(inp)


def e383(inp):
    version = ""
    for line in Path("/etc/os-release").read_text().splitlines():
        if line.startswith("VERSION_ID="):
            version = line.split("=", 1)[1].strip().strip('"')
    if version != "13":
        return blocked(inp)
    return {"blocked": False}


def e384(_inp):
    info = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            info[key] = value.strip().strip('"')
    return {"system": os.uname().sysname, "machine": os.uname().machine, "version_id": info.get("VERSION_ID", "")}


TABLE = {i: globals()[f"e{i}"] for i in range(345, 385)}
