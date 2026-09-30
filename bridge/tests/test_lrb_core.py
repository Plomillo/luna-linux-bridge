"""Read-only contract regression suite. Run: python3 -m unittest discover -s bridge/tests -v"""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("lrb_core", HERE / "lrb_core.py")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
CONTRACT = json.loads((HERE / "CONTRACT.v0.json").read_text())


class BridgeContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = core.secure_state(Path(self.tmp.name) / "state")

    def tearDown(self):
        self.tmp.cleanup()

    def test_contract_not_certified(self):
        self.assertEqual(CONTRACT["release"]["status"] if "status" in CONTRACT["release"] else CONTRACT["status"], "DRAFT_UNCERTIFIED")
        self.assertFalse(CONTRACT["release"]["certified"])

    def test_ledger_append_and_verify(self):
        ledger = core.EvidenceLedger(self.state)
        first = ledger.append("TEST", {"sample": 1})
        second = ledger.append("TEST", {"sample": 2})
        self.assertEqual(ledger.verify(), second["entry_hash"])
        self.assertEqual(second["previous_hash"], first["entry_hash"])

    def test_ledger_detects_tampering(self):
        ledger = core.EvidenceLedger(self.state)
        ledger.append("TEST", {"data": "original"})
        logfile = self.state / "EVENTS.jsonl"
        logfile.write_text(logfile.read_text().replace("original", "altered"))
        with self.assertRaisesRegex(RuntimeError, "EVIDENCE_HASH_BROKEN"):
            ledger.verify()

    def test_time_revision_and_hot_reload(self):
        default = core.load_time_policy(self.state, CONTRACT)
        new = core.update_time_policy(self.state, CONTRACT, default["revision"], 20, 600)
        self.assertEqual(new["revision"], 1)
        self.assertEqual(core.load_time_policy(self.state, CONTRACT)["heartbeat_sec"], 20)
        with self.assertRaisesRegex(RuntimeError, "STALE_TIME_REVISION"):
            core.update_time_policy(self.state, CONTRACT, 0, 30, 500)

    def test_time_extension_is_not_silently_authorized(self):
        core.update_time_policy(self.state, CONTRACT, 0, 20, 600)
        with self.assertRaisesRegex(RuntimeError, "EXTENDED_BUDGET_REQUIRES_NEW_AUTHORITY"):
            core.update_time_policy(self.state, CONTRACT, 1, 20, 900)

    def test_time_policy_upper_and_lower_bounds(self):
        with self.assertRaisesRegex(RuntimeError, "HEARTBEAT_OUT_OF_BOUNDS"):
            core.update_time_policy(self.state, CONTRACT, 0, 0, 10)
        with self.assertRaisesRegex(RuntimeError, "WORK_TIME_OUT_OF_BOUNDS"):
            core.update_time_policy(self.state, CONTRACT, 0, 15, 3601)

    def test_expected_and_user_objectives_are_separate(self):
        result = core.validate_claims("inspect exact PC", "I expect to inspect the PC", "declared", "v1")
        self.assertNotEqual(result["user_requirements"], result["model_expectations"])
        self.assertFalse(result["execution_allowed"])
        self.assertFalse(result["model"]["verified_by_provider"])

    def test_model_version_required(self):
        with self.assertRaisesRegex(RuntimeError, "MODEL_AND_VERSION_DECLARATION_REQUIRED"):
            core.validate_claims("inspect", "", "declared", "")

    def test_user_objective_required(self):
        with self.assertRaisesRegex(RuntimeError, "USER_OBJECTIVE_REQUIRED"):
            core.validate_claims("", "surprise action", "declared", "v1")

    def test_url_requires_exact_https_host(self):
        self.assertEqual(core.validate_url("https://example.org/docs", "example.org"), "https://example.org/docs")
        for url, host in (("http://example.org", "example.org"),
                          ("https://example.org", "other.org"),
                          ("https://localhost/path", "localhost"),
                          ("https://127.0.0.1/path", "127.0.0.1"),
                          ("https://example.org:8443/path", "example.org"),
                          ("https://u:password@example.org", "example.org")):
            with self.subTest(url=url):
                with self.assertRaises(RuntimeError):
                    core.validate_url(url, host)

    def test_priority_project_index_is_non_recursive(self):
        root = self.state / "priority"
        root.mkdir()
        (root / "projectA").mkdir()
        (root / "projectA" / "hidden").mkdir()
        (root / "projectB").write_text("safe")
        result = core.priority_index(root)
        self.assertEqual({x["name"] for x in result["items"]}, {"projectA", "projectB"})
        self.assertFalse(result["recursive_scan"])

    def test_symlinked_priority_root_denied(self):
        original = self.state / "original"
        original.mkdir()
        symlink = self.state / "alias"
        symlink.symlink_to(original, target_is_directory=True)
        with self.assertRaises(RuntimeError):
            core.priority_index(symlink)

    def test_readonly_observation_not_live_p3_certification(self):
        observed = core.snapshot(False)
        self.assertEqual(observed["project_partition"], "NOT_LIVE_VERIFIED")
        self.assertEqual(observed["bridge_root_shell"], "NOT_DEPLOYED")
        self.assertEqual(observed["sudo_noninteractive"], "NOT_PROBED")


if __name__ == "__main__":
    unittest.main()
