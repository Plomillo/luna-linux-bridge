#!/usr/bin/env python3
"""Inference runtime for a same-source Qwen3 low-rank INT8-factor candidate."""
from __future__ import annotations
import json, pathlib, time
import torch
from torch import nn
from torch.nn import functional as F
import sys
_RUNTIME_ROOT = next(
    (parent for parent in pathlib.Path(__file__).resolve().parents
     if (parent / "cajita_weight_materializer.py").is_file()),
    None,
)
if _RUNTIME_ROOT is None:
    raise RuntimeError("CAJITA_RUNTIME_ROOT_NOT_FOUND")
sys.path.insert(0, str(_RUNTIME_ROOT))
from cajita_weight_materializer import load_model_state
from cajita_tokenizer_materializer import load_pretrained_with_compressed_tokenizer
from transformers import AutoConfig, AutoTokenizer, GenerationConfig, Qwen3ForCausalLM

ROOT = pathlib.Path(__file__).resolve().parent

class LowRankLinear(nn.Module):
    def __init__(self, base, rank):
        super().__init__()
        self.in_features, self.out_features = base.in_features, base.out_features
        self.weight_u = nn.Parameter(torch.empty((self.out_features, rank), dtype=torch.int8, device="meta"), requires_grad=False)
        self.weight_v = nn.Parameter(torch.empty((rank, self.in_features), dtype=torch.int8, device="meta"), requires_grad=False)
        self.scale_u = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.scale_v = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.bias = base.bias

    def forward(self, x):
        v = self.weight_v.to(dtype=x.dtype) * self.scale_v.to(dtype=x.dtype).unsqueeze(1)
        u = self.weight_u.to(dtype=x.dtype) * self.scale_u.to(dtype=x.dtype).unsqueeze(0)
        return F.linear(F.linear(x, v), u, self.bias)

class LowRankEmbedding(nn.Module):
    def __init__(self, base, rank):
        super().__init__()
        self.num_embeddings, self.embedding_dim = base.num_embeddings, base.embedding_dim
        self.padding_idx = base.padding_idx
        self.max_norm, self.norm_type = base.max_norm, base.norm_type
        self.scale_grad_by_freq, self.sparse = base.scale_grad_by_freq, base.sparse
        self.weight_u = nn.Parameter(torch.empty((self.num_embeddings, rank), dtype=torch.int8, device="meta"), requires_grad=False)
        self.weight_v = nn.Parameter(torch.empty((rank, self.embedding_dim), dtype=torch.int8, device="meta"), requires_grad=False)
        self.scale_u = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.scale_v = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)

    def forward(self, ids):
        u = F.embedding(ids, self.weight_u).to(dtype=torch.bfloat16)
        u = u * self.scale_u.to(dtype=u.dtype)
        v = self.weight_v.to(dtype=u.dtype) * self.scale_v.to(dtype=u.dtype).unsqueeze(1)
        return torch.matmul(u, v)

def load_candidate():
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    cfg = AutoConfig.from_pretrained(ROOT, local_files_only=True)
    if getattr(cfg, "model_type", None) != "qwen3":
        raise RuntimeError("MODEL_IDENTITY_MISMATCH")
    with torch.device("meta"):
        model = Qwen3ForCausalLM(cfg)
    modules = dict(model.named_modules())
    factorized = 0
    for name, module in list(modules.items()):
        if not name:
            continue
        if isinstance(module, nn.Embedding):
            replacement = LowRankEmbedding(module, int(json.loads((ROOT / "compression_metadata.json").read_text())["rank"]))
        elif isinstance(module, nn.Linear):
            replacement = LowRankLinear(module, int(json.loads((ROOT / "compression_metadata.json").read_text())["rank"]))
        else:
            continue
        parent_name, _, leaf = name.rpartition(".")
        parent = modules[parent_name]
        setattr(parent, leaf, replacement)
        factorized += 1
    if factorized < 200:
        raise RuntimeError("MODEL_MAPPING_INCOMPLETE:" + str(factorized))
    weights = load_model_state(ROOT / "model.safetensors")
    missing, unexpected = model.load_state_dict(weights, strict=True, assign=True)
    if missing or unexpected:
        raise RuntimeError("STATE_MAPPING_MISMATCH:" + json.dumps({"missing": missing[:20], "unexpected": unexpected[:20]}))
    # Qwen3's rotary buffers were initialized under the meta device. Re-materialize
    # the exact configured RoPE frequencies on CPU after loading the factor weights.
    from transformers.modeling_rope_utils import ROPE_INIT_FUNCTIONS
    rope_count = 0
    for module in model.modules():
        if module.__class__.__name__ == "Qwen3RotaryEmbedding":
            inv_freq, attention_scaling = ROPE_INIT_FUNCTIONS[module.rope_type](module.config, device=torch.device("cpu"))
            module.inv_freq = inv_freq
            module.original_inv_freq = inv_freq.clone()
            module.attention_scaling = attention_scaling
            rope_count += 1
    if rope_count < 1:
        raise RuntimeError("QWEN3_ROPE_MODULE_NOT_FOUND")
    remaining_meta = [name for name, buf in model.named_buffers() if buf.is_meta]
    if remaining_meta:
        raise RuntimeError("UNMATERIALIZED_META_BUFFERS:" + ",".join(remaining_meta[:20]))
    model._lowrank_rope_materialized = rope_count
    # Bind EOS/PAD behavior to the exact local generation policy shipped with the weights.
    generation_config = GenerationConfig.from_pretrained(ROOT, local_files_only=True)
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
    return model

def smoke_test(generate=False, prompt="Test", max_new_tokens=1):
    t0=time.monotonic()
    if not isinstance(prompt,str) or not prompt.strip(): raise ValueError("PROMPT_REQUIRED")
    if isinstance(max_new_tokens,bool) or not 1<=int(max_new_tokens)<=128: raise ValueError("MAX_NEW_TOKENS_OUT_OF_RANGE")
    tokenizer=load_pretrained_with_compressed_tokenizer(ROOT,AutoTokenizer,local_files_only=True)
    model=load_candidate()
    tok=tokenizer(prompt,return_tensors="pt")
    with torch.inference_mode(): out=model(input_ids=tok["input_ids"],attention_mask=tok.get("attention_mask"),use_cache=False)
    logits=out.logits
    if logits.ndim!=3 or logits.shape[0]!=1 or not torch.isfinite(logits).all(): raise RuntimeError("NONFINITE_OR_MALFORMED_LOGITS")
    next_id=int(logits[0,-1].argmax().item())
    if not 0<=next_id<int(model.config.vocab_size): raise RuntimeError("NEXT_TOKEN_OUT_OF_RANGE")
    result={"status":"PASS_MODEL_START_AND_FORWARD","model_type":model.config.model_type,"vocab_size":int(model.config.vocab_size),
            "input_token_count":int(tok["input_ids"].shape[-1]),"logits_shape":list(logits.shape),"finite_logits":True,"argmax_token_id":next_id,
            "elapsed_seconds":round(time.monotonic()-t0,3),"rope_buffers_materialized":int(getattr(model,"_lowrank_rope_materialized",0)),
            "quality_equivalence":"NOT_ESTABLISHED_BY_SMOKE_TEST"}
    if generate:
        rendered = prompt
        if hasattr(tokenizer, "apply_chat_template"):
            messages = [{"role": "user", "content": prompt}]
            for extra in ({"enable_thinking": False}, {}):
                try:
                    candidate = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, **extra)
                except Exception:
                    continue
                if isinstance(candidate, str) and candidate.strip():
                    rendered = candidate
                    break
        gen_tok = tokenizer(rendered, return_tensors="pt")
        with torch.inference_mode():
            generated = model.generate(
                gen_tok["input_ids"],
                attention_mask=gen_tok.get("attention_mask"),
                max_new_tokens=int(max_new_tokens),
                min_new_tokens=min(3, int(max_new_tokens)),
                do_sample=False,
                repetition_penalty=1.12,
                no_repeat_ngram_size=3,
                renormalize_logits=True,
                use_cache=True,
            )
        count = int(generated.shape[-1] - gen_tok["input_ids"].shape[-1])
        if count < 1: raise RuntimeError("MODEL_GENERATED_NO_NEW_TOKENS")
        result.update({"generation_status":"PASS_GENERATE","generated_token_count":count,
                       "output_text":tokenizer.decode(generated[0, gen_tok["input_ids"].shape[-1]:], skip_special_tokens=True)[:8192],
                       "generation_prompt":"CHAT_TEMPLATE_THINKING_DISABLED_WHEN_AVAILABLE"})
    return result

if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--smoke-test",action="store_true");p.add_argument("--task-json-stdin",action="store_true")
    a=p.parse_args()
    if a.task_json_stdin:
        task=json.load(sys.stdin)
        if task.get("operation")!="analyze_reasoning": p.error("Unsupported task operation")
        result=smoke_test(True,task.get("prompt",""),int(task.get("max_new_tokens",8)));result["status"]="PASS_TASK_REASONING"
    else:
        if not a.smoke_test: p.error("Use --smoke-test or --task-json-stdin")
        result=smoke_test()
    print(json.dumps(result,indent=2,ensure_ascii=False))
