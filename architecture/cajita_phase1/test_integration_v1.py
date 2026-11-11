from __future__ import annotations

import unittest

import integration_v1 as integration


SOURCE = "La evidencia debe ser examinada dentro de su contexto histórico."
PAYLOAD = {
    "source_text": SOURCE,
    "source_id": "doc-1",
    "genre": "prosa",
    "audience": "comunidad original",
    "historical_context": "siglo I",
    "preceding_context": "párrafo anterior",
    "following_context": "párrafo posterior",
    "hypotheses": [{
        "statement": "La evidencia exige análisis contextual.",
        "evidence_spans": ["dentro de su contexto histórico"],
    }],
}

EXPECTED_CFE_COUNTS = {
    "/help": 14,
    "/play PT": 40,
    "/play PA": 40,
    "/play DCI": 34,
    "/play DCIL": 54,
    "/play traductor": 44,
    "/play e": 34,
    "/play ema": 24,
    "/play p": 24,
    "/play c": 34,
    "/play cp": 64,
    "/play MA": 74,
    "/play H": 34,
    "/play AE": 40,
}


class Phase1IntegrationTests(unittest.TestCase):
    def test_pcreadme_gate_is_read_and_not_certified(self):
        gate = integration.pcreadme_gate()
        self.assertEqual("READ_AND_VERIFIED", gate["status"])
        self.assertEqual(78, gate["block_count"])
        self.assertEqual(64, len(gate["sha256"]))
        self.assertFalse(gate["certified"])
        self.assertEqual("FORBIDDEN", gate["main_mutation"])

    def test_fourteen_commands_keep_agents_engines_and_cfe(self):
        self.assertEqual(set(integration.engine.COMMAND_ENGINES), set(EXPECTED_CFE_COUNTS))
        for command, count in EXPECTED_CFE_COUNTS.items():
            binding = integration.command_binding(command)
            self.assertIn("Luna", binding["agents"])
            self.assertEqual(count, len(binding["cfe"]))
            self.assertEqual(binding["cfe"], tuple(sorted(set(binding["cfe"]))))
            self.assertFalse(binding["identity_mutation"])
        self.assertIn("E11", integration.engine.COMMAND_ENGINES["/play H"])
        self.assertNotIn("E11", integration.engine.COMMAND_ENGINES["/play traductor"])
        self.assertEqual(
            ("Luna", "Josefina", "Katya"),
            integration.engine.COMMAND_AGENTS["/play cp"],
        )

    def test_eighteen_frames_are_operational_profiles(self):
        self.assertEqual(18, len(integration.FRAME_PROFILES))
        methods = set()
        for name in integration.FRAME_ORDER:
            profile = integration.FRAME_PROFILES[name]
            self.assertEqual(name, profile["frame_id"])
            for field in integration._PROFILE_FIELDS:
                self.assertTrue(profile[field].strip(), field)
            methods.add(profile["method"])
        self.assertEqual(18, len(methods))

    def test_single_frame_is_not_mixed_with_the_other_seventeen(self):
        selected = integration.select_frames("Aplica el marco judío a este párrafo.", command="/play H")
        self.assertEqual("PRIMARY_ONLY", selected["mode"])
        self.assertEqual("Jewish", selected["primary"])
        self.assertEqual((), selected["secondary"])

    def test_exhaustive_request_uses_all_eighteen_without_collapsing_them(self):
        selected = integration.select_frames(
            "Necesito una comparación exhaustiva de los 18 marcos.", command="/play H"
        )
        names = (selected["primary"], *selected["secondary"])
        self.assertEqual("EXHAUSTIVE_18", selected["mode"])
        self.assertEqual(18, len(set(names)))
        self.assertEqual(set(integration.FRAME_ORDER), set(names))

    def test_ambiguous_frames_fail_closed(self):
        selected = integration.select_frames(
            "Compara el marco calvinista con el marco luterano.", command="/play H"
        )
        self.assertEqual("AMBIGUOUS", selected["mode"])
        self.assertIsNone(selected["primary"])

    def test_everyday_translation_does_not_receive_a_theological_frame(self):
        cycle = integration.integrate_request("/play traductor", "Traduce este correo al inglés.")
        self.assertEqual("GENERAL", cycle["translation_modality"])
        self.assertEqual("NOT_APPLICABLE", cycle["frames"]["mode"])
        self.assertNotIn("3. Transcripción", cycle["domains"])
        self.assertEqual((), tuple(cycle["engines_executed"]))
        self.assertEqual("NOT_GRANTED", cycle["certification"])

    def test_audio_goes_to_transcription_before_translation(self):
        cycle = integration.integrate_request(
            "/play traductor", "mensaje de voz", audio=True
        )
        self.assertEqual("TRANSCRIPTION_THEN_TRANSLATION", cycle["translation_modality"])
        self.assertIn("3. Transcripción", cycle["domains"])
        self.assertIn("4. Traductor Inteligente", cycle["domains"])
        self.assertEqual((), tuple(cycle["engines_executed"]))

    def test_biblical_translation_does_not_silently_call_e11(self):
        before = integration.engine.COMMAND_ENGINES["/play traductor"]
        cycle = integration.integrate_request(
            "/play traductor", "Traduce este versículo: " + SOURCE
        )
        self.assertEqual(before, integration.engine.COMMAND_ENGINES["/play traductor"])
        self.assertNotIn("E11", before)
        self.assertEqual("HANDOFF_NOT_A_ROUTE_CHANGE", cycle["frames"]["mode"])
        self.assertEqual((), tuple(cycle["engines_executed"]))
        self.assertFalse(cycle["privileged_operations_authorized"])

    def test_authorized_handoff_runs_e11_on_play_h_not_inside_traductor(self):
        cycle = integration.integrate_request(
            "/play traductor",
            "Traduce este versículo: " + SOURCE,
            authorize_hermeneutic_handoff=True,
            hermeneutic_payload=PAYLOAD,
        )
        self.assertEqual(1, len(cycle["engines_executed"]))
        executed = cycle["engines_executed"][0]
        self.assertEqual("/play H", executed["command"])
        self.assertEqual("E11", executed["engine_id"])
        self.assertEqual("PASS_ENGINE_OPERATION", executed["status"])
        self.assertTrue(executed["source_preserved"])
        self.assertNotIn("E11", integration.engine.COMMAND_ENGINES["/play traductor"])

    def test_play_h_executes_existing_e11_with_one_frame(self):
        cycle = integration.integrate_request(
            "/play H",
            "Lee este versículo con el marco calvinista. " + SOURCE,
            hermeneutic_payload=PAYLOAD,
        )
        self.assertEqual("Calvinist", cycle["frames"]["primary"])
        self.assertEqual((), cycle["frames"]["secondary"])
        self.assertEqual("REFORMED_TULIP_SOLA_SCRIPTURA_SUPREME",
                         cycle["frames"]["theological_configuration"]["identity"])
        self.assertNotEqual("Calvinist", cycle["frames"]["theological_configuration"]["identity"])
        self.assertEqual("PASS_ENGINE_OPERATION", cycle["engines_executed"][0]["status"])
        self.assertEqual("PROVISIONAL_NOT_FINAL_MEANING", cycle["engines_executed"][0]["interpretation_status"])
        self.assertEqual(15, len(cycle["stages"]))
        self.assertEqual(
            integration.COGNITIVE_STAGES,
            tuple(row["stage"] for row in cycle["stages"]),
        )

    def test_unknown_command_and_privileged_verb_fail_closed_without_stopping_the_cycle(self):
        cycle = integration.integrate_request("/play nope", "modify_main")
        self.assertEqual("FAIL_CLOSED", cycle["stages"][6]["status"])
        self.assertEqual(15, len(cycle["stages"]))
        self.assertTrue(any(item.startswith("PRIVILEGED_OPERATION_DENIED") for item in cycle["errors"]))
        self.assertFalse(cycle["privileged_operations_authorized"])
        self.assertEqual("NOT_GRANTED", cycle["g23"])
        self.assertFalse(cycle["console"]["executes_engines"])

    def test_memory_is_one_store_shared_by_brain_and_orchestration(self):
        memory = integration.GovernedMemory()
        first = integration.integrate_request("/help", "qué rutas existen", memory=memory)
        second = integration.integrate_request("/play p", "plan de trabajo", memory=memory)
        self.assertEqual(1, first["memory"]["stores"])
        self.assertEqual("6. Sistema Inteligente", memory.PHYSICAL_DOMAIN)
        self.assertEqual(2, len(memory))
        self.assertEqual(2, second["memory"]["records"])
        self.assertEqual(first["console"]["command"], "/help")
        self.assertIs(first["console"]["engines_executed"], first["engines_executed"])


if __name__ == "__main__":
    unittest.main()
