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
from safetensors.torch import load_file
from transformers import AutoTokenizer, GptOssConfig, GptOssForCausalLM
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
    state = load_file(str(ROOT / "model.safetensors"), device="cpu")
    missing, unexpected = model.load_state_dict(state, strict=True, assign=True)
    if missing or unexpected:
        raise RuntimeError("STATE_MAPPING_MISMATCH:" + json.dumps({"missing": missing[:25], "unexpected": unexpected[:25]}))
    model.eval()
    return model


def smoke_test(generate: bool = False):
    started = time.monotonic()
    tokenizer = AutoTokenizer.from_pretrained(ROOT, local_files_only=True)
    model = build_model()
    enc = tokenizer("Test", return_tensors="pt")
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
              "quality_equivalence": "NOT_ESTABLISHED_BY_SMOKE_TEST",
              "compression_rank": 1}
    if generate:
        with torch.inference_mode():
            generated = model.generate(enc["input_ids"], max_new_tokens=1, do_sample=False, use_cache=False)
        result["generation_status"] = "PASS_GENERATE_ONE_TOKEN" if generated.shape[-1] == enc["input_ids"].shape[-1] + 1 else "FAIL_GENERATION_LENGTH"
        result["generated_token_count"] = int(generated.shape[-1] - enc["input_ids"].shape[-1])
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--generate-test", action="store_true")
    args = parser.parse_args()
    if not (args.smoke_test or args.generate_test):
        parser.error("Use --smoke-test or --generate-test")
    result = smoke_test(generate=args.generate_test)
    print(json.dumps(result, indent=2))
    if result["status"] != "PASS_MODEL_START_AND_FORWARD" or result.get("generation_status", "").startswith("FAIL"):
        raise SystemExit(1)

[executed on device: LOUKSNA (98c2b7f6-ee30-4f31-9444-06f7ba58f353)]