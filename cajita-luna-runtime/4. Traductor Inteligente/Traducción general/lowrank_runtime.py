#!/usr/bin/env python3
"""Inference smoke runtime for a low-rank, INT8-factor SeamlessM4T v2 candidate."""
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
from transformers import AutoConfig, AutoProcessor, SeamlessM4Tv2Model

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

    @property
    def weight(self):
        # INT8 factor sentinel for generic HF layers that inspect .weight.dtype;
        # actual multiplication stays in forward() and never materializes dense weights.
        return self.weight_u

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
        u = F.embedding(ids, self.weight_u).to(dtype=torch.float32)
        u = u * self.scale_u.to(dtype=u.dtype)
        v = self.weight_v.to(dtype=u.dtype) * self.scale_v.to(dtype=u.dtype).unsqueeze(1)
        return torch.matmul(u, v)

class LowRankConv1d(nn.Module):
    def __init__(self, base, rank):
        super().__init__()
        self.in_channels, self.out_channels = base.in_channels, base.out_channels
        self.kernel_size, self.stride, self.padding = base.kernel_size, base.stride, base.padding
        self.dilation, self.groups, self.padding_mode = base.dilation, base.groups, base.padding_mode
        self.weight_u = nn.Parameter(torch.empty((self.out_channels, rank), dtype=torch.int8, device="meta"), requires_grad=False)
        self.weight_v = nn.Parameter(torch.empty((rank, (self.in_channels // self.groups) * self.kernel_size[0]), dtype=torch.int8, device="meta"), requires_grad=False)
        self.scale_u = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.scale_v = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.bias = base.bias
    def forward(self, x):
        u = self.weight_u.to(dtype=x.dtype) * self.scale_u.to(dtype=x.dtype).unsqueeze(0)
        v = self.weight_v.to(dtype=x.dtype) * self.scale_v.to(dtype=x.dtype).unsqueeze(1)
        k = self.kernel_size[0]
        if self.groups == self.in_channels == self.out_channels:
            if u.shape[1] != 1:
                raise RuntimeError("DEPTHWISE_CONV_REQUIRES_RANK_ONE")
            w = u[:, 0].reshape(self.out_channels, 1, 1) * v[0].reshape(1, 1, k)
            return F.conv1d(x, w, self.bias, self.stride, self.padding, self.dilation, self.groups)
        if self.groups != 1:
            raise RuntimeError("UNSUPPORTED_GROUPED_CONV1D:" + str(self.groups))
        v = v.reshape(v.shape[0], self.in_channels, k)
        if self.padding_mode != "zeros":
            pad = self.padding
            if isinstance(pad, str):
                raise RuntimeError("NONZERO_PADDING_MODE_WITH_STRING_PADDING")
            left = right = int(pad[0])
            x = F.pad(x, (left, right), mode=self.padding_mode)
            padding = 0
        else:
            padding = self.padding
        mid = F.conv1d(x, v, None, self.stride, padding, self.dilation, 1)
        u = u.unsqueeze(-1)
        return F.conv1d(mid, u, self.bias, 1, 0, 1, 1)

class LowRankConvTranspose1d(nn.Module):
    def __init__(self, base, rank):
        super().__init__()
        self.in_channels, self.out_channels = base.in_channels, base.out_channels
        self.kernel_size, self.stride, self.padding = base.kernel_size, base.stride, base.padding
        self.output_padding, self.groups, self.dilation = base.output_padding, base.groups, base.dilation
        self.padding_mode = base.padding_mode
        self.weight_u = nn.Parameter(torch.empty((base.in_channels, rank), dtype=torch.int8, device="meta"), requires_grad=False)
        self.weight_v = nn.Parameter(torch.empty((rank, (base.out_channels // base.groups) * base.kernel_size[0]), dtype=torch.int8, device="meta"), requires_grad=False)
        self.scale_u = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.scale_v = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.bias = base.bias

    def forward(self, x):
        if self.groups != 1:
            raise RuntimeError("UNSUPPORTED_LOW_RANK_CONV_TRANSPOSE_GROUPS:" + str(self.groups))
        if self.padding_mode != "zeros":
            raise RuntimeError("UNSUPPORTED_LOW_RANK_CONV_TRANSPOSE_PADDING_MODE:" + str(self.padding_mode))
        dtype = x.dtype
        u = self.weight_u.to(dtype=dtype) * self.scale_u.to(dtype=dtype).unsqueeze(0)
        v = self.weight_v.to(dtype=dtype) * self.scale_v.to(dtype=dtype).unsqueeze(1)
        mid = F.conv_transpose1d(x, u.unsqueeze(-1), None, stride=1, padding=0, output_padding=0, groups=1, dilation=1)
        weight_v = v.reshape(v.shape[0], self.out_channels, self.kernel_size[0])
        bias = self.bias.to(dtype=dtype) if self.bias is not None else None
        return F.conv_transpose1d(mid, weight_v, bias, self.stride, self.padding, self.output_padding, 1, self.dilation)


def load_candidate():
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    cfg = AutoConfig.from_pretrained(ROOT, local_files_only=True)
    if getattr(cfg, "model_type", None) != "seamless_m4t_v2":
        raise RuntimeError("MODEL_IDENTITY_MISMATCH")
    weights = load_model_state(ROOT / "model.safetensors")
    with torch.device("meta"):
        model = SeamlessM4Tv2Model(cfg)
    modules = dict(model.named_modules())
    factorized = 0

    def factor_rank(name, u_dim0, v_dim1):
        u = weights.get(name + ".weight_u")
        v = weights.get(name + ".weight_v")
        if u is None or v is None:
            raise RuntimeError("FACTOR_WEIGHTS_MISSING:" + name)
        if u.ndim != 2 or v.ndim != 2 or u.shape[0] != u_dim0 or v.shape[1] != v_dim1 or u.shape[1] != v.shape[0]:
            raise RuntimeError("FACTOR_SHAPE_MISMATCH:" + name + ":" + str(tuple(u.shape)) + ":" + str(tuple(v.shape)))
        return int(u.shape[1])

    for name, module in list(modules.items()):
        if not name:
            continue
        if isinstance(module, nn.Embedding) and name + ".weight_u" in weights:
            rank_i = factor_rank(name, module.num_embeddings, module.embedding_dim)
            replacement = LowRankEmbedding(module, rank_i)
        elif isinstance(module, nn.Linear) and name + ".weight_u" in weights:
            rank_i = factor_rank(name, module.out_features, module.in_features)
            replacement = LowRankLinear(module, rank_i)
        elif isinstance(module, nn.Conv1d) and name + ".weight_u" in weights:
            rank_i = factor_rank(name, module.out_channels, (module.in_channels // module.groups) * module.kernel_size[0])
            replacement = LowRankConv1d(module, rank_i)
        elif isinstance(module, nn.ConvTranspose1d) and name + ".weight_u" in weights:
            rank_i = factor_rank(name, module.in_channels, (module.out_channels // module.groups) * module.kernel_size[0])
            replacement = LowRankConvTranspose1d(module, rank_i)
        else:
            continue
        parent_name, _, leaf = name.rpartition(".")
        setattr(modules[parent_name], leaf, replacement)
        factorized += 1
    if factorized < 300:
        raise RuntimeError("MODEL_MAPPING_INCOMPLETE:" + str(factorized))
    # The compact format stores tied embedding/head factors once (shared.*)
    # and intentionally omits four duplicated dense .weight aliases.
    # Accept only this exact missing-key set; every other mismatch fails closed.
    missing, unexpected = model.load_state_dict(weights, strict=False, assign=True)
    expected_alias_missing = {
        "text_encoder.embed_tokens.weight",
        "text_decoder.embed_tokens.weight",
        "lm_head.weight",
        "t2u_model.lm_head.weight",
    }
    if set(missing) != expected_alias_missing or unexpected:
        raise RuntimeError("STATE_MAPPING_MISMATCH:" + json.dumps({"missing": sorted(missing), "unexpected": unexpected[:20]}))
    if not bool(getattr(cfg, "tie_word_embeddings", False)):
        raise RuntimeError("TIED_WEIGHT_CONFIG_NOT_DECLARED")

    # Bind the two text embeddings to the single compact shared embedding.
    model.text_encoder.embed_tokens = model.shared
    model.text_decoder.embed_tokens = model.shared

    # Recreate output heads as low-rank linears tied to their source embeddings.
    def tie_lowrank_head(path, base_head, source_embedding):
        if not isinstance(source_embedding, LowRankEmbedding):
            raise RuntimeError("TIED_SOURCE_NOT_LOW_RANK:" + path)
        rank_i = int(source_embedding.weight_u.shape[1])
        tied = LowRankLinear(base_head, rank_i)
        tied.weight_u = source_embedding.weight_u
        tied.weight_v = source_embedding.weight_v
        tied.scale_u = source_embedding.scale_u
        tied.scale_v = source_embedding.scale_v
        if tied.out_features != source_embedding.num_embeddings or tied.in_features != source_embedding.embedding_dim:
            raise RuntimeError("TIED_HEAD_SHAPE_MISMATCH:" + path)
        return tied

    model.lm_head = tie_lowrank_head("lm_head", model.lm_head, model.shared)
    t2u_embedding = model.t2u_model.model.decoder.embed_tokens
    model.t2u_model.lm_head = tie_lowrank_head("t2u_model.lm_head", model.t2u_model.lm_head, t2u_embedding)

    for name, module in {
        "shared": model.shared,
        "text_encoder.embed_tokens": model.text_encoder.embed_tokens,
        "text_decoder.embed_tokens": model.text_decoder.embed_tokens,
        "lm_head": model.lm_head,
        "t2u_model.model.decoder.embed_tokens": t2u_embedding,
        "t2u_model.lm_head": model.t2u_model.lm_head,
    }.items():
        params = list(module.parameters())
        if not params or any(getattr(param, "is_meta", False) for param in params):
            raise RuntimeError("TIED_COMPONENT_NOT_MATERIALIZED:" + name)
    if model.text_encoder.embed_tokens is not model.shared or model.text_decoder.embed_tokens is not model.shared:
        raise RuntimeError("SHARED_EMBEDDING_ALIAS_NOT_BOUND")
    if model.lm_head.weight_u is not model.shared.weight_u or model.lm_head.weight_v is not model.shared.weight_v:
        raise RuntimeError("OUTPUT_HEAD_FACTORS_NOT_TIED")
    if model.t2u_model.lm_head.weight_u is not t2u_embedding.weight_u or model.t2u_model.lm_head.weight_v is not t2u_embedding.weight_v:
        raise RuntimeError("T2U_OUTPUT_HEAD_FACTORS_NOT_TIED")

    # Meta-device construction leaves non-persistent sinusoidal position buffers
    # unmaterialized; these are deterministic functions of shape, not model weights.
    positional_buffers = 0
    for module in model.modules():
        if type(module).__name__ == "SeamlessM4Tv2SinusoidalPositionalEmbedding":
            weights_buf = getattr(module, "weights", None)
            if weights_buf is not None and getattr(weights_buf, "is_meta", False):
                n_positions = int(weights_buf.shape[0])
                module.weights = module.get_embedding(n_positions, int(module.embedding_dim), module.padding_idx)
                if getattr(module.weights, "is_meta", False):
                    raise RuntimeError("POSITION_BUFFER_REMAINS_META")
                positional_buffers += 1
    if positional_buffers == 0:
        raise RuntimeError("NO_META_POSITION_BUFFERS_RECONSTRUCTED")

    model.eval()
    return model

def smoke_test(text="Hello world.", src_lang="eng", tgt_lang="spa", max_new_tokens=4):
    t0 = time.monotonic()
    if not isinstance(text, str) or not text.strip():
        raise ValueError("TRANSLATION_TEXT_REQUIRED")
    if isinstance(max_new_tokens, bool) or not 1 <= int(max_new_tokens) <= 128:
        raise ValueError("MAX_NEW_TOKENS_OUT_OF_RANGE")
    processor = load_pretrained_with_compressed_tokenizer(ROOT, AutoProcessor, local_files_only=True)
    model = load_candidate()
    tok = getattr(processor, "tokenizer", None)
    if tok is None:
        raise RuntimeError("TOKENIZER_REQUIRED_FOR_TEXT_LANGUAGE_MAP")
    decoder_map = {}
    for token in getattr(tok, "additional_special_tokens", None) or []:
        if isinstance(token, str) and token.startswith("__") and token.endswith("__") and len(token) > 4:
            lang = token[2:-2]
            token_id = tok.convert_tokens_to_ids(token)
            if isinstance(token_id, int) and token_id >= 0 and lang:
                decoder_map[lang] = token_id
    if not decoder_map or src_lang not in decoder_map or tgt_lang not in decoder_map:
        raise RuntimeError("PACKAGED_TOKENIZER_LANGUAGE_MAP_INCOMPLETE")
    model.generation_config.text_decoder_lang_to_code_id = decoder_map
    inputs = processor(text=text, src_lang=src_lang, return_tensors="pt")
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            tgt_lang=tgt_lang,
            max_new_tokens=int(max_new_tokens),
            min_new_tokens=min(3, int(max_new_tokens)),
            repetition_penalty=1.12,
            no_repeat_ngram_size=3,
            renormalize_logits=True,
            do_sample=False,
            generate_speech=False,
        )
    seq = generated.sequences if hasattr(generated, "sequences") else generated
    if not isinstance(seq, torch.Tensor) or seq.ndim != 2 or seq.shape[0] != 1:
        raise RuntimeError("MALFORMED_TEXT_TRANSLATION_OUTPUT:" + type(generated).__name__)
    decoded = processor.batch_decode(seq, skip_special_tokens=True)
    return {"status":"PASS_TEXT_TRANSLATION_GENERATION","model_type":model.config.model_type,
            "input_token_count":int(inputs["input_ids"].shape[-1]),"generated_token_count":int(seq.shape[-1]),
            "output_text":decoded[0][:8192] if decoded else "", "src_lang":src_lang, "tgt_lang":tgt_lang,
            "elapsed_seconds":round(time.monotonic()-t0,3),"quality_equivalence":"NOT_ESTABLISHED_BY_SMOKE_TEST"}

if __name__ == "__main__":
    import argparse, sys
    parser=argparse.ArgumentParser()
    parser.add_argument("--smoke-test",action="store_true")
    parser.add_argument("--task-json-stdin",action="store_true")
    args=parser.parse_args()
    if args.task_json_stdin:
        task=json.load(sys.stdin)
        if task.get("operation")!="translate_text": parser.error("Unsupported task operation")
        result=smoke_test(task.get("text",""),task.get("src_lang","eng"),task.get("tgt_lang","spa"),int(task.get("max_new_tokens",8)))
    else:
        if not args.smoke_test: parser.error("Use --smoke-test or --task-json-stdin")
        result=smoke_test()
    print(json.dumps(result,indent=2,ensure_ascii=False))
