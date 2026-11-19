use crate::error::{err, Result};
use crate::store::Store;
use rusqlite::params;
use serde_json::{json, Value};

pub fn create_plan(store: &Store, title: &str, scope: &[String]) -> Result<String> {
    if title.trim().is_empty() {
        return Err(err("PLAN_TITLE_EMPTY"));
    }
    if scope.is_empty() {
        return Err(err("PLAN_SCOPE_EMPTY"));
    }
    let id = format!("plan-{}-{}", crate::store::now(), store.conn().last_insert_rowid());
    let scope_json = serde_json::to_string(scope)?;
    store.conn().execute(
        "INSERT INTO plans(id,title,scope_json,state,created_at) VALUES(?1,?2,?3,'AWAITING_APPROVAL',?4)",
        params![id, title, scope_json, crate::store::now()],
    )?;
    store.insert_record(5, "plan", &json!({"id": id, "state": "AWAITING_APPROVAL", "title": title}).to_string())?;
    store.log_event("PLAN_CREATE", "PASS", &format!("plan={id} state=AWAITING_APPROVAL"))?;
    Ok(id)
}

pub fn plan_state(store: &Store, id: &str) -> Result<String> {
    let state = store.conn().query_row(
        "SELECT state FROM plans WHERE id=?1",
        params![id],
        |r| r.get(0),
    )?;
    Ok(state)
}

pub fn plan_scope(store: &Store, id: &str) -> Result<Vec<String>> {
    let raw: String = store.conn().query_row(
        "SELECT scope_json FROM plans WHERE id=?1",
        params![id],
        |r| r.get(0),
    )?;
    Ok(serde_json::from_str(&raw)?)
}

pub fn approve_plan(store: &Store, id: &str) -> Result<()> {
    let state = plan_state(store, id)?;
    if state != "AWAITING_APPROVAL" {
        return Err(err(format!("PLAN_NOT_AWAITING:{state}")));
    }
    let n = store.conn().execute(
        "UPDATE plans SET state='AUTHORIZED' WHERE id=?1 AND state='AWAITING_APPROVAL'",
        params![id],
    )?;
    if n != 1 {
        return Err(err("PLAN_APPROVE_RACE"));
    }
    store.insert_record(5, "plan_approval", &json!({"id": id, "state": "AUTHORIZED"}).to_string())?;
    store.log_event("PLAN_APPROVE", "PASS", &format!("plan={id} authorized once"))?;
    Ok(())
}

pub fn enqueue_task(store: &Store, plan_id: &str, kind: &str, payload: &str) -> Result<String> {
    let state = plan_state(store, plan_id)?;
    if state != "AUTHORIZED" {
        return Err(err(format!("PLAN_NOT_AUTHORIZED:{state}")));
    }
    let scope = plan_scope(store, plan_id)?;
    if !scope.iter().any(|s| s == kind || s == "*") {
        store.log_event("TASK_SCOPE", "FAIL", &format!("kind={kind} rejected"))?;
        return Err(err("TASK_OUTSIDE_SCOPE"));
    }
    let voice_before = session_state(store, "VOICE_SESSION").ok();
    let id = format!("task-{}-{}", crate::store::now(), kind);
    store.conn().execute(
        "INSERT INTO tasks(id,plan_id,kind,payload,state,result,created_at) VALUES(?1,?2,?3,?4,'QUEUED','',?5)",
        params![id, plan_id, kind, crate::store::redact(payload), crate::store::now()],
    )?;
    set_session(store, "TASK_SESSION", "ACTIVE")?;
    let voice_after = session_state(store, "VOICE_SESSION").ok();
    if voice_before != voice_after {
        return Err(err("VOICE_SESSION_MUTATED_BY_TASK"));
    }
    store.insert_record(2, "task", &json!({"id": id, "plan": plan_id, "kind": kind, "state": "QUEUED"}).to_string())?;
    store.log_event("TASK_ENQUEUE", "PASS", &format!("task={id} kind={kind}"))?;
    Ok(id)
}

pub fn set_session(store: &Store, kind: &str, state: &str) -> Result<()> {
    if kind != "VOICE_SESSION" && kind != "TASK_SESSION" {
        return Err(err("SESSION_KIND_UNKNOWN"));
    }
    store.conn().execute(
        "INSERT INTO sessions(id,kind,state,updated_at) VALUES(?1,?2,?3,?4)
         ON CONFLICT(id) DO UPDATE SET state=excluded.state, updated_at=excluded.updated_at",
        params![kind, kind, state, crate::store::now()],
    )?;
    store.insert_record(10, "session", &json!({"kind": kind, "state": state}).to_string())?;
    Ok(())
}

pub fn session_state(store: &Store, kind: &str) -> Result<String> {
    store.conn()
        .query_row("SELECT state FROM sessions WHERE id=?1", params![kind], |r| r.get(0))
        .map_err(|_| err("SESSION_ABSENT"))
}

pub fn complete_task(store: &Store, id: &str, ok: bool, result: &str) -> Result<()> {
    let (plan_id, state): (String, String) = store.conn().query_row(
        "SELECT plan_id,state FROM tasks WHERE id=?1",
        params![id],
        |r| Ok((r.get(0)?, r.get(1)?)),
    )?;
    if state != "QUEUED" && state != "EXECUTING" && state != "FAILED" {
        return Err(err(format!("TASK_NOT_RUNNABLE:{state}")));
    }
    if plan_state(store, &plan_id)? != "AUTHORIZED" {
        return Err(err("PLAN_AUTHORIZATION_LOST"));
    }
    let next = if ok { "DONE" } else { "FAILED" };
    store.conn().execute(
        "UPDATE tasks SET state=?1, result=?2 WHERE id=?3",
        params![next, crate::store::redact(result), id],
    )?;
    if !ok {
        store.insert_record(13, "repair", &json!({"task": id, "result": result, "next": "RETRY_SAME_PLAN"}).to_string())?;
    }
    store.log_event("TASK_COMPLETE", if ok { "PASS" } else { "FAIL" }, &format!("task={id} state={next}"))?;
    Ok(())
}

pub fn record_validation(store: &Store, gate: &str, subject: &str, verdict: &str, db_sha: &str) -> Result<()> {
    if gate == "G24" && verdict == "PASS" {
        let prior: i64 = store.conn().query_row(
            "SELECT COUNT(*) FROM validations WHERE gate='G23' AND subject=?1 AND verdict='PASS'",
            params![subject],
            |r| r.get(0),
        )?;
        if prior < 1 {
            return Err(err("G24_WITHOUT_G23_PASS"));
        }
    }
    store.conn().execute(
        "INSERT INTO validations(gate,subject,verdict,db_sha256,created_at) VALUES(?1,?2,?3,?4,?5)",
        params![gate, subject, verdict, db_sha, crate::store::now()],
    )?;
    store.insert_record(14, "validation", &json!({"gate": gate, "subject": subject, "verdict": verdict}).to_string())?;
    Ok(())
}

pub fn plans_overview(store: &Store) -> Result<Value> {
    let mut stmt = store.conn().prepare("SELECT id,title,state,scope_json FROM plans ORDER BY created_at")?;
    let rows = stmt.query_map([], |r| {
        Ok(json!({
            "id": r.get::<_, String>(0)?,
            "title": r.get::<_, String>(1)?,
            "state": r.get::<_, String>(2)?,
            "scope": r.get::<_, String>(3)?,
        }))
    })?;
    let mut plans = Vec::new();
    for row in rows {
        plans.push(row?);
    }
    let mut stmt = store.conn().prepare("SELECT id,plan_id,kind,state FROM tasks ORDER BY created_at")?;
    let rows = stmt.query_map([], |r| {
        Ok(json!({
            "id": r.get::<_, String>(0)?,
            "plan_id": r.get::<_, String>(1)?,
            "kind": r.get::<_, String>(2)?,
            "state": r.get::<_, String>(3)?,
        }))
    })?;
    let mut tasks = Vec::new();
    for row in rows {
        tasks.push(row?);
    }
    Ok(json!({"plans": plans, "tasks": tasks}))
}
