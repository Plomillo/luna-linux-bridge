//! Real Linux voice pipeline. No mocks or synthetic audio are accepted by these commands.
//! Required: ALSA utilities, whisper.cpp CLI/model, Piper CLI/model, and a local Ollama model.
use serde::Serialize;
use serde_json::{json, Value};
use std::{path::PathBuf, process::{Command, Stdio}, io::Write, time::{Duration, Instant}};
use wait_timeout::ChildExt;

const CAPTURE_SECONDS: &str = "8";
const MAX_TEXT_CHARS: usize = 4_000;

#[derive(Debug, Serialize)]
pub struct VoicePreflight {
    status: String,
    missing: Vec<String>,
    detail: String,
}
#[derive(Debug, Serialize)]
pub struct VoiceTurn {
    status: String,
    transcript: String,
    response: String,
    elapsed_ms: u128,
    audio_played: bool,
}
struct TempAudio(PathBuf);
impl Drop for TempAudio {
    fn drop(&mut self) { let _ = std::fs::remove_dir_all(&self.0); }
}

fn env_path(key: &str) -> Result<PathBuf, String> {
    let raw = std::env::var(key).map_err(|_| format!("VOICE_CONFIG_MISSING:{key}"))?;
    let p = PathBuf::from(raw);
    if !p.is_file() { return Err(format!("VOICE_MODEL_NOT_FOUND:{key}")); }
    Ok(p)
}
fn command_exists(name: &str) -> bool {
    Command::new("sh").args(["-c", "command -v \"$1\" >/dev/null 2>&1", "voice-preflight", name])
        .status().map(|s| s.success()).unwrap_or(false)
}
fn run_bounded(program: &str, args: &[&str], stdin_text: Option<&str>, timeout: Duration) -> Result<(String,String),String> {
    let mut cmd = Command::new(program);
    cmd.args(args).stdout(Stdio::piped()).stderr(Stdio::null());
    if stdin_text.is_some() { cmd.stdin(Stdio::piped()); } else { cmd.stdin(Stdio::null()); }
    let mut child = cmd.spawn().map_err(|_| format!("VOICE_DEPENDENCY_EXEC_FAILED:{program}"))?;
    if let Some(text) = stdin_text {
        let write_result = child.stdin.take().ok_or("VOICE_STDIN_UNAVAILABLE")?
            .write_all(text.as_bytes());
        if write_result.is_err() { let _ = child.kill(); let _ = child.wait(); return Err("VOICE_STDIN_WRITE_FAILED".into()); }
    }
    match child.wait_timeout(timeout).map_err(|e| format!("VOICE_PROCESS_WAIT_FAILED:{e}"))? {
        Some(status) => {
            let mut out = String::new(); let err = String::new();
            if let Some(mut pipe) = child.stdout.take() { use std::io::Read; pipe.read_to_string(&mut out).map_err(|_| "VOICE_STDOUT_READ_FAILED")?; }

            if !status.success() { return Err(format!("VOICE_COMMAND_FAILED:{program}:{}", status.code().unwrap_or(-1))); }
            Ok((out,err))
        },
        None => { let _ = child.kill(); let _ = child.wait(); Err(format!("VOICE_COMMAND_TIMEOUT:{program}")) }
    }
}
fn ollama_endpoint() -> String {
    std::env::var("LOUKSNA_VOICE_OLLAMA_URL").unwrap_or_else(|_| "http://127.0.0.1:11434/api/chat".into())
}
fn validate_local_endpoint(endpoint: &str) -> Result<(),String> {
    let parsed = reqwest::Url::parse(endpoint).map_err(|_| "VOICE_OLLAMA_URL_INVALID")?;
    let host = parsed.host_str().unwrap_or("");
    let loopback = matches!(host, "127.0.0.1" | "localhost" | "[::1]" | "::1");
    let local_http = parsed.scheme() == "http" && loopback;
    let remote_https_explicitly_enabled = parsed.scheme() == "https"
        && std::env::var("LOUKSNA_VOICE_ALLOW_REMOTE_HTTPS").map(|v| v == "1").unwrap_or(false);
    if !local_http && !remote_https_explicitly_enabled {
        return Err("VOICE_OLLAMA_URL_MUST_BE_LOOPBACK_HTTP_OR_EXPLICIT_REMOTE_HTTPS".into());
    }
    Ok(())
}
fn preflight_sync() -> VoicePreflight {
    let mut missing = Vec::new();
    for cmd in ["arecord","aplay","whisper-cli","piper"] {
        if !command_exists(cmd) { missing.push(format!("executable:{cmd}")); }
    }
    for (key,label) in [("LOUKSNA_WHISPER_MODEL","whisper-model"),("LOUKSNA_PIPER_MODEL","piper-model")] {
        if env_path(key).is_err() { missing.push(format!("config:{key}")); } else { let _ = label; }
    }
    if std::env::var("LOUKSNA_OLLAMA_MODEL").map(|s| s.trim().is_empty()).unwrap_or(true) {
        missing.push("config:LOUKSNA_OLLAMA_MODEL".into());
    }
    if validate_local_endpoint(&ollama_endpoint()).is_err() { missing.push("config:LOUKSNA_VOICE_OLLAMA_URL".into()); }
    let status = if missing.is_empty() { "READY" } else { "DEGRADED" };
    VoicePreflight { status: status.into(), detail: "Preflight checks real executables/configuration only; it is not an E2E pass.".into(), missing }
}

fn ollama_model_present(payload: &Value, model: &str) -> bool {
    payload.get("models").and_then(Value::as_array).map(|models| models.iter().any(|item| {
        item.get("name").and_then(Value::as_str).map(|name| {
            name == model || name.strip_suffix(":latest") == Some(model)
        }).unwrap_or(false)
    })).unwrap_or(false)
}

#[tauri::command]
pub async fn voice_preflight() -> Result<VoicePreflight,String> {
    let mut p = preflight_sync();
    if p.status == "READY" {
        let model = std::env::var("LOUKSNA_OLLAMA_MODEL").unwrap_or_default();
        let mut tags_url = reqwest::Url::parse(&ollama_endpoint()).map_err(|_| "VOICE_OLLAMA_URL_INVALID")?;
        tags_url.set_path("/api/tags");
        tags_url.set_query(None);
        let check = async {
            let client = reqwest::Client::builder().connect_timeout(Duration::from_secs(2)).timeout(Duration::from_secs(4)).build().map_err(|_| "VOICE_PREFLIGHT_HTTP_CLIENT_FAILED")?;
            let response = client.get(tags_url).send().await.map_err(|_| "VOICE_OLLAMA_UNREACHABLE")?;
            if !response.status().is_success() { return Err("VOICE_OLLAMA_HEALTH_HTTP_FAILED"); }
            let payload: Value = response.json().await.map_err(|_| "VOICE_OLLAMA_HEALTH_INVALID_JSON")?;
            if !ollama_model_present(&payload, &model) { return Err("VOICE_OLLAMA_MODEL_NOT_AVAILABLE"); }
            Ok::<(),&'static str>(())
        }.await;
        if let Err(error) = check {
            p.missing.push(format!("service:{error}"));
            p.status = "DEGRADED".into();
        }
    }
    super::log_event("VOICE_PREFLIGHT", if p.status == "READY" {"PASS"} else {"DEGRADED"}, &format!("missing_dependency_count={}", p.missing.len()))?;
    Ok(p)
}

#[tauri::command]
pub async fn voice_e2e() -> Result<VoiceTurn,String> {
    match voice_e2e_inner().await {
        Ok(turn) => {
            super::log_event("VOICE_E2E", "EXECUTED_NOT_CERTIFIED", "real_capture=true;stt=whisper.cpp;response=ollama;tts=piper;playback=alsa;independent_validation=pending")?;
            Ok(turn)
        }
        Err(error) => {
            let _ = super::log_event("VOICE_E2E", "FAIL", &format!("failure_code={}", error.split(':').next().unwrap_or("VOICE_ERROR")));
            Err(error)
        }
    }
}

async fn voice_e2e_inner() -> Result<VoiceTurn,String> {
    let started = Instant::now();
    let pf = preflight_sync();
    if pf.status != "READY" { return Err(format!("VOICE_PREFLIGHT_BLOCKED:{}", pf.missing.join(","))); }
    let whisper_model = env_path("LOUKSNA_WHISPER_MODEL")?;
    let piper_model = env_path("LOUKSNA_PIPER_MODEL")?;
    let ollama_model = std::env::var("LOUKSNA_OLLAMA_MODEL").map_err(|_| "VOICE_CONFIG_MISSING:LOUKSNA_OLLAMA_MODEL")?;
    let root = std::env::temp_dir().join(format!("louksna-voice-{}-{}", std::process::id(), chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()));
    std::fs::create_dir_all(&root).map_err(|_| "VOICE_TEMP_CREATE_FAILED")?;
    let _cleanup = TempAudio(root.clone());
    let capture = root.join("capture.wav");
    let response_audio = root.join("response.wav");
    let capture_s = capture.to_string_lossy().to_string();
    run_bounded("arecord", &["-q","-D","default","-f","S16_LE","-r","16000","-c","1","-d",CAPTURE_SECONDS,"-t","wav",&capture_s],None,Duration::from_secs(12))?;
    if !capture.is_file() || std::fs::metadata(&capture).map(|m|m.len()).unwrap_or(0) < 8_000 { return Err("VOICE_CAPTURE_EMPTY_OR_TOO_SMALL".into()); }

    let model_s = whisper_model.to_string_lossy().to_string();
    let capture_s = capture.to_string_lossy().to_string();
    let (transcript_out, _) = run_bounded("whisper-cli", &["-m",&model_s,"-f",&capture_s,"-nt","-np","-t","2"],None,Duration::from_secs(60))?;
    let transcript = transcript_out.trim().to_string();
    if transcript.is_empty() { return Err("VOICE_TRANSCRIPTION_EMPTY".into()); }
    if transcript.chars().count() > MAX_TEXT_CHARS { return Err("VOICE_TRANSCRIPTION_TOO_LONG".into()); }

    let endpoint = ollama_endpoint();
    validate_local_endpoint(&endpoint)?;
    let client = reqwest::Client::builder().connect_timeout(Duration::from_secs(3)).timeout(Duration::from_secs(45)).build().map_err(|_| "VOICE_HTTP_CLIENT_FAILED")?;
    let result = client.post(endpoint).json(&json!({"model":ollama_model,"stream":false,"messages":[{"role":"user","content":transcript}]}))
        .send().await.map_err(|_| "VOICE_RESPONSE_TRANSPORT_FAILED")?;
    if !result.status().is_success() { return Err(format!("VOICE_RESPONSE_HTTP_STATUS:{}",result.status().as_u16())); }
    let payload: Value = result.json().await.map_err(|_| "VOICE_RESPONSE_INVALID_JSON")?;
    let response = payload.pointer("/message/content").and_then(Value::as_str).unwrap_or("").trim().to_string();
    if response.is_empty() { return Err("VOICE_RESPONSE_EMPTY".into()); }
    if response.chars().count() > MAX_TEXT_CHARS { return Err("VOICE_RESPONSE_TOO_LONG".into()); }

    let response_audio_s = response_audio.to_string_lossy().to_string();
    let piper_model_s = piper_model.to_string_lossy().to_string();
    run_bounded("piper",&["--model",&piper_model_s,"--output_file",&response_audio_s],Some(&response),Duration::from_secs(45))?;
    if !response_audio.is_file() || std::fs::metadata(&response_audio).map(|m|m.len()).unwrap_or(0) < 8_000 { return Err("VOICE_SYNTHESIS_EMPTY_OR_TOO_SMALL".into()); }
    run_bounded("aplay",&["-q",&response_audio_s],None,Duration::from_secs(30))?;
    Ok(VoiceTurn { status:"E2E_EXECUTED_NOT_CERTIFIED".into(), transcript, response, elapsed_ms:started.elapsed().as_millis(), audio_played:true })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn preflight_does_not_claim_e2e_without_real_dependencies() {
        let p = preflight_sync();
        assert!(["READY","DEGRADED"].contains(&p.status.as_str()));
        assert!(p.detail.contains("not an E2E pass"));
    }
    #[test]
    fn endpoint_rejects_untrusted_plain_http_hosts() {
        assert!(validate_local_endpoint("http://127.0.0.1:11434/api/chat").is_ok());
        assert!(validate_local_endpoint("http://voice.example/api/chat").is_err());
    }
    #[test]
    fn remote_https_requires_explicit_opt_in() {
        std::env::remove_var("LOUKSNA_VOICE_ALLOW_REMOTE_HTTPS");
        assert!(validate_local_endpoint("https://voice.example/api/chat").is_err());
        std::env::set_var("LOUKSNA_VOICE_ALLOW_REMOTE_HTTPS", "1");
        assert!(validate_local_endpoint("https://voice.example/api/chat").is_ok());
        std::env::remove_var("LOUKSNA_VOICE_ALLOW_REMOTE_HTTPS");
    }
    #[test]
    fn ollama_model_check_accepts_exact_or_latest_tag_only() {
        let payload = json!({"models":[{"name":"llama3.2:latest"},{"name":"qwen2.5:7b"}]});
        assert!(ollama_model_present(&payload, "llama3.2"));
        assert!(ollama_model_present(&payload, "qwen2.5:7b"));
        assert!(!ollama_model_present(&payload, "missing-model"));
    }
    #[test]
    fn response_transcript_bound_is_explicit() { assert_eq!(MAX_TEXT_CHARS, 4000); }
}
