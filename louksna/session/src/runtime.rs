use crate::error::{err, Result};
use crate::flow;
use crate::github::{self, UreqGithub};
use crate::store::{self, write_secret_file, Store};
use crate::voice;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};

enum ChatCall {
    Ok(String),
    Status(u16, String),
    Net(String),
}

pub struct App {
    pub state_dir: PathBuf,
    pub store: Store,
}

impl App {
    pub fn open(state_dir: &Path) -> Result<Self> {
        std::fs::create_dir_all(state_dir)?;
        let db_path = state_dir.join("louksna.db");
        let store = Store::open(&db_path)?;
        Ok(App {
            state_dir: state_dir.to_path_buf(),
            store,
        })
    }

    pub fn probe(&self) -> Result<Value> {
        let layers = self.store.layer_count()?;
        Ok(json!({
            "status": if layers == 15 { "PASS" } else { "DEGRADED" },
            "identity": "LUNA",
            "product": "LOUKSNA",
            "version": "3.0.0",
            "layers": layers,
            "bind": "127.0.0.1",
            "certification": "NOT_CERTIFIED",
            "voice_primary": "piper:es_ES-sharvard-medium:speaker=1",
            "paid_inference": false
        }))
    }

    pub fn chat_send(&self, message: &str) -> Result<String> {
        let msg = message.trim();
        if msg.is_empty() {
            return Err(err("EMPTY_MESSAGE"));
        }
        self.store.insert_chat("user", msg, "local")?;
        let settings = self.store.load_settings()?;
        if settings.get("offline_mode").and_then(|v| v.as_bool()).unwrap_or(false)
            && !settings.get("remote_chat_bridge").and_then(|v| v.as_str()).unwrap_or("").is_empty()
        {
            return Err(err("OFFLINE_MODE_ENABLED"));
        }
        let bridge = settings.get("remote_chat_bridge").and_then(|v| v.as_str()).unwrap_or("").trim().to_string();
        if bridge.is_empty() {
            if let Some(key) = self.engine_key() {
                if settings.get("offline_mode").and_then(|v| v.as_bool()).unwrap_or(false) {
                    return Err(err("OFFLINE_MODE_ENABLED"));
                }
                return self.chat_engine(&key);
            }
            let reply = "Mensaje registrado. El bridge remoto de arquitectura todavia no esta enlazado; no simulare una respuesta remota.";
            self.store.insert_chat("louksna", reply, "local-status")?;
            self.store.log_event("CHAT", "PARTIAL", "Mensaje persistido; bridge remoto no configurado.")?;
            return Ok(reply.to_string());
        }
        self.post_bridge(&bridge, msg)
    }

    fn engine_key(&self) -> Option<String> {
        if let Ok(value) = std::env::var("LOUKSNA_XAI_API_KEY") {
            let value = value.trim().to_string();
            if value.len() >= 20 {
                return Some(value);
            }
        }
        std::fs::read_to_string(self.state_dir.join("secrets/xai_api_key"))
            .ok()
            .map(|s| s.trim().to_string())
            .filter(|s| s.len() >= 20)
    }

    fn chat_cancel_requested(&self) -> bool {
        self.state_dir.join("chat.cancel").is_file()
    }

    fn chat_engine(&self, key: &str) -> Result<String> {
        if self.chat_cancel_requested() {
            let _ = std::fs::remove_file(self.state_dir.join("chat.cancel"));
            self.store.log_event("CHAT_ENGINE", "FAIL", "cancelled before dispatch")?;
            return Err(err("CHAT_CANCELLED"));
        }
        let history = self.store.chat_history(40)?;
        let mut messages = vec![json!({"role":"system","content":"Eres LUNA, la sesion LOUKSNA. Responde en espanol, breve y concreto. No afirmes certificacion. No reveles credenciales."})];
        for item in &history {
            let role = item.get("role").and_then(|v| v.as_str()).unwrap_or("user");
            let content = item.get("content").and_then(|v| v.as_str()).unwrap_or("");
            let api_role = if role == "louksna" { "assistant" } else { "user" };
            messages.push(json!({"role": api_role, "content": content}));
        }
        let model = std::env::var("LOUKSNA_CHAT_MODEL").unwrap_or_else(|_| "grok-4.20-0309-non-reasoning".into());
        let url = self.completions_url()?;
        let payload = json!({"model": model, "messages": messages, "temperature": 0});
        let timeout = self.chat_timeout();
        let url_call = url.clone();
        let key_call = key.to_string();
        let (tx, rx) = std::sync::mpsc::channel();
        std::thread::spawn(move || {
            let agent = ureq::AgentBuilder::new()
                .https_only(true)
                .redirects(0)
                .timeout(timeout)
                .build();
            let outcome = match agent
                .post(&url_call)
                .set("Authorization", &format!("Bearer {key_call}"))
                .set("Content-Type", "application/json")
                .set("User-Agent", "LOUKSNA-ZONA-DIRECTIVA/3.0")
                .send_json(payload)
            {
                Ok(resp) => match resp.into_string() {
                    Ok(text) => ChatCall::Ok(text),
                    Err(e) => ChatCall::Net(e.to_string()),
                },
                Err(ureq::Error::Status(code, resp)) => ChatCall::Status(code, resp.into_string().unwrap_or_default()),
                Err(e) => ChatCall::Net(e.to_string()),
            };
            let _ = tx.send(outcome);
        });
        let started = std::time::Instant::now();
        let outcome = loop {
            if self.chat_cancel_requested() {
                let _ = std::fs::remove_file(self.state_dir.join("chat.cancel"));
                self.store.log_event("CHAT_ENGINE", "FAIL", "cancelled during dispatch")?;
                return Err(err("CHAT_CANCELLED"));
            }
            match rx.recv_timeout(std::time::Duration::from_millis(200)) {
                Ok(outcome) => break outcome,
                Err(std::sync::mpsc::RecvTimeoutError::Timeout) if started.elapsed() >= timeout => {
                    self.store.log_event("CHAT_ENGINE", "FAIL", "CHAT_ENGINE_TIMEOUT")?;
                    self.store.insert_chat(
                        "louksna",
                        "El motor remoto no respondio dentro del tiempo limite. No hay respuesta simulada.",
                        "xai-error",
                    )?;
                    return Err(err("CHAT_ENGINE_TIMEOUT"));
                }
                Err(std::sync::mpsc::RecvTimeoutError::Timeout) => continue,
                Err(std::sync::mpsc::RecvTimeoutError::Disconnected) => {
                    self.store.log_event("CHAT_ENGINE", "FAIL", "CHAT_ENGINE_NETWORK:disconnected")?;
                    self.store.insert_chat(
                        "louksna",
                        "El motor remoto no pudo contactarse. No hay respuesta simulada.",
                        "xai-error",
                    )?;
                    return Err(err("CHAT_ENGINE_NETWORK"));
                }
            }
        };
        if self.chat_cancel_requested() {
            let _ = std::fs::remove_file(self.state_dir.join("chat.cancel"));
            self.store.log_event("CHAT_ENGINE", "FAIL", "cancelled after dispatch")?;
            return Err(err("CHAT_CANCELLED"));
        }
        let text = match outcome {
            ChatCall::Ok(text) => text,
            ChatCall::Status(code, body) => {
                let kind = match code {
                    402 => "CHAT_ENGINE_SPENDING_LIMIT",
                    401 | 403 => "CHAT_ENGINE_UNAUTHORIZED",
                    408 | 429 => "CHAT_ENGINE_RATE_OR_TIMEOUT",
                    _ => "CHAT_ENGINE_HTTP",
                };
                let detail = self.scrub(
                    format!("{kind} HTTP {code} {}", body.chars().take(160).collect::<String>()),
                    key,
                );
                self.store.log_event("CHAT_ENGINE", "FAIL", &detail)?;
                let honest = match code {
                    402 => "El motor remoto rechazo la solicitud por limite de credito. No hay respuesta simulada.",
                    401 | 403 => "El motor remoto rechazo la autenticacion. No hay respuesta simulada.",
                    _ => "El motor remoto devolvio un error. No hay respuesta simulada.",
                };
                self.store.insert_chat("louksna", honest, "xai-error")?;
                return Err(err(detail));
            }
            ChatCall::Net(raw) => {
                let kind = if raw.to_ascii_lowercase().contains("timed") {
                    "CHAT_ENGINE_TIMEOUT"
                } else {
                    "CHAT_ENGINE_NETWORK"
                };
                let detail = self.scrub(format!("{kind}:{raw}"), key);
                self.store.log_event("CHAT_ENGINE", "FAIL", &detail)?;
                let honest = if kind == "CHAT_ENGINE_TIMEOUT" {
                    "El motor remoto no respondio dentro del tiempo limite. No hay respuesta simulada."
                } else {
                    "El motor remoto no pudo contactarse. No hay respuesta simulada."
                };
                self.store.insert_chat("louksna", honest, "xai-error")?;
                return Err(err(detail));
            }
        };
        let parsed: Value = serde_json::from_str(&text).map_err(|e| err(self.scrub(e.to_string(), key)))?;
        let reply = parsed
            .pointer("/choices/0/message/content")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_string();
        if reply.is_empty() || reply.len() > 200_000 {
            return Err(err("CHAT_ENGINE_RESPONSE_INVALID"));
        }
        let reply = self.scrub(reply, key);
        self.store.insert_chat("louksna", &reply, "xai")?;
        self.store.log_event("CHAT_ENGINE", "PASS", "Round-trip xAI completado.")?;
        Ok(reply)
    }

    fn scrub(&self, text: String, key: &str) -> String {
        let mut out = crate::store::redact(&text);
        if !key.is_empty() {
            out = out.replace(key, "[REDACTED]");
        }
        out
    }

    fn chat_timeout(&self) -> std::time::Duration {
        let secs = std::env::var("LOUKSNA_CHAT_TIMEOUT_SECS")
            .ok()
            .and_then(|s| s.parse::<u64>().ok())
            .unwrap_or(45)
            .clamp(1, 120);
        std::time::Duration::from_secs(secs)
    }

    fn completions_url(&self) -> Result<String> {
        let url = std::env::var("LOUKSNA_CHAT_COMPLETIONS_URL")
            .unwrap_or_else(|_| "https://api.x.ai/v1/chat/completions".into());
        let url = url.trim().to_string();
        if !url.starts_with("https://") || url[8..].contains('@') || url.contains(' ') || url.contains('\\') {
            return Err(err("CHAT_URL_REJECTED"));
        }
        Ok(url)
    }

    fn post_bridge(&self, bridge: &str, msg: &str) -> Result<String> {
        if !bridge.starts_with("https://") || bridge[8..].contains('@') {
            return Err(err("CHAT_BRIDGE_URL_REQUIRES_HTTPS_VALID_HOST_NO_USERINFO"));
        }
        let host = bridge[8..].split(['/', '?', '#']).next().unwrap_or("");
        if host.is_empty() || host.contains(' ') {
            return Err(err("CHAT_BRIDGE_URL_INVALID"));
        }
        let agent = ureq::AgentBuilder::new().https_only(true).redirects(0).build();
        let response = agent
            .post(bridge)
            .set("User-Agent", "LOUKSNA-ZONA-DIRECTIVA/3.0")
            .send_json(json!({"message": msg, "source": "LOUKSNA_ZONA_DIRECTIVA", "mode": "GOVERNED"}));
        match response {
            Ok(resp) => {
                if resp.status() != 200 {
                    self.store.log_event("CHAT_BRIDGE", "FAIL", &format!("HTTP {}", resp.status()))?;
                    return Err(err(format!("CHAT_BRIDGE_HTTP_{}", resp.status())));
                }
                let text = resp.into_string().map_err(|e| err(e.to_string()))?;
                if text.trim().is_empty() || text.len() > 200_000 {
                    return Err(err("CHAT_BRIDGE_RESPONSE_INVALID"));
                }
                let reply = serde_json::from_str::<Value>(&text)
                    .ok()
                    .and_then(|v| v.get("response").and_then(|x| x.as_str()).map(|s| s.to_string()))
                    .unwrap_or(text);
                self.store.insert_chat("louksna", &reply, "remote-bridge")?;
                self.store.log_event("CHAT_BRIDGE", "PASS", "Round-trip remoto completado.")?;
                Ok(reply)
            }
            Err(ureq::Error::Status(code, _)) => {
                self.store.log_event("CHAT_BRIDGE", "FAIL", &format!("HTTP {code}"))?;
                Err(err(format!("CHAT_BRIDGE_HTTP_{code}")))
            }
            Err(e) => Err(err(format!("CHAT_BRIDGE_NETWORK_ERROR:{e}"))),
        }
    }

    pub fn store_credential(&self, token: &str) -> Result<&'static str> {
        let kind = github::classify_credential(token)?;
        let secrets = self.state_dir.join("secrets");
        match kind {
            "installation" | "user_to_server" => {
                write_secret_file(&secrets.join("installation_token"), token.trim())?;
                self.store.log_event("GITHUB_SECRET_STORE", "PASS", &format!("credential kind={kind} stored mode 0600; value not recorded."))?;
                Ok(kind)
            }
            "app_private_key" => {
                write_secret_file(&secrets.join("github_app.pem"), token.trim())?;
                self.store.log_event("GITHUB_APP_KEY_STORE", "PASS", "App private key stored mode 0600; value not recorded.")?;
                Ok("app_private_key")
            }
            _ => Err(err("CREDENTIAL_REJECTED")),
        }
    }

    pub fn remove_credential(&self) -> Result<()> {
        let _ = std::fs::remove_file(self.state_dir.join("secrets/installation_token"));
        let _ = std::fs::remove_file(self.state_dir.join("secrets/github_app.pem"));
        if self.installation_token().is_some() {
            return Err(err("SECRET_CLEAR_NOT_VERIFIED"));
        }
        self.store.log_event("GITHUB_SECRET_REMOVE", "PASS", "Ausencia de credencial verificada.")?;
        Ok(())
    }

    fn installation_token(&self) -> Option<String> {
        std::fs::read_to_string(self.state_dir.join("secrets/installation_token")).ok().map(|s| s.trim().to_string()).filter(|s| !s.is_empty())
    }

    fn offline(&self) -> Result<bool> {
        Ok(self.store.load_settings()?.get("offline_mode").and_then(|v| v.as_bool()).unwrap_or(false))
    }

    pub fn github_connection(&self) -> Result<Value> {
        if self.offline()? {
            return Err(err("OFFLINE_MODE_ENABLED"));
        }
        let token = self.installation_token().ok_or_else(|| err("GITHUB_TOKEN_NOT_STORED"))?;
        let kind = github::classify_credential(&token)?;
        if kind == "user_to_server" {
            let (_status, body) = UreqGithub::get_json("https://api.github.com/user", &token)?;
            let user = github::parse_user(&body)?;
            self.store.log_event("GITHUB_API", "PASS", "user endpoint respondio.")?;
            return Ok(user);
        }
        let (_status, body) = UreqGithub::get_json(&github::installation_repo_url(1), &token)?;
        let repos = github::parse_installation_repos(&body)?;
        self.store.log_event("GITHUB_API", "PASS", "installation/repositories respondio.")?;
        Ok(json!({
            "connected": true,
            "login": "installation",
            "name": "GitHub App",
            "repository_count_page": repos.len()
        }))
    }

    pub fn github_repos(&self) -> Result<Vec<Value>> {
        if self.offline()? {
            return Err(err("OFFLINE_MODE_ENABLED"));
        }
        let token = self.installation_token().ok_or_else(|| err("GITHUB_TOKEN_NOT_STORED"))?;
        let kind = github::classify_credential(&token)?;
        let (_status, body) = if kind == "user_to_server" {
            UreqGithub::get_json(&github::user_repos_url(100), &token)?
        } else {
            UreqGithub::get_json(&github::installation_repo_url(100), &token)?
        };
        let repos = if kind == "user_to_server" {
            github::parse_user_repos(&body)?
        } else {
            github::parse_installation_repos(&body)?
        };
        let filter = self.store.load_settings()?.get("github_owner_filter").and_then(|v| v.as_str()).unwrap_or("").to_string();
        let repos = if filter.is_empty() {
            repos
        } else {
            repos.into_iter().filter(|r| r.get("full_name").and_then(|v| v.as_str()).unwrap_or("").starts_with(&format!("{filter}/"))).collect()
        };
        self.store.log_event("GITHUB_REPOS", "PASS", &format!("{} repositorios", repos.len()))?;
        Ok(repos)
    }

    pub fn github_pulls(&self, repo: &str) -> Result<Vec<Value>> {
        if self.offline()? {
            return Err(err("OFFLINE_MODE_ENABLED"));
        }
        let token = self.installation_token().ok_or_else(|| err("GITHUB_TOKEN_NOT_STORED"))?;
        let (_status, body) = UreqGithub::get_json(&github::pulls_url(repo)?, &token)?;
        let prs = github::parse_pulls(&body)?;
        self.store.log_event("GITHUB_PULLS", "PASS", &format!("{repo} count={}", prs.len()))?;
        Ok(prs)
    }

    pub fn github_issues(&self, repo: &str) -> Result<Vec<Value>> {
        if self.offline()? {
            return Err(err("OFFLINE_MODE_ENABLED"));
        }
        let token = self.installation_token().ok_or_else(|| err("GITHUB_TOKEN_NOT_STORED"))?;
        let (_status, body) = UreqGithub::get_json(&github::issues_url(repo)?, &token)?;
        let issues = github::parse_pulls(&body)?;
        self.store.log_event("GITHUB_ISSUES", "PASS", &format!("{repo} count={}", issues.len()))?;
        Ok(issues)
    }

    pub fn github_branch(&self, repo: &str, name: &str) -> Result<Value> {
        if self.offline()? {
            return Err(err("OFFLINE_MODE_ENABLED"));
        }
        let token = self.installation_token().ok_or_else(|| err("GITHUB_TOKEN_NOT_STORED"))?;
        let (_status, body) = UreqGithub::get_json(&github::branch_url(repo, name)?, &token)?;
        let row = github::parse_branch(&body)?;
        self.store.log_event("GITHUB_BRANCH", "PASS", &format!("{repo} {name}"))?;
        Ok(row)
    }

    pub fn github_branches(&self, repo: &str) -> Result<Vec<Value>> {
        if self.offline()? {
            return Err(err("OFFLINE_MODE_ENABLED"));
        }
        let token = self.installation_token().ok_or_else(|| err("GITHUB_TOKEN_NOT_STORED"))?;
        let (_status, body) = UreqGithub::get_json(&github::branches_url(repo)?, &token)?;
        let rows = github::parse_branches(&body)?;
        self.store.log_event("GITHUB_BRANCHES", "PASS", &format!("{repo} count={}", rows.len()))?;
        Ok(rows)
    }

    pub fn github_commits(&self, repo: &str) -> Result<Vec<Value>> {
        if self.offline()? {
            return Err(err("OFFLINE_MODE_ENABLED"));
        }
        let token = self.installation_token().ok_or_else(|| err("GITHUB_TOKEN_NOT_STORED"))?;
        let (_status, body) = UreqGithub::get_json(&github::commits_url(repo)?, &token)?;
        let rows = github::parse_commits(&body)?;
        self.store.log_event("GITHUB_COMMITS", "PASS", &format!("{repo} count={}", rows.len()))?;
        Ok(rows)
    }

    pub fn github_file(&self, repo: &str, path: &str) -> Result<Value> {
        if self.offline()? {
            return Err(err("OFFLINE_MODE_ENABLED"));
        }
        let token = self.installation_token().ok_or_else(|| err("GITHUB_TOKEN_NOT_STORED"))?;
        let (_status, body) = UreqGithub::get_json(&github::contents_url(repo, path)?, &token)?;
        let file = github::parse_contents(&body)?;
        let sha = file.get("sha").and_then(|v| v.as_str()).unwrap_or("");
        self.store.log_event("GITHUB_CONTENTS", "PASS", &format!("{repo} {path} sha={sha}"))?;
        Ok(file)
    }

    pub fn github_rate(&self) -> Result<Value> {
        if self.offline()? {
            return Err(err("OFFLINE_MODE_ENABLED"));
        }
        let token = self.installation_token().ok_or_else(|| err("GITHUB_TOKEN_NOT_STORED"))?;
        let (_status, body) = UreqGithub::get_json(github::rate_url(), &token)?;
        let rate = github::parse_rate(&body)?;
        self.store.log_event(
            "GITHUB_RATE",
            "PASS",
            &format!("remaining={}", rate.get("remaining").and_then(|v| v.as_i64()).unwrap_or(0)),
        )?;
        Ok(rate)
    }

    pub fn model_dir(&self) -> PathBuf {
        if let Some(dir) = std::env::var_os("LOUKSNA_MODEL_DIR") {
            return PathBuf::from(dir);
        }
        let bundled = PathBuf::from("/usr/share/louksna/models");
        if bundled.join(voice::REQUIRED_MODEL_FILE).is_file() {
            return bundled;
        }
        PathBuf::from("/tmp/louksna-cache")
    }

    pub fn piper_program(&self) -> String {
        std::env::var("LOUKSNA_PIPER").unwrap_or_else(|_| "/usr/lib/louksna/piper-wrapper".into())
    }

    pub fn whisper_program(&self) -> String {
        std::env::var("LOUKSNA_WHISPER").unwrap_or_else(|_| "/usr/lib/louksna/whisper-cli".into())
    }

    pub fn speak(&self, text: &str) -> Result<PathBuf> {
        flow::set_session(&self.store, "VOICE_SESSION", "ACTIVE")?;
        let out = self.state_dir.join("voice").join(format!("utt-{}.wav", store::now()));
        voice::speak(
            &self.piper_program(),
            &self.model_dir().join(voice::REQUIRED_MODEL_FILE),
            text,
            &out,
        )?;
        self.store.insert_record(4, "tts", &json!({"speaker": "1", "model": voice::REQUIRED_MODEL_FILE, "bytes": std::fs::metadata(&out).map(|m| m.len()).unwrap_or(0)}).to_string())?;
        self.store.log_event("TTS", "PASS", "Piper Sharvard speaker 1")?;
        Ok(out)
    }

    pub fn transcribe_wav(&self, wav: &Path) -> Result<String> {
        flow::set_session(&self.store, "VOICE_SESSION", "ACTIVE")?;
        let text = voice::transcribe(&self.whisper_program(), &self.model_dir().join("ggml-tiny.bin"), wav)?;
        self.store.insert_chat("user", &text, "stt")?;
        self.store.insert_record(4, "stt", &json!({"chars": text.chars().count()}).to_string())?;
        self.store.log_event("STT", "PASS", "whisper-cli transcript persisted")?;
        Ok(text)
    }
}
