#!/usr/bin/env python3
"""Fail-closed runtime loader and CPU image-to-DocTags startup smoke for the isolated candidate."""
from __future__ import annotations
import argparse, hashlib, json, time, sys
from pathlib import Path

_TOKENIZER_RUNTIME_ROOT = next(
    (parent for parent in Path(__file__).resolve().parents if (parent / "cajita_tokenizer_materializer.py").is_file()),
    None,
)
if _TOKENIZER_RUNTIME_ROOT is None:
    raise RuntimeError("CAJITA_TOKENIZER_RUNTIME_ROOT_NOT_FOUND")
sys.path.insert(0, str(_TOKENIZER_RUNTIME_ROOT))
from cajita_tokenizer_materializer import load_pretrained_with_compressed_tokenizer
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
    from transformers import AutoConfig, AutoModelForImageTextToText, GenerationConfig
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
            target=state[name]
            decode_tensor_chunked_into(view,r,target)
            loaded.add(name)
    if hasattr(model,"tie_weights"): model.tie_weights()
    params=set(dict(model.named_parameters()))
    missing=sorted(params-loaded)
    if meta.get("tie_word_embeddings") and "lm_head.weight" in missing: missing.remove("lm_head.weight")
    if missing: raise RuntimeError("UNINITIALIZED_MODEL_PARAMETERS:"+",".join(missing[:10]))
    # Bind EOS/PAD behavior to the exact local generation policy shipped with this candidate.
    generation_config = GenerationConfig.from_pretrained(p, local_files_only=True)
    expected_eos = getattr(model.config, "eos_token_id", None)
    expected_eos_ids = set(expected_eos if isinstance(expected_eos, (list, tuple, set)) else ([expected_eos] if expected_eos is not None else []))
    observed_eos = generation_config.eos_token_id
    observed_eos_ids = set(observed_eos if isinstance(observed_eos, (list, tuple, set)) else ([observed_eos] if observed_eos is not None else []))
    if expected_eos_ids and not expected_eos_ids.issubset(observed_eos_ids):
        raise RuntimeError("GENERATION_CONFIG_EOS_MISMATCH")
    if model.config.pad_token_id is not None and generation_config.pad_token_id != model.config.pad_token_id:
        raise RuntimeError("GENERATION_CONFIG_PAD_MISMATCH")
    model.generation_config = generation_config
    model.eval()
    return model,meta

def make_test_image():
    from PIL import Image,ImageDraw
    im=Image.new("RGB",(640,480),"white"); d=ImageDraw.Draw(im)
    for i,line in enumerate(["INVOICE","Invoice number: INV-1042","Date: 2026-10-21",
        "Description             Amount","Document processing      123.45","Tax                      10.00","TOTAL                    133.45"]):
        d.text((28,28+i*48),line,fill="black")
    return im

def prepare_bounded_square_image(image, side):
    """Letterbox a document into the exact square expected by the bounded Idefics3 profile."""
    from PIL import Image
    if side < 1:
        raise ValueError("BOUNDED_IMAGE_SIDE_INVALID")
    image = image.convert("RGB")
    image.thumbnail((side, side), Image.Resampling.LANCZOS)
    # Neutral mid-grey maps close to zero under the packaged processor's mean/std normalization.
    canvas = Image.new("RGB", (side, side), (127, 127, 127))
    canvas.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    return canvas

ROOT=Path(__file__).resolve().parent

def smoke(candidate_dir, max_new_tokens=48, image_path=None, prompt="Convert this page to docling."):
    t=time.time()
    model,meta=load_candidate(candidate_dir)
    from transformers import AutoProcessor
    proc=load_pretrained_with_compressed_tokenizer(candidate_dir,AutoProcessor,local_files_only=True,trust_remote_code=False)
    # The packaged preprocessor defaults to a 2048-edge resize plus 512-edge
    # image splitting. That can exceed the 1 GiB CPU contract even with splitting
    # disabled. Use one bounded 256px square view and no high-resolution tiles.
    # Idefics3 expands each image into a fixed sequence of <image> tokens. Its count
    # must match the vision encoder after pixel-shuffle: (side / patch / scale)^2.
    # Letterboxing keeps the visual input square so one sequence length works for
    # arbitrary document aspect ratios without changing the pinned model weights.
    # This is a resource-bounded smoke profile, not a quality-equivalence claim.
    image_processor=getattr(proc,"image_processor",None)
    if image_processor is None:
        raise RuntimeError("DOCLING_IMAGE_PROCESSOR_MISSING")
    image_side=256
    vision_config=model.config.vision_config
    patch_size=int(vision_config.patch_size)
    scale_factor=int(model.config.scale_factor)
    if image_side % (patch_size * scale_factor) != 0:
        raise RuntimeError("DOCLING_BOUNDED_IMAGE_GEOMETRY_INVALID")
    image_seq_len=((image_side // patch_size) ** 2) // (scale_factor ** 2)
    if image_seq_len < 1:
        raise RuntimeError("DOCLING_IMAGE_SEQUENCE_LENGTH_INVALID")
    image_processor.do_image_splitting=False
    image_processor.do_pad=True
    image_processor.size={"longest_edge":image_side}
    image_processor.max_image_size={"longest_edge":image_side}
    proc.image_seq_len=image_seq_len
    if image_path:
        from PIL import Image
        path=Path(image_path)
        if path.is_symlink() or not path.is_file(): raise RuntimeError("INPUT_IMAGE_MISSING_OR_SYMLINK")
        image=Image.open(path).convert("RGB")
    else:
        image=make_test_image()
    image=prepare_bounded_square_image(image, image_side)
    try:
        msgs=[{"role":"user","content":[{"type":"image","image":image},{"type":"text","text":prompt}]}]
        inputs=proc.apply_chat_template(msgs,add_generation_prompt=True,tokenize=True,return_dict=True,return_tensors="pt")
    except Exception:
        inputs=proc(images=image,text=prompt,return_tensors="pt")
    inputs={k:(v.to("cpu") if isinstance(v,torch.Tensor) else v) for k,v in inputs.items()}
    image_token_count=int((inputs["input_ids"] == int(model.config.image_token_id)).sum().item())
    if image_token_count != image_seq_len:
        raise RuntimeError(f"DOCLING_IMAGE_TOKEN_COUNT_MISMATCH:{image_token_count}!={image_seq_len}")
    with torch.inference_mode():
        out=model.generate(**inputs,max_new_tokens=int(max_new_tokens),do_sample=False)
    prompt_ids=inputs["input_ids"]
    if out.shape[-1] >= prompt_ids.shape[-1] and torch.equal(out[:, :prompt_ids.shape[-1]], prompt_ids):
        new_ids=out[:, prompt_ids.shape[-1]:]
    else:
        new_ids=out
    if int(new_ids.shape[-1]) < 1:
        raise RuntimeError("DOCLING_GENERATED_NO_NEW_TOKENS")
    decoded=proc.batch_decode(new_ids, skip_special_tokens=True)[0]
    if len(decoded.strip())<1: raise RuntimeError("RUNTIME_SMOKE_EMPTY_OUTPUT")
    return {"status":"PASS","candidate_id":meta["candidate_id"],"model_load":"PASS","processor_load":"PASS",
            "image_preprocess":"PASS","generation":"PASS","generated_token_count":int(new_ids.shape[-1]),
            "output_text":decoded[:8192],"output_sha256":hashlib.sha256(decoded.encode("utf-8")).hexdigest(),
            "decoded_chars":len(decoded),"elapsed_seconds":round(time.time()-t,3),
            "decoded_span":"NEW_TOKENS_ONLY","quality_equivalence":"NOT_ESTABLISHED"}


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--candidate-dir",default=str(ROOT));ap.add_argument("--smoke-test",action="store_true")
    ap.add_argument("--verify-only",action="store_true");ap.add_argument("--max-new-tokens",type=int,default=48);ap.add_argument("--task-json-stdin",action="store_true")
    a=ap.parse_args()
    if a.task_json_stdin:
        task=json.load(sys.stdin)
        if task.get("operation")!="extract_document_image": ap.error("Unsupported task operation")
        print(json.dumps(smoke(a.candidate_dir,int(task.get("max_new_tokens",24)),task.get("image_path"),task.get("prompt","Extract visible text and fields.")),indent=2,ensure_ascii=False));return 0
    if a.smoke_test: print(json.dumps(smoke(a.candidate_dir,a.max_new_tokens),indent=2,ensure_ascii=False));return 0
    if a.verify_only:
        model,meta=load_candidate(a.candidate_dir);print(json.dumps({"status":"PASS","candidate_id":meta["candidate_id"]}));return 0
    ap.error("use --smoke-test, --verify-only, or --task-json-stdin")
if __name__=="__main__": raise SystemExit(main())
