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


## Instrument display labels — additive v1.8 metadata

The v1.8 status surface exposes the following human-facing labels. These are labels only; they do not rename binaries, paths, Flatpak application IDs, smoke-test commands, engine IDs, or command routes:

| Display label | Existing technical identity | Existing acceptance command |
|---|---|---|
| Brújula giroscópica | `/opt/lunita/instruments/brujula` | `brujula-self-test` |
| Sacapuntas | Flatpak `org.jamovi.jamovi` | `jamovi-self-test` |
| Lupa | Flatpak `org.jaspstats.JASP` | `jasp-self-test` |

The registry is separate from canonical E01–E15 engine identities. Existing v1.7 application checks remain delegated with the pinned legacy launcher; v1.8 adds the display metadata and the E01–E15 consensus-capable engine gateway without replacing that launcher.

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

## Direct target deployment and acceptance

The additive overlay is validated from its contents and hash-bound checkpoint, without binding authorization to an external worker identity. The installer remains fail-closed: it requires the exact candidate ID, a PASS checkpoint with the registered schema and scope, a real checkpoint manifest whose SHA-256 matches, the pinned v1.7 launcher, complete payload files/directories, and a non-existing overlay destination. It never overwrites an installed overlay.

1. Point `ROOTFS` to the candidate filesystem tree. Create the real checkpoint receipt and complete rootfs manifest from that exact tree; the checkpoint directory must be outside the rootfs and must not already exist:

```bash
python3 checkpoint_v1.py \
  --rootfs "$ROOTFS" \
  --checkpoint-dir "$CHECKPOINT_DIR" \
  --candidate-id G06_REBUILD_CANDIDATE_R1

export CHECKPOINT_RECEIPT="$CHECKPOINT_DIR/CHECKPOINT_RECEIPT.json"
```

The checkpoint tool hashes every regular file, records symlinks and filesystem modes without following links, checks that the tree did not change during the scan, and refuses to overwrite an existing checkpoint. The installer recomputes the tree manifest before applying and rejects a receipt for a different path or changed bytes.

2. Run a dry-run, then apply only after the dry-run returns `PREFLIGHT_PASS`:

```bash
python3 apply_engine_overlay_v1.py \
  --rootfs "$ROOTFS" \
  --checkpoint-receipt "$CHECKPOINT_RECEIPT" \
  --candidate-id G06_REBUILD_CANDIDATE_R1

python3 apply_engine_overlay_v1.py \
  --rootfs "$ROOTFS" \
  --checkpoint-receipt "$CHECKPOINT_RECEIPT" \
  --candidate-id G06_REBUILD_CANDIDATE_R1 \
  --apply
```

3. Validate the installed prefix directly. The default is `/opt/lunita`; set `LUNITA_ROOT` only when the installed prefix differs. The target runner and independent certification lane share the same receipt directory by default:

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

A target PASS requires the real local Qwen E01 inference, E02–E15 acceptance with zero skipped tests, measured E04 INT8 receipt, complete dependency inventory, and zero-return legacy Brújula/R/Jamovi/JASP/fault smoke commands. The runner writes a timestamped receipt and never grants certification.

The independent lane must then pass the actual candidate rootfs inventory and dependency closure, all four pinned JASP fixture non-regression cases, every hash-bound runtime check, and the separate S32 issuance gate. G23/G24 and the versioned release remain denied until their own evidence chain passes. Hosted CI validates source/runtime contracts but cannot substitute for local Qwen, Flatpak/JASP and rootfs evidence.
