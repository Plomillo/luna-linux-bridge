# Louksna E01–E15 — additive runtime implementation candidate

Status: `IMPLEMENTATION_CANDIDATE_PENDING_TARGET_DEPLOYMENT_AND_INDEPENDENT_CERTIFICATION`.

This directory adds adapters for existing E01–E15 identities. It does not add, rename, merge, replace, or reassign canonical engines, agents, commands, blocks, axioms, or CFE identifiers. Luna remains present in every command route. The exact assignment and 14-command routing matrix is in `engine_assignments_v1.json`.

## Implementation
- E01 LLM: existing candidate-rootfs Qwen3-0.6B GGUF through the bundled llama.cpp runtime; no placeholder model.
- E02 NLP: spaCy Spanish small pipeline.
- E03 RAG: source-bound retrieval/context assembly, delegating response generation to E01.
- E04 embeddings: FastEmbed `minishlab/potion-multilingual-128M`, 256-dimensional multilingual static embeddings (not contextual token embeddings).
- E05 vector search: Qdrant embedded local index, memory or persistent path.
- E06 knowledge graph: NetworkX directed multigraph.
- E07 RDF: RDFLib parsing, serialization and SPARQL.
- E08 OWL: explicit OWL vocabulary/profile validation.
- E09 semantic inference: OWL 2 RL entailment closure via OWL-RL.
- E10 rule engine: deterministic allow-listed rules; no dynamic Python evaluation.
- E11 hermeneutic: source-preserving staged workflow; context and hypotheses remain separate; human/independent validation required.
- E12 formalization: structured expression AST into SymPy; user strings are never evaluated as code.
- E13 validation: JSON Schema Draft 2020-12.
- E14 provenance: append-only SHA-256 hash chain.
- E15 consensus: unanimity gate from assigned agents against one evidence digest.


## Installation and validation

The GitHub Actions workflow provisions CPython 3.12 dependencies into the isolated `vendor/python3.12/site-packages` folder, verifies the OWL-RL wheel SHA-256, installs the official Spanish spaCy model, downloads the FastEmbed model weights into `model-cache/fastembed`, and runs the acceptance suite against those vendored files. The resulting Actions artifact is named `lunita-engine-overlay-v1-py312`.

Run from this directory when validating a locally provisioned build:

```bash
PYTHONPATH=vendor/python3.12/site-packages \
LUNITA_FASTEMBED_CACHE=model-cache/fastembed \
python engine_acceptance_v1.py
```

The hosted test suite executes E02–E15 with actual library/model operations. E01 requires the actual Qwen GGUF and llama.cpp binaries from the target runtime; its target-specific test is skipped on hosted CI only when those external assets are absent, and must be executed on the deployed target.

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
   Re-run E01 against the exact Qwen GGUF and llama.cpp binary in the target rootfs; hosted CI does not contain those assets.
5. Keep this layer in `APPLIED_ADDITIVELY_NOT_CERTIFIED` until target runtime acceptance, actual JASP fixture non-regression, full rootfs inventory, G23, and G24 all pass.

The installer is deliberately not self-authorizing. No checkpoint receipt means no mutation; no V7 identity means no mutation; an existing target means no overwrite. The local rootfs has no `pip` or `ensurepip`, so deployment does not modify system/global package paths and does not assume they exist.
