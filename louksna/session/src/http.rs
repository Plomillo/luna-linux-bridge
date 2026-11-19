use crate::error::{err, Result};
use crate::flow;
use crate::g23;
use crate::runtime::App;
use crate::store;
use serde_json::{json, Value};
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::path::Path;

pub fn enforce_loopback(addr: &str) -> Result<SocketAddr> {
    let parsed: SocketAddr = addr.parse().map_err(|_| err("BIND_ADDRESS_INVALID"))?;
    if !parsed.ip().is_loopback() {
        return Err(err("BIND_NOT_LOOPBACK"));
    }
    Ok(parsed)
}

const INDEX: &str = include_str!("../ui/index.html");
const APP_JS: &str = include_str!("../ui/app.js");
const CSS: &str = include_str!("../ui/styles.css");
const ICON: &str = include_str!("../ui/icon.svg");

pub fn serve(state_dir: &Path, addr: &str) -> Result<()> {
    let socket = enforce_loopback(addr)?;
    let listener = TcpListener::bind(socket)?;
    for conn in listener.incoming() {
        match conn {
            Ok(stream) => {
                if let Err(e) = handle(state_dir, stream) {
                    eprintln!("LOUKSNA_HTTP:{e}");
                }
            }
            Err(e) => eprintln!("LOUKSNA_ACCEPT:{e}"),
        }
    }
    Ok(())
}

fn handle(state_dir: &Path, mut stream: TcpStream) -> Result<()> {
    let peer = stream.peer_addr()?;
    if !peer.ip().is_loopback() {
        return write_response(&mut stream, 403, "application/json", br#"{"error":"PEER_NOT_LOOPBACK"}"#);
    }
    let mut buf = vec![0u8; 1024 * 256];
    let n = stream.read(&mut buf)?;
    buf.truncate(n);
    let text = String::from_utf8_lossy(&buf);
    let mut lines = text.split("\r\n");
    let request = lines.next().unwrap_or("");
    let mut parts = request.split(' ');
    let method = parts.next().unwrap_or("");
    let target = parts.next().unwrap_or("/");
    let mut content_length = 0usize;
    let mut client_ok = false;
    for line in lines.by_ref() {
        if line.is_empty() {
            break;
        }
        let lower = line.to_ascii_lowercase();
        if let Some(v) = lower.strip_prefix("content-length:") {
            content_length = v.trim().parse().unwrap_or(0);
        }
        if lower.starts_with("x-louksna-client:") && lower.split(':').nth(1).unwrap_or("").trim() == "luna" {
            client_ok = true;
        }
    }
    let header_end = text.find("\r\n\r\n").map(|i| i + 4).unwrap_or(text.len());
    let mut body = buf.get(header_end..).unwrap_or(&[]).to_vec();
    while body.len() < content_length && body.len() < 5_000_000 {
        let mut tmp = [0u8; 8192];
        let k = stream.read(&mut tmp)?;
        if k == 0 {
            break;
        }
        body.extend_from_slice(&tmp[..k]);
    }
    body.truncate(content_length);

    let path = target.split('?').next().unwrap_or("/");
    if method == "GET" && !path.starts_with("/api/") {
        return match path {
            "/" | "/index.html" => write_response(&mut stream, 200, "text/html; charset=utf-8", INDEX.as_bytes()),
            "/app.js" => write_response(&mut stream, 200, "text/javascript; charset=utf-8", APP_JS.as_bytes()),
            "/styles.css" => write_response(&mut stream, 200, "text/css; charset=utf-8", CSS.as_bytes()),
            "/icon.svg" => write_response(&mut stream, 200, "image/svg+xml", ICON.as_bytes()),
            _ if path.starts_with("/reference/") => serve_reference(&mut stream, path),
            _ => write_response(&mut stream, 404, "application/json", br#"{"error":"NOT_FOUND"}"#),
        };
    }
    if !client_ok {
        return write_response(&mut stream, 403, "application/json", br#"{"error":"CLIENT_HEADER_REQUIRED"}"#);
    }
    let app = App::open(state_dir)?;
    let result = dispatch(&app, method, path, target, &body);
    match result {
        Ok(value) => {
            let bytes = serde_json::to_vec(&value)?;
            write_response(&mut stream, 200, "application/json", &bytes)
        }
        Err(e) => {
            let bytes = serde_json::to_vec(&json!({"error": e.0}))?;
            write_response(&mut stream, 400, "application/json", &bytes)
        }
    }
}

fn serve_reference(stream: &mut TcpStream, path: &str) -> Result<()> {
    let name = path.trim_start_matches("/reference/");
    if name.contains("..") || name.contains('/') {
        return write_response(stream, 400, "application/json", br#"{"error":"BAD_REFERENCE"}"#);
    }
    let roots = [
        std::env::var("LOUKSNA_REFERENCE_DIR").unwrap_or_default(),
        "/usr/share/louksna/reference".into(),
    ];
    for root in roots {
        if root.is_empty() {
            continue;
        }
        let file = Path::new(&root).join(name);
        if file.is_file() {
            let bytes = std::fs::read(file)?;
            return write_response(stream, 200, "image/png", &bytes);
        }
    }
    write_response(stream, 404, "application/json", br#"{"error":"REFERENCE_ABSENT"}"#)
}

fn dispatch(app: &App, method: &str, path: &str, target: &str, body: &[u8]) -> Result<Value> {
    let payload: Value = if body.is_empty() { json!({}) } else { serde_json::from_slice(body).unwrap_or(json!({})) };
    match (method, path) {
        ("GET", "/api/probe") => app.probe(),
        ("GET", "/api/settings") => app.store.load_settings(),
        ("POST", "/api/settings") => {
            app.store.save_settings_obj(&payload)?;
            Ok(json!({"ok": true}))
        }
        ("GET", "/api/evidence") => Ok(json!(app.store.evidence_recent(100)?)),
        ("GET", "/api/chat") => Ok(json!(app.store.chat_history(100)?)),
        ("POST", "/api/chat") => {
            let message = payload.get("message").and_then(|v| v.as_str()).unwrap_or("");
            let reply = app.chat_send(message)?;
            Ok(json!({"reply": reply}))
        }
        ("POST", "/api/token") => {
            let token = payload.get("token").and_then(|v| v.as_str()).unwrap_or("");
            let kind = app.store_credential(token)?;
            Ok(json!({"ok": true, "kind": kind}))
        }
        ("POST", "/api/token/remove") => {
            app.remove_credential()?;
            Ok(json!({"ok": true}))
        }
        ("GET", "/api/github/connection") => app.github_connection(),
        ("GET", "/api/github/repos") => Ok(json!(app.github_repos()?)),
        ("GET", "/api/github/pulls") => {
            let repo = query_param(target, "repo").unwrap_or_default();
            Ok(json!(app.github_pulls(&repo)?))
        }
        ("GET", "/api/github/issues") => {
            let repo = query_param(target, "repo").unwrap_or_default();
            Ok(json!(app.github_issues(&repo)?))
        }
        ("GET", "/api/layers") => Ok(json!({"count": app.store.layer_count()?, "names": crate::store::LAYER_NAMES})),
        ("GET", "/api/plans") => flow::plans_overview(&app.store),
        ("POST", "/api/plans") => {
            let title = payload.get("title").and_then(|v| v.as_str()).unwrap_or("");
            let scope = payload.get("scope").and_then(|v| v.as_array()).cloned().unwrap_or_default();
            let scope: Vec<String> = scope.into_iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect();
            let id = flow::create_plan(&app.store, title, &scope)?;
            Ok(json!({"id": id, "state": "AWAITING_APPROVAL"}))
        }
        ("POST", "/api/plans/approve") => {
            let id = payload.get("id").and_then(|v| v.as_str()).unwrap_or("");
            flow::approve_plan(&app.store, id)?;
            Ok(json!({"id": id, "state": "AUTHORIZED"}))
        }
        ("POST", "/api/tasks") => {
            let plan = payload.get("plan_id").and_then(|v| v.as_str()).unwrap_or("");
            let kind = payload.get("kind").and_then(|v| v.as_str()).unwrap_or("");
            let task_payload = payload.get("payload").and_then(|v| v.as_str()).unwrap_or("");
            let id = flow::enqueue_task(&app.store, plan, kind, task_payload)?;
            flow::complete_task(&app.store, &id, true, "local-ack")?;
            Ok(json!({"id": id}))
        }
        ("POST", "/api/voice/session") => {
            let state = payload.get("state").and_then(|v| v.as_str()).unwrap_or("ACTIVE");
            flow::set_session(&app.store, "VOICE_SESSION", state)?;
            Ok(json!({"kind": "VOICE_SESSION", "state": state}))
        }
        ("GET", "/api/sessions") => Ok(json!({
            "voice": flow::session_state(&app.store, "VOICE_SESSION").unwrap_or_else(|_| "ABSENT".into()),
            "task": flow::session_state(&app.store, "TASK_SESSION").unwrap_or_else(|_| "ABSENT".into())
        })),
        ("POST", "/api/voice/speak") => {
            let text = payload.get("text").and_then(|v| v.as_str()).unwrap_or("");
            let path = app.speak(text)?;
            Ok(json!({"ok": true, "wav": path, "speaker": "1"}))
        }
        ("POST", "/api/voice/transcribe") => {
            let path = payload.get("wav").and_then(|v| v.as_str()).unwrap_or("");
            let wav = Path::new(path);
            if !wav.starts_with(&app.state_dir) {
                return Err(err("WAV_OUTSIDE_STATE"));
            }
            let text = app.transcribe_wav(wav)?;
            Ok(json!({"text": text}))
        }
        ("POST", "/api/checkpoints") => {
            let id = format!("cp-{}", store::now());
            let path = app.state_dir.join("checkpoints").join(format!("{id}.sqlite"));
            app.store.snapshot_to(&path)?;
            let sha = store::file_sha256(&path)?;
            app.store.conn().execute(
                "INSERT INTO checkpoints(id,label,db_sha256,path,created_at) VALUES(?1,?2,?3,?4,?5)",
                rusqlite::params![id, id, sha, path.display().to_string(), store::now()],
            )?;
            Ok(json!({"id": id, "sha256": sha}))
        }
        ("POST", "/api/g23") => {
            let verdict = g23::validate(&app.store)?;
            let path = app.state_dir.join("g23-verdict.json");
            g23::write_verdict(&path, &verdict)?;
            Ok(verdict)
        }
        ("POST", "/api/g24") => {
            let subject = payload.get("subject").and_then(|v| v.as_str()).unwrap_or("product");
            g23::certify_g24(&app.store, &app.state_dir.join("g23-verdict.json"), subject)
        }
        _ => Err(err("NO_ROUTE")),
    }
}

fn query_param(target: &str, key: &str) -> Option<String> {
    let q = target.split_once('?')?.1;
    for pair in q.split('&') {
        if let Some((k, v)) = pair.split_once('=') {
            if k == key {
                return Some(v.to_string());
            }
        }
    }
    None
}

fn write_response(stream: &mut TcpStream, status: u16, content_type: &str, body: &[u8]) -> Result<()> {
    let reason = match status {
        200 => "OK",
        400 => "Bad Request",
        403 => "Forbidden",
        404 => "Not Found",
        _ => "Error",
    };
    let header = format!(
        "HTTP/1.1 {status} {reason}\r\nContent-Type: {content_type}\r\nContent-Length: {}\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n\r\n",
        body.len()
    );
    stream.write_all(header.as_bytes())?;
    stream.write_all(body)?;
    Ok(())
}
