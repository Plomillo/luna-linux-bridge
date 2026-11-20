use crate::error::{err, Result};
use rusqlite::{backup::Backup, params, Connection};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

pub const LAYER_NAMES: [&str; 15] = [
    "conversational",
    "operational",
    "project",
    "voice",
    "plans",
    "checkpoints",
    "evidence",
    "attachments",
    "github_linkage",
    "sessions",
    "settings",
    "artifacts",
    "repairs",
    "audit",
    "non_regression",
];

pub struct Store {
    pub path: PathBuf,
    conn: Connection,
}

impl Store {
    pub fn open(path: &Path) -> Result<Self> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let conn = Connection::open(path)?;
        conn.busy_timeout(std::time::Duration::from_secs(4))?;
        let store = Store {
            path: path.to_path_buf(),
            conn,
        };
        store.init()?;
        Ok(store)
    }

    fn init(&self) -> Result<()> {
        self.conn.execute_batch(
            r#"
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS records (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              layer INTEGER NOT NULL CHECK(layer BETWEEN 1 AND 15),
              kind TEXT NOT NULL,
              body TEXT NOT NULL,
              sha256 TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              utc TEXT NOT NULL,
              operation TEXT NOT NULL,
              status TEXT NOT NULL,
              detail TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              utc TEXT NOT NULL,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              transport TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS plans (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              scope_json TEXT NOT NULL,
              state TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY,
              plan_id TEXT NOT NULL,
              kind TEXT NOT NULL,
              payload TEXT NOT NULL,
              state TEXT NOT NULL,
              result TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              FOREIGN KEY(plan_id) REFERENCES plans(id)
            );
            CREATE TABLE IF NOT EXISTS validations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              gate TEXT NOT NULL,
              subject TEXT NOT NULL,
              verdict TEXT NOT NULL,
              db_sha256 TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS checkpoints (
              id TEXT PRIMARY KEY,
              label TEXT NOT NULL,
              db_sha256 TEXT NOT NULL,
              path TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              state TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            "#,
        )?;
        let n: i64 = self
            .conn
            .query_row("SELECT COUNT(*) FROM records WHERE kind='genesis'", [], |r| r.get(0))?;
        if n == 0 {
            for (idx, name) in LAYER_NAMES.iter().enumerate() {
                let body = format!("{{\"layer\":{},\"name\":\"{name}\",\"event\":\"genesis\"}}", idx + 1);
                self.insert_record((idx + 1) as i64, "genesis", &body)?;
            }
        }
        Ok(())
    }

    pub fn layer_count(&self) -> Result<i64> {
        let n = self.conn.query_row(
            "SELECT COUNT(DISTINCT layer) FROM records",
            [],
            |r| r.get(0),
        )?;
        Ok(n)
    }

    pub fn insert_record(&self, layer: i64, kind: &str, body: &str) -> Result<i64> {
        if !(1..=15).contains(&layer) {
            return Err(err("LAYER_OUT_OF_RANGE"));
        }
        let body = redact(body);
        let sha = sha256_hex(body.as_bytes());
        self.conn.execute(
            "INSERT INTO records(layer,kind,body,sha256,created_at) VALUES(?1,?2,?3,?4,?5)",
            params![layer, kind, body, sha, now()],
        )?;
        Ok(self.conn.last_insert_rowid())
    }

    pub fn log_event(&self, operation: &str, status: &str, detail: &str) -> Result<()> {
        let detail = redact(detail);
        self.conn.execute(
            "INSERT INTO evidence(utc,operation,status,detail) VALUES(?1,?2,?3,?4)",
            params![now(), operation, status, detail],
        )?;
        let _ = self.insert_record(
            7,
            "evidence",
            &format!("{{\"operation\":\"{operation}\",\"status\":\"{status}\",\"detail\":{}}}", serde_json::to_string(&detail)?),
        );
        Ok(())
    }

    pub fn evidence_recent(&self, limit: i64) -> Result<Vec<serde_json::Value>> {
        let n = limit.clamp(1, 500);
        let mut stmt = self.conn.prepare(
            "SELECT id,utc,operation,status,detail FROM evidence ORDER BY id DESC LIMIT ?1",
        )?;
        let rows = stmt.query_map([n], |r| {
            Ok(serde_json::json!({
                "id": r.get::<_, i64>(0)?,
                "utc": r.get::<_, String>(1)?,
                "operation": r.get::<_, String>(2)?,
                "status": r.get::<_, String>(3)?,
                "detail": r.get::<_, String>(4)?,
            }))
        })?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?);
        }
        out.reverse();
        Ok(out)
    }

    pub fn insert_chat(&self, role: &str, content: &str, transport: &str) -> Result<i64> {
        let content = redact(content);
        self.conn.execute(
            "INSERT INTO chat_messages(utc,role,content,transport) VALUES(?1,?2,?3,?4)",
            params![now(), role, content, transport],
        )?;
        let id = self.conn.last_insert_rowid();
        self.insert_record(
            1,
            "chat",
            &serde_json::json!({"id": id, "role": role, "content": content, "transport": transport}).to_string(),
        )?;
        Ok(id)
    }

    pub fn chat_history(&self, limit: i64) -> Result<Vec<serde_json::Value>> {
        let n = limit.clamp(1, 500);
        let mut stmt = self.conn.prepare(
            "SELECT id,utc,role,content,transport FROM chat_messages ORDER BY id DESC LIMIT ?1",
        )?;
        let rows = stmt.query_map([n], |r| {
            Ok(serde_json::json!({
                "id": r.get::<_, i64>(0)?,
                "utc": r.get::<_, String>(1)?,
                "role": r.get::<_, String>(2)?,
                "content": r.get::<_, String>(3)?,
                "transport": r.get::<_, String>(4)?,
            }))
        })?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?);
        }
        out.reverse();
        Ok(out)
    }

    pub fn setting_set(&self, key: &str, value: &str) -> Result<()> {
        if key.to_ascii_lowercase().contains("token") || key.to_ascii_lowercase().contains("secret") || key.to_ascii_lowercase().contains("private") {
            return Err(err("SECRET_NOT_ALLOWED_IN_SETTINGS"));
        }
        let value = redact(value);
        self.conn.execute(
            "INSERT INTO settings(key,value) VALUES(?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            params![key, value],
        )?;
        self.insert_record(11, "setting", &serde_json::json!({"key": key, "value": value}).to_string())?;
        Ok(())
    }

    pub fn setting_get(&self, key: &str) -> Result<Option<String>> {
        let mut stmt = self.conn.prepare("SELECT value FROM settings WHERE key=?1")?;
        let mut rows = stmt.query(params![key])?;
        if let Some(row) = rows.next()? {
            Ok(Some(row.get(0)?))
        } else {
            Ok(None)
        }
    }

    pub fn load_settings(&self) -> Result<serde_json::Value> {
        let mut settings = serde_json::json!({
            "offline_mode": false,
            "preferred_repo": "",
            "github_owner_filter": "",
            "remote_chat_bridge": ""
        });
        let mut stmt = self.conn.prepare("SELECT key,value FROM settings")?;
        let rows = stmt.query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?)))?;
        for row in rows {
            let (k, v) = row?;
            match k.as_str() {
                "offline_mode" => settings["offline_mode"] = serde_json::json!(v == "true"),
                "preferred_repo" => settings["preferred_repo"] = serde_json::json!(v),
                "github_owner_filter" => settings["github_owner_filter"] = serde_json::json!(v),
                "remote_chat_bridge" => settings["remote_chat_bridge"] = serde_json::json!(v),
                _ => {}
            }
        }
        Ok(settings)
    }

    pub fn save_settings_obj(&self, settings: &serde_json::Value) -> Result<()> {
        let pairs = [
            ("offline_mode", if settings.get("offline_mode").and_then(|v| v.as_bool()).unwrap_or(false) { "true" } else { "false" }),
            ("preferred_repo", ""),
            ("github_owner_filter", ""),
            ("remote_chat_bridge", ""),
        ];
        let preferred = settings.get("preferred_repo").and_then(|v| v.as_str()).unwrap_or("");
        let owner = settings.get("github_owner_filter").and_then(|v| v.as_str()).unwrap_or("");
        let bridge = settings.get("remote_chat_bridge").and_then(|v| v.as_str()).unwrap_or("");
        self.setting_set("offline_mode", pairs[0].1)?;
        self.setting_set("preferred_repo", preferred)?;
        self.setting_set("github_owner_filter", owner)?;
        self.setting_set("remote_chat_bridge", bridge)?;
        self.log_event("SETTINGS_SAVE", "PASS", "Configuracion no secreta persistida en SQLite.")?;
        Ok(())
    }

    pub fn conn(&self) -> &Connection {
        &self.conn
    }

    pub fn checkpoint_wal(&self) -> Result<()> {
        self.conn.execute_batch("PRAGMA wal_checkpoint(FULL);")?;
        Ok(())
    }

    pub fn snapshot_to(&self, dest: &Path) -> Result<()> {
        if let Some(parent) = dest.parent() {
            fs::create_dir_all(parent)?;
        }
        self.checkpoint_wal()?;
        let mut dst = Connection::open(dest)?;
        {
            let backup = Backup::new(&self.conn, &mut dst)?;
            backup.step(-1)?;
        }
        Ok(())
    }
}

pub fn now() -> String {
    let secs = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    format!("{secs}")
}

pub fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hex::encode(hasher.finalize())
}

pub fn file_sha256(path: &Path) -> Result<String> {
    let bytes = fs::read(path)?;
    Ok(sha256_hex(&bytes))
}

pub fn redact(input: &str) -> String {
    let mut out = input.to_string();
    for prefix in ["github_pat_", "ghp_", "gho_", "ghu_", "ghs_", "glpat-", "AKIA", "xai-"] {
        while let Some(start) = out.find(prefix) {
            let rest = &out[start..];
            let end_rel = rest.find(|c: char| c.is_whitespace() || c == '"' || c == '\'' || c == ',' || c == '}').unwrap_or(rest.len());
            let end = start + end_rel.max(prefix.len());
            out.replace_range(start..end, "[REDACTED]");
        }
    }
    if let Some(start) = out.find("-----BEGIN") {
        if let Some(rel) = out[start..].find("-----END") {
            let after = start + rel;
            let tail = out[after..].find("-----").map(|n| after + n + 5).unwrap_or(out.len());
            out.replace_range(start..tail, "[REDACTED]");
        }
    }
    out
}

pub fn restore_snapshot(live: &Path, snapshot: &Path) -> Result<()> {
    if !snapshot.is_file() {
        return Err(err("CHECKPOINT_MISSING"));
    }
    let wal = PathBuf::from(format!("{}-wal", live.display()));
    let shm = PathBuf::from(format!("{}-shm", live.display()));
    let _ = fs::remove_file(&wal);
    let _ = fs::remove_file(&shm);
    fs::copy(snapshot, live)?;
    Ok(())
}

pub fn write_secret_file(path: &Path, contents: &str) -> Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = fs::set_permissions(parent, fs::Permissions::from_mode(0o700));
        }
    }
    fs::write(path, contents)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(path, fs::Permissions::from_mode(0o600))?;
    }
    Ok(())
}

pub fn secret_mode_is_private(path: &Path) -> Result<bool> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mode = fs::metadata(path)?.permissions().mode() & 0o777;
        Ok(mode == 0o600)
    }
    #[cfg(not(unix))]
    {
        let _ = path;
        Ok(true)
    }
}
