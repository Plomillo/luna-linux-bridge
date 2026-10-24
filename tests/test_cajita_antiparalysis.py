from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from cajita_antiparalysis import PersistentAntiParalysis, digest_bytes, retry_allowed

class AntiParalysisTests(unittest.TestCase):
 def test_three_identical_blockers_enter_hold(self):
  with tempfile.TemporaryDirectory() as tmp:
   ctl=PersistentAntiParalysis(tmp); digest=digest_bytes(b"task")
   seen=[ctl.observe_plan(task_id="task",input_sha256=digest,blockers=["adapter missing"],plan_status="PLAN_ONLY_BLOCKED") for _ in range(3)]
   self.assertEqual([x["state"] for x in seen],["BLOCKED_WAITING_FOR_PREREQUISITES","BLOCKED_WAITING_FOR_PREREQUISITES","HOLD_CONSCIOUS"])
   self.assertFalse(seen[-1]["automatic_retry"])
 def test_changed_blocker_resets_stagnation(self):
  with tempfile.TemporaryDirectory() as tmp:
   ctl=PersistentAntiParalysis(tmp); digest=digest_bytes(b"task")
   ctl.observe_plan(task_id="task",input_sha256=digest,blockers=["A"],plan_status="PLAN_ONLY_BLOCKED")
   ctl.observe_plan(task_id="task",input_sha256=digest,blockers=["A"],plan_status="PLAN_ONLY_BLOCKED")
   seen=ctl.observe_plan(task_id="task",input_sha256=digest,blockers=["B"],plan_status="PLAN_ONLY_BLOCKED")
   self.assertEqual(seen["stagnant_observations"],1)
 def test_retry_requires_every_precondition_and_finite_budget(self):
  good=dict(idempotent=True,effect_known=True,checkpoint_verified=True,attempts=0,deadline_expired=True)
  self.assertTrue(retry_allowed(**good))
  for key,value in [("idempotent",False),("effect_known",False),("checkpoint_verified",False),("attempts",3),("deadline_expired",False)]:
   self.assertFalse(retry_allowed(**{**good,key:value}))
 def test_journal_tampering_fails_closed(self):
  with tempfile.TemporaryDirectory() as tmp:
   ctl=PersistentAntiParalysis(tmp)
   ctl.observe_plan(task_id="task",input_sha256=digest_bytes(b"task"),blockers=["A"],plan_status="PLAN_ONLY_BLOCKED")
   path=Path(tmp)/"events.jsonl"; row=json.loads(path.read_text()); row["state"]="PASS"; path.write_text(json.dumps(row)+"\n")
   with self.assertRaisesRegex(RuntimeError,"CHAIN_INVALID"): ctl.status()
 def test_selftest(self):
  self.assertEqual(PersistentAntiParalysis.selftest()["status"],"PASS")

if __name__=="__main__": unittest.main()
