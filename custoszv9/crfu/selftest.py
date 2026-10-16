"""Deterministic CRFU smoke tests."""
import tempfile
from pathlib import Path
from .anti_paralysis import decide_next_action,state_fingerprint
from .evidence import append_event,verify_journal
from .model import sha256_bytes
from .planner import ActionSpec,build_plan
from .recovery import checkpoint_record,verify_restoration
from .resources import ResourceBudget,ResourceSnapshot,evaluate_budget
def run_selftest()->dict:
 checks={}
 p=build_plan([ActionSpec("b",("a",)),ActionSpec("a")],max_alternatives=4,available_capabilities=set(),admissible_effects=set())
 checks["deterministic_topological_plan"]=p["status"]=="PLAN_VALIDATED" and p["ordered_actions"]==["a","b"]
 c=build_plan([ActionSpec("a",("b",)),ActionSpec("b",("a",))],max_alternatives=4,available_capabilities=set(),admissible_effects=set())
 checks["dependency_cycle_denied"]=c["status"]=="DENIED"
 r=evaluate_budget(ResourceBudget(1,1,0,1),ResourceSnapshot(None,None,None,"2026-01-01T00:00:00Z","selftest","UNKNOWN"))
 checks["unknown_resources_hold"]=r["status"]=="HOLD"
 h=state_fingerprint({"phase":1})
 d=decide_next_action(action_id="a",strategy_id="s",state_hash=h,previous_attempts=[{"action_id":"a","strategy_id":"s","state_hash":h}],new_evidence=False,planning_budget_remaining=1,retry_budget_remaining=0)
 checks["repeated_strategy_blocked"]=d["decision"]=="BLOCKED"
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/"journal.jsonl"
  ev={"operation_id":"o","mission_id":"m","sequence_id":1,"timestamp_utc":"2026-01-01T00:00:00Z","actor":"selftest","tool_and_version":"crfu-selftest/1","source_identity":"test","input_hash_and_size":{"sha256":sha256_bytes(b"i"),"size_bytes":1},"output_hash_and_size":{"sha256":sha256_bytes(b"o"),"size_bytes":1},"validation_result":"PASS","authorization_evidence_reference":"test-only","dependency_context":[],"rollback_pointer":None,"status":"TEST_ONLY"}
  append_event(path,ev);checks["journal_chain_valid"]=verify_journal(path)["status"]=="PASS"
  path.write_text(path.read_text().replace('"status":"TEST_ONLY"','"status":"TAMPERED"'),encoding="utf-8")
  checks["journal_tamper_detected"]=verify_journal(path)["status"]=="FAIL"
 payload=b"checkpoint";dep=sha256_bytes(b"deps");rec=checkpoint_record(payload,checkpoint_id="cp",state_identity="s",dependency_fingerprint=dep)
 checks["checkpoint_not_restoration"]=rec["restoration_proven"] is False
 restored=verify_restoration(rec,payload,expected_state_identity="s",expected_dependency_fingerprint=dep,invariants_pass=True,journal_valid=True)
 checks["restoration_postvalidated"]=restored["restoration_proven"] is True
 failed=sorted(k for k,v in checks.items() if not v)
 return {"schema":"CUSTOSZV9_CRFU_SELFTEST/1.0","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,"certification":"NOT_GRANTED"}
