#!/usr/bin/env python3
"""Experimental GPT-OSS low-rank inference runtime; derived candidate only."""
from __future__ import annotations
import argparse
import json
import pathlib
import time
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
from transformers import AutoTokenizer, GenerationConfig, GptOssConfig, GptOssForCausalLM
from transformers.models.gpt_oss.modeling_gpt_oss import GptOssExperts, GptOssTopKRouter

ROOT = pathlib.Path(__file__).resolve().parent


class LowRankLinear(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.in_features, self.out_features = base.in_features, base.out_features
        self.weight_u = nn.Parameter(torch.empty((self.out_features, 1), dtype=torch.int8, device="meta"), requires_grad=False)
        self.weight_v = nn.Parameter(torch.empty((1, self.in_features), dtype=torch.int8, device="meta"), requires_grad=False)
        self.scale_u = nn.Parameter(torch.empty((1,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.scale_v = nn.Parameter(torch.empty((1,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.bias = base.bias

    def forward(self, x):
        v = self.weight_v.to(dtype=x.dtype) * self.scale_v.to(dtype=x.dtype).unsqueeze(1)
        u = self.weight_u.to(dtype=x.dtype) * self.scale_u.to(dtype=x.dtype).unsqueeze(0)
        return F.linear(F.linear(x, v), u, self.bias)


class LowRankEmbedding(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.num_embeddings, self.embedding_dim = base.num_embeddings, base.embedding_dim
        self.padding_idx = base.padding_idx
        self.weight_u = nn.Parameter(torch.empty((self.num_embeddings, 1), dtype=torch.int8, device="meta"), requires_grad=False)
        self.weight_v = nn.Parameter(torch.empty((1, self.embedding_dim), dtype=torch.int8, device="meta"), requires_grad=False)
        self.scale_u = nn.Parameter(torch.empty((1,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.scale_v = nn.Parameter(torch.empty((1,), dtype=torch.float32, device="meta"), requires_grad=False)

    def forward(self, ids):
        dtype = torch.bfloat16
        u = F.embedding(ids, self.weight_u.to(dtype=dtype)) * self.scale_u.to(dtype=dtype)
        v = self.weight_v.to(dtype=dtype) * self.scale_v.to(dtype=dtype).unsqueeze(1)
        return torch.matmul(u, v)


class LowRankRouter(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.top_k, self.num_experts, self.hidden_dim = base.top_k, base.num_experts, base.hidden_dim
        self.weight_u = nn.Parameter(torch.empty((self.num_experts, 1), dtype=torch.int8, device="meta"), requires_grad=False)
        self.weight_v = nn.Parameter(torch.empty((1, self.hidden_dim), dtype=torch.int8, device="meta"), requires_grad=False)
        self.scale_u = nn.Parameter(torch.empty((1,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.scale_v = nn.Parameter(torch.empty((1,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.bias = base.bias

    def forward(self, hidden_states):
        hidden_states = hidden_states.reshape(-1, self.hidden_dim)
        dtype = hidden_states.dtype
        v = self.weight_v.to(dtype=dtype) * self.scale_v.to(dtype=dtype).unsqueeze(1)
        u = self.weight_u.to(dtype=dtype) * self.scale_u.to(dtype=dtype).unsqueeze(0)
        router_logits = F.linear(F.linear(hidden_states, v), u, self.bias)
        router_top_value, router_indices = torch.topk(router_logits, self.top_k, dim=-1)
        router_top_value = F.softmax(router_top_value, dim=1, dtype=router_top_value.dtype)
        router_scores = torch.zeros_like(router_logits).scatter_(1, router_indices, router_top_value)
        return router_scores, router_indices


class LowRankExperts(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.intermediate_size = base.intermediate_size
        self.num_experts = base.num_experts
        self.hidden_size = base.hidden_size
        self.expert_dim = base.expert_dim
        self.alpha = base.alpha
        self.limit = base.limit
        # Expert matrices are stored in source orientation [input, output].
        self.gate_up_proj_u = nn.Parameter(torch.empty((self.num_experts, self.hidden_size, 1), dtype=torch.int8, device="meta"), requires_grad=False)
        self.gate_up_proj_v = nn.Parameter(torch.empty((self.num_experts, 1, 2 * self.expert_dim), dtype=torch.int8, device="meta"), requires_grad=False)
        self.gate_up_proj_scale_u = nn.Parameter(torch.empty((self.num_experts, 1), dtype=torch.float32, device="meta"), requires_grad=False)
        self.gate_up_proj_scale_v = nn.Parameter(torch.empty((self.num_experts, 1), dtype=torch.float32, device="meta"), requires_grad=False)
        self.down_proj_u = nn.Parameter(torch.empty((self.num_experts, self.expert_dim, 1), dtype=torch.int8, device="meta"), requires_grad=False)
        self.down_proj_v = nn.Parameter(torch.empty((self.num_experts, 1, self.hidden_size), dtype=torch.int8, device="meta"), requires_grad=False)
        self.down_proj_scale_u = nn.Parameter(torch.empty((self.num_experts, 1), dtype=torch.float32, device="meta"), requires_grad=False)
        self.down_proj_scale_v = nn.Parameter(torch.empty((self.num_experts, 1), dtype=torch.float32, device="meta"), requires_grad=False)
        self.gate_up_proj_bias = base.gate_up_proj_bias
        self.down_proj_bias = base.down_proj_bias

    def forward(self, hidden_states, router_indices=None, routing_weights=None):
        batch_size = hidden_states.shape[0]
        hidden_states = hidden_states.reshape(-1, self.hidden_size)
        next_states = torch.zeros_like(hidden_states, dtype=hidden_states.dtype, device=hidden_states.device)
        with torch.no_grad():
            expert_mask = F.one_hot(router_indices, num_classes=self.num_experts + 1).permute(2, 1, 0)
            expert_hit = torch.greater(expert_mask.sum(dim=(-1, -2)), 0).nonzero()
        for expert_tensor in expert_hit:
            expert_idx = int(expert_tensor[0].item())
            if expert_idx == self.num_experts:
                continue
            with torch.no_grad():
                _, token_idx = torch.where(expert_mask[expert_idx])
            current = hidden_states[token_idx]
            dtype = current.dtype
            gu_u = self.gate_up_proj_u[expert_idx].to(dtype=dtype) * self.gate_up_proj_scale_u[expert_idx].to(dtype=dtype).unsqueeze(0)
            gu_v = self.gate_up_proj_v[expert_idx].to(dtype=dtype) * self.gate_up_proj_scale_v[expert_idx].to(dtype=dtype).unsqueeze(1)
            gate_up = (current @ gu_u) @ gu_v + self.gate_up_proj_bias[expert_idx]
            gate, up = gate_up[..., ::2], gate_up[..., 1::2]
            gate = gate.clamp(max=self.limit)
            up = up.clamp(min=-self.limit, max=self.limit)
            glu = gate * torch.sigmoid(gate * self.alpha)
            activated = (up + 1) * glu
            down_u = self.down_proj_u[expert_idx].to(dtype=dtype) * self.down_proj_scale_u[expert_idx].to(dtype=dtype).unsqueeze(0)
            down_v = self.down_proj_v[expert_idx].to(dtype=dtype) * self.down_proj_scale_v[expert_idx].to(dtype=dtype).unsqueeze(1)
            out = (activated @ down_u) @ down_v + self.down_proj_bias[expert_idx]
            weighted = out * routing_weights[token_idx, expert_idx, None]
            next_states.index_add_(0, token_idx, weighted.to(hidden_states.dtype))
        return next_states.view(batch_size, -1, self.hidden_size)


def build_model():
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    cfg = GptOssConfig.from_pretrained(ROOT, local_files_only=True)
    # The candidate uses its own rank-1 factor format, not the source MXFP4 loader.
    if hasattr(cfg, "quantization_config"):
        cfg.quantization_config = None
    cfg.torch_dtype = torch.bfloat16
    with torch.device("meta"):
        model = GptOssForCausalLM(cfg)
    modules = dict(model.named_modules())
    replacements = 0
    for name, module in list(modules.items()):
        if not name:
            continue
        if isinstance(module, GptOssExperts):
            replacement = LowRankExperts(module)
        elif isinstance(module, GptOssTopKRouter):
            replacement = LowRankRouter(module)
        elif isinstance(module, nn.Embedding):
            replacement = LowRankEmbedding(module)
        elif isinstance(module, nn.Linear):
            replacement = LowRankLinear(module)
        else:
            continue
        parent_name, _, leaf = name.rpartition(".")
        setattr(modules[parent_name], leaf, replacement)
        replacements += 1
    if replacements < 200:
        raise RuntimeError(f"MODEL_MAPPING_INCOMPLETE:{replacements}")
    state = load_model_state(ROOT / "model.safetensors")
    missing, unexpected = model.load_state_dict(state, strict=True, assign=True)
    if missing or unexpected:
        raise RuntimeError("STATE_MAPPING_MISMATCH:" + json.dumps({"missing": missing[:25], "unexpected": unexpected[:25]}))
    rope_count = 0
    for module in model.modules():
        if module.__class__.__name__ == "GptOssRotaryEmbedding":
            inv_freq, attention_scaling = module.rope_init_fn(module.config, device=torch.device("cpu"))
            module.inv_freq = inv_freq
            module.original_inv_freq = inv_freq.clone()
            module.attention_scaling = attention_scaling
            rope_count += 1
    if rope_count < 1:
        raise RuntimeError("GPTOSS_ROPE_MODULE_NOT_MATERIALIZED")
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


def smoke_test(generate: bool = False, prompt: str = "Test", max_new_tokens: int = 1):
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("PROMPT_REQUIRED")
    if isinstance(max_new_tokens, bool) or not 1 <= int(max_new_tokens) <= 128:
        raise ValueError("MAX_NEW_TOKENS_OUT_OF_RANGE")
    started = time.monotonic()
    tokenizer = load_pretrained_with_compressed_tokenizer(ROOT, AutoTokenizer, local_files_only=True)
    model = build_model()
    enc = tokenizer(prompt, return_tensors="pt")
    with torch.inference_mode():
        out = model(input_ids=enc["input_ids"], attention_mask=enc.get("attention_mask"), use_cache=False)
    logits = out.logits
    if logits.ndim != 3 or logits.shape[0] != 1 or not torch.isfinite(logits).all():
        raise RuntimeError("NONFINITE_OR_MALFORMED_LOGITS")
    next_id = int(logits[0, -1].argmax().item())
    result = {"status": "PASS_MODEL_START_AND_FORWARD", "model_type": model.config.model_type,
              "vocab_size": int(model.config.vocab_size), "logits_shape": list(logits.shape),
              "finite_logits": True, "argmax_token_id": next_id,
              "elapsed_seconds": round(time.monotonic() - started, 3),
              "quality_equivalence": "NOT_ESTABLISHED_BY_SMOKE_TEST", "compression_rank": 1}
    if generate:
        # GPT-OSS is a chat-tuned model. Plainly tokenizing a user prompt omits
        # its serialized role/channel boundary and can produce non-conversational
        # continuations even when the forward pass is finite.
        rendered_prompt = prompt
        prompt_mode = "RAW_PROMPT_NO_TEMPLATE_AVAILABLE"
        if callable(getattr(tokenizer, "apply_chat_template", None)):
            messages = [{"role": "user", "content": prompt}]
            rendered = None
            last_error = None
            for template_kwargs in ({"enable_thinking": False}, {}):
                try:
                    candidate = tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True,
                        **template_kwargs,
                    )
                except Exception as exc:
                    last_error = type(exc).__name__
                    continue
                if isinstance(candidate, str) and candidate.strip():
                    rendered = candidate
                    prompt_mode = (
                        "CHAT_TEMPLATE_THINKING_DISABLED"
                        if template_kwargs.get("enable_thinking") is False
                        else "CHAT_TEMPLATE_DEFAULT"
                    )
                    break
            if rendered is None:
                raise RuntimeError("CHAT_TEMPLATE_RENDER_FAILED:" + str(last_error or "EMPTY_TEMPLATE"))
            rendered_prompt = rendered
        generation_enc = tokenizer(rendered_prompt, return_tensors="pt")
        with torch.inference_mode():
            generated = model.generate(
                generation_enc["input_ids"],
                attention_mask=generation_enc.get("attention_mask"),
                max_new_tokens=int(max_new_tokens),
                do_sample=False,
                use_cache=False,
            )
        prompt_length = int(generation_enc["input_ids"].shape[-1])
        count = int(generated.shape[-1] - prompt_length)
        if count < 1:
            raise RuntimeError("MODEL_GENERATED_NO_NEW_TOKENS")
        result["generation_status"] = "PASS_GENERATE"
        result["generation_prompt_mode"] = prompt_mode
        result["generation_input_token_count"] = prompt_length
        result["generated_token_count"] = count
        result["output_text"] = tokenizer.decode(
            generated[0, prompt_length:], skip_special_tokens=True
        )[:8192]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--generate-test", action="store_true")
    parser.add_argument("--task-json-stdin", action="store_true")
    args = parser.parse_args()
    if args.task_json_stdin:
        task = json.load(sys.stdin)
        if task.get("operation") != "generate_text":
            parser.error("Unsupported task operation")
        result = smoke_test(True, task.get("prompt", ""), int(task.get("max_new_tokens", 8)))
        result["status"] = "PASS_TASK_GENERATION"
    else:
        if not (args.smoke_test or args.generate_test):
            parser.error("Use --smoke-test, --generate-test, or --task-json-stdin")
        result = smoke_test(generate=args.generate_test)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] not in {"PASS_MODEL_START_AND_FORWARD", "PASS_TASK_GENERATION"}:
        raise SystemExit(1)
