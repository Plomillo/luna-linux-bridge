pub mod error;
pub mod flow;
pub mod g23;
pub mod github;
pub mod http;
pub mod mra;
pub mod mra_oracle;
pub mod runtime;
pub mod store;
pub mod voice;

use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

fn scratch() -> PathBuf {
    let nanos = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
    let dir = std::env::temp_dir().join(format!("louksna-test-{nanos}"));
    fs::create_dir_all(&dir).unwrap();
    dir
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::flow::{approve_plan, complete_task, create_plan, enqueue_task, session_state, set_session};
    use crate::github::{app_jwt, branches_url, classify_credential, contents_put_body, contents_url, parse_branches, parse_commits, parse_contents, parse_rate, ref_update_allowed, verify_webhook};
    use crate::runtime::App;
    use crate::store::{redact, restore_snapshot, secret_mode_is_private};
    use crate::voice::{assert_speaker_locked, female_speaker_id, piper_invocation, reject_empty_audio, whisper_invocation, REQUIRED_SPEAKER};
    use hmac::Mac;
    use std::fs;
    use std::path::PathBuf;
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn fifteen_layers_and_chat_is_not_a_fake_model() {
        let dir = scratch();
        let app = App::open(&dir).unwrap();
        assert_eq!(app.store.layer_count().unwrap(), 15);
        let reply = app.chat_send("hola luna").unwrap();
        assert!(reply.contains("no simulare"));
        let history = app.store.chat_history(10).unwrap();
        assert_eq!(history.len(), 2);
        assert_eq!(history[0]["role"], "user");
        assert_eq!(history[1]["transport"], "local-status");
    }

    #[test]
    fn plan_gate_scope_and_voice_session_survives_task() {
        let dir = scratch();
        let app = App::open(&dir).unwrap();
        set_session(&app.store, "VOICE_SESSION", "ACTIVE").unwrap();
        let plan = create_plan(&app.store, "reconstruir", &["record".into()]).unwrap();
        assert!(enqueue_task(&app.store, &plan, "record", "x").is_err());
        approve_plan(&app.store, &plan).unwrap();
        assert!(approve_plan(&app.store, &plan).is_err());
        assert!(enqueue_task(&app.store, &plan, "github:write", "no").is_err());
        let task = enqueue_task(&app.store, &plan, "record", "ok").unwrap();
        assert_eq!(session_state(&app.store, "VOICE_SESSION").unwrap(), "ACTIVE");
        assert_eq!(session_state(&app.store, "TASK_SESSION").unwrap(), "ACTIVE");
        complete_task(&app.store, &task, false, "fallo").unwrap();
        complete_task(&app.store, &task, true, "repaired").unwrap();
    }

    #[test]
    fn secrets_are_redacted_and_pat_is_rejected() {
        assert!(redact("token ghp_abcdefghijklmnopqrstuvwxyz").contains("[REDACTED]"));
        assert!(!redact("ghp_abcdefghijklmnopqrstuvwxyz").contains("ghp_"));
        assert!(classify_credential("github_pat_abcdefghijklmnopqrstuvwxyz").is_err());
        assert!(classify_credential("ghp_abcdefghijklmnopqrstuvwxyz").is_err());
        assert_eq!(classify_credential("ghs_abcdefghijklmnopqrstuvwxyz").unwrap(), "installation");
        assert_eq!(classify_credential("ghu_abcdefghijklmnopqrstuvwxyz").unwrap(), "user_to_server");
        let dir = scratch();
        let app = App::open(&dir).unwrap();
        app.chat_send("mira ghp_abcdefghijklmnopqrstuvwxyz por favor").unwrap();
        let history = app.store.chat_history(10).unwrap();
        let blob = serde_json::to_string(&history).unwrap();
        assert!(!blob.contains("ghp_"));
        app.store_credential("ghs_abcdefghijklmnopqrstuvwxyz").unwrap();
        let path = dir.join("secrets/installation_token");
        assert!(secret_mode_is_private(&path).unwrap());
        assert!(app.store_credential("ghp_abcdefghijklmnopqrstuvwxyz").is_err());
    }

    #[test]
    fn webhook_and_expected_sha_and_speaker_lock() {
        let secret = b"s3cret";
        let body = b"{\"ok\":true}";
        let mut mac = hmac::Hmac::<sha2::Sha256>::new_from_slice(secret).unwrap();
        hmac::Mac::update(&mut mac, body);
        let sig = format!("sha256={}", hex::encode(mac.finalize().into_bytes()));
        assert!(verify_webhook(secret, body, &sig).unwrap());
        assert!(!verify_webhook(secret, b"tamper", &sig).unwrap());
        assert!(ref_update_allowed("0123456789abcdef0123456789abcdef01234567", "0123456789abcdef0123456789abcdef01234567"));
        assert!(!ref_update_allowed("0123456789abcdef0123456789abcdef01234567", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"));
        assert!(contents_put_body("m", "hello", "work/luna-v3-reconstruction-20261119", "").is_err());
        let body = contents_put_body("m", "hello", "work/luna-v3-reconstruction-20261119", "0123456789abcdef0123456789abcdef01234567").unwrap();
        assert_eq!(body["sha"], "0123456789abcdef0123456789abcdef01234567");
        let model = r#"{"language":{"code":"es_ES"},"speaker_id_map":{"M":0,"F":1},"num_speakers":2}"#;
        assert_eq!(female_speaker_id(model).unwrap(), 1);
        assert!(female_speaker_id(r#"{"language":{"code":"es_ES"},"speaker_id_map":{"F":0}}"#).is_err());
        let inv = piper_invocation("/usr/lib/louksna/piper-wrapper", "/usr/share/louksna/models/es_ES-sharvard-medium.onnx", "/tmp/out.wav");
        assert_speaker_locked(&inv).unwrap();
        assert!(inv.args.windows(2).any(|w| w[0] == "--speaker" && w[1] == REQUIRED_SPEAKER));
        let (_bin, args) = whisper_invocation("whisper-cli", "ggml-tiny.bin", "in.wav");
        assert!(args.windows(2).any(|w| w[0] == "-l" && w[1] == "es"));
        assert!(reject_empty_audio(b"RIFF").is_err());
    }

    #[test]
    fn checkpoint_restore_and_g23_before_g24() {
        let dir = scratch();
        let app = App::open(&dir).unwrap();
        app.store.insert_record(2, "marker", "antes").unwrap();
        let snap = dir.join("snap.sqlite");
        app.store.snapshot_to(&snap).unwrap();
        app.store.insert_record(2, "marker", "despues").unwrap();
        drop(app);
        restore_snapshot(&dir.join("louksna.db"), &snap).unwrap();
        let app = App::open(&dir).unwrap();
        let n: i64 = app.store.conn().query_row(
            "SELECT COUNT(*) FROM records WHERE body LIKE '%despues%'",
            [],
            |r| r.get(0),
        ).unwrap();
        assert_eq!(n, 0);
        let verdict = crate::g23::validate(&app.store).unwrap();
        assert_eq!(verdict["verdict"], "PASS");
        assert!(crate::g23::certify_g24(&app.store, &dir.join("missing.json"), "product").is_err());
        let verdict_path = dir.join("g23-verdict.json");
        crate::g23::write_verdict(&verdict_path, &verdict).unwrap();
        let g24 = crate::g23::certify_g24(&app.store, &verdict_path, "product").unwrap();
        assert_eq!(g24["verdict"], "PASS");
        assert_eq!(g24["depends_on"], "louksna-g23");
        let other = scratch();
        let foreign = App::open(&other).unwrap();
        std::fs::copy(&verdict_path, other.join("g23-verdict.json")).unwrap();
        let rejected = crate::g23::certify_g24(&foreign.store, &other.join("g23-verdict.json"), "foreign");
        assert!(rejected.is_err(), "fresh database must not inherit another G23 verdict");
    }

    #[test]
    fn loopback_only() {
        assert!(crate::http::enforce_loopback("127.0.0.1:47321").is_ok());
        assert!(crate::http::enforce_loopback("0.0.0.0:47321").is_err());
        assert!(crate::http::enforce_loopback("192.168.1.10:47321").is_err());
    }

    #[test]
    fn mra_suite_matches_pre_registered_expectations_and_oracle_rejects_tamper() {
        let dir = scratch();
        let report = crate::mra::run_suite(&dir).unwrap();
        assert_eq!(report["count"], 36);
        assert_eq!(report["failed"], 0, "{report}");
        assert_eq!(report["certification"], "PENDING_ORACLE");
        assert_eq!(report["consciousness"], "NOT_CLAIMED");
        let verdict = crate::mra::oracle_verify(&report).unwrap();
        assert_eq!(verdict["producer"], "louksna-mra-oracle");
        assert_eq!(verdict["verdict"], "GRANTED");
        assert_eq!(verdict["product_platform"], "NOT_CERTIFIED");
        let mut tampered = report.clone();
        tampered["cases"][0]["observed"] = serde_json::json!("TAMPERED");
        assert!(crate::mra::oracle_verify(&tampered).is_err());
        let mut self_cert = report.clone();
        self_cert["certification"] = serde_json::json!("GRANTED");
        assert!(crate::mra::oracle_verify(&self_cert).is_err());
    }

    #[test]
    fn github_read_parsers_and_path_guards() {
        assert!(branches_url("not-a-repo").is_err());
        assert!(crate::github::branch_url("Plomillo/luna-linux-bridge", "../x").is_err());
        assert!(crate::github::branch_url("Plomillo/luna-linux-bridge", "work/luna").unwrap().contains("work%2Fluna"));
        assert!(contents_url("Plomillo/luna-linux-bridge", "../secret").is_err());
        let branches = parse_branches(&serde_json::json!([
            {"name":"work","protected":true,"commit":{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}
        ])).unwrap();
        assert_eq!(branches[0]["name"], "work");
        assert_eq!(branches[0]["sha"], "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
        let commits = parse_commits(&serde_json::json!([
            {"sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","commit":{"message":"hola\nmas","author":{"date":"2026-01-01T00:00:00Z"}}}
        ])).unwrap();
        assert_eq!(commits[0]["message"], "hola");
        let rate = parse_rate(&serde_json::json!({"resources":{"core":{"limit":5000,"remaining":4990,"reset":1,"used":10}}})).unwrap();
        assert_eq!(rate["remaining"], 4990);
        let file = parse_contents(&serde_json::json!({
            "type":"file","encoding":"base64","path":"README.md","sha":"abc","size":4,"content":"aG9sYQ=="
        })).unwrap();
        assert_eq!(file["text"], "hola");
        assert!(parse_contents(&serde_json::json!({"type":"dir"})).is_err());
    }

    #[test]
    fn real_sharvard_json_locks_female_speaker_to_one() {
        let path = "/tmp/louksna-cache/es_ES-sharvard-medium.onnx.json";
        if !std::path::Path::new(path).is_file() {
            panic!("MODEL_JSON_ABSENT {path}");
        }
        let raw = fs::read_to_string(path).unwrap();
        assert_eq!(female_speaker_id(&raw).unwrap(), 1);
    }

    #[test]
    fn jwt_rs256_roundtrip_with_ephemeral_key() {
        let dir = scratch();
        let key = dir.join("app.pem");
        let pubk = dir.join("app.pub.pem");
        let status = std::process::Command::new("openssl")
            .args(["genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out"])
            .arg(&key)
            .status();
        if status.map(|s| !s.success()).unwrap_or(true) {
            panic!("OPENSSL_REQUIRED_FOR_JWT");
        }
        let pem = fs::read_to_string(&key).unwrap();
        let token = app_jwt("123456", &pem, 1_700_000_000).unwrap();
        let mut parts = token.split('.');
        let header = parts.next().unwrap();
        let payload = parts.next().unwrap();
        let sig_b64 = parts.next().unwrap();
        assert!(parts.next().is_none());
        let payload_json = String::from_utf8(b64url_decode(payload)).unwrap();
        assert!(payload_json.contains("\"iss\":\"123456\""));
        let signing = dir.join("signing.txt");
        fs::write(&signing, format!("{header}.{payload}")).unwrap();
        let sig = dir.join("sig.bin");
        fs::write(&sig, b64url_decode(sig_b64)).unwrap();
        let pub_status = std::process::Command::new("openssl")
            .args(["rsa", "-in"])
            .arg(&key)
            .arg("-pubout")
            .arg("-out")
            .arg(&pubk)
            .status()
            .unwrap();
        assert!(pub_status.success());
        let verify = std::process::Command::new("openssl")
            .args(["dgst", "-sha256", "-verify"])
            .arg(&pubk)
            .arg("-signature")
            .arg(&sig)
            .arg(&signing)
            .status()
            .unwrap();
        assert!(verify.success(), "openssl rejected the GitHub App JWT");
    }
}

#[cfg(test)]
fn b64url_decode(input: &str) -> Vec<u8> {
    let mut s = input.replace('-', "+").replace('_', "/");
    while s.len() % 4 != 0 {
        s.push('=');
    }
    base64::Engine::decode(&base64::engine::general_purpose::STANDARD, s).unwrap()
}

pub fn selftest() -> crate::error::Result<serde_json::Value> {
    use crate::flow::{approve_plan, complete_task, create_plan, enqueue_task, session_state, set_session};
    use crate::runtime::App;
    use crate::voice::{assert_speaker_locked, piper_invocation};
    let dir = scratch();
    let app = App::open(&dir)?;
    let mut checks = serde_json::Map::new();
    checks.insert("layers".into(), serde_json::json!(app.store.layer_count()? == 15));
    let reply = app.chat_send("ping")?;
    checks.insert("chat_no_fake".into(), serde_json::json!(reply.contains("no simulare")));
    set_session(&app.store, "VOICE_SESSION", "ACTIVE")?;
    let plan = create_plan(&app.store, "selftest", &["record".into()])?;
    approve_plan(&app.store, &plan)?;
    let task = enqueue_task(&app.store, &plan, "record", "self")?;
    checks.insert("voice_survives".into(), serde_json::json!(session_state(&app.store, "VOICE_SESSION")? == "ACTIVE"));
    complete_task(&app.store, &task, true, "ok")?;
    let inv = piper_invocation("piper", "/models/es_ES-sharvard-medium.onnx", "/tmp/x.wav");
    checks.insert("speaker_1".into(), serde_json::json!(assert_speaker_locked(&inv).is_ok()));
    let verdict = g23::validate(&app.store)?;
    let vpath = dir.join("g23-verdict.json");
    g23::write_verdict(&vpath, &verdict)?;
    let g24_ok = verdict["verdict"] == "PASS" && g23::certify_g24(&app.store, &vpath, "selftest").is_ok();
    checks.insert("g23".into(), serde_json::json!(verdict["verdict"] == "PASS"));
    checks.insert("g24".into(), serde_json::json!(g24_ok));
    let require_voice = std::env::var("LOUKSNA_REQUIRE_SYNTHESIS").ok().as_deref() == Some("1");
    match app.speak("Hola. Soy Luna.") {
        Ok(path) => checks.insert("synthesis".into(), serde_json::json!({"verdict":"PASS","wav":path})),
        Err(e) if require_voice => return Err(e),
        Err(e) => checks.insert("synthesis".into(), serde_json::json!({"verdict":"NOT_RUN","error":e.0})),
    };
    let all = ["layers", "chat_no_fake", "voice_survives", "speaker_1", "g23", "g24"].iter().all(|k| checks.get(*k).and_then(|v| v.as_bool()) == Some(true));
    Ok(serde_json::json!({"ok": all, "checks": checks, "certification": "NOT_CERTIFIED"}))
}
