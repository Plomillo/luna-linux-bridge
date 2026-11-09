"""Additive runtime adapters for Louksna's existing E01-E15 engine identities.

This package is an implementation candidate, not architectural authority.
It does not mutate or certify canonical identities, agents, commands or CFE IDs.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import pathlib
import subprocess
import tempfile
import uuid
import sys
from collections import deque
from fractions import Fraction
from functools import lru_cache
from importlib import metadata
from typing import Any, Iterable, Mapping, Sequence

ENGINE_DIR = pathlib.Path(__file__).resolve().parent
VENDOR_SITE_PACKAGES = ENGINE_DIR / "vendor" / "python3.12" / "site-packages"
if VENDOR_SITE_PACKAGES.is_dir() and str(VENDOR_SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(VENDOR_SITE_PACKAGES))

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSION = 384
E02_MODEL = "LUNITA_SPANISH_RULE_BASED_NLP_V1"
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
    if set(ENGINE_NAMES) != expected:
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


def assert_command_route(command: str, agent: str, engine_id: str) -> None:
    """Validate only the canonical command -> team + engine relation.

    Louksna defines agent teams per command; it does not define an independent
    agent-to-engine ownership matrix. This gate deliberately avoids inventing one.
    """
    if command not in COMMAND_ENGINES or command not in COMMAND_AGENTS:
        raise EngineContractError(f"Unknown canonical command: {command}")
    if engine_id not in ENGINE_NAMES:
        raise EngineContractError(f"Unknown canonical engine: {engine_id}")
    if engine_id not in COMMAND_ENGINES[command]:
        raise EngineContractError(f"{engine_id} is not routed by {command}")
    if agent not in COMMAND_AGENTS[command]:
        raise EngineContractError(f"{agent} is not assigned to command {command}")
    return None


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
        "fastembed": "fastembed",
        "onnxruntime": "onnxruntime",
        "qdrant-client": "qdrant-client",
        "rdflib": "rdflib",
        "owlrl": "owlrl",
        "jsonschema": "jsonschema",
        "numpy": "numpy",
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


# E02 — NLP: deterministic Spanish tokenizer, sentence segmentation,
# lexicon/suffix morphology, heuristic POS and proper-name recognition.
# The model is explicit and versioned; no network access or external weights.
_SPANISH_STOP_WORDS = frozenset({
    "a", "al", "algo", "algunas", "algunos", "ante", "antes", "como", "con",
    "contra", "cual", "cuando", "de", "del", "desde", "donde", "durante",
    "e", "el", "ella", "ellas", "ellos", "en", "entre", "era", "erais",
    "eran", "eras", "eres", "es", "esa", "esas", "ese", "eso", "esos",
    "esta", "estaba", "estaban", "estado", "estais", "estamos", "estan",
    "estar", "estas", "este", "esto", "estos", "fue", "fueron", "ha",
    "habeis", "haber", "habia", "habian", "han", "hasta", "hay", "la",
    "las", "le", "les", "lo", "los", "mas", "me", "mi", "mis", "mucho",
    "muy", "no", "nos", "o", "os", "otra", "otras", "otro", "otros",
    "para", "pero", "poco", "por", "porque", "que", "quien", "se", "sea",
    "ser", "si", "sin", "sobre", "son", "su", "sus", "tambien", "te",
    "tiene", "tienen", "todo", "todos", "tu", "tus", "un", "una", "unas",
    "uno", "unos", "y", "ya",
})
_SPANISH_DETERMINERS = frozenset({"el", "la", "los", "las", "un", "una", "unos", "unas", "este", "esta", "estos", "estas", "ese", "esa", "mi", "mis", "su", "sus"})
_SPANISH_PRONOUNS = frozenset({"yo", "tu", "tú", "usted", "ustedes", "el", "él", "ella", "nosotros", "nosotras", "vosotros", "vosotras", "ellos", "ellas", "me", "te", "se", "nos", "os", "lo", "la", "le", "les"})
_SPANISH_PREPOSITIONS = frozenset({"a", "ante", "bajo", "con", "contra", "de", "desde", "durante", "en", "entre", "hacia", "hasta", "para", "por", "segun", "sin", "sobre", "tras"})
_SPANISH_CONJUNCTIONS = frozenset({"y", "e", "o", "u", "ni", "pero", "aunque", "porque", "si", "que"})
_SPANISH_VERB_LEMMAS = {
    "conserva": "conservar", "conservan": "conservar", "conservar": "conservar",
    "valida": "validar", "validan": "validar", "validar": "validar",
    "requiere": "requerir", "requieren": "requerir", "requiere": "requerir",
    "protege": "proteger", "protegen": "proteger", "proteger": "proteger",
    "preparan": "preparar", "prepara": "preparar", "preparar": "preparar",
    "organiza": "organizar", "organizan": "organizar", "organizar": "organizar",
    "analiza": "analizar", "analizan": "analizar", "analizar": "analizar",
    "preserva": "preservar", "preservan": "preservar", "preservar": "preservar",
    "es": "ser", "son": "ser", "era": "ser", "fue": "ser", "ser": "ser",
    "esta": "estar", "está": "estar", "estan": "estar", "están": "estar",
    "estar": "estar", "tiene": "tener", "tienen": "tener", "tener": "tener",
    "puede": "poder", "pueden": "poder", "poder": "poder",
}
_SPANISH_ADJECTIVE_SUFFIXES = ("able", "ible", "oso", "osa", "osos", "osas", "ico", "ica", "icos", "icas", "ivo", "iva", "ivos", "ivas", "al", "ar")
_SPANISH_ADVERB_SUFFIXES = ("mente",)


def _spanish_lemma_and_pos(token: str) -> tuple[str, str]:
    word = token.casefold()
    if word in _SPANISH_VERB_LEMMAS:
        return _SPANISH_VERB_LEMMAS[word], "VERB"
    if word in _SPANISH_DETERMINERS:
        return word, "DET"
    if word in _SPANISH_PRONOUNS:
        return word, "PRON"
    if word in _SPANISH_PREPOSITIONS:
        return word, "ADP"
    if word in _SPANISH_CONJUNCTIONS:
        return word, "CCONJ"
    if word.endswith(_SPANISH_ADVERB_SUFFIXES):
        return word, "ADV"
    if word.endswith(_SPANISH_ADJECTIVE_SUFFIXES):
        return word, "ADJ"
    # Conservative regular morphology: plural nominal endings only.
    if len(word) > 4 and word.endswith("es") and not word.endswith(("ies", "ues")):
        return word[:-2], "NOUN"
    if len(word) > 3 and word.endswith("s") and not word.endswith(("is", "us")):
        return word[:-1], "NOUN"
    # Verb suffix classification is evidence-based and deliberately labelled heuristic.
    if len(word) > 5 and word.endswith(("ando", "iendo", "aron", "ieron", "aba", "aban", "ía", "ían")):
        return word, "VERB"
    return word, "NOUN"


def nlp_analyze(text: str) -> dict[str, Any]:
    _require_nonempty(text, "text")
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
    tokens = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:['’][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)?|\d+(?:[.,]\d+)?", text)
    token_rows = []
    for token in tokens:
        lemma, pos = _spanish_lemma_and_pos(token)
        token_rows.append({
            "text": token,
            "lemma": lemma,
            "pos": pos,
            "is_stop": token.casefold() in _SPANISH_STOP_WORDS,
            "morphology": "LEXICON" if token.casefold() in _SPANISH_VERB_LEMMAS else "RULE_BASED",
        })
    # Proper-name candidate extraction: two or more consecutive title-case tokens,
    # excluding common determiners/connectors even when they start a sentence.
    entities = []
    pattern = re.compile(r"\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)+\b")
    for match in pattern.finditer(text):
        phrase = match.group(0)
        first = phrase.split()[0]
        if all(part.casefold() not in _SPANISH_STOP_WORDS for part in phrase.split()):
            entities.append({"text": phrase, "label": "PROPER_NAME_CANDIDATE", "confidence": "HEURISTIC"})
    return {
        "engine_id": "E02",
        "language": "es",
        "model": E02_MODEL,
        "pipeline": [
            "unicode_tokenizer", "sentence_boundary_detection",
            "spanish_stopword_lexicon", "spanish_lemma_and_pos_rules",
            "proper_name_candidate_detection",
        ],
        "source_sha256": _sha256_bytes(text.encode("utf-8")),
        "tokens": token_rows,
        "sentences": sentences,
        "entities": entities,
        "limitations": [
            "Rule-based Spanish morphology and POS; not a statistical dependency parser.",
            "Proper names are heuristic candidates and require contextual validation.",
        ],
    }


# E04 — Embeddings: CPU-based multilingual vectorization.
@lru_cache(maxsize=1)
def _embedder():
    from fastembed import TextEmbedding
    try:
        cache_dir = os.environ.get("LUNITA_FASTEMBED_CACHE")
        if cache_dir:
            pathlib.Path(cache_dir).mkdir(parents=True, exist_ok=True)
        return TextEmbedding(
            model_name=EMBEDDING_MODEL, cache_dir=cache_dir, threads=1, mmap=True,
        )
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
        if storage_path is None:
            storage_path = os.environ.get("LUNITA_VECTOR_DB_PATH")
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
    def __init__(
        self,
        documents: Sequence[Mapping[str, str]],
        storage_path: str | None = None,
        document_vectors: Sequence[Sequence[float]] | None = None,
    ):
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
        # E04 is invoked only when the calling command actually routes E04.
        # Commands without E04 must supply precomputed vectors; no hidden engine call.
        if document_vectors is None:
            vectors = embed_texts(self.texts)
            self.embedding_mode = "E04_RUNTIME_VECTOR_PREPARATION"
        else:
            vectors = [[float(value) for value in vector] for vector in document_vectors]
            self.embedding_mode = "PRECOMPUTED_VECTOR_INPUT"
        if len(vectors) != len(self.texts) or any(len(vector) != EMBEDDING_DIMENSION for vector in vectors):
            raise EngineContractError("RAG requires one 384-dimensional vector per source")
        if not all(math.isfinite(value) for vector in vectors for value in vector):
            raise EngineContractError("RAG vectors must contain finite values")
        self.index = VectorIndex(storage_path=storage_path)
        self.index.upsert(self.source_ids, self.texts, vectors)

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        query_vector: Sequence[float] | None = None,
    ) -> dict[str, Any]:
        _require_nonempty(query, "query")
        if query_vector is None:
            query_values = embed_texts([query])[0]
            query_mode = "E04_RUNTIME_QUERY_VECTOR"
        else:
            query_values = [float(value) for value in query_vector]
            query_mode = "PRECOMPUTED_QUERY_VECTOR"
        if len(query_values) != EMBEDDING_DIMENSION or not all(math.isfinite(value) for value in query_values):
            raise EngineContractError("RAG query vector must be finite and 384-dimensional")
        hits = self.index.search(query_values, limit=limit)
        return {
            "engine_id": "E03", "query_sha256": _sha256_bytes(query.encode("utf-8")),
            "retrieval_mode": self.embedding_mode,
            "query_vector_mode": query_mode,
            "retrieved_sources": hits,
            "context": "\n\n".join(
                f"[SOURCE:{hit['source_id']}][SHA256:{hit['source_sha256']}]\n{hit['text']}"
                for hit in hits
            ),
            "answer_generation": "DELEGATED_TO_E01",
        }

    def close(self) -> None:
        self.index.close()


# E06 — Directed multigraph with adjacency indexes and breadth-first traversal.
# The implementation is pure Python and preserves multi-edge relation metadata.
class DirectedKnowledgeGraph:
    def __init__(self):
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[tuple[str, str, dict[str, Any]]] = []
        self._adjacency: dict[str, list[str]] = {}

    def add_node(self, node_id: str, **attributes: Any) -> None:
        self._nodes.setdefault(node_id, {}).update(attributes)
        self._adjacency.setdefault(node_id, [])

    def add_edge(self, source: str, target: str, **attributes: Any) -> None:
        if source not in self._nodes or target not in self._nodes:
            raise EngineContractError("Knowledge graph edge references an undeclared node")
        self._edges.append((source, target, dict(attributes)))
        self._adjacency[source].append(target)

    def has_edge(self, source: str, target: str) -> bool:
        return any(destination == target for destination in self._adjacency.get(source, []))

    def nodes(self, data: bool = False):
        if data:
            return [(node_id, dict(attributes)) for node_id, attributes in self._nodes.items()]
        return list(self._nodes)

    def edges(self, data: bool = False):
        if data:
            return [(source, target, dict(attributes)) for source, target, attributes in self._edges]
        return [(source, target) for source, target, _ in self._edges]

    def shortest_path(self, source: str, target: str) -> list[str]:
        if source not in self._nodes or target not in self._nodes:
            raise EngineContractError("Knowledge graph path endpoint is undeclared")
        queue = deque([source])
        predecessor: dict[str, str | None] = {source: None}
        while queue:
            current = queue.popleft()
            if current == target:
                path = []
                while current is not None:
                    path.append(current)
                    current = predecessor[current]
                return list(reversed(path))
            for neighbor in self._adjacency[current]:
                if neighbor not in predecessor:
                    predecessor[neighbor] = current
                    queue.append(neighbor)
        raise EngineContractError(f"No directed path from {source} to {target}")

    def number_of_nodes(self) -> int:
        return len(self._nodes)

    def number_of_edges(self) -> int:
        return len(self._edges)

    def is_directed(self) -> bool:
        return True


def build_knowledge_graph(nodes: Sequence[Mapping[str, Any]], edges: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    graph = DirectedKnowledgeGraph()
    for node in nodes:
        node_id = _require_nonempty(str(node.get("id", "")), "node id")
        if node_id in graph._nodes:
            raise EngineContractError(f"Duplicate knowledge graph node: {node_id}")
        graph.add_node(node_id, **dict(node.get("attributes", {})))
    for edge in edges:
        source = _require_nonempty(str(edge.get("source", "")), "edge source")
        target = _require_nonempty(str(edge.get("target", "")), "edge target")
        relation = _require_nonempty(str(edge.get("relation", "")), "edge relation")
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
    linguistic_analysis: Mapping[str, Any] | None = None,
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
    if linguistic_analysis is not None:
        observations = dict(linguistic_analysis)
        if "tokens" not in observations or "sentences" not in observations:
            raise EngineContractError("Provided E02 linguistic analysis is incomplete")
        observation_source = "E02_ROUTE_INPUT"
    else:
        # E11 remains independently operable when the invoking command does
        # not route E02. These are lexical observations, not spaCy NLP claims.
        import re
        tokens = re.findall(r"[^\W_]+", source_text, flags=re.UNICODE)
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", source_text) if part.strip()]
        observations = {
            "tokens": [{"text": token} for token in tokens],
            "sentences": sentences,
            "entities": [],
        }
        observation_source = "E11_INTRINSIC_TEXT_OBSERVATION"
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
        "observation_source": observation_source,
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


# E12 — Formalization: typed mathematical AST, exact rational constants,
# deterministic normalization, and no parsing/eval of source code.
def _formal_number(value: Any) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EngineContractError("Only integer or finite decimal constants are allowed")
    if isinstance(value, float) and not math.isfinite(value):
        raise EngineContractError("Numeric constants must be finite")
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise EngineContractError("Invalid rational numeric constant") from exc


def _formal_expr_key(expression: Any) -> str:
    return json.dumps(_formal_expr_data(expression), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _formal_expr_data(expression: Any) -> dict[str, Any]:
    kind = expression[0]
    if kind == "symbol":
        return {"type": "symbol", "name": expression[1]}
    if kind == "number":
        value: Fraction = expression[1]
        return {"type": "number", "numerator": value.numerator, "denominator": value.denominator}
    if kind == "boolean":
        return {"type": "boolean", "value": expression[1]}
    return {"type": kind, "args": [_formal_expr_data(value) for value in expression[1]]}


def _formalize_node(node: Any, symbols: set[str]):
    if not isinstance(node, Mapping):
        raise EngineContractError("Formalization nodes must be typed objects")
    if set(node) == {"symbol"}:
        name = _require_nonempty(str(node["symbol"]), "symbol")
        if not name.isidentifier():
            raise EngineContractError(f"Invalid symbol name: {name}")
        symbols.add(name)
        return ("symbol", name)
    if set(node) == {"number"}:
        return ("number", _formal_number(node["number"]))
    if set(node) != {"op", "args"}:
        raise EngineContractError("Formalization nodes accept only symbol, number, or op/args shapes")
    operator = node["op"]
    args = node["args"]
    if not isinstance(args, list):
        raise EngineContractError("Formalization operator requires an args list")
    built = [_formalize_node(item, symbols) for item in args]
    arity = {"sub": 2, "div": 2, "pow": 2, "eq": 2, "lt": 2, "gt": 2, "not": 1}
    if operator not in {"add", "mul", "sub", "div", "pow", "eq", "lt", "gt", "and", "or", "not"}:
        raise EngineContractError(f"Unsupported formalization operator: {operator}")
    if operator in arity and len(built) != arity[operator]:
        raise EngineContractError(f"{operator} requires exactly {arity[operator]} arguments")
    if operator in {"add", "mul", "and", "or"} and len(built) < 2:
        raise EngineContractError(f"{operator} requires at least two arguments")

    # Flatten associative operators and sort commutative operands deterministically.
    if operator in {"add", "mul", "and", "or"}:
        flattened = []
        for item in built:
            flattened.extend(item[1] if item[0] == operator else [item])
        built = flattened

    if operator == "add":
        numeric = sum((item[1] for item in built if item[0] == "number"), Fraction(0))
        rest = [item for item in built if item[0] != "number"]
        if numeric or not rest:
            rest.append(("number", numeric))
        rest.sort(key=_formal_expr_key)
        return rest[0] if len(rest) == 1 else ("add", tuple(rest))
    if operator == "mul":
        numeric = Fraction(1)
        rest = []
        for item in built:
            if item[0] == "number":
                numeric *= item[1]
            else:
                rest.append(item)
        if numeric == 0:
            return ("number", Fraction(0))
        if numeric != 1 or not rest:
            rest.append(("number", numeric))
        rest.sort(key=_formal_expr_key)
        return rest[0] if len(rest) == 1 else ("mul", tuple(rest))
    if operator == "sub":
        left, right = built
        if right[0] == "number" and right[1] == 0:
            return left
        if left[0] == right[0] == "number":
            return ("number", left[1] - right[1])
    if operator == "div":
        left, right = built
        if right[0] == "number" and right[1] == 0:
            raise EngineContractError("Division by zero is not permitted")
        if right[0] == "number" and right[1] == 1:
            return left
        if left[0] == right[0] == "number":
            return ("number", left[1] / right[1])
    if operator == "pow":
        left, right = built
        if right[0] == "number" and right[1].denominator == 1:
            exponent = right[1].numerator
            if abs(exponent) > 64:
                raise EngineContractError("Constant exponent magnitude exceeds 64")
            if left[0] == "number":
                if left[1] == 0 and exponent < 0:
                    raise EngineContractError("Zero cannot be raised to a negative exponent")
                return ("number", left[1] ** exponent)
            if exponent == 1:
                return left
            if exponent == 0:
                return ("number", Fraction(1))
    if operator in {"eq", "lt", "gt"} and built[0][0] == built[1][0] == "number":
        left, right = built[0][1], built[1][1]
        result = left == right if operator == "eq" else left < right if operator == "lt" else left > right
        return ("boolean", result)
    if operator in {"and", "or"}:
        if all(item[0] == "boolean" for item in built):
            values = [item[1] for item in built]
            return ("boolean", all(values) if operator == "and" else any(values))
        built.sort(key=_formal_expr_key)
    return (operator, tuple(built))


def _formal_expr_string(expression: Any) -> str:
    kind = expression[0]
    if kind == "symbol":
        return expression[1]
    if kind == "number":
        value: Fraction = expression[1]
        return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
    if kind == "boolean":
        return "true" if expression[1] else "false"
    args = [_formal_expr_string(value) for value in expression[1]]
    if kind == "not":
        return f"not({args[0]})"
    return f"{kind}({','.join(args)})"


def formalize_expression(ast: Mapping[str, Any]) -> dict[str, Any]:
    symbols: set[str] = set()
    expression = _formalize_node(ast, symbols)
    canonical = _formal_expr_data(expression)
    return {
        "engine_id": "E12",
        "status": "PASS_FORMALIZATION",
        "expression": _formal_expr_string(_formalize_node(ast, set())),
        "simplified": _formal_expr_string(expression),
        "canonical_expression": _formal_expr_string(expression),
        "canonical_ast": canonical,
        "free_symbols": sorted(symbols),
        "symbolic_boolean": expression[0] in {"eq", "lt", "gt", "and", "or", "not", "boolean"},
        "normalization": "EXACT_RATIONALS; ASSOCIATIVE_FLATTENING; COMMUTATIVE_SORTING; SAFE_CONSTANT_FOLDING",
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
    command: str,
    required_agents: Sequence[str],
) -> dict[str, Any]:
    if engine_id != "E15":
        raise EngineContractError("Consensus aggregation is restricted to canonical engine E15")
    if command not in COMMAND_ENGINES or "E15" not in COMMAND_ENGINES[command]:
        raise EngineContractError(f"Command {command} does not route E15")
    expected_agents = COMMAND_AGENTS[command]
    if tuple(required_agents) != expected_agents:
        raise EngineContractError("Consensus participants must match the exact command team")
    if "Luna" not in required_agents:
        raise EngineContractError("Luna must chair every consensus route")
    required = set(required_agents)
    if len(required) != len(required_agents) or not required:
        raise EngineContractError("required_agents must be unique and non-empty")
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
        "command_routes": {
            command: {"agents": list(COMMAND_AGENTS[command]), "engines": list(COMMAND_ENGINES[command])}
            for command in COMMAND_ENGINES
        },
        "direct_agent_to_engine_assignment": "NOT_DEFINED_BY_CANONICAL_SPEC",
        "dependencies": engine_dependency_inventory(),
    }
