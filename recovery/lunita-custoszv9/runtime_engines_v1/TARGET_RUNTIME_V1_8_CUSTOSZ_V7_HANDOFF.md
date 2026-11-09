# Lunita v1.8 target acceptance — CUSTOSZ_V7 handoff

Status: REQUIRED_BEFORE_G23_S32; NOT_YET_EXECUTED_ON_TARGET.

This handoff does not authorize Desktop Commander or an ordinary shell session to mutate the target rootfs. It is an execution contract for the already-authorized CUSTOSZ_V7 worker only.

## Preconditions

1. The additive overlay has been applied by CUSTOSZ_V7 after a valid, hash-verified checkpoint.
2. /opt/lunita/engines/runtime_engines_v1/OVERLAY_APPLY_RECEIPT.json exists and binds the beta-v1.7 launcher hash, every top-level payload file, the vendored site-packages tree, and the E04 model-cache tree.
3. LUNITA_E04_ONNX_QUANTIZATION_RECEIPT.json exists next to the pinned E04 model in the overlay cache. The receipt must show ONNX Runtime CPU load PASS, INT8 initializers, semantic thresholds, 100% top-1 retrieval agreement, and the model-size threshold. Any absent or mismatched receipt blocks target acceptance.
4. The existing Qwen GGUF and llama.cpp runtime are present at the paths pinned in engine_runtime_v1.py.
5. No other target-runtime acceptance worker is running.

## Authorized invocation

The CUSTOSZ_V7 worker must set its worker version and direct the evidence receipt into the existing append-only operator output tree:

    export CUSTOSZ_WORKER_VERSION=CUSTOSZ_V7
    export LUNITA_TARGET_RUNTIME_RECEIPT_DIR='/home/diegoignacionorambuenamiranda/Proyectos/1. PROYECTOS PRIORITARIOS/5. CUSTOSZ/0. CUSTOSZ  - OPERADOR/CUSTOSZ_CONTINUITY_V1/state/worker_outputs/lunita_target_runtime_acceptance'
    export PYTHONPATH='/opt/lunita/engines/runtime_engines_v1/vendor/python3.12/site-packages:/opt/lunita/engines/runtime_engines_v1'
    export LUNITA_FASTEMBED_CACHE='/opt/lunita/engines/runtime_engines_v1/model-cache/fastembed'
    export LUNITA_VECTOR_DB_PATH="$HOME/.local/state/lunita/vectors"
    export LUNITA_ENGINE_AUDIT_LOG="$HOME/.local/state/lunita/audit/engine-execution.jsonl"
    export HF_HUB_OFFLINE=1
    export TRANSFORMERS_OFFLINE=1
    export HF_HUB_DISABLE_TELEMETRY=1
    python3.12 /opt/lunita/engines/runtime_engines_v1/target_runtime_acceptance_v1.py

The worker must preserve the process exit code and JSON output. A successful target run writes a unique LUNITA_TARGET_RUNTIME_ACCEPTANCE_*.json receipt under the destination directory. It records the applied overlay and launcher integrity, exact model and INT8 receipt hashes, E01 generated output from the actual local Qwen weights, the E02–E15 acceptance suite with zero skipped tests, legacy Brújula/R 4.6.1/Jamovi/JASP/fault-injection smoke results, worker version and candidate identity, and certification=NOT_GRANTED.

## Postconditions

1. The receipt must report PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED. A BLOCKED_* result is retained as evidence and does not advance G23.
2. The CUSTOSZ_LUNITA_STABILITY_CERT_LANE must consume that exact receipt, re-hash it, and add the check target_v1_8_runtime_acceptance_e01_e15_int8 to the independent report.
3. Only after target acceptance, real JASP fixture regression, complete rootfs inventory and dependency closure, and every other independent check pass may G23 be considered for S32. S32 is the separate issuance authority. G24 must remain separate.
4. No status in this handoff certifies frozen G06, canonical G08, or any other canonical identity. No automatic certification propagation is permitted.

Do not run the command as Desktop Commander, as an unaffiliated user session, or from GitHub-hosted CI and then relabel the result as target evidence.