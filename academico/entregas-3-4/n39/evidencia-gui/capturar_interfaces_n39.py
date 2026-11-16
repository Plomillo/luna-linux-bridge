#!/usr/bin/env python3
from __future__ import annotations
import os, subprocess, time, shutil
from pathlib import Path
import pyautogui

ROOT = Path(os.environ["GITHUB_WORKSPACE"])
BASE = ROOT / "academico/entregas-3-4/n39"
CSV = Path.home() / "Documents/n39/base_expandida_marginal_n39.csv"
OUT = BASE / "evidencia-gui"
OUT.mkdir(parents=True, exist_ok=True)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.8

def run_bg(args, log):
    f = open(log, "w")
    return subprocess.Popen(args, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)

def focus(term, timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        listing = subprocess.run(["wmctrl","-l"],capture_output=True,text=True).stdout
        match = next((line.split(None,3)[-1] for line in listing.splitlines() if term.lower() in line.lower()), None)
        if match:
            subprocess.run(["wmctrl","-a",match],check=False)
            time.sleep(3)
            subprocess.run(["wmctrl","-r",match,"-b","add,maximized_vert,maximized_horz"],check=False)
            time.sleep(3)
            return True
        time.sleep(2)
    return False

def save(name):
    # Capture the real X11 desktop with scrot (installed by the workflow).
    target = OUT / name
    subprocess.run(["scrot", str(target)], check=True)
    if not target.is_file() or target.stat().st_size < 10_000:
        raise RuntimeError(f"Screenshot missing or unexpectedly small: {target}")

# RStudio Desktop (Posit) running R; load the project script into the editor.
r_script = BASE / "R/interfaz_r_n39.R"
run_bg(["rstudio", "--no-restore", "--no-save", str(r_script)], OUT/"rstudio-launch.log")
if not focus("RStudio", 120):
    raise RuntimeError("RStudio GUI window did not appear")
pyautogui.hotkey("ctrl","2")
time.sleep(2)
cmd = f'source("{r_script.as_posix()}")'
pyautogui.write(cmd, interval=0.004)
pyautogui.press("enter")
time.sleep(18)
save("01_RStudio_R_n39.png")

# jamovi official Flatpak desktop app.
run_bg(["flatpak","run","org.jamovi.jamovi",str(CSV)], OUT/"jamovi-launch.log")
if not focus("jamovi", 120):
    raise RuntimeError("jamovi GUI window did not appear")
# The CSV was passed as the official application's launch argument.
time.sleep(8)
save("02_jamovi_n39.png")

# JASP official Flatpak desktop app.
run_bg(["flatpak","run","org.jaspstats.JASP",str(CSV)], OUT/"jasp-launch.log")
if not focus("JASP", 120):
    # Some builds use lower-case title or append a file name.
    if not focus("jasp", 30):
        raise RuntimeError("JASP GUI window did not appear")
time.sleep(8)
save("03_JASP_n39.png")

# Save deterministic app/version/process evidence.
manifest = OUT / "captura_aplicaciones.txt"
lines=[]
for cmd in (["R","--version"],["rstudio","--version"],["flatpak","run","org.jamovi.jamovi","--version"],["flatpak","run","org.jaspstats.JASP","--version"]):
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
        lines.append("$ "+" ".join(cmd)+"\n"+(p.stdout+p.stderr).strip()+"\n")
    except Exception as e:
        lines.append("$ "+" ".join(cmd)+"\n"+repr(e)+"\n")
manifest.write_text("\n".join(lines),encoding="utf-8")
