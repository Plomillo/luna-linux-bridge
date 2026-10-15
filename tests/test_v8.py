"""Operational tests for the CUSTOSZ V8 candidate; stdlib unittest only."""
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from custoszv8.core import (
    CapabilityRegistry, EvidenceJournal, GitHubBridge, MissionStateMachine, TranslationEngine,
    V8Error, inspect_archive, inspect_wasm, is_sha256, selftest, sha256_bytes, validate_manifest,
    verify_component, run_native_readonly
)
from custoszv8.cli import validate_mission

class TestHashesAndManifest(unittest.TestCase):
    def test_sha256_known_vector(self):
        self.assertEqual(sha256_bytes(b"abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_sha_format(self):
        self.assertTrue(is_sha256("a" * 64))
        self.assertFalse(is_sha256("A" * 64))
        self.assertFalse(is_sha256("a" * 63))

    def test_manifest_valid_candidate(self):
        manifest = {
            "schema_version":"1.0.0", "artifact_id":"CUSTOSZV8", "artifact_version":"8.0.0-candidate",
            "artifact_status":"CANDIDATE", "canonical_authority_ref":"Louksna.md", "components":{},
            "capability_ownership":[], "gates":[],
            "certification":{"g23":"NOT_GRANTED","g24":"NOT_GRANTED"}, "limitations":[]
        }
        self.assertEqual(validate_manifest(manifest), [])

    def test_manifest_missing_fields_detected(self):
        self.assertTrue(validate_manifest({}))

    def test_release_requires_g23_g24(self):
        manifest = {
            "schema_version":"1.0.0", "artifact_id":"CUSTOSZV8", "artifact_version":"8.0.0-candidate",
            "artifact_status":"CANDIDATE", "canonical_authority_ref":"Louksna.md", "components":{},
            "capability_ownership":[], "gates":[],
            "certification":{"g23":"NOT_GRANTED","g24":"NOT_GRANTED"}, "limitations":[]
        }
        problems = validate_manifest(manifest, require_final_identity=True)
        self.assertTrue(any("G23" in x for x in problems))
        self.assertTrue(any("G24" in x for x in problems))

class TestCapabilityOwnership(unittest.TestCase):
    def test_unique_owner_resolves(self):
        registry = CapabilityRegistry([{"capability_id":"X","owner_component":"A","status":"VERIFIED"}])
        self.assertEqual(registry.resolve("X")["owner_component"], "A")

    def test_missing_capability_denied(self):
        with self.assertRaises(V8Error):
            CapabilityRegistry([]).resolve("missing")

    def test_conflicting_owners_detected(self):
        registry = CapabilityRegistry([
            {"capability_id":"X","owner_component":"A","status":"VERIFIED"},
            {"capability_id":"X","owner_component":"B","status":"VERIFIED"}
        ])
        self.assertTrue(any("conflicting owners" in x for x in registry.validate()))
        with self.assertRaises(V8Error):
            registry.resolve("X")

    def test_overlap_without_review_detected(self):
        registry = CapabilityRegistry([{
            "capability_id":"X","owner_component":"A","status":"VERIFIED",
            "overlaps":["Y"]
        }])
        self.assertTrue(any("overlap lacks review" in x for x in registry.validate()))

class TestMissionStateMachine(unittest.TestCase):
    def test_valid_transition(self):
        self.assertEqual(MissionStateMachine().transition("RECEIVED","PREFLIGHT"),"PREFLIGHT")

    def test_forbidden_transition_rejected(self):
        with self.assertRaises(V8Error):
            MissionStateMachine().transition("RECEIVED","RUNNING")

    def test_terminal_states(self):
        self.assertTrue(MissionStateMachine.is_terminal("COMPLETED"))
        self.assertFalse(MissionStateMachine.is_terminal("HOLD"))

class TestTranslationAndCode(unittest.TestCase):
    TEXT = ("Si el runtime no responde en el plazo establecido, guarda la evidencia, "
            "intenta recuperarlo una sola vez y, si falla, detén esa misión sin bloquear las demás.")

    def test_supported_es_en_translation(self):
        result = TranslationEngine().translate(self.TEXT, "es", "en")
        self.assertEqual(result["validation_state"], "PASS", result)
        self.assertIn("attempt recovery exactly once", result["translation"])
        self.assertIn("without blocking independent missions", result["translation"])
        self.assertFalse(result["execution_authorized"])

    def test_unknown_text_not_falsely_translated(self):
        result = TranslationEngine().translate("utterly novel unregistered request", "en", "es")
        self.assertEqual(result["validation_state"], "UNKNOWN")
        self.assertEqual(result["translation"], "")

    def test_partial_translation_is_explicit(self):
        result = TranslationEngine().translate("si el runtime no responde magic", "es", "en")
        self.assertEqual(result["validation_state"], "PARTIAL")
        self.assertIn("magic", result["translation"])

    def test_protected_identifier_preserved(self):
        source = self.TEXT + " Revisa " + chr(96) + "CUSTOSZV8.pyz" + chr(96) + "."
        result = TranslationEngine().translate(source, "es", "en")
        self.assertIn("CUSTOSZV8.pyz", result["translation"])
        self.assertTrue(result["protected_tokens_preserved"])

    def test_code_static_analysis_does_not_execute(self):
        source = "import os\ndef f():\n    os.remove('x')\n"
        result = TranslationEngine.code_to_english(source)
        self.assertFalse(result["source_executed"])
        self.assertTrue(any(x["call"] == "os.remove" for x in result["potentially_effectful_calls"]))

    def test_invalid_python_rejected(self):
        with self.assertRaises(V8Error):
            TranslationEngine.code_to_english("def broken(:\n pass")

class TestEvidenceJournal(unittest.TestCase):
    def test_append_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            journal = EvidenceJournal(Path(td)/"events.jsonl")
            journal.append("MISSION_RECEIVED", {"x":1})
            journal.append("MISSION_STARTED", {"x":2})
            self.assertEqual(journal.verify()["records"], 2)

    def test_tamper_detected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"events.jsonl"
            journal = EvidenceJournal(path)
            journal.append("TEST", {"value":"original"})
            row = json.loads(path.read_text())
            row["payload"]["value"] = "tampered"
            path.write_text(json.dumps(row)+"\n")
            with self.assertRaises(V8Error):
                journal.verify()

    def test_incomplete_final_record_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"events.jsonl"
            path.write_text('{"partial":true}')
            with self.assertRaises(V8Error):
                EvidenceJournal(path).verify()

class TestArtifactAndWasm(unittest.TestCase):
    def test_zipapp_inspected_without_execution(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"x.pyz"
            with zipfile.ZipFile(path,"w") as z:
                z.writestr("__main__.py","raise SystemExit(99)\n")
            result=inspect_archive(path)
            self.assertEqual(result["format"],"ZIPAPP_CANDIDATE")
            self.assertFalse(result["execution_authorized"])

    def test_zip_path_traversal_detected(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"bad.pyz"
            with zipfile.ZipFile(path,"w") as z:
                z.writestr("__main__.py","pass\n")
                z.writestr("../outside.txt","bad\n")
            with self.assertRaises(V8Error):
                inspect_archive(path)

    def test_digest_conflict_detected(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"x.bin"; path.write_bytes(b"real")
            result=verify_component(path, "0"*64)
            self.assertEqual(result["status"],"CONFLICT")
            self.assertFalse(result["execution_authorized"])

    def test_wasm_export_metadata(self):
        module=b"\x00asm\x01\x00\x00\x00\x07\x05\x01\x01f\x00\x00"
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"x.wasm"; path.write_bytes(module)
            result=inspect_wasm(path)
            self.assertEqual(result["exports"][0]["name"],"f")
            self.assertFalse(result["function_signatures_verified"])

    def test_invalid_wasm_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"bad.wasm"; path.write_bytes(b"notwasm")
            with self.assertRaises(V8Error):
                inspect_wasm(path)

class TestAuthorizationAndBridge(unittest.TestCase):
    def test_native_execution_denied_without_opt_in(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"x.pyz"
            with zipfile.ZipFile(path,"w") as z: z.writestr("__main__.py","pass\n")
            old=os.environ.pop("CUSTOSZV8_ALLOW_NATIVE_EXECUTION",None)
            try:
                with self.assertRaises(V8Error):
                    run_native_readonly(path,"v07-status",expected_sha256=__import__("hashlib").sha256(path.read_bytes()).hexdigest(),
                                        authorization_ref=None)
            finally:
                if old is not None: os.environ["CUSTOSZV8_ALLOW_NATIVE_EXECUTION"]=old

    def test_native_command_allowlist_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"x.pyz"
            with zipfile.ZipFile(path,"w") as z: z.writestr("__main__.py","pass\n")
            os.environ["CUSTOSZV8_ALLOW_NATIVE_EXECUTION"]="1"
            try:
                with self.assertRaises(V8Error):
                    run_native_readonly(path,"install",expected_sha256=__import__("hashlib").sha256(path.read_bytes()).hexdigest(),
                                        authorization_ref="AUTH-TEST")
            finally:
                os.environ.pop("CUSTOSZV8_ALLOW_NATIVE_EXECUTION",None)

    def test_github_write_denied_without_token_and_authorization(self):
        bridge=GitHubBridge(token=None)
        with self.assertRaises(V8Error):
            bridge._request("POST","/repos/example/repo/actions/workflows/x/dispatches",{},None)

    def test_invalid_repo_name_rejected(self):
        with self.assertRaises(V8Error):
            GitHubBridge._validate_repo("bad owner","repo")

    def test_mission_missing_deadline_blocked(self):
        m = {"mission_id":"MIS-1","scope":{"environment_id":"test"},
            "capability_plan":["X"],"authorization_ref":"AUTH-1","acceptance_criteria":["AC-1"],
            "target_candidate":{"artifact_sha256":"a"*64}}
        result=validate_mission(m)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertTrue(any("deadline" in x for x in result["issues"]))

    def test_core_selftest(self):
        result=selftest()
        self.assertEqual(result["status"],"PASS",result)
        self.assertEqual(result["g23"],"NOT_GRANTED")
        self.assertEqual(result["g24"],"NOT_GRANTED")

if __name__ == "__main__":
    unittest.main(verbosity=2)
