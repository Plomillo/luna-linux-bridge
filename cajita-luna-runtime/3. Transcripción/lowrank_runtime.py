#!/usr/bin/env python3
"""Offline smoke runtime for a low-rank INT8-factor Whisper transcription candidate."""
from __future__ import annotations
import json, pathlib, time
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from safetensors.torch import load_file
from transformers import AutoConfig, WhisperForConditionalGeneration, WhisperProcessor

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
        bias = self.bias.to(dtype=x.dtype) if self.bias is not None else None
        return F.linear(F.linear(x, v), u, bias)

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
        bias = self.bias.to(dtype=x.dtype) if self.bias is not None else None
        if self.groups == self.in_channels == self.out_channels:
            if u.shape[1] != 1:
                raise RuntimeError("DEPTHWISE_CONV_REQUIRES_RANK_ONE")
            w = u[:,0].reshape(self.out_channels,1,1) * v[0].reshape(1,1,k)
            return F.conv1d(x,w,bias,self.stride,self.padding,self.dilation,self.groups)
        if self.groups != 1:
            raise RuntimeError("UNSUPPORTED_GROUPED_CONV1D:"+str(self.groups))
        v = v.reshape(v.shape[0], self.in_channels, k)
        if self.padding_mode != "zeros":
            pad = self.padding
            if isinstance(pad, str):
                raise RuntimeError("NONZERO_PADDING_MODE_WITH_STRING_PADDING")
            left = right = int(pad[0] if isinstance(pad, tuple) else pad)
            x = F.pad(x,(left,right),mode=self.padding_mode)
            padding = 0
        else:
            padding = self.padding
        mid = F.conv1d(x,v,None,self.stride,padding,self.dilation,1)
        return F.conv1d(mid,u.unsqueeze(-1),bias,1,0,1,1)

def load_candidate():
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    cfg = AutoConfig.from_pretrained(ROOT, local_files_only=True)
    if getattr(cfg,"model_type",None)!="whisper":
        raise RuntimeError("MODEL_IDENTITY_MISMATCH")
    meta = json.loads((ROOT/"compression_metadata.json").read_text(encoding="utf-8"))
    rank = int(meta["rank"])
    with torch.device("meta"):
        model = WhisperForConditionalGeneration(cfg)
    modules = dict(model.named_modules())
    factorized = 0
    for name,module in list(modules.items()):
        if not name or name in ("model.encoder.embed_positions", "model.decoder.embed_positions"):
            continue
        if isinstance(module, nn.Embedding):
            replacement=LowRankEmbedding(module,rank)
        elif isinstance(module,nn.Linear):
            replacement=LowRankLinear(module,rank)
        elif isinstance(module,nn.Conv1d):
            replacement=LowRankConv1d(module,rank)
        else:
            continue
        parent_name,_,leaf=name.rpartition(".")
        setattr(modules[parent_name],leaf,replacement)
        factorized+=1
    if factorized < 200:
        raise RuntimeError("MODEL_MAPPING_INCOMPLETE:"+str(factorized))
    weights=load_file(str(ROOT/"model.safetensors"),device="cpu")
    missing,unexpected=model.load_state_dict(weights,strict=True,assign=True)
    if missing or unexpected:
        raise RuntimeError("STATE_MAPPING_MISMATCH:"+json.dumps({"missing":missing[:30],"unexpected":unexpected[:30]}))
    model = model.float()
    model.eval()
    return model

def smoke_test():
    t0=time.monotonic()
    processor=WhisperProcessor.from_pretrained(ROOT,local_files_only=True)
    model=load_candidate()
    audio=np.zeros(16000,dtype=np.float32)
    inputs=processor(audio,sampling_rate=16000,return_tensors="pt")
    inputs["input_features"] = inputs["input_features"].to(dtype=torch.float32)
    with torch.inference_mode():
        generated=model.generate(**inputs,max_new_tokens=4)
    if not isinstance(generated,torch.Tensor) or generated.ndim!=2 or generated.shape[0]!=1:
        raise RuntimeError("MALFORMED_TRANSCRIPTION_OUTPUT")
    decoded=processor.batch_decode(generated,skip_special_tokens=True)
    return {"status":"PASS_TRANSCRIPTION_GENERATION","model_type":model.config.model_type,
            "input_feature_shape":list(inputs["input_features"].shape),
            "generated_token_count":int(generated.shape[-1]),
            "decoded":decoded[0] if decoded else "",
            "elapsed_seconds":round(time.monotonic()-t0,3),
            "quality_equivalence":"NOT_ESTABLISHED_BY_SMOKE_TEST"}
if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--smoke-test",action="store_true")
    args=parser.parse_args()
    if not args.smoke_test: parser.error("Use --smoke-test")
    print(json.dumps(smoke_test(),indent=2,ensure_ascii=False))
