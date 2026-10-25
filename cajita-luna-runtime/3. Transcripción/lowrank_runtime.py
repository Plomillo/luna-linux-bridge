#!/usr/bin/env python3
"""Offline smoke runtime for a low-rank INT8-factor Whisper transcription candidate."""
from __future__ import annotations
import json, pathlib, time, wave
import numpy as np
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
    weights=load_model_state(ROOT/"model.safetensors")
    missing,unexpected=model.load_state_dict(weights,strict=True,assign=True)
    if missing or unexpected:
        raise RuntimeError("STATE_MAPPING_MISMATCH:"+json.dumps({"missing":missing[:30],"unexpected":unexpected[:30]}))
    model = model.float()
    model.eval()
    return model

def load_waveform(audio_path):
    path = pathlib.Path(audio_path)
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("AUDIO_FILE_MISSING_OR_SYMLINK")
    with wave.open(str(path), "rb") as stream:
        channels, width, rate, frame_count = stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getnframes()
        if stream.getcomptype() != "NONE" or width != 2:
            raise RuntimeError("AUDIO_REQUIRES_UNCOMPRESSED_PCM16_WAV")
        if rate <= 0 or channels not in (1, 2) or frame_count <= 0:
            raise RuntimeError("AUDIO_WAV_FORMAT_INVALID")
        if frame_count > rate * 60:
            raise RuntimeError("AUDIO_DURATION_OVER_60_SECONDS")
        raw = stream.readframes(frame_count)
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if channels == 2:
        samples = samples.reshape(-1, 2).mean(axis=1)
    if rate != 16000:
        source_times = np.arange(samples.size, dtype=np.float64) / float(rate)
        count = max(1, int(round(samples.size * 16000 / rate)))
        target_times = np.arange(count, dtype=np.float64) / 16000.0
        samples = np.interp(target_times, source_times, samples).astype(np.float32)
    return samples.astype(np.float32), rate


def smoke_test(audio_path=None, max_new_tokens=4):
    t0 = time.monotonic()
    if isinstance(max_new_tokens, bool) or not 1 <= int(max_new_tokens) <= 128:
        raise ValueError("MAX_NEW_TOKENS_OUT_OF_RANGE")
    original_rate = 16000
    if audio_path:
        audio, original_rate = load_waveform(audio_path)
    else:
        audio = np.zeros(16000, dtype=np.float32)
    processor = load_pretrained_with_compressed_tokenizer(ROOT, WhisperProcessor, local_files_only=True)
    model = load_candidate()
    inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
    inputs["input_features"] = inputs["input_features"].to(dtype=torch.float32)
    generate_kwargs = {"max_new_tokens": int(max_new_tokens), "do_sample": False}
    if audio_path:
        # This candidate carries a legacy forced_decoder_ids value in its
        # generation config. Transformers rejects passing language/task while
        # that legacy field is set. Use the explicit language/task arguments,
        # and remove only the conflicting generation-config override.
        # Model weights and token identities remain unchanged.
        if getattr(model.generation_config, "forced_decoder_ids", None) is not None:
            model.generation_config.forced_decoder_ids = None
        generate_kwargs["language"] = "en"
        generate_kwargs["task"] = "transcribe"
    with torch.inference_mode():
        generated = model.generate(**inputs, **generate_kwargs)
    if not isinstance(generated, torch.Tensor) or generated.ndim != 2 or generated.shape[0] != 1 or generated.shape[-1] < 1:
        raise RuntimeError("MALFORMED_TRANSCRIPTION_OUTPUT")
    decoded = processor.batch_decode(generated, skip_special_tokens=True)
    return {"status": "PASS_TRANSCRIPTION_GENERATION", "model_type": model.config.model_type,
            "input_feature_shape": list(inputs["input_features"].shape),
            "generated_token_count": int(generated.shape[-1]),
            "output_text": decoded[0][:8192] if decoded else "",
            "original_sample_rate_hz": original_rate, "processed_sample_rate_hz": 16000,
            "duration_seconds": round(len(audio) / 16000, 3),
            "elapsed_seconds": round(time.monotonic() - t0, 3),
            "quality_equivalence": "NOT_ESTABLISHED_BY_SMOKE_TEST"}

if __name__=="__main__":
    import argparse, sys
    parser=argparse.ArgumentParser()
    parser.add_argument("--smoke-test",action="store_true")
    parser.add_argument("--task-json-stdin",action="store_true")
    args=parser.parse_args()
    if args.task_json_stdin:
        task=json.load(sys.stdin)
        if task.get("operation")!="transcribe_audio": parser.error("Unsupported task operation")
        result=smoke_test(task.get("audio_path"),int(task.get("max_new_tokens",8)))
    else:
        if not args.smoke_test: parser.error("Use --smoke-test or --task-json-stdin")
        result=smoke_test()
    print(json.dumps(result,indent=2,ensure_ascii=False))
