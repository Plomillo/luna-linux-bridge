"""Command-team bound gateway for real E01-E15 operations."""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Mapping

import engine_runtime_v1 as engine


def _need(payload: Mapping[str, Any], key: str) -> Any:
    if key not in payload:
        raise engine.EngineContractError(f"Required input missing: {key}")
    return payload[key]


def execute_engine_for_route(
    command: str,
    agent: str,
    engine_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute one real engine operation through its canonical command route."""
    engine.assert_command_route(command, agent, engine_id)
    if not isinstance(payload, Mapping):
        raise engine.EngineContractError("Engine payload must be a JSON object")

    if engine_id == "E01":
        result = engine.llm_infer(
            _need(payload, "prompt"),
            model_path=pathlib.Path(payload.get("model_path", str(engine.DEFAULT_MODEL))),
            llama_cli=pathlib.Path(payload["llama_cli"]) if payload.get("llama_cli") else None,
            max_tokens=int(payload.get("max_tokens", 96)),
            timeout_seconds=int(payload.get("timeout_seconds", 120)),
        )
    elif engine_id == "E02":
        result = engine.nlp_analyze(_need(payload, "text"))
    elif engine_id == "E03":
        documents = _need(payload, "documents")
        query = _need(payload, "query")
        if "E04" in engine.COMMAND_ENGINES[command]:
            rag = engine.RAGIndex(documents, storage_path=payload.get("storage_path"))
            try:
                result = rag.retrieve(query, limit=int(payload.get("limit", 5)))
            finally:
                rag.close()
        else:
            document_vectors = _need(payload, "document_vectors")
            query_vector = _need(payload, "query_vector")
            rag = engine.RAGIndex(
                documents, storage_path=payload.get("storage_path"),
                document_vectors=document_vectors,
            )
            try:
                result = rag.retrieve(query, limit=int(payload.get("limit", 5)),
                                      query_vector=query_vector)
            finally:
                rag.close()
    elif engine_id == "E04":
        result = {
            "engine_id": "E04",
            "vectors": engine.embed_texts(_need(payload, "texts")),
            "model": engine.EMBEDDING_MODEL,
            "dimension": engine.EMBEDDING_DIMENSION,
        }
    elif engine_id == "E05":
        ids = _need(payload, "ids")
        texts = _need(payload, "texts")
        vectors = _need(payload, "vectors")
        query_vector = _need(payload, "query_vector")
        index = engine.VectorIndex(storage_path=payload.get("storage_path"))
        try:
            index.upsert(ids, texts, vectors)
            result = {
                "engine_id": "E05",
                "hits": index.search(query_vector, limit=int(payload.get("limit", 5))),
                "indexed_count": len(ids),
            }
        finally:
            index.close()
    elif engine_id == "E06":
        graph_result = engine.build_knowledge_graph(_need(payload, "nodes"), _need(payload, "edges"))
        graph = graph_result.pop("graph")
        graph_result["nodes"] = [
            {"id": node_id, "attributes": attributes}
            for node_id, attributes in graph.nodes(data=True)
        ]
        graph_result["edges"] = [
            {"source": source, "target": target, **attributes}
            for source, target, attributes in graph.edges(data=True)
        ]
        result = graph_result
    elif engine_id == "E07":
        result = engine.rdf_query(_need(payload, "turtle_text"), _need(payload, "sparql"))
    elif engine_id == "E08":
        result = engine.validate_owl_ontology(_need(payload, "turtle_text"))
    elif engine_id == "E09":
        result = engine.owlrl_infer(_need(payload, "turtle_text"), payload.get("required_triples", ()))
    elif engine_id == "E10":
        result = engine.evaluate_rules(_need(payload, "facts"), _need(payload, "rules"),
                                       max_passes=int(payload.get("max_passes", 8)))
    elif engine_id == "E11":
        result = engine.hermeneutic_analyze(
            _need(payload, "source_text"),
            source_id=_need(payload, "source_id"),
            genre=_need(payload, "genre"),
            audience=_need(payload, "audience"),
            historical_context=_need(payload, "historical_context"),
            preceding_context=_need(payload, "preceding_context"),
            following_context=_need(payload, "following_context"),
            hypotheses=_need(payload, "hypotheses"),
            linguistic_analysis=payload.get("linguistic_analysis"),
        )
    elif engine_id == "E12":
        result = engine.formalize_expression(_need(payload, "ast"))
    elif engine_id == "E13":
        result = engine.validate_json_schema(_need(payload, "instance"), _need(payload, "schema"))
    elif engine_id == "E14":
        action = _need(payload, "action")
        if action == "append":
            result = {
                "engine_id": "E14",
                "status": "PASS_EVENT_HASHED",
                "record": engine.append_provenance_event(
                    _need(payload, "previous_hash"), _need(payload, "event")
                ),
            }
        elif action == "verify":
            result = engine.verify_provenance_chain(
                _need(payload, "events"), payload.get("genesis", "0" * 64)
            )
        else:
            raise engine.EngineContractError("E14 action must be append or verify")
    elif engine_id == "E15":
        result = engine.aggregate_consensus(
            "E15", _need(payload, "evidence_sha256"), _need(payload, "votes"),
            command=command, required_agents=engine.COMMAND_AGENTS[command],
        )
    else:
        raise engine.EngineContractError(f"No operation adapter for {engine_id}")

    return {
        "schema": "LUNITA_ENGINE_EXECUTION_RECEIPT/1.0",
        "status": "PASS_ENGINE_OPERATION" if result.get("status", "PASS") not in {
            "FAIL", "FAIL_VALIDATION", "FAIL_REQUIRED_ENTAILMENT",
            "FAIL_PROVENANCE_CHAIN", "FAIL_PROVENANCE_HASH",
            "HOLD_CONSENSUS", "BLOCKED_CONTEXT_INCOMPLETE",
            "BLOCKED_UNGROUNDED_HYPOTHESIS",
        } else "HOLD_ENGINE_OPERATION",
        "command": command,
        "agent": agent,
        "engine_id": engine_id,
        "engine_name": engine.ENGINE_NAMES[engine_id],
        "result": result,
        "certification": "NOT_GRANTED",
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=pathlib.Path,
                        help="JSON object with command, agent, engine_id and payload")
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        result = execute_engine_for_route(
            request["command"], request["agent"], request["engine_id"], request["payload"]
        )
    except (OSError, ValueError, KeyError, engine.EngineContractError,
            engine.EngineUnavailable) as exc:
        print(json.dumps({"status": "DENIED_OR_BLOCKED", "error": str(exc)}, ensure_ascii=False, indent=2),
              file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS_ENGINE_OPERATION" else 3


if __name__ == "__main__":
    raise SystemExit(main())
