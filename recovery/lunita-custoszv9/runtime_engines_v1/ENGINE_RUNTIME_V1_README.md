# Louksna E01–E15 — additive runtime implementation candidate

Status: `IMPLEMENTATION_CANDIDATE_PENDING_TARGET_DEPLOYMENT_AND_INDEPENDENT_CERTIFICATION`.

This directory adds adapters for existing E01–E15 identities. It does not add, rename, merge, replace, or reassign canonical engines, agents, commands, blocks, axioms, or CFE identifiers. Luna remains present in every command route. The exact 14-command team-to-engine routing matrix is in `engine_assignments_v1.json`. Louksna does not define an independent one-agent-to-one-engine ownership table; the runtime enforces the canonical team and engine set together for each command.

## Implementation
- E01 LLM: existing candidate-rootfs Qwen3-0.6B GGUF through the bundled llama.cpp runtime; no placeholder model.
- E02 NLP: deterministic Spanish tokenizer, sentence segmentation, stop-word lexicon, morphology/lemma rules, heuristic POS and proper-name candidate detection. It explicitly does not claim statistical dependency parsing; named-entity candidates remain heuristic. The runtime exposes those limitations in every result.
- E03 RAG: source-bound retrieval/context assembly, delegating response generation to E01.
- E04 embeddings: FastEmbed `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384-dimensional multilingual transformer embeddings. CI creates a dynamic per-channel INT8 ONNX candidate only when mean cosine ≥0.995, minimum cosine ≥0.985, and the Spanish retrieval corpus keeps 100% top-1 decisions; its hash-bound receipt is required on target.
- E05 vector search: Qdrant embedded local index, memory or persistent path.
- E06 knowledge graph: pure-Python directed multigraph with adjacency indexes, multi-edge relation metadata and breadth-first shortest-path traversal.
- E07 RDF: RDFLib parsing, serialization and SPARQL.
- E08 OWL: explicit OWL vocabulary/profile validation.
- E09 semantic inference: OWL 2 RL entailment closure via OWL-RL.
- E10 rule engine: deterministic allow-listed rules; no dynamic Python evaluation.
- E11 hermeneutic: source-preserving staged workflow; context and hypotheses remain separate; human/independent validation required.
- E12 formalization: typed symbolic AST with exact rational constants, associative flattening, commutative normalization and safe constant folding over the declared operator set; no string evaluation or arbitrary code execution.
- E13 validation: JSON Schema Draft 2020-12.
- E14 provenance: append-only SHA-256 hash chain.
- E15 consensus: unanimity gate from the exact agent team assigned to the invoking command, against one evidence digest.
- Command gateway: `engine_gateway_v1.py` exposes each engine through a validated `(command, agent team, engine)` route. It rejects agents outside the command team and engines outside that command's engine set.
- Additive launcher beta v1.8: `lunita_beta_v1_8.py` delegates legacy v1.7 commands only after verifying the exact v1.7 launcher SHA-256; `engine-run` and `engine-status` expose the new engine runtime without replacing v1.7.


## Installation and validation

The GitHub Actions workflow provisions CPython 3.12 dependencies into the isolated `vendor/python3.12/site-packages` folder, verifies the OWL-RL wheel SHA-256, downloads the FastEmbed model weights into `model-cache/fastembed`, and runs the acceptance suite against those vendored files. The resulting Actions artifact is named `lunita-engine-overlay-v1-py312`.

Run from this directory when validating a locally provisioned build:

```bash
PYTHONPATH=vendor/python3.12/site-packages \
LUNITA_FASTEMBED_CACHE=model-cache/fastembed \
python engine_acceptance_v1.py
python gateway_acceptance_v1.py
python launcher_acceptance_v1.py
```

The hosted test suite executes E02–E15 with actual library/model operations; E02, E06 and E12 are deterministic code-native engines, while E04 runs the multilingual ONNX model. E01 requires the actual Qwen GGUF and llama.cpp binaries from the target runtime; its target-specific test is skipped on hosted CI only when those external assets are absent, and must be executed on the deployed target.

Passing hosted tests validates the additive code and pinned dependency layer in that environment. It does not prove deployment inside the Lunita rootfs, actual Qwen inference on the target, JASP fixture non-regression, complete rootfs inventory, G23, G24, or canonical release eligibility.

## Target deployment — authorized CUSTOSZ_V7 only

The overlay must be activated by the existing authorized CUSTOSZ_V7 worker. GitHub CI is not an authorization to mutate the local candidate rootfs.

1. Create and verify a checkpoint using the worker's normal checkpoint mechanism. Export a receipt conforming to `LUNITA_RUNTIME_OVERLAY_CHECKPOINT/1.0` with `status=PASS`, `worker_version=CUSTOSZ_V7`, `candidate_id=G06_REBUILD_CANDIDATE_R1`, `scope=LUNITA_ADDITIVE_RUNTIME_ENGINE_OVERLAY`, `checkpoint_root`, `checkpoint_manifest`, and the actual `checkpoint_manifest_sha256`.
2. Run `apply_engine_overlay_v1.py` first without `--apply`. Only a PASS with the exact beta-v1.7 launcher SHA authorizes proceeding.
3. Execute again with `--apply`. It creates only `/opt/lunita/engines/runtime_engines_v1`; code, vendored CPython 3.12 packages, and model weights are copied into that new directory and hash checked. Reapplication/overwrite is denied.
4. Use the deployed Python 3.12 interpreter to run `engine_acceptance_v1.py` with:
   - `PYTHONPATH=/opt/lunita/engines/runtime_engines_v1/vendor/python3.12/site-packages`
   - `LUNITA_FASTEMBED_CACHE=/opt/lunita/engines/runtime_engines_v1/model-cache/fastembed`
   - `LUNITA_VECTOR_DB_PATH=/var/lib/lunita/vectors`
   Verify `LUNITA_E04_ONNX_QUANTIZATION_RECEIPT.json` and its ONNX digest, then re-run E01 against the exact Qwen GGUF and llama.cpp binary in the target rootfs; hosted CI does not contain those assets.
5. Keep this layer in `APPLIED_ADDITIVELY_NOT_CERTIFIED` until target runtime acceptance, actual JASP fixture non-regression, full rootfs inventory, G23, and G24 all pass.

The installer is deliberately not self-authorizing. No checkpoint receipt means no mutation; no V7 identity means no mutation; an existing target means no overwrite. The local rootfs has no `pip` or `ensurepip`, so deployment does not modify system/global package paths and does not assume they exist.
