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

## Installation
Install the version-pinned Python dependencies listed in `requirements-engine-stack.txt`, then install the Spanish model:

```bash
python -m pip install --disable-pip-version-check -r requirements-engine-stack.txt
python -m pip install --disable-pip-version-check \
  "https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.8.0/es_core_news_sm-3.8.0-py3-none-any.whl"
python -m pip download --disable-pip-version-check --no-deps --only-binary=:all: \
  --dest /tmp/lunita-owlrl "owlrl==7.6.2"
echo "83347bf7f133979e87b2b18695d51d25510b99cec3f6919b5df05d4fbf058ae0  /tmp/lunita-owlrl/owlrl-7.6.2-py3-none-any.whl" | sha256sum -c -
python -m pip install --disable-pip-version-check --no-deps /tmp/lunita-owlrl/owlrl-7.6.2-py3-none-any.whl
```

The multilingual embedding weights are downloaded by FastEmbed on first use. The target candidate must provision the model before offline operation and record its exact cache hash and Hugging Face revision. No model is treated as installed merely because its name is in a registry.

## Validation
Run from this directory:

```bash
python -m unittest -v test_engine_runtime_v1.py
```

The tests perform actual NLP, embedding, vector indexing/search, graph, RDF/SPARQL, OWL profile, OWL-RL inference, rule evaluation, hermeneutic staging, symbolic formalization, schema validation, provenance, and consensus operations. E01 requires the actual Qwen GGUF and llama.cpp binaries from the target runtime; its target-specific test is skipped on hosted CI only when those external assets are absent, and is mandatory on the deployed target.

Passing these tests validates this additive code/dependency candidate in the tested environment only. It does not prove deployment inside the Lunita rootfs, the JASP fixture regression gate, complete rootfs inventory, G23, G24, or canonical release eligibility.


## Target deployment — authorized CUSTOSZ_V7 only

The overlay must be activated by the existing authorized CUSTOSZ_V7 worker. GitHub CI is not an authorization to mutate the local candidate rootfs.

1. Create and verify a checkpoint using the worker's normal checkpoint mechanism. Export a receipt conforming to \`LUNITA_RUNTIME_OVERLAY_CHECKPOINT/1.0\` with:
   - \`status=PASS\`, \`worker_version=CUSTOSZ_V7\`, \`candidate_id=G06_REBUILD_CANDIDATE_R1\`
   - \`scope=LUNITA_ADDITIVE_RUNTIME_ENGINE_OVERLAY\`
   - \`checkpoint_root\`, \`checkpoint_manifest\` and the actual \`checkpoint_manifest_sha256\`.
2. Run \`apply_engine_overlay_v1.py\` first without \`--apply\`. Only a PASS with the exact beta-v1.7 launcher SHA authorizes proceeding.
3. Execute again with \`--apply\`. It creates only \`/opt/lunita/engines/runtime_engines_v1\`; all files are copied into a new directory and hash checked. Reapplication/overwrite is denied.
4. Use the target's Python 3.12 binary to run \`provision_engine_runtime_v1.py\`, directing site packages into the overlay vendor directory and model cache into a separate writable state path. No system/global Python package path is modified.
5. Run \`engine_acceptance_v1.py\` with \`PYTHONPATH=/opt/lunita/engines/runtime_engines_v1/vendor/python3.12/site-packages\`, \`LUNITA_FASTEMBED_CACHE\` and \`LUNITA_VECTOR_DB_PATH\` set to the receipt-bound locations. Re-run E01 on the target rootfs; the hosted E01 test is skipped because the Qwen GGUF is not present in the hosted runner.
6. Keep this layer in \`DEPENDENCIES_PROVISIONED_NOT_CERTIFIED\` until target runtime acceptance, actual JASP fixture non-regression, full rootfs inventory, G23 and G24 all pass.

The installer and provisioner are deliberately not self-authorizing. No checkpoint receipt means no mutation; no V7 identity means no mutation; an existing target means no overwrite.
