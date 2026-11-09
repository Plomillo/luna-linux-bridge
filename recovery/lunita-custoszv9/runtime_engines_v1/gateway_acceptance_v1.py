from __future__ import annotations

import hashlib
import unittest

import engine_gateway_v1 as gateway
import engine_runtime_v1 as engine


class CanonicalCommandGatewayTests(unittest.TestCase):
    def test_complete_canonical_route_matrix_for_all_fourteen_commands(self):
        self.assertEqual(14, len(engine.COMMAND_AGENTS))
        self.assertEqual(set(engine.COMMAND_AGENTS), set(engine.COMMAND_ENGINES))
        for command, agents in engine.COMMAND_AGENTS.items():
            engines = engine.COMMAND_ENGINES[command]
            self.assertTrue(agents, command)
            self.assertTrue(engines, command)
            self.assertIn("Luna", agents, command)
            for agent in agents:
                for engine_id in engines:
                    with self.subTest(command=command, agent=agent, engine=engine_id):
                        self.assertIsNone(engine.assert_command_route(command, agent, engine_id))
        self.assertEqual({f"E{i:02d}" for i in range(1, 16)},
                         set().union(*map(set, engine.COMMAND_ENGINES.values())))

    def test_support_agent_can_run_engine_in_its_assigned_command(self):
        receipt = gateway.execute_engine_for_route(
            "/play PA", "Ancapi", "E06",
            {
                "nodes": [{"id": "A"}, {"id": "B"}],
                "edges": [{"source": "A", "target": "B", "relation": "supports"}],
            },
        )
        self.assertEqual("PASS_ENGINE_OPERATION", receipt["status"])
        self.assertEqual("E06", receipt["engine_id"])
        self.assertEqual(2, receipt["result"]["node_count"])
        self.assertEqual(1, receipt["result"]["edge_count"])

    def test_agent_outside_command_team_is_denied(self):
        with self.assertRaises(engine.EngineContractError):
            gateway.execute_engine_for_route(
                "/play PA", "Katya", "E06",
                {"nodes": [{"id": "A"}], "edges": []},
            )

    def test_engine_outside_command_route_is_denied(self):
        with self.assertRaises(engine.EngineContractError):
            gateway.execute_engine_for_route(
                "/play PA", "Ancapi", "E15",
                {"evidence_sha256": hashlib.sha256(b"x").hexdigest(), "votes": []},
            )

    def test_e03_on_cp_requires_precomputed_vectors_not_hidden_e04(self):
        docs = [{"source_id": "src-1", "text": "fuente uno"}]
        vector = [0.0] * engine.EMBEDDING_DIMENSION
        vector[0] = 1.0
        receipt = gateway.execute_engine_for_route(
            "/play cp", "Katya", "E03",
            {"documents": docs, "query": "consulta", "document_vectors": [vector],
             "query_vector": vector},
        )
        self.assertEqual("PASS_ENGINE_OPERATION", receipt["status"])
        self.assertEqual("PRECOMPUTED_VECTOR_INPUT", receipt["result"]["retrieval_mode"])
        with self.assertRaises(engine.EngineContractError):
            gateway.execute_engine_for_route(
                "/play cp", "Katya", "E03", {"documents": docs, "query": "consulta"},
            )

    def test_e11_on_hermeneutic_command_does_not_call_unrouted_e02(self):
        source = "La interpretación requiere contexto histórico y literario."
        receipt = gateway.execute_engine_for_route(
            "/play H", "Josefina", "E11",
            {
                "source_text": source,
                "source_id": "doc-1",
                "genre": "prosa",
                "audience": "audiencia original",
                "historical_context": "contexto histórico",
                "preceding_context": "contexto anterior",
                "following_context": "contexto posterior",
                "hypotheses": [{
                    "statement": "La interpretación necesita contexto.",
                    "evidence_spans": ["contexto histórico y literario"],
                }],
            },
        )
        self.assertEqual("PASS_ENGINE_OPERATION", receipt["status"])
        self.assertEqual("E11_INTRINSIC_TEXT_OBSERVATION", receipt["result"]["observation_source"])

    def test_e15_consensus_uses_exact_team_for_the_selected_command(self):
        digest = hashlib.sha256(b"evidence").hexdigest()
        receipt = gateway.execute_engine_for_route(
            "/play AE", "Ancapi", "E15",
            {"evidence_sha256": digest, "votes": [
                {"agent": "Luna", "decision": "APPROVE", "evidence_sha256": digest},
                {"agent": "Ancapi", "decision": "APPROVE", "evidence_sha256": digest},
            ]},
        )
        self.assertEqual("PASS_ENGINE_OPERATION", receipt["status"])
        self.assertEqual("PASS_CONSENSUS", receipt["result"]["status"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
