# LOUKSNAPG2 — GPU repair stack foundation V1

**Status:** Stack configuration added; GPU execution and model repair are not certified.
**Integration branch:** `repair/louksnapg2-gpu-foundation-20261103`
**Parent:** `repair/louksnapg2-operational-engines-20261103`
**Policy:** `EXTEND_DO_NOT_REPLACE / APPEND_ONLY / FAIL_CLOSED`

## 1. Pinned software stack

The GPU workflow uses `nvcr.io/nvidia/nemo:26.06`. NVIDIA's NeMo Framework 26.06 compatibility table records:

| Component | Version |
|---|---:|
| PyTorch | 2.12.0a0+0291f960b6 |
| Megatron Core | 0.18.0 |
| Megatron Bridge | 0.5.0 |
| Transformer Engine | 2.16 |
| NVIDIA ModelOpt | 0.44.0 |
| CUDA | 13.2.1.009 |
| Transformers | 5.8.1 |

Official references:
- [NeMo software component versions](https://docs.nvidia.com/nemo/megatron-bridge/latest/releases/software-versions.html)
- [Megatron Bridge supported models](https://docs.nvidia.com/nemo/megatron-bridge/latest/models/README.html)
- [GPT-OSS 120B verified configurations](https://docs.nvidia.com/nemo/megatron-bridge/latest/models/gpt_oss/gpt-oss-120b.html)
- [Qwen3 model support and recipes](https://docs.nvidia.com/nemo/megatron-bridge/latest/models/qwen/qwen.html)

NVIDIA documents GPT-OSS 120B LoRA/PEFT on 8 H100 GPUs and full SFT on 32 H100 GPUs. The Qwen3 8B–14B LoRA recipe family is documented for an 8-GPU node. These are model-family references, not proof that this repository's weights, adapter, dataset or evaluation are ready.

## 2. Framework assignment

- **GPT-OSS 120B:** NeMo Megatron Bridge; architecture-aware import/export and LoRA/PEFT. Current adapter status: `NOT_IMPLEMENTED`.
- **Qwen3-14B:** NeMo Megatron Bridge; model-native Qwen3 mapping, LoRA/PEFT and held-out reasoning suite. Current adapter status: `NOT_IMPLEMENTED`.
- **Whisper large-v3-turbo:** Transformers/PyTorch; new ASR repair path and held-out WER are required. Current status: `EXPERIMENTAL_FAILED`.
- **SeamlessM4T v2 Large:** Transformers/PyTorch; shared embedding/head handling and bilingual evaluation are required. Current status: `NOT_IMPLEMENTED`. Upstream license is CC-BY-NC-4.0; non-commercial restriction must be retained.
- **Granite Docling 258M:** Transformers and Docling evaluation; paired FP16 baseline, processor parity and document-field tests are required. Current status: `EXPERIMENTAL_FAILED`.

This is intentionally not a single universal repair adapter. A framework supporting a model family does not itself repair a damaged compact representation.

## 3. Runner requirements

The manual workflow expects a dedicated self-hosted Linux x86-64 runner with:
- Docker Engine and NVIDIA Container Toolkit;
- a working `nvidia-smi` command and CUDA GPU passthrough into Docker;
- access to `nvcr.io` to pull the official NeMo image;
- repository secret `NGC_API_KEY` (used only for registry login).

For GPT-OSS 120B, the documented PEFT profile is 8 × H100 80 GB. For Qwen3-14B, the published LoRA recipe family uses 8 GPUs; exact per-card VRAM suitability remains to be measured. The other three models are assigned a GPU requirement but their per-model capacity profiles are explicitly unverified.

No remote GPU host was found/confirmed by the current repository inspection. The workflow does not provision paid infrastructure and does not launch paid Hugging Face jobs. It will wait for an appropriately labelled self-hosted runner only when manually dispatched.

## 4. Workflow behavior

`.github/workflows/louksnapg2-gpu-repair-stack.yml` provides:
1. automatic CPU-only static contract tests when this branch changes;
2. manual GPU preflight on a `self-hosted, linux, x64, gpu` runner;
3. image identity, CUDA, GPU count/VRAM, PyTorch, Transformers and Megatron Bridge evidence;
4. a JSON diagnostic artifact tied to the exact Git commit.

`mode=preflight` is read-only. `mode=repair` is deliberately fail-closed until the selected model has an executable adapter, a pinned upstream model revision, a pinned training-data revision and the required independent evaluation. It does not invoke an auxiliary engine or label a preflight as a repair.

## 5. Source and distribution boundaries

The existing runtime manifest records compact model representations; it does not establish full upstream checkpoint availability or semantic equivalence. Original and upstream checkpoints, datasets, optimizer state and training scratch must remain outside Git and outside the runtime package. The workflow mounts the repository read-only inside the container.

The 490,000,000-byte limit remains unchanged. It applies to the runtime distribution, not the external GPU workspace. Only separately hashed candidate overlays or distilled candidates may later be considered for packaging, and only if the complete runtime package stays below the exact limit.

A simple lower bound illustrates why all five original models cannot be embedded in that package: their combined parameter count is roughly 137 billion. Even a theoretical 4-bit representation needs roughly 68.5 GB for weight values alone, before scales, metadata, tokenizers, processors or runtime. That is over 100 times the 490 MB cap. The feasible design is external model storage/inference or genuinely smaller distilled candidates; the latter cannot be called equivalent without held-out proof.

## 6. Required next implementation work

1. Obtain and hash-pin the five upstream model revisions and the appropriate licensed training/calibration corpora.
2. Implement five independent, architecture-specific repair adapters. No adapter is registered as ready by this commit.
3. Restore the paired baseline inference for each original upstream checkpoint using the exact same processor, tokenizer, task settings and fixtures as the compact candidate.
4. Run domain-specific calibration/repair experiments on the remote GPU node; write candidates to isolated external scratch.
5. Evaluate the exact candidate package against the existing 13 acceptance cases and each domain's held-out suite.
6. Run independent G23, then G24, then rollback and non-regression checks.

## 7. Current evidence state

- GPU stack software/image: configured in repository; not pulled on a real GPU host by this commit.
- GPU runner: not confirmed.
- GPU preflight: not executed.
- Repair adapters: 0/5 ready.
- Model training/inference executed by this commit: no.
- Candidate weights written: no.
- Original weights mutated: no.
- Canonical promotion/global certification: not authorized.
