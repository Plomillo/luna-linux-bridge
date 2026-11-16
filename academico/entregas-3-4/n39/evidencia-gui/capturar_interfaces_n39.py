#!/usr/bin/env python3
from __future__ import annotations
import os, subprocess, time
from pathlib import Path
import pyautogui

ROOT = Path(os.environ["GITHUB_WORKSPACE"])
BASE = ROOT / "academico/entregas-3-4/n39"
RAW_CSV = Path.home() / "Documents/n39/base_expandida_marginal_n39.csv"
JAMOVI_RESULTS = BASE / "salidas/descriptivos_jamovi_jmv.csv"
JASP_RESULTS = BASE / "salidas/descriptivos_jasp.csv"
OUT = BASE / "evidencia-gui"
OUT.mkdir(parents=True, exist_ok=True)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.6

# Remove duplicate artifacts from previous non-overwriting screenshot attempts.
for old in OUT.glob("*_000.png"):
    old.unlink(missing_ok=True)

def run_bg(args, log):
    f = open(log, "w")
    return subprocess.Popen(args, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)

def window_list():
    p = subprocess.run(["wmctrl", "-lx"], capture_output=True, text=True, check=False)
    return p.stdout

def focus(needles, process, log_path, timeout=180):
    needles = [x.lower() for x in needles]
    end = time.time() + timeout
    last = ""
    while time.time() < end:
        last = window_list()
        for line in last.splitlines():
            fields = line.split(None, 4)
            if len(fields) < 4:
                continue
            if any(term in line.lower() for term in needles):
                wid = fields[0]
                subprocess.run(["wmctrl", "-i", "-a", wid], check=False)
                subprocess.run(["xdotool", "windowmap", wid], check=False)
                subprocess.run(["xdotool", "windowraise", wid], check=False)
                subprocess.run(["xdotool", "windowactivate", "--sync", wid], check=False)
                subprocess.run(["wmctrl", "-i", "-r", wid, "-b", "add,maximized_vert,maximized_horz"], check=False)
                time.sleep(4)
                OUT.joinpath("ventanas_"+log_path+".txt").write_text(last, encoding="utf-8")
                return wid
        if process.poll() is not None:
            time.sleep(2)
            continue
        time.sleep(2)
    details = [
        "NEEDLES="+repr(needles),
        "PROCESS_RETURN_CODE="+repr(process.poll()),
        "WINDOWS="+last,
        "PROCESS_LIST="+subprocess.run(["ps","-eo","pid,comm,args"],capture_output=True,text=True).stdout,
    ]
    OUT.joinpath("diagnostico_"+log_path+".txt").write_text("\n".join(details),encoding="utf-8")
    raise RuntimeError(f"Window not found for {needles}; see diagnostico_{log_path}.txt")

def save(name):
    target = OUT / name
    target.unlink(missing_ok=True)
    subprocess.run(["scrot", str(target)], check=True)
    if not target.is_file() or target.stat().st_size < 10_000:
        raise RuntimeError(f"Screenshot missing or unexpectedly small: {target}")

# 1) RStudio Desktop by Posit: explicitly run the open R script from its Source toolbar.
r_script = BASE / "R/interfaz_r_n39.R"
rproc = run_bg(["rstudio", "--no-restore", "--no-save", str(r_script)], OUT/"rstudio-launch.log")
rwid = focus(["rstudio"], rproc, "rstudio")
time.sleep(8)
# In the maximized 1600x1200 RStudio window, Source is on the script toolbar.
pyautogui.click(530, 115)
time.sleep(25)
save("01_RStudio_R_n39.png")

# 2) jamovi Desktop: show the six-row descriptive table produced by the jmv engine.
jproc = run_bg(["flatpak", "run", "org.jamovi.jamovi", str(JAMOVI_RESULTS)], OUT/"jamovi-launch.log")
jwid = focus(["jamovi"], jproc, "jamovi")
time.sleep(12)
save("02_jamovi_n39.png")

# 3) JASP Desktop: dismiss its first-run prompt and use File > Open > Computer.
sproc = run_bg(["flatpak", "run", "org.jaspstats.JASP"], OUT/"jasp-launch.log")
swid = focus(["jasp"], sproc, "jasp-start")
time.sleep(4)
# First-run dialog shown by JASP 0.99.0; choose "No" to keep the capture offline.
pyautogui.click(819, 578)
time.sleep(5)
swid = focus(["jasp"], sproc, "jasp-main", timeout=60)
# Ctrl+O opens JASP's File menu. Choose Open > Computer.
pyautogui.hotkey("ctrl", "o")
time.sleep(2)
pyautogui.click(220, 185)
time.sleep(4)
# Computer opens the native file chooser; Ctrl+L selects its location field.
pyautogui.hotkey("ctrl", "l")
time.sleep(1)
pyautogui.write(str(JASP_RESULTS), interval=0.003)
pyautogui.press("enter")
time.sleep(2)
pyautogui.press("enter")
time.sleep(20)
swid = focus(["jasp"], sproc, "jasp-results", timeout=60)
save("03_JASP_n39.png")

# Record exact app identities and native window classes used for the captures.
manifest = OUT / "captura_aplicaciones.txt"
lines = [
    "RStudio_window_id="+rwid,
    "jamovi_window_id="+jwid,
    "JASP_window_id="+swid,
    "jamovi_result_file="+str(JAMOVI_RESULTS),
    "JASP_result_file="+str(JASP_RESULTS),
    "X11_WINDOWS_AFTER_CAPTURE:\n"+window_list(),
]
for cmd in (["R","--version"],["rstudio","--version"],["flatpak","info","org.jamovi.jamovi"],["flatpak","info","org.jaspstats.JASP"]):
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
        lines.append("$ "+" ".join(cmd)+"\n"+(p.stdout+p.stderr).strip())
    except Exception as e:
        lines.append("$ "+" ".join(cmd)+"\n"+repr(e))
manifest.write_text("\n\n".join(lines)+"\n",encoding="utf-8")
