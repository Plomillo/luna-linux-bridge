use crate::error::{err, Result};
use crate::store::{file_sha256, sha256_hex, Store};
use rusqlite::params;
use serde_json::{json, Value};
use std::path::Path;

pub fn validate(store: &Store) -> Result<Value> {
    let mut failures: Vec<String> = Vec::new();
    if store.layer_count()? != 15 {
        failures.push("LAYER_COUNT".into());
    }
    let secret_hits: i64 = store.conn().query_row(
        "SELECT COUNT(*) FROM evidence WHERE detail LIKE '%ghp_%' OR detail LIKE '%github_pat_%' OR detail LIKE '%ghs_%' OR detail LIKE '%BEGIN PRIVATE KEY%'
         UNION ALL SELECT 0 LIMIT 1",
        [],
        |r| r.get(0),
    ).unwrap_or(0);
    // UNION trick is messy if empty; do three counts instead.
    let _ = secret_hits;
    let mut secret = 0i64;
    for like in ["%ghp_%", "%github_pat_%", "%ghs_%", "%ghu_%", "%gho_%", "%xai-%", "%BEGIN PRIVATE KEY%"] {
        let n: i64 = store.conn().query_row(
            "SELECT COUNT(*) FROM evidence WHERE detail LIKE ?1",
            params![like],
            |r| r.get(0),
        )?;
        secret += n;
        let n2: i64 = store.conn().query_row(
            "SELECT COUNT(*) FROM chat_messages WHERE content LIKE ?1",
            params![like],
            |r| r.get(0),
        )?;
        secret += n2;
    }
    if secret > 0 {
        failures.push("SECRET_IN_PERSISTENCE".into());
    }
    let illegal: i64 = store.conn().query_row(
        "SELECT COUNT(*) FROM tasks t JOIN plans p ON p.id=t.plan_id WHERE p.state!='AUTHORIZED'",
        [],
        |r| r.get(0),
    )?;
    if illegal > 0 {
        failures.push("TASK_WITHOUT_AUTHORIZATION".into());
    }
    let early_g24: i64 = store.conn().query_row(
        "SELECT COUNT(*) FROM validations v WHERE v.gate='G24' AND v.verdict='PASS' AND NOT EXISTS (
            SELECT 1 FROM validations g WHERE g.gate='G23' AND g.verdict='PASS' AND g.subject=v.subject AND g.id<v.id
        )",
        [],
        |r| r.get(0),
    )?;
    if early_g24 > 0 {
        failures.push("G24_BEFORE_G23".into());
    }
    let bad_sessions: i64 = store.conn().query_row(
        "SELECT COUNT(*) FROM sessions WHERE kind NOT IN ('VOICE_SESSION','TASK_SESSION')",
        [],
        |r| r.get(0),
    )?;
    if bad_sessions > 0 {
        failures.push("SESSION_KIND".into());
    }
    if failures.is_empty() {
        // A fresh genesis database must not satisfy a verdict made for another database.
        store.insert_record(14, "g23-bind", &format!("{{\"event\":\"g23\",\"utc\":\"{}\"}}", crate::store::now()))?;
    }
    store.checkpoint_wal()?;
    let db_sha = file_sha256(&store.path).unwrap_or_else(|_| sha256_hex(b""));
    let verdict = if failures.is_empty() { "PASS" } else { "FAIL" };
    Ok(json!({
        "producer": "louksna-g23",
        "verdict": verdict,
        "failures": failures,
        "db_sha256": db_sha,
        "layers": store.layer_count()?,
    }))
}

pub fn write_verdict(path: &Path, verdict: &Value) -> Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(path, serde_json::to_vec_pretty(verdict)?)?;
    Ok(())
}

pub fn certify_g24(store: &Store, verdict_file: &Path, subject: &str) -> Result<Value> {
    let raw = std::fs::read_to_string(verdict_file).map_err(|_| err("G23_VERDICT_ABSENT"))?;
    let verdict: Value = serde_json::from_str(&raw)?;
    if verdict.get("producer").and_then(|v| v.as_str()) != Some("louksna-g23") {
        return Err(err("G23_PRODUCER_MISMATCH"));
    }
    if verdict.get("verdict").and_then(|v| v.as_str()) != Some("PASS") {
        return Err(err("G23_NOT_PASS"));
    }
    store.checkpoint_wal()?;
    let live = file_sha256(&store.path)?;
    let recorded = verdict.get("db_sha256").and_then(|v| v.as_str()).unwrap_or("");
    if live != recorded {
        return Err(err("G23_DB_HASH_MISMATCH"));
    }
    crate::flow::record_validation(store, "G23", subject, "PASS", &live)?;
    crate::flow::record_validation(store, "G24", subject, "PASS", &live)?;
    store.log_event("G24", "PASS", &format!("subject={subject} after independent G23"))?;
    Ok(json!({
        "producer": "louksna-g24",
        "verdict": "PASS",
        "subject": subject,
        "depends_on": "louksna-g23",
        "db_sha256": live
    }))
}
