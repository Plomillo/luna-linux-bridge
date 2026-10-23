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

def decode_tensor_chunked_into(blob, r, target, chunk_rows=256):
    """Decode one quantized tensor directly into its destination, bounding temporary RAM."""
    if r.get("kind") != "nanoquant_style_binary_lowrank":
        arr = decode_tensor(blob, r)
        if tuple(arr.shape) != tuple(target.shape):
            raise RuntimeError("SHAPE_MISMATCH:" + r["name"])
        target.copy_(torch.from_numpy(np.ascontiguousarray(arr)).to(device=target.device, dtype=target.dtype))
        del arr
        return
    shape = tuple(int(x) for x in r["shape"])
    m, n = map(int, r["matrix_shape"])
    rank = int(r["rank"])
    if tuple(target.shape) != shape or int(np.prod(shape)) != m * n:
        raise RuntimeError("CHUNK_TARGET_SHAPE_MISMATCH:" + r["name"])
    required = {
        "a_sign_nbytes": (m * rank + 7) // 8,
        "a_scale_nbytes": m * 2,
        "b_sign_nbytes": (rank * n + 7) // 8,
        "b_scale_nbytes": rank * 2,
    }
    for key, expected in required.items():
        if int(r[key]) != expected:
            raise RuntimeError("CHUNK_MANIFEST_LENGTH_MISMATCH:" + r["name"] + ":" + key)
    def read_sign_range(off, bit_start, bit_count):
        first = bit_start // 8
        last = (bit_start + bit_count + 7) // 8
        raw = np.frombuffer(blob[off + first:off + last], dtype=np.uint8)
        bits = np.unpackbits(raw, bitorder="little")
        skip = bit_start - first * 8
        return (bits[skip:skip + bit_count].astype(np.float32) * 2.0 - 1.0)
    b_bits = _signs(blob, int(r["b_sign_offset"]), int(r["b_sign_nbytes"]), rank * n).reshape(rank, n)
    b_scales = np.frombuffer(
        blob[int(r["b_scale_offset"]):int(r["b_scale_offset"]) + int(r["b_scale_nbytes"])],
        dtype="<f2",
    ).astype(np.float32)
    if b_scales.size != rank:
        raise RuntimeError("CHUNK_B_SCALE_MISMATCH:" + r["name"])
    b_matrix = b_bits * b_scales[:, None]
    chunk_rows = max(8, int(chunk_rows))
    for start in range(0, m, chunk_rows):
        end = min(m, start + chunk_rows)
        rows = end - start
        a_bits = read_sign_range(int(r["a_sign_offset"]), start * rank, rows * rank).reshape(rows, rank)
        s0 = int(r["a_scale_offset"]) + start * 2
        sn = rows * 2
        a_scales = np.frombuffer(blob[s0:s0 + sn], dtype="<f2").astype(np.float32)
        if a_scales.size != rows:
            raise RuntimeError("CHUNK_A_SCALE_MISMATCH:" + r["name"])
        decoded = ((a_bits * a_scales[:, None]) @ b_matrix).astype(np.float16)
        target[start:end].copy_(
            torch.from_numpy(np.ascontiguousarray(decoded)).to(device=target.device, dtype=target.dtype)
        )
        del decoded, a_bits, a_scales
    del b_bits, b_scales, b_matrix

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
        # Construct on the meta device to avoid allocating and initializing a full
        # random FP16 model before overwriting every declared tensor with decoded weights.
        torch.set_default_dtype(torch.float16)
        with torch.device("meta"):
            model=AutoModelForImageTextToText.from_config(config,trust_remote_code=False)
    finally:
        torch.set_default_dtype(old)
    # Allocate uninitialized CPU storage; the verified quantized manifest fills all
    # declared parameters below, after which missing parameters are rejected.
    model.to_empty(device="cpu")
    # File-map the compact payload and release mapped resident pages periodically.
    # read_bytes() duplicates the complete payload in anonymous RSS at the same time
    # the full FP16 parameter set is resident. DONTNEED is safe for this read-only file:
    # any tensor accessed later is transparently paged back from the verified payload.
    import mmap
    with bp.open("rb") as weights_file:
        mapped=mmap.mmap(weights_file.fileno(),0,access=mmap.ACCESS_READ)
    view=memoryview(mapped); loaded=set()
    try:
        with torch.no_grad():
            for name,r in meta["tensors"].items():
                if r["kind"]=="alias": continue
                if name not in state: raise RuntimeError("TENSOR_NOT_IN_ARCHITECTURE:"+name)
                target=state[name]
                decode_tensor_chunked_into(view,r,target)
                loaded.add(name)
                if (len(loaded) % 8 == 0 and hasattr(mapped,"madvise")
                        and hasattr(mmap,"MADV_DONTNEED")):
                    mapped.madvise(mmap.MADV_DONTNEED)
    finally:
        view.release()
        try:
            mapped.close()
        except BufferError:
            # Failures can retain temporary NumPy views in traceback frames. Keep the
            # exception authoritative; the mapping is read-only and GC will close it.
            pass
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
