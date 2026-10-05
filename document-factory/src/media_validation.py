from __future__ import annotations
import hashlib,json,shutil,subprocess
from pathlib import Path
def _load(x): return json.loads(Path(x).read_text(encoding="utf-8")) if isinstance(x,(str,Path)) else x
def ffprobe_admission(lock):
    obj=_load(lock); row=next((x for x in obj.get("providers",[]) if x.get("id")=="ffprobe"),None)
    if not row: return {"status":"EXCLUDED","admitted":False,"reason":"FFPROBE_NOT_DECLARED"}
    pinned=all(row.get(k) for k in ("version","source","sha256")) and not str(row.get("state","")).startswith("UNRESOLVED")
    binary=shutil.which("ffprobe"); observed=None
    if binary:
        p=subprocess.run([binary,"-version"],text=True,capture_output=True,timeout=10)
        observed={"path":binary,"binary_sha256":hashlib.sha256(Path(binary).read_bytes()).hexdigest(),"version_line":(p.stdout.splitlines() or [""])[0],"exit_code":p.returncode}
    return {"status":"ADMITTED" if pinned else "EXCLUDED","admitted":bool(pinned),"reason":None if pinned else "FFPROBE_PROVENANCE_NOT_PINNED","declared":row,"observed_binary":observed}
def validate_probe_metadata(probe,c):
    video=next((x for x in probe.get("streams",[]) if x.get("codec_type")=="video"),None); failures=[]
    if not video: return {"status":"FAIL","failures":["VIDEO_STREAM_MISSING"]}
    width=int(video.get("width") or 0); height=int(video.get("height") or 0)
    try: dur=float((probe.get("format") or {}).get("duration"))
    except Exception: dur=-1
    if c.get("max_duration_seconds") is not None and (dur<0 or dur>float(c["max_duration_seconds"])): failures.append("VIDEO_DURATION_OUT_OF_RANGE")
    if c.get("orientation")=="horizontal" and not width>height: failures.append("VIDEO_ORIENTATION_NOT_HORIZONTAL")
    if c.get("orientation")=="vertical" and not height>width: failures.append("VIDEO_ORIENTATION_NOT_VERTICAL")
    return {"status":"PASS" if not failures else "FAIL","failures":failures,"width":width,"height":height,"duration_seconds":dur}
