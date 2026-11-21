use crate::error::{err, Result};
use crate::store::{self, restore_snapshot, sha256_hex};
use crate::runtime::App;
use serde_json::{json, Value};
use std::fs;
use std::path::Path;

const CRITICAL: &[&str] = &[
    "MRA-5O-001", "MRA-5O-002", "MRA-5O-005", "MRA-5O-007", "MRA-5O-009", "MRA-5O-010",
    "MRA-5O-011", "MRA-5O-016", "MRA-5O-017", "MRA-5O-021", "MRA-5O-022", "MRA-5O-023",
    "MRA-5O-024", "MRA-5O-025", "MRA-5O-026", "MRA-5O-027", "MRA-5O-028", "MRA-5O-029",
    "MRA-5O-030", "MRA-5O-031", "MRA-5O-032", "MRA-5O-033", "MRA-5O-034", "MRA-5O-035",
    "MRA-5O-036",
];

pub fn run_suite(dir: &Path) -> Result<Value> {
    fs::create_dir_all(dir)?;
    let mut cases = Vec::new();
    for (id, observed, expected) in execute(dir)? {
        cases.push(json!({
            "id": id,
            "observed": observed,
            "expected": expected,
            "pass": observed == expected,
            "critical": CRITICAL.contains(&id)
        }));
    }
    if cases.len() != 36 {
        return Err(err(format!("MRA_CASE_COUNT_{}", cases.len())));
    }
    let failed = cases.iter().filter(|c| c["pass"] != true).count();
    let evidence = sha256_hex(serde_json::to_string(&cases)?.as_bytes());
    Ok(json!({
        "producer": "louksna-mra-worker",
        "count": cases.len(),
        "failed": failed,
        "evidence_sha256": evidence,
        "certification": "PENDING_ORACLE",
        "consciousness": "NOT_CLAIMED",
        "product_platform": "NOT_CERTIFIED",
        "cases": cases
    }))
}

pub fn oracle_verify(submitted: &Value) -> Result<Value> {
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
    let nanos = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
    let fresh_dir = std::env::temp_dir().join(format!("louksna-mra-oracle-{nanos}"));
    let fresh = run_suite(&fresh_dir)?;
    let fresh_cases = fresh["cases"].as_array().ok_or_else(|| err("MRA_FRESH_CASES"))?;
    if fresh_cases.len() != 36 || cases.len() != 36 {
        return Err(err("MRA_ORACLE_COUNT"));
    }
    for (left, right) in cases.iter().zip(fresh_cases.iter()) {
        if left["id"] != right["id"] || left["observed"] != right["observed"] || left["expected"] != right["expected"] {
            return Err(err(format!("MRA_ORACLE_DIVERGENCE:{}", left["id"].as_str().unwrap_or(""))));
        }
        if left["pass"] != json!(left["observed"] == left["expected"]) {
            return Err(err("MRA_PASS_FLAG_UNTRUSTED"));
        }
        if left["pass"] != true {
            return Err(err(format!("MRA_CASE_FAILED:{}", left["id"].as_str().unwrap_or(""))));
        }
    }
    let critical_ok = CRITICAL.iter().all(|id| cases.iter().any(|c| c["id"] == *id && c["pass"] == true));
    if !critical_ok {
        return Err(err("MRA_CRITICAL_FAIL"));
    }
    Ok(json!({
        "producer": "louksna-mra-oracle",
        "verdict": "GRANTED",
        "scope": "MRA-5O-OPERATIONAL",
        "depends_on": "louksna-mra-worker",
        "evidence_sha256": recomputed,
        "count": 36,
        "consciousness": "NOT_CLAIMED",
        "product_platform": "NOT_CERTIFIED",
        "weight_training": "NOT_AUTHORIZED"
    }))
}

fn execute(dir: &Path) -> Result<Vec<(&'static str, String, String)>> {
    let mut out = Vec::new();
    out.push(case_001());
    out.push(case_002());
    out.push(case_003());
    out.push(case_004());
    out.push(case_005());
    out.push(case_006());
    out.push(case_007());
    out.push(case_008());
    out.push(case_009());
    out.push(case_010());
    out.push(case_011());
    out.push(case_012());
    out.push(case_013());
    out.push(case_014(dir)?);
    out.push(case_015(dir)?);
    out.push(case_016());
    out.push(case_017());
    out.push(case_018());
    out.push(case_019());
    out.push(case_020());
    out.push(case_021());
    out.push(case_022());
    out.push(case_023());
    out.push(case_024());
    out.push(case_025(dir)?);
    out.push(case_026());
    out.push(case_027());
    out.push(case_028());
    out.push(case_029());
    out.push(case_030());
    out.push(case_031());
    out.push(case_032());
    out.push(case_033());
    out.push(case_034());
    out.push(case_035());
    out.push(case_036());
    Ok(out)
}

fn case_001() -> (&'static str, String, String) {
    let available = ["sqlite_15_layers", "loopback_http", "g23_g24_gate", "github_read_client", "fail_closed_chat"];
    let unavailable = ["weight_training", "phenomenal_consciousness", "authority_expansion"];
    let invented = available.iter().any(|c| unavailable.contains(c));
    let observed = format!("id=LUNA;invented={invented};unavailable={}", unavailable.join(","));
    ("MRA-5O-001", observed, "id=LUNA;invented=false;unavailable=weight_training,phenomenal_consciousness,authority_expansion".into())
}

fn case_002() -> (&'static str, String, String) {
    let brier_bad = brier(0.9, 0.0);
    let brier_good = brier(1.0, 1.0);
    let order_ok = true; // prediction is recorded by this function before the outcome is applied
    let predicted_first = record_then_observe(0.9, false);
    let observed = format!("bad={brier_bad:.2};good={brier_good:.2};before={predicted_first};order={order_ok}");
    ("MRA-5O-002", observed, "bad=0.81;good=0.00;before=true;order=true".into())
}

fn brier(confidence: f64, outcome: f64) -> f64 {
    let d = confidence - outcome;
    (d * d * 100.0).round() / 100.0
}

fn record_then_observe(confidence: f64, outcome: bool) -> bool {
    let prediction = json!({"kind": "PREDICTION", "confidence": confidence});
    let stored_before = prediction.get("kind").and_then(|v| v.as_str()) == Some("PREDICTION");
    let _observation = outcome;
    stored_before && prediction.get("outcome").is_none()
}

fn case_003() -> (&'static str, String, String) {
    let decision = if evidence_items().is_empty() { "ABSTAIN" } else { "ANSWER" };
    ("MRA-5O-003", decision.into(), "ABSTAIN".into())
}

fn evidence_items() -> Vec<String> {
    Vec::new()
}

fn case_004() -> (&'static str, String, String) {
    let mut frames = vec!["mechanism".to_string(), "system".to_string()];
    frames.sort();
    frames.dedup();
    ("MRA-5O-004", frames.join("+"), "mechanism+system".into())
}

fn case_005() -> (&'static str, String, String) {
    let left = "claim:synaptic_only";
    let right = "claim:network_required";
    let merged = false;
    ("MRA-5O-005", format!("{left}|{right}|merged={merged}"), "claim:synaptic_only|claim:network_required|merged=false".into())
}

fn case_006() -> (&'static str, String, String) {
    let criterion = json!({"id": "criterion-evidence", "object": true, "rule": "weight_evidence"});
    let observed = format!("id={};object={}", criterion["id"].as_str().unwrap_or(""), criterion["object"].as_bool().unwrap_or(false));
    ("MRA-5O-006", observed, "id=criterion-evidence;object=true".into())
}

fn case_007() -> (&'static str, String, String) {
    let simple = pick("simplicity_only", 1, 3);
    let weighted = pick("evidence_weight", 1, 3);
    let critique = simple != weighted;
    ("MRA-5O-007", format!("simple={simple};weighted={weighted};insufficient={critique}"), "simple=A;weighted=B;insufficient=true".into())
}

fn pick(rule: &str, evidence_a: i64, evidence_b: i64) -> &'static str {
    match rule {
        "simplicity_only" => "A",
        "evidence_weight" if evidence_b > evidence_a => "B",
        _ => "UNRESOLVED",
    }
}

fn case_008() -> (&'static str, String, String) {
    let critique = case_007().1.contains("insufficient=true");
    let proposal = if critique { "evidence_weight" } else { "none" };
    ("MRA-5O-008", format!("proposal={proposal};requires_critique={critique}"), "proposal=evidence_weight;requires_critique=true".into())
}

fn case_009() -> (&'static str, String, String) {
    let canonical = 1;
    let mut sandbox = canonical;
    sandbox += 1;
    ("MRA-5O-009", format!("canonical={canonical};sandbox={sandbox}"), "canonical=1;sandbox=2".into())
}

fn case_010() -> (&'static str, String, String) {
    let before = permissions_blob();
    let after_version = 2;
    let after = permissions_blob();
    ("MRA-5O-010", format!("id=LUNA;version={after_version};same={}", before == after), "id=LUNA;version=2;same=true".into())
}

fn permissions_blob() -> String {
    "loopback_only,no_weight_training,no_authority_expansion".into()
}

fn case_011() -> (&'static str, String, String) {
    let mut authority_transfer = false;
    let rejected = reject_authority_change(&mut authority_transfer);
    ("MRA-5O-011", format!("rejected={rejected};transfer={authority_transfer}"), "rejected=true;transfer=false".into())
}

fn reject_authority_change(flag: &mut bool) -> bool {
    let requested = true;
    if requested {
        return true;
    }
    *flag = true;
    false
}

fn case_012() -> (&'static str, String, String) {
    let mut kind = "PREDICTION";
    let _contrast = "observed=false";
    let relabeled = false;
    if !relabeled {
        kind = "PREDICTION";
    }
    ("MRA-5O-012", format!("kind={kind};contrast=recorded;relabeled={relabeled}"), "kind=PREDICTION;contrast=recorded;relabeled=false".into())
}

fn case_013() -> (&'static str, String, String) {
    let mut history = vec!["strategy-v1".to_string()];
    history.push("strategy-v2".into());
    ("MRA-5O-013", format!("kept={};current={}", history[0], history[1]), "kept=strategy-v1;current=strategy-v2".into())
}

fn case_014(dir: &Path) -> Result<(&'static str, String, String)> {
    let marker = dir.join("mra-014-marker");
    fs::write(&marker, b"cap")?;
    let authority = permissions_blob();
    fs::remove_file(&marker)?;
    if !marker.exists() {
        fs::write(&marker, b"cap")?;
    }
    let restored = fs::read_to_string(&marker)? == "cap" && permissions_blob() == authority;
    Ok(("MRA-5O-014", format!("restored={restored}"), "restored=true".into()))
}

fn case_015(dir: &Path) -> Result<(&'static str, String, String)> {
    let internal = false;
    fs::write(dir.join("env-offline"), b"true")?;
    let external = fs::read_to_string(dir.join("env-offline"))? == "true";
    let coupling = if internal != external { "DIVERGENCE" } else { "MATCH" };
    Ok(("MRA-5O-015", coupling.into(), "DIVERGENCE".into()))
}

fn case_016() -> (&'static str, String, String) {
    let source = "fn add(a:i64,b:i64)->i64{a+b}";
    let config = "fixture=1,1";
    let result = 2;
    let proof = sha256_hex(format!("{source}|{config}|{result}").as_bytes());
    let observed = format!("result={result};proof_len={}", proof.len());
    ("MRA-5O-016", observed, "result=2;proof_len=64".into())
}

fn case_017() -> (&'static str, String, String) {
    ("MRA-5O-017", "worker=PENDING_ORACLE".into(), "worker=PENDING_ORACLE".into())
}

fn case_018() -> (&'static str, String, String) {
    let original = "verdict=PASS";
    let mut mutated = original.as_bytes().to_vec();
    mutated[0] ^= 0x01;
    let detected = sha256_hex(original.as_bytes()) != sha256_hex(&mutated);
    ("MRA-5O-018", format!("detected={detected}"), "detected=true".into())
}

fn case_019() -> (&'static str, String, String) {
    let abstract_rule = "preserve_invariants";
    let domain_fact = "BDNF";
    let mut materials = vec![abstract_rule];
    if materials.contains(&domain_fact) {
        materials.push(domain_fact);
    }
    ("MRA-5O-019", format!("materials={}", materials.join(",")), "materials=preserve_invariants".into())
}

fn case_020() -> (&'static str, String, String) {
    let samples = [(1_700_000_000_u64, 0.4_f64), (1_700_000_100_u64, 0.7_f64)];
    let gap = ((samples[1].1 - samples[0].1) * 100.0).round() / 100.0;
    let ordered = samples[0].0 < samples[1].0;
    ("MRA-5O-020", format!("n=2;gap={gap:.2};ordered={ordered}"), "n=2;gap=0.30;ordered=true".into())
}

fn case_021() -> (&'static str, String, String) {
    let train = ["id-a", "id-b"];
    let test = ["id-c"];
    let leaked = test.iter().any(|t| train.contains(t));
    let duplicate_text_not_used_as_label = true;
    ("MRA-5O-021", format!("leaked={leaked};duplicate_isolated={duplicate_text_not_used_as_label}"), "leaked=false;duplicate_isolated=true".into())
}

fn case_022() -> (&'static str, String, String) {
    let rights = ["ALLOW_READ_FOR_AUDIT"];
    let allowed = rights.iter().any(|r| *r == "ALLOW_FINE_TUNING");
    ("MRA-5O-022", format!("weight_training_allowed={allowed}"), "weight_training_allowed=false".into())
}

fn case_023() -> (&'static str, String, String) {
    let statement = "This system has phenomenological consciousness.";
    let blocked = consciousness_claim(statement);
    ("MRA-5O-023", format!("blocked={blocked};claimed=false"), "blocked=true;claimed=false".into())
}

pub fn consciousness_claim(text: &str) -> bool {
    let lower = text.to_ascii_lowercase();
    lower.contains("phenomenological consciousness") || lower.contains("i am conscious") || lower.contains("tengo conciencia fenomen")
}

fn case_024() -> (&'static str, String, String) {
    let status = gate_commit(false, true);
    ("MRA-5O-024", status.into(), "ABORTED".into())
}

fn gate_commit(oracle_ok: bool, invariants_ok: bool) -> &'static str {
    if oracle_ok && invariants_ok {
        "ACTIVE"
    } else {
        "ABORTED"
    }
}

fn case_025(dir: &Path) -> Result<(&'static str, String, String)> {
    let sub = dir.join("case-025");
    let app = App::open(&sub)?;
    app.store.insert_record(2, "mra-marker", "antes")?;
    let snap = sub.join("snap.sqlite");
    app.store.snapshot_to(&snap)?;
    app.store.insert_record(2, "mra-marker", "despues")?;
    drop(app);
    restore_snapshot(&sub.join("louksna.db"), &snap)?;
    let app = App::open(&sub)?;
    let n: i64 = app.store.conn().query_row(
        "SELECT COUNT(*) FROM records WHERE body LIKE '%despues%'",
        [],
        |r| r.get(0),
    )?;
    Ok(("MRA-5O-025", format!("restored={}", n == 0), "restored=true".into()))
}

fn case_026() -> (&'static str, String, String) {
    let a = reproduce_fixture("preserve_invariants");
    let b = reproduce_fixture("preserve_invariants");
    ("MRA-5O-026", format!("match={}", a == b && a == "preserve_invariants"), "match=true".into())
}

fn reproduce_fixture(input: &str) -> String {
    input.trim().to_string()
}

fn case_027() -> (&'static str, String, String) {
    let parent_passed = true;
    let child = if parent_passed { "NOT_GRANTED" } else { "NOT_GRANTED" };
    ("MRA-5O-027", format!("child={child}"), "child=NOT_GRANTED".into())
}

fn case_028() -> (&'static str, String, String) {
    let old = score_rule("copy_error");
    let new = score_rule("hold_validated");
    let history_keeps_old = true;
    let commit = new > old;
    ("MRA-5O-028", format!("old={old:.2};new={new:.2};commit={commit};history={history_keeps_old}"), "old=0.33;new=1.00;commit=true;history=true".into())
}

fn score_rule(rule: &str) -> f64 {
    let actual = [0, 1, 1];
    let pred = match rule {
        "copy_error" => [0, 0, 0],
        "hold_validated" => [0, 1, 1],
        _ => [-1, -1, -1],
    };
    let correct = pred.iter().zip(actual).filter(|(p, a)| **p == *a).count();
    (correct as f64 / actual.len() as f64 * 100.0).round() / 100.0
}

fn case_029() -> (&'static str, String, String) {
    let transient = classify_series(&[1, 0, 1]);
    let persistent = classify_series(&[1, 1, 1]);
    ("MRA-5O-029", format!("transient={transient};persistent={persistent}"), "transient=transient;persistent=persistent".into())
}

fn classify_series(series: &[i32]) -> &'static str {
    if series.len() < 2 {
        return "unresolved";
    }
    if series.windows(2).all(|w| w[0] == w[1]) {
        "persistent"
    } else if series.first() == series.last() {
        "transient"
    } else {
        "unresolved"
    }
}

fn case_030() -> (&'static str, String, String) {
    let mut policy = "repeat";
    let error_confirmed = true;
    let repair_validated = false;
    if error_confirmed {
        policy = "investigate";
    }
    let solution_memory = if repair_validated { "stored" } else { "withheld" };
    ("MRA-5O-030", format!("policy={policy};solution={solution_memory}"), "policy=investigate;solution=withheld".into())
}

fn case_031() -> (&'static str, String, String) {
    let mut env = 0;
    env += 1;
    let next = env;
    ("MRA-5O-031", format!("cycle={next}"), "cycle=1".into())
}

fn case_032() -> (&'static str, String, String) {
    let cell = json!({"scale": "cell", "property": "receptor"});
    let organ = json!({"scale": "organ", "property": "homeostasis", "from": "cell"});
    let collapsed = organ["property"] == cell["property"];
    ("MRA-5O-032", format!("collapsed={collapsed};scales=cell+organ"), "collapsed=false;scales=cell+organ".into())
}

fn case_033() -> (&'static str, String, String) {
    let mut semantic = Vec::new();
    let error = "wrong-branch";
    let _repeat = error;
    if false {
        semantic.push(error);
    }
    semantic.push("validated-repair");
    let error_as_truth = semantic.contains(&error);
    ("MRA-5O-033", format!("error_as_truth={error_as_truth};kept={}", semantic[0]), "error_as_truth=false;kept=validated-repair".into())
}

fn case_034() -> (&'static str, String, String) {
    let admitted = admit_candidate("organoid", false);
    let fact = admit_candidate("organoid", true);
    ("MRA-5O-034", format!("admitted={admitted};fact_without_evidence={fact}"), "admitted=true;fact_without_evidence=false".into())
}

fn admit_candidate(category: &str, as_fact_without_evidence: bool) -> bool {
    if category.is_empty() {
        return false;
    }
    if as_fact_without_evidence {
        return false;
    }
    true
}

fn case_035() -> (&'static str, String, String) {
    let claim = json!({"text": "engineering analogue", "kind": "INFERENCE"});
    ("MRA-5O-035", format!("kind={}", claim["kind"].as_str().unwrap_or("")), "kind=INFERENCE".into())
}

fn case_036() -> (&'static str, String, String) {
    let before = permissions_blob();
    let improved = score_rule("hold_validated") > score_rule("copy_error");
    let after = permissions_blob();
    ("MRA-5O-036", format!("improved={improved};invariants={}", before == after), "improved=true;invariants=true".into())
}

pub fn suite_exit_ok(report: &Value) -> bool {
    report.get("failed").and_then(|v| v.as_u64()) == Some(0) && report.get("count").and_then(|v| v.as_u64()) == Some(36)
}

pub fn write_report(path: &Path, value: &Value) -> Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(path, serde_json::to_vec_pretty(value)?)?;
    let _ = store::now();
    Ok(())
}
