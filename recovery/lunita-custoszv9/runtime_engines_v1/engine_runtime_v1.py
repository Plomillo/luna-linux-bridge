"""Additive runtime adapters for Louksna's existing E01-E15 engine identities.

This package is an implementation candidate, not architectural authority.
It does not mutate or certify canonical identities, agents, commands or CFE IDs.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import subprocess
import tempfile
import uuid
from functools import lru_cache
from importlib import metadata
from typing import Any, Iterable, Mapping, Sequence

EMBEDDING_MODEL = "minishlab/potion-multilingual-128M"
EMBEDDING_DIMENSION = 256
SPACY_MODEL = "es_core_news_sm"
CANDIDATE_ROOT = pathlib.Path("/opt/lunita")
DEFAULT_MODEL = CANDIDATE_ROOT / "brain/model/Qwen_Qwen3-0.6B-IQ3_XS.gguf"
DEFAULT_LLAMA_ROOT = CANDIDATE_ROOT / "brain/runtime"


ENGINE_NAMES = {
    "E01": "LLM", "E02": "NLP", "E03": "RAG", "E04": "EMBEDDINGS",
    "E05": "VECTOR_SEARCH", "E06": "KNOWLEDGE_GRAPH", "E07": "RDF",
    "E08": "OWL", "E09": "SEMANTIC_INFERENCE", "E10": "RULE_ENGINE",
    "E11": "HERMENEUTIC", "E12": "FORMALIZATION", "E13": "VALIDATION",
    "E14": "PROVENANCE", "E15": "CONSENSUS",
}

ENGINE_ASSIGNMENTS = {
    "E01": frozenset({"Luna", "Josefina", "Katya"}),
    "E02": frozenset({"Luna", "Josefina", "Katya"}),
    "E03": frozenset({"Luna", "Josefina", "Katya", "Ancapi"}),
    "E04": frozenset({"Luna", "Josefina", "Katya"}),
    "E05": frozenset({"Luna", "Josefina", "Katya", "Ancapi"}),
    "E06": frozenset({"Luna", "Ancapi"}),
    "E07": frozenset({"Luna", "Ancapi"}),
    "E08": frozenset({"Luna", "Ancapi"}),
    "E09": frozenset({"Luna", "Josefina", "Katya", "Ancapi"}),
    "E10": frozenset({"Luna", "Josefina", "Ancapi"}),
    "E11": frozenset({"Luna", "Josefina", "Katya"}),
    "E12": frozenset({"Luna", "Josefina", "Katya", "Ancapi"}),
    "E13": frozenset({"Luna", "Josefina", "Katya", "Ancapi"}),
    "E14": frozenset({"Luna", "Josefina", "Ancapi"}),
    "E15": frozenset({"Luna", "Josefina", "Katya", "Ancapi"}),
}

COMMAND_ENGINES = {
    "/help": ("E13", "E14", "E15"),
    "/play PT": ("E01", "E02", "E11", "E12", "E13"),
    "/play PA": ("E06", "E07", "E08", "E09", "E10", "E12", "E13", "E14"),
    "/play DCI": ("E03", "E04", "E05", "E09", "E11", "E12", "E13", "E14"),
    "/play DCIL": ("E01", "E02", "E03", "E04", "E05", "E09", "E11", "E12", "E13", "E14", "E15"),
    "/play traductor": ("E01", "E02", "E03", "E04", "E05", "E12", "E13", "E14", "E15"),
    "/play e": ("E11", "E12", "E13", "E14", "E15"),
    "/play ema": ("E11", "E12", "E13", "E14", "E15"),
    "/play p": ("E10", "E12", "E13", "E14", "E15"),
    "/play c": ("E01", "E02", "E09", "E12", "E13", "E15"),
    "/play cp": ("E03", "E05", "E06", "E09", "E11", "E12", "E13", "E14", "E15"),
    "/play MA": tuple(f"E{i:02d}" for i in range(1, 16)),
    "/play H": ("E11", "E12", "E13", "E14", "E15"),
    "/play AE": ("E06", "E07", "E08", "E09", "E10", "E12", "E13", "E14", "E15"),
}

COMMAND_AGENTS = {
    "/help": ("Luna",),
    "/play PT": ("Luna", "Katya"),
    "/play PA": ("Luna", "Ancapi"),
    "/play DCI": ("Luna", "Josefina"),
    "/play DCIL": ("Luna", "Josefina", "Katya"),
    "/play traductor": ("Luna", "Katya"),
    "/play e": ("Luna", "Josefina"),
    "/play ema": ("Luna", "Josefina", "Katya"),
    "/play p": ("Luna", "Ancapi"),
    "/play c": ("Luna", "Katya"),
    "/play cp": ("Luna", "Josefina", "Katya"),
    "/play MA": ("Luna",),
    "/play H": ("Luna", "Josefina"),
    "/play AE": ("Luna", "Ancapi"),
}

CFE_FAMILY_BY_ENGINE = {
    "E01": "CFE001-CFE010", "E02": "CFE001-CFE010",
    "E03": "CFE011-CFE020", "E04": "CFE011-CFE020", "E05": "CFE011-CFE020",
    "E06": "CFE021-CFE030", "E07": "CFE021-CFE030", "E08": "CFE031-CFE040",
    "E09": "CFE031-CFE040", "E10": "CFE041-CFE050",
    "E11": "CFE051-CFE060", "E12": "CFE051-CFE060",
    "E13": "CFE041-CFE050", "E14": "CFE061-CFE070", "E15": "CFE071-CFE074",
}


class EngineUnavailable(RuntimeError):
    """A required dependency, runtime binary, or model is not available."""


class EngineContractError(ValueError):
    """An engine request violates its declared input or assignment contract."""


def validate_registry() -> dict[str, Any]:
    expected = {f"E{i:02d}" for i in range(1, 16)}
    if set(ENGINE_NAMES) != expected or set(ENGINE_ASSIGNMENTS) != expected:
        raise EngineContractError("Canonical seed-engine namespace mismatch")
    if set(COMMAND_ENGINES) != {
        "/help", "/play PT", "/play PA", "/play DCI", "/play DCIL",
        "/play traductor", "/play e", "/play ema", "/play p", "/play c",
        "/play cp", "/play MA", "/play H", "/play AE",
    }:
        raise EngineContractError("Canonical command namespace mismatch")
    if set(COMMAND_AGENTS) != set(COMMAND_ENGINES):
        raise EngineContractError("Command-to-agent routing namespace mismatch")
    if any("Luna" not in agents for agents in COMMAND_AGENTS.values()):
        raise EngineContractError("Luna must remain present in every command route")
    allowed_agents = {"Luna", "Josefina", "Katya", "Ancapi"}
    if any(not set(agents).issubset(allowed_agents) for agents in COMMAND_AGENTS.values()):
        raise EngineContractError("Unsupported agent in command route")
    for command, engines in COMMAND_ENGINES.items():
        for engine in engines:
            if engine not in ENGINE_NAMES:
                raise EngineContractError(f"Unknown engine {engine} in {command}")
    return {
        "status": "PASS_REGISTRY_CONFORMANCE",
        "engine_count": len(ENGINE_NAMES),
        "command_count": len(COMMAND_ENGINES),
        "canonical_identity_mutation": False,
        "engine_reassignment": False,
    }


def assert_agent_assignment(engine_id: str, agent: str) -> None:
    if engine_id not in ENGINE_ASSIGNMENTS:
        raise EngineContractError(f"Unknown canonical engine: {engine_id}")
    if agent not in ENGINE_ASSIGNMENTS[engine_id]:
        raise EngineContractError(f"{agent} is not assigned to {engine_id}")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_json(data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(payload)


def _require_nonempty(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EngineContractError(f"{label} must be a non-empty string")
    return value


def _distribution_version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError as exc:
        raise EngineUnavailable(f"Required package not installed: {package}") from exc


def engine_dependency_inventory() -> dict[str, Any]:
    packages = {
        "spacy": "spacy", "fastembed": "fastembed", "qdrant-client": "qdrant-client",
        "networkx": "networkx", "rdflib": "rdflib", "owlrl": "owlrl",
        "sympy": "sympy", "jsonschema": "jsonschema",
    }
    found = {}
    missing = []
    for label, dist in packages.items():
        try:
            found[label] = _distribution_version(dist)
        except EngineUnavailable:
            missing.append(label)
    return {"installed": found, "missing": missing, "status": "PASS" if not missing else "BLOCKED_DEPENDENCIES"}


# E01 — LLM: use the existing target Qwen3 GGUF and llama.cpp binaries.
def discover_llama_cli(runtime_root: pathlib.Path = DEFAULT_LLAMA_ROOT) -> pathlib.Path:
    if not runtime_root.is_dir():
        raise EngineUnavailable(f"llama.cpp runtime directory not found: {runtime_root}")
    matches = sorted(runtime_root.glob("*/llama-cli"))
    if not matches:
        raise EngineUnavailable("llama-cli not found in the installed Lunita runtime")
    return matches[0]


def llm_infer(
    prompt: str,
    *,
    model_path: pathlib.Path = DEFAULT_MODEL,
    llama_cli: pathlib.Path | None = None,
    max_tokens: int = 96,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    _require_nonempty(prompt, "prompt")
    if not 1 <= max_tokens <= 512:
        raise EngineContractError("max_tokens must be between 1 and 512")
    if not model_path.is_file():
        raise EngineUnavailable(f"Required local Qwen model is absent: {model_path}")
    binary = llama_cli or discover_llama_cli()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise EngineUnavailable(f"llama-cli is not executable: {binary}")
    env = os.environ.copy()
    libdir = str(binary.parent)
    env["LD_LIBRARY_PATH"] = libdir + (os.pathsep + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    cpu_backend = binary.parent / "libggml-cpu-x64.so"
    if cpu_backend.is_file():
        env["GGML_BACKEND_PATH"] = str(cpu_backend)
    command = [
        str(binary), "-m", str(model_path), "-t", "1", "-c", "512", "-b", "64", "-ub", "32",
        "-n", str(max_tokens), "--single-turn", "--simple-io", "--no-warmup", "-p", prompt,
    ]
    try:
        result = subprocess.run(command, env=env, capture_output=True, text=True,
                                timeout=timeout_seconds, check=False)
    except subprocess.TimeoutExpired as exc:
        raise EngineUnavailable(f"Qwen inference timed out after {timeout_seconds}s") from exc
    if result.returncode != 0:
        raise EngineUnavailable(f"Qwen inference failed ({result.returncode}): {result.stderr[-1200:]}")
    return {
        "engine_id": "E01", "model": model_path.name, "runtime": str(binary),
        "prompt_sha256": _sha256_bytes(prompt.encode("utf-8")),
        "output": result.stdout.strip(), "returncode": result.returncode,
    }


# E02 — NLP: Spanish tokenization, morphology, lemmatization, parsing and NER.
@lru_cache(maxsize=1)
def _spanish_nlp():
    import spacy
    try:
        return spacy.load(SPACY_MODEL)
    except OSError as exc:
        raise EngineUnavailable(f"Spanish spaCy model is not installed: {SPACY_MODEL}") from exc


def nlp_analyze(text: str) -> dict[str, Any]:
    _require_nonempty(text, "text")
    nlp = _spanish_nlp()
    doc = nlp(text)
    return {
        "engine_id": "E02", "language": nlp.lang, "model": SPACY_MODEL,
        "pipeline": list(nlp.pipe_names), "source_sha256": _sha256_bytes(text.encode("utf-8")),
        "tokens": [
            {"text": token.text, "lemma": token.lemma_, "pos": token.pos_, "is_stop": bool(token.is_stop)}
            for token in doc if not token.is_space
        ],
        "sentences": [sentence.text for sentence in doc.sents],
        "entities": [{"text": ent.text, "label": ent.label_} for ent in doc.ents],
    }


# E04 — Embeddings: CPU-based multilingual vectorization.
@lru_cache(maxsize=1)
def _embedder():
    from fastembed import TextEmbedding
    try:
        return TextEmbedding(model_name=EMBEDDING_MODEL)
    except Exception as exc:
        raise EngineUnavailable(f"Unable to load embedding model {EMBEDDING_MODEL}: {exc}") from exc


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    if not texts:
        raise EngineContractError("At least one text is required for embedding")
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise EngineContractError("Embedding inputs must be non-empty strings")
    vectors = []
    for vector in _embedder().embed(list(texts)):
        values = [float(value) for value in vector.tolist()]
        if len(values) != EMBEDDING_DIMENSION or not all(math.isfinite(value) for value in values):
            raise EngineUnavailable("Embedding output dimension or numeric integrity check failed")
        vectors.append(values)
    if len(vectors) != len(texts):
        raise EngineUnavailable("Embedding model returned an unexpected vector count")
    return vectors


# E05 — Vector Search: Qdrant's embedded local index (memory or persistent path).
class VectorIndex:
    def __init__(self, storage_path: str | None = None, collection: str = "lunita_e05"):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        self.client = QdrantClient(":memory:") if storage_path is None else QdrantClient(path=storage_path)
        self.collection = collection
        self._closed = False
        self.client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE),
        )

    def upsert(self, ids: Sequence[str], texts: Sequence[str], vectors: Sequence[Sequence[float]]) -> None:
        from qdrant_client.models import PointStruct
        if not (len(ids) == len(texts) == len(vectors)) or not ids:
            raise EngineContractError("Vector index inputs must have the same non-zero length")
        points = []
        for source_id, text, vector in zip(ids, texts, vectors):
            _require_nonempty(source_id, "source_id")
            _require_nonempty(text, "text")
            if len(vector) != EMBEDDING_DIMENSION:
                raise EngineContractError("Vector dimension mismatch")
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, source_id))
            points.append(PointStruct(
                id=point_id, vector=list(vector),
                payload={"source_id": source_id, "text": text,
                         "source_sha256": _sha256_bytes(text.encode("utf-8"))},
            ))
        self.client.upsert(collection_name=self.collection, points=points, wait=True)

    def search(self, query_vector: Sequence[float], limit: int = 5) -> list[dict[str, Any]]:
        if self._closed:
            raise EngineContractError("Vector index is closed")
        if len(query_vector) != EMBEDDING_DIMENSION or not 1 <= limit <= 100:
            raise EngineContractError("Invalid query vector or limit")
        result = self.client.query_points(
            collection_name=self.collection, query=list(query_vector), limit=limit, with_payload=True,
        )
        return [
            {"source_id": hit.payload["source_id"], "text": hit.payload["text"],
             "score": float(hit.score), "source_sha256": hit.payload["source_sha256"]}
            for hit in result.points
        ]

    def close(self) -> None:
        if not self._closed:
            self.client.close()
            self._closed = True


# E03 — RAG: source-bound retrieval plus explicit context for E01 synthesis.
class RAGIndex:
    def __init__(self, documents: Sequence[Mapping[str, str]], storage_path: str | None = None):
        if not documents:
            raise EngineContractError("RAG requires at least one source document")
        self.source_ids = []
        self.texts = []
        for document in documents:
            source_id = _require_nonempty(document.get("source_id", ""), "source_id")
            text = _require_nonempty(document.get("text", ""), "document text")
            if source_id in self.source_ids:
                raise EngineContractError(f"Duplicate RAG source_id: {source_id}")
            self.source_ids.append(source_id)
            self.texts.append(text)
        vectors = embed_texts(self.texts)
        self.index = VectorIndex(storage_path=storage_path)
        self.index.upsert(self.source_ids, self.texts, vectors)

    def retrieve(self, query: str, limit: int = 5) -> dict[str, Any]:
        _require_nonempty(query, "query")
        query_vector = embed_texts([query])[0]
        hits = self.index.search(query_vector, limit=limit)
        return {
            "engine_id": "E03", "query_sha256": _sha256_bytes(query.encode("utf-8")),
            "retrieved_sources": hits,
            "context": "\n\n".join(
                f"[SOURCE:{hit['source_id']}][SHA256:{hit['source_sha256']}]\n{hit['text']}"
                for hit in hits
            ),
            "answer_generation": "DELEGATED_TO_E01",
        }

    def close(self) -> None:
        self.index.close()


# E06 — Knowledge Graph: explicit directed graph, edge types and traversals.
def build_knowledge_graph(nodes: Sequence[Mapping[str, Any]], edges: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    import networkx as nx
    graph = nx.MultiDiGraph()
    for node in nodes:
        node_id = _require_nonempty(str(node.get("id", "")), "node id")
        graph.add_node(node_id, **dict(node.get("attributes", {})))
    for edge in edges:
        source = _require_nonempty(str(edge.get("source", "")), "edge source")
        target = _require_nonempty(str(edge.get("target", "")), "edge target")
        relation = _require_nonempty(str(edge.get("relation", "")), "edge relation")
        if source not in graph or target not in graph:
            raise EngineContractError("Knowledge graph edge references an undeclared node")
        graph.add_edge(source, target, relation=relation)
    return {"engine_id": "E06", "graph": graph, "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(), "is_directed": graph.is_directed()}


# E07 — RDF: parse/serialize triples and execute SPARQL.
def rdf_query(turtle_text: str, sparql: str) -> dict[str, Any]:
    from rdflib import Graph
    _require_nonempty(turtle_text, "turtle_text")
    _require_nonempty(sparql, "sparql")
    graph = Graph()
    graph.parse(data=turtle_text, format="turtle")
    rows = []
    for row in graph.query(sparql):
        rows.append([str(value) if value is not None else None for value in row])
    return {
        "engine_id": "E07", "triple_count": len(graph),
        "graph_sha256": _sha256_bytes(graph.serialize(format="nt").encode("utf-8")),
        "rows": rows, "serialization": graph.serialize(format="turtle"),
    }


# E08 — OWL: validate ontology vocabulary/declarations without changing axioms.
def validate_owl_ontology(turtle_text: str) -> dict[str, Any]:
    from rdflib import Graph, RDF, OWL, URIRef
    _require_nonempty(turtle_text, "turtle_text")
    graph = Graph()
    graph.parse(data=turtle_text, format="turtle")
    classes = sorted(str(subject) for subject in graph.subjects(RDF.type, OWL.Class))
    object_properties = sorted(str(subject) for subject in graph.subjects(RDF.type, OWL.ObjectProperty))
    datatype_properties = sorted(str(subject) for subject in graph.subjects(RDF.type, OWL.DatatypeProperty))
    malformed = []
    for subject in graph.subjects(RDF.type, OWL.ObjectProperty):
        if not isinstance(subject, URIRef):
            malformed.append(str(subject))
    if not classes:
        raise EngineContractError("OWL ontology contains no explicit owl:Class declarations")
    if malformed:
        raise EngineContractError("OWL object-property identifiers must be URIRefs")
    return {
        "engine_id": "E08", "status": "PASS_OWL_PROFILE_VALIDATION",
        "classes": classes, "object_properties": object_properties,
        "datatype_properties": datatype_properties,
        "axiom_count": len(graph),
        "source_graph_sha256": _sha256_bytes(graph.serialize(format="nt").encode("utf-8")),
    }


# E09 — Semantic inference: materialize OWL 2 RL consequences and prove entailments.
def owlrl_infer(turtle_text: str, required_triples: Sequence[Sequence[str]] = ()) -> dict[str, Any]:
    from rdflib import Graph
    from owlrl import DeductiveClosure, OWLRL_Semantics
    _require_nonempty(turtle_text, "turtle_text")
    graph = Graph()
    graph.parse(data=turtle_text, format="turtle")
    before = len(graph)
    DeductiveClosure(OWLRL_Semantics).expand(graph)
    entailments = []
    for triple in required_triples:
        if len(triple) != 3:
            raise EngineContractError("Each required entailment must have three RDF terms")
        from rdflib import URIRef, Literal
        terms = tuple(Literal(value) if not str(value).startswith("http") else URIRef(value) for value in triple)
        entailments.append({"triple": [str(term) for term in terms], "entailed": terms in graph})
    return {
        "engine_id": "E09", "status": "PASS" if all(item["entailed"] for item in entailments) else "FAIL_REQUIRED_ENTAILMENT",
        "triple_count_before": before, "triple_count_after": len(graph),
        "inferred_triple_count": len(graph) - before, "required_entailments": entailments,
    }


# E10 — Rule Engine: deterministic allow-list; never eval/exec user expressions.
_ALLOWED_OPERATORS = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "contains", "exists"}


def _evaluate_condition(facts: Mapping[str, Any], condition: Mapping[str, Any]) -> bool:
    field = _require_nonempty(str(condition.get("field", "")), "rule field")
    operator = condition.get("op")
    if operator not in _ALLOWED_OPERATORS:
        raise EngineContractError(f"Unsupported rule operator: {operator}")
    exists = field in facts
    if operator == "exists":
        return exists is bool(condition.get("value", True))
    if not exists:
        return False
    left = facts[field]
    right = condition.get("value")
    if operator == "eq": return left == right
    if operator == "ne": return left != right
    if operator == "gt": return left > right
    if operator == "gte": return left >= right
    if operator == "lt": return left < right
    if operator == "lte": return left <= right
    if operator == "in": return left in right
    if operator == "contains": return right in left
    return False


def evaluate_rules(facts: Mapping[str, Any], rules: Sequence[Mapping[str, Any]], max_passes: int = 8) -> dict[str, Any]:
    if not 1 <= max_passes <= 32:
        raise EngineContractError("max_passes must be between 1 and 32")
    working = dict(facts)
    applied: list[str] = []
    seen = set()
    for _ in range(max_passes):
        changed = False
        for rule in rules:
            rule_id = _require_nonempty(str(rule.get("id", "")), "rule id")
            condition = rule.get("when")
            conclusion = rule.get("then")
            if not isinstance(condition, Mapping) or not isinstance(conclusion, Mapping):
                raise EngineContractError(f"Malformed rule: {rule_id}")
            if _evaluate_condition(working, condition):
                target = _require_nonempty(str(conclusion.get("field", "")), "conclusion field")
                if target in working and working[target] != conclusion.get("value"):
                    raise EngineContractError(f"Rule conflict on fact {target}: {rule_id}")
                if target not in working:
                    working[target] = conclusion.get("value")
                    applied.append(rule_id)
                    changed = True
        fingerprint = _sha256_json(working)
        if fingerprint in seen and changed:
            raise EngineContractError("Rule engine detected a non-convergent cycle")
        seen.add(fingerprint)
        if not changed:
            return {"engine_id": "E10", "status": "PASS_RULES_CONVERGED",
                    "facts": working, "applied_rules": applied, "passes": _ + 1}
    raise EngineContractError("Rule engine exceeded max_passes; fail closed")


# E11 — Hermeneutic: preserve source, separate observation/context/inference/interpretation.
def hermeneutic_analyze(
    source_text: str,
    *,
    source_id: str,
    genre: str,
    audience: str,
    historical_context: str,
    preceding_context: str,
    following_context: str,
    hypotheses: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    _require_nonempty(source_text, "source_text")
    required = {
        "source_id": source_id, "genre": genre, "audience": audience,
        "historical_context": historical_context,
        "preceding_context": preceding_context, "following_context": following_context,
    }
    missing = [key for key, value in required.items() if not isinstance(value, str) or not value.strip()]
    source_hash = _sha256_bytes(source_text.encode("utf-8"))
    if missing:
        return {"engine_id": "E11", "status": "BLOCKED_CONTEXT_INCOMPLETE",
                "missing_context_fields": missing, "source_sha256": source_hash,
                "source_text_preserved": True}
    if not hypotheses:
        raise EngineContractError("Hermeneutic processing requires explicit, reviewable hypotheses")
    observations = nlp_analyze(source_text)
    reviewed = []
    ungrounded = []
    for hypothesis in hypotheses:
        statement = _require_nonempty(str(hypothesis.get("statement", "")), "hypothesis statement")
        evidence_spans = hypothesis.get("evidence_spans", [])
        if not isinstance(evidence_spans, list) or not evidence_spans:
            ungrounded.append(statement)
            continue
        valid_spans = [span for span in evidence_spans if isinstance(span, str) and span and span in source_text]
        if len(valid_spans) != len(evidence_spans):
            ungrounded.append(statement)
        reviewed.append({"statement": statement, "evidence_spans": valid_spans,
                         "grounded_in_source": len(valid_spans) == len(evidence_spans)})
    return {
        "engine_id": "E11",
        "status": "BLOCKED_UNGROUNDED_HYPOTHESIS" if ungrounded else "READY_FOR_INDEPENDENT_HERMENEUTIC_VALIDATION",
        "source": {"id": source_id, "text": source_text, "sha256": source_hash},
        "observation": {"token_count": len(observations["tokens"]), "sentences": observations["sentences"],
                        "entities": observations["entities"]},
        "linguistic_analysis": observations,
        "context": {key: value for key, value in required.items()},
        "historical_cultural_analysis": {"status": "CONTEXT_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED"},
        "inference": {"hypotheses": reviewed, "ungrounded_hypotheses": ungrounded},
        "interpretation": {"status": "PROVISIONAL_NOT_FINAL_MEANING"},
        "controls": {
            "eisegesis": "SOURCE_EVIDENCE_REQUIRED",
            "proof_texting": "WIDER_CONTEXT_REQUIRED",
            "anachronism": "HISTORICAL_CONTEXT_REQUIRED",
            "lexical_fallacy": "LEXICAL_ANALYSIS_SEPARATE_FROM_DOCTRINAL_MEANING",
            "semantic_overloading": "HYPOTHESES_REQUIRE_EXPLICIT_EVIDENCE",
            "contextual_displacement": "PRECEDING_AND_FOLLOWING_CONTEXT_REQUIRED",
        },
        "source_text_preserved": True,
        "human_or_independent_validation_required": True,
    }


# E12 — Formalization: structured AST -> symbolic expression; no parsing/eval of source code.
def _build_symbolic_expression(node: Any, symbols: dict[str, Any]):
    import sympy as sp
    if not isinstance(node, Mapping):
        raise EngineContractError("Formalization nodes must be typed objects")
    if "symbol" in node:
        name = _require_nonempty(str(node["symbol"]), "symbol")
        if not name.isidentifier():
            raise EngineContractError(f"Invalid symbol name: {name}")
        return symbols.setdefault(name, sp.Symbol(name, real=True))
    if "number" in node:
        number = node["number"]
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise EngineContractError("Only numeric constants are allowed")
        if isinstance(number, float) and not math.isfinite(number):
            raise EngineContractError("Numeric constants must be finite")
        return sp.Rational(str(number))
    operator = node.get("op")
    args = node.get("args")
    if not isinstance(args, list):
        raise EngineContractError("Formalization operator requires an args list")
    built = [_build_symbolic_expression(argument, symbols) for argument in args]
    operations = {
        "add": (lambda a: sp.Add(*a)),
        "mul": (lambda a: sp.Mul(*a)),
        "sub": (lambda a: a[0] - a[1] if len(a) == 2 else (_ for _ in ()).throw(EngineContractError("sub requires 2 args"))),
        "div": (lambda a: a[0] / a[1] if len(a) == 2 else (_ for _ in ()).throw(EngineContractError("div requires 2 args"))),
        "pow": (lambda a: a[0] ** a[1] if len(a) == 2 else (_ for _ in ()).throw(EngineContractError("pow requires 2 args"))),
        "eq": (lambda a: sp.Eq(*a) if len(a) == 2 else (_ for _ in ()).throw(EngineContractError("eq requires 2 args"))),
        "lt": (lambda a: sp.Lt(*a) if len(a) == 2 else (_ for _ in ()).throw(EngineContractError("lt requires 2 args"))),
        "gt": (lambda a: sp.Gt(*a) if len(a) == 2 else (_ for _ in ()).throw(EngineContractError("gt requires 2 args"))),
        "and": (lambda a: sp.And(*a)),
        "or": (lambda a: sp.Or(*a)),
        "not": (lambda a: sp.Not(a[0]) if len(a) == 1 else (_ for _ in ()).throw(EngineContractError("not requires 1 arg"))),
    }
    if operator not in operations:
        raise EngineContractError(f"Unsupported formalization operator: {operator}")
    if not built:
        raise EngineContractError(f"Operator {operator} requires arguments")
    return operations[operator](built)


def formalize_expression(ast: Mapping[str, Any]) -> dict[str, Any]:
    import sympy as sp
    symbols: dict[str, Any] = {}
    expression = _build_symbolic_expression(ast, symbols)
    simplified = sp.simplify(expression)
    return {
        "engine_id": "E12", "status": "PASS_FORMALIZATION",
        "expression": str(expression), "simplified": str(simplified),
        "srepr": sp.srepr(simplified),
        "free_symbols": sorted(str(symbol) for symbol in simplified.free_symbols),
        "symbolic_boolean": bool(getattr(simplified, "is_Boolean", False)),
    }


# E13 — Validation: JSON Schema Draft 2020-12 with deterministic diagnostics.
def validate_json_schema(instance: Any, schema: Mapping[str, Any]) -> dict[str, Any]:
    from jsonschema import Draft202012Validator
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda error: (list(error.path), error.message))
    diagnostics = [
        {"path": list(error.path), "schema_path": list(error.schema_path), "message": error.message}
        for error in errors
    ]
    return {
        "engine_id": "E13", "status": "PASS_VALIDATION" if not diagnostics else "FAIL_VALIDATION",
        "valid": not diagnostics, "errors": diagnostics,
        "instance_sha256": _sha256_json(instance), "schema_sha256": _sha256_json(schema),
    }


# E14 — Provenance: append-only SHA-256 event chain.
def append_provenance_event(previous_hash: str, event: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(previous_hash, str) or len(previous_hash) != 64:
        raise EngineContractError("previous_hash must be a 64-character SHA-256 hex digest")
    try:
        bytes.fromhex(previous_hash)
    except ValueError as exc:
        raise EngineContractError("previous_hash is not hexadecimal") from exc
    event_copy = dict(event)
    event_hash = _sha256_json({"previous_hash": previous_hash, "event": event_copy})
    return {"previous_hash": previous_hash, "event": event_copy, "event_hash": event_hash}


def verify_provenance_chain(events: Sequence[Mapping[str, Any]], genesis: str = "0" * 64) -> dict[str, Any]:
    previous = genesis
    for index, record in enumerate(events):
        event = record.get("event")
        if not isinstance(event, Mapping) or record.get("previous_hash") != previous:
            return {"engine_id": "E14", "status": "FAIL_PROVENANCE_CHAIN", "failed_index": index}
        expected = _sha256_json({"previous_hash": previous, "event": dict(event)})
        if record.get("event_hash") != expected:
            return {"engine_id": "E14", "status": "FAIL_PROVENANCE_HASH", "failed_index": index}
        previous = expected
    return {"engine_id": "E14", "status": "PASS_PROVENANCE_CHAIN",
            "event_count": len(events), "terminal_hash": previous}


# E15 — Consensus: evidence-bound unanimous vote by the selected, assigned agents.
def aggregate_consensus(
    engine_id: str,
    evidence_sha256: str,
    votes: Sequence[Mapping[str, str]],
    *,
    required_agents: Sequence[str],
) -> dict[str, Any]:
    if engine_id not in ENGINE_ASSIGNMENTS:
        raise EngineContractError(f"Unknown engine: {engine_id}")
    if "Luna" not in required_agents:
        raise EngineContractError("Luna must chair every consensus route")
    required = set(required_agents)
    if len(required) != len(required_agents) or not required:
        raise EngineContractError("required_agents must be unique and non-empty")
    for agent in required:
        assert_agent_assignment(engine_id, agent)
    if len(evidence_sha256) != 64:
        raise EngineContractError("evidence_sha256 must be a SHA-256 digest")
    submitted: dict[str, str] = {}
    for vote in votes:
        agent = vote.get("agent", "")
        decision = vote.get("decision", "")
        if agent in submitted:
            raise EngineContractError(f"Duplicate consensus vote from {agent}")
        if agent not in required:
            raise EngineContractError(f"Unexpected consensus participant: {agent}")
        if decision not in {"APPROVE", "REJECT", "ABSTAIN"}:
            raise EngineContractError(f"Unsupported decision: {decision}")
        if vote.get("evidence_sha256") != evidence_sha256:
            raise EngineContractError("Consensus vote is not bound to the same evidence hash")
        submitted[agent] = decision
    missing = sorted(required - submitted.keys())
    rejected = sorted(agent for agent, decision in submitted.items() if decision != "APPROVE")
    return {
        "engine_id": "E15",
        "status": "PASS_CONSENSUS" if not missing and not rejected else "HOLD_CONSENSUS",
        "required_agents": sorted(required), "votes": dict(sorted(submitted.items())),
        "missing_agents": missing, "non_approving_agents": rejected,
        "evidence_sha256": evidence_sha256,
    }


def capability_status_snapshot() -> dict[str, Any]:
    validate_registry()
    return {
        "schema": "LOUKSNA_RUNTIME_ENGINE_STATUS/1.0",
        "canonical_engine_count": 15,
        "agent_count": 4,
        "command_count": 14,
        "engine_implementation_candidate": "runtime_engines_v1",
        "canonical_certification": "NOT_GRANTED",
        "engine_assignments": {key: sorted(value) for key, value in ENGINE_ASSIGNMENTS.items()},
        "dependencies": engine_dependency_inventory(),
    }
