#!/usr/bin/env python3
"""Material P06 executor: STT + primary Chatterbox Spanish + local Sabela.

No voice provider is silently substituted. Every selected artifact, revision,
license and generated-output digest is recorded. Any failed lane fails closed.
"""
from __future__ import annotations
import hashlib,json,os,subprocess,sys,time,venv
from pathlib import Path

ROOT=Path(os.environ["MISSION_ROOT"]).resolve()
OUT=Path(os.environ.get("OUT_DIR",ROOT/"continuity/runtime-evidence/p06")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
V03_SHA="7a1449a5d6194b6cbc3e083bf1c7ba55533ad196"
BRIDGE_SHA="ad95248dd78fadf45645774e0338df0f1bbc128b"
SABELA_REPO="HiTZ/TTS-gl_sabela"
SABELA_COMMIT="b513a2e957d53c3e5bcf32bb51fce01688decd92"
SABELA_ONNX_SHA256="b7df43263c2eefffa79b841431d542957c8c6478b41448be679ef36036087f22"
SABELA_LICENSE="Apache-2.0"
CHATTERBOX_REPO="https://github.com/resemble-ai/chatterbox.git"
CHATTERBOX_COMMIT="5de7a54aa4e5e2baadb0182dde554908b48b85c2"

def sh(cmd,cwd=None,env=None,timeout=None):
    print("P06_EXEC "+ " ".join(map(str,cmd)),flush=True)
    try:
        return subprocess.run(cmd,cwd=cwd,env=env,text=True,check=True,timeout=timeout,capture_output=True)
    except subprocess.CalledProcessError as e:
        print("P06_SUBPROCESS_STDOUT "+(e.stdout or "")[-12000:],flush=True)
        print("P06_SUBPROCESS_STDERR "+(e.stderr or "")[-12000:],file=sys.stderr,flush=True)
        raise

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def main():
    subprocess.run(["git","cat-file","-e",V03_SHA+"^{commit}"],cwd=ROOT,check=True)
    subprocess.run(["git","cat-file","-e",BRIDGE_SHA+"^{commit}"],cwd=ROOT,check=True)
    print("LOUKSNA_P06_TELEMETRY "+json.dumps({"event":"P06_START","utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"v03_head":V03_SHA,"bridge_head":BRIDGE_SHA},sort_keys=True),flush=True)

    work=Path(os.environ.get("P06_WORK_DIR",str(Path(os.environ.get("RUNNER_TEMP","/tmp"))/"louksna-p06")))
    work.mkdir(parents=True,exist_ok=True)
    evidence={"schema":"LOUKSNA_ZD_P06_VOICE/1.0","status":"RUNNING","primary_requested":"CHATTERBOX_ES_ES_SELF_HOSTED_API","sabela":{"repo":SABELA_REPO,"revision":SABELA_COMMIT,"license":SABELA_LICENSE,"artifact_sha256":SABELA_ONNX_SHA256}}

    # ---- STT: official whisper.cpp candidate, fully local ----
    whisper=work/"whisper.cpp"
    if not whisper.exists():
        sh(["git","clone","--depth","1","https://github.com/ggml-org/whisper.cpp.git",str(whisper)])
    whisper_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=whisper,text=True).strip()
    sh(["cmake","-B","build","-DCMAKE_BUILD_TYPE=Release"],cwd=whisper,timeout=300)
    sh(["cmake","--build","build","-j2"],cwd=whisper,timeout=600)
    sh(["bash","models/download-ggml-model.sh","base"],cwd=whisper,timeout=600)
    model=whisper/"models/ggml-base.bin"
    if not model.is_file(): raise RuntimeError("WHISPER_MODEL_MISSING")
    stt_probe=whisper/"samples/jfk.wav"
    if not stt_probe.is_file(): raise RuntimeError("WHISPER_SAMPLE_MISSING")
    r=sh(["./build/bin/whisper-cli","-m","models/ggml-base.bin","-f","samples/jfk.wav","-nt","-np"],cwd=whisper,timeout=300)
    stt_text=(r.stdout+r.stderr).strip()
    if len(stt_text)<3: raise RuntimeError("STT_FUNCTIONAL_PROBE_EMPTY")
    evidence["stt"]={"implementation":"ggml-org/whisper.cpp","commit":whisper_head,"model_sha256":sha256(model),"probe":"samples/jfk.wav","text_excerpt":stt_text[-500:]}

    # ---- Primary TTS: self-hosted Chatterbox Multilingual V3, Spanish ----
    venv_dir=work/"venv"; py=venv_dir/"bin/python"
    if not py.exists(): venv.EnvBuilder(with_pip=True).create(venv_dir)
    sh([str(py),"-m","pip","install","--upgrade","pip","setuptools","wheel"],timeout=600)
    cb_src=work/"chatterbox"
    if not cb_src.exists():
        sh(["git","clone",CHATTERBOX_REPO,str(cb_src)],timeout=600)
    sh(["git","checkout","--detach",CHATTERBOX_COMMIT],cwd=cb_src,timeout=120)
    cb_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=cb_src,text=True).strip()
    if cb_head != CHATTERBOX_COMMIT: raise RuntimeError("CHATTERBOX_SOURCE_COMMIT_MISMATCH")
    sh([str(py),"-m","pip","install","-e",".","soundfile"],cwd=cb_src,timeout=1800)
    probe=OUT/"p06_chatterbox_es_es.wav"
    code='''import inspect, torch, torchaudio as ta\nfrom chatterbox.mtl_tts import ChatterboxMultilingualTTS\nsig=inspect.signature(ChatterboxMultilingualTTS.from_pretrained)\nif "t3_model" not in sig.parameters: raise RuntimeError("CHATTERBOX_API_MISSING_T3_MODEL")\ndevice="cuda" if torch.cuda.is_available() else "cpu"\ntorch.manual_seed(1234)\nmodel=ChatterboxMultilingualTTS.from_pretrained(device=device,t3_model="v3")\ntext="Esta es una prueba controlada de la voz de Louksna en español."\nwav=model.generate(text,language_id="es")\nta.save(r"%s",wav,model.sr)\nprint("DEVICE="+device)\nprint("SR="+str(model.sr))\nprint("API="+str(sig))\n''' % str(probe)
    r=sh([str(py),"-c",code],timeout=3600)
    if not probe.is_file() or probe.stat().st_size<1000: raise RuntimeError("CHATTERBOX_READ_ALOUD_EMPTY")
    evidence["tts"]={"implementation":"ResembleAI/chatterbox","source_commit":CHATTERBOX_COMMIT,"model":"ChatterboxMultilingual V3","language":"es","device_line":r.stdout.strip()[-200:],"output_sha256":sha256(probe),"output_size":probe.stat().st_size,"silent_failover":False}

    # ---- E2E STT of generated Spanish audio ----
    e2e=sh([str(whisper/"build/bin/whisper-cli"),"-m",str(model),"-f",str(probe),"-nt","-np"],cwd=whisper,timeout=600)
    transcript=(e2e.stdout+e2e.stderr).strip()
    if len(transcript)<3: raise RuntimeError("E2E_STT_OF_TTS_EMPTY")
    evidence["stt"]["e2e_generated_audio_transcript"]=transcript[-1000:]

    # ---- Local Sabela: official HiTZ artifact + aHoTTS ----
    ahot=work/"aHoTTS"
    if not ahot.exists(): sh(["git","clone","--depth","1","https://github.com/hitz-zentroa/aHoTTS.git",str(ahot)],timeout=600)
    ahot_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ahot,text=True).strip()
    sh([str(py),"-m","pip","install","-r","requirements.txt"],cwd=ahot,timeout=1200)
    sabela_out=OUT/"p06_sabela.wav"
    sh([str(py),"synthesize.py","-t","Esta es una prueba de Sabela.","-l","gl","-m","sabela","-o",str(sabela_out)],cwd=ahot,timeout=1200)
    candidates=list(OUT.glob("p06_sabela*.wav"))+[sabela_out]
    existing=next((p for p in candidates if p.is_file() and p.stat().st_size>1000),None)
    if existing is None: raise RuntimeError("SABELA_SYNTHESIS_OUTPUT_MISSING")
    # Locate the downloaded Sabela ONNX and verify its published SHA-256.
    hf_cache=Path(os.environ.get("HF_HOME",str(Path.home()/".cache/huggingface")))
    matches=list(hf_cache.rglob("vits.onnx")) if hf_cache.exists() else []
    verified=[p for p in matches if p.is_file() and sha256(p)==SABELA_ONNX_SHA256]
    if not verified: raise RuntimeError("SABELA_ONNX_HASH_NOT_VERIFIED")
    evidence["sabela"].update({"implementation":"HiTZ/aHoTTS","repo_commit":ahot_head,"language":"gl","output_sha256":sha256(existing),"output_size":existing.stat().st_size,"model_verified":True,"model_path":str(verified[0])})

    evidence["status"]="PASS"
    (OUT/"P06_VOICE_EVIDENCE.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    result={"status":"PASS","checkpoint":"CHECKPOINT_06","parent_checkpoint":"CHECKPOINT_05","next_point":"P07","transition_id":"P06-CHECKPOINT-TO-P07-001","certified":False,"active":False,"g23":"SEPARATE_REQUIRED","g24":"SEPARATE_REQUIRED","material_evidence":evidence}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("LOUKSNA_P06_TELEMETRY "+json.dumps({"event":"CHECKPOINT_06_REACHED","next_point":"P07","status":"PASS"},sort_keys=True),flush=True)

if __name__=="__main__":
    try: main()
    except Exception as e:
        print("P06_FAIL_CLOSED "+type(e).__name__+": "+str(e),file=sys.stderr)
        raise
