#!/usr/bin/env python3
"""Fail-closed runtime loader and CPU image-to-DocTags startup smoke for the isolated candidate."""
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path
import numpy as np
import torch

def sha256_file(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def _signs(blob, offset, nbytes, count):
    bits=np.unpackbits(np.frombuffer(blob[offset:offset+nbytes],dtype=np.uint8),bitorder="little")[:count]
    return bits.astype(np.float32)*2.0-1.0

def decode_tensor(blob, r):
    shape=tuple(int(x) for x in r["shape"]); kind=r["kind"]
    if kind=="fp16":
        a=np.frombuffer(blob[r["offset"]:r["offset"]+r["nbytes"]],dtype="<f2")
        if a.size!=int(np.prod(shape)): raise RuntimeError("FP16_SIZE_MISMATCH:"+r["name"])
        return a.reshape(shape).copy()
    if kind=="bivlm_binary_outliers":
        m,n=map(int,r["matrix_shape"])
        s=_signs(blob,r["sign_offset"],r["sign_nbytes"],m*n).reshape(m,n)
        scales=np.frombuffer(blob[r["scale_offset"]:r["scale_offset"]+r["scale_nbytes"]],dtype="<f2").astype(np.float32)
        if scales.size!=m: raise RuntimeError("SCALE_MISMATCH:"+r["name"])
        w=s*scales[:,None]; k=int(r["outlier_count"])
        if k:
            ids=np.frombuffer(blob[r["outlier_index_offset"]:r["outlier_index_offset"]+4*k],dtype="<u4").astype(np.int64)
            vals=np.frombuffer(blob[r["outlier_value_offset"]:r["outlier_value_offset"]+2*k],dtype="<f2").astype(np.float32)
            if ids.size!=k or np.any(ids>=m*n): raise RuntimeError("OUTLIER_INDEX_INVALID:"+r["name"])
            w.reshape(-1)[ids]+=vals
        return w.reshape(shape).astype(np.float16)
    if kind=="nanoquant_style_binary_lowrank":
        m,n=map(int,r["matrix_shape"]); rank=int(r["rank"])
        a=_signs(blob,r["a_sign_offset"],r["a_sign_nbytes"],m*rank).reshape(m,rank)
        b=_signs(blob,r["b_sign_offset"],r["b_sign_nbytes"],rank*n).reshape(rank,n)
        sa=np.frombuffer(blob[r["a_scale_offset"]:r["a_scale_offset"]+r["a_scale_nbytes"]],dtype="<f2").astype(np.float32)
        sb=np.frombuffer(blob[r["b_scale_offset"]:r["b_scale_offset"]+r["b_scale_nbytes"]],dtype="<f2").astype(np.float32)
        if sa.size!=m or sb.size!=rank: raise RuntimeError("LOWRANK_SCALE_MISMATCH:"+r["name"])
        return ((a*sa[:,None])@(b*sb[:,None])).reshape(shape).astype(np.float16)
    raise RuntimeError("UNKNOWN_QUANT_ENCODING:"+str(kind))

def load_candidate(candidate_dir):
    p=Path(candidate_dir).resolve(); mp=p/"quantized_manifest.json"; bp=p/"quantized_weights.bin"
    if not mp.is_file() or not bp.is_file(): raise FileNotFoundError("CANDIDATE_MANIFEST_OR_WEIGHTS_MISSING")
    meta=json.loads(mp.read_text(encoding="utf-8"))
    if meta.get("schema")!="DOCLING_BINARY_QUANTIZED_MANIFEST/1.0" or meta.get("hard_cap_bytes")!=30_000_000:
        raise RuntimeError("CANDIDATE_MANIFEST_OR_CAP_MISMATCH")
    if sha256_file(bp)!=meta.get("weights_sha256"): raise RuntimeError("WEIGHTS_HASH_MISMATCH")
    from transformers import AutoConfig, AutoModelForImageTextToText
    config=AutoConfig.from_pretrained(str(p),local_files_only=True,trust_remote_code=False)
    old=torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.float16)
        model=AutoModelForImageTextToText.from_config(config,trust_remote_code=False)
    finally: torch.set_default_dtype(old)
    model.to(device="cpu",dtype=torch.float16)
    state=model.state_dict(keep_vars=True); raw=bp.read_bytes(); view=memoryview(raw); loaded=set()
    with torch.no_grad():
        for name,r in meta["tensors"].items():
            if r["kind"]=="alias": continue
            if name not in state: raise RuntimeError("TENSOR_NOT_IN_ARCHITECTURE:"+name)
            arr=decode_tensor(view,r); target=state[name]
            if tuple(arr.shape)!=tuple(target.shape): raise RuntimeError("SHAPE_MISMATCH:"+name)
            target.copy_(torch.from_numpy(np.ascontiguousarray(arr)).to(device="cpu",dtype=target.dtype))
            loaded.add(name); del arr
    if hasattr(model,"tie_weights"): model.tie_weights()
    params=set(dict(model.named_parameters()))
    missing=sorted(params-loaded)
    if meta.get("tie_word_embeddings") and "lm_head.weight" in missing: missing.remove("lm_head.weight")
    if missing: raise RuntimeError("UNINITIALIZED_MODEL_PARAMETERS:"+",".join(missing[:10]))
    model.eval()
    return model,meta

def make_test_image():
    from PIL import Image,ImageDraw
    im=Image.new("RGB",(640,480),"white"); d=ImageDraw.Draw(im)
    for i,line in enumerate(["INVOICE","Invoice number: INV-1042","Date: 2026-10-21",
        "Description             Amount","Document processing      123.45","Tax                      10.00","TOTAL                    133.45"]):
        d.text((28,28+i*48),line,fill="black")
    return im

def smoke(candidate_dir,max_new_tokens=48):
    t=time.time(); model,meta=load_candidate(candidate_dir)
    from transformers import AutoProcessor
    proc=AutoProcessor.from_pretrained(candidate_dir,local_files_only=True,trust_remote_code=False)
    image=make_test_image(); prompt="Convert this page to docling."
    try:
        msgs=[{"role":"user","content":[{"type":"image","image":image},{"type":"text","text":prompt}]}]
        inputs=proc.apply_chat_template(msgs,add_generation_prompt=True,tokenize=True,return_dict=True,return_tensors="pt")
    except Exception:
        inputs=proc(images=image,text=prompt,return_tensors="pt")
    inputs={k:(v.to("cpu") if isinstance(v,torch.Tensor) else v) for k,v in inputs.items()}
    with torch.inference_mode(): out=model.generate(**inputs,max_new_tokens=max_new_tokens,do_sample=False)
    decoded=proc.batch_decode(out,skip_special_tokens=False)[0]
    if len(decoded.strip())<4: raise RuntimeError("RUNTIME_SMOKE_EMPTY_OR_SHORT_OUTPUT")
    return {"status":"PASS","candidate_id":meta["candidate_id"],"model_load":"PASS","processor_load":"PASS",
        "image_preprocess":"PASS","generation":"PASS","decoded_chars":len(decoded),"output_prefix":decoded[:200],
        "elapsed_seconds":round(time.time()-t,3),"quality_equivalence":"NOT_ESTABLISHED"}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--candidate-dir",required=True); ap.add_argument("--smoke-test",action="store_true")
    ap.add_argument("--verify-only",action="store_true"); ap.add_argument("--max-new-tokens",type=int,default=48); a=ap.parse_args()
    if a.smoke_test: print(json.dumps(smoke(a.candidate_dir,a.max_new_tokens),indent=2,ensure_ascii=False)); return 0
    if a.verify_only:
        model,meta=load_candidate(a.candidate_dir); print(json.dumps({"status":"PASS","candidate_id":meta["candidate_id"]})); return 0
    ap.error("use --smoke-test or --verify-only")
if __name__=="__main__": raise SystemExit(main())
