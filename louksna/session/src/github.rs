use crate::error::{err, Result};
use hmac::{Hmac, Mac};
use jsonwebtoken::{Algorithm, EncodingKey, Header};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::Sha256;
use std::time::{SystemTime, UNIX_EPOCH};

type HmacSha256 = Hmac<Sha256>;

#[derive(Debug, Serialize, Deserialize)]
struct AppClaims {
    iat: u64,
    exp: u64,
    iss: String,
}

pub fn app_jwt(app_id: &str, pem: &str, now: u64) -> Result<String> {
    if !pem.contains("BEGIN") {
        return Err(err("APP_KEY_NOT_PEM"));
    }
    let key = EncodingKey::from_rsa_pem(pem.as_bytes()).map_err(|e| err(format!("APP_KEY_REJECTED:{e}")))?;
    let claims = AppClaims {
        iat: now.saturating_sub(30),
        exp: now.saturating_add(540),
        iss: app_id.to_string(),
    };
    jsonwebtoken::encode(&Header::new(Algorithm::RS256), &claims, &key).map_err(|e| err(format!("JWT_ENCODE:{e}")))
}

pub fn classify_credential(token: &str) -> Result<&'static str> {
    let t = token.trim();
    if t.starts_with("ghs_") && t.len() >= 20 {
        Ok("installation")
    } else if t.starts_with("ghp_") || t.starts_with("github_pat_") || t.starts_with("gho_") || t.starts_with("ghu_") {
        Err(err("PAT_REJECTED_USE_GITHUB_APP_INSTALLATION_TOKEN"))
    } else if t.contains("BEGIN PRIVATE KEY") || t.contains("BEGIN RSA PRIVATE KEY") {
        Ok("app_private_key")
    } else {
        Err(err("CREDENTIAL_REJECTED"))
    }
}

pub fn verify_webhook(secret: &[u8], body: &[u8], signature_header: &str) -> Result<bool> {
    let hexsig = signature_header
        .strip_prefix("sha256=")
        .ok_or_else(|| err("WEBHOOK_SIGNATURE_MALFORMED"))?;
    let mut mac = HmacSha256::new_from_slice(secret).map_err(|e| err(e.to_string()))?;
    mac.update(body);
    let expected = hex::encode(mac.finalize().into_bytes());
    Ok(constant_time_eq(expected.as_bytes(), hexsig.as_bytes()))
}

fn constant_time_eq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut diff = 0u8;
    for (x, y) in a.iter().zip(b.iter()) {
        diff |= x ^ y;
    }
    diff == 0
}

pub fn ref_update_allowed(current_sha: &str, expected_sha: &str) -> bool {
    !expected_sha.is_empty() && current_sha == expected_sha && current_sha.len() == 40
}

pub fn contents_put_body(message: &str, content: &str, branch: &str, expected_sha: &str) -> Result<Value> {
    if expected_sha.trim().is_empty() {
        return Err(err("EXPECTED_SHA_REQUIRED"));
    }
    if branch.trim().is_empty() || message.trim().is_empty() {
        return Err(err("COMMIT_FIELDS_REQUIRED"));
    }
    let b64 = base64::Engine::encode(&base64::engine::general_purpose::STANDARD, content.as_bytes());
    Ok(json!({
        "message": message,
        "content": b64,
        "branch": branch,
        "sha": expected_sha
    }))
}

pub fn parse_installation_repos(body: &Value) -> Result<Vec<Value>> {
    let repos = body
        .get("repositories")
        .and_then(|v| v.as_array())
        .ok_or_else(|| err("GITHUB_REPOS_SHAPE"))?;
    let mut out = Vec::new();
    for repo in repos {
        out.push(json!({
            "full_name": repo.get("full_name").and_then(|v| v.as_str()).unwrap_or(""),
            "private": repo.get("private").and_then(|v| v.as_bool()).unwrap_or(false),
            "default_branch": repo.get("default_branch").and_then(|v| v.as_str()).unwrap_or(""),
            "updated_at": repo.get("updated_at").and_then(|v| v.as_str()).unwrap_or(""),
            "open_issues_count": repo.get("open_issues_count").and_then(|v| v.as_i64()).unwrap_or(0)
        }));
    }
    Ok(out)
}

pub fn parse_pulls(body: &Value) -> Result<Vec<Value>> {
    let arr = body.as_array().ok_or_else(|| err("GITHUB_PULLS_SHAPE"))?;
    let mut out = Vec::new();
    for pr in arr {
        out.push(json!({
            "number": pr.get("number").and_then(|v| v.as_i64()).unwrap_or(0),
            "title": pr.get("title").and_then(|v| v.as_str()).unwrap_or(""),
            "state": pr.get("state").and_then(|v| v.as_str()).unwrap_or(""),
            "draft": pr.get("draft").and_then(|v| v.as_bool()).unwrap_or(false),
            "updated_at": pr.get("updated_at").and_then(|v| v.as_str()).unwrap_or(""),
            "html_url": pr.get("html_url").and_then(|v| v.as_str()).unwrap_or("")
        }));
    }
    Ok(out)
}

pub fn unix_now() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0)
}

pub struct UreqGithub;

impl UreqGithub {
    pub fn get_json(url: &str, token: &str) -> Result<(u16, Value)> {
        if !(url.starts_with("https://api.github.com/")) {
            return Err(err("GITHUB_URL_NOT_API"));
        }
        let response = ureq::get(url)
            .set("Authorization", &format!("Bearer {token}"))
            .set("Accept", "application/vnd.github+json")
            .set("User-Agent", "LOUKSNA-ZONA-DIRECTIVA/3.0")
            .set("X-GitHub-Api-Version", "2022-11-28")
            .call();
        match response {
            Ok(resp) => {
                let status = resp.status();
                let value: Value = resp.into_json().map_err(|e| err(format!("GITHUB_JSON:{e}")))?;
                Ok((status, value))
            }
            Err(ureq::Error::Status(code, resp)) => {
                let _ = resp;
                if code == 403 || code == 429 {
                    Err(err(format!("GITHUB_RATE_OR_FORBIDDEN:{code}")))
                } else {
                    Err(err(format!("GITHUB_HTTP_{code}")))
                }
            }
            Err(e) => Err(err(format!("GITHUB_NETWORK:{e}"))),
        }
    }

    pub fn put_json(url: &str, token: &str, body: &Value) -> Result<(u16, Value)> {
        if !(url.starts_with("https://api.github.com/")) {
            return Err(err("GITHUB_URL_NOT_API"));
        }
        let response = ureq::put(url)
            .set("Authorization", &format!("Bearer {token}"))
            .set("Accept", "application/vnd.github+json")
            .set("User-Agent", "LOUKSNA-ZONA-DIRECTIVA/3.0")
            .set("X-GitHub-Api-Version", "2022-11-28")
            .send_json(body.clone());
        match response {
            Ok(resp) => {
                let status = resp.status();
                let value: Value = resp.into_json().map_err(|e| err(format!("GITHUB_JSON:{e}")))?;
                Ok((status, value))
            }
            Err(ureq::Error::Status(code, _)) => Err(err(format!("GITHUB_HTTP_{code}"))),
            Err(e) => Err(err(format!("GITHUB_NETWORK:{e}"))),
        }
    }
}

pub fn installation_repo_url(per_page: u32) -> String {
    format!("https://api.github.com/installation/repositories?per_page={per_page}")
}

pub fn pulls_url(repo: &str) -> Result<String> {
    validate_repo(repo)?;
    Ok(format!("https://api.github.com/repos/{repo}/pulls?state=open&per_page=50"))
}

pub fn issues_url(repo: &str) -> Result<String> {
    validate_repo(repo)?;
    Ok(format!("https://api.github.com/repos/{repo}/issues?state=open&per_page=50"))
}

pub fn contents_url(repo: &str, path: &str) -> Result<String> {
    validate_repo(repo)?;
    if path.is_empty() || path.contains("..") || path.starts_with('/') {
        return Err(err("GITHUB_PATH_REJECTED"));
    }
    Ok(format!("https://api.github.com/repos/{repo}/contents/{path}"))
}

fn validate_repo(repo: &str) -> Result<()> {
    let mut parts = repo.split('/');
    let owner = parts.next().unwrap_or("");
    let name = parts.next().unwrap_or("");
    if parts.next().is_some() || owner.is_empty() || name.is_empty() {
        return Err(err("REPO_SHAPE"));
    }
    if !owner.chars().all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_') {
        return Err(err("REPO_OWNER"));
    }
    if !name.chars().all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_' || c == '.') {
        return Err(err("REPO_NAME"));
    }
    Ok(())
}
