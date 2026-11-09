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
```

The multilingual embedding weights are downloaded by FastEmbed on first use. The target candidate must provision the model before offline operation and record its exact cache hash and Hugging Face revision. No model is treated as installed merely because its name is in a registry.

## Validation
Run from this directory:

```bash
python -m unittest -v test_engine_runtime_v1.py
```

The tests perform actual NLP, embedding, vector indexing/search, graph, RDF/SPARQL, OWL profile, OWL-RL inference, rule evaluation, hermeneutic staging, symbolic formalization, schema validation, provenance, and consensus operations. E01 requires the actual Qwen GGUF and llama.cpp binaries from the target runtime; its target-specific test is skipped on hosted CI only when those external assets are absent, and is mandatory on the deployed target.

Passing these tests validates this additive code/dependency candidate in the tested environment only. It does not prove deployment inside the Lunita rootfs, the JASP fixture regression gate, complete rootfs inventory, G23, G24, or canonical release eligibility.
