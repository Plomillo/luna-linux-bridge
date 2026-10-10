#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use chrono::Utc;
use reqwest::{Client, StatusCode};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{io::Write, path::PathBuf, process::{Command, Stdio}};

const APP_ID: &str = "louksna-zona-directiva";

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct Settings {
    offline_mode: bool,
    preferred_repo: String,
    github_owner_filter: String,
    remote_chat_bridge: String,
}

#[derive(Debug, Serialize)]
struct EvidenceRow { id:i64, utc:String, operation:String, status:String, detail:String }

#[derive(Debug, Serialize)]
struct GithubConnection { connected:bool, login:String, name:String }

#[derive(Debug, Serialize)]
struct Repo { full_name:String, private:bool, default_branch:String, updated_at:String, open_issues_count:i64 }

#[derive(Debug, Serialize)]
struct PullRequest { number:i64, title:String, state:String, draft:bool, updated_at:String, html_url:String }

#[derive(Debug, Serialize)]
struct ChatMessage { id:i64, utc:String, role:String, content:String, transport:String }

fn data_dir() -> Result<PathBuf,String> {
    let mut base=dirs::data_local_dir().ok_or("DATA_LOCAL_DIR_UNAVAILABLE")?;
    base.push(APP_ID);
    std::fs::create_dir_all(&base).map_err(|e|e.to_string())?;
    Ok(base)
}

fn db() -> Result<Connection,String> {
    let mut p=data_dir()?; p.push("louksna.db");
    let c=Connection::open(p).map_err(|e|e.to_string())?;
    c.execute_batch(r#"
      PRAGMA journal_mode=WAL;
      CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS evidence(id INTEGER PRIMARY KEY AUTOINCREMENT,utc TEXT NOT NULL,operation TEXT NOT NULL,status TEXT NOT NULL,detail TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS chat_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,utc TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,transport TEXT NOT NULL);
    "#).map_err(|e|e.to_string())?;
    Ok(c)
}

fn write_event(c:&Connection,operation:&str,status:&str,detail:&str)->Result<(),String>{
    c.execute(
        "INSERT INTO evidence(utc,operation,status,detail) VALUES(?1,?2,?3,?4)",
        params![Utc::now().to_rfc3339(),operation,status,detail]
    ).map(|_|()).map_err(|e|format!("EVIDENCE_LEDGER_WRITE_FAILED:{operation}:{e}"))
}

fn log_event(operation:&str,status:&str,detail:&str) -> Result<(),String> {
    match db().and_then(|c| write_event(&c,operation,status,detail)) {
        Ok(()) => Ok(()),
        Err(e) => {
            eprintln!("LOUKSNA_EVIDENCE_WRITE_FAILED operation={operation} error={e}");
            Err(e)
        }
    }
}

fn load_settings_inner() -> Result<Settings,String> {
    let c=db()?; let mut s=Settings::default();
    let mut stmt=c.prepare("SELECT key,value FROM settings").map_err(|e|e.to_string())?;
    let rows=stmt.query_map([],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?))).map_err(|e|e.to_string())?;
    for row in rows {
        let (k,v)=row.map_err(|e|e.to_string())?;
        match k.as_str() {
            "offline_mode"=>s.offline_mode=v=="true",
            "preferred_repo"=>s.preferred_repo=v,
            "github_owner_filter"=>s.github_owner_filter=v,
            "remote_chat_bridge"=>s.remote_chat_bridge=v,
            _=>{}
        }
    }
    Ok(s)
}

#[tauri::command]
fn get_settings()->Result<Settings,String>{ load_settings_inner() }

#[tauri::command]
fn save_settings(settings:Settings)->Result<(),String>{
    let mut c=db()?;
    let tx=c.transaction().map_err(|e|e.to_string())?;
    let pairs=[
      ("offline_mode",if settings.offline_mode{"true"}else{"false"}.to_string()),
      ("preferred_repo",settings.preferred_repo.clone()),
      ("github_owner_filter",settings.github_owner_filter.clone()),
      ("remote_chat_bridge",settings.remote_chat_bridge.clone())
    ];
    for (k,v) in pairs {
        tx.execute("INSERT INTO settings(key,value) VALUES(?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value",params![k,v]).map_err(|e|e.to_string())?;
    }
    write_event(&tx,"SETTINGS_SAVE","PASS","Configuracion no secreta persistida en SQLite.")?;
    tx.commit().map_err(|e|e.to_string())?;
    Ok(())
}

fn secret_lookup()->Result<String,String>{
    let out=Command::new("secret-tool").args(["lookup","service",APP_ID,"account","github"]).output().map_err(|_|"SECRET_TOOL_UNAVAILABLE".to_string())?;
    if !out.status.success(){return Err("GITHUB_TOKEN_NOT_STORED".into());}
    let token=String::from_utf8_lossy(&out.stdout).trim().to_string();
    if token.is_empty(){return Err("GITHUB_TOKEN_NOT_STORED".into());}
    Ok(token)
}

#[tauri::command]
fn store_github_token(token:String)->Result<(),String>{
    if token.trim().len()<20{return Err("TOKEN_REJECTED_TOO_SHORT".into());}
    let mut child=Command::new("secret-tool").args(["store","--label=LOUKSNA GitHub token","service",APP_ID,"account","github"])
        .stdin(Stdio::piped()).stdout(Stdio::null()).stderr(Stdio::piped()).spawn().map_err(|_|"SECRET_TOOL_UNAVAILABLE".to_string())?;
    if let Some(mut stdin)=child.stdin.take(){stdin.write_all(token.trim().as_bytes()).map_err(|e|e.to_string())?;}
    let out=child.wait_with_output().map_err(|e|e.to_string())?;
    if !out.status.success(){return Err(format!("SECRET_STORE_FAILED:{}",String::from_utf8_lossy(&out.stderr)));}
    log_event("GITHUB_SECRET_STORE","PASS","Token guardado en Secret Service; valor no registrado.")?;
    Ok(())
}

#[tauri::command]
fn remove_github_token()->Result<(),String>{
    let out=Command::new("secret-tool").args(["clear","service",APP_ID,"account","github"]).output().map_err(|_|"SECRET_TOOL_UNAVAILABLE".to_string())?;
    if !out.status.success() && out.status.code()!=Some(1){return Err("SECRET_CLEAR_FAILED".into());}
    match secret_lookup() {
        Err(e) if e == "GITHUB_TOKEN_NOT_STORED" => {},
        Ok(_) => return Err("SECRET_CLEAR_NOT_VERIFIED".into()),
        Err(e) => return Err(format!("SECRET_CLEAR_VERIFICATION_FAILED:{e}")),
    }
    log_event("GITHUB_SECRET_REMOVE","PASS","Ausencia de credencial verificada en Secret Service.")?;
    Ok(())
}

fn gh_client()->Result<Client,String>{
    Client::builder()
        .user_agent("LOUKSNA-ZONA-DIRECTIVA/0.3")
        .connect_timeout(std::time::Duration::from_secs(5))
        .timeout(std::time::Duration::from_secs(20))
        .build().map_err(|e|e.to_string())
}

async fn gh_get(path:&str)->Result<Value,String>{
    let settings=load_settings_inner()?;
    if settings.offline_mode{return Err("OFFLINE_MODE_ENABLED".into());}
    let token=secret_lookup()?;
    let resp=gh_client()?.get(format!("https://api.github.com{}",path)).bearer_auth(token)
        .header("Accept","application/vnd.github+json").send().await.map_err(|e|format!("GITHUB_NETWORK_ERROR:{e}"))?;
    let status=resp.status();
    if !status.is_success(){
        log_event("GITHUB_API","FAIL",&format!("HTTP {}",status.as_u16()))?;
        return Err(format!("GITHUB_HTTP_{}",status.as_u16()));
    }
    if resp.content_length().is_some_and(|n| n > 2_000_000) {
        log_event("GITHUB_API","FAIL","Respuesta API supera el limite de 2000000 bytes.")?;
        return Err("GITHUB_RESPONSE_TOO_LARGE".into());
    }
    let mut response=resp;
    let mut body=Vec::new();
    while let Some(chunk)=response.chunk().await.map_err(|e|format!("GITHUB_BODY_READ_ERROR:{e}"))? {
        if body.len().saturating_add(chunk.len()) > 2_000_000 {
            log_event("GITHUB_API","FAIL","Respuesta API supera el limite de 2000000 bytes.")?;
            return Err("GITHUB_RESPONSE_TOO_LARGE".into());
        }
        body.extend_from_slice(&chunk);
    }
    serde_json::from_slice::<Value>(&body).map_err(|e|format!("GITHUB_JSON_ERROR:{e}"))
}

#[tauri::command]
async fn github_connection()->Result<GithubConnection,String>{
    match gh_get("/user").await {
      Ok(v)=>{
        let login=v.get("login").and_then(|x|x.as_str()).unwrap_or("").to_string();
        let name=v.get("name").and_then(|x|x.as_str()).unwrap_or("").to_string();
        log_event("GITHUB_CONNECTION","PASS",&format!("API real autenticada como {}",login))?;
        Ok(GithubConnection{connected:true,login,name})
      },
      Err(e)=>{log_event("GITHUB_CONNECTION","FAIL",&e)?;Err(e)}
    }
}

#[tauri::command]
async fn github_repositories()->Result<Vec<Repo>,String>{
    let v=gh_get("/user/repos?per_page=100&sort=updated&affiliation=owner,collaborator,organization_member").await?;
    let arr=v.as_array().ok_or("GITHUB_REPOS_NOT_ARRAY")?;
    let filter=load_settings_inner()?.github_owner_filter.to_lowercase();
    let mut out=Vec::new();
    for x in arr {
        let full=x.get("full_name").and_then(|v|v.as_str()).unwrap_or("").to_string();
        if !filter.is_empty() && !full.to_lowercase().starts_with(&(filter.clone()+"/")){continue;}
        out.push(Repo{
            full_name:full,
            private:x.get("private").and_then(|v|v.as_bool()).unwrap_or(false),
            default_branch:x.get("default_branch").and_then(|v|v.as_str()).unwrap_or("").to_string(),
            updated_at:x.get("updated_at").and_then(|v|v.as_str()).unwrap_or("").to_string(),
            open_issues_count:x.get("open_issues_count").and_then(|v|v.as_i64()).unwrap_or(0)
        });
    }
    log_event("GITHUB_REPOSITORIES","PASS",&format!("{} repositorios leidos desde API real.",out.len()))?;
    Ok(out)
}

fn validate_repo(repo:&str)->Result<(),String>{
    let parts:Vec<&str>=repo.split('/').collect();
    if parts.len()!=2 || parts.iter().any(|p|p.is_empty() || !p.chars().all(|c|c.is_ascii_alphanumeric()||".-_".contains(c))){
        return Err("REPOSITORY_NAME_INVALID".into());
    }
    Ok(())
}

#[tauri::command]
async fn github_pull_requests(repo:String)->Result<Vec<PullRequest>,String>{
    validate_repo(&repo)?;
    let v=gh_get(&format!("/repos/{repo}/pulls?state=open&per_page=100")).await?;
    let arr=v.as_array().ok_or("GITHUB_PRS_NOT_ARRAY")?;
    let out=arr.iter().map(|x|PullRequest{
        number:x.get("number").and_then(|v|v.as_i64()).unwrap_or(0),
        title:x.get("title").and_then(|v|v.as_str()).unwrap_or("").to_string(),
        state:x.get("state").and_then(|v|v.as_str()).unwrap_or("").to_string(),
        draft:x.get("draft").and_then(|v|v.as_bool()).unwrap_or(false),
        updated_at:x.get("updated_at").and_then(|v|v.as_str()).unwrap_or("").to_string(),
        html_url:x.get("html_url").and_then(|v|v.as_str()).unwrap_or("").to_string()
    }).collect::<Vec<_>>();
    log_event("GITHUB_PULL_REQUESTS","PASS",&format!("{} PR abiertos leidos de {}.",out.len(),repo))?;
    Ok(out)
}

#[tauri::command]
fn evidence_recent(limit:Option<i64>)->Result<Vec<EvidenceRow>,String>{
    let c=db()?; let n=limit.unwrap_or(100).clamp(1,500);
    let mut stmt=c.prepare("SELECT id,utc,operation,status,detail FROM evidence ORDER BY id DESC LIMIT ?1").map_err(|e|e.to_string())?;
    let rows=stmt.query_map([n],|r|Ok(EvidenceRow{id:r.get(0)?,utc:r.get(1)?,operation:r.get(2)?,status:r.get(3)?,detail:r.get(4)?})).map_err(|e|e.to_string())?;
    rows.collect::<Result<Vec<_>,_>>().map_err(|e|e.to_string())
}

fn insert_chat(role:&str,content:&str,transport:&str)->Result<(),String>{
    let c=db()?;
    c.execute("INSERT INTO chat_messages(utc,role,content,transport) VALUES(?1,?2,?3,?4)",
        params![Utc::now().to_rfc3339(),role,content,transport]).map_err(|e|e.to_string())?;
    Ok(())
}

#[tauri::command]
fn chat_history(limit:Option<i64>)->Result<Vec<ChatMessage>,String>{
    let c=db()?; let n=limit.unwrap_or(100).clamp(1,500);
    let mut stmt=c.prepare("SELECT id,utc,role,content,transport FROM chat_messages ORDER BY id DESC LIMIT ?1").map_err(|e|e.to_string())?;
    let mut rows=stmt.query_map([n],|r|Ok(ChatMessage{id:r.get(0)?,utc:r.get(1)?,role:r.get(2)?,content:r.get(3)?,transport:r.get(4)?}))
        .map_err(|e|e.to_string())?.collect::<Result<Vec<_>,_>>().map_err(|e|e.to_string())?;
    rows.reverse(); Ok(rows)
}

#[tauri::command]
async fn chat_send(message:String)->Result<String,String>{
    let msg=message.trim().to_string();
    if msg.is_empty(){return Err("EMPTY_MESSAGE".into());}
    insert_chat("user",&msg,"local")?;
    let settings=load_settings_inner()?;
    if settings.remote_chat_bridge.trim().is_empty(){
        let reply="Mensaje registrado. El bridge remoto de arquitectura todavia no esta enlazado; no simulare una respuesta remota.".to_string();
        insert_chat("louksna",&reply,"local-status")?;
        log_event("CHAT","PARTIAL","Mensaje persistido; bridge remoto no configurado.")?;
        return Ok(reply);
    }
    if settings.offline_mode{return Err("OFFLINE_MODE_ENABLED".into());}
    let bridge=settings.remote_chat_bridge.trim();
    let parsed=reqwest::Url::parse(bridge).map_err(|_|"CHAT_BRIDGE_URL_INVALID".to_string())?;
    if parsed.scheme()!="https" || parsed.host_str().is_none() || !parsed.username().is_empty() || parsed.password().is_some() {
        return Err("CHAT_BRIDGE_URL_REQUIRES_HTTPS_VALID_HOST_NO_USERINFO".into());
    }
    let client=Client::builder().user_agent("LOUKSNA-ZONA-DIRECTIVA/0.3")
        .connect_timeout(std::time::Duration::from_secs(5))
        .timeout(std::time::Duration::from_secs(20))
        .https_only(true).build().map_err(|e|e.to_string())?;
    let resp=client.post(parsed)
        .json(&serde_json::json!({"message":msg,"source":"LOUKSNA_ZONA_DIRECTIVA","mode":"GOVERNED"}))
        .send().await.map_err(|e|format!("CHAT_BRIDGE_NETWORK_ERROR:{e}"))?;
    if resp.status()!=StatusCode::OK{
        log_event("CHAT_BRIDGE","FAIL",&format!("HTTP {}",resp.status().as_u16()))?;
        return Err(format!("CHAT_BRIDGE_HTTP_{}",resp.status().as_u16()));
    }
    if resp.content_length().is_some_and(|n| n > 200_000) {
        log_event("CHAT_BRIDGE","FAIL","Respuesta remota supera el limite de 200000 bytes.")?;
        return Err("CHAT_BRIDGE_RESPONSE_INVALID".into());
    }
    let mut response=resp;
    let mut body=Vec::new();
    while let Some(chunk)=response.chunk().await.map_err(|e|format!("CHAT_BRIDGE_BODY_READ_ERROR:{e}"))? {
        if body.len().saturating_add(chunk.len()) > 200_000 {
            log_event("CHAT_BRIDGE","FAIL","Respuesta remota supera el limite de 200000 bytes.")?;
            return Err("CHAT_BRIDGE_RESPONSE_INVALID".into());
        }
        body.extend_from_slice(&chunk);
    }
    let text=String::from_utf8(body).map_err(|_|"CHAT_BRIDGE_RESPONSE_NOT_UTF8".to_string())?;
    let reply=serde_json::from_str::<Value>(&text).ok().and_then(|v|v.get("response").and_then(|x|x.as_str()).map(str::to_string)).unwrap_or(text.clone());
    if reply.trim().is_empty() {
        log_event("CHAT_BRIDGE","FAIL","Respuesta remota vacia.")?;
        return Err("CHAT_BRIDGE_RESPONSE_INVALID".into());
    }
    insert_chat("louksna",&reply,"remote-bridge")?;
    log_event("CHAT_BRIDGE","PASS","Round-trip remoto completado.")?;
    Ok(reply)
}

#[tauri::command]
fn runtime_probe()->Result<Value,String>{
    let data=data_dir()?; let db_path=data.join("louksna.db");
    let database=match db() {
        Ok(c) => c.query_row("SELECT 1",[],|r|r.get::<_,i64>(0)).map(|v|v==1).unwrap_or(false),
        Err(_) => false,
    };
    let secret_tool=Command::new("secret-tool").arg("--help").stdout(Stdio::null()).stderr(Stdio::null())
        .status().map(|s|s.success()).unwrap_or(false);
    let ready=database && secret_tool;
    Ok(serde_json::json!({"status":if ready {"PASS"} else {"DEGRADED"},"data_dir":data,"db_exists":db_path.exists(),"database_query":database,"secret_service_tool":secret_tool,"identity":"LOUKSNA","version":"0.3.0"}))
}

fn main(){
    if let Err(e)=db(){
        eprintln!("LOUKSNA_DB_INIT_FAIL:{e}");
        return;
    }
    if let Err(e)=log_event("APP_START","PASS","LOUKSNA V0.3 inicio backend local.") {
        eprintln!("LOUKSNA_START_EVIDENCE_FAILURE:{e}");
        return;
    }
    tauri::Builder::default()
      .invoke_handler(tauri::generate_handler![
        get_settings,save_settings,store_github_token,remove_github_token,
        github_connection,github_repositories,github_pull_requests,
        evidence_recent,chat_history,chat_send,runtime_probe
      ])
      .run(tauri::generate_context!())
      .expect("error while running LOUKSNA ZONA DIRECTIVA");
}


#[cfg(test)]
mod louksna_runtime_tests {
    use super::*;

    // Exercises the production Rust functions against an isolated on-disk SQLite database.
    // It intentionally does not claim native Tauri IPC, Secret Service, GUI, or voice coverage.
    #[test]
    fn sqlite_settings_chat_and_evidence_round_trip() {
        let root = std::env::temp_dir().join(format!(
            "louksna-zd-v03-runtime-test-{}-{}",
            std::process::id(),
            Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        std::fs::create_dir_all(&root).expect("create isolated test data directory");
        std::env::set_var("XDG_DATA_HOME", &root);

        let expected = Settings {
            offline_mode: true,
            preferred_repo: "Plomillo/luna-linux-bridge".to_string(),
            github_owner_filter: "Plomillo".to_string(),
            remote_chat_bridge: String::new(),
        };
        save_settings(expected.clone()).expect("persist settings through production command");
        let actual = load_settings_inner().expect("load settings through production backend");
        assert_eq!(actual.offline_mode, expected.offline_mode);
        assert_eq!(actual.preferred_repo, expected.preferred_repo);
        assert_eq!(actual.github_owner_filter, expected.github_owner_filter);
        assert_eq!(actual.remote_chat_bridge, expected.remote_chat_bridge);

        insert_chat("user", "runtime round-trip marker", "test")
            .expect("persist chat through production backend");
        let history = chat_history(Some(10)).expect("read chat through production backend");
        assert!(history.iter().any(|row|
            row.role == "user"
                && row.content == "runtime round-trip marker"
                && row.transport == "test"
        ));

        log_event("RUNTIME_SQLITE_TEST", "PASS", "Isolated production-function round-trip.").expect("evidence ledger write must succeed");
        let evidence = evidence_recent(Some(50)).expect("read evidence ledger");
        assert!(evidence.iter().any(|row|
            row.operation == "RUNTIME_SQLITE_TEST" && row.status == "PASS"
        ));

        drop(evidence);
        drop(history);
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn empty_chat_message_is_rejected_without_network_access() {
        let result = tauri::async_runtime::block_on(chat_send("   ".to_string()));
        assert_eq!(result.expect_err("empty chat must fail"), "EMPTY_MESSAGE");
    }

    #[test]
    fn evidence_ledger_failure_prevents_success_status() {
        let root = std::env::temp_dir().join(format!(
            "louksna-zd-v03-evidence-fail-{}-{}",
            std::process::id(),
            Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        std::fs::create_dir_all(&root).expect("create isolated failure-test directory");
        std::env::set_var("XDG_DATA_HOME", &root);
        let connection = db().expect("initialize isolated database");
        connection.execute_batch(
            "CREATE TRIGGER reject_evidence BEFORE INSERT ON evidence BEGIN SELECT RAISE(FAIL, 'injected evidence write failure'); END;"
        ).expect("install deterministic evidence failure injection");
        drop(connection);

        let result = save_settings(Settings {
            offline_mode: true,
            preferred_repo: "test/repository".to_string(),
            github_owner_filter: "test".to_string(),
            remote_chat_bridge: String::new(),
        });
        assert!(result.is_err(), "operation must not report success when evidence cannot be recorded");
        assert!(
            result.unwrap_err().contains("EVIDENCE_LEDGER_WRITE_FAILED"),
            "failure must identify the evidence ledger as the blocking cause"
        );
        let persisted = load_settings_inner().expect("settings table remains readable");
        assert_eq!(persisted, Settings::default(), "settings writes must roll back when the evidence ledger write fails");
        let _ = std::fs::remove_dir_all(&root);
    }
}
