"""Negative tests for bounded metacognitive routing on unchanged user goals."""
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import elastic_automation as elastic
import metacog_diagnosis as meta

CONTRACT=json.loads((ROOT/"CONTRACT.v0.json").read_text())
NOW=datetime(2030,1,1,tzinfo=timezone.utc)


def observed():
    return {"memory_bytes":{"MemTotal":10000,"MemAvailable":9000},
            "root_fs_bytes":{"available":1024**3},"load":[0.01]}


def mission(kind="OBSERVE_LOCAL"):
    steps=([{"kind":"GATED_OPERATION","requested_capability":"CAP_FSTAB_FIX"}]
           if kind=="GATED_OPERATION" else [{"kind":"OBSERVE_LOCAL"}])
    return {"mission_id":"meta-001","user_objective":"Owner expects only approved scope",
            "model_proposal":"The LLM would optimize aggressively, but may not override the owner",
            "model":{"declared_name":"FIXTURE_MODEL","declared_version":"SELF_DECLARED"},
            "max_auto_steps":2,"steps":steps,
            "deadline_utc":(NOW+timedelta(hours=1)).isoformat()}


class MetacogTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.clock=[NOW]
        self.engine=elastic.Automation(Path(self.tmp.name)/"state",CONTRACT,
            observer=observed,clock=lambda:self.clock[0])

    def tearDown(self):
        self.tmp.cleanup()

    def check(self,**kwargs):
        return meta.diagnose(self.engine,"meta-001",observation=observed(),**kwargs)

    def test_owner_goal_preserved_and_three_review_passes(self):
        self.engine.admit(mission())
        report=self.check(same_uid_socket_verified=True)
        self.assertEqual(report["owner_goal_exact"],mission()["user_objective"])
        self.assertNotEqual(report["owner_goal_exact"],report["llm_proposal_separate"])
        self.assertEqual(len(report["review_passes"]),3)
        self.assertEqual(report["status"],"READY_REGISTERED_READONLY_STEP")
        self.assertFalse(report["next_action_executed"])
        self.assertFalse(report["certified"])

    def test_historical_runner_not_presently_alive(self):
        self.engine.admit(mission())
        report=self.check()
        self.assertEqual(report["status"],"HOLD_NO_LIVE_EXECUTION_CHANNEL")
        self.assertEqual(report["channel_status"]["github_runner"],"HISTORIC_PROOFS_NOT_LIVE")

    def test_evidenced_live_github_channel_allows_only_readonly_route(self):
        self.engine.admit(mission())
        report=self.check(github_runner_live_verified=True)
        self.assertEqual(report["status"],"READY_REGISTERED_READONLY_STEP")
        self.assertFalse(report["privileged_execution_allowed"])

    def test_gated_step_never_gets_authority_from_channels(self):
        self.engine.admit(mission("GATED_OPERATION"))
        self.engine.run_once("meta-001")
        report=self.check(same_uid_socket_verified=True,github_runner_live_verified=True)
        self.assertEqual(report["status"],"HOLD_INDEPENDENT_GATES_REQUIRED")
        self.assertEqual(report["g24"],"NOT_EXECUTED")
        self.assertNotIn("SCHEDULER_TICK_READONLY",report["next_route"])

    def test_readonly_completion_is_not_certification(self):
        self.engine.admit(mission())
        self.engine.run_once("meta-001")
        report=self.check(same_uid_socket_verified=True)
        self.assertEqual(report["status"],"READONLY_WORK_COMPLETE_UNCERTIFIED")
        self.assertFalse(report["certified"])

    def test_low_resources_prevent_next_step(self):
        self.engine.admit(mission())
        weak=observed()
        weak["memory_bytes"]["MemAvailable"]=1
        report=meta.diagnose(self.engine,"meta-001",observation=weak,same_uid_socket_verified=True)
        self.assertEqual(report["status"],"HOLD_RESOURCE_PRESSURE")
        self.assertNotIn("SCHEDULER_TICK_READONLY",report["next_route"])

    def test_signed_extension_needed_on_expiry(self):
        self.engine.admit(mission())
        self.clock[0]=NOW+timedelta(hours=2)
        report=self.check(same_uid_socket_verified=True)
        self.assertEqual(report["status"],"HOLD_EXPIRED_OWNER_REVISION_REQUIRED")
        self.assertIn("REQUEST_SIGNED_TIME_CONTRACT",report["next_route"])

    def test_state_tampering_stops_diagnosis(self):
        self.engine.admit(mission())
        file=self.engine.store
        doc=json.loads(file.read_text())
        doc["missions"]["meta-001"]["request"]["user_objective"]="changed"
        file.write_text(json.dumps(doc))
        with self.assertRaisesRegex(RuntimeError,"ELASTIC_STATE_ROLLBACK_OR_TAMPERING"):
            self.check(same_uid_socket_verified=True)

    def test_invalid_identity_cannot_probe(self):
        self.engine.admit(mission())
        with self.assertRaisesRegex(RuntimeError,"MISSION_ID_INVALID"):
            meta.diagnose(self.engine,"../someone",observation=observed())

if __name__=="__main__":
    unittest.main()
