from __future__ import annotations

import hashlib
import unittest

import engine_runtime_v1 as engine


class EngineRegistryTests(unittest.TestCase):
    def test_exact_fifteen_engines_and_fourteen_commands(self):
        result = engine.validate_registry()
        self.assertEqual("PASS_REGISTRY_CONFORMANCE", result["status"])
        self.assertEqual(15, result["engine_count"])
        self.assertEqual(14, result["command_count"])
        self.assertFalse(result["canonical_identity_mutation"])

    def test_command_team_to_engine_routes_are_canonical_and_not_reassigned(self):
        self.assertEqual(("Luna", "Ancapi"), engine.COMMAND_AGENTS["/play PA"])
        self.assertEqual(("E06", "E07", "E08", "E09", "E10", "E12", "E13", "E14"),
                         engine.COMMAND_ENGINES["/play PA"])
        engine.assert_command_route("/play PA", "Ancapi", "E06")
        engine.assert_command_route("/play MA", "Luna", "E15")
        with self.assertRaises(engine.EngineContractError):
            engine.assert_command_route("/play PA", "Katya", "E06")
        with self.assertRaises(engine.EngineContractError):
            engine.assert_command_route("/play PA", "Ancapi", "E15")

    def test_exact_fourteen_command_agent_routes_and_luna_presence(self):
        expected = {
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
        self.assertEqual(expected, engine.COMMAND_AGENTS)
        expected_engine_sets = {
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
        self.assertEqual(expected_engine_sets, engine.COMMAND_ENGINES)
        self.assertEqual(14, len(engine.COMMAND_ENGINES))
        self.assertTrue(all("Luna" in agents for agents in engine.COMMAND_AGENTS.values()))


class RealRuntimeEngineTests(unittest.TestCase):
    def test_e02_spanish_nlp_executes_tokenization_morphology_and_pos(self):
        result = engine.nlp_analyze("La arquitectura conserva la evidencia y valida las inferencias.")
        self.assertEqual("E02", result["engine_id"])
        self.assertEqual("es", result["language"])
        self.assertEqual("LUNITA_SPANISH_RULE_BASED_NLP_V1", result["model"])
        self.assertIn("spanish_lemma_and_pos_rules", result["pipeline"])
        self.assertGreaterEqual(len(result["tokens"]), 8)
        self.assertEqual(1, len(result["sentences"]))
        conserva = next(token for token in result["tokens"] if token["text"] == "conserva")
        self.assertEqual("conservar", conserva["lemma"])
        self.assertEqual("VERB", conserva["pos"])
        self.assertTrue(next(token for token in result["tokens"] if token["text"] == "La")["is_stop"])

    def test_e02_spanish_nlp_recognizes_proper_name_candidates(self):
        result = engine.nlp_analyze("Diego Norambuena valida la evidencia.")
        self.assertIn(
            {"text": "Diego Norambuena", "label": "PROPER_NAME_CANDIDATE", "confidence": "HEURISTIC"},
            result["entities"],
        )

    def test_e04_embedding_and_e05_vector_search_execute_real_models(self):
        texts = [
            "La conservación del agua potable requiere proteger las cuencas hidrográficas.",
            "Los equipos de fútbol preparan sus tácticas para el campeonato.",
        ]
        vectors = engine.embed_texts(texts)
        self.assertEqual(2, len(vectors))
        self.assertTrue(all(len(vector) == engine.EMBEDDING_DIMENSION for vector in vectors))
        index = engine.VectorIndex()
        try:
            index.upsert(["water", "football"], texts, vectors)
            query = engine.embed_texts(["proteger el agua de las cuencas"])[0]
            hits = index.search(query, limit=2)
            self.assertEqual(2, len(hits))
            self.assertEqual("water", hits[0]["source_id"])
            self.assertTrue(hits[0]["source_sha256"])
        finally:
            index.close()

    def test_e03_rag_returns_source_bound_context(self):
        rag = engine.RAGIndex([
            {"source_id": "src-water", "text": "La conservación del agua protege los ecosistemas y las cuencas."},
            {"source_id": "src-music", "text": "La armonía musical organiza alturas y relaciones entre sonidos."},
        ])
        try:
            result = rag.retrieve("proteger las cuencas de agua", limit=1)
            self.assertEqual("E03", result["engine_id"])
            self.assertEqual("src-water", result["retrieved_sources"][0]["source_id"])
            self.assertIn("[SHA256:", result["context"])
            self.assertEqual("DELEGATED_TO_E01", result["answer_generation"])
        finally:
            rag.close()

    def test_e06_knowledge_graph_executes_paths(self):
        result = engine.build_knowledge_graph(
            [{"id": "diego"}, {"id": "luna"}, {"id": "louksna"}],
            [{"source": "diego", "target": "luna", "relation": "uses"},
             {"source": "luna", "target": "louksna", "relation": "governed_by"}],
        )
        graph = result["graph"]
        self.assertEqual(3, result["node_count"])
        self.assertEqual(2, result["edge_count"])
        self.assertTrue(graph.has_edge("diego", "luna"))
        self.assertEqual(["diego", "luna", "louksna"], graph.shortest_path("diego", "louksna"))
        self.assertEqual(2, len(graph.edges(data=True)))
        with self.assertRaises(engine.EngineContractError):
            graph.shortest_path("louksna", "diego")

    def test_e07_rdf_parse_serialize_and_sparql(self):
        turtle = """
        @prefix ex: <https://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        ex:alice rdf:type ex:Researcher .
        """
        result = engine.rdf_query(
            turtle,
            "SELECT ?person WHERE { ?person a <https://example.org/Researcher> . }",
        )
        self.assertEqual("E07", result["engine_id"])
        self.assertEqual(1, result["triple_count"])
        self.assertEqual([["https://example.org/alice"]], result["rows"])

    def test_e08_owl_profile_validates_explicit_classes_and_properties(self):
        turtle = """
        @prefix ex: <https://example.org/> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        ex:Researcher a owl:Class .
        ex:Person a owl:Class .
        ex:studies a owl:ObjectProperty .
        """
        result = engine.validate_owl_ontology(turtle)
        self.assertEqual("PASS_OWL_PROFILE_VALIDATION", result["status"])
        self.assertEqual(2, len(result["classes"]))
        self.assertIn("https://example.org/studies", result["object_properties"])

    def test_e09_owlrl_semantic_inference_materializes_subclass_entailment(self):
        turtle = """
        @prefix ex: <https://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        ex:Researcher rdfs:subClassOf ex:Person .
        ex:alice rdf:type ex:Researcher .
        """
        result = engine.owlrl_infer(
            turtle,
            [["https://example.org/alice",
              "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
              "https://example.org/Person"]],
        )
        self.assertEqual("PASS", result["status"])
        self.assertGreater(result["inferred_triple_count"], 0)
        self.assertTrue(result["required_entailments"][0]["entailed"])

    def test_e10_safe_rule_engine_converges_without_eval(self):
        result = engine.evaluate_rules(
            {"risk": "high", "reviewed": True},
            [
                {"id": "R1", "when": {"field": "risk", "op": "eq", "value": "high"},
                 "then": {"field": "escalate", "value": True}},
                {"id": "R2", "when": {"field": "escalate", "op": "eq", "value": True},
                 "then": {"field": "status", "value": "HOLD"}},
            ],
        )
        self.assertEqual("PASS_RULES_CONVERGED", result["status"])
        self.assertEqual("HOLD", result["facts"]["status"])
        with self.assertRaises(engine.EngineContractError):
            engine.evaluate_rules({}, [{"id": "evil", "when": {"field": "x", "op": "__import__", "value": "os"},
                                        "then": {"field": "a", "value": 1}}])

    def test_e11_hermeneutic_separates_source_context_and_hypothesis(self):
        source = "La evidencia debe ser examinada dentro de su contexto histórico y literario."
        result = engine.hermeneutic_analyze(
            source, source_id="doc-1", genre="prosa", audience="comunidad original",
            historical_context="siglo I, Judea", preceding_context="párrafo anterior",
            following_context="párrafo posterior",
            hypotheses=[{"statement": "La evidencia exige análisis contextual.",
                         "evidence_spans": ["dentro de su contexto histórico y literario"]}],
        )
        self.assertEqual("READY_FOR_INDEPENDENT_HERMENEUTIC_VALIDATION", result["status"])
        self.assertTrue(result["source_text_preserved"])
        self.assertEqual(source, result["source"]["text"])
        self.assertEqual("PROVISIONAL_NOT_FINAL_MEANING", result["interpretation"]["status"])

    def test_e11_missing_context_fails_closed(self):
        result = engine.hermeneutic_analyze(
            "Texto de prueba", source_id="doc-1", genre="", audience="",
            historical_context="", preceding_context="", following_context="",
            hypotheses=[{"statement": "hipótesis", "evidence_spans": ["Texto"]}],
        )
        self.assertEqual("BLOCKED_CONTEXT_INCOMPLETE", result["status"])

    def test_e12_formalization_builds_symbolic_expression_without_eval(self):
        result = engine.formalize_expression({
            "op": "eq",
            "args": [
                {"op": "sub",
                 "args": [
                     {"op": "pow", "args": [{"symbol": "x"}, {"number": 2}]},
                     {"number": 1},
                 ]},
                {"number": 0},
            ],
        })
        self.assertEqual("PASS_FORMALIZATION", result["status"])
        self.assertEqual(["x"], result["free_symbols"])
        self.assertIn("eq(", result["canonical_expression"])
        self.assertEqual("EXACT_RATIONALS; ASSOCIATIVE_FLATTENING; COMMUTATIVE_SORTING; SAFE_CONSTANT_FOLDING",
                         result["normalization"])

    def test_e12_formalization_folds_exact_rationals_and_rejects_code(self):
        result = engine.formalize_expression({
            "op": "add",
            "args": [{"number": 0.5}, {"number": 0.25}, {"symbol": "x"}, {"number": 0.25}],
        })
        self.assertEqual("x + 1", result["simplified"] if result["simplified"] == "add(number(1),x)" else result["simplified"])
        with self.assertRaises(engine.EngineContractError):
            engine.formalize_expression({"op": "__import__", "args": [{"symbol": "os"}]})

    def test_e13_json_schema_validation_positive_and_negative(self):
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object", "required": ["engine_id", "status"],
            "properties": {"engine_id": {"const": "E13"}, "status": {"type": "string"}},
            "additionalProperties": False,
        }
        valid = engine.validate_json_schema({"engine_id": "E13", "status": "PASS"}, schema)
        invalid = engine.validate_json_schema({"engine_id": "E14"}, schema)
        self.assertTrue(valid["valid"])
        self.assertFalse(invalid["valid"])
        self.assertEqual("FAIL_VALIDATION", invalid["status"])

    def test_e14_provenance_chain_detects_tampering(self):
        genesis = "0" * 64
        first = engine.append_provenance_event(genesis, {"action": "ingest", "source": "doc-1"})
        second = engine.append_provenance_event(first["event_hash"], {"action": "validate", "result": "PASS"})
        self.assertEqual("PASS_PROVENANCE_CHAIN",
                         engine.verify_provenance_chain([first, second], genesis)["status"])
        tampered = dict(second)
        tampered["event"] = {"action": "validate", "result": "FORGED"}
        self.assertEqual("FAIL_PROVENANCE_HASH",
                         engine.verify_provenance_chain([first, tampered], genesis)["status"])

    def test_e15_consensus_requires_all_assigned_votes_and_same_evidence(self):
        evidence_hash = hashlib.sha256(b"same source").hexdigest()
        votes = [
            {"agent": agent, "decision": "APPROVE", "evidence_sha256": evidence_hash}
            for agent in ["Luna", "Ancapi"]
        ]
        result = engine.aggregate_consensus("E15", evidence_hash, votes, command="/play AE",
                                            required_agents=["Luna", "Ancapi"])
        self.assertEqual("PASS_CONSENSUS", result["status"])
        conflict = engine.aggregate_consensus(
            "E15", evidence_hash,
            [votes[0], {"agent": "Ancapi", "decision": "REJECT", "evidence_sha256": evidence_hash}],
            command="/play AE", required_agents=["Luna", "Ancapi"],
        )
        self.assertEqual("HOLD_CONSENSUS", conflict["status"])


class E01TargetRuntimeContractTests(unittest.TestCase):
    def test_e01_requires_real_qwen_weights_and_never_returns_a_stub(self):
        with self.assertRaises(engine.EngineUnavailable):
            engine.llm_infer("Devuelve OK.", model_path=__import__("pathlib").Path("/nonexistent/lunita-model.gguf"))

    def test_e01_target_qwen_artifact_is_discovered_when_deployed(self):
        model = engine.DEFAULT_MODEL
        if not model.is_file():
            self.skipTest("Target Qwen GGUF is not mounted in this hosted contract runner")
        binary = engine.discover_llama_cli()
        self.assertTrue(binary.is_file())
        self.assertTrue(binary.stat().st_mode & 0o111)
        result = engine.llm_infer(
            "Responde únicamente OK.",
            max_tokens=4,
            timeout_seconds=120,
        )
        self.assertEqual("E01", result["engine_id"])
        self.assertEqual(0, result["returncode"])
        self.assertTrue(result["output"].strip(), "Qwen completed without an output token")


if __name__ == "__main__":
    unittest.main(verbosity=2)
