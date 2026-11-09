# Lunita v1.8 — direct target acceptance

Status: REQUIRED_BEFORE_INDEPENDENT_VALIDATION; NOT_YET_EXECUTED_ON_TARGET.

This procedure validates the actual installed candidate. It does not delegate execution to CUSTOSZ, Kestra, GitHub-hosted CI, or another orchestration service. It does not grant certification by itself.

## Preconditions

1. The additive overlay is present at `$LUNITA_ROOT/engines/runtime_engines_v1`.
2. `OVERLAY_APPLY_RECEIPT.json` exists and its source-file, vendored dependency, and E04 model-cache manifests match the installed bytes.
3. The installed legacy v1.7 launcher still matches the pinned SHA-256 in `target_runtime_acceptance_v1.py`.
4. The measured E04 INT8 quantization receipt and its pinned ONNX model are present.
5. The existing Qwen GGUF and executable llama.cpp runtime are present under the candidate root.
6. No other acceptance execution is modifying the candidate during the test.

## Direct invocation

Set the target root and the shared receipt directory. The target validator and the independent certification lane use the same default receipt location; override it only when both processes receive the same value.

```bash
export LUNITA_ROOT=/opt/lunita
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
export LUNITA_TARGET_RUNTIME_RECEIPT_DIR="${XDG_STATE_HOME}/lunita/runtime_validation"
export PYTHONPATH="$LUNITA_ROOT/engines/runtime_engines_v1/vendor/python3.12/site-packages:$LUNITA_ROOT/engines/runtime_engines_v1"
export LUNITA_FASTEMBED_CACHE="$LUNITA_ROOT/engines/runtime_engines_v1/model-cache/fastembed"
export LUNITA_VECTOR_DB_PATH="$XDG_STATE_HOME/lunita/vectors"
export LUNITA_ENGINE_AUDIT_LOG="$XDG_STATE_HOME/lunita/audit/engine-execution.jsonl"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1

python3.12 "$LUNITA_ROOT/engines/runtime_engines_v1/target_runtime_acceptance_v1.py"
```

A successful process must exit 0 and emit `PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED`. It creates a unique JSON receipt in `LUNITA_TARGET_RUNTIME_RECEIPT_DIR`. A failure exits 2 and retains a `BLOCKED_TARGET_RUNTIME_ACCEPTANCE` receipt. Do not edit either receipt to change its status.

## Required functional evidence

The receipt is accepted only when all of the following are demonstrated against the installed candidate:

- exact integrity of the additive overlay and preserved v1.7 launcher;
- installed dependency inventory complete;
- E04 INT8 ONNX model loads, meets its semantic and size thresholds, and preserves all required top-1 retrieval decisions;
- E01 performs an actual local Qwen inference through the installed llama.cpp runtime and creates a hash-bound provenance audit event;
- the engine acceptance suite covers E02–E15, has zero failures and zero skipped tests, and includes the complete fourteen-command routing matrix;
- Brújula, R 4.6.1, Jamovi, JASP and fault-injection legacy smoke commands all return zero.

The runner does not issue S32, G23, G24, or a stable release.

## Independent certification

After a valid target receipt exists, run the existing independent certification lane against the same candidate state. It must still prove the complete rootfs inventory and dependency closure, all four packaged JASP non-regression cases (`flatpak_launch`, `reliability`, `weight_gain`, `death_penalty_roundtrip`), the hash-bound runtime report, and the independent S32 receipt. G23 and G24 remain separate gates.

No test is replaced by a mock, no fixture or reference result is rewritten to force a pass, and no historical receipt may override a newer failure.
