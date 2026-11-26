"""One local path from instruction to checked evidence. It does not certify the case."""
from __future__ import annotations

from pathlib import Path

from metagente_luna_s3.evidence import verify_run, write_run
from metagente_luna_s3.interpret import interpret
from metagente_luna_s3.planner import plan_for
from metagente_luna_s4.runner import execute


def run_local_case(case_id: str, instruction: str, evidence_root: Path) -> dict:
    interpreted = interpret(instruction)
    ready = interpreted.status == "READY" and interpreted.arguments[0].provenance.value == "SOURCE_INSTRUCTION"
    plan = plan_for(case_id, interpreted.intent if ready else None)
    if plan.status != "READY":
        return {"case_id": case_id, "execution_status": "REJECTED", "contract_status": "NOT_A_PASS", "plan_status": plan.status}
    record = execute(interpreted.intent, {"cidr": interpreted.arguments[0].value}, case_id, backend="LOCAL_TEST_ONLY")
    record["program_oracle"] = "NOT_MATCHED_TO_THE_PROGRAM_TEXT"
    record["contract_status"] = "NOT_A_PASS"
    if record["execution_status"] != "EXECUTED":
        return record
    folder = write_run(evidence_root, case_id, "run-" + record["run_id"], {
        "instruction.json": {"text": instruction},
        "observed.json": record["observed"],
        "oracle.json": record["oracle_result"],
        "result.json": {"execution_status": record["execution_status"], "contract_status": "NOT_A_PASS", "backend": record["backend"]},
    })
    record["evidence_status"] = verify_run(folder, evidence_root)
    record["evidence_path"] = str(folder)
    return record
