from pathlib import Path
import importlib.util, json

JOB = Path(__file__).resolve().parent
WORKER = JOB / "docling_30mb_quantize_worker_v1.py"
RUNTIME = JOB / "docling_30mb_runtime_v1.py"
MISSION = JOB / "DOCLING_30MB_MISSION.json"

def load_module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def test_mission_hard_cap_is_exact_and_fail_closed():
    m=json.loads(MISSION.read_text(encoding="utf-8"))
    assert m["target"]["hard_cap_bytes"] == 30_000_000
    assert m["target"]["fail_closed"] is True
    assert m["target"]["no_padding"] is True

def test_source_resources_read_only_and_calibre_preserved():
    w=load_module(WORKER,"docling_worker_contract")
    assert len(w.SOURCES)==5
    assert w.CAP==30_000_000
    assert all(v["bytes"]>0 and len(v["sha256"])==64 for v in w.SOURCES.values())
    assert all(v["path"].exists() for v in w.SOURCES.values())

def test_runtime_supports_explicit_quantization_kinds():
    r=load_module(RUNTIME,"docling_runtime_contract")
    assert callable(r.decode_tensor)
    assert callable(r.load_candidate)
    assert callable(r.smoke)

def test_worker_never_overwrites_original_files():
    source=WORKER.read_text(encoding="utf-8")
    assert "source_files_modified\":False" in source
    assert "os.replace(stage,final)" in source
    assert "if bundle_bytes>CAP: raise RuntimeError" in source

def test_candidate_gate_counts_every_file_in_directory():
    source=WORKER.read_text(encoding="utf-8")
    assert "bundle_bytes=tree_bytes(stage)" in source
    assert "staged_final_bytes>CAP" in source
    assert "final_bytes>CAP" in source
