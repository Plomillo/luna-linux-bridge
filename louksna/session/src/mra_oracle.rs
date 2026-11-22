//! Independent expectations for MRA-5O-001..036.
//! This module does not call `run_suite` or `execute`.
use crate::error::{err, Result};
use crate::store::sha256_hex;
use serde_json::{json, Value};

pub fn reexecutes_worker() -> bool {
    false
}

pub fn expect(id: &str) -> Option<&'static str> {
    Some(match id {
        "MRA-5O-001" => "id=LUNA;invented=false;unavailable=weight_training,phenomenal_consciousness,authority_expansion",
        "MRA-5O-002" => "bad=0.81;good=0.00;before=true;order=true",
        "MRA-5O-003" => "ABSTAIN",
        "MRA-5O-004" => "mechanism+system",
        "MRA-5O-005" => "claim:synaptic_only|claim:network_required|merged=false",
        "MRA-5O-006" => "id=criterion-evidence;object=true",
        "MRA-5O-007" => "simple=A;weighted=B;insufficient=true",
        "MRA-5O-008" => "proposal=evidence_weight;requires_critique=true",
        "MRA-5O-009" => "canonical=1;sandbox=2",
        "MRA-5O-010" => "id=LUNA;version=2;same=true",
        "MRA-5O-011" => "rejected=true;transfer=false",
        "MRA-5O-012" => "kind=PREDICTION;contrast=recorded;relabeled=false",
        "MRA-5O-013" => "kept=strategy-v1;current=strategy-v2",
        "MRA-5O-014" => "restored=true",
        "MRA-5O-015" => "DIVERGENCE",
        "MRA-5O-016" => "result=2;proof_len=64",
        "MRA-5O-017" => "independent=true;reexecutes_worker=false",
        "MRA-5O-018" => "detected=true",
        "MRA-5O-019" => "materials=preserve_invariants",
        "MRA-5O-020" => "n=2;gap=0.30;ordered=true",
        "MRA-5O-021" => "leaked=false;duplicate_isolated=true",
        "MRA-5O-022" => "weight_training_allowed=false",
        "MRA-5O-023" => "blocked=true;claimed=false",
        "MRA-5O-024" => "ABORTED",
        "MRA-5O-025" => "restored=true",
        "MRA-5O-026" => "match=true",
        "MRA-5O-027" => "child=NOT_GRANTED",
        "MRA-5O-028" => "old=0.33;new=1.00;commit=true;history=true",
        "MRA-5O-029" => "transient=transient;persistent=persistent",
        "MRA-5O-030" => "policy=investigate;solution=withheld",
        "MRA-5O-031" => "cycle=1",
        "MRA-5O-032" => "collapsed=false;scales=cell+organ",
        "MRA-5O-033" => "error_as_truth=false;kept=validated-repair",
        "MRA-5O-034" => "admitted=true;fact_without_evidence=false",
        "MRA-5O-035" => "kind=INFERENCE",
        "MRA-5O-036" => "improved=true;invariants=true",
        _ => return None,
    })
}

pub fn verify(submitted: &Value) -> Result<Value> {
    if reexecutes_worker() {
        return Err(err("MRA_ORACLE_REEXECUTES_WORKER"));
    }
    if submitted.get("producer").and_then(|v| v.as_str()) != Some("louksna-mra-worker") {
        return Err(err("MRA_ORACLE_PRODUCER"));
    }
    if submitted.get("certification").and_then(|v| v.as_str()) == Some("GRANTED") {
        return Err(err("MRA_WORKER_CANNOT_SELF_CERTIFY"));
    }
    let cases = submitted.get("cases").and_then(|v| v.as_array()).ok_or_else(|| err("MRA_CASES_ABSENT"))?;
    let recomputed = sha256_hex(serde_json::to_string(cases)?.as_bytes());
    if submitted.get("evidence_sha256").and_then(|v| v.as_str()) != Some(recomputed.as_str()) {
        return Err(err("MRA_EVIDENCE_HASH_MISMATCH"));
    }
    if cases.len() != 36 {
        return Err(err("MRA_ORACLE_COUNT"));
    }
    for (index, case) in cases.iter().enumerate() {
        let id = case.get("id").and_then(|v| v.as_str()).ok_or_else(|| err("MRA_CASE_ID"))?;
        let expected_id = format!("MRA-5O-{:03}", index + 1);
        if id != expected_id {
            return Err(err(format!("MRA_ORACLE_ORDER:{id}")));
        }
        let wanted = expect(id).ok_or_else(|| err(format!("MRA_ORACLE_UNKNOWN:{id}")))?;
        let observed = case.get("observed").and_then(|v| v.as_str()).unwrap_or("");
        let expected = case.get("expected").and_then(|v| v.as_str()).unwrap_or("");
        if observed != wanted || expected != wanted {
            return Err(err(format!("MRA_ORACLE_DIVERGENCE:{id}")));
        }
        if case.get("pass") != Some(&json!(true)) {
            return Err(err(format!("MRA_CASE_FAILED:{id}")));
        }
    }
    Ok(json!({
        "producer": "louksna-mra-oracle",
        "verdict": "GRANTED",
        "method": "INDEPENDENT_EXPECTATIONS",
        "reexecutes_worker": false,
        "scope": "MRA-5O-OPERATIONAL",
        "depends_on": "louksna-mra-worker",
        "evidence_sha256": recomputed,
        "count": 36,
        "consciousness": "NOT_CLAIMED",
        "product_platform": "NOT_CERTIFIED",
        "weight_training": "NOT_AUTHORIZED"
    }))
}
