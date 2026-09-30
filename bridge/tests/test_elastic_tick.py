"""A bounded scheduler must never enlarge scope or repeat terminal work."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import elastic_automation as elastic
import elastic_tick as tick

CONTRACT = json.loads((ROOT / "CONTRACT.v0.json").read_text())
NOW = lambda: datetime(2030, 1, 1, tzinfo=timezone.utc)


def mission(mid, deadline="2030-01-02T00:00:00Z", gated=False):
    return {"mission_id": mid, "user_objective": "Exact owner observation",
            "model_proposal": "Suggest read-only verification",
            "model": {"declared_name": "TEST", "declared_version": "SELF_REPORTED"},
            "deadline_utc": deadline, "max_auto_steps": 2,
            "steps": ([{"kind": "GATED_OPERATION", "requested_capability": "CAP_REBOOT"}]
                      if gated else [{"kind": "OBSERVE_LOCAL"}])}


def observed():
    return {"memory_bytes": {"MemTotal": 100, "MemAvailable": 99},
            "root_fs_bytes": {"available": 1024**3}, "load": [0.1]}


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        agent = elastic.Automation(Path(self.temp.name) / "state", CONTRACT,
                                   observer=observed, clock=NOW)
        self.agent = agent
        self.sched = tick.Scheduler(agent)

    def tearDown(self):
        self.temp.cleanup()

    def test_idle_is_not_a_false_pass(self):
        x = self.sched.tick()
        self.assertEqual(x["status"], "IDLE_NO_ELIGIBLE_TASK")
        self.assertEqual(x["executed_steps"], 0)
        self.assertFalse(x["certified"])

    def test_deadline_priority_and_dryrun(self):
        self.agent.admit(mission("later", "2030-01-03T00:00:00Z"))
        self.agent.admit(mission("earlier", "2030-01-02T00:00:00Z"))
        d = self.sched.tick(dry_run=True)
        self.assertEqual(d["selected"], "earlier")
        self.assertEqual(self.sched.tick()["selected"], "earlier")
        self.assertEqual(self.sched.tick()["selected"], "later")
        self.assertEqual(self.sched.tick()["executed_steps"], 0)

    def test_gated_step_remains_blocked(self):
        self.agent.admit(mission("blocked", gated=True))
        first = self.sched.tick()
        self.assertEqual(first["status"], "WAITING_FRESH_G23_G24")
        self.assertEqual(first["executed_steps"], 0)
        self.assertEqual(self.sched.tick()["status"], "IDLE_NO_ELIGIBLE_TASK")

    def test_priority_never_bypasses_user_resource_guard(self):
        self.agent.admit(mission("pressure"))
        self.agent.observer = lambda: {
            "memory_bytes": {"MemTotal": 100, "MemAvailable": 1},
            "root_fs_bytes": {"available": 1024**3}, "load": [0.1]}
        x = self.sched.tick()
        self.assertEqual(x["status"], "HOLD_RESOURCE_PRESSURE")
        self.assertEqual(x["executed_steps"], 0)
        self.assertEqual(self.agent.report("pressure")["next_step"], 0)


if __name__ == "__main__":
    unittest.main()
