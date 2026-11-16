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
            # The GUI may delegate to a background process; keep checking the X11 window list.
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

def open_file_in_gui(path):
    # Use the application's native Open dialog rather than assuming command-line file association.
    pyautogui.hotkey("ctrl", "o")
    time.sleep(3)
    pyautogui.hotkey("ctrl", "l")
    time.sleep(1)
    pyautogui.write(str(path), interval=0.003)
    pyautogui.press("enter")
    time.sleep(2)
    pyautogui.press("enter")
    time.sleep(18)

def save(name):
    target = OUT / name
    subprocess.run(["scrot", str(target)], check=True)
    if not target.is_file() or target.stat().st_size < 10_000:
        raise RuntimeError(f"Screenshot missing or unexpectedly small: {target}")

# 1) RStudio Desktop by Posit. The actual R script computes the six distributions
# and displays the descriptive table plus six frequency plots in its Plots pane.
r_script = BASE / "R/interfaz_r_n39.R"
rproc = run_bg(["rstudio", "--no-restore", "--no-save", str(r_script)], OUT/"rstudio-launch.log")
rwid = focus(["rstudio"], rproc, "rstudio")
pyautogui.hotkey("ctrl", "2")
time.sleep(2)
cmd = f'source("{r_script.as_posix()}")'
pyautogui.write(cmd, interval=0.004)
pyautogui.press("enter")
time.sleep(20)
save("01_RStudio_R_n39.png")

# 2) jamovi Desktop. Open the descriptive table actually produced by the jmv engine.
jproc = run_bg(["flatpak", "run", "org.jamovi.jamovi", str(JAMOVI_RESULTS)], OUT/"jamovi-launch.log")
jwid = focus(["jamovi"], jproc, "jamovi")
time.sleep(12)
save("02_jamovi_n39.png")

# 3) JASP Desktop. Dismiss the first-run update prompt, then open the table produced
# by JASP's own jaspDescriptives engine through its native Open dialog.
sproc = run_bg(["flatpak", "run", "org.jaspstats.JASP"], OUT/"jasp-launch.log")
swid = focus(["jasp"], sproc, "jasp-start")
time.sleep(4)
# First-run dialog shown by JASP 0.99.0; choose "No" to keep the capture offline.
pyautogui.click(819, 578)
time.sleep(5)
swid = focus(["jasp"], sproc, "jasp-main", timeout=60)
open_file_in_gui(JASP_RESULTS)
swid = focus(["jasp"], sproc, "jasp-results", timeout=60)
save("03_JASP_n39.png")

# Evidence of official binaries, versions and real X11 windows found.
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
