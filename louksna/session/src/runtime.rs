use crate::error::{err, Result};
use crate::flow;
use crate::github::{self, UreqGithub};
use crate::store::{self, write_secret_file, Store};
use crate::voice;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};

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
            let reply = "Mensaje registrado. El bridge remoto de arquitectura todavia no esta enlazado; no simulare una respuesta remota.";
            self.store.insert_chat("louksna", reply, "local-status")?;
            self.store.log_event("CHAT", "PARTIAL", "Mensaje persistido; bridge remoto no configurado.")?;
            return Ok(reply.to_string());
        }
        self.post_bridge(&bridge, msg)
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
            "installation" => {
                write_secret_file(&secrets.join("installation_token"), token.trim())?;
                self.store.log_event("GITHUB_SECRET_STORE", "PASS", "Installation token stored mode 0600; value not recorded.")?;
                Ok("installation")
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
        let (_status, body) = UreqGithub::get_json(&github::installation_repo_url(100), &token)?;
        let repos = github::parse_installation_repos(&body)?;
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
